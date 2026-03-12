# --- src/entities/npc.py ---
import pygame
import random
import math
from src.definitions import *
from src.utils import Appearance, log_game_event
from .base import CardBase
from .building import Building
from .resource import Resource  # <---
import json # <--- 
from src.item_system import ItemManager 
from src.npc_personality import NPCPersonality, generate_personality_from_job, get_social_credit_system

# ═══════════════════════════════════════════════════════════════════
# 势力颜色系统 - 让玩家直观感知社会分层
# 【重设计】使用深色系确保白字清晰可读，标签文字始终为白色
# ═══════════════════════════════════════════════════════════════════
POWER_COLORS = {
    '士': (128, 90, 200),     # 深紫色 - 朝廷官员（高贵感）
    '农': (76, 140, 43),      # 深绿色 - 地主农户（田园感）
    '工': (200, 120, 50),     # 深橙色 - 工匠（铁锈感）
    '商': (180, 140, 20),     # 深金色 - 商贾（铜钱色）
    '学': (50, 120, 180),     # 深蓝色 - 学者/僧人（沉稳感）
    '兵': (180, 50, 50),      # 深红色 - 军人护卫（血色）
    '游': (30, 130, 150),     # 深青色 - 江湖人士（神秘感）
    '匪': (100, 65, 55),      # 深褐色 - 盗匪（泥土色）
    '民': (110, 110, 110),    # 深灰色 - 普通百姓（朴素感）
}

# 组织简称映射
ORG_SHORT_NAMES = {
    'kaifeng_fu': '开封府',
    'shenhou_fu': '神侯府',
    'gao_manor': '高府',
    'tianshui_alley': '商会',
    'taixue': '太学',
    'daxiangguo': '相国寺',
    'beggar_gang': '丐帮',
    'shizizhipo': '十字坡',
    'heifeng_zhai': '黑风寨',
    'qinglang_bang': '青狼帮',
    'luopo_gang': '骆驼帮',
    'NONE': '',
    None: '',
}

# 等级标识符号
RANK_SYMBOLS = {
    5: '[领]',      # 首领
    4: '◆',      # 长老
    3: '▲',      # 头目
    2: '●',      # 核心
    1: '○',      # 门徒
    0: '',       # 无组织
}

