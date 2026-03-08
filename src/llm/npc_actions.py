"""
NPC行为库定义 - 区分对话触发和事件触发的行为

=== 设计原则 ===
1. 对话触发行为：只涉及NPC自身动作，不直接修改属性/状态数值
2. 事件触发行为：可以修改NPC属性、游戏状态、触发系统事件
3. 行为分级：即时行为 / 持续行为 / 中断当前行为

=== 行为分类 ===
【可对话触发】- NPC在闲聊中可以自主决定执行的行为
  - 移动类：过来找玩家、跟随玩家、离开、停下
  - 情绪类：表情变化（已通过emotion字段处理）
  - 动作类：挥手、点头、摇头（视觉反馈）

【仅事件触发】- 只有剧情事件/任务系统可以触发的行为
  - 状态类：进入战斗、进入工作、设置繁忙
  - 属性类：修改好感度、修改金钱、修改生命值
  - 系统类：触发任务、添加记忆、传送
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from src.entities.npc import NPC


class ActionTriggerType(Enum):
    """行为触发类型"""
    CHAT = "chat"         # 可在对话中触发
    EVENT = "event"       # 仅事件可触发
    BOTH = "both"         # 两者皆可


class ActionCategory(Enum):
    """行为分类"""
    MOVEMENT = "movement"     # 移动类
    GESTURE = "gesture"       # 动作/手势类
    EMOTION = "emotion"       # 情绪类
    STATE = "state"           # 状态修改类
    ATTRIBUTE = "attribute"   # 属性修改类
    SYSTEM = "system"         # 系统类


@dataclass
class NPCActionDef:
    """NPC行为定义"""
    name: str                           # 行为名称（英文，用于LLM输出）
    display_name: str                   # 显示名称（中文，用于提示词）
    description: str                    # 行为描述
    category: ActionCategory            # 行为分类
    trigger_type: ActionTriggerType     # 触发类型
    requires_target: bool = False       # 是否需要目标
    requires_position: bool = False     # 是否需要位置参数
    interruptible: bool = True          # 是否可被中断
    duration_ms: int = 0                # 预计持续时间（0=即时）


# ═══════════════════════════════════════════════════════════════════
# 行为定义库
# ═══════════════════════════════════════════════════════════════════

NPC_ACTIONS: Dict[str, NPCActionDef] = {
    
    # ─────────────────────────────────────────
    # 移动类 - 可对话触发
    # ─────────────────────────────────────────
    
    "come_to_player": NPCActionDef(
        name="come_to_player",
        display_name="过来找玩家",
        description="NPC移动到玩家身边（需要考虑距离，太远会拒绝）",
        category=ActionCategory.MOVEMENT,
        trigger_type=ActionTriggerType.CHAT,
        requires_target=False,
        interruptible=True,
        duration_ms=5000,
    ),
    
    "follow_player": NPCActionDef(
        name="follow_player",
        display_name="跟随玩家",
        description="NPC开始跟随玩家移动（持续行为，直到被取消）",
        category=ActionCategory.MOVEMENT,
        trigger_type=ActionTriggerType.CHAT,
        requires_target=False,
        interruptible=True,
        duration_ms=-1,  # -1 表示持续
    ),
    
    "stop_following": NPCActionDef(
        name="stop_following",
        display_name="停止跟随",
        description="NPC停止跟随玩家",
        category=ActionCategory.MOVEMENT,
        trigger_type=ActionTriggerType.CHAT,
        requires_target=False,
        interruptible=True,
        duration_ms=0,
    ),
    
    "leave": NPCActionDef(
        name="leave",
        display_name="离开",
        description="NPC转身离开当前位置",
        category=ActionCategory.MOVEMENT,
        trigger_type=ActionTriggerType.CHAT,
        requires_target=False,
        interruptible=True,
        duration_ms=3000,
    ),
    
    "stay": NPCActionDef(
        name="stay",
        display_name="原地等待",
        description="NPC原地不动",
        category=ActionCategory.MOVEMENT,
        trigger_type=ActionTriggerType.CHAT,
        requires_target=False,
        interruptible=True,
        duration_ms=0,
    ),
    
    # ─────────────────────────────────────────
    # 交易/物品类 - 可对话触发（需要好感度判定）
    # ─────────────────────────────────────────
    
    "give_item_to_player": NPCActionDef(
        name="give_item_to_player",
        display_name="赠送物品给玩家",
        description="NPC将自己的物品赠送给玩家（需要好感度足够且有物品）",
        category=ActionCategory.ATTRIBUTE,
        trigger_type=ActionTriggerType.CHAT,
        requires_target=False,
    ),
    
    "give_money_to_player": NPCActionDef(
        name="give_money_to_player",
        display_name="赠送金钱给玩家",
        description="NPC将一些金钱赠送给玩家（需要好感度高且有钱）",
        category=ActionCategory.ATTRIBUTE,
        trigger_type=ActionTriggerType.CHAT,
        requires_target=False,
    ),
    
    "trade_with_player": NPCActionDef(
        name="trade_with_player",
        display_name="与玩家交易",
        description="NPC表示愿意与玩家进行交易",
        category=ActionCategory.SYSTEM,
        trigger_type=ActionTriggerType.CHAT,
        requires_target=False,
    ),
    
    # ─────────────────────────────────────────
    # 好感度类 - 可对话触发（立即生效）
    # ─────────────────────────────────────────
    
    "like_player_more": NPCActionDef(
        name="like_player_more",
        display_name="好感度提升",
        description="NPC对玩家的好感度小幅提升（+5）",
        category=ActionCategory.ATTRIBUTE,
        trigger_type=ActionTriggerType.CHAT,
    ),
    
    "like_player_much": NPCActionDef(
        name="like_player_much",
        display_name="好感度大幅提升",
        description="NPC对玩家的好感度大幅提升（+15）",
        category=ActionCategory.ATTRIBUTE,
        trigger_type=ActionTriggerType.CHAT,
    ),
    
    "dislike_player": NPCActionDef(
        name="dislike_player",
        display_name="好感度下降",
        description="NPC对玩家的好感度下降（-5）",
        category=ActionCategory.ATTRIBUTE,
        trigger_type=ActionTriggerType.CHAT,
    ),
    
    "hate_player": NPCActionDef(
        name="hate_player",
        display_name="好感度大幅下降",
        description="NPC对玩家的好感度大幅下降（-15）",
        category=ActionCategory.ATTRIBUTE,
        trigger_type=ActionTriggerType.CHAT,
    ),
    
    # ─────────────────────────────────────────
    # 战斗/敌对类 - 可对话触发（慎用）
    # ─────────────────────────────────────────
    
    "attack_player": NPCActionDef(
        name="attack_player",
        display_name="攻击玩家",
        description="NPC愤怒地攻击玩家（会引发战斗）",
        category=ActionCategory.STATE,
        trigger_type=ActionTriggerType.CHAT,
        interruptible=False,
    ),
    
    "threaten_player": NPCActionDef(
        name="threaten_player",
        display_name="威胁玩家",
        description="NPC威胁玩家，增加仇恨值但不立即攻击",
        category=ActionCategory.ATTRIBUTE,
        trigger_type=ActionTriggerType.CHAT,
    ),
    
    "call_guards": NPCActionDef(
        name="call_guards",
        display_name="呼叫守卫",
        description="NPC大喊呼叫附近的守卫",
        category=ActionCategory.SYSTEM,
        trigger_type=ActionTriggerType.CHAT,
        duration_ms=2000,
    ),
    
    # ─────────────────────────────────────────
    # 动作/手势类 - 可对话触发
    # ─────────────────────────────────────────
    
    "wave": NPCActionDef(
        name="wave",
        display_name="挥手",
        description="NPC向玩家挥手示意",
        category=ActionCategory.GESTURE,
        trigger_type=ActionTriggerType.CHAT,
        duration_ms=1500,
    ),
    
    "nod": NPCActionDef(
        name="nod",
        display_name="点头",
        description="NPC点头表示同意",
        category=ActionCategory.GESTURE,
        trigger_type=ActionTriggerType.CHAT,
        duration_ms=800,
    ),
    
    "shake_head": NPCActionDef(
        name="shake_head",
        display_name="摇头",
        description="NPC摇头表示拒绝",
        category=ActionCategory.GESTURE,
        trigger_type=ActionTriggerType.CHAT,
        duration_ms=800,
    ),
    
    "bow": NPCActionDef(
        name="bow",
        display_name="行礼",
        description="NPC向玩家行礼",
        category=ActionCategory.GESTURE,
        trigger_type=ActionTriggerType.CHAT,
        duration_ms=1200,
    ),
    
    # ─────────────────────────────────────────
    # 状态修改类 - 仅事件触发
    # ─────────────────────────────────────────
    
    "enter_combat": NPCActionDef(
        name="enter_combat",
        display_name="进入战斗",
        description="NPC进入战斗状态",
        category=ActionCategory.STATE,
        trigger_type=ActionTriggerType.EVENT,
        requires_target=True,
        interruptible=False,
    ),
    
    "start_work": NPCActionDef(
        name="start_work",
        display_name="开始工作",
        description="NPC开始在当前位置工作",
        category=ActionCategory.STATE,
        trigger_type=ActionTriggerType.EVENT,
    ),
    
    "flee": NPCActionDef(
        name="flee",
        display_name="逃跑",
        description="NPC惊慌逃跑",
        category=ActionCategory.STATE,
        trigger_type=ActionTriggerType.EVENT,
        interruptible=False,
        duration_ms=5000,
    ),
    
    "set_idle": NPCActionDef(
        name="set_idle",
        display_name="设为空闲",
        description="NPC进入空闲状态",
        category=ActionCategory.STATE,
        trigger_type=ActionTriggerType.EVENT,
    ),
    
    # ─────────────────────────────────────────
    # 属性修改类 - 仅事件触发
    # ─────────────────────────────────────────
    
    "modify_affinity": NPCActionDef(
        name="modify_affinity",
        display_name="修改好感度",
        description="修改NPC对玩家的好感度",
        category=ActionCategory.ATTRIBUTE,
        trigger_type=ActionTriggerType.EVENT,
    ),
    
    "modify_money": NPCActionDef(
        name="modify_money",
        display_name="修改金钱",
        description="修改NPC的金钱数量",
        category=ActionCategory.ATTRIBUTE,
        trigger_type=ActionTriggerType.EVENT,
    ),
    
    "modify_health": NPCActionDef(
        name="modify_health",
        display_name="修改生命",
        description="修改NPC的生命值",
        category=ActionCategory.ATTRIBUTE,
        trigger_type=ActionTriggerType.EVENT,
    ),
    
    # ─────────────────────────────────────────
    # 系统类 - 仅事件触发
    # ─────────────────────────────────────────
    
    "add_memory": NPCActionDef(
        name="add_memory",
        display_name="添加记忆",
        description="给NPC添加一条记忆",
        category=ActionCategory.SYSTEM,
        trigger_type=ActionTriggerType.EVENT,
    ),
    
    "trigger_quest": NPCActionDef(
        name="trigger_quest",
        display_name="触发任务",
        description="触发一个任务事件",
        category=ActionCategory.SYSTEM,
        trigger_type=ActionTriggerType.EVENT,
    ),
    
    "teleport": NPCActionDef(
        name="teleport",
        display_name="传送",
        description="将NPC传送到指定位置",
        category=ActionCategory.SYSTEM,
        trigger_type=ActionTriggerType.EVENT,
        requires_position=True,
    ),
}


# ═══════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════

def get_chat_available_actions() -> List[NPCActionDef]:
    """获取对话中可用的行为列表"""
    return [
        action for action in NPC_ACTIONS.values() 
        if action.trigger_type in [ActionTriggerType.CHAT, ActionTriggerType.BOTH]
    ]


def get_event_only_actions() -> List[NPCActionDef]:
    """获取仅事件可触发的行为列表"""
    return [
        action for action in NPC_ACTIONS.values() 
        if action.trigger_type == ActionTriggerType.EVENT
    ]


def get_action_prompt_text() -> str:
    """生成供LLM使用的行为列表说明"""
    lines = ["可选行为（在action字段中指定）："]
    
    for action in get_chat_available_actions():
        lines.append(f"  - {action.name}: {action.display_name} - {action.description}")
    
    return "\n".join(lines)


def is_action_valid_for_chat(action_name: str) -> bool:
    """检查行为是否可以在对话中触发"""
    if action_name not in NPC_ACTIONS:
        return False
    action = NPC_ACTIONS[action_name]
    return action.trigger_type in [ActionTriggerType.CHAT, ActionTriggerType.BOTH]


# ═══════════════════════════════════════════════════════════════════
# 行为执行器 - 将LLM的action字符串转换为实际的AtomicAction
# ═══════════════════════════════════════════════════════════════════

class NPCActionExecutor:
    """
    NPC行为执行器
    
    负责：
    1. 解析LLM返回的action字符串
    2. 创建对应的AtomicAction
    3. 加入NPC的行为队列
    """
    
    def __init__(self, ctx=None):
        """
        Args:
            ctx: 游戏上下文，用于获取玩家位置等信息
        """
        self.ctx = ctx
    
    def execute_chat_action(self, npc: 'NPC', action_name: str, 
                            params: Optional[Dict[str, Any]] = None) -> bool:
        """
        执行对话触发的行为
        
        Args:
            npc: 执行行为的NPC
            action_name: 行为名称
            params: 可选参数
            
        Returns:
            bool: 是否成功执行
        """
        if not is_action_valid_for_chat(action_name):
            print(f"[NPCActionExecutor] 行为 {action_name} 不能在对话中触发")
            return False
        
        # 根据行为名称创建对应的AtomicAction
        action = self._create_action(npc, action_name, params or {})
        if action is None:
            print(f"[NPCActionExecutor] 无法创建行为: {action_name}")
            return False
        
        # 加入NPC的行为队列
        if hasattr(npc, 'action_queue'):
            # 清除当前行为，立即执行新行为
            npc.action_queue.clear()
            npc.action_queue.enqueue(action)
            print(f"[NPCActionExecutor] {npc.name} 开始执行: {action_name}")
            return True
        else:
            print(f"[NPCActionExecutor] NPC {npc.name} 没有 action_queue")
            return False
    
    def _create_action(self, npc: 'NPC', action_name: str, 
                       params: Dict[str, Any]):
        """创建AtomicAction实例"""
        from src.atomic_actions import (
            MoveToPosition, FollowTarget, Stay, Wait
        )
        
        if action_name == "come_to_player":
            # 移动到玩家位置
            player = self._get_player()
            if player:
                return MoveToPosition(
                    player.rect.centerx, player.rect.centery,
                    stop_dist=60,
                    reason="走向玩家"
                )
        
        elif action_name == "follow_player":
            # 跟随玩家
            player = self._get_player()
            if player:
                return FollowTarget(
                    target=player,
                    stop_dist=50,
                    start_dist=80,
                    keep_follow=True,
                    reason="跟随玩家"
                )
        
        elif action_name == "stop_following":
            # 停止跟随 = 原地等待
            return Stay(reason="停下")
        
        elif action_name == "leave":
            # 离开 - 向远离玩家的方向移动
            player = self._get_player()
            if player:
                import math
                dx = npc.rect.centerx - player.rect.centerx
                dy = npc.rect.centery - player.rect.centery
                dist = max(1, math.hypot(dx, dy))
                # 向相反方向移动150像素
                tx = npc.rect.centerx + (dx / dist) * 150
                ty = npc.rect.centery + (dy / dist) * 150
                return MoveToPosition(tx, ty, stop_dist=30, reason="离开")
            else:
                # 随机方向
                import random
                angle = random.uniform(0, 6.28)
                import math
                tx = npc.rect.centerx + math.cos(angle) * 150
                ty = npc.rect.centery + math.sin(angle) * 150
                return MoveToPosition(tx, ty, stop_dist=30, reason="离开")
        
        elif action_name == "stay":
            return Stay(reason="原地等待")
        
        elif action_name in ["wave", "nod", "shake_head", "bow"]:
            # 手势类行为 - 目前用等待+显示气泡实现
            duration = NPC_ACTIONS[action_name].duration_ms
            npc._salute_bubble = NPC_ACTIONS[action_name].display_name
            npc._salute_bubble_timer = duration
            return Wait(duration, reason=NPC_ACTIONS[action_name].display_name)
        
        # ─────────────────────────────────────────
        # 好感度类行为
        # ─────────────────────────────────────────
        
        elif action_name == "like_player_more":
            # 好感度小幅提升
            self._modify_affinity(npc, 5)
            npc._salute_bubble = "[爱]"
            npc._salute_bubble_timer = 1000
            return Wait(500, reason="好感度提升")
        
        elif action_name == "like_player_much":
            # 好感度大幅提升
            self._modify_affinity(npc, 15)
            npc._salute_bubble = "[爱爱爱]"
            npc._salute_bubble_timer = 1500
            return Wait(800, reason="好感度大幅提升")
        
        elif action_name == "dislike_player":
            # 好感度下降
            self._modify_affinity(npc, -5)
            npc._salute_bubble = "[怒]"
            npc._salute_bubble_timer = 1000
            return Wait(500, reason="好感度下降")
        
        elif action_name == "hate_player":
            # 好感度大幅下降
            self._modify_affinity(npc, -15)
            npc._salute_bubble = "[怒怒]"
            npc._salute_bubble_timer = 1500
            return Wait(800, reason="好感度大幅下降")
        
        # ─────────────────────────────────────────
        # 物品/金钱类行为
        # ─────────────────────────────────────────
        
        elif action_name == "give_item_to_player":
            # 赠送物品给玩家
            result = self._give_item_to_player(npc)
            if result:
                npc._salute_bubble = f"送你{result}"
                npc._salute_bubble_timer = 2000
                return Wait(1000, reason=f"赠送{result}")
            else:
                npc._salute_bubble = "没东西可送..."
                npc._salute_bubble_timer = 1500
                return Wait(500, reason="没有物品")
        
        elif action_name == "give_money_to_player":
            # 赠送金钱给玩家
            amount = self._give_money_to_player(npc)
            if amount > 0:
                npc._salute_bubble = f"送你{amount}文"
                npc._salute_bubble_timer = 2000
                return Wait(1000, reason=f"赠送{amount}文")
            else:
                npc._salute_bubble = "我也没钱..."
                npc._salute_bubble_timer = 1500
                return Wait(500, reason="没有金钱")
        
        elif action_name == "trade_with_player":
            # 表示愿意交易（目前只是显示提示）
            npc._salute_bubble = "来看看货吧"
            npc._salute_bubble_timer = 2000
            # TODO: 触发交易UI
            return Wait(1000, reason="准备交易")
        
        # ─────────────────────────────────────────
        # 战斗/敌对类行为
        # ─────────────────────────────────────────
        
        elif action_name == "attack_player":
            # 攻击玩家 - 进入战斗状态
            player = self._get_player()
            if player:
                self._start_combat_with_player(npc, player)
                npc._salute_bubble = "找死！"
                npc._salute_bubble_timer = 1000
                return Wait(200, reason="准备战斗")
            return None
        
        elif action_name == "threaten_player":
            # 威胁玩家 - 增加仇恨但不攻击
            player = self._get_player()
            if player:
                self._add_hatred(npc, player.id, 30)
                self._modify_affinity(npc, -10)
                npc._salute_bubble = "你最好给我小心点！"
                npc._salute_bubble_timer = 2000
                return Wait(1000, reason="威胁")
            return Wait(500, reason="威胁")
        
        elif action_name == "call_guards":
            # 呼叫守卫
            self._call_nearby_guards(npc)
            npc._salute_bubble = "来人啊！有贼！"
            npc._salute_bubble_timer = 2500
            return Wait(2000, reason="呼叫守卫")
        
        return None
    
    # ═══════════════════════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════════════════════
    
    def _modify_affinity(self, npc: 'NPC', delta: int):
        """修改NPC对玩家的好感度"""
        player = self._get_player()
        if player and hasattr(npc, 'modify_affinity'):
            npc.modify_affinity(player.id, delta)
            npc.sync_affinity_to_player(player.id)
            print(f"[NPCActionExecutor] {npc.name} 好感度 {'+' if delta > 0 else ''}{delta}")
    
    def _give_item_to_player(self, npc: 'NPC') -> Optional[str]:
        """
        NPC赠送物品给玩家
        
        Returns:
            str: 赠送的物品名称，如果没有物品则返回None
        """
        player = self._get_player()
        if not player:
            return None
        
        # 检查NPC好感度是否足够（需要50以上才愿意送东西）
        # 【修正】从affinity字典获取对玩家的好感度
        affinity = npc.affinity.get(player.id, 0)
        if affinity < 50:
            print(f"[NPCActionExecutor] {npc.name} 好感度不足({affinity})，不愿送东西")
            return None
        
        # 获取NPC的物品（排除金钱）
        inventory = getattr(npc, 'inventory', {})
        from src.definitions import ITEM_COIN
        
        available_items = [(k, v) for k, v in inventory.items() 
                          if k != ITEM_COIN and v > 0]
        
        if not available_items:
            return None
        
        # 随机选一个物品送出
        import random
        item_id, qty = random.choice(available_items)
        
        # 从NPC移除
        npc.inventory[item_id] -= 1
        if npc.inventory[item_id] <= 0:
            del npc.inventory[item_id]
        
        # 给玩家（如果玩家有inventory）
        if hasattr(player, 'inventory'):
            player.inventory[item_id] = player.inventory.get(item_id, 0) + 1
        
        print(f"[NPCActionExecutor] {npc.name} 赠送 {item_id} 给玩家")
        return item_id
    
    def _give_money_to_player(self, npc: 'NPC') -> int:
        """
        NPC赠送金钱给玩家
        
        Returns:
            int: 赠送的金额，如果没有钱则返回0
        """
        player = self._get_player()
        if not player:
            return 0
        
        # 检查NPC好感度
        # 【修正】从affinity字典获取对玩家的好感度
        affinity = npc.affinity.get(player.id, 0)
        if affinity < 30:
            print(f"[NPCActionExecutor] {npc.name} 好感度不足({affinity})，不愿送钱")
            return 0
        
        # 获取NPC的金钱
        from src.definitions import ITEM_COIN
        money = getattr(npc, 'inventory', {}).get(ITEM_COIN, 0)
        
        if money <= 10:
            return 0
        
        # 根据好感度和财富决定送多少
        import random
        if affinity >= 80:
            give_amount = random.randint(int(money * 0.1), int(money * 0.3))
        elif affinity >= 50:
            give_amount = random.randint(10, min(50, money // 4))
        else:
            give_amount = random.randint(5, min(20, money // 5))
        
        give_amount = max(1, give_amount)
        
        # 转移金钱
        npc.inventory[ITEM_COIN] -= give_amount
        if hasattr(player, 'inventory'):
            player.inventory[ITEM_COIN] = player.inventory.get(ITEM_COIN, 0) + give_amount
        
        print(f"[NPCActionExecutor] {npc.name} 赠送 {give_amount}文 给玩家")
        return give_amount
    
    def _start_combat_with_player(self, npc: 'NPC', player):
        """让NPC进入战斗状态并锁定玩家"""
        from src.definitions import STATE_COMBAT
        
        npc.state = STATE_COMBAT
        npc.aggro_target = player
        npc.in_combat = True
        
        # 添加仇恨
        if not hasattr(npc, 'hatred'):
            npc.hatred = {}
        npc.hatred[player.id] = npc.hatred.get(player.id, 0) + 100
        
        print(f"[NPCActionExecutor] {npc.name} 进入战斗，锁定玩家")
    
    def _add_hatred(self, npc: 'NPC', target_id: int, amount: int):
        """增加NPC对目标的仇恨值"""
        if not hasattr(npc, 'hatred'):
            npc.hatred = {}
        npc.hatred[target_id] = npc.hatred.get(target_id, 0) + amount
        print(f"[NPCActionExecutor] {npc.name} 对 #{target_id} 仇恨 +{amount}")
    
    def _call_nearby_guards(self, npc: 'NPC'):
        """呼叫附近的守卫"""
        if not self.ctx:
            return
        
        player = self._get_player()
        if not player:
            return
        
        # 获取所有NPC
        all_cards = getattr(self.ctx, 'all_cards', [])
        
        import math
        from src.definitions import STATE_COMBAT
        
        call_radius = 300  # 呼叫范围（像素）
        guards_called = 0
        
        for card in all_cards:
            if not hasattr(card, 'job'):
                continue
            
            # 只呼叫守卫和士兵
            if card.job not in ['GUARD', 'SOLDIER']:
                continue
            
            # 已经在战斗中的跳过
            if getattr(card, 'state', None) == STATE_COMBAT:
                continue
            
            # 检查距离
            dist = math.hypot(
                card.rect.centerx - npc.rect.centerx,
                card.rect.centery - npc.rect.centery
            )
            
            if dist <= call_radius:
                # 让守卫锁定玩家
                card.aggro_target = player
                card.state = STATE_COMBAT
                card.in_combat = True
                if not hasattr(card, 'hatred'):
                    card.hatred = {}
                card.hatred[player.id] = card.hatred.get(player.id, 0) + 50
                guards_called += 1
                print(f"[NPCActionExecutor] 守卫 {card.name} 响应呼叫")
        
        print(f"[NPCActionExecutor] 呼叫守卫，{guards_called}人响应")
    
    def _get_player(self):
        """获取玩家实体"""
        if self.ctx and hasattr(self.ctx, 'player'):
            return self.ctx.player
        return None


# ═══════════════════════════════════════════════════════════════════
# 距离计算辅助
# ═══════════════════════════════════════════════════════════════════

def calculate_distance_to_player(npc: 'NPC', ctx) -> Optional[float]:
    """
    计算NPC与玩家的距离
    
    Returns:
        float: 距离（像素），如果无法计算返回None
    """
    if not ctx or not hasattr(ctx, 'player'):
        return None
    
    player = ctx.player
    import math
    return math.hypot(
        npc.rect.centerx - player.rect.centerx,
        npc.rect.centery - player.rect.centery
    )


def get_distance_description(distance_px: float) -> str:
    """
    将像素距离转换为游戏内描述
    
    假设：1像素 ≈ 0.5米（可调整）
    """
    if distance_px is None:
        return "未知"
    
    meters = distance_px * 0.5
    
    if meters < 3:
        return "近在咫尺（约1-2步）"
    elif meters < 10:
        return f"很近（约{int(meters)}米）"
    elif meters < 30:
        return f"不远（约{int(meters)}米）"
    elif meters < 60:
        return f"有一段距离（约{int(meters)}米）"
    elif meters < 100:
        return f"比较远（约{int(meters)}米）"
    else:
        return f"很远（约{int(meters)}米以上）"
