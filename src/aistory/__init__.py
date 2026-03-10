"""
大宋实况 - AI叙事导演系统

基于大语言模型的全局导演系统，用于生成有意义的NPC困境和故事弧。
"""

# 共享类型（与director_system共用）
from .shared_types import (
    WorldSnapshot,
    DramaticTension
)

# 数据模型
from .dilemma_seed import (
    NPCDilemmaSeed,
    DilemmaPhase,
    StoryBeat,
    Tension,
    TensionType
)

# NPC数据模型
from .dilemma_deriver import NPCData

# 核心模块
from .dilemma_deriver import DilemmaDeriver
from .rolling_story_generator import RollingStoryGenerator, EventCard, EventChoice
from .phase_evaluator import PhaseEvaluator
from .ripple_engine import RippleEngine, RippleEffect, SocialLink, RippleType

# 主控制器
from .story_director import StoryDirector, DirectorConfig, ActiveArc

__all__ = [
    # 共享类型
    'WorldSnapshot',
    'DramaticTension',
    
    # 数据模型
    'NPCDilemmaSeed',
    'DilemmaPhase',
    'StoryBeat',
    'Tension',
    'TensionType',
    'NPCData',
    
    # 事件生成
    'EventCard',
    'EventChoice',
    
    # 涟漪系统
    'RippleEffect',
    'SocialLink',
    'RippleType',
    
    # 导演配置
    'DirectorConfig',
    'ActiveArc',
    
    # 核心模块
    'DilemmaDeriver',
    'RollingStoryGenerator',
    'PhaseEvaluator',
    'RippleEngine',
    'StoryDirector',
]
