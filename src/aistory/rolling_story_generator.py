"""
滚动故事生成器 (RollingStoryGenerator)

不预写多幕，每一步都是基于"当前状态"即时生成下一步。
这是实现"玩家选择不确定，空间不会爆炸"的关键。

起承转合四阶段：
- EMERGE（起）：风声渐起，暗流涌动
- ESCALATE（承）：矛盾公开化，立场分化  
- CLIMAX（转）：不可调和，必须表态
- SETTLE（合）：木已成舟，善后处理
"""

import json
import re
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .dilemma_seed import NPCDilemmaSeed, StoryBeat
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


# ═══════════════════════════════════════════════════════════════
# 起承转合四阶段枚举
# ═══════════════════════════════════════════════════════════════
class StoryPhase(Enum):
    """起承转合四阶段 - 更符合中文叙事传统"""
    EMERGE = "EMERGE"       # 起：风声渐起，暗流涌动
    ESCALATE = "ESCALATE"   # 承：矛盾公开化，立场分化
    CLIMAX = "CLIMAX"       # 转：不可调和，必须表态
    SETTLE = "SETTLE"       # 合：木已成舟，善后处理


# ═══════════════════════════════════════════════════════════════
# 困境类型枚举
# ═══════════════════════════════════════════════════════════════
class DilemmaType(Enum):
    """困境类型 - 必须属于以下七大类之一"""
    SACRIFICE = "SACRIFICE"         # 自我牺牲（帮别人但自己受损）
    BETRAY = "BETRAY"               # 背叛（为了自己收益最大化，让朋友受损）
    COMPROMISE = "COMPROMISE"       # 妥协（自己和敌人都获得了好处，即使不是最优解）
    DESTRUCTION = "DESTRUCTION"     # 玉石俱焚（为了打击敌人宁愿自己也受损失）
    BIAS = "BIAS"                   # 偏心（两个亲近的人对立，帮一个必然损害另一个）
    MORAL_GREY = "MORAL_GREY"       # 道德灰色（两个选择都不完全道德）
    SHORT_VS_LONG = "SHORT_VS_LONG" # 短期vs长期（眼前利益vs长远正义）


# ═══════════════════════════════════════════════════════════════
# 事件主题
# ═══════════════════════════════════════════════════════════════
EVENT_THEMES = {
    "维持生计": ["财富贬值", "职场内卷", "店铺裁员", "老板剥削", "买房借贷", "房价暴涨/下跌", "赌博成瘾"],
    "社会治安": ["当街碰瓷", "造黄谣", "噪音扰民", "地域歧视", "杀猪盘", "假冒官差", "黑社会强收保护费"],
    "家庭情感": ["天价彩礼", "扶弟魔", "赘婿尊严", "千金爱上穷书生", "私奔未遂", "重男轻女", "断袖之癖", "吃绝户"],
    "江湖恩怨": ["恩将仇报", "清理门户", "金盆洗手", "冒名顶替"],
    "奇幻搞笑": ["性别互换", "梦境共享", "我是秦始皇打钱"]
}


@dataclass
class EventChoice:
    """事件选项 - 起承转合规范"""
    text: str = ""                           # 选项描述（15-20字，格式：[手段]具体做法）
    requirement: Optional[str] = None        # 前置条件（actor_name:attribute:compare_symbol:needvalue）
    cost: Optional[str] = None               # 代价（actor_name:attribute:changevalue，负值）
    effect: Optional[str] = None             # 收益（actor_name:attribute:changevalue，正值）
    tension_delta: int = 0                   # 局势压力变化（-10~30）
    consequence_preview: str = ""            # 后果预览（必须包含4句：[即时反应]；[资源波动]；[关系变化]；[埋下隐患]/[最终走向]/[长远影响]）
    hidden: bool = False                     # 是否是隐藏选项
    unlock_condition: Optional[str] = None   # 解锁条件


@dataclass
class AutoDecay:
    """自动恶化机制 - 让玩家感受到'不作为也是一种选择'"""
    next_phase_preview: str = ""             # 如果玩家不介入，下一阶段将如何恶化
    auto_effect: Optional[str] = None        # 自动恶化时的效果
    auto_tension_delta: int = 0              # 自动恶化时的局势压力变化


@dataclass
class DilemmaDesc:
    """困境描述 - 内心两种力量的牵扯"""
    summary: str = ""                        # 困境总体描述
    desire: str = ""                         # 内心渴望（想要）
    misgiving: str = ""                      # 内心顾虑（害怕失去）


