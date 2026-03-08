# --- src/economy_system.py ---
"""
阶段2：经济循环系统
- 市场供需价格波动
- 商人贸易利润计算
- NPC消费驱动
"""
import math
from src.definitions import *
from src.item_system import ItemManager

# ═══════════════════════════════════════════════════════════════════
# 市场价格系统 - 供需决定价格
# ═══════════════════════════════════════════════════════════════════

class MarketPriceSystem:
    """
    市场价格由供需关系决定：
    - 基准价格来自 items.csv
    - 当前价格 = 基准价 × 供需系数
    - 供需系数范围: 0.5 ~ 2.0
    """
    
    # 商品供需基准（每日期望消费量）
    DAILY_DEMAND = {
        ITEM_GRAIN: 20,      # 粮食需求高
        ITEM_CLOTH: 5,       # 布匹需求中
        ITEM_FOOD: 15,       # 熟食需求高
        ITEM_BOOK: 3,        # 书卷需求低
        ITEM_CRAFT: 5,       # 精制器物需求中
        ITEM_IRON: 8,        # 铁矿需求中
    }
    
    def __init__(self):
        self.item_sys = ItemManager.get_instance()
        # 当前价格缓存 {item_id: current_price}
        self.current_prices = {}
        # 供需系数 {item_id: multiplier} 范围 0.5~2.0
        self.supply_demand_ratio = {}
        # 今日销量统计（用于计算需求）
        self.daily_sales = {}
        # 今日库存量统计（用于计算供给）
        self.daily_supply = {}
        
    def get_price(self, item_id, is_buy=True):
        """
        获取物品当前价格
        is_buy=True: NPC购买价格（稍高）
        is_buy=False: NPC出售价格（稍低）
        """
        base_price = self.item_sys.get_market_price(item_id)
        if base_price == 0:
            base_price = 5  # 默认基础价格
            
        # 获取供需系数
        ratio = self.supply_demand_ratio.get(item_id, 1.0)
        
        # 计算当前价格
        current = int(base_price * ratio)
        
        # 买入价比卖出价高20%（商人利润空间）
        if is_buy:
            return max(1, int(current * 1.1))
        else:
            return max(1, int(current * 0.9))
    
    def record_sale(self, item_id, quantity=1):
        """记录一笔销售（增加需求信号）"""
        self.daily_sales[item_id] = self.daily_sales.get(item_id, 0) + quantity
        
    def record_supply(self, item_id, quantity=1):
        """记录一笔供给（商人上架）"""
        self.daily_supply[item_id] = self.daily_supply.get(item_id, 0) + quantity
        
    def update_prices(self, market_building):
        """
        每日结算时调用，根据供需更新价格
        market_building: 市场建筑对象，用于获取当前库存
        """
        for item_id in list(self.DAILY_DEMAND.keys()):
            base_demand = self.DAILY_DEMAND.get(item_id, 10)
            
            # 实际需求 = 销量
            actual_demand = self.daily_sales.get(item_id, 0)
            # 实际供给 = 库存 + 今日入库
            current_stock = market_building.inventory.get(item_id, 0) if market_building else 0
            actual_supply = current_stock + self.daily_supply.get(item_id, 0)
            
            # 计算供需比
            if actual_demand == 0:
                actual_demand = base_demand * 0.5  # 没有销量假设需求减半
            
            if actual_supply == 0:
                # 无供给 → 价格暴涨
                new_ratio = 2.0
            else:
                # 供需比 = 需求 / 供给
                raw_ratio = actual_demand / actual_supply
                # 平滑：新比例 = 旧比例 × 0.7 + 原始比例 × 0.3
                old_ratio = self.supply_demand_ratio.get(item_id, 1.0)
                new_ratio = old_ratio * 0.7 + raw_ratio * 0.3
            
            # 限制在 0.5 ~ 2.0 之间
            new_ratio = max(0.5, min(2.0, new_ratio))
            self.supply_demand_ratio[item_id] = new_ratio
            
            # 更新价格缓存
            base_price = self.item_sys.get_market_price(item_id) or 5
            self.current_prices[item_id] = int(base_price * new_ratio)
        
        # 清空今日统计
        self.daily_sales = {}
        self.daily_supply = {}
    
    def get_price_trend(self, item_id):
        """
        获取价格趋势文字描述
        返回: (趋势符号, 颜色)
        """
        ratio = self.supply_demand_ratio.get(item_id, 1.0)
        if ratio > 1.3:
            return ("↑↑", (255, 50, 50))    # 大涨（红色）
        elif ratio > 1.1:
            return ("↑", (255, 150, 50))    # 小涨（橙色）
        elif ratio < 0.7:
            return ("↓↓", (50, 200, 50))    # 大跌（绿色）
        elif ratio < 0.9:
            return ("↓", (100, 255, 100))   # 小跌（浅绿）
        else:
            return ("—", (150, 150, 150))   # 平稳（灰色）


