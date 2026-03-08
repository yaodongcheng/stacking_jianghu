# --- src/atomic_actions.py ---
"""
原子行为系统 - 汴京沙盒
所有NPC行为都是以下原子行为的组合：

移动类：
- MoveToPosition: 移动到指定坐标（支持极坐标偏移）
- FollowTarget: 跟随某个Card（支持极坐标偏移、威胁响应）

堆叠类：
- CarryTarget: 背起目标
- DropTarget: 放下目标  
- StackOn: 堆叠到目标
- Unstack: 取消堆叠

其他：
- Wait: 等待
- Stay: 原地驻守
"""

import math
import random
from abc import ABC, abstractmethod
from src.ai.constants import SPECTATE_RADIUS_MIN, SPECTATE_RADIUS_MAX
from src.utils import log_game_event


class AtomicAction(ABC):
    """原子行为基类"""
    
    def __init__(self):
        self.finished = False
    
    @abstractmethod
    def on_start(self, agent): pass
    
    @abstractmethod  
    def on_tick(self, agent, dt_ms: float) -> bool:
        """返回False表示完成"""
        pass
    
    def on_end(self, agent): pass


# ═══════════════════════════════════════════════════════════════════
# 移动类
# ═══════════════════════════════════════════════════════════════════

class MoveToPosition(AtomicAction):
    """移动到坐标，支持极坐标偏移"""
    
    def __init__(self, x, y, stop_dist=15, radius=0, angle=0, reason="移动", timeout=None, state_override=None):
        # 使用definitions中的超时常量作为默认值
        from src.definitions import TIMEOUT_NPC_MOVE_MS
        if timeout is None:
            timeout = TIMEOUT_NPC_MOVE_MS
        super().__init__()
        # 应用极坐标偏移
        self.tx = x + math.cos(angle) * radius if radius else x
        self.ty = y + math.sin(angle) * radius if radius else y
        self.stop_dist = stop_dist
        self.reason = reason
        self.timeout = timeout
        self.elapsed = 0
        self.state_override = state_override  # 可选：强制使用指定状态（如 STATE_CARRYING）
    
    def on_start(self, agent):
        from src.definitions import STATE_MOVING
        agent.set_movement_target(self.tx, self.ty, self.reason)
        agent.state = self.state_override if self.state_override else STATE_MOVING
        agent.ai_reason = self.reason
    
    def on_tick(self, agent, dt_ms):
        self.elapsed += dt_ms
        if self.elapsed > self.timeout:
            self.finished = True
            return False
        dist = math.hypot(agent.rect.centerx - self.tx, agent.rect.centery - self.ty)
        if dist <= self.stop_dist:
            self.finished = True
            return False
        return True
    
    def on_end(self, agent):
        from src.definitions import STATE_IDLE
        agent.state = STATE_IDLE
        agent.clear_movement_target("MoveToPosition完成")


class FollowTarget(AtomicAction):
    """
    跟随目标Card
    - radius/angle: 极坐标偏移（相对目标位置）
    - stop_dist/start_dist: 停止/启动距离（形成死区防抖动）
    - keep_follow: True=持续跟随，False=到位即完成
    - threat_response: True=根据威胁动态调整距离（护卫模式）
    """
    
    def __init__(self, target, stop_dist=60, start_dist=90, 
                 radius=0, angle=0, keep_follow=True,
                 threat_response=False, reason="跟随"):
        super().__init__()
        self.target = target
        self.stop_dist = stop_dist
        self.start_dist = start_dist
        self.radius = radius
        self.angle = angle
        self.keep_follow = keep_follow
        self.threat_response = threat_response
        self.reason = reason
        self._moving = False
        self._timer = 0
    
    def _get_ideal_pos(self):
        tx, ty = self.target.rect.centerx, self.target.rect.centery
        if self.radius:
            return tx + math.cos(self.angle) * self.radius, ty + math.sin(self.angle) * self.radius
        return tx, ty
    
    def on_start(self, agent):
        agent.ai_reason = self.reason
    
    def on_tick(self, agent, dt_ms):
        from src.definitions import STATE_MOVING, STATE_IDLE, SAFETY_DEAD, SAFETY_EXILED
        
        # 目标失效
        if not self.target or getattr(self.target, 'safety', None) in [SAFETY_DEAD, SAFETY_EXILED]:
            self.finished = True
            return False
        
        ix, iy = self._get_ideal_pos()
        dist = math.hypot(agent.rect.centerx - ix, agent.rect.centery - iy)
        
        if self._moving:
            if dist <= self.stop_dist:
                self._moving = False
                agent.state = STATE_IDLE
                agent.clear_movement_target("跟随到位")
                if not self.keep_follow:
                    self.finished = True
                    return False
            else:
                self._timer += dt_ms
                if self._timer > 200:  # 200ms更新一次
                    self._timer = 0
                    agent.set_movement_target(ix, iy, self.reason)
        else:
            if dist > self.start_dist:
                self._moving = True
                agent.state = STATE_MOVING
                agent.set_movement_target(ix, iy, self.reason)
        
        return True


