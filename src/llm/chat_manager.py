# src/llm/chat_manager.py
"""
聊天会话管理器 - 整合LLM服务、提示词构建和记忆系统
提供完整的NPC对话功能
"""

import json
import re
import time
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

from .config import LLMConfig
from .llm_service import LLMService, LLMResponse
from .prompt_builder import PromptBuilder
from .npc_memory import NPCMemorySystem, MemoryManager


@dataclass
class NPCChatResponse:
    """NPC闲聊响应结构 - 由ChatManager自己解析"""
    reply: str = ""                          # NPC的回复文本
    emotion: str = "neutral"                 # 情绪状态
    action: str = ""                         # 动作描述
    affinity_change: int = 0                 # 好感度变化
    player_options: List[str] = field(default_factory=list)  # 玩家选项
    memory_update: str = ""                  # 需要记录的记忆
    success: bool = True                     # 是否成功
    error: str = ""                          # 错误信息
    
    @classmethod
    def from_error(cls, error_msg: str):
        """创建错误响应"""
        return cls(
            reply="（思绪中断...）",
            success=False,
            error=error_msg
        )
    
    @classmethod
    def from_llm_raw(cls, raw_text: str):
        """
        从LLM原始响应解析JSON
        如果解析失败，将纯文本包装为有效响应
        """
        text = raw_text.strip()
        
        # 尝试提取JSON
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1 and end > start:
            json_text = text[start:end + 1]
            
            # 修复常见的JSON问题
            # 1. 移除注释
            json_text = re.sub(r'//.*?(?=\n|$)', '', json_text)
            json_text = re.sub(r'/\*.*?\*/', '', json_text, flags=re.DOTALL)
            # 2. 修复尾随逗号
            json_text = re.sub(r',\s*([}\]])', r'\1', json_text)
            
            try:
                data = json.loads(json_text)
                return cls(
                    reply=data.get("reply", "..."),
                    emotion=data.get("emotion", "neutral"),
                    action=data.get("action", ""),
                    affinity_change=data.get("affinity_change", 0),
                    player_options=data.get("player_options", []),
                    memory_update=data.get("memory_update", ""),
                    success=True
                )
            except json.JSONDecodeError:
                pass  # 解析失败，继续走纯文本包装逻辑
        
        # 无法找到JSON，将纯文本包装为响应
        # 清理文本：移除可能的表情前缀，如"（皱眉）"
        reply_text = text
        emotion = "neutral"
        action = ""
        
        # 尝试从文本中提取表情/动作（如"（皱眉）"、"（微笑）"等）
        emotion_match = re.match(r'^[（\(]([^）\)]+)[）\)](.*)$', text, re.DOTALL)
        if emotion_match:
            action = emotion_match.group(1).strip()
            reply_text = emotion_match.group(2).strip()
            
            # 尝试将动作映射为情绪
            action_to_emotion = {
                '皱眉': 'angry', '怒': 'angry', '生气': 'angry', '不悦': 'angry',
                '笑': 'happy', '微笑': 'happy', '高兴': 'happy', '开心': 'happy',
                '哭': 'sad', '悲伤': 'sad', '难过': 'sad', '叹气': 'sad',
                '惊': 'surprised', '惊讶': 'surprised', '吃惊': 'surprised',
                '怕': 'fearful', '害怕': 'fearful', '担忧': 'fearful',
                '冷笑': 'contempt', '不屑': 'contempt', '轻蔑': 'contempt',
            }
            for key, emo in action_to_emotion.items():
                if key in action:
                    emotion = emo
                    break
        
        # 如果回复为空，使用原文
        if not reply_text:
            reply_text = text
        
        return cls(
            reply=reply_text,
            emotion=emotion,
            action=action,
            affinity_change=0,
            success=True
        )


class ChatState(Enum):
    """对话状态"""
    IDLE = "idle"                 # 空闲
    WAITING_INPUT = "waiting"     # 等待玩家输入
    PROCESSING = "processing"     # AI处理中
    DISPLAYING = "displaying"     # 显示回复中
    FINISHED = "finished"         # 对话结束


@dataclass
class ChatMessage:
    """对话消息"""
    role: str           # "player" / "npc" / "system"
    content: str        # 消息内容
    emotion: str = ""   # NPC情绪
    action: str = ""    # NPC动作
    timestamp: float = field(default_factory=time.time)


