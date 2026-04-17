# --- src/task/actions/cinematic.py ---
"""
轻量演出系统 Action Handlers

转场效果、时间/场景控制、状态设置、NPC 操作等演出类动作。
从 quest_system.py 提取，所有函数签名统一为 (quest_mgr, ctx, *params)。

【设计原则】
- 所有移动操作必须使用封装好的方法：set_pos(), set_movement_target(), clear_movement_target()
- 禁止直接修改 rect / _target_x / _target_y 等属性
- NPC 查找统一使用 _helpers.py 中的 find_npc_by_id / find_npc_by_name
- 剧情期间 NPC 移动需要考虑屏蔽机制：通过 story_actor_ids 确保
"""

from src.definitions import STATE_EVENT, STATE_MOVING, STATE_IDLE
from ._helpers import find_npc_by_id, find_npc_by_name
import time as _time_mod

# ======================== 屏幕特效管理器 ========================

class ScreenEffectsManager:
    """
    屏幕特效管理器 - 负责淡入淡出、昼夜遮罩等全屏效果。

    由 main.py 创建并挂到 ctx.screen_effects，每帧调用 update() 和 draw()。
    action 函数（如 FADE_FROM_BLACK）通过 ctx.screen_effects 来触发效果。
    """

    # 深蓝色夜色，比纯黑更有氛围
    NIGHT_COLOR = (10, 10, 40)

    # 昼夜 alpha 曲线：progress(0~1) 对应 12 时辰
    # 子(0)=深夜, 丑(1), 寅(2)=黎明前, 卯(3)=日出, 辰(4)~未(7)=白天,
    # 申(8), 酉(9)=日落, 戌(10)=入夜, 亥(11)=深夜
    _NIGHT_ALPHA_TABLE = [
        120,  # 子时 23-01 深夜
        110,  # 丑时 01-03
         80,  # 寅时 03-05 黎明前
         30,  # 卯时 05-07 日出
          0,  # 辰时 07-09 白天
          0,  # 巳时 09-11
          0,  # 午时 11-13
          0,  # 未时 13-15
         10,  # 申时 15-17 傍晚
         50,  # 酉时 17-19 日落
         80,  # 戌时 19-21 入夜
        100,  # 亥时 21-23
    ]

    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        # 淡入淡出
        self._fade_type = None    # 'from_black' / 'to_black' / 'flash_white'
        self._fade_duration = 0.0
        self._fade_start = 0.0
        # 昼夜
        self._night_alpha = 0
        # 全黑覆盖（开场用）
        self._full_black = False
        # 缓存 surface 避免每帧创建
        self._overlay = None

    def set_full_black(self):
        """设置全黑状态（开场用，FADE_FROM_BLACK 会解除）"""
        self._full_black = True

    def start_fade(self, fade_type, duration):
        """启动淡入淡出效果"""
        self._fade_type = fade_type
        self._fade_duration = max(float(duration), 0.01)
        self._fade_start = _time_mod.time()
        # from_black 解除全黑
        if fade_type == 'from_black':
            self._full_black = False

    def update_day_night(self, day_progress):
        """根据一天进度 (0~1) 计算夜晚遮罩 alpha，平滑插值"""
        p = max(0.0, min(day_progress, 0.9999))
        # 连续 shichen 索引
        pos = p * 12.0
        idx = int(pos)
        frac = pos - idx
        a0 = self._NIGHT_ALPHA_TABLE[idx]
        a1 = self._NIGHT_ALPHA_TABLE[(idx + 1) % 12]
        self._night_alpha = int(a0 + (a1 - a0) * frac)

    def draw_day_night(self, screen):
        """仅绘制昼夜遮罩（在游戏世界之上、UI之下调用）"""
        if self._full_black or self._night_alpha <= 0:
            return
        import pygame
        sw, sh = self.screen_w, self.screen_h
        if self._overlay is None or self._overlay.get_size() != (sw, sh):
            self._overlay = pygame.Surface((sw, sh))
        self._overlay.fill(self.NIGHT_COLOR)
        self._overlay.set_alpha(self._night_alpha)
        screen.blit(self._overlay, (0, 0))

    def draw(self, screen):
        """绘制屏幕特效：全黑覆盖 + 淡入淡出（昼夜遮罩已移至 draw_day_night）"""
        import pygame

        sw, sh = self.screen_w, self.screen_h

        # --- 1. 全黑覆盖（开场） ---
        if self._full_black:
            if self._overlay is None or self._overlay.get_size() != (sw, sh):
                self._overlay = pygame.Surface((sw, sh))
            self._overlay.fill((0, 0, 0))
            self._overlay.set_alpha(255)
            screen.blit(self._overlay, (0, 0))
            return  # 全黑时不绘制其他效果

        # --- 2. 淡入淡出 ---
        if self._fade_type:
            elapsed = _time_mod.time() - self._fade_start
            progress = min(elapsed / self._fade_duration, 1.0)

            if self._fade_type == 'from_black':
                alpha = int(255 * (1.0 - progress))
            elif self._fade_type == 'to_black':
                alpha = int(255 * progress)
            elif self._fade_type == 'flash_white':
                alpha = int(255 * (1.0 - progress))
            else:
                alpha = 0

            if alpha > 0:
                fade_surf = pygame.Surface((sw, sh))
                if self._fade_type == 'flash_white':
                    fade_surf.fill((255, 255, 255))
                else:
                    fade_surf.fill((0, 0, 0))
                fade_surf.set_alpha(alpha)
                screen.blit(fade_surf, (0, 0))

            if progress >= 1.0:
                self._fade_type = None


