# AI原子行为系统重构设计

## 核心设计理念

基于你的C#代码思想：**大部分NPC行为都是原子行为的组合**。

NPC的行为本质上就是：
- **移动** - 去某个位置
- **堆叠** - 物理关系（背起、放下、叠上去）
- **等待** - 时间消耗
- **战斗** - 追击+攻击
- **动画/表现** - 播放动作、说话气泡

---

## 一、原子行为分类（保留）

### 移动类
| 行为 | 说明 | 参数 |
|------|------|------|
| `MoveToPosition` | 移动到坐标 | x, y, stop_dist, reason |
| `FollowTarget` | 跟随目标 | target, stop_dist, keep_follow |
| `Roam` | 区域漫步 | zone_rect, duration |

### 堆叠类
| 行为 | 说明 | 参数 |
|------|------|------|
| `CarryTarget` | 背起目标 | target |
| `DropTarget` | 放下目标 | offset_x, offset_y |
| `StackOn` | 堆叠到目标上 | target |
| `Unstack` | 取消堆叠 | bounce_dist |

### 时间类
| 行为 | 说明 | 参数 |
|------|------|------|
| `Wait` | 等待 | duration_ms |
| `Stay` | 原地驻守（永不结束） | - |

### 战斗类
| 行为 | 说明 | 参数 |
|------|------|------|
| `Combat` | 追击+攻击 | target, combat_manager |

### 表现类（建议新增）
| 行为 | 说明 | 参数 |
|------|------|------|
| `Say` | 显示气泡对话 | text, duration |
| `LookAt` | 面向目标 | target, duration |

---

## 二、复合行为 = 原子行为队列

### 当前已有的复合行为（保留）

| 复合行为 | 原子组合 |
|----------|----------|
| `MoveToBuilding` | MoveToPosition → StackOn |
| `Spectate` | MoveToPosition → Stay(看向目标) |
| `Rescue` | MoveToPosition → CarryTarget → MoveToPosition → DropTarget |
| `Salute` | MoveToPosition(侧移) → Say → Wait |
| `PayTribute` | MoveToPosition → Wait |

### 需要删除的冗余代码

以下是 `ai_system.py` 中不应该存在的**行为逻辑**（应由原子行为组合完成）：

1. **`_enqueue_farmer`** → 应归入 `FarmerBehavior.execute()` 
2. **`_enqueue_merchant`** → 应归入 `MerchantBehavior.execute()`
3. **`_enqueue_guard`** → 应归入 `GuardBehavior.execute()`
4. **`_enqueue_scholar`** → 应归入 `ScholarBehavior.execute()`
5. **`_enqueue_bandit`** → 应归入 `BanditBehavior.execute()`
6. **`_enqueue_artisan`** → 应归入 `ArtisanBehavior.execute()`
7. **各种内联的移动/等待逻辑** → 应调用 `action_queue.enqueue()`

---

## 三、AISystem 职责精简

### ✅ 保留（核心职责）
```python
class AISystem:
    def __init__(self, combat_manager):
        self.combat_manager = combat_manager
        self.job_registry = JobBehaviorRegistry()  # 职业行为注册表
    
    # 1. 事件广播/处理
    def push_event(self, npc, evt): ...
    def _process_events(self, npc, world_map): ...
    
    # 2. 感知系统
    def _process_see(self, npc, all_npcs): ...
    
    # 3. 战斗仇恨管理
    def _calc_priority_target(self, npc, nearby): ...
    
    # 4. 主循环分发
    def update(self, all_npcs, ...):
        for npc in all_npcs:
            # 4.1 处理事件
            if self._process_events(npc, world_map):
                continue
            # 4.2 处理战斗
            if npc.in_combat:
                self._tick_combat(npc)
                continue
            # 4.3 委托给职业行为
            behavior = self.job_registry.get(npc.job)
            behavior.execute(npc, context)
```

### ❌ 删除（冗余逻辑）
- `_enqueue_farmer`, `_enqueue_merchant` 等所有内联行为方法
- 重复的移动/等待逻辑
- 与 `job_behaviors/*.py` 重复的代码

---

## 四、核心API：EnqueueAction 模式

### 设计核心

