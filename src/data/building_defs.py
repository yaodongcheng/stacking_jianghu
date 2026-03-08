# src/data/building_defs.py
"""
建筑定义数据库 - 北宋汴京建筑类型
每种建筑属于特定势力类型，产出特定物品，形成完整经济循环。

势力类型对应：
- 士(COURT): 府衙、岗哨、牢房、武库
- 农(LANDOWNER): 农田、粮仓、磨坊、牧场、猎场
- 工(ARTISAN): 工坊、铁匠铺、织坊、窑场、首饰铺
- 商(MERCHANT): 集市、当铺、粮铺、茶馆、酒楼、马厩
- 学(SCHOLAR): 书院、医馆、药铺、书斋、寺庙、道观
- 兵(MILITARY): 校场、武库
- 游(MARTIAL): 瓦舍
- 匪(BANDIT): 赌坊、青楼、黑市、山寨
"""
from src.definitions import *

# 建筑定义库
# [重构] 移除了 'production' 字段，工作逻辑全部由 recipes.csv 驱动
BUILDING_DB = {
    # ══════════════════════════════════════════════════════════════
    # 自然资源建筑（无势力归属）
    # ══════════════════════════════════════════════════════════════
    'BUSH': {
        'name': '浆果丛', 'type': 'BUSH', 'work_time': 0,
        'power_type': None,
        'desc': '可采集浆果。'
    },
    'TREE': {
        'name': '枯树', 'type': 'TREE', 'work_time': 0,
        'power_type': None,
        'desc': '可伐木。'
    },
    'MINE': {
        'name': '矿山', 'type': 'MINE', 'work_time': 0,
        'power_type': None,
        'desc': '可采集石料和铁料。'
    },
    'FISHPOND': {
        'name': '河滩', 'type': 'FISHPOND', 'work_time': 0,
        'power_type': None,
        'desc': '可捕鱼。'
    },
    'CAMPFIRE': {
        'name': '篝火', 'type': 'CAMPFIRE', 'work_time': 0,
        'power_type': None,
        'desc': '提供温暖，可烹饪。',
        'is_heat_source': True,
        'heat_range': 150,
        'fuel_max': 500,
        'fuel_burn_rate': 1,
    },
    
    # ══════════════════════════════════════════════════════════════
    # 朝廷/军事势力建筑 (士/兵)
    # ══════════════════════════════════════════════════════════════
    'GOV_OFFICE': {
        'name': '府衙', 'type': 'GOV_OFFICE', 'work_time': 0,
        'power_type': '士',
        'desc': '官吏办公，维护治安，是朝廷权力的象征。',
        'base_fee': 0,  # 府衙不收使用费
        'strategic_value': 5,  # 战略价值最高
    },
    'GATEHOUSE': {
        'name': '岗哨', 'type': 'GATEHOUSE', 'work_time': 0,
        'power_type': '士',
        'desc': '城门关卡，检查过往行人，控制进出。',
        'base_fee': 10,  # 过路费
        'can_block_passage': True,  # 可以阻挡通行
    },
    'JAIL': {
        'name': '牢房', 'type': 'JAIL', 'work_time': 0,
        'power_type': '士',
        'desc': '关押犯人之所，森严阴冷。',
        'base_fee': 20,  # 探监费
        'strategic_value': 3,
    },
    'BARRACKS': {
        'name': '校场', 'type': 'BARRACKS', 'work_time': 0,
        'power_type': '兵',
        'desc': '训练武艺的场所，提升战斗能力。',
        'base_fee': 5,
    },
    'ARMORY': {
        'name': '武库', 'type': 'ARMORY', 'work_time': 0,
        'power_type': '兵',
        'desc': '存储兵器甲胄的仓库。',
        'base_fee': 0,
        'strategic_value': 4,
    },

    # ══════════════════════════════════════════════════════════════
    # 农业势力建筑 (农)
    # ══════════════════════════════════════════════════════════════
    'FARM': {
        'name': '农田', 'type': 'FARM', 'work_time': 0,
        'power_type': '农',
        'desc': '需农夫耕种，产出粮食。'
    },
    'GRANARY': {
        'name': '官仓', 'type': 'GRANARY', 'work_time': 0,
        'power_type': '农',
        'desc': '储存物资与安置流民。',
        'strategic_value': 3,
    },
    'MILL': {
        'name': '磨坊', 'type': 'MILL', 'work_time': 0,
        'power_type': '农',
        'desc': '加工粮食，磨面蒸馒头。',
        'base_fee': 3,
    },
    'RANCH': {
        'name': '牧场', 'type': 'RANCH', 'work_time': 0,
        'power_type': '农',
        'desc': '牧养牲畜，产出肉食和皮毛。',
        'base_fee': 5,
    },
    'HUNTING': {
        'name': '猎场', 'type': 'HUNTING', 'work_time': 0,
        'power_type': '农',
        'desc': '狩猎野物，采集药草。',
        'base_fee': 0,
    },
    'HOUSE': {
        'name': '民居', 'type': 'HOUSE', 'work_time': 0,
        'power_type': '农',
        'desc': '普通住宅，可休息恢复体力。'
    },

    # ══════════════════════════════════════════════════════════════
    # 商业势力建筑 (商)
    # ══════════════════════════════════════════════════════════════
    'MARKET': {
        'name': '集市', 'type': 'MARKET', 'work_time': 0,
        'power_type': '商',
        'desc': '交易场所，可出售物资。',
        'max_inventory': 50,
        'initial_inventory': {
            '谷物': 20, '棉袄': 5, '布料': 3, '精制器物': 2,
        },
        'strategic_value': 4,
    },
    'PAWNSHOP': {
        'name': '当铺', 'type': 'PAWNSHOP', 'work_time': 0,
        'power_type': '商',
        'desc': '质库典当，急需用钱时的好去处。',
        'base_fee': 0,  # 典当本身不收费，但典当价低于市价
    },
    'GRAIN_SHOP': {
        'name': '粮铺', 'type': 'GRAIN_SHOP', 'work_time': 0,
        'power_type': '商',
        'desc': '专营粮食买卖。',
        'initial_inventory': {'谷物': 30, '小麦': 20, '稻米': 10},
    },
    'TEAHOUSE': {
        'name': '茶馆', 'type': 'TEAHOUSE', 'work_time': 0,
        'power_type': '商',
        'desc': '品茗闲聊，打探消息的好地方。',
        'base_fee': 5,
    },
    'TAVERN': {
        'name': '酒楼', 'type': 'TAVERN', 'work_time': 0,
        'power_type': '商',
        'desc': '高档餐饮，美酒佳肴。',
        'base_fee': 10,
    },
    'STABLE': {
        'name': '马厩', 'type': 'STABLE', 'work_time': 0,
        'power_type': '商',
        'desc': '买卖马匹，寄存坐骑。',
        'base_fee': 5,
    },
    'INN': {
        'name': '酒肆', 'type': 'INN', 'work_time': 0,
        'power_type': '商',
        'desc': '路边客栈，卖肉包子。'
    },

    # ══════════════════════════════════════════════════════════════
    # 工匠势力建筑 (工)
    # ══════════════════════════════════════════════════════════════
    'WORKSHOP': {
        'name': '工坊', 'type': 'WORKSHOP', 'work_time': 0,
        'power_type': '工',
        'desc': '工匠作业，产出器物。'
    },
    'SMITHY': {
        'name': '铁铺', 'type': 'SMITHY', 'work_time': 0,
        'power_type': '工',
        'desc': '打铁锻造，制作兵器护甲。',
        'is_heat_source': True,
        'heat_range': 100,
        'fuel_max': 300,
        'base_fee': 5,
    },
    'WEAVING': {
        'name': '织坊', 'type': 'WEAVING', 'work_time': 0,
        'power_type': '工',
        'desc': '纺织丝绸布料，缝制衣物。',
        'base_fee': 3,
    },
    'KILN': {
        'name': '窑场', 'type': 'KILN', 'work_time': 0,
        'power_type': '工',
        'desc': '烧制砖瓦瓷器。',
        'is_heat_source': True,
        'heat_range': 80,
        'fuel_max': 400,
        'base_fee': 5,
    },
    'JEWELER': {
        'name': '珠宝', 'type': 'JEWELER', 'work_time': 0,
        'power_type': '工',
        'desc': '制作和售卖金银首饰。',
        'base_fee': 0,
    },

    # ══════════════════════════════════════════════════════════════
    # 学术/宗教势力建筑 (学)
    # ══════════════════════════════════════════════════════════════
    'SCHOOL': {
        'name': '书院', 'type': 'SCHOOL', 'work_time': 0,
        'power_type': '学',
        'desc': '文人墨客聚集地，产出字画。'
    },
    'CLINIC': {
        'name': '医馆', 'type': 'CLINIC', 'work_time': 0,
        'power_type': '学',
        'desc': '治疗伤病，悬壶济世。',
        'base_fee': 15,
    },
    'PHARMACY': {
        'name': '药铺', 'type': 'PHARMACY', 'work_time': 0,
        'power_type': '学',
        'desc': '买卖药材，制作丹药。',
        'initial_inventory': {'草药': 10, '伤药': 5},
        'base_fee': 0,
    },
    'LIBRARY': {
        'name': '书斋', 'type': 'LIBRARY', 'work_time': 0,
        'power_type': '学',
        'desc': '藏书万卷，可借阅抄录。',
        'base_fee': 5,
    },
    'TEMPLE': {
        'name': '禅院', 'type': 'TEMPLE', 'work_time': 0,
        'power_type': '学',
        'desc': '烧香拜佛，产出护身符。'
    },
    'TAOIST': {
        'name': '道观', 'type': 'TAOIST', 'work_time': 0,
        'power_type': '学',
        'desc': '炼丹修道，卜卦问卜。',
        'base_fee': 10,
    },

    # ══════════════════════════════════════════════════════════════
    # 江湖势力建筑 (游)
    # ══════════════════════════════════════════════════════════════
    'THEATER': {
        'name': '瓦舍', 'type': 'THEATER', 'work_time': 0,
        'power_type': '游',
        'desc': '勾栏瓦舍，才艺变现。',
        'base_fee': 5,
    },

    # ══════════════════════════════════════════════════════════════
    # 盗匪势力建筑 (匪)
    # ══════════════════════════════════════════════════════════════
    'GAMBLING': {
        'name': '赌坊', 'type': 'GAMBLING', 'work_time': 0,
        'power_type': '匪',
        'desc': '赌博娱乐，小赌怡情大赌伤身。',
        'base_fee': 0,  # 赌博本身收费
    },
    'BROTHEL': {
        'name': '青楼', 'type': 'BROTHEL', 'work_time': 0,
        'power_type': '匪',
        'desc': '风月场所，销金窟。',
        'base_fee': 30,
    },
    'BLACKMARKET': {
        'name': '黑市', 'type': 'BLACKMARKET', 'work_time': 0,
        'power_type': '匪',
        'desc': '见不得光的交易场所。',
        'base_fee': 0,
    },
    'BANDIT_LAIR': {
        'name': '山寨', 'type': 'BANDIT_LAIR', 'work_time': 0,
        'power_type': '匪',
        'desc': '落草为寇的据点。',
        'strategic_value': 3,
    },
}

