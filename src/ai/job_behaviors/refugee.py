# --- src/ai/job_behaviors/refugee.py ---
"""
流民职业行为
流离失所的人，等待被招募或自己找工作
"""
import random
from src.ai.job_behaviors.base import BaseJobBehavior
from src.definitions import SAFETY_NORMAL


class RefugeeBehavior(BaseJobBehavior):
    """
    流民行为：
    - 在城内乞讨/闲逛
    - 偶尔去茶馆/市场附近找机会
    - 可被招募加入组织
    """
    
    def execute(self, npc, context: dict) -> bool:
        # 已有行为在执行
        if self.has_pending_action(npc):
            return False
        
        # 非正常状态不处理
        if npc.safety != SAFETY_NORMAL:
            return False
        
        all_buildings = context.get('all_buildings', [])
        all_npcs = context.get('all_npcs', [])
        world_map = context.get('world_map')
        
        # 优先级1：检查是否有敌人
        enemy = self.find_enemy(npc, all_npcs)
        if enemy:
            # 流民遇到敌人选择逃跑
            self.enqueue_flee(npc, enemy, flee_distance=350, reason="逃命")
            return True
        
        # 随机行为选择
        roll = random.random()
        
        if roll < 0.4:
            # 40% 在城内乞讨闲逛
            if world_map and hasattr(world_map, 'city_rect'):
                self.enqueue_roam(npc, world_map.city_rect, duration_ms=6000, reason="乞讨")
                return True
        
        elif roll < 0.6:
            # 20% 去最近的市场附近找机会
            market = self.find_nearest_building(npc, all_buildings, 'MARKET')
            if market:
                self.enqueue_move_to_position(
                    npc, market.rect.centerx, market.rect.centery,
                    stop_dist=100, reason="找活干"
                )
                self.enqueue_wait(npc, 3000, reason="观望")
                return True
        
        elif roll < 0.75:
            # 15% 去最近的茶馆打探消息
            teahouse = self.find_nearest_building(npc, all_buildings, 'TEAHOUSE')
            if teahouse:
                self.enqueue_move_to_position(
                    npc, teahouse.rect.centerx, teahouse.rect.centery,
                    stop_dist=80, reason="打探消息"
                )
                self.enqueue_wait(npc, 2000, reason="听人说话")
                return True
        
        # 默认：等待
        self.enqueue_wait(npc, random.randint(2000, 5000), reason="发呆")
        return True
