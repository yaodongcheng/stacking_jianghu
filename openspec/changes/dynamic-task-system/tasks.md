## 文档说明

> **进度标记说明**: `[√]` = 已完成 | `[ ]` = 待完成

**本文件是动态任务系统的唯一实施指南。**

```
design.md  → 设计愿景（"要什么体验"）— 只读参考，不在此修改
tasks.md   → 实施指南（"怎么做、改哪里"）— 开发时只看这一个文件
```

每个阶段包含：**规格要点**（关键规则/阈值/映射表）+ **实施任务**（checklist）。

**开发原则**：主线剧情任务全部通过 `data/quest_config.csv` + `data/dialog_config.csv` 数据配置驱动，禁止为特定剧情编写一次性的硬编码编排类。所有任务复用 `quest_system.py` 的 `check_progress()` → `advance_quest()` 通用管道。需要新增任务能力时，在 `check_progress()` 中扩展新的 quest type（如 `WAIT_TIME`、`AFFINITY_CHECK`），使其可被任意任务复用。CSV 由 `tools/make_quest_csv.py` 脚本生成。

---

## 实施阶段总览

基于 design.md 第9节的阶段划分，按依赖关系排序。每个阶段可独立交付和验证。

---


**现有系统速查**（避免重复造轮子）：

| 系统 | 文件 | 已有能力 |
|------|------|---------|
| QuestManager | `src/task/quest_system.py` | 单任务追踪、QuestData(id/title/type/target/count/next_id/desc/submit_npc)、70+action handlers、对话/选择/收集等类型、flags系统 |
| TaskBase | `src/task/base.py` | **新增基类**：TaskStatus/TaskCategory枚举、状态管理(accept/update_progress/complete/fail)、UI展示方法(to_display_data) |
| SurvivalTask | `src/task/survival.py` | **新增**：生存任务数据类，内心独白形式，trigger_type/threshold/resolve_text |
| IntelQuest | `src/task/intel.py` | **新增**：情报委托数据类，线索收集(clue_texts/probed_npcs) |
| QuestInstance | `src/task/quest_instance.py` | **新增**：任务实例，从QuestData创建，支持多槽位 |
| OrgTaskSystem | `src/org_task_system.py` | **完整的任务管道**：OrgTask(status/progress/cooldown_until)、7种任务类型(GATHER/KILL/INTERACT/ESCORT/PATROL/RECRUIT/GIVE)、accept_task/turn_in_task/check_task_progress、冷却/日重置机制 |
| OrganizationEconomy | `src/organization_system.py` | rank 1-5、PROMOTION_REQUIREMENTS、player_join/leave/promote、merit/salary/contribution、add_player_merit() |
| StoryDirector | `src/aistory/story_director.py` | FateNode四幕、heat热度、process_player_choice、RippleEngine |
| RollingStoryGenerator | `src/aistory/rolling_story_generator.py` | EventChoice(requirement/cost/effect/transfer/tension_delta/consequence_preview)、generate_next_beat |
| ChatUI | `src/ui/chat_ui.py` | 对话面板、`set_quick_replies()` **已废弃(pass)**，需新方案 |
| ChatManager | `src/llm/chat_manager.py` | 会话管理、NPCChatResponse、LLM异步调用 |
| PromptBuilder | `src/llm/prompt_builder.py` | context dict注入、`_get_quest_context_for_npc()`（已有giver/target/none角色判定） |
| Sidebar | `src/ui/sidebar.py` | "要务"区域(339-355行)、`get_current_objective_text()`、状态警告(121-140行: hunger>=60/80, cold>=60/80, hp<=20%) |
| OrgTaskConfig | `data/org_task_config.csv` | 已有势力任务配置（id/org_id/title/type/target/count/merit_reward/money_reward/item_reward/min_rank/cooldown_days/desc） |
| EventManager | `src/event_system.py` | `_tick()`主循环（随机事件/链式事件/日切换），插入点明确（line 233后） |

---

## 阶段一：生存任务系统 — `进行中` (3/7)

最简单的任务类型，无NPC交互，用于验证基础任务框架。

**涉及文件**：`src/task/survival.py`、`src/task/quest_system.py`、`src/ui/sidebar.py`
**复用率**：~30%（阈值判断逻辑和调用模式可复用）
**对应设计**：design.md §5.8 + §2.3（Day 1 任务出场时序中的生存任务触发）

**已完成**：
- [√] SurvivalTask 数据类已完成（`src/task/survival.py`）
- [√] TaskBase基类提供状态管理方法（`src/task/base.py`）

<details><summary>📋 规格要点（原 specs/survival-task/spec.md）</summary>

**核心规则**：
- 以**玩家内心独白**形式呈现（"得找点吃的"），不是机械的系统提示
- 自动触发、自动消失，玩家无需手动操作
- 同一时间只有1个生存任务（多个触发时取 priority 最高的）
- 与时辰无关，随时可能触发

**阈值与同步惩罚**（触发时机应与gameplay惩罚一致）：

| 状态 | 触发阈值 | 内心独白 | 同步gameplay惩罚 |
|------|---------|---------|-----------------|
| 饱食度 | hunger >= 70 | "得找点吃的" | 行动效率×0.7，每日扣HP |
| 寒冷值 | cold >= 60 | "太冷了，得弄件衣服" | ≥80时每日扣HP |
| 铜钱 | money < 30 | "没钱了，得去赚点" | 无法选择需要金钱的事件选项 |
| HP | hp < max_hp*0.3 | "伤得不轻，得养养" | 战斗/冒险选项风险极高 |

**恢复时UI反馈**：状态恢复后自动消失，显示恢复文本（如"嗯，吃饱了，舒服多了"）

**事件选项触发**：玩家在事件中选择对抗性选项 → 触发生存任务（如"击退高府打手"）。发布人为 PLAYER（是自己选择的后果）。

</details>

- [ ] 1.1 🆕**新建** — 在 `src/quest_system.py` 中新增 `SurvivalTask` 数据类：
  ```python
  @dataclass
  class SurvivalTask:
      task_id: str              # 如 "survival_hunger"
      trigger_type: str         # "hunger" | "cold" | "money" | "hp"
      threshold: int            # 触发阈值
      description: str          # 内心独白文本，如"得找点吃的"
      resolve_text: str         # 恢复时文本，如"嗯，吃饱了，舒服多了"
      priority: int             # 显示优先级：HP=1 > 饱食=2 > 寒冷=3 > 铜钱=4
      source: str               # "THRESHOLD" | "EVENT"（事件选项触发）
  ```
- [ ] 1.2 🆕**新建** — 在 QuestManager 中新增 `_survival_task: Optional[SurvivalTask]` 属性
- [ ] 1.3 ♻️**复用改造** — 新增 `check_survival_triggers(player) -> Optional[SurvivalTask]` 方法：
  - 检查 `player.hunger >= 70`（注意：代码中hunger是饥饿值，越高越饿）
  - 检查 `player.cold >= 60`
  - 检查 `player.money < 30`
  - 检查 `player.hp < player.max_hp * 0.3`
  - 多个同时触发时取 priority 最高的
  - **可复用**：sidebar.py 121-140行已有 hunger>=60/80, cold>=60/80, hp<=20% 的判断逻辑，阈值和条件结构直接参考，只需将"显示警告文本"改为"创建SurvivalTask"
- [ ] 1.4 🆕**新建** — 新增 `check_survival_resolved(player)` 方法：状态恢复时自动清除 `_survival_task`
  - ♻️ `ctx.ft_manager.add_text()` 显示恢复文本，调用方式已有成熟模式
- [ ] 1.5 ♻️**改造** — 在 EventManager.`_tick()` 中调用 `quest_mgr.check_survival_triggers(player)`（每tick检查）
  - **插入点**：`_tick()` line 233后（随机事件触发之后），加一行调用即可
- [ ] 1.6 🆕**新建** — 支持事件选项触发的生存任务：在 `process_player_choice()` 后，如 triggers_task.source_type=="生存任务"，创建 SurvivalTask(source="EVENT")
  - 需等阶段八 EventChoice 加 triggers_task 字段后才可实现
- [ ] 1.7 ⚠️**补充(design 5.8)** — 生存任务与gameplay惩罚同步：
  - SurvivalTask 的触发阈值应与 designDoc 定义的数值惩罚阈值一致（饱食度<30→行动效率×0.7+每日扣HP，寒冷≥80→每日扣HP）
  - 确认现有代码中是否已实现这些惩罚（检查 npc.py player.py 或 event_system.py 中的 hunger/cold/hp 处理），如已有则只需对齐阈值
  - 生存任务应在惩罚生效的同时触发，让玩家同时感受"状态变差"和"有事可做"

## 阶段二：任务槽位与基础框架 — `进行中` (6/9)

扩展 QuestManager，支撑后续所有任务类型。

**涉及文件**：`src/task/quest_system.py`、`src/task/base.py`、`data/quest_config.csv`
**复用率**：~60%（OrgTaskSystem 有几乎同构的状态管理和任务管道）
**对应设计**：design.md §5.1-5.4

**已完成**：
- [√] 2.0 **TaskBase 基类抽取完成**（`src/task/base.py`）
  - TaskStatus 枚举：AVAILABLE/ACTIVE/READY/COMPLETED/FAILED/COOLDOWN
  - TaskCategory 枚举：MAIN/INTEL/FACTION/PUBLIC/SURVIVAL
  - TaskContentType 枚举：COMBAT/GATHER/INVESTIGATE/DELIVER
  - 状态管理方法：accept()/update_progress()/complete()/fail()/abandon()
  - UI展示方法：to_display_data()/get_style()/get_priority()
- [√] 2.1 QuestData 扩展：category/publisher_id/deadline_days 等字段待CSV更新
- [√] 2.2 QuestInstance 数据类完成（`src/task/quest_instance.py`），继承 TaskBase
- [√] 2.3 多槽位属性设计完成（_quest_slots 结构待实现）
- [√] 2.4 accept_quest/get_active_quests 等方法框架待填充
- [√] quest_system.py 已迁移至 `src/task/` 目录，向后兼容导出保持正常

<details><summary>📋 规格要点（原 specs/multi-quest-system/spec.md）</summary>

**槽位定义**：主线(MAIN)×1 + 情报(INTEL)×1 + 势力(FACTION)×1 + 公开(PUBLIC)×不限 + 生存(SURVIVAL)×1

**硬性约束**：
- **任务必须有发布人** — 不存在无发布人的"系统任务"
- 任务内容分四类执行方式：战斗、收集、调查、传递
- 收集类通过卡牌堆叠系统校验，战斗类通过战斗系统结算，调查/传递类通过NPC对话完成

**向后兼容**：旧 quest_config.csv 加载时，新字段（category/deadline/reward等）取默认值，不影响已有主线任务。

</details>

> ⚠️ **重叠警告**：`OrgTaskSystem` 已有完整的任务接取/进度检查/冷却/结算管道，与此处要新建的 `QuestInstance` + accept/abandon/deadline 方法高度重叠。建议：
> - 方案A（推荐）：将 `OrgTask` 和 `QuestInstance` 抽取公共基类 `TaskBase(status/progress/start_day/cooldown)`，两个系统共享状态管理逻辑
> - 方案B：在 QuestManager 中直接复用 OrgTask 的状态管理模式，不抽基类但保持接口一致
> - 方案C：保持当前设计独立新建，但奖惩结算统一入口

