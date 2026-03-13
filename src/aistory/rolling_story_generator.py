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
# NPCData 类型别名 - 直接使用NPC对象
from typing import Any
NPCData = Any
from .shared_types import WorldSnapshot

# 导入日志函数
try:
    from src.utils import log_game_event
except ImportError:
    def log_game_event(text, tag="INFO"):
        print(f"[{tag}] {text}")


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
            "id": self.id,
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
                                  player: NPCData) -> EventCard:
        """
        生成下一个故事节拍
        
        基于：
        - NPC当前状态
        - 已发生的故事
        - 当前困境阶段
        - 玩家资源状况（玩家对象，继承自NPC）
        """
        log_game_event(f"[RollingStoryGenerator] 开始为 {npc.name} 生成故事节拍", tag="DILEMMA")
        log_game_event(f"[RollingStoryGenerator] 困境阶段: {seed.phase.value}, 张力数: {len(seed.tensions)}", tag="DILEMMA")
        log_game_event(f"[RollingStoryGenerator] 核心矛盾: {seed.desire[:30]}... vs {seed.reality_block[:30]}...", tag="DILEMMA")
        
        # 构建已有故事的摘要
        story_so_far = self._summarize_story_beats(seed.story_beats)
        
        # 获取阶段指导
        phase_instruction = self._get_phase_instruction(seed.phase)
        
        # 构建玩家信息字符串
        player_info = self._format_player_info(player)
        
        # 获取NPC属性（处理可能不存在的属性）
        name = getattr(npc, 'name', '未知')
        gender = getattr(npc, 'gender', '未知')
        age = getattr(npc, 'age', 30)
        job = getattr(npc, 'job', '平民')
        org_id = getattr(npc, 'org_id', '')
        money = getattr(npc, 'money', 0)
        emotion = getattr(npc, 'emotion', 50)
        health = getattr(npc, 'hp', getattr(npc, 'health', 100))
        backstory = getattr(npc, 'backstory', '')
        
        prompt = f"""你是宋代市井剧的编剧。现在需要为一个人物生成【下一个故事节拍】。\n
===== 人物档案 =====
姓名：{name}
性别：{gender}  年龄：{age}
职业：{job}
所属组织：{org_id}
{npc.get_personality_profile()}
背景故事：{backstory if backstory else '暂无'}
当前经济状况：{money} 文
当前情绪：{emotion}/100
当前健康：{health}/100

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
{player_info}

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
            # LLMService的chat方法不是异步的，不需要await
            response = self.llm.chat(
                system_prompt="你是一个宋代市井剧的编剧专家。",
                user_message=prompt,
                max_tokens=2500
            )
            # 如果response是对象，获取content属性；如果是字符串，直接使用
            response_text = response.content if hasattr(response, 'content') else str(response)
            return self._parse_event_card(response_text, npc.id, seed.phase)
        except Exception as e:
            log_game_event(f"[RollingStoryGenerator] 生成失败: {e}", tag="ERROR")
            # 异常时中止，不使用兜底方案
            raise
    
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
    
    def _format_player_info(self, player: NPCData) -> str:
        """
        格式化玩家信息
        
        玩家对象继承自NPC，使用NPC的属性加上玩家特有属性
        """
        if player is None:
            return "玩家信息不可用"
        
        # 基础信息（从NPC继承）
        money = getattr(player, 'money', 0)
        health = getattr(player, 'health', 100)
        emotion = getattr(player, 'emotion', 50)
        
        # 玩家特有属性
        fame = getattr(player, 'fame', 0)  # 江湖善名
        followers = getattr(player, 'followers_count', 0)
        
        # 背包信息
        inventory = getattr(player, 'inventory', {})
        if inventory:
            items = [f"{k}:{v}" for k, v in list(inventory.items())[:5]]
            inventory_str = ", ".join(items)
            if len(inventory) > 5:
                inventory_str += f" 等共{len(inventory)}种"
        else:
            inventory_str = "无"
        
        # 势力声望
        org_rep = getattr(player, 'org_reputation', {})
        if org_rep:
            rep_items = [f"{org}:{val}" for org, val in list(org_rep.items())[:3]]
            rep_str = ", ".join(rep_items)
        else:
            rep_str = "暂无"
        
        return f"""玩家当前状况：
