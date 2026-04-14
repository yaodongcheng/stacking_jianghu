# --- src/combat_system.py ---
import pygame
import math
import random
from src.definitions import *
from src.entities import NPC, Player
from src.utils import FloatingTextManager, log_game_event
from src.rumor_system import get_rumor_system

class Projectile:
    def __init__(self, x, y, target_x, target_y, damage, owner):
        self.x = x
        self.y = y
        self.damage = damage
        self.owner = owner
        self.speed = 8
        self.active = True
        
        # 计算向量
        dx = target_x - x
        dy = target_y - y
        dist = math.hypot(dx, dy)
        self.vx = (dx / dist) * self.speed if dist > 0 else 0
        self.vy = (dy / dist) * self.speed if dist > 0 else 0
        
    def update(self):
        self.x += self.vx
        self.y += self.vy
        # 简单的生命周期或出界销毁
        if self.x < 0 or self.x > 3000 or self.y < 0 or self.y > 2000:
            self.active = False
            
    def draw(self, screen, cam=None):
        if cam is not None:
            sx, sy = cam.world_to_screen(self.x, self.y)
        else:
            sx, sy = self.x, self.y
        pygame.draw.circle(screen, (255, 255, 0), (int(sx), int(sy)), 4)

class CombatManager:
    def __init__(self, ft_mgr):
        self.projectiles = []
        self.ft_mgr = ft_mgr
        self._ai_system = None   # 延迟注入，由 main.py 在 AISystem 初始化后设置

    def set_ai_system(self, ai_system):
        """注入 AISystem，使战斗模块可以触发旁观者广播"""
        self._ai_system = ai_system

    def spawn_bandit(self, world_map, all_cards):
        """生成一个土匪"""
        # 构造假数据
        data = {
            'id': random.randint(1000, 9999),
            'name': '山贼',
            'job': 'BANDIT',
            'hp': 50,
            'atk': 10,
            'def': 2,
            'tags': 'VILLAIN'
        }
        bandit = NPC(data)
        
        margin = 30
        side = random.choice(['LEFT', 'RIGHT', 'BOTTOM'])
        if side == 'LEFT':
            sx = margin + bandit.rect.width // 2
            sy = random.randint(margin, world_map.h - margin)
        elif side == 'RIGHT':
            sx = world_map.w - margin - bandit.rect.width // 2
            sy = random.randint(margin, world_map.h - margin)
        else:
            sx = random.randint(margin, world_map.w - margin)
            sy = world_map.h - margin - bandit.rect.height // 2
        bandit.set_pos(sx, sy)
        all_cards.append(bandit)
        return bandit

    def update(self, all_cards, world_map):
        # 1. 更新投射物
        for p in self.projectiles:
            p.update()
            # 简单的矩形碰撞检测
            p_rect = pygame.Rect(p.x-4, p.y-4, 8, 8)
            for card in all_cards:
                if not isinstance(card, NPC) or card == p.owner or card.safety == SAFETY_DEAD: continue
                if p_rect.colliderect(card.rect):
                    self.apply_damage(card, p.damage, attacker=p.owner)  # 修复：传入攻击者
                    p.active = False
                    break
               
        
        self.projectiles = [p for p in self.projectiles if p.active]

        

    def _check_hostile(self, a, b):
        """判断 a 和 b 是否敌对"""
        role_a = a.job
        role_b = b.job
        bad_guys = ['BANDIT', 'THUG']
        good_guys = ['GUARD', 'PLAYER', 'FARMER', 'MERCHANT', 'SCHOLAR']
        
        if role_a in bad_guys and role_b in good_guys: return True
        if role_a in good_guys and role_b in bad_guys: return True
        return False



    def apply_damage(self, victim, dmg, attacker=None):
        """伤害应用：HP归零变重伤"""
        # 提前拦截：已死亡/已倒地不再受伤
        if victim.safety in [SAFETY_DEAD, SAFETY_DOWNED]:
            atk_name = attacker.name if attacker else "?"
            log_game_event(
                f"[COMBAT][BLOCKED] {atk_name}→{victim.name} dmg={dmg} 被拦截"
                f"(victim.safety={victim.safety})", tag="COMBAT")
            return
        
        # 【事件保护】如果受害者正在参与事件演出，免疫伤害
        if getattr(victim, '_event_protected', False):
            log_game_event(
                f"[COMBAT][EVENT_PROTECTED] {victim.name} 正在参与事件演出，免疫伤害 dmg={dmg}",
                tag="COMBAT")
            return

        hp_before = victim.hp
        victim.hp -= dmg
        hp_after = max(0, victim.hp)
        victim.hp = hp_after
        hp_pct = hp_after / victim.max_hp if victim.max_hp > 0 else 0

        atk_name = attacker.name if attacker else "未知"
        atk_pos  = f"({attacker.rect.centerx},{attacker.rect.centery})" if attacker else "(?)"
        vic_pos  = f"({victim.rect.centerx},{victim.rect.centery})"
        log_game_event(
            f"[COMBAT][HIT] {atk_name}{atk_pos} → {victim.name}{vic_pos}"
            f"  dmg={dmg}  HP {hp_before}→{hp_after}/{victim.max_hp}"
            f"  ({hp_pct*100:.0f}%)",
            tag="COMBAT")

        # 浮字1：伤害数字（大红字）
        self.ft_mgr.add_text(f"-{dmg}", victim.rect.centerx, victim.rect.top - 10, (255, 60, 60), size=22)
        # 浮字2：当前 HP（颜色随血量变化）
        hp_color = (255, 80, 80) if hp_pct < 0.35 else (255, 180, 50) if hp_pct < 0.65 else (100, 220, 100)
        self.ft_mgr.add_text(f"HP {hp_after}/{victim.max_hp}", victim.rect.centerx + 20, victim.rect.top - 28, hp_color, size=16)

        # [修复] 被攻击时立即离开工作状态（调用bounce_off处理堆叠断开）
        if victim.stack_parent is not None:
            log_game_event(f"[COMBAT][LEAVE_WORK] {victim.name} 被攻击，离开工作状态", tag="COMBAT")
            victim.bounce_off(victim.stack_parent, distance=30)  # 小幅弹开，表示离开工作状态
            victim.is_working = False
            victim.work_timer = 0

        # --- 仇恨系统 ---
        if attacker is not None and hasattr(victim, 'hatred'):
            old_target = victim.aggro_target.name if victim.aggro_target else "无"
            if victim.aggro_target is None:
                victim.aggro_target = attacker
                victim.hatred[attacker.id] = victim.aggro_threshold
                log_game_event(
                    f"[COMBAT][AGGRO] {victim.name} 锁定 {attacker.name}"
                    f"  仇恨拉满→{victim.aggro_threshold}",
                    tag="COMBAT")
            else:
                hate_gain = dmg * 3
                victim.hatred[attacker.id] = victim.hatred.get(attacker.id, 0) + hate_gain
                current_target_hate = victim.hatred.get(victim.aggro_target.id, 0)
                if victim.hatred[attacker.id] > current_target_hate:
                    victim.aggro_target = attacker
                    log_game_event(
                        f"[COMBAT][AGGRO] {victim.name} 切换目标 {old_target}→{attacker.name}"
                        f"  仇恨={victim.hatred[attacker.id]}",
                        tag="COMBAT")
        
        # ═══════════════════════════════════════════════════════════════
        # 组织联动仇恨：攻击组织成员会引起同组织其他人的敌意
        # ═══════════════════════════════════════════════════════════════
        if attacker is not None and self._ai_system is not None:
            self._propagate_org_hatred(attacker, victim, dmg)

        # --- 倒地判定 ---
        if victim.hp <= 0:
            # 【事件保护】如果NPC正在参与事件演出，不设置重伤状态
            if getattr(victim, '_event_protected', False):
                log_game_event(
                    f"[COMBAT][EVENT_PROTECTED] {victim.name} 血量归零但有事件保护，跳过重伤判定",
                    tag="COMBAT")
                return
            
            prev_safety = victim.safety
            victim.safety = SAFETY_DOWNED
            victim.state  = STATE_DOWNED
            victim.in_combat = False
            
            # [!] 传闻系统：创建战斗传闻
            if attacker is not None:
                rumor_sys = get_rumor_system()
                is_player_attacker = getattr(attacker, 'job', '') == 'PLAYER'
                is_player_victim = getattr(victim, 'job', '') == 'PLAYER'
                
                if is_player_attacker:
                    # 玩家击败了NPC
                    rumor_sys.on_player_action('DEFEAT', attacker, target=victim)
                elif is_player_victim:
                    # 玩家被击败
                    rumor_sys.on_player_action('DEFEATED', victim, target=attacker)
            
            # [!] 物品掉落：重伤倒地时掉落部分物品
            self._drop_items_on_down(victim, attacker)
            
            # [!]【新增】检测是否是黑风大王被玩家击败
            # 如果玩家击败了黑风大王，触发悬赏取消和任务完成
            if attacker is not None and getattr(attacker, 'job', '') == 'PLAYER':
                victim_name = getattr(victim, 'name', '')
                victim_org = getattr(victim, 'org_id', '')
                victim_role = getattr(victim, 'org_role', '')
                
                # 检测黑风大王：黑风寨的首领
                is_heifeng_leader = (victim_org == 'heifeng_zhai' and victim_role == 'LEADER')
                if is_heifeng_leader:
                    self._on_heifeng_leader_defeated(attacker, victim)
            
            # [!] 立即广播 COMBAT_END：不依赖胜利方下一帧的 aggro_target 检查。
            # 这是最可靠的触发时机——倒地的瞬间直接清除 broadcast，
            # 让旁观者当帧就能在下一个 ai_system.update 帧末收到结束信号。
            if self._ai_system is not None and attacker is not None:
                # 从 ai_system 获取当前所有 NPC 列表进行广播
                all_npcs = getattr(self._ai_system, '_current_npcs', None)
                self._ai_system.broadcast_combat_end(attacker, victim, all_npcs)
                log_game_event(
                    f"[COMBAT][END_BROADCAST] {victim.name} 倒地，立即广播COMBAT_END"
                    f"  胜者={attacker.name}  通知NPC数={len(all_npcs) if all_npcs else 0}",
                    tag="COMBAT")
                # 同步清除攻击方的战斗状态（不等到下一帧 _decide_behavior）
                attacker.aggro_target = None
                attacker.combat_anchor_x = None
                attacker.combat_anchor_y = None
                attacker.in_combat = False
            victim.aggro_target = None
            self.ft_mgr.add_text("重伤倒地!", victim.rect.centerx, victim.rect.top - 40, (200, 50, 50))
            log_game_event(
                f"[COMBAT][DOWN] {victim.name}{vic_pos} 重伤倒地"
                f"  safety: {prev_safety}→{SAFETY_DOWNED}"
                f"  被 {atk_name} 击倒",
                tag="COMBAT")

    def apply_melee_attack(self, attacker, victim, all_cards=None):
        """近战结算：伤害 + 双方互弹"""
        # 使用含装备加成的有效攻击/防御（向下兼容：若无装备方法则直接读属性）
        eff_atk = attacker.get_effective_atk() if hasattr(attacker, 'get_effective_atk') else attacker.atk
        eff_def = victim.get_effective_def()   if hasattr(victim,   'get_effective_def') else victim.def_
        dmg = max(1, eff_atk - eff_def)

        atk_pos = f"({attacker.rect.centerx},{attacker.rect.centery})"
        vic_pos = f"({victim.rect.centerx},{victim.rect.centery})"
        dist = math.hypot(victim.rect.centerx - attacker.rect.centerx,
                          victim.rect.centery - attacker.rect.centery)
        log_game_event(
            f"[COMBAT][ATTACK] {attacker.name}{atk_pos} 攻击 {victim.name}{vic_pos}"
            f"  dist={dist:.1f}  atk={attacker.atk} def={victim.def_} → dmg={dmg}"
            f"  atk_cd={attacker.attack_cooldown:.0f}ms  atk_spd={attacker.atk_speed}ms",
            tag="COMBAT")

        # ── 战斗广播：在伤害结算之前判断是否需要广播 COMBAT_START ──
        # 必须在 apply_damage 之前判断 in_combat，否则 apply_damage 里
        # 的倒地逻辑会把 attacker.in_combat 设为 False，导致下面误触发重复广播。
        should_broadcast_start = (
            self._ai_system is not None and
            not getattr(attacker, 'in_combat', False)
        )

        self.apply_damage(victim, dmg, attacker=attacker)

        # 广播 COMBAT_START（只在本次攻击前双方都未标记战斗中时触发）
        if should_broadcast_start:
            # 直接从 all_cards 筛选出所有 NPC
            all_npcs = [c for c in all_cards if isinstance(c, NPC)]
            self._ai_system.broadcast_combat_start(attacker, victim, all_npcs)

        # 计算击退方向（从攻击者指向受害者）
        dx = victim.rect.centerx - attacker.rect.centerx
        dy = victim.rect.centery - attacker.rect.centery
        length = math.hypot(dx, dy)
        if length == 0:
            dx, dy, length = 1.0, 0.0, 1.0
        nx, ny = dx / length, dy / length

        # 受害者弹开目标点 —— 写入专属被动位移字段，不污染 AI 寻路的 target_x/y
        kb_tx = victim.rect.centerx + nx * 60
        kb_ty = victim.rect.centery + ny * 60
        victim.knockback_tx = kb_tx   # [!] 专属字段
        victim.knockback_ty = kb_ty
        victim.knockback_timer = 80
        log_game_event(
            f"[COMBAT][KNOCKBACK] {victim.name}{vic_pos}"
            f" → 弹开目标({kb_tx:.0f},{kb_ty:.0f})  硬直=80ms",
            tag="COMBAT")

        # 攻击者后缩目标点 —— 同上，写入专属字段
        rb_tx = attacker.rect.centerx - nx * 25
        rb_ty = attacker.rect.centery - ny * 25
        attacker.knockback_tx = rb_tx  # [!] 专属字段
        attacker.knockback_ty = rb_ty
        attacker.knockback_timer = 50
        log_game_event(
            f"[COMBAT][RECOIL]   {attacker.name}{atk_pos}"
            f" → 后缩目标({rb_tx:.0f},{rb_ty:.0f})  后摇=50ms",
            tag="COMBAT")

    # ═══════════════════════════════════════════════════════════════════
    # 组织联动仇恨系统：攻击组织成员会引起同组织其他人的敌意
    # ═══════════════════════════════════════════════════════════════════
    def _propagate_org_hatred(self, attacker, victim, dmg):
        """
        组织联动仇恨机制：
        - 当 victim 被攻击时，周围同组织的成员会对 attacker 产生仇恨
        - 仇恨值基于伤害量和组织等级
        - 距离越近，仇恨传播越强
        """
        # 1. 检查受害者是否有组织
        victim_org = getattr(victim, 'org_id', None)
        if not victim_org or victim_org == 'NONE':
            return
        
        # 2. 获取所有NPC列表
        all_npcs = getattr(self._ai_system, '_current_npcs', None)
        if not all_npcs:
            return
        
        # 3. 传播范围：根据组织性质决定
        # 军事/官方组织传播范围更大，江湖组织较小
        org_range = {
            'kaifeng_fu': 400,      # 开封府 - 官方势力，范围大
            'shenhou_fu': 350,      # 神侯府
            'gao_manor': 300,       # 高府
            'beggar_gang': 250,     # 丐帮 - 江湖帮派
            'shizizhipo': 200,      # 十字坡 - 黑店
            'tianshui_alley': 150,  # 商会 - 商业组织，反应较慢
            'taixue': 150,          # 太学 - 书生文弱
            'daxiangguo': 200,      # 相国寺
        }
        propagate_range = org_range.get(victim_org, 200)
        
        # 4. 遍历所有同组织成员
        propagated_count = 0
        for npc in all_npcs:
            # 跳过自己和受害者
            if npc == victim or npc == attacker:
                continue
            
            # 检查是否同组织
            npc_org = getattr(npc, 'org_id', None)
            if npc_org != victim_org:
                continue
            
            # 检查是否有效（非死亡/倒地）
            if npc.safety in [SAFETY_DEAD, SAFETY_DOWNED]:
                continue
            
            # 计算距离
            dist = math.hypot(npc.rect.centerx - victim.rect.centerx,
                              npc.rect.centery - victim.rect.centery)
            if dist > propagate_range:
                continue
            
            # 5. 计算仇恨值
            # 【修改】大幅提高仇恨基础值，确保同伴被攻击时能立即响应
            # 基础仇恨 = 伤害 * 系数（距离衰减）
            distance_factor = 1.0 - (dist / propagate_range) * 0.3  # 距离最远只衰减30%
            
            # 组织等级加成：高级成员对同伴被打反应更强烈
            npc_rank = getattr(npc, 'org_rank', 0)
            rank_factor = 1.0 + npc_rank * 0.3  # rank 5 = 2.5x (提高)
            
            # 角色加成：护卫/军人反应最快
            role_factor = 2.0 if npc.job in ['GUARD', 'SOLDIER'] else 1.2  # 提高护卫系数
            
            # 【新增】如果攻击者是山贼/泼皮，仇恨值翻倍
            attacker_is_hostile = getattr(attacker, 'job', '') in ['BANDIT', 'THUG']
            hostile_factor = 2.0 if attacker_is_hostile else 1.0
            
            hate_gain = int(dmg * distance_factor * rank_factor * role_factor * hostile_factor)
            hate_gain = max(15, hate_gain)  # 最低15点仇恨（提高）
            
            # 【新增】如果NPC是护卫职业，仇恨直接拉满（护卫必须出手保护）
            if npc.job in ['GUARD', 'SOLDIER']:
                hate_gain = max(hate_gain, npc.aggro_threshold + 5)
            
            # 6. 添加仇恨
            if not hasattr(npc, 'hatred'):
                npc.hatred = {}
            npc.hatred[attacker.id] = npc.hatred.get(attacker.id, 0) + hate_gain
            
            # 如果仇恨超过阈值且没有锁定目标，立即锁定
            if npc.aggro_target is None and npc.hatred[attacker.id] >= npc.aggro_threshold:
                npc.aggro_target = attacker
                npc.state = STATE_COMBAT  # 【新增】立即进入战斗状态
                npc.in_combat = True      # 【新增】
                log_game_event(
                    f"[ORG_AGGRO] {npc.name}({victim_org}) 因同伴{victim.name}被打 → 锁定{attacker.name}"
                    f"  仇恨={npc.hatred[attacker.id]} dist={dist:.0f}",
                    tag="ORG_AGGRO")
            else:
                # 仇恨不足以战斗，但应该向事件点集结
                # 投递 ORG_RALLY 事件让成员移动过来
                self._push_rally_event(npc, victim.rect.centerx, victim.rect.centery, victim_org)
            
            propagated_count += 1
        
        if propagated_count > 0:
            log_game_event(
                f"[ORG_HATRED] {victim.name}被攻击 → {victim_org}组织{propagated_count}人产生仇恨/集结",
                tag="ORG_AGGRO")

    def _push_rally_event(self, npc, cx, cy, org_id):
        """
        向 NPC 投递组织集结事件
        让成员向事件点移动（非战斗状态下）
        """
        # 如果已经在战斗或已经在集结，不重复推送
        if npc.aggro_target is not None:
            return
        rally_point = getattr(npc, '_rally_point', None)
        if rally_point is not None:
            return  # 已有集结点
        
        # 设置集结点
        npc._rally_point = (cx, cy)
        npc._rally_org = org_id
        npc._rally_time = 10000  # 集结持续10秒
        
        log_game_event(
            f"[ORG_RALLY] {npc.name} 收到集结信号 → ({cx},{cy})",
            tag="ORG_AGGRO")

    # ═══════════════════════════════════════════════════════════════════
    # 重伤掉落系统：NPC倒地时掉落物品，吸引周围山贼来抢
    # ═══════════════════════════════════════════════════════════════════
    def _drop_items_on_down(self, victim, attacker):
        """
        当NPC重伤倒地时，掉落部分物品和金钱到地上
        - 掉落概率和数量基于角色身份
        - 商人/富人掉落更多，平民掉落少
        - 掉落物品会广播给附近的掠夺者（山贼等）
        """
        # 获取受害者的物品清单和金钱
        inventory = getattr(victim, 'inventory', {})
        money = getattr(victim, 'money', 0)
        
        # 没有东西可掉落
        if not inventory and money <= 0:
            return
        
        # 计算掉落概率（富人/商人掉落概率高）
        drop_chance = 0.3  # 基础30%
        if victim.job in ['MERCHANT', 'TRADER']:
            drop_chance = 0.7  # 商人70%
        elif victim.job in ['SCHOLAR', 'OFFICIAL']:
            drop_chance = 0.5  # 文官50%
        elif victim.job in ['FARMER', 'CRAFTSMAN']:
            drop_chance = 0.2  # 平民20%
        
        dropped_items = []
        
        # 金钱掉落：掉落50%-100%的金钱
        if money > 0 and random.random() < drop_chance:
            drop_money = int(money * random.uniform(0.5, 1.0))
            victim.money -= drop_money
            dropped_items.append(('money', drop_money))
            self.ft_mgr.add_text(f"掉落 {drop_money}文", victim.rect.centerx, victim.rect.top - 55, (255, 215, 0))
        
        # 物品掉落：每件物品单独判定
        items_to_drop = []
        for item_id, qty in list(inventory.items()):
            if random.random() < drop_chance:
                drop_qty = random.randint(1, qty)
                items_to_drop.append((item_id, drop_qty))
        
        for item_id, drop_qty in items_to_drop:
            inventory[item_id] -= drop_qty
            if inventory[item_id] <= 0:
                del inventory[item_id]
            dropped_items.append(('item', item_id, drop_qty))
        
        # 如果有物品掉落，广播给附近的掠夺者
        if dropped_items and self._ai_system is not None:
            self._broadcast_loot_event(victim, dropped_items, attacker)
            log_game_event(
                f"[LOOT][DROP] {victim.name} 倒地掉落 {len(dropped_items)}件物品"
                f"  被 {attacker.name if attacker else '?'} 击倒",
                tag="LOOT")

    def _on_heifeng_leader_defeated(self, attacker, victim):
        """
        黑风大王被玩家击败的回调
        - 取消黑风寨对玩家的悬赏
        - 设置任务完成标记
        - 触发任务对话
        """
        log_game_event(f"[QUEST] 黑风大王被玩家击败！触发任务完成逻辑", tag="QUEST")
        
        # 获取势力战争系统（取消悬赏）
        faction_war = getattr(self._ai_system, '_faction_war_ref', None)
        if faction_war:
            # 取消黑风寨对玩家的所有悬赏
            player_id = getattr(attacker, 'id', 9999)
            for bounty in faction_war.active_bounties:
                if bounty.get('target_id') == player_id and bounty.get('issuer_org') == 'heifeng_zhai':
                    bounty['active'] = False
                    log_game_event(f"[QUEST] 悬赏 {bounty['id']} 已取消", tag="QUEST")
        
        # 设置任务完成标记
        # 需要通过某种方式访问 QuestManager
        # 这里使用一个全局标记，在 main.py 的游戏循环中检测
        victim._defeated_by_player = True
        victim._defeat_trigger_quest = True
        
        # 浮动文字
        self.ft_mgr.add_text("击败黑风大王！", attacker.rect.centerx, attacker.rect.top - 60, (255, 215, 0), size=24)
        self.ft_mgr.add_text("悬赏已取消！", attacker.rect.centerx, attacker.rect.top - 85, (100, 255, 100))

    def _broadcast_loot_event(self, victim, dropped_items, attacker):
        """
        广播掉落事件给附近的掠夺者（山贼、恶霸等）
        让他们移动过来捡取物品
        """
        all_npcs = getattr(self._ai_system, '_current_npcs', None)
        if not all_npcs:
            return
        
        loot_x, loot_y = victim.rect.centerx, victim.rect.centery
        
        # 掠夺者职业列表
        looter_jobs = ['BANDIT', 'THUG', 'VILLAIN']
        
        notified_count = 0
        for npc in all_npcs:
            if npc == attacker:
                continue  # 攻击者自己会直接拿
            
            # 检查是否是掠夺者
            if npc.job not in looter_jobs:
                continue
            
            # 检查状态
            if npc.safety in [SAFETY_DEAD, SAFETY_DOWNED]:
                continue
            
            # 检查距离（300像素范围内的掠夺者会响应）
            dist = math.hypot(npc.rect.centerx - loot_x, npc.rect.centery - loot_y)
            if dist > 300:
                continue
            
            # 设置抢夺目标点
            npc._loot_target = (loot_x, loot_y)
            npc._loot_timer = 8000  # 8秒内前往抢夺
            npc._loot_items = dropped_items  # 可抢物品列表
            notified_count += 1
        
        if notified_count > 0:
            log_game_event(
                f"[LOOT][BROADCAST] {victim.name}掉落 → 通知{notified_count}名掠夺者",
                tag="LOOT")
