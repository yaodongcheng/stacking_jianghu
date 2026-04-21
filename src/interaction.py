# --- src/interaction.py ---
import math
import pygame
from src.definitions import *
from src.entities import NPC, Player, Building, Resource
from src.utils import log_game_event

# 玩家拖拽操作范围（像素）
PLAYER_DRAG_RANGE = 100

class InteractionManager:
    """
    负责处理卡牌的物理交互：点击、拖拽、堆叠判定
    """
    def __init__(self):
        self.dragged_card = None
        self.mouse_down_pos = (0, 0)
        self.is_dragging = False
        
        # 【新增】拖拽范围限制相关
        self._player_ref = None           # 玩家引用（用于计算操作范围）
        self._drag_center = (0, 0)        # 拖拽开始时的玩家中心位置
        self._show_drag_circle = False    # 是否显示拖拽范围圈
    
    
    def handle_mouse_down(self, mx, my, all_cards, player, is_paused=False):
        """
        处理鼠标按下
        返回: Boolean (是否捕获了卡牌)
        """
        self.mouse_down_pos = (mx, my)
        self.dragged_card = None
        self.is_dragging = False
        self._player_ref = player
        self._show_drag_circle = False
        self._undraggable_click = False  # 重置不可拖拽点击标记
        def get_stack_depth(card):
                depth = 0
                curr = card
                while curr.stack_parent:
                    depth += 1
                    curr = curr.stack_parent
                return depth
        sorted_cards_by_depth = sorted(all_cards, key=get_stack_depth)
        # 逆序遍历，优先选中渲染层最上层（List末尾）的卡牌
        for card in reversed(sorted_cards_by_depth):
            if card.rect.collidepoint(mx, my):
                can_drag = True
                if card == player:
                    # 【新增】玩家自己重伤时不能被拖拽
                    if player and player.safety == SAFETY_DOWNED:
                        can_drag = False
                    else:
                        can_drag = True
                # 2. NPC 判断
                elif isinstance(card, NPC):
                    is_follower = getattr(card, 'is_follower', False)
                    is_refugee = getattr(card, 'is_refugee', False) # 或者是 job == 'NONE'
                    is_downed = card.safety == SAFETY_DOWNED  # 重伤倒地的NPC可以被背起
                    
                    if is_follower:
                        can_drag = True # 自己的门客可以动
                    elif is_refugee:
                        can_drag = True # 流民可以动（引导）
                    elif is_downed:
                        can_drag = True # 重伤NPC可以被拖拽（让玩家背起来送医）
                    else:
                        can_drag = False # 其他路人（张三李四）不可动，只能点击交互
                
                # 3. 建筑不可拖拽
                elif isinstance(card, Building):
                    can_drag = False  # 建筑是固定的，不可拖拽
                elif isinstance(card, Resource):
                    can_drag = True
                
                if is_paused:
                    can_drag = False
                
                # [核心修复] 只有可拖拽的卡牌才设置为 dragged_card
                # 不可拖拽的卡牌（如建筑）只用于点击检测，不应该进入拖拽流程
                if can_drag:
                    self.dragged_card = card
                    # [修复] 延迟断开堆叠关系，只有真正拖拽时才断开
                    # 先记录原始堆叠关系，但不立即断开
                    self._original_parent = getattr(card, 'stack_parent', None)
                    self._original_child = getattr(self._original_parent, 'stack_child', None) if self._original_parent else None

                    self.dragged_card.start_drag(mx, my)
                    
                    # 【新增】记录拖拽开始时玩家的中心位置，作为操作圈圆心
                    if player and card != player:
                        self._drag_center = (player.rect.centerx, player.rect.centery)
                        self._show_drag_circle = True
                    else:
                        # 玩家拖拽自己时不限制范围
                        self._drag_center = (mx, my)
                        self._show_drag_circle = False
                else:
                    # 不可拖拽的卡牌：仍然记录下来用于点击判定，但标记为不可拖拽
                    self.dragged_card = card
                    self._undraggable_click = True  # 标记：这是一个不可拖拽的点击
                
                # 无论是否可拖拽，只要点到了卡牌，都返回 True
                return True
               
        return False

    def handle_mouse_up(self, mx, my, all_cards, player, quest_manager=None, recipe_manager=None):
        """
        处理鼠标抬起
        返回: (ActionType, TargetObj)
        ActionType: 'CLICK', 'STACK', 'NONE'
        TargetObj: 交互的目标对象
        """
        if not self.dragged_card:
            self.on_drag_end()  # 清理拖拽状态
            return 'NONE', None

        # 计算位移距离，判断是点击还是拖拽
        dist = math.hypot(mx - self.mouse_down_pos[0], my - self.mouse_down_pos[1])
        card = self.dragged_card
        self.dragged_card = None
        was_dragged=card.dragging 
        card.dragging = False # 停止物理拖拽状态

        # 1. 判定为点击（位移阈值：Resource 用 20px，其他 12px，防止轻点误触拖拽）
        click_thresh = 20 if isinstance(card, Resource) else 12
        if dist < click_thresh:
            self.on_drag_end()  # 清理拖拽状态
            # 如果点的是 NPC/Resource/Building，返回 CLICK 事件
            if isinstance(card, NPC):
                return 'CLICK', card
            elif isinstance(card, Resource):
                return 'CLICK', card
            elif isinstance(card, Building):
                return 'CLICK', card
            return 'NONE', None

        # 2. 判定为拖拽结束 -> 处理堆叠吸附
        else:
            if not was_dragged:
                return 'NONE', None
            
            # [修复] 真正拖拽时才断开堆叠关系和清理工作状态
            if hasattr(self, '_original_parent') and self._original_parent:
                self._original_parent.stack_child = None
                card.stack_parent = None
                log_game_event(f"[INTERACTION] {card.name} 离开了 {self._original_parent.name}", tag="INTERACTION")
            
            # 真正拖拽时清理工作状态
            card.last_recipe_id = None
            card.is_working = False
            card.work_timer = 0
            if hasattr(card, 'recipe_proxy'):
                card.recipe_proxy = None
            best_target = None
            candidates = []
            for target in all_cards:
                # 自己不能叠自己，也不能叠在自己的子卡上（防止死循环）
                if target == card: continue
                if target in card.get_all_children(): continue 
                
                # 简单的矩形碰撞检测
                if card.rect.colliderect(target.rect):
                    # 计算中心点距离，用于筛选最近的目标
                    d = math.hypot(card.rect.centerx - target.rect.centerx, card.rect.centery - target.rect.centery)
                    candidates.append((d, target))
            
            # 如果没有重叠对象
            if not candidates:
                print(f"没找到重叠对象")
                return 'NONE', None

            # 按照距离排序，选最近的一个 (d, target)
            candidates.sort(key=lambda x: x[0])
            best_target = candidates[0][1]
            
            
            if best_target:
                if quest_manager:
                    allowed, reason = quest_manager.check_action_allowed(card, best_target, recipe_manager)
                    if not allowed:
                        print(f"DENY DRAG {reason}")
                        return 'DENIED', reason
                #资源 -> 资源 (同类合并)
                if isinstance(card, Resource) and isinstance(best_target, Resource):
                    if card.item_type == best_target.item_type:
                        best_target.count += card.count
                        # 返回 MERGE 动作，让 Main 移除 card
                        return 'MERGE_RESOURCE', card 
                #资源 -> NPC 塞入背包
                if isinstance(card, Resource) and isinstance(best_target, NPC):
                    # 检查是否能堆叠（比如背包满了），这里简化为无限背包或简单逻辑
                    # 只有活人能捡
                    if best_target.safety not in ['DEAD', 'EXILED']:
                        # 【新增】检查是否是交付任务
                        if quest_manager:
                            is_delivery = quest_manager.on_item_delivered(
                                card.item_type, 
                                card.count, 
                                best_target,
                                player,
                                ft_manager=None  # 将由外部处理
                            )
                            if is_delivery:
                                # 物品被交付任务消耗，不放入NPC背包
                                return 'DELIVER_ITEM', (card, best_target)
                        
                        # 正常放入背包（走 add_item 收口，is_player 时会自动通知 QuestManager）
                        best_target.add_item(card.item_type, card.count, reason="pickup_resource")
                        return 'PICKUP_RESOURCE', card
                # [关键逻辑] 找到堆叠链的最末端
                # 如果 best_target 已经身上有人了，就往它下面找，直到找到空位
                # 比如：拖拽 NPC 到 房子 上，如果房子里已经有人，就叠在这个人下面
                top_card = best_target
                loop_guard = 0
                while top_card.stack_child and top_card.stack_child != card and loop_guard < 20:
                    top_card = top_card.stack_child
                    loop_guard += 1
                print(f"\n[DEBUG] 发生堆叠:")
                print(f"  > 子卡 (拖拽): {card.name} (Job: {getattr(card, 'job', 'N/A')}, ID: {getattr(card, 'id', 'N/A')})")
                print(f"  > 父卡 (目标): {top_card.name} (Type: {getattr(top_card, 'building_type', 'NPC')})")
                if hasattr(card, 'job'): print(f"  > 子卡 Job状态: '{card.job}' (期望 'NONE' 为流民)")
                if hasattr(top_card, 'building_type'): print(f"  > 父卡建筑类型: '{top_card.building_type}' (期望 'GRANARY')")
                
                # 【手续费系统】检测建筑使用费
                # 只对玩家或门客堆叠到建筑时触发
                fee_check_result = self._check_building_fee(card, best_target, player)
                if fee_check_result:
                    # 返回手续费确认请求，让主循环处理弹窗
                    return 'FEE_REQUIRED', fee_check_result
                
                # 建立双向链表关系
                if top_card != card:
                    top_card.stack_child = card
                    card.stack_parent = top_card
                    
                    # 立即吸附位置（统一走 set_pos，中心点坐标）
                    card.set_pos(top_card.rect.centerx,
                                 top_card.rect.centery + STACK_OFFSET_Y)
                    
                    return 'STACK', top_card

        return 'NONE', None

    def update(self, mx, my):
        """
        每帧更新拖拽位置
        【新增】范围限制：当拖拽非玩家对象时，限制在玩家周围 PLAYER_DRAG_RANGE 像素内
        """
        if self.dragged_card:
            # 如果启用了拖拽范围限制（拖拽的不是玩家自己）
            if self._show_drag_circle and self._player_ref:
                # 计算鼠标位置到玩家中心的距离
                cx, cy = self._drag_center
                dist = math.hypot(mx - cx, my - cy)
                
                # 如果超出范围，将位置钳制到圆周上
                if dist > PLAYER_DRAG_RANGE:
                    # 计算方向向量并归一化
                    angle = math.atan2(my - cy, mx - cx)
                    clamped_x = cx + PLAYER_DRAG_RANGE * math.cos(angle)
                    clamped_y = cy + PLAYER_DRAG_RANGE * math.sin(angle)
                    self.dragged_card.update_drag_pos(clamped_x, clamped_y)
                else:
                    self.dragged_card.update_drag_pos(mx, my)
            else:
                # 玩家自己拖拽不受范围限制
                self.dragged_card.update_drag_pos(mx, my)
    
    def get_drag_circle_info(self):
        """
        获取拖拽操作圈的绘制信息
        返回: (center_x, center_y, radius) 或 None（不需要绘制时）
        """
        if self._show_drag_circle and self.dragged_card:
            return (self._drag_center[0], self._drag_center[1], PLAYER_DRAG_RANGE)
        return None
    
    def on_drag_end(self):
        """拖拽结束时的清理"""
        self._show_drag_circle = False
    
    def _check_building_fee(self, dragged_card, target, player):
        """
        【手续费系统】检测是否需要支付建筑使用费
        
        Args:
            dragged_card: 被拖拽的卡牌（玩家/NPC/资源）
            target: 目标卡牌（可能是建筑）
            player: 玩家引用
            
        Returns:
            dict 或 None - 如果需要手续费，返回费用信息字典；否则返回 None
        """
        from src.faction_war_system import get_faction_war_system
        
        # 找到实际的建筑目标（可能是目标本身，或者堆叠链中的某个建筑）
        building_target = None
        current = target
        loop_guard = 0
        while current and loop_guard < 20:
            if isinstance(current, Building):
                building_target = current
                break
            current = getattr(current, 'stack_parent', None)
            loop_guard += 1
        
        if not building_target:
            return None  # 没有建筑参与，不需要手续费
        
        # 确定谁是使用者（付费人）
        # 玩家拖拽自己 -> 玩家付费
        # 玩家拖拽门客 -> 玩家付费
        # 玩家拖拽物资到建筑 -> 玩家付费
        user_entity = player
        
        # 如果拖拽的是门客，使用者仍然是玩家（因为是玩家操作）
        if isinstance(dragged_card, NPC):
            if dragged_card == player:
                user_entity = player
            elif getattr(dragged_card, 'is_follower', False):
                user_entity = player  # 门客的操作由玩家承担费用
            else:
                return None  # 非玩家控制的NPC不触发手续费确认
        elif isinstance(dragged_card, Resource):
            user_entity = player
        elif dragged_card == player:
            user_entity = player
        else:
            return None  # 其他情况不处理
        
        # 获取势力战争系统并计算费用
        faction_war = get_faction_war_system()
        fee_info = faction_war.calculate_usage_fee(user_entity, building_target)
        
        # 如果免费且不是敌对势力，不需要确认
        # 注意：敌对势力即使费用为0也需要弹出警告！
        if fee_info['fee'] <= 0 and not fee_info.get('is_hostile', False):
            return None
        
        # 需要手续费或敌对警告，返回确认信息
        return {
            'user': user_entity,
            'building': building_target,
            'fee_info': fee_info,
            'stack_target': target,
            'dragged_card': dragged_card,
        }

    def manual_stack(self, child_card, parent_card, all_cards):
        """
        [核心功能] 强制执行堆叠（用于自动吸附、事件跳转等）
        让 child_card 瞬间吸附到 parent_card 上，并处理好所有指针关系
        """
        # 1. 如果 child 已经在别的上面，先断开旧关系
        if child_card.stack_parent: 
            child_card.stack_parent.stack_child = None
        
        # 2. 建立新关系
        # 注意：这里我们简单地覆盖 parent 的 child。
        # 如果 parent 已经有 child 了，原来的 child 会变成孤儿（符合预期，被顶替）
        # 或者你可以选择把它叠在链条末端，视游戏设计而定。这里采用直接吸附模式。
        if parent_card.stack_child:
            parent_card.stack_child.stack_parent = None # 断开旧的子卡
            
        child_card.stack_parent = parent_card
        parent_card.stack_child = child_card
        
        # 3. 物理瞬移 (同步 rect 和 pixel)       
        child_card.set_pos(parent_card.rect.centerx, parent_card.rect.centery + STACK_OFFSET_Y)
        
        # 4. 提到渲染层最上层 (确保显示在父卡上方)
        if child_card in all_cards:
            all_cards.remove(child_card)
            all_cards.append(child_card)