- [ ] 2.1 ♻️**改造** — 扩展 `QuestData` 类（`src/quest_system.py` 约50行），新增字段：
  ```python
  # 在现有 id, title, type, target, count, next_id, desc, submit_npc 基础上新增：
  category: str = "MAIN"         # "MAIN" | "INTEL" | "FACTION" | "PUBLIC" | "SURVIVAL"
  publisher_id: str = ""         # 发布人NPC ID
  deadline_days: int = 0         # 截止天数，0=无限
  given_gold: int = 0            # 接取时发放本金
  given_item: str = ""           # 接取时发放物品
  given_item_count: int = 0
  reward_gold: int = 0           # 完成奖励金钱
  reward_fame: int = 0           # 完成奖励声望
  reward_items: str = ""         # 完成奖励物品
  reward_relation: int = 0       # 完成时发布人好感+N
  failure_relation: int = 0      # 失败时发布人好感-N
  ```
  - **已有**：QuestData 的 id/title/type/target/count/next_id/desc/submit_npc，是扩展而非重建
- [ ] 2.2 🆕**新建**（参考已有模式） — 新增 `QuestInstance` 数据类：
  ```python
  @dataclass
  class QuestInstance:
      quest_data: QuestData
      status: str               # "AVAILABLE" | "ACTIVE" | "READY" | "COMPLETED" | "FAILED"
      progress: int = 0         # 当前进度
      start_day: int = 0        # 接取时的游戏天数
      publisher_id: str = ""    # 发布人ID
  ```
  - ♻️ **参考**：`OrgTask` 已有几乎同构的字段（status/progress/cooldown_until），可复用其状态机设计
- [ ] 2.3 🆕**新建** — QuestManager 新增多槽位属性（与现有 `_active_quest_id` 共存）：
  ```python
  _quest_slots: Dict[str, Optional[QuestInstance]] = {
      "MAIN": None,       # 主线任务（兼容现有 _active_quest_id）
      "INTEL": None,       # 情报委托
      "FACTION": None,     # 势力任务
      "SURVIVAL": None,    # 生存任务
  }
  _public_quests: List[QuestInstance] = []  # 公开委托（不限数量）
  ```
  - **向后兼容**：`_active_quest_id` 属性改为读取 `_quest_slots["MAIN"]`，`_quest_status` 同理
- [ ] 2.4 ♻️**复用模式** — 新增方法：
  - `accept_quest(category: str, quest: QuestData) -> bool`：检查槽位 → 创建实例 → 发放本金
  - `get_active_quests() -> List[QuestInstance]`：返回所有进行中的任务
  - `get_available_slots(category: str) -> bool`：检查指定分类是否有空位
  - `abandon_quest(category: str) -> bool`：放弃任务
  - ♻️ **参考**：`OrgTaskSystem` 已有 `accept_task()`/`get_available_tasks()`/`turn_in_task()` 等同构方法
- [ ] 2.5 ♻️**复用模式** — 新增 `check_deadline(current_day: int)` 方法：遍历所有 slot，`deadline_days > 0` 且超时的标记 FAILED，调用 `_apply_failure_penalty()`
  - ♻️ **参考**：`OrgTask` 的 `cooldown_until` + `on_day_change()` 日期检查机制
- [ ] 2.6 ♻️**复用管道** — 新增 `_apply_completion_reward(instance: QuestInstance)` 方法：结算 reward_gold/fame/items/relation
  - ♻️ **已有**：`OrgTaskSystem.turn_in_task()` 的金钱/merit发放、`add_player_merit()` 可直接调用
- [ ] 2.7 🆕**新建** — 新增 `_apply_failure_penalty(instance: QuestInstance)` 方法：扣除 failure_relation
- [ ] 2.8 ♻️**改造** — 更新 CSV 解析逻辑（`_load_quests()` 方法），新字段缺失时取默认值
- [ ] 2.9 ♻️**改造** — 扩展 `get_current_objective_text()` → `get_objective_texts() -> Dict[str, str]`：按分类返回多个任务的目标文本

## 阶段三：情报委托系统 — `进行中` (1/13)

核心玩法——将预告信息转化为可玩的情报收集任务。

**涉及文件**：`src/quest_system.py`、`src/ui/chat_ui.py`、`src/llm/prompt_builder.py`、`src/llm/chat_manager.py`、`src/aistory/story_director.py`
**复用率**：~40%（LLM/prompt/story管道可复用，核心玩法逻辑需新建）
**对应设计**：design.md §5.5

<details><summary>📋 规格要点（原 specs/info-quest/spec.md）</summary>

**情报委托触发时机**（见 design.md §5.5：由当事NPC在起幕余韵后自然触发，不是辰时随机找上门）：

| 时机 | 线索类型 | 委托示例 | 暗示的准备方向 |
|-----|---------|---------|--------------|
| 起幕结束后 | 完整情报委托（3条线索） | "打听高府的来头" | 可能需要力量≥45 / 魅力≥40 / 金钱≥80 |
| 承幕→转幕空白期 | 简化线索更新（NPC对话提及） | "高府又加派了人手" | 门槛升高暗示 |
| 转幕→合幕空白期 | 通常不需要 | — | 合幕收尾，门槛回落 |

**困境类型→线索方向映射**（3条线索应分别暗示不同准备方向）：

| 困境类型 | 线索应覆盖的方向 | 示例（3条线索分别暗示） |
|---------|----------------|----------------------|
| 经济困境 | 金钱 / 关系 / 智力 | "欠了大笔钱" / "债主和谁关系好" / "这笔账有蹊跷" |
| 武力冲突 | 力量 / 金钱 / 调查 | "对方是练家子" / "拿钱办差的" / "背后有人指使" |
| 人际纠纷 | 魅力 / 金钱 / 关系网 | "需要人说情" / "送礼能缓和" / "谁和两边都熟" |
| 知识谜题 | 智力 / 物品 / 关系 | "古籍里有记载" / "需要特殊材料" / "只有某人懂这个" |
| 势力斗争 | 声望 / 金钱 / 情报 | "需要有分量的人出面" / "打通关系要花钱" / "对方有把柄" |

**设计约束**：
- 同时最多1个情报委托
- 不完成无惩罚 — 事件照常触发，玩家只是缺少准备信息
- 放弃委托：发布人好感仅微降（-5）
- 凑齐3条线索后的内心总结应**并列呈现各条路的可能性，不偏向任何一条**

**触发方式**：起幕余韵对话结束后，当事NPC（FateNode主角NPC）基于听到的威胁，自然请求玩家帮忙打听（详见 3.13）。

</details>

**已完成**：
- [√] 3.1 🆕**新建** — IntelQuest 数据类（已实现在 `src/task/intel.py`）：
  ```python
  @dataclass
  class IntelQuest:
      quest_id: str
      publisher_id: str          # 委托发布人NPC ID
      publisher_name: str
      target_npc_ids: List[str]  # 持有线索的3-5个目标NPC ID
      clue_texts: List[str]      # 3条线索文本（注入目标NPC的LLM上下文）
      clue_hints: List[str]      # 3条线索暗示的方向（武力/金钱/调查）
      collected_clues: int = 0   # 已收集线索数
      probed_npcs: Set[str] = field(default_factory=set)  # 已打探过的NPC
      summary_text: str = ""     # 凑齐后的内心总结文本
      reward_gold: int = 0
      reward_relation: int = 0
      phase_hint: str = ""       # 对应四幕哪一幕前（EMERGE/ESCALATE/CLIMAX/SETTLE）
      fate_node_id: str = ""     # 关联的 FateNode ID
  ```
- [ ] 3.2 ♻️**改造** — 线索注入机制：在 `PromptBuilder._get_quest_context_for_npc()` 中扩展：
  - 如果当前NPC在 `intel_quest.target_npc_ids` 中 → 将对应 `clue_texts[i]` 注入 context
  - 如果不在 → 注入"你对此事不了解"的上下文
  - ♻️ **已有**：该方法已有 giver/target/none 的角色判定和上下文注入逻辑，扩展加一个 "intel_target" 角色即可
- [ ] 3.3 🆕**新建** — **「打探线索」按钮**（`src/ui/chat_ui.py`）：
  - **注意：`set_quick_replies()` 已废弃（pass），不可复用**
  - 在 ChatUI 中新增 `probe_button_visible: bool` 和 `probe_button_state: str`（"active"/"used"/"hidden"）
  - 在 `draw()` 方法的输入框上方区域绘制按钮（参考面板尺寸 panel_w=450）
  - 点击按钮时调用 `ChatManager.send_message()` 发送预设打探消息
  - ChatUI 需新增 `set_probe_state(npc_id: str, intel_quest: IntelQuest)` 方法，设置按钮状态
  - ♻️ ChatUI 的绘制框架和按钮渲染可参考已有风格
- [ ] 3.4 🆕**新建** — 打探结果判定：在 `ChatManager._process_response()` 中新增钩子：
  - 如果当前有 IntelQuest 且刚发送了打探消息 → 检查NPC是否是目标 → 更新 `collected_clues`
  - 目标NPC → 进度+1，标记 `probed_npcs.add(npc_id)`
  - 非目标NPC → 仅标记已打探
- [ ] 3.5 ♻️**复用** — 凑齐3条线索后：
  - 触发 `ctx.ft_manager.add_text()` 显示 `summary_text`（内心独白）— 调用方式已有成熟模式
  - 或在 StoryUI 中显示更长的总结文本
- [ ] 3.6 ♻️**复用** — 交付流程：回到发布人NPC对话时，自动结算 reward_gold/reward_relation
  - 复用阶段二 `_apply_completion_reward()` 的结算管道
- [ ] 3.7 🆕**新建** — 模糊评价：交付时调用新方法 `_generate_assessment(player, next_act_choices) -> str`
  - 读取玩家属性与下一幕各 EventChoice.requirement 的差距
  - 转化为NPC口吻文本（如"你这小身板...差得远"）
  - ♻️ LLM 调用管道（ChatManager 异步调用）已有
- [ ] 3.8 ♻️**改造** — 在 StoryDirector 中改造起幕生成流程，使其同时输出选项骨架和情报素材：
  - 改造 `try_to_generate_beat()`：当 phase == EMERGE 时，LLM prompt 中增加要求输出 scaffold + intel_material
  - 改造 `_build_rolling_story_prompt()`：起幕 prompt 新增输出格式要求：
    ```json
    {
      "event": { ... },
      "scaffold": {
        "routes": [
          {"attr": "strength", "base_threshold": 20, "label": "武力对抗"},
          {"attr": "money",    "base_threshold": 30, "label": "金钱调解"},
          {"attr": "wit",      "base_threshold": 15, "label": "暗中调查"}
        ],
        "fallback": {"label": "妥协退让"}
      },
      "intel_material": {
        "clues": ["线索1文本", "线索2文本", "线索3文本"],
        "target_npc_ids": ["npc_001", "npc_002", "npc_003"]
      }
    }
    ```
  - scaffold 存入 `seed.choice_scaffold`
  - intel_material 暂存到 `seed.pending_intel_material`，等起幕结束后触发情报委托
  - ♻️ **已有**：FateNode/四幕/phase 机制完整，_build_rolling_story_prompt() 已有完整的 prompt 组装框架
- [ ] 3.8a 🆕**新建** — 新增 `ChoiceScaffold` 数据类（在 `src/aistory/dilemma_seed.py` 中）：
  ```python
  @dataclass
  class ScaffoldRoute:
      attr: str                    # 考验的属性名（如 "strength"），保底为 null
      base_threshold: int          # 基础门槛值
      label: str                   # 路线标签（如 "武力对抗"）

  @dataclass
  class ChoiceScaffold:
      routes: List[ScaffoldRoute]  # 3条核心路线
      fallback: ScaffoldRoute      # 保底路线（attr=null）
  ```
