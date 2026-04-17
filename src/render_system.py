# --- src/render_system.py ---
import pygame
import math
from src.definitions import *
from src.entities import NPC,Resource
from src.utils import log_game_event
class RenderSystem:
    def __init__(self, screen, ui_manager, world_map, ft_manager):
        self.screen = screen
        self.ui_manager = ui_manager
        self.world_map = world_map
        self.ft_manager = ft_manager
        self.camera = None   # 由 main.py 注入，None 时退化为单屏模式
        
        # ═══════════════════════════════════════════════════════════════
        # 【系统功能菜单】折叠状态
        # ═══════════════════════════════════════════════════════════════
        self.system_menu_expanded = False  # 是否展开系统功能菜单

    def render(self, context, mx, my, click_event, event=None):
        """
        统一渲染入口
        context: GameContext 对象 (或包含必要引用的对象)
        """
        screen = self.screen
        all_cards = context.all_cards
        player = context.player
        current_state = context.current_state
        interaction_mgr = context.interaction_mgr
        combat_manager = context.combat_manager
        story_ui = context.story_ui
        cam = self.camera   # 可能为 None（单屏模式）

        # ── 说话状态标记 ──────────────────────────────────────────
        for card in all_cards:
            if hasattr(card, 'is_talking'):
                card.is_talking = False
        speaker_id = story_ui.get_current_speaker_id()
        if speaker_id:
            speaker = next((n for n in all_cards if hasattr(n, 'id') and n.id == speaker_id), None)
            if speaker:
                speaker.is_talking = True

        # ── 1. 绘制地图背景 ───────────────────────────────────────
        self.world_map.draw_background(screen, cam)

        # ── 2. 卡牌排序与绘制 ────────────────────────────────────
        # 【修复】角色卡默认绘制在建筑卡上层
        # 排序优先级：1. 建筑卡（最底层）→ 2. 资源卡 → 3. NPC/角色卡（最上层）
        # 同类型内部按堆叠层级排序
        def get_render_layer(card):
            from src.entities import NPC, Building
            from src.entities.resource import Resource
            
            # 基础层级：建筑=0，资源=1000，NPC=2000
            if isinstance(card, Building):
                base_layer = 0
            elif isinstance(card, Resource):
                base_layer = 1000
            elif isinstance(card, NPC):
                base_layer = 2000
            else:
                base_layer = 500  # 未知类型放中间
            
            # 堆叠层级附加
            stack_layer = 0
            curr = card
            while curr.stack_parent:
                stack_layer += 1
                curr = curr.stack_parent
            
            return base_layer + stack_layer

        sorted_cards = sorted(all_cards, key=get_render_layer)

        # 拖拽中的卡牌强制提到最上层
        if interaction_mgr.dragged_card:
            if interaction_mgr.dragged_card in sorted_cards:
                sorted_cards.remove(interaction_mgr.dragged_card)
                sorted_cards.append(interaction_mgr.dragged_card)

        for card in sorted_cards:
            # ── 隐身检查：隐身单位根据DEBUG开关决定是否绘制 ──
            if getattr(card, 'is_invisible', False):
                if not DEBUG_SHOW_INVISIBLE:
                    continue  # 不绘制隐身单位
                # DEBUG模式下继续绘制，稍后添加特殊标记
            
            # ── 视口裁剪：屏幕外不渲染（逻辑层继续运行）──
            if cam is not None and not cam.is_visible(card.rect, margin=20):
                continue
            if cam is not None:
                # 临时将 rect 平移到屏幕坐标，绘制后还原（不污染逻辑坐标）
                sx, sy = cam.world_to_screen(card.rect.x, card.rect.y)
                ox, oy = card.rect.x, card.rect.y
                card.rect.x, card.rect.y = int(sx), int(sy)
                card.draw(screen, self.ui_manager.font_sys)
                
                # 【新增】隐身单位的特殊标记（紫色半透明边框）
                if getattr(card, 'is_invisible', False) and DEBUG_SHOW_INVISIBLE:
                    invis_surf = pygame.Surface((card.rect.w, card.rect.h), pygame.SRCALPHA)
                    invis_surf.fill((180, 100, 220, 80))  # 紫色半透明覆盖
                    screen.blit(invis_surf, card.rect.topleft)
                    pygame.draw.rect(screen, (200, 100, 255), card.rect, 2)  # 紫色边框
                
                card.rect.x, card.rect.y = ox, oy
                
                # 【新增】绘制行为气泡（在屏幕坐标系下）
                self._draw_action_bubble(screen, card, sx, sy)
            else:
                card.draw(screen, self.ui_manager.font_sys)
                
                # 隐身标记（无镜头模式）
                if getattr(card, 'is_invisible', False) and DEBUG_SHOW_INVISIBLE:
                    invis_surf = pygame.Surface((card.rect.w, card.rect.h), pygame.SRCALPHA)
                    invis_surf.fill((180, 100, 220, 80))
                    screen.blit(invis_surf, card.rect.topleft)
                    pygame.draw.rect(screen, (200, 100, 255), card.rect, 2)
                
                # 【新增】绘制行为气泡（无镜头模式）
                self._draw_action_bubble(screen, card, card.rect.x, card.rect.y)

        # ── 2.5 绘制玩家操作范围圈（拖拽中显示）────────────────
        drag_circle = interaction_mgr.get_drag_circle_info()
        if drag_circle:
            cx, cy, radius = drag_circle
            # 转换为屏幕坐标
            if cam is not None:
                sx, sy = cam.world_to_screen(cx, cy)
            else:
                sx, sy = cx, cy
            # 绘制半透明圆形（淡蓝色）
            circle_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(circle_surf, (80, 180, 255, 60), (radius, radius), radius)  # 填充
            pygame.draw.circle(circle_surf, (100, 200, 255, 150), (radius, radius), radius, 2)  # 边框
            screen.blit(circle_surf, (int(sx - radius), int(sy - radius)))

        # ── 2.6 绘制任务目标指引标记（黄色菱形/箭头）────────────────
        self._draw_quest_marker(screen, context, cam)

        # ── 3. 选中框与调试线 ────────────────────────────────────
        if context.selected_npc:
            sel = context.selected_npc
            if cam is not None:
                sx, sy = cam.world_to_screen(sel.rect.x, sel.rect.y)
                sel_rect = pygame.Rect(int(sx), int(sy), sel.rect.w, sel.rect.h)
            else:
                sel_rect = sel.rect
            pygame.draw.rect(screen, COLOR_HIGHLIGHT, sel_rect, 3)
            if DEBUG_NPCPATHFINDING and isinstance(sel, NPC):
                self._draw_npc_debug(sel, cam)

        # ── 4. 浮动文字 & 投射物 ──────────────────────────────────
        self.ft_manager.update()
        self.ft_manager.draw(screen, self.ui_manager.font_sys, cam)

        for p in combat_manager.projectiles:
            if cam is not None:
                p.draw(screen, cam)
            else:
                p.draw(screen)

        # ── 4.5 事件区域遮罩（半透明+边框）────────────────────────
        self._draw_event_zone(context, screen, cam)

        # ── 4.6 昼夜遮罩（在世界之上、UI之下）─────────────────────
        sfx = getattr(context, 'screen_effects', None)
        if sfx:
            sfx.draw_day_night(screen)

        # ── 5. UI 层（固定坐标，不随摄像机移动）──────────────────
        self._draw_ui_layer(context, mx, my, click_event)

        # ── 6. 小地图 ────────────────────────────────────────────
        if cam is not None:
            cam.draw_minimap(screen, self.world_map, all_cards,
                             font=self.ui_manager.font_small)

        # ── 7. 剧情与调试层 ──────────────────────────────────────
        # 注意：story_ui.draw() 已移至 main.py 中 screen_effects.draw() 之后，
        # 确保对话框不被淡入淡出遮罩覆盖
        self._draw_modals(context, mx, my, click_event, event)

        if DEBUG_NPCPATHFINDING and hasattr(self.world_map, 'pathfinder'):
            self.world_map.pathfinder.draw_debug(screen, self.ui_manager.font_small)
            self._draw_player_debug(player, cam)

        # 注意：flip() 已移至 main.py 统一调用，避免多次刷新导致闪烁

    def _draw_event_zone(self, ctx, screen, cam):
        """
        绘制事件区域遮罩（半透明+边框）
        
        Args:
            ctx: 游戏上下文
            screen: Pygame 屏幕对象
            cam: 摄像机对象（可能为 None）
        """
        # 检查是否有活跃的事件区域
        event_zone = getattr(ctx, '_event_zone', None)
        if not event_zone or not event_zone.get('active', False):
            return
        
        center_x = event_zone.get('center_x', 0)
        center_y = event_zone.get('center_y', 0)
        radius = event_zone.get('radius', 300)
        
        # 应用摄像机偏移
        if cam is not None:
            draw_x = center_x - cam.offset_x
            draw_y = center_y - cam.offset_y
        else:
            draw_x = center_x
            draw_y = center_y
        
        # 创建半透明遮罩表面
        mask_size = radius * 2 + 4  # 边框占 2 像素
        mask_surface = pygame.Surface((mask_size, mask_size), pygame.SRCALPHA)
        
        # 绘制半透明圆形区域（淡红色，表示事件区）
        # 外圈：半透明遮罩
        pygame.draw.circle(mask_surface, (255, 200, 200, 40), 
                          (radius + 2, radius + 2), radius)
        
        # 边框：红色虚线效果（用多个短弧线模拟）
        border_color = (255, 100, 100, 180)
        num_dashes = 36  # 虚线段数
        for i in range(num_dashes):
            if i % 2 == 0:  # 间隔绘制，形成虚线
                start_angle = i * 2 * math.pi / num_dashes
                end_angle = (i + 1) * 2 * math.pi / num_dashes
                # 绘制弧线
                rect = pygame.Rect(2, 2, radius * 2, radius * 2)
                pygame.draw.arc(mask_surface, border_color, rect, 
                               start_angle, end_angle, 3)
        
        # 绘制到屏幕
        screen.blit(mask_surface, (draw_x - radius - 2, draw_y - radius - 2))

    def _draw_ui_layer(self, ctx, mx, my, click_event):
        # 顶部时间栏
        mx, my = pygame.mouse.get_pos()
        # 注意：此处 click_event 需要从外部传入或在 Render 内部不处理逻辑只绘制
        # 既然 UIManager.draw_xxx 包含了逻辑，我们需要小心。
        # 这里仅负责绘制调用。
        
        self.ui_manager.draw_top_bar(self.screen, ctx.event_manager, mx, my, click_event)
        
        # ═══════════════════════════════════════════════════════════════
        # 【系统功能菜单】绘制在小地图上方
        # ═══════════════════════════════════════════════════════════════
        self._draw_system_menu(ctx, mx, my, click_event)

        # 侧边栏 (带点击交互 → 打开玩家详情)
        sidebar_result = self.ui_manager.draw_sidebar(self.screen, ctx.player, ctx.all_cards, ctx.tech_manager, ctx.quest_manager, mx, my, click_event)
        
        # 处理侧边栏点击
        if sidebar_result:
            if sidebar_result == 'OPEN_PLAYER_DETAIL' and ctx.current_state == GAME_STATE_PLAYING:
                ctx.active_event_npc = ctx.player
                ctx.current_state = GAME_STATE_NPC_DETAIL
                # 默认打开属性tab
                self.ui_manager._npc_detail_tab = 0
            elif isinstance(sidebar_result, tuple) and sidebar_result[0] == 'OPEN_PLAYER_DETAIL':
                # 带tab索引的打开请求
                if ctx.current_state == GAME_STATE_PLAYING:
                    ctx.active_event_npc = ctx.player
                    ctx.current_state = GAME_STATE_NPC_DETAIL
                    # 设置UI管理器的tab索引
                    self.ui_manager._npc_detail_tab = sidebar_result[1]
            elif sidebar_result == 'OPEN_FOLLOWER_PANEL' and ctx.current_state == GAME_STATE_PLAYING:
                ctx.current_state = GAME_STATE_FOLLOWER_PANEL
            elif sidebar_result == 'TASK_CLICKED':
                # 任务详情弹窗已显示，不需要额外处理
                pass
        
        # 绘制任务详情弹窗（如果有）
        from src.ui.sidebar import draw_task_detail_panel, is_task_detail_visible
        if is_task_detail_visible():
            draw_task_detail_panel(self.screen, self.ui_manager.font_ui)


    def _draw_modals(self, ctx, mx, my, click_event, event=None):
        screen = self.screen
        
        if ctx.current_state == GAME_STATE_TECH_TREE:
            if self.ui_manager.draw_tech_tree(screen, ctx.tech_manager, ctx.player, mx, my, click_event):
                ctx.current_state = GAME_STATE_PLAYING
                
        elif ctx.current_state == GAME_STATE_NEWS_FEED:
            if self.ui_manager.draw_news_feed(screen, ctx.event_manager, mx, my, click_event):
                ctx.current_state = GAME_STATE_PLAYING
                
        elif ctx.current_state == GAME_STATE_ROSTER:
            # 简单封装以适配 draw_roster
            class SimpleMgr: pass
            sm = SimpleMgr(); sm.npcs = [c for c in ctx.all_cards if isinstance(c, NPC) and c != ctx.player]
            
            self.ui_manager.draw_roster(screen, sm)
            
            # 返回按钮逻辑
            back_rect = pygame.Rect(self.screen.get_width() - 120, self.screen.get_height() - 60, 100, 40)
            if self.ui_manager.draw_button(screen, back_rect, "返回", self.ui_manager.font_ui, mx, my):
                 if click_event: ctx.current_state = GAME_STATE_PLAYING
            
            if click_event: 
                self.ui_manager.handle_roster_click(sm.npcs, mx, my)

        elif ctx.current_state == GAME_STATE_NPC_DETAIL and ctx.active_event_npc:
            # 临时注入 all_cards，供 get_display_info 内仇恨列表反查名字使用
            self.ui_manager.all_cards = ctx.all_cards
            res = self.ui_manager.draw_npc_detail(screen, ctx.active_event_npc, ctx.player, mx, my, click_event, ctx.ft_manager, event)
            
            # 处理 UI 返回的逻辑
            if isinstance(res, tuple) and res[0] == "DROP_ITEM_CONFIRM":
                # 带数量的丢弃确认
                item_name = res[1]
                drop_count = res[2] if len(res) > 2 else 1
                print(f"[UI->DROP] 收到丢弃请求: {item_name} x{drop_count}, NPC={ctx.active_event_npc.name}")
                result = ctx.active_event_npc.drop_item(item_name, ctx.all_cards, count=drop_count)
                print(f"[UI->DROP] 丢弃结果: {result}")
            
            elif isinstance(res, tuple) and res[0] == "DROP_ITEM":
                # 兼容旧的单件丢弃（如果还有其他地方调用）
                print(f"[UI->DROP] 收到丢弃请求: {res[1]}, NPC={ctx.active_event_npc.name}")
                result = ctx.active_event_npc.drop_item(res[1], ctx.all_cards)
                print(f"[UI->DROP] 丢弃结果: {result}")

            elif isinstance(res, tuple) and res[0] == "USE_FOOD":
                # 【新增】吃东西 - 恢复饥饿值
                item_name = res[1]
                self._handle_use_food(ctx.player, item_name, ctx.ft_manager)
            
            elif isinstance(res, tuple) and res[0] == "EQUIP_ITEM":
                # 【新增】装备物品
                item_name = res[1]
                self._handle_equip_item(ctx.player, item_name, ctx.ft_manager)
            
            elif isinstance(res, tuple) and res[0] == "UNEQUIP_ITEM":
                # 【新增】卸下物品
                item_name = res[1]
                self._handle_unequip_item(ctx.player, item_name, ctx.ft_manager)

            elif isinstance(res, tuple) and res[0] in ("REQUEST_ITEM", "STEAL_ITEM"):
                self._handle_npc_item_action(res[0], res[1], ctx)

            elif res == True: 
                # 关闭面板
                #print(f"关闭了角色信息面板")
                ctx.input_delay = 10
                ctx.player.bounce_off(ctx.active_event_npc)
                ctx.current_state = GAME_STATE_PLAYING
                ctx.event_manager.request_interaction_resume()
            elif res == "GOTO_EVENT": 
                ctx.current_state = GAME_STATE_EVENT_DIALOG
            elif res == "AUTO_STACK": 
                # 闲聊：自动飞过去
                ctx.interaction_mgr.manual_stack(ctx.player, ctx.active_event_npc, ctx.all_cards)
                ctx.current_state = GAME_STATE_PLAYING
                ctx.event_manager.request_interaction_resume()
            elif res == "NEGOTIATE":
                # 【新增】进入交涉界面
                ctx.current_state = GAME_STATE_PERSUASION
            
            elif res == "AI_CHAT":
                # 【修复】进入AI聊天界面 - 确保立即响应
                print(f"[RenderSystem] 收到AI_CHAT请求，NPC: {ctx.active_event_npc.name}")
                from src.llm import get_chat_integration
                chat_integration = get_chat_integration()
                # 【关键修复】传入ctx以便检查StoryUI状态
                if chat_integration.start_chat(ctx.active_event_npc, ctx=ctx):
                    # 成功开始聊天，关闭NPC详情面板
                    print(f"[RenderSystem] AI聊天启动成功")
                    ctx.current_state = GAME_STATE_PLAYING
                    ctx.event_manager.request_interaction_resume()
                else:
                    # 无法聊天 - 根据具体原因显示不同提示
                    fail_reason = chat_integration.get_last_fail_reason()
                    print(f"[RenderSystem] AI聊天启动失败，原因: {fail_reason}")
                    
                    if hasattr(ctx, 'ft_manager'):
                        npc = ctx.active_event_npc
                        npc_name = getattr(npc, 'name', '对方')
                        
                        if fail_reason == "STORY_ACTIVE":
                            # StoryUI正在播放对话（NPC正在说任务台词）
                            msg = f"请等{npc_name}说完话再闲聊"
                        elif fail_reason == "NPC_UNAVAILABLE":
                            # NPC状态不允许（战斗/死亡等）
                            msg = f"{npc_name}现在无法与你对话"
                        else:
                            # 其他未知原因
                            msg = "无法对话"
                        
                        ctx.ft_manager.add_text(msg, 
                            npc.rect.centerx, 
                            npc.rect.top - 30, 
                            (255, 200, 100))  # 橙黄色提示
            
            elif isinstance(res, tuple) and res[0] == "ORG_TASK_DIALOG":
                # 【组织任务】打开长老对话界面
                org_id = res[1]
                elder_npc = res[2]
                ctx.org_task_dialog_org_id = org_id
                ctx.org_task_dialog_elder = elder_npc
                ctx.current_state = GAME_STATE_ORG_TASK_DIALOG
        
        elif ctx.current_state == GAME_STATE_RESOURCE_DETAIL and ctx.active_resource_card:
            if ctx.active_resource_card not in ctx.all_cards: 
                ctx.current_state = GAME_STATE_PLAYING
            else:
                act = self.ui_manager.draw_resource_detail(screen, ctx.active_resource_card, mx, my, click_event, ctx.ft_manager)
                if act == "CLOSE": 
                    
                    ctx.input_delay = 10
                    ctx.current_state = GAME_STATE_PLAYING
                    ctx.event_manager.request_interaction_resume()
                elif isinstance(act, tuple) and act[0] == "SPLIT":
                    split_amt = act[1]
                    if ctx.active_resource_card.count > split_amt:
                        ctx.active_resource_card.count -= split_amt
                        new_res = Resource(ctx.active_resource_card.rect.x+40, ctx.active_resource_card.rect.y+40, 
                                           ctx.active_resource_card.item_type, count=split_amt)
                        # 这里需要 import Resource，如果报错请在文件头添加 from src.entities import Resource
                        new_res.bounce_off(ctx.active_resource_card)
                        ctx.all_cards.append(new_res)
        
        elif ctx.current_state == GAME_STATE_EVENT_DIALOG and ctx.active_event_npc:
            npc_list = [c for c in ctx.all_cards if isinstance(c, NPC) and c != ctx.player]
            act, eff, chain, txt = self.ui_manager.draw_event_dialog(screen, ctx.active_event_npc, ctx.player, mx, my, click_event, npc_list)
            if act == "RESOLVE":
                res = ctx.event_manager.resolve_event(ctx.active_event_npc, eff, chain, ctx.player, txt)
                for ft in res.get('floating_texts', []): ctx.ft_manager.add_text(*ft)
                ctx.current_state = GAME_STATE_PLAYING
            elif act == "CLOSE":
                ctx.player.bounce_off(ctx.active_event_npc)
                ctx.current_state = GAME_STATE_PLAYING
        
        elif ctx.current_state == GAME_STATE_DAILY_REPORT:
            if self.ui_manager.draw_daily_report(screen, ctx.daily_report_data, mx, my, click_event):
                ctx.current_state = GAME_STATE_PLAYING
                
        elif ctx.current_state == GAME_STATE_GAME_OVER:
             self.ui_manager.draw_game_over(screen, ctx.game_result_msg)
            
        elif ctx.current_state == GAME_STATE_QUEST_LOG:
            if self.ui_manager.draw_quest_log(screen, ctx.quest_manager, mx, my, click_event):
                ctx.current_state = GAME_STATE_PLAYING
        
        # 【阶段4】势力关系面板
        elif ctx.current_state == GAME_STATE_FACTION_VIEW:
            # 获取所有NPC用于势力统计
            all_npcs = ctx.all_cards if hasattr(ctx, 'all_cards') else []
            if hasattr(ctx, 'faction_war') and self.ui_manager.draw_faction_view(screen, ctx.faction_war, ctx.player, mx, my, click_event, all_npcs):
                ctx.current_state = GAME_STATE_PLAYING
            
            # 【新增】处理门派任务接取请求
            if hasattr(self.ui_manager, '_pending_task_accept') and self.ui_manager._pending_task_accept:
                org_id, task_id = self.ui_manager._pending_task_accept
                self.ui_manager._pending_task_accept = None  # 清除请求
                
                from src.org_task_system import get_org_task_system
                org_task_sys = get_org_task_system()
                success, msg = org_task_sys.accept_task(org_id, task_id, ctx.ft_manager, ctx.player)
                
                if success:
                    ctx.ft_manager.add_text(msg, ctx.player.rect.centerx, ctx.player.rect.top - 30, (100, 255, 150))
                else:
                    ctx.ft_manager.add_text(msg, ctx.player.rect.centerx, ctx.player.rect.top - 30, (255, 100, 100))
        
        # 【阶段1】语言检定界面
        elif ctx.current_state == GAME_STATE_PERSUASION and ctx.active_event_npc:
            from src.persuasion_system import persuasion_system
            action = self.ui_manager.draw_persuasion_dialog(
                screen, ctx.player, ctx.active_event_npc, 
                persuasion_system, mx, my, click_event, ctx.ft_manager
            )
            
            if action == 'CANCEL':
                ctx.current_state = GAME_STATE_NPC_DETAIL
            elif isinstance(action, tuple) and action[0] == 'PERSUADE':
                # 执行检定
                method = action[1]
                bribe_amount = action[2] if len(action) > 2 else 0
                
                if method == 'persuade':
                    result, rate, msg = persuasion_system.check_persuade(ctx.player, ctx.active_event_npc)
                elif method == 'threaten':
                    result, rate, msg = persuasion_system.check_threaten(ctx.player, ctx.active_event_npc)
                elif method == 'bribe':
                    result, rate, msg = persuasion_system.check_bribe(ctx.player, ctx.active_event_npc, bribe_amount)
                    # 扣除贿赂金额（无论成功失败）
                    if bribe_amount > 0:
                        ctx.player.money -= bribe_amount
                        ctx.active_event_npc.money = getattr(ctx.active_event_npc, 'money', 0) + bribe_amount
                else:
                    result, rate, msg = 'FAILURE', 0, '未知方法'
                
                # 保存结果供结果界面显示
                ctx.persuasion_result = result
                ctx.persuasion_message = msg
                ctx.persuasion_method = method
                
                # 处理检定后果
                self._handle_persuasion_result(ctx, result, method)
                
                # 切换到结果显示界面
                ctx.current_state = GAME_STATE_PERSUASION_RESULT
        
        # 【阶段1】检定结果显示
        elif ctx.current_state == GAME_STATE_PERSUASION_RESULT:
            result_type = getattr(ctx, 'persuasion_result', 'FAILURE')
            message = getattr(ctx, 'persuasion_message', '检定结束')
            
            close_action = self.ui_manager.draw_persuasion_result(
                screen, result_type, message, mx, my, click_event
            )
            
            if close_action == 'CLOSE':
                # 根据结果决定返回哪个状态
                if result_type in ['SUCCESS', 'CRIT_SUCCESS']:
                    # 成功：可能关闭面板或触发后续事件
                    ctx.current_state = GAME_STATE_PLAYING
                    ctx.event_manager.request_interaction_resume()
                else:
                    # 失败：返回NPC详情页
                    ctx.current_state = GAME_STATE_NPC_DETAIL
        
        # 【组织任务】长老对话界面
        elif ctx.current_state == GAME_STATE_ORG_TASK_DIALOG:
            org_id = getattr(ctx, 'org_task_dialog_org_id', None)
            elder_npc = getattr(ctx, 'org_task_dialog_elder', None)
            
            if org_id and elder_npc:
                from src.org_task_system import get_org_task_system
                org_task_sys = get_org_task_system()
                
                # 调用对话框绘制
                action = self.ui_manager.draw_org_task_dialog(
                    screen, ctx.player, org_id, elder_npc,
                    org_task_sys, mx, my, click_event
                )
                
                # 处理返回动作
                if action == 'CLOSE':
                    # 关闭对话框，返回NPC详情页
                    ctx.current_state = GAME_STATE_NPC_DETAIL
                    
                elif isinstance(action, tuple) and action[0] == 'ACCEPT':
                    # 接取任务
                    task_id = action[1]
                    success, msg = org_task_sys.accept_task(
                        org_id, task_id, ctx.ft_manager, ctx.player
                    )
                    if success:
                        ctx.ft_manager.add_text(
                            f"[ok] {msg}",
                            ctx.player.rect.centerx, ctx.player.rect.top - 40,
                            (100, 255, 150)
                        )
                    else:
                        ctx.ft_manager.add_text(
                            f"[x] {msg}",
                            ctx.player.rect.centerx, ctx.player.rect.top - 40,
                            (255, 100, 100)
                        )
                    # 留在对话框继续操作
                    
                elif isinstance(action, tuple) and action[0] == 'TURNIN':
                    # 交付任务
                    task_id = action[1]
                    success, msg, rewards = org_task_sys.turn_in_task(
                        org_id, task_id, ctx.player, ctx.ft_manager
                    )
                    if success:
                        # 奖励已在turn_in_task中通过ft_manager显示
                        pass
                    else:
                        ctx.ft_manager.add_text(
                            f"[x] {msg}",
                            ctx.player.rect.centerx, ctx.player.rect.top - 40,
                            (255, 100, 100)
                        )
                    # 留在对话框继续操作
            else:
                # 状态异常，返回游戏
                ctx.current_state = GAME_STATE_PLAYING
        
        # ══════════════════════════════════════════════════════════════
        # 【门客管理】门客管理面板
        # ══════════════════════════════════════════════════════════════
        elif ctx.current_state == GAME_STATE_FOLLOWER_PANEL:
            if self.ui_manager.draw_follower_panel(screen, ctx.player, ctx.all_cards, mx, my, click_event):
                ctx.current_state = GAME_STATE_PLAYING
        
        # ══════════════════════════════════════════════════════════════
        # 【阶层系统】护卫拦截界面
        # ══════════════════════════════════════════════════════════════
        elif ctx.current_state == GAME_STATE_GUARD_INTERCEPT:
            guard = getattr(ctx, 'intercept_guard', None)
            leader = getattr(ctx, 'intercept_leader', None)
            
            if guard and leader:
                action = self._draw_guard_intercept_dialog(
                    screen, ctx.player, guard, leader, mx, my, click_event, ctx.ft_manager
                )
                
                if action == 'LEAVE':
                    # 离开：玩家自动后退，护卫恢复跟随状态
                    guard.state = STATE_IDLE
                    guard.intercept_target = None
                    guard.intercept_leader = None
                    ctx.current_state = GAME_STATE_PLAYING
                    ctx.event_manager.request_interaction_resume()
                    ctx.ft_manager.add_text("知趣地离开", ctx.player.rect.centerx, ctx.player.rect.top - 40, (200, 200, 200))
                    
                elif action == 'BRIBE_SUCCESS':
                    # 贿赂成功：护卫放行
                    guard.state = STATE_IDLE
                    guard.intercept_target = None
                    guard.intercept_leader = None
                    ctx.current_state = GAME_STATE_PLAYING
                    ctx.event_manager.request_interaction_resume()
                    
                elif action == 'BRIBE_FAIL':
                    # 贿赂失败：护卫变得敌对（但不立即攻击，给玩家机会离开）
                    guard.hatred[ctx.player.id] = guard.hatred.get(ctx.player.id, 0) + 30
                    ctx.ft_manager.add_text("护卫怒目而视", guard.rect.centerx, guard.rect.top - 40, (255, 100, 100))
                    
                elif action == 'FORCE':
                    # 强行通过：触发战斗
                    guard.state = STATE_COMBAT
                    guard.aggro_target = ctx.player
                    guard.intercept_target = None
                    guard.intercept_leader = None
                    ctx.current_state = GAME_STATE_PLAYING
                    ctx.event_manager.request_interaction_resume()
                    ctx.ft_manager.add_text(f"{guard.name}拔刀!", guard.rect.centerx, guard.rect.top - 40, (255, 50, 50))
                    
            else:
                # 状态异常
                ctx.current_state = GAME_STATE_PLAYING
                ctx.event_manager.request_interaction_resume()
        
        # ══════════════════════════════════════════════════════════════
        # 【手续费系统】使用费确认弹窗
        # ══════════════════════════════════════════════════════════════
        elif ctx.current_state == GAME_STATE_FEE_CONFIRM:
            pending_action = ctx.pending_fee_action
            
            if pending_action:
                result = self.ui_manager.draw_fee_confirm_dialog(
                    screen, pending_action, ctx.player, mx, my, click_event
                )
                
                if result == 'CONFIRM':
                    # 支付手续费并执行堆叠
                    from src.faction_war_system import get_faction_war_system
                    faction_war = get_faction_war_system()
                    
                    fee = pending_action['fee_info']['fee']
                    user = pending_action['user']
                    building = pending_action['building']
                    dragged_card = pending_action['dragged_card']
                    stack_target = pending_action['stack_target']
                    
                    # 支付费用
                    success, msg = faction_war.pay_usage_fee(user, building, fee)
                    
                    if success:
                        # 执行堆叠
                        ctx.interaction_mgr.manual_stack(dragged_card, stack_target, ctx.all_cards)
                        ctx.ft_manager.add_text(f"-{fee}铜", user.rect.centerx, user.rect.top - 30, (255, 200, 100))
                    else:
                        ctx.ft_manager.add_text(msg, user.rect.centerx, user.rect.top - 30, (255, 100, 100))
                    
                    # 清理状态
                    ctx.pending_fee_action = None
                    ctx.current_state = GAME_STATE_PLAYING
                    
                elif result == 'CONFIRM_HOSTILE':
                    # 【敌对警报】强行使用敌对设施，触发警报！
                    from src.faction_war_system import get_faction_war_system
                    faction_war = get_faction_war_system()
                    
                    fee = pending_action['fee_info']['fee']
                    user = pending_action['user']
                    building = pending_action['building']
                    dragged_card = pending_action['dragged_card']
                    stack_target = pending_action['stack_target']
                    controller_name = pending_action['fee_info'].get('controller_name', '???')
                    
                    # 仍然支付费用（加价后的）
                    if fee > 0:
                        success, msg = faction_war.pay_usage_fee(user, building, fee)
                        if not success:
                            ctx.ft_manager.add_text(msg, user.rect.centerx, user.rect.top - 30, (255, 100, 100))
                            ctx.pending_fee_action = None
                            ctx.current_state = GAME_STATE_PLAYING
                            return  # 无法支付，取消操作
                        ctx.ft_manager.add_text(f"-{fee}铜", user.rect.centerx, user.rect.top - 30, (255, 200, 100))
                    
                    # 执行堆叠
                    ctx.interaction_mgr.manual_stack(dragged_card, stack_target, ctx.all_cards)
                    
                    # 【警报系统】触发敌对警报（传入控制势力ID以正确匹配NPC）
                    controller_org_id = pending_action['fee_info'].get('controller_org', None)
                    self._trigger_hostile_alarm(ctx, user, building, controller_name, controller_org_id)
                    
                    # 清理状态
                    ctx.pending_fee_action = None
                    ctx.current_state = GAME_STATE_PLAYING
                    
                elif result == 'CANCEL':
                    # 取消操作
                    ctx.pending_fee_action = None
                    ctx.current_state = GAME_STATE_PLAYING
            else:
                # 状态异常
                ctx.pending_fee_action = None
                ctx.current_state = GAME_STATE_PLAYING

        # ══════════════════════════════════════════════════════════════
        # 【建筑面板】显示建筑详情与占领功能
        # ══════════════════════════════════════════════════════════════
        elif ctx.current_state == GAME_STATE_BUILDING_INFO:
            building = getattr(ctx, 'active_building', None)
            
            if building:
                from src.faction_war_system import get_faction_war_system
                faction_war = get_faction_war_system()
                
                close_clicked, occupy_clicked = self.ui_manager.draw_building_info_panel(
                    screen, building, ctx.player, faction_war, mx, my, click_event
                )
                
                if close_clicked:
                    ctx.active_building = None
                    ctx.current_state = GAME_STATE_PLAYING
                    ctx.event_manager.request_interaction_resume()
                
                elif occupy_clicked:
                    # 执行占领操作
                    player_org = getattr(ctx.player, 'org_id', None)
                    if player_org and player_org != 'NONE':
                        # 发起争夺
                        success, msg = faction_war.start_contest(building, player_org)
                        if success:
                            ctx.ft_manager.add_text(f"[战] 发起占领！", building.rect.centerx, building.rect.top - 30, (255, 200, 100))
                            log_game_event(f"[BUILDING] 玩家势力 {player_org} 发起对 {building.name} 的占领")
                        else:
                            ctx.ft_manager.add_text(msg, building.rect.centerx, building.rect.top - 30, (255, 100, 100))
                    
                    # 关闭面板
                    ctx.active_building = None
                    ctx.current_state = GAME_STATE_PLAYING
                    ctx.event_manager.request_interaction_resume()
            else:
                ctx.current_state = GAME_STATE_PLAYING
        
        # ══════════════════════════════════════════════════════════════
        # 【命运图谱】NPC命运轨迹面板
        # ══════════════════════════════════════════════════════════════
        elif ctx.current_state == GAME_STATE_FATE_GRAPH:
            from src.ui.fate_graph_ui import get_fate_graph_ui
            
            fate_ui = get_fate_graph_ui(screen.get_width(), screen.get_height())
            fate_ui.set_fonts(self.ui_manager.font_big, self.ui_manager.font_ui, self.ui_manager.font_small)
            
            # 加载数据
            story_director = getattr(ctx, 'story_director', None)
            # 从player获取天数，从event_manager获取game_tick计算季节
            current_day = getattr(ctx.player, 'day', 1)
            fate_ui.load_data(story_director, ctx.all_cards, current_day)
            
            # 处理事件（支持滚轮滚动和滚动条拖动）
            mouse_down = (event.type == pygame.MOUSEBUTTONDOWN) if event else False
            mouse_up = (event.type == pygame.MOUSEBUTTONUP) if event else False
            # 获取鼠标滚轮值
            scroll_y = 0
            if event and event.type == pygame.MOUSEWHEEL:
                scroll_y = event.y
            action = fate_ui.handle_event(mx, my, click_event, mouse_down, mouse_up, scroll_y)
            if action == "CLOSE":
                ctx.current_state = GAME_STATE_PLAYING
            elif action and action.startswith("INTERVENE:"):
                # 介入某个NPC的困境
                npc_id = action.split(":")[1]
                # TODO: 触发介入逻辑
                print(f"[FateGraph] 介入NPC: {npc_id}")
                ctx.current_state = GAME_STATE_PLAYING
            elif action and action.startswith("VIEW:"):
                # 查看节点详情
                npc_id = action.split(":")[1]
                print(f"[FateGraph] 查看NPC: {npc_id}")
            
            # 绘制
            game_time = {
                'year': 1 + current_day // 360,
                'season': ["春", "夏", "秋", "冬"][(current_day // 90) % 4],
                'day': current_day
            }
            fate_ui.draw(screen, mx, my, game_time)

    def _trigger_hostile_alarm(self, ctx, user, building, controller_name, controller_org_id=None):
        """
        【敌对警报系统】
        当玩家强行使用敌对势力的建筑时触发：
        1. 在建筑周围一定范围内搜索该势力的NPC
        2. 让这些NPC进入战斗状态，攻击使用者
        3. 显示警报浮动文字
        
        Args:
            ctx: GameContext
            user: 使用者（触发警报的人）
            building: 被使用的建筑
            controller_name: 控制势力名称（用于显示）
            controller_org_id: 控制势力ID（用于匹配NPC），可选
        """
        from src.entities import NPC
        from src.faction_war_system import get_faction_war_system
        
        # 警报范围
        ALARM_RADIUS = 400
        
        # 获取建筑的控制势力（优先使用传入的，否则从系统查询）
        building_controller = controller_org_id
        if not building_controller:
            faction_war = get_faction_war_system()
            building_controller, _ = faction_war.get_building_controller(building)
        
        # 搜索范围内的敌对NPC
        bx, by = building.rect.centerx, building.rect.centery
        alarmed_count = 0
        
        for card in ctx.all_cards:
            if not isinstance(card, NPC):
                continue
            if card is user:  # 不攻击自己
                continue
            if card is ctx.player:  # 不攻击玩家（如果用户不是玩家的情况）
                continue
            
            # 检查是否属于该势力
            npc_org = getattr(card, 'organization', None)
            if not npc_org or npc_org != building_controller:
                continue
            
            # 检查距离
            dx = card.rect.centerx - bx
            dy = card.rect.centery - by
            dist = (dx * dx + dy * dy) ** 0.5
            
            if dist > ALARM_RADIUS:
                continue
            
            # 触发警报：设置仇恨值并切换为战斗状态
            card.hatred = getattr(card, 'hatred', {})
            card.hatred[user.id] = card.hatred.get(user.id, 0) + 100  # 大量仇恨
            card.aggro_target = user
            card.state = STATE_COMBAT
            alarmed_count += 1
            
            # 每个被警报的NPC显示一个浮动文字
            ctx.ft_manager.add_text("!", card.rect.centerx, card.rect.top - 20, (255, 50, 50))
        
        # 显示警报信息
        if alarmed_count > 0:
            ctx.ft_manager.add_text(
                f"[!] 触发{controller_name}警报！{alarmed_count}人来袭！",
                user.rect.centerx, user.rect.top - 50, 
                (255, 80, 80)
            )
            log_game_event(f"[ALARM] {user.name} 在 {building.name} 触发敌对警报，{alarmed_count}名 {controller_name} 成员响应")
        else:
            ctx.ft_manager.add_text(
                f"[!] 触发警报（但附近无人）",
                user.rect.centerx, user.rect.top - 50, 
                (255, 180, 80)
            )
            log_game_event(f"[ALARM] {user.name} 在 {building.name} 触发警报，但附近没有敌人")

    def _draw_guard_intercept_dialog(self, screen, player, guard, leader, mx, my, click_event, ft_manager):
        """
        绘制护卫拦截对话框
        
        选项：
        1. 退让离开（安全选项）
        2. 贿赂护卫（需要金钱，成功率取决于金额和护卫贪婪度）
        3. 强行通过（触发战斗）
        """
        import pygame
        from src.ui.base import COLOR_UI_PANEL, COLOR_BTN, COLOR_TEXT
        
        # 对话框尺寸和位置
        dialog_w, dialog_h = 500, 350
        dialog_x = (self.screen.get_width() - dialog_w) // 2
        dialog_y = (self.screen.get_height() - dialog_h) // 2
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_w, dialog_h)
        
        # 绘制半透明遮罩
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()))
        overlay.set_alpha(180)
        overlay.fill((10, 10, 20))
        screen.blit(overlay, (0, 0))
        
        # 绘制对话框背景
        pygame.draw.rect(screen, COLOR_UI_PANEL, dialog_rect, border_radius=10)
        pygame.draw.rect(screen, (200, 150, 50), dialog_rect, 2, border_radius=10)
        
        # 标题
        leader_level = getattr(leader, 'social_level', 1)
        level_names = {1: '平民', 2: '富户', 3: '官绅', 4: '权贵', 5: '显贵'}
        level_name = level_names.get(leader_level, '贵人')
        
        title = f"[卫] 护卫拦截"
        title_surf = self.ui_manager.font_big.render(title, True, (255, 200, 50))
        screen.blit(title_surf, (dialog_rect.centerx - title_surf.get_width() // 2, dialog_rect.y + 20))
        
        # 描述文本
        desc_lines = [
            f"'{guard.name}'挡住了你的去路。",
            f"",
            f"他身后是{level_name}【{leader.name}】。",
            f"护卫冷冷地说：'这位大人不是你能随便接近的。'",
        ]
        
        y_offset = dialog_rect.y + 70
        for line in desc_lines:
            if line:
                line_surf = self.ui_manager.font_ui.render(line, True, COLOR_TEXT)
                screen.blit(line_surf, (dialog_rect.x + 30, y_offset))
            y_offset += 28
        
        # 按钮区域
        btn_w, btn_h = 140, 45
        btn_gap = 20
        btn_start_x = dialog_rect.centerx - (btn_w * 3 + btn_gap * 2) // 2
        btn_y = dialog_rect.bottom - 80
        
        action = None
        
        # 按钮1：退让离开
        btn1_rect = pygame.Rect(btn_start_x, btn_y, btn_w, btn_h)
        btn1_hover = btn1_rect.collidepoint(mx, my)
        btn1_color = (80, 120, 80) if btn1_hover else (60, 90, 60)
        pygame.draw.rect(screen, btn1_color, btn1_rect, border_radius=6)
        pygame.draw.rect(screen, (100, 150, 100), btn1_rect, 2, border_radius=6)
        btn1_text = self.ui_manager.font_ui.render("退让离开", True, (255, 255, 255))
        screen.blit(btn1_text, (btn1_rect.centerx - btn1_text.get_width() // 2, btn1_rect.centery - btn1_text.get_height() // 2))
        if click_event and btn1_hover:
            action = 'LEAVE'
        
        # 按钮2：贿赂护卫
        bribe_cost = 20 + leader_level * 30  # 贿赂金额根据等级
        can_bribe = player.money >= bribe_cost
        
        btn2_rect = pygame.Rect(btn_start_x + btn_w + btn_gap, btn_y, btn_w, btn_h)
        btn2_hover = btn2_rect.collidepoint(mx, my) and can_bribe
        btn2_color = (120, 100, 50) if btn2_hover else ((80, 70, 40) if can_bribe else (50, 50, 50))
        pygame.draw.rect(screen, btn2_color, btn2_rect, border_radius=6)
        pygame.draw.rect(screen, (150, 120, 50) if can_bribe else (80, 80, 80), btn2_rect, 2, border_radius=6)
        btn2_text = self.ui_manager.font_ui.render(f"贿赂({bribe_cost}钱)", True, (255, 255, 255) if can_bribe else (120, 120, 120))
        screen.blit(btn2_text, (btn2_rect.centerx - btn2_text.get_width() // 2, btn2_rect.centery - btn2_text.get_height() // 2))
        
        if click_event and btn2_hover and can_bribe:
            # 扣钱并判定成功率
            player.money -= bribe_cost
            import random
            # 成功率：基础40% + 金额每多10%增加5%成功率，最高80%
            success_rate = min(0.8, 0.4 + (bribe_cost / 200))
            if random.random() < success_rate:
                action = 'BRIBE_SUCCESS'
                ft_manager.add_text(f"护卫收下{bribe_cost}钱，让开了路", player.rect.centerx, player.rect.top - 40, (255, 230, 100))
            else:
                action = 'BRIBE_FAIL'
                ft_manager.add_text(f"护卫将钱扔回你脸上", player.rect.centerx, player.rect.top - 40, (255, 100, 100))
        
        # 按钮3：强行通过
        btn3_rect = pygame.Rect(btn_start_x + (btn_w + btn_gap) * 2, btn_y, btn_w, btn_h)
        btn3_hover = btn3_rect.collidepoint(mx, my)
        btn3_color = (150, 50, 50) if btn3_hover else (100, 40, 40)
        pygame.draw.rect(screen, btn3_color, btn3_rect, border_radius=6)
        pygame.draw.rect(screen, (200, 80, 80), btn3_rect, 2, border_radius=6)
        btn3_text = self.ui_manager.font_ui.render("强行通过", True, (255, 255, 255))
        screen.blit(btn3_text, (btn3_rect.centerx - btn3_text.get_width() // 2, btn3_rect.centery - btn3_text.get_height() // 2))
        if click_event and btn3_hover:
            action = 'FORCE'
        
        # 显示玩家当前金钱
        money_text = f"你的铜钱: {player.money}"
        money_surf = self.ui_manager.font_small.render(money_text, True, (200, 180, 100))
        screen.blit(money_surf, (dialog_rect.right - money_surf.get_width() - 20, dialog_rect.bottom - 30))
        
        return action

    def _handle_npc_item_action(self, action_type, item_key, ctx):
        """
        处理索要 / 偷窃逻辑（概率判定）

        索要成功率 = 30% + 玩家魅力加成 + 声望加成
          ├ 成功 → NPC 给出1件物品，NPC 轻微不满 (+dissatisfaction)
          └ 失败 → 声望小幅下降，NPC 情绪变差

        偷窃成功率 = 20% + 玩家敏捷加成
          ├ 成功 → 拿走1件，NPC 不知情（无处罚）
          └ 失败 → 声望下降较多，NPC 仇恨值激增（可能追打）
        """
        import random
        npc    = ctx.active_event_npc
        player = ctx.player
        ft_mgr = ctx.ft_manager

        if item_key not in npc.inventory or npc.inventory[item_key] <= 0:
            if ft_mgr: ft_mgr.add_text("对方没有了", npc.rect.x, npc.rect.y - 50, (200, 200, 200))
            return

        # ── 属性读取（带容错）──
        p_charm  = getattr(player, 'charm',  5)
        p_agility= getattr(player, 'agility', 5)
        p_fame   = getattr(player, 'fame',   0)

        if action_type == "REQUEST_ITEM":
            # 索要成功率：基础30% + 魅力加成(每+1 +3%) + 声望加成(每100声望+2%，上限+20%)
            charm_bonus = (p_charm - 5) * 0.03
            fame_bonus  = min(p_fame / 100 * 0.02, 0.20)
            success_rate = max(0.05, min(0.90, 0.30 + charm_bonus + fame_bonus))

            if random.random() < success_rate:
                # ── 成功 ──
                npc.inventory[item_key] -= 1
                if npc.inventory[item_key] <= 0:
                    del npc.inventory[item_key]
                player.inventory[item_key] = player.inventory.get(item_key, 0) + 1
                npc.dissatisfaction = min(getattr(npc, 'dissatisfaction', 0) + 5, 100)
                log_game_event(f"玩家成功向 {npc.name} 索要了 {item_key}")
                if ft_mgr:
                    ft_mgr.add_text(f"索要成功 +{item_key}", npc.rect.x, npc.rect.y - 60, (100, 220, 100))
            else:
                # ── 失败 ──
                player.fame = getattr(player, 'fame', 0) - 5
                npc.dissatisfaction = min(getattr(npc, 'dissatisfaction', 0) + 10, 100)
                log_game_event(f"玩家向 {npc.name} 索要 {item_key} 被拒绝，声望-5")
                if ft_mgr:
                    ft_mgr.add_text("被拒绝 声望-5", npc.rect.x, npc.rect.y - 60, (255, 120, 80))

        elif action_type == "STEAL_ITEM":
            # 偷窃成功率：基础20% + 敏捷加成(每+1 +4%)
            agility_bonus = (p_agility - 5) * 0.04
            success_rate  = max(0.05, min(0.85, 0.20 + agility_bonus))

            if random.random() < success_rate:
                # ── 成功（不知情，无仇恨惩罚）──
                npc.inventory[item_key] -= 1
                if npc.inventory[item_key] <= 0:
                    del npc.inventory[item_key]
                player.inventory[item_key] = player.inventory.get(item_key, 0) + 1
                log_game_event(f"玩家悄悄偷走了 {npc.name} 的 {item_key}")
                if ft_mgr:
                    ft_mgr.add_text(f"偷窃成功 +{item_key}", npc.rect.x, npc.rect.y - 60, (180, 100, 220))
            else:
                # ── 失败（被发现）──
                player.fame = getattr(player, 'fame', 0) - 15
                # NPC 仇恨值激增，可能追打玩家
                npc.hatred[player.id] = npc.hatred.get(player.id, 0) + 80
                npc.aggro_target = player
                npc.dissatisfaction = min(getattr(npc, 'dissatisfaction', 0) + 20, 100)
                log_game_event(f"玩家偷窃 {npc.name} 被发现！声望-15，对方仇恨激增！")
                if ft_mgr:
                    ft_mgr.add_text("被发现！声望-15", npc.rect.x, npc.rect.y - 60, (255, 50, 50))
                    ft_mgr.add_text("追来了！", player.rect.x, player.rect.y - 40, (255, 80, 80))

    def _handle_persuasion_result(self, ctx, result, method):
        """
        处理检定结果对游戏世界的影响
        
        Args:
            ctx: GameContext
            result: 'CRIT_SUCCESS' | 'SUCCESS' | 'FAILURE' | 'CRIT_FAILURE'
            method: 'persuade' | 'threaten' | 'bribe'
        """
        npc = ctx.active_event_npc
        player = ctx.player
        
        if not npc:
            return
        
        # 根据结果调整好感度
        affinity_change = 0
        
        if result == 'CRIT_SUCCESS':
            affinity_change = 20
            # 大成功：可能触发特殊效果（如愿意提供帮助、透露信息等）
            if method == 'persuade':
                ctx.ft_manager.add_text("心悦诚服！", npc.rect.x, npc.rect.y - 50, (255, 215, 0))
            elif method == 'threaten':
                ctx.ft_manager.add_text("瑟瑟发抖！", npc.rect.x, npc.rect.y - 50, (255, 100, 100))
            elif method == 'bribe':
                ctx.ft_manager.add_text("眉开眼笑！", npc.rect.x, npc.rect.y - 50, (255, 215, 0))
            
        elif result == 'SUCCESS':
            affinity_change = 5 if method == 'persuade' else -5 if method == 'threaten' else 10
            ctx.ft_manager.add_text("成功！", npc.rect.x, npc.rect.y - 50, (100, 255, 100))
            
        elif result == 'FAILURE':
            affinity_change = -5
            ctx.ft_manager.add_text("失败...", npc.rect.x, npc.rect.y - 50, (200, 200, 200))
            
        elif result == 'CRIT_FAILURE':
            affinity_change = -30
            # 大失败：可能导致敌对
            if method == 'persuade':
                ctx.ft_manager.add_text("恼羞成怒！", npc.rect.x, npc.rect.y - 50, (255, 50, 50))
            elif method == 'threaten':
                # 威胁大失败：对方可能反击
                ctx.ft_manager.add_text("激怒了对方！", npc.rect.x, npc.rect.y - 50, (255, 50, 50))
                # 增加仇恨值
                if hasattr(npc, 'hatred'):
                    npc.hatred[player.id] = npc.hatred.get(player.id, 0) + 50
            elif method == 'bribe':
                ctx.ft_manager.add_text("被侮辱了！", npc.rect.x, npc.rect.y - 50, (255, 50, 50))
        
        # 应用好感度变化 - 使用 affinity_to_player
        if affinity_change != 0:
            current_affinity = getattr(npc, 'affinity_to_player', 0)
            npc.affinity_to_player = max(-100, min(100, current_affinity + affinity_change))
            
            # 显示好感度变化
            if affinity_change > 0:
                ctx.ft_manager.add_text(f"好感+{affinity_change}", npc.rect.x + 30, npc.rect.y - 30, (255, 200, 100))
            else:
                ctx.ft_manager.add_text(f"好感{affinity_change}", npc.rect.x + 30, npc.rect.y - 30, (200, 100, 100))
        
        # 检查是否需要更新任务状态
        # 例如：说服恶霸成功 -> 更新任务标记
        if result in ['SUCCESS', 'CRIT_SUCCESS'] and hasattr(ctx, 'quest_manager'):
            npc_tags = getattr(npc, 'tags', [])
            
            # 如果目标是恶霸王老虎
            if 'BULLY' in npc_tags or getattr(npc, 'name', '') == '王老虎':
                # 标记悬赏已取消
                ctx.quest_manager.set_flag('bully_bounty_cancelled', True)
                log_game_event(f"[QUEST] 通过{method}说服了恶霸，悬赏取消")

    # ═══════════════════════════════════════════════════════════════
    # 【物品使用/装备处理】
    # ═══════════════════════════════════════════════════════════════
    
    def _handle_use_food(self, player, item_name, ft_manager):
        """
        处理吃东西：消耗食物，恢复饥饿值
        """
        from src.item_system import ItemManager
        item_sys = ItemManager.get_instance()
        
        if item_name not in player.inventory or player.inventory[item_name] <= 0:
            if ft_manager:
                ft_manager.add_text("没有这个物品", player.rect.centerx, player.rect.top - 40, (255, 100, 100))
            return
        
        # 获取食物恢复值
        hunger_rec = item_sys.get_hunger_recovery(item_name)
        if hunger_rec <= 0:
            if ft_manager:
                ft_manager.add_text("这不是食物", player.rect.centerx, player.rect.top - 40, (255, 100, 100))
            return
        
        # 消耗食物
        player.inventory[item_name] -= 1
        if player.inventory[item_name] <= 0:
            del player.inventory[item_name]
        
        # 恢复饥饿值（hunger越低越饿，所以减少hunger值）
        old_hunger = player.hunger
        player.hunger = max(0, player.hunger - hunger_rec)
        
        log_game_event(f"玩家吃了 {item_name}，饥饿值 {old_hunger} -> {player.hunger}")
        
        if ft_manager:
            ft_manager.add_text(f"吃了{item_name} 饥饿-{hunger_rec}", player.rect.centerx, player.rect.top - 40, (100, 255, 100))
    
    def _handle_equip_item(self, player, item_name, ft_manager):
        """
        处理装备物品：武器/护甲/衣物
        """
        from src.item_system import ItemManager
        item_sys = ItemManager.get_instance()
        
        if item_name not in player.inventory or player.inventory[item_name] <= 0:
            if ft_manager:
                ft_manager.add_text("没有这个物品", player.rect.centerx, player.rect.top - 40, (255, 100, 100))
            return
        
        # 判断装备槽位
        if item_sys.is_weapon(item_name):
            # 卸下旧武器（如果有）
            old_weapon = getattr(player, 'equip_weapon', None)
            if old_weapon:
                player.inventory[old_weapon] = player.inventory.get(old_weapon, 0) + 1
            
            # 装备新武器
            player.equip_weapon = item_name
            player.inventory[item_name] -= 1
            if player.inventory[item_name] <= 0:
                del player.inventory[item_name]
            
            # 更新攻击力加成
            atk_bonus = item_sys.get_atk_bonus(item_name)
            log_game_event(f"玩家装备了武器 {item_name}，攻击+{atk_bonus}")
            
            if ft_manager:
                ft_manager.add_text(f"装备{item_name} 攻击+{atk_bonus}", player.rect.centerx, player.rect.top - 40, (100, 200, 255))
        
        elif item_sys.is_armor(item_name):
            # 卸下旧护甲
            old_armor = getattr(player, 'equip_armor', None)
            if old_armor:
                player.inventory[old_armor] = player.inventory.get(old_armor, 0) + 1
            
            # 装备新护甲
            player.equip_armor = item_name
            player.inventory[item_name] -= 1
            if player.inventory[item_name] <= 0:
                del player.inventory[item_name]
            
            def_bonus = item_sys.get_def_bonus(item_name)
            log_game_event(f"玩家装备了护甲 {item_name}，防御+{def_bonus}")
            
            if ft_manager:
                ft_manager.add_text(f"装备{item_name} 防御+{def_bonus}", player.rect.centerx, player.rect.top - 40, (100, 200, 255))
        
        elif item_sys.is_clothing(item_name):
            # 卸下旧衣物
            old_clothing = getattr(player, 'equip_clothing', None)
            if old_clothing:
                player.inventory[old_clothing] = player.inventory.get(old_clothing, 0) + 1
            
            # 装备新衣物
            player.equip_clothing = item_name
            player.inventory[item_name] -= 1
            if player.inventory[item_name] <= 0:
                del player.inventory[item_name]
            
            warm_val = item_sys.get_warm_val(item_name)
            log_game_event(f"玩家装备了衣物 {item_name}，保暖+{warm_val}")
            
            if ft_manager:
                ft_manager.add_text(f"穿上{item_name} 保暖+{warm_val}", player.rect.centerx, player.rect.top - 40, (100, 200, 255))
        
        else:
            if ft_manager:
                ft_manager.add_text("无法装备此物品", player.rect.centerx, player.rect.top - 40, (255, 100, 100))
    
    def _handle_unequip_item(self, player, item_name, ft_manager):
        """
        处理卸下装备
        """
        from src.item_system import ItemManager
        item_sys = ItemManager.get_instance()
        
        unequipped = False
        
        if item_sys.is_weapon(item_name) and getattr(player, 'equip_weapon', None) == item_name:
            player.equip_weapon = None
            player.inventory[item_name] = player.inventory.get(item_name, 0) + 1
            unequipped = True
            log_game_event(f"玩家卸下了武器 {item_name}")
        
        elif item_sys.is_armor(item_name) and getattr(player, 'equip_armor', None) == item_name:
            player.equip_armor = None
            player.inventory[item_name] = player.inventory.get(item_name, 0) + 1
            unequipped = True
            log_game_event(f"玩家卸下了护甲 {item_name}")
        
        elif item_sys.is_clothing(item_name) and getattr(player, 'equip_clothing', None) == item_name:
            player.equip_clothing = None
            player.inventory[item_name] = player.inventory.get(item_name, 0) + 1
            unequipped = True
            log_game_event(f"玩家卸下了衣物 {item_name}")
        
        if unequipped and ft_manager:
            ft_manager.add_text(f"卸下{item_name}", player.rect.centerx, player.rect.top - 40, (200, 200, 100))

    def _draw_system_menu(self, ctx, mx, my, click_event):
        """
        绘制系统功能折叠菜单
        位于小地图上方，点击主按钮后向上展开二级菜单
        """
        screen = self.screen
        
        # 【UI层级系统】导入命中检测
        from src.ui.hit_test import register_ui_zone, UI_LAYER_PANEL, UI_LAYER_OVERLAY
        
        # 计算小地图位置（与camera.py保持一致）
        mm_x = screen.get_width() - SIDEBAR_W - MINIMAP_W - MINIMAP_MARGIN
        mm_y = screen.get_height() - MINIMAP_H - MINIMAP_MARGIN
        
        # 系统功能主按钮参数
        main_btn_w = MINIMAP_W  # 与小地图同宽
        main_btn_h = 32
        main_btn_x = mm_x
        main_btn_y = mm_y - main_btn_h - 45  # 小地图上方45像素（上移40像素避免与"小地图"标题重叠）
        
        # 二级按钮参数
        sub_btn_w = main_btn_w
        sub_btn_h = 30
        sub_btn_gap = 3
        
        # 定义二级按钮列表 (key, 显示文本, 颜色, 是否可用)
        # 第4个元素为 False 时按钮置灰
        # 【修复】使用纯文本符号替代emoji，避免口字渲染问题
        sub_buttons = [
            ('NEWS', "[实况] 大宋实况", (180, 60, 60), True),
            ('ROSTER', "[名册] 百姓名册", (180, 140, 60), True),
            ('TECH', "[科技] 政策科技", (140, 60, 140), True),
            ('FACTION', "[势力] 势力纵横", (160, 120, 60), True),
            ('QUEST', "[任务] 任务日志", (60, 100, 180), True),
            ('FATE', "[命运] 命运图谱", (180, 100, 180), True),  # 【新增】命运图谱
            ('SKIP_QUEST', "[跳过] 跳过任务(调试)", (100, 180, 100), True),
        ]
        
        # 【调试】触发事件按钮 - 如果正在生成中且未超时则置灰
        director = getattr(ctx, 'director', None)
        event_btn_enabled = True
        event_btn_text = "[事件] 触发事件(调试)"
        if director:
            if director.is_generating():
                if director.is_generation_timeout():
                    event_btn_text = "[事件] 触发事件(超时重试)"
                else:
                    event_btn_enabled = False
                    event_btn_text = "[等待] 事件生成中..."
        
        sub_buttons.append(('TRIGGER_EVENT', event_btn_text, (60, 140, 180), event_btn_enabled))
        sub_buttons.append(('EXIT', "[退出] 退出游戏", (120, 50, 50), True))
        
        # 大地图模式下添加"对准自己"按钮
        if self.camera is not None:
            follow_on = getattr(self.camera, 'follow_player', False)
            focus_col = (60, 150, 80) if follow_on else (70, 90, 130)
            sub_buttons.insert(-1, ('FOCUS', "[定位] 对准自己", focus_col, True))  # 在退出前插入
        
        # 绘制主按钮
        main_btn_rect = pygame.Rect(main_btn_x, main_btn_y, main_btn_w, main_btn_h)
        main_hover = main_btn_rect.collidepoint(mx, my)
        
        # 【UI层级系统】注册主按钮区域
        register_ui_zone(main_btn_rect, UI_LAYER_PANEL, "系统功能主按钮")
        
        # 主按钮颜色：展开时高亮
        if self.system_menu_expanded:
            main_color = (80, 100, 130)
        elif main_hover:
            main_color = (70, 85, 110)
        else:
            main_color = (55, 65, 85)
        
        pygame.draw.rect(screen, main_color, main_btn_rect, border_radius=4)
        pygame.draw.rect(screen, (100, 120, 150), main_btn_rect, 1, border_radius=4)
        
        # 主按钮文字
        arrow = "▼" if self.system_menu_expanded else "▲"
        main_text = f"{arrow} 系统功能"
        main_surf = self.ui_manager.font_ui.render(main_text, True, (230, 230, 240))
        screen.blit(main_surf, (main_btn_rect.centerx - main_surf.get_width() // 2, 
                                main_btn_rect.centery - main_surf.get_height() // 2))
        
        # 主按钮点击：切换展开状态
        if click_event and main_hover:
            self.system_menu_expanded = not self.system_menu_expanded
        
        # 如果展开，绘制二级按钮（向上展开）
        clicked_action = None
        if self.system_menu_expanded:
            # 计算所有二级按钮的总高度
            total_sub_height = len(sub_buttons) * (sub_btn_h + sub_btn_gap)
            
            # 绘制半透明背景面板
            panel_rect = pygame.Rect(
                main_btn_x - 2, 
                main_btn_y - total_sub_height - 8,
                main_btn_w + 4,
                total_sub_height + 8
            )
            
            # 【UI层级系统】注册展开菜单区域（使用OVERLAY层级，优先级更高）
            register_ui_zone(panel_rect, UI_LAYER_OVERLAY, "系统功能展开菜单")
            
            panel_surf = pygame.Surface((panel_rect.w, panel_rect.h), pygame.SRCALPHA)
            panel_surf.fill((30, 35, 45, 220))
            screen.blit(panel_surf, panel_rect.topleft)
            pygame.draw.rect(screen, (80, 90, 110), panel_rect, 1, border_radius=4)
            
            # 从下往上绘制二级按钮
            for i, btn_data in enumerate(sub_buttons):
                key, text, color = btn_data[0], btn_data[1], btn_data[2]
                enabled = btn_data[3] if len(btn_data) > 3 else True
                
                btn_y = main_btn_y - (i + 1) * (sub_btn_h + sub_btn_gap)
                btn_rect = pygame.Rect(main_btn_x, btn_y, sub_btn_w, sub_btn_h)
                
                btn_hover = btn_rect.collidepoint(mx, my)
                
                # 禁用状态：灰色，不响应点击
                if not enabled:
                    btn_color = (80, 80, 90)  # 灰色
                    text_color = (150, 150, 160)  # 暗淡文字
                elif btn_hover:
                    btn_color = tuple(min(255, c + 30) for c in color)
                    text_color = (240, 240, 240)
                else:
                    btn_color = color
                    text_color = (240, 240, 240)
                
                pygame.draw.rect(screen, btn_color, btn_rect, border_radius=4)
                border_col = (100, 100, 110) if not enabled else tuple(min(255, c + 50) for c in color)
                pygame.draw.rect(screen, border_col, btn_rect, 1, border_radius=4)
                
                btn_surf = self.ui_manager.font_ui.render(text, True, text_color)
                screen.blit(btn_surf, (btn_rect.centerx - btn_surf.get_width() // 2,
                                       btn_rect.centery - btn_surf.get_height() // 2))
                
                # 处理点击（仅在启用时响应）
                if click_event and btn_hover and enabled:
                    clicked_action = key
                    self.system_menu_expanded = False  # 点击后收起菜单
        
        # 处理按钮动作
        if clicked_action:
            if clicked_action == 'NEWS':
                # 【修复】使用新版大宋实况面板而非旧版
                if hasattr(ctx, 'live_news_panel'):
                    ctx.live_news_panel.toggle()
                else:
                    # 兜底：旧版
                    ctx.current_state = GAME_STATE_NEWS_FEED
            elif clicked_action == 'ROSTER':
                ctx.current_state = GAME_STATE_ROSTER
            elif clicked_action == 'TECH':
                ctx.current_state = GAME_STATE_TECH_TREE
            elif clicked_action == 'FACTION':
                ctx.current_state = GAME_STATE_FACTION_VIEW
            elif clicked_action == 'QUEST':
                ctx.current_state = GAME_STATE_QUEST_LOG
            elif clicked_action == 'FATE':
                # 【新增】打开命运图谱
                ctx.current_state = GAME_STATE_FATE_GRAPH
                return  # 立即返回，避免同一帧中命运图谱处理点击事件
            elif clicked_action == 'FOCUS':
                if self.camera:
                    self.camera.follow_player = not self.camera.follow_player
            elif clicked_action == 'SKIP_QUEST':
                # 【调试】跳过当前任务对话
                if hasattr(ctx, 'quest_manager') and ctx.quest_manager:
                    success, msg = ctx.quest_manager.skip_current_dialogs(ctx)
                    print(f"[Debug] 跳过任务: {msg}")
                    # 显示浮动提示
                    if hasattr(ctx, 'ft_manager') and ctx.ft_manager and ctx.player:
                        color = (100, 255, 100) if success else (255, 150, 100)
                        ctx.ft_manager.add_text(msg, ctx.player.rect.centerx, ctx.player.rect.top - 50, color)
            elif clicked_action == 'TRIGGER_EVENT':
                # 【调试】强制触发AI事件
                director = getattr(ctx, 'director', None)
                if director:
                    success = director.force_trigger_event(ctx)
                    if success:
                        if hasattr(ctx, 'ft_manager') and ctx.ft_manager and ctx.player:
                            ctx.ft_manager.add_text("[AI] 正在生成AI事件...",
                                ctx.player.rect.centerx, ctx.player.rect.top - 50, (100, 200, 255))
                    else:
                        if hasattr(ctx, 'ft_manager') and ctx.ft_manager and ctx.player:
                            ctx.ft_manager.add_text("⏳ 请等待当前事件生成完成", 
                                ctx.player.rect.centerx, ctx.player.rect.top - 50, (255, 200, 100))
                else:
                    print(f"[Debug] 导演系统未初始化")
            elif clicked_action == 'EXIT':
                # 退出游戏需要特殊处理，设置一个标志让main.py知道
                ctx.request_exit = True
        
        # 点击菜单外部区域时收起菜单
        if click_event and self.system_menu_expanded:
            # 计算整个菜单区域
            total_sub_height = len(sub_buttons) * (sub_btn_h + sub_btn_gap)
            full_menu_rect = pygame.Rect(
                main_btn_x - 5,
                main_btn_y - total_sub_height - 10,
                main_btn_w + 10,
                total_sub_height + main_btn_h + 20
            )
            if not full_menu_rect.collidepoint(mx, my):
                self.system_menu_expanded = False

    def _draw_npc_debug(self, npc, cam=None):
        def w2s_pt(wx, wy):
            if cam:
                return cam.world_to_screen(wx, wy)
            return wx, wy
        if npc.target_x is not None:
            start = w2s_pt(*npc.rect.center)
            end = w2s_pt(int(npc.target_x), int(npc.target_y))
            pygame.draw.line(self.screen, (0, 200, 255), start, end, 1)
            pygame.draw.circle(self.screen, (0, 200, 255), (int(end[0]), int(end[1])), 4)
        if getattr(npc, 'debug_next_waypoint', None):
            wp_s = w2s_pt(*npc.debug_next_waypoint)
            pygame.draw.line(self.screen, (255, 50, 50), w2s_pt(*npc.rect.center), wp_s, 2)
            pygame.draw.circle(self.screen, (255, 50, 50), (int(wp_s[0]), int(wp_s[1])), 3)

    def _draw_player_debug(self, player, cam=None):
        def w2s_pt(wx, wy):
            if cam:
                return cam.world_to_screen(wx, wy)
            return wx, wy
        if player.target_x is not None:
            pygame.draw.line(self.screen, (0, 255, 255),
                             w2s_pt(*player.rect.center),
                             w2s_pt(player.target_x, player.target_y), 2)
            if getattr(player, 'debug_next_waypoint', None):
                wp_s = w2s_pt(*player.debug_next_waypoint)
                pygame.draw.line(self.screen, (255, 0, 255),
                                 w2s_pt(*player.rect.center), wp_s, 3)
                pygame.draw.circle(self.screen, (255, 0, 255),
                                   (int(wp_s[0]), int(wp_s[1])), 8)

    def _draw_action_bubble(self, screen, card, screen_x: float, screen_y: float):
        """
        绘制NPC行为气泡（如挥手、送礼等反馈）
        
        Args:
            screen: pygame屏幕
            card: 卡牌对象
            screen_x, screen_y: 卡牌在屏幕上的坐标
        """
        # 检查是否有气泡要显示
        bubble_text = getattr(card, '_salute_bubble', None)
        bubble_timer = getattr(card, '_salute_bubble_timer', 0)
        
        if not bubble_text or bubble_timer <= 0:
            return
        
        # 获取字体
        font = getattr(self.ui_manager, 'font_sys', None)
        if not font:
            return
        
        # === 根据气泡内容选择样式 ===
        # 好感类：红色爱心背景
        # 愤怒类：红色背景
        # 物品类：金色背景
        # 普通类：白色背景
        
        if '[爱]' in bubble_text or '[爱爱]' in bubble_text or '[爱爱爱]' in bubble_text:
            bg_color = (255, 200, 200, 230)  # 粉色
            text_color = (200, 50, 80)
            border_color = (220, 100, 120)
        elif '[怒]' in bubble_text:
            bg_color = (255, 180, 180, 230)  # 浅红
            text_color = (180, 50, 50)
            border_color = (200, 80, 80)
        elif '送你' in bubble_text or '文' in bubble_text:
            bg_color = (255, 240, 200, 230)  # 金色
            text_color = (120, 80, 20)
            border_color = (200, 160, 80)
        elif '找死' in bubble_text or '小心' in bubble_text or '来人' in bubble_text:
            bg_color = (255, 150, 150, 230)  # 红色
            text_color = (150, 30, 30)
            border_color = (200, 60, 60)
        else:
            bg_color = (255, 255, 255, 230)  # 白色
            text_color = (50, 50, 50)
            border_color = (150, 150, 150)
        
        # === 计算气泡位置和大小 ===
        padding = 8
        text_surf = font.render(bubble_text, True, text_color)
        bubble_w = text_surf.get_width() + padding * 2
        bubble_h = text_surf.get_height() + padding * 2
        
        # 气泡在卡牌上方居中
        card_center_x = screen_x + card.rect.width // 2
        bubble_x = card_center_x - bubble_w // 2
        bubble_y = screen_y - bubble_h - 10  # 在卡牌上方10像素
        
        # === 根据剩余时间计算透明度（淡出效果）===
        if bubble_timer < 500:
            alpha = int(255 * (bubble_timer / 500))
            bg_color = (*bg_color[:3], min(bg_color[3], alpha))
        
        # === 绘制气泡 ===
        bubble_surf = pygame.Surface((bubble_w, bubble_h), pygame.SRCALPHA)
        pygame.draw.rect(bubble_surf, bg_color, (0, 0, bubble_w, bubble_h), border_radius=6)
        pygame.draw.rect(bubble_surf, border_color, (0, 0, bubble_w, bubble_h), 2, border_radius=6)
        
        # 绘制小三角指向卡牌
        tri_w = 8
        tri_h = 6
        tri_points = [
            (bubble_w // 2 - tri_w // 2, bubble_h),
            (bubble_w // 2 + tri_w // 2, bubble_h),
            (bubble_w // 2, bubble_h + tri_h)
        ]
        pygame.draw.polygon(bubble_surf, bg_color[:3], tri_points)
        pygame.draw.line(bubble_surf, border_color, tri_points[0], tri_points[2], 2)
        pygame.draw.line(bubble_surf, border_color, tri_points[1], tri_points[2], 2)
        
        screen.blit(bubble_surf, (int(bubble_x), int(bubble_y)))
        
        # 绘制文字
        screen.blit(text_surf, (int(bubble_x + padding), int(bubble_y + padding)))
    
    def _draw_quest_marker(self, screen, context, cam):
        """
        绘制任务目标指引标记
        - 如果目标在屏幕内：显示黄色菱形标记
        - 如果目标在屏幕外：在屏幕边缘显示方向箭头
        
        不显示指引的情况：
        1. 玩家自己身上有任务指引（目标是玩家自己）
        2. 玩家正在剧情对话中
        """
        import math
        
        # ── 检查是否在剧情对话中 ──
        story_ui = getattr(context, 'story_ui', None)
        if story_ui and getattr(story_ui, 'is_active', False):
            return  # 剧情中不显示任务指引
        
        quest_mgr = getattr(context, 'quest_manager', None)
        if not quest_mgr:
            return
        
        # 获取当前任务目标位置和类型
        target_info = self._get_quest_target_position(context, quest_mgr)
        if not target_info:
            return
        
        # 解包目标信息
        if isinstance(target_info, tuple) and len(target_info) == 2:
            # 旧格式兼容：只有坐标
            target_pos = target_info
            target_type = 'coordinate'
            target_entity = None
        elif isinstance(target_info, dict):
            target_pos = target_info.get('position')
            target_type = target_info.get('type', 'coordinate')
            target_entity = target_info.get('entity')
        else:
            return
        
        if not target_pos:
            return
        
        # ── 检查目标是否是玩家自己 ──
        player = getattr(context, 'player', None)
        if player and target_entity:
            # 如果目标实体就是玩家，不显示指引
            if target_entity is player:
                return
            if hasattr(target_entity, 'job') and target_entity.job == 'PLAYER':
                return
            if hasattr(target_entity, 'is_player') and target_entity.is_player:
                return
        
        world_x, world_y = target_pos
        
        # 转换为屏幕坐标
        if cam is not None:
            screen_x, screen_y = cam.world_to_screen(world_x, world_y)
        else:
            screen_x, screen_y = world_x, world_y
        
        # 获取可绘制区域（排除侧边栏和顶部栏）
        drawable_left = 0
        drawable_top = TOPBAR_H
        drawable_right = screen.get_width() - SIDEBAR_W
        drawable_bottom = screen.get_height()
        
        # 检查目标是否在屏幕可见区域内
        margin = 50  # 边缘距离
        in_screen = (drawable_left + margin < screen_x < drawable_right - margin and
                     drawable_top + margin < screen_y < drawable_bottom - margin)
        
        if in_screen:
            # 目标在屏幕内：绘制黄色菱形标记（脉冲动画）
            self._draw_diamond_marker(screen, int(screen_x), int(screen_y))
        else:
            # 目标在屏幕外：绘制边缘箭头
            self._draw_edge_arrow(screen, screen_x, screen_y, 
                                  drawable_left, drawable_top, drawable_right, drawable_bottom)
    
    def _get_quest_target_position(self, context, quest_mgr):
        """
        根据当前任务类型获取目标位置
        返回: dict {
            'position': (world_x, world_y),
            'type': 'npc' | 'building' | 'coordinate',
            'entity': card实体或None
        } 或 None
        """
        q = quest_mgr.get_current_quest()
        if not q:
            return None
        
        all_cards = context.all_cards
        player = getattr(context, 'player', None)
        
        # 辅助函数：创建返回字典
        def make_result(pos, result_type, entity=None):
            return {
                'position': pos,
                'type': result_type,
                'entity': entity
            }
        
        # 辅助函数：查找最近的Building
        def find_nearest_building(building_type):
            """查找距离玩家最近的指定类型建筑"""
            from src.entities import Building
            nearest = None
            min_dist = float('inf')
            px, py = player.rect.centerx, player.rect.centery if player else (0, 0)
            
            for card in all_cards:
                if isinstance(card, Building):
                    # 检查建筑类型匹配
                    card_type = getattr(card, 'building_type', None) or getattr(card, 'name', '')
                    if building_type.lower() in card_type.lower() or card_type.lower() in building_type.lower():
                        dist = ((card.rect.centerx - px) ** 2 + (card.rect.centery - py) ** 2) ** 0.5
                        if dist < min_dist:
                            min_dist = dist
                            nearest = card
            return nearest
        
        # 根据任务状态确定目标
        if quest_mgr.quest_status == QS_AVAILABLE or quest_mgr.quest_status == QS_READY:
            # 需要找提交NPC
            submit_npc = q.submit_npc
            if submit_npc == '9999':
                # 自动完成任务，不需要指引
                return None
            
            # 查找提交NPC
            for card in all_cards:
                if hasattr(card, 'id') and str(card.id) == str(submit_npc):
                    return make_result((card.rect.centerx, card.rect.centery), 'npc', card)
                if hasattr(card, 'name') and card.name == submit_npc:
                    return make_result((card.rect.centerx, card.rect.centery), 'npc', card)
        
        elif quest_mgr.quest_status == QS_ACTIVE:
            # 任务进行中，根据任务类型确定目标
            if q.type == 'REACH':
                # REACH任务：目标是指定区域/坐标
                reach_pos = self._get_reach_target_position(q.target)
                if reach_pos:
                    return make_result(reach_pos, 'coordinate', None)
            
            elif q.type == 'INTERACT':
                # 交互任务：目标是指定NPC
                for card in all_cards:
                    if hasattr(card, 'name') and card.name == q.target:
                        return make_result((card.rect.centerx, card.rect.centery), 'npc', card)
            
            elif q.type == 'GATHER':
                # 采集任务：从配方系统获取资源对应的建筑类型
                from src.recipe_system import get_resource_building_map
                resource_building_map = get_resource_building_map()
                
                # 获取可以产出该资源的建筑类型列表
                building_types = resource_building_map.get(q.target, [])
                nearest_building = None
                for bt in building_types:
                    nearest_building = find_nearest_building(bt)
                    if nearest_building:
                        break
                
                if nearest_building:
                    return make_result(
                        (nearest_building.rect.centerx, nearest_building.rect.centery),
                        'building',
                        nearest_building
                    )
                
                # 兜底：使用 world_map 的固定区域（如果配方表没有该资源）
                resource_locations = {
                    '生鱼': self.world_map.fish_rect.center if hasattr(self.world_map, 'fish_rect') else None,
                    '木材': self.world_map.forest_rect.center if hasattr(self.world_map, 'forest_rect') else None,
                    '浆果': self.world_map.farm_rect.center if hasattr(self.world_map, 'farm_rect') else None,
                }
                pos = resource_locations.get(q.target)
                if pos:
                    return make_result(pos, 'coordinate', None)
            
            elif q.type == 'DELIVER':
                # 交付任务：目标是提交NPC
                submit_npc = q.submit_npc
                for card in all_cards:
                    if hasattr(card, 'id') and str(card.id) == str(submit_npc):
                        return make_result((card.rect.centerx, card.rect.centery), 'npc', card)
                    if hasattr(card, 'name') and card.name == submit_npc:
                        return make_result((card.rect.centerx, card.rect.centery), 'npc', card)
            
            elif q.type == 'COMBAT':
                # 战斗任务：目标是敌人
                for card in all_cards:
                    if hasattr(card, 'name') and card.name == q.target:
                        return make_result((card.rect.centerx, card.rect.centery), 'npc', card)
            
            elif q.type in ['DIALOG', 'RECRUIT']:
                # 对话/招募任务：目标是相关NPC
                submit_npc = q.submit_npc
                for card in all_cards:
                    if hasattr(card, 'id') and str(card.id) == str(submit_npc):
                        return make_result((card.rect.centerx, card.rect.centery), 'npc', card)
                    if hasattr(card, 'name') and card.name == submit_npc:
                        return make_result((card.rect.centerx, card.rect.centery), 'npc', card)
            
            elif q.type == 'GOTO_BUILDING':
                # 前往建筑任务：查找最近的指定类型建筑
                nearest_building = find_nearest_building(q.target)
                if nearest_building:
                    return make_result(
                        (nearest_building.rect.centerx, nearest_building.rect.centery),
                        'building',
                        nearest_building
                    )
        
        return None
    
    def _get_reach_target_position(self, target):
        """
        解析REACH任务的目标位置
        """
        # 预定义区域点（与quest_system.py保持一致）
        REACH_POINTS = {
            'AMBUSH_POINT': (2200, 2100),
            'RIVER_BANK': (3000, 2500),
            'HUNTER_CABIN': (500, 500),
            'MARKET_CENTER': (1700, 1400),
        }
        
        if target in REACH_POINTS:
            return REACH_POINTS[target]
        
        # 尝试解析坐标格式 "x,y"
        if ',' in str(target):
            try:
                parts = str(target).split(',')
                return (int(parts[0]), int(parts[1]))
            except:
                pass
        
        return None
    
    def _draw_diamond_marker(self, screen, x, y):
        """
        在指定位置绘制黄色菱形标记（带脉冲动画）
        """
        import time
        
        # 脉冲动画：大小随时间变化
        pulse = abs(math.sin(time.time() * 3)) * 0.3 + 0.7  # 0.7 ~ 1.0
        size = int(20 * pulse)
        
        # 绘制菱形
        points = [
            (x, y - size),      # 上
            (x + size, y),      # 右
            (x, y + size),      # 下
            (x - size, y),      # 左
        ]
        
        # 填充半透明黄色
        diamond_surf = pygame.Surface((size * 2 + 4, size * 2 + 4), pygame.SRCALPHA)
        local_points = [
            (size + 2, 2),
            (size * 2 + 2, size + 2),
            (size + 2, size * 2 + 2),
            (2, size + 2),
        ]
        pygame.draw.polygon(diamond_surf, (255, 230, 80, 150), local_points)
        pygame.draw.polygon(diamond_surf, (255, 215, 0), local_points, 2)
        screen.blit(diamond_surf, (x - size - 2, y - size - 2))
        
        # 绘制中心感叹号
        font_marker = pygame.font.Font(None, int(24 * pulse))
        marker_text = font_marker.render("!", True, (200, 50, 50))
        screen.blit(marker_text, (x - marker_text.get_width() // 2, y - marker_text.get_height() // 2))
    
    def _draw_edge_arrow(self, screen, target_x, target_y, 
                          left, top, right, bottom):
        """
        在屏幕边缘绘制指向屏幕外目标的箭头
        """
        import math
        
        # 屏幕中心
        center_x = (left + right) / 2
        center_y = (top + bottom) / 2
        
        # 计算从中心到目标的方向
        dx = target_x - center_x
        dy = target_y - center_y
        
        if dx == 0 and dy == 0:
            return
        
        angle = math.atan2(dy, dx)
        
        # 计算箭头在边缘的位置
        # 找到射线与边界的交点
        arrow_x, arrow_y = self._find_edge_intersection(
            center_x, center_y, angle, left, top, right, bottom
        )
        
        # 绘制箭头
        arrow_size = 20
        
        # 箭头三角形顶点
        tip_x = arrow_x + math.cos(angle) * 10
        tip_y = arrow_y + math.sin(angle) * 10
        
        # 箭头两翼
        wing_angle = 2.5  # 约145度
        wing1_x = arrow_x - math.cos(angle - wing_angle) * arrow_size
        wing1_y = arrow_y - math.sin(angle - wing_angle) * arrow_size
        wing2_x = arrow_x - math.cos(angle + wing_angle) * arrow_size
        wing2_y = arrow_y - math.sin(angle + wing_angle) * arrow_size
        
        arrow_points = [
            (int(tip_x), int(tip_y)),
            (int(wing1_x), int(wing1_y)),
            (int(wing2_x), int(wing2_y)),
        ]
        
        # 绘制箭头（黄色填充 + 深色边框）
        pygame.draw.polygon(screen, (255, 230, 80), arrow_points)
        pygame.draw.polygon(screen, (180, 150, 30), arrow_points, 2)
        
        # 可选：显示距离
        dist = math.hypot(dx, dy)
        if dist > 200:
            dist_text = f"{int(dist)}px"
            font_small = pygame.font.Font(None, 18)
            dist_surf = font_small.render(dist_text, True, (255, 230, 150))
            # 距离文字位置：箭头内侧
            text_x = arrow_x - math.cos(angle) * 30
            text_y = arrow_y - math.sin(angle) * 30
            screen.blit(dist_surf, (int(text_x - dist_surf.get_width() // 2), 
                                    int(text_y - dist_surf.get_height() // 2)))
    
    def _find_edge_intersection(self, cx, cy, angle, left, top, right, bottom):
        """
        找到从中心点沿指定角度的射线与边界的交点
        """
        import math
        
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        # 防止除零
        if abs(cos_a) < 0.0001:
            cos_a = 0.0001
        if abs(sin_a) < 0.0001:
            sin_a = 0.0001
        
        # 计算到各边界的距离
        candidates = []
        
        # 右边界
        if cos_a > 0:
            t = (right - 20 - cx) / cos_a
            y = cy + t * sin_a
            if top <= y <= bottom:
                candidates.append((right - 20, y, t))
        
        # 左边界
        if cos_a < 0:
            t = (left + 20 - cx) / cos_a
            y = cy + t * sin_a
            if top <= y <= bottom:
                candidates.append((left + 20, y, t))
        
        # 下边界
        if sin_a > 0:
            t = (bottom - 20 - cy) / sin_a
            x = cx + t * cos_a
            if left <= x <= right:
                candidates.append((x, bottom - 20, t))
        
        # 上边界
        if sin_a < 0:
            t = (top + 20 - cy) / sin_a
            x = cx + t * cos_a
            if left <= x <= right:
                candidates.append((x, top + 20, t))
        
        # 选择最近的交点
        if candidates:
            candidates.sort(key=lambda p: p[2])
            return candidates[0][0], candidates[0][1]
        
        # 默认返回中心
        return cx, cy
