"""
传闻系统 (Rumor System)

设计目标：
- 让玩家的行动产生后续影响（名声、仇恨、关系网传播）
- NPC会谈论玩家的行为，传闻会在社交网络中传播
- 传闻影响NPC对玩家的态度、任务触发、势力反应

传闻类型：
1. 战斗传闻：玩家击败了某人、被某人击败
2. 交易传闻：玩家买卖了什么东西
3. 社交传闻：玩家与某人结交/结仇
4. 门派传闻：玩家完成了门派任务、获得晋升
5. 悬赏传闻：玩家被悬赏、悬赏被取消
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class RumorType(Enum):
    """传闻类型"""
    COMBAT_VICTORY = "combat_victory"      # 战斗胜利
    COMBAT_DEFEAT = "combat_defeat"        # 战斗失败
    KILLED_NPC = "killed_npc"              # 杀死某人
    TRADE_EXPENSIVE = "trade_expensive"    # 大额交易
    BEFRIEND = "befriend"                  # 结交好友
    MAKE_ENEMY = "make_enemy"              # 结仇
    ORG_TASK_COMPLETE = "org_task_complete"  # 完成门派任务
    ORG_PROMOTION = "org_promotion"        # 门派晋升
    BOUNTY_POSTED = "bounty_posted"        # 被悬赏
    BOUNTY_CANCELLED = "bounty_cancelled"  # 悬赏取消
    THEFT_SUCCESS = "theft_success"        # 偷窃成功
    THEFT_CAUGHT = "theft_caught"          # 偷窃被抓
    HELP_NPC = "help_npc"                  # 帮助NPC
    BETRAY = "betray"                      # 背叛


@dataclass
class Rumor:
    """单条传闻"""
    rumor_type: RumorType
    subject_id: int          # 主角ID（通常是玩家）
    target_id: Optional[int] # 相关对象ID（被击败的NPC等）
    target_name: str         # 相关对象名字
    org_id: Optional[str]    # 相关组织ID
    
    # 传闻属性
    fame_impact: int = 0     # 对声望的影响
    spread_range: int = 3    # 传播范围（影响多少NPC）
    decay_days: int = 7      # 衰减天数（传闻多久后消失）
    
    # 状态
    created_day: int = 0     # 创建日期
    spread_count: int = 0    # 已传播给多少人
    known_by: List[int] = field(default_factory=list)  # 知道这条传闻的NPC ID列表
    
    # 生成传闻文本
    text_template: str = ""  # 传闻模板
    
    def get_text(self) -> str:
        """生成传闻文本"""
        if self.text_template:
            return self.text_template
        
        # 默认模板
        templates = {
            RumorType.COMBAT_VICTORY: f"听说有人击败了{self.target_name}！",
            RumorType.COMBAT_DEFEAT: f"听说有人被{self.target_name}打败了...",
            RumorType.KILLED_NPC: f"可怕！{self.target_name}被人杀了！",
            RumorType.TRADE_EXPENSIVE: f"有人出手阔绰，花了大价钱！",
            RumorType.BEFRIEND: f"有人和{self.target_name}成了朋友。",
            RumorType.MAKE_ENEMY: f"有人得罪了{self.target_name}！",
            RumorType.ORG_TASK_COMPLETE: f"有人为门派完成了任务。",
            RumorType.ORG_PROMOTION: f"有人在门派中升职了！",
            RumorType.BOUNTY_POSTED: f"有人被悬赏了！小心为妙。",
            RumorType.BOUNTY_CANCELLED: f"悬赏被取消了，不知道发生了什么。",
            RumorType.THEFT_SUCCESS: f"小偷！有人的东西被偷了！",
            RumorType.THEFT_CAUGHT: f"有个小偷被当场抓住了！",
            RumorType.HELP_NPC: f"好心人！有人帮助了{self.target_name}。",
            RumorType.BETRAY: f"有人背叛了{self.target_name}！真是卑鄙！",
        }
        return templates.get(self.rumor_type, "发生了一些事情...")
    
    def is_expired(self, current_day: int) -> bool:
        """检查传闻是否过期"""
        return current_day - self.created_day > self.decay_days


class RumorSystem:
    """传闻系统管理器"""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = RumorSystem()
        return cls._instance
    
    def __init__(self):
        self.rumors: List[Rumor] = []
        self.current_day = 0
        self.max_rumors = 50  # 最大传闻数量
    
    def create_rumor(self, 
                     rumor_type: RumorType,
                     subject_id: int,
                     target_id: Optional[int] = None,
                     target_name: str = "",
                     org_id: Optional[str] = None,
                     fame_impact: int = 0,
                     spread_range: int = 3,
                     decay_days: int = 7,
                     custom_text: str = "") -> Rumor:
        """
        创建一条新传闻
        
        Args:
            rumor_type: 传闻类型
            subject_id: 主角ID
            target_id: 相关对象ID
            target_name: 相关对象名字
            org_id: 相关组织ID
            fame_impact: 声望影响
            spread_range: 传播范围
            decay_days: 衰减天数
            custom_text: 自定义传闻文本
        """
        rumor = Rumor(
            rumor_type=rumor_type,
            subject_id=subject_id,
            target_id=target_id,
            target_name=target_name,
            org_id=org_id,
            fame_impact=fame_impact,
            spread_range=spread_range,
            decay_days=decay_days,
            created_day=self.current_day,
            text_template=custom_text
        )
        
        self.rumors.append(rumor)
        
        # 限制传闻数量
        if len(self.rumors) > self.max_rumors:
            self.rumors = self.rumors[-self.max_rumors:]
        
        return rumor
    
    def spread_rumors(self, all_npcs: list, player):
        """
        传播传闻
        每个游戏周期调用一次，让传闻在NPC之间传播
        
        Args:
            all_npcs: 所有NPC列表
            player: 玩家对象
        """
        from src.entities import NPC
        
        npcs = [n for n in all_npcs if isinstance(n, NPC) and n != player and 
                getattr(n, 'safety', 'NORMAL') not in ['DEAD', 'EXILED']]
        
        if not npcs:
            return
        
        for rumor in self.rumors:
            if rumor.is_expired(self.current_day):
                continue
            
            if rumor.spread_count >= rumor.spread_range:
                continue
            
            # 随机选择一个NPC传播给
            available_npcs = [n for n in npcs if n.id not in rumor.known_by]
            if not available_npcs:
                continue
            
            # 传播概率
            spread_chance = 0.3  # 基础30%传播率
            
            # 重大事件更容易传播
            if rumor.rumor_type in [RumorType.KILLED_NPC, RumorType.BOUNTY_POSTED, 
                                    RumorType.ORG_PROMOTION]:
                spread_chance = 0.6
            
            if random.random() < spread_chance:
                target_npc = random.choice(available_npcs)
                rumor.known_by.append(target_npc.id)
                rumor.spread_count += 1
                
                # 应用传闻影响
                self._apply_rumor_effect(rumor, target_npc, player)
    
    def _apply_rumor_effect(self, rumor: Rumor, npc, player):
        """
        应用传闻对NPC的影响
        
        Args:
            rumor: 传闻对象
            npc: 受影响的NPC
            player: 玩家对象
        """
        # 根据传闻类型调整NPC对玩家的看法
        affinity_change = 0
        
        if rumor.rumor_type == RumorType.COMBAT_VICTORY:
            # 击败敌人，根据NPC与被击败者的关系决定
            if rumor.target_id and hasattr(npc, 'affinity_map'):
                target_affinity = npc.affinity_map.get(rumor.target_id, 0)
                if target_affinity < -20:
                    # NPC不喜欢被击败的人，对玩家好感+
                    affinity_change = 5
                elif target_affinity > 20:
                    # NPC喜欢被击败的人，对玩家好感-
                    affinity_change = -5
        
        elif rumor.rumor_type == RumorType.KILLED_NPC:
            # 杀人总是引起警惕
            affinity_change = -10
            # 如果被杀的是恶人，可能有人暗自高兴
            if rumor.target_id and hasattr(npc, 'hatred'):
                if npc.hatred.get(rumor.target_id, 0) > 50:
                    affinity_change = 10
        
        elif rumor.rumor_type == RumorType.HELP_NPC:
            # 帮助别人，普遍好感
            affinity_change = 3
        
        elif rumor.rumor_type == RumorType.THEFT_CAUGHT:
            # 偷窃被抓，坏名声
            affinity_change = -8
        
        elif rumor.rumor_type == RumorType.BETRAY:
            # 背叛行为，坏名声
            affinity_change = -15
        
        elif rumor.rumor_type == RumorType.BOUNTY_POSTED:
            # 被悬赏，看NPC与悬赏方的关系
            if rumor.org_id and hasattr(npc, 'org_id') and npc.org_id == rumor.org_id:
                affinity_change = -20  # 同门派，对叛徒没好感
        
        # 应用好感度变化
        if affinity_change != 0:
            current = getattr(npc, 'affinity_to_player', 0)
            npc.affinity_to_player = max(-100, min(100, current + affinity_change))
    
    def get_npc_known_rumors(self, npc_id: int) -> List[Rumor]:
        """获取某个NPC知道的所有传闻"""
        return [r for r in self.rumors if npc_id in r.known_by and not r.is_expired(self.current_day)]
    
    def get_recent_rumors(self, count: int = 5) -> List[Rumor]:
        """获取最近的传闻"""
        active = [r for r in self.rumors if not r.is_expired(self.current_day)]
        return active[-count:]
    
    def update_day(self, day: int):
        """更新当前日期"""
        self.current_day = day
        # 清理过期传闻
        self.rumors = [r for r in self.rumors if not r.is_expired(self.current_day)]
    
    def on_player_action(self, action: str, player, target=None, **kwargs):
        """
        玩家行为触发传闻
        
        Args:
            action: 行为类型字符串
            player: 玩家对象
            target: 行为目标（NPC/物品等）
            **kwargs: 额外参数
        """
        target_id = getattr(target, 'id', None) if target else None
        target_name = getattr(target, 'name', '某人') if target else '某人'
        org_id = kwargs.get('org_id')
        
        # 根据行为类型创建传闻
        if action == 'KILL':
            self.create_rumor(
                RumorType.KILLED_NPC,
                player.id, target_id, target_name,
                fame_impact=-20,
                spread_range=10,
                decay_days=14,
                custom_text=f"杀人了！{target_name}被杀害了！"
            )
        
        elif action == 'DEFEAT':
            self.create_rumor(
                RumorType.COMBAT_VICTORY,
                player.id, target_id, target_name,
                fame_impact=5,
                spread_range=5,
                decay_days=7
            )
        
        elif action == 'DEFEATED':
            self.create_rumor(
                RumorType.COMBAT_DEFEAT,
                player.id, target_id, target_name,
                fame_impact=-3,
                spread_range=3,
                decay_days=5
            )
        
        elif action == 'STEAL_SUCCESS':
            self.create_rumor(
                RumorType.THEFT_SUCCESS,
                player.id, target_id, target_name,
                fame_impact=-5,
                spread_range=3,
                decay_days=5
            )
        
        elif action == 'STEAL_CAUGHT':
            self.create_rumor(
                RumorType.THEFT_CAUGHT,
                player.id, target_id, target_name,
                fame_impact=-15,
                spread_range=8,
                decay_days=10,
                custom_text=f"有人偷{target_name}的东西被抓了个现行！"
            )
        
        elif action == 'HELP':
            self.create_rumor(
                RumorType.HELP_NPC,
                player.id, target_id, target_name,
                fame_impact=5,
                spread_range=4,
                decay_days=7,
                custom_text=f"好心人帮助了{target_name}。"
            )
        
        elif action == 'ORG_TASK':
            self.create_rumor(
                RumorType.ORG_TASK_COMPLETE,
                player.id, org_id=org_id,
                target_name='',
                fame_impact=3,
                spread_range=3,
                decay_days=5
            )
        
        elif action == 'ORG_PROMOTION':
            rank_name = kwargs.get('rank_name', '职位')
            self.create_rumor(
                RumorType.ORG_PROMOTION,
                player.id, org_id=org_id,
                target_name='',
                fame_impact=10,
                spread_range=6,
                decay_days=10,
                custom_text=f"有人晋升为{rank_name}了！"
            )
        
        elif action == 'BOUNTY':
            bounty_value = kwargs.get('bounty_value', 0)
            self.create_rumor(
                RumorType.BOUNTY_POSTED,
                player.id, org_id=org_id,
                target_name='',
                fame_impact=-10,
                spread_range=10,
                decay_days=14,
                custom_text=f"悬赏令！{bounty_value}铜捉拿此人！"
            )


# 全局单例
def get_rumor_system() -> RumorSystem:
    return RumorSystem.get_instance()
