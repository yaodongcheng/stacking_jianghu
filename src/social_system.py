# --- src/social_system.py ---
"""
社会系统：管理NPC之间的关系图谱和组织架构。
"""

# 关系类型常量
REL_PARENT = 'PARENT'
REL_CHILD = 'CHILD'
REL_SPOUSE = 'SPOUSE'
REL_LEADER = 'LEADER'
REL_SUBORDINATE = 'SUBORDINATE'
REL_FRIEND = 'FRIEND'
REL_ENEMY = 'ENEMY'

class Organization:
    def __init__(self, id, name, leader_id=None):
        self.id = id
        self.name = name
        self.leader_id = leader_id
        self.members = [] # list of npc_ids

class SocialGraph:
    def __init__(self):
        # 邻接表: {npc_id: {target_id: 'RELATION_TYPE'}}
        self.relations = {}
        self.orgs = {}

    def register_relation(self, id_a, id_b, rel_type):
        """注册单向关系 (通常在加载NPC时调用)"""
        if id_a not in self.relations: self.relations[id_a] = {}
        self.relations[id_a][id_b] = rel_type
        
        # 自动补全反向关系 (如果是亲属)
        rev_rel = None
        if rel_type == REL_PARENT: rev_rel = REL_CHILD
        elif rel_type == REL_CHILD: rev_rel = REL_PARENT
        elif rel_type == REL_SPOUSE: rev_rel = REL_SPOUSE
        elif rel_type == REL_LEADER: rev_rel = REL_SUBORDINATE
        elif rel_type == REL_SUBORDINATE: rev_rel = REL_LEADER
        elif rel_type == REL_FRIEND: rev_rel = REL_FRIEND
        
        if rev_rel:
            if id_b not in self.relations: self.relations[id_b] = {}
            self.relations[id_b][id_a] = rev_rel

    def get_relation(self, id_a, id_b):
        """获取 A 对 B 的关系"""
        if id_a in self.relations:
            return self.relations[id_a].get(id_b, None)
        return None

    def get_related_npcs(self, id_a, rel_type_filter=None):
        """获取某人的所有关系人 ID"""
        if id_a not in self.relations: return []
        if rel_type_filter:
            return [tid for tid, rel in self.relations[id_a].items() if rel == rel_type_filter]
        return list(self.relations[id_a].keys())
    
    def get_affinity(self, id_a, id_b) -> int:
        """获取两个NPC之间的亲密度/好感度
        
        基于关系类型返回默认亲密度值:
        - 配偶: 80
        - 亲子/父母: 60
        - 朋友: 40
        - 上下级: 20
        - 敌人: -50
        - 无关系: 0
        
        Args:
            id_a: NPC A 的 ID
            id_b: NPC B 的 ID
            
        Returns:
            亲密度数值 (-100 ~ 100)
        """
        # 检查是否有直接关系
        rel = self.get_relation(id_a, id_b)
        
        if rel is None:
            return 0
        
        # 根据关系类型返回默认亲密度
        affinity_map = {
            REL_SPOUSE: 80,
            REL_PARENT: 60,
            REL_CHILD: 60,
            REL_FRIEND: 40,
            REL_LEADER: 20,
            REL_SUBORDINATE: 20,
            REL_ENEMY: -50,
        }
        
        return affinity_map.get(rel, 0)
    
    def modify_affinity(self, id_a, id_b, delta: int):
        """修改两个NPC之间的亲密度
        
        由于当前系统基于关系类型，这里使用一个动态亲密度字典来覆盖默认值。
        
        Args:
            id_a: NPC A 的 ID
            id_b: NPC B 的 ID
            delta: 亲密度变化值 (正数增加，负数减少)
        """
        # 初始化动态亲密度存储（如果不存在）
        if not hasattr(self, '_dynamic_affinity'):
            self._dynamic_affinity = {}
        
        # 创建双向键（确保顺序一致）
        key = tuple(sorted([id_a, id_b]))
        
        # 获取当前亲密度（基础 + 动态）
        base_affinity = self.get_affinity(id_a, id_b)
        current_dynamic = self._dynamic_affinity.get(key, 0)
        
        # 计算新的动态值
        new_dynamic = current_dynamic + delta
        self._dynamic_affinity[key] = new_dynamic
        
        # 计算最终亲密度（限制在 -100 到 100）
        final_affinity = max(-100, min(100, base_affinity + new_dynamic))
        
        print(f"[Social] 亲密度变化: {id_a} ↔ {id_b}: {base_affinity + current_dynamic} → {final_affinity} (delta={delta:+d})")
        
        return final_affinity
    
    def get_affinity_with_dynamic(self, id_a, id_b) -> int:
        """获取包含动态修改的亲密度
        
        Args:
            id_a: NPC A 的 ID
            id_b: NPC B 的 ID
            
        Returns:
            亲密度数值 (-100 ~ 100)
        """
        base = self.get_affinity(id_a, id_b)
        
        if not hasattr(self, '_dynamic_affinity'):
            return base
        
        key = tuple(sorted([id_a, id_b]))
        dynamic = self._dynamic_affinity.get(key, 0)
        
        return max(-100, min(100, base + dynamic))

# 全局单例
social_manager = SocialGraph()
