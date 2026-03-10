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
    NPC性格维度数据类
    
    所有维度默认值为"普通"，可以根据NPC人设进行调整。
    """
    # 字符串表示（用于数据存储和显示）
    temper_str: str = "普通"           # 脾气：温和、性急、普通
    spirit_str: str = "普通"           # 胆量：胆小、勇敢、普通
    ism_str: str = "普通"              # 主义：理想、现实、普通
    act_style_str: str = "普通"        # 行动风格：慎重、轻率、普通
    friendship_str: str = "普通"       # 情义重视：不重情义、重视情义、普通
    desire_str: str = "普通"           # 物欲：无欲、贪心、普通
    desire_type_str: str = "金钱"      # 物欲类型：书籍、武具、金钱、南蛮物、艺术品
    
    # 野心值 (0-100，独立数值)
    ambition: int = 50
    
    @property
    def temper(self) -> TemperEnum:
        """脾气性情枚举"""
        mapping = {
            "温和": TemperEnum.Mild,
            "性急": TemperEnum.Impatient,
        }
        return mapping.get(self.temper_str, TemperEnum.Normal)
    
    @property
    def spirit(self) -> SpiritEnum:
        """精神胆量枚举"""
        mapping = {
            "胆小": SpiritEnum.Timid,
            "勇敢": SpiritEnum.Brave,
        }
        return mapping.get(self.spirit_str, SpiritEnum.Normal)
    
    @property
    def ism(self) -> IsmEnum:
        """主义倾向枚举"""
        mapping = {
            "理想": IsmEnum.Ideal,
            "现实": IsmEnum.Realistic,
        }
        return mapping.get(self.ism_str, IsmEnum.Normal)
    
    @property
    def act_style(self) -> ActStyleEnum:
        """行动风格枚举"""
        mapping = {
            "慎重": ActStyleEnum.Considerate,
            "轻率": ActStyleEnum.Flippancy,
        }
        return mapping.get(self.act_style_str, ActStyleEnum.Normal)
    
    @property
    def friendship_importance(self) -> FriendshipImportanceEnum:
        """情义重视程度枚举"""
        mapping = {
            "不重情义": FriendshipImportanceEnum.NotImportant,
            "重视情义": FriendshipImportanceEnum.Important,
        }
        return mapping.get(self.friendship_str, FriendshipImportanceEnum.Normal)
    
    @property
    def desire(self) -> DesireEnum:
        """物欲程度枚举"""
        mapping = {
            "无欲": DesireEnum.DesireLess,
            "贪心": DesireEnum.Greedy,
        }
        return mapping.get(self.desire_str, DesireEnum.Normal)
    
    @property
    def desire_type(self) -> DesireTypeEnum:
        """物欲类型枚举"""
        mapping = {
            "书籍": DesireTypeEnum.Book,
            "武具": DesireTypeEnum.Weapon,
            "南蛮物": DesireTypeEnum.Nanman,
            "艺术品": DesireTypeEnum.Art,
        }
        return mapping.get(self.desire_type_str, DesireTypeEnum.Money)
    
    def to_dict(self) -> Dict:
        """转换为字典（用于序列化）"""
        return {
            "temper": self.temper_str,
            "spirit": self.spirit_str,
            "ism": self.ism_str,
            "act_style": self.act_style_str,
            "friendship": self.friendship_str,
            "desire": self.desire_str,
            "desire_type": self.desire_type_str,
            "ambition": self.ambition,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'NPCPersonality':
        """从字典创建（用于反序列化）"""
        return cls(
            temper_str=data.get("temper", "普通"),
            spirit_str=data.get("spirit", "普通"),
            ism_str=data.get("ism", "普通"),
            act_style_str=data.get("act_style", "普通"),
            friendship_str=data.get("friendship", "普通"),
            desire_str=data.get("desire", "普通"),
            desire_type_str=data.get("desire_type", "金钱"),
            ambition=data.get("ambition", 50),
        )
    
    def get_description(self) -> str:
        """获取性格描述文本"""
        parts = []
        if self.temper_str != "普通":
            parts.append(f"性情{self.temper_str}")
        if self.spirit_str != "普通":
            parts.append(f"为人{self.spirit_str}")
        if self.ism_str != "普通":
            parts.append(f"倾向{self.ism_str}")
        if self.act_style_str != "普通":
            parts.append(f"行事{self.act_style_str}")
        if self.friendship_str != "普通":
            parts.append(f"{self.friendship_str}")
        if self.desire_str != "普通":
            parts.append(f"{self.desire_str}")
        if self.ambition > 70:
            parts.append("野心勃勃")
        elif self.ambition < 30:
            parts.append("淡泊名利")
        
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
    根据职业和标签生成性格
    
    Args:
        job: 职业类型
        tags: NPC标签列表
    
    Returns:
        NPCPersonality对象
    """
    import random
    
    tags = tags or []
    template = PERSONALITY_TEMPLATES.get(job, PERSONALITY_TEMPLATES["DEFAULT"])
    
    # 基础性格从模板选择
    personality = NPCPersonality(
        temper_str=random.choice(template["temper"]),
        spirit_str=random.choice(template["spirit"]),
        ism_str=random.choice(template["ism"]),
        act_style_str=random.choice(template["act_style"]),
        friendship_str=random.choice(template["friendship"]),
        desire_str=random.choice(template["desire"]),
        desire_type_str=random.choice(template["desire_type"]),
        ambition=random.randint(*template["ambition_range"]),
    )
    
    # 根据标签调整
    if "BRAVE" in tags:
        personality.spirit_str = "勇敢"
    if "COWARD" in tags:
        personality.spirit_str = "胆小"
    if "GREEDY" in tags:
        personality.desire_str = "贪心"
    if "RIGHTEOUS" in tags:
        personality.friendship_str = "重视情义"
        personality.ism_str = "理想"
    if "HERO" in tags:
        personality.spirit_str = "勇敢"
        personality.friendship_str = "重视情义"
        personality.ambition = max(personality.ambition, 60)
    if "VILLAIN" in tags:
        personality.friendship_str = "不重情义"
        personality.ism_str = "现实"
    
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
