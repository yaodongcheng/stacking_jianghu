# --- src/ai/job_behaviors/base.py ---
"""
职业行为基类
提供所有职业共享的基础行为
"""
import math
import random
from abc import ABC, abstractmethod
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from src.entities import NPC, Building


class BaseJobBehavior(ABC):
    """
    职业行为基类
    
    子类需实现：
    - execute(npc, context) -> bool
    
    设计原则：
    - 所有具体行为都是原子行为的组合
    - 通过 action_queue.enqueue() 入队原子行为
    - 不直接修改 NPC 状态，让原子行为处理
    """
    
    # 类级别的默认配置
    DECISION_COOLDOWN_MS = 3000
    ROAM_DURATION_MS = 5000
    WAIT_DURATION_MS = 3000
    
    def __init__(self, ai_system=None):
        self._ai = ai_system
        self._hatred_system = None
    
    @abstractmethod
    def execute(self, npc: 'NPC', context: dict) -> bool:
        """
        执行职业行为
        
        Args:
            npc: 目标NPC
            context: 上下文字典，包含：
                - all_npcs: 所有NPC列表
                - all_buildings: 所有建筑列表
                - world_map: 世界地图引用
                - dt_ms: 帧间隔毫秒
                - combat_manager: 战斗管理器
        
        Returns:
            True - 成功入队行为
            False - 无行为
        """
        pass
    
    # ─── 仇恨系统集成 ───────────────────────────────────────────
    
    def get_hatred_system(self):
        """获取仇恨系统引用"""
        if self._hatred_system is None:
            from src.ai.hatred_system import get_hatred_system
            self._hatred_system = get_hatred_system()
        return self._hatred_system
    
    def find_enemy(self, npc: 'NPC', all_npcs: List['NPC']) -> Optional['NPC']:
        """通过仇恨系统寻找敌人"""
        return self.get_hatred_system().find_enemy(npc, all_npcs)
    
    def is_villain(self, npc: 'NPC') -> bool:
        """判断是否是反派"""
        return self.get_hatred_system().is_villain(npc)
    
    def is_guard(self, npc: 'NPC') -> bool:
        """判断是否是执法者"""
        return self.get_hatred_system().is_guard(npc)
    
    # ─── 原子行为入队快捷方法 ─────────────────────────────────────
    
    def has_pending_action(self, npc: 'NPC') -> bool:
        """检查NPC是否有未完成的行为"""
        return not npc.action_queue.is_empty()
    
    def clear_actions(self, npc: 'NPC'):
        """清空行为队列"""
        npc.action_queue.clear()
    
    def enqueue_roam(self, npc: 'NPC', area_rect, duration_ms: int = None, reason: str = "闲逛"):
        """入队闲逛行为"""
        from src.atomic_actions import Roam
        if duration_ms is None:
            duration_ms = self.ROAM_DURATION_MS
        npc.action_queue.enqueue(Roam(area_rect, duration_ms=duration_ms, reason=reason))
    
    def enqueue_wait(self, npc: 'NPC', duration_ms: int = None, reason: str = "等待"):
        """入队等待行为"""
        from src.atomic_actions import Wait
        if duration_ms is None:
            duration_ms = self.WAIT_DURATION_MS
        npc.action_queue.enqueue(Wait(duration_ms, reason=reason))
    
    def enqueue_move_to_building(self, npc: 'NPC', building: 'Building', reason: str = "前往"):
        """入队移动到建筑"""
        from src.atomic_actions import MoveToBuilding
        npc.action_queue.enqueue(MoveToBuilding(building, reason=reason))
    
    def enqueue_move_to_position(self, npc: 'NPC', x: float, y: float, 
                                  stop_dist: int = 30, reason: str = "移动",
                                  state_override=None):
        """入队移动到位置"""
        from src.atomic_actions import MoveToPosition
        npc.action_queue.enqueue(MoveToPosition(
            x, y, stop_dist=stop_dist, reason=reason,
            state_override=state_override
        ))
    
    def enqueue_combat(self, npc: 'NPC', target: 'NPC', combat_manager, reason: str = "战斗"):
        """入队战斗行为"""
        from src.atomic_actions import Combat
        npc.action_queue.enqueue(Combat(target, combat_manager, reason=reason))
    
    def enqueue_follow(self, npc: 'NPC', target: 'NPC', stop_dist: int = 60, 
                       start_dist: int = 90, keep_follow: bool = True, reason: str = "跟随"):
        """入队跟随行为"""
        from src.atomic_actions import FollowTarget
        npc.action_queue.enqueue(FollowTarget(
            target, stop_dist=stop_dist, start_dist=start_dist,
            keep_follow=keep_follow, reason=reason
        ))
    
    def enqueue_patrol(self, npc: 'NPC', waypoints: list, loop: bool = True, reason: str = "巡逻"):
        """入队巡逻行为"""
        from src.atomic_actions import Patrol
        npc.action_queue.enqueue(Patrol(waypoints, loop=loop, reason=reason))
    
    def enqueue_work(self, npc: 'NPC', building: 'Building', duration_ms: int = 5000,
                     produce_item: str = None, produce_amount: int = 1, reason: str = "工作"):
        """入队工作行为"""
        from src.atomic_actions import Work
        npc.action_queue.enqueue(Work(
            building, duration_ms=duration_ms,
            produce_item=produce_item, produce_amount=produce_amount,
            reason=reason
        ))
    
    def enqueue_trade(self, npc: 'NPC', target, sell_item: str = None, 
                      sell_amount: int = 0, reason: str = "交易"):
        """入队交易行为"""
        from src.atomic_actions import Trade
        npc.action_queue.enqueue(Trade(
            target, sell_item=sell_item, sell_amount=sell_amount,
            reason=reason
        ))
    
    def enqueue_flee(self, npc: 'NPC', threat: 'NPC', flee_distance: int = 300, reason: str = "逃跑"):
        """入队逃跑行为"""
        from src.atomic_actions import Flee
        npc.action_queue.enqueue(Flee(threat, flee_distance=flee_distance, reason=reason))
    
    def enqueue_spectate(self, npc: 'NPC', cx: float, cy: float, reason: str = "围观"):
        """入队围观行为"""
        from src.atomic_actions import Spectate
        npc.action_queue.enqueue(Spectate(cx, cy, npc.id, reason=reason))
    
    def enqueue_rescue(self, npc: 'NPC', patient: 'NPC', clinic: 'Building', reason: str = "救援"):
        """入队救援行为"""
        from src.atomic_actions import Rescue
        npc.action_queue.enqueue(Rescue(patient, clinic, reason=reason))
    
    def enqueue_say(self, npc: 'NPC', text: str, duration_ms: int = 2000, reason: str = "说话"):
        """入队说话行为"""
        from src.atomic_actions import Say
        npc.action_queue.enqueue(Say(text, duration_ms=duration_ms, reason=reason))
    
    def enqueue_look_at(self, npc: 'NPC', target: 'NPC', duration_ms: int = 500, reason: str = "看向"):
        """入队看向行为"""
        from src.atomic_actions import LookAt
        npc.action_queue.enqueue(LookAt(target, duration_ms=duration_ms, reason=reason))
    
    def enqueue_rally(self, npc: 'NPC', x: float, y: float, duration_ms: int = 10000, reason: str = "集结"):
        """入队集结行为"""
        from src.atomic_actions import Rally
        npc.action_queue.enqueue(Rally(x, y, duration_ms=duration_ms, reason=reason))
    
    # ─── 建筑查找 ───────────────────────────────────────────────
    
    def find_building_by_type(self, buildings: list, btype: str, 
                               require_empty: bool = True,
                               npc: 'NPC' = None) -> Optional['Building']:
        """
        按类型查找建筑（优先最近的空闲建筑）
        
        Args:
            buildings: 建筑列表
            btype: 建筑类型（如 'MARKET', 'FARM'）
            require_empty: 是否要求建筑无人工作（默认True，避免扎堆）
            npc: NPC引用（用于计算距离，如果提供则返回最近的）
        
        Returns:
            找到的建筑，或 None
        """
        # 先筛选出符合类型的建筑
        candidates = [b for b in buildings if getattr(b, 'building_type', None) == btype]
        
        if not candidates:
            return None
        
        # 根据 require_empty 过滤
        if require_empty:
            empty_candidates = [b for b in candidates if b.stack_child is None]
            if empty_candidates:
                candidates = empty_candidates
            else:
                # 所有建筑都被占用，返回 None（让调用方知道没有空位）
                return None
        
        # 如果提供了 NPC，返回最近的建筑
        if npc and len(candidates) > 1:
            return min(candidates, key=lambda b: self.distance_to_building(npc, b))
        
        # 否则返回第一个
        return candidates[0] if candidates else None
    
    def find_buildings_by_type(self, buildings: list, btype: str, 
                                require_empty: bool = False) -> List['Building']:
        """
        按类型查找所有建筑
        
        Args:
            buildings: 建筑列表
            btype: 建筑类型
            require_empty: 是否只返回空闲的建筑
        """
        result = [b for b in buildings if getattr(b, 'building_type', None) == btype]
        if require_empty:
            result = [b for b in result if b.stack_child is None]
        return result
    
    def find_nearest_building(self, npc: 'NPC', buildings: list, btype: str = None,
                               require_empty: bool = False) -> Optional['Building']:
        """
        查找最近的建筑
        
        Args:
            npc: NPC引用
            buildings: 建筑列表
            btype: 建筑类型（可选）
            require_empty: 是否只考虑空闲建筑
        """
        candidates = buildings
        if btype:
            candidates = self.find_buildings_by_type(buildings, btype, require_empty=require_empty)
        elif require_empty:
            candidates = [b for b in buildings if b.stack_child is None]
        
        if not candidates:
            return None
        
        return min(candidates, key=lambda b: self.distance_to_building(npc, b))
    
    def find_nearest_empty_building(self, npc: 'NPC', buildings: list, btype: str) -> Optional['Building']:
        """
        查找最近的空闲建筑（快捷方法）
        
        这是 NPC 最常用的方法：找到最近且无人工作的建筑
        """
        return self.find_nearest_building(npc, buildings, btype, require_empty=True)
    
    # ─── 距离计算 ───────────────────────────────────────────────
    
    def distance_to_building(self, npc: 'NPC', building: 'Building') -> float:
        """计算NPC到建筑的距离"""
        return math.hypot(
            npc.rect.centerx - building.rect.centerx,
            npc.rect.centery - building.rect.centery
        )
    
    def distance_to_npc(self, npc1: 'NPC', npc2: 'NPC') -> float:
        """计算两个NPC之间的距离"""
        return math.hypot(
            npc1.rect.centerx - npc2.rect.centerx,
            npc1.rect.centery - npc2.rect.centery
        )
    
    def is_at_building(self, npc: 'NPC', building: 'Building', threshold: float = 60) -> bool:
        """检查NPC是否在建筑附近"""
        return self.distance_to_building(npc, building) <= threshold
    
    def is_in_city(self, npc: 'NPC', world_map) -> bool:
        """检查NPC是否在城内"""
        if world_map and hasattr(world_map, 'city_rect'):
            return world_map.city_rect.collidepoint(npc.rect.centerx, npc.rect.centery)
        return True
    
    # ─── NPC属性 ───────────────────────────────────────────────
    
    def get_social_level(self, npc: 'NPC') -> int:
        """获取NPC的社会等级"""
        return getattr(npc, 'social_level', 1)
    
    def get_org_id(self, npc: 'NPC') -> Optional[str]:
        """获取NPC的组织ID"""
        org_id = getattr(npc, 'org_id', None)
        return org_id if org_id and org_id != 'NONE' else None
    
    # ─── 组织相关 ───────────────────────────────────────────────
    
    def apply_org_contribution(self, npc: 'NPC', amount: int) -> int:
        """
        应用组织贡献扣除
        
        Returns:
            扣除后实际获得的金额
        """
        if self._ai:
            return self._ai._apply_org_contribution(npc, amount)
        return amount
    
    def find_org_members(self, npc: 'NPC', all_npcs: List['NPC']) -> List['NPC']:
        """查找同组织的其他成员"""
        org_id = self.get_org_id(npc)
        if not org_id:
            return []
        return [n for n in all_npcs 
                if n != npc and self.get_org_id(n) == org_id]
    
    def find_org_leader(self, npc: 'NPC', all_npcs: List['NPC']) -> Optional['NPC']:
        """查找组织首领"""
        org_id = self.get_org_id(npc)
        if not org_id:
            return None
        for n in all_npcs:
            if self.get_org_id(n) == org_id and getattr(n, 'org_role', '') == 'LEADER':
                return n
        return None
    
    # ─── 伤员/救援相关 ───────────────────────────────────────────
    
    def find_nearby_downed(self, npc: 'NPC', all_npcs: List['NPC'], 
                           radius: float = 400) -> Optional['NPC']:
        """查找附近需要救援的倒地NPC"""
        from src.definitions import SAFETY_DOWNED
        for other in all_npcs:
            if other == npc:
                continue
            if other.safety != SAFETY_DOWNED:
                continue
            if other.stack_parent is not None:  # 已被带回家
                continue
            if self.distance_to_npc(npc, other) <= radius:
                return other
        return None