# --- src/item_system.py ---
import csv
import os
from src.utils import resource_path

class ItemData:
    def __init__(self, data):
        self.id = data.get('id', '未知')
        self.type = data.get('type', 'MATERIAL')
        
        self.value = int(data.get('value') or 0)
        self.price = int(data.get('price') or self.value or 0)  # 市场交易价（默认等于 value）
        self.hunger_rec = int(data.get('hunger_rec') or 0)
        self.burn_time = int(data.get('burn_time') or 0)
        self.warm_val = int(data.get('warm_val') or 0)
        self.atk_bonus = int(data.get('atk_bonus') or 0)
        self.def_bonus = int(data.get('def_bonus') or 0)  # 新增防御加成
        self.buff_duration = int(data.get('buff_duration') or 0)  # 攻防 buff 持续秒数
        self.desc = data.get('desc', '')

class ItemManager:
    _instance = None

    def __init__(self):
        self.items = {} # {id: ItemData}
        self.load_data()

    @staticmethod
    def get_instance():
        if ItemManager._instance is None:
            ItemManager._instance = ItemManager()
        return ItemManager._instance

    def load_data(self):
        path = resource_path('data/items.csv')
        if not os.path.exists(path):
            print(f"Warning: {path} not found.")
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row['id']: continue
                    self.items[row['id']] = ItemData(row)
            print(f"[ItemSystem] Loaded {len(self.items)} items.")
        except Exception as e:
            print(f"[ItemSystem] Load Error: {e}")

    def get_data(self, item_id):
        return self.items.get(item_id, None)

    def is_food(self, item_id):
        data = self.get_data(item_id)
        return data and data.type == 'FOOD'

    def get_hunger_recovery(self, item_id):
        data = self.get_data(item_id)
        return data.hunger_rec if data else 0

    def is_fuel(self, item_id):
        data = self.get_data(item_id)
        return data and data.burn_time > 0

    def is_weapon(self, item_id):
        data = self.get_data(item_id)
        return data and data.type == 'WEAPON'

    def is_armor(self, item_id):
        data = self.get_data(item_id)
        return data and data.type == 'ARMOR'

    def is_clothing(self, item_id):
        data = self.get_data(item_id)
        return data and data.type == 'CLOTHING'

    def get_atk_bonus(self, item_id):
        data = self.get_data(item_id)
        return data.atk_bonus if data else 0

    def get_def_bonus(self, item_id):
        data = self.get_data(item_id)
        return data.def_bonus if data else 0

    def get_warm_val(self, item_id):
        data = self.get_data(item_id)
        return data.warm_val if data else 0

    def get_market_price(self, item_id):
        """返回物品在市场的固定价格（铜钱）"""
        data = self.get_data(item_id)
        return data.value if data else 0


def apply_food_effects(consumer, item_id):
    """把食物的所有效果立刻施加到 consumer (NPC/Player) 身上。

    饥饿(hunger_rec)与寒冷(warm_val)立即生效且永久；
    攻防加成(atk_bonus/def_bonus)按 buff_duration 秒挂临时 buff。

    Returns: dict 描述本次施加了哪些效果，供 UI 提示。空 dict 表示不是食物或没效果。
    """
    item_sys = ItemManager.get_instance()
    data = item_sys.get_data(item_id)
    if data is None:
        return {}

    applied = {}

    if data.hunger_rec > 0:
        old = getattr(consumer, 'hunger', 0)
        consumer.hunger = max(0, old - data.hunger_rec)
        applied['hunger'] = data.hunger_rec

    if data.warm_val > 0:
        old = getattr(consumer, 'cold', 0)
        consumer.cold = max(0, old - data.warm_val)
        applied['warm'] = data.warm_val

    if data.buff_duration > 0:
        duration_ms = data.buff_duration * 1000
        if data.atk_bonus > 0:
            # 同维度 buff 取较强值并刷新时长（不叠加，避免反复吃刷出离谱数值）
            if data.atk_bonus >= getattr(consumer, 'atk_buff', 0):
                consumer.atk_buff = data.atk_bonus
            consumer.atk_buff_remaining_ms = max(getattr(consumer, 'atk_buff_remaining_ms', 0), duration_ms)
            applied['atk_buff'] = data.atk_bonus
            applied['atk_buff_sec'] = data.buff_duration
        if data.def_bonus > 0:
            if data.def_bonus >= getattr(consumer, 'def_buff', 0):
                consumer.def_buff = data.def_bonus
            consumer.def_buff_remaining_ms = max(getattr(consumer, 'def_buff_remaining_ms', 0), duration_ms)
            applied['def_buff'] = data.def_bonus
            applied['def_buff_sec'] = data.buff_duration

    return applied
