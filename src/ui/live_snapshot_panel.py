"""
大宋实况 - 实况快照面板
========================================

小红书/抖音风格的事件展示面板
包含：
- 爆款标题
- AI生成定格画面
- 热度指标
- 模拟评论/弹幕
- 玩家选择按钮
"""

import pygame
import random
import math
import os
from pathlib import Path as PyPath
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass

from src.definitions import (
    COLOR_UI_PANEL, COLOR_BTN, COLOR_BTN_HOVER, COLOR_TEXT, COLOR_TEXT_WHITE,
    GAME_STATE_PLAYING
)
from src.utils import resource_path

# 默认屏幕尺寸（实际值由构造函数传入）
DEFAULT_SCREEN_W = 1280
DEFAULT_SCREEN_H = 720


@dataclass
class LiveSnapshotData:
    """实况快照数据"""
    title: str                       # 爆款标题
    image_url: Optional[str] = None  # AI生图URL (None时显示加载中)
    heat_score: int = 0              # 热度值
    comments: List[Dict] = None      # 评论列表
    tags: List[str] = None           # 标签
    choices: List[Dict] = None       # 玩家选项
    actor_names: List[str] = None    # 演员名字
    news_item: object = None         # 关联的 LiveNewsItem
    description: str = ""            # 事件详细描述（前因后果）
    
    def __post_init__(self):
        if self.comments is None:
            self.comments = []
        if self.tags is None:
            self.tags = []
        if self.choices is None:
            self.choices = []
        if self.actor_names is None:
            self.actor_names = []


