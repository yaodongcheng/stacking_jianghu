# --- src/ai/job_behaviors/farmer.py ---
"""
农民职业行为
使用原子行为组合模式
"""
import random
from src.ai.job_behaviors.base import BaseJobBehavior
from src.definitions import ITEM_GRAIN, ITEM_COIN, SAFETY_NORMAL


class FarmerBehavior(BaseJobBehavior):
    """
    农民行为：
    - 有粮食时去市场卖粮
    - 否则去农田工作
    - 闲暇时在城内闲逛
    """
    
    GRAIN_SELL_THRESHOLD = 3  # 达到此数量去卖粮
    WORK_DURATION_MS = 8000   # 工作时长
    GRAIN_PER_WORK = 1        # 每次工作产出
    GRAIN_SELL_PRICE = 5      # 每单位粮食售价
    
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
            # 农民遇到敌人选择逃跑
            self.enqueue_flee(npc, enemy, flee_distance=400, reason="逃命")
            return True
        
        # 优先级2：有足够粮食，去卖粮
        grain_count = npc.inventory.get(ITEM_GRAIN, 0)
        if grain_count >= self.GRAIN_SELL_THRESHOLD:
            # 找最近的市场（市场不需要 require_empty，可以多人同时交易）
            market = self.find_building_by_type(all_buildings, 'MARKET', require_empty=False, npc=npc)
            if market:
                # 移动到市场 -> 等待交易 -> 卖粮
                self.enqueue_move_to_position(
                    npc, market.rect.centerx, market.rect.centery,
                    stop_dist=50, reason="去市场卖粮"
                )
                self.enqueue_wait(npc, 1500, reason="交易中")
                self.enqueue_trade(
                    npc, market, 
                    sell_item=ITEM_GRAIN, sell_amount=grain_count,
                    reason="卖粮"
                )
                return True
        
        # 优先级3：去农田工作（找最近的空闲农田）
        farm = self.find_nearest_empty_building(npc, all_buildings, 'FARM')
        if farm:
            # 移动到农田 -> 工作 -> 产出粮食
            self.enqueue_move_to_building(npc, farm, reason="去农田")
            self.enqueue_work(
                npc, farm,
                duration_ms=self.WORK_DURATION_MS,
                produce_item=ITEM_GRAIN,
                produce_amount=self.GRAIN_PER_WORK,
                reason="耕作"
            )
            return True
        
        # 优先级4：在城内闲逛
        if world_map and hasattr(world_map, 'city_rect'):
            self.enqueue_roam(npc, world_map.city_rect, reason="散步")
            return True
        
        # 兜底：等待
        self.enqueue_wait(npc, random.randint(2000, 5000), reason="休息")
        return True