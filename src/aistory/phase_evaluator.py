"""
阶段评估器 (PhaseEvaluator)

评估NPC困境应该推进到什么阶段。
不是按"第几幕"推进，而是按"积累了多少故事节拍+当前状态"推进。
"""

import json
import re
from typing import List, Dict, Optional

from .dilemma_seed import NPCDilemmaSeed, DilemmaPhase, StoryBeat
# NPCData 类型别名 - 直接使用NPC对象
from typing import Any
NPCData = Any


class PhaseEvaluator:
    """
    困境阶段评估器
    
    核心逻辑：
    - 0节拍 → LATENT
    - 1节拍 → SURFACED  
    - 2+节拍 → 让LLM判断是否升级
    """
    
    def __init__(self, llm_service=None):
        self.llm = llm_service
    
    async def evaluate_phase(self, seed: NPCDilemmaSeed, npc: NPCData) -> DilemmaPhase:
        """
        评估困境应该推进到什么阶段
        
        规则：
        - 0个节拍 → LATENT（潜伏）
        - 1个节拍 → SURFACED（浮出水面）
        - 2+个节拍 → 让LLM判断
        - AFTERMATH需要特殊触发（故事自然结束或玩家完成救赎）
        """
        beat_count = len(seed.story_beats)
        
        # 基础规则 - 起承转合四阶段
        if beat_count == 0:
            return DilemmaPhase.EMERGE
        
        if beat_count == 1:
            return DilemmaPhase.ESCALATE
        
        if beat_count == 2:
            return DilemmaPhase.CLIMAX
        
        # 3个及以上节拍，进入SETTLE
        if beat_count >= 3:
            return DilemmaPhase.SETTLE
        
        # 无LLM时的启发式规则
        return self._heuristic_evaluate_phase(seed, npc)
    
    async def _llm_evaluate_phase(self, seed: NPCDilemmaSeed, npc: NPCData) -> DilemmaPhase:
        """使用LLM评估阶段（起承转合四阶段）"""
        
        prompt = f"""根据以下NPC的故事发展，判断困境应该处于哪个阶段。

===== 已发生的故事节拍 =====
{self._format_beats(seed.story_beats)}

===== 当前状态 =====
NPC姓名：{npc.name}
当前情绪：{npc.emotion}/100
当前健康：{npc.health}/100
当前财富：{npc.money} 文

当前困境核心：
{self._format_tensions(seed)}

===== 阶段选项（起承转合） =====
- EMERGE(起)：事件初现，暴露内心困境，还有缓冲空间
- ESCALATE(承)：矛盾升级，压力增大，事态逐步恶化
- CLIMAX(转)：关键抉择时刻，必须选边站，矛盾集中爆发
- SETTLE(合)：尘埃落定，后果显现，进入尾声

===== 判断依据 =====
1. 节拍数规则：0节拍→EMERGE, 1节拍→ESCALATE, 2节拍→CLIMAX, 3+节拍→SETTLE
2. NPC的状态是否到了临界点（情绪/健康/财富极低）
3. 故事是否积累了足够的情感浓度来支撑一个高潮
4. 当前节拍数：{len(seed.story_beats)}

请以JSON格式输出：
{{
    "phase": "阶段名（EMERGE/ESCALATE/CLIMAX/SETTLE）",
    "reason": "判断理由（详细说明为什么选这个阶段）",
    "confidence": 置信度0-100
}}
"""
        
        try:
            response = await self.llm.generate(prompt)
            return self._parse_phase_response(response, seed)
        except Exception as e:
            print(f"[PhaseEvaluator] LLM评估失败: {e}")
            return self._heuristic_evaluate_phase(seed, npc)
    
    def _heuristic_evaluate_phase(self, seed: NPCDilemmaSeed, npc: NPCData) -> DilemmaPhase:
        """启发式规则评估阶段（无LLM时）- 起承转合四阶段"""
        beat_count = len(seed.story_beats)
        
        # 基于节拍数的简单规则
        if beat_count == 0:
            return DilemmaPhase.EMERGE
        elif beat_count == 1:
            return DilemmaPhase.ESCALATE
        elif beat_count == 2:
            return DilemmaPhase.CLIMAX
        elif beat_count >= 3:
            return DilemmaPhase.SETTLE
        
        return seed.phase
    
    def _parse_phase_response(self, response: str, seed: NPCDilemmaSeed) -> DilemmaPhase:
        """解析LLM的阶段评估响应 - 起承转合四阶段"""
        
        try:
            # 提取JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)
            
            phase_str = data.get('phase', 'EMERGE').upper()
            
            # 映射到枚举（起承转合四阶段）
            phase_map = {
                'EMERGE': DilemmaPhase.EMERGE,
                'ESCALATE': DilemmaPhase.ESCALATE,
                'CLIMAX': DilemmaPhase.CLIMAX,
                'SETTLE': DilemmaPhase.SETTLE
            }
            
            new_phase = phase_map.get(phase_str, seed.phase)
            
            # 不允许回退（除了特殊情况）
            phase_order = [
                DilemmaPhase.EMERGE,
                DilemmaPhase.ESCALATE,
                DilemmaPhase.CLIMAX,
                DilemmaPhase.SETTLE
            ]
            
            old_idx = phase_order.index(seed.phase)
            new_idx = phase_order.index(new_phase)
            
            if new_idx < old_idx:
                # 不允许回退，保持原阶段
                return seed.phase
            
            return new_phase
            
        except Exception as e:
            print(f"[PhaseEvaluator] 解析阶段响应失败: {e}")
            return seed.phase
    
    def _format_beats(self, beats: List[StoryBeat]) -> str:
        """格式化故事节拍"""
        if not beats:
            return "（无）"
        
        lines = []
        for beat in beats:
            line = f"第{beat.beat_number}幕: {beat.event_summary}"
            if beat.player_choice:
                line += f"\n  → 玩家选择: {beat.player_choice}"
            if beat.consequence_summary:
                line += f"\n  → 后果: {beat.consequence_summary}"
            lines.append(line)
        
        return "\n\n".join(lines)
    
    def _format_tensions(self, seed: NPCDilemmaSeed) -> str:
        """格式化困境核心矛盾（重构后使用 desire vs misgiving）"""
        if not seed.desire and not seed.misgiving:
            return "（暂无核心矛盾）"
        
        lines = []
        if seed.desire:
            lines.append(f"渴望: {seed.desire}")
        if seed.misgiving:
            lines.append(f"顾虑: {seed.misgiving}")
        return "\n".join(lines)
    
    def should_enter_settle(self, seed: NPCDilemmaSeed, 
                            player_helped: bool = True) -> bool:
        """
        判断是否应该进入SETTLE阶段（原AFTERMATH）
        
        条件：
        1. 至少经历了3个节拍
        2. 当前是CLIMAX阶段
        3. 玩家做出了关键选择（或故事自然结束）
        """
        if len(seed.story_beats) < 3:
            return False
        
        if seed.phase != DilemmaPhase.CLIMAX:
            return False
        
        # 检查最后一个节拍是否是CLIMAX的解决
        last_beat = seed.story_beats[-1]
        if last_beat.player_choice and last_beat.consequence_summary:
            return True
        
        return False
    
    def check_recruitment_eligible(self, seed: NPCDilemmaSeed) -> bool:
        """
        检查NPC是否满足招募条件
        
        条件：
        1. 已进入SETTLE阶段
        2. 玩家一路帮助（通过story_beats判断）
        """
        if seed.phase != DilemmaPhase.SETTLE:
            return False
        
        # 统计帮助性选择
        helpful_count = 0
        total_choices = 0
        
        for beat in seed.story_beats:
            if beat.player_choice:
                total_choices += 1
                # 简单启发式判断
                positive_keywords = ['帮助', '救', '支持', '给', '资助', '保护', '感谢']
                if any(kw in beat.consequence_summary for kw in positive_keywords):
                    helpful_count += 1
                elif beat.tension_delta > 0:
                    helpful_count += 1
        
        # 至少60%的选择是帮助性的
        if total_choices > 0:
            return helpful_count / total_choices >= 0.6
        
        return False