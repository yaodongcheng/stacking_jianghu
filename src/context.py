# --- src/context.py ---
from src.definitions import * 
class GameContext:
    """
    游戏上下文容器，用于在各系统间共享核心数据。
    避免函数调用时传递十几个参数。
    """
    def __init__(self):
        self.screen = None
        self.screen_w = 0
        self.screen_h = 0
        
        # 核心实体
        self.all_cards = []
        self.player = None
        self.world_map = None
        
        # 系统/管理器
        self.event_manager = None
        self.tech_manager = None
        self.quest_manager = None
        self.ui_manager = None
        self.interaction_mgr = None
        self.ft_manager = None
        self.combat_manager = None
        self.ai_system = None
        self.economy_system = None
        self.movement_system = None
        
        # 游戏状态
        self.current_state = GAME_STATE_PLAYING # GAME_STATE_PLAYING
        self.running = True
        self.input_delay = 0  # 核心修改：用于防止点击穿透
        
        # 临时交互数据
        self.intro_played = False
        self.selected_npc = None
        self.active_event_npc = None
        self.active_resource_card = None
        self.active_building = None  # 【建筑面板】当前打开的建筑
        self.daily_report_data = None
        self.game_result_msg = ""
        
        # 【手续费系统】待确认的操作信息
        self.pending_fee_action = None  # {
        #     'user': 操作者(Player/NPC),
        #     'building': 目标建筑,
        #     'fee_info': calculate_usage_fee()返回的字典,
        #     'stack_target': 原堆叠目标(用于确认后继续堆叠),
        #     'dragged_card': 被拖拽的卡牌,
        # }
