# --- src/ai/spectate_ai.py ---
"""
围观AI：处理NPC围观行为
从原ai_system.py抽离 _handle_bystander 和 _enqueue_spectate

改进：使用网格系统检查NPC重叠和障碍物
"""
import math
import random
from src.definitions import STATE_IDLE, STATE_MOVING
from src.utils import log_game_event
from src.ai.constants import SPECTATE_RADIUS_MIN, SPECTATE_RADIUS_MAX


class SpectateAI:
    """
    围观行为模块
    
    设计原则：
    - 围观信号由事件处理器设置（spectate_src_x/y）
    - 本模块只负责执行围观行为（走向围观位、驻足）
    - 散去由事件处理器的COMBAT_END事件触发
    - 使用网格系统避免围观NPC相互重叠
    """
    
    def __init__(self, ai_system):
        self._ai = ai_system
    
    def enqueue_spectate(self, npc) -> bool:
        """
        检查并执行围观行为
        
        Returns:
            True - 接管了本帧决策
            False - 不在围观状态
        """
        cx = getattr(npc, 'spectate_src_x', None)
        cy = getattr(npc, 'spectate_src_y', None)
        if cx is None:
            return False
        
        # 如果在建筑内工作，先弹出
        if npc.stack_parent is not None:
            from src.entities.building import Building
            if isinstance(npc.stack_parent, Building):
                npc.bounce_off(npc.stack_parent)
                npc.is_working = False
                npc.work_timer = 0
        
        # 计算专属围观站位（基于ID黄金角，避免扎堆）
        target_sx, target_sy = self._calculate_spectate_position(npc, cx, cy)
        
        # 已到围观位 → 驻足
        dist_to_slot = math.hypot(
            npc.rect.centerx - target_sx, 
            npc.rect.centery - target_sy
        )
        
        if dist_to_slot < 30:
            npc.state = STATE_IDLE
            npc.clear_movement_target("决策树-已到围观位")
            npc.ai_reason = "围观中"
            npc.spectate_anchor_set = True
            return True
        
        # 走向围观位
        npc.state = STATE_MOVING
        npc.set_movement_target(target_sx, target_sy, "赶去围观")
        npc.clear_target_obj("围观不产生堆叠")
        npc.ai_reason = "赶去围观"
        npc.spectate_anchor_set = True
        return True
    
    def _calculate_spectate_position(self, npc, cx: float, cy: float) -> tuple:
        """
        计算NPC的专属围观站位
        
        使用黄金角分布，避免扎堆
        5圈：160→190→220→250→280→310 px
        
        改进：优先使用网格系统检查NPC重叠和障碍物
        """
        npc_id = getattr(npc, 'id', -1)
        id_angle_base = (npc_id * 137.5) % 360  # 黄金角
        layer = npc_id % 5  # 5圈
        r_base = SPECTATE_RADIUS_MIN + layer * 32
        
        target_sx, target_sy = None, None
        world_map = getattr(npc, '_world_map_ref', None)
        
        # 尝试获取网格系统（通过ai_system -> game引用链）
        occupancy_grid = None
        try:
            if hasattr(self._ai, 'game') and hasattr(self._ai.game, 'movement_system'):
                occupancy_grid = self._ai.game.movement_system.occupancy_grid
        except Exception as e:
            log_game_event(f"[SpectateAI] 无法获取网格系统: {e}", tag="GRID")
        
        # 尝试8个角度找到不被阻挡且不与其他NPC重叠的位置
        for attempt in range(8):
            angle = math.radians(id_angle_base + attempt * 45) + random.uniform(-0.15, 0.15)
            r = r_base + random.randint(0, 20)
            tx = cx + math.cos(angle) * r
            ty = cy + math.sin(angle) * r
            
            # 检查障碍物
            test_rect = npc.rect.copy()
            test_rect.center = (int(tx), int(ty))
            if world_map and world_map.is_blocked(test_rect):
                continue
            
            # 检查网格占用（如果有网格系统）
            if occupancy_grid is not None:
                gx, gy = occupancy_grid.world_to_grid(tx, ty)
                if not occupancy_grid.is_available(gx, gy, exclude_npc_id=npc_id):
                    # 该位置被占用，尝试找附近空闲位置
                    free_x, free_y = occupancy_grid.find_free_position(tx, ty, exclude_npc_id=npc_id)
                    # 如果找到的位置离围观中心太远，跳过这个角度
                    dist_to_center = math.hypot(free_x - cx, free_y - cy)
                    if dist_to_center > SPECTATE_RADIUS_MAX + 50:
                        continue
                    tx, ty = free_x, free_y
            
            target_sx, target_sy = tx, ty
            break
        
        # 兜底：使用默认位置，但通过网格系统调整
        if target_sx is None:
            default_x = cx + math.cos(math.radians(id_angle_base)) * r_base
            default_y = cy + math.sin(math.radians(id_angle_base)) * r_base
            
            if occupancy_grid is not None:
                # 使用网格系统找空闲位置
                target_sx, target_sy = occupancy_grid.find_free_position(
                    default_x, default_y, exclude_npc_id=npc_id
                )
            else:
                target_sx, target_sy = default_x, default_y
        
        return target_sx, target_sy
