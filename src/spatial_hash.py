"""
空间哈希网格 - 用于加速邻近查询
将 O(n²) 的暴力搜索降低到 O(n) 的局部查询

设计特点：
1. 惰性更新：只在需要时重建网格
2. 缓存友好：连续内存存储同一格子的实体
3. 零 GC 压力：复用列表对象
4. 继承 BaseGrid 提供通用网格功能
"""
from typing import List, Dict, Set, Tuple, Optional, Any
import math

from src.grid_base import BaseGrid


class SpatialHash(BaseGrid):
    """
    空间哈希网格 - 继承自 BaseGrid
    
    用于加速 AI 感知和碰撞检测的邻近查询
    
    使用方法：
        1. 每帧开始调用 rebuild(all_entities) 重建网格
        2. 查询邻近实体调用 query_radius(entity, radius)
    """
    
    def __init__(self, cell_size: int = 200):
        """
        Args:
            cell_size: 网格单元格大小（像素），应该接近常用的感知半径
                       过小：查询时需要检查很多格子
                       过大：每个格子实体过多，失去分区优势
        """
        super().__init__(cell_size)  # 调用基类构造函数
        self._grid: Dict[Tuple[int, int], List[Any]] = {}
        self._entity_cells: Dict[int, Tuple[int, int]] = {}  # entity.id -> cell
        self._version = 0  # 版本号，用于检测是否需要重建
    
    def rebuild(self, entities: List[Any]) -> None:
        """
        重建整个网格（每帧调用一次）
        
        Args:
            entities: 所有需要空间查询的实体（需要有 rect 和 id 属性）
        """
        # 清空旧数据（复用字典对象，减少 GC）
        self._grid.clear()
        self._entity_cells.clear()
        self._version += 1
        
        for entity in entities:
            if not hasattr(entity, 'rect'):
                continue
            
            cell = self._get_cell(entity.rect.centerx, entity.rect.centery)
            
            # 插入网格
            if cell not in self._grid:
                self._grid[cell] = []
            self._grid[cell].append(entity)
            
            # 记录实体所在格子
            eid = getattr(entity, 'id', id(entity))
            self._entity_cells[eid] = cell
    
    def _get_cell(self, x: float, y: float) -> Tuple[int, int]:
        """计算坐标所属的网格单元（使用基类方法）"""
        return self.world_to_cell(x, y)
    
    def query_radius(self, entity: Any, radius: float) -> List[Any]:
        """
        查询指定半径内的所有实体（不包含自己）
        
        Args:
            entity: 查询中心实体
            radius: 查询半径（像素）
        
        Returns:
            半径内的实体列表
        """
        if not hasattr(entity, 'rect'):
            return []
        
        cx, cy = entity.rect.centerx, entity.rect.centery
        eid = getattr(entity, 'id', id(entity))
        
        # 计算需要检查的网格范围
        cell_radius = int(math.ceil(radius / self.cell_size))
        center_cell = self._get_cell(cx, cy)
        
        results = []
        radius_sq = radius * radius  # 用平方避免 sqrt
        
        # 遍历周围的格子
        for dx in range(-cell_radius, cell_radius + 1):
            for dy in range(-cell_radius, cell_radius + 1):
                cell = (center_cell[0] + dx, center_cell[1] + dy)
                cell_entities = self._grid.get(cell)
                if not cell_entities:
                    continue
                
                # 检查每个实体
                for other in cell_entities:
                    other_id = getattr(other, 'id', id(other))
                    if other_id == eid:
                        continue
                    
                    # 快速距离检测（平方比较）
                    dist_sq = (cx - other.rect.centerx) ** 2 + (cy - other.rect.centery) ** 2
                    if dist_sq <= radius_sq:
                        results.append(other)
        
        return results
    
    def query_cell(self, x: float, y: float) -> List[Any]:
        """
        查询指定坐标所在格子的所有实体
        """
        cell = self._get_cell(x, y)
        return self._grid.get(cell, [])
    
    def get_nearby_cells(self, entity: Any, cell_range: int = 1) -> List[Any]:
        """
        获取实体周围若干格范围内的所有实体（比 query_radius 更快但不精确）
        
        Args:
            entity: 中心实体
            cell_range: 格子范围（1 表示 3x3 的 9 格）
        """
        if not hasattr(entity, 'rect'):
            return []
        
        eid = getattr(entity, 'id', id(entity))
        center_cell = self._get_cell(entity.rect.centerx, entity.rect.centery)
        
        results = []
        for dx in range(-cell_range, cell_range + 1):
            for dy in range(-cell_range, cell_range + 1):
                cell = (center_cell[0] + dx, center_cell[1] + dy)
                cell_entities = self._grid.get(cell)
                if cell_entities:
                    for other in cell_entities:
                        if getattr(other, 'id', id(other)) != eid:
                            results.append(other)
        
        return results


# ═══════════════════════════════════════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════════════════════════════════════
_spatial_hash: Optional[SpatialHash] = None


def get_spatial_hash(cell_size: int = 200) -> SpatialHash:
    """获取全局空间哈希实例"""
    global _spatial_hash
    if _spatial_hash is None:
        _spatial_hash = SpatialHash(cell_size)
    return _spatial_hash
