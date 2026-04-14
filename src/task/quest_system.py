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
from src.entities import Player, NPC, Building, Resource
from src.utils import resource_path

# 导入角色种子数据，用于动态构建 ID 映射
from src.data.character_seeds import SEEDS

# ======================== 从同目录模块导入 ========================
from .display import TaskDisplayData
from .base import (
    TaskCategory,
    TASK_PRIORITY as _TASK_PRIORITY,
    TASK_TYPE_STYLES as _TASK_TYPE_STYLES,
)

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


# ======================== NPC ID 映射系统 ========================
# 从 SEEDS 动态构建，避免手动维护两份数据导致不一致
# ID 规则：普通NPC = 8000 + SEEDS索引，特殊ID见下方

# 动态构建：名字 → ID
NAME_TO_ID = {seed['name']: 8000 + idx for idx, seed in enumerate(SEEDS)}
# 添加特殊ID和别名
NAME_TO_ID.update({
    '村长': 9000,
    '我': 9999,
    '泼皮': NAME_TO_ID.get('泼皮牛二', 8026),      # 别名
    '泼皮甲': NAME_TO_ID.get('泼皮牛二', 8026),    # 兼容旧对话脚本
    '泼皮乙': NAME_TO_ID.get('泼皮狗蛋', 8027),    # 兼容旧对话脚本
})

# 动态构建：ID → 名字（反向映射，排除别名避免覆盖）
ID_TO_NAME = {str(8000 + idx): seed['name'] for idx, seed in enumerate(SEEDS)}
ID_TO_NAME.update({
    '9000': '村长',
    '9999': '玩家',
})

def get_speaker_id(name: str) -> int:
    """根据说话者名字获取 NPC ID（从 SEEDS 动态查询）"""
    return NAME_TO_ID.get(name, None)

def get_npc_name_by_id(npc_id) -> str:
    """根据 NPC ID 获取名字，用于 UI 显示"""
    # 特殊值处理
    if str(npc_id) == '9999':
        return '（自动完成）'
    if str(npc_id) == '9000':
        return '未指定'
    return ID_TO_NAME.get(str(npc_id), f'NPC({npc_id})')


# ======================== TaskDisplayData ========================
# 注意：TaskDisplayData 已移至 src/task/display.py
# 这里保留导入（上面已导入），不需要再定义


class QuestData:
    def __init__(self, row):
        self.id = row['id']
        self.title = row['title']
        self.type = row['type']
        self.target = row['target']
        self.count = int(row['count'])
        self.next_id = row['next']
        self.desc = row['desc']
        self.submit_npc = row.get('submit_npc', '9000')
        self.scenario = row.get('scenario', '')
        
        # 【新增】分支任务支持
        # CHOICE类型任务可以有多个后续分支
        # 格式: "next_good|next_evil" 或 "BRANCH_A:条件A|BRANCH_B:条件B"
        self.branches = {}  # {choice_key: next_quest_id}
        if self.type == 'CHOICE' and '|' in self.next_id:
            parts = self.next_id.split('|')
            for i, part in enumerate(parts):
                if ':' in part:
                    key, val = part.split(':', 1)
                    self.branches[key] = val
                else:
                    # 默认: 第一个是正义路线，第二个是邪恶路线
                    if i == 0:
                        self.branches['GOOD'] = part
                    else:
                        self.branches['EVIL'] = part
