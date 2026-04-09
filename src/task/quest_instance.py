# --- src/task/quest_instance.py ---
"""
任务实例类
用于主线任务、公开委托等通用任务类型

设计依据：tasks.md 阶段二

与 QuestData 配合使用：
- QuestData 是静态配置（从CSV加载）
- QuestInstance 是运行时实例（玩家当前任务状态）
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .base import TaskBase, TaskCategory, TaskContentType

if TYPE_CHECKING:
    from .quest_system import QuestData


@dataclass
class QuestInstance(TaskBase):
    """
    任务实例
    
    对应槽位：
    - MAIN（主线任务）：槽位限1
    - PUBLIC（公开委托）：不限数量
    """
    # 关联的 QuestData ID（如果有）
    quest_data_id: str = ""
    # 任务类型（GATHER/DIALOG/INTERACT 等来自 quest_config）
    quest_type: str = ""
    # 目标（物品/NPC/区域）
    target: str = ""
    # 目标数量
    count: int = 1
    # 下一任务ID
    next_quest_id: str = ""
    
    def __post_init__(self):
        """初始化后处理"""
        self.progress_target = self.count
    
    @classmethod
    def from_quest_data(cls, quest_data: 'QuestData', 
                         category: TaskCategory = TaskCategory.MAIN) -> 'QuestInstance':
        """
        从 QuestData 创建实例
        
        Args:
            quest_data: QuestData 对象
            category: 任务分类
            
        Returns:
            QuestInstance 实例
        """
        # 内容类型映射
        type_mapping = {
            'GATHER': TaskContentType.GATHER,
            'DIALOG': TaskContentType.DELIVER,
            'INTERACT': TaskContentType.DELIVER,
            'COMBAT': TaskContentType.COMBAT,
            'SURVIVE': TaskContentType.GATHER,
        }
        content_type = type_mapping.get(quest_data.type, TaskContentType.GATHER)
        
        return cls(
            task_id=quest_data.id,
            title=quest_data.title,
            category=category,
            content_type=content_type,
            quest_data_id=quest_data.id,
            quest_type=quest_data.type,
            target=quest_data.target,
            count=quest_data.count,
            progress_target=quest_data.count,
            description=quest_data.desc,
            publisher_id=quest_data.submit_npc,
            next_quest_id=quest_data.next_id,
        )
    
    def get_display_text(self) -> str:
        """获取显示文本"""
        return self.description or self.title