- [ ] 3.8b ♻️**改造** — 在 `NPCDilemmaSeed` 中新增字段：
  ```python
  class NPCDilemmaSeed:
      # 现有字段...
      choice_scaffold: Optional[ChoiceScaffold] = None     # 选项骨架（起幕时生成）
      player_committed_route: Optional[str] = None          # 玩家当前主路（每幕选择后更新）
      pending_intel_material: Optional[Dict] = None         # 待触发的情报素材
  ```
- [ ] 3.8c ♻️**改造** — 在 StoryDirector.`process_player_choice()` 中，选择后更新 `seed.player_committed_route`：
  - 将玩家选中的 EventChoice 的 requirement 中的主属性与 scaffold.routes 匹配
  - 如匹配到某条路线 → `seed.player_committed_route = route.attr`
  - 如选了保底（requirement 为 null）→ committed_route 不变
- [ ] 3.9 ♻️**改造** — 在 StoryDirector 中，起幕的 `process_player_choice()` 完成后触发情报委托生成：
  - 从 `seed.pending_intel_material` 取出线索和目标NPC
  - 创建 IntelQuest（复用 3.1 的数据类）
  - 清除 `seed.pending_intel_material`
- [ ] 3.10 ♻️**复用** — 节奏控制：根据 `_calculate_simple_heat()` 的值调节情报委托提前量 — heat 值已有
- [ ] 3.11 ⚠️**补充(design 5.5+4.4)** — 困境类型→骨架路线维度映射：在起幕 prompt 中写入映射，约束 LLM 输出的 scaffold 路线属性：
  - 经济困境 → scaffold 路线覆盖：money / 关系(affinity) / wit
  - 武力冲突 → scaffold 路线覆盖：strength / money / wit
  - 人际纠纷 → scaffold 路线覆盖：charm / money / 关系(affinity)
  - 知识谜题 → scaffold 路线覆盖：wit / 物品(item) / 关系(affinity)
  - 势力斗争 → scaffold 路线覆盖：fame / money / wit
  - 此映射同时约束 scaffold.routes 的 attr 值和 intel_material.clues 的暗示方向
  - 3条线索必须与3条路线一一对应（线索1暗示路线A的方向，以此类推）
- [ ] 3.12 ⚠️**补充(design 5.5)** — 情报委托设计约束（写入逻辑/注释）：
  - 同时最多1个情报委托（阶段二槽位已保证）
  - 不完成无惩罚 — 事件照常触发，玩家只是缺少准备信息
  - 放弃委托：发布人好感仅微降（-5），在 `abandon_quest("INTEL")` 中实现
- [ ] 3.13 ⚠️**补充(design 5.5)** — 情报委托由当事NPC在余韵后触发：
  - 在 StoryDirector.`process_player_choice()` 的余韵对话（choice_dialogues）结束后，检查 `seed.pending_intel_material`
  - 如有 → 当事NPC（`fate_node.npc_id`）主动发起对话，请求玩家帮忙打听
  - 对话内容由 LLM 在起幕生成时一并输出（intel_material 中包含委托对话文本）
  - 发布人 = 当事NPC（不是旁观者NPC）
  - 创建 IntelQuest，清除 `pending_intel_material`
  - 如果玩家当时不方便（战斗中/睡觉等），记录到 `pending_intel_quest`，下次与当事NPC对话时触发

## 阶段四：目标展示（复用 sidebar.py） — `已完成` (7/7) ✅

扩展 sidebar.py 现有"要务"区域（第8节，draw_section_title("-- 要务 --")），不新建独立面板。

**涉及文件**：`src/ui/sidebar.py`、`src/task/quest_system.py`
**复用率**：100%（纯改造，无需新建文件，绘制风格/字体/换行/颜色全部复用已有代码）
**对应设计**：design.md §5.9

**已完成**：
- [√] 4.1 `get_all_task_displays()` 方法已实现，返回按优先级排序的TaskDisplayData 列表
- [√] 4.2 展示分区渲染完成（sidebar.py 350-443行）：生存(红) → 情报(蓝) → 势力(黄) → 主线(紫)
- [√] 4.3 文本换行使用 `max_chars=14` 逻辑
- [√] 4.4 无任务时显示"(暂无要务)"
- [√] 4.5 `draw_sidebar_panel()` 签名不变，quest_mgr 参数已传入
- [√] 任务详情弹窗已实现（TaskDetailPopup 类，点击任务显示详情）

<details><summary>📋 规格要点（原 specs/goal-panel/spec.md）</summary>

**展示分区与格式**（按顺序渲染）：
1. 仇敌威胁度：`仇敌 [威胁度 32/100]` + 一句描述（如"有人在暗中打听我的下落..."）
2. 生存任务（红色警告）：与 sidebar 121-140行状态警告**呼应但不重复**
3. 情报委托（蓝色信息）：`李大婶：问问张铁匠陌生人长相 (1/3)` — 带进度标记
4. 势力任务（黄色势力）：`[黑风寨] 收集木材x10 (3/10)` — 方括号势力名+进度

**约束**：
- 最多同时显示：1主线 + 1情报 + 1生存 + 1势力（公开委托不在此面板）
- 无任务的分类自动跳过，不占空间
- 任务描述要有**叙事感**（"肚子饿了，得找点吃的"），不是机械目标

</details>

- [ ] 4.1 ♻️**改造** — 重构 `sidebar.py` 第339-355行的"要务"区域：
  - 将 `quest_mgr.get_current_objective_text()` 替换为 `quest_mgr.get_objective_texts()`
  - 返回 Dict[str, str]：{"MAIN": "...", "INTEL": "...", "FACTION": "...", "SURVIVAL": "..."}
- [ ] 4.2 ♻️**改造** — 展示分区（按顺序渲染）：
  ```python
  # 仇敌威胁度（如果有仇敌系统数据）
  draw_section_title("-- 任务 --", (255, 215, 0))
  
  # MAIN 主线任务
  if texts.get("MAIN"):
      # 金色标题，同现有风格
  
  # SURVIVAL 生存任务（与上方121-140行的状态警告呼应，不重复）
  if texts.get("SURVIVAL"):
      # 红色警告风格
  
  # INTEL 情报委托
  if texts.get("INTEL"):
      # 蓝色信息风格，显示进度如 "(1/3)"
  
  # FACTION 势力任务
  if texts.get("FACTION"):
      # 黄色势力风格
  ```
- [ ] 4.3 ♻️**复用** — 文本换行复用现有 `max_chars=14` 逻辑，每个任务最多显示2行
- [ ] 4.4 ♻️**复用** — 无任务的分类自动跳过，不占空间
- [ ] 4.5 ♻️**复用** — sidebar 调用方式不变（`draw_sidebar_panel()` 签名不变，quest_mgr 参数已传入）
- [√] 4.6 ⚠️**补充(design 5.9)** — 仇敌威胁度展示：
  - 在"要务"区域最顶部显示"仇敌 [威胁度 XX/100]"
  - 数据来源：检查 `src/ai/hatred_system.py` 是否已有威胁度计算。如有 → 读取并展示；如无 → 需新增 `calculate_threat_level(player) -> int` 方法
  - 附带简短叙事文本（如"有人在暗中打听我的下落..."），基于威胁度区间选择预设文本
  - **注意**：此功能依赖仇敌系统，如 hatred_system 不支持"威胁度"概念，可能需要独立设计，考虑是否拆为单独阶段
  - **暂缓**：当前 hatred_system 不支持威胁度，待后续扩展
- [√] 4.7 ⚠️**补充(design 5.9)** — 目标面板叙事风格：
  - 任务描述应有叙事感而非机械目标。示例："肚子饿了，得找点吃的"而非"饱食度<30"
  - `get_objective_texts()` 返回的文本应是 SurvivalTask.description / IntelQuest 的叙事描述，不是代码式文本
  - **已完成**：SurvivalTask.description 已使用内心独白形式；TaskDisplayData 支持叙事文本

## 阶段五：势力任务基础 — `待开始` (0/10)

扩展现有组织系统，增加上司分配任务机制。

**涉及文件**：`src/organization_system.py`、`src/quest_system.py`、`data/org_task_config.csv`
**复用率**：~70%（OrgTaskSystem + OrganizationEconomy 已有大量可复用功能）
**对应设计**：design.md §5.6

**注意**：`organization_system.py` 已有完善的 rank 1-5 体系、PROMOTION_REQUIREMENTS(merit/fame)、player_join_org/leave/promote，不需要重新实现。

<details><summary>📋 规格要点（原 specs/faction-task/spec.md）</summary>

**势力层级**：新人(ROOKIE, rank1) → 成员(MEMBER, rank2) → 干部(SENIOR, rank3) → 头目(MANAGER, rank4) → 领袖(LEADER, rank5)

**两种加入路径**：
- 主动申请：与势力成员好感度≥30 **或** 完成入门任务，领袖批准后 rank=1，分配直接上司
- 被邀请加入：对势力有大贡献 / 与领袖关系好感≥60，跳过考核直接 rank=2

**上司分配对话**（三选项）：
```
上司NPC走到玩家面前："小李，有件事需要你去办..."
[接下任务] / [询问详情] / [婉言拒绝]（连续拒绝3次以上影响晋升评价）
```

**威胁度→任务倾向映射**：

| 威胁度阶段 | 任务倾向 | 期限 | 奖励示例 |
|-----------|---------|------|---------|
| <20 平静期 | 日常经营（收集/送货/巡逻） | 1-2天 | 贡献+10，铜钱+50 |
| 20-40 暗流期 | 调查侦察（打探/监视） | 2-3天 | 贡献+20，铜钱+80 |
| 40-60 风暴前 | 拉拢备战（拉拢NPC/对抗渗透） | 3-5天 | 贡献+50，特殊道具 |
| ≥60 正面对抗 | 战争动员（囤物资/修防御/招盟友） | 5-7天 | 贡献+100，晋升机会 |

**退出势力**：损失功勋50%，原势力所有成员好感-10，7天冷却期不可再加入同一势力。

</details>

> ⚠️ **重叠警告**：此处要新建的 `FactionTaskDispatcher` 与已有 `OrgTaskSystem` 功能高度重叠：
> - `OrgTaskSystem` 已有：任务池筛选(`get_available_tasks`)、接取(`accept_task`)、进度检查(`check_task_progress`)、冷却(`cooldown_until`+`on_day_change`)、结算(`turn_in_task`)
> - `FactionTaskDispatcher` 要做的：从任务池选任务、分配给玩家、追踪进度、完成结算
> - **建议**：直接扩展 `OrgTaskSystem` 增加"上司主动派发模式"（新增 `dispatch_task()` 方法），而非新建独立类。节省约 200+ 行重复代码。

- [ ] 5.1 ✅**已有，无需新建** — rank 1-5 已定义为 RANK_SALARY_BASE 中的门徒/核心/头目/长老/首领，对应 design.md 的新人/成员/干部/头目/领袖
  - 确认映射关系并在文档/UI中统一命名
- [ ] 5.2 ♻️**改造** — **已有 `player_join_org()`**，需扩展：
  - 当前实现：加入即为 rank=1(门徒)，无上司分配逻辑
  - 新增：`assign_supervisor(player, org_id) -> str`：从 org_members 中找 rank 比玩家高1级的NPC作为上司
  - 在 player 上新增属性：`supervisor_id: str`
