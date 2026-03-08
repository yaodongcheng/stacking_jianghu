"""
性能分析工具 v2 - 实时帧内计时
使用方法：将此文件的 PerformanceMonitor 导入到 main.py 中使用

在游戏中按 F3 显示/隐藏性能面板
"""

import time
import pygame
from collections import deque


class PerformanceMonitor:
    """实时性能监控器 - 直接在游戏界面显示各系统耗时"""
    
    def __init__(self, screen_w=1920, screen_h=1080):
        self.screen_w = screen_w
        self.screen_h = screen_h
        
        # 各系统计时数据（滑动窗口平均）
        self.window_size = 60  # 60帧滑动窗口
        self.timings = {
            'total_frame': deque(maxlen=self.window_size),
            'event_handling': deque(maxlen=self.window_size),
            'ai_system': deque(maxlen=self.window_size),
            'combat_system': deque(maxlen=self.window_size),
            'movement_system': deque(maxlen=self.window_size),
            'card_update': deque(maxlen=self.window_size),
            'render': deque(maxlen=self.window_size),
            'ui_draw': deque(maxlen=self.window_size),
        }
        
        # 当前帧计时
        self._start_times = {}
        self._frame_start = 0
        
        # 显示控制
        self.visible = True
        self.font = None
        
        # 性能告警阈值（毫秒）
        self.warn_thresholds = {
            'ai_system': 5.0,
            'render': 8.0,
            'total_frame': 16.67,  # 60fps = 16.67ms/frame
        }
        
        # 帧率历史
        self.fps_history = deque(maxlen=120)
        
        # 调试按钮
        self._buttons = []
        self._game_ref = None  # 游戏引用，用于获取 all_cards
        
        # 按钮点击状态
        self._button_hover = None
        self._button_clicked = False
        
    def set_game_ref(self, game):
        """设置游戏引用，用于调试功能"""
        self._game_ref = game
        
    def _get_font(self):
        """延迟加载字体（使用系统字体支持中文）"""
        if self.font is None:
            # 使用与项目其他UI一致的中文字体列表
            font_names = "microsoftyahei,simhei,pingfangsc,notosanscjk,arial"
            try:
                self.font = pygame.font.SysFont(font_names, 14)
            except:
                self.font = pygame.font.Font(None, 16)
        return self.font
    
    def frame_start(self):
        """帧开始"""
        self._frame_start = time.perf_counter()
    
    def frame_end(self, fps: float):
        """帧结束"""
        elapsed = (time.perf_counter() - self._frame_start) * 1000
        self.timings['total_frame'].append(elapsed)
        self.fps_history.append(fps)
    
    def begin(self, system_name: str):
        """开始计时某个系统"""
        self._start_times[system_name] = time.perf_counter()
    
    def end(self, system_name: str):
        """结束计时某个系统"""
        if system_name in self._start_times:
            elapsed = (time.perf_counter() - self._start_times[system_name]) * 1000
            if system_name in self.timings:
                self.timings[system_name].append(elapsed)
            del self._start_times[system_name]
    
    def toggle(self):
        """切换显示/隐藏"""
        self.visible = not self.visible
    
    def _avg(self, name: str) -> float:
        """计算平均值"""
        data = self.timings.get(name, [])
        return sum(data) / len(data) if data else 0
    
    def _max(self, name: str) -> float:
        """计算最大值"""
        data = self.timings.get(name, [])
        return max(data) if data else 0
    
    def draw(self, screen):
        """绘制性能面板"""
        if not self.visible:
            return
        
        font = self._get_font()
        
        # 面板位置和尺寸（增加高度以容纳调试按钮）
        panel_w, panel_h = 280, 370
        panel_x, panel_y = 10, 60
        
        # 半透明背景
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill((20, 20, 30, 220))
        screen.blit(panel_surf, (panel_x, panel_y))
        
        # 边框
        pygame.draw.rect(screen, (100, 100, 150), (panel_x, panel_y, panel_w, panel_h), 1)
        
        y = panel_y + 8
        line_h = 22
        
        # 标题
        title = font.render("🔧 性能监控 (F3 关闭)", True, (255, 220, 100))
        screen.blit(title, (panel_x + 10, y))
        y += line_h + 5
        
        # 分隔线
        pygame.draw.line(screen, (80, 80, 120), (panel_x + 5, y), (panel_x + panel_w - 5, y))
        y += 8
        
        # FPS
        avg_fps = sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0
        min_fps = min(self.fps_history) if self.fps_history else 0
        fps_color = (100, 255, 100) if avg_fps >= 55 else (255, 255, 100) if avg_fps >= 40 else (255, 100, 100)
        fps_text = font.render(f"FPS: {avg_fps:.1f} (最低: {min_fps:.1f})", True, fps_color)
        screen.blit(fps_text, (panel_x + 10, y))
        y += line_h
        
        # 帧时间
        frame_avg = self._avg('total_frame')
        frame_max = self._max('total_frame')
        frame_color = (100, 255, 100) if frame_avg < 16.67 else (255, 255, 100) if frame_avg < 25 else (255, 100, 100)
        frame_text = font.render(f"帧时间: {frame_avg:.2f}ms (峰值: {frame_max:.2f}ms)", True, frame_color)
        screen.blit(frame_text, (panel_x + 10, y))
        y += line_h + 5
        
        # 分隔线
        pygame.draw.line(screen, (80, 80, 120), (panel_x + 5, y), (panel_x + panel_w - 5, y))
        y += 8
        
        # 各系统耗时
        systems = [
            ('ai_system', 'AI系统', 5.0),
            ('combat_system', '战斗系统', 3.0),
            ('movement_system', '移动系统', 3.0),
            ('card_update', '卡牌更新', 5.0),
            ('render', '渲染系统', 8.0),
            ('event_handling', '事件处理', 2.0),
        ]
        
        total_system_time = 0
        for key, name, threshold in systems:
            avg = self._avg(key)
            total_system_time += avg
            
            # 颜色根据阈值判断
            if avg < threshold * 0.5:
                color = (100, 255, 100)  # 绿色：良好
            elif avg < threshold:
                color = (255, 255, 100)  # 黄色：一般
            else:
                color = (255, 100, 100)  # 红色：瓶颈
            
            # 绘制进度条背景
            bar_x = panel_x + 100
            bar_w = 120
            bar_h = 12
            pygame.draw.rect(screen, (50, 50, 70), (bar_x, y + 3, bar_w, bar_h))
            
            # 绘制进度条
            fill_ratio = min(avg / (threshold * 2), 1.0)
            pygame.draw.rect(screen, color, (bar_x, y + 3, int(bar_w * fill_ratio), bar_h))
            
            # 文字
            text = font.render(f"{name}:", True, (200, 200, 220))
            screen.blit(text, (panel_x + 10, y))
            
            val_text = font.render(f"{avg:.2f}ms", True, color)
            screen.blit(val_text, (bar_x + bar_w + 5, y))
            
            y += line_h
        
        y += 5
        pygame.draw.line(screen, (80, 80, 120), (panel_x + 5, y), (panel_x + panel_w - 5, y))
        y += 8
        
        # 总计
        total_text = font.render(f"系统总计: {total_system_time:.2f}ms", True, (200, 200, 255))
        screen.blit(total_text, (panel_x + 10, y))
        y += line_h
        
        # 瓶颈诊断
        y += 5
        pygame.draw.line(screen, (80, 80, 120), (panel_x + 5, y), (panel_x + panel_w - 5, y))
        y += 8
        
        # 找出最耗时的系统
        bottleneck = None
        bottleneck_time = 0
        for key, name, threshold in systems:
            avg = self._avg(key)
            if avg > bottleneck_time:
                bottleneck_time = avg
                bottleneck = name
        
        if bottleneck and bottleneck_time > 3.0:
            diag_text = font.render(f"[!] 瓶颈: {bottleneck} ({bottleneck_time:.1f}ms)", True, (255, 150, 100))
        else:
            diag_text = font.render("[ok] 性能良好", True, (100, 255, 150))
        screen.blit(diag_text, (panel_x + 10, y))
        y += line_h + 5
        
        # ═══════════════════════════════════════════════════════════
        # 调试按钮区域
        # ═══════════════════════════════════════════════════════════
        pygame.draw.line(screen, (80, 80, 120), (panel_x + 5, y), (panel_x + panel_w - 5, y))
        y += 8
        
        # 清空按钮列表
        self._buttons = []
        
        # 按钮: 打印网格重叠信息
        btn_rect = pygame.Rect(panel_x + 10, y, panel_w - 20, 24)
        self._buttons.append(('grid_overlap', btn_rect))
        
        # 检测鼠标悬停
        mouse_pos = pygame.mouse.get_pos()
        is_hover = btn_rect.collidepoint(mouse_pos)
        
        # 绘制按钮
        btn_color = (80, 120, 180) if is_hover else (60, 80, 120)
        pygame.draw.rect(screen, btn_color, btn_rect)
        pygame.draw.rect(screen, (100, 140, 200), btn_rect, 1)
        
        btn_text = font.render("📍 打印静止NPC网格信息", True, (220, 230, 255))
        text_rect = btn_text.get_rect(center=btn_rect.center)
        screen.blit(btn_text, text_rect)
    
    def handle_click(self, pos):
        """
        处理鼠标点击事件
        返回 True 如果点击被消费
        """
        if not self.visible:
            return False
        
        for btn_id, btn_rect in self._buttons:
            if btn_rect.collidepoint(pos):
                self._on_button_click(btn_id)
                return True
        return False
    
    def _on_button_click(self, btn_id):
        """按钮点击回调"""
        if btn_id == 'grid_overlap':
            self._print_grid_overlap_info()
    
    def _print_grid_overlap_info(self):
        """打印网格重叠信息"""
        print("\n[F3调试] 正在收集网格信息...")
        
        if self._game_ref is None:
            print("[F3调试] 错误：未设置游戏引用，无法获取NPC列表")
            return
        
        # 尝试获取 movement_system 和 all_cards
        try:
            movement_system = getattr(self._game_ref, 'movement_system', None)
            all_cards = getattr(self._game_ref, 'all_cards', None)
            
            if movement_system is None:
                print("[F3调试] 错误：未找到 movement_system")
                return
            if all_cards is None:
                print("[F3调试] 错误：未找到 all_cards")
                return
            
            # 调用网格调试方法
            occupancy_grid = movement_system.occupancy_grid
            occupancy_grid.print_all_static_npcs_info(all_cards)
            
        except Exception as e:
            print(f"[F3调试] 错误: {e}")
            import traceback
            traceback.print_exc()
    
    def get_report(self) -> str:
        """生成文字报告"""
        lines = ["=" * 50, "性能分析报告", "=" * 50]
        
        for name, data in self.timings.items():
            if data:
                avg = sum(data) / len(data)
                max_val = max(data)
                lines.append(f"{name:20}: avg={avg:.2f}ms, max={max_val:.2f}ms")
        
        return "\n".join(lines)


# 全局实例
_perf_monitor = None

def get_perf_monitor(screen_w=1920, screen_h=1080) -> PerformanceMonitor:
    """获取全局性能监控器实例"""
    global _perf_monitor
    if _perf_monitor is None:
        _perf_monitor = PerformanceMonitor(screen_w, screen_h)
    return _perf_monitor