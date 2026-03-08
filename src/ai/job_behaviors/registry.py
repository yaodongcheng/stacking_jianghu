# --- src/ai/job_behaviors/registry.py ---
"""
职业行为注册表
使用延迟加载避免循环导入
"""

# 职业行为类映射（延迟加载）
_JOB_BEHAVIOR_CLASSES = {}


def _lazy_load_behaviors():
    """延迟加载职业行为类"""
    global _JOB_BEHAVIOR_CLASSES
    if _JOB_BEHAVIOR_CLASSES:
        return
    
    # 导入各职业行为类
    from src.ai.job_behaviors.farmer import FarmerBehavior
    from src.ai.job_behaviors.merchant import MerchantBehavior
    from src.ai.job_behaviors.bandit import BanditBehavior
    from src.ai.job_behaviors.scholar import ScholarBehavior
    from src.ai.job_behaviors.guard import GuardBehavior
    from src.ai.job_behaviors.artisan import ArtisanBehavior
    from src.ai.job_behaviors.official import OfficialBehavior
    from src.ai.job_behaviors.refugee import RefugeeBehavior
    
    _JOB_BEHAVIOR_CLASSES = {
        # 基础职业
        'FARMER': FarmerBehavior,
        'MERCHANT': MerchantBehavior,
        'ARTISAN': ArtisanBehavior,
        'SCHOLAR': ScholarBehavior,
        
        # 执法/军事
        'GUARD': GuardBehavior,
        'OFFICIAL': OfficialBehavior,
        'SOLDIER': GuardBehavior,  # 士兵使用守卫行为
        
        # 反派
        'BANDIT': BanditBehavior,
        'THUG': BanditBehavior,    # 泼皮使用山贼行为
        
        # 特殊职业
        'MONK': ScholarBehavior,   # 僧侣类似学者
        'NONE': RefugeeBehavior,   # 流民
    }


# 职业行为实例缓存
JOB_BEHAVIOR_REGISTRY = {}


def get_job_behavior(job: str, ai_system=None):
    """
    获取职业行为实例
    
    Args:
        job: 职业名称
        ai_system: AI系统引用（用于回调）
    
    Returns:
        职业行为实例或None
    """
    _lazy_load_behaviors()
    
    cache_key = f"{job}_{id(ai_system)}"
    if cache_key in JOB_BEHAVIOR_REGISTRY:
        return JOB_BEHAVIOR_REGISTRY[cache_key]
    
    behavior_class = _JOB_BEHAVIOR_CLASSES.get(job)
    if behavior_class is None:
        return None
    
    instance = behavior_class(ai_system)
    JOB_BEHAVIOR_REGISTRY[cache_key] = instance
    return instance


def clear_registry():
    """清空注册表缓存"""
    global JOB_BEHAVIOR_REGISTRY
    JOB_BEHAVIOR_REGISTRY = {}