@dataclass
class EventCard:
    """事件卡 - 起承转合完整规范"""
    id: str = ""
    chain_phase: StoryPhase = StoryPhase.EMERGE    # 当前阶段
    dilemma_type: DilemmaType = DilemmaType.MORAL_GREY  # 困境类型
    event_theme: str = ""                        # 事件主题
    dilemma_desc: DilemmaDesc = field(default_factory=DilemmaDesc)  # 困境详情
    
    title: str = ""                              # 新闻标题（15字以内，爆款风格）
    description: str = ""                        # 新闻描述（50-120字，报社小编口吻）
    image_prompt: str = ""                       # 配图描述（四层结构）
    tags: List[str] = field(default_factory=list)  # 标签（类似小红书/抖音）
    comments: List[Dict] = field(default_factory=list)  # 网友评论
    
    actors: List[Dict] = field(default_factory=list)    # 演员列表
    choices: List[EventChoice] = field(default_factory=list)  # 选项
    auto_decay: AutoDecay = field(default_factory=AutoDecay)  # 自动恶化
    
    npc_id: str = ""                             # 主要NPC
    emotion_tone: str = ""                       # 情绪基调
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "chain_phase": self.chain_phase.value,
            "dilemma_type": self.dilemma_type.value,
            "event_theme": self.event_theme,
            "dilemma_desc": {
                "summary": self.dilemma_desc.summary,
                "desire": self.dilemma_desc.desire,
                "misgiving": self.dilemma_desc.misgiving
            },
            "title": self.title,
            "description": self.description,
            "image_prompt": self.image_prompt,
            "tags": self.tags,
            "comments": self.comments,
            "actors": self.actors,
            "choices": [
                {
                    "text": c.text,
                    "requirement": c.requirement,
                    "cost": c.cost,
                    "effect": c.effect,
                    "tension_delta": c.tension_delta,
                    "consequence_preview": c.consequence_preview,
                    "hidden": c.hidden,
                    "unlock_condition": c.unlock_condition
                } for c in self.choices
            ],
            "auto_decay": {
                "next_phase_preview": self.auto_decay.next_phase_preview,
                "auto_effect": self.auto_decay.auto_effect,
                "auto_tension_delta": self.auto_decay.auto_tension_delta
            },
            "npc_id": self.npc_id,
            "emotion_tone": self.emotion_tone
        }