参考C#代码的设计，所有行为通过 **`enqueue_action()`** 入队原子行为：

```csharp
// C# 原版写法
EnqueueAction(new LookAtAction(targetAgent, 0.5f));
EnqueueAction(new FollowAgentAction(targetAgent, false, radius: 2.0f));
EnqueueAction(new LookAtAction(targetAgent, 0.5f));
EnqueueAction(new StayAction(targetAgent));
```

### Python 对应实现

```python
# Python 写法（统一通过 action_queue）
npc.action_queue.enqueue(LookAt(target, duration=0.5))
npc.action_queue.enqueue(FollowTarget(target, radius=2.0, stop_dist=0.5))
npc.action_queue.enqueue(LookAt(target, duration=0.5))
npc.action_queue.enqueue(Stay(reason="待命"))
```

### ActionQueue 核心方法

```python
class ActionQueue:
    """NPC行为队列管理器"""
    
    def enqueue(self, action: AtomicAction):
        """入队（末尾添加）"""
        self._queue.append(action)
    
    def enqueue_front(self, action: AtomicAction):
        """插队（头部添加，用于紧急行为）"""
        self._queue.insert(0, action)
    
    def clear(self):
        """清空队列（被打断时调用）"""
        if self._current:
            self._current.on_end(self.owner)
        self._current = None
        self._queue.clear()
    
    def is_empty(self) -> bool:
        """是否空闲"""
        return self._current is None and len(self._queue) == 0
    
    def tick(self, dt_ms) -> bool:
        """每帧执行"""
        # 取出队首执行，完成后自动切换下一个
```

---

## 五、职业行为统一接口

所有职业行为继承 `BaseJobBehavior`，核心是用 `enqueue()` 组合原子行为：

```python
class BaseJobBehavior(ABC):
    @abstractmethod
    def execute(self, npc, context: dict) -> bool:
        """组合原子行为入队"""
        pass
```

### 职业行为示例

```python
# 玩家下达"过来"指令
def handle_come_here(npc, target_agent):
    npc.action_queue.clear()  # 打断当前行为
    npc.action_queue.enqueue(LookAt(target_agent, duration=0.5))
    npc.action_queue.enqueue(FollowTarget(target_agent, radius=2.0, stop_dist=0.5))
    npc.action_queue.enqueue(LookAt(target_agent, duration=0.5))
    npc.action_queue.enqueue(Stay(reason="待命"))

# 农民日常行为
class FarmerBehavior(BaseJobBehavior):
    def execute(self, npc, context):
        # 有粮食 → 去卖
        if npc.inventory.get(ITEM_GRAIN, 0) >= 3:
            market = self.find_building_by_type(context['all_buildings'], 'MARKET')
            npc.action_queue.enqueue(MoveToPosition(market.rect.centerx, market.rect.centery, reason="运粮去卖"))
            npc.action_queue.enqueue(Wait(1500, reason="交易"))
            return True
        
        # 去农场工作
        farm = self.find_building_by_type(context['all_buildings'], 'FARM')
        npc.action_queue.enqueue(MoveToBuilding(farm, reason="干活"))
        return True

# 守卫护卫行为
class GuardBehavior(BaseJobBehavior):
    def execute(self, npc, context):
        leader = self._find_leader(npc, context['all_npcs'])
        if leader:
            npc.action_queue.enqueue(FollowTarget(leader, radius=70, keep_follow=True, reason=f"护卫{leader.name}"))
            return True
        
        # 普通巡逻
        patrol_pos = self._get_next_patrol_point(npc, context['world_map'])
        npc.action_queue.enqueue(MoveToPosition(*patrol_pos, reason="巡逻"))
        npc.action_queue.enqueue(Wait(random.randint(1000, 3000), reason="巡逻驻足"))
        return True
```

### 事件驱动的行为链

