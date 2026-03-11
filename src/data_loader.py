# src/data_loader.py
import csv
import json
from src.entities import NPC
from src.utils import resource_path

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