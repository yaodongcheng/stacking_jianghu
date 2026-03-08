# StoryDirective 剧情指令规范

## 概述
本文档定义了剧情系统与游戏引擎之间的标准化指令协议。
所有AI生成的剧情内容都通过这套指令影响游戏世界。

## 设计目标
1. **言行一致**：剧情中的每句话、每个选项都应产生对应的机械影响
2. **NPC人生可变**：事件能真正改变NPC的人生轨迹（职业、组织、阶层）
3. **世界持久化**：所有变更都自动同步到游戏状态，无需手动CSV编辑

## 指令分类

### 一、NPC属性指令

| 指令 | 格式 | 说明 |
|-----|------|-----|
| SET_AFFINITY | `SET_AFFINITY:{npc_id}:{delta}` | 修改好感度 |
| SET_HP | `SET_HP:{npc_id}:{value}` | 设置生命值 |
| SET_HUNGER | `SET_HUNGER:{npc_id}:{value}` | 设置饥饿值 |
| SET_MONEY | `SET_MONEY:{npc_id}:{delta}` | 修改金钱 |
| SET_FAME | `SET_FAME:{npc_id}:{delta}` | 修改声望 |
| SET_EMOTION | `SET_EMOTION:{npc_id}:{emotion}` | 设置表情 |

### 二、NPC行为指令

| 指令 | 格式 | 说明 |
|-----|------|-----|
| NPC_MOVE | `NPC_MOVE:{npc_id}:{x}:{y}` | 移动到坐标 |
| NPC_FOLLOW | `NPC_FOLLOW:{npc_id}:{target_id}` | 跟随目标 |
| NPC_ATTACK | `NPC_ATTACK:{npc_id}:{target_id}` | 攻击目标 |
| NPC_FLEE | `NPC_FLEE:{npc_id}` | 逃跑 |
| NPC_SAY | `NPC_SAY:{npc_id}:{text}` | 说话气泡 |
| NPC_ENTER | `NPC_ENTER:{npc_id}` | 角色入场 |
| NPC_EXIT | `NPC_EXIT:{npc_id}` | 角色退场 |

### 三、世界状态指令

| 指令 | 格式 | 说明 |
|-----|------|-----|
| SPAWN_NPC | `SPAWN_NPC:{template}:{x}:{y}` | 生成NPC |
| DESPAWN_NPC | `DESPAWN_NPC:{npc_id}` | 移除NPC |
| ADVANCE_TIME | `ADVANCE_TIME:{hours}` | 时间推进 |
| SET_WEATHER | `SET_WEATHER:{type}` | 设置天气 |
| TRIGGER_EVENT | `TRIGGER_EVENT:{event_id}` | 触发事件 |

### 四、演出效果指令

| 指令 | 格式 | 说明 |
|-----|------|-----|
| FADE_TO_BLACK | `FADE_TO_BLACK:{ms}` | 黑屏渐入 |
| FADE_FROM_BLACK | `FADE_FROM_BLACK:{ms}` | 黑屏渐出 |
| FLASH_WHITE | `FLASH_WHITE:{ms}` | 白屏闪烁 |
| SHAKE_CAMERA | `SHAKE_CAMERA:{intensity}` | 镜头震动 |
| PLAY_SOUND | `PLAY_SOUND:{sound_id}` | 播放音效 |

### 五、玩家指令

| 指令 | 格式 | 说明 |
|-----|------|-----|
| PLAYER_HP | `PLAYER_HP:{delta}` | 玩家生命变化 |
| PLAYER_MONEY | `PLAYER_MONEY:{delta}` | 玩家金钱变化 |
| PLAYER_FAME | `PLAYER_FAME:{delta}` | 玩家声望变化 |
| PLAYER_TELEPORT | `PLAYER_TELEPORT:{x}:{y}` | 传送玩家 |
| PLAYER_KNOCKOUT | `PLAYER_KNOCKOUT` | 玩家昏倒 |

### 六、关系指令

