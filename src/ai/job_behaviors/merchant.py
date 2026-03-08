# --- src/ai/job_behaviors/merchant.py ---
"""
商人职业行为
从原ai_system.py抽离 _enqueue_merchant
"""
import math
import random
from src.ai.job_behaviors.base import BaseJobBehavior
from src.definitions import ITEM_GRAIN, ITEM_CRAFT, ITEM_CLOTH, ITEM_IRON, ITEM_BOOK
from src.definitions import STATE_CARRYING
from src.utils import log_game_event

# 商人状态
MERCHANT_STATE_IDLE = 0
MERCHANT_STATE_BUYING = 1
MERCHANT_STATE_SELLING = 2


class MerchantBehavior(BaseJobBehavior):
    """
    商人行为逻辑
    
    工作循环：进货 → 运输 → 卖货 → 利润
    基于 social_level 差异化行为：
    - level 1-2: 伙计/小贩 - 跑腿为主
    - level 3: 掌柜 - 管理经营
    - level 4-5: 大商人 - 坐镇收钱
    """
    
    TRADEABLE_ITEMS = [ITEM_GRAIN, ITEM_CRAFT, ITEM_CLOTH, ITEM_IRON, ITEM_BOOK]
    
    def execute(self, npc, context: dict) -> bool:
        """执行商人行为"""
        all_buildings = context.get('all_buildings', [])
        world_map = context.get('world_map')
        
        if self.has_pending_action(npc):
            return True
        
        social_level = self.get_social_level(npc)
        
        # ─── 大商人 (4-5): 坐镇为主 ───
        if social_level >= 4:
            return self._big_merchant_behavior(npc, all_buildings, world_map)
        
        # ─── 掌柜 (3): 管理经营 ───
        if social_level >= 3:
            return self._manager_behavior(npc, all_buildings, world_map)
        
        # ─── 伙计/小贩 (1-2): 正常贸易 ───
        return self._trader_behavior(npc, all_buildings, world_map)
    
    def _big_merchant_behavior(self, npc, all_buildings, world_map) -> bool:
        """大商人行为"""
        roll = random.random()
        
        if roll < 0.5:
            # 50% 在市场坐镇（找最近的市场）
            market = self.find_nearest_building(npc, all_buildings, 'MARKET')
            if market and not self.is_at_building(npc, market, 80):
                self.enqueue_move_to_building(npc, market, "坐镇")
                npc.ai_reason = "去市场坐镇"
                return True
            self.enqueue_wait(npc, 5000, "坐镇")
            npc.ai_reason = "市场坐镇"
            return True
        
        elif roll < 0.8:
            # 30% 去茶馆会客（找最近的茶馆）
            teahouse = self.find_nearest_building(npc, all_buildings, 'TEAHOUSE')
            if teahouse:
                self.enqueue_move_to_building(npc, teahouse, "会客")
                npc.ai_reason = "茶馆会客"
                return True
        
        # 20% 休息
        self.enqueue_wait(npc, 4000, "休息")
        npc.ai_reason = "歇息片刻"
        return True
    
    def _manager_behavior(self, npc, all_buildings, world_map) -> bool:
        """掌柜行为"""
        roll = random.random()
        
        if roll < 0.6:
            # 60% 在市场坐镇揽客（找最近的市场）
            market = self.find_nearest_building(npc, all_buildings, 'MARKET')
            if market:
                if not self.is_at_building(npc, market):
                    self.enqueue_move_to_building(npc, market, "坐镇")
                    npc.ai_reason = "去市场坐镇"
                    return True
                # 在市场附近揽客
                import pygame
                market_area = pygame.Rect(
                    market.rect.x - 80, market.rect.y - 80,
                    market.rect.width + 160, market.rect.height + 160
                )
                self.enqueue_roam(npc, market_area, duration_ms=5000, reason="揽客")
                npc.ai_reason = "坐镇揽客"
                return True
        
        elif roll < 0.8:
            # 20% 去茶馆休息（找最近的空闲茶馆）
            teahouse = self.find_nearest_empty_building(npc, all_buildings, 'TEAHOUSE')
            if teahouse:
                self.enqueue_move_to_building(npc, teahouse, "休息")
                npc.ai_reason = "茶馆歇脚"
                return True
        
        # 20% 执行贸易逻辑
        return self._trader_behavior(npc, all_buildings, world_map)
    
    def _trader_behavior(self, npc, all_buildings, world_map) -> bool:
        """普通贸易行为"""
        # 获取最近的市场
        market = self.find_nearest_building(npc, all_buildings, 'MARKET')
        if not market:
            self.enqueue_roam(npc, world_map.city_rect, duration_ms=5000, reason="找市场")
            return True
        
        # 计算背包中的可售商品
        sellable_items = {}
        for item_id in self.TRADEABLE_ITEMS:
            count = npc.inventory.get(item_id, 0)
            if count > 0:
                sellable_items[item_id] = count
        
        total_sellable = sum(sellable_items.values())
        
        # 情况1：有货 → 去卖
        if total_sellable > 0:
            return self._sell_goods(npc, market, sellable_items, world_map)
        
        # 情况2：无货 → 去进货
        return self._buy_goods(npc, market, all_buildings, world_map)
    
    def _sell_goods(self, npc, market, sellable_items, world_map) -> bool:
        """卖货"""
        if not self.is_at_building(npc, market):
            first_item = list(sellable_items.keys())[0]
            total = sum(sellable_items.values())
            self.enqueue_move_to_position(
                npc, market.rect.centerx, market.rect.centery,
                stop_dist=50, reason=f"运货({first_item[:2]}×{total})",
                state_override=STATE_CARRYING
            )
            npc._trade_state = MERCHANT_STATE_SELLING
            return True
        
        # 上架销售
        total_earned = 0
        for item_id, count in sellable_items.items():
            # 简化的价格计算
            sell_price = self._get_sell_price(item_id)
            
            # 上架到市场
            market.inventory[item_id] = market.inventory.get(item_id, 0) + count
            
            # 收款
            earnings = sell_price * count
            actual = self.apply_org_contribution(npc, earnings)
            npc.money += actual
            total_earned += actual
            
            # 清空库存
            del npc.inventory[item_id]
            
            log_game_event(
                f"[商人] {npc.name} 上架 {item_id}×{count} 售价{sell_price}/件",
                tag="ECONOMY"
            )
        
        npc.ai_reason = f"卖货+{total_earned}铜"
        npc._trade_state = MERCHANT_STATE_IDLE
        self.enqueue_wait(npc, 2000, f"收入{total_earned}铜")
        return True
    
    def _buy_goods(self, npc, market, all_buildings, world_map) -> bool:
        """进货"""
        # 决定进什么货
        best_item = self._decide_purchase(market)
        if not best_item:
            # 无货可进，在市场揽客
            return self._idle_at_market(npc, market, world_map)
        
        # 找供货点
        source = self._find_source(best_item, all_buildings)
        if not source:
            return self._idle_at_market(npc, market, world_map)
        
        if not self.is_at_building(npc, source):
            self.enqueue_move_to_position(
                npc, source.rect.centerx, source.rect.centery,
                stop_dist=50, reason=f"进货({best_item[:2]})"
            )
            npc._trade_state = MERCHANT_STATE_BUYING
            return True
        
        # 尝试收购
        available = source.inventory.get(best_item, 0)
        if available > 0:
            buy_price = self._get_buy_price(best_item)
            max_buy = min(available, 5, npc.money // max(1, buy_price))
            
            if max_buy > 0:
                total_cost = buy_price * max_buy
                npc.money -= total_cost
                npc.inventory[best_item] = npc.inventory.get(best_item, 0) + max_buy
                source.inventory[best_item] -= max_buy
                if source.inventory[best_item] <= 0:
                    del source.inventory[best_item]
                
                log_game_event(
                    f"[商人] {npc.name} 进货 {best_item}×{max_buy} 花费{total_cost}铜",
                    tag="ECONOMY"
                )
                npc.ai_reason = f"进货-{total_cost}铜"
                npc._trade_state = MERCHANT_STATE_IDLE
                self.enqueue_wait(npc, 1500, "装货")
                return True
            else:
                npc.ai_reason = "资金不足"
        else:
            npc.ai_reason = "无货可进"
        
        self.enqueue_wait(npc, 3000, "等货")
        return True
    
    def _idle_at_market(self, npc, market, world_map) -> bool:
        """在市场揽客"""
        if self.is_at_building(npc, market, 100):
            if random.random() < 0.4:
                import pygame
                market_area = pygame.Rect(
                    market.rect.x - 60, market.rect.y - 60,
                    market.rect.width + 120, market.rect.height + 120
                )
                self.enqueue_roam(npc, market_area, duration_ms=4000, reason="揽客")
            else:
                self.enqueue_wait(npc, 3000, "守店")
        else:
            self.enqueue_move_to_position(
                npc, market.rect.centerx, market.rect.centery,
                stop_dist=40, reason="返回铺位"
            )
        npc._trade_state = MERCHANT_STATE_IDLE
        return True
    
    def _decide_purchase(self, market) -> str:
        """决定进什么货"""
        best_item = None
        best_score = -1
        for item_id in self.TRADEABLE_ITEMS:
            stock = market.inventory.get(item_id, 0)
            # 缺货越多分数越高
            score = max(0, 20 - stock)
            if score > best_score:
                best_score = score
                best_item = item_id
        return best_item if best_score > 0 else None
    
    def _find_source(self, item_id: str, all_buildings) -> object:
        """查找供货点"""
        source_map = {
            ITEM_GRAIN: 'FARM',
            ITEM_CRAFT: 'WORKSHOP',
            ITEM_CLOTH: 'WORKSHOP',
            ITEM_IRON: 'WORKSHOP',
            ITEM_BOOK: 'SCHOOL',
        }
        btype = source_map.get(item_id)
        if not btype:
            return None
        
        # 优先找有库存的
        for b in all_buildings:
            if getattr(b, 'building_type', None) == btype:
                if b.inventory.get(item_id, 0) > 0:
                    return b
        
        # 否则找任意一个
        return self.find_building_by_type(all_buildings, btype)
    
    def _get_sell_price(self, item_id: str) -> int:
        """获取售价"""
        prices = {
            ITEM_GRAIN: 4,
            ITEM_CRAFT: 6,
            ITEM_CLOTH: 5,
            ITEM_IRON: 8,
            ITEM_BOOK: 10,
        }
        return prices.get(item_id, 5)
    
    def _get_buy_price(self, item_id: str) -> int:
        """获取进价"""
        prices = {
            ITEM_GRAIN: 2,
            ITEM_CRAFT: 3,
            ITEM_CLOTH: 3,
            ITEM_IRON: 5,
            ITEM_BOOK: 6,
        }
        return prices.get(item_id, 3)
