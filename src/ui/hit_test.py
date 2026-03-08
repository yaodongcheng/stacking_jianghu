# --- src/ui/hit_test.py ---
"""
统一UI层级命中检测系统

解决UI点击穿透问题：确保任何UI点击响应时，地图移动是最后一层。

设计思路：
1. 每帧渲染时，各UI组件向 UIHitTest 注册自己的可交互区域
2. 在事件处理阶段，通过 is_ui_blocking(mx, my) 判断是否有UI在该位置
3. 只有当所有UI都没有消费该事件时，才让地图移动逻辑处理

使用方式：
1. 在渲染代码中调用 register_zone() 注册可交互区域
2. 在下一帧开始时调用 clear() 清空上一帧的区域
3. 在事件处理时调用 is_ui_blocking() 判断是否被UI阻挡

区域类型（优先级从高到低）：
- MODAL: 模态对话框（阻止所有其他交互）
- OVERLAY: 覆盖层UI（如系统菜单展开时）
- PANEL: 面板UI
- WIDGET: 普通控件
"""
import pygame
from typing import List, Tuple, Optional

# UI层级优先级常量（数值越大优先级越高）
UI_LAYER_NONE = 0        # 无UI层级（游戏世界）
UI_LAYER_WIDGET = 10     # 普通控件（如小地图）
UI_LAYER_PANEL = 20      # 面板UI（如系统菜单）
UI_LAYER_OVERLAY = 30    # 覆盖层（如展开的下拉菜单）
UI_LAYER_MODAL = 100     # 模态对话框（阻止所有交互）


class UIHitZone:
    """表示一个可交互的UI区域"""
    __slots__ = ('rect', 'layer', 'name')
    
    def __init__(self, rect: pygame.Rect, layer: int = UI_LAYER_WIDGET, name: str = ""):
        self.rect = rect
        self.layer = layer
        self.name = name  # 用于调试
    
    def contains(self, mx: int, my: int) -> bool:
        return self.rect.collidepoint(mx, my)


class UIHitTest:
    """
    UI命中检测管理器（单例模式）
    
    用于统一管理所有UI可交互区域，解决点击穿透问题。
    """
    _instance: Optional['UIHitTest'] = None
    
    def __init__(self):
        self._zones: List[UIHitZone] = []
        self._debug = False  # 调试模式：绘制所有命中区域
    
    @classmethod
    def get_instance(cls) -> 'UIHitTest':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = UIHitTest()
        return cls._instance
    
    def clear(self):
        """
        清空所有注册的UI区域。
        应在每帧开始时调用。
        """
        self._zones.clear()
    
    def register_zone(self, rect: pygame.Rect, layer: int = UI_LAYER_WIDGET, name: str = ""):
        """
        注册一个可交互的UI区域。
        
        Args:
            rect: UI区域的矩形范围
            layer: UI层级（优先级）
            name: 区域名称（用于调试）
        """
        if rect is None:
            return
        zone = UIHitZone(rect, layer, name)
        self._zones.append(zone)
    
    def register_rect(self, x: int, y: int, w: int, h: int, 
                      layer: int = UI_LAYER_WIDGET, name: str = ""):
        """
        注册一个可交互的UI区域（使用坐标和尺寸）。
        """
        rect = pygame.Rect(x, y, w, h)
        self.register_zone(rect, layer, name)
    
    def is_ui_blocking(self, mx: int, my: int, min_layer: int = UI_LAYER_WIDGET) -> bool:
        """
        检测指定位置是否被UI阻挡。
        
        Args:
            mx, my: 鼠标位置
            min_layer: 最小层级阈值，只检测该层级及以上的UI
            
        Returns:
            True 如果该位置被UI阻挡
        """
        for zone in self._zones:
            if zone.layer >= min_layer and zone.contains(mx, my):
                return True
        return False
    
    def get_blocking_zone(self, mx: int, my: int) -> Optional[UIHitZone]:
        """
        获取阻挡指定位置的最高优先级UI区域。
        
        Returns:
            阻挡该位置的UIHitZone，如果没有则返回None
        """
        blocking = None
        max_layer = UI_LAYER_NONE
        for zone in self._zones:
            if zone.contains(mx, my) and zone.layer > max_layer:
                blocking = zone
                max_layer = zone.layer
        return blocking
    
    def get_top_layer_at(self, mx: int, my: int) -> int:
        """
        获取指定位置的最高UI层级。
        
        Returns:
            最高层级值，如果没有UI则返回 UI_LAYER_NONE
        """
        max_layer = UI_LAYER_NONE
        for zone in self._zones:
            if zone.contains(mx, my) and zone.layer > max_layer:
                max_layer = zone.layer
        return max_layer
    
    def has_modal(self) -> bool:
        """
        检测当前是否有模态对话框。
        
        Returns:
            True 如果存在模态对话框
        """
        for zone in self._zones:
            if zone.layer >= UI_LAYER_MODAL:
                return True
        return False
    
    def set_debug(self, enabled: bool):
        """设置调试模式"""
        self._debug = enabled
    
    def draw_debug(self, screen: pygame.Surface):
        """
        绘制调试信息（所有注册的UI区域）
        """
        if not self._debug:
            return
        
        # 定义不同层级的颜色
        layer_colors = {
            UI_LAYER_WIDGET: (100, 100, 255, 80),   # 蓝色
            UI_LAYER_PANEL: (100, 255, 100, 80),    # 绿色
            UI_LAYER_OVERLAY: (255, 255, 100, 80),  # 黄色
            UI_LAYER_MODAL: (255, 100, 100, 80),    # 红色
        }
        
        for zone in self._zones:
            # 选择颜色
            color = layer_colors.get(zone.layer, (200, 200, 200, 80))
            
            # 绘制半透明矩形
            surf = pygame.Surface((zone.rect.w, zone.rect.h), pygame.SRCALPHA)
            surf.fill(color)
            screen.blit(surf, zone.rect.topleft)
            
            # 绘制边框
            border_color = tuple(min(255, c + 50) for c in color[:3])
            pygame.draw.rect(screen, border_color, zone.rect, 1)
            
            # 绘制名称
            if zone.name:
                try:
                    font = pygame.font.SysFont("microsoftyahei,simhei,arial", 12)
                    text_surf = font.render(f"{zone.name} L{zone.layer}", True, (255, 255, 255))
                    screen.blit(text_surf, (zone.rect.x + 2, zone.rect.y + 2))
                except:
                    pass


# 便捷函数
def get_ui_hit_test() -> UIHitTest:
    """获取UI命中检测管理器实例"""
    return UIHitTest.get_instance()


def clear_ui_zones():
    """清空所有UI区域（每帧开始时调用）"""
    get_ui_hit_test().clear()


def register_ui_zone(rect: pygame.Rect, layer: int = UI_LAYER_WIDGET, name: str = ""):
    """注册一个可交互的UI区域"""
    get_ui_hit_test().register_zone(rect, layer, name)


def is_ui_blocking(mx: int, my: int) -> bool:
    """检测指定位置是否被UI阻挡"""
    return get_ui_hit_test().is_ui_blocking(mx, my)
