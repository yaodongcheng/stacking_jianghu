# src/llm/prompt_builder.py
"""
提示词构建器 - 根据NPC属性和上下文构建系统提示
基于参考项目的设计，实现身份地位演算、情感防线等高级特性
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class CharacterInfo:
    """
    通用角色信息数据类
    
    玩家和NPC共用同一套数据结构，实现平权设计。
    可用于NPC自我认知、NPC对玩家的评估、甚至NPC之间的互评。
    """
    # 基础身份
    entity_id: int = 0
    name: str = ""
    job: str = "NONE"
    power_type: str = "民"       # 势力类型：士/农/工/商/学/兵/游/匪/民
    org_id: str = "NONE"         # 组织ID
    org_rank: int = 0            # 组织等级 0-5
    desc: str = ""               # 描述
    tags: List[str] = field(default_factory=list)
    
    # 数值属性
    level: int = 1               # 角色等级
    hp: int = 100                # 当前生命值
    max_hp: int = 100            # 最大生命值
    attack: int = 10             # 攻击力
    defense: int = 5             # 防御力
    
    # 内在属性
    morality: int = 50           # 道德值 0-100
    wit: int = 5                 # 智力
    charm: int = 5               # 魅力
    strength: int = 5            # 力量
    bravery: int = 50            # 勇气
    
    # 社会地位
    social_level: int = 1        # 社会等级 1-5
    wealth_level: int = 1        # 财富等级 1-5
    money: int = 0               # 身上的钱
    fame: int = 0                # 名声/声望
    
    # 装备与物品
    equip_weapon: str = ""       # 武器
    equip_armor: str = ""        # 防具
    inventory_summary: str = ""  # 背包物品摘要
    
    # 关系
    followers_count: int = 0     # 追随者数量


@dataclass
class NPCContext:
    """NPC上下文信息（用于构建系统提示词）"""
    # 基础信息
    npc_id: int
    name: str
    job: str
    power_type: str  # 势力类型：士/农/工/商/学/兵/游/匪/民
    org_id: str      # 组织ID
    org_rank: int    # 组织等级 0-5
    desc: str        # 描述
    tags: List[str]  # 标签
    
    # 数值属性
    morality: int      # 道德值 0-100
    wit: int           # 智力
    charm: int         # 魅力
    strength: int      # 力量
    bravery: int       # 勇气
    
    # 状态
    affinity_to_player: int  # 对玩家好感度 -100~100
    knows_player: bool       # 是否认识玩家
    emotion: str             # 当前情绪
    
    # 社会地位
    social_level: int    # 社会等级 1-5
    wealth_level: int    # 财富等级 1-5
    eco_status: str      # 经济状况
    
    # 当前行为状态
    current_state: str = ""       # NPC状态：IDLE/WORKING/MOVING/COMBAT等
    current_activity: str = ""    # 当前活动描述（ai_reason）
    current_location: str = ""    # 当前位置（建筑名或区域）
    
    # 任务上下文
    active_quest_info: str = ""   # 当前活跃任务信息
    quest_role: str = ""          # NPC在任务中的角色：giver/target/none
    
    # 与玩家的距离信息
    distance_to_player: str = ""  # 与玩家的距离描述
    
    # 【新增】通用角色信息（NPC自己）
    self_info: CharacterInfo = None
    
    # 【新增】通用角色信息（玩家）
    player_info: CharacterInfo = None
    
    # 记忆摘要（由PromptBuilder填充）
    memory_summary: str = ""
    
    # 【新增】详细状态信息
    health_status: str = ""       # 身体状况
    combat_status: str = ""       # 战斗能力
    inventory_status: str = ""    # 背包物品
    relations_status: str = ""    # 人际关系
    player_assessment: str = ""   # 对玩家的评估


class CharacterInfoExtractor:
    """
    通用角色信息提取器
    
    玩家和NPC平权设计 - 使用同一套方法提取角色信息。
    可用于：
    - NPC自我认知：提取NPC自己的信息
    - NPC对玩家的评估：提取玩家的信息
    - NPC对其他NPC的评估：提取任意角色的信息
    """
    
    @classmethod
    def extract(cls, entity, game_ctx=None) -> CharacterInfo:
        """
        从任意角色实体提取通用信息
        
        Args:
            entity: 角色实体（玩家或NPC）
            game_ctx: 游戏上下文（用于获取额外信息）
            
        Returns:
            CharacterInfo: 填充完毕的角色信息数据类
        """
        if entity is None:
            return CharacterInfo()
        
        # 基础身份
        info = CharacterInfo(
            entity_id=getattr(entity, 'id', 0),
            name=getattr(entity, 'name', ''),
            job=getattr(entity, 'job', 'NONE'),
            power_type=getattr(entity, 'power_type', '民'),
            org_id=getattr(entity, 'player_org_id', None) or getattr(entity, 'org_id', 'NONE'),
            org_rank=getattr(entity, 'player_org_rank', 0) or getattr(entity, 'org_rank', 0),
            desc=getattr(entity, 'desc', ''),
            tags=getattr(entity, 'tags', []) or [],
            
            # 数值属性
            level=getattr(entity, 'level', 1),
            hp=getattr(entity, 'hp', 100),
            max_hp=getattr(entity, 'max_hp', 100),
            attack=getattr(entity, 'attack', 10),
            defense=getattr(entity, 'defense', 5),
            
            # 内在属性
            morality=getattr(entity, 'morality', 50),
            wit=getattr(entity, 'wit', 5),
            charm=getattr(entity, 'charm', 5),
            strength=getattr(entity, 'strength', 5),
            bravery=getattr(entity, 'bravery', 50),
            
            # 社会地位
            social_level=getattr(entity, 'social_level', 1),
            wealth_level=getattr(entity, 'wealth_level', 1),
            money=getattr(entity, 'money', 0),
            fame=getattr(entity, 'fame', 0),
            
            # 追随者
            followers_count=getattr(entity, 'followers_count', 0),
        )
        
        # 装备信息
        info.equip_weapon = cls._get_weapon_name(entity)
        info.equip_armor = cls._get_armor_name(entity)
        info.inventory_summary = cls._get_inventory_summary(entity)
        
        return info
    
    @classmethod
    def _get_weapon_name(cls, entity) -> str:
        """获取武器名称"""
        # 方法1: 直接属性
        weapon = getattr(entity, 'equip_weapon', None)
        if weapon:
            return weapon if isinstance(weapon, str) else getattr(weapon, 'name', str(weapon))
        
        # 方法2: equipment字典
        equipment = getattr(entity, 'equipment', {})
        if isinstance(equipment, dict):
            weapon = equipment.get('weapon')
            if weapon:
                return weapon if isinstance(weapon, str) else getattr(weapon, 'name', str(weapon))
        
        return ""
    
    @classmethod
    def _get_armor_name(cls, entity) -> str:
        """获取防具名称"""
        # 方法1: 直接属性
        armor = getattr(entity, 'equip_armor', None)
        if armor:
            return armor if isinstance(armor, str) else getattr(armor, 'name', str(armor))
        
        # 方法2: equipment字典
        equipment = getattr(entity, 'equipment', {})
        if isinstance(equipment, dict):
            armor = equipment.get('armor')
            if armor:
                return armor if isinstance(armor, str) else getattr(armor, 'name', str(armor))
        
        return ""
    
    @classmethod
    def _get_inventory_summary(cls, entity) -> str:
        """获取背包物品摘要"""
        inventory = getattr(entity, 'inventory', [])
        
        # 处理字典类型的 inventory（转换为列表）
        if isinstance(inventory, dict):
            inventory = list(inventory.values())
        
        if not inventory or len(inventory) == 0:
            return ""
        
        item_names = []
        for item in inventory[:5]:
            if hasattr(item, 'name'):
                item_names.append(item.name)
            elif isinstance(item, dict) and 'name' in item:
                item_names.append(item['name'])
            elif isinstance(item, str):
                item_names.append(item)
        
        if not item_names:
            return ""
        
        summary = "、".join(item_names)
        if len(inventory) > 5:
            summary += f"（还有{len(inventory)-5}件其他东西）"
        return summary
    
    # ═══════════════════════════════════════════════════════════════
    # 文本描述生成（基于CharacterInfo生成人类可读的描述）
    # ═══════════════════════════════════════════════════════════════
    
    @classmethod
    def describe_health(cls, info: CharacterInfo) -> str:
        """生成身体状况描述"""
        max_hp = max(info.max_hp, 1)
        hp_percent = (info.hp / max_hp) * 100
        
        if hp_percent >= 90:
            return f"身体很好，精力充沛（{info.hp}/{info.max_hp}）"
        elif hp_percent >= 60:
            return f"有些小伤，但不碍事（{info.hp}/{info.max_hp}）"
        elif hp_percent >= 30:
            return f"受了伤，需要休息（{info.hp}/{info.max_hp}）"
        else:
            return f"伤势很重，快撑不住了（{info.hp}/{info.max_hp}）"
    
    @classmethod
    def describe_combat_power(cls, info: CharacterInfo) -> str:
        """生成战斗能力描述"""
        lines = []
        
        if info.attack >= 30:
            lines.append(f"武艺高强（攻击{info.attack}）")
        elif info.attack >= 15:
            lines.append(f"有些身手（攻击{info.attack}）")
        else:
            lines.append(f"不擅长打架（攻击{info.attack}）")
        
        if info.defense >= 20:
            lines.append(f"防御不错（防御{info.defense}）")
        
        if info.equip_weapon:
            lines.append(f"带着{info.equip_weapon}")
        
        return "，".join(lines)
    
    @classmethod
    def describe_wealth(cls, info: CharacterInfo) -> str:
        """生成财富状况描述"""
        if info.money >= 1000:
            return f"有些积蓄（{info.money}文）"
        elif info.money >= 100:
            return f"有些银钱（{info.money}文）"
        elif info.money > 0:
            return f"不太宽裕（{info.money}文）"
        else:
            return "身无分文"
    
    @classmethod
    def describe_fame(cls, info: CharacterInfo) -> str:
        """生成名声描述"""
        if info.fame >= 500:
            return f"名声在外（声望{info.fame}）"
        elif info.fame >= 100:
            return f"略有名气（声望{info.fame}）"
        elif info.fame <= -500:
            return f"臭名昭著（声望{info.fame}）"
        elif info.fame <= -100:
            return f"名声不好（声望{info.fame}）"
        else:
            return ""
    
    @classmethod
    def compare_power(cls, self_info: CharacterInfo, target_info: CharacterInfo) -> tuple:
        """
        比较两个角色的战力
        
        Args:
            self_info: 自己的信息
            target_info: 对方的信息
            
        Returns:
            (power_ratio: float, assessment: str)
            - power_ratio: 对方战力/我的战力
            - assessment: 人类可读的战力评估
        """
        self_power = self_info.attack + self_info.defense + (self_info.hp / 10)
        target_power = target_info.attack + target_info.defense + (target_info.hp / 10)
        
        power_ratio = target_power / max(self_power, 1)
        
        if power_ratio >= 2.0:
            assessment = f"此人实力远在我之上！（攻击{target_info.attack}，防御{target_info.defense}）我最好谨慎行事。"
        elif power_ratio >= 1.3:
            assessment = f"此人实力比我强一些（攻击{target_info.attack}，防御{target_info.defense}）打起来我可能吃亏。"
        elif power_ratio >= 0.7:
            assessment = f"我们实力相当（他的攻击{target_info.attack}，我的攻击{self_info.attack}）真打起来胜负难料。"
        elif power_ratio >= 0.5:
            assessment = f"此人实力不如我（攻击{target_info.attack}，防御{target_info.defense}）若有冲突，我占上风。"
        else:
            assessment = f"此人实力远不如我！（攻击{target_info.attack}，防御{target_info.defense}）不过是个弱者。"
        
        return (power_ratio, assessment)
    
    @classmethod
    def build_full_assessment(cls, observer_info: CharacterInfo, target_info: CharacterInfo, 
                               power_type_desc: dict = None, org_desc: dict = None) -> str:
        """
        构建完整的角色评估文本（观察者视角）
        
        这是一个通用方法：
        - NPC观察玩家：observer=NPC, target=玩家
        - 玩家观察NPC：observer=玩家, target=NPC
        - NPC观察NPC：observer=NPC_A, target=NPC_B
        
        Args:
            observer_info: 观察者的信息
            target_info: 被观察者的信息
            power_type_desc: 势力类型描述字典（可选）
            org_desc: 组织描述字典（可选）
            
        Returns:
            str: 完整的评估文本
        """
        lines = []
        
        # 基本身份
        lines.append(f"【眼前这个人】名叫：{target_info.name}")
        
        # 势力类型
        if power_type_desc:
            desc = power_type_desc.get(target_info.power_type, "看不出什么来历")
            lines.append(f"- 看起来是：{desc[:20]}...")
        
        # 组织背景
        if target_info.org_id and target_info.org_id != 'NONE' and org_desc:
            org_name = org_desc.get(target_info.org_id, target_info.org_id)
            lines.append(f"- 所属势力：{org_name[:15]}")
        else:
            lines.append("- 似乎是个江湖散人，没有明显的组织背景")
        
        # 战力对比
        lines.append("")
        lines.append("【我对此人实力的判断】")
        _, power_assessment = cls.compare_power(observer_info, target_info)
        lines.append(f"- {power_assessment}")
        
        # 身体状况
        lines.append(f"- 此人{cls.describe_health(target_info).replace('身体很好', '精神饱满')}")
        
        # 财富
        wealth_desc = cls.describe_wealth(target_info)
        if "积蓄" in wealth_desc:
            lines.append(f"- 看起来是个有钱人（{target_info.money}文）")
        elif "银钱" in wealth_desc:
            lines.append(f"- 身上有些银钱（{target_info.money}文）")
        elif target_info.money > 0:
            lines.append(f"- 看起来不太宽裕（{target_info.money}文）")
        else:
            lines.append("- 看起来很穷，身无分文")
        
        # 名声
        fame_desc = cls.describe_fame(target_info)
        if fame_desc:
            lines.append(f"- {fame_desc}")
        
        # 追随者
        if target_info.followers_count >= 5:
            lines.append(f"- 此人手下有{target_info.followers_count}人，势力不小")
        elif target_info.followers_count >= 1:
            lines.append(f"- 此人有{target_info.followers_count}个跟班")
        
        # 装备
        if target_info.equip_weapon:
            lines.append(f"- 此人手持{target_info.equip_weapon}")
        if target_info.equip_armor:
            lines.append(f"- 此人身着{target_info.equip_armor}")
        
        return "\n".join(lines)


class PromptBuilder:
    """
    提示词构建器
    
    负责根据NPC属性、对话情境、世界设定构建高质量的系统提示词
    """
    
    # ═══════════════════════════════════════════════════════════════
    # 世界观设定
    # ═══════════════════════════════════════════════════════════════
    
    WORLD_SETTING = """
