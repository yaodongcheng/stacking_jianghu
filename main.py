# --- main.py ---
import pygame
import sys
import random
import csv
import math
import time
from src.definitions import * 
import src.definitions as defs
from src.entities import Player, NPC, Building, Resource
from src.event_system import EventManager
from src.tech_system import TechManager
from src.ui import UIManager
from src.utils import FloatingTextManager, log_game_event, wrap_text
from src.world_map import WorldMap
from src.interaction import InteractionManager
from src.recipe_system import RecipeManager  
from src.combat_system import CombatManager 
from src.pathfinding import FloydPathfinder  
from src.ai_system import AISystem 
from src.social_system import social_manager
from src.economy_system import EconomySystem 
from src.quest_system import QuestManager
from src.ui.story_ui import StoryUI
from src.data_loader import load_raw_npc_data, load_npcs_from_csv
from src.ui.creation import CharacterCreationUI
from src.render_system import RenderSystem
from src.context import GameContext, ctx

from src.movement_system import MovementSystem
from src.world_loader import WorldLoader
from src.item_system import ItemManager
from src.ui.main_menu import MainMenuUI
from src.data.building_defs import BUILDING_DB
from src.camera import Camera

# 【新增】性能监控器
from tools.perf_profiler import get_perf_monitor
####姚东成测试111
# 【新增】大宋实况系统
from src.live_news_system import get_live_news_manager
from src.director_system import get_director
# NewsNotificationBar 已移除，统一使用 EventNotificationManager
   
# --- 全局配置 ---
# 各剧本对应的世界尺寸（单位：像素）
# 值为 None 表示退化为单屏模式，不启用摄像机
SCENARIO_WORLD_SIZES = {
    SCENARIO_TUTORIAL: None,            # 小村教程：全屏单屏，不需要摄像机
    SCENARIO_SANDBOX:  (4800, 3600),    # 闯荡汴京：城内不变，上下野外扩大（从2700→3600）
    # 未来剧本在此扩展 ...
}


def _preregister_system_menu_zones(screen_w: int, screen_h: int, menu_expanded: bool):
    """
    【UI层级系统修复】预先注册系统功能菜单的UI区域
    
    这个函数必须在事件处理循环之前调用，否则点击系统功能按钮时
    UI区域还未注册，会导致 is_ui_blocking() 返回 False，
    从而触发玩家移动（点击穿透问题）。
    
    参数:
        screen_w: 屏幕宽度
        screen_h: 屏幕高度
        menu_expanded: 菜单是否展开
    """
    from src.ui.hit_test import register_ui_zone, UI_LAYER_PANEL, UI_LAYER_OVERLAY
    
    # 计算小地图位置（与render_system._draw_system_menu保持一致）
    mm_x = screen_w - SIDEBAR_W - MINIMAP_W - MINIMAP_MARGIN
    mm_y = screen_h - MINIMAP_H - MINIMAP_MARGIN
    
    # 系统功能主按钮参数
    main_btn_w = MINIMAP_W
    main_btn_h = 32
    main_btn_x = mm_x
    main_btn_y = mm_y - main_btn_h - 45
    
    # 注册主按钮区域
    main_btn_rect = pygame.Rect(main_btn_x, main_btn_y, main_btn_w, main_btn_h)
    register_ui_zone(main_btn_rect, UI_LAYER_PANEL, "系统功能主按钮")
    
    # 如果菜单展开，注册展开区域
    if menu_expanded:
        # 二级按钮参数（与render_system保持一致）
        sub_btn_h = 30
        sub_btn_gap = 3
        # 最多9个按钮（包括对准自己按钮）
        num_buttons = 9
        total_sub_height = num_buttons * (sub_btn_h + sub_btn_gap)
        
        panel_rect = pygame.Rect(
            main_btn_x - 2,
            main_btn_y - total_sub_height - 8,
            main_btn_w + 4,
            total_sub_height + 8
        )
        register_ui_zone(panel_rect, UI_LAYER_OVERLAY, "系统功能展开菜单")

def init_game_systems(screen_w, screen_h, scenario_type='village'):
    """初始化所有子系统并打包到 Context"""
    # 重新初始化全局ctx（清除之前的状态）
    ctx.__init__()
    ctx.screen_w, ctx.screen_h = screen_w, screen_h
    ctx.scenario_type = scenario_type

    ctx.ui_manager = UIManager(screen_w, screen_h, ctx)
    ctx.ft_manager = FloatingTextManager()
    ctx.interaction_mgr = InteractionManager()

    # 按剧本选择世界尺寸
    world_size = SCENARIO_WORLD_SIZES.get(scenario_type, None)
    if world_size:
        world_w, world_h = world_size
        ctx.world_map = WorldMap(screen_w, screen_h, world_w=world_w, world_h=world_h)
    else:
        ctx.world_map = WorldMap(screen_w, screen_h)
    
    # 【边界保护】将世界尺寸注入到 CardBase，供 set_pos 边界检查使用
    from src.entities.base import CardBase
    CardBase._world_width = ctx.world_map.w
    CardBase._world_height = ctx.world_map.h
    
    pathfinder = FloydPathfinder(ctx.world_map) 
    ctx.world_map.pathfinder = pathfinder
    
    npc_raw_data = load_raw_npc_data("data/npc_data.csv")
    ctx.event_manager = EventManager("data/event_data.csv", npc_raw_data)
    ctx.tech_manager = TechManager()
    ctx.recipe_manager = RecipeManager()
    ctx.economy_system = EconomySystem(ctx.ft_manager)
    ctx.quest_manager = QuestManager()
    ctx.event_manager.quest_flags = ctx.quest_manager.flags
    ctx.story_ui = StoryUI(screen_w, screen_h)
    
    ctx.combat_manager = CombatManager(ctx.ft_manager)
    ctx.ai_system = AISystem(ctx.combat_manager)
    ctx.combat_manager.set_ai_system(ctx.ai_system)   # 互相注入，让战斗广播能触发旁观
    ctx.movement_system = MovementSystem()
    ItemManager.get_instance()
    return ctx, npc_raw_data


