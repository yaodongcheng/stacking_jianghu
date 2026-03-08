# --- src/ai/job_behaviors/scholar.py ---
"""
学者/僧侣职业行为
从原ai_system.py抽离 _enqueue_scholar
"""
import random
from src.ai.job_behaviors.base import BaseJobBehavior
from src.definitions import ITEM_BOOK
from src.utils import log_game_event


class ScholarBehavior(BaseJobBehavior):
    """
    学者行为逻辑
    
    工作循环：学堂著书 → 产出书卷 → 卖书/论道
    基于 social_level 差异化行为：
    - level 1: 学生/书童 - 学习、跑腿
    - level 2-3: 秀才/举人 - 著书立说
    - level 4-5: 大儒/名士 - 讲学授徒
    """
    
    WORK_TIME_MS = 20000   # 工作20秒产出1本书
    BOOK_PRICE = 8         # 书卷售价
    
    def execute(self, npc, context: dict) -> bool:
        """执行学者行为"""
        all_buildings = context.get('all_buildings', [])
        world_map = context.get('world_map')
        
        if self.has_pending_action(npc):
            return True
        
        social_level = self.get_social_level(npc)
        
        # ─── 大儒/名士 (4-5): 讲学为主 ───
        if social_level >= 4:
            return self._master_behavior(npc, all_buildings, world_map)
        
        # ─── 秀才/举人 (2-3): 著书立说 ───
        if social_level >= 2:
            return self._scholar_behavior(npc, all_buildings, world_map)
        
        # ─── 学生/书童 (1): 学习为主 ───
        return self._student_behavior(npc, all_buildings, world_map)
    
    def _master_behavior(self, npc, all_buildings, world_map) -> bool:
        """大儒行为"""
        roll = random.random()
        
        if roll < 0.5:
            # 50% 在学堂讲学（找最近的学堂）
            school = self.find_nearest_building(npc, all_buildings, 'SCHOOL')
            if school:
                if not self.is_at_building(npc, school, 80):
                    self.enqueue_move_to_building(npc, school, "讲学")
                    npc.ai_reason = "去学堂讲学"
                    return True
                self.enqueue_wait(npc, 6000, "讲学")
                npc.ai_reason = "学堂讲学"
                return True
        
        elif roll < 0.8:
            # 30% 茶馆论道（找最近的茶馆）
            teahouse = self.find_nearest_building(npc, all_buildings, 'TEAHOUSE')
            if teahouse:
                self.enqueue_move_to_building(npc, teahouse, "论道")
                npc.ai_reason = "茶馆论道"
                return True
        
        # 20% 散步思考
        self.enqueue_roam(npc, world_map.city_rect, duration_ms=5000, reason="散步")
        npc.ai_reason = "散步思考"
        return True
    
    def _scholar_behavior(self, npc, all_buildings, world_map) -> bool:
        """普通学者行为"""
        # 查找最近的学堂
        school = self.find_nearest_building(npc, all_buildings, 'SCHOOL')
        if not school:
            self.enqueue_roam(npc, world_map.city_rect, reason="找学堂")
            return True
        
        # 有书要卖
        book_count = npc.inventory.get(ITEM_BOOK, 0)
        if book_count >= 2:
            return self._sell_books(npc, all_buildings, world_map)
        
        # 前往学堂工作
        if not self.is_at_building(npc, school):
            self.enqueue_move_to_building(npc, school, "著书")
            npc.ai_reason = "去学堂"
            return True
        
        # 在学堂著书
        self._do_writing(npc, school)
        return True
    
    def _student_behavior(self, npc, all_buildings, world_map) -> bool:
        """学生行为"""
        # 查找最近的学堂
        school = self.find_nearest_building(npc, all_buildings, 'SCHOOL')
        if not school:
            self.enqueue_roam(npc, world_map.city_rect, reason="找学堂")
            return True
        
        # 前往学堂
        if not self.is_at_building(npc, school):
            self.enqueue_move_to_building(npc, school, "学习")
            npc.ai_reason = "去学堂"
            return True
        
        # 学习（不产出）
        roll = random.random()
        if roll < 0.7:
            self.enqueue_wait(npc, 5000, "读书")
            npc.ai_reason = "读书学习"
        else:
            # 偶尔帮先生跑腿
            self.enqueue_roam(npc, world_map.city_rect, duration_ms=4000, reason="跑腿")
            npc.ai_reason = "帮先生跑腿"
        return True
    
    def _do_writing(self, npc, school):
        """著书"""
        work_time = getattr(npc, '_scholar_work_time', 0)
        work_time += getattr(npc, '_dt_ms', 16)
        
        if work_time >= self.WORK_TIME_MS:
            # 产出书卷
            npc.inventory[ITEM_BOOK] = npc.inventory.get(ITEM_BOOK, 0) + 1
            school.inventory[ITEM_BOOK] = school.inventory.get(ITEM_BOOK, 0) + 1
            npc._scholar_work_time = 0
            npc.ai_reason = "著成一卷"
            log_game_event(f"[学者] {npc.name} 著成一卷书", tag="ECONOMY")
        else:
            npc._scholar_work_time = work_time
            progress = int(work_time / self.WORK_TIME_MS * 100)
            npc.ai_reason = f"著书{progress}%"
        
        self.enqueue_wait(npc, 2000, "著书")
    
    def _sell_books(self, npc, all_buildings, world_map) -> bool:
        """卖书"""
        # 优先最近的茶馆
        teahouse = self.find_nearest_building(npc, all_buildings, 'TEAHOUSE')
        if teahouse and random.random() < 0.6:
            if not self.is_at_building(npc, teahouse):
                self.enqueue_move_to_building(npc, teahouse, "卖书")
                npc.ai_reason = "去茶馆卖书"
                return True
        
        # 或去最近的市场
        market = self.find_nearest_building(npc, all_buildings, 'MARKET')
        if market:
            if not self.is_at_building(npc, market):
                self.enqueue_move_to_position(
                    npc, market.rect.centerx, market.rect.centery,
                    stop_dist=50, reason="去卖书"
                )
                npc.ai_reason = "去市场卖书"
                return True
        
        # 卖掉书
        books = npc.inventory.get(ITEM_BOOK, 0)
        if books > 0:
            earnings = books * self.BOOK_PRICE
            actual = self.apply_org_contribution(npc, earnings)
            npc.money += actual
            npc.inventory[ITEM_BOOK] = 0
            npc.ai_reason = f"卖书+{actual}铜"
        
        self.enqueue_wait(npc, 1500, "交易")
        return True
