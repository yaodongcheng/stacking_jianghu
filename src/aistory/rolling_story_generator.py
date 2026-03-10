"""
滚动故事生成器 (RollingStoryGenerator)

不预写多幕，每一步都是基于"当前状态"即时生成下一步。
这是实现"玩家选择不确定，空间不会爆炸"的关键。
"""

import json
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

from .dilemma_seed import NPCDilemmaSeed, DilemmaPhase, StoryBeat
from .dilemma_deriver import NPCData
from .shared_types import WorldSnapshot


@dataclass
class PlayerData:
    """玩家数据"""
    money: int = 0
    stamina: int = 100
    reputation: int = 0
    inventory: Dict[str, int] = field(default_factory=dict)
    
    @property
    def inventory_summary(self) -> str:
        if not self.inventory:
            return "无"
        items = [f"{k}:{v}" for k, v in list(self.inventory.items())[:5]]
        return ", ".join(items)


@dataclass
class EventChoice:
    """事件选项"""
    text: str = ""                           # 选项描述
    cost: str = ""                           # 代价描述（消耗什么资源/得罪谁/花多少时间）
    consequence: str = ""                    # 可能后果
    effect: str = ""                         # 效果字符串（用于程序解析）
    hidden: bool = False                     # 是否是隐藏选项
    unlock_condition: str = ""               # 解锁条件
    heat_delta: float = 0.0                  # 选择此选项对热度的影响


@dataclass
class EventCard:
    """事件卡 - 滚动生成的故事节拍"""
    id: str = ""
    title: str = ""                          # 事件标题
    description: str = ""                    # 事件描述（2-3句话）
    npc_id: str = ""                         # 主要NPC
    choices: List[EventChoice] = field(default_factory=list)
    ignore_consequence: str = ""             # 如果玩家忽略，NPC自己会怎么做
    emotion_tone: str = ""                   # 情绪基调（用于配图）
    phase: DilemmaPhase = DilemmaPhase.LATENT
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "npc_id": self.npc_id,
            "choices": [
                {
                    "text": c.text,
                    "cost": c.cost,
                    "consequence": c.consequence,
                    "effect": c.effect,
                    "hidden": c.hidden,
                    "unlock_condition": c.unlock_condition
                } for c in self.choices
            ],
            "ignore_consequence": self.ignore_consequence,
            "emotion_tone": self.emotion_tone,
            "phase": self.phase.value
        }


