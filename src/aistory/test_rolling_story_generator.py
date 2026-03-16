"""
验证脚本：测试 rolling_story_generator 是否符合 aistory_prompt_example.md 的起承转合规范

运行方式：
    python -m src.aistory.test_rolling_story_generator

验证内容：
1. 数据结构完整性检查
2. Prompt 构建检查
3. JSON 输出格式检查
"""

import json
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入被测试的模块
from src.aistory.rolling_story_generator import (
    RollingStoryGenerator, StoryPhase, DilemmaType,
    EventCard, EventChoice, AutoDecay, DilemmaDesc,
    EVENT_THEMES
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
    name: str = "李师师"
    gender: str = "女"
    age: int = 30
    job: str = "花魁"
    power_type: str = "民"
    org_id: str = "甜水巷"
    desc: str = "名动京师的花魁，琴棋书画样样精通"
    money: int = 500
    emotion: int = 50
    hp_percent: float = 1.0
    personality: MockPersonality = field(default_factory=MockPersonality)
    social_credit: int = 0


@dataclass
class MockPlayer:
    id: str = "player_001"
    name: str = "玩家"
    money: int = 1000
    hp_percent: float = 1.0
    fame: int = 0
    followers_count: int = 5
    inventory: Dict = field(default_factory=dict)
    org_reputation: Dict = field(default_factory=dict)
    # 属性
    strength: int = 50
    agility: int = 50
    wit: int = 50
    charm: int = 50
    temper: int = 50
    spirit: int = 50
    ism: int = 50
    act_style: int = 50
    loyalty: int = 50


# ═══════════════════════════════════════════════════════════════
# 验证测试类
# ═══════════════════════════════════════════════════════════════

class RollingStoryValidator:
    """滚动故事生成器验证器"""
    
    def __init__(self):
        self.generator = RollingStoryGenerator(llm_service=None)
        self.results = []
        
    def log(self, message: str, status: str = "INFO"):
        """记录验证结果"""
        prefix = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "INFO": "ℹ️"}.get(status, "ℹ️")
        self.results.append(f"{prefix} [{status}] {message}")
        print(f"{prefix} {message}")
        
    def validate_data_structures(self):
        """验证数据结构完整性"""
        print("\n" + "="*60)
        print("【测试1】数据结构完整性检查")
        print("="*60)
        
        # 1. 验证 StoryPhase 枚举
        phases = [StoryPhase.EMERGE, StoryPhase.ESCALATE, StoryPhase.CLIMAX, StoryPhase.SETTLE]
        expected_phases = ["EMERGE", "ESCALATE", "CLIMAX", "SETTLE"]
        actual_phases = [p.value for p in phases]
        if actual_phases == expected_phases:
            self.log("StoryPhase 枚举包含全部四阶段", "PASS")
        else:
            self.log(f"StoryPhase 枚举不匹配: {actual_phases}", "FAIL")
            
        # 2. 验证 DilemmaType 枚举
        dilemma_types = [
            DilemmaType.SACRIFICE, DilemmaType.BETRAY, DilemmaType.COMPROMISE,
            DilemmaType.DESTRUCTION, DilemmaType.BIAS, DilemmaType.MORAL_GREY,
            DilemmaType.SHORT_VS_LONG
        ]
        if len(dilemma_types) == 7:
            self.log("DilemmaType 枚举包含全部七大困境类型", "PASS")
        else:
            self.log(f"DilemmaType 枚举数量不对: {len(dilemma_types)}", "FAIL")
            
        # 3. 验证 EventCard 字段
        card = EventCard()
        required_fields = [
            'id', 'chain_phase', 'dilemma_type', 'event_theme', 'dilemma_desc',
            'title', 'description', 'image_prompt', 'tags', 'comments',
            'actors', 'choices', 'auto_decay', 'npc_id', 'emotion_tone'
        ]
        card_dict = card.to_dict()
        missing_fields = [f for f in required_fields if f not in card_dict]
        if not missing_fields:
            self.log("EventCard 包含所有必需字段", "PASS")
        else:
            self.log(f"EventCard 缺少字段: {missing_fields}", "FAIL")
            
        # 4. 验证 EventChoice 字段
        choice = EventChoice()
        required_choice_fields = [
            'text', 'requirement', 'cost', 'effect', 'tension_delta',
            'consequence_preview', 'hidden', 'unlock_condition'
        ]
        # EventChoice 没有 to_dict 方法，直接检查属性
        missing_choice_fields = [f for f in required_choice_fields if not hasattr(choice, f)]
        if not missing_choice_fields:
            self.log("EventChoice 包含所有必需字段", "PASS")
        else:
            self.log(f"EventChoice 缺少字段: {missing_choice_fields}", "FAIL")
            
        # 5. 验证 AutoDecay 字段
        decay = AutoDecay()
        required_decay_fields = ['next_phase_preview', 'auto_effect', 'auto_tension_delta']
        missing_decay_fields = [f for f in required_decay_fields if not hasattr(decay, f)]
        if not missing_decay_fields:
            self.log("AutoDecay 包含所有必需字段", "PASS")
        else:
            self.log(f"AutoDecay 缺少字段: {missing_decay_fields}", "FAIL")
            
        # 6. 验证 DilemmaDesc 字段
        desc = DilemmaDesc()
        required_desc_fields = ['summary', 'desire', 'misgiving']
        missing_desc_fields = [f for f in required_desc_fields if not hasattr(desc, f)]
        if not missing_desc_fields:
            self.log("DilemmaDesc 包含所有必需字段", "PASS")
        else:
            self.log(f"DilemmaDesc 缺少字段: {missing_desc_fields}", "FAIL")
            
        # 7. 验证 EVENT_THEMES
        expected_themes = ["维持生计", "社会治安", "家庭情感", "江湖恩怨", "奇幻搞笑"]
        actual_themes = list(EVENT_THEMES.keys())
        if actual_themes == expected_themes:
            self.log("EVENT_THEMES 包含全部五大类主题", "PASS")
        else:
            self.log(f"EVENT_THEMES 不匹配: {actual_themes}", "FAIL")
            
    def validate_prompt_construction(self):
        """验证 Prompt 构建"""
        print("\n" + "="*60)
        print("【测试2】Prompt 构建检查")
        print("="*60)
        
        # 创建测试数据
        npc = MockNPC()
        player = MockPlayer()
        
        # 创建 seed（不同节拍数测试不同阶段）
        for beat_count, expected_phase in [(0, "EMERGE"), (1, "ESCALATE"), (2, "CLIMAX"), (3, "SETTLE")]:
            seed = NPCDilemmaSeed(
                id="npc_001",
                story_beats=[StoryBeat(beat_number=i+1, event_summary=f"测试事件{i+1}") for i in range(beat_count)]
            )
            
            snapshot = WorldSnapshot(
                timestamp=1000.0,
                all_available_npcs=[
                    {"id": "npc_002", "name": "王小乐", "power_type": "民", "job": "伙计", "org_id": "甜水巷"},
                    {"id": "npc_003", "name": "郁芊芊", "power_type": "商", "job": "会长", "org_id": "甜水巷商会"}
                ]
            )
            
            # 构建 prompt (现在返回元组 system_prompt, user_prompt)
            system_prompt, user_prompt = self.generator._build_rolling_story_prompt(npc, seed, player, snapshot)
            
            # 合并两个prompt用于检查
            full_prompt = system_prompt + "\n" + user_prompt
            
            # 检查关键内容
            checks = [
                (f'chain_phase: "{expected_phase}"' in full_prompt or f"当前阶段：{expected_phase}" in full_prompt, 
                 f"包含当前阶段 {expected_phase}"),
                ("SACRIFICE" in full_prompt and "BETRAY" in full_prompt, "包含困境类型说明"),
                ("维持生计" in full_prompt and "家庭情感" in full_prompt, "包含事件主题"),
                ("李师师" in full_prompt, "包含NPC姓名"),
                ("甜水巷" in full_prompt, "包含NPC组织"),
                ("四层结构" in full_prompt or "风格锁定" in full_prompt, "包含配图四层结构说明"),
                ("[威胁]" in full_prompt and "[贿赂]" in full_prompt, "包含手段标签"),
                ("consequence_preview" in full_prompt, "包含后果预览说明"),
                ("auto_decay" in full_prompt, "包含自动恶化说明"),
                ("tension_delta" in full_prompt, "包含局势压力说明"),
            ]
            
            for check, desc in checks:
                if check:
                    self.log(f"[{expected_phase}阶段] {desc}", "PASS")
                else:
                    self.log(f"[{expected_phase}阶段] 缺少: {desc}", "FAIL")
                    
            # 检查阶段特殊要求
            if expected_phase == "CLIMAX":
                if "此刻不争取就永远失去的渴望" in full_prompt:
                    self.log("[CLIMAX] 包含 desire 特殊要求", "PASS")
                else:
                    self.log("[CLIMAX] 缺少 desire 特殊要求", "FAIL")
                    
            if expected_phase == "SETTLE":
                if "半年后的平静生活" in full_prompt:
                    self.log("[SETTLE] 包含 auto_decay 特殊要求", "PASS")
                else:
                    self.log("[SETTLE] 缺少 auto_decay 特殊要求", "FAIL")
                    
    def validate_json_output_format(self):
        """验证 JSON 输出格式"""
        print("\n" + "="*60)
        print("【测试3】JSON 输出格式检查")
        print("="*60)
        
        # 创建一个示例 EventCard
        card = EventCard(
            id="test_001",
            chain_phase=StoryPhase.EMERGE,
            dilemma_type=DilemmaType.SACRIFICE,
            event_theme="家庭情感-扶弟魔",
            dilemma_desc=DilemmaDesc(
                summary="测试困境描述",
                desire="想要帮助弟弟",
                misgiving="担心自己的积蓄"
            ),
            title="测试标题",
            description="测试描述",
            image_prompt="测试配图",
            tags=["标签1", "标签2"],
            comments=[{"user": "张三", "text": "测试评论", "type": "吃瓜"}],
            actors=[{"role": "主角", "npc_name": "李师师", "npc_id": "npc_001"}],
            npc_id="npc_001",
            emotion_tone="焦虑"
        )
        
        # 添加选项
        card.choices.append(EventChoice(
            text="[威胁]测试选项",
            requirement="PLAYER:strength:>=:50",
            cost="PLAYER:money:-100",
            effect="PLAYER:fame:+10",
            tension_delta=10,
            consequence_preview="[即时反应]...；[资源波动]...；[关系变化]...；[埋下隐患]..."
        ))
        
        # 设置 auto_decay
        card.auto_decay = AutoDecay(
            next_phase_preview="测试恶化预览",
            auto_effect="PLAYER:money:-200",
            auto_tension_delta=15
        )
        
        # 转换为字典
        try:
            card_dict = card.to_dict()
            
            # 验证必需字段
            required_top_fields = [
                'id', 'chain_phase', 'dilemma_type', 'event_theme', 'dilemma_desc',
                'title', 'description', 'image_prompt', 'tags', 'comments',
                'actors', 'choices', 'auto_decay', 'npc_id', 'emotion_tone'
            ]
            
            for field in required_top_fields:
                if field in card_dict:
                    self.log(f"JSON 包含顶级字段: {field}", "PASS")
                else:
                    self.log(f"JSON 缺少顶级字段: {field}", "FAIL")
                    
            # 验证 dilemma_desc 结构
            if 'dilemma_desc' in card_dict:
                desc_fields = ['summary', 'desire', 'misgiving']
                for field in desc_fields:
                    if field in card_dict['dilemma_desc']:
                        self.log(f"dilemma_desc 包含: {field}", "PASS")
                    else:
                        self.log(f"dilemma_desc 缺少: {field}", "FAIL")
                        
            # 验证 choices 结构
            if 'choices' in card_dict and len(card_dict['choices']) > 0:
                choice = card_dict['choices'][0]
                choice_fields = ['text', 'requirement', 'cost', 'effect', 'tension_delta', 'consequence_preview']
                for field in choice_fields:
                    if field in choice:
                        self.log(f"choice 包含: {field}", "PASS")
                    else:
                        self.log(f"choice 缺少: {field}", "FAIL")
                        
            # 验证 auto_decay 结构
            if 'auto_decay' in card_dict:
                decay_fields = ['next_phase_preview', 'auto_effect', 'auto_tension_delta']
                for field in decay_fields:
                    if field in card_dict['auto_decay']:
                        self.log(f"auto_decay 包含: {field}", "PASS")
                    else:
                        self.log(f"auto_decay 缺少: {field}", "FAIL")
                        
            # 尝试序列化为 JSON
            try:
                json_str = json.dumps(card_dict, ensure_ascii=False, indent=2)
                self.log("JSON 序列化成功", "PASS")
                
                # 验证 JSON 可以反序列化
                parsed = json.loads(json_str)
                self.log("JSON 反序列化成功", "PASS")
            except Exception as e:
                self.log(f"JSON 序列化失败: {e}", "FAIL")
                
        except Exception as e:
            self.log(f"to_dict 转换失败: {e}", "FAIL")
            
    def validate_phase_progression(self):
        """验证阶段推进逻辑"""
        print("\n" + "="*60)
        print("【测试4】阶段推进逻辑检查")
        print("="*60)
        
        # 测试 _get_next_phase
        progression_tests = [
            (StoryPhase.EMERGE, StoryPhase.ESCALATE),
            (StoryPhase.ESCALATE, StoryPhase.CLIMAX),
            (StoryPhase.CLIMAX, StoryPhase.SETTLE),
            (StoryPhase.SETTLE, StoryPhase.EMERGE),
        ]
        
        for current, expected_next in progression_tests:
            actual_next = self.generator._get_next_phase(current)
            if actual_next == expected_next:
                self.log(f"阶段推进: {current.value} → {expected_next.value}", "PASS")
            else:
                self.log(f"阶段推进错误: {current.value} → {actual_next.value} (期望: {expected_next.value})", "FAIL")
                
        # 测试 _infer_current_phase
        beat_tests = [
            (0, StoryPhase.EMERGE),
            (1, StoryPhase.ESCALATE),
            (2, StoryPhase.CLIMAX),
            (3, StoryPhase.SETTLE),
            (4, StoryPhase.EMERGE),  # 超过3个节拍，重新开始
        ]
        
        for beat_count, expected_phase in beat_tests:
            seed = NPCDilemmaSeed(
                id="test",
                story_beats=[StoryBeat(beat_number=i+1, event_summary=f"事件{i+1}") for i in range(beat_count)]
            )
            actual_phase = self.generator._infer_current_phase(seed)
            if actual_phase == expected_phase:
                self.log(f"节拍数 {beat_count} → 阶段 {expected_phase.value}", "PASS")
            else:
                self.log(f"节拍数 {beat_count} → 阶段 {actual_phase.value} (期望: {expected_phase.value})", "FAIL")
                
    def validate_phase_instructions(self):
        """验证阶段指导内容"""
        print("\n" + "="*60)
        print("【测试5】阶段指导内容检查")
        print("="*60)
        
        phases = [StoryPhase.EMERGE, StoryPhase.ESCALATE, StoryPhase.CLIMAX, StoryPhase.SETTLE]
        
        for phase in phases:
            instruction = self.generator._get_phase_instruction(phase)
            
            # 检查基本内容
            checks = [
                ("叙事节奏" in instruction, f"[{phase.value}] 包含叙事节奏"),
                ("选项特征" in instruction, f"[{phase.value}] 包含选项特征"),
                ("新闻语气" in instruction, f"[{phase.value}] 包含新闻语气"),
                ("玩家情绪目标" in instruction, f"[{phase.value}] 包含玩家情绪目标"),
            ]
            
            for check, desc in checks:
                if check:
                    self.log(desc, "PASS")
                else:
                    self.log(desc, "FAIL")
                    
            # 检查阶段特殊要求
            if phase == StoryPhase.CLIMAX:
                if "选项数量必须恰好为2" in instruction:
                    self.log("[CLIMAX] 包含选项数量限制", "PASS")
                else:
                    self.log("[CLIMAX] 缺少选项数量限制", "FAIL")
                    
            if phase == StoryPhase.SETTLE:
                if "禁止引入任何新的对立方" in instruction:
                    self.log("[SETTLE] 包含禁止新对立方", "PASS")
                else:
                    self.log("[SETTLE] 缺少禁止新对立方", "FAIL")
                    
    def print_summary(self):
        """打印验证总结"""
        print("\n" + "="*60)
        print("【验证总结】")
        print("="*60)
        
        pass_count = sum(1 for r in self.results if "[PASS]" in r)
        fail_count = sum(1 for r in self.results if "[FAIL]" in r)
        warn_count = sum(1 for r in self.results if "[WARN]" in r)
        
        print(f"\n总计: {len(self.results)} 项检查")
        print(f"✅ 通过: {pass_count}")
        print(f"❌ 失败: {fail_count}")
        print(f"⚠️  警告: {warn_count}")
        
        if fail_count == 0:
            print("\n🎉 所有检查通过！rolling_story_generator 完全符合起承转合规范。")
        else:
            print(f"\n⚠️  有 {fail_count} 项检查未通过，需要修复。")
            
        return fail_count == 0


# ═══════════════════════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════════════════════

def main():
    """主验证函数"""
    print("="*60)
    print("滚动故事生成器验证工具")
    print("对比标准: aistory_prompt_example.md 起承转合规范")
    print("="*60)
    
    validator = RollingStoryValidator()
    
    # 运行所有验证
    validator.validate_data_structures()
    validator.validate_prompt_construction()
    validator.validate_json_output_format()
    validator.validate_phase_progression()
    validator.validate_phase_instructions()
    
    # 打印总结
    success = validator.print_summary()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
