# src/llm/npc_memory.py
"""
NPC记忆系统 - 管理短期记忆和长期记忆
基于参考项目的设计，实现记忆压缩和关键事件提取
"""

import json
import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from enum import Enum
from pathlib import Path

from src.utils import log_game_event, resource_path


class MemoryType(Enum):
    """记忆类型"""
    CONVERSATION = "conversation"     # 对话记忆
    EVENT = "event"                   # 事件记忆
    IMPRESSION = "impression"         # 印象（对某人的看法）
    KNOWLEDGE = "knowledge"           # 知识（了解到的信息）
    EMOTION = "emotion"               # 情感体验
    RELATIONSHIP = "relationship"     # 关系变化


class MemoryImportance(Enum):
    """记忆重要性"""
    TRIVIAL = 1      # 琐碎（闲聊）
    MINOR = 2        # 次要
    NORMAL = 3       # 一般
    IMPORTANT = 4    # 重要
    CRITICAL = 5     # 关键（生死攸关、誓言等）


@dataclass
class MemoryEntry:
    """单条记忆"""
    id: str                           # 唯一ID
    memory_type: str                  # 记忆类型
    content: str                      # 记忆内容
    importance: int = 3               # 重要性 1-5
    timestamp: float = 0              # 游戏内时间戳
    real_timestamp: float = 0         # 现实时间戳
    related_npc_id: Optional[int] = None      # 相关NPC ID
    related_npc_name: str = ""        # 相关NPC名字
    emotion: str = "neutral"          # 当时的情绪
    location: str = ""                # 发生地点
    tags: List[str] = field(default_factory=list)  # 标签
    decay_rate: float = 1.0           # 遗忘速率 (越高遗忘越快)
    access_count: int = 0             # 被访问次数
    
    def __post_init__(self):
        if not self.real_timestamp:
            self.real_timestamp = time.time()
        if not self.id:
            self.id = f"mem_{int(self.real_timestamp * 1000)}"
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MemoryEntry':
        """从字典创建"""
        return cls(**data)
    
    def get_age_days(self, current_time: float = None) -> float:
        """获取记忆年龄（天）"""
        if current_time is None:
            current_time = time.time()
        return (current_time - self.real_timestamp) / 86400
    
    def calculate_relevance(self, query_tags: List[str] = None) -> float:
        """
        计算记忆相关性分数
        
        Args:
            query_tags: 查询相关的标签
            
        Returns:
            float: 0-1的相关性分数
        """
        score = self.importance / 5.0
        
        # 访问次数提升相关性
        score += min(0.2, self.access_count * 0.02)
        
        # 标签匹配
        if query_tags and self.tags:
            match_count = len(set(query_tags) & set(self.tags))
            score += match_count * 0.1
        
        # 时间衰减
        age = self.get_age_days()
        decay = 1.0 / (1.0 + age * self.decay_rate * 0.1)
        score *= decay
        
        return min(1.0, score)


