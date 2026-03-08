"""
语言检定系统 (Persuasion System)

用于处理玩家与NPC的言语交互：
- 说服 (Persuade): 基于魅力和声望
- 威胁 (Threaten): 基于武力和名声
- 贿赂 (Bribe): 基于金钱和对方贪婪度

每次检定都会计算成功率，并可能触发暴击（大成功）或失败后果。
"""

import random
from src.utils import log_game_event


class PersuasionSystem:
    """
    语言检定系统
    
    检定公式:
        成功率 = 基础率 + (玩家属性 - NPC抵抗) * 系数 + 声望加成
    
    属性对应:
        说服 → 魅力(charm) vs 意志(morality)
        威胁 → 武力(attack) vs 勇气(bravery)
        贿赂 → 金钱 vs 贪婪度(greed)
    """
    
    # 基础成功率
    BASE_SUCCESS_RATE = 0.30
    
    # 每点属性差带来的成功率变化
    ATTRIBUTE_FACTOR = 0.02  # 每点差异 ±2%
    
    # 声望加成系数
    FAME_FACTOR = 0.001  # 每点声望 +0.1%
    
    # 好感度加成系数
    AFFINITY_FACTOR = 0.005  # 每点好感 +0.5%
    
    # 检定结果类型
    RESULT_CRIT_SUCCESS = "CRIT_SUCCESS"  # 大成功
    RESULT_SUCCESS = "SUCCESS"             # 成功
    RESULT_FAILURE = "FAILURE"             # 失败
    RESULT_CRIT_FAILURE = "CRIT_FAILURE"   # 大失败
    
    def __init__(self):
        # 检定历史记录（用于调试和UI显示）
        self.last_check_result = None
        self.last_check_details = {}
    
    def check_persuade(self, player, target_npc, difficulty_mod=0):
        """
        说服检定
        
        Args:
            player: 玩家对象
            target_npc: 目标NPC
            difficulty_mod: 难度修正（-50~+50），正值更难
        
        Returns:
            (result_type, success_rate, message)
        """
        # 获取属性
        player_charm = getattr(player, 'charm', 50)
        npc_will = getattr(target_npc, 'morality', 50)  # 道德值越高越难说服做坏事
        
        # 好感度加成 - 兼容两种存储方式
        if hasattr(target_npc, 'affinity') and isinstance(getattr(target_npc, 'affinity', None), dict):
            affinity = target_npc.affinity.get(getattr(player, 'id', 9999), 0)
        else:
            affinity = getattr(target_npc, 'affinity_to_player', 0)
        
        # 计算成功率
        base_rate = self.BASE_SUCCESS_RATE
        attr_bonus = (player_charm - npc_will) * self.ATTRIBUTE_FACTOR
        fame_bonus = getattr(player, 'fame', 0) * self.FAME_FACTOR
        affinity_bonus = affinity * self.AFFINITY_FACTOR
        difficulty_penalty = -difficulty_mod * 0.01
        
        success_rate = base_rate + attr_bonus + fame_bonus + affinity_bonus + difficulty_penalty
        success_rate = max(0.05, min(0.95, success_rate))  # 限制在5%~95%
        
        # 保存检定详情
        self.last_check_details = {
            'type': '说服',
            'player_attr': f'魅力{player_charm}',
            'npc_attr': f'意志{npc_will}',
            'base_rate': base_rate,
            'attr_bonus': attr_bonus,
            'fame_bonus': fame_bonus,
            'affinity_bonus': affinity_bonus,
            'final_rate': success_rate
        }
        
        # 进行检定
        return self._roll_check(success_rate, "说服")
    
    def check_threaten(self, player, target_npc, difficulty_mod=0):
        """
        威胁检定
        
        Args:
            player: 玩家对象
            target_npc: 目标NPC
            difficulty_mod: 难度修正
        
        Returns:
            (result_type, success_rate, message)
        """
        # 获取属性（使用攻击力代表武力）
        player_power = getattr(player, 'attack', 10)
        npc_bravery = getattr(target_npc, 'bravery', 50)
        
        # NPC当前HP影响（残血更容易被威胁）
        hp_ratio = getattr(target_npc, 'hp', 100) / max(1, getattr(target_npc, 'max_hp', 100))
        hp_bonus = (1 - hp_ratio) * 0.3  # 残血最多+30%
        
        # 计算成功率
        base_rate = self.BASE_SUCCESS_RATE
        attr_bonus = (player_power - npc_bravery * 0.5) * self.ATTRIBUTE_FACTOR
        fame_bonus = abs(getattr(player, 'fame', 0)) * self.FAME_FACTOR  # 恶名也有用
        difficulty_penalty = -difficulty_mod * 0.01
        
        success_rate = base_rate + attr_bonus + fame_bonus + hp_bonus + difficulty_penalty
        success_rate = max(0.05, min(0.95, success_rate))
        
        # 保存检定详情
        self.last_check_details = {
            'type': '威胁',
            'player_attr': f'武力{player_power}',
            'npc_attr': f'勇气{npc_bravery}',
            'hp_bonus': hp_bonus,
            'final_rate': success_rate
        }
        
        return self._roll_check(success_rate, "威胁")
    
    def check_bribe(self, player, target_npc, bribe_amount, difficulty_mod=0):
        """
        贿赂检定
        
        Args:
            player: 玩家对象
            target_npc: 目标NPC
            bribe_amount: 贿赂金额
            difficulty_mod: 难度修正
        
        Returns:
            (result_type, success_rate, message)
        """
        # 获取属性
        player_money = getattr(player, 'money', 0)
        npc_greed = 100 - getattr(target_npc, 'morality', 50)  # 道德越低越贪
        
        # 贿赂金额影响（相对于NPC财富）
        npc_wealth = getattr(target_npc, 'money', 50)
        relative_bribe = bribe_amount / max(1, npc_wealth)
        bribe_bonus = min(relative_bribe * 0.5, 0.4)  # 最多+40%
        
        # 计算成功率
        base_rate = 0.20  # 贿赂基础率较低
        greed_bonus = npc_greed * 0.005  # 贪婪度每点+0.5%
        difficulty_penalty = -difficulty_mod * 0.01
        
        success_rate = base_rate + greed_bonus + bribe_bonus + difficulty_penalty
        success_rate = max(0.05, min(0.95, success_rate))
        
        # 保存检定详情
        self.last_check_details = {
            'type': '贿赂',
            'bribe_amount': bribe_amount,
            'npc_greed': npc_greed,
            'bribe_bonus': bribe_bonus,
            'final_rate': success_rate
        }
        
        return self._roll_check(success_rate, "贿赂")
    
    def _roll_check(self, success_rate, check_type):
        """
        执行骰子检定
        
        Returns:
            (result_type, actual_rate, message)
        """
        roll = random.random()
        
        # 大成功：骰出 < 成功率 * 0.2
        # 大失败：骰出 > 1 - (1-成功率) * 0.2
        crit_success_threshold = success_rate * 0.2
        crit_failure_threshold = 1 - (1 - success_rate) * 0.2
        
        if roll < crit_success_threshold:
            result = self.RESULT_CRIT_SUCCESS
            message = f"【大成功】{check_type}效果拔群！"
        elif roll < success_rate:
            result = self.RESULT_SUCCESS
            message = f"【成功】{check_type}奏效了。"
        elif roll > crit_failure_threshold:
            result = self.RESULT_CRIT_FAILURE
            message = f"【大失败】{check_type}彻底失败，对方恼羞成怒！"
        else:
            result = self.RESULT_FAILURE
            message = f"【失败】{check_type}没有效果。"
        
        self.last_check_result = {
            'result': result,
            'roll': roll,
            'threshold': success_rate,
            'message': message
        }
        
        log_game_event(
            f"[检定] {check_type} 成功率={success_rate:.1%} 骰点={roll:.3f} 结果={result}",
            tag="PERSUASION"
        )
        
        return result, success_rate, message
    
    def get_preview_rate(self, player, target_npc, check_type, bribe_amount=0):
        """
        预览成功率（不实际进行检定）
        用于UI显示
        
        Returns:
            (success_rate, details_dict)
        """
        if check_type == 'persuade':
            player_charm = getattr(player, 'charm', 50)
            npc_will = getattr(target_npc, 'morality', 50)
            affinity = getattr(target_npc, 'affinity', {}).get(player.id, 0)
            
            base_rate = self.BASE_SUCCESS_RATE
            attr_bonus = (player_charm - npc_will) * self.ATTRIBUTE_FACTOR
            fame_bonus = getattr(player, 'fame', 0) * self.FAME_FACTOR
            affinity_bonus = affinity * self.AFFINITY_FACTOR
            
            rate = max(0.05, min(0.95, base_rate + attr_bonus + fame_bonus + affinity_bonus))
            
            return rate, {
                '基础': f'{base_rate:.0%}',
                '魅力差': f'{attr_bonus:+.0%}',
                '声望': f'{fame_bonus:+.0%}',
                '好感': f'{affinity_bonus:+.0%}'
            }
            
        elif check_type == 'threaten':
            player_power = getattr(player, 'attack', 10)
            npc_bravery = getattr(target_npc, 'bravery', 50)
            hp_ratio = getattr(target_npc, 'hp', 100) / max(1, getattr(target_npc, 'max_hp', 100))
            hp_bonus = (1 - hp_ratio) * 0.3
            
            base_rate = self.BASE_SUCCESS_RATE
            attr_bonus = (player_power - npc_bravery * 0.5) * self.ATTRIBUTE_FACTOR
            
            rate = max(0.05, min(0.95, base_rate + attr_bonus + hp_bonus))
            
            return rate, {
                '基础': f'{base_rate:.0%}',
                '武力差': f'{attr_bonus:+.0%}',
                '残血': f'{hp_bonus:+.0%}'
            }
            
        elif check_type == 'bribe':
            npc_greed = 100 - getattr(target_npc, 'morality', 50)
            npc_wealth = getattr(target_npc, 'money', 50)
            relative_bribe = bribe_amount / max(1, npc_wealth)
            bribe_bonus = min(relative_bribe * 0.5, 0.4)
            
            base_rate = 0.20
            greed_bonus = npc_greed * 0.005
            
            rate = max(0.05, min(0.95, base_rate + greed_bonus + bribe_bonus))
            
            return rate, {
                '基础': f'{base_rate:.0%}',
                '贪婪': f'{greed_bonus:+.0%}',
                '金额': f'{bribe_bonus:+.0%}'
            }
        
        return 0.5, {}