```python
# 响应"围观犯罪"事件
def on_witness_crime(npc, event):
    criminal = event['criminal']
    assigned_pos = event['position']
    turn_dir = event['look_direction']
    delay = calculate_reaction_delay(npc, criminal)
    
    npc.action_queue.clear()
    npc.action_queue.enqueue(Wait(delay * 1000, reason="反应时间"))  # 延迟反应
    npc.action_queue.enqueue(LookAt(criminal, duration=0.5))
    npc.action_queue.enqueue(MoveToPosition(*assigned_pos, reason="围观"))
    npc.action_queue.enqueue(Stay(reason="围观中"))

# 响应"跟随"指令
def on_order_follow(npc, event):
    target = event['target']
    npc.action_queue.clear()
    npc.action_queue.enqueue(FollowTarget(target, keep_follow=True, reason="跟随"))

# 响应"攻击"指令
def on_order_attack(npc, event):
    target = event['target']
    npc.action_queue.clear()
    npc.action_queue.enqueue(Combat(target, reason=f"攻击{target.name}"))
```

---

## 五、事件驱动中断机制

参考你的C#代码 `ReceiveEvent()` 设计：

```python
def receive_event(self, npc, event):
    """处理突发事件，可能打断当前行为"""
    
    if event['type'] == 'COMBAT_START':
        # 清空当前行为，开始围观
        npc.action_queue.clear()
        self.enqueue_spectate(npc, event['cx'], event['cy'], "围观")
    
    elif event['type'] == 'ATTACKED':
        attacker = event['attacker']
        npc.action_queue.clear()
        self.enqueue_combat(npc, attacker, "反击")
    
    elif event['type'] == 'ORDER_FOLLOW':
        target = event['target']
        npc.action_queue.clear()
        self.enqueue_follow(npc, target, keep_follow=True)
```

---

## 六、文件结构（重构后）

```
src/
├── atomic_actions.py        # 所有原子行为（已有，保留）
├── ai_system.py             # 精简版：事件/感知/主循环分发
├── ai/
│   ├── __init__.py
│   ├── constants.py         # AI相关常量
│   ├── event_processor.py   # 事件处理
│   ├── job_behaviors/
│   │   ├── __init__.py
│   │   ├── base.py          # 基类（已有，保留）
│   │   ├── registry.py      # 注册表（已有，保留）
│   │   ├── farmer.py        # 农民
│   │   ├── merchant.py      # 商人
│   │   ├── guard.py         # 守卫
│   │   ├── bandit.py        # 山贼
│   │   ├── scholar.py       # 学者
│   │   └── artisan.py       # 工匠
│   ├── combat_ai.py         # 战斗AI（仇恨/锁定/追击）
│   └── spectate_ai.py       # 围观AI
```

---

## 七、实施计划

### Phase 1: 清理 ai_system.py
1. 删除所有 `_enqueue_xxx` 方法
2. 保留：事件处理、感知系统、主循环
3. 主循环中改为调用 `job_registry.get(npc.job).execute()`

### Phase 2: 完善 job_behaviors
1. 确保每个职业都有对应的 Behavior 类
2. 所有行为只通过 `enqueue_xxx` 方法组合原子行为
3. 不允许在 Behavior 中直接操作 `npc.state` 等底层属性

### Phase 3: 统一事件机制
1. 参考 C# 的 `ReceiveEvent` 模式
2. 所有中断行为通过事件触发
3. 事件处理统一在一个地方

---

## 八、对比：冗余代码 vs 原子组合

### ❌ 冗余写法（ai_system.py 现状）
```python
def _enqueue_farmer(self, npc, buildings, world_map):
    farm = self._find_building(buildings, 'FARM')
    if not farm:
        tx, ty = world_map.get_random_pos()
        npc.set_movement_target(tx, ty, "找农场")
        npc.state = STATE_MOVING
        return
    
    dist = math.hypot(npc.rect.centerx - farm.rect.centerx, ...)
    if dist > 60:
        npc.set_movement_target(farm.rect.centerx, farm.rect.centery, "去农场")
        npc.state = STATE_MOVING
    else:
        npc.state = STATE_WORKING
        # ... 更多逻辑
```

### ✅ 原子组合写法
```python
class FarmerBehavior(BaseJobBehavior):
    def execute(self, npc, context):
        farm = self.find_building_by_type(context['all_buildings'], 'FARM')
        if not farm:
            self.enqueue_roam(npc, context['world_map'].city_rect, reason="找农场")
            return True
        
        if not self.is_at_building(npc, farm):
            self.enqueue_move_to_building(npc, farm, "去农场")
            return True
        
        self.enqueue_wait(npc, 2000, "耕作")
        return True
```

