"""
叙事导演系统 (StoryDirector)

整合所有叙事模块的主控制器。
"""

import asyncio
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

from .dilemma_seed import NPCDilemmaSeed, DilemmaPhase, StoryBeat, Tension
from .dilemma_deriver import DilemmaDeriver
from .shared_types import WorldSnapshot

# 类型别名
from typing import Any
NPCData = Any  # NPC对象或字典
from .rolling_story_generator import RollingStoryGenerator, EventCard, EventChoice
# PlayerData 已移除，直接使用 Player NPC 对象
from .phase_evaluator import PhaseEvaluator
from .ripple_engine import RippleEngine, RippleEffect, SocialLink
from src.utils import log_game_event
from src.context import ctx

@dataclass
class DirectorConfig:
    """导演系统配置"""
    max_concurrent_arcs: int = 2          # 最大同时进行的故事弧
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
    
    # 单例实例
    _instance: Optional['StoryDirector'] = None
    _initialized: bool = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, llm_service=None, config: DirectorConfig = None):
        # 防止重复初始化
        if StoryDirector._initialized:
            return
            
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
        
        StoryDirector._initialized = True
    
    @classmethod
    def get_instance(cls, llm_service=None, config: DirectorConfig = None) -> 'StoryDirector':
        if cls._instance is None:
            cls._instance = cls(llm_service, config)
        return cls._instance
    
    
    def register_npc(self, npc: NPCData) -> NPCDilemmaSeed:
        """注册NPC到导演系统"""
        self.npc_data[npc.id] = npc
        
        # 创建困境种子
        seed = NPCDilemmaSeed(
            id=npc.id,
            phase=DilemmaPhase.LATENT
        )
        self.seeds[npc.id] = seed
        
        return seed
    
    async def initialize_npc_tensions(self, npc_id: str, 
                                      world_state: WorldSnapshot) -> bool:
        """初始化NPC的张力"""

        
        npc = self.npc_data[npc_id]
        seed = self.seeds[npc_id]
        
        if npc_id not in self.npc_data:
            log_game_event(f"[StoryDirector] 错误: NPC {npc.name} 未注册", tag="DIRECTOR")
            return False
        
        npc = self.npc_data[npc_id]
        seed = self.seeds[npc_id]

        log_game_event(f"[StoryDirector] NPC信息: {npc.name}, 类别={npc.power_type}, 职业={npc.job}, 组织={npc.org_id}", tag="DIRECTOR")
        
        # 1. 派生核心矛盾（欲望 vs 阻碍）
        #其实就是基于Npc的性格，计算出Npc的欲望和阻碍是什么，欲望可能是“渴望被认可”，阻碍可能是“社交恐惧”之类的东西
        seed.desire, seed.reality_block = self.deriver._derive_core_conflict(npc)
        log_game_event(f"[StoryDirector] 核心矛盾: 欲望={seed.desire}..., 阻碍={seed.reality_block}...", tag="DIRECTOR")
        
        # 2. 推导张力
        tensions = await self.deriver.derive_tensions(npc, world_state)
        if len(tensions) > 0:
            log_game_event(f"[StoryDirector] 派生张力: {len(tensions)} 个", tag="DIRECTOR")
            for t in tensions:
                log_game_event(f"  -类别 {t.type} 张力: {t.force_a} vs {t.force_b}, 强度={t.intensity}", tag="DIRECTOR")
            seed.tensions = tensions
            seed.heat = self.deriver.calculate_heat(seed, world_state)
            return True
        else:
            log_game_event(f"[StoryDirector] 警告: 未能为 {npc.name} 派生任何张力", tag="DIRECTOR")
            seed.tensions = []
            seed.heat = 0
            return False
        
  
    
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
    
    async def try_to_generate_beat(self, 
                                  npc_id: str,
                                  world_state: WorldSnapshot) -> Optional[EventCard]:
        """
        为指定NPC生成下一个故事节拍
        
        流程：
        1. 评估当前阶段
        2. 生成事件卡片
        3. 更新种子状态
        """
        
        npc = self.npc_data[npc_id]
        seed = self.seeds[npc_id]
        
        # 1. 评估阶段
        new_phase = await self.evaluator.evaluate_phase(seed, npc)
        if new_phase != seed.phase:
            log_game_event(f"[StoryDirector] {npc.name} 阶段变化: {seed.phase.value} -> {new_phase.value}", tag="DIRECTOR")
            seed.phase = new_phase

        log_game_event(f"[StoryDirector] 基于困境和张力生成故事：角色: {npc.name},困境: {seed.desire}，阻碍 {seed.reality_block}, 阶段={seed.phase}, 热度={seed.heat:.1f}", tag="DIRECTOR")
        
        # 从全局 ctx 获取玩家对象       
        player = ctx.player 
        event_card = await self.generator.generate_next_beat(
            npc, seed, world_state, player
        )
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
       
        return events
    @staticmethod
    def trigger_dilemma_test_event(npc, ctx):
        """
        触发困境测试事件 - 基于NPC的内心隐秘生成AI事件
        
        调用StoryDirector生成基于人生困境的滚动故事事件
        
        Args:
            npc: NPC对象
            ctx: 游戏上下文（必须提供）
        """
        print(f"[DilemmaTest] 触发NPC {npc.name} 的困境测试事件")
        
        if not ctx:
            print("[DilemmaTest] 错误：ctx不能为空")
            return
        
        try:
            # 导入必要的模块
            from src.llm.llm_service import LLMService
            from src.utils import log_game_event
            from .shared_types import WorldSnapshot
            from datetime import datetime
            
            # 获取LLM服务
            llm_service = LLMService.get_instance()
            if not llm_service or not llm_service.is_available():
                log_game_event("[DilemmaTest] 警告：LLM服务不可用，将使用备用方案", tag="DILEMMA")
            else:
                log_game_event("[DilemmaTest] LLM服务已就绪", tag="DILEMMA")
            
            # 获取或创建StoryDirector实例（单例模式）
            director = StoryDirector.get_instance(llm_service)
            if not director:
                log_game_event("[DilemmaTest] 错误：无法获取StoryDirector", tag="DILEMMA")
                return
            
            # 使用异步执行器来运行异步代码
            
            async def _async_trigger():
                npc_data = npc
                npc_id = npc_data.id
                
                # 检查NPC是否已注册，如果没有则注册
                if npc_id not in director.npc_data:
                    director.register_npc(npc_data)
                    print(f"[DilemmaTest] 已注册NPC {npc.name} 到StoryDirector")
                
                # 创建世界快照
                world_state = WorldSnapshot(timestamp=datetime.now().timestamp())
                # 可以从ctx获取更多世界状态信息
                if hasattr(ctx, 'all_cards'):
                    world_state.active_npcs = len([c for c in ctx.all_cards 
                                                   if hasattr(c, 'is_player') and not c.is_player])
                # 将玩家对象附加到 world_state
                if hasattr(ctx, 'player'):
                    world_state.player = ctx.player
                
                # 初始化NPC的张力（如果还没有）
                if npc_id not in director.seeds or not director.seeds[npc_id].tensions:
                    await director.initialize_npc_tensions(npc_id, world_state)
                #检查张力是否成功派生
                if not director.seeds[npc_id].tensions or len(director.seeds[npc_id].tensions) == 0:
                    print(f"[DilemmaTest] 警告: 无法为 {npc.name} 派生张力，无法生成事件")                    
                    return None
                
                # 生成下一个故事节拍
                event_card = await director.try_to_generate_beat(npc_id, world_state)
                
                return event_card
            
            # 运行异步任务
            try:
                # 尝试获取当前事件循环
                loop = asyncio.get_running_loop()
                # 如果已经在事件循环中，创建任务
                future = asyncio.ensure_future(_async_trigger())
                # 由于我们在Pygame的主循环中，不能阻塞等待
                # 所以我们设置一个回调来处理结果
                def on_event_generated(fut):
                    try:
                        event_card = fut.result()
                        if event_card:
                            StoryDirector._handle_generated_event_static(npc, event_card, ctx)
                        else:
                            print(f"[DilemmaTest] 未能生成事件")
                            if hasattr(ctx, 'ft_manager') and ctx.ft_manager:
                                ctx.ft_manager.add_text(
                                    f"[AI] 暂时无法生成事件",
                                    npc.rect.centerx, npc.rect.top - 50, (255, 200, 100)
                                )
                    except Exception as e:
                        print(f"[DilemmaTest] 生成事件时出错: {e}")
                        import traceback
                        traceback.print_exc()
                
                future.add_done_callback(on_event_generated)
                
                # 显示正在生成的提示
                if hasattr(ctx, 'ft_manager') and ctx.ft_manager:
                    ctx.ft_manager.add_text(
                        f"[AI] 正在为{npc.name}生成困境事件...",
                        npc.rect.centerx, npc.rect.top - 50, (150, 200, 255)
                    )
                
            except RuntimeError:
                # 没有正在运行的事件循环，创建一个新的
                event_card = asyncio.run(_async_trigger())
                if event_card:
                    StoryDirector._handle_generated_event_static(npc, event_card, ctx)
                else:
                    print(f"[DilemmaTest] 未能生成事件")
                    if hasattr(ctx, 'ft_manager') and ctx.ft_manager:
                        ctx.ft_manager.add_text(
                            f"[AI] 暂时无法生成事件",
                            npc.rect.centerx, npc.rect.top - 50, (255, 200, 100)
                        )
                
        except Exception as e:
            print(f"[DilemmaTest] 错误: {e}")
            import traceback
            traceback.print_exc()
    
    @staticmethod
    def _handle_generated_event_static(npc, event_card, ctx):
        """处理生成的事件卡片（静态版本）"""
        print(f"[DilemmaTest] 成功生成事件: {event_card.title}")
        print(f"[DilemmaTest] 事件描述: {event_card.description}")
        print(f"[DilemmaTest] 选项数: {len(event_card.choices)}")
        
        # 显示浮动提示
        if hasattr(ctx, 'ft_manager') and ctx.ft_manager:
            ctx.ft_manager.add_text(
                f"[AI] {npc.name}的困境事件已生成!",
                npc.rect.centerx, npc.rect.top - 50, (100, 255, 150)
            )
        
        # 显示事件对话框
        StoryDirector._show_dilemma_event_dialog_static(npc, event_card)
    
    def _handle_generated_event(self, npc, event_card, ctx):
        """处理生成的事件卡片（实例版本，供内部使用）"""
        print(f"[DilemmaTest] 成功生成事件: {event_card.title}")
        print(f"[DilemmaTest] 事件描述: {event_card.description}")
        print(f"[DilemmaTest] 选项数: {len(event_card.choices)}")
        
        # 存储待处理的事件，供后续显示
        if not hasattr(self, '_pending_dilemma_events'):
            self._pending_dilemma_events = {}
        self._pending_dilemma_events[npc.id] = event_card
        
        # 显示浮动提示
        if hasattr(ctx, 'ft_manager') and ctx.ft_manager:
            ctx.ft_manager.add_text(
                f"[AI] {npc.name}的困境事件已生成!",
                npc.rect.centerx, npc.rect.top - 50, (100, 255, 150)
            )
        
        # 显示事件对话框
        self._show_dilemma_event_dialog(npc, event_card)
    
    @staticmethod
    def _show_dilemma_event_dialog_static(npc, event_card):
        """
        显示困境事件对话框（静态版本）
        
        Args:
            npc: NPC对象
            event_card: EventCard事件卡片
        """
        print(f"[DilemmaTest] 准备显示事件对话框: {event_card.title}")
        
        # 将EventCard转换为游戏内事件格式
        # 这里可以根据需要集成到现有的事件系统中
        # 暂时打印事件信息供调试
        print(f"  标题: {event_card.title}")
        print(f"  描述: {event_card.description}")
        print(f"  情绪基调: {event_card.emotion_tone}")
        print(f"  忽略后果: {event_card.ignore_consequence}")
        print("  选项:")
        for i, choice in enumerate(event_card.choices):
            print(f"    {i+1}. {choice.text}")
            print(f"       代价: {choice.cost}")
            print(f"       后果: {choice.consequence}")
    
    def _show_dilemma_event_dialog(self, npc, event_card):
        """
        显示困境事件对话框（实例版本）
        
        Args:
            npc: NPC对象
            event_card: EventCard事件卡片
        """
        print(f"[DilemmaTest] 准备显示事件对话框: {event_card.title}")
        
        # 将EventCard转换为游戏内事件格式
        # 这里可以根据需要集成到现有的事件系统中
        # 暂时打印事件信息供调试
        print(f"  标题: {event_card.title}")
        print(f"  描述: {event_card.description}")
        print(f"  情绪基调: {event_card.emotion_tone}")
        print(f"  忽略后果: {event_card.ignore_consequence}")
        print("  选项:")
        for i, choice in enumerate(event_card.choices):
            print(f"    {i+1}. {choice.text}")
            print(f"       代价: {choice.cost}")
            print(f"       后果: {choice.consequence}")
