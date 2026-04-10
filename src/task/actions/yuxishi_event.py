# --- src/task/actions/yuxishi_event.py ---
"""
鱼西施事件 Action Handlers

鱼西施事件的所有专属逻辑：选择显示、正义/邪恶路线奖惩、
玩家攻击泼皮演出、泼皮逃跑、事件NPC释放、剧情记忆注入等。
从 quest_system.py 提取，所有函数签名统一为 (quest_mgr, ctx, *params)。
"""

import math
import random
from src.definitions import STATE_EVENT, STATE_IDLE, STATE_FLEEING
from ._helpers import find_npc_by_name


# ═══════════════════════════════════════════════════════════════
# Action Handlers
# ═══════════════════════════════════════════════════════════════

def action_show_choice(quest_mgr, ctx=None, choice_quest_id=None):
    """显示选择对话框 - 同时让玩家移动到事件现场"""
    print(f"[Quest] Action: SHOW_CHOICE - 准备显示选择界面 (目标任务: {choice_quest_id or '默认下一个'})")

    # ═══════════════════════════════════════════════════════════════
    # 【大宋实况事件】检查是否是大宋实况事件的选择
    # ═══════════════════════════════════════════════════════════════
    try:
        from src.live_news_to_dialog import get_news_dialog_bridge
        news_bridge = get_news_dialog_bridge()

        if news_bridge.is_choice_pending():
            current_news = news_bridge.get_current_news()
            story_choices = current_news.story_choices if current_news and hasattr(current_news, 'story_choices') else []
            if current_news and story_choices:
                print(f"[Quest] SHOW_EVENT_CHOICE - 大宋实况事件选择，共 {len(story_choices)} 个选项")

                options = []
                for i, choice in enumerate(story_choices):
                    if isinstance(choice, dict):
                        option_data = choice.copy()
                        option_data['key'] = chr(ord('A') + i) if i < 3 else str(i)
                        if 'hint' not in option_data:
                            effect = choice.get('effect', '')
                            option_data['hint'] = effect[:30] if effect else ''
                    else:
                        option_data = {
                            'key': chr(ord('A') + i) if i < 3 else str(i),
                            'text': str(choice),
                            'hint': ''
                        }
                    options.append(option_data)

                if ctx and hasattr(ctx, 'story_ui') and ctx.story_ui:
                    prompt = current_news.title if hasattr(current_news, 'title') else "做出你的选择"
                    ctx.story_ui.show_choice(options, prompt)
                    print(f"[Quest] 大宋实况事件选择界面已显示")
                return
            else:
                print(f"[Quest] 警告：大宋实况事件没有选项数据")
    except Exception as e:
        print(f"[Quest] 检查大宋实况事件失败: {e}")

    # ═══════════════════════════════════════════════════════════════
    # 主线任务选择（原有逻辑）
    # ═══════════════════════════════════════════════════════════════
    quest_mgr.pending_choice_dialog = True

    if ctx:
        player = getattr(ctx, 'player', None)
        event_focus = getattr(ctx, 'event_focus_point', None)

        if player and event_focus:
            from src.atomic_actions import MoveToPosition

            occupied_positions = []
            yuxishi = getattr(ctx, 'yuxishi_npc', None)
            popi_npcs = getattr(ctx, 'popi_npcs', [])

            if yuxishi:
                occupied_positions.append((yuxishi.rect.centerx, yuxishi.rect.centery))
            for popi in popi_npcs:
                occupied_positions.append((popi.rect.centerx, popi.rect.centery))

            min_dist_to_npcs = 80
            candidate_positions = [
                (event_focus[0] + 120, event_focus[1] + 50),
                (event_focus[0] + 100, event_focus[1] - 50),
                (event_focus[0] + 150, event_focus[1]),
                (event_focus[0], event_focus[1] - 100),
                (event_focus[0] - 120, event_focus[1] - 50),
            ]

            def is_safe_position(px, py):
                for ox, oy in occupied_positions:
                    if math.hypot(px - ox, py - oy) < min_dist_to_npcs:
                        return False
                return True

            target_x, target_y = candidate_positions[0]
            for cx, cy in candidate_positions:
                if is_safe_position(cx, cy):
                    target_x, target_y = cx, cy
                    break

            move_action = MoveToPosition(target_x, target_y, stop_dist=20, reason="介入事件")
            player.action_queue.enqueue(move_action)
            player.ai_reason = "介入事件..."
            print(f"[Quest] 玩家开始移动到事件现场 ({target_x}, {target_y}), 避开{len(occupied_positions)}个NPC")

    if choice_quest_id and choice_quest_id in quest_mgr.quests:
        quest_mgr.advance_quest(manual_next_id=choice_quest_id)
    else:
        quest_mgr.advance_quest()


