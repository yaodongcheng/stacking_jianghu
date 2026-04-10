# --- src/task/actions/economy.py ---
"""
经济/悬赏相关 Action Handlers

卖鱼奖励、恶霸悬赏、击败恶霸奖励、解锁难民等。
从 quest_system.py 提取，所有函数签名统一为 (quest_mgr, ctx, *params)。
"""

from ._helpers import show_float_text


def action_reward_fish_money(quest_mgr, ctx=None):
    """经济任务奖励：卖鱼获得铜钱"""
    print("[Quest] Action: REWARD_FISH_MONEY - 卖鱼获得铜钱奖励")
    if ctx and hasattr(ctx, 'player'):
        player = ctx.player

        # 移除已交付的鱼（兜底）
        fish_key = '生鱼'
        if fish_key in player.inventory and player.inventory[fish_key] >= 3:
            player.inventory[fish_key] -= 3
            if player.inventory[fish_key] <= 0:
                del player.inventory[fish_key]

        # 发放铜钱奖励（3条鱼 × 10铜/条 = 30铜）
        reward_money = 30
        player.money = getattr(player, 'money', 0) + reward_money

        # 小幅提升声望
        fame_gain = 5
        player.fame = getattr(player, 'fame', 0) + fame_gain

        # 浮动文字提示
        ft = getattr(ctx, 'ft_manager', None)
        if ft:
            ft.add_text(f"+{reward_money} 铜钱",
                        player.rect.centerx, player.rect.top - 30, (255, 215, 0))
            ft.add_text(f"+{fame_gain} 声望",
                        player.rect.centerx, player.rect.top - 50, (255, 200, 100))

    quest_mgr.set_flag('first_money_quest_done', True)


def action_trigger_bully_bounty(quest_mgr, ctx=None):
    """恶霸王老虎发出悬赏"""
    print("[Quest] Action: TRIGGER_BULLY_BOUNTY - 恶霸发出悬赏")
    if ctx:
        faction_war_system = getattr(ctx, 'faction_war', None) or getattr(ctx, 'faction_war_system', None)
        player = getattr(ctx, 'player', None)

        if faction_war_system and player:
            success, bounty_id = faction_war_system.post_bounty(
                issuer_org='heifeng_zhai',
                target_id=getattr(player, 'id', 9999),
                reward=50,
                reason='得罪王老虎',
                is_player_target=True
            )

            if success:
                quest_mgr.bully_bounty_id = bounty_id
                print(f"[Quest] 恶霸悬赏ID: {bounty_id}")

            ft = getattr(ctx, 'ft_manager', None)
            if ft:
                ft.add_text("[!] 王老虎悬赏你！",
                            player.rect.centerx, player.rect.top - 30, (255, 50, 50))

    quest_mgr.set_flag('bully_bounty_active', True)


def action_reward_bully_victory(quest_mgr, ctx=None):
    """击败恶霸的奖励"""
    print("[Quest] Action: REWARD_BULLY_VICTORY - 发放击败恶霸奖励")
    if ctx:
        player = getattr(ctx, 'player', None)
        ft_manager = getattr(ctx, 'ft_manager', None)

        if player:
            reward_money = 100
            player.money = getattr(player, 'money', 0) + reward_money

            fame_gain = 30
            player.fame = getattr(player, 'fame', 0) + fame_gain

            player.morality = min(100, getattr(player, 'morality', 50) + 10)

            if ft_manager:
                ft_manager.add_text(f"+{reward_money} 铜钱",
                                    player.rect.centerx, player.rect.top - 30, (255, 215, 0))
                ft_manager.add_text(f"+{fame_gain} 声望",
                                    player.rect.centerx, player.rect.top - 50, (255, 215, 0))
                ft_manager.add_text("惩恶扬善！",
                                    player.rect.centerx, player.rect.top - 70, (100, 255, 100))

    quest_mgr.set_flag('bully_bounty_active', False)
    quest_mgr.set_flag('bully_defeated', True)


def action_unlock_refugee(quest_mgr, ctx=None):
    """解锁难民系统"""
    quest_mgr.set_flag('refugee_unlocked', True)
    if ctx:
        ctx.event_manager.spawn_refugee_immediately(ctx)


# ======================== Handler 注册表 ========================
HANDLERS = {
    'REWARD_FISH_MONEY': action_reward_fish_money,
    'TRIGGER_BULLY_BOUNTY': action_trigger_bully_bounty,
    'REWARD_BULLY_VICTORY': action_reward_bully_victory,
    'UNLOCK_REFUGEE': action_unlock_refugee,
}
