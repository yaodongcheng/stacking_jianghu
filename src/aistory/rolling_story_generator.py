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

from src.ui.event_notification import LiveNewsItem, NewsCategory, DilemmaType
from src.utils import log_game_event
from src.definitions import Emotion
EMOTION_OPTIONS = ",".join([f"{e.value[0]}({e.value[1]})" for e in Emotion])



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
    cost: Optional[str] = None               # 代价（actor_name:attribute:changevalue，负值，用于非物质资源）
    effect: Optional[str] = None             # 收益（actor_name:attribute:changevalue，正值，用于能力/关系/情绪）
    transfer: Optional[str] = None           # 转移（from_actor->to_actor:attr:value，用于金钱/物品转移）
    tension_delta: int = 0                   # 局势压力变化（-10~30）
    consequence_preview: str = ""            # 后果预览（必须包含4句：[即时反应]；[资源波动]；[关系变化]；[埋下隐患]/[最终走向]/[长远影响]）
    hidden: bool = False                     # 是否是隐藏选项
    unlock_condition: Optional[str] = None   # 解锁条件


@dataclass
class AutoDecay:
    """自动恶化机制 - 让玩家感受到'不作为也是一种选择'"""
    next_phase_preview: str = ""             # 如果玩家不介入，下一阶段将如何恶化
    auto_effect: Optional[str] = None        # 自动恶化时的效果（非物质资源）
    auto_transfer: Optional[str] = None      # 自动恶化时的资源转移（金钱/物品）
    auto_tension_delta: int = 0              # 自动恶化时的局势压力变化


