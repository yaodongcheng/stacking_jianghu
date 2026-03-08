# --- src/ui/creation.py ---
import pygame
from src.definitions import *

class CharacterCreationUI:
    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        
        # 字体加载 (尝试加载更合适的中文字体，如果没有则回退)
        font_names = "microsoftyahei,simhei,pingfangsc,notosanscjk,arial"
        self.font_title = pygame.font.SysFont(font_names, 40, bold=True)
        self.font_label = pygame.font.SysFont(font_names, 22)
        self.font_input = pygame.font.SysFont(font_names, 20)
        self.font_btn = pygame.font.SysFont(font_names, 24, bold=True)
        
        # --- 数据状态 ---
        self.data = {
            'player_name': '',
            'player_gender': 'Male',
            'has_follower': False,
            'follower_name': '',
            'follower_gender': 'Male',
            'follower_desc': ''
        }
        
        # 当前激活的输入框 key
        self.active_key = None
        
        # --- UI 布局配置 ---
        self.panel_w = 900
        self.panel_h = 600
        self.x_base = (screen_w - self.panel_w) // 2
        self.y_base = (screen_h - self.panel_h) // 2
        
        # 定义输入框区域 (Rect)
        # 左栏：玩家
        left_center = self.x_base + self.panel_w // 4
        self.rects = {
            'player_name': pygame.Rect(left_center - 100, self.y_base + 180, 200, 40),
            'p_gender_m': pygame.Rect(left_center - 80, self.y_base + 260, 60, 30),
            'p_gender_f': pygame.Rect(left_center + 20, self.y_base + 260, 60, 30),
        }
        
        # 右栏：门客
        right_center = self.x_base + 3 * self.panel_w // 4
        self.rects.update({
            'toggle_follower': pygame.Rect(right_center - 120, self.y_base + 120, 240, 40),
            'follower_name': pygame.Rect(right_center - 100, self.y_base + 200, 200, 40),
            'f_gender_m': pygame.Rect(right_center - 80, self.y_base + 280, 60, 30),
            'f_gender_f': pygame.Rect(right_center + 20, self.y_base + 280, 60, 30),
            'follower_desc': pygame.Rect(right_center - 140, self.y_base + 360, 280, 40),
        })
        
        # 底部开始按钮
        self.btn_start = pygame.Rect((screen_w - 200)//2, self.y_base + self.panel_h - 100, 200, 60)
        
        # 完成标记
        self.is_finished = False

    def handle_input(self, event):
        """处理输入事件"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            
            # 1. 检查输入框聚焦
            self.active_key = None
            for key in ['player_name', 'follower_name', 'follower_desc']:
                if self.data['has_follower'] is False and key.startswith('follower'):
                    continue # 没启用门客时，无法聚焦右侧
                
                if self.rects[key].collidepoint(mx, my):
                    self.active_key = key
                    # 启用输入法支持 (Pygame 2)
                    pygame.key.start_text_input()
                    break
            
            # 2. 检查按钮点击
            # 性别切换
            if self.rects['p_gender_m'].collidepoint(mx, my): self.data['player_gender'] = 'Male'
            elif self.rects['p_gender_f'].collidepoint(mx, my): self.data['player_gender'] = 'Female'
            
            if self.data['has_follower']:
                if self.rects['f_gender_m'].collidepoint(mx, my): self.data['follower_gender'] = 'Male'
                elif self.rects['f_gender_f'].collidepoint(mx, my): self.data['follower_gender'] = 'Female'
            
            # 门客开关
            if self.rects['toggle_follower'].collidepoint(mx, my):
                self.data['has_follower'] = not self.data['has_follower']
                if not self.data['has_follower']:
                    self.active_key = None # 如果关闭了门客，清除焦点
            
            # 开始游戏
            if self.btn_start.collidepoint(mx, my):
                if self._validate():
                    self.is_finished = True

        # 3. 键盘输入处理 (兼容中文输入法)
        elif event.type == pygame.TEXTINPUT:
            if self.active_key:
                # 限制长度
                current_text = self.data[self.active_key]
                limit = 30 if self.active_key == 'follower_desc' else 8
                if len(current_text) < limit:
                    self.data[self.active_key] += event.text

        elif event.type == pygame.KEYDOWN:
            if self.active_key:
                if event.key == pygame.K_BACKSPACE:
                    self.data[self.active_key] = self.data[self.active_key][:-1]
                # 兼容旧版 Pygame 或英文直接输入
                elif not hasattr(pygame, 'TEXTINPUT'): 
                     if len(event.unicode) > 0 and event.unicode.isprintable():
                        current_text = self.data[self.active_key]
                        limit = 30 if self.active_key == 'follower_desc' else 8
                        if len(current_text) < limit:
                             self.data[self.active_key] += event.unicode

    def _validate(self):
        """简单校验"""
        if len(self.data['player_name'].strip()) == 0: return False
        if self.data['has_follower']:
            if len(self.data['follower_name'].strip()) == 0: return False
        return True

    def update(self):
        pass

    def draw(self, screen, mx, my, click_event):
        # 1. 绘制背景 (全屏深色 + 卷轴面板)
        screen.fill((20, 20, 25))
        
        # 面板底色
        panel_rect = pygame.Rect(self.x_base, self.y_base, self.panel_w, self.panel_h)
        pygame.draw.rect(screen, (40, 40, 45), panel_rect, border_radius=15)
        pygame.draw.rect(screen, (80, 80, 80), panel_rect, 2, border_radius=15)
        
        # 标题
        title = self.font_title.render("欢迎来到堆叠江湖！请校核您和同行人信息", True, (255, 215, 0))
        screen.blit(title, (self.screen_w//2 - title.get_width()//2, self.y_base + 30))

        # 中轴线
        line_x = self.x_base + self.panel_w // 2
        pygame.draw.line(screen, (60, 60, 60), (line_x, self.y_base + 100), (line_x, self.y_base + self.panel_h - 120), 2)

        # --- 左侧：主公信息 ---
        l_center = self.x_base + self.panel_w // 4
        
        # 小标题
        t_p = self.font_label.render("【阁下名讳】", True, (200, 200, 200))
        screen.blit(t_p, (l_center - t_p.get_width()//2, self.y_base + 140))
        
        # 输入框
        self._draw_input_box(screen, 'player_name', "输入姓名...")
        
        # 性别
        t_pg = self.font_label.render("【阁下性别】", True, (200, 200, 200))
        screen.blit(t_pg, (l_center - t_pg.get_width()//2, self.y_base + 230))
        self._draw_gender_toggle(screen, 'p_gender_m', 'p_gender_f', self.data['player_gender'])

        # --- 右侧：门客信息 ---
        r_center = self.x_base + 3 * self.panel_w // 4
        
        # 开关按钮
        toggle_col = (50, 100, 50) if self.data['has_follower'] else (60, 60, 60)
        toggle_rect = self.rects['toggle_follower']
        pygame.draw.rect(screen, toggle_col, toggle_rect, border_radius=5)
        pygame.draw.rect(screen, (150,150,150), toggle_rect, 1, border_radius=5)
        
        toggle_txt = "携一门客同行" if self.data['has_follower'] else "不想孤身闯荡？"
        t_surf = self.font_btn.render(toggle_txt, True, (255, 255, 255) if self.data['has_follower'] else (150, 150, 150))
        screen.blit(t_surf, (toggle_rect.centerx - t_surf.get_width()//2, toggle_rect.centery - t_surf.get_height()//2))

        # 门客详细 (如果启用)
        if self.data['has_follower']:
            # 名字
            t_f = self.font_label.render("【门客姓名】", True, (200, 200, 200))
            screen.blit(t_f, (r_center - t_f.get_width()//2, self.y_base + 165))
            self._draw_input_box(screen, 'follower_name', "输入姓名...")

            # 性别
            
            t_fpg = self.font_label.render("【门客性别】", True, (200, 200, 200))
            screen.blit(t_fpg, (r_center - t_fpg.get_width()//2, self.y_base + 245))
            self._draw_gender_toggle(screen, 'f_gender_m', 'f_gender_f', self.data['follower_gender'])

            # 描述
            t_d = self.font_label.render("【既往经历】", True, (200, 200, 200))
            screen.blit(t_d, (r_center - t_d.get_width()//2, self.y_base + 330))
            self._draw_input_box(screen, 'follower_desc', "如：似乎优点只有美貌了...")
            
        else:
            # 未启用时的提示
            tips = self.font_label.render("前方路途凶险，", True, (100, 100, 100))
            tips2 = self.font_label.render("真的不需要帮手吗？", True, (100, 100, 100))
            screen.blit(tips, (r_center - tips.get_width()//2, self.y_base + 220))
            screen.blit(tips2, (r_center - tips2.get_width()//2, self.y_base + 250))

        # --- 底部：开始按钮 ---
        btn_hover = self.btn_start.collidepoint(mx, my)
        # 校验
        can_start = self._validate()
        
        if not can_start:
            btn_col = (60, 60, 60)
            btn_txt_str = "请登记信息"
        elif btn_hover:
            btn_col = (180, 50, 50)
            btn_txt_str = "进入游戏"
        else:
            btn_col = (150, 40, 40)
            btn_txt_str = "进入游戏"
            
        pygame.draw.rect(screen, btn_col, self.btn_start, border_radius=10)
        # 按钮边框
        border_col = (255, 215, 0) if (can_start and btn_hover) else (100, 100, 100)
        pygame.draw.rect(screen, border_col, self.btn_start, 2, border_radius=10)
        
        t_btn = self.font_btn.render(btn_txt_str, True, (255, 255, 255) if can_start else (150, 150, 150))
        screen.blit(t_btn, (self.btn_start.centerx - t_btn.get_width()//2, self.btn_start.centery - t_btn.get_height()//2))

        return self.is_finished

    def _draw_input_box(self, screen, key, placeholder):
        rect = self.rects[key]
        is_active = (self.active_key == key)
        
        col_bg = (30, 30, 35)
        col_border = (100, 200, 255) if is_active else (100, 100, 100)
        
        pygame.draw.rect(screen, col_bg, rect, border_radius=5)
        pygame.draw.rect(screen, col_border, rect, 2 if is_active else 1, border_radius=5)
        
        txt = self.data[key]
        if not txt and not is_active:
            # 占位符
            surf = self.font_input.render(placeholder, True, (80, 80, 80))
        else:
            # 内容
            display_txt = txt + ("|" if is_active and (pygame.time.get_ticks() // 500) % 2 == 0 else "")
            surf = self.font_input.render(display_txt, True, (255, 255, 255))
            
        # 垂直居中
        screen.blit(surf, (rect.x + 10, rect.centery - surf.get_height()//2))

    def _draw_gender_toggle(self, screen, key_m, key_f, current_val):
        rect_m = self.rects[key_m]
        rect_f = self.rects[key_f]
        
        col_active = (100, 150, 200)
        col_inactive = (50, 50, 60)
        
        # 男按钮
        pygame.draw.rect(screen, col_active if current_val == 'Male' else col_inactive, rect_m, border_radius=4)
        m_txt = self.font_input.render("男", True, (255,255,255))
        screen.blit(m_txt, (rect_m.centerx - m_txt.get_width()//2, rect_m.centery - m_txt.get_height()//2))
        
        # 女按钮
        pygame.draw.rect(screen, (200, 100, 100) if current_val == 'Female' else col_inactive, rect_f, border_radius=4)
        f_txt = self.font_input.render("女", True, (255,255,255))
        screen.blit(f_txt, (rect_f.centerx - f_txt.get_width()//2, rect_f.centery - f_txt.get_height()//2))

    def get_result(self):
        return self.data
    def run(self, screen, clock):
        """
        运行角色创建循环，阻塞直到玩家点击开始。
        返回: creation_result (dict)
        """
        try:
            pygame.key.start_text_input()
        except AttributeError:
            pass # 旧版本忽略
        creating = True
        while creating:
            # 限制帧率，防止空循环占用过高CPU
            clock.tick(60) 
            mx, my = pygame.mouse.get_pos()
            click_event = False
            
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    click_event = True
                
                # 处理输入
                self.handle_input(event)
            
            self.update()
            
            # draw 返回 True 表示点击了“开始游戏”按钮
            is_done = self.draw(screen, mx, my, click_event)
            
            if is_done:
                creating = False
            
            pygame.display.flip()
        
        # 退出输入模式
        try:
            pygame.key.stop_text_input()
        except AttributeError:
            pass
            
        return self.get_result()