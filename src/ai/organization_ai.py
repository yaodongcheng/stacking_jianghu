# --- src/ai/organization_ai.py ---
"""
组织AI：处理NPC的组织行为（首领系统、集结、跟随）
从原ai_system.py抽离 _rally_npc, _broadcast_rally, _handle_rally_target
"""
import math
import random
import time
from src.definitions import STATE_MOVING, STATE_COMBAT
from src.utils import log_game_event
from src.ai.constants import RALLY_RADIUS, RALLY_COOLDOWN


class OrganizationAI:
    """
    组织行为模块
    
    包含功能：
    - 首领认定（_find_leader）
    - 集结广播（broadcast_rally）
    - 跟随首领移动（follow_leader）
    - 响应集结号召（handle_rally_target）
    """
    
    def __init__(self, ai_system):
        self._ai = ai_system
        self._rally_cooldown: dict = {}  # npc_id -> last_rally_time
    
    def find_leader(self, npc, all_npcs: list) -> object:
        """
        在同门派/组织中找到首领
        
        优先级：
        1. 帮派帮主
        2. 派内武力最高者
        
        Returns:
            首领NPC或None
        """
        my_gang = getattr(npc, 'gang', None)
        if not my_gang:
            return None
        
        candidates = [
            n for n in all_npcs
            if n is not npc
            and n.alive
            and getattr(n, 'gang', None) == my_gang
        ]
        
        if not candidates:
            return None
        
        # 帮主优先
        boss_candidates = [c for c in candidates if getattr(c, 'is_gang_boss', False)]
        if boss_candidates:
            return boss_candidates[0]
        
        # 否则取武力最高
        candidates.sort(key=lambda c: getattr(c, 'attack_power', 0), reverse=True)
        return candidates[0] if candidates else None
    
    def broadcast_rally(self, leader, target_x: float, target_y: float, 
                       all_npcs: list, reason: str = "集结"):
        """
        首领发起集结号召
        
        Args:
            leader: 发起集结的首领NPC
            target_x/y: 集结目标坐标
            all_npcs: 全体NPC列表
            reason: 集结原因
        """
        leader_id = getattr(leader, 'id', -1)
        now = time.time()
        
        # 集结冷却
        last_rally = self._rally_cooldown.get(leader_id, 0)
        if now - last_rally < RALLY_COOLDOWN:
            return
        self._rally_cooldown[leader_id] = now
        
        my_gang = getattr(leader, 'gang', None)
        lx, ly = leader.rect.centerx, leader.rect.centery
        
        rallied = 0
        for npc in all_npcs:
            if npc is leader or not npc.alive:
                continue
            if getattr(npc, 'gang', None) != my_gang:
                continue
            
            # 距离检测
            dx = npc.rect.centerx - lx
            dy = npc.rect.centery - ly
            if dx * dx + dy * dy > RALLY_RADIUS ** 2:
                continue
            
            # 战斗中不响应集结
            if npc.state == STATE_COMBAT:
                continue
            
            # 设置集结目标
            npc.rally_target_x = target_x
            npc.rally_target_y = target_y
            npc.rally_leader_id = leader_id
            npc.ai_reason = f"响应{leader.name}集结"
            rallied += 1
        
        if rallied > 0:
            log_game_event(f"[组织AI] {leader.name} 发起集结，{rallied}人响应")
    
    def handle_rally_target(self, npc) -> bool:
        """
        处理NPC的集结目标
        
        Returns:
            True - 接管了本帧决策
            False - 无集结任务
        """
        tx = getattr(npc, 'rally_target_x', None)
        ty = getattr(npc, 'rally_target_y', None)
        if tx is None:
            return False
        
        # 已到集结点
        dist = math.hypot(npc.rect.centerx - tx, npc.rect.centery - ty)
        if dist < 50:
            npc.rally_target_x = None
            npc.rally_target_y = None
            npc.rally_leader_id = None
            npc.ai_reason = "已到集结点"
            return False  # 到达后释放决策权
        
        # 前往集结点
        npc.state = STATE_MOVING
        npc.set_movement_target(tx, ty, "前往集结点")
        return True
    
    def follow_leader(self, npc, leader) -> bool:
        """
        跟随首领移动
        
        保持20-60px距离，不贴身
        
        Returns:
            True - 接管了本帧决策
            False - 无需跟随
        """
        if not leader or not leader.alive:
            return False
        
        lx, ly = leader.rect.centerx, leader.rect.centery
        nx, ny = npc.rect.centerx, npc.rect.centery
        dist = math.hypot(lx - nx, ly - ny)
        
        # 太近，无需移动
        if dist < 60:
            return False
        
        # 太远，需要跟上
        if dist > 200:
            # 计算跟随位置（首领后方随机偏移）
            angle = math.atan2(ny - ly, nx - lx)
            follow_dist = random.uniform(40, 80)
            tx = lx + math.cos(angle) * follow_dist
            ty = ly + math.sin(angle) * follow_dist
            
            npc.state = STATE_MOVING
            npc.set_movement_target(tx, ty, "跟随首领")
            npc.ai_reason = f"跟随{leader.name}"
            return True
        
        return False
    
    def disband_rally(self, leader_id: int, all_npcs: list):
        """
        解散集结
        
        Args:
            leader_id: 首领ID
            all_npcs: 全体NPC列表
        """
        for npc in all_npcs:
            if getattr(npc, 'rally_leader_id', None) == leader_id:
                npc.rally_target_x = None
                npc.rally_target_y = None
                npc.rally_leader_id = None