def action_reward_good(quest_mgr, ctx=None):
    """正义路线奖励 - 仅增加声望"""
    print("[Quest] Action: REWARD_GOOD - 发放正义奖励(声望)")
    if ctx and hasattr(ctx, 'player'):
        player = ctx.player
        player.fame = getattr(player, 'fame', 0) + 10

        if hasattr(ctx, 'ft_manager') and ctx.ft_manager:
            ctx.ft_manager.add_text("+10 声望", player.rect.centerx, player.rect.top - 30, (255, 215, 0))

    quest_mgr.set_flag('yuxishi_saved', True)
    quest_mgr.set_flag('choice_Q_YUXISHI_CHOICE', 'GOOD')


def action_trigger_bounty(quest_mgr, ctx=None):
    """邪恶路线触发悬赏"""
    print("[Quest] Action: TRIGGER_BOUNTY - 触发悬赏")
    if ctx:
        faction_war_system = getattr(ctx, 'faction_war_system', None)
        player = getattr(ctx, 'player', None)

        if faction_war_system and player:
            faction_war_system.post_bounty(
                issuer_org='YAMEN',
                target_id=getattr(player, 'id', 9999),
                reward=30,
                reason='欺压良善',
                is_player_target=True
            )

            player.money = getattr(player, 'money', 0) + 20
            player.fame = max(0, getattr(player, 'fame', 0) - 5)

            if hasattr(ctx, 'ft_manager') and ctx.ft_manager:
                ctx.ft_manager.add_text("+20 铜钱", player.rect.centerx, player.rect.top - 30, (255, 215, 0))
                ctx.ft_manager.add_text("-5 声望", player.rect.centerx, player.rect.top - 50, (255, 80, 80))
                ctx.ft_manager.add_text("[!] 被悬赏了！", player.rect.centerx, player.rect.top - 70, (255, 50, 50))

    quest_mgr.set_flag('yuxishi_saved', False)
    quest_mgr.set_flag('choice_Q_YUXISHI_CHOICE', 'EVIL')


def action_affinity_change(quest_mgr, ctx=None, amount='30'):
    """改变鱼西施对玩家的好感度"""
    print(f"[Quest] Action: AFFINITY_CHANGE - 调整好感度 {amount}")
    try:
        delta = int(amount)
    except Exception:
        delta = 30

    if ctx and hasattr(ctx, 'all_cards'):
        npc = find_npc_by_name(ctx.all_cards, '鱼西施')
        if npc:
            current = getattr(npc, 'affinity_to_player', 0)
            npc.affinity_to_player = max(-100, min(100, current + delta))
            print(f"[Quest] 鱼西施好感度: {current} -> {npc.affinity_to_player}")

            if hasattr(ctx, 'ft_manager') and ctx.ft_manager:
                color = (255, 200, 100) if delta > 0 else (200, 100, 100)
                text = f"好感+{delta}" if delta > 0 else f"好感{delta}"
                ctx.ft_manager.add_text(text, npc.rect.centerx, npc.rect.top - 20, color)


