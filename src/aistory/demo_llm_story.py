"""
真实LLM调用演示：使用 rolling_story_generator 生成起承转合四阶段事件

运行方式：
    cd e:\pyscript\aistory
    python -m src.aistory.demo_llm_story

注意：会真实调用LLM API，消耗token
"""

import sys
import asyncio
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.aistory.rolling_story_generator import (
    RollingStoryGenerator, StoryPhase, DilemmaType
)
from src.aistory.dilemma_seed import NPCDilemmaSeed, StoryBeat
from src.aistory.shared_types import WorldSnapshot
from src.llm.llm_service import LLMService


# ═══════════════════════════════════════════════════════════════
# Mock 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass
class MockPersonality:
    temper: int = 50
    spirit: int = 50
    ism: int = 50
    act_style: int = 50
    friendship: int = 50
    ambition: int = 50
    desire_type: str = "金钱"


@dataclass
class MockNPC:
    id: str = "npc_001"
    name: str = "王小乐"
    gender: str = "男"
    age: int = 25
    job: str = "伙计"
    power_type: str = "民"
    org_id: str = "悦来客栈"
    desc: str = "悦来客栈的伙计，为人老实勤快，但最近因为弟弟欠下赌债而愁眉不展"
    money: int = 300
    emotion: int = 40
    hp_percent: float = 1.0
    personality: MockPersonality = field(default_factory=MockPersonality)
    social_credit: int = 0


@dataclass
class MockPlayer:
    id: str = "player_001"
    name: str = "玩家"
    money: int = 2000
    hp_percent: float = 1.0
    fame: int = 10
    followers_count: int = 3
    inventory: Dict = field(default_factory=lambda: {"疗伤药": 5, "银票": 2})
    org_reputation: Dict = field(default_factory=lambda: {"悦来客栈": 20})
    strength: int = 60
    agility: int = 50
    wit: int = 55
    charm: int = 45
    temper: int = 50
    spirit: int = 60
    ism: int = 40
    act_style: int = 50
    loyalty: int = 70


# ═══════════════════════════════════════════════════════════════
# LLM演示类
# ═══════════════════════════════════════════════════════════════

