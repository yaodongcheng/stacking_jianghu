import random
import math
import pygame
from src.definitions import *
from src.entities import Player, NPC, Building,Resource
from src.data_loader import load_npcs_from_csv, load_buildings_from_csv
from src.social_system import social_manager

# ════════════════════════════════════════════════════════════════
# 建筑间距检查系统
# 确保所有建筑之间有足够的距离（至少2个网格 = 80像素）
# ════════════════════════════════════════════════════════════════
BUILDING_MIN_EDGE_DISTANCE = 80  # 建筑边缘之间的最小距离（2个网格 × 40像素）

def check_building_overlap(new_x, new_y, new_w, new_h, existing_buildings, min_edge_dist=BUILDING_MIN_EDGE_DISTANCE):
    """
    检查新建筑是否与已有建筑重叠或太近
    
    Args:
        new_x, new_y: 新建筑的中心坐标
        new_w, new_h: 新建筑的宽高（默认使用卡牌尺寸）
        existing_buildings: 已有建筑列表
        min_edge_dist: 边缘之间的最小距离
    
    Returns:
        bool: True = 位置安全，False = 太近或重叠
    """
    # 新建筑的边界（假设坐标是中心点）
    new_left = new_x - new_w // 2
    new_right = new_x + new_w // 2
    new_top = new_y - new_h // 2
    new_bottom = new_y + new_h // 2
    
    for b in existing_buildings:
        if not isinstance(b, Building):
            continue
        
        # 已有建筑的边界
        b_left = b.rect.left
        b_right = b.rect.right
        b_top = b.rect.top
        b_bottom = b.rect.bottom
        
        # 计算边缘之间的距离（取四个方向的最小非负距离）
        # 如果有重叠，距离为负
        h_dist = max(new_left - b_right, b_left - new_right)
        v_dist = max(new_top - b_bottom, b_top - new_bottom)
        
        # 如果水平和垂直都有间隙，取较小的
        # 如果任一方向重叠（负值），则另一方向需要有足够间隙
        if h_dist < 0 and v_dist < 0:
            # 完全重叠
            return False
        
        # 取实际的边缘距离
        edge_dist = max(h_dist, v_dist)
        
        if edge_dist < min_edge_dist:
            return False
    
    return True

def find_valid_building_position(base_x, base_y, existing_buildings, world_map=None, 
                                  spread=100, max_attempts=20, 
                                  building_w=CARD_W, building_h=CARD_H):
    """
    在基础位置附近找到一个有效的建筑放置位置
    
    Args:
        base_x, base_y: 基础位置
        existing_buildings: 已有建筑列表
        world_map: 世界地图（用于检查城墙）
        spread: 搜索范围
        max_attempts: 最大尝试次数
        building_w, building_h: 建筑尺寸
    
    Returns:
        (x, y): 有效位置，如果找不到则返回原始位置
    """
    # 首先检查基础位置是否可用
    if check_building_overlap(base_x, base_y, building_w, building_h, existing_buildings):
        return base_x, base_y
    
    # 螺旋搜索有效位置
    for attempt in range(max_attempts):
        # 逐渐扩大搜索范围
        current_spread = spread * (1 + attempt * 0.3)
        
        # 随机偏移
        offset_x = random.randint(int(-current_spread), int(current_spread))
        offset_y = random.randint(int(-current_spread), int(current_spread))
        
        new_x = base_x + offset_x
        new_y = base_y + offset_y
        
        # 确保在世界边界内
        if world_map:
            new_x = max(60, min(new_x, world_map.w - 60))
            new_y = max(60, min(new_y, world_map.h - 60))
            
            # 检查城墙碰撞
            test_rect = pygame.Rect(new_x - building_w//2, new_y - building_h//2, 
                                     building_w, building_h)
            wall_collision = False
            for wall in world_map.walls:
                if test_rect.colliderect(wall):
                    wall_collision = True
                    break
            if wall_collision:
                continue
        
        # 检查与其他建筑的距离
        if check_building_overlap(new_x, new_y, building_w, building_h, existing_buildings):
            return new_x, new_y
    
    # 找不到有效位置，返回原始位置（会记录警告）
    print(f"[WorldLoader] [!] 无法为建筑找到有效位置，原位置 ({base_x}, {base_y}) 可能与其他建筑重叠")
    return base_x, base_y

