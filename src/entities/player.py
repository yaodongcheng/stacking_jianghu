# --- src/entities/player.py ---
import pygame
from src.definitions import *
from src.utils import log_game_event
from .npc import NPC
from .building import Building

class Player(NPC):
    def __init__(self):
        # 构造玩家的基础数据
        player_data = {
            'id': 9999,
            'name': '我',
            'eco_status': ECO_ENOUGH,
            'safety': SAFETY_NORMAL,
            'job': 'PLAYER',
            # 玩家战斗属性 - 比普通平民稍强
            'power_type': '游',      # 江湖人士
            'social_level': 2,       # 中等社会地位
            'org_rank': 0,
        }
        # 初始化父类 NPC
        super().__init__(player_data)
        
        # 【关键】标记为玩家，用于剧情系统识别
        self.is_player = True
        
        # 玩家卡牌特有属性
        self.color = COLOR_PLAYER_CARD
        self.set_pos(400, 300)   # 统一走 set_pos（中心点）
        
        
        # --- 游戏进程控制 ---
        self.day = 1
        self.max_days = 30
        
        # --- 胜利条件目标 ---
        self.fame = 0                    # 江湖善名 (-100 ~ +100)
        self.target_fame = 2000 
        self.target_followers = 5
        self.followers_count = 0
        
        # ═══════════════════════════════════════════════════════════════
        # 【新增】势力与声望系统
        # ═══════════════════════════════════════════════════════════════
        self.player_org_id = None        # 玩家所属组织ID
        self.player_org_rank = 0         # 玩家组织等级 (0=无, 1=门徒, 2=核心, 3=头目, 4=长老, 5=首领)
        self.merit = 0                   # 功勋值（用于晋升）
        self.org_reputation = {}         # {org_id: standing} 各势力声望 (-100 ~ +100)
        
        # 悬赏状态
        self.bounty_value = 0            # 被悬赏金额（0=无悬赏）
        self.bounty_issuer = None        # 悬赏发布者组织ID
        
        # 其他属性
        self.tags = set() 
        self.move_speed = 200.0  # 单位：px/s，每0.05s步长移动10px
        
    def _give_starter_kit(self):
        #初始背包
        self.money = 200 # 初始资金
        return None

    def update(self, all_cards, world_map, ctx, dt_ms=16):
        """
        玩家卡牌的更新逻辑：
        1. 处理重伤状态（禁止操作，等待救援）
        2. 处理鼠标拖拽。
        3. 处理堆叠工作逻辑（Stacklands 核心玩法）。
        4. 执行原子行为队列（剧情动作等）。
        """
        # ═══════════════════════════════════════════════════════════════
        # -1. 执行原子行为队列（剧情攻击等脚本行为）
        # ═══════════════════════════════════════════════════════════════
        if hasattr(self, 'action_queue'):
            self.action_queue.tick(dt_ms)
        
        # ═══════════════════════════════════════════════════════════════
        # 0. 重伤状态检查 - 玩家重伤时无法操作，等待NPC救援
        # ═══════════════════════════════════════════════════════════════
        if self.safety == SAFETY_DOWNED:
            self.state = STATE_DOWNED
            self.dragging = False  # 强制停止拖拽
            self.clear_movement_target("重伤倒地")
            
            # 显示状态
            if self.stack_parent:
                # 正在被救援
                parent_name = getattr(self.stack_parent, 'name', '某人')
                if hasattr(self.stack_parent, 'building_type'):
                    # 在建筑上（医馆等）
                    self.ai_reason = "正在救治..."
                else:
                    # 被人背着
                    self.ai_reason = f"被{parent_name}救援中"
            else:
                self.ai_reason = "重伤倒地！等待救援..."
            return
        
        # 1. 物理拖拽处理（rect 由 update_drag_pos → set_pos 驱动，无需额外同步）

        # 2. 堆叠逻辑处理 (玩家是万能工，可以放在建筑上工作)
        if self.stack_parent:
            pass  # 堆叠位置由 ai_system 的 set_pos 级联驱动，无需手动同步
        else:
            # 没有堆叠父对象，重置工作状态
            self.is_working = False
            self.work_timer = 0
            self.recipe_proxy = None
            
        self._update_survival_stats(all_cards, ctx)
        # 更新状态显示文字
        if self.is_working:
            self.ai_reason = "正在劳作..."
        elif self.dragging:
            self.ai_reason = "被拖拽中"
        else:
            self.ai_reason = "等待指令"

    def check_victory(self):
        """检查是否满足胜利条件"""
        return None

    def check_defeat(self):
       
            
        return None

    def draw(self, screen, font):
        """
        绘制玩家卡牌
        1. 调用父类 NPC 绘制基础卡牌。
        2. 覆盖底部区域，显示核心生存数据（粮/智）。
        """
        # 继承 NPC 的绘制 (头像、边框等)
        super().draw(screen, font)
    def get_display_info(self, ui_manager=None):
        """玩家界面信息"""
        role = "玩家" 
        coins = self.inventory.get(ITEM_COIN, 0)
        info = [
           f"{role} {self.name} ({self.job})",
           f"生命: {self.hp}/{self.max_hp}",
           f"不满: {self.dissatisfaction}/{MAX_DISSATISFACTION}",
           f"饥饿: {self.hunger}%  寒冷: {self.cold}%",
           f"金钱: {coins}{ITEM_COIN}",
           f"武力: {self.atk}  防御: {self.def_}",
           f"门客: {self.followers_count}",
           f"状态: {self.safety}"
        ]
        return info
        