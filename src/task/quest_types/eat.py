# --- src/task/quest_types/eat.py ---
"""EAT：饥饿值降到阈值以下（"吃饱"任务）"""

from ._base import QuestType, register


@register
class EatType(QuestType):
    name = "EAT"

    def objective_text(self, q):
        return f"将饥饿值降到 {q.count} 以下"

    def progress_text(self, q, player, all_cards):
        # 进度归生存卡管，主线 text 只讲"怎么做"，不附带饥饿值
        return ""
