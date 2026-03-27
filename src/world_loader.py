import random
import math
import pygame
from src.definitions import *
from src.entities import Player, NPC, Building,Resource
from src.data_loader import load_npcs_from_csv, register_npc_id_name
from src.social_system import social_manager
from src.data.character_seeds import SEEDS

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

# ════════════════════════════════════════════════════════════════
# 从 SEEDS 征调角色的辅助函数
# 将"演员"从人物设定库中拉出来，临时安排到开场剧情里
# ════════════════════════════════════════════════════════════════
def _recruit_actor_from_seeds(name):
    """从 SEEDS 中查找角色，返回适配 NPC 构造器的字典
    
    Args:
        name: 角色名称（必须存在于 SEEDS 中）
        
    Returns:
        dict: 可直接传给 NPC(data) 的字典
    """
    for idx, seed in enumerate(SEEDS):
        if seed['name'] == name:
            # 从 seed 构建 NPC 所需的数据字典
            # 使用 seed 的索引作为基础ID，避免与 CSV NPC 冲突
            # 8000+ 保留给事件角色
            npc_id = 8000 + idx
            
            # 根据性别选择外观
            is_female = seed.get('gender', 'Male') == 'Female'
            body_img = 'body_02.png' if is_female else 'body_01.png'
            head_img = 'head_02.png' if is_female else 'head_01.png'
            
            # 整合 tags
            tags = seed.get('tags', [])
            tags_str = ';'.join(tags) if isinstance(tags, list) else tags
            
            # 根据 power_type 映射 job（与 organization_system.py 保持一致）
            power_type = seed.get('power_type', '')
            tags = seed.get('tags', [])
            
            job_by_power = {
                '士': 'OFFICIAL',
                '农': 'FARMER',
                '工': 'ARTISAN',
                '商': 'MERCHANT',
                '学': 'SCHOLAR',
                '兵': 'GUARD',
                '游': 'GUARD',
                '匪': 'BANDIT',
            }
            job = job_by_power.get(power_type, 'NONE')
            
            # 特殊处理：带有 THUG tag 的匪类角色应该是泼皮（城内混混）而不是山贼（城外强盗）
            if 'THUG' in tags and power_type == '匪':
                job = 'THUG'
            
            return {
                'id': npc_id,
                'name': seed['name'],
                'job': job,
                'power_type': power_type,
                'social_level': seed.get('social_level', 1),
                'tags': tags_str,
                'body_img': body_img,
                'head_img': head_img,
                'desc': seed.get('desc', ''),
                'org_id': seed.get('org_id'),
                'org_role': seed.get('org_role'),
                'org_rank': seed.get('org_rank', 0),
                'personality': seed.get('personality'),
                'initial_dilemma': seed.get('initial_dilemma'),
            }
    
    raise ValueError(f"[WorldLoader] 致命错误：角色 '{name}' 不存在于 SEEDS 中！")


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
            # 【阶段1】玩家出生在城东门外，方便触发鱼西施事件
            # ═══════════════════════════════════════════════════════════════
            cr = ctx.world_map.city_rect
            # 城东门外位置（城墙右侧往外，留足野外空间）
            # 【修改】玩家出生在更远的东侧，更像从远处进城
            east_gate = ctx.world_map.gates['EAST']
            
            # 事件发生点：东门外 200 像素（鱼西施摊位）
            event_center_x = east_gate.centerx + 200
            event_center_y = east_gate.centery
            
            # 玩家出生点：事件东侧 350 像素（远处进城）
            spawn_cx = event_center_x + 350
            spawn_cy = event_center_y + 30  # 稍微错开Y轴，更自然
            player.set_pos(spawn_cx, spawn_cy)
            print(f"[WorldLoader] 玩家出生位置: ({spawn_cx}, {spawn_cy}), 事件中心: ({event_center_x}, {event_center_y})")
            
            # ─── 生成鱼西施事件相关NPC ───────────────────────────────────
            # 【核心理念】所有角色都从 character_seeds.py 征调，不再硬编码
            # 他们是沙盒世界里真正存在的居民，只是被临时"征调"来演出开场剧情
            
            # 首先加载所有预定义NPC（从CSV）
            predefined_npcs = load_npcs_from_csv("data/npc_data.csv")
            
            # ═══════════════════════════════════════════════════════════════
            # 【开场站位设计】
            # - 事件中心在东门外（玩家从远处看到）
            # - 鱼西施在中央，两个泼皮围着她（不重叠）
            # - 玩家在事件东侧远处，需要走过去才能介入
            # ═══════════════════════════════════════════════════════════════
            
            # 辅助函数：从已加载的NPC列表中查找角色
            def find_npc_by_name(npcs, name):
                for npc in npcs:
                    if npc.name == name:
                        return npc
                return None
            
            # 鱼西施（卖鱼妹子）- 从CSV加载的NPC中查找
            yuxishi = find_npc_by_name(predefined_npcs, '鱼西施')
            if yuxishi is None:
                # 兜底：如果CSV中没有，从SEEDS征调
                yuxishi_data = _recruit_actor_from_seeds('鱼西施')
                yuxishi = NPC(yuxishi_data)
            else:
                # 从列表中移除，避免重复
                predefined_npcs.remove(yuxishi)
            
            yuxishi.set_pos(event_center_x, event_center_y)  # 事件中心
            yuxishi.ai_reason = "卖鱼中..."
            yuxishi.state = STATE_EVENT  # 事件状态，不乱跑
            all_cards.append(yuxishi)
            
            # 泼皮牛二（骚扰者1 - 主说话者）- 从CSV加载的NPC中查找
            popi1 = find_npc_by_name(predefined_npcs, '泼皮牛二')
            if popi1 is None:
                popi1_data = _recruit_actor_from_seeds('泼皮牛二')
                popi1 = NPC(popi1_data)
            else:
                predefined_npcs.remove(popi1)
            
            # 站在鱼西施左前方（不与其他人重叠）
            popi1.set_pos(event_center_x - 70, event_center_y + 35)
            popi1.ai_reason = "调戏中..."
            popi1.state = STATE_EVENT
            popi1.is_main_speaker = True  # 标记为主说话者（对话中"泼皮"指他）
            all_cards.append(popi1)
            
            # 泼皮狗蛋（骚扰者2 - 帮腔者）- 从CSV加载的NPC中查找
            popi2 = find_npc_by_name(predefined_npcs, '泼皮狗蛋')
            if popi2 is None:
                popi2_data = _recruit_actor_from_seeds('泼皮狗蛋')
                popi2 = NPC(popi2_data)
            else:
                predefined_npcs.remove(popi2)
            
            # 站在鱼西施右前方（不与其他人重叠）
            popi2.set_pos(event_center_x + 70, event_center_y + 35)
            popi2.ai_reason = "帮腔中..."
            popi2.state = STATE_EVENT
            all_cards.append(popi2)
            
            # 存储引用，供后续剧情使用
            ctx.yuxishi_npc = yuxishi
            ctx.popi_npcs = [popi1, popi2]  # 第一个是主说话者

            # 存储事件中心位置，供镜头聚焦使用
            ctx.event_focus_point = (event_center_x, event_center_y)

            # 存储所有事件演员，确保他们保持在 EVENT 状态
            ctx.event_actors = [yuxishi, popi1, popi2]

            print(f"[WorldLoader] 征调演员完成: 鱼西施, 泼皮牛二, 泼皮狗蛋 (来自CSV数据)")
            print(f"[WorldLoader] 所有事件演员已设置为 STATE_EVENT 状态")
            org_building_map = {
                'SCHOOL': 'SCHOOL',
                'INN': 'INN',
                'GOV': 'GOV_OFFICE',
                'TEMPLE': 'TEMPLE',
                'SWEET': 'THEATER',
                'GOD_FORT': 'GOV_OFFICE',
                'NONE': 'HOUSE'
            }
            spawned_orgs = {}

            # ---- 安全建筑区域：城内中央区，留足边距避免贴墙 ----
            cr = ctx.world_map.city_rect
            safe_margin = 120  # 距城墙至少120像素
            safe_left  = cr.left  + safe_margin
            safe_top   = cr.top   + safe_margin
            safe_right = cr.right - safe_margin
            safe_bot   = cr.bottom - safe_margin
            # 城内建筑网格（3列×3行 = 9格）
            # 格子编号示意（r=行, c=列，从左到右、从上到下）：
            #   [0][1][2]
            #   [3][4][5]
            #   [6][7][8]
            col_step = (safe_right - safe_left) // 3
            row_step = (safe_bot - safe_top) // 3
            city_grid = [
                (safe_left + col_step * c + col_step // 2,
                 safe_top  + row_step * r + row_step // 2)
                for r in range(3) for c in range(3)
            ]
            # ── 固定公共/核心建筑位置 ──────────────────────────────
            # 索引0 = 左上    → 学堂（文人聚集）
            # 索引2 = 右上    → 寺庙（僧侣诵经）
            # 索引3 = 左中    → 市场（贸易区，靠近城门方向）
            # 索引4 = 正中心  → 府衙（城市权力中心）
            # 索引5 = 右中    → 医馆（城东救治）
            # 索引8 = 右下    → 工坊（城东南生产）
            RESERVED_SLOTS = {0, 2, 3, 4, 5, 8}  # 学堂、寺庙、市场、府衙、医馆、工坊
            school_pos   = city_grid[0]   # 左上：学堂
            temple_pos   = city_grid[2]   # 右上：寺庙
            market_pos   = city_grid[3]   # 左中：市场
            gov_pos      = city_grid[4]   # 正中心：府衙
            clinic_pos   = city_grid[5]   # 右中：医馆
            workshop_pos = city_grid[8]   # 右下：工坊
            # 组织建筑只能使用未被保留的格子
            org_slots = [p for i, p in enumerate(city_grid) if i not in RESERVED_SLOTS]

            # ---- 核心公共建筑 ----
            all_cards.append(Building(gov_pos[0],      gov_pos[1],      'GOV_OFFICE'))  # 府衙居中
            
            # ════════════════════════════════════════════════════════════════
            # 【新增】城内多个同类建筑，避免NPC都挤在一处
            # ════════════════════════════════════════════════════════════════
            
            # 主市场（城西）：初始有基础库存
            market_bld = Building(market_pos[0],   market_pos[1],   'MARKET')
            market_bld.inventory = {
                ITEM_GRAIN: 10,  # 粮食（供 NPC 买来吃）
                '棉袄':      5,   # 棉袄（供 NPC 买来抵寒）
                ITEM_COIN:  100, # 初始铜钱（市场的营运资金）
            }
            all_cards.append(market_bld)
            
            # 副市场（城东南）：第二个交易点
            market2_x = safe_right - col_step // 3
            market2_y = safe_bot - row_step // 3
            market_bld2 = Building(market2_x, market2_y, 'MARKET')
            market_bld2.inventory = {
                ITEM_GRAIN: 5,
                ITEM_COIN:  50,
            }
            all_cards.append(market_bld2)
            
            # 小摊（城北）：第三个小型交易点
            market3_x = cr.centerx + 80
            market3_y = safe_top + row_step // 4
            market_bld3 = Building(market3_x, market3_y, 'MARKET')
            market_bld3.inventory = {
                ITEM_COIN:  30,
            }
            all_cards.append(market_bld3)
            
            print(f"[WorldLoader] 生成了 3 个市场/交易点")
            
            all_cards.append(Building(clinic_pos[0],   clinic_pos[1],   'CLINIC'))      # 医馆右中
            all_cards.append(Building(workshop_pos[0], workshop_pos[1], 'WORKSHOP'))    # 工坊右下
            
            # ---- 阶段1新增：学堂和寺庙（为学者和僧侣提供工作场所）----
            all_cards.append(Building(school_pos[0], school_pos[1], 'SCHOOL'))   # 学堂左上
            all_cards.append(Building(temple_pos[0], temple_pos[1], 'TEMPLE'))   # 寺庙右上
            spawned_orgs['SCHOOL'] = school_pos  # 预注册，避免重复生成
            spawned_orgs['TEMPLE'] = temple_pos  # 预注册，避免重复生成
            
            # ════════════════════════════════════════════════════════════════
            # 【新增】城内休闲建筑：茶馆、酒楼（供高等级NPC享乐）
            # ════════════════════════════════════════════════════════════════
            # 茶馆（城中偏北）
            teahouse_x = cr.centerx - 100
            teahouse_y = safe_top + row_step // 2
            all_cards.append(Building(teahouse_x, teahouse_y, 'TEAHOUSE'))
            
            # 酒楼（城中偏南）
            tavern_x = cr.centerx + 100
            tavern_y = safe_bot - row_step // 2
            all_cards.append(Building(tavern_x, tavern_y, 'TAVERN'))
            
            print(f"[WorldLoader] 生成了茶馆和酒楼（供高等级NPC休闲）")

            # ════════════════════════════════════════════════════════════════
            # 城外农田：均匀分布在城池四周（北、南、西三个方向，东边留给开局事件）
            # ════════════════════════════════════════════════════════════════
            wm = ctx.world_map
            cr = ctx.world_map.city_rect
            farm_margin = 100  # 距城墙的距离
            
            farm_positions = []
            
            # 西侧农田（城西门外，2块）
            west_x = cr.left - farm_margin - 80
            farm_positions.append((west_x, cr.centery - 150))
            farm_positions.append((west_x, cr.centery + 150))
            
            # 北侧农田（城北门外，2块）
            north_y = cr.top - farm_margin - 80
            farm_positions.append((cr.centerx - 200, north_y))
            farm_positions.append((cr.centerx + 200, north_y))
            
            # 南侧农田（城南门外，2块）
            south_y = cr.bottom + farm_margin + 80
            farm_positions.append((cr.centerx - 200, south_y))
            farm_positions.append((cr.centerx + 200, south_y))
            
            # 西北角农田（1块）
            farm_positions.append((cr.left - farm_margin - 150, cr.top - farm_margin - 50))
            
            # 西南角农田（1块）
            farm_positions.append((cr.left - farm_margin - 150, cr.bottom + farm_margin + 50))
            
            # 确保农田在世界边界内
            for fx, fy in farm_positions:
                fx = max(60, min(fx, wm.w - 60))
                fy = max(60, min(fy, wm.h - 60))
                all_cards.append(Building(int(fx), int(fy), 'FARM'))
            
            print(f"[WorldLoader] 生成了 {len(farm_positions)} 块农田分布在城池周围")

            # ════════════════════════════════════════════════════════════════
            # 【重构】城外资源点：均匀分散分布，避开城墙
            # 使用随机偏移确保资源不会太集中
            # ════════════════════════════════════════════════════════════════
            wm = ctx.world_map
            wall_thick = wm.wall_thick
            resource_count = 0
            
            # 辅助函数：在指定区域内生成随机位置，避开城墙，并检查建筑间距
            def safe_pos(base_x, base_y, spread_x=80, spread_y=80):
                """生成安全的随机位置，确保不与城墙重叠，且与其他建筑保持2格(80px)间距"""
                for _ in range(20):  # 增加尝试次数确保能找到合适位置
                    x = base_x + random.randint(-spread_x, spread_x)
                    y = base_y + random.randint(-spread_y, spread_y)
                    # 确保在世界边界内
                    x = max(60, min(x, wm.w - 60))
                    y = max(60, min(y, wm.h - 60))
                    # 检查是否与城墙重叠
                    test_rect = pygame.Rect(x - 20, y - 20, 40, 40)
                    wall_collision = False
                    for wall in wm.walls:
                        if test_rect.colliderect(wall):
                            wall_collision = True
                            break
                    if wall_collision:
                        continue
                    # 检查与其他建筑的间距（至少2格=80像素）
                    if check_building_overlap(x, y, CARD_W, CARD_H, all_cards):
                        return x, y
                # 兜底：使用find_valid_building_position做最后挣扎
                return find_valid_building_position(base_x, base_y, all_cards, wm, 
                                                    spread=max(spread_x, spread_y) * 2)
            
            # ═══════════════════════════════════════════════════════════════
            # 【中立区】城东门外：玩家开局区域，资源大范围分散分布
            # 【修复】资源点远离城门，沿城墙外侧均匀分布
            # ═══════════════════════════════════════════════════════════════
            east_gate = wm.gates['EAST']
            gate_cx = east_gate.centerx
            gate_cy = east_gate.centery
            
            # 城东河滩群（3个河滩，远离城门大范围分散）
            fishpond_positions = [
                (gate_cx + 350, gate_cy - 350),   # 东北远处
                (gate_cx + 450, gate_cy + 200),   # 东南远处
                (gate_cx + 500, gate_cy - 80),    # 正东远处
            ]
            for bx, by in fishpond_positions:
                px, py = safe_pos(bx, by, 80, 80)
                all_cards.append(Building(px, py, 'FISHPOND'))
                resource_count += 1
            
            # 城东浆果丛（4个，大范围散布远离城门）
            bush_positions_east = [
                (gate_cx + 250, gate_cy - 400),   # 东北
                (gate_cx + 550, gate_cy - 200),   # 远东偏北
                (gate_cx + 500, gate_cy + 350),   # 远东南
                (gate_cx + 300, gate_cy + 450),   # 东南角
            ]
            for bx, by in bush_positions_east:
                px, py = safe_pos(bx, by, 100, 100)
                all_cards.append(Building(px, py, 'BUSH'))
                resource_count += 1
            
            # 城东树林（3棵，分散在远处）
            tree_positions_east = [
                (gate_cx + 600, gate_cy - 100),   # 远东
                (gate_cx + 550, gate_cy + 150),   # 远东南
                (gate_cx + 400, gate_cy - 280),   # 东北
            ]
            for bx, by in tree_positions_east:
                px, py = safe_pos(bx, by, 70, 70)
                all_cards.append(Building(px, py, 'TREE'))
                resource_count += 1
            
            print(f"[WorldLoader] 城东中立区: 3河滩 + 4浆果丛 + 3树林（分散远离城门）")
            
            # ═══════════════════════════════════════════════════════════════
            # 西侧区域：树林为主
            # ═══════════════════════════════════════════════════════════════
            west_gate = wm.gates['WEST']
            west_cx = west_gate.centerx
            west_cy = west_gate.centery
            
            # 西侧树林（6棵，沿城墙外侧分散）
            tree_positions_west = [
                (west_cx - 150, west_cy - 300),
                (west_cx - 200, west_cy - 100),
                (west_cx - 180, west_cy + 100),
                (west_cx - 220, west_cy + 280),
                (west_cx - 300, west_cy - 200),
                (west_cx - 350, west_cy + 50),
            ]
            for bx, by in tree_positions_west:
                px, py = safe_pos(bx, by, 80, 80)
                all_cards.append(Building(px, py, 'TREE'))
                resource_count += 1
            
            # 西侧浆果丛（3个）
            bush_positions_west = [
                (west_cx - 120, west_cy + 350),
                (west_cx - 250, west_cy - 350),
                (west_cx - 400, west_cy + 150),
            ]
            for bx, by in bush_positions_west:
                px, py = safe_pos(bx, by, 60, 60)
                all_cards.append(Building(px, py, 'BUSH'))
                resource_count += 1
            
            # ═══════════════════════════════════════════════════════════════
            # 北侧区域：浆果丛为主 + 河滩
            # ═══════════════════════════════════════════════════════════════
            north_gate = wm.gates['NORTH']
            north_cx = north_gate.centerx
            north_cy = north_gate.centery
            
            # 北侧浆果丛（5个，横向分散）
            bush_positions_north = [
                (north_cx - 400, north_cy - 150),
                (north_cx - 200, north_cy - 200),
                (north_cx + 100, north_cy - 180),
                (north_cx + 300, north_cy - 220),
                (north_cx + 450, north_cy - 150),
            ]
            for bx, by in bush_positions_north:
                px, py = safe_pos(bx, by, 70, 50)
                all_cards.append(Building(px, py, 'BUSH'))
                resource_count += 1
            
            # 北侧树林（2棵）
            tree_positions_north = [
                (north_cx - 350, north_cy - 280),
                (north_cx + 380, north_cy - 300),
            ]
            for bx, by in tree_positions_north:
                px, py = safe_pos(bx, by, 60, 40)
                all_cards.append(Building(px, py, 'TREE'))
                resource_count += 1
            
            # 北侧河滩（2个）
            fishpond_north = [
                (north_cx - 100, north_cy - 350),
                (north_cx + 200, north_cy - 380),
            ]
            for bx, by in fishpond_north:
                px, py = safe_pos(bx, by, 50, 40)
                all_cards.append(Building(px, py, 'FISHPOND'))
                resource_count += 1
            
            # ═══════════════════════════════════════════════════════════════
            # 南侧区域：混合资源
            # ═══════════════════════════════════════════════════════════════
            south_gate = wm.gates['SOUTH']
            south_cx = south_gate.centerx
            south_cy = south_gate.centery
            
            # 南侧树林（4棵）
            tree_positions_south = [
                (south_cx - 350, south_cy + 150),
                (south_cx - 150, south_cy + 220),
                (south_cx + 200, south_cy + 180),
                (south_cx + 400, south_cy + 200),
            ]
            for bx, by in tree_positions_south:
                px, py = safe_pos(bx, by, 70, 60)
                all_cards.append(Building(px, py, 'TREE'))
                resource_count += 1
            
            # 南侧浆果丛（3个）
            bush_positions_south = [
                (south_cx - 250, south_cy + 300),
                (south_cx + 50, south_cy + 350),
                (south_cx + 350, south_cy + 320),
            ]
            for bx, by in bush_positions_south:
                px, py = safe_pos(bx, by, 60, 50)
                all_cards.append(Building(px, py, 'BUSH'))
                resource_count += 1
            
            # 南侧矿山（2个）
            mine_south = [
                (south_cx + 450, south_cy + 280),
                (south_cx - 400, south_cy + 350),
            ]
            for bx, by in mine_south:
                px, py = safe_pos(bx, by, 50, 40)
                all_cards.append(Building(px, py, 'MINE'))
                resource_count += 1
            
            # ═══════════════════════════════════════════════════════════════
            # 四个角落区域：特色资源
            # ═══════════════════════════════════════════════════════════════
            
            # 西北角：矿山区（4个矿山）
            nw_base_x = cr.left - 400
            nw_base_y = cr.top - 300
            mine_nw = [
                (nw_base_x, nw_base_y),
                (nw_base_x - 150, nw_base_y + 100),
                (nw_base_x + 100, nw_base_y + 150),
                (nw_base_x - 100, nw_base_y + 250),
            ]
            for bx, by in mine_nw:
                px, py = safe_pos(bx, by, 80, 80)
                all_cards.append(Building(px, py, 'MINE'))
                resource_count += 1
            
            # 西南角：树林带（5棵树）
            sw_base_x = cr.left - 350
            sw_base_y = cr.bottom + 250
            tree_sw = [
                (sw_base_x, sw_base_y),
                (sw_base_x - 120, sw_base_y + 80),
                (sw_base_x + 80, sw_base_y + 150),
                (sw_base_x - 180, sw_base_y + 200),
                (sw_base_x + 50, sw_base_y + 280),
            ]
            for bx, by in tree_sw:
                px, py = safe_pos(bx, by, 70, 70)
                all_cards.append(Building(px, py, 'TREE'))
                resource_count += 1
            
            # 东北角：河滩 + 浆果（3河滩 + 3浆果）
            ne_base_x = cr.right + 300
            ne_base_y = cr.top - 250
            fishpond_ne = [
                (ne_base_x, ne_base_y),
                (ne_base_x + 150, ne_base_y + 100),
                (ne_base_x + 80, ne_base_y + 200),
            ]
            for bx, by in fishpond_ne:
                px, py = safe_pos(bx, by, 60, 60)
                all_cards.append(Building(px, py, 'FISHPOND'))
                resource_count += 1
            
            bush_ne = [
                (ne_base_x + 200, ne_base_y - 50),
                (ne_base_x + 280, ne_base_y + 150),
                (ne_base_x - 80, ne_base_y + 250),
            ]
            for bx, by in bush_ne:
                px, py = safe_pos(bx, by, 50, 50)
                all_cards.append(Building(px, py, 'BUSH'))
                resource_count += 1
            
            # 东南角：浆果 + 树（4浆果 + 3树）
            se_base_x = cr.right + 350
            se_base_y = cr.bottom + 200
            bush_se = [
                (se_base_x, se_base_y),
                (se_base_x + 130, se_base_y + 80),
                (se_base_x + 60, se_base_y + 180),
                (se_base_x + 200, se_base_y + 150),
            ]
            for bx, by in bush_se:
                px, py = safe_pos(bx, by, 60, 60)
                all_cards.append(Building(px, py, 'BUSH'))
                resource_count += 1
            
            tree_se = [
                (se_base_x + 250, se_base_y + 50),
                (se_base_x + 180, se_base_y + 250),
                (se_base_x - 100, se_base_y + 280),
            ]
            for bx, by in tree_se:
                px, py = safe_pos(bx, by, 50, 50)
                all_cards.append(Building(px, py, 'TREE'))
                resource_count += 1
            
            print(f"[WorldLoader] 生成了 {resource_count} 个城外资源点（分散分布）")

            # ---- 组织建筑，占城内剩余格 ----
            slot_idx = 0
            cx, cy = cr.center  # 仅用于散兵NPC的偏移参考
            # 预注册已生成的固定建筑，让对应 org 的 NPC 直接归属，不重复生成建筑
            spawned_orgs['GOV']     = gov_pos       # 府衙 org → 固定中心位置
            spawned_orgs['GOD_FORT']= gov_pos       # 神侯府也归属府衙（同类型）

            # ── 建筑位置索引（用于NPC开局分散就位）────────────────────────────────
            # 结构: org_id → (建筑中心x, 建筑中心y)
            # 已注册的固定建筑直接复用，避免重复生成
            # ── 统计每个组织已经生成了多少NPC，用于螺旋式分散偏移 ──
            org_npc_counts = {}   # org_id → 已放置NPC数量

            for npc in predefined_npcs:
                if npc.id == 9000 or (npc.job == 'NONE' and npc.name == '流民'):
                    continue
                if npc.hidden_job != 'NONE':
                    npc.job = npc.hidden_job

                org = getattr(npc, 'org_id', 'NONE')
                b_x, b_y = 0, 0

                # ════════════════════════════════════════════════════════════════
                # 土匪/山贼/黑风寨 → 城外四周游荡（但避开城东门开局剧情区域）
                # 乞丐/流氓 → 城南贫民窟散养
                # 泼皮牛二/狗蛋由剧情系统单独生成，这里跳过
                # ════════════════════════════════════════════════════════════════
                # 【修复】heifeng_zhai（黑风寨）成员应该在城外，不是城内
                is_outlaw = (npc.job == 'BANDIT' or 
                             org == 'BANDIT_ZHAI' or 
                             org == 'heifeng_zhai')
                
                # 泼皮牛二和泼皮狗蛋由剧情系统征调，这里跳过
                from src.definitions import NPC_POPI_NIUER, NPC_POPI_GOUDAN
                if npc.name in [NPC_POPI_NIUER, NPC_POPI_GOUDAN]:
                    print(f"[WorldLoader] 跳过 {npc.name}，由剧情系统征调")
                    continue
                
                if is_outlaw:
                    # 山贼/黑风寨分布在城外野外的边缘区域
                    # 【修复】距离城墙至少 600px，确保在 bandit_zones 范围内
                    wm = ctx.world_map
                    cr = wm.city_rect
                    safe_dist = 600  # 距离城墙的最小安全距离（与 bandit_zones 边距一致）
                    
                    # 定义城外边缘区域（远离城墙）
                    # 格式: (min_x, max_x, min_y, max_y)
                    # [修复] 北部区域太小时改用整个北部野外区域
                    outer_zones = []
                    
                    # 北部区域：如果城墙距离顶部足够远，就用北部
                    if cr.top > safe_dist + 100:
                        outer_zones.append((50, wm.w - 50, 50, cr.top - safe_dist))
                    
                    # 南部区域：如果城墙距离底部足够远，就用南部
                    if wm.h - cr.bottom > safe_dist + 100:
                        outer_zones.append((50, wm.w - 50, cr.bottom + safe_dist, wm.h - 50))
                    
                    # 西部区域：如果城墙距离左侧足够远，就用西部
                    if cr.left > safe_dist + 100:
                        outer_zones.append((50, cr.left - safe_dist, 50, wm.h - 50))
                    
                    # 东部区域（避开剧情区但可以用远东）：如果右侧空间足够
                    if wm.w - cr.right > safe_dist + 200:
                        outer_zones.append((cr.right + safe_dist + 100, wm.w - 50, 50, wm.h - 50))
                    
                    # 过滤掉无效区域（宽度或高度太小）
                    valid_zones = []
                    for zone in outer_zones:
                        w = zone[1] - zone[0]
                        h = zone[3] - zone[2]
                        if w > 100 and h > 100:
                            valid_zones.append(zone)
                    
                    if valid_zones:
                        zone = random.choice(valid_zones)
                        b_x = random.randint(max(50, zone[0]), min(zone[1], wm.w - 50))
                        b_y = random.randint(max(50, zone[2]), min(zone[3], wm.h - 50))
                    else:
                        # 兜底：放在地图左下角
                        b_x = random.randint(50, 200)
                        b_y = random.randint(wm.h - 200, wm.h - 50)
                    
                elif org == 'BEGGAR' or npc.job == 'THUG':
                    # 乞丐和泼皮 → 贫民窟（城南）
                    rect = ctx.world_map.slum_rect
                    b_x = random.randint(rect.left + 30, rect.right - 30)
                    b_y = random.randint(rect.top + 30, rect.bottom - 30)
                else:
                    # 正规组织 → 分配城内格子（每个org生成一栋建筑）
                    if org not in spawned_orgs:
                        if slot_idx < len(org_slots):
                            bx_grid, by_grid = org_slots[slot_idx]
                            slot_idx += 1
                        else:
                            # 格子用完，城内安全区随机
                            bx_grid = random.randint(safe_left, safe_right)
                            by_grid = random.randint(safe_top,  safe_bot)
                        b_type = org_building_map.get(org, 'HOUSE')
                        all_cards.append(Building(bx_grid, by_grid, b_type))
                        spawned_orgs[org] = (bx_grid, by_grid)

                    bx_grid, by_grid = spawned_orgs[org]

                    # ── 螺旋分散：让同一建筑下的多个NPC以扇形散开，不堆叠 ──
                    n = org_npc_counts.get(org, 0)
                    org_npc_counts[org] = n + 1
                    # 半径和角度：第0个人在建筑正右方，之后依次旋转约137°（黄金角）
                    radius  = 80 + (n // 6) * 55       # 每圈6人后扩大半径
                    angle   = n * 2.399                 # 黄金角弧度，避免对齐成行
                    b_x = bx_grid + int(math.cos(angle) * radius)
                    b_y = by_grid + int(math.sin(angle) * radius)

                    # 加一点随机抖动，让排列不那么机械
                    b_x += random.randint(-12, 12)
                    b_y += random.randint(-12, 12)

                    # 防止超出城内安全边界
                    b_x = max(safe_left, min(b_x, safe_right))
                    b_y = max(safe_top,  min(b_y, safe_bot))

                npc.set_pos(b_x, b_y)
                npc.clear_movement_target("初始分布")  # 确保目标同步

                if npc.eco_status == 'RICH':     npc.money = 500
                elif npc.eco_status == 'ENOUGH': npc.money = 200
                else:                            npc.money = 50

                all_cards.append(npc)

                if hasattr(npc, 'relations'):
                    for rel_type, target_id in npc.relations.items():
                        social_manager.register_relation(npc.id, target_id, rel_type)

            # ---- 初始散落资源（放在市场旁边，方便捡取）----
            mx, my = market_pos
            all_cards.append(Resource(mx + 80, my + 60, ITEM_WOOD,  count=5))
            all_cards.append(Resource(mx - 80, my + 60, ITEM_BERRY, count=5))
            all_cards.append(Resource(mx,      my + 90, ITEM_COIN,  count=10))

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
                # 【修改】沙盒模式以鱼西施事件作为开场
                ctx.quest_manager.active_quest_id = "Q_YUXISHI_TRIGGER"
                ctx.quest_manager.quest_status = "AVAILABLE"
                ctx.quest_manager.set_flag('guidance_visible', True)
                ctx.quest_manager.set_flag('refugee_unlocked', True)
                # 设置标记让开场自动触发对话
                ctx.quest_manager.set_flag('sandbox_intro_ready', True)
                player.money = 0  # 沙盒模式：初始无金钱，需通过任务赚取

            print(f"[WorldLoader] 汴京加载完毕。NPC: {len(predefined_npcs)}，组织建筑: {len(spawned_orgs)}")
            
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
