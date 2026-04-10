# --- src/task/actions/faction.py ---
"""
势力/组织相关 Action Handlers

声望检查、加入势力、任务计数器、等级检查等。
从 quest_system.py 提取，所有函数签名统一为 (quest_mgr, ctx, *params)。
"""

from ._helpers import increment_flag_counter


def action_set_fame_req(quest_mgr, ctx=None, fame_req='20'):
    """设置声望要求 - 用于势力加入任务"""
    print(f"[Quest] Action: SET_FAME_REQ - 设置声望要求: {fame_req}")

    try:
        fame_value = int(fame_req)
    except (ValueError, TypeError):
        print(f"[Quest] 警告：无法解析声望值 {fame_req}，使用默认值 20")
        fame_value = 20

    player = getattr(ctx, 'player', None) if ctx else None
    if player:
        current_fame = getattr(player, 'fame', 0)
        print(f"[Quest] 玩家当前声望: {current_fame}, 要求: {fame_value}")

        current_quest = quest_mgr.get_current_quest()
        if current_quest:
            flag_name = f'fame_req_{current_quest.id}'
            quest_mgr.set_flag(flag_name, fame_value)
            print(f"[Quest] 声望要求标记已设置: {flag_name} = {fame_value}")

        if current_fame < fame_value:
            quest_mgr.set_flag('fame_insufficient', True)
            print(f"[Quest] 声望不足，需要 {fame_value - current_fame} 点声望")
        else:
            quest_mgr.set_flag('fame_insufficient', False)
            print(f"[Quest] 声望满足要求")


def action_join_org(quest_mgr, ctx=None, org_id='kaifeng_fu'):
    """加入势力 - 让玩家加入指定组织"""
    print(f"[Quest] Action: JOIN_ORG - 加入组织: {org_id}")
    if not ctx:
        return

    player = getattr(ctx, 'player', None)
    org_economy = getattr(ctx, 'org_economy', None)
    ft_manager = getattr(ctx, 'ft_manager', None)

    if not player:
        print("[Quest] 错误：找不到玩家对象")
        return

    player.org_id = org_id
    player.org_role = 'MEMBER'
    player.org_rank = 1

    if org_economy:
        if org_id not in org_economy.org_members:
            org_economy.org_members[org_id] = []
        org_economy.org_members[org_id].append(player.id)

    if ft_manager:
        from src.data.character_seeds import ORGANIZATIONS
        org_name = ORGANIZATIONS.get(org_id, {}).get('name', org_id)
        ft_manager.add_text(f"加入 {org_name}！", player.rect.centerx, player.rect.top - 30, (100, 200, 255))

    print(f"[Quest] 玩家已加入组织：{org_id}")


def action_set_flag(quest_mgr, ctx=None, flag_name='flag', flag_value=True):
    """设置标记"""
    print(f"[Quest] Action: SET_FLAG - 设置标记: {flag_name} = {flag_value}")
    quest_mgr.set_flag(flag_name, flag_value)


def action_complete_any_task(quest_mgr, ctx=None, task_count='3'):
    """完成任意任务计数器"""
    print(f"[Quest] Action: COMPLETE_ANY_TASK - 完成任意任务: {task_count}")
    reached = increment_flag_counter(quest_mgr, 'task_count', int(task_count))
    if reached:
        print(f"[Quest] 已完成足够任务，可以推进任务")
    return reached


def action_org_task(quest_mgr, ctx=None, task_count='1'):
    """完成组织任务计数器"""
    print(f"[Quest] Action: ORG_TASK - 完成组织任务: {task_count}")
    reached = increment_flag_counter(quest_mgr, 'org_task_count', int(task_count))
    if reached:
        print(f"[Quest] 已完成足够组织任务，可以推进任务")
    return reached


def action_org_rank(quest_mgr, ctx=None, target_rank='5'):
    """检查组织等级"""
    print(f"[Quest] Action: ORG_RANK - 检查组织等级: {target_rank}")
    if not ctx:
        return False

    player = getattr(ctx, 'player', None)
    if not player:
        print("[Quest] 错误：找不到玩家对象")
        return False

    try:
        target = int(target_rank)
    except (ValueError, TypeError):
        target = 5

    current_rank = getattr(player, 'org_rank', 0)
    print(f"[Quest] 玩家当前组织等级: {current_rank}, 目标: {target}")

    if current_rank >= target:
        print(f"[Quest] 组织等级满足要求")
        return True
    else:
        print(f"[Quest] 组织等级不足，需要 {target - current_rank} 级")
        return False


def action_war_participate(quest_mgr, ctx=None, war_count='1'):
    """参与势力战争计数器"""
    print(f"[Quest] Action: WAR_PARTICIPATE - 参与势力战争: {war_count}")
    reached = increment_flag_counter(quest_mgr, 'war_count', int(war_count))
    if reached:
        print(f"[Quest] 已参与足够战争，可以推进任务")
    return reached


def action_occupy_building(quest_mgr, ctx=None, building_count='1'):
    """占领建筑计数器"""
    print(f"[Quest] Action: OCCUPY_BUILDING - 占领建筑: {building_count}")
    reached = increment_flag_counter(quest_mgr, 'occupy_count', int(building_count))
    if reached:
        print(f"[Quest] 已占领足够建筑，可以推进任务")
    return reached


def action_control_building(quest_mgr, ctx=None, building_count='10'):
    """检查控制的建筑数量"""
    print(f"[Quest] Action: CONTROL_BUILDING - 检查控制的建筑数量: {building_count}")
    if not ctx:
        return False

    player = getattr(ctx, 'player', None)
    faction_war_system = getattr(ctx, 'faction_war', None)

    if not player:
        print("[Quest] 错误：找不到玩家对象")
        return False

    try:
        target = int(building_count)
    except (ValueError, TypeError):
        target = 10

    controlled_count = 0
    if faction_war_system:
        player_org_id = getattr(player, 'org_id', None)
        if player_org_id:
            for building_id, owner_org_id in faction_war_system.control_points.items():
                if owner_org_id == player_org_id:
                    controlled_count += 1

    print(f"[Quest] 玩家当前控制建筑数量: {controlled_count}, 目标: {target}")

    if controlled_count >= target:
        print(f"[Quest] 控制建筑数量满足要求")
        return True
    else:
        print(f"[Quest] 控制建筑数量不足，需要 {target - controlled_count} 个建筑")
        return False


def action_investigate(quest_mgr, ctx=None, target_name=''):
    """收集情报"""
    print(f"[Quest] Action: INVESTIGATE - 收集情报: {target_name}")
    current_quest = quest_mgr.get_current_quest()
    if current_quest:
        flag_name = f'investigated_{current_quest.id}'
        quest_mgr.set_flag(flag_name, True)
        print(f"[Quest] 情报收集标记已设置: {flag_name}")
    return True


# ======================== Handler 注册表 ========================
HANDLERS = {
    'SET_FAME_REQ': action_set_fame_req,
    'JOIN_ORG': action_join_org,
    'SET_FLAG': action_set_flag,
    'COMPLETE_ANY_TASK': action_complete_any_task,
    'ORG_TASK': action_org_task,
    'ORG_RANK': action_org_rank,
    'WAR_PARTICIPATE': action_war_participate,
    'OCCUPY_BUILDING': action_occupy_building,
    'CONTROL_BUILDING': action_control_building,
    'INVESTIGATE': action_investigate,
}
