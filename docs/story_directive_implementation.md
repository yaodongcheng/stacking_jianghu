# StoryDirective 剧情指令系统 - 实现总结

## 已完成的工作

### 1. 创建 StoryDirectiveExecutor (`src/story/story_directive_executor.py`)

统一的剧情指令执行器，支持以下指令类型：

#### NPC属性指令
- `SET_AFFINITY:{npc}:{delta}` - 修改好感度
- `SET_HP:{npc}:{value}` - 设置生命值
- `SET_HUNGER:{npc}:{value}` - 设置饥饿值
- `SET_MONEY:{npc}:{delta}` - 修改金钱
- `SET_EMOTION:{npc}:{emotion}` - 设置表情

#### NPC行为指令
- `NPC_MOVE:{npc}:{x}:{y}` - 移动NPC
- `NPC_FOLLOW:{npc}:{target}` - 跟随目标
- `NPC_ATTACK:{npc}:{target}` - 攻击目标
- `NPC_FLEE:{npc}` - NPC逃跑
- `NPC_SAY:{npc}:{text}` - NPC说话气泡

#### 世界状态指令
- `SPAWN_NPC:{template}:{x}:{y}` - 生成NPC
- `DESPAWN_NPC:{npc}` - 移除NPC
- `ADVANCE_TIME:{hours}` - 时间推进

#### 演出效果指令
- `FADE_TO_BLACK:{ms}` - 黑屏渐入
- `FADE_FROM_BLACK:{ms}` - 黑屏渐出
- `FLASH_WHITE:{ms}` - 白屏闪烁
- `SHAKE_CAMERA:{intensity}` - 镜头震动

#### 玩家指令
- `PLAYER_HP:{delta}` - 玩家生命变化
- `PLAYER_MONEY:{delta}` - 玩家金钱变化
- `PLAYER_FAME:{delta}` - 玩家声望变化
- `PLAYER_KNOCKOUT` - 玩家昏倒

#### 关系指令
- `SET_RELATION:{a}:{b}:{delta}` - NPC间好感度

### 2. 集成到 QuestManager (`src/quest_system.py`)

修改了 `trigger_action()` 方法：
- 支持分号分隔的多条指令
- 优先使用本地 action_handlers
- 未知指令自动委托给 StoryDirectiveExecutor

### 3. 更新 LLM Prompt (`src/llm/event_dialog_generator.py`)

在 `expand_to_full_script()` 方法中添加了完整的指令说明：
- 演出效果指令
- NPC状态指令
- NPC行为指令
- 玩家状态指令
- 示例组合

## 使用示例

### 在LLM生成的对话中
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

## 文件清单

- `src/story/__init__.py` - 包初始化
- `src/story/story_directive_executor.py` - 指令执行器
- `docs/story_directive_spec.md` - 设计文档

## 核心设计原则

1. **言行一致**：对话中提到的效果必须有对应的机械实现
2. **环境同步**：剧情演出需配套环境设置
3. **指令复用**：基于已有的原子行为和action_handlers构建
4. **向后兼容**：不影响现有的action_handlers逻辑
