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

# 导入日志函数
try:
    from src.utils import log_game_event
except ImportError:
    # 备用日志函数
    def log_game_event(text, tag="INFO"):
        print(f"[{tag}] {text}")


# 类型别名：NPC数据可以是字典或NPC对象
NPCData = Any  # 向前兼容：NPC对象或字典


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
        # 获取NPC属性（处理属性名差异）
        name = getattr(npc, 'name', '未知')
        money = getattr(npc, 'money', 0)
        emotion = getattr(npc, 'emotion', 50)
        health = getattr(npc, 'hp', getattr(npc, 'health', 100))  # NPC使用hp而不是health
        
        # 从personality获取性格属性
        personality = getattr(npc, 'personality', None)
        if personality:
            temper = getattr(personality, 'temper', 50)
            spirit = getattr(personality, 'spirit', 50)
            ism = getattr(personality, 'ism', 50)
            act_style = getattr(personality, 'act_style', 50)
            friendship = getattr(personality, 'friendship', 50)
            ambition = getattr(personality, 'ambition', 50)
        else:
            temper = spirit = ism = act_style = friendship = ambition = 50
        
        log_game_event(f"[DilemmaDeriver] 开始为 {name} 派生张力线", tag="DILEMMA")
        log_game_event(f"[DilemmaDeriver] NPC状态: 财富={money}, 情绪={emotion}, 健康={health}", tag="DILEMMA")
        log_game_event(f"[DilemmaDeriver] 性格特质: 脾气={temper}, 胆量={spirit}, 主义={ism}, 风格={act_style}, 情义={friendship}, 野心={ambition}", tag="DILEMMA")
        
        if self.llm:
            log_game_event(f"[DilemmaDeriver] 使用LLM派生张力", tag="DILEMMA")
            result = await self._derive_tensions_with_llm(npc, world_state)
        else:
            log_game_event(f"[DilemmaDeriver] 使用启发式规则派生张力", tag="DILEMMA")
            result = self._derive_tensions_heuristic(npc, world_state)
        
        log_game_event(f"[DilemmaDeriver] 为 {npc.name} 派生出 {len(result)} 条张力线", tag="DILEMMA")
        for i, t in enumerate(result, 1):
            log_game_event(f"[DilemmaDeriver] 张力{i}: [{t.type.value}] {t.force_a} vs {t.force_b} (强度:{t.intensity})", tag="DILEMMA")
        
        return result
    
    async def create_seed(self, npc: NPCData, world_state: WorldSnapshot) -> NPCDilemmaSeed:
        """
        为NPC创建完整的困境种子
        
        流程：
        1. 派生张力线
        2. 计算热度
        3. 组装成种子
        """
        seed = NPCDilemmaSeed(npc_id=npc.id)
        
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
        self._cache[npc.id] = seed
        
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
        if behavior['temper_hot']:
            personality_impact.append("此人脾气暴躁，容易因冲动而陷入麻烦")
        if behavior['ambitious']:
            personality_impact.append("此人野心勃勃，困境常与向上爬升的欲望有关")
        if behavior['content']:
            personality_impact.append("此人安于现状，困境常是被迫改变或卷入纷争")
        
        impact_text = '\n'.join(f"- {p}" for p in personality_impact) if personality_impact else "（请根据性格自行推断）"
        
        # 获取NPC属性（处理可能不存在的属性）
        name = getattr(npc, 'name', '未知')
        gender = getattr(npc, 'gender', '未知')
        age = getattr(npc, 'age', 30)
        job = getattr(npc, 'job', '平民')
        org_id = getattr(npc, 'org_id', '')
        money = getattr(npc, 'money', 0)
        emotion = getattr(npc, 'emotion', 50)
        health = getattr(npc, 'hp', getattr(npc, 'health', 100))
        desc = getattr(npc, 'desc', '')
        backstory = getattr(npc, 'backstory', '')
        
        prompt = f"""你是一个宋代市井故事的编剧。
分析以下人物的数据，识别出他/她人生中潜在的"张力"——
即两股对立的力量在拉扯这个人，让他/她迟早会面临两难困境。

【人物信息】
姓名：{name}
性别：{gender}  年龄：{age}
职业：{job}
所属组织：{org_id}
{personality_profile}
背景故事：{backstory if backstory else '暂无'}
当前经济状况：{money} 文（{self._wealth_level(money)}）
当前情绪：{emotion}/100
当前健康：{health}/100
人设描述：{desc if desc else '暂无'}

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
            # LLMService的chat方法不是异步的，不需要await
            response = self.llm.chat(
                system_prompt="你是一个分析人物性格和困境的编剧专家。",
                user_message=prompt,
                max_tokens=2000
            )
            # 如果response是对象，获取content属性；如果是字符串，直接使用
            response_text = response.content if hasattr(response, 'content') else str(response)
            return self._parse_tensions(response_text)
        except Exception as e:
            log_game_event(f"[DilemmaDeriver] LLM张力派生失败: {e}", tag="ERROR")
            # 异常时中止，不使用兜底方案
            raise
    
    def _derive_tensions_heuristic(self, npc: NPCData, world_state: WorldSnapshot) -> List[Tension]:
        """启发式规则派生张力（无LLM时的备选）"""
        tensions = []
        
        # 获取NPC属性（处理属性名差异）
        money = getattr(npc, 'money', 0)
        emotion = getattr(npc, 'emotion', 50)
        health = getattr(npc, 'hp', getattr(npc, 'health', 100))  # NPC使用hp而不是health
        org_id = getattr(npc, 'org_id', None)
        
        # 经济张力
        if money < 30:
            tensions.append(Tension(
                type=TensionType.ECONOMIC,
                force_a="想要维持生计、改善生活",
                force_b="现实的经济困境和债务压力",
                intensity=min(100, (30 - money) * 3 + 30),
                potential_crisis="因无力还债而陷入困境，或被迫做出违背本心的事"
            ))
        
        # 生存张力
        if health < 40:
            tensions.append(Tension(
                type=TensionType.SURVIVAL,
                force_a="想要活下去、恢复健康",
                force_b="缺乏医疗资源和经济能力",
                intensity=min(100, (40 - health) * 2 + 50),
                potential_crisis="病重无力医治，可能寻求极端手段"
            ))
        
        # 情绪张力
        if emotion < 30:
            tensions.append(Tension(
                type=TensionType.IDENTITY,
                force_a="想要摆脱负面情绪、重新振作",
                force_b="内心的绝望和外部环境的压迫",
                intensity=min(100, (30 - emotion) * 2 + 40),
                potential_crisis="情绪崩溃，可能做出冲动或极端行为"
            ))
        
        # 组织忠诚张力
        if npc.org_id:
            org_tension = world_state.faction_tensions.get(npc.org_id, {})
            if org_tension.get('hostility', 0) > 50:
                tensions.append(Tension(
                    type=TensionType.LOYALTY,
                    force_a=f"对{npc.org_id}的忠诚",
                    force_b="组织内部斗争带来的生存压力",
                    intensity=org_tension.get('hostility', 50),
                    potential_crisis="被迫在忠诚和自保之间做出选择"
                ))
        
        return tensions
    
    def _derive_core_conflict(self, npc: NPCData) -> tuple:
        """派生核心矛盾：欲望 vs 现实阻碍（集成数值型性格维度 0-100）"""
        
        behavior = npc.get_behavior_tendency()
        desc = npc.get_personality_description()
        
        # 从personality对象获取性格属性
        personality = getattr(npc, 'personality', None)
        if personality:
            desire_type = getattr(personality, 'desire_type', None)
            ambition = getattr(personality, 'ambition', 50)
            friendship = getattr(personality, 'friendship', 50)
            ism = getattr(personality, 'ism', 50)
            act_style = getattr(personality, 'act_style', 50)
            temper = getattr(personality, 'temper', 50)
        else:
            desire_type = None
            ambition = 50
            friendship = 50
            ism = 50
            act_style = 50
            temper = 50
        
        # === 基于多维度性格系统推断欲望 ===
        desire = ""
        
        # 1. 基于物欲类型和野心
        if desire_type and ambition != 50:
            if desire_type == "金钱":
                if ambition > 60:
                    desire = "想要积累大量财富，成为富甲一方的豪商"
                else:
                    desire = "想要衣食无忧，不为钱财发愁"
            elif desire_type == "权力":
                if ambition > 60:
                    desire = "想要掌握更大的权力，影响更多人"
                else:
                    desire = "想要获得一定的地位和话语权"
            elif desire_type == "名声":
                if ambition > 60:
                    desire = "想要名垂青史，成为人人敬仰的人物"
                else:
                    desire = "想要获得他人的尊重和认可"
            elif desire_type == "知识":
                desire = "想要追求学问，增长见识"
            elif desire_type == "安稳":
                desire = "想要过上平静安稳的生活"
            elif desire_type == "正义":
                desire = "想要伸张正义，惩治恶人"
        
        # 2. 基于职业推断（如果物欲类型不明确）
        if not desire:
            if "商" in npc.job or npc.tags and "MERCHANT" in npc.tags:
                desire = "想要经商致富，改善生活"
            elif "官" in npc.job or npc.tags and "OFFICIAL" in npc.tags:
                desire = "想要在仕途上有所成就"
            elif "武" in npc.job or npc.tags and "WARRIOR" in npc.tags:
                desire = "想要在江湖上闯出名声"
            elif "农" in npc.job:
                desire = "想要风调雨顺，安稳度日"
            elif behavior['ambitious']:
                desire = "想要出人头地，不再被人轻视"
            elif behavior['content']:
                desire = "想要安稳度日，不被打扰"
            else:
                desire = "想要过上更好的生活"
        
        # 3. 基于情义调整欲望描述（数值型：越小越重情义）
        if friendship < 40:  # 重情义
            desire += "，同时守护身边重要的人"
        elif friendship > 60:  # 不重情义
            desire += "，不惜为此牺牲人情往来"
        
        # === 基于性格推断阻碍 ===
        reality_block = ""
        
        # 1. 基于主义（理想vs现实，数值型：越小越理想）
        if ism < 40:  # 理想主义
            if npc.money < 30:
                reality_block = "理想主义在贫困现实面前的无力"
            else:
                reality_block = "理想与世俗现实的冲突"
        elif ism > 60:  # 现实主义
            if npc.money < 30:
                reality_block = "贫困的经济状况限制了选择"
            else:
                reality_block = "现实主义带来的道德困境"
        
        # 2. 基于行事风格（数值型：越小越缜密）
        if not reality_block:
            if act_style < 40:  # 缜密
                reality_block = "过于谨慎导致错失机会"
            elif act_style > 60:  # 豪放/大胆
                reality_block = "冒进带来的风险和后果"
        
        # 3. 基于现状（兜底逻辑）
        # 获取健康值（NPC使用hp而不是health）
        health = getattr(npc, 'hp', getattr(npc, 'health', 100))
        if not reality_block:
            if npc.money < 20:
                reality_block = "贫困的经济状况限制了选择"
            elif npc.money > 200:
                reality_block = "财富带来的嫉妒和觊觎"
            elif npc.org_id and "底层" in npc.org_id:
                reality_block = "出身卑微，缺乏上升渠道"
            elif health < 50:
                reality_block = "身体抱恙，力不从心"
            else:
                reality_block = "复杂的人际关系和社会环境"
        
        # 4. 基于脾气调整（数值型：越大越暴躁）
        if temper > 60:  # 暴躁
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
        player_relation = self._get_player_relation(seed.id, world_state)
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
        if not npc.org_id:
            return "无组织"
        
        org_data = world_state.faction_tensions.get(npc.org_id, {})
        if org_data:
            hostility = org_data.get('hostility', 0)
            return f"{npc.org_id} - 敌对度: {hostility}"
        return f"{npc.org_id} - 状态平稳"
    
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
        self._cache[seed.id] = seed
    
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