class LiveSnapshotPanel:
    """实况快照展示面板
    
    仿抖音/小红书风格的全屏事件面板
    """
    
    def __init__(self, screen_w: int, screen_h: int):
        self.screen_w = screen_w
        self.screen_h = screen_h
        
        # 面板宽度：根据图片宽度动态计算（比图片宽一点点）
        self.img_max_w = 480  # 图片最大宽度
        self.panel_w = self.img_max_w + 80  # 图片宽度 + 左右边距
        
        # 面板高度：自适应（初始值，会在show时根据内容调整）
        self.panel_h = 800  # 默认高度，实际会根据内容调整
        self.panel_y = 50  # 顶部留白
        
        # 水平居中
        self.panel_x = (screen_w - self.panel_w) // 2
        
        # 间距常量（可配置）
        self.SECTION_GAP = 12  # 各部分之间的空行
        self.COMMENT_BUTTON_GAP = 12  # 评论区和按钮区间距
        self.DANMAKU_Y_OFFSET = 30  # 弹幕位置上移（从图片顶部往下）
        
        # 当前显示的快照
        self.snapshot: Optional[LiveSnapshotData] = None
        self.visible = False
        
        # 动画状态
        self.show_progress = 0.0  # 0~1 弹出动画
        self.heat_anim = 0.0      # 热度数字滚动
        self.comment_scroll = 0   # 评论滚动位置
        self.danmaku_timer = 0    # 弹幕生成计时器
        
        # 弹幕系统
        self.flying_comments: List[Dict] = []  # {text, x, y, speed, color}
        
        # 评论动画
        self.visible_comment_count = 0  # 当前显示的评论数
        self.comment_timer = 0  # 评论逐个出现计时
        
        # 选项悬停
        self.hovered_choice = -1
        
        # 当事人头像悬停
        self.hovered_actor_index = -1  # 当前悬浮的当事人索引
        self.actor_name_widths = {}  # 缓存名字宽度
        
        # 评论区滚动
        self.comment_scroll_y = 0  # 滚动偏移量
        self.comment_max_scroll = 0  # 最大滚动值
        self.comment_scroll_speed = 25  # 每次滚动像素数
        self.comment_area_rect = None  # 评论区区域（用于滚轮检测）
        
        # 两级选择状态
        self.choice_level = 1  # 1=第一级(当面/快信), 2=第二级(具体选项)
        self.original_choices = []  # 保存原始选项
        
        # 字体缓存（必须在 _create_placeholder 之前初始化）
        self._font_cache = {}
        
        # 占位图
        self.placeholder_surface = None
        self._create_placeholder()
        
        # 回调
        self.on_choice_selected: Optional[Callable[[int, Dict], None]] = None
        self.on_close: Optional[Callable[[], None]] = None
    
    def _get_font(self, size: int) -> pygame.font.Font:
        """获取缓存的字体"""
        if size not in self._font_cache:
            # 优先使用系统中文字体，确保中文正常显示
            font_names = "microsoftyahei,simhei,pingfangsc,notosanscjk,arial"
            self._font_cache[size] = pygame.font.SysFont(font_names, size)
        return self._font_cache[size]
    
    def _create_placeholder(self):
        """创建图片占位符"""
        w, h = self.panel_w - 40, 240
        self.placeholder_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # 渐变背景
        for y in range(h):
            r = int(30 + (60 - 30) * y / h)
            g = int(25 + (50 - 25) * y / h)
            b = int(40 + (70 - 40) * y / h)
            pygame.draw.line(self.placeholder_surface, (r, g, b), (0, y), (w, y))
        
        # 加载中图标（使用纯文本避免emoji渲染问题）
        font = self._get_font(16)
        text = font.render("[加载中] 事件画面生成中...", True, (150, 150, 170))
        text_rect = text.get_rect(center=(w // 2, h // 2))
        self.placeholder_surface.blit(text, text_rect)
        
        # 装饰边框
        pygame.draw.rect(self.placeholder_surface, (80, 70, 100), (0, 0, w, h), 2, border_radius=8)
    
    def show(self, snapshot: LiveSnapshotData):
        """显示快照面板"""
        self.snapshot = snapshot
        self.visible = True
        self.show_progress = 0.0
        self.heat_anim = 0.0
        self.visible_comment_count = 0
        self.comment_timer = 0
        self.flying_comments.clear()
        self.danmaku_timer = 0
        
        # 初始化两级选择状态
        self.choice_level = 1
        if snapshot.choices:
            # 保存原始选项
            self.original_choices = snapshot.choices.copy()
            # 设置第一级选项：当面处理 + 快信处理
            snapshot.choices = [
                {"text": "当面处理", "action": "FACE_TO_FACE", "_level": 1},
                {"text": "快信处理", "action": "LETTER", "_level": 1}
            ]
        else:
            self.original_choices = []
        
        # 【修改】直接显示全部热评，不逐个出现
        if snapshot.comments:
            self.visible_comment_count = len(snapshot.comments)
        
        # 【改进】立即生成几条初始弹幕，让效果更明显
        if snapshot.comments:
            for i in range(min(3, len(snapshot.comments))):
                comment = snapshot.comments[i]
                self.flying_comments.append({
                    'text': comment['text'][:15],
                    'x': self.panel_x + self.panel_w - i * 100,  # 错开位置
                    'y': self.panel_y + self.DANMAKU_Y_OFFSET + random.randint(0, 80),  # 上移50像素
                    'speed': random.uniform(1.0, 2.5),
                    'color': self._get_comment_color(comment.get('type', '中立'))
                })
    
    def hide(self):
        """隐藏面板"""
        self.visible = False
        self.snapshot = None
        self.flying_comments.clear()
        if self.on_close:
            self.on_close()
    
    def update(self, dt_ms: int):
        """更新动画"""
        if not self.visible:
            return
        
        # 弹出动画
        if self.show_progress < 1.0:
            self.show_progress = min(1.0, self.show_progress + dt_ms / 300)  # 300ms动画
        
        # 热度数字滚动
        if self.snapshot and self.heat_anim < self.snapshot.heat_score:
            speed = max(100, self.snapshot.heat_score // 20)
            self.heat_anim = min(self.snapshot.heat_score, self.heat_anim + speed * dt_ms / 1000 * 30)
        
        # 【修复】定期检查图片是否已异步加载完成
        if self.snapshot and self.snapshot.image_url == "loading":
            # 检查news_item上是否已有图片surface（异步回调已完成）
            news_item = self.snapshot.news_item
            if news_item:
                if hasattr(news_item, '_image_surface') and news_item._image_surface:
                    # 图片已就绪，更新状态
                    self.snapshot.image_url = getattr(news_item, '_image_path', 'ready')
                    self.snapshot._image_surface = news_item._image_surface
                    print(f"[LiveSnapshotPanel] 检测到图片已就绪，更新显示")
        
        # 【修改】评论已全部显示，不需要逐个出现
        # 保留代码结构，但不做任何事
        
        # 弹幕生成
        self.danmaku_timer += dt_ms
        if self.danmaku_timer > 2000:  # 每2秒生成一条弹幕
            self.danmaku_timer = 0
            if self.snapshot and self.snapshot.comments:
                # 从评论中随机选一条作为弹幕
                comment = random.choice(self.snapshot.comments)
                self.flying_comments.append({
                    'text': comment['text'][:15],  # 限制长度
                    'x': self.panel_x + self.panel_w,  # 从右侧开始
                    'y': self.panel_y + self.DANMAKU_Y_OFFSET + random.randint(0, 200),
                    'speed': random.uniform(1.5, 3.0),
                    'color': self._get_comment_color(comment.get('type', '中立'))
                })
        
        # 更新弹幕位置
        for danmaku in self.flying_comments[:]:
            danmaku['x'] -= danmaku['speed']
            if danmaku['x'] < self.panel_x - 200:
                self.flying_comments.remove(danmaku)
    
    def _get_comment_color(self, comment_type: str) -> tuple:
        """根据评论类型返回颜色 - 加深以提高报纸背景对比度"""
        colors = {
            '支持': (0, 120, 0),      # 深绿色
            '反对': (180, 0, 0),      # 深红色
            '中立': (80, 80, 80),     # 深灰色
            '搞笑': (180, 140, 0),    # 深黄色/金色
        }
        return colors.get(comment_type, (80, 80, 80))
    
    def handle_event(self, event: pygame.event.Event) -> bool:
        """处理事件，返回是否消费了事件"""
        if not self.visible:
            return False
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            
            # 点击关闭按钮
            close_rect = pygame.Rect(
                self.panel_x + self.panel_w - 40,
                self.panel_y + 10,
                30, 30
            )
            if close_rect.collidepoint(mx, my):
                self.hide()
                return True
            
            # 点击选项 - 使用缓存的按钮位置（在draw中计算）
            if self.snapshot and self.snapshot.choices and hasattr(self, '_cached_button_rects'):
                for i, btn_rect in enumerate(self._cached_button_rects):
                    # 将相对坐标转换为屏幕坐标
                    screen_rect = btn_rect.move(self.panel_x, self.panel_y)
                    if screen_rect.collidepoint(mx, my):
                        # [!] 播放选择确认音效
                        try:
                            from src.audio.sound_manager import get_sound_manager
                            get_sound_manager().play_confirm()
                        except Exception:
                            pass
                        
                        choice = self.snapshot.choices[i]
                        action = choice.get('action', '')
                        
                        # 第一级选择处理
                        if choice.get('_level') == 1:
                            if action == 'FACE_TO_FACE':
                                # 当面处理：触发回调（由外部处理）
                                if self.on_choice_selected:
                                    self.on_choice_selected(i, choice)
                                self.hide()
                                return True
                            elif action == 'LETTER':
                                # 快信处理：切换到第二级选项
                                self.choice_level = 2
                                # 恢复原始选项，并在最后添加返回键
                                self.snapshot.choices = self.original_choices.copy()
                                self.snapshot.choices.append({
                                    "text": "← 返回",
                                    "action": "BACK",
                                    "_level": 2
                                })
                                self.hovered_choice = -1
                                return True
                        # 第二级选择处理
                        elif choice.get('_level') == 2:
                            if action == 'BACK':
                                # 返回第一级
                                self.choice_level = 1
                                self.snapshot.choices = [
                                    {"text": "当面处理", "action": "FACE_TO_FACE", "_level": 1},
                                    {"text": "快信处理", "action": "LETTER", "_level": 1}
                                ]
                                self.hovered_choice = -1
                                return True
                            else:
                                # 普通选项：触发回调
                                if self.on_choice_selected:
                                    self.on_choice_selected(i, choice)
                                self.hide()
                                return True
                        else:
                            # 普通选项（兼容旧逻辑）
                            if self.on_choice_selected:
                                self.on_choice_selected(i, choice)
                            self.hide()
                            return True
            
            # 点击面板外关闭
            panel_rect = pygame.Rect(self.panel_x, self.panel_y, self.panel_w, self.panel_h)
            if not panel_rect.collidepoint(mx, my):
                self.hide()
                return True
        
        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hovered_choice = -1
            
            # 使用缓存的按钮位置检测悬停
            if self.snapshot and self.snapshot.choices and hasattr(self, '_cached_button_rects'):
                for i, btn_rect in enumerate(self._cached_button_rects):
                    screen_rect = btn_rect.move(self.panel_x, self.panel_y)
                    if screen_rect.collidepoint(mx, my):
                        self.hovered_choice = i
                        break
        
        # 处理评论区滚轮事件
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4 or event.button == 5:  # 滚轮上/下
                mx, my = event.pos
                # 检查鼠标是否在评论区区域内
                if self.comment_area_rect and self.comment_area_rect.collidepoint(mx, my):
                    # 计算滚动方向：4=上滚(向上滚动内容)，5=下滚(向下滚动内容)
                    direction = -1 if event.button == 4 else 1
                    self.comment_scroll_y += direction * self.comment_scroll_speed
                    # 限制滚动范围
                    self.comment_scroll_y = max(0, min(self.comment_scroll_y, self.comment_max_scroll))
                    return True  # 消费事件
        
        return True  # 面板打开时消费所有事件
    
    def draw(self, screen: pygame.Surface):
        """绘制面板"""
        if not self.visible or not self.snapshot:
            return
        
        # 半透明背景遮罩
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(180 * self.show_progress)))
        screen.blit(overlay, (0, 0))
        
        # 弹出动画缩放
        scale = 0.8 + 0.2 * self._ease_out_back(self.show_progress)
        
        # 【关键】先预计算内容高度（简化版，用于确定面板高度）
        content_height = self._estimate_content_height()
        # 最小高度和最大高度限制
        min_h = 500
        max_h = self.screen_h - 100  # 留边距
        actual_h = max(min_h, min(content_height, max_h))
        
        # 更新面板高度（自适应）
        self.panel_h = actual_h
        
        # 计算动画后的面板位置（垂直居中）
        anim_w = int(self.panel_w * scale)
        anim_h = int(self.panel_h * scale)
        anim_x = self.panel_x + (self.panel_w - anim_w) // 2
        anim_y = (self.screen_h - anim_h) // 2  # 屏幕居中
        
        # 主面板背景 - 使用实际计算出的高度
        panel_surface = pygame.Surface((self.panel_w, self.panel_h), pygame.SRCALPHA)
        
        # 报纸黄色背景（复古风格）- 纯色
        paper_color = (255, 250, 220)  # 更黄的报纸黄
        panel_surface.fill(paper_color)
        
        # 边框
        pygame.draw.rect(panel_surface, (80, 70, 100), (0, 0, self.panel_w, self.panel_h), 2, border_radius=15)
        
        # 绘制内容 - 小红书风格布局（各部分之间留空行）
        y_offset = 20
        
        # === 图片区域 ===
        y_offset = self._draw_image(panel_surface, y_offset)
        y_offset += self.SECTION_GAP  # 空行
        
        # === 标题和描述（双列布局：左侧参与人，右侧标题+正文）===
        y_offset = self._draw_title_and_actors(panel_surface, y_offset)
        y_offset += self.SECTION_GAP  # 空行
        
        # === 标签（小红书风格：正文下方）===
        y_offset = self._draw_tags(panel_surface, y_offset)
        y_offset += self.SECTION_GAP  # 空行
        
        # === 评论区 ===
        # 第一次调用：估算评论区高度（用于计算面板总高度）
        # 限制评论区最大高度为150px，避免占用过多空间
        comments_temp_y = self._draw_comments(panel_surface, y_offset, max_height=150)
        comments_actual_height = comments_temp_y - y_offset
        
        # 【关键】根据实际内容高度，动态计算按钮位置和面板的最终高度
        # 按钮紧跟在评论区下方，留出 COMMENT_BUTTON_GAP 间距
        num_choices = len(self.snapshot.choices) if self.snapshot.choices else 0
        buttons_height = num_choices * 60  # 按钮总高度
        
        # 计算按钮起始位置（评论区高度 + 间距）
        buttons_y = y_offset + comments_actual_height + self.COMMENT_BUTTON_GAP
        
        # 计算所需总高度（内容 + 间距 + 按钮 + 底部边距）
        required_height = buttons_y + buttons_height + 50  # 50是底部边距，确保按钮完全可见
        
        # 限制最小和最大高度，确保按钮完全显示
        min_h = max(500, required_height)  # 最小高度必须能容纳所有内容
        max_h = self.screen_h - 50  # 留50px边距
        
        # 如果内容超出屏幕，需要滚动，但目前先确保高度足够
        if required_height > max_h:
            # 内容太多，使用最大高度（后续可以考虑添加滚动）
            self.panel_h = max_h
        else:
            self.panel_h = required_height
        
        # 重新创建面板surface（因为高度可能改变了）
        panel_surface = pygame.Surface((self.panel_w, self.panel_h), pygame.SRCALPHA)
        panel_surface.fill(paper_color)
        pygame.draw.rect(panel_surface, (80, 70, 100), (0, 0, self.panel_w, self.panel_h), 2, border_radius=15)
        
        # 重新绘制所有内容到新的surface
        y_offset = 20
        y_offset = self._draw_image(panel_surface, y_offset)
        y_offset += self.SECTION_GAP
        y_offset = self._draw_title_and_actors(panel_surface, y_offset)
        y_offset += self.SECTION_GAP
        y_offset = self._draw_tags(panel_surface, y_offset)
        y_offset += self.SECTION_GAP
        # 第二次绘制使用相同的max_height，确保Y值一致
        y_offset = self._draw_comments(panel_surface, y_offset, max_height=150)
        
        # 计算按钮位置
        buttons_y = y_offset + self.COMMENT_BUTTON_GAP
        
        # === 选项按钮 ===
        self._draw_choices_at_y(panel_surface, buttons_y)
        
        # === 关闭按钮 ===
        self._draw_close_button(panel_surface)
        
        # 绘制到屏幕（使用实际位置，不使用动画缩放）
        screen.blit(panel_surface, (self.panel_x, self.panel_y))
        
        # 绘制弹幕（在面板外绘制）
        self._draw_danmaku(screen)
    
    def _draw_choices_at_y(self, surface: pygame.Surface, start_y: int):
        """在指定Y位置绘制选项按钮，并缓存按钮位置用于点击检测"""
        if not self.snapshot.choices:
            return
        
        font = self._get_font(22)
        num_choices = len(self.snapshot.choices)
        
        # 初始化按钮位置缓存
        self._cached_button_rects = []
        
        for i, choice in enumerate(self.snapshot.choices):
            btn_rect = pygame.Rect(30, start_y + i * 60, self.panel_w - 60, 50)
            
            # 缓存按钮位置（相对坐标，用于handle_event）
            self._cached_button_rects.append(btn_rect)
            
            is_hover = (i == self.hovered_choice)
            
            if is_hover:
                btn_color = (60, 60, 80)
                border_color = (100, 100, 140)
            else:
                btn_color = (40, 40, 60)
                border_color = (70, 70, 90)
            
            pygame.draw.rect(surface, btn_color, btn_rect, border_radius=8)
            pygame.draw.rect(surface, border_color, btn_rect, 2, border_radius=8)
            
            text = choice.get('text', f'选项{i+1}')
            text_surf = font.render(text, True, (255, 255, 255))
            text_x = btn_rect.centerx - text_surf.get_width() // 2
            text_y = btn_rect.centery - text_surf.get_height() // 2
            surface.blit(text_surf, (text_x, text_y))
    
    # 注意：旧的绘制代码已删除
    
    def _get_image_bottom_y(self, start_y: int) -> int:
        """计算图片区域底部Y坐标"""
        margin_x = 40
        max_img_w = self.panel_w - margin_x * 2
        max_img_h = 360
        
        # 检查是否有实际图片
        img_surface = None
        if self.snapshot.image_url and self.snapshot.image_url not in ("placeholder", "loading"):
            news_item = self.snapshot.news_item
            if news_item and hasattr(news_item, '_image_surface') and news_item._image_surface:
                img_surface = news_item._image_surface
            elif hasattr(self.snapshot, '_image_surface') and self.snapshot._image_surface:
                img_surface = self.snapshot._image_surface
        
        if img_surface:
            orig_w, orig_h = img_surface.get_size()
            orig_ratio = orig_w / orig_h
            if orig_ratio > max_img_w / max_img_h:
                display_h = int(max_img_w / orig_ratio)
            else:
                display_h = max_img_h
            return start_y + display_h
        else:
            # 占位图或加载中高度
            return start_y + 280
    
    def _get_title_bottom_y(self, start_y: int) -> int:
        """计算标题区域底部Y坐标"""
        y = start_y
        # 标题（最多2行）
        y += 32 * 2 + 5
        # 当事人头像（如果有）- 36px头像+名字，可能换行
        if self.snapshot.actor_names:
            num_actors = len(self.snapshot.actor_names)
            # 估算每行能放几个头像（头像36+间距12+名字约40）
            actors_per_row = max(1, (self.panel_w - 40) // 100)
            num_rows = (num_actors + actors_per_row - 1) // actors_per_row
            y += (36 + 8) * num_rows + 4  # 头像高度 + 间距
        # 描述（最多3行）
        if self.snapshot.description:
            y += 28 * 3
        return y
    
    def _get_tags_bottom_y(self, start_y: int) -> int:
        """计算标签区域底部Y坐标"""
        if not self.snapshot.tags:
            return start_y
        # 标签高度
        return start_y + 32
    
    def _get_comments_bottom_y(self, start_y: int) -> int:
        """计算评论区底部Y坐标 - 小红书风格布局"""
        if not self.snapshot.comments:
            return start_y
        
        y = start_y
        y += 32  # 标题高度
        
        font_content = self._get_font(15)
        AVATAR_COL_WIDTH = 55
        content_x = 25 + AVATAR_COL_WIDTH
        content_width = self.panel_w - content_x - 25
        LINE_HEIGHT = 18  # 减小行高
        COMMENT_GAP = 8  # 减小评论间距
        
        num_comments = min(self.visible_comment_count, 6)
        for comment in self.snapshot.comments[:num_comments]:
            text = comment.get('text', '')
            
            # 计算内容需要的行数
            content_prefix_width = font_content.size("[赞] ")[0]
            content_lines = self._wrap_comment_text(text, font_content, content_width - content_prefix_width)
            total_lines = 1 + len(content_lines)  # 名字行 + 内容行
            
            # 评论高度 = max(头像高度, 内容行数*行高) + 间距
            comment_height = max(44, total_lines * LINE_HEIGHT + 8)
            y += comment_height + COMMENT_GAP
        
        y += 10  # 底部间距
        return y
    
    def _estimate_content_height(self) -> int:
        """估算内容高度（用于确定面板高度）"""
        if not self.snapshot:
            return 600
        
        h = 20  # 顶部边距
        
        # 图片高度
        h += 280  # 图片默认高度
        h += self.SECTION_GAP
        
        # 标题高度（最多2行）
        h += 32 * 2 + 5
        
        # 当事人头像（如果有）
        if self.snapshot.actor_names:
            h += 28 + 8  # 头像高度 + 间距
        
        # 描述高度（最多3行）
        if self.snapshot.description:
            h += 28 * 3
        
        h += self.SECTION_GAP
        
        # 标签高度
        if self.snapshot.tags:
            h += 32
        h += self.SECTION_GAP
        
        # 评论区高度 - 考虑换行
        if self.snapshot.comments:
            h += 28  # 标题
            font_xs = self._get_font(16)
            content_start_x = 25 + 20 + 6  # avatar_x + avatar_size + spacing
            max_line_width = self.panel_w - content_start_x - 25
            
            num_comments = min(len(self.snapshot.comments), 5)
            for comment in self.snapshot.comments[:num_comments]:
                user = comment.get('user', '路人')
                text = comment.get('text', '')
                user_prefix = f"@{user}[评]："
                user_prefix_width = font_xs.size(user_prefix)[0]
                remaining_width = self.panel_w - content_start_x - user_prefix_width - 25
                
                # 估算行数（考虑用户名占用空间后剩余的宽度）
                if remaining_width > 50:
                    # 第一行可用宽度
                    first_line_available = remaining_width
                    # 后续行可用宽度
                    other_lines_available = max_line_width
                    
                    # 估算需要多少行
                    text_width = font_xs.size(text)[0]
                    if text_width <= first_line_available:
                        lines_needed = 1
                    else:
                        # 第一行 + 剩余文字需要的行数
                        remaining_text_width = text_width - first_line_available
                        lines_needed = 1 + max(1, int(remaining_text_width / other_lines_available))
                else:
                    lines_needed = max(1, int(font_xs.size(text)[0] / max_line_width) + 1)
                
                h += 22 * lines_needed  # 每行22像素
            h += 10  # 底部间距
        
        # 按钮区域高度 - 确保按钮完全可见
        num_choices = len(self.snapshot.choices) if self.snapshot.choices else 0
        h += self.COMMENT_BUTTON_GAP + num_choices * 60 + 50  # 间距 + 按钮 + 更大的底部边距
        
        return h
    
    def _draw_header(self, surface: pygame.Surface, y: int) -> int:
        """绘制顶部标签和热度"""
        font_sm = self._get_font(18)  # 增大字体
        
        # 标签
        x = 20
        for tag in self.snapshot.tags[:3]:  # 最多显示3个标签
            tag_text = f"#{tag}"
            text_surf = font_sm.render(tag_text, True, (150, 200, 255))
            
            # 标签背景
            tag_w = text_surf.get_width() + 12
            tag_h = 22
            tag_rect = pygame.Rect(x, y, tag_w, tag_h)
            pygame.draw.rect(surface, (60, 70, 100, 180), tag_rect, border_radius=11)
            
            surface.blit(text_surf, (x + 6, y + 4))
            x += tag_w + 8
        
        # 热度（使用文字）
        heat_text = f"热度 {int(self.heat_anim):,}"
        heat_surf = font_sm.render(heat_text, True, (255, 100, 50))
        surface.blit(heat_surf, (self.panel_w - heat_surf.get_width() - 50, y + 3))
        
        return y + 35
    
    def _draw_actor_avatars_header(self, surface: pygame.Surface, y: int) -> int:
        """绘制主要演员头像（在图片上方）"""
        if not self.snapshot or not self.snapshot.actor_names:
            return y  # 没有演员，直接返回
        
        from pathlib import Path
        
        avatar_size = 48  # 头像大小
        spacing = 12  # 头像间距
        margin_x = 40  # 左右边距
        
        # 计算总宽度（头像 + 间距）
        num_actors = len(self.snapshot.actor_names)
        total_width = num_actors * avatar_size + (num_actors - 1) * spacing
        
        # 居中排列
        start_x = (self.panel_w - total_width) // 2
        
        # 绘制每个演员头像
        for i, actor_name in enumerate(self.snapshot.actor_names):
            x = start_x + i * (avatar_size + spacing)
            
            # 尝试加载头像
            avatar_surface = None
            avatar_path = PyPath(resource_path(f"assets/head_icon/{actor_name}.png"))
            
            if avatar_path.exists():
                try:
                    avatar_surface = pygame.image.load(str(avatar_path))
                    avatar_surface = pygame.transform.smoothscale(avatar_surface, (avatar_size, avatar_size))
                except:
                    pass
            
            # 绘制圆形裁剪区域
            circle_surf = pygame.Surface((avatar_size, avatar_size), pygame.SRCALPHA)
            pygame.draw.ellipse(circle_surf, (255, 255, 255), (0, 0, avatar_size, avatar_size))
            
            if avatar_surface:
                # 使用头像
                avatar_surface.blit(circle_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                surface.blit(avatar_surface, (x, y))
            else:
                # 使用默认头像（名字首字）
                pygame.draw.ellipse(surface, (100, 100, 130), (x, y, avatar_size, avatar_size))
                font = self._get_font(20)
                initial = actor_name[0] if actor_name else "?"
                text_surf = font.render(initial, True, (240, 240, 240))
                text_x = x + (avatar_size - text_surf.get_width()) // 2
                text_y = y + (avatar_size - text_surf.get_height()) // 2
                surface.blit(text_surf, (text_x, text_y))
            
            # 绘制边框
            pygame.draw.ellipse(surface, (80, 80, 100), (x, y, avatar_size, avatar_size), 2)
            
            # 绘制演员名字（头像下方）
            name_font = self._get_font(12)
            name_surf = name_font.render(actor_name, True, (60, 60, 60))
            name_x = x + (avatar_size - name_surf.get_width()) // 2
            surface.blit(name_surf, (name_x, y + avatar_size + 4))
        
        # 返回新的Y位置（头像 + 名字 + 间距）
        return y + avatar_size + 20 + 10  # 头像高度 + 名字高度 + 间距
    
    def _draw_image(self, surface: pygame.Surface, y: int) -> int:
        """绘制事件图片 - 小红书/报纸风格：保持原始比例，优雅留白"""
        
        margin_x = 40  # 左右边距
        max_img_w = self.panel_w - margin_x * 2  # 最大可用宽度
        max_img_h = 360  # 最大高度（避免过大）
        
        drawn = False
        img_surface = None
        
        # 尝试获取图片
        if self.snapshot.image_url and self.snapshot.image_url not in ("placeholder", "loading"):
            news_item = self.snapshot.news_item
            
            if news_item and hasattr(news_item, '_image_surface') and news_item._image_surface:
                img_surface = news_item._image_surface
            elif hasattr(self.snapshot, '_image_surface') and self.snapshot._image_surface:
                img_surface = self.snapshot._image_surface
            elif self.snapshot.image_url and isinstance(self.snapshot.image_url, str):
                img_surface = self._load_image_from_path(self.snapshot.image_url)
                if img_surface and news_item:
                    news_item._image_surface = img_surface
        
        if img_surface:
            # 获取原始尺寸
            orig_w, orig_h = img_surface.get_size()
            orig_ratio = orig_w / orig_h
            
            # 计算缩放后的尺寸（保持比例，不拉伸）
            # 策略：在限制范围内尽可能大，保持原始比例
            if orig_ratio > max_img_w / max_img_h:
                # 图片偏宽，以宽度为限制
                display_w = max_img_w
                display_h = int(display_w / orig_ratio)
            else:
                # 图片偏高或方正，以高度为限制
                display_h = max_img_h
                display_w = int(display_h * orig_ratio)
            
            # 确保不超出限制
            display_w = min(display_w, max_img_w)
            display_h = min(display_h, max_img_h)
            
            # 居中显示
            img_x = (self.panel_w - display_w) // 2
            
            # 缩放图片（保持比例）
            scaled = pygame.transform.smoothscale(img_surface, (display_w, display_h))
            
            # 绘制阴影效果（报纸风格）
            shadow_offset = 4
            pygame.draw.rect(surface, (20, 20, 25), 
                           (img_x + shadow_offset, y + shadow_offset, display_w, display_h))
            
            # 绘制图片
            surface.blit(scaled, (img_x, y))
            
            # 绘制细边框（优雅风格）
            pygame.draw.rect(surface, (100, 95, 110), 
                           (img_x, y, display_w, display_h), 1)
            
            drawn = True
            actual_img_h = display_h
        
        # 加载中状态
        elif self.snapshot.image_url == "loading":
            img_x = margin_x
            loading_w = max_img_w
            loading_h = 280
            self._draw_loading_image(surface, img_x, y, loading_w, loading_h)
            drawn = True
            actual_img_h = loading_h
        
        # 占位图
        if not drawn:
            img_x = margin_x
            placeholder_w = max_img_w
            placeholder_h = 280
            
            # 创建优雅占位图
            placeholder = pygame.Surface((placeholder_w, placeholder_h), pygame.SRCALPHA)
            # 柔和渐变背景
            for py in range(placeholder_h):
                ratio = py / placeholder_h
                r = int(35 + 20 * ratio)
                g = int(30 + 15 * ratio)
                b = int(45 + 25 * ratio)
                pygame.draw.line(placeholder, (r, g, b), (0, py), (placeholder_w, py))
            
            # 装饰边框
            pygame.draw.rect(placeholder, (70, 65, 85), (0, 0, placeholder_w, placeholder_h), 1)
            
            # 文字
            font = self._get_font(18)
            text = font.render("[AI绘图] 生成中...", True, (140, 135, 160))
            text_rect = text.get_rect(center=(placeholder_w // 2, placeholder_h // 2))
            placeholder.blit(text, text_rect)
            
            surface.blit(placeholder, (img_x, y))
            actual_img_h = placeholder_h
        
        return y + actual_img_h   
    
    def _load_image_from_path(self, path: str) -> Optional[pygame.Surface]:
        """从文件路径加载图片（带缓存）"""
        import os
        
        # 检查文件是否存在
        if not path or not os.path.exists(path):
            return None
        
        try:
            return pygame.image.load(path)
        except Exception as e:
            print(f"[LiveSnapshotPanel] 图片加载失败: {path}, 错误: {e}")
            return None
    
    def _draw_loading_image(self, surface: pygame.Surface, x: int, y: int, w: int, h: int):
        """绘制加载中动画"""
        # 背景
        pygame.draw.rect(surface, (35, 30, 45), (x, y, w, h), border_radius=8)
        pygame.draw.rect(surface, (60, 55, 75), (x, y, w, h), 2, border_radius=8)
        
        # 旋转加载指示器
        import time
        t = time.time() * 3  # 旋转速度
        cx, cy = x + w // 2, y + h // 2
        radius = 25
        
        for i in range(8):
            angle = t + i * (math.pi / 4)
            alpha = int(255 * (1 - i / 8))
            px = cx + int(radius * math.cos(angle))
            py = cy + int(radius * math.sin(angle))
            color = (150, 140, 180, alpha)
            pygame.draw.circle(surface, (150, 140, 180), (px, py), 4 - i // 2)
        
        # 加载文字（使用纯文本避免emoji渲染问题）
        font = self._get_font(14)
        text = font.render("[绘制中] AI作画中...", True, (180, 175, 200))
        text_rect = text.get_rect(center=(cx, cy + 50))
        surface.blit(text, text_rect)
    
    def _draw_title_and_actors(self, surface: pygame.Surface, y: int) -> int:
        """绘制标题+正文，标题下方一行显示参与人（默认只显示头像，悬浮时显示名字并推开后面的头像）"""
        font_lg = self._get_font(26)  # 标题字体
        font_md = self._get_font(20)  # 正文字体
        font_name = self._get_font(14)  # 名字字体
        
        MARGIN = 20
        content_width = self.panel_w - MARGIN * 2
        
        start_y = y
        
        # ===== 主标题（自动换行）=====
        title = self.snapshot.title
        title_lines = self._wrap_text(title, font_lg, content_width)
        
        for i, line in enumerate(title_lines[:2]):  # 最多2行
            text_surf = font_lg.render(line, True, (30, 30, 30))
            surface.blit(text_surf, (MARGIN, y + i * 30))
        
        y += len(title_lines[:2]) * 30 + 6
        
        # ===== 参与人一行显示（在标题下方）=====
        if self.snapshot.actor_names:
            AVATAR_SIZE = 40  # 和评论区头像一样大
            SPACING = 8  # 头像间距
            
            # 预计算每个名字宽度（用于悬浮时推开效果）
            for actor_name in self.snapshot.actor_names:
                if actor_name not in self.actor_name_widths:
                    name_surf = font_name.render(actor_name, True, (80, 80, 80))
                    self.actor_name_widths[actor_name] = name_surf.get_width()
            
            # 计算每个头像的位置（考虑悬浮推开效果）
            actor_positions = []  # [(x, show_name), ...]
            current_x = MARGIN
            
            for i, actor_name in enumerate(self.snapshot.actor_names[:6]):  # 最多6个
                # 检查是否悬浮在这个头像上
                avatar_rect = pygame.Rect(
                    self.panel_x + current_x,
                    self.panel_y + y,
                    AVATAR_SIZE,
                    AVATAR_SIZE
                )
                is_hovered = avatar_rect.collidepoint(pygame.mouse.get_pos())
                
                # 更新悬浮状态（用于handle_event）
                if is_hovered:
                    self.hovered_actor_index = i
                
                show_name = is_hovered
                name_width = self.actor_name_widths.get(actor_name, 40) if show_name else 0
                
                actor_positions.append((current_x, show_name, actor_name, name_width))
                
                # 计算下一个头像的位置
                if show_name:
                    # 显示名字：头像 + 间距 + 名字 + 间距
                    current_x += AVATAR_SIZE + 6 + name_width + SPACING
                else:
                    # 只显示头像：头像 + 间距
                    current_x += AVATAR_SIZE + SPACING
                
                # 如果超出面板宽度，停止
                if current_x > self.panel_w - MARGIN - AVATAR_SIZE:
                    break
            
            # 绘制头像和名字
            for x, show_name, actor_name, name_width in actor_positions:
                # 绘制头像
                self._draw_actor_avatar_small(surface, actor_name, x, y, AVATAR_SIZE)
                
                # 如果悬浮，显示名字（在头像右侧）
                if show_name:
                    name_surf = font_name.render(actor_name, True, (80, 80, 80))
                    name_y = y + (AVATAR_SIZE - name_surf.get_height()) // 2
                    surface.blit(name_surf, (x + AVATAR_SIZE + 6, name_y))
            
            y += AVATAR_SIZE + 10  # 头像高度 + 间距
        
        # ===== 事件描述（正文）=====
        description = self.snapshot.description
        if description:
            desc_lines = self._wrap_text(description, font_md, content_width)
            
            for line in desc_lines[:3]:  # 最多3行
                desc_surf = font_md.render(line, True, (70, 70, 70))
                surface.blit(desc_surf, (MARGIN, y))
                y += 24
        
        return y + 8
    
    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int) -> List[str]:
        """通用文本换行"""
        if not text:
            return []
        
        lines = []
        current_line = ""
        
        for char in text:
            test_line = current_line + char
            if font.size(test_line)[0] > max_width:
                if current_line:
                    lines.append(current_line)
                current_line = char
            else:
                current_line = test_line
        
        if current_line:
            lines.append(current_line)
        
        return lines if lines else [text]
    
    def _draw_actor_avatar_small(self, surface: pygame.Surface, actor_name: str, x: int, y: int, size: int):
        """绘制小型演员头像"""
        from pathlib import Path
        
        avatar_surface = None
        avatar_path = PyPath(resource_path(f"assets/head_icon/{actor_name}.png"))
        
        if avatar_path.exists():
            try:
                avatar_surface = pygame.image.load(str(avatar_path))
                avatar_surface = pygame.transform.smoothscale(avatar_surface, (size, size))
            except:
                pass
        
        # 圆形裁剪
        circle_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.ellipse(circle_surf, (255, 255, 255), (0, 0, size, size))
        
        if avatar_surface:
            avatar_surface.blit(circle_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(avatar_surface, (x, y))
        else:
            # 默认头像
            pygame.draw.ellipse(surface, (100, 100, 130), (x, y, size, size))
            font = self._get_font(max(12, size // 3))
            initial = actor_name[0] if actor_name else "?"
            text_surf = font.render(initial, True, (240, 240, 240))
            text_x = x + (size - text_surf.get_width()) // 2
            text_y = y + (size - text_surf.get_height()) // 2
            surface.blit(text_surf, (text_x, text_y))
        
        # 边框
        pygame.draw.ellipse(surface, (80, 80, 100), (x, y, size, size), 1)
    
    def _draw_actor_avatars_inline(self, surface: pygame.Surface, y: int, title_height: int):
        """在标题行右侧绘制当事人头像（紧凑排列，与标题同高）"""
        if not self.snapshot or not self.snapshot.actor_names:
            return
        
        from pathlib import Path
        
        avatar_size = 28  # 更小的头像，与标题行高匹配
        spacing = 8  # 头像间距
        
        # 计算头像区域总宽度
        num_actors = min(len(self.snapshot.actor_names), 3)  # 最多显示3个
        total_width = num_actors * avatar_size + (num_actors - 1) * spacing
        
        # 靠右排列，留出边距
        start_x = self.panel_w - total_width - 25
        # 垂直居中（基于标题高度）
        avatar_y = y + (title_height - avatar_size) // 2
        
        for i, actor_name in enumerate(self.snapshot.actor_names[:3]):
            x = start_x + i * (avatar_size + spacing)
            
            # 尝试加载头像
            avatar_surface = None
            avatar_path = PyPath(resource_path(f"assets/head_icon/{actor_name}.png"))
            
            if avatar_path.exists():
                try:
                    avatar_surface = pygame.image.load(str(avatar_path))
                    avatar_surface = pygame.transform.smoothscale(avatar_surface, (avatar_size, avatar_size))
                except:
                    pass
            
            # 绘制圆形裁剪区域
            circle_surf = pygame.Surface((avatar_size, avatar_size), pygame.SRCALPHA)
            pygame.draw.ellipse(circle_surf, (255, 255, 255), (0, 0, avatar_size, avatar_size))
            
            if avatar_surface:
                avatar_surface.blit(circle_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                surface.blit(avatar_surface, (x, avatar_y))
            else:
                # 使用默认头像
                pygame.draw.ellipse(surface, (100, 100, 130), (x, avatar_y, avatar_size, avatar_size))
                font = self._get_font(12)
                initial = actor_name[0] if actor_name else "?"
                text_surf = font.render(initial, True, (240, 240, 240))
                text_x = x + (avatar_size - text_surf.get_width()) // 2
                text_y = avatar_y + (avatar_size - text_surf.get_height()) // 2
                surface.blit(text_surf, (text_x, text_y))
            
            # 绘制边框
            pygame.draw.ellipse(surface, (80, 80, 100), (x, avatar_y, avatar_size, avatar_size), 1)
    
    def _draw_actor_avatars_compact(self, surface: pygame.Surface, y: int) -> int:
        """绘制主要演员头像和名字（小红书风格：头像+名字横向排列）"""
        if not self.snapshot or not self.snapshot.actor_names:
            return y  # 没有演员，直接返回
        
        from pathlib import Path
        
        avatar_size = 36  # 增大头像大小
        spacing = 12  # 每个演员之间的间距
        margin_x = 20  # 左边距
        
        start_x = margin_x
        current_x = start_x
        
        # 绘制每个演员（头像+名字）
        for i, actor_name in enumerate(self.snapshot.actor_names[:4]):  # 最多显示4个
            # 尝试加载头像
            avatar_surface = None
            avatar_path = PyPath(resource_path(f"assets/head_icon/{actor_name}.png"))
            
            if avatar_path.exists():
                try:
                    avatar_surface = pygame.image.load(str(avatar_path))
                    avatar_surface = pygame.transform.smoothscale(avatar_surface, (avatar_size, avatar_size))
                except:
                    pass
            
            # 绘制圆形裁剪区域
            circle_surf = pygame.Surface((avatar_size, avatar_size), pygame.SRCALPHA)
            pygame.draw.ellipse(circle_surf, (255, 255, 255), (0, 0, avatar_size, avatar_size))
            
            avatar_y = y
            if avatar_surface:
                # 使用头像
                avatar_surface.blit(circle_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                surface.blit(avatar_surface, (current_x, avatar_y))
            else:
                # 使用默认头像（名字首字）
                pygame.draw.ellipse(surface, (100, 100, 130), (current_x, avatar_y, avatar_size, avatar_size))
                font = self._get_font(16)
                initial = actor_name[0] if actor_name else "?"
                text_surf = font.render(initial, True, (240, 240, 240))
                text_x = current_x + (avatar_size - text_surf.get_width()) // 2
                text_y = avatar_y + (avatar_size - text_surf.get_height()) // 2
                surface.blit(text_surf, (text_x, text_y))
            
            # 绘制边框
            pygame.draw.ellipse(surface, (80, 80, 100), (current_x, avatar_y, avatar_size, avatar_size), 2)
            
            # 绘制演员名字（头像右侧）
            name_font = self._get_font(13)
            name_surf = name_font.render(actor_name, True, (60, 60, 60))
            name_x = current_x + avatar_size + 6
            name_y = avatar_y + (avatar_size - name_surf.get_height()) // 2
            surface.blit(name_surf, (name_x, name_y))
            
            # 计算下一个演员的位置
            actor_width = avatar_size + 6 + name_surf.get_width() + spacing
            current_x += actor_width
            
            # 如果超出面板宽度，换行
            if current_x > self.panel_w - 80 and i < len(self.snapshot.actor_names) - 1:
                current_x = start_x
                y += avatar_size + 8
        
        # 返回新的Y位置
        return y + avatar_size + 12
    
    def _draw_tags(self, surface: pygame.Surface, y: int) -> int:
        """绘制标签（小红书风格：纯文字蓝色标签），热度右对齐"""
        font = self._get_font(18)
        start_y = y
        x = 20
        
        # 先计算热度文字的宽度
        heat_text = f"热度 {int(self.heat_anim):,}"
        heat_surf = font.render(heat_text, True, (255, 120, 80))
        heat_width = heat_surf.get_width()
        
        # 可用宽度（留出热度区域）
        available_width = self.panel_w - 40 - heat_width - 20  # 边距 + 热度宽度 + 间距
        
        # 绘制标签
        if self.snapshot.tags:
            for tag in self.snapshot.tags[:4]:  # 最多显示4个标签
                tag_text = f"#{tag}"
                text_surf = font.render(tag_text, True, (80, 160, 255))
                
                # 检查是否超出可用宽度
                if x + text_surf.get_width() > available_width:
                    break  # 超出空间，停止绘制标签
                
                surface.blit(text_surf, (x, y + 4))
                x += text_surf.get_width() + 15
        
        # 热度右对齐
        heat_x = self.panel_w - heat_width - 25
        surface.blit(heat_surf, (heat_x, y + 4))
        
        return y + 32
    
    def _draw_comments(self, surface: pygame.Surface, y: int, max_height: int = 200) -> int:
        """绘制评论区 - 小红书风格：左侧头像，右侧3行（名字/[赞]+内容），支持滚动
        
        Args:
            surface: 绘制目标
            y: 起始Y坐标
            max_height: 评论区最大高度（默认200px）
        
        Returns:
            评论区实际占用的高度
        """
        if not self.snapshot.comments:
            return y
        
        font_sm = self._get_font(20)  # 标题字体
        font_name = self._get_font(15)  # 名字字体
        font_content = self._get_font(15)  # 评论内容字体
        
        # 评论区标题（黑色文字）
        title_surf = font_sm.render("[热评] 吃瓜群众怎么看:", True, (30, 30, 30))
        surface.blit(title_surf, (20, y))
        y += 32
        
        # 布局常量
        AVATAR_SIZE = 40  # 头像大小
        AVATAR_COL_WIDTH = 55  # 头像列固定宽度
        LINE_HEIGHT = 18  # 每行文字高度
        COMMENT_GAP = 8  # 评论间距
        
        # 计算所有评论的总高度
        total_comments_height = 0
        comment_heights = []  # 记录每条评论的高度
        for comment in self.snapshot.comments[:self.visible_comment_count]:
            text = comment.get('text', '')
            content_x = 25 + AVATAR_COL_WIDTH
            content_width = self.panel_w - content_x - 25
            
            # 计算内容行数
            content_prefix = "[赞] "
            content_lines = self._wrap_comment_text(text, font_content, content_width - font_content.size(content_prefix)[0])
            total_lines = 1 + len(content_lines)  # 名字行 + 内容行数
            comment_height = max(AVATAR_SIZE + 4, total_lines * LINE_HEIGHT + 8)
            
            comment_heights.append(comment_height)
            total_comments_height += comment_height + COMMENT_GAP
        
        # 评论区可见区域
        comments_area_top = y
        # 实际显示高度 = min(总高度, 最大高度)
        actual_display_height = min(total_comments_height, max_height)
        comments_area_bottom = comments_area_top + actual_display_height
        
        # 记录评论区区域（用于滚轮检测）- 使用屏幕坐标
        self.comment_area_rect = pygame.Rect(
            self.panel_x + 25,
            self.panel_y + comments_area_top,
            self.panel_w - 50,
            actual_display_height
        )
        
        # 更新最大滚动值
        self.comment_max_scroll = max(0, total_comments_height - actual_display_height)
        self.comment_scroll_y = min(self.comment_scroll_y, self.comment_max_scroll)
        
        # 创建裁剪区域（只显示评论区内）
        clip_rect = pygame.Rect(25, comments_area_top, self.panel_w - 50, actual_display_height)
        
        # 保存原始裁剪区域
        original_clip = surface.get_clip()
        # 设置评论区裁剪区域
        surface.set_clip(clip_rect)
        
        # 绘制评论（考虑滚动偏移）
        current_y = y - self.comment_scroll_y
        displayed_count = 0
        
        for i, comment in enumerate(self.snapshot.comments[:self.visible_comment_count]):
            user = comment.get('user', '路人')
            text = comment.get('text', '')
            ctype = comment.get('type', '中立')
            
            comment_height = comment_heights[i] if i < len(comment_heights) else 44
            
            # 跳过完全在可见区域外的评论
            if current_y + comment_height < comments_area_top or current_y > comments_area_bottom:
                current_y += comment_height + COMMENT_GAP
                continue
            
            # 评论类型图标
            type_icons = {
                '支持': '[赞]',
                '反对': '[踩]', 
                '中立': '[围观]',
                '搞笑': '[笑]'
            }
            type_icon = type_icons.get(ctype, '[评]')
            
            # 计算布局
            avatar_x = 25
            content_x = avatar_x + AVATAR_COL_WIDTH
            content_width = self.panel_w - content_x - 25
            
            # 换行处理评论内容
            content_prefix = f"{type_icon} "
            content_lines = self._wrap_comment_text(text, font_content, content_width - font_content.size(content_prefix)[0])
            
            # 绘制头像（左侧固定列，垂直居中）
            avatar_y = current_y + (comment_height - AVATAR_SIZE) // 2
            self._draw_small_avatar(surface, user, avatar_x, avatar_y, AVATAR_SIZE)
            
            # 第1行：用户名
            name_color = self._get_comment_color(ctype)
            name_surf = font_name.render(user, True, name_color)
            surface.blit(name_surf, (content_x, current_y + 2))
            
            # 第2行及以后：[赞]+评论内容
            content_y = current_y + 2 + LINE_HEIGHT
            for line_idx, line_text in enumerate(content_lines):
                if line_idx == 0:
                    # 第一行带[赞]前缀
                    prefix_surf = font_content.render(content_prefix, True, (200, 120, 60))
                    surface.blit(prefix_surf, (content_x, content_y))
                    
                    text_surf = font_content.render(line_text, True, (60, 60, 60))
                    surface.blit(text_surf, (content_x + prefix_surf.get_width(), content_y))
                else:
                    # 后续行对齐到内容起始位置
                    text_surf = font_content.render(line_text, True, (60, 60, 60))
                    surface.blit(text_surf, (content_x, content_y))
                
                content_y += LINE_HEIGHT
            
            current_y += comment_height + COMMENT_GAP
            displayed_count += 1
        
        # 恢复原始裁剪区域
        surface.set_clip(original_clip)
        
        # 绘制滚动条（如果有可滚动内容）
        if self.comment_max_scroll > 0:
            scrollbar_x = self.panel_w - 15
            scrollbar_top = comments_area_top + 5
            scrollbar_height = actual_display_height - 10
            
            # 滚动条背景
            pygame.draw.rect(surface, (200, 200, 200), (scrollbar_x, scrollbar_top, 8, scrollbar_height), border_radius=4)
            
            # 滚动条滑块
            scroll_ratio = self.comment_scroll_y / self.comment_max_scroll if self.comment_max_scroll > 0 else 0
            thumb_height = max(30, scrollbar_height * (actual_display_height / total_comments_height))
            thumb_y = scrollbar_top + (scrollbar_height - thumb_height) * scroll_ratio
            pygame.draw.rect(surface, (100, 100, 120), (scrollbar_x, thumb_y, 8, thumb_height), border_radius=4)
        
        # 如果还有更多评论未显示，添加提示
        total_comments = len(self.snapshot.comments)
        if total_comments > self.visible_comment_count:
            more_text = f"...还有 {total_comments - self.visible_comment_count} 条热评"
            more_surf = font_content.render(more_text, True, (120, 120, 150))
            surface.blit(more_surf, (25 + AVATAR_COL_WIDTH, comments_area_bottom - 20))
        
        # 返回评论区底部Y坐标（标题32px + 评论区域高度）
        return comments_area_bottom + 5
    
    def _wrap_comment_text(self, text: str, font: pygame.font.Font, max_width: int) -> List[str]:
        """将评论文本按最大宽度换行"""
        if not text:
            return [""]
        
        lines = []
        current_line = ""
        
        for char in text:
            test_line = current_line + char
            if font.size(test_line)[0] > max_width:
                if current_line:
                    lines.append(current_line)
                current_line = char
            else:
                current_line = test_line
        
        if current_line:
            lines.append(current_line)
        
        # 如果没有换行，返回原文本
        if not lines:
            lines = [text]
        
        return lines
    
    # 注意：_draw_choices 已被 _draw_choices_at_y 替代
    # 此方法已不再使用
    
    def _draw_close_button(self, surface: pygame.Surface):
        """绘制关闭按钮"""
        x, y = self.panel_w - 40, 10
        
        # 背景圆
        pygame.draw.circle(surface, (60, 55, 70), (x + 15, y + 15), 15)
        pygame.draw.circle(surface, (100, 90, 120), (x + 15, y + 15), 15, 2)
        
        # X 图标（使用画线代替字体，避免渲染问题）
        cx, cy = x + 15, y + 15
        line_len = 7
        pygame.draw.line(surface, (200, 200, 210), (cx - line_len, cy - line_len), (cx + line_len, cy + line_len), 2)
        pygame.draw.line(surface, (200, 200, 210), (cx - line_len, cy + line_len), (cx + line_len, cy - line_len), 2)
    
    def _draw_danmaku(self, screen: pygame.Surface):
        """绘制飞行弹幕"""
        font = self._get_font(20)  # 增大弹幕字体
        
        for danmaku in self.flying_comments:
            # 带阴影的弹幕文字
            shadow = font.render(danmaku['text'], True, (0, 0, 0))
            text = font.render(danmaku['text'], True, danmaku['color'])
            
            x, y = int(danmaku['x']), int(danmaku['y'])
            screen.blit(shadow, (x + 1, y + 1))
            screen.blit(text, (x, y))
    
    def _draw_small_avatar(self, surface: pygame.Surface, user_name: str, x: int, y: int, size: int = 20):
        """绘制小头像（用于评论区）"""
        
        # 头像路径 - 唯一路径
        avatar_path = PyPath(resource_path(f"assets/head_icon/{user_name}.png"))
        
        # 尝试加载头像
        avatar_surface = None
        if avatar_path.exists():
            try:
                avatar_surface = pygame.image.load(str(avatar_path))
                avatar_surface = pygame.transform.smoothscale(avatar_surface, (size, size))
            except Exception as e:
                print(f"[LiveSnapshotPanel] 头像加载失败: {avatar_path}, 错误: {e}")
                pass
        
        # 绘制圆形裁剪区域
        circle_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.ellipse(circle_surf, (255, 255, 255), (0, 0, size, size))
        
        if avatar_surface:
            # 使用头像
            avatar_surface.blit(circle_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(avatar_surface, (x, y))
        else:
            # 使用默认头像（名字首字）
            pygame.draw.ellipse(surface, (120, 120, 140), (x, y, size, size))
            font = self._get_font(max(10, size // 2))
            initial = user_name[0] if user_name else "?"
            text_surf = font.render(initial, True, (240, 240, 240))
            text_x = x + (size - text_surf.get_width()) // 2
            text_y = y + (size - text_surf.get_height()) // 2
            surface.blit(text_surf, (text_x, text_y))
        
        # 绘制边框
        pygame.draw.ellipse(surface, (100, 100, 120), (x, y, size, size), 1)
    
    def _ease_out_back(self, t: float) -> float:
        """弹性缓出动画曲线"""
        c1 = 1.70158
        c3 = c1 + 1
        return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)


# 全局单例
_snapshot_panel: Optional[LiveSnapshotPanel] = None

def get_snapshot_panel(screen_w: int = 0, screen_h: int = 0) -> LiveSnapshotPanel:
    """获取全局快照面板"""
    global _snapshot_panel
    if _snapshot_panel is None:
        if screen_w == 0 or screen_h == 0:
            screen_w, screen_h = pygame.display.get_surface().get_size()
        _snapshot_panel = LiveSnapshotPanel(screen_w, screen_h)
    return _snapshot_panel