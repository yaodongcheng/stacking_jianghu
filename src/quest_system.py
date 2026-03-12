# --- src/quest_system.py ---
import csv
import random
import os
from src.definitions import *
from src.entities import Player, NPC, Building, Resource
from src.utils import resource_path

# 导入角色种子数据，用于动态构建 ID 映射
from src.data.character_seeds import SEEDS

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
        
        self.action_handlers = {
            'UNLOCK_GUIDANCE': self._action_unlock_guidance,
            'SHOW_UI_ONLY': lambda: self.set_flag('guidance_visible', True),
            'UNLOCK_REFUGEE': self._action_unlock_refugee,
            'START_RAID': lambda: print(">> 触发山贼袭击逻辑 (需对接EventManager) <<"),
            # 鱼西施事件相关
            'SHOW_CHOICE': self._action_show_choice,
            'SHOW_EVENT_CHOICE': self._action_show_choice,  # 别名：事件对话中使用
            'REWARD_GOOD': self._action_reward_good,
            'TRIGGER_BOUNTY': self._action_trigger_bounty,
            # 【新增】好感度调整
            'AFFINITY_YUXISHI': self._action_affinity_change,
            # 恶霸任务相关
            'TRIGGER_BULLY_BOUNTY': self._action_trigger_bully_bounty,
            'REWARD_BULLY_VICTORY': self._action_reward_bully_victory,
            # 【新增】剧情演出行为
            'POPI_FLEE': self._action_popi_flee,      # 泼皮逃跑
            'EVENT_NPC_RELEASE': self._action_release_event_npcs,  # 释放事件NPC恢复正常AI
            'PLAYER_ATTACK_POPI': self._action_player_attack_popi,  # 玩家攻击泼皮
            # 【新增】新手引导剧情行为
            'PLAYER_DEFEATED': self._action_player_defeated,  # 玩家被打倒
            'TRIGGER_HUNGRY': self._action_trigger_hungry,    # 触发饥饿状态
            'RECRUIT_ZHANGSAN': self._action_recruit_zhangsan,  # 招募张三
            'SPAWN_BULLY_FOR_REVENGE': self._action_spawn_bully,  # 生成泼皮供反击
            'START_COMBAT_BULLY': self._action_start_combat_bully,  # 开始与泼皮战斗
            'COMPLETE_TUTORIAL': self._action_complete_tutorial,  # 完成新手教程
            # 【新增】过渡剧情
            'TRIGGER_REVENGE_AMBUSH': self._action_trigger_revenge_ambush,  # 触发报复伏击
            # 【新增】经济任务奖励
            'REWARD_FISH_MONEY': self._action_reward_fish_money,  # 卖鱼获得铜钱
            # 【新增】势力引导任务
            'SET_FAME_REQ': self._action_set_fame_req,  # 设置声望要求
            'JOIN_ORG': self._action_join_org,  # 加入势力
            # 【新增】优化方案新增的 action handlers
            'SET_FLAG': self._action_set_flag,  # 设置标记
            'COMPLETE_ANY_TASK': self._action_complete_any_task,  # 完成任意任务
            'ORG_TASK': self._action_org_task,  # 完成组织任务
            'ORG_RANK': self._action_org_rank,  # 晋升为特定等级
            'WAR_PARTICIPATE': self._action_war_participate,  # 参与势力战争
            'OCCUPY_BUILDING': self._action_occupy_building,  # 占领建筑
            'CONTROL_BUILDING': self._action_control_building,  # 控制特定数量的建筑
            'INVESTIGATE': self._action_investigate,  # 收集情报
            
            # ═══════════════════════════════════════════════════════════════
            # 【轻量演出系统】场景/状态/转场Action
            # ═══════════════════════════════════════════════════════════════
            # 转场效果
            'FADE_TO_BLACK': self._action_fade_to_black,       # 黑屏渐入
            'FADE_FROM_BLACK': self._action_fade_from_black,   # 黑屏渐出
            'FLASH_WHITE': self._action_flash_white,           # 白屏闪烁（被打击效果）
            
            # 时间/场景
            'ADVANCE_TIME': self._action_advance_time,         # 时间推进
            'TELEPORT_PLAYER': self._action_teleport_player,   # 传送玩家
            
            # 状态设置
            'SET_HUNGER': self._action_set_hunger,             # 设置饥饿值
            'SET_HP': self._action_set_hp,                     # 设置生命值
            'SET_STAMINA': self._action_set_stamina,           # 设置体力
            
            # NPC操作
            'SPAWN_ENEMY_NEAR': self._action_spawn_enemy_near, # 在玩家附近生成敌人
            'DESPAWN_NPC': self._action_despawn_npc,           # 移除指定NPC
            'KNOCKOUT': self._action_knockout_player,          # 玩家昏倒效果
            
            # 战斗
            'START_AUTO_COMBAT': self._action_start_auto_combat,  # 自动战斗（玩家被动挨打）
        }
        
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
    def _action_unlock_refugee(self, ctx=None):
        self.set_flag('refugee_unlocked', True)
        if ctx:
            ctx.event_manager.spawn_refugee_immediately(ctx)
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
        if base_action in self.action_handlers:
            handler = self.action_handlers[base_action]
            try:
                # 尝试传递参数
                if action_params:
                    handler(ctx, *action_params)
                else:
                    handler(ctx)
            except TypeError:
                try:
                    handler()  # 不接受参数的handler (如lambda)
                except TypeError:
                    # 可能handler只接受ctx但我们传了额外参数
                    handler(ctx)
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
        choice_effects = self._get_choice_effects(q.id, choice_key)
        
        # ═══════════════════════════════════════════════════════════════
        # 【核心：剧情记忆系统】为所有当事人添加记忆
        # 当发生重要剧情选择时，所有参与者都应该记住这件事
        # ═══════════════════════════════════════════════════════════════
        self._apply_story_memories(q.id, choice_key, player, all_cards, ft_manager)
        
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
    
    # ═══════════════════════════════════════════════════════════════
    # 【核心：剧情记忆系统】
    # 为所有剧情参与者添加持久化记忆，用于后续AI叙事
    # ═══════════════════════════════════════════════════════════════
    
    def _apply_story_memories(self, quest_id, choice_key, player, all_cards, ft_manager=None):
        """
        根据剧情分支为所有当事人添加记忆
        
        设计原则：
        1. 受害者记忆自己被欺负 / 被帮助
        2. 加害者记忆自己欺负了谁
        3. 帮助者（玩家）记忆自己帮助了谁 / 参与欺负了谁
        4. 好感度根据行为调整
        
        Args:
            quest_id: 当前任务ID
            choice_key: 玩家的选择 ('GOOD', 'EVIL' 等)
            player: 玩家对象
            all_cards: 所有卡牌列表（用于查找NPC）
            ft_manager: 浮动文字管理器（可选）
        """
        if not all_cards:
            print("[Quest] 警告: all_cards 为空，无法生成剧情记忆")
            return
        
        # NPC 名字 → ID 映射（用于查找NPC）
        def find_npc_by_name(name):
            for card in all_cards:
                if hasattr(card, 'name') and name in card.name:
                    return card
            return None
        
        # ═══════════════════════════════════════════════════════════════
        # 鱼西施事件记忆配置
        # ═══════════════════════════════════════════════════════════════
        if quest_id == 'Q_YUXISHI_CHOICE':
            yuxishi = find_npc_by_name('鱼西施')
            popi_niuer = find_npc_by_name('泼皮牛二')
            popi_goudan = find_npc_by_name('泼皮狗蛋')
            
            # 无论玩家选什么，鱼西施都被泼皮欺负过
            # 泼皮也记住自己欺负过鱼西施
            if yuxishi:
                # 鱼西施记忆：被泼皮牛二和狗蛋欺负
                if popi_niuer:
                    yuxishi.add_memory(
                        event_type='BULLIED_BY',
                        target_id=getattr(popi_niuer, 'id', None),
                        target_name='泼皮牛二',
                        description='在城东街头被泼皮牛二骚扰欺负',
                        importance=4
                    )
                    yuxishi.modify_affinity(getattr(popi_niuer, 'id', 0), -40)  # 极度厌恶
                
                if popi_goudan:
                    yuxishi.add_memory(
                        event_type='BULLIED_BY',
                        target_id=getattr(popi_goudan, 'id', None),
                        target_name='泼皮狗蛋',
                        description='泼皮狗蛋帮着牛二一起欺负自己',
                        importance=3
                    )
                    yuxishi.modify_affinity(getattr(popi_goudan, 'id', 0), -30)
            
            # 泼皮们记住自己欺负过鱼西施
            if popi_niuer and yuxishi:
                popi_niuer.add_memory(
                    event_type='BULLIED',
                    target_id=getattr(yuxishi, 'id', None),
                    target_name='鱼西施',
                    description='在城东街头调戏欺负鱼西施',
                    importance=2  # 对泼皮来说是家常便饭
                )
            
            if popi_goudan and yuxishi:
                popi_goudan.add_memory(
                    event_type='BULLIED',
                    target_id=getattr(yuxishi, 'id', None),
                    target_name='鱼西施',
                    description='跟着牛二一起欺负鱼西施',
                    importance=2
                )
            
            # ───────────────────────────────────────────────────────────
            # 玩家选择 GOOD：出手相救
            # ───────────────────────────────────────────────────────────
            if choice_key == 'GOOD':
                player_id = getattr(player, 'id', 9999)
                player_name = getattr(player, 'name', '玩家')
                
                # 鱼西施记住：被玩家帮助
                if yuxishi:
                    yuxishi.add_memory(
                        event_type='HELPED_BY',
                        target_id=player_id,
                        target_name=player_name,
                        description=f'{player_name}挺身而出，救我于泼皮之手',
                        importance=5  # 恩情，极其重要
                    )
                    yuxishi.modify_affinity(player_id, +50)  # 感恩戴德
                    yuxishi.affinity_to_player = yuxishi.get_affinity_to(player_id)  # 同步快捷属性
                    
                    if ft_manager:
                        ft_manager.add_text("鱼西施好感度 +50", 
                                           yuxishi.rect.centerx, yuxishi.rect.top - 60, (255, 200, 255))
                
                # 泼皮们记住：和玩家动过手
                if popi_niuer:
                    popi_niuer.add_memory(
                        event_type='FOUGHT_WITH',
                        target_id=player_id,
                        target_name=player_name,
                        description=f'在欺负鱼西施时被{player_name}阻止，动了手',
                        importance=4
                    )
                    popi_niuer.modify_affinity(player_id, -40)  # 结下梁子
                    popi_niuer.sync_affinity_to_player(player_id)  # 同步到快捷属性
                
                if popi_goudan:
                    popi_goudan.add_memory(
                        event_type='FOUGHT_WITH',
                        target_id=player_id,
                        target_name=player_name,
                        description=f'被{player_name}打了，怀恨在心',
                        importance=3
                    )
                    popi_goudan.modify_affinity(player_id, -30)
                    popi_goudan.sync_affinity_to_player(player_id)  # 同步到快捷属性
                
                # 玩家记住：帮助了鱼西施，以及对他们的好感度
                if player and hasattr(player, 'add_memory'):
                    player.add_memory(
                        event_type='HELPED',
                        target_id=getattr(yuxishi, 'id', None) if yuxishi else None,
                        target_name='鱼西施',
                        description='在城东出手相救被泼皮欺负的鱼西施',
                        importance=4
                    )
                    # 玩家对鱼西施好感度
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
                        # 玩家对泼皮们的好感度
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
                
                # 【新增】注入LLM记忆系统
                try:
                    from src.llm.event_memory_bridge import inject_help_memory
                    if yuxishi:
                        inject_help_memory(player, yuxishi, "出手相救")
                except Exception as e:
                    print(f"[Quest] LLM记忆注入失败: {e}")
                
                print(f"[Quest] 记忆系统: 玩家选择GOOD，已为鱼西施、泼皮、玩家添加记忆")
            
            # ───────────────────────────────────────────────────────────
            # 玩家选择 EVIL：助纣为虐
            # ───────────────────────────────────────────────────────────
            elif choice_key == 'EVIL':
                player_id = getattr(player, 'id', 9999)
                player_name = getattr(player, 'name', '玩家')
                
                # 鱼西施记住：被玩家也欺负了
                if yuxishi:
                    yuxishi.add_memory(
                        event_type='BULLIED_BY',
                        target_id=player_id,
                        target_name=player_name,
                        description=f'{player_name}不仅不帮忙，还和泼皮一起欺负我',
                        importance=5  # 仇恨，极其重要
                    )
                    yuxishi.modify_affinity(player_id, -60)  # 深仇大恨
                    yuxishi.affinity_to_player = yuxishi.get_affinity_to(player_id)
                    
                    if ft_manager:
                        ft_manager.add_text("鱼西施好感度 -60", 
                                           yuxishi.rect.centerx, yuxishi.rect.top - 60, (255, 50, 50))
                
                # 泼皮们记住：玩家是"自己人"
                if popi_niuer:
                    popi_niuer.add_memory(
                        event_type='PARTNERED_WITH',
                        target_id=player_id,
                        target_name=player_name,
                        description=f'{player_name}和咱们一起欺负鱼西施，是自己人',
                        importance=3
                    )
                    popi_niuer.modify_affinity(player_id, +30)  # 狼狈为奸
                    popi_niuer.sync_affinity_to_player(player_id)  # 同步到快捷属性
                
                if popi_goudan:
                    popi_goudan.add_memory(
                        event_type='PARTNERED_WITH',
                        target_id=player_id,
                        target_name=player_name,
                        description=f'{player_name}帮着我们欺负人，够意思',
                        importance=2
                    )
                    popi_goudan.modify_affinity(player_id, +20)
                    popi_goudan.sync_affinity_to_player(player_id)  # 同步到快捷属性
                
                # 玩家记住：自己助纣为虐，以及对他们的好感度
                if player and hasattr(player, 'add_memory'):
                    player.add_memory(
                        event_type='BULLIED',
                        target_id=getattr(yuxishi, 'id', None) if yuxishi else None,
                        target_name='鱼西施',
                        description='在城东和泼皮一起欺负鱼西施，分了赃',
                        importance=4
                    )
                    # 玩家对鱼西施好感度（助纣为虐，也不会喜欢她）
                    if yuxishi and hasattr(player, 'modify_affinity'):
                        player.modify_affinity(getattr(yuxishi, 'id', 0), -10)
                    
                    # 玩家对泼皮们的好感度（狼狈为奸，倒是看得顺眼了）
                    if popi_niuer and hasattr(player, 'modify_affinity'):
                        player.modify_affinity(getattr(popi_niuer, 'id', 0), +15)
                    if popi_goudan and hasattr(player, 'modify_affinity'):
                        player.modify_affinity(getattr(popi_goudan, 'id', 0), +10)
                
                print(f"[Quest] 记忆系统: 玩家选择EVIL，已为所有当事人添加记忆")
        
        # ═══════════════════════════════════════════════════════════════
        # 可以在这里扩展更多剧情的记忆配置...
        # ═══════════════════════════════════════════════════════════════
    
    def _get_choice_effects(self, quest_id, choice_key):
        """
        获取选择的效果数据
        这里硬编码一些预设效果，也可以扩展为从CSV读取
        """
        # 鱼西施事件的效果定义
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
                    'money': 20,  # 泼皮给你分赃
                    'bounty': {
                        'issuer': 'YAMEN',  # 衙门发布悬赏
                        'reward': 30,
                        'reason': '欺压良善'
                    },
                    'message': '你选择了黑暗面...',
                }
            },
            # 可以添加更多事件的效果...
        }
        
        quest_effects = CHOICE_EFFECTS.get(quest_id, {})
        return quest_effects.get(choice_key, {})
    
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
            effects = self._get_choice_effects(q.id, choice_key)
            
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
    def _action_unlock_guidance(self):
        self.set_flag('guidance_visible', True)
    def _action_unlock_guidance_strict(self):      
        print("触发：解锁引导并推进任务")
        self.set_flag('guidance_visible', True)
        self.advance_quest()
    
    # ═══════════════════════════════════════════════════════════════
    # 鱼西施事件 Action Handlers
    # ═══════════════════════════════════════════════════════════════
    
    def _action_show_choice(self, ctx=None, choice_quest_id=None):
        """
        显示选择对话框 - 同时让玩家移动到事件现场
        
        Args:
            ctx: 游戏上下文
            choice_quest_id: 可选参数，指定要跳转到的选择任务ID
                            如果不提供，默认使用当前任务的 next_id
        """
        print(f"[Quest] Action: SHOW_CHOICE - 准备显示选择界面 (目标任务: {choice_quest_id or '默认下一个'})")
        
        # ═══════════════════════════════════════════════════════════════
        # 【大宋实况事件】检查是否是大宋实况事件的选择
        # 如果是，不推进主线任务，而是显示事件选项
        # ═══════════════════════════════════════════════════════════════
        try:
            from src.live_news_to_dialog import get_news_dialog_bridge
            news_bridge = get_news_dialog_bridge()
            
            if news_bridge.is_choice_pending():
                # 这是大宋实况事件，从 news_item 获取选项
                current_news = news_bridge.get_current_news()
                if current_news and hasattr(current_news, 'choices') and current_news.choices:
                    print(f"[Quest] SHOW_EVENT_CHOICE - 大宋实况事件选择，共 {len(current_news.choices)} 个选项")
                    
                    # 构建选项格式供 StoryUI 显示
                    options = []
                    for i, choice in enumerate(current_news.choices):
                        if isinstance(choice, dict):
                            text = choice.get('text', f'选项{i+1}')
                            effect = choice.get('effect', '')
                            # 使用索引作为 key (A, B, C 或 0, 1, 2)
                            key = chr(ord('A') + i) if i < 3 else str(i)
                        else:
                            text = str(choice)
                            effect = ''
                            key = chr(ord('A') + i) if i < 3 else str(i)
                        
                        options.append({
                            'key': key,
                            'text': text,
                            'hint': effect[:30] if effect else ''
                        })
                    
                    # 显示选择界面
                    if ctx and hasattr(ctx, 'story_ui') and ctx.story_ui:
                        prompt = current_news.title if hasattr(current_news, 'title') else "做出你的选择"
                        ctx.story_ui.show_choice(options, prompt)
                        print(f"[Quest] 大宋实况事件选择界面已显示")
                    
                    # 注意：不调用 advance_quest()，不设置 pending_choice_dialog
                    return
                else:
                    print(f"[Quest] 警告：大宋实况事件没有选项数据")
        except Exception as e:
            print(f"[Quest] 检查大宋实况事件失败: {e}")
        
        # ═══════════════════════════════════════════════════════════════
        # 主线任务选择（原有逻辑）
        # ═══════════════════════════════════════════════════════════════
        self.pending_choice_dialog = True
        
        # 【新增】让玩家移动到事件中心附近（避开剧情角色）
        if ctx:
            player = getattr(ctx, 'player', None)
            event_focus = getattr(ctx, 'event_focus_point', None)
            
            if player and event_focus:
                from src.atomic_actions import MoveToPosition
                import math
                
                # 收集所有剧情角色的位置
                occupied_positions = []
                yuxishi = getattr(ctx, 'yuxishi_npc', None)
                popi_npcs = getattr(ctx, 'popi_npcs', [])
                
                if yuxishi:
                    occupied_positions.append((yuxishi.rect.centerx, yuxishi.rect.centery))
                for popi in popi_npcs:
                    occupied_positions.append((popi.rect.centerx, popi.rect.centery))
                
                # 【智能位置计算】寻找一个不与任何角色重叠的安全位置
                # 候选位置：从玩家当前位置到事件中心方向的多个点
                min_dist_to_npcs = 80  # 与NPC的最小距离
                
                # 方案1：站在事件右侧（玩家来的方向），Y轴略偏下
                candidate_positions = [
                    (event_focus[0] + 120, event_focus[1] + 50),   # 右下方
                    (event_focus[0] + 100, event_focus[1] - 50),   # 右上方
                    (event_focus[0] + 150, event_focus[1]),        # 正右侧
                    (event_focus[0], event_focus[1] - 100),        # 正上方（面对泼皮）
                    (event_focus[0] - 120, event_focus[1] - 50),   # 左上方
                ]
                
                def is_safe_position(px, py):
                    """检查位置是否与所有角色保持安全距离"""
                    for ox, oy in occupied_positions:
                        dist = math.hypot(px - ox, py - oy)
                        if dist < min_dist_to_npcs:
                            return False
                    return True
                
                # 选择第一个安全位置
                target_x, target_y = candidate_positions[0]  # 默认值
                for cx, cy in candidate_positions:
                    if is_safe_position(cx, cy):
                        target_x, target_y = cx, cy
                        break
                
                # 使用原子动作控制玩家移动
                move_action = MoveToPosition(target_x, target_y, stop_dist=20, reason="介入事件")
                player.action_queue.enqueue(move_action)
                player.ai_reason = "介入事件..."
                print(f"[Quest] 玩家开始移动到事件现场 ({target_x}, {target_y}), 避开{len(occupied_positions)}个NPC")
        
        # 推进到选择任务（如果指定了目标任务ID，则跳转到指定任务）
        if choice_quest_id and choice_quest_id in self.quests:
            self.advance_quest(manual_next_id=choice_quest_id)
        else:
            self.advance_quest()
        
    def _action_reward_good(self, ctx=None):
        """正义路线奖励 - 仅增加声望，不再给鱼"""
        print("[Quest] Action: REWARD_GOOD - 发放正义奖励(声望)")
        if ctx and hasattr(ctx, 'player'):
            player = ctx.player
            # 增加声望
            player.fame = getattr(player, 'fame', 0) + 10
            
            # 如果有浮动文字管理器，显示获得物品
            if hasattr(ctx, 'ft_manager') and ctx.ft_manager:
                ctx.ft_manager.add_text("+10 声望", player.rect.centerx, player.rect.top - 30, (255, 215, 0))
        
        # 设置标记
        self.set_flag('yuxishi_saved', True)
        self.set_flag('choice_Q_YUXISHI_CHOICE', 'GOOD')
    
    def _action_affinity_change(self, ctx=None, amount='30'):
        """改变NPC对玩家的好感度 - 通用方法
        
        调用格式: AFFINITY_YUXISHI:30 或 AFFINITY_ZHANGSAN:-10
        """
        print(f"[Quest] Action: AFFINITY_CHANGE - 调整好感度 {amount}")
        try:
            delta = int(amount)
        except:
            delta = 30
            
        if ctx and hasattr(ctx, 'all_cards'):
            # 找到鱼西施
            for card in ctx.all_cards:
                if getattr(card, 'name', None) == '鱼西施':
                    # 增加好感度
                    current = getattr(card, 'affinity_to_player', 0)
                    card.affinity_to_player = max(-100, min(100, current + delta))
                    print(f"[Quest] 鱼西施好感度: {current} -> {card.affinity_to_player}")
                    
                    # 显示浮动文字
                    if hasattr(ctx, 'ft_manager') and ctx.ft_manager:
                        color = (255, 200, 100) if delta > 0 else (200, 100, 100)
                        text = f"好感+{delta}" if delta > 0 else f"好感{delta}"
                        ctx.ft_manager.add_text(text, card.rect.centerx, card.rect.top - 20, color)
                    break
        
    def _action_trigger_bounty(self, ctx=None):
        """邪恶路线触发悬赏"""
        print("[Quest] Action: TRIGGER_BOUNTY - 触发悬赏")
        if ctx:
            # 获取势力战争系统
            faction_war_system = getattr(ctx, 'faction_war_system', None)
            player = getattr(ctx, 'player', None)
            
            if faction_war_system and player:
                # 发布悬赏
                faction_war_system.post_bounty(
                    issuer_org='YAMEN',
                    target_id=getattr(player, 'id', 9999),
                    reward=30,
                    reason='欺压良善',
                    is_player_target=True
                )
                
                # 给予金钱（分赃）
                player.money = getattr(player, 'money', 0) + 20
                
                # 降低声望
                player.fame = max(0, getattr(player, 'fame', 0) - 5)
                
                # 浮动文字提示
                if hasattr(ctx, 'ft_manager') and ctx.ft_manager:
                    ctx.ft_manager.add_text("+20 铜钱", player.rect.centerx, player.rect.top - 30, (255, 215, 0))
                    ctx.ft_manager.add_text("-5 声望", player.rect.centerx, player.rect.top - 50, (255, 80, 80))
                    ctx.ft_manager.add_text("[!] 被悬赏了！", player.rect.centerx, player.rect.top - 70, (255, 50, 50))
        
        # 设置标记
        self.set_flag('yuxishi_saved', False)
        self.set_flag('choice_Q_YUXISHI_CHOICE', 'EVIL')
    
    def _action_reward_fish_money(self, ctx=None):
        """经济任务奖励：卖鱼获得铜钱
        
        任务场景：玩家帮鱼西施捕了3条鱼，交给她后获得报酬
        """
        print("[Quest] Action: REWARD_FISH_MONEY - 卖鱼获得铜钱奖励")
        if ctx and hasattr(ctx, 'player'):
            player = ctx.player
            
            # 移除已交付的鱼（任务系统应已检测扣除，此处做兜底）
            fish_key = '生鱼'
            if fish_key in player.inventory and player.inventory[fish_key] >= 3:
                player.inventory[fish_key] -= 3
                if player.inventory[fish_key] <= 0:
                    del player.inventory[fish_key]
            
            # 发放铜钱奖励（3条鱼 × 10铜/条 = 30铜）
            reward_money = 30
            player.money = getattr(player, 'money', 0) + reward_money
            
            # 小幅提升声望（帮助他人）
            fame_gain = 5
            player.fame = getattr(player, 'fame', 0) + fame_gain
            
            # 浮动文字提示
            if hasattr(ctx, 'ft_manager') and ctx.ft_manager:
                ctx.ft_manager.add_text(f"+{reward_money} 铜钱", 
                                       player.rect.centerx, player.rect.top - 30, (255, 215, 0))
                ctx.ft_manager.add_text(f"+{fame_gain} 声望", 
                                       player.rect.centerx, player.rect.top - 50, (255, 200, 100))
        
        # 设置标记，标识首个经济任务完成
        self.set_flag('first_money_quest_done', True)
    
    def _action_trigger_bully_bounty(self, ctx=None):
        """恶霸王老虎发出悬赏"""
        print("[Quest] Action: TRIGGER_BULLY_BOUNTY - 恶霸发出悬赏")
        if ctx:
            # 兼容两种属性名: faction_war 或 faction_war_system
            faction_war_system = getattr(ctx, 'faction_war', None) or getattr(ctx, 'faction_war_system', None)
            player = getattr(ctx, 'player', None)
            
            if faction_war_system and player:
                # 恶霸发布悬赏
                success, bounty_id = faction_war_system.post_bounty(
                    issuer_org='heifeng_zhai',  # 恶霸所属势力
                    target_id=getattr(player, 'id', 9999),
                    reward=50,
                    reason='得罪王老虎',
                    is_player_target=True
                )
                
                if success:
                    self.bully_bounty_id = bounty_id
                    print(f"[Quest] 恶霸悬赏ID: {bounty_id}")
                
                # 浮动文字提示
                if hasattr(ctx, 'ft_manager') and ctx.ft_manager:
                    ctx.ft_manager.add_text("[!] 王老虎悬赏你！",
                                           player.rect.centerx, player.rect.top - 30, (255, 50, 50))
        
        # 设置标记
        self.set_flag('bully_bounty_active', True)
    
    def _action_reward_bully_victory(self, ctx=None):
        """击败恶霸的奖励"""
        print("[Quest] Action: REWARD_BULLY_VICTORY - 发放击败恶霸奖励")
        if ctx:
            player = getattr(ctx, 'player', None)
            ft_manager = getattr(ctx, 'ft_manager', None)
            
            if player:
                # 奖励金钱
                reward_money = 100
                player.money = getattr(player, 'money', 0) + reward_money
                
                # 大幅提升声望
                fame_gain = 30
                player.fame = getattr(player, 'fame', 0) + fame_gain
                
                # 道德值提升
                player.morality = min(100, getattr(player, 'morality', 50) + 10)
                
                # 浮动文字
                if ft_manager:
                    ft_manager.add_text(f"+{reward_money} 铜钱", 
                                       player.rect.centerx, player.rect.top - 30, (255, 215, 0))
                    ft_manager.add_text(f"+{fame_gain} 声望", 
                                       player.rect.centerx, player.rect.top - 50, (255, 215, 0))
                    ft_manager.add_text("惩恶扬善！", 
                                       player.rect.centerx, player.rect.top - 70, (100, 255, 100))
        
        # 清除恶霸悬赏标记
        self.set_flag('bully_bounty_active', False)
        self.set_flag('bully_defeated', True)
    
    def _action_player_attack_popi(self, ctx=None):
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
        
        # 获取第一个泼皮（主说话者）作为攻击目标
        target_popi = popi_list[0] if popi_list else None
        if not target_popi:
            return
        
        # 暂停对话，等待攻击完成
        if story_ui:
            story_ui.waiting_for_action = True
            print("[Quest] 对话已暂停，等待玩家攻击完成")
        
        # 创建攻击回调函数
        def on_attack_complete():
            """攻击完成后的回调"""
            print("[Quest] 剧情攻击完成，恢复对话")
            if story_ui:
                story_ui.waiting_for_action = False
        
        # 使用原子动作队列：移动到泼皮 -> 执行攻击
        from src.atomic_actions import MoveToPosition
        import math
        
        # ═══════════════════════════════════════════════════════════════
        # 【智能位置计算】改进版 - 优先从当前位置攻击
        # ═══════════════════════════════════════════════════════════════
        MIN_SAFE_DIST = 50  # 与任何演员的最小安全距离
        ATTACK_RANGE = 100  # 攻击范围（需要在这个距离内才能攻击）
        
        # 玩家当前位置
        player_cx, player_cy = player.rect.centerx, player.rect.centery
        target_cx, target_cy = target_popi.rect.centerx, target_popi.rect.centery
        
        # 收集所有事件演员的位置（除了攻击目标本身）
        other_actor_positions = []
        yuxishi = getattr(ctx, 'yuxishi_npc', None)
        if yuxishi:
            other_actor_positions.append((yuxishi.rect.centerx, yuxishi.rect.centery, yuxishi.name))
        for popi in popi_list:
            if popi and popi != target_popi:  # 排除攻击目标
                other_actor_positions.append((popi.rect.centerx, popi.rect.centery, popi.name))
        
        print(f"[Quest] ═══════════════════════════════════════")
        print(f"[Quest] 【位置计算调试】")
        print(f"[Quest]   玩家当前位置: ({player_cx}, {player_cy})")
        print(f"[Quest]   攻击目标({target_popi.name}): ({target_cx}, {target_cy})")
        print(f"[Quest]   其他演员: {[(name, x, y) for x, y, name in other_actor_positions]}")
        
        # 计算玩家与目标的当前距离
        current_dist_to_target = math.hypot(player_cx - target_cx, player_cy - target_cy)
        print(f"[Quest]   玩家与目标距离: {current_dist_to_target:.0f}px (攻击范围: {ATTACK_RANGE}px)")
        
        # 检查玩家当前位置是否与其他演员重叠
        current_min_dist_to_others = float('inf')
        for ax, ay, name in other_actor_positions:
            d = math.hypot(player_cx - ax, player_cy - ay)
            current_min_dist_to_others = min(current_min_dist_to_others, d)
            print(f"[Quest]   与{name}的距离: {d:.0f}px")
        
        # 【关键判断】如果玩家已经在攻击范围内，且不与其他演员重叠，就原地攻击
        can_attack_from_here = (current_dist_to_target <= ATTACK_RANGE and 
                                current_min_dist_to_others >= MIN_SAFE_DIST)
        
        if can_attack_from_here:
            print(f"[Quest] [ok] 玩家当前位置可以直接攻击，无需移动！")
            target_x, target_y = player_cx, player_cy
            need_move = False
        else:
            print(f"[Quest] [!] 需要移动到新位置（距离目标过远或与演员重叠）")
            need_move = True
            
            # 在目标泼皮周围寻找一个安全位置
            # 候选方向：优先考虑玩家来的方向（从玩家到目标的反方向）
            # 这样玩家移动距离最短
            
            # 计算玩家相对于目标的方向向量
            dx_player = player_cx - target_cx
            dy_player = player_cy - target_cy
            dist_player = math.hypot(dx_player, dy_player) or 1
            primary_dx = dx_player / dist_player
            primary_dy = dy_player / dist_player
            
            # 候选方向：先从玩家方向开始，再依次检查其他方向
            directions = [
                (primary_dx, primary_dy),  # 玩家方向（最短路径）
                (1, 0),   # 东
                (-1, 0),  # 西  
                (0, 1),   # 南
                (0, -1),  # 北
                (1, 1),   # 东南
                (1, -1),  # 东北
                (-1, 1),  # 西南
                (-1, -1), # 西北
            ]
            
            best_pos = None
            best_score = float('inf')  # 分数越低越好（优先距离玩家近）
            
            for i, (dx, dy) in enumerate(directions):
                # 归一化方向
                length = math.hypot(dx, dy) or 1
                nx, ny = dx / length, dy / length
                
                # 候选位置（距离泼皮 ATTACK_RANGE - 20 像素，确保在攻击范围内）
                check_dist = ATTACK_RANGE - 20
                cand_x = target_cx + nx * check_dist
                cand_y = target_cy + ny * check_dist
                
                # 检查与其他演员的距离
                min_dist_to_others = float('inf')
                closest_actor = "无"
                for ax, ay, name in other_actor_positions:
                    d = math.hypot(cand_x - ax, cand_y - ay)
                    if d < min_dist_to_others:
                        min_dist_to_others = d
                        closest_actor = name
                
                # 检查是否安全
                is_safe = min_dist_to_others >= MIN_SAFE_DIST
                
                # 计算与玩家的距离（作为优先级得分）
                dist_to_player = math.hypot(cand_x - player_cx, cand_y - player_cy)
                
                dir_name = ["玩家方向", "东", "西", "南", "北", "东南", "东北", "西南", "西北"][i] if i < 9 else f"方向{i}"
                print(f"[Quest]   候选[{dir_name}] ({cand_x:.0f},{cand_y:.0f}): "
                      f"离玩家{dist_to_player:.0f}px, 最近演员({closest_actor}){min_dist_to_others:.0f}px, "
                      f"{'[ok]安全' if is_safe else '[!]不安全'}")
                
                # 选择安全且距离玩家最近的位置
                if is_safe and dist_to_player < best_score:
                    best_score = dist_to_player
                    best_pos = (cand_x, cand_y)
            
            # 使用最佳位置
            if best_pos:
                target_x, target_y = best_pos
                print(f"[Quest] → 选择最佳位置: ({target_x:.0f}, {target_y:.0f})")
            else:
                # 兜底：直接向目标方向移动到攻击范围边缘
                target_x = target_cx + primary_dx * (ATTACK_RANGE - 10)
                target_y = target_cy + primary_dy * (ATTACK_RANGE - 10)
                print(f"[Quest] → 使用兜底位置: ({target_x:.0f}, {target_y:.0f})")
        
        print(f"[Quest] ═══════════════════════════════════════")
        
        # 创建攻击动作（使用剧情攻击动作类，实现AtomicAction接口）
        class ScriptedAttackAction:
            """剧情攻击原子动作 - 执行一次攻击并调用回调（兼容ActionQueue接口）"""
            def __init__(self, target, combat_manager, ft_manager, callback):
                self.target = target
                self.combat_manager = combat_manager
                self.ft_manager = ft_manager
                self.callback = callback
                self.finished = False  # ActionQueue标准接口
                self.attack_triggered = False
                self.delay_timer = 0  # 攻击后等待时间(毫秒)
            
            def on_start(self, agent):
                """ActionQueue调用：动作开始时"""
                agent.ai_reason = "挺身而出！"
                print(f"[Quest] ScriptedAttackAction.on_start: {agent.name} -> {self.target.name}")
            
            def on_tick(self, agent, dt_ms) -> bool:
                """ActionQueue调用：每帧更新，返回True继续执行，False表示完成"""
                if self.finished:
                    return False
                
                if not self.attack_triggered:
                    # 执行攻击
                    if self.combat_manager and self.target:
                        # 使用战斗系统的真实攻击（有击退效果）
                        self.combat_manager.apply_melee_attack(agent, self.target, [])
                        print(f"[Quest] 玩家攻击 {self.target.name} (使用战斗系统)")
                    else:
                        # 备用：直接扣血
                        attack_damage = 15
                        old_hp = self.target.hp
                        self.target.hp = max(0, self.target.hp - attack_damage)
                        print(f"[Quest] 玩家攻击 {self.target.name}: HP {old_hp} -> {self.target.hp}")
                        if self.ft_manager:
                            self.ft_manager.add_text(f"-{attack_damage}", 
                                                   self.target.rect.centerx, self.target.rect.top - 20, 
                                                   (255, 50, 50))
                    
                    # 显示"出手相救"浮字
                    if self.ft_manager:
                        self.ft_manager.add_text("出手相救！", 
                                               agent.rect.centerx, agent.rect.top - 30, 
                                               (100, 255, 100))
                    
                    self.attack_triggered = True
                    agent.ai_reason = "一拳打倒！"
                
                # 等待一小段时间让攻击动画完成
                self.delay_timer += dt_ms
                if self.delay_timer > 500:  # 0.5秒
                    self.finished = True
                    return False
                
                return True
            
            def on_end(self, agent):
                """ActionQueue调用：动作结束时"""
                print(f"[Quest] ScriptedAttackAction.on_end: 攻击完成")
                if self.callback:
                    self.callback()
            
            def __repr__(self):
                return "ScriptedAttackAction"
        
        # 创建攻击动作实例
        ft_manager = getattr(ctx, 'ft_manager', None)
        attack_action = ScriptedAttackAction(target_popi, combat_manager, ft_manager, on_attack_complete)
        
        # 加入玩家行动队列：如果需要移动则先移动再攻击，否则直接攻击
        if need_move:
            move_action = MoveToPosition(target_x, target_y, stop_dist=20, reason="冲向泼皮")
            player.action_queue.enqueue(move_action)
            print(f"[Quest] 已安排移动动作: 玩家 -> ({target_x:.0f},{target_y:.0f})")
        
        player.action_queue.enqueue(attack_action)
        player.ai_reason = "挺身而出..."
        
        print(f"[Quest] 已安排剧情攻击：玩家 -> {target_popi.name}" + 
              (f"（移动到({target_x:.0f},{target_y:.0f})后攻击）" if need_move else "（原地攻击）"))
    
    def _action_popi_flee(self, ctx=None):
        """泼皮逃跑 - 剧情演出"""
        print("[Quest] Action: POPI_FLEE - 泼皮开始逃跑")
        if not ctx:
            return
        
        # 获取泼皮 NPC 列表
        popi_list = getattr(ctx, 'popi_npcs', [])
        if not popi_list:
            # 备用方案：从 all_cards 中查找
            popi_list = [c for c in ctx.all_cards if hasattr(c, 'name') and '泼皮' in c.name]
        
        for popi in popi_list:
            if not popi:
                continue
            # 设置逃跑状态
            popi.state = STATE_FLEEING
            popi.ai_reason = "落荒而逃..."
            
            # 设置逃跑目标（向城外方向跑）
            # 泼皮被吓跑后应该往城外逃，而不是进城
            if hasattr(ctx, 'world_map'):
                wm = ctx.world_map
                # 计算逃跑方向：从泼皮当前位置向远离城门的方向逃跑
                # 开局剧情在城东门外，所以泼皮应该往东边（地图右侧）逃跑
                popi_x, popi_y = popi.rect.centerx, popi.rect.centery
                
                # 逃跑目标：向地图边缘方向跑（远离城池）
                # 以泼皮当前位置为基准，向远离城墙的方向延伸 400-600 像素
                city_center_x = wm.city_rect.centerx
                city_center_y = wm.city_rect.centery
                
                # 计算逃跑方向（从城中心指向泼皮，再延伸）
                dx = popi_x - city_center_x
                dy = popi_y - city_center_y
                dist = max(1, (dx**2 + dy**2)**0.5)
                
                # 标准化方向并延伸 500 像素
                flee_dist = 500
                flee_x = popi_x + int(dx / dist * flee_dist) + random.randint(-50, 50)
                flee_y = popi_y + int(dy / dist * flee_dist) + random.randint(-50, 50)
                
                # 确保逃跑目标在地图边界内
                flee_x = max(50, min(flee_x, wm.w - 50))
                flee_y = max(50, min(flee_y, wm.h - 50))
                
                popi.set_movement_target(flee_x, flee_y, reason="逃跑")
                popi.move_speed = 720.0  # 逃跑速度是正常速度(80)的9倍，狼狈而逃
            
            # 【关键修复】将泼皮加入剧情演员列表，确保他们在剧情期间能移动
            popi_id = getattr(popi, 'id', None)
            if popi_id is not None and hasattr(ctx, 'story_ui'):
                ctx.story_ui.story_actor_ids.add(popi_id)
                print(f"[Quest] 已将 {popi.name}(ID:{popi_id}) 加入剧情演员列表")
            
            print(f"[Quest] {popi.name} 开始逃跑 -> 目标({flee_x}, {flee_y})")
        
        # 浮动文字
        if hasattr(ctx, 'ft_manager') and popi_list:
            popi = popi_list[0]
            ctx.ft_manager.add_text("小子你等着！", popi.rect.centerx, popi.rect.top - 30, (255, 100, 100))
    
    def _action_release_event_npcs(self, ctx=None):
        """释放事件 NPC 恢复正常 AI"""
        print("[Quest] Action: EVENT_NPC_RELEASE - 释放事件NPC")
        if not ctx:
            print("[Quest] ERROR: ctx is None, cannot release NPCs!")
            return
        
        # 释放鱼西施
        yuxishi = getattr(ctx, 'yuxishi_npc', None)
        if yuxishi:
            old_state = yuxishi.state
            yuxishi.state = STATE_IDLE
            yuxishi.ai_reason = "卖鱼中..."
            print(f"[Quest] 释放 {yuxishi.name}: state {old_state} -> {yuxishi.state}")
        else:
            print("[Quest] WARNING: yuxishi_npc not found in ctx")
        
        # 释放泼皮们（如果他们还在逃跑，不干扰；如果还在 EVENT 状态，释放为 IDLE）
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
        
        # 【新增】遍历 all_cards 释放所有处于 STATE_EVENT 的 NPC
        # 确保任何可能被遗漏的 NPC 都能恢复正常
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
        
        # 【调试】打印开场三人最终状态
        print("=" * 60)
        print("[Quest] === 剧情结束后NPC状态检查 ===")
        if yuxishi:
            print(f"  鱼西施: state={yuxishi.state}, in_combat={getattr(yuxishi, 'in_combat', False)}, safety={getattr(yuxishi, 'safety', '?')}, ai_reason={getattr(yuxishi, 'ai_reason', '?')}")
        for i, popi in enumerate(popi_list):
            if popi:
                print(f"  泼皮{i+1}({popi.name}): state={popi.state}, in_combat={getattr(popi, 'in_combat', False)}, safety={getattr(popi, 'safety', '?')}, ai_reason={getattr(popi, 'ai_reason', '?')}")
        print("=" * 60)

    # ═══════════════════════════════════════════════════════════════
    # 【新增】新手引导剧情 Action Handlers
    # ═══════════════════════════════════════════════════════════════
    
    def _action_player_defeated(self, ctx=None):
        """玩家被打倒 - 剧情演出"""
        print("[Quest] Action: PLAYER_DEFEATED - 玩家被泼皮群殴打倒")
        if not ctx:
            return
        
        player = getattr(ctx, 'player', None)
        ft_manager = getattr(ctx, 'ft_manager', None)
        
        if player:
            # 降低玩家HP（但不会死亡）
            player.hp = max(1, player.hp - 40)
            
            # 设置受伤状态
            player.ai_reason = "被打倒了..."
            
            # 浮动文字
            if ft_manager:
                ft_manager.add_text("寡不敌众！", player.rect.centerx, player.rect.top - 30, (255, 50, 50))
                ft_manager.add_text("-40 HP", player.rect.centerx, player.rect.top - 50, (255, 80, 80))
        
        # 设置标记，用于后续剧情判断
        self.set_flag('player_defeated_once', True)
    
    def _action_trigger_hungry(self, ctx=None):
        """触发饥饿状态 - 引导玩家了解生存系统"""
        print("[Quest] Action: TRIGGER_HUNGRY - 触发饥饿引导")
        if not ctx:
            return
        
        player = getattr(ctx, 'player', None)
        ft_manager = getattr(ctx, 'ft_manager', None)
        
        if player:
            # 设置较高的饥饿值（不是0，但需要吃东西）
            player.hunger = max(60, getattr(player, 'hunger', 100))
            
            # 显示饥饿提示
            if ft_manager:
                ft_manager.add_text("肚子饿了...", player.rect.centerx, player.rect.top - 30, (255, 200, 100))
        
        # 自动激活下一个任务（饥饿任务）
        self.quest_status = QS_ACTIVE
        print("[Quest] 饥饿任务已激活")
    
    def _action_recruit_zhangsan(self, ctx=None):
        """招募张三为门客"""
        print("[Quest] Action: RECRUIT_ZHANGSAN - 招募猎户张三")
        if not ctx:
            return
        
        player = getattr(ctx, 'player', None)
        ft_manager = getattr(ctx, 'ft_manager', None)
        all_cards = getattr(ctx, 'all_cards', [])
        
        # 寻找张三NPC
        zhangsan = None
        for card in all_cards:
            if hasattr(card, 'name') and card.name == '猎户张三':
                zhangsan = card
                break
        
        if player and zhangsan:
            # 扣除招募费用
            recruit_cost = 50
            if player.money >= recruit_cost:
                player.money -= recruit_cost
                
                # 设置张三为门客/跟随者
                zhangsan.is_follower = True
                zhangsan.follow_target = player
                zhangsan.ai_mode = "FOLLOW"  # 【关键】设置AI模式为跟随
                zhangsan.state = STATE_IDLE  # 状态由AI系统控制
                zhangsan.ai_reason = "跟随主人"
                
                # 添加到玩家的门客列表
                if not hasattr(player, 'followers'):
                    player.followers = []
                player.followers.append(zhangsan)
                
                # 浮动文字
                if ft_manager:
                    ft_manager.add_text(f"-{recruit_cost} 铜钱", player.rect.centerx, player.rect.top - 30, (255, 215, 0))
                    ft_manager.add_text("张三加入！", zhangsan.rect.centerx, zhangsan.rect.top - 30, (100, 255, 100))
                
                print(f"[Quest] 张三已成为门客")
            else:
                print(f"[Quest] 招募失败：金钱不足 ({player.money} < {recruit_cost})")
                if ft_manager:
                    ft_manager.add_text("金钱不足！", player.rect.centerx, player.rect.top - 30, (255, 50, 50))
        
        # 设置招募标记
        self.set_flag('recruited_猎户张三', True)
    
    def _action_spawn_bully(self, ctx=None):
        """生成泼皮供反击 - 将泼皮牛二移动到贫民窟附近等待战斗"""
        print("[Quest] Action: SPAWN_BULLY_FOR_REVENGE - 生成泼皮供反击")
        if not ctx:
            return
        
        world_map = getattr(ctx, 'world_map', None)
        all_cards = getattr(ctx, 'all_cards', [])
        ft_manager = getattr(ctx, 'ft_manager', None)
        
        if world_map and all_cards:
            # 在贫民窟附近设置泼皮位置
            slum = world_map.slum_rect
            spawn_x = slum.centerx + random.randint(-50, 50)
            spawn_y = slum.centery + random.randint(-50, 50)
            
            # 找到泼皮牛二和狗蛋（已经在游戏中存在）
            popi_niuer = None
            popi_goudan = None
            for card in all_cards:
                name = getattr(card, 'name', '')
                if name == '泼皮牛二':
                    popi_niuer = card
                elif name == '泼皮狗蛋':
                    popi_goudan = card
            
            # 移动泼皮到贫民窟附近
            if popi_niuer:
                popi_niuer.set_pos(spawn_x, spawn_y)
                popi_niuer.state = 'IDLE'  # 恢复正常状态，可被战斗
                popi_niuer.ai_reason = "等着那小子送死..."
                print(f"[Quest] 泼皮牛二已移动到 ({spawn_x}, {spawn_y})")
                
                if ft_manager:
                    ft_manager.add_text("泼皮牛二出现在贫民窟！", spawn_x, spawn_y - 30, (255, 150, 50))
            
            if popi_goudan:
                # 狗蛋站在牛二旁边
                popi_goudan.set_pos(spawn_x + 60, spawn_y + 20)
                popi_goudan.state = 'IDLE'
                popi_goudan.ai_reason = "跟着牛二哥"
                print(f"[Quest] 泼皮狗蛋已移动到牛二旁边")
            
            # 设置标记表示可以开始复仇战斗
            self.set_flag('revenge_bully_spawned', True)
            print(f"[Quest] 泼皮已就位，等待玩家复仇")
    
    def _action_start_combat_bully(self, ctx=None):
        """开始与泼皮的战斗"""
        print("[Quest] Action: START_COMBAT_BULLY - 开始与泼皮战斗")
        if not ctx:
            return
        
        player = getattr(ctx, 'player', None)
        all_cards = getattr(ctx, 'all_cards', [])
        combat_manager = getattr(ctx, 'combat_manager', None)
        
        # 寻找泼皮牛二
        target_bully = None
        for card in all_cards:
            if hasattr(card, 'name') and '泼皮牛二' in card.name:
                target_bully = card
                break
        
        if player and target_bully and combat_manager:
            # 设置泼皮为敌对状态
            target_bully.attitude = -100  # 敌对
            target_bully.state = STATE_COMBAT
            target_bully.ai_reason = "与玩家战斗"
            
            # 设置玩家进入战斗
            player.in_combat = True
            player.combat_target = target_bully
            
            print(f"[Quest] 战斗开始：玩家 vs {target_bully.name}")
        
        # 监听战斗结果（通过flag）
        self.set_flag('combat_with_bully_started', True)
    
    def _action_complete_tutorial(self, ctx=None):
        """完成新手教程"""
        print("[Quest] Action: COMPLETE_TUTORIAL - 新手教程完成")
        if not ctx:
            return
        
        player = getattr(ctx, 'player', None)
        ft_manager = getattr(ctx, 'ft_manager', None)
        
        if player:
            # 给予教程完成奖励
            bonus_money = 50
            bonus_fame = 20
            player.money += bonus_money
            player.fame = getattr(player, 'fame', 0) + bonus_fame
            
            # 浮动文字
            if ft_manager:
                ft_manager.add_text("教程完成！", player.rect.centerx, player.rect.top - 30, (255, 215, 0))
                ft_manager.add_text(f"+{bonus_money} 铜钱", player.rect.centerx, player.rect.top - 50, (255, 215, 0))
                ft_manager.add_text(f"+{bonus_fame} 声望", player.rect.centerx, player.rect.top - 70, (255, 215, 0))
        
        # 设置教程完成标记
        self.set_flag('tutorial_completed', True)
        self.set_flag('guidance_visible', True)  # 确保引导面板可见
    
    def _action_set_fame_req(self, ctx=None, fame_req='20'):
        """设置声望要求 - 用于势力加入任务
        
        Args:
            ctx: 游戏上下文
            fame_req: 声望要求值（字符串格式，如 '20'）
        """
        print(f"[Quest] Action: SET_FAME_REQ - 设置声望要求: {fame_req}")
        
        # 尝试转换为整数
        try:
            fame_value = int(fame_req)
        except (ValueError, TypeError):
            print(f"[Quest] 警告：无法解析声望值 {fame_req}，使用默认值 20")
            fame_value = 20
        
        # 检查玩家声望
        player = getattr(ctx, 'player', None) if ctx else None
        if player:
            current_fame = getattr(player, 'fame', 0)
            print(f"[Quest] 玩家当前声望: {current_fame}, 要求: {fame_value}")
            
            # 设置声望要求标记
            current_quest = self.get_current_quest()
            if current_quest:
                flag_name = f'fame_req_{current_quest.id}'
                self.set_flag(flag_name, fame_value)
                print(f"[Quest] 声望要求标记已设置: {flag_name} = {fame_value}")
            
            # 如果声望不足，设置一个标记用于对话分支判断
            if current_fame < fame_value:
                self.set_flag('fame_insufficient', True)
                print(f"[Quest] 声望不足，需要 {fame_value - current_fame} 点声望")
            else:
                self.set_flag('fame_insufficient', False)
                print(f"[Quest] 声望满足要求")
    
    def _action_join_org(self, ctx=None, org_id='kaifeng_fu'):
        """加入势力 - 让玩家加入指定组织
        
        Args:
            ctx: 游戏上下文
            org_id: 组织ID（如 'kaifeng_fu', 'tianshui_alley' 等）
        """
        print(f"[Quest] Action: JOIN_ORG - 加入组织: {org_id}")
        if not ctx:
            return
        
        player = getattr(ctx, 'player', None)
        org_economy = getattr(ctx, 'org_economy', None)
        ft_manager = getattr(ctx, 'ft_manager', None)
        
        if not player:
            print("[Quest] 错误：找不到玩家对象")
            return
        
        # 设置玩家组织
        player.org_id = org_id
        player.org_role = 'MEMBER'
        player.org_rank = 1  # 门徒
        
        # 更新组织成员列表
        if org_economy:
            if org_id not in org_economy.org_members:
                org_economy.org_members[org_id] = []
            org_economy.org_members[org_id].append(player.id)
        
        # 浮动文字提示
        if ft_manager:
            from src.data.character_seeds import ORGANIZATIONS
            org_name = ORGANIZATIONS.get(org_id, {}).get('name', org_id)
            ft_manager.add_text(f"加入 {org_name}！", player.rect.centerx, player.rect.top - 30, (100, 200, 255))
        
        print(f"[Quest] 玩家已加入组织：{org_id}")
    
    # ═══════════════════════════════════════════════════════════════
    # 【新增】优化方案新增的 action handlers
    # ═══════════════════════════════════════════════════════════════
    
    def _action_set_flag(self, ctx=None, flag_name='flag', flag_value=True):
        """设置标记
        
        Args:
            ctx: 游戏上下文
            flag_name: 标记名称
            flag_value: 标记值
        """
        print(f"[Quest] Action: SET_FLAG - 设置标记: {flag_name} = {flag_value}")
        self.set_flag(flag_name, flag_value)
    
    def _action_complete_any_task(self, ctx=None, task_count='3'):
        """完成任意任务计数器
        
        Args:
            ctx: 游戏上下文
            task_count: 需要完成的任务数量
        """
        print(f"[Quest] Action: COMPLETE_ANY_TASK - 完成任意任务: {task_count}")
        # 这个 action 只是设置一个标记，实际计数在任务完成时检查
        try:
            count = int(task_count)
        except (ValueError, TypeError):
            count = 3
        
        # 设置任务完成计数器
        current_quest = self.get_current_quest()
        if current_quest:
            flag_name = f'task_count_{current_quest.id}'
            current_count = self.get_flag(flag_name, 0)
            self.set_flag(flag_name, current_count + 1)
            print(f"[Quest] 任务完成计数: {flag_name} = {current_count + 1}/{count}")
            
            # 检查是否达到目标
            if current_count + 1 >= count:
                print(f"[Quest] 已完成足够任务，可以推进任务")
                return True
        return False
    
    def _action_org_task(self, ctx=None, task_count='1'):
        """完成组织任务计数器
        
        Args:
            ctx: 游戏上下文
            task_count: 需要完成的组织任务数量
        """
        print(f"[Quest] Action: ORG_TASK - 完成组织任务: {task_count}")
        # 这个 action 只是设置一个标记，实际计数在组织任务完成时检查
        try:
            count = int(task_count)
        except (ValueError, TypeError):
            count = 1
        
        # 设置组织任务完成计数器
        current_quest = self.get_current_quest()
        if current_quest:
            flag_name = f'org_task_count_{current_quest.id}'
            current_count = self.get_flag(flag_name, 0)
            self.set_flag(flag_name, current_count + 1)
            print(f"[Quest] 组织任务完成计数: {flag_name} = {current_count + 1}/{count}")
            
            # 检查是否达到目标
            if current_count + 1 >= count:
                print(f"[Quest] 已完成足够组织任务，可以推进任务")
                return True
        return False
    
    def _action_org_rank(self, ctx=None, target_rank='5'):
        """检查组织等级
        
        Args:
            ctx: 游戏上下文
            target_rank: 目标等级
        """
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
    
    def _action_war_participate(self, ctx=None, war_count='1'):
        """参与势力战争计数器
        
        Args:
            ctx: 游戏上下文
            war_count: 需要参与的战争数量
        """
        print(f"[Quest] Action: WAR_PARTICIPATE - 参与势力战争: {war_count}")
        # 这个 action 只是设置一个标记，实际计数在参与战争时检查
        try:
            count = int(war_count)
        except (ValueError, TypeError):
            count = 1
        
        # 设置战争参与计数器
        current_quest = self.get_current_quest()
        if current_quest:
            flag_name = f'war_count_{current_quest.id}'
            current_count = self.get_flag(flag_name, 0)
            self.set_flag(flag_name, current_count + 1)
            print(f"[Quest] 战争参与计数: {flag_name} = {current_count + 1}/{count}")
            
            # 检查是否达到目标
            if current_count + 1 >= count:
                print(f"[Quest] 已参与足够战争，可以推进任务")
                return True
        return False
    
    def _action_occupy_building(self, ctx=None, building_count='1'):
        """占领建筑计数器
        
        Args:
            ctx: 游戏上下文
            building_count: 需要占领的建筑数量
        """
        print(f"[Quest] Action: OCCUPY_BUILDING - 占领建筑: {building_count}")
        # 这个 action 只是设置一个标记，实际计数在占领建筑时检查
        try:
            count = int(building_count)
        except (ValueError, TypeError):
            count = 1
        
        # 设置建筑占领计数器
        current_quest = self.get_current_quest()
        if current_quest:
            flag_name = f'occupy_count_{current_quest.id}'
            current_count = self.get_flag(flag_name, 0)
            self.set_flag(flag_name, current_count + 1)
            print(f"[Quest] 建筑占领计数: {flag_name} = {current_count + 1}/{count}")
            
            # 检查是否达到目标
            if current_count + 1 >= count:
                print(f"[Quest] 已占领足够建筑，可以推进任务")
                return True
        return False
    
    def _action_control_building(self, ctx=None, building_count='10'):
        """检查控制的建筑数量
        
        Args:
            ctx: 游戏上下文
            building_count: 需要控制的建筑数量
        """
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
        
        # 获取玩家控制的建筑数量
        controlled_count = 0
        if faction_war_system:
            player_org_id = getattr(player, 'org_id', None)
            if player_org_id:
                # 计算玩家势力控制的建筑数量
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
    
    def _action_investigate(self, ctx=None, target_name=''):
        """收集情报
        
        Args:
            ctx: 游戏上下文
            target_name: 目标名称
        """
        print(f"[Quest] Action: INVESTIGATE - 收集情报: {target_name}")
        # 这个 action 只是设置一个标记，表示已经收集了情报
        current_quest = self.get_current_quest()
        if current_quest:
            flag_name = f'investigated_{current_quest.id}'
            self.set_flag(flag_name, True)
            print(f"[Quest] 情报收集标记已设置: {flag_name}")
        return True
    
    def _action_trigger_revenge_ambush(self, ctx=None):
        """
        触发报复伏击事件
        当玩家赚到第一笔钱后，泼皮伏击玩家
        这个动作只是设置一个标记，Q_REVENGE 任务的对话会处理后续
        """
        print("[Quest] Action: TRIGGER_REVENGE_AMBUSH - 触发报复伏击")
        
        # 设置标记表示伏击即将发生
        self.set_flag('revenge_ambush_triggered', True)
        
        # 这里不需要做太多事情，因为 Q_REVENGE 任务的对话会自动播放
        # 在 Q_FIRST_MONEY_END 对话中已经通过 TRIGGER_REVENGE_AMBUSH 触发
        # 对话会通过 next 字段自动跳转到 Q_REVENGE
        
        # 可选：生成伏击的泼皮（如果需要在世界中实际生成）
        if ctx:
            all_cards = getattr(ctx, 'all_cards', [])
            player = getattr(ctx, 'player', None)
            
            # 查找泼皮牛二，确保他在场
            popi = None
            for card in all_cards:
                if hasattr(card, 'name') and card.name == '泼皮牛二':
                    popi = card
                    break
            
            if popi and player:
                # 将泼皮移动到玩家附近（模拟伏击）
                popi.rect.centerx = player.rect.centerx + 100
                popi.rect.centery = player.rect.centery
                popi.state = STATE_EVENT  # 锁定状态参与事件
                print(f"[Quest] 泼皮牛二已移动到玩家附近准备伏击")
    
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

    # ═══════════════════════════════════════════════════════════════
    # 【轻量演出系统】Action实现
    # ═══════════════════════════════════════════════════════════════
    
    def _action_fade_to_black(self, ctx=None, duration=1.0):
        """黑屏渐入效果 - 通过设置标记让渲染系统处理"""
        print(f"[Quest] Action: FADE_TO_BLACK - 黑屏渐入 ({duration}s)")
        self.set_flag('screen_fade', {'type': 'to_black', 'duration': float(duration), 'start_time': None})
    
    def _action_fade_from_black(self, ctx=None, duration=1.0):
        """黑屏渐出效果"""
        print(f"[Quest] Action: FADE_FROM_BLACK - 黑屏渐出 ({duration}s)")
        self.set_flag('screen_fade', {'type': 'from_black', 'duration': float(duration), 'start_time': None})
    
    def _action_flash_white(self, ctx=None, duration=0.3):
        """白屏闪烁效果 - 被打击时的视觉反馈"""
        print(f"[Quest] Action: FLASH_WHITE - 白屏闪烁 ({duration}s)")
        self.set_flag('screen_fade', {'type': 'flash_white', 'duration': float(duration), 'start_time': None})
    
    def _action_advance_time(self, ctx=None, hours=8):
        """时间推进 - 模拟时间流逝"""
        print(f"[Quest] Action: ADVANCE_TIME - 时间推进 {hours} 小时")
        if ctx:
            em = getattr(ctx, 'event_manager', None)
            if em:
                ticks_per_hour = em.ticks_per_day // 24
                em.current_day_ticks += ticks_per_hour * int(hours)
                em.game_tick += ticks_per_hour * int(hours)
                print(f"[Quest] 时间已推进 {hours} 小时")
    
    def _action_teleport_player(self, ctx=None, location=''):
        """传送玩家到指定位置"""
        print(f"[Quest] Action: TELEPORT_PLAYER - 传送到 {location}")
        if ctx:
            player = getattr(ctx, 'player', None)
            all_cards = getattr(ctx, 'all_cards', [])
            
            # 查找目标位置（可以是建筑名、地点名等）
            target_pos = None
            for card in all_cards:
                # 按名称查找建筑/地点
                card_name = getattr(card, 'name', '')
                if location in card_name:
                    target_pos = (card.rect.centerx, card.rect.centery + 50)
                    break
            
            if player and target_pos:
                player.rect.centerx = target_pos[0]
                player.rect.centery = target_pos[1]
                print(f"[Quest] 玩家已传送到 {location} ({target_pos})")
    
    def _action_set_hunger(self, ctx=None, value=50):
        """设置玩家饥饿值"""
        print(f"[Quest] Action: SET_HUNGER - 设置饥饿值为 {value}")
        if ctx:
            player = getattr(ctx, 'player', None)
            if player and hasattr(player, 'hunger'):
                player.hunger = int(value)
                print(f"[Quest] 玩家饥饿值已设置为 {value}")
    
    def _action_set_hp(self, ctx=None, value=10):
        """设置玩家生命值"""
        print(f"[Quest] Action: SET_HP - 设置HP为 {value}")
        if ctx:
            player = getattr(ctx, 'player', None)
            if player and hasattr(player, 'hp'):
                player.hp = int(value)
                print(f"[Quest] 玩家HP已设置为 {value}")
    
    def _action_set_stamina(self, ctx=None, value=50):
        """设置玩家体力值"""
        print(f"[Quest] Action: SET_STAMINA - 设置体力为 {value}")
        if ctx:
            player = getattr(ctx, 'player', None)
            if player and hasattr(player, 'stamina'):
                player.stamina = int(value)
                print(f"[Quest] 玩家体力已设置为 {value}")
    
    def _action_spawn_enemy_near(self, ctx=None, enemy_names=''):
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
                # 查找已存在的NPC并移动到玩家附近
                for card in all_cards:
                    if hasattr(card, 'name') and card.name == name:
                        card.rect.centerx = player.rect.centerx + offset * (i + 1)
                        card.rect.centery = player.rect.centery
                        card.state = STATE_EVENT
                        print(f"[Quest] {name} 已移动到玩家附近")
                        break
    
    def _action_despawn_npc(self, ctx=None, npc_name=''):
        """移除指定NPC（设置为不可见/远离玩家）"""
        print(f"[Quest] Action: DESPAWN_NPC - 移除NPC: {npc_name}")
        if ctx:
            all_cards = getattr(ctx, 'all_cards', [])
            for card in all_cards:
                if hasattr(card, 'name') and card.name == npc_name:
                    # 移动到地图边缘
                    card.rect.centerx = -1000
                    card.rect.centery = -1000
                    print(f"[Quest] {npc_name} 已移除")
                    break
    
    def _action_knockout_player(self, ctx=None):
        """玩家昏倒效果 - 设置低HP并触发视觉效果"""
        print("[Quest] Action: KNOCKOUT - 玩家昏倒")
        if ctx:
            player = getattr(ctx, 'player', None)
            if player:
                # 设置为濒死状态
                if hasattr(player, 'hp'):
                    player.hp = 1
                if hasattr(player, 'stamina'):
                    player.stamina = 0
                # 触发黑屏
                self.set_flag('screen_fade', {'type': 'to_black', 'duration': 2.0, 'start_time': None})
    
    def _action_start_auto_combat(self, ctx=None):
        """自动战斗 - 玩家被动挨打，用于演出被群殴的场景"""
        print("[Quest] Action: START_AUTO_COMBAT - 自动战斗(被动挨打)")
        # 这里主要是视觉效果，实际战斗由 KNOCKOUT 处理
        self.set_flag('screen_fade', {'type': 'flash_white', 'duration': 0.5, 'start_time': None})
        # 可以在这里触发音效等

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