def main():
    pygame.init()   
    info = pygame.display.Info()
    SCREEN_W, SCREEN_H = info.current_w, info.current_h - 50 # 留一点底边给任务栏
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE) # 允许调整大小
    pygame.display.set_caption("堆叠江湖")
    clock = pygame.time.Clock()
    

    main_menu = MainMenuUI(SCREEN_W, SCREEN_H)
    scenario_type = main_menu.run(screen, clock)
    if not scenario_type: # 如果关闭窗口或返回 None
        pygame.quit()
        sys.exit()
    log_game_event(f"=== 玩家选择了剧本: {scenario_type} ===")

    # --- 1. 初始化各子系统 ---
    
    creation_ui = CharacterCreationUI(SCREEN_W, SCREEN_H)
    create_res = creation_ui.run(screen, clock)

    ctx, npc_raw = init_game_systems(SCREEN_W, SCREEN_H, scenario_type)
    # 3. 实体生成
    ctx.all_cards = WorldLoader.init_world_entities(ctx, create_res, npc_raw, scenario_type)
    
    # 3.5 【阶段3】初始化组织经济系统
    from src.organization_system import get_org_economy
    org_economy = get_org_economy()
    org_economy.initialize_from_npcs(ctx.all_cards)
    ctx.org_economy = org_economy  # 存入上下文供其他系统访问
    
    # 3.6 【阶段4】初始化势力战争系统
    from src.faction_war_system import get_faction_war_system
    faction_war = get_faction_war_system()
    # 从建筑初始化控制点
    all_buildings = [c for c in ctx.all_cards if hasattr(c, 'building_type')]
    faction_war.initialize_control_points(all_buildings)
    faction_war.initialize_relations()
    # 【新增】根据NPC初始位置分配控制点，确保开局就有势力分布
    faction_war.initialize_control_with_npcs(ctx.all_cards)
    ctx.faction_war = faction_war  # 存入上下文
    
    # 3.7 【新增】绑定招募系统依赖
    from src.persuasion_system import recruitment_system
    recruitment_system.bind_systems(
        faction_war_sys=faction_war,
        quest_mgr=ctx.quest_manager
    )
    
    # 3.8 【新增】将势力战争系统注入AI系统（用于悬赏猎人逻辑）
    ctx.ai_system._faction_war_ref = faction_war
    
    # 4. 渲染器初始化
    renderer = RenderSystem(screen, ctx.ui_manager, ctx.world_map, ctx.ft_manager)

    # 5. 摄像机（仅大地图剧本启用）
    world_size = SCENARIO_WORLD_SIZES.get(scenario_type, None)
    if world_size:
        camera = Camera(
            screen_w=SCREEN_W, screen_h=SCREEN_H,
            world_w=world_size[0], world_h=world_size[1]
        )
        # 开局立刻将视口中心对准玩家，避免玩家出现在屏幕外
        camera.snap_to(ctx.player.rect.centerx, ctx.player.rect.centery)
        renderer.camera = camera
    else:
        camera = None

    log_game_event(f"=== 游戏启动 === 初始人口: {len(ctx.all_cards)}")
    
    # 【新增】用于追踪剧情状态变化，检测剧情结束时释放事件NPC
    _prev_story_blocking = False
    
    # 【新增】沙盒模式开场镜头聚焦到事件中心
    if camera and hasattr(ctx, 'event_focus_point') and ctx.event_focus_point:
        event_x, event_y = ctx.event_focus_point
        camera.start_event_focus(event_x, event_y, duration=60)
    
    # 【新增】为气泡式对话设置摄像机引用
    ctx.story_ui.set_references(camera=camera, all_cards=ctx.all_cards)
    
    # 【新增】初始化AI聊天系统
    from src.ui.chat_ui import ChatUI
    from src.llm import get_chat_integration
    ctx.chat_ui = ChatUI(SCREEN_W, SCREEN_H)
    chat_integration = get_chat_integration()
    chat_integration.setup(ctx.chat_ui, player_id=ctx.player.id if hasattr(ctx.player, 'id') else 0)
    ctx.chat_integration = chat_integration

    # ══════════════════════════════════════════════════════════════════════
    # 【大宋实况】统一事件系统初始化
    # ══════════════════════════════════════════════════════════════════════
    from src.ui.event_notification import get_notification_manager
    
    # 初始化统一事件管理器（整合了原LiveNewsManager）
    ctx.event_notification = get_notification_manager(SCREEN_W, SCREEN_H)
    ctx.live_news_manager = ctx.event_notification  # 兼容别名
    
    # 事件生成器和导演系统
    ctx.director = get_director()
    
    # 初始化实况快照面板
    from src.ui.live_snapshot_panel import get_snapshot_panel, LiveSnapshotData
    ctx.snapshot_panel = get_snapshot_panel(SCREEN_W, SCREEN_H)
    
    # 【大宋实况】新闻历史面板
    from src.ui.live_news_panel import get_live_news_panel
    ctx.live_news_panel = get_live_news_panel(SCREEN_W, SCREEN_H)
    
    # 设置历史面板点击事件回调
    def on_history_item_click(item):
        """点击历史面板中的事件条目"""
        # 如果没有 snapshot_data，尝试从 item 属性动态构建
        snapshot_data = item.snapshot_data
        if not snapshot_data:
            print(f"[大宋实况] 事件 {item.title} 缺少 snapshot_data，尝试动态构建...")
            from src.ui.live_snapshot_panel import LiveSnapshotData
            snapshot_data = LiveSnapshotData(
                title=item.title or "未知事件",
                description=item.description or "",
                image_url=getattr(item, '_image_path', None) or "placeholder",
                heat_score=item.heat_score if hasattr(item, 'heat_score') else 0,
                tags=item.tags if hasattr(item, 'tags') else [],
                comments=item.comments if hasattr(item, 'comments') else [],
                choices=item.choices if hasattr(item, 'choices') else [],
                actor_names=item.actor_names if hasattr(item, 'actor_names') else [],
                news_item=item
            )
            # 缓存以便下次使用
            item.snapshot_data = snapshot_data
        
        ctx.snapshot_panel.show(snapshot_data)
        ctx.current_state = GAME_STATE_LIVE_SNAPSHOT
        ctx.live_news_panel.hide()  # 关闭历史面板
        log_game_event(f"[大宋实况] 从历史查看事件: {item.title[:20]}...", tag="LIVE")
    
    ctx.live_news_panel.on_item_click = on_history_item_click
    
    ctx.mode_selector = None  # 保留属性以兼容旧代码
    
    # ═══════════════════════════════════════════════════════════════
    # 【调试日志】玩家点击时打印大宋实况具体内容的函数
    # 【重要】必须定义在 on_notification_click 之前，否则会 NameError
    # ═══════════════════════════════════════════════════════════════
    def _log_snapshot_detail(snapshot_data, source: str = ""):
        """打印大宋实况面板的具体内容（调试用）"""
        if not snapshot_data:
            print(f"[大宋实况] _log_snapshot_detail 收到空数据！来源: {source}")
            return
        
        print(f"\n{'═'*70}")
        print(f"[大宋实况] ╔═════════════════════════════════════════════════════════════════╗")
        print(f"[大宋实况] ║          【玩家点击·事件详情】来源: {source:20}   ║")
        print(f"[大宋实况] ╚═════════════════════════════════════════════════════════════════╝")
        
        # 标题
        title = getattr(snapshot_data, 'title', '无标题')
        subtitle = getattr(snapshot_data, 'subtitle', '')
        print(f"[大宋实况] ┌─────────────────────────────────────────────────────────────────┐")
        print(f"[大宋实况] │ 📰 标题: {title[:50]:50} │")
        if subtitle:
            print(f"[大宋实况] │ 📝 副标: {subtitle[:50]:50} │")
        print(f"[大宋实况] └─────────────────────────────────────────────────────────────────┘")
        
        # 热度和标签
        heat_score = getattr(snapshot_data, 'heat_score', 0)
        tags = getattr(snapshot_data, 'tags', [])
        print(f"[大宋实况] ┌─────────────────────────────────────────────────────────────────┐")
        print(f"[大宋实况] │ 🔥 热度: {heat_score:,}                                          │")
        if tags:
            tags_str = " ".join([f"#{t}" for t in tags[:5]])
            print(f"[大宋实况] │ 🏷️  标签: {tags_str[:50]:50} │")
        print(f"[大宋实况] └─────────────────────────────────────────────────────────────────┘")
        
        # 演员
        actor_names = getattr(snapshot_data, 'actor_names', [])
        if actor_names:
            print(f"[大宋实况] ┌─────────────────────────────────────────────────────────────────┐")
            print(f"[大宋实况] │ 👥 参演人物: {', '.join(actor_names[:5]):48} │")
            print(f"[大宋实况] └─────────────────────────────────────────────────────────────────┘")
        
        # 图片状态
        image_url = getattr(snapshot_data, 'image_url', None)
        print(f"[大宋实况] ┌─────────────────────────────────────────────────────────────────┐")
        if image_url == "loading":
            print(f"[大宋实况] │ 🎨 配图状态: 生成中...                                          │")
        elif image_url == "placeholder":
            print(f"[大宋实况] │ 🎨 配图状态: 占位图（生成失败）                                  │")
        elif image_url:
            print(f"[大宋实况] │ 🎨 配图状态: 已就绪                                             │")
            print(f"[大宋实况] │    路径: {str(image_url)[:55]:55} │")
        else:
            print(f"[大宋实况] │ 🎨 配图状态: 无                                                 │")
        print(f"[大宋实况] └─────────────────────────────────────────────────────────────────┘")
        
        # 玩家选项
        choices = getattr(snapshot_data, 'choices', [])
        if choices:
            print(f"[大宋实况] ┌─────────────────────────────────────────────────────────────────┐")
            print(f"[大宋实况] │ 🎮 玩家选项:                                                    │")
            for i, choice in enumerate(choices, 1):
                if isinstance(choice, dict):
                    text = choice.get('text', f'选项{i}')
                    effect = choice.get('effect', '')
                else:
                    text = str(choice)
                    effect = ''
                print(f"[大宋实况] │   [{i}] {text[:35]:35} → {effect[:18]:18} │")
            print(f"[大宋实况] └─────────────────────────────────────────────────────────────────┘")
        
        # 评论
        comments = getattr(snapshot_data, 'comments', [])
        if comments:
            print(f"[大宋实况] ┌─────────────────────────────────────────────────────────────────┐")
            print(f"[大宋实况] │ 💬 模拟评论 ({len(comments)}条):                                │")
            for comment in comments[:4]:
                if isinstance(comment, dict):
                    user = comment.get('user', '匿名')[:8]
                    text = comment.get('text', '')[:30]
                    ctype = comment.get('type', '中立')
                    print(f"[大宋实况] │   @{user:8}: {text:30} [{ctype}] │")
            print(f"[大宋实况] └─────────────────────────────────────────────────────────────────┘")
        
        # 关联的news_item信息
        news_item = getattr(snapshot_data, 'news_item', None)
        if news_item:
            print(f"[大宋实况] ┌─────────────────────────────────────────────────────────────────┐")
            print(f"[大宋实况] │ 📋 关联新闻条目:                                                │")
            news_id = str(getattr(news_item, 'news_id', '?'))[:30]
            headline = getattr(news_item, 'headline', '')[:50]
            print(f"[大宋实况] │    ID: {news_id:30}                      │")
            print(f"[大宋实况] │    标题: {headline:50} │")
            print(f"[大宋实况] └─────────────────────────────────────────────────────────────────┘")
        
        print(f"{'═'*70}\n")
    
    # 设置通知点击回调：点击后直接显示事件面板
    def on_notification_click(notification):
        """玩家点击右侧通知卡片 → 直接显示事件面板"""
        # 动态构建 snapshot_data（与历史面板使用相同逻辑）
        snapshot_data = notification.snapshot_data
        if not snapshot_data:
            from src.ui.live_snapshot_panel import LiveSnapshotData
            snapshot_data = LiveSnapshotData(
                title=notification.title or "未知事件",
                description=notification.description or "",
                image_url=getattr(notification, '_image_path', None) or "placeholder",
                heat_score=notification.heat_score if hasattr(notification, 'heat_score') else 0,
                tags=notification.tags if hasattr(notification, 'tags') else [],
                comments=notification.comments if hasattr(notification, 'comments') else [],
                choices=notification.choices if hasattr(notification, 'choices') else [],
                actor_names=notification.actor_names if hasattr(notification, 'actor_names') else [],
                news_item=notification
            )
            notification.snapshot_data = snapshot_data
            log_game_event(f"[大宋实况] 动态构建 snapshot_data: {notification.title[:20]}...", tag="LIVE")
        
        # 直接展示事件面板，无需模式选择
        ctx.snapshot_panel.show(snapshot_data)
        ctx.current_state = GAME_STATE_LIVE_SNAPSHOT
        log_game_event(f"[大宋实况] 玩家点击事件: {notification.title[:20]}...", tag="LIVE")
        
        # ═══════════════════════════════════════════════════════════════
        # 【调试日志】打印大宋实况具体内容
        # ═══════════════════════════════════════════════════════════════
        _log_snapshot_detail(snapshot_data, "右侧通知点击")
    
    ctx.event_notification.on_notification_click = on_notification_click
    
    # 设置快照面板的选项回调
    def on_snapshot_choice(choice_idx: int, choice_data: dict):
        """玩家在快照面板做出选择"""
        news_item = None
        if ctx.snapshot_panel.snapshot and ctx.snapshot_panel.snapshot.news_item:
            news_item = ctx.snapshot_panel.snapshot.news_item
        
        # 检查动作类型
        action = choice_data.get('action', '')
        
        # 当面处理：启动对话演绎模式
        if action == 'FACE_TO_FACE' and news_item:
            # 尝试启动对话演绎模式
            if _start_event_dialog_mode(news_item, choice_idx, ctx):
                log_game_event(f"[大宋实况] 玩家选择当面处理: {choice_data.get('text', '?')}", tag="LIVE")
                return  # 对话模式会在结束后设置状态
        
        # 快信处理后的具体选项：应用效果
        if action not in ('FACE_TO_FACE', 'LETTER', 'BACK') and news_item:
            # 应用选择效果
            ctx.live_news_manager.apply_choice(news_item, choice_idx, ctx)
            ctx.current_state = GAME_STATE_PLAYING
            log_game_event(f"[大宋实况] 玩家快信处理: {choice_data.get('text', '?')}", tag="LIVE")
            return
        
        # 其他情况（如返回按钮）不处理
        ctx.current_state = GAME_STATE_PLAYING
    
    def _start_event_dialog_mode(news_item, choice_idx: int, ctx) -> bool:
        """
        【任务引导式】启动事件处理流程
        
        流程：
        1. 确定事发地点（NPC当前位置或随机建筑）
        2. 相关NPC快速移动到事发地点（加速移动、状态保护）
        3. 玩家自动移动到事件地点
        4. 所有人到达后自动触发对话
        
        Returns:
            bool: 是否成功启动
        """
        import math
        from src.entities import NPC, Building
        from src.definitions import STATE_EVENT
        
        try:
            print(f"[大宋实况·任务] ║        启动任务引导模式: {news_item.title}  ║")
            
            # ═══════════════════════════════════════════════════════════════
            # 1. 查找相关 NPC
            # ═══════════════════════════════════════════════════════════════
            actor_ids = getattr(news_item, 'actor_ids', [])
            actor_names = getattr(news_item, 'actor_names', [])
            
            event_npcs = []
            for card in ctx.all_cards:
                if not isinstance(card, NPC):
                    continue
                card_id = getattr(card, 'id', None)
                card_name = getattr(card, 'name', '')
                # 通过 ID 或名字匹配
                if (card_id and str(card_id) in [str(a) for a in actor_ids]) or \
                   (card_name and card_name in actor_names):
                    event_npcs.append(card)
            
            if not event_npcs:
                print(f"[大宋实况·任务] 警告: 未找到关联NPC")
                return None
            
            print(f"[大宋实况·任务] 找到 {len(event_npcs)} 个关联NPC: {[n.name for n in event_npcs]}")
            
            # ═══════════════════════════════════════════════════════════════
            # 2. 确定事发地点（选择第一个NPC的位置或附近建筑）
            # ═══════════════════════════════════════════════════════════════
            main_npc = event_npcs[0]
            event_x = main_npc.rect.centerx
            event_y = main_npc.rect.centery
            
            # 尝试找到附近的建筑作为集合点（更自然）
            buildings = [c for c in ctx.all_cards if isinstance(c, Building)]
            nearest_building = None
            nearest_dist = 9999
            for b in buildings:
                dist = math.hypot(b.rect.centerx - event_x, b.rect.centery - event_y)
                if dist < nearest_dist and dist < 400:  # 400像素范围内
                    nearest_dist = dist
                    nearest_building = b
            
            if nearest_building:
                # 使用建筑位置作为集合点
                event_x = nearest_building.rect.centerx
                event_y = nearest_building.rect.centery + 50  # 建筑前方
                event_location_name = getattr(nearest_building, 'name', '附近')
                print(f"[大宋实况·任务] 集合地点: {event_location_name} ({event_x}, {event_y})")
            else:
                event_location_name = "事发现场"
                print(f"[大宋实况·任务] 集合地点: NPC当前位置 ({event_x}, {event_y})")
            
            # ═══════════════════════════════════════════════════════════════
            # 3. 让相关 NPC 移动到事发地点（加速移动 + 状态保护）
            # ═══════════════════════════════════════════════════════════════
            for i, npc in enumerate(event_npcs):
                # ═══════════════════════════════════════════════════════════════
                # 【演出状态恢复】确保NPC能够参与演出
                # ═══════════════════════════════════════════════════════════════
                from src.definitions import SAFETY_NORMAL, SAFETY_DOWNED, STATE_COMBAT, STATE_DOWNED
                
                # 保存原始状态信息（用于调试和恢复）
                original_safety = getattr(npc, 'safety', SAFETY_NORMAL)
                original_state = getattr(npc, 'state', 'IDLE')
                original_hp = getattr(npc, 'hp', 100)
                max_hp = getattr(npc, 'max_hp', 100)
                
                # 【战斗脱离】如果NPC正在战斗中，强制结束战斗
                if getattr(npc, 'aggro_target', None) is not None:
                    print(f"[大宋实况·任务] NPC {npc.name} 正在战斗，强制脱离战斗")
                    npc.aggro_target = None
                if getattr(npc, 'in_combat', False):
                    npc.in_combat = False
                # 清空仇恨列表，防止被其他NPC追击
                if hasattr(npc, 'hatred'):
                    npc.hatred.clear()
                
                # 【重伤恢复】如果NPC处于DOWNED状态，恢复其行动能力
                if original_safety == SAFETY_DOWNED or original_state == STATE_DOWNED or original_state == 'DOWNED':
                    # 恢复安全状态
                    npc.safety = SAFETY_NORMAL
                    print(f"[大宋实况·任务] NPC {npc.name} 从重伤状态恢复 (safety: {original_safety} -> NORMAL)")
                    
                    # 如果血量为0或过低，恢复10%血量
                    if original_hp <= 0 and max_hp > 0:
                        heal_amount = int(max_hp * 0.1)
                        npc.hp = heal_amount
                        print(f"[大宋实况·任务] NPC {npc.name} 血量恢复: {original_hp} -> {npc.hp}/{max_hp} (+10%)")
                    elif original_hp < max_hp * 0.1 and max_hp > 0:
                        # 血量过低也恢复到10%
                        heal_amount = int(max_hp * 0.1)
                        npc.hp = max(npc.hp, heal_amount)
                        print(f"[大宋实况·任务] NPC {npc.name} 血量补充: {original_hp} -> {npc.hp}/{max_hp}")
                
                # 【负面状态清除】清除可能导致晕倒的状态
                # 恢复饥饿值和温度（防止立即再次晕倒）
                if hasattr(npc, 'hunger'):
                    if npc.hunger <= 10:  # 饥饿过度
                        npc.hunger = 30  # 恢复到安全值
                        print(f"[大宋实况·任务] NPC {npc.name} 饥饿恢复: -> {npc.hunger}")
                if hasattr(npc, 'temperature'):
                    if npc.temperature <= 10:  # 体温过低
                        npc.temperature = 30  # 恢复到安全值
                        print(f"[大宋实况·任务] NPC {npc.name} 体温恢复: -> {npc.temperature}")
                
                # 【清除被背负状态】如果NPC正在被背着，放下来
                if hasattr(npc, 'stack_parent') and npc.stack_parent:
                    carrier = npc.stack_parent
                    npc.stack_parent = None
                    if hasattr(carrier, 'dragging') and carrier.dragging == npc:
                        carrier.dragging = None
                    print(f"[大宋实况·任务] NPC {npc.name} 从 {getattr(carrier, 'name', '某人')} 身上放下")
                
                # 保存原始移动速度（用于事件结束后恢复）
                original_speed = getattr(npc, 'move_speed', 80.0)
                if not hasattr(npc, '_event_original_speed'):
                    npc._event_original_speed = original_speed
                
                # 【加速移动】事件期间NPC移动速度提升为2倍
                npc.move_speed = original_speed * 2.0
                print(f"[大宋实况·任务] NPC {npc.name} 移动速度: {original_speed} -> {npc.move_speed}")
                
                # 【状态保护】设置为事件状态（暂停AI，防止被攻击等中断）
                npc.state = STATE_EVENT
                npc.ai_reason = f"参与事件: {news_item.title[:15]}..."
                
                # 【事件保护标记】防止战斗系统/其他系统干扰
                npc._event_protected = True
                npc._event_news_id = getattr(news_item, 'news_id', None)
                
                # 设置移动目标（分散站位，避免重叠）
                # 卡牌宽度70px，相邻NPC中心点距离至少80px（70+10间隔）
                offset_x = (i % 3 - 1) * 80  # -80, 0, +80
                offset_y = (i // 3) * 100   # 0, 100, 200（Y轴间隔更大）
                npc.set_movement_target(event_x + offset_x, event_y + offset_y, reason="前往事件地点")
                
                print(f"[大宋实况·任务] NPC {npc.name} 开始快速移动到事件地点（状态保护已启用）")
            
            # ═══════════════════════════════════════════════════════════════
            # 4. 【玩家自动移动】强制控制玩家前往事件地点
            # ═══════════════════════════════════════════════════════════════
            # 保存待处理的事件信息
            ctx._pending_event_news = news_item
            ctx._pending_event_choice_idx = choice_idx
            ctx._pending_event_location = (event_x, event_y)
            ctx._pending_event_npcs = event_npcs
            ctx._pending_event_location_name = event_location_name
            ctx._pending_event_active = True
            ctx._pending_event_start_time = time.time()  # 记录开始时间
            
            # 【玩家自动移动】强制设置玩家移动目标
            player_dist = math.hypot(ctx.player.rect.centerx - event_x, ctx.player.rect.centery - event_y)
            print(f"[大宋实况·任务] 玩家当前距离事件地点: {player_dist:.0f}px")
            
            # 计算玩家的目标位置（在NPC集合点附近，但稍微偏移）
            player_target_x = event_x
            player_target_y = event_y - 30  # 玩家站在NPC前面一点
            
            # 强制设置玩家移动目标
            ctx.player.set_movement_target(player_target_x, player_target_y, reason="前往事件地点")
            print(f"[大宋实况·任务] 玩家自动移动目标: ({player_target_x}, {player_target_y})")
            
            # 显示浮动提示
            ctx.ft_manager.add_text(f"📍 正在前往{event_location_name}...", 
                                   ctx.player.rect.centerx, ctx.player.rect.top - 60, 
                                   (255, 220, 100))
            
            # 如果摄像机支持，聚焦到事件地点
            if camera:
                camera.start_event_focus(event_x, event_y, duration=45)
            
            # 关闭事件面板，恢复游戏状态（但玩家会自动移动）
            ctx.snapshot_panel.hide()
            ctx.current_state = GAME_STATE_PLAYING
            
            print(f"[大宋实况·任务] 任务引导模式已启动，玩家和NPC正在移动...")
            print(f"{'='*70}\n")
            return True
            
        except Exception as e:
            print(f"[大宋实况·任务] 启动失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    
    
    def _check_event_arrival_and_trigger():
        """
        【主循环调用】检测玩家是否到达事件地点，所有演员是否就位
        返回 True 表示应该触发对话
        """
        import math
        from src.definitions import STATE_IDLE
        
        if not getattr(ctx, '_pending_event_active', False):
            return False
        
        event_x, event_y = ctx._pending_event_location
        event_npcs = ctx._pending_event_npcs
        event_location_name = getattr(ctx, '_pending_event_location_name', '事件地点')
        start_time = getattr(ctx, '_pending_event_start_time', time.time())
        
        # 检查玩家是否到达
        player_dist = math.hypot(
            ctx.player.rect.centerx - event_x,
            ctx.player.rect.centery - event_y
        )
        
        # 【调试】定期打印状态
        debug_timer = getattr(ctx, '_event_arrival_debug_timer', 0) + 1
        ctx._event_arrival_debug_timer = debug_timer
        elapsed = time.time() - start_time
        
        # 【超时保护】如果超过60秒还没到达，强制开始
        timeout_reached = elapsed > 60.0
        
        if debug_timer % 60 == 0:  # 每秒打印一次
            # 只打印不满足要求的玩家和NPC
            issues_found = False
            
            if player_dist > 120 and not timeout_reached:
                print(f"[任务引导·检测] 已经过{elapsed:.1f}秒 | ⚠️ 玩家未到达: 距离{event_location_name} {player_dist:.0f}px (需<120)")
                print(f"    玩家位置: ({ctx.player.rect.centerx}, {ctx.player.rect.centery})")
                player_target_x = getattr(ctx.player, '_target_x', None)
                player_target_y = getattr(ctx.player, '_target_y', None)
                print(f"    玩家目标: ({player_target_x}, {player_target_y})")
                issues_found = True
            
            for npc in event_npcs:
                npc_dist = math.hypot(npc.rect.centerx - event_x, npc.rect.centery - event_y)
                if npc_dist > 80 and not timeout_reached:
                    npc_speed = getattr(npc, 'move_speed', '?')
                    npc_target_x = getattr(npc, '_target_x', None)
                    npc_target_y = getattr(npc, '_target_y', None)
                    npc_cooldown = getattr(npc, '_grid_adjust_cooldown', 0)
                    print(f"  - ⚠️ {npc.name}: 距离={npc_dist:.0f}px (需<80), state={npc.state}, speed={npc_speed}")
                    print(f"      当前位置: ({npc.rect.centerx}, {npc.rect.centery})")
                    print(f"      目标位置: ({npc_target_x}, {npc_target_y})")
                    if npc_cooldown > 0:
                        print(f"      ⚠️ 网格调整冷却中: {npc_cooldown}帧")
                    issues_found = True
            
            if not issues_found and not timeout_reached:
                print(f"[任务引导·检测] 已经过{elapsed:.1f}秒 | 所有人已就位，等待触发对话")
        
        if timeout_reached:
            print(f"[任务引导·检测] 超时60秒，强制开始事件！")
        
        # 【关键修复】检查玩家是否有移动目标，如果没有则重新设置
        player_target_x = getattr(ctx.player, '_target_x', None)
        player_target_y = getattr(ctx.player, '_target_y', None)
        player_cooldown = getattr(ctx.player, '_grid_adjust_cooldown', 0)
        
        # 如果冷却期结束且没有移动目标，重新设置目标
        if player_cooldown <= 0 and (player_target_x is None or player_target_y is None) and player_dist > 120:
            player_target_x = event_x
            player_target_y = event_y - 30  # 玩家站在NPC前面一点
            ctx.player.set_movement_target(player_target_x, player_target_y, reason="冷却结束，重新前往事件地点")
            print(f"[任务引导·检测] 玩家冷却结束，重新设置移动目标")
        
        if player_dist > 120 and not timeout_reached:  # 玩家还没到
            return False
        
        # 检查所有 NPC 是否到达，同时恢复DOWNED状态的NPC
        from src.definitions import SAFETY_NORMAL, SAFETY_DOWNED, STATE_DOWNED
        
        all_arrived = True
        for npc in event_npcs:
            npc_state = getattr(npc, 'state', None)
            npc_safety = getattr(npc, 'safety', SAFETY_NORMAL)
            
            # 【实时恢复】如果NPC在移动过程中进入DOWNED状态，立即恢复
            if npc_state == 'DOWNED' or npc_state == STATE_DOWNED or npc_safety == SAFETY_DOWNED:
                # 恢复安全状态
                npc.safety = SAFETY_NORMAL
                npc.state = STATE_EVENT
                
                # 恢复血量（如果为0，恢复10%）
                max_hp = getattr(npc, 'max_hp', 100)
                if npc.hp <= 0 and max_hp > 0:
                    npc.hp = int(max_hp * 0.1)
                    print(f"[任务引导·检测] NPC {npc.name} 演出恢复: 血量 0 -> {npc.hp}")
                
                # 恢复饥饿和体温
                if hasattr(npc, 'hunger') and npc.hunger <= 10:
                    npc.hunger = 30
                if hasattr(npc, 'temperature') and npc.temperature <= 10:
                    npc.temperature = 30
                
                # 清除战斗状态
                if getattr(npc, 'aggro_target', None) is not None:
                    npc.aggro_target = None
                if getattr(npc, 'in_combat', False):
                    npc.in_combat = False
                
                print(f"[任务引导·检测] NPC {npc.name} 从重伤状态恢复，继续前往事件地点")
                
                # 重新设置移动目标（使用与初始设置相同的offset计算）
                npc_idx = event_npcs.index(npc)
                offset_x = (npc_idx % 3 - 1) * 80  # -80, 0, +80
                offset_y = (npc_idx // 3) * 100   # 0, 100, 200
                npc.set_movement_target(event_x + offset_x, event_y + offset_y, reason="前往事件地点")
            
            # 【关键修复】检查NPC是否有移动目标，如果没有则重新设置
            npc_target_x = getattr(npc, '_target_x', None)
            npc_target_y = getattr(npc, '_target_y', None)
            npc_cooldown = getattr(npc, '_grid_adjust_cooldown', 0)
            
            # 如果冷却期结束且没有移动目标，重新设置目标
            if npc_cooldown <= 0 and (npc_target_x is None or npc_target_y is None):
                npc_idx = event_npcs.index(npc)
                offset_x = (npc_idx % 3 - 1) * 80  # -80, 0, +80
                offset_y = (npc_idx // 3) * 100   # 0, 100, 200
                npc.set_movement_target(event_x + offset_x, event_y + offset_y, reason="冷却结束，重新前往事件地点")
                print(f"[任务引导·检测] NPC {npc.name} 冷却结束，重新设置移动目标")
            
            # 检查NPC距离
            npc_dist = math.hypot(
                npc.rect.centerx - event_x,
                npc.rect.centery - event_y
            )
            # 【放宽到达距离】从80px增加到120px，避免网格系统防重叠机制导致NPC无法到达
            if npc_dist > 120 and not timeout_reached:
                all_arrived = False
        
        if not all_arrived:
            return False
        
        # ═══════════════════════════════════════════════════════════════
        # 所有人就位（或超时），触发对话！
        # ═══════════════════════════════════════════════════════════════
        print(f"\n{'='*70}")
        print(f"[大宋实况·任务] ╔════════════════════════════════════════════════════════╗")
        print(f"[大宋实况·任务] ║              所有人就位，触发对话演绎！                  ║")
        print(f"[大宋实况·任务] ╚════════════════════════════════════════════════════════╝")
        print(f"[大宋实况·任务] 等待时间: {elapsed:.1f}秒")
        print(f"{'='*70}\n")
        
        ctx._pending_event_active = False
        
        # ═══════════════════════════════════════════════════════════════
        # 【事件结束准备】注册清理回调
        # 对话结束后会恢复NPC速度、移除保护标记
        # ═══════════════════════════════════════════════════════════════
        def _cleanup_event_npcs():
            """对话结束后清理事件NPC状态"""
            print(f"[大宋实况·任务] 清理事件NPC状态...")
            for npc in event_npcs:
                # 恢复原始移动速度
                if hasattr(npc, '_event_original_speed'):
                    npc.move_speed = npc._event_original_speed
                    print(f"  - {npc.name} 速度恢复: {npc.move_speed}")
                    del npc._event_original_speed
                
                # 移除保护标记
                if hasattr(npc, '_event_protected'):
                    del npc._event_protected
                if hasattr(npc, '_event_news_id'):
                    del npc._event_news_id
                
                # 恢复状态为IDLE（如果还在EVENT状态）
                if npc.state == STATE_EVENT:
                    npc.state = STATE_IDLE
                    npc.ai_reason = "事件结束，恢复正常"
                    print(f"  - {npc.name} 状态恢复: EVENT -> IDLE")
            
            print(f"[大宋实况·任务] 事件NPC清理完成！")
        
        # 保存清理函数到ctx，供剧情结束时调用
        ctx._pending_event_cleanup = _cleanup_event_npcs
        
        # 启动对话
        news_item = ctx._pending_event_news
        try:
            from src.live_news_to_dialog import get_news_dialog_bridge
            
            bridge = get_news_dialog_bridge()
            dialogs = bridge.convert_news_to_dialogs(news_item, ctx)
            
            if dialogs:
                # 直接传递 DialogLine 对象列表，不转换为字典
                ctx.story_ui.start_dialog(dialogs)
                ctx.ft_manager.add_text("🎬 事件开始！", event_x, event_y - 40, (100, 255, 100))
                
                # 【音效】播放事件开始音效
                try:
                    from src.audio.sound_manager import get_sound_manager
                    get_sound_manager().play_confirm()
                except Exception:
                    pass
                
                return True
        except Exception as e:
            print(f"[大宋实况·任务] 触发对话失败: {e}")
            import traceback
            traceback.print_exc()
            # 即使对话失败也要清理
            _cleanup_event_npcs()
        
        return False
    
    # 保存检测函数到 ctx，供主循环调用
    ctx._check_event_arrival = _check_event_arrival_and_trigger
    
    ctx.snapshot_panel.on_choice_selected = on_snapshot_choice
    ctx.snapshot_panel.on_close = lambda: setattr(ctx, 'current_state', GAME_STATE_PLAYING)
    
    log_game_event("=== 大宋实况系统初始化完成（含导演系统）===")

    # 【已移除】旧的顶部按钮现在由系统功能菜单处理（render_system._draw_system_menu）
    # 初始化退出请求标志
    ctx.request_exit = False
    # 【UI层级系统】导入命中检测
    from src.ui.hit_test import clear_ui_zones, is_ui_blocking
    
    # 【性能监控】初始化
    perf = get_perf_monitor(SCREEN_W, SCREEN_H)
    perf.visible = False  # 默认隐藏，按 F3 显示
    perf.set_game_ref(ctx)  # 设置游戏引用，用于调试按钮功能
    
    running = True
    while running:
        perf.frame_start()  # 【性能监控】帧开始
        dt = clock.tick(60)
        
        # 【UI层级系统】每帧开始时清空上一帧的UI区域
        clear_ui_zones()
        
        # 【UI层级系统修复】预先注册系统功能菜单的UI区域，确保事件处理时能正确检测
        # 这必须在事件处理循环之前执行，否则点击按钮时UI区域还未注册，会导致点击穿透
        _preregister_system_menu_zones(SCREEN_W, SCREEN_H, renderer.system_menu_expanded)
        
        # 【新增】确保所有事件演员保持在 STATE_EVENT 状态
        if hasattr(ctx, 'event_actors') and ctx.event_actors:
            for actor in ctx.event_actors:
                if hasattr(actor, 'state') and actor.state != STATE_EVENT:
                    actor.state = STATE_EVENT
                    actor.clear_movement_target("事件演员锁定")
        
        if ctx.input_delay > 0:
            ctx.input_delay -= 1
        mx, my = pygame.mouse.get_pos()
        click_event = False
        keys = pygame.key.get_pressed()

        # 摄像机边缘滚动 & 小地图拖拽（每帧更新）
        if camera:
            # 【新增】剧情期间 / UI面板期间锁定摄像机
            is_story_mode = ctx.story_ui.is_active or ctx.story_ui.choice_mode
            # 【新增】NPC详情/资源详情等面板打开时也禁止摄像机滚动
            is_ui_panel_open = ctx.current_state in (
                GAME_STATE_NPC_DETAIL,
                GAME_STATE_RESOURCE_DETAIL,
                GAME_STATE_EVENT_DIALOG
            )
            camera.story_locked = is_story_mode or is_ui_panel_open
            
            # 【新增】优先更新事件聚焦动画（动画期间不响应其他操作）
            if camera.event_focus_active:
                camera.update_event_focus()
            elif not camera.story_locked:  # 剧情锁定时禁止边缘滚动
                # 若检测到边缘滚动触发，取消跟随模式
                zone = EDGE_SCROLL_ZONE
                if (0 <= mx < zone or
                    camera.view_w - zone < mx <= camera.view_w or
                    (mx <= camera.view_w and TOPBAR_H <= my < TOPBAR_H + zone) or
                    (mx <= camera.view_w and my >= camera.screen_h - zone)):
                    camera.follow_player = False
                camera.update(dt, mx, my)

        # 1. 输入事件处理
        current_event = None  # 保存当前事件用于渲染
        for event in pygame.event.get():
            current_event = event  # 保存最新事件
            #退出游戏
            if event.type == pygame.QUIT:
                running = False
                continue
            
            # 【新增】AI聊天界面事件处理（最高优先级）
            if ctx.chat_integration.is_chat_active():
                if ctx.chat_integration.handle_event(event):
                    continue  # 聊天界面消费了事件
            
            # ══════════════════════════════════════════════════════════════════════
            # 【大宋实况】快照面板事件处理（高优先级，全屏遮挡）
            # ══════════════════════════════════════════════════════════════════════
            if ctx.current_state == GAME_STATE_LIVE_SNAPSHOT and hasattr(ctx, 'snapshot_panel'):
                if ctx.snapshot_panel.handle_event(event):
                    continue  # 快照面板消费了事件
            
            # 【新增】选择界面输入处理（最高优先级）
            if ctx.story_ui.choice_mode:
                selected_key = ctx.story_ui.handle_choice_input(event, ctx)
                if selected_key:
                    # ═══════════════════════════════════════════════════════════════
                    # 【大宋实况事件】检查是否是大宋实况事件的选择
                    # 如果是，使用 LiveNewsToDialogBridge 处理后续对话
                    # ═══════════════════════════════════════════════════════════════
                    from src.live_news_to_dialog import get_news_dialog_bridge
                    news_bridge = get_news_dialog_bridge()
                    
                    if news_bridge.is_choice_pending():
                        # 这是大宋实况事件的选择，获取后续对话
                        followup_dialogs = news_bridge.get_choice_followup_dialogs(selected_key, ctx)
                        if followup_dialogs:
                            ctx.story_ui.start_dialog(followup_dialogs)
                            ctx.ft_manager.add_text(f"📜 {selected_key}", ctx.player.rect.centerx, 
                                                   ctx.player.rect.top - 50, (255, 230, 150))
                            print(f"[大宋实况] 玩家选择 {selected_key}，播放后续对话 {len(followup_dialogs)} 句")
                        else:
                            print(f"[大宋实况] 玩家选择 {selected_key}，但没有后续对话")
                            news_bridge.clear_current()  # 清理状态
                    else:
                        # 主线任务的选择，使用原有逻辑
                        # 【核心】传入 all_cards 以便为所有剧情参与者生成记忆
                        success, next_qid, msg = ctx.quest_manager.make_choice(
                            selected_key,
                            player=ctx.player,
                            faction_war_system=ctx.faction_war if hasattr(ctx, 'faction_war') else None,
                            ft_manager=ctx.ft_manager,
                            all_cards=ctx.all_cards
                        )
                        if success:
                            ctx.ft_manager.add_text(msg, ctx.player.rect.centerx, 
                                                   ctx.player.rect.top - 50, (255, 230, 150))
                            # 播放分支对话
                            ctx.quest_manager.try_start_quest_dialog(ctx.story_ui, ctx.all_cards)
                continue  # 选择模式下阻断其他输入
            
            # ══════════════════════════════════════════════════════════════════════
            # 【大宋实况】新闻历史面板事件处理（高优先级）
            # ══════════════════════════════════════════════════════════════════════
            if hasattr(ctx, 'live_news_panel') and ctx.live_news_panel.is_open():
                if ctx.live_news_panel.handle_event(event):
                    continue  # 新闻面板消费了事件
            
            # 【大宋实况】右侧事件通知点击处理
            if hasattr(ctx, 'event_notification') and ctx.current_state == GAME_STATE_PLAYING:
                if ctx.event_notification.handle_event(event):
                    continue  # 事件通知消费了事件
            
            # 【大宋实况】快捷键 L 打开新闻历史面板
            if event.type == pygame.KEYDOWN and event.key == pygame.K_l:
                if ctx.current_state == GAME_STATE_PLAYING and hasattr(ctx, 'live_news_panel'):
                    ctx.live_news_panel.toggle()
                    continue
            
            # 【性能监控】F3 切换显示
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
                perf.toggle()
                continue
            
            # 【性能监控】调试按钮点击处理
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if perf.handle_click((mx, my)):
                    continue  # 性能面板消费了点击事件
            
            # 【大宋实况】模式选择器事件处理（已移除，保留兼容性）
            # if hasattr(ctx, 'mode_selector') and ctx.mode_selector and ctx.mode_selector.visible:
            #     if ctx.mode_selector.handle_event(event):
            #         continue
            
            # 【系统功能菜单点击优先级】检测是否点击在系统功能菜单区域
            # 如果是，跳过剧情处理，让渲染阶段的菜单逻辑处理该点击
            _skip_story_input = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # 计算系统功能菜单区域（与render_system._draw_system_menu保持一致）
                mm_x = SCREEN_W - SIDEBAR_W - MINIMAP_W - MINIMAP_MARGIN
                mm_y = SCREEN_H - MINIMAP_H - MINIMAP_MARGIN
                menu_btn_y = mm_y - 32 - 45  # 主按钮位置
                menu_btn_rect = pygame.Rect(mm_x, menu_btn_y, MINIMAP_W, 32)
                
                # 展开菜单区域（向上展开最多7个按钮）
                menu_expanded_top = menu_btn_y - 7 * 33 - 10
                menu_full_rect = pygame.Rect(mm_x - 5, menu_expanded_top, MINIMAP_W + 10, menu_btn_y - menu_expanded_top + 42)
                
                if menu_btn_rect.collidepoint(mx, my) or (renderer.system_menu_expanded and menu_full_rect.collidepoint(mx, my)):
                    _skip_story_input = True  # 点击在菜单区域，跳过剧情处理
            
            #刷新任务
            prev_qid = ctx.quest_manager.active_quest_id
            if not _skip_story_input and ctx.story_ui.handle_input(event, ctx):
                if ctx.quest_manager.active_quest_id != prev_qid:
                    title = ctx.quest_manager.get_quest_title()
                    if title: ctx.story_ui.show_quest_title(title)
                    ctx.quest_manager.set_flag('guidance_visible', True)
                    ctx.ft_manager.add_text("任务更新", ctx.player.rect.x, ctx.player.rect.y - 80, (255, 215, 0))
                continue

            #按下鼠标左键
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if ctx.input_delay > 0:
                    continue
                click_event = True
                # 小地图点击/拖拽起始（优先处理，不穿透到游戏世界）
                if camera and camera.handle_minimap_click(mx, my):
                    click_event = False
                    continue
                if my < TOPBAR_H:
                    continue
                is_paused = (ctx.event_manager.time_speed == 0)
                # 将屏幕坐标转换为世界坐标（用于玩家移动和卡牌交互）
                if camera:
                    wmx, wmy = camera.screen_to_world(mx, my)
                else:
                    wmx, wmy = float(mx), float(my)
                if ctx.current_state == GAME_STATE_PLAYING:
                    # 【已移至系统功能菜单】旧的顶部按钮点击逻辑已移除
                    # 卡牌交互（用世界坐标检测碰撞）
                    if True:  # 保持缩进结构
                        captured = ctx.interaction_mgr.handle_mouse_down(wmx, wmy, ctx.all_cards, ctx.player, is_paused=is_paused)
                        if not captured:
                            ctx.selected_npc = None
                            # 玩家移动逻辑（目标使用世界坐标）
                            if ctx.current_state == GAME_STATE_PLAYING:
                                # 【UI层级系统】检测是否被UI阻挡
                                # 如果点击位置被UI覆盖，不触发玩家移动
                                if is_ui_blocking(mx, my):
                                    pass  # UI阻挡，不处理玩家移动
                                # [!] 重伤状态禁止移动，显示提示
                                elif ctx.player.safety == SAFETY_DOWNED:
                                    ctx.ft_manager.add_text("重伤！等待救援...", ctx.player.rect.centerx, ctx.player.rect.top - 40, (255, 50, 50))
                                # [!] 剧情期间禁止玩家主动移动
                                elif ctx.story_ui.is_active or ctx.story_ui.waiting_for_action:
                                    ctx.ft_manager.add_text("剧情中...", ctx.player.rect.centerx, ctx.player.rect.top - 40, (255, 200, 100))
                                elif not is_paused and (not (ctx.player.stack_parent or ctx.player.state == STATE_EVENT)):                                    
                                    ctx.player.set_movement_target(wmx, wmy, reason="玩家点击移动") # <--- 新增：设置移动目标
                                    ctx.player.clear_target_obj("玩家点击移动") # <--- 新增：清理目标对象，防止AI误判                                    
                                    ctx.player.state = 'MOVING'
                                    ctx.player.is_working = False
                                    ctx.player.work_timer = 0
                                    # 浮动文字在世界坐标位置显示
                                    ctx.ft_manager.add_text("前往", wmx, wmy, (100, 255, 255))
                                else:
                                    warn_msg = "目前无法移动"
                                    ctx.ft_manager.add_text(warn_msg, ctx.player.rect.centerx, ctx.player.rect.top - 40, (255, 80, 80))
                        else:
                            ctx.selected_npc = ctx.interaction_mgr.dragged_card


            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    # 小地图拖拽结束
                    if camera:
                        camera.handle_minimap_release()
                    if camera:
                        wmx, wmy = camera.screen_to_world(mx, my)
                    else:
                        wmx, wmy = float(mx), float(my)
                    action, target = ctx.interaction_mgr.handle_mouse_up(wmx, wmy, ctx.all_cards, ctx.player, ctx.quest_manager, ctx.recipe_manager)
                    
                    if action == 'DENIED':
                        ctx.ft_manager.add_text(target, mx, my - 50, (255, 50, 50))
                    elif action == 'CLICK':
                        triggered = ctx.quest_manager.try_trigger_npc_interaction(target, ctx.story_ui)
                        # 【修改】任务NPC点击后：播放任务提示 + 同时打开详情面板
                        # 即使 triggered=True（有任务对话），也打开详情面板
                        if isinstance(target, NPC):
                            # --- NPC 寻路调试模式 ---
                            if DEBUG_NPC_PATH_NO_PAUSE:
                                # 清除上一个调试 NPC 的标记
                                old_debug = getattr(ctx, 'debug_path_npc', None)
                                if old_debug and old_debug is not target:
                                    old_debug.debug_selected = False
                                # 切换：如果再次点击同一 NPC 则取消调试
                                if getattr(ctx, 'debug_path_npc', None) is target:
                                    target.debug_selected = False
                                    ctx.debug_path_npc = None
                                    ctx.ft_manager.add_text("取消寻路调试", target.rect.x, target.rect.y - 40, (200, 200, 100))
                                    print(f"[PathDebug] 已取消调试 NPC: {target.name}")
                                else:
                                    target.debug_selected = True
                                    target.debug_path_log_timer = 0  # 立即触发一次打印
                                    ctx.debug_path_npc = target
                                    ctx.ft_manager.add_text("寻路调试中...", target.rect.x, target.rect.y - 40, (100, 255, 100))
                                    print(f"[PathDebug] 开始调试 NPC: {target.name} | 状态:{target.state} | 位置:({target.rect.centerx},{target.rect.centery})")
                                # 不暂停，不弹详情页
                            elif target.state == STATE_EVENT: # 模拟自动寻路过去交互
                                ctx.player.set_movement_target(target.rect.x, target.rect.y + 30, reason="前往事件NPC")      
                                ctx.player.set_target_obj(target, reason="前往事件NPC") 
                                ctx.player.state = 'MOVING'                                
                                ctx.ft_manager.add_text("前往...", ctx.player.target_x, ctx.player.target_y, (150, 255, 150))
                            else:
                                ctx.active_event_npc = target
                                ctx.current_state = GAME_STATE_NPC_DETAIL
                                ctx.event_manager.request_interaction_pause()
                        elif isinstance(target, Resource):
                            print(f"展示资源卡信息")
                            ctx.active_resource_card = target
                            ctx.current_state = GAME_STATE_RESOURCE_DETAIL
                            ctx.ui_manager._temp_split_val = 1 
                            ctx.event_manager.request_interaction_pause()
                        elif isinstance(target, Building):
                            # 【新增】点击建筑显示建筑面板
                            print(f"展示建筑信息: {getattr(target, 'name', target)}")
                            ctx.active_building = target
                            ctx.current_state = GAME_STATE_BUILDING_INFO
                            ctx.event_manager.request_interaction_pause()
                    elif action == 'MERGE_RESOURCE' or action == 'PICKUP_RESOURCE':
                        if target in ctx.all_cards:
                            ctx.all_cards.remove(target)
                            ctx.ft_manager.add_text("资源操作{action}!", target.rect.x, target.rect.y, (100, 255, 100))
                    
                    # 【手续费系统】处理建筑使用费确认请求
                    elif action == 'FEE_REQUIRED':
                        ctx.pending_fee_action = target  # target 是包含费用信息的字典
                        ctx.current_state = GAME_STATE_FEE_CONFIRM
                    
                    elif action == 'DELIVER_ITEM':
                        # 交付任务：物品堆叠到NPC身上完成交付
                        resource_card, target_npc = target
                        # 显示交付浮动文字
                        current, total = ctx.quest_manager.get_delivery_progress()
                        if current < total:
                            ctx.ft_manager.add_text(f"交付 {resource_card.item_type} ({current}/{total})", 
                                                   target_npc.rect.centerx, target_npc.rect.top - 30, (255, 215, 0))
                        else:
                            ctx.ft_manager.add_text("交付完成！", 
                                                   target_npc.rect.centerx, target_npc.rect.top - 30, (100, 255, 100))
                        # 移除资源卡
                        if resource_card in ctx.all_cards:
                            ctx.all_cards.remove(resource_card)
                    
                    # 【新增】处理堆叠事件 - 触发配方工作
                    elif action == 'STACK':
                        # target 是堆叠的父卡（建筑或NPC）
                        stacked_on = target
                        # 找到被拖拽的卡牌（刚刚堆叠上去的）
                        dragged_card = stacked_on.stack_child
                        if dragged_card and isinstance(stacked_on, Building):
                            # 检查配方匹配
                            recipe = ctx.recipe_manager.check_match(dragged_card, stacked_on)
                            if recipe:
                                dragged_card.state = STATE_WORKING
                                dragged_card.recipe_proxy = recipe
                                # 计算工作时间（考虑职业效率）
                                base_time = int(recipe.data.get('time', 100) or 100)
                                preferred_job = recipe.data.get('preferred_job', '')
                                worker_job = getattr(dragged_card, 'job', '')
                                # 职业匹配检查：PLAYER视为万能工，匹配所有
                                if preferred_job and worker_job != 'PLAYER' and worker_job != preferred_job:
                                    # 非专业职业，效率降低50%（时间*1.5）
                                    work_time = int(base_time * 1.5)
                                    ctx.ft_manager.add_text(f"效率↓ ({preferred_job}更适合)", 
                                                           dragged_card.rect.centerx, dragged_card.rect.top - 30, (255, 200, 100))
                                else:
                                    work_time = base_time
                                dragged_card.work_max = work_time
                                dragged_card.work_timer = 0
                                dragged_card.is_working = True
                                dragged_card.ai_reason = f"工作中: {recipe.data.get('desc', '劳作')}"
                                print(f"[STACK] {dragged_card.name} 开始工作: {recipe.data.get('desc')} (时间:{work_time})")
                            else:
                                ctx.ft_manager.add_text("无可用配方", 
                                                       dragged_card.rect.centerx, dragged_card.rect.top - 30, (200, 100, 100))
               
        # =====================================================================
        # 2. 游戏逻辑更新
        # =====================================================================
        
        
        if ctx.current_state == GAME_STATE_PLAYING:
            # 【修复】只有镜头动画结束后才触发剧情对话
            camera_ready = (camera is None) or (not camera.event_focus_active)
            if camera_ready and ctx.quest_manager.check_and_play_intro(ctx.all_cards, ctx.story_ui):
                pass # 刚刚触发了剧情
            # 2. 全局更新（拖拽用世界坐标，避免摄像机偏移导致NPC闪到屏幕左上角）
            if camera:
                _wmx, _wmy = camera.screen_to_world(mx, my)
            else:
                _wmx, _wmy = float(mx), float(my)
            ctx.interaction_mgr.update(_wmx, _wmy)
            ctx.quest_manager.check_progress(ctx.player, ctx.all_cards, ctx)
            
            # 【修复】剧情期间暂停AI系统和战斗系统
            is_story_blocking = ctx.story_ui.is_active or ctx.story_ui.choice_mode
            
            # ══════════════════════════════════════════════════════════════
            # 【核心修复】检测剧情结束时统一释放所有事件NPC
            # 这样不依赖复杂的任务链是否完整播放
            # ══════════════════════════════════════════════════════════════
            if _prev_story_blocking and not is_story_blocking:
                print("[Main] 检测到剧情结束，释放所有事件NPC...")
                event_npcs_released = 0
                for card in ctx.all_cards:
                    if hasattr(card, 'state') and card.state == STATE_EVENT:
                        old_state = card.state
                        card.state = STATE_IDLE
                        card.ai_reason = "剧情结束，恢复正常"
                        event_npcs_released += 1
                        print(f"  释放 {getattr(card, 'name', '?')}: {old_state} -> {card.state}")
                if event_npcs_released > 0:
                    print(f"[Main] 共释放了 {event_npcs_released} 个事件NPC")
                else:
                    print("[Main] 没有需要释放的事件NPC")
                
                # ══════════════════════════════════════════════════════════════
                # 【大宋实况·任务模式】剧情结束后调用清理回调
                # 恢复NPC速度、移除保护标记等
                # ══════════════════════════════════════════════════════════════
                if hasattr(ctx, '_pending_event_cleanup') and ctx._pending_event_cleanup:
                    try:
                        ctx._pending_event_cleanup()
                    except Exception as e:
                        print(f"[Main] 事件清理回调失败: {e}")
                    finally:
                        ctx._pending_event_cleanup = None  # 清除回调，避免重复执行
            
            # 更新状态追踪
            _prev_story_blocking = is_story_blocking
            
            if ctx.event_manager.time_speed > 0 and not is_story_blocking:
                perf.begin('ai_system')  # 【性能监控】
                ctx.ai_system.update(ctx.all_cards, ctx.world_map, dt_ms=dt)
                perf.end('ai_system')
                
                perf.begin('combat_system')  # 【性能监控】
                ctx.combat_manager.update(ctx.all_cards, ctx.world_map)
                perf.end('combat_system')
                
                # ══════════════════════════════════════════════════════════════
                # 【阶层系统】检测玩家是否被护卫拦截
                # 护卫在 ai_system._process_see 中设置 player._intercepted_by
                # ══════════════════════════════════════════════════════════════
                if hasattr(ctx.player, '_intercepted_by') and ctx.player._intercepted_by:
                    guard = ctx.player._intercepted_by
                    leader = getattr(ctx.player, '_intercept_leader', None)
                    
                    # 保存拦截信息到 ctx
                    ctx.intercept_guard = guard
                    ctx.intercept_leader = leader
                    
                    # 清除标记
                    ctx.player._intercepted_by = None
                    ctx.player._intercept_leader = None
                    
                    # 切换到护卫拦截界面
                    ctx.current_state = GAME_STATE_GUARD_INTERCEPT
                    ctx.event_manager.request_interaction_pause()
                    log_game_event(f"[阶层] 护卫 {guard.name} 拦截玩家靠近 {leader.name if leader else '?'}", tag="SOCIAL")
                
                # [!]【新手任务2】检测NPC是否被击败（通用）
                for card in ctx.all_cards:
                    if getattr(card, '_defeat_trigger_quest', False):
                        # 清除标记，避免重复触发
                        card._defeat_trigger_quest = False
                        npc_name = getattr(card, 'name', 'unknown')
                        
                        # 设置通用击败标记（供任务系统检查）
                        ctx.quest_manager.set_flag(f'defeated_{npc_name}', True)
                        log_game_event(f"[QUEST] 主循环检测到 {npc_name} 被击败，设置任务标记", tag="QUEST")
                        
                        # 特殊处理：黑风大王
                        if '黑风大王' in npc_name:
                            ctx.quest_manager.set_flag('bully_bounty_active', False)
                            ctx.quest_manager.set_flag('bully_defeated', True)
                            # 如果当前任务是 Q_BOUNTY_CANCEL（悬赏取消），自动推进到 Q_BULLY_DEFEATED 并播放对话
                            if ctx.quest_manager.active_quest_id == 'Q_BOUNTY_CANCEL':
                                ctx.quest_manager.advance_quest()  # 推进到 Q_BULLY_DEFEATED
                                # 播放击败恶霸的对话
                                dialogs = ctx.quest_manager.get_dialog('Q_BULLY_DEFEATED')
                                if dialogs:
                                    ctx.story_ui.start_dialog(dialogs)
                                    log_game_event(f"[QUEST] 自动播放击败恶霸对话", tag="QUEST")
                        
                        # 特殊处理：泼皮牛二（复仇任务）
                        elif '泼皮牛二' in npc_name or '泼皮' in npc_name:
                            ctx.quest_manager.set_flag('revenge_complete', True)
                            # 如果当前任务是击败泼皮任务，自动推进并播放对话
                            if ctx.quest_manager.active_quest_id == 'Q_DEFEAT_BULLY':
                                # 先播放击败胜利对话
                                dialogs = ctx.quest_manager.get_dialog('Q_DEFEAT_BULLY_END')
                                if dialogs:
                                    ctx.story_ui.start_dialog(dialogs)
                                    log_game_event(f"[QUEST] 自动播放击败泼皮对话", tag="QUEST")
                                # 然后推进任务
                                ctx.quest_manager.advance_quest()
                        break
            
            # 【阶段4】势力战争系统更新
            if ctx.event_manager.time_speed > 0 and hasattr(ctx, 'faction_war'):
                # 更新控制点状态
                ctx.faction_war.update_control_points(ctx.all_cards)
                # 检测敌对组织遭遇战斗（传入ft_manager和ai_system）
                ctx.faction_war.check_hostile_encounters(ctx.all_cards, ctx.combat_manager, ctx.ft_manager, ctx.ai_system)
            
            # ══════════════════════════════════════════════════════════════
            # 【大宋实况·任务模式】检测玩家是否到达事件地点
            # ══════════════════════════════════════════════════════════════
            if hasattr(ctx, '_check_event_arrival') and ctx._check_event_arrival:
                ctx._check_event_arrival()  # 检测并触发对话
            
            # ══════════════════════════════════════════════════════════════════════
            # 【大宋实况】导演系统 + 新闻事件生成
            # 导演系统优先（LLM模式），否则回退到本地种子生成
            # 【注意】主线剧情进行中不自动触发事件
            # ══════════════════════════════════════════════════════════════════════
            if ctx.event_manager.time_speed > 0 and hasattr(ctx, 'director'):
                # 检查是否处于主线剧情中（主线进行中则跳过自动事件生成）
                is_in_main_quest = False
                if hasattr(ctx, 'quest_manager') and ctx.quest_manager:
                    # 如果还没到自由模式，或者剧情UI正在播放，都视为主线进行中
                    qm = ctx.quest_manager
                    if qm.active_quest_id != "Q_FREE_PLAY":
                        is_in_main_quest = True
                    # 另外检查剧情UI是否激活
                    story_ui = getattr(ctx, 'story_ui', None)
                    if story_ui and getattr(story_ui, 'is_active', False):
                        is_in_main_quest = True
                
            
            # 时间推进
            is_story_active = ctx.story_ui.is_active
            is_choice_active = ctx.story_ui.choice_mode  # 【新增】选择界面时也暂停
            is_snapshot_active = ctx.current_state == GAME_STATE_LIVE_SNAPSHOT  # 【新增】全屏事件面板时暂停
            
            # ══════════════════════════════════════════════════════════════
            # 【核心逻辑】剧情/全屏事件期间：部分或完全暂停游戏逻辑
            # ══════════════════════════════════════════════════════════════
            if ctx.event_manager.time_speed > 0:
                # 【新增】全屏事件面板期间：完全暂停游戏（玩家需要做出选择）
                if is_snapshot_active:
                    # 不更新任何游戏逻辑，等待玩家关闭面板
                    pass
                elif is_story_active or is_choice_active:
                    # 剧情期间：只更新剧情演员的移动和行为
                    story_actors = ctx.story_ui.story_actor_ids
                    story_actor_cards = []
                    for card in ctx.all_cards:
                        card_id = getattr(card, 'id', None)
                        is_player = getattr(card, 'is_player', False)
                        # 玩家始终是剧情演员
                        if is_player or (card_id is not None and card_id in story_actors):
                            story_actor_cards.append(card)
                    
                    # 只更新剧情演员的移动
                    if story_actor_cards:
                        ctx.movement_system.update(story_actor_cards, ctx.world_map, dt_ms=dt)
                        
                        # 【关键修复】剧情期间也要调用剧情演员的 update（执行 action_queue.tick）
                        for card in story_actor_cards:
                            if hasattr(card, 'update'):
                                card.update(ctx.all_cards, ctx.world_map, ctx, dt_ms=dt)
                else:
                    # 非剧情期间：所有人正常更新
                    ticks = ctx.event_manager.time_speed 
                    for _ in range(ticks):
                        # [已禁用] 事件系统暂时关闭，等待重构
                        # ctx.event_manager.update(ctx.all_cards, ctx.player, ctx.world_map, ctx.tech_manager)
                        perf.begin('movement_system')  # 【性能监控】
                        ctx.movement_system.update(ctx.all_cards, ctx.world_map, dt_ms=dt)
                        perf.end('movement_system')

                        # NPC 到达目标建筑后执行堆叠
                        for card in ctx.all_cards[:]:
                            if isinstance(card, NPC) and not card.dragging and not card.stack_parent:
                                card.check_arrival_and_interact(ctx.interaction_mgr, ctx.economy_system, ctx.all_cards)

                    # 统一处理卡牌工作与AI
                    for card in ctx.all_cards[:]:
                        # 堆叠生产逻辑
                        if isinstance(card, Resource) and card.count <= 0:
                            if card.stack_child:
                                
                                card.stack_child.bounce_off(card)
                            ctx.all_cards.remove(card)
                            continue # 已经删除了，跳过后续逻辑
                        
                        if getattr(card, 'recipe_proxy', None):
                            card.work_timer += 1
                            if card.work_timer >= card.work_max:
                                # 完成配方
                                result = card.recipe_proxy.result_callback(card, card.stack_parent, ctx.player)
                                card.recipe_proxy = None
                                card.work_timer = 0
                                card.is_working = False
                                # 处理结果
                                if isinstance(result, str):
                                    ctx.ft_manager.add_text(result, card.rect.x, card.rect.y)
                                elif result: # 是个对象 (Card)
                                    ctx.all_cards.append(result)
                                    ctx.ft_manager.add_text("合成成功!", card.rect.x, card.rect.y, (100,255,100))
                                
                                # 检查原料是否耗尽 (Resource count <= 0)
                                if isinstance(card, Resource) and card.count <= 0:
                                    ctx.all_cards.remove(card)
                        
                        # 检测新配方 (当刚刚堆叠上去，且没有在工作时)
                        elif card.stack_parent and not card.is_working and not getattr(card, 'recipe_proxy', None):
                            # 仅当没有在移动时
                            if not card.dragging:
                                # 🔧 通用队列机制：只有队长才能参与配方，排队的人不参与
                                if hasattr(card, '_is_in_queue_but_not_leader') and card._is_in_queue_but_not_leader():
                                    continue
                                    
                                recipe = ctx.recipe_manager.check_match(card, card.stack_parent)
                                if recipe:
                                    card.recipe_proxy = recipe
                                    card.work_timer = 0
                                    card.work_max = recipe.duration 
                                    card.is_working = True

                                    if isinstance(card, NPC):
                                        card.ai_reason = recipe.name 
                                        card.state = STATE_WORKING

                                    if getattr(card, 'last_recipe_id', None) != recipe.id:
                                        ctx.ft_manager.add_text(f"开始: {recipe.name}", card.rect.x, card.rect.y)
                                    card.last_recipe_id = recipe.id
                        # 玩家手动操作堆叠时候
                        if isinstance(card, NPC) and card.stack_child == ctx.player:
                            card.is_working = True; card.work_timer += 1
                            if card.work_timer >= 60:
                                card.work_timer = 0; card.is_working = False
                                if card.state == STATE_EVENT and card.active_event_data:
                                    ctx.active_event_npc = card; ctx.current_state = GAME_STATE_EVENT_DIALOG
                                else:
                                    #没有事件，单纯触发一次闲聊
                                    ctx.ft_manager.add_text("你好啊！", card.rect.x, card.rect.y - 40, (255, 255, 100))
                                    ctx.player.bounce_off(card)
                                    ctx.active_event_npc = None

                        # ── 玩家背起重伤NPC（重伤NPC → 拖到玩家身上）────────────────
                        # 当玩家是"父卡"，子卡是重伤NPC时，玩家进入背人状态，自动前往医馆
                        if isinstance(card, Player):
                            carried = card.stack_child
                            if carried and isinstance(carried, NPC) and carried.safety == SAFETY_DOWNED:
                                # 玩家在背人，更新显示
                                card.ai_reason = f"背着{carried.name}..."
                                # 找医馆并引导玩家前往（若玩家无主动移动目标则自动设置）
                                if card.target_x is None:
                                    buildings_list = [c for c in ctx.all_cards if isinstance(c, Building)]
                                    clinic = next((b for b in buildings_list if b.building_type == 'CLINIC'), None)
                                    if clinic:
                                        # 若玩家距医馆已经很近，放下伤员
                                        dist_to_clinic = math.hypot(
                                            card.rect.centerx - clinic.rect.centerx,
                                            card.rect.centery - clinic.rect.centery)
                                        if dist_to_clinic < 65:
                                            # 放入医馆堆叠链末端
                                            last_card = clinic
                                            loop_safe = 0
                                            while last_card.stack_child and loop_safe < 20:
                                                last_card = last_card.stack_child
                                                loop_safe += 1
                                            card.stack_child = None
                                            carried.stack_parent = None
                                            last_card.stack_child = carried
                                            carried.stack_parent = last_card
                                            carried.set_pos(last_card.rect.centerx,
                                                            last_card.rect.centery + STACK_OFFSET_Y)
                                            card.ai_reason = "等待指令"
                                            ctx.ft_manager.add_text(
                                                f"已将{carried.name}送入医馆",
                                                card.rect.centerx, card.rect.top - 50,
                                                (100, 255, 150))

                        # NPC 自有Update（传入 dt_ms 让玩家能执行 action_queue）
                        if hasattr(card, 'update'): card.update(ctx.all_cards, ctx.world_map, ctx, dt_ms=dt)         
              
                         

        # 玩家防丢失（使用世界总尺寸）
        wmap = ctx.world_map
        if (ctx.player.rect.right < 0 or ctx.player.rect.left > wmap.w or
                ctx.player.rect.bottom < 0 or ctx.player.rect.top > wmap.h):
            ctx.player.rect.center = ctx.world_map.city_rect.center
            ctx.player.pixel_x, ctx.player.pixel_y = float(ctx.player.rect.x), float(ctx.player.rect.y)
            log_game_event("警告：玩家卡牌迷失，已强制召回！")

        # 摄像机跟随玩家（仅在 follow_player=True 时软跟随，默认自由视角）
        if camera and camera.follow_player:
            camera.focus_on(ctx.player.rect.centerx, ctx.player.rect.centery, smooth=True)

        # 胜负判定 & 日报
        defeat = ctx.player.check_defeat()
        if defeat: ctx.game_result_msg = defeat; ctx.current_state = GAME_STATE_GAME_OVER
        if ctx.event_manager.day_end_flag:
            npc_only = [c for c in ctx.all_cards if isinstance(c, NPC) and c != ctx.player]
            ctx.daily_report_data = ctx.event_manager.process_day_end(ctx.player, npc_only)
            ctx.current_state = GAME_STATE_DAILY_REPORT

        # 更新剧情UI状态
        ctx.story_ui.update()
        ctx.story_ui.update_choice()  # 【新增】更新选择界面动画
        
        # 【新增】更新AI聊天系统
        ctx.chat_integration.update()
        
        # [!] 更新视觉效果系统
        try:
            from src.ui.visual_effects import get_visual_effects
            vfx = get_visual_effects(SCREEN_W, SCREEN_H)
            vfx.update(dt)
        except Exception:
            pass
                
        # --- 渲染 ---
        renderer.render(ctx, mx, my, click_event, current_event)
        
        # [!] 绘制视觉效果（边缘光晕等，在所有UI之上）
        try:
            from src.ui.visual_effects import get_visual_effects
            vfx = get_visual_effects(SCREEN_W, SCREEN_H)
            vfx.draw(screen)
        except Exception:
            pass
        
        # 【新增】绘制AI聊天界面（在其他UI之上）
        ctx.chat_integration.draw(screen)
        
        # ══════════════════════════════════════════════════════════════════════
        # 【大宋实况】绘制右侧事件通知（可点击）
        # ══════════════════════════════════════════════════════════════════════
        if hasattr(ctx, 'event_notification') and ctx.current_state == GAME_STATE_PLAYING:
            ctx.event_notification.update(dt)
            ctx.event_notification.draw(screen)
        
        # ══════════════════════════════════════════════════════════════════════
        # 【大宋实况】实况快照面板（全屏事件展示）
        # ══════════════════════════════════════════════════════════════════════
        if ctx.current_state == GAME_STATE_LIVE_SNAPSHOT and hasattr(ctx, 'snapshot_panel'):
            # 更新快照面板动画
            ctx.snapshot_panel.update(dt)
            # 绘制快照面板（全屏覆盖）
            ctx.snapshot_panel.draw(screen)
        
        # ══════════════════════════════════════════════════════════════════════
        # 【大宋实况】新闻历史面板（按L键打开）
        # ══════════════════════════════════════════════════════════════════════
        if hasattr(ctx, 'live_news_panel') and ctx.live_news_panel.visible:
            ctx.live_news_panel.update(dt)
            ctx.live_news_panel.draw(screen)
        
        # 【新增】在最顶层绘制选择界面（覆盖所有其他UI）
        ctx.story_ui.draw_choice(screen)
        
        # 【性能监控】绘制性能面板并记录帧结束
        perf.draw(screen)
        perf.frame_end(clock.get_fps())

        pygame.display.flip()
        
        # 【新增】检测系统功能菜单的退出请求
        if getattr(ctx, 'request_exit', False):
            running = False
        
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()