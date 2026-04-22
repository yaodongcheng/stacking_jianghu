# --- src/task/quest_types/have_unit.py ---
"""HAVE_UNIT：拥有指定单位类型的任务（如 拥有 ARCHER ×3）"""

from ._base import QuestType, register


@register
class HaveUnitType(QuestType):
    name = "HAVE_UNIT"

    def objective_text(self, q):
        return f"拥有 {q.target} ×{q.count}"

    def _count_owned(self, q, all_cards):
        return sum(
            1 for c in all_cards
            if (getattr(c, 'job', '') if hasattr(c, 'job') else getattr(c, 'building_type', '')) == q.target
        )

    def current_value_text(self, q, player, all_cards):
        return str(self._count_owned(q, all_cards))

    def progress_text(self, q, player, all_cards):
        return f"（当前 {self._count_owned(q, all_cards)}）"
