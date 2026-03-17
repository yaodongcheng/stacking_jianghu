"""
困境种子系统 - 定义NPC的人生困境数据结构

核心概念：
- 困境不是手写的剧本，而是从NPC数据自动派生的"人生张力"
- 每个困境包含多条张力线（两股对立力量的拉扯）
- 困境热度决定导演系统何时将其转化为事件
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum, auto
from datetime import datetime


class DilemmaPhase(Enum):
    """
    困境阶段 - 起承转合四阶段模型（与aistory_prompt_example.md一致）
    
    阶段规则：
    - EMERGE(起): 0个节拍，事件初现，3个选项
    - ESCALATE(承): 1个节拍，矛盾升级，3个选项
    - CLIMAX(转): 2个节拍，关键抉择，2个选项（必须选边站）
    - SETTLE(合): 3个节拍，尘埃落定，2个选项
    """
    EMERGE = "EMERGE"           # 起：事件初现，暴露内心困境
    ESCALATE = "ESCALATE"       # 承：矛盾升级，压力增大
    CLIMAX = "CLIMAX"           # 转：关键抉择，必须选边站
    SETTLE = "SETTLE"           # 合：尘埃落定，后果显现


class TensionType(Enum):
    """张力类型"""
    RELATIONSHIP = "RELATIONSHIP"   # 人际关系张力
    ECONOMIC = "ECONOMIC"           # 经济/生存张力
    MORAL = "MORAL"                 # 道德/伦理张力
    IDENTITY = "IDENTITY"           # 身份/认同张力
    SURVIVAL = "SURVIVAL"           # 生死存亡张力
    LOYALTY = "LOYALTY"             # 忠诚冲突张力


@dataclass
class Tension:
    """
    一条张力线——两个对立力量在拉扯这个NPC
    
    示例：
    - type: RELATIONSHIP
    - force_a: "对丈夫的忠诚"
    - force_b: "对自由的渴望"
    - intensity: 75
    - related_npcs: ["husband_id"]
    """
    type: TensionType
    force_a: str                    # 拉向一边的力量描述
    force_b: str                    # 拉向另一边的力量描述
    intensity: float = 0.0          # 张力强度 0-100
    related_npcs: List[str] = field(default_factory=list)
    potential_crisis: str = ""      # 如果爆发，最可能的危机场景
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "force_a": self.force_a,
            "force_b": self.force_b,
            "intensity": self.intensity,
            "related_npcs": self.related_npcs,
            "potential_crisis": self.potential_crisis
        }


@dataclass
class StoryBeat:
    """
    已经发生的一个故事节拍
    
    记录NPC经历的关键事件，用于：
    1. 推断当前困境阶段
    2. 生成连贯的后续事件
    3. 计算困境热度
    """
    beat_number: int = 0
    timestamp: str = ""
    event_summary: str = ""         # LLM生成的事件摘要
    player_choice: str = ""         # 玩家做了什么选择
    consequence_summary: str = ""   # 造成了什么后果
    npc_state_change: Dict = field(default_factory=dict)  # NPC状态的具体变化
    tension_delta: float = 0.0      # 这个节拍让局势压力变化了多少（与JSON输出对应）
    phase: 'DilemmaPhase' = None    # 发生时的困境阶段
    # 新增字段：用于记录完整的困境信息，供后续阶段参考
    dilemma_type: str = ""          # 困境类型（如 SACRIFICE, BETRAY 等）
    event_theme: str = ""           # 事件主题（如 维持生计-赌博成瘾）
    desire: str = ""                # 内心渴望
    misgiving: str = ""             # 内心顾虑
    
    def __post_init__(self):
        if self.phase is None:
            from .dilemma_seed import DilemmaPhase
            self.phase = DilemmaPhase.EMERGE
    
    def to_dict(self) -> Dict:
        return {
            "beat_number": self.beat_number,
            "timestamp": self.timestamp,
            "event_summary": self.event_summary,
            "player_choice": self.player_choice,
            "consequence_summary": self.consequence_summary,
            "npc_state_change": self.npc_state_change,
            "tension_delta": self.tension_delta,
            "phase": self.phase.value if self.phase else "EMERGE",
            "dilemma_type": self.dilemma_type,
            "event_theme": self.event_theme,
            "desire": self.desire,
            "misgiving": self.misgiving
        }


@dataclass
class NPCDilemmaSeed:
    """
    NPC困境种子 - 简化版，用于记录故事进度
    
    【重构后】核心变化：
    - 不再预计算 tensions 列表
    - desire 和 misgiving 在生成时从 NPC 属性动态计算
    - 主要作为状态容器，记录阶段和历史节拍
    """
    id: str = ""
    
    # 核心矛盾：欲望 vs 顾虑（在首次生成时从NPC动态计算）
    desire: str = ""                # 内心渴望（首次生成时计算）
    misgiving: str = ""             # 内心顾虑（首次生成时计算，代替原来的reality_block）
    
    # 困境热度（0-100），越高越该被导演安排事件
    heat: float = 0.0
    
    # 已经发生的故事节拍记录
    story_beats: List[StoryBeat] = field(default_factory=list)
    
    # 当前困境阶段（从已发生的节拍推断）
    phase: DilemmaPhase = DilemmaPhase.EMERGE
    
    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """序列化为字典"""
        return {
            "id": self.id,
            "desire": self.desire,
            "misgiving": self.misgiving,
            "heat": self.heat,
            "story_beats": [b.to_dict() for b in self.story_beats],
            "phase": self.phase.value,
            "created_at": self.created_at,
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'NPCDilemmaSeed':
        """从字典反序列化"""
        seed = cls(
            id=data.get("id", ""),
            desire=data.get("desire", ""),
            # 兼容旧数据：reality_block 映射到 misgiving
            misgiving=data.get("misgiving") or data.get("reality_block", ""),
            heat=data.get("heat", 0.0),
            phase=DilemmaPhase(data.get("phase", "EMERGE")),
            created_at=data.get("created_at", ""),
            last_updated=data.get("last_updated", "")
        )
        
        # 反序列化故事节拍（包含新的 dilemma_type, event_theme 等字段）
        for b_data in data.get("story_beats", []):
            beat = StoryBeat(
                beat_number=b_data.get("beat_number", 0),
                timestamp=b_data.get("timestamp", ""),
                event_summary=b_data.get("event_summary", ""),
                player_choice=b_data.get("player_choice", ""),
                consequence_summary=b_data.get("consequence_summary", ""),
                npc_state_change=b_data.get("npc_state_change", {}),
                heat_delta=b_data.get("heat_delta", 0.0),
                tension_delta=b_data.get("tension_delta", b_data.get("heat_delta", 0.0)),
                dilemma_type=b_data.get("dilemma_type", ""),
                event_theme=b_data.get("event_theme", ""),
                desire=b_data.get("desire", ""),
                misgiving=b_data.get("misgiving", "")
            )
            seed.story_beats.append(beat)
        
        return seed
    
    def get_story_summary(self) -> str:
        """获取故事摘要，用于生成上下文"""
        if not self.story_beats:
            return "故事刚刚开始，这是第一个节拍。"
        
        summaries = []
        for beat in self.story_beats[-3:]:  # 最近3个节拍
            summaries.append(f"第{beat.beat_number}幕：{beat.event_summary}")
        return "；".join(summaries)
    
    def add_story_beat(self, beat: StoryBeat):
        """添加一个新的故事节拍"""
        beat.beat_number = len(self.story_beats) + 1
        beat.timestamp = datetime.now().isoformat()
        self.story_beats.append(beat)
        self.last_updated = datetime.now().isoformat()
        
    def is_recruitable(self) -> bool:
        """
        判断此NPC是否可被招募
        
        条件：
        1. 困境已进入SETTLE阶段
        2. 玩家一路帮助了此人（通过story_beats判断）
        """
        if self.phase != DilemmaPhase.SETTLE:
            return False
        
        # 检查玩家是否一路帮助
        helpful_choices = 0
        total_choices = 0
        
        for beat in self.story_beats:
            if beat.player_choice:
                total_choices += 1
                # 简单启发式：如果后果是正面的，认为是帮助
                if beat.tension_delta > 0 or "感谢" in beat.consequence_summary:
                    helpful_choices += 1
        
        # 至少70%的选择是帮助性的
        if total_choices > 0:
            return helpful_choices / total_choices >= 0.7
        return False