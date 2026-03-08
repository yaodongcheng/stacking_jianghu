# --- src/recipe_system.py ---
import random
import csv
import os
from src.definitions import *
from src.utils import log_game_event, resource_path
from src.data.building_defs import BUILDING_DB
from src.entities import Building, Resource, NPC, Player


class RecipeProxy:
    """代理类，用于把字典转成对象访问，兼容 main.py"""
    def __init__(self, data):
        self.data = data
        self.id = data['id']
        self.duration = int(data['time']) if data.get('time') else 100 
        self.name = data['desc']
    def result_callback(self, child, parent, player):
        """配方完成后的回调"""
        out_str = self.data['output']
        raw = self.data.get('req_count')
        req_count = int(raw) if raw else 1
        if self.data.get('target_type') == 'RESOURCE' and isinstance(parent, Resource):
            parent.count -= req_count
            
        # 2. 扣除输入材料
        if isinstance(child, Resource):
            child.count -= req_count
        
        # 2. 扣除额外消耗 (ext_input, 如农夫种地需要消耗背包里的种子)
        # 格式: GRAIN:1
        ext = self.data.get('ext_input', '')
        if ext:
            req_item, req_amt = ext.split(':')
            req_amt = int(req_amt)
            # 扣除工作者(Child)背包
            if hasattr(child, 'inventory') and child.inventory.get(req_item, 0) >= req_amt:
                child.inventory[req_item] -= req_amt
                if child.inventory[req_item] <= 0: del child.inventory[req_item]
         # 3. 扣除金钱消耗 (cost_money)
        cost_money = int(self.data.get('cost_money', 0) or 0)
        if cost_money > 0:
            if isinstance(child, (NPC, Player)):                
                child.money -= cost_money
        # 3. 处理产出
        if out_str == '_FUEL':
            if hasattr(parent, 'fuel_time'):
                parent.fuel_time += 300
                parent.show_popup("燃料UP")
            return "添加燃料"
        
        
        # ═══════════════════════════════════════════════════════════════════
        # ACTION 类型处理
        # ═══════════════════════════════════════════════════════════════════
        if out_str.startswith('ACTION:'):
            return self._handle_action_output(out_str, child, parent, player)
        
        # 保留旧的HEAL处理（兼容）
        if out_str == 'ACTION:HEAL' or out_str == 'ACTION:HEAL_SLOW':
            # 谁在接受治疗？
            # 场景 A (医馆): Parent=Clinic, Child=Patient. 此时 child 被治疗。
            # 场景 B (野外): Parent=Healer, Child=Patient. 
            #                与背人逻辑一致：健康NPC(parent)背着/治疗重伤者(child)
            #                重伤者被放到健康NPC身上，重伤者是child，健康NPC是parent
            
            patient = None
            healer = None
            
            if out_str == 'ACTION:HEAL': # 医馆模式
                patient = child
                log_game_event(f"[HEAL_DEBUG] 医馆治疗模式: 患者={child.name if hasattr(child, 'name') else 'Unknown'}, 医馆={parent.name if hasattr(parent, 'name') else 'Unknown'}", tag="HEAL")
            else: # 野外模式 ACTION:HEAL_SLOW
                # 与背人逻辑一致：
                # parent = 健康NPC（治疗者，在下面）
                # child = 重伤者（患者，被放在上面）
                patient = child
                healer = parent
                log_game_event(f"[HEAL_DEBUG] 野外治疗模式: 患者={child.name if hasattr(child, 'name') else 'Unknown'}, 治疗者={parent.name if hasattr(parent, 'name') else 'Unknown'}", tag="HEAL")

            # 调试：检查患者状态
            if isinstance(patient, NPC):
                log_game_event(f"[HEAL_DEBUG] 患者状态检查: {patient.name} 职业={patient.job} 安全={patient.safety} 血量={patient.hp}/{patient.max_hp}", tag="HEAL")
            else:
                log_game_event(f"[HEAL_DEBUG] 患者类型错误: 期望NPC，实际={type(patient)}", tag="HEAL")
                return "患者类型错误"

            if isinstance(patient, NPC) and patient.safety == SAFETY_DOWNED:
                # 治疗回血
                heal_amt = 20 if out_str == 'ACTION:HEAL' else 5
                old_hp = patient.hp
                patient.hp = min(patient.max_hp, patient.hp + heal_amt)
                log_game_event(f"[HEAL_DEBUG] 治疗回血: {patient.name} {old_hp}->{patient.hp}/{patient.max_hp} (+{heal_amt})", tag="HEAL")
                
                # 检查是否痊愈
                if patient.hp >= patient.max_hp:
                    patient.safety = SAFETY_NORMAL
                    patient.state = STATE_IDLE
                    log_game_event(f"[HEAL_DEBUG] 患者痊愈: {patient.name} 血量满了，开始检查归化", tag="HEAL")
                    
                    # ═══════════════════════════════════════════════════════════
                    # 【新增】野外急救完成后：患者对治疗者产生好感 + 记忆
                    # ═══════════════════════════════════════════════════════════
                    if healer and isinstance(healer, NPC) and out_str == 'ACTION:HEAL_SLOW':
                        # 患者增加对治疗者的好感度
                        healer_id = getattr(healer, 'id', None)
                        if healer_id is not None:
                            # 使用 affinity 字典存储对其他NPC的好感度
                            if not hasattr(patient, 'affinity'):
                                patient.affinity = {}
                            old_aff = patient.affinity.get(healer_id, 0)
                            patient.affinity[healer_id] = old_aff + 30  # 救命之恩 +30好感
                            
                            # 如果治疗者是玩家，也更新 affinity_to_player
                            if hasattr(healer, 'is_player') and healer.is_player:
                                patient.affinity_to_player = getattr(patient, 'affinity_to_player', 0) + 30
                            
                            log_game_event(f"[HEAL_DEBUG] 好感度提升: {patient.name} 对 {healer.name} 好感 {old_aff} -> {patient.affinity[healer_id]}", tag="HEAL")
                        
                        # 添加记忆：被XX救过命
                        if hasattr(patient, 'add_memory'):
                            patient.add_memory(
                                event_type='SAVED_BY',
                                target_id=healer_id,
                                target_name=healer.name,
                                description=f"被{healer.name}救过一命",
                                importance=3  # 重要记忆
                            )
                            log_game_event(f"[HEAL_DEBUG] 记忆添加: {patient.name} 记住了 {healer.name} 的救命之恩", tag="HEAL")
                        
                        # 治疗者也可以获得记忆：曾救过XX
                        if hasattr(healer, 'add_memory'):
                            healer.add_memory(
                                event_type='SAVED',
                                target_id=getattr(patient, 'id', None),
                                target_name=patient.name,
                                description=f"曾在野外救过{patient.name}",
                                importance=2
                            )
                        
                        log_game_event(f"【叙事】{healer.name} 在野外救治了重伤的 {patient.name}，两人之间产生了羁绊。")
                    
                    # 1. 土匪感化逻辑
                    is_villain = patient.job in ['BANDIT', 'THUG'] or 'VILLAIN' in getattr(patient, 'tags', [])
                    log_game_event(f"[HEAL_DEBUG] 归化检查: {patient.name} 职业={patient.job} 标签={getattr(patient, 'tags', [])} 是恶徒={is_villain}", tag="HEAL")
                    
                    if is_villain:
                        old_job = patient.job
                        old_tags = getattr(patient, 'tags', []).copy()
                        
                        patient.job = 'FARMER'
                        patient.tags = [t for t in getattr(patient, 'tags', []) if t != 'VILLAIN']
                        patient.tags.append('HONEST')
                        patient.ai_reason = "改过自新"
                        
                        log_game_event(f"[HEAL_DEBUG] 归化完成: {patient.name} {old_job}->{patient.job} 标签{old_tags}->{patient.tags}", tag="HEAL")
                        log_game_event(f"【感化】恶徒 {patient.name} 在医馆被救治，决定洗心革面成为农夫！")
                        if hasattr(parent, 'show_popup'): parent.show_popup("感化成功")
                    else:
                        log_game_event(f"[HEAL_DEBUG] 普通治疗: {patient.name} 不是恶徒，正常痊愈", tag="HEAL")
                        log_game_event(f"{patient.name} 痊愈出院。")
                        if hasattr(parent, 'show_popup'): parent.show_popup("痊愈")

                    # 2. 排队处理逻辑 (仅医馆模式)
                    if out_str == 'ACTION:HEAL':
                        # 记录患者的下一个排队者 (Grandchild)
                        next_patient = patient.stack_child
                        log_game_event(f"[HEAL_DEBUG] 排队处理: {patient.name} 准备离开，下一位={next_patient.name if next_patient and hasattr(next_patient, 'name') else 'None'}", tag="HEAL")
                        
                        # 患者离开 (Bounce Off)
                        # #补充弹开前和弹开后的坐标
                        old_x, old_y = patient.rect.centerx, patient.rect.centery
                        patient.bounce_off(parent,howToProcessChild="connectToParent")
                        new_x, new_y = patient.rect.centerx, patient.rect.centery
                        log_game_event(f"[HEAL_DEBUG] 患者离开: {patient.name} 从({old_x},{old_y})弹开到({new_x},{new_y})", tag="HEAL")
                        #补充弹开前和弹开后的坐标
                        
                        # 如果后面还有人，把下一个人接到医馆上
                        if next_patient:                            
                            log_game_event(f"[HEAL_DEBUG] 下一位患者: {next_patient.name} 开始接受治疗", tag="HEAL")
                else:
                    log_game_event(f"[HEAL_DEBUG] 治疗中: {patient.name} 血量{patient.hp}/{patient.max_hp}，尚未痊愈", tag="HEAL")
                            
                return "治疗中..."
                
            elif isinstance(patient, NPC) and patient.safety == SAFETY_NORMAL:
                # 已经好了
                log_game_event(f"[HEAL_DEBUG] 患者已痊愈: {patient.name} 状态正常，准备离开", tag="HEAL")
                patient.bounce_off(parent,howToProcessChild="connectToParent")
                return "已痊愈"
                
            log_game_event(f"[HEAL_DEBUG] 治疗条件不满足: 患者={type(patient)} 安全={patient.safety if isinstance(patient, NPC) else 'N/A'}", tag="HEAL")
            return "治疗中..."





        # 解析产出: "ITEM:小麦:1" 或 "BUILDING:HOUSE" 或 "STAT:REST"
        parts = out_str.split(':')
        category = parts[0] if len(parts) > 1 else 'ITEM'
        
        if category == 'BUILDING':
            b_type = parts[1]
            return Building(parent.rect.x, parent.rect.y + 50, b_type)
            
        elif category == 'ITEM' or category not in ['STAT', 'RESOURCE']:
            # 兼容旧格式 "小麦" -> 视为 ITEM
            item_type = parts[1] if len(parts)>1 else out_str
            amt = int(parts[2]) if len(parts)>2 else 1
            
            # 如果是人在工作，产物优先进背包
            if isinstance(child, NPC):
                # === 四大属性加成 ===
                # 力量：农夫种粮/工匠打造 -> 粮食/器物有概率多产一件
                if item_type in (ITEM_GRAIN, '精制器物'):
                    bonus_chance = (getattr(child, 'strength', 5) - 5) * 0.04  # 每+1力量+4%概率
                    if random.random() < bonus_chance:
                        amt += 1
                # 智力：官员/书生的金钱产出 -> 按智力线性加成
                if item_type == ITEM_COIN and child.job in ('OFFICIAL', 'SCHOLAR'):
                    bonus = int((getattr(child, 'wit', 5) - 5) * 1.5)  # 每+1智力+1.5钱
                    amt += max(0, bonus)
                # 魅力：商人/舞姬的金钱产出 -> 按魅力线性加成
                if item_type == ITEM_COIN and child.job in ('MERCHANT', 'DANCER'):
                    bonus = int((getattr(child, 'charm', 5) - 5) * 1.2)
                    amt += max(0, bonus)
                # 钱直接进钱包
                if item_type == ITEM_COIN:
                    child.money += amt
                else:
                    child.inventory[item_type] = child.inventory.get(item_type, 0) + amt
                return f"获得 {item_type}"
            else:
                # 否则掉落在地上
                return Resource(parent.rect.x, parent.rect.y + 50, item_type, count=amt)

        elif category == 'STAT':
            # ═══════════════════════════════════════════════════════════════════
            # STAT 类型处理 - 状态/属性变化
            # ═══════════════════════════════════════════════════════════════════
            return self._handle_stat_output(out_str, child, parent, player)
        
        elif category == 'JOB':
            new_job = parts[1]
            if isinstance(child, NPC):
                child.job = new_job
                child.is_refugee = False # 既然有了工作，就不是流民了
                child.ai_reason = "就职成功"
                #parent.show_popup(f"转职: {new_job}")
                child.bounce_off(parent)
            return f"转职为 {new_job}"

        elif category == 'FOLLOWER':
            # 格式: FOLLOWER:TRUE (招募)
            # 注意：金钱消耗已在上面 cost_money 处理了
            if isinstance(child, NPC):
                child.is_follower = True
                child.is_refugee = False
                child.ai_mode = "FOLLOW"  # 设置AI模式为跟随
                child.job = 'GUARD' # 默认转为护院，或者可以再加参数指定
                child.atk = 15
                player.followers_count += 1
                #parent.show_popup("招募成功")
                child.bounce_off(parent)
            return "新门客加入"

        return f"完成: {self.name}"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ACTION 类型产出处理
    # ═══════════════════════════════════════════════════════════════════════════
    def _handle_action_output(self, out_str, child, parent, player):
        """
        处理 ACTION:XXX 类型的配方输出
        
        支持的ACTION类型：
        - GAMBLE_SMALL / GAMBLE_BIG: 赌博（小赌/豪赌）
        - REPAIR: 修理装备
        - HIRE_THUG: 雇佣打手
        - PLAN_RAID: 谋划劫掠
        - VISIT_PRISONER: 探监
        - HEAL / HEAL_SLOW: 治疗（已在上层处理）
        """
        action_type = out_str.split(':')[1] if ':' in out_str else ''
        
        # ─── 赌博系统 ─────────────────────────────────────────────────────────
        if action_type == 'GAMBLE_SMALL':
            return self._do_gamble(child, parent, bet_amount=10, win_rate=0.45)
        
        elif action_type == 'GAMBLE_BIG':
            return self._do_gamble(child, parent, bet_amount=50, win_rate=0.40)
        
        # ─── 武器修理 ─────────────────────────────────────────────────────────
        elif action_type == 'REPAIR':
            if isinstance(child, NPC):
                # 检查是否有武器需要修理（简化：恢复耐久度属性）
                weapon_durability = getattr(child, 'weapon_durability', 100)
                if weapon_durability < 100:
                    child.weapon_durability = 100
                    log_game_event(f"{child.name} 修理了武器")
                    if hasattr(parent, 'show_popup'):
                        parent.show_popup("修理完成")
                    return "武器修理完成"
                else:
                    if hasattr(parent, 'show_popup'):
                        parent.show_popup("无需修理")
                    return "武器状态良好"
            return "修理中..."
        
        # ─── 雇佣打手 ─────────────────────────────────────────────────────────
        elif action_type == 'HIRE_THUG':
            if isinstance(child, NPC):
                # 雇佣一个打手作为临时跟随者
                child._hired_thug = True
                child._hired_thug_timer = 30000  # 30秒有效期
                log_game_event(f"{child.name} 在黑市雇佣了打手")
                if hasattr(parent, 'show_popup'):
                    parent.show_popup("打手已就位")
                return "雇佣打手成功"
            return "雇佣失败"
        
        # ─── 山贼谋划劫掠 ─────────────────────────────────────────────────────
        elif action_type == 'PLAN_RAID':
            if isinstance(child, NPC) and child.job in ['BANDIT', 'THUG']:
                # 增加下次劫掠的成功率
                raid_bonus = getattr(child, 'raid_bonus', 0)
                child.raid_bonus = min(raid_bonus + 0.15, 0.5)  # 最多+50%成功率
                child.ai_reason = "谋划已成"
                log_game_event(f"【山贼】{child.name} 在山寨谋划劫掠，下次出击成功率提升")
                if hasattr(parent, 'show_popup'):
                    parent.show_popup("计划周全")
                return "劫掠计划完成"
            return "谋划中..."
        
        # ─── 探监 ─────────────────────────────────────────────────────────────
        elif action_type == 'VISIT_PRISONER':
            if isinstance(child, NPC):
                # 探监可以获得情报或影响囚犯
                # 检查牢房是否有囚犯
                prisoner = None
                if hasattr(parent, 'stack_child'):
                    # 遍历堆叠链找囚犯
                    check = parent.stack_child
                    while check:
                        if hasattr(check, 'is_prisoner') and check.is_prisoner:
                            prisoner = check
                            break
                        check = getattr(check, 'stack_child', None)
                
                if prisoner:
                    # 与囚犯交流，可能获得情报
                    if random.random() < 0.3:
                        child.inventory['情报'] = child.inventory.get('情报', 0) + 1
                        log_game_event(f"{child.name} 探监时获得了{prisoner.name}的情报")
                        if hasattr(parent, 'show_popup'):
                            parent.show_popup("获得情报")
                        return "探监获得情报"
                    else:
                        log_game_event(f"{child.name} 探监了{prisoner.name}")
                        if hasattr(parent, 'show_popup'):
                            parent.show_popup("探监完毕")
                        return "探监完成"
                else:
                    if hasattr(parent, 'show_popup'):
                        parent.show_popup("牢房空空")
                    return "无人可探"
            return "探监中..."
        
        # ─── 治疗（转发到旧逻辑处理） ─────────────────────────────────────────
        elif action_type in ['HEAL', 'HEAL_SLOW']:
            # 这两个ACTION已经在上层有详细处理，这里不重复
            return None  # 返回None让上层继续处理
        
        # ─── 未知ACTION ─────────────────────────────────────────────────────
        else:
            log_game_event(f"[RECIPE] 未实现的ACTION类型: {action_type}", tag="WARN")
            return f"执行: {action_type}"
    
    def _do_gamble(self, child, parent, bet_amount, win_rate):
        """执行赌博逻辑"""
        if not isinstance(child, NPC):
            return "赌博失败"
        
        # 检查赌注
        if child.money < bet_amount:
            if hasattr(parent, 'show_popup'):
                parent.show_popup("钱不够")
            return "赌资不足"
        
        # 扣除赌注（配方已经扣过cost_money了，这里只处理结果）
        # 注意：cost_money已在上层扣除，这里处理输赢结果
        
        # 赌运受魅力影响
        charm = getattr(child, 'charm', 5)
        adjusted_rate = win_rate + (charm - 5) * 0.02  # 每点魅力+2%胜率
        adjusted_rate = max(0.1, min(0.7, adjusted_rate))  # 限制在10%-70%
        
        if random.random() < adjusted_rate:
            # 赢了！
            winnings = bet_amount * 2  # 翻倍
            child.money += winnings
            log_game_event(f"【赌博】{child.name} 赢了{winnings}铜！")
            if hasattr(parent, 'show_popup'):
                parent.show_popup(f"赢+{winnings}!")
            
            # 可能获得赌神标签
            if random.random() < 0.05:
                if not hasattr(child, 'tags'):
                    child.tags = []
                if 'LUCKY' not in child.tags:
                    child.tags.append('LUCKY')
                    log_game_event(f"【赌运】{child.name} 获得了「赌运亨通」称号！")
            
            return f"赢得{winnings}铜"
        else:
            # 输了
            log_game_event(f"【赌博】{child.name} 输了{bet_amount}铜...")
            if hasattr(parent, 'show_popup'):
                parent.show_popup(f"输-{bet_amount}")
            
            # 连输可能触发破产
            losses = getattr(child, '_consecutive_losses', 0) + 1
            child._consecutive_losses = losses
            if losses >= 3 and child.money < 5:
                child.ai_reason = "赌输了..."
                if hasattr(child, 'tags') and 'GAMBLER' not in child.tags:
                    child.tags.append('GAMBLER')
                log_game_event(f"【悲剧】{child.name} 连输{losses}把，几乎输光了...")
            
            return f"输掉{bet_amount}铜"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STAT 类型产出处理
    # ═══════════════════════════════════════════════════════════════════════════
    def _handle_stat_output(self, out_str, child, parent, player):
        """
        处理 STAT:XXX 类型的配方输出 - 状态/属性变化
        
        支持的STAT类型：
        - REST: 休息恢复体力
        - COMBAT_EXP: 战斗经验（提升攻击/防御）
        - KNOWLEDGE_EXP: 知识经验（提升智力）
        - MOOD_BOOST: 心情提升（提升好感/士气）
        - HUNGER_FULL: 吃饱（恢复体力）
        - ARMORY_STORED: 武库存储（增加武库库存）
        """
        parts = out_str.split(':')
        stat_type = parts[1] if len(parts) > 1 else ''
        
        if not isinstance(child, NPC):
            return "无效目标"
        
        # ─── 休息恢复 ─────────────────────────────────────────────────────────
        if stat_type == 'REST':
            heal_amt = 5
            old_hp = child.hp
            child.hp = min(child.max_hp, child.hp + heal_amt)
            if hasattr(parent, 'show_popup') and child.hp > old_hp:
                parent.show_popup(f"+{child.hp - old_hp}HP")
            return "休息完成"
        
        # ─── 战斗经验 ─────────────────────────────────────────────────────────
        elif stat_type == 'COMBAT_EXP':
            # 训练提升战斗属性
            exp_gain = random.uniform(0.3, 0.8)
            
            # 攻击提升
            old_atk = getattr(child, 'atk', 10)
            child.atk = min(old_atk + exp_gain, 35)  # 攻击上限35
            
            # 力量提升（小幅）
            old_str = getattr(child, 'strength', 5)
            child.strength = min(old_str + exp_gain * 0.3, 15)  # 力量上限15
            
            # 记录训练次数
            train_count = getattr(child, '_train_count', 0) + 1
            child._train_count = train_count
            
            child.ai_reason = "习武中"
            
            if hasattr(parent, 'show_popup'):
                parent.show_popup(f"武艺+{exp_gain:.1f}")
            
            log_game_event(f"[STAT] {child.name} 训练完成，攻击{old_atk:.1f}->{child.atk:.1f}")
            return f"武艺精进（第{train_count}次）"
        
        # ─── 知识经验 ─────────────────────────────────────────────────────────
        elif stat_type == 'KNOWLEDGE_EXP':
            # 读书/学习提升智力
            exp_gain = random.uniform(0.2, 0.5)
            
            old_wit = getattr(child, 'wit', 5)
            child.wit = min(old_wit + exp_gain, 18)  # 智力上限18
            
            # 记录学习次数
            study_count = getattr(child, '_study_count', 0) + 1
            child._study_count = study_count
            
            child.ai_reason = "苦读中"
            
            if hasattr(parent, 'show_popup'):
                parent.show_popup(f"学识+{exp_gain:.1f}")
            
            log_game_event(f"[STAT] {child.name} 学习完成，智力{old_wit:.1f}->{child.wit:.1f}")
            return f"增长见识（第{study_count}次）"
        
        # ─── 心情提升 ─────────────────────────────────────────────────────────
        elif stat_type == 'MOOD_BOOST':
            # 娱乐/放松提升心情
            mood_gain = random.randint(5, 15)
            
            # 提升士气（如果有）
            old_morale = getattr(child, 'morale', 50)
            child.morale = min(old_morale + mood_gain, 100)
            
            # 提升对玩家好感（如果是门客或关系好的NPC）
            if getattr(child, 'is_follower', False):
                old_aff = getattr(child, 'affinity_to_player', 0)
                child.affinity_to_player = min(old_aff + 2, 100)
            
            child.ai_reason = "心情愉悦"
            
            if hasattr(parent, 'show_popup'):
                parent.show_popup(f"心情+{mood_gain}")
            
            log_game_event(f"[STAT] {child.name} 心情提升，士气{old_morale}->{child.morale}")
            return "心情愉悦"
        
        # ─── 吃饱恢复 ─────────────────────────────────────────────────────────
        elif stat_type == 'HUNGER_FULL':
            # 用膳恢复体力（比REST更多）
            heal_amt = 15
            old_hp = child.hp
            child.hp = min(child.max_hp, child.hp + heal_amt)
            
            # 清除饥饿状态
            if hasattr(child, 'tags') and 'HUNGRY' in child.tags:
                child.tags.remove('HUNGRY')
            
            child.ai_reason = "酒足饭饱"
            
            if hasattr(parent, 'show_popup'):
                parent.show_popup(f"饱餐+{heal_amt}HP")
            
            log_game_event(f"[STAT] {child.name} 用膳完毕，体力{old_hp}->{child.hp}")
            return "酒足饭饱"
        
        # ─── 武库存储 ─────────────────────────────────────────────────────────
        elif stat_type == 'ARMORY_STORED':
            # 存入武器到武库
            if isinstance(parent, Building) and parent.building_type == 'ARMORY':
                # 增加武库库存计数
                stored = getattr(parent, 'armory_stock', 0) + 1
                parent.armory_stock = stored
                
                # 从NPC背包移除武器（如果配方要求）
                weapon_types = ['铁剑', '朴刀', '长枪', '大刀']
                for wt in weapon_types:
                    if child.inventory.get(wt, 0) > 0:
                        child.inventory[wt] -= 1
                        if child.inventory[wt] <= 0:
                            del child.inventory[wt]
                        break
                
                if hasattr(parent, 'show_popup'):
                    parent.show_popup(f"库存:{stored}")
                
                log_game_event(f"[STAT] {child.name} 向武库存入武器，当前库存{stored}")
                return f"武库库存+1（共{stored}）"
            return "存储失败"
        
        # ─── 未知STAT ─────────────────────────────────────────────────────────
        else:
            log_game_event(f"[RECIPE] 未实现的STAT类型: {stat_type}", tag="WARN")
            return f"状态变化: {stat_type}"


