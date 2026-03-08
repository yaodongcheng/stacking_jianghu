# --- src/story/story_directive_executor.py ---
"""
StoryDirective 指令执行器

统一解析和执行剧情指令，让AI生成的对话能够影响游戏世界。
"""

from typing import Dict, Any, Callable, Optional, List
import re


class StoryDirectiveExecutor:
    """剧情指令执行器"""
    
    def __init__(self):
        self._ctx = None
        self._handlers: Dict[str, Callable] = {}
        self._register_handlers()
    
    def bind_context(self, ctx):
        """绑定游戏上下文"""
        self._ctx = ctx
    
    def _register_handlers(self):
        """注册所有指令处理器"""
        # NPC属性 - 基础
        self._handlers['SET_AFFINITY'] = self._handle_set_affinity
        self._handlers['SET_HP'] = self._handle_set_hp
        self._handlers['SET_HUNGER'] = self._handle_set_hunger
        self._handlers['SET_MONEY'] = self._handle_set_money
        self._handlers['SET_EMOTION'] = self._handle_set_emotion
        
        # NPC属性 - 组织与势力 (NEW)
        self._handlers['SET_ORG'] = self._handle_set_org           # 加入/离开组织
        self._handlers['SET_ORG_RANK'] = self._handle_set_org_rank # 组织内升降级
        self._handlers['SET_ORG_ROLE'] = self._handle_set_org_role # 组织角色变更
        self._handlers['SET_JOB'] = self._handle_set_job           # 转换职业
        self._handlers['SET_POWER_TYPE'] = self._handle_set_power_type  # 势力阵营变更
        
        # NPC属性 - 社会地位 (NEW)
        self._handlers['SET_SOCIAL_LEVEL'] = self._handle_set_social_level
        self._handlers['SET_WEALTH_LEVEL'] = self._handle_set_wealth_level
        self._handlers['SET_INFLUENCE'] = self._handle_set_influence_level
        self._handlers['SET_FREEDOM'] = self._handle_set_freedom
        
        # NPC属性 - 标签与身份 (NEW)
        self._handlers['ADD_TAG'] = self._handle_add_tag           # 添加标签
        self._handlers['REMOVE_TAG'] = self._handle_remove_tag     # 移除标签
        self._handlers['SET_REFUGEE'] = self._handle_set_refugee   # 流民状态
        self._handlers['SET_FOLLOWER'] = self._handle_set_follower # 门客状态
        
        # NPC属性 - 关系网络 (NEW)
        self._handlers['SET_HATRED'] = self._handle_set_hatred     # 仇恨值
        self._handlers['SET_KNOWS_PLAYER'] = self._handle_set_knows_player
        
        # NPC属性 - 人际与家庭关系 (NEW)
        self._handlers['SET_SPOUSE'] = self._handle_set_spouse       # 设置配偶
        self._handlers['SET_MASTER'] = self._handle_set_master       # 师徒关系
        self._handlers['SET_BOSS'] = self._handle_set_boss           # 上下级关系
        self._handlers['SET_ALLY'] = self._handle_set_ally           # 盟友关系
        self._handlers['SET_ENEMY'] = self._handle_set_enemy         # 敌人关系
        
        # NPC属性 - 技能与能力 (NEW)
        self._handlers['LEARN_SKILL'] = self._handle_learn_skill     # 学习技能
        self._handlers['FORGET_SKILL'] = self._handle_forget_skill   # 遗忘技能
        self._handlers['SET_COMBAT_STYLE'] = self._handle_set_combat_style  # 战斗风格
        self._handlers['BOOST_STAT'] = self._handle_boost_stat       # 属性提升
        
        # NPC属性 - 物品与装备 (NEW)
        self._handlers['GIVE_ITEM'] = self._handle_give_item         # 给予物品
        self._handlers['TAKE_ITEM'] = self._handle_take_item         # 收走物品
        self._handlers['EQUIP_WEAPON'] = self._handle_equip_weapon   # 装备武器
        
        # NPC行为
        self._handlers['NPC_MOVE'] = self._handle_npc_move
        self._handlers['NPC_FOLLOW'] = self._handle_npc_follow
        self._handlers['NPC_ATTACK'] = self._handle_npc_attack
        self._handlers['NPC_FLEE'] = self._handle_npc_flee
        self._handlers['NPC_SAY'] = self._handle_npc_say
        
        # 世界状态
        self._handlers['SPAWN_NPC'] = self._handle_spawn_npc
        self._handlers['DESPAWN_NPC'] = self._handle_despawn_npc
        self._handlers['ADVANCE_TIME'] = self._handle_advance_time
        
        # 演出效果
        self._handlers['FADE_TO_BLACK'] = self._handle_fade_to_black
        self._handlers['FADE_FROM_BLACK'] = self._handle_fade_from_black
        self._handlers['FLASH_WHITE'] = self._handle_flash_white
        self._handlers['SHAKE_CAMERA'] = self._handle_shake_camera
        
        # 玩家
        self._handlers['PLAYER_HP'] = self._handle_player_hp
        self._handlers['PLAYER_MONEY'] = self._handle_player_money
        self._handlers['PLAYER_FAME'] = self._handle_player_fame
        self._handlers['PLAYER_KNOCKOUT'] = self._handle_player_knockout
        
        # 关系
        self._handlers['SET_RELATION'] = self._handle_set_relation
    
    # ═══════════════════════════════════════════════════════════════════
    # 公共API
    # ═══════════════════════════════════════════════════════════════════
    
    def execute(self, directive_str: str) -> bool:
        """
        执行单条或多条指令
        
        Args:
            directive_str: 指令字符串，多条用分号分隔
                例: "SET_AFFINITY:8001:+20;SHAKE_CAMERA:5"
        
        Returns:
            bool: 是否全部执行成功
        """
        if not directive_str or not self._ctx:
            return False
        
        directives = directive_str.split(';')
        all_success = True
        
        for d in directives:
            d = d.strip()
            if not d:
                continue
            if not self._execute_single(d):
                all_success = False
        
        return all_success
    
    def _execute_single(self, directive: str) -> bool:
        """执行单条指令"""
        parts = directive.split(':')
        cmd = parts[0].upper()
        args = parts[1:] if len(parts) > 1 else []
        
        handler = self._handlers.get(cmd)
        if handler:
            try:
                handler(*args)
                print(f"[StoryDirective] [ok] {cmd} {args}")
                return True
            except Exception as e:
                print(f"[StoryDirective] [!] {cmd} 执行失败: {e}")
                return False
        else:
            print(f"[StoryDirective] [!] 未知指令: {cmd}")
            return False
    
    def _find_npc(self, npc_id_or_name: str):
        """通过ID或名称查找NPC（支持 PLAYER 标识符）"""
        if not self._ctx:
            return None
        
        # 特殊处理：PLAYER 标识符返回玩家
        if npc_id_or_name.upper() == 'PLAYER':
            return getattr(self._ctx, 'player', None)
        
        if not hasattr(self._ctx, 'all_cards'):
            return None
        
        # 尝试按ID查找
        try:
            npc_id = int(npc_id_or_name)
            for card in self._ctx.all_cards:
                if getattr(card, 'id', None) == npc_id:
                    return card
        except ValueError:
            pass
        
        # 按名称查找
        for card in self._ctx.all_cards:
            if getattr(card, 'name', None) == npc_id_or_name:
                return card
        
        return None
    
    # ═══════════════════════════════════════════════════════════════════
    # NPC属性指令
    # ═══════════════════════════════════════════════════════════════════
    
    def _handle_set_affinity(self, npc_id: str, delta: str):
        """SET_AFFINITY:{npc_id}:{delta} - 修改NPC对玩家好感度"""
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        delta_val = int(delta)
        current = getattr(npc, 'affinity_to_player', 0)
        npc.affinity_to_player = max(-100, min(100, current + delta_val))
        
        # 浮动文字反馈
        if hasattr(self._ctx, 'ft_manager'):
            color = (255, 200, 100) if delta_val > 0 else (200, 100, 100)
            self._ctx.ft_manager.add_text(
                f"好感{delta_val:+d}", 
                npc.rect.centerx, npc.rect.top - 30, color
            )
    
    def _handle_set_hp(self, npc_id: str, value: str):
        """SET_HP:{npc_id}:{value} - 设置NPC生命值"""
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        val = int(value)
        max_hp = getattr(npc, 'max_hp', 100)
        npc.hp = max(0, min(max_hp, val))
    
    def _handle_set_hunger(self, npc_id: str, value: str):
        """SET_HUNGER:{npc_id}:{value} - 设置饥饿值"""
        npc = self._find_npc(npc_id)
        if not npc:
            return
        npc.hunger = max(0, min(100, int(value)))
    
    def _handle_set_money(self, npc_id: str, delta: str):
        """SET_MONEY:{npc_id}:{delta} - 修改金钱"""
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        delta_val = int(delta)
        npc.money = max(0, getattr(npc, 'money', 0) + delta_val)
        
        if hasattr(self._ctx, 'ft_manager'):
            color = (255, 215, 0) if delta_val > 0 else (200, 100, 100)
            self._ctx.ft_manager.add_text(
                f"{delta_val:+d}铜", 
                npc.rect.centerx, npc.rect.top - 30, color
            )
    
    def _handle_set_emotion(self, npc_id: str, emotion: str):
        """SET_EMOTION:{npc_id}:{emotion} - 设置表情"""
        npc = self._find_npc(npc_id)
        if not npc:
            return
        npc.emotion = emotion.upper()
    
    # ═══════════════════════════════════════════════════════════════════
    # NPC行为指令
    # ═══════════════════════════════════════════════════════════════════
    
    def _handle_npc_move(self, npc_id: str, x: str, y: str):
        """NPC_MOVE:{npc_id}:{x}:{y} - 移动NPC"""
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        from src.atomic_actions import MoveToPosition
        if hasattr(npc, 'action_queue'):
            npc.action_queue.clear()
            npc.action_queue.enqueue(MoveToPosition(int(x), int(y), reason="剧情移动"))
    
    def _handle_npc_follow(self, npc_id: str, target_id: str):
        """NPC_FOLLOW:{npc_id}:{target_id} - 跟随目标"""
        npc = self._find_npc(npc_id)
        target = self._find_npc(target_id)
        if not npc or not target:
            return
        
        from src.atomic_actions import FollowTarget
        if hasattr(npc, 'action_queue'):
            npc.action_queue.clear()
            npc.action_queue.enqueue(FollowTarget(target, reason="剧情跟随"))
    
    def _handle_npc_attack(self, npc_id: str, target_id: str):
        """NPC_ATTACK:{npc_id}:{target_id} - 攻击目标"""
        npc = self._find_npc(npc_id)
        target = self._find_npc(target_id)
        if not npc or not target:
            return
        
        from src.atomic_actions import Combat
        if hasattr(npc, 'action_queue') and hasattr(self._ctx, 'combat_manager'):
            npc.action_queue.clear()
            npc.action_queue.enqueue(
                Combat(target, self._ctx.combat_manager, reason="剧情战斗")
            )
    
    def _handle_npc_flee(self, npc_id: str, distance: str = '300'):
        """NPC_FLEE:{npc_id}:{distance} - NPC逃跑"""
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        import random
        import math
        
        # 随机方向逃跑
        angle = random.uniform(0, 2 * math.pi)
        dist = int(distance)
        tx = npc.rect.centerx + math.cos(angle) * dist
        ty = npc.rect.centery + math.sin(angle) * dist
        
        from src.atomic_actions import MoveToPosition
        if hasattr(npc, 'action_queue'):
            npc.action_queue.clear()
            npc.action_queue.enqueue(MoveToPosition(tx, ty, reason="逃跑"))
    
    def _handle_npc_say(self, npc_id: str, *text_parts):
        """NPC_SAY:{npc_id}:{text} - NPC说话气泡"""
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        text = ':'.join(text_parts)  # 重新组合包含冒号的文本
        npc.ai_reason = text
        npc._salute_bubble = text
        npc._salute_bubble_timer = 3000
    
    # ═══════════════════════════════════════════════════════════════════
    # 世界状态指令
    # ═══════════════════════════════════════════════════════════════════
    
    def _handle_spawn_npc(self, template: str, x: str, y: str):
        """SPAWN_NPC:{template}:{x}:{y} - 生成NPC"""
        # 需要与CardManager协作
        if hasattr(self._ctx, 'spawn_npc'):
            self._ctx.spawn_npc(template, int(x), int(y))
    
    def _handle_despawn_npc(self, npc_id: str):
        """DESPAWN_NPC:{npc_id} - 移除NPC"""
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        from src.definitions import SAFETY_EXILED
        npc.safety = SAFETY_EXILED
    
    def _handle_advance_time(self, hours: str = '1'):
        """ADVANCE_TIME:{hours} - 时间推进"""
        if hasattr(self._ctx, 'time_manager'):
            self._ctx.time_manager.advance_time(int(hours) * 60)  # 转换为分钟
    
    # ═══════════════════════════════════════════════════════════════════
    # 演出效果指令
    # ═══════════════════════════════════════════════════════════════════
    
    def _handle_fade_to_black(self, duration_ms: str = '500'):
        """FADE_TO_BLACK:{ms} - 黑屏渐入"""
        if hasattr(self._ctx, 'screen_effects'):
            self._ctx.screen_effects.fade_to_black(int(duration_ms))
    
    def _handle_fade_from_black(self, duration_ms: str = '500'):
        """FADE_FROM_BLACK:{ms} - 黑屏渐出"""
        if hasattr(self._ctx, 'screen_effects'):
            self._ctx.screen_effects.fade_from_black(int(duration_ms))
    
    def _handle_flash_white(self, duration_ms: str = '100'):
        """FLASH_WHITE:{ms} - 白屏闪烁"""
        if hasattr(self._ctx, 'screen_effects'):
            self._ctx.screen_effects.flash_white(int(duration_ms))
    
    def _handle_shake_camera(self, intensity: str = '5'):
        """SHAKE_CAMERA:{intensity} - 镜头震动"""
        if hasattr(self._ctx, 'camera'):
            self._ctx.camera.shake(int(intensity))
    
    # ═══════════════════════════════════════════════════════════════════
    # 玩家指令
    # ═══════════════════════════════════════════════════════════════════
    
    def _handle_player_hp(self, delta: str):
        """PLAYER_HP:{delta} - 玩家生命变化"""
        if not hasattr(self._ctx, 'player'):
            return
        
        player = self._ctx.player
        delta_val = int(delta)
        player.hp = max(0, min(player.max_hp, player.hp + delta_val))
        
        if delta_val < 0 and hasattr(self._ctx, 'screen_effects'):
            self._ctx.screen_effects.flash_red(100)
    
    def _handle_player_money(self, delta: str):
        """PLAYER_MONEY:{delta} - 玩家金钱变化"""
        if not hasattr(self._ctx, 'player'):
            return
        
        player = self._ctx.player
        delta_val = int(delta)
        player.money = max(0, player.money + delta_val)
        
        if hasattr(self._ctx, 'ft_manager'):
            color = (255, 215, 0) if delta_val > 0 else (200, 100, 100)
            self._ctx.ft_manager.add_text(
                f"{delta_val:+d}铜", 
                player.rect.centerx, player.rect.top - 30, color
            )
    
    def _handle_player_fame(self, delta: str):
        """PLAYER_FAME:{delta} - 玩家声望变化"""
        if not hasattr(self._ctx, 'player'):
            return
        
        player = self._ctx.player
        delta_val = int(delta)
        player.fame = max(0, getattr(player, 'fame', 0) + delta_val)
        
        if hasattr(self._ctx, 'ft_manager'):
            self._ctx.ft_manager.add_text(
                f"声望{delta_val:+d}", 
                player.rect.centerx, player.rect.top - 50, (180, 150, 255)
            )
    
    def _handle_player_knockout(self):
        """PLAYER_KNOCKOUT - 玩家昏倒"""
        if not hasattr(self._ctx, 'player'):
            return
        
        from src.definitions import SAFETY_DOWNED
        self._ctx.player.safety = SAFETY_DOWNED
        self._ctx.player.hp = 0
        
        if hasattr(self._ctx, 'screen_effects'):
            self._ctx.screen_effects.fade_to_black(500)
    
    # ═══════════════════════════════════════════════════════════════════
    # 关系指令
    # ═══════════════════════════════════════════════════════════════════
    
    def _handle_set_relation(self, npc_a_id: str, npc_b_id: str, delta: str):
        """SET_RELATION:{a_id}:{b_id}:{delta} - 修改好感度（支持玩家）"""
        npc_a = self._find_npc(npc_a_id)
        npc_b = self._find_npc(npc_b_id)
        if not npc_a or not npc_b:
            return
        
        delta_val = int(delta)
        
        # 尝试使用社交系统（玩家与NPC的关系通常存储在这里）
        is_player_involved = (npc_a_id.upper() == 'PLAYER' or npc_b_id.upper() == 'PLAYER')
        if is_player_involved:
            try:
                from src.social_system import social_manager
                if social_manager:
                    old_affinity = social_manager.get_affinity(npc_a.id, npc_b.id)
                    social_manager.modify_affinity(npc_a.id, npc_b.id, delta_val)
                    new_affinity = social_manager.get_affinity(npc_a.id, npc_b.id)
                    print(f"[SET_RELATION] {npc_a.name} → {npc_b.name}: {old_affinity} → {new_affinity} (Δ{delta_val:+d})")
                    
                    # 浮动文字反馈（在 NPC 头上显示）
                    target_npc = npc_b if npc_a_id.upper() == 'PLAYER' else npc_a
                    if hasattr(self._ctx, 'ft_manager') and hasattr(target_npc, 'rect'):
                        color = (255, 200, 100) if delta_val > 0 else (200, 100, 100)
                        self._ctx.ft_manager.add_text(
                            f"好感{delta_val:+d}", 
                            target_npc.rect.centerx, target_npc.rect.top - 30, color
                        )
                    return
            except ImportError:
                pass
        
        # 回退：使用NPC的affinity字典
        if hasattr(npc_a, 'modify_affinity'):
            npc_a.modify_affinity(npc_b.id, delta_val)
        elif hasattr(npc_a, 'affinity'):
            if not isinstance(npc_a.affinity, dict):
                npc_a.affinity = {}
            current = npc_a.affinity.get(npc_b.id, 0)
            npc_a.affinity[npc_b.id] = max(-100, min(100, current + delta_val))
    
    # ═══════════════════════════════════════════════════════════════════
    # 组织与势力指令 (NEW - 人生转折类)
    # ═══════════════════════════════════════════════════════════════════
    
    # 组织ID映射
    VALID_ORGS = {
        'kaifeng_fu': '开封府',
        'shenhou_fu': '神侯府',
        'gao_manor': '高府',
        'tianshui_alley': '天水商会',
        'taixue': '太学',
        'daxiangguo': '大相国寺',
        'beggar_gang': '丐帮',
        'shizizhipo': '十字坡',
        'heifeng_zhai': '黑风寨',
        'qinglang_bang': '青狼帮',
        'luopo_gang': '骆驼帮',
        'NONE': '无组织'
    }
    
    def _handle_set_org(self, npc_id: str, org_id: str):
        """
        SET_ORG:{npc_id}:{org_id} - NPC加入/离开组织
        
        用法:
        - SET_ORG:8001:beggar_gang  → 加入丐帮
        - SET_ORG:8001:NONE         → 离开当前组织
        
        效果：自动刷新组织成员缓存，并发送世界消息
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        old_org = getattr(npc, 'org_id', 'NONE')
        new_org = org_id.lower() if org_id != 'NONE' else 'NONE'
        
        # 验证组织ID
        if new_org not in self.VALID_ORGS and new_org != 'NONE':
            print(f"[StoryDirective] 无效组织ID: {new_org}")
            return
        
        npc.org_id = new_org
        
        # 如果离开组织，重置组织等级
        if new_org == 'NONE':
            npc.org_rank = 0
            npc.org_role = None
        else:
            # 新加入组织，初始为普通成员
            if not getattr(npc, 'org_rank', 0):
                npc.org_rank = 1
            npc.org_role = 'MEMBER'
        
        # 浮动文字反馈
        if hasattr(self._ctx, 'ft_manager'):
            if new_org == 'NONE':
                msg = f"离开{self.VALID_ORGS.get(old_org, old_org)}"
                color = (200, 100, 100)
            else:
                msg = f"加入{self.VALID_ORGS.get(new_org, new_org)}"
                color = (100, 200, 255)
            self._ctx.ft_manager.add_text(
                msg, npc.rect.centerx, npc.rect.top - 30, color
            )
        
        # 刷新组织系统缓存
        if hasattr(self._ctx, 'org_system'):
            self._ctx.org_system._rebuild_member_cache()
        
        from src.utils import log_game_event
        log_game_event(
            f"[人生转折] {npc.name} {msg}", 
            tag="LIFE_EVENT"
        )
    
    def _handle_set_org_rank(self, npc_id: str, rank: str):
        """
        SET_ORG_RANK:{npc_id}:{rank} - 组织内升降级
        
        用法:
        - SET_ORG_RANK:8001:3   → 晋升为头目(rank 3)
        - SET_ORG_RANK:8001:+1  → 升一级
        - SET_ORG_RANK:8001:-1  → 降一级
        
        等级说明: 0=无 1=门徒 2=核心 3=头目 4=长老 5=首领
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        current_rank = getattr(npc, 'org_rank', 0)
        
        # 支持相对值
        if rank.startswith('+') or rank.startswith('-'):
            new_rank = current_rank + int(rank)
        else:
            new_rank = int(rank)
        
        new_rank = max(0, min(5, new_rank))
        old_rank = current_rank
        npc.org_rank = new_rank
        
        # 等级名称
        rank_names = {0: '无', 1: '门徒', 2: '核心', 3: '头目', 4: '长老', 5: '首领'}
        
        if hasattr(self._ctx, 'ft_manager'):
            if new_rank > old_rank:
                msg = f"晋升为{rank_names.get(new_rank, str(new_rank))}"
                color = (255, 215, 0)
            else:
                msg = f"降为{rank_names.get(new_rank, str(new_rank))}"
                color = (200, 100, 100)
            self._ctx.ft_manager.add_text(
                msg, npc.rect.centerx, npc.rect.top - 30, color
            )
        
        from src.utils import log_game_event
        log_game_event(
            f"[人生转折] {npc.name} 在组织内{msg}", 
            tag="LIFE_EVENT"
        )
    
    def _handle_set_org_role(self, npc_id: str, role: str):
        """
        SET_ORG_ROLE:{npc_id}:{role} - 组织角色变更
        
        用法:
        - SET_ORG_ROLE:8001:LEADER     → 成为首领
        - SET_ORG_ROLE:8001:BODYGUARD  → 成为护卫
        - SET_ORG_ROLE:8001:MEMBER     → 普通成员
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        valid_roles = ['LEADER', 'MEMBER', 'BODYGUARD', 'ELDER', 'ADVISOR']
        role_upper = role.upper()
        
        if role_upper not in valid_roles:
            print(f"[StoryDirective] 无效组织角色: {role}")
            return
        
        old_role = getattr(npc, 'org_role', 'MEMBER')
        npc.org_role = role_upper
        
        # 如果成为首领，自动设置最高等级
        if role_upper == 'LEADER':
            npc.org_rank = 5
        
        role_names = {
            'LEADER': '首领', 'MEMBER': '成员', 'BODYGUARD': '护卫',
            'ELDER': '长老', 'ADVISOR': '军师'
        }
        
        if hasattr(self._ctx, 'ft_manager'):
            msg = f"成为{role_names.get(role_upper, role_upper)}"
            color = (255, 200, 100)
            self._ctx.ft_manager.add_text(
                msg, npc.rect.centerx, npc.rect.top - 30, color
            )
    
    def _handle_set_job(self, npc_id: str, job: str):
        """
        SET_JOB:{npc_id}:{job} - 转换职业
        
        用法:
        - SET_JOB:8001:MERCHANT  → 转职为商人
        - SET_JOB:8001:BANDIT    → 落草为寇
        - SET_JOB:8001:GUARD     → 成为护卫
        
        合法职业: FARMER, MERCHANT, ARTISAN, OFFICIAL, SCHOLAR, GUARD, 
                 SOLDIER, BANDIT, THUG, BEGGAR, MONK, NONE
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        valid_jobs = [
            'FARMER', 'MERCHANT', 'ARTISAN', 'OFFICIAL', 'SCHOLAR',
            'GUARD', 'SOLDIER', 'BANDIT', 'THUG', 'BEGGAR', 'MONK',
            'SERVANT', 'WORKER', 'NONE'
        ]
        job_upper = job.upper()
        
        if job_upper not in valid_jobs:
            print(f"[StoryDirective] 无效职业: {job}")
            return
        
        old_job = getattr(npc, 'job', 'NONE')
        npc.job = job_upper
        
        job_names = {
            'FARMER': '农夫', 'MERCHANT': '商人', 'ARTISAN': '工匠',
            'OFFICIAL': '官员', 'SCHOLAR': '学者', 'GUARD': '护卫',
            'SOLDIER': '士兵', 'BANDIT': '山贼', 'THUG': '泼皮',
            'BEGGAR': '乞丐', 'MONK': '僧人', 'SERVANT': '仆从',
            'WORKER': '劳工', 'NONE': '无业'
        }
        
        if hasattr(self._ctx, 'ft_manager'):
            msg = f"转职为{job_names.get(job_upper, job_upper)}"
            self._ctx.ft_manager.add_text(
                msg, npc.rect.centerx, npc.rect.top - 30, (100, 200, 255)
            )
        
        from src.utils import log_game_event
        log_game_event(
            f"[人生转折] {npc.name} 从{job_names.get(old_job, old_job)}转为{job_names.get(job_upper, job_upper)}", 
            tag="LIFE_EVENT"
        )
    
    def _handle_set_power_type(self, npc_id: str, power_type: str):
        """
        SET_POWER_TYPE:{npc_id}:{type} - 势力阵营变更
        
        用法:
        - SET_POWER_TYPE:8001:匪  → 变成匪类（立场大转变）
        - SET_POWER_TYPE:8001:兵  → 从军
        
        合法类型: 士/农/工/商/学/兵/游/匪/民
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        valid_types = ['士', '农', '工', '商', '学', '兵', '游', '匪', '民']
        
        if power_type not in valid_types:
            print(f"[StoryDirective] 无效势力类型: {power_type}")
            return
        
        old_type = getattr(npc, 'power_type', '民')
        npc.power_type = power_type
        
        type_names = {
            '士': '官场', '农': '农户', '工': '工匠', '商': '商贾',
            '学': '学林', '兵': '军伍', '游': '江湖', '匪': '绿林', '民': '平民'
        }
        
        if hasattr(self._ctx, 'ft_manager'):
            msg = f"投身{type_names.get(power_type, power_type)}"
            self._ctx.ft_manager.add_text(
                msg, npc.rect.centerx, npc.rect.top - 30, (200, 150, 255)
            )
        
        from src.utils import log_game_event
        log_game_event(
            f"[人生转折] {npc.name} 从{type_names.get(old_type, old_type)}投身{type_names.get(power_type, power_type)}", 
            tag="LIFE_EVENT"
        )
    
    # ═══════════════════════════════════════════════════════════════════
    # 社会地位指令 (NEW)
    # ═══════════════════════════════════════════════════════════════════
    
    def _handle_set_social_level(self, npc_id: str, level: str):
        """
        SET_SOCIAL_LEVEL:{npc_id}:{level} - 社会等级变化
        
        用法:
        - SET_SOCIAL_LEVEL:8001:4  → 设置为高等级(4)
        - SET_SOCIAL_LEVEL:8001:+1 → 提升一级
        
        等级说明: 1=贱民 2=平民 3=中产 4=富裕 5=权贵
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        current = getattr(npc, 'social_level', 1)
        
        if level.startswith('+') or level.startswith('-'):
            new_level = current + int(level)
        else:
            new_level = int(level)
        
        new_level = max(1, min(5, new_level))
        npc.social_level = new_level
        
        level_names = {1: '贱民', 2: '平民', 3: '中产', 4: '富裕', 5: '权贵'}
        
        if hasattr(self._ctx, 'ft_manager') and new_level != current:
            direction = "↑" if new_level > current else "↓"
            msg = f"社会地位{direction}{level_names.get(new_level, str(new_level))}"
            color = (255, 215, 0) if new_level > current else (150, 150, 150)
            self._ctx.ft_manager.add_text(
                msg, npc.rect.centerx, npc.rect.top - 30, color
            )
    
    def _handle_set_wealth_level(self, npc_id: str, level: str):
        """
        SET_WEALTH_LEVEL:{npc_id}:{level} - 财富等级变化
        
        用法同 SET_SOCIAL_LEVEL
        等级说明: 1=赤贫 2=贫困 3=温饱 4=小康 5=富豪
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        current = getattr(npc, 'wealth_level', 1)
        
        if level.startswith('+') or level.startswith('-'):
            new_level = current + int(level)
        else:
            new_level = int(level)
        
        new_level = max(1, min(5, new_level))
        npc.wealth_level = new_level
        
        level_names = {1: '赤贫', 2: '贫困', 3: '温饱', 4: '小康', 5: '富豪'}
        
        if hasattr(self._ctx, 'ft_manager') and new_level != current:
            direction = "↑" if new_level > current else "↓"
            msg = f"财富{direction}{level_names.get(new_level, str(new_level))}"
            color = (255, 215, 0) if new_level > current else (150, 100, 100)
            self._ctx.ft_manager.add_text(
                msg, npc.rect.centerx, npc.rect.top - 30, color
            )
    
    def _handle_set_influence_level(self, npc_id: str, level: str):
        """
        SET_INFLUENCE:{npc_id}:{level} - 影响力等级变化
        
        等级说明: 1=无名 2=小有名气 3=知名 4=显赫 5=权倾一方
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        current = getattr(npc, 'influence_level', 1)
        
        if level.startswith('+') or level.startswith('-'):
            new_level = current + int(level)
        else:
            new_level = int(level)
        
        new_level = max(1, min(5, new_level))
        npc.influence_level = new_level
        
        level_names = {1: '无名', 2: '小有名气', 3: '知名', 4: '显赫', 5: '权倾一方'}
        
        if hasattr(self._ctx, 'ft_manager') and new_level != current:
            direction = "↑" if new_level > current else "↓"
            msg = f"声望{direction}{level_names.get(new_level, str(new_level))}"
            color = (180, 150, 255) if new_level > current else (150, 150, 150)
            self._ctx.ft_manager.add_text(
                msg, npc.rect.centerx, npc.rect.top - 30, color
            )
    
    def _handle_set_freedom(self, npc_id: str, freedom: str):
        """
        SET_FREEDOM:{npc_id}:{freedom} - 自由度变化
        
        用法:
        - SET_FREEDOM:8001:FREE_FULL   → 完全自由
        - SET_FREEDOM:8001:FREE_HALF   → 半自由(如佃农)
        - SET_FREEDOM:8001:FREE_NONE   → 无自由(如奴仆)
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        from src.definitions import FREE_FULL, FREE_HALF, FREE_NONE
        
        freedom_map = {
            'FREE_FULL': FREE_FULL,
            'FREE_HALF': FREE_HALF, 
            'FREE_NONE': FREE_NONE
        }
        
        if freedom.upper() not in freedom_map:
            print(f"[StoryDirective] 无效自由度: {freedom}")
            return
        
        npc.freedom = freedom_map[freedom.upper()]
        
        freedom_names = {
            'FREE_FULL': '自由身', 
            'FREE_HALF': '半自由',
            'FREE_NONE': '奴籍'
        }
        
        if hasattr(self._ctx, 'ft_manager'):
            msg = freedom_names.get(freedom.upper(), freedom)
            color = (100, 200, 100) if freedom.upper() == 'FREE_FULL' else (200, 150, 100)
            self._ctx.ft_manager.add_text(
                msg, npc.rect.centerx, npc.rect.top - 30, color
            )
    
    # ═══════════════════════════════════════════════════════════════════
    # 标签与身份指令 (NEW)
    # ═══════════════════════════════════════════════════════════════════
    
    def _handle_add_tag(self, npc_id: str, tag: str):
        """
        ADD_TAG:{npc_id}:{tag} - 添加NPC标签
        
        用法:
        - ADD_TAG:8001:CRIMINAL   → 标记为罪犯
        - ADD_TAG:8001:HERO       → 标记为英雄
        - ADD_TAG:8001:OUTLAW     → 标记为法外之徒
        - ADD_TAG:8001:WANTED     → 被通缉
        - ADD_TAG:8001:VETERAN    → 老兵
        - ADD_TAG:8001:INJURED    → 受伤
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        tag_upper = tag.upper()
        
        if not hasattr(npc, 'tags'):
            npc.tags = []
        
        if tag_upper not in npc.tags:
            npc.tags.append(tag_upper)
            
            if hasattr(self._ctx, 'ft_manager'):
                tag_names = {
                    'CRIMINAL': '罪犯', 'HERO': '英雄', 'OUTLAW': '法外之徒',
                    'WANTED': '通缉犯', 'VETERAN': '老兵', 'INJURED': '受伤',
                    'CORRUPT': '贪官', 'RIGHTEOUS': '正义', 'VILLAIN': '恶人'
                }
                msg = f"+{tag_names.get(tag_upper, tag_upper)}"
                self._ctx.ft_manager.add_text(
                    msg, npc.rect.centerx, npc.rect.top - 30, (255, 200, 100)
                )
    
    def _handle_remove_tag(self, npc_id: str, tag: str):
        """
        REMOVE_TAG:{npc_id}:{tag} - 移除NPC标签
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        tag_upper = tag.upper()
        
        if hasattr(npc, 'tags') and tag_upper in npc.tags:
            npc.tags.remove(tag_upper)
    
    def _handle_set_refugee(self, npc_id: str, value: str):
        """
        SET_REFUGEE:{npc_id}:{0|1} - 设置流民状态
        
        用法:
        - SET_REFUGEE:8001:1  → 变成流民
        - SET_REFUGEE:8001:0  → 不再是流民
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        npc.is_refugee = (value == '1' or value.lower() == 'true')
        
        if hasattr(self._ctx, 'ft_manager'):
            if npc.is_refugee:
                msg = "沦为流民"
                color = (200, 150, 100)
            else:
                msg = "安定下来"
                color = (100, 200, 100)
            self._ctx.ft_manager.add_text(
                msg, npc.rect.centerx, npc.rect.top - 30, color
            )
    
    def _handle_set_follower(self, npc_id: str, value: str):
        """
        SET_FOLLOWER:{npc_id}:{0|1} - 设置门客状态
        
        用法:
        - SET_FOLLOWER:8001:1  → 成为玩家门客
        - SET_FOLLOWER:8001:0  → 不再是门客
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        npc.is_follower = (value == '1' or value.lower() == 'true')
        
        if hasattr(self._ctx, 'ft_manager'):
            if npc.is_follower:
                msg = "成为门客"
                color = (100, 255, 200)
            else:
                msg = "离开门下"
                color = (200, 150, 100)
            self._ctx.ft_manager.add_text(
                msg, npc.rect.centerx, npc.rect.top - 30, color
            )
    
    def _handle_set_hatred(self, npc_id: str, target_id: str, value: str):
        """
        SET_HATRED:{npc_id}:{target_id}:{value} - 设置仇恨值
        
        用法:
        - SET_HATRED:8001:8002:+50  → 增加仇恨
        - SET_HATRED:8001:8002:0    → 清除仇恨
        """
        npc = self._find_npc(npc_id)
        target = self._find_npc(target_id)
        if not npc or not target:
            return
        
        if not hasattr(npc, 'hatred'):
            npc.hatred = {}
        
        if value.startswith('+') or value.startswith('-'):
            current = npc.hatred.get(target.id, 0)
            new_val = current + int(value)
        else:
            new_val = int(value)
        
        npc.hatred[target.id] = max(0, new_val)
        
        # 如果仇恨超过阈值，可能触发战斗
        if new_val > getattr(npc, 'aggro_threshold', 30):
            npc.aggro_target = target
    
    def _handle_set_knows_player(self, npc_id: str, value: str):
        """
        SET_KNOWS_PLAYER:{npc_id}:{0|1} - 设置是否认识玩家
        
        用法:
        - SET_KNOWS_PLAYER:8001:1  → 现在认识玩家了
        - SET_KNOWS_PLAYER:8001:0  → 忘记玩家
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        npc.knows_player = (value == '1' or value.lower() == 'true')

    # ═══════════════════════════════════════════════════════════════════
    # 人际与家庭关系指令 (NEW)
    # ═══════════════════════════════════════════════════════════════════
    
    def _handle_set_spouse(self, npc_id: str, spouse_id: str):
        """
        SET_SPOUSE:{npc_id}:{spouse_id} - 设置配偶关系
        
        用法:
        - SET_SPOUSE:8001:8002    → 两人结为夫妻
        - SET_SPOUSE:8001:NONE    → 解除婚姻
        
        效果：双向设置，同时更新双方的 spouse_id 属性
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        # 解除婚姻
        if spouse_id.upper() == 'NONE':
            old_spouse_id = getattr(npc, 'spouse_id', None)
            npc.spouse_id = None
            
            # 解除对方的婚姻关系
            if old_spouse_id:
                old_spouse = self._find_npc(str(old_spouse_id))
                if old_spouse:
                    old_spouse.spouse_id = None
            
            if hasattr(self._ctx, 'ft_manager'):
                self._ctx.ft_manager.add_text(
                    "休妻/和离", npc.rect.centerx, npc.rect.top - 30, (200, 150, 100)
                )
            return
        
        # 建立婚姻
        spouse = self._find_npc(spouse_id)
        if not spouse:
            return
        
        # 双向绑定
        npc.spouse_id = spouse.id
        spouse.spouse_id = npc.id
        
        if hasattr(self._ctx, 'ft_manager'):
            self._ctx.ft_manager.add_text(
                f"与{spouse.name}结为夫妻", npc.rect.centerx, npc.rect.top - 30, (255, 150, 200)
            )
        
        from src.utils import log_game_event
        log_game_event(
            f"[人生大事] {npc.name} 与 {spouse.name} 喜结连理", 
            tag="LIFE_EVENT"
        )
    
    def _handle_set_master(self, npc_id: str, master_id: str):
        """
        SET_MASTER:{npc_id}:{master_id} - 设置师徒关系
        
        用法:
        - SET_MASTER:8001:8002   → 8001拜8002为师
        - SET_MASTER:8001:NONE   → 脱离师门
        
        效果：设置 apprentice.master_id，并将 apprentice 加入 master.disciples
        """
        apprentice = self._find_npc(npc_id)
        if not apprentice:
            return
        
        # 脱离师门
        if master_id.upper() == 'NONE':
            old_master_id = getattr(apprentice, 'master_id', None)
            apprentice.master_id = None
            
            # 从原师父的弟子列表移除
            if old_master_id:
                old_master = self._find_npc(str(old_master_id))
                if old_master and hasattr(old_master, 'disciples'):
                    if apprentice.id in old_master.disciples:
                        old_master.disciples.remove(apprentice.id)
            
            if hasattr(self._ctx, 'ft_manager'):
                self._ctx.ft_manager.add_text(
                    "脱离师门", apprentice.rect.centerx, apprentice.rect.top - 30, (200, 150, 100)
                )
            return
        
        # 拜师
        master = self._find_npc(master_id)
        if not master:
            return
        
        apprentice.master_id = master.id
        
        if not hasattr(master, 'disciples'):
            master.disciples = []
        if apprentice.id not in master.disciples:
            master.disciples.append(apprentice.id)
        
        if hasattr(self._ctx, 'ft_manager'):
            self._ctx.ft_manager.add_text(
                f"拜{master.name}为师", apprentice.rect.centerx, apprentice.rect.top - 30, (200, 200, 255)
            )
        
        from src.utils import log_game_event
        log_game_event(
            f"[人生大事] {apprentice.name} 拜 {master.name} 为师", 
            tag="LIFE_EVENT"
        )
    
    def _handle_set_boss(self, npc_id: str, boss_id: str):
        """
        SET_BOSS:{npc_id}:{boss_id} - 设置上下级关系
        
        用法:
        - SET_BOSS:8001:8002   → 8001成为8002的下属
        - SET_BOSS:8001:NONE   → 脱离上下级关系
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        if boss_id.upper() == 'NONE':
            npc.boss_id = None
        else:
            boss = self._find_npc(boss_id)
            if boss:
                npc.boss_id = boss.id
                
                if hasattr(self._ctx, 'ft_manager'):
                    self._ctx.ft_manager.add_text(
                        f"效命于{boss.name}", npc.rect.centerx, npc.rect.top - 30, (150, 200, 255)
                    )
    
    def _handle_set_ally(self, npc_id: str, ally_id: str):
        """
        SET_ALLY:{npc_id}:{ally_id} - 建立盟友关系
        
        用法:
        - SET_ALLY:8001:8002   → 两人结为盟友
        """
        npc = self._find_npc(npc_id)
        ally = self._find_npc(ally_id)
        if not npc or not ally:
            return
        
        if not hasattr(npc, 'allies'):
            npc.allies = []
        if not hasattr(ally, 'allies'):
            ally.allies = []
        
        # 双向添加
        if ally.id not in npc.allies:
            npc.allies.append(ally.id)
        if npc.id not in ally.allies:
            ally.allies.append(npc.id)
        
        if hasattr(self._ctx, 'ft_manager'):
            self._ctx.ft_manager.add_text(
                f"与{ally.name}结盟", npc.rect.centerx, npc.rect.top - 30, (100, 200, 255)
            )
    
    def _handle_set_enemy(self, npc_id: str, enemy_id: str):
        """
        SET_ENEMY:{npc_id}:{enemy_id} - 建立仇敌关系
        
        用法:
        - SET_ENEMY:8001:8002   → 两人成为仇敌
        """
        npc = self._find_npc(npc_id)
        enemy = self._find_npc(enemy_id)
        if not npc or not enemy:
            return
        
        if not hasattr(npc, 'enemies'):
            npc.enemies = []
        if not hasattr(enemy, 'enemies'):
            enemy.enemies = []
        
        # 双向添加
        if enemy.id not in npc.enemies:
            npc.enemies.append(enemy.id)
        if npc.id not in enemy.enemies:
            enemy.enemies.append(npc.id)
        
        # 同时增加仇恨值
        if not hasattr(npc, 'hatred'):
            npc.hatred = {}
        npc.hatred[enemy.id] = 100
        
        if hasattr(self._ctx, 'ft_manager'):
            self._ctx.ft_manager.add_text(
                f"与{enemy.name}反目", npc.rect.centerx, npc.rect.top - 30, (255, 100, 100)
            )
        
        from src.utils import log_game_event
        log_game_event(
            f"[人生转折] {npc.name} 与 {enemy.name} 反目成仇", 
            tag="LIFE_EVENT"
        )
    
    # ═══════════════════════════════════════════════════════════════════
    # 技能与能力指令 (NEW)
    # ═══════════════════════════════════════════════════════════════════
    
    def _handle_learn_skill(self, npc_id: str, skill_id: str):
        """
        LEARN_SKILL:{npc_id}:{skill_id} - 学习技能
        
        用法:
        - LEARN_SKILL:8001:SWORD_BASIC    → 学会基础剑法
        - LEARN_SKILL:8001:COOKING        → 学会烹饪
        - LEARN_SKILL:8001:MEDICINE       → 学会医术
        
        常用技能ID: SWORD_BASIC, FIST_BASIC, BOW_BASIC, COOKING, MEDICINE,
                   STEALTH, PERSUASION, TRADE, FARMING, CRAFT
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        skill_upper = skill_id.upper()
        
        if not hasattr(npc, 'skills'):
            npc.skills = []
        
        if skill_upper not in npc.skills:
            npc.skills.append(skill_upper)
            
            skill_names = {
                'SWORD_BASIC': '基础剑法', 'FIST_BASIC': '拳脚功夫',
                'BOW_BASIC': '弓箭入门', 'COOKING': '烹饪',
                'MEDICINE': '医术', 'STEALTH': '潜行',
                'PERSUASION': '话术', 'TRADE': '商道',
                'FARMING': '农艺', 'CRAFT': '手艺',
                'HORSE_RIDING': '骑术', 'SWIMMING': '泳术',
                'POISON': '用毒', 'LOCK_PICK': '开锁'
            }
            
            if hasattr(self._ctx, 'ft_manager'):
                msg = f"习得{skill_names.get(skill_upper, skill_upper)}"
                self._ctx.ft_manager.add_text(
                    msg, npc.rect.centerx, npc.rect.top - 30, (150, 255, 200)
                )
    
    def _handle_forget_skill(self, npc_id: str, skill_id: str):
        """
        FORGET_SKILL:{npc_id}:{skill_id} - 遗忘技能
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        skill_upper = skill_id.upper()
        
        if hasattr(npc, 'skills') and skill_upper in npc.skills:
            npc.skills.remove(skill_upper)
    
    def _handle_set_combat_style(self, npc_id: str, style: str):
        """
        SET_COMBAT_STYLE:{npc_id}:{style} - 设置战斗风格
        
        用法:
        - SET_COMBAT_STYLE:8001:AGGRESSIVE  → 激进型
        - SET_COMBAT_STYLE:8001:DEFENSIVE   → 防御型
        - SET_COMBAT_STYLE:8001:CUNNING     → 狡诈型
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        valid_styles = ['AGGRESSIVE', 'DEFENSIVE', 'BALANCED', 'CUNNING', 'BERSERKER']
        style_upper = style.upper()
        
        if style_upper in valid_styles:
            npc.combat_style = style_upper
            
            style_names = {
                'AGGRESSIVE': '激进', 'DEFENSIVE': '稳健',
                'BALANCED': '均衡', 'CUNNING': '狡诈', 'BERSERKER': '狂暴'
            }
            
            if hasattr(self._ctx, 'ft_manager'):
                msg = f"战斗风格→{style_names.get(style_upper, style_upper)}"
                self._ctx.ft_manager.add_text(
                    msg, npc.rect.centerx, npc.rect.top - 30, (200, 150, 255)
                )
    
    def _handle_boost_stat(self, npc_id: str, stat: str, value: str):
        """
        BOOST_STAT:{npc_id}:{stat}:{value} - 提升基础属性
        
        用法:
        - BOOST_STAT:8001:ATK:+10    → 攻击力+10
        - BOOST_STAT:8001:DEF:+5     → 防御力+5
        - BOOST_STAT:8001:MAX_HP:+20 → 最大生命+20
        - BOOST_STAT:8001:SPEED:+2   → 速度+2
        
        常用属性: ATK, DEF, MAX_HP, SPEED, CRIT, DODGE
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        stat_upper = stat.upper()
        
        # 属性映射
        stat_map = {
            'ATK': 'atk_base',
            'DEF': 'def_base', 
            'MAX_HP': 'max_hp',
            'SPEED': 'move_speed',
            'CRIT': 'crit_rate',
            'DODGE': 'dodge_rate'
        }
        
        attr_name = stat_map.get(stat_upper)
        if not attr_name:
            print(f"[StoryDirective] 未知属性: {stat}")
            return
        
        current = getattr(npc, attr_name, 0)
        
        if value.startswith('+') or value.startswith('-'):
            new_val = current + int(value)
        else:
            new_val = int(value)
        
        setattr(npc, attr_name, max(0, new_val))
        
        stat_names = {
            'ATK': '攻击', 'DEF': '防御', 'MAX_HP': '生命上限',
            'SPEED': '速度', 'CRIT': '暴击', 'DODGE': '闪避'
        }
        
        if hasattr(self._ctx, 'ft_manager'):
            delta_val = int(value) if value.startswith(('+', '-')) else new_val - current
            msg = f"{stat_names.get(stat_upper, stat_upper)}{delta_val:+d}"
            color = (150, 255, 150) if delta_val > 0 else (255, 150, 150)
            self._ctx.ft_manager.add_text(
                msg, npc.rect.centerx, npc.rect.top - 30, color
            )
    
    # ═══════════════════════════════════════════════════════════════════
    # 物品与装备指令 (NEW)
    # ═══════════════════════════════════════════════════════════════════
    
    def _handle_give_item(self, npc_id: str, item_id: str, quantity: str = '1'):
        """
        GIVE_ITEM:{npc_id}:{item_id}:{quantity} - 给予NPC物品
        
        用法:
        - GIVE_ITEM:8001:GRAIN:100     → 给予100单位粮食
        - GIVE_ITEM:8001:SWORD_IRON:1  → 给予铁剑
        - GIVE_ITEM:8001:MEDICINE:5    → 给予5个药品
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        item_upper = item_id.upper()
        qty = int(quantity)
        
        if not hasattr(npc, 'inventory'):
            npc.inventory = {}
        
        current = npc.inventory.get(item_upper, 0)
        npc.inventory[item_upper] = current + qty
        
        item_names = {
            'GRAIN': '粮食', 'MONEY': '铜钱', 'MEDICINE': '药品',
            'SWORD_IRON': '铁剑', 'SWORD_BRONZE': '铜剑', 'BOW_BASIC': '弓',
            'ARMOR_LEATHER': '皮甲', 'ARMOR_IRON': '铁甲',
            'TOOL_HOE': '锄头', 'TOOL_HAMMER': '铁锤',
            'RARE_JADE': '美玉', 'RARE_SCROLL': '秘籍'
        }
        
        if hasattr(self._ctx, 'ft_manager'):
            msg = f"+{qty}个{item_names.get(item_upper, item_upper)}"
            self._ctx.ft_manager.add_text(
                msg, npc.rect.centerx, npc.rect.top - 30, (255, 215, 100)
            )
    
    def _handle_take_item(self, npc_id: str, item_id: str, quantity: str = '1'):
        """
        TAKE_ITEM:{npc_id}:{item_id}:{quantity} - 从NPC收走物品
        
        用法:
        - TAKE_ITEM:8001:GRAIN:50   → 收走50单位粮食
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        item_upper = item_id.upper()
        qty = int(quantity)
        
        if not hasattr(npc, 'inventory'):
            npc.inventory = {}
        
        current = npc.inventory.get(item_upper, 0)
        npc.inventory[item_upper] = max(0, current - qty)
        
        if npc.inventory[item_upper] == 0:
            del npc.inventory[item_upper]
        
        item_names = {
            'GRAIN': '粮食', 'MONEY': '铜钱', 'MEDICINE': '药品'
        }
        
        if hasattr(self._ctx, 'ft_manager'):
            msg = f"-{qty}个{item_names.get(item_upper, item_upper)}"
            self._ctx.ft_manager.add_text(
                msg, npc.rect.centerx, npc.rect.top - 30, (200, 150, 100)
            )
    
    def _handle_equip_weapon(self, npc_id: str, weapon_id: str):
        """
        EQUIP_WEAPON:{npc_id}:{weapon_id} - 装备武器
        
        用法:
        - EQUIP_WEAPON:8001:SWORD_IRON   → 装备铁剑
        - EQUIP_WEAPON:8001:NONE         → 卸下武器
        
        效果：更新 NPC 的 weapon_id 属性，并重新计算攻击力
        """
        npc = self._find_npc(npc_id)
        if not npc:
            return
        
        weapon_upper = weapon_id.upper()
        
        # 卸下武器
        if weapon_upper == 'NONE':
            npc.weapon_id = None
            npc.weapon_atk_bonus = 0
            
            if hasattr(self._ctx, 'ft_manager'):
                self._ctx.ft_manager.add_text(
                    "卸下武器", npc.rect.centerx, npc.rect.top - 30, (150, 150, 150)
                )
            return
        
        # 武器攻击力加成
        weapon_bonus = {
            'SWORD_BRONZE': 5, 'SWORD_IRON': 10, 'SWORD_STEEL': 15,
            'BOW_BASIC': 8, 'BOW_COMPOUND': 12,
            'SPEAR_IRON': 12, 'AXE_IRON': 14,
            'STAFF_WOOD': 3, 'STAFF_IRON': 8,
            'FISTS': 0
        }
        
        npc.weapon_id = weapon_upper
        npc.weapon_atk_bonus = weapon_bonus.get(weapon_upper, 5)
        
        weapon_names = {
            'SWORD_BRONZE': '铜剑', 'SWORD_IRON': '铁剑', 'SWORD_STEEL': '钢剑',
            'BOW_BASIC': '木弓', 'BOW_COMPOUND': '复合弓',
            'SPEAR_IRON': '铁枪', 'AXE_IRON': '铁斧',
            'STAFF_WOOD': '木棍', 'STAFF_IRON': '铁棍'
        }
        
        if hasattr(self._ctx, 'ft_manager'):
            msg = f"装备{weapon_names.get(weapon_upper, weapon_upper)}"
            self._ctx.ft_manager.add_text(
                msg, npc.rect.centerx, npc.rect.top - 30, (200, 150, 255)
            )


# ═══════════════════════════════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════════════════════════════

_directive_executor = None

def get_directive_executor() -> StoryDirectiveExecutor:
    """获取指令执行器单例"""
    global _directive_executor
    if _directive_executor is None:
        _directive_executor = StoryDirectiveExecutor()
    return _directive_executor