# ═══════════════════════════════════════════════════════════════
# 悬赏取消检定 - 特殊场景
# ═══════════════════════════════════════════════════════════════

class BountyNegotiationMixin:
    """
    悬赏谈判检定 - 作为 PersuasionSystem 的扩展
    
    用于处理玩家与悬赏发布者（如恶霸）的谈判
    """
    
    def check_cancel_bounty(self, player, bounty_issuer, method='persuade', bribe_amount=0):
        """
        检定是否能取消悬赏
        
        Args:
            player: 玩家对象
            bounty_issuer: 悬赏发布者NPC
            method: 方法 ('persuade', 'threaten', 'bribe', 'defeat')
            bribe_amount: 贿赂金额（仅当method='bribe'时使用）
        
        Returns:
            (success: bool, result_type: str, message: str)
        """
        if method == 'defeat':
            # 击败后无需检定，直接成功
            return True, 'SUCCESS', "你用武力让对方屈服了！"
        
        # 恶霸有额外抵抗（难度+30）
        difficulty_mod = 30
        
        persuasion = PersuasionSystem()
        
        if method == 'persuade':
            result, rate, msg = persuasion.check_persuade(player, bounty_issuer, difficulty_mod)
        elif method == 'threaten':
            result, rate, msg = persuasion.check_threaten(player, bounty_issuer, difficulty_mod)
        elif method == 'bribe':
            result, rate, msg = persuasion.check_bribe(player, bounty_issuer, bribe_amount, difficulty_mod)
        else:
            return False, 'INVALID', "无效的方法"
        
        success = result in [PersuasionSystem.RESULT_SUCCESS, PersuasionSystem.RESULT_CRIT_SUCCESS]
        
        # 大失败的后果
        if result == PersuasionSystem.RESULT_CRIT_FAILURE:
            msg += " 对方决定提高悬赏金额！"
        
        return success, result, msg


