import math
import pygame
from src.definitions import *
from src.utils import log_game_event
from src.grid_base import BaseGrid

# ═══════════════════════════════════════════════════════════════════
# 隐性网格管理系统 - 防止静止NPC堆叠
# ═══════════════════════════════════════════════════════════════════
# 设计原则：
#   - 只追踪"静止"状态的NPC（IDLE、WORKING等非移动状态）
#   - 当NPC停止移动时，检查目标位置是否被占用
#   - 如果被占用，自动寻找附近的空闲位置
#   - 移动中的NPC可以自由穿过（不受限制）
#   - NPC与建筑的重叠保持允许
#   - 继承 BaseGrid 提供通用网格功能
# ═══════════════════════════════════════════════════════════════════

class OccupancyGrid(BaseGrid):
    """
    隐性网格占用管理器 - 继承自 BaseGrid
    
    【核心设计】多格占用模型：
    - 每个NPC根据其卡牌大小占用多个网格（类似元胞自动机中的车辆模型）
    - 网格记录的是"有哪些NPC覆盖此格"，而非"此格属于谁"
    - 允许临时重叠（移动中），但目标点选择时尽量避免重叠
    
    数据结构：
    - _grid_to_npcs: {(gx,gy): set(npc_id1, npc_id2, ...)} - 每个格子被哪些NPC覆盖
    - _npc_to_grids: {npc_id: set((gx1,gy1), (gx2,gy2), ...)} - 每个NPC覆盖了哪些格子
    """
    
    # 网格粒度（像素），较小的值提供更精细的控制
    DEFAULT_CELL_SIZE = 40  # 40px，卡牌约80x100，会覆盖2x3=6格
    
    # 寻找空闲位置时的搜索半径（网格单位）
    MAX_SEARCH_RADIUS = 10  # 最多搜索10格范围（约400px）
    
    # NPC卡牌的默认尺寸（用于计算覆盖格子）
    DEFAULT_CARD_WIDTH = 70
    DEFAULT_CARD_HEIGHT = 90
    
    def __init__(self):
        super().__init__(self.DEFAULT_CELL_SIZE)
        # {(grid_x, grid_y): set(npc_id, ...)} - 每个网格被哪些NPC覆盖
        self._grid_to_npcs = {}
        # {npc_id: set((gx, gy), ...)} - 每个NPC覆盖了哪些网格
        self._npc_to_grids = {}
        # 世界地图引用（用于障碍物检测）
        self._world_map = None
    
    def set_world_map(self, world_map):
        """设置世界地图引用，用于障碍物检测"""
        self._world_map = world_map
    
    def world_to_grid(self, wx, wy):
        """世界坐标转网格坐标（使用基类方法）"""
        return self.world_to_cell(wx, wy)
    
    def grid_to_world(self, gx, gy):
        """网格坐标转世界坐标（使用基类方法）"""
        return self.cell_to_world(gx, gy)
    
    def _get_covered_grids(self, center_x, center_y, width=None, height=None):
        """
        计算一个矩形区域覆盖的所有网格
        
        Args:
            center_x, center_y: 矩形中心的世界坐标
            width, height: 矩形尺寸（默认使用标准卡牌尺寸）
        
        Returns:
            set of (gx, gy): 覆盖的所有网格坐标
        """
        if width is None:
            width = self.DEFAULT_CARD_WIDTH
        if height is None:
            height = self.DEFAULT_CARD_HEIGHT
        
        # 计算矩形的四个边界
        left = center_x - width // 2
        right = center_x + width // 2
        top = center_y - height // 2
        bottom = center_y + height // 2
        
        # 转换为网格坐标
        gx_min = int(left) // self.cell_size
        gx_max = int(right) // self.cell_size
        gy_min = int(top) // self.cell_size
        gy_max = int(bottom) // self.cell_size
        
        # 收集所有覆盖的格子
        covered = set()
        for gx in range(gx_min, gx_max + 1):
            for gy in range(gy_min, gy_max + 1):
                covered.add((gx, gy))
        
        return covered
    
    def get_overlap_count(self, center_x, center_y, exclude_npc_id=None, width=None, height=None):
        """
        计算在指定位置放置卡牌会与多少其他NPC重叠
        
        Args:
            center_x, center_y: 卡牌中心的世界坐标
            exclude_npc_id: 排除的NPC（通常是自己）
            width, height: 卡牌尺寸
        
        Returns:
            int: 重叠的NPC数量
        """
        covered_grids = self._get_covered_grids(center_x, center_y, width, height)
        
        # 收集所有在这些格子上的NPC（去重）
        overlapping_npcs = set()
        for grid in covered_grids:
            npcs_in_grid = self._grid_to_npcs.get(grid, set())
            overlapping_npcs.update(npcs_in_grid)
        
        # 排除自己
        if exclude_npc_id is not None:
            overlapping_npcs.discard(exclude_npc_id)
        
        return len(overlapping_npcs)
    
    def is_position_clean(self, center_x, center_y, exclude_npc_id=None, width=None, height=None):
        """
        检查在指定位置放置卡牌是否完全不与其他NPC重叠
        
        Returns:
            True: 完全干净，没有重叠
            False: 有重叠
        """
        return self.get_overlap_count(center_x, center_y, exclude_npc_id, width, height) == 0
    
    def is_blocked_by_obstacle(self, gx, gy):
        """检查网格是否被障碍物阻挡"""
        if self._world_map is None:
            return False
        
        wx, wy = self.grid_to_world(gx, gy)
        test_rect = pygame.Rect(0, 0, self.cell_size - 8, self.cell_size - 8)
        test_rect.center = (int(wx), int(wy))
        
        return self._world_map.is_blocked(test_rect)
    
    def occupy(self, npc_id, center_x, center_y, width=None, height=None):
        """
        NPC占用指定位置（标记覆盖的所有格子）
        
        Args:
            npc_id: NPC的ID
            center_x, center_y: 卡牌中心的世界坐标
            width, height: 卡牌尺寸
        """
        # 先释放之前占用的位置
        self.release(npc_id)
        
        # 计算新覆盖的格子
        new_grids = self._get_covered_grids(center_x, center_y, width, height)
        
        # 记录占用关系
        self._npc_to_grids[npc_id] = new_grids
        for grid in new_grids:
            if grid not in self._grid_to_npcs:
                self._grid_to_npcs[grid] = set()
            self._grid_to_npcs[grid].add(npc_id)
    
    def release(self, npc_id):
        """NPC释放占用的所有网格"""
        old_grids = self._npc_to_grids.pop(npc_id, set())
        for grid in old_grids:
            if grid in self._grid_to_npcs:
                self._grid_to_npcs[grid].discard(npc_id)
                # 清理空集合
                if not self._grid_to_npcs[grid]:
                    del self._grid_to_npcs[grid]
    
    # ═══════════════════════════════════════════════════════════════════
    # 公开查询方法
    # ═══════════════════════════════════════════════════════════════════
    
    def get_npcs_at_grid(self, gx, gy):
        """
        返回占用指定格子的所有NPC ID集合
        
        Args:
            gx, gy: 网格坐标
        
        Returns:
            set: NPC ID 集合（可能为空）
        """
        return self._grid_to_npcs.get((gx, gy), set()).copy()
    
    def get_npcs_at_world_pos(self, wx, wy):
        """
        返回占用指定世界坐标所在格子的所有NPC ID集合
        
        Args:
            wx, wy: 世界坐标（像素）
        
        Returns:
            set: NPC ID 集合（可能为空）
        """
        gx, gy = self.world_to_grid(wx, wy)
        return self.get_npcs_at_grid(gx, gy)
    
    def get_grids_by_npc(self, npc_id):
        """
        返回指定NPC占用的所有格子坐标集合
        
        Args:
            npc_id: NPC的ID
        
        Returns:
            set: 格子坐标 (gx, gy) 集合（可能为空）
        """
        return self._npc_to_grids.get(npc_id, set()).copy()
    
    def get_all_occupied_grids(self):
        """
        返回所有被占用的格子及其占用者
        
        Returns:
            dict: {(gx, gy): set(npc_ids), ...}
        """
        return {k: v.copy() for k, v in self._grid_to_npcs.items()}
    
    def get_conflict_grids(self):
        """
        返回所有存在冲突（被多个NPC占用）的格子
        
        Returns:
            dict: {(gx, gy): set(npc_ids), ...} 只包含len >= 2的项
        """
        return {k: v.copy() for k, v in self._grid_to_npcs.items() if len(v) >= 2}
    
    def find_free_position(self, wx, wy, exclude_npc_id=None, check_obstacles=True, 
                          width=None, height=None):
        """
        寻找指定位置附近的最佳空闲位置
        
        策略：
        1. 首选完全无重叠的位置
        2. 次选重叠最少的位置
        3. 使用螺旋搜索从近到远
        
        Returns:
            (world_x, world_y): 找到的最佳世界坐标
        """
        # 首先检查目标位置是否已经足够好（无重叠）
        if self.is_position_clean(wx, wy, exclude_npc_id, width, height):
            # 位置干净，检查障碍物
            gx, gy = self.world_to_grid(wx, wy)
            if not check_obstacles or not self.is_blocked_by_obstacle(gx, gy):
                return (wx, wy)
        
        # 螺旋搜索：收集候选位置及其重叠数
        import random
        best_pos = (wx, wy)
        best_overlap = self.get_overlap_count(wx, wy, exclude_npc_id, width, height)
        
        gx_center, gy_center = self.world_to_grid(wx, wy)
        
        for radius in range(1, self.MAX_SEARCH_RADIUS + 1):
            # 该半径的候选点
            candidates = []
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) == radius or abs(dy) == radius:
                        candidates.append((gx_center + dx, gy_center + dy))
            
            # 打乱顺序
            random.shuffle(candidates)
            
            for cgx, cgy in candidates:
                # 检查障碍物
                if check_obstacles and self.is_blocked_by_obstacle(cgx, cgy):
                    continue
                
                # 转换为世界坐标
                cand_x, cand_y = self.grid_to_world(cgx, cgy)
                overlap = self.get_overlap_count(cand_x, cand_y, exclude_npc_id, width, height)
                
                # 找到完全无重叠的位置，立即返回
                if overlap == 0:
                    return (cand_x, cand_y)
                
                # 记录重叠最少的位置
                if overlap < best_overlap:
                    best_overlap = overlap
                    best_pos = (cand_x, cand_y)
        
        # 没找到完全无重叠的，返回重叠最少的
        if best_overlap > 0:
            log_game_event(f"[Grid] 在({wx:.0f},{wy:.0f})附近未找到完全空闲位置，选择重叠最少的({best_pos[0]:.0f},{best_pos[1]:.0f})，重叠{best_overlap}个NPC", tag="GRID")
        
        return best_pos
    
    def update_from_cards(self, all_cards):
        """
        根据当前所有卡牌更新网格占用状态
        只追踪静止状态的NPC
        
        【多格占用模型】：
        - 每个静止NPC占用其卡牌覆盖的所有格子
        - 新加入的NPC如果与现有NPC重叠，尝试寻找空位
        """
        from src.entities.npc import NPC
        
        static_states = {STATE_IDLE, STATE_WORKING, STATE_WATCHING, STATE_EVENT, STATE_MEETING, STATE_DOWNED}
        
        # 获取当前应该占用网格的NPC集合
        static_npcs = set()
        for card in all_cards:
            if not isinstance(card, NPC):
                continue
            if card.job == 'PLAYER':
                continue
            if card.state not in static_states:
                continue
            # 被堆叠的NPC不占用独立网格（位置跟随父级）
            if card.stack_parent is not None:
                continue
            
            # 【事件保护】跳过有事件保护标记的NPC，防止干扰事件引导
            if getattr(card, '_event_protected', False):
                continue
            
            static_npcs.add(card.id)
            curr_x, curr_y = card.rect.centerx, card.rect.centery
            card_w, card_h = card.rect.width, card.rect.height
            
            # 如果这个NPC还没有注册网格位置，帮它注册
            if card.id not in self._npc_to_grids:
                # 检查当前位置是否与其他NPC重叠
                if not self.is_position_clean(curr_x, curr_y, exclude_npc_id=card.id, 
                                              width=card_w, height=card_h):
                    # 有重叠，寻找附近空位
                    free_x, free_y = self.find_free_position(
                        curr_x, curr_y, 
                        exclude_npc_id=card.id,
                        width=card_w, height=card_h
                    )
                    if (free_x, free_y) != (curr_x, curr_y):
                        # 移动到空位（调整NPC实际位置）
                        card.set_pos(free_x, free_y, "网格防重叠调整")
                        #log_game_event(f"[Grid] {card.name} 位置被占用，从({curr_x:.0f},{curr_y:.0f})调整到({free_x:.0f},{free_y:.0f})", tag="GRID")
                        curr_x, curr_y = free_x, free_y
                        
                        # 【关键修复】清除NPC的移动目标，防止AI反复驱动去同一个被占位置
                        # 同时设置冷却期，让AI有时间重新决策
                        if hasattr(card, 'clear_movement_target'):
                            card.clear_movement_target("网格系统调整位置，等待AI重新决策")
                        else:
                            card.target_x = None
                            card.target_y = None
                        
                        # 设置网格调整冷却（防止AI立刻又设置相同目标）
                        card._grid_adjust_cooldown = 60  # 约1秒冷却（60帧）
                
                # 占用位置（多格）
                self.occupy(card.id, curr_x, curr_y, card_w, card_h)
        
        # 清除不再静止的NPC的占用
        for npc_id in list(self._npc_to_grids.keys()):
            if npc_id not in static_npcs:
                self.release(npc_id)
    
    def get_debug_info(self):
        """返回调试信息"""
        total_grids = len(self._grid_to_npcs)
        total_npcs = len(self._npc_to_grids)
        return f"网格占用: {total_grids}格, NPC数: {total_npcs}"
    
    def print_all_static_npcs_info(self, all_cards):
        """
        打印所有静止NPC的位置和重叠信息（多格模型）
        用于 F3 调试面板的按钮回调
        
        【多格模型下的重叠定义】：
        当一个格子被2个或以上NPC覆盖时，意味着这些NPC的边界存在物理重叠。
        """
        from src.entities.npc import NPC
        
        print("\n" + "=" * 70)
        print("[位置] 静止 NPC 网格占用信息 (多格模型)")
        print("=" * 70)
        
        static_states = {STATE_IDLE, STATE_WORKING, STATE_WATCHING, STATE_EVENT, STATE_MEETING, STATE_DOWNED}
        
        # 收集所有静止NPC
        static_npcs = []
        for card in all_cards:
            if not isinstance(card, NPC):
                continue
            if card.job == 'PLAYER':
                continue
            if card.state not in static_states:
                continue
            if card.stack_parent is not None:
                continue
            static_npcs.append(card)
        
        # 打印每个NPC的覆盖信息
        print(f"\n【NPC列表】共 {len(static_npcs)} 个静止NPC：")
        for npc in static_npcs:
            center_x, center_y = npc.rect.centerx, npc.rect.centery
            covered = self._npc_to_grids.get(npc.id, set())
            overlap_count = self.get_overlap_count(center_x, center_y, exclude_npc_id=npc.id,
                                                    width=npc.rect.width, height=npc.rect.height)
            status = "[!]重叠" if overlap_count > 0 else "[ok]干净"
            print(f"  {status} {npc.name} | 中心({center_x}, {center_y}) | 覆盖{len(covered)}格 | 与{overlap_count}个NPC重叠")
        
        # 找出所有有冲突的格子
        print(f"\n【重叠热点】被多个NPC覆盖的格子：")
        conflict_grids = [(grid, npcs) for grid, npcs in self._grid_to_npcs.items() if len(npcs) > 1]
        if conflict_grids:
            for (gx, gy), npc_ids in sorted(conflict_grids):
                # 查找NPC名字
                npc_names = []
                for card in all_cards:
                    if hasattr(card, 'id') and card.id in npc_ids:
                        npc_names.append(card.name)
                print(f"  [!] 格({gx}, {gy}): {', '.join(npc_names)}")
        else:
            print("  [ok] 无冲突格子")
        
        # 统计
        total_static = len(static_npcs)
        total_grids = len(self._grid_to_npcs)
        overlap_grids = len(conflict_grids)
        
        print("\n" + "-" * 70)
        print(f"[统计] 静止NPC {total_static} 个 | 占用格子 {total_grids} 个 | 冲突格子 {overlap_grids} 个")
        print("=" * 70 + "\n")
        
        log_game_event(f"[Grid调试] 静止NPC: {total_static}, 格子: {total_grids}, 冲突: {overlap_grids}", tag="GRID")
        
        return total_static, total_grids, overlap_grids