【时代背景】北宋末年，开封城内外，朝堂昏庸，江湖动荡。
【社会分层】士(官员)、农(地主)、工(工匠)、商(商贾)、学(学者)、兵(军士)、游(江湖人)、匪(盗匪)、民(百姓)
【语言风格】使用古白话对话，保持宋代市井气息，称谓符合时代（官人、娘子、大官人、小的、爷、哥哥等）
"""

    # 势力类型描述
    POWER_TYPE_DESC = {
        '士': "朝廷命官，讲究礼数体面，说话官腔十足，注重身份尊卑",
        '农': "地主乡绅或庄稼汉，朴实直率，关心收成年景，重视土地家业",
        '工': "匠人手艺人，务实稳重，以手艺为傲，看重信誉口碑",
        '商': "商贾买卖人，精于算计，八面玲珑，利益至上但也讲商道义气",
        '学': "读书人或僧道，满口诗书道理，追求清高，看不起铜臭味",
        '兵': "军中将士，讲究忠勇，粗犷直爽，重视袍泽情义",
        '游': "江湖人士，快意恩仇，重视侠义，不拘小节但有自己的规矩",
        '匪': "盗匪亡命，凶狠狡诈，弱肉强食，只认拳头和利益",
        '民': "普通百姓，谨小慎微，关心柴米油盐，怕事但也有血性",
    }
    
    # 组织背景描述
    ORG_DESC = {
        'kaifeng_fu': "开封府是京城衙门，包青天曾任府尹，府中官差行事讲规矩法度",
        'shenhou_fu': "神侯府乃诸葛先生所设，专管江湖大事，府中高手如云",
        'gao_manor': "高俅的府邸，权倾朝野，府中人皆是太尉的爪牙走狗",
        'tianshui_alley': "汴京商会，控制城中大半买卖，商人们利益盘根错节",
        'taixue': "太学是朝廷设立的学府，太学生们忧国忧民，常有激烈言论",
        'daxiangguo': "大相国寺是京城第一大寺，香火鼎盛，和尚们见多识广",
        'beggar_gang': "丐帮天下第一大帮，弟子遍布天下，消息灵通",
        'shizizhipo': "十字坡黑店，孙二娘卖人肉包子的地方，过路人闻风丧胆",
        'heifeng_zhai': "黑风寨占山为王，专劫过路商旅，寨中都是亡命之徒",
        'qinglang_bang': "青狼帮是城中一霸，收保护费为生，手下打手众多",
        'luopo_gang': "骆驼帮行走商路，名为镖局实则走私，水深得很",
    }
    
    # 职业话术风格
    JOB_SPEECH_STYLE = {
        'OFFICIAL': "说话文绉绉，常用官场套话，端着架子，注重措辞",
        'MERCHANT': "满嘴生意经，说话带铜臭味，爱讨价还价，精于世故",
        'SCHOLAR': "出口成章，爱引经据典，清高自矜，看不起粗人",
        'FARMER': "话语朴实，关心天气收成，老实本分，不善言辞",
        'ARTISAN': "说话实在，爱聊手艺，以技艺为傲，直来直去",
        'GUARD': "话少硬气，有军中习气，执行命令为先，讲究忠义",
        'SOLDIER': "粗声大气，喜欢吹嘘战功，重袍泽情义，直爽",
        'BANDIT': "话糙理歪，言语间带威胁，拜高踩低，见财起意",
        'THUG': "痞里痞气，爱占便宜，欺软怕硬，贪生怕死",
        'MONK': "阿弥陀佛不离口，说话玄乎，看破红尘的样子",
        'BEGGAR': "可怜兮兮或江湖气，消息灵通，察言观色",
        'NONE': "说话磕巴犹豫，底气不足，小心翼翼",
    }
    
    # ═══════════════════════════════════════════════════════════════
    # 核心提示词构建
    # ═══════════════════════════════════════════════════════════════
    
    @classmethod
    def build_system_prompt(cls, ctx: NPCContext, scenario: str = "chat", 
                            memory_system=None) -> str:
        """
        构建完整的系统提示词
        
        Args:
            ctx: NPC上下文
            scenario: 场景类型 - chat/negotiate/skill_check/event
            memory_system: NPCMemorySystem实例（用于双轨制判断）
            
        Returns:
            str: 系统提示词
        """
        sections = []
        
        # 1. 世界观
        sections.append(cls.WORLD_SETTING)
        
        # 2. 角色身份
        sections.append(cls._build_identity_section(ctx))
        
        # 3. 性格特质
        sections.append(cls._build_personality_section(ctx))
        
        # 4. 与玩家关系（传入memory_system用于双轨制判断）
        sections.append(cls._build_relationship_section(ctx, memory_system))
        
        # 5. 记忆
        if ctx.memory_summary:
            sections.append(f"\n【我的记忆】\n{ctx.memory_summary}")
        
        # 5.5 任务上下文（如果有的话）
        if ctx.active_quest_info and ctx.quest_role:
            sections.append(cls._build_quest_context_section(ctx))
        
        # 6. 对话规则
        sections.append(cls._build_rules_section(ctx, scenario))
        
        # 7. 输出格式
        sections.append(cls._build_output_format())
        
        return "\n".join(sections)
    
    @classmethod
    def _build_identity_section(cls, ctx: NPCContext) -> str:
        """构建身份设定部分"""
        lines = ["\n【我的身份】"]
        lines.append(f"我叫{ctx.name}，")
        
        # 势力类型描述
        power_desc = cls.POWER_TYPE_DESC.get(ctx.power_type, "普通人")
        lines.append(f"我是{power_desc}。")
        
        # 组织背景
        if ctx.org_id and ctx.org_id != 'NONE':
            org_desc = cls.ORG_DESC.get(ctx.org_id, "")
            if org_desc:
                rank_title = cls._get_rank_title(ctx.org_rank)
                lines.append(f"我在组织中是{rank_title}。{org_desc}")
        
        # 描述
        if ctx.desc:
            lines.append(f"关于我：{ctx.desc}")
        
        # 职业话术
        job_style = cls.JOB_SPEECH_STYLE.get(ctx.job, "")
        if job_style:
            lines.append(f"我说话的风格：{job_style}")
        
        # 【新增】当前状态 - 让NPC知道自己正在做什么
        lines.append("")
        lines.append("【我现在的状态】")
        if ctx.current_state:
            lines.append(f"- 我正在：{ctx.current_state}")
        if ctx.current_activity:
            lines.append(f"- 具体来说：{ctx.current_activity}")
        if ctx.current_location:
            lines.append(f"- 位置：{ctx.current_location}")
        
        # 【新增】与玩家的距离
        if ctx.distance_to_player:
            lines.append(f"- 与玩家的距离：{ctx.distance_to_player}")
        
        # 如果什么都没有，给个默认
        if not ctx.current_state and not ctx.current_activity and not ctx.current_location:
            lines.append("- 我在闲逛，没什么特别的事")
        
        # 【新增】我的身体状况
        if hasattr(ctx, 'health_status') and ctx.health_status:
            lines.append("")
            lines.append("【我的身体状况】")
            lines.append(ctx.health_status)
        
        # 【新增】我的能力
        if hasattr(ctx, 'combat_status') and ctx.combat_status:
            lines.append("")
            lines.append("【我的战斗能力】")
            lines.append(ctx.combat_status)
        
        # 【新增】我身上携带的东西
        if hasattr(ctx, 'inventory_status') and ctx.inventory_status:
            lines.append("")
            lines.append("【我身上的东西】")
            lines.append(ctx.inventory_status)
        
        # 【新增】我认识的人
        if hasattr(ctx, 'relations_status') and ctx.relations_status:
            lines.append("")
            lines.append("【我认识的人】")
            lines.append(ctx.relations_status)
        
        return "\n".join(lines)
    
    @classmethod
    def _build_personality_section(cls, ctx: NPCContext) -> str:
        """构建性格特质部分"""
        lines = ["\n【我的性格】"]
        
        # 根据道德值
        if ctx.morality > 70:
            lines.append("- 我是个正直善良的人，痛恨恶行，乐于助人")
        elif ctx.morality > 40:
            lines.append("- 我是个普通人，有自己的底线，但也会权衡利弊")
        elif ctx.morality > 20:
            lines.append("- 我不是什么好人，利益面前道德算什么")
        else:
            lines.append("- 我是个心狠手辣的人，只要对我有利，什么都干得出来")
        
        # 根据智力
        if ctx.wit > 7:
            lines.append("- 我心思缜密，说话滴水不漏，善于察言观色")
        elif ctx.wit < 4:
            lines.append("- 我头脑简单，不爱动脑子，说话直来直去")
        
        # 根据勇气
        if ctx.bravery > 60:
            lines.append("- 我胆子大，不怕事，敢作敢当")
        elif ctx.bravery < 30:
            lines.append("- 我胆子小，怕惹麻烦，遇事先想自保")
        
        # 根据标签
        if 'VILLAIN' in ctx.tags:
            lines.append("- 我是个反派，阴险狡诈是我的本色")
        if 'HERO' in ctx.tags:
            lines.append("- 我是个英雄人物，行事光明磊落")
        if 'GREEDY' in ctx.tags:
            lines.append("- 我贪财，见钱眼开")
        if 'RIGHTEOUS' in ctx.tags:
            lines.append("- 我讲义气，重情重义")
        if 'COWARD' in ctx.tags:
            lines.append("- 我胆小如鼠，见势不妙就想跑")
        if 'BRAVE' in ctx.tags:
            lines.append("- 我勇猛无畏，越是危险越兴奋")
        
        return "\n".join(lines)
    
    @classmethod
    def _build_relationship_section(cls, ctx: NPCContext, memory_system=None) -> str:
        """
        构建与玩家关系部分
        
        【双轨制体现】：
        - 如果有相关记忆：清晰描述原因
        - 如果没有记忆但好感度高/低：描述为"模糊的直觉"
        """
        lines = ["\n【我与玩家的关系】"]
        
        # 检查是否有关于玩家的记忆
        has_player_memory = False
        memory_reason = ""
        if memory_system:
            player_memories = memory_system.get_memories_about_player(max_count=2)
            if player_memories:
                has_player_memory = True
                memory_reason = player_memories[0].content[:30]  # 取第一条记忆的摘要
        
        # 是否认识
        if not ctx.knows_player:
            lines.append("我不认识眼前这个人，要根据他的言行举止判断。")
        else:
            # 根据好感度和记忆综合判断
            aff = ctx.affinity_to_player
            
            if aff > 60:
                if has_player_memory:
                    lines.append(f"这是我的好朋友/恩人，我对他非常信任和感激（好感度:{aff}）")
                    lines.append(f"（因为：{memory_reason}...）")
                else:
                    # 【双轨制】记忆已遗忘，但关系分数保留
                    lines.append(f"这是我的恩人，虽然我记不清具体发生过什么，但我对他有种发自内心的好感（好感度:{aff}）")
            elif aff > 30:
                if has_player_memory:
                    lines.append(f"这是个不错的朋友，我愿意帮助他（好感度:{aff}）")
                else:
                    lines.append(f"这人给我的印象不错，虽然具体原因我说不上来（好感度:{aff}）")
            elif aff > 0:
                lines.append(f"我对这个人印象还可以，但还不够熟（好感度:{aff}）")
            elif aff > -30:
                lines.append(f"我对这个人没什么好感，保持距离（好感度:{aff}）")
            elif aff > -60:
                if has_player_memory:
                    lines.append(f"我讨厌这个人，不想和他多说话（好感度:{aff}）")
                    lines.append(f"（因为：{memory_reason}...）")
                else:
                    lines.append(f"我讨厌这个人，说不清为什么，就是看他不顺眼（好感度:{aff}）")
            else:
                if has_player_memory:
                    lines.append(f"我恨透了这个人，见面就来气（好感度:{aff}）")
                    lines.append(f"（因为：{memory_reason}...）")
                else:
                    # 【双轨制】记忆已遗忘，但仇恨保留
                    lines.append(f"我恨透了这个人，具体原因已经模糊了，但每次见到他心里就有股无名火（好感度:{aff}）")
        
        # 社会地位差异提示
        if ctx.social_level >= 4:
            lines.append("我身份尊贵，和普通人说话要端着架子。")
        elif ctx.social_level <= 1:
            lines.append("我地位卑微，说话要小心谨慎。")
        
        # 【新增】玩家评估信息 - 让NPC知道玩家是什么样的人
        if hasattr(ctx, 'player_assessment') and ctx.player_assessment:
            lines.append("")
            lines.append(ctx.player_assessment)
        
        return "\n".join(lines)
    
    @classmethod
    def _build_rules_section(cls, ctx: NPCContext, scenario: str) -> str:
        """构建对话规则部分"""
        lines = ["\n【对话规则】"]
        
        # 通用规则
        lines.append("1. 保持角色扮演，用第一人称说话，不要出戏")
        lines.append("2. 回复要简短有力，控制在50字以内")
        lines.append("3. 根据我的身份和性格来说话，保持一致性")
        lines.append("4. 对话要有宋代市井气息，用语要符合时代")
        
        # 场景特定规则
        if scenario == "chat":
            lines.append("5. 这是一次闲聊，态度轻松，但保持角色特点")
            lines.append("6. 可以透露一些我知道的信息，但不要一次说太多")
        elif scenario == "negotiate":
            lines.append("5. 这是一次谈判，我要争取最大利益")
            lines.append("6. 不轻易答应，要让对方付出代价")
        elif scenario == "skill_check":
            lines.append("5. 玩家正在试图说服/威胁/欺骗我")
            lines.append("6. 根据我的性格决定是否被说服")
        
        # 情感防线规则（基于参考项目）
        lines.append("\n【绝对事实防御】")
        lines.append("- 即使玩家说得天花乱坠，违背我核心利益的事我不会答应")
        lines.append("- 我不会因为几句话就改变立场，除非有足够的理由和好处")
        lines.append("- 我会记住玩家说过的话，前后矛盾的话会让我起疑")
        
        return "\n".join(lines)
    
    @classmethod
    def _build_output_format(cls, include_actions: bool = True) -> str:
        """构建输出格式部分"""
        base_format = """
