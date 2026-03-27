"""
大宋实况 - 全局导演系统 (Director System)
===================================================

核心职责：
1. 世界状态观察 - 收集势力、NPC、玩家的实时数据
2. 戏剧性分析 - 识别高张力的人物关系和势力冲突
3. 事件编排 - 调用LLM选择最合适的事件和演员
4. 实况快照 - 生成小红书/抖音风格的事件快照（含AI配图）

设计理念：
- 不是随机事件，而是"有意义的戏剧"
- 导演知道所有角色的秘密，选择最能推进剧情的冲突
- 像真人秀导演一样，制造戏剧性但不强制结果
"""

import asyncio
import json
import time
import random
import threading
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
import traceback
import re
from pathlib import Path
from src.llm.doubao_image import get_image_generator

from src.ui.event_notification import (
    LiveNewsItem, EventNotificationManager, get_notification_manager,
    NewsCategory, DilemmaType
)
from src.definitions import *
from src.utils import log_game_event

# 对话扩写系统
from src.llm.event_dialog_generator import (
    EventDialogGenerator, EventScriptFull,
    get_event_dialog_generator
)

# UI数据类
from src.ui.live_snapshot_panel import LiveSnapshotData

# 从aistory导入共享类型（避免重复定义）
from src.aistory.shared_types import WorldSnapshot, DramaticTension


@dataclass
class EventCandidate:
    """事件候选 - 导演筛选后的备选"""
    event_type: str
    actors: List[Any]  # NPC列表
    tension_level: DramaticTension
    dramatic_potential: float  # 0-100 戏剧性潜力分数
    reason: str  # 为什么选择这个事件
    context: Dict = field(default_factory=dict)


