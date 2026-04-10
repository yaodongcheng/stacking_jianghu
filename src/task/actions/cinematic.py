# --- src/task/actions/cinematic.py ---
"""
轻量演出系统 Action Handlers

转场效果、时间/场景控制、状态设置、NPC 操作等演出类动作。
从 quest_system.py 提取，所有函数签名统一为 (quest_mgr, ctx, *params)。
"""

from src.definitions import STATE_EVENT
from ._helpers import find_npc_by_name


def action_fade_to_black(quest_mgr, ctx=None, duration=1.0):
    """黑屏渐入效果 - 通过设置标记让渲染系统处理"""
    print(f"[Quest] Action: FADE_TO_BLACK - 黑屏渐入 ({duration}s)")
    quest_mgr.set_flag('screen_fade', {'type': 'to_black', 'duration': float(duration), 'start_time': None})


def action_fade_from_black(quest_mgr, ctx=None, duration=1.0):
    """黑屏渐出效果"""
    print(f"[Quest] Action: FADE_FROM_BLACK - 黑屏渐出 ({duration}s)")
    quest_mgr.set_flag('screen_fade', {'type': 'from_black', 'duration': float(duration), 'start_time': None})


def action_flash_white(quest_mgr, ctx=None, duration=0.3):
    """白屏闪烁效果 - 被打击时的视觉反馈"""
    print(f"[Quest] Action: FLASH_WHITE - 白屏闪烁 ({duration}s)")
    quest_mgr.set_flag('screen_fade', {'type': 'flash_white', 'duration': float(duration), 'start_time': None})


def action_advance_time(quest_mgr, ctx=None, hours=8):
    """时间推进 - 模拟时间流逝"""
    print(f"[Quest] Action: ADVANCE_TIME - 时间推进 {hours} 小时")
    if ctx:
        em = getattr(ctx, 'event_manager', None)
        if em:
            ticks_per_hour = em.ticks_per_day // 24
            em.current_day_ticks += ticks_per_hour * int(hours)
            em.game_tick += ticks_per_hour * int(hours)
            print(f"[Quest] 时间已推进 {hours} 小时")


def action_teleport_player(quest_mgr, ctx=None, location=''):
    """传送玩家到指定位置"""
    print(f"[Quest] Action: TELEPORT_PLAYER - 传送到 {location}")
    if ctx:
        player = getattr(ctx, 'player', None)
        all_cards = getattr(ctx, 'all_cards', [])

        target_pos = None
        for card in all_cards:
            card_name = getattr(card, 'name', '')
            if location in card_name:
                target_pos = (card.rect.centerx, card.rect.centery + 50)
                break

        if player and target_pos:
            player.rect.centerx = target_pos[0]
            player.rect.centery = target_pos[1]
            print(f"[Quest] 玩家已传送到 {location} ({target_pos})")


def action_set_hunger(quest_mgr, ctx=None, value=50):
    """设置玩家饥饿值"""
    print(f"[Quest] Action: SET_HUNGER - 设置饥饿值为 {value}")
    if ctx:
        player = getattr(ctx, 'player', None)
        if player and hasattr(player, 'hunger'):
            player.hunger = int(value)
            print(f"[Quest] 玩家饥饿值已设置为 {value}")


def action_set_hp(quest_mgr, ctx=None, value=10):
    """设置玩家生命值"""
    print(f"[Quest] Action: SET_HP - 设置HP为 {value}")
    if ctx:
        player = getattr(ctx, 'player', None)
        if player and hasattr(player, 'hp'):
            player.hp = int(value)
            print(f"[Quest] 玩家HP已设置为 {value}")


def action_set_stamina(quest_mgr, ctx=None, value=50):
    """设置玩家体力值"""
    print(f"[Quest] Action: SET_STAMINA - 设置体力为 {value}")
    if ctx:
        player = getattr(ctx, 'player', None)
        if player and hasattr(player, 'stamina'):
            player.stamina = int(value)
            print(f"[Quest] 玩家体力已设置为 {value}")


def action_spawn_enemy_near(quest_mgr, ctx=None, enemy_names=''):
    """在玩家附近生成敌人"""
    print(f"[Quest] Action: SPAWN_ENEMY_NEAR - 生成敌人: {enemy_names}")
    if ctx:
        player = getattr(ctx, 'player', None)
        all_cards = getattr(ctx, 'all_cards', [])

        if not player:
            return

        names = enemy_names.split('|') if '|' in enemy_names else [enemy_names]
        offset = 80

        for i, name in enumerate(names):
            name = name.strip()
            npc = find_npc_by_name(all_cards, name)
            if npc:
                npc.rect.centerx = player.rect.centerx + offset * (i + 1)
                npc.rect.centery = player.rect.centery
                npc.state = STATE_EVENT
                print(f"[Quest] {name} 已移动到玩家附近")


def action_despawn_npc(quest_mgr, ctx=None, npc_name=''):
    """移除指定NPC（设置为不可见/远离玩家）"""
    print(f"[Quest] Action: DESPAWN_NPC - 移除NPC: {npc_name}")
    if ctx:
        all_cards = getattr(ctx, 'all_cards', [])
        npc = find_npc_by_name(all_cards, npc_name)
        if npc:
            npc.rect.centerx = -1000
            npc.rect.centery = -1000
            print(f"[Quest] {npc_name} 已移除")


def action_knockout_player(quest_mgr, ctx=None):
    """玩家昏倒效果 - 设置低HP并触发视觉效果"""
    print("[Quest] Action: KNOCKOUT - 玩家昏倒")
    if ctx:
        player = getattr(ctx, 'player', None)
        if player:
            if hasattr(player, 'hp'):
                player.hp = 1
            if hasattr(player, 'stamina'):
                player.stamina = 0
            quest_mgr.set_flag('screen_fade', {'type': 'to_black', 'duration': 2.0, 'start_time': None})


def action_start_auto_combat(quest_mgr, ctx=None):
    """自动战斗 - 玩家被动挨打，用于演出被群殴的场景"""
    print("[Quest] Action: START_AUTO_COMBAT - 自动战斗(被动挨打)")
    quest_mgr.set_flag('screen_fade', {'type': 'flash_white', 'duration': 0.5, 'start_time': None})


# ======================== Handler 注册表 ========================
HANDLERS = {
    'FADE_TO_BLACK': action_fade_to_black,
    'FADE_FROM_BLACK': action_fade_from_black,
    'FLASH_WHITE': action_flash_white,
    'ADVANCE_TIME': action_advance_time,
    'TELEPORT_PLAYER': action_teleport_player,
    'SET_HUNGER': action_set_hunger,
    'SET_HP': action_set_hp,
    'SET_STAMINA': action_set_stamina,
    'SPAWN_ENEMY_NEAR': action_spawn_enemy_near,
    'DESPAWN_NPC': action_despawn_npc,
    'KNOCKOUT': action_knockout_player,
    'START_AUTO_COMBAT': action_start_auto_combat,
}
