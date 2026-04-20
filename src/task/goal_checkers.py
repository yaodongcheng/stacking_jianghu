"""
任务目标检查器（按 quest.type 派发的注册表）

目的：替代 quest_system.check_progress 里 100 行的 if/elif 链。
每个检查器纯函数，签名统一：

    def check_X(quest, player, all_cards, manager, ctx) -> bool

返回 True 表示任务目标已达成（不负责状态推进，不负责副作用以外的事）。
QuestManager.check_progress 拿到 True 后再做状态机推进 / NPC 弹开 / 自动激活
等业务编排——这部分逻辑保持留在 QuestManager 上下文。

新增任务类型只要：
  1. 写一个 check_xxx 函数
  2. 注册到 GOAL_CHECKERS 字典

不再有"为新类型在主循环里加 elif"的需求。
"""

import math
from src.entities import NPC, Building, Resource


# 12 时辰 → 一天 12 段
SHICHEN_MAP = {
    '子': 0, '丑': 1, '寅': 2, '卯': 3, '辰': 4, '巳': 5,
    '午': 6, '未': 7, '申': 8, '酉': 9, '戌': 10, '亥': 11,
}

# REACH 任务的预定义区域点（坐标）
REACH_POINTS = {
    'AMBUSH_POINT':   (2200, 2100),
    'RIVER_BANK':     (3000, 2500),
    'HUNTER_CABIN':   (500, 500),
    'MARKET_CENTER':  (1700, 1400),
}


# ============================================================================
# 各 type 的检查函数
# ============================================================================

def check_gather(quest, player, all_cards, manager, ctx):
    """采集类：玩家+所有随从背包合计达到 count"""
    count = player.inventory.get(quest.target, 0)
    for c in all_cards:
        if getattr(c, 'is_follower', False):
            count += c.inventory.get(quest.target, 0)
    return count >= quest.count


def check_have_unit(quest, player, all_cards, manager, ctx):
    """拥有 N 个指定职业 NPC / 类型建筑 / 类型资源"""
    count = 0
    for c in all_cards:
        if isinstance(c, NPC) and getattr(c, 'job', '') == quest.target:
            count += 1
        elif isinstance(c, Building) and getattr(c, 'building_type', '') == quest.target:
            count += 1
        elif isinstance(c, Resource) and c.item_type == quest.target:
            count += c.count
    return count >= quest.count


def check_resource_total(quest, player, all_cards, manager, ctx):
    """玩家身上的某项总量达到 count（MONEY / FAME）"""
    if quest.target == 'MONEY':
        return player.money >= quest.count
    if quest.target == 'FAME':
        return player.fame >= quest.count
    return False


def check_survive(quest, player, all_cards, manager, ctx):
    """生存到第 N 天"""
    return quest.target == 'DAY' and player.day >= quest.count


def check_goal(quest, player, all_cards, manager, ctx):
    """特殊目标 flag（CANCEL_BOUNTY / DEFEAT_BULLY / HUNGER）"""
    if quest.target == 'CANCEL_BOUNTY':
        return not manager.flags.get('bully_bounty_active', True)
    if quest.target == 'DEFEAT_BULLY':
        return manager.flags.get('bully_defeated', False)
    if quest.target == 'HUNGER':
        return getattr(player, 'hunger', 100) <= quest.count
    return False


def check_recruit(quest, player, all_cards, manager, ctx):
    """招募指定 NPC：先看 flag，再看 followers 列表（找到则补 flag）"""
    name = quest.target
    if manager.flags.get(f'recruited_{name}', False):
        return True
    for f in getattr(player, 'followers', []):
        if getattr(f, 'name', '') == name:
            manager.set_flag(f'recruited_{name}', True)
            return True
    return False


def check_combat(quest, player, all_cards, manager, ctx):
    """战胜指定 NPC（外部代码负责 set defeated_NAME flag）"""
    return manager.flags.get(f'defeated_{quest.target}', False)


def check_eat(quest, player, all_cards, manager, ctx):
    """饥饿值降到 count 以下"""
    target_hunger = int(quest.count) if quest.count else 50
    return getattr(player, 'hunger', 100) < target_hunger


def check_deliver(quest, player, all_cards, manager, ctx):
    """交付物品到指定 NPC：进度由 on_item_delivered 在外部累加 flag"""
    return manager.flags.get(f'deliver_{quest.id}', 0) >= quest.count


def check_reach(quest, player, all_cards, manager, ctx):
    """玩家到达指定区域（命名点 或 "x,y"），count 是判定半径"""
    if not player:
        return False

    pos = REACH_POINTS.get(quest.target)
    if pos is None and ',' in str(quest.target):
        try:
            xs, ys = str(quest.target).split(',')[:2]
            pos = (int(xs), int(ys))
        except ValueError:
            pos = None
    if pos is None:
        print(f"[Quest] REACH 目标解析失败: {quest.target}")
        return False

    px, py = player.rect.centerx, player.rect.centery
    radius = int(quest.count) if quest.count else 150
    dist = math.hypot(px - pos[0], py - pos[1])
    if dist <= radius:
        print(f"[Quest] 玩家到达目标区域 {quest.target}! 距离={dist:.0f}px <= {radius}px")
        return True
    return False


def check_wait_time(quest, player, all_cards, manager, ctx):
    """到达指定 day:时辰。target 格式 "1:子" / "2:申" """
    if not ctx:
        return False
    parts = str(quest.target).split(':')
    if len(parts) != 2:
        return False
    try:
        target_day = int(parts[0])
    except ValueError:
        return False
    target_shichen = SHICHEN_MAP.get(parts[1], -1)
    if target_shichen < 0:
        return False

    em = ctx.event_manager
    current_shichen = int(em.current_day_ticks / em.ticks_per_day * 12)
    current_day = player.day

    if current_day > target_day:
        return True
    if current_day == target_day and current_shichen >= target_shichen:
        print(f"[Quest] WAIT_TIME 条件满足: Day {current_day} {parts[1]}时 (shichen={current_shichen})")
        return True
    return False


# ============================================================================
# 注册表
# ============================================================================
# DIALOG / INTERACT 由对话流转推进，没有"被动检查目标完成"的语义，故不在此表。
# CHOICE / FREE / AFFINITY_CHECK / ORG_RANK 同理（目前由其他子系统推进）。
GOAL_CHECKERS = {
    'GATHER':         check_gather,
    'HAVE_UNIT':      check_have_unit,
    'RESOURCE_TOTAL': check_resource_total,
    'SURVIVE':        check_survive,
    'GOAL':           check_goal,
    'RECRUIT':        check_recruit,
    'COMBAT':         check_combat,
    'EAT':            check_eat,
    'DELIVER':        check_deliver,
    'REACH':          check_reach,
    'WAIT_TIME':      check_wait_time,
}


def is_goal_met(quest, player, all_cards, manager, ctx):
    """统一入口：返回 True 表示目标已达成。无对应检查器返回 False。"""
    checker = GOAL_CHECKERS.get(quest.type)
    if checker is None:
        return False
    return checker(quest, player, all_cards, manager, ctx)