# ══════════════════════════════════════════════════════════════════════════════
# 全局缓存：资源 → 可产出该资源的建筑类型列表
# 启动时由 RecipeManager 构建，供任务指引等系统使用
# ══════════════════════════════════════════════════════════════════════════════
_RESOURCE_TO_BUILDING_CACHE: dict = {}  # {'生鱼': ['FISHPOND'], '木材': ['TREE'], ...}

def get_resource_building_map() -> dict:
    """
    获取资源→建筑类型的映射（全局缓存）
    
    返回格式: {'生鱼': ['FISHPOND'], '木材': ['TREE'], '浆果': ['BUSH', 'FARM'], ...}
    
    用于任务指引系统：根据任务目标物品找到应该去的建筑
    """
    global _RESOURCE_TO_BUILDING_CACHE
    if not _RESOURCE_TO_BUILDING_CACHE:
        # 首次调用时构建缓存
        _build_resource_building_cache()
    return _RESOURCE_TO_BUILDING_CACHE

def _build_resource_building_cache():
    """从 recipes.csv 构建资源→建筑映射缓存"""
    global _RESOURCE_TO_BUILDING_CACHE
    _RESOURCE_TO_BUILDING_CACHE.clear()
    
    path = resource_path('data/recipes.csv')
    if not os.path.exists(path):
        log_game_event("[RECIPE] recipes.csv 不存在，无法构建资源-建筑映射", tag="WARN")
        return
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 只处理在建筑上产出物品的配方
                if row.get('target_type') != 'BUILDING':
                    continue
                
                output = row.get('output', '')
                if not output.startswith('ITEM:'):
                    continue
                
                # 解析产出: ITEM:生鱼:1 -> 生鱼
                parts = output.split(':')
                if len(parts) < 2:
                    continue
                item_name = parts[1]
                
                # 获取建筑类型
                building_type = row.get('target_id', '')
                if not building_type:
                    continue
                
                # 添加到映射
                if item_name not in _RESOURCE_TO_BUILDING_CACHE:
                    _RESOURCE_TO_BUILDING_CACHE[item_name] = []
                if building_type not in _RESOURCE_TO_BUILDING_CACHE[item_name]:
                    _RESOURCE_TO_BUILDING_CACHE[item_name].append(building_type)
        
        log_game_event(f"[RECIPE] 资源-建筑映射构建完成: {len(_RESOURCE_TO_BUILDING_CACHE)} 种资源", tag="INIT")
    except Exception as e:
        log_game_event(f"[RECIPE] 构建资源-建筑映射失败: {e}", tag="ERROR")