class DialogData:
    def __init__(self, row):
        self.quest_id = row['quest_id']
        self.speaker = row['speaker']
        # 处理CSV中的转义换行符：将 \n 文本转换为真正的换行
        raw_text = row['text']
        self.text = raw_text.replace('\\n', '\n') if raw_text else ''
        self.bg_img = row['bg_img']
        self.action = row['action']
        self.speaker_id = self._resolve_speaker_id(self.speaker)

    def _resolve_speaker_id(self, name):
        """根据对话中的说话者名字，解析对应的 NPC ID"""
        # 使用模块级的动态映射函数（从 SEEDS 自动构建）
        return get_speaker_id(name)

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
        """检查 NPC 是否与任务的 submit_npc 字段匹配
        
        支持两种格式：
        1. NPC ID（如 '8002', '9000'）
        2. NPC 名称（如 '鱼西施', '村长'）
        
        Returns:
            bool: 是否匹配
        """
        if not submit_npc_field:
            return True  # 无指定 NPC，任何人都可以
        
        # 方式1：直接按 ID 匹配
        if npc_id is not None and str(npc_id) == submit_npc_field:
            return True
        
        # 方式2：按名称匹配（submit_npc 字段是名称而非 ID）
        if npc_name and npc_name == submit_npc_field:
            return True
        
        # 方式3：submit_npc 是名称，通过 NAME_TO_ID 转换后匹配
        expected_id = NAME_TO_ID.get(submit_npc_field)
        if expected_id is not None and npc_id is not None and npc_id == expected_id:
            return True
        
        # 方式4：submit_npc 是 ID，通过 ID_TO_NAME 转换后匹配
        expected_name = ID_TO_NAME.get(submit_npc_field)
        if expected_name is not None and npc_name and npc_name == expected_name:
            return True
        
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
        """检查当前任务是否完成"""
        if self.quest_status != QS_ACTIVE:
            return False
        q = self.get_current_quest()
        if not q: return False
        if q.type in ['DIALOG', 'INTERACT']: 
            return False
        
        completed = False
        
        # 1. 采集类
        if q.type == 'GATHER':
            # 检查玩家或任意随从背包
            count = player.inventory.get(q.target, 0)
            for c in all_cards:
                if getattr(c, 'is_follower', False):
                    count += c.inventory.get(q.target, 0)
            if count >= q.count: completed = True
        
        elif q.type == 'HAVE_UNIT':
            count = 0
            for c in all_cards:
                # 检查 NPC 职业
                if isinstance(c, NPC) and getattr(c, 'job', '') == q.target:
                    count += 1
                # 检查 建筑 类型
                elif isinstance(c, Building) and getattr(c, 'building_type', '') == q.target:
                    count += 1
                elif isinstance(c, Resource) and c.item_type == q.target:
                    count += c.count
            if count >= q.count: completed = True
        elif q.type == 'RESOURCE_TOTAL':
            current_val = 0
            if q.target == 'MONEY': current_val = player.money
            elif q.target == 'FAME': current_val = player.fame
            if current_val >= q.count: completed = True
        # 2. 生存天数类
        elif q.type == 'SURVIVE':
            if q.target == 'DAY' and player.day >= q.count:
                completed = True
        
        # 3. 目标完成类 (GOAL) - 用于特殊目标如"取消悬赏"
        elif q.type == 'GOAL':
            if q.target == 'CANCEL_BOUNTY':
                # 检查恶霸悬赏是否已取消
                if not self.flags.get('bully_bounty_active', True):
                    completed = True
            elif q.target == 'DEFEAT_BULLY':
                # 检查恶霸是否被击败
                if self.flags.get('bully_defeated', False):
                    completed = True
            elif q.target == 'HUNGER':
                # 检查玩家饥饿值是否低于目标值（即已吃东西）
                current_hunger = getattr(player, 'hunger', 100)
                if current_hunger <= q.count:
                    completed = True
        
        # 4. 招募类任务 (RECRUIT) - 检查是否已招募指定NPC
        elif q.type == 'RECRUIT':
            recruit_target = q.target  # NPC名字
            recruited = self.flags.get(f'recruited_{recruit_target}', False)
            if recruited:
                completed = True
            else:
                # 也检查 followers 列表
                followers = getattr(player, 'followers', [])
                for f in followers:
                    if getattr(f, 'name', '') == recruit_target:
                        completed = True
                        self.set_flag(f'recruited_{recruit_target}', True)
                        break
        
        # 5. 战斗类任务 (COMBAT) - 检查是否击败指定目标
        elif q.type == 'COMBAT':
            combat_target = q.target  # NPC名字
            if self.flags.get(f'defeated_{combat_target}', False):
                completed = True
        
        # 6. 进食/恢复类任务 (EAT) - 只看结果：饥饿值是否低于目标
        elif q.type == 'EAT':
            # target 是目标饥饿阈值，饥饿值低于此值即完成
            # 例如 target=50 表示"饥饿值降到50以下"
            target_hunger = int(q.count) if q.count else 50
            current_hunger = getattr(player, 'hunger', 100)
            if current_hunger < target_hunger:
                completed = True
        
        # 7. 交付类任务 (DELIVER) - 通过将物品堆叠到NPC身上来完成
        # 进度由 on_item_delivered 方法更新
        elif q.type == 'DELIVER':
            # 检查交付进度计数器
            deliver_count = self.flags.get(f'deliver_{q.id}', 0)
            if deliver_count >= q.count:
                completed = True
        
        # 8. 【新增】到达区域类任务 (REACH) - 玩家到达指定区域即完成
        elif q.type == 'REACH':
            # target 格式: "x,y,radius" 如 "2800,2000,150" 或区域名 "AMBUSH_POINT"
            if self._check_player_reach_target(player, q.target, q.count):
                completed = True
    
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
            
            # 【特殊处理】REACH类型任务且submit_npc='9999'时，自动推进并触发下个任务对话
            if q.type == 'REACH' and q.submit_npc == '9999':
                self.quest_status = QS_READY
                print(f"[Quest] REACH任务 '{q.title}' 完成，自动推进...")
                self.advance_quest()
                
                # 获取下一个任务，如果是DIALOG类型则立即触发对话
                next_q = self.get_current_quest()
                if next_q and next_q.type == 'DIALOG':
                    self.quest_status = QS_ACTIVE
                    print(f"[Quest] 自动触发DIALOG任务: {next_q.id}")
                    dialogs = self.get_dialog(next_q.id)
                    if dialogs and ctx:
                        ctx.story_ui.start_dialog(dialogs)
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
                auto_activate = (
                    next_quest.type in ('GOAL', 'RESOURCE_TOTAL', 'FREE') or
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
        """
        检查是否是演出型 action（需要让玩家观看，不能跳过）
        """
        if not action_str:
            return False
        # 提取基础动作名（去掉参数）
        base_action = action_str.split(':')[0]
        return base_action in self.CINEMATIC_ACTIONS
    
    def trigger_action(self, action_name, ctx=None):
        """由 StoryUI 在对话结束或点击时调用
        
        支持三种来源的action:
        1. 本地action_handlers中注册的处理器
        2. StoryDirective统一指令（新增）
        3. 多条指令用分号分隔，逐条执行
        """
        # 只有真正有动作时才处理
        if not action_name:
            return
        
        # 【新增】支持分号分隔的多条指令
        # 例如: "SHAKE_CAMERA:5;SET_AFFINITY:鱼西施:+30;PLAYER_FAME:+10"
        directives = action_name.split(';')
        
        for directive in directives:
            directive = directive.strip()
            if not directive:
                continue
            self._execute_single_action(directive, ctx)
    
    def _execute_single_action(self, action_str, ctx=None):
        """执行单条action指令"""
        # 解析带参数的动作格式: ACTION_NAME:PARAM 或 ACTION_NAME:PARAM1:PARAM2
        action_parts = action_str.split(':')
        base_action = action_parts[0].upper()  # 统一大写
        action_params = action_parts[1:] if len(action_parts) > 1 else []
        
        print(f"[Quest] ▶▶▶ 执行动作: {base_action}" + (f" 参数: {action_params}" if action_params else ""))
        
        # 1. 优先使用本地action_handlers
        #    所有handler签名统一为 (quest_mgr, ctx, *params)
        if base_action in self.action_handlers:
            handler = self.action_handlers[base_action]
            try:
                if action_params:
                    handler(self, ctx, *action_params)
                else:
                    handler(self, ctx)
            except TypeError:
                try:
                    handler(self)
                except TypeError:
                    handler()
            return
        
        # 2. 尝试使用StoryDirectiveExecutor处理
        try:
            from src.story.story_directive_executor import get_directive_executor
            executor = get_directive_executor()
            if ctx:
                executor.bind_context(ctx)
            if executor.execute(action_str):
                return  # 执行成功
        except Exception as e:
            print(f"[Quest] StoryDirective执行失败: {e}")
        
        # 3. 都没能处理
        print(f"[Quest] [!] 未知动作: {base_action}")
       

       
    def on_dialog_finished(self, npc_id=None, ctx=None, npc_name=None):
        """
        [新增] 当整段对话完全结束时调用，处理任务状态流转
        
        Args:
            npc_id: NPC 的数字 ID
            ctx: 游戏上下文
            npc_name: NPC 名称（可选，用于支持按名称匹配 submit_npc）
        """
        q = self.get_current_quest()
        print(f"[Quest] 对话序列结束 | 当前任务:{self.active_quest_id} | 状态:{self.quest_status} | 类型:{q.type if q else '?'}")
        
        # ════════════════════════════════════════════════════════════════
        # 【核心修复】将剧情对话注入参与NPC的记忆系统
        # ════════════════════════════════════════════════════════════════
        self._inject_dialog_memory_to_npcs(ctx, q)
        
        # 1. 接取任务：从 AVAILABLE -> ACTIVE
        if self.quest_status == QS_AVAILABLE:
            q = self.get_current_quest()
            if q:
                # 如果是跟任务发布人对话完了，且之前没接，现在接取
                # 支持两种格式：NPC ID（如 '8002'）或 NPC 名称（如 '鱼西施'）
                npc_matched = self._match_submit_npc(npc_id, npc_name, q.submit_npc)
                if npc_id is None or npc_matched:
                    self.accept_quest()
# =============================================================================
#                     if q.type == 'DIALOG':
#                          print(f"[Quest] 纯对话任务 {q.id} 自动完成")
#                          self.advance_quest() # 直接完成并跳到下一个
# =============================================================================
                    return

        # 2. 完成任务：从 ACTIVE -> READY (仅限纯对话任务)
        if self.quest_status == QS_ACTIVE:
            q = self.get_current_quest()
            if q and q.type in ['DIALOG', 'INTERACT']:
                # 如果是跟目标对话完了
                target_check = (q.type == 'DIALOG') or (q.type == 'INTERACT' and str(npc_id) == q.target)
                if target_check:
                    self.quest_status = QS_READY
                    print(f"[Quest] 对话类任务 {q.id} 目标达成 -> READY")
                    
                    # 【修复】DIALOG类型任务完成后，自动推进到下一个任务
                    if q.type == 'DIALOG' and q.next_id and q.next_id in self.quests:
                        print(f"[Quest] DIALOG任务自动推进: {q.id} -> {q.next_id}")
                        self.advance_quest()
                        
                        next_q = self.get_current_quest()
                        if next_q:
                            # 如果下一个也是DIALOG任务，立即开始播放
                            if next_q.type == 'DIALOG':
                                self.quest_status = QS_ACTIVE
                                print(f"[Quest] 任务接取: {next_q.id}")
                                # 获取对话并通过story_ui播放
                                dialogs = self.get_dialog(next_q.id)
                                if dialogs and ctx:
                                    ctx.story_ui.start_dialog(dialogs)
                            # 【新增】如果下一个任务的 submit_npc 与当前任务相同，自动接取
                            elif next_q.submit_npc == q.submit_npc and self.quest_status == QS_AVAILABLE:
                                self.quest_status = QS_ACTIVE
                                print(f"[Quest] 连续任务自动接取: {next_q.id} (同一NPC: {q.submit_npc})")
                                # 播放接取对话
                                dialogs = self.get_dialog(next_q.id)
                                if dialogs and ctx:
                                    ctx.story_ui.start_dialog(dialogs)
                    return
        
        
        
    # --- 交互限制接口 (InteractionManager 调用) ---
    def try_trigger_npc_interaction(self, target_npc, story_ui):
        q = self.get_current_quest()
        if not q: return False
        if not hasattr(target_npc, 'id'): 
            return False
        
        # 【修复】点击玩家自己时不触发任务交互，直接返回False让详情页打开
        if getattr(target_npc, 'job', None) == 'PLAYER':
            return False
        
        npc_id_str = str(target_npc.id)
        npc_name = getattr(target_npc, 'name', None)  # 获取 NPC 名称
        
        # 1. 接取任务 (AVAILABLE) -> 读取 "Q_ID"
        if self.quest_status == QS_AVAILABLE:
            if self._match_submit_npc(target_npc.id, npc_name, q.submit_npc):
                # 尝试读取接任务对话
                dialogs = self.get_dialog(q.id)
                
                if dialogs:
                    story_ui.start_dialog(dialogs)                
                self.accept_quest()
                return True
            return False

        # 2. 进行中 (ACTIVE)
        if self.quest_status == QS_ACTIVE:
            # A. 交互类任务 (INTERACT) -> 读取 "Q_ID" (保持原样，通常交互任务没有接取阶段直接开始)
            if q.type == 'INTERACT' and npc_id_str == q.target:
                dialogs = self.get_dialog(q.id)
                if dialogs:
                    story_ui.start_dialog(dialogs) 
                else:
                    self.quest_status = QS_READY 
                return True
            
            # B. 找发布人提示 (REMIND) -> 读取 "Q_ID_REMIND"
            if self._match_submit_npc(target_npc.id, npc_name, q.submit_npc):
                # 【新增】检查是否是声望检查任务，如果是，根据声望标记选择对话
                if 'FAME_CHECK' in q.id:
                    # 检查声望是否不足
                    if self.get_flag('fame_insufficient', False):
                        # 声望不足，显示 REMIND 对话
                        remind_dialogs = self.get_dialog(q.id + "_REMIND")
                        if remind_dialogs:
                            story_ui.start_dialog(remind_dialogs)
                        else:
                            # 兜底：如果没有配置提示，显示通用文本
                            remind_text = f"请尽快完成【{q.title}】，我们需要{q.target}。"
                            dummy_dialog = type('DialogData', (object,), {
                                'quest_id': 'SYS', 'speaker': target_npc.name, 
                                'text': remind_text, 
                                'bg_img': '', 'action': '', 'speaker_id': target_npc.id
                            })
                            story_ui.start_dialog([dummy_dialog])
                    else:
                        # 声望足够，显示正常对话并推进任务
                        dialogs = self.get_dialog(q.id)
                        if dialogs:
                            story_ui.start_dialog(dialogs)
                        else:
                            # 如果没有对话，直接推进任务
                            self.advance_quest()
                    return True
                
                # 【原有逻辑】普通任务的 REMIND 对话
                remind_dialogs = self.get_dialog(q.id + "_REMIND")
                if remind_dialogs:
                    story_ui.start_dialog(remind_dialogs)
                else:
                    # 兜底：如果没有配置提示，显示通用文本
                    remind_text = f"请尽快完成【{q.title}】，我们需要{q.target}。"
                    dummy_dialog = type('DialogData', (object,), {
                        'quest_id': 'SYS', 'speaker': target_npc.name, 
                        'text': remind_text, 
                        'bg_img': '', 'action': '', 'speaker_id': target_npc.id
                    })
                    story_ui.start_dialog([dummy_dialog])
                return True
            return False 
       
        # 3. 交付任务 (READY) -> 读取 "Q_ID_END"
        if self.quest_status == QS_READY:
            if self._match_submit_npc(target_npc.id, npc_name, q.submit_npc):
                # 尝试获取完成对话
                finish_dialogs = self.get_dialog(q.id + "_END")
                
                # 核心逻辑：先推进任务数据，再播放对话
                self.advance_quest()
                
                if finish_dialogs:
                    story_ui.start_dialog(finish_dialogs)
                else:
                    if q.type == 'DIALOG':
                        return True
                    # 兜底完成对话
                    story_ui.start_dialog([
                        type('DialogData', (object,), {
                            'quest_id': 'SYS', 'speaker': target_npc.name, 
                            'text': '做得好！这对村子帮助很大。', 
                            'bg_img': '', 'action': '', 'speaker_id': target_npc.id
                        })
                    ])
                return True
            return False

        return False
    
    def _inject_dialog_memory_to_npcs(self, ctx, quest):
        """
        【核心】将剧情对话内容注入参与NPC的记忆系统
        
        这是解决"NPC失忆"问题的关键：
        - StoryUI 播放的剧情对话之前不会进入 NPC 的 LLM 记忆
        - 现在在对话结束后，将对话摘要写入所有参与NPC的记忆
        
        Args:
            ctx: 游戏上下文（含 story_ui 和 all_cards）
            quest: 当前任务对象
        """
        if not ctx:
            return
        
        story_ui = getattr(ctx, 'story_ui', None)
        all_cards = getattr(ctx, 'all_cards', None)
        
        if not story_ui or not all_cards:
            print("[Quest] 无法注入对话记忆: 缺少 story_ui 或 all_cards")
            return
        
        # 获取对话摘要
        dialog_summary = story_ui.get_last_dialog_summary()
        if not dialog_summary:
            print("[Quest] 无对话数据可注入")
            return
        
        quest_id = dialog_summary['quest_id']
        speakers = dialog_summary['speakers']
        summary = dialog_summary['summary']
        
        # 获取任务标题（如果有的话）
        quest_title = quest.title if quest else "一段对话"
        
        # 构造记忆内容
        memory_content = f"【剧情】关于「{quest_title}」的对话：{summary}"
        
        print(f"[Quest] 注入对话记忆到 {len(speakers)} 个参与者: {memory_content[:80]}...")
        
        # 为每个参与的NPC添加记忆
        try:
            from src.llm.npc_memory import MemoryManager
            memory_mgr = MemoryManager.get_instance()
            
            injected_count = 0
            for card in all_cards:
                # 获取NPC ID
                card_id = getattr(card, 'id', None)
                if card_id is None:
                    npc_data = getattr(card, 'npc_data', None)
                    if npc_data:
                        card_id = getattr(npc_data, 'id', None)
                
                # 检查是否是玩家（跳过，玩家不需要LLM记忆）
                is_player = getattr(card, 'is_player', False)
                if is_player:
                    continue
                
                # 检查是否是对话参与者
                if card_id is not None and card_id in speakers:
                    card_name = getattr(card, 'name', f'NPC_{card_id}')
                    
                    # 获取或创建该NPC的记忆系统
                    memory_sys = memory_mgr.get_npc_memory(card_id, card_name)
                    
                    # 添加剧情记忆（高重要性）
                    memory_sys.add_event_memory(
                        event_desc=memory_content,
                        importance=4,  # 高重要性
                        involved_npcs=[]
                    )
                    injected_count += 1
                    print(f"[Quest] [ok] 已注入记忆到 {card_name} (ID={card_id})")
            
            print(f"[Quest] 对话记忆注入完成: {injected_count} 个NPC")
            
        except Exception as e:
            print(f"[Quest] 注入对话记忆失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 清理对话数据，避免重复注入
        story_ui.clear_dialog_data()
    
    def accept_quest(self):
        """从 AVAILABLE -> ACTIVE"""
        if self.quest_status == QS_AVAILABLE:
            self.quest_status = QS_ACTIVE
            print(f"[Quest] 任务接取: {self.active_quest_id}")
    
    # ═══════════════════════════════════════════════════════════════
    # 【新增】交付物品处理
    # ═══════════════════════════════════════════════════════════════
    
    def on_item_delivered(self, item_type, item_count, target_npc, player, ft_manager=None):
        """
        当玩家将物品堆叠到NPC身上时调用，检查是否完成交付任务
        
        Args:
            item_type: 物品类型（如 '生鱼'）
            item_count: 交付的物品数量
            target_npc: 目标NPC
            player: 玩家对象
            ft_manager: 浮动文字管理器
        
        Returns:
            bool: 是否是有效的任务交付（物品已被消耗）
        """
        q = self.get_current_quest()
        if not q or q.type != 'DELIVER':
            return False
        
        if self.quest_status != QS_ACTIVE:
            return False
        
        # 检查目标物品是否匹配
        if item_type != q.target:
            return False
        
        # 检查目标NPC是否匹配
        npc_name = getattr(target_npc, 'name', '')
        npc_id = getattr(target_npc, 'id', None)
        if not self._match_submit_npc(npc_id, npc_name, q.submit_npc):
            return False
        
        # 交付有效，更新进度
        current_count = self.flags.get(f'deliver_{q.id}', 0)
        new_count = min(current_count + item_count, q.count)
        self.flags[f'deliver_{q.id}'] = new_count
        
        remaining = q.count - new_count
        
        if ft_manager:
            if remaining > 0:
                ft_manager.add_text(f"交付 {item_type} ({new_count}/{q.count})", 
                                   target_npc.rect.centerx, target_npc.rect.top - 30, (255, 215, 0))
            else:
                ft_manager.add_text(f"交付完成！", 
                                   target_npc.rect.centerx, target_npc.rect.top - 30, (100, 255, 100))
        
        print(f"[Quest] 交付任务 {q.id}: {item_type} x{item_count} -> {npc_name} (进度: {new_count}/{q.count})")
        
        return True
    
    def get_delivery_progress(self, quest_id=None):
        """获取交付任务的当前进度"""
        if quest_id is None:
            q = self.get_current_quest()
            if not q or q.type != 'DELIVER':
                return 0, 0
            quest_id = q.id
        else:
            q = self.quests.get(quest_id)
        
        if not q:
            return 0, 0
        
        current = self.flags.get(f'deliver_{quest_id}', 0)
        return current, q.count
    
    # ═══════════════════════════════════════════════════════════════
    # 【新增】选择分支任务支持
    # ═══════════════════════════════════════════════════════════════
    
    def make_choice(self, choice_key, player=None, faction_war_system=None, ft_manager=None, all_cards=None):
        """
        玩家做出选择分支
        
        Args:
            choice_key: 选择键 ('GOOD', 'EVIL', 或自定义键)
            player: 玩家对象，用于更新属性
            faction_war_system: 势力战争系统，用于发布悬赏
            ft_manager: 浮动文字管理器
            all_cards: 所有卡牌列表，用于查找NPC并为其添加记忆
        
        Returns:
            (success: bool, next_quest_id: str, message: str)
        """
        q = self.get_current_quest()
        if not q or q.type != 'CHOICE':
            return False, None, "当前任务不是选择类型"
        
        if choice_key not in q.branches:
            return False, None, f"无效的选择: {choice_key}"
        
        next_quest_id = q.branches[choice_key]
        
        # 根据选择执行效果
        from .actions.yuxishi_event import get_choice_effects, apply_story_memories
        choice_effects = get_choice_effects(q.id, choice_key)

        # ═══════════════════════════════════════════════════════════════
        # 【核心：剧情记忆系统】为所有当事人添加记忆
        # 当发生重要剧情选择时，所有参与者都应该记住这件事
        # ═══════════════════════════════════════════════════════════════
        apply_story_memories(self, q.id, choice_key, player, all_cards, ft_manager)
        
        if player and choice_effects:
            # 声望变化
            fame_delta = choice_effects.get('fame', 0)
            if fame_delta != 0:
                player.fame = max(0, player.fame + fame_delta)
                if ft_manager:
                    color = (255, 215, 0) if fame_delta > 0 else (255, 80, 80)
                    ft_manager.add_text(f"声望 {fame_delta:+d}", 
                                       player.rect.centerx, player.rect.top - 30, color)
            
            # 道德值变化（如果有）
            morality_delta = choice_effects.get('morality', 0)
            if morality_delta != 0:
                player.morality = getattr(player, 'morality', 50) + morality_delta
                player.morality = max(0, min(100, player.morality))
            
            # 金钱变化
            money_delta = choice_effects.get('money', 0)
            if money_delta != 0:
                player.money = max(0, player.money + money_delta)
                if ft_manager:
                    color = (255, 215, 0) if money_delta > 0 else (255, 80, 80)
                    ft_manager.add_text(f"铜钱 {money_delta:+d}", 
                                       player.rect.centerx, player.rect.top - 50, color)
            
            # 悬赏效果
            bounty_data = choice_effects.get('bounty')
            if bounty_data and faction_war_system:
                faction_war_system.post_bounty(
                    issuer_org=bounty_data.get('issuer', 'YAMEN'),
                    target_id=player.id,
                    reward=bounty_data.get('reward', 50),
                    reason=bounty_data.get('reason', '作恶多端'),
                    is_player_target=True
                )
                if ft_manager:
                    ft_manager.add_text("[!] 被悬赏了！",
                                       player.rect.centerx, player.rect.top - 70, (255, 50, 50))
        
        # 设置分支标记（供后续剧情使用）
        self.set_flag(f"choice_{q.id}", choice_key)
        
        # 推进到对应分支
        self.advance_quest(manual_next_id=next_quest_id)
        
        effect_msg = choice_effects.get('message', '你做出了选择')
        print(f"[Quest] 选择分支: {choice_key} -> {next_quest_id}")
        
        return True, next_quest_id, effect_msg
    
    def try_start_quest_dialog(self, story_ui, all_cards=None):
        """
        尝试播放当前任务的对话
        在玩家做出选择后调用，播放对应分支的对话
        
        Args:
            story_ui: StoryUI 实例
            all_cards: 所有卡牌列表（用于查找NPC）
        
        Returns:
            bool: 是否成功开始对话
        """
        q = self.get_current_quest()
        if not q:
            return False
        
        # 获取任务对话
        dialogs = self.get_dialog(q.id)
        if dialogs:
            # 【关键修复】播放对话时将状态设为ACTIVE，确保on_dialog_finished能正确处理
            self.quest_status = QS_ACTIVE
            story_ui.start_dialog(dialogs)
            print(f"[Quest] 开始播放分支对话: {q.id} (状态已设为ACTIVE)")
            return True
        else:
            print(f"[Quest] 分支 {q.id} 没有配置对话")
            return False

    def get_choice_options(self):
        """
        获取当前选择任务的选项列表（供UI显示）
        Returns: [{'key': 'GOOD', 'text': '救人', 'hint': '+10声望'}, ...]
        """
        q = self.get_current_quest()
        if not q or q.type != 'CHOICE':
            return []
        
        options = []
        for choice_key in q.branches.keys():
            from .actions.yuxishi_event import get_choice_effects
            effects = get_choice_effects(q.id, choice_key)
            
            # 构建提示文本
            hints = []
            if effects.get('fame', 0) > 0:
                hints.append(f"+{effects['fame']}声望")
            elif effects.get('fame', 0) < 0:
                hints.append(f"{effects['fame']}声望")
            
            if effects.get('money', 0) > 0:
                hints.append(f"+{effects['money']}铜")
            
            if effects.get('bounty'):
                hints.append("[!] 被悬赏")
            
            # 选项文本（可以从对话配置读取，这里用默认值）
            option_texts = {
                'GOOD': '出手相救',
                'EVIL': '助纣为虐',
                'IGNORE': '袖手旁观',
            }
            
            options.append({
                'key': choice_key,
                'text': option_texts.get(choice_key, choice_key),
                'hint': ' | '.join(hints) if hints else ''
            })
        
        return options
            
   
    
    def check_action_allowed(self, dragged_card, target_card, recipe_mgr=None):
        q = self.get_current_quest()
        if not q: return True, ""
        
        # 1. 自由模式不限制
        if q.id == 'Q_FREE_PLAY': return True, ""
        
        # 2. 序章纯剧情禁止操作
        if q.id == 'Q_PROLOGUE': return False, "剧情中..."
        
        if self.quest_status != QS_ACTIVE:
            return True, ""

        # 3. 采集任务 (GATHER) 智能判断
        if q.type == 'GATHER':
            # --- A. 直接操作目标物品 (如整理背包、合并堆叠) ---
            # 检查被拖拽物是否是任务目标
            drag_type = getattr(dragged_card, 'item_type', '') 
            if drag_type == q.target: return True, ""
            
            # 检查目标物是否是任务目标 (如把人拖到木材上捡起)
            target_type = getattr(target_card, 'item_type', '')
            if target_type == q.target: return True, ""
            
            # 映射一下 CSV 里的中文 '浆果' -> 对应建筑类型 'BUSH' (为了兼容采集浆果的直观逻辑)
            # 这是一个特例，因为采集浆果不需要配方系统(如果是直接放置采集的话)
            if q.target == '浆果' and getattr(target_card, 'building_type', '') == 'BUSH':
                return True, ""

            # --- B. 配方预测 (核心修复) ---
            # 检查这两个卡牌互动，是否会产出任务目标
            if recipe_mgr:
                recipe = recipe_mgr.check_match(dragged_card, target_card)
                if recipe:
                    # 获取配方产出，例如 "ITEM:木材:1"
                    output_str = recipe.data['output']
                    # 如果产出字符串包含任务目标 (如 "木材")，则放行
                    if q.target in output_str:
                        return True, ""

            # --- C. 严格模式判断 (Configurable Restriction) ---
            # 如果上面都没通过，说明玩家在做与任务无关的事 (比如去砍树但任务是采浆果，或者去吃东西)
            
            # 我们可以定义哪些任务是 "严格教学" (不允许做别的)
            # 这里演示：前3个任务 (Q0, Q1, Q2, Q3) 强制引导，后续任务放开自由度
            # 你也可以在 Quest Config 的 desc 里写上 [STRICT] 标签来判断
            is_strict_tutorial = q.id in ['Q0_FIND_ELDER', 'Q1_FOOD', 'Q2_WOOD', 'Q3_CAMPFIRE']
            
            # 或者读取 CSV 中的 desc 字段是否有特殊标记 (这是你要求的配置化)
            if '[STRICT]' in q.desc: 
                is_strict_tutorial = True

            if is_strict_tutorial:
                return False, f"教学阶段，请专注于：{q.target}"
            
            # 如果不是严格模式，允许玩家做其他事 (高自由度)
            return True, ""

        # 4. 交互任务 (INTERACT)
        if q.type == 'INTERACT':
             target_id = str(getattr(target_card, 'id', ''))
             if target_id == q.target:
                 return True, ""
             # 允许在空地上拖拽(InteractionManager层级处理)，但禁止与无关NPC深度互动
             return False, "请先与目标人物交谈"

        return True, ""
    def start_quest(self, story_ui):
        """[新增] 正式开始当前任务（接取任务）"""
        self.quest_status = "ACTIVE"
        print(f"[Quest] Accepted: {self.get_current_quest().title}")
    # --- UI 显示接口 ---
    def get_dialog_by_key(self, key, replacements=None):
        """
        获取指定 Key 的对话列表，并支持文本替换。
        key: CSV中的 quest_id (如 INTRO_SOLO)
        replacements: 字典 { '{follower}': '张三' }
        """
        raw_dialogs = self.dialogs.get(key, [])
        if not replacements:
            return raw_dialogs
        
        # 动态创建副本并替换文本，防止修改原始数据
        processed = []
        for d in raw_dialogs:
            # 创建临时对象（简单的浅拷贝即可，因为我们只改 text 和 speaker）
            new_d = DialogData({
                'quest_id': d.quest_id,
                'speaker': d.speaker, # 先复制
                'text': d.text,       # 先复制
                'bg_img': d.bg_img,
                'action': d.action
            })
            
            # 执行替换
            for k, v in replacements.items():
                if k in new_d.text:
                    new_d.text = new_d.text.replace(k, v)
                if k in new_d.speaker:
                    new_d.speaker = new_d.speaker.replace(k, v)
                    # 重新解析 speaker_id
                    if new_d.speaker == '我': new_d.speaker_id = 9999
                    elif new_d.speaker == '村长': new_d.speaker_id = 9000
                    # 如果是门客名字，尝试寻找 ID (需外部逻辑支持，这里简单处理)
                    else: new_d.speaker_id = 9998 

            processed.append(new_d)
        return processed
    def _check_player_reach_target(self, player, target, radius):
        """
        检查玩家是否到达目标区域
        target: 区域名（如 AMBUSH_POINT）或坐标字符串 "x,y"
        radius: 判定半径（像素）
        """
        if not player:
            return False
        
        px, py = player.rect.centerx, player.rect.centery
        
        # 预定义的特殊区域点
        REACH_POINTS = {
            'AMBUSH_POINT': (2200, 2100),   # 城东门外的伏击点（城门附近）
            'RIVER_BANK': (3000, 2500),     # 河滩
            'HUNTER_CABIN': (500, 500),     # 猎户小屋
            'MARKET_CENTER': (1700, 1400),  # 市场中心
        }
        
        # 解析目标点
        target_pos = None
        if target in REACH_POINTS:
            target_pos = REACH_POINTS[target]
        elif ',' in str(target):
            # 格式: "x,y"
            try:
                parts = str(target).split(',')
                target_pos = (int(parts[0]), int(parts[1]))
            except:
                pass
        
        if not target_pos:
            print(f"[Quest] REACH任务目标解析失败: {target}")
            return False
        
        # 计算距离
        import math
        dist = math.hypot(px - target_pos[0], py - target_pos[1])
        check_radius = int(radius) if radius else 150
        
        if dist <= check_radius:
            print(f"[Quest] 玩家到达目标区域 {target}! 距离={dist:.0f}px <= {check_radius}px")
            return True
        return False

    def trigger_yuxishi_event(self, story_ui, ctx=None):
        """
        手动触发鱼西施事件
        可以由 EventManager 或其他系统调用
        """
        # 检查是否已经触发过
        if self.is_quest_finished('Q_YUXISHI_TRIGGER'):
            return False
        
        # 设置当前任务为鱼西施触发事件
        self.active_quest_id = 'Q_YUXISHI_TRIGGER'
        self.quest_status = QS_ACTIVE
        
        # 播放对话
        dialogs = self.get_dialog('Q_YUXISHI_TRIGGER')
        if dialogs:
            story_ui.start_dialog(dialogs)
            return True
        
        return False
    def get_quest_log_data(self):
        """返回 (active_list, finished_list) 供 UI 显示"""
        active_list = []
        if self.active_quest_id != "Q_FREE_PLAY":
            q = self.get_current_quest()
            status_str = "待接取"
            if self.quest_status == QS_ACTIVE: status_str = "进行中"
            elif self.quest_status == QS_READY: status_str = "可交付"
            
            active_list.append({
                'title': q.title,
                'desc': q.desc,
                'target': f"{q.target} x{q.count}" if q.count > 0 else "与NPC交谈",
                'status': status_str
            })
        
        finished_list = []
        # 按照 ID 顺序查找已完成的
        for qid in self.quests:
            if qid in self.finished_quests:
                q = self.quests[qid]
                finished_list.append({'title': q.title, 'desc': q.desc})
                
        return active_list, finished_list
    
    def _get_npc_name_by_id(self, npc_id_or_name):
        """根据 NPC ID 或名称获取显示名字，用于 UI 显示
        
        支持两种格式：
        1. NPC ID（如 '8002', '9000'）→ 返回对应名称
        2. NPC 名称（如 '鱼西施'）→ 直接返回
        """
        if not npc_id_or_name:
            return '未指定'
        
        # 如果是数字ID格式，使用模块级映射函数
        if npc_id_or_name.isdigit() or npc_id_or_name in ID_TO_NAME:
            return get_npc_name_by_id(npc_id_or_name)
        
        # 如果是名称格式（在 NAME_TO_ID 中存在），直接返回
        if npc_id_or_name in NAME_TO_ID:
            return npc_id_or_name
        
        # 兜底：直接返回原值
        return npc_id_or_name
    
    def get_current_objective_text(self, player=None, all_cards=[]):
        """侧边栏简略显示"""
        if not self.flags['guidance_visible']: return ""
        q = self.get_current_quest()
        if not q: return ""
        
        # 获取提交NPC的名字
        submit_npc_name = self._get_npc_name_by_id(q.submit_npc)
        
        if self.quest_status == QS_AVAILABLE:
            # 自动完成的任务不需要找NPC接取
            if q.submit_npc == '9999':
                return f"[!] 新任务：{q.title} (自动触发)"
            else:
                return f"[!] 新任务：{q.title} (找{submit_npc_name}接取)"
        elif self.quest_status == QS_READY:
            # 如果是自动完成的任务，提示玩家等待剧情
            if q.submit_npc == '9999':
                return f"[√] {q.title} 完成 (等待剧情触发...)"
            else:
                return f"[√] {q.title} 完成 (找{submit_npc_name}复命)"
        elif self.quest_status == QS_ACTIVE:
            # 计算进度
            current = 0
            prog_str = ""
            if player:
                if q.type == 'GATHER':
                    current = player.inventory.get(q.target, 0)
                    for c in all_cards:
                        if getattr(c, 'is_follower', False): current += c.inventory.get(q.target, 0)
                    prog_str = f"({current}/{q.count})"
                elif q.type == 'HAVE_UNIT':
                     for c in all_cards:
                        type_val = getattr(c, 'job', '') if hasattr(c, 'job') else getattr(c, 'building_type', '')
                        if type_val == q.target: current += 1
                     prog_str = f"({current}/{q.count})"
                elif q.type == 'RESOURCE_TOTAL':
                    if q.target == 'MONEY': current = player.money
                    prog_str = f"({current}/{q.count})"
                elif q.type == 'EAT':
                    # 饥饿恢复任务：显示当前饥饿值和目标值
                    current_hunger = getattr(player, 'hunger', 100)
                    target_hunger = int(q.count) if q.count else 50
                    if current_hunger < target_hunger:
                        prog_str = "([ok] 已恢复)"
                    else:
                        prog_str = f"(饥饿:{int(current_hunger)}→需<{target_hunger})"
                elif q.type in ['DIALOG', 'INTERACT']:
                    prog_str = ""  # 对话/交互类不显示进度
                elif q.type in ['COMBAT', 'RECRUIT']:
                    prog_str = "(进行中)"  # 战斗/招募类简单显示
                elif q.count > 0:
                    prog_str = f"({current}/{q.count})"
            
            return f">> {q.desc} {prog_str}"
            
        return ""
    
    def get_all_task_displays(self, player=None, all_cards=[]) -> list:
        """
        获取所有任务的展示数据（按优先级排序）
        
        返回 TaskDisplayData 列表，按优先级排序：
        生存 > 情报 > 势力 > 主线
        
        目前返回模拟数据，后续阶段填充真实数据
        """
        tasks = []
        
        # ===== 1. 生存任务（模拟数据） =====
        # TODO: 阶段一实现真实检测逻辑
        if player:
            hunger = getattr(player, 'hunger', 0)
            cold = getattr(player, 'cold', 0)
            
            # 【调试模式】始终显示一个生存任务，方便测试 UI
            # 后续删除此调试代码
            if hunger >= 70:
                tasks.append(TaskDisplayData(
                    task_type=TASK_TYPE_SURVIVAL,
                    text="得找点吃的",
                    is_urgent=True
                ))
            elif hunger >= 50:
                tasks.append(TaskDisplayData(
                    task_type=TASK_TYPE_SURVIVAL,
                    text="肚子有些饿了",
                    is_urgent=False
                ))
            else:
                # 【调试】低饥饿时也显示，方便看 UI 效果
                tasks.append(TaskDisplayData(
                    task_type=TASK_TYPE_SURVIVAL,
                    text="饥饿度测试(调试)",
                    is_urgent=False,
                    target_npc="自己",
                    objective="找到食物恢复饥饿值",
                    reward="恢复体力",
                    deadline_days=0,
                    description="肚子饿了，需要找点吃的填饱肚子。"
                ))
            
            # 寒冷警告（超过阈值才显示）
            if cold >= 70:
                tasks.append(TaskDisplayData(
                    task_type=TASK_TYPE_SURVIVAL,
                    text="快冻僵了",
                    is_urgent=True
                ))
        
        # ===== 2. 情报委托（模拟数据） =====
        # TODO: 阶段三实现真实数据
        tasks.append(TaskDisplayData(
            task_type=TASK_TYPE_INTEL,
            text="打探鱼西施的消息",
            progress="1/3",
            target_npc="鱼西施",
            objective="向3个不同的NPC打听鱼西施的近况",
            reward="鱼西施的好感度+20，铜钱500",
            deadline_days=7,
            description="鱼西施最近行踪神秘，有人想知道她最近在和谁来往。"
        ))
        
        # ===== 3. 势力任务（模拟数据） =====
        # TODO: 阶段五实现真实数据
        # 【调试】启用模拟数据，方便测试 UI
        tasks.append(TaskDisplayData(
            task_type=TASK_TYPE_FACTION,
            text="帮帮主收集铜钱",
            progress="50/100",
            target_npc="帮主",
            objective="收集100枚铜钱交给帮主",
            reward="帮派贡献+10，铜钱200",
            deadline_days=5,
            description="帮主需要资金扩充帮派势力，急需铜钱。"
        ))
        
        # ===== 4. 主线任务 =====
        # 从现有方法获取主线任务数据
        main_text = self.get_current_objective_text(player, all_cards)
        if main_text:
            is_complete = "[√]" in main_text
            # 清理前缀符号
            clean_text = main_text.replace("[!]", "").replace("[√]", "").replace(">>", "").strip()
            tasks.append(TaskDisplayData(
                task_type=TASK_TYPE_MAIN,
                text=clean_text,
                is_complete=is_complete
            ))
        else:
            # 【调试】无主线任务时显示模拟数据
            tasks.append(TaskDisplayData(
                task_type=TASK_TYPE_MAIN,
                text="主线任务测试(调试)",
                target_npc="村长",
                objective="前往村长家接取任务",
                reward="经验值+100，铜钱200",
                deadline_days=0,
                description="这是游戏的主线任务，请前往村长家了解详情。"
            ))
        
        # 按优先级排序
        tasks.sort(key=lambda t: TASK_PRIORITY.get(t.type, 99))
        
        return tasks
    
    def get_quest_title(self):
        q = self.get_current_quest()
        return q.title if q else ""
    def check_and_play_intro(self, all_cards, story_ui):
        """检查并播放开场剧情 (Main Loop 瘦身用)"""
        # 开场剧情其实就两段，一个是开头cg，还有一个是落地介绍
        if self.flags.get('intro_played') and self.flags.get('intro_played_dialog'): 
            return True
        
        # ═══════════════════════════════════════════════════════════════
        # 教程模式：Q_PROLOGUE 序章
        # ═══════════════════════════════════════════════════════════════
        if self.active_quest_id == 'Q_PROLOGUE' and not self.flags.get('intro_played'):
             self.flags['intro_played'] = True
             dialogs = self.get_dialog('Q_PROLOGUE')
             story_ui.start_dialog(dialogs)
             self.quest_status = QS_ACTIVE # 序章自动激活
             print(f"[Quest] 自动激活了第一段开场剧情 (教程模式)")
             return True
                 
        if self.active_quest_id == 'Q0_FIND_ELDER' and not self.flags.get('intro_played_dialog'):
            self.flags['intro_played'] = True
            self.flags['intro_played_dialog'] = True # 防止重复播放
            
            follower = next((c for c in all_cards if getattr(c, 'is_follower', False)), None)
            dialog_key = 'INTRO_FOLLOWER' if follower else 'INTRO_SOLO'
            replacements = {}
            if follower: replacements['{follower}'] = follower.name
            
            intro_dialogs = self.get_dialog_by_key(dialog_key, replacements)
            if intro_dialogs:
                story_ui.start_dialog(intro_dialogs)
                print(f"[Quest] 自动激活了第二段开场剧情 (教程模式)")
                return True
        
        # ═══════════════════════════════════════════════════════════════
        # 【新增】沙盒模式：鱼西施事件作为开场
        # ═══════════════════════════════════════════════════════════════
        if self.active_quest_id == 'Q_YUXISHI_TRIGGER' and self.flags.get('sandbox_intro_ready'):
            self.flags['sandbox_intro_ready'] = False  # 防止重复
            self.flags['intro_played'] = True
            self.flags['intro_played_dialog'] = True
            
            dialogs = self.get_dialog('Q_YUXISHI_TRIGGER')
            if dialogs:
                story_ui.start_dialog(dialogs)
                self.quest_status = QS_ACTIVE
                print(f"[Quest] 自动激活沙盒开场剧情：鱼西施事件")
                return True
        
        return False

    # ==================== 调试功能：快速完成任务 ====================
    
    # 需要保留演出效果的 action 列表（跳过时会执行这些但停下来让玩家观看）
    CINEMATIC_ACTIONS = {
        # 动画/演出
        'POPI_FLEE',              # 泼皮逃跑动画
        'EVENT_NPC_RELEASE',      # 释放事件NPC
        # 战斗相关
        'KNOCKOUT',               # 击倒玩家
        'START_AUTO_COMBAT',      # 自动战斗（玩家被动挨打）
        'PLAYER_DEFEATED',        # 玩家被打倒
        'PLAYER_ATTACK_POPI',     # 玩家攻击泼皮
        'START_COMBAT_BULLY',     # 开始与泼皮战斗
        # 生成/伏击
        'SPAWN_ENEMY_NEAR',       # 在玩家附近生成敌人
        'SPAWN_BULLY_FOR_REVENGE',# 生成泼皮供反击
        'TRIGGER_REVENGE_AMBUSH', # 触发报复伏击
        # 屏幕效果
        'FADE_TO_BLACK',          # 黑屏渐入
        'FADE_FROM_BLACK',        # 黑屏渐出
        'FLASH_WHITE',            # 白屏闪烁（被打击）
        # 传送
        'TELEPORT_PLAYER',        # 传送玩家
    }
    
    def skip_current_dialogs(self, ctx, _recursion_depth=0):
        """
        【调试功能】快速完成当前任务的对话
        
        跳过规则：
        - 跳过纯对话文字
        - 遇到 CHOICE 或 SHOW_CHOICE 时停止，显示选择界面
        - 遇到演出型 action（如泼皮逃跑）时执行它但停止跳过，让玩家观看
        
        Returns:
            (bool, str): (是否成功, 说明文字)
        """
        # 防止无限递归
        MAX_RECURSION = 20
        if _recursion_depth > MAX_RECURSION:
            return False, f"跳过达到上限({MAX_RECURSION})"
        
        story_ui = ctx.story_ui if ctx else None
        total_skipped = 0
        
        # 1. 检查当前任务
        q = self.get_current_quest()
        if not q:
            return False, "没有当前任务"
        
        # 2. 如果是 CHOICE 类型任务，检查是否已有选项显示
        if q.type == 'CHOICE':
            # 检查选择UI是否已经激活
            if story_ui and getattr(story_ui, 'choice_mode', False):
                return True, "请做出选择"
            # 否则尝试显示选择
            options = self.get_choice_options()
            if options and story_ui:
                prompt = q.title if q else "做出你的选择"
                story_ui.show_choice(options, prompt)
                return True, "请做出选择"
            return False, "选择任务需要玩家决定"
        
        # 3. 检查是否正在播放对话
        if story_ui and story_ui.is_active:
            skipped_count = 0
            
            # 先处理当前行的 action（如果有）
            if story_ui.current_line and story_ui.current_line.action:
                action_str = story_ui.current_line.action
                # 检查是否是演出型 action
                if self._is_cinematic_action(action_str):
                    # 执行演出，但不继续跳过，让玩家观看
                    self.trigger_action(action_str, ctx)
                    # 移到下一句对话（如果有的话）
                    if story_ui.dialog_queue:
                        story_ui.current_line = story_ui.dialog_queue.pop(0)
                        story_ui.text_progress = 0
                    else:
                        story_ui.current_line = None
                        story_ui.is_active = False
                        story_ui._restore_actor_movement()
                    return True, f"演出中..."
                elif 'SHOW_CHOICE' in action_str:
                    self.trigger_action(action_str, ctx)
                    story_ui.current_line = None
                    story_ui.is_active = False
                    story_ui._restore_actor_movement()
                    # 【关键】立即显示选择界面
                    options = self.get_choice_options()
                    if options:
                        q = self.get_current_quest()
                        prompt = q.title if q else "做出你的选择"
                        story_ui.show_choice(options, prompt)
                    return True, "请做出选择"
                else:
                    # 普通 action，执行并继续
                    self.trigger_action(action_str, ctx)
            
            # 处理队列中剩余的对话
            while story_ui.dialog_queue:
                dialog_line = story_ui.dialog_queue.pop(0)
                skipped_count += 1
                
                # 检查这行对话的 action
                if dialog_line.action:
                    action_str = dialog_line.action
                    
                    # 检查是否是 SHOW_CHOICE 动作
                    if 'SHOW_CHOICE' in action_str:
                        self.trigger_action(action_str, ctx)
                        story_ui.current_line = None
                        story_ui.is_active = False
                        story_ui.bg_image_surf = None
                        story_ui._restore_actor_movement()
                        # 【关键】立即显示选择界面，避免main.py误判剧情结束
                        options = self.get_choice_options()
                        if options:
                            q = self.get_current_quest()
                            prompt = q.title if q else "做出你的选择"
                            story_ui.show_choice(options, prompt)
                        return True, f"跳过{skipped_count}句，请选择"
                    
                    # 检查是否是演出型 action
                    if self._is_cinematic_action(action_str):
                        # 执行演出
                        self.trigger_action(action_str, ctx)
                        # 把这行设为当前行，让玩家看到演出后的对话
                        story_ui.current_line = dialog_line
                        story_ui.text_progress = len(dialog_line.text) if dialog_line.text else 0
                        return True, f"跳过{skipped_count}句，演出中..."
                    
                    # 普通 action，执行并继续跳过
                    self.trigger_action(action_str, ctx)
            
            # 对话队列已清空，结束对话
            last_speaker_id = None
            if story_ui.current_line:
                last_speaker_id = story_ui.current_line.speaker_id
            
            story_ui.current_line = None
            story_ui.is_active = False
            story_ui.bg_image_surf = None
            story_ui._restore_actor_movement()
            
            # 通知任务系统对话结束
            self.on_dialog_finished(npc_id=last_speaker_id, ctx=ctx)
            total_skipped += skipped_count
            
            # 检查是否需要显示选择界面
            if self.pending_choice_dialog:
                self.pending_choice_dialog = False
                options = self.get_choice_options()
                if options:
                    prompt = q.title if q else "做出你的选择"
                    story_ui.show_choice(options, prompt)
                    return True, f"跳过{total_skipped}句，请选择"
            
            # [关键] 检查是否有新的对话被启动，继续跳过
            if story_ui.is_active:
                return self.skip_current_dialogs(ctx, _recursion_depth + 1)
            
            # 检查当前任务是否变了，如果有新任务继续跳过
            new_q = self.get_current_quest()
            if new_q and new_q.id != q.id:
                if new_q.type == 'CHOICE':
                    options = self.get_choice_options()
                    if options and story_ui:
                        prompt = new_q.title
                        story_ui.show_choice(options, prompt)
                        return True, f"跳过{total_skipped}句，请选择"
                elif new_q.type == 'DIALOG':
                    dialogs = self.get_dialog(new_q.id)
                    if dialogs:
                        story_ui.start_dialog(dialogs)
                        return self.skip_current_dialogs(ctx, _recursion_depth + 1)
            
            return True, f"跳过{total_skipped}句对话"
        
        # 4. 如果没有在播放对话，尝试自动触发当前任务的对话
        dialogs = self.get_dialog_for_current_quest()
        if dialogs:
            # 加载对话后快速执行
            if story_ui:
                story_ui.start_dialog(dialogs)
                # 递归调用自己来跳过刚加载的对话
                return self.skip_current_dialogs(ctx, _recursion_depth + 1)
        
        # 5. 没有对话可跳过，尝试直接推进任务
        if self.quest_status == QS_AVAILABLE:
            self.accept_quest()
            # 接取后可能有新对话，继续跳过
            if story_ui and story_ui.is_active:
                return self.skip_current_dialogs(ctx, _recursion_depth + 1)
            return True, f"接取: {q.title}"
        elif self.quest_status == QS_READY:
            self.advance_quest()
            # 完成后可能有新任务对话
            if story_ui and story_ui.is_active:
                return self.skip_current_dialogs(ctx, _recursion_depth + 1)
            # 检查新任务
            new_q = self.get_current_quest()
            if new_q and new_q.type in ['DIALOG', 'CHOICE']:
                return self.skip_current_dialogs(ctx, _recursion_depth + 1)
            return True, f"完成: {q.title}"
        elif self.quest_status == QS_ACTIVE:
            # 检查是否是纯对话任务可以直接完成
            if q.type == 'DIALOG':
                self.quest_status = QS_READY
                self.advance_quest()
                # 完成后可能有新任务
                if story_ui and story_ui.is_active:
                    return self.skip_current_dialogs(ctx, _recursion_depth + 1)
                new_q = self.get_current_quest()
                if new_q and new_q.type in ['DIALOG', 'CHOICE']:
                    return self.skip_current_dialogs(ctx, _recursion_depth + 1)
                return True, f"跳过: {q.title}"
            else:
                return False, f"进行中: {q.title} (需要完成目标)"
        
        return False, "无法跳过当前状态"