def action_fade_to_black(quest_mgr, ctx=None, duration=1.0):
    """黑屏渐入效果"""
    print(f"[Quest] Action: FADE_TO_BLACK - 黑屏渐入 ({duration}s)")
    sfx = getattr(ctx, 'screen_effects', None) if ctx else None
    if sfx:
        sfx.start_fade('to_black', duration)
    else:
        quest_mgr.set_flag('screen_fade', {'type': 'to_black', 'duration': float(duration), 'start_time': None})


def action_fade_from_black(quest_mgr, ctx=None, duration=1.0):
    """黑屏渐出效果"""
    print(f"[Quest] Action: FADE_FROM_BLACK - 黑屏渐出 ({duration}s)")
    sfx = getattr(ctx, 'screen_effects', None) if ctx else None
    if sfx:
        sfx.start_fade('from_black', duration)
    else:
        quest_mgr.set_flag('screen_fade', {'type': 'from_black', 'duration': float(duration), 'start_time': None})


def action_flash_white(quest_mgr, ctx=None, duration=0.3):
    """白屏闪烁效果 - 被打击时的视觉反馈"""
    print(f"[Quest] Action: FLASH_WHITE - 白屏闪烁 ({duration}s)")
    sfx = getattr(ctx, 'screen_effects', None) if ctx else None
    if sfx:
        sfx.start_fade('flash_white', duration)
    else:
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
            sfx = getattr(ctx, 'screen_effects', None)
            if sfx:
                sfx.start_fade('to_black', 2.0)


# ═══════════════════════════════════════════════════════════════════
# 通用 NPC 查找（统一入口，支持名字/ID/PLAYER）
# ═══════════════════════════════════════════════════════════════════

def _find_npc(ctx, npc_spec):
    """
    通用 NPC 查找函数
    
    优先使用 _helpers.py 中的 find_npc_by_id / find_npc_by_name。
    
    Args:
        ctx: 游戏上下文
        npc_spec: NPC 标识，支持：
            - 'PLAYER' / '我'：玩家
            - 数字字符串（如 '8001'）：按 ID 查找
            - NPC 名字（如 '鱼西施'）：按名字查找
    
    Returns:
        card 对象或 None
    """
    if not npc_spec or not ctx:
        return None
    
    spec = npc_spec.strip()
    all_cards = getattr(ctx, 'all_cards', [])
    
    # 1. 玩家
    if spec.upper() in ('PLAYER', '我'):
        return getattr(ctx, 'player', None)
    
    # 2. 纯数字 → 按 ID 查找
    if spec.isdigit():
        npc = find_npc_by_id(all_cards, int(spec))
        if npc:
            return npc
    
    # 3. 按名字查找
    npc = find_npc_by_name(all_cards, spec)
    return npc


