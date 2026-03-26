# src/live_news_system.py
"""
═══════════════════════════════════════════════════════════════════════════════
【已废弃】大宋实况系统 - 兼容层
═══════════════════════════════════════════════════════════════════════════════

此文件仅用于向后兼容。
所有功能已整合到 src/ui/event_notification.py 中的 EventNotificationManager。

使用方式：
  from src.ui.event_notification import (
      EventNotification,      # 统一数据类
      EventNotificationManager,
      get_notification_manager,
      NewsCategory,
      DilemmaType,
  )
  
  # 或使用旧的别名（兼容）
  from src.live_news_system import LiveNewsItem, get_live_news_manager
"""

# 重导出所有类，保持向后兼容
from src.ui.event_notification import (
    LiveNewsItem,
    EventNotificationManager,
    get_notification_manager,
    NewsCategory,
    DilemmaType,
    LiveNewsItem,  # 别名
)

# 兼容别名
LiveNewsManager = EventNotificationManager


def get_live_news_manager() -> EventNotificationManager:
    """
    【兼容】获取事件管理器
    
    推荐使用 get_notification_manager() 代替
    """
    return get_notification_manager()


# 保留旧的导出，确保所有import都能工作
__all__ = [
    'LiveNewsItem',
    'LiveNewsManager',
    'get_live_news_manager',
    'NewsCategory',
    'DilemmaType',
    # 新名称
    'LiveNewsItem',
    'EventNotificationManager',
    'get_notification_manager',
]