class RollingStoryGenerator:
    """
    滚动式故事生成器——每次只生成下一个节拍
    
    核心原则：
    - 不预写全部四幕，只基于当前状态生成下一步
    - 每个选项必须有真实代价
    - 两难设计：不能有一个选项明显更好
    """
    
    def __init__(self, llm_service=None):
        self.llm = llm_service
    
    async def generate_next_beat(self,
                                  npc: NPCData,
                                  seed: NPCDilemmaSeed,
                                  world_state: WorldSnapshot,
                                  player: PlayerData) -> EventCard:
        """
        生成下一个故事节拍
        
        基于：
        - NPC当前状态
        - 已发生的故事
        - 当前困境阶段
        - 玩家资源状况
        """
        
        # 构建已有故事的摘要
        story_so_far = self._summarize_story_beats(seed.story_beats)
        
        # 获取阶段指导
        phase_instruction = self._get_phase_instruction(seed.phase)
        
        prompt = f"""你是宋代市井剧的编剧。现在需要为一个人物生成【下一个故事节拍】。

===== 人物档案 =====
姓名：{npc.name}
性别：{npc.gender}  年龄：{npc.age}
职业：{npc.identity}
所属组织：{npc.org}
{npc.get_personality_profile()}
背景故事：{npc.backstory if npc.backstory else '暂无'}
当前经济状况：{npc.wealth} 文
当前情绪：{npc.emotion}/100
当前健康：{npc.health}/100

===== 此人当前的困境 =====
核心矛盾：{seed.desire} vs {seed.reality_block}
当前张力：
{self._format_tensions(seed)}

===== 性格对叙事的影响 =====
{self._get_personality_narrative_guidance(npc)}

===== 至今为止发生的故事 =====
{story_so_far if story_so_far else "（这是此人的第一个故事节拍）"}

===== 当前阶段 =====
困境阶段：{seed.phase.value}
{phase_instruction}

===== 世界近况 =====
{self._format_relevant_world_events(npc, world_state)}

===== 玩家信息 =====
玩家当前状况：银钱 {player.money} 文，体力 {player.stamina}，声望 {player.reputation}
玩家当前拥有的资源：{player.inventory_summary}

===== 任务 =====
生成此人的【下一个故事节拍】。要求：

1. 事件描述（2-3句话，描述发生了什么，玩家看到了什么）

2. 两个选项（每个选项都必须有真实代价）：
   【两难设计原则】：
   - 不能有一个选项明显更好
   - 代价类型应该不同（钱 vs 人情，短期 vs 长期，这个人 vs 那个人）
   - 两个选项都应该解决一部分问题但制造新问题
   - 可以有隐藏的第三选项，但需要玩家拥有特定资源或关系才会出现

3. 如果玩家忽略此事件（选择不介入），NPC自己会怎么做，后果是什么

4. 此节拍的情绪基调（用于生成配图）

请以JSON格式输出：
{{
    "title": "事件标题（简洁有力）",
    "description": "事件描述（2-3句话）",
    "choices": [
        {{
            "text": "选项A描述",
            "cost": "代价说明（消耗什么/得罪谁/花多少时间）",
            "consequence": "可能后果",
            "effect": "程序效果字符串"
        }},
        {{
            "text": "选项B描述",
            "cost": "代价说明",
            "consequence": "可能后果",
            "effect": "程序效果字符串"
        }}
    ],
    "hidden_choice": {{
        "text": "隐藏选项（如果有）",
        "unlock_condition": "解锁条件",
        "cost": "代价",
        "consequence": "后果",
        "effect": "效果"
    }},
    "ignore_consequence": "如果玩家忽略，NPC自己会怎么做",
    "emotion_tone": "情绪基调（如：压抑、紧张、温情、绝望等）"
}}

注意：
- 选项必须是合理的，基于情境的
- 不可以设计明显更好的选项但是不提供
- 代价必须是真实的，玩家能感受到的
"""
        
        try:
            response = await self.llm.generate(prompt)
            return self._parse_event_card(response, npc.npc_id, seed.phase)
        except Exception as e:
            print(f"[RollingStoryGenerator] 生成失败: {e}")
            return self._create_fallback_card(npc, seed)
    
    def _get_phase_instruction(self, phase: DilemmaPhase) -> str:
        """根据困境阶段给LLM不同的编剧指导"""
        instructions = {
            DilemmaPhase.LATENT: """这是困境第一次浮现。
要求：事件不要太激烈，像是日常中的一个不对劲的细节。
让玩家嗅到"这个人有故事"，而不是直接给大冲突。
类比：真人秀第一集，介绍人物时的"伏笔片段"。""",
            
            DilemmaPhase.SURFACED: """困境已经浮出水面，但还没到危急时刻。
要求：矛盾开始加剧，NPC需要面对他一直逃避的问题。
玩家的选择会影响事态走向，但不是最终决定。
类比：真人秀中段，矛盾积累，小爆发。""",
            
            DilemmaPhase.ESCALATED: """事态已经升级，不可能再假装没事了。
要求：逼迫NPC（和玩家）做出更大的决定。
之前的选择造成的后果开始显现。
出现新的利益相关方，让局面更复杂。
类比：真人秀高潮前的"逼宫"。""",
            
            DilemmaPhase.CRISIS: """这是决定性时刻。
要求：NPC面临人生的岔路口，玩家的选择将真正决定此人的命运。
所有之前积累的矛盾在此刻汇聚爆发。
选项应该格外痛苦——两边都是要放弃重要的东西。
类比：真人秀的决赛/最终对决。""",
            
            DilemmaPhase.AFTERMATH: """尘埃落定。
要求：展示选择的长期后果。NPC的人生真的改变了。
如果玩家一路帮助了此人，这里应该有情感回报（NPC申请加入/深度感谢）。
如果玩家一路忽略或做了伤害此人的选择，这里展示遗憾。
类比：真人秀的"X年后回访"。"""
        }
        return instructions.get(phase, "")
    
    def _summarize_story_beats(self, beats: List[StoryBeat]) -> str:
        """总结已发生的故事节拍"""
        if not beats:
            return ""
        
        summaries = []
        for beat in beats[-3:]:  # 只显示最近3个节拍
            summary = f"- 第{beat.beat_number}幕: {beat.event_summary}"
            if beat.player_choice:
                summary += f"（玩家选择：{beat.player_choice}）"
            if beat.consequence_summary:
                summary += f"→ 后果：{beat.consequence_summary}"
            summaries.append(summary)
        
        return "\n".join(summaries)
    
    def _format_tensions(self, seed: NPCDilemmaSeed) -> str:
        """格式化张力信息"""
        if not seed.tensions:
            return "暂无"
        
        lines = []
        for i, t in enumerate(seed.tensions, 1):
            lines.append(f"{i}. [{t.type.value}] {t.force_a} vs {t.force_b} (强度:{t.intensity})")
        return "\n".join(lines)
    
    def _format_relevant_world_events(self, npc: NPCData, world_state: WorldSnapshot) -> str:
        """格式化相关的世界事件"""
        # 简化版本，可以扩展
        return "（世界运转中...）"
    
    def _get_personality_narrative_guidance(self, npc: NPCData) -> str:
        """
        根据NPC性格生成叙事指导
        
        这告诉LLM如何根据性格特点来设计事件和选项
        """
        guidance_lines = []
        behavior = npc.get_behavior_tendency()
        
        # 基于性格维度的叙事指导
        if behavior.get('impulsive'):
            guidance_lines.append("- 此人行事冲动，事件中可能做出仓促决定，导致事态恶化")
        else:
            guidance_lines.append("- 此人行事谨慎，会深思熟虑后再行动")
        
        if behavior.get('risk_taking'):
            guidance_lines.append("- 敢于冒险，选项中可以包含高风险高回报的选择")
        else:
            guidance_lines.append("- 厌恶风险，更倾向于稳妥的解决方案")
        
        if behavior.get('pragmatic'):
            guidance_lines.append("- 现实主义者，会优先考虑实际利益而非道德原则")
        else:
            guidance_lines.append("- 理想主义者，可能为了原则放弃实际利益")
        
        if behavior.get('loyal'):
            guidance_lines.append("- 重视情义，在涉及朋友/家人的抉择时会特别纠结")
        else:
            guidance_lines.append("- 轻视情义，可能为了利益牺牲人际关系")
        
        if behavior.get('ambitious'):
            guidance_lines.append("- 野心勃勃，渴望出人头地，可能为此不择手段")
        else:
            guidance_lines.append("- 安于现状，更重视当下的平静生活")
        
        # 根据欲望类型添加特定指导
        desire_guidance = {
            "金钱": "对财富有强烈渴望，涉及金钱的诱惑会特别有效",
            "名声": "渴望被认可，名誉受损是致命的打击",
            "权力": "追求掌控感，失去自主权是最大恐惧",
            "知识": "求知欲强，可能为了求知忽视其他",
            "爱情": "情感丰富，感情问题是核心矛盾",
            "安全": "极度需要安全感，威胁安全的事会引发强烈反应"
        }
        if npc.desire_type in desire_guidance:
            guidance_lines.append(f"- {desire_guidance[npc.desire_type]}")
        
        # 人情值影响
        if npc.social_credit > 0:
            guidance_lines.append(f"- 欠玩家人情({npc.social_credit}点)，可能因此感到有义务回报")
        elif npc.social_credit < 0:
            guidance_lines.append(f"- 玩家欠其人情({-npc.social_credit}点)，可能借此机会要求回报")
        
        return "\n".join(guidance_lines) if guidance_lines else "（暂无特殊性格影响）"
    
    def _parse_event_card(self, response: str, npc_id: str, phase: DilemmaPhase) -> EventCard:
        """解析LLM返回的事件卡JSON"""
        
        try:
            # 提取JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)
            
            card = EventCard(
                id=f"beat_{npc_id}_{phase.value}_{hash(response) % 10000}",
                title=data.get('title', '未命名事件'),
                description=data.get('description', ''),
                npc_id=npc_id,
                ignore_consequence=data.get('ignore_consequence', ''),
                emotion_tone=data.get('emotion_tone', '中性'),
                phase=phase
            )
            
            # 解析选项
            for choice_data in data.get('choices', []):
                choice = EventChoice(
                    text=choice_data.get('text', ''),
                    cost=choice_data.get('cost', ''),
                    consequence=choice_data.get('consequence', ''),
                    effect=choice_data.get('effect', ''),
                    hidden=False
                )
                card.choices.append(choice)
            
            # 解析隐藏选项
            hidden_data = data.get('hidden_choice')
            if hidden_data:
                hidden = EventChoice(
                    text=hidden_data.get('text', ''),
                    cost=hidden_data.get('cost', ''),
                    consequence=hidden_data.get('consequence', ''),
                    effect=hidden_data.get('effect', ''),
                    hidden=True,
                    unlock_condition=hidden_data.get('unlock_condition', '')
                )
                card.choices.append(hidden)
            
            return card
            
        except Exception as e:
            print(f"[RollingStoryGenerator] 解析事件卡失败: {e}")
            return self._create_fallback_card_from_data(npc_id, phase)
    
    def _create_fallback_card(self, npc: NPCData, seed: NPCDilemmaSeed) -> EventCard:
        """创建备用事件卡（当LLM失败时）"""
        return EventCard(
            id=f"fallback_{npc.npc_id}",
            title=f"{npc.name}的困境",
            description=f"{npc.name}似乎遇到了一些麻烦，需要有人帮助...",
            npc_id=npc.npc_id,
            choices=[
                EventChoice(
                    text="伸出援手",
                    cost="消耗时间和金钱",
                    consequence="可能改善此人的处境",
                    effect="affinity:+20"
                ),
                EventChoice(
                    text="袖手旁观",
                    cost="无",
                    consequence="此人可能陷入更深的困境",
                    effect=""
                )
            ],
            ignore_consequence=f"{npc.name}只能独自面对困境",
            emotion_tone="沉重",
            phase=seed.phase
        )
    
    def _create_fallback_card_from_data(self, npc_id: str, phase: DilemmaPhase) -> EventCard:
        """从最少数据创建备用事件卡"""
        return EventCard(
            id=f"fallback_{npc_id}",
            title="突发事件",
            description="一件意外的事情发生了...",
            npc_id=npc_id,
            choices=[
                EventChoice(text="介入处理", cost="消耗时间", consequence="事态可能好转", effect=""),
                EventChoice(text="静观其变", cost="无", consequence="事态自行发展", effect="")
            ],
            ignore_consequence="事情按照它自己的轨迹发展",
            emotion_tone="紧张",
            phase=phase
        )