# --- src/world_map.py ---
import pygame
import random
import math
from src.definitions import *

class WorldMap:
    def __init__(self, screen_w, screen_h, world_w=None, world_h=None):
        """
        world_w / world_h : 世界逻辑总尺寸。
          - 若不传（None），默认退化为单屏尺寸（向后兼容旧代码）。
          - 传入后，WorldMap 的所有区域坐标都在 [0, world_w] × [0, world_h] 范围内，
            与屏幕分辨率无关，由 Camera 负责视口偏移映射到屏幕坐标。
        """
        # 屏幕可玩区域尺寸（仅供外部代码参考，不用于世界坐标计算）
        self.screen_view_w = screen_w - SIDEBAR_W
        self.screen_view_h = screen_h - TOPBAR_H

        # 世界逻辑总尺寸
        self.w = world_w if world_w is not None else (screen_w - SIDEBAR_W)
        self.h = world_h if world_h is not None else screen_h

        # --- 2. 区域定义 (核心逻辑 & 视觉) ---
        
        # 墙体预留缓冲 (防止生成的卡牌贴墙太近)
        wall_padding = 40
        
        # 内城尺寸固定，不随世界尺寸按比例缩放
        # 基准：约1700x1700的内城区域，足够容纳所有建筑
        city_w = min(1700, int(self.w * 0.55))  # 城内宽度
        city_h = min(1700, int(self.h * 0.50))  # 城内高度（占比降低以留出更多野外空间）
        
        # 内城居中偏左（留出更多右侧野外空间，上下均匀）
        margin_x = int((self.w - city_w) * 0.35)  # 城墙左侧留35%，右侧65%野外
        margin_y = int((self.h - city_h) * 0.5)   # 城墙上下各留50%野外
        
        self.city_rect = pygame.Rect(margin_x, margin_y, city_w, city_h)
        
        # 市场 (内城的一个子区域，用于商贾 AI 聚集)
        self.market_rect = self.city_rect.inflate(-100, -100)
        
        # 农田区域 (城墙左侧外部，避开墙体)
        self.farm_rect = pygame.Rect(20, 20, margin_x - wall_padding, self.h - 40)
        
        # 贫民窟区域 (城墙下方外部，避开墙体)
        slum_top = self.city_rect.bottom + wall_padding
        slum_height = max(100, self.h - slum_top - 20)
        self.slum_rect = pygame.Rect(self.city_rect.left, slum_top, self.city_rect.width, slum_height)
        
        # 【新增】城外野外区域定义（供山贼等 NPC 限定活动范围）
        # 野外区域是整个地图减去城内区域
        # 这里存储几个主要野外区块，供 AI 系统使用
        
        # [逻辑] 普通野外安全边距（翻倍到 400px）
        safe_margin = 400
        self.outer_zones = {
            'NORTH': pygame.Rect(0, 0, self.w, max(50, self.city_rect.top - safe_margin)),
            'SOUTH': pygame.Rect(0, self.city_rect.bottom + safe_margin, self.w, max(50, self.h - self.city_rect.bottom - safe_margin)),
            'WEST': pygame.Rect(0, 0, max(50, self.city_rect.left - safe_margin), self.h),
            'EAST': pygame.Rect(self.city_rect.right + safe_margin, 0, max(50, self.w - self.city_rect.right - safe_margin), self.h),
        }
        
        # [逻辑] 山贼专用活动区域：在 outer_zones 的更外层，远离城墙
        # 山贼边距 = 普通野外边距的1.5倍，确保山贼只在地图边缘活动
        bandit_margin = 600  # 距离城墙 600px
        self.bandit_zones = {
            'NORTH': pygame.Rect(0, 0, self.w, max(50, self.city_rect.top - bandit_margin)),
            'SOUTH': pygame.Rect(0, self.city_rect.bottom + bandit_margin, self.w, max(50, self.h - self.city_rect.bottom - bandit_margin)),
            'WEST': pygame.Rect(0, 0, max(50, self.city_rect.left - bandit_margin), self.h),
            'EAST': pygame.Rect(self.city_rect.right + bandit_margin, 0, max(50, self.w - self.city_rect.right - bandit_margin), self.h),
        }

        # --- 3. 物理阻挡定义 (墙体 & 城门) ---
        
        # 城墙厚度随世界规模等比缩放（最小12px，最大40px）
        self.wall_thick = max(12, min(40, int(self.w / 100)))
        gate_w = max(120, int(self.w * 0.09))   # 城门宽度约为世界宽度9%
        cx, cy = self.city_rect.centerx, self.city_rect.centery
        
        # 城门矩形
        self.gates = {
            'NORTH': pygame.Rect(cx - gate_w//2, self.city_rect.top - 10, gate_w, 20 + self.wall_thick),
            'SOUTH': pygame.Rect(cx - gate_w//2, self.city_rect.bottom - 10, gate_w, 20 + self.wall_thick),
            'WEST':  pygame.Rect(self.city_rect.left - 10, cy - gate_w//2, 20 + self.wall_thick, gate_w),
            'EAST':  pygame.Rect(self.city_rect.right - 10, cy - gate_w//2, 20 + self.wall_thick, gate_w)
        }
        
        # 定义实体墙体
        self.walls = []
        r = self.city_rect
        t = self.wall_thick
        g_w = gate_w
        
        # 北墙
        self.walls.append(pygame.Rect(r.left, r.top, (r.width - g_w)//2, t))
        self.walls.append(pygame.Rect(r.right - (r.width - g_w)//2, r.top, (r.width - g_w)//2, t))
        # 南墙
        self.walls.append(pygame.Rect(r.left, r.bottom - t, (r.width - g_w)//2, t))
        self.walls.append(pygame.Rect(r.right - (r.width - g_w)//2, r.bottom - t, (r.width - g_w)//2, t))
        # 西墙
        self.walls.append(pygame.Rect(r.left, r.top, t, (r.height - g_w)//2))
        self.walls.append(pygame.Rect(r.left, r.bottom - (r.height - g_w)//2, t, (r.height - g_w)//2))
        # 东墙
        self.walls.append(pygame.Rect(r.right - t, r.top, t, (r.height - g_w)//2))
        self.walls.append(pygame.Rect(r.right - t, r.bottom - (r.height - g_w)//2, t, (r.height - g_w)//2))

    def draw_background(self, screen, camera=None):
        """
        绘制游戏背景板。
        camera : Camera 实例（有摄像机时只绘制可见区域）。
                 若为 None，则退化为旧行为（坐标不偏移），向后兼容。
        """
        def w2s(rect):
            """世界矩形 → 屏幕矩形（带摄像机偏移）"""
            if camera is None:
                return rect
            sx, sy = camera.world_to_screen(rect.x, rect.y)
            return pygame.Rect(int(sx), int(sy), rect.w, rect.h)

        # 1. 填充可玩区域背景（只填充视口区域即可）
        if camera:
            play_area = pygame.Rect(0, TOPBAR_H, camera.view_w, camera.view_h)
        else:
            play_area = pygame.Rect(0, 0, self.w, self.h)
        pygame.draw.rect(screen, COLOR_BG, play_area)

        # 绘制农田纹理（只绘制可见行，节省性能）
        fr_s = w2s(self.farm_rect)
        if camera is None or camera.is_visible(self.farm_rect):
            step = 40
            for i in range(0, self.farm_rect.height, step):
                sy_line = fr_s.top + int(i * fr_s.height / self.farm_rect.height)
                if camera and (sy_line < TOPBAR_H or sy_line > camera.view_h + TOPBAR_H):
                    continue
                pygame.draw.line(screen, (70, 80, 60),
                                 (fr_s.left, sy_line), (fr_s.right, sy_line), 2)

        # 绘制内城地面
        if camera is None or camera.is_visible(self.city_rect):
            pygame.draw.rect(screen, COLOR_CITY_GROUND, w2s(self.city_rect))

        # 绘制市场区域暗示
        if camera is None or camera.is_visible(self.market_rect):
            pygame.draw.rect(screen, (110, 105, 100), w2s(self.market_rect))

        # 绘制贫民窟暗示
        if camera is None or camera.is_visible(self.slum_rect):
            pygame.draw.rect(screen, (60, 55, 50), w2s(self.slum_rect), 1)

        # 2. 城门
        for gate in self.gates.values():
            if camera is None or camera.is_visible(gate):
                pygame.draw.rect(screen, (90, 85, 80), w2s(gate))

        # 3. 城墙
        for wall in self.walls:
            if camera is None or camera.is_visible(wall):
                pygame.draw.rect(screen, COLOR_WALL, w2s(wall))
                pygame.draw.rect(screen, (0, 0, 0), w2s(wall), 1)

    # =========================================
    # 物理 & 逻辑方法 (完全保留并恢复)
    # =========================================

    def get_zone_rect(self, zone_name):
        """根据区域名称返回对应的 Rect"""
        if zone_name == ZONE_FARM: return self.farm_rect
        if zone_name == ZONE_MARKET: return self.market_rect
        if zone_name == ZONE_SLUM: return self.slum_rect
        if zone_name == ZONE_INNER: return self.city_rect
        return pygame.Rect(0,0, self.w, self.h)

    def get_random_pos_in_rect(self, rect):
        """在指定矩形内随机取点"""
        padding = 20
        if rect.width <= padding*2 or rect.height <= padding*2:
            return rect.centerx, rect.centery
        x = random.randint(rect.left + padding, rect.right - padding)
        y = random.randint(rect.top + padding, rect.bottom - padding)
        return x, y

    # --- 【恢复】被我误删的随机生成逻辑 ---
    def get_random_pos(self, zone_type):
        """根据区域类型获取随机坐标"""
        target_rect = self.city_rect # 默认
        
        if zone_type == ZONE_INNER: target_rect = self.city_rect
        elif zone_type == ZONE_MARKET: target_rect = self.market_rect
        elif zone_type == ZONE_FARM: target_rect = self.farm_rect
        elif zone_type == ZONE_SLUM: target_rect = self.slum_rect
        elif zone_type == ZONE_OUTER:
             # 随机选一个非城内区域
             if random.random() < 0.5:
                 target_rect = self.farm_rect
             else:
                 target_rect = self.slum_rect
             
        # 获取坐标后，检查是否撞墙
        x, y = self.get_random_pos_in_rect(target_rect)
        
        # 简单的防卡死检查
        test_rect = pygame.Rect(x-10, y-10, 20, 20)
        if self.is_blocked(test_rect):
            return target_rect.centerx, target_rect.centery
            
        return x, y

    # --- 【恢复】被我误删的区域检测逻辑 ---
    def check_zone(self, x, y):
        """判断坐标在哪个逻辑区域 (用于判断卡牌 buff)"""
        # 优先判断具体的小区域
        if self.market_rect.collidepoint(x, y):
            return ZONE_MARKET
        if self.farm_rect.collidepoint(x, y):
            return ZONE_FARM
        if self.slum_rect.collidepoint(x, y):
            return ZONE_SLUM
            
        # 然后判断是否在城内
        if self.city_rect.collidepoint(x, y):
            return ZONE_INNER
            
        return ZONE_OUTER

    def get_nearest_gate(self, x, y):
        """返回最近城门的中心点坐标"""
        best_gate_pos = None
        min_dist = float('inf')
        for gate in self.gates.values():
            gx, gy = gate.center
            dist = math.hypot(x - gx, y - gy)
            if dist < min_dist:
                min_dist = dist
                best_gate_pos = (gx, gy)
        return best_gate_pos

    def is_blocked(self, rect):
        """
        核心物理检测：检查实体是否撞墙或出界。
        注意：rect 使用世界坐标（与 camera 无关）。
        """
        # 1. 检查是否撞墙
        if rect.collidelist(self.walls) != -1:
            return True
            
        # 2. 边界检查（使用 self.w/self.h = 世界总尺寸）
        if rect.left < 0 or rect.right > self.w or rect.top < 0 or rect.bottom > self.h:
            return True
            
        return False