class NPC(CardBase):
    def __init__(self, data):

        #data是什么？

        # 初始随机位置
        start_x, start_y = random.randint(100, 600), random.randint(100, 400)
        CardBase.__init__(self, start_x, start_y, CARD_W, CARD_H, COLOR_NPC_CARD)
        
        #第一部分：属性界面
        #基础属性
        self.id = int(data.get('id', 0))
        self.name = data.get('name', '无名氏')
        self.job = data.get('job', 'NONE')         
        self.hidden_job = data.get('hidden_job', 'NONE')
        self.card_type = CARD_TYPE_HUMAN        

        # 生存属性
        self.cold = 0 #寒冷值
        self.hunger = 0 #饥饿值
        self.dissatisfaction = 0 #不满值
        self.survival_timer = 0 # 计时器

        

        # 标签（必须在 generate_personality_from_job 之前初始化）
        raw_tags = data.get('tags', '') 
        self.tags = raw_tags.split(';') if raw_tags else []
        
        # 背包和装备槽（必须在 _init_combat_stats 之前初始化）
        self.inventory = {}
        self.equip_weapon  = None   # e.g. '铁剑' / '朴刀'
        self.equip_armor   = None   # e.g. '皮甲' / '锁子甲'
        self.equip_clothing = None  # e.g. '棉袄' / '粗布衣'
        
        # 能力属性
        self._init_core_stats(data)
         # 战斗属性 
         # 计算攻击、防御、血量
        self._init_combat_stats(data)        
        # --- 战斗仇恨---
        # hatred: {npc_id: hate_value}，记录对每个NPC的仇恨值
        self.hatred = {}


        #第二部分：内心界面       
       #情绪？
        self.emotion = data.get('emotion', EMOTION_NORMAL)
        # 性格特质        
        personality_data = data.get('personality')
        if personality_data:
            # 从存档数据加载
            if isinstance(personality_data, dict):
                self.personality = NPCPersonality.from_dict(personality_data)
            else:
                self.personality = generate_personality_from_job(self.job, self.tags)
        else:
            # 根据职业和标签自动生成
            self.personality = generate_personality_from_job(self.job, self.tags)    
        # 初始困境
        self.initial_dilemma = data.get('initial_dilemma', None)
        # 当前困境状态（由StoryDirector管理）
        self.current_dilemma = None
        # 困境阶段
        self.dilemma_phase = None  # 'latent', 'surfaced', 'escalated', 'crisis', 'aftermath'
        

        #第?部分？组织
        # 经济与社会地位
        self.eco_status = data.get('eco_status', ECO_POOR)
        self.soc_status = data.get('soc_status', SOC_COMMON)
        self.freedom = data.get('freedom', FREE_FULL)
        self.org_id = data.get('org_id', 'NONE')
        self.rank = int(data.get('rank', 0))
        
         # 组织与社会阶级
        self.power_type = data.get('power_type', '民')      # 势力类型
        self.org_role = data.get('org_role', None)          # 组织角色: LEADER/MEMBER/BODYGUARD
        self.org_rank = int(data.get('org_rank', 0))        # 组织等级 0-5
        self.social_level = int(data.get('social_level', 1)) # 社会等级 1-5
        self.wealth_level = int(data.get('wealth_level', 1)) # 财富等级 1-5
        self.influence_level = int(data.get('influence_level', 1)) # 影响力等级 1-5

        self.desc = data.get('desc', '')
        
        # 安全状态（影响是否参与AI和事件）
        self.safety = data.get('safety', SAFETY_NORMAL)
        
        #第三部分。关系界面
        # 人际关系，也存在冗余定义
        # 人际关系
        self.relations = {}
        raw_rels = data.get('relations_json', '{}')
        #NPC之间的好感度 {npc_id: score}
        self.affinity = {}
        #对玩家的态度，不应该额外存储，而是需要从affinity里面get
        self.affinity_to_player = 0      # 对玩家好感度 (-100 ~ +100)
        self.knows_player = False        # 是否认识玩家
        self.last_interaction_day = 0    # 上次与玩家互动的天数
        #人情值也没必要单独开一个系统，感觉直接用relationDebt就可以了，毕竟它也是NPC之间的关系属性
        self._social_credit_system = get_social_credit_system()
        try:
            if raw_rels:
                self.relations = json.loads(raw_rels)
        except:
            print(f"Error parsing relations for {self.name}")


        
        # 其他玩法功能属性
        # 招募相关
        self.is_follower = False # 是否是门客
        self.recruit_cost = 500 
        self.recruit_fame_req = 100         
        # 流民标记
        self.is_refugee = False
        # 初始装备和资源        
        self._update_recruit_cost()
        self._give_starter_kit()




        # --- 渲染与物理 ---
        self.sprite_w = 28
        self.sprite_h = 42
        # 初始化私有像素坐标（在 __init__ 中直接访问是安全的）
        self._pixel_x = float(self.rect.x)
        self._pixel_y = float(self.rect.y)
        

        # 寻路与防卡死
        self.debug_next_waypoint = None
        self.stuck_timer = 0         # 记录卡住的帧数
        self.last_frame_pos = (self.pixel_x, self.pixel_y) # 上一帧的坐
        self.stuck_check_timer = 0      # 计时器，每隔 N 帧检查一次
        self.stuck_check_pos = (self.pixel_x, self.pixel_y) # 上一次检查时的坐标
        self.stuck_accumulated = 0      # 连续判定为卡死的次数

        # AI 状态机
        #这两个属性是用来干什么的？感觉有点重复了
        self.work_mode = "DEFAULT" 
        self.ai_mode = "DEFAULT"       # DEFAULT: 自由/工作, FOLLOW: 跟随玩家, IDLE: 待机/摸鱼

        self.state = STATE_IDLE
        self.state_timer = 0
        self.clear_movement_target("初始化")
        self.move_speed = 80.0        # 单位：px/s，每0.1s步长移动8px
        self.ai_reason = "初始化..."         
        #AI决策
        self.decision_timer = 0
        self.decision_interval = 30 + random.randint(0, 20) # 0.5 ~ 0.8秒决策一次
        #记忆
        self.memory = [] # 记忆列表，存储最近的事件和互动（用于AI决策）
        
        # 事件系统接口
        self.active_event_data = None 
        self.event_partner = None
        self.event_cooldown =0        
        # 事件导致的隐身
        self.is_invisible = False     # 是否处于隐身状态（不参与AI、不渲染、不碰撞）

       
        
       
        # --- 外观加载 (仅头像) ---
        # 头像路径：head_icon目录
        avatar_path = Appearance.get_avatar_path(self.name)
        self.appearance = Appearance(head_path=avatar_path, size=(64, 64))
        

        
        # 解析关系数据用于护卫系统
        self.relations_data = {}
        try:
            if self.relations:
                self.relations_data = self.relations.copy()
        except:
            pass
        
        # --- 原子行为队列系统 (新增) ---
        from src.atomic_actions import ActionQueue
        self.action_queue = ActionQueue(self)
        # aggro_target: 当前锁定的战斗目标 (npc对象引用)，None=未锁定
        self.aggro_target = None


        # 仇恨阈值：超过此值才进入战斗
        # 【修改】降低阈值，让NPC更快响应同伴被攻击
        _is_villain = (self.job in ['BANDIT', 'THUG'] or 'VILLAIN' in self.tags)
        if _is_villain:
            self.aggro_threshold = 10   # 山贼/泼皮：极低阈值（好斗）
        elif self.job in ['GUARD', 'SOLDIER']:
            self.aggro_threshold = 15   # 护卫/士兵：低阈值（警惕性高）
        else:
            self.aggro_threshold = 25   # 普通人：中等阈值（从40降低到25）
        # 仇恨衰减计时器（错开初始值，避免所有NPC同帧计算）
        self.hatred_decay_timer = random.randint(0, 180)
        
        # 任务属性        
        self.quest_icon_active = False # 是否头顶有任务
       
    
    @property
    def money(self):
        return self.inventory.get(ITEM_COIN, 0)

    @money.setter
    def money(self, value):
        # 确保 value 是整数
        val = int(value)
        if val <= 0:
            if ITEM_COIN in self.inventory:
                del self.inventory[ITEM_COIN]
        else:
            self.inventory[ITEM_COIN] = val
    
    def _give_starter_kit(self):
        """
        初始背包：根据职业给予不同的启动资源
        【阶段2】商人需要启动资金，官员有俸禄储蓄，普通人有少量铜钱
        """
        # 根据社会等级给予基础铜钱
        base_money = 0
        social_level = getattr(self, 'social_level', 1)
        
        if self.job == 'MERCHANT':
            # 商人：需要较多启动资金进货
            base_money = 50 + social_level * 30  # 80-200铜
        elif self.job == 'OFFICIAL':
            # 官员：有俸禄储蓄
            base_money = 30 + social_level * 20  # 50-130铜
        elif self.job == 'SCHOLAR':
            # 学者：有些积蓄
            base_money = 20 + social_level * 10  # 30-70铜
        elif self.job in ['FARMER', 'ARTISAN']:
            # 农民/工匠：有少量积蓄
            base_money = 10 + social_level * 5   # 15-35铜
        elif self.job in ['BANDIT', 'THUG']:
            # 匪类：有些掠夺所得
            base_money = 15 + social_level * 10  # 25-65铜
        elif self.job == 'NONE':
            # 流民：一贫如洗
            base_money = random.randint(0, 5)
        else:
            # 其他：少量铜钱
            base_money = 5 + social_level * 3
        
        if base_money > 0:
            self.inventory[ITEM_COIN] = base_money
    
    # ═══════════════════════════════════════════════════════════════════
    # 战斗属性初始化 - 根据势力类型、社会等级、组织等级动态计算
    # ═══════════════════════════════════════════════════════════════════
    def _init_combat_stats(self, data):
        """
        根据势力类型和社会等级初始化战斗属性（HP、ATK、DEF）
        并分配初始装备
        """
        # 从数据中读取势力信息（可能还未赋值到self）
        power_type = data.get('power_type', '民')
        social_level = int(data.get('social_level', 1))
        org_rank = int(data.get('org_rank', 0) or data.get('rank', 0))
        org_role = data.get('org_role', None)
        tags = data.get('tags', '')
        if isinstance(tags, str):
            tags = tags.split(';') if tags else []
        
        # ─── 基础战斗属性（根据势力类型） ───
        # 格式：(base_hp, base_atk, base_def)
        power_combat_base = {
            '士': (80, 3, 2),      # 官员：血少，攻低，有点防御
            '农': (100, 4, 1),     # 地主：血多，中攻，低防
            '工': (90, 5, 0),      # 工匠：中血，攻稍高（工具），无防
            '商': (70, 2, 1),      # 商人：血少，攻低，低防
            '学': (60, 2, 0),      # 学者：血最少，攻最低，无防
            '兵': (120, 10, 5),    # 军人：血最多，攻最高，防最高
            '游': (100, 8, 3),     # 江湖：血中，攻高，中防
            '匪': (90, 8, 2),      # 盗匪：中血，攻高，低防
            '民': (80, 3, 0),      # 平民：中血，低攻，无防
        }
        base_hp, base_atk, base_def = power_combat_base.get(power_type, (80, 3, 0))
        
        # ─── 社会等级加成 ───
        # 社会等级1-5，每级+10%属性
        level_multiplier = 1.0 + (social_level - 1) * 0.15
        
        # ─── 组织等级加成 ───
        # 组织等级0-5，每级+5%属性
        rank_multiplier = 1.0 + org_rank * 0.08
        
        # ─── 特殊角色加成 ───
        role_bonus_hp = 0
        role_bonus_atk = 0
        role_bonus_def = 0
        
        if org_role == 'LEADER':
            role_bonus_hp = 30
            role_bonus_atk = 3
            role_bonus_def = 2
        elif org_role == 'BODYGUARD':
            role_bonus_hp = 20
            role_bonus_atk = 5
            role_bonus_def = 3
        
        # ─── 标签加成 ───
        if 'STRONG' in tags:
            role_bonus_hp += 20
            role_bonus_atk += 3
        if 'WARRIOR' in tags:
            role_bonus_atk += 5
            role_bonus_def += 2
        if 'HERO' in tags:
            role_bonus_hp += 30
            role_bonus_atk += 5
        if 'VILLAIN' in tags:
            role_bonus_atk += 3
        
        # ─── 计算最终属性 ───
        self.hp = int((base_hp + role_bonus_hp) * level_multiplier * rank_multiplier)
        self.max_hp = self.hp
        self.atk = int((base_atk + role_bonus_atk) * level_multiplier * rank_multiplier)
        self.def_ = int((base_def + role_bonus_def) * level_multiplier * rank_multiplier)

         # 攻击速度：两次攻击之间的间隔（毫秒），越小打得越快
        self.atk_speed = int(data.get('atk_speed', 1000))
        self.attack_cooldown = 0               # 当前冷却计时（毫秒）
        self.knockback_timer = 0              # 被击退后的硬直计时（毫秒），>0 时不接受新的移动指令
        
        # ─── 分配初始装备 ───
        self._assign_starting_equipment(power_type, social_level, org_role, tags)
    
    def _assign_starting_equipment(self, power_type, social_level, org_role, tags):
        """
        根据势力类型和等级分配初始装备
        装备会同时放入背包并装备上
        """
        # 武器分配
        if power_type == '兵' or org_role == 'BODYGUARD' or 'WARRIOR' in tags:
            # 军人/护卫/武者：根据等级分配武器
            if social_level >= 4:
                self.equip_weapon = '铁剑'  # +8攻击
                self.inventory['铁剑'] = self.inventory.get('铁剑', 0) + 1
            else:
                self.equip_weapon = '朴刀'  # +5攻击
                self.inventory['朴刀'] = self.inventory.get('朴刀', 0) + 1
        elif power_type == '游' or power_type == '匪':
            # 江湖/盗匪：基本都有武器
            self.equip_weapon = '朴刀'
            self.inventory['朴刀'] = self.inventory.get('朴刀', 0) + 1
        elif social_level >= 4 and org_role == 'LEADER':
            # 高等级首领可能有防身武器
            self.equip_weapon = '铁剑'
            self.inventory['铁剑'] = self.inventory.get('铁剑', 0) + 1
        
        # 护甲分配
        if power_type == '兵':
            # 军人必有护甲
            if social_level >= 3:
                self.equip_armor = '锁子甲'  # +12防御
                self.inventory['锁子甲'] = self.inventory.get('锁子甲', 0) + 1
            else:
                self.equip_armor = '皮甲'    # +6防御
                self.inventory['皮甲'] = self.inventory.get('皮甲', 0) + 1
        elif org_role == 'BODYGUARD':
            # 护卫有皮甲
            self.equip_armor = '皮甲'
            self.inventory['皮甲'] = self.inventory.get('皮甲', 0) + 1
        elif 'HERO' in tags or 'WARRIOR' in tags:
            # 英雄/武者
            self.equip_armor = '皮甲'
            self.inventory['皮甲'] = self.inventory.get('皮甲', 0) + 1
        
        # 服装分配（根据经济状况）
        if social_level >= 3:
            self.equip_clothing = '棉袄'    # +25保暖
            self.inventory['棉袄'] = self.inventory.get('棉袄', 0) + 1
        elif social_level >= 2:
            self.equip_clothing = '粗布衣'  # +10保暖
            self.inventory['粗布衣'] = self.inventory.get('粗布衣', 0) + 1
        # 等级1的穷人没有额外衣服
    
    def _init_core_stats(self, data):
        """
        根据势力类型初始化四大核心属性（力量、敏捷、智力、魅力）
        """
        power_type = data.get('power_type', '民')
        social_level = int(data.get('social_level', 1))
        tags = data.get('tags', '')
        if isinstance(tags, str):
            tags = tags.split(';') if tags else []
        
        # ─── 势力类型基础属性 ───
        # 格式：(strength, agility, wit, charm)
        power_stats_base = {
            '士': (3, 3, 8, 6),      # 官员：智力魅力高
            '农': (7, 4, 3, 3),      # 地主：力量高
            '工': (6, 5, 5, 3),      # 工匠：力量敏捷均衡
            '商': (3, 5, 6, 8),      # 商人：魅力智力高
            '学': (2, 3, 9, 5),      # 学者：智力最高
            '兵': (8, 6, 3, 3),      # 军人：力量敏捷高
            '游': (6, 8, 4, 5),      # 江湖：敏捷最高
            '匪': (7, 6, 3, 2),      # 盗匪：力量敏捷高，魅力低
            '民': (5, 5, 5, 5),      # 平民：均衡
        }
        base_str, base_agi, base_wit, base_charm = power_stats_base.get(power_type, (5, 5, 5, 5))
        
        # 社会等级加成
        level_bonus = (social_level - 1) * 1
        
        # 标签加成
        tag_bonus_str = 3 if 'STRONG' in tags else 0
        tag_bonus_wit = 3 if 'SMART' in tags else 0
        tag_bonus_charm = 3 if 'BEAUTIFUL' in tags or 'FAMOUS' in tags else 0
        
        self.strength = base_str + level_bonus + tag_bonus_str
        self.agility = base_agi + level_bonus
        self.wit = base_wit + level_bonus + tag_bonus_wit
        self.charm = base_charm + level_bonus + tag_bonus_charm
        
    def reveal_job(self):
        """流民加入城镇，觉醒真实职业"""
        if self.job == 'NONE' and self.hidden_job != 'NONE':
            self.job = self.hidden_job
            return True, f"{self.name} 展现出了 {self.job} 的才能！"
        return False, ""

    # ═══════════════════════════════════════════════════════════════
    # 【新增】记忆系统 - 用于AI叙事
    # ═══════════════════════════════════════════════════════════════
    def add_memory(self, event_type, target_id=None, target_name="", description="", importance=1):
        """
        添加一条记忆，用于AI叙事和人际关系追踪
        
        Args:
            event_type: 事件类型，如 'SAVED_BY', 'ATTACKED_BY', 'TRADE', 'HELPED_BY' 等
            target_id: 相关NPC的ID（如果有）
            target_name: 相关NPC的名字（可选，用于显示）
            description: 可读描述
            importance: 重要性等级 1-5
        """
        import time
        memory_entry = {
            'type': event_type,
            'target_id': target_id,
            'target_name': target_name,
            'desc': description,
            'importance': importance,
            'timestamp': time.time()
        }
        self.memory.append(memory_entry)
        
        # 限制记忆数量，保留最重要/最新的50条
        if len(self.memory) > 50:
            # 按重要性和时间排序，保留重要或新的
            self.memory.sort(key=lambda m: (m.get('importance', 1), m.get('timestamp', 0)), reverse=True)
            self.memory = self.memory[:50]
        
        log_game_event(f"[记忆] {self.name}: {event_type} - {description}", tag="MEMORY")
        return memory_entry
    
    def get_memories_about(self, target_id):
        """获取关于某NPC的所有记忆"""
        return [m for m in self.memory if m.get('target_id') == target_id]
    
    def get_affinity_to(self, target_id):
        """获取对某NPC的好感度"""
        return self.affinity.get(target_id, 0)
    
    def modify_affinity(self, target_id, delta):
        """修改对某NPC的好感度"""
        current = self.affinity.get(target_id, 0)
        new_val = max(-100, min(100, current + delta))  # 限制在-100到100之间
        self.affinity[target_id] = new_val
        log_game_event(f"[好感度] {self.name} 对 #{target_id}: {current} → {new_val} ({'+' if delta>=0 else ''}{delta})", tag="AFFINITY")
        return new_val
    
    def sync_affinity_to_player(self, player_id):
        """同步对玩家的好感度到快捷属性 affinity_to_player"""
        self.affinity_to_player = self.affinity.get(player_id, 0)



    def _update_recruit_cost(self):
        base = 300
        if self.eco_status == ECO_RICH: base = 2000
        elif self.eco_status == ECO_ENOUGH: base = 800
        elif self.eco_status == ECO_POOR: base = 100
        if self.soc_status == SOC_NOBLE: base *= 1.5
        elif self.soc_status == SOC_LOW: base *= 0.8
        self.recruit_cost = int(base)
        self.recruit_fame_req = int(base / 3)

    def check_eco_status_update(self):
        old_status = self.eco_status
        money = self.inventory.get(ITEM_COIN, 0)
        if money < 100: self.eco_status = ECO_POOR
        elif money < 500: self.eco_status = ECO_COMMON
        elif money < 1500: self.eco_status = ECO_ENOUGH
        else: self.eco_status = ECO_RICH
        if old_status != self.eco_status:
            self._update_recruit_cost()
            return True
        return False

    def set_initial_pos(self, world_map):
        # 根据职业让NPC出生在对应区域，增加沉浸感
        rect = world_map.city_rect
        if self.job == 'FARMER': rect = world_map.farm_rect
        elif self.job == 'MERCHANT': rect = world_map.market_rect
        elif self.job == 'THUG': rect = world_map.slum_rect
        
        tx = random.randint(rect.left, rect.right)
        ty = random.randint(rect.top, rect.bottom)
        
        self.set_pos(tx, ty) 
        self.set_movement_target(self.pixel_x, self.pixel_y, "设置初始位置") # <--- 新增：使用 set_movement_target 来设置初始位置，确保日志记录和状态同步
        
    def update_quest_icon(self, quest_manager):
        if not quest_manager:
            self.quest_icon_active = False
            return

        # 默认关闭
        self.quest_icon_active = False
        
        # 获取当前任务
        current_q = quest_manager.get_current_quest()
        if not current_q: return
        
        # 检查是否是任务相关人
        if str(self.id) == current_q.submit_npc:
            if quest_manager.quest_status == QS_AVAILABLE:
                self.quest_icon_active = True # 黄色叹号
            elif quest_manager.quest_status == QS_READY:
                self.quest_icon_active = True # 黄色问号

    def drop_item(self, item_type, all_cards, count=1):
        current_count = self.inventory.get(item_type, 0)
        
        # 检查是否是已装备的物品 - 如果是，先卸下再丢弃
        is_equipped = False
        if getattr(self, 'equip_weapon', None) == item_type:
            self.equip_weapon = None
            current_count += 1  # 装备槽里的也算
            is_equipped = True
            log_game_event(f"{self.name} 卸下武器 {item_type} 准备丢弃")
        elif getattr(self, 'equip_armor', None) == item_type:
            self.equip_armor = None
            current_count += 1
            is_equipped = True
            log_game_event(f"{self.name} 卸下护甲 {item_type} 准备丢弃")
        elif getattr(self, 'equip_clothing', None) == item_type:
            self.equip_clothing = None
            current_count += 1
            is_equipped = True
            log_game_event(f"{self.name} 卸下衣物 {item_type} 准备丢弃")
        
        if current_count <= 0: 
            print(f"[DROP] 丢弃失败：背包里没有 {item_type}")
            return False, "背包里没有这个"
        
        # 确定实际丢弃数量
        drop_count = count
        if drop_count > current_count: drop_count = current_count
        
        # 扣除库存
        self.inventory[item_type] -= drop_count
        if self.inventory[item_type] <= 0:
            del self.inventory[item_type] # 数量为0则移除key
            
        # 在脚下生成资源卡
        drop_x = self.rect.x + random.randint(-20, 20)
        drop_y = self.rect.y + 40
        
        # [关键] 传入 count
        res_card = Resource(drop_x, drop_y, item_type, count=drop_count)
        
        # 尝试稍微错开位置避免完全重叠
        res_card.rect.clamp_ip(pygame.Rect(0,0, 2000, 2000)) # 简单边界保护
        
        all_cards.append(res_card)
        
        print(f"[DROP] 成功丢弃 {item_type} x{drop_count} 到 ({drop_x}, {drop_y}), all_cards 长度: {len(all_cards)}")
        return True, f"{self.name}丢弃了 {item_type} x{drop_count}"
    def set_ai_mode(self, mode):
        self.ai_mode = mode
        if mode == "FOLLOW":
            self.ai_reason = "跟随主公"
        elif mode == "IDLE":
            self.ai_reason = "休养生息"
            self.clear_movement_target("切换到IDLE") # <--- 新增
        else:
            self.ai_reason = "自由行动"
    def update(self, all_cards, world_map, ctx, dt_ms=16):
        # 【气泡定时器】递减并清理
        if getattr(self, '_salute_bubble_timer', 0) > 0:
            self._salute_bubble_timer -= dt_ms
            if self._salute_bubble_timer <= 0:
                self._salute_bubble = None
                self._salute_bubble_timer = 0
        
        self._update_survival_stats(all_cards,ctx) 
        if self.event_cooldown > 0:
            self.event_cooldown -= 1
        # 0. 死亡/流放、重伤检查
        if self.safety in [SAFETY_DEAD, SAFETY_EXILED]:
            self.state = STATE_GONE
            return
        if self.safety == SAFETY_DOWNED:
            self.state = STATE_DOWNED
            self.clear_movement_target("重伤倒地") # <--- 新增：清理移动目标，防止AI误判
            
            # [关键] 优先保持救援状态的 ai_reason，避免被覆盖
            if self.stack_parent:
                # 位置由堆叠级联 set_pos 驱动，无需手动同步 pixel_x/y
                if not getattr(self, 'is_working', False):
                    # 检查是否正在被人背着（被救援中）
                    if hasattr(self.stack_parent, 'name') and "被" not in self.ai_reason:
                        self.ai_reason = f"重伤（被{self.stack_parent.name}背）"
                    elif "被" not in self.ai_reason:
                        self.ai_reason = "等待救治..."
            else:
                # 没有被背着，显示倒地状态
                if "被" not in self.ai_reason:
                    self.ai_reason = "重伤倒地..."
            return

        if self.ai_mode == "FOLLOW":
            player_card = next((c for c in all_cards if getattr(c, 'job', None) == 'PLAYER'), None)
            if player_card:
                self.move_speed = getattr(player_card, 'move_speed', 100.0) * 1.1 
        else:
            self.move_speed = 80.0   # 单位：px/s
        # 1. [物理层] 拖拽时拥有最高优先级，打断一切AI
        # update_drag_pos 已经调用 set_pos，rect/pixel 均已同步，无需重复赋值
        if self.dragging:
            self.state = STATE_IDLE
            self.clear_movement_target("被玩家拖拽") # <--- 
        
        if self.state == STATE_EVENT or self.state == STATE_MEETING:
            return
        
        # 【新增】逃跑状态：只需要移动，不需要AI决策
        if self.state == STATE_FLEEING:
            # 逃跑中不触发其他逻辑，只移动
            return

        # 2. [堆叠层] 作为子卡牌（被堆在建筑或人身上）
        if self.stack_parent:
            if getattr(self, 'is_doing_recipe', False):
                return
            # 位置由 ai_system 的级联 set_pos 驱动，此处只停止移动意图
            self.clear_movement_target("堆叠在别人身上，停止移动")
            
            if isinstance(self.stack_parent, NPC):
                # 排队状态处理
                in_clinic = self._is_in_clinic_queue()
                self.is_working = False
                self.work_timer = 0
                
                # 特殊处理：如果是医馆排队，显示排队状态
                if in_clinic:
                    self.ai_reason = "排队救治中"
                    
            elif isinstance(self.stack_parent, Building):
                # 直接在建筑上的处理
                if self.stack_parent.building_type == 'CLINIC':
                    # [修复] 重伤人员在医馆治疗时的ai_reason显示
                    if self.safety == SAFETY_DOWNED:
                        if getattr(self, 'is_working', False):
                            self.ai_reason = "正在治疗..."
                        else:
                            self.ai_reason = "等待治疗..."
                    
            return

        # 3. [交互层] 身上有别人（作为父卡牌），通常静止,但是carrying除外
        if self.stack_child is not None and self.state != STATE_CARRYING:
            self.state = STATE_IDLE
            self.clear_movement_target("被堆叠，停止移动")
            return
        if self.state == STATE_WATCHING:
            # 如果有目标，且距离过远，就走过去；到了就停下看
            if self.target_x is not None:
                
                # 简单的朝向修正或停止逻辑
                if self.target_x is None: # 表示到达了
                    self.clear_target_obj("观看目标到达，停止跟踪") # <--- 新增：清理目标对象引用
            return


        # 4. [事件层] 正在播放事件动画或对话中
        if self.state == STATE_EVENT or self.state == STATE_MEETING:
            # 如果有 target_x (interaction manager 设置的)，允许它走完最后一段路
            # 但通常事件会锁死位置
            pass

        # 5. [AI层] 行为决策 (只有自由状态才思考)
        if self.state_timer > 0:
            self.state_timer -= 1
            if self.state_timer <= 0:
                self._on_state_timer_end()
        
        self.update_quest_icon(ctx.quest_manager)
        # --- 仇恨衰减（仅在未锁定目标时进行）---
        if self.aggro_target is None:
            self.hatred_decay_timer += 1
            if self.hatred_decay_timer >= 180:  # 每3秒衰减一次
                self.hatred_decay_timer = 0
                for npc_id in list(self.hatred.keys()):
                    self.hatred[npc_id] = max(0, self.hatred[npc_id] - 5)
                    if self.hatred[npc_id] == 0:
                        del self.hatred[npc_id]
        else:
            # 战斗中：验证目标是否还有效（死亡/倒地/消失则解除锁定）
            t = self.aggro_target
            if t.safety in [SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED]:
                self.aggro_target = None
                self.hatred_decay_timer = 0  # 解除后重新开始衰减计时


    def _set_destination(self, x, y, next_state):
        self.state = next_state 
        self.set_movement_target(x, y, f"前往目标点 ({x}, {y})") # <--- 新增：使用 set_movement_target 来设置目标，确保日志记录和状态同步
   
    def check_arrival_and_interact(self, interaction_mgr, economy_sys, all_cards):
        """
        每帧调用：检查是否到达目的地，并处理到达后的堆叠逻辑。
        """
        # 只处理有明确建筑目标的情况
        if self.target_obj is None: return
        if self.target_x is None: return

        # ── 安全护栏：战斗/knockback/重伤状态下禁止触发建筑堆叠 ──────────
        from src.definitions import STATE_COMBAT, STATE_DOWNED, STATE_CARRYING
        if self.state in (STATE_COMBAT, STATE_DOWNED, STATE_CARRYING):
            return
        if getattr(self, 'knockback_timer', 0) > 0:
            return

        # 距离检查
        dist = math.hypot(self.target_x - self.rect.centerx, self.target_y - self.rect.centery)
        if dist > 30: return  # 还没到

        # --- 到达逻辑 ---

        # 只对建筑执行堆叠
        if not isinstance(self.target_obj, Building):
            return

        # 保存目标建筑的引用（因为 clear_movement_target 会将其置为 None）
        target_building = self.target_obj

        # 清理移动目标（避免重复触发）
        self.clear_movement_target("到达建筑，准备堆叠") #

        self.debug_next_waypoint = None

        # 抢占检查
        if target_building.stack_child is not None and target_building.stack_child != self:
            self.bounce_off(target_building, distance=50)
            self.state = STATE_IDLE
            # 保留原意图，显示"想XX但位置被占"
            from src.entities.building import BUILDING_WORK_TEXT
            work_desc = BUILDING_WORK_TEXT.get(target_building.building_type, '工作')
            self.ai_reason = f"想{work_desc}但位置被占"
            return

        # 执行堆叠：NPC 叠在建筑上，NPC 是 child，建筑是 parent
        interaction_mgr.manual_stack(self, target_building, all_cards)
        self.state = STATE_WORKING
        # 更新干活文本
        from src.entities.building import BUILDING_WORK_TEXT
        self.ai_reason = BUILDING_WORK_TEXT.get(target_building.building_type, '干活中')
    

    def _on_state_timer_end(self):
        self.state = STATE_IDLE
        self.event_partner = None
        self.clear_target_obj("状态结束，清理目标对象") # <--- 新增：清理目标对象引用

    def get_daily_contribution(self):
        """计算门客每日产出"""
        if not self.is_follower: return 0, 0 
        money_gain = 0
        fame_gain = 0
        if self.work_mode == "EARN_MONEY": money_gain += 20
        elif self.work_mode == "EARN_FAME": fame_gain += 10
        return money_gain, fame_gain
    
    def apply_change(self, attr_name, value):
        """通用属性修改接口 (用于 EventAction)"""
        change_desc = ""
        
      
        
        # 2. 物品 (格式 inventory:Item:Count)
        if attr_name == 'inventory' and ':' in str(value):
            parts = str(value).split(':')
            if len(parts) >= 2:
                item, count = parts[0], int(parts[1])
                self.inventory[item] = self.inventory.get(item, 0) + count
                change_desc = f"获得 {item}x{count}"
                return True, change_desc
    
            

        # 6. 通用属性反射
        if hasattr(self, attr_name):
            # 布尔值转换
            if attr_name == 'is_follower': 
                value = (str(value).lower() == 'true')
            
            old_val = getattr(self, attr_name)
            if str(old_val) != str(value):
                setattr(self, attr_name, value)
                if attr_name == 'is_follower' and value:
                    change_desc = "加入麾下!"
                elif attr_name == 'safety' and value == 'DANGER':
                    change_desc = "遭遇追杀!"
            return True, change_desc
        return False, ""

    def draw(self, screen, font):
        # 调用基类绘制背景，但跳过名字（NPC自己处理带势力标签的名字）
        self.draw_card_bg(screen, font, skip_name=True)
        
        
        # [新增] 绘制“正在说话”的气泡 (由 StoryUI 标记)
        if getattr(self, 'is_talking', False):
            bubble_x = self.rect.centerx
            bubble_y = self.rect.top - 25
            bubble_w = 40
            draw_x = bubble_x - bubble_w // 2
            pygame.draw.ellipse(screen, (255, 255, 255), (draw_x, bubble_y, bubble_w, 25))
            pygame.draw.ellipse(screen, (0, 0, 0), (draw_x, bubble_y, bubble_w, 25), 2)
            # 画三个点 ...
            for i in range(3):
                pygame.draw.circle(screen, (50, 50, 50), (draw_x + 10 + i*10, bubble_y + 12), 3)
           
        
        
        
        # 死亡/流放状态 - 绘制灰色覆盖层
        if self.safety in [SAFETY_DEAD, SAFETY_EXILED]:
            # 绘制灰色半透明覆盖层表示死亡状态
            gray_overlay = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            gray_overlay.fill((50, 50, 50, 150))
            screen.blit(gray_overlay, self.rect)
            return
          # 2. [美化] 血条移到名字正下方 (Header高度是22，所以从 y+23 开始画)
        if self.hp <= self.max_hp : # 只有掉血或者战斗状态才显示血条，平时隐藏更清爽，或者你想一直显示也可以
            bar_w = self.rect.width - 12
            bar_h = 3
            bar_x = self.rect.x + 6
            bar_y = self.rect.bottom - 20 
            # 判定颜色：土匪/恶棍用红色，良民/玩家用绿色
            if self.job in ['BANDIT', 'THUG'] or 'VILLAIN' in self.tags:
                hp_color = (220, 60, 60) # 敌方红
            else:
                hp_color = (60, 200, 60) # 友方绿
            hp_pct = max(0, self.hp / self.max_hp)
            pygame.draw.rect(screen, (80, 30, 30), (bar_x, bar_y, bar_w, bar_h)) # 血槽底色
            pygame.draw.rect(screen, hp_color, (bar_x, bar_y, bar_w * hp_pct, bar_h)) # 血条
            font_small = pygame.font.Font(None, 16) 
            hp_surf = font_small.render(f"Hp {self.hp}", True, (0, 0, 0)) #hp
            # 右对齐
            screen.blit(hp_surf, (self.rect.centerx - hp_surf.get_width()//2 - 4, self.rect.bottom - 16))

    
        
        
      
        # --- 资源携带可视化 (Stacklands感) ---
        grain_count = self.inventory.get(ITEM_GRAIN, 0)
        if grain_count > 0:
            # 画一个小麻袋在人物右下角
            pygame.draw.circle(screen, (200, 160, 100), (self.rect.right - 15, self.rect.bottom - 35), 8)
            num_txt = pygame.font.Font(None, 16).render(str(grain_count), True, (20, 20, 20))
            screen.blit(num_txt, (self.rect.right - 18, self.rect.bottom - 40))

        font_small = pygame.font.Font(None, 18) # 使用更小的字体
        # --- 信息栏 --- 使用 definitions.py 的 JOB_LABELS
        from src.definitions import JOB_LABELS
        display_text = "发呆"
        display_color = (150, 150, 150)

        # 【修复】玩家卡牌始终显示特殊文字，不显示AI reason
        if self.job == 'PLAYER':
            if self.state == STATE_COMBAT:
                display_text = "战斗中"
                display_color = (255, 80, 80)
            elif self.is_working: 
                display_text = "忙碌中"
                display_color = (50, 200, 50)
            elif self.dragging:
                display_text = "移动中"
                display_color = (100, 180, 255)
            elif self.target_x is not None:
                display_text = "前往中"
                display_color = (100, 180, 255)
            else:
                display_text = "自由活动"
                display_color = (200, 200, 200)
        elif self.ai_reason:
            display_text = self.ai_reason
        else:
                if self.safety == SAFETY_DOWNED:
                    display_text = "重伤倒地"
                    display_color = (255, 50, 50)
                elif self.state == STATE_COMBAT: # 需要配合 AI System 修改
                    display_text = self.ai_reason if self.ai_reason else "战斗中"
                    display_color = (255, 80, 80) # 战斗红
                elif self.state == STATE_WORKING:
                    # 如果有配方正在进行，ai_reason 应该是配方名
                    display_text = self.ai_reason if self.ai_reason else "工作中"
                    display_color = (50, 200, 50) # 工作绿
                elif self.state == STATE_MOVING:
                    display_text = self.ai_reason if self.ai_reason else "赶路中"
                    display_color = (100, 180, 255) # 移动蓝
                elif self.state == STATE_EVENT:
                    display_text = "事件中"
                    display_color = (220, 100, 220) # 事件紫
                elif self.is_refugee:
                    display_text = "流浪中"
                    display_color = (180, 180, 180)
           
        if len(display_text) > 5: display_text = display_text[:4] + ".."
        # 使用 definitions.py 统一定义的 JOB_LABELS（不再重复定义）
        job_str = JOB_LABELS.get(self.job, self.job)
        
        # ═══════════════════════════════════════════════════════════════
        # 绘制社会分层信息（势力色+组织+等级）
        # 【修复】势力标签移到左上角，名字居中（已在base.py处理）
        # ═══════════════════════════════════════════════════════════════
        
        # 获取势力颜色
        power_color = POWER_COLORS.get(self.power_type, POWER_COLORS['民'])
        
        # 获取组织简称
        org_name = ORG_SHORT_NAMES.get(self.org_id, '')
        
        # 获取等级符号和职业称号
        org_rank = getattr(self, 'org_rank', 0) if hasattr(self, 'org_rank') else int(getattr(self, 'rank', 0))
        rank_symbol = RANK_SYMBOLS.get(org_rank, '')
        
        # 获取职业等级称号（如"喽啰"、"大当家"等）
        from src.data.character_seeds import get_job_title
        job_title = get_job_title(self.job, org_rank)
        
        # ═══════════════════════════════════════════════════════════════
        # 【修改】第一行：名字居中（不再有左上角势力标签）
        # ═══════════════════════════════════════════════════════════════
        name_str = self.name
        # 重伤时显示血量百分比
        if self.safety == SAFETY_DOWNED and self.max_hp > 0:
            hp_pct = int((self.hp / self.max_hp) * 100)
            name_str = f"{name_str} {hp_pct}%"
        if len(name_str) > 6: name_str = name_str[:5] + ".."
        
        name_surf = font.render(name_str, True, (255, 255, 255))
        screen.blit(name_surf, (self.rect.centerx - name_surf.get_width()//2, self.rect.y + 2))
        
        # ═══════════════════════════════════════════════════════════════
        # 第二行：[势力]·组织（势力标签+组织名，整体居中且垂直对齐）
        # 格式：[匪]黑风寨、[农]流民、[学]太学
        # ═══════════════════════════════════════════════════════════════
        # 【修复】统一使用12号字体，确保势力标签和组织名大小一致、垂直对齐
        font_org = pygame.font.SysFont("microsoftyahei,simhei,pingfangsc,notosanscjk", 12, bold=False)
        font_badge = pygame.font.SysFont("microsoftyahei,simhei,pingfangsc,notosanscjk", 12, bold=True)
        
        # 计算第二行内容
        if org_name and org_name != '':
            org_display = org_name
        else:
            org_display = job_title  # 无组织时显示职业称号
        
        # 使用统一字体渲染组织名
        org_surf = font_org.render(org_display, True, power_color)
        
        # 计算势力标签和组织名的总宽度，以便整体居中
        badge_w = 14  # 稍微缩小标签宽度
        badge_h = 14
        gap = 2       # 标签与文字间距
        total_w = badge_w + gap + org_surf.get_width()
        
        # 计算起始x位置（整体居中）
        start_x = self.rect.centerx - total_w // 2
        row2_y = self.rect.y + 26  # 职业组织名下移，避免与进度条重叠
        
        # 【关键】计算垂直居中的基准：取标签高度和文字高度的最大值
        row_h = max(badge_h, org_surf.get_height())
        
        # 绘制势力标签背景（垂直居中）
        badge_x = start_x
        badge_y = row2_y + (row_h - badge_h) // 2
        badge_rect = pygame.Rect(badge_x, badge_y, badge_w, badge_h)
        pygame.draw.rect(screen, power_color, badge_rect, border_radius=2)
        pygame.draw.rect(screen, (40, 40, 40), badge_rect, 1, border_radius=2)
        
        # 绘制势力类型字符（在标签内居中）
        badge_surf = font_badge.render(self.power_type, True, (255, 255, 255))
        screen.blit(badge_surf, (badge_x + badge_w//2 - badge_surf.get_width()//2, 
                                  badge_y + badge_h//2 - badge_surf.get_height()//2))
        
        # 绘制组织名（垂直居中对齐）
        org_x = badge_x + badge_w + gap
        org_y = row2_y + (row_h - org_surf.get_height()) // 2
        screen.blit(org_surf, (org_x, org_y))
        
        # 绘制 行为 (AI Reason) - 第三行
        state_surf = font.render(f"{display_text}", True, display_color)
        screen.blit(state_surf, (self.rect.centerx - state_surf.get_width()//2, self.rect.y + 40))

        
       
        
        
        # 6. 战斗数值 (仅在有数值时显示在最底部角落)
        if self.atk > 0 or self.def_ > 0:
            font_small = pygame.font.Font(None, 16) 
            
            atk_surf = font_small.render(f"Atk {self.atk}", True, (220, 80, 80)) # 红色攻击
            screen.blit(atk_surf, (self.rect.x + 4, self.rect.bottom - 30))
            
           
            def_surf = font_small.render(f"Def {self.def_}", True, (80, 120, 220)) # 蓝色防御
            # 右对齐
            screen.blit(def_surf, (self.rect.right - def_surf.get_width()- 4, self.rect.bottom - 30))
            

        # 门客金标
        if self.is_follower:
            pygame.draw.circle(screen, (255, 215, 0), (self.rect.right - 8, self.rect.top + 8), 5)
            
         # 绘制任务感叹号/气泡
        if self.quest_icon_active:
            bubble_x = self.rect.right
            bubble_y = self.rect.top - 10
            # 简单的黄色气泡
            pygame.draw.circle(screen, (255, 255, 200), (bubble_x, bubble_y), 10)
            pygame.draw.circle(screen, (0, 0, 0), (bubble_x, bubble_y), 10, 1)
            # 红色感叹号
            font_q = pygame.font.Font(None, 20)
            q_surf = font_q.render("!", True, (255, 50, 50))
            screen.blit(q_surf, (bubble_x - q_surf.get_width()//2, bubble_y - q_surf.get_height()//2))
    def _update_survival_stats(self, all_cards,ctx):
        
        quest_manager = ctx.quest_manager
        if quest_manager and not quest_manager.flags.get('guidance_visible', False):
            return
        
        # 【修复】事件状态期间暂停饥饿/寒冷等状态伤害
        if self.state == STATE_EVENT:
            return  # 事件进行中，时间暂停
        
        # 【修复】剧情对话期间暂停饥饿/寒冷等状态伤害
        story_ui = getattr(ctx, 'story_ui', None)
        if story_ui and story_ui.is_active:
            return  # 剧情进行中，时间暂停
        
        
        
        # 仅对活人有效
        if self.safety in [SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED]: return
        if self.job == 'PLAYER': return # 玩家有单独的逻辑(Player类继承NPC，可以覆盖或共用，这里假设Player逻辑独立)

        self.survival_timer += 1
        if self.survival_timer < 60: return # 每秒(60帧)结算一次
        self.survival_timer = 0

        # 1. 饥饿逻辑 (自然增长) - 降低下降速度
        self.hunger += 0.5 # 每秒+0.5，200秒(3.3分钟)饿满
        
        # 自动进食逻辑：如果背包里有食物且饥饿 > 30（更早触发）
        if self.hunger > 30:
            self._try_eat_from_inventory()

        # 饥饿扣血 - 提高阈值，让NPC更不容易饿晕
        if self.hunger >= 90:  # 从80提高到90
            self.hp -= 1
            self.dissatisfaction += 2
            if self.hp <= 0:
                # 【事件保护】如果NPC正在参与事件演出，不设置重伤状态
                if getattr(self, '_event_protected', False):
                    log_game_event(f"[NPC][EVENT_PROTECTED] {self.name} 饿晕但有事件保护，跳过重伤判定")
                    # 恢复少量血量，避免持续扣血
                    self.hp = max(1, self.hp + 5)
                else:
                    self.safety = SAFETY_DOWNED
                    log_game_event(f"{self.name} 饿晕了。")

        # 2. 寒冷逻辑 - 降低下降速度
        is_warm = self._check_warmth(all_cards)
        
        if is_warm:
            self.cold = max(0, self.cold - 5) # 回暖
        else:
            self.cold += 1 # 变冷（从2降到1）
            
        # 寒冷扣血 - 提高阈值，让NPC更不容易冻晕
        if self.cold >= 90:  # 从80提高到90
            self.hp -= 1
            self.dissatisfaction += 1
            if self.hp <= 0:
                # 【事件保护】如果NPC正在参与事件演出，不设置重伤状态
                if getattr(self, '_event_protected', False):
                    log_game_event(f"[NPC][EVENT_PROTECTED] {self.name} 冻晕但有事件保护，跳过重伤判定")
                    # 恢复少量血量，避免持续扣血
                    self.hp = max(1, self.hp + 5)
                else:
                    self.safety = SAFETY_DOWNED
                    log_game_event(f"{self.name} 冻晕了。")
        # 3. 不满值自然衰减 (如果环境舒适)
        if self.hunger < 50 and self.cold < 50 and self.dissatisfaction > 0:
            self.dissatisfaction -= 1
            
    def _try_eat_from_inventory(self):
        
        item_sys = ItemManager.get_instance()
        food_to_eat = None
        for item_id in list(self.inventory.keys()):
            if item_sys.is_food(item_id):
                food_to_eat = item_id
                break
        if food_to_eat:
            # 吃掉
            self.inventory[food_to_eat] -= 1
            if self.inventory[food_to_eat] <= 0: del self.inventory[food_to_eat]
            
            # 恢复数值 (查表)
            rec_val = item_sys.get_hunger_recovery(food_to_eat)
            
            # 吃东西同时降低饥饿和寒冷
            self.hunger = max(0, self.hunger - rec_val)
            self.cold = max(0, self.cold - rec_val * 0.5)  # 食物也提供一些保暖效果

    # ──────────────────────────────────────────────────────────────
    # 装备系统：穿戴武器/护甲/服装 → 动态影响战斗属性和保暖
    # ──────────────────────────────────────────────────────────────
    def equip_item(self, item_id):
        """
        从背包穿戴物品到对应装备槽。
        - 武器 → equip_weapon，若已有装备则将旧装备退回背包
        - 护甲 → equip_armor
        - 服装 → equip_clothing
        """
        item_sys = ItemManager.get_instance()
        if self.inventory.get(item_id, 0) <= 0:
            return False  # 背包里没有

        if item_sys.is_weapon(item_id):
            # 旧武器退回背包
            if self.equip_weapon:
                self.inventory[self.equip_weapon] = self.inventory.get(self.equip_weapon, 0) + 1
            self.equip_weapon = item_id
        elif item_sys.is_armor(item_id):
            if self.equip_armor:
                self.inventory[self.equip_armor] = self.inventory.get(self.equip_armor, 0) + 1
            self.equip_armor = item_id
        elif item_sys.is_clothing(item_id):
            if self.equip_clothing:
                self.inventory[self.equip_clothing] = self.inventory.get(self.equip_clothing, 0) + 1
            self.equip_clothing = item_id
        else:
            return False

        # 从背包扣除
        self.inventory[item_id] -= 1
        if self.inventory[item_id] <= 0:
            del self.inventory[item_id]

        log_game_event(f"{self.name} 装备了 [{item_id}]", tag="EQUIP")
        return True

    def get_effective_atk(self):
        """返回含装备加成的实际攻击力"""
        item_sys = ItemManager.get_instance()
        bonus = item_sys.get_atk_bonus(self.equip_weapon) if self.equip_weapon else 0
        return self.atk + bonus

    def get_effective_def(self):
        """返回含装备加成的实际防御力（护甲+衣物）"""
        item_sys = ItemManager.get_instance()
        armor_bonus = item_sys.get_def_bonus(self.equip_armor) if self.equip_armor else 0
        clothing_bonus = item_sys.get_def_bonus(self.equip_clothing) if self.equip_clothing else 0
        return self.def_ + armor_bonus + clothing_bonus

    def _check_warmth(self, all_cards):
        """检查是否有热源（含装备服装加成）"""
        item_sys = ItemManager.get_instance()

        # 1. 已穿戴的服装直接提供保暖
        if self.equip_clothing:
            warm = item_sys.get_warm_val(self.equip_clothing)
            if warm > 0:
                return True

        # 2. 背包里的保暖物品（火把等）
        for item_id in self.inventory:
            item_data = item_sys.get_data(item_id)
            if item_data and item_data.warm_val > 0:
                return True

        # 3. 环境热源（篝火）
        from src.entities.building import Building
        for card in all_cards:
            if isinstance(card, Building):
                if card.building_type == 'CAMPFIRE' and card.fuel_time > 0:
                    dist = math.hypot(card.rect.centerx - self.rect.centerx,
                                      card.rect.centery - self.rect.centery)
                    if dist < 150:
                        return True
        return False
        
      
    def _is_queue_leader(self):
        """
        检查当前NPC是否是队列的队长
        队长定义：直接堆叠在建筑上的NPC
        """
        if self.stack_parent is None:
            return False
            
        # 导入Building类来检查
        from src.entities.building import Building
        
        # 如果直接父节点是建筑，则是队长
        return isinstance(self.stack_parent, Building)
    
    def _is_in_queue_but_not_leader(self):
        """
        检查当前NPC是否在排队但不是队长
        """
        if self.stack_parent is None:
            return False
            
        # 向上遍历堆叠链，找到根节点
        current = self
        while current.stack_parent is not None:
            current = current.stack_parent
            
        # 导入Building类来检查
        from src.entities.building import Building
        
        # 如果根节点是建筑，且自己不是队长，则是排队但非队长
        if isinstance(current, Building):
            return not self._is_queue_leader()
            
        return False
    
    def _is_in_clinic_queue(self):
        """
        检查当前NPC是否在医馆排队（保持兼容性）
        """
        # 向上遍历堆叠链，找到根节点
        current = self
        while current.stack_parent is not None:
            current = current.stack_parent
            
        # 导入Building类来检查
        from src.entities.building import Building
        
        # 检查根节点是否是医馆
        if isinstance(current, Building) and current.building_type == 'CLINIC':
            return True
            
        return False

   
    
    # ═══════════════════════════════════════════════════════════════
    # 【新增】人情值系统相关方法
    # ═══════════════════════════════════════════════════════════════
    def get_social_credit(self, target_id: int) -> int:
        """获取与目标NPC的人情值"""
        if hasattr(self, '_social_credit_system') and self._social_credit_system:
            return self._social_credit_system.get_credit(self.id, target_id)
        return 0
    
    def add_social_credit(self, target_id: int, amount: int):
        """增加人情值（正数=对方欠我，负数=我欠对方）"""
        if hasattr(self, '_social_credit_system') and self._social_credit_system:
            self._social_credit_system.add_credit(self.id, target_id, amount)
    
    def can_ask_favor(self, target_id: int, favor_cost: int) -> tuple[bool, str]:
        """
        检查是否可以向目标NPC请求帮助
        
        Args:
            target_id: 目标NPC的ID
            favor_cost: 请求帮助需要的人情值成本
            
        Returns:
            (是否可以请求, 原因说明)
        """
        if not hasattr(self, '_social_credit_system') or not self._social_credit_system:
            return False, "人情值系统未初始化"
        
        # 获取当前人情值（负数表示我欠对方）
        credit = self._social_credit_system.get_credit(self.id, target_id)
        
        # 获取目标NPC对象
        target_npc = None
        # 这里需要通过外部传入或全局查找
        # 暂时返回计算结果，实际调用时需要传入target_npc
        
        return self._social_credit_system.can_spend_credit(self.id, target_id, favor_cost)
    
    def spend_social_credit(self, target_id: int, amount: int) -> tuple[bool, str]:
        """
        消耗人情值来请求帮助
        
        Args:
            target_id: 目标NPC的ID
            amount: 需要消耗的人情值
            
        Returns:
            (是否成功, 结果说明)
        """
        if not hasattr(self, '_social_credit_system') or not self._social_credit_system:
            return False, "人情值系统未初始化"
        
        return self._social_credit_system.spend_credit(self.id, target_id, amount)
    
    def get_personality_description(self) -> str:
        """获取性格描述文本（用于AI叙事）"""
        if not hasattr(self, 'personality') or not self.personality:
            return f"{self.name}性格普通。"
        
        p = self.personality
        desc_parts = []
        
        # 脾气描述
        temper_desc = {
            "温和": f"{self.name}脾气温和，不易动怒",
            "性急": f"{self.name}性子急躁，容易冲动",
            "普通": f"{self.name}脾气普通"
        }.get(p.temper_str, f"{self.name}脾气{p.temper_str}")
        desc_parts.append(temper_desc)
        
        # 胆量描述
        spirit_desc = {
            "胆小": "胆小怕事",
            "大胆": "胆大心细",
            "普通": "胆量普通"
        }.get(p.spirit_str, f"胆量{p.spirit_str}")
        desc_parts.append(spirit_desc)
        
        # 主义描述
        ism_desc = {
            "现实主义": "注重实际利益",
            "理想主义": "追求理想",
            "普通": "现实主义与理想主义平衡"
        }.get(p.ism_str, p.ism_str)
        desc_parts.append(ism_desc)
        
        # 风格描述
        style_desc = {
            "保守": "行事保守稳重",
            "激进": "行事激进冒险",
            "普通": "行事风格中庸"
        }.get(p.act_style_str, f"行事{p.act_style_str}")
        desc_parts.append(style_desc)
        
        return "。".join(desc_parts) + "。"
    
    def to_aistory_format(self) -> dict:
        """
        转换为aistory模块使用的格式
        
        Returns:
            符合dilemma_deriver要求的字典
        """
        data = {
            'npc_id': str(self.id),
            'name': self.name,
            'gender': getattr(self, 'gender', ''),
            'age': getattr(self, 'age', 30),
            'identity': self.job,
            'org': self.org_id if self.org_id != 'NONE' else '',
            'personality': getattr(self, 'desc', ''),  # 向后兼容
            'backstory': getattr(self, 'backstory', ''),
            'wealth': self.money,
            'emotion': getattr(self, 'emotion', 50),
            'health': self.hp,
            'tags': self.tags,
            'desc': getattr(self, 'desc', ''),
            'location': getattr(self, 'location', ''),
        }
        
        # 添加多维度性格数据 - 直接传递数值
        if hasattr(self, 'personality') and self.personality:
            p = self.personality
            data['personality'] = {
                'temper': p.temper,
                'spirit': p.spirit,
                'ism': p.ism,
                'act_style': p.act_style,
                'friendship': p.friendship,
                'ambition': p.ambition,
                'desire_type': p.desire_type,
                'desire_level': p.ambition,  # 使用野心值作为物欲程度
            }
        
        # 添加人情值
        if hasattr(self, '_social_credit_system') and self._social_credit_system:
            player_id = 0  # 假设玩家ID为0
            credit = self._social_credit_system.get_credit(player_id, self.id)
            data['social_credit'] = credit
        
        # 添加初始困境
        if hasattr(self, 'initial_dilemma') and self.initial_dilemma:
            data['initial_dilemma'] = self.initial_dilemma
        
        return data
    
    def get_personality_profile(self) -> str:
        """生成性格画像（用于LLM提示词）"""
        if not hasattr(self, 'personality') or not self.personality:
            return getattr(self, 'desc', '') or "性格信息暂无"
        
        p = self.personality
        lines = []
        
        # 基础性格
        traits = []
        if p.temper != 50:
            traits.append(f"脾气{'温和' if p.temper < 50 else '暴躁'}({p.temper})")
        if p.spirit != 50:
            traits.append(f"胆量{'胆小' if p.spirit < 50 else '勇敢'}({p.spirit})")
        if p.ism != 50:
            traits.append(f"{'理想' if p.ism < 50 else '现实'}主义({p.ism})")
        if p.act_style != 50:
            traits.append(f"行事{'缜密' if p.act_style < 50 else '豪放'}({p.act_style})")
        if p.friendship != 50:
            traits.append(f"{'重情义' if p.friendship < 50 else '不重情义'}({p.friendship})")
        
        if traits:
            lines.append(f"性格特质：{'，'.join(traits)}")
        
        # 野心和物欲
        if p.ambition != 50:
            ambition_desc = "野心勃勃" if p.ambition > 70 else "胸无大志" if p.ambition < 30 else f"野心{p.ambition}/100"
            lines.append(f"野心程度：{ambition_desc}")
        
        if p.desire_type and p.ambition != 50:
            lines.append(f"物欲倾向：{p.desire_type}（{p.ambition}）")
        
        # 人情往来
        if hasattr(self, '_social_credit_system') and self._social_credit_system:
            player_id = 0
            credit = self._social_credit_system.get_credit(player_id, self.id)
            if credit != 0:
                if credit > 0:
                    lines.append(f"人情往来：欠玩家 {credit} 点人情")
                else:
                    lines.append(f"人情往来：玩家欠其 {-credit} 点人情")
        
        return '\n'.join(lines) if lines else (getattr(self, 'desc', '') or "性格信息暂无")
    
    def get_behavior_tendency(self) -> dict:
        """获取行为倾向（用于启发式规则）"""
        if not hasattr(self, 'personality') or not self.personality:
            return {
                'risk_taking': False,
                'pragmatic': False,
                'loyal': False,
                'temper_hot': False,
                'temper_calm': False,
                'ambitious': False,
                'content': False
            }
        
        p = self.personality
        return {
            'risk_taking': p.spirit > 60 or p.act_style > 60,
            'pragmatic': p.ism > 60,
            'loyal': p.friendship < 40,
            'temper_hot': p.temper > 60,
            'temper_calm': p.temper < 40,
            'ambitious': p.ambition > 60,
            'content': p.ambition < 40
        }
    
    def get_personality_description_dict(self) -> dict:
        """获取性格描述字典（数值转文本）"""
        if not hasattr(self, 'personality') or not self.personality:
            return {}
        
        p = self.personality
        return {
            'temper': '暴躁' if p.temper > 60 else '温和' if p.temper < 40 else '平和',
            'spirit': '勇敢' if p.spirit > 60 else '胆小' if p.spirit < 40 else '一般',
            'ism': '现实' if p.ism > 60 else '理想' if p.ism < 40 else '平衡',
            'act_style': '豪放' if p.act_style > 60 else '缜密' if p.act_style < 40 else '适中',
            'friendship': '不重情义' if p.friendship > 60 else '重情义' if p.friendship < 40 else '一般'
        }
       