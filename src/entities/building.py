# --- src/entities/building.py ---
import pygame
import traceback
from src.definitions import *
from .base import CardBase
from src.data.building_defs import BUILDING_DB
from src.utils import log_game_event

# 每种建筑对应的NPC干活文本（≤3字）
BUILDING_WORK_TEXT = {
    'FARM':       '耕种中',
    'MARKET':     '叫卖中',
    'WORKSHOP':   '打铁中',
    'SCHOOL':     '苦读中',
    'BARRACKS':   '操练中',
    'HOUSE':      '休息中',
    'GRANARY':    '搬运中',
    'INN':        '掌柜中',
    'TEMPLE':     '诵经中',
    'THEATER':    '献艺中',
    'GOV_OFFICE': '审案中',
    'CLINIC':     '问诊中',
    'HOSPITAL':   '问诊中',
    'CAMPFIRE':   '烹饪中',
    'BUSH':       '采摘中',
    'TREE':       '伐木中',
}

class Building(CardBase):
    # 建筑位移警告阈值：超过此值时打印调用栈
    BUILDING_MOVE_WARN_THRESHOLD = 5
    
    def __init__(self, x, y, b_type):
        conf = BUILDING_DB.get(b_type, BUILDING_DB['GRANARY'])
        super().__init__(x, y, CARD_W, CARD_H, COLOR_BUILDING_CARD)
        self.name = conf.get('name', '建筑')
        self.card_type = CARD_TYPE_BUILDING
        self.building_type = b_type 
        self.resource_count = 0
        self.max_resource = 99
        self.popup_text = None
        self.popup_timer = 0
        # 自动化相关（work_time已废弃，统一由recipes.csv的duration驱动）
        self.auto_max = 0
        self.auto_progress = 0
        self.auto_mode = False
        # --- 燃料系统 ---
        self.fuel_time = 0 
        if conf.get('is_heat_source'):
            self.fuel_time = 600 # 初始给一点燃料 (10秒)
        self.max_fuel = conf.get('fuel_max', 1000)
        # 建筑库存：供市场/官府存放物品（{item_id: count}）
        self.inventory = {}
        # 最大库存容量（每种物品）
        self.max_inventory_per_item = conf.get('max_inventory', 99)
        
        # 【阶段2】加载初始库存
        initial_inv = conf.get('initial_inventory', {})
        for item_id, count in initial_inv.items():
            self.inventory[item_id] = count

    def set_pos(self, x, y, reason=None):
        """
        覆盖父类的 set_pos 方法，添加建筑位移调试。
        建筑通常不应该移动，任何移动都需要记录。
        """
        import math
        
        # 计算位移距离
        old_cx = self.rect.centerx
        old_cy = self.rect.centery
        
        # 调用父类方法执行实际位移
        super().set_pos(x, y, reason)
        
        new_cx = self.rect.centerx
        new_cy = self.rect.centery
        
        # 计算位移量
        dist = math.hypot(new_cx - old_cx, new_cy - old_cy)
        
        # 建筑只要发生移动就打印调用栈（阈值很低）
        if dist >= Building.BUILDING_MOVE_WARN_THRESHOLD:
            stack_lines = traceback.format_stack()
            # 只取最近几层调用栈，过滤掉过深的框架调用
            relevant_stack = ''.join(stack_lines[-8:-1])  # 跳过当前函数
            log_game_event(
                f"[BUILDING_MOVE!] 建筑 '{self.name}' 发生位移!\n"
                f"  位置变化: ({old_cx},{old_cy}) → ({new_cx},{new_cy})\n"
                f"  位移距离: {dist:.1f}px\n"
                f"  原因: {reason}\n"
                f"  调用栈:\n{relevant_stack}"
            )

    def show_popup(self, text):
        self.popup_text = text
        self.popup_timer = 60


    def draw(self, screen, font):
        # 1. 绘制卡牌背景
        self.draw_card_bg(screen, font)
        
        center_y = self.rect.centery
        # 使用新的图标系统
        from src.data.building_defs import get_building_icon
        icon_txt, color = get_building_icon(self.building_type)

        try:
            font_icon = pygame.font.Font(None, 40)
            surf = font_icon.render(icon_txt, True, color)
            screen.blit(surf, (self.rect.centerx - surf.get_width()//2, center_y - 15))
        except:
            pygame.draw.circle(screen, color, (self.rect.centerx, center_y), 15)

        # 状态显示 ── 展示库存摘要
        short_map = {
            '谷物': '粮', '棉袄': '棉', '铜币': '钱', 
            '精制器物': '器', '布料': '布', '铁器': '铁',
            '书卷': '书'
        }
        
        # 市场/工坊/农场等有库存的建筑都显示库存
        if self.inventory and self.building_type in ['MARKET', 'WORKSHOP', 'FARM', 'SCHOOL']:
            parts = []
            for k, v in list(self.inventory.items())[:3]:
                if v > 0:
                    label = short_map.get(k, k[:1])
                    parts.append(f"{label}:{v}")
            hint = " ".join(parts) if parts else "空仓"
        else:
            hint = "空闲"
            if self.resource_count > 0:
                hint = f"存:{self.resource_count}"
            elif self.stack_child:
                hint = "工作中" if self.stack_child.is_working else "就绪"
            
        s = font.render(hint, True, (50, 50, 50))
        screen.blit(s, (self.rect.centerx - s.get_width()//2, self.rect.bottom - 20))
            
        if self.popup_timer > 0:
            self.popup_timer -= 1
            y_off = 30 - (self.popup_timer / 2) 
            pop = font.render(self.popup_text, True, (50, 200, 50))
            screen.blit(pop, (self.rect.centerx - pop.get_width()//2, self.rect.top - y_off))
        
        # [新增] 绘制火焰/燃料
        conf = BUILDING_DB.get(self.building_type, {})
        if conf.get('is_heat_source'):
            if self.fuel_time > 0:
                self.fuel_time -= 1 # 燃烧消耗
                
                # 画个简单的火焰圆圈
                import random
                radius = 10 + random.randint(0, 5)
                color = (255, 100 + random.randint(0, 100), 0)
                pygame.draw.circle(screen, color, self.rect.center, radius)
                
                # 画燃料条
                pct = self.fuel_time / self.max_fuel
                bar_rect = pygame.Rect(self.rect.x + 5, self.rect.bottom - 10, self.rect.width - 10, 4)
                pygame.draw.rect(screen, (50,0,0), bar_rect)
                pygame.draw.rect(screen, (255,150,0), (bar_rect.x, bar_rect.y, bar_rect.width * pct, bar_rect.height))
            else:
                # 熄灭提示
                txt = font.render("熄灭", True, (100, 100, 100))
                screen.blit(txt, (self.rect.centerx - txt.get_width()//2, self.rect.centery))
        
        # 【阶段4】绘制势力控制标记
        self._draw_control_flag(screen, font)
    
    def _draw_control_flag(self, screen, font):
        """绘制建筑势力控制旗帜/标记"""
        from src.faction_war_system import get_faction_war_system
        from src.data.organization_defs import ORGANIZATIONS
        from src.entities.npc import POWER_COLORS
        
        faction_war = get_faction_war_system()
        
        # 查找此建筑对应的控制点
        control_point = None
        for cp in faction_war.control_points.values():
            if cp.building_ref is self:
                control_point = cp
                break
        
        if not control_point:
            return  # 此建筑不是控制点
        
        # 获取控制者信息
        controller_org = control_point.controller_org_id
        if controller_org:
            org_data = ORGANIZATIONS.get(controller_org, {})
            power_type = org_data.get('power_type', '民')
            org_color = POWER_COLORS.get(power_type, (150, 150, 150))
            org_name = org_data.get('name', controller_org)[:2]  # 取前两字
        else:
            org_color = (80, 80, 80)
            org_name = "?"
        
        # 绘制旗帜（建筑左上角）
        flag_x = self.rect.left + 3
        flag_y = self.rect.top + 3
        
        # 旗杆
        pygame.draw.line(screen, (60, 40, 30), (flag_x, flag_y), (flag_x, flag_y + 25), 2)
        
        # 旗帜背景（根据控制强度调整大小和颜色饱和度）
        strength = control_point.control_strength / 100
        flag_w = int(20 * (0.5 + 0.5 * strength))
        flag_h = int(14 * (0.5 + 0.5 * strength))
        
        # 调整颜色亮度
        r, g, b = org_color
        adjusted_color = (
            int(r * (0.5 + 0.5 * strength)),
            int(g * (0.5 + 0.5 * strength)),
            int(b * (0.5 + 0.5 * strength))
        )
        
        pygame.draw.rect(screen, adjusted_color, (flag_x + 2, flag_y, flag_w, flag_h))
        
        # 边框（争夺中时闪烁红色）
        if control_point.contested:
            import time
            blink = int(time.time() * 4) % 2 == 0
            border_color = (255, 50, 50) if blink else (100, 50, 50)
        else:
            border_color = (30, 30, 30)
        pygame.draw.rect(screen, border_color, (flag_x + 2, flag_y, flag_w, flag_h), 1)
        
        # 组织名缩写（仅在旗帜足够大时显示）
        if flag_w >= 16 and controller_org:
            try:
                name_surf = font.render(org_name[0], True, (255, 255, 255))
                screen.blit(name_surf, (flag_x + 4, flag_y + 1))
            except:
                pass
      