# --- src/ui/base.py ---
import pygame
from src.definitions import *
from src.ui.constants import TRANS_MAP

class UIBase:
    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self._init_fonts()

    def _init_fonts(self):
        print("[System] 正在初始化字体 (SysFont模式)...")
        # 优先列表：微软雅黑(Windows), 苹方(Mac), 文泉驿(Linux), Arial(兜底)
        # SysFont 的第一个参数是字体名列表或逗号分隔的字符串
        font_names = "microsoftyahei,simhei,pingfangsc,notosanscjk,arial"
        
        try:
            # SysFont 会自动处理 .ttc 和系统路径问题
            # 地图卡牌使用的字体（保持原大小）
            self.font_sys = pygame.font.SysFont(font_names, 14) 
            
            # 二级面板使用的字体（加大以提高可读性）
            # font_ui: 中等字体  16 -> 20
            # font_big: 标题字体 24 -> 28
            # font_small: 小字体 12 -> 16
            self.font_ui = pygame.font.SysFont(font_names, 20)
            self.font_big = pygame.font.SysFont(font_names, 28, bold=True)
            self.font_small = pygame.font.SysFont(font_names, 16)
            print("[System] 字体初始化完成")
        except Exception as e:
            print(f"[System] 字体加载异常: {e}")
            # 最后的保底
            self.font_sys = pygame.font.Font(None, 16)
            self.font_ui = pygame.font.Font(None, 24)
            self.font_big = pygame.font.Font(None, 32)
            self.font_small = pygame.font.Font(None, 18)


    def _get_text(self, key):
        return TRANS_MAP.get(key, key)

    def draw_button(self, screen, rect, text, font, mx, my, base_color=COLOR_BTN, border_col=(150,150,150), disabled=False):
        is_hover = rect.collidepoint(mx, my) and not disabled
        if disabled:
            color = COLOR_BTN_DISABLED
            border_col = (80, 50, 50)
            txt_color = (100, 100, 100)
        else:
            color = COLOR_BTN_HOVER if is_hover else base_color
            txt_color = COLOR_TEXT
        pygame.draw.rect(screen, color, rect, border_radius=5)
        pygame.draw.rect(screen, border_col, rect, 2, border_radius=5)
        txt = font.render(text, True, txt_color)
        screen.blit(txt, (rect.centerx - txt.get_width()//2, rect.centery - txt.get_height()//2))
        return is_hover

    def parse_cost_from_effect(self, effect_str, npc_name="当事人", partner_name="对方"):
        display_items = []
        if not effect_str: return display_items
        parts = effect_str.split(';')
        
        for part in parts:
            if not part: continue
            segments = part.split(':')
            if len(segments) < 3: continue
            
            target, attr, val = segments[0], segments[1], segments[2]
            txt = ""
            color = COLOR_TEXT 
            
            attr_cn = self._get_text(attr)
            val_cn = self._get_text(val)

            if target == 'PLAYER':
                if attr in ['Money', 'Fame', 'food', 'sanity']:
                    try:
                        v = int(val)
                        if v > 0:
                            txt = f"玩家: +{v} {attr_cn}"
                            color = COLOR_COST_GOOD
                        else:
                            txt = f"玩家: {v} {attr_cn}"
                            color = COLOR_COST_BAD
                    except: pass
                elif attr == 'AddTag':
                    txt = f"玩家获得名号: [{val_cn}]"
                    color = (255, 100, 255)
            else:
                display_name = npc_name if target == 'SELF' else partner_name
                if attr == 'money':
                    v = int(val)
                    txt = f"{display_name}: {'+' if v>0 else ''}{v} 铜"
                    color = COLOR_COST_GOOD if v > 0 else COLOR_COST_BAD
                elif attr == 'is_follower' and val == 'True':
                    txt = f"{display_name}: 纳为门客"
                    color = COLOR_HIGHLIGHT
                elif attr == 'freedom' and val == 'SLAVE':
                    txt = f"{display_name}: 沦为奴籍"
                    color = COLOR_COST_BAD
                elif attr == 'safety' and val == 'DANGER':
                    txt = f"{display_name}: 遭遇追杀"
                    color = COLOR_COST_BAD
                elif attr == 'eco_status' and val == 'POOR':
                    txt = f"{display_name}: 倾家荡产"
                    color = COLOR_COST_BAD
                else:
                    txt = f"{display_name}: {val_cn}"
                    color = COLOR_TAG_NEUTRAL
                    
            if txt: display_items.append((txt, color))
        return display_items

    def check_requirements(self, player, req_str, all_npcs):
        if not req_str: return True, ""
        reqs = req_str.split(';')
        for r in reqs:
            parts = r.split(':')
            if len(parts) < 2: continue
            r_type, r_val = parts[0], parts[1]
            val_cn = self._get_text(r_val)

            if r_type == 'MONEY':
                val = int(r_val)
                if player.money < val: return False, f"需铜钱 {val}"
            elif r_type == 'FAME':
                val = int(r_val)
                if r_val.startswith('-'):
                    if player.fame > val: return False, f"需恶名昭著({val})"
                else:
                    if player.fame < val: return False, f"需威望 {val}"
            elif r_type == 'TAG':
                if r_val not in player.tags: return False, f"需名号: {val_cn}"
            elif r_type == 'FOLLOWER':
                has_it = False
                for npc in all_npcs:
                    if getattr(npc, 'is_follower', False):
                        if npc.job == r_val or r_val in getattr(npc, 'tags', []):
                            has_it = True
                            break
                if not has_it: return False, f"需麾下有【{val_cn}】"
        return True, ""

    def draw_close_button(self, screen, panel_rect, mx, my, click_event=False, offset=(10, 10), size=30):
        """
        在面板右上角绘制统一风格的关闭按钮（X符号）
        
        Args:
            screen: pygame屏幕对象
            panel_rect: 面板的Rect区域
            mx, my: 鼠标位置
            click_event: 是否有鼠标点击事件
            offset: 按钮距离右上角的偏移 (右偏移, 上偏移)
            size: 按钮尺寸
        
        Returns:
            bool: 是否点击了关闭按钮
        """
        btn_x = panel_rect.right - offset[0] - size
        btn_y = panel_rect.top + offset[1]
        btn_rect = pygame.Rect(btn_x, btn_y, size, size)
        
        is_hover = btn_rect.collidepoint(mx, my)
        
        # 绘制圆形/圆角矩形背景
        if is_hover:
            bg_color = (200, 80, 80)  # 悬停时红色
        else:
            bg_color = (80, 70, 70)   # 默认深灰
        
        pygame.draw.rect(screen, bg_color, btn_rect, border_radius=6)
        pygame.draw.rect(screen, (150, 100, 100), btn_rect, 2, border_radius=6)
        
        # 绘制X符号
        x_color = (255, 255, 255) if is_hover else (200, 200, 200)
        padding = 8
        x1, y1 = btn_rect.left + padding, btn_rect.top + padding
        x2, y2 = btn_rect.right - padding, btn_rect.bottom - padding
        pygame.draw.line(screen, x_color, (x1, y1), (x2, y2), 3)
        pygame.draw.line(screen, x_color, (x2, y1), (x1, y2), 3)
        
        # 返回是否点击了关闭按钮
        return click_event and is_hover

    def draw_option_button(self, screen, rect, title, effect_str, req_str, player, mx, my, npc_name, partner_name, all_npcs):
        if not title: return False, False 
        
        is_possible, req_msg = self.check_requirements(player, req_str, all_npcs)
        base_color = COLOR_BTN
        if not is_possible: base_color = COLOR_BTN_DISABLED
        is_hover = rect.collidepoint(mx, my) and is_possible
        color = COLOR_BTN_HOVER if is_hover else base_color
        border_col = (150, 150, 150) if is_possible else (200, 50, 50)
        
        pygame.draw.rect(screen, color, rect, border_radius=8)
        pygame.draw.rect(screen, border_col, rect, 2, border_radius=8)
        
        title_col = (255, 230, 150) if is_possible else (150, 150, 150)
        title_surf = self.font_ui.render(title, True, title_col)
        screen.blit(title_surf, (rect.centerx - title_surf.get_width()//2, rect.y + 8))
        
        curr_y = rect.y + 35
        if not is_possible:
            req_surf = self.font_small.render(f"条件不足: {req_msg}", True, (255, 80, 80))
            screen.blit(req_surf, (rect.centerx - req_surf.get_width()//2, curr_y))
            curr_y += 16
        
        display_items = self.parse_cost_from_effect(effect_str, npc_name, partner_name)
        if display_items:
            for txt, txt_color in display_items:
                s = self.font_small.render(txt, True, txt_color)
                screen.blit(s, (rect.centerx - s.get_width()//2, curr_y))
                curr_y += 14
        return is_hover, is_possible