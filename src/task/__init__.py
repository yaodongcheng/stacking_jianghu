# --- src/task/__init__.py ---
"""
任务系统模块

提供统一的任务基类和具体任务类型，供整个游戏使用。
包含 quest_system 的所有功能（QuestManager、QuestData、DialogData等）
"""

from .base import (
    TaskBase,
    TaskStatus,
    TaskCategory,
    TaskContentType,
    TASK_PRIORITY as _TASK_PRIORITY_ENUM,
    TASK_TYPE_STYLES as _TASK_TYPE_STYLES_ENUM,
)
from .display import TaskDisplayData
from .survival import SurvivalTask
from .intel import IntelQuest
from .quest_instance import QuestInstance

# 向后兼容：从 quest_system 导出的常量
from .quest_system import (
    TASK_TYPE_MAIN,
    TASK_TYPE_SURVIVAL,
    TASK_TYPE_INTEL,
    TASK_TYPE_FACTION,
    TaskDisplayData as _TaskDisplayData,  # 已在上面导出，这里用别名避免重复
    QuestData,
    DialogData,
    QuestManager,
    NAME_TO_ID,
    ID_TO_NAME,
    get_speaker_id,
    get_npc_name_by_id,
)

# ======================== 向后兼容：字符串键版本的常量 ========================
# sidebar.py 等UI代码使用字符串键（"MAIN", "SURVIVAL"等）查找样式
# 因此需要提供字符串键版本的字典

TASK_PRIORITY = {k.value: v for k, v in _TASK_PRIORITY_ENUM.items()}
TASK_TYPE_STYLES = {k.value: v for k, v in _TASK_TYPE_STYLES_ENUM.items()}

# 同时导出枚举版本（供需要类型提示的代码使用）
TASK_PRIORITY_ENUM = _TASK_PRIORITY_ENUM
TASK_TYPE_STYLES_ENUM = _TASK_TYPE_STYLES_ENUM

__all__ = [
    # 基类
    'TaskBase',
    'TaskStatus',
    'TaskCategory',
    'TaskContentType',
    'TASK_PRIORITY',
    'TASK_TYPE_STYLES',
    # 显示数据
    'TaskDisplayData',
    # 具体任务类型
    'SurvivalTask',
    'IntelQuest',
    'QuestInstance',
    # quest_system 兼容导出
    'TASK_TYPE_MAIN',
    'TASK_TYPE_SURVIVAL',
    'TASK_TYPE_INTEL',
    'TASK_TYPE_FACTION',
    'QuestData',
    'DialogData',
    'QuestManager',
    'NAME_TO_ID',
    'ID_TO_NAME',
    'get_speaker_id',
    'get_npc_name_by_id',
]