class RollingStoryGenerator:
    """
    滚动式故事生成器——每次只生成下一个节拍（起承转合四阶段）
    
    核心原则：
    - 不预写全部四幕，只基于当前状态生成下一步
    - 每个选项必须有真实代价
    - 两难设计：不能有一个选项明显更好
    """
    
    def __init__(self, llm_service=None):
        self.llm = llm_service

    def _get_next_phase(self, current_phase: StoryPhase) -> StoryPhase:
        """获取下一阶段"""
        progression = {
            StoryPhase.EMERGE: StoryPhase.ESCALATE,
            StoryPhase.ESCALATE: StoryPhase.CLIMAX,
            StoryPhase.CLIMAX: StoryPhase.SETTLE,
            StoryPhase.SETTLE: StoryPhase.EMERGE  # 结束后开始新困境
        }
        return progression.get(current_phase, StoryPhase.EMERGE)

    def _build_rolling_story_prompt(self, npc: NPCData, seed: NPCDilemmaSeed, player: NPCData, snapshot: WorldSnapshot) -> Tuple[str, str]:
        """构建滚动prompt - 起承转合规范
        
        Returns:
            Tuple[str, str]: (system_prompt, user_prompt)
        """
        
        # 从seed中推断当前阶段
        current_phase = self._infer_current_phase(seed)
        
        # 计算当前局势压力（基于已发生节拍数）
        tension_level = self._calculate_tension_level(seed.story_beats)
        
        # 构建已有故事的详细记录（起承转合格式）
        story_so_far = self._format_story_beats_detailed(seed.story_beats)
        
        # 获取阶段指导
        phase_instruction = self._get_phase_instruction(current_phase)
        
        # 构建玩家信息字符串
        player_info = self._format_player_info(player)
        
        # 获取主角属性
        name = getattr(npc, 'name', '未知')
        gender = getattr(npc, 'gender', '未知')
        age = getattr(npc, 'age', 30)
        job = getattr(npc, 'job', '平民')
        power_type = getattr(npc, 'power_type', '无')
        org_id = getattr(npc, 'org_id', '')
        money = getattr(npc, 'money', 0)
        emotion = getattr(npc, 'emotion', 50)
        health = int(getattr(npc, 'hp_percent', 1.0) * 100)
        desc = getattr(npc, 'desc', '')

        # 构建世界状态
        world_state = []
        if snapshot.all_available_npcs:
            world_state.append("【可用演员池】（请从这些人物中挑选演员）")
            npcs_by_org = {}
            for npc_data in snapshot.all_available_npcs:
                org = npc_data.get('org_id', '无组织') or '无组织'
                if org not in npcs_by_org:
                    npcs_by_org[org] = []
                npcs_by_org[org].append(npc_data)
            
            for org, npcs in npcs_by_org.items():
                world_state.append(f"\n  [{org}]")
                for npc_data in npcs[:15]:
                    status_tags = []
                    if npc_data.get('hunger', 0) > 60:
                        status_tags.append("饥饿")
                    if npc_data.get('wealth', 100) > 200:
                        status_tags.append("富有")
                    elif npc_data.get('wealth', 100) < 30:
                        status_tags.append("贫穷")
                    if npc_data.get('status') == '重伤':
                        status_tags.append("重伤")
                    
                    npc_tags = npc_data.get('tags', [])
                    if npc_tags:
                        status_tags.extend(npc_tags[:3])
                    
                    status_str = f" [{','.join(status_tags)}]" if status_tags else ""
                    npc_line = f"    ID={npc_data['id']} {npc_data['name']}({npc_data.get('power_type','民')}/{npc_data.get('job','')}){status_str}"
                    world_state.append(npc_line)
                    
                    desc_short = npc_data.get('desc', '')
                    if desc_short:
                        desc_short = desc_short[:35] + '...' if len(desc_short) > 35 else desc_short
                        world_state.append(f"        人设: {desc_short}")
                    
                    relations = npc_data.get('relations', [])
                    if relations:
                        # 处理不同格式的relations
                        if isinstance(relations, dict):
                            # 字典格式，取前3个键
                            rel_items = list(relations.items())[:3]
                            rel_strs = []
                            for rel_name, rel_val in rel_items:
                                if isinstance(rel_val, (int, float)):
                                    rel_strs.append(f"{rel_name}({int(rel_val)})")
                                elif isinstance(rel_val, dict):
                                    rel_strs.append(f"{rel_name}")
                                else:
                                    rel_strs.append(f"{rel_name}")
                            rel_str = ", ".join(rel_strs)
                        elif isinstance(relations, list):
                            # 列表格式
                            rel_str = ", ".join(str(r) for r in relations[:3])
                        else:
                            rel_str = str(relations)
                        world_state.append(f"        关系: {rel_str}")
                    
                    memories = npc_data.get('recent_memories', [])
                    if memories:
                        world_state.append(f"        近期: {memories[0]}")
            
            world_state.append(f"\n  （共{len(snapshot.all_available_npcs)}名可用演员）")
        
        world_state_text = "\n".join(world_state)

        # 构建已有困境记录
        dilemma_history = self._build_dilemma_history(seed.story_beats)
        
        # 构建相关NPC信息
        related_npcs = self._build_related_npcs(npc, snapshot)

        # System Prompt
        system_prompt = """你是一个资深的游戏叙事总监，担任宋代武侠/市井世界的「事件导演」，负责为NPC生成充满戏剧张力的人生困境事件。

## 你的核心职责
基于NPC的人设、性格、当前状态和周围人际关系，生成一个有血有肉的困境事件，并将其包装成游戏世界内的「报纸新闻」供玩家发现和参与。

## 当前阶段：{phase}{phase_name}
{phase_instruction}

## 困境类型-填入Json中的dilemma_type
困境必须源于NPC的性格缺陷或内心矛盾，不能是无端飞来横祸
困境必须涉及至少2个NPC，形成人际张力
没有明确的"正确答案"——每个选择都有代价
困境的来源是矛盾冲突，必须属于以下大类之一：
- SACRIFICE:    自我牺牲（帮别人但自己受损）
- BETRAY:       背叛（为了自己收益最大化，让朋友受损）
- COMPROMISE:   妥协（自己和敌人都获得了好处，即使不是最优解）
- DESTRUCTION:  玉石俱焚（为了打击敌人宁愿自己也受损失）
- BIAS:         偏心（两个亲近的人对立，帮一个必然损害另一个）
- MORAL_GREY:   道德灰色（两个选择都不完全道德）
- SHORT_VS_LONG:短期vs长期（眼前利益vs长远正义）

## 困境详情
需要按照环境和性格驱动命运的思路，结合挑选的困境类型，来设计独属于这个事件主角的人生困境。需要包含内心两种力量的牵扯，这种牵扯可以是经济、伦理、道德、责任等各个层面：
- 内心渴望desire字段：使用事件主角NPC的第一人称口吻（"我..."），基于NPC的现状以及性格特质推导，描述角色在这个困境中"想要"的东西
- 内心顾虑misgiving字段：使用事件主角NPC的第一人称口吻（"我..."），基于NPC的现状以及性格特质推导，描述角色在这个困境中"害怕"或者"担心失去"的东西
- 示例：desire="我想帮弟弟还清赌债，让他重新做人"，misgiving="我怕拿出全部积蓄后，自己连房租都付不起"
将desire和misgiving填入Json中的dilemma_desc

## 事件主题说明-填入Json中的event_theme
每个阶段的困境，都需要表现为具体的市井/江湖事件，可以围绕以下的主题编排事件：
维持生计：财富贬值、职场内卷、店铺裁员、老板剥削、买房借贷、房价暴涨/下跌、赌博成瘾
社会治安：当街碰瓷、造黄谣、噪音扰民、地域歧视、杀猪盘、假冒官差、黑社会强收保护费
家庭情感：天价彩礼、扶弟魔、赘婿尊严、千金爱上穷书生、私奔未遂、重男轻女、断袖之癖、吃绝户
江湖恩怨：恩将仇报、清理门户、金盆洗手、冒名顶替
奇幻搞笑：性别互换、梦境共享、我是秦始皇打钱

## 困境和主题的软映射（可参考不强制）
SACRIFICE / MORAL_GREY → 优先：家庭情感、江湖恩怨
BETRAY / DESTRUCTION → 优先：社会治安、江湖恩怨
COMPROMISE / SHORT_VS_LONG → 优先：维持生计、社会治安
BIAS → 优先：家庭情感

## 配图描述四层结构（用于image_prompt字段）
必须严格按照以下四层结构编写配图描述，总长度300-500字：
【第一层·风格锁定】参考《雾山五行》风格，手绘2D国漫，硬朗线条，平涂阴影，高对比度色彩，宋代市井/江湖场景，手绘笔触，电影级构图。
【第二层·背景与氛围】交代具体地点（如：悦来客栈后院/汴河码头/甜水巷），描写光线天气（如：黄昏斜阳/阴雨绵绵/月色如水），路人反应（围观/窃窃私语/指指点点）。用光影暗示情绪：冲突用侧逆光强阴影，温情用暖色散射光。
【第三层·角色交互】100-200字，详细描写画面中每个角色的位置、姿态、表情、动作、服装细节。角色之间的空间关系要体现冲突或情感张力。不要写对话，只写可视化的身体语言和表情。
【第四层·镜头语言】指定构图方式（对角线构图/三角构图/框架构图/黄金分割等），指定景别（远景/中景/近景/特写），指定视角（仰拍/俯拍/平视/偷窥视角）。

## actors角色定位说明
actors数组中的role字段可选值：
- "困境主角"：事件的核心NPC
- "压力来源"：给主角制造困境的NPC
- "求助对象"：主角可能寻求帮助的对象
- "潜在受害者"：可能被主角行为伤害的NPC
- "信任方"：信任主角的NPC
- "对立方"：与主角对立的NPC
- "旁观者"：围观或评论的NPC
""".format(
            phase=current_phase.value,
            phase_name=self._get_phase_chinese_name(current_phase),
            phase_instruction=phase_instruction
        )

        # User Prompt
        user_prompt = f"""## 任务
请为以下NPC生成{current_phase.value}阶段的困境事件。{self._get_task_description(current_phase)}

## 事件主角NPC信息
- 姓名: {name}
- id = {getattr(npc, 'id', '未知')}
- 人设: {age}岁，{gender}，{job}。{desc}
- 性格特质: {self._get_personality_profile(npc)}
- 当前状态: {{"money": {money}, "emotion": {emotion}, "health": {health}%}}
- 职业: {job}
- 所属组织: {org_id}

## 已有困境记录
{dilemma_history}

## 当前困境压力：
{tension_level}


## 当前世界状态
{world_state_text}

## 当前势力格局
{self._get_faction_status(snapshot)}

## 玩家状态
- 银钱: {getattr(player, 'money', 0)} 文
- 能力属性: strength:{getattr(player, 'strength', 0)}, agility:{getattr(player, 'agility', 0)}, wit:{getattr(player, 'wit', 0)}, charm:{getattr(player, 'charm', 0)}

## 字段格式详细说明

### 内容要求
1. 标题要有爆点，像小红书热门标题
2. 评论要模拟真实网友风格（支持、反对、调侃都要有），网友不能是虚构，必须来自于完整演员池（所有可用NPC，但是剔除当事人）
3. effect格式：角色:属性:增减值，多个用分号隔开
4. 角色可以是 A/B/C（对应actors顺序）或 PLAYER5、
5. tags数组中的标签只写纯文字，如 ["职场霸凌", "废柴集合"]等吸引人注目的标签

### requirement字段格式
格式: `actor_name:attribute:compare_symbol:needvalue`
- actor_name: 使用NPC的ID（如npc_001）或PLAYER
- attribute: 属性名（strength/agility/wit/charm/money/emotion/health等）
- compare_symbol: 比较符号（>、<、>=、<=、=）
- needvalue: 需要的数值
- 示例: `PLAYER:charm:>=:50` 或 `npc_001:money:>::100`

### cost/effect/auto_effect字段格式
格式: `actor_name:attribute:changevalue`（多个用分号隔开）
- actor_name: 使用NPC的ID（如npc_001）或PLAYER
- attribute: 属性名
- changevalue: 变化数值（cost必须为负数，effect为正数）
- 示例: `PLAYER:money:-200;npc_001:emotion:15`

### consequence_preview标签要求
必须按顺序包含以下四个标签，用"；"分隔：
- [即时反应]：选择后的立即效果
- [资源波动]：金钱/物品变化
- [关系变化]：与NPC关系变化
- [埋下隐患]/[最终走向]/[长远影响]：根据阶段使用对应标签

## 输出格式
严格输出下方JSON结构，不要输出任何JSON以外的内容。字段不可缺省。
```json
{{
  "chain_phase": "{current_phase.value}",
  "dilemma_type": "困境类型枚举值",
  "event_theme": "事件主题",
   "dilemma_desc":
    {{
        "summary":"事件主角的困境描述，包含渴望与顾虑的拉扯" ,
        "desire":"基于状况和性格推导的内心渴望（第一人称口吻）",
        "misgiving":"基于状况和性格推导的内心顾虑（第一人称口吻）"
    }},
    "actors": [
        {{"role": "角色定位", "npc_name": "NPC名字", "npc_id": "NPC的ID"}}
    ],
     "title": "报纸标题，15字以内，八卦试探语气",
    "description": "报纸正文，80-120字，以传闻/风声形式书写，需要从报社小编的口吻写清楚前因、当前角色的困境和矛盾冲突，需要有很强的可读性和八卦风格，让人一看就觉得吸引眼球",
    "image_prompt": "严格按四层结构编写的文生图描述，总长300-500字",
    "tags": ["标签1", "标签2", "标签3"],
    "comments": [
        {{"user": "围观群众名", "text": "评论内容", "type": "赞/踩/吃瓜"}},
        {{"user": "围观群众名", "text": "评论内容", "type": "赞/踩/吃瓜"}},
        {{"user": "围观群众名", "text": "评论内容", "type": "赞/踩/吃瓜"}}
    ],
   "choices": [
        {{
            "text": "选项文本，15-20字，玩家帮助视角，格式：[手段]具体做法",
            "requirement": "actor_name:attribute:compare_symbol:needvalue 或 null",
            "cost":"actor_name:attribute:changevalue 或 null，多个用分号隔开，changevalue为负数",
            "effect":"actor_name:attribute:changevalue 或 null，多个用分号隔开，changevalue为正数",
            "tension_delta":10,
            "consequence_preview": "[即时反应]...；[资源波动]...；[关系变化]...；[埋下隐患]/[最终走向]/[长远影响]..."
        }}
    ],
  "auto_decay": {{
    "next_phase_preview": "无人介入后的自然发展描述（40-60字）",
    "auto_effect": "actor_name:attribute:changevalue 或 null，多个用分号隔开，严重负面",
    "auto_tension_delta":15
  }}
}}
```
"""
        return system_prompt, user_prompt

    def _infer_current_phase(self, seed: NPCDilemmaSeed) -> StoryPhase:
        """根据已有故事节拍推断当前阶段"""
        beat_count = len(seed.story_beats)
        
        if beat_count == 0:
            return StoryPhase.EMERGE
        elif beat_count == 1:
            return StoryPhase.ESCALATE
        elif beat_count == 2:
            return StoryPhase.CLIMAX
        elif beat_count == 3:
            return StoryPhase.SETTLE
        else:
            # 超过3个节拍，说明已经完成一个困境循环，重新开始
            return StoryPhase.EMERGE

    def _get_phase_chinese_name(self, phase: StoryPhase) -> str:
        """获取阶段中文名"""
        names = {
            StoryPhase.EMERGE: "（起：风声渐起）",
            StoryPhase.ESCALATE: "（承：矛盾升级）",
            StoryPhase.CLIMAX: "（转：高潮爆发）",
            StoryPhase.SETTLE: "（合：尘埃落定）"
        }
        return names.get(phase, "")

    def _get_phase_instruction(self, phase: StoryPhase) -> str:
        """根据困境阶段给LLM不同的编剧指导 - 起承转合规范"""
        
        # 通用的手段标签说明
        means_tags = """
## 选项设计（玩家帮助视角）
选项必须从"玩家作为第三者帮助事件主角"的角度来写，而不是事件主角自己的行动。
- 正确示例："[利诱]出双倍价钱让钱掌柜宽限三日"、"[调解]找郁芊芊预支工钱应急"
- 错误示例："[恳求]向掌柜求情宽限"（这是主角自己的行动，不是玩家帮助）
- 格式要求：[手段]具体做法，15-20字
- 可选手段标签：[威胁]、[贿赂]、[揭露]、[恳求]、[嫁祸]、[卧底]、[硬闯]、[利诱]、[挑拨]、[调解]
"""
        
        instructions = {
            StoryPhase.EMERGE: f"""
这是困境的第一幕。矛盾刚刚出现苗头，大多数人还浑然不觉。
- 叙事节奏：暗流涌动，信息不完整，暗示更大的阴谋或冲突
- 选项特征：成本低但效果不确定，试探性介入
- 新闻语气：八卦试探，街头巷尾的风言风语
- 玩家情绪目标：好奇 + 轻微担忧
- 选项数值变动范围：±5~±20（低成本、低收益）
- ⚠️ EMERGE阶段特殊要求：
  - 允许出现"旁观/打听消息"类选项（玩家可以选择不介入）
  - 但不能只生成旁观选项，必须提供2-3个主动介入的选项
{means_tags}""",
            
            StoryPhase.ESCALATE: f"""
这是困境的第二幕。事情已经藏不住了，周围人开始站队。
- 叙事节奏：矛盾公开化，立场分化，旁观者被迫表态
- 选项特征：开始出现站队压力，选择会明确得罪某一方
- 新闻语气：追踪报道，连续关注
- 玩家情绪目标：愤怒/焦虑 + 站队欲
- 选项数值变动范围：±10~±30（成本上升、收益也更明显）
- ⚠️ ESCALATE阶段特殊要求（重要）：
  - 🚫 严禁出现"旁观/不介入/观望/打听消息"类选项（已经没有骑墙的余地了）
  - 所有选项必须体现"站队压力"——每个选项都会明确得罪至少一方
  - consequence_preview第4句使用[埋下隐患]标签
{means_tags}""",
            
            StoryPhase.CLIMAX: f"""
这是困境的第三幕，也是最关键的一幕。所有退路都被堵死，必须正面抉择。
- 叙事节奏：不可调和，背水一战，所有伏笔在此收束
- 选项特征：选择代价最高，无法骑墙，鱼与熊掌不可兼得
- 新闻语气：头版头条，惊天大事
- 玩家情绪目标：心痛/纠结 + 史诗感
- ⚠️ CLIMAX阶段特殊要求（重要）：
  - 选项数量必须恰好为2（二选一，不留中间地带）
  - 🚫 严禁出现"旁观/不介入/观望/拖延"类选项（必须做出选择）
  - 两个选项必须形成"desire vs misgiving"的直接对立
  - desire必须是"此刻不争取就永远失去的渴望"
  - misgiving必须是"一旦失去就无法挽回的顾虑"
  - 必须包含至少一项绝对值≥30的剧烈变化
  - consequence_preview第4句使用[最终走向]标签，描述结局画面
{means_tags}""",
            
            StoryPhase.SETTLE: f"""
这是困境的最后一幕。大局已定，现在是处理余波的时候。
- 叙事节奏：尘埃落定，余波荡漾，交代各方结局
- 选项特征：不是"如何解决问题"而是"如何面对结果"——修复、巩固、弥补或放下
- 新闻语气：事后复盘，盖棺定论
- 玩家情绪目标：释然/唏嘘 + 成就感
- ⚠️ SETTLE阶段特殊要求（重要）：
  - 🚫 严禁出现"旁观/不介入/观望"类选项（必须参与善后）
  - 🚫 禁止引入任何新的对立方或新威胁
  - 选项围绕"善后"设计：修复关系/巩固收益/弥补损失/放下执念
  - 正面收益可以大于负面代价（允许2:1甚至3:1），作为玩家全程参与的奖励
  - consequence_preview第4句使用[长远影响]标签
  - auto_decay描述的是"半年后的平静生活"，不是"新的恶化"
{means_tags}"""
        }
        return instructions.get(phase, "")

    def _get_personality_profile(self, npc: NPCData) -> str:
        """获取性格档案简述"""
        personality = getattr(npc, 'personality', None)
        if not personality:
            return "性情平和"
        
        temper = getattr(personality, 'temper', 50)
        spirit = getattr(personality, 'spirit', 50)
        ism = getattr(personality, 'ism', 50)
        act_style = getattr(personality, 'act_style', 50)
        friendship = getattr(personality, 'friendship', 50)
        ambition = getattr(personality, 'ambition', 50)
        
        traits = []
        if temper <= 40:
            traits.append("性情温和")
        elif temper >= 60:
            traits.append("脾气暴躁")
        
        if spirit >= 60:
            traits.append("为人勇敢")
        elif spirit <= 40:
            traits.append("较为胆小")
        
        if ism <= 40:
            traits.append("倾向理想")
        elif ism >= 60:
            traits.append("倾向现实")
        
        if act_style <= 40:
            traits.append("行事缜密")
        elif act_style >= 60:
            traits.append("行事豪放")
        
        if friendship <= 40:
            traits.append("重情义")
        elif friendship >= 60:
            traits.append("不重情义")
        
        if ambition >= 60:
            traits.append("追求事业")
        elif ambition <= 40:
            traits.append("淡泊名利")
        
        return "，".join(traits) if traits else "性情平和"

    def _calculate_tension_level(self, beats: List[StoryBeat]) -> str:
        """
        计算当前局势压力（基于各节拍的 tension_delta 累计）
        
        每个 StoryBeat 的 tension_delta 字段记录了该节拍带来的张力变化
        从0开始累计，得到当前总张力值
        """
        total_tension = 0
        for beat in beats:
            # 累加每个节拍的张力变化
            total_tension += getattr(beat, 'tension_delta', 0) or 0
        
        # 根据累计值返回张力等级描述
        if total_tension <= 0:
            return f"{int(total_tension)}(低)"
        elif total_tension <= 30:
            return f"{int(total_tension)}(中)"
        elif total_tension <= 60:
            return f"{int(total_tension)}(高)"
        else:
            return f"{int(total_tension)}(极高)"

    def _get_task_description(self, phase: StoryPhase) -> str:
        """获取任务描述"""
        descriptions = {
            StoryPhase.EMERGE: "这是故事的第一幕，矛盾刚刚露头。",
            StoryPhase.ESCALATE: "这是故事的第二幕，矛盾公开化。",
            StoryPhase.CLIMAX: "这是故事的第三幕，不可调和的高潮。",
            StoryPhase.SETTLE: "这是故事的第四幕，尘埃落定。"
        }
        return descriptions.get(phase, "")

    def _get_faction_status(self, snapshot: WorldSnapshot) -> str:
        """获取势力格局状态"""
        # 简化处理，实际应该从snapshot中获取
        return "没有势力处于纷争中"

    def _build_dilemma_history(self, beats: List[StoryBeat]) -> str:
        """构建已有困境记录（与示例文件格式一致）"""
        if not beats:
            return "无（这是全新困境的起点）"
        
        history_lines = []
        phase_names = {
            StoryPhase.EMERGE: "EMERGE",
            StoryPhase.ESCALATE: "ESCALATE", 
            StoryPhase.CLIMAX: "CLIMAX",
            StoryPhase.SETTLE: "SETTLE"
        }
        
        for i, beat in enumerate(beats[-4:]):
            # 根据节拍数推断阶段
            if i == 0:
                phase = "EMERGE"
            elif i == 1:
                phase = "ESCALATE"
            elif i == 2:
                phase = "CLIMAX"
            else:
                phase = "SETTLE"
            
            history_lines.append(f"### {phase}阶段")
            # 显示困境类型和事件主题（如果有）
            if beat.dilemma_type:
                history_lines.append(f"- 困境类型: {beat.dilemma_type}")
            if beat.event_theme:
                history_lines.append(f"- 事件主题: {beat.event_theme}")
            # 显示desire和misgiving（如果有）
            if beat.desire:
                history_lines.append(f"- 困境desire: {beat.desire}")
            if beat.misgiving:
                history_lines.append(f"- 困境misgiving: {beat.misgiving}")
            # 显示事件描述
            history_lines.append(f"- 事件描述: {beat.event_summary}")
            # 显示玩家选择
            if beat.player_choice:
                history_lines.append(f"- 玩家选择: {beat.player_choice}")
            # 显示选择结果
            if beat.consequence_summary:
                history_lines.append(f"- 选择结果: {beat.consequence_summary}")
            history_lines.append("")
        
        return "\n".join(history_lines)

    def _build_related_npcs(self, npc: NPCData, snapshot: WorldSnapshot) -> str:
        """构建相关NPC信息（与示例文件格式一致）"""
        lines = []
        
        # 从NPC的relations获取相关人物
        relations = getattr(npc, 'relations', [])
        # 确保 relations 是列表
        if relations and isinstance(relations, dict):
            # 如果是字典，转换为列表（处理值可能是int或dict的情况）
            converted_relations = []
            for k, v in relations.items():
                if isinstance(v, dict):
                    # 值是字典格式
                    converted_relations.append({
                        'target_name': k, 
                        'rel_type': v.get('type', '未知'), 
                        'rel_value': v.get('value', 0)
                    })
                elif isinstance(v, (int, float)):
                    # 值是数字格式（直接是好感度）
                    converted_relations.append({
                        'target_name': k, 
                        'rel_type': '关系', 
                        'rel_value': int(v)
                    })
                else:
                    # 其他格式，使用默认值
                    converted_relations.append({
                        'target_name': k, 
                        'rel_type': '未知', 
                        'rel_value': 0
                    })
            relations = converted_relations
        elif not isinstance(relations, list):
            relations = []
        
        if relations:
            lines.append("与事件主角有关系的NPC：")
            for rel in relations[:5]:
                target_name = getattr(rel, 'target_name', '') or rel.get('target_name', '未知')
                rel_type = getattr(rel, 'rel_type', '') or rel.get('rel_type', '未知')
                rel_value = getattr(rel, 'rel_value', 0) or rel.get('rel_value', 0)
                lines.append(f"- {target_name} ({rel_type}, 好感度: {rel_value})")
        
        # 添加可用演员池中的其他NPC
        if snapshot.all_available_npcs:
            lines.append("\n其他可用演员（请从中选择1-2位卷入困境）：")
            # 排除主角自己
            npc_id = str(getattr(npc, 'id', ''))
            other_npcs = [n for n in snapshot.all_available_npcs if str(n.get('id', '')) != npc_id][:10]
            
            for npc_data in other_npcs:
                name = npc_data.get('name', '未知')
                npc_id_short = npc_data.get('id', '未知')
                job = npc_data.get('job', '')
                org = npc_data.get('org_id', '无组织') or '无组织'
                lines.append(f"- {name} (ID={npc_id_short}, {job}, {org})")
        
        return "\n".join(lines) if lines else "（请从世界状态中挑选相关NPC）"

    def _format_story_beats_detailed(self, beats: List[StoryBeat]) -> str:
        """格式化已发生的故事节拍（起承转合详细格式）"""
        if not beats:
            return ""
        
        summaries = []
        phase_names = ["EMERGE", "ESCALATE", "CLIMAX", "SETTLE"]
        
        for i, beat in enumerate(beats[-4:]):  # 只显示最近4个节拍
            phase_name = phase_names[i] if i < len(phase_names) else "EMERGE"
            summary = f"### {phase_name}阶段"
            summary += f"\n- 事件描述：{beat.event_summary}"
            if beat.player_choice:
                summary += f"\n- 玩家选择：{beat.player_choice}"
            if beat.consequence_summary:
                summary += f"\n- 选择结果：{beat.consequence_summary}"
            summaries.append(summary)
        
        return "\n\n".join(summaries)

    def _get_dilemma_desc_requirement(self, phase: StoryPhase) -> str:
        """获取困境描述的特殊要求"""
        if phase == StoryPhase.CLIMAX:
            return """⚠️ CLIMAX阶段特殊要求：
   - desire必须是"此刻不争取就永远失去的渴望"
   - misgiving必须是"一旦失去就无法挽回的顾虑"
   - 两个选项必须分别对应满足desire和保全misgiving，禁止折中"""
        elif phase == StoryPhase.SETTLE:
            return """⚠️ SETTLE阶段特殊要求：
   - desire反映角色现在最想修复/巩固/弥补的东西（基于CLIMAX的选择结果）
   - misgiving反映角色仍然放不下/后悔/担忧的东西（基于CLIMAX中被放弃的那一面）"""
        return ""

    def _get_auto_decay_requirement(self, phase: StoryPhase) -> str:
        """获取自动恶化的特殊要求"""
        if phase == StoryPhase.SETTLE:
            return """⚠️ SETTLE阶段特殊要求：
   - 用auto_epilogue替代auto_decay（字段名仍用auto_decay）
   - auto_tension_delta必须为0
   - next_phase_preview描述的是"半年后的平静生活"，不是新的恶化
   - 语气应是"生活还在继续"而非"新的灾难来了"
"""
        return ""

    def _summarize_story_beats(self, beats: List[StoryBeat]) -> str:
        """总结已发生的故事节拍（简化版）"""
        if not beats:
            return ""
        
        summaries = []
        phase_names = ["EMERGE", "ESCALATE", "CLIMAX", "SETTLE"]
        
        for i, beat in enumerate(beats[-4:]):  # 只显示最近4个节拍
            phase_name = phase_names[i] if i < len(phase_names) else "EMERGE"
            summary = f"- [{phase_name}] 第{beat.beat_number}幕: {beat.event_summary}"
            if beat.player_choice:
                summary += f"（玩家选择：{beat.player_choice}）"
            if beat.consequence_summary:
                summary += f"→ 后果：{beat.consequence_summary}"
            summaries.append(summary)
        
        return "\n".join(summaries)

    def _get_personality_narrative_guidance(self, npc: NPCData) -> str:
        """根据NPC性格生成叙事指导"""
        guidance_lines = []
        
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
        
        social_credit = getattr(npc, 'social_credit', 0)
        
        # 脾气
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
        
        # 胆量
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
        
        # 主义
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
        
        # 风格
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
        
        # 情义
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
        
        # 野心
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
        
        # 欲望类型
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
        
        # 人情值
        if social_credit > 0:
            guidance_lines.append(f"- 【人情债】欠玩家人情({social_credit}点)，可能因此感到有义务回报")
        elif social_credit < 0:
            guidance_lines.append(f"- 【人情债】玩家欠其人情({-social_credit}点)，可能借此机会要求回报")
        
        return "\n".join(guidance_lines) if guidance_lines else "（暂无特殊性格影响）"

    def _format_player_info(self, player: NPCData) -> str:
        """格式化玩家信息"""
        if player is None:
            return "玩家信息不可用"
        
        money = getattr(player, 'money', 0)
        health = int(getattr(player, 'hp_percent', 1.0) * 100)
        fame = getattr(player, 'fame', 0)
        followers = getattr(player, 'followers_count', 0)
        
        inventory = getattr(player, 'inventory', {})
        if inventory:
            items = [f"{k}:{v}" for k, v in list(inventory.items())[:5]]
            inventory_str = ", ".join(items)
            if len(inventory) > 5:
                inventory_str += f" 等共{len(inventory)}种"
        else:
            inventory_str = "无"
        
        org_rep = getattr(player, 'org_reputation', {})
        if org_rep:
            rep_items = [f"{org}:{val}" for org, val in list(org_rep.items())[:3]]
            rep_str = ", ".join(rep_items)
        else:
            rep_str = "暂无"
        
        # 玩家属性
        strength = getattr(player, 'strength', 0)
        agility = getattr(player, 'agility', 0)
        wit = getattr(player, 'wit', 0)
        charm = getattr(player, 'charm', 0)
        temper = getattr(player, 'temper', 0)
        spirit = getattr(player, 'spirit', 0)
        ism = getattr(player, 'ism', 0)
        act_style = getattr(player, 'act_style', 0)
        loyalty = getattr(player, 'loyalty', 0)
        
        return f"""玩家当前状况：
- 银钱：{money} 文
- 健康：{health}%
- 江湖善名：{fame}（-100 ~ +100）
- 追随者：{followers} 人
- 势力声望：{rep_str}
- 拥有的资源：{inventory_str}
- 能力属性：strength:{strength}, agility:{agility}, wit:{wit}, charm:{charm}
- 性格属性：temper:{temper}, spirit:{spirit}, ism:{ism}, act_style:{act_style}, loyalty:{loyalty}"""

    async def generate_next_beat(self,
                                  npc: NPCData,
                                  seed: NPCDilemmaSeed,
                                  worldsnapshot: WorldSnapshot,
                                  player: NPCData) -> EventCard:
        """
        生成下一个故事节拍（起承转合四阶段）
        
        基于：
        - NPC当前状态
        - 已发生的故事
        - 当前困境阶段
        - 玩家资源状况
        """
        system_prompt, user_prompt = self._build_rolling_story_prompt(npc, seed, player, worldsnapshot)
        
        try:
            response = self.llm.chat(
                system_prompt=system_prompt,
                user_message=user_prompt,
                max_tokens=3000
            )
            log_game_event(f"[RollingStoryGenerator] LLM响应: {response.raw_response}", tag="LLM_RESPONSE")
            
            # 解析返回的JSON
            event_card = self._parse_event_card(response.raw_response, str(getattr(npc, 'id', 'unknown')))
            return event_card
            
        except Exception as e:
            log_game_event(f"[RollingStoryGenerator] 生成失败: {e}", tag="ERROR")
            raise

    def _parse_event_card(self, response: str, npc_id: str) -> EventCard:
        """解析LLM返回的事件卡JSON - 起承转合规范"""
        
        try:
            # 提取JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)
            
            # 解析困境描述
            dilemma_desc_data = data.get('dilemma_desc', {})
            dilemma_desc = DilemmaDesc(
                summary=dilemma_desc_data.get('summary', ''),
                desire=dilemma_desc_data.get('desire', ''),
                misgiving=dilemma_desc_data.get('misgiving', '')
            )
            
            # 解析自动恶化
            auto_decay_data = data.get('auto_decay', {})
            auto_decay = AutoDecay(
                next_phase_preview=auto_decay_data.get('next_phase_preview', ''),
                auto_effect=auto_decay_data.get('auto_effect'),
                auto_tension_delta=auto_decay_data.get('auto_tension_delta', 0)
            )
            
            # 创建事件卡
            card = EventCard(
                id=f"beat_{npc_id}_{data.get('chain_phase', 'EMERGE')}_{hash(response) % 10000}",
                chain_phase=StoryPhase(data.get('chain_phase', 'EMERGE')),
                dilemma_type=DilemmaType(data.get('dilemma_type', 'MORAL_GREY')),
                event_theme=data.get('event_theme', ''),
                dilemma_desc=dilemma_desc,
                title=data.get('title', '未命名事件'),
                description=data.get('description', ''),
                image_prompt=data.get('image_prompt', ''),
                tags=data.get('tags', []),
                comments=data.get('comments', []),
                actors=data.get('actors', []),
                auto_decay=auto_decay,
                npc_id=npc_id,
                emotion_tone=data.get('emotion_tone', '中性')
            )
            
            # 解析选项
            for choice_data in data.get('choices', []):
                choice = EventChoice(
                    text=choice_data.get('text', ''),
                    requirement=choice_data.get('requirement'),
                    cost=choice_data.get('cost'),
                    effect=choice_data.get('effect'),
                    tension_delta=choice_data.get('tension_delta', 0),
                    consequence_preview=choice_data.get('consequence_preview', ''),
                    hidden=choice_data.get('hidden', False),
                    unlock_condition=choice_data.get('unlock_condition')
                )
                card.choices.append(choice)
            
            return card
            
        except Exception as e:
            log_game_event(f"[RollingStoryGenerator] 解析事件卡失败: {e}", tag="ERROR")
            # 返回一个默认的事件卡
            return EventCard(
                id=f"beat_{npc_id}_ERROR_{hash(response) % 10000}",
                title="事件生成中...",
                description="请稍后再试",
                npc_id=npc_id
            )