# --- src/task/quest_types/deliver.py ---
"""
DELIVER：把指定物品交给某个 NPC

策划须知：
====================================================================
quest_config.csv 写一行：
  type=DELIVER, target=<物品名>, count=<数量>, submit_npc=<NPC名或ID>
玩家把物品堆到对应 NPC 身上时自动累加进度，凑够 count 触发 READY。
====================================================================
"""

from ._base import QuestType, register


def _progress_key(quest_id):
    """进度存放在 qm.flags 的哪个键下（goal_checkers 也读这里）"""
    return f'deliver_{quest_id}'


@register
class DeliverType(QuestType):
    name = "DELIVER"

    def objective_text(self, q):
        return f"向指定 NPC 交付 {q.target} ×{q.count}"

    def progress_text(self, q, player, all_cards):
        # 用 QuestManager 单例查 flag，不需要从外面传 manager
        from src.task.quest_system import QuestManager
        qm = QuestManager.get_instance()
        if not qm:
            return f"(0/{q.count})" if q.count > 0 else ""
        current = qm.flags.get(_progress_key(q.id), 0)
        return f"({current}/{q.count})"

    # ── 业务方法（被 QuestManager 委托调用）─────────────────────────

    def on_delivered(self, qm, item_type, item_count, target_npc, player, ft_manager=None):
        """玩家把物品堆到 NPC 上时调用。命中任务则消耗物品并累加进度。

        Returns:
            bool: True 表示是有效任务交付（外部应消耗物品卡）
        """
        from src.definitions import QS_ACTIVE

        q = qm.get_current_quest()
        if not q or q.type != 'DELIVER':
            return False
        if qm.quest_status != QS_ACTIVE:
            return False
        if item_type != q.target:
            return False

        npc_name = getattr(target_npc, 'name', '')
        npc_id = getattr(target_npc, 'id', None)
        if not qm._match_submit_npc(npc_id, npc_name, q.submit_npc):
            return False

        key = _progress_key(q.id)
        current_count = qm.flags.get(key, 0)
        new_count = min(current_count + item_count, q.count)
        qm.flags[key] = new_count

        remaining = q.count - new_count

        if ft_manager:
            if remaining > 0:
                ft_manager.add_text(
                    f"交付 {item_type} ({new_count}/{q.count})",
                    target_npc.rect.centerx, target_npc.rect.top - 30, (255, 215, 0),
                )
            else:
                ft_manager.add_text(
                    "交付完成！",
                    target_npc.rect.centerx, target_npc.rect.top - 30, (100, 255, 100),
                )

        print(f"[Quest] 交付任务 {q.id}: {item_type} x{item_count} -> {npc_name} "
              f"(进度: {new_count}/{q.count})")
        return True

    def get_progress(self, qm, quest_id=None):
        """查询交付进度。返回 (current, total)；非 DELIVER 任务返回 (0, 0)。"""
        if quest_id is None:
            q = qm.get_current_quest()
            if not q or q.type != 'DELIVER':
                return 0, 0
            quest_id = q.id
        else:
            q = qm.quests.get(quest_id)

        if not q:
            return 0, 0

        current = qm.flags.get(_progress_key(quest_id), 0)
        return current, q.count

    def is_goal_met(self, qm, quest):
        """供 goal_checkers 委托使用：进度凑够即完成"""
        return qm.flags.get(_progress_key(quest.id), 0) >= quest.count
