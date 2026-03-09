# src/ui/settings_panel.py
"""
系统设置面板 - 配置API密钥和游戏参数
支持：
- LLM API（文本生成）- 可配置任意模型
- 图像生成 API - 可配置任意模型
- 导演系统参数
"""

import pygame
from typing import Optional, Callable, Tuple, Dict

class SettingsPanel:
    """系统设置面板 - 支持自定义LLM和图像生成配置"""
    
    # 输入框配置: (标签, 键名, 提示文本, 宽度)
    LLM_INPUTS = [
        ("模型名称", "llm_model", "例如: deepseek-chat", 280),
        ("Base URL", "llm_base_url", "例如: https://api.deepseek.com", 400),
        ("API Key", "llm_api_key", "输入 API Key (sk-xxx...)", 400),
    ]
    
    IMAGE_INPUTS = [
        ("模型名称", "image_model", "例如: doubao-seedream-5-0-260128", 320),
        ("Base URL", "image_base_url", "例如: https://ark.cn-beijing.volces.com/api/v3", 400),
        ("API Key", "image_api_key", "输入 API Key", 400),
    ]
    
    def __init__(self, screen_w: int, screen_h: int):
        self.screen_w = screen_w
        self.screen_h = screen_h
        
        # 面板尺寸 - 增加高度以容纳更多输入框
        self.panel_w = 800
        self.panel_h = 700
        self.panel_x = (screen_w - self.panel_w) // 2
        self.panel_y = (screen_h - self.panel_h) // 2
        
        # 字体
        font_names = "microsoftyahei,simhei,pingfangsc,notosanscjk,arial"
        self.font_title = pygame.font.SysFont(font_names, 28, bold=True)
        self.font_section = pygame.font.SysFont(font_names, 22, bold=True)
        self.font_label = pygame.font.SysFont(font_names, 16)
        self.font_input = pygame.font.SysFont(font_names, 14)
        self.font_hint = pygame.font.SysFont(font_names, 13)
        
        # 颜色
        self.bg_color = (25, 25, 35)
        self.border_color = (80, 80, 100)
        self.text_color = (220, 220, 220)
        self.hint_color = (150, 150, 160)
        self.input_bg = (40, 40, 50)
        self.input_active_bg = (50, 50, 65)
        self.btn_normal = (60, 60, 80)
        self.btn_hover = (80, 100, 140)
        self.btn_success = (40, 120, 80)
        self.btn_danger = (140, 60, 60)
        self.btn_active = (60, 140, 60)
        self.status_ok = (80, 200, 120)
        self.status_warn = (200, 150, 80)
        self.status_off = (150, 80, 80)
        
        # 输入框状态 - 存储临时输入值
        self.active_input: Optional[str] = None
        self.input_values: Dict[str, str] = {
            "llm_model": "",
            "llm_base_url": "",
            "llm_api_key": "",
            "image_model": "",
            "image_base_url": "",
            "image_api_key": "",
        }
        self.input_cursor_visible = True
        self.cursor_timer = 0
        
        # 消息提示
        self.message = ""
        self.message_color = self.text_color
        self.message_timer = 0
        
        # 回调
        self.on_close: Optional[Callable] = None
        
        # 初始化时从配置加载值
        self._load_values_from_config()
        
    def show_message(self, text: str, is_error: bool = False):
        """显示提示消息"""
        self.message = text
        self.message_color = self.status_off if is_error else self.status_ok
        self.message_timer = 3000
        
    def _get_config(self):
        """获取配置管理器"""
        from src.llm.config import LLMConfig
        return LLMConfig.get_instance()
    
    def _mask_key(self, key: str) -> str:
        """遮蔽API Key中间部分"""
        if not key:
            return ""
        if len(key) <= 10:
            return "*" * len(key)
        return key[:6] + "*" * (len(key) - 10) + key[-4:]
    
    def _load_values_from_config(self):
        """从配置加载当前值到输入框"""
        config = self._get_config()
        self.input_values["llm_model"] = config.model or ""
        self.input_values["llm_base_url"] = config.api_base or ""
        self.input_values["llm_api_key"] = ""
        self.input_values["image_model"] = config.doubao_model or ""
        self.input_values["image_base_url"] = config.doubao_api_base or ""
        self.input_values["image_api_key"] = ""
    
    def _save_all_settings(self):
        """保存所有设置"""
        config = self._get_config()
        
        # 保存LLM设置
        if self.input_values["llm_model"]:
            config.model = self.input_values["llm_model"]
        if self.input_values["llm_base_url"]:
            config.api_base = self.input_values["llm_base_url"]
        if self.input_values["llm_api_key"]:
            config.api_key = self.input_values["llm_api_key"]
            self.input_values["llm_api_key"] = ""
        
        # 保存图像生成设置
        if self.input_values["image_model"]:
            config.doubao_model = self.input_values["image_model"]
        if self.input_values["image_base_url"]:
            config.doubao_api_base = self.input_values["image_base_url"]
        if self.input_values["image_api_key"]:
            config.doubao_api_key = self.input_values["image_api_key"]
            self.input_values["image_api_key"] = ""
        
        self.show_message("设置已保存！")
    
    def _clear_llm_settings(self):
        """清除LLM设置"""
        config = self._get_config()
        config.api_key = ""
        config.api_base = ""
        config.model = ""
        self.input_values["llm_model"] = ""
        self.input_values["llm_base_url"] = ""
        self.input_values["llm_api_key"] = ""
        self.show_message("LLM设置已清除")
    
    def _clear_image_settings(self):
        """清除图像生成设置"""
        config = self._get_config()
        config.doubao_api_key = ""
        config.doubao_api_base = ""
        config.doubao_model = ""
        self.input_values["image_model"] = ""
        self.input_values["image_base_url"] = ""
        self.input_values["image_api_key"] = ""
        self.show_message("图像生成设置已清除")
    
    def _get_input_rect(self, y_offset: int, width: int) -> pygame.Rect:
        """获取输入框区域"""
        return pygame.Rect(self.panel_x + 200, y_offset, width, 32)
    
    def handle_event(self, event: pygame.event.Event) -> bool:
        """处理事件"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            
            panel_rect = pygame.Rect(self.panel_x, self.panel_y, self.panel_w, self.panel_h)
            if not panel_rect.collidepoint(mx, my):
                if self.on_close:
                    self.on_close()
                return True
            
            close_rect = pygame.Rect(self.panel_x + self.panel_w - 40, self.panel_y + 10, 30, 30)
            if close_rect.collidepoint(mx, my):
                if self.on_close:
                    self.on_close()
                return True
            
            # 检查输入框点击 - 必须与draw方法中的y_offset计算一致
            # LLM区域: panel_y + 65(标题) + 35(状态) = panel_y + 100
            y_offset = self.panel_y + 100
            
            # LLM输入框
            for label, key, hint, width in self.LLM_INPUTS:
                input_rect = self._get_input_rect(y_offset, width)
                if input_rect.collidepoint(mx, my):
                    self.active_input = key
                    return True
                y_offset += 45
            
            # 图像生成区域: LLM结束 + 按钮(50) + 分隔(15) + 标题(35) = y_offset + 100
            y_offset += 100  # 按钮区域(50) + 分隔(15) + 标题(35)
            
            # 图像生成输入框
            for label, key, hint, width in self.IMAGE_INPUTS:
                input_rect = self._get_input_rect(y_offset, width)
                if input_rect.collidepoint(mx, my):
                    self.active_input = key
                    return True
                y_offset += 45
            
            self.active_input = None
            
            # 处理按钮点击
            if self._handle_button_clicks(mx, my):
                return True
            
            return True
            
        elif event.type == pygame.KEYDOWN:
            if self.active_input:
                if event.key == pygame.K_BACKSPACE:
                    self.input_values[self.active_input] = self.input_values[self.active_input][:-1]
                elif event.key == pygame.K_RETURN:
                    self.active_input = None
                elif event.key == pygame.K_ESCAPE:
                    self.active_input = None
                elif event.key == pygame.K_TAB:
                    all_inputs = [k for _, k, _, _ in self.LLM_INPUTS + self.IMAGE_INPUTS]
                    if self.active_input in all_inputs:
                        idx = all_inputs.index(self.active_input)
                        self.active_input = all_inputs[(idx + 1) % len(all_inputs)]
                elif event.key == pygame.K_v and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    # 使用 pygame.scrap 实现跨平台粘贴（支持PyInstaller打包）
                    try:
                        import pygame.scrap
                        pygame.scrap.init()
                        clipboard = pygame.scrap.get(pygame.SCRAP_TEXT)
                        if clipboard:
                            text = clipboard.decode('utf-8', errors='ignore').strip('\x00')
                            self.input_values[self.active_input] += text
                    except Exception:
                        pass
                else:
                    if event.unicode and event.unicode.isprintable():
                        self.input_values[self.active_input] += event.unicode
                return True
        
        return False
    
    def _get_button_positions(self) -> dict:
        """计算所有按钮的位置 - 与draw方法保持一致"""
        # LLM区域起始
        y_offset = self.panel_y + 100  # 65(标题) + 35(状态)
        
        # LLM输入框 (3个，每个45像素)
        y_offset += len(self.LLM_INPUTS) * 45
        
        # LLM按钮
        llm_btn_y = y_offset + 5
        
        # 图像生成区域
        y_offset = llm_btn_y + 50  # 分隔线
        y_offset += 15  # 间距
        y_offset += 35  # 标题和状态
        
        # 图像生成输入框 (3个，每个45像素)
        y_offset += len(self.IMAGE_INPUTS) * 45
        
        # 图像生成按钮
        image_btn_y = y_offset + 5
        
        return {
            "llm_save": pygame.Rect(self.panel_x + 200, llm_btn_y, 80, 30),
            "llm_clear": pygame.Rect(self.panel_x + 290, llm_btn_y, 80, 30),
            "image_save": pygame.Rect(self.panel_x + 200, image_btn_y, 80, 30),
            "image_clear": pygame.Rect(self.panel_x + 290, image_btn_y, 80, 30),
        }
    
    def _handle_button_clicks(self, mx: int, my: int) -> bool:
        """处理按钮点击"""
        buttons = self._get_button_positions()
        
        if buttons["llm_save"].collidepoint(mx, my):
            self._save_llm_settings()
            return True
        
        if buttons["llm_clear"].collidepoint(mx, my):
            self._clear_llm_settings()
            return True
        
        if buttons["image_save"].collidepoint(mx, my):
            self._save_image_settings()
            return True
        
        if buttons["image_clear"].collidepoint(mx, my):
            self._clear_image_settings()
            return True
        
        return False
    
    def _save_llm_settings(self):
        """保存LLM设置"""
        config = self._get_config()
        saved = []
        
        if self.input_values["llm_model"]:
            config.model = self.input_values["llm_model"]
            saved.append("模型")
        if self.input_values["llm_base_url"]:
            config.api_base = self.input_values["llm_base_url"]
            saved.append("Base URL")
        if self.input_values["llm_api_key"]:
            config.api_key = self.input_values["llm_api_key"]
            self.input_values["llm_api_key"] = ""
            saved.append("API Key")
        
        if saved:
            self.show_message(f"LLM {', '.join(saved)} 已保存！")
        else:
            self.show_message("没有要保存的LLM设置", is_error=True)
    
    def _save_image_settings(self):
        """保存图像生成设置"""
        config = self._get_config()
        saved = []
        
        if self.input_values["image_model"]:
            config.doubao_model = self.input_values["image_model"]
            saved.append("模型")
        if self.input_values["image_base_url"]:
            config.doubao_api_base = self.input_values["image_base_url"]
            saved.append("Base URL")
        if self.input_values["image_api_key"]:
            config.doubao_api_key = self.input_values["image_api_key"]
            self.input_values["image_api_key"] = ""
            saved.append("API Key")
        
        if saved:
            self.show_message(f"图像生成 {', '.join(saved)} 已保存！")
        else:
            self.show_message("没有要保存的图像生成设置", is_error=True)
    
    def update(self, dt_ms: int):
        """更新动画"""
        self.cursor_timer += dt_ms
        if self.cursor_timer >= 500:
            self.cursor_timer = 0
            self.input_cursor_visible = not self.input_cursor_visible
        
        if self.message_timer > 0:
            self.message_timer -= dt_ms
            if self.message_timer <= 0:
                self.message = ""
    
    def draw(self, screen: pygame.Surface):
        """绘制设置面板"""
        config = self._get_config()
        mx, my = pygame.mouse.get_pos()
        
        # 背景遮罩
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        
        # 面板背景
        panel_rect = pygame.Rect(self.panel_x, self.panel_y, self.panel_w, self.panel_h)
        pygame.draw.rect(screen, self.bg_color, panel_rect, border_radius=10)
        pygame.draw.rect(screen, self.border_color, panel_rect, 2, border_radius=10)
        
        # 标题
        title = self.font_title.render("[设置] AI 模型配置", True, self.text_color)
        screen.blit(title, (self.panel_x + 30, self.panel_y + 15))
        
        # 关闭按钮
        close_rect = pygame.Rect(self.panel_x + self.panel_w - 40, self.panel_y + 10, 30, 30)
        close_hover = close_rect.collidepoint(mx, my)
        pygame.draw.rect(screen, self.btn_danger if close_hover else self.btn_normal, 
                        close_rect, border_radius=5)
        close_text = self.font_label.render("×", True, self.text_color)
        screen.blit(close_text, (close_rect.centerx - close_text.get_width()//2, 
                                close_rect.centery - close_text.get_height()//2))
        
        # ========== LLM 配置区域 ==========
        y_offset = self.panel_y + 65
        
        # 区域标题
        section_title = self.font_section.render("🤖 LLM 文本生成设置", True, (100, 180, 255))
        screen.blit(section_title, (self.panel_x + 30, y_offset))
        
        # 状态指示
        status = config.get_ai_status()
        llm_ready = status["llm"]["ready"]
        status_text = "✓ 已配置" if llm_ready else "✗ 未配置"
        status_color = self.status_ok if llm_ready else self.status_off
        status_surf = self.font_label.render(status_text, True, status_color)
        screen.blit(status_surf, (self.panel_x + self.panel_w - 120, y_offset + 3))
        
        y_offset += 35
        
        # LLM输入框
        for label, key, hint, width in self.LLM_INPUTS:
            # 标签
            label_surf = self.font_label.render(label + ":", True, self.text_color)
            screen.blit(label_surf, (self.panel_x + 40, y_offset + 6))
            
            # 输入框
            input_rect = self._get_input_rect(y_offset, width)
            is_active = self.active_input == key
            pygame.draw.rect(screen, self.input_active_bg if is_active else self.input_bg, 
                            input_rect, border_radius=4)
            pygame.draw.rect(screen, (100, 150, 200) if is_active else self.border_color, 
                            input_rect, 2 if is_active else 1, border_radius=4)
            
            # 输入内容或提示
            display_value = self.input_values.get(key, "")
            # API Key显示脱敏版本
            if "api_key" in key and display_value:
                display_value = self._mask_key(display_value)
            
            if display_value:
                text_surf = self.font_input.render(display_value, True, self.text_color)
            else:
                # 显示当前配置值（非输入值）
                current_val = ""
                if key == "llm_model":
                    current_val = config.model
                elif key == "llm_base_url":
                    current_val = config.api_base
                elif key == "llm_api_key" and config.api_key:
                    current_val = self._mask_key(config.api_key)
                
                if current_val:
                    text_surf = self.font_input.render(current_val, True, self.hint_color)
                else:
                    text_surf = self.font_input.render(hint, True, self.hint_color)
            
            screen.blit(text_surf, (input_rect.x + 8, input_rect.centery - text_surf.get_height()//2))
            
            # 光标
            if is_active and self.input_cursor_visible:
                cursor_x = input_rect.x + 8 + self.font_input.size(self.input_values.get(key, ""))[0]
                pygame.draw.line(screen, self.text_color, (cursor_x, input_rect.y + 6), 
                                (cursor_x, input_rect.y + 26), 2)
            
            y_offset += 45
        
        # LLM按钮
        llm_btn_y = y_offset + 5
        llm_save_rect = pygame.Rect(self.panel_x + 200, llm_btn_y, 80, 30)
        llm_clear_rect = pygame.Rect(self.panel_x + 290, llm_btn_y, 80, 30)
        self._draw_button(screen, llm_save_rect, "保存", mx, my, self.btn_success)
        self._draw_button(screen, llm_clear_rect, "清除", mx, my, self.btn_danger)
        
        # ========== 分隔线 ==========
        y_offset = llm_btn_y + 50
        pygame.draw.line(screen, self.border_color, 
                        (self.panel_x + 30, y_offset), 
                        (self.panel_x + self.panel_w - 30, y_offset), 1)
        
        # ========== 图像生成配置区域 ==========
        y_offset += 15
        
        # 区域标题
        section_title2 = self.font_section.render("🎨 图像生成设置", True, (255, 180, 100))
        screen.blit(section_title2, (self.panel_x + 30, y_offset))
        
        # 状态指示
        image_ready = status["image"]["ready"]
        status_text2 = "✓ 已配置" if image_ready else "✗ 未配置"
        status_color2 = self.status_ok if image_ready else self.status_off
        status_surf2 = self.font_label.render(status_text2, True, status_color2)
        screen.blit(status_surf2, (self.panel_x + self.panel_w - 120, y_offset + 3))
        
        y_offset += 35
        
        # 图像生成输入框
        for label, key, hint, width in self.IMAGE_INPUTS:
            # 标签
            label_surf = self.font_label.render(label + ":", True, self.text_color)
            screen.blit(label_surf, (self.panel_x + 40, y_offset + 6))
            
            # 输入框
            input_rect = self._get_input_rect(y_offset, width)
            is_active = self.active_input == key
            pygame.draw.rect(screen, self.input_active_bg if is_active else self.input_bg, 
                            input_rect, border_radius=4)
            pygame.draw.rect(screen, (100, 150, 200) if is_active else self.border_color, 
                            input_rect, 2 if is_active else 1, border_radius=4)
            
            # 输入内容或提示
            display_value = self.input_values.get(key, "")
            if "api_key" in key and display_value:
                display_value = self._mask_key(display_value)
            
            if display_value:
                text_surf = self.font_input.render(display_value, True, self.text_color)
            else:
                # 显示当前配置值
                current_val = ""
                if key == "image_model":
                    current_val = config.doubao_model
                elif key == "image_base_url":
                    current_val = config.doubao_api_base
                elif key == "image_api_key" and config.doubao_api_key:
                    current_val = self._mask_key(config.doubao_api_key)
                
                if current_val:
                    text_surf = self.font_input.render(current_val, True, self.hint_color)
                else:
                    text_surf = self.font_input.render(hint, True, self.hint_color)
            
            screen.blit(text_surf, (input_rect.x + 8, input_rect.centery - text_surf.get_height()//2))
            
            # 光标
            if is_active and self.input_cursor_visible:
                cursor_x = input_rect.x + 8 + self.font_input.size(self.input_values.get(key, ""))[0]
                pygame.draw.line(screen, self.text_color, (cursor_x, input_rect.y + 6), 
                                (cursor_x, input_rect.y + 26), 2)
            
            y_offset += 45
        
        # 图像生成按钮
        image_btn_y = y_offset + 5
        image_save_rect = pygame.Rect(self.panel_x + 200, image_btn_y, 80, 30)
        image_clear_rect = pygame.Rect(self.panel_x + 290, image_btn_y, 80, 30)
        self._draw_button(screen, image_save_rect, "保存", mx, my, self.btn_success)
        self._draw_button(screen, image_clear_rect, "清除", mx, my, self.btn_danger)
        
        # ========== 整体状态提示 ==========
        y_offset = image_btn_y + 50
        pygame.draw.line(screen, self.border_color, 
                        (self.panel_x + 30, y_offset), 
                        (self.panel_x + self.panel_w - 30, y_offset), 1)
        
        y_offset += 15
        
        # AI就绪状态
        ai_ready = status["ready"]
        ready_text = "✓ AI 配置完成，可以开始游戏" if ai_ready else "✗ 请先完成上方 AI 配置"
        ready_color = self.status_ok if ai_ready else self.status_warn
        ready_surf = self.font_label.render(ready_text, True, ready_color)
        screen.blit(ready_surf, (self.panel_x + 30, y_offset))
        
        # 消息提示
        if self.message:
            msg_surf = self.font_label.render(self.message, True, self.message_color)
            msg_x = self.panel_x + (self.panel_w - msg_surf.get_width()) // 2
            msg_y = self.panel_y + self.panel_h - 35
            screen.blit(msg_surf, (msg_x, msg_y))
    
    def _draw_button(self, screen: pygame.Surface, rect: pygame.Rect, text: str, 
                     mx: int, my: int, base_color: Tuple[int, int, int]):
        """绘制按钮"""
        hover = rect.collidepoint(mx, my)
        color = tuple(min(c + 30, 255) for c in base_color) if hover else base_color
        pygame.draw.rect(screen, color, rect, border_radius=4)
        pygame.draw.rect(screen, self.border_color, rect, 1, border_radius=4)
        
        text_surf = self.font_hint.render(text, True, self.text_color)
        screen.blit(text_surf, (rect.centerx - text_surf.get_width()//2, 
                               rect.centery - text_surf.get_height()//2))


_settings_panel: Optional[SettingsPanel] = None

def get_settings_panel(screen_w: int = 0, screen_h: int = 0) -> SettingsPanel:
    """获取设置面板单例"""
    global _settings_panel
    if _settings_panel is None:
        if screen_w == 0 or screen_h == 0:
            raise ValueError("首次调用需要提供 screen_w 和 screen_h")
        _settings_panel = SettingsPanel(screen_w, screen_h)
    return _settings_panel