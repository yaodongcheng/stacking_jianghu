# src/data_loader.py
import csv
import json
import random
import pygame
from src.entities import NPC, Building, Resource
from src.utils import resource_path
from src.definitions import CARD_W, CARD_H, ITEM_GRAIN, ITEM_COIN, ITEM_BERRY, ITEM_WOOD, SCENARIO_SANDBOX, SCENARIO_TUTORIAL

# 全局 NPC ID -> Name 映射表（运行时动态维护）
NPC_ID_NAME_MAP = {}

def register_npc_id_name(npc_id, npc_name):
    """注册 NPC ID 和名字的映射关系"""
    NPC_ID_NAME_MAP[str(npc_id)] = npc_name

def get_npc_name_by_id_global(npc_id):
    """
    根据 NPC ID 获取名字（通用函数）
    
    查询顺序：
    1. 运行时加载的 NPC（从 CSV 或动态生成）
    2. 种子 NPC（从 character_seeds.py）
    3. 特殊 ID
    """
    npc_id_str = str(npc_id)
    
    # 1. 优先从运行时映射表中查找
    if npc_id_str in NPC_ID_NAME_MAP:
        return NPC_ID_NAME_MAP[npc_id_str]
    
    # 2. 从种子 NPC 中查找（task 模块的 ID_TO_NAME）
    from src.task import ID_TO_NAME
    if npc_id_str in ID_TO_NAME:
        return ID_TO_NAME[npc_id_str]
    
    # 3. 特殊 ID 处理
    if npc_id_str == '9999':
        return '（自动完成）'
    if npc_id_str == '9000':
        return '未指定'
    if npc_id_str == '0' or npc_id_str == '':
        return '玩家'
    
    # 4. 默认返回 ID 本身
    return f'NPC({npc_id})'

def clear_npc_id_name_map():
    """清空映射表（用于重新加载游戏时）"""
    NPC_ID_NAME_MAP.clear()


def get_npc_id_by_name_global(npc_name: str):
    """
    根据 NPC 名字获取 ID（通用函数）
    
    查询顺序：
    1. 运行时加载的 NPC（从 NPC_ID_NAME_MAP 反向查找）
    2. 种子 NPC（从 character_seeds.py）
    
    Args:
        npc_name: NPC 名字
        
    Returns:
        int or None: NPC ID，未找到返回 None
    """
    if not npc_name:
        return None
    
    # 1. 从运行时映射表中反向查找
    for npc_id_str, name in NPC_ID_NAME_MAP.items():
        if name == npc_name:
            return int(npc_id_str)
    
    # 2. 从种子 NPC 中反向查找
    from src.task import ID_TO_NAME
    for npc_id_str, name in ID_TO_NAME.items():
        if name == npc_name:
            return int(npc_id_str)
    
    return None

def load_npcs_from_csv(filepath):
    npcs = []
    try:
        path = resource_path(filepath)
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            # 读取所有行
            rows = list(reader)
            
            if len(rows) < 4:
                return []
            
            # 第一行是 keys (英文表头)
            keys = rows[0]
            
            # 从第四行开始是数据 (索引为3)
            data_rows = rows[3:]
            
            for row in data_rows:
                if not row: continue # 跳过空行
                
                # 将 key 和 value 组合成字典
                # 比如 {'id': '101', 'name': '张三', ...}
                row_data = dict(zip(keys, row))
                
                # 解析 JSON 字段 (personality 和 initial_dilemma)
                # 将 personality_json 解析为 personality 对象
                personality_json = row_data.pop('personality_json', '{}')
                if personality_json and personality_json != '{}':
                    try:
                        row_data['personality'] = json.loads(personality_json)
                    except json.JSONDecodeError:
                        row_data['personality'] = None
                else:
                    row_data['personality'] = None
                
                # 将 initial_dilemma_json 解析为 initial_dilemma 对象
                dilemma_json = row_data.pop('initial_dilemma_json', '{}')
                if dilemma_json and dilemma_json != '{}':
                    try:
                        row_data['initial_dilemma'] = json.loads(dilemma_json)
                    except json.JSONDecodeError:
                        row_data['initial_dilemma'] = None
                else:
                    row_data['initial_dilemma'] = None
                
                # 创建 NPC 对象
                new_npc = NPC(row_data)
                npcs.append(new_npc)
                
                # 【新增】注册到全局 ID->Name 映射表
                npc_id = row_data.get('id')
                npc_name = row_data.get('name', '无名氏')
                if npc_id:
                    register_npc_id_name(npc_id, npc_name)
                
    except FileNotFoundError:
        print(f"错误: 找不到文件 {filepath}")
    except Exception as e:
        print(f"读取 CSV 出错: {e}")
        
    return npcs

