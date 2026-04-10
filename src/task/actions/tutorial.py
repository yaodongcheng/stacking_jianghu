# --- src/task/actions/tutorial.py ---
"""
新手引导/教程 Action Handlers

玩家被打、饥饿触发、招募张三、泼皮战斗等教程流程动作。
从 quest_system.py 提取，所有函数签名统一为 (quest_mgr, ctx, *params)。
"""

import random
from src.definitions import STATE_EVENT, STATE_IDLE, STATE_COMBAT, QS_ACTIVE
from ._helpers import find_npc_by_name


def action_player_defeated(quest_mgr, ctx=None):
    """玩家被打倒 - 剧情演出"""
    print("[Quest] Action: PLAYER_DEFEATED - 玩家被泼皮群殴打倒")
    if not ctx:
        return

    player = getattr(ctx, 'player', None)
    ft_manager = getattr(ctx, 'ft_manager', None)

    if player:
        player.hp = max(1, player.hp - 40)
        player.ai_reason = "被打倒了..."

        if ft_manager:
            ft_manager.add_text("寡不敌众！", player.rect.centerx, player.rect.top - 30, (255, 50, 50))
            ft_manager.add_text("-40 HP", player.rect.centerx, player.rect.top - 50, (255, 80, 80))

    quest_mgr.set_flag('player_defeated_once', True)


def action_trigger_hungry(quest_mgr, ctx=None):
    """触发饥饿状态 - 引导玩家了解生存系统"""
    print("[Quest] Action: TRIGGER_HUNGRY - 触发饥饿引导")
    if not ctx:
        return

    player = getattr(ctx, 'player', None)
    ft_manager = getattr(ctx, 'ft_manager', None)

    if player:
        player.hunger = max(60, getattr(player, 'hunger', 100))
        if ft_manager:
            ft_manager.add_text("肚子饿了...", player.rect.centerx, player.rect.top - 30, (255, 200, 100))

    quest_mgr.quest_status = QS_ACTIVE
    print("[Quest] 饥饿任务已激活")


def action_recruit_zhangsan(quest_mgr, ctx=None):
    """招募张三为门客"""
    print("[Quest] Action: RECRUIT_ZHANGSAN - 招募猎户张三")
    if not ctx:
        return

    player = getattr(ctx, 'player', None)
    ft_manager = getattr(ctx, 'ft_manager', None)
    all_cards = getattr(ctx, 'all_cards', [])

    zhangsan = find_npc_by_name(all_cards, '猎户张三')

    if player and zhangsan:
        recruit_cost = 50
        if player.money >= recruit_cost:
            player.money -= recruit_cost

            zhangsan.is_follower = True
            zhangsan.follow_target = player
            zhangsan.ai_mode = "FOLLOW"
            zhangsan.state = STATE_IDLE
            zhangsan.ai_reason = "跟随主人"

            if not hasattr(player, 'followers'):
                player.followers = []
            player.followers.append(zhangsan)

            if ft_manager:
                ft_manager.add_text(f"-{recruit_cost} 铜钱", player.rect.centerx, player.rect.top - 30, (255, 215, 0))
                ft_manager.add_text("张三加入！", zhangsan.rect.centerx, zhangsan.rect.top - 30, (100, 255, 100))

            print(f"[Quest] 张三已成为门客")
        else:
            print(f"[Quest] 招募失败：金钱不足 ({player.money} < {recruit_cost})")
            if ft_manager:
                ft_manager.add_text("金钱不足！", player.rect.centerx, player.rect.top - 30, (255, 50, 50))

    quest_mgr.set_flag('recruited_猎户张三', True)


