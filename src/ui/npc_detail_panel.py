# --- src/ui/npc_detail_panel.py ---
import pygame
from src.definitions import *
from src.utils import log_game_event, wrap_text
from src.entities import Resource 
from src.data.character_seeds import ORGANIZATIONS
from src.item_system import ItemManager
from src.aistory.story_director import StoryDirector
from src.ui.live_news_panel import toggle_live_news_panel
import asyncio

class UIDialogsMixin:
    """
    提供NPC详情、事件对话框的绘制
    包含：NPC面板、事件弹窗、以及事件选项按钮的逻辑处理
    """

    def draw_npc_detail(self, screen, npc, player, mx, my, click_event, ft_manager, event=None):
        """绘制NPC详细信息面板（重构版 v3 - 带 Tab 分页）
        布局采用四栏式：
          A. 顶部：头像 + 名字 + 基础状态 (固定高度 70px)
          B. Tab栏：属性 | 背包 | 记忆 | 关系 (固定高度 30px)
          C. 中部：根据Tab显示不同内容 (可滚动区域)
          D. 底部：操作按钮栏 (固定高度 80px)
        """
        is_self = (npc == player)
        panel_w, panel_h = 340, 600  # 稍微加宽加高
        panel_rect = pygame.Rect(self.screen_w - panel_w - 280, 60, panel_w, panel_h)

        pygame.draw.rect(screen, COLOR_UI_PANEL, panel_rect, border_radius=8)
        pygame.draw.rect(screen, (200, 200, 200), panel_rect, 2, border_radius=8)

        # ══════════════════════════════════════════════════════════════
        # A. 头像 + 名字 + 基础状态
        # ══════════════════════════════════════════════════════════════
        # 绘制头像 (64x64)
        avatar_size = 64
        avatar_x = panel_rect.x + 12
        avatar_y = panel_rect.y + 10
        
        # 头像背景框
        avatar_bg_rect = pygame.Rect(avatar_x - 2, avatar_y - 2, avatar_size + 4, avatar_size + 4)
        pygame.draw.rect(screen, (80, 80, 80), avatar_bg_rect, border_radius=4)
        
        # 绘制头像（使用平滑缩放）
        if hasattr(npc, 'appearance') and npc.appearance:
            head_surf = npc.appearance.get_head_surface((avatar_size, avatar_size))
            if head_surf:
                screen.blit(head_surf, (avatar_x, avatar_y))
            else:
                # 头像加载失败，显示占位图
                self._draw_avatar_placeholder(screen, avatar_x, avatar_y, avatar_size)
        else:
            # 默认占位图
            self._draw_avatar_placeholder(screen, avatar_x, avatar_y, avatar_size)

        # 文字起始X坐标（头像右侧）
        text_start_x = avatar_x + avatar_size + 12
        
        name_color = (255, 215, 0) if getattr(npc, 'is_follower', False) else COLOR_HIGHLIGHT
        if npc.safety in [SAFETY_DEAD, SAFETY_EXILED]:
            name_color = (150, 150, 150)
        status_suffix = " (已故)" if npc.safety in [SAFETY_DEAD, SAFETY_EXILED] else ""
        name_txt = self.font_big.render(npc.name + status_suffix, True, name_color)
        screen.blit(name_txt, (text_start_x, panel_rect.y + 5))
        
        # NPC描述 - 自动换行显示
        if hasattr(npc, 'desc') and npc.desc:
            # 计算描述文本可用宽度（考虑头像位置和边距）
            desc_available_width = panel_rect.right - text_start_x - 20
            desc_lines = wrap_text(npc.desc, self.font_small, desc_available_width)
            desc_y = panel_rect.y  + name_txt.get_height() 
            for i, line in enumerate(desc_lines):
                desc_surf = self.font_small.render(line, True, (180, 180, 180))
                screen.blit(desc_surf, (text_start_x, desc_y + i * (desc_surf.get_height() + 2)))



        #职业-组织，以及状态，可以放在名字右侧的一列
        col3_x = text_start_x + name_txt.get_width() + 15
        # 【修复】身份行（第二行）- 职业和组织放在同一行
        job_label = JOB_LABELS.get(getattr(npc, 'job', 'NONE'), '平民')
        power_type = getattr(npc, 'power_type', None)
        org_name = ""
        if hasattr(npc, 'org_id') and npc.org_id and npc.org_id != 'NONE':            
            org_data = ORGANIZATIONS.get(npc.org_id, {})
            org_name = org_data.get('name', npc.org_id)
        identity_info = f"[{power_type}]{job_label}" + (f"·{org_name}" if org_name else "")
        identity_surf = self.font_small.render(identity_info, True, (180, 180, 180))
        screen.blit(identity_surf, (col3_x, panel_rect.y + 0))
        
        # 【修复】AI状态行（第三行）- 与身份行保持合理间距
        ai_reason = getattr(npc, 'ai_reason', '')
        if ai_reason:
            # 截断过长的状态文本，避免超框
            display_reason = ai_reason[:14] if len(ai_reason) > 14 else ai_reason
            ai_txt = f"状态: {display_reason}"
            ai_surf = self.font_small.render(ai_txt, True, (150, 200, 150))
            screen.blit(ai_surf, (col3_x, panel_rect.y + 20))

        # ══════════════════════════════════════════════════════════════
        # B. Tab 栏
        # ══════════════════════════════════════════════════════════════
        TAB_LABELS = ['属性', '背包', '记忆', '关系', '内心']
        tab_y = panel_rect.y + 85  # 调整Tab栏位置以适应更大的头像区域
        tab_h = 26
        tab_w = (panel_w - 20) // len(TAB_LABELS)
        
        # 初始化当前选中的Tab（存储在UI管理器中）
        if not hasattr(self, '_npc_detail_tab'):
            self._npc_detail_tab = 0
        
        # 确保 Tab 索引有效
        current_tab = self._npc_detail_tab
        
        for i, label in enumerate(TAB_LABELS):
            tab_rect = pygame.Rect(panel_rect.x + 10 + i * tab_w, tab_y, tab_w - 2, tab_h)
            is_selected = (i == current_tab)
            is_hover = tab_rect.collidepoint(mx, my)
            
            # Tab 背景色
            if is_selected:
                bg_color = (80, 100, 140)
                border_color = (150, 180, 220)
            elif is_hover:
                bg_color = (60, 70, 90)
                border_color = (100, 110, 130)
            else:
                bg_color = (45, 50, 60)
                border_color = (70, 75, 85)
            
            pygame.draw.rect(screen, bg_color, tab_rect, border_radius=4)
            pygame.draw.rect(screen, border_color, tab_rect, 1, border_radius=4)
            
            # Tab 文字
            text_color = (255, 255, 255) if is_selected else (180, 180, 180)
            tab_txt = self.font_small.render(label, True, text_color)
            screen.blit(tab_txt, (tab_rect.centerx - tab_txt.get_width() // 2, 
                                  tab_rect.centery - tab_txt.get_height() // 2))
            
            # 点击切换 Tab
            if click_event and is_hover:
                self._npc_detail_tab = i
                return False  # 消费点击事件，但不关闭面板

        # ══════════════════════════════════════════════════════════════
        # C. 内容区域（根据 Tab 显示不同内容）
        # ══════════════════════════════════════════════════════════════
        content_y = tab_y + tab_h + 8
        # 预留底部操作栏高度，内容区域可滚动显示，比如招募、闲聊、关闭按钮
        ACTION_BAR_H = 95
        content_bottom = panel_rect.bottom - ACTION_BAR_H
        content_rect = pygame.Rect(panel_rect.x + 8, content_y, panel_w - 16, content_bottom - content_y)
        
        pending_action = None
        
        if current_tab == 0:
            # ─────────────────────────────────────────────────────────────
            # Tab 0: 属性
            # ─────────────────────────────────────────────────────────────
            pending_action = self._draw_npc_tab_attributes(screen, npc, player, is_self, content_rect, mx, my, click_event)
        
        elif current_tab == 1:
            # ─────────────────────────────────────────────────────────────
            # Tab 1: 背包
            # ─────────────────────────────────────────────────────────────
            pending_action = self._draw_npc_tab_inventory(screen, npc, player, is_self, content_rect, mx, my, click_event)
        
        elif current_tab == 2:
            # ─────────────────────────────────────────────────────────────
            # Tab 2: 记忆
            # ─────────────────────────────────────────────────────────────
            self._draw_npc_tab_memory(screen, npc, content_rect)
        
        elif current_tab == 3:
            # ─────────────────────────────────────────────────────────────
            # Tab 3: 人际关系
            # ─────────────────────────────────────────────────────────────
            self._draw_npc_tab_relations(screen, npc, player, content_rect)
        
        elif current_tab == 4:
            # ─────────────────────────────────────────────────────────────
            # Tab 4: 内心 (性格特质 + 人生困境)
            # ─────────────────────────────────────────────────────────────
            # 处理滚轮事件（翻转方向：y>0向上滚动，y<0向下滚动）
            if event and event.type == pygame.MOUSEWHEEL:
                if hasattr(self, '_inner_heart_scroll'):
                    self._inner_heart_scroll -= event.y * 20  # 翻转方向：y>0时向上（减小scroll值）
                    self._inner_heart_scroll = max(0, self._inner_heart_scroll)
            
            self._draw_npc_tab_inner_heart(screen, npc, content_rect, mx, my, click_event)

        # ══════════════════════════════════════════════════════════════
        # D. 底部操作栏
        # ══════════════════════════════════════════════════════════════
        action_bar_y = panel_rect.bottom - ACTION_BAR_H + 6
        pygame.draw.line(screen, (100, 100, 100),
                         (panel_rect.x + 8, action_bar_y - 3),
                         (panel_rect.right - 8, action_bar_y - 3))

        if npc.safety in [SAFETY_DEAD, SAFETY_EXILED]:
            btn_close_rect = pygame.Rect(panel_rect.centerx - 40, action_bar_y + 8, 80, 30)
            if self.draw_button(screen, btn_close_rect, "关闭", self.font_ui, mx, my, (150, 50, 50)):
                if click_event: return True
            return pending_action or False

        btn_h_main = 28

        if not is_self:
            btn_row1_y = action_bar_y + 6

            is_follower = getattr(npc, 'is_follower', False)
            can_recruit = (not is_follower
                           and player.fame  >= npc.recruit_fame_req
                           and player.money >= npc.recruit_cost
                           and not (player.fame < -500 and 'THUG' not in getattr(npc, 'tags', [])))
            recruit_label = "已招募" if is_follower else "招募"
            btn_recruit_rect = pygame.Rect(panel_rect.x + 10, btn_row1_y, 70, btn_h_main)
            recruit_btn_hover = self.draw_button(screen, btn_recruit_rect, recruit_label, self.font_ui, mx, my,
                                (200, 150, 50), disabled=is_follower or not can_recruit)
            if recruit_btn_hover and click_event and can_recruit:
                player.money -= npc.recruit_cost
                npc.is_follower = True
                npc.ai_mode = "FOLLOW"  # 设置AI模式为跟随
                player.followers_count += 1
                if ft_manager:
                    ft_manager.add_text("招募成功!", npc.rect.x, npc.rect.y - 60, (255, 215, 0))
                log_game_event(f"玩家招募了 {npc.name}，花费 {npc.recruit_cost}")

            # 【修复】招募条件只在鼠标悬停在招募按钮上时才显示
            if not is_follower and not can_recruit and recruit_btn_hover:
                tips = []
                if player.fame < -500 and 'THUG' not in getattr(npc, 'tags', []):
                    tips.append("名声太臭")
                else:
                    if player.fame < npc.recruit_fame_req:
                        tips.append(f"望{player.fame}/{npc.recruit_fame_req}")
                    if player.money < npc.recruit_cost:
                        tips.append(f"钱{player.money}/{npc.recruit_cost}")
                # 在按钮下方显示提示
                tip_y = btn_row1_y + btn_h_main + 2
                for tip in tips:
                    warn_surf = self.font_small.render(tip, True, (255, 130, 80))
                    screen.blit(warn_surf, (panel_rect.x + 10, tip_y))
                    tip_y += 14

            is_event_state = (npc.state == STATE_EVENT) if hasattr(npc, 'state') else False
            if is_event_state and npc.active_event_data:
                btn_ev_rect = pygame.Rect(panel_rect.x + 86, btn_row1_y, 96, btn_h_main)
                if self.draw_button(screen, btn_ev_rect, "查看事件", self.font_small, mx, my, (200, 50, 50)):
                    if click_event: return "GOTO_EVENT"

            # 【合并】闲聊按钮 - 直接进入AI聊天界面
            btn_chat_rect = pygame.Rect(panel_rect.right - 88, btn_row1_y, 78, btn_h_main)
            chat_hover = self.draw_button(screen, btn_chat_rect, "闲聊", self.font_ui, mx, my, (60, 100, 60))
            if chat_hover and click_event:
                if ft_manager:
                    ft_manager.add_text("开始聊天...", npc.rect.x, npc.rect.y - 40, (255, 255, 0))
                log_game_event(f"玩家开始与 {npc.name} 闲聊")
                return "AI_CHAT"  # 改为触发AI聊天
            
            # 【暂时隐藏】交涉按钮 (说服/威胁/贿赂)
            # 设计说明：交涉应该是情境驱动的功能，只在特定场景下启用：
            #   - 被守卫拦截时（需要说服/贿赂通行）
            #   - 被强盗打劫时（需要威胁/谈判脱身）
            #   - 招募NPC时（已有 RecruitmentSystem 处理）
            #   - 任务对话中需要检定时（可由事件系统触发）
            # 目前常驻显示没有意义，等后续有明确的交涉情景再启用
            # ----------------------------------------------------------------
            # btn_negotiate_rect = pygame.Rect(panel_rect.x + 10, btn_row1_y + btn_h_main + 6, 78, btn_h_main)
            # if self.draw_button(screen, btn_negotiate_rect, "交涉", self.font_ui, mx, my, (150, 100, 50)):
            #     if click_event:
            #         log_game_event(f"玩家准备与 {npc.name} 交涉")
            #         return "NEGOTIATE"
            
            # 【新增】组织任务按钮 - 当NPC是玩家所属组织的长老时显示
            npc_org_id = getattr(npc, 'org_id', None)
            npc_org_role = getattr(npc, 'org_role', None)
            player_org_ids = player.organizations if hasattr(player, 'organizations') else []
            
            # 判断: NPC是长老 且 玩家属于同一组织
            if npc_org_id and npc_org_role == 'LEADER' and npc_org_id in player_org_ids:
                btn_org_task_rect = pygame.Rect(panel_rect.x + 94, btn_row1_y + btn_h_main + 6, 78, btn_h_main)
                if self.draw_button(screen, btn_org_task_rect, "门派任务", self.font_small, mx, my, (80, 130, 180)):
                    if click_event:
                        log_game_event(f"玩家向 {npc.name} 询问组织任务")
                        return ("ORG_TASK_DIALOG", npc_org_id, npc)

        btn_row2_y = action_bar_y + btn_h_main + 12
        btn_close_rect = pygame.Rect(panel_rect.right - 88, btn_row2_y, 78, 28)
        if self.draw_button(screen, btn_close_rect, "关闭", self.font_ui, mx, my, (150, 50, 50)):
            if click_event: return True

        if pending_action:
            return pending_action
        return False

    def _draw_avatar_placeholder(self, screen, x, y, size):
        """绘制头像占位图"""
        placeholder = pygame.Surface((size, size))
        placeholder.fill((150, 150, 150))
        pygame.draw.rect(screen, (100, 100, 100), (x, y, size, size), 2)
        # 绘制问号
        q_font = pygame.font.Font(None, 36)
        q_surf = q_font.render("?", True, (80, 80, 80))
        screen.blit(q_surf, (x + size//2 - q_surf.get_width()//2, 
                            y + size//2 - q_surf.get_height()//2))

    def draw_resource_detail(self, screen, res_card, mx, my, click_event, ft_manager):
  
           w, h = 300, 250
           cx, cy = self.screen_w // 2, self.screen_h // 2
           rect = pygame.Rect(cx - w//2, cy - h//2, w, h)
           
           # 遮罩
           s = pygame.Surface((self.screen_w, self.screen_h))
           s.set_alpha(150)
           s.fill((0,0,0))
           screen.blit(s, (0,0))
           
           # 背景
           pygame.draw.rect(screen, COLOR_UI_PANEL, rect, border_radius=10)
           pygame.draw.rect(screen, (200, 200, 200), rect, 2, border_radius=10)
           
           # 标题
           title = self.font_big.render(f"资源: {res_card.name}", True, res_card.color)
           screen.blit(title, (rect.x + 20, rect.y + 20))
           
           info = self.font_ui.render(f"当前堆叠数量: {res_card.count}", True, (255, 255, 255))
           screen.blit(info, (rect.x + 20, rect.y + 60))
           
           # 拆分逻辑 (如果数量 > 1)
           action = None
           split_val = getattr(self, '_temp_split_val', 1) # 临时存在 UI 管理器里
           
           if res_card.count > 1:
               # 拆分控制区
               y_ctrl = rect.y + 100
               
               # 减号
               btn_minus = pygame.Rect(rect.x + 50, y_ctrl, 30, 30)
               if self.draw_button(screen, btn_minus, "-", self.font_big, mx, my):
                   if click_event: self._temp_split_val = max(1, split_val - 1)
               
               # 数字
               num_surf = self.font_big.render(str(split_val), True, (255, 255, 255))
               screen.blit(num_surf, (rect.x + 100, y_ctrl + 5))
               
               # 加号
               btn_plus = pygame.Rect(rect.x + 160, y_ctrl, 30, 30)
               if self.draw_button(screen, btn_plus, "+", self.font_big, mx, my):
                   if click_event: self._temp_split_val = min(res_card.count - 1, split_val + 1)
               
               # 拆分按钮
               btn_split = pygame.Rect(rect.x + 60, y_ctrl + 50, 120, 35)
               if self.draw_button(screen, btn_split, "拆分", self.font_ui, mx, my, (50, 150, 50)):
                   if click_event:
                       action = ("SPLIT", split_val)
                       self._temp_split_val = 1 # 重置
           
           else:
               t = self.font_small.render("数量为 1，无法拆分", True, (150, 150, 150))
               screen.blit(t, (rect.x + 20, rect.y + 120))
       
           # 关闭按钮
           btn_close = pygame.Rect(rect.right - 80, rect.bottom - 45, 70, 30)
           if self.draw_button(screen, btn_close, "关闭", self.font_ui, mx, my, (150, 50, 50)):
               if click_event: action = "CLOSE"
               
           return action
    def draw_event_dialog(self, screen, npc, player, mx, my, click_event, all_npcs=[]):
        """
        绘制事件对话框（完整版本，带交互逻辑）
        """
        if not npc or not npc.active_event_data: return "CLOSE", None, None
        data = npc.active_event_data
        npc_name = npc.name
        partner_name = data.get('partner').name if data.get('partner') else "神秘人"

        dialog_rect = pygame.Rect(100, 80, self.screen_w - 200, 500)
        
        # 1. 绘制半透明遮罩和弹窗背景
        overlay = pygame.Surface((self.screen_w, self.screen_h))
        overlay.set_alpha(180)
        overlay.fill((10,10,20)) 
        screen.blit(overlay, (0,0))
        pygame.draw.rect(screen, COLOR_UI_PANEL, dialog_rect, border_radius=10)
        pygame.draw.rect(screen, (200, 200, 200), dialog_rect, 2, border_radius=10)
        
        # 2. 标题
        title_txt = self.font_big.render(f"【{data.get('title')}】", True, (255, 200, 50))
        screen.blit(title_txt, (dialog_rect.centerx - title_txt.get_width()//2, dialog_rect.y + 25))
        
        # 3. 描述文本 (支持换行)
        desc = data.get('description', '')
        lines = wrap_text(desc, self.font_ui, dialog_rect.width - 60)
        y_off = dialog_rect.y + 70
        for line in lines:
            t = self.font_ui.render(line, True, COLOR_TEXT)
            screen.blit(t, (dialog_rect.x + 30, y_off))
            y_off += 25

        # 4. 选项按钮
        btn_w = 200
        btn_gap = 15
        start_x = dialog_rect.centerx - (btn_w * 3 + btn_gap * 2) // 2
        btn_y = dialog_rect.bottom - 150

        btn_a_rect = pygame.Rect(start_x, btn_y, btn_w, 110)
        btn_b_rect = pygame.Rect(start_x + btn_w + btn_gap, btn_y, btn_w, 110)
        btn_c_rect = pygame.Rect(start_x + (btn_w + btn_gap) * 2, btn_y, btn_w, 110)

        # 调用 draw_option_button 绘制三个选项（传入chain_str用于显示连锁事件提示）
        hover_a, possible_a = self.draw_option_button(
            screen, btn_a_rect, data.get('btn_a'), data.get('eff_a'), data.get('req_a'), 
            player, mx, my, npc_name, partner_name, all_npcs, data.get('chain_a', '')
        )
        hover_b, possible_b = self.draw_option_button(
            screen, btn_b_rect, data.get('btn_b'), data.get('eff_b'), data.get('req_b'), 
            player, mx, my, npc_name, partner_name, all_npcs, data.get('chain_b', '')
        )
        hover_c, possible_c = self.draw_option_button(
            screen, btn_c_rect, data.get('btn_c'), data.get('eff_c'), data.get('req_c'), 
            player, mx, my, npc_name, partner_name, all_npcs, data.get('chain_c', '')
        )
        
        # 找到 "处理点击逻辑" 部分
        if click_event:
            if hover_a and possible_a: 
                # [修改] 返回按钮文本 (去掉括号里的备注，让新闻更自然)
                txt = data.get('btn_a').split('(')[0]
                return "RESOLVE", data.get('eff_a'), data.get('chain_a'), txt
            elif hover_b and possible_b: 
                txt = data.get('btn_b').split('(')[0]
                return "RESOLVE", data.get('eff_b'), data.get('chain_b'), txt
            elif hover_c and possible_c: 
                txt = data.get('btn_c').split('(')[0]
                return "RESOLVE", data.get('eff_c'), data.get('chain_c'), txt
                
        # 5. 关闭按钮
        btn_close = pygame.Rect(dialog_rect.right - 80, dialog_rect.top + 10, 70, 30)
        if self.draw_button(screen, btn_close, "X", self.font_ui, mx, my, (150, 50, 50)):
            if click_event: return "CLOSE", None, None, None # 补齐返回值数量

        return "WAIT", None, None, None # 补齐返回值数量


    def draw_option_button(self, screen, rect, text, effect, req_str, player, mx, my, npc_name, partner_name, all_npcs, chain_str=""):
        """
        绘制事件选项按钮，并检测需求是否满足
        【增强版】在悬停时显示效果预览，让玩家清楚每个选择的后果
        
        返回: (is_hover, is_possible)
        """
        if not text: return False, False # 选项不存在
        
        # 导入效果预览解析器
        from src.event_effect_preview import get_preview_parser
        preview_parser = get_preview_parser()
        
        # --- 解析需求 ---
        possible = True
        fail_reason = ""
        
        if req_str and req_str != "NONE":
            reqs = req_str.split(';')
            for r in reqs:
                if not r: continue
                parts = r.split(':')
                r_type = parts[0]
                r_val = parts[1] if len(parts) > 1 else ''
                
                # 检查金钱
                if r_type == 'MONEY':
                    val = int(r_val)
                    if player.money < val:
                        possible = False
                        fail_reason = f"需 {val} 钱"
                # 检查声望
                elif r_type == 'FAME':
                    val = int(r_val)
                    if r_val.startswith('-'):
                        if player.fame > val:
                            possible = False
                            fail_reason = f"需恶名 {abs(val)}+"
                    else:
                        if player.fame < val:
                            possible = False
                            fail_reason = f"需声望 {val}+"
                # 检查道具 (ITEM:GRAIN)
                elif r_type == 'ITEM':
                    item_name = r_val
                    has_item = False
                    if item_name == 'GRAIN' and player.food > 0: has_item = True
                    if not has_item:
                        possible = False
                        fail_reason = f"需物品: {item_name}"
                # 检查标签
                elif r_type == 'TAG':
                    if r_val not in getattr(player, 'tags', []):
                        possible = False
                        tag_names = {'JUSTICE': '侠义', 'THUG': '恶名'}
                        fail_reason = f"需称号「{tag_names.get(r_val, r_val)}」"
                # 检查门客
                elif r_type == 'FOLLOWER':
                    # 简化检查：有对应职业的门客
                    follower_names = {'THUG': '打手', 'SCHOLAR': '文人', 'DOCTOR': '医生'}
                    fail_reason = f"需门客: {follower_names.get(r_val, r_val)}"
                    # 这里可以添加实际检查逻辑
        
        # --- 绘制按钮 ---
        is_hover = rect.collidepoint(mx, my)
        
        # 颜色逻辑：不可用=灰色，可用+悬停=高亮，可用=普通
        if not possible:
            bg_color = (70, 70, 70)
            border_color = (50, 50, 50)
        elif is_hover:
            bg_color = (80, 90, 140)
            border_color = (150, 180, 255)
        else:
            bg_color = (50, 55, 70)
            border_color = (90, 100, 120)
            
        pygame.draw.rect(screen, bg_color, rect, border_radius=8)
        pygame.draw.rect(screen, border_color, rect, 2, border_radius=8)
        
        # 替换文本中的占位符
        display_text = text.replace('{npc}', npc_name).replace('{partner}', partner_name)
        
        # 绘制选项文本（在按钮上半部分）
        text_surf = self.font_ui.render(display_text, True, (255, 255, 255) if possible else (140, 140, 140))
        text_rect = text_surf.get_rect(center=(rect.centerx, rect.y + 22))
        screen.blit(text_surf, text_rect)
        
        # 分隔线
        pygame.draw.line(screen, (80, 80, 100) if possible else (50, 50, 50),
                        (rect.x + 10, rect.y + 40), (rect.right - 10, rect.y + 40))
        
        # --- 【核心功能】绘制效果预览 ---
        if possible and effect:
            # 解析效果
            preview = preview_parser.parse_choice(
                btn_text=text,
                effect_str=effect,
                req_str=req_str or "",
                chain_str=chain_str or "",
                npc_a_name=npc_name,
                npc_b_name=partner_name,
                player=player
            )
            
            # 绘制效果列表
            effect_y = rect.y + 46
            max_effects = 4  # 最多显示4条效果
            
            for i, eff in enumerate(preview.effects[:max_effects]):
                # 颜色：正面绿色，负面红色
                if eff.is_positive:
                    eff_color = (120, 220, 120)
                    prefix = "+"
                else:
                    eff_color = (255, 130, 130)
                    prefix = "-"
                
                # 目标标识
                if eff.target == 'PLAYER':
                    target_str = "[你]"
                elif eff.target == 'SELF':
                    target_str = f"[{npc_name[:2]}]"
                elif eff.target == 'OTHER':
                    target_str = f"[{partner_name[:2]}]"
                else:
                    target_str = ""
                
                # 组合显示文本
                eff_text = f"{target_str} {eff.description}"
                if len(eff_text) > 18:
                    eff_text = eff_text[:17] + ".."
                
                eff_surf = self.font_small.render(eff_text, True, eff_color)
                screen.blit(eff_surf, (rect.x + 8, effect_y))
                effect_y += 14
            
            # 如果有更多效果，显示省略号
            if len(preview.effects) > max_effects:
                more_surf = self.font_small.render(f"...还有{len(preview.effects) - max_effects}项", True, (150, 150, 150))
                screen.blit(more_surf, (rect.x + 8, effect_y))
            
            # 连锁事件提示
            if preview.chain_hint:
                chain_surf = self.font_small.render(preview.chain_hint, True, (255, 200, 100))
                screen.blit(chain_surf, (rect.x + 8, rect.bottom - 16))
        
        # 绘制需求/警告文本
        elif not possible:
            warn_surf = self.font_small.render(fail_reason, True, (255, 100, 100))
            warn_rect = warn_surf.get_rect(center=(rect.centerx, rect.centery + 15))
            screen.blit(warn_surf, warn_rect)

        return is_hover, possible

    # ═══════════════════════════════════════════════════════════════
    # 语言检定对话框 (Persuasion Check Dialog)
    # ═══════════════════════════════════════════════════════════════
    
    def draw_persuasion_dialog(self, screen, player, target_npc, persuasion_system, mx, my, click_event, ft_manager=None):
        """
        绘制语言检定对话框
        
        Args:
            screen: pygame屏幕
            player: 玩家对象
            target_npc: 目标NPC
            persuasion_system: PersuasionSystem实例
            mx, my: 鼠标坐标
            click_event: 是否有点击
            ft_manager: 浮动文字管理器
        
        Returns:
            action: None | ('PERSUADE', method) | 'CANCEL'
        """
        # 对话框尺寸
        dialog_w, dialog_h = 500, 400
        dialog_rect = pygame.Rect(
            (self.screen_w - dialog_w) // 2,
            (self.screen_h - dialog_h) // 2,
            dialog_w, dialog_h
        )
        
        # 半透明遮罩
        overlay = pygame.Surface((self.screen_w, self.screen_h))
        overlay.set_alpha(180)
        overlay.fill((10, 10, 20))
        screen.blit(overlay, (0, 0))
        
        # 对话框背景
        pygame.draw.rect(screen, COLOR_UI_PANEL, dialog_rect, border_radius=10)
        pygame.draw.rect(screen, (200, 180, 100), dialog_rect, 3, border_radius=10)
        
        # 标题
        title_txt = self.font_big.render(f"与 {target_npc.name} 交涉", True, (255, 215, 0))
        screen.blit(title_txt, (dialog_rect.centerx - title_txt.get_width() // 2, dialog_rect.y + 20))
        
        # 目标信息
        info_y = dialog_rect.y + 60
        info_lines = [
            f"对方职业: {getattr(target_npc, 'job', '平民')}",
            f"对方态度: {self._get_attitude_text(target_npc, player)}",
        ]
        for line in info_lines:
            t = self.font_ui.render(line, True, COLOR_TEXT)
            screen.blit(t, (dialog_rect.x + 30, info_y))
            info_y += 25
        
        # 分隔线
        pygame.draw.line(screen, (100, 100, 100),
                        (dialog_rect.x + 20, info_y + 10),
                        (dialog_rect.right - 20, info_y + 10))
        
        # 三个选项按钮
        btn_w, btn_h = 140, 100
        btn_gap = 20
        btn_start_x = dialog_rect.centerx - (btn_w * 3 + btn_gap * 2) // 2
        btn_y = info_y + 30
        
        action = None
        
        # === 说服按钮 ===
        persuade_rate, persuade_details = persuasion_system.get_preview_rate(player, target_npc, 'persuade')
        btn_persuade = pygame.Rect(btn_start_x, btn_y, btn_w, btn_h)
        if self._draw_persuasion_option(screen, btn_persuade, "说服", persuade_rate, 
                                        f"魅力 vs 意志", mx, my, (100, 180, 100)):
            if click_event:
                action = ('PERSUADE', 'persuade')
        
        # === 威胁按钮 ===
        threaten_rate, threaten_details = persuasion_system.get_preview_rate(player, target_npc, 'threaten')
        btn_threaten = pygame.Rect(btn_start_x + btn_w + btn_gap, btn_y, btn_w, btn_h)
        if self._draw_persuasion_option(screen, btn_threaten, "威胁", threaten_rate,
                                        f"武力 vs 勇气", mx, my, (200, 100, 100)):
            if click_event:
                action = ('PERSUADE', 'threaten')
        
        # === 贿赂按钮 ===
        bribe_amount = getattr(self, '_bribe_amount', 50)
        bribe_rate, bribe_details = persuasion_system.get_preview_rate(player, target_npc, 'bribe', bribe_amount)
        btn_bribe = pygame.Rect(btn_start_x + (btn_w + btn_gap) * 2, btn_y, btn_w, btn_h)
        
        # 检查玩家是否有足够的钱
        can_bribe = player.money >= bribe_amount
        if self._draw_persuasion_option(screen, btn_bribe, "贿赂", bribe_rate,
                                        f"出价: {bribe_amount}铜", mx, my, (200, 180, 50),
                                        disabled=not can_bribe):
            if click_event and can_bribe:
                action = ('PERSUADE', 'bribe', bribe_amount)
        
        # 贿赂金额调节
        bribe_ctrl_y = btn_y + btn_h + 15
        bribe_minus = pygame.Rect(btn_start_x + (btn_w + btn_gap) * 2, bribe_ctrl_y, 40, 25)
        bribe_plus = pygame.Rect(btn_start_x + (btn_w + btn_gap) * 2 + 100, bribe_ctrl_y, 40, 25)
        
        if self.draw_button(screen, bribe_minus, "-10", self.font_small, mx, my, (80, 80, 80)):
            if click_event:
                self._bribe_amount = max(10, bribe_amount - 10)
        
        # 显示当前金额
        amount_txt = self.font_ui.render(f"{bribe_amount}", True, (255, 255, 255))
        screen.blit(amount_txt, (bribe_minus.right + 15, bribe_ctrl_y + 3))
        
        if self.draw_button(screen, bribe_plus, "+10", self.font_small, mx, my, (80, 80, 80)):
            if click_event:
                self._bribe_amount = min(player.money, bribe_amount + 10)
        
        # 玩家金钱提示
        money_txt = self.font_small.render(f"你的铜钱: {player.money}", True, (200, 200, 200))
        screen.blit(money_txt, (dialog_rect.x + 30, bribe_ctrl_y + 5))
        
        # 关闭/取消按钮
        btn_cancel = pygame.Rect(dialog_rect.centerx - 50, dialog_rect.bottom - 50, 100, 35)
        if self.draw_button(screen, btn_cancel, "离开", self.font_ui, mx, my, (150, 50, 50)):
            if click_event:
                action = 'CANCEL'
        
        return action
    
    def _draw_persuasion_option(self, screen, rect, label, success_rate, hint, mx, my, color, disabled=False):
        """
        绘制单个检定选项按钮
        
        Returns:
            is_hover: bool
        """
        is_hover = rect.collidepoint(mx, my) and not disabled
        
        # 颜色
        if disabled:
            bg_color = (60, 60, 60)
            border_color = (40, 40, 40)
            text_color = (100, 100, 100)
        elif is_hover:
            bg_color = tuple(min(255, c + 40) for c in color)
            border_color = (255, 255, 255)
            text_color = (255, 255, 255)
        else:
            bg_color = color
            border_color = tuple(min(255, c + 60) for c in color)
            text_color = (255, 255, 255)
        
        pygame.draw.rect(screen, bg_color, rect, border_radius=8)
        pygame.draw.rect(screen, border_color, rect, 2, border_radius=8)
        
        # 标签
        label_surf = self.font_ui.render(label, True, text_color)
        screen.blit(label_surf, (rect.centerx - label_surf.get_width() // 2, rect.y + 10))
        
        # 成功率
        rate_text = f"{success_rate:.0%}"
        rate_color = (100, 255, 100) if success_rate >= 0.5 else (255, 200, 100) if success_rate >= 0.3 else (255, 100, 100)
        if disabled:
            rate_color = (100, 100, 100)
        rate_surf = self.font_big.render(rate_text, True, rate_color)
        screen.blit(rate_surf, (rect.centerx - rate_surf.get_width() // 2, rect.y + 35))
        
        # 提示
        hint_surf = self.font_small.render(hint, True, (180, 180, 180) if not disabled else (80, 80, 80))
        screen.blit(hint_surf, (rect.centerx - hint_surf.get_width() // 2, rect.y + 70))
        
        return is_hover
    
    def _get_attitude_text(self, npc, player):
        """获取NPC对玩家的态度文本"""
        # 兼容两种存储方式
        if hasattr(npc, 'affinity') and isinstance(getattr(npc, 'affinity', None), dict):
            affinity = npc.affinity.get(getattr(player, 'id', 9999), 0)
        else:
            affinity = getattr(npc, 'affinity_to_player', 0)
        
        if affinity >= 80:
            return "亲密 [爱]"
        elif affinity >= 50:
            return "友好"
        elif affinity >= 20:
            return "好感"
        elif affinity >= -20:
            return "中立"
        elif affinity >= -50:
            return "冷淡"
        else:
            return "敌视"
    
    def draw_persuasion_result(self, screen, result_type, message, mx, my, click_event):
        """
        绘制检定结果弹窗
        
        Returns:
            'CLOSE' | None
        """
        # 对话框尺寸
        dialog_w, dialog_h = 400, 200
        dialog_rect = pygame.Rect(
            (self.screen_w - dialog_w) // 2,
            (self.screen_h - dialog_h) // 2,
            dialog_w, dialog_h
        )
        
        # 半透明遮罩
        overlay = pygame.Surface((self.screen_w, self.screen_h))
        overlay.set_alpha(180)
        overlay.fill((10, 10, 20))
        screen.blit(overlay, (0, 0))
        
        # 根据结果类型选择颜色
        if result_type == 'CRIT_SUCCESS':
            border_color = (255, 215, 0)  # 金色
            title = "【大成功】"
            title_color = (255, 215, 0)
        elif result_type == 'SUCCESS':
            border_color = (100, 255, 100)  # 绿色
            title = "【成功】"
            title_color = (100, 255, 100)
        elif result_type == 'FAILURE':
            border_color = (200, 200, 200)  # 灰色
            title = "【失败】"
            title_color = (200, 200, 200)
        else:  # CRIT_FAILURE
            border_color = (255, 50, 50)  # 红色
            title = "【大失败】"
            title_color = (255, 50, 50)
        
        # 对话框背景
        pygame.draw.rect(screen, COLOR_UI_PANEL, dialog_rect, border_radius=10)
        pygame.draw.rect(screen, border_color, dialog_rect, 3, border_radius=10)
        
        # 标题
        title_surf = self.font_big.render(title, True, title_color)
        screen.blit(title_surf, (dialog_rect.centerx - title_surf.get_width() // 2, dialog_rect.y + 30))
        
        # 消息
        msg_lines = wrap_text(message, self.font_ui, dialog_w - 40)
        msg_y = dialog_rect.y + 80
        for line in msg_lines:
            t = self.font_ui.render(line, True, COLOR_TEXT)
            screen.blit(t, (dialog_rect.centerx - t.get_width() // 2, msg_y))
            msg_y += 25
        
        # 确认按钮
        btn_ok = pygame.Rect(dialog_rect.centerx - 50, dialog_rect.bottom - 50, 100, 35)
        if self.draw_button(screen, btn_ok, "确定", self.font_ui, mx, my, (100, 100, 150)):
            if click_event:
                return 'CLOSE'
        
        return None

    # ═══════════════════════════════════════════════════════════════
    # 组织任务对话框 (NPC交互方式)
    # ═══════════════════════════════════════════════════════════════
    
    def draw_org_task_dialog(self, screen, org_id, elder_npc, player, org_task_system, mx, my, click_event):
        """
        绘制组织任务对话框 - 向长老领取/交付任务
        
        Args:
            screen: pygame屏幕
            org_id: 组织ID
            elder_npc: 长老NPC对象
            player: 玩家对象
            org_task_system: OrgTaskSystem实例
            mx, my: 鼠标坐标
            click_event: 是否有点击
        
        Returns:
            action: None | ('ACCEPT', task_id) | ('TURNIN', task_id) | 'CLOSE'
        """
        from src.org_task_system import OrgTaskState
        
        # 对话框尺寸
        dialog_w, dialog_h = 600, 500
        dialog_rect = pygame.Rect(
            (self.screen_w - dialog_w) // 2,
            (self.screen_h - dialog_h) // 2,
            dialog_w, dialog_h
        )
        
        # 半透明遮罩
        overlay = pygame.Surface((self.screen_w, self.screen_h))
        overlay.set_alpha(180)
        overlay.fill((10, 10, 20))
        screen.blit(overlay, (0, 0))
        
        # 对话框背景
        pygame.draw.rect(screen, COLOR_UI_PANEL, dialog_rect, border_radius=10)
        pygame.draw.rect(screen, (100, 150, 200), dialog_rect, 3, border_radius=10)
        
        # 标题 - 显示长老名字
        org_name = org_task_system.get_org_display_name(org_id)
        title_txt = self.font_big.render(f"{elder_npc.name} - {org_name}任务", True, (255, 215, 0))
        screen.blit(title_txt, (dialog_rect.centerx - title_txt.get_width() // 2, dialog_rect.y + 15))
        
        # 长老对话语
        greeting = self._get_elder_greeting(elder_npc, player, org_task_system, org_id)
        greeting_surf = self.font_ui.render(greeting, True, (200, 200, 200))
        screen.blit(greeting_surf, (dialog_rect.x + 30, dialog_rect.y + 55))
        
        # 玩家信息栏 (功勋/职位)
        player_merit = org_task_system.get_player_merit(org_id)
        player_rank = org_task_system.get_player_rank_name(org_id)
        info_txt = f"你的职位: {player_rank}  |  功勋: {player_merit}"
        info_surf = self.font_small.render(info_txt, True, (150, 200, 255))
        screen.blit(info_surf, (dialog_rect.x + 30, dialog_rect.y + 80))
        
        # 分隔线
        pygame.draw.line(screen, (100, 100, 100),
                        (dialog_rect.x + 20, dialog_rect.y + 105),
                        (dialog_rect.right - 20, dialog_rect.y + 105))
        
        action = None
        content_y = dialog_rect.y + 115
        
        # === 获取任务列表 ===
        available_tasks = org_task_system.get_available_tasks(org_id, player)
        active_tasks = org_task_system.get_active_tasks(org_id)
        completed_tasks = [t for t in active_tasks if t.state == OrgTaskState.COMPLETED]
        in_progress_tasks = [t for t in active_tasks if t.state == OrgTaskState.ACTIVE]
        
        # === 可交付的任务 (优先显示) ===
        if completed_tasks:
            section_surf = self.font_ui.render("【可交付的任务】", True, (100, 255, 100))
            screen.blit(section_surf, (dialog_rect.x + 30, content_y))
            content_y += 28
            
            for task in completed_tasks[:2]:  # 最多显示2个
                btn_rect = pygame.Rect(dialog_rect.x + 30, content_y, dialog_w - 60, 50)
                is_hover = btn_rect.collidepoint(mx, my)
                
                bg_color = (60, 100, 60) if is_hover else (40, 70, 40)
                pygame.draw.rect(screen, bg_color, btn_rect, border_radius=5)
                pygame.draw.rect(screen, (100, 200, 100), btn_rect, 2, border_radius=5)
                
                # 任务名称
                task_name = self.font_ui.render(f"[ok] {task.name}", True, (255, 255, 255))
                screen.blit(task_name, (btn_rect.x + 10, btn_rect.y + 5))
                
                # 奖励
                reward_txt = f"奖励: {task.reward_money}铜 | +{task.reward_merit}功勋"
                reward_surf = self.font_small.render(reward_txt, True, (255, 215, 0))
                screen.blit(reward_surf, (btn_rect.x + 10, btn_rect.y + 28))
                
                # 交付按钮
                turnin_btn = pygame.Rect(btn_rect.right - 70, btn_rect.y + 10, 60, 30)
                if self.draw_button(screen, turnin_btn, "交付", self.font_small, mx, my, (100, 180, 100)):
                    if click_event:
                        action = ('TURNIN', task.task_id)
                
                content_y += 55
        
        # === 进行中的任务 ===
        if in_progress_tasks:
            section_surf = self.font_ui.render("【进行中的任务】", True, (255, 200, 100))
            screen.blit(section_surf, (dialog_rect.x + 30, content_y))
            content_y += 28
            
            for task in in_progress_tasks[:2]:
                btn_rect = pygame.Rect(dialog_rect.x + 30, content_y, dialog_w - 60, 50)
                
                pygame.draw.rect(screen, (50, 50, 60), btn_rect, border_radius=5)
                pygame.draw.rect(screen, (150, 150, 100), btn_rect, 1, border_radius=5)
                
                # 任务名称
                task_name = self.font_ui.render(f"◐ {task.name}", True, (255, 255, 200))
                screen.blit(task_name, (btn_rect.x + 10, btn_rect.y + 5))
                
                # 进度提示
                progress_txt = org_task_system.get_task_progress_text(task)
                progress_surf = self.font_small.render(progress_txt, True, (180, 180, 180))
                screen.blit(progress_surf, (btn_rect.x + 10, btn_rect.y + 28))
                
                content_y += 55
        
        # === 可接取的任务 ===
        section_surf = self.font_ui.render("【可领取的任务】", True, (100, 200, 255))
        screen.blit(section_surf, (dialog_rect.x + 30, content_y))
        content_y += 28
        
        if not available_tasks:
            empty_surf = self.font_small.render("暂无可领取的任务", True, (120, 120, 120))
            screen.blit(empty_surf, (dialog_rect.x + 50, content_y))
            content_y += 25
        else:
            for task in available_tasks[:3]:  # 最多显示3个
                if content_y + 55 > dialog_rect.bottom - 60:
                    break
                    
                btn_rect = pygame.Rect(dialog_rect.x + 30, content_y, dialog_w - 60, 50)
                is_hover = btn_rect.collidepoint(mx, my)
                
                bg_color = (50, 60, 80) if is_hover else (40, 45, 60)
                pygame.draw.rect(screen, bg_color, btn_rect, border_radius=5)
                pygame.draw.rect(screen, (100, 150, 200), btn_rect, 1, border_radius=5)
                
                # 任务名称
                task_name = self.font_ui.render(f"○ {task.name}", True, (255, 255, 255))
                screen.blit(task_name, (btn_rect.x + 10, btn_rect.y + 5))
                
                # 描述和奖励
                desc_txt = f"{task.description[:20]}... | +{task.reward_merit}功勋"
                desc_surf = self.font_small.render(desc_txt, True, (180, 180, 180))
                screen.blit(desc_surf, (btn_rect.x + 10, btn_rect.y + 28))
                
                # 接取按钮
                accept_btn = pygame.Rect(btn_rect.right - 70, btn_rect.y + 10, 60, 30)
                if self.draw_button(screen, accept_btn, "领取", self.font_small, mx, my, (80, 130, 180)):
                    if click_event:
                        action = ('ACCEPT', task.task_id)
                
                content_y += 55
        
        # === 关闭按钮 ===
        btn_close = pygame.Rect(dialog_rect.centerx - 50, dialog_rect.bottom - 45, 100, 35)
        if self.draw_button(screen, btn_close, "告辞", self.font_ui, mx, my, (150, 100, 100)):
            if click_event:
                action = 'CLOSE'
        
        return action
    
    def _get_elder_greeting(self, elder_npc, player, org_task_system, org_id):
        """获取长老问候语"""
        player_rank = org_task_system.get_player_rank_name(org_id)
        
        # 根据组织风格生成问候语
        org_style = org_task_system._get_org_style(org_id)
        
        if org_style == 'gang':
            greetings = [
                f"「{player_rank}，又来讨活儿干了？」",
                f"「好，看看今天有什么差事给你。」",
                f"「来得正好，正愁没人跑腿呢。」"
            ]
        elif org_style == 'official':
            greetings = [
                f"「{player_rank}到了，公务繁忙，有何要事？」",
                f"「嗯，看看衙门里有什么差事。」",
                f"「正好，有几件案子需要人手。」"
            ]
        elif org_style == 'temple':
            greetings = [
                f"「阿弥陀佛，{player_rank}有何指教？」",
                f"「施主来得正好，有几件善事需人去办。」",
                f"「善哉，看看有何修行之事。」"
            ]
        else:
            greetings = [
                f"「{player_rank}，来领任务吗？」",
                f"「看看有什么事情可以交给你。」",
                f"「正好有几件事需要办。」"
            ]
        
        import random
        return random.choice(greetings)

    # ═══════════════════════════════════════════════════════════════
    # NPC详情面板 - Tab 内容绘制方法
    # ═══════════════════════════════════════════════════════════════
    
    def _draw_npc_tab_attributes(self, screen, npc, player, is_self, content_rect, mx, my, click_event):
        """
        绘制 Tab 0: 属性页
        显示NPC的基础属性、装备、六维属性等
        """
        pygame.draw.rect(screen, (30, 35, 45), content_rect, border_radius=5)
        pygame.draw.rect(screen, (80, 80, 100), content_rect, 1, border_radius=5)
        
        y = content_rect.y + 8
        #左右两半区域
        x_left = content_rect.x + 10
        x_right = content_rect.centerx + 10
        line_h = 22
        
        # === 基础信息 ===
        title = self.font_small.render("【状态属性】", True, (150, 200, 250))
        screen.blit(title, (x_left, y))
        y += line_h
        
        # 生命/饱食度
        hp_text = f"生命: {npc.hp}/{npc.max_hp}"
        hp_color = (100, 255, 100) if npc.hp > npc.max_hp * 0.5 else (255, 200, 100) if npc.hp > npc.max_hp * 0.2 else (255, 100, 100)
        screen.blit(self.font_small.render(hp_text, True, hp_color), (x_left, y))
        
        food_text = f"饱食: {getattr(npc, 'food', 0)}"
        screen.blit(self.font_small.render(food_text, True, (200, 200, 200)), (x_right, y))
        y += line_h
        
        # 金钱/声望
        money_text = f"铜钱: {getattr(npc, 'money', 0)}"
        screen.blit(self.font_small.render(money_text, True, (255, 215, 0)), (x_left, y))
        
        fame_text = f"声望: {getattr(npc, 'fame', 0)}"
        fame_color = (100, 200, 255) if getattr(npc, 'fame', 0) >= 0 else (255, 100, 100)
        screen.blit(self.font_small.render(fame_text, True, fame_color), (x_right, y))
        y += line_h

        #补充寒冷、不满值
        cold_text = f"寒冷: {getattr(npc, 'cold', 0)}"
        cold_color = (100, 220, 220) if getattr(npc, 'cold', 0) < 50 else (255, 150, 150)
        screen.blit(self.font_small.render(cold_text, True, cold_color), (x_left, y))
        discontent_text = f"不满: {getattr(npc, 'discontent', 0)}"
        discontent_color = (100, 220, 100) if getattr(npc, 'discontent', 0) < 50 else (255, 150, 150)
        screen.blit(self.font_small.render(discontent_text, True, discontent_color), (x_right, y))
        y += line_h
        
        # 分隔线
        y += 5
        pygame.draw.line(screen, (80, 80, 100), (x_left, y), (content_rect.right - 10, y))
        y += 10
        
        # === 六维属性 ===
        title2 = self.font_small.render("【能力属性】", True, (150, 200, 250))
        screen.blit(title2, (x_left, y))
        y += line_h
        
        attrs = [
            ('力量', getattr(npc, 'strength', 0)),
            ('敏捷', getattr(npc, 'agility', 0)),
            ('智力', getattr(npc, 'wit', 0)),
            ('魅力', getattr(npc, 'charm', 0)),
        ]
        
        for i, (name, val) in enumerate(attrs):
            col = x_left if i % 2 == 0 else x_right
            if i % 2 == 0 and i > 0:
                y += line_h
            
            # 根据数值选择颜色
            val_color = (100, 220, 100) if val >= 70 else (220, 200, 100) if val >= 40 else (220, 100, 100)
            attr_txt = f"{name}: {val}"
            screen.blit(self.font_small.render(attr_txt, True, val_color), (col, y))
        
        y += line_h + 10
        
        # === 战斗属性 ===
        pygame.draw.line(screen, (80, 80, 100), (x_left, y), (content_rect.right - 10, y))
        y += 10
        
        title3 = self.font_small.render("【战斗属性】", True, (150, 200, 250))
        screen.blit(title3, (x_left, y))
        y += line_h
        
        # 导入物品系统计算装备加成
        item_sys = ItemManager.get_instance()
        
        # 获取装备
        equip_weapon = getattr(npc, 'equip_weapon', None)
        equip_armor = getattr(npc, 'equip_armor', None)
        equip_clothing = getattr(npc, 'equip_clothing', None)
        
        # 计算加成（防御力 = 护甲加成 + 衣物加成）
        atk_bonus = item_sys.get_atk_bonus(equip_weapon) if equip_weapon else 0
        armor_def_bonus = item_sys.get_def_bonus(equip_armor) if equip_armor else 0
        clothing_def_bonus = item_sys.get_def_bonus(equip_clothing) if equip_clothing else 0
        total_def_bonus = armor_def_bonus + clothing_def_bonus
        warm_bonus = item_sys.get_warm_val(equip_clothing) if equip_clothing else 0
        
        # 基础属性
        base_atk = getattr(npc, 'atk', 0)
        base_def = getattr(npc, 'def_', 0)
        
        # 显示攻击力（格式：总值 (+加成)）
        total_atk = base_atk + atk_bonus
        if atk_bonus > 0:
            atk_text = f"攻击力: {total_atk} (+{atk_bonus})"
        else:
            atk_text = f"攻击力: {total_atk}"
        screen.blit(self.font_small.render(atk_text, True, (220, 100, 100)), (x_left, y))
        y += line_h
        
        # 显示防御力（护甲+衣物）
        total_def = base_def + total_def_bonus
        if total_def_bonus > 0:
            def_text = f"防御力: {total_def} (+{total_def_bonus})"
        else:
            def_text = f"防御力: {total_def}"
        screen.blit(self.font_small.render(def_text, True, (100, 150, 220)), (x_left, y))
        y += line_h
        
        # 显示保暖值
        if warm_bonus > 0:
            warm_text = f"保暖值: +{warm_bonus}"
            screen.blit(self.font_small.render(warm_text, True, (180, 220, 180)), (x_left, y))
            y += line_h
        
        # === 装备信息（紧凑显示） ===
        y += 5
        equip_info = []
        if equip_weapon:
            equip_info.append(f"武:{equip_weapon}")
        if equip_armor:
            equip_info.append(f"甲:{equip_armor}")
        if equip_clothing:
            equip_info.append(f"衣:{equip_clothing}")
        
        if equip_info:
            equip_str = "  ".join(equip_info)
            screen.blit(self.font_small.render(equip_str, True, (150, 150, 150)), (x_left, y))
        else:
            screen.blit(self.font_small.render("(无装备)", True, (100, 100, 100)), (x_left, y))
        
        y += line_h + 5

        # === 战斗仇恨 ===
        # 检查是否有仇恨数据且空间足够
        if hasattr(npc, 'hatred') and npc.hatred and y + line_h * 2 < content_rect.bottom - 10:
            # 导入通用的获取NPC名字函数
            from src.data_loader import get_npc_name_by_id_global
            
            pygame.draw.line(screen, (80, 80, 100), (x_left, y), (content_rect.right - 10, y))
            y += 10
            
            title4 = self.font_small.render("【战斗仇恨】", True, (150, 200, 250))
            screen.blit(title4, (x_left, y))
            y += line_h
            
            # 按仇恨值排序，显示前3个
            sorted_hatred = sorted(npc.hatred.items(), key=lambda x: x[1], reverse=True)
            hatred_entries = []
            for target_id, hate_val in sorted_hatred[:3]:
                # 使用通用函数获取名字（支持CSV加载的NPC、种子NPC、动态NPC）
                target_name = get_npc_name_by_id_global(target_id)
                hatred_entries.append(f"{target_name}:{hate_val}")
            
            hatred_info = "  ".join(hatred_entries)
            screen.blit(self.font_small.render(hatred_info, True, (200, 100, 100)), (x_left, y))
            y += line_h
        
        return None  # 属性页没有操作按钮
    
    def _draw_npc_tab_inventory(self, screen, npc, player, is_self, content_rect, mx, my, click_event):
        """
        绘制 Tab 1: 背包页
        显示NPC的物品列表，支持使用/装备/丢弃等操作
        鼠标悬停在物品上时显示详情气泡
        """
        from src.definitions import DEBUG_CONTROLNPC
        from src.item_system import ItemManager
        item_sys = ItemManager.get_instance()
        
        # === 检查是否有待确认的丢弃操作 ===
        if hasattr(self, '_drop_confirm_item') and self._drop_confirm_item:
            return self._draw_drop_confirm_dialog(screen, npc, mx, my, click_event)
        
        pygame.draw.rect(screen, (30, 35, 45), content_rect, border_radius=5)
        pygame.draw.rect(screen, (80, 80, 100), content_rect, 1, border_radius=5)
        
        # 标题栏 + 物品总数统计
        inv_count = sum(npc.inventory.values()) if npc.inventory else 0
        inv_title_text = f"【行囊物品】({inv_count}件)"
        inv_title = self.font_small.render(inv_title_text, True, (150, 200, 250))
        screen.blit(inv_title, (content_rect.x + 8, content_rect.y + 5))
        
        can_control = getattr(npc, 'is_follower', False) or DEBUG_CONTROLNPC or is_self
        can_interact = not is_self
        
        pending_action = None
        inv_y = content_rect.y + 28
        item_row_h = 24
        max_visible_items = (content_rect.height - 35) // item_row_h
        
        # 用于记录悬停的物品（最后绘制详情气泡）
        hovered_item = None
        hovered_item_rect = None
        
        if not npc.inventory:
            empty_t = self.font_small.render("（空）", True, (100, 100, 100))
            screen.blit(empty_t, (content_rect.x + 12, inv_y))
        else:
            items_list = list(npc.inventory.items())
            items_shown = 0
            overflow_count = max(0, len(items_list) - max_visible_items)
            
            for item, count in items_list:
                if inv_y + item_row_h > content_rect.bottom - 8:
                    # 显示溢出提示
                    more_txt = f"…还有{overflow_count}种物品"
                    more = self.font_small.render(more_txt, True, (120, 150, 180))
                    screen.blit(more, (content_rect.x + 12, inv_y))
                    break
                
                # 检测物品行是否被悬停
                item_row_rect = pygame.Rect(content_rect.x + 5, inv_y, content_rect.width - 10, item_row_h)
                if item_row_rect.collidepoint(mx, my):
                    hovered_item = item
                    hovered_item_rect = item_row_rect
                    # 高亮背景
                    pygame.draw.rect(screen, (50, 60, 80), item_row_rect, border_radius=3)
                
                # 物品名称（限制长度）
                item_display = item[:8] if len(item) > 8 else item
                item_str = f"{item_display} x{count}"
                t_item = self.font_small.render(item_str, True, (220, 220, 220))
                screen.blit(t_item, (content_rect.x + 10, inv_y + 2))
                
                btn_right = content_rect.right - 8
                btn_h_s, btn_w_s = 20, 32
                
                if can_control:
                    from src.item_system import ItemManager
                    item_sys = ItemManager.get_instance()
                    
                    btn_x = btn_right - btn_w_s
                    
                    # 【丢】按钮 - 点击打开数量确认弹窗
                    btn_drop = pygame.Rect(btn_x, inv_y, btn_w_s, btn_h_s)
                    if self.draw_button(screen, btn_drop, "丢", self.font_small, mx, my, (100, 55, 55)):
                        if click_event:
                            # 打开丢弃确认弹窗
                            self._drop_confirm_item = item
                            self._drop_confirm_count = 1
                    btn_x -= btn_w_s + 3
                    
                    # 根据物品类型显示不同的使用按钮（仅玩家自己可用）
                    if is_self:
                        if item_sys.is_food(item):
                            btn_use = pygame.Rect(btn_x, inv_y, btn_w_s, btn_h_s)
                            if self.draw_button(screen, btn_use, "吃", self.font_small, mx, my, (50, 120, 50)):
                                if click_event:
                                    pending_action = ("USE_FOOD", item)
                        elif item_sys.is_weapon(item) or item_sys.is_armor(item) or item_sys.is_clothing(item):
                            is_equipped = False
                            if item_sys.is_weapon(item) and getattr(npc, 'equip_weapon', None) == item:
                                is_equipped = True
                            elif item_sys.is_armor(item) and getattr(npc, 'equip_armor', None) == item:
                                is_equipped = True
                            elif item_sys.is_clothing(item) and getattr(npc, 'equip_clothing', None) == item:
                                is_equipped = True
                            
                            btn_label = "卸" if is_equipped else "装"
                            btn_color = (120, 80, 50) if is_equipped else (50, 80, 120)
                            btn_equip = pygame.Rect(btn_x, inv_y, btn_w_s, btn_h_s)
                            if self.draw_button(screen, btn_equip, btn_label, self.font_small, mx, my, btn_color):
                                if click_event:
                                    if is_equipped:
                                        pending_action = ("UNEQUIP_ITEM", item)
                                    else:
                                        pending_action = ("EQUIP_ITEM", item)
                elif can_interact:
                    btn_steal = pygame.Rect(btn_right - btn_w_s, inv_y, btn_w_s, btn_h_s)
                    btn_req = pygame.Rect(btn_right - btn_w_s * 2 - 4, inv_y, btn_w_s + 8, btn_h_s)
                    if self.draw_button(screen, btn_steal, "偷", self.font_small, mx, my, (120, 50, 120)):
                        if click_event:
                            pending_action = ("STEAL_ITEM", item)
                    if self.draw_button(screen, btn_req, "索", self.font_small, mx, my, (50, 90, 130)):
                        if click_event:
                            pending_action = ("REQUEST_ITEM", item)
                
                inv_y += item_row_h
                items_shown += 1
        
        # === 绘制物品详情气泡（最后绘制，确保在最上层） ===
        if hovered_item:
            self._draw_item_tooltip(screen, hovered_item, hovered_item_rect, item_sys)
        
        return pending_action
    
    def _draw_item_tooltip(self, screen, item_id, anchor_rect, item_sys):
        """
        绘制物品详情气泡
        
        Args:
            screen: pygame屏幕
            item_id: 物品ID
            anchor_rect: 锚定矩形（物品行的位置）
            item_sys: ItemManager实例
        """
        item_data = item_sys.get_data(item_id)
        
        # 准备显示内容
        lines = []
        lines.append(("name", item_id, (255, 255, 255)))  # 物品名称
        
        if item_data:
            # 物品类型
            type_names = {
                'WEAPON': '[兵] 武器',
                'ARMOR': '[甲] 护甲',
                'CLOTHING': '[衣] 衣物',
                'FOOD': '[食] 食物',
                'MATERIAL': '[料] 材料',
                'FUEL': '[燃] 燃料',
            }
            type_name = type_names.get(item_data.type, '其他')
            lines.append(("type", type_name, (180, 180, 180)))
            
            # 属性效果
            if item_data.atk_bonus > 0:
                lines.append(("effect", f"攻击力 +{item_data.atk_bonus}", (220, 100, 100)))
            if item_data.def_bonus > 0:
                lines.append(("effect", f"防御力 +{item_data.def_bonus}", (100, 150, 220)))
            if item_data.warm_val > 0:
                lines.append(("effect", f"保暖值 +{item_data.warm_val}", (180, 220, 180)))
            if item_data.hunger_rec > 0:
                lines.append(("effect", f"饱食恢复 +{item_data.hunger_rec}", (200, 180, 100)))
            if item_data.burn_time > 0:
                lines.append(("effect", f"燃烧时间 {item_data.burn_time}秒", (255, 150, 50)))
            
            # 价值
            if item_data.price > 0:
                lines.append(("price", f"市价: {item_data.price}铜", (255, 215, 0)))
            
            # 描述
            if item_data.desc:
                desc = item_data.desc if len(item_data.desc) <= 20 else item_data.desc[:19] + '...'
                lines.append(("desc", desc, (150, 150, 150)))
        else:
            lines.append(("desc", "(无详细信息)", (100, 100, 100)))
        
        # 计算气泡大小
        line_h = 18
        padding = 8
        tooltip_h = len(lines) * line_h + padding * 2
        tooltip_w = 160
        
        # 计算气泡位置（在物品行左侧显示）
        tooltip_x = anchor_rect.x - tooltip_w - 10
        tooltip_y = anchor_rect.y
        
        # 如果超出左边界，改为显示在右侧
        if tooltip_x < 10:
            tooltip_x = anchor_rect.right + 10
        
        # 如果超出底部，向上调整
        if tooltip_y + tooltip_h > self.screen_h - 10:
            tooltip_y = self.screen_h - tooltip_h - 10
        
        tooltip_rect = pygame.Rect(tooltip_x, tooltip_y, tooltip_w, tooltip_h)
        
        # 绘制气泡背景
        pygame.draw.rect(screen, (25, 30, 40), tooltip_rect, border_radius=6)
        pygame.draw.rect(screen, (100, 120, 150), tooltip_rect, 2, border_radius=6)
        
        # 绘制内容
        y = tooltip_rect.y + padding
        for line_type, text, color in lines:
            if line_type == "name":
                # 名称用稍大的字体
                surf = self.font_ui.render(text, True, color)
            else:
                surf = self.font_small.render(text, True, color)
            screen.blit(surf, (tooltip_rect.x + padding, y))
            y += line_h
    
    def _draw_npc_tab_memory(self, screen, npc, content_rect):
        """
        绘制 Tab 2: 记忆页
        显示NPC的记忆列表
        """
        pygame.draw.rect(screen, (30, 35, 45), content_rect, border_radius=5)
        pygame.draw.rect(screen, (80, 80, 100), content_rect, 1, border_radius=5)
        
        # 标题
        memory_list = getattr(npc, 'memory', [])
        title_text = f"【记忆】(共{len(memory_list)}条)"
        title = self.font_small.render(title_text, True, (150, 200, 250))
        screen.blit(title, (content_rect.x + 8, content_rect.y + 5))
        
        y = content_rect.y + 28
        line_h = 42  # 每条记忆的高度（含描述）
        max_visible = (content_rect.height - 35) // line_h
        
        if not memory_list:
            empty_t = self.font_small.render("（暂无记忆）", True, (100, 100, 100))
            screen.blit(empty_t, (content_rect.x + 12, y))
            return
        
        # 按时间倒序显示（最新的在上面）- 兼容 'time' 和 'timestamp' 两种字段名
        sorted_memories = sorted(memory_list, key=lambda m: m.get('time', m.get('timestamp', 0)), reverse=True)
        
        # 记忆类型对应的颜色、图标和中文名称
        type_info = {
            # 帮助/被帮助
            'HELPED_BY': ((100, 200, 100), '[助]', '受助'),
            'HELPED': ((80, 180, 80), '[助]', '助人'),
            
            # 冲突/战斗
            'BULLIED_BY': ((255, 100, 100), '[欺]', '被欺'),
            'FOUGHT_WITH': ((255, 150, 50), '[战]', '交战'),
            'DEFEATED_BY': ((200, 100, 100), '[败]', '战败'),
            'DEFEATED': ((200, 200, 100), '[胜]', '胜利'),
            'COMBAT_WIN': ((255, 215, 0), '[胜]', '战胜'),
            'COMBAT_LOSS': ((180, 80, 80), '[败]', '战败'),
            'WITNESSED_COMBAT': ((150, 150, 200), '○', '目击'),
            'ATTACK': ((255, 100, 100), '[战]', '攻击'),
            'ATTACKED_BY': ((255, 80, 80), '[攻]', '被攻击'),
            
            # 交易
            'TRADE': ((100, 200, 200), '◇', '交易'),
            'TRADE_BUY': ((100, 180, 180), '◇', '购买'),
            'TRADE_SELL': ((180, 200, 100), '◇', '出售'),
            
            # 社交
            'CHAT': ((180, 180, 180), '[话]', '交谈'),
            'FIRST_MEET': ((200, 180, 255), '[遇]', '初遇'),
            'GREET': ((150, 200, 150), '[候]', '问候'),
            
            # 世界事件
            'WORLD_EVENT': ((255, 200, 100), '[事]', '事件'),
            'WITNESSED_EVENT': ((200, 200, 150), '○', '目睹'),
            'HEARD_EVENT': ((150, 150, 150), '○', '听闻'),
            
            # 任务
            'QUEST_COMPLETE': ((100, 255, 100), '[完]', '任务完成'),
            'QUEST_FAILED': ((255, 100, 100), '[败]', '任务失败'),
            'QUEST': ((200, 200, 100), '[任]', '任务'),
            
            # 其他
            'GIFT': ((255, 200, 150), '[礼]', '赠礼'),
            'THEFT': ((255, 100, 100), '[盗]', '盗窃'),
            'INSULT': ((200, 100, 100), '[辱]', '侮辱'),
            'PRAISE': ((100, 200, 100), '[赞]', '赞美'),
            'UNKNOWN': ((150, 150, 150), '?', '未知'),
        }
        
        for i, mem in enumerate(sorted_memories):
            if y + line_h > content_rect.bottom - 8:
                remaining = len(sorted_memories) - i
                more_txt = f"…还有{remaining}条记忆"
                more = self.font_small.render(more_txt, True, (120, 150, 180))
                screen.blit(more, (content_rect.x + 12, y))
                break
            
            # 记忆类型和时间
            mem_type = mem.get('type', 'UNKNOWN')
            mem_time = mem.get('time', 0)
            
            # 获取类型信息（颜色、图标、中文名）
            color, icon, type_name = type_info.get(mem_type, ((150, 150, 150), '?', '其他'))
            
            # 背景框
            mem_rect = pygame.Rect(content_rect.x + 5, y, content_rect.width - 10, line_h - 4)
            pygame.draw.rect(screen, (40, 45, 55), mem_rect, border_radius=4)
            pygame.draw.rect(screen, color, mem_rect, 1, border_radius=4)
            
            # 图标和类型（使用中文名称）
            type_str = f"{icon} {type_name}"
            type_surf = self.font_small.render(type_str, True, color)
            screen.blit(type_surf, (mem_rect.x + 6, mem_rect.y + 3))
            
            # 时间（转换为游戏日期）
            day = mem_time // 1440 + 1  # 假设1440分钟/天
            time_str = f"第{day}天"
            time_surf = self.font_small.render(time_str, True, (120, 120, 120))
            screen.blit(time_surf, (mem_rect.right - time_surf.get_width() - 8, mem_rect.y + 3))
            
            # 描述 - 控制长度避免超框
            desc = mem.get('description', mem.get('desc', ''))
            # 计算可用宽度，考虑内边距
            max_desc_width = mem_rect.width - 16
            # 逐字符截断，确保不超框
            if desc:
                while len(desc) > 0:
                    test_surf = self.font_small.render(desc, True, (180, 180, 180))
                    if test_surf.get_width() <= max_desc_width:
                        break
                    desc = desc[:-1]
                if len(desc) < len(mem.get('description', mem.get('desc', ''))) and len(desc) > 0:
                    desc = desc[:-2] + '..'
            desc_surf = self.font_small.render(desc if desc else '(无描述)', True, (180, 180, 180))
            screen.blit(desc_surf, (mem_rect.x + 8, mem_rect.y + 20))
            
            y += line_h
    
    def _draw_npc_tab_relations(self, screen, npc, player, content_rect):
        """
        绘制 Tab 3: 人际关系页
        显示NPC与其他角色的好感度关系
        """
        pygame.draw.rect(screen, (30, 35, 45), content_rect, border_radius=5)
        pygame.draw.rect(screen, (80, 80, 100), content_rect, 1, border_radius=5)
        
        # 获取好感度字典
        affinity_dict = getattr(npc, 'affinity', {})
        
        # 标题
        title_text = f"【人际关系】(共{len(affinity_dict)}人)"
        title = self.font_small.render(title_text, True, (150, 200, 250))
        screen.blit(title, (content_rect.x + 8, content_rect.y + 5))
        
        y = content_rect.y + 28
        line_h = 26
        max_visible = (content_rect.height - 35) // line_h
        
        if not affinity_dict:
            empty_t = self.font_small.render("（暂无社交记录）", True, (100, 100, 100))
            screen.blit(empty_t, (content_rect.x + 12, y))
            return
        
        # 按好感度排序（从高到低）
        sorted_relations = sorted(affinity_dict.items(), key=lambda x: x[1], reverse=True)
        
        for i, (target_id, affinity) in enumerate(sorted_relations):
            if y + line_h > content_rect.bottom - 8:
                remaining = len(sorted_relations) - i
                more_txt = f"…还有{remaining}人"
                more = self.font_small.render(more_txt, True, (120, 150, 180))
                screen.blit(more, (content_rect.x + 12, y))
                break
            
            # 尝试获取目标名称
            target_name = self._get_name_by_id(target_id, player, npc)
            
            # 根据好感度选择颜色和态度文字
            if affinity >= 80:
                aff_color = (255, 150, 200)  # 粉色 - 亲密
                attitude = "亲密[爱]"
            elif affinity >= 50:
                aff_color = (100, 255, 100)  # 绿色 - 友好
                attitude = "友好"
            elif affinity >= 20:
                aff_color = (150, 200, 150)  # 浅绿 - 好感
                attitude = "好感"
            elif affinity >= -20:
                aff_color = (180, 180, 180)  # 灰色 - 中立
                attitude = "中立"
            elif affinity >= -50:
                aff_color = (200, 150, 100)  # 橙色 - 冷淡
                attitude = "冷淡"
            else:
                aff_color = (255, 80, 80)    # 红色 - 敌视
                attitude = "敌视"
            
            # 显示关系条目
            # 名称
            name_surf = self.font_small.render(target_name, True, (220, 220, 220))
            screen.blit(name_surf, (content_rect.x + 10, y + 3))
            
            # 好感度数值
            aff_str = f"{affinity:+d}"
            aff_surf = self.font_small.render(aff_str, True, aff_color)
            screen.blit(aff_surf, (content_rect.x + 120, y + 3))
            
            # 态度文字
            att_surf = self.font_small.render(attitude, True, aff_color)
            screen.blit(att_surf, (content_rect.right - att_surf.get_width() - 10, y + 3))
            
            # 好感度条
            bar_x = content_rect.x + 160
            bar_y = y + 6
            bar_w = 60
            bar_h = 10
            
            # 背景
            pygame.draw.rect(screen, (40, 40, 50), (bar_x, bar_y, bar_w, bar_h), border_radius=3)
            
            # 填充（中间为0，左右为正负）
            center_x = bar_x + bar_w // 2
            if affinity >= 0:
                fill_w = int((bar_w / 2) * min(affinity, 100) / 100)
                if fill_w > 0:
                    pygame.draw.rect(screen, aff_color, (center_x, bar_y, fill_w, bar_h), border_radius=3)
            else:
                fill_w = int((bar_w / 2) * min(-affinity, 100) / 100)
                if fill_w > 0:
                    pygame.draw.rect(screen, aff_color, (center_x - fill_w, bar_y, fill_w, bar_h), border_radius=3)
            
            # 中线
            pygame.draw.line(screen, (100, 100, 100), (center_x, bar_y), (center_x, bar_y + bar_h))
            
            y += line_h
    
    def _draw_drop_confirm_dialog(self, screen, npc, mx, my, click_event):
        """
        绘制丢弃物品确认弹窗（子弹窗，覆盖在背包页上）
        
        Returns:
            pending_action: None | ("DROP_ITEM_CONFIRM", item, count)
        """
        item_name = self._drop_confirm_item
        max_count = npc.inventory.get(item_name, 1)
        drop_count = getattr(self, '_drop_confirm_count', 1)
        
        # 确保 drop_count 在有效范围内
        drop_count = max(1, min(drop_count, max_count))
        
        # 弹窗尺寸和位置（屏幕中央）
        dialog_w, dialog_h = 280, 200
        dialog_x = (self.screen_w - dialog_w) // 2
        dialog_y = (self.screen_h - dialog_h) // 2
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_w, dialog_h)
        
        # 半透明遮罩
        overlay = pygame.Surface((self.screen_w, self.screen_h))
        overlay.set_alpha(160)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))
        
        # 弹窗背景
        pygame.draw.rect(screen, (35, 40, 50), dialog_rect, border_radius=10)
        pygame.draw.rect(screen, (150, 100, 100), dialog_rect, 3, border_radius=10)
        
        # 标题
        title_surf = self.font_ui.render(f"丢弃: {item_name}", True, (255, 200, 200))
        screen.blit(title_surf, (dialog_rect.centerx - title_surf.get_width() // 2, dialog_rect.y + 15))
        
        # 当前数量提示
        info_txt = f"你持有 {max_count} 个"
        info_surf = self.font_small.render(info_txt, True, (180, 180, 180))
        screen.blit(info_surf, (dialog_rect.centerx - info_surf.get_width() // 2, dialog_rect.y + 45))
        
        pending_action = None
        
        # === 数量选择区（仅当数量 > 1 时显示） ===
        if max_count > 1:
            ctrl_y = dialog_rect.y + 75
            
            # 减号按钮
            btn_minus = pygame.Rect(dialog_rect.x + 40, ctrl_y, 35, 35)
            if self.draw_button(screen, btn_minus, "-", self.font_big, mx, my, (80, 60, 60)):
                if click_event:
                    self._drop_confirm_count = max(1, drop_count - 1)
            
            # 数量显示
            num_surf = self.font_big.render(str(drop_count), True, (255, 255, 255))
            num_x = dialog_rect.centerx - num_surf.get_width() // 2
            screen.blit(num_surf, (num_x, ctrl_y + 5))
            
            # 加号按钮
            btn_plus = pygame.Rect(dialog_rect.right - 75, ctrl_y, 35, 35)
            if self.draw_button(screen, btn_plus, "+", self.font_big, mx, my, (60, 80, 60)):
                if click_event:
                    self._drop_confirm_count = min(max_count, drop_count + 1)
            
            # 快捷按钮：全部
            btn_all = pygame.Rect(dialog_rect.centerx - 25, ctrl_y + 40, 50, 22)
            if self.draw_button(screen, btn_all, "全部", self.font_small, mx, my, (70, 70, 90)):
                if click_event:
                    self._drop_confirm_count = max_count
        else:
            # 数量为1时，直接显示提示
            hint_surf = self.font_small.render("将丢弃仅有的 1 个", True, (200, 180, 150))
            screen.blit(hint_surf, (dialog_rect.centerx - hint_surf.get_width() // 2, dialog_rect.y + 80))
        
        # === 底部按钮区 ===
        btn_y = dialog_rect.bottom - 50
        btn_w = 80
        btn_gap = 20
        
        # 确认丢弃按钮
        btn_confirm = pygame.Rect(dialog_rect.centerx - btn_w - btn_gap // 2, btn_y, btn_w, 35)
        if self.draw_button(screen, btn_confirm, "丢弃", self.font_ui, mx, my, (150, 70, 70)):
            if click_event:
                pending_action = ("DROP_ITEM_CONFIRM", item_name, drop_count)
                # 重置状态
                self._drop_confirm_item = None
                self._drop_confirm_count = 1
        
        # 取消按钮
        btn_cancel = pygame.Rect(dialog_rect.centerx + btn_gap // 2, btn_y, btn_w, 35)
        if self.draw_button(screen, btn_cancel, "取消", self.font_ui, mx, my, (70, 70, 70)):
            if click_event:
                # 取消，关闭弹窗
                self._drop_confirm_item = None
                self._drop_confirm_count = 1
                pending_action = None
        
        return pending_action
    
    def _get_name_by_id(self, target_id, player, npc=None):
        """根据ID获取角色名称（辅助方法）
        
        优先级：
        1. 如果是玩家自己，返回"玩家(你)"
        2. 从NPC或玩家的记忆中查找 target_name
        3. 返回默认的 "角色#ID" 格式
        """
        # 检查是否是玩家
        player_id = getattr(player, 'id', 9999)
        if target_id == player_id:
            return "玩家(你)"
        
        # 优先从当前NPC的记忆中查找
        if npc and hasattr(npc, 'memory'):
            for m in npc.memory:
                if m.get('target_id') == target_id and m.get('target_name'):
                    return m.get('target_name')
        
        # 再从玩家的记忆中查找
        if player and hasattr(player, 'memory'):
            for m in player.memory:
                if m.get('target_id') == target_id and m.get('target_name'):
                    return m.get('target_name')
        
        # 检查是否在 _npc_name_cache 中（如果有）
        if hasattr(self, '_npc_name_cache') and target_id in self._npc_name_cache:
            return self._npc_name_cache[target_id]
        
        return f"角色#{target_id}"
    
    def draw_fee_confirm_dialog(self, screen, pending_action, player, mx, my, click_event):
        """
        【手续费系统】绘制手续费确认弹窗
        
        【升级】现在支持三种情况：
        1. 中立/友好：支付手续费
        2. 同盟：享受折扣
        3. 敌对：警告会触发警报
        
        Args:
            pending_action: {
                'user': 操作者,
                'building': 目标建筑,
                'fee_info': 费用信息字典,
                'stack_target': 原堆叠目标,
                'dragged_card': 被拖拽的卡牌,
            }
            
        Returns:
            'CONFIRM' | 'CANCEL' | None
        """
        if not pending_action:
            return None
        
        fee_info = pending_action['fee_info']
        building = pending_action['building']
        user = pending_action['user']
        dragged_card = pending_action['dragged_card']
        
        fee = fee_info['fee']
        controller_name = fee_info['controller_name']
        is_hostile = fee_info.get('is_hostile', False)
        allow_use = fee_info.get('allow_use', True)
        discount_rate = fee_info.get('discount_rate', 1.0)
        reason = fee_info.get('reason', '场地费')
        
        # 弹窗尺寸（敌对情况下需要更大空间显示警告）
        dialog_w = 380
        dialog_h = 260 if is_hostile else 220
        dialog_x = (self.screen_w - dialog_w) // 2
        dialog_y = (self.screen_h - dialog_h) // 2
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_w, dialog_h)
        
        # 绘制半透明遮罩
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))
        
        # 弹窗背景（敌对时用红色调）
        if is_hostile:
            bg_color = (60, 35, 35)
            border_color = (180, 80, 80)
        else:
            bg_color = (50, 45, 40)
            border_color = (150, 130, 90)
        
        pygame.draw.rect(screen, bg_color, dialog_rect, border_radius=8)
        pygame.draw.rect(screen, border_color, dialog_rect, 3, border_radius=8)
        
        # 标题
        if is_hostile:
            title = "! 敌对势力领地！"
            title_color = (255, 80, 80)
        elif discount_rate < 1.0:
            title = "* 盟友折扣"
            title_color = (100, 200, 255)
        else:
            title = "! 需支付使用费"
            title_color = (255, 200, 100)
        
        title_surf = self.font_big.render(title, True, title_color)
        screen.blit(title_surf, (dialog_x + (dialog_w - title_surf.get_width()) // 2, dialog_y + 15))
        
        # 势力信息
        y = dialog_y + 55
        building_name = getattr(building, 'name', '建筑')
        
        # 根据情况显示不同信息
        info_lines = [
            f"此{building_name}属于【{controller_name}】势力范围",
        ]
        
        if is_hostile:
            info_lines.extend([
                f"强行使用将触发警报！",
                f"周围敌人会立即攻击你！",
            ])
        elif discount_rate <= 0.5:
            info_lines.append(f"盟友身份享受 {int((1-discount_rate)*100)}% 折扣")
        
        if fee > 0:
            info_lines.append(f"费用: {fee} 铜钱 ({reason})")
        
        for line in info_lines:
            line_color = (255, 150, 150) if is_hostile and "警报" in line else (230, 230, 230)
            line_surf = self.font_ui.render(line, True, line_color)
            screen.blit(line_surf, (dialog_x + 20, y))
            y += 26
        
        # 玩家余额显示
        y += 5
        user_money = user.inventory.get(ITEM_COIN, 0)
        can_afford = user_money >= fee
        
        balance_color = (100, 255, 100) if can_afford else (255, 100, 100)
        balance_text = f"你的铜钱: {user_money}" + (f" (需要: {fee})" if fee > 0 else "")
        balance_surf = self.font_ui.render(balance_text, True, balance_color)
        screen.blit(balance_surf, (dialog_x + 20, y))
        
        # 操作说明
        y += 28
        action_name = getattr(dragged_card, 'name', '???')
        if is_hostile:
            hint = f"冒险使用？{action_name} 可能会被攻击！"
            hint_color = (255, 180, 100)
        else:
            hint = f"是否让 {action_name} 继续操作？"
            hint_color = (180, 180, 180)
        hint_surf = self.font_small.render(hint, True, hint_color)
        screen.blit(hint_surf, (dialog_x + 20, y))
        
        # 按钮区域
        btn_y = dialog_y + dialog_h - 55
        btn_w = 120 if is_hostile else 100
        btn_h = 35
        btn_gap = 30
        
        # 确认按钮
        btn_confirm_rect = pygame.Rect(
            dialog_x + dialog_w // 2 - btn_w - btn_gap // 2,
            btn_y, btn_w, btn_h
        )
        
        if is_hostile:
            confirm_text = "冒险使用"
            confirm_disabled = False  # 敌对情况下强制可以选择
        else:
            confirm_text = f"支付 ({fee}铜)" if fee > 0 else "确认"
            confirm_disabled = not can_afford and fee > 0
        
        if confirm_disabled:
            pygame.draw.rect(screen, (60, 60, 60), btn_confirm_rect, border_radius=5)
            btn_text = self.font_ui.render(confirm_text, True, (100, 100, 100))
        elif btn_confirm_rect.collidepoint(mx, my):
            btn_color = (150, 80, 80) if is_hostile else (80, 120, 80)
            pygame.draw.rect(screen, btn_color, btn_confirm_rect, border_radius=5)
            btn_text = self.font_ui.render(confirm_text, True, (255, 255, 255))
        else:
            btn_color = (120, 60, 60) if is_hostile else (60, 100, 60)
            pygame.draw.rect(screen, btn_color, btn_confirm_rect, border_radius=5)
            btn_text = self.font_ui.render(confirm_text, True, (230, 230, 230))
        
        screen.blit(btn_text, (
            btn_confirm_rect.centerx - btn_text.get_width() // 2,
            btn_confirm_rect.centery - btn_text.get_height() // 2
        ))
        
        # 取消按钮
        btn_cancel_rect = pygame.Rect(
            dialog_x + dialog_w // 2 + btn_gap // 2,
            btn_y, btn_w, btn_h
        )
        
        if btn_cancel_rect.collidepoint(mx, my):
            pygame.draw.rect(screen, (120, 80, 80), btn_cancel_rect, border_radius=5)
            btn_text = self.font_ui.render("取消", True, (255, 255, 255))
        else:
            pygame.draw.rect(screen, (100, 60, 60), btn_cancel_rect, border_radius=5)
            btn_text = self.font_ui.render("取消", True, (230, 230, 230))
        
        screen.blit(btn_text, (
            btn_cancel_rect.centerx - btn_text.get_width() // 2,
            btn_cancel_rect.centery - btn_text.get_height() // 2
        ))
        
        # 处理点击
        if click_event:
            if btn_confirm_rect.collidepoint(mx, my) and not confirm_disabled:
                # 敌对情况返回特殊标记
                return 'CONFIRM_HOSTILE' if is_hostile else 'CONFIRM'
            elif btn_cancel_rect.collidepoint(mx, my):
                return 'CANCEL'
        
        return None

    def _draw_npc_tab_inner_heart(self, screen, npc, content_rect, mx=None, my=None, click_event=None):
        """
        绘制"内心"页签：上部分性格特质，下部分内心隐秘（人生困境）
        """
        font_title = self.font_ui
        font_text = self.font_small
        
        # 绘制内容区域背景
        pygame.draw.rect(screen, (30, 35, 45), content_rect, border_radius=5)
        pygame.draw.rect(screen, (80, 80, 100), content_rect, 1, border_radius=5)
        
        # 获取personality数据
        personality_obj = getattr(npc, 'personality', None)
        if personality_obj is None:
            personality = {}
        elif hasattr(personality_obj, 'to_dict'):
            personality = personality_obj.to_dict()
        else:
            personality = personality_obj
        
        initial_dilemma = getattr(npc, 'initial_dilemma', {}) or {}
        
        # ═══════════════════════════════════════════════════════════════
        # 上半部分：性格特质（居中布局）
        # ═══════════════════════════════════════════════════════════════
        content_center_x = content_rect.centerx
        y = content_rect.y + 12
        
        # 标题
        section_title = font_title.render("性格特质", True, (255, 215, 0))
        screen.blit(section_title, (content_center_x - section_title.get_width() // 2, y))
        y += 28
        
        # 性格维度 - 使用拔河进度条显示（全部居中）
        # 格式: (key, 维度名称, 左端标签(0), 右端标签(100), 左端颜色, 右端颜色)
        # 颜色设计：左冷色 → 右暖色，中间渐变，直观显示偏向
        dimensions = [
            ('temper', '性情', '温和', '暴躁', (80, 160, 220), (220, 80, 80)),    # 蓝 → 红
            ('spirit', '胆量', '胆小', '勇敢', (150, 150, 180), (80, 180, 80)),    # 灰紫 → 绿
            ('ism', '主义', '理想', '现实', (220, 180, 100), (100, 140, 200)),     # 金黄 → 蓝灰
            ('act_style', '作风', '缜密', '豪放', (100, 160, 160), (200, 140, 80)), # 青灰 → 橙
            ('friendship', '情义', '重情义', '不重情义', (80, 180, 120), (180, 80, 100)) # 绿 → 玫红
        ]
        
        bar_width = 100
        bar_height = 12
        name_width = 40      # 维度名称宽度
        label_width = 50     # 左右极端标签宽度
        
        for key, name, left_label, right_label, left_color, right_color in dimensions:
            # 直接获取数值 (0-100)，新格式已经是数值化
            raw_value = personality.get(key, 50)
            if isinstance(raw_value, (int, float)):
                value = int(raw_value)
            else:
                # 兼容旧格式：如果是字符串，尝试转换或映射
                try:
                    value = int(raw_value)
                except (ValueError, TypeError):
                    value = 50  # 默认值
            
            # 计算总宽度用于居中: 名称 + 左标签 + 进度条 + 右标签
            total_width = name_width + label_width + bar_width + label_width
            start_x = content_center_x - total_width // 2
            
            # 维度名称（最左侧）
            name_surf = font_text.render(name, True, (200, 200, 200))
            screen.blit(name_surf, (start_x, y))
            
            # 左极端标签
            left_label_x = start_x + name_width
            left_label_surf = font_text.render(left_label, True, left_color)
            screen.blit(left_label_surf, (left_label_x, y))
            
            # 进度条位置
            bar_x = left_label_x + label_width
            bar_rect = pygame.Rect(bar_x, y + 2, bar_width, bar_height)
            pygame.draw.rect(screen, (60, 60, 60), bar_rect, border_radius=3)
            
            # 中立滑块式设计：滑块位置直接代表倾向程度
            # value 0-100，0=最左(左侧标签)，100=最右(右侧标签)，50=中间
            
            # 绘制轨道背景
            track_rect = pygame.Rect(bar_x, y + 4, bar_width, bar_height - 4)
            pygame.draw.rect(screen, (60, 60, 60), track_rect, border_radius=2)
            
            # 计算滑块位置
            slider_x = bar_x + int((value / 100) * bar_width)
            slider_y = y + bar_height // 2 + 1
            slider_radius = 4  # 改小一点
            
            # 绘制滑块（圆形，颜色根据位置渐变）
            t = value / 100  # 0.0 ~ 1.0
            slider_color = (
                int(left_color[0] + (right_color[0] - left_color[0]) * t),
                int(left_color[1] + (right_color[1] - left_color[1]) * t),
                int(left_color[2] + (right_color[2] - left_color[2]) * t)
            )
            
            # 绘制滑块阴影（立体效果）
            pygame.draw.circle(screen, (40, 40, 40), (slider_x, slider_y + 1), slider_radius)
            # 绘制滑块主体
            pygame.draw.circle(screen, slider_color, (slider_x, slider_y), slider_radius)
            
            # 中心标记点（显示50%默认位置）
            center_x = bar_x + bar_width // 2
            pygame.draw.circle(screen, (100, 100, 100), (center_x, slider_y), 2)
            
            # 右极端标签
            right_label_x = bar_x + bar_width + 5
            right_label_surf = font_text.render(right_label, True, right_color)
            screen.blit(right_label_surf, (right_label_x, y))
            
            y += 22
        
        # 野心（滑块式，与性格维度统一）
        ambition = personality.get('ambition', 50)
        if hasattr(ambition, 'value'):
            ambition = ambition.value
        ambition_value = int(ambition) if isinstance(ambition, (int, float)) else 50
        
        # 使用与性格维度相同的布局: 名称 + 左标签("低") + 滑块 + 右标签("高")
        total_width = name_width + label_width + bar_width + label_width
        start_x = content_center_x - total_width // 2
        
        name_surf = font_text.render("野心", True, (200, 180, 150))
        screen.blit(name_surf, (start_x, y))
        
        # 左标签"低"
        left_label_x = start_x + name_width
        left_label_surf = font_text.render("低", True, (150, 150, 150))
        screen.blit(left_label_surf, (left_label_x, y))
        
        # 滑块轨道
        bar_x = left_label_x + label_width
        track_rect = pygame.Rect(bar_x, y + 4, bar_width, bar_height - 4)
        pygame.draw.rect(screen, (60, 60, 60), track_rect, border_radius=2)
        
        # 计算滑块位置
        slider_x = bar_x + int((ambition_value / 100) * bar_width)
        slider_y = y + bar_height // 2 + 1
        slider_radius = 4
        
        # 野心滑块颜色（低=灰，高=橙黄）
        low_color = (150, 150, 150)
        high_color = (220, 160, 80)
        t = ambition_value / 100
        slider_color = (
            int(low_color[0] + (high_color[0] - low_color[0]) * t),
            int(low_color[1] + (high_color[1] - low_color[1]) * t),
            int(low_color[2] + (high_color[2] - low_color[2]) * t)
        )
        
        # 绘制滑块
        pygame.draw.circle(screen, (40, 40, 40), (slider_x, slider_y + 1), slider_radius)
        pygame.draw.circle(screen, slider_color, (slider_x, slider_y), slider_radius)
        
        # 右标签"高"
        right_label_x = bar_x + bar_width + 5
        right_label_surf = font_text.render("高", True, high_color)
        screen.blit(right_label_surf, (right_label_x, y))
        
        y += 22
        
        # 渴望类型（字符串显示，与上方对齐）
        desire_type = personality.get('desire_type', '')
        
        total_width = name_width + label_width + bar_width + label_width
        start_x = content_center_x - total_width // 2
        
        name_surf = font_text.render("渴望", True, (180, 160, 140))
        screen.blit(name_surf, (start_x, y))
        
        # 渴望类型直接显示为文字
        desire_text = str(desire_type) if desire_type else "普通"
        value_surf = font_text.render(desire_text, True, (220, 180, 140))
        screen.blit(value_surf, (start_x + name_width + 10, y))
        y += 22
        
        # ═══════════════════════════════════════════════════════════════
        # 分隔线
        # ═══════════════════════════════════════════════════════════════
        y += 5
        pygame.draw.line(screen, (80, 80, 100), (content_rect.x + 10, y), (content_rect.right - 10, y))
        y += 15
        
        # ═══════════════════════════════════════════════════════════════
        # 下半部分：当前困境与四幕阶段（从StoryDirector获取）
        # ═══════════════════════════════════════════════════════════════
        
        # 尝试从StoryDirector获取当前故事弧信息
        current_phase = None
        current_dilemma_info = None
        story_beats = []
        
        # 只在点击事件时打印调试信息
        if click_event:
            print(f"[NPC面板] ===== 点击内心 tab: NPC {npc.id} =====")
            
            try:
                director = StoryDirector.get_instance()
                print(f"[NPC面板] director: {director}, _initialized: {getattr(director, '_initialized', 'N/A')}")
                
                if director and hasattr(director, 'active_arcs') and director.active_arcs:
                    print(f"[NPC面板] active_arcs keys: {list(director.active_arcs.keys())}")
                    arc = director.active_arcs.get(npc.id)
                    print(f"[NPC面板] arc for {npc.id}: {arc}")
                else:
                    print(f"[NPC面板] director 或 active_arcs 无效")
            except Exception as e:
                print(f"[NPC面板] 错误: {e}")
        
        try:
            director = StoryDirector.get_instance()
            # 检查 director 是否已初始化（有 active_arcs）
            if director and hasattr(director, 'active_arcs') and director.active_arcs:
                arc = director.active_arcs.get(npc.id)
                
                if arc is None:
                    pass  # 静默处理
                elif arc.seed and hasattr(arc.seed, 'story_beats') and arc.seed.story_beats is not None:
                    story_beats = arc.seed.story_beats
                    # 根据story_beats数量推断当前阶段
                    beat_count = len(story_beats)
                    if beat_count == 0:
                        current_phase = "未触发"
                    elif beat_count == 1:
                        current_phase = "起"
                    elif beat_count == 2:
                        current_phase = "承"
                    elif beat_count == 3:
                        current_phase = "转"
                    else:
                        current_phase = "合"
                    # 获取最新的困境信息
                    if story_beats:
                        latest_beat = story_beats[-1]
                        current_dilemma_info = {
                            'event_summary': latest_beat.event_summary,
                            'player_choice': latest_beat.player_choice,
                            'dilemma_type': getattr(latest_beat, 'dilemma_type', ''),
                            'consequence_summary': getattr(latest_beat, 'consequence_summary', '')
                        }
        except Exception as e:
            # 忽略错误，保持默认值
            pass
        
        # 绘制四幕阶段指示器
        phase_title = font_title.render("故事阶段", True, (255, 215, 0))
        screen.blit(phase_title, (content_center_x - phase_title.get_width() // 2, y))
        y += 26
        
        # 四幕阶段进度条
        phase_stages = ["起", "承", "转", "合"]
        phase_colors = {
            "起": (80, 180, 80),    # 绿色 - 风声渐起
            "承": (80, 160, 220),   # 蓝色 - 矛盾升级
            "转": (220, 160, 80),   # 橙色 - 高潮爆发
            "合": (180, 80, 180),   # 紫色 - 尘埃落定
            "未触发": (100, 100, 100)  # 灰色
        }
        
        # 绘制阶段节点
        phase_bar_y = y
        phase_bar_width = content_rect.width - 60
        phase_node_radius = 12
        phase_node_spacing = phase_bar_width // 3
        
        # 绘制阶段连线
        line_start_x = content_rect.x + 30
        line_end_x = line_start_x + phase_bar_width
        pygame.draw.line(screen, (60, 60, 70), (line_start_x, phase_bar_y), (line_end_x, phase_bar_y), 3)
        
        # 标记当前位置
        if current_phase and current_phase != "未触发":
            current_index = phase_stages.index(current_phase) if current_phase in phase_stages else -1
        else:
            current_index = -1
        
        # 初始化节点点击区域列表（用于点击检测）
        node_click_rects = []
        
        # 节点状态枚举
        PHASE_COMPLETED = "completed"   # 已完成
        PHASE_CURRENT = "current"       # 当前待处理
        PHASE_FUTURE = "future"         # 未来未知
        
        # 绘制每个阶段节点
        for i, stage in enumerate(phase_stages):
            node_x = line_start_x + i * phase_node_spacing
            node_color = phase_colors.get(stage, (100, 100, 100))
            
            # 确定节点状态
            if current_index >= 0:
                if i < current_index:
                    # 已完成的阶段（过去的）
                    phase_status = PHASE_COMPLETED
                elif i == current_index:
                    # 当前阶段（待处理）
                    phase_status = PHASE_CURRENT
                else:
                    # 未来未知阶段
                    phase_status = PHASE_FUTURE
            else:
                # 未触发任何阶段
                phase_status = PHASE_FUTURE
            
            # 根据状态设置显示效果
            if phase_status == PHASE_COMPLETED:
                # 已完成：实心 + 白色边框 + 勾选标记
                fill_color = node_color
                border_color = (255, 255, 255)
                is_clickable = True
                status_label = "已完成"
            elif phase_status == PHASE_CURRENT:
                # 当前：实心 + 闪烁边框 + 脉冲效果
                fill_color = node_color
                border_color = (255, 220, 100)  # 金色边框
                is_clickable = True
                status_label = "待处理"
            else:
                # 未来：空心 + 灰色边框
                fill_color = (50, 50, 60)
                border_color = (80, 80, 90)
                is_clickable = False
                status_label = "未解锁"
            
            # 绘制节点填充
            pygame.draw.circle(screen, fill_color, (node_x, phase_bar_y), phase_node_radius)
            # 绘制节点边框
            pygame.draw.circle(screen, border_color, (node_x, phase_bar_y), phase_node_radius, 2)
            
            # 如果是已完成或当前阶段，绘制小标记
            if phase_status == PHASE_COMPLETED:
                # 绘制勾选标记
                check_size = 4
                check_points = [
                    (node_x - check_size, phase_bar_y),
                    (node_x - 2, phase_bar_y + check_size),
                    (node_x + check_size, phase_bar_y - check_size)
                ]
                pygame.draw.lines(screen, (255, 255, 255), False, check_points, 2)
            elif phase_status == PHASE_CURRENT:
                # 绘制脉冲圆环
                import time
                pulse = int((time.time() % 1) * 6) + 6
                pygame.draw.circle(screen, (255, 220, 100), (node_x, phase_bar_y), phase_node_radius + pulse, 1)
            
            # 绘制阶段文字
            stage_text = font_text.render(stage, True, (255, 255, 255))
            screen.blit(stage_text, (node_x - stage_text.get_width() // 2, phase_bar_y - stage_text.get_height() // 2))
            
            # 存储节点点击区域
            node_rect = pygame.Rect(node_x - phase_node_radius - 5, phase_bar_y - phase_node_radius - 5,
                                    phase_node_radius * 2 + 10, phase_node_radius * 2 + 10)
            node_click_rects.append({
                'rect': node_rect,
                'index': i,
                'stage': stage,
                'status': phase_status,
                'is_clickable': is_clickable,
                'beat_data': story_beats[i] if i < len(story_beats) else None
            })
            
            # 在节点下方显示状态标签
            status_color = {
                PHASE_COMPLETED: (100, 200, 100),
                PHASE_CURRENT: (255, 200, 100),
                PHASE_FUTURE: (100, 100, 100)
            }.get(phase_status, (100, 100, 100))
            
            status_text = font_text.render(status_label, True, status_color)
            screen.blit(status_text, (node_x - status_text.get_width() // 2, phase_bar_y + phase_node_radius + 3))
        
        # 处理节点点击事件 - 点击任一可点击节点都跳转到大宋实况
        if click_event and mx is not None and my is not None:
            for node_info in node_click_rects:
                if node_info['is_clickable'] and node_info['rect'].collidepoint(mx, my):
                    # 无论是当前阶段还是已完成阶段，都跳转到大宋实况查看
                    toggle_live_news_panel()
                    break
        
        # 显示当前阶段名称
        y += 30
        phase_desc = current_phase if current_phase else "未知"
        phase_desc_color = phase_colors.get(phase_desc, (150, 150, 150))
        current_phase_text = font_text.render(f"当前阶段: {phase_desc}", True, phase_desc_color)
        screen.blit(current_phase_text, (content_center_x - current_phase_text.get_width() // 2, y))
        y += 25
        
        # ═══════════════════════════════════════════════════════════════
        # 当前困境详情
        # ═══════════════════════════════════════════════════════════════
        if current_dilemma_info:
            # 困境标题
            dilemma_header = font_title.render("当前困境", True, (220, 180, 220))
            screen.blit(dilemma_header, (content_center_x - dilemma_header.get_width() // 2, y))
            y += 26
            
            # 困境内容区域
            max_content_width = content_rect.width - 40
            
            # 事件摘要
            event_text = current_dilemma_info.get('event_summary', '暂无')
            event_lines = self._wrap_text(event_text, font_text, max_content_width)
            for line in event_lines[:3]:  # 最多显示3行
                event_surf = font_text.render(line, True, (200, 200, 200))
                screen.blit(event_surf, (content_rect.x + 20, y))
                y += font_text.get_height() + 2
            
            y += 5
            
            # 困境类型
            dilemma_type = current_dilemma_info.get('dilemma_type', '')
            if dilemma_type:
                type_label = font_text.render(f"困境类型: {dilemma_type}", True, (180, 150, 150))
                screen.blit(type_label, (content_rect.x + 20, y))
                y += font_text.get_height() + 2
            
            # 玩家选择
            player_choice = current_dilemma_info.get('player_choice', '')
            if player_choice:
                choice_label = font_text.render(f"你的选择: {player_choice[:30]}", True, (150, 180, 150))
                screen.blit(choice_label, (content_rect.x + 20, y))
                y += font_text.get_height() + 2
        else:
            # 无困境时显示提示
            no_dilemma = font_text.render("暂无触发困境事件", True, (120, 120, 120))
            screen.blit(no_dilemma, (content_center_x - no_dilemma.get_width() // 2, y + 20))
            
            # 如果有initial_dilemma，提示可以查看
            if initial_dilemma:
                y += 50
                hint = font_text.render("可触发困境事件查看详情", True, (100, 100, 120))
                screen.blit(hint, (content_center_x - hint.get_width() // 2, y))
        
        # 【测试按钮】触发AI事件生成
        test_btn_w = 60
        test_btn_h = 22
        test_btn_x = content_rect.right - test_btn_w - 20
        test_btn_y = content_rect.bottom - test_btn_h - 15
        test_btn_rect = pygame.Rect(test_btn_x, test_btn_y, test_btn_w, test_btn_h)
        
        # 绘制测试按钮
        is_test_hover = test_btn_rect.collidepoint(mx, my) if mx is not None and my is not None else False
        test_bg_color = (100, 80, 120) if is_test_hover else (70, 55, 85)
        test_border_color = (180, 150, 200) if is_test_hover else (120, 100, 140)
        pygame.draw.rect(screen, test_bg_color, test_btn_rect, border_radius=4)
        pygame.draw.rect(screen, test_border_color, test_btn_rect, 1, border_radius=4)
        
        test_text = font_text.render("触发事件", True, (220, 200, 240))
        screen.blit(test_text, (test_btn_rect.centerx - test_text.get_width() // 2, 
                               test_btn_rect.centery - test_text.get_height() // 2))
        
        # 处理测试按钮点击
        if click_event and is_test_hover:
            ctx = getattr(self, '_game_ctx', None)
            StoryDirector.trigger_dilemma_test_event(npc, ctx)

    def _get_dimension_labels(self, key):
        """获取性格维度的左右标签（用于数值映射）"""
        labels = {
            'temper': ('性急', '温和'),
            'spirit': ('胆小', '勇敢'),
            'ism': ('理想', '现实'),
            'act_style': ('轻率', '慎重'),
            'friendship': ('凉薄', '重义')
        }
        return labels.get(key, ('低', '高'))

    def _map_desire_to_value(self, desire_str):
        """将物欲字符串映射为0-100的数值"""
        if not desire_str or desire_str == '普通':
            return 50
        mappings = {
            '淡泊': 10, '清心寡欲': 15, '低': 20,
            '一般': 50, '普通': 50,
            '贪心': 70, '重利': 75, '高': 80,
            '极度贪婪': 90, '欲壑难填': 95, '极高': 100
        }
        return mappings.get(desire_str, 50)

    
    
    def _wrap_text(self, text, font, max_width):
        """将文本按最大宽度换行，返回行列表"""
        if not text:
            return []
        
        # 首先按显式换行符分割
        paragraphs = text.split('\n')
        all_lines = []
        
        for para_idx, paragraph in enumerate(paragraphs):
            if para_idx > 0:
                # 段落之间添加空行（可选）
                pass
            
            if not paragraph:
                all_lines.append("")
                continue
            
            # 对每段进行自动换行
            lines = []
            current_line = ""
            
            for char in paragraph:
                test_line = current_line + char
                if font.size(test_line)[0] <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = char
            
            if current_line:
                lines.append(current_line)
            
            all_lines.extend(lines)
        
        return all_lines if all_lines else [text]

    def _map_personality_str_to_value(self, key, value_str):
        """将性格字符串映射为0-100的数值"""
        # 映射表：低值对应负面/极端，高值对应正面/温和，普通对应50
        mappings = {
            'temper': {'性急': 20, '温和': 80, '普通': 50},
            'spirit': {'胆小': 20, '勇敢': 80, '普通': 50},
            'ism': {'理想': 20, '现实': 80, '普通': 50},
            'act_style': {'轻率': 20, '慎重': 80, '普通': 50},
            'friendship': {'凉薄': 20, '重视情义': 80, '不重情义': 20, '重义': 80, '普通': 50},
        }
        mapping = mappings.get(key, {})
        return mapping.get(value_str, 50)

    def _draw_wrapped_text(self, screen, text, font, rect, color):
        """绘制自动换行的文本"""
        words = text
        x, y = rect.x, rect.y
        max_width = rect.width
        line_height = font.get_height() + 2
        
        # 简单按字符换行（中文）
        current_line = ""
        for char in words:
            test_line = current_line + char
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    line_surface = font.render(current_line, True, color)
                    screen.blit(line_surface, (x, y))
                    y += line_height
                current_line = char
                if y > rect.bottom - line_height:
                    break
        
        if current_line and y <= rect.bottom - line_height:
            line_surface = font.render(current_line, True, color)
            screen.blit(line_surface, (x, y))