def validate_all_buildings(all_cards):
    """
    验证所有建筑之间的间距，返回重叠警告列表
    
    Returns:
        list: 警告信息列表
    """
    warnings = []
    buildings = [c for c in all_cards if isinstance(c, Building)]
    
    for i, b1 in enumerate(buildings):
        for j, b2 in enumerate(buildings):
            if j <= i:
                continue
            
            # 计算边缘距离
            h_dist = max(b1.rect.left - b2.rect.right, b2.rect.left - b1.rect.right)
            v_dist = max(b1.rect.top - b2.rect.bottom, b2.rect.top - b1.rect.bottom)
            edge_dist = max(h_dist, v_dist)
            
            if edge_dist < 0:
                warnings.append(f"建筑重叠: {b1.name}({b1.building_type}) 与 {b2.name}({b2.building_type})")
            elif edge_dist < BUILDING_MIN_EDGE_DISTANCE:
                warnings.append(f"建筑过近({edge_dist}px): {b1.name} 与 {b2.name}")

    return warnings


class WorldLoader:
    @staticmethod
    def init_world_entities(ctx, creation_result, npc_raw_data, scenario_type):
        """初始化实体(玩家、NPC、建筑)"""
        all_cards = []
        
       
        # 3. 玩家创建
        player = Player()
        player.name = creation_result['player_name']
        if creation_result['player_gender'] == 'Female':
            # 注意：这里需要确保 Player 类或者 Utils 能处理 Appearance，或者直接赋值路径
            # 假设 Player 内部还是使用 Appearance 类
            from src.utils import Appearance
            player.appearance = Appearance("assets/bodies/body_02.png", "assets/heads/head_02.png")
        all_cards.append(player)
        ctx.player = player

        # 4. 初始门客
        if creation_result['has_follower']:
            f_data = {'id': 9998, 'name': creation_result['follower_name'], 'job': 'GUARD', 
                      'body_img': 'body_01.png' if creation_result['follower_gender']=='Male' else 'body_02.png',
                      'head_img': 'head_01.png' if creation_result['follower_gender']=='Male' else 'head_02.png'}
            follower = NPC(f_data)
            follower.is_follower = True
            follower.set_pos(player.rect.centerx + 80, player.rect.centery)
            follower.money = 50
            follower.set_ai_mode("FOLLOW")
            all_cards.append(follower)
            player.followers_count = 1




        # =========================================
        # 分支 1: 乱世荒村 (新手引导)
        # =========================================
        if scenario_type == SCENARIO_TUTORIAL:
            # 初始建筑：1浆果丛，1树
            initial_buildings = [
                (ctx.world_map.city_rect.centerx + 110, ctx.world_map.city_rect.centery + 70, 'BUSH'),
                (ctx.world_map.city_rect.centerx + 120, ctx.world_map.city_rect.centery - 70, 'TREE'),
            ]
            for bx, by, btype in initial_buildings:
                all_cards.append(Building(bx, by, btype))
            
            # 村长 (关键NPC)
            village_head = NPC({'id': 9000, 'name': '村长', 'job': 'OFFICIAL', 'head_img': 'head_01.png'})
            cx, cy = ctx.world_map.city_rect.center
            village_head.set_pos(cx, cy)
            village_head.quest_icon_active = True
            village_head.state = STATE_EVENT # 初始静止
            all_cards.append(village_head)
            
            # 任务设置
            ctx.quest_manager.active_quest_id = "Q_PROLOGUE"
            ctx.quest_manager.quest_status = "AVAILABLE" 

        # =========================================
        # 分支 2: 闯荡汴京 (沙盒模式)
        # =========================================
        elif scenario_type == SCENARIO_SANDBOX:
            print("[WorldLoader] 正在加载汴京沙盒...")
            
            # ═══════════════════════════════════════════════════════════════
            # 【12.7】玩家出生在城东门外远处（开场演出：走向城门）
            # ═══════════════════════════════════════════════════════════════
            east_gate = ctx.world_map.gates['EAST']
            spawn_cx = east_gate.centerx + 400
            spawn_cy = east_gate.centery + 30
            player.set_pos(spawn_cx, spawn_cy)
            print(f"[WorldLoader] 玩家出生位置: ({spawn_cx}, {spawn_cy})")

            # 加载所有预定义NPC（从CSV），鱼西施/泼皮作为普通NPC生成
            predefined_npcs = load_npcs_from_csv("data/npc_data.csv")
            # ===============================================================
            # 从 CSV 加载所有建筑（基础设施、住房、农田、资源点）
            # ===============================================================
            building_cards, org_workplace_refs, npc_home_map, market_pos = \
                load_buildings_from_csv("data/building_config.csv", ctx.world_map, scenario_type)
            all_cards.extend(building_cards)

            # ── 组织区域配置表（用于NPC初始位置分散）─────────────────
            ORG_ZONE = {
                'heifeng_zhai':   'WILD',
                'qinglang_bang':  'WILD',
                'luopo_gang':     'WILD',
                'beggar_gang':    'SLUM',
            }

            cr = ctx.world_map.city_rect
            safe_margin = 120
            safe_left  = cr.left  + safe_margin
            safe_top   = cr.top   + safe_margin
            safe_right = cr.right - safe_margin
            safe_bot   = cr.bottom - safe_margin

            wm = ctx.world_map
            _safe_dist = 600
            _outer_zones = []
            if cr.top > _safe_dist + 100:
                _outer_zones.append((cr.left, wm.w - 50, 50, cr.top - _safe_dist))
            if wm.h - cr.bottom > _safe_dist + 100:
                _outer_zones.append((50, wm.w - 50, cr.bottom + _safe_dist, wm.h - 50))
            if cr.left > _safe_dist + 100:
                _outer_zones.append((50, cr.left - _safe_dist, 50, wm.h - 50))
            if wm.w - cr.right > _safe_dist + 200:
                _outer_zones.append((cr.right + _safe_dist + 100, wm.w - 50, 50, wm.h - 50))
            _outer_zones = [(x0, x1, y0, y1) for x0, x1, y0, y1 in _outer_zones
                            if x1 - x0 > 100 and y1 - y0 > 100]

            def _random_wild_pos():
                if _outer_zones:
                    z = random.choice(_outer_zones)
                    return random.randint(z[0], z[1]), random.randint(z[2], z[3])
                return random.randint(50, 200), random.randint(wm.h - 200, wm.h - 50)

            def _random_slum_pos():
                rect = wm.slum_rect
                return (random.randint(rect.left + 30, rect.right - 30),
                        random.randint(rect.top + 30, rect.bottom - 30))

            # ── 以组织工作建筑为参考点，分散放置NPC ──────────────────
            spawned_orgs = {}
            for org_id, bld in org_workplace_refs.items():
                spawned_orgs[org_id] = (bld.rect.centerx, bld.rect.centery)

            org_npc_counts = {}

            for npc in predefined_npcs:
                if npc.id == 9000 or (npc.job == 'NONE' and npc.name == '流民'):
                    continue
                if npc.hidden_job != 'NONE':
                    npc.job = npc.hidden_job

                org = getattr(npc, 'org_id', 'NONE')
                zone = ORG_ZONE.get(org, 'CITY')

                if zone == 'WILD':
                    b_x, b_y = _random_wild_pos()
                    if org != 'NONE' and org not in spawned_orgs:
                        spawned_orgs[org] = (b_x, b_y)

                elif zone == 'SLUM':
                    b_x, b_y = _random_slum_pos()
                    if org != 'NONE' and org not in spawned_orgs:
                        spawned_orgs[org] = (b_x, b_y)

                else:  # CITY
                    if org in spawned_orgs:
                        bx_grid, by_grid = spawned_orgs[org]
                    else:
                        bx_grid = random.randint(safe_left, safe_right)
                        by_grid = random.randint(safe_top, safe_bot)
                        spawned_orgs[org] = (bx_grid, by_grid)

                    # 螺旋分散
                    n = org_npc_counts.get(org, 0)
                    org_npc_counts[org] = n + 1
                    radius = 80 + (n // 6) * 55
                    angle = n * 2.399
                    b_x = bx_grid + int(math.cos(angle) * radius)
                    b_y = by_grid + int(math.sin(angle) * radius)
                    b_x += random.randint(-12, 12)
                    b_y += random.randint(-12, 12)
                    b_x = max(safe_left, min(b_x, safe_right))
                    b_y = max(safe_top, min(b_y, safe_bot))

                npc.set_pos(b_x, b_y)
                npc.clear_movement_target("初始分布")

                if npc.eco_status == 'RICH':     npc.money = 500
                elif npc.eco_status == 'ENOUGH': npc.money = 200
                else:                            npc.money = 50

                all_cards.append(npc)

                if hasattr(npc, 'relations'):
                    for rel_type, target_id in npc.relations.items():
                        social_manager.register_relation(npc.id, target_id, rel_type)

            # ════════════════════════════════════════════════════════════════
            # 【住所系统】统一分配 home_building
            # ════════════════════════════════════════════════════════════════
            # 第一步：CSV 中已定义的 NPC 个人住所
            for card in all_cards:
                if not isinstance(card, NPC) or card.job == 'PLAYER':
                    continue
                npc_id_str = str(card.id)
                if npc_id_str in npc_home_map:
                    card.home_building = npc_home_map[npc_id_str]

            # 第二步：兜底 - 仍无家的NPC动态生成 HOUSE
            npcs_need_home = [
                n for n in all_cards
                if isinstance(n, NPC) and n.job != 'PLAYER'
                and not getattr(n, 'is_refugee', False)
                and getattr(n, 'home_building', None) is None
            ]
            if npcs_need_home:
                import math as _math
                num_houses = len(npcs_need_home)
                house_area_w = safe_right - safe_left
                house_area_h = safe_bot - safe_top
                cols = max(1, int(_math.ceil(_math.sqrt(num_houses * house_area_w / max(house_area_h, 1)))))
                rows = max(1, int(_math.ceil(num_houses / cols)))
                cell_w = house_area_w // max(cols, 1)
                cell_h = house_area_h // max(rows, 1)

                for i, npc in enumerate(npcs_need_home):
                    r = i // cols
                    c = i % cols
                    hx = safe_left + c * cell_w + cell_w // 2 + random.randint(-20, 20)
                    hy = safe_top + r * cell_h + cell_h // 2 + random.randint(-20, 20)
                    hx = max(safe_left + 30, min(hx, safe_right - 30))
                    hy = max(safe_top + 30, min(hy, safe_bot - 30))
                    house = Building(hx, hy, 'HOUSE')
                    all_cards.append(house)
                    npc.home_building = house
                print(f"[WorldLoader] 兜底生成了 {num_houses} 栋住所")

            home_total = sum(1 for c in all_cards if isinstance(c, NPC) and getattr(c, 'home_building', None))
            print(f"[WorldLoader] 住所分配完成：{home_total} 个NPC有家")

            # 【住所系统】开局子时，将有家的NPC堆叠到民居上
            from src.definitions import STACK_OFFSET_Y
            for card in all_cards:
                if not isinstance(card, NPC) or card.job == 'PLAYER':
                    continue
                home = getattr(card, 'home_building', None)
                if home is None:
                    continue
                if home.stack_child is not None and home.stack_child != card:
                    card.set_pos(home.rect.centerx + random.randint(-40, 40),
                                 home.rect.centery + random.randint(-30, 30))
                    card.clear_movement_target("开局回家")
                    card.ai_reason = "睡觉中"
                    continue
                card.stack_parent = home
                home.stack_child = card
                card.set_pos(home.rect.centerx, home.rect.centery + STACK_OFFSET_Y)
                card.clear_movement_target("开局回家")
                card.ai_reason = "睡觉中"

            # ---- 解锁所有限制 ----
            from src.definitions import DEBUG_SKIP_YUXISHI, STATE_IDLE
            if DEBUG_SKIP_YUXISHI:
                # 【调试模式】跳过鱼西施主线，直接进入自由模式
                ctx.quest_manager.active_quest_id = "Q_FREE_PLAY"
                ctx.quest_manager.quest_status = "AVAILABLE"
                ctx.quest_manager.set_flag('guidance_visible', True)
                ctx.quest_manager.set_flag('refugee_unlocked', True)
                ctx.quest_manager.set_flag('intro_played', True)
                ctx.quest_manager.set_flag('intro_played_dialog', True)
                player.money = 100  # 调试模式：给一些初始金钱
                print(f"[WorldLoader] 【调试模式】跳过鱼西施主线，直接进入自由模式")
                
                # 【调试模式】释放开场剧情NPC，让他们自由活动
                if hasattr(ctx, 'event_actors') and ctx.event_actors:
                    for npc in ctx.event_actors:
                        npc.state = STATE_IDLE
                        npc.ai_reason = "自由活动"
                        npc._event_protected = False
                        print(f"[WorldLoader] 【调试模式】释放 {npc.name}: EVENT -> IDLE")
                    ctx.event_actors = []  # 清空事件演员列表
            else:
                # 沙盒模式：系统驱动开局（designDoc 12.7）
                # 子时（深夜）抵达小镇，开场独白立即触发
                ctx.quest_manager.active_quest_id = "Q_SETTLE_INTRO"
                ctx.quest_manager.quest_status = QS_ACTIVE
                # guidance_visible 保持 False，开场独白结束后由 UNLOCK_GUIDANCE 解锁
                ctx.quest_manager.set_flag('refugee_unlocked', True)
                ctx.quest_manager.set_flag('intro_played', True)
                ctx.quest_manager.set_flag('intro_played_dialog', True)
                # 12.7 初始状态：铜钱5，饥饿高（饱食度20→hunger=80），HP 70
                player.money = 5
                player.hunger = 80
                player.hp = 70

            print(f"[WorldLoader] 汴京加载完毕。NPC: {len(predefined_npcs)}，组织建筑: {len(org_workplace_refs)}")
            
            # ════════════════════════════════════════════════════════════════
            # 【最终验证】检查所有建筑之间的间距
            # ════════════════════════════════════════════════════════════════
            spacing_warnings = validate_all_buildings(all_cards)
            if spacing_warnings:
                print(f"[WorldLoader] [!] 建筑间距警告 ({len(spacing_warnings)} 个问题):")
                for warn in spacing_warnings[:10]:  # 只打印前10个避免刷屏
                    print(f"    - {warn}")
                if len(spacing_warnings) > 10:
                    print(f"    ... 以及 {len(spacing_warnings) - 10} 个其他问题")
            else:
                print(f"[WorldLoader] [ok] 所有建筑间距检查通过（最小间距 {BUILDING_MIN_EDGE_DISTANCE}px）")
            
        return all_cards
