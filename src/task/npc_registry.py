# --- src/task/npc_registry.py ---
"""
NPC 名字 ↔ ID 映射表（项目唯一）

策划须知：
- NPC 的 ID 来自 data/npc_data.csv 的 id 列，是项目里唯一的 NPC 标识
- 想新增 NPC：直接在 npc_data.csv 加一行，重启游戏即可被识别
- 别名（如"泼皮"→"泼皮牛二"）在 ALIASES 里加，方便对话脚本里写简称
- 特殊 ID：9999 = 玩家、9998 = 玩家随从（玩家命名，不在 csv）

代码须知：
- 模块 import 时立即从 csv 读取并构建映射；DialogData 等使用方在模块加载完
  即可正确解析 speaker_id，不依赖运行时的延迟注册
"""

import csv

from src.utils import resource_path


# ======================== 特殊 NPC ID ========================
ID_VILLAGE_HEAD = 9000   # 村长（也存在于 npc_data.csv，但保留常量给代码引用）
ID_FOLLOWER = 9998       # 玩家随从（玩家命名，运行时创建）
ID_PLAYER = 9999         # 玩家自己


# ======================== 名字别名表 ========================
# 策划想给某个 NPC 加别名/兼容旧脚本，加到这里
ALIASES = {
    '泼皮': '泼皮牛二',
    '泼皮甲': '泼皮牛二',
    '泼皮乙': '泼皮狗蛋',
}


# ======================== 主映射表（从 npc_data.csv 构建） ========================
NAME_TO_ID = {}
ID_TO_NAME = {}


def _load_from_csv():
    """模块 import 时调用，从 npc_data.csv 填充映射。
    csv 前 3 行是 header（英文字段名 / 类型 / 中文名），第 4 行起是数据。
    """
    try:
        path = resource_path('data/npc_data.csv')
        with open(path, 'r', encoding='utf-8') as f:
            rows = list(csv.reader(f))
    except FileNotFoundError:
        print(f"[npc_registry] 找不到 data/npc_data.csv，NPC 映射表为空")
        return

    if len(rows) < 4:
        return

    keys = rows[0]
    try:
        id_idx = keys.index('id')
        name_idx = keys.index('name')
    except ValueError:
        print(f"[npc_registry] npc_data.csv header 缺少 id/name 列")
        return

    for row in rows[3:]:
        if not row or len(row) <= max(id_idx, name_idx):
            continue
        npc_id_raw = row[id_idx].strip()
        name = row[name_idx].strip()
        if not npc_id_raw or not name:
            continue
        try:
            npc_id = int(npc_id_raw)
        except ValueError:
            print(f"[npc_registry] 跳过非整型 id: {npc_id_raw} ({name})")
            continue
        if name in NAME_TO_ID and NAME_TO_ID[name] != npc_id:
            print(f"[npc_registry] 警告：NPC 重名 '{name}'，新 id={npc_id} 覆盖旧 id={NAME_TO_ID[name]}")
        NAME_TO_ID[name] = npc_id
        ID_TO_NAME[str(npc_id)] = name


_load_from_csv()

# 玩家固定别名
NAME_TO_ID['我'] = ID_PLAYER
ID_TO_NAME[str(ID_PLAYER)] = '玩家'

# 别名映射到真名 ID
for alias, real_name in ALIASES.items():
    if real_name in NAME_TO_ID:
        NAME_TO_ID[alias] = NAME_TO_ID[real_name]


# ======================== 查询函数 ========================
def get_speaker_id(name: str):
    """名字 → NPC ID。找不到返回 None。"""
    return NAME_TO_ID.get(name, None)


def get_npc_name_by_id(npc_id) -> str:
    """NPC ID → 名字，用于 UI 显示。"""
    npc_id_str = str(npc_id)
    if npc_id_str == str(ID_PLAYER):
        return '（自动完成）'
    return ID_TO_NAME.get(npc_id_str, f'NPC({npc_id})')


def resolve_npc_display_name(npc_id_or_name) -> str:
    """既支持 ID 也支持名字，返回显示用名字。

    - 数字 ID → 查 ID_TO_NAME
    - 已知名字 → 直接返回
    - 都不是 → 原样返回
    """
    if not npc_id_or_name:
        return '未指定'
    s = str(npc_id_or_name)
    if s.isdigit() or s in ID_TO_NAME:
        return get_npc_name_by_id(s)
    if s in NAME_TO_ID:
        return s
    return s
