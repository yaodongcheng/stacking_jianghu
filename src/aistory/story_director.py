"""
叙事导演系统 (StoryDirector)

整合所有叙事模块的主控制器。
"""

import asyncio
import time
import threading
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src.ui.event_notification import LiveNewsItem

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
            phase=DilemmaPhase.EMERGE
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
        
        # 【重构后】派生核心矛盾（欲望 vs 顾虑）
        # 基于Npc的性格，计算出Npc的欲望和顾虑
        # 欲望可能是"渴望被认可"，顾虑可能是"社交恐惧"之类的东西
        seed.desire, seed.misgiving = self.deriver._derive_core_conflict(npc)
        log_game_event(f"[StoryDirector] 核心矛盾: 渴望={seed.desire}..., 顾虑={seed.misgiving}...", tag="DIRECTOR")
        
        # 【重构后】不再派生 tensions 列表
        # 热度基于NPC的当前状态简单计算
        seed.heat = self._calculate_simple_heat(npc, world_state)
        return True
    
    def _calculate_simple_heat(self, npc, world_state) -> float:
        """简化版热度计算，不再依赖 tensions"""
        base_heat = 30.0  # 基础热度
        
        # 根据NPC状态调整
        if hasattr(npc, 'emotion'):
            if npc.emotion < 30:  # 情绪低落
                base_heat += 20
            elif npc.emotion > 70:  # 情绪高涨（可能冲动）
                base_heat += 10
        
        if hasattr(npc, 'hp_percent') and npc.hp_percent < 0.5:  # 受伤
            base_heat += 15
        
        if hasattr(npc, 'hunger') and npc.hunger > 70:  # 饥饿
            base_heat += 10
        
        return min(100.0, base_heat)
        
  
    
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
            if seed.phase == DilemmaPhase.SETTLE:
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

        log_game_event(f"[StoryDirector] 基于困境生成故事：角色: {npc.name},渴望: {seed.desire[:30] if seed.desire else '待生成'}...，顾虑: {seed.misgiving[:30] if seed.misgiving else '待生成'}..., 阶段={seed.phase}, 热度={seed.heat:.1f}", tag="DIRECTOR")
        
        # 从全局 ctx 获取玩家对象       
        player = ctx.player 
        event_card = await self.generator.generate_next_beat(
            npc, seed, world_state, player
        )
        
        # 【关键】将 LLM 生成的 desire 和 misgiving 保存到 seed，供下一阶段使用
        if event_card and event_card.dilemma_desc:
            if event_card.dilemma_desc.desire:
                seed.desire = event_card.dilemma_desc.desire
            if event_card.dilemma_desc.misgiving:
                seed.misgiving = event_card.dilemma_desc.misgiving
            log_game_event(f"[StoryDirector] 已保存困境描述: desire={seed.desire[:30]}..., misgiving={seed.misgiving[:30]}...", tag="DIRECTOR")
        
        # 将事件保存为待处理事件，供 process_player_choice 使用
        if event_card:
            seed.pending_event = event_card
            log_game_event(f"[StoryDirector] 事件已生成并设置为待处理: {event_card.title[:30]}...", tag="DIRECTOR")
        
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
        
        # 2. 创建故事节拍（完整记录，供后续阶段使用）
        beat = StoryBeat(
            beat_number=len(seed.story_beats) + 1,
            timestamp=datetime.now().isoformat(),
            event_summary=event.title,
            player_choice=choice.text,
            consequence_summary=choice.consequence,
            npc_state_change={},  # 可以后续填充
            tension_delta=choice.tension_delta,
            # 记录完整的困境信息供后续阶段使用
            dilemma_type=event.dilemma_type.value if event.dilemma_type else "",
            event_theme=event.event_theme,
            desire=event.dilemma_desc.desire if event.dilemma_desc else seed.desire,
            misgiving=event.dilemma_desc.misgiving if event.dilemma_desc else seed.misgiving
        )
        seed.story_beats.append(beat)
        log_game_event(f"[StoryDirector] 已记录故事节拍 #{beat.beat_number}: {beat.event_summary[:30]}...", tag="DIRECTOR")
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
        seed.heat = max(0, min(100, seed.heat + choice.tension_delta))
        
            # 6. 检查是否进入SETTLE
        settle_triggered = False
        if self.evaluator.should_enter_settle(seed):
            seed.phase = DilemmaPhase.SETTLE
            settle_triggered = True
            print(f"[StoryDirector] {npc.name} 进入SETTLE阶段")
        
        # 7. 检查招募资格（仅在SETTLE阶段）
        recruitment_offered = False
        if seed.phase == DilemmaPhase.SETTLE:
            recruitment_offered = self.evaluator.check_recruitment_eligible(seed)
            if recruitment_offered:
                print(f"[StoryDirector] {npc.name} 满足招募条件！")
        
        return {
            "success": True,
            "beat_created": beat,
            "ripples": ripples,
            "settle_triggered": settle_triggered,
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
            "desire": seed.desire,
            "misgiving": seed.misgiving,
            "is_recruitable": seed.phase == DilemmaPhase.SETTLE and \
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
                
                # 【关键】确保 seed 存在（像 demo_llm_story.py 一样）
                # desire 和 misgiving 将由 LLM 在生成事件时动态生成
                if npc_id not in director.seeds:
                    from src.aistory.dilemma_seed import NPCDilemmaSeed
                    director.seeds[npc_id] = NPCDilemmaSeed(id=npc_id)
                    print(f"[DilemmaTest] 已为 {npc.name} 创建空的困境种子")
                
                # 【使用 WorldObserver 构建世界快照】
                from src.director_system import WorldObserver
                observer = WorldObserver()
                world_state = observer.observe(ctx)
                
                # 将玩家对象附加到 world_state（供生成器使用）
                if hasattr(ctx, 'player'):
                    world_state.player = ctx.player
                
                # 【重构后】直接生成故事节拍，不再依赖张力系统
                # RollingStoryGenerator 会基于 NPC 的属性和当前阶段直接生成事件
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
        """处理生成的事件卡片（静态版本）- 接入director_system的配图和扩写流程"""
        # 将EventCard转换为LiveNewsItem并接入配图+扩写流程
        StoryDirector._convert_and_start_generation(npc, event_card, ctx)
    
    @staticmethod
    def _convert_and_start_generation(npc, event_card, ctx):
        """
        将EventCard转换为LiveNewsItem，并启动配图+对话扩写流程
        参考director_system.py的_start_parallel_generation实现
        """
        from src.live_news_system import LiveNewsItem, NewsCategory, DilemmaType
        from src.director_system import AIDirector, get_director
        
        print(f"[DilemmaTest] 转换EventCard为LiveNewsItem: {event_card.title}")
        
        # 1. 转换困境类型（与 event_notification.py 中的 DilemmaType 保持一致）
        dilemma_map = {
            'SACRIFICE': DilemmaType.SACRIFICE,
            'BETRAY': DilemmaType.BETRAY,
            'COMPROMISE': DilemmaType.COMPROMISE,
            'DESTRUCTION': DilemmaType.DESTRUCTION,
            'BIAS': DilemmaType.BIAS,
            'MORAL_GREY': DilemmaType.MORAL_GREY,
            'SHORT_VS_LONG': DilemmaType.SHORT_VS_LONG
        }
        dilemma_type = dilemma_map.get(
            event_card.dilemma_type.value if event_card.dilemma_type else '',
            DilemmaType.MORAL_GREY
        )
        
        # 2. 转换选项格式
        choices = []
        for choice in event_card.choices:
            choice_dict = {
                'text': choice.text,
                'requirement': choice.requirement,
                'cost': choice.cost,
                'effect': choice.effect,
                'tension_delta': choice.tension_delta,
                'consequence_preview': choice.consequence_preview
            }
            choices.append(choice_dict)
        
        # 3. 添加"前往处理"按钮作为第一个选项
        choices.insert(0, {
            'text': '前往处理',
            'action': 'START_DIALOG',
            'effect': ''
        })
        
        # 4. 提取演员信息
        actor_ids = []
        actor_names = []
        for actor in event_card.actors:
            actor_ids.append(actor.get('npc_id', ''))
            actor_names.append(actor.get('npc_name', ''))
        
        # 5. 创建LiveNewsItem
        news_item = LiveNewsItem(
            id=f"dilemma_{npc.id}_{int(time.time())}",
            title=event_card.title,
            headline=event_card.description[:50] + '...' if len(event_card.description) > 50 else event_card.description,
            description=event_card.description,
            category=NewsCategory.SOCIAL,
            dilemma_type=dilemma_type,
            actor_ids=actor_ids,
            actor_names=actor_names,
            image_prompt=event_card.image_prompt,
            tags=event_card.tags,
            comments=event_card.comments,
            choices=choices,
            created_at=time.time()
        )
        
        # 6. 保存关联的NPC、EventCard和auto_decay信息供后续使用
        news_item._source_npc = npc
        news_item._source_event_card = event_card
        news_item._auto_decay = {
            'next_phase_preview': event_card.auto_decay.next_phase_preview if event_card.auto_decay else '',
            'auto_effect': event_card.auto_decay.auto_effect if event_card.auto_decay else '',
            'auto_tension_delta': event_card.auto_decay.auto_tension_delta if event_card.auto_decay else 0
        } if event_card.auto_decay else None
        
        print(f"[DilemmaTest] LiveNewsItem创建成功，启动配图+扩写流程")
        
        # 7. 启动并行生成流程（配图+对话扩写）
        StoryDirector._start_parallel_generation_for_dilemma(news_item, ctx)
    
    @staticmethod
    def _start_parallel_generation_for_dilemma(news_item: LiveNewsItem, ctx):
        """
        为困境事件启动并行配图生成+对话扩写
        改编自director_system.py的_start_parallel_generation
        """
        import threading
        import time
        from src.live_news_system import get_live_news_manager
        from src.llm.event_dialog_generator import EventScriptBrief, get_event_dialog_generator
        from src.llm.doubao_image import get_image_generator
        from pathlib import Path
        
        TIMEOUT_IMAGE_GEN = 30  # 图片生成超时时间
        
        log_game_event(f"[DilemmaTest] 并行生成启动: 图片 + 对话扩写", tag="DILEMMA")
        
        news_mgr = get_live_news_manager()
        start_time = time.time()
        max_wait_time = TIMEOUT_IMAGE_GEN
        
        # 使用标志防止重复添加新闻
        news_added = [False]
        image_done = threading.Event()
        dialog_done = threading.Event()
        
        # ═══════════════════════════════════════════════════════════════
        # 任务1：配图生成
        # ═══════════════════════════════════════════════════════════════
        def on_image_ready(surface, path):
            elapsed = time.time() - start_time
            if path:
                news_item._image_path = path
                news_item._image_surface = surface
                log_game_event(f"[DilemmaTest] 配图已就绪({elapsed:.1f}秒): {path}", tag="DILEMMA")
            else:
                news_item._image_path = "placeholder"
                log_game_event(f"[DilemmaTest] 配图生成失败({elapsed:.1f}秒)，使用占位图", tag="DILEMMA")
            image_done.set()
            _try_add_news()
        
        # ═══════════════════════════════════════════════════════════════
        # 任务2：对话扩写
        # ═══════════════════════════════════════════════════════════════
        def generate_dialog():
            try:
                dialog_gen = get_event_dialog_generator()
                if not dialog_gen.is_available():
                    log_game_event("[DilemmaTest] 对话扩写跳过：LLM不可用", tag="DILEMMA")
                    dialog_done.set()
                    return
                
                # 从news_item构建Brief（跳过"前往处理"按钮）
                all_choices = news_item.choices or []
                story_choices = [c for c in all_choices if c.get('action') != 'START_DIALOG']
                
                brief = EventScriptBrief(
                    title=news_item.title,
                    description=news_item.description,
                    choice_a=story_choices[0].get('text', '选项A') if len(story_choices) > 0 else '介入此事',
                    choice_b=story_choices[1].get('text', '选项B') if len(story_choices) > 1 else '静观其变',
                    choice_c=story_choices[2].get('text', '选项C') if len(story_choices) > 2 else '离开现场',
                    context_hint=news_item.headline or news_item.description,
                    image_prompt=news_item.image_prompt
                )
                
                # 提取效果字符串
                effect_a = story_choices[0].get('effect', '') if len(story_choices) > 0 else ''
                effect_b = story_choices[1].get('effect', '') if len(story_choices) > 1 else ''
                effect_c = story_choices[2].get('effect', '') if len(story_choices) > 2 else ''
                
                # NPC名字
                npc_a_name = news_item.actor_names[0] if news_item.actor_names else '当事人甲'
                npc_b_name = news_item.actor_names[1] if len(news_item.actor_names) > 1 else None
                
                log_game_event(f"[DilemmaTest] 对话扩写开始: {npc_a_name} vs {npc_b_name}", tag="DILEMMA")
                
                full_script = dialog_gen.expand_to_full_script(
                    brief=brief,
                    npc_a_name=npc_a_name,
                    npc_b_name=npc_b_name,
                    effect_a=effect_a,
                    effect_b=effect_b,
                    effect_c=effect_c
                )
                
                # 将预生成的剧本挂到news_item上
                news_item._pregen_script = full_script
                elapsed = time.time() - start_time
                log_game_event(f"[DilemmaTest] 对话扩写完成({elapsed:.1f}秒)", tag="DILEMMA")
                
            except Exception as e:
                log_game_event(f"[DilemmaTest] 对话扩写失败: {e}", tag="DILEMMA")
            finally:
                dialog_done.set()
                _try_add_news()
        
        # ═══════════════════════════════════════════════════════════════
        # 汇合：两个任务都完成后添加新闻
        # ═══════════════════════════════════════════════════════════════
        def _try_add_news():
            """检查是否两个任务都完成了，是则添加新闻"""
            if image_done.is_set() and dialog_done.is_set() and not news_added[0]:
                news_added[0] = True
                news_mgr.add_news(news_item)
                elapsed = time.time() - start_time
                log_game_event(f"[DilemmaTest] 新闻已添加(图片+对话均就绪, {elapsed:.1f}秒): {news_item.title}", tag="DILEMMA")
        
        # ═══════════════════════════════════════════════════════════════
        # 准备参考图（当事人头像）
        # ═══════════════════════════════════════════════════════════════
        reference_images = []
        enhanced_prompt = news_item.image_prompt
        
        if news_item.actor_names:
            avatar_dirs = [Path("assets/head_icon_hd"), Path("assets/head_icon")]
            ref_image_info = []
            
            for actor_name in news_item.actor_names:
                avatar_path = None
                for avatar_dir in avatar_dirs:
                    test_path = avatar_dir / f"{actor_name}.png"
                    if test_path.exists():
                        avatar_path = test_path
                        break
                
                if avatar_path:
                    reference_images.append(str(avatar_path))
                    ref_image_info.append((str(avatar_path), actor_name))
                    log_game_event(f"[DilemmaTest] 找到当事人头像: {actor_name} -> {avatar_path}", tag="DILEMMA")
            
            # 在prompt中明确说明每张参考图对应的当事人
            if ref_image_info:
                ref_description = "\n\n【参考图说明】\n"
                for i, (path, name) in enumerate(ref_image_info, 1):
                    ref_description += f"第{i}张参考图是{name}的头像，请严格参考其面部特征。"
                enhanced_prompt = news_item.image_prompt + ref_description
        
        # ═══════════════════════════════════════════════════════════════
        # 启动并行任务
        # ═══════════════════════════════════════════════════════════════
        try:
            # 启动图片生成
            generator = get_image_generator()
            news_item._image_path = "loading"
            log_game_event(f"[DilemmaTest] 图片生成请求: {enhanced_prompt[:80]}...", tag="DILEMMA")
            
            if reference_images:
                log_game_event(f"[DilemmaTest] 使用参考图: {reference_images}", tag="DILEMMA")
                generator.generate_image_async(
                    prompt=enhanced_prompt,
                    callback=on_image_ready,
                    reference_images=reference_images
                )
            else:
                generator.generate_image_async(
                    prompt=enhanced_prompt,
                    callback=on_image_ready
                )
            
            # 启动对话扩写（在线程中）
            dialog_thread = threading.Thread(target=generate_dialog, daemon=True)
            dialog_thread.start()
            
            # 设置超时保护
            def timeout_check():
                time.sleep(max_wait_time)
                if not news_added[0]:
                    log_game_event(f"[DilemmaTest] 生成超时({max_wait_time}秒)，强制添加新闻", tag="DILEMMA")
                    image_done.set()
                    dialog_done.set()
                    _try_add_news()
            
            timeout_thread = threading.Thread(target=timeout_check, daemon=True)
            timeout_thread.start()
            
        except Exception as e:
            log_game_event(f"[DilemmaTest] 启动并行生成失败: {e}", tag="DILEMMA")
            # 失败时直接添加新闻（无配图）
            news_mgr.add_news(news_item)
    
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
    
    def _handle_generated_event(self, event_card: 'EventCard'):
        """
        实例方法：处理生成的事件卡片
        将EventCard接入配图和扩写流程
        """
        print(f"[StoryDirector] 实例方法处理生成的事件: {event_card.title}")
        
        # 查找关联的NPC
        npc = None
        for actor in event_card.actors:
            npc_id = actor.get('npc_id', '')
            if npc_id in self.npc_data:
                npc = self.npc_data[npc_id]
                break
        
        if not npc:
            print(f"[StoryDirector] 警告: 找不到事件关联的NPC")
            return
        
        # 调用静态方法处理
        StoryDirector._handle_generated_event_static(npc, event_card, ctx)
    
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
