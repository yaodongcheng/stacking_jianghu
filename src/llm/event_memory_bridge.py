# src/llm/event_memory_bridge.py
"""
事件记忆桥接器 - 将游戏事件注入NPC记忆系统
============================================

职责：
1. 监听游戏事件（战斗、交易、剧情等）
2. 识别相关NPC（当事人、目击者、关系人）
3. 将事件转化为NPC记忆并注入

设计原则：
- 当事人：完整记忆，高重要性
- 目击者：部分记忆（看到了什么），中重要性
- 关系人：听说/传闻，低重要性
"""

import time
import math
from typing import List, Dict, Optional, Any, Set, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

if TYPE_CHECKING:
    from src.entities.npc import NPC
    from src.live_news_system import LiveNewsItem


class EventRole(Enum):
    """NPC在事件中的角色"""
    PARTICIPANT = "participant"     # 当事人（直接参与）
    WITNESS = "witness"            # 目击者（在场看到）
    RELATED = "related"            # 关系人（当事人的朋友/敌人/同事）
    HEARSAY = "hearsay"            # 传闻（通过传播得知）


@dataclass
class EventMemoryData:
    """事件记忆数据"""
    event_type: str           # 事件类型
    description: str          # 事件描述
    importance: int = 3       # 重要性 1-5
    related_npc_ids: Set[int] = field(default_factory=set)  # 相关NPC ID
    tags: List[str] = field(default_factory=list)
    location: str = ""        # 发生地点
    timestamp: float = field(default_factory=time.time)


