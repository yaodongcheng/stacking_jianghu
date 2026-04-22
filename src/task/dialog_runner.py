# --- src/task/dialog_runner.py ---
"""
对话流转引擎

策划须知：
- 这个文件管"什么时候播什么对话、对话结束后怎么推进任务"
- 对话内容本身写在 dialog_config.csv，不在代码里
- 想改某种状态下的对话流转规则（比如"接任务时弹什么、提醒玩家时弹什么"）→ 改这里

包含三个职责：
- 对话播放触发：玩家点 NPC 时播什么（try_trigger_npc_interaction）
- 对话结束后处理：状态推进、记忆注入（on_dialog_finished）
- 调试快进：开发时跳过对话（skip_current_dialogs）
"""

from src.definitions import QS_AVAILABLE, QS_ACTIVE, QS_READY
from .quest_data import DialogData
from .npc_registry import ID_PLAYER, ID_VILLAGE_HEAD
from .action_dispatcher import is_cinematic_action


def _make_system_dialog(speaker_name, speaker_id, text):
    """构造一条系统兜底对话（没配 dialog 时用，避免 NPC 干站着）"""
    return type('DialogData', (object,), {
        'quest_id': 'SYS', 'speaker': speaker_name,
        'text': text, 'bg_img': '', 'action': '', 'speaker_id': speaker_id,
    })


