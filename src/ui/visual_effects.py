"""
视觉效果管理器 - AI事件通知特效
===================================================

提供简单的视觉效果，用于：
- AI事件到来时的屏幕闪烁
- 边缘光晕提示
- 粒子效果
"""

import pygame
import math
import random
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ScreenFlash:
    """屏幕闪烁效果"""
    color: Tuple[int, int, int]
    duration_ms: int
    elapsed: int = 0
    intensity: float = 0.3  # 最大透明度
    
    def is_done(self) -> bool:
        return self.elapsed >= self.duration_ms
    
    def get_alpha(self) -> int:
        if self.elapsed >= self.duration_ms:
            return 0
        # 快闪后淡出
        progress = self.elapsed / self.duration_ms
        if progress < 0.2:
            return int(255 * self.intensity * (progress / 0.2))
        else:
            return int(255 * self.intensity * (1 - (progress - 0.2) / 0.8))


@dataclass
class EdgeGlow:
    """边缘光晕效果"""
    color: Tuple[int, int, int]
    duration_ms: int
    thickness: int = 30
    elapsed: int = 0
    pulse: bool = True  # 是否脉动
    
    def is_done(self) -> bool:
        return self.elapsed >= self.duration_ms
    
    def get_intensity(self) -> float:
        if self.elapsed >= self.duration_ms:
            return 0
        
        progress = self.elapsed / self.duration_ms
        
        # 淡入淡出
        if progress < 0.1:
            base = progress / 0.1
        elif progress > 0.7:
            base = (1 - progress) / 0.3
        else:
            base = 1.0
        
        # 脉动效果
        if self.pulse:
            pulse_val = 0.5 + 0.5 * math.sin(self.elapsed / 100 * math.pi)
            return base * pulse_val
        
        return base


@dataclass 
class Particle:
    """粒子"""
    x: float
    y: float
    vx: float
    vy: float
    color: Tuple[int, int, int]
    size: float
    life: float
    max_life: float
    
    def update(self, dt_ms: int):
        self.x += self.vx * dt_ms / 1000
        self.y += self.vy * dt_ms / 1000
        self.life -= dt_ms
        # 重力
        self.vy += 200 * dt_ms / 1000
    
    def is_dead(self) -> bool:
        return self.life <= 0
    
    def get_alpha(self) -> int:
        return int(255 * (self.life / self.max_life))