# ══════════════════════════════════════════════════════════════
# 建筑图标映射（用于UI渲染）
# ══════════════════════════════════════════════════════════════
BUILDING_ICONS = {
    # 自然资源
    'BUSH': ("草", (50, 150, 50)),
    'TREE': ("木", (60, 120, 60)),
    'MINE': ("矿", (120, 100, 80)),
    'FISHPOND': ("鱼", (50, 100, 150)),
    'CAMPFIRE': ("火", (200, 100, 50)),
    
    # 朝廷/军事
    'GOV_OFFICE': ("衙", (80, 80, 120)),
    'GATEHOUSE': ("关", (100, 80, 60)),
    'JAIL': ("牢", (60, 60, 80)),
    'BARRACKS': ("兵", (100, 20, 20)),
    'ARMORY': ("甲", (80, 80, 100)),
    
    # 农业
    'FARM': ("田", (50, 100, 50)),
    'GRANARY': ("仓", (120, 100, 50)),
    'MILL': ("磨", (100, 90, 70)),
    'RANCH': ("牧", (120, 100, 80)),
    'HUNTING': ("猎", (80, 120, 60)),
    'HOUSE': ("宅", (100, 100, 150)),
    
    # 商业
    'MARKET': ("市", (150, 100, 50)),
    'PAWNSHOP': ("当", (130, 100, 70)),
    'GRAIN_SHOP': ("粮", (140, 120, 60)),
    'TEAHOUSE': ("茶", (100, 130, 100)),
    'TAVERN': ("酒", (150, 120, 80)),
    'STABLE': ("马", (120, 100, 80)),
    'INN': ("店", (120, 80, 50)),
    
    # 工匠
    'WORKSHOP': ("工", (100, 50, 50)),
    'SMITHY': ("铁", (150, 80, 50)),
    'WEAVING': ("织", (150, 100, 150)),
    'KILN': ("窑", (180, 100, 50)),
    'JEWELER': ("珠", (150, 150, 200)),
    
    # 学术/宗教
    'SCHOOL': ("书", (50, 50, 150)),
    'CLINIC': ("医", (200, 50, 50)),
    'PHARMACY': ("药", (80, 150, 80)),
    'LIBRARY': ("藏", (100, 80, 60)),
    'TEMPLE': ("寺", (180, 150, 50)),
    'TAOIST': ("道", (100, 100, 150)),
    
    # 江湖
    'THEATER': ("戏", (150, 50, 150)),
    
    # 盗匪
    'GAMBLING': ("赌", (200, 50, 50)),
    'BROTHEL': ("楼", (200, 100, 100)),
    'BLACKMARKET': ("黑", (50, 50, 50)),
    'BANDIT_LAIR': ("寨", (100, 80, 60)),
}

