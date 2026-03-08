# --- src/ai/job_behaviors/official.py ---
"""
官员职业行为
管理城市、审案、收税的官员
"""
import random
from src.ai.job_behaviors.base import BaseJobBehavior
from src.definitions import SAFETY_NORMAL, SAFETY_DOWNED


class OfficialBehavior(BaseJobBehavior):
    """
    官员行为：
    - 高级官员坐镇府衙办公
    - 中级官员巡视城区、收税
    - 低级小吏跑腿传话
    """
    
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
        if npc.aggro_target is not None and combat_manager:
            self.enqueue_combat(npc, npc.aggro_target, combat_manager, reason=f"拿下{npc.aggro_target.name}")
            return True
        
        # 优先级2：搜索敌人
        enemy = self.find_enemy(npc, all_npcs)
        if enemy and combat_manager:
            self.enqueue_combat(npc, enemy, combat_manager, reason=f"抓捕{enemy.name}")
            return True
        
        social_level = self.get_social_level(npc)
        
        # ─── 高官 (4-5): 坐镇府衙 ───
        if social_level >= 4:
            return self._high_official_behavior(npc, all_buildings, world_map)
        
        # ─── 中级 (2-3): 巡视/收税 ───
        if social_level >= 2:
            return self._mid_official_behavior(npc, all_buildings, world_map)
        
        # ─── 小吏 (1): 跑腿 ───
        return self._low_official_behavior(npc, all_buildings, world_map)
    
    def _high_official_behavior(self, npc, all_buildings, world_map) -> bool:
        """高官行为"""
        roll = random.random()
        
        if roll < 0.6:
            # 60% 在府衙办公（找最近的府衙）
            yamen = self.find_nearest_building(npc, all_buildings, 'YAMEN')
            if yamen:
                if not self.is_at_building(npc, yamen, 80):
                    self.enqueue_move_to_building(npc, yamen, "办公")
                    return True
                self.enqueue_wait(npc, 5000, "理政")
                return True
        
        elif roll < 0.8:
            # 20% 茶馆议事（找最近的茶馆）
            teahouse = self.find_nearest_building(npc, all_buildings, 'TEAHOUSE')
            if teahouse:
                self.enqueue_move_to_building(npc, teahouse, "议事")
                return True
        
        # 20% 在城中散步
        if world_map and hasattr(world_map, 'city_rect'):
            self.enqueue_roam(npc, world_map.city_rect, duration_ms=4000, reason="微服私访")
        else:
            self.enqueue_wait(npc, 3000, "思考")
        return True
    
    def _mid_official_behavior(self, npc, all_buildings, world_map) -> bool:
        """中级官员行为"""
        roll = random.random()
        
        if roll < 0.4:
            # 40% 巡视市场（收税）- 找最近的市场
            market = self.find_nearest_building(npc, all_buildings, 'MARKET')
            if market:
                self.enqueue_move_to_position(
                    npc, market.rect.centerx, market.rect.centery,
                    stop_dist=60, reason="巡查市场"
                )
                self.enqueue_wait(npc, 3000, "督查")
                return True
        
        elif roll < 0.7:
            # 30% 在府衙值班（找最近的府衙）
            yamen = self.find_nearest_building(npc, all_buildings, 'YAMEN')
            if yamen:
                self.enqueue_move_to_building(npc, yamen, "值班")
                self.enqueue_wait(npc, 4000, "当值")
                return True
        
        # 30% 在城中巡视
        if world_map and hasattr(world_map, 'city_rect'):
            self.enqueue_roam(npc, world_map.city_rect, duration_ms=5000, reason="巡视")
        else:
            self.enqueue_wait(npc, 3000, "等待")
        return True
    
    def _low_official_behavior(self, npc, all_buildings, world_map) -> bool:
        """小吏行为"""
        roll = random.random()
        
        if roll < 0.5:
            # 50% 在府衙候命（找最近的府衙）
            yamen = self.find_nearest_building(npc, all_buildings, 'YAMEN')
            if yamen:
                self.enqueue_move_to_building(npc, yamen, "候命")
                self.enqueue_wait(npc, 3000, "待命")
                return True
        
        # 50% 在城中跑腿
        if world_map and hasattr(world_map, 'city_rect'):
            self.enqueue_roam(npc, world_map.city_rect, duration_ms=4000, reason="跑腿")
        else:
            self.enqueue_wait(npc, 3000, "歇息")
        return True
