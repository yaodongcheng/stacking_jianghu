"""
建筑目标选择器 - 统一的建筑选择工具
═══════════════════════════════════════════════════════════════════

提供智能的建筑目标选择逻辑，集成网格占用系统，避免NPC扎堆。

核心功能：
1. 优先选择"空闲"建筑（周围无NPC占用网格）
2. 次选"拥挤度最低"的建筑
3. 支持多种筛选条件（类型、距离、容量等）
4. 返回建筑+推荐站位坐标

使用示例：
    from src.building_selector import BuildingSelector
    
    selector = BuildingSelector(occupancy_grid)
    result = selector.find_best_building(
        npc, all_buildings, 
        building_type='MARKET',
        prefer_empty=True
    )
    if result:
        building, stand_x, stand_y = result
        npc.set_movement_target(stand_x, stand_y, "去市场")
"""

import math
from typing import Optional, Tuple, List, Set
from src.utils import log_game_event


class BuildingSelector:
    """
    智能建筑选择器
    
    结合网格占用系统，为NPC选择最佳目标建筑及站位。
    """
    
    # 建筑周围的默认搜索半径（像素）
    DEFAULT_SEARCH_RADIUS = 100
    
    # 认为"拥挤"的NPC数量阈值
    CROWDED_THRESHOLD = 3
    
    def __init__(self, occupancy_grid=None):
        """
        Args:
            occupancy_grid: OccupancyGrid 实例，用于查询网格占用
                           如果为 None，则退化为只检查 stack_child
        """
        self._grid = occupancy_grid
    
    def set_occupancy_grid(self, grid):
        """设置或更新网格系统引用"""
        self._grid = grid
    
    def find_best_building(
        self,
        npc,
        all_buildings: list,
        building_type: str = None,
        prefer_empty: bool = True,
        max_distance: float = None,
        exclude_buildings: Set = None
    ) -> Optional[Tuple[object, float, float]]:
        """
        为NPC找到最佳目标建筑
        
        Args:
            npc: NPC实例
            all_buildings: 所有建筑列表
            building_type: 筛选的建筑类型（如 'MARKET', 'CLINIC'）
            prefer_empty: 是否优先选择周围无人的建筑
            max_distance: 最大搜索距离（像素），None=不限
            exclude_buildings: 要排除的建筑集合
        
        Returns:
            (building, stand_x, stand_y): 最佳建筑及推荐站位
            None: 没有找到合适的建筑
        """
        if exclude_buildings is None:
            exclude_buildings = set()
        
        # 1. 筛选候选建筑
        candidates = self._filter_candidates(
            npc, all_buildings, building_type, max_distance, exclude_buildings
        )
        
        if not candidates:
            return None
        
        # 2. 评估每个建筑的"拥挤度"
        scored_buildings = []
        for building in candidates:
            crowdedness = self._get_building_crowdedness(building)
            distance = self._distance_to_building(npc, building)
            
            # 评分：拥挤度越低越好，距离越近越好
            # 空闲建筑得分 = 1000 - distance
            # 拥挤建筑得分 = 500 - crowdedness * 50 - distance
            if crowdedness == 0:
                score = 1000 - distance * 0.1
            else:
                score = 500 - crowdedness * 50 - distance * 0.1
            
            scored_buildings.append((building, score, crowdedness, distance))
        
        # 3. 排序：优先空闲，次选拥挤度低，最后考虑距离
        if prefer_empty:
            # 空闲建筑优先
            scored_buildings.sort(key=lambda x: (-x[1], x[2], x[3]))
        else:
            # 只按距离排序
            scored_buildings.sort(key=lambda x: x[3])
        
        # 4. 选择最佳建筑
        best_building = scored_buildings[0][0]
        crowdedness = scored_buildings[0][2]
        
        # 5. 计算推荐站位（避开已占用的位置）
        stand_x, stand_y = self._find_stand_position(npc, best_building)
        
        # 日志
        if crowdedness > 0:
            log_game_event(
                f"[BuildingSelector] {npc.name} 选择 {best_building.name}（拥挤度{crowdedness}）",
                tag="AI"
            )
        
        return (best_building, stand_x, stand_y)
    
    def find_empty_building(
        self,
        npc,
        all_buildings: list,
        building_type: str
    ) -> Optional[Tuple[object, float, float]]:
        """
        只查找完全空闲的建筑（简化版）
        
        如果没有空闲的，返回 None（不会退而求其次）
        """
        candidates = self._filter_candidates(npc, all_buildings, building_type)
        
        for building in candidates:
            if self._get_building_crowdedness(building) == 0:
                stand_x, stand_y = self._find_stand_position(npc, building)
                return (building, stand_x, stand_y)
        
        return None
    
    def find_any_building(
        self,
        npc,
        all_buildings: list,
        building_type: str
    ) -> Optional[Tuple[object, float, float]]:
        """
        查找任意该类型建筑（不考虑拥挤度）
        
        直接返回最近的建筑。
        """
        return self.find_best_building(
            npc, all_buildings, building_type, 
            prefer_empty=False
        )
    
    def is_building_crowded(self, building, threshold: int = None) -> bool:
        """检查建筑是否拥挤"""
        if threshold is None:
            threshold = self.CROWDED_THRESHOLD
        return self._get_building_crowdedness(building) >= threshold
    
    def get_building_crowdedness(self, building) -> int:
        """获取建筑的拥挤度（周围NPC数量）"""
        return self._get_building_crowdedness(building)
    
    # ═══════════════════════════════════════════════════════════════
    # 内部方法
    # ═══════════════════════════════════════════════════════════════
    
    def _filter_candidates(
        self, 
        npc, 
        all_buildings: list, 
        building_type: str = None,
        max_distance: float = None,
        exclude_buildings: Set = None
    ) -> List:
        """筛选候选建筑"""
        candidates = []
        
        for b in all_buildings:
            # 类型筛选
            if building_type and getattr(b, 'building_type', None) != building_type:
                continue
            
            # 排除列表
            if exclude_buildings and b in exclude_buildings:
                continue
            
            # 距离筛选
            if max_distance:
                dist = self._distance_to_building(npc, b)
                if dist > max_distance:
                    continue
            
            candidates.append(b)
        
        # 按距离排序
        candidates.sort(key=lambda b: self._distance_to_building(npc, b))
        
        return candidates
    
    def _get_building_crowdedness(self, building) -> int:
        """
        计算建筑周围的拥挤度
        
        综合考虑：
        1. 建筑上堆叠的NPC（stack_child）
        2. 建筑周围网格被占用的NPC数量
        """
        crowdedness = 0
        
        # 检查堆叠
        if building.stack_child is not None:
            crowdedness += 1
        
        # 检查网格占用
        if self._grid:
            center_x = building.rect.centerx
            center_y = building.rect.centery
            
            # 检查建筑周围的网格
            nearby_npcs = self._get_npcs_near_position(
                center_x, center_y, 
                radius=self.DEFAULT_SEARCH_RADIUS
            )
            crowdedness += len(nearby_npcs)
        
        return crowdedness
    
    def _get_npcs_near_position(self, center_x, center_y, radius=100) -> Set:
        """获取指定位置附近的NPC ID集合"""
        if not self._grid:
            return set()
        
        # 计算需要检查的网格范围
        cell_size = self._grid.cell_size
        grid_radius = int(radius / cell_size) + 1
        
        gx_center, gy_center = self._grid.world_to_cell(center_x, center_y)
        
        nearby_npcs = set()
        for dx in range(-grid_radius, grid_radius + 1):
            for dy in range(-grid_radius, grid_radius + 1):
                gx = gx_center + dx
                gy = gy_center + dy
                npcs = self._grid.get_npcs_at_grid(gx, gy)
                nearby_npcs.update(npcs)
        
        return nearby_npcs
    
    def _find_stand_position(self, npc, building) -> Tuple[float, float]:
        """
        为NPC找到建筑周围的最佳站位
        
        尽量避开已被其他NPC占用的位置。
        """
        center_x = building.rect.centerx
        center_y = building.rect.centery
        
        # 如果有网格系统，使用它来找空闲位置
        if self._grid:
            # 获取建筑周围已被占用的网格
            free_x, free_y = self._grid.find_free_position(
                center_x, center_y,
                exclude_npc_id=getattr(npc, 'id', None),
                check_obstacles=True
            )
            return (free_x, free_y)
        
        # 退化：直接返回建筑中心
        return (center_x, center_y)
    
    def _distance_to_building(self, npc, building) -> float:
        """计算NPC到建筑的距离"""
        return math.hypot(
            npc.rect.centerx - building.rect.centerx,
            npc.rect.centery - building.rect.centery
        )


