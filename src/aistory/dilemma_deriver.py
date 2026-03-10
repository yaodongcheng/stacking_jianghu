"""
困境生成器 (DilemmaDeriver)

从NPC的原始数据中自动识别困境。
不需要手写任何剧情——困境从人物关系和处境中涌现。
"""

import json
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

from .dilemma_seed import NPCDilemmaSeed, Tension, TensionType, StoryBeat, DilemmaPhase
from .shared_types import WorldSnapshot


@dataclass
class NPCData:
    """
    NPC数据包装类
    
    这是aistory模块使用的完整NPC数据定义。
    与director_system中的简单Dict不同，这是强类型的。
    """
    npc_id: str
    name: str
    gender: str = ""
    age: int = 0
    identity: str = ""           # 身份/职业
    org: str = ""                # 所属组织
    personality: str = ""        # 性格描述（自然语言，向后兼容）
    backstory: str = ""          # 背景故事
    
    # 状态属性
    wealth: int = 0              # 财富（文）
    emotion: int = 50            # 情绪（0-100）
    health: int = 100            # 健康（0-100）
    
    # 标签和描述
    tags: List[str] = field(default_factory=list)
    desc: str = ""               # 人设描述
    location: str = ""           # 当前位置
    
    # 关系
    spouse_id: Optional[str] = None
    master_id: Optional[str] = None
    grudge_target: Optional[str] = None
    
    # === 多维度性格系统（太阁5风格）===
    temper: str = ""             # 脾气: 性急/温和
    spirit: str = ""             # 胆量: 勇敢/谨慎
    ism: str = ""                # 主义: 理想/现实
    act_style: str = ""          # 风格: 慎重/大胆
    friendship: str = ""         # 情义: 重视/轻视
    ambition: int = 50           # 野心: 0-100
    desire_type: str = ""        # 物欲类型: 金钱/权力/名声/知识/安稳
    desire_level: str = ""       # 物欲程度: 低/普通/高/极高
    
    # 人情值系统
    social_credit: int = 0       # 人情值: 正数=NPC欠玩家, 负数=玩家欠NPC
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'NPCData':
        """从字典创建（兼容director_system的NPC格式）"""
        return cls(
            npc_id=str(data.get('id', data.get('npc_id', ''))),
            name=data.get('name', ''),
            gender=data.get('gender', ''),
            age=data.get('age', 0),
            identity=data.get('job', data.get('identity', '')),
            org=data.get('org', data.get('org_id', '')),
            personality=data.get('personality', ''),
            backstory=data.get('backstory', ''),
            wealth=data.get('wealth', data.get('money', 0)),
            emotion=data.get('emotion', 50),
            health=data.get('health', 100),
            tags=data.get('tags', []),
            desc=data.get('desc', ''),
            location=data.get('location', ''),
            spouse_id=data.get('spouse_id'),
            master_id=data.get('master_id'),
            grudge_target=data.get('grudge_target'),
            # 多维度性格
            temper=data.get('temper', ''),
            spirit=data.get('spirit', ''),
            ism=data.get('ism', ''),
            act_style=data.get('act_style', ''),
            friendship=data.get('friendship', ''),
            ambition=data.get('ambition', 50),
            desire_type=data.get('desire_type', ''),
            desire_level=data.get('desire_level', ''),
            social_credit=data.get('social_credit', 0)
        )
    
    def get_personality_profile(self) -> str:
        """生成性格画像（用于LLM提示词）"""
        lines = []
        
        # 基础性格
        traits = []
        if self.temper:
            traits.append(f"脾气{self.temper}")
        if self.spirit:
            traits.append(f"胆量{self.spirit}")
        if self.ism:
            traits.append(f"{self.ism}主义")
        if self.act_style:
            traits.append(f"行事{self.act_style}")
        if self.friendship:
            traits.append(f"{self.friendship}")
        
        if traits:
            lines.append(f"性格特质：{'，'.join(traits)}")
        
        # 野心和物欲
        if self.ambition != 50:
            ambition_desc = "野心勃勃" if self.ambition > 70 else "胸无大志" if self.ambition < 30 else f"野心{self.ambition}/100"
            lines.append(f"野心程度：{ambition_desc}")
        
        if self.desire_type and self.desire_level:
            lines.append(f"物欲倾向：{self.desire_type}（{self.desire_level}）")
        
        # 人情往来
        if self.social_credit != 0:
            if self.social_credit > 0:
                lines.append(f"人情往来：欠玩家 {self.social_credit} 点人情")
            else:
                lines.append(f"人情往来：玩家欠其 {-self.social_credit} 点人情")
        
        # 向后兼容：如果有多维性格就用它，否则用旧的personality字符串
        if lines:
            return '\n'.join(lines)
        return self.personality if self.personality else "性格信息暂无"
    
    def get_behavior_tendency(self) -> Dict[str, Any]:
        """获取行为倾向（用于启发式规则）"""
        return {
            'risk_taking': self.spirit == '勇敢' or self.act_style == '大胆',
            'pragmatic': self.ism == '现实',
            'loyal': self.friendship == '重视情义',
            'impulsive': self.temper == '性急',
            'ambitious': self.ambition > 60,
            'content': self.ambition < 40
        }


