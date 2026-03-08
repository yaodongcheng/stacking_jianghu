# --- src/ai/job_behaviors/bandit.py ---
"""
山贼/恶霸职业行为
从原ai_system.py抽离 _enqueue_bandit, _enqueue_villain
"""
import math
import random
from src.ai.job_behaviors.base import BaseJobBehavior
from src.definitions import SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED
from src.utils import log_game_event


class BanditBehavior(BaseJobBehavior):
    """
    山贼行为逻辑
    
    基于 social_level 差异化行为：
    - level 1: 喽啰 - 埋伏打劫
    - level 2-3: 头目/精锐 - 带队行动
    - level 4-5: 山大王/二当家 - 山寨坐镇
    """
    
    EXTORT_COOLDOWN_MS = 30000  # 勒索冷却
    PREY_DETECT_RANGE = 150     # 猎物发现距离
    
    def execute(self, npc, context: dict) -> bool:
        """执行山贼行为"""
        world_map = context.get('world_map')
        all_npcs = context.get('all_npcs', [])
        combat_manager = context.get('combat_manager')
        
        if self.has_pending_action(npc):
            return True
        
        # 优先级1：有锁定目标，继续战斗
        if npc.aggro_target is not None and combat_manager:
            self.enqueue_combat(npc, npc.aggro_target, combat_manager, reason=f"攻击{npc.aggro_target.name}")
            return True
        
        # 先处理抢夺目标
        if self._handle_loot_target(npc):
            return True
        
        # 优先级2：有仇恨目标，进入战斗
        enemy = self.find_enemy(npc, all_npcs)
        if enemy and combat_manager:
            self.enqueue_combat(npc, enemy, combat_manager, reason=f"打劫{enemy.name}！")
            return True
        
        social_level = self.get_social_level(npc)
        
        # ─── 山大王 (4-5): 山寨坐镇 ───
        if social_level >= 4:
            return self._boss_behavior(npc, world_map)
        
        # ─── 头目 (2-3): 带队行动 ───
        if social_level >= 2:
            return self._leader_behavior(npc, world_map, all_npcs)
        
        # ─── 喽啰 (1): 埋伏打劫 ───
        return self._grunt_behavior(npc, world_map, all_npcs)
    
    def _handle_loot_target(self, npc) -> bool:
        """处理抢夺目标"""
        loot_target = getattr(npc, '_loot_target', None)
        loot_timer = getattr(npc, '_loot_timer', 0)
        
        if not loot_target or loot_timer <= 0:
            npc._loot_target = None
            npc._loot_timer = 0
            return False
        
        loot_x, loot_y = loot_target
        dist = math.hypot(npc.rect.centerx - loot_x, npc.rect.centery - loot_y)
        
        if dist <= 30:
            # 到达抢夺点 → 拾取
            loot_items = getattr(npc, '_loot_items', [])
            for item in loot_items:
                if item[0] == 'money':
                    npc.money = getattr(npc, 'money', 0) + item[1]
                elif item[0] == 'item':
                    inv = getattr(npc, 'inventory', {})
                    inv[item[1]] = inv.get(item[1], 0) + item[2]
            
            npc._loot_target = None
            npc._loot_timer = 0
            npc._loot_items = []
            npc.ai_reason = "抢夺完成"
            self.enqueue_wait(npc, 1000, "抢到东西了")
            return True
        
        # 移动到抢夺点
        npc._loot_timer = loot_timer - 16
        self.enqueue_move_to_position(npc, loot_x, loot_y, stop_dist=25, reason="前往抢夺")
        return True
    
    def _boss_behavior(self, npc, world_map) -> bool:
        """山大王行为"""
        in_slum = world_map.slum_rect.collidepoint(npc.rect.center)
        roll = random.random()
        
        if roll < 0.5:
            # 50% 山寨坐镇
            if not in_slum:
                tx, ty = world_map.get_random_pos_in_rect(world_map.slum_rect)
                self.enqueue_move_to_position(npc, tx, ty, stop_dist=30, reason="回山寨")
                npc.ai_reason = "返回山寨"
            else:
                self.enqueue_wait(npc, 5000, "坐镇")
                npc.ai_reason = "山寨坐镇"
            return True
        
        elif roll < 0.8:
            # 30% 山寨巡视
            self.enqueue_roam(npc, world_map.slum_rect, duration_ms=6000, reason="巡视")
            npc.ai_reason = "巡视山寨"
            return True
        
        # 20% 运筹帷幄
        self.enqueue_wait(npc, 4000, "思考")
        npc.ai_reason = "运筹帷幄"
        return True
    
    def _leader_behavior(self, npc, world_map, all_npcs) -> bool:
        """头目行为"""
        roll = random.random()
        
        if roll < 0.4:
            # 40% 打劫逻辑
            return self._grunt_behavior(npc, world_map, all_npcs)
        
        elif roll < 0.7:
            # 30% 城外侦察
            bandit_zones = getattr(world_map, 'bandit_zones', None)
            if bandit_zones:
                zone_key = random.choice(['NORTH', 'SOUTH', 'WEST'])
                zone_rect = bandit_zones[zone_key]
                self.enqueue_roam(npc, zone_rect, duration_ms=5000, reason="侦察")
                npc.ai_reason = "侦察敌情"
                return True
        
        # 30% 回山寨
        in_slum = world_map.slum_rect.collidepoint(npc.rect.center)
        if not in_slum:
            tx, ty = world_map.get_random_pos_in_rect(world_map.slum_rect)
            self.enqueue_move_to_position(npc, tx, ty, stop_dist=30, reason="回山寨")
            npc.ai_reason = "返回山寨"
        else:
            self.enqueue_wait(npc, 3000, "休息")
            npc.ai_reason = "寨中歇息"
        return True
    
    def _grunt_behavior(self, npc, world_map, all_npcs) -> bool:
        """喽啰行为"""
        in_city = world_map.city_rect.collidepoint(npc.rect.center)
        in_slum = world_map.slum_rect.collidepoint(npc.rect.center)
        
        # 查找猎物
        prey = self._find_prey(npc, all_npcs)
        
        if prey is not None:
            # 发现猎物 → 积累仇恨
            current_hate = npc.hatred.get(prey.id, 0)
            if current_hate < npc.aggro_threshold:
                npc.hatred[prey.id] = current_hate + 15
                npc.ai_reason = f"盯上{prey.name[:4]}"
                self.enqueue_wait(npc, 500, f"盯上{prey.name[:4]}")
            return True
        
        # 在城内但没猎物 → 撤退
        if in_city:
            tx, ty = world_map.get_random_pos_in_rect(world_map.slum_rect)
            self.enqueue_move_to_position(npc, tx, ty, stop_dist=30, reason="撤回山寨")
            return True
        
        # 在贫民窟 → 埋伏
        if in_slum:
            if random.random() < 0.5:
                self.enqueue_wait(npc, 3000, "埋伏等待")
            else:
                self.enqueue_roam(npc, world_map.slum_rect, duration_ms=6000, reason="巡视地盘")
            return True
        
        # 野外 → 游荡
        bandit_zones = getattr(world_map, 'bandit_zones', None)
        if bandit_zones:
            zone_key = random.choice(['NORTH', 'SOUTH', 'WEST'])
            zone_rect = bandit_zones[zone_key]
            tx, ty = world_map.get_random_pos_in_rect(zone_rect)
        else:
            tx, ty = world_map.get_random_pos_in_rect(world_map.slum_rect)
        
        self.enqueue_move_to_position(npc, tx, ty, stop_dist=30, reason="野外游荡")
        return True
    
    def _find_prey(self, npc, all_npcs) -> object:
        """查找猎物"""
        nearby = getattr(npc, '_nearby_npcs_ref', all_npcs)
        
        prey = None
        prey_dist = 999999
        
        for other in nearby:
            if other is npc:
                continue
            if other.safety in [SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED]:
                continue
            if self._is_villain(other):
                continue
            if other.job == 'PLAYER':
                continue
            
            dist = math.hypot(
                npc.rect.centerx - other.rect.centerx,
                npc.rect.centery - other.rect.centery
            )
            
            if dist > self.PREY_DETECT_RANGE:
                continue
            
            # 有钱或有货物
            money = getattr(other, 'money', 0)
            has_goods = len(getattr(other, 'inventory', {})) > 0
            
            if (money > 0 or has_goods) and dist < prey_dist:
                prey = other
                prey_dist = dist
        
        return prey
    
    def _is_villain(self, npc) -> bool:
        """检查是否是同类"""
        return npc.job in ['BANDIT', 'THUG']
