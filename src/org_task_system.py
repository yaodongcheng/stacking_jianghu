# --- src/org_task_system.py ---
"""
组织任务系统
玩家加入门派后可以领取组织任务，完成后获得功勋和奖励

玩家感知入口:
1. NPC对话 - 找长老"领取任务"/"交付任务"
2. UI面板 - FACTION面板的"门派任务"标签页
3. 浮动文字 - "+15功勋" / "任务完成!"
"""

import csv
import random
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

from src.utils import resource_path


class OrgTaskType(Enum):
    """任务类型"""
    GATHER = "GATHER"       # 采集物品
    KILL = "KILL"           # 击杀目标
    INTERACT = "INTERACT"   # 与NPC交谈
    ESCORT = "ESCORT"       # 护送NPC
    PATROL = "PATROL"       # 巡逻区域
    RECRUIT = "RECRUIT"     # 招募成员
    GIVE = "GIVE"           # 赠送物品给NPC


class OrgTaskStatus(Enum):
    """任务状态"""
    AVAILABLE = "available"     # 可接取
    ACTIVE = "active"           # 进行中
    COMPLETED = "completed"     # 已完成(待交付)
    TURNED_IN = "turned_in"     # 已交付
    COOLDOWN = "cooldown"       # 冷却中

# 别名 (兼容旧代码)
OrgTaskState = OrgTaskStatus


@dataclass
class OrgTask:
    """组织任务数据"""
    id: str
    org_id: str              # 所属组织
    title: str               # 任务标题
    task_type: OrgTaskType   # 任务类型
    target: str              # 目标(物品名/NPC ID/区域名)
    count: int               # 目标数量
    merit_reward: int        # 功勋奖励
    money_reward: int        # 金钱奖励
    item_reward: str         # 物品奖励 (格式: "物品名:数量")
    min_rank: int            # 最低职级要求
    cooldown_days: int       # 冷却天数
    desc: str                # 任务描述
    
    # 运行时状态
    status: OrgTaskStatus = field(default=OrgTaskStatus.AVAILABLE)
    progress: int = field(default=0)           # 当前进度
    cooldown_until: int = field(default=0)     # 冷却结束的游戏日
    
    @classmethod
    def from_csv_row(cls, row: dict) -> 'OrgTask':
        """从CSV行创建任务"""
        return cls(
            id=row['id'],
            org_id=row['org_id'],
            title=row['title'],
            task_type=OrgTaskType(row['type']),
            target=row['target'],
            count=int(row['count']),
            merit_reward=int(row['merit_reward']),
            money_reward=int(row['money_reward']),
            item_reward=row.get('item_reward', ''),
            min_rank=int(row.get('min_rank', 0)),
            cooldown_days=int(row.get('cooldown_days', 1)),
            desc=row['desc']
        )
    
    def get_progress_text(self) -> str:
        """获取进度文本"""
        return f"{self.progress}/{self.count}"
    
    def is_complete(self) -> bool:
        """检查是否完成目标"""
        return self.progress >= self.count
    
    # 属性别名 (兼容UI代码)
    @property
    def name(self) -> str:
        """任务名称 (title的别名)"""
        return self.title
    
    @property
    def description(self) -> str:
        """任务描述 (desc的别名)"""
        return self.desc
    
    @property
    def task_id(self) -> str:
        """任务ID (id的别名)"""
        return self.id
    
    @property
    def reward_money(self) -> int:
        """金钱奖励 (money_reward的别名)"""
        return self.money_reward
    
    @property
    def reward_merit(self) -> int:
        """功勋奖励 (merit_reward的别名)"""
        return self.merit_reward
    
    @property
    def state(self) -> OrgTaskStatus:
        """任务状态 (status的别名)"""
        return self.status


