# --- src/task/actions/_helpers.py ---
"""
Action handler 通用工具函数

提取自 quest_system.py 中反复出现的模式，供各 action 模块复用。
"""

import math


def find_npc_by_id(all_cards, npc_id):
    """根据 ID 在 all_cards 中查找 NPC，返回 card 或 None"""
    npc_id = int(npc_id)
    for card in all_cards:
        if getattr(card, 'id', None) == npc_id:
            return card
    return None


def find_npc_by_name(all_cards, name):
    """根据名字在 all_cards 中查找 NPC，返回第一个匹配项或 None"""
    for card in all_cards:
        if hasattr(card, 'name') and card.name == name:
            return card
    return None


def find_npcs_by_names(all_cards, names):
    """根据名字列表在 all_cards 中批量查找 NPC，返回 {name: card} 字典"""
    result = {}
    name_set = set(names)
    for card in all_cards:
        card_name = getattr(card, 'name', '')
        if card_name in name_set:
            result[card_name] = card
            if len(result) == len(name_set):
                break
    return result


def increment_flag_counter(quest_mgr, prefix, target_count):
    """
    通用 flag 计数器，用于 COMPLETE_ANY_TASK / ORG_TASK / WAR_PARTICIPATE / OCCUPY_BUILDING 等。

    自增 flags['{prefix}_{active_quest_id}']，返回是否达到目标。
    """
    quest = quest_mgr.get_active_quest()
    if not quest:
        return False
    flag_name = f'{prefix}_{quest.id}'
    current = quest_mgr.get_flag(flag_name, 0)
    quest_mgr.set_flag(flag_name, current + 1)
    return (current + 1) >= int(target_count)


def find_safe_position(candidates, all_cards, min_dist=80):
    """
    从候选位置中找到一个不与已有 NPC 重叠的安全位置。

    Args:
        candidates: [(x, y), ...] 候选位置列表
        all_cards: 所有实体列表，用于碰撞检测
        min_dist: 最小安全距离

    Returns:
        (x, y) 安全位置，若全部不安全则返回第一个候选位置
    """
    occupied = []
    for card in all_cards:
        if hasattr(card, 'rect'):
            occupied.append((card.rect.centerx, card.rect.centery))

    for cx, cy in candidates:
        safe = True
        for ox, oy in occupied:
            if math.hypot(cx - ox, cy - oy) < min_dist:
                safe = False
                break
        if safe:
            return (cx, cy)

    return candidates[0] if candidates else (0, 0)


def show_float_text(ctx, text, x, y, color=(255, 255, 255)):
    """安全地显示浮动文字，自动处理 ft_manager 不存在的情况"""
    ft = getattr(ctx, 'ft_manager', None) if ctx else None
    if ft:
        ft.add_text(text, x, y, color)