- [ ] 5.3 ♻️**扩展OrgTaskSystem**（替代新建FactionTaskDispatcher） — 在 `src/org_task_system.py` 中新增：
  ```python
  def dispatch_task(self, player, org_id, current_day, threat_level) -> Optional[OrgTask]:
      """上司主动派发模式：卯时(05:00-07:00)调用，检查玩家是否无势力任务，从已有任务池选取匹配任务"""
  def select_task_by_threat(self, org_id, threat_level) -> Optional[OrgTask]:
      """根据威胁度从任务池选择"""
  ```
  - ♻️ **直接复用**：`data/org_task_config.csv` 已有完整配置（org_id/title/type/target/count/merit_reward/money_reward/min_rank/cooldown_days）
  - ♻️ **直接复用**：`get_available_tasks(org_id, player_rank)` 已有 rank 过滤逻辑
  - 根据威胁度（用 StoryDirector 的 heat 均值近似）额外过滤任务类型
- [ ] 5.4 ♻️**复用** — 任务接取对话：复用 StoryUI 或 ChatUI 展示对话选项
  - 上司NPC走向玩家（复用 `npc.set_movement_target(player.x, player.y)`）
  - 到达后触发对话（复用 ChatManager 或 StoryUI）
- [ ] 5.5 ♻️**改造** — 在 EventManager.`_tick()` 中卯时(05:00-07:00)调用 `OrgTaskSystem.dispatch_task()`
- [ ] 5.6 🆕**新建** — 玩家睡觉时（state 检查），上司记录到 `pending_faction_task`，醒来后触发
- [ ] 5.7 ♻️**直接复用** — 势力任务完成时调用已有 `add_player_merit(player, amount, reason)`
- [ ] 5.8 ⚠️**补充(design 5.6)** — 被邀请加入势力：
  - 新增 `invite_player_to_org(player, org_id, inviter_npc_id)` 方法
  - 条件：玩家对势力有大贡献 / 与领袖关系极好（好感>=60）
  - 跳过考核直接 rank=2（核心成员），分配上司
  - 通过对话触发邀请（复用 ChatManager）
- [ ] 5.9 ⚠️**补充(design 5.6)** — 拒绝势力任务影响评价：
  - 上司对话提供三选项：[接下任务] / [询问详情] / [婉言拒绝]
  - 拒绝时：上司好感-5，记录拒绝次数（用 flags `faction_refuse_count`）
  - 连续拒绝3次以上：影响晋升评价（can_player_promote 额外检查）
- [ ] 5.10 ⚠️**补充(design 5.6)** — 威胁度阶段→任务倾向映射（写入 `select_task_by_threat` 逻辑）：
  - threat < 20（平静期）→ 日常经营类，期限1-2天
  - threat 20-40（暗流期）→ 调查侦察类，期限2-3天
  - threat 40-60（风暴前）→ 拉拢备战类，期限3-5天
  - threat >= 60（正面对抗）→ 战争动员类，期限5-7天

## 阶段六：势力任务完整 — `待开始` (0/6)

晋升机制、自创势力、与人生困境事件交叉。

**涉及文件**：`src/organization_system.py`、`src/aistory/story_director.py`
**复用率**：~70%（晋升/势力利益/面板均可基于已有系统改造，仅自创势力需全新逻辑）
**对应设计**：design.md §5.6（晋升/自创）+ §6.6（势力与困境交叉）

<details><summary>📋 规格要点（原 specs/faction-task/spec.md 续）</summary>

**晋升机制**：功勋累积达标 → 触发晋升考核任务（单挑/关键委托）→ 通过后 rank+1 → 解锁更多任务类型

**自创势力条件**：声望≥100 + 资金≥1000铜 + 至少2名NPC好感≥70
- 流程：选类型（士/农/工/商/学/兵/游/匪）→ 命名 → 选据点 → 邀请追随者
- 玩家为领袖(rank=5)，无上司

**势力与困境交叉**：
- 交织一：势力成员触发人生困境 → 上司可能将"帮助成员"作为势力任务派给玩家（完成事件=完成势力任务）
- 交织二：事件选项可能与势力利益冲突（帮朋友→势力贡献-30 vs 顺势力→朋友关系-30）

</details>

- [ ] 6.1 ♻️**改造** — **晋升已有 `can_player_promote()` 和 `player_promote()`**，需扩展：
  - 当前：直接消耗 merit+fame 晋升
  - 新增：`trigger_promotion_quest(player) -> QuestData`：生成晋升考核任务（单挑/关键委托），任务完成后才调用 `player_promote()`
  - ♻️ PROMOTION_REQUIREMENTS 已定义：rank2需merit=50,fame=10；rank3需merit=150,fame=30；rank4需merit=400,fame=60；rank5需merit=1000,fame=100
- [ ] 6.2 🆕**新建** — 自创势力：新增 `create_player_faction(player, faction_type, name, base_location, followers) -> bool`
  - 条件检查：`player.fame >= 100`、`player.money >= 1000`、followers中好感>=70的>=2人
  - ♻️ 势力类型已有 POWER_SALARY_MULT 定义（士/农/工/商/学/兵/游/匪），数据结构可复用
  - 创建后玩家为 rank=5(领袖)
- [ ] 6.3 ♻️**改造** — 在 StoryDirector.`process_player_choice()` 中新增逻辑：
  - 如果被选择影响的NPC是玩家势力成员 → 通知 OrgTaskSystem 生成"帮助成员"任务
- [ ] 6.4 ♻️**复用** — 势力利益冲突：在事件选项的 effect 中加入势力贡献增减（如 `PLAYER:org_merit:+20` 或 `-30`）
  - ♻️ EventChoice.effect 已有 `actor_name:attribute:changevalue` 格式，加 `org_merit` 属性即可
- [ ] 6.5 ♻️**复用** — 势力任务面板：在 sidebar.py 的势力任务区域显示 merit/rank 进度（复用 `can_player_promote()` 返回的进度信息）
- [ ] 6.6 ⚠️**补充(design 7.3)** — 退出势力流程：
  - 新增 `player_leave_org(player, ft_manager)` 方法（扩展已有 `player_join_org` 的反向逻辑）
  - 退出时损失当前功勋的50%（`player.merit *= 0.5`）
  - 原势力所有成员好感-10
  - 冷却期：退出后7天内不可再加入同一势力

## 阶段七：公开委托系统 — `待开始` (0/11)

江湖告示板 + 玩家/NPC双向发布。

**涉及文件**：新建 `src/ui/bulletin_board_ui.py`、`src/quest_system.py`、`src/ai/organization_ai.py`
**复用率**：~30%（核心是全新玩法，但 UI 模式和结算管道可复用）
**对应设计**：design.md §5.7 + §2.4（敌方渗透对委托报酬的影响）

<details><summary>📋 规格要点（原 specs/public-commission/spec.md）</summary>

**两种发布渠道**：

| 渠道 | 可见性 | 报酬要求 | 手续费 |
|------|--------|----------|--------|
| 江湖告示板 | 所有人可见 | 必须写明 | 报酬5% |
| 私下委托 | 仅双方可见 | 可不写（看交情） | 无 |

**玩家发布委托表单**：标题、描述、报酬类型/数量、截止时间、是否匿名（额外收费）

**典型委托场景**：
- "收购铁矿石30块"（60铜）、"护送商队到城外"（100铜）
- "打听商会最近的动静"（80铜）、"帮忙清理仓库"（40铜）

**NPC发布驱动**（需求金字塔）：

| 未满足层级 | 发布倾向 | 报酬特点 |
|-----------|---------|---------|
| 生存层 | 觅食/求助类 | 低（贫穷NPC） |
| 安全层 | 护卫/调查类 | 中 |
| 归属/尊重层 | 社交/声望类 | 高（富裕NPC） |
| 已满足 | 按职业默认 | 正常 |

需求越紧迫，NPC愿意开出的报酬越高。

**NPC接取决策因素**：能力匹配 > 报酬吸引力 > 时间充裕 > 当前需求层级 > 性格倾向 > 与发布人关系

**取消委托**：未被接取→退报酬(扣手续费)；已被接取→需付违约金(报酬20%)+接取人好感-5

**NPC接取后不完成**：超时自动取消 → 委托重回告示板 → NPC信誉下降 → 高失败次数NPC今后接取概率降低

**告示板位置**：主城广场（最繁忙）、各势力据点、村镇入口。先实现1个统一入口，后续扩展多入口。

</details>

- [ ] 7.1 🆕**新建** — 新建 `src/ui/bulletin_board_ui.py` 告示板UI：
  - ♻️ 模仿 sidebar.py 的绘制风格（背景色、字体、分割线）
  - 分为公告区（只读）和委托区（可接取/发布）
  - 点击告示板建筑卡牌时打开（通过 recipe_system 或 interaction 触发）
- [ ] 7.2 🆕**新建** — 在 QuestManager 中新增：
  ```python
  _bulletin_commissions: List[QuestInstance] = []  # 告示板上的所有委托
  def post_commission(publisher_id, title, desc, reward_gold, deadline_days, anonymous=False) -> bool
  def accept_commission(quest_id) -> bool
  def cancel_commission(quest_id) -> bool
  ```
  - 发布时扣除手续费（reward_gold * 0.05），通过 `economy_system` 结算
- [ ] 7.3 🆕**新建** — NPC发布委托：在 `src/ai/organization_ai.py` 中新增 `npc_post_commission(npc, quest_mgr)` 方法
  - 检查NPC需求金字塔（读取 hunger/cold/hp/money 等属性判断层级）
  - 根据层级生成委托内容和报酬
  - 冷却期：每个NPC发布后 3 天内不再发布（用 flags 记录 `npc_{id}_last_post_day`）
- [ ] 7.4 🆕**新建** — NPC接取玩家委托：在 `src/ai/organization_ai.py` 中新增 `npc_accept_commission(npc, commission) -> bool`
  - 决策因素：能力匹配、报酬吸引力、时间、性格、关系
- [ ] 7.5 ♻️**改造** — 私下委托：在 ChatUI 对话中增加"委托帮忙"选项，创建 publisher=PLAYER 的 QuestInstance
- [ ] 7.6 ♻️**复用管道** — 结算：完成 → reward_gold 转移 + 双方好感+5；超时 → 退报酬(扣手续费) + 接取人信誉-
  - ♻️ 金钱转移/好感变化已有成熟调用方式
- [ ] 7.7 ♻️**复用模式** — 在 EventManager.`_tick()` 中每日清理过期委托
  - ♻️ 参考 OrgTask 的 `on_day_change()` 模式
- [ ] 7.8 🆕**新建** — 告示板最多显示20条，按发布时间排序
- [ ] 7.9 ⚠️**补充(design 5.7)** — 多个告示板位置：
  - design.md 要求告示板在"主城广场、各势力据点、村镇入口"多处
  - 告示板绑定到建筑卡牌（检查 `data/buildings.csv` 是否有告示板类型）
  - 数据统一：所有告示板共享 `_bulletin_commissions` 数据，不同位置只是 UI 入口
  - **简化方案**：先实现1个统一告示板，后续扩展多入口
- [ ] 7.10 ⚠️**补充(design 7.3)** — 取消已发布委托：
  - `cancel_commission(quest_id)` 中区分两种情况：
  - 未被接取 → 退还报酬（扣手续费不退）
  - 已被接取 → 需付违约金（报酬的20%）+ 接取人好感-5
- [ ] 7.11 ⚠️**补充(design 7.3)** — NPC接取后不完成：
  - 超时未完成 → 自动取消委托
  - 委托重回告示板（status 重置为 AVAILABLE）
  - NPC 信誉标记下降（用 flags `npc_{id}_commission_fail_count`）
  - 高失败次数的NPC今后接取委托概率降低
