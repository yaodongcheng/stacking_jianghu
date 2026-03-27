# src/ui/story_ui.py
import pygame
import math
from src.definitions import *
from src.utils import wrap_text, load_image
from src.ui.choice_tooltip import ChoiceTooltipHelper

class StoryUI:
    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        
        # 字体初始化
        font_names = "microsoftyahei,simhei,pingfangsc,notosanscjk,arial"
        self.font_avg = pygame.font.SysFont(font_names, 20)
        self.font_name = pygame.font.SysFont(font_names, 22, bold=True)
        self.font_quest_big = pygame.font.SysFont(font_names, 48, bold=True)        
        self.font_big = pygame.font.SysFont(font_names, 24) # 序章用大字体
        self.font_quest = pygame.font.SysFont(font_names, 48, bold=True)
        self.font_choice = pygame.font.SysFont(font_names, 22, bold=True)  # 选择按钮字体
        self.font_hint = pygame.font.SysFont(font_names, 16)  # 选择提示字体
        self.font_bubble = pygame.font.SysFont(font_names, 18)  # 气泡文字字体
        self.font_bubble_name = pygame.font.SysFont(font_names, 16, bold=True)  # 气泡名字字体
        
        # 字体缓存（用于tooltip）
        self._font_cache = {}
        
        # AVG 对话状态
        self.dialog_queue = [] 
        self.current_line = None
        self.is_active = False
        self.char_index = 0
        self.timer = 0
        self.bg_image_surf = None # 当前背景图缓存
        self.current_bg_path = ""
        
        # 任务标题动画状态
        self.quest_anim_active = False
        self.quest_title = ""
        self.anim_timer = 0
        self.anim_phase = 0 # 0:FadeIn, 1:Stay, 2:Move
        
        # 【新增】选择界面状态
        self.choice_mode = False           # 是否处于选择模式
        self.choice_options = []           # 当前选项列表
        self.choice_hover_index = -1       # 鼠标悬停的选项索引
        self.choice_buttons = []           # 按钮矩形区域列表
        self.choice_anim_timer = 0         # 选择界面动画计时器
        self.choice_prompt = ""            # 选择提示文字
        
        # 【新增】选项tooltip
        self.choice_tooltip = None  # {lines: [], btn_rect: Rect, alpha: float}
        
        # 【新增】缓存选择界面的遮罩层，避免每帧重建导致闪烁
        self._choice_overlay = None
        
        # 【新增】角色气泡式对话需要的引用
        self._camera_ref = None            # 摄像机引用（用于坐标转换）
        self._all_cards_ref = None         # 所有卡牌引用（用于查找说话者）
        
        # 【新增】剧情演员ID集合（剧情期间这些角色的移动不暂停）
        self.story_actor_ids = set()
        
        # 【新增】保存剧情演员进入剧情前的移动状态，用于剧情结束后恢复
        self._saved_movement_states = {}  # {npc_id: {'target_x': x, 'target_y': y, 'target_obj': obj, 'target_building': bld}}
        
        # 【新增】等待异步动作完成（如玩家靠近攻击）
        self.waiting_for_action = False
        self._pending_action_callback = None  # 动作完成后的回调
        self._action_triggered_for_line = False  # 当前行的动作是否已触发
        
    def start_dialog(self, dialog_datas):
        """开始一段对话 lines: [{'speaker':str, 'text':str, 'id':int}]"""
        self.dialog_queue = list(dialog_datas)
        
        # 【调试】打印开始的对话信息
        if dialog_datas:
            first_line = dialog_datas[0]
            quest_id = getattr(first_line, 'quest_id', '?')
            print(f"[StoryUI] ===== 开始对话 quest_id={quest_id} 共{len(dialog_datas)}句 =====")
        
        # 【新增】保存完整对话用于注入记忆
        self._current_dialog_data = list(dialog_datas)
        
        # 【新增】自动识别剧情演员：从对话中提取所有说话人ID
        self._extract_story_actors(dialog_datas)
        
        self._next_line()
        self.is_active = True
    
    def _extract_story_actors(self, dialog_datas):
        """从对话数据中提取所有说话人的ID，作为剧情演员"""
        self.story_actor_ids.clear()
        for d in dialog_datas:
            speaker_id = getattr(d, 'speaker_id', None)
            if speaker_id is not None:
                self.story_actor_ids.add(speaker_id)
        
        # 玩家始终是剧情演员（ID可能是0或9999）
        self.story_actor_ids.add(0)
        self.story_actor_ids.add(9999)
        
        print(f"[StoryUI] 剧情演员ID列表: {self.story_actor_ids}")
        
        # 【新增】保存剧情演员的移动状态并清除他们的移动目标
        self._save_and_clear_actor_movement()
    
    def _save_and_clear_actor_movement(self):
        """
        保存剧情演员的移动状态，并清除他们的移动目标
        用于确保剧情演出时角色不会因为之前的移动目标而乱跑
        """
        if not self._all_cards_ref:
            print("[StoryUI] 警告: 无法保存移动状态，_all_cards_ref 为空")
            return
        
        self._saved_movement_states.clear()
        
        for card in self._all_cards_ref:
            # 获取卡牌ID
            card_id = getattr(card, 'id', None)
            if card_id is None:
                # 尝试从 npc_data 获取
                npc_data = getattr(card, 'npc_data', None)
                if npc_data:
                    card_id = getattr(npc_data, 'id', None)
            
            # 检查是否是玩家
            is_player = getattr(card, 'is_player', False)
            if is_player:
                card_id = 9999  # 统一玩家ID
            
            # 检查是否是剧情演员
            if card_id is not None and card_id in self.story_actor_ids:
                # 保存移动状态
                state = {
                    'target_x': getattr(card, '_target_x', None),
                    'target_y': getattr(card, '_target_y', None),
                    'target_obj': getattr(card, '_target_obj', None),
                    'target_building': getattr(card, 'target_building', None),
                }
                self._saved_movement_states[card_id] = state
                
                # 清除移动目标（使用安全方法）
                if hasattr(card, 'clear_movement_target'):
                    card.clear_movement_target("进入剧情演出，暂停原移动")
                    print(f"[StoryUI] 保存并清除 {getattr(card, 'name', card_id)} 的移动状态: ({state['target_x']}, {state['target_y']})")
    
    def _restore_actor_movement(self):
        """
        恢复剧情演员之前保存的移动状态
        在剧情结束时调用
        """
        if not self._all_cards_ref or not self._saved_movement_states:
            return
        
        for card in self._all_cards_ref:
            # 获取卡牌ID
            card_id = getattr(card, 'id', None)
            if card_id is None:
                npc_data = getattr(card, 'npc_data', None)
                if npc_data:
                    card_id = getattr(npc_data, 'id', None)
            
            # 检查是否是玩家
            is_player = getattr(card, 'is_player', False)
            if is_player:
                card_id = 9999
            
            # 检查是否有保存的状态
            if card_id is not None and card_id in self._saved_movement_states:
                state = self._saved_movement_states[card_id]
                
                # 恢复移动目标
                if state['target_x'] is not None and state['target_y'] is not None:
                    if hasattr(card, 'set_movement_target'):
                        card.set_movement_target(state['target_x'], state['target_y'], "剧情结束，恢复原移动目标")
                        print(f"[StoryUI] 恢复 {getattr(card, 'name', card_id)} 的移动状态: ({state['target_x']}, {state['target_y']})")
                
                # 恢复目标对象
                if state['target_obj'] is not None and hasattr(card, 'set_target_obj'):
                    card.set_target_obj(state['target_obj'], "剧情结束，恢复目标对象")
                
                # 恢复目标建筑
                if state['target_building'] is not None:
                    card.target_building = state['target_building']
        
        # 清理保存的状态
        self._saved_movement_states.clear()
        print("[StoryUI] 剧情演员移动状态已恢复")

    def _next_line(self):
        if self.dialog_queue:
            self.current_line = self.dialog_queue.pop(0)
            print(f"{self.current_line.text}")
            self.char_index = 0
            self.timer = 0
            self._action_triggered_for_line = False  # 重置动作触发标记
            new_bg = self.current_line.bg_img
            if new_bg and new_bg != self.current_bg_path:
                self.current_bg_path = new_bg
                # 加载并缩放图片
                raw_img = load_image(new_bg)
                # 简单居中缩放适配
                scale = max(self.screen_w / raw_img.get_width(), self.screen_h / raw_img.get_height())
                new_size = (int(raw_img.get_width() * scale), int(raw_img.get_height() * scale))
                self.bg_image_surf = pygame.transform.scale(raw_img, new_size)
            elif not new_bg:
                self.bg_image_surf = None # 清除背景
                self.current_bg_path = ""

            # 执行回调
            if self.current_line.action:
                # 这里需要在外部传入 QuestManager 引用，或者在 Main 里执行
                # 为简化，我们在 get_current_action 里处理
                pass
           
        else:
            self.current_line = None
            self.is_active = False # 对话结束
            self.bg_image_surf = None
            
            # 【新增】对话结束时恢复剧情演员的移动状态
            self._restore_actor_movement()

    def show_quest_title(self, title):
        """触发屏幕中央的大标题动画"""
        self.quest_title = title
        self.quest_anim_active = True
        self.anim_timer = 0
        self.anim_phase = 0 
    def handle_input(self, event, ctx):
        """处理输入。返回 True 表示阻断其他输入"""
        quest_manager = ctx.quest_manager
        player = ctx.player
        
        if not self.is_active: 
            return False
        
        # 【新增】如果正在等待异步动作完成，阻止输入但不推进对话
        if self.waiting_for_action:
            return True  # 阻止所有输入，等待动作完成
        
        # 获取鼠标位置（如果是鼠标事件）
        mx, my = 0, 0
        if hasattr(event, 'pos'):
            mx, my = event.pos
        
        # 【重要】判断是否是全屏覆盖模式（序章有背景图）
        # 只有全屏模式才阻止NPC点击穿透
        is_fullscreen_mode = self.bg_image_surf is not None
        
        if event.type == pygame.MOUSEBUTTONDOWN or (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE):
            if not self.current_line: 
                return False
            
            # 打字机加速或下一句
            txt = self.current_line.text
            if self.char_index < len(txt):
                self.char_index = len(txt)
                # 只有在全屏模式才阻止穿透
                return is_fullscreen_mode
            else:
                # [核心修复] 只有在文本已经显示完整，再次点击准备下一句时，才触发动作
                # 使用 _action_triggered_for_line 标记防止同一句对话的动作被多次触发
                if quest_manager and self.current_line.action and not self._action_triggered_for_line:
                    self._action_triggered_for_line = True  # 标记为已触发
                    quest_manager.trigger_action(self.current_line.action, ctx)
                
                # 【新增】如果动作设置了等待标志，不推进对话
                if self.waiting_for_action:
                    return True  # 阻止输入，等待动作完成
                
                last_speaker_id = self.current_line.speaker_id 
                self._next_line()
                # 检查是否刚结束对话 -> 通知 QuestManager 推进
                if not self.is_active and quest_manager:
                    # 调用新方法，传入最后说话人的ID辅助判断
                    quest_manager.on_dialog_finished(npc_id=last_speaker_id, ctx=ctx)
                    
                    # 【新增】检查是否需要显示选择界面
                    if quest_manager.pending_choice_dialog:
                        quest_manager.pending_choice_dialog = False
                        options = quest_manager.get_choice_options()
                        if options:
                            q = quest_manager.get_current_quest()
                            prompt = q.title if q else "做出你的选择"
                            self.show_choice(options, prompt)
                # 对话推进后，阻止本次点击穿透（防止意外点到其他东西）
                return True
        
        # 非点击事件：全屏模式阻止其他输入，气泡模式允许穿透
        return is_fullscreen_mode


    def update(self):
        # AVG 打字机效果
        if self.is_active and self.current_line:
            full_text = self.current_line.text
            if self.char_index < len(full_text):
                self.char_index += 0.5 # 打字速度
        
        # 任务动画状态机
        if self.quest_anim_active:
            self.anim_timer += 1
            if self.anim_phase == 0: # 淡入 (0.5s)
                if self.anim_timer > 30: 
                    self.anim_phase = 1
                    self.anim_timer = 0
            elif self.anim_phase == 1: # 停留 (1.5s)
                if self.anim_timer > 90: 
                    self.anim_phase = 2
                    self.anim_timer = 0
            elif self.anim_phase == 2: # 移动到侧边栏 (1s)
                if self.anim_timer > 60:
                    self.quest_anim_active = False 

    def set_references(self, camera=None, all_cards=None):
        """设置气泡式对话需要的引用"""
        self._camera_ref = camera
        self._all_cards_ref = all_cards

    def draw(self, screen):
        if not self.is_active: 
            # 即使对话不激活，也要画任务标题动画
            self._draw_quest_anim(screen)
            return

        # 1. 绘制背景图 (如果是序章模式)
        if self.bg_image_surf:
            # 居中绘制
            rect = self.bg_image_surf.get_rect(center=(self.screen_w//2, self.screen_h//2))
            screen.blit(self.bg_image_surf, rect)
            
            # 序章模式的文字框 (底部大黑框)
            self._draw_prologue_text(screen)
        else:
            # 根据配置选择对话显示模式
            if DIALOG_DISPLAY_MODE == 'BUBBLE':
                self._draw_bubble_dialog(screen)
            else:
                # 底部字幕式
                self._draw_dialog_box(screen)

        self._draw_quest_anim(screen)


  
    def _draw_prologue_text(self, screen):
        """序章样式的文本框"""
        h = 200
        rect = pygame.Rect(50, self.screen_h - h - 50, self.screen_w - 100, h)
        
        s = pygame.Surface((rect.width, rect.height))
        s.set_alpha(200)
        s.fill((0,0,0))
        screen.blit(s, (rect.x, rect.y))
        pygame.draw.rect(screen, (255,255,255), rect, 2)
        
        txt = self.current_line.text
        display_txt = txt[:int(self.char_index)]
        lines = wrap_text(display_txt, self.font_big, rect.width - 60)
        
        y = rect.y + 40
        for line in lines:
            surf = self.font_big.render(line, True, (255, 255, 255))
            screen.blit(surf, (rect.x + 30, y))
            y += 35
            
        # 提示
        if int(self.char_index) >= len(txt):
            tip = self.font_avg.render(">>> 点击继续 >>>", True, (150, 150, 150))
            screen.blit(tip, (rect.right - 180, rect.bottom - 30))

    def _draw_dialog_box(self, screen):
        """普通交互对话框 - 底部字幕式，带头像显示"""
        panel_h = 180
        y_pos = self.screen_h - panel_h - 20
        x_pos = 100
        w = self.screen_w - 200
        
        s = pygame.Surface((w, panel_h))
        s.set_alpha(220)
        s.fill((25, 25, 30))
        screen.blit(s, (x_pos, y_pos))
        pygame.draw.rect(screen, (200, 200, 200), (x_pos, y_pos, w, panel_h), 2)
        
        # 获取说话者信息
        speaker_id = getattr(self.current_line, 'speaker_id', None)
        name = self.current_line.speaker
        
        # 绘制头像
        avatar_size = 64
        avatar_x = x_pos + 20
        avatar_y = y_pos + 20
        
        if name != 'NARRATOR' and speaker_id is not None:
            speaker_avatar = self._get_speaker_avatar(speaker_id, (avatar_size, avatar_size))
            if speaker_avatar:
                # 头像背景框
                avatar_bg_rect = pygame.Rect(avatar_x - 2, avatar_y - 2, avatar_size + 4, avatar_size + 4)
                pygame.draw.rect(screen, (60, 60, 70), avatar_bg_rect, border_radius=4)
                # 绘制头像
                screen.blit(speaker_avatar, (avatar_x, avatar_y))
                text_offset_x = avatar_x + avatar_size + 20
            else:
                text_offset_x = x_pos + 40
        else:
            text_offset_x = x_pos + 40
        
        # 名字
        if name != 'NARRATOR':
            name_surf = self.font_name.render(name, True, (255, 230, 100))
            screen.blit(name_surf, (text_offset_x, y_pos + 15))
        
        # 内容
        txt = self.current_line.text
        display_txt = txt[:int(self.char_index)]
        lines = wrap_text(display_txt, self.font_avg, w - 80 - (text_offset_x - x_pos - 40))
        
        y = y_pos + 50
        for line in lines:
            surf = self.font_avg.render(line, True, (255, 255, 255))
            screen.blit(surf, (text_offset_x, y))
            y += 28

    def _draw_bubble_dialog(self, screen):
        """气泡式对话 - 智能位置算法，避免遮挡角色，带头像显示"""
        if not self.current_line:
            return
        
        speaker_id = self.current_line.speaker_id
        speaker_name = self.current_line.speaker
        txt = self.current_line.text
        display_txt = txt[:int(self.char_index)]
        
        # 查找说话者的屏幕位置（返回卡牌中心和顶部）
        speaker_center_x, speaker_top_y = self._find_speaker_screen_pos(speaker_id)
        
        # 判断是否为系统旁白或找不到说话者
        is_narrator = (speaker_name == 'NARRATOR' or speaker_name == '旁白' or 
                       speaker_id is None or speaker_center_x is None)
        
        # 如果是旁白或找不到说话者，使用屏幕底部居中位置（无尖角）
        if is_narrator:
            self._draw_narrator_dialog(screen, display_txt, txt)
            return
        
        # 获取说话者头像
        speaker_avatar = self._get_speaker_avatar(speaker_id, (48, 48))
        
        # 气泡参数
        max_width = BUBBLE_MAX_WIDTH
        padding = 15
        line_height = 22
        avatar_size = 48
        name_height = 24 if speaker_name and speaker_name != 'NARRATOR' else 0
        
        # 【新布局】上下结构：第一行头像+名字，第二行文字
        # 文字区域可用宽度 = 最大宽度 - 两侧padding
        text_area_width = max_width - padding * 2
        
        # 计算文字行
        lines = wrap_text(display_txt, self.font_bubble, text_area_width)
        if not lines:
            lines = [""]
        
        # 计算气泡尺寸
        text_width = max(self.font_bubble.size(line)[0] for line in lines) if lines else 50
        
        # 第一行宽度：头像 + 名字
        name_width = 0
        if speaker_name and speaker_name != 'NARRATOR':
            name_surf_temp = self.font_bubble_name.render(f"【{speaker_name}】", True, BUBBLE_NAME_COLOR)
            name_width = name_surf_temp.get_width()
        
        if speaker_avatar:
            # 有头像时，第一行宽度 = 头像 + 间距 + 名字
            header_width = avatar_size + 10 + name_width
            # 气泡宽度 = max(第一行宽度, 文字宽度) + 两侧padding
            bubble_w = min(max_width, max(header_width, text_width) + padding * 2)
            # 气泡高度 = padding + 第一行(头像高度) + 间距 + 文字高度 + padding
            bubble_h = padding + max(avatar_size, name_height) + 10 + len(lines) * line_height + padding
        else:
            # 无头像时
            bubble_w = min(max_width, max(name_width, text_width) + padding * 2)
            bubble_h = padding + name_height + len(lines) * line_height + padding
        
        # ═══════════════════════════════════════════════════════════════
        # 【智能定位算法】检查四个方向的可用空间
        # ═══════════════════════════════════════════════════════════════
        
        CARD_WIDTH = 60    # 卡牌大约宽度
        CARD_HEIGHT = 90   # 卡牌大约高度
        GAP = 15           # 气泡与卡牌的间距
        SCREEN_MARGIN = 15 # 距离屏幕边缘的最小距离
        
        # 说话者卡牌的屏幕边界估算
        card_left = speaker_center_x - CARD_WIDTH // 2
        card_right = speaker_center_x + CARD_WIDTH // 2
        card_top = speaker_top_y
        card_bottom = speaker_top_y + CARD_HEIGHT
        
        # 评估各方向可用空间
        space_above = card_top - SCREEN_MARGIN                           # 上方空间
        space_below = self.screen_h - card_bottom - SCREEN_MARGIN        # 下方空间
        space_left = card_left - SCREEN_MARGIN                           # 左侧空间
        space_right = self.screen_w - card_right - SCREEN_MARGIN         # 右侧空间
        
        # 确定最佳位置（优先级：上 > 右 > 左 > 下）
        best_dir = 'ABOVE'  # 默认上方
        
        if space_above >= bubble_h + GAP:
            best_dir = 'ABOVE'
        elif space_right >= bubble_w + GAP:
            best_dir = 'RIGHT'
        elif space_left >= bubble_w + GAP:
            best_dir = 'LEFT'
        elif space_below >= bubble_h + GAP:
            best_dir = 'BELOW'
        else:
            # 空间都不够，选择空间最大的方向并压缩气泡
            best_dir = 'ABOVE'  # 兜底
        
        # 根据方向计算气泡位置和尖角锚点
        tail_x, tail_y = speaker_center_x, speaker_top_y  # 尖角指向
        tail_dir = 'DOWN'  # 尖角朝向
        
        if best_dir == 'ABOVE':
            bx = speaker_center_x - bubble_w // 2
            by = card_top - GAP - bubble_h
            tail_x = speaker_center_x
            tail_y = card_top - GAP // 2
            tail_dir = 'DOWN'
        elif best_dir == 'BELOW':
            bx = speaker_center_x - bubble_w // 2
            by = card_bottom + GAP
            tail_x = speaker_center_x
            tail_y = card_bottom + GAP // 2
            tail_dir = 'UP'
        elif best_dir == 'LEFT':
            bx = card_left - GAP - bubble_w
            by = speaker_top_y + CARD_HEIGHT // 2 - bubble_h // 2
            tail_x = card_left - GAP // 2
            tail_y = speaker_top_y + CARD_HEIGHT // 2
            tail_dir = 'RIGHT'
        elif best_dir == 'RIGHT':
            bx = card_right + GAP
            by = speaker_top_y + CARD_HEIGHT // 2 - bubble_h // 2
            tail_x = card_right + GAP // 2
            tail_y = speaker_top_y + CARD_HEIGHT // 2
            tail_dir = 'LEFT'
        
        # 确保气泡在屏幕内（微调）
        bx = max(SCREEN_MARGIN, min(self.screen_w - bubble_w - SCREEN_MARGIN, bx))
        by = max(SCREEN_MARGIN + TOPBAR_H, min(self.screen_h - bubble_h - SCREEN_MARGIN, by))
        
        # 绘制气泡（带方向尖角）
        self._draw_speech_bubble_smart(screen, bx, by, bubble_w, bubble_h, tail_x, tail_y, tail_dir)
        
        # 绘制头像（在气泡左上角）
        avatar_size = 48
        avatar_x = bx + padding
        avatar_y = by + padding
        
        # 【新布局】第一行：头像 + 名字（水平排列）
        if speaker_avatar:
            # 头像背景框
            avatar_bg_rect = pygame.Rect(avatar_x - 2, avatar_y - 2, avatar_size + 4, avatar_size + 4)
            pygame.draw.rect(screen, (60, 60, 70), avatar_bg_rect, border_radius=4)
            # 绘制头像
            screen.blit(speaker_avatar, (avatar_x, avatar_y))
            # 名字在头像右侧，垂直居中
            name_x = avatar_x + avatar_size + 10
            name_y = avatar_y + (avatar_size - self.font_bubble_name.get_height()) // 2
        else:
            # 无头像时名字在左侧
            name_x = bx + padding
            name_y = avatar_y
        
        # 绘制名字
        if speaker_name and speaker_name != 'NARRATOR':
            name_surf = self.font_bubble_name.render(f"【{speaker_name}】", True, BUBBLE_NAME_COLOR)
            screen.blit(name_surf, (name_x, name_y))
        
        # 【新布局】第二行：文字内容（从第一行下方开始）
        # 计算文字起始Y位置
        if speaker_avatar:
            # 有头像时，文字从头像下方开始
            y_offset = avatar_y + avatar_size + 10
        else:
            # 无头像时，文字从名字下方开始
            y_offset = by + padding + name_height + 5
        
        # 文字X位置统一从左侧padding开始
        text_x = bx + padding
        
        for line in lines:
            line_surf = self.font_bubble.render(line, True, BUBBLE_TEXT_COLOR)
            screen.blit(line_surf, (text_x, y_offset))
            y_offset += line_height
        
        # 绘制继续提示（小巧，不遮挡）
        if int(self.char_index) >= len(txt):
            tip_surf = self.font_hint.render("▼", True, (180, 180, 180))
            tip_x = bx + bubble_w - 20
            tip_y = by + bubble_h - 18
            # 呼吸动画
            breathe = math.sin(self.choice_anim_timer * 0.12) * 2 if hasattr(self, 'choice_anim_timer') else 0
            screen.blit(tip_surf, (tip_x, tip_y + breathe))
    
    def _draw_narrator_dialog(self, screen, display_txt, full_txt):
        """绘制系统旁白/无说话者的对话框 - 屏幕中下部居中，无尖角"""
        # 参数设置
        max_width = 500
        padding = 25
        line_height = 26
        tip_area_h = 30  # 为"点击继续"预留的空间
        
        # 计算文字行
        lines = wrap_text(display_txt, self.font_bubble, max_width - padding * 2)
        if not lines:
            lines = [""]
        
        # 计算气泡尺寸（包含提示区域）
        text_width = max(self.font_bubble.size(line)[0] for line in lines) if lines else 100
        bubble_w = min(max_width, text_width + padding * 2 + 20)
        bubble_h = len(lines) * line_height + padding * 2 + tip_area_h
        
        # 屏幕中下部居中位置（距离底部约1/3屏幕高度）
        bx = (self.screen_w - bubble_w) // 2
        by = self.screen_h * 2 // 3 - bubble_h // 2  # 在屏幕下方2/3处居中
        
        # 绘制无尖角的圆角矩形背景
        bg_color = (30, 30, 40, 230)  # 稍深一点的颜色表示系统消息
        border_color = (150, 150, 180)  # 银灰色边框
        
        bubble_surf = pygame.Surface((bubble_w, bubble_h), pygame.SRCALPHA)
        pygame.draw.rect(bubble_surf, bg_color, (0, 0, bubble_w, bubble_h), border_radius=10)
        pygame.draw.rect(bubble_surf, border_color, (0, 0, bubble_w, bubble_h), 2, border_radius=10)
        screen.blit(bubble_surf, (bx, by))
        
        # 绘制文字
        y_offset = by + padding
        for line in lines:
            line_surf = self.font_bubble.render(line, True, (230, 230, 230))
            screen.blit(line_surf, (bx + padding, y_offset))
            y_offset += line_height
        
        # 绘制继续提示（在气泡框内底部）
        if int(self.char_index) >= len(full_txt):
            tip_surf = self.font_hint.render("▼ 点击继续", True, (150, 150, 150))
            tip_x = bx + bubble_w // 2 - tip_surf.get_width() // 2
            tip_y = by + bubble_h - tip_area_h + 5  # 在预留区域内
            # 呼吸动画
            breathe = math.sin(self.choice_anim_timer * 0.12) * 2 if hasattr(self, 'choice_anim_timer') else 0
            screen.blit(tip_surf, (tip_x, tip_y + breathe))
    
    def _find_speaker_screen_pos(self, speaker_id):
        """查找说话者的屏幕坐标 - 每帧实时计算"""
        if not self._camera_ref or not self._all_cards_ref:
            return None, None
        
        # 如果是玩家 (speaker_id == 9999 或 0)
        if speaker_id in (0, 9999):
            for card in self._all_cards_ref:
                if getattr(card, 'is_player', False):
                    world_x, world_y = card.rect.centerx, card.rect.top
                    screen_x = world_x - self._camera_ref.offset_x
                    screen_y = world_y - self._camera_ref.offset_y
                    return screen_x, screen_y
        
        # 在所有卡牌中查找（支持多种ID存储方式）
        for card in self._all_cards_ref:
            # 检查 card.id（直接创建的 NPC 或从 data['id'] 初始化的）
            card_id = getattr(card, 'id', None)
            if card_id is not None and card_id == speaker_id:
                world_x, world_y = card.rect.centerx, card.rect.top
                screen_x = world_x - self._camera_ref.offset_x
                screen_y = world_y - self._camera_ref.offset_y
                return screen_x, screen_y
            
            # 检查 npc_data.id（从 CSV 加载的 NPC）
            npc_data = getattr(card, 'npc_data', None)
            if npc_data and getattr(npc_data, 'id', None) == speaker_id:
                world_x, world_y = card.rect.centerx, card.rect.top
                screen_x = world_x - self._camera_ref.offset_x
                screen_y = world_y - self._camera_ref.offset_y
                return screen_x, screen_y
        
        # 【备用】根据当前对话的 speaker 名字匹配卡牌 name
        # 用于处理ID映射可能不一致的情况
        if self.current_line:
            speaker_name = self.current_line.speaker
            if speaker_name and speaker_name not in ('NARRATOR', '旁白', '我'):
                # 第一轮：精确匹配名字中包含 speaker_name 的卡牌
                # 同时优先选择标记为 is_main_speaker 的卡牌
                best_match = None
                fallback_match = None
                
                for card in self._all_cards_ref:
                    card_name = getattr(card, 'name', '')
                    if not card_name:
                        continue
                    
                    # 模糊匹配：泼皮 能匹配 泼皮牛二/泼皮狗蛋
                    if speaker_name in card_name or card_name in speaker_name:
                        # 优先选择标记为主说话者的卡牌（如泼皮牛二）
                        if getattr(card, 'is_main_speaker', False):
                            best_match = card
                            break  # 找到主说话者，立即采用
                        elif fallback_match is None:
                            fallback_match = card  # 第一个匹配的备用
                
                matched_card = best_match or fallback_match
                if matched_card:
                    world_x, world_y = matched_card.rect.centerx, matched_card.rect.top
                    screen_x = world_x - self._camera_ref.offset_x
                    screen_y = world_y - self._camera_ref.offset_y
                    return screen_x, screen_y
        
        return None, None
    
    def _get_speaker_avatar(self, speaker_id, size=(48, 48)):
        """获取说话者的头像surface
        
        Args:
            speaker_id: 说话者ID
            size: 头像尺寸元组 (宽, 高)
            
        Returns:
            pygame.Surface 或 None
        """
        if not self._all_cards_ref:
            return None
        
        # 查找说话者卡牌
        speaker_card = None
        
        # 如果是玩家
        if speaker_id in (0, 9999):
            for card in self._all_cards_ref:
                if getattr(card, 'is_player', False):
                    speaker_card = card
                    break
        else:
            # 查找NPC - 先按ID查找
            for card in self._all_cards_ref:
                card_id = getattr(card, 'id', None)
                if card_id is not None and card_id == speaker_id:
                    speaker_card = card
                    break
                # 检查 npc_data.id
                npc_data = getattr(card, 'npc_data', None)
                if npc_data and getattr(npc_data, 'id', None) == speaker_id:
                    speaker_card = card
                    break
            
            # 【修复】如果没找到，尝试按名字匹配（备用方案）
            if speaker_card is None and self.current_line:
                speaker_name = self.current_line.speaker
                if speaker_name and speaker_name not in ('NARRATOR', '旁白', '我'):
                    for card in self._all_cards_ref:
                        card_name = getattr(card, 'name', '')
                        if not card_name:
                            continue
                        # 模糊匹配：名字互相包含
                        if speaker_name in card_name or card_name in speaker_name:
                            speaker_card = card
                            print(f"[StoryUI] 按名字匹配到头像: {speaker_name} -> {card_name}")
                            break
        
        # 获取头像
        if speaker_card and hasattr(speaker_card, 'appearance'):
            return speaker_card.appearance.get_head_surface(size)
        
        # 【调试】如果找不到头像，打印日志
        if speaker_card is None:
            print(f"[StoryUI] 警告: 找不到说话者头像 ID={speaker_id}, name={getattr(self.current_line, 'speaker', '???')}")
        
        return None
    
    def _draw_speech_bubble(self, screen, x, y, w, h, tail_x, tail_y):
        """绘制带尖角的气泡（旧版，保留兼容）"""
        self._draw_speech_bubble_smart(screen, x, y, w, h, tail_x, tail_y, 'DOWN')
    
    def _draw_speech_bubble_smart(self, screen, x, y, w, h, tail_x, tail_y, tail_dir='DOWN'):
        """
        绘制带方向尖角的气泡
        
        Args:
            tail_dir: 尖角朝向 - 'DOWN'(下), 'UP'(上), 'LEFT'(左), 'RIGHT'(右)
        """
        bg_color = BUBBLE_BG_COLOR
        border_color = BUBBLE_BORDER_COLOR
        
        # 根据方向决定surface尺寸的额外空间
        extra_w = 25 if tail_dir in ('LEFT', 'RIGHT') else 20
        extra_h = 25 if tail_dir in ('UP', 'DOWN') else 20
        
        bubble_surf = pygame.Surface((w + extra_w, h + extra_h), pygame.SRCALPHA)
        
        # 气泡主体偏移（为尖角腾出空间）
        body_x = 10 if tail_dir != 'LEFT' else 20
        body_y = 10 if tail_dir != 'UP' else 20
        
        # 绘制主体
        pygame.draw.rect(bubble_surf, bg_color, (body_x, body_y, w, h), border_radius=8)
        pygame.draw.rect(bubble_surf, border_color, (body_x, body_y, w, h), 2, border_radius=8)
        
        # 绘制尖角
        tail_size = 10  # 尖角大小
        
        if tail_dir == 'DOWN':
            # 尖角在底部中央
            tail_local_x = (tail_x - x)
            tail_local_x = max(20, min(w - 20, tail_local_x))
            p1 = (body_x + tail_local_x - 6, body_y + h - 2)
            p2 = (body_x + tail_local_x + 6, body_y + h - 2)
            p3 = (body_x + tail_local_x, body_y + h + tail_size)
            
        elif tail_dir == 'UP':
            # 尖角在顶部
            tail_local_x = (tail_x - x)
            tail_local_x = max(20, min(w - 20, tail_local_x))
            p1 = (body_x + tail_local_x - 6, body_y + 2)
            p2 = (body_x + tail_local_x + 6, body_y + 2)
            p3 = (body_x + tail_local_x, body_y - tail_size)
            
        elif tail_dir == 'LEFT':
            # 尖角在左侧
            tail_local_y = h // 2
            p1 = (body_x + 2, body_y + tail_local_y - 6)
            p2 = (body_x + 2, body_y + tail_local_y + 6)
            p3 = (body_x - tail_size, body_y + tail_local_y)
            
        elif tail_dir == 'RIGHT':
            # 尖角在右侧
            tail_local_y = h // 2
            p1 = (body_x + w - 2, body_y + tail_local_y - 6)
            p2 = (body_x + w - 2, body_y + tail_local_y + 6)
            p3 = (body_x + w + tail_size, body_y + tail_local_y)
        
        # 绘制尖角三角形
        pygame.draw.polygon(bubble_surf, bg_color, [p1, p2, p3])
        pygame.draw.line(bubble_surf, border_color, p1, p3, 2)
        pygame.draw.line(bubble_surf, border_color, p2, p3, 2)
        
        # 计算绘制偏移
        blit_x = x - body_x
        blit_y = y - body_y
        
        screen.blit(bubble_surf, (blit_x, blit_y))

    def _draw_quest_anim(self, screen):
        """绘制任务标题的大动画：淡入 -> 停留 -> 缩小移动到侧边栏"""
        if self.quest_anim_active:
            # 1. 准备文本
            title = self.quest_title
            # 使用大字体
            text_surf = self.font_quest.render(f"任务：{title}", True, (255, 215, 0))
            text_border = self.font_quest.render(f"任务：{title}", True, (0, 0, 0))
            
            # 2. 计算起始点（屏幕中上部，约1/3高度处）
            start_x = self.screen_w // 2 - text_surf.get_width() // 2
            start_y = self.screen_h // 3 - 50
            
            # 3. 计算目标点（侧边栏大概位置）
            # 侧边栏宽度 SIDEBAR_W=280，所以在 screen_w - 280 附近
            # 我们稍微往右一点，让它看起来是飞进列表里
            target_x = self.screen_w - 250 
            target_y = 150 
            
            # 4. 根据当前 Phase 计算位置、透明度、缩放
            cur_x, cur_y = start_x, start_y
            scale = 1.0
            alpha = 255
            
            if self.anim_phase == 0: # Fade In (淡入)
                # 0~30帧
                progress = min(1.0, self.anim_timer / 30)
                alpha = int(255 * progress)
                
            elif self.anim_phase == 1: # Stay (停留)
                alpha = 255
                
            elif self.anim_phase == 2: # Move & Shrink (移动并缩小)
                # 0~60帧
                t = min(1.0, self.anim_timer / 60)
                # 使用 ease out 曲线让移动更顺滑
                ease = t * t * (3 - 2 * t) 
                
                cur_x = start_x + (target_x - start_x) * ease
                cur_y = start_y + (target_y - start_y) * ease
                scale = 1.0 - 0.6 * ease # 缩小到 0.4 倍
                alpha = int(255 * (1.0 - t)) # 逐渐变透明，产生“融入”侧边栏的效果

            # 5. 执行绘制
            if alpha > 5:
                # 缩放处理
                if scale != 1.0:
                    final_surf = pygame.transform.rotozoom(text_surf, 0, scale)
                    final_border = pygame.transform.rotozoom(text_border, 0, scale)
                else:
                    final_surf = text_surf
                    final_border = text_border
                
                # 透明度处理
                final_surf.set_alpha(alpha)
                final_border.set_alpha(alpha)

                # 先画黑边，再画字
                screen.blit(final_border, (cur_x + 2, cur_y + 2))
                screen.blit(final_surf, (cur_x, cur_y))
    

    def get_current_speaker_id(self):
        if self.is_active and self.current_line:
            return self.current_line.speaker_id
        return None
    
    def get_last_dialog_summary(self):
        """
        获取刚结束的对话摘要，用于注入NPC记忆
        
        Returns:
            dict: {
                'quest_id': str,
                'speakers': set of speaker_ids,
                'summary': str  对话摘要文本
            } 或 None
        """
        if not hasattr(self, '_current_dialog_data') or not self._current_dialog_data:
            return None
        
        dialog_data = self._current_dialog_data
        
        # 提取信息
        quest_id = getattr(dialog_data[0], 'quest_id', 'UNKNOWN') if dialog_data else 'UNKNOWN'
        speakers = set()
        lines_by_speaker = {}  # {speaker_name: [lines]}
        
        for d in dialog_data:
            speaker_id = getattr(d, 'speaker_id', None)
            speaker_name = getattr(d, 'speaker', '???')
            text = getattr(d, 'text', '')
            
            if speaker_id is not None:
                speakers.add(speaker_id)
            
            # 收集每个角色说的话
            if speaker_name not in lines_by_speaker:
                lines_by_speaker[speaker_name] = []
            # 只保留前50个字符以节省空间
            short_text = text[:50] + '...' if len(text) > 50 else text
            lines_by_speaker[speaker_name].append(short_text)
        
        # 生成摘要
        summary_parts = []
        for speaker, lines in lines_by_speaker.items():
            if speaker in ['NARRATOR', '旁白']:
                continue  # 跳过旁白
            # 每个角色最多取3句
            sample_lines = lines[:3]
            speaker_summary = f"{speaker}说：「{'」「'.join(sample_lines)}」"
            summary_parts.append(speaker_summary)
        
        summary = '；'.join(summary_parts) if summary_parts else "进行了一段对话"
        
        return {
            'quest_id': quest_id,
            'speakers': speakers,
            'summary': summary
        }
    
    def clear_dialog_data(self):
        """清除已播放的对话数据"""
        if hasattr(self, '_current_dialog_data'):
            self._current_dialog_data = []
    
    # ═══════════════════════════════════════════════════════════════
    # 【新增】选择分支界面
    # ═══════════════════════════════════════════════════════════════
    
    def show_choice(self, options, prompt="做出你的选择"):
        """
        显示选择界面
        
        Args:
            options: 选项列表 [{'key': 'GOOD', 'text': '救人', 'hint': '+10声望'}, ...]
            prompt: 提示文字
        """
        self.choice_mode = True
        self.choice_options = options
        self.choice_prompt = prompt
        self.choice_hover_index = -1
        self.choice_anim_timer = 0
        self.choice_buttons = []
        print(f"[StoryUI] 显示选择界面: {len(options)} 个选项")
    
    def hide_choice(self):
        """隐藏选择界面"""
        self.choice_mode = False
        self.choice_options = []
        self.choice_buttons = []
        self.choice_hover_index = -1
        self.choice_tooltip = None  # 清除tooltip
    
    def handle_choice_input(self, event, ctx):
        """
        处理选择界面的输入
        
        Returns:
            选中的选项 key，或 None（未选择）
        """
        if not self.choice_mode:
            return None
        
        # 鼠标移动 - 更新悬停状态
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            prev_hover = self.choice_hover_index
            self.choice_hover_index = -1
            for i, btn_rect in enumerate(self.choice_buttons):
                if btn_rect.collidepoint(mx, my):
                    self.choice_hover_index = i
                    break
            
            # 如果悬停变化，清除tooltip（让新的悬停重新准备）
            if prev_hover != self.choice_hover_index:
                self.choice_tooltip = None
        
        # 鼠标点击 - 选择
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, btn_rect in enumerate(self.choice_buttons):
                if btn_rect.collidepoint(mx, my):
                    selected_key = self.choice_options[i]['key']
                    print(f"[StoryUI] 玩家选择: {selected_key}")
                    self.hide_choice()
                    return selected_key
        
        # 键盘快捷键 (1, 2, 3...)
        if event.type == pygame.KEYDOWN:
            key_map = {
                pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2,
                pygame.K_4: 3, pygame.K_5: 4,
            }
            if event.key in key_map:
                idx = key_map[event.key]
                if idx < len(self.choice_options):
                    selected_key = self.choice_options[idx]['key']
                    print(f"[StoryUI] 玩家按键选择: {selected_key}")
                    self.hide_choice()
                    return selected_key
        
        return None
    
    def update_choice(self):
        """更新选择界面动画"""
        if self.choice_mode:
            self.choice_anim_timer += 1
    
    def draw_choice(self, screen):
        """绘制选择界面 - 屏幕中间靠右1/3位置"""
        if not self.choice_mode or not self.choice_options:
            return
        
        # 使用缓存的遮罩层，避免每帧创建新 Surface 导致闪烁
        # 轻微的全屏半透明遮罩
        if self._choice_overlay is None or self._choice_overlay.get_size() != (self.screen_w, self.screen_h):
            self._choice_overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            # 均匀的半透明黑色遮罩
            self._choice_overlay.fill((0, 0, 0, 120))
        
        screen.blit(self._choice_overlay, (0, 0))
        
        # 面板参数
        panel_w = 420
        btn_h = 65
        btn_gap = 12
        num_options = len(self.choice_options)
        panel_h = 80 + num_options * (btn_h + btn_gap) + 20
        
        # 放置在屏幕中间靠右1/3位置（水平方向在2/3处）
        panel_x = self.screen_w * 2 // 3 - panel_w // 2
        panel_y = (self.screen_h - panel_h) // 2
        
        # 面板背景 - 右侧半透明深色
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        self._draw_choice_panel_bg(screen, panel_rect)
        
        # 提示文字 - 左对齐风格
        prompt_surf = self.font_name.render(self.choice_prompt, True, (255, 230, 150))
        screen.blit(prompt_surf, (panel_x + 25, panel_y + 22))
        
        # 分隔线
        pygame.draw.line(screen, (100, 90, 70), 
                        (panel_x + 20, panel_y + 55), 
                        (panel_x + panel_w - 20, panel_y + 55), 1)
        
        # 绘制选项按钮
        self.choice_buttons = []
        btn_y = panel_y + 70
        
        # 获取玩家引用（用于tooltip条件检查）
        player = None
        try:
            from src.context import ctx
            player = getattr(ctx, 'player', None)
        except:
            pass
        
        for i, option in enumerate(self.choice_options):
            btn_rect = pygame.Rect(panel_x + 15, btn_y, panel_w - 30, btn_h)
            self.choice_buttons.append(btn_rect)
            
            # 动画：按钮从右侧滑入（仅前几帧有动画）
            anim_offset = max(0, (i + 1) * 4 - self.choice_anim_timer) * 25
            btn_rect_draw = btn_rect.move(anim_offset, 0)
            
            # 判断是否悬停
            is_hover = (i == self.choice_hover_index)
            
            # 绘制按钮
            self._draw_choice_button(screen, btn_rect_draw, option, i + 1, is_hover)
            
            # 悬停时准备tooltip
            if is_hover:
                self._prepare_choice_tooltip(option, btn_rect_draw, player)
            
            btn_y += btn_h + btn_gap
        
        # 绘制tooltip（在所有按钮之后绘制，确保显示在最上层）
        if self.choice_tooltip and self.choice_hover_index >= 0:
            self._draw_choice_tooltip(screen)
    
    def _prepare_choice_tooltip(self, choice: dict, btn_rect: pygame.Rect, player=None):
        """准备选项的tooltip内容"""
        self.choice_tooltip = ChoiceTooltipHelper.create_tooltip_data(choice, btn_rect, player)
    
    def _draw_choice_tooltip(self, screen: pygame.Surface):
        """绘制选项tooltip"""
        if not self.choice_tooltip:
            return
        
        ChoiceTooltipHelper.draw_tooltip(
            surface=screen,
            tooltip_data=self.choice_tooltip,
            font_cache=self._font_cache,
            fixed_width=280,
            line_height=26,
            padding=12,
            panel_h=self.screen_h,  # 使用屏幕高度进行边界检测
            panel_offset=(0, 0)
        )
    
    def _draw_choice_panel_bg(self, screen, rect):
        """绘制选择面板背景 - 直接在screen上绘制，避免创建临时Surface"""
        # 主体背景 - 直接绘制不透明矩形
        pygame.draw.rect(screen, (20, 20, 35), rect, border_radius=5)
        
        # 金色边框
        pygame.draw.rect(screen, (180, 150, 80), rect, 3, border_radius=5)
        
        # 内部装饰线
        inner_rect = rect.inflate(-10, -10)
        pygame.draw.rect(screen, (100, 80, 50), inner_rect, 1, border_radius=3)
        
        # 顶部装饰
        deco_w = 100
        deco_x = rect.centerx - deco_w // 2
        pygame.draw.line(screen, (200, 170, 100), 
                        (deco_x, rect.y), (deco_x + deco_w, rect.y), 3)
    
    def _draw_choice_button(self, screen, rect, option, num, is_hover):
        """绘制单个选择按钮"""
        # 根据选项类型决定颜色风格
        key = option['key']
        if key == 'GOOD':
            base_color = (40, 80, 60)      # 绿色基调
            hover_color = (60, 120, 80)
            border_color = (100, 200, 120)
            icon = "善"
        elif key == 'EVIL':
            base_color = (80, 40, 50)      # 红色基调
            hover_color = (120, 60, 70)
            border_color = (200, 100, 100)
            icon = "恶"
        else:
            base_color = (50, 50, 70)      # 中性蓝色
            hover_color = (70, 70, 100)
            border_color = (150, 150, 200)
            icon = "中"
        
        # 按钮背景
        color = hover_color if is_hover else base_color
        pygame.draw.rect(screen, color, rect, border_radius=8)
        
        # 边框 (悬停时更亮)
        border_w = 3 if is_hover else 2
        pygame.draw.rect(screen, border_color, rect, border_w, border_radius=8)
        
        # 悬停时的发光效果
        if is_hover:
            glow_rect = rect.inflate(4, 4)
            glow_color = (*border_color, 100)
            glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, glow_color, glow_surf.get_rect(), border_radius=10)
            screen.blit(glow_surf, glow_rect.topleft)
        
        # 序号和图标
        num_text = f"{num}. {icon}"
        num_surf = self.font_choice.render(num_text, True, border_color)
        screen.blit(num_surf, (rect.x + 15, rect.y + 12))
        
        # 选项文本
        text = option.get('text', key)
        text_color = (255, 255, 255) if is_hover else (220, 220, 220)
        text_surf = self.font_choice.render(text, True, text_color)
        screen.blit(text_surf, (rect.x + 70, rect.y + 14))
        
        # 提示文本（效果预览）
        hint = option.get('hint', '')
        if hint:
            # 根据提示内容决定颜色
            if '+' in hint and '声望' in hint:
                hint_color = (150, 220, 150)  # 绿色（正面）
            elif '悬赏' in hint or '-' in hint:
                hint_color = (220, 150, 150)  # 红色（负面）
            else:
                hint_color = (180, 180, 180)  # 灰色（中性）
            
            hint_surf = self.font_hint.render(hint, True, hint_color)
            screen.blit(hint_surf, (rect.x + 70, rect.y + 42))
        
        # 悬停时的箭头指示
        if is_hover:
            arrow = ">"
            arrow_surf = self.font_choice.render(arrow, True, (255, 255, 255))
            # 箭头呼吸动画
            breathe = math.sin(self.choice_anim_timer * 0.15) * 3
            screen.blit(arrow_surf, (rect.right - 30 + breathe, rect.centery - 10))