# ═══════════════════════════════════════════════════════════════
# 招募系统 - 把敌人变成下属
# ═══════════════════════════════════════════════════════════════

class RecruitmentSystem:
    """
    招募系统
    
    允许玩家通过说服、威胁、贿赂等方式招募NPC为下属。
    招募成功后：
    - NPC成为玩家的追随者
    - 如果该NPC的势力对玩家有悬赏，悬赏自动撤销
    - NPC的组织关系变更为玩家势力
    """
    
    # 招募难度修正（基于NPC类型）
    RECRUIT_DIFFICULTY = {
        'VILLAIN': 20,      # 恶人较难招募（骄傲）
        'LOYAL': 50,        # 忠诚型极难招募
        'SIMPLE': -10,      # 头脑简单较易招募
        'GREEDY': -20,      # 贪婪型容易被收买
        'FOLLOWER': -15,    # 跟班型较易招募
        'POOR': -10,        # 穷人更容易招募
    }
    
    # 招募方式
    METHOD_PERSUADE = 'persuade'    # 说服 - 以理服人
    METHOD_THREATEN = 'threaten'    # 威胁 - 以武服人
    METHOD_BRIBE = 'bribe'          # 贿赂 - 以利诱人
    METHOD_DEFEAT = 'defeat'        # 击败 - 武力征服
    
    def __init__(self, persuasion_sys=None, faction_war_sys=None, quest_mgr=None):
        self.persuasion = persuasion_sys or PersuasionSystem()
        self.faction_war_sys = faction_war_sys
        self.quest_mgr = quest_mgr
    
    def bind_systems(self, faction_war_sys=None, quest_mgr=None):
        """
        延迟绑定其他系统引用
        在游戏初始化完成后调用，避免循环导入问题
        """
        if faction_war_sys:
            self.faction_war_sys = faction_war_sys
        if quest_mgr:
            self.quest_mgr = quest_mgr
    
    def can_recruit(self, player, target_npc):
        """
        检查是否可以尝试招募目标NPC
        
        Returns:
            (can_recruit: bool, reason: str)
        """
        # 已经是追随者
        if getattr(target_npc, 'is_follower', False):
            return False, "已经是你的追随者"
        
        # 社会等级过高（大人物不能被玩家招募）
        social_level = getattr(target_npc, 'social_level', 1)
        player_fame = getattr(player, 'fame', 0)
        
        # 需要足够的声望才能招募高级NPC
        fame_threshold = social_level * 50  # 等级1需要50声望，等级5需要250声望
        if player_fame < fame_threshold and social_level >= 3:
            return False, f"声望不足，需要{fame_threshold}声望才能招募此人"
        
        # 组织领导者不能被招募
        org_role = getattr(target_npc, 'org_role', None)
        if org_role == 'LEADER':
            return False, "组织首领无法被招募"
        
        return True, ""
    
    def get_recruit_difficulty(self, target_npc):
        """
        计算招募难度修正
        基于NPC的tags计算
        """
        tags = getattr(target_npc, 'tags', [])
        difficulty = 0
        
        for tag in tags:
            difficulty += self.RECRUIT_DIFFICULTY.get(tag, 0)
        
        # HP残血额外降低难度
        hp_ratio = getattr(target_npc, 'hp', 100) / max(1, getattr(target_npc, 'max_hp', 100))
        if hp_ratio < 0.3:
            difficulty -= 30  # 残血大幅降低难度
        elif hp_ratio < 0.5:
            difficulty -= 15
        
        return difficulty
    
    def check_recruit(self, player, target_npc, method='persuade', bribe_amount=0):
        """
        执行招募检定
        
        Args:
            player: 玩家对象
            target_npc: 目标NPC
            method: 招募方式
            bribe_amount: 贿赂金额（仅当method='bribe'时使用）
        
        Returns:
            (success: bool, result_type: str, message: str)
        """
        # 先检查是否可招募
        can, reason = self.can_recruit(player, target_npc)
        if not can:
            return False, 'INVALID', reason
        
        # 击败后的招募无需检定
        if method == self.METHOD_DEFEAT:
            return True, 'SUCCESS', f"{target_npc.name}愿意为你效力！"
        
        # 计算难度
        difficulty = self.get_recruit_difficulty(target_npc)
        
        # 根据方式进行检定
        if method == self.METHOD_PERSUADE:
            result, rate, msg = self.persuasion.check_persuade(player, target_npc, difficulty)
            action_text = "你动之以情晓之以理"
        elif method == self.METHOD_THREATEN:
            result, rate, msg = self.persuasion.check_threaten(player, target_npc, difficulty)
            action_text = "你展示实力进行威慑"
        elif method == self.METHOD_BRIBE:
            result, rate, msg = self.persuasion.check_bribe(player, target_npc, bribe_amount, difficulty)
            action_text = f"你拿出{bribe_amount}铜钱"
        else:
            return False, 'INVALID', "无效的招募方式"
        
        success = result in [PersuasionSystem.RESULT_SUCCESS, PersuasionSystem.RESULT_CRIT_SUCCESS]
        
        if success:
            if result == PersuasionSystem.RESULT_CRIT_SUCCESS:
                msg = f"【大成功】{action_text}，{target_npc.name}心悦诚服地加入了你！"
            else:
                msg = f"【成功】{action_text}，{target_npc.name}同意为你效力。"
        else:
            if result == PersuasionSystem.RESULT_CRIT_FAILURE:
                msg = f"【大失败】{target_npc.name}恼羞成怒，彻底拒绝！"
            else:
                msg = f"【失败】{target_npc.name}拒绝了你的提议。"
        
        return success, result, msg
    
    def execute_recruit(self, player, target_npc, method='persuade', bribe_amount=0, ctx=None):
        """
        执行完整的招募流程（包括检定和后续处理）
        
        Args:
            player: 玩家对象
            target_npc: 目标NPC
            method: 招募方式
            bribe_amount: 贿赂金额
            ctx: 游戏上下文（用于访问其他系统）
        
        Returns:
            (success: bool, message: str, effects: dict)
        """
        # 进行检定
        success, result_type, message = self.check_recruit(player, target_npc, method, bribe_amount)
        
        effects = {
            'recruited': False,
            'bounty_cancelled': False,
            'affinity_change': 0,
            'money_spent': 0
        }
        
        if not success:
            # 失败影响好感
            if result_type == PersuasionSystem.RESULT_CRIT_FAILURE:
                effects['affinity_change'] = -20
                self._apply_affinity_change(target_npc, player, -20)
            else:
                effects['affinity_change'] = -5
                self._apply_affinity_change(target_npc, player, -5)
            
            return False, message, effects
        
        # ═══════════════════════════════════════════════════════════════
        # 招募成功！执行后续效果
        # ═══════════════════════════════════════════════════════════════
        
        effects['recruited'] = True
        
        # 1. 扣除贿赂金
        if method == self.METHOD_BRIBE and bribe_amount > 0:
            player.money = max(0, getattr(player, 'money', 0) - bribe_amount)
            effects['money_spent'] = bribe_amount
        
        # 2. NPC成为追随者
        target_npc.is_follower = True
        target_npc.following = player
        target_npc.ai_mode = "FOLLOW"  # 设置AI模式为跟随
        target_npc.ai_reason = f"追随{player.name}"
        
        # 3. 更新组织关系
        old_org = getattr(target_npc, 'org_id', None)
        target_npc.org_id = getattr(player, 'org_id', None)  # 跟随玩家的势力
        target_npc.org_role = 'MEMBER'
        
        # 4. 【核心】撤销该势力对玩家的悬赏
        if old_org and self.faction_war_sys:
            cancelled = self._cancel_org_bounty_on_player(old_org, player, ctx)
            effects['bounty_cancelled'] = cancelled
            if cancelled:
                message += "\n悬赏已自动撤销！"
        
        # 5. 更新任务状态（如果有）
        if self.quest_mgr:
            self.quest_mgr.set_flag('bully_bounty_active', False)
            self.quest_mgr.set_flag('bully_recruited', True)
        
        # 6. 好感度提升
        effects['affinity_change'] = 30
        self._apply_affinity_change(target_npc, player, 30)
        
        log_game_event(
            f"[招募] {player.name} 成功招募 {target_npc.name} (方式={method}, 原组织={old_org})",
            tag="RECRUIT"
        )
        
        return True, message, effects
    
    def _apply_affinity_change(self, npc, player, delta):
        """更新NPC对玩家的好感度"""
        if not hasattr(npc, 'affinity'):
            npc.affinity = {}
        player_id = getattr(player, 'id', 9999)
        current = npc.affinity.get(player_id, 0)
        npc.affinity[player_id] = max(-100, min(100, current + delta))
    
    def _cancel_org_bounty_on_player(self, org_id, player, ctx=None):
        """
        撤销指定组织对玩家的悬赏
        
        当玩家招募了该组织的成员后，悬赏失去意义，应当撤销
        """
        if not self.faction_war_sys:
            return False
        
        player_id = getattr(player, 'id', 9999)
        
        # 遍历悬赏列表，找到该组织对玩家的悬赏
        bounties_to_cancel = []
        for bounty in self.faction_war_sys.active_bounties:
            if bounty.get('target_id') == player_id and bounty.get('issuer_org') == org_id:
                if bounty.get('active', True):  # 只处理活跃悬赏
                    bounties_to_cancel.append(bounty.get('id'))
        
        # 撤销悬赏
        for bounty_id in bounties_to_cancel:
            self.faction_war_sys.cancel_bounty(bounty_id)
            log_game_event(f"[悬赏] 组织{org_id}对玩家的悬赏(ID:{bounty_id})已因招募而撤销", tag="BOUNTY")
        
        return len(bounties_to_cancel) > 0
    
    def get_recruit_options(self, player, target_npc):
        """
        获取可用的招募选项（供UI显示）
        
        Returns:
            [{'method': 'persuade', 'name': '说服', 'rate': 0.45, 'cost': 0, 'hint': '+10%好感'}, ...]
        """
        can, reason = self.can_recruit(player, target_npc)
        if not can:
            return []
        
        options = []
        difficulty = self.get_recruit_difficulty(target_npc)
        
        # 说服选项
        rate, _ = self.persuasion.get_preview_rate(player, target_npc, 'persuade')
        rate = max(0.05, min(0.95, rate - difficulty * 0.01))
        options.append({
            'method': self.METHOD_PERSUADE,
            'name': '说服',
            'rate': rate,
            'cost': 0,
            'hint': '以理服人'
        })
        
        # 威胁选项
        rate, _ = self.persuasion.get_preview_rate(player, target_npc, 'threaten')
        rate = max(0.05, min(0.95, rate - difficulty * 0.01))
        options.append({
            'method': self.METHOD_THREATEN,
            'name': '威胁',
            'rate': rate,
            'cost': 0,
            'hint': '以武服人'
        })
        
        # 贿赂选项（需要计算合适金额）
        npc_wealth = getattr(target_npc, 'money', 50)
        suggested_bribe = max(50, npc_wealth * 2)  # 建议贿赂金额
        rate, _ = self.persuasion.get_preview_rate(player, target_npc, 'bribe', suggested_bribe)
        rate = max(0.05, min(0.95, rate - difficulty * 0.01))
        
        player_money = getattr(player, 'money', 0)
        if player_money >= suggested_bribe:
            options.append({
                'method': self.METHOD_BRIBE,
                'name': '贿赂',
                'rate': rate,
                'cost': suggested_bribe,
                'hint': f'花费{suggested_bribe}铜'
            })
        
        return options


# 创建全局实例（供其他模块使用）
persuasion_system = PersuasionSystem()
recruitment_system = RecruitmentSystem(persuasion_system)
