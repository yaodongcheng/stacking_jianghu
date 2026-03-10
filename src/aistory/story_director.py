"""
叙事导演系统 (StoryDirector)

整合所有叙事模块的主控制器。
"""

import asyncio
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

from .dilemma_seed import NPCDilemmaSeed, DilemmaPhase, StoryBeat, Tension
from .dilemma_deriver import DilemmaDeriver, NPCData
from .shared_types import WorldSnapshot
from .rolling_story_generator import RollingStoryGenerator, EventCard, EventChoice
from .phase_evaluator import PhaseEvaluator
from .ripple_engine import RippleEngine, RippleEffect, SocialLink


@dataclass
class DirectorConfig:
    """导演系统配置"""
    max_concurrent_arcs: int = 5          # 最大同时进行的故事弧
    heat_threshold: int = 30               # 热度阈值（超过才考虑推进）
    min_beat_interval: int = 3             # 最小节拍间隔（游戏内天数）
    enable_ripple: bool = True             # 是否启用涟漪效果
    enable_llm: bool = True                # 是否使用LLM


@dataclass
class ActiveArc:
    """活跃的故事弧"""
    npc_id: str
    seed: NPCDilemmaSeed
    npc_data: NPCData
    last_update: datetime = field(default_factory=datetime.now)
    is_paused: bool = False


