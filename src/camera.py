# --- src/camera.py ---
"""
摄像机系统：管理世界坐标与屏幕坐标之间的转换。
支持：
  1. 边缘滚动（鼠标接近屏幕边缘时自动移动视口）
  2. 小地图拖拽（拖动小地图内的视口矩形来跳转）
  3. 屏幕坐标 ↔ 世界坐标互转（供点击、AI 逻辑等使用）
"""
import pygame
from src.definitions import (
    SIDEBAR_W, TOPBAR_H,
    MINIMAP_W, MINIMAP_H, MINIMAP_MARGIN, MINIMAP_ALPHA,
    EDGE_SCROLL_ZONE, EDGE_SCROLL_SPEED,
    COLOR_BG, COLOR_CITY_GROUND, COLOR_WALL
)


class Camera:
    """
    属性：
        offset_x / offset_y  : 当前视口左上角在世界坐标中的位置
        world_w / world_h     : 世界总尺寸（逻辑坐标）
        view_w / view_h       : 可玩区域视口尺寸（屏幕宽-侧边栏, 屏幕高-顶部栏）
    """

    def __init__(self, screen_w: int, screen_h: int, world_w: int, world_h: int):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.world_w  = world_w
        self.world_h  = world_h

        # 可玩视口（去掉 UI 边框）
        self.view_w = screen_w - SIDEBAR_W
        self.view_h = screen_h - TOPBAR_H

        # 初始视口偏移（从世界左上角出发）
        self.offset_x = 0.0
        self.offset_y = 0.0

        # 小地图状态
        # 小地图放在侧边栏左侧，底部对齐屏幕底部留边距，避免与顶部按钮重叠
        self._mm_rect = pygame.Rect(
            screen_w - SIDEBAR_W - MINIMAP_W - MINIMAP_MARGIN,
            screen_h - MINIMAP_H - MINIMAP_MARGIN,
            MINIMAP_W,
            MINIMAP_H
        )
        self._mm_dragging = False       # 是否正在拖动小地图视口框
        self._mm_drag_offset = (0, 0)   # 拖拽起始偏移（相对视口框左上角）

        # 预渲染小地图底图（首帧由 world_map 绘制后更新）
        self._mm_surface = pygame.Surface((MINIMAP_W, MINIMAP_H), pygame.SRCALPHA)

        # 跟随模式：False = 自由视角（默认），True = 每帧软跟随玩家
        self.follow_player = False
        
        # 【新增】剧情锁定：锁定后禁止玩家边缘滚动、小地图拖拽
        self.story_locked = False
        
        # ═══════════════════════════════════════════════════════════════
        # 【新增】事件聚焦动画状态
        # ═══════════════════════════════════════════════════════════════
        self.event_focus_active = False     # 是否正在执行事件聚焦动画
        self.event_focus_target = None      # 目标世界坐标 (wx, wy)
        self.event_focus_timer = 0          # 动画计时器
        self.event_focus_duration = 45      # 动画持续帧数（约0.75秒）
        self.event_focus_start_offset = (0, 0)  # 动画开始时的视口偏移

    # ─────────────────────────────────────────────────────────────
    # 公开接口
    # ─────────────────────────────────────────────────────────────

    def resize(self, screen_w: int, screen_h: int):
        """窗口大小改变时重新计算"""
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.view_w = screen_w - SIDEBAR_W
        self.view_h = screen_h - TOPBAR_H
        self._mm_rect.x = screen_w - SIDEBAR_W - MINIMAP_W - MINIMAP_MARGIN
        self._mm_rect.y = screen_h - MINIMAP_H - MINIMAP_MARGIN
        self._clamp()

    def snap_to(self, wx: float, wy: float):
        """将视口中心直接跳到世界坐标 (wx, wy)，用于开局初始化。"""
        self.offset_x = wx - self.view_w / 2
        self.offset_y = wy - self.view_h / 2
        self._clamp()

    def world_to_screen(self, wx: float, wy: float):
        """世界坐标 → 屏幕坐标"""
        return wx - self.offset_x, wy - self.offset_y + TOPBAR_H

    def screen_to_world(self, sx: float, sy: float):
        """屏幕坐标 → 世界坐标（sy 需减去 TOPBAR_H）"""
        return sx + self.offset_x, sy - TOPBAR_H + self.offset_y

    def is_visible(self, rect: pygame.Rect, margin: int = 80) -> bool:
        """判断世界矩形是否在当前视口可见范围内（加 margin 作为渲染缓冲区）"""
        sx = rect.x - self.offset_x
        sy = rect.y - self.offset_y
        if sx + rect.width  + margin < 0:      return False
        if sy + rect.height + margin < 0:      return False
        if sx - margin > self.view_w:          return False
        if sy - margin > self.view_h:          return False
        return True

    # ─────────────────────────────────────────────────────────────
    # 每帧更新：边缘滚动
    # ─────────────────────────────────────────────────────────────

    def update(self, dt: int, mx: int, my: int, ui_focused: bool = False):
        """
        每帧调用。
        dt          : 帧间隔毫秒（暂未使用，保留接口）
        mx, my      : 当前鼠标屏幕坐标
        ui_focused  : 若为 True（鼠标在 UI 面板上），禁用边缘滚动
        """
        if ui_focused:
            return

        # 小地图拖拽中，根据鼠标位置实时更新视口
        if self._mm_dragging:
            wc = self._screen_to_minimap_world(mx, my)
            self.offset_x = wc[0] - self.view_w / 2
            self.offset_y = wc[1] - self.view_h / 2
            self._clamp()
            return   # 拖拽中不做边缘滚动

        spd = EDGE_SCROLL_SPEED
        zone = EDGE_SCROLL_ZONE

        # 水平边缘滚动（仅在游戏可见区域 [0, view_w] 内生效，不含侧边栏）
        if 0 <= mx < zone:
            self.offset_x -= spd * (1.0 - mx / zone)        # 越靠近左边缘越快
        elif self.view_w - zone < mx <= self.view_w:
            self.offset_x += spd * (1.0 - (self.view_w - mx) / zone)  # 越靠近右边缘越快

        # 垂直边缘滚动（仅在游戏区域内，忽略顶部栏；鼠标在侧边栏时也不触发）
        if mx <= self.view_w:  # 只在游戏区域（非侧边栏）判断纵向滚动
            game_my = my - TOPBAR_H
            if 0 <= game_my < zone:
                self.offset_y -= spd * (1.0 - game_my / zone)
            elif self.view_h - zone < game_my <= self.view_h:
                self.offset_y += spd * (1.0 - (self.view_h - game_my) / zone)

        self._clamp()

    # ─────────────────────────────────────────────────────────────
    # 小地图事件处理（按需调用接口 / 旧事件接口两套均保留）
    # ─────────────────────────────────────────────────────────────

    def handle_minimap_click(self, mx: int, my: int) -> bool:
        """
        鼠标按下时调用。
        若点击落在小地图上，则跳转视口并开始拖拽，返回 True（消费事件）。
        剧情锁定期间禁止操作。
        """
        if self.story_locked:
            return False  # 剧情期间禁止小地图操作
        if self._mm_rect.collidepoint(mx, my):
            wc = self._screen_to_minimap_world(mx, my)
            self.offset_x = wc[0] - self.view_w / 2
            self.offset_y = wc[1] - self.view_h / 2
            self._clamp()
            self._mm_dragging = True
            return True
        return False

    def handle_minimap_release(self):
        """鼠标抬起时调用，结束小地图拖拽。"""
        self._mm_dragging = False

    def handle_minimap_event(self, event) -> bool:
        """
        旧接口：将 pygame 事件传入，处理小地图交互。
        返回 True 表示事件已被小地图消费（上层不应再处理）。
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.handle_minimap_click(*event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._mm_dragging:
                self.handle_minimap_release()
                return True
        elif event.type == pygame.MOUSEMOTION:
            if self._mm_dragging:
                wc = self._screen_to_minimap_world(*event.pos)
                self.offset_x = wc[0] - self.view_w / 2
                self.offset_y = wc[1] - self.view_h / 2
                self._clamp()
                return True
        return False

    def focus_on(self, wx: float, wy: float, smooth: bool = False):
        """
        将视口居中到世界坐标 (wx, wy)。
        smooth=True 时做平滑插值（软跟随），False 时直接跳转。
        通常用于跟随玩家，但仅在玩家接近屏幕边缘时才移动（留出缓冲区）。
        """
        # 计算玩家在当前视口的屏幕坐标
        sx = wx - self.offset_x
        sy = wy - self.offset_y
        margin = 150   # 玩家距边缘 150px 内才触发跟随

        target_x = self.offset_x
        target_y = self.offset_y

        if sx < margin:
            target_x = wx - margin
        elif sx > self.view_w - margin:
            target_x = wx - (self.view_w - margin)

        if sy < margin:
            target_y = wy - margin
        elif sy > self.view_h - margin:
            target_y = wy - (self.view_h - margin)

        if smooth:
            lerp = 0.08   # 平滑系数（0=不移动，1=立即跳）
            self.offset_x += (target_x - self.offset_x) * lerp
            self.offset_y += (target_y - self.offset_y) * lerp
        else:
            self.offset_x = target_x
            self.offset_y = target_y

        self._clamp()

    # ─────────────────────────────────────────────────────────────
    # 渲染小地图
    # ─────────────────────────────────────────────────────────────

    def draw_minimap(self, screen: pygame.Surface,
                     world_map,          # WorldMap 实例，用于绘制区域颜色
                     all_cards: list,    # 用于在小地图上点绘 NPC/玩家
                     font=None):
        """在屏幕上绘制小地图 + 当前视口框"""
        # 【UI层级系统】注册小地图区域
        from src.ui.hit_test import register_ui_zone, UI_LAYER_WIDGET
        register_ui_zone(self._mm_rect, UI_LAYER_WIDGET, "小地图")
        
        mm = self._mm_surface
        # 先填充统一的野外底色（深绿棕色，代表荒野）
        WILD_COLOR = (45, 55, 40, MINIMAP_ALPHA)
        mm.fill(WILD_COLOR)

        scale_x = MINIMAP_W / self.world_w
        scale_y = MINIMAP_H / self.world_h

        def w2m(wx, wy):
            """世界坐标 → 小地图像素"""
            return int(wx * scale_x), int(wy * scale_y)

        # ── 绘制区域底色（整个地图统一野外底色，然后在上面绘制特殊区域）──
        # fill已经用WILD_COLOR填充了整个小地图，所有野外区域颜色一致
        
        # 农田区域（城市左侧）- 比野外底色稍浅
        fr = world_map.farm_rect
        pygame.draw.rect(mm, (50, 60, 42, 200),
                         (*w2m(fr.x, fr.y),
                          max(1, int(fr.w * scale_x)),
                          max(1, int(fr.h * scale_y))))

        # 贫民窟区域（城市下方）- 比野外底色稍暗
        sr = world_map.slum_rect
        pygame.draw.rect(mm, (55, 52, 48, 200),
                         (*w2m(sr.x, sr.y),
                          max(1, int(sr.w * scale_x)),
                          max(1, int(sr.h * scale_y))))

        # 城内地面（城市区域，最后绘制覆盖在上面）
        cr = world_map.city_rect
        CITY_COLOR = (85, 80, 75, 220)
        pygame.draw.rect(mm, CITY_COLOR,
                         (*w2m(cr.x, cr.y),
                          max(1, int(cr.w * scale_x)),
                          max(1, int(cr.h * scale_y))))

        # ── 城墙 ──
        for wall in world_map.walls:
            wx, wy = w2m(wall.x, wall.y)
            ww = max(1, int(wall.w * scale_x))
            wh = max(1, int(wall.h * scale_y))
            pygame.draw.rect(mm, (70, 65, 60), (wx, wy, ww, wh))

        # ── NPC 点（势力颜色区分，无边框，更小的点）──────────────────────────────────
        from src.entities import NPC
        from src.faction_colors import get_npc_faction_visual
        
        for card in all_cards:
            if not isinstance(card, NPC):
                continue
            if card.stack_parent:
                continue   # 堆叠中的不单独标点
            
            mx_card, my_card = w2m(card.rect.centerx, card.rect.centery)
            
            # 获取势力可视化信息
            faction_vis = get_npc_faction_visual(card)
            color = faction_vis['color']
            r = faction_vis['minimap_radius']
            
            # 战斗中的额外标记：点颜色闪烁（更亮的颜色）
            in_combat = getattr(card, 'in_combat', False) or getattr(card, 'state', '') == 'COMBAT'
            if in_combat and faction_vis.get('is_player') is not True:
                # 战斗中使用更亮的颜色
                import time
                if int(time.time() * 3) % 2 == 0:
                    color = (255, min(255, color[1] + 100), min(255, color[2] + 50))
            
            # 绘制势力颜色点（无边框，实心圆）
            pygame.draw.circle(mm, color, (mx_card, my_card), r)

        # ── 当前视口框 ──
        vx, vy = w2m(self.offset_x, self.offset_y)
        vw = max(2, int(self.view_w * scale_x))
        vh = max(2, int(self.view_h * scale_y))
        pygame.draw.rect(mm, (255, 255, 255), (vx, vy, vw, vh), 1)

        # ── 贴到屏幕 ──
        screen.blit(mm, self._mm_rect.topleft)

        # ── 边框 ──
        pygame.draw.rect(screen, (120, 120, 130), self._mm_rect, 1)

        # ── 标题 ──
        if font:
            label = font.render("地图", True, (200, 200, 200))
            screen.blit(label, (self._mm_rect.x + 4,
                                self._mm_rect.y - label.get_height() - 2))

    # ─────────────────────────────────────────────────────────────
    # 内部工具
    # ─────────────────────────────────────────────────────────────

    def _clamp(self):
        """确保视口不超出世界边界"""
        self.offset_x = max(0.0, min(self.offset_x, self.world_w - self.view_w))
        self.offset_y = max(0.0, min(self.offset_y, self.world_h - self.view_h))

    def _screen_to_minimap_world(self, sx: int, sy: int):
        """小地图上的屏幕坐标 → 世界坐标"""
        rel_x = (sx - self._mm_rect.x) / MINIMAP_W
        rel_y = (sy - self._mm_rect.y) / MINIMAP_H
        return rel_x * self.world_w, rel_y * self.world_h

    @property
    def minimap_rect(self) -> pygame.Rect:
        return self._mm_rect
    
    # ═══════════════════════════════════════════════════════════════
    # 【新增】事件聚焦动画
    # ═══════════════════════════════════════════════════════════════
    
    def start_event_focus(self, wx: float, wy: float, duration: int = 45):
        """
        开始事件聚焦动画：镜头平滑移动到目标位置
        
        Args:
            wx, wy: 事件中心的世界坐标
            duration: 动画持续帧数（默认45帧，约0.75秒）
        """
        self.event_focus_active = True
        self.event_focus_target = (wx, wy)
        self.event_focus_timer = 0
        self.event_focus_duration = duration
        self.event_focus_start_offset = (self.offset_x, self.offset_y)
        print(f"[Camera] 开始事件聚焦动画: 目标({wx:.0f}, {wy:.0f})")
    
    def update_event_focus(self):
        """
        更新事件聚焦动画（每帧调用）
        
        Returns:
            bool: 动画是否仍在进行中
        """
        if not self.event_focus_active:
            return False
        
        self.event_focus_timer += 1
        t = min(1.0, self.event_focus_timer / self.event_focus_duration)
        
        # 使用 ease-out 缓动函数，让移动更自然
        ease = 1.0 - (1.0 - t) ** 3  # cubic ease-out
        
        # 计算目标视口偏移（让目标点居中）
        target_wx, target_wy = self.event_focus_target
        target_offset_x = target_wx - self.view_w / 2
        target_offset_y = target_wy - self.view_h / 2
        
        # 插值计算当前偏移
        start_x, start_y = self.event_focus_start_offset
        self.offset_x = start_x + (target_offset_x - start_x) * ease
        self.offset_y = start_y + (target_offset_y - start_y) * ease
        self._clamp()
        
        # 检查动画是否完成
        if self.event_focus_timer >= self.event_focus_duration:
            self.event_focus_active = False
            print(f"[Camera] 事件聚焦动画完成")
            return False
        
        return True
    
    def cancel_event_focus(self):
        """取消事件聚焦动画"""
        self.event_focus_active = False
        self.event_focus_timer = 0