| 指令 | 格式 | 说明 |
|-----|------|-----|
| SET_RELATION | `SET_RELATION:{a_id}:{b_id}:{delta}` | NPC间好感 |
| SET_HATRED | `SET_HATRED:{npc}:{target}:{delta}` | 仇恨值（超30攻击） |
| SET_ALLY | `SET_ALLY:{a_id}:{b_id}` | 设为盟友 |
| SET_ENEMY | `SET_ENEMY:{a_id}:{b_id}` | 设为仇敌 |
| SET_KNOWS_PLAYER | `SET_KNOWS_PLAYER:{npc_id}:{0或1}` | NPC是否认识玩家 |

### 七、组织与势力指令（人生转折）

| 指令 | 格式 | 说明 | 示例 |
|-----|------|-----|------|
| SET_ORG | `SET_ORG:{npc}:{org_id}` | 加入/离开组织 | `SET_ORG:张三:beggar_gang` |
| SET_ORG_RANK | `SET_ORG_RANK:{npc}:{rank}` | 组织内等级 | `SET_ORG_RANK:张三:+1` |
| SET_ORG_ROLE | `SET_ORG_ROLE:{npc}:{role}` | 组织角色 | `SET_ORG_ROLE:张三:LEADER` |
| SET_JOB | `SET_JOB:{npc}:{job}` | 转换职业 | `SET_JOB:张三:BANDIT` |
| SET_POWER_TYPE | `SET_POWER_TYPE:{npc}:{type}` | 势力阵营 | `SET_POWER_TYPE:张三:匪` |

**合法组织ID**: `kaifeng_fu`, `shenhou_fu`, `gao_manor`, `tianshui_alley`, `taixue`, `daxiangguo`, `beggar_gang`, `shizizhipo`, `heifeng_zhai`, `qinglang_bang`, `luopo_gang`, `NONE`

**合法职业**: `FARMER`, `MERCHANT`, `ARTISAN`, `OFFICIAL`, `SCHOLAR`, `GUARD`, `SOLDIER`, `BANDIT`, `THUG`, `BEGGAR`, `MONK`, `SERVANT`, `WORKER`, `NONE`

**合法势力类型**: `士`, `农`, `工`, `商`, `学`, `兵`, `游`, `匪`, `民`

**组织角色**: `LEADER`(首领), `ELDER`(长老), `ADVISOR`(军师), `BODYGUARD`(护卫), `MEMBER`(成员)

### 八、社会地位指令

| 指令 | 格式 | 说明 | 等级范围 |
|-----|------|-----|---------|
| SET_SOCIAL_LEVEL | `SET_SOCIAL_LEVEL:{npc}:{level}` | 社会阶层 | 1贱民~5权贵 |
| SET_WEALTH_LEVEL | `SET_WEALTH_LEVEL:{npc}:{level}` | 财富等级 | 1赤贫~5富豪 |
| SET_INFLUENCE | `SET_INFLUENCE:{npc}:{level}` | 影响力 | 1无名~5权倾一方 |
| SET_FREEDOM | `SET_FREEDOM:{npc}:{status}` | 自由度 | FREE_FULL/FREE_HALF/FREE_NONE |

### 九、标签与身份指令

| 指令 | 格式 | 说明 |
|-----|------|-----|
| ADD_TAG | `ADD_TAG:{npc}:{tag}` | 添加标签 |
| REMOVE_TAG | `REMOVE_TAG:{npc}:{tag}` | 移除标签 |
| SET_REFUGEE | `SET_REFUGEE:{npc}:{0或1}` | 流民状态 |
| SET_FOLLOWER | `SET_FOLLOWER:{npc}:{0或1}` | 门客状态 |

**常用标签**: `CRIMINAL`(罪犯), `HERO`(英雄), `OUTLAW`(法外之徒), `WANTED`(通缉), `VETERAN`(老兵), `INJURED`(受伤), `CORRUPT`(贪官), `RIGHTEOUS`(正义), `VILLAIN`(恶人)

### 十、人际与家庭指令

| 指令 | 格式 | 说明 |
|-----|------|-----|
| SET_SPOUSE | `SET_SPOUSE:{npc}:{spouse_id或NONE}` | 配偶关系（双向） |
| SET_MASTER | `SET_MASTER:{apprentice}:{master_id或NONE}` | 师徒关系 |
| SET_BOSS | `SET_BOSS:{npc}:{boss_id或NONE}` | 上下级关系 |

### 十一、技能与能力指令

