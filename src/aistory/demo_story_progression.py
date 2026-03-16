"""
起承转合四阶段层层推进演示脚本

这个脚本模拟完整的游戏循环，展示：
1. 如何根据故事节拍数推断当前阶段
2. 每个阶段的Prompt如何变化
3. 阶段之间的递进关系

运行方式：
    python -m src.aistory.demo_story_progression
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.aistory.rolling_story_generator import (
    RollingStoryGenerator, StoryPhase, DilemmaType,
    EventCard, EventChoice, AutoDecay, DilemmaDesc
)
from src.aistory.dilemma_seed import NPCDilemmaSeed, StoryBeat
from src.aistory.shared_types import WorldSnapshot


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
# 演示类
# ═══════════════════════════════════════════════════════════════

class StoryProgressionDemo:
    """起承转合四阶段层层推进演示"""
    
    def __init__(self):
        self.generator = RollingStoryGenerator(llm_service=None)
        self.npc = MockNPC()
        self.player = MockPlayer()
        self.story_beats: List[StoryBeat] = []
        
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
        
    def simulate_beat(self, beat_number: int, player_choice: str, consequence: str):
        """模拟一个游戏节拍"""
        self.print_header(f"第 {beat_number} 幕 - 玩家决策")
        
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
        
        # 显示阶段指导摘要
        instruction = self.generator._get_phase_instruction(current_phase)
        print(f"\n📝 阶段编剧指导:")
        # 提取关键行
        for line in instruction.strip().split('\n'):
            line = line.strip()
            if line.startswith('-'):
                print(f"   {line}")
                
        # 生成Prompt（简化展示）
        snapshot = self.create_snapshot()
        prompt = self.generator._build_rolling_story_prompt(
            self.npc, seed, self.player, snapshot
        )
        
        print(f"\n🔍 Prompt 关键内容检查:")
        checks = [
            ("当前阶段标识", f"当前阶段：{current_phase.value}" in prompt),
            ("困境类型说明", "SACRIFICE" in prompt and "BETRAY" in prompt),
            ("事件主题", "维持生计" in prompt and "家庭情感" in prompt),
            ("NPC信息", self.npc.name in prompt),
            ("配图四层结构", "风格锁定" in prompt),
            ("手段标签", "[威胁]" in prompt and "[贿赂]" in prompt),
            ("局势压力", "当前局势压力" in prompt),
        ]
        
        for name, passed in checks:
            status = "✅" if passed else "❌"
            print(f"   {status} {name}")
            
        # 显示特殊要求（如果有）
        if current_phase == StoryPhase.CLIMAX:
            print(f"\n⚠️  CLIMAX 特殊要求:")
            print(f"   - desire必须是'此刻不争取就永远失去的渴望'")
            print(f"   - misgiving必须是'一旦失去就无法挽回的顾虑'")
            print(f"   - 选项必须恰好为2个，形成desire vs misgiving对立")
        elif current_phase == StoryPhase.SETTLE:
            print(f"\n⚠️  SETTLE 特殊要求:")
            print(f"   - 不引入新对立方")
            print(f"   - 选项围绕'善后'：修复/巩固/弥补/放下")
            print(f"   - auto_decay描述'半年后的平静生活'")
            
        # 模拟玩家选择
        print(f"\n🎮 模拟玩家选择:")
        print(f"   玩家选择了: {player_choice}")
        print(f"   后果: {consequence}")
        
        # 记录故事节拍
        beat = StoryBeat(
            beat_number=beat_number,
            event_summary=f"{current_phase.value}阶段事件",
            player_choice=player_choice,
            consequence_summary=consequence
        )
        self.story_beats.append(beat)
        
        print(f"\n✅ 第 {beat_number} 幕完成，已记录到故事节拍")
        
    def run_full_demo(self):
        """运行完整的四阶段演示"""
        self.print_header("起承转合四阶段层层推进演示")
        
        print("\n📖 故事背景:")
        print(f"   主角 {self.npc.name} 是{self.npc.org_id}的{self.npc.job}。")
        print(f"   {self.npc.desc}")
        print(f"   玩家是一名江湖侠客，与{self.npc.name}有交情。")
        
        print("\n" + "="*70)
        print("开始第 1 幕（EMERGE - 起）...")
        print("="*70)
        
        # 第1幕：EMERGE
        self.simulate_beat(
            beat_number=1,
            player_choice="[打听]悄悄打听弟弟欠了多少钱",
            consequence="得知弟弟欠下500两银子，债主是钱掌柜"
        )
        
        print("\n" + "="*70)
        print("开始第 2 幕（ESCALATE - 承）...")
        print("="*70)
        
        # 第2幕：ESCALATE
        self.simulate_beat(
            beat_number=2,
            player_choice="[劝说]劝王小乐向老板预支工钱",
            consequence="郁芊芊同意预支200两，但要求加班三个月，弟弟又借了100两"
        )
        
        print("\n" + "="*70)
        print("开始第 3 幕（CLIMAX - 转）...")
        print("="*70)
        
        # 第3幕：CLIMAX
        self.simulate_beat(
            beat_number=3,
            player_choice="[牺牲]拿出自己的积蓄帮他还债",
            consequence="玩家花费300两，王小乐感激涕零，发誓改过自新"
        )
        
        print("\n" + "="*70)
        print("开始第 4 幕（SETTLE - 合）...")
        print("="*70)
        
        # 第4幕：SETTLE
        self.simulate_beat(
            beat_number=4,
            player_choice="[巩固]帮他在客栈争取更好的待遇",
            consequence="郁芊芊提拔王小乐为账房，月钱翻倍，生活逐渐稳定"
        )
        
        # 总结
        self.print_header("故事完结总结")
        print(f"\n📚 完整故事线（起承转合）:")
        for i, beat in enumerate(self.story_beats, 1):
            phase_names = ["EMERGE", "ESCALATE", "CLIMAX", "SETTLE"]
            phase = phase_names[i-1] if i <= 4 else "UNKNOWN"
            print(f"\n   第{i}幕 [{phase}]:")
            print(f"   事件: {beat.event_summary}")
            print(f"   选择: {beat.player_choice}")
            print(f"   结果: {beat.consequence_summary}")
            
        print(f"\n🎭 角色成长:")
        print(f"   王小乐从困境中走出，戒掉了赌博恶习")
        print(f"   玩家与王小乐的友谊更加深厚")
        print(f"   悦来客栈多了一位忠诚的账房先生")
        
        print(f"\n✨ 演示结束！")
        

def main():
    """主函数"""
    demo = StoryProgressionDemo()
    demo.run_full_demo()


if __name__ == "__main__":
    main()