# ═══════════════════════════════════════════════════════════════════
# 堆叠类
# ═══════════════════════════════════════════════════════════════════

class CarryTarget(AtomicAction):
    """背起目标"""
    def __init__(self, target, reason="背起"):
        super().__init__()
        self.target = target
        self.reason = reason
    
    def on_start(self, agent):
        from src.definitions import STATE_CARRYING, STACK_OFFSET_Y, SAFETY_DOWNED
        if self.target.safety != SAFETY_DOWNED or self.target.stack_parent:
            self.finished = True
            return
        self.target.stack_parent = agent
        agent.stack_child = self.target
        self.target.set_pos(agent.rect.centerx, agent.rect.centery + STACK_OFFSET_Y)
        agent.state = STATE_CARRYING
        agent.ai_reason = self.reason
        self.finished = True
    
    def on_tick(self, agent, dt_ms): return False


class DropTarget(AtomicAction):
    """放下背负的目标"""
    def __init__(self, offset_x=60, offset_y=0, reason="放下"):
        super().__init__()
        self.ox, self.oy = offset_x, offset_y
        self.reason = reason
    
    def on_start(self, agent):
        from src.definitions import STATE_IDLE
        if not agent.stack_child:
            self.finished = True
            return
        t = agent.stack_child
        agent.stack_child = None
        t.stack_parent = None
        t.set_pos(agent.rect.centerx + self.ox, agent.rect.centery + self.oy)
        agent.state = STATE_IDLE
        agent.ai_reason = self.reason
        self.finished = True
    
    def on_tick(self, agent, dt_ms): return False


class StackOn(AtomicAction):
    """堆叠到目标上"""
    def __init__(self, target, reason="堆叠"):
        super().__init__()
        self.target = target
        self.reason = reason
    
    def on_start(self, agent):
        from src.definitions import STACK_OFFSET_Y
        last = self.target
        for _ in range(20):
            if not last.stack_child: break
            last = last.stack_child
        last.stack_child = agent
        agent.stack_parent = last
        agent.set_pos(last.rect.centerx, last.rect.centery + STACK_OFFSET_Y)
        agent.ai_reason = self.reason
        self.finished = True
    
    def on_tick(self, agent, dt_ms): return False


class Unstack(AtomicAction):
    """取消堆叠"""
    def __init__(self, bounce_dist=30, reason="离开"):
        super().__init__()
        self.dist = bounce_dist
        self.reason = reason
    
    def on_start(self, agent):
        if agent.stack_parent:
            agent.bounce_off(agent.stack_parent, distance=self.dist)
        agent.ai_reason = self.reason
        self.finished = True
    
    def on_tick(self, agent, dt_ms): return False


# ═══════════════════════════════════════════════════════════════════
# 其他
# ═══════════════════════════════════════════════════════════════════

class Wait(AtomicAction):
    """等待指定时间"""
    def __init__(self, duration_ms, reason="等待"):
        super().__init__()
        self.duration = duration_ms
        self.elapsed = 0
        self.reason = reason
    
    def on_start(self, agent):
        from src.definitions import STATE_IDLE
        agent.state = STATE_IDLE
        agent.ai_reason = self.reason
    
    def on_tick(self, agent, dt_ms):
        self.elapsed += dt_ms
        if self.elapsed >= self.duration:
            self.finished = True
            return False
        return True


class Stay(AtomicAction):
    """原地驻守（永不自动结束）"""
    def __init__(self, reason="驻守"):
        super().__init__()
        self.reason = reason
    
    def on_start(self, agent):
        from src.definitions import STATE_IDLE
        agent.state = STATE_IDLE
        agent.clear_movement_target("Stay")
        agent.ai_reason = self.reason
    
    def on_tick(self, agent, dt_ms): return True  # 永远继续


class Roam(AtomicAction):
    """在指定区域随机漫步"""
    def __init__(self, zone_rect, duration_ms=5000, reason="散步"):
        super().__init__()
        self.zone_rect = zone_rect
        self.duration = duration_ms
        self.elapsed = 0
        self.reason = reason
        self.tx, self.ty = None, None
    
    def on_start(self, agent):
        from src.definitions import STATE_MOVING
        # 在区域内随机选点
        self.tx = random.randint(self.zone_rect.left + 20, self.zone_rect.right - 20)
        self.ty = random.randint(self.zone_rect.top + 20, self.zone_rect.bottom - 20)
        agent.set_movement_target(self.tx, self.ty, self.reason)
        agent.state = STATE_MOVING
        agent.ai_reason = self.reason
    
    def on_tick(self, agent, dt_ms):
        self.elapsed += dt_ms
        if self.elapsed >= self.duration:
            self.finished = True
            return False
        # 到达检查
        if self.tx and math.hypot(agent.rect.centerx - self.tx, agent.rect.centery - self.ty) < 15:
            self.finished = True
            return False
        return True
    
    def on_end(self, agent):
        from src.definitions import STATE_IDLE
        agent.state = STATE_IDLE