| 指令 | 格式 | 说明 |
|-----|------|-----|
| LEARN_SKILL | `LEARN_SKILL:{npc}:{skill_id}` | 学习技能 |
| FORGET_SKILL | `FORGET_SKILL:{npc}:{skill_id}` | 遗忘技能 |
| SET_COMBAT_STYLE | `SET_COMBAT_STYLE:{npc}:{style}` | 战斗风格 |
| BOOST_STAT | `BOOST_STAT:{npc}:{stat}:{delta}` | 属性提升 |

**常用技能**: `SWORD_BASIC`, `FIST_BASIC`, `BOW_BASIC`, `COOKING`, `MEDICINE`, `STEALTH`, `PERSUASION`, `TRADE`, `FARMING`, `CRAFT`

**战斗风格**: `AGGRESSIVE`, `DEFENSIVE`, `BALANCED`, `CUNNING`, `BERSERKER`

**可提升属性**: `ATK`, `DEF`, `MAX_HP`, `SPEED`, `CRIT`, `DODGE`

### 十二、物品与装备指令

| 指令 | 格式 | 说明 |
|-----|------|-----|
| GIVE_ITEM | `GIVE_ITEM:{npc}:{item}:{qty}` | 给予物品 |
| TAKE_ITEM | `TAKE_ITEM:{npc}:{item}:{qty}` | 收走物品 |
| EQUIP_WEAPON | `EQUIP_WEAPON:{npc}:{weapon或NONE}` | 装备/卸下武器 |

**常用物品**: `GRAIN`, `MONEY`, `MEDICINE`, `SWORD_IRON`, `ARMOR_LEATHER`

**武器类型**: `SWORD_BRONZE`, `SWORD_IRON`, `SWORD_STEEL`, `BOW_BASIC`, `SPEAR_IRON`, `AXE_IRON`

## 复合指令（宏）

常用的指令组合：

```
COMBAT_START = SHAKE_CAMERA:5 + FLASH_WHITE:100
DRAMATIC_ENTRANCE = FADE_FROM_BLACK:500 + NPC_ENTER:{id}
TIME_SKIP = FADE_TO_BLACK:300 + ADVANCE_TIME:{h} + FADE_FROM_BLACK:300
```

## 实现位置

- 指令执行器: `src/story/story_directive_executor.py` ✅ 已实现
- 注册到: `src/quest_system.py` 的 `trigger_action()` 方法 ✅ 已集成

## 集成方式

### QuestManager中的处理优先级

```python
def trigger_action(self, action_name, ctx=None):
    # 1. 支持分号分隔的多条指令
    directives = action_name.split(';')
    for directive in directives:
        self._execute_single_action(directive, ctx)

def _execute_single_action(self, action_str, ctx=None):
    # 优先级1: 本地action_handlers
    if base_action in self.action_handlers:
        handler(ctx, *params)
        return
    
    # 优先级2: StoryDirectiveExecutor
    executor = get_directive_executor()
    executor.bind_context(ctx)
    executor.execute(action_str)
```

### LLM Prompt中的指令说明

`src/llm/event_dialog_generator.py` 的 `expand_to_full_script()` 方法已更新，
包含完整的指令说明供AI生成对话时使用。

## 使用示例

### 在对话中使用（CSV或LLM生成）

```json
{
  "speaker": "NARRATOR",
  "text": "那恶霸猛地一拍桌子，木板应声碎裂。",
  "action": "SHAKE_CAMERA:8;SET_EMOTION:李四:SCARED"
}
```

### 选项后果

```json
{
  "speaker": "PLAYER",
  "text": "光天化日，岂容你如此行凶！",
  "action": "PLAYER_FAME:+10;SET_AFFINITY:鱼西施:+30;NPC_FLEE:恶霸"
}
```

## 人生转折场景示例

### 场景1：平民沦为流民

**背景**：商人被山贼洗劫，家破人亡

```json
{
  "speaker": "NARRATOR",
  "text": "李掌柜跪倒在废墟中，家产尽失，从此流落街头...",
  "action": "SET_JOB:李掌柜:NONE;SET_REFUGEE:李掌柜:1;SET_WEALTH_LEVEL:李掌柜:1;SET_SOCIAL_LEVEL:李掌柜:1;TAKE_ITEM:李掌柜:MONEY:9999"
}
```