class WorldObserver:
    """世界观察器 - 收集和分析世界状态"""
    
    def __init__(self):
        self.history: List[WorldSnapshot] = []
        self.max_history = 10
        
    def observe(self, ctx) -> WorldSnapshot:
        """观察当前世界状态，生成快照"""
        snapshot = WorldSnapshot(timestamp=time.time())
        
        # 1. 收集势力状态
        self._observe_factions(ctx, snapshot)
        
        # 2. 收集NPC状态
        self._observe_npcs(ctx, snapshot)
        
        # 3. 收集玩家状态
        self._observe_player(ctx, snapshot)
        
        
        # 保存历史
        self.history.append(snapshot)
        if len(self.history) > self.max_history:
            self.history.pop(0)
            
        return snapshot


    def _observe_factions(self, ctx, snapshot: WorldSnapshot):
        """观察势力状态"""
        faction_war = getattr(ctx, 'faction_war', None)
        if not faction_war:
            return
        
        # 获取所有组织ID
        from src.faction_war_system import ORGANIZATIONS
        org_ids = list(ORGANIZATIONS.keys())
        
        # 势力实力对比 - 基于控制点数量估算
        for org_id in org_ids:
            controlled_points = faction_war.get_org_controlled_points(org_id)
            # 简单用控制点数量作为实力指标
            snapshot.faction_power_balance[org_id] = len(controlled_points) * 10
        
        # 势力间张力（敌对关系）
        relation_mgr = getattr(faction_war, 'relation_manager', None)
        if relation_mgr:
            # 遍历所有组织对检查关系
            for i, org1 in enumerate(org_ids):
                for org2 in org_ids[i+1:]:
                    relation = relation_mgr.get_relation(org1, org2)
                    if relation < 0:  # 敌对
                        key = f"{org1}_vs_{org2}"
                        snapshot.faction_tensions[key] = {
                            'orgs': [org1, org2],
                            'hostility': abs(relation),
                            'at_war': relation <= -50
                        }
        
        # 近期冲突
        # TODO: 从faction_war获取战斗记录
        
        # 3. 收集玩家状态
        self._observe_player(ctx, snapshot)
        
        
        # 保存历史
        self.history.append(snapshot)
        if len(self.history) > self.max_history:
            self.history.pop(0)
            
        return snapshot
    
    def _observe_factions(self, ctx, snapshot: WorldSnapshot):
        """观察势力状态"""
        faction_war = getattr(ctx, 'faction_war', None)
        if not faction_war:
            return
        
        # 获取所有组织ID
        from src.faction_war_system import ORGANIZATIONS
        org_ids = list(ORGANIZATIONS.keys())
        
        # 势力实力对比 - 基于控制点数量估算
        for org_id in org_ids:
            controlled_points = faction_war.get_org_controlled_points(org_id)
            # 简单用控制点数量作为实力指标
            snapshot.faction_power_balance[org_id] = len(controlled_points) * 10
        
        # 势力间张力（敌对关系）
        relation_mgr = getattr(faction_war, 'relation_manager', None)
        if relation_mgr:
            # 遍历所有组织对检查关系
            for i, org1 in enumerate(org_ids):
                for org2 in org_ids[i+1:]:
                    relation = relation_mgr.get_relation(org1, org2)
                    if relation < 0:  # 敌对
                        key = f"{org1}_vs_{org2}"
                        snapshot.faction_tensions[key] = {
                            'orgs': [org1, org2],
                            'hostility': abs(relation),
                            'at_war': relation <= -50
                        }
        
        # 近期冲突
        # TODO: 从faction_war获取战斗记录
    
    def _observe_npcs(self, ctx, snapshot: WorldSnapshot):
        """
        观察NPC状态
        
        【优化】增加NPC记忆和详细状态的收集，让事件生成更贴合世界运转
        """
        from src.entities import NPC
        
        all_cards = getattr(ctx, 'all_cards', [])
        
        # 【优化】获取记忆管理器，用于查询NPC记忆
        memory_mgr = None
        try:
            from src.llm.npc_memory import MemoryManager
            memory_mgr = MemoryManager.get_instance()
        except Exception as e:
            log_game_event(f"[Observer] 记忆管理器加载失败: {e}", tag="DIRECTOR")
        
        for card in all_cards:
            if not isinstance(card, NPC) or card.safety in [SAFETY_DEAD, SAFETY_EXILED]:
                continue
            if getattr(card, 'is_player', False):
                continue
            
            # === 收集NPC基本信息到完整演员池 ===
            emotion_raw = getattr(card, 'emotion', 'NORMAL')
            # 将字符串情绪映射为数值（用于危机检测）
            emotion_value_map = {
                'NORMAL': 50, 'HAPPY': 80, 'SAD': 30, 'ANGRY': 40,
                'DEPRESSED': 15, 'DESPAIR': 5, 'ANXIOUS': 35, 'CONFUSED': 45
            }
            # 兼容旧数据：如果是数值则直接使用，否则查映射表
            if isinstance(emotion_raw, (int, float)):
                emotion = int(emotion_raw)
            else:
                emotion = emotion_value_map.get(str(emotion_raw).upper(), 50)
            hunger = getattr(card, 'hunger', 0)
            # NPC财富通过 money 属性获取（从inventory获取铜钱数量）
            wealth = getattr(card, 'money', 0)
            
            npc_info = {
                'id': card.id,
                'name': card.name,
                'org': getattr(card, 'org_id', ''),
                'power_type': getattr(card, 'power_type', '民'),
                'social_level': getattr(card, 'social_level', 0),
                'job': getattr(card, 'job', ''),
                'emotion': emotion,
                'hunger': hunger,
                'wealth': wealth,
                'status': '正常' if card.safety not in [SAFETY_DOWNED] else '重伤',
            }
            
            # ═══════════════════════════════════════════════════════════════
            # 【优化1】收集NPC的tags标签（用于事件匹配）
            # ═══════════════════════════════════════════════════════════════
            tags = getattr(card, 'tags', [])
            if tags:
                npc_info['tags'] = tags if isinstance(tags, list) else [tags]
            
            # ═══════════════════════════════════════════════════════════════
            # 【优化1.5】收集NPC的人设描述（desc）
            # ═══════════════════════════════════════════════════════════════
            desc = getattr(card, 'desc', '')
            if desc:
                npc_info['desc'] = desc
            
            # ═══════════════════════════════════════════════════════════════
            # 【优化2】收集NPC的记忆摘要（最近重要事件）
            # ═══════════════════════════════════════════════════════════════
            if memory_mgr:
                try:
                    npc_memory = memory_mgr.get_npc_memory(card.id, card.name)
                    if npc_memory:
                        # 获取最近的重要记忆（用于事件生成参考）
                        recent_memories = self._extract_memory_summary(npc_memory)
                        if recent_memories:
                            npc_info['recent_memories'] = recent_memories
                except Exception as e:
                    pass  # 静默处理单个NPC的记忆获取失败
            
            # ═══════════════════════════════════════════════════════════════
            # 【优化3】收集NPC的社会关系（家庭、师徒等）
            # ═══════════════════════════════════════════════════════════════
            relations = self._get_npc_social_relations(card, all_cards)
            if relations:
                npc_info['relations'] = relations
            
            # 添加到完整演员池
            snapshot.all_available_npcs.append(npc_info)
            
            # 检测危机状态
            crisis_reasons = []
            if emotion < 20:
                crisis_reasons.append(f"情绪低落({emotion})")
            if hunger > 80:
                crisis_reasons.append(f"饥饿({hunger})")
            if wealth < 20:
                crisis_reasons.append(f"贫困({wealth})")
            if card.safety == SAFETY_DOWNED:
                crisis_reasons.append("重伤")
            
            # 【优化】从记忆中检测潜在危机
            if npc_info.get('recent_memories'):
                for mem in npc_info['recent_memories']:
                    if any(keyword in mem for keyword in ['被欺负', '被抢', '欠债', '仇恨', '报复']):
                        crisis_reasons.append(f"有未解决的恩怨")
                        break
                
            if crisis_reasons:
                npc_info['crisis_reasons'] = crisis_reasons
                snapshot.npcs_in_crisis.append(npc_info)
            
            # 检测秘密/特殊状态
            secrets = []
            if getattr(card, 'hidden_identity', None):
                secrets.append(f"隐藏身份: {card.hidden_identity}")
            if getattr(card, 'secret_goal', None):
                secrets.append(f"秘密目标: {card.secret_goal}")
            if getattr(card, 'grudge_target', None):
                secrets.append(f"仇人: {card.grudge_target}")
                
            if secrets:
                npc_info['secrets'] = secrets
                snapshot.npcs_with_secrets.append(npc_info)
        
        # 检测关系紧张的NPC对
        self._find_tense_relationships(all_cards, snapshot)
    
    def _extract_memory_summary(self, npc_memory) -> List[str]:
        """
        【优化】从NPC记忆系统中提取关键记忆摘要
        
        用于让导演了解NPC最近经历了什么，从而生成连贯的事件
        """
        summaries = []
        try:
            # 获取最近的重要记忆（最多3条）
            recent = npc_memory.get_recent_memories(count=5)
            for mem in recent:
                # 只保留重要性>=3的记忆
                if getattr(mem, 'importance', 0) >= 3:
                    content = getattr(mem, 'content', '')
                    if content and len(content) > 5:
                        # 截取前40字符作为摘要
                        summaries.append(content[:40] + ('...' if len(content) > 40 else ''))
                        if len(summaries) >= 3:
                            break
            
            # 同时检查长期记忆中的重大事件
            if hasattr(npc_memory, 'long_term') and npc_memory.long_term:
                for mem in npc_memory.long_term[-3:]:  # 最近3条长期记忆
                    content = getattr(mem, 'content', '')
                    if content and content not in summaries:
                        summaries.append(content[:40] + ('...' if len(content) > 40 else ''))
                        if len(summaries) >= 5:
                            break
        except Exception as e:
            pass  # 静默处理
        
        return summaries
    
    def _get_npc_social_relations(self, card, all_cards: list) -> List[str]:
        """
        【优化】获取NPC的社会关系描述
        
        返回如：["夫妻:张三", "师徒:李四(师父)"]
        """
        relations = []
        try:
            from src.social_system import social_manager
            
            # 检查家庭关系
            spouse_id = getattr(card, 'spouse_id', None)
            if spouse_id:
                spouse_name = self._find_npc_name(spouse_id, all_cards)
                if spouse_name:
                    relations.append(f"配偶:{spouse_name}")
            
            # 检查师徒关系
            master_id = getattr(card, 'master_id', None)
            if master_id:
                master_name = self._find_npc_name(master_id, all_cards)
                if master_name:
                    relations.append(f"师父:{master_name}")
            
            # 检查仇人关系
            enemy_id = getattr(card, 'grudge_target', None)
            if enemy_id:
                enemy_name = self._find_npc_name(enemy_id, all_cards)
                if enemy_name:
                    relations.append(f"仇人:{enemy_name}")
            
            # 【从社会系统获取关系标签】
            if social_manager:
                # 获取最重要的几个关系
                for other_card in all_cards[:20]:  # 限制检查数量
                    if other_card.id == card.id:
                        continue
                    rel_type = social_manager.get_relation_type(card.id, other_card.id)
                    if rel_type and rel_type not in ['NEUTRAL', 'STRANGER']:
                        rel_type_cn = {
                            'FRIEND': '好友',
                            'ALLY': '盟友',
                            'ENEMY': '敌人',
                            'RIVAL': '对头',
                            'LOVER': '情人',
                            'FAMILY': '家人',
                            'SUBORDINATE': '下属',
                            'SUPERIOR': '上级'
                        }.get(rel_type, rel_type)
                        relations.append(f"{rel_type_cn}:{other_card.name}")
                        if len(relations) >= 5:  # 最多5个关系
                            break
        except Exception as e:
            pass  # 静默处理
        
        return relations
    
    def _find_npc_name(self, npc_id: int, all_cards: list) -> Optional[str]:
        """根据ID查找NPC名字"""
        for card in all_cards:
            if getattr(card, 'id', None) == npc_id:
                return getattr(card, 'name', None)
        return None
    
    def _find_tense_relationships(self, all_cards: list, snapshot: WorldSnapshot):
        """找出关系紧张的NPC对"""
        from src.entities import NPC
        from src.social_system import social_manager
        
        npcs = [c for c in all_cards if isinstance(c, NPC) 
                and c.safety not in [SAFETY_DEAD, SAFETY_EXILED]
                and not getattr(c, 'is_player', False)]
        
        checked_pairs = set()
        for npc1 in npcs:
            for npc2 in npcs:
                if npc1.id >= npc2.id:
                    continue
                pair_key = (npc1.id, npc2.id)
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)
                
                # 获取关系值
                affinity = social_manager.get_affinity(npc1.id, npc2.id)
                
                if affinity < -30:  # 敌对关系
                    snapshot.relationship_tensions.append({
                        'npc1': {'id': npc1.id, 'name': npc1.name},
                        'npc2': {'id': npc2.id, 'name': npc2.name},
                        'affinity': affinity,
                        'reason': self._infer_tension_reason(npc1, npc2, affinity)
                    })
    
    def _infer_tension_reason(self, npc1, npc2, affinity: int) -> str:
        """推断关系紧张的原因"""
        # 检查组织敌对
        org1 = getattr(npc1, 'org_id', '')
        org2 = getattr(npc2, 'org_id', '')
        if org1 and org2 and org1 != org2:
            return f"组织对立({org1} vs {org2})"
        
        # 检查个人恩怨
        if getattr(npc1, 'grudge_target', None) == npc2.id:
            return f"{npc1.name}对{npc2.name}有仇"
        if getattr(npc2, 'grudge_target', None) == npc1.id:
            return f"{npc2.name}对{npc1.name}有仇"
        
        if affinity < -60:
            return "深仇大恨"
        elif affinity < -40:
            return "积怨已久"
        else:
            return "关系不睦"
    
    def _observe_player(self, ctx, snapshot: WorldSnapshot):
        """观察玩家状态"""
        from src.social_system import social_manager
        from src.entities import NPC
        
        player = getattr(ctx, 'player', None)
        if not player:
            return
            
        # 玩家声望
        snapshot.player_reputation = {
            'fame': getattr(player, 'fame', 0),
            'infamy': getattr(player, 'infamy', 0),
        }
        
        # 玩家与NPC关系
        all_cards = getattr(ctx, 'all_cards', [])
        for card in all_cards:
            if not isinstance(card, NPC) or getattr(card, 'is_player', False):
                continue
            
            affinity = social_manager.get_affinity(player.id, card.id)
            if abs(affinity) > 20:  # 只记录有明显关系的
                snapshot.player_relationships.append({
                    'npc_id': card.id,
                    'npc_name': card.name,
                    'affinity': affinity,
                    'type': 'ally' if affinity > 30 else ('enemy' if affinity < -30 else 'neutral')
                })
    
    