def load_raw_npc_data(filepath):
    """
    读取原始字典数据，用于 EventManager 或生成流民。
    跳过 header 的类型行和中文名行。
    """
    data_list = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # 安全跳过 header 描述行
            try:
                # 你的CSV格式: Row0=Keys, Row1=Types, Row2=CN_Headers
                # DictReader 已经消耗了 Row0 作为 fieldnames
                next(reader) # 跳过 Types
                next(reader) # 跳过 CN Headers
            except StopIteration:
                pass 

            for row in reader:
                if not row or not row.get('id'): continue
                data_list.append(dict(row))
                
    except Exception as e:
        print(f"[DataLoader] Error loading raw NPC data: {e}")
        # 兜底数据
        data_list.append({
            'id': 999, 'name': '流民', 'job': 'NONE', 
            'eco_status': 'POOR', 'body_img': 'body_01.png', 'head_img': 'head_01.png'
        })
    return data_list


# ════════════════════════════════════════════════════════════════
# 建筑配置 CSV 加载
# ════════════════════════════════════════════════════════════════

# CSV 物品名 → 代码常量映射
_ITEM_NAME_MAP = {
    '谷物': ITEM_GRAIN, '铜钱': ITEM_COIN,
    '浆果': ITEM_BERRY, '木材': ITEM_WOOD,
    '棉袄': '棉袄',
}


def _parse_inventory(inv_str):
    """解析库存字符串，如 '谷物:10;棉袄:5' → {ITEM_GRAIN: 10, '棉袄': 5}"""
    if not inv_str:
        return {}
    result = {}
    for part in inv_str.split(';'):
        part = part.strip()
        if ':' not in part:
            continue
        name, count_str = part.split(':', 1)
        name = name.strip()
        item_key = _ITEM_NAME_MAP.get(name, name)
        result[item_key] = int(count_str.strip() or 0)
    return result


