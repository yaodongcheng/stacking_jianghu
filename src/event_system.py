# --- src/event_system.py ---
import csv
import random
import os
from src.definitions import *
from src.utils import log_game_event, resource_path
from src.entities import NPC,Player

class EventDefinition:
    def __init__(self, data):
        self.id = int(data.get('id', 0))
        self.title = data.get('title', '未知')
        self.desc_template = data.get('desc_template', '')
        self.type = data.get('type', 'CHOICE')
        
        self.tag_main = data.get('tag_main', '')   
        self.tag_target = data.get('tag_target', '')
        self.weight = int(data.get('weight', 10))
        
        # 【新增】对话ID字段
        self.intro_dialog_id = data.get('intro_dialog_id', '')  # 开场对话
        
        self.btn_a = data.get('btn_a', '')
        self.eff_a = data.get('eff_a', '')
        self.req_a = data.get('req_a', '')      
        self.chain_a = data.get('chain_a', '')
        self.dialog_a_id = data.get('dialog_a_id', '')  # 选项A后续对话
        
        self.btn_b = data.get('btn_b', '')
        self.eff_b = data.get('eff_b', '')
        self.req_b = data.get('req_b', '')      
        self.chain_b = data.get('chain_b', '')
        self.dialog_b_id = data.get('dialog_b_id', '')  # 选项B后续对话

        self.btn_c = data.get('btn_c', '')
        self.eff_c = data.get('eff_c', '')
        self.req_c = data.get('req_c', '')      
        self.chain_c = data.get('chain_c', '')
        self.dialog_c_id = data.get('dialog_c_id', '')  # 选项C后续对话

