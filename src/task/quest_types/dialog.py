# --- src/task/quest_types/dialog.py ---
"""DIALOG：纯对话任务（看一段剧情即完成）"""

from ._base import QuestType, register


@register
class DialogType(QuestType):
    name = "DIALOG"

    def objective_text(self, q):
        return ""  # 对话任务不需要"完成条件"文案

    def progress_text(self, q, player, all_cards):
        return ""
