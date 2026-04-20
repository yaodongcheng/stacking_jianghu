# --- src/task/quest_system.py ---
"""
任务系统 - 管理主线任务、对话、任务状态

重构说明：
- 此文件已移动到 src/task/ 目录
- 任务基类 TaskBase 在同目录的 base.py
- QuestManager 管理 QuestData 和 DialogData
"""

import csv
import random
import os
from src.definitions import *
from src.entities import NPC
from src.utils import resource_path

# ======================== 从同目录模块导入 ========================
from .display import TaskDisplayData  # noqa: F401  re-export 兼容外部
from .base import (
    TaskCategory,
    TASK_PRIORITY as _TASK_PRIORITY,
    TASK_TYPE_STYLES as _TASK_TYPE_STYLES,
)

# NPC 映射已抽到 npc_registry.py，这里 re-export 保持向后兼容
from .npc_registry import (
    NAME_TO_ID,
    ID_TO_NAME,
    get_speaker_id,
    get_npc_name_by_id,
    resolve_npc_display_name,
)

# QuestData / DialogData 已抽到 quest_data.py，re-export 兼容
from .quest_data import QuestData, DialogData

# ======================== 向后兼容常量 ========================
# 这些常量保持原有值，供其他模块使用
TASK_TYPE_MAIN = TaskCategory.MAIN.value
TASK_TYPE_SURVIVAL = TaskCategory.SURVIVAL.value
TASK_TYPE_INTEL = TaskCategory.INTEL.value
TASK_TYPE_FACTION = TaskCategory.FACTION.value

# 任务优先级（转换为字符串键）
TASK_PRIORITY = {k.value: v for k, v in _TASK_PRIORITY.items()}

# 任务样式（转换为字符串键）
TASK_TYPE_STYLES = {k.value: v for k, v in _TASK_TYPE_STYLES.items()}


# ======================== TaskDisplayData ========================
# 注意：TaskDisplayData 已移至 src/task/display.py
# 这里保留导入（上面已导入），不需要再定义


