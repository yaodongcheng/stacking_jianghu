# --- src/faction_war_system.py ---
"""
阶段4：组织竞争与势力冲突系统
- 资源控制点争夺
- 组织间敌对关系
- 组织战争与领地控制
"""

import random
import math
import pygame
from src.definitions import *
from src.utils import log_game_event
from src.data.character_seeds import ORGANIZATIONS, POWER_TYPES

# ═══════════════════════════════════════════════════════════════════
# 资源控制点系统
# ═══════════════════════════════════════════════════════════════════

class ResourceControlPoint:
    """
    资源控制点 - 组织争夺的战略目标
    控制点产生资源加成，谁控制谁受益
    
    【重构】所有建筑类型都纳入控制点系统，基于 BUILDING_DB 生成
    """
    
    # 控制点类型定义 - 覆盖所有 BUILDING_DB 中的建筑
    POINT_TYPES = {
        # ══════════════════════════════════════════════════════════════
        # 自然资源（无法被组织控制，但仍可显示在战略视图）
        # ══════════════════════════════════════════════════════════════
        'BUSH': {
            'name': '浆果丛',
            'resource': 'FOOD',
            'daily_income': 0,
            'control_difficulty': 0,  # 0表示无法被控制
        },
        'TREE': {
            'name': '枯树',
            'resource': 'WOOD',
            'daily_income': 0,
            'control_difficulty': 0,
        },
        'MINE': {
            'name': '矿山',
            'resource': 'IRON',
            'daily_income': 5,
            'control_difficulty': 2,
        },
        'FISHPOND': {
            'name': '河滩',
            'resource': 'FOOD',
            'daily_income': 0,  # 自然资源，无收益
            'control_difficulty': 0,  # 不可被控制，对所有人开放
        },
        'CAMPFIRE': {
            'name': '篝火',
            'resource': 'NONE',
            'daily_income': 0,
            'control_difficulty': 0,
        },
        
        # ══════════════════════════════════════════════════════════════
        # 朝廷/军事势力建筑 (士/兵)
        # ══════════════════════════════════════════════════════════════
        'GOV_OFFICE': {
            'name': '府衙',
            'resource': 'AUTHORITY',
            'daily_income': 30,
            'control_difficulty': 5,  # 最难控制
        },
        'GATEHOUSE': {
            'name': '岗哨',
            'resource': 'AUTHORITY',
            'daily_income': 10,
            'control_difficulty': 3,
        },
        'JAIL': {
            'name': '牢房',
            'resource': 'AUTHORITY',
            'daily_income': 5,
            'control_difficulty': 3,
        },
        'BARRACKS': {
            'name': '校场',
            'resource': 'MILITARY',
            'daily_income': 12,
            'control_difficulty': 4,
        },
        'ARMORY': {
            'name': '武库',
            'resource': 'MILITARY',
            'daily_income': 15,
            'control_difficulty': 4,
        },
        
        # ══════════════════════════════════════════════════════════════
        # 农业势力建筑 (农)
        # ══════════════════════════════════════════════════════════════
        'FARM': {
            'name': '农田',
            'resource': 'GRAIN',
            'daily_income': 8,
            'control_difficulty': 1,
        },
        'GRANARY': {
            'name': '官仓',
            'resource': 'GRAIN',
            'daily_income': 12,
            'control_difficulty': 3,
        },
        'MILL': {
            'name': '磨坊',
            'resource': 'GRAIN',
            'daily_income': 6,
            'control_difficulty': 1,
        },
        'RANCH': {
            'name': '牧场',
            'resource': 'FOOD',
            'daily_income': 8,
            'control_difficulty': 2,
        },
        'HUNTING': {
            'name': '猎场',
            'resource': 'FOOD',
            'daily_income': 5,
            'control_difficulty': 1,
        },
        'HOUSE': {
            'name': '民居',
            'resource': 'NONE',
            'daily_income': 2,
            'control_difficulty': 1,
        },
        
        # ══════════════════════════════════════════════════════════════
        # 商业势力建筑 (商)
        # ══════════════════════════════════════════════════════════════
        'MARKET': {
            'name': '集市',
            'resource': 'GOLD',
            'daily_income': 20,
            'control_difficulty': 3,
        },
        'PAWNSHOP': {
            'name': '当铺',
            'resource': 'GOLD',
            'daily_income': 18,
            'control_difficulty': 2,
        },
        'GRAIN_SHOP': {
            'name': '粮铺',
            'resource': 'GOLD',
            'daily_income': 10,
            'control_difficulty': 1,
        },
        'TEAHOUSE': {
            'name': '茶楼',
            'resource': 'GOLD',
            'daily_income': 12,
            'control_difficulty': 1,
        },
        'TAVERN': {
            'name': '酒楼',
            'resource': 'GOLD',
            'daily_income': 15,
            'control_difficulty': 2,
        },
        'STABLE': {
            'name': '马厩',
            'resource': 'GOLD',
            'daily_income': 8,
            'control_difficulty': 1,
        },
        'INN': {
            'name': '酒肆',
            'resource': 'GOLD',
            'daily_income': 10,
            'control_difficulty': 1,
        },
        
        # ══════════════════════════════════════════════════════════════
        # 工匠势力建筑 (工)
        # ══════════════════════════════════════════════════════════════
        'WORKSHOP': {
            'name': '工坊',
            'resource': 'CRAFT',
            'daily_income': 12,
            'control_difficulty': 2,
        },
        'SMITHY': {
            'name': '铁铺',
            'resource': 'CRAFT',
            'daily_income': 14,
            'control_difficulty': 2,
        },
        'WEAVING': {
            'name': '织坊',
            'resource': 'CRAFT',
            'daily_income': 10,
            'control_difficulty': 1,
        },
        'KILN': {
            'name': '窑场',
            'resource': 'CRAFT',
            'daily_income': 12,
            'control_difficulty': 2,
        },
        'JEWELER': {
            'name': '珠宝',
            'resource': 'GOLD',
            'daily_income': 20,
            'control_difficulty': 2,
        },
        
        # ══════════════════════════════════════════════════════════════
        # 学术/宗教势力建筑 (学)
        # ══════════════════════════════════════════════════════════════
        'SCHOOL': {
            'name': '书院',
            'resource': 'KNOWLEDGE',
            'daily_income': 8,
            'control_difficulty': 2,
        },
        'CLINIC': {
            'name': '医馆',
            'resource': 'SERVICE',
            'daily_income': 15,
            'control_difficulty': 2,
        },
        'PHARMACY': {
            'name': '药铺',
            'resource': 'MEDICINE',
            'daily_income': 12,
            'control_difficulty': 2,
        },
        'LIBRARY': {
            'name': '书斋',
            'resource': 'KNOWLEDGE',
            'daily_income': 6,
            'control_difficulty': 1,
        },
        'TEMPLE': {
            'name': '禅院',
            'resource': 'FAITH',
            'daily_income': 8,
            'control_difficulty': 1,
        },
        'TAOIST': {
            'name': '道观',
            'resource': 'FAITH',
            'daily_income': 8,
            'control_difficulty': 1,
        },
        
        # ══════════════════════════════════════════════════════════════
        # 江湖势力建筑 (游)
        # ══════════════════════════════════════════════════════════════
        'THEATER': {
            'name': '瓦舍',
            'resource': 'GOLD',
            'daily_income': 12,
            'control_difficulty': 1,
        },
        
        # ══════════════════════════════════════════════════════════════
        # 盗匪势力建筑 (匪)
        # ══════════════════════════════════════════════════════════════
        'GAMBLING': {
            'name': '赌坊',
            'resource': 'GOLD',
            'daily_income': 25,
            'control_difficulty': 2,
        },
        'BROTHEL': {
            'name': '青楼',
            'resource': 'GOLD',
            'daily_income': 30,
            'control_difficulty': 2,
        },
        'BLACKMARKET': {
            'name': '黑市',
            'resource': 'GOLD',
            'daily_income': 20,
            'control_difficulty': 3,
        },
        'BANDIT_LAIR': {
            'name': '山寨',
            'resource': 'MILITARY',
            'daily_income': 10,
            'control_difficulty': 4,
        },
    }
    
    def __init__(self, point_id, point_type, x, y, building_ref=None):
        self.id = point_id
        self.point_type = point_type
        self.x = x
        self.y = y
        self.building_ref = building_ref  # 关联的建筑对象
        
        # 控制状态
        self.controller_org_id = None  # 当前控制者
        self.control_strength = 0  # 控制强度 (0-100)
        self.contested = False  # 是否正在被争夺
        self.contesting_org_id = None  # 争夺者
        
        # 从类型获取属性
        type_data = self.POINT_TYPES.get(point_type, {})
        self.name = type_data.get('name', '未知控制点')
        self.resource_type = type_data.get('resource', 'GOLD')
        self.daily_income = type_data.get('daily_income', 10)
        self.difficulty = type_data.get('control_difficulty', 1)
        
    def get_info(self):
        """获取控制点信息（用于UI显示）"""
        controller_name = '无'
        if self.controller_org_id:
            org_data = ORGANIZATIONS.get(self.controller_org_id, {})
            controller_name = org_data.get('name', self.controller_org_id)
        
        return {
            'name': self.name,
            'type': self.point_type,
            'controller': controller_name,
            'control_strength': self.control_strength,
            'contested': self.contested,
            'daily_income': self.daily_income,
        }


