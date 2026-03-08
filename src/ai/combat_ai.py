# --- src/ai/combat_ai.py ---
"""
战斗AI：索敌、追击、攻击、广播
从原ai_system.py抽离战斗相关逻辑
"""
import math
import random
import pygame
from src.definitions import (
    SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED,
    STATE_COMBAT, STATE_IDLE
)
from src.utils import log_game_event
from src.ai.constants import (
    SCAN_RADIUS, COMBAT_FACE_DIST, COMBAT_ATTACK_RANGE, 
    SPECTATE_NOTICE_RADIUS, HOSTILE_JOBS, PASSIVE_HATE_COOLDOWN_MS
)


class CombatAI:
    """
    战斗AI模块
    
    职责：
    1. 索敌：_find_enemy - 扫描范围内敌人，管理仇恨系统
    2. 执行：_execute_combat - 追击、站位、攻击
    3. 广播：broadcast_combat_start/end - 通知周围NPC
    
    性能优化：
    - 已锁定目标时直接复用，避免每帧全量扫描
    - 仇恨累加带冷却，避免瞬间拉满
    """
    
    def __init__(self, ai_system, combat_manager):
        self._ai = ai_system
        self.combat_manager = combat_manager
        self._current_npcs = []  # 缓存当前帧的NPC列表
    
    def set_npcs_cache(self, npcs: list):
        """设置当前帧的NPC缓存（由AISystem.update调用）"""
        self._current_npcs = npcs
    
    # ══════════════════════════════════════════════════════════════
    # 索敌系统
    # ══════════════════════════════════════════════════════════════
    
    def find_enemy(self, npc, all_npcs, faction_war=None) -> object:
        """
        仇恨系统索敌逻辑：
        1. 优先返回已锁定的 aggro_target
        2. 扫描范围内潜在敌人，累加仇恨
        3. 返回仇恨最高且超过阈值的目标
        
        Args:
            npc: 当前NPC
            all_npcs: 所有NPC列表
            faction_war: 可选，势力战争系统引用（用于悬赏判断）
        
        Returns:
            目标NPC或None
        """
        my_is_villain = self._ai._is_villain(npc)
        
        # 获取玩家和悬赏系统引用
        player = next((x for x in all_npcs if getattr(x, 'job', '') == 'PLAYER'), None)

        # --- 步骤1：已锁定目标则直接复用 ---
        if npc.aggro_target is not None:
            t = npc.aggro_target
            if t.safety not in (SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED):
                dist = math.hypot(
                    npc.rect.centerx - t.rect.centerx, 
                    npc.rect.centery - t.rect.centery
                )
                if dist <= SCAN_RADIUS * 1.5:  # 追击范围比索敌范围略大
                    return t
            # 目标无效，解锁
            npc.aggro_target = None
            npc.combat_anchor_x = None
            npc.combat_anchor_y = None

        # --- 步骤2：全量扫描范围内潜在敌人 ---
        candidates = []  # [(npc, hate_value, score)]
        
        world_map = getattr(npc, '_world_map_ref', None)
        city_rect = world_map.city_rect if world_map else None
        my_is_guard = npc.job in ('GUARD', 'OFFICIAL', 'SOLDIER')
        current_time = pygame.time.get_ticks()

        for other in all_npcs:
            if other == npc:
                continue
            if other.safety in (SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED):
                continue

            dist = math.hypot(
                npc.rect.centerx - other.rect.centerx, 
                npc.rect.centery - other.rect.centery
            )
            if dist > SCAN_RADIUS:
                continue

            other_is_villain = self._ai._is_villain(other)

            # 判断敌对关系
            is_potential_enemy = False
            if my_is_villain and not other_is_villain:
                is_potential_enemy = True
            elif not my_is_villain and other_is_villain:
                is_potential_enemy = True

            if not is_potential_enemy:
                continue
            
            # 守卫不主动追击城外山贼
            if my_is_guard and city_rect and other_is_villain:
                other_in_city = city_rect.collidepoint(
                    other.rect.centerx, other.rect.centery
                )
                if not other_in_city:
                    if npc.id not in getattr(other, 'hatred', {}):
                        continue

            # 山贼城外主动施加仇恨
            if my_is_villain and city_rect:
                self._apply_villain_passive_hate(
                    npc, other, city_rect, current_time
                )
            
            # 悬赏系统：对被悬赏的玩家施加仇恨
            if player and other == player and faction_war:
                self._apply_bounty_hate(npc, player, faction_war)

            current_hate = npc.hatred.get(other.id, 0)
            
            # 计算优先级打分：距离近+财富高
            dist_score = max(0, SCAN_RADIUS - dist)
            wealth = other.inventory.get('铜钱', 0) if hasattr(other, 'inventory') else 0
            wealth_score = min(wealth * 0.5, 50)
            tie_score = dist_score + wealth_score

            candidates.append((other, current_hate, tie_score))

        if not candidates:
            return None

        # --- 步骤3：选择仇恨最高且超过阈值的目标 ---
        candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
        best_npc, best_hate, _ = candidates[0]

        if best_hate >= npc.aggro_threshold:
            npc.aggro_target = best_npc
            return best_npc

        return None
    
    def _apply_villain_passive_hate(self, npc, other, city_rect, current_time):
        """山贼对城外目标施加被动仇恨"""
        me_in_city = city_rect.collidepoint(npc.rect.centerx, npc.rect.centery)
        other_in_city = city_rect.collidepoint(other.rect.centerx, other.rect.centery)
        
        # 双方都在城外时才主动施加仇恨
        if not me_in_city and not other_in_city:
            if not hasattr(npc, '_passive_hate_cd'):
                npc._passive_hate_cd = {}
            
            last_hate_time = npc._passive_hate_cd.get(other.id, 0)
            if current_time - last_hate_time > PASSIVE_HATE_COOLDOWN_MS:
                npc._passive_hate_cd[other.id] = current_time
                passive_hate = 8
                npc.hatred[other.id] = npc.hatred.get(other.id, 0) + passive_hate
    
    def _apply_bounty_hate(self, npc, player, faction_war):
        """对被悬赏的玩家施加仇恨"""
        me_org = getattr(npc, 'org_id', '')
        if me_org == 'heifeng_zhai' or npc.job in ('BANDIT', 'THUG'):
            total_bounty, bounties = faction_war.get_bounty_on_player(player)
            for bounty in bounties:
                if (bounty.get('issuer_org') == 'heifeng_zhai' and 
                    bounty.get('active', True)):
                    bounty_hate = 50
                    npc.hatred[player.id] = npc.hatred.get(player.id, 0) + bounty_hate
                    break
    
    # ══════════════════════════════════════════════════════════════
    # 战斗执行
    # ══════════════════════════════════════════════════════════════
    
    def execute_combat(self, npc, target, world_map, dt_ms=16):
        """
        执行战斗：追击、站位、攻击
        
        设计原则：
        - 整个战斗过程中 npc.in_combat 始终为 True
        - 双方保持 COMBAT_FACE_DIST 距离"对碰"
        """
        from src.entities.building import Building
        
        # 如果在建筑内工作，先弹出
        if npc.stack_parent is not None:
            if isinstance(npc.stack_parent, Building):
                npc.bounce_off(npc.stack_parent)
                npc.is_working = False
                npc.work_timer = 0
                npc.ai_reason = "被迫应战"
        
        # 如果正在背人，先放下
        if npc.stack_child is not None:
            from src.entities import NPC as NPCClass
            patient = npc.stack_child
            if isinstance(patient, NPCClass) and patient.safety == SAFETY_DOWNED:
                npc.stack_child = None
                patient.stack_parent = None
                offset_x = random.choice([-60, 60])
                offset_y = random.choice([-40, 40])
                patient.set_pos(npc.rect.centerx + offset_x, npc.rect.centery + offset_y)
                patient.ai_reason = f"被{npc.name}紧急放下"
                npc.ai_reason = "放下伤员迎战"
                log_game_event(
                    f"[AI][COMBAT] {npc.name} 被攻击，紧急放下 {patient.name} 准备应战", 
                    tag="COMBAT"
                )

        # 目标已倒地 → 战斗结束
        if target.safety in (SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED):
            self._on_combat_victory(npc, target)
            return

        dist = math.hypot(
            target.rect.centerx - npc.rect.centerx,
            target.rect.centery - npc.rect.centery
        )

        # 计算站位点
        if dist > 0:
            dx = (npc.rect.centerx - target.rect.centerx) / dist
            dy = (npc.rect.centery - target.rect.centery) / dist
        else:
            dx, dy = 1.0, 0.0

        stand_x = target.rect.centerx + dx * COMBAT_FACE_DIST
        stand_y = target.rect.centery + dy * COMBAT_FACE_DIST

        # 弹开硬直中
        if npc.knockback_timer > 0:
            npc.state = STATE_COMBAT
            npc.ai_reason = "弹开中"
            return

        if dist > COMBAT_ATTACK_RANGE:
            # 追击
            npc.state = STATE_COMBAT
            npc.ai_reason = f"追击{target.name}"
            npc.set_movement_target(stand_x, stand_y, f"追击{target.name}")
            if not getattr(npc, 'combat_anchor_x', None):
                npc.combat_anchor_x = npc.rect.centerx
                npc.combat_anchor_y = npc.rect.centery
        else:
            # 到达攻击位置
            npc.state = STATE_COMBAT
            npc.clear_movement_target("决策树-到达战斗位置")
            npc.ai_reason = "战斗中"

            if not getattr(npc, 'combat_anchor_x', None):
                npc.combat_anchor_x = stand_x
                npc.combat_anchor_y = stand_y

            if npc.attack_cooldown <= 0:
                log_game_event(
                    f"[AI][READY] {npc.name}({npc.rect.centerx},{npc.rect.centery}) "
                    f"攻击就绪 → {target.name} dist={dist:.1f}", tag="AI"
                )
                all_npcs = self._current_npcs
                self.combat_manager.apply_melee_attack(npc, target, all_npcs)
                npc.attack_cooldown = npc.atk_speed
    
    def _on_combat_victory(self, npc, target):
        """战斗胜利处理"""
        self.broadcast_combat_end(npc, target)
        npc.aggro_target = None
        npc.combat_anchor_x = None
        npc.combat_anchor_y = None
        npc.in_combat = False
        npc.state = STATE_IDLE
        npc.clear_movement_target("对手倒地")
        npc.ai_reason = "对手倒地"
        log_game_event(
            f"[AI][VICTORY] {npc.name} 目标 {target.name} 已倒地，解除战斗",
            tag="AI"
        )
    
    # ══════════════════════════════════════════════════════════════
    # 战斗广播
    # ══════════════════════════════════════════════════════════════
    
    def broadcast_combat_start(self, attacker, defender, all_npcs=None):
        """
        战斗开始广播：通知范围内所有NPC
        """
        if getattr(attacker, 'in_combat', False):
            return  # 已广播过
        
        cx = (attacker.rect.centerx + defender.rect.centerx) // 2
        cy = (attacker.rect.centery + defender.rect.centery) // 2
        
        evt = {
            'type': 'COMBAT_START',
            'cx': cx, 'cy': cy,
            'source_ids': {attacker.id, defender.id},
            'combatant_names': f"{attacker.name} vs {defender.name}"
        }
        
        attacker.in_combat = True
        defender.in_combat = True
        
        if all_npcs:
            count = self._broadcast_to_range(evt, all_npcs)
            log_game_event(
                f"[BROADCAST] 战斗开始 {attacker.name} vs {defender.name} "
                f"中心=({cx},{cy}) 通知了{count}个围观者", tag="AI"
            )
        else:
            log_game_event(
                f"[BROADCAST] 战斗开始 {attacker.name} vs {defender.name} "
                f"中心=({cx},{cy}) 但无NPC列表，无法广播", tag="AI"
            )

    def broadcast_combat_end(self, winner, loser, all_npcs=None):
        """
        战斗结束广播：通知所有围观者散去
        """
        cx = (winner.rect.centerx + loser.rect.centerx) // 2
        cy = (winner.rect.centery + loser.rect.centery) // 2
        
        evt = {
            'type': 'COMBAT_END',
            'cx': cx, 'cy': cy,
            'source_ids': {winner.id, loser.id}
        }
        
        winner.in_combat = False
        
        # 注入战斗记忆
        self._inject_combat_memory(winner, loser, cx, cy, all_npcs)
        
        if all_npcs is None:
            all_npcs = self._current_npcs
        
        if all_npcs:
            count = self._broadcast_to_range(evt, all_npcs)
            log_game_event(
                f"[BROADCAST] 战斗结束 胜者={winner.name} "
                f"中心=({cx},{cy}) 通知了{count}个围观者散去", tag="AI"
            )
        else:
            log_game_event(
                f"[BROADCAST] 战斗结束 胜者={winner.name} "
                f"中心=({cx},{cy}) 但无NPC列表，无法广播", tag="AI"
            )
    
    def _inject_combat_memory(self, winner, loser, cx, cy, all_npcs):
        """将战斗结果注入NPC记忆系统"""
        try:
            from src.llm.event_memory_bridge import inject_combat_memory
            if loser.safety == SAFETY_DEAD:
                result = "被杀死了"
            elif loser.safety == SAFETY_DOWNED:
                result = "重伤倒地"
            else:
                result = "落败逃走"
            inject_combat_memory(winner, loser, result, all_npcs, (cx, cy))
        except Exception as e:
            log_game_event(f"[BROADCAST] 战斗记忆注入失败: {e}", tag="AI")
    
    def _broadcast_to_range(self, evt, all_npcs) -> int:
        """
        范围广播：向距离合适的NPC投递事件
        
        Returns:
            通知的NPC数量
        """
        cx, cy = evt['cx'], evt['cy']
        source_ids = evt.get('source_ids', set())
        count = 0
        
        for npc in all_npcs:
            if npc.job == 'PLAYER':
                continue
            if npc.id in source_ids:
                continue
            
            dist = math.hypot(npc.rect.centerx - cx, npc.rect.centery - cy)
            if dist > SPECTATE_NOTICE_RADIUS:
                continue
            
            self._ai.push_event(npc, evt)
            count += 1
        
        return count