def _add_to_story_actors(story_ui, npc):
    """
    将 NPC 添加到剧情演员列表，确保剧情期间可以移动。
    
    注意：剧情系统会自动从对话中提取说话人作为演员，
    但移动的目标 NPC 可能不在对话中，需要手动添加。
    """
    if not story_ui or not npc:
        return
    
    npc_id = getattr(npc, 'id', None)
    if npc_id is not None:
        story_ui.story_actor_ids.add(npc_id)
    
    # 如果是玩家，确保相关的特殊 ID 也在集合中
    if getattr(npc, 'is_player', False):
        story_ui.story_actor_ids.add(0)
        story_ui.story_actor_ids.add(9999)


# ═══════════════════════════════════════════════════════════════════
# 位置解析（地标 / 坐标 / 相对玩家）
# ═══════════════════════════════════════════════════════════════════

def _resolve_location(wm, location, player=None):
    """
    将位置描述解析为世界坐标 (x, y)
    
    支持格式：
    - 地标名：EAST_GATE / WEST_GATE / NORTH_GATE / SOUTH_GATE / CITY_CENTER / MARKET
    - 坐标格式：x,y（如 2800,1500）
    - 相对玩家：@PLAYER 或 @PLAYER:dx,dy（偏移）
    
    Args:
        wm: WorldMap 实例
        location: 位置描述字符串
        player: 玩家 card（用于 @PLAYER 格式）
    
    Returns:
        (x, y) 元组 或 None
    """
    if not location:
        return None
    
    loc = location.strip()
    
    # 1. 坐标格式：x,y
    if ',' in loc and not loc.startswith('@'):
        try:
            parts = loc.split(',')
            return (float(parts[0].strip()), float(parts[1].strip()))
        except (ValueError, IndexError):
            print(f"[Quest] _resolve_location: 无效坐标格式 '{loc}'")
            return None
    
    # 2. 相对玩家格式：@PLAYER 或 @PLAYER:dx,dy
    if loc.upper().startswith('@PLAYER'):
        if not player:
            print("[Quest] _resolve_location: @PLAYER 但找不到玩家")
            return None
        dx, dy = 0, 0
        if ':' in loc:
            offset_str = loc.split(':', 1)[1]
            try:
                parts = offset_str.split(',')
                dx = float(parts[0].strip())
                dy = float(parts[1].strip()) if len(parts) > 1 else 0
            except (ValueError, IndexError):
                print(f"[Quest] _resolve_location: 无效偏移格式 '{offset_str}'")
        return (player.rect.centerx + dx, player.rect.centery + dy)
    
    # 3. 地标名
    loc_upper = loc.upper()
    if loc_upper == 'EAST_GATE':
        g = wm.gates.get('EAST')
        return (g.centerx, g.centery) if g else None
    elif loc_upper == 'EAST_GATE_INNER':
        g = wm.gates.get('EAST')
        return (g.centerx - 150, g.centery) if g else None
    elif loc_upper == 'WEST_GATE':
        g = wm.gates.get('WEST')
        return (g.centerx, g.centery) if g else None
    elif loc_upper == 'NORTH_GATE':
        g = wm.gates.get('NORTH')
        return (g.centerx, g.centery) if g else None
    elif loc_upper == 'SOUTH_GATE':
        g = wm.gates.get('SOUTH')
        return (g.centerx, g.centery) if g else None
    elif loc_upper == 'CITY_CENTER':
        return (wm.city_rect.centerx, wm.city_rect.centery)
    elif loc_upper == 'MARKET':
        return (wm.market_rect.centerx, wm.market_rect.centery)
    
    print(f"[Quest] _resolve_location: 未知位置 '{loc}'")
    return None


# ═══════════════════════════════════════════════════════════════════
# 通用 NPC 移动指令
# ═══════════════════════════════════════════════════════════════════

