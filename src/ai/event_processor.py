# --- src/ai/event_processor.py ---
"""
事件处理器：处理突发事件和视觉感知
从原ai_system.py抽离 _process_events 和 _process_see
"""
import math
import time
import pygame
from src.definitions import (
    SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED,
    STATE_COMBAT, STATE_MOVING, STATE_IDLE, STATE_EVENT
)
from src.utils import log_game_event
from src.ai.constants import (
    SEE_RADIUS, HOSTILE_JOBS,
    HATE_COOLDOWN_MS, ALLY_HATE_COOLDOWN_MS, INTERCEPT_COOLDOWN_SEC, INTERCEPT_RANGE
)


class EventProcessor:
    """
    事件/感知处理器
    
    职责：
    1. 处理突发事件队列（COMBAT_START/END等）
    2. 视觉感知：扫描周围情况并决定反应
    
    设计原则：
    - 事件处理每帧执行，不受decision_timer节流
    - 视觉感知仅在决策前执行，发现敌人可打断当前行为
    """
    
    def __init__(self, ai_system):
        """
        Args:
            ai_system: 父AISystem引用，用于访问 _is_villain, _find_bodyguard_leader 等
        """
        self._ai = ai_system
        self._guard_intercept_cooldowns = {}  # 拦截冷却记录
    
    # ══════════════════════════════════════════════════════════════
    # 突发事件处理（每帧无条件执行）
    # ══════════════════════════════════════════════════════════════
    
    def process_events(self, npc, world_map) -> bool:
        """
        消费 npc._event_queue 中的所有事件，立即应用状态变更。
        
        Returns:
            True  → 本帧有突发事件被处理，主动决策树应跳过
            False → 无突发事件，正常走 decision_timer 节流
        """
        queue = getattr(npc, '_event_queue', None)
        if not queue:
            return False
        
        # 重伤、死亡等状态的 NPC 不处理事件
        if npc.safety in (SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED):
            npc._event_queue = []
            return False

        interrupted = False

        for evt in queue:
            etype = evt.get('type')

            # ── COMBAT_START：开始围观 ──────────────────────────
            if etype == 'COMBAT_START':
                interrupted = self._handle_combat_start_event(npc, evt)

            # ── COMBAT_END：散去 ────────────────────────────────
            elif etype == 'COMBAT_END':
                interrupted = self._handle_combat_end_event(npc, evt, world_map) or interrupted

        npc._event_queue = []  # 消费完毕，清空队列
        return interrupted
    
    def _handle_combat_start_event(self, npc, evt) -> bool:
        """处理战斗开始事件"""
        # 当事人不围观
        if npc.id in evt.get('source_ids', set()):
            return False
        
        ecx, ecy = evt['cx'], evt['cy']
        already = getattr(npc, 'spectate_src_x', None) is not None
        npc.spectate_src_x = ecx
        npc.spectate_src_y = ecy
        
        if not already:
            combatants = evt.get('combatant_names', '未知 vs 未知')
            log_game_event(
                f"[EVENT] {npc.name} 收到COMBAT_START → 围观({ecx},{ecy}) "
                f"战斗双方=[{combatants}]", tag="AI"
            )
        return True  # 打断主动决策，让围观逻辑接管
    
    def _handle_combat_end_event(self, npc, evt, world_map) -> bool:
        """处理战斗结束事件"""
        if getattr(npc, 'spectate_src_x', None) is None:
            return False  # 没在围观，忽略
        
        log_game_event(f"[EVENT] {npc.name} 收到COMBAT_END → 立即散去", tag="AI")
        npc.spectate_anchor_set = False
        npc.spectate_src_x = None
        npc.spectate_src_y = None
        npc.action_queue.clear()
        
        if world_map:
            tx, ty = world_map.get_random_pos_in_rect(world_map.city_rect)
            npc.set_movement_target(tx, ty, "围观结束-散去离开")
            npc.state = STATE_MOVING
            npc.ai_reason = "散去离开"
        else:
            npc.state = STATE_IDLE
            npc.ai_reason = "散去(原地)"
        
        return True

    # ══════════════════════════════════════════════════════════════
    # 视觉感知系统
    # ══════════════════════════════════════════════════════════════
    
    def process_see(self, npc, all_npcs) -> bool:
        """
        视觉感知处理：NPC 主动扫描视野内的情况。
        
        Returns:
            True  → 发现需要立即反应的事件（如敌人），应打断当前行为
            False → 没有需要反应的事，继续原行为
        """
        # 前置条件检查
        if getattr(npc, 'aggro_target', None) is not None:
            return False
        if npc.state == STATE_COMBAT:
            return False
        if npc.safety in (SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED):
            return False
        
        my_is_villain = self._ai._is_villain(npc)
        my_is_guard = npc.job in ('GUARD', 'OFFICIAL', 'SOLDIER')
        
        mx, my = npc.rect.centerx, npc.rect.centery
        
        # 性能优化：预先过滤有效目标
        # 【优化点1】使用列表推导式替代循环，减少属性访问
        valid_others = [
            o for o in all_npcs
            if o != npc
            and o.safety not in (SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED)
        ]
        
        for other in valid_others:
            dist = math.hypot(mx - other.rect.centerx, my - other.rect.centery)
            if dist > SEE_RADIUS:
                continue
            
            # 情况1-4 的处理逻辑
            result = self._check_see_situation(
                npc, other, all_npcs, 
                my_is_villain, my_is_guard
            )
            if result:
                return True
        
        return False
    
    def _check_see_situation(self, npc, other, all_npcs, 
                              my_is_villain, my_is_guard) -> bool:
        """
        检查各种视觉感知情况
        返回 True 表示发现需要立即反应的情况
        """
        other_is_villain = self._ai._is_villain(other)
        other_is_fighting = getattr(other, 'in_combat', False)
        
        current_time = pygame.time.get_ticks()
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 情况1: 守卫/官差 看到 山贼/泼皮正在作恶 → 产生仇恨
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if my_is_guard and other_is_villain:
            is_doing_evil = other_is_fighting or getattr(other, 'is_robbing', False)
            if is_doing_evil:
                if self._apply_hate_with_cooldown(npc, other.id, 30, current_time, HATE_COOLDOWN_MS):
                    log_game_event(
                        f"[SEE] {npc.name}({npc.job}) 看到山贼 {other.name} 正在作恶 "
                        f"→ 仇恨 +30 = {npc.hatred[other.id]}", tag="SEE_AGGRO"
                    )
                    if self._check_and_lock_target(npc, other, f"制止山贼{other.name}"):
                        return True
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 情况2: 守卫 看到 恶人正在攻击平民 → 仇恨攻击者
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if my_is_guard and not my_is_villain:
            other_victim = getattr(other, 'aggro_target', None)
            if other_is_villain and other_is_fighting and other_victim:
                victim_is_innocent = not self._ai._is_villain(other_victim)
                if victim_is_innocent:
                    npc.hatred[other.id] = npc.hatred.get(other.id, 0) + 50
                    log_game_event(
                        f"[SEE] {npc.name} 看到 {other.name} 正在攻击无辜的 {other_victim.name} "
                        f"→ 仇恨攻击者 +50", tag="SEE_AGGRO"
                    )
                    if self._check_and_lock_target(npc, other, f"路见不平，救{other_victim.name}"):
                        return True
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 情况3: 同组织成员被攻击 → 仇恨攻击者
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if self._check_ally_under_attack(npc, other, all_npcs, current_time):
            return True
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 情况3.5: 跟随者协助主人
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if self._check_follower_assist(npc, other, all_npcs):
            return True
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 情况4: 护卫拦截低阶层接近被保护者
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if self._check_bodyguard_intercept(npc, other, all_npcs):
            return True
        
        return False
    
    def _apply_hate_with_cooldown(self, npc, target_id, hate_amount, 
                                   current_time, cooldown_ms) -> bool:
        """
        带冷却的仇恨累加
        
        Returns:
            True - 成功累加仇恨
            False - 在冷却中，跳过
        """
        if not hasattr(npc, '_hate_cooldown'):
            npc._hate_cooldown = {}
        
        last_hate_time = npc._hate_cooldown.get(target_id, 0)
        if current_time - last_hate_time <= cooldown_ms:
            return False
        
        npc._hate_cooldown[target_id] = current_time
        npc.hatred[target_id] = npc.hatred.get(target_id, 0) + hate_amount
        return True
    
    def _check_and_lock_target(self, npc, target, reason) -> bool:
        """
        检查仇恨是否超过阈值，如果是则锁定目标
        
        Returns:
            True - 已锁定目标并进入战斗
            False - 仇恨不足
        """
        if npc.hatred.get(target.id, 0) >= npc.aggro_threshold:
            npc.aggro_target = target
            npc.state = STATE_COMBAT
            npc.ai_reason = reason
            npc.action_queue.clear()
            return True
        return False
    
    def _check_ally_under_attack(self, npc, other, all_npcs, current_time) -> bool:
        """检查同组织成员是否被攻击"""
        # 找到正在攻击 other 的人
        attacker_of_other = None
        for potential_atk in all_npcs:
            if getattr(potential_atk, 'aggro_target', None) == other:
                attacker_of_other = potential_atk
                break
        
        if not attacker_of_other or attacker_of_other == npc:
            return False
        
        my_org = getattr(npc, 'org_id', None)
        other_org = getattr(other, 'org_id', None)
        attacker_org = getattr(attacker_of_other, 'org_id', None)
        
        if my_org and my_org == other_org and my_org != attacker_org:
            if self._apply_hate_with_cooldown(
                npc, attacker_of_other.id, 40, current_time, ALLY_HATE_COOLDOWN_MS
            ):
                log_game_event(
                    f"[SEE] {npc.name} 看到同门 {other.name} 正在被 {attacker_of_other.name} 攻击 "
                    f"→ 仇恨攻击者 +40", tag="SEE_AGGRO"
                )
                if self._check_and_lock_target(npc, attacker_of_other, f"救援同门{other.name}"):
                    return True
        return False
    
    def _check_follower_assist(self, npc, other, all_npcs) -> bool:
        """检查跟随者是否需要协助主人"""
        if not getattr(npc, 'is_follower', False) or npc.ai_mode != "FOLLOW":
            return False
        if other.job != 'PLAYER':
            return False
        
        # 场景A: 有人在攻击主人 → 保护主人
        for potential_atk in all_npcs:
            if potential_atk == npc:
                continue
            if getattr(potential_atk, 'aggro_target', None) == other:
                npc.hatred[potential_atk.id] = 100
                npc.aggro_target = potential_atk
                npc.state = STATE_COMBAT
                npc.ai_reason = f"保护主人，对抗{potential_atk.name}"
                npc.action_queue.clear()
                log_game_event(
                    f"[SEE] 跟随者 {npc.name} 发现主人被 {potential_atk.name} 攻击 "
                    f"→ 加入战斗保护主人", tag="SEE_AGGRO"
                )
                return True
        
        # 场景B: 主人在攻击别人 → 协助主人
        player_target = getattr(other, 'aggro_target', None)
        if player_target and player_target != npc:
            if player_target.safety not in (SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED):
                npc.hatred[player_target.id] = 80
                npc.aggro_target = player_target
                npc.state = STATE_COMBAT
                npc.ai_reason = f"协助主人攻击{player_target.name}"
                npc.action_queue.clear()
                log_game_event(
                    f"[SEE] 跟随者 {npc.name} 发现主人在攻击 {player_target.name} "
                    f"→ 协助攻击", tag="SEE_AGGRO"
                )
                return True
        
        return False
    
    def _check_bodyguard_intercept(self, npc, other, all_npcs) -> bool:
        """检查护卫是否需要拦截接近的低阶层人物"""
        my_org_role = getattr(npc, 'org_role', None)
        if my_org_role != 'BODYGUARD' or other.job != 'PLAYER':
            return False
        
        leader = self._ai._find_bodyguard_leader(npc, all_npcs)
        if not leader:
            return False
        
        leader_level = getattr(leader, 'social_level', 1)
        player_level = getattr(other, 'social_level', 1)
        
        if leader_level < 3 or player_level >= leader_level - 1:
            return False
        
        # 检查玩家到领导者的距离
        player_dist_to_leader = math.hypot(
            other.rect.centerx - leader.rect.centerx,
            other.rect.centery - leader.rect.centery
        )
        
        if player_dist_to_leader >= INTERCEPT_RANGE:
            return False
        
        # 检查拦截冷却
        current_time = time.time()
        cooldown_key = f"intercept_{leader.id}"
        last_intercept = self._guard_intercept_cooldowns.get(cooldown_key, 0)
        
        if current_time - last_intercept < INTERCEPT_COOLDOWN_SEC:
            return False
        
        # 更新冷却并设置拦截状态
        self._guard_intercept_cooldowns[cooldown_key] = current_time
        npc.intercept_target = other
        npc.intercept_leader = leader
        npc.state = STATE_EVENT
        npc.action_queue.clear()
        npc.ai_reason = "盘问可疑人员"
        
        # 标记玩家被拦截
        other._intercepted_by = npc
        other._intercept_leader = leader
        
        log_game_event(
            f"[SEE] [卫] {npc.name}(护卫) 拦截 {other.name} 靠近 {leader.name} "
            f"(玩家等级{player_level} < 领导等级{leader_level})", tag="SEE_AGGRO"
        )
        return True