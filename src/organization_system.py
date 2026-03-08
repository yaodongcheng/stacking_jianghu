# --- src/organization_system.py ---
"""
阶段3：组织扩张系统
管理组织的资金、招募、薪俸和成员贡献。
每个组织是一个"经济实体"，有自己的金库、收入来源和支出。
"""

import random
from src.definitions import ITEM_COIN
from src.utils import log_game_event
from src.data.character_seeds import ORGANIZATIONS, ORG_RANKS, POWER_TYPES

# ═══════════════════════════════════════════════════════════════════
# 组织经济管理器 - 管理所有组织的资金流动
# ═══════════════════════════════════════════════════════════════════

class OrganizationEconomy:
    """
    组织经济系统：
    - 每个组织有金库 (treasury)
    - 首领可以从流民池中招募新成员
    - 成员定期获得薪俸
    - 成员工作收益按比例上缴
    """
    
    # 不同势力类型的薪俸系数
    POWER_SALARY_MULT = {
        '士': 1.5,   # 官员俸禄最高
        '农': 0.8,   # 地主雇工薪水低
        '工': 1.0,   # 工匠标准工资
        '商': 1.2,   # 商铺伙计有提成
        '学': 0.7,   # 学徒薪水低
        '兵': 1.3,   # 军饷较高
        '游': 0.5,   # 江湖人不讲薪俸
        '匪': 0.3,   # 盗匪靠分赃
    }
    
    # 组织等级对应的薪俸基数
    RANK_SALARY_BASE = {
        1: 5,    # 门徒：5铜/日
        2: 10,   # 核心：10铜/日
        3: 20,   # 头目：20铜/日
        4: 35,   # 长老：35铜/日
        5: 0,    # 首领：不发薪水，直接分红
    }
    
    # 招募成本系数（基于组织等级）
    RECRUIT_COST_BASE = 30  # 基础招募成本
    
    def __init__(self):
        # 组织金库: {org_id: treasury_amount}
        self.treasuries = {}
        
        # 组织成员缓存: {org_id: [npc_ids]}
        self.org_members = {}
        
        # 组织首领缓存: {org_id: leader_npc_id}
        self.org_leaders = {}
        
        # 每日收支记录（用于UI显示）
        self.daily_income = {}   # {org_id: income}
        self.daily_expense = {}  # {org_id: expense}
        
        # 招募冷却: {org_id: cooldown_ticks}
        self.recruit_cooldown = {}
        
    def initialize_from_npcs(self, all_cards):
        """
        从NPC列表初始化组织数据
        在游戏开始时调用
        """
        from src.entities.npc import NPC
        
        self.org_members.clear()
        self.org_leaders.clear()
        
        for card in all_cards:
            if not isinstance(card, NPC):
                continue
                
            org_id = getattr(card, 'org_id', None)
            if not org_id or org_id == 'NONE':
                continue
                
            # 添加到成员列表
            if org_id not in self.org_members:
                self.org_members[org_id] = []
            self.org_members[org_id].append(card.id)
            
            # 记录首领
            if getattr(card, 'org_role', None) == 'LEADER':
                self.org_leaders[org_id] = card.id
                
        # 初始化金库（基于组织数据）
        for org_id, org_data in ORGANIZATIONS.items():
            wealth_level = org_data.get('wealth_level', 1)
            # 初始金库 = 财富等级 * 100 + 随机波动
            initial_treasury = wealth_level * 100 + random.randint(0, 50)
            self.treasuries[org_id] = initial_treasury
            self.daily_income[org_id] = 0
            self.daily_expense[org_id] = 0
            self.recruit_cooldown[org_id] = 0
            
        log_game_event("组织经济系统初始化完成", tag="ORG")
        
    def get_treasury(self, org_id):
        """获取组织金库余额"""
        return self.treasuries.get(org_id, 0)
        
    def deposit(self, org_id, amount, reason=""):
        """向组织金库存入资金"""
        if org_id not in self.treasuries:
            self.treasuries[org_id] = 0
        self.treasuries[org_id] += amount
        self.daily_income[org_id] = self.daily_income.get(org_id, 0) + amount
        if reason:
            log_game_event(f"[{org_id}] +{amount}铜 ({reason})", tag="ORG_INCOME")
            
    def withdraw(self, org_id, amount, reason=""):
        """从组织金库支出资金"""
        if org_id not in self.treasuries:
            return False
        if self.treasuries[org_id] < amount:
            return False
        self.treasuries[org_id] -= amount
        self.daily_expense[org_id] = self.daily_expense.get(org_id, 0) + amount
        if reason:
            log_game_event(f"[{org_id}] -{amount}铜 ({reason})", tag="ORG_EXPENSE")
        return True
        
    # ═══════════════════════════════════════════════════════════════
    # 招募系统 - 首领从流民池招募新成员
    # ═══════════════════════════════════════════════════════════════
    
    def get_recruit_cost(self, org_id, refugee_npc):
        """
        计算招募某个流民的成本
        成本 = 基础成本 * 流民社会等级 * 组织财力折扣
        """
        base_cost = self.RECRUIT_COST_BASE
        
        # 流民社会等级影响（有才能的人更贵）
        social_level = getattr(refugee_npc, 'social_level', 1)
        cost = base_cost * social_level
        
        # 组织财力折扣（富裕组织招人更容易）
        org_data = ORGANIZATIONS.get(org_id, {})
        wealth_level = org_data.get('wealth_level', 1)
        discount = 1.0 - (wealth_level - 1) * 0.1  # 每级-10%
        cost = int(cost * max(0.5, discount))
        
        return cost
        
    def can_recruit(self, org_id, refugee_npc):
        """
        检查组织是否可以招募某个流民
        条件：
        1. 组织金库足够
        2. 流民是真正的流民（job=NONE, is_refugee=True）
        3. 招募冷却已过
        """
        # 冷却检查
        if self.recruit_cooldown.get(org_id, 0) > 0:
            return False, "招募冷却中"
            
        # 流民检查
        if getattr(refugee_npc, 'job', '') != 'NONE':
            return False, "不是流民"
        if not getattr(refugee_npc, 'is_refugee', False):
            return False, "不是流民"
        if getattr(refugee_npc, 'org_id', None) not in [None, 'NONE']:
            return False, "已有组织"
            
        # 资金检查
        cost = self.get_recruit_cost(org_id, refugee_npc)
        if self.get_treasury(org_id) < cost:
            return False, f"资金不足(需{cost}铜)"
            
        return True, f"可招募(费用{cost}铜)"
        
    def recruit_refugee(self, org_id, refugee_npc, leader_npc=None):
        """
        执行招募操作
        返回: (success, message)
        """
        can, reason = self.can_recruit(org_id, refugee_npc)
        if not can:
            return False, reason
            
        cost = self.get_recruit_cost(org_id, refugee_npc)
        
        # 扣除金库
        self.withdraw(org_id, cost, f"招募{refugee_npc.name}")
        
        # 更新流民状态
        org_data = ORGANIZATIONS.get(org_id, {})
        power_type = org_data.get('power_type', '民')
        
        # 根据势力类型分配职业
        job_by_power = {
            '士': 'OFFICIAL',
            '农': 'FARMER',
            '工': 'ARTISAN',
            '商': 'MERCHANT',
            '学': 'SCHOLAR',
            '兵': 'GUARD',
            '游': 'GUARD',
            '匪': 'BANDIT',
        }
        new_job = job_by_power.get(power_type, 'NONE')
        
        # 更新NPC属性
        refugee_npc.job = new_job
        refugee_npc.org_id = org_id
        refugee_npc.org_role = 'MEMBER'
        refugee_npc.org_rank = 1  # 新人从门徒开始
        refugee_npc.power_type = power_type
        refugee_npc.is_refugee = False
        
        # 设置与首领的关系
        if leader_npc:
            refugee_npc.relations_data['LEADER'] = leader_npc.id
            
        # 更新缓存
        if org_id not in self.org_members:
            self.org_members[org_id] = []
        self.org_members[org_id].append(refugee_npc.id)
        
        # 设置招募冷却（60秒 = 3600帧）
        self.recruit_cooldown[org_id] = 3600
        
        org_name = org_data.get('name', org_id)
        log_game_event(f"{refugee_npc.name} 加入了 {org_name}，成为{new_job}", tag="RECRUIT")
        
        return True, f"成功招募 {refugee_npc.name}"
        
    # ═══════════════════════════════════════════════════════════════
    # 薪俸系统 - 组织定期支付成员薪水
    # ═══════════════════════════════════════════════════════════════
    
    def calculate_salary(self, npc):
        """计算NPC应得的日薪"""
        org_id = getattr(npc, 'org_id', None)
        if not org_id or org_id == 'NONE':
            return 0
            
        org_rank = getattr(npc, 'org_rank', 1)
        org_role = getattr(npc, 'org_role', 'MEMBER')
        power_type = getattr(npc, 'power_type', '民')
        
        # 首领不拿固定薪水
        if org_role == 'LEADER':
            return 0
            
        # 基础薪俸
        base_salary = self.RANK_SALARY_BASE.get(org_rank, 5)
        
        # 势力类型系数
        power_mult = self.POWER_SALARY_MULT.get(power_type, 1.0)
        
        # 护卫加成
        if org_role == 'BODYGUARD':
            power_mult *= 1.3
            
        return int(base_salary * power_mult)
        
    def pay_daily_salaries(self, all_cards):
        """
        每日结算：支付所有组织的薪俸
        在日循环系统中调用
        返回: {org_id: (total_paid, members_paid)}
        """
        from src.entities.npc import NPC
        
        result = {}
        
        for org_id in list(self.org_members.keys()):
            total_paid = 0
            members_paid = 0
            treasury = self.get_treasury(org_id)
            
            # 找出所有该组织的NPC
            for card in all_cards:
                if not isinstance(card, NPC):
                    continue
                if getattr(card, 'org_id', None) != org_id:
                    continue
                    
                salary = self.calculate_salary(card)
                if salary <= 0:
                    continue
                    
                # 检查金库是否足够
                if treasury >= salary:
                    # 支付薪俸
                    self.withdraw(org_id, salary)
                    card.inventory[ITEM_COIN] = card.inventory.get(ITEM_COIN, 0) + salary
                    treasury -= salary
                    total_paid += salary
                    members_paid += 1
                else:
                    # 发不出工资，增加不满
                    card.dissatisfaction = getattr(card, 'dissatisfaction', 0) + 10
                    log_game_event(f"{card.name} 未收到薪俸，不满+10", tag="ORG")
                    
            result[org_id] = (total_paid, members_paid)
            
        return result
        
    # ═══════════════════════════════════════════════════════════════
    # 贡献系统 - 成员收入按比例上缴
    # ═══════════════════════════════════════════════════════════════
    
    def get_contribution_rate(self, npc):
        """
        获取NPC的贡献比例
        等级越低，上缴比例越高
        """
        org_rank = getattr(npc, 'org_rank', 1)
        org_role = getattr(npc, 'org_role', 'MEMBER')
        
        # 首领不上缴
        if org_role == 'LEADER':
            return 0.0
            
        # 基础贡献率: 门徒50%, 核心40%, 头目30%, 长老20%
        base_rates = {
            1: 0.50,
            2: 0.40,
            3: 0.30,
            4: 0.20,
            5: 0.0,
        }
        return base_rates.get(org_rank, 0.30)
        
    def collect_contribution(self, npc, income):
        """
        从NPC收入中扣除组织贡献
        返回: (npc_keeps, org_gets)
        """
        org_id = getattr(npc, 'org_id', None)
        if not org_id or org_id == 'NONE':
            return income, 0
            
        rate = self.get_contribution_rate(npc)
        org_share = int(income * rate)
        npc_share = income - org_share
        
        if org_share > 0:
            self.deposit(org_id, org_share, f"{npc.name}贡献")
            
        return npc_share, org_share
        
    # ═══════════════════════════════════════════════════════════════
    # 首领AI - 自动招募决策
    # ═══════════════════════════════════════════════════════════════
    
    def update_leader_ai(self, leader_npc, all_cards, refugees):
        """
        首领AI：自动决定是否招募流民
        条件：
        1. 金库充足（>200铜）
        2. 有合适的流民
        3. 组织规模未超过上限
        """
        org_id = getattr(leader_npc, 'org_id', None)
        if not org_id or org_id == 'NONE':
            return None
            
        # 更新冷却
        if self.recruit_cooldown.get(org_id, 0) > 0:
            self.recruit_cooldown[org_id] -= 1
            return None
            
        # 检查金库
        treasury = self.get_treasury(org_id)
        if treasury < 200:
            return None
            
        # 检查组织规模上限（财富等级 * 3）
        org_data = ORGANIZATIONS.get(org_id, {})
        wealth_level = org_data.get('wealth_level', 1)
        max_members = wealth_level * 3 + 2
        current_members = len(self.org_members.get(org_id, []))
        
        if current_members >= max_members:
            return None
            
        # 寻找合适的流民
        for refugee in refugees:
            can, _ = self.can_recruit(org_id, refugee)
            if can:
                # 招募概率：每帧1%
                if random.random() < 0.01:
                    success, msg = self.recruit_refugee(org_id, refugee, leader_npc)
                    if success:
                        return refugee
                        
        return None
        
    # ═══════════════════════════════════════════════════════════════
    # 日结算
    # ═══════════════════════════════════════════════════════════════
    
    def daily_reset(self):
        """每日重置统计数据"""
        for org_id in self.daily_income:
            self.daily_income[org_id] = 0
            self.daily_expense[org_id] = 0
            
    def get_org_summary(self, org_id):
        """获取组织经济摘要（用于UI显示）"""
        org_data = ORGANIZATIONS.get(org_id, {})
        return {
            'name': org_data.get('name', org_id),
            'treasury': self.get_treasury(org_id),
            'members': len(self.org_members.get(org_id, [])),
            'daily_income': self.daily_income.get(org_id, 0),
            'daily_expense': self.daily_expense.get(org_id, 0),
            'power_type': org_data.get('power_type', '民'),
        }

    # ═══════════════════════════════════════════════════════════════
    # 【新增】玩家势力系统 - 玩家加入/晋升/退出组织
    # ═══════════════════════════════════════════════════════════════
    
    # 晋升所需功勋门槛
    PROMOTION_REQUIREMENTS = {
        2: {'merit': 50, 'fame': 10},    # 门徒 → 核心
        3: {'merit': 150, 'fame': 30},   # 核心 → 头目
        4: {'merit': 400, 'fame': 60},   # 头目 → 长老
        5: {'merit': 1000, 'fame': 100}, # 长老 → 首领（需要特殊条件）
    }
    
    # 入门声望门槛（势力类型 → 所需声望）
    JOIN_FAME_REQUIREMENTS = {
        '士': 50,   # 朝廷势力门槛最高
        '农': 20,   # 地主势力
        '工': 10,   # 工匠势力
        '商': 30,   # 商业势力需要一定信誉
        '学': 15,   # 学术势力
        '兵': 25,   # 军事势力
        '游': 5,    # 江湖势力门槛低
        '匪': 0,    # 盗匪势力不看声望（甚至喜欢恶名）
    }
    
    def can_player_join_org(self, player, org_id):
        """
        检查玩家是否可以加入某个组织
        返回: (can_join: bool, reason: str)
        """
        # 1. 已有组织，不能再加入
        if player.player_org_id and player.player_org_id != 'NONE':
            return False, f"你已是{ORGANIZATIONS.get(player.player_org_id, {}).get('name', '某组织')}的成员"
        
        # 2. 组织不存在
        org_data = ORGANIZATIONS.get(org_id)
        if not org_data:
            return False, "此组织不存在"
        
        # 3. 声望检查
        power_type = org_data.get('power_type', '民')
        fame_req = self.JOIN_FAME_REQUIREMENTS.get(power_type, 20)
        
        # 对于盗匪势力，检查是否有恶名（善名太高不让加入）
        if power_type == '匪':
            if player.fame > 30:
                return False, "你名声太好了，盗匪们不信任你"
        else:
            # 普通势力检查善名
            if player.fame < fame_req:
                return False, f"声望不足（需要{fame_req}，当前{player.fame}）"
        
        # 4. 检查玩家与该组织的声望值
        org_standing = player.org_reputation.get(org_id, 0)
        if org_standing < -20:
            return False, f"你与{org_data.get('name')}关系恶劣，无法加入"
        
        return True, "可以加入"
    
    def player_join_org(self, player, org_id, ft_manager=None):
        """
        玩家加入组织
        返回: (success: bool, message: str)
        """
        can_join, reason = self.can_player_join_org(player, org_id)
        if not can_join:
            return False, reason
        
        org_data = ORGANIZATIONS.get(org_id, {})
        org_name = org_data.get('name', org_id)
        power_type = org_data.get('power_type', '民')
        
        # 设置玩家组织属性
        player.player_org_id = org_id
        player.player_org_rank = 1  # 从门徒开始
        player.merit = 0            # 功勋清零
        
        # 根据势力类型设置玩家职业显示（可选）
        # player.power_type = power_type  # 如果想改变玩家势力色
        
        # 添加到组织成员列表
        if org_id not in self.org_members:
            self.org_members[org_id] = []
        self.org_members[org_id].append(player.id)
        
        # 浮动文字反馈
        if ft_manager:
            ft_manager.add_text(f"加入{org_name}！", player.rect.centerx, player.rect.top - 30, 
                               color=(255, 215, 0), size=20)
        
        log_game_event(f"玩家加入了 {org_name}，成为门徒", tag="PLAYER_ORG")
        return True, f"你加入了{org_name}，成为门徒"
    
    def player_leave_org(self, player, ft_manager=None):
        """
        玩家退出组织
        返回: (success: bool, message: str)
        """
        if not player.player_org_id or player.player_org_id == 'NONE':
            return False, "你不属于任何组织"
        
        org_id = player.player_org_id
        org_data = ORGANIZATIONS.get(org_id, {})
        org_name = org_data.get('name', org_id)
        
        # 退出会降低与该组织的声望
        player.org_reputation[org_id] = player.org_reputation.get(org_id, 0) - 30
        
        # 从成员列表移除
        if org_id in self.org_members:
            if player.id in self.org_members[org_id]:
                self.org_members[org_id].remove(player.id)
        
        # 重置玩家组织属性
        player.player_org_id = None
        player.player_org_rank = 0
        player.merit = 0
        
        if ft_manager:
            ft_manager.add_text(f"退出{org_name}", player.rect.centerx, player.rect.top - 30, 
                               color=(255, 100, 100), size=18)
        
        log_game_event(f"玩家退出了 {org_name}", tag="PLAYER_ORG")
        return True, f"你退出了{org_name}，组织声望-30"
    
    def can_player_promote(self, player):
        """
        检查玩家是否可以晋升
        返回: (can_promote: bool, reason: str, next_rank: int)
        """
        if not player.player_org_id or player.player_org_id == 'NONE':
            return False, "你不属于任何组织", 0
        
        current_rank = player.player_org_rank
        next_rank = current_rank + 1
        
        if next_rank > 5:
            return False, "你已是最高级别", current_rank
        
        # 获取晋升条件
        req = self.PROMOTION_REQUIREMENTS.get(next_rank, {'merit': 9999, 'fame': 9999})
        
        # 检查功勋
        if player.merit < req['merit']:
            return False, f"功勋不足（需要{req['merit']}，当前{player.merit}）", next_rank
        
        # 检查声望
        if player.fame < req['fame']:
            return False, f"声望不足（需要{req['fame']}，当前{player.fame}）", next_rank
        
        # 特殊：晋升首领需要击败现任首领（这里简化为组织没有首领或首领倒台）
        if next_rank == 5:
            org_id = player.player_org_id
            leader_id = self.org_leaders.get(org_id)
            if leader_id and leader_id != player.id:
                return False, "需要击败或取代现任首领", next_rank
        
        return True, "可以晋升", next_rank
    
    def player_promote(self, player, ft_manager=None):
        """
        玩家晋升
        返回: (success: bool, message: str)
        """
        can_promote, reason, next_rank = self.can_player_promote(player)
        if not can_promote:
            return False, reason
        
        org_id = player.player_org_id
        org_data = ORGANIZATIONS.get(org_id, {})
        org_name = org_data.get('name', org_id)
        
        # 执行晋升
        player.player_org_rank = next_rank
        
        # 获取等级称号
        rank_names = {1: '门徒', 2: '核心', 3: '头目', 4: '长老', 5: '首领'}
        rank_name = rank_names.get(next_rank, f'{next_rank}级')
        
        # 如果晋升为首领，更新组织首领记录
        if next_rank == 5:
            self.org_leaders[org_id] = player.id
        
        # 浮动文字
        if ft_manager:
            ft_manager.add_text(f"晋升为{rank_name}！", player.rect.centerx, player.rect.top - 40, 
                               color=(255, 215, 0), size=24)
        
        log_game_event(f"玩家在{org_name}晋升为{rank_name}", tag="PLAYER_ORG")
        return True, f"恭喜！你在{org_name}晋升为{rank_name}"
    
    def add_player_merit(self, player, amount, reason="", ft_manager=None):
        """
        给玩家增加功勋
        """
        if not player.player_org_id or player.player_org_id == 'NONE':
            return  # 没有组织，不计功勋
        
        player.merit += amount
        
        if ft_manager and amount > 0:
            ft_manager.add_text(f"+{amount}功勋", player.rect.centerx, player.rect.top - 20, 
                               color=(255, 200, 100), size=16)
        
        if reason:
            log_game_event(f"玩家获得{amount}功勋（{reason}）", tag="MERIT")
    
    def modify_player_org_reputation(self, player, org_id, delta, reason="", ft_manager=None):
        """
        修改玩家与某组织的声望
        
        Args:
            player: 玩家对象
            org_id: 组织ID
            delta: 声望变化值
            reason: 变化原因
            ft_manager: 浮动文字管理器
        """
        current = player.org_reputation.get(org_id, 0)
        new_val = max(-100, min(100, current + delta))
        player.org_reputation[org_id] = new_val
        
        org_name = ORGANIZATIONS.get(org_id, {}).get('name', org_id)
        
        # 浮动文字提示
        if ft_manager and delta != 0:
            color = (100, 200, 255) if delta > 0 else (255, 100, 100)
            ft_manager.add_text(f"{org_name}声望{delta:+d}", 
                               player.rect.centerx, player.rect.top - 30, color)
        
        if reason:
            log_game_event(f"玩家与{org_name}声望{delta:+d}（{reason}）", tag="REPUTATION")
        
        return new_val


# ═══════════════════════════════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════════════════════════════

_org_economy_instance = None

def get_org_economy():
    """获取组织经济系统单例"""
    global _org_economy_instance
    if _org_economy_instance is None:
        _org_economy_instance = OrganizationEconomy()
    return _org_economy_instance