# ═══════════════════════════════════════════════════════════════════
# 商人贸易管理器 - 记录进货成本和利润
# ═══════════════════════════════════════════════════════════════════

class MerchantTradeManager:
    """
    管理商人的贸易记录：
    - 进货时记录成本
    - 卖出时计算利润
    - 追踪每个商人的总利润
    """
    
    def __init__(self):
        # {npc_id: {item_id: {'cost': total_cost, 'count': count}}}
        self.purchase_records = {}
        # {npc_id: total_profit}
        self.merchant_profits = {}
        
    def record_purchase(self, npc, item_id, quantity, cost_per_unit):
        """
        记录商人进货
        """
        npc_id = npc.id
        if npc_id not in self.purchase_records:
            self.purchase_records[npc_id] = {}
            
        record = self.purchase_records[npc_id]
        if item_id not in record:
            record[item_id] = {'cost': 0, 'count': 0}
            
        record[item_id]['cost'] += cost_per_unit * quantity
        record[item_id]['count'] += quantity
        
    def record_sale(self, npc, item_id, quantity, sell_price):
        """
        记录商人卖出，计算利润
        返回: 本次利润
        """
        npc_id = npc.id
        if npc_id not in self.purchase_records:
            # 没有进货记录，假设成本为0
            profit = sell_price * quantity
        else:
            record = self.purchase_records[npc_id].get(item_id)
            if record and record['count'] > 0:
                # 计算平均成本
                avg_cost = record['cost'] / record['count']
                profit = int((sell_price - avg_cost) * quantity)
                # 扣除已售数量
                record['count'] -= quantity
                record['cost'] -= avg_cost * quantity
                if record['count'] <= 0:
                    del self.purchase_records[npc_id][item_id]
            else:
                profit = sell_price * quantity
        
        # 累计利润
        self.merchant_profits[npc_id] = self.merchant_profits.get(npc_id, 0) + profit
        return profit
    
    def get_profit(self, npc):
        """获取商人累计利润"""
        return self.merchant_profits.get(npc.id, 0)


# ═══════════════════════════════════════════════════════════════════
# 统一经济系统门面类 - 对外提供统一接口
# ═══════════════════════════════════════════════════════════════════

class EconomySystem:
    """
    经济系统门面类，整合市场价格和商人贸易功能。
    main.py 通过此类访问所有经济功能。
    """
    
    def __init__(self, font_manager=None):
        self.font_manager = font_manager
        self.market = MarketPriceSystem()
        self.trade_manager = MerchantTradeManager()
    
    # ---- 市场价格相关 ----
    def get_price(self, item_id, is_buy=True):
        """获取物品当前市场价格"""
        return self.market.get_price(item_id, is_buy)
    
    def record_sale(self, item_id, quantity=1):
        """记录销售（增加需求信号）"""
        self.market.record_sale(item_id, quantity)
    
    def record_supply(self, item_id, quantity=1):
        """记录供给"""
        self.market.record_supply(item_id, quantity)
    
    def update_prices(self, market_building):
        """每日结算，更新价格"""
        self.market.update_prices(market_building)
    
    def get_price_trend(self, item_id):
        """获取价格趋势"""
        return self.market.get_price_trend(item_id)
    
    # ---- 商人贸易相关 ----
    def record_purchase(self, npc, item_id, quantity, cost_per_unit):
        """记录商人进货"""
        self.trade_manager.record_purchase(npc, item_id, quantity, cost_per_unit)
    
    def record_merchant_sale(self, npc, item_id, quantity, sell_price):
        """记录商人卖出，返回利润"""
        return self.trade_manager.record_sale(npc, item_id, quantity, sell_price)
    
    def get_merchant_profit(self, npc):
        """获取商人累计利润"""
        return self.trade_manager.get_profit(npc)


# ═══════════════════════════════════════════════════════════════════
# 全局经济系统实例
# ═══════════════════════════════════════════════════════════════════

_market_price_system = None
_merchant_trade_manager = None

def get_market_price_system():
    global _market_price_system
    if _market_price_system is None:
        _market_price_system = MarketPriceSystem()
    return _market_price_system

def get_merchant_trade_manager():
    global _merchant_trade_manager
    if _merchant_trade_manager is None:
        _merchant_trade_manager = MerchantTradeManager()
    return _merchant_trade_manager