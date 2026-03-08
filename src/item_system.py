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
