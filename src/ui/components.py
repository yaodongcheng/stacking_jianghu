# --- src/ui/components.py ---
"""
UI 通用组件库

提供可复用的 UI 渲染函数:
- 按钮
- 面板背景
- 进度条
- 分隔线
- 工具提示

设计目标：减少 panels.py 和 dialogs.py 中的重复代码
"""

import pygame
from typing import Tuple, Optional


# ═══════════════════════════════════════════════════════════════
# 颜色预设
# ═══════════════════════════════════════════════════════════════

class Colors:
    """标准 UI 颜色"""
    # 背景
    PANEL_BG = (30, 30, 40)
    PANEL_BG_LIGHT = (50, 50, 60)
    PANEL_BG_DARK = (20, 20, 30)
    
    # 边框
    BORDER_NORMAL = (80, 80, 80)
    BORDER_HIGHLIGHT = (150, 150, 150)
    BORDER_GOLD = (200, 180, 100)
    
    # 文字
    TEXT_WHITE = (255, 255, 255)
    TEXT_GRAY = (180, 180, 180)
    TEXT_DARK = (100, 100, 100)
    TEXT_GOLD = (255, 215, 100)
    TEXT_GREEN = (100, 255, 100)
    TEXT_RED = (255, 100, 100)
    TEXT_YELLOW = (255, 255, 100)
    
    # 按钮
    BUTTON_NORMAL = (60, 60, 70)
    BUTTON_HOVER = (80, 80, 100)
    BUTTON_PRESSED = (50, 50, 60)
    BUTTON_DISABLED = (40, 40, 40)
    
    # 特殊
    HEALTH_FULL = (100, 255, 100)
    HEALTH_MED = (255, 255, 100)
    HEALTH_LOW = (255, 150, 50)
    HEALTH_CRIT = (255, 50, 50)


# ═══════════════════════════════════════════════════════════════
# 按钮组件
# ═══════════════════════════════════════════════════════════════

def draw_button(
    screen,
    font,
    text: str,
    x: int, y: int,
    w: int, h: int,
    mx: int, my: int,
    enabled: bool = True,
    style: str = 'normal'
) -> Tuple[pygame.Rect, bool]:
    """
    绘制标准按钮
    
    Args:
        screen: pygame 屏幕
        font: 字体
        text: 按钮文字
        x, y, w, h: 位置和大小
        mx, my: 鼠标位置
        enabled: 是否启用
        style: 样式 ('normal', 'danger', 'success', 'gold')
        
    Returns:
        (rect, is_hover): 按钮区域和是否悬停
    """
    rect = pygame.Rect(x, y, w, h)
    is_hover = rect.collidepoint(mx, my) and enabled
    
    # 根据样式选择颜色
    if style == 'danger':
        bg_normal = (120, 40, 40)
        bg_hover = (180, 60, 60)
        border = (200, 80, 80)
    elif style == 'success':
        bg_normal = (40, 100, 40)
        bg_hover = (60, 140, 60)
        border = (80, 180, 80)
    elif style == 'gold':
        bg_normal = (100, 80, 40)
        bg_hover = (140, 110, 50)
        border = (200, 180, 100)
    else:  # normal
        bg_normal = Colors.BUTTON_NORMAL
        bg_hover = Colors.BUTTON_HOVER
        border = Colors.BORDER_NORMAL
    
    if not enabled:
        bg_color = Colors.BUTTON_DISABLED
        text_color = Colors.TEXT_DARK
        border = (60, 60, 60)
    else:
        bg_color = bg_hover if is_hover else bg_normal
        text_color = Colors.TEXT_WHITE
    
    # 绘制
    pygame.draw.rect(screen, bg_color, rect, border_radius=6)
    pygame.draw.rect(screen, border, rect, 2, border_radius=6)
    
    text_surf = font.render(text, True, text_color)
    text_rect = text_surf.get_rect(center=rect.center)
    screen.blit(text_surf, text_rect)
    
    return (rect, is_hover)


def draw_close_button(
    screen,
    font,
    x: int, y: int,
    mx: int, my: int,
    size: int = 24
) -> Tuple[pygame.Rect, bool]:
    """
    绘制关闭按钮 (X)
    
    Returns:
        (rect, is_hover)
    """
    rect = pygame.Rect(x, y, size, size)
    is_hover = rect.collidepoint(mx, my)
    
    bg_color = (180, 60, 60) if is_hover else (120, 40, 40)
    border_color = (200, 80, 80) if is_hover else (150, 60, 60)
    
    pygame.draw.rect(screen, bg_color, rect, border_radius=4)
    pygame.draw.rect(screen, border_color, rect, 1, border_radius=4)
    
    x_surf = font.render("×", True, Colors.TEXT_WHITE)
    x_rect = x_surf.get_rect(center=rect.center)
    screen.blit(x_surf, x_rect)
    
    return (rect, is_hover)


# ═══════════════════════════════════════════════════════════════
# 面板组件
# ═══════════════════════════════════════════════════════════════

def draw_panel_background(
    screen,
    x: int, y: int,
    w: int, h: int,
    alpha: int = 230,
    border: bool = True,
    border_radius: int = 10
):
    """绘制面板背景"""
    # 半透明背景
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((*Colors.PANEL_BG, alpha))
    screen.blit(surf, (x, y))
    
    if border:
        pygame.draw.rect(screen, Colors.BORDER_HIGHLIGHT, (x, y, w, h), 2, border_radius=border_radius)


