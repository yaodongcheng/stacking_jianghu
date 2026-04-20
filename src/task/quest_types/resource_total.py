# --- src/task/quest_types/resource_total.py ---
"""RESOURCE_TOTAL：累积资源（铜钱、声望等）达到阈值"""

from ._base import QuestType, register


# 资源类型显示名映射
RESOURCE_DISPLAY = {
    'MONEY': '铜钱',
    'FAME': '声望',
}


def _player_resource(player, target):
    """读取玩家当前的指定资源数。"""
    if target == 'MONEY':
        return getattr(player, 'money', 0)
    if target == 'FAME':
        return getattr(player, 'fame', 0)
    return 0


@register
class ResourceTotalType(QuestType):
    name = "RESOURCE_TOTAL"
    auto_activate = True  # 这类任务自动激活，不需要找 NPC 接取

    def objective_text(self, q):
        unit = RESOURCE_DISPLAY.get(q.target, q.target)
        return f"{unit}累积达到 {q.count}"

    def progress_text(self, q, player, all_cards):
        return f"({_player_resource(player, q.target)}/{q.count})"