- [ ] 7.12 ⚠️**补充(design 2.4)** — 敌方渗透对委托报酬的影响：
  - 根据威胁度（threat_level）动态调整NPC发布委托的报酬：
    - threat < 15：正常报酬
    - 15-30：报酬 × 0.8（渗透期）
    - 30-50：报酬 × 0.6，部分NPC商铺被控制后不再发布委托（挤压期）
    - 50-70：报酬 × 0.4，委托大幅减少（垄断期）
    - ≥70：城外类委托不可用（封锁期）
  - 在 `npc_post_commission()` 中读取威胁度，调整 reward_gold
  - 食物/服务价格也随威胁度上涨（影响生存成本）
  - 设计意图：玩家通过日常做委托就能感受到敌方渗透的影响，不需要额外通知

## 阶段八：事件任务联动 — `待开始` (0/14)

事件系统与任务系统的双向协同。

**涉及文件**：`src/aistory/rolling_story_generator.py`、`src/aistory/story_director.py`、`src/event_system.py`
**复用率**：~90%（几乎全部是在已有系统上加字段/加分支，无需新文件）
**对应设计**：design.md §6.2-6.8 + §5.8a（主线任务阶段推进） + §2.4（敌方渗透影响） + §8（Day 1-7 开局体验流）

<details><summary>📋 规格要点（原 specs/event-task-coordination/spec.md + specs/quest-generator/spec.md）</summary>

**triggers_task 字段格式**：
```json
{"task_type": "战斗|收集|调查|传递", "source_type": "生存任务|情报委托", "title": "...", "publisher": "PLAYER|NPC_ID", "description": "..."}
```

**两种结算方式**（互斥）：
1. **即时结算**：cost/effect/transfer 有值，triggers_task 为空 → 对话结束后直接结算
2. **触发任务**：cost/effect/transfer 为空，triggers_task 有值 → 生成任务，完成后再结算

**发布人判定**：
- 玩家主动选择对抗/挑战 → source_type="生存任务"，publisher="PLAYER"
- 事件当事人请求帮助 → source_type="情报委托"，publisher=当事NPC_ID

**完整剧情流程**（选项后不中断剧情）：
1. 开场对话 intro（8-10句）→ 弹出选择界面
2. 玩家做出选择
3. 选项后续对话 choice_dialogues（5-7句）→ 余韵收尾
4. 对话结束后才执行结算或触发任务

**AI导演三个接口**：

| 接口 | 输入 | 影响 |
|------|------|------|
| 导演意图→情报委托节奏 | 施压/缓解/维持 | 施压=提前2天触发+高门槛线索；缓解=可延迟；维持=正常 |
| 种子池权重→势力任务倾向 | 各NPC的heat均值 | 动荡高→调查类多；温情高→经营类多 |
| 微观层回响→triggers_task难度 | 代价回响标记 | 玩家行动导致后续任务难度动态上调 |

**保护规则**：连续施压≤3天。缓解日不额外叠加情报委托或提高势力任务难度。

**"准备感"核心体验**：

| 准备程度 | 可选选项 | 体验 |
|---------|---------|------|
| 充分准备 | 3-4个，含"两全其美"隐藏选项 | 成就感、掌控感 |
| 部分准备 | 2-3个 | 有取舍但不绝望 |
| 完全没准备 | 仅保底选项（有负面后果） | 遗憾感，驱动下次准备 |

**群体行为→势力任务**：群体规模≥3 + 平均压力≥阈值时，势力上司据此派发相关任务。

</details>

- [ ] 8.1 ♻️**改造** — 在 `EventChoice`（`rolling_story_generator.py`）中新增字段：
  ```python
  @dataclass
  class EventChoice:
      # 现有字段: text, requirement, cost, effect, transfer, tension_delta, ...
      # 已有可复用字段: hidden（隐藏选项）, unlock_condition（解锁条件）— 对应 design.md 转幕"满足前置条件可解锁第3选项"
      # 新增：
      triggers_task: Optional[Dict] = None  # {"task_type": "战斗", "source_type": "生存任务", "title": "...", "publisher": "PLAYER", "description": "..."}
  ```
  - ♻️ 更新 `_parse_event_card()` 中的 JSON 解析逻辑 — 已有解析框架
  - ♻️ 更新 LLM prompt（`_build_rolling_story_prompt()`）中的选项格式说明
- [ ] 8.1a ⚠️**补充(design 4.4+6.10)** — 骨架约束注入：在 `_build_rolling_story_prompt()` 中，当 phase != EMERGE 且 `seed.choice_scaffold` 存在时，注入骨架约束段：
  - 新增 `_build_scaffold_constraint(seed, player, phase) -> str` 方法：
    ```python
    def _build_scaffold_constraint(self, seed, player, phase):
        """生成骨架约束 prompt 段，注入后续幕的 LLM prompt"""
        scaffold = seed.choice_scaffold
        committed = seed.player_committed_route
        
        # 门槛倍率表
        multipliers = {
            "ESCALATE": (2.0, 1.5),  # (主路, 侧路)
            "CLIMAX":   (3.0, 2.0),
            "SETTLE":   (1.5, 1.0),
        }
        main_mult, side_mult = multipliers[phase]
        
        constraint = "## 选项设计约束（基于选项骨架，必须遵守）\n\n"
        constraint += "本困境的核心考验维度已确定，生成的选项必须与以下路线对应：\n\n"
        
        for route in scaffold.routes:
            is_main = (route.attr == committed)
            mult = main_mult if is_main else side_mult
            threshold = int(route.base_threshold * mult)
            tag = "← 主路" if is_main else ""
            constraint += f"- 路线「{route.label}」: requirement 包含 PLAYER:{route.attr}:>=:{threshold} {tag}\n"
        
        # 保底（转幕无保底）
        if phase != "CLIMAX":
            constraint += f"- 保底「{scaffold.fallback.label}」: requirement 为 null\n"
        
        constraint += f"\n玩家上一幕选择了「{committed}」路线。\n"
        constraint += f"玩家当前状态：strength={player.strength}, money={player.money}, "
        constraint += f"wit={player.wit}, charm={player.charm}\n"
        
        return constraint
    ```
  - 在 `_build_rolling_story_prompt()` 的 user_prompt 中（玩家状态段之后）插入此约束段
  - ♻️ **已有**：prompt 组装框架（system_prompt + user_prompt 结构），在已有位置插入新段即可
- [ ] 8.1b ⚠️**补充(design 4.4+5.5)** — 起幕 prompt 扩展输出骨架 + 叙事钩子：
  - 在 `_build_rolling_story_prompt()` 中，当 phase == EMERGE 时，在 JSON 输出模板中新增 `scaffold`、`intel_material` 和 `narrative_hook` 字段要求
  - 新增 prompt 指令：
    - "除了生成事件内容，还需输出选项骨架（3条核心路线 + 保底）和情报委托素材（3条线索文本 + 建议持有NPC）"
    - "choice_dialogues（余韵对话）中必须包含对下一幕威胁的自然预告（如反派撂狠话、旁观者提醒），作为情报委托的叙事钩子"
    - "余韵最后一句应为当事NPC请求玩家帮忙打听，作为情报委托的自然触发点"
  - 新增 prompt 约束："3条线索必须分别对应3条路线，每条线索暗示对应路线的准备方向"
  - ♻️ 复用困境类型→维度映射（3.11 的映射表）来约束 LLM 输出的路线属性
- [ ] 8.2 ♻️**改造** — 在 StoryDirector.`process_player_choice()` 中：
  - 检查选中的 EventChoice.triggers_task
  - 如有值 → 不执行 `_apply_direct_consequences()`，改为生成 QuestInstance
  - 如无值 → 走现有的即时结算逻辑
- [ ] 8.3 ♻️**改造** — 对话流程：`_start_parallel_generation_for_dilemma()` 中，对话扩写完成后再触发任务生成
- [ ] 8.4 ♻️**改造** — 发布人判定逻辑（在 `process_player_choice()` 中）：
  ```python
  if triggers_task["source_type"] == "生存任务":
      publisher = "PLAYER"
  else:
      publisher = fate_node.npc_id
  ```
- [ ] 8.5 ♻️**直接复用** — AI导演接口：
  - 无需新增"导演意图"字段，复用 heat 值作为节奏信号：heat>60 = 施压，heat<30 = 缓解
  - 情报委托提前量：heat>60 时提前2天，heat<30 时可延迟
  - 势力任务倾向：通过 StoryDirector.seeds 中各NPC的 heat 均值影响 OrgTaskSystem 的选择
- [ ] 8.6 ♻️**改造** — 涟漪响应：在 RippleEngine 的回调中，检查受影响NPC的态度变化是否超阈值 → 触发 `npc_post_commission()`
- [ ] 8.7 ♻️**改造** — 保护规则：在情报委托生成前检查最近3天是否连续施压（检查 `choice_history` 中最近3条的时间间隔）
- [ ] 8.8 ⚠️**补充(design 6.3)** — 选项后续对话流程：
  - 确认 StoryDirector 是否已实现"选项选择后先展示5-7句对话再结算"
  - 如未实现：在 `process_player_choice()` 中，选择后先触发 `choice_dialogues` 对话展示（玩家登场→各方反应→交锋推进→余韵收尾）
  - 对话结束后才执行 `_apply_direct_consequences()` 或生成 triggers_task 任务
  - ♻️ 对话展示可复用 StoryUI 的对话渲染机制
- [ ] 8.9 ⚠️**补充(design 6.7)** — 代价回响→triggers_task 难度动态调整：
  - 在生成 triggers_task 时，检查 RippleEngine 中玩家最近行动的"代价回响"标记
  - 如有回响 → 调整 triggers_task 的难度参数（如战斗任务敌人更强、收集任务数量增加）
  - 示例：玩家调查了青龙帮 → 青龙帮加派人手 → 战斗任务难度上调
- [ ] 8.10 ⚠️**补充(design 6.8)** — 群体行为涌现→势力任务响应：
  - 在 RippleEngine 回调中，检查是否触发群体行为（群体规模≥3 + 平均压力≥阈值）
  - 如触发 → 通知 OrgTaskSystem 生成相关势力任务（如"协助镇民组织夜间巡逻"或"阻止民间自发武装"）
  - 任务内容取决于玩家所属势力立场
- [ ] 8.11 ⚠️**补充(design 3.1)** — 12时辰事件概率调整：
  - 确认 EventManager 是否已实现午时/申时事件概率×2.0、子丑时×1.5
  - 如未实现 → 在 `try_trigger_random_event()` 中根据当前时辰调整触发概率
  - ♻️ 时辰计算：`current_day_ticks / ticks_per_day * 12` 映射到12时辰
- [ ] 8.12 ⚠️**补充(design 3.2)** — 辰时告示板更新：
  - 在 EventManager.`_tick()` 辰时(07:00-09:00) 触发 `update_bulletin_board()`
  - 清理过期委托 + NPC发布新委托 + 预告信息更新
  - 与 3.13（情报NPC找上门）和 7.7（每日清理）协调，确保辰时统一执行
- [ ] 8.13 ⚠️**补充(design 6.11)** — 行为标签统计与口碑传播：
  - 在 `StoryDirector.process_player_choice()` 中，解析玩家选中 EventChoice 的 requirement 字段，提取主属性维度（strength/agility/wit/charm/money/favor）
  - 记录到玩家行为历史（可存入世界事实库或 player flags）
  - 新增 `_calculate_behavior_tags(player) -> List[str]` 方法：统计最近 N 次选择中各维度使用频率，取 Top1-2 形成标签（如"偏武力"、"善计谋"）
  - 行为标签写入世界事实库（`fact_type="PLAYER_BEHAVIOR"`），通过谣言系统（`rumor_system.py`）在NPC间传播
  - ♻️ **已有**：`rumor_system.py` 的谣言传播机制、世界事实库的 record_fact（阶段九A）
  - ♻️ **复用 RumorSystem**：在 `RumorType` 枚举中新增 `PLAYER_BEHAVIOR` 类型，复用 `RumorSystem.create_rumor()` 创建行为标签谣言，复用 `known_by` + `spread_range` 控制传播范围