def action_npc_goto(quest_mgr, ctx=None, npc_spec='', location=''):
    """
    【通用 NPC 移动指令】
    
    让指定 NPC 移动到目标位置，对话暂停等待到达。
    内部使用封装好的 set_movement_target() 方法（通过 MoveToPosition AtomicAction）。
    
    CSV 用法示例：
    - NPC_GOTO:鱼西施:EAST_GATE         # 按名字查找，移动到地标
    - NPC_GOTO:8001:CITY_CENTER          # 按 ID 查找，移动到地标
    - NPC_GOTO:鱼西施:2800,1500          # 移动到坐标
    - NPC_GOTO:PLAYER:CITY_CENTER        # 玩家移动（替代 PLAYER_WALK_TO）
    - NPC_GOTO:猎户张三:@PLAYER          # 移动到玩家位置
    - NPC_GOTO:鱼西施:@PLAYER:50,0       # 移动到玩家右侧50像素
    
    支持的位置格式：
    - 地标：EAST_GATE / WEST_GATE / NORTH_GATE / SOUTH_GATE / CITY_CENTER / MARKET
    - 坐标：x,y（如 2800,1500）
    - 相对玩家：@PLAYER 或 @PLAYER:dx,dy
    """
    if not ctx:
        print("[Quest] NPC_GOTO: 无 ctx")
        return
    
    wm = getattr(ctx, 'world_map', None)
    story_ui = getattr(ctx, 'story_ui', None)
    player = getattr(ctx, 'player', None)
    
    if not wm:
        print("[Quest] NPC_GOTO: 无 world_map")
        return
    
    # 1. 查找移动的 NPC（统一使用 _find_npc）
    npc = _find_npc(ctx, npc_spec)
    if not npc:
        print(f"[Quest] NPC_GOTO: 找不到目标 NPC '{npc_spec}'")
        return
    
    # 2. 解析目标位置（统一使用 _resolve_location）
    target = _resolve_location(wm, location, player)
    if not target:
        print(f"[Quest] NPC_GOTO: 无法解析目标位置 '{location}'")
        return
    
    target_x, target_y = target
    npc_display_name = getattr(npc, 'name', npc_spec)
    print(f"[Quest] Action: NPC_GOTO {npc_display_name} -> {location} ({target_x:.0f}, {target_y:.0f})")
    
    # 3. 确保该 NPC 在剧情演员列表中（否则剧情期间不会更新移动）
    _add_to_story_actors(story_ui, npc)
    
    # 4. 暂停对话，等待 NPC 走到
    if story_ui:
        story_ui.waiting_for_action = True
    
    # 5. 使用 AtomicAction 系统（内部调用 set_movement_target）
    from src.atomic_actions import MoveToPosition
    
    class _GotoTarget(MoveToPosition):
        """带回调的移动：到达后恢复对话"""
        def __init__(self, x, y, story_ui_ref, npc_name_ref, location_ref):
            super().__init__(x, y, stop_dist=30, reason=f"剧情移动到{location_ref}", timeout=15000)
            self._story_ui_ref = story_ui_ref
            self._npc_name_ref = npc_name_ref
            self._location_ref = location_ref

        def on_end(self, agent):
            super().on_end(agent)
            if self._story_ui_ref:
                self._story_ui_ref.waiting_for_action = False
                print(f"[Quest] {self._npc_name_ref} 到达 {self._location_ref}，对话继续")
    
    # 清空现有动作队列，开始新的移动
    if hasattr(npc, 'action_queue'):
        npc.action_queue.clear()
        npc.action_queue.enqueue(_GotoTarget(target_x, target_y, story_ui, npc_display_name, location))
    else:
        # 没有 action_queue 的情况，直接使用 set_movement_target
        npc.set_movement_target(target_x, target_y, f"剧情移动到{location}")
        npc.state = STATE_MOVING
        npc.ai_reason = f"前往{location}"
        if story_ui:
            story_ui.waiting_for_action = False
        print(f"[Quest] NPC_GOTO: {npc_display_name} 无 action_queue，直接设置移动目标")