【输出格式】
请用JSON格式回复:
{
    "reply": "我的回复（50字以内）",
    "emotion": "neutral/happy/angry/sad/surprised/fearful/contempt",
    "action": "可选的动作或行为（见下方行为列表）",
    "affinity_change": 0,
    "memory_update": "如果这次对话有重要信息需要记住，写在这里"
}

emotion说明:
- neutral: 平静
- happy: 高兴/满意
- angry: 愤怒/恼火
- sad: 悲伤/失落
- surprised: 惊讶
- fearful: 恐惧/担忧
- contempt: 轻蔑/不屑

affinity_change说明:
- 范围 -10 到 +10
- 玩家表现好/帮助我: +1到+5
- 玩家表现差/冒犯我: -1到-5
- 重大帮助/仇恨: ±10
"""
        
        if include_actions:
            action_format = """
action说明:
- 可以是表情动作描述（如：冷笑、皱眉、叹气等）
- 也可以是以下特殊行为指令之一：
  - come_to_player: 走向玩家身边（如果愿意过去的话）
  - follow_player: 开始跟随玩家（直到我决定停下）
  - stop_following: 停止跟随玩家
  - leave: 转身离开（不想再聊了）
  - stay: 原地不动
  - wave: 向玩家挥手
  - nod: 点头表示同意
  - shake_head: 摇头表示拒绝
  - bow: 向玩家行礼

