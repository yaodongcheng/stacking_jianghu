# --- src/ui/manager.py ---
from src.ui.base import UIBase
from src.ui.panels import UIPanelsMixin
from src.ui.dialogs import UIDialogsMixin

class UIManager(UIBase, UIPanelsMixin, UIDialogsMixin):
    """
    UI管理器：聚合了基础绘图、面板组件和对话框组件
    """
    def __init__(self, screen_w, screen_h, ctx=None):
        super().__init__(screen_w, screen_h)
        self._game_ctx = ctx  # 存储游戏上下文，供AI叙事系统使用
        