class QuestManager:
    # ═══════════════════════════════════════════════════════════════
    # 单例模式支持
    # ═══════════════════════════════════════════════════════════════
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """获取全局唯一的QuestManager实例"""
        return cls._instance
    
    @classmethod
    def set_instance(cls, instance):
        """设置全局实例（在main.py中调用）"""
        cls._instance = instance
    
    def __init__(self):
        self.quests = {}
        self.dialogs = {} # {quest_id: [DialogData]}
        
        self._active_quest_id = "Q_PROLOGUE" # 初始任务（内部变量）
        self._quest_status = QS_AVAILABLE    # 当前主线任务的状态（内部变量）
        self.finished_quests = set()        # 已完成的任务ID集合
        
        # 调试：打印初始任务状态
        print(f"[Quest] [初] 初始化: 任务={self._active_quest_id}, 状态={self._quest_status}")
        
        # 自动设置单例实例
        QuestManager._instance = self
        
        self.flags = {
            "refugee_unlocked": False,
            "guidance_visible": False,
            "intro_played": False,
            "intro_played_dialog":False
        }
        
        # ======================== Action Handlers ========================
        # 从 actions/ 子模块加载所有handler
        from .actions import ALL_HANDLERS
        self.action_handlers = dict(ALL_HANDLERS)
        # 保留过于简单的 lambda（不值得单独建文件）
        self.action_handlers['UNLOCK_GUIDANCE'] = lambda qm, ctx=None: qm.set_flag('guidance_visible', True)
        self.action_handlers['SHOW_UI_ONLY'] = lambda qm, ctx=None: qm.set_flag('guidance_visible', True)
        self.action_handlers['START_RAID'] = lambda qm, ctx=None: print(">> 触发山贼袭击逻辑 (需对接EventManager) <<")
        
        # 【新增】存储 ctx 引用，供 action handler 使用
        self._ctx_ref = None
        
        # 【新增】恶霸悬赏相关
        self.bully_bounty_id = None  # 记录恶霸发出的悬赏ID
        self.bully_npc_id = None     # 记录恶霸NPC的ID
        
        # 【新增】待处理的选择对话框显示请求
        self.pending_choice_dialog = False
        self._choice_context = None  # 存储选择时需要的上下文

        self._load_data()

        # UI 展示数据生成器（详情面板/侧边栏/任务日志）
        from .quest_presenter import QuestPresenter
        self._presenter = QuestPresenter(self)

        # 对话流转引擎（接取对话/REMIND/交付/记忆注入/调试跳过）
        from .dialog_runner import DialogRunner
        self._dialog = DialogRunner(self)

        # Action 指令分发器（CSV action 字段 -> handler）
        from .action_dispatcher import ActionDispatcher
        self._action = ActionDispatcher(self)
    
    # ═══════════════════════════════════════════════════════════════
    # 属性访问器：追踪任务状态变化，打印调试信息
    # ═══════════════════════════════════════════════════════════════
    @property
    def active_quest_id(self):
        return self._active_quest_id
    
    @active_quest_id.setter
    def active_quest_id(self, value):
        old_value = getattr(self, '_active_quest_id', None)
        self._active_quest_id = value
        if old_value != value:
            quest_title = self.quests.get(value, None)
            title_str = f"({quest_title.title})" if quest_title else ""
            print(f"[Quest] [任] 任务变更: {old_value} -> {value} {title_str}")
    
    @property
    def quest_status(self):
        return self._quest_status
    
    @quest_status.setter
    def quest_status(self, value):
        old_value = getattr(self, '_quest_status', None)
        self._quest_status = value
        if old_value != value:
            print(f"[Quest] 状态变更: {old_value} -> {value} (当前任务: {self._active_quest_id})")
    
    def get_active_quest(self):
        """
        获取当前活跃任务的数据对象
        
        Returns:
            QuestData or None: 当前活跃任务，如果没有则返回None
        """
        if not self._active_quest_id:
            return None
        return self.quests.get(self._active_quest_id)
    
    def get_quest_giver_info(self, quest_id: str = None) -> tuple:
        """
        获取任务发布者信息
        
        Args:
            quest_id: 任务ID，默认为当前活跃任务
            
        Returns:
            (giver_name, giver_id) - 任务发布者的名称和ID
        """
        quest_id = quest_id or self._active_quest_id
        quest = self.quests.get(quest_id)
        if not quest:
            return (None, None)
        
        # 从任务的 submit_npc 或 target 中获取发布者信息
        # 注意：submit_npc 是提交任务的NPC，通常也是发布者
        submit_npc = getattr(quest, 'submit_npc', None)
        
        if submit_npc and submit_npc != '9000':
            # 尝试解析为名称
            giver_name = get_npc_name_by_id(submit_npc)
            return (giver_name, submit_npc)
        
        return (None, None)

    def _load_data(self):
        # 1. Load Quests
        try:
            path = resource_path('data/quest_config.csv')
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    q = QuestData(row)
                    self.quests[q.id] = q
        except Exception as e:
            print(f"[Quest] Load Quest Error: {e}")

        # 2. Load Dialogs
        try:
            path = resource_path('data/dialog_config.csv')
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    d = DialogData(row)
                    if d.quest_id not in self.dialogs:
                        self.dialogs[d.quest_id] = []
                    self.dialogs[d.quest_id].append(d)
        except Exception as e:
            print(f"[Quest] Load Dialog Error: {e}")

    def set_flag(self, key, val):
        self.flags[key] = val

    def get_flag(self, key, default=None):
        return self.flags.get(key, default)

    def _match_submit_npc(self, npc_id, npc_name, submit_npc_field):
        """检查 NPC 是否匹配当前任务的 submit_npc。
        QuestData 已把 submit_npc 标准化为 submit_npc_id (int)，运行时只比较 ID。
        npc_name / submit_npc_field 仅为兼容旧调用签名，未使用。
        """
        quest = self.get_current_quest()
        if not quest or quest.submit_npc_id is None:
            return True  # 无指定 NPC
        if npc_id is None:
            return False
        try:
            return int(npc_id) == quest.submit_npc_id
        except (TypeError, ValueError):
            return False

    # --- 核心状态查询接口 ---

    def is_quest_started(self, quest_id):
        return self.active_quest_id == quest_id

    def is_quest_finished(self, quest_id):
        return quest_id in self.finished_quests

    def get_current_quest(self):
        return self.quests.get(self.active_quest_id)

    def get_dialog_for_current_quest(self):
        """获取当前任务对应的对话列表（如果有）"""
        return self.dialogs.get(self.active_quest_id, [])
    def get_dialog(self, key):
        """获取指定key的对话，如果没找到返回空列表"""
        return self.dialogs.get(key, [])

    # --- 逻辑更新 ---
    @property
    def is_ready_to_turn_in(self):
        return self.quest_status == "READY"

    @is_ready_to_turn_in.setter
    def is_ready_to_turn_in(self, val):
        if val: self.quest_status = "READY"

    def check_progress(self, player, all_cards, ctx=None):
        """检查当前任务是否完成。

        目标判定按 quest.type 派发到 goal_checkers 注册表。
        本方法只负责后续状态机推进 / NPC 弹开 / 自动激活下一段对话。
        """
        if self.quest_status != QS_ACTIVE:
            return False
        q = self.get_current_quest()
        if not q:
            return False
        # DIALOG / INTERACT 由对话流转完成，无被动判定
        if q.type in ('DIALOG', 'INTERACT'):
            return False

        from .goal_checkers import is_goal_met
        completed = is_goal_met(q, player, all_cards, self, ctx)

        if completed:
            if q.type == 'GATHER':
                for card in all_cards:
                    # 只针对正在工作的NPC
                    if isinstance(card, NPC) and card.is_working and getattr(card, 'recipe_proxy', None):
                        # 获取当前配方的产出物字符串 (例如 "ITEM:木材:1")
                        output_str = card.recipe_proxy.data.get('output', '')
                        # 如果配方产出包含任务目标 (例如目标是"木材")
                        if q.target in output_str:
                            # 1. 停止工作并弹开
                            if card.stack_parent:
                                card.bounce_off(card.stack_parent)

                            # 2. 修改AI状态描述作为"说话" (显示在人物下方或面板上)
                            card.ai_reason = f"采集够了{q.target}，可以回去交任务了"

                            # 3. 如果需要，可以重置计时器防止瞬间再次吸附
                            card.state = "IDLE"

            # 【通用】submit_npc='9999' 的任务自动推进（WAIT_TIME/EAT/REACH等）
            if q.submit_npc == '9999':
                self.quest_status = QS_READY
                print(f"[Quest] '{q.title}' 完成，自动推进...")

                old_id = q.id
                self.advance_quest()
                next_q = self.get_current_quest()

                # 拼接过场对话：本段 _END（收尾内心独白）+ 下段开场叙述
                # 之前只在"下段是 DIALOG"时才播 next 对话，导致非对话型主线
                # （HAVE_UNIT/RESOURCE_TOTAL 等）的开场和上段的收尾全被吞掉。
                combined = []
                end_dialogs = self.get_dialog(f"{old_id}_END")
                if end_dialogs:
                    combined.extend(end_dialogs)
                if next_q:
                    start_dialogs = self.get_dialog(next_q.id)
                    if start_dialogs:
                        combined.extend(start_dialogs)

                # 下段如果是 DIALOG 任务，先置 ACTIVE，让对话结束时 on_dialog_finished 能推进
                if next_q and next_q.type == 'DIALOG':
                    self.quest_status = QS_ACTIVE
                    print(f"[Quest] 自动触发DIALOG任务: {next_q.id}")

                if combined and ctx:
                    print(f"[Quest] 播放过场对话: {old_id}_END({len(end_dialogs) if end_dialogs else 0}行) "
                          f"+ {next_q.id if next_q else '-'}({len(start_dialogs) if (next_q and start_dialogs) else 0}行)")
                    ctx.story_ui.start_dialog(combined)
                return True

            self.quest_status = QS_READY
            submit_name = self._get_npc_name_by_id(q.submit_npc)
            print(f"[Quest] '{q.title}' 目标达成 -> READY (去找{submit_name}交付)")
            return True

        return False

    def advance_quest(self, manual_next_id=None):
        """推进任务"""
        current = self.get_current_quest()
        if current:
            self.finished_quests.add(current.id)
            print(f"[Quest] Finished: {current.title}")
            
            # 决定下一个任务
            next_id = manual_next_id if manual_next_id else current.next_id
            
            if next_id and next_id in self.quests:
                self.active_quest_id = next_id
                next_quest = self.quests[next_id]
                
                # 【修复】以下类型任务自动激活，不需要找NPC接取:
                # 1. GOAL 类型任务
                # 2. submit_npc == '9999' 的自动完成任务
                # 3. RESOURCE_TOTAL 类型（收集金钱等）
                # 自动激活规则（不需要找 NPC 接取）：
                # 1. 任务类型在 quest_types/ 里声明了 auto_activate = True
                # 2. submit_npc == '9999'（玩家自己执行）
                from . import quest_types
                auto_activate = (
                    quest_types.is_auto_activate(next_quest.type) or
                    next_quest.submit_npc == '9999'
                )
                
                if auto_activate:
                    self.quest_status = QS_ACTIVE
                    print(f"[Quest] 任务自动激活: {next_quest.title} (类型:{next_quest.type}, NPC:{next_quest.submit_npc})")
                else:
                    self.quest_status = "AVAILABLE"
            else:
                self.active_quest_id = "Q_FREE_PLAY"
                self.quest_status = "ACTIVE"

    def _is_cinematic_action(self, action_str):
        """委托给 action_dispatcher.is_cinematic_action"""
        from .action_dispatcher import is_cinematic_action
        return is_cinematic_action(action_str)

    def trigger_action(self, action_name, ctx=None):
        """委托给 ActionDispatcher（详细逻辑在 action_dispatcher.py）"""
        return self._action.trigger(action_name, ctx)
    def on_dialog_finished(self, npc_id=None, ctx=None, npc_name=None):
        """委托给 DialogRunner（详细逻辑在 dialog_runner.py）"""
        return self._dialog.on_dialog_finished(npc_id, ctx, npc_name)

    def try_trigger_npc_interaction(self, target_npc, story_ui):
        """委托给 DialogRunner"""
        return self._dialog.try_trigger_npc_interaction(target_npc, story_ui)

    def accept_quest(self):
        """从 AVAILABLE -> ACTIVE"""
        if self.quest_status == QS_AVAILABLE:
            self.quest_status = QS_ACTIVE
            print(f"[Quest] 任务接取: {self.active_quest_id}")
    
    # ═══════════════════════════════════════════════════════════════
    # 交付物品（业务在 quest_types/deliver.py）
    # ═══════════════════════════════════════════════════════════════

    def on_item_delivered(self, item_type, item_count, target_npc, player, ft_manager=None):
        """委托给 DeliverType.on_delivered"""
        from . import quest_types
        return quest_types.get('DELIVER').on_delivered(
            self, item_type, item_count, target_npc, player, ft_manager
        )

    def get_delivery_progress(self, quest_id=None):
        """委托给 DeliverType.get_progress"""
        from . import quest_types
        return quest_types.get('DELIVER').get_progress(self, quest_id)
    
    # ═══════════════════════════════════════════════════════════════
    # 【新增】选择分支任务支持（业务在 quest_types/choice.py）
    # ═══════════════════════════════════════════════════════════════

    def make_choice(self, choice_key, player=None, faction_war_system=None,
                    ft_manager=None, all_cards=None):
        """委托给 ChoiceType.apply_choice"""
        from . import quest_types
        return quest_types.get('CHOICE').apply_choice(
            self, choice_key, player, faction_war_system, ft_manager, all_cards
        )

    def try_start_quest_dialog(self, story_ui, all_cards=None):
        """委托给 ChoiceType.play_branch_dialog（玩家选完分支后播对应对话）"""
        from . import quest_types
        return quest_types.get('CHOICE').play_branch_dialog(self, story_ui)

    def get_choice_options(self):
        """委托给 ChoiceType.get_options"""
        from . import quest_types
        q = self.get_current_quest()
        return quest_types.get('CHOICE').get_options(q)
    def check_action_allowed(self, dragged_card, target_card, recipe_mgr=None):
        q = self.get_current_quest()
        if not q: return True, ""

        # 1. 自由模式不限制
        if q.id == 'Q_FREE_PLAY': return True, ""

        # 2. 序章纯剧情禁止操作
        if q.id == 'Q_PROLOGUE': return False, "剧情中..."

        if self.quest_status != QS_ACTIVE:
            return True, ""

        # 3. 委托给任务类型插件（quest_types/<类型>.py 的 can_act 方法）
        from . import quest_types
        return quest_types.get(q.type).can_act(q, dragged_card, target_card, recipe_mgr)

    # --- UI 显示接口 ---
    def get_dialog_by_key(self, key, replacements=None):
        """委托给 DialogRunner（支持 {占位符} 文本替换）"""
        return self._dialog.get_dialog_by_key(key, replacements)

    def get_quest_log_data(self):
        """委托给 QuestPresenter"""
        return self._presenter.get_quest_log_data()

    def _get_npc_name_by_id(self, npc_id_or_name):
        """兼容老调用，转发到 npc_registry.resolve_npc_display_name"""
        return resolve_npc_display_name(npc_id_or_name)

    def _derive_objective(self, q):
        """委托给 QuestPresenter"""
        return self._presenter.derive_objective(q)

    def get_current_objective_text(self, player=None, all_cards=[]):
        """委托给 QuestPresenter"""
        return self._presenter.get_current_objective_text(player, all_cards)

    def get_all_task_displays(self, player=None, all_cards=[]) -> list:
        """委托给 QuestPresenter"""
        return self._presenter.get_all_task_displays(player, all_cards)
    
    def get_quest_title(self):
        q = self.get_current_quest()
        return q.title if q else ""
    def check_and_play_intro(self, all_cards, story_ui):
        """委托给 DialogRunner（开场剧情自动播放）"""
        return self._dialog.check_and_play_intro(all_cards, story_ui)

    # ==================== 调试功能：快速完成任务 ====================
    # CINEMATIC_ACTIONS 已搬到 action_dispatcher.py

    def skip_current_dialogs(self, ctx, _recursion_depth=0):
        """委托给 DialogRunner（详细逻辑在 dialog_runner.py 的 _skip_active_dialog_queue 等）"""
        return self._dialog.skip_current_dialogs(ctx, _recursion_depth)