"""
NPC性格维度系统 - 基于太阁立志传5的性格设计

为每个NPC定义多维度性格特征，影响其行为和决策。
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Dict, Optional


class TemperEnum(Enum):
    """脾气性情"""
    Mild = auto()       # 温和
    Normal = auto()     # 普通
    Impatient = auto()  # 性急


class SpiritEnum(Enum):
    """精神胆量"""
    Timid = auto()      # 胆小
    Normal = auto()     # 普通
    Brave = auto()      # 勇敢


class IsmEnum(Enum):
    """主义倾向"""
    Ideal = auto()      # 理想主义
    Normal = auto()     # 普通
    Realistic = auto()  # 现实主义


class ActStyleEnum(Enum):
    """行动风格"""
    Considerate = auto()   # 慎重
    Normal = auto()        # 普通
    Flippancy = auto()     # 轻率


class FriendshipImportanceEnum(Enum):
    """对情义的重视程度"""
    NotImportant = auto()  # 不重情义
    Normal = auto()        # 普通
    Important = auto()     # 重视情义


class DesireEnum(Enum):
    """物欲程度"""
    DesireLess = auto()    # 无欲
    Normal = auto()        # 普通
    Greedy = auto()        # 贪心


class DesireTypeEnum(Enum):
    """物欲类型"""
    Money = auto()         # 金钱
    Book = auto()          # 书籍
    Weapon = auto()        # 武具
    Nanman = auto()        # 南蛮物（异域珍品）
    Art = auto()           # 艺术品


@dataclass
class NPCPersonality:
    """
    NPC性格维度数据类 - 数值化拔河进度条格式
    
    所有维度默认值为50（中间平衡），范围0-100。
    0-50偏向左侧特质，50-100偏向右侧特质。
    """
    # 数值化性格维度 (0-100，50为中间平衡)
    temper: int = 50           # 脾气：0温和 ←→ 100暴躁
    spirit: int = 50           # 胆量：0胆小 ←→ 100勇敢
    ism: int = 50              # 主义：0理想 ←→ 100现实
    act_style: int = 50        # 风格：0缜密 ←→ 100豪放
    friendship: int = 50       # 情义：0重情义 ←→ 100不重情义
    
    # 野心值 (0-100，单向进度条)
    ambition: int = 50
    
    # 物欲类型（字符串）
    desire_type: str = "金钱"  # 金钱、权力、美色、安定等
    
    # 向后兼容：保留字符串属性（通过计算属性实现）
    @property
    def temper_str(self) -> str:
        """脾气字符串表示（向后兼容）"""
        if self.temper < 30:
            return "温和"
        elif self.temper > 70:
            return "暴躁"
        return "普通"
    
    @property
    def spirit_str(self) -> str:
        """胆量字符串表示（向后兼容）"""
        if self.spirit < 30:
            return "胆小"
        elif self.spirit > 70:
            return "勇敢"
        return "普通"
    
    @property
    def ism_str(self) -> str:
        """主义字符串表示（向后兼容）"""
        if self.ism < 30:
            return "理想"
        elif self.ism > 70:
            return "现实"
        return "普通"
    
    @property
    def act_style_str(self) -> str:
        """风格字符串表示（向后兼容）"""
        if self.act_style < 30:
            return "缜密"
        elif self.act_style > 70:
            return "豪放"
        return "普通"
    
    @property
    def friendship_str(self) -> str:
        """情义字符串表示（向后兼容）"""
        if self.friendship < 30:
            return "重情义"
        elif self.friendship > 70:
            return "不重情义"
        return "普通"
    
    @property
    def desire_str(self) -> str:
        """物欲程度字符串表示（向后兼容）"""
        if self.ambition < 30:
            return "无欲"
        elif self.ambition > 70:
            return "贪心"
        return "普通"
    
    @property
    def desire_type_str(self) -> str:
        """物欲类型字符串表示（向后兼容）"""
        return self.desire_type
    
    def get_temper_enum(self) -> TemperEnum:
        """脾气性情枚举"""
        if self.temper < 30:
            return TemperEnum.Mild
        elif self.temper > 70:
            return TemperEnum.Impatient
        return TemperEnum.Normal
    
    def get_spirit_enum(self) -> SpiritEnum:
        """精神胆量枚举"""
        if self.spirit < 30:
            return SpiritEnum.Timid
        elif self.spirit > 70:
            return SpiritEnum.Brave
        return SpiritEnum.Normal
    
    def get_ism_enum(self) -> IsmEnum:
        """主义倾向枚举"""
        if self.ism < 30:
            return IsmEnum.Ideal
        elif self.ism > 70:
            return IsmEnum.Realistic
        return IsmEnum.Normal
    
    def get_act_style_enum(self) -> ActStyleEnum:
        """行动风格枚举"""
        if self.act_style < 30:
            return ActStyleEnum.Considerate
        elif self.act_style > 70:
            return ActStyleEnum.Flippancy
        return ActStyleEnum.Normal
    
    def get_friendship_enum(self) -> FriendshipImportanceEnum:
        """情义重视程度枚举"""
        if self.friendship < 30:
            return FriendshipImportanceEnum.Important
        elif self.friendship > 70:
            return FriendshipImportanceEnum.NotImportant
        return FriendshipImportanceEnum.Normal
    
    def get_desire_enum(self) -> DesireEnum:
        """物欲程度枚举（基于野心值）"""
        if self.ambition < 30:
            return DesireEnum.DesireLess
        elif self.ambition > 70:
            return DesireEnum.Greedy
        return DesireEnum.Normal
    
    def get_desire_type_enum(self) -> DesireTypeEnum:
        """物欲类型枚举"""
        mapping = {
            "金钱": DesireTypeEnum.Money,
            "财富": DesireTypeEnum.Money,
            "书籍": DesireTypeEnum.Book,
            "武具": DesireTypeEnum.Weapon,
            "武器": DesireTypeEnum.Weapon,
            "南蛮物": DesireTypeEnum.Nanman,
            "艺术品": DesireTypeEnum.Art,
            "艺术": DesireTypeEnum.Art,
        }
        return mapping.get(self.desire_type, DesireTypeEnum.Money)
    
    def to_dict(self) -> Dict:
        """转换为字典（用于序列化）- 新格式：数值化"""
        return {
            "temper": self.temper,
            "spirit": self.spirit,
            "ism": self.ism,
            "act_style": self.act_style,
            "friendship": self.friendship,
            "desire_type": self.desire_type,
            "ambition": self.ambition,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'NPCPersonality':
        """从字典创建（用于反序列化）- 兼容新旧格式"""
        # 检测数据格式：如果是数值，直接读取；如果是字符串，转换为数值
        def parse_value(value, left_str, right_str, left_val=20, right_val=80):
            """解析性格值，支持数值和字符串"""
            if isinstance(value, (int, float)):
                return int(value)
            elif isinstance(value, str):
                # 旧格式字符串映射
                if value == left_str or left_str in value:
                    return left_val
                elif value == right_str or right_str in value:
                    return right_val
                elif value == "普通":
                    return 50
                else:
                    # 尝试解析为数字
                    try:
                        return int(value)
                    except ValueError:
                        return 50
            return 50
        
        # 解析各维度
        temper = parse_value(data.get("temper", 50), "温和", "暴躁")
        spirit = parse_value(data.get("spirit", 50), "胆小", "勇敢")
        ism = parse_value(data.get("ism", 50), "理想", "现实")
        act_style = parse_value(data.get("act_style", 50), "缜密", "豪放")
        friendship = parse_value(data.get("friendship", 50), "重情义", "不重情义")
        
        # 野心直接读取
        ambition = data.get("ambition", 50)
        if isinstance(ambition, str):
            try:
                ambition = int(ambition)
            except ValueError:
                ambition = 50
        
        # 物欲类型
        desire_type = data.get("desire_type", "金钱")
        if not desire_type or desire_type == "None":
            desire_type = "金钱"
        
        return cls(
            temper=temper,
            spirit=spirit,
            ism=ism,
            act_style=act_style,
            friendship=friendship,
            desire_type=desire_type,
            ambition=ambition,
        )
    
    def get_description(self) -> str:
        """获取性格描述文本"""
        parts = []
        # 根据数值生成描述
        if self.temper < 30:
            parts.append("性情温和")
        elif self.temper > 70:
            parts.append("性情暴躁")
        
        if self.spirit < 30:
            parts.append("为人胆小")
        elif self.spirit > 70:
            parts.append("为人勇敢")
        
        if self.ism < 30:
            parts.append("倾向理想")
        elif self.ism > 70:
            parts.append("倾向现实")
        
        if self.act_style < 30:
            parts.append("行事缜密")
        elif self.act_style > 70:
            parts.append("行事豪放")
        
        if self.friendship < 30:
            parts.append("重情义")
        elif self.friendship > 70:
            parts.append("不重情义")
        
        if self.ambition > 70:
            parts.append("野心勃勃")
        elif self.ambition < 30:
            parts.append("淡泊名利")
        
        if self.desire_type:
            parts.append(f"追求{self.desire_type}")
        
        return "，".join(parts) if parts else "性格普通"


# ═══════════════════════════════════════════════════════════════════
# 基于人设的性格生成器
# ═══════════════════════════════════════════════════════════════════

PERSONALITY_TEMPLATES = {
    # 职业模板
    "OFFICIAL": {
        "temper": ["温和", "普通"],
        "spirit": ["普通", "勇敢"],
        "ism": ["现实", "普通"],
        "act_style": ["慎重", "普通"],
        "friendship": ["普通", "重视情义"],
        "desire": ["普通", "贪心"],
        "desire_type": ["金钱", "艺术品"],
        "ambition_range": (60, 90),
    },
    "MERCHANT": {
        "temper": ["普通", "性急"],
        "spirit": ["普通", "勇敢"],
        "ism": ["现实"],
        "act_style": ["慎重", "轻率"],
        "friendship": ["普通", "不重情义"],
        "desire": ["贪心"],
        "desire_type": ["金钱", "南蛮物"],
        "ambition_range": (50, 80),
    },
    "SCHOLAR": {
        "temper": ["温和"],
        "spirit": ["普通", "胆小"],
        "ism": ["理想"],
        "act_style": ["慎重"],
        "friendship": ["重视情义"],
        "desire": ["无欲", "普通"],
        "desire_type": ["书籍", "艺术品"],
        "ambition_range": (30, 60),
    },
    "WARRIOR": {
        "temper": ["性急"],
        "spirit": ["勇敢"],
        "ism": ["普通", "现实"],
        "act_style": ["轻率", "普通"],
        "friendship": ["重视情义"],
        "desire": ["普通"],
        "desire_type": ["武具"],
        "ambition_range": (50, 80),
    },
    "BANDIT": {
        "temper": ["性急"],
        "spirit": ["勇敢", "普通"],
        "ism": ["现实"],
        "act_style": ["轻率"],
        "friendship": ["不重情义", "普通"],
        "desire": ["贪心"],
        "desire_type": ["金钱", "武具"],
        "ambition_range": (40, 70),
    },
    "FARMER": {
        "temper": ["温和", "普通"],
        "spirit": ["普通", "胆小"],
        "ism": ["普通"],
        "act_style": ["慎重", "普通"],
        "friendship": ["普通", "重视情义"],
        "desire": ["无欲", "普通"],
        "desire_type": ["金钱"],
        "ambition_range": (20, 50),
    },
    "MONK": {
        "temper": ["温和"],
        "spirit": ["勇敢", "普通"],
        "ism": ["理想"],
        "act_style": ["慎重"],
        "friendship": ["普通"],
        "desire": ["无欲"],
        "desire_type": ["书籍", "艺术品"],
        "ambition_range": (10, 40),
    },
    # 默认模板
    "DEFAULT": {
        "temper": ["普通"],
        "spirit": ["普通"],
        "ism": ["普通"],
        "act_style": ["普通"],
        "friendship": ["普通"],
        "desire": ["普通"],
        "desire_type": ["金钱"],
        "ambition_range": (30, 70),
    },
}


def generate_personality_from_job(job: str, tags: list = None) -> NPCPersonality:
    """
    根据职业和标签生成性格 - 新格式：数值化
    
    Args:
        job: 职业类型
        tags: NPC标签列表
    
    Returns:
        NPCPersonality对象
    """
    import random
    
    tags = tags or []
    template = PERSONALITY_TEMPLATES.get(job, PERSONALITY_TEMPLATES["DEFAULT"])
    
    # 辅助函数：将字符串选择转换为数值
    def str_to_value(choices, left_val=20, right_val=80, mid_val=50):
        """根据字符串选择返回数值"""
        choice = random.choice(choices)
        if choice in ["温和", "胆小", "理想", "缜密", "重情义", "无欲"]:
            return left_val
        elif choice in ["暴躁", "勇敢", "现实", "豪放", "不重情义", "贪心"]:
            return right_val
        return mid_val
    
    # 基础性格从模板选择（转换为数值）
    personality = NPCPersonality(
        temper=str_to_value(template["temper"], 20, 80, 50),
        spirit=str_to_value(template["spirit"], 20, 80, 50),
        ism=str_to_value(template["ism"], 20, 80, 50),
        act_style=str_to_value(template["act_style"], 20, 80, 50),
        friendship=str_to_value(template["friendship"], 20, 80, 50),
        desire_type=random.choice(template["desire_type"]),
        ambition=random.randint(*template["ambition_range"]),
    )
    
    # 根据标签调整（直接调整数值）
    if "BRAVE" in tags:
        personality.spirit = 80  # 勇敢
    if "COWARD" in tags:
        personality.spirit = 20  # 胆小
    if "GREEDY" in tags:
        personality.ambition = max(personality.ambition, 70)  # 贪心
    if "RIGHTEOUS" in tags:
        personality.friendship = 20  # 重情义
        personality.ism = 20  # 理想
    if "HERO" in tags:
        personality.spirit = 80  # 勇敢
        personality.friendship = 20  # 重情义
        personality.ambition = max(personality.ambition, 60)
    if "VILLAIN" in tags:
        personality.friendship = 80  # 不重情义
        personality.ism = 80  # 现实
    
    return personality


# ═══════════════════════════════════════════════════════════════════
# 人情值系统 - 社交货币
# ═══════════════════════════════════════════════════════════════════

class SocialCreditSystem:
    """
    人情值系统 - 独立于好感度的社交货币
    
    用途：
    - 消耗人情值可以让NPC帮你做事
    - 人情值通过帮助NPC、送礼、完成任务获得
    - 人情值会自然衰减（欠人情要还，否则关系变差）
    """
    
    def __init__(self):
        # {npc_id: {target_npc_id: credit_value}}
        self._credits: Dict[int, Dict[int, int]] = {}
    
    def get_credit(self, npc_id: int, target_id: int) -> int:
        """获取NPC对目标的人情值"""
        return self._credits.get(npc_id, {}).get(target_id, 0)
    
    def add_credit(self, npc_id: int, target_id: int, amount: int) -> int:
        """
        增加人情值
        
        Returns:
            更新后的人情值
        """
        if npc_id not in self._credits:
            self._credits[npc_id] = {}
        
        current = self._credits[npc_id].get(target_id, 0)
        new_value = max(0, min(100, current + amount))  # 限制0-100
        self._credits[npc_id][target_id] = new_value
        
        return new_value
    
    def consume_credit(self, npc_id: int, target_id: int, amount: int) -> bool:
        """
        消耗人情值
        
        Returns:
            是否成功消耗（余额不足返回False）
        """
        current = self.get_credit(npc_id, target_id)
        if current < amount:
            return False
        
        self._credits[npc_id][target_id] = current - amount
        return True
    
    def check_can_request(self, npc_id: int, target_id: int, 
                          cost: int, personality: NPCPersonality = None) -> tuple:
        """
        检查是否可以请求NPC帮忙
        
        Args:
            npc_id: 请求者ID
            target_id: 被请求者ID
            cost: 需要消耗的人情值
            personality: 被请求者的性格（影响判断）
        
        Returns:
            (能否帮忙, 原因说明)
        """
        credit = self.get_credit(npc_id, target_id)
        
        # 基础检查：人情值是否足够
        if credit >= cost:
            return True, "人情值充足"
        
        # 性格修正
        if personality:
            # 重视情义的人可能降低要求
            if personality.friendship_importance == FriendshipImportanceEnum.Important:
                if credit >= cost * 0.7:  # 7折
                    return True, "看在情义的份上"
            
            # 理想主义者可能为了正义免费帮忙
            if personality.ism == IsmEnum.Ideal and cost <= 20:
                return True, "为了正义"
            
            # 无欲的人要求更低
            if personality.desire == DesireEnum.DesireLess:
                if credit >= cost * 0.5:  # 5折
                    return True, "我不图回报"
        
        return False, f"人情值不足（需要{cost}，只有{credit}）"
    
    def daily_decay(self, decay_rate: float = 0.05):
        """
        每日人情值衰减
        
        模拟"人情债要还"的现实逻辑
        """
        for npc_id in self._credits:
            for target_id in list(self._credits[npc_id].keys()):
                current = self._credits[npc_id][target_id]
                new_value = int(current * (1 - decay_rate))
                if new_value <= 0:
                    del self._credits[npc_id][target_id]
                else:
                    self._credits[npc_id][target_id] = new_value
    
    def to_dict(self) -> Dict:
        """序列化"""
        return {
            str(k): {str(k2): v2 for k2, v2 in v.items()}
            for k, v in self._credits.items()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SocialCreditSystem':
        """反序列化"""
        system = cls()
        for k, v in data.items():
            system._credits[int(k)] = {int(k2): v2 for k2, v2 in v.items()}
        return system


# 全局人情值系统实例
_social_credit_system: Optional[SocialCreditSystem] = None


def get_social_credit_system() -> SocialCreditSystem:
    """获取全局人情值系统实例"""
    global _social_credit_system
    if _social_credit_system is None:
        _social_credit_system = SocialCreditSystem()
    return _social_credit_system


def reset_social_credit_system():
    """重置人情值系统（用于新游戏）"""
    global _social_credit_system
    _social_credit_system = SocialCreditSystem()
