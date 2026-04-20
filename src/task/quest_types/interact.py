# --- src/task/quest_types/interact.py ---
"""INTERACT：与指定 NPC 交互"""

from ._base import QuestType, register


@register
class InteractType(QuestType):
    name = "INTERACT"

    def objective_text(self, q):
        return f"与 {q.target} 交互"

    def progress_text(self, q, player, all_cards):
        return ""

    def can_act(self, q, dragged_card, target_card, recipe_mgr=None):
        target_id = str(getattr(target_card, 'id', ''))
        if target_id == q.target:
            return True, ""
        return False, "请先与目标人物交谈"
