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
    """困境阶段 - 不是预设的，而是从已发生的节拍推断的"""
    LATENT = "latent"           # 困境潜伏，玩家还不知道
    SURFACED = "surfaced"       # 困境浮出水面，玩家见过一次
    ESCALATED = "escalated"     # 事态升级，不处理会恶化
    CRISIS = "crisis"           # 危机爆发，必须做决定
    AFTERMATH = "aftermath"     # 尘埃落定，NPC人生转折


class TensionType(Enum):
    """张力类型"""
    RELATIONSHIP = "relationship"   # 人际关系张力
    ECONOMIC = "economic"           # 经济/生存张力
    MORAL = "moral"                 # 道德/伦理张力
    IDENTITY = "identity"           # 身份/认同张力
    SURVIVAL = "survival"           # 生死存亡张力
    LOYALTY = "loyalty"             # 忠诚冲突张力


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
    heat_delta: float = 0.0         # 这个节拍让热度变化了多少
    phase: 'DilemmaPhase' = None    # 发生时的困境阶段
    
    def __post_init__(self):
        if self.phase is None:
            from .dilemma_seed import DilemmaPhase
            self.phase = DilemmaPhase.LATENT
    
    def to_dict(self) -> Dict:
        return {
            "beat_number": self.beat_number,
            "timestamp": self.timestamp,
            "event_summary": self.event_summary,
            "player_choice": self.player_choice,
            "consequence_summary": self.consequence_summary,
            "npc_state_change": self.npc_state_change,
            "heat_delta": self.heat_delta,
            "phase": self.phase.value if self.phase else "latent"
        }


@dataclass
class NPCDilemmaSeed:
    """
    NPC困境种子 - 从NPC原始数据自动派生的人生张力
    
    这是导演系统的核心数据结构：
    - 不是手写的剧本，而是从人物数据推算
    - 热度系统决定何时转化为事件
    - 故事节拍记录已发生的剧情
    """
    npc_id: str = ""
    
    # ===== 以下全部从NPC现有数据推算，不手写 =====
    # 核心矛盾：欲望 vs 现实
    desire: str = ""                # 从性格+背景推算出的深层渴望
    reality_block: str = ""         # 阻碍欲望的现实因素
    
    # 张力来源（多个，可叠加）
    tensions: List[Tension] = field(default_factory=list)
    
    # 困境热度（0-100），越高越该被导演安排事件
    heat: float = 0.0
    
    # 已经发生的故事节拍记录
    story_beats: List[StoryBeat] = field(default_factory=list)
    
    # 当前困境阶段（从已发生的节拍推断）
    phase: DilemmaPhase = DilemmaPhase.LATENT
    
    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """序列化为字典"""
        return {
            "npc_id": self.npc_id,
            "desire": self.desire,
            "reality_block": self.reality_block,
            "tensions": [t.to_dict() for t in self.tensions],
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
            npc_id=data.get("npc_id", ""),
            desire=data.get("desire", ""),
            reality_block=data.get("reality_block", ""),
            heat=data.get("heat", 0.0),
            phase=DilemmaPhase(data.get("phase", "latent")),
            created_at=data.get("created_at", ""),
            last_updated=data.get("last_updated", "")
        )
        
        # 反序列化张力
        for t_data in data.get("tensions", []):
            tension = Tension(
                type=TensionType(t_data.get("type", "relationship")),
                force_a=t_data.get("force_a", ""),
                force_b=t_data.get("force_b", ""),
                intensity=t_data.get("intensity", 0.0),
                related_npcs=t_data.get("related_npcs", []),
                potential_crisis=t_data.get("potential_crisis", "")
            )
            seed.tensions.append(tension)
        
        # 反序列化故事节拍
        for b_data in data.get("story_beats", []):
            beat = StoryBeat(
                beat_number=b_data.get("beat_number", 0),
                timestamp=b_data.get("timestamp", ""),
                event_summary=b_data.get("event_summary", ""),
                player_choice=b_data.get("player_choice", ""),
                consequence_summary=b_data.get("consequence_summary", ""),
                npc_state_change=b_data.get("npc_state_change", {}),
                heat_delta=b_data.get("heat_delta", 0.0)
            )
            seed.story_beats.append(beat)
        
        return seed
    
    def get_max_tension(self) -> Optional[Tension]:
        """获取当前最强的张力"""
        if not self.tensions:
            return None
        return max(self.tensions, key=lambda t: t.intensity)
    
    def get_related_npcs(self) -> List[str]:
        """获取所有相关的NPC ID"""
        related = set()
        for tension in self.tensions:
            related.update(tension.related_npcs)
        return list(related)
    
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
        1. 困境已进入AFTERMATH阶段
        2. 玩家一路帮助了此人（通过story_beats判断）
        """
        if self.phase != DilemmaPhase.AFTERMATH:
            return False
        
        # 检查玩家是否一路帮助
        helpful_choices = 0
        total_choices = 0
        
        for beat in self.story_beats:
            if beat.player_choice:
                total_choices += 1
                # 简单启发式：如果后果是正面的，认为是帮助
                if beat.heat_delta > 0 or "感谢" in beat.consequence_summary:
                    helpful_choices += 1
        
        # 至少70%的选择是帮助性的
        if total_choices > 0:
            return helpful_choices / total_choices >= 0.7
        return False