class DialogRunner:
    """对话流转引擎。挂在 QuestManager 上，通过 self.qm 访问任务状态。"""

    def __init__(self, qm):
        self.qm = qm

    # ═══════════════════════════════════════════════════════════════
    # 1. 对话结束回调（StoryUI 播完最后一句时调用）
    # ═══════════════════════════════════════════════════════════════
    def on_dialog_finished(self, npc_id=None, ctx=None, npc_name=None):
        """整段对话播完后处理：注入 NPC 记忆，推进任务状态。

        Args:
            npc_id:   说话方的数字 ID（用于匹配 submit_npc）
            ctx:      游戏上下文（含 story_ui / all_cards）
            npc_name: 说话方的名字（按名字匹配 submit_npc 时用）
        """
        qm = self.qm
        q = qm.get_current_quest()
        print(f"[Quest] 对话序列结束 | 当前任务:{qm.active_quest_id} | 状态:{qm.quest_status} | 类型:{q.type if q else '?'}")

        # 在记忆注入清空对话数据前，收集这段对话所有说话人名字（用于 INTERACT 目标匹配）
        # 因为对话最后一句很可能是"我"（玩家），单看 last_speaker 会漏掉真正的目标 NPC
        all_speaker_names = set()
        story_ui = getattr(ctx, 'story_ui', None) if ctx else None
        if story_ui:
            dlg_data = getattr(story_ui, '_current_dialog_data', None) or []
            for d in dlg_data:
                spk = getattr(d, 'speaker', None)
                if spk:
                    all_speaker_names.add(spk)

        # 把这段对话注入参与 NPC 的 LLM 记忆
        self._inject_dialog_memory_to_npcs(ctx, q)

        # 路径 1：接取任务（AVAILABLE → ACTIVE）
        if qm.quest_status == QS_AVAILABLE and q:
            # CLICKNPC 任务必须等玩家点对应 NPC（_handle_accept_dialog 那条路）；
            # 过场对话播完(npc_id=None) 不算"接取"，否则会跳过 NPC 交互直接进 ACTIVE，
            # 玩家再点 NPC 就只能弹 REMIND 了。
            if q.trigger == 'CLICKNPC':
                return
            npc_matched = qm._match_submit_npc(npc_id, npc_name, q.submit_npc)
            if npc_id is None or npc_matched:
                qm.accept_quest()
            return

        # 路径 2：完成对话型任务（ACTIVE → READY）
        if qm.quest_status == QS_ACTIVE and q and q.type in ('DIALOG', 'INTERACT'):
            target_check = (q.type == 'DIALOG') or (
                q.type == 'INTERACT' and (
                    str(npc_id) == q.target
                    or npc_name == q.target
                    or q.target in all_speaker_names
                )
            )
            if not target_check:
                return

            qm.quest_status = QS_READY
            print(f"[Quest] 对话类任务 {q.id} 目标达成 -> READY")

            # DIALOG / INTERACT 任务都自动推进到下一段
            # （INTERACT 的"提交"动作本质就是和目标 NPC 对完这段话，无需再点一次）
            if q.type in ('DIALOG', 'INTERACT') and q.next_id and q.next_id in qm.quests:
                self._auto_advance_dialog_chain(q, ctx)

    def _auto_advance_dialog_chain(self, current_quest, ctx):
        """DIALOG 任务完成后推进到下一段。
        新逻辑：完全看 next.trigger 决定要不要播开场对白
          - AUTO         → 状态已是 ACTIVE，播开场对白
          - CLICKNPC:xx  → 状态已是 AVAILABLE，等玩家点 NPC，不主动播
          - 空(legacy)   → 走旧的隐式判断（DIALOG→DIALOG / 同 NPC 自动接）
        """
        qm = self.qm
        print(f"[Quest] DIALOG任务自动推进: {current_quest.id} -> {current_quest.next_id}")
        qm.advance_quest()

        next_q = qm.get_current_quest()
        if not next_q:
            return

        # 显式 trigger=AUTO：advance_quest 已置 ACTIVE，这里负责播开场对白
        if next_q.trigger == 'AUTO':
            dialogs = qm.get_dialog(next_q.id)
            if dialogs and ctx:
                print(f"[Quest] 播放下一段开场对白: {next_q.id} (trigger=AUTO)")
                ctx.story_ui.start_dialog(dialogs)
            return

        # 显式 trigger=CLICKNPC：等玩家点 NPC，不在这里播
        if next_q.trigger == 'CLICKNPC':
            return

        # ── 以下为旧配置兼容路径（trigger 为空）──
        # 下一段也是 DIALOG → 立即播
        if next_q.type == 'DIALOG':
            qm.quest_status = QS_ACTIVE
            print(f"[Quest] 任务接取(legacy): {next_q.id}")
            dialogs = qm.get_dialog(next_q.id)
            if dialogs and ctx:
                ctx.story_ui.start_dialog(dialogs)
            return

        # 下一段 submit_npc 与当前任务相同 → 自动接取（连续任务）
        if next_q.submit_npc == current_quest.submit_npc and qm.quest_status == QS_AVAILABLE:
            qm.quest_status = QS_ACTIVE
            print(f"[Quest] 连续任务自动接取(legacy): {next_q.id} (同一NPC: {current_quest.submit_npc})")
            dialogs = qm.get_dialog(next_q.id)
            if dialogs and ctx:
                ctx.story_ui.start_dialog(dialogs)

    # ═══════════════════════════════════════════════════════════════
    # 2. 玩家点 NPC 时触发的对话
    # ═══════════════════════════════════════════════════════════════
    def try_trigger_npc_interaction(self, target_npc, story_ui):
        """玩家点击/拖到 NPC 上时调用。返回 True 表示已处理。"""
        qm = self.qm
        q = qm.get_current_quest()
        if not q or not hasattr(target_npc, 'id'):
            return False

        # 点玩家自己 → 不触发任务交互（让详情页打开）
        if getattr(target_npc, 'job', None) == 'PLAYER':
            return False

        npc_id_str = str(target_npc.id)
        npc_name = getattr(target_npc, 'name', None)

        if qm.quest_status == QS_AVAILABLE:
            return self._handle_accept_dialog(target_npc, npc_name, q, story_ui)
        if qm.quest_status == QS_ACTIVE:
            return self._handle_active_dialog(target_npc, npc_name, npc_id_str, q, story_ui)
        if qm.quest_status == QS_READY:
            return self._handle_turn_in_dialog(target_npc, npc_name, q, story_ui)

        return False

    def _handle_accept_dialog(self, target_npc, npc_name, q, story_ui):
        """AVAILABLE 阶段：玩家找发布人接取任务。
        【新】优先读 trigger=CLICKNPC:<NPC名>；trigger 为空才回落到 submit_npc 兼容旧逻辑。
        """
        qm = self.qm
        matched = False
        if q.trigger == 'CLICKNPC' and q.trigger_npc:
            matched = (npc_name == q.trigger_npc)
        else:
            matched = qm._match_submit_npc(target_npc.id, npc_name, q.submit_npc)

        if not matched:
            return False
        dialogs = qm.get_dialog(q.id)
        if dialogs:
            story_ui.start_dialog(dialogs)
        qm.accept_quest()
        return True

    def _handle_active_dialog(self, target_npc, npc_name, npc_id_str, q, story_ui):
        """ACTIVE 阶段：交互型任务 / 找发布人提醒"""
        qm = self.qm

        # A. 交互类任务：跟目标 NPC 对上话（target 可填 NPC ID 或名字）
        if q.type == 'INTERACT' and (npc_id_str == q.target or npc_name == q.target):
            dialogs = qm.get_dialog(q.id)
            if dialogs:
                story_ui.start_dialog(dialogs)
            else:
                qm.quest_status = QS_READY
            return True

        # B. 找发布人提醒（REMIND）
        if not qm._match_submit_npc(target_npc.id, npc_name, q.submit_npc):
            return False

        # 声望检查任务的特殊处理
        if 'FAME_CHECK' in q.id:
            return self._handle_fame_check_dialog(target_npc, q, story_ui)

        # 普通任务的 REMIND 对话
        remind_dialogs = qm.get_dialog(q.id + "_REMIND")
        if remind_dialogs:
            story_ui.start_dialog(remind_dialogs)
        else:
            text = f"请尽快完成【{q.title}】，我们需要{q.target}。"
            story_ui.start_dialog([_make_system_dialog(target_npc.name, target_npc.id, text)])
        return True

    def _handle_fame_check_dialog(self, target_npc, q, story_ui):
        """声望检查类任务：声望不够弹 REMIND，够了弹正常对话并推进"""
        qm = self.qm

        if qm.get_flag('fame_insufficient', False):
            # 声望不足：弹 REMIND
            remind_dialogs = qm.get_dialog(q.id + "_REMIND")
            if remind_dialogs:
                story_ui.start_dialog(remind_dialogs)
            else:
                text = f"请尽快完成【{q.title}】，我们需要{q.target}。"
                story_ui.start_dialog([_make_system_dialog(target_npc.name, target_npc.id, text)])
        else:
            # 声望足够：弹正常对话或直接推进
            dialogs = qm.get_dialog(q.id)
            if dialogs:
                story_ui.start_dialog(dialogs)
            else:
                qm.advance_quest()
        return True

    def _handle_turn_in_dialog(self, target_npc, npc_name, q, story_ui):
        """READY 阶段：玩家找发布人交付任务"""
        qm = self.qm
        if not qm._match_submit_npc(target_npc.id, npc_name, q.submit_npc):
            return False

        finish_dialogs = qm.get_dialog(q.id + "_END")
        # 先推进任务数据，再播对话
        qm.advance_quest()

        if finish_dialogs:
            story_ui.start_dialog(finish_dialogs)
        elif q.type != 'DIALOG':
            # 兜底完成对话
            story_ui.start_dialog([_make_system_dialog(target_npc.name, target_npc.id, '做得好！这对村子帮助很大。')])
        return True

    # ═══════════════════════════════════════════════════════════════
    # 3. 对话记忆注入
    # ═══════════════════════════════════════════════════════════════
    def _inject_dialog_memory_to_npcs(self, ctx, quest):
        """把刚播完的剧情对话写入参与 NPC 的 LLM 记忆。
        解决 "NPC 失忆" 问题——StoryUI 播的剧情之前不会进 NPC 记忆。
        """
        if not ctx:
            return
        story_ui = getattr(ctx, 'story_ui', None)
        all_cards = getattr(ctx, 'all_cards', None)
        if not story_ui or not all_cards:
            print("[Quest] 无法注入对话记忆: 缺少 story_ui 或 all_cards")
            return

        dialog_summary = story_ui.get_last_dialog_summary()
        if not dialog_summary:
            print("[Quest] 无对话数据可注入")
            return

        speakers = dialog_summary['speakers']
        summary = dialog_summary['summary']
        quest_title = quest.title if quest else "一段对话"
        memory_content = f"【剧情】关于「{quest_title}」的对话：{summary}"

        print(f"[Quest] 注入对话记忆到 {len(speakers)} 个参与者: {memory_content[:80]}...")

        try:
            from src.llm.npc_memory import MemoryManager
            memory_mgr = MemoryManager.get_instance()

            injected_count = 0
            for card in all_cards:
                # 跳过玩家
                if getattr(card, 'is_player', False):
                    continue

                card_id = getattr(card, 'id', None)
                if card_id is None:
                    npc_data = getattr(card, 'npc_data', None)
                    if npc_data:
                        card_id = getattr(npc_data, 'id', None)

                if card_id is None or card_id not in speakers:
                    continue

                card_name = getattr(card, 'name', f'NPC_{card_id}')
                memory_sys = memory_mgr.get_npc_memory(card_id, card_name)
                memory_sys.add_event_memory(
                    event_desc=memory_content, importance=4, involved_npcs=[]
                )
                injected_count += 1
                print(f"[Quest] [ok] 已注入记忆到 {card_name} (ID={card_id})")

            print(f"[Quest] 对话记忆注入完成: {injected_count} 个NPC")

        except Exception as e:
            print(f"[Quest] 注入对话记忆失败: {e}")
            import traceback
            traceback.print_exc()

        story_ui.clear_dialog_data()

    # ═══════════════════════════════════════════════════════════════
    # 4. 开场剧情自动播放
    # ═══════════════════════════════════════════════════════════════
    def check_and_play_intro(self, all_cards, story_ui):
        """检查并播放开场剧情（main loop 调用）。

        通用机制：扫描所有 trigger=NEWGAME 的任务，若该任务正好是当前激活任务、
        precondition 通过且尚未播放过，则自动播放其对话。

        Q0_FIND_ELDER 因有动态分支（门客/独行者）走单独逻辑。
        """
        qm = self.qm

        # 通用配置驱动：trigger=NEWGAME 的任务自动播放
        for q in qm.quests.values():
            if q.trigger != 'NEWGAME':
                continue
            if qm.active_quest_id != q.id:
                continue
            played_flag = f'newgame_intro_played_{q.id}'
            if qm.flags.get(played_flag):
                continue
            if not self._check_precondition(q.precondition):
                continue

            qm.flags[played_flag] = True
            dialogs = qm.get_dialog(q.id)
            if dialogs:
                story_ui.start_dialog(dialogs)
                qm.quest_status = QS_ACTIVE
                print(f"[Quest] 自动激活了开场剧情 {q.id} (trigger=NEWGAME)")
                return True

        # 第二段：落地介绍（带门客/独行者两版，动态内容暂保留专用逻辑）
        if qm.active_quest_id == 'Q0_FIND_ELDER' and not qm.flags.get('intro_played_dialog'):
            qm.flags['intro_played'] = True
            qm.flags['intro_played_dialog'] = True

            follower = next((c for c in all_cards if getattr(c, 'is_follower', False)), None)
            dialog_key = 'INTRO_FOLLOWER' if follower else 'INTRO_SOLO'
            replacements = {'{follower}': follower.name} if follower else {}

            intro_dialogs = self.get_dialog_by_key(dialog_key, replacements)
            if intro_dialogs:
                story_ui.start_dialog(intro_dialogs)
                print("[Quest] 自动激活了第二段开场剧情 (教程模式)")
                return True

        return False

    def _check_precondition(self, precondition):
        """检查 precondition 表达式是否通过。

        目前支持：
        - 空字符串 / 'true' → 始终通过
        - 'flag:foo' → 检查 quest flag foo 为真
        - 'flag:foo;flag:bar' → 多条件 AND
        """
        cond = (precondition or '').strip().lower()
        if not cond or cond == 'true':
            return True

        for clause in cond.split(';'):
            clause = clause.strip()
            if not clause:
                continue
            if clause.startswith('flag:'):
                flag_name = clause[5:].strip()
                if not self.qm.flags.get(flag_name):
                    return False
            else:
                print(f"[Quest] 未知 precondition 子句: {clause}")
                return False
        return True

    # ═══════════════════════════════════════════════════════════════
    # 5. 模板替换的对话查询（如 {follower} → 实际门客名）
    # ═══════════════════════════════════════════════════════════════
    def get_dialog_by_key(self, key, replacements=None):
        """获取指定 key 的对话列表，支持 {占位符} 文本替换。
        replacements: 字典 { '{follower}': '张三' }
        """
        raw_dialogs = self.qm.dialogs.get(key, [])
        if not replacements:
            return raw_dialogs

        processed = []
        for d in raw_dialogs:
            new_d = DialogData({
                'quest_id': d.quest_id,
                'speaker': d.speaker,
                'text': d.text,
                'bg_img': d.bg_img,
                'action': d.action,
            })
            for k, v in replacements.items():
                if k in new_d.text:
                    new_d.text = new_d.text.replace(k, v)
                if k in new_d.speaker:
                    new_d.speaker = new_d.speaker.replace(k, v)
                    # speaker 改了要重新解析 ID
                    if new_d.speaker == '我':
                        new_d.speaker_id = ID_PLAYER
                    elif new_d.speaker == '村长':
                        new_d.speaker_id = ID_VILLAGE_HEAD
                    else:
                        new_d.speaker_id = 9998  # 临时占位
            processed.append(new_d)
        return processed

    # ═══════════════════════════════════════════════════════════════
    # 6. 调试跳过（开发期使用）
    # ═══════════════════════════════════════════════════════════════
    def skip_current_dialogs(self, ctx, _recursion_depth=0):
        """【调试】快速跳过当前任务的对话。
        - 跳过纯文字
        - 遇到 CHOICE / SHOW_CHOICE 停下来弹选项
        - 遇到演出型 action（如打斗动画）执行后停下，让玩家观看
        """
        MAX_RECURSION = 20
        if _recursion_depth > MAX_RECURSION:
            return False, f"跳过达到上限({MAX_RECURSION})"

        qm = self.qm
        story_ui = ctx.story_ui if ctx else None
        q = qm.get_current_quest()
        if not q:
            return False, "没有当前任务"

        # 1. CHOICE 任务 → 弹选项
        if q.type == 'CHOICE':
            if story_ui and getattr(story_ui, 'choice_mode', False):
                return True, "请做出选择"
            return self._show_choices_or_fail(q, story_ui)

        # 2. 正在播对话 → 跳过队列中的对话
        if story_ui and story_ui.is_active:
            return self._skip_active_dialog_queue(q, ctx, story_ui, _recursion_depth)

        # 3. 没在播对话 → 尝试触发当前任务的对话
        dialogs = qm.get_dialog_for_current_quest()
        if dialogs and story_ui:
            story_ui.start_dialog(dialogs)
            return self.skip_current_dialogs(ctx, _recursion_depth + 1)

        # 4. 没有对话可跳，按状态推进任务
        return self._advance_by_status(q, ctx, story_ui, _recursion_depth)

    def _show_choices_or_fail(self, q, story_ui):
        """显示选择 UI；不能显示就报失败"""
        options = self.qm.get_choice_options()
        if options and story_ui:
            prompt = q.title or "做出你的选择"
            story_ui.show_choice(options, prompt)
            return True, "请做出选择"
        return False, "选择任务需要玩家决定"

    def _skip_active_dialog_queue(self, q, ctx, story_ui, depth):
        """跳过 story_ui 当前对话队列里剩余的对话"""
        qm = self.qm
        skipped_count = 0

        # 先处理当前行的 action
        if story_ui.current_line and story_ui.current_line.action:
            result = self._handle_action_during_skip(
                story_ui.current_line.action, ctx, story_ui, dialog_line=None, skipped_count=0
            )
            if result is not None:
                return result

        # 处理队列里剩余对话
        while story_ui.dialog_queue:
            dialog_line = story_ui.dialog_queue.pop(0)
            skipped_count += 1
            if dialog_line.action:
                result = self._handle_action_during_skip(
                    dialog_line.action, ctx, story_ui, dialog_line, skipped_count
                )
                if result is not None:
                    return result

        # 队列空了，结束对话
        last_speaker_id = story_ui.current_line.speaker_id if story_ui.current_line else None
        story_ui.current_line = None
        story_ui.is_active = False
        story_ui.bg_image_surf = None
        story_ui._restore_actor_movement()

        self.on_dialog_finished(npc_id=last_speaker_id, ctx=ctx)

        # 待处理的 CHOICE 弹窗
        if qm.pending_choice_dialog:
            qm.pending_choice_dialog = False
            options = qm.get_choice_options()
            if options:
                prompt = q.title or "做出你的选择"
                story_ui.show_choice(options, prompt)
                return True, f"跳过{skipped_count}句，请选择"

        # 有新对话被启动 → 继续跳
        if story_ui.is_active:
            return self.skip_current_dialogs(ctx, depth + 1)

        # 任务变了 → 看新任务类型决定
        new_q = qm.get_current_quest()
        if new_q and new_q.id != q.id:
            if new_q.type == 'CHOICE':
                options = qm.get_choice_options()
                if options and story_ui:
                    story_ui.show_choice(options, new_q.title)
                    return True, f"跳过{skipped_count}句，请选择"
            elif new_q.type == 'DIALOG':
                dialogs = qm.get_dialog(new_q.id)
                if dialogs:
                    story_ui.start_dialog(dialogs)
                    return self.skip_current_dialogs(ctx, depth + 1)

        return True, f"跳过{skipped_count}句对话"

    def _handle_action_during_skip(self, action_str, ctx, story_ui, dialog_line, skipped_count):
        """跳过过程中遇到 action 的统一处理。返回 (bool, str) 表示要中止跳过，或 None 表示继续"""
        qm = self.qm

        # SHOW_CHOICE：执行后立即弹选项 UI
        if 'SHOW_CHOICE' in action_str:
            qm.trigger_action(action_str, ctx)
            story_ui.current_line = None
            story_ui.is_active = False
            story_ui.bg_image_surf = None
            story_ui._restore_actor_movement()
            options = qm.get_choice_options()
            if options:
                q = qm.get_current_quest()
                prompt = (q.title if q else "做出你的选择")
                story_ui.show_choice(options, prompt)
            msg = "请做出选择" if dialog_line is None else f"跳过{skipped_count}句，请选择"
            return True, msg

        # 演出型 action：执行后停下，让玩家观看
        if is_cinematic_action(action_str):
            qm.trigger_action(action_str, ctx)
            if dialog_line is None:
                # 当前行的 action：移到下一句
                if story_ui.dialog_queue:
                    story_ui.current_line = story_ui.dialog_queue.pop(0)
                    story_ui.text_progress = 0
                else:
                    story_ui.current_line = None
                    story_ui.is_active = False
                    story_ui._restore_actor_movement()
                return True, "演出中..."
            else:
                # 队列里的 action：把这行设为当前行
                story_ui.current_line = dialog_line
                story_ui.text_progress = len(dialog_line.text) if dialog_line.text else 0
                return True, f"跳过{skipped_count}句，演出中..."

        # 普通 action：执行后继续跳过
        qm.trigger_action(action_str, ctx)
        return None

    def _advance_by_status(self, q, ctx, story_ui, depth):
        """没有对话可跳时，按当前任务状态推进"""
        qm = self.qm

        if qm.quest_status == QS_AVAILABLE:
            qm.accept_quest()
            if story_ui and story_ui.is_active:
                return self.skip_current_dialogs(ctx, depth + 1)
            return True, f"接取: {q.title}"

        if qm.quest_status == QS_READY:
            qm.advance_quest()
            if story_ui and story_ui.is_active:
                return self.skip_current_dialogs(ctx, depth + 1)
            new_q = qm.get_current_quest()
            if new_q and new_q.type in ('DIALOG', 'CHOICE'):
                return self.skip_current_dialogs(ctx, depth + 1)
            return True, f"完成: {q.title}"

        if qm.quest_status == QS_ACTIVE:
            if q.type == 'DIALOG':
                qm.quest_status = QS_READY
                qm.advance_quest()
                if story_ui and story_ui.is_active:
                    return self.skip_current_dialogs(ctx, depth + 1)
                new_q = qm.get_current_quest()
                if new_q and new_q.type in ('DIALOG', 'CHOICE'):
                    return self.skip_current_dialogs(ctx, depth + 1)
                return True, f"跳过: {q.title}"
            return False, f"进行中: {q.title} (需要完成目标)"

        return False, "无法跳过当前状态"