class MoveToBuilding(AtomicAction):
    """移动到建筑并堆叠上去开始工作"""
    def __init__(self, building, reason="去工作"):
        super().__init__()
        self.building = building
        self.reason = reason
        self._phase = 'MOVING'  # MOVING -> STACKING -> DONE
    
    def on_start(self, agent):
        from src.definitions import STATE_MOVING
        # 移动到建筑旁边
        tx = self.building.rect.centerx + self.building.rect.width // 2 + 10
        ty = self.building.rect.centery
        agent.set_movement_target(tx, ty, self.reason)
        agent.set_target_obj(self.building, self.reason)
        agent.state = STATE_MOVING
        agent.ai_reason = self.reason
    
    def on_tick(self, agent, dt_ms):
        from src.definitions import STATE_WORKING, STACK_OFFSET_Y
        
        if self._phase == 'MOVING':
            # 检查是否到达
            dist = math.hypot(agent.rect.centerx - self.building.rect.centerx,
                             agent.rect.centery - self.building.rect.centery)
            if dist < 60:
                self._phase = 'STACKING'
        
        if self._phase == 'STACKING':
            # 执行堆叠
            if self.building.stack_child is None:
                self.building.stack_child = agent
                agent.stack_parent = self.building
                agent.set_pos(self.building.rect.centerx, 
                             self.building.rect.centery + STACK_OFFSET_Y)
                agent.state = STATE_WORKING
                agent.ai_reason = f"在{self.building.name}工作"
            self.finished = True
            return False
        
        return True


class Combat(AtomicAction):
    """战斗行为：追击目标并攻击"""
    def __init__(self, target, combat_manager, reason="战斗"):
        super().__init__()
        self.target = target
        self.combat_manager = combat_manager
        self.reason = reason
        self.face_dist = 55
        self.attack_range = 85
    
    def on_start(self, agent):
        from src.definitions import STATE_COMBAT
        agent.state = STATE_COMBAT
        agent.aggro_target = self.target
        agent.in_combat = True
        agent.ai_reason = self.reason
    
    def on_tick(self, agent, dt_ms):
        from src.definitions import STATE_COMBAT, STATE_IDLE, SAFETY_DEAD, SAFETY_DOWNED, SAFETY_EXILED
        
        # 目标失效
        if not self.target or self.target.safety in [SAFETY_DEAD, SAFETY_DOWNED, SAFETY_EXILED]:
            self.finished = True
            return False
        
        # 硬直中
        if agent.knockback_timer > 0:
            agent.state = STATE_COMBAT
            agent.ai_reason = "弹开中"
            return True
        
        dist = math.hypot(self.target.rect.centerx - agent.rect.centerx,
                         self.target.rect.centery - agent.rect.centery)
        
        # 计算站位点
        if dist > 0:
            dx = (agent.rect.centerx - self.target.rect.centerx) / dist
            dy = (agent.rect.centery - self.target.rect.centery) / dist
        else:
            dx, dy = 1.0, 0.0
        
        stand_x = self.target.rect.centerx + dx * self.face_dist
        stand_y = self.target.rect.centery + dy * self.face_dist
        
        if dist > self.attack_range:
            # 追击
            agent.state = STATE_COMBAT
            agent.ai_reason = f"追击{self.target.name}"
            agent.set_movement_target(stand_x, stand_y, f"追击{self.target.name}")
        else:
            # 攻击
            agent.state = STATE_COMBAT
            agent.clear_movement_target("战斗位置")
            agent.ai_reason = "战斗中"
            
            if agent.attack_cooldown <= 0:
                # 执行攻击
                nearby = getattr(agent, '_nearby_npcs_ref', [])
                self.combat_manager.apply_melee_attack(agent, self.target, nearby)
                agent.attack_cooldown = agent.atk_speed
        
        return True
    
    def on_end(self, agent):
        from src.definitions import STATE_IDLE
        agent.aggro_target = None
        agent.in_combat = False
        agent.state = STATE_IDLE
        agent.combat_anchor_x = None
        agent.combat_anchor_y = None


class LookAt(AtomicAction):
    """看向目标"""
    def __init__(self, target, duration_ms=500, reason="看向"):
        super().__init__()
        self.target = target
        self.duration = duration_ms
        self.elapsed = 0
        self.reason = reason
    
    def on_start(self, agent):
        from src.definitions import STATE_IDLE
        agent.state = STATE_IDLE
        agent.clear_movement_target("看向目标")
        agent.ai_reason = self.reason
        # 设置朝向（如果NPC有方向属性）
        if hasattr(agent, 'facing_dir') and self.target:
            dx = self.target.rect.centerx - agent.rect.centerx
            agent.facing_dir = 'right' if dx > 0 else 'left'
    
    def on_tick(self, agent, dt_ms):
        self.elapsed += dt_ms
        if self.elapsed >= self.duration:
            self.finished = True
            return False
        return True