class DilemmaDeriver:
    """
    困境生成器 - 使用LLM从NPC数据中自动识别困境
    
    核心功能：
    1. derive_tensions() - 分析NPC，识别潜在张力
    2. calculate_heat() - 计算困境热度
    3. create_seed() - 为NPC创建完整的困境种子
    """
    
    def __init__(self, llm_service=None):
        self.llm = llm_service
        self._cache: Dict[str, NPCDilemmaSeed] = {}
    
    async def derive_tensions(self, npc: NPCData, world_state: WorldSnapshot) -> List[Tension]:
        """
        为NPC派生张力线（公共接口）
        
        Args:
            npc: NPC数据
            world_state: 世界状态
            
        Returns:
            张力线列表
        """
        if self.llm:
            return await self._derive_tensions_with_llm(npc, world_state)
        else:
            return self._derive_tensions_heuristic(npc, world_state)
    
    async def create_seed(self, npc: NPCData, world_state: WorldSnapshot) -> NPCDilemmaSeed:
        """
        为NPC创建完整的困境种子
        
        流程：
        1. 派生张力线
        2. 计算热度
        3. 组装成种子
        """
        seed = NPCDilemmaSeed(npc_id=npc.npc_id)
        
        # 1. 派生核心矛盾
        seed.desire, seed.reality_block = self._derive_core_conflict(npc)
        
        # 2. 派生张力线（使用LLM）
        if self.llm:
            seed.tensions = await self._derive_tensions_with_llm(npc, world_state)
        else:
            # 无LLM时使用启发式规则
            seed.tensions = self._derive_tensions_heuristic(npc, world_state)
        
        # 3. 计算热度
        seed.heat = self.calculate_heat(seed, world_state)
        
        # 缓存
        self._cache[npc.npc_id] = seed
        
        return seed
    
    async def _derive_tensions_with_llm(self, npc: NPCData, world_state: WorldSnapshot) -> List[Tension]:
        """使用LLM分析NPC数据，识别潜在张力"""
        
        # 获取性格画像和行为倾向
        personality_profile = npc.get_personality_profile()
        behavior = npc.get_behavior_tendency()
        
        # 构建性格对困境的影响提示
        personality_impact = []
        if behavior['risk_taking']:
            personality_impact.append("此人敢于冒险，困境可能涉及高风险高回报的选择")
        if behavior['pragmatic']:
            personality_impact.append("此人现实务实，困境通常是利益权衡而非道德困境")
        if behavior['loyal']:
            personality_impact.append("此人重视情义，困境常涉及对朋友/家人的忠诚考验")
        if behavior['impulsive']:
            personality_impact.append("此人性子急躁，容易因冲动而陷入麻烦")
        if behavior['ambitious']:
            personality_impact.append("此人野心勃勃，困境常与向上爬升的欲望有关")
        if behavior['content']:
            personality_impact.append("此人安于现状，困境常是被迫改变或卷入纷争")
        
        impact_text = '\n'.join(f"- {p}" for p in personality_impact) if personality_impact else "（请根据性格自行推断）"
        
        prompt = f"""你是一个宋代市井故事的编剧。
分析以下人物的数据，识别出他/她人生中潜在的"张力"——
即两股对立的力量在拉扯这个人，让他/她迟早会面临两难困境。

【人物信息】
姓名：{npc.name}
性别：{npc.gender}  年龄：{npc.age}
职业：{npc.identity}
所属组织：{npc.org}
{personality_profile}
背景故事：{npc.backstory if npc.backstory else '暂无'}
当前经济状况：{npc.wealth} 文（{self._wealth_level(npc.wealth)}）
当前情绪：{npc.emotion}/100
当前健康：{npc.health}/100
人设描述：{npc.desc if npc.desc else '暂无'}

【此人的关系网】
{self._format_relationships(npc)}

【此人所属组织的处境】
{self._format_org_status(npc, world_state)}

【性格对困境类型的影响】
{impact_text}

请识别出1-3条张力线，每条格式必须是有效的JSON：
{{
    "type": "RELATIONSHIP/ECONOMIC/MORAL/IDENTITY/SURVIVAL/LOYALTY 之一",
    "force_a": "拉向一边的力量（用一句话描述）",
    "force_b": "拉向另一边的力量（用一句话描述）", 
    "intensity": 张力强度0-100,
    "related_npcs": ["涉及的其他NPC的ID或名字"],
    "potential_crisis": "如果这个张力爆发，最可能的危机场景是什么（一句话）"
}}

注意：
- 张力必须从数据中自然推导，不要凭空编造
- 必须充分考虑人物的性格维度（脾气、胆量、主义、情义等）
- 优先识别与其他NPC有关的张力（这样更有戏剧性）
- 强度要基于当前状况的紧迫程度（欠债快还不上了=高强度，暗恋还没表白=低强度）
- 必须返回JSON数组格式，如：[{{...}}, {{...}}]
"""
        
        try:
            response = await self.llm.generate(prompt)
            return self._parse_tensions(response)
        except Exception as e:
            print(f"[DilemmaDeriver] LLM张力派生失败: {e}")
            return self._derive_tensions_heuristic(npc, world_state)
    
    def _derive_tensions_heuristic(self, npc: NPCData, world_state: WorldSnapshot) -> List[Tension]:
        """启发式规则派生张力（无LLM时的备选）"""
        tensions = []
        
        # 经济张力
        if npc.wealth < 30:
            tensions.append(Tension(
                type=TensionType.ECONOMIC,
                force_a="想要维持生计、改善生活",
                force_b="现实的经济困境和债务压力",
                intensity=min(100, (30 - npc.wealth) * 3 + 30),
                potential_crisis="因无力还债而陷入困境，或被迫做出违背本心的事"
            ))
        
        # 生存张力
        if npc.health < 40:
            tensions.append(Tension(
                type=TensionType.SURVIVAL,
                force_a="想要活下去、恢复健康",
                force_b="缺乏医疗资源和经济能力",
                intensity=min(100, (40 - npc.health) * 2 + 50),
                potential_crisis="病重无力医治，可能寻求极端手段"
            ))
        
        # 情绪张力
        if npc.emotion < 30:
            tensions.append(Tension(
                type=TensionType.IDENTITY,
                force_a="想要摆脱负面情绪、重新振作",
                force_b="内心的绝望和外部环境的压迫",
                intensity=min(100, (30 - npc.emotion) * 2 + 40),
                potential_crisis="情绪崩溃，可能做出冲动或极端行为"
            ))
        
        # 组织忠诚张力
        if npc.org:
            org_tension = world_state.faction_tensions.get(npc.org, {})
            if org_tension.get('hostility', 0) > 50:
                tensions.append(Tension(
                    type=TensionType.LOYALTY,
                    force_a=f"对{npc.org}的忠诚",
                    force_b="组织内部斗争带来的生存压力",
                    intensity=org_tension.get('hostility', 50),
                    potential_crisis="被迫在忠诚和自保之间做出选择"
                ))
        
        return tensions
    
    def _derive_core_conflict(self, npc: NPCData) -> tuple:
        """派生核心矛盾：欲望 vs 现实阻碍（集成性格维度）"""
        
        behavior = npc.get_behavior_tendency()
        
        # === 基于多维度性格系统推断欲望 ===
        desire = ""
        
        # 1. 基于物欲类型和野心
        if npc.desire_type and npc.ambition != 50:
            if npc.desire_type == "金钱":
                if npc.ambition > 60:
                    desire = "想要积累大量财富，成为富甲一方的豪商"
                else:
                    desire = "想要衣食无忧，不为钱财发愁"
            elif npc.desire_type == "权力":
                if npc.ambition > 60:
                    desire = "想要掌握更大的权力，影响更多人"
                else:
                    desire = "想要获得一定的地位和话语权"
            elif npc.desire_type == "名声":
                if npc.ambition > 60:
                    desire = "想要名垂青史，成为人人敬仰的人物"
                else:
                    desire = "想要获得他人的尊重和认可"
            elif npc.desire_type == "知识":
                desire = "想要追求学问，增长见识"
            elif npc.desire_type == "安稳":
                desire = "想要过上平静安稳的生活"
        
        # 2. 基于职业推断（如果物欲类型不明确）
        if not desire:
            if "商" in npc.identity or npc.tags and "MERCHANT" in npc.tags:
                desire = "想要经商致富，改善生活"
            elif "官" in npc.identity or npc.tags and "OFFICIAL" in npc.tags:
                desire = "想要在仕途上有所成就"
            elif "武" in npc.identity or npc.tags and "WARRIOR" in npc.tags:
                desire = "想要在江湖上闯出名声"
            elif "农" in npc.identity:
                desire = "想要风调雨顺，安稳度日"
            elif behavior['ambitious']:
                desire = "想要出人头地，不再被人轻视"
            elif behavior['content']:
                desire = "想要安稳度日，不被打扰"
            else:
                desire = "想要过上更好的生活"
        
        # 3. 基于情义调整欲望描述
        if npc.friendship == "重视情义":
            desire += "，同时守护身边重要的人"
        elif npc.friendship == "轻视情义":
            desire += "，不惜为此牺牲人情往来"
        
        # === 基于性格推断阻碍 ===
        reality_block = ""
        
        # 1. 基于主义（理想vs现实）
        if npc.ism == "理想":
            if npc.wealth < 30:
                reality_block = "理想主义在贫困现实面前的无力"
            else:
                reality_block = "理想与世俗现实的冲突"
        elif npc.ism == "现实":
            if npc.wealth < 30:
                reality_block = "贫困的经济状况限制了选择"
            else:
                reality_block = "现实主义带来的道德困境"
        
        # 2. 基于行事风格
        if not reality_block:
            if npc.act_style == "慎重":
                reality_block = "过于谨慎导致错失机会"
            elif npc.act_style == "大胆":
                reality_block = "冒进带来的风险和后果"
        
        # 3. 基于现状（兜底逻辑）
        if not reality_block:
            if npc.wealth < 20:
                reality_block = "贫困的经济状况限制了选择"
            elif npc.wealth > 200:
                reality_block = "财富带来的嫉妒和觊觎"
            elif npc.org and "底层" in npc.org:
                reality_block = "出身卑微，缺乏上升渠道"
            elif npc.health < 50:
                reality_block = "身体抱恙，力不从心"
            else:
                reality_block = "复杂的人际关系和社会环境"
        
        # 4. 基于脾气调整
        if npc.temper == "性急":
            reality_block += "，加上急躁性格容易让事情变得更糟"
        
        return desire, reality_block
    
    def calculate_heat(self, seed: NPCDilemmaSeed, world_state: WorldSnapshot) -> float:
        """
        计算困境热度——导演用这个来决定优先安排哪个NPC的事件。
        
        热度来源：
        1. 张力强度本身
        2. 外部事件施压（如债主要来了、组织内斗加剧）
        3. 与玩家的关系亲密度（玩家更关心的人优先）
        4. 距离上次事件的时间间隔（太久没出现要降权，但积累的矛盾要升温）
        5. 与其他NPC故事线的交叉度
        """
        heat = 0.0
        
        # 基础张力热度
        for tension in seed.tensions:
            heat += tension.intensity * 0.3
        
        # 阶段加成
        phase_bonus = {
            DilemmaPhase.LATENT: 0,
            DilemmaPhase.SURFACED: 10,
            DilemmaPhase.ESCALATED: 25,
            DilemmaPhase.CRISIS: 40,
            DilemmaPhase.AFTERMATH: -50  # 已结束，降低热度
        }
        heat += phase_bonus.get(seed.phase, 0)
        
        # 时间压力
        if seed.story_beats:
            days_since_last = self._days_since(seed.story_beats[-1].timestamp)
            if seed.phase == DilemmaPhase.ESCALATED:
                heat += min(days_since_last * 5, 30)  # 升级阶段，每天热度+5
            elif seed.phase == DilemmaPhase.SURFACED:
                heat += min(days_since_last * 2, 15)  # 浮出水面，慢慢升温
        
        # 玩家关系加权
        player_relation = self._get_player_relation(seed.npc_id, world_state)
        if player_relation:
            heat += player_relation.get('closeness', 0) * 0.2  # 越亲近越优先
        
        # 交叉故事线加成
        cross_count = self._count_story_intersections(seed, world_state)
        heat += cross_count * 10  # 和其他活跃故事线有交叉的优先
        
        return min(heat, 100)
    
    def _parse_tensions(self, response: str) -> List[Tension]:
        """解析LLM返回的张力JSON"""
        tensions = []
        
        try:
            # 尝试提取JSON
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)
            
            if not isinstance(data, list):
                data = [data]
            
            for item in data:
                tension = Tension(
                    type=TensionType(item.get('type', 'RELATIONSHIP')),
                    force_a=item.get('force_a', ''),
                    force_b=item.get('force_b', ''),
                    intensity=float(item.get('intensity', 50)),
                    related_npcs=item.get('related_npcs', []),
                    potential_crisis=item.get('potential_crisis', '')
                )
                tensions.append(tension)
                
        except Exception as e:
            print(f"[DilemmaDeriver] 解析张力失败: {e}")
        
        return tensions
    
    def _wealth_level(self, wealth: int) -> str:
        """财富等级描述"""
        if wealth < 20:
            return "赤贫"
        elif wealth < 50:
            return "贫困"
        elif wealth < 100:
            return "一般"
        elif wealth < 200:
            return "小康"
        else:
            return "富裕"
    
    def _format_relationships(self, npc: NPCData) -> str:
        """格式化关系网信息"""
        # 这里可以从social_system获取真实关系
        # 简化版本返回占位
        return "（待从社交系统获取）"
    
    def _format_org_status(self, npc: NPCData, world_state: WorldSnapshot) -> str:
        """格式化组织处境"""
        if not npc.org:
            return "无组织"
        
        org_data = world_state.faction_tensions.get(npc.org, {})
        if org_data:
            hostility = org_data.get('hostility', 0)
            return f"{npc.org} - 敌对度: {hostility}"
        return f"{npc.org} - 状态平稳"
    
    def _days_since(self, timestamp: str) -> int:
        """计算距离某个时间戳的天数"""
        from datetime import datetime
        try:
            past = datetime.fromisoformat(timestamp)
            now = datetime.now()
            return (now - past).days
        except:
            return 0
    
    def _get_player_relation(self, npc_id: str, world_state: WorldSnapshot) -> Optional[Dict]:
        """获取玩家与NPC的关系"""
        return world_state.player_reputation.get(npc_id)
    
    def _count_story_intersections(self, seed: NPCDilemmaSeed, world_state: WorldSnapshot) -> int:
        """计算与其他活跃故事线的交叉数"""
        related = seed.get_related_npcs()
        count = 0
        
        for npc_id in related:
            other_seed = self._cache.get(npc_id)
            if other_seed and other_seed.phase not in [DilemmaPhase.LATENT, DilemmaPhase.AFTERMATH]:
                count += 1
        
        return count
    
    def get_seed(self, npc_id: str) -> Optional[NPCDilemmaSeed]:
        """获取缓存的困境种子"""
        return self._cache.get(npc_id)
    
    def update_seed(self, seed: NPCDilemmaSeed):
        """更新困境种子"""
        self._cache[seed.npc_id] = seed
    
    def get_all_active_seeds(self) -> List[NPCDilemmaSeed]:
        """获取所有活跃的困境种子（非LATENT、非AFTERMATH）"""
        return [
            seed for seed in self._cache.values()
            if seed.phase not in [DilemmaPhase.LATENT, DilemmaPhase.AFTERMATH]
        ]
    
    def get_hottest_seeds(self, limit: int = 5) -> List[NPCDilemmaSeed]:
        """获取热度最高的困境种子"""
        active = self.get_all_active_seeds()
        return sorted(active, key=lambda s: s.heat, reverse=True)[:limit]