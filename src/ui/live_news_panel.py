# src/ui/live_news_panel.py
"""
═══════════════════════════════════════════════════════════════════════════════
【大宋实况】新闻面板 - 当前事件 + 历史事件查看
═══════════════════════════════════════════════════════════════════════════════

功能：
  1. 显示当前活跃的新闻事件
  2. 显示历史新闻事件（可滚动）
  3. 点击查看事件详情
  4. 筛选功能（按分类、按优先级）
"""

import pygame
import time
import os
from pathlib import Path as PyPath
from typing import Optional, List, Callable, Tuple
from enum import Enum

from src.ui.event_notification import (
    EventNotification, EventNotificationManager, 
    get_notification_manager, NewsCategory,
    draw_event_card
)
from src.definitions import SIDEBAR_W, DEBUG_LIVE_NEWS_TEST_EVENT
from src.utils import resource_path


class NewsTab(Enum):
    """新闻标签页"""
    CURRENT = "当前"
    HISTORY = "历史"


class LiveNewsPanel:
    """
    大宋实况新闻面板
    
    显示当前活跃事件和历史事件的完整列表
    """
    
    # 布局
    PANEL_WIDTH = 420
    PANEL_HEIGHT = 550
    HEADER_HEIGHT = 50
    TAB_HEIGHT = 36
    ITEM_HEIGHT = 80  # 与 EventNotificationManager 保持一致
    ITEM_MARGIN = 10  # 与 EventNotificationManager 保持一致
    PADDING = 16
    SCROLL_WIDTH = 8
    
    # 头像缓存（复用通知管理器的缓存）
    _shared_avatar_cache: dict = {}
    
    # 颜色
    COLOR_BG = (25, 23, 35, 245)
    COLOR_HEADER = (35, 32, 50)
    COLOR_TAB_ACTIVE = (60, 80, 120)
    COLOR_TAB_INACTIVE = (40, 38, 55)
    COLOR_ITEM_BG = (38, 35, 52)
    COLOR_ITEM_HOVER = (50, 48, 70)
    COLOR_ITEM_UNREAD = (45, 50, 70)
    COLOR_BORDER = (70, 65, 90)
    COLOR_TEXT = (240, 240, 250)
    COLOR_TEXT_DIM = (160, 160, 180)
    COLOR_TEXT_MUTED = (120, 120, 140)
    COLOR_ACCENT = (100, 150, 255)
    COLOR_URGENT = (255, 120, 100)
    COLOR_SCROLL = (80, 75, 100)
    COLOR_SCROLL_THUMB = (120, 115, 150)
    
    # 分类颜色
    CATEGORY_COLORS = {
        NewsCategory.ECONOMIC: (255, 200, 80),
        NewsCategory.SOCIAL: (100, 200, 255),
        NewsCategory.MORAL: (200, 150, 255),
        NewsCategory.MARTIAL: (255, 100, 100),
        NewsCategory.SUPERNATURAL: (100, 255, 180),
        NewsCategory.POLITICAL: (255, 180, 100),
    }
    
    # 分类名称
    CATEGORY_NAMES = {
        NewsCategory.ECONOMIC: "经济",
        NewsCategory.SOCIAL: "社会",
        NewsCategory.MORAL: "道德",
        NewsCategory.MARTIAL: "武林",
        NewsCategory.SUPERNATURAL: "奇闻",
        NewsCategory.POLITICAL: "官场",
    }
    
    def __init__(self, screen_w: int, screen_h: int):
        self.screen_w = screen_w
        self.screen_h = screen_h
        
        # 面板位置（居中偏上）
        self.panel_x = (screen_w - SIDEBAR_W - self.PANEL_WIDTH) // 2
        self.panel_y = (screen_h - self.PANEL_HEIGHT) // 2 - 30
        
        # 状态
        self.visible = False
        self.current_tab = NewsTab.CURRENT
        self.scroll_offset = 0
        self.max_scroll = 0
        self.hovered_item_index = -1
        self.is_scrolling = False
        self.scroll_drag_start_y = 0
        self.scroll_drag_start_offset = 0
        
        # 字体缓存
        self._font_cache = {}
        
        # 回调
        self.on_item_click: Optional[Callable[[EventNotification], None]] = None
        self.on_close: Optional[Callable[[], None]] = None
        
        # 动画
        self.open_progress = 0.0
        self.target_progress = 0.0
        
        # 【调试】添加测试事件到历史
        if DEBUG_LIVE_NEWS_TEST_EVENT:
            self._add_test_event()
    
    def _add_test_event(self):
        """添加调试测试事件 - 添加多个不同场景的事件以测试布局
        
        【角色说明】使用 npc_data.csv 中实际存在的角色：
        - 1000:方承意, 1001:无情, 1002:林冲, 1003:高衙内, 1004:高大胜
        - 1005:张青, 1006:郁芊芊, 1007:孙二娘, 1008:王小乐, 1009:李师师
        - 1010:袁桐, 1011:孙小溪, 1012:鲁智深, 1013:弥乐, 1014:阿禅
        - 1015:洪小六, 1016:赵师爷, 1017:铁牛, 1018:钱掌柜, 1019:老李头
        - 1020:小翠, 1021:黑风大王, 1022:山贼甲, 1023:山贼乙, 1024:泼皮牛二
        """
        from src.ui.live_snapshot_panel import LiveSnapshotData
        from src.live_news_system import LiveNewsItem, NewsCategory, DilemmaType
        
        # 基础时间（当前时间），每个事件间隔5分钟
        base_time = time.time()
        
        # ═══════════════════════════════════════════════════════════════════════
        # 测试事件1：标准事件（2个当事人）- 最早发生（20分钟前）
        # 使用角色：郁芊芊(1006) vs 泼皮牛二(1024) - 商会与泼皮的冲突
        # ═══════════════════════════════════════════════════════════════════════
        test_news_1 = LiveNewsItem(
            id="test_event_001",
            title="【爆款】甜水巷商会与泼皮发生冲突！",
            description="郁芊芊的商队运送贵重布料途中，被泼皮牛二当街拦路勒索。牛二声称要收'过路费'，否则不让通行。郁芊芊不愿屈服，双方僵持不下。",
            category=NewsCategory.SOCIAL,
            dilemma_type=DilemmaType.JUSTICE,
            actor_ids=[1006, 1024],  # 郁芊芊, 泼皮牛二
            actor_names=["郁芊芊", "泼皮牛二"],
            location="无更市甜水巷",
            choices=[
                {"text": "帮助郁芊芊赶走泼皮", "effect": "JUSTICE:+20;FAME:+10"},
                {"text": "暗中调解，各退一步", "effect": "INTEL:+15;GOLD:-30"},
                {"text": "静观其变", "effect": "NEUTRAL"}
            ],
            priority=4,
            auto_popup=False,
            tags=["郁芊芊", "泼皮牛二", "商会", "勒索"],
            comments=[
                {"user": "路人甲", "text": "这泼皮太可恶了，必须严惩！", "type": "支持"},
                {"user": "吃瓜群众", "text": "郁大小姐太可怜了，希望有人能帮她", "type": "中立"},
            ],
            heat_score=25888,
            image_prompt="A dramatic scene in ancient Chinese market..."
        )
        snapshot_1 = LiveSnapshotData(
            title=test_news_1.title,
            description=test_news_1.description,
            image_url="placeholder",
            heat_score=test_news_1.heat_score,
            tags=test_news_1.tags,
            comments=test_news_1.comments,
            choices=test_news_1.choices,
            actor_names=test_news_1.actor_names,
            news_item=test_news_1
        )
        test_news_1.snapshot_data = snapshot_1
        test_news_1.is_resolved = False  # 未解决
        test_news_1.read = False
        test_news_1.created_at = base_time - 20 * 60  # 20分钟前
        
        # ═══════════════════════════════════════════════════════════════════════
        # 测试事件2：多个当事人（测试头像和名字省略）- 15分钟前
        # 使用角色：黑风寨众人 - 黑风大王(1021), 山贼甲(1022), 山贼乙(1023) + 泼皮牛二(1024) + 洪小六(1015)
        # ═══════════════════════════════════════════════════════════════════════
        test_news_2 = LiveNewsItem(
            id="test_event_002",
            title="黑风寨众匪当街斗殴引发骚乱，路人纷纷躲避",
            subtitle="多人受伤，官府已介入调查",
            category=NewsCategory.MARTIAL,
            actor_ids=[1021, 1022, 1023, 1024, 1015],
            actor_names=["黑风大王", "山贼甲", "山贼乙", "泼皮牛二", "洪小六"],
            location="无更市东街",
            choices=[
                {"text": "上前制止", "effect": "FAME:+30"},
                {"text": "暗中观察", "effect": "NEUTRAL"},
            ],
            priority=3,
            tags=["黑风寨", "斗殴", "骚乱"],
            comments=[],
            heat_score=15234,
        )
        snapshot_2 = LiveSnapshotData(
            title=test_news_2.title,
            description=test_news_2.description or test_news_2.subtitle,
            image_url="placeholder",
            heat_score=test_news_2.heat_score,
            tags=test_news_2.tags,
            comments=test_news_2.comments,
            choices=test_news_2.choices,
            actor_names=test_news_2.actor_names,
            news_item=test_news_2
        )
        test_news_2.snapshot_data = snapshot_2
        test_news_2.is_resolved = False  # 未解决
        test_news_2.read = False
        test_news_2.created_at = base_time - 15 * 60  # 15分钟前
        
        # ═══════════════════════════════════════════════════════════════════════
        # 测试事件3：超长标题（测试省略）- 10分钟前
        # 使用角色：老李头(1019) - 城郊老农，负责看守粮仓
        # ═══════════════════════════════════════════════════════════════════════
        test_news_3 = LiveNewsItem(
            id="test_event_003",
            title="【紧急】无更市粮仓突发大火，火势蔓延至周边商铺，百姓哭喊求救，情况万分危急！",
            subtitle="老李头呼救，火势凶猛",
            category=NewsCategory.SOCIAL,
            actor_ids=[1019],  # 老李头
            actor_names=["老李头"],
            location="无更市粮仓",
            choices=[{"text": "组织救火", "effect": "FAME:+50"}],
            priority=5,  # 最高优先级
            tags=["火灾", "紧急"],
            comments=[],
            heat_score=99999,
        )
        snapshot_3 = LiveSnapshotData(
            title=test_news_3.title,
            description=test_news_3.description or test_news_3.subtitle,
            image_url="placeholder",
            heat_score=test_news_3.heat_score,
            tags=test_news_3.tags,
            comments=test_news_3.comments,
            choices=test_news_3.choices,
            actor_names=test_news_3.actor_names,
            news_item=test_news_3
        )
        test_news_3.snapshot_data = snapshot_3
        test_news_3.is_resolved = False  # 未解决，显示在"当前"tab
        test_news_3.read = False
        test_news_3.created_at = base_time - 10 * 60  # 10分钟前
        
        # ═══════════════════════════════════════════════════════════════════════
        # 测试事件4：无当事人（系统事件）- 5分钟前（最新）
        # 使用角色：弥乐(1013) - 以算命为幌子的骗子和尚，可以解读天象
        # ═══════════════════════════════════════════════════════════════════════
        test_news_4 = LiveNewsItem(
            id="test_event_004",
            title="天降异象，红月当空",
            subtitle="算命和尚弥乐称此乃大凶之兆",
            category=NewsCategory.SUPERNATURAL,
            actor_ids=[1013],  # 弥乐
            actor_names=["弥乐"],
            location="无更市全城",
            choices=[{"text": "观测天象", "effect": "INTEL:+10"}],
            priority=2,
            tags=["天象", "异象"],
            comments=[],
            heat_score=5000,
        )
        snapshot_4 = LiveSnapshotData(
            title=test_news_4.title,
            description=test_news_4.description or test_news_4.subtitle,
            image_url="placeholder",
            heat_score=test_news_4.heat_score,
            tags=test_news_4.tags,
            comments=test_news_4.comments,
            choices=test_news_4.choices,
            actor_names=test_news_4.actor_names,
            news_item=test_news_4
        )
        test_news_4.snapshot_data = snapshot_4
        test_news_4.is_resolved = False  # 未解决
        test_news_4.read = False
        test_news_4.created_at = base_time - 5 * 60  # 5分钟前（最新）
        
        # 添加到通知管理器
        mgr = get_notification_manager()
        mgr.add_event(test_news_1)
        mgr.add_event(test_news_2)
        mgr.add_event(test_news_3)
        mgr.add_event(test_news_4)
        
        print(f"[LiveNewsPanel] 已添加 {4} 个调试测试事件")
        
    def _get_font(self, size: int) -> pygame.font.Font:
        """获取缓存字体"""
        if size not in self._font_cache:
            self._font_cache[size] = pygame.font.SysFont(
                "microsoftyahei,simhei,pingfangsc,arial", size
            )
        return self._font_cache[size]
    
    def show(self):
        """显示面板"""
        self.visible = True
        self.target_progress = 1.0
        self.scroll_offset = 0
        print("[LiveNewsPanel] 打开大宋实况面板")
    
    def hide(self):
        """隐藏面板"""
        self.target_progress = 0.0
        print("[LiveNewsPanel] 关闭大宋实况面板")
    
    def toggle(self):
        """切换显示状态"""
        if self.visible and self.open_progress > 0.5:
            self.hide()
        else:
            self.show()
    
    def is_open(self) -> bool:
        """是否正在显示"""
        return self.visible and self.open_progress > 0.1
    
    def update(self, dt_ms: int):
        """更新动画"""
        # 开关动画
        speed = dt_ms / 200.0  # 200ms完成动画
        if self.open_progress < self.target_progress:
            self.open_progress = min(self.target_progress, self.open_progress + speed)
        elif self.open_progress > self.target_progress:
            self.open_progress = max(self.target_progress, self.open_progress - speed)
            if self.open_progress <= 0:
                self.visible = False
    
    def _get_items(self) -> List[EventNotification]:
        """获取当前标签页的事件列表
        
        当前tab: 未处理的事件 (is_resolved=False)
        历史tab: 已处理的事件 (is_resolved=True)
        
        按 created_at 时间倒序排列（最新的在前）
        """
        mgr = get_notification_manager()
        # 获取所有历史事件，按时间倒序排列
        all_events = sorted(
            mgr.get_history(),
            key=lambda e: e.created_at,
            reverse=True  # 最新的在前
        )
        
        if self.current_tab == NewsTab.CURRENT:
            # 当前tab: 未处理的事件
            return [e for e in all_events if not e.is_resolved]
        else:
            # 历史tab: 已处理的事件
            return [e for e in all_events if e.is_resolved]
    
    def _get_content_rect(self) -> pygame.Rect:
        """获取内容区域"""
        x = self.panel_x + self.PADDING
        y = self.panel_y + self.HEADER_HEIGHT + self.TAB_HEIGHT + 10
        w = self.PANEL_WIDTH - self.PADDING * 2 - self.SCROLL_WIDTH - 4
        h = self.PANEL_HEIGHT - self.HEADER_HEIGHT - self.TAB_HEIGHT - 30
        return pygame.Rect(x, y, w, h)
    
    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        处理事件
        
        Returns:
            是否消费了事件
        """
        if not self.visible or self.open_progress < 0.5:
            return False
        
        panel_rect = pygame.Rect(
            self.panel_x, self.panel_y, 
            self.PANEL_WIDTH, self.PANEL_HEIGHT
        )
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            
            # 点击面板外关闭
            if not panel_rect.collidepoint(mx, my):
                self.hide()
                return True
            
            # 点击关闭按钮
            close_rect = pygame.Rect(
                self.panel_x + self.PANEL_WIDTH - 40,
                self.panel_y + 10,
                30, 30
            )
            if close_rect.collidepoint(mx, my):
                self.hide()
                return True
            
            # 点击标签页
            tab_y = self.panel_y + self.HEADER_HEIGHT
            for i, tab in enumerate(NewsTab):
                tab_rect = pygame.Rect(
                    self.panel_x + 10 + i * 90,
                    tab_y,
                    80, self.TAB_HEIGHT - 4
                )
                if tab_rect.collidepoint(mx, my):
                    if self.current_tab != tab:
                        self.current_tab = tab
                        self.scroll_offset = 0
                    return True
            
            # 滚动条拖拽
            scroll_rect = self._get_scroll_rect()
            if scroll_rect and scroll_rect.collidepoint(mx, my):
                self.is_scrolling = True
                self.scroll_drag_start_y = my
                self.scroll_drag_start_offset = self.scroll_offset
                return True
            
            # 点击事件项
            content_rect = self._get_content_rect()
            if content_rect.collidepoint(mx, my):
                items = self._get_items()
                for i, item in enumerate(items):
                    item_y = content_rect.y + i * (self.ITEM_HEIGHT + self.ITEM_MARGIN) - self.scroll_offset
                    if item_y > content_rect.y - self.ITEM_HEIGHT and item_y < content_rect.bottom:
                        item_rect = pygame.Rect(
                            content_rect.x, item_y,
                            content_rect.width, self.ITEM_HEIGHT
                        )
                        if item_rect.collidepoint(mx, my):
                            self._on_item_click(item)
                            return True
            
            return True  # 点击面板内都消费事件
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if self.is_scrolling:
                self.is_scrolling = False
                return True
        
        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            
            # 拖拽滚动条
            if self.is_scrolling:
                delta_y = my - self.scroll_drag_start_y
                content_rect = self._get_content_rect()
                items = self._get_items()
                total_height = len(items) * (self.ITEM_HEIGHT + self.ITEM_MARGIN)
                if total_height > content_rect.height:
                    scroll_range = content_rect.height - 40  # 滚动条滑块区域
                    scroll_ratio = delta_y / scroll_range
                    new_offset = self.scroll_drag_start_offset + scroll_ratio * (total_height - content_rect.height)
                    self.scroll_offset = max(0, min(new_offset, total_height - content_rect.height))
                return True
            
            # 悬停检测
            content_rect = self._get_content_rect()
            self.hovered_item_index = -1
            if content_rect.collidepoint(mx, my):
                items = self._get_items()
                for i, item in enumerate(items):
                    item_y = content_rect.y + i * (self.ITEM_HEIGHT + self.ITEM_MARGIN) - self.scroll_offset
                    if item_y > content_rect.y - self.ITEM_HEIGHT and item_y < content_rect.bottom:
                        item_rect = pygame.Rect(
                            content_rect.x, item_y,
                            content_rect.width, self.ITEM_HEIGHT
                        )
                        if item_rect.collidepoint(mx, my):
                            self.hovered_item_index = i
                            break
        
        elif event.type == pygame.MOUSEWHEEL:
            if panel_rect.collidepoint(pygame.mouse.get_pos()):
                # 滚轮滚动
                content_rect = self._get_content_rect()
                items = self._get_items()
                total_height = len(items) * (self.ITEM_HEIGHT + self.ITEM_MARGIN)
                if total_height > content_rect.height:
                    self.scroll_offset -= event.y * 40
                    self.scroll_offset = max(0, min(self.scroll_offset, total_height - content_rect.height))
                return True
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.hide()
                return True
        
        return False
    
    def _get_scroll_rect(self) -> Optional[pygame.Rect]:
        """获取滚动条区域"""
        content_rect = self._get_content_rect()
        items = self._get_items()
        total_height = len(items) * (self.ITEM_HEIGHT + self.ITEM_MARGIN)
        
        if total_height <= content_rect.height:
            return None
        
        # 滚动条轨道
        track_x = content_rect.right + 4
        track_y = content_rect.y
        track_h = content_rect.height
        
        # 滑块大小和位置
        thumb_ratio = content_rect.height / total_height
        thumb_h = max(30, int(track_h * thumb_ratio))
        scroll_range = total_height - content_rect.height
        thumb_y = track_y + int((self.scroll_offset / scroll_range) * (track_h - thumb_h)) if scroll_range > 0 else track_y
        
        return pygame.Rect(track_x, thumb_y, self.SCROLL_WIDTH, thumb_h)
    
    def _on_item_click(self, item: EventNotification):
        """点击事件项"""
        print(f"[LiveNewsPanel] 点击事件: {item.title}")
        print(f"[LiveNewsPanel] snapshot_data 存在: {item.snapshot_data is not None}")
        if item.snapshot_data:
            print(f"[LiveNewsPanel] snapshot_data.title: {getattr(item.snapshot_data, 'title', 'N/A')}")
            print(f"[LiveNewsPanel] snapshot_data.choices: {getattr(item.snapshot_data, 'choices', [])}")
        else:
            print(f"[LiveNewsPanel] [!] 事件没有 snapshot_data！检查 Director 是否正确设置")
            print(f"[LiveNewsPanel] item 属性: id={item.id}, title={item.title}")
            print(f"[LiveNewsPanel] item.headline={item.headline}, item.description={item.description}")
        item.read = True
        if self.on_item_click:
            self.on_item_click(item)
    
    def draw(self, screen: pygame.Surface):
        """绘制面板"""
        if not self.visible or self.open_progress <= 0:
            return
        
        # 应用动画缩放
        scale = self._ease_out_back(self.open_progress)
        alpha = int(255 * self.open_progress)
        
        # 创建面板surface
        panel_surf = pygame.Surface((self.PANEL_WIDTH, self.PANEL_HEIGHT), pygame.SRCALPHA)
        
        # 背景
        pygame.draw.rect(panel_surf, self.COLOR_BG, 
                         (0, 0, self.PANEL_WIDTH, self.PANEL_HEIGHT), 
                         border_radius=12)
        pygame.draw.rect(panel_surf, self.COLOR_BORDER, 
                         (0, 0, self.PANEL_WIDTH, self.PANEL_HEIGHT), 
                         2, border_radius=12)
        
        # 头部
        self._draw_header(panel_surf)
        
        # 标签页
        self._draw_tabs(panel_surf)
        
        # 内容区域
        self._draw_content(panel_surf)
        
        # 绘制到屏幕（带缩放动画）
        if scale < 1.0:
            scaled_w = int(self.PANEL_WIDTH * scale)
            scaled_h = int(self.PANEL_HEIGHT * scale)
            scaled_surf = pygame.transform.smoothscale(panel_surf, (scaled_w, scaled_h))
            x = self.panel_x + (self.PANEL_WIDTH - scaled_w) // 2
            y = self.panel_y + (self.PANEL_HEIGHT - scaled_h) // 2
            screen.blit(scaled_surf, (x, y))
        else:
            screen.blit(panel_surf, (self.panel_x, self.panel_y))
    
    def _draw_header(self, surf: pygame.Surface):
        """绘制头部"""
        # 头部背景
        pygame.draw.rect(surf, self.COLOR_HEADER,
                         (0, 0, self.PANEL_WIDTH, self.HEADER_HEIGHT),
                         border_top_left_radius=12, border_top_right_radius=12)
        
        # 标题
        font_title = self._get_font(20)
        title_surf = font_title.render("[报] 大宋实况", True, self.COLOR_TEXT)
        surf.blit(title_surf, (self.PADDING, (self.HEADER_HEIGHT - title_surf.get_height()) // 2))
        
        # 统计信息
        mgr = get_notification_manager()
        unread = mgr.get_unread_count()
        total_history = mgr.get_history_count()
        
        font_stat = self._get_font(12)
        stat_text = f"未读 {unread} | 历史 {total_history} 条"
        stat_surf = font_stat.render(stat_text, True, self.COLOR_TEXT_DIM)
        surf.blit(stat_surf, (self.PANEL_WIDTH - stat_surf.get_width() - 50, 
                              (self.HEADER_HEIGHT - stat_surf.get_height()) // 2))
        
        # 关闭按钮
        close_font = self._get_font(18)
        close_surf = close_font.render("X", True, self.COLOR_TEXT_DIM)
        surf.blit(close_surf, (self.PANEL_WIDTH - 32, 14))
    
    def _draw_tabs(self, surf: pygame.Surface):
        """绘制标签页"""
        tab_y = self.HEADER_HEIGHT + 4
        font_tab = self._get_font(14)
        
        # 只从历史记录获取（与 _get_items 逻辑一致，避免重复）
        mgr = get_notification_manager()
        all_events = mgr.get_history()
        
        for i, tab in enumerate(NewsTab):
            x = 10 + i * 90
            is_active = (tab == self.current_tab)
            
            # 标签背景
            color = self.COLOR_TAB_ACTIVE if is_active else self.COLOR_TAB_INACTIVE
            pygame.draw.rect(surf, color, (x, tab_y, 80, self.TAB_HEIGHT - 8), border_radius=6)
            
            # 标签文字
            text_color = self.COLOR_TEXT if is_active else self.COLOR_TEXT_DIM
            tab_text = tab.value
            
            # 根据 is_resolved 状态统计数量
            if tab == NewsTab.CURRENT:
                count = len([e for e in all_events if not e.is_resolved])
                if count > 0:
                    tab_text = f"{tab.value} ({count})"
            else:
                count = len([e for e in all_events if e.is_resolved])
                if count > 0:
                    tab_text = f"{tab.value} ({count})"
            
            text_surf = font_tab.render(tab_text, True, text_color)
            tx = x + (80 - text_surf.get_width()) // 2
            ty = tab_y + (self.TAB_HEIGHT - 8 - text_surf.get_height()) // 2
            surf.blit(text_surf, (tx, ty))
    
    def _draw_content(self, surf: pygame.Surface):
        """绘制内容区域"""
        items = self._get_items()
        content_rect = pygame.Rect(
            self.PADDING,
            self.HEADER_HEIGHT + self.TAB_HEIGHT + 10,
            self.PANEL_WIDTH - self.PADDING * 2 - self.SCROLL_WIDTH - 4,
            self.PANEL_HEIGHT - self.HEADER_HEIGHT - self.TAB_HEIGHT - 30
        )
        
        # 空状态
        if not items:
            font = self._get_font(14)
            empty_text = "暂无事件" if self.current_tab == NewsTab.CURRENT else "暂无历史记录"
            text_surf = font.render(empty_text, True, self.COLOR_TEXT_MUTED)
            surf.blit(text_surf, (
                content_rect.x + (content_rect.width - text_surf.get_width()) // 2,
                content_rect.y + 50
            ))
            return
        
        # 计算总高度
        total_height = len(items) * (self.ITEM_HEIGHT + self.ITEM_MARGIN)
        self.max_scroll = max(0, total_height - content_rect.height)
        
        # 创建裁剪区域
        content_surf = pygame.Surface((content_rect.width, content_rect.height), pygame.SRCALPHA)
        
        # 绘制每个事件项
        for i, item in enumerate(items):
            item_y = i * (self.ITEM_HEIGHT + self.ITEM_MARGIN) - self.scroll_offset
            
            # 跳过不可见项
            if item_y < -self.ITEM_HEIGHT or item_y > content_rect.height:
                continue
            
            is_hover = (i == self.hovered_item_index)
            self._draw_item(content_surf, item, 0, item_y, content_rect.width, is_hover)
        
        surf.blit(content_surf, content_rect.topleft)
        
        # 绘制滚动条
        if total_height > content_rect.height:
            self._draw_scrollbar(surf, content_rect, total_height)
    
    def _draw_item(self, surf: pygame.Surface, item: EventNotification, 
                   x: int, y: int, width: int, is_hover: bool):
        """绘制单个事件项 - 复用与通知栏相同的布局"""
        # 使用共享的 draw_event_card 函数，保持UI一致性
        # 复用通知管理器的头像缓存
        mgr = get_notification_manager()
        
        draw_event_card(
            surface=surf,
            notif=item,
            x=x,
            y=y,
            width=width,
            height=self.ITEM_HEIGHT,
            font_cache=self._font_cache,
            avatar_cache=mgr._avatar_cache,  # 复用通知管理器的头像缓存
            is_hover=is_hover,
            is_unread=not item.read,
            show_border=True
        )
        
        # 额外绘制：已解决标记（在右上角）
        if item.is_resolved:
            font_small = self._get_font(10)
            resolved_surf = font_small.render("✓", True, (100, 200, 150))
            surf.blit(resolved_surf, (x + width - 20, y + 6))
    
    def _draw_scrollbar(self, surf: pygame.Surface, content_rect: pygame.Rect, total_height: float):
        """绘制滚动条"""
        track_x = content_rect.x + content_rect.width + 4
        track_y = content_rect.y
        track_h = content_rect.height
        
        # 轨道
        pygame.draw.rect(surf, self.COLOR_SCROLL, 
                         (track_x, track_y, self.SCROLL_WIDTH, track_h), 
                         border_radius=4)
        
        # 滑块
        thumb_ratio = content_rect.height / total_height
        thumb_h = max(30, int(track_h * thumb_ratio))
        scroll_range = total_height - content_rect.height
        thumb_y = track_y + int((self.scroll_offset / scroll_range) * (track_h - thumb_h)) if scroll_range > 0 else track_y
        
        thumb_color = self.COLOR_SCROLL_THUMB if not self.is_scrolling else (150, 145, 180)
        pygame.draw.rect(surf, thumb_color, 
                         (track_x, thumb_y, self.SCROLL_WIDTH, thumb_h), 
                         border_radius=4)
    
    def _draw_actor_avatar(self, surf: pygame.Surface, actor_name: str, x: int, y: int, size: int = 36):
        """绘制角色头像"""
        
        # 头像路径（优先使用优化后的head_icon）
        avatar_path = PyPath(resource_path(f"assets/head_icon/{actor_name}.png"))
        if not avatar_path.exists():
            avatar_path = PyPath(resource_path(f"data/avatars/{actor_name}.png"))
        if not avatar_path.exists():
            avatar_path = PyPath(resource_path(f"avatars/{actor_name}.png"))
        
        # 尝试加载头像
        avatar_surface = None
        if avatar_path.exists():
            try:
                avatar_surface = pygame.image.load(str(avatar_path))
                avatar_surface = pygame.transform.smoothscale(avatar_surface, (size, size))
            except:
                pass
        
        # 绘制圆形裁剪区域
        circle_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.ellipse(circle_surf, (255, 255, 255), (0, 0, size, size))
        
        if avatar_surface:
            # 使用头像
            avatar_surface.blit(circle_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(avatar_surface, (x, y))
        else:
            # 使用默认头像（名字首字）
            pygame.draw.ellipse(surf, (80, 80, 100), (x, y, size, size))
            font = self._get_font(size // 2)
            initial = actor_name[0] if actor_name else "?"
            text_surf = font.render(initial, True, (200, 200, 220))
            text_x = x + (size - text_surf.get_width()) // 2
            text_y = y + (size - text_surf.get_height()) // 2
            surf.blit(text_surf, (text_x, text_y))
        
        # 绘制边框
        pygame.draw.ellipse(surf, (120, 120, 140), (x, y, size, size), 2)
    
    def _ease_out_back(self, t: float) -> float:
        """弹性缓出动画"""
        c1 = 1.70158
        c3 = c1 + 1
        return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)


# ═══════════════════════════════════════════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════════════════════════════════════════

_live_news_panel: Optional[LiveNewsPanel] = None

def get_live_news_panel(screen_w: int = 0, screen_h: int = 0) -> LiveNewsPanel:
    """获取全局大宋实况面板"""
    global _live_news_panel
    if _live_news_panel is None:
        if screen_w == 0 or screen_h == 0:
            try:
                screen_w, screen_h = pygame.display.get_surface().get_size()
            except:
                screen_w, screen_h = 1280, 720
        _live_news_panel = LiveNewsPanel(screen_w, screen_h)
    return _live_news_panel


def toggle_live_news_panel():
    """切换大宋实况面板显示"""
    panel = get_live_news_panel()
    panel.toggle()