def action_player_attack_popi(quest_mgr, ctx=None):
    """玩家攻击泼皮 - 剧情演出原子动作（暂停对话，玩家移动到目标再攻击）"""
    print("[Quest] Action: PLAYER_ATTACK_POPI - 玩家攻击泼皮（移动+攻击）")
    if not ctx:
        print("[Quest] ERROR: ctx is None!")
        return

    player = getattr(ctx, 'player', None)
    popi_list = getattr(ctx, 'popi_npcs', [])
    story_ui = getattr(ctx, 'story_ui', None)
    combat_manager = getattr(ctx, 'combat_manager', None)

    if not player or not popi_list:
        print("[Quest] ERROR: player or popi_npcs not found!")
        return

    target_popi = popi_list[0] if popi_list else None
    if not target_popi:
        return

    # 暂停对话，等待攻击完成
    if story_ui:
        story_ui.waiting_for_action = True
        print("[Quest] 对话已暂停，等待玩家攻击完成")

    def on_attack_complete():
        """攻击完成后的回调"""
        print("[Quest] 剧情攻击完成，恢复对话")
        if story_ui:
            story_ui.waiting_for_action = False

    from src.atomic_actions import MoveToPosition

    # ═══════════════════════════════════════════════════════════════
    # 【智能位置计算】改进版 - 优先从当前位置攻击
    # ═══════════════════════════════════════════════════════════════
    MIN_SAFE_DIST = 50
    ATTACK_RANGE = 100

    player_cx, player_cy = player.rect.centerx, player.rect.centery
    target_cx, target_cy = target_popi.rect.centerx, target_popi.rect.centery

    other_actor_positions = []
    yuxishi = getattr(ctx, 'yuxishi_npc', None)
    if yuxishi:
        other_actor_positions.append((yuxishi.rect.centerx, yuxishi.rect.centery, yuxishi.name))
    for popi in popi_list:
        if popi and popi != target_popi:
            other_actor_positions.append((popi.rect.centerx, popi.rect.centery, popi.name))

    print(f"[Quest] ═══════════════════════════════════════")
    print(f"[Quest] 【位置计算调试】")
    print(f"[Quest]   玩家当前位置: ({player_cx}, {player_cy})")
    print(f"[Quest]   攻击目标({target_popi.name}): ({target_cx}, {target_cy})")
    print(f"[Quest]   其他演员: {[(name, x, y) for x, y, name in other_actor_positions]}")

    current_dist_to_target = math.hypot(player_cx - target_cx, player_cy - target_cy)
    print(f"[Quest]   玩家与目标距离: {current_dist_to_target:.0f}px (攻击范围: {ATTACK_RANGE}px)")

    current_min_dist_to_others = float('inf')
    for ax, ay, name in other_actor_positions:
        d = math.hypot(player_cx - ax, player_cy - ay)
        current_min_dist_to_others = min(current_min_dist_to_others, d)
        print(f"[Quest]   与{name}的距离: {d:.0f}px")

    can_attack_from_here = (current_dist_to_target <= ATTACK_RANGE and
                            current_min_dist_to_others >= MIN_SAFE_DIST)

    if can_attack_from_here:
        print(f"[Quest] [ok] 玩家当前位置可以直接攻击，无需移动！")
        target_x, target_y = player_cx, player_cy
        need_move = False
    else:
        print(f"[Quest] [!] 需要移动到新位置（距离目标过远或与演员重叠）")
        need_move = True

        dx_player = player_cx - target_cx
        dy_player = player_cy - target_cy
        dist_player = math.hypot(dx_player, dy_player) or 1
        primary_dx = dx_player / dist_player
        primary_dy = dy_player / dist_player

        directions = [
            (primary_dx, primary_dy),
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (1, 1), (1, -1), (-1, 1), (-1, -1),
        ]

        best_pos = None
        best_score = float('inf')

        for i, (dx, dy) in enumerate(directions):
            length = math.hypot(dx, dy) or 1
            nx, ny = dx / length, dy / length

            check_dist = ATTACK_RANGE - 20
            cand_x = target_cx + nx * check_dist
            cand_y = target_cy + ny * check_dist

            min_dist_to_others = float('inf')
            closest_actor = "无"
            for ax, ay, name in other_actor_positions:
                d = math.hypot(cand_x - ax, cand_y - ay)
                if d < min_dist_to_others:
                    min_dist_to_others = d
                    closest_actor = name

            is_safe = min_dist_to_others >= MIN_SAFE_DIST
            dist_to_player = math.hypot(cand_x - player_cx, cand_y - player_cy)

            dir_name = ["玩家方向", "东", "西", "南", "北", "东南", "东北", "西南", "西北"][i] if i < 9 else f"方向{i}"
            print(f"[Quest]   候选[{dir_name}] ({cand_x:.0f},{cand_y:.0f}): "
                  f"离玩家{dist_to_player:.0f}px, 最近演员({closest_actor}){min_dist_to_others:.0f}px, "
                  f"{'[ok]安全' if is_safe else '[!]不安全'}")

            if is_safe and dist_to_player < best_score:
                best_score = dist_to_player
                best_pos = (cand_x, cand_y)

        if best_pos:
            target_x, target_y = best_pos
            print(f"[Quest] → 选择最佳位置: ({target_x:.0f}, {target_y:.0f})")
        else:
            target_x = target_cx + primary_dx * (ATTACK_RANGE - 10)
            target_y = target_cy + primary_dy * (ATTACK_RANGE - 10)
            print(f"[Quest] → 使用兜底位置: ({target_x:.0f}, {target_y:.0f})")

    print(f"[Quest] ═══════════════════════════════════════")

    # 创建攻击动作
    class ScriptedAttackAction:
        """剧情攻击原子动作 - 执行一次攻击并调用回调（兼容ActionQueue接口）"""
        def __init__(self, target, combat_mgr, ft_mgr, callback):
            self.target = target
            self.combat_manager = combat_mgr
            self.ft_manager = ft_mgr
            self.callback = callback
            self.finished = False
            self.attack_triggered = False
            self.delay_timer = 0

        def on_start(self, agent):
            agent.ai_reason = "挺身而出！"
            print(f"[Quest] ScriptedAttackAction.on_start: {agent.name} -> {self.target.name}")

        def on_tick(self, agent, dt_ms) -> bool:
            if self.finished:
                return False

            if not self.attack_triggered:
                if self.combat_manager and self.target:
                    self.combat_manager.apply_melee_attack(agent, self.target, [])
                    print(f"[Quest] 玩家攻击 {self.target.name} (使用战斗系统)")
                else:
                    attack_damage = 15
                    old_hp = self.target.hp
                    self.target.hp = max(0, self.target.hp - attack_damage)
                    print(f"[Quest] 玩家攻击 {self.target.name}: HP {old_hp} -> {self.target.hp}")
                    if self.ft_manager:
                        self.ft_manager.add_text(f"-{attack_damage}",
                                                 self.target.rect.centerx, self.target.rect.top - 20,
                                                 (255, 50, 50))

                if self.ft_manager:
                    self.ft_manager.add_text("出手相救！",
                                             agent.rect.centerx, agent.rect.top - 30,
                                             (100, 255, 100))

                self.attack_triggered = True
                agent.ai_reason = "一拳打倒！"

            self.delay_timer += dt_ms
            if self.delay_timer > 500:
                self.finished = True
                return False
            return True

        def on_end(self, agent):
            print(f"[Quest] ScriptedAttackAction.on_end: 攻击完成")
            if self.callback:
                self.callback()

        def __repr__(self):
            return "ScriptedAttackAction"

    ft_manager = getattr(ctx, 'ft_manager', None)
    attack_action = ScriptedAttackAction(target_popi, combat_manager, ft_manager, on_attack_complete)

    if need_move:
        move_action = MoveToPosition(target_x, target_y, stop_dist=20, reason="冲向泼皮")
        player.action_queue.enqueue(move_action)
        print(f"[Quest] 已安排移动动作: 玩家 -> ({target_x:.0f},{target_y:.0f})")

    player.action_queue.enqueue(attack_action)
    player.ai_reason = "挺身而出..."

    print(f"[Quest] 已安排剧情攻击：玩家 -> {target_popi.name}" +
          (f"（移动到({target_x:.0f},{target_y:.0f})后攻击）" if need_move else "（原地攻击）"))


