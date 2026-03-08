# src/ui/chat_ui.py
"""
AI聊天界面 - 提供玩家与NPC的实时对话界面
支持文本输入、消息显示、情绪展示等功能
"""

import pygame
import math
from typing import List, Optional, Callable
from dataclasses import dataclass


@dataclass
class DisplayMessage:
    """显示用的消息"""
    role: str           # "player" / "npc" / "system"
    content: str
    emotion: str = ""
    action: str = ""
    display_progress: float = 1.0  # 打字机效果进度 0-1


class ChatUI:
    """
    AI聊天界面
    
    特性：
    - 底部输入框
    - 消息气泡显示
    - 打字机效果
    - 情绪图标
    - 快捷回复建议
    """
    
    # 颜色定义
    COLOR_BG = (20, 20, 30, 230)           # 背景
    COLOR_INPUT_BG = (40, 40, 55)          # 输入框背景
    COLOR_INPUT_BORDER = (100, 100, 120)   # 输入框边框
    COLOR_INPUT_ACTIVE = (150, 150, 200)   # 激活时边框
    COLOR_PLAYER_MSG = (60, 100, 160)      # 玩家消息气泡
    COLOR_NPC_MSG = (60, 60, 80)           # NPC消息气泡
    COLOR_SYSTEM_MSG = (50, 50, 50)        # 系统消息
    COLOR_TEXT = (240, 240, 240)           # 文字
    COLOR_NAME = (255, 220, 150)           # 名字
    COLOR_ACTION = (180, 180, 150)         # 动作描述
    
    # 情绪图标映射（使用文字替代emoji）
    EMOTION_ICONS = {
        "neutral": "平",
        "happy": "喜",
        "angry": "怒",
        "sad": "哀",
        "surprised": "惊",
        "fearful": "惧",
        "contempt": "蔑",
    }
    
    def __init__(self, screen_w: int, screen_h: int):
        self.screen_w = screen_w
        self.screen_h = screen_h
        
        # 字体
        font_names = "microsoftyahei,simhei,pingfangsc,notosanscjk,arial"
        self.font = pygame.font.SysFont(font_names, 18)
        self.font_name = pygame.font.SysFont(font_names, 16, bold=True)
        self.font_input = pygame.font.SysFont(font_names, 20)
        self.font_hint = pygame.font.SysFont(font_names, 14)
        self.font_emotion = pygame.font.SysFont("segoeuisymbol,notocoloremoji,arial", 24)
        
        # UI布局
        self.panel_w = 450
        self.panel_h = 500
        # 默认居中显示
        self.panel_x = (screen_w - self.panel_w) // 2
        self.panel_y = (screen_h - self.panel_h) // 2
        
        self.input_h = 45
        self.msg_area_h = self.panel_h - self.input_h - 60  # 减去标题和输入框（移除了快捷回复区域）
        
        # 状态
        self.is_active = False
        self.npc_name = ""
        self.npc_emotion = "neutral"
        self.messages: List[DisplayMessage] = []
        
        # 输入状态
        self.input_text = ""
        self.input_active = False
        self.cursor_blink_timer = 0
        self.cursor_visible = True
        
        # 滚动
        self.scroll_offset = 0
        self.max_scroll = 0
        
        # 动画
        self.anim_timer = 0
        self.typing_speed = 0.5  # 每帧显示字符数
        
        # 回调
        self._on_send_callback: Optional[Callable[[str], None]] = None
        self._on_close_callback: Optional[Callable[[], None]] = None
        
        # 【新增】拖拽状态
        self._is_dragging = False
        self._drag_offset_x = 0
        self._drag_offset_y = 0
        self._header_height = 45  # 标题栏高度，用于拖拽检测
        
        # 更新UI元素位置（调用方法以便后续更新时复用）
        self._update_ui_rects()
    
    def _update_ui_rects(self):
        """更新UI元素的位置（当面板位置改变时调用）"""
        # 输入框区域
        self._input_rect = pygame.Rect(
            self.panel_x + 15,
            self.panel_y + self.panel_h - self.input_h - 15,
            self.panel_w - 90,
            self.input_h
        )
        
        # 发送按钮区域
        self._send_btn_rect = pygame.Rect(
            self._input_rect.right + 10,
            self._input_rect.y,
            50,
            self.input_h
        )
        
        # 关闭按钮
        self._close_btn_rect = pygame.Rect(
            self.panel_x + self.panel_w - 35,
            self.panel_y + 8,
            25,
            25
        )
    
    # ═══════════════════════════════════════════════════════════════
    # 公共接口
    # ═══════════════════════════════════════════════════════════════
    
    def show(self, npc_name: str):
        """显示聊天界面"""
        self.is_active = True
        self.npc_name = npc_name
        self.messages.clear()
        self.input_text = ""
        self.scroll_offset = 0
        self.input_active = True
        # 【关键】启用文本输入模式，确保pygame接收TEXTINPUT事件
        pygame.key.start_text_input()
        print(f"[ChatUI] 显示聊天界面: {npc_name}")
    
    def hide(self):
        """隐藏聊天界面"""
        self.is_active = False
        self.input_active = False
        if self._on_close_callback:
            self._on_close_callback()
    
    def add_message(self, role: str, content: str, emotion: str = "", action: str = ""):
        """添加消息"""
        msg = DisplayMessage(
            role=role,
            content=content,
            emotion=emotion,
            action=action,
            display_progress=0.0 if role == "npc" else 1.0  # NPC消息有打字机效果
        )
        self.messages.append(msg)
        
        # 自动滚动到底部
        self._scroll_to_bottom()
        
        # 更新NPC情绪
        if role == "npc" and emotion:
            self.npc_emotion = emotion
    
    def set_processing(self, is_processing: bool):
        """设置处理中状态"""
        if is_processing:
            # 显示"思考中"提示
            self.add_message("system", "思考中...", "", "")
        else:
            # 移除"思考中"提示
            if self.messages and self.messages[-1].content == "思考中...":
                self.messages.pop()
    
    def set_quick_replies(self, replies: List[str]):
        """设置快捷回复选项（已废弃，保留接口兼容性）"""
        pass  # 不再使用快捷回复
    
    def set_on_send(self, callback: Callable[[str], None]):
        """设置发送回调"""
        self._on_send_callback = callback
    
    def set_on_close(self, callback: Callable[[], None]):
        """设置关闭回调"""
        self._on_close_callback = callback
    
    # ═══════════════════════════════════════════════════════════════
    # 事件处理
    # ═══════════════════════════════════════════════════════════════
    
    def handle_event(self, event) -> bool:
        """
        处理事件
        
        Returns:
            bool: 是否消费了事件
        """
        if not self.is_active:
            return False
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            
            # 检查是否点击了面板外部
            panel_rect = pygame.Rect(self.panel_x, self.panel_y, self.panel_w, self.panel_h)
            if not panel_rect.collidepoint(mx, my):
                return False  # 允许点击外部
            
            # 关闭按钮
            if self._close_btn_rect.collidepoint(mx, my):
                self.hide()
                return True
            
            # 输入框
            if self._input_rect.collidepoint(mx, my):
                self.input_active = True
                return True
            
            # 发送按钮
            if self._send_btn_rect.collidepoint(mx, my):
                self._send_message()
                return True
            
            # 【新增】标题栏拖拽检测
            header_rect = pygame.Rect(self.panel_x, self.panel_y, self.panel_w, self._header_height)
            if header_rect.collidepoint(mx, my) and not self._close_btn_rect.collidepoint(mx, my):
                self._is_dragging = True
                self._drag_offset_x = mx - self.panel_x
                self._drag_offset_y = my - self.panel_y
                return True
            
            return True
        
        elif event.type == pygame.MOUSEBUTTONUP:
            # 停止拖拽
            if self._is_dragging:
                self._is_dragging = False
                return True
        
        elif event.type == pygame.MOUSEMOTION:
            # 拖拽中
            if self._is_dragging:
                mx, my = event.pos
                new_x = mx - self._drag_offset_x
                new_y = my - self._drag_offset_y
                
                # 限制在屏幕范围内
                new_x = max(0, min(new_x, self.screen_w - self.panel_w))
                new_y = max(0, min(new_y, self.screen_h - self.panel_h))
                
                self.panel_x = new_x
                self.panel_y = new_y
                
                # 更新所有UI元素的位置
                self._update_ui_rects()
                return True
        
        elif event.type == pygame.MOUSEWHEEL:
            # 先检查鼠标是否在面板内
            mx, my = pygame.mouse.get_pos()
            panel_rect = pygame.Rect(self.panel_x, self.panel_y, self.panel_w, self.panel_h)
            if panel_rect.collidepoint(mx, my):
                # 滚动消息
                self.scroll_offset -= event.y * 30
                self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))
                return True
            return False
        
        elif event.type == pygame.KEYDOWN and self.input_active:
            if event.key == pygame.K_RETURN:
                self._send_message()
                return True
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
                return True
            elif event.key == pygame.K_ESCAPE:
                self.hide()
                return True
            elif event.key == pygame.K_v and event.mod & pygame.KMOD_CTRL:
                # 粘贴
                try:
                    clipboard = pygame.scrap.get(pygame.SCRAP_TEXT)
                    if clipboard:
                        self.input_text += clipboard.decode('utf-8').strip('\x00')
                except:
                    pass
                return True
        
        elif event.type == pygame.TEXTINPUT and self.input_active:
            self.input_text += event.text
            return True
        
        return False
    
    def _send_message(self):
        """发送消息"""
        text = self.input_text.strip()
        if not text:
            print("[ChatUI] _send_message: 输入为空，忽略")
            return
        
        print(f"[ChatUI] _send_message: 发送消息 '{text[:30]}...'")
        
        # 【先清空输入，避免重复发送】
        self.input_text = ""
        
        # 添加玩家消息到UI显示
        self.add_message("player", text)
        print(f"[ChatUI] 玩家消息已添加到显示列表，当前消息数: {len(self.messages)}")
        
        # 调用回调（发送给AI处理）
        if self._on_send_callback:
            print(f"[ChatUI] 调用回调处理消息...")
            self._on_send_callback(text)
        else:
            print("[ChatUI] 警告: 没有设置发送回调!")
    
    # ═══════════════════════════════════════════════════════════════
    # 更新和渲染
    # ═══════════════════════════════════════════════════════════════
    
    def update(self):
        """每帧更新"""
        if not self.is_active:
            return
        
        self.anim_timer += 1
        
        # 光标闪烁
        self.cursor_blink_timer += 1
        if self.cursor_blink_timer >= 30:
            self.cursor_blink_timer = 0
            self.cursor_visible = not self.cursor_visible
        
        # 打字机效果
        for msg in self.messages:
            if msg.display_progress < 1.0:
                msg.display_progress = min(1.0, msg.display_progress + self.typing_speed / max(1, len(msg.content)))
    
    def draw(self, screen):
        """绘制聊天界面"""
        if not self.is_active:
            return
        
        # 主面板背景
        panel_surf = pygame.Surface((self.panel_w, self.panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, self.COLOR_BG, panel_surf.get_rect(), border_radius=12)
        screen.blit(panel_surf, (self.panel_x, self.panel_y))
        
        # 边框
        panel_rect = pygame.Rect(self.panel_x, self.panel_y, self.panel_w, self.panel_h)
        pygame.draw.rect(screen, (100, 100, 130), panel_rect, 2, border_radius=12)
        
        # 标题栏
        self._draw_header(screen)
        
        # 消息区域
        self._draw_messages(screen)
        
        # 输入框
        self._draw_input(screen)
    
    def _draw_header(self, screen):
        """绘制标题栏"""
        # NPC名字和情绪
        title_y = self.panel_y + 12
        
        # 情绪图标
        emotion_icon = self.EMOTION_ICONS.get(self.npc_emotion, "平")
        try:
            emotion_surf = self.font_emotion.render(emotion_icon, True, (255, 255, 255))
            screen.blit(emotion_surf, (self.panel_x + 15, title_y - 2))
        except:
            pass  # 某些系统可能不支持emoji
        
        # 名字
        name_surf = self.font_name.render(f"与 {self.npc_name} 对话", True, self.COLOR_NAME)
        screen.blit(name_surf, (self.panel_x + 50, title_y + 4))
        
        # 关闭按钮
        close_color = (200, 100, 100) if self._close_btn_rect.collidepoint(pygame.mouse.get_pos()) else (150, 150, 150)
        pygame.draw.rect(screen, close_color, self._close_btn_rect, border_radius=4)
        x_surf = self.font.render("×", True, (255, 255, 255))
        screen.blit(x_surf, (self._close_btn_rect.centerx - x_surf.get_width()//2, 
                            self._close_btn_rect.centery - x_surf.get_height()//2))
        
        # 分隔线
        pygame.draw.line(screen, (80, 80, 100),
                        (self.panel_x + 10, self.panel_y + 45),
                        (self.panel_x + self.panel_w - 10, self.panel_y + 45), 1)
    
    def _draw_messages(self, screen):
        """绘制消息列表"""
        # 消息区域裁剪
        msg_area = pygame.Rect(
            self.panel_x + 10,
            self.panel_y + 50,
            self.panel_w - 20,
            self.msg_area_h
        )
        
        # 计算所有消息的总高度
        total_height = 0
        msg_heights = []
        for msg in self.messages:
            h = self._calculate_message_height(msg)
            msg_heights.append(h)
            total_height += h + 10  # 间距
        
        self.max_scroll = max(0, total_height - self.msg_area_h)
        
        # 【关键修复】钳制scroll_offset到有效范围，防止消息画到屏幕外
        if self.scroll_offset > self.max_scroll:
            self.scroll_offset = self.max_scroll
        
        # 绘制消息
        y = msg_area.y - self.scroll_offset
        
        for i, msg in enumerate(self.messages):
            h = msg_heights[i]
            
            # 只绘制可见的消息
            if y + h > msg_area.y and y < msg_area.bottom:
                self._draw_message(screen, msg, msg_area.x, y, msg_area.width)
            
            y += h + 10
    
    def _calculate_message_height(self, msg: DisplayMessage) -> int:
        """计算消息高度"""
        # 简化计算，假设每行20像素
        content = msg.content[:int(len(msg.content) * msg.display_progress)]
        lines = self._wrap_text(content, self.panel_w - 80)
        return max(50, len(lines) * 22 + 20)
    
    def _draw_message(self, screen, msg: DisplayMessage, x: int, y: int, max_width: int):
        """绘制单条消息"""
        is_player = msg.role == "player"
        
        # 气泡颜色
        if msg.role == "system":
            bg_color = self.COLOR_SYSTEM_MSG
        elif is_player:
            bg_color = self.COLOR_PLAYER_MSG
        else:
            bg_color = self.COLOR_NPC_MSG
        
        # 计算文本内容
        content = msg.content[:int(len(msg.content) * msg.display_progress)]
        lines = self._wrap_text(content, max_width - 60)
        
        # 气泡尺寸
        bubble_w = min(max_width - 40, max(100, max(self.font.size(l)[0] for l in lines) + 20))
        bubble_h = len(lines) * 22 + 16
        
        # 气泡位置（玩家在右，NPC在左）
        if is_player:
            bubble_x = x + max_width - bubble_w - 10
        else:
            bubble_x = x + 10
        
        # 绘制气泡
        bubble_rect = pygame.Rect(bubble_x, y, bubble_w, bubble_h)
        pygame.draw.rect(screen, bg_color, bubble_rect, border_radius=8)
        
        # 绘制文本
        text_y = y + 8
        for line in lines:
            text_surf = self.font.render(line, True, self.COLOR_TEXT)
            screen.blit(text_surf, (bubble_x + 10, text_y))
            text_y += 22
        
        # 绘制动作（如果有）
        if msg.action and not is_player:
            action_text = f"*{msg.action}*"
            action_surf = self.font_hint.render(action_text, True, self.COLOR_ACTION)
            screen.blit(action_surf, (bubble_x + 10, y + bubble_h + 2))
    
    def _draw_input(self, screen):
        """绘制输入框"""
        # 输入框背景
        border_color = self.COLOR_INPUT_ACTIVE if self.input_active else self.COLOR_INPUT_BORDER
        pygame.draw.rect(screen, self.COLOR_INPUT_BG, self._input_rect, border_radius=6)
        pygame.draw.rect(screen, border_color, self._input_rect, 2, border_radius=6)
        
        # 输入文本
        display_text = self.input_text
        if len(display_text) > 30:
            display_text = "..." + display_text[-27:]
        
        text_surf = self.font_input.render(display_text, True, self.COLOR_TEXT)
        screen.blit(text_surf, (self._input_rect.x + 10, self._input_rect.y + 10))
        
        # 光标
        if self.input_active and self.cursor_visible:
            cursor_x = self._input_rect.x + 10 + text_surf.get_width() + 2
            pygame.draw.line(screen, (200, 200, 200),
                           (cursor_x, self._input_rect.y + 8),
                           (cursor_x, self._input_rect.y + self.input_h - 8), 2)
        
        # 占位符
        if not self.input_text and not self.input_active:
            placeholder = self.font_hint.render("输入消息...", True, (120, 120, 140))
            screen.blit(placeholder, (self._input_rect.x + 10, self._input_rect.y + 14))
        
        # 发送按钮
        btn_hover = self._send_btn_rect.collidepoint(pygame.mouse.get_pos())
        btn_color = (80, 130, 180) if btn_hover else (60, 100, 150)
        pygame.draw.rect(screen, btn_color, self._send_btn_rect, border_radius=6)
        
        send_text = self.font.render("发送", True, (255, 255, 255))
        screen.blit(send_text, (self._send_btn_rect.centerx - send_text.get_width()//2,
                               self._send_btn_rect.centery - send_text.get_height()//2))
    
    def _wrap_text(self, text: str, max_width: int) -> List[str]:
        """文本自动换行"""
        words = list(text)
        lines = []
        current_line = ""
        
        for char in words:
            test_line = current_line + char
            if self.font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char
        
        if current_line:
            lines.append(current_line)
        
        return lines if lines else [""]
    
    def _scroll_to_bottom(self):
        """滚动到底部"""
        # 下一帧再计算，因为消息刚添加
        self.scroll_offset = 999999  # 临时设置一个大值，update时会修正
