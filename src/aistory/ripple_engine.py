"""
涟漪扩散器 (RippleEngine)

事件对其他人的影响。
当玩家做出选择，"涟漪"会扩散到相关NPC的社交圈。
"""

import json
import re
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from enum import Enum

from .dilemma_seed import NPCDilemmaSeed, DilemmaPhase, Tension
# NPCData 类型别名 - 直接使用NPC对象
from typing import Any
NPCData = Any


class RippleType(Enum):
    """涟漪类型"""
    DIRECT_IMPACT = "direct_impact"      # 直接影响（如：救的人、伤害的人）
    SOCIAL_CHAIN = "social_chain"        # 社交链反应（如：家人、朋友）
    ORG_REACTION = "org_reaction"        # 组织反应（如：帮派、官府）
    RUMOR_SPREAD = "rumor_spread"        # 谣言传播
    ECONOMIC_WAVE = "economic_wave"      # 经济波动（如：物价、工资）


@dataclass
class RippleEffect:
    """涟漪效果"""
    target_npc_id: str                   # 目标NPC
    ripple_type: RippleType              # 涟漪类型
    description: str                     # 描述
    tension_changes: List[Dict] = None   # 张力变化
    stat_changes: Dict[str, int] = None  # 属性变化
    new_tensions: List[Tension] = None   # 新增张力
    heat_delta: int = 0                  # 热度变化
    
    def __post_init__(self):
        if self.tension_changes is None:
            self.tension_changes = []
        if self.stat_changes is None:
            self.stat_changes = {}
        if self.new_tensions is None:
            self.new_tensions = []


@dataclass
class SocialLink:
    """社交关系"""
    source_id: str
    target_id: str
    relation_type: str       # 如：family, friend, colleague, rival
    strength: int            # 关系强度 1-100
    is_mutual: bool = True   # 是否双向