def action_popi_flee(quest_mgr, ctx=None):
    """泼皮逃跑 - 剧情演出"""
    print("[Quest] Action: POPI_FLEE - 泼皮开始逃跑")
    if not ctx:
        return

    popi_list = getattr(ctx, 'popi_npcs', [])
    if not popi_list:
        popi_list = [c for c in ctx.all_cards if hasattr(c, 'name') and '泼皮' in c.name]

    for popi in popi_list:
        if not popi:
            continue
        popi.state = STATE_FLEEING
        popi.ai_reason = "落荒而逃..."

        if hasattr(ctx, 'world_map'):
            wm = ctx.world_map
            popi_x, popi_y = popi.rect.centerx, popi.rect.centery

            city_center_x = wm.city_rect.centerx
            city_center_y = wm.city_rect.centery

            dx = popi_x - city_center_x
            dy = popi_y - city_center_y
            dist = max(1, (dx**2 + dy**2)**0.5)

            flee_dist = 500
            flee_x = popi_x + int(dx / dist * flee_dist) + random.randint(-50, 50)
            flee_y = popi_y + int(dy / dist * flee_dist) + random.randint(-50, 50)

            flee_x = max(50, min(flee_x, wm.w - 50))
            flee_y = max(50, min(flee_y, wm.h - 50))

            popi.set_movement_target(flee_x, flee_y, reason="逃跑")
            popi.move_speed = 720.0

        popi_id = getattr(popi, 'id', None)
        if popi_id is not None and hasattr(ctx, 'story_ui'):
            ctx.story_ui.story_actor_ids.add(popi_id)
            print(f"[Quest] 已将 {popi.name}(ID:{popi_id}) 加入剧情演员列表")

        print(f"[Quest] {popi.name} 开始逃跑 -> 目标({flee_x}, {flee_y})")

    if hasattr(ctx, 'ft_manager') and popi_list:
        popi = popi_list[0]
        ctx.ft_manager.add_text("小子你等着！", popi.rect.centerx, popi.rect.top - 30, (255, 100, 100))