class NPCMemorySystem:
    """
    NPC记忆管理系统
    
    管理单个NPC的所有记忆，支持:
    - 短期记忆（最近对话）
    - 长期记忆（重要事件）
    - 记忆压缩（定期将短期记忆总结为长期记忆）
    - 记忆检索（根据上下文查找相关记忆）
    """
    
    # 记忆容量限制
    SHORT_TERM_CAPACITY = 20      # 短期记忆容量
    LONG_TERM_CAPACITY = 100      # 长期记忆容量
    
    # 记忆文件存储路径（使用 resource_path 确保打包后也能正常工作）
    MEMORY_DIR = Path(resource_path("data/npc_memories"))
    
    def __init__(self, npc_id: int, npc_name: str = ""):
        self.npc_id = npc_id
        self.npc_name = npc_name
        
        # 短期记忆（最近的对话和事件）
        self.short_term: List[MemoryEntry] = []
        
        # 长期记忆（重要的、经过压缩的记忆）
        self.long_term: List[MemoryEntry] = []
        
        # 对其他NPC的印象
        # {npc_id: {"name": str, "impression": str, "affinity": int, "last_interaction": float}}
        self.impressions: Dict[int, Dict] = {}
        
        # 核心信念/原则（不会遗忘）
        self.core_beliefs: List[str] = []
        
        # 记忆压缩计数器
        self._compression_counter = 0
        self._compression_threshold = 10  # 每10条新记忆触发一次压缩
        
        # 加载已保存的记忆
        self._load_memories()
    
    # ═══════════════════════════════════════════════════════════════
    # 记忆添加
    # ═══════════════════════════════════════════════════════════════
    
    def add_memory(self, content: str, memory_type: str = "conversation",
                   importance: int = 3, related_npc_id: int = None,
                   related_npc_name: str = "", emotion: str = "neutral",
                   location: str = "", tags: List[str] = None) -> MemoryEntry:
        """
        添加一条新记忆
        
        Args:
            content: 记忆内容
            memory_type: 记忆类型
            importance: 重要性 1-5
            related_npc_id: 相关NPC ID
            related_npc_name: 相关NPC名字
            emotion: 当时情绪
            location: 地点
            tags: 标签列表
            
        Returns:
            MemoryEntry: 创建的记忆条目
        """
        entry = MemoryEntry(
            id="",
            memory_type=memory_type,
            content=content,
            importance=importance,
            timestamp=time.time(),
            related_npc_id=related_npc_id,
            related_npc_name=related_npc_name,
            emotion=emotion,
            location=location,
            tags=tags or []
        )
        
        # 根据重要性决定存储位置
        if importance >= 4:
            # 重要记忆直接进入长期记忆
            self.long_term.append(entry)
            self._trim_long_term()
        else:
            # 一般记忆进入短期记忆
            self.short_term.append(entry)
            self._trim_short_term()
        
        # 更新压缩计数器
        self._compression_counter += 1
        if self._compression_counter >= self._compression_threshold:
            self._compress_memories()
            self._compression_counter = 0
        
        log_game_event(f"[Memory] {self.npc_name} 添加记忆: {content[:30]}...", tag="MEMORY")
        return entry
    
    def add_conversation_memory(self, speaker: str, content: str, 
                                is_player: bool = False,
                                emotion_response: str = "neutral") -> MemoryEntry:
        """
        添加对话记忆
        
        Args:
            speaker: 说话者名字
            content: 对话内容
            is_player: 是否是玩家说的
            emotion_response: NPC的情绪反应
        """
        prefix = "玩家对我说" if is_player else f"{speaker}说"
        memory_content = f"{prefix}：「{content}」"
        
        return self.add_memory(
            content=memory_content,
            memory_type="conversation",
            importance=2 if is_player else 1,
            emotion=emotion_response,
            tags=["对话", "玩家" if is_player else speaker]
        )
    
    def add_event_memory(self, event_desc: str, importance: int = 3,
                         involved_npcs: List[str] = None) -> MemoryEntry:
        """
        添加事件记忆
        
        Args:
            event_desc: 事件描述
            importance: 重要性
            involved_npcs: 涉及的NPC名字列表
        """
        tags = ["事件"]
        if involved_npcs:
            tags.extend(involved_npcs)
        
        return self.add_memory(
            content=event_desc,
            memory_type="event",
            importance=importance,
            tags=tags
        )
    
    # ═══════════════════════════════════════════════════════════════
    # 印象管理
    # ═══════════════════════════════════════════════════════════════
    
    def update_impression(self, target_npc_id: int, target_name: str,
                          impression: str = None, affinity_delta: int = 0):
        """
        更新对某NPC的印象
        
        Args:
            target_npc_id: 目标NPC ID
            target_name: 目标NPC名字
            impression: 印象描述（可选，会追加到现有印象）
            affinity_delta: 好感度变化
        """
        if target_npc_id not in self.impressions:
            self.impressions[target_npc_id] = {
                "name": target_name,
                "impression": "",
                "affinity": 0,
                "last_interaction": time.time(),
                "interaction_count": 0
            }
        
        imp = self.impressions[target_npc_id]
        imp["name"] = target_name
        imp["last_interaction"] = time.time()
        imp["interaction_count"] = imp.get("interaction_count", 0) + 1
        
        if impression:
            # 追加新印象（保持最近的印象在前）
            if imp["impression"]:
                imp["impression"] = f"{impression}；{imp['impression']}"
            else:
                imp["impression"] = impression
            # 限制印象长度
            if len(imp["impression"]) > 500:
                imp["impression"] = imp["impression"][:500] + "..."
        
        if affinity_delta:
            imp["affinity"] = max(-100, min(100, imp["affinity"] + affinity_delta))
    
    def get_impression(self, target_npc_id: int) -> Optional[Dict]:
        """获取对某NPC的印象"""
        return self.impressions.get(target_npc_id)
    
    def get_impression_text(self, target_npc_id: int) -> str:
        """获取印象的文本描述"""
        imp = self.impressions.get(target_npc_id)
        if not imp:
            return "我不认识这个人。"
        
        affinity = imp.get("affinity", 0)
        if affinity > 50:
            relation = "很亲近的朋友"
        elif affinity > 20:
            relation = "友善的熟人"
        elif affinity > -20:
            relation = "普通相识"
        elif affinity > -50:
            relation = "不太喜欢的人"
        else:
            relation = "讨厌的人"
        
        impression = imp.get("impression", "没什么特别印象")
        return f"【{imp['name']}】是我的{relation}。{impression}"
    
    # ═══════════════════════════════════════════════════════════════
    # 记忆检索
    # ═══════════════════════════════════════════════════════════════
    
    def retrieve_relevant_memories(self, query: str = "", 
                                   related_npc_id: int = None,
                                   tags: List[str] = None,
                                   max_count: int = 5) -> List[MemoryEntry]:
        """
        检索相关记忆
        
        Args:
            query: 查询关键词
            related_npc_id: 相关NPC ID
            tags: 相关标签
            max_count: 最大返回数量
            
        Returns:
            List[MemoryEntry]: 相关记忆列表
        """
        candidates = []
        
        # 合并短期和长期记忆
        all_memories = self.short_term + self.long_term
        
        for mem in all_memories:
            score = 0
            
            # 关键词匹配
            if query and query in mem.content:
                score += 0.5
            
            # NPC匹配
            if related_npc_id and mem.related_npc_id == related_npc_id:
                score += 0.3
            
            # 标签匹配
            if tags and mem.tags:
                match_count = len(set(tags) & set(mem.tags))
                score += match_count * 0.2
            
            # 基础相关性
            score += mem.calculate_relevance(tags)
            
            if score > 0:
                candidates.append((score, mem))
        
        # 按分数排序
        candidates.sort(key=lambda x: x[0], reverse=True)
        
        # 更新访问计数
        results = []
        for _, mem in candidates[:max_count]:
            mem.access_count += 1
            results.append(mem)
        
        return results
    
    def get_recent_memories(self, count: int = 5, limit: int = None) -> List[MemoryEntry]:
        """获取最近的记忆
        
        Args:
            count: 要获取的记忆数量（兼容旧代码）
            limit: 同count，作为别名支持
        """
        # 支持limit作为count的别名
        if limit is not None:
            count = limit
        all_memories = sorted(
            self.short_term + self.long_term,
            key=lambda m: m.real_timestamp,
            reverse=True
        )
        return all_memories[:count]
    
    def get_memories_about_player(self, max_count: int = 10) -> List[MemoryEntry]:
        """获取与玩家相关的记忆"""
        return self.retrieve_relevant_memories(tags=["玩家"], max_count=max_count)
    
    # ═══════════════════════════════════════════════════════════════
    # 记忆格式化（用于LLM提示词）
    # ═══════════════════════════════════════════════════════════════
    
    def format_memories_for_prompt(self, max_entries: int = 10,
                                   include_impressions: bool = True) -> str:
        """
        将记忆格式化为LLM提示词使用的文本
        
        Args:
            max_entries: 最大条目数
            include_impressions: 是否包含印象
            
        Returns:
            str: 格式化的记忆文本
        """
        lines = []
        
        # 核心信念
        if self.core_beliefs:
            lines.append("【核心信念】")
            for belief in self.core_beliefs[:3]:
                lines.append(f"- {belief}")
            lines.append("")
        
        # 重要记忆
        important_memories = [m for m in self.long_term if m.importance >= 4]
        if important_memories:
            lines.append("【重要记忆】")
            for mem in important_memories[:5]:
                lines.append(f"- {mem.content}")
            lines.append("")
        
        # 最近记忆
        recent = self.get_recent_memories(max_entries)
        if recent:
            lines.append("【最近记忆】")
            for mem in recent:
                prefix = f"[{mem.memory_type}]" if mem.memory_type != "conversation" else ""
                lines.append(f"- {prefix}{mem.content}")
            lines.append("")
        
        # 人际印象
        if include_impressions and self.impressions:
            lines.append("【我认识的人】")
            for npc_id, imp in list(self.impressions.items())[:5]:
                affinity = imp.get("affinity", 0)
                if affinity > 20:
                    relation = "友善"
                elif affinity < -20:
                    relation = "敌意"
                else:
                    relation = "中立"
                lines.append(f"- {imp['name']}({relation}): {imp.get('impression', '无特别印象')[:50]}")
        
        return "\n".join(lines)
    
    def format_conversation_history(self, max_turns: int = 5) -> List[Dict]:
        """
        格式化对话历史为OpenAI格式
        
        Returns:
            List[Dict]: [{"role": "user/assistant", "content": "..."}]
        """
        history = []
        
        # 筛选对话记忆
        conv_memories = [m for m in self.short_term 
                        if m.memory_type == "conversation"]
        
        # 取最近的对话
        recent_convs = sorted(conv_memories, 
                             key=lambda m: m.real_timestamp)[-max_turns*2:]
        
        for mem in recent_convs:
            if "玩家" in mem.tags or "玩家对我说" in mem.content:
                role = "user"
            else:
                role = "assistant"
            
            # 提取对话内容
            content = mem.content
            if "「" in content and "」" in content:
                content = content[content.find("「")+1:content.find("」")]
            
            history.append({"role": role, "content": content})
        
        return history
    
    # ═══════════════════════════════════════════════════════════════
    # 记忆压缩与遗忘
    # ═══════════════════════════════════════════════════════════════
    
    def _compress_memories(self):
        """
        压缩记忆：将短期记忆中的重要内容提取到长期记忆
        """
        if len(self.short_term) < 5:
            return
        
        # 找出重要的短期记忆
        important_short = [m for m in self.short_term if m.importance >= 3]
        
        for mem in important_short:
            # 将重要记忆复制到长期记忆
            if mem not in self.long_term:
                mem.importance = max(mem.importance, 3)  # 确保至少为3
                self.long_term.append(mem)
        
        # 清理短期记忆中的旧记忆
        self._trim_short_term()
        self._trim_long_term()
        
        print(f"[Memory] {self.npc_name} 记忆压缩完成: 短期{len(self.short_term)} 长期{len(self.long_term)}")
    
    def condense_memories_with_llm(self, llm_client=None, target_npc_id: int = None) -> Optional[str]:
        """
        使用LLM将关于某人/某事的多条记忆凝练成一句核心印象
        
        Args:
            llm_client: LLM客户端（如果没有则尝试使用默认配置）
            target_npc_id: 要凝练的目标NPC（如果为None则凝练所有近期记忆）
            
        Returns:
            str: 凝练后的印象文本，或None如果失败
        """
        # 收集需要凝练的记忆
        if target_npc_id:
            memories_to_condense = [
                m for m in (self.short_term + self.long_term)
                if m.related_npc_id == target_npc_id
            ]
        else:
            # 凝练最近的记忆
            memories_to_condense = sorted(
                self.short_term + self.long_term,
                key=lambda m: m.real_timestamp,
                reverse=True
            )[:15]
        
        if len(memories_to_condense) < 3:
            return None  # 记忆太少，不需要凝练
        
        # 构建凝练prompt
        memory_texts = [m.content for m in memories_to_condense[:10]]
        memory_list = "\n".join([f"- {t}" for t in memory_texts])
        
        prompt = f"""你是{self.npc_name}的内心独白。
请将以下记忆凝练成一句简短的核心印象（不超过30字）：

【记忆片段】
{memory_list}

要求：
1. 用第一人称
2. 提炼出最核心的情感或判断
3. 语言简洁，像内心的一个念头
4. 只输出凝练后的一句话，不要解释

例如："这个人救过我的命，我欠他一份恩情。"
"""
        
        # 尝试调用LLM
        try:
            if llm_client is None:
                # 使用默认配置调用
                condensed = self._call_llm_for_condensation(prompt)
            else:
                condensed = llm_client.generate(prompt)
            
            if condensed:
                # 存储凝练结果
                if target_npc_id:
                    self.update_impression(
                        target_npc_id=target_npc_id,
                        target_name=memories_to_condense[0].related_npc_name or f"NPC#{target_npc_id}",
                        impression=condensed.strip()
                    )
                else:
                    # 添加为核心信念
                    if len(self.core_beliefs) < 5:
                        self.core_beliefs.append(condensed.strip())
                    else:
                        self.core_beliefs[-1] = condensed.strip()
                
                print(f"[Memory] {self.npc_name} 记忆凝练: {condensed.strip()}")
                return condensed.strip()
                
        except Exception as e:
            print(f"[Memory] 记忆凝练失败: {e}")
        
        return None
    
    def _call_llm_for_condensation(self, prompt: str) -> Optional[str]:
        """调用LLM进行记忆凝练（同步版本）"""
        try:
            from src.llm.config import LLMConfig
            import requests
            
            config = LLMConfig.get_instance()
            if not config.is_enabled():
                return None
            
            headers = {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": config.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 100,
                "temperature": 0.7,
            }
            
            # 使用definitions中的超时配置
            from src.definitions import TIMEOUT_MEMORY_QUERY
            
            response = requests.post(
                f"{config.api_base}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=TIMEOUT_MEMORY_QUERY
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('choices', [{}])[0].get('message', {}).get('content', '')
                
        except Exception as e:
            print(f"[Memory] LLM调用失败: {e}")
        
        return None
    
    def _trim_short_term(self):
        """裁剪短期记忆到容量限制"""
        if len(self.short_term) > self.SHORT_TERM_CAPACITY:
            # 按重要性和时间排序，保留重要/新的
            self.short_term.sort(
                key=lambda m: (m.importance, m.real_timestamp),
                reverse=True
            )
            self.short_term = self.short_term[:self.SHORT_TERM_CAPACITY]
    
    def _trim_long_term(self):
        """裁剪长期记忆到容量限制"""
        if len(self.long_term) > self.LONG_TERM_CAPACITY:
            # 按重要性和访问频率排序
            self.long_term.sort(
                key=lambda m: (m.importance, m.access_count, m.real_timestamp),
                reverse=True
            )
            self.long_term = self.long_term[:self.LONG_TERM_CAPACITY]
    
    def apply_time_decay(self, days_passed: int = 1):
        """
        应用时间衰减（每游戏日调用）
        
        Args:
            days_passed: 过去的游戏天数
        """
        # 短期记忆衰减更快
        memories_to_remove = []
        for mem in self.short_term:
            if mem.importance < 2 and mem.get_age_days() > 3:
                memories_to_remove.append(mem)
        
        for mem in memories_to_remove:
            self.short_term.remove(mem)
        
        if memories_to_remove:
            print(f"[Memory] {self.npc_name} 遗忘了 {len(memories_to_remove)} 条记忆")
    
    # ═══════════════════════════════════════════════════════════════
    # 持久化
    # ═══════════════════════════════════════════════════════════════
    
    def _get_save_path(self) -> Path:
        """获取存档路径"""
        self.MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        return self.MEMORY_DIR / f"npc_{self.npc_id}.json"
    
    def save_memories(self):
        """保存记忆到文件"""
        save_path = self._get_save_path()
        
        data = {
            "npc_id": self.npc_id,
            "npc_name": self.npc_name,
            "short_term": [m.to_dict() for m in self.short_term],
            "long_term": [m.to_dict() for m in self.long_term],
            "impressions": self.impressions,
            "core_beliefs": self.core_beliefs,
            "saved_at": time.time()
        }
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[Memory] {self.npc_name} 记忆已保存")
        except Exception as e:
            print(f"[Memory] 保存失败: {e}")
    
    def _load_memories(self):
        """从文件加载记忆"""
        save_path = self._get_save_path()
        
        if not save_path.exists():
            return
        
        try:
            with open(save_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.short_term = [MemoryEntry.from_dict(m) for m in data.get("short_term", [])]
            self.long_term = [MemoryEntry.from_dict(m) for m in data.get("long_term", [])]
            self.impressions = data.get("impressions", {})
            self.core_beliefs = data.get("core_beliefs", [])
            
            print(f"[Memory] {self.npc_name} 记忆已加载: 短期{len(self.short_term)} 长期{len(self.long_term)}")
        except Exception as e:
            print(f"[Memory] 加载失败: {e}")
    
    def clear_all(self):
        """清空所有记忆（慎用）"""
        self.short_term.clear()
        self.long_term.clear()
        self.impressions.clear()
        print(f"[Memory] {self.npc_name} 记忆已清空")
    
    # ═══════════════════════════════════════════════════════════════
    # 调试
    # ═══════════════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict:
        """获取记忆统计"""
        return {
            "npc_id": self.npc_id,
            "npc_name": self.npc_name,
            "short_term_count": len(self.short_term),
            "long_term_count": len(self.long_term),
            "impressions_count": len(self.impressions),
            "core_beliefs_count": len(self.core_beliefs)
        }


# ═══════════════════════════════════════════════════════════════
# 全局记忆管理器
# ═══════════════════════════════════════════════════════════════

class MemoryManager:
    """全局NPC记忆管理器（管理所有NPC的记忆）"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._memories = {}
            cls._instance._condense_counter = 0
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        return cls()
    
    def get_npc_memory(self, npc_id: int, npc_name: str = "") -> NPCMemorySystem:
        """获取或创建NPC的记忆系统"""
        if npc_id not in self._memories:
            self._memories[npc_id] = NPCMemorySystem(npc_id, npc_name)
        return self._memories[npc_id]
    
    def save_all(self):
        """保存所有NPC的记忆"""
        for memory_sys in self._memories.values():
            memory_sys.save_memories()
        print(f"[MemoryManager] 已保存 {len(self._memories)} 个NPC的记忆")
    
    def apply_daily_decay(self):
        """应用每日记忆衰减"""
        for memory_sys in self._memories.values():
            memory_sys.apply_time_decay()
    
    def periodic_condense(self, max_npcs_per_call: int = 3):
        """
        周期性凝练记忆（每次只处理少量NPC，避免卡顿）
        
        建议在游戏空闲时调用（如每天结束、场景切换等）
        
        Args:
            max_npcs_per_call: 每次调用最多处理的NPC数量
        """
        import random
        
        # 选择有足够记忆的NPC进行凝练
        candidates = [
            (npc_id, mem_sys) 
            for npc_id, mem_sys in self._memories.items()
            if len(mem_sys.short_term) + len(mem_sys.long_term) >= 5
        ]
        
        if not candidates:
            return
        
        # 随机选择几个NPC
        selected = random.sample(candidates, min(max_npcs_per_call, len(candidates)))
        
        for npc_id, mem_sys in selected:
            # 尝试凝练记忆（如果LLM可用）
            try:
                mem_sys.condense_memories_with_llm()
            except Exception as e:
                print(f"[MemoryManager] NPC#{npc_id} 凝练失败: {e}")
        
        self._condense_counter += len(selected)
        if self._condense_counter >= 10:
            print(f"[MemoryManager] 已凝练 {self._condense_counter} 个NPC的记忆")
            self._condense_counter = 0
    
    def sync_from_npc_entity(self, npc) -> NPCMemorySystem:
        """
        从NPC实体同步记忆到LLM记忆系统
        
        用于确保 npc.memory (UI) 和 NPCMemorySystem (LLM) 保持一致
        """
        npc_id = npc.id
        npc_name = getattr(npc, 'name', '')
        
        mem_sys = self.get_npc_memory(npc_id, npc_name)
        
        # 从实体记忆同步到LLM记忆
        entity_memories = getattr(npc, 'memory', [])
        
        # 找出LLM系统中没有的记忆
        existing_contents = {m.content for m in mem_sys.short_term + mem_sys.long_term}
        
        for mem in entity_memories:
            desc = mem.get('description', mem.get('desc', ''))
            if desc and desc not in existing_contents:
                # 添加到LLM记忆
                mem_sys.add_memory(
                    content=desc,
                    memory_type="event",
                    importance=mem.get('importance', 2),
                    related_npc_id=mem.get('target_id'),
                    related_npc_name=mem.get('target_name', ''),
                    tags=[mem.get('type', 'UNKNOWN')]
                )
        
        return mem_sys
