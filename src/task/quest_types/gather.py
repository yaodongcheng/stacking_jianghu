# --- src/task/quest_types/gather.py ---
"""GATHER：采集类任务（砍树、采浆果、捕鱼...）"""

from ._base import QuestType, register


# 教学阶段的任务 ID（在这些任务进行时，玩家不能做与目标无关的事）
# 策划想加入新教学任务：1) 加进这里 或 2) 在 quest_config.csv 的 desc 写 [STRICT]
STRICT_TUTORIAL_QUESTS = {
    'Q0_FIND_ELDER', 'Q1_FOOD', 'Q2_WOOD', 'Q3_CAMPFIRE',
}


@register
class GatherType(QuestType):
    name = "GATHER"

    def objective_text(self, q):
        return f"采集 {q.target} ×{q.count}"

    def _count_owned(self, q, player, all_cards):
        n = player.inventory.get(q.target, 0)
        for c in all_cards:
            if getattr(c, 'is_follower', False):
                n += c.inventory.get(q.target, 0)
        return n

    def current_value_text(self, q, player, all_cards):
        if player is None:
            return ""
        return str(self._count_owned(q, player, all_cards))

    def progress_text(self, q, player, all_cards):
        return f"（当前 {self._count_owned(q, player, all_cards)}）"

    def can_act(self, q, dragged_card, target_card, recipe_mgr=None):
        # A. 直接操作目标物品（整理背包、合并堆叠）
        drag_type = getattr(dragged_card, 'item_type', '')
        if drag_type == q.target:
            return True, ""
        target_type = getattr(target_card, 'item_type', '')
        if target_type == q.target:
            return True, ""

        # 特例：浆果与灌木丛的直接采集
        if q.target == '浆果' and getattr(target_card, 'building_type', '') == 'BUSH':
            return True, ""

        # B. 配方预测：两卡互动会产出任务目标
        if recipe_mgr:
            recipe = recipe_mgr.check_match(dragged_card, target_card)
            if recipe and q.target in recipe.data.get('output', ''):
                return True, ""

        # C. 严格教学模式：玩家在做与任务无关的事
        is_strict = q.id in STRICT_TUTORIAL_QUESTS or '[STRICT]' in q.desc
        if is_strict:
            return False, f"教学阶段，请专注于：{q.target}"

        return True, ""
