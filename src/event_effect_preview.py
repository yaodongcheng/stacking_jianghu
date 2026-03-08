# src/event_effect_preview.py
"""
事件效果预览系统

将效果字符串解析为人类可读的后果预览，
让玩家在选择前就能看到预期影响。
"""

from typing import List, Dict, Tuple
from dataclasses import dataclass, field


@dataclass
class EffectPreview:
    """单条效果预览"""
    target: str           # 影响对象: PLAYER/SELF/OTHER/第三方名字
    target_name: str      # 显示名称
    description: str      # 效果描述
    is_positive: bool     # 是否正面效果
    severity: int         # 严重程度 1-5
    category: str         # 分类: MONEY/FAME/RELATION/STATUS/ORG/CHAIN


@dataclass 
class ChoicePreview:
    """选项完整预览"""
    button_text: str                      # 按钮文字
    effects: List[EffectPreview] = field(default_factory=list)
    requirements_met: bool = True         # 是否满足需求
    requirement_desc: str = ""            # 需求描述
    chain_hint: str = ""                  # 连锁事件提示


class EffectPreviewParser:
    """效果预览解析器"""
    
    def __init__(self):
        # 效果类型映射
        self.effect_templates = {
            'Money': self._parse_money,
            'Fame': self._parse_fame,
            'AddTag': self._parse_add_tag,
            'emotion': self._parse_emotion,
            'safety': self._parse_safety,
            'is_follower': self._parse_follower,
            'eco_status': self._parse_eco_status,
            'money': self._parse_npc_money,
            'hp': self._parse_hp,
            'inventory': self._parse_inventory,
            'freedom': self._parse_freedom,
            'soc_status': self._parse_soc_status,
            'health': self._parse_health,
            'tags': self._parse_tags,
            'family': self._parse_family,
            'social': self._parse_social,
        }
    
    def parse_choice(self, btn_text: str, effect_str: str, 
                     req_str: str, chain_str: str,
                     npc_a_name: str = "当事人",
                     npc_b_name: str = "相关人",
                     player=None) -> ChoicePreview:
        """解析单个选项的完整预览"""
        preview = ChoicePreview(button_text=btn_text)
        
        # 解析效果
        if effect_str:
            preview.effects = self._parse_effects(
                effect_str, npc_a_name, npc_b_name
            )
        
        # 解析需求
        if req_str:
            preview.requirements_met, preview.requirement_desc = \
                self._parse_requirements(req_str, player)
        
        # 解析连锁
        if chain_str:
            preview.chain_hint = self._parse_chain(chain_str)
        
        return preview
    
    def _parse_effects(self, effect_str: str, 
                       npc_a_name: str,
                       npc_b_name: str) -> List[EffectPreview]:
        """解析效果字符串为预览列表"""
        effects = []
        commands = effect_str.split(';')
        
        for cmd in commands:
            cmd = cmd.strip()
            if not cmd:
                continue
            
            effect = self._parse_single_effect(
                cmd, npc_a_name, npc_b_name
            )
            if effect:
                effects.append(effect)
        
        return effects
    
    def _parse_single_effect(self, cmd: str,
                             npc_a_name: str,
                             npc_b_name: str) -> EffectPreview:
        """解析单条效果"""
        parts = cmd.split(':')
        if len(parts) < 3:
            return None
        
        target_role = parts[0]
        attr = parts[1]
        value = ':'.join(parts[2:])
        
        # 确定目标名称
        if target_role == 'PLAYER':
            target_name = "你"
        elif target_role == 'SELF':
            target_name = npc_a_name
        elif target_role == 'OTHER':
            target_name = npc_b_name
        else:
            target_name = target_role
        
        # 调用对应解析器
        parser = self.effect_templates.get(attr)
        if parser:
            return parser(target_name, target_role, value)
        
        # 默认解析
        return EffectPreview(
            target=target_role,
            target_name=target_name,
            description=f"{attr}: {value}",
            is_positive=True,
            severity=1,
            category='OTHER'
        )
    
    # ═══════════════════════════════════════════════════════════
    # 具体效果解析器
    # ═══════════════════════════════════════════════════════════
    
    def _parse_money(self, name: str, role: str, val: str) -> EffectPreview:
        v = int(val)
        if v > 0:
            desc = f"获得 {v} 铜钱"
            positive = True
        else:
            desc = f"失去 {abs(v)} 铜钱"
            positive = False
        
        severity = 1 if abs(v) < 100 else (2 if abs(v) < 300 else 3)
        
        return EffectPreview(
            target=role, target_name=name,
            description=desc,
            is_positive=positive,
            severity=severity,
            category='MONEY'
        )
    
    def _parse_fame(self, name: str, role: str, val: str) -> EffectPreview:
        v = int(val)
        if v > 0:
            desc = f"声望 +{v}"
            positive = True
        else:
            desc = f"声望 {v}"
            positive = False
        
        severity = 1 if abs(v) < 50 else (2 if abs(v) < 150 else 3)
        
        return EffectPreview(
            target=role, target_name=name,
            description=desc,
            is_positive=positive,
            severity=severity,
            category='FAME'
        )
    
    def _parse_add_tag(self, name: str, role: str, val: str) -> EffectPreview:
        tag_names = {
            'THUG': '恶名', 'JUSTICE': '侠义',
            'WANTED': '被通缉', 'GREEDY': '贪婪',
            'VILLAIN': '恶人', 'HERO': '英雄',
            'OPEN_MIND': '开明', 'CRUEL': '残忍',
            'SCIENTIST': '博学'
        }
        tag_desc = tag_names.get(val, val)
        
        negative_tags = ['THUG', 'WANTED', 'GREEDY', 'VILLAIN', 'CRUEL']
        positive = val not in negative_tags
        
        return EffectPreview(
            target=role, target_name=name,
            description=f"获得称号「{tag_desc}」",
            is_positive=positive,
            severity=2,
            category='STATUS'
        )
    
    def _parse_emotion(self, name: str, role: str, val: str) -> EffectPreview:
        emotion_map = {
            'HAPPY': ('心情愉悦', True),
            'NORMAL': ('心情平复', True),
            'DEPRESSED': ('情绪低落', False),
            'SAD': ('心情悲伤', False),
            'ANGRY': ('勃然大怒', False),
            'DESPAIR': ('陷入绝望', False),
            'CONFUSED': ('困惑不解', False),
        }
        desc, positive = emotion_map.get(val, (f'情绪变化: {val}', True))
        severity = 1 if positive else (3 if val == 'DESPAIR' else 2)
        
        return EffectPreview(
            target=role, target_name=name,
            description=desc,
            is_positive=positive,
            severity=severity,
            category='STATUS'
        )
    
    def _parse_safety(self, name: str, role: str, val: str) -> EffectPreview:
        safety_map = {
            'NORMAL': ('恢复安全', True, 1),
            'DANGER': ('处于危险', False, 3),
            'DOWNED': ('重伤倒地', False, 4),
            'DEAD': ('死亡', False, 5),
            'EXILED': ('被流放', False, 4),
        }
        desc, positive, severity = safety_map.get(
            val, (f'状态: {val}', True, 1)
        )
        
        return EffectPreview(
            target=role, target_name=name,
            description=desc,
            is_positive=positive,
            severity=severity,
            category='STATUS'
        )
    
    def _parse_follower(self, name: str, role: str, val: str) -> EffectPreview:
        if val.lower() == 'true':
            return EffectPreview(
                target=role, target_name=name,
                description="成为你的门客",
                is_positive=True,
                severity=3,
                category='RELATION'
            )
        else:
            return EffectPreview(
                target=role, target_name=name,
                description="离开你的门下",
                is_positive=False,
                severity=3,
                category='RELATION'
            )
    
    def _parse_eco_status(self, name: str, role: str, val: str) -> EffectPreview:
        eco_map = {
            'RICH': ('变得富裕', True),
            'ENOUGH': ('生活改善', True),
            'COMMON': ('维持现状', True),
            'POOR': ('陷入贫困', False),
        }
        desc, positive = eco_map.get(val, (f'经济变化', True))
        
        return EffectPreview(
            target=role, target_name=name,
            description=desc,
            is_positive=positive,
            severity=2,
            category='STATUS'
        )
    
    def _parse_npc_money(self, name: str, role: str, val: str) -> EffectPreview:
        v = int(val)
        if v > 0:
            desc = f"获得 {v} 铜钱"
            positive = True
        else:
            desc = f"损失 {abs(v)} 铜钱"
            positive = False
        
        return EffectPreview(
            target=role, target_name=name,
            description=desc,
            is_positive=positive,
            severity=1,
            category='MONEY'
        )
    
    def _parse_hp(self, name: str, role: str, val: str) -> EffectPreview:
        v = int(val)
        if v > 0:
            desc = f"恢复 {v} 生命"
            positive = True
        else:
            desc = f"受到 {abs(v)} 伤害"
            positive = False
        
        severity = 1 if abs(v) < 20 else (2 if abs(v) < 50 else 3)
        
        return EffectPreview(
            target=role, target_name=name,
            description=desc,
            is_positive=positive,
            severity=severity,
            category='STATUS'
        )
    
    def _parse_inventory(self, name: str, role: str, val: str) -> EffectPreview:
        # 格式: ITEM:COUNT
        parts = val.split(':')
        item = parts[0]
        count = int(parts[1]) if len(parts) > 1 else 1
        
        item_names = {'GRAIN': '粮食', 'COIN': '铜钱'}
        item_desc = item_names.get(item, item)
        
        if count > 0:
            desc = f"获得 {item_desc} x{count}"
            positive = True
        else:
            desc = f"失去 {item_desc} x{abs(count)}"
            positive = False
        
        return EffectPreview(
            target=role, target_name=name,
            description=desc,
            is_positive=positive,
            severity=1,
            category='MONEY'
        )
    
    def _parse_freedom(self, name: str, role: str, val: str) -> EffectPreview:
        freedom_map = {
            'FULL': ('获得自由', True),
            'SLAVE': ('沦为奴隶', False),
        }
        desc, positive = freedom_map.get(val, ('身份变化', True))
        
        return EffectPreview(
            target=role, target_name=name,
            description=desc,
            is_positive=positive,
            severity=4 if val == 'SLAVE' else 3,
            category='STATUS'
        )
    
    def _parse_soc_status(self, name: str, role: str, val: str) -> EffectPreview:
        status_map = {
            'NOBLE': ('跻身贵族', True),
            'COMMON': ('维持身份', True),
            'LOW': ('地位下降', False),
        }
        desc, positive = status_map.get(val, ('社会地位变化', True))
        
        return EffectPreview(
            target=role, target_name=name,
            description=desc,
            is_positive=positive,
            severity=2,
            category='STATUS'
        )
    
    def _parse_health(self, name: str, role: str, val: str) -> EffectPreview:
        health_map = {
            'GOOD': ('身体康复', True),
            'NORMAL': ('健康正常', True),
            'POOR': ('健康恶化', False),
        }
        desc, positive = health_map.get(val, ('健康变化', True))
        
        return EffectPreview(
            target=role, target_name=name,
            description=desc,
            is_positive=positive,
            severity=2 if not positive else 1,
            category='STATUS'
        )
    
    def _parse_tags(self, name: str, role: str, val: str) -> EffectPreview:
        tag_names = {
            'LAY_FLAT': '躺平',
            'LOVE_BRAIN': '恋爱脑',
            'LIAR': '骗子',
            'SHAMELESS': '厚颜无耻',
            'COWARD': '懦夫',
            'HYPOCRITE': '伪君子',
            'HATED': '被人憎恨',
            'LOYAL': '忠诚',
            'TIMETRAVELER': '穿越者',
            'ROBOT': '机器人',
            'BEAUTIFUL': '美丽',
            'SLAVE_MIND': '奴性',
        }
        tag_desc = tag_names.get(val, val)
        
        negative_tags = ['LIAR', 'SHAMELESS', 'COWARD', 'HYPOCRITE', 
                        'HATED', 'SLAVE_MIND']
        positive = val not in negative_tags
        
        return EffectPreview(
            target=role, target_name=name,
            description=f"标签「{tag_desc}」",
            is_positive=positive,
            severity=2,
            category='STATUS'
        )
    
    def _parse_family(self, name: str, role: str, val: str) -> EffectPreview:
        if val == 'ISOLATED':
            return EffectPreview(
                target=role, target_name=name,
                description="与家人断绝关系",
                is_positive=False,
                severity=3,
                category='RELATION'
            )
        return EffectPreview(
            target=role, target_name=name,
            description=f"家庭关系: {val}",
            is_positive=True,
            severity=2,
            category='RELATION'
        )
    
    def _parse_social(self, name: str, role: str, val: str) -> EffectPreview:
        if val == 'ISOLATED':
            return EffectPreview(
                target=role, target_name=name,
                description="被社会孤立",
                is_positive=False,
                severity=3,
                category='RELATION'
            )
        return EffectPreview(
            target=role, target_name=name,
            description=f"社交关系: {val}",
            is_positive=True,
            severity=2,
            category='RELATION'
        )
    
    # ═══════════════════════════════════════════════════════════
    # 需求和连锁解析
    # ═══════════════════════════════════════════════════════════
    
    def _parse_requirements(self, req_str: str, 
                           player=None) -> Tuple[bool, str]:
        """解析需求字符串"""
        reqs = req_str.split(';')
        descriptions = []
        all_met = True
        
        for r in reqs:
            parts = r.split(':')
            if len(parts) < 2:
                continue
            
            r_type, r_val = parts[0], parts[1]
            
            if r_type == 'MONEY':
                val = int(r_val)
                descriptions.append(f"需要 {val} 铜钱")
                if player and player.money < val:
                    all_met = False
            
            elif r_type == 'FAME':
                val = int(r_val)
                if r_val.startswith('-'):
                    descriptions.append(f"需要恶名 {abs(val)}+")
                else:
                    descriptions.append(f"需要声望 {val}+")
                if player:
                    if r_val.startswith('-'):
                        if player.fame > val:
                            all_met = False
                    else:
                        if player.fame < val:
                            all_met = False
            
            elif r_type == 'TAG':
                tag_names = {
                    'JUSTICE': '侠义', 'THUG': '恶名',
                    'SCIENTIST': '博学'
                }
                tag_desc = tag_names.get(r_val, r_val)
                descriptions.append(f"需要称号「{tag_desc}」")
                if player and r_val not in getattr(player, 'tags', []):
                    all_met = False
            
            elif r_type == 'FOLLOWER':
                follower_names = {
                    'THUG': '打手', 'SCHOLAR': '文人',
                    'DOCTOR': '医生', 'SCIENTIST': '科学家'
                }
                f_desc = follower_names.get(r_val, r_val)
                descriptions.append(f"需要门客: {f_desc}")
        
        return all_met, '；'.join(descriptions)
    
    def _parse_chain(self, chain_str: str) -> str:
        """解析连锁事件提示"""
        if ':' in chain_str:
            parts = chain_str.split(':')
            days = float(parts[1]) if len(parts) > 1 else 1
            if days < 1:
                return "⚡ 可能引发后续事件"
            else:
                return f"⚡ {int(days)}天后可能有后续"
        return "⚡ 可能引发后续事件"


# 全局单例
_preview_parser = None

def get_preview_parser() -> EffectPreviewParser:
    global _preview_parser
    if _preview_parser is None:
        _preview_parser = EffectPreviewParser()
    return _preview_parser