# ═══════════════════════════════════════════════════════════════════
# 组织敌对关系系统（增强版 - 支持主从/同盟细分）
# ═══════════════════════════════════════════════════════════════════

# 【新增】同盟类型常量
ALLIANCE_NONE = 0             # 无同盟
ALLIANCE_EQUAL = 1            # 平等同盟
ALLIANCE_VASSALAGE = 2        # 主从关系

class FactionRelationManager:
    """
    管理组织间的敌对/友好关系
    
    关系值范围: -100(死敌) ~ 0(中立) ~ +100(盟友)
    
    【新增】同盟细分：
    - 平等同盟：双方地位对等，共享部分资源
    - 主从关系：有明确的上下家，下家向上家纳贡，上家保护下家
    """
    
    # 关系等级阈值
    # 【修复】提高战争门槛，避免战争太频繁爆发
    RELATION_THRESHOLDS = {
        'ALLY': 60,        # 盟友
        'FRIENDLY': 30,    # 友好
        'NEUTRAL': -30,    # 中立
        'HOSTILE': -60,    # 敌对
        'WAR': -120,       # 战争状态（从-80提高到-120，需要严重仇恨才会开战）
    }
    
    def __init__(self):
        # 关系矩阵: {(org_a, org_b): relation_value}
        self.relations = {}
        
        # 【新增】同盟结构: {(org_a, org_b): {'type': ALLIANCE_TYPE, 'master': org_id_or_none}}
        # 当 type=ALLIANCE_VASSALAGE 时，master 指向上家
        self.alliances = {}
        
        # 战争状态: {(org_a, org_b): war_data}
        self.active_wars = {}
        
        # 关系变化日志
        self.relation_log = []
        
    def _get_key(self, org_a, org_b):
        """生成有序的关系键（确保A-B和B-A使用同一个键）"""
        return tuple(sorted([org_a, org_b]))
        
    def get_relation(self, org_a, org_b):
        """获取两个组织之间的关系值"""
        if org_a == org_b:
            return 100  # 同一组织
        key = self._get_key(org_a, org_b)
        return self.relations.get(key, 0)  # 默认中立
        
    def modify_relation(self, org_a, org_b, delta, reason=""):
        """修改组织间关系"""
        if org_a == org_b:
            return
        key = self._get_key(org_a, org_b)
        old_val = self.relations.get(key, 0)
        new_val = max(-100, min(100, old_val + delta))
        self.relations[key] = new_val
        
        if reason:
            self.relation_log.append({
                'orgs': key,
                'old': old_val,
                'new': new_val,
                'delta': delta,
                'reason': reason
            })
            log_game_event(f"[外交] {org_a} 与 {org_b} 关系{delta:+d} ({reason})", tag="DIPLOMACY")
        
        # 检查是否触发战争
        if new_val <= self.RELATION_THRESHOLDS['WAR'] and key not in self.active_wars:
            self._declare_war(org_a, org_b, reason)
        # 检查是否结束战争
        elif new_val > self.RELATION_THRESHOLDS['HOSTILE'] and key in self.active_wars:
            self._end_war(org_a, org_b, "关系改善")
            
    def get_relation_status(self, org_a, org_b):
        """获取关系状态文字"""
        val = self.get_relation(org_a, org_b)
        if val >= self.RELATION_THRESHOLDS['ALLY']:
            return 'ALLY', '盟友'
        elif val >= self.RELATION_THRESHOLDS['FRIENDLY']:
            return 'FRIENDLY', '友好'
        elif val >= self.RELATION_THRESHOLDS['NEUTRAL']:
            return 'NEUTRAL', '中立'
        elif val >= self.RELATION_THRESHOLDS['HOSTILE']:
            return 'HOSTILE', '敌对'
        else:
            return 'WAR', '交战'
            
    def is_at_war(self, org_a, org_b):
        """检查两个组织是否处于战争状态"""
        key = self._get_key(org_a, org_b)
        return key in self.active_wars
        
    def _declare_war(self, org_a, org_b, casus_belli=""):
        """宣战"""
        key = self._get_key(org_a, org_b)
        if key in self.active_wars:
            return
            
        self.active_wars[key] = {
            'start_day': 0,  # 需要外部设置
            'casus_belli': casus_belli,
            'org_a_kills': 0,
            'org_b_kills': 0,
            'org_a_losses': 0,
            'org_b_losses': 0,
        }
        
        org_a_name = ORGANIZATIONS.get(org_a, {}).get('name', org_a)
        org_b_name = ORGANIZATIONS.get(org_b, {}).get('name', org_b)
        log_game_event(f"【战争爆发】{org_a_name} 与 {org_b_name} 开战！理由：{casus_belli}", tag="WAR")
        
    def _end_war(self, org_a, org_b, reason=""):
        """结束战争"""
        key = self._get_key(org_a, org_b)
        if key not in self.active_wars:
            return
            
        war_data = self.active_wars.pop(key)
        org_a_name = ORGANIZATIONS.get(org_a, {}).get('name', org_a)
        org_b_name = ORGANIZATIONS.get(org_b, {}).get('name', org_b)
        log_game_event(f"【战争结束】{org_a_name} 与 {org_b_name} 停战。{reason}", tag="WAR")
        
    def record_kill(self, killer_org, victim_org):
        """记录战争中的击杀"""
        key = self._get_key(killer_org, victim_org)
        if key not in self.active_wars:
            return
            
        war = self.active_wars[key]
        if killer_org == key[0]:
            war['org_a_kills'] += 1
            war['org_b_losses'] += 1
        else:
            war['org_b_kills'] += 1
            war['org_a_losses'] += 1
    
    # ═══════════════════════════════════════════════════════════════
    # 【新增】同盟系统
    # ═══════════════════════════════════════════════════════════════
    
    def form_alliance(self, org_a, org_b, alliance_type=ALLIANCE_EQUAL, master=None):
        """
        建立同盟关系
        
        Args:
            org_a, org_b: 参与同盟的两个组织
            alliance_type: ALLIANCE_EQUAL (平等) 或 ALLIANCE_VASSALAGE (主从)
            master: 若为主从关系，指定谁是上家（主人）
            
        Returns:
            (success: bool, message: str)
        """
        if org_a == org_b:
            return False, "不能与自己结盟"
        
        key = self._get_key(org_a, org_b)
        
        # 检查是否已在战争中
        if key in self.active_wars:
            return False, "战争期间无法结盟"
        
        # 建立同盟
        self.alliances[key] = {
            'type': alliance_type,
            'master': master if alliance_type == ALLIANCE_VASSALAGE else None,
            'formed_day': 0  # 需要外部设置
        }
        
        # 同时提升关系值
        self.modify_relation(org_a, org_b, 40, "建立同盟")
        
        org_a_name = ORGANIZATIONS.get(org_a, {}).get('name', org_a)
        org_b_name = ORGANIZATIONS.get(org_b, {}).get('name', org_b)
        
        if alliance_type == ALLIANCE_VASSALAGE:
            master_name = ORGANIZATIONS.get(master, {}).get('name', master)
            vassal = org_a if master == org_b else org_b
            vassal_name = ORGANIZATIONS.get(vassal, {}).get('name', vassal)
            log_game_event(f"【同盟】{vassal_name} 臣服于 {master_name}（主从关系）", tag="DIPLOMACY")
        else:
            log_game_event(f"【同盟】{org_a_name} 与 {org_b_name} 结为平等同盟", tag="DIPLOMACY")
        
        return True, "同盟建立成功"
    
    def break_alliance(self, org_a, org_b, reason=""):
        """
        解除同盟
        """
        key = self._get_key(org_a, org_b)
        if key not in self.alliances:
            return False, "并无同盟关系"
        
        alliance = self.alliances.pop(key)
        
        # 关系恶化
        self.modify_relation(org_a, org_b, -30, f"解除同盟: {reason}")
        
        org_a_name = ORGANIZATIONS.get(org_a, {}).get('name', org_a)
        org_b_name = ORGANIZATIONS.get(org_b, {}).get('name', org_b)
        log_game_event(f"【外交】{org_a_name} 与 {org_b_name} 解除同盟（{reason}）", tag="DIPLOMACY")
        
        return True, "同盟已解除"
    
    def get_alliance_info(self, org_a, org_b):
        """
        获取两个组织之间的同盟信息
        
        Returns:
            {
                'has_alliance': bool,
                'type': ALLIANCE_TYPE,
                'type_name': str,           # "平等同盟" / "主从关系"
                'master': org_id or None,   # 上家（若为主从关系）
                'is_master': bool,          # org_a 是否是上家
                'is_vassal': bool,          # org_a 是否是下家
            }
        """
        if org_a == org_b:
            return {
                'has_alliance': True,
                'type': ALLIANCE_EQUAL,
                'type_name': '同一组织',
                'master': None,
                'is_master': False,
                'is_vassal': False,
            }
        
        key = self._get_key(org_a, org_b)
        if key not in self.alliances:
            return {
                'has_alliance': False,
                'type': ALLIANCE_NONE,
                'type_name': '无',
                'master': None,
                'is_master': False,
                'is_vassal': False,
            }
        
        alliance = self.alliances[key]
        alliance_type = alliance['type']
        master = alliance.get('master')
        
        type_name = "平等同盟" if alliance_type == ALLIANCE_EQUAL else "主从关系"
        
        return {
            'has_alliance': True,
            'type': alliance_type,
            'type_name': type_name,
            'master': master,
            'is_master': (master == org_a),
            'is_vassal': (alliance_type == ALLIANCE_VASSALAGE and master != org_a),
        }
    
    def is_same_faction_group(self, org_a, org_b):
        """
        检查两个组织是否属于同一派系集团（用于免费使用判断）
        
        同一集团的定义：
        1. 同一组织
        2. 存在主从关系（互为上下家）
        
        平等同盟不算同一集团（但有折扣）
        """
        if org_a == org_b:
            return True
        
        alliance_info = self.get_alliance_info(org_a, org_b)
        
        # 主从关系视为同一集团
        if alliance_info['type'] == ALLIANCE_VASSALAGE:
            return True
        
        return False
    
    def get_fee_discount_rate(self, user_org, controller_org):
        """
        【核心】根据势力关系计算手续费折扣率
        
        Returns:
            (discount_rate: float, reason: str, allow_use: bool)
            - discount_rate: 0.0=免费, 0.5=半价, 1.0=全价, 2.0=双倍
            - reason: 原因说明
            - allow_use: 是否允许使用（敌对建筑可能不允许或触发警报）
        """
        if not user_org or not controller_org:
            return 1.0, "外来者", True
        
        # 同一组织：免费
        if user_org == controller_org:
            return 0.0, "同门兄弟", True
        
        # 检查同盟
        alliance_info = self.get_alliance_info(user_org, controller_org)
        
        if alliance_info['has_alliance']:
            if alliance_info['type'] == ALLIANCE_VASSALAGE:
                # 主从关系：免费（都是一家人）
                if alliance_info['is_master']:
                    return 0.0, "我方属下", True
                else:
                    return 0.0, "上家产业", True
            elif alliance_info['type'] == ALLIANCE_EQUAL:
                # 平等同盟：半价
                return 0.5, "盟友折扣", True
        
        # 检查敌对关系
        status, status_text = self.get_relation_status(user_org, controller_org)
        
        if status in ['WAR', 'HOSTILE']:
            # 敌对势力：可以用但会触发警报（双倍费用也没用，人家不想收你钱想打你）
            return 2.0, "敌对势力", False  # allow_use=False 表示需要特殊处理
        elif status == 'FRIENDLY':
            # 友好势力：8折
            return 0.8, "友好减免", True
        else:
            # 中立：全价
            return 1.0, "外来者", True


