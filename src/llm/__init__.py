# src/llm/__init__.py
"""
LLM 模块 - AI对话系统
提供NPC智能对话、记忆系统、提示词构建等功能
"""

from .config import LLMConfig
from .npc_memory import NPCMemorySystem, MemoryManager
from .npc_chat_integration import NPCChatIntegration, get_chat_integration
from .event_memory_bridge import (
    EventMemoryBridge, 
    get_event_memory_bridge,
    inject_world_event,
    inject_combat_memory,
    inject_trade_memory,
    inject_help_memory,
    inject_quest_memory
)

__all__ = [
    'LLMConfig',
    'NPCMemorySystem',
    'MemoryManager',
    'NPCChatIntegration',
    'get_chat_integration',
    # 事件记忆桥接器
    'EventMemoryBridge',
    'get_event_memory_bridge',
    'inject_world_event',
    'inject_combat_memory',
    'inject_trade_memory',
    'inject_help_memory',
    'inject_quest_memory',
]