@dataclass
class DilemmaDesc:
    """困境描述 - 内心两种力量的锁住"""
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
    raw_json: Dict = field(default_factory=dict, repr=False)  # 原始JSON数据（用于对话扩写）
    
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
        protagonist_id = getattr(npc, 'id', '未知')
        protagonist_name = name
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
        # ====== 完整演员池（所有可用NPC） ======
        if snapshot.all_available_npcs:
            world_state.append("【可用演员池】（请从这些人物中挑选演员，主角已固定）")
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
                    npc_id = npc.get('id')
                    npc_name = npc.get('name', '')
                    
                    # 判断是否是主角，添加特殊标记
                    is_protagonist = (str(npc_id) == str(protagonist_id))
                    protagonist_mark = " ⭐【本事件绝对主角】" if is_protagonist else ""
                    
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
                    npc_line = f"    ID={npc_id} {npc_name}({npc.get('power_type','民')}/{npc.get('job','')}){status_str}{protagonist_mark}"
                    world_state.append(npc_line)
                    
                    # 【优化】显示NPC人设描述（desc）
                    desc = npc.get('desc', '')
                    if desc:
                        # 截取前30字，避免过长
                        desc_short = desc[:35] + '...' if len(desc) > 35 else desc
                        world_state.append(f"        人设: {desc_short}")
                        
                        # 如果是主角，额外强调身份
                        if is_protagonist:
                            world_state.append(f"        ⚠️ 注意：以上人设描述属于本事件主角{protagonist_name}，困境必须围绕TA展开！")
                    
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
            world_state.append(f"  ⚠️ 主角锁定：ID={protagonist_id} 的 {protagonist_name} 是本事件唯一主角！")
        
        world_state_text = "\n".join(world_state)

        # 构建已有困境记录
        dilemma_history = self._build_dilemma_history(seed.story_beats)
        
        # 构建相关NPC信息
        related_npcs = self._build_related_npcs(npc, snapshot)

        # System Prompt - 使用f-string而不是.format()避免冲突
        system_prompt = f"""你是一个资深的游戏叙事总监，担任宋代武侠/市井世界的「事件导演」，负责为NPC生成充满戏剧张力的人生困境事件。

## 你的核心职责
基于NPC的人设、性格、当前状态和周围人际关系，生成一个有血有肉的困境事件，并将其包装成游戏世界内的「报纸新闻」供玩家发现和参与。

## 当前阶段：{current_phase.value}{self._get_phase_chinese_name(current_phase)}
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

### 📝 设计前确认（必须完成）
在开始设计困境前，请确认以下三点：
1. 本事件主角是【{{protagonist_name}}(ID={{protagonist_id}})】，不是其他NPC
2. 困境必须是{{protagonist_name}}作为直接受害者（被威胁/被逼迫/被欺负），不能是旁观者
3. desire和misgiving必须是{{protagonist_name}}的第一人称内心独白

### 困境设计规范
需要按照环境和性格驱动命运的思路，结合挑选的困境类型，来设计独属于这个事件主角的人生困境。需要包含内心两种力量的拉扯，这种拉扯可以是经济、伦理、道德、责任等各个层面：
- 内心渴望desire字段：使用事件主角NPC的第一人称口吻（"我，{{protagonist_name}}..."），基于{{protagonist_name}}的现状以及性格特质推导，描述角色在这个困境中"想要"的东西
- 内心顾虑misgiving字段：使用事件主角NPC的第一人称口吻（"我，{{protagonist_name}}..."），基于{{protagonist_name}}的现状以及性格特质推导，描述角色在这个困境中"害怕"或者"担心失去"的东西        
- 示例：desire="我，{{protagonist_name}}，想帮弟弟还清赌债，让他重新做人"，misgiving="我，{{protagonist_name}}，怕拿出全部积蓄后，自己连房租都付不起"
将desire和misgiving填入Json中的dilemma_desc

## 事件主题说明-填入Json中的event_theme
每个阶段的困境，都需要表现为具体的求情/ nhuwi luong. 可以围绕以下的主题编排事件：
维持生计：财富贬值、职场内卷、店铺裁员、老板剥削、买房借贷、房价暴涨/下跌、赌博成瘾
社会治安：当街碰瓷、造黄谣、噪音款待、地域歧视、杀猪盘、假冒官差、黑社会强收保护费
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
"""

        # User Prompt - 增加主角锁定和身份澄清
        user_prompt = f"""## 任务
请为以下NPC生成{current_phase.value}阶段的困境事件。{self._get_task_description(current_phase)}

## 🔒 【主角锁定 - 严格使用以下NPC】🔒
- 姓名: {protagonist_name}
- ID: {protagonist_id}
- 人设: {age}岁，{gender}，{job}。{desc}
- 性格特质: {self._get_personality_profile(npc)}
- 当前状态: {{"money": {money}, "emotion": {emotion}, "health": {health}%}}
- 职业: {job}
- 所属组织: {org_id}

⚠️ 警告：困境主角必须是【{protagonist_name}(ID={protagonist_id})】，禁止更换为其他NPC！
⚠️ 警告：其他所有NPC只能作为配角/对手/旁观者出现！

## 【主角身份澄清 - 必读】
在设计困境前，请仔细分析{protagonist_name}的背景：
- 如果{protagonist_name}有伪装身份/冒名顶替：困境是{protagonist_name}本人的困境（伪装被揭穿的危机，或被迫继续伪装的挣扎）
- 如果{protagonist_name}是某人的亲属/下属：困境是{protagonist_name}的困境（被亲属牵连，或在组织中进退两难）
- 如果{protagonist_name}的背景提到"像XXX""被称为XXX"：那只是比喻/外号，{protagonist_name}仍是独立个体

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
1. 【核心原则】困境主角必须是事件的直接受害者或利益相关方，不能是旁观者！
   - 正确示例：无情被方承意和高衙内用朝堂关系威逼（无情是受害者）
   - 错误示例：无情看着鱼西施被高衙内骚扰（无情是旁观者，鱼西施是受害者）
   - 标题要体现困境主角的两难处境（如"两难！无情遭方承意威逼，神侯府颜面何存？"）
   - 描述要重点描写困境主角作为受害者的内心挣扎（dilemma_desc中的desire与misgiving的拉扯）
2. 标题要有爆点，像小红书热门标题
3. 评论要模拟真实网友风格（支持、反对、调侃都要有），网友不能是虚构，必须来自于完整演员池（所有可用NPC，但是剔除当事人）
4. effect格式：角色:属性:增减值，多个用分号隔开
5. 角色可以是 A/B/C（对应actors顺序）或 PLAYER5、
6. tags数组中的标签只写纯文字，如 ["职场霸凌", "废柴集合"]等吸引人注目的标签
7. 故事中涉及的所有人物，都必须来自于当前的完整演员池，禁止编造不存在的NPC禁止编造不存在的NPC禁止编造不存在的NPC
8. 

 ### requirement字段格式
 格式: `actor_name:attribute:compare_symbol:needvalue`
 - actor_name: 使用NPC的ID（如npc_001）或PLAYER
 - attribute: 属性名（strength/agility/wit/charm/money/emotion/health等）
 - compare_symbol: 比较符号（>、<、>=、<=、=）
 - needvalue: 需要的数值
 - 示例: `PLAYER:charm:>=:50` 或 `1001:money:>::100`
 - ⚠️ 重要规则：requirement中的needvalue必须与cost/transfer中玩家实际消耗的资源数值一致！
   - 如果transfer是`PLAYER->1001:money:30`，则requirement必须是`PLAYER:money:>=:30`
   - 如果cost是`PLAYER:fame:-20`，则requirement必须是`PLAYER:fame:<=:20`（因为fame减少）
   - 禁止出现requirement和实际消耗数值不一致的情况！

 ### cost/effect/auto_effect字段格式
格式: `actor_id:attribute:changevalue`（多个用分号隔开）
 - actor_id: 使用NPC的纯数字ID（如1001、1013）或PLAYER，不要使用npc_前缀
 - attribute: 属性名（支持关系属性如1001:relation表示与该NPC的好感度）
 - changevalue: 变化数值（cost必须为负数，effect为正数）
 - 示例: `PLAYER:money:-200;1001:relation:-10;1013:relation:20`
 - NPC情绪变化格式: `actor_id:emotion:EMOTION值`（如1001:emotion:HAPPY表示NPC 1001变得开心）
 - 情绪枚举候选: {EMOTION_OPTIONS}
 
 ### 物质守恒规则（重要！）
 金钱/物品的转移必须使用 transfer 字段，满足进出平衡：
 - 格式：from_actor->to_actor:attr:value
 - 示例：PLAYER->1001:money:30（玩家给NPC 30金钱）
 - NPC间转移：1003->1001:money:50（NPC之间转移）
 - 多个转移用分号分隔：PLAYER->1001:money:30;1001->1003:item: sword
 
 ### cost字段重要规则（必须遵守！）
 cost只用于表达玩家的"代价"和"损失"：
 - 格式：actor:attr:changevalue
 - 可用类型：
   - PLAYER:fame:N（玩家声望变化，负数表示损失）
   - PLAYER:strength:N、PLAYER:wit:N、PLAYER:charm:N、PLAYER:agility:N（玩家能力属性变化）
   - NPC:affinity_to_player:N（NPC对玩家好感降低，负数）
 - ⚠️ 禁止用于金钱！金钱必须用transfer字段！
 - 示例：cost: "PLAYER:fame:-10"（损失名声）、cost: "1001:affinity_to_player:-5"（与NPC1好感降低）
 
 ### effect字段重要说明
 effect字段只用于正面收益！禁止放入任何会让玩家感觉"亏了"的效果！
 - ✅ 正确：NPC:charm:5（NPC增加魅力）、1001:affinity_to_player:10（NPC更喜欢玩家）
 - ✅ 正确：1001:emotion:HAPPY（NPC变得开心）、PLAYER:wit:3（玩家变聪明）
 - ❌ 错误：1001:affinity_to_player:-10（这是代价，应该放cost！）
 - ❌ 错误：1008:emotion:ANXIOUS（这是代价，应该放cost！）
 - ⚠️ 重要：NPC对玩家的好感度统一用 affinity_to_player！
 - ⚠️ 重要：金钱和物品必须用transfer，不可用effect中的money/item
 
 ### 选项设计核心规则（最重要！）
 1. 【每个选项必须有代价】每个选项的 cost 字段禁止为 null！
    - 如果选项需要玩家付出代价（金钱/名声/能力下降/好感降低），必须标注
    - 如果选项会让某个NPC对玩家好感下降，必须用cost标注
 2. 【正负分开】正面收益放 effect，负面代价放 cost，泾渭分明
 3. 【代价守恒】effect正面收益的绝对值与cost负面代价的绝对值比例不得超过 2:1
    - 例如：cost总绝对值为10，则effect总绝对值不能超过20
 4. 【零成本禁止】EMERGE/ESCALATE/SETTLE阶段禁止"零成本"选项！
    - CLIMAX阶段除外（两难选择可以代价极高）
 5. 【代价逻辑一致性】（重要！）代价必须与选项做法逻辑一致，禁止违背常识！
    - ❌ 错误示例：选项"揭露恶人罪行"，cost却是"PLAYER:fame:-10"（做好事不应该扣声望）
    - ❌ 错误示例：选项"花钱消灾"，cost却是"PLAYER:fame:-10"（花钱已经付出了，不应该再扣名声）
    - ✅ 正确示例：选项"仗势欺人"，cost: "PLAYER:fame:-10"（仗势欺人确实会损伤名声）
    - ✅ 正确示例：选项"揭露恶人罪行"��cost: "1026:affinity_to_player:-20"（会得罪恶人及其同伙）
    - ✅ 正确示例：选项"花钱贿赂"，cost为null（用transfer表达金钱消耗即可）
 6. 【禁止重复属性】（重要！）cost 和 effect 禁止包含相同的属性！
    - ❌ 错误示例：cost: "PLAYER:wit:-1" + effect: "PLAYER:wit:2"（互相抵消，逻辑混乱）
    - ✅ 正确示例：只保留 effect: "PLAYER:wit:2"（没有代价时）
    - ✅ 正确示例：cost: "1008:affinity_to_player:-5" + effect: "PLAYER:wit:2"（不同属性，各有意义）
 7. 【典型代价模式】
    - 花钱类：transfer表达金钱消耗，cost可为null
    - 消耗人情/得罪人：cost: "NPC:affinity_to_player:-N"
    - 仗势欺人类：cost: "PLAYER:fame:-N"（会损伤名声）
    - 损耗能力/精力：cost: "PLAYER:wit:-3"或"PLAYER:charm:-2"
 
 ### consequence_preview标签要求
 必须按顺序包含以下两个标签，用"；"分隔：
 - [即时反应]：选择后的立即效果（短期）
 - [埋下隐患]或[最终走向]或[长远影响]：选择后产生的潜在影响（长期），根据故事阶段选择最合适的标签
 不需要再包含[资源波动]和[关系变化]，这些应该在effect字段中体现。

## 输出格式
严格输出下方JSON结构，不要输出任何JSON以外的内容。字段不可缺省。

### 🔍 输出前强制验证清单
在生成JSON前，请逐项检查：
- [ ] actors[0].npc_id 是否为 "{protagonist_id}"？
- [ ] actors[0].npc_name 是否为 "{protagonist_name}"？
- [ ] dilemma_desc.desire 是否以"我，{protagonist_name}..."开头？
- [ ] 困境是否围绕{protagonist_name}作为受害者展开？
- [ ] 所有引用的NPC是否都来自【可用演员池】？

只有以上检查全部通过，才能输出JSON。

```json
{{
  "chain_phase": "{current_phase.value}",
  "dilemma_type": "困境类型枚举值",
  "event_theme": "事件主题",
  "_protagonist_confirmation": "{protagonist_name}(ID={protagonist_id})",
    "dilemma_desc":
    {{
        "summary":"事件主角【{protagonist_name}】作为直接受害者面临的困境描述，包含渴望与忧虑的拉扯。必须是{protagonist_name}自己被欺负/被威胁/被逼迫，不能是{protagonist_name}看着别人受害" ,
        "desire":"我，{protagonist_name}，想...（基于{protagonist_name}的处境推导）",
        "misgiving":"我，{protagonist_name}，怕...（基于{protagonist_name}的处境推导）"
    }},
    "actors": [
        {{"role": "困境主角（必须是受害者，被欺负/被威胁/被逼迫）", "npc_name": "{protagonist_name}", "npc_id": "{protagonist_id}"}},
        {{"role": "压力来源（欺负/威胁困境主角的人）", "npc_name": "NPC名字", "npc_id": "NPC的ID"}},
        {{"role": "其他相关方", "npc_name": "NPC名字", "npc_id": "NPC的ID"}}
    ],
     "title": "报纸标题，15字以内，八卦试探语气，必须以'{protagonist_name}'为核心视角，标题要体现{protagonist_name}的两难处境",
    "description": "报纸正文，80-120字，以传闻/风声形式书写。必须从'困境主角'的视角出发，重点描写他面临的 dilemma_desc 中的渴望与顾虑的拉扯，而非仅描述表面事件。要有很强的可读性和八卦风格，让人一看就觉得吸引眼球。故事中禁止出现不存在完整演员池的NPC，禁止编造不存在的NPC，禁止编造不存在的NPC！必须使用完整演员池中的NPC来构建故事角色和事件。",
    "image_prompt": "严格按四层结构写入的文生图描述，总长300-500字",
    "tags": ["标签1", "标签2", "标签3"],
    "comments": [
        {{"user": "围观群众名", "text": "评论内容", "type": "赞/踩/吃瓜"}},
        {{"user": "围观群众名", "text": "评论内容", "type": "赞/踩/吃瓜"}},
        {{"user": "围观群众名", "text": "评论内容", "type": "赞/踩/吃瓜"}}
    ],
     "choices": [
        {{
            "text": "选项文本，不超过15字，玩家帮助视角，格式：[手段]具体做法，如：[资助]帮其渡过难关。禁止提到不存在的NPC，必须使用完整演员池中的NPC来设计选项",
            "requirement": "actor_name:attribute:compare_symbol:needvalue 或 null",
            "cost": "玩家必须付出的代价，禁止为null！如 PLAYER:fame:-10 或 1001:affinity_to_player:-5",
            "effect": "玩家的正面收益，禁止放入负面效果！如 1001:affinity_to_player:10 或 PLAYER:wit:3",
            "transfer": "from_actor->to_actor:attr:value 或 null，用于金钱/物品转移，如 PLAYER->1001:money:30",
            "tension_delta":10,
            "consequence_preview": "[即时反应]...；[埋下隐患]/[最终走向]/[长远影响]..."
        }}
    ],
   "auto_decay": {{
    "next_phase_preview": "无人介入后的自然发展描述（40-60字）",
    "auto_effect": "actor:attr:changevalue 或 null，用于非物质资源的单向损失，如 PLAYER:fame:-10",
    "auto_transfer": "from_actor->to_actor:attr:value 或 null，多个用分号隔开，用于自动恶化时金钱/物品的转移（必须守恒）",
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
## 选项设计（围绕困境主角）
选项必须围绕"困境主角的两难抉择"来设计，帮助主角解决 dilemma_desc 中的 desire 与 misgiving 的冲突。
- 正确示例："[匿名警告]写匿名信给高衙内，假称神侯府已盯上他"（帮助无情既保护百姓又避免直接冲突）
- 正确示例："[私下调解]请与双方都有交情的第三方出面说和"（帮助无情找到折中办法）
- 错误示例："[威胁]恐吓高衙内让他收手"（这是玩家替无情做决定，不是帮助无情）
- 格式要求：[手段]具体做法，15-20字
- 可选手段标签：[匿名警告]、[私下调解]、[迂回保护]、[暗中调查]、[借力施压]、[拖延时间]、[转移视线]、[制造障碍]

【重要】选项必须体现对困境主角 dilemma_desc 的回应：
- 选项1：帮助主角实现 desire（想做但不敢做的事）
- 选项2：帮助主角化解 misgiving（担心但不得不面对的事）
- 选项3：折中方案，平衡 desire 和 misgiving
"""
        
        instructions = {
            StoryPhase.EMERGE: f"""
这是困境的第一幕。矛盾刚刚出现苗头，大多数人还浑然不觉。
- 叙事节奏：暗流涌动，信息不完整，暗示更大的阴谋或冲突
- 选项特征：成本低但效果不确定，试探性介入
- 新闻语气：八卦试探，街头巷尾的风言风语
- 玩家情绪目标：好奇 + 轻微担忧
- 选项总数：3个，数值变动范围：±5~±20（低成本、低收益）
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
- 选项总数：3个，选项数值变动范围：±10~±30（成本上升、收益也更明显）
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
- 玩家情绪目标：心痛/ Lesser-texture/宝石ți Bottom/until the end/diaspora
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
  - 选项总数：3个，围绕"善后"设计：修复关系/巩固收益/弥补损失/放下执念
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
            traits.append("行事谨慎")
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
            guidance_lines.append("- 【脾气暴躁】此人易怒冲动，事件中可能因一时气愤做出匆忙决定")
        elif temper <= 20:
            guidance_lines.append("- 【极度温和】此人脾性极好，极少动怒，即使受辱也能保持冷静")
        elif temper <= 40:
            guidance_lines.append("- 【脾气温和】此人性格平和，不易被激怒，会理性思考后再行动")
        else:
            guidance_lines.append("- 【脾气一般】此人情绪稳定，既不易暴怒也不过分节气门")
        
        # 胆量
        if spirit >= 80:
            guidance_lines.append("- 【极度勇敢】此人胆大包天，面对强敌也毫不退缩，甚至敢于挑战权威")
        elif spirit >= 60:
            guidance_lines.append("- 【胆识过人】此人勇敢无畏， xây遵守冒险，选项可包含高风险高回报的选择")
        elif spirit <= 20:
            guidance_lines.append("- 【极度胆小】此人胆小如鼠，稍有危险就退缩，需要被保护或推动")
        elif spirit <= 40:
            guidance_lines.append("- 【较为胆小】此人谨慎保守，厌恶风险，更倾向于稳妥的解决方案")
        else:
            guidance_lines.append("- 【胆识一般】此人既不过于鲁莽也不过分离合，会权衡利弊后行动")
        
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
            guidance_lines.append("- 【极度吸尘】此人思虑极深，每一步都精心计算，从不做无把握之事")
        elif act_style <= 40:
            guidance_lines.append("- 【风格惨烈】此人谨慎细致，谋定而后动，但可能因过于谨慎错失良机")
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
            guidance_lines.append("- 【情无不特别倾向】此人对待感情比较理性，不会过分执着")
        
        # 野心
        if ambition >= 80:
            guidance_lines.append("- 【野心极大】此人志向远大，渴望功成名就，为此可以忍受常人不能忍之事")
        elif ambition >= 60:
            guidance_lines.append("- 【野心勃勃】此人渴望出人头地，有强烈的抱负，可能为此不择手段")
        elif ambition <= 20:
            guidance_lines.append("- 【毫无野心】此人淡泊名利，只想安稳度日，对权力地位毫无兴趣")
        elif ambition <= 40:
            guidance_lines.append("- 【较为砖瓦】此人安于现状，更重视当下的平静生活")
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
                                  player: NPCData) -> LiveNewsItem:
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
            import asyncio
            # 修复：在Pygame环境中，获取事件循环可能导致死锁
            # 使用 get_running_loop() 获取当前运行的事件循环
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # 如果没有运行中的循环，才使用 get_event_loop()
                loop = asyncio.get_event_loop()
            
            # 在线程池中执行同步LLM调用，避免阻塞事件循环
            response = await loop.run_in_executor(
                None,  # 使用默认线程池
                lambda: self.llm.chat(
                    system_prompt=system_prompt,
                    user_message=user_prompt,
                    max_tokens=3000
                )
            )
            log_game_event(f"[RollingStoryGenerator] LLM响应: {response.raw_response}", tag="LLM_RESPONSE")
            
            # 解析返回的JSON，直接创建LiveNewsItem
            npc_id_str = str(getattr(npc, 'id', 'unknown'))
            npc_name_str = str(getattr(npc, 'name', '未知'))
            news_item = self._parse_event_card(
                response.raw_response, 
                npc_id_str,
                npc_name_str
            )
            return news_item
            
        except Exception as e:
            log_game_event(f"[RollingStoryGenerator] 生成失败: {e}", tag="ERROR")
            raise

    def _parse_event_card(self, response: str, npc_id: str, npc_name: str = "") -> LiveNewsItem:
        """解析LLM返回的事件卡JSON - 直接创建LiveNewsItem，避免中间转换
        
        Args:
            response: LLM返回的JSON字符串
            npc_id: 困境主角NPC的ID（生成事件的核心NPC）
            npc_name: 困境主角NPC的名字
        """
        
        try:
            # 提取JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)
            
            # 解析困境描述
            dilemma_desc_data = data.get('dilemma_desc', {})
            
            # 解析自动恶化
            auto_decay_data = data.get('auto_decay', {})
            
            # 解析选项（转换为LiveNewsItem的choices格式）
            choices = []
            for choice_data in data.get('choices', []):
                choice = {
                    "text": choice_data.get('text', ''),
                    "requirement": choice_data.get('requirement'),
                    "cost": choice_data.get('cost'),
                    "effect": choice_data.get('effect'),
                    "transfer": choice_data.get('transfer'),
                    "tension_delta": choice_data.get('tension_delta', 0),
                    "consequence_preview": choice_data.get('consequence_preview', ''),
                    "hidden": choice_data.get('hidden', False),
                    "unlock_condition": choice_data.get('unlock_condition')
                }
                # 过滤掉None值
                choice = {k: v for k, v in choice.items() if v is not None}
                choices.append(choice)
            
            # 从actors中提取actor_ids和actor_names
            actors = data.get('actors', [])
            actor_ids = []
            actor_names = []
            for actor in actors:
                npc_id_val = actor.get('npc_id')
                if npc_id_val:
                    try:
                        actor_ids.append(int(npc_id_val))
                    except (ValueError, TypeError):
                        pass
                actor_names.append(actor.get('npc_name', ''))
            
            # 创建LiveNewsItem（直接创建，避免EventCard中间转换）
            news_item = LiveNewsItem(
                id=f"beat_{npc_id}_{data.get('chain_phase', 'EMERGE')}_{hash(response) % 10000}",
                title=data.get('title', '未命名事件'),
                subtitle=data.get('event_theme', ''),
                headline=data.get('description', '')[:100],  # 取前100字作为headline
                description=data.get('description', ''),
                category=NewsCategory.SOCIAL,  # 默认社会类
                dilemma_type=DilemmaType(data.get('dilemma_type', 'MORAL_GREY')) if DilemmaType else None,
                actor_ids=actor_ids,
                actor_names=actor_names,
                location="街市",  # 默认地点
                choices=choices,
                tags=data.get('tags', []),
                comments=data.get('comments', []),
                image_prompt=data.get('image_prompt', ''),
                # 事件扩写相关字段
                dilemma_desc_summary=dilemma_desc_data.get('summary', ''),
                dilemma_desc_desire=dilemma_desc_data.get('desire', ''),
                dilemma_desc_misgiving=dilemma_desc_data.get('misgiving', ''),
                actors=actors,
                auto_decay_next_phase=auto_decay_data.get('next_phase_preview', ''),
                auto_decay_auto_effect=auto_decay_data.get('auto_effect', ''),
                auto_decay_auto_transfer=auto_decay_data.get('auto_transfer', ''),
                auto_decay_auto_tension_delta=auto_decay_data.get('auto_tension_delta', 0),
                chain_phase=data.get('chain_phase', 'EMERGE'),
                event_theme=data.get('event_theme', ''),
                emotion_tone=data.get('emotion_tone', '中性'),
                target_npc_id=npc_id,  # 困境主角ID
                target_npc_name=npc_name,  # 困境主角名字
                raw_json=data  # 保存原始JSON用于对话扩写
            )
            
            return news_item
            
        except Exception as e:
            log_game_event(f"[RollingStoryGenerator] 解析事件卡失败: {e}", tag="ERROR")
            # 返回一个默认的LiveNewsItem
            return LiveNewsItem(
                id=f"beat_{npc_id}_ERROR_{hash(response) % 10000}",
                title="事件生成中...",
                description="请稍后再试"
            )
