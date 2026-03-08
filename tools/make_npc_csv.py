# --- tools/make_npc_csv.py ---
import csv
import os
import sys
import json

# 添加项目根目录到路径以便导入 src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.character_seeds import SEEDS, ORGS, POWER_TYPES, ORGANIZATIONS

os.makedirs('../data', exist_ok=True)
filepath = '../data/npc_data.csv'

# 1. 第一遍扫描：分配 ID 并建立 Name->ID 映射
name_to_id = {}
current_id = 1000

for npc in SEEDS:
    npc['id'] = current_id
    name_to_id[npc['name']] = current_id
    current_id += 1

print(f"Assign IDs for {len(SEEDS)} characters. Max ID: {current_id-1}")

# 2. 第二遍扫描：解析关系 (将名字转换为 ID)
final_rows = []

# 定义 CSV 表头 - 增加新的社会分层字段
headers = [
    ['id', 'name', 'job', 'hidden_job', 'head_img', 'body_img', 
     'eco_status', 'soc_status', 'freedom', 'emotion', 
     'tags', 'safety', 'org_id', 'rank', 'relations_json', 'desc',
     'power_type', 'org_role', 'social_level', 'wealth_level', 'influence_level'],
     
    ['int', 'str', 'enum', 'str', 'str', 'str', 
     'enum', 'enum', 'enum', 'enum', 
     'list', 'enum', 'str', 'int', 'json', 'str',
     'str', 'str', 'int', 'int', 'int'],
     
    ['编号', '姓名', '当前职业', '潜能职业', '头图', '身图', 
     '经济', '地位', '自由', '心情', 
     '标签', '安全', '组织ID', '职级', '关系数据', '描述',
     '势力类型', '组织角色', '社会等级', '财富等级', '影响力等级']
]

for npc in SEEDS:
    # --- 基础属性 ---
    pid = npc['id']
    name = npc['name']
    
    # --- 新的社会分层属性处理 (先读取，后面需要用) ---
    power_type = npc.get('power_type', '民')  # 势力类型
    social_level = npc.get('social_level', 1)  # 社会等级
    org_role = npc.get('org_role', 'MEMBER')   # 组织角色
    
    # 根据势力类型和组织角色推断职业
    # power_type → job 映射
    power_to_job = {
        '士': 'OFFICIAL',   # 官员
        '农': 'FARMER',     # 农民/地主
        '工': 'ARTISAN',    # 工匠
        '商': 'MERCHANT',   # 商人
        '学': 'SCHOLAR',    # 学者
        '兵': 'GUARD',      # 护卫/军人
        '游': 'THUG',       # 江湖人士
        '匪': 'BANDIT',     # 土匪
    }
    
    # 特殊角色覆盖
    if org_role == 'BODYGUARD':
        job = 'GUARD'  # 护卫优先
    elif 'MONK' in npc.get('tags', []):
        job = 'MONK'   # 和尚
    else:
        job = power_to_job.get(power_type, 'NONE')
    
    hidden_job = npc.get('hidden_job', 'NONE')
    
    # 图像资源映射 (简单根据性别分配)
    gender = npc.get('gender', 'Male')
    head_img = 'head_02.png' if gender == 'Female' else 'head_01.png'
    body_img = 'body_02.png' if gender == 'Female' else 'body_01.png'
    
    # 根据社会分层和势力类型计算经济和社会地位
    wealth_level = npc.get('wealth_level', 1)
    influence_level = npc.get('influence_level', 1)
    
    # 推算经济状态
    if wealth_level >= 4: eco = 'RICH'
    elif wealth_level >= 3: eco = 'ENOUGH'  
    elif wealth_level >= 2: eco = 'COMMON'
    else: eco = 'POOR'
    
    # 推算社会地位
    if social_level >= 4: soc = 'NOBLE'
    elif social_level >= 3: soc = 'HIGH'
    elif social_level >= 2: soc = 'COMMON'
    else: soc = 'LOW'
    
    # 其他状态
    free = 'FULL'
    emo = 'NORMAL'
    safe = 'NORMAL'
    
    # 标签处理
    tags = npc.get('tags', [])
    tags_str = ";".join(tags)
    
    # 组织信息 - 兼容旧字段
    org_id = npc.get('org_id', npc.get('org', None))
    if org_id is None:
        org = 'NONE'
    else:
        org = org_id  # 使用新的org_id字段
    
    rank = npc.get('org_rank', npc.get('rank', 0))  # 兼容新旧字段
    
    # --- 关键：关系解析 ---
    # 将 {'FATHER': '张三'} 转换为 {'FATHER': 1001}
    raw_rels = npc.get('relations', {})
    processed_rels = {}
    for rel_type, target_name in raw_rels.items():
        if target_name in name_to_id:
            target_id = name_to_id[target_name]
            processed_rels[rel_type] = target_id
        else:
            print(f"Warning: Relation target '{target_name}' not found for {name}")
    
    # 序列化为 JSON 字符串存储到 CSV
    rels_json = json.dumps(processed_rels)
    
    desc = npc.get('desc', '')

    row = [
        pid, name, job, hidden_job, head_img, body_img,
        eco, soc, free, emo,
        tags_str, safe, org, rank, rels_json, desc,
        power_type, org_role, social_level, wealth_level, influence_level
    ]
    final_rows.append(row)

# 写入文件
try:
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(headers)
        writer.writerows(final_rows)
    print(f"Successfully generated {filepath} with Social Relations.")
except Exception as e:
    print(f"Error: {e}")