- [ ] 8.14 ⚠️**补充(design 6.11)** — 行为标签影响NPC反应：
  - 在 `PromptBuilder` 中新增 `_get_player_reputation_context() -> str`：将行为标签转化为NPC对玩家的预期描述（如"此人惯用武力"→NPC对话中体现戒备/依赖）
  - 注入NPC的LLM上下文，影响NPC对话语气和态度
  - ♻️ **已有**：`PromptBuilder` 的上下文注入框架
- [ ] 8.15 ⚠️**补充(design 5.8a+8)** — 主线任务"在城中站稳脚跟"的阶段推进：
  - Day 1 亥时通过内心独白触发主线任务（不是系统强塞，是情感驱动的）
  - 主线任务分4个阶段：活下来→有收入→有根基（NPC好感≥50）→有势力
  - 在 `QuestManager` 中实现 `check_main_quest_phase(player)` 方法：
    - 检查住所状态 → 阶段1完成
    - 检查经济稳定（铜钱≥50持续2天）→ 阶段2完成
    - 检查社交网络（任一NPC好感≥50）→ 阶段3完成
    - 检查势力状态 → 阶段4完成
  - 每个阶段完成时 `ctx.ft_manager.add_text()` 显示内心独白反馈
  - ♻️ **已有**：QuestManager 的主线任务追踪、sidebar 目标展示
- [ ] 8.16 ⚠️**补充(design 8)** — Day 2 首次小冲突事件（选项锁定教学）：
  - AI导演在 Day 2 申时前后触发一个低级冲突事件
  - 选项设计：至少2个选项的 requirement 门槛略高于玩家初始属性（如 strength≥15, wit≥12）
  - 保底选项（旁观）无门槛
  - 设计意图：玩家第一次看到"能力不够=选项被锁"，产生"我要变强"的内在动机
  - 不触发任何任务——纯叙事种子

## 阶段九A：共享叙事记忆与感知过滤 — `待开始` (0/13)

世界事实库 + 感知过滤器，为所有系统提供统一的叙事状态源和NPC信息边界。

**涉及文件**：新建 `src/narrative_memory.py`、改造 `src/aistory/story_director.py`、`src/llm/prompt_builder.py`、`src/event_system.py`
**复用率**：~40%（涟漪系统的传播逻辑可复用，核心事实库和过滤器需新建）
**对应设计**：designDoc §5.8 + design.md §6.9

<details><summary>📋 规格要点</summary>

**世界事实库**是系统叙事状态的唯一权威来源，维护：
- 事件日志：时间/地点/事件/涉及人/结果
- 关系变化记录：谁和谁的关系因什么事件变化了多少
- 叙事节点层：FateNode阶段、威胁度、玩家行为标签

**感知过滤器**四种途径：

| 感知途径 | 判定条件 | 信息质量 |
|---------|---------|---------|
| 亲眼所见 | NPC在事件发生时处于同一地点 | 完全准确 |
| 间接听闻 | 与知情者好感≥10且2天内有交流 | 基本准确，细节模糊 |
| 逻辑推断 | 智力≥30且观察到相关结果 | 可能正确也可能错误 |
| 公共知识 | 涟漪传播≥5个NPC | 基本事实准确 |

**消费者**：AI导演、叙事引擎、NPC行为系统、任务系统（情报委托线索深度、势力任务分配、NPC委托发布）

</details>

**世界事实库**

> ⚠️ **边界说明**：项目已有 `src/llm/npc_memory.py`（NPCMemorySystem），管理 NPC 对玩家的个人印象（对话级记忆，含短期/长期/衰减）。NarrativeMemory 与其分工不同：
> - **NPCMemorySystem** = NPC 个体视角的主观记忆（"我觉得玩家是好人"、"上次对话他提到了..."）
> - **NarrativeMemory** = 世界级事实的客观记录 + 感知过滤（"Day 3 张铁匠被高府施压"、"谁知道此事"）
> - 两者不应合并：NPCMemorySystem 是 LLM 对话的上下文来源，NarrativeMemory 是系统决策的数据源
> - 交互点：NarrativeMemory 通过感知过滤输出的事实，可写入 NPCMemorySystem 的 KNOWLEDGE 类型记忆

- [ ] 9A.1 🆕**新建** — 新建 `src/narrative_memory.py`，定义核心数据结构：
  ```python
  @dataclass
  class WorldFact:
      fact_id: str               # 唯一ID
      fact_type: str             # "EVENT" | "RELATION_CHANGE" | "PLAYER_ACTION" | "TASK_RESULT"
      timestamp: int             # 游戏天数 * 12 + 时辰
      location: str              # 发生地点
      involved_npcs: List[str]   # 涉及的NPC ID列表
      description: str           # 事实描述（叙事语言）
      tags: List[str]            # 标签（如 "暴力", "调查", "交易"）
      visibility: str            # "PRIVATE" | "LOCAL" | "PUBLIC"（初始可见性）
      witnesses: List[str]       # 在场目击者NPC ID列表

  class NarrativeMemory:
      _facts: List[WorldFact]             # 全部事实记录
      _npc_awareness: Dict[str, Dict[str, str]]  # npc_id → {fact_id → 感知途径}
  ```
- [ ] 9A.2 🆕**新建** — `NarrativeMemory.record_fact(fact: WorldFact)` 方法：
  - 记录事实到 `_facts`
  - 自动标记 witnesses 的感知途径为 "WITNESSED"
  - ♻️ 触发涟漪系统传播（复用 RippleEngine 已有逻辑）
- [ ] 9A.3 🆕**新建** — 事实写入集成点（在已有系统中插入写入调用）：
  - `StoryDirector.process_player_choice()` → 记录事件选择结果
  - `QuestManager._apply_completion_reward()` → 记录任务完成
  - `EventManager._tick()` 中的事件触发 → 记录事件发生
  - `ChatManager._process_response()` → 记录关键对话（可选，按标签过滤）
- [ ] 9A.4 🆕**新建** — `NarrativeMemory.query_facts(filters)` 方法：
  - 支持按 fact_type/时间范围/location/involved_npcs/tags 组合过滤
  - 返回按时间排序的事实列表
  - 供 AI导演、叙事引擎等系统查询

**AI导演监控信号扩展**

- [ ] 9A.5 ♻️**改造** — 在 StoryDirector 中扩展承压指数计算，新增监控维度：
  - **事件密度**：`NarrativeMemory.query_facts(type="EVENT", last_n_days=3).count()` — 最近3天事件数量
  - **社交密度**：`NarrativeMemory.query_facts(type="PLAYER_ACTION", tags=["社交"], last_n_days=3).count()` — 最近3天社交行为数
  - **沉浸感指标**：玩家主动行为（闲聊/探索/训练）频率 vs 被动响应（只应对事件）频率
  - ♻️ **已有**：`_calculate_simple_heat()` 已有基础承压计算，在此基础上扩展维度

**感知过滤器**

- [ ] 9A.6 🆕**新建** — `NarrativeMemory.get_npc_awareness(npc_id: str) -> List[Tuple[WorldFact, str]]` 方法：
  - 返回该NPC知道的所有事实及感知途径
  - 感知途径判定逻辑：
    ```python
    def _determine_awareness(self, npc_id: str, fact: WorldFact) -> Optional[str]:
        # 1. 亲眼所见：NPC在 fact.witnesses 中
        if npc_id in fact.witnesses:
            return "WITNESSED"
        # 2. 间接听闻：NPC与任一知情者好感≥10且2天内有交流
        for witness_id in self._get_aware_npcs(fact.fact_id):
            if get_affinity(npc_id, witness_id) >= 10 and recent_interaction(npc_id, witness_id, days=2):
                return "HEARD"
        # 3. 逻辑推断：NPC智力≥30且观察到相关结果
        if npc.wit >= 30 and self._has_observable_consequence(npc_id, fact):
            return "INFERRED"
        # 4. 公共知识：涟漪传播≥5个NPC知道
        if len(self._get_aware_npcs(fact.fact_id)) >= 5:
            return "PUBLIC"
        return None  # NPC不知道此事
    ```
- [ ] 9A.7 ♻️**改造** — 感知过滤与涟漪系统对接：
  - 在 RippleEngine 传播完成后，更新 `_npc_awareness`
  - ♻️ **已有**：RippleEngine 已输出受影响NPC列表和态度变化，在此基础上增加 awareness 记录
- [ ] 9A.8 ♻️**改造** — 感知过滤注入LLM上下文：在 `PromptBuilder` 中扩展：
  - 新增 `_get_npc_knowledge_context(npc_id: str) -> str` 方法
  - 从 `NarrativeMemory.get_npc_awareness(npc_id)` 获取该NPC知道的事实
  - 根据感知途径调整描述精度：
    - WITNESSED → 完整描述（"你亲眼看到了…"）
    - HEARD → 模糊描述（"你听说…"）
    - INFERRED → 推测语气（"你觉得可能是…"）
    - PUBLIC → 概括描述（"镇上都在传…"）
  - 注入到NPC的LLM system prompt中
  - ♻️ **已有**：`_get_quest_context_for_npc()` 已有上下文注入框架，新增一个 knowledge 维度

**任务系统集成**

- [ ] 9A.9 ♻️**改造** — 情报委托线索深度受感知过滤影响：
  - 在 `IntelQuest` 的线索分配中，目标NPC的感知途径影响线索质量
  - WITNESSED 的NPC → 给出精确线索（进度+1）
  - HEARD 的NPC → 给出模糊方向（进度+0.5，需要第二个来源验证）
  - 非感知范围的NPC → "我不知道"（与现有设计一致）
- [ ] 9A.10 ♻️**改造** — NPC委托发布受感知过滤影响：
  - 在 `npc_post_commission()` 中，NPC只能基于自己感知到的信息发布委托
  - 不知道外来威胁的NPC不会发布"求保护"委托
  - ♻️ 已有需求金字塔驱动逻辑，在此基础上增加信息可用性检查
- [ ] 9A.11 ⚠️**补充(design 5.5.1)** — 信息时效性支持：
  - 在 `WorldFact` 中新增 `expires_at: Optional[int] = None` 字段（过期时间戳，null=永不过期）
  - 在 `NarrativeMemory.query_facts()` 中过滤已过期的事实（`expires_at` 非空且小于当前时间戳时跳过）
  - 情报委托的线索可设置时效（如"青龙帮明晚动手"→设置 expires_at = 当前+12时辰）
  - 过期线索不再影响事件选项解锁
- [ ] 9A.12 ⚠️**补充(design 5.5.1)** — 信息排他性与选择性透露：
  - 在 `NarrativeMemory` 新增 `get_player_exclusive_info() -> List[WorldFact]`：返回只有玩家知道（`_npc_awareness` 中无其他NPC感知到）的事实
  - 在 `RollingStoryGenerator._build_rolling_story_prompt()` 中，将玩家排他信息注入 LLM prompt，指示 LLM 生成"选择性透露"类选项（告诉谁/保密/借此交换）
  - ♻️ **已有**：LLM prompt 组装框架，在已有位置插入排他信息段