class AIDirector:
    """AI导演 - 使用LLM编排事件"""
    
    def __init__(self):
        self.observer = WorldObserver()
        self.last_decision_time = 0
        self.pending_news_item: Optional[LiveNewsItem] = None
        
        # 从配置读取决策间隔
        self._load_config_interval()
        
        # 事件模板库（供LLM参考）
        self.event_templates = self._load_event_templates()
    
    def _load_config_interval(self):
        """从LLMConfig加载决策间隔"""
        try:
            from src.llm.config import LLMConfig
            config = LLMConfig.get_instance()
            self.min_decision_interval = config.director_interval_ms
            log_game_event(f"[Director] 决策间隔: {self.min_decision_interval}ms", tag="DIRECTOR")
        except Exception as e:
            self.min_decision_interval = 60000  # 默认60秒（1分钟）
            log_game_event(f"[Director] 配置加载失败，使用默认间隔: {e}", tag="DIRECTOR")
    
    def _load_event_templates(self) -> List[Dict]:
        """
        加载事件模板库
        
        【优化】从 make_event_csv.py 中提取的丰富事件种子库
        包含：经济类、家庭伦理、社会乱象、江湖恩怨、超自然等
        """
        return [
            # ═══════════════════════════════════════════════════════════════
            # 100系列：经济类事件
            # ═══════════════════════════════════════════════════════════════
            {
                "id": "protection_money",
                "name": "收保护费",
                "category": "ECONOMIC",
                "description": "地痞流氓围住商贩摊位，扬言不交钱就砸摊子",
                "required_roles": ["victim", "aggressor"],
                "victim_traits": ["power_type:商", "job:商贩|小贩|摊贩"],
                "aggressor_traits": ["power_type:匪|游"],
                "tension": "HIGH",
                "player_choices": ["替他交钱(破财)", "武力驱逐(需实力)", "袖手旁观"],
                "drama_hook": "小人物的无奈与街头正义"
            },
            {
                "id": "tax_extortion",
                "name": "官府查账",
                "category": "ECONOMIC",
                "description": "税务官造访店铺，吹毛求疵意图索贿",
                "required_roles": ["merchant", "official"],
                "merchant_traits": ["power_type:商", "wealth:>50"],
                "tension": "MEDIUM",
                "player_choices": ["帮忙塞红包", "仗义执言", "袖手旁观"],
                "drama_hook": "官商博弈与腐败"
            },
            {
                "id": "currency_crisis",
                "name": "交子贬值",
                "category": "ECONOMIC",
                "description": "持旧交子去钱庄兑换被拒，急得想跳河",
                "required_roles": ["victim"],
                "victim_traits": ["wealth:<50", "eco_status:POOR"],
                "tension": "MEDIUM",
                "player_choices": ["原价兑换(收买人心)", "低价收割(奸商)", "派人交涉"],
                "drama_hook": "金融风暴下的小人物"
            },
            {
                "id": "housing_dream",
                "name": "汴京买房梦",
                "category": "ECONOMIC",
                "description": "书生为在汴京买房，每日打三份工，几近猝死",
                "required_roles": ["striver"],
                "striver_traits": ["power_type:文", "wealth:<100"],
                "tension": "MEDIUM",
                "player_choices": ["劝他租房(躺平)", "借他首付(高利贷)", "爱莫能助"],
                "drama_hook": "古代版房奴的辛酸"
            },
            {
                "id": "usury_trap",
                "name": "高利贷陷阱",
                "category": "ECONOMIC",
                "description": "借了「驴打滚」买首饰，如今利滚利家产将被封",
                "required_roles": ["debtor"],
                "debtor_traits": ["tags:DEBTOR|POOR", "safety:DANGER"],
                "tension": "HIGH",
                "player_choices": ["代为还债(大善人)", "买下卖身契(趁火打劫)", "暴力解决"],
                "drama_hook": "债务陷阱与人性抉择"
            },
            {
                "id": "apprentice_exploit",
                "name": "学徒剥削",
                "category": "ECONOMIC",
                "description": "师傅以「学艺」为由，三年不给学徒工钱",
                "required_roles": ["apprentice", "master"],
                "tension": "MEDIUM",
                "player_choices": ["仗义执言(劳动法)", "支持师傅(传统规矩)", "推荐去处(招募)"],
                "drama_hook": "行规与公平的碰撞"
            },
            
            # ═══════════════════════════════════════════════════════════════
            # 200系列：家庭伦理
            # ═══════════════════════════════════════════════════════════════
            {
                "id": "bride_price",
                "name": "天价聘礼",
                "category": "SOCIAL",
                "description": "凑不齐聘礼，想去卖身",
                "required_roles": ["groom"],
                "groom_traits": ["wealth:<100"],
                "tension": "HIGH",
                "player_choices": ["资助聘礼(成人之美)", "介绍高利贷", "劝其分手(现实)"],
                "drama_hook": "爱情与现实的碰撞"
            },
            {
                "id": "son_in_law_dignity",
                "name": "赘婿的尊严",
                "category": "SOCIAL",
                "description": "赘婿被岳家当狗使唤，连上桌吃饭都不行",
                "required_roles": ["son_in_law"],
                "tension": "MEDIUM",
                "player_choices": ["教唆夺权(黑化)", "劝他忍耐(男德)", "提供工作(招募)"],
                "drama_hook": "尊严与生存的抉择"
            },
            {
                "id": "helping_brother",
                "name": "扶弟魔",
                "category": "SOCIAL",
                "description": "妻子偷光家中积蓄，全给了不成器的弟弟",
                "required_roles": ["wife", "brother"],
                "tension": "MEDIUM",
                "player_choices": ["支持她(亲情至上)", "教训弟弟", "清官难断(无视)"],
                "drama_hook": "家庭矛盾与立场选择"
            },
            {
                "id": "arranged_marriage",
                "name": "指腹为婚",
                "category": "SOCIAL",
                "description": "富家女爱上穷书生，却被父亲强迫嫁给太尉之子",
                "required_roles": ["rich_girl", "poor_scholar"],
                "tension": "HIGH",
                "player_choices": ["协助私奔", "劝她认命", "抢亲(需打手)"],
                "drama_hook": "自由恋爱vs包办婚姻"
            },
            {
                "id": "abandon_wife",
                "name": "抛妻弃子",
                "category": "SOCIAL",
                "description": "新科状元想要休掉糟糠之妻，迎娶高官之女",
                "required_roles": ["scholar", "wife"],
                "scholar_traits": ["power_type:官|文", "social_level:>5"],
                "tension": "HIGH",
                "player_choices": ["写文揭露(舆论战)", "收封口费", "派人痛打"],
                "drama_hook": "功成名就后的忘恩负义"
            },
            
            # ═══════════════════════════════════════════════════════════════
            # 300系列：社会乱象
            # ═══════════════════════════════════════════════════════════════
            {
                "id": "street_scam",
                "name": "当街碰瓷",
                "category": "SOCIAL",
                "description": "老人倒在马车前哀嚎，实际上他腿早就断了",
                "required_roles": ["scammer"],
                "tension": "MEDIUM",
                "player_choices": ["送医(冤大头)", "当众揭穿", "以暴制暴"],
                "drama_hook": "善心与防骗的平衡"
            },
            {
                "id": "false_rumor",
                "name": "造谣一张嘴",
                "category": "SOCIAL",
                "description": "被谣传是江洋大盗，客栈不敢收，饭馆不敢卖",
                "required_roles": ["victim"],
                "tension": "MEDIUM",
                "player_choices": ["收留他(查明真相)", "驱逐出城", "官府辟谣"],
                "drama_hook": "谣言的杀伤力"
            },
            {
                "id": "spoiled_child",
                "name": "熊孩子作恶",
                "category": "SOCIAL",
                "description": "小孩划坏了名贵字画，家长称「他还是个孩子」",
                "required_roles": ["parent"],
                "tension": "LOW",
                "player_choices": ["严厉惩罚(教做人)", "息事宁人", "恐吓家长"],
                "drama_hook": "熊家长与社会公德"
            },
            {
                "id": "queue_cutting",
                "name": "插队冲突",
                "category": "SOCIAL",
                "description": "施粥铺前，身强力壮者插队抢夺老弱妇孺的口粮",
                "required_roles": ["bully", "victim"],
                "bully_traits": ["power_type:匪|游"],
                "tension": "MEDIUM",
                "player_choices": ["武力驱逐", "额外给一份", "呵斥(需名望)"],
                "drama_hook": "弱肉强食与社会公平"
            },
            {
                "id": "romance_scam",
                "name": "杀猪盘",
                "category": "SOCIAL",
                "description": "貌美女子主动搭讪老人，实则为了骗取棺材本",
                "required_roles": ["scammer", "victim"],
                "scammer_traits": ["tags:BEAUTIFUL"],
                "victim_traits": ["tags:OLD"],
                "tension": "MEDIUM",
                "player_choices": ["提醒老人", "参与分红", "当场揭穿"],
                "drama_hook": "情感诈骗与老年危机"
            },
            {
                "id": "fake_official",
                "name": "假冒官差",
                "category": "SOCIAL",
                "description": "穿官服招摇撞骗，正在勒索小摊贩",
                "required_roles": ["fake_official", "victim"],
                "tension": "HIGH",
                "player_choices": ["当场拿下", "假装不知", "报官"],
                "drama_hook": "冒充公权力的恶行"
            },
            
            # ═══════════════════════════════════════════════════════════════
            # 400系列：江湖恩怨
            # ═══════════════════════════════════════════════════════════════
            {
                "id": "retire_assassin",
                "name": "金盆洗手难",
                "category": "MARTIAL",
                "description": "杀手想退隐，组织却以其家人性命相逼",
                "required_roles": ["assassin"],
                "assassin_traits": ["power_type:匪", "tags:ASSASSIN|THUG"],
                "tension": "CRITICAL",
                "player_choices": ["协助他灭了组织", "出卖他领赏", "劝他快跑(中立)"],
                "drama_hook": "江湖身不由己"
            },
            {
                "id": "secret_manual",
                "name": "秘籍争夺",
                "category": "MARTIAL",
                "description": "一本假秘籍引发械斗，死伤惨重",
                "required_roles": ["fighter1", "fighter2"],
                "tension": "HIGH",
                "player_choices": ["告知是假的", "坐收渔利", "远离是非(离开)"],
                "drama_hook": "贪婪与武林传说"
            },
            {
                "id": "escort_betrayal",
                "name": "镖局失信",
                "category": "MARTIAL",
                "description": "镖局弄丢了孤儿寡母唯一的寄托，拒绝赔偿",
                "required_roles": ["victim", "escort"],
                "victim_traits": ["wealth:<30"],
                "tension": "HIGH",
                "player_choices": ["代为索赔(武力)", "劝她算了", "打上门去"],
                "drama_hook": "江湖道义vs商业利益"
            },
            {
                "id": "impersonation",
                "name": "冒名顶替",
                "category": "MARTIAL",
                "description": "冒充大侠名号招摇撞骗，被正主撞见",
                "required_roles": ["faker", "real_hero"],
                "tension": "HIGH",
                "player_choices": ["救他一命(收小弟)", "看着他被打死", "当众揭穿"],
                "drama_hook": "假大侠与真武林"
            },
            {
                "id": "black_on_black",
                "name": "黑吃黑",
                "category": "MARTIAL",
                "description": "交易违禁品时，一方埋伏了刀斧手",
                "required_roles": ["trader1", "trader2"],
                "role_traits": ["tags:EVIL|THUG"],
                "tension": "CRITICAL",
                "player_choices": ["全部举报", "加入埋伏", "快速溜走(保命)"],
                "drama_hook": "黑道无信义"
            },
            
            # ═══════════════════════════════════════════════════════════════
            # 500系列：超自然与荒诞
            # ═══════════════════════════════════════════════════════════════
            {
                "id": "time_traveler",
                "name": "时间穿越者",
                "category": "SUPERNATURAL",
                "description": "疯子满嘴「YYDS」、「绝绝子」，被官府抓捕",
                "required_roles": ["stranger"],
                "stranger_traits": ["tags:CRAZY"],
                "tension": "LOW",
                "player_choices": ["保释他(老乡?)", "送去切片研究", "听不懂(无视)"],
                "drama_hook": "穿越者的窘境(彩蛋)"
            },
            {
                "id": "gender_swap",
                "name": "性别互换",
                "category": "SUPERNATURAL",
                "description": "误食丹药，壮汉变成了娇滴滴的女子",
                "required_roles": ["victim"],
                "victim_traits": ["tags:STRONG"],
                "tension": "MEDIUM",
                "player_choices": ["捧她做花魁", "帮他寻找解药", "收为家丁(招募)"],
                "drama_hook": "奇幻与身份认同"
            },
            {
                "id": "antique_spirit",
                "name": "古董成精",
                "category": "SUPERNATURAL",
                "description": "传言传家宝夜里会说话，引来各路觊觎",
                "required_roles": ["owner"],
                "tension": "MEDIUM",
                "player_choices": ["低价收购", "辟谣保护", "鉴定真伪"],
                "drama_hook": "神秘主义与贪婪"
            },
            
            # ═══════════════════════════════════════════════════════════════
            # 600系列：门客/帮派专属
            # ═══════════════════════════════════════════════════════════════
            {
                "id": "farm_disaster",
                "name": "农田虫害",
                "category": "ECONOMIC",
                "description": "农夫看着满地蝗虫欲哭无泪，今年的收成要完了",
                "required_roles": ["farmer"],
                "farmer_traits": ["power_type:农", "job:农夫|佃户"],
                "tension": "HIGH",
                "player_choices": ["资助买药(善举)", "科学除虫(需专家)", "烧香祈福(迷信)"],
                "drama_hook": "天灾与生计"
            },
            {
                "id": "bully_market",
                "name": "恶霸欺市",
                "category": "ECONOMIC",
                "description": "在市场被恶霸欺负，敢怒不敢言",
                "required_roles": ["victim", "bully"],
                "victim_traits": ["power_type:商"],
                "bully_traits": ["power_type:匪|游"],
                "tension": "HIGH",
                "player_choices": ["花钱摆平", "路见不平(需打手)", "大声呵斥(需名望)"],
                "drama_hook": "市井暴力与正义"
            },
            {
                "id": "fake_medicine",
                "name": "虚假宣传",
                "category": "SOCIAL",
                "description": "郎中宣称「大力丸」包治百病，被路人当街揭穿",
                "required_roles": ["doctor", "whistleblower"],
                "doctor_traits": ["job:郎中|医生"],
                "tension": "MEDIUM",
                "player_choices": ["帮郎中圆谎(狼狈为奸)", "当众拆穿", "看热闹(无视)"],
                "drama_hook": "医疗欺诈与公众健康"
            },
            {
                "id": "gambling_addiction",
                "name": "关扑成瘾",
                "category": "SOCIAL",
                "description": "老实人沉迷关扑(彩票)，输光家产后想卖儿卖女",
                "required_roles": ["gambler"],
                "gambler_traits": ["tags:GAMBLER", "wealth:<20"],
                "tension": "HIGH",
                "player_choices": ["劝诫并资助", "开设赌局(做庄)", "痛打一顿"],
                "drama_hook": "赌博成瘾与家庭悲剧"
            },
            
            # ═══════════════════════════════════════════════════════════════
            # 700系列：民生类
            # ═══════════════════════════════════════════════════════════════
            {
                "id": "refugee_begging",
                "name": "叩阙求食",
                "category": "SOCIAL",
                "description": "流民跪在城门外，衣衫褴褛，恳求施舍一口热粥",
                "required_roles": ["refugee"],
                "refugee_traits": ["hunger:>70", "wealth:<10"],
                "tension": "MEDIUM",
                "player_choices": ["开仓放粮(仁政)", "武力驱逐(酷吏)", "视而不见(冷漠)"],
                "drama_hook": "灾民与社会责任",
                "weight": 30  # 高权重，保证高频触发
            },
            {
                "id": "moral_kidnap",
                "name": "道德绑架",
                "category": "SOCIAL",
                "description": "乞丐抱住你大腿，指责你为富不仁不施舍",
                "required_roles": ["beggar"],
                "beggar_traits": ["wealth:<10"],
                "tension": "LOW",
                "player_choices": ["破财免灾", "放狗咬人", "一脚踢开"],
                "drama_hook": "道德绑架与个人边界"
            },
            
            # ═══════════════════════════════════════════════════════════════
            # 势力冲突类（保留原有）
            # ═══════════════════════════════════════════════════════════════
            {
                "id": "faction_clash",
                "name": "帮派冲突",
                "category": "FACTION",
                "description": "两个敌对势力成员在街头相遇",
                "required_roles": ["faction1_member", "faction2_member"],
                "role_traits": ["factions_hostile:true"],
                "tension": "HIGH",
                "player_choices": ["支持一方", "两边调停", "袖手旁观"],
                "drama_hook": "势力争斗与立场选择"
            },
            {
                "id": "power_struggle",
                "name": "权力斗争",
                "category": "FACTION",
                "description": "组织内部的权力争夺",
                "required_roles": ["contender1", "contender2"],
                "role_traits": ["same_org:true", "both_ambitious:true"],
                "tension": "CRITICAL",
                "player_choices": ["支持其中一方", "渔翁得利", "保持中立"],
                "drama_hook": "权力游戏"
            },
        ]
    
    def should_generate_event(self, dt_ms: int) -> bool:
        """判断是否应该生成新事件"""
        self.last_decision_time += dt_ms
        return self.last_decision_time >= self.min_decision_interval
    
    
    


    
    async def direct_event(self, ctx) -> Optional[LiveNewsItem]:
        """导演一个事件（异步，调用LLM）"""
        self.last_decision_time = 0
        
        # 1. 观察世界状态
        snapshot = self.observer.observe(ctx)
        
        # 2. 构建LLM prompt
        prompt = self._build_director_prompt(snapshot)
        
        # 3. 调用LLM决策
        decision = None
        try:
            decision = await self._call_llm_for_decision(prompt)
        except Exception as e:
            log_game_event(f"[Director] LLM调用失败，中止后续步骤，报错信息: {e}", tag="DIRECTOR")
            return None
        
        # 4. 解析LLM响应，生成事件（即使是fallback也能正确解析）
        news_item = self._parse_llm_decision(decision, snapshot, ctx)
        
        if news_item:
            # 5. 并行启动配图生成 + 对话扩写（两者都就绪后再添加新闻）
            self._start_parallel_generation(news_item)
            self.pending_news_item = news_item
            return news_item
        
        return None
    
    def _build_director_prompt(self, snapshot: WorldSnapshot) -> str:
        """构建给LLM的导演prompt"""
        
        # 格式化世界状态
        world_state = []
        
        # ====== 完整演员池（所有可用NPC） ======
        if snapshot.all_available_npcs:
            world_state.append("【可用演员池】（请从这些人物中挑选演员）")
            # 按组织分组显示
            npcs_by_org = {}
            for npc in snapshot.all_available_npcs:
                org = npc.get('org', '无组织') or '无组织'
                if org not in npcs_by_org:
                    npcs_by_org[org] = []
                npcs_by_org[org].append(npc)
            
            for org, npcs in npcs_by_org.items():
                world_state.append(f"\n  [{org}] ({len(npcs)}人)")
                for npc in npcs:  # 显示该组织所有NPC
                    # 格式：ID=123 姓名(职业/身份) 状态
                    status_tags = []
                    if npc.get('emotion', 50) < 30:
                        status_tags.append("情绪低")
                    if npc.get('hunger', 0) > 60:
                        status_tags.append("饥饿")
                    if npc.get('wealth', 100) > 200:
                        status_tags.append("富有")
                    elif npc.get('wealth', 100) < 30:
                        status_tags.append("贫穷")
                    if npc.get('status') == '重伤':
                        status_tags.append("重伤")
                    
                    # 【优化】添加NPC标签
                    npc_tags = npc.get('tags', [])
                    if npc_tags:
                        status_tags.extend(npc_tags[:3])  # 最多3个标签
                    
                    status_str = f" [{','.join(status_tags)}]" if status_tags else ""
                    
                    # 基本信息行
                    npc_line = f"    ID={npc['id']} {npc['name']}({npc.get('power_type','民')}/{npc.get('job','')}){status_str}"
                    world_state.append(npc_line)
                    
                    # 【优化】显示NPC人设描述（desc）
                    desc = npc.get('desc', '')
                    if desc:
                        # 截取前30字，避免过长
                        desc_short = desc[:35] + '...' if len(desc) > 35 else desc
                        world_state.append(f"        人设: {desc_short}")
                    
                    # 【优化】如果NPC有重要关系，显示在下一行
                    relations = npc.get('relations', [])
                    if relations:
                        rel_str = ", ".join(relations[:3])  # 最多3个关系
                        world_state.append(f"        关系: {rel_str}")
                    
                    # 【优化】如果NPC有重要记忆，显示最关键的一条
                    memories = npc.get('recent_memories', [])
                    if memories:
                        # 只显示第一条最重要的记忆
                        world_state.append(f"        近期: {memories[0]}")
            
            world_state.append(f"\n  （共{len(snapshot.all_available_npcs)}名可用演员）")
        
        # 势力状态
        if snapshot.faction_tensions:
            world_state.append("\n【势力局势】")
            for key, data in snapshot.faction_tensions.items():
                orgs = data['orgs']
                world_state.append(f"  - {orgs[0]} vs {orgs[1]}: 敌对度{data['hostility']}" + 
                                  (" (战争中)" if data['at_war'] else ""))
        
        # 危机NPC（高亮显示）
        if snapshot.npcs_in_crisis:
            world_state.append("\n【陷入困境的人物】[!] 高戏剧性潜力")
            for npc in snapshot.npcs_in_crisis[:5]:  # 最多5个
                reasons = ", ".join(npc.get('crisis_reasons', []))
                world_state.append(f"  - ID={npc['id']} {npc['name']}({npc.get('org','')}): {reasons}")
        
        # 紧张关系（高亮显示）
        if snapshot.relationship_tensions:
            world_state.append("\n【人物矛盾】[火] 冲突爆发点")
            for tension in snapshot.relationship_tensions[:5]:
                world_state.append(
                    f"  - ID={tension['npc1']['id']} {tension['npc1']['name']} ↔ "
                    f"ID={tension['npc2']['id']} {tension['npc2']['name']}: "
                    f"{tension['reason']} (好感度:{tension['affinity']})"
                )
        
        # 有秘密的NPC
        if snapshot.npcs_with_secrets:
            world_state.append("\n【隐藏秘密的人物】[秘] 可揭露")
            for npc in snapshot.npcs_with_secrets[:3]:
                secrets = ", ".join(npc.get('secrets', []))
                world_state.append(f"  - ID={npc['id']} {npc['name']}: {secrets}")
        
        # 玩家关系
        if snapshot.player_relationships:
            world_state.append("\n【玩家人际关系】")
            for rel in snapshot.player_relationships[:5]:
                rel_type = "盟友" if rel['type'] == 'ally' else ("敌人" if rel['type'] == 'enemy' else "普通")
                world_state.append(f"  - ID={rel['npc_id']} {rel['npc_name']}: {rel_type} (好感:{rel['affinity']})")
        
       
        
        world_state_text = "\n".join(world_state)
        
        # 事件模板列表（包含drama_hook戏剧性钩子）
        templates_text = "\n".join([
            f"- {t['id']}: {t['name']} ({t['category']}) - {t['description']}" + 
            (f" 【{t.get('drama_hook', '')}】" if t.get('drama_hook') else "")
            for t in self.event_templates
        ])
        
        prompt = f"""你是《大宋实况》的导演AI，负责编排真人秀风格的社会事件。
你的目标是创造有深度、有连贯性的世界事件，让玩家感受到这是一个"活着的"宋代社会。

【当前世界状态】
{world_state_text}

【可用事件模板】（共{len(self.event_templates)}种）
{templates_text}

【随机性要求】[!] 必须遵守
- **不要每次都选择列表前面的事件模板**（如protection_money收保护费）
- 每次从全部33种模板中**随机挑选**，确保事件类型多样化
- 避免连续两次选择同一类事件（如连续两次都是ECONOMIC经济类）

【导演核心原则】[*] 重要
1. **记忆连贯性**：如果某个NPC有"近期"记忆，事件应该与其经历相关
   - 例：NPC近期"被泼皮欺负" → 可能触发"报复"或"寻求帮助"事件
   - 例：NPC近期"得到玩家帮助" → 可能触发"回报"或"感恩"事件
2. **关系驱动**：优先选择有明确关系的NPC组合
   - 仇人之间 → 冲突事件
   - 师徒/家人之间 → 家庭伦理事件
   - 同门/同组织 → 权力斗争事件
3. **状态匹配**：NPC当前状态应该与事件匹配
   - 贫穷的NPC → 经济困境类事件
   - 情绪低落的NPC → 需要安慰/爆发类事件
   - 有标签[THUG]的NPC → 作为恶霸/打手角色

【你的任务】
1. 分析当前局势，**特别关注NPC的记忆和关系**
2. 选择最有戏剧性和张力的事件模板
3. 从上述人物中选择**状态和经历匹配**的演员
4. 编写一个"小红书/抖音直播"风格的实况快照

请以JSON格式返回决策：
```json
{{
    "event_type": "选择的事件模板ID",
    "actors": [
        {{"role": "角色名", "npc_name": "NPC名字", "npc_id": "NPC的ID"}}
    ],
    "tension_level": "LOW/MEDIUM/HIGH/CRITICAL",
    "reason": "为什么选择这个事件（导演思路）",
    
    "title": "【爆款标题】例：无更市惊现天价救命药！",
    "description": "事件劲爆描述，30字左右，讲清楚前因后果和人物困境",
    "image_prompt": "给AI生图的中文描述，必须严格按以下四层结构编写：

        【第一层·风格锁定】
        《雾山五行》风格，手绘2D国漫，硬朗线条，平涂阴影，
        高对比度色彩，宋代市井场景。手绘笔触，电影级构图。

        【第二层·背景与氛围】
        交代具体地点，描写光线天气，路人反应。
        用光影暗示情绪：冲突用侧逆光强阴影，温情用暖色散射光。

        【第三层·角色交互（核心，必须详写200字以上）】
        规则：
        1. 用物理接触建立关系（揪衣领/递东西/推搡/牵手），
           禁止只写'A看着B'这种抽象描述。
        2. 设定一个「视觉焦点道具」（钱袋/武器/信件/食物等），
           让核心角色的视线通过该道具产生交汇。
        3. 明确每个角色的画面位置（左/中/右）、身体朝向、
           姿态（前倾/后仰/侧身）。
        4. 禁止任何角色看向镜头/画面外。
        5. 禁止角色之间无动作连接。

        【第四层·情绪微细节】
        至少2个微表情/微动作（攥拳、咬唇、冒汗、衣角飘动等）。",
    "tags": ["市井纠纷", "见义勇为", "宋代风情"],
    "comments": [
        {{"user": "路人甲", "text": "评论内容", "type": "支持/反对/中立/搞笑"}},
        {{"user": "吃瓜群众", "text": "这也太离谱了吧", "type": "中立"}}
    ],
    "choices": [
        {{"text": "选项1文本", "effect": "A:affinity:-30;B:affinity:+40"}},
        {{"text": "选项2文本", "effect": ""}},
        {{"text": "选项3文本", "effect": "PLAYER:fame:+10"}}
    ]
    
}}
```



【选项要求】
- 必须提供 2-3 个选项，不要更多
- 每个选项要有明确的效果（effect 字段）
- 选项要体现不同的处理思路（激进/保守/中立）
- **【关键约束】选项中只能引用以下人物：**
  1. **actors列表中的NPC**（困境主角、压力来源、潜在受害者等）
  2. **comments列表中的NPC**（作为评论者被提及）
  3. **玩家自己（PLAYER）**
  **禁止引用不存在的人物！** 
  **如果需要一个中间人/关系人，必须从完整演员池中选择一个真实存在的NPC加入actors或comments，禁止虚构！**
- **【自查要求】生成选项后，检查每个选项提到的所有人物名称，确认他们都在actors或comments中，否则重新设计该选项。**

【格式要求】[!] 严格遵守
1. 必须返回合法的JSON格式，所有字符串必须用双引号包裹
2. 不要在JSON中使用单引号
3. 不要在数组或对象末尾添加多余逗号
4. 不需要返回heat_score，由系统根据tension_level自动计算

【内容要求】
1. 标题要有爆点，像小红书热门标题
2. 评论要模拟真实网友风格（支持、反对、调侃都要有），网友不能是虚构，必须来自于完整演员池（所有可用NPC，但是剔除当事人）
3. effect格式：角色:属性:增减值，多个用分号隔开
4. 角色可以是 A/B/C（对应actors顺序）或 PLAYER5、
5. tags数组中的标签只写纯文字，如 ["职场霸凌", "废柴集合"]等吸引人注目的标签
"""
        return prompt
    
    async def _call_llm_for_decision(self, prompt: str) -> Dict:
        """调用LLM进行决策（使用LLMService）"""
        from src.llm.llm_service import LLMService
        import asyncio
        
        llm_service = LLMService.get_instance()
        
        # 检查是否启用LLM模式
        if not llm_service.is_available():
            log_game_event("[Director] LLM服务不可用，中止事件生成", tag="DIRECTOR")
            return None
        
       
        system_prompt = "你是一个专业的游戏导演AI，负责为《大宋实况》生成戏剧性事件。请严格按照JSON格式返回结果。"
        start_time = time.time()
        # Director系统需要更多token（prompt很长，需要预留足够token生成回复）
        director_max_tokens = 6000
        
        try:
            # 在线程池中执行同步调用，避免阻塞事件循环
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,  # 使用默认线程池
                lambda: llm_service.chat(system_prompt, prompt, max_tokens=director_max_tokens)
            )
            
            if not response.success:
                log_game_event(f"[Director] LLM调用失败: {response.error}", tag="DIRECTOR")
                return None
            elapsed = time.time() - start_time
            # ===== 记录响应日志 =====
            log_game_event(f"[Director] 收到LLM响应,耗时 {elapsed:.2f}s,内容 {response.raw_response}...", tag="DIRECTOR")
            
            # 导演系统自己解析JSON响应
            result = llm_service.clean_llm_response(response.raw_response)
            return result
                    
        except Exception as e:
            log_game_event(f"[Director] LLM API调用异常: {e}", tag="DIRECTOR")
            return None
    
    
    
    
    def _parse_llm_decision(self, decision: Dict, snapshot: WorldSnapshot, ctx) -> Optional[LiveNewsItem]:
        """解析LLM决策，生成事件对象"""
        try:
            # 获取演员信息
            actors = decision.get('actors', [])
            
            # 获取演员ID
            actor_ids = [int(a.get('npc_id', 0)) for a in actors if a.get('npc_id')]
            actor_names = [a.get('npc_name', '') for a in actors]
            
            # ════════════════════════════════════════════════════════════
            # 【事发地显示模式】获取事件位置（第一个演员的位置）
            # ════════════════════════════════════════════════════════════
            location_x = 0
            location_y = 0
            location_name = "未知地点"
            
            if actor_ids and ctx and hasattr(ctx, 'all_cards'):
                # 从 all_cards 中查找第一个演员的位置
                for card in ctx.all_cards:
                    if hasattr(card, 'id') and card.id == actor_ids[0]:
                        location_x = card.rect.centerx
                        location_y = card.rect.centery
                        # 尝试获取位置名称
                        if hasattr(card, 'zone'):
                            zone_names = {
                                'INNER': '城内',
                                'OUTER': '城外',
                                'FARM': '农田',
                                'MARKET': '集市',
                                'SLUM': '贫民窟'
                            }
                            location_name = zone_names.get(card.zone, '城内')
                        break
            
            # 确定事件类别
            event_type = decision.get('event_type', '')
            template = next((t for t in self.event_templates if t['id'] == event_type), None)
            category = NewsCategory.SOCIAL
            if template:
                cat_map = {
                    'ECONOMIC': NewsCategory.ECONOMIC,
                    'SOCIAL': NewsCategory.SOCIAL,
                    'MARTIAL': NewsCategory.MARTIAL,
                    'FACTION': NewsCategory.POLITICAL,
                    'SUPERNATURAL': NewsCategory.SUPERNATURAL
                }
                category = cat_map.get(template.get('category', ''), NewsCategory.SOCIAL)
            
            # 确定困境类型（与新定义的 DilemmaType 保持一致）
            tension = decision.get('tension_level', 'MEDIUM')
            dilemma_map = {
                'LOW': None,
                'MEDIUM': DilemmaType.MORAL_GREY,
                'HIGH': DilemmaType.SACRIFICE,
                'CRITICAL': DilemmaType.BETRAY
            }
            dilemma = dilemma_map.get(tension)
            
            # ════════════════════════════════════════════════════════════
            # 【格式修正】tags去掉#前缀（LLM可能仍然带上），heat_score由程序生成
            # ════════════════════════════════════════════════════════════
            raw_tags = decision.get('tags', [])
            clean_tags = [tag.lstrip('#') for tag in raw_tags if isinstance(tag, str)]
            
            # 根据tension_level自动计算heat_score，不依赖LLM输出
            heat_map = {'LOW': 5000, 'MEDIUM': 12000, 'HIGH': 25000, 'CRITICAL': 50000}
            import random as _rand
            base_heat = heat_map.get(tension, 10000)
            heat_score = base_heat + _rand.randint(-2000, 2000)
            
            # ════════════════════════════════════════════════════════════
            # 处理选项格式
            # ════════════════════════════════════════════════════════════
            choices = decision.get('choices', [])
            # 确保选项是字典格式
            if choices and isinstance(choices[0], str):
                choices = [{"text": c, "effect": ""} for c in choices]
            
            # 创建LiveNewsItem（包含小红书风格字段）
            news_item = LiveNewsItem(
                id=f"dir_{event_type}_{int(time.time())}",
                title=decision.get('title', '突发事件'),
                description=decision.get('description', ''),
                category=category,
                dilemma_type=dilemma,
                actor_ids=actor_ids,
                actor_names=actor_names,
                location=location_name,  # 根据演员位置动态确定
                location_x=location_x,   # 【事发地显示模式】世界坐标
                location_y=location_y,
                choices=choices,  # 使用处理后的选项（包含"前往处理"）
                priority=3 if tension == 'HIGH' else (4 if tension == 'CRITICAL' else 2),
                auto_popup=(tension == 'CRITICAL'),
                # ====== 小红书风格字段 ======
                tags=clean_tags,
                comments=decision.get('comments', []),
                heat_score=heat_score,
                image_prompt=decision.get('image_prompt', ''),
            )
            
            return news_item
            
        except Exception as e:
            log_game_event(f"[Director] 解析LLM决策失败: {e}", tag="DIRECTOR")
            return None
    
   
    
    def _start_parallel_generation(self, news_item: LiveNewsItem):
        """并行启动配图生成 + 对话扩写，两者都就绪（或超时）后再添加新闻
        
        这样玩家点击"前往处理"时，对话剧本已经预生成好了，无需等待。
        """
        log_game_event(f"[Director] 并行生成启动: 图片 + 对话扩写", tag="DIRECTOR")
        
        news_mgr = get_notification_manager()
        start_time = time.time()
        max_wait_time = TIMEOUT_IMAGE_GEN
        
        # 使用标志防止重复添加新闻
        news_added = [False]
        # 用于追踪两个任务的完成状态
        image_done = threading.Event()
        dialog_done = threading.Event()
        
        # ═══════════════════════════════════════════════════════════════
        # 任务1：配图生成
        # ═══════════════════════════════════════════════════════════════
        def on_image_ready(surface, path):
            elapsed = time.time() - start_time
            if path:
                news_item._image_path = path
                news_item._image_surface = surface
                log_game_event(f"[Director] 配图已就绪({elapsed:.1f}秒): {path}", tag="DIRECTOR")
            else:
                news_item._image_path = "placeholder"
                log_game_event(f"[Director] 配图生成失败({elapsed:.1f}秒)，使用占位图", tag="DIRECTOR")
            image_done.set()
            _try_add_news()
        
        # ═══════════════════════════════════════════════════════════════
        # 任务2：对话扩写
        # ═══════════════════════════════════════════════════════════════
        def generate_dialog():
            try:
                dialog_gen = get_event_dialog_generator()
                if not dialog_gen.is_available():
                    log_game_event("[Director] 对话扩写跳过：LLM不可用", tag="DIRECTOR")
                    dialog_done.set()
                    return
                
                # 注意：choices[0]可能是"前往处理"按钮（action=START_DIALOG），需要跳过
                all_choices = news_item.choices or []
                story_choices = [c for c in all_choices if c.get('action') != 'START_DIALOG']
                
                # 提取效果字符串
                effect_a = story_choices[0].get('effect', '') if len(story_choices) > 0 else ''
                effect_b = story_choices[1].get('effect', '') if len(story_choices) > 1 else ''
                effect_c = story_choices[2].get('effect', '') if len(story_choices) > 2 else ''
                
                # NPC名字
                npc_a_name = news_item.actor_names[0] if news_item.actor_names else '当事人甲'
                npc_b_name = news_item.actor_names[1] if len(news_item.actor_names) > 1 else None
                
                log_game_event(f"[Director] 对话扩写开始: {npc_a_name} vs {npc_b_name}", tag="DIRECTOR")
                
                # 直接传递 news_item，函数内部会提取所有需要的信息（包括tooltip）
                full_script = dialog_gen.expand_to_full_script(
                    news_item=news_item,
                    npc_a_name=npc_a_name,
                    npc_b_name=npc_b_name,
                    effect_a=effect_a,
                    effect_b=effect_b,
                    effect_c=effect_c
                )
                
                # 将预生成的剧本挂到 news_item 上
                news_item._pregen_script = full_script
                elapsed = time.time() - start_time
                log_game_event(f"[Director] 对话扩写完成({full_script})", tag="DIRECTOR")
                log_game_event(f"[Director] 对话扩写完成({elapsed:.1f}秒)", tag="DIRECTOR")
                
            except Exception as e:
                log_game_event(f"[Director] 对话扩写失败: {e}", tag="DIRECTOR")
            finally:
                dialog_done.set()
                _try_add_news()
        
        # ═══════════════════════════════════════════════════════════════
        # 汇合：两个任务都完成后添加新闻
        # ═══════════════════════════════════════════════════════════════
        def _try_add_news():
            """检查是否两个任务都完成了，是则添加新闻"""
            if image_done.is_set() and dialog_done.is_set() and not news_added[0]:
                news_added[0] = True
                
                # ═══════════════════════════════════════════════════════════════
                # 【自动场景布置】事件生成完成后，立即让NPC瞬移到事发地点
                # ═══════════════════════════════════════════════════════════════
                self._setup_event_scene(news_item)
                
                news_mgr.add_news(news_item)
                elapsed = time.time() - start_time
                log_game_event(f"[Director] 新闻已添加(图片+对话均就绪, {elapsed:.1f}秒): {news_item.title}", tag="DIRECTOR")
        
        # ═══════════════════════════════════════════════════════════════
        # 准备参考图（当事人头像）
        # ═══════════════════════════════════════════════════════════════
        reference_images = []
        enhanced_prompt = news_item.image_prompt
        
        # 获取当事人头像路径（优先使用高清版本用于AI参考图）
        if news_item.actor_names:
            avatar_dirs = [Path("assets/head_icon_hd")]
            ref_image_info = []  # 存储 (路径, 角色名) 元组
            
            for actor_name in news_item.actor_names:
                # 尝试查找头像文件（优先高清版本）
                avatar_path = None
                for avatar_dir in avatar_dirs:
                    test_path = avatar_dir / f"{actor_name}.png"
                    if test_path.exists():
                        avatar_path = test_path
                        break
                
                if avatar_path:
                    reference_images.append(str(avatar_path))
                    ref_image_info.append((str(avatar_path), actor_name))
                    log_game_event(f"[Director] 找到当事人头像: {actor_name} -> {avatar_path}", tag="DIRECTOR")
                else:
                    log_game_event(f"[Director] 未找到头像: {actor_name}", tag="DIRECTOR")
            
            # 在prompt中明确说明每张参考图对应的当事人
            if ref_image_info:
                ref_description = "\n\n【参考图说明】\n"
                for i, (path, name) in enumerate(ref_image_info, 1):
                    ref_description += f"第{i}张参考图是{name}的头像，请严格参考其面部特征。"
                
                # 将参考图说明插入到prompt中
                enhanced_prompt = news_item.image_prompt + ref_description
                log_game_event(f"[Director] 已增强prompt，添加{len(ref_image_info)}个参考图说明", tag="DIRECTOR")
        
        # ═══════════════════════════════════════════════════════════════
        # 启动并行任务
        # ═══════════════════════════════════════════════════════════════
        try:
            # 启动图片生成
            from src.llm.doubao_image import get_image_generator
            generator = get_image_generator()
            news_item._image_path = "loading"
            log_game_event(f"[Director] 图片生成请求: {enhanced_prompt[:80]}...", tag="DIRECTOR")
            if reference_images:
                log_game_event(f"[Director] 使用参考图: {reference_images}", tag="DIRECTOR")
            
            generator.generate_image_async(
                prompt=enhanced_prompt,
                callback=on_image_ready,
                width=400,
                height=300,
                style="artistic",
                reference_images=reference_images if reference_images else None
            )
        except Exception as e:
            log_game_event(f"[Director] 图片生成启动失败: {e}", tag="DIRECTOR")
            news_item._image_path = "placeholder"
            image_done.set()
        
        # 启动对话扩写（后台线程）
        dialog_thread = threading.Thread(target=generate_dialog, daemon=True)
        dialog_thread.start()
        
        # 超时配置已在 definition 中处理，此处不再重复设置超时
    
    
    
    def _setup_event_scene(self, news_item: LiveNewsItem,ctx):
        """
        【自动场景布置】事件生成完成后，立即让NPC瞬移到事发地点并进入剧情保护状态
        
        这样玩家只需要走到事发地点，就能直接开始剧情演绎，无需点击"前往处理"
        """
        import math
        from src.entities import NPC, Building
        from src.definitions import STATE_EVENT, SAFETY_NORMAL
        
        try:
           
            
            # 1. 查找相关 NPC
            actor_ids = getattr(news_item, 'actor_ids', [])
            actor_names = getattr(news_item, 'actor_names', [])
            
            event_npcs = []
            for card in ctx.all_cards:
                if not isinstance(card, NPC):
                    continue
                card_id = getattr(card, 'id', None)
                card_name = getattr(card, 'name', '')
                # 通过 ID 或名字匹配
                if (card_id and str(card_id) in [str(a) for a in actor_ids]) or \
                   (card_name and card_name in actor_names):
                    event_npcs.append(card)
            
            if not event_npcs:
                print(f"[Director·场景布置] 警告: 未找到关联NPC")
                return
            
            print(f"\n{'='*70}")
            print(f"[Director·场景布置] ╔════════════════════════════════════════════════════════╗")
            print(f"[Director·场景布置] ║           自动布置事件场景: {news_item.title[:20]}...           ║")
            print(f"[Director·场景布置] ╚════════════════════════════════════════════════════════╝")
            print(f"[Director·场景布置] 关联NPC: {[n.name for n in event_npcs]}")
            
            # 2. 确定事发地点（选择第一个NPC的位置或附近建筑）
            main_npc = event_npcs[0]
            event_x = main_npc.rect.centerx
            event_y = main_npc.rect.centery
            
            # 尝试找到附近的建筑作为集合点
            buildings = [c for c in ctx.all_cards if isinstance(c, Building)]
            nearest_building = None
            nearest_dist = 9999
            for b in buildings:
                dist = math.hypot(b.rect.centerx - event_x, b.rect.centery - event_y)
                if dist < nearest_dist and dist < 400:
                    nearest_dist = dist
                    nearest_building = b
            
            if nearest_building:
                event_x = nearest_building.rect.centerx
                event_y = nearest_building.rect.centery + 50
                event_location_name = getattr(nearest_building, 'name', '附近')
                print(f"[Director·场景布置] 集合地点: {event_location_name} ({event_x}, {event_y})")
            else:
                event_location_name = "事发现场"
                print(f"[Director·场景布置] 集合地点: NPC当前位置 ({event_x}, {event_y})")
            
            # 3. 【瞬移+保护】让所有相关NPC瞬移到事发地点并进入剧情保护状态
            for i, npc in enumerate(event_npcs):
                # 【演出状态恢复】确保NPC能够参与演出
                from src.definitions import SAFETY_DOWNED, STATE_DOWNED, STATE_COMBAT
                
                # 【战斗脱离】如果NPC正在战斗中，强制结束战斗
                if getattr(npc, 'aggro_target', None) is not None:
                    npc.aggro_target = None
                if getattr(npc, 'in_combat', False):
                    npc.in_combat = False
                if hasattr(npc, 'hatred'):
                    npc.hatred.clear()
                
                # 【重伤恢复】如果NPC处于DOWNED状态，恢复其行动能力
                original_safety = getattr(npc, 'safety', SAFETY_NORMAL)
                original_state = getattr(npc, 'state', 'IDLE')
                if original_safety == SAFETY_DOWNED or original_state == STATE_DOWNED:
                    npc.safety = SAFETY_NORMAL
                    max_hp = getattr(npc, 'max_hp', 100)
                    if npc.hp <= 0 and max_hp > 0:
                        npc.hp = int(max_hp * 0.1)
                        print(f"[Director·场景布置] NPC {npc.name} 从重伤恢复，血量: {npc.hp}")
                
                # 【负面状态清除】
                if hasattr(npc, 'hunger') and npc.hunger <= 10:
                    npc.hunger = 30
                if hasattr(npc, 'temperature') and npc.temperature <= 10:
                    npc.temperature = 30
                
                # 【清除被背负状态】
                if hasattr(npc, 'stack_parent') and npc.stack_parent:
                    carrier = npc.stack_parent
                    npc.stack_parent = None
                    if hasattr(carrier, 'dragging') and carrier.dragging == npc:
                        carrier.dragging = None
                
                # 【瞬移】使用 set_pos 设置NPC位置（分散站位）
                offset_x = (i % 3 - 1) * 80  # -80, 0, +80
                offset_y = (i // 3) * 100   # 0, 100, 200
                target_x = event_x + offset_x
                target_y = event_y + offset_y
                
                # 使用 set_pos 方法设置位置（传入中心点坐标）
                npc.set_pos(target_x, target_y, reason=f"事件场景布置: {news_item.title[:15]}")
                
                # 【状态保护】设置为事件状态（暂停AI，防止被攻击等中断）
                npc.state = STATE_EVENT
                npc.ai_reason = f"等待演绎: {news_item.title[:15]}..."
                
                # 【事件保护标记】防止战斗系统/其他系统干扰
                npc._event_protected = True
                npc._event_news_id = getattr(news_item, 'news_id', None)
                
                print(f"[Director·场景布置] ✓ {npc.name} 已瞬移到 ({target_x}, {target_y}) 并进入剧情保护")
            
            # 4. 【保存事件信息】供后续玩家到达检测使用
            ctx._pending_event_news = news_item
            ctx._pending_event_location = (event_x, event_y)
            ctx._pending_event_npcs = event_npcs
            ctx._pending_event_location_name = event_location_name
            ctx._pending_event_active = True
            ctx._pending_event_start_time = time.time()
            
            # 5. 【添加围观群众】从 comments 中提取围观者并瞬移到周围
            self._spawn_spectators_from_comments(ctx, event_x, event_y, event_npcs, news_item)
            
            print(f"[Director·场景布置] 场景布置完成！等待玩家前往...")
            print(f"{'='*70}\n")
            
        except Exception as e:
            print(f"[Director·场景布置] 错误: {e}")
            import traceback
            traceback.print_exc()
    
    
    def _spawn_spectators_from_comments(self, ctx, event_x: int, event_y: int, event_npcs: list, news_item: LiveNewsItem):
        """
        从 news_item.comments 中提取围观群众并瞬移到事件周围
        
        Args:
            ctx: 游戏上下文
            event_x, event_y: 事件中心坐标
            event_npcs: 已参与事件的NPC列表（避免重复）
            news_item: 新闻事件对象
        """
        from src.entities import NPC
        import random
        import math
        
        # 获取评论列表
        comments = getattr(news_item, 'comments', [])
        if not comments:
            return
        
        # 从 comments 中提取 user 名字
        spectator_names = []
        for comment in comments:
            user_name = comment.get('user', '')
            if user_name and user_name not in spectator_names:
                spectator_names.append(user_name)
        
        if not spectator_names:
            return
        
        # 获取事件NPC的名字集合（避免重复）
        event_npc_names = {npc.name for npc in event_npcs}
        
        # 在 all_cards 中查找匹配的NPC
        spectators = []
        for card in ctx.all_cards:
            if not isinstance(card, NPC):
                continue
            card_name = getattr(card, 'name', '')
            # 如果评论者的名字匹配某个NPC，且该NPC不在事件中
            if card_name in spectator_names and card_name not in event_npc_names:
                spectators.append(card)
        
        if not spectators:
            print(f"[Director·场景布置] 未找到评论中提到的围观NPC")
            return
        
        print(f"[Director·场景布置] 从评论中找到 {len(spectators)} 位围观群众: {[n.name for n in spectators]}")
        
        # 瞬移围观群众到事件周围
        for i, npc in enumerate(spectators):
            # 在事件周围随机位置（距离150-280像素）
            angle = random.uniform(0, 3.14159 * 2)
            distance = random.uniform(150, 280)
            spectator_x = int(event_x + math.cos(angle) * distance)
            spectator_y = int(event_y + math.sin(angle) * distance)
            
            # 瞬移到围观位置（使用 set_pos）
            npc.set_pos(spectator_x, spectator_y, reason=f"围观事件: {news_item.title[:10]}")
            
            # 设置为围观状态
            npc.ai_reason = "围观事件..."
            
            print(f"[Director·场景布置]   👥 {npc.name} 作为围观群众出现在 ({spectator_x}, {spectator_y})")
    
    
    def get_pending_news_item(self) -> Optional[LiveNewsItem]:
        """获取待展示的新闻事件"""
        result = self.pending_news_item
        self.pending_news_item = None
        return result
    
    # ═══════════════════════════════════════════════════════════════
    # 状态查询与强制触发
    # ═══════════════════════════════════════════════════════════════
    
    def is_generating(self) -> bool:
        """检查是否正在生成事件"""
        return getattr(self, '_generating', False)
    
    def is_generation_timeout(self, timeout_sec: float = 30.0) -> bool:
        """检查事件生成是否超时"""
        if not self.is_generating():
            return False
        start = getattr(self, '_generation_start_time', 0)
        return (time.time() - start) > timeout_sec
    
    def force_trigger_event(self, ctx) -> bool:
        """
        强制触发一次AI事件生成（调试用）
        
        返回 True 表示已发起请求，False 表示已有请求进行中
        """
        if self.is_generating() and not self.is_generation_timeout():
            return False
        
        self._generating = True
        self._generation_start_time = time.time()
        
        def _run():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.direct_event(ctx))
            except Exception as e:
                log_game_event(f"[Director] force_trigger_event 异常: {e}", tag="DIRECTOR")
            finally:
                self._generating = False
        
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return True
    


# ═══════════════════════════════════════════════════════════════
# 单例工厂
# ═══════════════════════════════════════════════════════════════
_director_instance: Optional[AIDirector] = None

def get_director() -> AIDirector:
    """获取全局唯一的AIDirector实例"""
    global _director_instance
    if _director_instance is None:
        _director_instance = AIDirector()
    return _director_instance




