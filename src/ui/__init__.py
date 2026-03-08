# --- src/ui/__init__.py ---
"""
UI 模块包

架构设计：
├── manager.py          # UI管理器 (继承 UIBase + UIPanelsMixin + UIDialogsMixin)
├── base.py             # UI基类 (字体、屏幕尺寸)
├── panels.py           # 面板渲染 Mixin
├── dialogs.py          # 对话框渲染 Mixin
└── ...
"""

from .manager import UIManager
from .components import (
    Colors,
    draw_button,
    draw_close_button,
    draw_panel_background,
    draw_panel_header,
    draw_progress_bar,
    draw_health_bar,
    draw_separator,
    draw_section_title,
    draw_tooltip,
    draw_list_header,
    draw_list_row,
)

__all__ = [
    'UIManager',
    'Colors',
    'draw_button',
    'draw_close_button',
    'draw_panel_background',
    'draw_panel_header',
    'draw_progress_bar',
    'draw_health_bar',
    'draw_separator',
    'draw_section_title',
    'draw_tooltip',
    'draw_list_header',
    'draw_list_row',
]