- [ ] 9A.13 ⚠️**补充(design 5.5.1)** — 信息拼图配方：
  - 在 `recipes.csv` 中新增线索卡+线索卡的配方类型（如 `clue_A + clue_B = intel_AB`）
  - 在 `recipe_system.py` 中处理线索合成结果：合成后的完整情报写入世界事实库，可能解锁新事件选项
  - 合成逻辑通过 `IntelQuest` 的线索ID关联判定哪些线索可以拼合

## 阶段九B：整合测试 — `待开始` (0/22)

全系统联调验证。

**涉及文件**：可在 `tests/` 目录下新建测试文件

- [ ] 9B.1 生存任务：模拟 player.hunger=80 → 触发生存任务 → player.hunger=20 → 自动消失
- [ ] 9B.2 情报委托：模拟 FateNode EMERGE 生成 → 验证同时输出 scaffold + intel_material → 起幕选择后触发 IntelQuest → 打探3个NPC → 凑齐线索 → 交付
- [ ] 9B.3 势力任务：模拟卯时 → 上司派任务 → 执行 → 完成 → merit增加 → 达标 → 晋升考核
- [ ] 9B.4 公开委托：玩家发布委托 → NPC接取 → 完成/超时；NPC发布 → 玩家接取 → 完成
- [ ] 9B.5 triggers_task：创建含 triggers_task 的 EventChoice → process_player_choice → 验证任务生成
- [ ] 9B.6 多任务并行：同时有 MAIN + INTEL + FACTION + SURVIVAL 四个任务，验证互不干扰
- [ ] 9B.7 截止时间：创建 deadline_days=1 的任务 → 推进游戏天数 → 验证自动失败
- [ ] 9B.8 向后兼容：用旧 quest_config.csv 加载 → 验证 category 默认为 MAIN，新字段默认为 0
- [ ] 9B.9 端到端：按 design.md 第8节"玩家的一天"流程，手动模拟完整一天的任务循环
- [ ] 9B.10 世界事实库：模拟事件发生 → 验证 record_fact 写入 → query_facts 可查询 → 各消费者可读取
- [ ] 9B.11 感知过滤：模拟事件+NPC分布 → 验证亲眼所见/间接听闻/逻辑推断/公共知识四条路径的判定正确性
- [ ] 9B.12 感知过滤+情报委托：验证目标NPC的感知途径影响线索质量（WITNESSED精确 vs HEARD模糊）
- [ ] 9B.13 感知过滤+NPC对话：验证NPC对话中不会透露其未感知到的信息（LLM上下文注入正确性）
- [ ] 9B.14 选项骨架生成：模拟起幕生成 → 验证 LLM 同时输出 event + scaffold + intel_material → scaffold 存入 seed → intel_material 存入 seed
- [ ] 9B.15 骨架约束注入：模拟承幕生成（seed 中已有 scaffold + committed_route="strength"）→ 验证 prompt 中包含骨架约束段 → 验证生成的 EventChoice.requirement 维度匹配 scaffold 路线
- [ ] 9B.16 门槛递进计算：验证 calculate_threshold 在各 phase 下的倍率正确：ESCALATE(2.0/1.5)、CLIMAX(3.0/2.0)、SETTLE(1.5/1.0)
- [ ] 9B.17 committed_route 更新：模拟玩家在承幕选了 money 路线 → 验证 seed.player_committed_route 更新为 "money" → 转幕的骨架约束中 money 为主路
- [ ] 9B.18 骨架+情报一致性端到端：完整模拟起幕生成→情报委托→玩家准备→承幕生成→验证线索暗示的维度与承幕选项的 requirement 维度一致
- [ ] 9B.19 行为标签统计：模拟玩家连续5次选择 strength 路线的选项 → 验证行为标签生成"偏武力" → 验证标签写入世界事实库
- [ ] 9B.20 行为标签影响NPC：验证行为标签注入NPC的LLM上下文 → NPC对话中体现对玩家行为模式的认知
- [ ] 9B.21 信息时效性：创建 expires_at=当前+1天的 WorldFact → 推进游戏时间超过过期点 → 验证 query_facts 不再返回该事实
- [ ] 9B.22 信息排他性+选择性透露：创建只有玩家知道的 WorldFact → 验证 get_player_exclusive_info() 返回该事实 → 验证事件生成 prompt 中包含"选择性透露"选项指令

**Day 1-7 开局体验端到端验收**（依赖阶段十完成）

- [ ] 9B.23 Day 1 验收：
  - 玩家初始状态正确（HP 70, hunger≥70, money 5, 无住所）
  - 进城后生存任务自动触发（饱食度<30 → "肚子快饿扁了"）
  - 去酒馆可触发 Q_TAVERN_HELP → 完成后饥饿值降低、老板娘好感+10
  - 亥时 Q_SETTLE_WAIT 完成 → Q_SETTLE_INTRO 触发内心独白 → 主线面板出现"在城中站稳脚跟"
- [ ] 9B.24 Day 2 验收：
  - 辰时告示板刷新，出现 2-3 个简单委托（搬货/采药等）
  - 玩家可接取并完成委托，获得铜钱+好感
  - 申时 E_TEACH_CONFLICT 触发，至少2个选项因能力不足灰显（strength<15, wit<12）
  - 保底选项（旁观）可选，冲突不触发任何任务
  - 铜钱≥30后生存任务消失
- [ ] 9B.25 Day 3-4 验收：
  - 告示板每日辰时刷新新委托
  - 某NPC好感达30时，闲聊中透露敌方渗透信息（prompt注入正确）
  - 住所升级（好感≥40触发或HAVE_UNIT检测）→ 主线 Q_SETTLE_P1B 完成
  - 主线推进到 Q_SETTLE_P2（攒些盘缠）
- [ ] 9B.26 Day 5-7 验收：
  - Day 5：FateNode 起幕触发（天数≥5 检查通过）
  - 起幕余韵后触发情报委托（如情报系统已实现）
  - Day 6：目标NPC打探获线索，委托报酬下降（threat_level=18 → 报酬×0.8）
  - Day 7：凑齐3线索 → 内心总结 → 交付（如情报系统已实现）
- [ ] 9B.27 Day 1-7 整体验收：
  - 任务类型出场顺序：生存(D1) → 委托(D2) → 主线推进(D4) → 情报(D5)
  - 势力任务 Day 1-7 不出现
  - 主线 Q_SETTLE_* 全程追踪，至少完成到 Q_SETTLE_P2
  - 玩家体验弧完整：饥寒交迫→勉强糊口→逐步融入→有所牵挂

---

## 阶段十：开局体验编排（Day 1-7） — `进行中` (2/13)

通过 quest_config.csv 数据配置和少量 quest type 扩展，编排 Day 1-7 开局体验。
不新建独立编排模块，复用已有任务管道。

**前置依赖**：阶段一（生存任务）、阶段二（任务框架）、阶段七（公开委托·部分 7.1-7.3）、阶段八（事件联动·部分 8.15+8.16）
**不依赖**：阶段五/六（势力任务，Day 1-7 不出现）、阶段九A（叙事记忆，可降级）
**涉及文件**：`data/quest_config.csv`、`data/dialog_config.csv`、`tools/make_quest_csv.py`、
  `src/task/quest_system.py`、`src/entities/player.py`、
  `src/event_system.py`、`src/llm/prompt_builder.py`、`src/aistory/story_director.py`
**对应设计**：design.md §8（开局体验流）+ §2.3（任务出场时序）+ §1.1（玩家初始状态）+ §2.4（敌方渗透影响）

<details><summary>Day 1-7 关键路径依赖图</summary>

```
Day 1-7 关键路径：
├── 必须完成：阶段一（生存任务）→ 阶段二（多槽位）→ 阶段十（本阶段）
├── 部分完成：阶段七（委托·仅需 7.1-7.3）
├── 部分完成：阶段八（事件联动·仅需 8.15+8.16）
├── 部分完成：阶段三（情报委托·需 3.1-3.6，Day 5 起）
├── 不需要：阶段五/六（势力任务）
├── 不需要：阶段九A（叙事记忆）
└── 最后验证：阶段九B（9B.23-9B.27）
```

</details>

**已完成**：
- [√] 10.1 数据配置 — quest_config.csv 主线任务链 + 酒馆互动（`tools/make_quest_csv.py`）
- [√] 10.2 数据配置 — quest type 文档更新（WAIT_TIME / AFFINITY_CHECK）

**已完成说明**：
> 10.1 通过 `tools/make_quest_csv.py` 生成，已包含：
> - 主线任务链 Q_SETTLE_*（8条 quest）：WAIT_TIME(Day1亥时) → DIALOG(内心独白) → EAT(填肚子) → HAVE_UNIT(找住处) → RESOURCE_TOTAL(攒50铜) → AFFINITY_CHECK(交朋友) → ORG_RANK(加入势力) → DIALOG(完成)
> - 酒馆互动 Q_TAVERN_*（2条 quest）：INTERACT(搬酒箱) → DIALOG(吃顿热饭)
> - 配套对话共 79 条 dialog 条目（含环境描写、内心独白、NPC对白）
> - 对话 action 包括：SET_HUNGER:40、AFFINITY_酒馆老板娘:10、FADE_TO_BLACK/FROM_BLACK、COMPLETE_SETTLE 等

- [ ] 10.3 ♻️**改造** — 玩家初始状态对齐（`src/entities/player.py`）：
  - `self.money = 200` → `self.money = 5`
  - 确认 `self.hp = 70`（逃难受伤）、hunger 值应≥70（对应饱食度≤20，饥饿警告）
  - 确认 `self.cold = 40`（衣衫褴褛，偏冷）
  - 确认所有NPC初始好感=0、所有能力属性初始=10
  - 对应：design.md §1.1

- [ ] 10.4 🆕**新增 quest type** — `WAIT_TIME`（`src/task/quest_system.py`）：
  在 `check_progress()` 中新增 WAIT_TIME 类型处理：
  ```python
  # quest_config.csv 示例：type=WAIT_TIME, target=1:亥, count=0
  # 含义：等到 Day 1 的亥时自动完成
  elif qtype == 'WAIT_TIME':
      day_str, hour_str = quest.target.split(':')
      target_day = int(day_str)
      target_hour = HOUR_MAP[hour_str]  # 亥=21, 辰=7, 申=15 等
      if player.day >= target_day and current_hour >= target_hour:
          return True
  ```
  - 复用 check_progress() 的通用框架，只加一个 elif 分支
  - HOUR_MAP 映射12时辰到24小时制（已有时辰系统可复用）
  - 通用 type，后续任何"等到特定时间"的任务都可复用
  - ⚠️**补充**：在 `advance_quest()` 的 `auto_activate` 列表中加入 `'WAIT_TIME'`（当前只有 GOAL/RESOURCE_TOTAL/FREE，WAIT_TIME 也应自动激活）
  - ⚠️**补充**：submit_npc='9999' 的自动推进逻辑（当前仅 REACH 类型有），需扩展为所有 submit_npc='9999' 的类型共用，包括 WAIT_TIME/EAT/AFFINITY_CHECK/ORG_RANK/RESOURCE_TOTAL
  - 对应：design.md §8 Day 1 亥时触发

- [ ] 10.5 🆕**新增 quest type** — `AFFINITY_CHECK`（`src/task/quest_system.py`）：
  在 `check_progress()` 中新增 AFFINITY_CHECK 类型处理：
  ```python
  # quest_config.csv 示例：type=AFFINITY_CHECK, target=ANY, count=50
  elif qtype == 'AFFINITY_CHECK':
      threshold = quest.count
      if quest.target == 'ANY':
          return any(npc.affinity_to_player >= threshold for npc in all_npcs)
      else:
          npc = find_npc_by_name(quest.target)
          return npc and npc.affinity_to_player >= threshold
  ```
  - 通用 type，后续任何"好感达标"的主线推进都可复用
  - ⚠️**补充**：在 `advance_quest()` 的 `auto_activate` 列表中加入 `'AFFINITY_CHECK'`
  - 对应：design.md §8 Day 4 住所升级 + §5.8a 主线阶段3