class MovementSystem:
    def __init__(self):
        self._accum_ms = 0  # 累计未消费的毫秒数
        self._step_dt = 0.0 # 本次逻辑步长(秒)，供 _execute_entity_movement 使用
        
        # 初始化隐性网格管理器
        self.occupancy_grid = OccupancyGrid()
    

    def update(self, all_cards, world_map, dt_ms=16):
        """
        每帧调用，移动逻辑按固定时间步长（MOVE_LOGIC_INTERVAL_MS）执行。
        dt_ms: 本帧实际耗时(毫秒)，来自 clock.tick()，默认假设 60fps≈16ms。
        speed 单位：px/s（像素/秒），每步实际位移 = speed × MOVE_LOGIC_INTERVAL_MS/1000
        """
        # 确保网格系统有世界地图引用（用于障碍物检测）
        if self.occupancy_grid._world_map is None and world_map is not None:
            self.occupancy_grid.set_world_map(world_map)
        
        # 更新网格占用状态（每帧执行，消耗可忽略）
        self.occupancy_grid.update_from_cards(all_cards)
        
        self._accum_ms += dt_ms
        if self._accum_ms < MOVE_LOGIC_INTERVAL_MS:
            return  # 时间未到，本帧跳过移动逻辑
        
        #log_game_event(f"[DBG移动系统] update被调用 dt_ms={dt_ms} accum_ms={self._accum_ms}", tag="MOVEMENT")
        # [调试] 记录movement_system的调用频率
        import time
        current_time = time.time()
        if not hasattr(self, '_last_update_time'):
            self._last_update_time = current_time
        else:
            interval = current_time - self._last_update_time
            self._last_update_time = current_time
        
        # 消费一个固定步长，多余的留给下一帧（不追帧，防单帧暴冲）
        self._accum_ms -= MOVE_LOGIC_INTERVAL_MS
        self._step_dt = MOVE_LOGIC_INTERVAL_MS / 1000.0

        for card in all_cards:
            # 【冷却递减】每帧递减网格调整冷却计时器
            if hasattr(card, '_grid_adjust_cooldown') and card._grid_adjust_cooldown > 0:
                card._grid_adjust_cooldown -= 1
            
            agent = card
            is_player = getattr(agent, 'job', '') == 'PLAYER'
            # [调试] 背人时强制开启详细调试信息
            agent_state = getattr(agent, 'state', '')
            is_carrying = (agent_state == STATE_CARRYING)
            is_dbg = (DEBUG_NPC_PATH_VERBOSE and getattr(agent, 'debug_selected', False)) or \
                    (DEBUG_PLAYER_PATH and is_player)
            
            if is_dbg:
                log_game_event(f"[DBG移动系统] 开始更新位置信息 {card.name} state={agent_state} target=({getattr(agent, 'target_x', None)},{getattr(agent, 'target_y', None)}) pixel=({agent.pixel_x:.1f},{agent.pixel_y:.1f})", tag="MOVEMENT")
            
            if getattr(card, 'dragging', False):
                if is_dbg:
                    log_game_event(f"[DBG移动系统] 卡牌 {card.name} 正在被拖拽，跳过移动逻辑", tag="MOVEMENT")
                continue

            # ── 优先处理战斗被动位移（knockback/recoil）──────────────────
            # knockback_tx/ty 由 combat_system 专属写入，与 AI 寻路的 target_x/y 完全隔离。
            # 处理期间跳过 AI 寻路，硬直结束后自动清除，不影响后续任何逻辑。
            kb_tx = getattr(card, 'knockback_tx', None)
            kb_ty = getattr(card, 'knockback_ty', None)
            if kb_tx is not None and kb_ty is not None:
                self._execute_entity_movement(card, kb_tx, kb_ty, world_map, is_knockback=True)
                # 到达弹开目标点后清除（movement 内部会把 target_x 置 None，
                # 但 knockback 用独立字段，需在此检测到达后清除）
                dist_kb = math.hypot(card.rect.centerx - kb_tx, card.rect.centery - kb_ty)
                if dist_kb < 8:
                    card.knockback_tx = None
                    card.knockback_ty = None
                if is_dbg:
                    log_game_event(f"[DBG移动系统] 硬直不寻路 {card.name} 被弹开 towards ({kb_tx:.0f},{kb_ty:.0f}) 距离={dist_kb:.1f}", tag="MOVEMENT")
                continue  # 硬直期间不执行 AI 寻路移动

            # 检查是否有 AI 寻路目标点
            target_x = getattr(card, 'target_x', None)
            target_y = getattr(card, 'target_y', None)
            if is_dbg:
                log_game_event(f"[DBG移动系统] {card.name} AI目标点=({target_x},{target_y})", tag="MOVEMENT")

            if target_x is not None and target_y is not None and card.stack_parent is None:
                self._execute_entity_movement(card, target_x, target_y, world_map)

    def _execute_entity_movement(self, agent, target_x, target_y, world_map, is_knockback=False):
        """
        从 NPC 类中提取的移动核心逻辑 (Floyd寻路 + 物理碰撞 + 防卡死)
        is_knockback=True 时：跳过寻路/防卡死，直接线性滑向目标点（被动物理位移）
        """
        is_player = getattr(agent, 'job', '') == 'PLAYER'
        # [调试] 背人时强制开启详细调试信息
        agent_state = getattr(agent, 'state', '')
        is_carrying = (agent_state == STATE_CARRYING)
        is_dbg = (DEBUG_NPC_PATH_VERBOSE and getattr(agent, 'debug_selected', False)) or \
                 (DEBUG_PLAYER_PATH and is_player)
        
        if is_dbg:
            # [调试] 增强状态调试，检查是否有状态覆盖问题
            is_carrying_but_moving = (agent_state == STATE_MOVING and 
                                    getattr(agent, 'stack_child', None) is not None and 
                                    hasattr(getattr(agent, 'stack_child', None), 'name'))
            if is_carrying_but_moving:
                patient_name = agent.stack_child.name
                log_game_event(f"[DBG状态异常] {agent.name} 背着 {patient_name} 但state={agent_state}，应为CARRYING！", tag="MOVEMENT")
            log_game_event(f"[DBG移动-执行移动函数开头] {agent.name} 当前位置=({agent.rect.centerx},{agent.rect.centery}) 目标=({target_x},{target_y}) is_knockback={is_knockback} state={agent_state}", tag="MOVEMENT")

        # ── 被动击退：直接线性移动，不走寻路/防卡死 ─────────────────
        if is_knockback:
            speed = getattr(agent, 'move_speed', 80.0) * 1.5  # 1.5× 平滑滑动
            step_dt = getattr(self, '_step_dt', MOVE_LOGIC_INTERVAL_MS / 1000.0)
            speed_this_step = speed * step_dt
            dx = target_x - agent.rect.centerx
            dy = target_y - agent.rect.centery
            dist = math.hypot(dx, dy)
            if dist > 0:
                actual = min(speed_this_step, dist)
                agent.set_pos(
                    agent.rect.centerx + (dx / dist) * actual,
                    agent.rect.centery + (dy / dist) * actual,
                    "knockback滑动"
                )
            return

        pathfinder = getattr(world_map, 'pathfinder', None)
        
        # --- 1. 防卡死检测 ---
        # 确保 agent 有防卡死需要的属性，如果没有则初始化
        if not hasattr(agent, 'stuck_check_timer'): agent.stuck_check_timer = 0
        if not hasattr(agent, 'stuck_check_pos'): agent.stuck_check_pos = (agent.pixel_x, agent.pixel_y)
        if not hasattr(agent, 'stuck_accumulated'): agent.stuck_accumulated = 0
        
        
        
   
        # 防卡死：改为按"逻辑步数"计时（每次 _execute_entity_movement 被调用即+1）
        # 每 MOVE_LOGIC_INTERVAL_MS * CHECK_STEPS_INTERVAL ms 检查一次
        agent.stuck_check_timer += 1
        CHECK_STEPS_INTERVAL = 15  # 15步 × 100ms = 1.5秒检查一次
        if agent.stuck_check_timer >= CHECK_STEPS_INTERVAL:
            dist_since_last_check = math.hypot(agent.pixel_x - agent.stuck_check_pos[0], agent.pixel_y - agent.stuck_check_pos[1])
            # 期望位移 = speed(px/s) × 检查间隔(s) × 0.3
            speed_now = getattr(agent, 'move_speed', 80.0)
            check_interval_s = CHECK_STEPS_INTERVAL * MOVE_LOGIC_INTERVAL_MS / 1000.0
            expected_min_dist = speed_now * check_interval_s * 0.15
            # 如果处于移动状态但位移极小
            state = getattr(agent, 'state', STATE_IDLE)
            if state in [STATE_MOVING, STATE_CARRYING] and dist_since_last_check < expected_min_dist:
                agent.stuck_accumulated += 1
                if is_dbg:
                    log_game_event(f"[DBG卡顿] {agent.name} {CHECK_STEPS_INTERVAL}步位移{dist_since_last_check:.1f}px 期望≥{expected_min_dist:.1f}px 累计={agent.stuck_accumulated} 位置=({agent.rect.centerx},{agent.rect.centery}) 终点=({target_x:.0f},{target_y:.0f})", tag="MOVEMENT")
            else:
                agent.stuck_accumulated = 0
            
            agent.stuck_check_timer = 0
            agent.stuck_check_pos = (agent.pixel_x, agent.pixel_y)

        # --- 2. 严重卡死处理 (穿墙/瞬移/重置) ---
        use_force_graph = (agent.stuck_accumulated >= 1)
        is_forcing = False
        rescue_target = None

        if agent.stuck_accumulated >= 3:
            dist_to_final = math.hypot(target_x - agent.rect.centerx, target_y - agent.rect.centery)
            
            # 容错：距离很近直接吸附
            if dist_to_final < 120:
                agent.clear_movement_target(f"卡死救援-距离终点{dist_to_final:.0f}px直接吸附")
                agent.stuck_accumulated = 0
                # 直接吸附
                agent.set_pos(target_x,target_y,"卡住很久了并且距离终点120以内直接吸附")     
                if is_dbg:
                    log_game_event(f"[DBG卡死吸附] {agent.name} 已经卡住很久了，距离终点{dist_to_final:.0f}px，直接吸附 位置=({agent.rect.centerx},{agent.rect.centery}) 终点=({target_x:.0f},{target_y:.0f})", tag="MOVEMENT")
                return
            else:
                if pathfinder and pathfinder.nodes:
                    curr_pos = (agent.rect.centerx, agent.rect.centery)
                    # 优先找视线可达（width=60）的最近路点作为救援目标，避免选到墙后面的点
                    visible_rescue = [n for n in pathfinder.nodes if pathfinder._has_line_of_sight(curr_pos, n, width=60)]
                    candidates = visible_rescue if visible_rescue else pathfinder.nodes
                    nearest_node = min(candidates, key=lambda n: (n[0]-curr_pos[0])**2 + (n[1]-curr_pos[1])**2)
                    dist_to_rescue = math.hypot(nearest_node[0] - curr_pos[0], nearest_node[1] - curr_pos[1])
                    
                    if is_dbg:
                        log_game_event(f"[DBG救援] {agent.name} 救援点={nearest_node} 视线可达候选={len(visible_rescue)}/{len(pathfinder.nodes)} 距={dist_to_rescue:.0f}px", tag="MOVEMENT")
                    
                    if dist_to_rescue < 10:
                        agent.clear_movement_target("卡死救援-救援点太近彻底放弃")
                        agent.stuck_accumulated = 0
                        
                        return
                    else:
                        is_forcing = True
                        rescue_target = nearest_node
                else:
                    agent.clear_movement_target("卡死救援-无可用路径点强制停止")
                    agent.stuck_accumulated = 0
                    if is_dbg:
                        log_game_event(f"[DBG救援失败] {agent.name} 没有可用的路径点进行救援，强制停止移动", tag="MOVEMENT")
                    return

        # --- 3. 下一步路点计算 ---
        curr_center = agent.rect.center

        final_dest = (target_x, target_y)
        
        if is_forcing and rescue_target:
            move_target = rescue_target
            agent.debug_next_waypoint = rescue_target
        else:
            dist_sq_final = (target_x - curr_center[0])**2 + (target_y - curr_center[1])**2
            move_target = final_dest
            # 如果距离较远且有寻路器，使用寻路
            if pathfinder and dist_sq_final > 400: 
                move_target = pathfinder.get_next_move_target(curr_center, final_dest, force_graph=use_force_graph, agent=agent)
            agent.debug_next_waypoint = move_target

        # --- 4. 向量计算与移动 ---
        tx, ty = move_target
        dx = tx - curr_center[0]
        dy = ty - curr_center[1]
        dist_to_waypoint = math.hypot(dx, dy)
        dist_to_final = math.hypot(target_x - curr_center[0], target_y - curr_center[1])
        
        # speed 单位：px/s，乘以本步时长(s)得到本步像素位移
        speed = getattr(agent, 'move_speed', 80.0)
        agent_state = getattr(agent, 'state', '')

        # 到达判定 (这里只判断是否到了路点，最终到达由外部 System 或 arrive check 处理)
        if dist_to_waypoint < 10.0:
            if dist_to_final < 20.0:
                # [注意] 背人状态下需要更精确到达，不要过早停止
                if agent_state == STATE_CARRYING:
                    # [调试] 加强背人时的调试信息
                    patient_name = agent.stack_child.name if agent.stack_child and hasattr(agent.stack_child, 'name') else "？？？"
                    log_game_event(f"[DBG背人] {agent.name} 背着 {patient_name} 距离目标 {dist_to_final:.1f}px ai_reason={agent.ai_reason}", tag="MOVEMENT")
                    # 背人时需要准确到达医馆，允许更近距离才停止（5px内）
                    if dist_to_final < 5.0:
                        agent.clear_movement_target("背人精确到达目标点")
                        agent.set_pos(target_x,target_y,"背人精确到达")
                        log_game_event(f"[DBG背人到达] {agent.name} 背人精确到达目标点 位置=({curr_center[0]},{curr_center[1]}) 终点=({target_x:.0f},{target_y:.0f})", tag="MOVEMENT")
                        return
                else:
                    # 普通移动：到达终点时检查网格占用，避免与其他静止NPC重叠
                    final_x, final_y = target_x, target_y
                    npc_id = getattr(agent, 'id', None)
                    
                    # 使用网格系统找到空闲位置（防止与其他静止NPC重叠）
                    if npc_id is not None:
                        free_x, free_y = self.occupancy_grid.find_free_position(target_x, target_y, exclude_npc_id=npc_id)
                        if (free_x, free_y) != (target_x, target_y):
                            # 原位置被占用，移动到附近空闲位置
                            final_x, final_y = free_x, free_y
                            if is_dbg:
                                log_game_event(f"[Grid] {agent.name} 目标位置({target_x:.0f},{target_y:.0f})被占用，调整到({final_x:.0f},{final_y:.0f})", tag="GRID")
                        # 占用新位置
                        self.occupancy_grid.occupy(npc_id, final_x, final_y)
                    
                    agent.clear_movement_target("普通移动到达终点")
                    agent.set_pos(final_x, final_y, "很靠近终点了直接吸附")
                    
                    # [位置] NPC首次停止移动时输出网格信息
                    if not getattr(agent, '_grid_info_logged', False):
                        gx, gy = self.occupancy_grid.world_to_grid(final_x, final_y)
                        #log_game_event(f"[Grid停止] {agent.name} 首次停止 坐标({final_x:.0f},{final_y:.0f}) 网格({gx},{gy})", tag="GRID")
                        agent._grid_info_logged = True
                    
                    if is_dbg:
                        log_game_event(f"[DBG到达] {agent.name} 已经到达目标点附近，停止移动 位置=({curr_center[0]},{curr_center[1]}) 终点=({final_x:.0f},{final_y:.0f})", tag="MOVEMENT")
                    return

        if dist_to_waypoint == 0: 
            if is_dbg:
                log_game_event(f"[DBG警告] {agent.name} 路点计算结果与当前位置完全重合，无法移动 位置=({curr_center[0]},{curr_center[1]}) 终点=({target_x:.0f},{target_y:.0f})", tag="MOVEMENT")
            return

        # 计算实际移动速度（加成）
        original_speed = speed
        if agent_state == STATE_CARRYING:
            speed *= 1.0   # 背人时保持原速度
        elif agent_state == STATE_COMBAT:
            if getattr(agent, 'knockback_timer', 0) > 0:
                # 弹开硬直中：用 1.5× 速度缓慢滑动，避免一帧闪现到目标点
                speed *= 1.5
            else:
                # 追击中：用 2.5× 速度快速接近（原4×太快导致视觉跳帧）
                speed *= 2.5
        step_dt = getattr(self, '_step_dt', MOVE_LOGIC_INTERVAL_MS / 1000.0)
        speed_this_step = speed * step_dt  # 本步最大位移(px)
        
        curr_center_x = curr_center[0]
        curr_center_y = curr_center[1]
        
        actual_step = min(speed_this_step, dist_to_waypoint)
        
        step_x = (dx / dist_to_waypoint) * actual_step
        step_y = (dy / dist_to_waypoint) * actual_step
        
        # [调试] 背人时显示详细的移动计算过程
   
        
        new_center_x = curr_center_x + step_x
        new_center_y = curr_center_y + step_y
        
        def check_collision(cx, cy):
            if is_forcing: return False
            # 构造一个临时的 rect 用于检测
            # 因为 is_blocked 检测的是 rect，我们需要把中心点转回 rect (左上角)
            test_rect = agent.rect.copy()
            test_rect.center = (int(cx), int(cy))
            skin_rect = test_rect.inflate(-4, -4)
            return False
            #return world_map and world_map.is_blocked(skin_rect)
        
        # X轴尝试
        x_blocked = check_collision(new_center_x, curr_center_y)
        if x_blocked:
            new_center_x = curr_center_x # 撞墙了，X回退
            # X被阻时，尝试用X分量补偿Y方向（沿墙滑动）
            slide_y = curr_center_y + step_x * 0.5
            if not check_collision(curr_center_x, slide_y):
                new_center_y = slide_y
        
        # Y轴尝试
        y_blocked = check_collision(new_center_x, new_center_y)
        if y_blocked:
            new_center_y = curr_center_y # 撞墙了，Y回退
            # Y被阻时，尝试用Y分量补偿X方向（沿墙滑动）
            slide_x = new_center_x + step_y * 0.5
            if not check_collision(slide_x, curr_center_y):
                new_center_x = slide_x

        if is_dbg:
            log_game_event(f"[DBG移动-计算完预期坐标] {agent.name} 位置=({curr_center[0]},{curr_center[1]}) pixel_x={agent.pixel_x:.2f} size={agent.rect.size} 终点=({target_x:.0f},{target_y:.0f}) 中途点=({tx:.0f},{ty:.0f}) dist终={dist_to_final:.0f} stuck={agent.stuck_accumulated} force={is_forcing} x阻={x_blocked} y阻={y_blocked}", tag="MOVEMENT")

        # 最终应用
        if new_center_x != curr_center_x or new_center_y != curr_center_y:
            agent.set_pos(new_center_x, new_center_y, "移动更新")
            if is_dbg:
                # 调用后立刻验证坐标是否真的变了
                actual_cx = agent.rect.centerx
                actual_cy = agent.rect.centery
                ok = "[ok]" if (actual_cx != curr_center_x or actual_cy != curr_center_y) else "[!]被重置!"
                log_game_event(f"[DBG移动-最终应用] {agent.name} ({curr_center_x},{curr_center_y})→期望({new_center_x:.1f},{new_center_y:.1f}) 实际({actual_cx},{actual_cy}) {ok}", tag="MOVEMENT")
        elif is_dbg:
            log_game_event(f"[DBG无位移] {agent.name} step=({step_x:.2f},{step_y:.2f}) x阻={x_blocked} y阻={y_blocked} force={is_forcing} new=({new_center_x:.1f},{new_center_y:.1f}) curr=({curr_center_x},{curr_center_y})", tag="MOVEMENT")