# ══════════════════════════════════════════════════════════════
# 势力类型 -> 推荐建筑映射
# ══════════════════════════════════════════════════════════════
POWER_TYPE_BUILDINGS = {
    '士': ['GOV_OFFICE', 'GATEHOUSE', 'JAIL'],
    '农': ['FARM', 'GRANARY', 'MILL', 'RANCH', 'HUNTING', 'HOUSE'],
    '工': ['WORKSHOP', 'SMITHY', 'WEAVING', 'KILN', 'JEWELER'],
    '商': ['MARKET', 'PAWNSHOP', 'GRAIN_SHOP', 'TEAHOUSE', 'TAVERN', 'STABLE', 'INN'],
    '学': ['SCHOOL', 'CLINIC', 'PHARMACY', 'LIBRARY', 'TEMPLE', 'TAOIST'],
    '兵': ['BARRACKS', 'ARMORY'],
    '游': ['THEATER'],
    '匪': ['GAMBLING', 'BROTHEL', 'BLACKMARKET', 'BANDIT_LAIR'],
}

def get_building_icon(building_type):
    """获取建筑图标和颜色"""
    return BUILDING_ICONS.get(building_type, ("宅", (100, 100, 100)))

def get_buildings_for_power_type(power_type):
    """获取特定势力类型的推荐建筑列表"""
    return POWER_TYPE_BUILDINGS.get(power_type, [])