# --- src/ui/panels.py ---
import pygame
from src.definitions import *
from src.utils import wrap_text
from src.ui.sidebar import draw_sidebar_panel # 导入新模块
class UIPanelsMixin:
    """
    UI 渲染模块 (Mixin)
    包含：侧边栏、顶部时间栏、科技树、事件弹窗、新闻流、名册、日报、游戏结束
    """

    def draw_top_bar(self, screen, time_system, mx, my, click_event):
        """
        绘制顶部时间栏：包含进度条、倍速控制
        [修复] 增加了交互参数 mx, my, click_event，现在可以点击切换倍速了
        """
        rect = pygame.Rect(0, 0, self.screen_w, TOPBAR_H)
        pygame.draw.rect(screen, (30, 30, 35), rect)
        pygame.draw.line(screen, (80, 80, 80), (0, TOPBAR_H), (self.screen_w, TOPBAR_H), 2)

        # 1. 日期显示
        font_date = self.font_big
        # 兼容两种时间系统属性 (优先读取 day)
        day_val = getattr(time_system, 'day', 1)
        if hasattr(time_system, 'game_tick') and not hasattr(time_system, 'day'):
            day_val = time_system.game_tick // 3600 + 1

        date_str = f"第 {day_val} 天"
        txt_date = font_date.render(date_str, True, (255, 255, 255))
        screen.blit(txt_date, (20, 15))

        # 2. 时间进度条
        bar_w = 400
        bar_h = 10
        bar_x = (self.screen_w - bar_w) // 2
        bar_y = 25
        
        # 背景槽
        pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_w, bar_h), border_radius=5)
        
        # 进度计算 (优先使用 time_of_day)
        progress = 0.0
        if hasattr(time_system, 'time_of_day') and hasattr(time_system, 'day_length'):
            progress = time_system.time_of_day / time_system.day_length
        elif hasattr(time_system, 'get_day_progress'):
            progress = time_system.get_day_progress()
            
        fill_w = int(bar_w * progress)
        
        # 颜色随时间变化 (早晨绿 -> 中午黄 -> 晚上红)
        if progress < 0.3: col_bar = (100, 200, 100)
        elif progress < 0.7: col_bar = (220, 220, 100)
        else: col_bar = (200, 100, 100)
        
        pygame.draw.rect(screen, col_bar, (bar_x, bar_y, fill_w, bar_h), border_radius=5)
        
        # 3. 具体时刻文字（十二时辰显示）
        SHICHEN_NAMES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
        shichen_idx = min(int(progress * 12), 11)
        time_str = f"{SHICHEN_NAMES[shichen_idx]}时"
        txt_time = self.font_ui.render(time_str, True, (200, 200, 200))
        screen.blit(txt_time, (bar_x + bar_w + 15, 20))

        # 4. 倍速控制按钮
        # 兼容 time_scale 或 time_speed 属性名
        current_speed = getattr(time_system, 'time_scale', getattr(time_system, 'time_speed', 1))
        
        speeds = [0, 1, 2, 3] # 0=Pause
        btn_start_x = self.screen_w - 180
        for i, spd in enumerate(speeds):
            bx = btn_start_x + i * 40
            by = 15
            bw, bh = 30, 30
            btn_rect = pygame.Rect(bx, by, bw, bh)
            
            # 高亮当前速度
            is_active = (current_speed == spd)
            col_bg = (100, 200, 100) if is_active else (60, 60, 60)
            
            # 鼠标悬停变色
            if btn_rect.collidepoint(mx, my):
                col_bg = (150, 150, 150) if not is_active else (120, 220, 120)
                # 点击处理
                if click_event:
                    # 尝试调用 set_speed
                    if hasattr(time_system, 'set_speed'):
                        time_system.set_speed(spd)
            
            pygame.draw.rect(screen, col_bg, btn_rect, border_radius=4)
            pygame.draw.rect(screen, (200, 200, 200), btn_rect, 1)
            
            label = "||" if spd == 0 else f"x{spd}"
            txt = self.font_ui.render(label, True, (255, 255, 255))
            tx = bx + (bw - txt.get_width())//2
            ty = by + (bh - txt.get_height())//2
            screen.blit(txt, (tx, ty))

    
    def draw_sidebar(self, screen, player, all_cards, tech_mgr, quest_mgr, mx=0, my=0, click_event=False):
        """
        绘制侧边栏并处理交互
        
        Returns:
            'OPEN_PLAYER_DETAIL' | None
        """
        rect = pygame.Rect(self.screen_w - SIDEBAR_W, TOPBAR_H, SIDEBAR_W, self.screen_h - TOPBAR_H)
        
        # 注册 sidebar 为 UI 区域，防止点击时触发玩家移动
        from src.ui.hit_test import register_ui_zone, UI_LAYER_WIDGET
        register_ui_zone(rect, UI_LAYER_WIDGET, "sidebar")
        
        npcs = [c for c in all_cards if hasattr(c, 'job')] # 简单筛选
        result = draw_sidebar_panel(screen, rect, player, all_cards, tech_mgr, quest_mgr,
                           self.font_ui, self.font_big, self.font_small, mx, my, click_event,
                           self.screen_w, self.screen_h)
        return result

      


    def draw_event_debug_panel(self, screen, event_manager, player):
        """绘制事件弹窗 (包含选项需求和结果) - 此为 UIManager 备用方法"""
        if not hasattr(event_manager, 'current_event') or not event_manager.current_event:
            return

        evt = event_manager.current_event
        
        # 1. 半透明遮罩
        s = pygame.Surface((self.screen_w, self.screen_h))
        s.set_alpha(180)
        s.fill((0, 0, 0))
        screen.blit(s, (0, 0))
        
        # 2. 弹窗主体
        w, h = 600, 500
        x = (self.screen_w - w) // 2
        y = (self.screen_h - h) // 2
        
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(screen, COLOR_CARD_BG, rect, border_radius=8)
        pygame.draw.rect(screen, COLOR_CARD_BORDER, rect, 3, border_radius=8)
        
        # 3. 标题
        title = self.font_big.render(evt.title, True, (50, 50, 50))
        screen.blit(title, (x + 30, y + 30))
        
        # 4. 描述内容 (换行)
        desc_lines = wrap_text(evt.desc_template, self.font_ui, w - 60)
        dy = y + 80
        for line in desc_lines:
            t = self.font_ui.render(line, True, (20, 20, 20))
            screen.blit(t, (x + 30, dy))
            dy += 25
            
        # 5. 选项按钮
        options = [
            (evt.btn_a, evt.req_a, evt.eff_a, 'A'),
            (evt.btn_b, evt.req_b, evt.eff_b, 'B'),
            (evt.btn_c, evt.req_c, evt.eff_c, 'C')
        ]
        
        btn_start_y = y + h - 180
        btn_h = 50
        
        mouse_pos = pygame.mouse.get_pos()
        
        for i, (txt, req, eff, tag) in enumerate(options):
            if not txt: continue
            
            btn_y = btn_start_y + i * (btn_h + 10)
            btn_rect = pygame.Rect(x + 30, btn_y, w - 60, btn_h)
            
            # 检查条件
            can_afford = True
            if hasattr(event_manager, 'check_requirement'):
                can_afford = event_manager.check_requirement(player, req)
            
            # 颜色逻辑
            if not can_afford:
                bg_col = (100, 100, 100) # 灰色不可点
                border_col = (80, 80, 80)
            elif btn_rect.collidepoint(mouse_pos):
                bg_col = COLOR_BTN_HOVER
                border_col = (200, 200, 200)
            else:
                bg_col = COLOR_BTN
                border_col = (50, 50, 50)
                
            pygame.draw.rect(screen, bg_col, btn_rect, border_radius=5)
            pygame.draw.rect(screen, border_col, btn_rect, 2, border_radius=5)
            
            # 按钮文字
            t_btn = self.font_ui.render(f"{tag}. {txt}", True, (255, 255, 255))
            screen.blit(t_btn, (btn_rect.x + 15, btn_rect.y + 12))
            
            # 需求提示 (右对齐)
            if req:
                req_col = (255, 150, 150) if not can_afford else (150, 255, 150)
                t_req = self.font_small.render(f"需: {req}", True, req_col)
                screen.blit(t_req, (btn_rect.right - t_req.get_width() - 10, btn_rect.y + 15))


    def draw_tech_tree(self, screen, tech_mgr, player, mx, my, click_event):
        """绘制科技树界面 (含连线和交互)"""
        # 全屏深色背景
        s = pygame.Surface((self.screen_w, self.screen_h))
        s.set_alpha(245)
        s.fill((20, 25, 30))
        screen.blit(s, (0, 0))
        
        # 标题
        t_title = self.font_big.render("== 治国方略 (科技树) ==", True, (255, 215, 0))
        screen.blit(t_title, (50, 50))
        
        # 属性名兼容
        p_prestige = getattr(player, 'fame', getattr(player, 'prestige', 0))
        t_info = self.font_ui.render(f"当前威望: {p_prestige}   当前铜钱: {player.money}", True, (200, 200, 200))
        screen.blit(t_info, (50, 100))
        
        # 偏移量，让科技树居中
        offset_x = self.screen_w // 2
        offset_y = 200
        
        # 1. 画连线
        for tech_id, node in tech_mgr.techs.items():
            if not node.visible: continue
            
            # 当前节点中心位置
            node_center_x = node.x + offset_x + 80 # +w/2
            node_center_y = node.y + offset_y + 40 # +h/2
            
            # 查找前置科技，画线
            if node.req_tech and node.req_tech in tech_mgr.techs:
                parent = tech_mgr.techs[node.req_tech]
                parent_center_x = parent.x + offset_x + 80
                parent_center_y = parent.y + offset_y + 40
                
                # 连线颜色：如果父节点已解锁，线亮一点
                line_col = (100, 100, 100)
                if parent.unlocked:
                    line_col = (150, 200, 150)
                
                pygame.draw.line(screen, line_col, (parent_center_x, parent_center_y), (node_center_x, node_center_y), 3)
            
        # 2. 画节点
        should_close = False

        for tech_id, node in tech_mgr.techs.items():
            if not node.visible: continue
            
            x = node.x + offset_x
            y = node.y + offset_y
            w, h = 160, 80
            rect = pygame.Rect(x, y, w, h)
            
            # 状态颜色
            can_unlock = tech_mgr.can_unlock(tech_id, player)
            
            if node.unlocked:
                bg_col = (50, 150, 50) # 已解锁 (绿)
                bd_col = (100, 255, 100)
            elif can_unlock:
                bg_col = (150, 150, 50) # 可解锁 (黄)
                bd_col = (255, 255, 100)
                
                # 点击处理：解锁
                if click_event and rect.collidepoint(mx, my):
                    tech_mgr.unlock(tech_id, player)
            else:
                bg_col = (80, 80, 80) # 锁定 (灰)
                bd_col = (50, 50, 50)
                
            pygame.draw.rect(screen, bg_col, rect, border_radius=8)
            pygame.draw.rect(screen, bd_col, rect, 2, border_radius=8)
            
            # 文字
            t_name = self.font_ui.render(node.name, True, (255, 255, 255))
            screen.blit(t_name, (x + 10, y + 10))
            
            # 费用
            cost_p = getattr(node, 'cost_prestige', 0)
            cost_str = f"¥{node.cost_money} 冠{cost_p}"
            col_cost = (200, 200, 200)
            
            # 如果可解锁，检查资源是否足够，不够标红
            if can_unlock and not node.unlocked:
                if player.money < node.cost_money or p_prestige < cost_p:
                    col_cost = (255, 100, 100)
            
            t_cost = self.font_small.render(cost_str, True, col_cost)
            screen.blit(t_cost, (x + 10, y + 40))
            
            # 鼠标悬停提示 (Tooltip)
            if rect.collidepoint(mx, my):
                self.draw_tooltip(screen, node.desc, (mx, my))

        # 关闭按钮
        close_rect = pygame.Rect(self.screen_w - 60, 20, 40, 40)
        pygame.draw.rect(screen, (200, 50, 50), close_rect, border_radius=5)
        txt_close = self.font_big.render("X", True, (255,255,255))
        screen.blit(txt_close, (close_rect.centerx - txt_close.get_width()//2, close_rect.centery - txt_close.get_height()//2))

        if click_event and close_rect.collidepoint(mx, my):
            should_close = True
            
        return should_close


    def draw_news_feed(self, screen, event_manager, mx, my, click_event):
        """
        【整合版】大宋实况面板
        合并原有的：
        - 大宋头条（事件历史记录）
        - 江湖传闻（传闻系统）
        
        左侧显示新闻头条，右侧显示江湖传闻
        """
        # 1. 全屏遮罩
        s = pygame.Surface((self.screen_w, self.screen_h))
        s.set_alpha(240)
        s.fill((10, 10, 15))
        screen.blit(s, (0, 0))

        # 2. 窗口主体
        cx, cy = 80, 40
        cw, ch = self.screen_w - 160, self.screen_h - 80
        pygame.draw.rect(screen, (30, 30, 35), (cx, cy, cw, ch), border_radius=10)
        pygame.draw.rect(screen, (180, 140, 60), (cx, cy, cw, ch), 2, border_radius=10)

        # 3. 主标题
        title = self.font_big.render("══ 大宋实况 ══", True, (255, 215, 0))
        screen.blit(title, (cx + cw // 2 - title.get_width() // 2, cy + 15))
        pygame.draw.line(screen, (80, 80, 80), (cx + 20, cy + 55), (cx + cw - 20, cy + 55))

        # ═══════════════════════════════════════════════════════════════
        # 4. 左侧：事件头条（60%宽度）
        # ═══════════════════════════════════════════════════════════════
        left_panel_x = cx + 20
        left_panel_w = int((cw - 60) * 0.55)
        panel_top = cy + 70
        panel_h = ch - 140
        
        # 左侧标题
        left_title = self.font_ui.render("[报] 事件头条", True, (220, 200, 150))
        screen.blit(left_title, (left_panel_x, panel_top))
        pygame.draw.line(screen, (60, 60, 60), (left_panel_x, panel_top + 25), (left_panel_x + left_panel_w, panel_top + 25))
        
        # 事件列表
        history = event_manager.news_history
        list_y = panel_top + 35
        line_height = 24
        max_lines = (panel_h - 50) // line_height
        display_items = history[-max_lines:] if len(history) > max_lines else history

        if not display_items:
            empty_txt = self.font_small.render("暂无新闻...", True, (100, 100, 100))
            screen.blit(empty_txt, (left_panel_x + 10, list_y))
        else:
            # 倒序显示，最新的在上面
            for i, msg in enumerate(reversed(display_items)):
                text = msg['text'] if isinstance(msg, dict) else str(msg)
                cat = msg.get('category', 'NEWS') if isinstance(msg, dict) else 'NEWS'
                
                # 根据类别配色
                color = (180, 180, 180)
                icon = "○"
                if cat == 'IMPORTANT': 
                    color = (255, 100, 100)
                    icon = "●"
                elif cat == 'GOOD': 
                    color = (100, 255, 100)
                    icon = "◎"
                elif cat == 'COMBAT':
                    color = (255, 150, 100)
                    icon = "战"
                
                # 截断过长文本
                if len(text) > 35:
                    text = text[:35] + "..."
                
                full_str = f"{icon} {text}"
                txt_surf = self.font_small.render(full_str, True, color)
                screen.blit(txt_surf, (left_panel_x + 5, list_y))
                list_y += line_height
                
                if list_y > panel_top + panel_h - 20:
                    break

        # ═══════════════════════════════════════════════════════════════
        # 5. 右侧：江湖传闻（40%宽度）
        # ═══════════════════════════════════════════════════════════════
        right_panel_x = cx + 30 + left_panel_w + 20
        right_panel_w = cw - left_panel_w - 70
        
        # 右侧标题
        right_title = self.font_ui.render("[闻] 江湖传闻", True, (220, 180, 120))
        screen.blit(right_title, (right_panel_x, panel_top))
        pygame.draw.line(screen, (60, 60, 60), (right_panel_x, panel_top + 25), (right_panel_x + right_panel_w, panel_top + 25))
        
        # 获取传闻系统数据
        try:
            from src.rumor_system import get_rumor_system, RumorType
            rumor_sys = get_rumor_system()
            rumors = rumor_sys.get_recent_rumors(count=10)
        except:
            rumors = []
        
        list_y = panel_top + 35
        
        # 传闻类型对应的图标和颜色（使用文字替代emoji）
        rumor_styles = {
            RumorType.COMBAT_VICTORY: ("战", (255, 200, 100)),   # 战斗胜利
            RumorType.KILLED_NPC: ("杀", (255, 80, 80)),        # 击杀
            RumorType.HELP_NPC: ("助", (100, 255, 150)),        # 帮助
            RumorType.THEFT_CAUGHT: ("盗", (255, 150, 100)),    # 盗窃
            RumorType.BETRAY: ("叛", (200, 100, 200)),          # 背叛
            RumorType.BOUNTY_POSTED: ("赏", (255, 215, 0)),     # 悬赏
            RumorType.FACTION_CHANGE: ("势", (180, 180, 255)),  # 势力变动
            RumorType.TERRITORY_CHANGE: ("地", (100, 200, 255)), # 领地变化
        } if rumors else {}
        
        if not rumors:
            empty_txt = self.font_small.render("街头巷尾一片平静...", True, (100, 100, 100))
            screen.blit(empty_txt, (right_panel_x + 10, list_y))
        else:
            for rumor in reversed(rumors):  # 最新的在前
                if list_y > panel_top + panel_h - 20:
                    break
                
                # 获取图标和颜色
                icon, color = rumor_styles.get(rumor.rumor_type, ("○", (180, 180, 180)))
                
                # 计算时间
                days_ago = rumor_sys.current_day - rumor.created_day
                if days_ago == 0:
                    time_str = "今日"
                elif days_ago == 1:
                    time_str = "昨日"
                else:
                    time_str = f"{days_ago}日前"
                
                # 获取传闻文本
                rumor_text = rumor.get_text()
                if len(rumor_text) > 25:
                    rumor_text = rumor_text[:25] + "..."
                
                # 绘制时间标签
                time_surf = self.font_small.render(f"[{time_str}]", True, (120, 120, 120))
                screen.blit(time_surf, (right_panel_x + 5, list_y))
                
                # 绘制传闻内容
                text_surf = self.font_small.render(f"{icon} {rumor_text}", True, color)
                screen.blit(text_surf, (right_panel_x + 5, list_y + 16))
                
                # 传播度指示
                spread_pct = min(100, int(rumor.spread_count / max(1, rumor.spread_range) * 100))
                spread_color = (100, 255, 100) if spread_pct > 50 else (200, 200, 100)
                spread_surf = self.font_small.render(f"传播: {spread_pct}%", True, spread_color)
                screen.blit(spread_surf, (right_panel_x + right_panel_w - spread_surf.get_width() - 5, list_y))
                
                list_y += 40

        # 分隔线
        pygame.draw.line(screen, (60, 60, 60), 
                         (cx + 25 + left_panel_w + 5, panel_top), 
                         (cx + 25 + left_panel_w + 5, panel_top + panel_h), 1)

        # 6. 关闭按钮
        btn_close_rect = pygame.Rect((self.screen_w - 120) // 2, cy + ch - 55, 120, 40)
        
        btn_color = (120, 80, 40)
        if btn_close_rect.collidepoint(mx, my):
            btn_color = (160, 110, 60)
            if click_event:
                return True  # 返回 True 表示应该关闭

        pygame.draw.rect(screen, btn_color, btn_close_rect, border_radius=5)
        pygame.draw.rect(screen, (200, 160, 80), btn_close_rect, 1, border_radius=5)
        txt_close = self.font_ui.render("关闭", True, (255, 255, 255))
        screen.blit(txt_close, (btn_close_rect.centerx - txt_close.get_width()//2, btn_close_rect.centery - txt_close.get_height()//2))

        return False


    def draw_follower_panel(self, screen, player, all_cards, mx, my, click_event):
        """
        【新增】门客管理面板 - 专门管理已招募的门客
        显示：门客列表、战斗力、状态、指令
        """
        from src.entities import NPC
        
        # 1. 全屏遮罩
        s = pygame.Surface((self.screen_w, self.screen_h))
        s.set_alpha(240)
        s.fill((15, 15, 20))
        screen.blit(s, (0, 0))
        
        # 2. 面板主体
        cx, cy = 120, 60
        cw, ch = self.screen_w - 240, self.screen_h - 120
        pygame.draw.rect(screen, (40, 45, 50), (cx, cy, cw, ch), border_radius=10)
        pygame.draw.rect(screen, (255, 215, 0), (cx, cy, cw, ch), 2, border_radius=10)
        
        # 3. 标题
        title = self.font_big.render("══ 门客管理 ══", True, (255, 215, 0))
        screen.blit(title, (cx + 20, cy + 15))
        
        # 统计信息
        followers = [c for c in all_cards if isinstance(c, NPC) and getattr(c, 'is_follower', False)
                     and c.safety not in [SAFETY_DEAD, SAFETY_EXILED]]
        total_combat = sum(getattr(f, 'combat', 30) + getattr(f, 'atk', 0) for f in followers)
        
        stats_text = f"门客数量: {len(followers)}   总战力: {total_combat}"
        stats_surf = self.font_ui.render(stats_text, True, (200, 200, 200))
        screen.blit(stats_surf, (cx + cw - stats_surf.get_width() - 30, cy + 22))
        
        # 分隔线
        pygame.draw.line(screen, (100, 100, 80), (cx + 20, cy + 55), (cx + cw - 20, cy + 55))
        
        # 4. 表头
        headers = ["姓名", "战力", "生命", "状态", "装备", "指令"]
        col_widths = [100, 60, 80, 120, 100, 180]
        hx = cx + 20
        hy = cy + 65
        
        for i, h in enumerate(headers):
            h_surf = self.font_ui.render(h, True, (200, 180, 100))
            screen.blit(h_surf, (hx, hy))
            hx += col_widths[i]
        
        pygame.draw.line(screen, (80, 80, 60), (cx + 20, hy + 25), (cx + cw - 20, hy + 25))
        
        # 5. 门客列表
        curr_y = hy + 35
        row_height = 45
        
        for follower in followers:
            if curr_y + row_height > cy + ch - 70:
                break  # 防止溢出
            
            # 行背景（悬停高亮）
            row_rect = pygame.Rect(cx + 15, curr_y - 3, cw - 30, row_height - 5)
            is_hover = row_rect.collidepoint(mx, my)
            if is_hover:
                pygame.draw.rect(screen, (50, 55, 60), row_rect, border_radius=4)
            
            col_x = cx + 20
            
            # 姓名（显示健康状态颜色）
            name_color = (255, 100, 100) if follower.hp < follower.max_hp * 0.3 else (255, 255, 255)
            name_surf = self.font_ui.render(follower.name, True, name_color)
            screen.blit(name_surf, (col_x, curr_y))
            col_x += col_widths[0]
            
            # 战力
            combat = getattr(follower, 'combat', 30) + getattr(follower, 'atk', 0)
            combat_surf = self.font_ui.render(str(combat), True, (200, 150, 100))
            screen.blit(combat_surf, (col_x, curr_y))
            col_x += col_widths[1]
            
            # 生命（进度条）
            hp_pct = follower.hp / follower.max_hp if follower.max_hp > 0 else 0
            bar_w, bar_h = 60, 12
            pygame.draw.rect(screen, (50, 50, 50), (col_x, curr_y + 5, bar_w, bar_h), border_radius=3)
            if hp_pct > 0:
                hp_color = (60, 200, 60) if hp_pct > 0.5 else (255, 150, 50) if hp_pct > 0.2 else (255, 80, 80)
                pygame.draw.rect(screen, hp_color, (col_x, curr_y + 5, int(bar_w * hp_pct), bar_h), border_radius=3)
            hp_text = self.font_small.render(f"{follower.hp}/{follower.max_hp}", True, (200, 200, 200))
            screen.blit(hp_text, (col_x + bar_w + 5, curr_y + 3))
            col_x += col_widths[2]
            
            # 当前状态/任务
            ai_reason = getattr(follower, 'ai_reason', '待命')[:12]
            state_color = (100, 255, 100) if 'Follow' in ai_reason or '跟随' in ai_reason else (180, 180, 180)
            state_surf = self.font_small.render(ai_reason, True, state_color)
            screen.blit(state_surf, (col_x, curr_y + 3))
            col_x += col_widths[3]
            
            # 装备
            weapon = getattr(follower, 'equip_weapon', None)
            weapon_text = weapon if weapon else "空手"
            weapon_surf = self.font_small.render(weapon_text[:8], True, (180, 160, 140))
            screen.blit(weapon_surf, (col_x, curr_y + 3))
            col_x += col_widths[4]
            
            # 指令按钮
            btn_w, btn_h = 50, 24
            
            # 跟随按钮
            ai_mode = getattr(follower, 'ai_mode', 'DEFAULT')
            btn_follow = pygame.Rect(col_x, curr_y, btn_w, btn_h)
            is_follow_active = (ai_mode == "FOLLOW")
            follow_color = (80, 150, 80) if is_follow_active else (60, 60, 60)
            follow_hover = btn_follow.collidepoint(mx, my)
            if follow_hover:
                follow_color = (100, 180, 100) if is_follow_active else (80, 80, 80)
            
            pygame.draw.rect(screen, follow_color, btn_follow, border_radius=3)
            follow_txt = self.font_small.render("跟随", True, (255, 255, 255))
            screen.blit(follow_txt, (btn_follow.centerx - follow_txt.get_width()//2, 
                                     btn_follow.centery - follow_txt.get_height()//2))
            
            if click_event and follow_hover:
                follower.ai_mode = "FOLLOW"
            
            # 待命按钮
            btn_idle = pygame.Rect(col_x + btn_w + 5, curr_y, btn_w, btn_h)
            is_idle_active = (ai_mode == "IDLE")
            idle_color = (80, 80, 150) if is_idle_active else (60, 60, 60)
            idle_hover = btn_idle.collidepoint(mx, my)
            if idle_hover:
                idle_color = (100, 100, 180) if is_idle_active else (80, 80, 80)
            
            pygame.draw.rect(screen, idle_color, btn_idle, border_radius=3)
            idle_txt = self.font_small.render("待命", True, (255, 255, 255))
            screen.blit(idle_txt, (btn_idle.centerx - idle_txt.get_width()//2,
                                   btn_idle.centery - idle_txt.get_height()//2))
            
            if click_event and idle_hover:
                follower.ai_mode = "IDLE"
            
            # 自由按钮
            btn_free = pygame.Rect(col_x + (btn_w + 5) * 2, curr_y, btn_w, btn_h)
            is_free_active = (ai_mode == "DEFAULT")
            free_color = (150, 150, 80) if is_free_active else (60, 60, 60)
            free_hover = btn_free.collidepoint(mx, my)
            if free_hover:
                free_color = (180, 180, 100) if is_free_active else (80, 80, 80)
            
            pygame.draw.rect(screen, free_color, btn_free, border_radius=3)
            free_txt = self.font_small.render("自由", True, (255, 255, 255))
            screen.blit(free_txt, (btn_free.centerx - free_txt.get_width()//2,
                                   btn_free.centery - free_txt.get_height()//2))
            
            if click_event and free_hover:
                follower.ai_mode = "DEFAULT"
            
            curr_y += row_height
        
        # 无门客提示
        if not followers:
            empty_surf = self.font_ui.render("暂无门客，与NPC对话时可以招募", True, (150, 150, 150))
            screen.blit(empty_surf, (cx + cw // 2 - empty_surf.get_width() // 2, cy + ch // 2 - 30))
            
            hint_surf = self.font_small.render("提示：提高声望和金钱可以招募更强的帮手", True, (120, 120, 120))
            screen.blit(hint_surf, (cx + cw // 2 - hint_surf.get_width() // 2, cy + ch // 2 + 10))
        
        # 6. 底部说明
        help_text = "指令说明: 跟随=紧随玩家 | 待命=原地不动 | 自由=自主行动"
        help_surf = self.font_small.render(help_text, True, (120, 120, 120))
        screen.blit(help_surf, (cx + 20, cy + ch - 65))
        
        # 7. 关闭按钮
        btn_close_rect = pygame.Rect((self.screen_w - 120) // 2, cy + ch - 45, 120, 35)
        btn_hover = btn_close_rect.collidepoint(mx, my)
        close_color = (180, 120, 60) if btn_hover else (120, 80, 40)
        
        pygame.draw.rect(screen, close_color, btn_close_rect, border_radius=5)
        pygame.draw.rect(screen, (255, 215, 0), btn_close_rect, 1, border_radius=5)
        close_txt = self.font_ui.render("关闭", True, (255, 255, 255))
        screen.blit(close_txt, (btn_close_rect.centerx - close_txt.get_width()//2,
                                btn_close_rect.centery - close_txt.get_height()//2))
        
        if click_event and btn_hover:
            return True  # 请求关闭
        
        return False

    def draw_roster(self, screen, npc_mgr):
        """绘制百姓名册 (增强版：显示势力、等级、战力等信息)"""
        from src.data.character_seeds import ORGANIZATIONS
        from src.entities.npc import POWER_COLORS
        from src.faction_colors import get_org_color
        
        s = pygame.Surface((self.screen_w, self.screen_h))
        s.set_alpha(230)
        s.fill((30, 30, 40))
        screen.blit(s, (0, 0))

        cx, cy = 60, 40
        cw, ch = self.screen_w - 120, self.screen_h - 80
        pygame.draw.rect(screen, (50, 50, 60), (cx, cy, cw, ch), border_radius=10)
        pygame.draw.rect(screen, (150, 150, 150), (cx, cy, cw, ch), 2, border_radius=10)

        title = self.font_big.render("══ 百姓名册 ══", True, (255, 255, 255))
        screen.blit(title, (cx + 20, cy + 15))
        
        # 统计信息
        npc_list = getattr(npc_mgr, 'npcs', []) if not isinstance(npc_mgr, list) else npc_mgr
        total_alive = len([n for n in npc_list if getattr(n, 'safety', 'NORMAL') != SAFETY_DEAD and n.job != 'PLAYER'])
        follower_count = len([n for n in npc_list if getattr(n, 'is_follower', False)])
        stats_text = f"总人口: {total_alive}  门客: {follower_count}"
        stats_surf = self.font_small.render(stats_text, True, (180, 180, 180))
        screen.blit(stats_surf, (cx + cw - 200, cy + 22))

        # 列表头 - 增加更多列
        headers = ["姓名", "势力归属", "职级", "战力", "状态", "当前行为", "指令"]
        hx = cx + 15
        hy = cy + 55
        col_w = [80, 100, 60, 50, 50, 120, 160]
        
        for i, h_txt in enumerate(headers):
            t = self.font_small.render(h_txt, True, (200, 200, 100))
            screen.blit(t, (hx, hy))
            hx += col_w[i]
            
        pygame.draw.line(screen, (100, 100, 100), (cx + 15, hy + 22), (cx + cw - 15, hy + 22))

        # 获取列表并排序：门客在前 > 有势力的 > 流民 > 其他
        def sort_key(n):
            if getattr(n, 'is_follower', False):
                return (0, 0)  # 门客最前
            org = getattr(n, 'org_id', None)
            if org and org != 'NONE':
                rank = getattr(n, 'org_rank', 0) or 0
                return (1, -rank)  # 有势力的按等级排序
            if getattr(n, 'job', '') == 'NONE':
                return (2, 0)  # 流民
            return (3, 0)  # 其他
        
        sorted_npcs = sorted(npc_list, key=sort_key)

        mx, my = pygame.mouse.get_pos()
        
        y = hy + 28
        row_h = 26
        for npc in sorted_npcs:
            if getattr(npc, 'safety', 'NORMAL') == SAFETY_DEAD: continue 
            if npc.job == 'PLAYER': continue

            # 准备数据
            is_follower = getattr(npc, 'is_follower', False)
            org_id = getattr(npc, 'org_id', None) or 'NONE'
            org_rank = getattr(npc, 'org_rank', 0) or 0
            
            # 势力名称和颜色
            if is_follower:
                org_name = "【门客】"
                org_color = (80, 200, 255)
            elif org_id and org_id != 'NONE':
                org_data = ORGANIZATIONS.get(org_id, {})
                org_name = org_data.get('name', org_id)
                org_color = get_org_color(org_id)
            else:
                org_name = "无"
                org_color = (120, 120, 120)
            
            # 职级描述
            rank_names = {0: "成员", 1: "干部", 2: "精英", 3: "核心", 4: "首领"}
            rank_str = rank_names.get(org_rank, "成员") if org_id != 'NONE' else "--"
            rank_color = (255, 215, 100) if org_rank >= 3 else ((200, 200, 150) if org_rank >= 1 else (150, 150, 150))
            
            # 战力评估（基于属性）
            combat_power = getattr(npc, 'attack', 5) + getattr(npc, 'defense', 5) + getattr(npc, 'max_hp', 100) // 20
            if combat_power >= 25:
                power_str = "强"
                power_color = (255, 100, 100)
            elif combat_power >= 15:
                power_str = "中"
                power_color = (200, 200, 100)
            else:
                power_str = "弱"
                power_color = (150, 150, 150)
            
            # 状态
            hp_pct = npc.hp / max(npc.max_hp, 1) * 100
            if hp_pct >= 80:
                status_str = "健康"
                status_color = (100, 200, 100)
            elif hp_pct >= 50:
                status_str = "轻伤"
                status_color = (200, 200, 100)
            elif hp_pct >= 20:
                status_str = "重伤"
                status_color = (255, 150, 100)
            else:
                status_str = "濒死"
                status_color = (255, 80, 80)
            
            # 当前行为
            ai_status = getattr(npc, 'ai_reason', '发呆')
            if len(ai_status) > 10:
                ai_status = ai_status[:9] + ".."
            
            # 行高亮（门客用金色背景）
            if is_follower:
                row_rect = pygame.Rect(cx + 10, y - 2, cw - 20, row_h)
                pygame.draw.rect(screen, (60, 55, 40), row_rect, border_radius=3)
            
            # 绘制各列
            vx = cx + 15
            
            # 姓名
            name_surf = self.font_small.render(npc.name[:6], True, (255, 255, 255))
            screen.blit(name_surf, (vx, y))
            vx += col_w[0]
            
            # 势力归属
            org_surf = self.font_small.render(org_name[:6], True, org_color)
            screen.blit(org_surf, (vx, y))
            vx += col_w[1]
            
            # 职级
            rank_surf = self.font_small.render(rank_str, True, rank_color)
            screen.blit(rank_surf, (vx, y))
            vx += col_w[2]
            
            # 战力
            power_surf = self.font_small.render(power_str, True, power_color)
            screen.blit(power_surf, (vx, y))
            vx += col_w[3]
            
            # 状态
            status_surf = self.font_small.render(status_str, True, status_color)
            screen.blit(status_surf, (vx, y))
            vx += col_w[4]
            
            # 当前行为
            ai_surf = self.font_small.render(ai_status, True, (180, 180, 180))
            screen.blit(ai_surf, (vx, y))
            vx += col_w[5]
            
            # 指令按钮区域 (仅门客可用)
            if is_follower:
                ai_mode = getattr(npc, 'ai_mode', 'DEFAULT')
                
                # 按钮 1: 跟随
                btn_follow = pygame.Rect(vx, y - 2, 45, 22)
                follow_color = (80, 140, 80) if ai_mode == "FOLLOW" else (50, 50, 55)
                pygame.draw.rect(screen, follow_color, btn_follow, border_radius=3)
                follow_surf = self.font_small.render("跟随", True, (255, 255, 255))
                screen.blit(follow_surf, (btn_follow.centerx - follow_surf.get_width()//2, btn_follow.centery - follow_surf.get_height()//2))
                
                # 按钮 2: 干活
                btn_work = pygame.Rect(vx + 50, y - 2, 45, 22)
                work_color = (80, 140, 80) if ai_mode == "DEFAULT" else (50, 50, 55)
                pygame.draw.rect(screen, work_color, btn_work, border_radius=3)
                work_surf = self.font_small.render("干活", True, (255, 255, 255))
                screen.blit(work_surf, (btn_work.centerx - work_surf.get_width()//2, btn_work.centery - work_surf.get_height()//2))
                                
                # 按钮 3: 休息
                btn_idle = pygame.Rect(vx + 100, y - 2, 45, 22)
                idle_color = (80, 140, 80) if ai_mode == "IDLE" else (50, 50, 55)
                pygame.draw.rect(screen, idle_color, btn_idle, border_radius=3)
                idle_surf = self.font_small.render("休息", True, (255, 255, 255))
                screen.blit(idle_surf, (btn_idle.centerx - idle_surf.get_width()//2, btn_idle.centery - idle_surf.get_height()//2))
            else:
                t_na = self.font_small.render("--", True, (80, 80, 80))
                screen.blit(t_na, (vx + 40, y))

            y += row_h
            if y > cy + ch - 50: break
    
    def handle_roster_click(self, npc_mgr, mx, my):
        """处理名册内的点击事件 (在 Main 循环调用)"""
        # ... 复用上面的坐标计算逻辑 ...
        cx, cy = 100, 50
        hy = cy + 80
        col_w = [100, 80, 80, 150, 200]
        y = hy + 40
        
        npc_list = getattr(npc_mgr, 'npcs', []) if not isinstance(npc_mgr, list) else npc_mgr
        sorted_npcs = sorted(npc_list, key=lambda n: 0 if getattr(n, 'is_follower', False) else 1)
        
        for npc in sorted_npcs:
            if getattr(npc, 'safety', 'NORMAL') == SAFETY_DEAD: continue
            if npc.job == 'PLAYER': continue
            
            if getattr(npc, 'is_follower', False):
                vx = cx + 20 + sum(col_w[:4]) # 按钮起始X
                
                # 判定按钮点击
                if pygame.Rect(vx, y, 50, 24).collidepoint(mx, my):
                    npc.set_ai_mode("FOLLOW")
                elif pygame.Rect(vx + 55, y, 50, 24).collidepoint(mx, my):
                    npc.set_ai_mode("DEFAULT")
                elif pygame.Rect(vx + 110, y, 50, 24).collidepoint(mx, my):
                    npc.set_ai_mode("IDLE")
            
            y += 30


    def draw_daily_report(self, screen, report_data, mx, my, click_event):
        """绘制每日结算报告"""
        from src.data.character_seeds import ORGANIZATIONS
        from src.entities.npc import POWER_COLORS
        
        # 全黑背景
        screen.fill((0, 0, 0))
        
        # 居中显示
        cy = 100
        title = self.font_big.render(f"=== 第 {report_data.get('day', '?')} 天结算 ===", True, (255, 215, 0))
        tr = title.get_rect(center=(self.screen_w // 2, cy))
        screen.blit(title, tr)
        
        cy += 60
        
        income = report_data.get('income', 0)
        expenses = report_data.get('expenses', 0)
        if 'net_money' in report_data and income == 0 and expenses == 0:
            income = report_data['net_money']

        lines = [
            f"今日收入: +{income}",
            f"今日支出: -{expenses}",
            f"粮食消耗: -{report_data.get('food_consumed', 0)}",
            f"存活人口: {report_data.get('pop', 0)}",
            f"饿死人数: {report_data.get('died', 0)}",
        ]
        
        for line in lines:
            col = (255, 255, 255)
            if line.startswith("今日收入"): col = (100, 255, 100)
            if line.startswith("今日支出") or line.startswith("粮食消耗"): col = (255, 100, 100)
            if line.startswith("饿死"): col = (200, 50, 50)
            
            t = self.font_ui.render(line, True, col)
            tr = t.get_rect(center=(self.screen_w // 2, cy))
            screen.blit(t, tr)
            cy += 32
        
        # ═════════════════════════════════════════════════════════════════
        # 【阶段4】势力控制点收入展示
        # ═════════════════════════════════════════════════════════════════
        faction_income = report_data.get('faction_income', {})
        if faction_income:
            cy += 20
            faction_title = self.font_ui.render("── 势力控制点收入 ──", True, (180, 150, 100))
            tr = faction_title.get_rect(center=(self.screen_w // 2, cy))
            screen.blit(faction_title, tr)
            cy += 30
            
            # 按收入排序展示前5个势力
            sorted_factions = sorted(faction_income.items(), key=lambda x: x[1], reverse=True)[:5]
            for org_id, income_val in sorted_factions:
                org_data = ORGANIZATIONS.get(org_id, {})
                org_name = org_data.get('name', org_id)
                power_type = org_data.get('power_type', '民')
                org_color = POWER_COLORS.get(power_type, (150, 150, 150))
                
                faction_line = f"[{power_type}] {org_name}: +{income_val}铜"
                t = self.font_small.render(faction_line, True, org_color)
                tr = t.get_rect(center=(self.screen_w // 2, cy))
                screen.blit(t, tr)
                cy += 24
        
        cy += 30
        hint_line = self.font_small.render("按 [空格] 或 点击下方按钮 开始新的一天", True, (150, 150, 150))
        tr = hint_line.get_rect(center=(self.screen_w // 2, cy))
        screen.blit(hint_line, tr)
            
        # 交互按钮
        btn_rect = pygame.Rect((self.screen_w - 200)//2, self.screen_h - 120, 200, 50)
        pygame.draw.rect(screen, (50, 100, 50), btn_rect, border_radius=10)
        btn_txt = self.font_ui.render("开始新的一天", True, (255,255,255))
        screen.blit(btn_txt, (btn_rect.centerx - btn_txt.get_width()//2, btn_rect.centery - btn_txt.get_height()//2))
        
        if click_event and btn_rect.collidepoint(mx, my):
            return True
        return False


    def draw_game_over(self, screen, reason):
        """绘制游戏结束画面"""
        s = pygame.Surface((self.screen_w, self.screen_h))
        s.set_alpha(200)
        s.fill((50, 0, 0)) # 深红色背景
        screen.blit(s, (0, 0))
        
        t1 = self.font_big.render("胜败乃兵家常事", True, (255, 255, 255))
        r1 = t1.get_rect(center=(self.screen_w//2, self.screen_h//2 - 50))
        screen.blit(t1, r1)
        
        t2 = self.font_ui.render(f"失败原因: {reason}", True, (255, 100, 100))
        r2 = t2.get_rect(center=(self.screen_w//2, self.screen_h//2 + 20))
        screen.blit(t2, r2)
        
        t3 = self.font_small.render("按 ESC 退出游戏", True, (200, 200, 200))
        r3 = t3.get_rect(center=(self.screen_w//2, self.screen_h//2 + 80))
        screen.blit(t3, r3)


    def draw_tooltip(self, screen, text, pos):
        """通用悬停提示框"""
        lines = wrap_text(text, self.font_small, 200)
        w = 220
        h = len(lines) * 20 + 20
        
        x, y = pos
        # 防止出界
        if x + w > self.screen_w: x -= w
        if y + h > self.screen_h: y -= h
        
        rect = pygame.Rect(x, y + 20, w, h)
        pygame.draw.rect(screen, (30, 30, 30), rect)
        pygame.draw.rect(screen, (150, 150, 150), rect, 1)
        
        ty = y + 30
        for line in lines:
            t = self.font_small.render(line, True, (255, 255, 255))
            screen.blit(t, (x + 10, ty))
            ty += 20
    def draw_quest_log(self, screen, quest_mgr, mx, my, click_event):
        """绘制任务日志界面 (AVAILABLE/ACTIVE/FINISHED)"""
        # 1. 全屏半透明遮罩
        s = pygame.Surface((self.screen_w, self.screen_h))
        s.set_alpha(240)
        s.fill((15, 15, 20))
        screen.blit(s, (0, 0))

        # 2. 面板主体
        cx, cy = 100, 50
        cw, ch = self.screen_w - 200, self.screen_h - 100
        pygame.draw.rect(screen, (40, 40, 45), (cx, cy, cw, ch), border_radius=10)
        pygame.draw.rect(screen, (200, 200, 200), (cx, cy, cw, ch), 2, border_radius=10)

        # 3. 标题
        title = self.font_big.render("== 江湖传闻 (任务日志) ==", True, (255, 215, 0))
        screen.blit(title, (cx + 20, cy + 20))

        # 获取数据
        active_list, finished_list = quest_mgr.get_quest_log_data()

        # --- 左侧：当前任务 ---
        left_x = cx + 30
        curr_y = cy + 80
        
        header_act = self.font_ui.render("【当前要务】", True, (100, 255, 100))
        screen.blit(header_act, (left_x, curr_y))
        curr_y += 30
        
        if not active_list:
            t = self.font_ui.render("暂无活跃任务", True, (150, 150, 150))
            screen.blit(t, (left_x, curr_y))
        else:
            for q in active_list:
                # 标题 + 状态
                col_title = (255, 255, 255)
                if q['status'] == "可交付": col_title = (255, 255, 100)
                elif q['status'] == "待接取": col_title = (100, 200, 255)
                
                t_title = self.font_ui.render(f"[任] {q['title']} [{q['status']}]", True, col_title)
                screen.blit(t_title, (left_x, curr_y))
                curr_y += 25
                
                # 描述
                lines = wrap_text(q['desc'], self.font_small, 350)
                for line in lines:
                    t_desc = self.font_small.render(line, True, (200, 200, 200))
                    screen.blit(t_desc, (left_x + 20, curr_y))
                    curr_y += 18
                
                # 目标
                t_target = self.font_small.render(f"目标: {q['target']}", True, (150, 255, 150))
                screen.blit(t_target, (left_x + 20, curr_y))
                curr_y += 30

        # --- 右侧：已完成 ---
        right_x = cx + cw // 2 + 20
        curr_y = cy + 80
        
        # 分割线
        pygame.draw.line(screen, (80, 80, 80), (cx + cw // 2, cy + 60), (cx + cw // 2, cy + ch - 60))
        
        header_fin = self.font_ui.render("【往事如烟】(已完成)", True, (150, 150, 150))
        screen.blit(header_fin, (right_x, curr_y))
        curr_y += 30
        
        # 滚动区域 (简单截断)
        max_lines = 15
        for i, q in enumerate(reversed(finished_list)): # 最新的在上面
            if i >= max_lines: break
            t = self.font_small.render(f"[√] {q['title']} - {q['desc']}", True, (120, 120, 120))
            screen.blit(t, (right_x, curr_y))
            curr_y += 20

        # 4. 关闭按钮
        btn_close_rect = pygame.Rect((self.screen_w - 120) // 2, cy + ch - 60, 120, 40)
        btn_hover = btn_close_rect.collidepoint(mx, my)
        col = (200, 80, 80) if btn_hover else (150, 50, 50)
        
        pygame.draw.rect(screen, col, btn_close_rect, border_radius=5)
        txt_close = self.font_ui.render("关闭", True, (255, 255, 255))
        screen.blit(txt_close, (btn_close_rect.centerx - txt_close.get_width()//2, btn_close_rect.centery - txt_close.get_height()//2))

        if click_event and btn_hover:
            return True
        return False
    
    def _draw_org_task_tab(self, screen, player, mx, my, click_event, cx, cy, cw, ch):
        """
        绘制门派任务标签页
        显示：玩家所属门派任务列表、功勋、职级
        """
        from src.org_task_system import get_org_task_system
        from src.data.character_seeds import ORGANIZATIONS
        from src.entities.npc import POWER_COLORS
        
        org_task_sys = get_org_task_system()
        
        # ═══════════════════════════════════════════════════════════════
        # 左侧：组织选择列表
        # ═══════════════════════════════════════════════════════════════
        left_x = cx + 30
        curr_y = cy + 70
        
        header1 = self.font_ui.render("【选择势力】", True, (255, 215, 100))
        screen.blit(header1, (left_x, curr_y))
        curr_y += 35
        
        # 显示玩家有声望的组织
        org_btn_rects = []
        for org_id, org_data in list(ORGANIZATIONS.items())[:10]:
            power_type = org_data.get('power_type', '民')
            power_color = POWER_COLORS.get(power_type, (150, 150, 150))
            org_name = org_data.get('name', org_id)
            
            # 玩家声望
            standing = player.org_reputation.get(org_id, 0) if player else 0
            
            # 只显示有声望或玩家已加入的组织
            # 简化：显示所有组织
            btn_rect = pygame.Rect(left_x, curr_y, 180, 26)
            org_btn_rects.append((btn_rect, org_id))
            
            is_selected = (self._selected_org_for_task == org_id)
            is_hover = btn_rect.collidepoint(mx, my)
            
            if is_selected:
                bg_col = (60, 50, 40)
                pygame.draw.rect(screen, bg_col, btn_rect, border_radius=3)
                pygame.draw.rect(screen, power_color, btn_rect, 1, border_radius=3)
            elif is_hover:
                pygame.draw.rect(screen, (45, 40, 35), btn_rect, border_radius=3)
            
            # 组织名
            org_surf = self.font_small.render(f"[{power_type}] {org_name}", True, power_color)
            screen.blit(org_surf, (left_x + 5, curr_y + 4))
            
            # 功勋/职级（如果有）
            merit = org_task_sys.get_player_merit(org_id)
            if merit > 0:
                merit_surf = self.font_small.render(f"功勋:{merit}", True, (200, 180, 100))
                screen.blit(merit_surf, (left_x + 130, curr_y + 4))
            
            # 点击选择
            if click_event and is_hover:
                self._selected_org_for_task = org_id
                click_event = False
            
            curr_y += 28
        
        # ═══════════════════════════════════════════════════════════════
        # 中间：任务列表
        # ═══════════════════════════════════════════════════════════════
        mid_x = cx + 230
        task_area_w = cw - 280
        curr_y = cy + 70
        
        if self._selected_org_for_task:
            org_id = self._selected_org_for_task
            org_data = ORGANIZATIONS.get(org_id, {})
            org_name = org_data.get('name', org_id)
            power_type = org_data.get('power_type', '民')
            power_color = POWER_COLORS.get(power_type, (150, 150, 150))
            
            # 组织标题 + 玩家状态
            player_rank = org_task_sys.get_player_rank(org_id)
            rank_name = org_task_sys.get_rank_name(org_id, player_rank)
            merit = org_task_sys.get_player_merit(org_id)
            next_merit = org_task_sys.get_next_rank_requirement(org_id, player_rank)
            
            header2 = self.font_ui.render(f"【{org_name}】任务", True, power_color)
            screen.blit(header2, (mid_x, curr_y))
            
            # 职级和功勋
            if next_merit > 0:
                status_text = f"职位: {rank_name} | 功勋: {merit}/{next_merit}"
            else:
                status_text = f"职位: {rank_name} | 功勋: {merit} (已满级)"
            status_surf = self.font_small.render(status_text, True, (200, 200, 150))
            screen.blit(status_surf, (mid_x + 200, curr_y + 3))
            
            curr_y += 40
            
            # 分隔线
            pygame.draw.line(screen, (80, 70, 60), (mid_x, curr_y), (mid_x + task_area_w - 50, curr_y))
            curr_y += 15
            
            # 获取任务数据
            task_data = org_task_sys.get_task_panel_data(org_id, player_rank)
            
            # --- 进行中的任务 ---
            active_tasks = task_data['active']
            if active_tasks:
                act_header = self.font_small.render("═ 进行中 ═", True, (100, 200, 255))
                screen.blit(act_header, (mid_x, curr_y))
                curr_y += 22
                
                for task in active_tasks[:3]:  # 限制显示数量
                    # 任务标题
                    status_col = (100, 255, 100) if task.status.value == 'completed' else (255, 255, 200)
                    status_text = "[ok]待交付" if task.status.value == 'completed' else f"({task.progress}/{task.count})"
                    
                    task_title = self.font_small.render(f"● {task.title} {status_text}", True, status_col)
                    screen.blit(task_title, (mid_x + 10, curr_y))
                    
                    # 奖励
                    reward_text = f"+{task.merit_reward}功勋"
                    if task.money_reward > 0:
                        reward_text += f" +{task.money_reward}铜"
                    reward_surf = self.font_small.render(reward_text, True, (200, 180, 100))
                    screen.blit(reward_surf, (mid_x + task_area_w - 150, curr_y))
                    
                    curr_y += 20
                    
                    # 描述
                    desc_surf = self.font_small.render(task.desc[:30] + "..." if len(task.desc) > 30 else task.desc, True, (150, 150, 150))
                    screen.blit(desc_surf, (mid_x + 20, curr_y))
                    curr_y += 25
                
                curr_y += 10
            
            # --- 可接取的任务 ---
            available_tasks = task_data['available']
            if available_tasks:
                avail_header = self.font_small.render("═ 可接取 ═", True, (255, 215, 100))
                screen.blit(avail_header, (mid_x, curr_y))
                curr_y += 22
                
                for task in available_tasks[:5]:  # 限制显示数量
                    # 任务行
                    task_rect = pygame.Rect(mid_x, curr_y, task_area_w - 50, 45)
                    is_hover = task_rect.collidepoint(mx, my)
                    
                    if is_hover:
                        pygame.draw.rect(screen, (50, 45, 40), task_rect, border_radius=3)
                    
                    # 任务标题
                    task_title = self.font_small.render(f"○ {task.title}", True, (220, 220, 200))
                    screen.blit(task_title, (mid_x + 10, curr_y + 3))
                    
                    # 奖励
                    reward_text = f"+{task.merit_reward}功勋"
                    if task.money_reward > 0:
                        reward_text += f" +{task.money_reward}铜"
                    reward_surf = self.font_small.render(reward_text, True, (200, 180, 100))
                    screen.blit(reward_surf, (mid_x + task_area_w - 150, curr_y + 3))
                    
                    # 描述
                    desc_surf = self.font_small.render(task.desc[:35] + "..." if len(task.desc) > 35 else task.desc, True, (150, 150, 150))
                    screen.blit(desc_surf, (mid_x + 20, curr_y + 22))
                    
                    # 接取按钮
                    btn_accept = pygame.Rect(mid_x + task_area_w - 70, curr_y + 8, 50, 22)
                    btn_hover = btn_accept.collidepoint(mx, my)
                    btn_col = (100, 150, 80) if btn_hover else (70, 100, 60)
                    pygame.draw.rect(screen, btn_col, btn_accept, border_radius=3)
                    btn_text = self.font_small.render("接取", True, (255, 255, 255))
                    screen.blit(btn_text, (btn_accept.centerx - btn_text.get_width()//2,
                                          btn_accept.centery - btn_text.get_height()//2))
                    
                    # 点击接取
                    if click_event and btn_hover:
                        # 存储待处理的任务接取请求
                        if not hasattr(self, '_pending_task_accept'):
                            self._pending_task_accept = None
                        self._pending_task_accept = (org_id, task.id)
                        click_event = False
                    
                    curr_y += 50
            else:
                if not active_tasks:
                    empty_surf = self.font_small.render("暂无可用任务", True, (120, 120, 120))
                    screen.blit(empty_surf, (mid_x + 10, curr_y))
        else:
            # 未选择组织
            hint_surf = self.font_ui.render("← 请选择一个势力查看任务", True, (150, 150, 150))
            screen.blit(hint_surf, (mid_x + 50, cy + ch // 2 - 50))
        
        # ═══════════════════════════════════════════════════════════════
        # 关闭按钮
        # ═══════════════════════════════════════════════════════════════
        btn_close_rect = pygame.Rect((self.screen_w - 120) // 2, cy + ch - 55, 120, 40)
        btn_hover = btn_close_rect.collidepoint(mx, my)
        col = (180, 120, 60) if btn_hover else (120, 80, 40)
        
        pygame.draw.rect(screen, col, btn_close_rect, border_radius=5)
        pygame.draw.rect(screen, (200, 180, 150), btn_close_rect, 1, border_radius=5)
        txt_close = self.font_ui.render("关闭", True, (255, 255, 255))
        screen.blit(txt_close, (btn_close_rect.centerx - txt_close.get_width()//2, 
                                btn_close_rect.centery - txt_close.get_height()//2))

        if click_event and btn_hover:
            return True
        return False

    # ═══════════════════════════════════════════════════════════════════
    # 建筑详情面板 - 显示建筑信息并允许玩家势力占领
    # ═══════════════════════════════════════════════════════════════════
    
    def draw_building_info_panel(self, screen, building, player, faction_war_system, mx, my, click_event):
        """
        绘制建筑详情面板
        
        Args:
            building: 目标建筑对象
            player: 玩家对象
            faction_war_system: 势力战争系统
            mx, my: 鼠标位置
            click_event: 是否有点击事件
            
        Returns:
            (close_clicked: bool, occupy_clicked: bool)
        """
        from src.data.building_defs import BUILDING_DB, BUILDING_ICONS
        from src.data.character_seeds import ORGANIZATIONS
        from src.faction_war_system import ResourceControlPoint
        from src.recipe_system import RecipeManager
        
        # 获取建筑配方
        recipe_mgr = RecipeManager()
        b_type = getattr(building, 'building_type', 'UNKNOWN')
        recipes = recipe_mgr.get_recipes_for_building(b_type)
        
        # 根据配方数量动态调整面板高度
        base_height = 280
        recipe_height = min(len(recipes), 6) * 28  # 每行配方28像素，最多显示6条
        panel_h = base_height + recipe_height + (60 if recipes else 0)
        
        # 面板尺寸和位置
        panel_w = 450
        px = (self.screen_w - panel_w) // 2
        py = (self.screen_h - panel_h) // 2
        
        # 绘制背景
        bg_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        bg_surf.fill((40, 35, 30, 240))
        screen.blit(bg_surf, (px, py))
        
        # 边框
        pygame.draw.rect(screen, (150, 120, 80), (px, py, panel_w, panel_h), 3, border_radius=8)
        pygame.draw.rect(screen, (100, 80, 50), (px+2, py+2, panel_w-4, panel_h-4), 1, border_radius=6)
        
        # 获取建筑信息
        b_type = getattr(building, 'building_type', 'UNKNOWN')
        b_def = BUILDING_DB.get(b_type, {})
        b_name = b_def.get('name', '未知建筑')
        b_desc = b_def.get('desc', '没有描述')
        b_power_type = b_def.get('power_type', None)
        
        # 获取图标
        icon_data = BUILDING_ICONS.get(b_type, ("宅", (100, 100, 100)))
        icon_str = icon_data[0]
        icon_color = icon_data[1]
        
        # 获取控制点信息
        controller_org, control_point = faction_war_system.get_building_controller(building)
        
        curr_y = py + 15
        
        # ═══ 标题 ═══
        title_text = f"{icon_str} {b_name}"
        title_surf = self.font_big.render(title_text, True, (255, 220, 150))
        screen.blit(title_surf, (px + panel_w // 2 - title_surf.get_width() // 2, curr_y))
        curr_y += 40
        
        # ═══ 描述 ═══
        desc_surf = self.font_small.render(b_desc[:50], True, (180, 180, 180))
        screen.blit(desc_surf, (px + 20, curr_y))
        curr_y += 30
        
        # ═══ 分隔线 ═══
        pygame.draw.line(screen, (100, 80, 50), (px + 20, curr_y), (px + panel_w - 20, curr_y), 1)
        curr_y += 15
        
        # ═══ 控制状态 ═══
        if control_point:
            # 当前控制者
            if controller_org:
                org_data = ORGANIZATIONS.get(controller_org, {})
                org_name = org_data.get('name', controller_org)
                power_type = org_data.get('power_type', '民')
                
                # 势力类型颜色
                POWER_COLORS = {
                    '士': (200, 180, 100), '农': (100, 180, 100), '工': (180, 150, 100),
                    '商': (200, 150, 80), '学': (100, 150, 200), '兵': (200, 100, 100),
                    '游': (180, 100, 180), '匪': (100, 100, 100), '民': (150, 150, 150),
                }
                org_color = POWER_COLORS.get(power_type, (150, 150, 150))
                
                ctrl_label = self.font_ui.render("当前控制:", True, (200, 200, 200))
                screen.blit(ctrl_label, (px + 20, curr_y))
                
                ctrl_value = self.font_ui.render(f"[{power_type}] {org_name}", True, org_color)
                screen.blit(ctrl_value, (px + 120, curr_y))
                curr_y += 28
                
                # 控制强度
                strength_label = self.font_small.render(f"控制强度: {control_point.control_strength}%", True, (150, 200, 150))
                screen.blit(strength_label, (px + 20, curr_y))
                
                # 争夺中标记
                if control_point.contested:
                    contest_surf = self.font_small.render("战 争夺中!", True, (255, 100, 100))
                    screen.blit(contest_surf, (px + 200, curr_y))
                curr_y += 25
            else:
                no_ctrl = self.font_ui.render("当前控制: 无主", True, (150, 150, 150))
                screen.blit(no_ctrl, (px + 20, curr_y))
                curr_y += 28
            
            # 每日收益
            income_text = f"每日收益: +{control_point.daily_income} ({control_point.resource_type})"
            income_surf = self.font_small.render(income_text, True, (150, 200, 100))
            screen.blit(income_surf, (px + 20, curr_y))
            curr_y += 25
            
            # 控制难度
            diff_text = f"控制难度: {'*' * control_point.difficulty}{'-' * (5 - control_point.difficulty)}"
            diff_surf = self.font_small.render(diff_text, True, (200, 180, 100))
            screen.blit(diff_surf, (px + 20, curr_y))
            curr_y += 30
        else:
            # 不是控制点
            no_point = self.font_ui.render("此建筑不属于战略要地", True, (150, 150, 150))
            screen.blit(no_point, (px + 20, curr_y))
            curr_y += 50
        
        # ═══════════════════════════════════════════════════════════════════
        # 【新增】配方/产出显示区域
        # ═══════════════════════════════════════════════════════════════════
        if recipes:
            # 配方区域标题
            recipe_title = self.font_ui.render("[方] 可用配方/产出:", True, (220, 200, 150))
            screen.blit(recipe_title, (px + 20, curr_y))
            curr_y += 26
            
            # 显示配方列表（最多6条）
            for i, recipe in enumerate(recipes[:6]):
                # 交替背景色
                if i % 2 == 0:
                    row_bg = pygame.Surface((panel_w - 40, 24), pygame.SRCALPHA)
                    row_bg.fill((50, 45, 40, 120))
                    screen.blit(row_bg, (px + 20, curr_y))
                
                # 配方描述
                desc = recipe.get('desc', '未知')
                output = recipe.get('output', '')
                input_req = recipe.get('input', '')
                cost = recipe.get('cost', '')
                ext = recipe.get('ext_input', '')
                
                # 格式: [描述] → 产出 (需要: 输入)
                recipe_text = f"• {desc}"
                if output:
                    recipe_text += f" → {output}"
                if cost:
                    recipe_text += f" {cost}"
                
                # 限制显示长度
                if len(recipe_text) > 45:
                    recipe_text = recipe_text[:42] + "..."
                
                recipe_surf = self.font_small.render(recipe_text, True, (180, 200, 160))
                screen.blit(recipe_surf, (px + 25, curr_y + 3))
                
                # 在右侧显示输入要求（小字）
                if input_req and input_req != '任何人':
                    req_text = f"[{input_req}{ext}]"
                    req_surf = self.font_small.render(req_text, True, (150, 150, 180))
                    screen.blit(req_surf, (px + panel_w - 25 - req_surf.get_width(), curr_y + 3))
                
                curr_y += 24
            
            # 如果还有更多配方
            if len(recipes) > 6:
                more_text = f"... 还有 {len(recipes) - 6} 条配方"
                more_surf = self.font_small.render(more_text, True, (120, 120, 120))
                screen.blit(more_surf, (px + 25, curr_y))
                curr_y += 20
            
            curr_y += 10
        else:
            # 没有配方的建筑
            no_recipe = self.font_small.render("此建筑暂无可用配方", True, (120, 120, 120))
            screen.blit(no_recipe, (px + 20, curr_y))
            curr_y += 25
        
        # ═══ 分隔线 ═══
        pygame.draw.line(screen, (100, 80, 50), (px + 20, curr_y), (px + panel_w - 20, curr_y), 1)
        curr_y += 15
        
        # ═══ 玩家势力状态 ═══
        player_org = getattr(player, 'org_id', None)
        can_occupy = False
        occupy_reason = ""
        
        if player_org and player_org != 'NONE':
            player_org_data = ORGANIZATIONS.get(player_org, {})
            player_org_name = player_org_data.get('name', player_org)
            
            player_org_surf = self.font_ui.render(f"你的势力: {player_org_name}", True, (100, 200, 100))
            screen.blit(player_org_surf, (px + 20, curr_y))
            curr_y += 28
            
            # 判断是否可以占领
            if control_point:
                if controller_org == player_org:
                    occupy_reason = "已是我方控制"
                elif control_point.difficulty > 3:
                    # 高难度需要更多条件（这里简化为功勋）
                    player_merit = getattr(player, 'org_merit', 0)
                    if player_merit < 50:
                        occupy_reason = f"功勋不足（需要50，当前{player_merit}）"
                    else:
                        can_occupy = True
                else:
                    can_occupy = True
            else:
                occupy_reason = "非战略要地"
        else:
            no_org_surf = self.font_ui.render("你尚未加入任何势力", True, (200, 150, 100))
            screen.blit(no_org_surf, (px + 20, curr_y))
            curr_y += 28
            occupy_reason = "未加入势力"
        
        curr_y += 10
        
        # ═══ 按钮区域 ═══
        occupy_clicked = False
        close_clicked = False
        
        # 占领按钮
        if control_point:
            btn_occupy_rect = pygame.Rect(px + 30, curr_y, 160, 40)
            
            if can_occupy:
                btn_hover = btn_occupy_rect.collidepoint(mx, my)
                btn_color = (80, 150, 80) if btn_hover else (60, 120, 60)
                
                pygame.draw.rect(screen, btn_color, btn_occupy_rect, border_radius=5)
                pygame.draw.rect(screen, (100, 200, 100), btn_occupy_rect, 2, border_radius=5)
                
                occupy_text = self.font_ui.render("战 占领此地", True, (255, 255, 255))
                screen.blit(occupy_text, (btn_occupy_rect.centerx - occupy_text.get_width() // 2,
                                          btn_occupy_rect.centery - occupy_text.get_height() // 2))
                
                if click_event and btn_hover:
                    occupy_clicked = True
            else:
                # 不可占领 - 灰色按钮
                pygame.draw.rect(screen, (60, 60, 60), btn_occupy_rect, border_radius=5)
                pygame.draw.rect(screen, (80, 80, 80), btn_occupy_rect, 2, border_radius=5)
                
                occupy_text = self.font_ui.render("战 占领此地", True, (100, 100, 100))
                screen.blit(occupy_text, (btn_occupy_rect.centerx - occupy_text.get_width() // 2,
                                          btn_occupy_rect.centery - occupy_text.get_height() // 2))
                
                # 显示原因
                reason_surf = self.font_small.render(occupy_reason, True, (200, 150, 100))
                screen.blit(reason_surf, (px + 30, curr_y + 45))
        
        # 关闭按钮
        btn_close_rect = pygame.Rect(px + panel_w - 190, curr_y, 160, 40)
        btn_close_hover = btn_close_rect.collidepoint(mx, my)
        close_color = (150, 100, 60) if btn_close_hover else (120, 80, 50)
        
        pygame.draw.rect(screen, close_color, btn_close_rect, border_radius=5)
        pygame.draw.rect(screen, (200, 180, 150), btn_close_rect, 2, border_radius=5)
        
        close_text = self.font_ui.render("关闭", True, (255, 255, 255))
        screen.blit(close_text, (btn_close_rect.centerx - close_text.get_width() // 2,
                                 btn_close_rect.centery - close_text.get_height() // 2))
        
        if click_event and btn_close_hover:
            close_clicked = True
        
        return close_clicked, occupy_clicked

    # ═══════════════════════════════════════════════════════════════════
    # 【新增】江湖传闻面板 - 显示当前流传的传闻
    # ═══════════════════════════════════════════════════════════════════
    def draw_rumor_panel(self, screen, mx, my, click_event):
        """
        绘制江湖传闻面板 - 玩家可以在此了解最近发生的事件
        在酒馆或与NPC交谈时可查看
        """
        from src.rumor_system import get_rumor_system, RumorType
        
        rumor_sys = get_rumor_system()
        
        # 1. 全屏遮罩
        s = pygame.Surface((self.screen_w, self.screen_h))
        s.set_alpha(245)
        s.fill((15, 15, 20))
        screen.blit(s, (0, 0))
        
        # 2. 面板主体
        cx, cy = 150, 80
        cw, ch = self.screen_w - 300, self.screen_h - 160
        pygame.draw.rect(screen, (40, 38, 35), (cx, cy, cw, ch), border_radius=10)
        pygame.draw.rect(screen, (180, 150, 100), (cx, cy, cw, ch), 2, border_radius=10)
        
        # 3. 标题
        title = self.font_big.render("══ 江湖传闻 ══", True, (255, 215, 100))
        screen.blit(title, (cx + cw//2 - title.get_width()//2, cy + 15))
        
        subtitle = self.font_small.render("街头巷尾，人们都在谈论这些事...", True, (150, 150, 150))
        screen.blit(subtitle, (cx + cw//2 - subtitle.get_width()//2, cy + 55))
        
        pygame.draw.line(screen, (100, 90, 70), (cx + 30, cy + 85), (cx + cw - 30, cy + 85))
        
        # 4. 传闻列表
        rumors = rumor_sys.get_recent_rumors(count=8)
        
        curr_y = cy + 100
        
        if not rumors:
            empty_text = self.font_ui.render("最近江湖上风平浪静，没什么传闻...", True, (120, 120, 120))
            screen.blit(empty_text, (cx + cw//2 - empty_text.get_width()//2, curr_y + 50))
        else:
            # 传闻类型对应的图标和颜色（使用文字替代emoji）
            rumor_styles = {
                RumorType.COMBAT_VICTORY: ("胜", (150, 200, 150)),
                RumorType.COMBAT_DEFEAT: ("败", (200, 150, 150)),
                RumorType.KILLED_NPC: ("杀", (255, 80, 80)),
                RumorType.TRADE_EXPENSIVE: ("财", (255, 215, 0)),
                RumorType.BEFRIEND: ("友", (100, 200, 255)),
                RumorType.MAKE_ENEMY: ("敌", (255, 150, 50)),
                RumorType.ORG_TASK_COMPLETE: ("功", (100, 255, 150)),
                RumorType.ORG_PROMOTION: ("升", (255, 215, 0)),
                RumorType.BOUNTY_POSTED: ("悬", (255, 100, 100)),
                RumorType.BOUNTY_CANCELLED: ("消", (150, 255, 150)),
                RumorType.THEFT_SUCCESS: ("窃", (200, 150, 100)),
                RumorType.THEFT_CAUGHT: ("捕", (255, 100, 100)),
                RumorType.HELP_NPC: ("助", (255, 150, 200)),
                RumorType.BETRAY: ("叛", (150, 50, 50)),
            }
            
            for i, rumor in enumerate(reversed(rumors)):  # 最新的在前
                # 背景条
                row_rect = pygame.Rect(cx + 25, curr_y, cw - 50, 45)
                bg_color = (50, 48, 45) if i % 2 == 0 else (45, 43, 40)
                pygame.draw.rect(screen, bg_color, row_rect, border_radius=5)
                
                # 图标和颜色
                icon, color = rumor_styles.get(rumor.rumor_type, ("○", (180, 180, 180)))
                
                # 新鲜度标记
                days_ago = rumor_sys.current_day - rumor.created_day
                if days_ago == 0:
                    fresh_tag = "[今日]"
                    fresh_color = (255, 215, 0)
                elif days_ago == 1:
                    fresh_tag = "[昨日]"
                    fresh_color = (200, 180, 100)
                else:
                    fresh_tag = f"[{days_ago}日前]"
                    fresh_color = (120, 120, 120)
                
                fresh_surf = self.font_small.render(fresh_tag, True, fresh_color)
                screen.blit(fresh_surf, (cx + 35, curr_y + 5))
                
                # 图标
                icon_surf = self.font_ui.render(icon, True, color)
                screen.blit(icon_surf, (cx + 100, curr_y + 10))
                
                # 传闻内容
                rumor_text = rumor.get_text()
                if len(rumor_text) > 40:
                    rumor_text = rumor_text[:40] + "..."
                text_surf = self.font_ui.render(rumor_text, True, color)
                screen.blit(text_surf, (cx + 130, curr_y + 12))
                
                # 传播情况
                spread_text = f"已传播: {rumor.spread_count}/{rumor.spread_range}人"
                spread_surf = self.font_small.render(spread_text, True, (100, 100, 100))
                screen.blit(spread_surf, (cx + cw - 130, curr_y + 15))
                
                curr_y += 50
        
        # 5. 底部说明
        pygame.draw.line(screen, (100, 90, 70), (cx + 30, cy + ch - 70), (cx + cw - 30, cy + ch - 70))
        
        hint_text = "传闻会在NPC之间传播，影响他们对你的看法"
        hint_surf = self.font_small.render(hint_text, True, (130, 130, 130))
        screen.blit(hint_surf, (cx + cw//2 - hint_surf.get_width()//2, cy + ch - 60))
        
        # 6. 关闭按钮
        btn_close_rect = pygame.Rect((self.screen_w - 120) // 2, cy + ch - 35, 120, 35)
        btn_hover = btn_close_rect.collidepoint(mx, my)
        col = (180, 120, 60) if btn_hover else (120, 80, 40)
        
        pygame.draw.rect(screen, col, btn_close_rect, border_radius=5)
        pygame.draw.rect(screen, (200, 180, 150), btn_close_rect, 1, border_radius=5)
        txt_close = self.font_ui.render("关闭", True, (255, 255, 255))
        screen.blit(txt_close, (btn_close_rect.centerx - txt_close.get_width()//2, 
                                btn_close_rect.centery - txt_close.get_height()//2))

        if click_event and btn_hover:
            return True
        return False

    def draw_faction_view(self, screen, faction_war, player, mx, my, click_event, all_npcs=None):
        """
        【阶段4】绘制势力关系面板（增强版）
        显示：控制点状态、组织关系、战争情况、玩家势力声望
        增强：显示势力首领、规模、成员数量
        支持标签页：势力关系 | 门派任务
        """
        from src.data.character_seeds import ORGANIZATIONS
        from src.entities.npc import POWER_COLORS
        
        # 存储NPC列表供内部使用
        self.all_cards = all_npcs or []
        
        # 初始化标签页状态
        if not hasattr(self, '_faction_view_tab'):
            self._faction_view_tab = 0  # 0=势力关系, 1=门派任务
        if not hasattr(self, '_selected_org_for_task'):
            self._selected_org_for_task = None  # 当前选中的组织
        
        # 1. 全屏半透明遮罩
        s = pygame.Surface((self.screen_w, self.screen_h))
        s.set_alpha(245)
        s.fill((20, 20, 25))
        screen.blit(s, (0, 0))

        # 2. 面板主体
        cx, cy = 80, 40
        cw, ch = self.screen_w - 160, self.screen_h - 80
        pygame.draw.rect(screen, (35, 35, 40), (cx, cy, cw, ch), border_radius=10)
        pygame.draw.rect(screen, (180, 150, 100), (cx, cy, cw, ch), 2, border_radius=10)

        # 3. 标题 + 标签页按钮
        title = self.font_big.render("══ 势力纵横 ══", True, (255, 200, 100))
        screen.blit(title, (cx + 20, cy + 15))
        
        # 标签页按钮
        tab_names = ["势力关系", "门派任务"]
        tab_x = cx + cw - 280
        tab_rects = []
        for i, tab_name in enumerate(tab_names):
            tab_rect = pygame.Rect(tab_x + i * 130, cy + 12, 120, 30)
            tab_rects.append(tab_rect)
            
            is_active = (self._faction_view_tab == i)
            is_hover = tab_rect.collidepoint(mx, my)
            
            if is_active:
                col = (100, 80, 50)
                border_col = (255, 200, 100)
            elif is_hover:
                col = (70, 60, 45)
                border_col = (180, 150, 100)
            else:
                col = (50, 45, 40)
                border_col = (120, 100, 80)
            
            pygame.draw.rect(screen, col, tab_rect, border_radius=5)
            pygame.draw.rect(screen, border_col, tab_rect, 1, border_radius=5)
            
            text_col = (255, 230, 180) if is_active else (180, 160, 130)
            tab_surf = self.font_ui.render(tab_name, True, text_col)
            screen.blit(tab_surf, (tab_rect.centerx - tab_surf.get_width()//2, 
                                   tab_rect.centery - tab_surf.get_height()//2))
            
            # 点击切换标签
            if click_event and is_hover:
                self._faction_view_tab = i
                click_event = False  # 消费点击事件
        
        # 根据当前标签页绘制不同内容
        if self._faction_view_tab == 1:
            # 门派任务标签页
            return self._draw_org_task_tab(screen, player, mx, my, click_event, cx, cy, cw, ch)
        
        # ═══════════════════════════════════════════════════════════════
        # 左侧：控制点列表
        # ═══════════════════════════════════════════════════════════════
        left_x = cx + 30
        curr_y = cy + 70
        
        header1 = self.font_ui.render("【战略要地】", True, (255, 215, 100))
        screen.blit(header1, (left_x, curr_y))
        curr_y += 35
        
        # 绘制控制点
        for pid, point in list(faction_war.control_points.items())[:10]:  # 限制显示数量
            info = point.get_info()
            
            # 控制者颜色
            ctrl_org_id = point.controller_org_id
            if ctrl_org_id:
                org_data = ORGANIZATIONS.get(ctrl_org_id, {})
                power_type = org_data.get('power_type', '民')
                ctrl_color = POWER_COLORS.get(power_type, (150, 150, 150))
                ctrl_name = info['controller']
            else:
                ctrl_color = (100, 100, 100)
                ctrl_name = "无主"
            
            # 地点名 + 控制者
            point_text = f"● {info['name']}"
            point_surf = self.font_ui.render(point_text, True, (220, 220, 220))
            screen.blit(point_surf, (left_x, curr_y))
            
            # 控制者标签（带颜色）
            ctrl_surf = self.font_small.render(f"[{ctrl_name}]", True, ctrl_color)
            screen.blit(ctrl_surf, (left_x + 120, curr_y + 2))
            
            # 控制强度条
            bar_x = left_x + 200
            bar_w = 80
            bar_h = 10
            pygame.draw.rect(screen, (50, 50, 50), (bar_x, curr_y + 5, bar_w, bar_h))
            fill_w = int(bar_w * info['control_strength'] / 100)
            pygame.draw.rect(screen, ctrl_color, (bar_x, curr_y + 5, fill_w, bar_h))
            
            # 每日收益
            income_surf = self.font_small.render(f"+{info['daily_income']}/日", True, (150, 200, 100))
            screen.blit(income_surf, (bar_x + bar_w + 10, curr_y + 2))
            
            # 争夺中标记
            if info['contested']:
                contest_surf = self.font_small.render("战争夺中", True, (255, 80, 80))
                screen.blit(contest_surf, (bar_x + bar_w + 60, curr_y + 2))
            
            curr_y += 28
        
        # ═══════════════════════════════════════════════════════════════
        # 中部：组织列表（增强版）
        # ═══════════════════════════════════════════════════════════════
        mid_x = cx + cw // 3 + 20
        curr_y = cy + 70
        
        header2 = self.font_ui.render("【各方势力】", True, (100, 200, 255))
        screen.blit(header2, (mid_x, curr_y))
        curr_y += 35
        
        # 获取所有NPC用于统计势力信息
        all_npcs = getattr(self, 'all_cards', [])
        if not all_npcs and hasattr(faction_war, '_all_cards'):
            all_npcs = faction_war._all_cards
        
        # 按势力类型分组显示
        for org_id, org_data in list(ORGANIZATIONS.items())[:10]:
            power_type = org_data.get('power_type', '民')
            power_color = POWER_COLORS.get(power_type, (150, 150, 150))
            org_name = org_data.get('name', org_id)
            
            # 统计组织成员信息
            org_members = [npc for npc in all_npcs 
                          if hasattr(npc, 'org_id') and npc.org_id == org_id
                          and getattr(npc, 'safety', 'NORMAL') != SAFETY_DEAD]
            member_count = len(org_members)
            
            # 找出首领（优先 org_role='LEADER'，其次 org_rank 最高）
            # 【修复】多重排序：LEADER 角色优先，再按 org_rank 排序
            leader = None
            leader_rank = -1
            leader_role_priority = 0  # LEADER 角色给予额外优先级
            
            for npc in org_members:
                rank = getattr(npc, 'org_rank', 0) or 0
                role = getattr(npc, 'org_role', '') or ''
                role_priority = 100 if role == 'LEADER' else 0  # LEADER 角色加100优先级
                
                # 综合分数 = 角色优先级 + 等级
                score = role_priority + rank
                
                if score > leader_rank:
                    leader_rank = score
                    leader = npc
            
            leader_name = leader.name if leader else "不明"
            
            # 第一行：组织名 + 首领
            org_surf = self.font_ui.render(f"[{power_type}] {org_name}", True, power_color)
            screen.blit(org_surf, (mid_x, curr_y))
            
            leader_surf = self.font_small.render(f"首领:{leader_name}", True, (255, 220, 150))
            screen.blit(leader_surf, (mid_x + 160, curr_y + 2))
            
            # 第二行：规模 + 据点 + 日收入
            curr_y += 22
            ctrl_count = len(faction_war.get_org_controlled_points(org_id))
            daily = faction_war.daily_income_record.get(org_id, 0)
            
            # 规模描述
            if member_count >= 10:
                scale_desc = "大型"
                scale_color = (255, 200, 100)
            elif member_count >= 5:
                scale_desc = "中型"
                scale_color = (200, 200, 150)
            elif member_count >= 2:
                scale_desc = "小型"
                scale_color = (150, 150, 150)
            else:
                scale_desc = "微型"
                scale_color = (120, 120, 120)
            
            stats_surf = self.font_small.render(
                f"  规模:{scale_desc}({member_count}人) 据点:{ctrl_count} 日入:{daily}铜", 
                True, scale_color
            )
            screen.blit(stats_surf, (mid_x, curr_y))
            
            # 玩家与该势力的声望
            if player:
                standing = player.org_reputation.get(org_id, 0)
                # 根据声望值显示颜色和描述
                if standing >= 50:
                    rep_color = (100, 255, 100)
                    rep_desc = "友善"
                elif standing >= 20:
                    rep_color = (150, 220, 150)
                    rep_desc = "好感"
                elif standing >= -20:
                    rep_color = (180, 180, 180)
                    rep_desc = "中立"
                elif standing >= -50:
                    rep_color = (255, 180, 100)
                    rep_desc = "警惕"
                else:
                    rep_color = (255, 80, 80)
                    rep_desc = "敌视"
                
                rep_surf = self.font_small.render(f"[你:{rep_desc}{standing:+d}]", True, rep_color)
                screen.blit(rep_surf, (mid_x + 330, curr_y))
            
            curr_y += 26
        
        # ═══════════════════════════════════════════════════════════════
        # 右侧：外交关系 & 战争状态
        # ═══════════════════════════════════════════════════════════════
        right_x = cx + 2 * cw // 3 + 20
        curr_y = cy + 70
        
        header3 = self.font_ui.render("【敌友态势】", True, (255, 150, 150))
        screen.blit(header3, (right_x, curr_y))
        curr_y += 35
        
        # 显示战争状态
        if faction_war.relation_manager.active_wars:
            war_title = self.font_small.render("═ 当前战争 ═", True, (255, 80, 80))
            screen.blit(war_title, (right_x, curr_y))
            curr_y += 22
            
            for war_key, war_data in list(faction_war.relation_manager.active_wars.items())[:5]:
                org_a, org_b = war_key
                name_a = ORGANIZATIONS.get(org_a, {}).get('name', org_a)
                name_b = ORGANIZATIONS.get(org_b, {}).get('name', org_b)
                war_surf = self.font_small.render(f"[战] {name_a} vs {name_b}", True, (255, 100, 100))
                screen.blit(war_surf, (right_x, curr_y))
                curr_y += 20
        else:
            peace_surf = self.font_small.render("天下太平，暂无战事", True, (100, 200, 100))
            screen.blit(peace_surf, (right_x, curr_y))
            curr_y += 25
        
        curr_y += 15
        
        # 显示敌对关系（关系值 < -30）
        hostile_title = self.font_small.render("═ 敌对势力 ═", True, (255, 180, 80))
        screen.blit(hostile_title, (right_x, curr_y))
        curr_y += 22
        
        hostile_count = 0
        for (org_a, org_b), val in list(faction_war.relation_manager.relations.items())[:20]:
            if val < -30:
                name_a = ORGANIZATIONS.get(org_a, {}).get('name', org_a)
                name_b = ORGANIZATIONS.get(org_b, {}).get('name', org_b)
                
                # 颜色根据敌对程度
                if val < -80:
                    rel_color = (255, 50, 50)
                    rel_text = "死敌"
                elif val < -60:
                    rel_color = (255, 100, 80)
                    rel_text = "交战"
                else:
                    rel_color = (255, 180, 100)
                    rel_text = "敌对"
                
                rel_surf = self.font_small.render(f"{name_a} ↔ {name_b}: {rel_text}({val:+d})", True, rel_color)
                screen.blit(rel_surf, (right_x, curr_y))
                curr_y += 18
                hostile_count += 1
                if hostile_count >= 8: break
        
        if hostile_count == 0:
            none_surf = self.font_small.render("暂无明显敌对", True, (150, 150, 150))
            screen.blit(none_surf, (right_x, curr_y))

        # ═══════════════════════════════════════════════════════════════
        # 关闭按钮
        # ═══════════════════════════════════════════════════════════════
        btn_close_rect = pygame.Rect((self.screen_w - 120) // 2, cy + ch - 55, 120, 40)
        btn_hover = btn_close_rect.collidepoint(mx, my)
        col = (180, 120, 60) if btn_hover else (120, 80, 40)
        
        pygame.draw.rect(screen, col, btn_close_rect, border_radius=5)
        pygame.draw.rect(screen, (200, 180, 150), btn_close_rect, 1, border_radius=5)
        txt_close = self.font_ui.render("关闭", True, (255, 255, 255))
        screen.blit(txt_close, (btn_close_rect.centerx - txt_close.get_width()//2, 
                                btn_close_rect.centery - txt_close.get_height()//2))

        if click_event and btn_hover:
            return True
        return False
