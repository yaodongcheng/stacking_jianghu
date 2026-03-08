# --- src/ai/job_behaviors/__init__.py ---
"""
职业行为模块包
从原ai_system.py抽离各职业的AI行为逻辑

架构设计：
- 每个职业对应一个模块文件
- 使用注册表模式，根据npc.job动态调用对应行为
- 共享基础行为（闲逛、休息等）在base.py中
"""

from src.ai.job_behaviors.base import BaseJobBehavior
from src.ai.job_behaviors.registry import JOB_BEHAVIOR_REGISTRY, get_job_behavior

__all__ = [
    'BaseJobBehavior',
    'JOB_BEHAVIOR_REGISTRY', 
    'get_job_behavior',
]
