# --- src/ai/__init__.py ---
"""
AI系统模块包
将原4000+行的ai_system.py拆分为多个专职模块

架构设计：
- constants.py: 共享常量定义
- event_processor.py: 事件处理与感知
- combat_ai.py: 战斗AI（索敌、追击、战斗执行）
- spectate_ai.py: 围观AI
- organization_ai.py: 组织AI（集结、首领跟随）
- job_behaviors/: 职业行为包
"""

from src.ai.constants import *
from src.ai.event_processor import EventProcessor
from src.ai.combat_ai import CombatAI
from src.ai.spectate_ai import SpectateAI
from src.ai.organization_ai import OrganizationAI
from src.ai.job_behaviors import get_job_behavior, JOB_BEHAVIOR_REGISTRY

__all__ = [
    # 常量
    'COMBAT_FACE_DIST', 'COMBAT_ATTACK_RANGE',
    'SPECTATE_RADIUS_MIN', 'SPECTATE_RADIUS_MAX', 'SPECTATE_NOTICE_RADIUS',
    'SCAN_RADIUS', 'SEE_RADIUS',
    'HOSTILE_JOBS', 'NEUTRAL_JOBS',
    'RALLY_RADIUS', 'RALLY_COOLDOWN',
    
    # 模块类
    'EventProcessor',
    'CombatAI',
    'SpectateAI',
    'OrganizationAI',
    
    # 职业行为
    'get_job_behavior',
    'JOB_BEHAVIOR_REGISTRY',
]