def action_release_event_npcs(quest_mgr, ctx=None):
    """释放事件 NPC 恢复正常 AI"""
    print("[Quest] Action: EVENT_NPC_RELEASE - 释放事件NPC")
    if not ctx:
        print("[Quest] ERROR: ctx is None, cannot release NPCs!")
        return

    yuxishi = getattr(ctx, 'yuxishi_npc', None)
    if yuxishi:
        old_state = yuxishi.state
        yuxishi.state = STATE_IDLE
        yuxishi.ai_reason = "卖鱼中..."
        print(f"[Quest] 释放 {yuxishi.name}: state {old_state} -> {yuxishi.state}")
    else:
        print("[Quest] WARNING: yuxishi_npc not found in ctx")

    popi_list = getattr(ctx, 'popi_npcs', [])
    print(f"[Quest] 泼皮列表长度: {len(popi_list)}")
    for popi in popi_list:
        if popi:
            old_state = popi.state
            if popi.state == STATE_EVENT:
                popi.state = STATE_IDLE
                popi.ai_reason = "游荡中..."
                print(f"[Quest] 释放 {popi.name}: state {old_state} -> {popi.state}")
            else:
                print(f"[Quest] 跳过 {popi.name}: 当前状态={old_state} (非EVENT)")

    all_cards = getattr(ctx, 'all_cards', [])
    event_npcs_released = 0
    for card in all_cards:
        if hasattr(card, 'state') and card.state == STATE_EVENT:
            old_state = card.state
            card.state = STATE_IDLE
            event_npcs_released += 1
            print(f"[Quest] 额外释放 {getattr(card, 'name', '?')}: {old_state} -> IDLE")

    if event_npcs_released > 0:
        print(f"[Quest] 额外释放了 {event_npcs_released} 个事件NPC")

    print("=" * 60)
    print("[Quest] === 剧情结束后NPC状态检查 ===")
    if yuxishi:
        print(f"  鱼西施: state={yuxishi.state}, in_combat={getattr(yuxishi, 'in_combat', False)}, safety={getattr(yuxishi, 'safety', '?')}, ai_reason={getattr(yuxishi, 'ai_reason', '?')}")
    for i, popi in enumerate(popi_list):
        if popi:
            print(f"  泼皮{i+1}({popi.name}): state={popi.state}, in_combat={getattr(popi, 'in_combat', False)}, safety={getattr(popi, 'safety', '?')}, ai_reason={getattr(popi, 'ai_reason', '?')}")
    print("=" * 60)


# ═══════════════════════════════════════════════════════════════
# 导出函数（供 QuestManager.make_choice 调用）
# ═══════════════════════════════════════════════════════════════

def get_choice_effects(quest_id, choice_key):
    """获取选择的效果数据"""
    CHOICE_EFFECTS = {
        'Q_YUXISHI_CHOICE': {
            'GOOD': {
                'fame': 10,
                'morality': 10,
                'message': '你出手相救，声名远扬',
            },
            'EVIL': {
                'fame': -5,
                'morality': -20,
                'money': 20,
                'bounty': {
                    'issuer': 'YAMEN',
                    'reward': 30,
                    'reason': '欺压良善'
                },
                'message': '你选择了黑暗面...',
            }
        },
    }

    quest_effects = CHOICE_EFFECTS.get(quest_id, {})
    return quest_effects.get(choice_key, {})


