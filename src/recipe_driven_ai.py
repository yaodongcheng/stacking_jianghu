# src/recipe_driven_ai.py
"""
配方驱动AI系统 - NPC自动从recipes.csv查找可执行配方

设计原则：
1. NPC根据自己的职业(job)查询recipes.csv中匹配的配方
2. 根据当前状态(背包、金钱、位置)筛选可执行的配方
3. 选择最优配方并前往对应建筑执行

核心优势：
- 新增配方无需修改AI代码，自动被NPC识别和执行
- 经济系统自动形成闭环（生产→运输→销售）
- 职业行为由配方数据驱动，而非硬编码
"""

from __future__ import annotations

import math
import random
from typing import List, Dict, Optional, Tuple, TYPE_CHECKING
from src.recipe_system import RecipeManager
from src.definitions import *

if TYPE_CHECKING:
    from src.entities import Building


class RecipeDrivenAI:
    """配方驱动的NPC决策系统"""
    
    def __init__(self, recipe_manager: RecipeManager):
        self.recipe_mgr = recipe_manager
        # 缓存职业->配方映射，避免每帧遍历
        self._job_recipes_cache: Dict[str, List[dict]] = {}
        self._build_job_recipes_cache()
    
    def _build_job_recipes_cache(self):
        """构建职业->可用配方的缓存"""
        self._job_recipes_cache.clear()
        
        for recipe in self.recipe_mgr.recipes:
            job_input = recipe.get('input', 'ANY')
            
            # ANY 表示所有人都可以执行
            if job_input == 'ANY':
                # 添加到所有职业的缓存
                for job in ['FARMER', 'MERCHANT', 'ARTISAN', 'SCHOLAR', 'OFFICIAL', 
                           'GUARD', 'MONK', 'BANDIT', 'THUG', 'DANCER', 'NONE']:
                    if job not in self._job_recipes_cache:
                        self._job_recipes_cache[job] = []
                    self._job_recipes_cache[job].append(recipe)
            else:
                # 特定职业配方
                if job_input not in self._job_recipes_cache:
                    self._job_recipes_cache[job_input] = []
                self._job_recipes_cache[job_input].append(recipe)
    
    def find_executable_recipes(self, npc, all_buildings) -> List[Tuple[dict, Building, float]]:
        """
        为NPC查找所有可执行的配方
        
        返回: [(recipe_dict, target_building, priority_score), ...]
        按优先级排序，priority_score越高越优先
        
        注意: ANY配方已在 _build_job_recipes_cache() 中被分发到每个职业，
              所以这里只需获取该职业的缓存列表即可
        """
        from src.entities import Building
        
        job = getattr(npc, 'job', 'NONE')
        # 职业缓存已包含 ANY 配方（在 _build_job_recipes_cache 中合并）
        available_recipes = self._job_recipes_cache.get(job, [])
        
        results = []
        
        for recipe in available_recipes:
            # 检查配方是否可执行
            can_execute, target_building, score = self._check_recipe_executable(
                npc, recipe, all_buildings
            )
            
            if can_execute and target_building:
                results.append((recipe, target_building, score))
        
        # 按优先级排序（分数高的优先）
        results.sort(key=lambda x: x[2], reverse=True)
        return results
    
    def _check_recipe_executable(self, npc, recipe: dict, all_buildings) -> Tuple[bool, Optional[Building], float]:
        """
        检查单个配方是否可执行
        
        返回: (可执行, 目标建筑, 优先级分数)
        """
        from src.entities import Building
        
        target_type = recipe.get('target_type', '')
        target_id = recipe.get('target_id', '')
        
        # ─── 1. 检查目标建筑是否存在 ─────────────────────────────
        target_building = None
        
        if target_type == 'BUILDING':
            # 找空闲的目标建筑（没有其他NPC在工作）
            matching_buildings = [
                b for b in all_buildings 
                if getattr(b, 'building_type', None) == target_id
            ]
            
            # 优先选择空闲建筑
            empty_buildings = [b for b in matching_buildings if b.stack_child is None]
            if empty_buildings:
                # 选最近的
                target_building = min(
                    empty_buildings,
                    key=lambda b: math.hypot(
                        npc.rect.centerx - b.rect.centerx,
                        npc.rect.centery - b.rect.centery
                    )
                )
            elif matching_buildings:
                # 没有空闲的，但存在该类型建筑（可以排队等待）
                target_building = min(
                    matching_buildings,
                    key=lambda b: math.hypot(
                        npc.rect.centerx - b.rect.centerx,
                        npc.rect.centery - b.rect.centery
                    )
                )
        else:
            # 其他类型的配方（如 HUMAN, RESOURCE）暂不处理
            return (False, None, 0)
        
        if not target_building:
            return (False, None, 0)
        
        # ─── 1.5 社会等级过滤：高等级NPC不做低级体力劳动 ─────────────
        social_level = getattr(npc, 'social_level', 1)
        recipe_id = recipe.get('id', '')
        
        # 体力劳动配方列表（只有低等级NPC才执行）
        LABOR_RECIPES = {
            'CATCH_FISH', 'GATHER_BERRY', 'CHOP_TREE', 'MINE_STONE', 'MINE_IRON',
            'HUNT', 'GATHER_HERB', 'GATHER_MUD', 'GATHER_STICK',
            'WORK_FARM_WHEAT', 'FARM_WORK', 'DIG_ORE', 'DIG_STONE', 'CUT_TREE',
            'MILL_WHEAT', 'MILL_RICE', 'MAKE_NOODLE', 'RAISE_SHEEP', 'BUTCHER',
            'TEND_HORSE'
        }
        
        if recipe_id in LABOR_RECIPES and social_level >= 3:
            # 等级3及以上的NPC不做体力劳动
            return (False, None, 0)
        
        # ─── 2. 检查额外消耗条件 ─────────────────────────────────
        ext_input = recipe.get('ext_input', '')
        if ext_input:
            req_item, req_amt = ext_input.split(':')
            req_amt = int(req_amt)
            
            # 检查NPC背包是否有足够物品
            inv_count = npc.inventory.get(req_item, 0)
            if inv_count < req_amt:
                return (False, None, 0)
            
            # 【关键修复】防止NPC卖掉自己正在穿/用的装备
            # 装备类物品（衣服、武器、防具）如果只有1件，说明正在使用，不能卖
            EQUIPMENT_ITEMS = {
                '粗布衣', '棉袄', '斗篷', '丝衣', '僧袍', '官服',  # 衣服
                '护臂', '铁盔', '锁子甲', '鳞甲', '皮甲',          # 防具
                '铁剑', '朴刀', '长枪', '大刀', '弓箭', '菜刀',    # 武器
            }
            is_sell_recipe = 'SELL' in recipe.get('id', '')
            if is_sell_recipe and req_item in EQUIPMENT_ITEMS and inv_count <= 1:
                # 只有1件装备且是卖货配方 → 不执行（防止卖掉身上穿的）
                return (False, None, 0)
        
        # ─── 3. 检查金钱消耗条件 ─────────────────────────────────
        cost_money = int(recipe.get('cost_money', 0) or 0)
        if cost_money > 0:
            if getattr(npc, 'money', 0) < cost_money:
                return (False, None, 0)
        
        # ─── 4. 计算优先级分数 ─────────────────────────────────
        score = self._calculate_recipe_priority(npc, recipe, target_building)
        
        return (True, target_building, score)
    
    def _calculate_recipe_priority(self, npc, recipe: dict, target_building) -> float:
        """
        计算配方执行的优先级分数
        
        考虑因素：
        - 产出价值（产出金钱的配方更优先）
        - 距离（更近的建筑加分）
        - NPC需求（饥饿时优先寻找食物相关配方）
        - 职业契合度（职业专属配方加分）
        """
        score = 0.0
        
        output = recipe.get('output', '')
        job = getattr(npc, 'job', 'NONE')
        
        # ─── 产出价值 ─────────────────────────────────
        if output.startswith('ITEM:铜钱:'):
            # 直接产出金钱的配方
            parts = output.split(':')
            if len(parts) >= 3:
                coin_amt = int(parts[2])
                score += coin_amt * 2  # 每铜钱+2分
        elif output.startswith('ITEM:'):
            # 产出物品的配方
            score += 10  # 基础分
        elif output.startswith('STAT:'):
            # 状态恢复配方（如休息）
            score += 5
        
        # ─── 距离惩罚 ─────────────────────────────────
        dist = math.hypot(
            npc.rect.centerx - target_building.rect.centerx,
            npc.rect.centery - target_building.rect.centery
        )
        score -= dist / 100  # 每100像素-1分
        
        # ─── 职业契合度 ─────────────────────────────────
        recipe_input = recipe.get('input', 'ANY')
        is_sell_recipe = 'SELL' in recipe.get('id', '')
        
        if recipe_input == job:
            score += 50  # 专属配方大幅加分（比卖货更重要）
        elif recipe_input == 'ANY' and is_sell_recipe:
            # 通用卖货配方：降低优先级，让 NPC 优先做本职工作
            score -= 20
        
        # ─── 建筑空闲加分 ─────────────────────────────────
        if target_building.stack_child is None:
            score += 15  # 空闲建筑优先
        
        # ─── 紧急需求 ─────────────────────────────────
        # 只有背包真的满了（>=10件）才考虑卖货
        total_items = sum(npc.inventory.values()) if hasattr(npc, 'inventory') else 0
        if total_items >= 10:  # 背包快满了（提高阈值）
            if is_sell_recipe:
                score += 30  # 卖货配方加分
        
        # 如果NPC没钱且是生产职业，优先执行赚钱配方
        if getattr(npc, 'money', 0) < 10 and job in ('FARMER', 'ARTISAN', 'MERCHANT'):
            if output.startswith('ITEM:铜钱:'):
                score += 25
        
        return score
    
    def get_best_recipe_action(self, npc, all_buildings) -> Optional[Tuple[dict, Building]]:
        """
        为NPC获取最佳的配方和目标建筑
        
        返回: (recipe_dict, target_building) 或 None
        """
        results = self.find_executable_recipes(npc, all_buildings)
        
        if results:
            best = results[0]
            return (best[0], best[1])
        return None
    
    def get_work_building_for_job(self, job: str, all_buildings, prefer_empty: bool = True) -> Optional[Building]:
        """
        根据职业获取适合工作的建筑
        
        职业->建筑映射从配方表动态推导
        """
        # 从缓存的配方中找出该职业能使用的建筑类型
        job_recipes = self._job_recipes_cache.get(job, [])
        
        suitable_building_types = set()
        for recipe in job_recipes:
            if recipe.get('target_type') == 'BUILDING':
                suitable_building_types.add(recipe.get('target_id'))
        
        if not suitable_building_types:
            return None
        
        # 找出符合条件的建筑
        candidates = []
        for b in all_buildings:
            b_type = getattr(b, 'building_type', None)
            if b_type in suitable_building_types:
                if prefer_empty and b.stack_child is not None:
                    continue
                candidates.append(b)
        
        if candidates:
            return random.choice(candidates)
        return None


