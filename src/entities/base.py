# --- src/entities/base.py ---
import pygame
from src.definitions import *
import math, random
from src.utils import log_game_event

class CardBase:
    def __init__(self, x, y, width, height, color=COLOR_CARD_BG):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = color
        self.card_type = "BASE"
        self.name = "卡牌" 
        
        # --- 堆叠链表结构 ---
        self.stack_parent = None  
        self.stack_child = None   
        
        # --- 交互状态 ---
        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        
        # --- 工作进度 ---
        self.work_timer = 0
        self.work_max = 0
        self.is_working = False
        
        self.last_recipe_id = None 
        
        self._pixel_x = float(x) # 私有：唯一的浮点坐标源
        self._pixel_y = float(y) # 私有：请使用 set_pos() 方法
        
        # 私有移动目标变量
        self._target_x = None
        self._target_y = None  
        self._target_obj = None
    # 单帧位移超过此像素值时，触发"瞬移"警告日志（无论是否选中）
    TELEPORT_WARN_THRESHOLD = 150

    # === 属性访问器 ===
    @property
    def pixel_x(self):
        """只读访问像素X坐标"""
        return self._pixel_x
    
    @property
    def pixel_y(self):
        """只读访问像素Y坐标"""
        return self._pixel_y
    
    @property
    def target_x(self):
        """只读访问目标X坐标"""
        return self._target_x
    
    @property
    def target_y(self):
        """只读访问目标Y坐标"""
        return self._target_y
    
    @property
    def target_obj(self):
        """只读访问目标对象"""
        return self._target_obj
    
    # 禁止直接设置这些属性
    @pixel_x.setter
    def pixel_x(self, value):
        raise AttributeError("请使用 set_pos() 方法设置坐标")
    
    @pixel_y.setter
    def pixel_y(self, value):
        raise AttributeError("请使用 set_pos() 方法设置坐标")
    
    @target_x.setter
    def target_x(self, value):
        raise AttributeError("请使用 set_movement_target() 方法设置移动目标")
    
    @target_y.setter
    def target_y(self, value):
        raise AttributeError("请使用 set_movement_target() 方法设置移动目标")
    
    @target_obj.setter
    def target_obj(self, value):
        raise AttributeError("请使用 set_target_obj() 方法设置目标对象")

    def set_pos(self, x, y, reason=None):
        """
        【核心接口】统一设置坐标
        修改：输入 x, y 为卡牌的【中心点】坐标。
        内部自动计算左上角 pixel_x/y 以维持 rect 同步，确保物理和渲染正确。
        【边界保护】自动限制坐标不超出地图边界。
        """
        # 0. 【边界保护】限制坐标在地图范围内
        #    使用全局边界常量，防止 NPC 被击退到地图外
        from src.definitions import WORLD_BOUNDARY_PADDING
        world_w = getattr(CardBase, '_world_width', 3000)  # 默认3000，由 main.py 设置
        world_h = getattr(CardBase, '_world_height', 2400)  # 默认2400，由 main.py 设置
        
        half_w = self.rect.width / 2
        half_h = self.rect.height / 2
        
        # 限制中心点坐标，确保卡牌不会超出边界
        x = max(half_w + WORLD_BOUNDARY_PADDING, min(world_w - half_w - WORLD_BOUNDARY_PADDING, x))
        y = max(half_h + WORLD_BOUNDARY_PADDING, min(world_h - half_h - WORLD_BOUNDARY_PADDING, y))
        
        # 1. 根据传入的中心点 (x,y)，反推左上角的浮点坐标
        # pixel_x/y 依然存储左上角，因为 Pygame 的 rect 依赖左上角
        # 记录调用前的中心坐标（用于调试）

        is_dbg = DEBUG_NPC_PATH_VERBOSE and getattr(self, 'debug_selected', False)

        old_cx = self.rect.centerx
        old_cy = self.rect.centery

        self._pixel_x = float(x) - self.rect.width / 2
        self._pixel_y = float(y) - self.rect.height / 2
        
        # 2. 同步 Rect (Rect 使用整数左上角)
        self.rect.x = int(self._pixel_x)
        self.rect.y = int(self._pixel_y)

        new_cx = self.rect.centerx
        new_cy = self.rect.centery

        # ── 瞬移检测：单帧位移过大时无条件打印 ──────────────────────
        import math as _math
        dist = _math.hypot(new_cx - old_cx, new_cy - old_cy)
        if dist >= CardBase.TELEPORT_WARN_THRESHOLD:
            import traceback
            stack = traceback.extract_stack()
            caller  = stack[-2]
            caller2 = stack[-3] if len(stack) >= 3 else None
            c2_info = f" ← {caller2.filename.split('/')[-1].split(chr(92))[-1]}:{caller2.lineno}" if caller2 else ""
            log_game_event(
                f"[TELEPORT!] {self.name}  ({old_cx},{old_cy})->({new_cx},{new_cy})"
                f"  Δ={dist:.0f}px  reason={reason}"
                f"  @ {caller.filename.split('/')[-1].split(chr(92))[-1]}:{caller.lineno}{c2_info}"
            )
            

        # 调试：追踪选中NPC的坐标变化来源
        if is_dbg:
            log_game_event(f"[SET_POS_PRE] {self.name} set_pos({x:.1f}, {y:.1f}) reason={reason} before ({old_cx},{old_cy}) after ({new_cx},{new_cy})", tag="MOVEMENT")

            if old_cx != new_cx or old_cy != new_cy:
                import traceback
                stack = traceback.extract_stack()
                caller = stack[-2]
                caller2 = stack[-3] if len(stack) >= 3 else None
                c2_info = f" ← {caller2.filename.split('/')[-1].split(chr(92))[-1]}:{caller2.lineno}" if caller2 else ""
                log_game_event(f"[SET_POS] {self.name} center ({old_cx},{old_cy})→({new_cx},{new_cy}) reason={reason} @ {caller.filename.split('/')[-1].split(chr(92))[-1]}:{caller.lineno}{c2_info}", tag="MOVEMENT")
        
        # 3. 级联更新子卡牌位置 (实现堆叠跟随)
        if self.stack_child:      
            self.stack_child.set_pos(self.rect.centerx, self.rect.centery + STACK_OFFSET_Y)
 
            
    def move_ip(self, dx, dy):
        """增量移动"""
        self.set_pos(self.rect.centerx + dx, self.rect.centery + dy)
    def follow_stack(self, target_x, target_y):
        # 使用 set_pos 替代直接赋值
        self.set_pos(target_x, target_y)
     
    def start_drag(self, mx, my):
        # [!] 重伤状态的"自己"禁止拖拽（玩家重伤时需要等待救援）
        # 但允许被别人拖拽（玩家可以背起重伤NPC）
        # 这个检查会在 InteractionManager 中进行更细致的判断
        # 这里只阻止卡牌自身的拖拽初始化
        # 注：此检查已移至 InteractionManager，这里保持开放
        
        self.dragging = True
        self.drag_offset_x = self.rect.centerx - mx
        self.drag_offset_y = self.rect.centery - my
        # [修复] 不要立即清除工作状态和断开堆叠，等确认真正拖拽时再处理
        # self.last_recipe_id = None
        # self.is_working = False
        # self.work_timer = 0
        # self.recipe_proxy = None # 确保代理也被清除
        
        # [修复] 不要立即断开父级堆叠，交互系统会在确认拖拽时处理
        # if self.stack_parent:
        #     self.stack_parent.stack_child = None
        #     self.stack_parent = None
        return True  # 允许拖拽
    def get_all_children(self):
        """[新增] 获取所有下游堆叠的子卡牌，用于防止循环堆叠"""
        children = []
        curr = self.stack_child
        while curr:
            children.append(curr)
            curr = curr.stack_child
        return children

    def update_drag_pos(self, mx, my):
        if self.dragging:
            # 使用 set_pos 替代直接赋值
            self.set_pos(mx + self.drag_offset_x, my + self.drag_offset_y)
            
 

    def stop_drag(self):
        self.dragging = False

    def get_root(self):
        curr = self
        while curr.stack_parent:
            curr = curr.stack_parent
        return curr

    def bounce_off(self, target_card, distance=60,world_map=None,howToProcessChild=None):
        if not target_card: return
        if(self.stack_parent != target_card and self.stack_child != target_card):
            return
        self.last_recipe_id = None

        old_parent = self.stack_parent
        old_child = self.stack_child
        # 断开堆叠关系
        if self.stack_parent == target_card:
            self.stack_parent.stack_child = None
            self.stack_parent = None
        elif target_card.stack_parent == self:
            target_card.stack_parent.stack_child = None
            target_card.stack_parent = None
            
        # [修复] 完全断开自己的所有堆叠关系，防止级联传送


        if old_child:
            if howToProcessChild == "remove":
                old_child.stack_parent = None
                self.stack_child = None
            elif howToProcessChild == "connectToParent":
                if old_parent:
                    old_parent.stack_child = old_child
                    old_child.stack_parent = old_parent
                    self.stack_child = None
             
            
        # 物理位移
        dx = self.rect.centerx - target_card.rect.centerx
        dy = self.rect.centery - target_card.rect.centery
        
        # 如果重叠太完美，给个随机方向
        if dx == 0 and dy == 0: 
            dx = random.randint(-10, 10)
            dy = random.randint(-10, 10)
            
        length = math.hypot(dx, dy)
        if length == 0: length = 1
        
        # 归一化并应用力度
        push_x = (dx / length) * distance
        push_y = (dy / length) * distance
        
       
        self.move_ip(push_x, push_y)

        
    
    def set_movement_target(self, target_x, target_y, reason="未指定原因"):
        """
        统一的移动目标设置函数
        - 确保 target_x 和 target_y 始终同步设置
        - 提供详细的调用日志用于调试
        - 外部禁止直接修改 self.target_x 和 self.target_y
        - 【防重叠冷却】：网格系统调整位置后会设置冷却期，冷却期内拒绝新目标
        
        Args:
            target_x: 目标X坐标，None表示停止移动
            target_y: 目标Y坐标，None表示停止移动  
            reason: 设置原因，用于调试日志
        """
        # 【防重叠冷却检查】
        # 如果网格系统刚刚调整了位置，暂时拒绝AI设置新目标，防止反复弹开循环
        cooldown = getattr(self, '_grid_adjust_cooldown', 0)
        if cooldown > 0 and target_x is not None:
            # 冷却中，拒绝设置新目标（但允许清除目标）
            is_dbg = (DEBUG_NPC_PATH_VERBOSE and getattr(self, 'debug_selected', False))
            if is_dbg:
                log_game_event(f"[移动目标] {self.name} 网格调整冷却中({cooldown}帧)，拒绝设置新目标 原因:{reason}", tag="GRID")
            return (self._target_x, self._target_y)
        
        old_target = (self._target_x, self._target_y)
        self._target_x = target_x
        self._target_y = target_y


        
        # 记录详细日志
        agent_state = getattr(self, 'state', 'UNKNOWN')
        is_carrying = (agent_state == 'CARRYING')
        is_dbg = (DEBUG_NPC_PATH_VERBOSE and getattr(self, 'debug_selected', False)) or \
                 (DEBUG_PLAYER_PATH and getattr(self, 'job', '') == 'PLAYER') 
        
        if is_dbg: 
            current_pos = f"({self.rect.centerx},{self.rect.centery})" if hasattr(self, 'rect') else "(?,?)"
            new_target = f"({target_x},{target_y})" if target_x is not None else "停止移动"
            log_game_event(f"[移动目标] {self.name} {current_pos} → {new_target} 原因:{reason} 状态:{agent_state}", tag="MOVEMENT")
        
        return old_target
    
    def clear_movement_target(self, reason="未指定原因"):
        """停止移动的便捷函数"""
        self.clear_target_obj(reason)
        return self.set_movement_target(None, None, reason)
    def clear_target_obj(self, reason="未指定原因"):
        """清理目标对象的便捷函数"""
        self._target_obj = None
        return
    def set_target_obj(self, obj, reason="未指定原因"):
        """设置目标对象的便捷函数"""
        old_obj = self._target_obj
        self._target_obj = obj      
        return
    def draw_card_bg(self, screen, font_sys, showName=None, skip_name=False):
        """
        统一绘制卡牌背景、边框和顶部标题栏
        
        边框会向外扩展绘制，不遮挡卡牌内容
        
        Args:
            skip_name: 如果为True，跳过名字绘制（让子类自己处理）
        """
        # 1. 绘制卡牌底色
        pygame.draw.rect(screen, self.color, self.rect, border_radius=6)
        
        # 2. 绘制标题栏（顶部深色条）- 先绘制，在边框之前
        header_h = CARD_HEADER_H
        header_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, header_h)
        # 标题栏颜色：深灰半透明
        pygame.draw.rect(screen, (40, 40, 50), header_rect, border_top_left_radius=6, border_top_right_radius=6)
        
        # 3. 选中/拖拽高亮边框 OR 势力颜色边框（外扩绘制）
        if self.dragging:
            border_color = COLOR_HIGHLIGHT
            border_width = 3
        else:
            # 尝试获取势力可视化信息
            faction_visual = self._get_faction_visual()
            if faction_visual:
                border_color = faction_visual['color']
                border_width = faction_visual['border_width']
            else:
                border_color = COLOR_CARD_BORDER
                border_width = 2
        
        # 外扩边框：创建一个比原卡牌稍大的矩形来绘制边框
        # 这样边框不会遮挡卡牌内部内容
        outer_rect = self.rect.inflate(border_width, border_width)
        pygame.draw.rect(screen, border_color, outer_rect, border_width, border_radius=8)
        
        # 4. 在标题栏绘制名字 (白色字体) - 子类可以跳过自己处理
        if not skip_name:
            if showName:
                name_str = showName
            else:
                name_str = self.name
                
            # [逻辑] 重伤时在名字后面显示血量百分比
            if hasattr(self, 'safety') and hasattr(self, 'hp') and hasattr(self, 'max_hp'):
                from src.definitions import SAFETY_DOWNED
                if self.safety == SAFETY_DOWNED and self.max_hp > 0:
                    hp_pct = int((self.hp / self.max_hp) * 100)
                    name_str = f"{name_str} {hp_pct}%"
            
            # 如果名字太长，截断一下
            if len(name_str) > 8: name_str = name_str[:7] + ".."
            
            title_surf = font_sys.render(name_str, True, (255, 255, 255))
            # 居中显示名字
            screen.blit(title_surf, (self.rect.centerx - title_surf.get_width()//2, self.rect.y + 2))

        # 5. 进度条绘制 (如果在工作)
        if self.is_working and self.work_max > 0:
            # [调试] 追踪谁在显示进度条
            from src.utils import log_game_event
            # 避免循环导入，通过类名字符串检查
            if hasattr(self, 'job') and hasattr(self, 'stack_parent') and self.stack_parent:  # 是NPC
                parent_is_npc = hasattr(self.stack_parent, 'job')  # stack_parent也是NPC
                parent_is_clinic = hasattr(self.stack_parent, 'building_type') and self.stack_parent.building_type == 'CLINIC'
                
          
            bar_w = self.rect.width - 8
            bar_h = 4
            bx = self.rect.x + 4
            by = self.rect.y + 22  #
            pct = min(1.0, self.work_timer / self.work_max)
            pygame.draw.rect(screen, COLOR_PROGRESS_BG, (bx, by, bar_w, bar_h))
            pygame.draw.rect(screen, COLOR_PROGRESS_BAR, (bx, by, bar_w * pct, bar_h))

    def _get_faction_visual(self):
        """
        获取卡牌的势力可视化信息
        
        Returns:
            dict 或 None - 包含 'color' 和 'border_width' 的字典
            如果卡牌没有势力属性，返回 None
        """
        # 只有有 job 属性的才是 NPC/Player，才需要势力颜色
        if not hasattr(self, 'job'):
            return None
        
        try:
            from src.faction_colors import get_npc_faction_visual
            return get_npc_faction_visual(self)
        except Exception:
            return None

    def draw(self, screen, font):
        """默认绘制方法，子类可覆盖"""
        self.draw_card_bg(screen, font)
