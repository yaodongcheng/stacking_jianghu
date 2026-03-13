"""
滚动故事生成器 (RollingStoryGenerator)

不预写多幕，每一步都是基于"当前状态"即时生成下一步。
这是实现"玩家选择不确定，空间不会爆炸"的关键。
"""

import json
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

from matplotlib.pylab import seed

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

    def _build_rolling_story_prompt(self, npc: NPCData, seed: NPCDilemmaSeed, player: NPCData,snapshot: WorldSnapshot) -> str:
        """构建滚动prompt"""
        
        # 构建已有故事的摘要
        story_so_far = self._summarize_story_beats(seed.story_beats)
        
        # 获取阶段指导
        phase_instruction = self._get_phase_instruction(seed.phase)
        
        # 构建玩家信息字符串
        player_info = self._format_player_info(player)
        
        # 获取主角属性（处理可能不存在的属性）
        name = getattr(npc, 'name', '未知')
        gender = getattr(npc, 'gender', '未知')
        age = getattr(npc, 'age', 30)
        job = getattr(npc, 'job', '平民')
        power_type = getattr(npc, 'power_type', '无')
        org_id = getattr(npc, 'org_id', '')
        money = getattr(npc, 'money', 0)
        emotion = getattr(npc, 'emotion', 50)
        health = int(npc.hp_percent * 100) 
        desc = getattr(npc, 'desc', '')

        world_state = []
        # ====== 完整演员池（所有可用NPC） ======
        if snapshot.all_available_npcs:
            world_state.append("【可用演员池】（请从这些人物中挑选演员）")
            # 按组织分组显示
            npcs_by_org = {}
            for npc in snapshot.all_available_npcs:
                org = npc.get('org_id', '无组织') or '无组织'
                if org not in npcs_by_org:
                    npcs_by_org[org] = []
                npcs_by_org[org].append(npc)
            
            for org, npcs in npcs_by_org.items():
                world_state.append(f"\n  [{org}]")
                for npc in npcs[:15]:  # 每个组织最多显示15人
                    # 格式：ID=123 姓名(职业/身份) 状态
                    status_tags = []
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
        
        world_state_text = "\n".join(world_state)




        
        prompt = f"""
        你是《大宋实况》的导演AI，负责编排真人秀风格的社会事件。
你的目标是基于一个人物的人生困境，与目前困境阶段，创造事件。

===== 世界状态 =====
{world_state_text}

===== 事件中心角色档案 =====
姓名：{name}
性别：{gender}  年龄：{age}
职业：[{power_type}]{job}
所属组织：{npc.get_org_name()}
性格特质：{npc.get_personality_profile()}
背景故事：{desc}
当前经济状况：{money} 文
当前情绪：{emotion}
当前健康：{health}%

===== 事件中心角色当前的困境 =====
核心矛盾：{seed.desire} vs {seed.reality_block}
当前张力：
{self._format_tensions(seed)}

===== 性格对叙事的影响 =====
{self._get_personality_narrative_guidance(npc)}

===== 至今为止发生的故事 =====
{story_so_far if story_so_far else "（这是此人的第一个故事节拍）"}

===== 当前困境阶段 =====
困境阶段：{seed.phase.value}
{phase_instruction}


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



请以JSON格式返回决策：
```json
{{
    "event_type": "选择的事件模板ID",
    "actors": [
        {{"role": "角色名", "npc_name": "NPC名字", "npc_id": "NPC的ID"}}
    ],
    "tension_level": "LOW/MEDIUM/HIGH/CRITICAL",
    
    "title": "例：无更市惊现天价救命药！",
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
- 每个选项要有明确的效果和代价（effect 字段）
- 选项要体现不同的处理思路（激进/保守/中立）

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
6. event_type目前可以填EMPTY
7. actors第一个必然是事件中心角色，后续可以有其他相关角色（比如对手、路人等）必须来自于完整演员池（所有可用NPC，但是剔除当事人）

"""
        return prompt
    



    
    
    async def generate_next_beat(self,
                                  npc: NPCData,
                                  seed: NPCDilemmaSeed,
                                  worldsnapshot: WorldSnapshot,
                                  player: NPCData) -> EventCard:
        """
        生成下一个故事节拍
        
        基于：
        - NPC当前状态
        - 已发生的故事
        - 当前困境阶段
        - 玩家资源状况
        """
        prompt = self._build_rolling_story_prompt(npc, seed, player, worldsnapshot)
        
        try:
            # LLMService的chat方法不是异步的，不需要await
            response = self.llm.chat(
                system_prompt="你是一个宋代市井剧的编剧专家。",
                user_message=prompt,
                max_tokens=2500
            )
            log_game_event(f"[RollingStoryGenerator] LLM响应: {response.raw_response}", tag="LLM_RESPONSE")

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
        return "\n".join(lines[1])
    
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
        health = int(player.hp_percent * 100)
        
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
- 健康：{health}%
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
            return None
    
   