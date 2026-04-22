# --- src/task/quest_types/eat.py ---
"""EAT：饥饿值降到阈值以下（"吃饱"任务）"""

from ._base import QuestType, register


@register
class EatType(QuestType):
    name = "EAT"

    def objective_text(self, q):
        return f"将饥饿值降到 {q.count} 以下"

    def current_value_text(self, q, player, all_cards):
        if player is None:
            return ""
        return str(int(getattr(player, 'hunger', 0)))

    def progress_text(self, q, player, all_cards):
        if player is None:
            return ""
        return f"（当前 {int(getattr(player, 'hunger', 0))}）"
