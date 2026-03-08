# --- src/ai/job_behaviors/guard.py ---
"""
守卫/官差职业行为
使用原子行为组合模式
"""
import random
from src.ai.job_behaviors.base import BaseJobBehavior
from src.definitions import SAFETY_NORMAL, SAFETY_DOWNED


class GuardBehavior(BaseJobBehavior):
    """
    守卫行为：
    - 发现敌人（山贼/泼皮正在作恶）→ 战斗
    - 发现倒地的同组织成员 → 救援
    - 巡逻指定区域
    - 驻守岗位
    """
    
    PATROL_WAIT_MS = 2000   # 巡逻点等待时间
    RESCUE_RADIUS = 300     # 救援感知范围
    
    def execute(self, npc, context: dict) -> bool:
        # 已有行为在执行
        if self.has_pending_action(npc):
            return False
        
        # 非正常状态不处理
        if npc.safety != SAFETY_NORMAL:
            return False
        
        all_npcs = context.get('all_npcs', [])
        all_buildings = context.get('all_buildings', [])
        world_map = context.get('world_map')
        combat_manager = context.get('combat_manager')
        
        # 优先级1：有锁定目标，继续战斗
        if npc.aggro_target is not None:
            if combat_manager:
                self.enqueue_combat(npc, npc.aggro_target, combat_manager, reason=f"追捕{npc.aggro_target.name}")
            return True
        
        # 优先级2：搜索敌人
        enemy = self.find_enemy(npc, all_npcs)
        if enemy and combat_manager:
            self.enqueue_combat(npc, enemy, combat_manager, reason=f"拿下{enemy.name}！")
            return True
        
        # 优先级3：救援同组织倒地成员
        downed = self._find_org_downed(npc, all_npcs)
        if downed:
            # 找最近的诊所
            clinic = self.find_nearest_building(npc, all_buildings, 'CLINIC')
            self.enqueue_rescue(npc, downed, clinic, reason=f"救援{downed.name}")
            return True
        
        # 优先级4：巡逻
        patrol_points = self._get_patrol_points(npc, world_map)
        if patrol_points:
            self.enqueue_patrol(npc, patrol_points, loop=True, reason="巡逻")
            return True
        
        # 优先级5：驻守岗位
        post = self._find_guard_post(npc, all_buildings)
        if post:
            self.enqueue_move_to_position(
                npc, post.rect.centerx, post.rect.centery,
                stop_dist=30, reason="驻守"
            )
            self.enqueue_wait(npc, 5000, reason="站岗")
            return True
        
        # 兜底：在城内闲逛
        if world_map and hasattr(world_map, 'city_rect'):
            self.enqueue_roam(npc, world_map.city_rect, reason="巡视")
        else:
            self.enqueue_wait(npc, random.randint(2000, 4000), reason="戒备")
        return True
    
    def _find_org_downed(self, npc, all_npcs):
        """查找同组织倒地的NPC"""
        org_id = self.get_org_id(npc)
        if not org_id:
            return None
        
        for other in all_npcs:
            if other == npc:
                continue
            if other.safety != SAFETY_DOWNED:
                continue
            if other.stack_parent is not None:
                continue
            if self.get_org_id(other) != org_id:
                continue
            if self.distance_to_npc(npc, other) <= self.RESCUE_RADIUS:
                return other
        return None
    
    def _get_patrol_points(self, npc, world_map):
        """获取巡逻点"""
        if not world_map or not hasattr(world_map, 'city_rect'):
            return None
        
        city = world_map.city_rect
        # 生成4个巡逻点（城区四角附近）
        margin = 100
        points = [
            (city.left + margin, city.top + margin),
            (city.right - margin, city.top + margin),
            (city.right - margin, city.bottom - margin),
            (city.left + margin, city.bottom - margin),
        ]
        # 随机选择起点
        start = random.randint(0, 3)
        return points[start:] + points[:start]
    
    def _find_guard_post(self, npc, all_buildings):
        """查找最近的守卫岗位"""
        # 尝试查找府衙或城门（找最近的）
        for btype in ['YAMEN', 'GATE', 'TOWER']:
            post = self.find_nearest_building(npc, all_buildings, btype)
            if post:
                return post
        return None
