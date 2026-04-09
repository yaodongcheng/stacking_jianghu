# --- src/task/intel.py ---
"""
情报委托类

设计依据：tasks.md 阶段三

特点：
- 起幕事件的余韵对话中，当事NPC请求玩家帮忙打听
- 需要收集3条线索碎片
- 每条线索暗示不同的准备方向
- 凑齐3条线索后，触发玩家内心总结
"""

from dataclasses import dataclass, field
from typing import List, Set, Tuple

from .base import TaskBase, TaskCategory, TaskContentType


@dataclass
class IntelQuest(TaskBase):
    """
    情报委托
    
    触发方式：
    - 起幕余韵结束后，当事NPC（FateNode主角NPC）基于听到的威胁请求玩家帮忙打听
    - 发布人 = 当事NPC（不是旁观者）
    """
    # 目标NPC列表（持有线索的3-5个NPC）
    target_npc_ids: List[str] = field(default_factory=list)
    # 线索文本（注入目标NPC的LLM上下文）
    clue_texts: List[str] = field(default_factory=list)
    # 线索暗示的方向（武力/金钱/调查等）
    clue_hints: List[str] = field(default_factory=list)
    # 已收集线索数
    collected_clues: int = 0
    # 已打探过的NPC
    probed_npcs: Set[str] = field(default_factory=set)
    # 凑齐后的内心总结文本
    summary_text: str = ""
    # 对应四幕哪一幕前
    phase_hint: str = ""
    # 关联的 FateNode ID
    fate_node_id: str = ""
    
    def __post_init__(self):
        """初始化后处理"""
        self.category = TaskCategory.INTEL
        self.content_type = TaskContentType.INVESTIGATE
        self.progress_target = 3  # 默认需要收集3条线索
    
    def get_progress_text(self) -> str:
        """获取进度文本"""
        return f"{self.collected_clues}/{self.progress_target}"
    
    def is_npc_target(self, npc_id: str) -> bool:
        """检查NPC是否是目标NPC"""
        return str(npc_id) in [str(nid) for nid in self.target_npc_ids]
    
    def has_probed(self, npc_id: str) -> bool:
        """检查是否已打探过该NPC"""
        return str(npc_id) in self.probed_npcs
    
    def probe_npc(self, npc_id: str) -> Tuple[bool, bool, str]:
        """
        打探NPC
        
        Args:
            npc_id: NPC ID
            
        Returns:
            (是否是目标, 是否获得新线索, 线索文本)
        """
        npc_id_str = str(npc_id)
        self.probed_npcs.add(npc_id_str)
        
        if self.is_npc_target(npc_id):
            # 目标NPC
            idx_list = [str(nid) for nid in self.target_npc_ids]
            idx = idx_list.index(npc_id_str)
            clue_text = self.clue_texts[idx] if idx < len(self.clue_texts) else ""
            
            # 检查是否已收集过（基于NPC顺序）
            if idx >= self.collected_clues:
                self.collected_clues = idx + 1
                self.progress = self.collected_clues
                if self.is_complete():
                    self.status = TaskStatus.READY
                return (True, True, clue_text)
            return (True, False, clue_text)
        else:
            # 非目标NPC
            return (False, False, "我对此事不太了解...")
    
    def get_display_text(self) -> str:
        """获取显示文本"""
        if self.publisher_name:
            return f"{self.publisher_name}：{self.title}"
        return self.title
    
    @classmethod
    def create_from_fate_node(cls, fate_node_id: str, publisher_id: str, 
                               publisher_name: str, title: str,
                               target_npcs: List[str], clues: List[str],
                               hints: List[str] = None) -> 'IntelQuest':
        """
        从 FateNode 创建情报委托
        
        Args:
            fate_node_id: 关联的 FateNode ID
            publisher_id: 发布人NPC ID
            publisher_name: 发布人名称
            title: 任务标题
            target_npcs: 目标NPC列表
            clues: 线索文本列表
            hints: 线索暗示列表
            
        Returns:
            IntelQuest 实例
        """
        from .base import TaskStatus
        task = cls(
            task_id=f"INTEL_{fate_node_id}",
            title=title,
            category=TaskCategory.INTEL,
            content_type=TaskContentType.INVESTIGATE,
            status=TaskStatus.ACTIVE,
            publisher_id=publisher_id,
            publisher_name=publisher_name,
            target_npc_ids=[str(nid) for nid in target_npcs],
            clue_texts=clues,
            clue_hints=hints or [],
            fate_node_id=fate_node_id,
            description=f"打探关于「{title}」的消息",
        )
        return task


# 需要从 base 导入 TaskStatus
from .base import TaskStatus
