# --- src/task/display.py ---
"""
任务展示数据结构
用于 sidebar 等UI组件渲染
"""


class TaskDisplayData:
    """
    单个任务的展示数据结构
    用于 sidebar 等UI组件渲染
    
    设计原则：
    - 与 TaskBase.to_display_data() 配合使用
    - 提供UI渲染所需的全部字段
    - 支持转换为字典供模板引擎使用
    """
    def __init__(self, task_type: str, text: str, 
                 progress: str = "", is_complete: bool = False, 
                 is_urgent: bool = False,
                 # 详情弹窗用字段
                 target_npc: str = "",           # 对象（目标NPC名字）
                 objective: str = "",            # 任务目标（完成条件）
                 reward: str = "",               # 任务成果（奖励）
                 deadline_days: int = 0,         # 期限（剩余天数，0表示无期限）
                 description: str = ""):         # 详细描述
        self.type = task_type           # 任务类型：MAIN/SURVIVAL/INTEL/FACTION
        self.text = text                # 任务描述文本（sidebar显示用）
        self.progress = progress        # 进度文本，如 "1/3" 或 ""
        self.is_complete = is_complete  # 是否已完成待交付
        self.is_urgent = is_urgent      # 是否紧急（生存任务默认紧急）
        
        # 详情弹窗用字段
        self.target_npc = target_npc    # 对象
        self.objective = objective      # 任务目标
        self.reward = reward            # 任务成果
        self.deadline_days = deadline_days  # 期限
        self.description = description  # 详细描述
    
    def to_dict(self):
        """转换为字典，方便 UI 层使用"""
        return {
            'type': self.type,
            'text': self.text,
            'progress': self.progress,
            'is_complete': self.is_complete,
            'is_urgent': self.is_urgent,
            'target_npc': self.target_npc,
            'objective': self.objective,
            'reward': self.reward,
            'deadline_days': self.deadline_days,
            'description': self.description,
        }
