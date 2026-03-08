# --- src/ai/job_behaviors/artisan.py ---
"""
工匠职业行为
从原ai_system.py抽离 _enqueue_artisan
"""
import random
from src.ai.job_behaviors.base import BaseJobBehavior
from src.definitions import ITEM_CRAFT, ITEM_CLOTH, ITEM_IRON
from src.utils import log_game_event


class ArtisanBehavior(BaseJobBehavior):
    """
    工匠行为逻辑
    
    工作循环：工坊制作 → 产出工艺品/布匹/铁器 → 卖给市场
    基于 social_level 差异化行为：
    - level 1: 学徒 - 打杂学艺
    - level 2-3: 工匠 - 制作产出
    - level 4-5: 大师 - 指导收徒
    """
    
    WORK_TIME_MS = 18000   # 工作18秒产出1件
    CRAFT_PRICE = 5        # 工艺品基础售价
    
    # 工匠可生产的物品
    CRAFTABLE_ITEMS = [ITEM_CRAFT, ITEM_CLOTH, ITEM_IRON]
    
    def execute(self, npc, context: dict) -> bool:
        """执行工匠行为"""
        all_buildings = context.get('all_buildings', [])
        world_map = context.get('world_map')
        
        if self.has_pending_action(npc):
            return True
        
        social_level = self.get_social_level(npc)
        
        # ─── 大师 (4-5): 指导为主 ───
        if social_level >= 4:
            return self._master_behavior(npc, all_buildings, world_map)
        
        # ─── 工匠 (2-3): 制作产出 ───
        if social_level >= 2:
            return self._artisan_behavior(npc, all_buildings, world_map)
        
        # ─── 学徒 (1): 打杂学艺 ───
        return self._apprentice_behavior(npc, all_buildings, world_map)
    
    def _master_behavior(self, npc, all_buildings, world_map) -> bool:
        """大师行为"""
        roll = random.random()
        
        if roll < 0.5:
            # 50% 在工坊指导（大师不需要空位，可以多人同时在场）
            workshop = self.find_nearest_building(npc, all_buildings, 'WORKSHOP')
            if workshop:
                if not self.is_at_building(npc, workshop, 80):
                    self.enqueue_move_to_building(npc, workshop, "指导")
                    npc.ai_reason = "去工坊指导"
                    return True
                self.enqueue_wait(npc, 5000, "指导徒弟")
                npc.ai_reason = "指导徒弟"
                return True
        
        elif roll < 0.8:
            # 30% 去茶馆休息
            teahouse = self.find_nearest_building(npc, all_buildings, 'TEAHOUSE')
            if teahouse:
                self.enqueue_move_to_building(npc, teahouse, "休息")
                npc.ai_reason = "茶馆歇息"
                return True
        
        # 20% 在城中散步
        self.enqueue_roam(npc, world_map.city_rect, duration_ms=5000, reason="散步")
        npc.ai_reason = "城中散步"
        return True
    
    def _artisan_behavior(self, npc, all_buildings, world_map) -> bool:
        """普通工匠行为"""
        # 查找最近的工坊（工坊可以多人工作，不需要 require_empty）
        workshop = self.find_nearest_building(npc, all_buildings, 'WORKSHOP')
        if not workshop:
            self.enqueue_roam(npc, world_map.city_rect, reason="找工坊")
            return True
        
        # 有货要卖
        total_items = sum(npc.inventory.get(item, 0) for item in self.CRAFTABLE_ITEMS)
        if total_items >= 3:
            return self._sell_crafts(npc, all_buildings, world_map)
        
        # 前往工坊工作
        if not self.is_at_building(npc, workshop):
            self.enqueue_move_to_building(npc, workshop, "工作")
            npc.ai_reason = "去工坊"
            return True
        
        # 在工坊制作
        self._do_crafting(npc, workshop)
        return True
    
    def _apprentice_behavior(self, npc, all_buildings, world_map) -> bool:
        """学徒行为"""
        workshop = self.find_nearest_building(npc, all_buildings, 'WORKSHOP')
        if not workshop:
            self.enqueue_roam(npc, world_map.city_rect, reason="找工坊")
            return True
        
        # 前往工坊
        if not self.is_at_building(npc, workshop):
            self.enqueue_move_to_building(npc, workshop, "学艺")
            npc.ai_reason = "去工坊"
            return True
        
        # 学艺（产出较慢）
        roll = random.random()
        if roll < 0.6:
            # 学习观摩
            self.enqueue_wait(npc, 4000, "学艺")
            npc.ai_reason = "观摩学艺"
        elif roll < 0.8:
            # 打杂
            self.enqueue_roam(npc, world_map.city_rect, duration_ms=3000, reason="跑腿")
            npc.ai_reason = "帮师傅跑腿"
        else:
            # 尝试制作
            self._do_crafting(npc, workshop, slow=True)
        return True
    
    def _do_crafting(self, npc, workshop, slow: bool = False):
        """制作物品"""
        work_time = getattr(npc, '_artisan_work_time', 0)
        work_time += getattr(npc, '_dt_ms', 16)
        
        time_needed = self.WORK_TIME_MS * (2 if slow else 1)
        
        if work_time >= time_needed:
            # 随机产出一种物品
            item = random.choice(self.CRAFTABLE_ITEMS)
            npc.inventory[item] = npc.inventory.get(item, 0) + 1
            workshop.inventory[item] = workshop.inventory.get(item, 0) + 1
            npc._artisan_work_time = 0
            npc.ai_reason = f"制成{item[:2]}"
            log_game_event(f"[工匠] {npc.name} 制成 {item}", tag="ECONOMY")
        else:
            npc._artisan_work_time = work_time
            progress = int(work_time / time_needed * 100)
            npc.ai_reason = f"制作{progress}%"
        
        self.enqueue_wait(npc, 2000, "制作")
    
    def _sell_crafts(self, npc, all_buildings, world_map) -> bool:
        """卖工艺品"""
        # 找最近的市场
        market = self.find_nearest_building(npc, all_buildings, 'MARKET')
        if not market:
            self.enqueue_roam(npc, world_map.city_rect, reason="找市场")
            return True
        
        if not self.is_at_building(npc, market):
            self.enqueue_move_to_position(
                npc, market.rect.centerx, market.rect.centery,
                stop_dist=50, reason="去卖货"
            )
            npc.ai_reason = "运货去卖"
            return True
        
        # 卖掉所有工艺品
        total_earned = 0
        for item in self.CRAFTABLE_ITEMS:
            count = npc.inventory.get(item, 0)
            if count > 0:
                earnings = count * self.CRAFT_PRICE
                actual = self.apply_org_contribution(npc, earnings)
                npc.money += actual
                total_earned += actual
                market.inventory[item] = market.inventory.get(item, 0) + count
                npc.inventory[item] = 0
        
        if total_earned > 0:
            npc.ai_reason = f"卖货+{total_earned}铜"
        
        self.enqueue_wait(npc, 1500, "交易")
        return True