# ═══════════════════════════════════════════════════════════════════
# 势力战争系统 - 核心管理器
# ═══════════════════════════════════════════════════════════════════

class FactionWarSystem:
    """
    阶段4核心系统：管理势力竞争和战争
    """
    
    # 控制点争夺设置
    CONTEST_DURATION = 600   # 争夺持续时间(ticks)
    CONTEST_WIN_THRESHOLD = 100  # 争夺胜利所需积分
    
    # 战斗遭遇设置
    ENCOUNTER_RANGE = 150     # 遭遇触发距离
    ENCOUNTER_CHANCE = 0.02   # 敌对NPC相遇时的战斗概率/帧
    WAR_ENCOUNTER_CHANCE = 0.08  # 战争状态下的战斗概率
    
    # 组织敌对行为设置
    HOSTILITY_DECAY = 0.5     # 每日敌对值衰减
    KILL_HOSTILITY = -30      # 杀死对方成员的敌对影响
    ROB_HOSTILITY = -15       # 抢劫对方成员的敌对影响
    TRADE_FRIENDSHIP = 5      # 贸易带来的友好度
    
    def __init__(self):
        self.control_points = {}  # {point_id: ResourceControlPoint}
        self.relation_manager = FactionRelationManager()
        
        # 争夺状态跟踪
        self.active_contests = {}  # {point_id: contest_data}
        
        # 统计
        self.daily_income_record = {}  # {org_id: total_income}
        
        # 悬赏系统
        self.active_bounties = []  # 当前活跃的悬赏列表
        
    def initialize_control_points(self, all_buildings):
        """
        从建筑列表初始化控制点
        【重构】所有建筑类型都自动成为控制点（使用 POINT_TYPES 作为参照）
        
        控制点类型直接使用建筑类型（building_type），
        如果 POINT_TYPES 中没有定义，则跳过（如自然资源等）
        """
        point_id = 0
        for building in all_buildings:
            b_type = getattr(building, 'building_type', None)
            if not b_type:
                continue
            
            # 检查该建筑类型是否在 POINT_TYPES 中定义
            if b_type not in ResourceControlPoint.POINT_TYPES:
                # 未定义的类型，跳过（但可以记录下来以便调试）
                continue
            
            # 检查控制难度，0表示无法被控制（如自然资源）
            type_data = ResourceControlPoint.POINT_TYPES[b_type]
            if type_data.get('control_difficulty', 0) == 0:
                continue  # 自然资源类不纳入控制点系统
            
            point = ResourceControlPoint(
                point_id=f"CP_{point_id}",
                point_type=b_type,  # 直接使用建筑类型
                x=building.rect.centerx,
                y=building.rect.centery,
                building_ref=building
            )
            self.control_points[point.id] = point
            point_id += 1
                
        log_game_event(f"[势力] 初始化了 {len(self.control_points)} 个资源控制点", tag="FACTION")
        
    def initialize_relations(self):
        """
        初始化组织间的初始关系
        基于势力类型设置默认敌对/友好
        """
        # 相同势力类型的组织默认友好
        # 匪类与其他势力默认敌对
        org_ids = list(ORGANIZATIONS.keys())
        
        for i, org_a in enumerate(org_ids):
            for org_b in org_ids[i+1:]:
                data_a = ORGANIZATIONS.get(org_a, {})
                data_b = ORGANIZATIONS.get(org_b, {})
                
                power_a = data_a.get('power_type', '民')
                power_b = data_b.get('power_type', '民')
                
                # 初始关系设定
                if power_a == power_b:
                    # 同势力类型：友好
                    self.relation_manager.modify_relation(org_a, org_b, 30, "同道中人")
                elif power_a == '匪' or power_b == '匪':
                    # 涉及盗匪：敌对
                    self.relation_manager.modify_relation(org_a, org_b, -40, "匪患")
                elif power_a == '士' and power_b in ['商', '农']:
                    # 官府与商农：略微友好
                    self.relation_manager.modify_relation(org_a, org_b, 15, "治下子民")
                elif power_b == '士' and power_a in ['商', '农']:
                    self.relation_manager.modify_relation(org_a, org_b, 15, "治下子民")
                    
        log_game_event("[势力] 组织间关系初始化完成", tag="FACTION")
    
    def initialize_control_with_npcs(self, all_npcs):
        """
        【新增】根据NPC初始位置，让NPC所属组织立刻占领附近的控制点
        确保游戏开局就有势力分布，玩家立刻能感知到系统存在
        """
        from src.entities.npc import NPC
        
        # 统计每个控制点附近各组织的NPC数量
        point_orgs = {pid: {} for pid in self.control_points}
        
        for npc in all_npcs:
            if not isinstance(npc, NPC):
                continue
            org_id = getattr(npc, 'org_id', None)
            if not org_id or org_id == 'NONE':
                continue
                
            # 检查NPC在哪个控制点附近（使用更大范围200px）
            for pid, point in self.control_points.items():
                dist = math.hypot(npc.rect.centerx - point.x, npc.rect.centery - point.y)
                if dist <= 200:  # 初始化时使用较大范围
                    if org_id not in point_orgs[pid]:
                        point_orgs[pid][org_id] = 0
                    point_orgs[pid][org_id] += 1
        
        # 为每个控制点分配初始控制者（数量最多的组织）
        assigned = 0
        for pid, orgs in point_orgs.items():
            if not orgs:
                continue
            # 找出人数最多的组织
            dominant_org = max(orgs.keys(), key=lambda x: orgs[x])
            point = self.control_points[pid]
            point.controller_org_id = dominant_org
            point.control_strength = 70 + random.randint(0, 30)  # 70-100
            assigned += 1
            
            org_name = ORGANIZATIONS.get(dominant_org, {}).get('name', dominant_org)
            log_game_event(f"[势力初始化] {org_name} 控制了 {point.name}", tag="FACTION")
        
        log_game_event(f"[势力] 初始分配了 {assigned}/{len(self.control_points)} 个控制点", tag="FACTION")
        
    # ═══════════════════════════════════════════════════════════════
    # 控制点争夺
    # ═══════════════════════════════════════════════════════════════
    
    def check_control_point_presence(self, all_npcs):
        """
        检查各控制点的组织存在情况
        返回: {point_id: {org_id: npc_count}}
        """
        from src.entities.npc import NPC
        
        point_presence = {pid: {} for pid in self.control_points}
        
        for npc in all_npcs:
            if not isinstance(npc, NPC):
                continue
            if npc.safety in [SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED]:
                continue
                
            org_id = getattr(npc, 'org_id', None)
            if not org_id or org_id == 'NONE':
                continue
                
            # 检查NPC是否在某个控制点附近
            for pid, point in self.control_points.items():
                dist = math.hypot(npc.rect.centerx - point.x, npc.rect.centery - point.y)
                if dist <= 100:  # 控制点范围
                    if org_id not in point_presence[pid]:
                        point_presence[pid][org_id] = 0
                    point_presence[pid][org_id] += 1
                    
        return point_presence
        
    def update_control_points(self, all_npcs):
        """
        更新控制点状态 - 【重构】取消自动争夺机制
        
        设计原则：
        - NPC单纯站在控制点附近不会触发势力变化
        - 势力争夺必须通过"势力决策"系统显式发起
        - 这里只做轻量级的状态维护（如标记contested状态用于UI显示）
        """
        # 添加冷却机制，避免每帧执行
        current_time = pygame.time.get_ticks()
        if not hasattr(self, '_last_control_update'):
            self._last_control_update = 0
        
        # 每5秒才更新一次控制点状态
        if current_time - self._last_control_update < 5000:
            return
        self._last_control_update = current_time
        
        presence = self.check_control_point_presence(all_npcs)
        
        for pid, point in self.control_points.items():
            orgs_present = presence.get(pid, {})
            
            # 只更新contested标记，用于UI显示（不改变控制权）
            if point.controller_org_id:
                # 检查是否有其他势力在场
                other_orgs = [org for org in orgs_present if org != point.controller_org_id]
                point.contested = len(other_orgs) > 0
            else:
                point.contested = False
            
            # 【已移除】不再自动转移控制权
            # 势力变化必须通过以下方式：
            # 1. 势力决策系统发起的正式"夺取"行动
            # 2. 玩家的显式操作（如战争胜利）
            # 3. 剧情事件触发
                    
    # ═══════════════════════════════════════════════════════════════
    # 战斗遭遇检测
    # ═══════════════════════════════════════════════════════════════
    
    def check_hostile_encounters(self, all_npcs, combat_manager, ft_manager=None, ai_system=None):
        """
        检测敌对组织成员的遭遇并触发战斗
        返回: [(attacker, defender), ...]
        ft_manager: 浮动文字管理器（可选），用于显示战斗提示
        """
        from src.entities.npc import NPC
        
        encounters = []
        
        # 筛选有效NPC
        valid_npcs = [
            npc for npc in all_npcs 
            if isinstance(npc, NPC)
            and npc.safety not in [SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED]
            and getattr(npc, 'org_id', None) not in [None, 'NONE']
            and npc.state != STATE_COMBAT  # 已在战斗中的跳过
        ]
        
        # 两两检测
        for i, npc_a in enumerate(valid_npcs):
            for npc_b in valid_npcs[i+1:]:
                org_a = npc_a.org_id
                org_b = npc_b.org_id
                
                if org_a == org_b:
                    continue  # 同组织
                    
                # 检查距离
                dist = math.hypot(
                    npc_a.rect.centerx - npc_b.rect.centerx,
                    npc_a.rect.centery - npc_b.rect.centery
                )
                if dist > self.ENCOUNTER_RANGE:
                    continue
                    
                # 检查关系
                at_war = self.relation_manager.is_at_war(org_a, org_b)
                status, _ = self.relation_manager.get_relation_status(org_a, org_b)
                
                # 决定战斗概率
                if at_war:
                    chance = self.WAR_ENCOUNTER_CHANCE
                elif status == 'HOSTILE':
                    chance = self.ENCOUNTER_CHANCE
                else:
                    continue  # 非敌对，不会主动攻击
                    
                # 概率触发
                if random.random() < chance:
                    # 决定谁先攻击（基于武力值和随机）
                    combat_a = getattr(npc_a, 'combat', 30) + random.randint(0, 20)
                    combat_b = getattr(npc_b, 'combat', 30) + random.randint(0, 20)
                    
                    if combat_a >= combat_b:
                        attacker, defender = npc_a, npc_b
                    else:
                        attacker, defender = npc_b, npc_a
                        
                    encounters.append((attacker, defender))
                    
                    # 触发战斗：设置攻击目标并进入战斗状态
                    attacker.aggro_target = defender
                    attacker.state = STATE_COMBAT
                    attacker.in_combat = True
                    defender.in_combat = True
                    
                    # 如果有AI系统，广播战斗开始
                    if ai_system:
                        ai_system.broadcast_combat_start(attacker, defender)
                    
                    # 【新增】显示浮动文字，让玩家感知到势力冲突
                    if ft_manager:
                        atk_org_name = ORGANIZATIONS.get(attacker.org_id, {}).get('name', '???')
                        def_org_name = ORGANIZATIONS.get(defender.org_id, {}).get('name', '???')
                        
                        # 在冲突位置显示提示
                        mid_x = (attacker.rect.centerx + defender.rect.centerx) // 2
                        mid_y = min(attacker.rect.top, defender.rect.top) - 30
                        
                        if at_war:
                            ft_manager.add_text(f"[战] {atk_org_name} vs {def_org_name}",
                                               mid_x, mid_y, (255, 80, 80))
                        else:
                            ft_manager.add_text(f"势力冲突!", mid_x, mid_y, (255, 150, 50))
                    
                    log_game_event(
                        f"[冲突] {attacker.name}({attacker.org_id}) 攻击 {defender.name}({defender.org_id})",
                        tag="FACTION_COMBAT"
                    )
                    
        return encounters
        
    # ═══════════════════════════════════════════════════════════════
    # 日结算
    # ═══════════════════════════════════════════════════════════════
    
    def process_daily_income(self, org_economy):
        """
        处理控制点的每日收入
        收入存入组织金库
        """
        self.daily_income_record.clear()
        
        for pid, point in self.control_points.items():
            if not point.controller_org_id:
                continue
                
            org_id = point.controller_org_id
            income = point.daily_income
            
            # 控制强度影响收入
            income = int(income * (point.control_strength / 100))
            
            if income > 0:
                org_economy.deposit(org_id, income, f"{point.name}收益")
                self.daily_income_record[org_id] = self.daily_income_record.get(org_id, 0) + income
                
        # 日志
        for org_id, total in self.daily_income_record.items():
            if total > 0:
                org_name = ORGANIZATIONS.get(org_id, {}).get('name', org_id)
                log_game_event(f"[势力] {org_name} 今日控制点收入: {total}铜", tag="FACTION_INCOME")
                
    def daily_relation_decay(self):
        """每日关系衰减（敌对关系缓慢恢复）"""
        for key, val in list(self.relation_manager.relations.items()):
            if val < 0:
                # 敌对关系缓慢恢复
                self.relation_manager.relations[key] = min(0, val + self.HOSTILITY_DECAY)
            elif val > 0 and val > 30:
                # 过于友好的关系缓慢下降
                self.relation_manager.relations[key] = max(30, val - 0.2)
                
    # ═══════════════════════════════════════════════════════════════
    # 对外接口
    # ═══════════════════════════════════════════════════════════════
    
    def on_npc_killed(self, killer_npc, victim_npc):
        """NPC被杀时调用，更新敌对关系"""
        killer_org = getattr(killer_npc, 'org_id', None)
        victim_org = getattr(victim_npc, 'org_id', None)
        
        if not killer_org or not victim_org:
            return
        if killer_org == victim_org:
            return
            
        # 关系恶化
        self.relation_manager.modify_relation(
            killer_org, victim_org, 
            self.KILL_HOSTILITY,
            f"{killer_npc.name}杀死{victim_npc.name}"
        )
        
        # 记录战争统计
        if self.relation_manager.is_at_war(killer_org, victim_org):
            self.relation_manager.record_kill(killer_org, victim_org)
            
    def on_robbery(self, robber_npc, victim_npc):
        """NPC被抢劫时调用"""
        robber_org = getattr(robber_npc, 'org_id', None)
        victim_org = getattr(victim_npc, 'org_id', None)
        
        if not robber_org or not victim_org:
            return
        if robber_org == victim_org:
            return
            
        self.relation_manager.modify_relation(
            robber_org, victim_org,
            self.ROB_HOSTILITY,
            f"{robber_npc.name}抢劫{victim_npc.name}"
        )
        
    def on_trade(self, trader_a, trader_b):
        """两个NPC交易时调用"""
        org_a = getattr(trader_a, 'org_id', None)
        org_b = getattr(trader_b, 'org_id', None)
        
        if not org_a or not org_b:
            return
        if org_a == org_b:
            return
            
        self.relation_manager.modify_relation(
            org_a, org_b,
            self.TRADE_FRIENDSHIP,
            "贸易往来"
        )
        
    def get_org_controlled_points(self, org_id):
        """获取组织控制的所有控制点"""
        return [p for p in self.control_points.values() if p.controller_org_id == org_id]
    
    def get_building_controller(self, building):
        """
        获取建筑的控制势力
        
        Args:
            building: Building 对象
            
        Returns:
            (controller_org_id, control_point) 或 (None, None)
        """
        for cp in self.control_points.values():
            if cp.building_ref is building:
                return cp.controller_org_id, cp
        return None, None
    
    def calculate_usage_fee(self, user_entity, building, recipe_id=None):
        """
        计算使用建筑的手续费
        
        【新版】集成同盟关系系统：
        - 自家/上家/下家：免费
        - 平等同盟：半价
        - 友好：8折
        - 中立：全价
        - 敌对：触发警报（周围敌人会攻击）
        
        Args:
            user_entity: 使用者（Player 或 NPC）
            building: 目标建筑
            recipe_id: 配方ID（可选，用于计算特定配方的费用）
            
        Returns:
            {
                'fee': int,               # 手续费金额
                'controller_org': str,    # 控制势力ID
                'controller_name': str,   # 控制势力名称
                'reason': str,            # 收费原因
                'is_same_org': bool,      # 是否同势力/同集团（免费）
                'is_hostile': bool,       # 是否敌对
                'allow_use': bool,        # 是否允许使用（敌对可能触发警报）
                'discount_rate': float,   # 折扣率（用于显示）
            }
        """
        controller_org, control_point = self.get_building_controller(building)
        
        # 无人控制的建筑 - 免费使用
        if not controller_org:
            return {
                'fee': 0,
                'controller_org': None,
                'controller_name': '无主',
                'reason': '无人管理',
                'is_same_org': False,
                'is_hostile': False,
                'allow_use': True,
                'discount_rate': 0.0,
            }
        
        # 获取使用者的势力
        user_org = getattr(user_entity, 'org_id', None)
        org_data = ORGANIZATIONS.get(controller_org, {})
        controller_name = org_data.get('name', controller_org)
        
        # 【核心】使用关系管理器计算折扣率
        discount_rate, fee_reason, allow_use = self.relation_manager.get_fee_discount_rate(
            user_org, controller_org
        )
        
        # 判断是否同集团（免费）
        is_same_group = self.relation_manager.is_same_faction_group(user_org, controller_org) if user_org else False
        
        # 判断是否敌对
        is_hostile = False
        if user_org:
            status, _ = self.relation_manager.get_relation_status(user_org, controller_org)
            is_hostile = status in ['HOSTILE', 'WAR']
        
        # 如果是同集团（同势力/主从关系），免费
        if is_same_group:
            return {
                'fee': 0,
                'controller_org': controller_org,
                'controller_name': controller_name,
                'reason': fee_reason,
                'is_same_org': True,
                'is_hostile': False,
                'allow_use': True,
                'discount_rate': 0.0,
            }
        
        # 基础费用计算（基于建筑类型）
        building_type = getattr(building, 'building_type', 'UNKNOWN')
        
        # 不同建筑类型的基础费率
        FEE_RATES = {
            'MARKET': 5,      # 市场：基础5铜（交易税）
            'MINE': 10,       # 矿山：10铜（开采费）
            'WORKSHOP': 8,    # 工坊：8铜（场地费）
            'FARM': 3,        # 农田：3铜（耕地租金）
            'FISHPOND': 5,    # 河滩：5铜（捕鱼费）
            'CLINIC': 15,     # 医馆：15铜（诊金）
            'INN': 10,        # 酒肆：10铜（入场费）
            'TEMPLE': 5,      # 禅院：5铜（香火钱）
            'THEATER': 8,     # 瓦舍：8铜（门票）
            'SCHOOL': 10,     # 书院：10铜（学费）
            'GOV_OFFICE': 20, # 府衙：20铜（办事费）
            'BUSH': 2,        # 浆果丛：2铜
            'TREE': 3,        # 枯树：3铜（伐木费）
        }
        
        base_fee = FEE_RATES.get(building_type, 5)
        
        # 应用折扣率
        final_fee = int(base_fee * discount_rate)
        
        # 控制强度影响（控制越稳固，收费能力越强）
        if control_point and discount_rate > 0:
            strength_modifier = control_point.control_strength / 100
            final_fee = int(final_fee * (0.5 + 0.5 * strength_modifier))
        
        # 最低1铜（如果不是免费的话）
        if discount_rate > 0:
            final_fee = max(1, final_fee)
        
        return {
            'fee': final_fee,
            'controller_org': controller_org,
            'controller_name': controller_name,
            'reason': fee_reason,
            'is_same_org': False,
            'is_hostile': is_hostile,
            'allow_use': allow_use,
            'discount_rate': discount_rate,
        }
    
    def pay_usage_fee(self, user_entity, building, fee_amount):
        """
        支付使用费
        
        Args:
            user_entity: 付款人
            building: 目标建筑
            fee_amount: 费用金额
            
        Returns:
            (success: bool, message: str)
        """
        controller_org, control_point = self.get_building_controller(building)
        
        if not controller_org or fee_amount <= 0:
            return True, "无需付费"
        
        # 检查余额
        user_money = user_entity.inventory.get(ITEM_COIN, 0)
        if user_money < fee_amount:
            return False, f"铜钱不足（需要{fee_amount}，只有{user_money}）"
        
        # 扣款
        user_entity.inventory[ITEM_COIN] = user_money - fee_amount
        
        # 收入记入控制势力（可选：找到控制点附近的NPC收款）
        org_name = ORGANIZATIONS.get(controller_org, {}).get('name', controller_org)
        log_game_event(f"[手续费] {user_entity.name} 向 {org_name} 支付了 {fee_amount}铜", tag="FEE")
        
        # 微量增加关系
        user_org = getattr(user_entity, 'org_id', None)
        if user_org and user_org != controller_org:
            self.relation_manager.modify_relation(user_org, controller_org, 1, "交费往来")
        
        return True, f"已支付{fee_amount}铜"
    
    def start_contest(self, building, attacker_org):
        """
        发起对建筑的争夺
        
        Args:
            building: 目标建筑
            attacker_org: 发起势力ID
            
        Returns:
            (success: bool, message: str)
        """
        # 查找该建筑的控制点
        control_point = None
        for cp in self.control_points:
            if cp.building_ref is building:
                control_point = cp
                break
        
        if not control_point:
            return False, "此建筑不是战略要地"
        
        # 检查是否已经被该势力控制
        current_controller = control_point.controller
        if current_controller == attacker_org:
            return False, "已是我方控制"
        
        # 检查是否已经在争夺中
        if control_point.contested:
            # 如果已经在争夺中，可以加入（但这里简化处理，直接参与）
            pass
        
        # 设置争夺状态
        control_point.contested = True
        control_point.contest_participants.add(attacker_org)
        
        # 如果是无主建筑，直接获取控制权
        if not current_controller:
            control_point.controller = attacker_org
            control_point.control_strength = 30  # 初始控制强度较低
            control_point.contested = False
            control_point.contest_participants.clear()
            log_game_event(f"[CONTEST] {attacker_org} 占领了无主建筑 {building.name}", tag="FACTION")
            return True, f"成功占领！（初始控制强度30%）"
        
        # 有主建筑：需要逐渐削弱控制
        # 这里简化：每次发起争夺削弱10%控制强度
        weaken_amount = 10
        old_strength = control_point.control_strength
        control_point.control_strength = max(0, control_point.control_strength - weaken_amount)
        
        # 如果控制强度降到0，换主
        if control_point.control_strength <= 0:
            old_controller = control_point.controller
            control_point.controller = attacker_org
            control_point.control_strength = 30
            control_point.contested = False
            control_point.contest_participants.clear()
            
            log_game_event(f"[CONTEST] {attacker_org} 从 {old_controller} 手中夺取了 {building.name}", tag="FACTION")
            
            # 关系恶化
            if old_controller:
                self.relation_manager.modify_relation(
                    attacker_org, old_controller, 
                    -10,  # 夺取建筑的关系惩罚
                    f"武力夺取{building.name}"
                )
            
            return True, f"成功夺取控制权！"
        
        # 关系恶化（较轻微，因为还没夺取成功）
        if current_controller:
            self.relation_manager.modify_relation(
                attacker_org, current_controller,
                -3, f"试图夺取{building.name}"
            )
        
        log_game_event(f"[CONTEST] {attacker_org} 对 {building.name} 发起争夺（控制强度 {old_strength}% -> {control_point.control_strength}%）", tag="FACTION")
        return True, f"发起争夺！（对方控制强度降低至{control_point.control_strength}%）"
        
    def get_faction_summary(self, org_id):
        """获取势力摘要（用于UI）"""
        org_data = ORGANIZATIONS.get(org_id, {})
        controlled = self.get_org_controlled_points(org_id)
        
        # 获取敌对组织列表
        enemies = []
        allies = []
        for other_org in ORGANIZATIONS.keys():
            if other_org == org_id:
                continue
            status, text = self.relation_manager.get_relation_status(org_id, other_org)
            if status in ['HOSTILE', 'WAR']:
                enemies.append((other_org, text))
            elif status in ['ALLY', 'FRIENDLY']:
                allies.append((other_org, text))
                
        return {
            'name': org_data.get('name', org_id),
            'power_type': org_data.get('power_type', '民'),
            'controlled_points': len(controlled),
            'daily_income': self.daily_income_record.get(org_id, 0),
            'enemies': enemies,
            'allies': allies,
        }

    # ═══════════════════════════════════════════════════════════════
    # 【新增】悬赏系统 - NPC/组织可以对玩家或NPC发布悬赏
    # ═══════════════════════════════════════════════════════════════
    
    def __init_bounty_system(self):
        """初始化悬赏系统（在__init__中调用）"""
        self.active_bounties = []  # 当前活跃的悬赏列表
        
    def post_bounty(self, issuer_org, target_id, reward, reason="得罪了", is_player_target=True, player=None):
        """
        发布悬赏
        
        Args:
            issuer_org: 发布者组织ID
            target_id: 被悬赏者ID（NPC ID或玩家ID=9999）
            reward: 悬赏金额
            reason: 悬赏原因
            is_player_target: 是否是针对玩家的悬赏
            player: 玩家实例（可选，用于同步bounty_value）
        
        Returns:
            (success: bool, bounty_id: str)
        """
        bounty_id = f"BOUNTY_{len(self.active_bounties)}_{target_id}"
        
        bounty = {
            'id': bounty_id,
            'issuer_org': issuer_org,
            'target_id': target_id,
            'reward': reward,
            'reason': reason,
            'is_player_target': is_player_target,
            'hunters': [],           # 接受悬赏的NPC ID列表
            'posted_day': 0,         # 发布日期（需外部设置）
            'active': True
        }
        
        self.active_bounties.append(bounty)
        
        # 【新增】同步更新玩家的悬赏状态显示
        if is_player_target and player:
            self._sync_player_bounty_status(player)
            
            # 【新增】传闻系统：悬赏传闻
            from src.rumor_system import get_rumor_system
            rumor_sys = get_rumor_system()
            rumor_sys.on_player_action('BOUNTY', player, org_id=issuer_org, bounty_value=reward)
        
        issuer_name = ORGANIZATIONS.get(issuer_org, {}).get('name', issuer_org)
        target_type = "玩家" if is_player_target else f"#{target_id}"
        log_game_event(f"[悬赏] {issuer_name} 悬赏 {reward}铜 追杀 {target_type}（{reason}）", tag="BOUNTY")
        
        return True, bounty_id
    
    def _sync_player_bounty_status(self, player):
        """
        同步玩家的悬赏状态属性（供UI显示用）
        """
        if not player:
            return
            
        total_value, bounties = self.get_bounty_on_player(player)
        player.bounty_value = total_value
        
        # 找出最大悬赏的发布者
        if bounties:
            max_bounty = max(bounties, key=lambda b: b['reward'])
            player.bounty_issuer = max_bounty['issuer_org']
        else:
            player.bounty_issuer = None
    
    def cancel_bounty(self, bounty_id, player=None):
        """
        取消悬赏
        """
        for bounty in self.active_bounties:
            if bounty['id'] == bounty_id:
                bounty['active'] = False
                log_game_event(f"[悬赏] 悬赏 {bounty_id} 已取消", tag="BOUNTY")
                # 同步玩家悬赏状态
                if player and bounty['is_player_target']:
                    self._sync_player_bounty_status(player)
                return True
        return False
    
    def cancel_bounties_by_target(self, target_id, player=None):
        """
        取消针对某目标的所有悬赏
        """
        cancelled = 0
        is_player = False
        for bounty in self.active_bounties:
            if bounty['target_id'] == target_id and bounty['active']:
                bounty['active'] = False
                cancelled += 1
                if bounty['is_player_target']:
                    is_player = True
        
        if cancelled > 0:
            log_game_event(f"[悬赏] 取消了 {cancelled} 个针对 #{target_id} 的悬赏", tag="BOUNTY")
            # 同步玩家悬赏状态
            if is_player and player:
                self._sync_player_bounty_status(player)
        return cancelled
    
    def get_bounty_on_player(self, player):
        """
        获取针对玩家的悬赏信息
        返回: (total_bounty_value, list_of_bounties)
        """
        player_bounties = [
            b for b in self.active_bounties 
            if b['is_player_target'] and b['active']
        ]
        total_value = sum(b['reward'] for b in player_bounties)
        return total_value, player_bounties
    
    def npc_accept_bounty(self, npc, bounty_id):
        """
        NPC接受悬赏任务
        """
        for bounty in self.active_bounties:
            if bounty['id'] == bounty_id and bounty['active']:
                if npc.id not in bounty['hunters']:
                    bounty['hunters'].append(npc.id)
                    log_game_event(f"[悬赏] {npc.name} 接受了悬赏 {bounty_id}", tag="BOUNTY")
                    return True
        return False
    
    def check_bounty_hunters_ai(self, all_npcs, player):
        """
        悬赏猎人AI：检查NPC是否应该追杀被悬赏者
        在AI更新中调用
        
        Returns:
            list of (hunter_npc, target)
        """
        from src.entities.npc import NPC
        
        hunt_orders = []
        
        # 获取玩家悬赏总额
        total_bounty, player_bounties = self.get_bounty_on_player(player)
        
        if total_bounty <= 0:
            return hunt_orders
        
        # 遍历NPC，决定是否成为猎人
        for npc in all_npcs:
            if not isinstance(npc, NPC):
                continue
            if npc.safety in [SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED]:
                continue
            
            # 已锁定其他目标，跳过
            if npc.aggro_target is not None:
                continue
            
            # 门客/玩家自己不会追杀玩家
            if getattr(npc, 'is_follower', False):
                continue
            if npc.id == player.id:
                continue
            
            # 根据职业和势力决定是否追杀
            should_hunt = False
            
            # 盗匪/泼皮类：只要悬赏够高就追
            if npc.job in ['BANDIT', 'THUG']:
                if total_bounty >= 50:  # 门槛低
                    should_hunt = True
            
            # 官差/护卫：如果悬赏来自官府，会执行
            elif npc.job in ['GUARD', 'OFFICIAL']:
                for bounty in player_bounties:
                    org_data = ORGANIZATIONS.get(bounty['issuer_org'], {})
                    if org_data.get('power_type') == '士':  # 官府悬赏
                        should_hunt = True
                        break
            
            # 普通NPC：悬赏非常高才会冒险
            else:
                if total_bounty >= 200:
                    # 根据魅力/勇气决定（这里简化）
                    import random
                    if random.random() < 0.01:  # 1%概率
                        should_hunt = True
            
            if should_hunt:
                # 距离检查：太远不追
                import math
                dist = math.hypot(npc.rect.centerx - player.rect.centerx,
                                  npc.rect.centery - player.rect.centery)
                if dist < 300:  # 视野范围内
                    hunt_orders.append((npc, player))
                    # 接受最大悬赏
                    best_bounty = max(player_bounties, key=lambda b: b['reward'])
                    self.npc_accept_bounty(npc, best_bounty['id'])
        
        return hunt_orders
    
    def collect_bounty(self, hunter_npc, target_was_downed=True):
        """
        悬赏猎人完成任务，领取赏金
        """
        for bounty in self.active_bounties:
            if not bounty['active']:
                continue
            if hunter_npc.id not in bounty['hunters']:
                continue
            
            # 发放赏金
            reward = bounty['reward']
            hunter_npc.inventory[ITEM_COIN] = hunter_npc.inventory.get(ITEM_COIN, 0) + reward
            
            # 标记完成
            bounty['active'] = False
            
            log_game_event(f"[悬赏] {hunter_npc.name} 完成悬赏，获得 {reward}铜", tag="BOUNTY")
            return reward
        
        return 0


# ═══════════════════════════════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════════════════════════════

_faction_war_system = None

def get_faction_war_system():
    """获取势力战争系统单例"""
    global _faction_war_system
    if _faction_war_system is None:
        _faction_war_system = FactionWarSystem()
    return _faction_war_system