def action_spawn_bully(quest_mgr, ctx=None):
    """生成泼皮供反击 - 将泼皮牛二移动到贫民窟附近等待战斗"""
    print("[Quest] Action: SPAWN_BULLY_FOR_REVENGE - 生成泼皮供反击")
    if not ctx:
        return

    world_map = getattr(ctx, 'world_map', None)
    all_cards = getattr(ctx, 'all_cards', [])
    ft_manager = getattr(ctx, 'ft_manager', None)

    if world_map and all_cards:
        slum = world_map.slum_rect
        spawn_x = slum.centerx + random.randint(-50, 50)
        spawn_y = slum.centery + random.randint(-50, 50)

        popi_niuer = find_npc_by_name(all_cards, '泼皮牛二')
        popi_goudan = find_npc_by_name(all_cards, '泼皮狗蛋')

        if popi_niuer:
            popi_niuer.set_pos(spawn_x, spawn_y)
            popi_niuer.state = 'IDLE'
            popi_niuer.ai_reason = "等着那小子送死..."
            print(f"[Quest] 泼皮牛二已移动到 ({spawn_x}, {spawn_y})")

            if ft_manager:
                ft_manager.add_text("泼皮牛二出现在贫民窟！", spawn_x, spawn_y - 30, (255, 150, 50))

        if popi_goudan:
            popi_goudan.set_pos(spawn_x + 60, spawn_y + 20)
            popi_goudan.state = 'IDLE'
            popi_goudan.ai_reason = "跟着牛二哥"
            print(f"[Quest] 泼皮狗蛋已移动到牛二旁边")

        quest_mgr.set_flag('revenge_bully_spawned', True)
        print(f"[Quest] 泼皮已就位，等待玩家复仇")


def action_start_combat_bully(quest_mgr, ctx=None):
    """开始与泼皮的战斗"""
    print("[Quest] Action: START_COMBAT_BULLY - 开始与泼皮战斗")
    if not ctx:
        return

    player = getattr(ctx, 'player', None)
    all_cards = getattr(ctx, 'all_cards', [])
    combat_manager = getattr(ctx, 'combat_manager', None)

    target_bully = find_npc_by_name(all_cards, '泼皮牛二')

    if player and target_bully and combat_manager:
        target_bully.attitude = -100
        target_bully.state = STATE_COMBAT
        target_bully.ai_reason = "与玩家战斗"

        player.in_combat = True
        player.combat_target = target_bully

        print(f"[Quest] 战斗开始：玩家 vs {target_bully.name}")

    quest_mgr.set_flag('combat_with_bully_started', True)


def action_complete_tutorial(quest_mgr, ctx=None):
    """完成新手教程"""
    print("[Quest] Action: COMPLETE_TUTORIAL - 新手教程完成")
    if not ctx:
        return

    player = getattr(ctx, 'player', None)
    ft_manager = getattr(ctx, 'ft_manager', None)

    if player:
        bonus_money = 50
        bonus_fame = 20
        player.money += bonus_money
        player.fame = getattr(player, 'fame', 0) + bonus_fame

        if ft_manager:
            ft_manager.add_text("教程完成！", player.rect.centerx, player.rect.top - 30, (255, 215, 0))
            ft_manager.add_text(f"+{bonus_money} 铜钱", player.rect.centerx, player.rect.top - 50, (255, 215, 0))
            ft_manager.add_text(f"+{bonus_fame} 声望", player.rect.centerx, player.rect.top - 70, (255, 215, 0))

    quest_mgr.set_flag('tutorial_completed', True)
    quest_mgr.set_flag('guidance_visible', True)


def action_trigger_revenge_ambush(quest_mgr, ctx=None):
    """触发报复伏击事件"""
    print("[Quest] Action: TRIGGER_REVENGE_AMBUSH - 触发报复伏击")

    quest_mgr.set_flag('revenge_ambush_triggered', True)

    if ctx:
        all_cards = getattr(ctx, 'all_cards', [])
        player = getattr(ctx, 'player', None)

        popi = find_npc_by_name(all_cards, '泼皮牛二')

        if popi and player:
            popi.rect.centerx = player.rect.centerx + 100
            popi.rect.centery = player.rect.centery
            popi.state = STATE_EVENT
            print(f"[Quest] 泼皮牛二已移动到玩家附近准备伏击")


# ======================== Handler 注册表 ========================
HANDLERS = {
    'PLAYER_DEFEATED': action_player_defeated,
    'TRIGGER_HUNGRY': action_trigger_hungry,
    'RECRUIT_ZHANGSAN': action_recruit_zhangsan,
    'SPAWN_BULLY_FOR_REVENGE': action_spawn_bully,
    'START_COMBAT_BULLY': action_start_combat_bully,
    'COMPLETE_TUTORIAL': action_complete_tutorial,
    'TRIGGER_REVENGE_AMBUSH': action_trigger_revenge_ambush,
}
