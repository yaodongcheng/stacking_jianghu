# --- src/task/quest_types/recruit.py ---
"""RECRUIT：招募指定 NPC"""

from ._base import QuestType, register


@register
class RecruitType(QuestType):
    name = "RECRUIT"

    def objective_text(self, q):
        return f"招募 {q.target}"

    def progress_text(self, q, player, all_cards):
        return "(进行中)"