### 场景2：流民被招募为门客

**背景**：玩家收留走投无路的流浪汉

```json
{
  "speaker": "NARRATOR",
  "text": "张三感激涕零，愿追随恩公左右。",
  "action": "SET_FOLLOWER:张三:1;SET_REFUGEE:张三:0;SET_AFFINITY:张三:+50;SET_JOB:张三:SERVANT"
}
```

### 场景3：官员落草为寇

**背景**：被诬陷的清官逃入山林

```json
{
  "speaker": "王大人",
  "text": "罢了！既然朝廷负我，我便自立山头！",
  "action": "SET_ORG:王大人:NONE;SET_JOB:王大人:BANDIT;SET_POWER_TYPE:王大人:匪;SET_ORG:王大人:heifeng_zhai;ADD_TAG:王大人:OUTLAW"
}
```

### 场景4：丐帮弟子晋升

**背景**：玩家帮助乞丐立功

```json
{
  "speaker": "NARRATOR",
  "text": "洪七公抚须大笑：\"小子有胆识，升你做四袋弟子！\"",
  "action": "SET_ORG_RANK:阿九:+1;SET_INFLUENCE:阿九:+1;BOOST_STAT:阿九:ATK:+5;LEARN_SKILL:阿九:FIST_BASIC"
}
```

### 场景5：NPC拜师学艺

**背景**：铁匠收徒

```json
{
  "speaker": "铁匠老王",
  "text": "好！从今日起你便是我的徒弟！",
  "action": "SET_MASTER:小李:铁匠老王;SET_JOB:小李:ARTISAN;LEARN_SKILL:小李:CRAFT;SET_AFFINITY:小李:+30"
}
```

### 场景6：两人反目成仇

**背景**：利益冲突导致关系破裂

```json
{
  "speaker": "NARRATOR",
  "text": "二人同时拔刀相向，昔日的兄弟情谊荡然无存。",
  "action": "SET_ENEMY:张三:李四;SET_RELATION:张三:李四:-100;SHAKE_CAMERA:5"
}
```

### 场景7：成为组织首领

**背景**：旧首领被击败，新首领上位

```json
{
  "speaker": "众人",
  "text": "参见新帮主！",
  "action": "SET_ORG_ROLE:玩家:LEADER;SET_ORG_RANK:玩家:5;SET_INFLUENCE:玩家:+2;PLAYER_FAME:+50"
}
```

## 游戏循环集成

### 数据流

```
┌─────────────────────────────────────────────────────────────┐
│                       游戏循环                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│   │  主线任务   │     │  动态事件   │     │  LLM对话    │  │
│   │ (CSV静态)  │     │ (随机触发)  │     │ (AI生成)    │  │
│   └──────┬──────┘     └──────┬──────┘     └──────┬──────┘  │
│          │                   │                   │          │
│          ▼                   ▼                   ▼          │
│   ┌───────────────────────────────────────────────────────┐│
│   │              StoryDirectiveExecutor                   ││
│   │   (统一解析所有 SET_XXX / NPC_XXX / PLAYER_XXX 指令)  ││
│   └────────────────────────┬──────────────────────────────┘│
│                            │                                │
│          ┌─────────────────┼─────────────────┐             │
│          ▼                 ▼                 ▼             │
│   ┌────────────┐   ┌────────────┐   ┌────────────┐        │
│   │  NPC实体   │   │  组织系统   │   │  玩家状态  │        │
│   │ (属性变更) │   │ (缓存刷新) │   │ (资源变化) │        │
│   └────────────┘   └────────────┘   └────────────┘        │
│          │                 │                 │             │
│          └─────────────────┴─────────────────┘             │
│                            │                                │
│                            ▼                                │
│                  ┌────────────────┐                        │
│                  │   FloatingText  │                        │
│                  │   (UI反馈)      │                        │
│                  └────────────────┘                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 关键路径

1. **静态任务路径**: `story_ui.py` → `quest_manager.trigger_action()` → `StoryDirectiveExecutor`
2. **动态事件路径**: `event_system.resolve_event()` → `_resolve_role_names()` → `StoryDirectiveExecutor`
3. **LLM生成路径**: `event_dialog_generator.py` → 生成带action的对话 → `story_ui.py` → `StoryDirectiveExecutor`
