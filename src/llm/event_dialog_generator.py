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
    speaker_type: str     # NARRATOR/MAINNPC/MINORNPC/PLAYER/CROWD
    speaker_name: str     # 说话人名字
    text: str             # 对话文本
    action: str = ""      # 动作指令
    speaker_id: int = 0   # 说话人ID（旁白和玩家为0）


@dataclass
class EventScriptFull:
    """完整事件剧本（第3步输出）"""
    intro_dialogs: List[EventDialogLine]           # 开场对话序列
    choice_dialogues: Dict[str, List[EventDialogLine]]  # 选项后续对话 {choice_0: [...], ...}
    ignore_dialogue: List[EventDialogLine]         # 冷眼旁观对话


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
        news_item: 'LiveNewsItem',
        npc_a_name: str,
        npc_b_name: Optional[str] = None,
        effect_a: str = "",
        effect_b: str = "",
        effect_c: str = ""
    ) -> EventScriptFull:
        """
        第3步：基于LiveNewsItem，扩写完整的对话序列
        
        Args:
            news_item: 新闻事件对象（LiveNewsItem/EventNotification）
            npc_a_name: 主角名字（困境主角）
            npc_b_name: 配角名字（压力来源/求助对象等）
            effect_a/b/c: 三个选项的效果字符串（用于生成动作指令）
            
        Returns:
            EventScriptFull: 完整剧本
        """
        # 直接使用news_item中保存的原始JSON
        import json
        if hasattr(news_item, 'raw_json') and news_item.raw_json:
            event_json = json.dumps(news_item.raw_json, ensure_ascii=False, indent=2)
        else:
            # 兼容旧代码：如果没有raw_json，返回None
            log_game_event("[EventDialogGen] news_item缺少raw_json，无法扩写对话", tag="DIRECTOR")
            return None
        
        system_prompt = """你是《大宋实况》的高级对话编剧，擅长金庸、古龙式的武侠江湖对话。负责将事件剧本扩写成主线任务级别的AVG对话序列。

## 核心原则

- **你只写对话**：你的产出是"现场演绎对话"，以及相关的action剧情演出
- **剧情必须忠于输入**：每个 choice 对应的对话分支，其剧情走向、角色反应、情感结局必须与输入 JSON 中该 choice 的各字段保持一致
- **角色必须忠于输入**：对话中出现的角色名字和ID必须来自输入 JSON 的 actors 和 comments
- **时间必须即时**：所有对话发生在**同一现场、短时间内**（几分钟到几小时内），**禁止出现"几日后""三天后""数日后"等时间跳跃**！后续发展只留暗示，不要直接写出。

## 输入数据格式

你将收到一个完整的事件 JSON，重点关注以下字段：
- **actors**：角色列表（npc_name / npc_id / role），用于确定对话中的说话人
- **title / description**：新闻标题和正文，用于理解事件背景
- **dilemma_desc**：困境描述（summary / desire / misgiving），用于把握情感基调
- **choices**：玩家选项数组，每个选项的以下字段共同构成该分支对话的剧情指南：
  - `text`：玩家采取的行动（决定对话中"玩家做了什么"）
  - `cost`：玩家付出的代价（决定对话中玩家的"肉疼感"或"慷慨感"）
  - `effect`：对各NPC的影响（决定NPC的态度变化和情绪反应）
  - `transfer`：资源流转关系（决定"谁得到了好处、谁吃了亏"）
  - `consequence_preview`：短期影响应该直接表现出来，长期影响只需要留有暗示
- **comments**：街坊评论，其中的 NPC 可作为围观群众出场
- **auto_decay**：无人介入时的自然发展，作为"玩家旁观不介入"分支的剧情指南

## 输入中的机制字段参考说明

以下说明帮助你理解 cost/effect/transfer/auto_effect 字段的含义，以便准确地将其转化为对话剧情和 action 指令。你不需要在输出中原样复制这些字段值。

### cost/effect/auto_effect 字段格式
- 格式: `actor_id:attribute:changevalue`（多个用分号隔开）
- `actor_id`: NPC的纯数字ID（如1001、1013）或PLAYER
- `attribute`: 属性名（如 money、fame、strength、wit、charm、agility，或关系属性如 affinity_to_player）
- `changevalue`: 变化数值（负数代表损失，正数代表收益）
- NPC情绪变化格式: `actor_id:emotion:EMOTION值`
- 情绪枚举: NORMAL(平静), HAPPY(开心), SAD(悲伤), ANGRY(愤怒), DEPRESSED(沮丧), DESPAIR(绝望), ANXIOUS(焦虑), CONFUSED(困惑)

### transfer 字段格式
- 金钱/物品的转移，格式：`from_actor->to_actor:attr:value`
- 示例：`PLAYER->1001:money:30`（玩家给NPC 30金钱）
- NPC间转移：`1003->1001:money:50`

### choice对对话的影响
- **cost（代价）**：通过玩家对话中的犹豫、肉疼感，或NPC对玩家付出的反应来体现
- **effect（收益）**：通过NPC态度的明显转变、情绪变化来体现（如从冷漠变感激、从愤怒变开心）
- **transfer（资源流转）**：通过具体的给钱、交付物品等动作场景来体现
- **consequence_preview（影响预测）**：短期影响应该直接表现出来，长期影响只需要留有暗示

## 对话行数据结构

每句对话是一个 JSON 对象：
```json
{
  "speaker_type": "MAINNPC",
  "speaker_name": "阿禅",
  "speaker_id": 1015,
  "text": "各位...各位行行好，我真的不是有意欠账...",
  "action": "NPC_GOTO:阿禅:玩家"
}
```

### 字段说明
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| speaker_type | string | ✅ | 说话人类型，枚举值见下表 |
| speaker_name | string | ✅ | 说话人名字 |
| speaker_id | int | ✅ | 说话人NPC ID（旁白和玩家为0） |
| text | string | ✅ | 对话文本或旁白描写 |
| action | string | ❌ | NPC表演行动指令，无行动时填空字符串 "" |

### speaker_type 枚举值
| speaker_type | 适用场景 | speaker_name 规则 | speaker_id 来源 |
|---|---|---|---|
| NARRATOR | 环境描写、心理活动、场景转换 | 固定 "旁白" | 0 |
| MAINNPC | 当事NPC说话（困境主角） | 从 actors 中 role="困境主角" 取 npc_name | 对应 npc_id |
| MINORNPC | 配角NPC说话（压力来源/求助对象等） | 从 actors 中其他 role 取 npc_name | 对应 npc_id |
| PLAYER | 玩家角色说话 | 玩家游戏名 | 0 |
| CROWD | 围观NPC说话 | 从 comments 中取 user 字段 | 对应NPC的ID（如无法确定则填0） |

## action 字段规则（重要！严格遵守）

### action 的本质
action 字段是游戏引擎可解析的表演指令，用于驱动角色在场景中的实际动作。**禁止**填写纯文学描写（如"（他捏紧了手）""（眼中含泪）"），这些情感通过 text 对话文本本身来传达。

### 可用的 action 指令
| 指令格式 | 含义 | 使用场景示例 |
|---|---|---|
| NPC_FLEE:NPC名 | 该NPC逃跑离场 | 恶霸被吓退、小偷逃跑、懦夫溜走，某NPC在剧情中离开/逃跑/被赶走时使用 |
| NPC_ATTACK:攻击者名:目标名 | 攻击者对目标发动攻击 | 冲突升级打斗、恶霸动手、玩家出拳，只有明确的暴力冲突才使用，不要滥用 |
| NPC_GOTO:NPC名:目标名 | NPC走到目标附近 | 走上前对话、上前拦住、凑近耳语 |
| SHOW_EVENT_CHOICE | 弹出玩家选择界面 | 固定出现在 intro 最后一句的 action 中 |

## 对话编排结构（重要！严格遵守）

### 1. 开场对话（intro）：8-10 句
| 阶段 | 句数 | speaker_type | 内容要求 |
|---|---|---|---|
| 场景开幕 | 第1句 | NARRATOR | 描绘场景氛围，简短20字内，包含地点 |
| 冲突展示 | 第2-3句 | MINORNPC | 对立方先开口，展示威胁/挑衅/施压 |
| 当事人回应 | 第4-5句 | MAINNPC | 当事NPC回应，体现困境中的情绪（恐惧/愤怒/求饶/挣扎） |
| 群众反应 | 第6句 | CROWD | 围观群众窃窃私语，体现旁观者视角 |
| 冲突升级 | 第7句 | MINORNPC | 步步紧逼，言语或动作升级 |
| 群众或当事人反应 | 第8句 | MAINNPC/CROWD | 有人退缩、有人看热闹，体现众生相 |
| 氛围收紧 | 第9句 | NARRATOR | 描写紧张氛围升级到临界点 |
| 交给玩家 | 第10句 | NARRATOR | "围观的你，会怎么做？"，action 字段填 "SHOW_EVENT_CHOICE" |

> **禁止**：不要把所有剧情塞进第1句旁白！旁白只描述环境！
> **必须**：CROWD 至少出现 2 次，体现群众存在感！

### 2. 选项后续对话（choice_dialogues）：每个分支 5-7 句
对 choices 数组中的每个 choice，编写一个分支。编写时必须综合参考该 choice 的 text、cost、effect、transfer、consequence_preview。

| 阶段 | 句数 | speaker_type | 内容要求 |
|---|---|---|---|
| 玩家登场 | 第1句 | PLAYER | 代入感强，台词体现选择的性质和性格 |
| 群众惊讶 | 第2句 | CROWD | 群众对玩家介入的即时反应（惊讶/叫好/质疑） |
| 各方反应 | 第3-4句 | MINORNPC/MAINNPC | 对立方和主角对玩家行动的反应（惊讶/愤怒/感激） |
| 交锋推进 | 第5-6句 | 混合 | 对话或动作交锋，推进到结果 |
| 群众议论 | 第7句（可选） | CROWD | 事件落幕后群众的评价和议论 |
| 余韵收尾 | 最后一句 | NARRATOR | 简短结局余韵，留白暗示后续发展 |

### 3. 冷眼旁观对话（ignore_dialogue）：5-8 句
剧情走向必须符合输入 JSON 中 auto_decay 的描述。
| 阶段 | 句数 | speaker_type | 内容要求 |
|---|---|---|---|
| 旁观描写 | 第1句 | NARRATOR | 描写玩家驻足旁观、未出手的状态 |
| 事态恶化 | 第2-3句 | MINORNPC/MAINNPC | 无人介入，冲突按自然方向发展 |
| 群众冷漠 | 第4句 | CROWD | 群众摇头散去或冷眼旁观 |
| 结局落定 | 第5-6句 | MINORNPC/MAINNPC | 事件按 auto_decay 描述的方向收场 |
| 余韵收尾 | 最后一句 | NARRATOR | 体现"无人帮助"的唏嘘感，暗示后续恶化 |

## 对话风格要求
- **文白相间**：七分白话三分文言，如"你这厮好大的胆子"而非"你胆子很大"
- **性格鲜明**：恶霸要横、书生要酸、商人要精、百姓要怂，每个角色说话有辨识度
- **台词简短**：每句 text 控制在 15-30 字，不要长篇大论
- **CROWD 要活**：群众台词要有市井烟火气，展现围观百姓的真实反应
- **情感靠台词传达**：角色的情感、神态、语气通过 text 的措辞和语气词来体现，不要依赖 action 来描写表情神态

## 输出格式

严格输出以下 JSON，不要输出任何 JSON 以外的内容：

```json
{
  "intro": [
    {"speaker_type": "NARRATOR", "speaker_name": "旁白", "speaker_id": 0, "text": "...", "action": ""},
    ...
  ],
  "choice_dialogues": {
    "choice_0": [
      {"speaker_type": "PLAYER", "speaker_name": "玩家", "speaker_id": 0, "text": "...", "action": ""},
      ...
    ],
    "choice_1": [...],
    "choice_2": [...]
  },
  "ignore_dialogue": [
    {"speaker_type": "NARRATOR", "speaker_name": "旁白", "speaker_id": 0, "text": "...", "action": ""},
    ...
  ]
}
```"""

        # 获取困境主角信息
        target_npc_name = getattr(news_item, 'target_npc_name', '')
        target_npc_id = getattr(news_item, 'target_npc_id', '')
        
        user_message = f"""请根据以下事件 JSON 扩写完整的 AVG 对话序列。
严格遵守 System Prompt 中的对话编排结构和数据格式要求，只输出 JSON。

【重要提示】
- 困境主角（MAINNPC）是：{target_npc_name} (ID: {target_npc_id})
- 开场对话中，MAINNPC 必须出现并有台词，展现其内心挣扎
- 不要将被欺负的受害者或作恶的反派误认为 MAINNPC

{event_json}"""

        # 调用LLM（使用更高的max_tokens以确保完整的对话剧本）
        # 对话剧本通常需要 3000+ tokens（包含ignore_dialogue）
        response = self.llm_service.chat(system_prompt, user_message, max_tokens=3500)
        
        log_game_event(f"[EventDialogGen] LLM扩写响应：{response.raw_response}...", tag="DIRECTOR")

        if not response.success:
            return None
        
        # 解析JSON响应
        try:
            data = self._extract_json(response.raw_response)
            
            # 解析intro
            intro = [self._parse_dialog_line(d) for d in data.get('intro', [])]
            
            # 解析choice_dialogues（新格式）
            choice_dialogues = {}
            choice_data = data.get('choice_dialogues', {})
            for key in ['choice_0', 'choice_1', 'choice_2']:
                if key in choice_data:
                    choice_dialogues[key] = [self._parse_dialog_line(d) for d in choice_data[key]]
            
            # 解析ignore_dialogue
            ignore_dialogue = [self._parse_dialog_line(d) for d in data.get('ignore_dialogue', [])]
            
            # 自动注入效果指令到对应选项的首句
            effects = [effect_a, effect_b, effect_c]
            for i, key in enumerate(['choice_0', 'choice_1', 'choice_2']):
                if key in choice_dialogues and effects[i] and choice_dialogues[key]:
                    choice_dialogues[key][0].action = self._merge_actions(
                        choice_dialogues[key][0].action, effects[i]
                    )
            
            return EventScriptFull(
                intro_dialogs=intro,
                choice_dialogues=choice_dialogues,
                ignore_dialogue=ignore_dialogue
            )
        except Exception as e:
            log_game_event(f"[EventDialogGen] 解析完整剧本失败: {e}", tag="DIRECTOR")
            return None
    
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
        """解析单条对话（支持新格式）"""
        # 新格式：speaker_type, speaker_name, speaker_id
        speaker_type = data.get('speaker_type', data.get('speaker', 'NARRATOR'))
        speaker_name = data.get('speaker_name', '旁白')
        speaker_id = data.get('speaker_id', 0)
        
        # 兼容旧格式：如果只有speaker字段，尝试推断
        if 'speaker' in data and 'speaker_type' not in data:
            speaker = data['speaker']
            if speaker == 'NARRATOR':
                speaker_type = 'NARRATOR'
                speaker_name = '旁白'
            elif speaker == 'SELF':
                speaker_type = 'MAINNPC'
            elif speaker == 'OTHER':
                speaker_type = 'MINORNPC'
            elif speaker == 'PLAYER':
                speaker_type = 'PLAYER'
                speaker_name = '玩家'
            elif speaker == 'CROWD':
                speaker_type = 'CROWD'
        
        return EventDialogLine(
            speaker_type=speaker_type,
            speaker_name=speaker_name,
            text=data.get('text', '...'),
            action=data.get('action', ''),
            speaker_id=speaker_id
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
# 全局单例
# ═══════════════════════════════════════════════════════════════

_generator_instance = None

def get_event_dialog_generator() -> EventDialogGenerator:
    """获取事件对话生成器单例"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = EventDialogGenerator()
    return _generator_instance