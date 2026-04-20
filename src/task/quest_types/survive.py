# --- src/task/quest_types/survive.py ---
"""SURVIVE：存活到指定天数"""

from ._base import QuestType, register


@register
class SurviveType(QuestType):
    name = "SURVIVE"

    def objective_text(self, q):
        return f"存活到第 {q.count} 天"