class OrgTaskSystem:
    """
    组织任务管理系统
    
    核心职责:
    1. 加载和管理任务配置
    2. 处理任务接取/完成/交付流程
    3. 检查任务进度
    4. 发放奖励
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'OrgTaskSystem':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        # 任务模板库 {task_id: OrgTask}
        self.task_templates: Dict[str, OrgTask] = {}
        
        # 玩家当前的组织任务 {org_id: [OrgTask]}
        self.player_tasks: Dict[str, List[OrgTask]] = {}
        
        # 玩家在各组织的功勋 {org_id: merit}
        self.player_merit: Dict[str, int] = {}
        
        # 玩家在各组织的职级 {org_id: rank}
        self.player_rank: Dict[str, int] = {}
        
        # 今日已完成的任务ID列表
        self.completed_today: List[str] = []
        
        # 当前游戏日(由外部更新)
        self.current_day: int = 1
        
        # 加载任务配置
        self._load_tasks()
    
    def _load_tasks(self):
        """从CSV加载任务配置"""
        try:
            path = resource_path('data/org_task_config.csv')
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    task = OrgTask.from_csv_row(row)
                    self.task_templates[task.id] = task
            print(f"[OrgTask] 加载了 {len(self.task_templates)} 个组织任务模板")
        except FileNotFoundError:
            print("[OrgTask] 警告: org_task_config.csv 未找到")
        except Exception as e:
            print(f"[OrgTask] 加载任务配置失败: {e}")
    
    # ═══════════════════════════════════════════════════════════════
    # 玩家接口 (供UI和NPC对话调用)
    # ═══════════════════════════════════════════════════════════════
    
    def get_available_tasks(self, org_id: str, player_or_rank = 0) -> List[OrgTask]:
        """
        获取玩家可接取的任务列表
        
        Args:
            org_id: 组织ID
            player_or_rank: 玩家对象 或 玩家在该组织的职级(int)
        
        Returns:
            可接取的任务列表
        """
        # 兼容两种调用方式: 传入player对象 或 传入rank整数
        if isinstance(player_or_rank, int):
            player_rank = player_or_rank
        else:
            # 传入的是player对象，从系统中获取职级
            player_rank = self.player_rank.get(org_id, 0)
        
        available = []
        
        for task_id, template in self.task_templates.items():
            if template.org_id != org_id:
                continue
            
            # 检查职级要求
            if template.min_rank > player_rank:
                continue
            
            # 检查是否已接取
            if self._is_task_active(org_id, task_id):
                continue
            
            # 检查冷却
            if self._is_task_on_cooldown(task_id):
                continue
            
            # 创建任务副本
            task_copy = OrgTask.from_csv_row({
                'id': template.id,
                'org_id': template.org_id,
                'title': template.title,
                'type': template.task_type.value,
                'target': template.target,
                'count': template.count,
                'merit_reward': template.merit_reward,
                'money_reward': template.money_reward,
                'item_reward': template.item_reward,
                'min_rank': template.min_rank,
                'cooldown_days': template.cooldown_days,
                'desc': template.desc
            })
            available.append(task_copy)
        
        return available
    
    def get_active_tasks(self, org_id: str) -> List[OrgTask]:
        """获取玩家在该组织进行中的任务"""
        return [t for t in self.player_tasks.get(org_id, []) 
                if t.status in (OrgTaskStatus.ACTIVE, OrgTaskStatus.COMPLETED)]
    
    def get_all_player_tasks(self) -> Dict[str, List[OrgTask]]:
        """获取玩家所有组织的任务"""
        return self.player_tasks
    
    def accept_task(self, org_id: str, task_id: str, ft_manager=None, player=None) -> Tuple[bool, str]:
        """
        接取任务
        
        Args:
            org_id: 组织ID
            task_id: 任务ID
            ft_manager: 浮动文字管理器(用于反馈)
            player: 玩家对象(用于显示位置)
        
        Returns:
            (成功, 消息)
        """
        # 查找任务模板
        template = self.task_templates.get(task_id)
        if not template:
            return False, "任务不存在"
        
        if template.org_id != org_id:
            return False, "任务不属于该组织"
        
        # 检查是否已接取
        if self._is_task_active(org_id, task_id):
            return False, "任务已接取"
        
        # 检查职级
        player_rank = self.player_rank.get(org_id, 0)
        if template.min_rank > player_rank:
            return False, f"需要职级 {template.min_rank} 以上"
        
        # 检查冷却
        if self._is_task_on_cooldown(task_id):
            return False, "任务冷却中"
        
        # 创建任务实例
        task = OrgTask.from_csv_row({
            'id': template.id,
            'org_id': template.org_id,
            'title': template.title,
            'type': template.task_type.value,
            'target': template.target,
            'count': template.count,
            'merit_reward': template.merit_reward,
            'money_reward': template.money_reward,
            'item_reward': template.item_reward,
            'min_rank': template.min_rank,
            'cooldown_days': template.cooldown_days,
            'desc': template.desc
        })
        task.status = OrgTaskStatus.ACTIVE
        task.progress = 0
        
        # 添加到玩家任务列表
        if org_id not in self.player_tasks:
            self.player_tasks[org_id] = []
        self.player_tasks[org_id].append(task)
        
        # 浮动文字反馈
        if ft_manager and player:
            ft_manager.add_text(f"[任] 接取: {task.title}",
                               player.rect.centerx, player.rect.top - 30, 
                               (200, 230, 255))
        
        print(f"[OrgTask] 玩家接取任务: {task.title} ({org_id})")
        return True, f"接取任务: {task.title}"
    
    def turn_in_task(self, org_id: str, task_id: str, player=None, ft_manager=None) -> Tuple[bool, str, dict]:
        """
        交付任务
        
        Args:
            org_id: 组织ID
            task_id: 任务ID
            player: 玩家对象
            ft_manager: 浮动文字管理器
        
        Returns:
            (成功, 消息, 奖励详情)
        """
        # 查找任务
        task = self._find_player_task(org_id, task_id)
        if not task:
            return False, "未找到该任务", {}
        
        if task.status != OrgTaskStatus.COMPLETED:
            return False, f"任务未完成 ({task.progress}/{task.count})", {}
        
        # 发放奖励
        rewards = self._grant_rewards(task, player, ft_manager)
        
        # 更新任务状态
        task.status = OrgTaskStatus.TURNED_IN
        task.cooldown_until = self.current_day + task.cooldown_days
        
        # 从活跃任务中移除
        if org_id in self.player_tasks:
            self.player_tasks[org_id] = [
                t for t in self.player_tasks[org_id] if t.id != task_id
            ]
        
        # 记录今日完成
        self.completed_today.append(task_id)
        
        print(f"[OrgTask] 玩家交付任务: {task.title} | 奖励: {rewards}")
        return True, f"任务完成: {task.title}", rewards
    
    def check_task_progress(self, player, all_cards: list, ft_manager=None):
        """
        检查所有进行中任务的进度
        应该在主循环中定期调用
        
        Args:
            player: 玩家对象
            all_cards: 所有卡牌列表
            ft_manager: 浮动文字管理器
        """
        for org_id, tasks in self.player_tasks.items():
            for task in tasks:
                if task.status != OrgTaskStatus.ACTIVE:
                    continue
                
                old_progress = task.progress
                
                # 根据任务类型检查进度
                if task.task_type == OrgTaskType.GATHER:
                    task.progress = self._check_gather_progress(task, player, all_cards)
                elif task.task_type == OrgTaskType.KILL:
                    task.progress = self._check_kill_progress(task, player)
                elif task.task_type == OrgTaskType.INTERACT:
                    # INTERACT 类型在对话时更新，这里不处理
                    pass
                elif task.task_type == OrgTaskType.PATROL:
                    task.progress = self._check_patrol_progress(task, player, all_cards)
                
                # 检查是否刚刚完成
                if task.progress >= task.count and old_progress < task.count:
                    task.status = OrgTaskStatus.COMPLETED
                    if ft_manager and player:
                        ft_manager.add_text(f"[ok] {task.title} 完成!",
                                           player.rect.centerx, player.rect.top - 50, 
                                           (100, 255, 100))
                        ft_manager.add_text("找长老交付任务", 
                                           player.rect.centerx, player.rect.top - 30, 
                                           (200, 200, 150))
    
    def on_npc_interaction(self, npc_id: str, org_id: str = None):
        """
        当玩家与NPC交谈时调用，更新INTERACT类型任务进度
        
        Args:
            npc_id: NPC ID
            org_id: 限定组织(可选)
        """
        for oid, tasks in self.player_tasks.items():
            if org_id and oid != org_id:
                continue
            
            for task in tasks:
                if (task.status == OrgTaskStatus.ACTIVE and 
                    task.task_type == OrgTaskType.INTERACT and
                    task.target == str(npc_id)):
                    task.progress = task.count
                    task.status = OrgTaskStatus.COMPLETED
                    print(f"[OrgTask] INTERACT任务完成: {task.title}")
    
    def on_enemy_killed(self, enemy_type: str, player):
        """
        当玩家击杀敌人时调用
        
        Args:
            enemy_type: 敌人类型 (如 "BANDIT", "MERCHANT")
            player: 玩家对象
        """
        # 更新玩家击杀记录
        if not hasattr(player, 'kill_counts'):
            player.kill_counts = {}
        player.kill_counts[enemy_type] = player.kill_counts.get(enemy_type, 0) + 1
    
    def on_day_change(self, new_day: int):
        """
        当游戏日改变时调用
        
        Args:
            new_day: 新的游戏日
        """
        self.current_day = new_day
        self.completed_today.clear()
    
    # ═══════════════════════════════════════════════════════════════
    # 功勋和职级
    # ═══════════════════════════════════════════════════════════════
    
    def get_player_merit(self, org_id: str) -> int:
        """获取玩家在组织的功勋"""
        return self.player_merit.get(org_id, 0)
    
    def get_player_rank(self, org_id: str) -> int:
        """获取玩家在组织的职级"""
        return self.player_rank.get(org_id, 0)
    
    def get_rank_name(self, org_id: str, rank: int) -> str:
        """获取职级名称"""
        # 各组织职级名称
        RANK_NAMES = {
            'heifeng_zhai': ['喽啰', '小头目', '堂主', '副寨主', '寨主'],
            'beggar_gang': ['小乞丐', '九袋弟子', '七袋弟子', '五袋长老', '帮主'],
            'yamen': ['衙役', '捕快', '捕头', '都头', '知县'],
            'gao_family': ['家丁', '管事', '大管家', '副家主', '家主'],
        }
        
        names = RANK_NAMES.get(org_id, ['成员', '骨干', '长老', '副首领', '首领'])
        if rank < 0:
            rank = 0
        if rank >= len(names):
            rank = len(names) - 1
        return names[rank]
    
    def get_next_rank_requirement(self, org_id: str, current_rank: int) -> int:
        """获取晋升到下一职级所需功勋"""
        # 各职级晋升所需功勋
        RANK_REQUIREMENTS = [0, 50, 150, 350, 700]
        
        next_rank = current_rank + 1
        if next_rank >= len(RANK_REQUIREMENTS):
            return -1  # 已是最高职级
        return RANK_REQUIREMENTS[next_rank]
    
    def check_promotion(self, org_id: str, player=None, ft_manager=None) -> Tuple[bool, str]:
        """
        检查是否可以晋升
        
        Returns:
            (是否晋升, 新职级名称)
        """
        current_merit = self.player_merit.get(org_id, 0)
        current_rank = self.player_rank.get(org_id, 0)
        
        required = self.get_next_rank_requirement(org_id, current_rank)
        if required < 0:
            return False, ""  # 已是最高
        
        if current_merit >= required:
            # 晋升!
            new_rank = current_rank + 1
            self.player_rank[org_id] = new_rank
            new_rank_name = self.get_rank_name(org_id, new_rank)
            
            # 浮动文字
            if ft_manager and player:
                ft_manager.add_text(f"[升] 晋升为【{new_rank_name}】!",
                                   player.rect.centerx, player.rect.top - 70, 
                                   (255, 215, 0))
            
            print(f"[OrgTask] 玩家在 {org_id} 晋升为 {new_rank_name} (Rank {new_rank})")
            return True, new_rank_name
        
        return False, ""
    
    def get_player_rank_name(self, org_id: str) -> str:
        """获取玩家在组织的职级名称"""
        rank = self.player_rank.get(org_id, 0)
        return self.get_rank_name(org_id, rank)
    
    def get_org_display_name(self, org_id: str) -> str:
        """获取组织的显示名称"""
        ORG_DISPLAY_NAMES = {
            'heifeng_zhai': '黑风寨',
            'beggar_gang': '丐帮',
            'kaifeng_fu': '开封府',
            'yamen': '衙门',
            'gao_manor': '高家庄',
            'qinglang_bang': '青狼帮',
            'luopo_gang': '落魄帮',
            'tianshui_alley': '甜水巷',
            'shizizhipo': '十字坡',
            'daxiangguo': '大相国寺',
            'taixue': '太学',
            'shenhou_fu': '审厚府',
        }
        return ORG_DISPLAY_NAMES.get(org_id, org_id)
    
    def _get_org_style(self, org_id: str) -> str:
        """
        获取组织风格，用于生成对话语气
        
        Returns:
            'gang'    - 帮派风格 (黑风寨、青狼帮等)
            'official'- 官府风格 (开封府、衙门)
            'temple'  - 寺庙风格 (大相国寺)
            'merchant'- 商人风格 (甜水巷、十字坡)
            'school'  - 学院风格 (太学)
            'default' - 默认风格
        """
        ORG_STYLES = {
            'heifeng_zhai': 'gang',
            'qinglang_bang': 'gang',
            'luopo_gang': 'gang',
            'beggar_gang': 'gang',
            'kaifeng_fu': 'official',
            'yamen': 'official',
            'shenhou_fu': 'official',
            'daxiangguo': 'temple',
            'tianshui_alley': 'merchant',
            'shizizhipo': 'merchant',
            'gao_manor': 'merchant',
            'taixue': 'school',
        }
        return ORG_STYLES.get(org_id, 'default')
    
    def get_task_progress_text(self, task: OrgTask) -> str:
        """获取任务进度文本描述"""
        if task.task_type == OrgTaskType.GATHER:
            return f"进度: {task.progress}/{task.count} {task.target}"
        elif task.task_type == OrgTaskType.KILL:
            return f"击杀进度: {task.progress}/{task.count}"
        elif task.task_type == OrgTaskType.INTERACT:
            return f"交谈对象: {task.target}" if task.progress == 0 else "已交谈"
        elif task.task_type == OrgTaskType.PATROL:
            return f"巡逻进度: {task.progress}/{task.count}"
        else:
            return f"{task.progress}/{task.count}"
    
    # ═══════════════════════════════════════════════════════════════
    # UI数据接口
    # ═══════════════════════════════════════════════════════════════
    
    def get_task_panel_data(self, org_id: str, player_rank: int = 0) -> dict:
        """
        获取任务面板显示数据
        
        Returns:
            {
                'available': [可接取任务列表],
                'active': [进行中任务列表],
                'completed_today': [今日完成数量],
                'merit': 当前功勋,
                'rank': 当前职级,
                'rank_name': 职级名称,
                'next_rank_merit': 下一职级所需功勋
            }
        """
        return {
            'available': self.get_available_tasks(org_id, player_rank),
            'active': self.get_active_tasks(org_id),
            'completed_today': len([t for t in self.completed_today 
                                   if t.startswith(f"OT_{org_id[:2].upper()}")]),
            'merit': self.player_merit.get(org_id, 0),
            'rank': self.player_rank.get(org_id, 0),
            'rank_name': self.get_rank_name(org_id, self.player_rank.get(org_id, 0)),
            'next_rank_merit': self.get_next_rank_requirement(
                org_id, self.player_rank.get(org_id, 0)
            )
        }
    
    # ═══════════════════════════════════════════════════════════════
    # 内部方法
    # ═══════════════════════════════════════════════════════════════
    
    def _is_task_active(self, org_id: str, task_id: str) -> bool:
        """检查任务是否已接取"""
        for task in self.player_tasks.get(org_id, []):
            if task.id == task_id and task.status in (OrgTaskStatus.ACTIVE, OrgTaskStatus.COMPLETED):
                return True
        return False
    
    def _is_task_on_cooldown(self, task_id: str) -> bool:
        """检查任务是否在冷却"""
        template = self.task_templates.get(task_id)
        if not template:
            return False
        # 简单实现：检查是否今日已完成
        return task_id in self.completed_today
    
    def _find_player_task(self, org_id: str, task_id: str) -> Optional[OrgTask]:
        """查找玩家的任务实例"""
        for task in self.player_tasks.get(org_id, []):
            if task.id == task_id:
                return task
        return None
    
    def _grant_rewards(self, task: OrgTask, player, ft_manager) -> dict:
        """发放任务奖励"""
        rewards = {}
        
        # 功勋
        if task.merit_reward > 0:
            org_id = task.org_id
            self.player_merit[org_id] = self.player_merit.get(org_id, 0) + task.merit_reward
            rewards['merit'] = task.merit_reward
            
            if ft_manager and player:
                ft_manager.add_text(f"+{task.merit_reward} 功勋", 
                                   player.rect.centerx, player.rect.top - 30, 
                                   (255, 200, 100))
        
        # 金钱
        if task.money_reward > 0 and player:
            player.money = getattr(player, 'money', 0) + task.money_reward
            rewards['money'] = task.money_reward
            
            if ft_manager:
                ft_manager.add_text(f"+{task.money_reward} 铜钱", 
                                   player.rect.centerx, player.rect.top - 50, 
                                   (255, 215, 0))
        
        # 物品奖励
        if task.item_reward and player:
            # 格式: "物品名:数量"
            parts = task.item_reward.split(':')
            if len(parts) == 2:
                item_name, count_str = parts
                count = int(count_str)
                if not hasattr(player, 'inventory'):
                    player.inventory = {}
                player.add_item(item_name, count, reason="org_task_reward")
                rewards['items'] = {item_name: count}
                
                if ft_manager:
                    ft_manager.add_text(f"+{count} {item_name}", 
                                       player.rect.centerx, player.rect.top - 70, 
                                       (150, 200, 255))
        
        # 检查晋升
        self.check_promotion(task.org_id, player, ft_manager)
        
        return rewards
    
    def _check_gather_progress(self, task: OrgTask, player, all_cards: list) -> int:
        """检查采集类任务进度"""
        target = task.target
        count = 0
        
        # 特殊处理: 铜钱
        if target == '铜钱':
            return getattr(player, 'money', 0)
        
        # 检查玩家背包
        if hasattr(player, 'inventory'):
            count += player.inventory.get(target, 0)
        
        # 检查追随者背包
        for card in all_cards:
            if getattr(card, 'is_follower', False) and hasattr(card, 'inventory'):
                count += card.inventory.get(target, 0)
        
        return count
    
    def _check_kill_progress(self, task: OrgTask, player) -> int:
        """检查击杀类任务进度"""
        if not hasattr(player, 'kill_counts'):
            return 0
        return player.kill_counts.get(task.target, 0)
    
    def _check_patrol_progress(self, task: OrgTask, player, all_cards: list) -> int:
        """检查巡逻类任务进度"""
        # 简化实现：检查玩家是否在目标区域附近停留
        # 实际实现需要更复杂的区域检测
        # 这里暂时返回0，后续可以扩展
        return 0


# 单例获取函数
def get_org_task_system() -> OrgTaskSystem:
    return OrgTaskSystem.get_instance()
