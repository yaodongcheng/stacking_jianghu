"""
大宋实况 - AI叙事导演系统集成示例

展示如何将新的StoryDirector整合到主游戏循环中。
"""

import asyncio
from typing import Optional, Dict, List
from datetime import datetime

# 从aistory包导入
from src.aistory import (
    StoryDirector, DirectorConfig,
    NPCData, WorldSnapshot, DilemmaPhase,
    SocialLink
)

# 从旧系统导入
from src.director_system import AIDirector, get_director as get_old_director


class AistoryBridge:
    """
    新旧导演系统之间的桥梁
    
    职责：
    1. 将旧系统的世界状态转换为新系统格式
    2. 协调两个系统的运行
    3. 逐步迁移功能到新系统
    """
    
    def __init__(self, ctx, llm_service=None):
        self.ctx = ctx
        self.llm = llm_service
        
        # 新导演系统
        config = DirectorConfig(
            max_concurrent_arcs=3,      # 最多同时3个故事弧
            heat_threshold=25,           # 热度阈值
            min_beat_interval=2,         # 最小2天间隔
            enable_ripple=True,          # 启用涟漪效果
            enable_llm=True              # 使用LLM
        )
        self.new_director = StoryDirector(llm_service, config)
        
        # 旧导演系统（保留用于兼容）
        self.old_director: Optional[AIDirector] = None
        
        # 状态
        self._initialized = False
        self._npc_id_map: Dict[int, str] = {}  # card.id -> npc_id
    
    async def initialize(self):
        """初始化桥梁，注册所有NPC"""
        if self._initialized:
            return
        
        # 获取旧导演实例
        self.old_director = get_old_director()
        
        # 从游戏上下文获取所有NPC（排除建筑和玩家）
        all_cards = getattr(self.ctx, 'all_cards', [])
        
        for card in all_cards:
            # 跳过玩家
            if getattr(card, 'is_player', False):
                continue
            # 跳过已死亡或流放的
            if getattr(card, 'safety', '') in ['DEAD', 'EXILED']:
                continue
            # 跳过非NPC对象（如Building建筑）
            if not hasattr(card, 'id') or not hasattr(card, 'name'):
                continue
            # 跳过建筑对象（建筑通常有building_type属性）
            if hasattr(card, 'building_type'):
                continue
            
            # 转换为新格式
            npc_data = self._convert_npc(card)
            
            # 注册到新导演
            self.new_director.register_npc(npc_data)
            self._npc_id_map[card.id] = npc_data.npc_id
        
        print(f"[AistoryBridge] 已注册 {len(self._npc_id_map)} 个NPC到新导演系统")
        self._initialized = True
    
    def _convert_npc(self, card):
        """将游戏NPC对象转换为aistory可用的格式
        
        现在直接使用NPC对象的to_aistory_format()方法
        """
        # 确保NPC对象有必要的属性映射（用于兼容aistory模块的访问方式）
        if not hasattr(card, 'npc_id'):
            card.npc_id = str(card.id)
        if not hasattr(card, 'identity'):
            card.identity = card.job
        if not hasattr(card, 'org'):
            card.org = card.org_id if card.org_id != 'NONE' else ''
        if not hasattr(card, 'wealth'):
            card.wealth = card.money
        
        # 确保有性格相关的方法
        if not hasattr(card, 'get_personality_profile'):
            # 使用默认实现（如果NPC类没有这些方法）
            card.get_personality_profile = lambda: getattr(card, 'desc', '') or "性格信息暂无"
        if not hasattr(card, 'get_behavior_tendency'):
            card.get_behavior_tendency = lambda: {
                'risk_taking': False, 'pragmatic': False, 'loyal': False,
                'temper_hot': False, 'temper_calm': False, 'ambitious': False, 'content': False
            }
        if not hasattr(card, 'get_personality_description'):
            card.get_personality_description = lambda: {}
        
        return card
    
    def _create_world_snapshot(self) -> WorldSnapshot:
        """从游戏上下文创建世界快照"""
        # 使用旧系统的WorldObserver
        if self.old_director:
            old_snapshot = self.old_director.observer.observe(self.ctx)
            # 转换为新格式（字段兼容，可以直接使用）
            return old_snapshot
        
        # 备用：创建基本快照
        return WorldSnapshot(timestamp=datetime.now().timestamp())
    
    async def tick(self) -> List[Dict]:
        """
        每游戏日调用 - 推进叙事
        
        Returns:
            生成的事件列表
        """
        if not self._initialized:
            await self.initialize()
        
        # 创建世界快照
        world_state = self._create_world_snapshot()
        
        # 调用新导演系统
        events = await self.new_director.tick(world_state)
        
        # 同时调用旧导演系统（保持兼容）
        if self.old_director:
            old_event = await self.old_director.generate_live_event(self.ctx)
            if old_event:
                print(f"[AistoryBridge] 旧系统生成事件: {old_event.get('title', 'Unknown')}")
        
        return events
    
    async def process_player_choice(self, npc_id: str, choice_index: int) -> Dict:
        """
        处理玩家对事件的选择
        
        Args:
            npc_id: NPC ID
            choice_index: 选择的选项索引
        
        Returns:
            处理结果
        """
        world_state = self._create_world_snapshot()
        return await self.new_director.process_player_choice(
            npc_id, choice_index, world_state
        )
    
    def get_npc_story_status(self, card_id: int) -> Optional[Dict]:
        """获取NPC的故事状态"""
        npc_id = self._npc_id_map.get(card_id)
        if not npc_id:
            return None
        return self.new_director.get_npc_story_status(npc_id)
    
    def get_all_active_stories(self) -> List[Dict]:
        """获取所有活跃故事"""
        return self.new_director.get_all_active_stories()
    
    def register_social_link(self, source_card_id: int, target_card_id: int, 
                            relation_type: str, strength: int):
        """注册社交关系"""
        source_npc_id = self._npc_id_map.get(source_card_id)
        target_npc_id = self._npc_id_map.get(target_card_id)
        
        if source_npc_id and target_npc_id:
            link = SocialLink(
                source_id=source_npc_id,
                target_id=target_npc_id,
                relation_type=relation_type,
                strength=strength
            )
            self.new_director.register_social_link(link)


# 全局实例
_bridge_instance: Optional[AistoryBridge] = None


def get_aistory_bridge(ctx=None, llm_service=None) -> AistoryBridge:
    """获取AistoryBridge单例"""
    global _bridge_instance
    if _bridge_instance is None and ctx is not None:
        _bridge_instance = AistoryBridge(ctx, llm_service)
    return _bridge_instance


# ============ 使用示例 ============

async def example_usage():
    """使用示例"""
    
    # 假设在游戏主循环中
    # from src.game_context import get_context
    # ctx = get_context()
    # bridge = get_aistory_bridge(ctx, llm_service)
    
    # 每日tick
    # events = await bridge.tick()
    # for event in events:
    #     print(f"新事件: {event['npc_name']} - {event['event'].title}")
    #     # 显示给玩家...
    
    # 玩家做出选择后
    # result = await bridge.process_player_choice(npc_id, choice_index)
    # if result['recruitment_offered']:
    #     print("NPC申请加入！")
    
    pass


if __name__ == "__main__":
    # 测试代码
    print("AI叙事导演系统集成模块")
    print("运行示例: python -m src.aistory_integration")
