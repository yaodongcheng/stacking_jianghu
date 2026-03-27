# src/ui/event_notification.py
"""
═══════════════════════════════════════════════════════════════════════════════
【大宋实况】统一事件系统
═══════════════════════════════════════════════════════════════════════════════

这是游戏中唯一的事件/新闻通知系统，整合了原LiveNewsItem。

功能：
  1. LiveNewsItem - 统一数据类（包含业务数据+UI状态）
  2. EventNotificationManager - 通知管理+历史记录+效果应用
  3. 右侧通知卡片UI（支持右上角模式 / 事发地模式）
"""

import pygame
import math
import time
from typing import Optional, List, Dict, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum

from src.definitions import (
    SIDEBAR_W, TOPBAR_H,
    EVENT_DISPLAY_MODE, EVENT_ONSITE_CARD_OFFSET_X, EVENT_ONSITE_CARD_OFFSET_Y,
    EVENT_ARROW_SIZE, EVENT_ARROW_MARGIN
)


# ═══════════════════════════════════════════════════════════════════════════════
# 分类枚举
# ═══════════════════════════════════════════════════════════════════════════════

class NewsCategory(Enum):
    """新闻分类"""
    ECONOMIC = "economic"
    SOCIAL = "social"
    MORAL = "moral"
    MARTIAL = "martial"
    SUPERNATURAL = "supernatural"
    POLITICAL = "political"


class DilemmaType(Enum):
    """
    困境类型 - 与 rolling_story_generator.py 保持一致
    必须属于以下七大类之一
    """
    SACRIFICE = "SACRIFICE"         # 自我牺牲（帮别人但自己受损）
    BETRAY = "BETRAY"               # 背叛（为了自己收益最大化，让朋友受损）
    COMPROMISE = "COMPROMISE"       # 妥协（自己和敌人都获得了好处，即使不是最优解）
    DESTRUCTION = "DESTRUCTION"     # 玉石俱焚（为了打击敌人宁愿自己也受损失）
    BIAS = "BIAS"                   # 偏心（两个亲近的人对立，帮一个必然损害另一个）
    MORAL_GREY = "MORAL_GREY"       # 道德灰色（两个选择都不完全道德）
    SHORT_VS_LONG = "SHORT_VS_LONG" # 短期vs长期（眼前利益vs长远正义）


# ═══════════════════════════════════════════════════════════════════════════════
# 统一数据类
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LiveNewsItem:
    """
    统一事件数据类
    
    兼容字段映射：
      - news_id → id
      - is_read → read
      - created_tick → 使用 created_at 替代
    """
    # === 基础标识 ===
    id: str
    title: str
    subtitle: str = ""
    
    # === 业务数据 ===
    headline: str = ""
    description: str = ""
    category: Optional[NewsCategory] = None
    dilemma_type: Optional[DilemmaType] = None
    
    # 涉及的NPC
    actor_ids: List[int] = field(default_factory=list)
    actor_names: List[str] = field(default_factory=list)
    
    # 地点
    location: str = ""
    location_x: float = 0
    location_y: float = 0
    
    # 选项（最多3个）
    choices: List[Dict] = field(default_factory=list)
    
    # 状态
    priority: int = 2
    created_at: float = 0
    expires_at: float = 0
    read: bool = False
    is_resolved: bool = False
    player_choice: Optional[str] = None
    player_choice_idx: int = -1  # 玩家选择的选项索引
    auto_popup: bool = False
    
    # 小红书/抖音风格
    tags: List[str] = field(default_factory=list)
    comments: List[Dict] = field(default_factory=list)
    heat_score: int = 0
    image_prompt: str = ""
    
    # 运行时缓存
    _image_surface: object = field(default=None, repr=False)
    _image_path: str = field(default="", repr=False)
    _pregen_script: object = field(default=None, repr=False)
    
    # === 事件扩写相关字段（来自EventCard，避免重复转换）===
    # 困境描述
    dilemma_desc_summary: str = ""           # 困境总体描述
    dilemma_desc_desire: str = ""            # 内心渴望
    dilemma_desc_misgiving: str = ""         # 内心顾虑
    
    # 演员列表
    actors: List[Dict] = field(default_factory=list)  # [{role, npc_name, npc_id}, ...]
    
    # 自动恶化（无人介入时的自然发展）
    auto_decay_next_phase: str = ""          # 下一阶段预览
    auto_decay_auto_effect: str = ""         # 自动效果
    auto_decay_auto_transfer: str = ""       # 自动资源流转
    auto_decay_auto_tension_delta: int = 0   # 自动张力变化
    
    # 起承转合阶段
    chain_phase: str = ""                    # EMERGE/ESCALATE/CLIMAX/SETTLE
    event_theme: str = ""                    # 事件主题
    emotion_tone: str = ""                   # 情绪基调
    
    # 困境主角ID（明确标识谁是MAINNPC，避免角色定位错误）
    target_npc_id: str = ""                  # 困境主角的NPC ID
    target_npc_name: str = ""                # 困境主角的NPC名字
    
    # 原始JSON（用于对话扩写）
    raw_json: Dict = field(default_factory=dict, repr=False)
    
    # === UI动画状态 ===
    icon: str = "[报]"
    snapshot_data: Any = None
    slide_progress: float = 0.0
    fade_progress: float = 1.0
    
    # === 兼容属性 ===
    @property
    def news_id(self) -> str:
        return self.id
    
    @news_id.setter
    def news_id(self, value: str):
        self.id = value
    
    @property
    def is_read(self) -> bool:
        return self.read
    
    @is_read.setter
    def is_read(self, value: bool):
        self.read = value
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()
        if not self.id:
            self.id = f"event_{int(self.created_at * 1000)}"
        if not self.headline:
            self.headline = self.title
    
    def get_icon_color(self):
        """根据分类返回图标颜色"""
        colors = {
            NewsCategory.ECONOMIC: (255, 215, 0),
            NewsCategory.SOCIAL: (100, 200, 255),
            NewsCategory.MORAL: (200, 100, 255),
            NewsCategory.MARTIAL: (255, 100, 100),
            NewsCategory.SUPERNATURAL: (100, 255, 200),
            NewsCategory.POLITICAL: (255, 180, 100),
        }
        return colors.get(self.category, (200, 200, 200))


# 兼容别名（让旧代码继续工作）
LiveNewsItem = LiveNewsItem