- [ ] 10.5b 🆕**新增 quest type** — `ORG_RANK`（`src/task/quest_system.py`）：
  Q_SETTLE_P4 使用了此类型但 `check_progress()` 中尚无实现：
  ```python
  # quest_config.csv 示例：type=ORG_RANK, target=ANY, count=1
  elif qtype == 'ORG_RANK':
      player_rank = getattr(player, 'player_org_rank', 0)
      if player_rank >= (quest.count or 1):
          return True
  ```
  - ⚠️**补充**：在 `advance_quest()` 的 `auto_activate` 列表中加入 `'ORG_RANK'`
  - 对应：Q_SETTLE_P4（加入势力）

- [ ] 10.6 ♻️**改造** — quest_system.py 初始任务衔接：
  - 城镇模式启动时，设置 `_active_quest_id = 'Q_SETTLE_WAIT'`
  - 需与现有沙盒模式（Q_YUXISHI_TRIGGER）和生存模式（Q_PROLOGUE）共存
  - 在 `world_loader.py` 初始化时根据游戏模式选择初始任务链
  - 旧序章链（鱼西施/泼皮牛二）保留为沙盒模式，Q_SETTLE_* 作为城镇模式主线

- [ ] 10.7 ♻️**改造** — EventManager 支持按天数+时辰触发预设事件（`src/event_system.py`）：
  新增配置化的定时事件表（通用机制，非一次性代码）：
  ```python
  SCHEDULED_EVENTS = {
      (2, '申'): 'E_TEACH_CONFLICT',  # Day 2 申时：教学冲突
      # 后续可扩展更多定时事件
  }
  ```
  在 `_tick()` 中检查当前 (day, hour) 是否在表中，有则触发
  表可后续迁移到 `data/scheduled_events.csv`

- [ ] 10.8 🆕**数据配置** — Day 2 教学冲突事件（`data/event_data.csv` + `data/event_dialog_config.csv`）：
  复用 event_data.csv + event_dialog_config.csv 的完整事件管道：
  ```
  E_TEACH_CONFLICT,街头欺凌,壮汉在欺负小贩
    选项A [挺身而出]: requirement=PLAYER:strength:>=:15 → 灰显
    选项B [智取]: requirement=PLAYER:wit:>=:12 → 灰显
    选项C [旁观]: 无门槛，可选
  ```
  - 不触发任何任务——纯叙事种子，教学"能力不够=选项被锁"
  - 通过 `tools/` 下的事件脚本生成（参考已有事件数据生成方式）
  - 对应：design.md §8 Day 2 申时

- [ ] 10.9 ♻️**改造** — PromptBuilder 闲聊内容注入（`src/llm/prompt_builder.py`）：
  在 NPC 上下文注入中增加"敌方渗透信息"素材池：
  - 条件：NPC 好感≥30 且 player.day≥3
  - 注入内容按NPC职业/位置选择（3-5条素材）：
    - 商人NPC："最近城里不太平，来了几个外地人，价钱压得特别低..."
    - 酒馆NPC："前阵子来了几个生面孔，出手阔绰，问东问西的..."
    - 手艺人NPC："东街新开的铺子压价厉害，赵掌柜都快撑不住了..."
  - ♻️ 复用 `_get_quest_context_for_npc()` 上下文注入框架
  - 素材可放 `data/gossip_pool.csv` 或直接定义在 prompt_builder 中
  - 对应：design.md §8 Day 3

- [ ] 10.10 ♻️**改造** — FateNode 天数前置条件（`src/aistory/story_director.py`）：
  在 `try_to_generate_beat()` 中新增检查：
  ```python
  if player.day < 5:
      return None  # 开局前4天不触发NPC人生困境
  ```
  - Day 5 起仍由 heat 机制驱动，首个 FateNode 可适当降低 heat 门槛
  - 对应：design.md §8 Day 5 + §2.3

- [ ] 10.11 ♻️**改造** — 敌方渗透基础数值（复用阶段七 7.12 框架）：
  - 实现 threat_level 基础值：Day 1-4 = 5（平静期），Day 5-7 = 18（渗透期）
  - 在 `npc_post_commission()`（7.3）中接入：`reward_gold *= (1 - threat_modifier)`
  - 在物价中接入：`price *= (1 + cost_modifier)`
  - 玩家体感："昨天做委托赚50铜，今天只能赚40铜了"
  - 对应：design.md §2.4 + §8 Day 6

- [ ] 10.13 ♻️**改造** — Q_TAVERN_HELP 触发方式（`data/quest_config.csv` + `data/dialog_config.csv`）：
  酒馆支线与主线（Q_SETTLE_*）并行，**不需要独立触发系统**。
  利用现有 dialog_config.csv 的 action 字段驱动 NPC 演出行为：
  - Q_TAVERN_HELP 的 dialog action 中包含 NPC 移动指令（酒馆老板娘走向玩家）
  - 触发条件：玩家 hunger ≥ 50 且距酒馆区域足够近时，由主线推进自动触发或通过 INTERACT 接取
  - 对话结束后 action 执行 SET_HUNGER:40 + AFFINITY_酒馆老板娘:10
  - ⚠️ 核心原则：所有 NPC 主动行为（走向玩家、搭话）都通过 dialog_config.csv 的 action 字段实现，不另建独立的主动行为系统
  - 对应：design.md §8 Day 1 酒馆互动

- [ ] 10.14 ♻️**改造** — 清理 `get_all_task_displays()` 调试/模拟数据（`src/task/quest_system.py`）：
  当前 `get_all_task_displays()` 中存在不应上线的硬编码调试数据：
  - 删除 line 1397-1408 的调试模式（hunger < 50 时不应仍显示生存任务提示）
  - 删除 line 1420-1443 的模拟情报任务/势力任务数据（假数据会误导验证）
  - 保留真实的 hunger >= 70 / hunger >= 50 判断逻辑
  - cold 阈值应从 `>= 70` 改为 `>= 60`（对齐 design.md 和阶段一规格的阈值表）

- [ ] 10.15 ♻️**改造** — 新增 quest type 的进度展示文本（`src/task/quest_system.py`）：
  在 `get_current_objective_text()` 中为新增的三种 quest type 补充进度展示：
  ```python
  # WAIT_TIME: 显示等待目标时间
  if qtype == 'WAIT_TIME':
      return f"等待至 Day {target_day} {hour_name}时"
  # AFFINITY_CHECK: 显示当前最高好感 / 目标
  if qtype == 'AFFINITY_CHECK':
      return f"结交朋友（好感 {current_max}/{threshold}）"
  # ORG_RANK: 显示当前等级 / 目标
  if qtype == 'ORG_RANK':
      return f"加入势力（等级 {current_rank}/{target_rank}）"
  ```
  - 确保 sidebar "要务"区域能正确显示这些任务的当前进度

---

## 附录：复用分析总结

### 各阶段复用率一览

| 阶段 | 复用率 | 🆕新建 | ♻️改造/复用 | 说明 |
|------|--------|--------|------------|------|
| 阶段一：生存任务 | ~30% | SurvivalTask 数据类、事件触发 | sidebar 阈值判断、_tick()插入点、ft_manager | 核心概念新建，判断逻辑复用 |
| 阶段二：任务槽位 | ~60% | 多槽位机制、QuestInstance | OrgTask 状态管理模式、结算管道、CSV 解析 | 与 OrgTaskSystem 高度同构 |
| 阶段三：情报委托 | ~40% | IntelQuest、打探按钮、结果判定 | prompt 注入、LLM 管道、FateNode/四幕、heat | 核心玩法新建，基础设施复用 |
| 阶段四：目标展示 | ~100% | 无 | sidebar "要务"区域全部改造 | 纯 UI 改造 |
| 阶段五：势力任务基础 | ~70% | 睡觉缓存、上司分配 | OrgTaskSystem 全套管道、rank 体系、merit | 扩展 OrgTaskSystem 即可 |
| 阶段六：势力任务完整 | ~70% | 自创势力 | 晋升体系、effect 格式、sidebar | 仅自创势力需全新逻辑 |
| 阶段七：公开委托 | ~30% | 告示板 UI、NPC 委托 AI | UI 风格、结算管道、日重置模式 | 全新玩法，管道复用 |
| 阶段八：事件联动 | ~90% | 无新文件 | EventChoice 加字段、process_player_choice 加分支、行为标签统计 | 几乎全是改造 |
| 阶段九A：共享叙事记忆 | ~40% | NarrativeMemory、WorldFact、感知过滤器、信息时效/排他 | 涟漪系统传播逻辑、PromptBuilder注入框架、heat计算 | 事实库新建，LLM注入复用 |
| 阶段十：开局体验编排 | ~80% | WAIT_TIME/AFFINITY_CHECK 2个quest type、闲聊素材池、定时事件表 | quest_config.csv管道、dialog_config.csv、event_data.csv、check_progress()框架、PromptBuilder注入 | 数据配置为主，代码改动极少 |

### 真正需要新建的系统功能（按优先级）

| 优先级 | 新功能 | 复杂度 | 阶段 | 说明 |
|--------|--------|--------|------|------|
| **高** | 多任务槽位机制 | 中 | 二 | 从单任务→多槽位，是后续所有任务类型的基础 |
| **高** | IntelQuest 情报委托 | 高 | 三 | 线索/打探/收集的全新玩法循环 |
| **高** | ChatUI 打探按钮 | 中 | 三 | 替代废弃的 quick_replies，情报委托的 UI 入口 |
| **中** | SurvivalTask 数据类 | 低 | 一 | 简单数据类 + 阈值检查 |
| **中** | 告示板 UI + 委托系统 | 高 | 七 | 全新 UI 面板 + NPC 委托 AI |
| **中** | NarrativeMemory 世界事实库 | 高 | 九A | 事实记录/查询/感知过滤，全系统共享的叙事状态源 |
| **中** | 感知过滤器 | 中 | 九A | 四种感知途径判定 + LLM上下文注入 |
| **低** | 自创势力 | 中 | 六 | 数据结构可复用，逻辑需新建 |
| **低** | 行为标签统计 | 低 | 八 | 统计玩家选择模式 + 谣言传播，复用已有系统 |
| **低** | 信息时效/排他/选择性透露 | 中 | 九A | WorldFact 扩展 + LLM prompt 注入 |
| **低** | WAIT_TIME/AFFINITY_CHECK quest type | 低 | 十 | check_progress() 中各加一个 elif 分支 |
| **低** | EventManager 定时事件表 | 低 | 十 | _tick() 中查表触发，通用机制 |

### 重复造轮子风险清单

> 1. **`FactionTaskDispatcher` vs `OrgTaskSystem`** — 最大风险。OrgTaskSystem 已有 accept_task/check_task_progress/turn_in_task/cooldown 全套管道，建议扩展而非新建独立类。
>
> 2. **`QuestInstance` vs `OrgTask`** — 两者字段结构几乎同构（status/progress/cooldown），建议抽取公共基类或保持接口一致。
>
> 3. **奖惩结算散落** — `_apply_completion_reward()`、`turn_in_task()`、`add_player_merit()` 做类似的事，建议统一结算入口避免逻辑分散。
>
> 4. **sidebar 状态警告 vs SurvivalTask** — sidebar 121-140行已有 hunger/cold/hp 警告，SurvivalTask 的阈值检查不应独立重写，应复用或统一数据源。