# ══════════════════════════════════════════════════════════════
# 职业->推荐建筑类型映射（硬编码备份，当配方表不完整时使用）
# ══════════════════════════════════════════════════════════════
JOB_BUILDING_MAP = {
    'FARMER':   ['FARM', 'MILL', 'RANCH', 'HUNTING'],
    'MERCHANT': ['MARKET', 'PAWNSHOP', 'GRAIN_SHOP', 'TEAHOUSE', 'TAVERN', 'STABLE'],
    'ARTISAN':  ['WORKSHOP', 'SMITHY', 'WEAVING', 'KILN', 'JEWELER'],
    'SCHOLAR':  ['SCHOOL', 'LIBRARY', 'CLINIC'],
    'OFFICIAL': ['GOV_OFFICE', 'JAIL'],
    'GUARD':    ['GOV_OFFICE', 'GATEHOUSE', 'BARRACKS', 'ARMORY'],
    'MONK':     ['TEMPLE', 'TAOIST', 'PHARMACY'],
    'DANCER':   ['THEATER', 'BROTHEL'],
    'BANDIT':   ['BANDIT_LAIR', 'BLACKMARKET', 'GAMBLING'],
    'THUG':     ['GAMBLING', 'BROTHEL', 'BLACKMARKET'],
}


# ══════════════════════════════════════════════════════════════
# 单例访问器
# ══════════════════════════════════════════════════════════════
_recipe_driven_ai: Optional[RecipeDrivenAI] = None

def get_recipe_driven_ai() -> RecipeDrivenAI:
    """获取配方驱动AI的单例"""
    global _recipe_driven_ai
    if _recipe_driven_ai is None:
        from src.recipe_system import RecipeManager
        recipe_mgr = RecipeManager()
        _recipe_driven_ai = RecipeDrivenAI(recipe_mgr)
    return _recipe_driven_ai

def reset_recipe_driven_ai():
    """重置单例（用于重新加载配方后刷新缓存）"""
    global _recipe_driven_ai
    _recipe_driven_ai = None
