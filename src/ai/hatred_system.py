# --- src/ai/hatred_system.py ---
"""
仇恨系统模块 - 汴京沙盒

职责：
1. 仇恨值计算与衰减
2. 索敌逻辑（_find_enemy）
3. 组织联动仇恨（_propagate_org_hatred）
4. 视觉感知（_process_see）

设计原则：
- 仇恨系统独立于AI行为系统
- 仇恨值只决定"要不要打"，不决定"怎么打"
- 与原子行为系统解耦，通过 aggro_target 属性传递战斗目标
"""

import math
import pygame
from typing import Optional, List, TYPE_CHECKING

from src.definitions import (
    SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED,
    STATE_COMBAT, STATE_IDLE, STATE_MOVING
)
from src.utils import log_game_event

if TYPE_CHECKING:
    from src.entities import NPC


class HatredSystem:
    """
    仇恨系统
    
    管理NPC之间的仇恨关系，决定谁是敌人。
    仇恨值超过阈值（aggro_threshold）时，NPC会锁定目标（aggro_target）。
    """
    
    # 阵营定义
    HOSTILE_JOBS = {'BANDIT', 'THUG'}           # 主动攻击方（山贼/泼皮）
    GUARD_JOBS = {'GUARD', 'OFFICIAL', 'SOLDIER'}  # 执法方（守卫/官差/士兵）
    
    def __init__(self, scan_radius: int = 400, see_radius: int = 250):
        """
        Args:
            scan_radius: 索敌范围（像素）
            see_radius: 视觉感知范围（像素）
        """
        self.scan_radius = scan_radius
        self.see_radius = see_radius
        
        # 外部系统引用（可选）
        self._faction_war_ref = None
        self._world_map_ref = None
    
    def set_faction_war(self, faction_war):
        """设置势力战争系统引用（用于悬赏系统）"""
        self._faction_war_ref = faction_war
    
    def set_world_map(self, world_map):
        """设置世界地图引用（用于城内/城外判断）"""
        self._world_map_ref = world_map
    
    # ═══════════════════════════════════════════════════════════════════
    # 核心接口
    # ═══════════════════════════════════════════════════════════════════
    
    def is_villain(self, npc: 'NPC') -> bool:
        """判断是否是反派阵营（山贼/泼皮）"""
        return getattr(npc, 'job', '') in self.HOSTILE_JOBS
    
    def is_guard(self, npc: 'NPC') -> bool:
        """判断是否是执法方（守卫/官差/士兵）"""
        return getattr(npc, 'job', '') in self.GUARD_JOBS
    
    def add_hatred(self, npc: 'NPC', target_id: int, amount: int):
        """
        增加仇恨值
        
        Args:
            npc: 仇恨的持有者
            target_id: 仇恨目标的ID
            amount: 仇恨增量
        """
        if not hasattr(npc, 'hatred'):
            npc.hatred = {}
        npc.hatred[target_id] = npc.hatred.get(target_id, 0) + amount
    
    def get_hatred(self, npc: 'NPC', target_id: int) -> int:
        """获取仇恨值"""
        return getattr(npc, 'hatred', {}).get(target_id, 0)
    
    def clear_hatred(self, npc: 'NPC', target_id: int):
        """清除仇恨"""
        if hasattr(npc, 'hatred') and target_id in npc.hatred:
            del npc.hatred[target_id]
    
    def lock_target(self, npc: 'NPC', target: 'NPC'):
        """锁定战斗目标"""
        npc.aggro_target = target
        # 同时设置最低仇恨阈值
        self.add_hatred(npc, target.id, max(0, npc.aggro_threshold - self.get_hatred(npc, target.id)))
    
    def unlock_target(self, npc: 'NPC'):
        """解锁战斗目标"""
        npc.aggro_target = None
        npc.combat_anchor_x = None
        npc.combat_anchor_y = None
    
    # ═══════════════════════════════════════════════════════════════════
    # 索敌逻辑
    # ═══════════════════════════════════════════════════════════════════
    
    def find_enemy(self, me: 'NPC', all_npcs: List['NPC']) -> Optional['NPC']:
        """
        仇恨系统索敌逻辑：
        1. 优先返回已锁定的 aggro_target（目标有效则直接追击）
        2. 否则扫描范围内所有潜在敌人，更新仇恨表
        3. 返回仇恨最高且超过阈值的目标
        4. 仇恨相同时按"就近+财富"打分排序
        
        Returns:
            锁定的敌人，或None
        """
        my_is_villain = self.is_villain(me)
        
        # 获取玩家引用
        player = next((x for x in all_npcs if getattr(x, 'job', '') == 'PLAYER'), None)
        
        # --- 步骤1：已锁定目标则直接复用 ---
        if me.aggro_target is not None:
            t = me.aggro_target
            # 验证目标依然有效
            if t.safety not in [SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED]:
                dist = math.hypot(me.rect.centerx - t.rect.centerx, 
                                 me.rect.centery - t.rect.centery)
                if dist <= self.scan_radius * 1.5:
                    return t
            # 目标无效，解锁
            self.unlock_target(me)
        
        # --- 步骤2：全量扫描范围内的潜在敌人 ---
        candidates = []  # [(npc, hate_value, score)]
        
        # 获取城区范围
        world_map = self._world_map_ref or getattr(me, '_world_map_ref', None)
        city_rect = world_map.city_rect if world_map else None
        my_is_guard = self.is_guard(me)
        
        for other in all_npcs:
            if other == me:
                continue
            if other.safety in [SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED]:
                continue
            
            dist = math.hypot(me.rect.centerx - other.rect.centerx,
                             me.rect.centery - other.rect.centery)
            if dist > self.scan_radius:
                continue
            
            other_is_villain = self.is_villain(other)
            
            # 判断是否潜在敌对方
            is_potential_enemy = False
            if my_is_villain and not other_is_villain:
                is_potential_enemy = True
            elif not my_is_villain and other_is_villain:
                is_potential_enemy = True
            
            if not is_potential_enemy:
                continue
            
            # 守卫不主动追击城外山贼
            if my_is_guard and city_rect and other_is_villain:
                other_in_city = city_rect.collidepoint(other.rect.centerx, other.rect.centery)
                if not other_in_city:
                    if me.id not in getattr(other, 'hatred', {}):
                        continue
            
            # 山贼被动仇恨逻辑（城外对城外）
            if my_is_villain and city_rect:
                me_in_city = city_rect.collidepoint(me.rect.centerx, me.rect.centery)
                other_in_city = city_rect.collidepoint(other.rect.centerx, other.rect.centery)
                
                if not me_in_city and not other_in_city:
                    # 双方都在城外 → 山贼主动施加仇恨
                    self._apply_passive_hatred(me, other)
            
            # 悬赏系统：黑风寨成员对被悬赏玩家施加仇恨
            if player and other == player and self._faction_war_ref:
                self._apply_bounty_hatred(me, player)
            
            current_hate = self.get_hatred(me, other.id)
            
            # 计算优先级打分：就近+财富
            dist_score = max(0, self.scan_radius - dist)
            wealth = other.inventory.get('铜钱', 0) if hasattr(other, 'inventory') else 0
            wealth_score = min(wealth * 0.5, 50)
            tie_score = dist_score + wealth_score
            
            candidates.append((other, current_hate, tie_score))
        
        if not candidates:
            return None
        
        # --- 步骤3：找仇恨最高且超过阈值的目标 ---
        candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
        best_npc, best_hate, _ = candidates[0]
        
        if best_hate >= me.aggro_threshold:
            self.lock_target(me, best_npc)
            return best_npc
        
        return None
    
    def _apply_passive_hatred(self, me: 'NPC', other: 'NPC'):
        """山贼对城外好人施加被动仇恨"""
        if not hasattr(me, '_passive_hate_cd'):
            me._passive_hate_cd = {}
        
        current_time = pygame.time.get_ticks()
        last_hate_time = me._passive_hate_cd.get(other.id, 0)
        
        if current_time - last_hate_time > 5000:  # 5秒冷却
            me._passive_hate_cd[other.id] = current_time
            self.add_hatred(me, other.id, 8)
    
    def _apply_bounty_hatred(self, me: 'NPC', player: 'NPC'):
        """悬赏系统：山贼对被悬赏玩家施加仇恨"""
        me_org = getattr(me, 'org_id', '')
        if me_org != 'heifeng_zhai' and me.job not in self.HOSTILE_JOBS:
            return
        
        total_bounty, bounties = self._faction_war_ref.get_bounty_on_player(player)
        for bounty in bounties:
            if bounty.get('issuer_org') == 'heifeng_zhai' and bounty.get('active', True):
                self.add_hatred(me, player.id, 50)
                break
    
    # ═══════════════════════════════════════════════════════════════════
    # 视觉感知
    # ═══════════════════════════════════════════════════════════════════
    
    def process_see(self, npc: 'NPC', all_npcs: List['NPC']) -> bool:
        """
        视觉感知处理：NPC主动扫描视野内的情况
        
        Returns:
            True - 发现需要立即反应的事件，应打断当前行为
            False - 没有需要反应的事
        """
        # 已有锁定目标或正在战斗中，不需要感知
        if getattr(npc, 'aggro_target', None) is not None:
            return False
        if npc.state == STATE_COMBAT:
            return False
        if npc.safety in [SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED]:
            return False
        
        my_is_villain = self.is_villain(npc)
        my_is_guard = self.is_guard(npc)
        my_is_heroic = getattr(npc, 'morality', 50) >= 70
        
        mx, my = npc.rect.centerx, npc.rect.centery
        
        for other in all_npcs:
            if other == npc:
                continue
            if other.safety in [SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED]:
                continue
            
            dist = math.hypot(mx - other.rect.centerx, my - other.rect.centery)
            if dist > self.see_radius:
                continue
            
            other_is_villain = self.is_villain(other)
            other_is_fighting = getattr(other, 'in_combat', False)
            other_victim = getattr(other, 'aggro_target', None)
            
            # 情况1: 守卫看到山贼正在作恶
            if my_is_guard and other_is_villain:
                is_doing_evil = other_is_fighting or getattr(other, 'is_robbing', False)
                if is_doing_evil:
                    if self._apply_see_hatred_with_cooldown(npc, other, 30):
                        return True
            
            # 情况2: 善良的人看到恶人攻击平民
            if my_is_heroic and other_is_villain:
                if other_victim and not self.is_villain(other_victim):
                    if self._apply_see_hatred_with_cooldown(npc, other, 50):
                        return True
            
            # 情况3: 同组织成员被攻击
            my_org = getattr(npc, 'org_id', None)
            other_org = getattr(other, 'org_id', None)
            if my_org and my_org == other_org and my_org != 'NONE':
                attacker = self._find_attacker_of(other, all_npcs)
                if attacker and attacker != npc:
                    if self._apply_see_hatred_with_cooldown(npc, attacker, 40):
                        return True
        
        return False
    
    def _apply_see_hatred_with_cooldown(self, npc: 'NPC', target: 'NPC', amount: int) -> bool:
        """带冷却的视觉仇恨累加"""
        if not hasattr(npc, '_hate_cooldown'):
            npc._hate_cooldown = {}
        
        current_time = pygame.time.get_ticks()
        last_time = npc._hate_cooldown.get(target.id, 0)
        
        if current_time - last_time > 3000:  # 3秒冷却
            npc._hate_cooldown[target.id] = current_time
            self.add_hatred(npc, target.id, amount)
            
            log_game_event(
                f"[SEE_AGGRO] {npc.name} 看到 {target.name} 作恶 → 仇恨+{amount}",
                tag="SEE_AGGRO"
            )
            
            # 如果仇恨超过阈值，锁定目标
            if self.get_hatred(npc, target.id) >= npc.aggro_threshold:
                self.lock_target(npc, target)
                return True
        
        return False
    
    def _find_attacker_of(self, victim: 'NPC', all_npcs: List['NPC']) -> Optional['NPC']:
        """查找正在攻击victim的NPC"""
        for npc in all_npcs:
            if getattr(npc, 'aggro_target', None) == victim:
                return npc
        return None
    
    # ═══════════════════════════════════════════════════════════════════
    # 组织联动仇恨
    # ═══════════════════════════════════════════════════════════════════
    
    def propagate_org_hatred(self, attacker: 'NPC', victim: 'NPC', 
                             dmg: int, all_npcs: List['NPC']):
        """
        组织联动仇恨机制：
        当victim被攻击时，周围同组织成员会对attacker产生仇恨
        
        Args:
            attacker: 攻击者
            victim: 受害者
            dmg: 伤害量
            all_npcs: 所有NPC列表
        """
        victim_org = getattr(victim, 'org_id', None)
        if not victim_org or victim_org == 'NONE':
            return
        
        # 传播范围
        org_range = {
            'kaifeng_fu': 400,
            'shenhou_fu': 350,
            'gao_manor': 300,
            'beggar_gang': 250,
            'shizizhipo': 200,
            'tianshui_alley': 150,
            'taixue': 150,
            'daxiangguo': 200,
        }
        propagate_range = org_range.get(victim_org, 200)
        
        propagated_count = 0
        for npc in all_npcs:
            if npc == victim or npc == attacker:
                continue
            
            npc_org = getattr(npc, 'org_id', None)
            if npc_org != victim_org:
                continue
            
            if npc.safety in [SAFETY_DEAD, SAFETY_DOWNED]:
                continue
            
            dist = math.hypot(npc.rect.centerx - victim.rect.centerx,
                             npc.rect.centery - victim.rect.centery)
            if dist > propagate_range:
                continue
            
            # 计算仇恨值
            distance_factor = 1.0 - (dist / propagate_range) * 0.3
            npc_rank = getattr(npc, 'org_rank', 0)
            rank_factor = 1.0 + npc_rank * 0.3
            role_factor = 2.0 if npc.job in self.GUARD_JOBS else 1.2
            hostile_factor = 2.0 if self.is_villain(attacker) else 1.0
            
            hate_gain = int(dmg * distance_factor * rank_factor * role_factor * hostile_factor)
            hate_gain = max(15, hate_gain)
            
            # 护卫职业仇恨拉满
            if npc.job in self.GUARD_JOBS:
                hate_gain = max(hate_gain, npc.aggro_threshold + 5)
            
            self.add_hatred(npc, attacker.id, hate_gain)
            
            # 如果仇恨超过阈值，锁定目标
            if npc.aggro_target is None and self.get_hatred(npc, attacker.id) >= npc.aggro_threshold:
                self.lock_target(npc, attacker)
                npc.state = STATE_COMBAT
                npc.in_combat = True
                
                log_game_event(
                    f"[ORG_AGGRO] {npc.name}({victim_org}) 因同伴{victim.name}被打 "
                    f"→ 锁定{attacker.name}  仇恨={self.get_hatred(npc, attacker.id)}",
                    tag="ORG_AGGRO"
                )
            
            propagated_count += 1
        
        if propagated_count > 0:
            log_game_event(
                f"[ORG_HATRED] {victim.name}被攻击 → {victim_org}组织{propagated_count}人产生仇恨",
                tag="ORG_AGGRO"
            )


# 全局单例
_hatred_system: Optional[HatredSystem] = None

def get_hatred_system() -> HatredSystem:
    """获取仇恨系统单例"""
    global _hatred_system
    if _hatred_system is None:
        _hatred_system = HatredSystem()
    return _hatred_system