def apply_story_memories(quest_mgr, quest_id, choice_key, player, all_cards, ft_manager=None):
    """根据剧情分支为所有当事人添加记忆"""
    if not all_cards:
        print("[Quest] 警告: all_cards 为空，无法生成剧情记忆")
        return

    def _find(name):
        for card in all_cards:
            if hasattr(card, 'name') and name in card.name:
                return card
        return None

    if quest_id == 'Q_YUXISHI_CHOICE':
        yuxishi = _find('鱼西施')
        popi_niuer = _find('泼皮牛二')
        popi_goudan = _find('泼皮狗蛋')

        # 无论玩家选什么，鱼西施都被泼皮欺负过
        if yuxishi:
            if popi_niuer:
                yuxishi.add_memory(
                    event_type='BULLIED_BY',
                    target_id=getattr(popi_niuer, 'id', None),
                    target_name='泼皮牛二',
                    description='在城东街头被泼皮牛二骚扰欺负',
                    importance=4
                )
                yuxishi.modify_affinity(getattr(popi_niuer, 'id', 0), -40)

            if popi_goudan:
                yuxishi.add_memory(
                    event_type='BULLIED_BY',
                    target_id=getattr(popi_goudan, 'id', None),
                    target_name='泼皮狗蛋',
                    description='泼皮狗蛋帮着牛二一起欺负自己',
                    importance=3
                )
                yuxishi.modify_affinity(getattr(popi_goudan, 'id', 0), -30)

        if popi_niuer and yuxishi:
            popi_niuer.add_memory(
                event_type='BULLIED',
                target_id=getattr(yuxishi, 'id', None),
                target_name='鱼西施',
                description='在城东街头调戏欺负鱼西施',
                importance=2
            )

        if popi_goudan and yuxishi:
            popi_goudan.add_memory(
                event_type='BULLIED',
                target_id=getattr(yuxishi, 'id', None),
                target_name='鱼西施',
                description='跟着牛二一起欺负鱼西施',
                importance=2
            )

        # ─── 玩家选择 GOOD：出手相救 ───
        if choice_key == 'GOOD':
            player_id = getattr(player, 'id', 9999)
            player_name = getattr(player, 'name', '玩家')

            if yuxishi:
                yuxishi.add_memory(
                    event_type='HELPED_BY',
                    target_id=player_id,
                    target_name=player_name,
                    description=f'{player_name}挺身而出，救我于泼皮之手',
                    importance=5
                )
                yuxishi.modify_affinity(player_id, +50)
                yuxishi.affinity_to_player = yuxishi.get_affinity_to(player_id)

                if ft_manager:
                    ft_manager.add_text("鱼西施好感度 +50",
                                        yuxishi.rect.centerx, yuxishi.rect.top - 60, (255, 200, 255))

            if popi_niuer:
                popi_niuer.add_memory(
                    event_type='FOUGHT_WITH',
                    target_id=player_id,
                    target_name=player_name,
                    description=f'在欺负鱼西施时被{player_name}阻止，动了手',
                    importance=4
                )
                popi_niuer.modify_affinity(player_id, -40)
                popi_niuer.sync_affinity_to_player(player_id)

            if popi_goudan:
                popi_goudan.add_memory(
                    event_type='FOUGHT_WITH',
                    target_id=player_id,
                    target_name=player_name,
                    description=f'被{player_name}打了，怀恨在心',
                    importance=3
                )
                popi_goudan.modify_affinity(player_id, -30)
                popi_goudan.sync_affinity_to_player(player_id)

            if player and hasattr(player, 'add_memory'):
                player.add_memory(
                    event_type='HELPED',
                    target_id=getattr(yuxishi, 'id', None) if yuxishi else None,
                    target_name='鱼西施',
                    description='在城东出手相救被泼皮欺负的鱼西施',
                    importance=4
                )
                if yuxishi and hasattr(player, 'modify_affinity'):
                    player.modify_affinity(getattr(yuxishi, 'id', 0), +30)

                if popi_niuer:
                    player.add_memory(
                        event_type='FOUGHT_WITH',
                        target_id=getattr(popi_niuer, 'id', None),
                        target_name='泼皮牛二',
                        description='为救鱼西施与泼皮牛二动手',
                        importance=3
                    )
                    if hasattr(player, 'modify_affinity'):
                        player.modify_affinity(getattr(popi_niuer, 'id', 0), -20)

                if popi_goudan:
                    player.add_memory(
                        event_type='FOUGHT_WITH',
                        target_id=getattr(popi_goudan, 'id', None),
                        target_name='泼皮狗蛋',
                        description='与泼皮狗蛋一起打了一架',
                        importance=2
                    )
                    if hasattr(player, 'modify_affinity'):
                        player.modify_affinity(getattr(popi_goudan, 'id', 0), -20)

            try:
                from src.llm.event_memory_bridge import inject_help_memory
                if yuxishi:
                    inject_help_memory(player, yuxishi, "出手相救")
            except Exception as e:
                print(f"[Quest] LLM记忆注入失败: {e}")

            print(f"[Quest] 记忆系统: 玩家选择GOOD，已为鱼西施、泼皮、玩家添加记忆")

        # ─── 玩家选择 EVIL：助纣为虐 ───
        elif choice_key == 'EVIL':
            player_id = getattr(player, 'id', 9999)
            player_name = getattr(player, 'name', '玩家')

            if yuxishi:
                yuxishi.add_memory(
                    event_type='BULLIED_BY',
                    target_id=player_id,
                    target_name=player_name,
                    description=f'{player_name}不仅不帮忙，还和泼皮一起欺负我',
                    importance=5
                )
                yuxishi.modify_affinity(player_id, -60)
                yuxishi.affinity_to_player = yuxishi.get_affinity_to(player_id)

                if ft_manager:
                    ft_manager.add_text("鱼西施好感度 -60",
                                        yuxishi.rect.centerx, yuxishi.rect.top - 60, (255, 50, 50))

            if popi_niuer:
                popi_niuer.add_memory(
                    event_type='PARTNERED_WITH',
                    target_id=player_id,
                    target_name=player_name,
                    description=f'{player_name}和咱们一起欺负鱼西施，是自己人',
                    importance=3
                )
                popi_niuer.modify_affinity(player_id, +30)
                popi_niuer.sync_affinity_to_player(player_id)

            if popi_goudan:
                popi_goudan.add_memory(
                    event_type='PARTNERED_WITH',
                    target_id=player_id,
                    target_name=player_name,
                    description=f'{player_name}帮着我们欺负人，够意思',
                    importance=2
                )
                popi_goudan.modify_affinity(player_id, +20)
                popi_goudan.sync_affinity_to_player(player_id)

            if player and hasattr(player, 'add_memory'):
                player.add_memory(
                    event_type='BULLIED',
                    target_id=getattr(yuxishi, 'id', None) if yuxishi else None,
                    target_name='鱼西施',
                    description='在城东和泼皮一起欺负鱼西施，分了赃',
                    importance=4
                )
                if yuxishi and hasattr(player, 'modify_affinity'):
                    player.modify_affinity(getattr(yuxishi, 'id', 0), -10)

                if popi_niuer and hasattr(player, 'modify_affinity'):
                    player.modify_affinity(getattr(popi_niuer, 'id', 0), +15)
                if popi_goudan and hasattr(player, 'modify_affinity'):
                    player.modify_affinity(getattr(popi_goudan, 'id', 0), +10)

            print(f"[Quest] 记忆系统: 玩家选择EVIL，已为所有当事人添加记忆")


# ======================== Handler 注册表 ========================
HANDLERS = {
    'SHOW_CHOICE': action_show_choice,
    'SHOW_EVENT_CHOICE': action_show_choice,  # 别名
    'REWARD_GOOD': action_reward_good,
    'TRIGGER_BOUNTY': action_trigger_bounty,
    'AFFINITY_YUXISHI': action_affinity_change,
    'PLAYER_ATTACK_POPI': action_player_attack_popi,
    'POPI_FLEE': action_popi_flee,
    'EVENT_NPC_RELEASE': action_release_event_npcs,
}