class RippleEngine:
    """
    涟漪引擎
    
    核心逻辑：
    1. 识别受影响的目标（直接关系、社交链、组织）
    2. 计算涟漪强度（基于关系强度、事件重要性）
    3. 生成涟漪效果（张力变化、属性变化、新增张力）
    4. 应用涟漪到目标NPC
    """
    
    def __init__(self, llm_service=None):
        self.llm = llm_service
        self.social_graph: Dict[str, List[SocialLink]] = {}  # 社交图
    
    def register_social_link(self, link: SocialLink):
        """注册社交关系"""
        if link.source_id not in self.social_graph:
            self.social_graph[link.source_id] = []
        self.social_graph[link.source_id].append(link)
        
        # 双向关系
        if link.is_mutual:
            reverse = SocialLink(
                source_id=link.target_id,
                target_id=link.source_id,
                relation_type=link.relation_type,
                strength=link.strength,
                is_mutual=True
            )
            if reverse.source_id not in self.social_graph:
                self.social_graph[reverse.source_id] = []
            self.social_graph[reverse.source_id].append(reverse)
    
    async def propagate(self,
                        source_npc: NPCData,
                        source_seed: NPCDilemmaSeed,
                        player_choice: str,
                        consequence: str,
                        affected_npcs: List[NPCData]) -> List[RippleEffect]:
        """
        传播涟漪效果
        
        Args:
            source_npc: 事件源NPC
            source_seed: 事件源困境
            player_choice: 玩家选择
            consequence: 事件后果
            affected_npcs: 可能受影响的NPC列表
        
        Returns:
            涟漪效果列表
        """
        ripples = []
        
        # 1. 识别受影响的目标
        targets = self._identify_targets(source_npc, affected_npcs)
        
        # 2. 对每个目标生成涟漪效果
        for target in targets:
            if target.npc_id == source_npc.npc_id:
                continue
            
            # 使用LLM或启发式生成涟漪
            if self.llm:
                ripple = await self._generate_ripple_with_llm(
                    source_npc, source_seed, target, 
                    player_choice, consequence
                )
            else:
                ripple = self._generate_ripple_heuristic(
                    source_npc, source_seed, target,
                    player_choice, consequence
                )
            
            if ripple:
                ripples.append(ripple)
        
        return ripples
    
    def _identify_targets(self, 
                         source_npc: NPCData, 
                         all_npcs: List[NPCData]) -> List[NPCData]:
        """识别受影响的NPC目标"""
        targets = []
        
        # 1. 直接关系（同组织、同地点）
        for npc in all_npcs:
            if npc.npc_id == source_npc.npc_id:
                continue
            
            # 同组织
            if npc.org and npc.org == source_npc.org:
                targets.append(npc)
                continue
            
            # 同地点
            if npc.location == source_npc.location:
                targets.append(npc)
                continue
        
        # 2. 社交链关系
        if source_npc.npc_id in self.social_graph:
            for link in self.social_graph[source_npc.npc_id]:
                for npc in all_npcs:
                    if npc.npc_id == link.target_id:
                        if npc not in targets:
                            targets.append(npc)
                        break
        
        return targets
    
    async def _generate_ripple_with_llm(self,
                                        source: NPCData,
                                        source_seed: NPCDilemmaSeed,
                                        target: NPCData,
                                        player_choice: str,
                                        consequence: str) -> Optional[RippleEffect]:
        """使用LLM生成涟漪效果"""
        
        # 获取关系信息
        relation = self._get_relation(source.npc_id, target.npc_id)
        
        prompt = f"""分析以下事件对第三方NPC的影响。

===== 事件源 =====
NPC: {source.name}
事件: {source_seed.dilemma_summary}
玩家选择: {player_choice}
后果: {consequence}

===== 受影响NPC =====
姓名: {target.name}
身份: {target.identity}
性格: {target.personality}
当前情绪: {target.emotion}/100
所属组织: {target.org or '无'}

===== 关系 =====
{relation or '无明显关系'}

===== 分析任务 =====
判断这个事件如何影响{target.name}：
1. 是否会产生新的内心张力？（如：看到朋友被帮助→自己也想被关注）
2. 属性会如何变化？（情绪、健康、财富）
3. 热度如何变化？（是否更值得关注）

请以JSON格式输出：
{{
    "affected": true/false,
    "ripple_type": "direct_impact/social_chain/org_reaction/rumor_spread/economic_wave",
    "description": "具体影响描述",
    "tension_changes": [
        {{"tension_id": "张力ID", "delta": 变化值}}
    ],
    "new_tensions": [
        {{"force_a": "张力A", "force_b": "张力B", "intensity": 强度}}
    ],
    "stat_changes": {{
        "emotion": 情绪变化,
        "health": 健康变化,
        "wealth": 财富变化
    }},
    "heat_delta": 热度变化
}}

如果几乎没有影响，设置affected为false。
"""
        
        try:
            response = await self.llm.generate(prompt)
            return self._parse_ripple_response(response, target.npc_id)
        except Exception as e:
            print(f"[RippleEngine] LLM生成涟漪失败: {e}")
            return None
    
    def _generate_ripple_heuristic(self,
                                   source: NPCData,
                                   source_seed: NPCDilemmaSeed,
                                   target: NPCData,
                                   player_choice: str,
                                   consequence: str) -> Optional[RippleEffect]:
        """启发式生成涟漪效果（无LLM时）"""
        
        # 同组织成员受影响
        if source.org and source.org == target.org:
            # 组织声誉受损或受益
            if '帮' in consequence or '组织' in consequence:
                return RippleEffect(
                    target_npc_id=target.npc_id,
                    ripple_type=RippleType.ORG_REACTION,
                    description=f"因{source.name}的事件，对组织产生看法",
                    stat_changes={"emotion": -5},
                    heat_delta=5
                )
        
        # 同地点的谣言传播
        if source.location == target.location:
            if len(source_seed.story_beats) >= 2:  # 故事有一定发展
                return RippleEffect(
                    target_npc_id=target.npc_id,
                    ripple_type=RippleType.RUMOR_SPREAD,
                    description=f"听说了{source.name}的事情",
                    heat_delta=3
                )
        
        # 社交关系影响
        relation = self._get_relation(source.npc_id, target.npc_id)
        if relation:
            if relation.relation_type in ['family', 'friend']:
                return RippleEffect(
                    target_npc_id=target.npc_id,
                    ripple_type=RippleType.SOCIAL_CHAIN,
                    description=f"因{relation.relation_type}关系受到牵连",
                    stat_changes={"emotion": -10 if '伤害' in consequence else 5},
                    heat_delta=relation.strength // 10
                )
        
        return None
    
    def _parse_ripple_response(self, response: str, target_id: str) -> Optional[RippleEffect]:
        """解析LLM的涟漪响应"""
        
        try:
            # 提取JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)
            
            if not data.get('affected', False):
                return None
            
            # 解析涟漪类型
            type_str = data.get('ripple_type', 'social_chain')
            ripple_type = RippleType(type_str)
            
            # 解析新张力
            new_tensions = []
            for t_data in data.get('new_tensions', []):
                new_tensions.append(Tension(
                    tension_id=f"ripple_{target_id}_{t_data['force_a']}",
                    force_a=t_data['force_a'],
                    force_b=t_data['force_b'],
                    intensity=t_data.get('intensity', 50)
                ))
            
            return RippleEffect(
                target_npc_id=target_id,
                ripple_type=ripple_type,
                description=data.get('description', ''),
                tension_changes=data.get('tension_changes', []),
                stat_changes=data.get('stat_changes', {}),
                new_tensions=new_tensions,
                heat_delta=data.get('heat_delta', 0)
            )
            
        except Exception as e:
            print(f"[RippleEngine] 解析涟漪响应失败: {e}")
            return None
    
    def _get_relation(self, source_id: str, target_id: str) -> Optional[SocialLink]:
        """获取两个NPC之间的关系"""
        if source_id in self.social_graph:
            for link in self.social_graph[source_id]:
                if link.target_id == target_id:
                    return link
        return None
    
    def apply_ripple(self, 
                    ripple: RippleEffect,
                    target_seed: NPCDilemmaSeed,
                    target_npc: NPCData) -> bool:
        """
        应用涟漪效果到目标NPC
        
        Returns:
            是否成功应用
        """
        # 1. 应用属性变化
        for stat, delta in ripple.stat_changes.items():
            if hasattr(target_npc, stat):
                current = getattr(target_npc, stat)
                new_val = max(0, min(100, current + delta))
                setattr(target_npc, stat, new_val)
        
        # 2. 应用张力变化
        for change in ripple.tension_changes:
            tension_id = change.get('tension_id')
            delta = change.get('delta', 0)
            
            for tension in target_seed.tensions:
                if tension.tension_id == tension_id:
                    tension.intensity = max(0, min(100, tension.intensity + delta))
                    break
        
        # 3. 添加新张力
        target_seed.tensions.extend(ripple.new_tensions)
        
        # 4. 更新热度
        target_seed.heat = max(0, min(100, target_seed.heat + ripple.heat_delta))
        
        print(f"[RippleEngine] 涟漪应用到 {target_npc.name}: {ripple.description}")
        return True
    
    def get_propagation_radius(self, 
                              source_npc: NPCData,
                              event_importance: int = 50) -> int:
        """
        计算涟漪传播半径
        
        基于：
        - 事件重要性
        - NPC的社交影响力
        - 当前世界状态
        
        Returns:
            传播层数（0表示不传播）
        """
        # 基础半径
        base_radius = 1
        
        # 事件重要性加成
        if event_importance > 80:
            base_radius += 2
        elif event_importance > 50:
            base_radius += 1
        
        # NPC影响力（通过组织判断）
        if source_npc.org:
            base_radius += 1
        
        return min(base_radius, 3)  # 最大3层