class Say(AtomicAction):
    """说话（显示气泡）"""
    def __init__(self, text, duration_ms=2000, reason="说话"):
        super().__init__()
        self.text = text
        self.duration = duration_ms
        self.elapsed = 0
        self.reason = reason
    
    def on_start(self, agent):
        from src.definitions import STATE_IDLE
        agent.state = STATE_IDLE
        agent.ai_reason = self.text
        agent._salute_bubble = self.text
        agent._salute_bubble_timer = self.duration
    
    def on_tick(self, agent, dt_ms):
        self.elapsed += dt_ms
        if self.elapsed >= self.duration:
            self.finished = True
            return False
        return True
    
    def on_end(self, agent):
        agent._salute_bubble = None
        agent._salute_bubble_timer = 0


class Patrol(AtomicAction):
    """
    巡逻行为：在多个点之间循环移动
    """
    def __init__(self, waypoints, loop=True, stop_dist=30, reason="巡逻"):
        """
        Args:
            waypoints: [(x1,y1), (x2,y2), ...] 巡逻点列表
            loop: 是否循环巡逻
            stop_dist: 到达判定距离
        """
        super().__init__()
        self.waypoints = waypoints
        self.loop = loop
        self.stop_dist = stop_dist
        self.reason = reason
        self._current_idx = 0
    
    def on_start(self, agent):
        from src.definitions import STATE_MOVING
        if self.waypoints:
            tx, ty = self.waypoints[0]
            agent.set_movement_target(tx, ty, self.reason)
            agent.state = STATE_MOVING
        agent.ai_reason = self.reason
    
    def on_tick(self, agent, dt_ms):
        from src.definitions import STATE_MOVING, STATE_IDLE
        
        if not self.waypoints:
            self.finished = True
            return False
        
        tx, ty = self.waypoints[self._current_idx]
        dist = math.hypot(agent.rect.centerx - tx, agent.rect.centery - ty)
        
        if dist <= self.stop_dist:
            # 到达当前点，移动到下一个
            self._current_idx += 1
            if self._current_idx >= len(self.waypoints):
                if self.loop:
                    self._current_idx = 0
                else:
                    self.finished = True
                    agent.state = STATE_IDLE
                    return False
            
            tx, ty = self.waypoints[self._current_idx]
            agent.set_movement_target(tx, ty, self.reason)
            agent.state = STATE_MOVING
        
        return True
    
    def on_end(self, agent):
        from src.definitions import STATE_IDLE
        agent.state = STATE_IDLE


class Work(AtomicAction):
    """
    工作行为：在建筑上工作一段时间
    适用于：农民种地、工匠制作、商人经营等
    """
    def __init__(self, building, duration_ms=5000, produce_item=None, 
                 produce_amount=1, reason="工作"):
        """
        Args:
            building: 工作地点
            duration_ms: 工作时长
            produce_item: 生产的物品ID（可选）
            produce_amount: 生产数量
        """
        super().__init__()
        self.building = building
        self.duration = duration_ms
        self.produce_item = produce_item
        self.produce_amount = produce_amount
        self.reason = reason
        self.elapsed = 0
    
    def on_start(self, agent):
        from src.definitions import STATE_WORKING
        agent.state = STATE_WORKING
        agent.ai_reason = f"在{self.building.name}工作"
    
    def on_tick(self, agent, dt_ms):
        self.elapsed += dt_ms
        if self.elapsed >= self.duration:
            # 工作完成，生产物品
            if self.produce_item and hasattr(agent, 'inventory'):
                current = agent.inventory.get(self.produce_item, 0)
                agent.inventory[self.produce_item] = current + self.produce_amount
            self.finished = True
            return False
        return True
    
    def on_end(self, agent):
        from src.definitions import STATE_IDLE
        agent.state = STATE_IDLE


class Trade(AtomicAction):
    """
    交易行为：与建筑或NPC进行交易
    """
    def __init__(self, target, sell_item=None, sell_amount=0, 
                 buy_item=None, buy_amount=0, reason="交易"):
        """
        Args:
            target: 交易对象（建筑或NPC）
            sell_item: 卖出的物品ID
            sell_amount: 卖出数量
            buy_item: 买入的物品ID
            buy_amount: 买入数量
        """
        super().__init__()
        self.target = target
        self.sell_item = sell_item
        self.sell_amount = sell_amount
        self.buy_item = buy_item
        self.buy_amount = buy_amount
        self.reason = reason
    
    def on_start(self, agent):
        from src.definitions import STATE_IDLE, ITEM_COIN
        agent.state = STATE_IDLE
        agent.ai_reason = self.reason
        
        # 执行交易
        if self.sell_item and hasattr(agent, 'inventory'):
            # 卖出物品
            current = agent.inventory.get(self.sell_item, 0)
            actual_sell = min(current, self.sell_amount)
            if actual_sell > 0:
                agent.inventory[self.sell_item] = current - actual_sell
                # 获得金钱（简单定价：1单位=5铜钱）
                price = actual_sell * 5
                agent.inventory[ITEM_COIN] = agent.inventory.get(ITEM_COIN, 0) + price
                agent._salute_bubble = f"卖出{actual_sell}个，得{price}铜"
                agent._salute_bubble_timer = 1500
        
        self.finished = True
    
    def on_tick(self, agent, dt_ms):
        return False