@dataclass
class ChatSession:
    """对话会话"""
    npc_id: int
    npc_name: str
    state: ChatState = ChatState.IDLE
    messages: List[ChatMessage] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    total_affinity_change: int = 0
    is_first_meeting: bool = True
    
    def add_message(self, role: str, content: str, emotion: str = "", action: str = ""):
        """添加消息"""
        self.messages.append(ChatMessage(role, content, emotion, action))
    
    def get_recent_messages(self, count: int = 10) -> List[ChatMessage]:
        """获取最近的消息"""
        return self.messages[-count:]


class ChatManager:
    """
    聊天管理器
    
    管理玩家与NPC之间的对话，包括：
    - 会话生命周期管理
    - LLM请求和响应处理
    - 记忆更新
    - UI回调
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        # 核心组件
        self.config = LLMConfig.get_instance()
        self.llm_service = LLMService.get_instance()
        self.memory_manager = MemoryManager.get_instance()
        
        # 当前会话
        self.current_session: Optional[ChatSession] = None
        self.current_npc = None  # NPC对象引用
        
        # 回调函数
        self._on_message_callback: Optional[Callable[[ChatMessage], None]] = None
        self._on_state_change_callback: Optional[Callable[[ChatState], None]] = None
        self._on_session_end_callback: Optional[Callable[[ChatSession], None]] = None
        
        # 线程安全
        self._lock = threading.Lock()
        self._pending_response: Optional[LLMResponse] = None
        
        print("[ChatManager] 初始化完成")
    
    @classmethod
    def get_instance(cls):
        return cls()
    
    # ═══════════════════════════════════════════════════════════════
    # 会话管理
    # ═══════════════════════════════════════════════════════════════
    
    def start_chat(self, npc, auto_greeting: bool = True, game_ctx=None) -> bool:
        """
        开始与NPC的对话
        
        Args:
            npc: NPC对象
            auto_greeting: 是否自动生成开场白
            game_ctx: 游戏上下文（可选，用于计算距离等信息）
            
        Returns:
            bool: 是否成功开始
        """
        if not self.llm_service.is_available():
            print("[ChatManager] LLM服务不可用，无法开始对话")
            return False
        
        with self._lock:
            # 结束之前的会话
            if self.current_session:
                self._end_session_internal()
            
            # 创建新会话
            self.current_npc = npc
            self.game_ctx = game_ctx  # 保存游戏上下文
            self.current_session = ChatSession(
                npc_id=npc.id,
                npc_name=npc.name,
                is_first_meeting=not getattr(npc, 'knows_player', False)
            )
            
            self._set_state(ChatState.PROCESSING)
            
            print(f"[ChatManager] 开始与 {npc.name} 的对话")
        
        # 生成开场白
        if auto_greeting:
            self._generate_greeting()
        else:
            self._set_state(ChatState.WAITING_INPUT)
        
        return True
    
    def send_message(self, player_input: str) -> bool:
        """
        发送玩家消息
        
        Args:
            player_input: 玩家输入
            
        Returns:
            bool: 是否成功发送
        """
        if not self.current_session or not self.current_npc:
            print("[ChatManager] 没有活跃的对话会话")
            return False
        
        if self.current_session.state != ChatState.WAITING_INPUT:
            print(f"[ChatManager] 当前状态不允许发送消息: {self.current_session.state}")
            return False
        
        # 添加玩家消息
        self.current_session.add_message("player", player_input)
        self._notify_message(ChatMessage("player", player_input))
        
        # 更新NPC记忆
        memory = self._get_npc_memory()
        memory.add_conversation_memory(
            speaker="玩家",
            content=player_input,
            is_player=True
        )
        
        # 生成AI回复
        self._set_state(ChatState.PROCESSING)
        self._generate_response(player_input)
        
        return True
    
    def end_chat(self, save_memory: bool = True):
        """
        结束对话
        
        Args:
            save_memory: 是否保存记忆
        """
        with self._lock:
            if self.current_session:
                # 生成告别语（可选，这里简化处理）
                self._end_session_internal(save_memory)
    
    def _end_session_internal(self, save_memory: bool = True):
        """内部结束会话方法"""
        if not self.current_session:
            return
        
        session = self.current_session
        npc = self.current_npc
        
        # 更新NPC属性
        if npc and session.total_affinity_change != 0:
            npc.affinity_to_player = max(-100, min(100, 
                npc.affinity_to_player + session.total_affinity_change))
            npc.knows_player = True
            print(f"[ChatManager] {npc.name} 好感度变化: {session.total_affinity_change}")
        
        # 保存记忆
        if save_memory and npc:
            memory = self._get_npc_memory()
            memory.save_memories()
        
        # 通知回调
        if self._on_session_end_callback:
            self._on_session_end_callback(session)
        
        # 清理
        self.current_session = None
        self.current_npc = None
        self._set_state(ChatState.IDLE)
        
        print("[ChatManager] 对话结束")
    
    # ═══════════════════════════════════════════════════════════════
    # AI响应生成
    # ═══════════════════════════════════════════════════════════════
    
    def _generate_greeting(self):
        """生成NPC开场白"""
        npc = self.current_npc
        memory = self._get_npc_memory()
        
        # 构建开场白提示词
        system_prompt = PromptBuilder.build_opening_prompt(npc, memory)
        user_message = "（玩家走近了你）"
        
        print(f"[ChatManager] 请求NPC开场白: {npc.name}")
        print(f"[ChatManager] System Prompt长度: {len(system_prompt)} 字符")
        
        # 异步请求
        self.llm_service.chat_async(
            system_prompt=system_prompt,
            user_message=user_message,
            callback=self._on_greeting_received
        )
    
    def _generate_response(self, player_input: str):
        """生成AI回复"""
        npc = self.current_npc
        memory = self._get_npc_memory()
        
        # 构建提示词 - 传入game_ctx以支持距离计算
        game_ctx = getattr(self, 'game_ctx', None)
        system_prompt = PromptBuilder.build_from_npc(npc, memory, "chat", game_ctx=game_ctx)
        
        # 获取对话历史
        history = memory.format_conversation_history(max_turns=5)
        
        # 异步请求
        self.llm_service.chat_async(
            system_prompt=system_prompt,
            user_message=player_input,
            callback=self._on_response_received,
            conversation_history=history
        )
    
    def _on_greeting_received(self, response: LLMResponse):
        """处理开场白响应"""
        self._process_response(response, is_greeting=True)
    
    def _on_response_received(self, response: LLMResponse):
        """处理普通回复响应"""
        self._process_response(response, is_greeting=False)
    
    def _process_response(self, response: LLMResponse, is_greeting: bool = False):
        """处理LLM响应"""
        if not self.current_session:
            return
        
        if not response.success:
            # 处理错误
            error_msg = ChatMessage(
                role="system",
                content=f"（{self.current_npc.name}似乎在思考...）"
            )
            self._notify_message(error_msg)
            self._set_state(ChatState.WAITING_INPUT)
            return
        
        # 解析LLM原始响应为NPC闲聊格式
        chat_response = NPCChatResponse.from_llm_raw(response.raw_response)
        
        # 创建NPC消息
        npc_msg = ChatMessage(
            role="npc",
            content=chat_response.reply,
            emotion=chat_response.emotion,
            action=chat_response.action
        )
        
        with self._lock:
            # 添加到会话
            self.current_session.messages.append(npc_msg)
            
            # 累计好感度变化
            self.current_session.total_affinity_change += chat_response.affinity_change
        
        # 更新NPC记忆
        memory = self._get_npc_memory()
        memory.add_conversation_memory(
            speaker=self.current_npc.name,
            content=chat_response.reply,
            is_player=False,
            emotion_response=chat_response.emotion
        )
        
        # 如果有需要记住的内容
        if chat_response.memory_update:
            memory.add_memory(
                content=chat_response.memory_update,
                memory_type="knowledge",
                importance=3,
                tags=["对话", "玩家"]
            )
        
        # 更新玩家印象
        memory.update_impression(
            target_npc_id=9999,  # 玩家ID
            target_name="玩家",
            affinity_delta=chat_response.affinity_change
        )
        
        # 通知UI
        self._notify_message(npc_msg)
        
        # 更新状态
        self._set_state(ChatState.WAITING_INPUT)
    
    # ═══════════════════════════════════════════════════════════════
    # 快捷对话方法
    # ═══════════════════════════════════════════════════════════════
    
    def quick_response(self, npc, player_input: str, 
                       callback: Callable[[str], None] = None) -> Optional[str]:
        """
        快速获取NPC回复（不维护会话状态）
        
        Args:
            npc: NPC对象
            player_input: 玩家输入
            callback: 异步回调（如果提供则异步执行）
            
        Returns:
            str: NPC回复（同步模式）或 None（异步模式）
        """
        memory = self.memory_manager.get_npc_memory(npc.id, npc.name)
        system_prompt = PromptBuilder.build_from_npc(npc, memory, "chat")
        
        if callback:
            # 异步模式
            def _callback_wrapper(response: LLMResponse):
                if response.success:
                    chat_response = NPCChatResponse.from_llm_raw(response.raw_response)
                    callback(chat_response.reply)
                else:
                    callback("...")
            
            self.llm_service.chat_async(system_prompt, player_input, _callback_wrapper)
            return None
        else:
            # 同步模式
            response = self.llm_service.chat(system_prompt, player_input)
            if response.success:
                chat_response = NPCChatResponse.from_llm_raw(response.raw_response)
                return chat_response.reply
            return "..."
    
    def get_npc_reaction(self, npc, event_description: str) -> Optional[str]:
        """
        获取NPC对事件的反应
        
        Args:
            npc: NPC对象
            event_description: 事件描述
            
        Returns:
            str: NPC的反应
        """
        memory = self.memory_manager.get_npc_memory(npc.id, npc.name)
        
        system_prompt = PromptBuilder.build_from_npc(npc, memory, "event")
        user_message = f"【发生了以下事件】{event_description}\n请做出你的反应。"
        
        response = self.llm_service.chat(system_prompt, user_message)
        
        if response.success:
            # 解析响应
            chat_response = NPCChatResponse.from_llm_raw(response.raw_response)
            # 记录事件
            memory.add_event_memory(event_description, importance=3)
            return chat_response.reply
        
        return None
    
    # ═══════════════════════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════════════════════
    
    def _get_npc_memory(self) -> NPCMemorySystem:
        """获取当前NPC的记忆系统（会先同步NPC实体上的记忆）"""
        if self.current_npc:
            # 先从NPC实体同步记忆到LLM系统（确保两套系统一致）
            return self.memory_manager.sync_from_npc_entity(self.current_npc)
        return None
    
    def _set_state(self, new_state: ChatState):
        """设置会话状态"""
        if self.current_session:
            old_state = self.current_session.state
            self.current_session.state = new_state
            
            if self._on_state_change_callback and old_state != new_state:
                self._on_state_change_callback(new_state)
    
    def _notify_message(self, message: ChatMessage):
        """通知新消息"""
        if self._on_message_callback:
            self._on_message_callback(message)
    
    # ═══════════════════════════════════════════════════════════════
    # 回调设置
    # ═══════════════════════════════════════════════════════════════
    
    def set_on_message(self, callback: Callable[[ChatMessage], None]):
        """设置消息回调"""
        self._on_message_callback = callback
    
    def set_on_state_change(self, callback: Callable[[ChatState], None]):
        """设置状态变化回调"""
        self._on_state_change_callback = callback
    
    def set_on_session_end(self, callback: Callable[[ChatSession], None]):
        """设置会话结束回调"""
        self._on_session_end_callback = callback
    
    # ═══════════════════════════════════════════════════════════════
    # 状态查询
    # ═══════════════════════════════════════════════════════════════
    
    def is_chatting(self) -> bool:
        """是否正在对话中"""
        return self.current_session is not None
    
    def is_available(self) -> bool:
        """LLM服务是否可用"""
        return self.llm_service.is_available()
    
    def get_current_state(self) -> ChatState:
        """获取当前会话状态"""
        if self.current_session:
            return self.current_session.state
        return ChatState.IDLE
    
    def get_chat_history(self) -> List[ChatMessage]:
        """获取当前会话的聊天记录"""
        if self.current_session:
            return self.current_session.messages.copy()
        return []
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        llm_stats = self.llm_service.get_stats()
        return {
            "llm": llm_stats,
            "is_chatting": self.is_chatting(),
            "current_npc": self.current_npc.name if self.current_npc else None,
            "message_count": len(self.current_session.messages) if self.current_session else 0
        }
