# --- src/ui/main_menu.py ---
import pygame
import sys
from src.definitions import *
from src.utils import load_image
from src.ui.settings_panel import SettingsPanel
from src.llm.config import LLMConfig

class MainMenuUI:
    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        
        # 系统设置面板
        self.settings_panel = SettingsPanel(screen_w, screen_h)
        self.settings_panel.on_close = lambda: setattr(self, 'show_settings', False)
        self.show_settings = False
        
        # 提示弹窗
        self.show_alert = False
        self.alert_message = ""
        self.alert_timer = 0
        
        # 字体初始化 (复用 Base UI 的逻辑)
        font_names = "microsoftyahei,simhei,pingfangsc,notosanscjk,arial"
        self.font_title = pygame.font.SysFont(font_names, 60, bold=True)
        self.font_btn = pygame.font.SysFont(font_names, 28)
        self.font_desc = pygame.font.SysFont(font_names, 18)
        self.font_alert = pygame.font.SysFont(font_names, 20)
        self.font_alert_title = pygame.font.SysFont(font_names, 24, bold=True)
        
        # 加载背景
        self.bg_img = load_image("assets/story/mainmenu.png", (screen_w, screen_h))
        
        # 状态: 0=主菜单, 1=剧本选择
        self.menu_state = 0
        self.selected_scenario = None # 'TUTORIAL' or 'SANDBOX'
        
        # 布局参数
        self.sidebar_w = screen_w // 3
        self.btn_w = 220
        self.btn_h = 60
        self.btn_gap = 30
        self.start_y = screen_h // 2 - 100
    
    def _check_ai_config(self) -> bool:
        """检查AI是否已配置"""
        config = LLMConfig.get_instance()
        return config.is_ai_ready()
    
    def _show_alert(self, message: str):
        """显示提示弹窗"""
        self.show_alert = True
        self.alert_message = message
        self.alert_timer = 4000  # 4秒后自动关闭
    
    def _draw_alert(self, screen: pygame.Surface, mx: int, my: int):
        """绘制提示弹窗"""
        if not self.show_alert:
            return
        
        # 弹窗尺寸
        alert_w = 500
        alert_h = 200
        alert_x = (self.screen_w - alert_w) // 2
        alert_y = (self.screen_h - alert_h) // 2
        
        # 背景遮罩
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))
        
        # 弹窗背景
        alert_rect = pygame.Rect(alert_x, alert_y, alert_w, alert_h)
        pygame.draw.rect(screen, (35, 35, 45), alert_rect, border_radius=12)
        pygame.draw.rect(screen, (200, 150, 80), alert_rect, 3, border_radius=12)
        
        # 标题
        title = self.font_alert_title.render("⚠️ AI 配置提示", True, (255, 200, 100))
        screen.blit(title, (alert_x + (alert_w - title.get_width()) // 2, alert_y + 25))
        
        # 消息内容（支持多行）
        lines = self.alert_message.split('\n')
        line_y = alert_y + 70
        for line in lines:
            text = self.font_alert.render(line, True, (220, 220, 220))
            screen.blit(text, (alert_x + (alert_w - text.get_width()) // 2, line_y))
            line_y += 28
        
        # 确定按钮
        btn_w, btn_h = 100, 40
        btn_x = alert_x + (alert_w - btn_w) // 2
        btn_y = alert_y + alert_h - 60
        btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        
        hover = btn_rect.collidepoint(mx, my)
        btn_color = (100, 150, 200) if hover else (80, 120, 160)
        pygame.draw.rect(screen, btn_color, btn_rect, border_radius=6)
        pygame.draw.rect(screen, (150, 180, 220), btn_rect, 2, border_radius=6)
        
        btn_text = self.font_alert.render("确定", True, (255, 255, 255))
        screen.blit(btn_text, (btn_rect.centerx - btn_text.get_width()//2, 
                              btn_rect.centery - btn_text.get_height()//2))
        
        return btn_rect

    def draw_button(self, screen, text, y_pos, mx, my, disabled=False, callback=None):
        """绘制单个菜单按钮"""
        x_pos = (self.sidebar_w - self.btn_w) // 2
        rect = pygame.Rect(x_pos, y_pos, self.btn_w, self.btn_h)
        
        is_hover = rect.collidepoint(mx, my) and not disabled
        
        # 颜色样式
        if disabled:
            bg_col = (50, 50, 50, 200)
            txt_col = (100, 100, 100)
            border_col = (80, 80, 80)
        elif is_hover:
            bg_col = (180, 50, 50, 230) # 红色高亮
            txt_col = (255, 255, 255)
            border_col = (255, 215, 0)
        else:
            bg_col = (30, 30, 40, 200)
            txt_col = (200, 200, 200)
            border_col = (100, 100, 100)
            
        # 绘制半透明背景
        s = pygame.Surface((self.btn_w, self.btn_h), pygame.SRCALPHA)
        pygame.draw.rect(s, bg_col, s.get_rect(), border_radius=5)
        screen.blit(s, (x_pos, y_pos))
        
        # 边框
        pygame.draw.rect(screen, border_col, rect, 2, border_radius=5)
        
        # 文字
        txt_surf = self.font_btn.render(text, True, txt_col)
        screen.blit(txt_surf, (rect.centerx - txt_surf.get_width()//2, rect.centery - txt_surf.get_height()//2))
        
        return is_hover, rect

    def run(self, screen, clock):
        """运行主菜单循环，返回选择的剧本ID，或者退出"""
        running = True
        dt = 0  # delta time for settings panel animation
        while running:
            dt = clock.tick(60)
            mx, my = pygame.mouse.get_pos()
            click = False
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                # 如果提示弹窗显示，优先处理弹窗事件
                if self.show_alert:
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        # 点击任意位置关闭弹窗
                        self.show_alert = False
                        continue
                
                # 如果设置面板打开，优先处理设置面板事件
                if self.show_settings:
                    if self.settings_panel.handle_event(event):
                        continue  # 事件被设置面板消费
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    click = True
            
            # 更新设置面板动画
            if self.show_settings:
                self.settings_panel.update(dt)
            
            # 更新提示弹窗计时器
            if self.alert_timer > 0:
                self.alert_timer -= dt
                if self.alert_timer <= 0:
                    self.show_alert = False
                    
            # --- 绘制 ---
            # 1. 背景图
            screen.blit(self.bg_img, (0, 0))
            
            # 2. 左侧边栏蒙版
            overlay = pygame.Surface((self.sidebar_w, self.screen_h), pygame.SRCALPHA)
            overlay.fill((10, 10, 15, 220)) # 深色半透明
            screen.blit(overlay, (0, 0))
            pygame.draw.line(screen, (100, 100, 100), (self.sidebar_w, 0), (self.sidebar_w, self.screen_h), 2)
            
            # 3. 标题
            title_surf = self.font_title.render("堆叠江湖", True, (255, 215, 0))
            screen.blit(title_surf, (self.sidebar_w//2 - title_surf.get_width()//2, 100))
            
            # 4. 菜单逻辑
            current_y = self.start_y
            
            # 检查AI配置状态
            ai_ready = self._check_ai_config()
            
            if self.menu_state == 0: # 主层级
                # 按钮定义 - 选择剧本在未配置AI时禁用
                buttons = [
                    ("选择剧本", ai_ready),  # 根据AI配置状态启用/禁用
                    ("载入存档", False),
                    ("系统设置", True),  # 始终启用
                    ("退出游戏", True)
                ]
                
                for text, enabled in buttons:
                    hover, rect = self.draw_button(screen, text, current_y, mx, my, disabled=not enabled)
                    if click and hover:
                        if text == "选择剧本":
                            if ai_ready:
                                self.menu_state = 1 # 进入剧本选择
                            else:
                                # 显示配置提示
                                config = LLMConfig.get_instance()
                                status = config.get_ai_status()
                                missing = []
                                if not status["llm"]["api_key"]:
                                    missing.append("LLM API Key")
                                if not status["llm"]["base_url"]:
                                    missing.append("LLM Base URL")
                                if not status["llm"]["model"]:
                                    missing.append("LLM 模型名称")
                                if not status["image"]["api_key"]:
                                    missing.append("图像生成 API Key")
                                if not status["image"]["base_url"]:
                                    missing.append("图像生成 Base URL")
                                if not status["image"]["model"]:
                                    missing.append("图像生成 模型名称")
                                
                                msg = "请先完成 AI 配置:\n" + "\n".join([f"• {m}" for m in missing[:4]])
                                if len(missing) > 4:
                                    msg += f"\n...还有 {len(missing) - 4} 项"
                                self._show_alert(msg)
                        elif text == "系统设置":
                            self.show_settings = True  # 打开设置面板
                        elif text == "退出游戏":
                            pygame.quit()
                            sys.exit()
                    current_y += self.btn_h + self.btn_gap
                    
            elif self.menu_state == 1: # 剧本选择层级
                # 返回按钮 (小一点)
                back_rect = pygame.Rect(20, 20, 80, 40)
                back_hover = back_rect.collidepoint(mx, my)
                pygame.draw.rect(screen, (150, 50, 50) if back_hover else (100, 50, 50), back_rect, border_radius=5)
                back_txt = self.font_btn.render("<<", True, (255, 255, 255))
                screen.blit(back_txt, (back_rect.centerx - back_txt.get_width()//2, back_rect.centery - back_txt.get_height()//2))
                if click and back_hover:
                    self.menu_state = 0
                
                # 剧本 1
                hover1, _ = self.draw_button(screen, "乱世荒村 (新手)", current_y, mx, my)
                # 描述
                d1 = self.font_desc.render("从零开始，在废墟中重建家园。", True, (150, 150, 150))
                screen.blit(d1, (self.sidebar_w//2 - d1.get_width()//2, current_y + 65))
                
                if click and hover1:
                    return "SCENARIO_TUTORIAL"
                
                current_y += 110
                
                # 剧本 2
                hover2, _ = self.draw_button(screen, "闯荡汴京 (沙盒)", current_y, mx, my)
                # 描述
                d2 = self.font_desc.render("初始人口与资源较多，自由探索。", True, (150, 150, 150))
                screen.blit(d2, (self.sidebar_w//2 - d2.get_width()//2, current_y + 65))
                
                if click and hover2:
                    return "SCENARIO_SANDBOX"

            # 5. 绘制设置面板（最顶层）
            if self.show_settings:
                self.settings_panel.draw(screen)
            
            # 6. 绘制提示弹窗（最顶层）
            if self.show_alert:
                self._draw_alert(screen, mx, my)

            pygame.display.flip()