class Flee(AtomicAction):
    """
    逃跑行为：远离威胁
    """
    def __init__(self, threat, flee_distance=300, reason="逃跑"):
        """
        Args:
            threat: 威胁对象
            flee_distance: 逃跑距离
        """
        super().__init__()
        self.threat = threat
        self.flee_distance = flee_distance
        self.reason = reason
        self.elapsed = 0
    
    def on_start(self, agent):
        from src.definitions import STATE_MOVING
        # 计算逃跑方向（远离威胁）
        dx = agent.rect.centerx - self.threat.rect.centerx
        dy = agent.rect.centery - self.threat.rect.centery
        dist = max(1, math.hypot(dx, dy))
        
        # 逃跑目标点
        tx = agent.rect.centerx + (dx / dist) * self.flee_distance
        ty = agent.rect.centery + (dy / dist) * self.flee_distance
        
        agent.set_movement_target(tx, ty, self.reason)
        agent.state = STATE_MOVING
        agent.ai_reason = "逃命中！"
    
    def on_tick(self, agent, dt_ms):
        from src.definitions import SAFETY_DEAD, SAFETY_DOWNED
        self.elapsed += dt_ms
        
        # 威胁消失或足够远
        if self.threat.safety in [SAFETY_DEAD, SAFETY_DOWNED]:
            self.finished = True
            return False
        
        dist = math.hypot(agent.rect.centerx - self.threat.rect.centerx,
                         agent.rect.centery - self.threat.rect.centery)
        if dist > self.flee_distance:
            self.finished = True
            return False
        
        # 超时保护
        if self.elapsed > 10000:
            self.finished = True
            return False
        
        return True
    
    def on_end(self, agent):
        from src.definitions import STATE_IDLE
        agent.state = STATE_IDLE
        agent.clear_movement_target("逃跑结束")
        agent.ai_reason = "喘息中"


class Rally(AtomicAction):
    """
    集结行为：移动到指定集结点
    用于组织联动时的集结响应
    """
    def __init__(self, x, y, duration_ms=10000, reason="集结"):
        super().__init__()
        self.tx = x
        self.ty = y
        self.duration = duration_ms
        self.reason = reason
        self.elapsed = 0
    
    def on_start(self, agent):
        from src.definitions import STATE_MOVING
        agent.set_movement_target(self.tx, self.ty, self.reason)
        agent.state = STATE_MOVING
        agent.ai_reason = self.reason
    
    def on_tick(self, agent, dt_ms):
        from src.definitions import STATE_IDLE
        self.elapsed += dt_ms
        
        dist = math.hypot(agent.rect.centerx - self.tx, agent.rect.centery - self.ty)
        if dist < 50:
            agent.state = STATE_IDLE
            agent.clear_movement_target("集结到位")
            agent.ai_reason = "戒备中"
            self.finished = True
            return False
        
        if self.elapsed > self.duration:
            self.finished = True
            return False
        
        return True


class Spectate(AtomicAction):
    """围观行为：移动到围观位并驻足
    
    改进：使用网格系统检查NPC重叠和障碍物
    """
    # 使用统一常量（来自 src/ai/constants.py）
    
    def __init__(self, center_x, center_y, npc_id, reason="围观"):
        super().__init__()
        self.cx, self.cy = center_x, center_y
        self.npc_id = npc_id
        self.reason = reason
        self.target_x, self.target_y = None, None  # 延迟到on_start计算
    
    def _calc_spectate_pos(self, agent):
        """计算围观站位（黄金角避免扎堆）
        
        改进：使用网格系统检查NPC重叠和障碍物
        """
        id_angle_base = (self.npc_id * 137.5) % 360
        layer = self.npc_id % 5
        r_base = SPECTATE_RADIUS_MIN + layer * 32
        
        # 获取世界地图和网格系统
        world_map = getattr(agent, '_world_map_ref', None)
        occupancy_grid = None
        try:
            # 尝试通过agent获取网格系统
            if hasattr(agent, '_game_ref') and hasattr(agent._game_ref, 'movement_system'):
                occupancy_grid = agent._game_ref.movement_system.occupancy_grid
        except Exception as e:
            log_game_event(f"[Spectate] 无法获取网格系统: {e}", tag="GRID")
        
        target_x, target_y = None, None
        
        # 尝试8个角度找到合适位置
        for attempt in range(8):
            angle = math.radians(id_angle_base + attempt * 45) + random.uniform(-0.15, 0.15)
            r = r_base + random.randint(0, 20)
            tx = self.cx + math.cos(angle) * r
            ty = self.cy + math.sin(angle) * r
            
            # 检查障碍物
            if world_map:
                test_rect = agent.rect.copy()
                test_rect.center = (int(tx), int(ty))
                if world_map.is_blocked(test_rect):
                    continue
            
            # 检查网格占用
            if occupancy_grid is not None:
                gx, gy = occupancy_grid.world_to_grid(tx, ty)
                if not occupancy_grid.is_available(gx, gy, exclude_npc_id=self.npc_id):
                    # 尝试找附近空闲位置
                    free_x, free_y = occupancy_grid.find_free_position(tx, ty, exclude_npc_id=self.npc_id)
                    dist_to_center = math.hypot(free_x - self.cx, free_y - self.cy)
                    if dist_to_center > SPECTATE_RADIUS_MAX + 50:
                        continue
                    tx, ty = free_x, free_y
            
            target_x, target_y = tx, ty
            break
        
        # 兜底：使用默认位置
        if target_x is None:
            default_x = self.cx + math.cos(math.radians(id_angle_base)) * r_base
            default_y = self.cy + math.sin(math.radians(id_angle_base)) * r_base
            if occupancy_grid is not None:
                target_x, target_y = occupancy_grid.find_free_position(
                    default_x, default_y, exclude_npc_id=self.npc_id
                )
            else:
                target_x, target_y = default_x, default_y
        
        return target_x, target_y
    
    def on_start(self, agent):
        from src.definitions import STATE_MOVING
        # 延迟计算位置，这样可以访问agent和网格系统
        self.target_x, self.target_y = self._calc_spectate_pos(agent)
        agent.set_movement_target(self.target_x, self.target_y, self.reason)
        agent.state = STATE_MOVING
        agent.ai_reason = self.reason
        agent.spectate_src_x = self.cx
        agent.spectate_src_y = self.cy
    
    def on_tick(self, agent, dt_ms):
        from src.definitions import STATE_IDLE
        # 到达检查
        dist = math.hypot(agent.rect.centerx - self.target_x, agent.rect.centery - self.target_y)
        if dist < 30:
            agent.state = STATE_IDLE
            agent.clear_movement_target("围观到位")
            agent.ai_reason = "围观中"
            agent.spectate_anchor_set = True
            # 围观行为持续直到被打断
            return True
        return True
    
    def on_end(self, agent):
        agent.spectate_src_x = None
        agent.spectate_src_y = None
        agent.spectate_anchor_set = False