注意：
- 只有当对话内容真的需要行动时才使用行为指令
- 普通对话用表情动作就好（如"微笑"、"皱眉"）
- 行为指令会让我真的做出动作，请慎重使用
"""
            return base_format + action_format
        
        return base_format
    
    @classmethod
    def _get_rank_title(cls, rank: int) -> str:
        """获取组织等级称号"""
        rank_titles = {
            5: "首领/掌门/帮主",
            4: "长老/副手",
            3: "头目/香主",
            2: "核心成员",
            1: "普通成员/弟子",
            0: "外围人员"
        }
        return rank_titles.get(rank, "成员")
    
    @classmethod
    def _build_quest_context_section(cls, ctx: NPCContext) -> str:
        """
        构建任务上下文部分
        
        让NPC知道自己与玩家之间的任务关系，避免"失忆"问题
        """
        lines = ["\n【重要：当前任务情况】"]
        
        if ctx.quest_role == "giver":
            # 我是任务发布者
            lines.append(f"【我刚刚给玩家发布了一个任务！】")
            lines.append(f"任务详情：{ctx.active_quest_info}")
            lines.append("")
            lines.append("对话注意事项：")
            lines.append("- 我应该记得这个任务，并主动询问玩家的进展")
            lines.append("- 如果玩家问起任务相关的事，我应该给出有帮助的回答")
            lines.append("- 根据任务完成情况调整我的态度（鼓励/催促/感谢等）")
            lines.append("- 不要假装不知道这个任务的存在！")
        
        elif ctx.quest_role == "target":
            # 我是任务目标
            lines.append(f"【玩家正在执行一个与我相关的任务】")
            lines.append(f"任务详情：{ctx.active_quest_info}")
            lines.append("")
            lines.append("对话注意事项：")
            lines.append("- 玩家可能是来完成任务的，我应该有所回应")
            lines.append("- 根据我的性格决定是配合还是阻挠")
        
        elif ctx.quest_role == "related":
            # 我与任务有关联
            lines.append(f"【有一个进行中的任务与我有关】")
            lines.append(f"任务详情：{ctx.active_quest_info}")
            lines.append("")
            lines.append("对话注意事项：")
            lines.append("- 如果玩家问起相关的事，我可能知道一些信息")
        
        return "\n".join(lines)
    
    # ═══════════════════════════════════════════════════════════════
    # 便捷方法
    # ═══════════════════════════════════════════════════════════════
    
    @classmethod
    def build_from_npc(cls, npc, memory_system=None, scenario: str = "chat", 
                       game_ctx=None) -> str:
        """
        直接从NPC对象构建提示词
        
        Args:
            npc: NPC对象
            memory_system: NPCMemorySystem实例
            scenario: 场景类型
            game_ctx: 游戏上下文（可选，用于计算与玩家的距离、获取玩家信息）
            
        Returns:
            str: 系统提示词
        """
        print(f"\n[PromptBuilder] ===== 构建 {npc.name} 的提示词 =====")
        
        # 获取当前状态的人类可读描述
        current_state = cls._get_state_description(npc)
        current_activity = getattr(npc, 'ai_reason', '') or ''
        current_location = cls._get_location_description(npc)
        
        # 计算与玩家的距离
        distance_to_player = cls._get_distance_to_player(npc, game_ctx)
        print(f"[PromptBuilder] 与玩家距离: {distance_to_player}")
        
        print(f"[PromptBuilder] NPC状态: {current_state}")
        print(f"[PromptBuilder] 当前活动: {current_activity}")
        print(f"[PromptBuilder] 位置: {current_location}")
        
        # 【新增】获取任务上下文
        quest_info, quest_role = cls._get_quest_context_for_npc(npc)
        
        print(f"[PromptBuilder] 任务角色: {quest_role if quest_role else '(无)'}")
        if quest_info:
            print(f"[PromptBuilder] 任务信息: {quest_info[:100]}...")
        else:
            print(f"[PromptBuilder] 任务信息: (无)")
        
        # 【新增】获取详细状态信息
        health_status = cls._get_health_status(npc)
        combat_status = cls._get_combat_status(npc)
        inventory_status = cls._get_inventory_status(npc)
        relations_status = cls._get_relations_status(npc, game_ctx)
        
        print(f"[PromptBuilder] 身体状况: {health_status[:50] if health_status else '(无)'}...")
        print(f"[PromptBuilder] 战斗能力: {combat_status[:50] if combat_status else '(无)'}...")
        print(f"[PromptBuilder] 背包物品: {inventory_status[:50] if inventory_status else '(无)'}...")
        print(f"[PromptBuilder] 人际关系: {relations_status[:50] if relations_status else '(无)'}...")
        
        # 【新增】获取玩家评估（让NPC知道玩家的实力和状况）
        player_assessment = cls._get_player_assessment(npc, game_ctx)
        print(f"[PromptBuilder] 玩家评估: {player_assessment[:80] if player_assessment else '(无)'}...")
        
        # 构建上下文
        ctx = NPCContext(
            npc_id=npc.id,
            name=npc.name,
            job=getattr(npc, 'job', 'NONE'),
            power_type=getattr(npc, 'power_type', '民'),
            org_id=getattr(npc, 'org_id', 'NONE'),
            org_rank=getattr(npc, 'org_rank', 0),
            desc=getattr(npc, 'desc', ''),
            tags=getattr(npc, 'tags', []),
            morality=getattr(npc, 'morality', 50),
            wit=getattr(npc, 'wit', 5),
            charm=getattr(npc, 'charm', 5),
            strength=getattr(npc, 'strength', 5),
            bravery=getattr(npc, 'bravery', 50),
            affinity_to_player=getattr(npc, 'affinity_to_player', 0),
            knows_player=getattr(npc, 'knows_player', False),
            emotion=getattr(npc, 'emotion', 'NORMAL'),
            social_level=getattr(npc, 'social_level', 1),
            wealth_level=getattr(npc, 'wealth_level', 1),
            eco_status=getattr(npc, 'eco_status', 'POOR'),
            # 【新增】当前状态
            current_state=current_state,
            current_activity=current_activity,
            current_location=current_location,
            # 【新增】任务上下文
            active_quest_info=quest_info,
            quest_role=quest_role,
            # 【新增】与玩家的距离
            distance_to_player=distance_to_player,
            # 【新增】详细状态信息
            health_status=health_status,
            combat_status=combat_status,
            inventory_status=inventory_status,
            relations_status=relations_status,
            # 【新增】玩家评估
            player_assessment=player_assessment,
        )
        
        # 添加记忆
        if memory_system:
            ctx.memory_summary = memory_system.format_memories_for_prompt()
            print(f"[PromptBuilder] 记忆摘要长度: {len(ctx.memory_summary)} 字符")
            if ctx.memory_summary:
                print(f"[PromptBuilder] 记忆摘要内容:\n{ctx.memory_summary[:500]}...")
            else:
                print(f"[PromptBuilder] 记忆摘要为空！")
        else:
            print(f"[PromptBuilder] 未提供 memory_system")
        
        # 传递memory_system用于双轨制判断
        return cls.build_system_prompt(ctx, scenario, memory_system)
    
    @classmethod
    def _get_quest_context_for_npc(cls, npc) -> tuple:
        """
        获取与NPC相关的任务上下文
        
        Returns:
            (quest_info: str, quest_role: str) 
            - quest_info: 任务描述信息
            - quest_role: NPC在任务中的角色 (giver/target/related/none)
        """
        try:
            from src.quest_system import QuestManager, get_npc_name_by_id
            quest_mgr = QuestManager.get_instance()
            
            print(f"[PromptBuilder] _get_quest_context_for_npc: QuestManager实例={quest_mgr is not None}")
            
            if not quest_mgr:
                print(f"[PromptBuilder] QuestManager.get_instance() 返回 None！")
                return ("", "")
            
            # 获取当前活跃任务
            active_quest = quest_mgr.get_active_quest()
            print(f"[PromptBuilder] 活跃任务: {active_quest}")
            print(f"[PromptBuilder] 活跃任务ID: {quest_mgr._active_quest_id if hasattr(quest_mgr, '_active_quest_id') else '?'}")
            
            if not active_quest:
                print(f"[PromptBuilder] 无活跃任务")
                return ("", "")
            
            # 提取任务基本信息（使用QuestData的实际字段）
            quest_title = getattr(active_quest, 'title', '未知任务')
            quest_desc = getattr(active_quest, 'desc', '')
            quest_target = getattr(active_quest, 'target', '')  # 任务目标描述
            quest_type = getattr(active_quest, 'type', '')      # 任务类型
            submit_npc = getattr(active_quest, 'submit_npc', '')  # 提交任务的NPC
            
            # 获取任务状态
            quest_status = quest_mgr.quest_status if hasattr(quest_mgr, 'quest_status') else 0
            
            # 构建任务描述
            quest_info_parts = [f"任务名称：{quest_title}"]
            if quest_desc:
                quest_info_parts.append(f"任务描述：{quest_desc[:80]}")
            if quest_target:
                quest_info_parts.append(f"任务目标：{quest_target}")
            
            # 状态描述
            status_desc_map = {
                0: "可接取",
                1: "进行中", 
                2: "可提交",
                3: "已完成"
            }
            quest_info_parts.append(f"任务状态：{status_desc_map.get(quest_status, '未知')}")
            quest_info = "\n".join(quest_info_parts)
            
            # 判断NPC角色
            npc_id = str(npc.id) if npc.id else ""
            npc_name = npc.name if hasattr(npc, 'name') else ""
            
            # 检查是否是任务提交者/发布者（submit_npc字段）
            # submit_npc可能是ID或名称
            if submit_npc and submit_npc != '9000':
                # 转换submit_npc为名称进行比较
                submit_npc_name = get_npc_name_by_id(submit_npc) if submit_npc else ""
                
                if str(submit_npc) == npc_id or submit_npc_name == npc_name or submit_npc == npc_name:
                    return (quest_info, "giver")
            
            # 检查任务目标中是否包含NPC名称（例如"与鱼西施交谈"）
            if quest_target and npc_name:
                if npc_name in quest_target:
                    return (quest_info, "target")
            
        except Exception as e:
            print(f"[PromptBuilder] 获取任务上下文失败: {e}")
            import traceback
            traceback.print_exc()
        
        return ("", "")
    
    @classmethod
    def _get_state_description(cls, npc) -> str:
        """将NPC状态枚举转换为中文描述"""
        state = getattr(npc, 'state', None)
        if state is None:
            return "闲着"
        
        # 状态映射（使用字符串值直接匹配，避免导入问题）
        state_map = {
            "IDLE": "闲着没事做",
            "MOVING": "正在走路/赶路",
            "WORKING": "在忙工作",
            "TRADING": "在做买卖",
            "CHATTING": "在跟别人说话",
            "EVENT": "在处理事情",
            "MEETING": "在参加会议/聚会",
            "WATCHING": "在观望/围观",
            "COMBAT": "在战斗中",
            "CARRYING": "在搬运东西",
            "SLEEPING": "在休息/睡觉",
            "DOWNED": "受了重伤躺着",
            "FLEEING": "正在逃跑",
            "FOLLOW": "在跟随某人",
            "GONE": "不在这里",
        }
        return state_map.get(state, "闲着")
    
    @classmethod
    def _get_location_description(cls, npc) -> str:
        """获取NPC当前位置的人类可读描述"""
        # 尝试获取目标建筑
        target_building = getattr(npc, 'target_building', None)
        if target_building and hasattr(target_building, 'name'):
            return target_building.name
        
        # 尝试获取当前位置的建筑
        current_building = getattr(npc, 'current_building', None)
        if current_building and hasattr(current_building, 'name'):
            return current_building.name
        
        # 默认
        return "在外面闲逛"
    
    @classmethod
    def _get_distance_to_player(cls, npc, game_ctx) -> str:
        """
        计算NPC与玩家的距离并返回描述
        
        Args:
            npc: NPC对象
            game_ctx: 游戏上下文（包含玩家）
            
        Returns:
            str: 距离描述（如"约5米"）
        """
        if not game_ctx or not hasattr(game_ctx, 'player'):
            return ""
        
        try:
            # 【重要】如果正在对话，玩家必然在NPC身边
            # 检查是否正在与这个NPC对话
            try:
                from src.llm import get_chat_integration
                chat_integration = get_chat_integration()
                if chat_integration and chat_integration.is_chatting():
                    current_chat_npc = getattr(chat_integration, '_current_npc', None)
                    if current_chat_npc and getattr(current_chat_npc, 'id', None) == getattr(npc, 'id', -1):
                        # 正在与这个NPC对话，强制返回近距离
                        return "就在面前（正在交谈）"
            except:
                pass
            
            import math
            player = game_ctx.player
            
            # 计算像素距离
            distance_px = math.hypot(
                npc.rect.centerx - player.rect.centerx,
                npc.rect.centery - player.rect.centery
            )
            
            # 【调整比例】游戏中角色碰撞箱大约30像素宽 ≈ 成年人0.5米肩宽
            # 因此 1像素 ≈ 0.017米（而非0.5米）
            # 简化为：30像素 = 1米 → 1像素 ≈ 0.033米
            distance_m = distance_px * 0.033
            
            # 生成描述
            if distance_m < 2:
                return "就在身边（约1米）"
            elif distance_m < 5:
                return f"很近（约{int(distance_m)}米）"
            elif distance_m < 15:
                return f"不远（约{int(distance_m)}米）"
            elif distance_m < 50:
                return f"有些距离（约{int(distance_m)}米）"
            else:
                return f"较远（约{int(distance_m)}米）"
                
        except Exception as e:
            print(f"[PromptBuilder] 计算距离失败: {e}")
            return ""
    
    @classmethod
    def build_opening_prompt(cls, npc, memory_system=None) -> str:
        """
        构建开场白提示词（NPC主动搭话）
        
        用于：玩家接近NPC时，NPC的第一句话
        """
        base_prompt = cls.build_from_npc(npc, memory_system, "chat")
        
        # 根据记忆生成额外的上下文提示
        memory_context = ""
        if memory_system:
            # 检查是否有与玩家相关的重要记忆
            player_memories = memory_system.get_memories_about_player(max_count=3)
            if player_memories:
                important_ones = [m for m in player_memories if m.importance >= 4]
                if important_ones:
                    memory_hints = [m.content for m in important_ones[:2]]
                    memory_context = f"\n【重要：你对玩家有以下深刻记忆】\n" + "\n".join(f"- {h}" for h in memory_hints)
                    memory_context += "\n请务必在开场白中体现这些记忆对你的影响！"
        
        opening_instruction = f"""