def action_npc_teleport(quest_mgr, ctx=None, npc_spec='', location=''):
    """
    【NPC 瞬移指令】
    
    立即将 NPC 传送到目标位置（不播放移动动画）。
    内部使用封装好的 set_pos() 和 clear_movement_target() 方法。
    
    CSV 用法示例：
    - NPC_TELEPORT:鱼西施:EAST_GATE
    - NPC_TELEPORT:8001:2800,1500
    - NPC_TELEPORT:PLAYER:CITY_CENTER
    - NPC_TELEPORT:鱼西施:@PLAYER
    """
    if not ctx:
        print("[Quest] NPC_TELEPORT: 无 ctx")
        return
    
    wm = getattr(ctx, 'world_map', None)
    player = getattr(ctx, 'player', None)
    
    if not wm:
        print("[Quest] NPC_TELEPORT: 无 world_map")
        return
    
    # 1. 查找 NPC
    npc = _find_npc(ctx, npc_spec)
    if not npc:
        print(f"[Quest] NPC_TELEPORT: 找不到目标 NPC '{npc_spec}'")
        return
    
    # 2. 解析目标位置
    target = _resolve_location(wm, location, player)
    if not target:
        print(f"[Quest] NPC_TELEPORT: 无法解析目标位置 '{location}'")
        return
    
    target_x, target_y = target
    npc_display_name = getattr(npc, 'name', npc_spec)
    
    # 3. 使用封装好的 set_pos() 瞬移（禁止直接修改 rect）
    if hasattr(npc, 'set_pos'):
        npc.set_pos(target_x, target_y, f"剧情瞬移到{location}")
    else:
        # 兼容没有 set_pos 的情况（不应该发生，记录警告）
        npc.rect.centerx = target_x
        npc.rect.centery = target_y
        print(f"[Quest] 警告: {npc_display_name} 没有 set_pos 方法，回退到直接修改 rect")
    
    # 4. 清除移动目标，避免瞬移后继续向原目标移动
    if hasattr(npc, 'clear_movement_target'):
        npc.clear_movement_target(f"瞬移到{location}后清除移动目标")
    
    # 5. 重置状态
    if hasattr(npc, 'state'):
        npc.state = STATE_IDLE
    if hasattr(npc, 'ai_reason'):
        npc.ai_reason = ""
    
    print(f"[Quest] Action: NPC_TELEPORT {npc_display_name} -> {location} ({target_x:.0f}, {target_y:.0f})")


def action_npc_stop(quest_mgr, ctx=None, npc_spec=''):
    """
    【NPC 停止移动指令】
    
    让 NPC 立即停止移动。
    内部使用封装好的 clear_movement_target() 方法。
    
    CSV 用法示例：
    - NPC_STOP:鱼西施
    - NPC_STOP:PLAYER
    - NPC_STOP:8001
    """
    if not ctx:
        print("[Quest] NPC_STOP: 无 ctx")
        return
    
    # 1. 查找 NPC
    npc = _find_npc(ctx, npc_spec)
    if not npc:
        print(f"[Quest] NPC_STOP: 找不到目标 NPC '{npc_spec}'")
        return
    
    npc_display_name = getattr(npc, 'name', npc_spec)
    
    # 2. 清除移动目标和目标对象
    if hasattr(npc, 'clear_movement_target'):
        npc.clear_movement_target("剧情指令停止移动")
    
    # 3. 清空动作队列
    if hasattr(npc, 'action_queue'):
        npc.action_queue.clear()
    
    # 4. 重置状态
    if hasattr(npc, 'state'):
        npc.state = STATE_IDLE
    if hasattr(npc, 'ai_reason'):
        npc.ai_reason = ""
    
    print(f"[Quest] Action: NPC_STOP {npc_display_name}")


def action_start_auto_combat(quest_mgr, ctx=None):
    """自动战斗 - 玩家被动挨打，用于演出被群殴的场景"""
    print("[Quest] Action: START_AUTO_COMBAT - 自动战斗(被动挨打)")
    sfx = getattr(ctx, 'screen_effects', None) if ctx else None
    if sfx:
        sfx.start_fade('flash_white', 0.5)
    else:
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
    'NPC_GOTO': action_npc_goto,
    'NPC_TELEPORT': action_npc_teleport,
    'PLAYER_WALK_TO': lambda qm, ctx=None, loc='': action_npc_goto(qm, ctx, 'PLAYER', loc),
}
