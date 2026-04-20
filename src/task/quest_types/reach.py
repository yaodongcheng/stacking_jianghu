# --- src/task/quest_types/reach.py ---
"""REACH：到达指定地点"""

from ._base import QuestType, register


@register
class ReachType(QuestType):
    name = "REACH"

    def objective_text(self, q):
        return f"到达 {q.target}"
