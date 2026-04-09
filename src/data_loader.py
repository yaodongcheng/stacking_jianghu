# src/data_loader.py
import csv
import json
from src.entities import NPC
from src.utils import resource_path

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