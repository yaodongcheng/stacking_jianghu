# --- src/task/quest_types/choice.py ---
"""
CHOICE：选择分支任务（玩家做善/恶等抉择）

策划须知：
====================================================================
想加一个选择任务？两步：
  1. quest_config.csv 里写一行，type=CHOICE，next 字段填分支：
       GOOD:Q_NEXT_GOOD|EVIL:Q_NEXT_EVIL
  2. 想给某段选择配【数值奖惩】或【NPC 记忆注入】？
     在对应的 actions/<剧情>_event.py 里调用：
       register_effects('Q_XXX', {
           'GOOD': {'text': '出手相救', 'fame': +10, 'morality': +10},
           'EVIL': {'text': '助纣为虐', 'fame': -5, 'money': +20,
                    'bounty': {...}, 'message': '你选择了黑暗面...'},
       })
       register_memory_hook('Q_XXX', my_memory_func)
     效果会在玩家选择时自动结算，无需改 quest_system.py
====================================================================
"""

from ._base import QuestType, register


# ───────────────────────────────────────────────────────────────────
# 注册表：每段选择剧情自己注册自己的奖惩与记忆钩子
# ───────────────────────────────────────────────────────────────────

# {quest_id: {choice_key: {'text','hint','fame','morality','money','bounty','message'}}}
_EFFECTS: dict = {}

# {alias_quest_id: canonical_quest_id} —— 同一套效果被多个 quest_id 复用时
_ALIASES: dict = {}

# {quest_id: callable(qm, choice_key, player, all_cards, ft_manager)}
_MEMORY_HOOKS: dict = {}


def register_effects(quest_id, effects_by_choice):
    """注册选择任务的数值效果。每个 choice_key 对应一个效果字典。"""
    _EFFECTS[quest_id] = effects_by_choice


def register_alias(alias, canonical):
    """让 alias_quest_id 复用 canonical 的效果与记忆钩子。"""
    _ALIASES[alias] = canonical


def register_memory_hook(quest_id, hook):
    """注册"做出选择时给所有当事人写记忆"的回调。"""
    _MEMORY_HOOKS[quest_id] = hook


def get_effects(quest_id, choice_key):
    """查询某段选择的效果（解 alias 后返回）。"""
    qid = _ALIASES.get(quest_id, quest_id)
    return _EFFECTS.get(qid, {}).get(choice_key, {})


def _get_memory_hook(quest_id):
    qid = _ALIASES.get(quest_id, quest_id)
    return _MEMORY_HOOKS.get(qid)


# ───────────────────────────────────────────────────────────────────
# QuestType 插件
# ───────────────────────────────────────────────────────────────────

@register
class ChoiceType(QuestType):
    name = "CHOICE"

    def objective_text(self, q):
        return ""  # 抉择不需要"完成条件"文案

    def progress_text(self, q, player, all_cards):
        return ""

    # ── 业务方法（被 QuestManager 委托调用）─────────────────────────

    def get_options(self, q):
        """返回 UI 用的选项列表 [{'key','text','hint'}, ...]"""
        if not q or q.type != 'CHOICE':
            return []

        options = []
        for choice_key in q.branches.keys():
            effects = get_effects(q.id, choice_key)

            # 选项文本：优先 effects['text']，其次 choice_key 本身
            text = effects.get('text') or choice_key

            # 提示文本：自动从 effects 拼出 +X声望/+X铜/[!]悬赏
            hints = []
            fame = effects.get('fame', 0)
            if fame > 0:
                hints.append(f"+{fame}声望")
            elif fame < 0:
                hints.append(f"{fame}声望")

            money = effects.get('money', 0)
            if money > 0:
                hints.append(f"+{money}铜")
            elif money < 0:
                hints.append(f"{money}铜")

            if effects.get('bounty'):
                hints.append("[!] 被悬赏")

            options.append({
                'key': choice_key,
                'text': text,
                'hint': ' | '.join(hints),
            })

        return options

    def apply_choice(self, qm, choice_key, player=None,
                     faction_war_system=None, ft_manager=None, all_cards=None):
        """执行一次选择：写记忆 → 发奖惩 → 推进任务。

        Returns: (success, next_quest_id, message)
        """
        q = qm.get_current_quest()
        if not q or q.type != 'CHOICE':
            return False, None, "当前任务不是选择类型"
        if choice_key not in q.branches:
            return False, None, f"无效的选择: {choice_key}"

        next_quest_id = q.branches[choice_key]
        effects = get_effects(q.id, choice_key)

        # 1. 剧情记忆注入（per-quest 钩子，由各剧情 event 文件注册）
        memory_hook = _get_memory_hook(q.id)
        if memory_hook:
            try:
                memory_hook(qm, choice_key, player, all_cards, ft_manager)
            except Exception as e:
                print(f"[Choice] 记忆钩子执行失败 ({q.id}/{choice_key}): {e}")

        # 2. 数值效果结算
        if player and effects:
            self._apply_player_effects(player, effects, ft_manager, faction_war_system)

        # 3. 设置分支标记 + 推进任务
        qm.set_flag(f"choice_{q.id}", choice_key)
        qm.advance_quest(manual_next_id=next_quest_id)

        message = effects.get('message', '你做出了选择')
        print(f"[Choice] 分支: {q.id}/{choice_key} -> {next_quest_id}")
        return True, next_quest_id, message

    def _apply_player_effects(self, player, effects, ft_manager, faction_war_system):
        """把 effects dict 里的数值变化应用到 player 上。"""
        # 声望
        fame_delta = effects.get('fame', 0)
        if fame_delta:
            player.fame = max(0, player.fame + fame_delta)
            if ft_manager:
                color = (255, 215, 0) if fame_delta > 0 else (255, 80, 80)
                ft_manager.add_text(f"声望 {fame_delta:+d}",
                                    player.rect.centerx, player.rect.top - 30, color)

        # 道德值
        morality_delta = effects.get('morality', 0)
        if morality_delta:
            current = getattr(player, 'morality', 50)
            player.morality = max(0, min(100, current + morality_delta))

        # 金钱
        money_delta = effects.get('money', 0)
        if money_delta:
            player.money = max(0, player.money + money_delta)
            if ft_manager:
                color = (255, 215, 0) if money_delta > 0 else (255, 80, 80)
                ft_manager.add_text(f"铜钱 {money_delta:+d}",
                                    player.rect.centerx, player.rect.top - 50, color)

        # 悬赏
        bounty = effects.get('bounty')
        if bounty and faction_war_system:
            faction_war_system.post_bounty(
                issuer_org=bounty.get('issuer', 'YAMEN'),
                target_id=player.id,
                reward=bounty.get('reward', 50),
                reason=bounty.get('reason', '作恶多端'),
                is_player_target=True,
            )
            if ft_manager:
                ft_manager.add_text("[!] 被悬赏了！",
                                    player.rect.centerx, player.rect.top - 70, (255, 50, 50))

    def play_branch_dialog(self, qm, story_ui):
        """玩家选完分支后，播放对应分支任务的对话。"""
        from src.definitions import QS_ACTIVE
        q = qm.get_current_quest()
        if not q:
            return False
        dialogs = qm.get_dialog(q.id)
        if not dialogs:
            print(f"[Choice] 分支 {q.id} 没有配置对话")
            return False
        qm.quest_status = QS_ACTIVE
        story_ui.start_dialog(dialogs)
        print(f"[Choice] 开始播放分支对话: {q.id}")
        return True