def _precompute_zones(world_map):
    """
    根据 world_map 几何预计算所有 zone 的基础坐标。
    返回 dict: zone_key → (base_x, base_y)
    """
    cr = world_map.city_rect
    safe_margin = 120
    safe_left = cr.left + safe_margin
    safe_top = cr.top + safe_margin
    safe_right = cr.right - safe_margin
    safe_bot = cr.bottom - safe_margin

    # 城内3x3网格
    col_step = (safe_right - safe_left) // 3
    row_step = (safe_bot - safe_top) // 3
    city_grid = [
        (safe_left + col_step * c + col_step // 2,
         safe_top + row_step * r + row_step // 2)
        for r in range(3) for c in range(3)
    ]

    zones = {
        '_safe': (safe_left, safe_top, safe_right, safe_bot),
        '_col_step': col_step,
        '_row_step': row_step,
    }

    # 城内网格槽位
    for i, pos in enumerate(city_grid):
        zones[f'CITY_GRID:{i}'] = pos

    # 城门中心
    for direction in ('EAST', 'WEST', 'NORTH', 'SOUTH'):
        gate = world_map.gates.get(direction)
        if gate:
            zones[f'GATE:{direction}'] = (gate.centerx, gate.centery)

    # 城内象限
    zones['CITY:N'] = (cr.centerx, safe_top + row_step // 4)
    zones['CITY:S'] = (cr.centerx, safe_bot - row_step // 4)
    zones['CITY:SE'] = (safe_right - col_step // 3, safe_bot - row_step // 3)
    zones['CITY:NE'] = (safe_right - col_step // 3, safe_top + row_step // 3)
    zones['CITY:NW'] = (safe_left + col_step // 3, safe_top + row_step // 3)
    zones['CITY:SW'] = (safe_left + col_step // 3, safe_bot - row_step // 3)

    # 城外四角
    zones['NW'] = (cr.left - 400, cr.top - 300)
    zones['SW'] = (cr.left - 350, cr.bottom + 250)
    zones['NE'] = (cr.right + 300, cr.top - 250)
    zones['SE'] = (cr.right + 350, cr.bottom + 200)

    # 农田位置
    farm_margin = 100
    zones['FARM:W'] = (cr.left - farm_margin - 80, cr.centery)
    zones['FARM:N'] = (cr.centerx, cr.top - farm_margin - 80)
    zones['FARM:S'] = (cr.centerx, cr.bottom + farm_margin + 80)
    zones['FARM:NW'] = (cr.left - farm_margin - 150, cr.top - farm_margin - 50)
    zones['FARM:SW'] = (cr.left - farm_margin - 150, cr.bottom + farm_margin + 50)

    # 城市中心（CITY zone 的随机范围用 _safe 区域）
    zones['CITY'] = (cr.centerx, cr.centery)

    return zones


def _resolve_position(zone_str, offset_x, offset_y, spread, zone_data, world_map):
    """将 zone 标识 + 偏移量解析为实际 (x, y) 坐标。"""
    safe_left, safe_top, safe_right, safe_bot = zone_data['_safe']

    if zone_str == 'CITY':
        # 城内随机
        bx = random.randint(safe_left + 30, safe_right - 30)
        by = random.randint(safe_top + 30, safe_bot - 30)
    elif zone_str == 'WILD':
        # 城外荒野随机
        cr = world_map.city_rect
        _safe_dist = 600
        _outer_zones = []
        if cr.top > _safe_dist + 100:
            _outer_zones.append((cr.left, world_map.w - 50, 50, cr.top - _safe_dist))
        if world_map.h - cr.bottom > _safe_dist + 100:
            _outer_zones.append((50, world_map.w - 50, cr.bottom + _safe_dist, world_map.h - 50))
        if cr.left > _safe_dist + 100:
            _outer_zones.append((50, cr.left - _safe_dist, 50, world_map.h - 50))
        if world_map.w - cr.right > _safe_dist + 200:
            _outer_zones.append((cr.right + _safe_dist + 100, world_map.w - 50, 50, world_map.h - 50))
        _outer_zones = [(x0, x1, y0, y1) for x0, x1, y0, y1 in _outer_zones
                        if x1 - x0 > 100 and y1 - y0 > 100]
        if _outer_zones:
            z = random.choice(_outer_zones)
            bx, by = random.randint(z[0], z[1]), random.randint(z[2], z[3])
        else:
            bx = random.randint(50, 200)
            by = random.randint(world_map.h - 200, world_map.h - 50)
    elif zone_str == 'SLUM':
        rect = world_map.slum_rect
        bx = random.randint(rect.left + 30, rect.right - 30)
        by = random.randint(rect.top + 30, rect.bottom - 30)
    elif zone_str in zone_data:
        bx, by = zone_data[zone_str]
    else:
        print(f"[BuildingCSV] 未知 zone: {zone_str}，使用城市中心")
        bx, by = zone_data.get('CITY', (safe_left + 200, safe_top + 200))

    # 应用偏移
    bx += offset_x
    by += offset_y

    # 应用随机散布
    if spread > 0:
        bx += random.randint(-spread, spread)
        by += random.randint(-spread, spread)

    # 限制在世界边界内
    bx = max(60, min(bx, world_map.w - 60))
    by = max(60, min(by, world_map.h - 60))

    return int(bx), int(by)


def load_buildings_from_csv(filepath, world_map, scenario_type):
    """
    从 CSV 加载所有建筑定义。

    Returns:
        (cards, org_workplace_refs, npc_home_map, market_pos)
        - cards: Building / Resource 对象列表
        - org_workplace_refs: {org_id: Building} 组织工作建筑
        - npc_home_map: {npc_id_str: Building} NPC 独立住所
        - market_pos: (x, y) 主市场位置（用于散落资源定位）
    """
    from src.world_loader import find_valid_building_position

    cards = []
    org_workplace_refs = {}   # org_id → Building (工作场所)
    npc_home_map = {}         # npc_id_str → Building (住所)
    market_pos = None         # 主市场坐标
    zone_data = _precompute_zones(world_map)

    # 场景名映射
    scenario_name = 'SANDBOX' if scenario_type == SCENARIO_SANDBOX else 'TUTORIAL'

    try:
        path = resource_path(filepath)
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)

        if len(rows) < 4:
            print(f"[BuildingCSV] CSV 行数不足: {len(rows)}")
            return cards, org_workplace_refs, npc_home_map, market_pos

        keys = rows[0]

        for row in rows[3:]:
            if not row or not row[0].strip():
                continue

            # 补齐缺失列
            while len(row) < len(keys):
                row.append('')
            data = dict(zip(keys, row))

            # 场景过滤
            row_scenario = data.get('scenario', '').strip()
            if row_scenario and row_scenario != scenario_name:
                continue

            bid = data['id'].strip()
            building_type = data['building_type'].strip()
            zone_str = data.get('zone', 'CITY').strip()
            offset_x = int(data.get('offset_x') or 0)
            offset_y = int(data.get('offset_y') or 0)
            spread = int(data.get('spread') or 0)
            owner_type = data.get('owner_type', '').strip()
            owner_id = data.get('owner_id', '').strip()
            is_home = data.get('is_home', '0').strip() == '1'
            inventory_str = data.get('inventory', '').strip()

            # MARKET_NEAR 特殊处理：相对于主市场位置
            if zone_str == 'MARKET_NEAR' and market_pos:
                zone_data['MARKET_NEAR'] = market_pos

            # 解析位置
            bx, by = _resolve_position(zone_str, offset_x, offset_y, spread, zone_data, world_map)

            # 防重叠（资源点和住房用 find_valid_building_position）
            if building_type in ('BUSH', 'TREE', 'MINE', 'FISHPOND', 'HOUSE', 'FARM'):
                bx, by = find_valid_building_position(bx, by, cards, world_map, spread=max(spread, 80))

            # 散落资源（RESOURCE 类型）
            if building_type == 'RESOURCE':
                inv = _parse_inventory(inventory_str)
                for item_type, count in inv.items():
                    res = Resource(bx, by, item_type, count=count)
                    cards.append(res)
                continue

            # 创建建筑
            bld = Building(bx, by, building_type)

            # 设置库存
            if inventory_str:
                bld.inventory = _parse_inventory(inventory_str)

            # 记录主市场位置
            if bid == 'B_MARKET_MAIN':
                market_pos = (bx, by)

            # 所有者映射
            if owner_type == 'ORG' and owner_id:
                for oid in owner_id.split(';'):
                    oid = oid.strip()
                    if oid:
                        org_workplace_refs[oid] = bld

            if owner_type == 'NPC' and owner_id and is_home:
                npc_home_map[owner_id.strip()] = bld

            cards.append(bld)

        print(f"[BuildingCSV] 加载完成: {len(cards)} 个建筑/资源, "
              f"{len(org_workplace_refs)} 个组织工作点, {len(npc_home_map)} 个NPC住所")

    except FileNotFoundError:
        print(f"[BuildingCSV] 找不到文件: {filepath}")
    except Exception as e:
        import traceback
        print(f"[BuildingCSV] 加载出错: {e}")
        traceback.print_exc()

    return cards, org_workplace_refs, npc_home_map, market_pos