【特殊指令：开场白】
玩家刚刚靠近你，请主动打招呼或开口说话。
{memory_context}

规则：
- 如果记忆中玩家帮助过你：表现出感激、亲近，可能主动道谢
- 如果记忆中玩家伤害过你：表现出警惕、敌意，甚至害怕
- 如果记忆中有与玩家的仇恨：可能直接挑衅或回避
- 如果不认识玩家：根据你的身份给出合适的反应（好奇/警惕/无视等）
- 开场白要简短，1-2句话，但必须体现你对玩家的真实态度
"""
        return base_prompt + opening_instruction
    
    @classmethod
    def build_farewell_prompt(cls, npc, memory_system=None) -> str:
        """
        构建告别提示词
        
        用于：对话结束时NPC的告别语
        """
        base_prompt = cls.build_from_npc(npc, memory_system, "chat")
        
        farewell_instruction = """
【特殊指令：告别】
对话即将结束，请说一句告别语。
- 根据这次对话的情况和好感度变化决定态度
- 如果对话愉快：热情/友好的告别
- 如果对话不愉快：冷淡/不耐烦的告别
- 告别语要简短，1句话
"""
        return base_prompt + farewell_instruction
    
    @classmethod
    def build_summary_prompt(cls, npc_name: str, conversation_log: List[str]) -> str:
        """
        构建对话总结提示词
        
        用于：将对话记录压缩为简短的记忆
        """
        conv_text = "\n".join(conversation_log[-10:])  # 只取最近10句
        
        return f"""请将以下{npc_name}与玩家的对话总结为1-2句话的记忆：

