## ADDED Requirements

### Requirement: 任务必须有分类

系统必须为每个任务指定分类：MAIN（主线）、FACTION（势力）、PERSONAL（个人委托）。

#### Scenario: 主线任务分类
- **WHEN** 任务 category 为 MAIN
- **THEN** 任务进入主线任务槽，同时只能有1个主线任务

#### Scenario: 势力任务分类
- **WHEN** 任务 category 为 FACTION
- **THEN** 任务进入势力任务槽，每个势力同时只能有1个任务

#### Scenario: 个人委托分类
- **WHEN** 任务 category 为 PERSONAL
- **THEN** 任务进入个人委托槽，同时最多3个

---

### Requirement: 任务必须有发布人

系统必须确保每个任务都有明确的发布人NPC。没有发布人的任务不允许创建。

#### Scenario: 主线任务发布人
- **WHEN** 主线任务由AI导演生成
- **THEN** 任务必须有 submit_npc 字段指定发布人NPC

#### Scenario: 势力任务发布人
- **WHEN** 势力任务生成时
- **THEN** 发布人为势力领导（帮主、掌门等）

#### Scenario: 个人委托发布人
- **WHEN** NPC发布个人委托时
- **THEN** 发布人为该NPC自己

---

### Requirement: 多任务槽位管理

系统必须支持三层任务槽位：主线槽、势力槽、个人委托槽。

#### Scenario: 主线任务槽唯一
- **WHEN** 玩家已有一个进行中的主线任务
- **THEN** 不能接取新的主线任务，直到当前任务完成或失败

#### Scenario: 势力任务槽按势力分开
- **WHEN** 玩家同时加入两个势力
- **THEN** 每个势力可以各有1个进行中的任务

#### Scenario: 个人委托槽上限
- **WHEN** 玩家已有3个进行中的个人委托
- **THEN** 不能接取新的个人委托，直到有空位

---

### Requirement: 任务本金支持

系统必须支持任务发布时向玩家提供本金或物资。

#### Scenario: 领取任务本金
- **WHEN** 任务 given_gold > 0 且玩家接取任务
- **THEN** 玩家获得指定数量的铜钱

#### Scenario: 领取任务物资
- **WHEN** 任务 given_item 不为空且玩家接取任务
- **THEN** 玩家获得指定数量的物品

#### Scenario: 任务失败扣除本金
- **WHEN** 任务失败且有本金
- **THEN** 根据情况处理（可能扣除好感作为惩罚）

---

### Requirement: 任务截止时间

系统必须支持任务截止时间，超时任务自动失败。

#### Scenario: 任务有截止时间
- **WHEN** 任务 deadline_days > 0
- **THEN** 任务必须在指定天数内完成

#### Scenario: 任务超时失败
- **WHEN** 任务超过截止时间且未完成
- **THEN** 任务状态变为失败
- **AND** 扣除发布人好感度（failure_relation）

#### Scenario: 无截止时间任务
- **WHEN** 任务 deadline_days = 0
- **THEN** 任务没有时间限制

---

### Requirement: 任务奖励配置

系统必须支持配置任务奖励，任务完成时自动发放。

#### Scenario: 奖励铜钱
- **WHEN** 任务完成且 reward_gold > 0
- **THEN** 玩家获得指定数量的铜钱

#### Scenario: 奖励声望
- **WHEN** 任务完成且 reward_fame > 0
- **THEN** 玩家获得指定数量的声望

#### Scenario: 奖励物品
- **WHEN** 任务完成且 reward_items 不为空
- **THEN** 玩家获得指定的物品

#### Scenario: 奖励好感度
- **WHEN** 任务完成且 reward_relation > 0
- **THEN** 发布人NPC对玩家好感度增加

---

### Requirement: 兼容现有任务配置

系统必须向后兼容现有的 quest_config.csv 配置，旧配置的任务能正常运行。

#### Scenario: 旧配置默认分类
- **WHEN** 任务配置没有 category 字段
- **THEN** 默认分类为 MAIN

#### Scenario: 旧配置默认奖励
- **WHEN** 任务配置没有 reward 字段
- **THEN** 奖励为0，任务完成后无奖励

#### Scenario: 旧任务流程不变
- **WHEN** 使用旧配置的任务
- **THEN** 任务接取、进行、完成的流程保持不变
