# src/llm/npc_chat_integration.py
"""
NPC聊天系统集成层
将ChatManager、ChatUI、NPC记忆系统与游戏循环连接起来
"""

import pygame
import threading
from queue import Queue
from typing import Optional, Dict, Any, TYPE_CHECKING

from src.utils import log_game_event

if TYPE_CHECKING:
    from src.entities.npc import NPC
    from src.ui.chat_ui import ChatUI


class NPCChatIntegration:
    """
    NPC聊天系统集成管理器
    
    职责：
    1. 管理当前对话的NPC
    2. 连接ChatUI和ChatManager
    3. 处理AI响应的游戏效果（好感度变化等）
    4. 管理NPC记忆的持久化
    
    注意：LLM回调在后台线程执行，使用消息队列确保UI更新在主线程
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        # 避免重复初始化
        if NPCChatIntegration._instance is not None:
            return
            
        self._chat_ui: Optional['ChatUI'] = None
        self._current_npc: Optional['NPC'] = None
        self._player_id: int = 0  # 玩家ID，用于记忆中标识
        
        # 记忆系统缓存 {npc_id: NPCMemorySystem}
        self._memory_cache: Dict[int, Any] = {}
        
        # ChatManager引用
        self._chat_manager = None
        
        # API是否可用
        self._api_available = False
        
        # 【关键】线程安全的消息队列，用于从后台线程传递消息到主线程
        self._pending_messages: Queue = Queue()
        
        print("[NPCChatIntegration] 初始化完成")
    
    def setup(self, chat_ui: 'ChatUI', player_id: int = 0):
        """
        设置聊天UI和玩家ID
        
        Args:
            chat_ui: ChatUI实例
            player_id: 玩家的NPC ID
        """
        self._chat_ui = chat_ui
        self._player_id = player_id
        
        # 设置UI回调
        chat_ui.set_on_send(self._on_player_send)
        chat_ui.set_on_close(self._on_chat_close)
        
        # 检查API是否可用
        self._check_api_availability()
        
        print(f"[NPCChatIntegration] 设置完成，玩家ID: {player_id}")
    
    def _check_api_availability(self):
        """检查LLM API是否可用"""
        try:
            from src.llm.config import LLMConfig
            config = LLMConfig.get_instance()
            self._api_available = config.is_configured()
            
            if self._api_available:
                # 初始化ChatManager
                from src.llm.chat_manager import ChatManager
                self._chat_manager = ChatManager.get_instance()
        except Exception as e:
            print(f"[NPCChatIntegration] API检查失败: {e}")
            self._api_available = False
    
    def start_chat(self, npc: 'NPC', ctx=None) -> bool:
        """
        开始与NPC对话
        
        Args:
            npc: 要对话的NPC
            ctx: 游戏上下文（可选，用于检查 StoryUI 状态）
            
        Returns:
            bool: 是否成功开始对话
        """
        print(f"[NPCChatIntegration] start_chat 被调用，NPC: {npc.name}")
        
        if not self._chat_ui:
            print("[NPCChatIntegration] ChatUI未初始化")
            return False
        
        # 【新增】检查 StoryUI 是否正在播放对话
        # 这意味着NPC正在说任务相关的台词，需要等待完成
        self._last_fail_reason = None  # 清除上次失败原因
        
        if ctx:
            story_ui = getattr(ctx, 'story_ui', None)
            if story_ui and story_ui.is_active:
                print(f"[NPCChatIntegration] StoryUI正在播放，无法开始闲聊")
                self._last_fail_reason = "STORY_ACTIVE"
                return False
        
        # 检查NPC是否可对话
        if not self._can_chat_with(npc):
            print(f"[NPCChatIntegration] NPC {npc.name} 当前状态不允许对话")
            self._last_fail_reason = "NPC_UNAVAILABLE"
            return False
        
        self._current_npc = npc
        self._current_ctx = ctx  # 保存游戏上下文，供后续使用
        
        # 获取或创建NPC的记忆系统
        memory_system = self._get_or_create_memory(npc)
        
        # 显示聊天UI
        self._chat_ui.show(npc.name)
        
        # 添加NPC的开场白
        greeting = self._generate_greeting(npc)
        self._chat_ui.add_message("npc", greeting, "neutral")
        
        # 设置快捷回复
        quick_replies = self._generate_quick_replies(npc)
        self._chat_ui.set_quick_replies(quick_replies)
        
        print(f"[NPCChatIntegration] 开始与 {npc.name} 对话")
        return True
    
    def _can_chat_with(self, npc: 'NPC') -> bool:
        """检查NPC是否可以对话"""
        from src.definitions import SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED
        
        # 死亡/流放/重伤不能对话
        if npc.safety in [SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED]:
            print(f"[NPCChatIntegration] NPC {npc.name} 无法对话：安全状态={npc.safety}")
            return False
        
        # 战斗中不能对话
        from src.definitions import STATE_COMBAT
        if npc.state == STATE_COMBAT:
            print(f"[NPCChatIntegration] NPC {npc.name} 无法对话：正在战斗")
            return False
        
        # 【修复】允许EVENT状态的NPC对话（任务NPC也可以闲聊）
        # STATE_EVENT 不应该阻止闲聊
        
        print(f"[NPCChatIntegration] NPC {npc.name} 可以对话")
        return True
    
    def _get_or_create_memory(self, npc: 'NPC'):
        """获取或创建NPC的记忆系统"""
        npc_id = npc.id
        
        if npc_id not in self._memory_cache:
            try:
                from src.llm.npc_memory import NPCMemorySystem
                self._memory_cache[npc_id] = NPCMemorySystem(npc_id, npc.name)
            except Exception as e:
                print(f"[NPCChatIntegration] 创建记忆系统失败: {e}")
                return None
        
        return self._memory_cache[npc_id]
    
    def _generate_greeting(self, npc: 'NPC') -> str:
        """
        生成NPC的开场白（基于任务上下文、记忆和好感度）
        
        【调试信息】会打印开场白生成过程的详细日志
        """
        log_game_event("[NPCChatIntegration] ===== 生成开场白 =====")
        log_game_event(f"[NPCChatIntegration] NPC: {npc.name}, 好感度: {npc.affinity_to_player}, 认识玩家: {npc.knows_player}")
        
        affinity = npc.affinity_to_player
        knows = npc.knows_player
        
        # 【优先】检查是否有与该NPC相关的活跃任务
        print(f"[NPCChatIntegration] 检查任务相关开场白...")
        task_greeting = self._get_task_based_greeting(npc)
        if task_greeting:
            log_game_event(f"[NPCChatIntegration] [ok] 使用任务相关开场白: {task_greeting[:30]}...")
            return task_greeting
        else:
            print(f"[NPCChatIntegration] [!] 无任务相关开场白")
        
        # 【次优先】检查是否有最近的重要互动记忆
        print(f"[NPCChatIntegration] 检查记忆相关开场白...")
        memory_greeting = self._get_memory_based_greeting(npc)
        if memory_greeting:
            log_game_event(f"[NPCChatIntegration] [ok] 使用记忆相关开场白: {memory_greeting[:30]}...")
            return memory_greeting
        else:
            print(f"[NPCChatIntegration] [!] 无记忆相关开场白")
        
        # 【默认】根据势力类型和好感度生成不同的开场白
        print(f"[NPCChatIntegration] 使用默认模板开场白")
        power_type = getattr(npc, 'power_type', '民')
        
        if not knows:
            # 第一次见面
            greetings = {
                '士': "哦？你是何人？有何公干？",
                '农': "客官面生，是外乡来的么？",
                '工': "找我有事？我正忙着呢。",
                '商': "客官请看，小店货真价实！",
                '学': "施主有何指教？",
                '兵': "站住！报上名来！",
                '游': "阁下是哪条道上的朋友？",
                '匪': "小子，识相的就把钱袋留下！",
                '民': "这位公子，有何贵干？",
            }
        elif affinity >= 50:
            # 关系很好
            greetings = {
                '士': "哈哈，贤弟来了，快请坐！",
                '农': "是你呀！快进来喝杯茶！",
                '工': "老伙计！好久不见！",
                '商': "贵客临门，蓬荜生辉！",
                '学': "善哉善哉，施主别来无恙？",
                '兵': "兄弟！来得正好！",
                '游': "好兄弟！什么风把你吹来了？",
                '匪': "哥们！最近可有好买卖？",
                '民': "朋友来了！快请坐！",
            }
        elif affinity >= 0:
            # 关系普通
            greetings = {
                '士': "哦，是你。有何事？",
                '农': "又来了？有啥事儿？",
                '工': "你来了，找我做什么？",
                '商': "哟，老主顾来了。",
                '学': "施主安好。",
                '兵': "你来做什么？",
                '游': "又见面了。",
                '匪': "你又来干嘛？",
                '民': "嗯？找我有事？",
            }
        else:
            # 关系差
            greetings = {
                '士': "哼，你来做什么？",
                '农': "你怎么又来了？",
                '工': "你最好有正事。",
                '商': "……有事快说。",
                '学': "阿弥陀佛……施主请便。",
                '兵': "看到你就烦！",
                '游': "你最好给我个不打你的理由。",
                '匪': "你是来找死的吗？",
                '民': "你走吧，我不想见你。",
            }
        
        result = greetings.get(power_type, "你好。")
        log_game_event(f"[NPCChatIntegration] 默认开场白: {result}")
        return result
    
    def _get_task_based_greeting(self, npc: 'NPC') -> Optional[str]:
        """
        检查是否有与该NPC相关的活跃任务，生成任务相关开场白
        例如：鱼西施刚给玩家发布了捕鱼任务，再次对话时应该提及任务
        """
        try:
            # 尝试获取任务管理器
            from src.task import QuestManager, get_npc_name_by_id
            quest_mgr = QuestManager.get_instance()
            
            if not quest_mgr:
                print(f"[NPCChatIntegration] 任务开场白：QuestManager.get_instance() 返回 None")
                return None
            
            # 检查当前活跃任务
            active_quest = quest_mgr.get_active_quest()
            if not active_quest:
                print(f"[NPCChatIntegration] 任务开场白：无活跃任务")
                return None
            
            # 获取任务基本信息
            quest_title = getattr(active_quest, 'title', '未知任务')
            quest_desc = getattr(active_quest, 'desc', '')
            quest_target = getattr(active_quest, 'target', '')  # 任务目标描述
            submit_npc = getattr(active_quest, 'submit_npc', '')  # 提交任务的NPC ID或名称
            quest_status = quest_mgr.quest_status  # 0=可接取, 1=进行中, 2=可提交
            
            print(f"[NPCChatIntegration] 任务开场白检查：")
            print(f"  - 任务: {quest_title}")
            print(f"  - submit_npc: {submit_npc}")
            print(f"  - NPC ID: {npc.id}, NPC名字: {npc.name}")
            print(f"  - 任务状态: {quest_status}")
            
            # 检查任务发布者/提交者是否是这个NPC
            # submit_npc 可能是 ID（如 '8002'）或名称（如 '鱼西施'）
            npc_id_str = str(npc.id) if npc.id else ""
            is_submit_npc = False
            
            if submit_npc and submit_npc != '9000':
                # 尝试通过 ID 匹配
                if submit_npc == npc_id_str:
                    is_submit_npc = True
                # 尝试通过名称匹配
                elif submit_npc == npc.name:
                    is_submit_npc = True
                # 尝试将 submit_npc 作为 ID 解析为名称后匹配
                else:
                    submit_npc_name = get_npc_name_by_id(submit_npc)
                    if submit_npc_name == npc.name:
                        is_submit_npc = True
            
            print(f"  - 是否为任务NPC: {is_submit_npc}")
            
            if is_submit_npc:
                # 这个NPC是任务发布者/提交者
                # 根据任务状态生成不同的开场白
                if quest_status == 2:  # 可提交
                    return f"哦？你回来了！{quest_title}完成得怎么样了？让我看看..."
                elif quest_status == 1:  # 进行中
                    return f"你来了！{quest_title}进展如何？还需要什么帮助吗？"
                else:  # 可接取或其他
                    return f"你来了！{quest_title}的事，记得要上心啊！"
            
            # 检查任务目标中是否包含这个NPC的名字
            if quest_target and npc.name and npc.name in quest_target:
                print(f"  - NPC在任务目标中被提及")
                return f"你是来找我的吧？关于{quest_title}的事...我知道你在调查。"
        
        except Exception as e:
            print(f"[NPCChatIntegration] 获取任务开场白失败: {e}")
            import traceback
            traceback.print_exc()
        
        return None
    
    def _get_memory_based_greeting(self, npc: 'NPC') -> Optional[str]:
        """
        基于NPC记忆生成开场白
        例如：上次帮过NPC忙，这次见面会提及
        """
        try:
            # 获取NPC的记忆系统
            memory = self._get_or_create_memory(npc)
            if not memory:
                return None
            
            # 获取最近与玩家相关的重要记忆
            recent_memories = memory.get_recent_memories(limit=5) if hasattr(memory, 'get_recent_memories') else []
            
            for mem in recent_memories:
                # 检查是否是与玩家相关的重要记忆
                importance = getattr(mem, 'importance', 0) or mem.get('importance', 0) if isinstance(mem, dict) else 0
                description = getattr(mem, 'description', '') or mem.get('description', '') if isinstance(mem, dict) else str(mem)
                
                if importance >= 3 and '玩家' in description:
                    # 有重要的玩家相关记忆
                    if '帮助' in description or '救' in description:
                        return f"上次多亏你帮忙，{description[:20]}...我一直记着呢！"
                    elif '打' in description or '攻击' in description or '伤害' in description:
                        return f"你上次...{description[:15]}，我可没忘！"
                    elif '给' in description or '送' in description:
                        return f"上次你给的东西，真是太感谢了！"
        
        except Exception as e:
            print(f"[NPCChatIntegration] 获取记忆开场白失败: {e}")
        
        return None
    
    def _generate_quick_replies(self, npc: 'NPC') -> list:
        """生成快捷回复选项"""
        power_type = getattr(npc, 'power_type', '民')
        job = getattr(npc, 'job', 'NONE')
        
        # 基于NPC类型生成不同的快捷回复
        quick_replies = []
        
        # 通用选项
        quick_replies.append("最近怎么样？")
        
        # 根据职业添加特殊选项
        if job == 'MERCHANT':
            quick_replies.append("看看有什么好货")
        elif job in ['GUARD', 'SOLDIER']:
            quick_replies.append("这里安全吗？")
        elif job == 'SCHOLAR':
            quick_replies.append("请教个问题")
        elif job in ['BANDIT', 'THUG']:
            quick_replies.append("别误会，我没恶意")
        else:
            quick_replies.append("能帮个忙吗？")
        
        return quick_replies
    
    def _on_player_send(self, message: str):
        """玩家发送消息的回调"""
        print(f"[NPCChatIntegration] _on_player_send 被调用，消息: '{message[:30]}...'")
        
        if not self._current_npc:
            print("[NPCChatIntegration] 错误: _current_npc 为空!")
            return
        
        print(f"[NPCChatIntegration] 当前NPC: {self._current_npc.name}, API可用: {self._api_available}")
        
        if self._api_available and self._chat_manager:
            # 使用AI生成回复
            print("[NPCChatIntegration] 使用AI生成回复...")
            self._send_to_ai(message)
        else:
            # 使用本地模板回复
            print("[NPCChatIntegration] 使用本地模板回复（AI不可用）...")
            self._send_local_reply(message)
    
    def _send_to_ai(self, message: str):
        """发送消息给AI"""
        npc = self._current_npc
        
        print(f"[NPCChatIntegration] _send_to_ai 开始，NPC: {npc.name}, 消息: '{message[:50]}...'")
        
        # 显示处理中
        self._chat_ui.set_processing(True)
        
        # 获取记忆系统
        memory = self._get_or_create_memory(npc)
        
        # 添加玩家消息到记忆
        if memory:
            memory.add_conversation_memory("玩家", message, is_player=True)
        
        # 设置ChatManager的消息回调
        # 【关键】使用消息队列将回调结果传递到主线程，避免跨线程UI操作问题
        def on_message_callback(chat_message):
            """处理ChatManager发来的消息 - 注意：这个回调在后台线程执行！"""
            print(f"[NPCChatIntegration] *** on_message_callback 被调用 (后台线程)")
            print(f"[NPCChatIntegration]   role: {chat_message.role}")
            print(f"[NPCChatIntegration]   content: {chat_message.content[:100] if chat_message.content else '(空)'}...")
            
            if chat_message.role == "npc":
                # 将消息放入队列，由主线程的update()处理
                self._pending_messages.put({
                    'type': 'npc_response',
                    'content': chat_message.content,
                    'emotion': chat_message.emotion,
                    'action': chat_message.action
                })
                print(f"[NPCChatIntegration] [ok] NPC回复已放入队列，队列大小: {self._pending_messages.qsize()}")
            elif chat_message.role == "system":
                # 系统消息也需要显示（如错误提示）
                self._pending_messages.put({
                    'type': 'system_message',
                    'content': chat_message.content
                })
                print(f"[NPCChatIntegration] 收到系统消息，已放入队列")
            elif chat_message.role == "player":
                print(f"[NPCChatIntegration] 收到玩家消息回调，忽略（ChatUI已处理）")
        
        # 设置回调
        self._chat_manager.set_on_message(on_message_callback)
        print(f"[NPCChatIntegration] 已设置消息回调")
        
        # 发送消息
        try:
            # 如果还没有开始会话，先开始
            if not self._chat_manager.is_chatting():
                print(f"[NPCChatIntegration] ChatManager没有活跃会话，先开始会话...")
                # 传入 game_ctx 以支持 NPC 距离计算等空间感知功能
                game_ctx = getattr(self, '_current_ctx', None)
                if not self._chat_manager.start_chat(npc, auto_greeting=False, game_ctx=game_ctx):
                    print("[NPCChatIntegration] [!] 无法开始AI对话")
                    self._chat_ui.set_processing(False)
                    self._send_local_reply(message)
                    return
                print(f"[NPCChatIntegration] [ok] 会话已开始")
            
            # 发送玩家消息
            print(f"[NPCChatIntegration] 调用 ChatManager.send_message...")
            if not self._chat_manager.send_message(message):
                print("[NPCChatIntegration] [!] send_message 返回 False")
                self._chat_ui.set_processing(False)
                self._send_local_reply(message)
            else:
                print(f"[NPCChatIntegration] [ok] send_message 返回 True，等待AI回复...")
        except Exception as e:
            print(f"[NPCChatIntegration] [!] AI发送异常: {e}")
            import traceback
            traceback.print_exc()
            self._chat_ui.set_processing(False)
            self._send_local_reply(message)
    
    def _send_local_reply(self, message: str):
        """使用本地模板生成回复（无AI时的降级方案）"""
        npc = self._current_npc
        if not npc:
            return
        
        # 简单的关键词匹配回复
        message_lower = message.lower()
        
        replies = {
            "你好": ["你好啊。", "嗯，你好。", "见过了。"],
            "再见": ["慢走。", "再会。", "告辞。"],
            "帮忙": ["看情况吧。", "你想要什么帮助？", "我能帮什么？"],
            "买": ["看看吧。", "想要什么？", "您请看。"],
            "卖": ["有什么好东西？", "让我看看。", "拿出来瞧瞧。"],
            "任务": ["这个嘛...", "有点难办。", "看你本事了。"],
        }
        
        # 匹配关键词
        reply = None
        for keyword, responses in replies.items():
            if keyword in message_lower:
                import random
                reply = random.choice(responses)
                break
        
        if not reply:
            # 默认回复
            default_replies = [
                "嗯...",
                "是吗？",
                "哦。",
                "这样啊。",
                "我听着呢。",
            ]
            import random
            reply = random.choice(default_replies)
        
        # 显示回复
        self._chat_ui.add_message("npc", reply, "neutral")
    
    def _build_npc_context(self, npc: 'NPC') -> dict:
        """构建NPC的上下文信息"""
        return {
            'id': npc.id,
            'name': npc.name,
            'job': getattr(npc, 'job', 'NONE'),
            'power_type': getattr(npc, 'power_type', '民'),
            'org_id': getattr(npc, 'org_id', 'NONE'),
            'social_level': getattr(npc, 'social_level', 1),
            'affinity_to_player': getattr(npc, 'affinity_to_player', 0),
            'knows_player': getattr(npc, 'knows_player', False),
            'morality': getattr(npc, 'morality', 50),
            'bravery': getattr(npc, 'bravery', 50),
            'wit': getattr(npc, 'wit', 5),
            'charm': getattr(npc, 'charm', 5),
            'desc': getattr(npc, 'desc', ''),
            'tags': getattr(npc, 'tags', []),
        }
    
    def _apply_response_effects(self, npc: 'NPC', affinity_change: int, memory_update: str):
        """应用AI响应的游戏效果"""
        # 好感度变化
        if affinity_change != 0:
            npc.modify_affinity(self._player_id, affinity_change)
            npc.sync_affinity_to_player(self._player_id)
        
        # 记忆更新
        if memory_update:
            npc.add_memory(
                event_type='CHAT',
                target_id=self._player_id,
                target_name='玩家',
                description=memory_update,
                importance=2
            )
        
        # 标记玩家已认识这个NPC
        if not npc.knows_player:
            npc.knows_player = True
    
    def _on_chat_close(self):
        """聊天关闭的回调"""
        if self._current_npc and self._chat_manager:
            self._chat_manager.end_chat(save_memory=True)
        
        self._current_npc = None
        print("[NPCChatIntegration] 对话结束")
    
    def update(self):
        """每帧更新 - 在主线程中执行"""
        # 【关键】处理来自后台线程的消息队列
        queue_size = self._pending_messages.qsize()
        if queue_size > 0:
            print(f"[NPCChatIntegration] update() 检测到 {queue_size} 条待处理消息")
        
        while not self._pending_messages.empty():
            try:
                msg = self._pending_messages.get_nowait()
                print(f"[NPCChatIntegration] 主线程处理队列消息: type={msg['type']}")
                
                if msg['type'] == 'npc_response':
                    # 在主线程中安全地更新UI
                    if self._chat_ui:
                        self._chat_ui.set_processing(False)
                        content = msg.get('content', '')
                        emotion = msg.get('emotion', 'neutral')
                        action = msg.get('action')
                        print(f"[NPCChatIntegration] 添加NPC回复到UI: {content[:50]}...")
                        self._chat_ui.add_message("npc", content, emotion, action)
                        print(f"[NPCChatIntegration] [ok] NPC回复已添加到UI (主线程)")
                        
                        # 【新增】如果有action字段，执行对应的NPC行为
                        if action and self._current_npc:
                            self._execute_npc_action(action)
                    else:
                        print(f"[NPCChatIntegration] [!] chat_ui 为空，无法显示回复!")
                        
                elif msg['type'] == 'system_message':
                    # 系统消息（如错误提示）
                    if self._chat_ui:
                        self._chat_ui.set_processing(False)
                        self._chat_ui.add_message("system", msg.get('content', ''), "neutral")
                        print(f"[NPCChatIntegration] 系统消息已添加到UI")
                        
            except Exception as e:
                print(f"[NPCChatIntegration] [!] 处理队列消息失败: {e}")
                import traceback
                traceback.print_exc()
        
        if self._chat_ui:
            self._chat_ui.update()
    
    def draw(self, screen):
        """绘制聊天UI"""
        if self._chat_ui:
            self._chat_ui.draw(screen)
    
    def handle_event(self, event) -> bool:
        """
        处理事件
        
        Returns:
            bool: 是否消费了事件
        """
        if self._chat_ui:
            return self._chat_ui.handle_event(event)
        return False
    
    def is_chat_active(self) -> bool:
        """检查聊天是否激活"""
        return self._chat_ui is not None and self._chat_ui.is_active
    
    def get_current_npc(self) -> Optional['NPC']:
        """获取当前对话的NPC"""
        return self._current_npc
    
    def get_last_fail_reason(self) -> Optional[str]:
        """
        获取上次 start_chat 失败的原因
        
        Returns:
            str: 失败原因代码
                - "STORY_ACTIVE": StoryUI正在播放对话
                - "NPC_UNAVAILABLE": NPC状态不允许对话（死亡/战斗等）
                - None: 无失败或未知
        """
        return getattr(self, '_last_fail_reason', None)
    
    def _execute_npc_action(self, action_name: str):
        """
        执行NPC的行为动作
        
        Args:
            action_name: LLM返回的action字符串（如"come_to_player", "wave"等）
        """
        if not action_name or not self._current_npc:
            return
        
        try:
            from src.llm.npc_actions import NPCActionExecutor, is_action_valid_for_chat
            
            # 检查行为是否可在对话中触发
            if not is_action_valid_for_chat(action_name):
                print(f"[NPCChatIntegration] 行为 '{action_name}' 不能在对话中触发，跳过")
                return
            
            # 创建执行器并执行
            game_ctx = getattr(self, '_current_ctx', None)
            executor = NPCActionExecutor(ctx=game_ctx)
            
            if executor.execute_chat_action(self._current_npc, action_name):
                print(f"[NPCChatIntegration] [ok] 成功执行NPC行为: {action_name}")
            else:
                print(f"[NPCChatIntegration] [!] 执行NPC行为失败: {action_name}")
                
        except Exception as e:
            print(f"[NPCChatIntegration] 执行NPC行为时出错: {e}")
            import traceback
            traceback.print_exc()


# 便捷函数
def get_chat_integration() -> NPCChatIntegration:
    """获取聊天集成管理器实例"""
    return NPCChatIntegration.get_instance()