class Rescue(AtomicAction):
    """救援行为：移动到伤员 -> 背起 -> 送医馆 -> 放下"""
    def __init__(self, patient, clinic, reason="救援"):
        super().__init__()
        self.patient = patient
        self.clinic = clinic
        self.reason = reason
        self._phase = 'APPROACH'  # APPROACH -> CARRY -> DELIVER -> DROP
    
    def on_start(self, agent):
        from src.definitions import STATE_MOVING
        agent.set_movement_target(self.patient.rect.centerx, self.patient.rect.centery, f"救援{self.patient.name}")
        agent.state = STATE_MOVING
        agent.ai_reason = f"救援{self.patient.name}"
        agent._rescue_target_id = self.patient.id
    
    def on_tick(self, agent, dt_ms):
        from src.definitions import STATE_MOVING, STATE_CARRYING, STATE_IDLE, STACK_OFFSET_Y, SAFETY_DOWNED
        
        if self._phase == 'APPROACH':
            # 检查伤员是否还需要救
            if self.patient.stack_parent or self.patient.safety != SAFETY_DOWNED:
                self.finished = True
                return False
            
            dist = math.hypot(agent.rect.centerx - self.patient.rect.centerx,
                             agent.rect.centery - self.patient.rect.centery)
            
            # [修复] 增加容错：放宽接近阈值到 60px，避免因路径问题卡在边缘
            # [逻辑] 如果距离在60~100px之间且NPC已停止移动，也强制进入CARRY
            is_stopped = (agent.target_x is None or 
                         (hasattr(agent, 'state') and agent.state not in [STATE_MOVING, STATE_CARRYING]))
            
            if dist < 60 or (dist < 100 and is_stopped):
                self._phase = 'CARRY'
                # [修复] 如果距离稍远但要强制背起，先把救援者移近一点
                if dist >= 40:
                    # 把救援者吸附到伤员旁边
                    offset_x = 30 if agent.rect.centerx < self.patient.rect.centerx else -30
                    agent.set_pos(self.patient.rect.centerx + offset_x, self.patient.rect.centery, "救援吸附")
        
        elif self._phase == 'CARRY':
            # 背起伤员
            if self.patient.stack_parent or agent.stack_child:
                self.finished = True
                return False
            self.patient.stack_parent = agent
            agent.stack_child = self.patient
            self.patient.set_pos(agent.rect.centerx, agent.rect.centery + STACK_OFFSET_Y)
            agent.state = STATE_CARRYING
            agent.ai_reason = f"背着{self.patient.name}送医"
            self._phase = 'DELIVER'
            if self.clinic:
                agent.set_movement_target(self.clinic.rect.centerx, self.clinic.rect.centery, f"送往医馆")
        
        elif self._phase == 'DELIVER':
            if not self.clinic:
                self._phase = 'DROP'
                return True
            dist = math.hypot(agent.rect.centerx - self.clinic.rect.centerx,
                             agent.rect.centery - self.clinic.rect.centery)
            if dist < 60:
                self._phase = 'DROP'
        
        elif self._phase == 'DROP':
            # 放下伤员
            patient = agent.stack_child
            if patient:
                agent.stack_child = None
                patient.stack_parent = None
                if self.clinic:
                    # 堆叠到医馆
                    last = self.clinic
                    for _ in range(20):
                        if not last.stack_child: break
                        last = last.stack_child
                    last.stack_child = patient
                    patient.stack_parent = last
                    patient.set_pos(last.rect.centerx, last.rect.centery + STACK_OFFSET_Y)
                else:
                    patient.set_pos(agent.rect.centerx + 60, agent.rect.centery)
            agent.state = STATE_IDLE
            agent.ai_reason = "救援完成"
            self.finished = True
            return False
        
        return True
    
    def on_end(self, agent):
        agent._rescue_target_id = None
        agent._is_rescuing = False


