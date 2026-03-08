# src/llm/event_dialog_generator.py
"""
事件对话生成器 - 基于LLM动态生成事件剧情
流程：
1. EventManager触发事件 → 选择演员(NPC_A, NPC_B)和事件种子(event_id)
2. 调用LLM生成简版剧情（描述+选项）
3. 调用LLM扩写完整对话剧本（类似quest_system的DialogLine格式）
4. 返回对话序列供StoryUI播放
"""

import json
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from .llm_service import LLMService
from .config import LLMConfig
from src.utils import log_game_event


@dataclass
class EventDialogLine:
    """事件对话行（与quest_system的DialogLine兼容）"""
    speaker: str          # NARRATOR/SELF(A)/OTHER(B)/PLAYER
    text: str             # 对话文本
    action: str = ""      # 动作指令：SHAKE_CAMERA, SHOW_EVENT_CHOICE, PLAYER:Money:-100等
    speaker_id: Optional[int] = None  # 说话人ID（运行时填充）


@dataclass
class EventScriptBrief:
    """简版事件剧本（第2步输出）"""
    title: str                    # 事件标题
    description: str              # 事件描述
    choice_a: str                 # 选项A文本
    choice_b: str                 # 选项B文本
    choice_c: str = ""            # 选项C文本（可选）
    context_hint: str = ""        # 上下文提示（供扩写用）
    image_prompt: str = ""        # 豆包生图提示词（中文）


@dataclass
class EventScriptFull:
    """完整事件剧本（第3步输出）"""
    intro_dialogs: List[EventDialogLine]      # 开场对话序列
    choice_a_dialogs: List[EventDialogLine]   # 选项A后续对话
    choice_b_dialogs: List[EventDialogLine]   # 选项B后续对话
    choice_c_dialogs: List[EventDialogLine]   # 选项C后续对话