- 银钱：{money} 文
- 健康：{health}/100
- 情绪：{emotion}/100
- 江湖善名：{fame}（-100 ~ +100）
- 追随者：{followers} 人
- 势力声望：{rep_str}
- 拥有的资源：{inventory_str}"""
    
    def _get_personality_narrative_guidance(self, npc: NPCData) -> str:
        """
        根据NPC性格生成叙事指导
        
        从personality对象获取性格数值（0-100），提供更精细的叙事指导
        """
        guidance_lines = []
        
        # 从personality对象获取性格属性
        personality = getattr(npc, 'personality', None)
        if personality:
            temper = getattr(personality, 'temper', 50)
            spirit = getattr(personality, 'spirit', 50)
            ism = getattr(personality, 'ism', 50)
            act_style = getattr(personality, 'act_style', 50)
            friendship = getattr(personality, 'friendship', 50)
            ambition = getattr(personality, 'ambition', 50)
            desire_type = getattr(personality, 'desire_type', None)
        else:
            temper = spirit = ism = act_style = friendship = ambition = 50
            desire_type = None
        
        # 获取人情值（直接从npc获取）
        social_credit = getattr(npc, 'social_credit', 0)
        
        # ═══════════════════════════════════════════════════════════════
        # 1. 脾气 (temper: 0温和 ←→ 100暴躁)
        # ═══════════════════════════════════════════════════════════════
        if temper >= 80:
            guidance_lines.append("- 【极度暴躁】此人脾气极其火爆，极易被激怒，常因冲动酿成大祸")
        elif temper >= 60:
            guidance_lines.append("- 【脾气暴躁】此人易怒冲动，事件中可能因一时气愤做出鲁莽决定")
        elif temper <= 20:
            guidance_lines.append("- 【极度温和】此人脾性极好，极少动怒，即使受辱也能保持冷静")
        elif temper <= 40:
            guidance_lines.append("- 【脾气温和】此人性格平和，不易被激怒，会理性思考后再行动")
        else:
            guidance_lines.append("- 【脾气一般】此人情绪稳定，既不易暴怒也不过分隐忍")
        
        # ═══════════════════════════════════════════════════════════════
        # 2. 胆量 (spirit: 0胆小 ←→ 100勇敢)
        # ═══════════════════════════════════════════════════════════════
        if spirit >= 80:
            guidance_lines.append("- 【极度勇敢】此人胆大包天，面对强敌也毫不退缩，甚至敢于挑战权威")
        elif spirit >= 60:
            guidance_lines.append("- 【胆识过人】此人勇敢无畏，敢于冒险，选项可包含高风险高回报的选择")
        elif spirit <= 20:
            guidance_lines.append("- 【极度胆小】此人胆小如鼠，稍有危险就退缩，需要被保护或推动")
        elif spirit <= 40:
            guidance_lines.append("- 【较为胆小】此人谨慎保守，厌恶风险，更倾向于稳妥的解决方案")
        else:
            guidance_lines.append("- 【胆识一般】此人既不过于鲁莽也不过分怯懦，会权衡利弊后行动")
        
        # ═══════════════════════════════════════════════════════════════
        # 3. 主义 (ism: 0理想 ←→ 100现实)
        # ═══════════════════════════════════════════════════════════════
        if ism <= 20:
            guidance_lines.append("- 【极度理想】此人是坚定的理想主义者，愿为信念牺牲一切，包括生命")
        elif ism <= 40:
            guidance_lines.append("- 【偏向理想】此人重视原则与正义，可能为了道德底线放弃实际利益")
        elif ism >= 80:
            guidance_lines.append("- 【极度现实】此人是彻底的现实主义者，只认利益不认情义，为达目的不择手段")
        elif ism >= 60:
            guidance_lines.append("- 【偏向现实】此人务实理性，会优先考虑实际利益而非道德原则")
        else:
            guidance_lines.append("- 【理想现实平衡】此人能在原则与利益之间找到平衡点")
        
        # ═══════════════════════════════════════════════════════════════
        # 4. 风格 (act_style: 0缜密 ←→ 100豪放)
        # ═══════════════════════════════════════════════════════════════
        if act_style >= 80:
            guidance_lines.append("- 【极度豪放】此人行事大开大合，不拘小节，说话做事直来直去")
        elif act_style >= 60:
            guidance_lines.append("- 【风格豪放】此人爽朗直率，不喜欢拐弯抹角，可能因口无遮拦得罪人")
        elif act_style <= 20:
            guidance_lines.append("- 【极度缜密】此人思虑极深，每一步都精心计算，从不做无把握之事")
        elif act_style <= 40:
            guidance_lines.append("- 【风格缜密】此人谨慎细致，谋定而后动，但可能因过于谨慎错失良机")
        else:
            guidance_lines.append("- 【张弛有度】此人该谨慎时谨慎，该果断时果断")
        
        # ═══════════════════════════════════════════════════════════════
        # 5. 情义 (friendship: 0重情义 ←→ 100不重情义)
        # ═══════════════════════════════════════════════════════════════
        if friendship <= 20:
            guidance_lines.append("- 【极度重情义】此人把兄弟情义看得比命还重，为朋友两肋插刀，背叛朋友比死还难受")
        elif friendship <= 40:
            guidance_lines.append("- 【重视情义】此人讲义气重感情，在涉及朋友/家人的抉择时会特别纠结")
        elif friendship >= 80:
            guidance_lines.append("- 【极度薄情】此人冷酷无情，视感情为累赘，可以毫不犹豫出卖任何人")
        elif friendship >= 60:
            guidance_lines.append("- 【不重情义】此人利益至上，可能为了利益牺牲人际关系")
        else:
            guidance_lines.append("- 【情义无特别倾向】此人对待感情比较理性，不会过分执着")
        
        # ═══════════════════════════════════════════════════════════════
        # 6. 野心 (ambition: 0-100)
        # ═══════════════════════════════════════════════════════════════
        if ambition >= 80:
            guidance_lines.append("- 【野心极大】此人志向远大，渴望功成名就，为此可以忍受常人不能忍之事")
        elif ambition >= 60:
            guidance_lines.append("- 【野心勃勃】此人渴望出人头地，有强烈的进取心，可能为此不择手段")
        elif ambition <= 20:
            guidance_lines.append("- 【毫无野心】此人淡泊名利，只想安稳度日，对权力地位毫无兴趣")
        elif ambition <= 40:
            guidance_lines.append("- 【较为淡泊】此人安于现状，更重视当下的平静生活")
        else:
            guidance_lines.append("- 【野心适中】此人会争取机会但不会过分强求")
        
        # ═══════════════════════════════════════════════════════════════
        # 7. 欲望类型
        # ═══════════════════════════════════════════════════════════════
        desire_guidance = {
            "金钱": "对财富有强烈渴望，涉及金钱的诱惑会特别有效",
            "名声": "渴望被认可，名誉受损是致命的打击",
            "权力": "追求掌控感，失去自主权是最大恐惧",
            "知识": "求知欲强，可能为了求知忽视其他",
            "爱情": "情感丰富，感情问题是核心矛盾",
            "安全": "极度需要安全感，威胁安全的事会引发强烈反应",
            "正义": "嫉恶如仇，无法容忍不公，会主动挺身而出对抗邪恶"
        }
        if desire_type in desire_guidance:
            guidance_lines.append(f"- 【欲望：{desire_type}】{desire_guidance[desire_type]}")
        
        # ═══════════════════════════════════════════════════════════════
        # 8. 人情值影响
        # ═══════════════════════════════════════════════════════════════
        if social_credit > 0:
            guidance_lines.append(f"- 【人情债】欠玩家人情({social_credit}点)，可能因此感到有义务回报")
        elif social_credit < 0:
            guidance_lines.append(f"- 【人情债】玩家欠其人情({-social_credit}点)，可能借此机会要求回报")
        
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
            id=f"fallback_{npc.id}",
            title=f"{npc.name}的困境",
            description=f"{npc.name}似乎遇到了一些麻烦，需要有人帮助...",
            npc_id=npc.id,
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