# --- src/task/survival.py ---
"""
生存任务类

设计依据：tasks.md 阶段一

特点：
- 以玩家内心独白形式呈现（"得找点吃的"），不是机械的系统提示
- 自动触发、自动消失，玩家无需手动操作
- 同一时间只有1个生存任务（多个触发时取 priority 最高的）
- 与时辰无关，随时可能触发
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .base import TaskBase, TaskCategory, TaskContentType

if TYPE_CHECKING:
    from src.entities import Player


@dataclass
class SurvivalTask(TaskBase):
    """
    生存任务
    
    触发时机：
    - 饱食度 >= 70 → "得找点吃的"
    - 寒冷值 >= 60 → "太冷了，得弄件衣服"
    - 铜钱 < 30 → "没钱了，得去赚点"
    - HP < max_hp * 0.3 → "伤得不轻，得养养"
    """
    trigger_type: str = ""          # "hunger" | "cold" | "money" | "hp"
    threshold: int = 0              # 触发阈值
    resolve_text: str = ""          # 恢复时文本，如"嗯，吃饱了，舒服多了"
    source: str = "THRESHOLD"       # "THRESHOLD" | "EVENT"（事件选项触发）
    
    def __post_init__(self):
        """初始化后处理"""
        self.category = TaskCategory.SURVIVAL
        self.content_type = TaskContentType.GATHER
        # 生存任务总是紧急的
        self.progress_target = 1
    
    @property
    def priority_value(self) -> int:
        """优先级数值：HP=1 > 饱食=2 > 寒冷=3 > 铜钱=4"""
        priority_map = {
            'hp': 1,
            'hunger': 2,
            'cold': 3,
            'money': 4,
        }
        return priority_map.get(self.trigger_type, 5)
    
    def get_display_text(self) -> str:
        """获取显示文本（内心独白形式）"""
        return self.description or "需要解决生存问题"
    
    def check_resolved(self, player: 'Player') -> bool:
        """
        检查是否已解决
        
        Args:
            player: 玩家对象
            
        Returns:
            是否已解决
        """
        if self.trigger_type == 'hunger':
            return player.hunger < self.threshold
        elif self.trigger_type == 'cold':
            return player.cold < self.threshold
        elif self.trigger_type == 'money':
            return player.money >= self.threshold
        elif self.trigger_type == 'hp':
            return player.hp >= player.max_hp * 0.3
        return False
    
    @classmethod
    def create_hunger_task(cls, player: 'Player') -> 'SurvivalTask':
        """创建饥饿任务"""
        return cls(
            task_id="SURVIVAL_HUNGER",
            title="饥饿",
            category=TaskCategory.SURVIVAL,
            content_type=TaskContentType.GATHER,
            description="得找点吃的……",
            trigger_type="hunger",
            threshold=70,
            resolve_text="嗯，吃饱了，舒服多了。",
        )
    
    @classmethod
    def create_cold_task(cls, player: 'Player') -> 'SurvivalTask':
        """创建寒冷任务"""
        return cls(
            task_id="SURVIVAL_COLD",
            title="寒冷",
            category=TaskCategory.SURVIVAL,
            content_type=TaskContentType.GATHER,
            description="太冷了，得弄件衣服……",
            trigger_type="cold",
            threshold=60,
            resolve_text="暖和多了。",
        )
    
    @classmethod
    def create_money_task(cls, player: 'Player') -> 'SurvivalTask':
        """创建金钱不足任务"""
        return cls(
            task_id="SURVIVAL_MONEY",
            title="囊中羞涩",
            category=TaskCategory.SURVIVAL,
            content_type=TaskContentType.GATHER,
            description="没钱了，得去赚点……",
            trigger_type="money",
            threshold=30,
            resolve_text="手头宽裕些了。",
        )
    
    @classmethod
    def create_hp_task(cls, player: 'Player') -> 'SurvivalTask':
        """创建受伤任务"""
        return cls(
            task_id="SURVIVAL_HP",
            title="受伤",
            category=TaskCategory.SURVIVAL,
            content_type=TaskContentType.GATHER,
            description="伤得不轻，得养养……",
            trigger_type="hp",
            threshold=int(player.max_hp * 0.3),
            resolve_text="伤好多了。",
        )
