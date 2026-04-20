# --- src/task/quest_types/wait_time.py ---
"""WAIT_TIME：等到指定时辰/时间点"""

from ._base import QuestType, register


@register
class WaitTimeType(QuestType):
    name = "WAIT_TIME"

    def objective_text(self, q):
        return f"等到 {q.target}"