{conv_text}

总结要求：
1. 用{npc_name}的第一人称
2. 概括对话的主要内容和结果
3. 记录玩家是否做出了承诺或请求
4. 50字以内

直接输出总结内容，不要加任何格式："""

    # ═══════════════════════════════════════════════════════════════
    # 【新增】NPC详细状态获取方法
    # ═══════════════════════════════════════════════════════════════
    
    @classmethod
    def _get_health_status(cls, npc) -> str:
        """获取NPC的身体状况描述"""
        try:
            hp = getattr(npc, 'hp', 100)
            max_hp = getattr(npc, 'max_hp', 100)
            
            if max_hp <= 0:
                max_hp = 100
            
            hp_percent = (hp / max_hp) * 100
            
            lines = []
            if hp_percent >= 90:
                lines.append(f"- 我身体很好，精力充沛（生命值：{hp}/{max_hp}）")
            elif hp_percent >= 60:
                lines.append(f"- 我有些小伤，但不碍事（生命值：{hp}/{max_hp}）")
            elif hp_percent >= 30:
                lines.append(f"- 我受了伤，需要休息（生命值：{hp}/{max_hp}）")
            else:
                lines.append(f"- 我伤势很重，快撑不住了（生命值：{hp}/{max_hp}）")
            
            # 检查饥饿状态
            hunger = getattr(npc, 'hunger', 100)
            if hunger < 30:
                lines.append("- 我饿得很，需要吃东西")
            
            return "\n".join(lines)
        except Exception as e:
            return ""
    
    @classmethod
    def _get_combat_status(cls, npc) -> str:
        """获取NPC的战斗能力描述"""
        try:
            attack = getattr(npc, 'attack', 10)
            defense = getattr(npc, 'defense', 5)
            strength = getattr(npc, 'strength', 5)
            
            lines = []
            
            # 攻击力评估
            if attack >= 30:
                lines.append(f"- 我武艺高强，一般人不是我对手（攻击力：{attack}）")
            elif attack >= 15:
                lines.append(f"- 我有些身手，能打几下（攻击力：{attack}）")
            else:
                lines.append(f"- 我不擅长打架，尽量避免冲突（攻击力：{attack}）")
            
            # 防御力评估
            if defense >= 20:
                lines.append(f"- 我防御不错，能扛几下（防御力：{defense}）")
            
            # 检查是否有武器
            equipment = getattr(npc, 'equipment', {})
            weapon = equipment.get('weapon') if isinstance(equipment, dict) else None
            if weapon:
                weapon_name = getattr(weapon, 'name', str(weapon))
                lines.append(f"- 我带着{weapon_name}")
            
            return "\n".join(lines)
        except Exception as e:
            return ""
    
    @classmethod
    def _get_inventory_status(cls, npc) -> str:
        """获取NPC的背包物品描述"""
        try:
            inventory = getattr(npc, 'inventory', [])
            money = getattr(npc, 'money', 0)
            
            # 处理字典类型的 inventory（转换为列表）
            if isinstance(inventory, dict):
                inventory = list(inventory.values())
            
            lines = []
            
            # 钱财
            if money >= 1000:
                lines.append(f"- 我身上有{money}文钱，算是有些积蓄")
            elif money >= 100:
                lines.append(f"- 我身上有{money}文钱")
            elif money > 0:
                lines.append(f"- 我身上只有{money}文钱，不太宽裕")
            else:
                lines.append("- 我身上没什么钱")
            
            # 背包物品
            if inventory and len(inventory) > 0:
                item_names = []
                for item in inventory[:5]:  # 只显示前5个
                    if hasattr(item, 'name'):
                        item_names.append(item.name)
                    elif isinstance(item, dict) and 'name' in item:
                        item_names.append(item['name'])
                    elif isinstance(item, str):
                        item_names.append(item)
                
                if item_names:
                    lines.append(f"- 我身上带着：{', '.join(item_names)}")
                    if len(inventory) > 5:
                        lines.append(f"  （还有{len(inventory)-5}件其他东西）")
            else:
                lines.append("- 我没带什么特别的东西")
            
            return "\n".join(lines)
        except Exception as e:
            return ""
    
    @classmethod
    def _get_relations_status(cls, npc, game_ctx=None) -> str:
        """获取NPC的人际关系描述"""
        try:
            affinity = getattr(npc, 'affinity', {})
            
            if not affinity:
                return "- 我在这里认识的人不多"
            
            lines = []
            
            # 【关键】从game_ctx获取玩家名字，用于替换ID 9999
            player_name = None
            if game_ctx and hasattr(game_ctx, 'player') and game_ctx.player:
                player_name = getattr(game_ctx.player, 'name', None)
            
            # 按好感度排序
            sorted_relations = sorted(affinity.items(), key=lambda x: x[1], reverse=True)
            
            friends = []
            enemies = []
            
            for target_id, aff_value in sorted_relations[:10]:  # 只取前10个
                # 获取名字 - 优先从全局NPC列表获取，玩家ID特殊处理
                target_name = cls._get_entity_name_by_id(target_id, player_name)
                
                if aff_value >= 50:
                    friends.append(f"{target_name}(好感{aff_value})")
                elif aff_value <= -30:
                    enemies.append(f"{target_name}(好感{aff_value})")
            
            if friends:
                lines.append(f"- 我的朋友/熟人：{', '.join(friends[:3])}")
            
            if enemies:
                lines.append(f"- 我不喜欢的人：{', '.join(enemies[:3])}")
            
            if not friends and not enemies:
                lines.append("- 我和大多数人关系一般")
            
            return "\n".join(lines)
        except Exception as e:
            return ""
    
    @classmethod
    def _get_entity_name_by_id(cls, entity_id, player_name: str = None) -> str:
        """
        根据实体ID获取名字（支持玩家和NPC）
        
        Args:
            entity_id: 实体ID
            player_name: 玩家名字（如果已知，用于替换ID 9999）
        """
        try:
            entity_id_str = str(entity_id)
            
            # 玩家ID特殊处理（ID 9999 是玩家）
            if entity_id_str == '9999' or entity_id == 9999:
                # 如果已传入玩家名字，直接使用
                if player_name:
                    return player_name
                
                # 尝试从全局获取玩家名字（备用方案）
                try:
                    from src.llm import get_chat_integration
                    chat = get_chat_integration()
                    if chat and hasattr(chat, '_current_ctx') and chat._current_ctx:
                        ctx = chat._current_ctx
                        if hasattr(ctx, 'player') and ctx.player:
                            return getattr(ctx.player, 'name', '玩家')
                except:
                    pass
                
                return "玩家"
            
            # 尝试从quest_system获取NPC名字
            try:
                from src.quest_system import ID_TO_NAME
                if entity_id_str in ID_TO_NAME:
                    return ID_TO_NAME[entity_id_str]
            except:
                pass
            
            # 尝试从NPC_SEEDS获取
            try:
                from src.data.character_seeds import SEEDS
                npc_index = int(entity_id) - 8000
                if 0 <= npc_index < len(SEEDS):
                    return SEEDS[npc_index]['name']
            except:
                pass
            
            return f"某人({entity_id})"
        except Exception as e:
            return f"某人"
    
    # ═══════════════════════════════════════════════════════════════
    # 【重构】玩家评估 - 使用通用的 CharacterInfoExtractor
    # ═══════════════════════════════════════════════════════════════
    
    @classmethod
    def _get_player_assessment(cls, npc, game_ctx) -> str:
        """
        获取NPC对玩家的评估（包括玩家的实力、装备、身份等）
        
        【重构】现在使用通用的 CharacterInfoExtractor 来提取信息，
        实现玩家和NPC的平权设计。
        """
        if not game_ctx or not hasattr(game_ctx, 'player') or not game_ctx.player:
            return ""
        
        try:
            # 使用通用提取器获取双方信息
            npc_info = CharacterInfoExtractor.extract(npc, game_ctx)
            player_info = CharacterInfoExtractor.extract(game_ctx.player, game_ctx)
            
            # 使用通用方法构建完整评估
            return CharacterInfoExtractor.build_full_assessment(
                observer_info=npc_info,
                target_info=player_info,
                power_type_desc=cls.POWER_TYPE_DESC,
                org_desc=cls.ORG_DESC
            )
            
        except Exception as e:
            print(f"[PromptBuilder] 获取玩家评估失败: {e}")
            import traceback
            traceback.print_exc()
            return ""
