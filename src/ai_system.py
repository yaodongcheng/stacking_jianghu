# --- src/ai_system.py ---
import math
import random
import pygame
from src.definitions import *
from src.definitions import ITEM_BOOK, ITEM_MERIT
from src.entities import NPC, Building
from src.utils import log_game_event
from src.recipe_driven_ai import get_recipe_driven_ai, JOB_BUILDING_MAP
from src.spatial_hash import get_spatial_hash

class AISystem:
    def __init__(self, combat_manager):
        self.combat_manager = combat_manager # 需要调用战斗计算
        self.scan_radius = 400 # 索敌范围
        self.see_radius = 250  # 视觉感知半径（比索敌范围小，更真实）
        
        # ══════════════════════════════════════════════════════════════
        # 【性能优化】空间哈希 + 时间分片
        # ══════════════════════════════════════════════════════════════
        self._spatial_hash = get_spatial_hash(cell_size=200)  # 200px 网格
        self._frame_counter = 0  # 帧计数器（用于时间分片）
        self._stagger_groups = 4  # 分成4组，每组每4帧更新一次视觉感知

        # ══════════════════════════════════════════════════════════════
        # 事件系统（中断模型 - 一次性广播）
        # ══════════════════════════════════════════════════════════════
        #
        # 设计原则：
        #   主动决策（巡逻/工作/围观）受 decision_timer 节流，每隔若干帧才运行一次。
        #   突发事件（战斗开始/结束、被攻击、倒地/救援）需要立即响应，不能等节流。
        #
        # 实现方式（简化版）：
        #   npc._event_queue  : 每个 NPC 自己的事件队列
        #                       - 由 broadcast_combat_start/end 直接按距离写入
        #                       - 每帧无条件处理，不受 decision_timer 节流
        #
        # 帧流程：
        #   ① COMBAT_START/END 发生时：立即扫描所有 NPC → 符合条件的直接投递事件
        #   ② 帧中(每NPC)：_process_events(npc) 无条件处理队列，可打断主动决策
        #   ③ 帧中(每NPC)：若未被打断 → decision_timer 节流 → _decide_behavior
        #
        # 优势：无持续轮询，无去重复杂度，事件生命周期简单明了。
        # ══════════════════════════════════════════════════════════════
        self.SPECTATE_NOTICE_RADIUS = 600  # 听闻战斗广播事件的最大距离

    # ══════════════════════════════════════════════════════════════
    # 公开接口：外部向指定 NPC 投递突发事件
    # ══════════════════════════════════════════════════════════════
    def push_event(self, npc, evt: dict):
        """
        向单个 NPC 投递突发事件（直接入队，当帧即可处理）。
        evt 格式：{'type': 'COMBAT_START'/'COMBAT_END'/..., ...}
        调用方无需关心节流，保证本帧 _process_events 会消费。
        """
        queue = getattr(npc, '_event_queue', None)
        if queue is None:
            npc._event_queue = []
            queue = npc._event_queue
        queue.append(evt)

    # ══════════════════════════════════════════════════════════════
    # （已删除：轮询分发机制）
    # ══════════════════════════════════════════════════════════════
    # 一次性广播模式下不需要 _dispatch_broadcasts：
    # broadcast_combat_start/end 发生时直接扫描 all_npcs → push_event()

    # ══════════════════════════════════════════════════════════════
    # 内部：突发事件处理器（每帧无条件执行，不受 decision_timer 节流）
    # ══════════════════════════════════════════════════════════════
    def _process_events(self, npc, world_map) -> bool:
        """
        消费 npc._event_queue 中的所有事件，立即应用状态变更。
        返回 True  → 本帧有突发事件被处理，主动决策树应跳过。
        返回 False → 无突发事件，正常走 decision_timer 节流。

        支持的事件类型：
          COMBAT_START  → 记录围观中心，NPC 开始聚集（打断普通行为）
          COMBAT_END    → 清除围观状态，立即散去（打断围观行为）
        （后续可扩展：DISASTER / RESCUE_NEEDED / ALARM 等）
        """
        queue = getattr(npc, '_event_queue', None)
        if not queue:
            return False
        
        #重伤、死亡等状态的 NPC 不处理事件
        if npc.safety in [SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED]:
            return False

        interrupted = False

        for evt in queue:
            etype = evt.get('type')

            # ── COMBAT_START：开始围观 ──────────────────────────
            if etype == 'COMBAT_START':
                # 当事人不围观
                if npc.id in evt.get('source_ids', set()):
                    continue
                ecx, ecy = evt['cx'], evt['cy']
                already = getattr(npc, 'spectate_src_x', None) is not None
                npc.spectate_src_x = ecx
                npc.spectate_src_y = ecy
                if not already:
                    combatants = evt.get('combatant_names', '未知 vs 未知')
                    log_game_event(
                        f"[EVENT] {npc.name} 收到COMBAT_START → 围观({ecx},{ecy})"
                        f"  战斗双方=[{combatants}]", tag="AI")
                interrupted = True   # 打断主动决策，让围观逻辑接管

            # ── COMBAT_END：散去 ────────────────────────────────
            elif etype == 'COMBAT_END':
                if getattr(npc, 'spectate_src_x', None) is None:
                    continue   # 没在围观，忽略
                log_game_event(f"[EVENT] {npc.name} 收到COMBAT_END → 立即散去", tag="AI")
                npc.spectate_anchor_set = False
                npc.spectate_src_x     = None
                npc.spectate_src_y     = None
                # [修复] 清除围观行为，让NPC重新决策
                npc.action_queue.clear()
                if world_map:
                    tx, ty = world_map.get_random_pos_in_rect(world_map.city_rect)
                    npc.set_movement_target(tx, ty, "围观结束-散去离开")
                    npc.state    = STATE_MOVING
                    npc.ai_reason = "散去离开"
                else:
                    npc.state    = STATE_IDLE
                    npc.ai_reason = "散去(原地)"
                interrupted = True
            
            # ── EVENT_ZONE_CLEAR：清场（离开事件区）────────────────
            elif etype == 'EVENT_ZONE_CLEAR':
                # 事件区清场：让NPC离开事件区
                center_x = evt.get('center_x', 0)
                center_y = evt.get('center_y', 0)
                radius = evt.get('radius', 300)
                
                # 计算离开方向：从事件中心向外
                import math
                npc_x = npc.rect.centerx
                npc_y = npc.rect.centery
                angle = math.atan2(npc_y - center_y, npc_x - center_x)
                
                # 目标点：事件区边界外 50 像素
                exit_distance = radius + 50
                target_x = int(center_x + math.cos(angle) * exit_distance)
                target_y = int(center_y + math.sin(angle) * exit_distance)
                
                # 清除当前行为
                npc.action_queue.clear()
                npc.set_target_obj(None)  # 清除建筑目标
                
                # 设置移动目标和状态
                npc.state = STATE_MOVING
                npc.ai_reason = "清场"
                npc.set_movement_target(target_x, target_y, "清场：离开事件区")
                
                log_game_event(f"[EVENT] {npc.name} 收到EVENT_ZONE_CLEAR → 清场前往 ({target_x}, {target_y})", tag="AI")
                interrupted = True

        npc._event_queue = []   # 消费完毕，清空队列
        return interrupted

    # ══════════════════════════════════════════════════════════════
    # 视觉感知系统（See Event）
    # ══════════════════════════════════════════════════════════════
    # 
    # 设计原则：
    #   每个 NPC 在决策前会"看"一眼周围，根据自己的职业/性格决定反应。
    #   这是主动感知，不依赖广播事件。路过的守卫能看到正在作案的山贼。
    #
    # 触发条件：
    #   - NPC 处于 IDLE/MOVING 等非战斗状态
    #   - 视野内存在需要反应的情况
    #
    # 反应类型（按 NPC 职业分）：
    #   GUARD/OFFICIAL → 看到 BANDIT/THUG → 立即产生仇恨并攻击
    #   BANDIT/THUG    → 看到 肥羊 → 仇恨（已有逻辑）
    #   善良侠客       → 看到平民被攻击 → 仇恨攻击者
    #   普通人         → 看到打架 → 围观（已有广播机制）
    # ══════════════════════════════════════════════════════════════

    def _process_see(self, npc, all_npcs) -> bool:
        """
        视觉感知处理：NPC 主动扫描视野内的情况。
        返回 True  → 发现需要立即反应的事件（如敌人），应打断当前行为。
        返回 False → 没有需要反应的事，继续原行为。
        
        这是通用逻辑，不针对特定职业，而是根据 NPC 的属性动态决定反应。
        
        【性能优化】
        1. 使用空间哈希查询邻近 NPC，避免全量遍历
        2. 时间分片：每个 NPC 每 N 帧才执行一次完整感知
           - 战斗中的 NPC 每帧都感知（保证响应速度）
           - 非战斗 NPC 分组轮流感知
        """
        # 已有锁定目标或正在战斗中，不需要重新感知
        if getattr(npc, 'aggro_target', None) is not None:
            return False
        if npc.state == STATE_COMBAT:
            return False
        if npc.safety in [SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED]:
            return False
        
        # ══════════════════════════════════════════════════════════════
        # 【时间分片】非紧急 NPC 每 N 帧才执行一次视觉感知
        # 效果：将每帧的感知计算量降低到 1/N
        # ══════════════════════════════════════════════════════════════
        npc_group = getattr(npc, 'id', id(npc)) % self._stagger_groups
        if self._frame_counter % self._stagger_groups != npc_group:
            # 不是本组更新帧，跳过感知
            return False
        
        my_is_villain = self._is_villain(npc)
        my_is_guard = npc.job in ('GUARD', 'OFFICIAL', 'SOLDIER')
        
        mx, my = npc.rect.centerx, npc.rect.centery
        
        # ══════════════════════════════════════════════════════════════
        # 【空间哈希查询】只获取视野范围内的 NPC，避免遍历全部
        # 复杂度：从 O(n) 降到 O(k)，k 是邻近 NPC 数量
        # ══════════════════════════════════════════════════════════════
        nearby_npcs = self._spatial_hash.query_radius(npc, self.see_radius)
        
        for other in nearby_npcs:
            # query_radius 已经排除了自己和超出范围的实体，无需再判断
            if other.safety in [SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED]:
                continue
            
            other_is_villain = self._is_villain(other)
            other_is_fighting = getattr(other, 'in_combat', False)
            other_victim = getattr(other, 'aggro_target', None)
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 情况1: 守卫/官差 看到 山贼/泼皮正在作恶 → 产生仇恨
            # 【修复】守卫不再"见山贼就杀"，而是需要山贼正在做坏事
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            if my_is_guard and other_is_villain:
                # 检查山贼是否正在做坏事（正在攻击/抢劫等）
                is_doing_evil = other_is_fighting or getattr(other, 'is_robbing', False)
                
                # 如果山贼正在作恶，守卫才会介入
                if is_doing_evil:
                    # 添加冷却：同一个目标不要每帧都累加仇恨
                    if not hasattr(npc, '_hate_cooldown'):
                        npc._hate_cooldown = {}
                    
                    current_time = pygame.time.get_ticks()
                    last_hate_time = npc._hate_cooldown.get(other.id, 0)
                    
                    # 冷却3秒
                    if current_time - last_hate_time > 3000:
                        npc._hate_cooldown[other.id] = current_time
                        
                        see_hate = 30  # 视觉仇恨
                        current_hate = npc.hatred.get(other.id, 0)
                        npc.hatred[other.id] = current_hate + see_hate
                        
                        log_game_event(
                            f"[SEE] {npc.name}({npc.job}) 看到山贼 {other.name} 正在作恶"
                            f"  → 仇恨 +{see_hate} = {npc.hatred[other.id]}",
                            tag="SEE_AGGRO"
                        )
                        
                        # 如果仇恨超过阈值，立即锁定
                        if npc.hatred[other.id] >= npc.aggro_threshold:
                            npc.aggro_target = other
                            npc.state = STATE_COMBAT
                            npc.ai_reason = f"制止山贼{other.name}"
                            npc.action_queue.clear()
                            return True
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 情况2: 善良的人 看到 恶人正在攻击平民 → 仇恨攻击者
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            if ( my_is_guard) and not my_is_villain:
                if other_is_villain and other_is_fighting and other_victim:
                    # 检查受害者是不是无辜的人
                    victim_is_innocent = not self._is_villain(other_victim)
                    if victim_is_innocent:
                        see_hate = 50  # 看到欺负好人，仇恨拉满
                        current_hate = npc.hatred.get(other.id, 0)
                        npc.hatred[other.id] = current_hate + see_hate
                        
                        log_game_event(
                            f"[SEE] {npc.name} 看到 {other.name} 正在攻击无辜的 {other_victim.name}"
                            f"  → 仇恨攻击者 +{see_hate}",
                            tag="SEE_AGGRO"
                        )
                        
                        if npc.hatred[other.id] >= npc.aggro_threshold:
                            npc.aggro_target = other
                            npc.state = STATE_COMBAT
                            npc.ai_reason = f"路见不平，救{other_victim.name}"
                            npc.action_queue.clear()
                            return True
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 情况3: 同组织 看到 同组织的人正在被攻击 → 仇恨攻击者（援助）
            # 【修复】使用组织ID判断，而不是善恶阵营；添加冷却
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 【性能优化】使用攻击者缓存 O(1) 查询，替代遍历
            other_id = getattr(other, 'id', id(other))
            attacker_of_other = self._attacker_cache.get(other_id)
            
            if attacker_of_other and attacker_of_other != npc:
                # 检查是否同组织（使用org_id）
                my_org = getattr(npc, 'org_id', None)
                other_org = getattr(other, 'org_id', None)
                attacker_org = getattr(attacker_of_other, 'org_id', None)
                
                # 只有同组织成员被攻击时才援助
                if my_org and my_org == other_org and my_org != attacker_org:
                    # 添加冷却：同一个攻击者不要每帧累加仇恨
                    if not hasattr(npc, '_hate_cooldown'):
                        npc._hate_cooldown = {}
                    
                    current_time = pygame.time.get_ticks()
                    last_hate_time = npc._hate_cooldown.get(attacker_of_other.id, 0)
                    
                    # 冷却5秒
                    if current_time - last_hate_time > 5000:
                        npc._hate_cooldown[attacker_of_other.id] = current_time
                        
                        see_hate = 40
                        current_hate = npc.hatred.get(attacker_of_other.id, 0)
                        npc.hatred[attacker_of_other.id] = current_hate + see_hate
                        
                        log_game_event(
                            f"[SEE] {npc.name} 看到同门 {other.name} 正在被 {attacker_of_other.name} 攻击"
                            f"  → 仇恨攻击者 +{see_hate}",
                            tag="SEE_AGGRO"
                        )
                        
                        if npc.hatred[attacker_of_other.id] >= npc.aggro_threshold:
                            npc.aggro_target = attacker_of_other
                            npc.state = STATE_COMBAT
                            npc.ai_reason = f"救援同门{other.name}"
                            npc.action_queue.clear()
                            return True
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 情况3.5: 【跟随者协助】跟随者看到主人被攻击 → 仇恨攻击者
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            if getattr(npc, 'is_follower', False) and npc.ai_mode == "FOLLOW":
                # 检查主人（玩家）是否正在被攻击
                if other.job == 'PLAYER':
                    # 场景A: 有人在攻击主人 → 保护主人
                    # 【性能优化】使用攻击者缓存 O(1) 查询
                    player_id = getattr(other, 'id', id(other))
                    potential_atk = self._attacker_cache.get(player_id)
                    if potential_atk and potential_atk != npc:
                        # 有人在攻击主人！立即加入战斗
                        see_hate = 100  # 对攻击主人的人直接仇恨拉满
                        npc.hatred[potential_atk.id] = see_hate
                        npc.aggro_target = potential_atk
                        npc.state = STATE_COMBAT
                        npc.ai_reason = f"保护主人，对抗{potential_atk.name}"
                        npc.action_queue.clear()
                        
                        log_game_event(
                            f"[SEE] 跟随者 {npc.name} 发现主人被 {potential_atk.name} 攻击"
                            f"  → 加入战斗保护主人",
                            tag="SEE_AGGRO"
                        )
                        return True
                    
                    # 场景B: 主人在攻击别人 → 协助主人
                    player_target = getattr(other, 'aggro_target', None)
                    if player_target and player_target != npc and player_target.safety not in [SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED]:
                        # 主人在战斗！协助攻击同一目标
                        see_hate = 80
                        npc.hatred[player_target.id] = see_hate
                        npc.aggro_target = player_target
                        npc.state = STATE_COMBAT
                        npc.ai_reason = f"协助主人攻击{player_target.name}"
                        npc.action_queue.clear()
                        
                        log_game_event(
                            f"[SEE] 跟随者 {npc.name} 发现主人在攻击 {player_target.name}"
                            f"  → 协助攻击",
                            tag="SEE_AGGRO"
                        )
                        return True
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 情况4: 【阶层系统】护卫看到低阶层人物靠近被保护者 → 拦截盘问
            # 【已禁用】此功能暂时关闭，避免干扰事件演出
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # my_org_role = getattr(npc, 'org_role', None)
            # if my_org_role == 'BODYGUARD' and other.job == 'PLAYER':
            #     ... (拦截逻辑已禁用)
        
        return False

    def update(self, all_cards, world_map, dt_ms=16, day_progress=0.0):
        """每帧更新所有NPC的决策"""
        self._dt_ms = dt_ms  # 存储供 _execute_combat 使用
        self._day_progress = day_progress  # 【住所系统】存储日进度供夜间休息判断
        npcs = [c for c in all_cards if isinstance(c, NPC)]
        buildings = [c for c in all_cards if isinstance(c, Building)]
        
        # 存储 NPC 列表供 combat_system 广播使用
        self._current_npcs = npcs
        
        # ══════════════════════════════════════════════════════════════
        # 【性能优化】每帧重建空间哈希网格
        # 复杂度：O(n) 建立，后续查询从 O(n) 降到 O(k)（k = 邻近实体数）
        # ══════════════════════════════════════════════════════════════
        self._spatial_hash.rebuild(npcs)
        self._frame_counter += 1
        
        # ══════════════════════════════════════════════════════════════
        # 【性能优化】构建攻击者缓存：target_id -> attacker
        # 用于快速查询"谁在攻击某人"，避免每次都遍历全部 NPC
        # ══════════════════════════════════════════════════════════════
        self._attacker_cache = {}  # {target_id: attacker_npc}
        for npc_item in npcs:
            target = getattr(npc_item, 'aggro_target', None)
            if target is not None:
                target_id = getattr(target, 'id', id(target))
                self._attacker_cache[target_id] = npc_item

        for npc in npcs:
            if npc.job == 'PLAYER':
                continue

            # 将 world_map 引用注入 NPC
            npc._world_map_ref  = world_map
            npc._nearby_npcs_ref = npcs

            # ── 状态过滤：死亡/重伤/事件中/拖拽中 → 跳过 ─────────────
            # 【事件保护】如果NPC有事件保护标记，跳过DOWNED状态检查（允许演出）
            is_event_protected = getattr(npc, '_event_protected', False)
            
            if npc.safety in [SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED]:
                # 如果有事件保护，不强制设为DOWNED状态
                if is_event_protected and npc.safety == SAFETY_DOWNED:
                    # 事件期间自动恢复：将safety改回NORMAL，保持EVENT状态
                    npc.safety = SAFETY_NORMAL
                    npc.state = STATE_EVENT
                    continue
                    
                new_state = STATE_DOWNED if npc.safety == SAFETY_DOWNED else STATE_GONE
                if npc.state != new_state and npc.safety == SAFETY_DOWNED:
                    was_in_combat = getattr(npc, 'in_combat', False)
                    has_aggro     = getattr(npc, 'aggro_target', None) is not None
                    hunters       = [n for n in npcs if getattr(n, 'aggro_target', None) is npc]
                  #  log_game_event(                        f"[DEBUG][DOWNED] {npc.name} 进入重伤状态"                        f"  prev_state={npc.state}  in_combat={was_in_combat}"                        f"  aggro_target={'有' if has_aggro else '无'}"                        f"  追击者={[h.name for h in hunters] if hunters else '[!]无'}",                        tag="AI")
                npc.state = new_state
                continue

            if npc.dragging or npc.state == STATE_EVENT or npc.state == STATE_MEETING:
                continue
            
            # 【新增】逃跑状态：跳过AI决策，只执行移动
            if npc.state == STATE_FLEEING:
                continue

            # ── 每帧即时递减计时器（不受 decision_timer 节流）───────────
            if npc.knockback_timer > 0:
                npc.knockback_timer = max(0, npc.knockback_timer - dt_ms)
            if npc.attack_cooldown > 0:
                npc.attack_cooldown = max(0, npc.attack_cooldown - dt_ms)

            # ── Step B：突发事件处理（每帧无条件执行，不受节流）──────────
            event_interrupted = self._process_events(npc, world_map)
            
            # ── Step B2：视觉感知（每帧执行，发现敌人会打断当前行为）─────
            see_interrupted = self._process_see(npc, npcs)
            if see_interrupted:
                event_interrupted = True  # 视觉感知也算突发事件

            # ── 弹开硬直期：锁定状态，跳过决策树 ────────────────────────
            if npc.knockback_timer > 0:
                npc.state     = STATE_COMBAT
                npc.ai_reason = "弹开中"
                continue

            # ── 堆叠工作中：只有在突发事件需要响应时才进入决策树 ──────
            if npc.stack_parent and npc.state != STATE_CARRYING:
                # 白天 + 堆叠在自己的家上 → 起床，不跳过决策
                home = getattr(npc, 'home_building', None)
                if home is not None and npc.stack_parent == home and not self._is_nighttime():
                    npc.bounce_off(home, distance=50)
                    npc.state = STATE_IDLE
                    npc.ai_reason = "起床了"
                    npc.action_queue.clear()
                    # 不 continue —— 让决策树分配新工作
                elif npc.aggro_target is None and not event_interrupted:
                    if getattr(npc, 'spectate_src_x', None) is None:
                        continue   # 安静在建筑里干活，不需要决策

            # ── Step C：执行原子行为队列（每帧无条件执行）─────────────────
            queue_running = npc.action_queue.tick(dt_ms)
            
            # ── Step D：决策树分流 ────────────────────────────────────────
            # 如果行为队列有任务在执行，跳过决策树（除非是战斗/突发事件）
            if queue_running and not event_interrupted and npc.state != STATE_COMBAT:
                continue  # 行为队列接管，不进入决策树
            
            if event_interrupted:
                # 有突发事件 → 本帧立即进入决策树（跳过节流）
                self._decide_behavior(npc, npcs, buildings, world_map)
            elif npc.state in (STATE_COMBAT, STATE_CARRYING):
                # 战斗/背人 → 每帧都需要实时决策
                self._decide_behavior(npc, npcs, buildings, world_map)
            elif npc.action_queue.is_empty():
                # 行为队列为空 → 普通主动决策（受 decision_timer 节流）
                npc.decision_timer -= 1
                if npc.decision_timer > 0:
                    continue
                npc.decision_timer = npc.decision_interval
                self._decide_behavior(npc, npcs, buildings, world_map)

        # ── 同步堆叠位置 ──────────────────────────────────────────────
        # [优化] 减少不必要的位置更新，避免瞬移问题
        for card in all_cards:
            if card.stack_parent and not card.dragging:
                # 只有位置明显不对时才更新，避免每帧微调造成的抖动
                expected_x = card.stack_parent.rect.centerx
                expected_y = card.stack_parent.rect.centery + STACK_OFFSET_Y
                current_dist = abs(card.rect.centerx - expected_x) + abs(card.rect.centery - expected_y)
                
                if current_dist > 5:  # 只有距离超过5像素才同步
                    card.set_pos(expected_x, expected_y)


    def _decide_behavior(self, npc, all_npcs, all_buildings, world_map):
        """
        决策树（原子行为队列版）：
        所有决策最终都是向 npc.action_queue 中添加原子行为。
        决策树只负责"做什么决定"，不负责"怎么执行"。
        """
        from src.atomic_actions import (
            MoveToPosition, FollowTarget, Combat, Rescue, Spectate,
            Roam, MoveToBuilding, Wait, Stay, CarryTarget, DropTarget
        )
        
        # ══════════════════════════════════════════════════════════════
        # 特殊 NPC 检查
        # ══════════════════════════════════════════════════════════════
        if npc.id == 9000:
            if npc.quest_icon_active:
                npc.action_queue.clear()
                npc.action_queue.enqueue(Stay(reason="等待玩家..."))
                return
        
        # ══════════════════════════════════════════════════════════════
        # 被堆叠的 NPC 不做移动决策（白天起床例外）
        # ══════════════════════════════════════════════════════════════
        if npc.stack_parent is not None:
            # 白天 + 堆叠在自己的家上 → 起床
            home = getattr(npc, 'home_building', None)
            if home is not None and npc.stack_parent == home and not self._is_nighttime():
                npc.bounce_off(home, distance=50)
                npc.state = STATE_IDLE
                npc.ai_reason = "起床了"
                npc.action_queue.clear()
                # 继续往下走，让后续优先级分配工作
            else:
                return
        
        # ══════════════════════════════════════════════════════════════
        # 状态清理：STATE_CARRYING 但没在背人
        # ══════════════════════════════════════════════════════════════
        if npc.state == STATE_CARRYING and npc.stack_child is None:
            npc.state = STATE_IDLE
            npc.ai_reason = "背人完成"
            npc.action_queue.clear()
            npc._is_rescuing = False
            if hasattr(npc, '_rescue_target_id'):
                npc._rescue_target_id = None
        
        # ══════════════════════════════════════════════════════════════
        # 优先级 0: 正在背人送医 → 继续执行（行为队列已有 Rescue）
        # ══════════════════════════════════════════════════════════════
        if npc.state == STATE_CARRYING and npc.stack_child and isinstance(npc.stack_child, NPC):
            # Rescue 行为已在队列中，让它继续执行
            if npc.action_queue.is_empty():
                # 队列空了但还在背人 → 补上送医行为
                clinic = next((b for b in all_buildings if b.building_type == 'CLINIC'), None)
                npc.action_queue.enqueue(Rescue(npc.stack_child, clinic, reason=f"送{npc.stack_child.name}去医馆"))
            return
        
        # ══════════════════════════════════════════════════════════════
        # 优先级 1: 战斗
        # ══════════════════════════════════════════════════════════════
        if npc.atk > 0:
            # 已锁定目标但目标已倒地 → 广播结束并清除
            prev_target = getattr(npc, 'aggro_target', None)
            if prev_target is not None and prev_target.safety in [SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED]:
                self._broadcast_combat_end(npc, prev_target)
                npc.aggro_target = None
                npc.combat_anchor_x = None
                npc.combat_anchor_y = None
                npc.in_combat = False
                npc.action_queue.clear()
                npc.state = STATE_IDLE
                npc.ai_reason = "对手已倒地"
                log_game_event(f"[AI][VICTORY] {npc.name} 感知到 {prev_target.name} 倒地，广播COMBAT_END", tag="AI")
            
            target = self._find_enemy(npc, all_npcs)
            if target:
                self._enqueue_combat(npc, target)
                return
        
        # ══════════════════════════════════════════════════════════════
        # 优先级 2: 救援（非反派）
        # ══════════════════════════════════════════════════════════════
        if not self._is_villain(npc):
            if self._enqueue_rescue(npc, all_npcs, all_buildings):
                return
        
        # ══════════════════════════════════════════════════════════════
        # 优先级 3: 围观
        # ══════════════════════════════════════════════════════════════
        if self._enqueue_spectate(npc):
            return
        
        # ══════════════════════════════════════════════════════════════
        # 优先级 3.5: 组织集结（同伴被攻击时前去支援）
        # ══════════════════════════════════════════════════════════════
        # 设计：只在"有事"时触发，日常不影响工作
        # - 收到集结信号后，成员暂停工作，向集结点移动
        # - 到达后如果敌人在场，可能触发仇恨并加入战斗
        # - 集结时间结束后恢复正常工作
        if self._enqueue_org_rally(npc, all_npcs):
            return
        
        # ══════════════════════════════════════════════════════════════
        # 优先级 4: 跟随/指令模式
        # ══════════════════════════════════════════════════════════════
        if npc.ai_mode == "IDLE":
            npc.action_queue.clear()
            npc.action_queue.enqueue(Stay(reason="原地待命"))
            return
        elif npc.ai_mode == "FOLLOW":
            self._enqueue_follow_player(npc, all_npcs)
            return
        
        # ══════════════════════════════════════════════════════════════
        # 优先级 5: 生存需求（饥饿/寒冷）
        # ══════════════════════════════════════════════════════════════
        if self._enqueue_survival(npc, all_buildings, world_map):
            return

        # ══════════════════════════════════════════════════════════════
        # 优先级 5.3: 夜间休息（戌~寅时回家睡觉）
        # ══════════════════════════════════════════════════════════════
        if self._should_sleep(npc):
            if self._enqueue_sleep(npc):
                return

        # ══════════════════════════════════════════════════════════════
        # 优先级 5.5: 贴身护卫（只有BODYGUARD才在这里跟随）
        # ══════════════════════════════════════════════════════════════
        # 设计理念：
        #   - BODYGUARD：贴身跟随领导，不做其他工作
        #   - MEMBER：优先执行职业逻辑，只有"有事"时才集结
        #   - "有事"的定义：组织成员被攻击 → 通过事件系统触发集结
        org_role = getattr(npc, 'org_role', None)
        if org_role == 'BODYGUARD':
            # 护卫优先跟随领导（这是他的"工作"）
            if self._enqueue_bodyguard(npc, all_npcs): return
        # MEMBER 不在这里跟随！他们应该去做自己的职业工作
        
        # ══════════════════════════════════════════════════════════════
        # 优先级 5.6: 首领招募逻辑【阶段3】
        # ══════════════════════════════════════════════════════════════
        if org_role == 'LEADER':
            if self._enqueue_leader_recruit(npc, all_npcs, all_buildings, world_map):
                return
        
        # ══════════════════════════════════════════════════════════════
        # 优先级 6: 职业行为（原子行为组合模式）
        # ══════════════════════════════════════════════════════════════
        # 使用职业行为注册表来获取并执行职业逻辑
        # 这是新的统一入口，取代了之前的 _enqueue_xxx 方法
        from src.ai.job_behaviors.registry import get_job_behavior
        
        job_behavior = get_job_behavior(npc.job, self)
        if job_behavior:
            context = {
                'all_npcs': all_npcs,
                'all_buildings': all_buildings,
                'world_map': world_map,
                'dt_ms': getattr(self, '_dt_ms', 16),
                'combat_manager': self.combat_manager,
                'day_progress': getattr(self, '_day_progress', 0.0),
            }
            if job_behavior.execute(npc, context):
                return
        
        # ══════════════════════════════════════════════════════════════
        # 优先级 7: 默认漫游（职业行为未处理时的兜底）
        # ══════════════════════════════════════════════════════════════
        # 职业行为已在上面处理，这里只是兜底
        job_roam_reason = {
            'OFFICIAL': '巡视', 'GUARD': '巡逻', 'MERCHANT': '揽客',
            'FARMER': '闲逛', 'SCHOLAR': '散步', 'MONK': '化缘',
            'ARTISAN': '休息', 'BANDIT': '踩点', 'THUG': '游荡',
        }
        roam_reason = job_roam_reason.get(npc.job, '散步')
        
        # 山贼只在城外漫游
        if npc.job in ['BANDIT', 'THUG']:
            bandit_zones = getattr(world_map, 'bandit_zones', None)
            if bandit_zones:
                zone_key = random.choice(['NORTH', 'SOUTH', 'WEST'])
                roam_rect = bandit_zones[zone_key]
            else:
                roam_rect = world_map.slum_rect
            npc.action_queue.enqueue(Roam(roam_rect, duration_ms=5000, reason=roam_reason))
        else:
            npc.action_queue.enqueue(Roam(world_map.city_rect, duration_ms=5000, reason=roam_reason))


    # ---- 夜间休息系统 ----
    # 夜间时段：戌时(10/12)到寅末(3/12)，即约19:00~05:00
    # 豁免职业：匪盗夜间活动（GUARD不再整体豁免，护卫型GUARD也要睡觉）
    NIGHT_JOBS_EXEMPT = set()  # 所有NPC夜间都要休息

    def _is_nighttime(self):
        """检查当前是否是夜间（戌~寅时）"""
        p = getattr(self, '_day_progress', 0.0)
        return p >= 10 / 12 or p < 3 / 12  # 戌时(19:00)到寅末(05:00)

    def _should_sleep(self, npc):
        """判断NPC是否应该去睡觉"""
        if not self._is_nighttime():
            return False
        if npc.job in self.NIGHT_JOBS_EXEMPT:
            return False
        if getattr(npc, 'home_building', None) is None:
            return False
        if getattr(npc, 'is_follower', False):
            return False
        return True

    def _enqueue_sleep(self, npc):
        """让NPC回家睡觉"""
        from src.atomic_actions import MoveToPosition, Stay, MoveToBuilding

        home = getattr(npc, 'home_building', None)
        if home is None:
            return False

        # 已经堆叠在家上 → 保持不动
        if npc.stack_parent == home:
            npc.action_queue.clear()
            npc.ai_reason = "睡觉中"
            npc.action_queue.enqueue(Stay(reason="睡觉中"))
            return True

        hx, hy = home.rect.centerx, home.rect.centery
        dist = math.hypot(npc.rect.centerx - hx, npc.rect.centery - hy)

        if dist > 50:
            # 还没到家，走回去（用MoveToPosition避免MoveToBuilding的抢占弹开循环）
            npc.action_queue.clear()
            npc.action_queue.enqueue(MoveToPosition(hx, hy, reason="回家休息"))
            npc.ai_reason = "回家中"
            return True
        else:
            # 到家附近了
            # 如果建筑已被其他人占据，就在附近待着（共享建筑场景）
            if home.stack_child is not None and home.stack_child != npc:
                npc.action_queue.clear()
                npc.ai_reason = "睡觉中"
                npc.action_queue.enqueue(Stay(reason="睡觉中"))
                return True
            # 堆叠上去
            from src.definitions import STACK_OFFSET_Y
            if npc.stack_parent:
                npc.stack_parent.stack_child = None
            npc.stack_parent = home
            home.stack_child = npc
            npc.set_pos(home.rect.centerx, home.rect.centery + STACK_OFFSET_Y)
            npc.action_queue.clear()
            npc.ai_reason = "睡觉中"
            npc.action_queue.enqueue(Stay(reason="睡觉中"))
            return True


    # ---- 阵营判断（job 优先，tag 仅辅助） ----
    # VILLAIN tag 只表示人品差，不代表会主动攻击好人；
    # 真正会主动战斗的是 job=BANDIT/THUG
    HOSTILE_JOBS  = {'BANDIT', 'THUG'}           # 主动攻击方
    NEUTRAL_JOBS  = {'OFFICIAL', 'GUARD', 'FARMER', 'MERCHANT',
                     'SCHOLAR', 'MONK', 'ARTISAN', 'NONE', 'PLAYER'}  # 平民/官府方

    def _is_villain(self, npc):
        """只凭 job 判断是否是反派阵营，忽略 VILLAIN tag（tag 只影响剧情/事件）"""
        return npc.job in self.HOSTILE_JOBS

    def _find_enemy(self, me, all_npcs):
        """
        仇恨系统索敌逻辑：
        1. 优先返回已锁定的 aggro_target（目标有效则直接追击，无需重新扫描）
        2. 否则扫描范围内所有潜在敌人，给山贼施加基础仇恨，并返回仇恨最高且超过阈值的目标
        3. 仇恨相同时按"就近+财富"打分排序
        4. 【新增】如果NPC是黑风寨成员且玩家被黑风寨悬赏，则对玩家施加仇恨
        """
        my_is_villain = self._is_villain(me)
        
        # 【新增】获取玩家和悬赏系统引用
        player = next((x for x in all_npcs if getattr(x, 'job', '') == 'PLAYER'), None)
        faction_war = getattr(self, '_faction_war_ref', None)

        # --- 步骤1：已锁定目标则直接复用，避免每帧全量扫描 ---
        if me.aggro_target is not None:
            t = me.aggro_target
            # 验证目标依然有效（活着、在感知范围内）
            if t.safety not in [SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED]:
                dist = math.hypot(me.rect.centerx - t.rect.centerx, me.rect.centery - t.rect.centery)
                if dist <= self.scan_radius * 1.5:  # 追击范围比索敌范围略大，防止频繁脱战
                    return t
            # 目标无效，解锁并清除战斗锚点（准备下一场战斗时重新计算）
            me.aggro_target = None
            me.combat_anchor_x = None
            me.combat_anchor_y = None

        # --- 步骤2：空间哈希查询范围内的潜在敌人，更新仇恨表 ---
        # 【性能优化】从 O(n) 降到 O(k)，k = 邻近 NPC 数量
        candidates = []  # [(npc, hate_value, score)]
        
        # [逻辑] 获取城区范围，用于限制守卫/官差的攻击范围
        world_map = getattr(me, '_world_map_ref', None)
        city_rect = world_map.city_rect if world_map else None
        my_is_guard = me.job in ('GUARD', 'OFFICIAL', 'SOLDIER')
        
        # 【空间哈希】只获取扫描范围内的 NPC
        nearby_npcs = self._spatial_hash.query_radius(me, self.scan_radius)

        for other in nearby_npcs:
            # query_radius 已排除自己和超出范围的实体
            if other.safety in [SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED]: continue
            
            # 计算精确距离（用于后续打分）
            dist = math.hypot(me.rect.centerx - other.rect.centerx, me.rect.centery - other.rect.centery)

            other_is_villain = self._is_villain(other)

            # 判断是否属于潜在敌对方（纯以 job 阵营划分，VILLAIN tag 不参与）
            is_potential_enemy = False
            if my_is_villain:
                if not other_is_villain: is_potential_enemy = True
            else:
                if other_is_villain: is_potential_enemy = True

            if not is_potential_enemy: continue
            
            # [逻辑] 守卫/官差不主动追击城外的山贼（除非山贼进城）
            # 这避免了守卫在城墙边巡逻时跑到城外打架
            if my_is_guard and city_rect and other_is_villain:
                other_in_city = city_rect.collidepoint(other.rect.centerx, other.rect.centery)
                if not other_in_city:
                    # 山贼在城外，守卫不追击（除非山贼正在攻击守卫）
                    if me.id not in getattr(other, 'hatred', {}):
                        continue  # 山贼没仇恨我，我也不管他

            # 山贼对范围内所有好人施加持续基础仇恨（体现主动侵略性）
            if my_is_villain:
                # [策略] A+B组合策略
                # A) 山贼主要在城外活动（见上面漫游逻辑）
                # B) 山贼进城时处于"潜伏模式"，不主动攻击城内平民
                # 只有当目标也在城外时，山贼才会施加仇恨（城外对城外 OK）
                # 这样山贼可以偶尔溜进城里踩点，但不会冒然开打被群殴
                me_in_city = city_rect.collidepoint(me.rect.centerx, me.rect.centery) if city_rect else True
                other_in_city = city_rect.collidepoint(other.rect.centerx, other.rect.centery) if city_rect else True
                
                # [逻辑] 只有双方都在城外时，山贼才主动施加仇恨
                # 城内的山贼进入"潜伏模式"，不攻击平民（除非被攻击或有悬赏仇恨）
                if not me_in_city and not other_in_city:
                    # 双方都在城外 → 山贼主动施加仇恨（正常的野外劫道行为）
                    # [机制] 添加冷却机制：同一个目标每 5 秒才累加一次仇恨，避免瞬间拉满
                    if not hasattr(me, '_passive_hate_cd'):
                        me._passive_hate_cd = {}
                    
                    current_time = pygame.time.get_ticks()
                    last_hate_time = me._passive_hate_cd.get(other.id, 0)
                    
                    if current_time - last_hate_time > 5000:  # 5秒冷却
                        me._passive_hate_cd[other.id] = current_time
                        passive_hate = 8  # [调整] 降低单次仇恨（从15降到8），需要多次接触才会攻击
                        me.hatred[other.id] = me.hatred.get(other.id, 0) + passive_hate
                # else: 山贼在城内，或目标在城内 → 不主动攻击（潜伏模式）
                # 注：被攻击后的反击仇恨由战斗系统处理，不受此限制
            
            # 【新增】悬赏系统：黑风寨成员对被悬赏的玩家施加仇恨
            if player and other == player and faction_war:
                me_org = getattr(me, 'org_id', '')
                # 检查玩家是否被黑风寨悬赏
                if me_org == 'heifeng_zhai' or me.job in ['BANDIT', 'THUG']:
                    total_bounty, bounties = faction_war.get_bounty_on_player(player)
                    for bounty in bounties:
                        if bounty.get('issuer_org') == 'heifeng_zhai' and bounty.get('active', True):
                            # 黑风寨成员看到被本寨悬赏的玩家，立即施加高仇恨
                            bounty_hate = 50  # 高仇恨，立即锁定
                            me.hatred[other.id] = me.hatred.get(other.id, 0) + bounty_hate
                            break

            current_hate = me.hatred.get(other.id, 0)

            # 计算同值优先级打分：就近+财富（距离越近分越高；财富越多分越高）
            dist_score = max(0, self.scan_radius - dist)  # 距离近 -> 分高
            wealth = other.inventory.get('铜钱', 0) if hasattr(other, 'inventory') else 0
            wealth_score = min(wealth * 0.5, 50)  # 财富上限贡献50分，避免完全忽略距离
            tie_score = dist_score + wealth_score

            candidates.append((other, current_hate, tie_score))

        if not candidates:
            return None

        # --- 步骤3：找仇恨最高且超过阈值的目标；同值取 tie_score 最高者 ---
        # 按 (hate_value DESC, tie_score DESC) 排序
        candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
        best_npc, best_hate, _ = candidates[0]

        if best_hate >= me.aggro_threshold:
            me.aggro_target = best_npc  # 锁定目标
            return best_npc

        return None
    
    def _handle_follow(self, npc, all_npcs, world_map):
        player = next((x for x in all_npcs if x.job == 'PLAYER'), None)
        if player:
            dist = math.hypot(npc.rect.centerx - player.rect.centerx, npc.rect.centery - player.rect.centery)
            follow_dist = 90 
            if dist > follow_dist + 20: # 保持距离
                npc.ai_reason = "跟随中"
                npc.state = STATE_MOVING
                offset_dir = -1 if npc.rect.centerx < player.rect.centerx else 1
                
                # 尝试计算目标点
                tx = player.rect.centerx + (offset_dir * follow_dist)
                ty = player.rect.centery
                
                # 防卡墙检测
                target_rect = pygame.Rect(tx, ty, npc.rect.width, npc.rect.height)
                if world_map.is_blocked(target_rect):
                    # 如果这一侧被挡住了，尝试另一侧
                    tx = player.rect.centerx - (offset_dir * follow_dist)
                    target_rect.x = tx
                    if world_map.is_blocked(target_rect):
                        # 如果两侧都挡住了，就只好紧贴玩家（或者直接设为玩家位置让物理引擎挤开）
                        tx = player.rect.centerx
                
                npc.set_movement_target(tx, ty, "跟随中")
                npc.clear_target_obj("跟随不产生堆叠")
                
            else:
                npc.state = STATE_IDLE
                npc.clear_movement_target("护卫在侧")
                npc.ai_reason = "护卫在侧"
        return

    # ---- 战斗参数常量 ----
    COMBAT_FACE_DIST     = 55   # 双方面对面保持的间距(px)，不重叠
    COMBAT_ATTACK_RANGE  = 85   # 出拳判定范围（比 FACE_DIST 宽裕 30px，防止弹开后卡边界）
    SPECTATE_RADIUS_MIN  = 160  # 围观最小半径（扩大）
    SPECTATE_RADIUS_MAX  = 310  # 围观最大半径（与constants.py统一）

    # ── 战斗状态标记（NPC 自身属性，通过 getattr 访问）────────────────
    # npc.in_combat = True/False  : 是否处于战斗中（覆盖 STATE_MOVING 等短暂状态）
    # npc.spectate_src_x/y        : 正在围观的战斗中心坐标（广播来的）
    # npc.spectate_anchor_set     : 是否已到达围观位

    def _broadcast_combat_start(self, attacker, defender):
        """
        首次出拳时，向周围广播"战斗开始"事件。
        只广播一次：通过检查 npc.in_combat 标记避免重复。
        """
        if getattr(attacker, 'in_combat', False):
            return  # 已广播过，不重复
        self.broadcast_combat_start(attacker, defender)

    def broadcast_combat_start(self, attacker, defender, all_npcs=None):
        """
        公开接口：战斗开始时立即广播给范围内所有 NPC（一次性）。
        不再持续存在，收到的收到，没收到的就算了。
        """
        cx = (attacker.rect.centerx + defender.rect.centerx) // 2
        cy = (attacker.rect.centery + defender.rect.centery) // 2
        
        evt = {
            'type': 'COMBAT_START',
            'cx': cx, 'cy': cy,
            'source_ids': {attacker.id, defender.id},
            'combatant_names': f"{attacker.name} vs {defender.name}"
        }
        
        attacker.in_combat = True
        defender.in_combat = True
        
        # 立即范围广播：扫描所有 NPC，符合条件的直接投递事件
        if all_npcs:
            count = self._broadcast_to_range(evt, all_npcs)
            log_game_event(
                f"[BROADCAST] 战斗开始 {attacker.name} vs {defender.name}"
                f"  中心=({cx},{cy})  通知了{count}个围观者", tag="AI")
        else:
            log_game_event(
                f"[BROADCAST] 战斗开始 {attacker.name} vs {defender.name}"
                f"  中心=({cx},{cy})  但无 NPC 列表，无法广播", tag="AI")

    def broadcast_combat_end(self, winner, loser, all_npcs=None):
        """
        公开接口：战斗结束时立即广播给所有围观者（一次性）。
        """
        cx = (winner.rect.centerx + loser.rect.centerx) // 2
        cy = (winner.rect.centery + loser.rect.centery) // 2
        
        evt = {
            'type': 'COMBAT_END',
            'cx': cx, 'cy': cy,
            'source_ids': {winner.id, loser.id}
        }
        
        winner.in_combat = False
        
        # 【新增】将战斗结果注入NPC记忆系统
        try:
            from src.llm.event_memory_bridge import inject_combat_memory
            # 判断战斗结果
            if loser.safety == SAFETY_DEAD:
                result = "被杀死了"
            elif loser.safety == SAFETY_DOWNED:
                result = "重伤倒地"
            else:
                result = "落败逃走"
            inject_combat_memory(winner, loser, result, all_npcs, (cx, cy))
        except Exception as e:
            log_game_event(f"[BROADCAST] 战斗记忆注入失败: {e}", tag="AI")
        
        # 立即范围广播
        if all_npcs:
            count = self._broadcast_to_range(evt, all_npcs)
            log_game_event(
                f"[BROADCAST] 战斗结束 胜者={winner.name}"
                f"  中心=({cx},{cy})  通知了{count}个围观者散去", tag="AI")
        else:
            log_game_event(
                f"[BROADCAST] 战斗结束 胜者={winner.name}"
                f"  中心=({cx},{cy})  但无 NPC 列表，无法广播", tag="AI")

    def _broadcast_combat_end(self, winner, loser, all_npcs=None):
        """内部调用：战斗结束时广播散去事件"""
        if all_npcs is None:
            all_npcs = getattr(self, '_current_npcs', None)
        self.broadcast_combat_end(winner, loser, all_npcs)

    def _broadcast_to_range(self, evt, all_npcs) -> int:
        """
        立即范围广播：扫描所有 NPC，距离合适的直接投递事件到其 _event_queue。
        返回通知的 NPC 数量。
        """
        cx, cy = evt['cx'], evt['cy']
        source_ids = evt.get('source_ids', set())
        count = 0
        
        for npc in all_npcs:
            if npc.job == 'PLAYER':
                continue
            if npc.id in source_ids:
                continue   # 当事人不接收自己的广播
                
            dist = math.hypot(npc.rect.centerx - cx, npc.rect.centery - cy)
            if dist > self.SPECTATE_NOTICE_RADIUS:
                continue   # 距离太远
                
            # 符合条件 → 直接投递
            self.push_event(npc, evt)
            count += 1
            
        return count

    def _execute_combat(self, npc, target, world_map):
        """
        战斗执行（Stacklands 风格）：
        双方互相逼近并停在 COMBAT_FACE_DIST px 处"对碰"，
        不进入对方卡牌范围，攻击冷却期原地站立。

        关键设计：整个战斗过程中，包括弹开/追击等子状态，
        npc.in_combat 始终保持 True，这样旁观者不依赖 npc.state
        来判断战斗是否结束，而是依赖广播事件。
        """
        # 如果 NPC 正堆叠在建筑上（干活中），先弹出再战斗
        if npc.stack_parent is not None:
            from src.entities.building import Building
            if isinstance(npc.stack_parent, Building):
                npc.bounce_off(npc.stack_parent)
                npc.is_working = False
                npc.work_timer = 0
                npc.ai_reason = "被迫应战"
        
        # 如果 NPC 正在背人，先放下伤员再战斗
        if npc.stack_child is not None:
            patient = npc.stack_child
            if isinstance(patient, NPC) and patient.safety == SAFETY_DOWNED:
                # 放下伤员到安全位置
                npc.stack_child = None
                patient.stack_parent = None
                # 将伤员放在救援者旁边，避开战斗区域
                offset_x = random.choice([-60, 60])  # 随机左右
                offset_y = random.choice([-40, 40])  # 随机上下
                patient.set_pos(npc.rect.centerx + offset_x, npc.rect.centery + offset_y)
                patient.ai_reason = f"被{npc.name}紧急放下"
                npc.ai_reason = "放下伤员迎战"
                log_game_event(
                    f"[AI][COMBAT] {npc.name} 被攻击，紧急放下 {patient.name} 准备应战", 
                    tag="COMBAT")

        # ── 目标已倒地/死亡 → 战斗结束，广播散去，清理状态 ──────────
        if target.safety in [SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED]:
            # 无论 in_combat 状态如何都广播结束：
            # 目标可能是被玩家打倒的（外部触发），此时 npc.in_combat 仍为 False，
            # 但广播事件必须清除，否则围观者永远不散。
            self._broadcast_combat_end(npc, target)
            npc.aggro_target = None
            npc.combat_anchor_x = None
            npc.combat_anchor_y = None
            npc.in_combat = False
            npc.state = STATE_IDLE
            npc.clear_movement_target("对手倒地")
            npc.ai_reason = "对手倒地"
            log_game_event(
                f"[AI][VICTORY] {npc.name} 目标 {target.name} 已倒地，解除战斗",
                tag="AI")
            return

        dist = math.hypot(target.rect.centerx - npc.rect.centerx,
                          target.rect.centery - npc.rect.centery)

        # 在目标方向上，离目标 COMBAT_FACE_DIST 处是我的"站位点"
        if dist > 0:
            dx = (npc.rect.centerx - target.rect.centerx) / dist
            dy = (npc.rect.centery - target.rect.centery) / dist
        else:
            dx, dy = 1.0, 0.0

        stand_x = target.rect.centerx + dx * self.COMBAT_FACE_DIST
        stand_y = target.rect.centery + dy * self.COMBAT_FACE_DIST

        # ── 击退硬直中：state 强制锁为 STATE_COMBAT，不让外部看到 STATE_MOVING ──
        # 这样 npc.state 在整个战斗期间（含弹开/追击）都是 STATE_COMBAT，
        # 旁观者用 npc.in_combat 广播标记更可靠，但 state 也不会再误导任何人。
        if npc.knockback_timer > 0:
            # [!] 新方案：knockback 位移由 movement_system 通过 knockback_tx/ty 独立处理，
            # 这里只需锁住状态，不再写 target_x/y（否则会重新污染 AI 寻路目标）
            npc.state = STATE_COMBAT
            npc.ai_reason = "弹开中"
            return

        if dist > self.COMBAT_ATTACK_RANGE:
            # 还未到位 → 逼近站位点
            # [!] 关键修复：追击时也保持 STATE_COMBAT，不切换为 STATE_MOVING
            npc.state = STATE_COMBAT
            npc.ai_reason = f"追击{target.name}"
            npc.set_movement_target(stand_x, stand_y, f"追击{target.name}")
            if not getattr(npc, 'combat_anchor_x', None):
                npc.combat_anchor_x = npc.rect.centerx
                npc.combat_anchor_y = npc.rect.centery
        else:
            # 已到位 → 停下、出拳
            npc.state = STATE_COMBAT
            npc.clear_movement_target("决策树-到达战斗位置")
            npc.ai_reason = "战斗中"

            if not getattr(npc, 'combat_anchor_x', None):
                npc.combat_anchor_x = stand_x
                npc.combat_anchor_y = stand_y

            if npc.attack_cooldown <= 0:
                log_game_event(
                    f"[AI][READY] {npc.name}({npc.rect.centerx},{npc.rect.centery})"
                    f" 攻击就绪 → {target.name}  dist={dist:.1f}",
                    tag="AI")
                # 战斗开始广播已移至 combat_system.apply_melee_attack()
                all_npcs = getattr(self, '_current_npcs', [])
                all_cards_for_combat = all_npcs  # 战斗系统只需要 NPC 列表即可筛选
                self.combat_manager.apply_melee_attack(npc, target, all_cards_for_combat)
                npc.attack_cooldown = npc.atk_speed

    # 围观感知半径（扩大：让更远的人也能听闻战斗）
    SPECTATE_NOTICE_RADIUS = 600   # 听闻战斗广播事件的最大距离（原380→600）

    def _handle_bystander(self, npc, all_npcs):
        """
        围观逻辑（中断模型下的纯状态处理）：
        
        在新的中断模型下，事件处理已经全部移到 _process_events 中完成。
        这个方法现在只负责处理"已经接收到围观事件"的NPC的行为状态。
        
        当 NPC 收到 COMBAT_START 事件时，_process_events 会设置：
        - npc.spectate_src_x/y：围观中心坐标
        
        当 NPC 收到 COMBAT_END 事件时，_process_events 会清除围观状态。
        
        这个方法只负责让"正在围观中"的NPC朝围观位走过去或驻足。
        
        返回 True 表示接管了本帧决策。
        """
        # ── 检查是否有围观中心（由 _process_events 设置）──────────
        cx = getattr(npc, 'spectate_src_x', None)
        cy = getattr(npc, 'spectate_src_y', None)
        if cx is None:
            return False   # 没收到过围观事件，不围观

        # ── 如果在建筑内工作，先弹出 ────────────────────────────
        if npc.stack_parent is not None:
            from src.entities.building import Building
            if isinstance(npc.stack_parent, Building):
                npc.bounce_off(npc.stack_parent)
                npc.is_working = False
                npc.work_timer = 0

        # ── 计算本 NPC 专属围观站位（基于 id 黄金角，避免扎堆）──
        # 扩大到5圈：160→190→220→250→280→310 px，每圈容纳更多旁观者
        npc_id = getattr(npc, 'id', -1)
        id_angle_base = (npc_id * 137.5) % 360
        layer = npc_id % 5  # 5圈（原3圈）
        r_base = self.SPECTATE_RADIUS_MIN + layer * 32

        target_sx, target_sy = None, None
        for attempt in range(8):
            angle = math.radians(id_angle_base + attempt * 45) + random.uniform(-0.15, 0.15)
            r = r_base + random.randint(0, 20)
            tx = cx + math.cos(angle) * r
            ty = cy + math.sin(angle) * r
            test_rect = npc.rect.copy()
            test_rect.center = (int(tx), int(ty))
            if not (hasattr(npc, '_world_map_ref') and npc._world_map_ref and
                    npc._world_map_ref.is_blocked(test_rect)):
                target_sx, target_sy = tx, ty
                break
        if target_sx is None:
            target_sx = cx + math.cos(math.radians(id_angle_base)) * r_base
            target_sy = cy + math.sin(math.radians(id_angle_base)) * r_base

        # ── 已到围观位 → 驻足 ────────────────────────────────────
        dist_to_slot = math.hypot(
            npc.rect.centerx - target_sx, npc.rect.centery - target_sy)
        if dist_to_slot < 30:
            npc.state = STATE_IDLE
            npc.clear_movement_target("决策树-已到围观位")
            npc.ai_reason = "围观中"
            npc.spectate_anchor_set = True
            return True

        # ── 走向围观位 ────────────────────────────────────────────
        npc.state = STATE_MOVING
        npc.set_movement_target(target_sx, target_sy, "赶去围观")
        npc.clear_target_obj("围观不产生堆叠")
        npc.ai_reason = "赶去围观"
        npc.spectate_anchor_set = True
        return True
    # 救援感知距离（扩大：让更多NPC主动去救援重伤员）
    RESCUE_NOTICE_RADIUS = 500  # 专业救援职业感知距离（原300→500）
    def _handle_carry_delivery(self, npc, all_buildings, world_map):
        """背着人去医馆"""
        clinic = next((b for b in all_buildings if b.building_type == 'CLINIC'), None)
        
        if clinic:
            # [调试] 增加详细调试信息
            patient_name = npc.stack_child.name if npc.stack_child else "未知"
            dist = math.hypot(npc.rect.centerx - clinic.rect.centerx,
                              npc.rect.centery - clinic.rect.centery)
         
            npc.ai_reason = f"送往医馆(背着{patient_name})"
            npc.state = STATE_CARRYING
            # 判断是否到达医馆（用60px避免因卡牌宽度导致永远触达不了）
            if dist < 60:
                # 放下伤员到医馆队列
                patient = npc.stack_child
                if patient:
                    npc.stack_child = None
                    patient.stack_parent = None
                    patient.clear_movement_target("送医到达-清除目标点")
                    patient.ai_reason = f"已送达医馆(由{npc.name}背来)"

                    # 找医馆堆叠链的最末端
                    last_card = clinic
                    loop_safe = 0
                    while last_card.stack_child and loop_safe < 20:
                        last_card = last_card.stack_child
                        loop_safe += 1

                    last_card.stack_child = patient
                    patient.stack_parent = last_card
                    patient.set_pos(last_card.rect.centerx,
                                    last_card.rect.centery + STACK_OFFSET_Y)
                    npc.ai_reason = "已送达"
                    npc.state = STATE_IDLE
                    npc.clear_movement_target("背人-医馆到达")
                    log_game_event(f"[DBG送医完成] {npc.name} 成功送达{patient.name}到医馆，清除移动目标", tag="AI")
            else:
                # [关键] 确保设置医馆为目标点
                npc.set_movement_target(clinic.rect.centerx, clinic.rect.centery, f"送往医馆(背着{patient_name})")
        else:
            # 没有医馆：直接将伤员放下，救援者原地待命（避免循环引用）
            npc.ai_reason = "无医馆，就地放下"
            patient = npc.stack_child
            if patient:
                npc.stack_child = None
                patient.stack_parent = None
                # 将伤员放在旁边，等待自然恢复或玩家处理
                patient.set_pos(npc.rect.centerx + 60, npc.rect.centery)
                npc.state = STATE_IDLE
                npc.clear_movement_target("无医馆-就地放下")
            print(f"[DBG无医馆] {npc.name} 找不到医馆，就地放下伤员")
    # ── 勒索冷却常量（ms）──
    EXTORT_COOLDOWN_MS = 15_000   # 每次成功勒索后 15 秒内不重复，防止无限扣钱
    ARTISAN_PRODUCTS = {
        '精制器物': (15, '工匠'),
        '铁器':    (20, '工匠'),
        '布料':    (10, '工匠'),
    }
    # 饥饿/寒冷触发阈值（超过此值才会去市场）
    SURVIVAL_HUNGER_THRESHOLD = 40   # hunger > 40 → 去买粮（降低阈值，更早触发）
    SURVIVAL_COLD_THRESHOLD   = 40   # cold   > 40 → 去买棉袄（降低阈值，更早触发）

    def _handle_survival_needs(self, npc, all_buildings, world_map):
        """
        生存需求驱动（仅处理到达市场后的购买逻辑）：
        注意：移动逻辑已移至 _enqueue_survival，此方法只处理购物交易
        
        【阶段2更新】使用 economy_system 的价格系统，记录消费
        
        返回 True 表示购买成功
        """
        from src.item_system import ItemManager
        from src.economy_system import get_market_price_system
        
        item_sys = ItemManager.get_instance()
        price_sys = get_market_price_system()

        # ── 1. 判断是否有生存需求 ──────────────────────────────────
        # 饥饿或寒冷时都去买食物（因为食物可以同时缓解饥饿和寒冷）
        needs_food = (npc.hunger > self.SURVIVAL_HUNGER_THRESHOLD or
                      npc.cold > self.SURVIVAL_COLD_THRESHOLD) and \
                      not any(item_sys.is_food(iid) for iid in npc.inventory)
        needs_coat = (npc.cold > self.SURVIVAL_COLD_THRESHOLD and
                      npc.equip_clothing is None and
                      not any(item_sys.is_clothing(iid) for iid in npc.inventory))

        if not needs_food and not needs_coat:
            return False  # 无需求

        # ── 2. 找市场建筑并检查距离 ─────────────────────────────────
        market = next((b for b in all_buildings if b.building_type == 'MARKET'), None)
        if market is None:
            return False  # 没有市场，无法购物

        dist = math.hypot(npc.rect.centerx - market.rect.centerx,
                          npc.rect.centery - market.rect.centery)

        if dist > 60:
            # 还没到市场，由 _enqueue_survival 处理移动
            return False

        # ── 3. 到达市场 → 尝试购买 ───────────────────────────────
        # 统一使用 npc.money 作为货币（与薪资系统保持一致）
        coins = npc.money

        if needs_food:
            # 【阶段2】使用动态价格系统获取当前价格
            price = price_sys.get_price(ITEM_GRAIN, is_buy=True)
            market_grain = market.inventory.get(ITEM_GRAIN, 0)

            if market_grain > 0 and coins >= price:
                # 成交：NPC 付钱，获得粮食并立即吃掉
                npc.money -= price
                market.inventory[ITEM_GRAIN] -= 1
                if market.inventory[ITEM_GRAIN] <= 0:
                    del market.inventory[ITEM_GRAIN]
                market.inventory[ITEM_COIN] = market.inventory.get(ITEM_COIN, 0) + price
                
                # 【阶段2】记录销售到价格系统（增加需求信号）
                price_sys.record_sale(ITEM_GRAIN, 1)
                
                # 立刻吃掉：降低饥饿度和寒冷度（每份粮食降30饥饿+15寒冷）
                npc.hunger = max(0, npc.hunger - 30)
                npc.cold = max(0, npc.cold - 15)  # 食物也提供保暖效果
                npc.ai_reason = f"买粮吃饭(-{price}铜)"
                log_game_event(
                    f"[消费] {npc.name} 花{price}铜买粮 饥饿:{npc.hunger:.0f} 寒冷:{npc.cold:.0f}  "
                    f"市场剩余:{market.inventory.get(ITEM_GRAIN,0)}",
                    tag="ECONOMY")
                return True
            elif market_grain <= 0:
                npc.ai_reason = "市场无粮"
                npc.dissatisfaction += 5  # 买不到东西增加不满
            else:
                npc.ai_reason = f"钱不够({coins}<{price})"

        if needs_coat:
            coat_id = ITEM_CLOTHING  # 使用常量
            # 【阶段2】使用动态价格系统获取当前价格
            price = price_sys.get_price(coat_id, is_buy=True)
            market_coat = market.inventory.get(coat_id, 0)

            if market_coat > 0 and coins >= price:
                npc.money -= price
                market.inventory[coat_id] -= 1
                if market.inventory[coat_id] <= 0:
                    del market.inventory[coat_id]
                market.inventory[ITEM_COIN] = market.inventory.get(ITEM_COIN, 0) + price
                
                # 【阶段2】记录销售
                price_sys.record_sale(coat_id, 1)
                
                # 立刻穿上：先加入背包再装备（equip_item 要求物品在背包里）
                npc.inventory[coat_id] = npc.inventory.get(coat_id, 0) + 1
                npc.equip_item(coat_id)
                npc.cold = max(0, npc.cold - 40)
                npc.ai_reason = f"买棉袄御寒(-{price}铜)"
                log_game_event(
                    f"[消费] {npc.name} 花{price}铜买棉袄 寒冷:{npc.cold:.0f}  "
                    f"市场剩余:{market.inventory.get(coat_id,0)}",
                    tag="ECONOMY")
                return True
            elif market_coat <= 0:
                npc.ai_reason = "市场无棉袄"
                npc.dissatisfaction += 3

        return False  # 到了市场但买不成（缺货/缺钱），不接管后续逻辑
    def _find_bodyguard_leader(self, bodyguard, all_npcs):
        """寻找护卫需要保护的领导者"""
        # 1. 优先从关系数据中找 LEADER 关系
        relations = getattr(bodyguard, 'relations_data', {})
        if relations:
            leader_id = relations.get('LEADER')
            if leader_id:
                leader = next((npc for npc in all_npcs 
                              if getattr(npc, 'id', None) == leader_id), None)
                if leader and leader.safety not in [SAFETY_DEAD, SAFETY_EXILED]:
                    return leader
        
        # 2. 从同组织中找社会等级最高的 LEADER 角色
        org_id = getattr(bodyguard, 'org_id', None)
        if org_id and org_id != 'NONE':
            potential_leaders = []
            for npc in all_npcs:
                if (getattr(npc, 'org_id', None) == org_id and
                    getattr(npc, 'org_role', None) == 'LEADER' and
                    getattr(npc, 'social_level', 0) >= 3 and
                    npc.safety not in [SAFETY_DEAD, SAFETY_EXILED]):
                    potential_leaders.append(npc)
            
            if potential_leaders:
                # 选择社会等级最高的
                return max(potential_leaders, key=lambda x: getattr(x, 'social_level', 0))
        
        return None
    
    # ══════════════════════════════════════════════════════════════
    # 原子行为队列版职业逻辑（_enqueue_* 系列方法）
    # ══════════════════════════════════════════════════════════════
    
    def _enqueue_combat(self, npc, target):
        """入队战斗行为"""
        from src.atomic_actions import Combat
        
        # 已经在战斗这个目标了
        current = npc.action_queue.current
        if current and isinstance(current, Combat) and current.target == target:
            return
        
        # 先清除旧行为，入队战斗
        npc.action_queue.clear()
        npc.action_queue.enqueue(Combat(target, self.combat_manager, reason=f"与{target.name}战斗"))
    
    def _enqueue_rescue(self, npc, all_npcs, all_buildings):
        """入队救援行为，返回True表示找到需要救援的人"""
        from src.atomic_actions import Rescue
        
        # 确定本 NPC 的救援感知距离
        if npc.job in ('MONK', 'GUARD'):
            notice_r = self.RESCUE_NOTICE_RADIUS
        elif npc.job in ('FARMER', 'ARTISAN', 'SCHOLAR', 'OFFICIAL', 'MERCHANT'):
            notice_r = 280
        else:
            notice_r = 250
        
        # 找最近的、无人看护的重伤员
        closest_dist = notice_r
        target_patient = None
        
        for p in all_npcs:
            if p.safety != SAFETY_DOWNED:
                continue
            if p.stack_parent is not None:
                continue
            # 检查是否已有其他人在救
            other_rescuers = [n for n in all_npcs 
                            if n != npc 
                            and hasattr(n, '_rescue_target_id') 
                            and n._rescue_target_id == p.id]
            if other_rescuers:
                continue
            
            d = math.hypot(npc.rect.centerx - p.rect.centerx,
                          npc.rect.centery - p.rect.centery)
            if d < closest_dist:
                closest_dist = d
                target_patient = p
        
        if not target_patient:
            return False
        
        # 热心度判断（非专业救援者有概率跳过）
        if npc.job not in ('MONK', 'GUARD'):
            if getattr(npc, 'combat_anchor_x', None) is not None:
                if random.random() < 0.6:
                    npc.ai_reason = "观望中..."
                    return False
                npc.combat_anchor_x = None
                npc.combat_anchor_y = None
        
        # 找医馆
        clinic = next((b for b in all_buildings if b.building_type == 'CLINIC'), None)
        
        # 入队救援行为
        npc.action_queue.clear()
        npc.action_queue.enqueue(Rescue(target_patient, clinic, reason=f"救援{target_patient.name}"))
        npc._rescue_target_id = target_patient.id
        npc.ai_reason = f"救援{target_patient.name}"
        return True
    
    def _enqueue_spectate(self, npc):
        """入队围观行为，返回True表示需要围观"""
        from src.atomic_actions import Spectate
        
        cx = getattr(npc, 'spectate_src_x', None)
        cy = getattr(npc, 'spectate_src_y', None)
        if cx is None:
            return False
        
        # [优化] 先检查是否已在围观（避免无意义的弹出）
        current = npc.action_queue.current
        if current and isinstance(current, Spectate):
            return True
        
        # 如果在建筑内工作，先弹出
        if npc.stack_parent is not None:
            from src.entities.building import Building
            if isinstance(npc.stack_parent, Building):
                npc.bounce_off(npc.stack_parent)
                npc.is_working = False
                npc.work_timer = 0
        
        # 入队围观行为
        npc.action_queue.clear()
        npc.action_queue.enqueue(Spectate(cx, cy, npc.id, reason="赶去围观"))
        return True
    
    def _enqueue_follow_player(self, npc, all_npcs):
        """入队跟随玩家行为"""
        from src.atomic_actions import FollowTarget
        
        player = next((x for x in all_npcs if x.job == 'PLAYER'), None)
        if not player:
            return
        
        # 检查是否已在跟随
        current = npc.action_queue.current
        if current and isinstance(current, FollowTarget) and current.target == player:
            return
        
        npc.action_queue.clear()
        npc.action_queue.enqueue(FollowTarget(
            target=player,
            stop_dist=70,
            start_dist=110,
            radius=90,
            angle=random.uniform(0, 2 * math.pi),
            keep_follow=True,
            reason="跟随中"
        ))
    
    def _enqueue_survival(self, npc, all_buildings, world_map):
        """入队生存需求行为（去市场买粮/棉袄），返回True表示有需求"""
        from src.atomic_actions import MoveToPosition, Wait
        from src.item_system import ItemManager
        
        # 【修复】土匪/山贼不会去城内市场购物（他们靠抢劫为生）
        if npc.job in ['BANDIT', 'THUG']:
            return False
        
        # 正在背人/救援时不处理
        if npc.state == STATE_CARRYING and npc.stack_child:
            return False
        if hasattr(npc, '_is_rescuing') and npc._is_rescuing:
            return False
        
        item_sys = ItemManager.get_instance()
        
        # 饥饿或寒冷时都去买食物（因为食物可以同时缓解饥饿和寒冷）
        needs_food = (npc.hunger > self.SURVIVAL_HUNGER_THRESHOLD or
                      npc.cold > self.SURVIVAL_COLD_THRESHOLD) and \
                      not any(item_sys.is_food(iid) for iid in npc.inventory)
        needs_coat = (npc.cold > self.SURVIVAL_COLD_THRESHOLD and
                      npc.equip_clothing is None and
                      not any(item_sys.is_clothing(iid) for iid in npc.inventory))
        
        if not needs_food and not needs_coat:
            return False
        
        market = next((b for b in all_buildings if b.building_type == 'MARKET'), None)
        if not market:
            return False
        
        dist = math.hypot(npc.rect.centerx - market.rect.centerx,
                         npc.rect.centery - market.rect.centery)
        
        if dist > 60:
            # 去市场
            npc.action_queue.clear()
            npc.action_queue.enqueue(MoveToPosition(
                market.rect.centerx, market.rect.centery,
                stop_dist=50, reason="去市场购物"
            ))
            return True
        
        # 已到市场 → 执行购买逻辑（这里保留原有逻辑，因为涉及库存操作）
        return self._handle_survival_needs(npc, all_buildings, world_map)
    
    def _enqueue_bodyguard(self, npc, all_npcs):
        """入队护卫跟随行为"""
        from src.atomic_actions import FollowTarget
        
        leader = self._find_bodyguard_leader(npc, all_npcs)
        if not leader:
            return False
        
        # 正常护卫跟随逻辑（拦截检测在 _process_see 中统一处理）
        current = npc.action_queue.current
        if current and isinstance(current, FollowTarget) and current.target == leader:
            return True
        
        npc.action_queue.clear()
        npc.action_queue.enqueue(FollowTarget(
            target=leader,
            stop_dist=60,
            start_dist=90,
            radius=70,
            angle=random.uniform(0, 2 * math.pi),
            keep_follow=True,
            reason=f"护卫{leader.name}"
        ))
        npc.ai_reason = f"护卫{leader.name}"
        return True
    
    def _enqueue_member_follow(self, npc, all_npcs):
        """
        组织普通成员跟随行为
        - 只有当领导在较近范围内时才跟随
        - 跟随距离比护卫更远，更松散
        - 形成"随从团"效果
        """
        from src.atomic_actions import FollowTarget
        
        org_id = getattr(npc, 'org_id', None)
        if not org_id or org_id == 'NONE':
            return False
        
        # 查找同组织的领导
        leader = None
        for other in all_npcs:
            if other == npc: continue
            if other.safety in [SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED]: continue
            if getattr(other, 'org_id', None) != org_id: continue
            if getattr(other, 'org_role', None) != 'LEADER': continue
            
            # 检查距离：只有领导在250像素内才跟随
            dist = math.hypot(npc.rect.centerx - other.rect.centerx, 
                            npc.rect.centery - other.rect.centery)
            if dist < 300:  # 跟随触发距离
                leader = other
                break
        
        if not leader:
            return False  # 领导不在附近，继续做自己的事
        
        # 检查是否已经在跟随
        current = npc.action_queue.current
        if current and isinstance(current, FollowTarget) and current.target == leader:
            return True
        
        # 入队松散跟随（距离比护卫更远）
        npc.action_queue.clear()
        npc.action_queue.enqueue(FollowTarget(
            target=leader,
            stop_dist=100,    # 停止距离更远
            start_dist=150,   # 开始跟随距离更远
            radius=120,       # 散布半径更大
            angle=random.uniform(0, 2 * math.pi),
            keep_follow=True,
            reason=f"随从{leader.name}"
        ))
        npc.ai_reason = f"随从{leader.name}"
        return True

    # ═══════════════════════════════════════════════════════════════════
    # 组织集结：同伴被攻击时前去支援
    # ═══════════════════════════════════════════════════════════════════
    def _enqueue_org_rally(self, npc, all_npcs):
        """
        组织集结行为：
        - 当同组织成员被攻击时，combat_system 设置 _rally_point
        - 成员暂停日常工作，向集结点移动
        - 到达集结点后，如果有敌人在场会自动触发仇恨
        - 集结时间结束后清除状态，恢复正常工作
        """
        from src.atomic_actions import MoveToPosition, Wait
        
        # 检查是否有集结点
        rally_point = getattr(npc, '_rally_point', None)
        if rally_point is None:
            return False
        
        # 递减集结时间
        dt_ms = getattr(self, '_dt_ms', 16)
        rally_time = getattr(npc, '_rally_time', 0) - dt_ms
        npc._rally_time = rally_time
        
        # 集结时间结束 → 清除状态，返回正常工作
        if rally_time <= 0:
            npc._rally_point = None
            npc._rally_org = None
            npc._rally_time = 0
            npc.action_queue.clear()
            npc.ai_reason = "集结结束"
            log_game_event(f"[ORG_RALLY] {npc.name} 集结时间结束，恢复日常", tag="AI")
            return False  # 返回False让后续职业逻辑接管
        
        rx, ry = rally_point
        
        # 计算与集结点的距离
        dist = math.hypot(npc.rect.centerx - rx, npc.rect.centery - ry)
        
        # 已到达集结点附近 → 原地等待/观察
        if dist < 80:
            # 检查附近是否有敌人（可能触发战斗）
            # 这里不主动搜索敌人，让 _find_enemy 的仇恨系统处理
            current = npc.action_queue.current
            if current and isinstance(current, Wait):
                return True  # 继续等待
            
            npc.action_queue.clear()
            npc.action_queue.enqueue(Wait(duration_ms=3000, reason="集结待命"))
            npc.ai_reason = "集结待命"
            return True
        
        # 未到达 → 向集结点移动
        current = npc.action_queue.current
        if current and isinstance(current, MoveToPosition):
            # 已经在移动中
            return True
        
        npc.action_queue.clear()
        npc.action_queue.enqueue(MoveToPosition(rx, ry, stop_dist=60, reason="支援同伴"))
        npc.ai_reason = "支援同伴"
        log_game_event(f"[ORG_RALLY] {npc.name} 向集结点({rx},{ry})移动", tag="AI")
        return True

    # ═══════════════════════════════════════════════════════════════════
    # 阶段1：完善职业行为系统
    # ═══════════════════════════════════════════════════════════════════
    
    # ── 学者 (SCHOLAR) ─────────────────────────────────────────────────
    # 工作循环：学堂著书 → 产出书卷 → 卖给市场或茶馆论道
    # 日收入：3-10铜（卖书）
    # 产出：书卷（ITEM_BOOK）
    
    SCHOLAR_WORK_TIME_MS = 20000    # 在学堂工作20秒产出1本书
    SCHOLAR_BOOK_PRICE = 8          # 每本书卷售价8铜
    
    # ── 官员 (OFFICIAL) ────────────────────────────────────────────────
    # 工作循环：官府办公 → 巡视城区
    # 收入来源：【阶段3】组织日薪系统统一发放（每日结算时由 pay_daily_salaries 处理）
    # 特性：不在工作中直接发俸禄，改为日结薪俸
    
    OFFICIAL_WORK_CYCLE_MS = 30000  # 办公周期（30秒后可外出巡视）
    
    # ── 僧侣 (MONK) ────────────────────────────────────────────────────
    # 工作循环：寺庙诵经 → 城中化缘 → 治病救人
    # 日收入：2-8铜（化缘施舍）
    # 特性：有概率从市民处获得施舍，可治疗重伤者
    
    MONK_CHANT_TIME_MS = 15000      # 诵经时间
    MONK_ALMS_COOLDOWN_MS = 10000   # 化缘冷却
    
    # ── 流民 (NONE) ────────────────────────────────────────────────────
    # 行为循环：乞讨 → 找工作 → 流浪
    # 日收入：0-5铜（乞讨）
    # 特性：有概率被雇佣转职
    
    REFUGEE_BEG_COOLDOWN_MS = 12000  # 乞讨冷却
    REFUGEE_HIRE_CHANCE = 0.02       # 每次决策被雇佣的概率（2%）
    
    # ═══════════════════════════════════════════════════════════════════
    # 阶段3：组织扩张系统 - 首领招募逻辑
    # ═══════════════════════════════════════════════════════════════════
    
    LEADER_RECRUIT_RANGE = 200       # 首领招募范围（需要流民在附近）
    LEADER_RECRUIT_COOLDOWN = 3600   # 招募冷却（60秒）
    
    def _enqueue_leader_recruit(self, npc, all_npcs, all_buildings, world_map):
        """
        首领行为：管理组织，招募流民
        - 检查金库是否充足
        - 寻找附近的流民
        - 尝试招募
        """
        from src.atomic_actions import Wait, MoveToPosition, Roam
        from src.organization_system import get_org_economy
        
        org_id = getattr(npc, 'org_id', None)
        if not org_id or org_id == 'NONE':
            return False
            
        org_economy = get_org_economy()
        
        # 检查招募冷却
        recruit_cd = org_economy.recruit_cooldown.get(org_id, 0)
        if recruit_cd > 0:
            org_economy.recruit_cooldown[org_id] = recruit_cd - 1
            # 冷却中不阻断其他行为
            return False
        
        # 检查金库
        treasury = org_economy.get_treasury(org_id)
        if treasury < 100:
            # 金库不足，不招募
            return False
            
        # 寻找附近的流民
        nearby_refugees = []
        for other in all_npcs:
            if other is npc:
                continue
            if getattr(other, 'job', '') != 'NONE':
                continue
            if not getattr(other, 'is_refugee', False):
                continue
            if getattr(other, 'org_id', None) not in [None, 'NONE']:
                continue
            if other.safety in [SAFETY_DEAD, SAFETY_EXILED, SAFETY_DOWNED]:
                continue
                
            dist = math.hypot(npc.rect.centerx - other.rect.centerx,
                             npc.rect.centery - other.rect.centery)
            if dist <= self.LEADER_RECRUIT_RANGE:
                nearby_refugees.append((other, dist))
        
        if not nearby_refugees:
            # 没有附近的流民
            return False
        
        # 按距离排序，招募最近的
        nearby_refugees.sort(key=lambda x: x[1])
        target_refugee = nearby_refugees[0][0]
        
        # 检查是否可以招募
        can_recruit, reason = org_economy.can_recruit(org_id, target_refugee)
        if not can_recruit:
            return False
        
        # 执行招募
        success, msg = org_economy.recruit_refugee(org_id, target_refugee, npc)
        if success:
            npc.ai_reason = f"招募{target_refugee.name}"
            npc.action_queue.enqueue(Wait(2000, reason=f"招募{target_refugee.name}"))
            return True
        
        return False
    
    def _apply_org_contribution(self, npc, income):
        """
        对NPC收入应用组织贡献扣除
        【阶段3】成员收入的一部分上缴组织金库
        """
        from src.organization_system import get_org_economy
        
        org_id = getattr(npc, 'org_id', None)
        if not org_id or org_id == 'NONE':
            return income  # 无组织，全额收入
            
        org_economy = get_org_economy()
        npc_share, org_share = org_economy.collect_contribution(npc, income)
        
        if org_share > 0:
            log_game_event(f"[ORG] {npc.name} 上缴{org_share}铜给{org_id}", tag="ECONOMY")
        
        return npc_share
    
    # ═══════════════════════════════════════════════════════════════════
    # 【新增】配方驱动职业行为
    # ═══════════════════════════════════════════════════════════════════
    
    # ── 工匠 (ARTISAN) ─────────────────────────────────────────────────
    # 工作地点：工坊、铁铺、织坊、窑场、首饰铺
    # 产出：器物、武器、护甲、丝绸、瓷器、首饰
    
    ARTISAN_WORK_BUILDINGS = ['WORKSHOP', 'SMITHY', 'WEAVING', 'KILN', 'JEWELER']
    ARTISAN_PRODUCTS = ['精制器物', '铁剑', '朴刀', '长枪', '大刀', '皮甲', 
                        '锁子甲', '鳞甲', '丝绸', '丝衣', '瓷器', '首饰']
    
    # ── 护卫 (GUARD) ───────────────────────────────────────────────────
    # 工作地点：府衙、岗哨、校场、武库
    # 行为：把守城门、巡逻、训练、领俸禄
    
    GUARD_WORK_BUILDINGS = ['GOV_OFFICE', 'GATEHOUSE', 'BARRACKS', 'ARMORY']
    GUARD_PATROL_INTERVAL_MS = 20000  # 巡逻间隔

    # ═══════════════════════════════════════════════════════════════════════════
    # 【新增】配方驱动AI集成
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _try_recipe_driven_work(self, npc, all_buildings, world_map):
        """
        使用配方驱动AI为NPC找到合适的工作
        
        设计原则：
        1. 优先让NPC去执行能产生价值（金钱/物品）的配方
        2. 根据NPC背包状态决定是生产还是销售
        3. 考虑距离和建筑占用情况
        
        返回: True 如果成功安排了工作，False 需要回退到硬编码行为
        """
        from src.atomic_actions import MoveToBuilding, MoveToPosition, Wait
        
        # 只在队列为空时安排新任务
        if not npc.action_queue.is_empty():
            return True  # 有任务在执行，不打断
        
        # 正在工作中的NPC不需要重新安排
        if npc.state == STATE_WORKING and npc.stack_parent:
            return True
        
        # 获取配方驱动AI实例
        try:
            recipe_ai = get_recipe_driven_ai()
        except Exception as e:
            log_game_event(f"[AI] 配方驱动AI初始化失败: {e}", tag="ERROR")
            return False  # 回退到硬编码行为
        
        # ─── 阶段1: 检查是否需要卖货 ─────────────────────────────────────
        # 只有生产职业（农民、工匠、商人）背包接近满时才去卖货
        # 其他职业允许背包超量持有物资
        SELLING_JOBS = {'FARMER', 'ARTISAN', 'MERCHANT'}
        if npc.job in SELLING_JOBS:
            # 计算可出售物品数量（排除铜钱，铜钱不是商品）
            sellable_inv = {k: v for k, v in npc.inventory.items() if k != ITEM_COIN} if hasattr(npc, 'inventory') else {}
            total_items = sum(sellable_inv.values())
            # 只有背包超过 10 件物品（约 80% 满）才去卖货
            if total_items >= 10:
                market = self._find_nearest_building(npc, all_buildings, 'MARKET')
                if market:
                    # 检查是否已经在市场
                    if npc.stack_parent == market:
                        return True  # 正在市场工作
                    
                    # 找出背包中数量最多的可售物品（排除铜钱）
                    if sellable_inv:
                        main_item = max(sellable_inv.keys(), key=lambda k: sellable_inv[k])
                        main_count = sellable_inv.get(main_item, 0)
                    else:
                        main_item = "货物"
                        main_count = 0
                    
                    npc.action_queue.enqueue(MoveToBuilding(market, reason=f"去卖{main_item}"))
                    npc.ai_reason = f"去市场卖{main_item}×{main_count}"
                    return True
        
        # ─── 阶段2: 使用配方驱动AI查找可执行配方 ───────────────────────────
        best_action = recipe_ai.get_best_recipe_action(npc, all_buildings)
        
        if best_action:
            recipe, target_building = best_action
            recipe_name = recipe.get('desc', recipe.get('id', '未知'))
            
            # 检查是否已经在目标建筑
            if npc.stack_parent == target_building:
                # 已经在正确的建筑上了，让配方系统处理
                return True
            
            # 前往目标建筑
            dist = math.hypot(
                npc.rect.centerx - target_building.rect.centerx,
                npc.rect.centery - target_building.rect.centery
            )
            
            if dist > 50:
                npc.action_queue.enqueue(MoveToBuilding(target_building, reason=f"前往{recipe_name}"))
                npc.ai_reason = f"准备{recipe_name}"
                log_game_event(f"[AI_RECIPE] {npc.name}({npc.job}) 选择配方「{recipe_name}」", tag="AI_RECIPE")
                return True
            else:
                # 已经很近了，等待自动堆叠
                npc.action_queue.enqueue(Wait(500, reason="等待工作"))
                return True
        
        # ─── 阶段3: 没有可执行配方，使用备用建筑映射 ─────────────────────────
        # 从 JOB_BUILDING_MAP 获取职业对应的建筑列表
        suitable_buildings = JOB_BUILDING_MAP.get(npc.job, [])
        
        if suitable_buildings:
            # 找一个空闲的合适建筑
            for b_type in suitable_buildings:
                target = self._find_nearest_empty_building(npc, all_buildings, b_type)
                if target:
                    if npc.stack_parent == target:
                        return True
                    npc.action_queue.enqueue(MoveToBuilding(target, reason=f"去{target.name}"))
                    npc.ai_reason = "寻找工作"
                    return True
        
        # 配方驱动AI没有找到工作，返回False让硬编码逻辑处理
        return False
    
    def _is_in_event_zone(self, target) -> bool:
        """
        检查目标是否在事件区内
        
        Args:
            target: 建筑、NPC 或任何有 rect 属性的对象
            
        Returns:
            bool: True 表示在事件区内，应该被排除
        """
        from src.context import ctx
        
        event_zone = getattr(ctx, '_event_zone', None)
        if not event_zone or not event_zone.get('active', False):
            return False
        
        # 获取目标位置
        if hasattr(target, 'rect'):
            tx = target.rect.centerx
            ty = target.rect.centery
        elif hasattr(target, 'x') and hasattr(target, 'y'):
            tx, ty = target.x, target.y
        else:
            return False
        
        # 计算距离
        center_x = event_zone.get('center_x', 0)
        center_y = event_zone.get('center_y', 0)
        radius = event_zone.get('radius', 0)
        
        dist = math.hypot(tx - center_x, ty - center_y)
        return dist <= radius
    
    def _find_nearest_building(self, npc, all_buildings, building_type):
        """找到最近的指定类型建筑（排除事件区内的建筑）"""
        from src.context import ctx
        
        candidates = [b for b in all_buildings if b.building_type == building_type]
        
        # 排除事件区内的建筑
        if getattr(ctx, '_event_zone', {}).get('active', False):
            # 无关NPC不能选择事件区内的建筑
            if not getattr(npc, '_event_protected', False):
                candidates = [b for b in candidates if not self._is_in_event_zone(b)]
        
        if not candidates:
            return None
        return min(candidates, key=lambda b: math.hypot(
            npc.rect.centerx - b.rect.centerx,
            npc.rect.centery - b.rect.centery
        ))
    
    def _find_nearest_empty_building(self, npc, all_buildings, building_type):
        """找到最近的空闲指定类型建筑（排除事件区内的建筑）"""
        from src.context import ctx
        
        candidates = [
            b for b in all_buildings 
            if b.building_type == building_type and b.stack_child is None
        ]
        
        # 排除事件区内的建筑
        if getattr(ctx, '_event_zone', {}).get('active', False):
            if not getattr(npc, '_event_protected', False):
                candidates = [b for b in candidates if not self._is_in_event_zone(b)]
        
        if not candidates:
            return None
        return min(candidates, key=lambda b: math.hypot(
            npc.rect.centerx - b.rect.centerx,
            npc.rect.centery - b.rect.centery
        ))