class LLMStoryDemo:
    """真实LLM调用的起承转合演示"""
    
    def __init__(self):
        self.npc = MockNPC()
        self.player = MockPlayer()
        self.story_beats: List[StoryBeat] = []
        self.llm = None
        self.generator = None
        
    def print_header(self, title: str):
        """打印标题"""
        print("\n" + "="*70)
        print(f"【{title}】")
        print("="*70)
        
    def print_phase_banner(self, phase: StoryPhase, beat_count: int):
        """打印阶段横幅"""
        phase_names = {
            StoryPhase.EMERGE: "起 - 风声渐起",
            StoryPhase.ESCALATE: "承 - 矛盾升级", 
            StoryPhase.CLIMAX: "转 - 高潮爆发",
            StoryPhase.SETTLE: "合 - 尘埃落定"
        }
        name = phase_names.get(phase, phase.value)
        print(f"\n{'='*70}")
        print(f"  当前阶段: {phase.value} ({name})")
        print(f"  已发生节拍数: {beat_count}")
        print(f"{'='*70}")
        
    def init_llm(self):
        """初始化LLM服务"""
        print("正在初始化LLM服务...")
        self.llm = LLMService.get_instance()
        
        if not self.llm.is_available():
            print("❌ LLM服务不可用，请检查配置: user_config/ai_config.json")
            return False
            
        print(f"✅ LLM服务已初始化")
        print(f"   模型: {self.llm.config.model}")
        print(f"   API地址: {self.llm.config.api_base}")
        
        self.generator = RollingStoryGenerator(llm_service=self.llm)
        return True
        
    def create_snapshot(self) -> WorldSnapshot:
        """创建世界快照"""
        return WorldSnapshot(
            timestamp=1000.0 + len(self.story_beats) * 100,
            all_available_npcs=[
                {
                    "id": "npc_002", 
                    "name": "郁芊芊", 
                    "power_type": "商", 
                    "job": "客栈老板", 
                    "org_id": "悦来客栈",
                    "desc": "悦来客栈的女老板，精明能干",
                    "relations": ["雇佣:王小乐"]
                },
                {
                    "id": "npc_003", 
                    "name": "王二狗", 
                    "power_type": "民", 
                    "job": "赌徒", 
                    "org_id": "无",
                    "desc": "王小乐的弟弟，沉迷赌博",
                    "relations": ["兄弟:王小乐"]
                },
                {
                    "id": "npc_004", 
                    "name": "钱掌柜", 
                    "power_type": "商", 
                    "job": "钱庄掌柜", 
                    "org_id": "大通钱庄",
                    "desc": "放高利贷的掌柜，心狠手辣"
                }
            ]
        )
        
    async def generate_beat(self, beat_number: int):
        """生成一个真实的故事节拍，并让玩家选择"""
        self.print_header(f"第 {beat_number} 幕 - LLM生成事件")
        
        # 显示当前状态
        print(f"\n📊 当前故事状态:")
        print(f"   - 主角: {self.npc.name} ({self.npc.job})")
        print(f"   - 困境: {self.npc.desc}")
        print(f"   - 已发生事件数: {len(self.story_beats)}")
        
        if self.story_beats:
            print(f"\n📜 故事回顾:")
            for i, beat in enumerate(self.story_beats, 1):
                print(f"   第{i}幕: {beat.event_summary}")
                print(f"           玩家选择: {beat.player_choice}")
                
        # 推断当前阶段
        seed = NPCDilemmaSeed(
            id=self.npc.id,
            story_beats=self.story_beats
        )
        current_phase = self.generator._infer_current_phase(seed)
        self.print_phase_banner(current_phase, len(self.story_beats))
        
        # 创建世界快照
        snapshot = self.create_snapshot()
        
        # 调用LLM生成事件
        print(f"\n🤖 正在调用LLM生成事件...")
        print(f"   这可能需要几秒钟...")
        
        try:
            event_card = await self.generator.generate_next_beat(
                npc=self.npc,
                seed=seed,
                worldsnapshot=snapshot,
                player=self.player
            )
            
            print(f"\n✅ 事件生成成功！")
            
            # 显示生成的事件
            self.display_event_card(event_card)
            
            # 让玩家选择选项
            if event_card.choices:
                choice = await self.let_player_choose(event_card, event_card.choices)
                if choice is None:
                    print("\n⚠️  玩家选择退出，停止生成")
                    return False
                
                # 处理忽略事件的情况
                if choice == "IGNORE":
                    print(f"\n🎮 玩家选择忽略此事")
                    print(f"   事件将自行发展...")
                    if event_card.auto_decay:
                        print(f"   后果: {event_card.auto_decay.next_phase_preview}")
                    
                    # 记录故事节拍（忽略事件）- 包含完整的困境信息
                    beat = StoryBeat(
                        beat_number=beat_number,
                        event_summary=event_card.title,
                        player_choice="[忽略] 让事件自行发展",
                        consequence_summary=event_card.auto_decay.next_phase_preview[:100] if event_card.auto_decay else "事件恶化",
                        # 记录完整的困境信息供后续阶段使用
                        dilemma_type=event_card.dilemma_type.value if event_card.dilemma_type else "",
                        event_theme=event_card.event_theme,
                        desire=event_card.dilemma_desc.desire if event_card.dilemma_desc else "",
                        misgiving=event_card.dilemma_desc.misgiving if event_card.dilemma_desc else ""
                    )
                    self.story_beats.append(beat)
                else:
                    print(f"\n🎮 玩家选择:")
                    print(f"   选择: {choice.text}")
                    print(f"   后果预览: {choice.consequence_preview[:100]}...")
                    
                    # 记录故事节拍 - 包含完整的困境信息
                    beat = StoryBeat(
                        beat_number=beat_number,
                        event_summary=event_card.title,
                        player_choice=choice.text,
                        consequence_summary=choice.consequence_preview[:100],
                        # 记录完整的困境信息供后续阶段使用
                        dilemma_type=event_card.dilemma_type.value if event_card.dilemma_type else "",
                        event_theme=event_card.event_theme,
                        desire=event_card.dilemma_desc.desire if event_card.dilemma_desc else "",
                        misgiving=event_card.dilemma_desc.misgiving if event_card.dilemma_desc else ""
                    )
                    self.story_beats.append(beat)
                
                print(f"\n✅ 第 {beat_number} 幕完成")
                return True
            else:
                print("❌ 生成的事件没有选项")
                return False
                
        except Exception as e:
            print(f"\n❌ LLM调用失败: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    async def let_player_choose(self, event_card, choices: list):
        """让玩家在控制台选择选项，包括忽略事件"""
        print(f"\n{'='*70}")
        print("🎮 请做出你的选择:")
        print(f"{'='*70}")
        
        # 显示所有选项（玩家帮助视角）
        for i, choice in enumerate(choices, 1):
            print(f"\n  [{i}] {choice.text}")
            if choice.requirement:
                print(f"      要求: {choice.requirement}")
            if choice.cost:
                print(f"      代价: {choice.cost}")
            if choice.effect:
                print(f"      收益: {choice.effect}")
            print(f"      局势变化: {choice.tension_delta}")
            print(f"      后果: {choice.consequence_preview[:60]}...")
        
        # 添加"忽略事件"选项（自动恶化）
        print(f"\n  [9] 忽略此事，让事件自行发展")
        if event_card.auto_decay:
            print(f"      后果: {event_card.auto_decay.next_phase_preview}")
            print(f"      局势变化: +{event_card.auto_decay.auto_tension_delta}")
        
        # 添加退出选项
        print(f"\n  [0] 退出演示")
        
        # 获取玩家输入
        while True:
            try:
                print(f"\n{'='*70}")
                user_input = input("请输入选项编号 (0-{}, 或9忽略): ".format(len(choices))).strip()
                
                if user_input == "0":
                    return None
                
                if user_input == "9":
                    # 返回特殊标记表示忽略事件
                    return "IGNORE"
                
                choice_idx = int(user_input)
                if 1 <= choice_idx <= len(choices):
                    return choices[choice_idx - 1]
                else:
                    print(f"⚠️  请输入 0、9 或 1-{len(choices)} 之间的数字")
                    
            except ValueError:
                print("⚠️  请输入有效的数字")
            except EOFError:
                # 处理非交互式环境（如管道输入）
                print("\n⚠️  检测到非交互式环境，自动选择第一个选项")
                return choices[0] if choices else None
            
    def display_event_card(self, card):
        """显示事件卡内容"""
        print(f"\n📰 生成的事件:")
        print(f"   阶段: {card.chain_phase.value}")
        print(f"   困境类型: {card.dilemma_type.value}")
        print(f"   事件主题: {card.event_theme}")
        print(f"\n   标题: {card.title}")
        print(f"   描述: {card.description}")
        
        if card.dilemma_desc:
            print(f"\n   💭 困境详情:")
            print(f"      概述: {card.dilemma_desc.summary[:80]}...")
            print(f"      渴望: {card.dilemma_desc.desire}")
            print(f"      顾虑: {card.dilemma_desc.misgiving}")
            
        print(f"\n   🏷️  标签: {', '.join(card.tags)}")
        
        if card.comments:
            print(f"\n   💬 网友评论:")
            for comment in card.comments[:2]:
                print(f"      {comment.get('user')}: {comment.get('text')[:40]}...")
                
        print(f"\n   🎭 演员:")
        for actor in card.actors:
            print(f"      {actor.get('role')}: {actor.get('npc_name')}")
            
        print(f"\n   📋 选项 ({len(card.choices)}个):")
        for i, choice in enumerate(card.choices, 1):
            print(f"      {i}. {choice.text}")
            if choice.requirement:
                print(f"         要求: {choice.requirement}")
            if choice.cost:
                print(f"         代价: {choice.cost}")
            if choice.effect:
                print(f"         收益: {choice.effect}")
            print(f"         局势变化: {choice.tension_delta}")
            
        if card.auto_decay:
            print(f"\n   ⏰ 自动恶化:")
            print(f"      {card.auto_decay.next_phase_preview}")
            
    async def run_demo(self, max_beats: int = 2):
        """运行演示"""
        self.print_header("真实LLM调用 - 起承转合四阶段演示")
        
        print("\n⚠️  警告: 这将真实调用LLM API，消耗token！")
        print(f"   计划生成 {max_beats} 个事件节拍\n")
        
        # 初始化LLM
        if not self.init_llm():
            return
            
        print("\n📖 故事背景:")
        print(f"   主角 {self.npc.name} 是{self.npc.org_id}的{self.npc.job}。")
        print(f"   {self.npc.desc}")
        print(f"   玩家是一名江湖侠客，与{self.npc.name}有交情。")
        
        # 生成指定数量的节拍
        for beat_num in range(1, max_beats + 1):
            print(f"\n{'='*70}")
            print(f"开始第 {beat_num} 幕...")
            print(f"{'='*70}")
            
            success = await self.generate_beat(beat_num)
            if not success:
                print(f"\n❌ 第 {beat_num} 幕生成失败，停止演示")
                break
                
        # 总结
        if self.story_beats:
            self.print_header("演示总结")
            print(f"\n📚 已生成 {len(self.story_beats)} 个故事节拍:")
            for i, beat in enumerate(self.story_beats, 1):
                print(f"\n   第{i}幕:")
                print(f"   事件: {beat.event_summary}")
                print(f"   选择: {beat.player_choice}")
                
        print(f"\n✨ 演示结束！")


async def main():
    """主函数"""
    demo = LLMStoryDemo()
    # 生成完整的4个节拍（起承转合）
    await demo.run_demo(max_beats=4)


if __name__ == "__main__":
    asyncio.run(main())