# ═══════════════════════════════════════════════════════════════════
# 礼仪系统原子行为
# ═══════════════════════════════════════════════════════════════════

class Salute(AtomicAction):
    """
    行礼行为 - 低阶层NPC看到高阶层NPC时触发
    
    流程：
    1. 停下当前动作
    2. 侧移让路（如果在对方前进路上）
    3. 显示行礼气泡
    4. 短暂等待
    5. 恢复原行为
    """
    
    # 根据阶层差距的行礼台词
    SALUTE_TEXTS = {
        # (我方类型, 对方类型, 阶层差) → 台词列表
        ('COMMONER', 'OFFICIAL', 2): ["见过大人", "大人好", "小的有礼了"],
        ('COMMONER', 'OFFICIAL', 3): ["参见大人！", "小民叩见大人", "大人万福"],
        ('COMMONER', 'NOBLE', 2): ["见过老爷", "老爷好", "小的这厢有礼了"],
        ('COMMONER', 'NOBLE', 3): ["参见老爷！", "给老爷请安"],
        ('MERCHANT', 'OFFICIAL', 2): ["大人，您来了", "见过大人"],
        ('MERCHANT', 'OFFICIAL', 3): ["大人驾到！恕小人有失远迎"],
        ('BANDIT', 'GUARD', 1): ["...", "（避开视线）", "我没干坏事..."],
        ('DEFAULT', 'DEFAULT', 2): ["您好", "有礼了"],
        ('DEFAULT', 'DEFAULT', 3): ["见过贵人", "贵人有礼"],
    }
    
    def __init__(self, target, my_level, target_level, my_type='DEFAULT', target_type='DEFAULT', 
                 duration_ms=1500, dodge_distance=40, reason="行礼"):
        """
        Args:
            target: 行礼对象
            my_level: 本NPC社会等级
            target_level: 对方社会等级
            my_type: 本NPC类型 (COMMONER/MERCHANT/BANDIT/GUARD等)
            target_type: 对方类型 (OFFICIAL/NOBLE/GUARD等)
            duration_ms: 行礼持续时间
            dodge_distance: 侧移距离
        """
        super().__init__()
        self.target = target
        self.my_level = my_level
        self.target_level = target_level
        self.my_type = my_type
        self.target_type = target_type
        self.duration = duration_ms
        self.dodge_distance = dodge_distance
        self.reason = reason
        self.elapsed = 0
        self._phase = 'DODGE'  # DODGE → SALUTE → WAIT → DONE
        self._original_target_x = None
        self._original_target_y = None
        self._salute_text = None
    
    def _get_salute_text(self):
        """根据类型和阶层差获取行礼台词"""
        level_diff = self.target_level - self.my_level
        
        # 尝试精确匹配
        key = (self.my_type, self.target_type, level_diff)
        if key in self.SALUTE_TEXTS:
            return random.choice(self.SALUTE_TEXTS[key])
        
        # 尝试默认匹配
        key = ('DEFAULT', 'DEFAULT', min(3, level_diff))
        if key in self.SALUTE_TEXTS:
            return random.choice(self.SALUTE_TEXTS[key])
        
        return "有礼了"
    
    def on_start(self, agent):
        from src.definitions import STATE_IDLE
        
        # 保存原来的移动目标
        self._original_target_x = agent.target_x
        self._original_target_y = agent.target_y
        
        # 获取行礼台词
        self._salute_text = self._get_salute_text()
        
        # 计算侧移方向（垂直于与目标的连线）
        dx = self.target.rect.centerx - agent.rect.centerx
        dy = self.target.rect.centery - agent.rect.centery
        dist = max(1, math.hypot(dx, dy))
        
        # 侧移方向（顺时针90度）
        side_dx = -dy / dist * self.dodge_distance
        side_dy = dx / dist * self.dodge_distance
        
        self._dodge_x = agent.rect.centerx + side_dx
        self._dodge_y = agent.rect.centery + side_dy
        
        agent.clear_movement_target("行礼让路")
        agent.state = STATE_IDLE
        agent.ai_reason = self.reason
    
    def on_tick(self, agent, dt_ms):
        from src.definitions import STATE_MOVING, STATE_IDLE
        
        self.elapsed += dt_ms
        
        if self._phase == 'DODGE':
            # 快速侧移让路
            agent.set_movement_target(self._dodge_x, self._dodge_y, "让路")
            agent.state = STATE_MOVING
            dist = math.hypot(agent.rect.centerx - self._dodge_x, 
                            agent.rect.centery - self._dodge_y)
            if dist < 10 or self.elapsed > 500:
                self._phase = 'SALUTE'
                agent.clear_movement_target("让路完成")
                agent.state = STATE_IDLE
        
        elif self._phase == 'SALUTE':
            # 显示行礼气泡（通过 ai_reason 显示）
            agent.ai_reason = self._salute_text
            
            # 设置临时气泡显示标记
            agent._salute_bubble = self._salute_text
            agent._salute_bubble_timer = self.duration - self.elapsed
            
            self._phase = 'WAIT'
        
        elif self._phase == 'WAIT':
            # 等待行礼结束
            if self.elapsed >= self.duration:
                self._phase = 'DONE'
                self.finished = True
                return False
        
        return True
    
    def on_end(self, agent):
        from src.definitions import STATE_IDLE
        
        # 清除气泡
        agent._salute_bubble = None
        agent._salute_bubble_timer = 0
        
        # 恢复原来的移动目标（如果有）
        if self._original_target_x is not None:
            agent.set_movement_target(self._original_target_x, self._original_target_y, "恢复移动")
        
        agent.ai_reason = "继续前进"


