# --- src/task/quest_types/combat.py ---
"""COMBAT：击败指定目标"""

from ._base import QuestType, register


@register
class CombatType(QuestType):
    name = "COMBAT"

    def objective_text(self, q):
        return f"击败 {q.target}"

    def progress_text(self, q, player, all_cards):
        return "(进行中)"
