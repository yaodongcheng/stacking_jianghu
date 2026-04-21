# --- src/task/quest_types/consume.py ---
"""
CONSUME：累计使用/消费指定物品 N 次

策划须知：
====================================================================
quest_config.csv 写一行：
  type=CONSUME, target=<物品名>, count=<次数>
玩家在背包里点"吃"或"使用"该物品时累加进度，凑够 count 完成。
====================================================================
"""

from ._base import QuestType, register


def _progress_key(quest_id):
    return f'consume_{quest_id}'


@register
class ConsumeType(QuestType):
    name = "CONSUME"

    def objective_text(self, q):
        return f"使用 {q.target} ×{q.count}"

    def progress_text(self, q, player, all_cards):
        from src.task.quest_system import QuestManager
        qm = QuestManager.get_instance()
        if not qm:
            return f"(0/{q.count})" if q.count > 0 else ""
        current = qm.flags.get(_progress_key(q.id), 0)
        return f"({current}/{q.count})"

    def on_consumed(self, qm, item_id, count, player, ft_manager=None):
        """玩家在背包里使用了物品时调用。命中当前任务则累加进度。"""
        from src.definitions import QS_ACTIVE

        q = qm.get_current_quest()
        if not q or q.type != 'CONSUME':
            return False
        if qm.quest_status != QS_ACTIVE:
            return False
        if item_id != q.target:
            return False

        key = _progress_key(q.id)
        current = qm.flags.get(key, 0)
        new_count = min(current + count, q.count)
        qm.flags[key] = new_count

        remaining = q.count - new_count
        if ft_manager and player:
            if remaining > 0:
                ft_manager.add_text(
                    f"使用 {item_id} ({new_count}/{q.count})",
                    player.rect.centerx, player.rect.top - 60, (255, 215, 0),
                )
            else:
                ft_manager.add_text(
                    "目标完成！",
                    player.rect.centerx, player.rect.top - 60, (100, 255, 100),
                )
        print(f"[Quest] CONSUME 任务 {q.id}: {item_id} x{count} (进度: {new_count}/{q.count})")
        return True

    def is_goal_met(self, qm, quest):
        return qm.flags.get(_progress_key(quest.id), 0) >= quest.count