class VisualEffectsManager:
    """
    视觉效果管理器
    
    使用方法:
        vfx = get_visual_effects()
        vfx.add_screen_flash((255, 200, 100), 500)  # 黄色闪烁500ms
        vfx.add_edge_glow((100, 150, 255), 2000)    # 蓝色边缘光晕2秒
    """
    
    def __init__(self, screen_w: int, screen_h: int):
        self.screen_w = screen_w
        self.screen_h = screen_h
        
        self._flashes: List[ScreenFlash] = []
        self._glows: List[EdgeGlow] = []
        self._particles: List[Particle] = []
        
        # 缓存的surface
        self._glow_surface: Optional[pygame.Surface] = None
    
    def update(self, dt_ms: int):
        """更新所有效果"""
        # 更新闪烁
        for flash in self._flashes[:]:
            flash.elapsed += dt_ms
            if flash.is_done():
                self._flashes.remove(flash)
        
        # 更新光晕
        for glow in self._glows[:]:
            glow.elapsed += dt_ms
            if glow.is_done():
                self._glows.remove(glow)
        
        # 更新粒子
        for particle in self._particles[:]:
            particle.update(dt_ms)
            if particle.is_dead():
                self._particles.remove(particle)
    
    def draw(self, screen: pygame.Surface):
        """绘制所有效果"""
        # 绘制屏幕闪烁
        for flash in self._flashes:
            alpha = flash.get_alpha()
            if alpha > 0:
                overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
                overlay.fill((*flash.color, alpha))
                screen.blit(overlay, (0, 0))
        
        # 绘制边缘光晕
        for glow in self._glows:
            intensity = glow.get_intensity()
            if intensity > 0:
                self._draw_edge_glow(screen, glow.color, glow.thickness, intensity)
        
        # 绘制粒子
        for particle in self._particles:
            alpha = particle.get_alpha()
            if alpha > 0:
                size = int(particle.size * (particle.life / particle.max_life))
                if size > 0:
                    pygame.draw.circle(
                        screen, 
                        particle.color, 
                        (int(particle.x), int(particle.y)), 
                        size
                    )
    
    def _draw_edge_glow(self, screen: pygame.Surface, color: Tuple[int, int, int], 
                        thickness: int, intensity: float):
        """绘制边缘渐变光晕"""
        alpha_base = int(150 * intensity)
        
        # 上边缘
        for i in range(thickness):
            alpha = int(alpha_base * (1 - i / thickness))
            if alpha > 0:
                pygame.draw.line(
                    screen, (*color, alpha),
                    (0, i), (self.screen_w, i)
                )
        
        # 下边缘
        for i in range(thickness):
            y = self.screen_h - 1 - i
            alpha = int(alpha_base * (1 - i / thickness))
            if alpha > 0:
                pygame.draw.line(
                    screen, (*color, alpha),
                    (0, y), (self.screen_w, y)
                )
        
        # 左边缘
        for i in range(thickness):
            alpha = int(alpha_base * (1 - i / thickness))
            if alpha > 0:
                pygame.draw.line(
                    screen, (*color, alpha),
                    (i, 0), (i, self.screen_h)
                )
        
        # 右边缘
        for i in range(thickness):
            x = self.screen_w - 1 - i
            alpha = int(alpha_base * (1 - i / thickness))
            if alpha > 0:
                pygame.draw.line(
                    screen, (*color, alpha),
                    (x, 0), (x, self.screen_h)
                )
    
    # ═══════════════════════════════════════════════════════════════
    # 公共接口
    # ═══════════════════════════════════════════════════════════════
    
    def add_screen_flash(self, color: Tuple[int, int, int] = (255, 220, 150), 
                         duration_ms: int = 400, intensity: float = 0.25):
        """添加屏幕闪烁效果"""
        self._flashes.append(ScreenFlash(color, duration_ms, intensity=intensity))
    
    def add_edge_glow(self, color: Tuple[int, int, int] = (100, 180, 255),
                      duration_ms: int = 2000, thickness: int = 25, pulse: bool = True):
        """添加边缘光晕效果"""
        self._glows.append(EdgeGlow(color, duration_ms, thickness, pulse=pulse))
    
    def add_notification_effect(self, priority: int = 2):
        """
        AI事件通知效果（根据优先级选择效果强度）
        
        Args:
            priority: 事件优先级 (1=低, 2=普通, 3=高, 4=紧急)
        """
        if priority >= 4:
            # 紧急事件：红色边缘+闪烁
            self.add_screen_flash((255, 100, 100), 300, 0.3)
            self.add_edge_glow((255, 80, 80), 3000, 40, pulse=True)
        elif priority >= 3:
            # 重要事件：金色边缘
            self.add_screen_flash((255, 200, 100), 250, 0.2)
            self.add_edge_glow((255, 180, 80), 2500, 30, pulse=True)
        elif priority >= 2:
            # 普通事件：蓝色边缘
            self.add_edge_glow((100, 150, 255), 2000, 20, pulse=True)
        else:
            # 低优先级：淡蓝色提示
            self.add_edge_glow((150, 200, 255), 1500, 15, pulse=False)
    
    def add_particle_burst(self, x: int, y: int, color: Tuple[int, int, int] = (255, 220, 150),
                           count: int = 15, speed: float = 150):
        """在指定位置添加粒子爆发"""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            spd = random.uniform(speed * 0.5, speed * 1.5)
            self._particles.append(Particle(
                x=float(x),
                y=float(y),
                vx=math.cos(angle) * spd,
                vy=math.sin(angle) * spd - 50,  # 向上偏移
                color=color,
                size=random.uniform(3, 6),
                life=random.uniform(500, 1000),
                max_life=1000
            ))
    
    def clear(self):
        """清除所有效果"""
        self._flashes.clear()
        self._glows.clear()
        self._particles.clear()


# ═══════════════════════════════════════════════════════════════════════════
# 全局实例
# ═══════════════════════════════════════════════════════════════════════════

_visual_effects: Optional[VisualEffectsManager] = None

def get_visual_effects(screen_w: int = 0, screen_h: int = 0) -> VisualEffectsManager:
    """获取全局视觉效果管理器"""
    global _visual_effects
    if _visual_effects is None:
        if screen_w == 0 or screen_h == 0:
            # 尝试从pygame获取屏幕尺寸
            try:
                surface = pygame.display.get_surface()
                if surface:
                    screen_w, screen_h = surface.get_size()
                else:
                    screen_w, screen_h = 1920, 1080  # 默认值
            except:
                screen_w, screen_h = 1920, 1080
        _visual_effects = VisualEffectsManager(screen_w, screen_h)
    return _visual_effects