class StoryDirector:
    """
    叙事导演系统
    
    职责：
    1. 管理所有NPC的困境种子
    2. 决定哪个NPC的故事应该推进
    3. 协调各模块生成下一个故事节拍
    4. 处理玩家选择并传播涟漪效果
    5. 管理招募逻辑
    """
    
    def __init__(self, llm_service=None, config: DirectorConfig = None):
        self.config = config or DirectorConfig()
        self.llm = llm_service
        
        # 子模块
        self.deriver = DilemmaDeriver(llm_service)
        self.generator = RollingStoryGenerator(llm_service)
        self.evaluator = PhaseEvaluator(llm_service)
        self.ripple = RippleEngine(llm_service)
        
        # 状态
        self.seeds: Dict[str, NPCDilemmaSeed] = {}      # npc_id -> seed
        self.active_arcs: Dict[str, ActiveArc] = {}     # npc_id -> arc
        self.npc_data: Dict[str, NPCData] = {}          # npc_id -> data
        self.world_state: Optional[WorldSnapshot] = None
        
        # 历史记录
        self.choice_history: List[Dict] = []            # 玩家选择历史
    
    def register_npc(self, npc: NPCData) -> NPCDilemmaSeed:
        """注册NPC到导演系统"""
        self.npc_data[npc.npc_id] = npc
        
        # 创建困境种子
        seed = NPCDilemmaSeed(
            npc_id=npc.npc_id,
            phase=DilemmaPhase.LATENT
        )
        self.seeds[npc.npc_id] = seed
        
        return seed
    
    async def initialize_npc_tensions(self, npc_id: str, 
                                      world_state: WorldSnapshot) -> bool:
        """初始化NPC的张力"""
        if npc_id not in self.npc_data:
            return False
        
        npc = self.npc_data[npc_id]
        seed = self.seeds[npc_id]
        
        # 推导张力
        tensions = await self.deriver.derive_tensions(npc, world_state)
        seed.tensions = tensions
        
        # 计算初始热度
        seed.heat = self.deriver.calculate_heat(seed, world_state)
        
        print(f"[StoryDirector] {npc.name} 初始化完成，"
              f"张力数: {len(tensions)}, 热度: {seed.heat}")
        
        return True
    
    async def select_next_arc(self, 
                              world_state: WorldSnapshot) -> Optional[ActiveArc]:
        """
        选择下一个要推进的故事弧
        
        策略：
        1. 热度最高的NPC优先
        2. 考虑与玩家的距离
        3. 避免同时进行太多弧
        """
        # 检查是否已达上限
        active_count = len([a for a in self.active_arcs.values() 
                           if not a.is_paused])
        if active_count >= self.config.max_concurrent_arcs:
            return None
        
        # 筛选候选NPC
        candidates = []
        for npc_id, seed in self.seeds.items():
            # 跳过已完成或暂停的
            if seed.phase == DilemmaPhase.AFTERMATH:
                continue
            if npc_id in self.active_arcs and self.active_arcs[npc_id].is_paused:
                continue
            
            # 检查热度阈值
            if seed.heat < self.config.heat_threshold:
                continue
            
            npc = self.npc_data[npc_id]
            
            # 重新计算热度
            seed.heat = self.deriver.calculate_heat(seed, world_state)
            
            candidates.append((npc_id, seed.heat, npc))
        
        if not candidates:
            return None
        
        # 按热度排序
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # 选择热度最高的
        selected_id, heat, npc = candidates[0]
        
        # 创建或获取活跃弧
        if selected_id in self.active_arcs:
            arc = self.active_arcs[selected_id]
        else:
            arc = ActiveArc(
                npc_id=selected_id,
                seed=self.seeds[selected_id],
                npc_data=npc
            )
            self.active_arcs[selected_id] = arc
        
        return arc
    
    async def generate_next_beat(self, 
                                  npc_id: str,
                                  world_state: WorldSnapshot) -> Optional[EventCard]:
        """
        为指定NPC生成下一个故事节拍
        
        流程：
        1. 评估当前阶段
        2. 生成事件卡片
        3. 更新种子状态
        """
        if npc_id not in self.npc_data or npc_id not in self.seeds:
            return None
        
        npc = self.npc_data[npc_id]
        seed = self.seeds[npc_id]
        
        # 1. 评估阶段
        new_phase = await self.evaluator.evaluate_phase(seed, npc)
        if new_phase != seed.phase:
            print(f"[StoryDirector] {npc.name} 阶段变化: "
                  f"{seed.phase.value} -> {new_phase.value}")
            seed.phase = new_phase
        
        # 2. 生成事件
        from .rolling_story_generator import PlayerData
        player = PlayerData()  # 可以从world_state或ctx获取玩家数据
        event_card = await self.generator.generate_next_beat(
            npc, seed, world_state, player
        )
        
        if event_card:
            # 记录待处理的选择
            seed.pending_event = event_card
            print(f"[StoryDirector] 为 {npc.name} 生成事件: {event_card.title}")
        
        return event_card
    
    async def process_player_choice(self,
                                    npc_id: str,
                                    choice_index: int,
                                    world_state: WorldSnapshot) -> Dict:
        """
        处理玩家选择
        
        流程：
        1. 记录选择
        2. 创建故事节拍
        3. 应用直接后果
        4. 传播涟漪效果
        5. 检查阶段推进
        6. 检查招募资格
        
        Returns:
            处理结果字典
        """
        if npc_id not in self.npc_data or npc_id not in self.seeds:
            return {"success": False, "error": "NPC not found"}
        
        npc = self.npc_data[npc_id]
        seed = self.seeds[npc_id]
        
        if not seed.pending_event:
            return {"success": False, "error": "No pending event"}
        
        event = seed.pending_event
        if choice_index < 0 or choice_index >= len(event.choices):
            return {"success": False, "error": "Invalid choice index"}
        
        choice = event.choices[choice_index]
        
        # 1. 记录选择历史
        self.choice_history.append({
            "npc_id": npc_id,
            "npc_name": npc.name,
            "event_title": event.title,
            "choice_text": choice.text,
            "timestamp": datetime.now()
        })
        
        # 2. 创建故事节拍
        beat = StoryBeat(
            beat_number=len(seed.story_beats) + 1,
            phase=seed.phase,
            event_summary=event.description,
            player_choice=choice.text,
            consequence_summary=choice.consequence,
            heat_delta=choice.heat_delta
        )
        seed.story_beats.append(beat)
        seed.pending_event = None
        
        # 3. 应用直接后果到NPC
        self._apply_direct_consequences(npc, choice)
        
        # 4. 传播涟漪效果
        ripples = []
        if self.config.enable_ripple:
            all_npcs = list(self.npc_data.values())
            ripples = await self.ripple.propagate(
                npc, seed, choice.text, choice.consequence, all_npcs
            )
            
            # 应用涟漪
            for ripple in ripples:
                if ripple.target_npc_id in self.seeds:
                    target_seed = self.seeds[ripple.target_npc_id]
                    target_npc = self.npc_data[ripple.target_npc_id]
                    self.ripple.apply_ripple(ripple, target_seed, target_npc)
        
        # 5. 更新热度
        seed.heat = max(0, min(100, seed.heat + choice.heat_delta))
        
        # 6. 检查是否进入AFTERMATH
        aftermath_triggered = False
        if self.evaluator.should_enter_aftermath(seed):
            seed.phase = DilemmaPhase.AFTERMATH
            aftermath_triggered = True
            print(f"[StoryDirector] {npc.name} 进入AFTERMATH阶段")
        
        # 7. 检查招募资格
        recruitment_offered = False
        if seed.phase == DilemmaPhase.AFTERMATH:
            recruitment_offered = self.evaluator.check_recruitment_eligible(seed)
            if recruitment_offered:
                print(f"[StoryDirector] {npc.name} 满足招募条件！")
        
        return {
            "success": True,
            "beat_created": beat,
            "ripples": ripples,
            "aftermath_triggered": aftermath_triggered,
            "recruitment_offered": recruitment_offered,
            "new_phase": seed.phase.value
        }
    
    def _apply_direct_consequences(self, npc: NPCData, choice: EventChoice):
        """应用选择的直接后果到NPC"""
        # 解析effect字符串（简单实现）
        # 格式示例: "emotion:-10,wealth:-50"
        if not choice.effect:
            return
        
        try:
            for part in choice.effect.split(','):
                if ':' in part:
                    stat, val = part.split(':')
                    stat = stat.strip()
                    val = int(val.strip())
                    
                    if hasattr(npc, stat):
                        current = getattr(npc, stat)
                        new_val = max(0, min(100, current + val))
                        setattr(npc, stat, new_val)
        except Exception as e:
            print(f"[StoryDirector] 应用后果失败: {e}")
    
    def register_social_link(self, link: SocialLink):
        """注册社交关系"""
        self.ripple.register_social_link(link)
    
    def get_npc_story_status(self, npc_id: str) -> Optional[Dict]:
        """获取NPC故事状态"""
        if npc_id not in self.seeds:
            return None
        
        seed = self.seeds[npc_id]
        npc = self.npc_data.get(npc_id)
        
        return {
            "npc_name": npc.name if npc else "Unknown",
            "phase": seed.phase.value,
            "heat": seed.heat,
            "beat_count": len(seed.story_beats),
            "tensions": [
                {"a": t.force_a, "b": t.force_b, "intensity": t.intensity}
                for t in seed.tensions
            ],
            "is_recruitable": seed.phase == DilemmaPhase.AFTERMATH and \
                             self.evaluator.check_recruitment_eligible(seed)
        }
    
    def get_all_active_stories(self) -> List[Dict]:
        """获取所有活跃故事的状态"""
        return [
            self.get_npc_story_status(npc_id)
            for npc_id in self.active_arcs.keys()
        ]
    
    def pause_arc(self, npc_id: str):
        """暂停故事弧"""
        if npc_id in self.active_arcs:
            self.active_arcs[npc_id].is_paused = True
    
    def resume_arc(self, npc_id: str):
        """恢复故事弧"""
        if npc_id in self.active_arcs:
            self.active_arcs[npc_id].is_paused = False
    
    async def tick(self, world_state: WorldSnapshot) -> List[Dict]:
        """
        导演系统心跳
        
        每游戏日调用一次，决定推进哪些故事。
        
        Returns:
            本tick生成的事件列表
        """
        self.world_state = world_state
        events = []
        
        # 1. 选择下一个故事弧
        arc = await self.select_next_arc(world_state)
        if not arc:
            return events
        
        # 2. 生成事件
        event = await self.generate_next_beat(arc.npc_id, world_state)
        if event:
            events.append({
                "npc_id": arc.npc_id,
                "npc_name": arc.npc_data.name,
                "event": event
            })
        
        return events