class EventDialogGenerator:
    """
    事件对话生成器
    """
    
    def __init__(self):
        self.llm_service = LLMService.get_instance()
        self.config = LLMConfig.get_instance()
    
    def is_available(self) -> bool:
        """检查LLM服务是否可用"""
        return self.llm_service.is_available()
    # 扩写完整对话剧本
    
    def expand_to_full_script(
        self,
        brief: EventScriptBrief,
        npc_a_name: str,
        npc_b_name: Optional[str] = None,
        effect_a: str = "",
        effect_b: str = "",
        effect_c: str = ""
    ) -> EventScriptFull:
        """
        第3步：基于简版剧本，扩写完整的对话序列
        
        Args:
            brief: 简版剧本
            npc_a_name: 主角名字（用于替换{A}）
            npc_b_name: 配角名字（用于替换{B}）
            effect_a/b/c: 三个选项的效果字符串（用于生成动作指令）
            
        Returns:
            EventScriptFull: 完整剧本
        """
        system_prompt = """你是《大宋实况》的高级对话编剧，擅长金庸、古龙式的武侠江湖对话。负责将事件剧本扩写成主线任务级别的AVG对话序列。

【质量标准】（对标金庸/古龙武侠小说）
1. **对话要有层次感**：从平静 → 紧张 → 爆发 → 余韵（参考《天龙八部》酒楼冲突、《多情剑客无情剑》街头对峙）
2. **角色要有个性**：
   - 恶霸：狠辣、阴狠、不讲理（"今天你若不给，别怪我手下不留情！"）
   - 商人：胆怯但有骨气（"我...我实在拿不出这么多..."）
   - 侠客：义薄云天、一言九鼎（"光天化日，岂容你如此行凶！"）
3. **玩家抉择要有分量**：选择前有犹豫，选择后有后果展现
4. **情绪要细腻**：用动作、语气词、省略号表现人物心理

【对话结构】（重要！）
1. **开场对话（intro）**（6-8句，必须分散到角色）：
   - 第1句：旁白描绘场景氛围（简短，20字内）
   - 第2-3句：**OTHER先开口**（恶霸威胁/挑衅）
   - 第4-5句：**SELF回应**（恐惧/愤怒/求饶）
   - 第6-7句：**OTHER步步紧逼**（言语或动作升级）
   - 第8句：旁白"围观的你，会怎么做？" + 动作SHOW_EVENT_CHOICE
   - **禁止**：不要把所有剧情塞进第1句旁白！旁白只描述环境！

2. **选项后续对话（choice_a/b/c）**（4-6句每个）：
   - 第1句：**PLAYER开口**（代入感强，展现性格）
   - 第2-3句：**OTHER/SELF反应**（惊讶/愤怒/感激）
   - 第4-5句：**对话或动作交锋**（打斗/交涉/逃跑）
   - 最后一句：旁白结局余韵（简短总结，留白）

【角色代号】
- **NARRATOR**: 旁白（环境描述、心理活动、时间流逝）
- **SELF**: 主角NPC（事件受害者/发起者）
- **OTHER**: 配角NPC（对手/帮手）
- **PLAYER**: 玩家（我/你）

【动作指令】（action字段，可用分号组合多条）

**演出效果**（视觉反馈）：
- `SHAKE_CAMERA:强度` - 震动镜头（打斗5/冲击10/爆炸15）
- `FLASH_WHITE:毫秒` - 白屏闪烁（被击中效果，通常100ms）
- `FADE_TO_BLACK:毫秒` - 黑屏渐入（时间流逝、昏迷，通常500ms）
- `FADE_FROM_BLACK:毫秒` - 黑屏渐出（苏醒、场景转换）

**NPC状态 - 基础**（言行一致：对话提到什么就改什么）：
- `SET_AFFINITY:NPC名:±数值` - 好感度变化（感激+30/厌恶-20）
- `SET_MONEY:NPC名:±数值` - 金钱变化（被抢-50/收到+100）
- `SET_EMOTION:NPC名:情绪` - 表情（ANGRY/SCARED/HAPPY/SAD）
- `SET_HP:NPC名:数值` - 设置生命值（受伤后）
- `SET_HUNGER:NPC名:数值` - 饥饿度（0-100，饥饿状态用）

**NPC组织与势力**（人生重大转折）：
- `SET_ORG:NPC名:组织ID` - 加入组织（如beggar_gang/heifeng_zhai/kaifeng_fu）
- `SET_ORG:NPC名:NONE` - 离开当前组织
- `SET_ORG_RANK:NPC名:±数值` - 组织内升降级（+1晋升/-1降级）
- `SET_ORG_ROLE:NPC名:角色` - 组织角色（LEADER/ELDER/MEMBER/BODYGUARD）
- `SET_JOB:NPC名:职业` - 转换职业（BANDIT/MERCHANT/GUARD/BEGGAR等）
- `SET_POWER_TYPE:NPC名:势力` - 势力阵营（士/农/工/商/学/兵/游/匪/民）

**NPC社会地位**（阶层变动）：
- `SET_SOCIAL_LEVEL:NPC名:±数值` - 社会等级（1贱民~5权贵）
- `SET_WEALTH_LEVEL:NPC名:±数值` - 财富等级（1赤贫~5富豪）
- `SET_INFLUENCE:NPC名:±数值` - 影响力等级（1无名~5权倾一方）
- `SET_FREEDOM:NPC名:状态` - 自由度（FREE_FULL/FREE_HALF/FREE_NONE）

**NPC标签与身份**（特殊标记）：
- `ADD_TAG:NPC名:标签` - 添加标签（CRIMINAL罪犯/HERO英雄/WANTED通缉/OUTLAW法外之徒）
- `REMOVE_TAG:NPC名:标签` - 移除标签
- `SET_REFUGEE:NPC名:0或1` - 流民状态（1变成流民/0安定）
- `SET_FOLLOWER:NPC名:0或1` - 门客状态（1成为门客）

**NPC关系网络**：
- `SET_RELATION:NPCA:NPCB:±数值` - NPC之间好感度
- `SET_HATRED:NPC名:目标:±数值` - 仇恨值（超过30会攻击）
- `SET_KNOWS_PLAYER:NPC名:1` - 标记NPC认识玩家

**NPC行为**（让角色动起来）：
- `NPC_FLEE:NPC名` - 逃跑（恶霸被吓退、小偷逃跑）
- `NPC_ATTACK:攻击者:目标` - 发动攻击（冲突升级）
- `NPC_SAY:NPC名:台词` - 额外气泡（场外喊话）
- `NPC_FOLLOW:NPC名:目标` - 跟随某人
- `NPC_MOVE:NPC名:x:y` - 移动到位置

**玩家状态**（选择后果）：
- `PLAYER_MONEY:±数值` - 玩家金钱（花钱-30/得钱+50）
- `PLAYER_FAME:±数值` - 玩家声望（行侠仗义+10/见死不救-5）
- `PLAYER_HP:±数值` - 玩家生命（被打伤-20）
- `PLAYER_KNOCKOUT` - 玩家昏迷（战斗失败）

**世界状态**：
- `DESPAWN_NPC:NPC名` - 移除NPC（死亡/离开）
- `ADVANCE_TIME:小时` - 时间推进（剧情需要）

**系统控制**（必须使用）：
- `SHOW_EVENT_CHOICE` - 显示选择界面（开场末尾**必须有**）

**示例组合**：
- 恶霸拍桌威胁：`"action": "SHAKE_CAMERA:5;SET_EMOTION:李四:SCARED"`
- 玩家出手相助：`"action": "PLAYER_FAME:+10;SET_AFFINITY:鱼西施:+30"`
- 恶霸被吓跑：`"action": "NPC_FLEE:恶霸;SET_AFFINITY:受害者:+20"`
- 玩家被打伤：`"action": "FLASH_WHITE:100;PLAYER_HP:-15;SHAKE_CAMERA:8"`

【语言风格】（江湖气韵）
- [宜] 宋代江湖对话："大爷饶命！""莫非你真当我好欺？""此恩，他日必报！"
- [宜] 古龙式短句："他笑了。""刀，出鞘了。""血，溅在青石板上。"
- [宜] 金庸式描写："那恶霸冷笑一声，伸手便要去抓账簿"
- [禁] 避免文言文："尔等休走！""吾当..."
- [禁] 避免现代网络用语："绝绝子""yyds"
- [宜] 善用情绪词：叹词（唉、哎呀）、语气（吧、啊、呢）、省略号

【细节技巧】
- 用"..."表示沉默/犹豫："他低下头，不再言语..."
- 用动作描写表现情绪："那恶霸猛地一拍桌子，吓得周围人纷纷后退"
- 用环境烘托氛围："围观的百姓开始窃窃私语，有人悄悄退开"
- **关键**：每句对话都要有"画面感"，让玩家仿佛看到武侠剧

【输出格式】
严格按照JSON格式返回：
```json
{
  "intro": [
    {"speaker": "NARRATOR", "text": "场景描绘（具体细节）", "action": ""},
    {"speaker": "OTHER", "text": "对手台词（带情绪）", "action": ""},
    {"speaker": "SELF", "text": "主角反应（恐惧/愤怒）", "action": ""},
    {"speaker": "NARRATOR", "text": "氛围升级描写", "action": ""},
    {"speaker": "NARRATOR", "text": "你会怎么做？", "action": "SHOW_EVENT_CHOICE"}
  ],
  "choice_a": [
    {"speaker": "PLAYER", "text": "玩家台词（展现性格）", "action": ""},
    {"speaker": "OTHER", "text": "对方反应", "action": ""},
    {"speaker": "SELF", "text": "主角感激/惊讶", "action": ""},
    {"speaker": "NARRATOR", "text": "事件结局（有余韵）", "action": ""}
  ],
  "choice_b": [同上结构],
  "choice_c": [同上结构]
}
```

【示例参考】（武侠小说质量）
[禁] 错误示例（干瘪无味）：
```json
"intro": [
  {"speaker": "NARRATOR", "text": "张三勒索李四，李四很害怕，你会怎么做？", "action": "SHOW_EVENT_CHOICE"}
]
```

[宜] 正确示例（江湖气韵）：
```json
"intro": [
  {"speaker": "NARRATOR", "text": "街市骤然安静。", "action": ""},
  {"speaker": "OTHER", "text": "李老板，这月的保护费，该交了吧？", "action": ""},
  {"speaker": "SELF", "text": "大爷...我、我这月生意不好，实在拿不出...", "action": ""},
  {"speaker": "OTHER", "text": "拿不出？", "action": ""},
  {"speaker": "NARRATOR", "text": "那恶霸猛地一掌拍在摊位上，木板应声碎裂。", "action": "SHAKE_CAMERA"},
  {"speaker": "OTHER", "text": "那就别怪我砸了你的摊子！", "action": ""},
  {"speaker": "NARRATOR", "text": "围观的百姓纷纷后退。你，会怎么做？", "action": "SHOW_EVENT_CHOICE"}
]
```

请根据以上标准，为玩家创造一个难忘的江湖抉择时刻。"""

        user_message = f"""简版剧本：
标题: {brief.title}
描述: {brief.description}
选项A: {brief.choice_a}
选项B: {brief.choice_b}
选项C: {brief.choice_c}
场景氛围: {brief.context_hint}

主角NPC: {npc_a_name}（用SELF代指）
配角NPC: {npc_b_name or '无'}（用OTHER代指）

请扩写成完整对话序列。"""

        # 调用LLM（使用更高的max_tokens以确保完整的对话剧本）
        # 对话剧本通常需要 2000+ tokens
        response = self.llm_service.chat(system_prompt, user_message, max_tokens=2500)
        
        if not response.success:
            return None
        
        # 解析JSON响应
        try:
            data = self._extract_json(response.raw_response)
            
            intro = [self._parse_dialog_line(d) for d in data.get('intro', [])]
            choice_a = [self._parse_dialog_line(d) for d in data.get('choice_a', [])]
            choice_b = [self._parse_dialog_line(d) for d in data.get('choice_b', [])]
            choice_c = [self._parse_dialog_line(d) for d in data.get('choice_c', [])]
            
            # 自动注入效果指令到对应选项的首句
            if effect_a and choice_a:
                choice_a[0].action = self._merge_actions(choice_a[0].action, effect_a)
            if effect_b and choice_b:
                choice_b[0].action = self._merge_actions(choice_b[0].action, effect_b)
            if effect_c and choice_c:
                choice_c[0].action = self._merge_actions(choice_c[0].action, effect_c)
            
            return EventScriptFull(
                intro_dialogs=intro,
                choice_a_dialogs=choice_a,
                choice_b_dialogs=choice_b,
                choice_c_dialogs=choice_c
            )
        except Exception as e:
            log_game_event(f"[EventDialogGen] 解析完整剧本失败: {e}", tag="DIRECTOR")
            return self._generate_fallback_full(brief, npc_a_name, npc_b_name)
    
    # ═══════════════════════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════════════════════
    
    def _extract_json(self, text: str) -> Dict:
        """从LLM响应中提取JSON"""
        # 移除markdown代码块
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*$', '', text)
        
        # 查找JSON对象
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            return json.loads(json_str)
        raise ValueError("未找到有效JSON")
    
    def _parse_dialog_line(self, data: Dict) -> EventDialogLine:
        """解析单条对话"""
        return EventDialogLine(
            speaker=data.get('speaker', 'NARRATOR'),
            text=data.get('text', '...'),
            action=data.get('action', '')
        )
    
    def _merge_actions(self, ai_action: str, effect_str: str) -> str:
        """合并AI生成的动作和事件效果"""
        actions = []
        if ai_action:
            actions.append(ai_action)
        if effect_str:
            actions.append(effect_str)
        return ';'.join(actions)
    
    # ═══════════════════════════════════════════════════════════════
    # 回退方案（LLM不可用时）
    # ═══════════════════════════════════════════════════════════════
    
    def _generate_fallback_brief(
        self, 
        event_id: str, 
        template: str, 
        npc_a: str, 
        npc_b: Optional[str]
    ) -> EventScriptBrief:
        """生成回退简版剧本"""
        return EventScriptBrief(
            title=f"{npc_a}的遭遇",
            description=f"{npc_a}遇到了麻烦：{template}",
            choice_a="伸出援手（花费资源）",
            choice_b="强力干涉（提升威望）",
            choice_c="视而不见",
            context_hint="街道场景"
        )
    
    def _generate_fallback_full(
        self,
        brief: EventScriptBrief,
        npc_a: str,
        npc_b: Optional[str]
    ) -> EventScriptFull:
        """生成回退完整剧本"""
        intro = [
            EventDialogLine('NARRATOR', f'{brief.description}', ''),
            EventDialogLine('NARRATOR', '你会怎么做？', 'SHOW_EVENT_CHOICE')
        ]
        
        choice_a = [
            EventDialogLine('PLAYER', f'让我来帮你！', ''),
            EventDialogLine('SELF', '多谢恩公！', '')
        ]
        
        choice_b = [
            EventDialogLine('PLAYER', f'我会处理这件事。', ''),
            EventDialogLine('NARRATOR', '事态得到了控制。', '')
        ]
        
        choice_c = [
            EventDialogLine('NARRATOR', '你选择了旁观。', ''),
            EventDialogLine('NARRATOR', '事件自行发展。', '')
        ]
        
        return EventScriptFull(intro, choice_a, choice_b, choice_c)


# ═══════════════════════════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════════════════════════

_generator_instance = None

def get_event_dialog_generator() -> EventDialogGenerator:
    """获取事件对话生成器单例"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = EventDialogGenerator()
    return _generator_instance