class PayTribute(AtomicAction):
    """
    缴纳税/保护费行为 - 组织成员定期向控制者缴费
    
    流程：
    1. 移动到收款人/建筑
    2. 计算应缴金额
    3. 扣款并转入对方/组织金库
    4. 显示缴费反馈
    """
    
    def __init__(self, collector, amount, tribute_type='TAX', reason="缴费"):
        """
        Args:
            collector: 收款对象（NPC或Building）
            amount: 缴纳金额
            tribute_type: TAX(税)/PROTECTION(保护费)/FEE(会费)
            reason: 行为描述
        """
        super().__init__()
        self.collector = collector
        self.amount = amount
        self.tribute_type = tribute_type
        self.reason = reason
        self._phase = 'APPROACH'
        self.elapsed = 0
    
    def on_start(self, agent):
        from src.definitions import STATE_MOVING
        
        # 移动到收款人位置
        agent.set_movement_target(
            self.collector.rect.centerx, 
            self.collector.rect.centery + 20,
            self.reason
        )
        agent.state = STATE_MOVING
        agent.ai_reason = f"去缴{self.reason}"
    
    def on_tick(self, agent, dt_ms):
        from src.definitions import STATE_IDLE
        
        self.elapsed += dt_ms
        if self.elapsed > 10000:  # 超时
            self.finished = True
            return False
        
        if self._phase == 'APPROACH':
            dist = math.hypot(
                agent.rect.centerx - self.collector.rect.centerx,
                agent.rect.centery - self.collector.rect.centery
            )
            if dist < 50:
                self._phase = 'PAY'
        
        elif self._phase == 'PAY':
            # 执行支付
            actual_pay = min(agent.money, self.amount)
            if actual_pay > 0:
                agent.money -= actual_pay
                
                # 如果收款人是NPC，钱进入他的口袋（后续可能上缴组织）
                if hasattr(self.collector, 'money'):
                    self.collector.money += actual_pay
                
                # 设置反馈气泡
                if self.tribute_type == 'TAX':
                    agent._salute_bubble = f"缴税{actual_pay}铜"
                elif self.tribute_type == 'PROTECTION':
                    agent._salute_bubble = f"（交保护费{actual_pay}铜）"
                else:
                    agent._salute_bubble = f"缴费{actual_pay}铜"
                agent._salute_bubble_timer = 1500
                
                agent.ai_reason = f"已缴{actual_pay}铜"
            else:
                agent._salute_bubble = "我没钱..."
                agent._salute_bubble_timer = 1000
                agent.ai_reason = "交不起..."
            
            agent.state = STATE_IDLE
            agent.clear_movement_target("缴费完成")
            self._phase = 'DONE'
            self.finished = True
            return False
        
        return True
    
    def on_end(self, agent):
        pass


# ═══════════════════════════════════════════════════════════════════
# 行为队列
# ═══════════════════════════════════════════════════════════════════

class ActionQueue:
    """NPC行为队列管理器"""
    
    def __init__(self, owner):
        self.owner = owner
        self._queue = []
        self._current = None
    
    def enqueue(self, action):
        self._queue.append(action)
    
    def enqueue_front(self, action):
        self._queue.insert(0, action)
    
    def clear(self):
        if self._current:
            self._current.on_end(self.owner)
        self._current = None
        self._queue.clear()
    
    def is_empty(self):
        return self._current is None and len(self._queue) == 0
    
    @property
    def current(self):
        return self._current
    
    def tick(self, dt_ms) -> bool:
        """返回True表示有行为在执行"""
        if self._current is None and self._queue:
            self._current = self._queue.pop(0)
            self._current.on_start(self.owner)
        
        if self._current:
            if not self._current.on_tick(self.owner, dt_ms) or self._current.finished:
                self._current.on_end(self.owner)
                self._current = None
            else:
                return True
        
        return self._current is not None or bool(self._queue)
