"""
网格系统基类 - 提供通用的网格坐标转换功能

所有基于网格的系统都应继承此类：
- OccupancyGrid: 防止静止NPC堆叠 (40px精细网格)
- SpatialHash: 加速邻近查询 (200px粗粒度网格)
"""

from typing import Tuple


class BaseGrid:
    """
    网格系统基类
    
    提供：
    - 世界坐标 ↔ 网格坐标转换
    - 网格相关的通用计算
    """
    
    def __init__(self, cell_size: int):
        """
        Args:
            cell_size: 网格单元格大小（像素）
        """
        self.cell_size = cell_size
    
    def world_to_cell(self, x: float, y: float) -> Tuple[int, int]:
        """
        世界坐标转网格坐标
        
        Args:
            x, y: 世界坐标（像素）
        Returns:
            (cell_x, cell_y): 网格坐标
        """
        return (int(x) // self.cell_size, int(y) // self.cell_size)
    
    def cell_to_world(self, cx: int, cy: int) -> Tuple[float, float]:
        """
        网格坐标转世界坐标（返回格子中心点）
        
        Args:
            cx, cy: 网格坐标
        Returns:
            (world_x, world_y): 世界坐标（格子中心）
        """
        return (
            cx * self.cell_size + self.cell_size // 2,
            cy * self.cell_size + self.cell_size // 2
        )
    
    def get_cell_bounds(self, cx: int, cy: int) -> Tuple[int, int, int, int]:
        """
        获取网格单元的世界坐标边界
        
        Args:
            cx, cy: 网格坐标
        Returns:
            (left, top, right, bottom): 世界坐标边界
        """
        left = cx * self.cell_size
        top = cy * self.cell_size
        return (left, top, left + self.cell_size, top + self.cell_size)
    
    def get_nearby_cells(self, cx: int, cy: int, radius: int = 1):
        """
        获取指定网格周围的所有网格坐标
        
        Args:
            cx, cy: 中心网格坐标
            radius: 搜索半径（网格单位），1 表示 3x3
        Yields:
            (cell_x, cell_y): 周围的网格坐标（包括中心）
        """
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                yield (cx + dx, cy + dy)
    
    def distance_in_cells(self, cell1: Tuple[int, int], cell2: Tuple[int, int]) -> int:
        """
        计算两个网格之间的切比雪夫距离（棋盘距离）
        
        Args:
            cell1, cell2: 两个网格坐标
        Returns:
            距离（网格单位）
        """
        return max(abs(cell1[0] - cell2[0]), abs(cell1[1] - cell2[1]))