class EventNotificationManager:
    """
    事件通知管理器
    
    管理事件通知卡片队列 + 历史记录
    统一管理"大宋实况"系统的所有事件数据
    
    显示模式：
      - CORNER: 右上角模式 - 事件卡片固定显示在屏幕右上角
      - ON_SITE: 事发地模式 - 事件卡片显示在事件发生位置
                如果事件超出摄像机范围，显示在最靠近的边界并添加方向箭头
    """
    
    # 布局常量
    CARD_WIDTH = 280
    CARD_HEIGHT = 80
    CARD_MARGIN = 10
    CARD_PADDING = 10
    MAX_VISIBLE = 5          # 最多同时显示的通知数
    NOTIFICATION_LIFETIME = 0.0  # 通知存活时间（秒），0表示不自动消失，直到玩家点击
    SLIDE_DURATION = 300     # 滑入动画时长（毫秒）
    MAX_HISTORY = 50         # 最大历史记录数
    
    # 头像配置
    AVATAR_SIZE = 26         # 头像大小（第二行用，稍小）
    AVATAR_MARGIN = 4        # 头像间距
    MAX_DISPLAY_ACTORS = 2   # 最多显示头像数量
    
    # 优先级颜色（用于边框）
    PRIORITY_COLORS = {
        1: (80, 80, 100),     # 低 - 灰
        2: (100, 150, 100),   # 普通 - 绿
        3: (180, 160, 80),    # 重要 - 黄
        4: (200, 120, 60),    # 紧急 - 橙
        5: (200, 60, 60),     # 危机 - 红
    }
    
    # 颜色
    COLOR_BG = (30, 28, 40, 230)
    COLOR_BORDER = (80, 75, 100)
    COLOR_BORDER_URGENT = (200, 100, 80)
    COLOR_BORDER_HOVER = (120, 140, 200)
    COLOR_TITLE = (255, 255, 255)
    COLOR_SUBTITLE = (180, 180, 200)
    COLOR_UNREAD = (100, 180, 255)
    COLOR_ARROW = (255, 200, 100)  # 箭头颜色
    
    def __init__(self, screen_w: int, screen_h: int):
        self.screen_w = screen_w
        self.screen_h = screen_h
        
        # 通知队列（当前活跃的，显示在右侧）
        self.notifications: List[LiveNewsItem] = []
        
        # ═══════════════════════════════════════════════════════════════
        # 【大宋实况·历史记录】所有事件的完整历史（最新在前）
        # 包括已过期、已读、被点击的所有通知
        # ═══════════════════════════════════════════════════════════════
        self.history: List[LiveNewsItem] = []
        
        # 悬停状态
        self.hovered_index = -1
        
        # 字体
        self._font_cache = {}
        
        # 头像缓存
        self._avatar_cache: Dict[str, pygame.Surface] = {}
        
        # 箭头图标缓存
        self._arrow_cache: Dict[str, pygame.Surface] = {}
        
        # 回调
        self.on_notification_click: Optional[Callable[[LiveNewsItem], None]] = None
        
        # 摄像机引用（用于事发地模式计算位置）
        self._camera = None
        
        # 计算位置（在侧边栏左侧，不重叠）
        # 侧边栏位于 screen_w - SIDEBAR_W 到 screen_w
        # 通知卡片位于侧边栏左侧
        self.base_x = screen_w - SIDEBAR_W - self.CARD_WIDTH - 15
        self.base_y = 100
    
    def set_camera(self, camera):
        """设置摄像机引用（事发地模式需要）"""
        self._camera = camera
    
    def _get_display_mode(self) -> str:
        """获取当前显示模式"""
        return EVENT_DISPLAY_MODE
    
    def _get_font(self, size: int) -> pygame.font.Font:
        """获取缓存的字体"""
        if size not in self._font_cache:
            font_names = "microsoftyahei,simhei,pingfangsc,arial"
            self._font_cache[size] = pygame.font.SysFont(font_names, size)
        return self._font_cache[size]
    
    def add_notification(self, title: str, subtitle: str = "", 
                         priority: int = 2, icon: str = "[报]",
                         snapshot_data: Any = None,
                         lifetime: float = None) -> LiveNewsItem:
        """
        添加新通知
        
        Args:
            title: 通知标题
            subtitle: 副标题
            priority: 优先级 (1=低, 2=普通, 3=重要, 4=紧急, 5=危机)
            icon: 显示图标
            snapshot_data: 关联的完整事件数据（点击后展示）
            lifetime: 存活时间（秒），None使用默认值
            
        Returns:
            创建的通知对象
        """
        if lifetime is None:
            lifetime = self.NOTIFICATION_LIFETIME
        
        notif = LiveNewsItem(
            id="",
            title=title,
            subtitle=subtitle,
            priority=priority,
            icon=icon,
            created_at=time.time(),
            expires_at=time.time() + lifetime if lifetime > 0 else 0,
            snapshot_data=snapshot_data,
            slide_progress=0.0
        )
        
        # 插入到通知队列头部（活跃通知）
        self.notifications.insert(0, notif)
        
        # ═══════════════════════════════════════════════════════════════
        # 【大宋实况·历史记录】同时添加到历史记录
        # ═══════════════════════════════════════════════════════════════
        self.history.insert(0, notif)
        # 限制历史记录长度
        while len(self.history) > self.MAX_HISTORY:
            self.history.pop()
        
        # 限制活跃队列长度
        while len(self.notifications) > self.MAX_VISIBLE * 2:
            self.notifications.pop()
        
        print(f"[LiveNewsItem] 添加通知: {title[:20]}... (历史:{len(self.history)}条)")
        return notif
    
    def update(self, dt_ms: int):
        """更新动画状态"""
        current_time = time.time()
        
        # 更新每个通知的状态
        to_remove = []
        for notif in self.notifications:
            # 滑入动画
            if notif.slide_progress < 1.0:
                notif.slide_progress = min(1.0, notif.slide_progress + dt_ms / self.SLIDE_DURATION)
            
            # 检查过期（仅当 NOTIFICATION_LIFETIME > 0 时才自动消失）
            if self.NOTIFICATION_LIFETIME > 0 and notif.expires_at > 0 and current_time > notif.expires_at:
                # 开始淡出
                notif.fade_progress = max(0, notif.fade_progress - dt_ms / 500)
                if notif.fade_progress <= 0:
                    to_remove.append(notif)
        
        # 移除过期的通知
        for notif in to_remove:
            self.notifications.remove(notif)
    
    def handle_event(self, event: pygame.event.Event, camera=None) -> bool:
        """
        处理事件
        
        Args:
            event: pygame事件
            camera: 摄像机对象（事发地模式需要）
        
        Returns:
            bool: 是否消费了事件
        """
        # 如果没有传入摄像机但有缓存的摄像机引用，使用缓存
        if camera is None:
            camera = self._camera
        
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hovered_index = -1
            
            for i, notif in enumerate(self.notifications[:self.MAX_VISIBLE]):
                card_rect, _ = self._get_card_rect(i, notif, camera)
                if card_rect.collidepoint(mx, my):
                    self.hovered_index = i
                    break
            
            return False  # 不消费 motion 事件
        
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            
            for i, notif in enumerate(self.notifications[:self.MAX_VISIBLE]):
                card_rect, direction_arrow = self._get_card_rect(i, notif, camera)
                if card_rect.collidepoint(mx, my):
                    # 事发地模式下，如果事件在视野外，先移动摄像机
                    if self._get_display_mode() == 'ON_SITE' and camera and direction_arrow:
                        # 事件在视野外，移动摄像机到事件位置
                        world_x = notif.location_x
                        world_y = notif.location_y
                        if world_x != 0 or world_y != 0:
                            camera.start_event_focus(world_x, world_y)
                            print(f"[EventNotification] 移动摄像机到事件位置: ({world_x}, {world_y})")
                    
                    # 标记为已读
                    notif.read = True
                    
                    # 触发回调
                    if self.on_notification_click:
                        self.on_notification_click(notif)
                    
                    # 从队列移除
                    self.notifications.remove(notif)
                    return True
        
        return False
    
    def _get_card_rect(self, index: int, notif: LiveNewsItem, 
                       camera=None) -> Tuple[pygame.Rect, Optional[str]]:
        """
        计算通知卡片的位置
        
        Args:
            index: 通知索引
            notif: 通知对象
            camera: 摄像机对象（事发地模式需要）
            
        Returns:
            (card_rect, direction_arrow): 卡片位置矩形, 方向箭头（None表示在视野内无需箭头）
        """
        mode = self._get_display_mode()
        
        # 右上角模式：固定位置
        if mode == 'CORNER' or not camera:
            slide_offset = int((1.0 - self._ease_out_cubic(notif.slide_progress)) * (self.CARD_WIDTH + 30))
            y = self.base_y + index * (self.CARD_HEIGHT + self.CARD_MARGIN)
            x = self.base_x + slide_offset
            return pygame.Rect(x, y, self.CARD_WIDTH, self.CARD_HEIGHT), None
        
        # 事发地模式：根据事件位置计算
        return self._get_onsite_card_rect(notif, camera)
    
    def _get_onsite_card_rect(self, notif: LiveNewsItem, 
                               camera) -> Tuple[pygame.Rect, Optional[str]]:
        """
        计算事发地模式下的卡片位置
        
        Args:
            notif: 通知对象
            camera: 摄像机对象
            
        Returns:
            (card_rect, direction_arrow): 卡片位置矩形, 方向箭头
        """
        # 获取事件世界坐标
        world_x = notif.location_x
        world_y = notif.location_y
        
        # 如果事件没有位置信息，退回到右上角模式
        if world_x == 0 and world_y == 0:
            return pygame.Rect(self.base_x, self.base_y, self.CARD_WIDTH, self.CARD_HEIGHT), None
        
        # 转换为屏幕坐标
        screen_x, screen_y = camera.world_to_screen(world_x, world_y)
        
        # 计算卡片目标位置（事件位置上方偏移）
        card_target_x = screen_x + EVENT_ONSITE_CARD_OFFSET_X
        card_target_y = screen_y + EVENT_ONSITE_CARD_OFFSET_Y - self.CARD_HEIGHT
        
        # 计算视口边界（排除侧边栏和顶部栏）
        view_left = EVENT_ARROW_MARGIN
        view_right = self.screen_w - SIDEBAR_W - self.CARD_WIDTH - EVENT_ARROW_MARGIN
        view_top = TOPBAR_H + EVENT_ARROW_MARGIN
        view_bottom = self.screen_h - self.CARD_HEIGHT - EVENT_ARROW_MARGIN
        
        # 判断事件是否在视野内
        event_in_view = (
            view_left <= screen_x <= self.screen_w - SIDEBAR_W - EVENT_ARROW_MARGIN and
            view_top <= screen_y <= self.screen_h - EVENT_ARROW_MARGIN
        )
        
        direction_arrow = None
        
        if event_in_view:
            # 事件在视野内：卡片显示在事件位置
            # 确保卡片不超出边界
            card_x = max(view_left, min(view_right, card_target_x))
            card_y = max(view_top, min(view_bottom, card_target_y))
        else:
            # 事件在视野外：计算最近边界位置和方向箭头
            card_x, card_y, direction_arrow = self._calc_boundary_position(
                screen_x, screen_y, view_left, view_right, view_top, view_bottom
            )
        
        # 滑入动画
        slide_progress = self._ease_out_cubic(notif.slide_progress)
        if slide_progress < 1.0:
            # 从右侧滑入
            slide_offset = int((1.0 - slide_progress) * (self.CARD_WIDTH + 30))
            card_x += slide_offset
        
        return pygame.Rect(card_x, card_y, self.CARD_WIDTH, self.CARD_HEIGHT), direction_arrow
    
    def _calc_boundary_position(self, event_sx: float, event_sy: float,
                                 view_left: float, view_right: float,
                                 view_top: float, view_bottom: float) -> Tuple[int, int, str]:
        """
        计算事件在视野外时的边界位置和方向箭头
        
        Args:
            event_sx, event_sy: 事件的屏幕坐标
            view_left, view_right, view_top, view_bottom: 视口边界
            
        Returns:
            (card_x, card_y, arrow_direction): 卡片位置和箭头方向
        """
        # 计算事件相对于视口中心的方位
        center_x = (view_left + view_right + self.CARD_WIDTH) / 2
        center_y = (view_top + view_bottom + self.CARD_HEIGHT) / 2
        
        dx = event_sx - center_x
        dy = event_sy - center_y
        angle = math.atan2(dy, dx)
        
        # 定义8个方向
        # 角度范围：-π 到 π
        # 右=0, 上=π/2, 左=π, 下=-π/2
        directions = [
            ('↗', math.pi * 3 / 8, math.pi * 5 / 8),      # 右上
            ('↑', math.pi * 5 / 8, math.pi * 7 / 8),      # 上
            ('↖', math.pi * 7 / 8, math.pi),              # 左上 (正范围)
            ('↖', -math.pi, -math.pi * 7 / 8),            # 左上 (负范围)
            ('←', -math.pi * 7 / 8, -math.pi * 5 / 8),    # 左
            ('↙', -math.pi * 5 / 8, -math.pi * 3 / 8),    # 左下
            ('↓', -math.pi * 3 / 8, -math.pi * 1 / 8),    # 下
            ('↘', -math.pi * 1 / 8, math.pi * 1 / 8),     # 右下
            ('→', math.pi * 1 / 8, math.pi * 3 / 8),      # 右
        ]
        
        arrow = '→'  # 默认箭头
        for direction, min_angle, max_angle in directions:
            if min_angle <= angle < max_angle:
                arrow = direction
                break
        
        # 特殊处理：左上方向的角度跨越边界
        if angle >= math.pi * 7 / 8 or angle <= -math.pi * 7 / 8:
            arrow = '↖'
        
        # 计算卡片位置：边界上最近的点
        # 优先考虑主要方向（上下左右）
        card_x = max(view_left, min(view_right, event_sx))
        card_y = max(view_top, min(view_bottom, event_sy - self.CARD_HEIGHT))
        
        # 如果事件在左侧或右侧外，卡片贴到边界
        if event_sx < view_left:
            card_x = view_left
            # 根据y位置调整箭头
            if event_sy < view_top:
                arrow = '↖'
                card_y = view_top
            elif event_sy > view_bottom + self.CARD_HEIGHT:
                arrow = '↙'
                card_y = view_bottom
        elif event_sx > view_right + self.CARD_WIDTH:
            card_x = view_right
            if event_sy < view_top:
                arrow = '↗'
                card_y = view_top
            elif event_sy > view_bottom + self.CARD_HEIGHT:
                arrow = '↘'
                card_y = view_bottom
        
        # 如果事件在上方或下方外，卡片贴到边界
        if event_sy < view_top:
            card_y = view_top
            if view_left <= event_sx <= view_right:
                arrow = '↑'
        elif event_sy > view_bottom + self.CARD_HEIGHT:
            card_y = view_bottom
            if view_left <= event_sx <= view_right:
                arrow = '↓'
        
        return int(card_x), int(card_y), arrow
    
    def draw(self, screen: pygame.Surface, camera=None):
        """
        绘制所有通知
        
        Args:
            screen: 目标surface
            camera: 摄像机对象（事发地模式需要）
        """
        # 调试：打印当前通知数量
        if self.notifications:
            # 每5秒打印一次，避免刷屏
            if not hasattr(self, '_last_debug_time') or time.time() - self._last_debug_time > 5:
                self._last_debug_time = time.time()
                print(f"[LiveNewsItem] 当前通知数量: {len(self.notifications)}")
        
        # 如果没有传入摄像机但有缓存的摄像机引用，使用缓存
        if camera is None:
            camera = self._camera
        
        for i, notif in enumerate(self.notifications[:self.MAX_VISIBLE]):
            self._draw_notification(screen, i, notif, camera)
    
    def _load_avatar(self, name: str) -> Optional[pygame.Surface]:
        """加载头像图片，从assets/head_icon目录"""
        if name in self._avatar_cache:
            return self._avatar_cache[name]
        
        # 尝试加载头像（唯一路径）
        avatar_paths = [
            f"assets/head_icon/{name}.png",
        ]
        
        for path in avatar_paths:
            try:
                img = pygame.image.load(path).convert_alpha()
                # 缩放到指定大小
                img = pygame.transform.scale(img, (self.AVATAR_SIZE, self.AVATAR_SIZE))
                self._avatar_cache[name] = img
                return img
            except:
                continue
        
        return None
    
    def _draw_rounded_avatar(self, surface: pygame.Surface, img: pygame.Surface, 
                              x: int, y: int, size: int):
        """绘制圆形头像"""
        # 创建圆形遮罩
        mask = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.ellipse(mask, (255, 255, 255), (0, 0, size, size))
        
        # 缩放图片
        scaled_img = pygame.transform.scale(img, (size, size))
        
        # 应用遮罩
        avatar = pygame.Surface((size, size), pygame.SRCALPHA)
        avatar.blit(scaled_img, (0, 0))
        avatar.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        
        surface.blit(avatar, (x, y))
        
        # 绘制边框
        pygame.draw.ellipse(surface, (100, 100, 120), (x, y, size, size), 1)
    
    def _draw_default_avatar(self, surface: pygame.Surface, x: int, y: int, size: int):
        """绘制默认头像（当没有头像图片时）"""
        # 背景圆
        pygame.draw.ellipse(surface, (80, 80, 100), (x, y, size, size))
        # 简化的"人"形图标
        center_x = x + size // 2
        head_y = y + size // 3
        body_y = y + size * 2 // 3
        # 头
        pygame.draw.circle(surface, (150, 150, 170), (center_x, head_y), size // 6)
        # 身体弧线
        pygame.draw.arc(surface, (150, 150, 170), 
                       (x + size//4, body_y - size//8, size//2, size//2),
                       3.14, 0, 2)
    
    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int) -> List[str]:
        """将文本按最大宽度换行"""
        lines = []
        words = []
        current_width = 0
        
        for char in text:
            char_width = font.size(char)[0]
            if current_width + char_width > max_width and words:
                lines.append(''.join(words))
                words = [char]
                current_width = char_width
            else:
                words.append(char)
                current_width += char_width
        
        if words:
            lines.append(''.join(words))
        
        return lines
    
    def _draw_notification(self, screen: pygame.Surface, index: int, notif: LiveNewsItem,
                           camera=None):
        """
        绘制单个通知卡片
        
        Args:
            screen: 目标surface
            index: 通知索引
            notif: 通知对象
            camera: 摄像机对象（事发地模式需要）
        """
        card_rect, direction_arrow = self._get_card_rect(index, notif, camera)
        is_hover = (index == self.hovered_index)
        
        # 使用共享的绘制函数
        draw_event_card(
            surface=screen,
            notif=notif,
            x=card_rect.x,
            y=card_rect.y,
            width=self.CARD_WIDTH,
            height=self.CARD_HEIGHT,
            font_cache=self._font_cache,
            avatar_cache=self._avatar_cache,
            is_hover=is_hover,
            is_unread=not notif.read,
            show_border=True
        )
        
        # 如果有方向箭头，绘制箭头
        if direction_arrow:
            self._draw_direction_arrow(screen, card_rect, direction_arrow, notif)
    
    def _draw_direction_arrow(self, screen: pygame.Surface, card_rect: pygame.Rect,
                               arrow: str, notif: LiveNewsItem):
        """
        绘制方向箭头
        
        Args:
            screen: 目标surface
            card_rect: 卡片矩形
            arrow: 箭头字符（↑↓←→↗↘↙↖）
            notif: 通知对象（用于判断闪烁效果）
        """
        # 箭头位置：卡片角落
        arrow_positions = {
            '↑': (card_rect.centerx, card_rect.bottom + 5),
            '↓': (card_rect.centerx, card_rect.top - 5),
            '←': (card_rect.right + 5, card_rect.centery),
            '→': (card_rect.left - 5, card_rect.centery),
            '↗': (card_rect.left - 5, card_rect.bottom + 5),
            '↘': (card_rect.left - 5, card_rect.top - 5),
            '↙': (card_rect.right + 5, card_rect.top - 5),
            '↖': (card_rect.right + 5, card_rect.bottom + 5),
        }
        
        pos_x, pos_y = arrow_positions.get(arrow, (card_rect.right, card_rect.centery))
        
        # 绘制箭头背景圆
        bg_radius = EVENT_ARROW_SIZE
        # 闪烁效果
        flash = (int(time.time() * 3) % 2 == 0)
        bg_color = (255, 220, 100, 200) if flash else (200, 160, 60, 200)
        
        # 创建带透明度的圆
        arrow_surf = pygame.Surface((bg_radius * 2 + 4, bg_radius * 2 + 4), pygame.SRCALPHA)
        center = (bg_radius + 2, bg_radius + 2)
        pygame.draw.circle(arrow_surf, bg_color, center, bg_radius)
        pygame.draw.circle(arrow_surf, (255, 255, 255), center, bg_radius, 2)
        
        # 绘制箭头文字
        font = self._get_font(EVENT_ARROW_SIZE)
        arrow_text = font.render(arrow, True, (50, 30, 10))
        text_rect = arrow_text.get_rect(center=center)
        arrow_surf.blit(arrow_text, text_rect)
        
        # 绘制到屏幕
        screen.blit(arrow_surf, (pos_x - bg_radius - 2, pos_y - bg_radius - 2))
    
    def _ease_out_cubic(self, t: float) -> float:
        """缓出动画曲线"""
        return 1 - pow(1 - t, 3)
    
    def get_unread_count(self) -> int:
        """获取未读通知数"""
        return sum(1 for n in self.notifications if not n.read)
    
    def clear_all(self):
        """清空所有通知（不清历史）"""
        self.notifications.clear()
    
    # ═══════════════════════════════════════════════════════════════════════
    # 【大宋实况·历史记录】API
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_history(self, limit: int = 0) -> List[LiveNewsItem]:
        """
        获取历史记录
        
        Args:
            limit: 返回数量限制，0表示全部
            
        Returns:
            历史记录列表（最新在前）
        """
        if limit <= 0:
            return list(self.history)
        return list(self.history[:limit])
    
    def get_history_count(self) -> int:
        """获取历史记录总数"""
        return len(self.history)
    
    def get_history_by_priority(self, min_priority: int = 1) -> List[LiveNewsItem]:
        """
        按优先级筛选历史记录
        
        Args:
            min_priority: 最低优先级 (1-5)
            
        Returns:
            符合条件的历史记录
        """
        return [n for n in self.history if n.priority >= min_priority]
    
    def find_in_history(self, title_keyword: str) -> List[LiveNewsItem]:
        """
        在历史中搜索标题包含关键词的事件
        
        Args:
            title_keyword: 搜索关键词
            
        Returns:
            匹配的历史记录
        """
        keyword = title_keyword.lower()
        return [n for n in self.history if keyword in n.title.lower()]
    
    def clear_history(self):
        """清空历史记录"""
        self.history.clear()
        print("[LiveNewsItem] 历史记录已清空")
    
    # ═══════════════════════════════════════════════════════════════════════
    # 【业务逻辑】效果应用（原LiveNewsManager）
    # ═══════════════════════════════════════════════════════════════════════
    
    def add_event(self, event: LiveNewsItem) -> bool:
        """
        添加事件到队列（带去重检查）
        
        Args:
            event: LiveNewsItem 完整事件对象
            
        Returns:
            是否成功添加
        """
        # 去重检查
        for existing in self.notifications:
            if existing.id == event.id:
                print(f"[LiveNewsItem] 拒绝重复事件: {event.id}")
                return False
        for existing in self.history:
            if existing.id == event.id:
                print(f"[LiveNewsItem] 拒绝重复事件（历史中已存在）: {event.id}")
                return False
        
        # 设置UI动画状态
        event.slide_progress = 0.0
        event.fade_progress = 1.0
        # 仅当 NOTIFICATION_LIFETIME > 0 时才设置过期时间
        if self.NOTIFICATION_LIFETIME > 0 and not event.expires_at:
            event.expires_at = time.time() + self.NOTIFICATION_LIFETIME
        
        # 按时间倒序插入（最新的在前）
        inserted = False
        for i, existing in enumerate(self.notifications):
            if event.created_at > existing.created_at:
                self.notifications.insert(i, event)
                inserted = True
                break
        if not inserted:
            self.notifications.append(event)
        
        # 同时加入历史（也按时间排序）
        inserted_history = False
        for i, existing in enumerate(self.history):
            if event.created_at > existing.created_at:
                self.history.insert(i, event)
                inserted_history = True
                break
        if not inserted_history:
            self.history.append(event)
        while len(self.history) > self.MAX_HISTORY:
            self.history.pop()
        
        # 限制活跃队列
        while len(self.notifications) > self.MAX_VISIBLE * 2:
            old = self.notifications.pop()
        
        print(f"[LiveNewsItem] 添加事件: {event.title} (ID: {event.id})")
        return True
    
    def resolve_event(self, event_id: str, choice_idx: int, ctx=None) -> Optional[Dict]:
        """
        解决事件（玩家做出选择）
        
        Args:
            event_id: 事件ID
            choice_idx: 选择索引
            ctx: 游戏上下文
            
        Returns:
            效果执行结果
        """
        event = None
        for e in self.notifications:
            if e.id == event_id:
                event = e
                break
        
        if not event or event.is_resolved:
            return None
        
        if choice_idx < 0 or choice_idx >= len(event.choices):
            return None
        
        choice = event.choices[choice_idx]
        event.player_choice = choice.get("text", "")
        event.player_choice_idx = choice_idx  # 保存选择索引
        event.is_resolved = True
        event.read = True
        
        # 从活跃队列移除
        if event in self.notifications:
            self.notifications.remove(event)
        
        # 执行效果
        effect_str = choice.get("effect", "")
        result = self._apply_effects(effect_str, event, ctx)
        
        return result
    
    def apply_choice(self, event: LiveNewsItem, choice_idx: int, ctx=None) -> Optional[Dict]:
        """
        直接应用选择到事件（供快照面板使用）
        
        【起承转合四幕追踪】
        - 记录玩家选择到 StoryBeat
        - 更新 StoryDirector 中的 FateNode 和 NPCDilemmaSeed
        - 推进困境阶段（EMERGE -> ESCALATE -> CLIMAX -> SETTLE）
        
        Args:
            event: LiveNewsItem对象
            choice_idx: 选择索引
            ctx: 游戏上下文
            
        Returns:
            效果执行结果
        """
        if not event or event.is_resolved:
            return None
        
        if choice_idx < 0 or choice_idx >= len(event.choices):
            return None
        
        choice = event.choices[choice_idx]
        event.player_choice = choice.get("text", "")
        event.player_choice_idx = choice_idx  # 保存选择索引
        event.is_resolved = True
        
        # 如果在队列中，移除
        if event in self.notifications:
            self.notifications.remove(event)
        
        # ═══════════════════════════════════════════════════════════════
        # 【起承转合四幕追踪】更新 StoryDirector 的故事进度
        # ═══════════════════════════════════════════════════════════════
        self._update_story_director_progress(event, choice, choice_idx, ctx)
        
        # 执行效果
        effect_str = choice.get("effect", "")
        result = self._apply_effects(effect_str, event, ctx)
        
        # 显示效果浮动文字
        if result and result.get('changes') and ctx and hasattr(ctx, 'ft_manager') and ctx.player:
            for change in result['changes']:
                ctx.ft_manager.add_text(
                    change,
                    ctx.player.rect.centerx,
                    ctx.player.rect.top - 60,
                    (255, 230, 150)
                )
        
        return result
    
    def _update_story_director_progress(self, event: LiveNewsItem, choice: Dict, choice_idx: int, ctx=None):
        """
        更新 StoryDirector 的故事进度，实现起承转合四幕追踪
        
        流程：
        1. 查找关联的NPC和FateNode
        2. 创建 StoryBeat 记录玩家选择
        3. 更新 NPCDilemmaSeed 的阶段和故事节拍
        4. 推进困境阶段（EMERGE -> ESCALATE -> CLIMAX -> SETTLE）
        """
        try:
            from src.aistory.story_director import StoryDirector
            from src.aistory.dilemma_seed import StoryBeat, DilemmaPhase
            from datetime import datetime
            
            # 获取 StoryDirector 实例
            director = StoryDirector.get_instance()
            if not director:
                print("[StoryProgress] StoryDirector 未初始化，跳过故事进度更新")
                return
            
            # 从 event 中获取关联的NPC（第一个演员）
            if not event.actor_ids:
                print("[StoryProgress] 事件没有关联的NPC，跳过故事进度更新")
                return
            
            # 获取NPC ID（event.actor_ids 是 List[int]）
            npc_id = event.actor_ids[0]
            npc_name = event.actor_names[0] if event.actor_names else f"NPC-{npc_id}"
            
            # 检查NPC是否已注册（story_director 实际使用整数ID作为key）
            if npc_id not in director.npc_data:
                print(f"[StoryProgress] NPC {npc_name}({npc_id}) 未注册到 StoryDirector")
                print(f"  npc_id 类型: {type(npc_id)}, 值: {repr(npc_id)}")
                keys = list(director.npc_data.keys())
                print(f"  npc_data keys: {keys}")
                if keys:
                    print(f"  第一个key类型: {type(keys[0])}, 值: {repr(keys[0])}")
                
                # 如果仍然未注册，跳过
                if npc_id not in director.npc_data:
                    return
            
            # 确保 seed 存在（使用整数ID作为key，与story_director保持一致）
            if npc_id not in director.seeds:
                from src.aistory.dilemma_seed import NPCDilemmaSeed
                director.seeds[npc_id] = NPCDilemmaSeed(id=npc_id)
                print(f"[StoryProgress] 已为 {npc_name} 创建新的困境种子")
            
            seed = director.seeds[npc_id]
            
            # 获取或创建 FateNode（使用整数ID作为key，与story_director保持一致）
            if npc_id not in director.npc_fates:
                director.npc_fates[npc_id] = []
            
            nodes = director.npc_fates[npc_id]
            
            # 查找当前活跃的 FateNode（最后一个未完成的）
            target_node = None
            for node in reversed(nodes):
                if node.seed.phase != DilemmaPhase.SETTLE:
                    target_node = node
                    break
            
            # 如果没有找到，创建新的 FateNode
            if target_node is None:
                import time
                node_id = f"{npc_id}_{int(time.time())}"
                from src.aistory.story_director import FateNode
                target_node = FateNode(
                    node_id=node_id,
                    npc_id=npc_id,
                    seed=seed
                )
                director.npc_fates[npc_id].append(target_node)
                print(f"[StoryProgress] 创建新的 FateNode: {node_id}")
            
            # 推断当前阶段（基于已有节拍数）
            beat_count = len(seed.story_beats)
            phase_map = {
                0: DilemmaPhase.EMERGE,
                1: DilemmaPhase.ESCALATE,
                2: DilemmaPhase.CLIMAX,
                3: DilemmaPhase.SETTLE
            }
            # 【方案2】current_phase 用于记录当前完成的阶段，不用于推进 seed.phase
            current_phase = phase_map.get(beat_count, DilemmaPhase.SETTLE)
            
            # 【方案2】不立即推进 seed.phase，保持为当前已完成阶段
            # 阶段推进将在新事件生成时由 story_director.py 处理
            if seed.phase != current_phase:
                print(f"[StoryProgress] {npc_name} 完成阶段: {current_phase.value} (seed.phase 保持为 {seed.phase.value})")
            # 注意：不修改 seed.phase，让它保持为当前已完成的阶段
            
            # 创建 StoryBeat 记录玩家选择
            beat = StoryBeat(
                beat_number=beat_count + 1,
                timestamp=datetime.now().isoformat(),
                event_summary=event.title,
                player_choice=choice.get("text", ""),
                consequence_summary=choice.get("consequence_preview", "")[:100],
                tension_delta=float(choice.get("tension_delta", 0)),
                phase=current_phase,
                # 记录困境信息（如果事件中有）
                dilemma_type=event.dilemma_type.value if event.dilemma_type else "",
                event_theme=getattr(event, 'event_theme', ''),
                desire=getattr(seed, 'desire', ''),
                misgiving=getattr(seed, 'misgiving', '')
            )
            
            # 添加到 seed 的故事节拍列表
            seed.story_beats.append(beat)
            seed.last_updated = datetime.now().isoformat()
            
            # 更新 FateNode 的玩家选择
            target_node.player_choice = choice.get("text", "")
            
            # 【方案2】不立即推进阶段，保持 seed.phase 为当前已完成阶段
            # 阶段推进将在新事件生成时由 story_director.py 处理
            phase_names = {
                DilemmaPhase.EMERGE: "起",
                DilemmaPhase.ESCALATE: "承",
                DilemmaPhase.CLIMAX: "转",
                DilemmaPhase.SETTLE: "合"
            }
            if beat_count < 3:
                next_phase_name = phase_names.get(phase_map.get(beat_count + 1, DilemmaPhase.SETTLE), '?')
                print(f"[StoryProgress] ✅ {npc_name} 的第 {beat.beat_number} 幕完成 ({phase_names.get(current_phase, '?')})")
                print(f"[StoryProgress]    事件: {event.title[:40]}...")
                print(f"[StoryProgress]    选择: {beat.player_choice[:40]}...")
                print(f"[StoryProgress]    等待生成下一阶段事件: {next_phase_name}")
            else:
                # 已完成四幕
                print(f"[StoryProgress] ✅ {npc_name} 已完成起承转合四幕！")
                print(f"[StoryProgress]    当前困境已尘埃落定，下次将开启新的命运线")
            
            # 显示浮动文字提示
            if ctx and hasattr(ctx, 'ft_manager') and ctx.player:
                phase_display = {
                    DilemmaPhase.EMERGE: "起",
                    DilemmaPhase.ESCALATE: "承", 
                    DilemmaPhase.CLIMAX: "转",
                    DilemmaPhase.SETTLE: "合"
                }
                current_phase_name = phase_display.get(current_phase, "?")
                ctx.ft_manager.add_text(
                    f"[{npc_name}] 命运{current_phase_name}幕完成",
                    ctx.player.rect.centerx,
                    ctx.player.rect.top - 80,
                    (255, 200, 100)
                )
            
        except Exception as e:
            print(f"[StoryProgress] 更新故事进度时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _apply_effects(self, effect_str: str, event: LiveNewsItem, ctx=None) -> Dict:
        """
        应用选择效果
        
        effect格式：角色:属性:增减值，多个用分号隔开
        例如：A:affinity:+20;B:affinity:-30;PLAYER:fame:+10
        """
        if not effect_str or not ctx:
            return {"success": True, "changes": []}
        
        try:
            from src.social_system import social_manager
        except ImportError:
            social_manager = None
        
        changes = []
        commands = effect_str.split(';')
        
        print(f"[LiveNewsItem] 应用效果: {effect_str}")
        
        for cmd in commands:
            cmd = cmd.strip()
            if not cmd:
                continue
            parts = cmd.split(':')
            if len(parts) < 3:
                print(f"[LiveNewsItem] 跳过无效效果: {cmd}")
                continue
            
            target, attr, val_str = parts[0].strip(), parts[1].strip(), parts[2].strip()
            
            try:
                val = int(val_str)
            except ValueError:
                print(f"[LiveNewsItem] 无效数值: {val_str}")
                continue
            
            if target == 'PLAYER' and ctx.player:
                if attr == 'money':
                    old_val = ctx.player.money
                    ctx.player.money = max(0, ctx.player.money + val)
                    changes.append(f"金钱{'+' if val >= 0 else ''}{val}")
                    print(f"[LiveNewsItem] 玩家金钱: {old_val} -> {ctx.player.money}")
                elif attr == 'fame':
                    old_val = getattr(ctx.player, 'fame', 0)
                    ctx.player.fame = getattr(ctx.player, 'fame', 0) + val
                    changes.append(f"声望{'+' if val >= 0 else ''}{val}")
                    print(f"[LiveNewsItem] 玩家声望: {old_val} -> {ctx.player.fame}")
                elif attr == 'infamy':
                    old_val = getattr(ctx.player, 'infamy', 0)
                    ctx.player.infamy = getattr(ctx.player, 'infamy', 0) + val
                    changes.append(f"恶名{'+' if val >= 0 else ''}{val}")
                    print(f"[LiveNewsItem] 玩家恶名: {old_val} -> {ctx.player.infamy}")
            
            elif target in ['A', 'B', 'C', 'D', 'E']:
                idx = ord(target) - ord('A')
                if idx < len(event.actor_ids):
                    npc_id = event.actor_ids[idx]
                    try:
                        npc_id = int(npc_id)
                    except (ValueError, TypeError):
                        pass
                    
                    npc = self._find_npc(npc_id, ctx)
                    npc_name = event.actor_names[idx] if idx < len(event.actor_names) else f"NPC-{npc_id}"
                    
                    if attr == 'affinity' and ctx.player and social_manager:
                        # 确保ID类型一致（都转为字符串）
                        player_id = str(ctx.player.id)
                        target_npc_id = str(npc_id)
                        old_affinity = social_manager.get_affinity(player_id, target_npc_id)
                        social_manager.modify_affinity(player_id, target_npc_id, val)
                        new_affinity = social_manager.get_affinity(player_id, target_npc_id)
                        changes.append(f"{npc_name}好感{'+' if val >= 0 else ''}{val}")
                        print(f"[LiveNewsItem] {npc_name}对玩家好感: {old_affinity} -> {new_affinity}")
                    elif attr == 'hatred' and npc:
                        old_hatred = npc.hatred.get(ctx.player.id, 0) if hasattr(npc, 'hatred') else 0
                        if not hasattr(npc, 'hatred'):
                            npc.hatred = {}
                        npc.hatred[ctx.player.id] = old_hatred + val
                        changes.append(f"{npc_name}仇恨{'+' if val >= 0 else ''}{val}")
                        print(f"[LiveNewsItem] {npc_name}对玩家仇恨: {old_hatred} -> {npc.hatred[ctx.player.id]}")
                    elif attr == 'money' and npc:
                        old_money = getattr(npc, 'money', 0)
                        npc.money = max(0, getattr(npc, 'money', 0) + val)
                        changes.append(f"{npc_name}金钱{'+' if val >= 0 else ''}{val}")
                        print(f"[LiveNewsItem] {npc_name}金钱: {old_money} -> {npc.money}")
                else:
                    print(f"[LiveNewsItem] 角色{target}不存在，actor_ids只有{len(event.actor_ids)}个")
        
        if changes:
            print(f"[LiveNewsItem] 效果应用完成: {', '.join(changes)}")
        else:
            print(f"[LiveNewsItem] 无有效效果被应用")
        
        return {"success": True, "changes": changes}
    
    def _find_npc(self, npc_id: int, ctx):
        """查找NPC"""
        if not ctx or not hasattr(ctx, 'all_cards'):
            return None
        for card in ctx.all_cards:
            if hasattr(card, 'id') and card.id == npc_id:
                return card
        return None
    
    def mark_read(self, event_id: str):
        """标记事件为已读"""
        for event in self.notifications:
            if event.id == event_id:
                event.read = True
                break
    
    def get_display_events(self) -> List[LiveNewsItem]:
        """获取用于显示的事件列表"""
        return self.notifications[:self.MAX_VISIBLE]
    
    # ═══════════════════════════════════════════════════════════════════════
    # 兼容API（原LiveNewsManager）
    # ═══════════════════════════════════════════════════════════════════════
    
    @property
    def news_queue(self) -> List[LiveNewsItem]:
        """兼容：返回活跃通知队列"""
        return self.notifications
    
    @property
    def news_history(self) -> List[LiveNewsItem]:
        """兼容：返回历史记录"""
        return self.history
    
    def add_news(self, news: LiveNewsItem):
        """兼容：添加新闻（等同于add_event）"""
        return self.add_event(news)
    
    def get_display_news(self) -> List[LiveNewsItem]:
        """兼容：获取显示用新闻列表"""
        return self.get_display_events()


# ═══════════════════════════════════════════════════════════════════════════════
# 共享绘制工具函数（供 EventNotificationManager 和 LiveNewsPanel 使用）
# ═══════════════════════════════════════════════════════════════════════════════

def draw_event_card(
    surface: pygame.Surface,
    notif: LiveNewsItem,
    x: int,
    y: int,
    width: int,
    height: int,
    font_cache: Dict[int, pygame.font.Font],
    avatar_cache: Dict[str, pygame.Surface],
    is_hover: bool = False,
    is_unread: bool = False,
    show_border: bool = True
) -> None:
    """
    绘制统一风格的事件卡片
    
    布局：
      - 第一行：标题（单行，省略）
      - 第二行：头像（最多2个）+ 当事人名字
    
    Args:
        surface: 目标绘制surface
        notif: 事件通知对象
        x, y: 位置
        width, height: 尺寸
        font_cache: 字体缓存字典
        avatar_cache: 头像缓存字典
        is_hover: 是否悬停
        is_unread: 是否未读（显示指示器）
        show_border: 是否显示边框
    """
    # 常量
    PADDING = 10
    AVATAR_SIZE = 26
    MAX_ACTORS = 2
    
    # 颜色
    COLOR_BG = (30, 28, 40, 230)
    COLOR_TITLE = (255, 255, 255)
    COLOR_NAMES = (180, 180, 200)
    COLOR_UNREAD = (100, 180, 255)
    PRIORITY_COLORS = {
        1: (80, 80, 100),
        2: (100, 150, 100),
        3: (180, 160, 80),
        4: (200, 120, 60),
        5: (200, 60, 60),
    }
    
    def get_font(size: int) -> pygame.font.Font:
        if size not in font_cache:
            font_cache[size] = pygame.font.SysFont("microsoftyahei,simhei,pingfangsc,arial", size)
        return font_cache[size]
    
    # 创建卡片surface
    card_surf = pygame.Surface((width, height), pygame.SRCALPHA)
    
    # 背景
    bg_color = COLOR_BG
    pygame.draw.rect(card_surf, bg_color, (0, 0, width, height), border_radius=8)
    
    # 边框
    if show_border:
        priority_color = PRIORITY_COLORS.get(notif.priority, (80, 75, 100))
        if is_hover:
            border_color = tuple(min(255, c + 40) for c in priority_color)
        else:
            border_color = priority_color
        pygame.draw.rect(card_surf, border_color, (0, 0, width, height), 2, border_radius=8)
    
    # 未读指示器
    if is_unread:
        pygame.draw.circle(card_surf, COLOR_UNREAD, (width - 12, 12), 4)
    
    # 计算时间差显示
    def format_time_ago(timestamp: float) -> str:
        """格式化时间为'xx分钟前'等形式"""
        if not timestamp:
            return ""
        delta = time.time() - timestamp
        if delta < 60:
            return "刚刚"
        elif delta < 3600:
            return f"{int(delta // 60)}分钟前"
        elif delta < 86400:
            return f"{int(delta // 3600)}小时前"
        else:
            return f"{int(delta // 86400)}天前"
    
    time_text = format_time_ago(notif.created_at)
    font_time = get_font(10)
    time_surf = font_time.render(time_text, True, (150, 150, 170))
    time_width = time_surf.get_width()
    
    # 第一行：标题（留出时间显示空间）
    title_x = PADDING
    title_max_width = width - PADDING * 3 - 20 - time_width
    font_title = get_font(13)
    title_text = notif.title
    while font_title.size(title_text + "…")[0] > title_max_width and len(title_text) > 1:
        title_text = title_text[:-1]
    if title_text != notif.title:
        title_text += "…"
    title_surf = font_title.render(title_text, True, COLOR_TITLE)
    card_surf.blit(title_surf, (title_x, PADDING + 2))
    
    # 绘制时间（右上角）
    if time_text:
        card_surf.blit(time_surf, (width - time_width - PADDING, PADDING + 4))
    
    # 第二行：头像 + 名字
    row2_y = PADDING + 24
    actor_names = notif.actor_names if notif.actor_names else []
    if not actor_names and notif.actor_ids:
        actor_names = [f"NPC-{aid}" for aid in notif.actor_ids[:MAX_ACTORS]]
    
    # 绘制头像
    displayed = actor_names[:MAX_ACTORS]
    avatar_x = PADDING
    for i, name in enumerate(displayed):
        ax = avatar_x + i * (AVATAR_SIZE + 4)
        draw_avatar_inline(card_surf, name, ax, row2_y, AVATAR_SIZE, avatar_cache)
    
    # 名字区域
    if displayed:
        names_x = avatar_x + len(displayed) * (AVATAR_SIZE + 4) + 6
    else:
        names_x = PADDING
    
    if actor_names:
        if len(actor_names) <= 2:
            names_text = "、".join(actor_names)
        else:
            names_text = f"{'、'.join(actor_names[:2])}等{len(actor_names)}人"
    else:
        names_text = "系统事件"
    
    font_names = get_font(11)
    names_max_width = width - names_x - PADDING - 8
    while font_names.size(names_text + "…")[0] > names_max_width and len(names_text) > 2:
        names_text = names_text[:-1]
    if len(names_text) < len("、".join(actor_names[:2]) if actor_names else "系统事件"):
        names_text += "…"
    
    names_surf = font_names.render(names_text, True, COLOR_NAMES)
    names_y = row2_y + (AVATAR_SIZE - names_surf.get_height()) // 2
    card_surf.blit(names_surf, (names_x, names_y))
    
    # 绘制到目标surface
    surface.blit(card_surf, (x, y))


def draw_avatar_inline(
    surface: pygame.Surface,
    name: str,
    x: int,
    y: int,
    size: int,
    avatar_cache: Dict[str, pygame.Surface]
) -> None:
    """在指定位置绘制头像（带缓存）"""
    # 尝试从缓存获取
    img = avatar_cache.get(name)
    
    if img is None:
        # 尝试加载（唯一路径）
        paths = [
            f"assets/head_icon/{name}.png",
        ]
        for path in paths:
            try:
                loaded = pygame.image.load(path).convert_alpha()
                img = pygame.transform.scale(loaded, (size, size))
                avatar_cache[name] = img
                break
            except:
                continue
    
    if img:
        # 圆形遮罩
        mask = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.ellipse(mask, (255, 255, 255), (0, 0, size, size))
        avatar = pygame.Surface((size, size), pygame.SRCALPHA)
        avatar.blit(img, (0, 0))
        avatar.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(avatar, (x, y))
        pygame.draw.ellipse(surface, (100, 100, 120), (x, y, size, size), 1)
    else:
        # 默认头像
        pygame.draw.ellipse(surface, (80, 80, 100), (x, y, size, size))
        # 简化的"人"形
        center_x = x + size // 2
        head_y = y + size // 3
        pygame.draw.circle(surface, (150, 150, 170), (center_x, head_y), size // 6)
        pygame.draw.arc(surface, (150, 150, 170),
                       (x + size//4, y + size*2//3 - size//8, size//2, size//2),
                       3.14, 0, 1)


# 全局单例
_notification_manager: Optional[EventNotificationManager] = None

def get_notification_manager(screen_w: int = 0, screen_h: int = 0) -> EventNotificationManager:
    """获取全局通知管理器"""
    global _notification_manager
    if _notification_manager is None:
        if screen_w == 0 or screen_h == 0:
            try:
                screen_w, screen_h = pygame.display.get_surface().get_size()
            except:
                screen_w, screen_h = 1280, 720
        _notification_manager = EventNotificationManager(screen_w, screen_h)
    return _notification_manager
