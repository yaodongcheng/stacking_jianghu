## 1. 数据结构升级

- [ ] 1.1 扩展 QuestData 类，新增字段：category, given_gold, given_item, given_item_count, deadline_days, reward_gold, reward_fame, reward_items, reward_relation, failure_relation
- [ ] 1.2 新增 QuestInstance 类，包含：quest_id, status, progress, start_day, publisher_id, publisher_name
- [ ] 1.3 更新 CSV 解析逻辑，支持新增字段（带默认值）
- [ ] 1.4 编写单元测试验证数据结构兼容性

## 2. 多任务槽位管理

- [ ] 2.1 QuestManager 新增槽位属性：main_quest_slot, faction_quest_slots, personal_quest_slots
- [ ] 2.2 实现 get_active_quests() 方法，返回所有进行中的任务
- [ ] 2.3 实现 accept_quest(category, quest_id) 方法，支持多任务接取
- [ ] 2.4 实现 check_progress_all() 方法，检查所有任务进度
- [ ] 2.5 实现 get_available_slots(category) 方法，返回指定分类的空余槽位
- [ ] 2.6 保持向后兼容：active_quest_id 和 quest_status 属性指向主线任务槽

## 3. 任务本金与奖励

- [ ] 3.1 接取任务时发放本金（given_gold）和物资（given_item）
- [ ] 3.2 任务完成时发放奖励：reward_gold, reward_fame, reward_items
- [ ] 3.3 任务完成时增加发布人好感度（reward_relation）
- [ ] 3.4 任务失败时扣除发布人好感度（failure_relation）

## 4. 任务截止时间

- [ ] 4.1 任务实例记录 start_day
- [ ] 4.2 每日检查任务是否超时（deadline_days > 0）
- [ ] 4.3 超时任务自动失败，触发惩罚逻辑

## 5. 任务生成器 - QuestGenerator

- [ ] 5.1 创建 QuestGenerator 类
- [ ] 5.2 实现物资收集任务模板生成
- [ ] 5.3 实现战斗任务模板生成
- [ ] 5.4 实现侦查任务模板生成
- [ ] 5.5 实现太阁风格对话文本生成

## 6. AI导演主线任务生成

- [ ] 6.1 在 AI导演系统 中添加主线任务生成触发点
- [ ] 6.2 实现威胁度阈值触发主线任务
- [ ] 6.3 实现前置任务完成触发下一个主线任务
- [ ] 6.4 主线任务生成后通知发布人NPC主动找玩家

## 7. 势力任务发布

- [ ] 7.1 势力数据结构新增 leader_id（领导NPC ID）
- [ ] 7.2 玩家加入势力时触发入门任务生成
- [ ] 7.3 实现势力任务定期刷新机制
- [ ] 7.4 势力领导使用太阁风格对话发布任务

## 8. NPC个人委托发布

- [ ] 8.1 NPC需求金字塔状态检测
- [ ] 8.2 实现NPC发布任务的好感度门槛检查
- [ ] 8.3 NPC主动接近玩家发布任务的AI行为
- [ ] 8.4 实现NPC发布任务冷却时间机制
- [ ] 8.5 玩家拒绝任务的处理逻辑

## 9. UI目标面板

- [ ] 9.1 创建任务面板UI组件
- [ ] 9.2 实现主线任务区域展示
- [ ] 9.3 实现势力任务区域展示
- [ ] 9.4 实现个人委托区域展示
- [ ] 9.5 实现预告信息区域展示
- [ ] 9.6 实现任务接取/放弃交互按钮

## 10. 整合测试

- [ ] 10.1 编写多任务并行测试用例
- [ ] 10.2 编写任务超时失败测试用例
- [ ] 10.3 编写NPC发布任务测试用例
- [ ] 10.4 编写向后兼容性测试用例（旧配置文件）
- [ ] 10.5 端到端游戏流程测试
