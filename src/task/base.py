# --- src/task/base.py ---
"""
任务基类系统
统一的任务状态管理和公共接口

设计依据：
- tasks.md 阶段二：任务槽位与基础框架
- OrgTaskSystem 已有 status/progress/cooldown_until 等同构字段
- 统一任务管道，避免重复造轮子

子类关系：
- TaskBase (基类)
  ├── OrgTask (势力任务)
  ├── QuestInstance (主线/公开委托)
  ├── SurvivalTask (生存任务)
  └── IntelQuest (情报委托)
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════════════
# 枚举定义
# ═══════════════════════════════════════════════════════════════════════════════

class TaskStatus(Enum):
    """统一任务状态枚举"""
    AVAILABLE = "available"     # 可接取（尚未开始）
    ACTIVE = "active"           # 进行中
    READY = "ready"             # 已完成目标，待交付（对应 OrgTaskStatus.COMPLETED）
    COMPLETED = "completed"     # 已交付完成
    FAILED = "failed"           # 失败（截止时间已过）
    COOLDOWN = "cooldown"       # 冷却中


class TaskCategory(Enum):
    """任务分类（对应槽位）"""
    MAIN = "MAIN"               # 主线任务 - 槽位限1
    INTEL = "INTEL"             # 情报委托 - 槽位限1
    FACTION = "FACTION"         # 势力任务 - 槽位限1
    PUBLIC = "PUBLIC"           # 公开委托 - 不限
    SURVIVAL = "SURVIVAL"       # 生存任务 - 槽位限1


class TaskContentType(Enum):
    """任务内容类型（执行方式）"""
    COMBAT = "COMBAT"           # 战斗 - 击败敌人/保护某人
    GATHER = "GATHER"           # 收集 - 收集资源/物品/金钱
    INVESTIGATE = "INVESTIGATE" # 调查 - 收集情报/打探消息
    DELIVER = "DELIVER"         # 传递 - 送信/传话


# ═══════════════════════════════════════════════════════════════════════════════
# 任务类型显示样式（供 UI 层引用）
# ═══════════════════════════════════════════════════════════════════════════════

# 任务类型优先级（数值越小越优先）
TASK_PRIORITY = {
    TaskCategory.SURVIVAL: 1,   # 生存最优先
    TaskCategory.INTEL: 2,      # 情报次之
    TaskCategory.FACTION: 3,    # 势力第三
    TaskCategory.MAIN: 4,       # 主线最后
    TaskCategory.PUBLIC: 5,     # 公开委托最后
}

# 任务类型显示样式
TASK_TYPE_STYLES = {
    TaskCategory.SURVIVAL: {
        'color': (255, 100, 80),          # 红色 - 紧急
        'prefix': '!',                    # 感叹号前缀
        'bg_color': (60, 30, 30),         # 深红背景
        'label': '生存',
    },
    TaskCategory.INTEL: {
        'color': (100, 180, 255),         # 蓝色 - 信息
        'prefix': '?',                    # 问号前缀
        'bg_color': (30, 40, 55),         # 深蓝背景
        'label': '情报',
    },
    TaskCategory.FACTION: {
        'color': (255, 200, 80),          # 黄色 - 势力
        'prefix': '*',                    # 星号前缀
        'bg_color': (50, 45, 30),         # 深黄背景
        'label': '势力',
    },
    TaskCategory.MAIN: {
        'color': (200, 150, 255),         # 紫金色 - 主线
        'prefix': '▶',                    # 三角前缀
        'bg_color': (45, 35, 55),         # 深紫背景
        'label': '主线',
    },
    TaskCategory.PUBLIC: {
        'color': (180, 180, 180),         # 灰白色 - 公开
        'prefix': '○',                    # 空心圆前缀
        'bg_color': (40, 40, 40),         # 深灰背景
        'label': '委托',
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# 任务基类
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TaskBase:
    """
    任务基类
    
    所有任务类型的公共基类，提供统一的状态管理和公共接口。
    子类包括：OrgTask、QuestInstance、SurvivalTask、IntelQuest
    
    设计原则：
    - 任务必须有发布人 - 不存在无发布人的"系统任务"
    - 任务状态机：AVAILABLE → ACTIVE → READY → COMPLETED
    - 截止时间、进度检查等通用逻辑在此类中定义
    """
    # ═══════════════════════════════════════════════════════════════
    # 核心标识字段
    # ═══════════════════════════════════════════════════════════════
    task_id: str                           # 任务唯一ID
    title: str                             # 任务标题（显示用）
    category: TaskCategory                 # 任务分类（对应槽位）
    content_type: TaskContentType          # 任务内容类型（执行方式）
    
    # ═══════════════════════════════════════════════════════════════
    # 状态管理字段
    # ═══════════════════════════════════════════════════════════════
    status: TaskStatus = field(default=TaskStatus.AVAILABLE)
    progress: int = field(default=0)       # 当前进度
    progress_target: int = field(default=1)  # 目标数量（用于计算进度）
    
    # ═══════════════════════════════════════════════════════════════
    # 时间相关字段
    # ═══════════════════════════════════════════════════════════════
    start_day: int = field(default=0)      # 接取时的游戏天数
    deadline_days: int = field(default=0)  # 截止天数，0=无限
    cooldown_until: int = field(default=0) # 冷却结束的游戏日（完成任务后）
    
    # ═══════════════════════════════════════════════════════════════
    # 发布人/关系字段
    # ════════��══════════════════════════════════════════════════════
    publisher_id: str = field(default="")  # 发布人ID（NPC ID 或 "PLAYER"）
    publisher_name: str = field(default="")# 发布人名称（显示用）
    
    # ═══════════════════════════════════════════════════════════════
    # 奖励字段
    # ═══════════════════════════════════════════════════════════════
    reward_gold: int = field(default=0)    # 金钱奖励
    reward_fame: int = field(default=0)    # 声望奖励
    reward_relation: int = field(default=0) # 发布人好感变化
    reward_items: str = field(default="")  # 物品奖励（格式: "物品名:数量"）
    
    # ═══════════════════════════════════════════════════════════════
    # 接取时发放字段
    # ═══════════════════════════════════════════════════════════════
    given_gold: int = field(default=0)     # 接取时发放本金
    given_item: str = field(default="")    # 接取时发放物品
    given_item_count: int = field(default=0)
    
    # ═══════════════════════════════════════════════════════════════
    # 失败惩罚字段
    # ═══════════════════════════════════════════════════════════════
    failure_relation: int = field(default=0)  # 失败时发布人好感-N
    
    # ═══════════════════════════════════════════════════════════════
    # 描述字段
    # ═══════════════════════════════════════════════════════════════
    description: str = field(default="")   # 任务描述（叙事感文本）
    target_desc: str = field(default="")   # 目标描述（如"去某地找某人"）
    
    # ═══════════════════════════════════════════════════════════════
    # 扩展字段（子类可用）
    # ═══════════════════════════════════════════════════════════════
    extra_data: Dict[str, Any] = field(default_factory=dict)  # 扩展数据
    
    # =========================================================================
    # 状态查询方法
    # =========================================================================
    
    def is_active(self) -> bool:
        """是否进行中"""
        return self.status == TaskStatus.ACTIVE
    
    def is_ready(self) -> bool:
        """是否已完成目标，待交付"""
        return self.status == TaskStatus.READY
    
    def is_complete(self) -> bool:
        """是否目标已完成（用于进度检查）"""
        return self.progress >= self.progress_target
    
    def is_failed(self) -> bool:
        """是否已失败"""
        return self.status == TaskStatus.FAILED
    
    def is_on_cooldown(self, current_day: int) -> bool:
        """是否在冷却期内"""
        return self.status == TaskStatus.COOLDOWN and current_day < self.cooldown_until
    
    def is_expired(self, current_day: int) -> bool:
        """是否已过期（超过截止时间）"""
        if self.deadline_days <= 0:
            return False
        return current_day > self.start_day + self.deadline_days
    
    # =========================================================================
    # 状态变更方法
    # =========================================================================
    
    def accept(self, current_day: int) -> bool:
        """
        接取任务
        
        Args:
            current_day: 当前游戏天数
            
        Returns:
            是否成功接取
        """
        if self.status != TaskStatus.AVAILABLE:
            return False
        self.status = TaskStatus.ACTIVE
        self.start_day = current_day
        self.progress = 0
        return True
    
    def update_progress(self, amount: int = 1) -> bool:
        """
        更新进度
        
        Args:
            amount: 进度增量
            
        Returns:
            是否达到目标
        """
        if self.status != TaskStatus.ACTIVE:
            return False
        self.progress += amount
        if self.is_complete():
            self.status = TaskStatus.READY
            return True
        return False
    
    def complete(self, current_day: int, cooldown_days: int = 0):
        """
        完成交付
        
        Args:
            current_day: 当前游戏天数
            cooldown_days: 冷却天数
        """
        self.status = TaskStatus.COMPLETED
        if cooldown_days > 0:
            self.cooldown_until = current_day + cooldown_days
    
    def fail(self):
        """标记失败"""
        self.status = TaskStatus.FAILED
    
    def abandon(self):
        """放弃任务"""
        self.status = TaskStatus.AVAILABLE
        self.progress = 0
        self.start_day = 0
    
    # =========================================================================
    # UI 展示方法
    # =========================================================================
    
    def get_progress_text(self) -> str:
        """获取进度文本，如 "3/10" """
        if self.progress_target <= 1:
            return ""
        return f"{self.progress}/{self.progress_target}"
    
    def get_display_text(self) -> str:
        """获取显示文本（简短版，用于 sidebar）"""
        return self.description or self.title
    
    def get_full_description(self) -> str:
        """获取完整描述（用于详情弹窗）"""
        parts = []
        if self.description:
            parts.append(self.description)
        if self.target_desc:
            parts.append(f"目标：{self.target_desc}")
        return "\n".join(parts)
    
    def get_reward_text(self) -> str:
        """获取奖励描述文本"""
        rewards = []
        if self.reward_gold > 0:
            rewards.append(f"铜钱 {self.reward_gold}")
        if self.reward_fame > 0:
            rewards.append(f"声望 {self.reward_fame}")
        if self.reward_relation > 0:
            rewards.append(f"好感 +{self.reward_relation}")
        if self.reward_items:
            rewards.append(self.reward_items)
        return "、".join(rewards) if rewards else "无"
    
    def get_deadline_text(self, current_day: int) -> str:
        """获取截止时间描述"""
        if self.deadline_days <= 0:
            return "无期限"
        remaining = self.start_day + self.deadline_days - current_day
        if remaining <= 0:
            return "已过期"
        return f"剩余 {remaining} 天"
    
    def get_style(self) -> Dict[str, Any]:
        """获取显示样式"""
        return TASK_TYPE_STYLES.get(self.category, TASK_TYPE_STYLES[TaskCategory.MAIN])
    
    def get_priority(self) -> int:
        """获取显示优先级"""
        return TASK_PRIORITY.get(self.category, 99)
    
    def to_display_data(self) -> 'TaskDisplayData':
        """
        转换为 TaskDisplayData（供 sidebar 使用）
        子类可覆盖此方法提供更多详情
        """
        from .display import TaskDisplayData
        style = self.get_style()
        return TaskDisplayData(
            task_type=self.category.value,
            text=self.get_display_text(),
            progress=self.get_progress_text(),
            is_complete=self.is_ready(),
            is_urgent=(self.category == TaskCategory.SURVIVAL),
            target_npc=self.publisher_name,
            objective=self.target_desc,
            reward=self.get_reward_text(),
            deadline_days=max(0, self.start_day + self.deadline_days),
            description=self.description,
        )
    
    # =========================================================================
    # 序列化方法
    # =========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于保存/传输）"""
        return {
            'task_id': self.task_id,
            'title': self.title,
            'category': self.category.value,
            'content_type': self.content_type.value,
            'status': self.status.value,
            'progress': self.progress,
            'progress_target': self.progress_target,
            'start_day': self.start_day,
            'deadline_days': self.deadline_days,
            'cooldown_until': self.cooldown_until,
            'publisher_id': self.publisher_id,
            'publisher_name': self.publisher_name,
            'reward_gold': self.reward_gold,
            'reward_fame': self.reward_fame,
            'reward_relation': self.reward_relation,
            'reward_items': self.reward_items,
            'given_gold': self.given_gold,
            'given_item': self.given_item,
            'given_item_count': self.given_item_count,
            'failure_relation': self.failure_relation,
            'description': self.description,
            'target_desc': self.target_desc,
            'extra_data': self.extra_data,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskBase':
        """从字典创建（用于加载）"""
        return cls(
            task_id=data['task_id'],
            title=data['title'],
            category=TaskCategory(data['category']),
            content_type=TaskContentType(data['content_type']),
            status=TaskStatus(data.get('status', 'available')),
            progress=data.get('progress', 0),
            progress_target=data.get('progress_target', 1),
            start_day=data.get('start_day', 0),
            deadline_days=data.get('deadline_days', 0),
            cooldown_until=data.get('cooldown_until', 0),
            publisher_id=data.get('publisher_id', ''),
            publisher_name=data.get('publisher_name', ''),
            reward_gold=data.get('reward_gold', 0),
            reward_fame=data.get('reward_fame', 0),
            reward_relation=data.get('reward_relation', 0),
            reward_items=data.get('reward_items', ''),
            given_gold=data.get('given_gold', 0),
            given_item=data.get('given_item', ''),
            given_item_count=data.get('given_item_count', 0),
            failure_relation=data.get('failure_relation', 0),
            description=data.get('description', ''),
            target_desc=data.get('target_desc', ''),
            extra_data=data.get('extra_data', {}),
        )
