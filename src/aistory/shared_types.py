"""
共享数据类型定义

用于在 director_system 和 aistory 模块之间共享基础数据类型
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class DramaticTension(Enum):
    """戏剧张力等级"""
    LOW = 1       # 日常小事
    MEDIUM = 2    # 有趣冲突
    HIGH = 3      # 重大事件
    CRITICAL = 4  # 命运转折


@dataclass
class WorldSnapshot:
    """
    世界状态快照 - 导演的"全知视角"
    
    这是共享定义，被 director_system 和 aistory 共同使用
    """
    timestamp: float
    
    # 势力状态
    faction_tensions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    faction_power_balance: Dict[str, float] = field(default_factory=dict)
    recent_conflicts: List[Dict] = field(default_factory=list)
    
    # NPC状态 - 完整演员池
    all_available_npcs: List[Dict] = field(default_factory=list)
    npcs_in_crisis: List[Dict] = field(default_factory=list)
    npcs_with_secrets: List[Dict] = field(default_factory=list)
    relationship_tensions: List[Dict] = field(default_factory=list)
    
    # 玩家相关
    player_reputation: Dict[str, float] = field(default_factory=dict)
    player_recent_actions: List[str] = field(default_factory=list)
    player_relationships: List[Dict] = field(default_factory=list)
    
    # 戏剧节奏
    recent_event_types: List[str] = field(default_factory=list)
    time_since_last_big_event: float = 0
    current_dramatic_arc: str = "rising"
    
    # 扩展：新版本添加的字段
    game_time: Optional[str] = None
    player_location: Optional[str] = None
    active_quests: List[str] = field(default_factory=list)