def draw_panel_header(
    screen,
    font,
    title: str,
    x: int, y: int,
    w: int,
    color: Tuple[int, int, int] = Colors.TEXT_WHITE
):
    """绘制面板标题"""
    title_surf = font.render(f"══ {title} ══", True, color)
    title_rect = title_surf.get_rect(center=(x + w // 2, y + 20))
    screen.blit(title_surf, title_rect)


# ═══════════════════════════════════════════════════════════════
# 进度条组件
# ═══════════════════════════════════════════════════════════════

def draw_progress_bar(
    screen,
    x: int, y: int,
    w: int, h: int,
    progress: float,
    bg_color: Tuple[int, int, int] = (50, 50, 50),
    fill_color: Optional[Tuple[int, int, int]] = None,
    border: bool = True
):
    """
    绘制进度条
    
    Args:
        progress: 0.0 ~ 1.0
        fill_color: 如果为 None，根据进度自动选择颜色
    """
    progress = max(0.0, min(1.0, progress))
    
    # 背景
    pygame.draw.rect(screen, bg_color, (x, y, w, h), border_radius=h//2)
    
    # 进度
    if fill_color is None:
        if progress >= 0.8:
            fill_color = Colors.HEALTH_FULL
        elif progress >= 0.5:
            fill_color = Colors.HEALTH_MED
        elif progress >= 0.2:
            fill_color = Colors.HEALTH_LOW
        else:
            fill_color = Colors.HEALTH_CRIT
    
    fill_w = int(w * progress)
    if fill_w > 0:
        pygame.draw.rect(screen, fill_color, (x, y, fill_w, h), border_radius=h//2)
    
    if border:
        pygame.draw.rect(screen, Colors.BORDER_NORMAL, (x, y, w, h), 1, border_radius=h//2)


def draw_health_bar(
    screen,
    x: int, y: int,
    w: int, h: int,
    current: int,
    maximum: int
):
    """绘制生命条"""
    progress = current / max(maximum, 1)
    draw_progress_bar(screen, x, y, w, h, progress)


# ═══════════════════════════════════════════════════════════════
# 分隔线和装饰
# ═══════════════════════════════════════════════════════════════

def draw_separator(
    screen,
    x: int, y: int,
    w: int,
    color: Tuple[int, int, int] = Colors.BORDER_NORMAL
):
    """绘制水平分隔线"""
    pygame.draw.line(screen, color, (x, y), (x + w, y), 1)


def draw_section_title(
    screen,
    font,
    title: str,
    x: int, y: int,
    color: Tuple[int, int, int] = Colors.TEXT_GOLD
):
    """绘制小节标题"""
    title_surf = font.render(f"[ {title} ]", True, color)
    screen.blit(title_surf, (x, y))


# ═══════════════════════════════════════════════════════════════
# 工具提示
# ═══════════════════════════════════════════════════════════════

def draw_tooltip(
    screen,
    font,
    text: str,
    x: int, y: int,
    max_width: int = 300
):
    """绘制工具提示"""
    padding = 8
    
    # 简单文字测量
    text_surf = font.render(text, True, Colors.TEXT_WHITE)
    text_w = text_surf.get_width()
    text_h = text_surf.get_height()
    
    # 背景
    bg_w = min(text_w + padding * 2, max_width)
    bg_h = text_h + padding * 2
    
    # 确保不超出屏幕
    screen_w, screen_h = screen.get_size()
    if x + bg_w > screen_w:
        x = screen_w - bg_w - 10
    if y + bg_h > screen_h:
        y = y - bg_h - 10
    
    # 绘制
    bg_surf = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
    bg_surf.fill((20, 20, 30, 240))
    screen.blit(bg_surf, (x, y))
    
    pygame.draw.rect(screen, Colors.BORDER_GOLD, (x, y, bg_w, bg_h), 1, border_radius=4)
    screen.blit(text_surf, (x + padding, y + padding))


# ═══════════════════════════════════════════════════════════════
# 列表/表格
# ═══════════════════════════════════════════════════════════════

def draw_list_header(
    screen,
    font,
    headers: list,
    col_widths: list,
    x: int, y: int,
    color: Tuple[int, int, int] = Colors.TEXT_GOLD
):
    """绘制列表表头"""
    current_x = x
    for i, header in enumerate(headers):
        text_surf = font.render(header, True, color)
        screen.blit(text_surf, (current_x, y))
        if i < len(col_widths):
            current_x += col_widths[i]


def draw_list_row(
    screen,
    font,
    values: list,
    colors: list,
    col_widths: list,
    x: int, y: int,
    row_h: int,
    mx: int, my: int
) -> Tuple[pygame.Rect, bool]:
    """
    绘制列表行
    
    Returns:
        (row_rect, is_hover)
    """
    total_w = sum(col_widths)
    row_rect = pygame.Rect(x - 5, y - 2, total_w + 10, row_h)
    is_hover = row_rect.collidepoint(mx, my)
    
    # 悬停高亮
    if is_hover:
        highlight = pygame.Surface((row_rect.w, row_rect.h), pygame.SRCALPHA)
        highlight.fill((255, 255, 255, 30))
        screen.blit(highlight, row_rect.topleft)
    
    # 绘制各列
    current_x = x
    for i, value in enumerate(values):
        color = colors[i] if i < len(colors) else Colors.TEXT_WHITE
        text_surf = font.render(str(value), True, color)
        screen.blit(text_surf, (current_x, y))
        if i < len(col_widths):
            current_x += col_widths[i]
    
    return (row_rect, is_hover)
