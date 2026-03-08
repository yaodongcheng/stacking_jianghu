# --- src/tech_system.py ---
from src.definitions import *

class TechNode:
    def __init__(self, t_id, name, desc, cost_money=0, cost_fame=0, req_tech=None, x=0, y=0):
        self.id = t_id
        self.name = name
        self.desc = desc
        self.cost_money = cost_money
        self.cost_fame = cost_fame
        self.req_tech = req_tech # 前置科技ID
        self.unlocked = False
        
        # UI 坐标 (相对于树中心的偏移)
        self.x = x
        self.y = y
        self.visible = True # 默认可见

class TechManager:
    def __init__(self):
        # 定义政策树 (宋代风格)
        # 坐标系: x=0, y=0 为中心顶部
        self.techs = {
            # --- 基础生存 ---
            'T_RECRUIT': TechNode('T_RECRUIT', '保甲法', '允许招募流民，并增加门客上限至3人。', 
                                  cost_money=100, cost_fame=50, x=0, y=0),
            
            'T_FARMING': TechNode('T_FARMING', '农田水利法', '【自动化】允许派遣农夫长期驻守农田自动生产。', 
                                  cost_money=300, cost_fame=100, req_tech='T_RECRUIT', x=-150, y=120),
            
            # --- 商业发展 ---
            'T_TRADE': TechNode('T_TRADE', '市易法', '【自动化】允许派遣商贾长期驻守集市自动交易。', 
                                cost_money=500, cost_fame=200, req_tech='T_RECRUIT', x=150, y=120),
            
            'T_EXPAND': TechNode('T_EXPAND', '开封扩建', '门客上限提升至 5 人，提升流民出现频率。', 
                                 cost_money=800, cost_fame=500, req_tech='T_TRADE', x=150, y=240),
            
            # --- 高级治理 ---
            'T_OFFICIAL': TechNode('T_OFFICIAL', '科举取士', '解锁【文人】职业的特殊事件收益。', 
                                   cost_money=1000, cost_fame=800, req_tech='T_EXPAND', x=50, y=360),
            
            'T_ARMY': TechNode('T_ARMY', '保马法', '解锁【打手】自动巡逻，降低事件危险度。', 
                               cost_money=1500, cost_fame=1000, req_tech='T_EXPAND', x=250, y=360),
        }
        # 默认门客上限
        self.max_followers = 1 

    def is_unlocked(self, t_id):
        if t_id not in self.techs: return False
        return self.techs[t_id].unlocked

    def can_unlock(self, t_id, player):
        tech = self.techs.get(t_id)
        if not tech: return False
        if tech.unlocked: return False
        if player.money < tech.cost_money: return False
        if player.fame < tech.cost_fame: return False
        
        # 检查前置
        if tech.req_tech:
            parent = self.techs.get(tech.req_tech)
            if not parent or not parent.unlocked:
                return False
        return True

    def unlock(self, t_id, player):
        if self.can_unlock(t_id, player):
            tech = self.techs[t_id]
            player.money -= tech.cost_money
            player.fame -= tech.cost_fame
            tech.unlocked = True
            
            # 应用被动效果
            if t_id == 'T_RECRUIT':
                self.max_followers = 3
            elif t_id == 'T_EXPAND':
                self.max_followers = 5
                
            return True, f"成功推行【{tech.name}】"
        return False, "条件不足"

    def get_max_followers(self):
        return self.max_followers