class RecipeManager:
    def __init__(self):
        self.recipes = []
        self._load_recipes()
        # 初始化时确保全局缓存已构建
        get_resource_building_map()
    
    def get_recipes_for_building(self, building_type: str) -> list:
        """
        获取某个建筑类型相关的所有配方
        
        Args:
            building_type: 建筑类型（如 'MARKET', 'BUSH', 'FARM' 等）
            
        Returns:
            list: 与该建筑相关的配方列表，每个元素包含配方详情
        """
        result = []
        for r in self.recipes:
            # 只匹配 target_type 为 BUILDING 且 target_id 匹配的配方
            if r.get('target_type') == 'BUILDING' and r.get('target_id') == building_type:
                # 解析产出信息
                output_str = r.get('output', '')
                output_desc = ''
                if output_str.startswith('ITEM:'):
                    # 格式: ITEM:物品名:数量
                    parts = output_str.split(':')
                    if len(parts) >= 3:
                        output_desc = f"{parts[1]} x{parts[2]}"
                    elif len(parts) >= 2:
                        output_desc = f"{parts[1]} x1"
                elif output_str.startswith('STAT:'):
                    # 格式: STAT:属性名
                    stat_name = output_str.split(':')[1] if ':' in output_str else output_str
                    stat_map = {
                        'REST': '恢复体力',
                        'HUNGER_FULL': '恢复饱食',
                        'COMBAT_EXP': '战斗经验',
                        'KNOWLEDGE_EXP': '知识经验',
                        'MOOD_BOOST': '心情愉悦',
                    }
                    output_desc = stat_map.get(stat_name, stat_name)
                elif output_str.startswith('ACTION:'):
                    action_name = output_str.split(':')[1] if ':' in output_str else output_str
                    action_map = {
                        'HEAL': '治疗',
                        'HEAL_SLOW': '缓慢治疗',
                        'GAMBLE_SMALL': '小赌',
                        'GAMBLE_BIG': '豪赌',
                        'REPAIR': '修理',
                        'VISIT_PRISONER': '探监',
                    }
                    output_desc = action_map.get(action_name, action_name)
                elif output_str.startswith('BUILDING:'):
                    output_desc = f"建造 {output_str.split(':')[1]}"
                elif output_str == '_FUEL':
                    output_desc = '添加燃料'
                else:
                    output_desc = output_str
                
                # 解析输入要求
                input_req = r.get('input', 'ANY')
                input_desc = ''
                if input_req == 'ANY':
                    input_desc = '任何人'
                elif input_req == 'PLAYER':
                    input_desc = '玩家'
                elif input_req == 'FARMER':
                    input_desc = '农夫'
                elif input_req == 'MERCHANT':
                    input_desc = '商人'
                elif input_req == 'SCHOLAR':
                    input_desc = '学者'
                elif input_req == 'ARTISAN':
                    input_desc = '工匠'
                elif input_req == 'GUARD':
                    input_desc = '护卫'
                elif input_req == 'MONK':
                    input_desc = '僧侣'
                elif input_req == 'OFFICIAL':
                    input_desc = '官员'
                elif input_req == 'BANDIT':
                    input_desc = '山贼'
                elif input_req == 'HUNTER':
                    input_desc = '猎人'
                elif input_req == 'FISHERMAN':
                    input_desc = '渔夫'
                elif input_req == 'MINER':
                    input_desc = '矿工'
                elif input_req == 'WOODCUTTER':
                    input_desc = '樵夫'
                elif input_req == 'DANCER':
                    input_desc = '舞女'
                elif input_req == 'NONE':
                    input_desc = '无职业'
                else:
                    # 可能是物品名
                    input_desc = f"需要 {input_req}"
                
                # 额外消耗
                ext_input = r.get('ext_input', '')
                ext_desc = ''
                if ext_input:
                    parts = ext_input.split(':')
                    if len(parts) >= 2:
                        ext_desc = f" + {parts[0]} x{parts[1]}"
                
                # 金钱消耗
                cost_money = int(r.get('cost_money', 0) or 0)
                cost_desc = f" ({cost_money}文)" if cost_money > 0 else ''
                
                result.append({
                    'id': r.get('id', ''),
                    'desc': r.get('desc', ''),
                    'input': input_desc,
                    'output': output_desc,
                    'ext_input': ext_desc,
                    'cost': cost_desc,
                    'time': int(r.get('time', 100) or 100),
                })
        
        return result

    def _load_recipes(self):
        path = resource_path('data/recipes.csv')
        if not os.path.exists(path): return
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.recipes.append(row)
        self.recipes.sort(key=lambda x: int(x.get('req_count') or 1), reverse=True)

    def check_match(self, child, parent):
        """
        检查 child 堆叠在 parent 上是否符合某个配方
        """
        

        for r in self.recipes:
            # --- 1. 匹配输入 (Child) ---
            
            req_count = int(r.get('req_count') or 1)
            input_match = False
            req_input = r['input']
            
            # A. 职业匹配 (FARMER, PLAYER, ANY)
            if isinstance(child, NPC):
                if req_input == 'ANY': input_match = True
                elif req_input == 'PLAYER' and child.job == 'PLAYER': input_match = True
                elif req_input == child.job: input_match = True
            
            # B. 资源匹配 (Resource)
            elif isinstance(child, Resource):
                if child.item_type == req_input and child.count >=req_count:
                    input_match = True
                    
            if not input_match: continue

            # --- 2. 匹配目标 (Parent) ---
            target_match = False
            t_type = r['target_type']
            t_id = r['target_id']
            
            if t_type == 'BUILDING':
                if isinstance(parent, Building) and parent.building_type == t_id:
                    target_match = True
            elif t_type == 'NPC':
                if isinstance(parent, NPC) and (str(parent.id) == t_id or t_id == 'ANY'):
                    # 野外急救配方只在父卡重伤时才触发，避免普通NPC互相堆叠误匹配
                    if r.get('output', '').startswith('ACTION:HEAL'):
                        if parent.safety == SAFETY_DOWNED:
                            target_match = True
                    else:
                        target_match = True
            elif t_type == 'HUMAN':
                if isinstance(parent, NPC): target_match = True
            elif t_type == 'RESOURCE':
                if isinstance(parent, Resource) and parent.item_type == t_id:
                    if parent.count >= req_count:
                        target_match = True

            if not target_match: continue

            # --- 3. 额外条件 (背包里必须有东西，或有钱) ---
            # 检查钱 cost_money
            cost = int(r['cost_money']) if r['cost_money'] else 0
            if cost > 0:
                if not hasattr(child, 'money') or child.money < cost:
                    continue
                    
            # 检查额外物品 ext_input (例如 "GRAIN:1")
            ext = r.get('ext_input', '')
            if ext:
                req_item, req_amt = ext.split(':')
                # 只有 NPC 有背包能检查这个
                if not isinstance(child, NPC) or child.inventory.get(req_item, 0) < int(req_amt):
                    continue

            return RecipeProxy(r)
        return None


    # --- 回调逻辑 ---
    
    def _make_farmer(self, child, parent, player):
        child.job = 'FARMER'
        child.is_refugee = False
        child.ai_reason = "刚找到工作，准备干活" # 更新AI状态
        parent.show_popup("安置成功")
        child.bounce_off(parent)
        # [新增] 返回日志描述
        return f"【民生】将 {child.name} 安置于粮仓，转化为了农夫，生产力提升。"

    def _recruit_follower(self, child, parent, player):
        cost = 100 # 也可以读取变量
        if player.money >= cost:
            player.money -= cost
            child.is_follower = True
            child.is_refugee = False
            child.job = 'GUARD'
            child.atk = 15 # 护院攻击力高
            child.def_ = 5
            child.name = f"护院{child.name}"
            child.ai_reason = "听候差遣"
            player.followers_count += 1
            parent.show_popup(f"招募(-{cost})")
            child.bounce_off(parent)
            return f"【招募】花费 {cost} 招募了护院。"
        else:
            parent.show_popup("没钱!")
            child.bounce_off(parent)
            return None
        
    def _cook_food(self, child, parent, player):
       # child 是 Resource(浆果)
       # 销毁浆果，生成烤果
       # 由于 RecipeManager 目前处理的是 entity 转换，我们需要特殊处理 Resource 转换
       
       # 简单逻辑：修改 child 的属性变成烤果
       child.item_type = '烤果' # ITEM_COOKED
       child.name = '烤果'
       child.color = (200, 100, 50) # 烤熟的颜色
       # 只有玩家吃才加饱食度逻辑在 event_system 里处理，或者这里也可以加 buff
       parent.show_popup("滋滋冒油")
       child.bounce_off(parent)
       return "【烹饪】制作了美味的烤浆果。"