---

---

## 九、现有行为完整映射

### 当前 ai_system.py 中的 22 个 _enqueue_xxx 方法

| 方法 | 归属 | 迁移目标 | 原子行为组合 |
|------|------|----------|--------------|
| `_enqueue_combat` | 通用 | `combat_ai.py` | `Combat(target)` |
| `_enqueue_rescue` | 通用 | `base.py` 辅助方法 | `Rescue(patient, clinic)` |
| `_enqueue_spectate` | 通用 | `spectate_ai.py` | `Spectate(cx, cy)` |
| `_enqueue_follow_player` | 指令 | `base.py` 辅助方法 | `FollowTarget(player, keep_follow=True)` |
| `_enqueue_survival` | 通用 | `base.py` 辅助方法 | `MoveToPosition(market)` → `Wait` |
| `_enqueue_farmer` | 职业 | `farmer.py` | 见下 |
| `_enqueue_merchant` | 职业 | `merchant.py` | 见下 |
| `_enqueue_bandit` | 职业 | `bandit.py` | 见下 |
| `_enqueue_villain` | 职业 | `bandit.py` | 见下 |
| `_enqueue_scholar` | 职业 | `scholar.py` | 见下 |
| `_enqueue_official` | 职业 | 新增 `official.py` | 见下 |
| `_enqueue_monk` | 职业 | 新增 `monk.py` | 见下 |
| `_enqueue_guard` | 职业 | `guard.py` | 见下 |
| `_enqueue_artisan` | 职业 | `artisan.py` | 见下 |
| `_enqueue_dancer` | 职业 | 新增 `dancer.py` | 见下 |
| `_enqueue_refugee` | 职业 | 新增 `refugee.py` | 见下 |
| `_enqueue_patrol` | 组织 | `guard.py` | `MoveToPosition` → `Wait` 循环 |
| `_enqueue_bodyguard` | 组织 | `guard.py` | `FollowTarget(leader, keep_follow=True)` |
| `_enqueue_member_follow` | 组织 | `base.py` | `FollowTarget(leader)` |
| `_enqueue_org_rally` | 组织 | `organization_ai.py` | `MoveToPosition(rally_point)` |
| `_enqueue_leader_recruit` | 组织 | `organization_ai.py` | `Roam` / `MoveToPosition` |
| `_enqueue_production` | 工作 | `base.py` 辅助方法 | `MoveToBuilding` → `Wait(工作)` |

---

### 职业行为详细映射

#### 农民 (FarmerBehavior)

```python
class FarmerBehavior(BaseJobBehavior):
    """
    农民行为逻辑
    social_level 4-5 (地主): 巡视为主
    social_level 2-3 (佃户): 正常农事
    social_level 1   (雇农): 干活为主
    """
    
    def execute(self, npc, context):
        # 已有行为在执行
        if self.has_pending_action(npc):
            return True
        
        level = self.get_social_level(npc)
        
        # 地主：巡视/休息
        if level >= 4:
            return self._landlord_behavior(npc, context)
        
        # 有粮食 → 去卖
        if npc.inventory.get(ITEM_GRAIN, 0) >= 3:
            market = self.find_building_by_type(context['all_buildings'], 'MARKET')
            if market:
                npc.action_queue.enqueue(MoveToPosition(market.rect.centerx, market.rect.centery, reason="运粮去卖"))
                npc.action_queue.enqueue(Wait(1500, reason="交易"))
                return True
        
        # 去农场工作
        farm = self.find_building_by_type(context['all_buildings'], 'FARM')
        if farm:
            npc.action_queue.enqueue(MoveToBuilding(farm, reason="干活"))
            return True
        
        # 找不到农场 → 漫游
        npc.action_queue.enqueue(Roam(context['world_map'].city_rect, reason="找农场"))
        return True
```

#### 商人 (MerchantBehavior)

