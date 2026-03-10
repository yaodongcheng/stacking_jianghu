# --- src/utils.py ---
import pygame
import datetime
import os
from pathlib import Path

# --- 日志系统 ---
from src.definitions import DEBUG_COMBAT

class GameLogger:
    _instance = None
    LOG_FILE = "game_log.txt"
    
    # 静默标签列表：当对应DEBUG开关为False时，这些标签的日志不会打印到控制台（但仍写入文件）
    # 格式: { 'TAG_NAME': 'DEBUG_开关名' }
    _SILENT_TAGS = {
        'COMBAT': 'DEBUG_COMBAT',
        'LOOT': 'DEBUG_COMBAT',         # 掉落系统归属战斗调试
        'ORG_AGGRO': 'DEBUG_ORG_AGGRO',  # 组织仇恨感知（友方被攻击提升仇恨）
        'AI_RECIPE': 'DEBUG_RECIPE_AI',  # NPC配方驱动AI调试
        'SEE_AGGRO': 'DEBUG_ORG_AGGRO',  # 视觉仇恨感知（看到友方被攻击）
    }

    @staticmethod
    def get_instance():
        if GameLogger._instance is None:
            GameLogger._instance = GameLogger()
        return GameLogger._instance

    def __init__(self):
        # 每次重启游戏清空旧日志，或者你可以选择追加 'a'
        with open(self.LOG_FILE, 'w', encoding='utf-8') as f:
            f.write(f"=== 大宋实况日志启动 {datetime.datetime.now()} ===\n")
            f.write("说明：此文件记录了玩家的游玩历程、选择和状态。\n\n")

    def _should_print(self, tag):
        """检查该标签是否应该打印到控制台"""
        if tag not in self._SILENT_TAGS:
            return True  # 不在静默列表中，默认打印
        
        # 动态获取对应的DEBUG开关值
        debug_flag_name = self._SILENT_TAGS[tag]
        from src import definitions
        debug_value = getattr(definitions, debug_flag_name, True)
        return debug_value

    def log(self, text, tag="INFO"):
        """记录一条日志，毫秒级时间戳"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]  # 精确到毫秒
        line = f"[{timestamp}][{tag}] {text}"
        
        # 根据DEBUG开关决定是否打印到控制台
        if self._should_print(tag):
            print(line)
        
        # 始终写入日志文件（便于事后排查）
        try:
            with open(self.LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(line + "\n")
        except Exception as e:
            print(f"日志写入失败: {e}")

def log_game_event(text, tag="INFO"):
    """全局快捷调用"""
    if tag == "MEMORY":
        return  # 记忆系统日志过于频繁，暂时不输出到控制台
    if tag == "COMBAT" and not DEBUG_COMBAT:
        return
    GameLogger.get_instance().log(text, tag=tag)

# --- 资源路径处理（支持打包后） ---

def resource_path(relative_path):
    """
    获取资源文件的绝对路径（支持开发环境和PyInstaller打包后）
    
    Args:
        relative_path: 相对于项目根目录的路径
        
    Returns:
        str: 资源文件的绝对路径
    """
    import sys
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的临时目录
        base_path = sys._MEIPASS
    else:
        # 开发环境
        base_path = Path(__file__).parent.parent
    
    return str(Path(base_path) / relative_path)


# --- 图像与文本工具 ---

def load_image(path, size=None, color=None):
    """
    加载图片，如果文件不存在，返回一个占位用的 Surface
    支持相对路径和绝对路径，自动处理打包后的资源路径
    """
    # 如果是相对路径，转换为资源路径
    if not Path(path).is_absolute():
        path = resource_path(path)
    
    try:
        image = pygame.image.load(path).convert_alpha()
        if size:
            image = pygame.transform.scale(image, size)
    except (FileNotFoundError, pygame.error):
        # 占位符
        w, h = size if size else (32, 32)
        image = pygame.Surface((w, h))
        image.fill((200, 200, 200)) 
        pygame.draw.rect(image, (0,0,0), (0,0,w,h), 1)

    if color:
        color_surf = pygame.Surface(image.get_size())
        color_surf.fill(color)
        image.blit(color_surf, (0, 0), special_flags=pygame.BLEND_MULT)
    
    return image

def wrap_text(text, font, max_width):
    """
    简单的中文文本自动换行工具
    返回: 一个字符串列表，每行不超过 max_width
    """
    if not text:
        return []
    
    lines = []
    current_line = ""
    
    for char in text:
        test_line = current_line + char
        # 获取当前行渲染后的宽度
        w, h = font.size(test_line)
        if w < max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = char
            
    if current_line:
        lines.append(current_line)
        
    return lines

class Appearance:
    """角色外观 - 仅包含头像"""
    # 头像搜索路径（按优先级排序）
    AVATAR_SEARCH_PATHS = [
        "assets/head_icon/{name}.png",      # 优化后的128x128头像（唯一）
    ]
    
    def __init__(self, head_path=None, size=(64, 64)):
        self.size = size
        self.head_path = head_path
        self.head_surf = None
        self._original_surf = None  # 保存原始图片用于高质量缩放
        if head_path:
            self._load_head_image(head_path, size)

    def _find_avatar_path(self, name: str) -> str:
        """根据角色名查找头像路径"""
        for path_template in self.AVATAR_SEARCH_PATHS:
            path = resource_path(path_template.format(name=name))
            if os.path.exists(path):
                return path
        return None

    def _load_head_image(self, head_path, size):
        """加载头像图片，使用平滑缩放"""
        try:
            # 如果传入的是角色名而非完整路径，尝试查找
            if not os.path.exists(head_path):
                # 尝试从路径中提取角色名
                name = os.path.splitext(os.path.basename(head_path))[0]
                found_path = self._find_avatar_path(name)
                if found_path:
                    head_path = found_path
                else:
                    print(f"[Appearance] 未找到头像: {name}")
                    self._original_surf = None
                    self.head_surf = None
                    return
            
            # 加载原始图片
            img = pygame.image.load(head_path).convert_alpha()
            self._original_surf = img
            # 使用平滑缩放
            self.head_surf = self._smooth_scale(img, size)
        except (FileNotFoundError, pygame.error) as e:
            print(f"[Appearance] 无法加载头像 {head_path}: {e}")
            self._original_surf = None
            self.head_surf = None

    def _smooth_scale(self, surface, size):
        """使用平滑算法缩放图片，减少锯齿"""
        orig_w, orig_h = surface.get_size()
        target_w, target_h = size
        
        # 如果目标尺寸比原始尺寸大，使用平滑缩放
        # 如果目标尺寸比原始尺寸小很多，使用多步缩放减少锯齿
        if target_w < orig_w // 4 or target_h < orig_h // 4:
            # 大幅缩小：分两步缩放，减少锯齿
            mid_w = orig_w // 2
            mid_h = orig_h // 2
            mid_surf = pygame.transform.smoothscale(surface, (mid_w, mid_h))
            return pygame.transform.smoothscale(mid_surf, size)
        else:
            # 普通缩放：使用smoothscale
            return pygame.transform.smoothscale(surface, size)

    def get_head_surface(self, size=None):
        """获取头像surface，可指定大小，使用平滑缩放"""
        if not self._original_surf:
            return None
        if size and size != self.size:
            return self._smooth_scale(self._original_surf, size)
        return self.head_surf

    def set_head_image(self, head_path, size=None):
        """设置新的头像图片"""
        self.head_path = head_path
        if size is None:
            size = self.size
        self._load_head_image(head_path, size)

    @classmethod
    def get_avatar_path(cls, name: str) -> str:
        """类方法：获取角色头像路径（供其他模块使用）"""
        for path_template in cls.AVATAR_SEARCH_PATHS:
            path = resource_path(path_template.format(name=name))
            if os.path.exists(path):
                return path
        return None

# --- 飘字系统 ---
class FloatingText:
    def __init__(self, text, x, y, color=(255, 255, 255), duration=150, font_size=None):
        self.text = text
        self.raw_x = x # 保存原始坐标数据，可能是 'CENTER'
        self.raw_y = y
        self.color = color
        self.timer = duration
        self.max_duration = duration
        self.y_offset = 0
        # 自定义字体大小（None=使用外部传入的 font）
        self._font_size = font_size
        self._font_cache = None  # 延迟创建，避免 pygame 未初始化

    def _get_font(self, default_font):
        if self._font_size is None:
            return default_font
        if self._font_cache is None:
            self._font_cache = pygame.font.Font(None, self._font_size)
        return self._font_cache

    def update(self):
        self.timer -= 1
        self.y_offset -= 0.6 # 向上飘动（略快一点，战斗浮字更有冲击感）

    def draw(self, screen, font, cam=None):
        """
        cam : Camera 实例（可选）。传入时将世界坐标转换为屏幕坐标后绘制。
              'CENTER'/'CENTER' 坐标不受摄像机影响，始终居中显示。
        """
        if self.timer <= 0: return
        alpha = int(255 * (self.timer / self.max_duration))
        render_font = self._get_font(font)
        text_surf = render_font.render(self.text, True, self.color)
        text_surf.set_alpha(alpha)

        # 计算实际绘制坐标
        if self.raw_x == 'CENTER':
            draw_x = screen.get_width() // 2 - text_surf.get_width() // 2
            draw_y = screen.get_height() // 2 if self.raw_y == 'CENTER' else self.raw_y
        else:
            draw_x = self.raw_x
            draw_y = screen.get_height() // 2 if self.raw_y == 'CENTER' else self.raw_y
            # 有摄像机时转换坐标
            if cam is not None:
                draw_x, draw_y = cam.world_to_screen(draw_x, draw_y)

        final_y = draw_y + self.y_offset
        screen.blit(text_surf, (draw_x, final_y))

class FloatingTextManager:
    def __init__(self):
        self.texts = []

    def add_text(self, text, x, y, color=(255, 255, 255), size=None):
        """
        size: 字体大小(px)，None 则使用全局默认字体。
              战斗伤害建议 size=22，HP 状态建议 size=16。
        """
        self.texts.append(FloatingText(text, x, y, color, font_size=size))

    def update(self):
        for t in self.texts:
            t.update()
        self.texts = [t for t in self.texts if t.timer > 0]

    def draw(self, screen, font, cam=None):
        for t in self.texts:
            t.draw(screen, font, cam)


# --- 通用寻位函数 ---
import math

def find_safe_position_around(center_x, center_y, radius=60, occupied_positions=None, 
                               min_safe_dist=40, directions=8, world_map=None):
    """
    在指定中心点周围寻找一个不与其他位置重叠的安全位置。
    
    Args:
        center_x, center_y: 目标中心点（如建筑中心）
        radius: 距离中心点的理想半径（像素）
        occupied_positions: 已占用位置列表 [(x, y), ...] 或 [(x, y, name), ...]
        min_safe_dist: 与已占用位置的最小安全距离（像素）
        directions: 检查的方向数量（4=四方向, 8=八方向, 12=更精细）
        world_map: WorldMap实例，用于检测墙壁碰撞（可选）
    
    Returns:
        (x, y): 找到的安全位置坐标
        None: 如果所有方向都不安全
    
    Usage:
        # 寻找建筑周围的空位
        pos = find_safe_position_around(building.rect.centerx, building.rect.centery,
                                         radius=70, occupied_positions=[(npc1.x, npc1.y)])
        if pos:
            npc.rect.centerx, npc.rect.centery = pos
    """
    if occupied_positions is None:
        occupied_positions = []
    
    # 归一化 occupied_positions 为 (x, y) 元组列表
    occ_coords = []
    for p in occupied_positions:
        if len(p) >= 2:
            occ_coords.append((p[0], p[1]))
    
    # 生成候选方向（均匀分布在圆周上）
    angle_step = 2 * math.pi / directions
    candidates = []
    
    for i in range(directions):
        angle = i * angle_step
        dx = math.cos(angle) * radius
        dy = math.sin(angle) * radius
        cand_x = center_x + dx
        cand_y = center_y + dy
        
        # 检查与已占用位置的距离
        is_safe = True
        min_dist_to_occ = float('inf')
        for ox, oy in occ_coords:
            dist = math.hypot(cand_x - ox, cand_y - oy)
            min_dist_to_occ = min(min_dist_to_occ, dist)
            if dist < min_safe_dist:
                is_safe = False
                break
        
        # 检查墙壁碰撞（如果提供了 world_map）
        if is_safe and world_map:
            import pygame
            test_rect = pygame.Rect(cand_x - 16, cand_y - 24, 32, 48)  # 假设NPC尺寸
            if world_map.is_blocked(test_rect):
                is_safe = False
        
        if is_safe:
            candidates.append((cand_x, cand_y, min_dist_to_occ))
    
    if not candidates:
        # 尝试更大的半径
        for i in range(directions):
            angle = i * angle_step
            dx = math.cos(angle) * (radius * 1.5)
            dy = math.sin(angle) * (radius * 1.5)
            cand_x = center_x + dx
            cand_y = center_y + dy
            
            is_safe = True
            for ox, oy in occ_coords:
                if math.hypot(cand_x - ox, cand_y - oy) < min_safe_dist:
                    is_safe = False
                    break
            
            if is_safe and world_map:
                import pygame
                test_rect = pygame.Rect(cand_x - 16, cand_y - 24, 32, 48)
                if world_map.is_blocked(test_rect):
                    is_safe = False
            
            if is_safe:
                candidates.append((cand_x, cand_y, float('inf')))
    
    if not candidates:
        return None
    
    # 选择离其他占用位置最远的候选点（最不拥挤的位置）
    candidates.sort(key=lambda c: c[2], reverse=True)
    return (candidates[0][0], candidates[0][1])


def find_formation_positions(center_x, center_y, count, spacing=50, world_map=None):
    """
    在中心点周围生成多个均匀分布的位置，用于NPC队列/阵型。
    
    Args:
        center_x, center_y: 阵型中心
        count: 需要的位置数量
        spacing: 位置之间的间距（像素）
        world_map: WorldMap实例，用于检测墙壁碰撞（可选）
    
    Returns:
        [(x1, y1), (x2, y2), ...]: 位置列表
    
    Usage:
        # 生成5个NPC在建筑周围的阵型位置
        positions = find_formation_positions(building.rect.centerx, building.rect.centery, 5)
        for i, npc in enumerate(npcs[:5]):
            npc.rect.centerx, npc.rect.centery = positions[i]
    """
    if count <= 0:
        return []
    
    if count == 1:
        return [(center_x, center_y)]
    
    positions = []
    radius = spacing
    angle_step = 2 * math.pi / count
    
    for i in range(count):
        angle = i * angle_step - math.pi / 2  # 从正上方开始
        px = center_x + math.cos(angle) * radius
        py = center_y + math.sin(angle) * radius
        
        # 检查墙壁碰撞
        if world_map:
            import pygame
            test_rect = pygame.Rect(px - 16, py - 24, 32, 48)
            if world_map.is_blocked(test_rect):
                # 尝试向外偏移
                px = center_x + math.cos(angle) * (radius + 30)
                py = center_y + math.sin(angle) * (radius + 30)
        
        positions.append((px, py))
    
    return positions