class EventMemoryBridge:
    """
    事件记忆桥接器
    
    单例模式，全局管理事件到记忆的转换
    """
    
    _instance = None
    
    # 目击范围（像素）
    WITNESS_RADIUS = 400
    
    # 传闻传播概率
    HEARSAY_PROBABILITY = 0.3
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        if EventMemoryBridge._instance is not None:
            return
        
        # 缓存 - 避免重复处理
        self._processed_events: Set[str] = set()
        self._max_cache = 1000
        
        print("[EventMemoryBridge] 初始化完成")
    
    # ═══════════════════════════════════════════════════════════════
    # 1. 世界事件（AI Director生成的剧情）
    # ═══════════════════════════════════════════════════════════════
    
    def inject_world_event(self, news_item: 'LiveNewsItem', 
                           involved_npcs: List['NPC'],
                           all_npcs: List['NPC'] = None,
                           event_location: tuple = None):
        """
        将AI Director生成的世界事件注入相关NPC记忆
        
        Args:
            news_item: LiveNewsItem 新闻事件
            involved_npcs: 直接参与的NPC列表
            all_npcs: 所有NPC（用于找目击者和关系人）
            event_location: 事件发生位置 (x, y)
        """
        # 使用 created_tick 而不是 timestamp (LiveNewsItem 没有 timestamp 属性)
        created_tick = getattr(news_item, 'created_tick', 0) or int(time.time())
        event_id = f"world_{created_tick}_{news_item.headline[:20]}"
        if event_id in self._processed_events:
            return
        self._processed_events.add(event_id)
        self._trim_cache()
        
        # 为当事人添加完整记忆
        for npc in involved_npcs:
            self._add_memory_to_npc(
                npc=npc,
                role=EventRole.PARTICIPANT,
                event_type="WORLD_EVENT",
                description=f"【重大事件】{news_item.headline}：{news_item.description}",
                importance=4,
                related_npc_ids={n.id for n in involved_npcs if n.id != npc.id},
                tags=["世界事件", news_item.category.value if hasattr(news_item.category, 'value') else str(news_item.category)]
            )
        
        if all_npcs and event_location:
            # 找目击者
            witnesses = self._find_witnesses(event_location, all_npcs, 
                                             exclude_ids={n.id for n in involved_npcs})
            for witness in witnesses:
                self._add_memory_to_npc(
                    npc=witness,
                    role=EventRole.WITNESS,
                    event_type="WITNESSED_EVENT",
                    description=f"【亲眼所见】我看到{news_item.headline}",
                    importance=2,
                    related_npc_ids={n.id for n in involved_npcs},
                    tags=["目击", "世界事件"]
                )
            
            # 找关系人（当事人的朋友/敌人）
            related = self._find_related_npcs(involved_npcs, all_npcs,
                                               exclude_ids={n.id for n in involved_npcs} | {w.id for w in witnesses})
            for rel_npc, relation_info in related:
                self._add_memory_to_npc(
                    npc=rel_npc,
                    role=EventRole.RELATED,
                    event_type="HEARD_EVENT",
                    description=f"【听说】{relation_info}卷入了一件事：{news_item.headline}",
                    importance=2,
                    related_npc_ids={n.id for n in involved_npcs},
                    tags=["传闻", "关系人"]
                )
        
        print(f"[EventMemoryBridge] 世界事件已注入 {len(involved_npcs)} 个当事人记忆")
    
    # ═══════════════════════════════════════════════════════════════
    # 2. 战斗事件
    # ═══════════════════════════════════════════════════════════════
    
    def inject_combat_event(self, winner: 'NPC', loser: 'NPC', 
                            combat_result: str,
                            all_npcs: List['NPC'] = None,
                            location: tuple = None):
        """
        记录战斗事件到相关NPC记忆
        
        Args:
            winner: 胜者
            loser: 败者
            combat_result: 结果描述（如 "重伤"、"死亡"、"逃跑"）
            all_npcs: 所有NPC
            location: 战斗位置
        """
        event_id = f"combat_{int(time.time())}_{winner.id}_{loser.id}"
        if event_id in self._processed_events:
            return
        self._processed_events.add(event_id)
        self._trim_cache()
        
        # 胜者记忆
        self._add_memory_to_npc(
            npc=winner,
            role=EventRole.PARTICIPANT,
            event_type="COMBAT_WON",
            description=f"我打败了{loser.name}，对方{combat_result}",
            importance=4,
            related_npc_ids={loser.id},
            tags=["战斗", "胜利"],
            related_npc_name=loser.name
        )
        
        # 败者记忆（如果还活着）
        from src.definitions import SAFETY_DEAD
        if loser.safety != SAFETY_DEAD:
            self._add_memory_to_npc(
                npc=loser,
                role=EventRole.PARTICIPANT,
                event_type="COMBAT_LOST",
                description=f"我被{winner.name}打败了，{combat_result}",
                importance=5,  # 更重要，因为这是负面经历
                related_npc_ids={winner.id},
                tags=["战斗", "失败"],
                related_npc_name=winner.name
            )
        
        # 目击者
        if all_npcs and location:
            witnesses = self._find_witnesses(location, all_npcs,
                                              exclude_ids={winner.id, loser.id})
            for witness in witnesses:
                self._add_memory_to_npc(
                    npc=witness,
                    role=EventRole.WITNESS,
                    event_type="WITNESSED_COMBAT",
                    description=f"我看到{winner.name}打败了{loser.name}",
                    importance=2,
                    related_npc_ids={winner.id, loser.id},
                    tags=["目击", "战斗"]
                )
            
            # 关系人
            participants = [winner, loser]
            related = self._find_related_npcs(participants, all_npcs,
                                               exclude_ids={winner.id, loser.id} | {w.id for w in witnesses})
            for rel_npc, relation_info in related:
                self._add_memory_to_npc(
                    npc=rel_npc,
                    role=EventRole.RELATED,
                    event_type="HEARD_COMBAT",
                    description=f"听说{relation_info}和别人打架了",
                    importance=1,
                    related_npc_ids={winner.id, loser.id},
                    tags=["传闻", "战斗"]
                )
        
        print(f"[EventMemoryBridge] 战斗事件已记录: {winner.name} vs {loser.name}")
    
    # ═══════════════════════════════════════════════════════════════
    # 3. 交易/交互事件
    # ═══════════════════════════════════════════════════════════════
    
    def inject_trade_event(self, buyer: 'NPC', seller: 'NPC',
                           item_name: str, item_count: int, price: int):
        """记录交易事件"""
        event_id = f"trade_{int(time.time())}_{buyer.id}_{seller.id}"
        if event_id in self._processed_events:
            return
        self._processed_events.add(event_id)
        
        # 买方记忆
        self._add_memory_to_npc(
            npc=buyer,
            role=EventRole.PARTICIPANT,
            event_type="TRADE_BUY",
            description=f"我从{seller.name}那里买了{item_count}个{item_name}，花了{price}文",
            importance=2,
            related_npc_ids={seller.id},
            tags=["交易", "购买"],
            related_npc_name=seller.name
        )
        
        # 卖方记忆
        self._add_memory_to_npc(
            npc=seller,
            role=EventRole.PARTICIPANT,
            event_type="TRADE_SELL",
            description=f"我卖给{buyer.name}{item_count}个{item_name}，赚了{price}文",
            importance=2,
            related_npc_ids={buyer.id},
            tags=["交易", "出售"],
            related_npc_name=buyer.name
        )
    
    def inject_help_event(self, helper: 'NPC', helped: 'NPC', help_type: str):
        """
        记录帮助事件（如治疗、救援等）
        
        Args:
            helper: 帮助者
            helped: 被帮助者
            help_type: 帮助类型（如 "治疗"、"救援"、"赠送物资"）
        """
        event_id = f"help_{int(time.time())}_{helper.id}_{helped.id}"
        if event_id in self._processed_events:
            return
        self._processed_events.add(event_id)
        
        # 帮助者记忆
        self._add_memory_to_npc(
            npc=helper,
            role=EventRole.PARTICIPANT,
            event_type="HELPED_SOMEONE",
            description=f"我{help_type}了{helped.name}",
            importance=3,
            related_npc_ids={helped.id},
            tags=["帮助", help_type],
            related_npc_name=helped.name
        )
        
        # 被帮助者记忆（更重要）
        self._add_memory_to_npc(
            npc=helped,
            role=EventRole.PARTICIPANT,
            event_type="RECEIVED_HELP",
            description=f"{helper.name}{help_type}了我，这份恩情我记下了",
            importance=4,
            related_npc_ids={helper.id},
            tags=["被帮助", help_type],
            related_npc_name=helper.name
        )
    
    # ═══════════════════════════════════════════════════════════════
    # 4. 任务/剧情事件
    # ═══════════════════════════════════════════════════════════════
    
    def inject_quest_event(self, quest_id: str, quest_name: str,
                           outcome: str,  # "success", "fail", "neutral"
                           involved_npcs: List['NPC'],
                           player_choice: str = ""):
        """
        记录任务/剧情事件
        
        Args:
            quest_id: 任务ID
            quest_name: 任务名称
            outcome: 结果
            involved_npcs: 涉及的NPC
            player_choice: 玩家选择的描述
        """
        event_id = f"quest_{quest_id}_{int(time.time())}"
        if event_id in self._processed_events:
            return
        self._processed_events.add(event_id)
        
        outcome_desc = {
            "success": "成功解决",
            "fail": "失败告终",
            "neutral": "不了了之"
        }.get(outcome, outcome)
        
        for npc in involved_npcs:
            desc = f"【剧情】「{quest_name}」{outcome_desc}"
            if player_choice:
                desc += f"，玩家选择了{player_choice}"
            
            self._add_memory_to_npc(
                npc=npc,
                role=EventRole.PARTICIPANT,
                event_type="QUEST_EVENT",
                description=desc,
                importance=4,
                related_npc_ids={n.id for n in involved_npcs if n.id != npc.id},
                tags=["剧情", quest_name, outcome]
            )
        
        print(f"[EventMemoryBridge] 任务事件已注入: {quest_name} -> {outcome}")
    
    # ═══════════════════════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════════════════════
    
    # ═══════════════════════════════════════════════════════════════
    # 关系影响配置（双轨制核心）
    # ═══════════════════════════════════════════════════════════════
    
    # 事件类型 → (当事人A对B的好感变化, 当事人B对A的好感变化)
    # 正数=好感增加，负数=好感减少
    AFFINITY_CHANGES = {
        # 战斗事件
        "COMBAT_WON": (-15, 0),      # 胜者对败者: -15（打败了对方，可能蔑视）
        "COMBAT_LOST": (-30, 0),     # 败者对胜者: -30（被打败，仇恨）
        "WITNESSED_COMBAT": (0, 0),  # 目击者不改变关系
        "HEARD_COMBAT": (0, 0),      # 传闻不改变关系
        
        # 帮助事件
        "HELPED_SOMEONE": (5, 0),    # 帮助者对被帮助者: +5
        "RECEIVED_HELP": (20, 0),    # 被帮助者对帮助者: +20
        "HELPED_BY": (25, 0),        # 被帮助（兼容旧格式）
        
        # 交易事件
        "TRADE_BUY": (2, 0),         # 买家对卖家: +2
        "TRADE_SELL": (2, 0),        # 卖家对买家: +2
        
        # 世界事件
        "WORLD_EVENT": (0, 0),       # 世界事件一般不直接改变关系
        "WITNESSED_EVENT": (0, 0),
        "HEARD_EVENT": (0, 0),
        
        # 任务事件
        "QUEST_EVENT": (0, 0),       # 任务事件需要根据具体情况判断
    }
    
    def _add_memory_to_npc(self, npc: 'NPC', role: EventRole,
                           event_type: str, description: str,
                           importance: int, related_npc_ids: Set[int],
                           tags: List[str], related_npc_name: str = "",
                           location: str = ""):
        """
        向NPC添加记忆（同时更新两个记忆系统）
        
        【双轨制】：
        - 轨道1: 记忆系统（可遗忘）
        - 轨道2: 关系分数（永久）
        
        即使记忆被淡忘，关系分数的变化会永久保留。
        NPC可能"不记得具体发生了什么"，但"就是对某人有好感/敌意"。
        """
        # ═══════════════════════════════════════════════════════════════
        # 轨道1: 记忆系统（可遗忘）
        # ═══════════════════════════════════════════════════════════════
        
        # 1. 更新NPC自带的简易记忆系统（用于游戏逻辑）
        if hasattr(npc, 'add_memory'):
            primary_target_id = next(iter(related_npc_ids), None)
            npc.add_memory(
                event_type=event_type,
                target_id=primary_target_id,
                target_name=related_npc_name,
                description=description,
                importance=importance
            )
        
        # ═══════════════════════════════════════════════════════════════
        # 轨道2: 关系分数（永久）
        # ═══════════════════════════════════════════════════════════════
        
        # 只有当事人才更新关系分数（目击者、传闻不影响）
        if role == EventRole.PARTICIPANT and related_npc_ids:
            affinity_delta, _ = self.AFFINITY_CHANGES.get(event_type, (0, 0))
            
            if affinity_delta != 0 and hasattr(npc, 'modify_affinity'):
                for target_id in related_npc_ids:
                    # 根据重要性调整关系变化幅度
                    scaled_delta = int(affinity_delta * (importance / 3.0))
                    npc.modify_affinity(target_id, scaled_delta)
                    print(f"[EventMemoryBridge][双轨制] {npc.name} 对 #{target_id} 关系变化: {scaled_delta}")
        
        # ═══════════════════════════════════════════════════════════════
        # 继续: 更新LLM记忆系统（用于AI对话）
        # ═══════════════════════════════════════════════════════════════
        
        # 2. 更新LLM记忆系统（用于AI对话）
        try:
            from .npc_memory import MemoryManager
            memory_mgr = MemoryManager.get_instance()
            memory_sys = memory_mgr.get_npc_memory(npc.id, npc.name)
            
            if role == EventRole.PARTICIPANT:
                memory_sys.add_event_memory(
                    event_desc=description,
                    importance=importance,
                    involved_npcs=[related_npc_name] if related_npc_name else []
                )
            elif role == EventRole.WITNESS:
                memory_sys.add_memory(
                    content=description,
                    memory_type="event",
                    importance=importance,
                    tags=tags
                )
            elif role in [EventRole.RELATED, EventRole.HEARSAY]:
                memory_sys.add_memory(
                    content=description,
                    memory_type="knowledge",
                    importance=importance,
                    tags=tags
                )
        except Exception as e:
            print(f"[EventMemoryBridge] LLM记忆更新失败: {e}")
    
    def _find_witnesses(self, location: tuple, all_npcs: List['NPC'],
                        exclude_ids: Set[int]) -> List['NPC']:
        """
        找到事件位置附近的目击者
        
        Args:
            location: (x, y) 事件位置
            all_npcs: 所有NPC
            exclude_ids: 排除的NPC ID
            
        Returns:
            目击者列表
        """
        witnesses = []
        cx, cy = location
        
        for npc in all_npcs:
            if npc.id in exclude_ids:
                continue
            if getattr(npc, 'job', '') == 'PLAYER':
                continue
            
            # 检查是否存活
            from src.definitions import SAFETY_DEAD, SAFETY_EXILED
            if npc.safety in [SAFETY_DEAD, SAFETY_EXILED]:
                continue
            
            # 计算距离
            dist = math.hypot(npc.rect.centerx - cx, npc.rect.centery - cy)
            if dist <= self.WITNESS_RADIUS:
                witnesses.append(npc)
        
        return witnesses
    
    def _find_related_npcs(self, participants: List['NPC'], 
                            all_npcs: List['NPC'],
                            exclude_ids: Set[int]) -> List[tuple]:
        """
        找到与当事人有关系的NPC
        
        Returns:
            List of (npc, relation_description)
        """
        related = []
        
        for participant in participants:
            # 检查同组织成员
            participant_org = getattr(participant, 'org_id', None)
            if participant_org and participant_org != 'NONE':
                for npc in all_npcs:
                    if npc.id in exclude_ids:
                        continue
                    if getattr(npc, 'job', '') == 'PLAYER':
                        continue
                    
                    npc_org = getattr(npc, 'org_id', None)
                    if npc_org == participant_org:
                        relation = f"我的同伴{participant.name}"
                        related.append((npc, relation))
                        exclude_ids.add(npc.id)
            
            # 检查好感度高的NPC（朋友）
            affinity_dict = getattr(participant, 'affinity', {})
            for target_id, affinity in affinity_dict.items():
                if target_id in exclude_ids:
                    continue
                if abs(affinity) >= 30:  # 好感度绝对值大于30才算有关系
                    # 找到这个NPC
                    for npc in all_npcs:
                        if npc.id == target_id:
                            if affinity > 0:
                                relation = f"我的朋友{participant.name}"
                            else:
                                relation = f"我的死对头{participant.name}"
                            related.append((npc, relation))
                            exclude_ids.add(npc.id)
                            break
        
        return related
    
    def _trim_cache(self):
        """清理过期缓存"""
        if len(self._processed_events) > self._max_cache:
            # 简单处理：清除一半
            events_list = list(self._processed_events)
            self._processed_events = set(events_list[len(events_list)//2:])


# ═══════════════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════════════

def get_event_memory_bridge() -> EventMemoryBridge:
    """获取事件记忆桥接器实例"""
    return EventMemoryBridge.get_instance()


def inject_world_event(news_item, involved_npcs, all_npcs=None, location=None):
    """快捷方法：注入世界事件"""
    get_event_memory_bridge().inject_world_event(
        news_item, involved_npcs, all_npcs, location
    )


def inject_combat_memory(winner, loser, result, all_npcs=None, location=None):
    """快捷方法：注入战斗记忆"""
    get_event_memory_bridge().inject_combat_event(
        winner, loser, result, all_npcs, location
    )


def inject_trade_memory(buyer, seller, item_name, count, price):
    """快捷方法：注入交易记忆"""
    get_event_memory_bridge().inject_trade_event(
        buyer, seller, item_name, count, price
    )


def inject_help_memory(helper, helped, help_type):
    """快捷方法：注入帮助记忆"""
    get_event_memory_bridge().inject_help_event(helper, helped, help_type)


def inject_quest_memory(quest_id, quest_name, outcome, involved_npcs, player_choice=""):
    """快捷方法：注入任务记忆"""
    get_event_memory_bridge().inject_quest_event(
        quest_id, quest_name, outcome, involved_npcs, player_choice
    )
