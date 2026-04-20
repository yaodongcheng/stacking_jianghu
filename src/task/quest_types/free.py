# --- src/task/quest_types/free.py ---
"""FREE / GOAL：自动激活的占位/抽象任务（不需要找 NPC 接取）"""

from ._base import QuestType, register


@register
class FreeType(QuestType):
    name = "FREE"
    auto_activate = True


@register
class GoalType(QuestType):
    name = "GOAL"
    auto_activate = True