```python
class MerchantBehavior(BaseJobBehavior):
    """
    商人行为逻辑
    social_level 4-5 (大商贾): 坐镇店铺、巡视产业
    social_level 2-3 (掌柜): 经营店铺、进货
    social_level 1   (伙计): 跑腿送货、叫卖
    """
    
    def execute(self, npc, context):
        if self.has_pending_action(npc):
            return True
        
        level = self.get_social_level(npc)
        
        # 大商贾
        if level >= 4:
            return self._boss_behavior(npc, context)
        
        # 掌柜
        if level >= 2:
            return self._manager_behavior(npc, context)
        
        # 伙计：跑腿
        return self._runner_behavior(npc, context)
    
    def _manager_behavior(self, npc, context):
        market = self.find_building_by_type(context['all_buildings'], 'MARKET')
        if market and not self.is_at_building(npc, market):
            npc.action_queue.enqueue(MoveToBuilding(market, reason="去店铺"))
            return True
        npc.action_queue.enqueue(Wait(3000, reason="经营店铺"))
        return True
```

#### 山贼 (BanditBehavior)

```python
class BanditBehavior(BaseJobBehavior):
    """
    山贼行为逻辑
    social_level 4-5 (山大王): 山寨坐镇
    social_level 2-3 (头目): 带队侦察
    social_level 1   (喽啰): 埋伏打劫
    """
    
    def execute(self, npc, context):
        if self.has_pending_action(npc):
            return True
        
        level = self.get_social_level(npc)
        world_map = context['world_map']
        
        # 山大王：坐镇
        if level >= 4:
            return self._boss_behavior(npc, world_map)
        
        # 头目：侦察
        if level >= 2:
            return self._captain_behavior(npc, world_map)
        
        # 喽啰：打劫
        return self._grunt_behavior(npc, context)
    
    def _grunt_behavior(self, npc, context):
        world_map = context['world_map']
        nearby = context.get('all_npcs', [])
        
        # 查找猎物
        prey = self._find_prey(npc, nearby)
        if prey:
            # 积累仇恨（触发战斗）
            npc.hatred[prey.id] = npc.hatred.get(prey.id, 0) + 15
            npc.action_queue.enqueue(Wait(500, reason=f"盯上{prey.name[:4]}"))
            return True
        
        # 在城外埋伏
        if world_map.slum_rect.collidepoint(npc.rect.center):
            npc.action_queue.enqueue(Wait(3000, reason="埋伏等待"))
        else:
            npc.action_queue.enqueue(Roam(world_map.slum_rect, reason="巡视地盘"))
        return True
```

#### 守卫 (GuardBehavior)

```python
class GuardBehavior(BaseJobBehavior):
    """
    守卫行为逻辑
    - BODYGUARD角色：贴身护卫领导
    - 普通守卫：巡逻/站岗
    """
    
    def execute(self, npc, context):
        if self.has_pending_action(npc):
            return True
        
        # 护卫模式
        org_role = getattr(npc, 'org_role', None)
        if org_role == 'BODYGUARD':
            return self._bodyguard_behavior(npc, context)
        
        # 普通巡逻
        return self._patrol_behavior(npc, context)
    
    def _bodyguard_behavior(self, npc, context):
        leader = self._find_leader(npc, context['all_npcs'])
        if not leader:
            return self._patrol_behavior(npc, context)
        
        npc.action_queue.enqueue(FollowTarget(
            target=leader,
            radius=70,
            keep_follow=True,
            reason=f"护卫{leader.name}"
        ))
        return True
    
    def _patrol_behavior(self, npc, context):
        world_map = context['world_map']
        
        # 初始化巡逻路线
        if not hasattr(npc, 'patrol_route') or not npc.patrol_route:
            npc.patrol_route = self._generate_patrol_route(world_map, 4)
            npc.patrol_index = 0
        
        idx = npc.patrol_index % len(npc.patrol_route)
        tx, ty = npc.patrol_route[idx]
        
        npc.action_queue.enqueue(MoveToPosition(tx, ty, reason=f"巡逻({idx+1}/{len(npc.patrol_route)})"))
        if random.random() < 0.3:
            npc.action_queue.enqueue(Wait(random.randint(1000, 3000), reason="巡逻驻足"))
        
        npc.patrol_index = (idx + 1) % len(npc.patrol_route)
        return True
```

#### 学者 (ScholarBehavior)