# ═══════════════════════════════════════════════════════════════════
# 全局单例（方便各处调用）
# ═══════════════════════════════════════════════════════════════════

_global_selector: Optional[BuildingSelector] = None

def get_building_selector() -> BuildingSelector:
    """获取全局建筑选择器实例"""
    global _global_selector
    if _global_selector is None:
        _global_selector = BuildingSelector()
    return _global_selector

def init_building_selector(occupancy_grid):
    """初始化全局建筑选择器（在游戏启动时调用）"""
    global _global_selector
    _global_selector = BuildingSelector(occupancy_grid)
    return _global_selector


# ═══════════════════════════════════════════════════════════════════
# 便捷函数（可直接导入使用）
# ═══════════════════════════════════════════════════════════════════

def find_best_building(npc, all_buildings, building_type, prefer_empty=True):
    """
    便捷函数：为NPC找到最佳目标建筑
    
    Returns:
        (building, stand_x, stand_y) 或 None
    
    Usage:
        result = find_best_building(npc, buildings, 'MARKET')
        if result:
            building, x, y = result
            npc.set_movement_target(x, y, f"去{building.name}")
    """
    return get_building_selector().find_best_building(
        npc, all_buildings, building_type, prefer_empty
    )

def find_empty_building(npc, all_buildings, building_type):
    """
    便捷函数：只查找完全空闲的建筑
    
    如果没有空闲的，返回 None
    """
    return get_building_selector().find_empty_building(
        npc, all_buildings, building_type
    )

def is_building_crowded(building, threshold=3):
    """
    便捷函数：检查建筑是否拥挤
    """
    return get_building_selector().is_building_crowded(building, threshold)