class EventManager:
    def __init__(self, filepath, npc_pool_data):
        self.events = self.load_events(filepath)

        # --- 时间系统 ---
        self.time_speed = 1 
        self._stored_speed = 0 
        self.game_tick = 0
        self.current_day_ticks = 0
        self.ticks_per_day = TICKS_PER_DAY 
        self.day_end_flag = False
        
        # --- 生成系统 ---
        self.npc_data_pool = npc_pool_data 
        self.spawn_timer = 0
        self.spawn_interval = 1200 # 流民刷新间隔
        
        # --- 事件与新闻 ---
        self.active_news_toast = [] 
        self.news_history = []
        self.pending_chains = [] # [(event_id, npc_id, delay_ticks)]
        self.event_timer = 0
        self.event_interval = 600
        self.MAX_ACTIVE_EVENTS = 1 
        self.last_refugee_day = -1
        # [UI 关键] 当前查看的事件对象，供 UI 弹窗读取详细信息 (如按钮文本、需求)
        self.current_event = None
        
    def request_interaction_pause(self):
        """请求交互暂停：记录当前速度并暂停"""
        if self.time_speed > 0:
            self._stored_speed = self.time_speed
            self.set_speed(0)
            #print("[Time] 交互暂停")
        else:
            # 如果本来就是暂停的，记录为0，恢复时也保持暂停
            self._stored_speed = 0

    def request_interaction_resume(self):
        """交互结束：恢复之前的速度"""
        if self._stored_speed > 0:
            self.set_speed(self._stored_speed)
            self._stored_speed = 0
            #print("[Time] 交互恢复")
        # 如果 _stored_speed 是 0，说明原本就是暂停的，不需要操作

    def load_events(self, filepath):
        """
        读取事件 CSV，具备跳过表头行的容错能力
        """
        events = []
        try:
            path = resource_path(filepath)
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
                # 假设结构：Row 0=Keys, Row 1=Types, Row 2=CN Headers, Row 3+=Data
                if len(rows) > 3:
                    keys = rows[0]
                    for row in rows[3:]:
                        if not row or len(row) < 3: continue 
                        # 补全缺失列
                        while len(row) < len(keys):
                            row.append('')
                        data = dict(zip(keys, row))
                        events.append(EventDefinition(data))
            print(f"[EventSys] 已加载 {len(events)} 条事件")
        except Exception as e:
            print(f"[EventSys] 加载事件失败: {e}")
        return events

    def set_speed(self, speed):
        self.time_speed = speed

    def get_day_progress(self):
        return min(1.0, self.current_day_ticks / self.ticks_per_day)

    def update(self, all_cards, player, world_map, tech_mgr):
        if self.time_speed == 0: return 
        # 根据倍速执行多次 tick，保证逻辑速度匹配
        for _ in range(self.time_speed):
            self._tick(all_cards, player, world_map, tech_mgr)

    def _tick(self, all_cards, player, world_map, tech_mgr):
        self.game_tick += 1
        self.current_day_ticks += 1
        refugee_unlocked = False
        # --- 1. 日夜循环 ---
        if self.current_day_ticks >= self.ticks_per_day:
            self.current_day_ticks = 0
            self.day_end_flag = True
        if hasattr(self, 'quest_flags') and self.quest_flags.get('refugee_unlocked'):
            refugee_unlocked = True
        
        # --- 2. 自动生成流民 ---
        current_refugees = [c for c in all_cards if hasattr(c, 'is_refugee') and c.is_refugee]
        # 允许场上最多存在 3 个流民
        if refugee_unlocked and len(current_refugees) < 3:
            if player.day > self.last_refugee_day: # [新增] 每天限1个 (自然刷新)
                self.spawn_timer += 1
                limit = self.spawn_interval
                if tech_mgr.is_unlocked('T_EXPAND'): limit = 800 
                if self.spawn_timer >= limit:
                    self.spawn_timer = 0
                    self.last_refugee_day = player.day # 记录今天刷过了
                    self._spawn_random_refugee(all_cards, world_map)

        # --- 3. 随机事件 ---
        self.event_timer += 1
        if self.event_timer >= self.event_interval:
            self.event_timer = 0
            self.try_trigger_random_event(all_cards, player)
            
        # --- 4. 连锁事件处理 ---
        # 倒序遍历以便安全删除
        for i in range(len(self.pending_chains) - 1, -1, -1):
            evt_id, npc_id, delay = self.pending_chains[i]
            if delay > 0:
                self.pending_chains[i] = (evt_id, npc_id, delay - 1)
            else:
                # 寻找目标NPC
                target_npc = next((n for n in all_cards if hasattr(n, 'id') and n.id == npc_id), None)
                if target_npc and target_npc.safety not in [SAFETY_DEAD, SAFETY_EXILED]:
                    self.trigger_specific_event(evt_id, target_npc, all_cards)
                self.pending_chains.pop(i)
        
        # --- 5. 清理新闻 ---
        self.active_news_toast = [(txt, t-1) for txt, t in self.active_news_toast if t > 0]
    def spawn_refugee_immediately(self, ctx):
        """剧情强制刷新流民，无视CD和每日限制"""
        print("[Event] 剧情强制生成流民")
        self._spawn_random_refugee(ctx.all_cards, ctx.world_map)
    def _spawn_random_refugee(self, all_cards, world_map):
        """生成流民，并尝试放置在城门口"""
        from src.entities import NPC # 局部引用防止循环导入
        if not self.npc_data_pool: return
        
        data = random.choice(self.npc_data_pool)
        new_npc = NPC(data)
        new_npc.is_follower = False
        new_npc.is_refugee = True 
        new_npc.job = 'NONE' # 流民没有职业
        new_npc.money = 0 
        new_npc.inventory = {}
        
        # 获取城门位置
        gate_pos = world_map.get_nearest_gate(world_map.city_rect.centerx, world_map.city_rect.centery)
        if gate_pos:
            gx, gy = gate_pos
        else:
            gx, gy = 100, 100
        # 随机偏移防止完全重叠，统一走 set_pos（中心点）
        gx += random.randint(-10, 10)
        gy += random.randint(-10, 10)
        new_npc.set_pos(gx, gy)
        new_npc.set_movement_target(float(new_npc.rect.centerx), float(new_npc.rect.centery), "初始位置") # 确保目标同步
        all_cards.append(new_npc)
        self.add_news(f"流民 {new_npc.name} 徘徊在城门口。", category='NEWS')

    def add_news(self, text, category='NEWS'):
        self.active_news_toast.append((text, 300))
        entry = {'text': text, 'category': category}
        self.news_history.insert(0, entry)
        if len(self.news_history) > 30: 
            self.news_history.pop()

    def trigger_specific_event(self, event_id, npc_a, all_npcs):
        """强制触发指定事件（用于连锁）"""
        if npc_a.state == STATE_EVENT: return 
        evt = next((e for e in self.events if e.id == int(event_id)), None)
        if not evt: return
        self._deploy_event(evt, npc_a, all_npcs)

    def try_trigger_random_event(self, all_npcs, player=None, force=False):
        print(f"[EventSys] 尝试触发事件 (Force={force})...") 
        
        # [修复 1]：先基于全局(all_npcs)统计当前正在进行事件的人数
        # 注意：必须检查 hasattr(n, 'state')，因为 all_npcs 里包含建筑(Building)和资源，它们没有 state 属性会导致报错
        active_count = 0
        for n in all_npcs:
            # 排除玩家、排除建筑(没有job属性或没有state属性的)
            if isinstance(n, NPC) and hasattr(n, 'state') and getattr(n, 'job', '') != 'PLAYER':
                if n.state in [STATE_EVENT, STATE_MEETING]:
                    active_count += 1

        # [修复 2]：如果不是强制触发，且当前事件数已达上限，直接返回
        if not force and active_count >= self.MAX_ACTIVE_EVENTS: 
            print(f"[EventSys] 跳过: 当前事件拥挤 ({active_count}/{self.MAX_ACTIVE_EVENTS})") 
            return

        valid_npcs = [
            n for n in all_npcs 
            if hasattr(n, 'state') 
            and n.job != 'PLAYER' 
            and n.job != 'BANDIT'
            and n.safety not in [SAFETY_DEAD, SAFETY_EXILED]
            and not getattr(n, 'is_refugee', False)
            and getattr(n, 'event_cooldown', 0) <= 0  # [新增] 检查冷却
        ]
        
        
        if not self.events or not valid_npcs: return
        
       

        # 优先选择有“故事”的NPC（比如理智低的，或者正在工作的）
        weighted_candidates = []
        for n in valid_npcs:
            w = 10
            if n.state == STATE_WORKING: w += 20
            # 使用 getattr 防止 NPC 数据缺失导致崩溃
            if getattr(n, 'sanity', 100) < 30: w += 30
            weighted_candidates.extend([n] * (w // 10))
        if not weighted_candidates: 
            print("[EventSys] 失败: 所有NPC都在忙于事件中") # [DEBUG]
            return
        chosen_npc = random.choice(weighted_candidates)
        print(f"[EventSys] 选中主角: {chosen_npc.name} (Job: {chosen_npc.job})") # [DEBUG]
        valid_events = []
        for e in self.events:
            if e.weight <= 0: continue
            is_recruitment = ('is_follower:True' in e.eff_a or 'is_follower:True' in e.eff_b)
            if chosen_npc.is_follower and is_recruitment: continue
            
            # 简单的上下文匹配
            if e.tag_main == 'ANY':
                valid_events.append(e)
            elif e.tag_main in getattr(chosen_npc, 'tags', []) or e.tag_main == chosen_npc.job:
                valid_events.append(e)
        
        if not valid_events: 
            print(f"[EventSys] 失败: {chosen_npc.name} 身上没有匹配的事件 (Tags: {chosen_npc.tags})") # [DEBUG]
            return        
        evt = random.choices(valid_events, weights=[e.weight for e in valid_events], k=1)[0]
        print(f"[EventSys] 成功触发: {evt.title}") # [DEBUG]
        chosen_npc.event_cooldown = 10000 # [新增] 设置较长冷却，避免它马上又出事
        self._deploy_event(evt, chosen_npc, valid_npcs)

    def _deploy_event(self, evt, npc_a, all_npcs):
        # 恢复双人互动逻辑
        stage_x, stage_y = npc_a.pixel_x, npc_a.pixel_y
        npc_b = None
        
        # 只有CHOICE类型才找搭档，NEWS类型不需要
        if evt.type == 'CHOICE':
            others = [
                n for n in all_npcs 
                if n.id != npc_a.id 
                and hasattr(n, 'state')
                and n.job != 'PLAYER' 
                and n.job != 'BANDIT' 
                and not getattr(n, 'is_refugee', False)
                and n.safety not in [SAFETY_DEAD, SAFETY_EXILED]
            ]
            # 如果事件指定了 target_tag
            if evt.tag_target and evt.tag_target != 'ANY':
                 others = [
                    n for n in others 
                    if evt.tag_target in getattr(n, 'tags', []) or evt.tag_target == n.job
                ]
            
            # 找最近的一个
            if others:
                npc_b = min(others, key=lambda n: (n.pixel_x - stage_x)**2 + (n.pixel_y - stage_y)**2)
                # 距离太远就算了 (例如 > 600像素)
                dist = ((npc_b.pixel_x - stage_x)**2 + (npc_b.pixel_y - stage_y)**2)**0.5
                if dist > 600: 
                    npc_b = None

        name_a = npc_a.name
        name_b = npc_b.name if npc_b else "某人"
        final_desc = evt.desc_template.replace("{A}", name_a).replace("{B}", name_b)
        if npc_a.stack_parent:
            npc_a.bounce_off(npc_a.stack_parent)


        npc_a.state = STATE_EVENT
        npc_a.state_timer = 3600 # 事件持续时间
        npc_a.set_movement_target(stage_x, stage_y, "事件系统设置移动目标")
        
        if npc_b:
            npc_b.state = STATE_MEETING
            npc_b.state_timer = 3600
            # 让B走到A旁边
            npc_b.set_movement_target(stage_x + 50, stage_y, "走向事件现场")
            npc_b.event_partner = npc_a
            npc_a.event_partner = npc_b
        else:
            npc_a.event_partner = None

        npc_a.active_event_data = {
            'id': evt.id,
            'title': evt.title,
            'description': final_desc,
            'btn_a': evt.btn_a, 'eff_a': evt.eff_a, 'req_a': evt.req_a, 'chain_a': evt.chain_a,
            'btn_b': evt.btn_b, 'eff_b': evt.eff_b, 'req_b': evt.req_b, 'chain_b': evt.chain_b,
            'btn_c': evt.btn_c, 'eff_c': evt.eff_c, 'req_c': evt.req_c, 'chain_c': evt.chain_c,
            'partner': npc_b
        }
        
        # [关键] 同步记录到 Manager 供 UI 读取
        self.current_event = evt 
        stage_x, stage_y = npc_a.pixel_x, npc_a.pixel_y
        onlookers = []
        for n in all_npcs:
            if n == npc_a or n == getattr(npc_a, 'event_partner', None): continue
            if n.job == 'PLAYER': continue
            if n.state != STATE_IDLE: continue # 只有闲人会看热闹
            
            dist = ((n.pixel_x - stage_x)**2 + (n.pixel_y - stage_y)**2)**0.5
            if dist < 350:
                onlookers.append(n)
        
       
            
        self.current_event = evt
        # [修改] 日志增加前缀
        log_game_event(f"【突发】事件“{evt.title}”在 {npc_a.name} 处发生，引发众人围观。")

    def resolve_event(self, npc_a, effect_str, chain_info, player, choice_text="默许", ctx=None):
        """
        结算事件效果
        
        【重构】现在优先使用 StoryDirectiveExecutor 处理新格式指令，
        同时保持对旧格式（PLAYER:Money:-100）的兼容
        """
        results = {'money_change': 0, 'fame_change': 0, 'floating_texts': []}
        evt_title = "未知事件"
        if npc_a.active_event_data:
            evt_title = npc_a.active_event_data.get('title', '')
        # [关键] 结算后清空 UI 事件引用，关闭弹窗
        self.current_event = None 
        
        # 处理连锁
        if chain_info:
            try:
                if ":" in chain_info:
                    c_id, c_delay_days = chain_info.split(':')
                    delay_ticks = int(float(c_delay_days) * self.ticks_per_day)
                    self.pending_chains.append((c_id, npc_a.id, delay_ticks))
            except Exception as e:
                print(f"Chain parsing error: {e}")

        if not effect_str: 
            return results
        
        npc_b = getattr(npc_a, 'event_partner', None)
        
        # 【新增】尝试使用 StoryDirectiveExecutor 处理新格式指令
        # 新格式识别：指令以大写字母开头且不包含角色前缀（PLAYER/SELF/OTHER）
        new_format_cmds = []
        old_format_cmds = []
        
        commands = effect_str.split(';')
        for cmd in commands:
            cmd = cmd.strip()
            if not cmd:
                continue
            
            # 判断是否是新格式（如 SET_AFFINITY:xxx 或 PLAYER_MONEY:xxx）
            # 旧格式的特征是以 PLAYER:/SELF:/OTHER: 开头
            first_part = cmd.split(':')[0].upper()
            if first_part in ['PLAYER', 'SELF', 'OTHER']:
                old_format_cmds.append(cmd)
            else:
                new_format_cmds.append(cmd)
        
        # 处理新格式指令（通过 StoryDirectiveExecutor）
        if new_format_cmds and ctx:
            try:
                from src.story.story_directive_executor import get_directive_executor
                executor = get_directive_executor()
                executor.bind_context(ctx)
                for cmd in new_format_cmds:
                    # 替换 SELF/OTHER 为实际 NPC 名称
                    resolved_cmd = self._resolve_role_names(cmd, npc_a, npc_b)
                    executor.execute(resolved_cmd)
            except Exception as e:
                print(f"[EventSys] StoryDirective执行失败: {e}")
        
        # 处理旧格式指令（保持兼容）
        for cmd in old_format_cmds:
            parts = cmd.split(':')
            if len(parts) < 3: continue
            target_role, attr = parts[0], parts[1]
            val = ":".join(parts[2:]) # 修复：如果有多个冒号，把剩余部分拼回去
            # --- 玩家属性 ---
            if target_role == 'PLAYER':
                if attr == 'Money':
                    v = int(val)
                    player.money += v
                    results['money_change'] += v
                elif attr == 'Fame':
                    v = int(val)
                    player.fame += v
                    results['fame_change'] += v
                elif attr == 'inventory' and val.startswith('GRAIN'): 
                    if len(parts) >= 4:
                        player.food += int(parts[3])
                        results['floating_texts'].append((f"粮食+{parts[3]}", 'CENTER', 0, (150, 255, 150)))
                elif attr == 'AddTag':
                    results['floating_texts'].append((f"获得名号: {val}", 'CENTER', 100, (200, 200, 255)))

            # --- NPC 属性 ---
            else:
                target_npc = None
                if target_role == 'SELF': target_npc = npc_a
                elif target_role == 'OTHER': target_npc = npc_b
                
                if target_npc:
                    # 特殊处理：招募
                    if attr == 'is_follower' and val == 'True':
                         val = True
                         if not target_npc.is_follower: 
                             player.followers_count += 1
                             results['floating_texts'].append(("加入麾下!", target_npc.pixel_x, target_npc.pixel_y - 80, (255, 215, 0)))

                    success, desc = target_npc.apply_change(attr, val)
                    
                    # 视觉反馈
                    if success and desc:
                        color = (100, 255, 100) # 默认绿色
                        if any(x in desc for x in ["死亡", "流放", "危险", "绝望", "减少", "下降"]):
                            color = (255, 80, 80) # 坏事红色
                        
                        results['floating_texts'].append((desc, target_npc.pixel_x, target_npc.pixel_y - 60, color))
                        
                        # 记录到 NPC 记忆中
                        if hasattr(target_npc, 'memory'):
                            target_npc.memory.append(f"参与了: {npc_a.active_event_data['title']}")

        news_str = f"针对【{evt_title}】，你选择了“{choice_text}”。"
        
        # 简单的结果描述
        changes = []
        if results['money_change'] != 0: changes.append(f"铜钱{results['money_change']}")
        if results['fame_change'] != 0: changes.append(f"威望{results['fame_change']}")
        
        if changes:
            news_str += f" 造成影响: {', '.join(changes)}。"
        else:
            news_str += " 事件平息。"

        self.add_news(news_str, category='IMPORTANT')
        self.current_event = None
        
        # [关键修复] 事件结束后，不仅重置状态，还要强制清空目标
        # 这样 NPC 的 AI 在下一帧会发现 target_x 为空，从而重新计算去农田的路径
        npc_a.state = STATE_IDLE
        npc_a.active_event_data = None
        npc_a.clear_movement_target("事件结算-重置目标") # <--- 新增
        player.bounce_off(npc_a, distance=80) # 玩家弹开
        
        return results

    def _resolve_role_names(self, cmd: str, npc_a, npc_b) -> str:
        """
        将指令中的 SELF/OTHER 替换为实际 NPC 名称或ID
        
        例如: SET_AFFINITY:SELF:+30 → SET_AFFINITY:张三:+30
        """
        if not cmd:
            return cmd
        
        # 获取名称
        name_a = npc_a.name if npc_a else ''
        name_b = npc_b.name if npc_b else ''
        
        # 按冒号分割，只替换参数部分（不替换指令名）
        parts = cmd.split(':')
        resolved_parts = []
        for i, part in enumerate(parts):
            if i == 0:
                # 第一部分是指令名，不替换
                resolved_parts.append(part)
            elif part.upper() == 'SELF' and name_a:
                resolved_parts.append(name_a)
            elif part.upper() == 'OTHER' and name_b:
                resolved_parts.append(name_b)
            else:
                resolved_parts.append(part)
        
        return ':'.join(resolved_parts)

    def check_requirement(self, player, req_str):
        """检查玩家是否满足事件选项的需求（UI用）"""
        if not req_str: return True
        reqs = req_str.split(';')
        for r in reqs:
            parts = r.split(':')
            if len(parts) < 2: continue
            r_type, r_val = parts[0], parts[1]

            if r_type == 'MONEY':
                val = int(r_val)
                if player.money < val: return False
            elif r_type == 'FAME':
                val = int(r_val)
                if r_val.startswith('-'):
                    if player.fame > val: return False 
                else:
                    if player.fame < val: return False
            elif r_type == 'TAG':
                if r_val not in player.tags: return False
        return True

    def process_day_end(self, player, all_npcs):
        """处理每日结算：消耗粮食、发工资、理智判定、组织薪俸"""
        self.day_end_flag = False
        player.day += 1
        
        followers = [n for n in all_npcs if n.is_follower and n.safety not in [SAFETY_DEAD, SAFETY_EXILED]]
        
        player.followers_count = len(followers)
        
        # 【阶段3】组织经济日结算 - 发放薪俸
        from src.organization_system import get_org_economy
        org_economy = get_org_economy()
        salary_result = org_economy.pay_daily_salaries(all_npcs)
        org_economy.daily_reset()
        
        # 生成薪俸报告
        for org_id, (paid, count) in salary_result.items():
            if paid > 0:
                log_game_event(f"[{org_id}] 发放薪俸 {paid}铜给{count}人", tag="ORG_SALARY")
        
        # 【阶段4】势力战争日结算 - 控制点收益 & 关系衰减
        from src.faction_war_system import get_faction_war_system
        faction_war = get_faction_war_system()
        faction_war.process_daily_income(org_economy)  # 控制点收益存入组织金库
        faction_war.daily_relation_decay()  # 敌对关系缓慢恢复
        
        report = {
            'day': player.day - 1,
            'pop': len(followers) + 1,
            'org_salaries': salary_result,  # 添加组织薪俸数据
            'faction_income': faction_war.daily_income_record.copy()  # 势力控制点收入
        }
        
        msg = f"【日报】第{player.day-1}天:过去了"
        self.add_news(msg, category='IMPORTANT')
        log_game_event(msg)
        return report