```python
class ScholarBehavior(BaseJobBehavior):
    """
    学者行为逻辑
    social_level 4-5 (大儒): 讲学/著书
    social_level 2-3 (先生): 教书/访友
    social_level 1   (书生): 读书/赶考
    """
    
    def execute(self, npc, context):
        if self.has_pending_action(npc):
            return True
        
        level = self.get_social_level(npc)
        
        if level >= 4:
            return self._master_behavior(npc, context)
        if level >= 2:
            return self._teacher_behavior(npc, context)
        return self._student_behavior(npc, context)
    
    def _student_behavior(self, npc, context):
        # 去书院读书
        academy = self.find_building_by_type(context['all_buildings'], 'ACADEMY')
        if academy:
            npc.action_queue.enqueue(MoveToBuilding(academy, reason="去书院"))
            return True
        
        # 没有书院 → 在茶馆读书
        teahouse = self.find_building_by_type(context['all_buildings'], 'TEAHOUSE')
        if teahouse:
            npc.action_queue.enqueue(MoveToBuilding(teahouse, reason="茶馆读书"))
            return True
        
        npc.action_queue.enqueue(Roam(context['world_map'].city_rect, reason="散步"))
        return True
```

---

### 通用行为（保留在 AISystem 或迁移到 base.py）

#### 战斗 (combat_ai.py)

```python
def enqueue_combat(npc, target, combat_manager):
    """入队战斗行为"""
    current = npc.action_queue.current
    if current and isinstance(current, Combat) and current.target == target:
        return  # 已在战斗
    
    npc.action_queue.clear()
    npc.action_queue.enqueue(Combat(target, combat_manager, reason=f"与{target.name}战斗"))
```

#### 救援 (base.py 辅助方法)

```python
def enqueue_rescue(self, npc, patient, clinic):
    """入队救援行为"""
    npc.action_queue.clear()
    npc.action_queue.enqueue(Rescue(patient, clinic, reason=f"救援{patient.name}"))
    npc._rescue_target_id = patient.id
```

#### 围观 (spectate_ai.py)

```python
def enqueue_spectate(npc, center_x, center_y):
    """入队围观行为"""
    npc.action_queue.clear()
    npc.action_queue.enqueue(Spectate(center_x, center_y, npc.id, reason="围观"))
```

#### 跟随玩家

```python
def enqueue_follow_player(npc, player):
    """入队跟随玩家"""
    npc.action_queue.clear()
    npc.action_queue.enqueue(FollowTarget(
        target=player,
        stop_dist=70,
        start_dist=110,
        radius=90,
        angle=random.uniform(0, 2 * math.pi),
        keep_follow=True,
        reason="跟随中"
    ))
```

---

## 十、重构执行计划

### Phase 1: 补充原子行为 (atomic_actions.py)

新增：
- [ ] `LookAt` - 面向目标（用于交互前）
- [ ] `Say` - 显示气泡对话

### Phase 2: 完善职业行为 (job_behaviors/)

- [ ] 确保所有职业都有 Behavior 类
- [ ] 新增: `official.py`, `monk.py`, `dancer.py`, `refugee.py`
- [ ] 迁移 ai_system.py 中对应的 `_enqueue_xxx` 逻辑

### Phase 3: 新增模块

- [ ] `ai/combat_ai.py` - 战斗相关（仇恨/锁定/Combat行为）
- [ ] `ai/spectate_ai.py` - 围观逻辑（已有）
- [ ] `ai/organization_ai.py` - 组织行为（集结/招募）

### Phase 4: 精简 ai_system.py

删除所有 `_enqueue_xxx` 方法，只保留：
- [ ] `update()` - 主循环
- [ ] `_process_events()` - 事件处理
- [ ] `_process_see()` - 视觉感知
- [ ] `_decide_behavior()` - 决策分发（改为调用 job_registry）
- [ ] `_find_enemy()` / `_is_villain()` - 辅助判断

### Phase 5: 测试验证

- [ ] 确保所有职业行为正常
- [ ] 确保战斗/救援/围观正常
- [ ] 确保组织行为正常

---

## 确认清单

请确认以下问题后开始执行：

- [ ] 是否同意以上职业行为映射？
- [ ] 是否需要调整某些行为的优先级？
- [ ] 是否有特殊的边界情况需要保留？
- [ ] 是否希望分阶段执行还是一次性完成？
