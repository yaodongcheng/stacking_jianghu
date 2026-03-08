# tools/make_gamedata_csv.py
# 注意：本文件是生成 data/ 下各 csv 的单一真相来源。
# 修改此文件后执行 `python tools/make_gamedata_csv.py` 重新生成 csv。
import csv
import os

os.makedirs('../data', exist_ok=True)

# --- 1. 物品定义 ---
# 注意：货币统一使用 '铜钱'（与 definitions.py 中的 ITEM_COIN = "铜钱" 一致）
# def_bonus 列新增，用于护甲加成；atk_bonus 用于武器加成
items = [
    # ══════════════════════════════════════════════════════════════
    # 货币
    # ══════════════════════════════════════════════════════════════
    {'id': '铜钱',   'type': 'CURRENCY',  'value': 1,   'desc': '大宋通宝。'},
    {'id': '银两',   'type': 'CURRENCY',  'value': 100, 'desc': '十足官银，一两抵百钱。'},

    # ══════════════════════════════════════════════════════════════
    # 食物 - 基础生存资源
    # ══════════════════════════════════════════════════════════════
    {'id': '浆果',   'type': 'FOOD',      'value': 2,  'hunger_rec': 5,  'desc': '酸甜可口。'},
    {'id': '谷物',   'type': 'FOOD',      'value': 4,  'price': 5,  'hunger_rec': 30, 'desc': '颗粒饱满的粮食，可裹腹。'},
    {'id': '小麦',   'type': 'FOOD',      'value': 3,  'hunger_rec': 5,  'desc': '农作物，可磨面。'},
    {'id': '稻米',   'type': 'FOOD',      'value': 4,  'hunger_rec': 8,  'desc': '南方运来的精米。'},
    {'id': '烤果',   'type': 'FOOD',      'value': 5,  'hunger_rec': 15, 'desc': '熟食。'},
    {'id': '肉包子', 'type': 'FOOD',      'value': 8,  'hunger_rec': 30, 'desc': '馅料来源十分可疑。'},
    {'id': '生鱼',   'type': 'FOOD',      'value': 5,  'hunger_rec': 8,  'desc': '刚捕上来的活鱼，新鲜但腥气重。'},
    {'id': '烤鱼',   'type': 'FOOD',      'value': 12, 'hunger_rec': 25, 'desc': '香喷喷的烤鱼，美味又管饱。'},
    {'id': '生肉',   'type': 'FOOD',      'value': 6,  'hunger_rec': 5,  'desc': '新鲜的肉，需要烹饪。'},
    {'id': '烤肉',   'type': 'FOOD',      'value': 15, 'hunger_rec': 35, 'desc': '滋滋冒油的烤肉。'},
    {'id': '馒头',   'type': 'FOOD',      'value': 4,  'hunger_rec': 20, 'desc': '炊饼，劳动人民的主食。'},
    {'id': '米饭',   'type': 'FOOD',      'value': 6,  'hunger_rec': 25, 'desc': '热腾腾的白米饭。'},
    {'id': '面条',   'type': 'FOOD',      'value': 8,  'hunger_rec': 28, 'desc': '热气腾腾的汤面。'},
    
    # ══════════════════════════════════════════════════════════════
    # 饮品 - 特殊效果
    # ══════════════════════════════════════════════════════════════
    {'id': '清水',   'type': 'DRINK',     'value': 1,  'hunger_rec': 2,  'desc': '清凉解渴。'},
    {'id': '茶水',   'type': 'DRINK',     'value': 5,  'hunger_rec': 3,  'desc': '提神醒脑的茶汤。'},
    {'id': '浊酒',   'type': 'DRINK',     'value': 8,  'hunger_rec': 5,  'desc': '村醪浊酒，易醉。'},
    {'id': '好酒',   'type': 'DRINK',     'value': 25, 'hunger_rec': 8,  'desc': '清澈香醇的美酒。'},
    {'id': '药酒',   'type': 'DRINK',     'value': 40, 'hunger_rec': 10, 'desc': '滋补药酒，活血化瘀。'},

    # ══════════════════════════════════════════════════════════════
    # 建材 - 建造系统
    # ══════════════════════════════════════════════════════════════
    {'id': '木材',   'type': 'MATERIAL',  'value': 3,  'burn_time': 60,  'desc': '建材。'},
    {'id': '石料',   'type': 'MATERIAL',  'value': 3,  'desc': '建材。'},
    {'id': '泥土',   'type': 'MATERIAL',  'value': 1,  'desc': '土壤。'},
    {'id': '木板',   'type': 'MATERIAL',  'value': 5,  'burn_time': 80,  'desc': '加工木材。'},
    {'id': '木棍',   'type': 'MATERIAL',  'value': 2,  'burn_time': 30,  'desc': '树枝。'},
    {'id': '铁料',   'type': 'MATERIAL',  'value': 6,  'desc': '锻造武器和护甲的原料。'},
    {'id': '砖瓦',   'type': 'MATERIAL',  'value': 4,  'desc': '烧制的砖块和瓦片。'},
    {'id': '绳索',   'type': 'MATERIAL',  'value': 3,  'desc': '麻绳，捆绑用。'},
    {'id': '公文',   'type': 'MATERIAL',  'value': 0,  'desc': '官府的文书。'},

    # ══════════════════════════════════════════════════════════════
    # 可部署道具
    # ══════════════════════════════════════════════════════════════
    {'id': '火把',   'type': 'DEPLOYABLE','value': 10, 'warm_val': 50,   'desc': '照明。'},
    {'id': '陷阱',   'type': 'DEPLOYABLE','value': 15, 'desc': '捕猎用的铁夹子。'},

    # ══════════════════════════════════════════════════════════════
    # 商品（买卖流通）- 各建筑产出
    # ══════════════════════════════════════════════════════════════
    # 文化类
    {'id': '字画',     'type': 'COMMODITY', 'value': 15, 'desc': '名家真迹，或是赝品。'},
    {'id': '书籍',     'type': 'COMMODITY', 'value': 12, 'desc': '经史子集，科举必备。'},
    {'id': '琴谱',     'type': 'COMMODITY', 'value': 20, 'desc': '古琴曲谱，文人雅趣。'},
    
    # 宗教类
    {'id': '护身符',   'type': 'COMMODITY', 'value': 10, 'desc': '大相国寺开光，保平安。'},
    {'id': '香烛',     'type': 'COMMODITY', 'value': 5,  'desc': '祭祀祈福用。'},
    {'id': '经文',     'type': 'COMMODITY', 'value': 8,  'desc': '佛经道藏。'},
    
    # 工艺类
    {'id': '精制器物', 'type': 'COMMODITY', 'value': 20, 'desc': '百工坊出品的精良器具。'},
    {'id': '丝绸',     'type': 'COMMODITY', 'value': 30, 'desc': '苏杭上等丝绸。'},
    {'id': '瓷器',     'type': 'COMMODITY', 'value': 25, 'desc': '汝窑青瓷，价值不菲。'},
    {'id': '玉器',     'type': 'COMMODITY', 'value': 50, 'desc': '和田美玉雕琢而成。'},
    {'id': '首饰',     'type': 'COMMODITY', 'value': 35, 'desc': '金银珠宝制成的饰品。'},
    
    # 药材类
    {'id': '草药',     'type': 'COMMODITY', 'value': 8,  'desc': '山野采集的药草。'},
    {'id': '丹药',     'type': 'COMMODITY', 'value': 30, 'desc': '炼丹炉中炼制的丹丸。'},
    {'id': '伤药',     'type': 'COMMODITY', 'value': 15, 'desc': '金疮药，外敷止血。'},
    
    # 特殊类
    {'id': '骰子',     'type': 'COMMODITY', 'value': 5,  'desc': '赌坊常见，六面骨牌。'},
    {'id': '当票',     'type': 'COMMODITY', 'value': 0,  'desc': '当铺凭证，可赎回典当物。'},
    {'id': '路引',     'type': 'COMMODITY', 'value': 10, 'desc': '官府核发的通行凭证。'},
    {'id': '密信',     'type': 'COMMODITY', 'value': 0,  'desc': '不知内容的密封书信。'},
    {'id': '情报',     'type': 'COMMODITY', 'value': 20, 'desc': '有价值的消息。'},
    
    # 畜产类  
    {'id': '马匹',     'type': 'COMMODITY', 'value': 200,'desc': '代步骑乘的良驹。'},
    {'id': '皮革',     'type': 'COMMODITY', 'value': 10, 'desc': '鞣制好的皮料。'},
    {'id': '羊毛',     'type': 'COMMODITY', 'value': 6,  'desc': '柔软保暖。'},

    # ══════════════════════════════════════════════════════════════
    # 武器（atk_bonus 提升战斗攻击力）
    # ══════════════════════════════════════════════════════════════
    {'id': '木棒',   'type': 'WEAPON',    'value': 5,  'atk_bonus': 2,  'desc': '粗壮木棍，攻击+2。'},
    {'id': '菜刀',   'type': 'WEAPON',    'value': 15, 'atk_bonus': 3,  'desc': '厨房用刀，攻击+3。'},
    {'id': '朴刀',   'type': 'WEAPON',    'value': 40, 'atk_bonus': 5,  'desc': '民间常见刀具，攻击+5。'},
    {'id': '铁剑',   'type': 'WEAPON',    'value': 60, 'atk_bonus': 8,  'desc': '锋利的铁制长剑，攻击+8。'},
    {'id': '长枪',   'type': 'WEAPON',    'value': 55, 'atk_bonus': 7,  'desc': '一寸长一寸强，攻击+7。'},
    {'id': '大刀',   'type': 'WEAPON',    'value': 70, 'atk_bonus': 10, 'desc': '青龙偃月刀式，攻击+10。'},
    {'id': '弓箭',   'type': 'WEAPON',    'value': 50, 'atk_bonus': 6,  'desc': '远程武器，攻击+6。'},
    {'id': '飞镖',   'type': 'WEAPON',    'value': 25, 'atk_bonus': 4,  'desc': '暗器，攻击+4。'},

    # ══════════════════════════════════════════════════════════════
    # 护甲（def_bonus 提升战斗防御力）
    # ══════════════════════════════════════════════════════════════
    {'id': '皮甲',   'type': 'ARMOR',     'value': 50, 'def_bonus': 6,  'desc': '轻便皮甲，防御+6。'},
    {'id': '锁子甲', 'type': 'ARMOR',     'value': 120,'def_bonus': 12, 'desc': '精制锁甲，防御+12。'},
    {'id': '鳞甲',   'type': 'ARMOR',     'value': 150,'def_bonus': 15, 'desc': '鱼鳞铁甲，防御+15。'},
    {'id': '护臂',   'type': 'ARMOR',     'value': 20, 'def_bonus': 3,  'desc': '皮质护臂，防御+3。'},
    {'id': '铁盔',   'type': 'ARMOR',     'value': 35, 'def_bonus': 4,  'desc': '保护头部，防御+4。'},

    # ══════════════════════════════════════════════════════════════
    # 服装（warm_val 抵御寒冷，def_bonus 提供少量防御）
    # ══════════════════════════════════════════════════════════════
    {'id': '粗布衣', 'type': 'CLOTHING',  'value': 5,  'warm_val': 10, 'def_bonus': 1, 'desc': '粗麻布衣，稍微抵御风寒，防御+1。'},
    {'id': '棉袄',   'type': 'CLOTHING',  'value': 20, 'warm_val': 25, 'def_bonus': 2, 'desc': '厚实棉衣，御寒效果极佳，防御+2。'},
    {'id': '丝衣',   'type': 'CLOTHING',  'value': 40, 'warm_val': 15, 'def_bonus': 1, 'desc': '丝绸长衫，轻盈华贵。'},
    {'id': '官服',   'type': 'CLOTHING',  'value': 80, 'warm_val': 20, 'def_bonus': 2, 'desc': '官吏朝服，身份象征。'},
    {'id': '僧袍',   'type': 'CLOTHING',  'value': 15, 'warm_val': 15, 'def_bonus': 1, 'desc': '出家人穿着。'},
    {'id': '斗篷',   'type': 'CLOTHING',  'value': 25, 'warm_val': 30, 'def_bonus': 1, 'desc': '遮风挡雨的披风。'},
    
    # ══════════════════════════════════════════════════════════════
    # 钥匙与凭证（解锁特殊区域/功能）
    # ══════════════════════════════════════════════════════════════
    {'id': '牢房钥匙', 'type': 'KEY',     'value': 0,  'desc': '打开牢房的铁钥匙。'},
    {'id': '库房钥匙', 'type': 'KEY',     'value': 0,  'desc': '打开仓库的钥匙。'},
    {'id': '城门令牌', 'type': 'KEY',     'value': 50, 'desc': '可自由进出城门。'},
]
# 新增 def_bonus 列（护甲加成）
item_headers = ['id', 'type', 'value', 'price', 'hunger_rec', 'burn_time', 'warm_val', 'atk_bonus', 'def_bonus', 'desc']

# --- 2. 配方定义 ---
# 关键字段说明：
# input: 主动堆叠者 (NPC职业 或 资源名)
# target_id: 被堆叠者 (建筑类型 或 NPC ID)
# ext_input: 额外消耗 (背包里的物品) e.g., "小麦:1"
# output: 产出 e.g., "ITEM:木板:1" 或 "铜钱:5"
recipes = [
    # ==========================
    # 基础采集 (无消耗)
    # ==========================
    {'id': 'GATHER_BERRY', 'input': 'ANY', 'target_type': 'BUILDING', 'target_id': 'BUSH', 'output': 'ITEM:浆果:1', 'time': 100, 'desc': '采集浆果'},
    {'id': 'CHOP_TREE', 'input': 'ANY', 'target_type': 'BUILDING', 'target_id': 'TREE', 'output': 'ITEM:木材:1', 'time': 150, 'desc': '伐木'},
    {'id': 'MINE_STONE', 'input': 'ANY', 'target_type': 'BUILDING', 'target_id': 'MINE', 'output': 'ITEM:石料:1', 'time': 180, 'desc': '采石'},
    {'id': 'MINE_IRON', 'input': 'ANY', 'target_type': 'BUILDING', 'target_id': 'MINE', 'output': 'ITEM:铁料:1', 'time': 250, 'desc': '挖矿'},
    {'id': 'CATCH_FISH', 'input': 'ANY', 'target_type': 'BUILDING', 'target_id': 'FISHPOND', 'output': 'ITEM:生鱼:1', 'time': 120, 'desc': '捕鱼'},
    
    # ==========================
    # 基础建设 (木材 -> 设施)
    # ==========================
    # 木材 + 人 -> 篝火 (生存第一步)
    {'id': 'BUILD_CAMPFIRE', 'input': 'ANY', 'req_count': 1, 'target_type': 'RESOURCE', 'target_id': '木材', 'output': 'BUILDING:CAMPFIRE', 'time': 150, 'desc': '搭建篝火'},
    # 民居: 2木材 + 人
    {'id': 'BUILD_HOUSE', 'input': 'ANY', 'req_count': 2, 'target_type': 'RESOURCE', 'target_id': '木材', 'output': 'BUILDING:HOUSE', 'time': 300, 'desc': '建造民居'},
    
    # 集市: 3木材 + 人
    {'id': 'BUILD_MARKET', 'input': 'ANY', 'req_count': 3, 'target_type': 'RESOURCE', 'target_id': '木材', 'output': 'BUILDING:MARKET', 'time': 400, 'desc': '搭建集市'},
    
    # 农田: 4木材 + 人
    {'id': 'BUILD_FARM', 'input': 'ANY', 'req_count': 4, 'target_type': 'RESOURCE', 'target_id': '木材', 'output': 'BUILDING:FARM', 'time': 400, 'desc': '开垦农田'},
    
    # 粮仓: 5木材 + 人
    {'id': 'BUILD_GRANARY', 'input': 'ANY', 'req_count': 5, 'target_type': 'RESOURCE', 'target_id': '木材', 'output': 'BUILDING:GRANARY', 'time': 400, 'desc': '建造粮仓'},
    
    
    # 木材x3 + 人 -> 民居 (恢复体力)
    {'id': 'BUILD_HOUSE', 'input': '木材', 'req_count': 3, 'target_type': 'HUMAN', 'target_id': 'ANY', 'output': 'BUILDING:HOUSE', 'time': 300, 'desc': '建造民居'},
    
    # 木材x5 + 人 -> 集市 (开启经济)
    {'id': 'BUILD_MARKET', 'input': '木材', 'req_count': 5, 'target_type': 'HUMAN', 'target_id': 'ANY', 'output': 'BUILDING:MARKET', 'time': 400, 'desc': '搭建集市'},
    
    # 木材x2 + 泥土x1 + 人 -> 农田 (开启农业) - 简化为木材
    {'id': 'BUILD_FARM', 'input': '木材', 'req_count': 5, 'target_type': 'HUMAN', 'target_id': 'ANY', 'output': 'BUILDING:FARM', 'time': 400, 'desc': '开垦农田'},
    
    # 木材x5 + 人 -> 粮仓 (开启流民招募)
    {'id': 'BUILD_GRANARY', 'input': '木材', 'req_count': 5, 'target_type': 'HUMAN', 'target_id': 'ANY', 'output': 'BUILDING:GRANARY', 'time': 400, 'desc': '建造粮仓'},

    # ==========================
    # 生活与生产
    # ==========================
    # 烹饪: 浆果 + 篝火 -> 烤果
    {'id': 'COOK_BERRY', 'input': '浆果', 'target_type': 'BUILDING', 'target_id': 'CAMPFIRE', 'output': 'ITEM:烤果:1', 'time': 120, 'desc': '烹饪'},
    # 烹饪: 生鱼 + 篝火 -> 烤鱼
    {'id': 'COOK_FISH', 'input': '生鱼', 'target_type': 'BUILDING', 'target_id': 'CAMPFIRE', 'output': 'ITEM:烤鱼:1', 'time': 150, 'desc': '烤鱼'},
    # 添柴: 木材 + 篝火
    {'id': 'ADD_FUEL', 'input': '木材', 'target_type': 'BUILDING', 'target_id': 'CAMPFIRE', 'output': '_FUEL', 'time': 60, 'desc': '添柴'},
    # 休息: 人 + 民居
    {'id': 'REST_HOUSE', 'input': 'ANY', 'target_type': 'BUILDING', 'target_id': 'HOUSE', 'output': 'STAT:REST', 'time': 200, 'desc': '休息'},
    # 种植: 泥土 + 浆果 -> 浆果丛 (循环资源)
    {'id': 'PLANT_BUSH', 'input': '泥土', 'ext_input': '浆果:1', 'target_type': 'HUMAN', 'target_id': 'ANY', 'output': 'BUILDING:BUSH', 'time': 200, 'desc': '种植'},

    # ==========================
    # 经济循环
    # ==========================
    # 【早期赚钱配方】玩家把资源拖到集市出售
    {'id': 'SELL_WOOD', 'input': '木材', 'req_count': 1, 'target_type': 'BUILDING', 'target_id': 'MARKET', 'output': 'ITEM:铜钱:3', 'time': 50, 'desc': '出售木材'},
    {'id': 'SELL_BERRY', 'input': '浆果', 'req_count': 1, 'target_type': 'BUILDING', 'target_id': 'MARKET', 'output': 'ITEM:铜钱:2', 'time': 30, 'desc': '出售浆果'},
    {'id': 'SELL_STONE', 'input': '石料', 'req_count': 1, 'target_type': 'BUILDING', 'target_id': 'MARKET', 'output': 'ITEM:铜钱:3', 'time': 50, 'desc': '出售石料'},
    {'id': 'SELL_IRON', 'input': '铁料', 'req_count': 1, 'target_type': 'BUILDING', 'target_id': 'MARKET', 'output': 'ITEM:铜钱:6', 'time': 50, 'desc': '出售铁料'},
    {'id': 'SELL_FISH', 'input': '生鱼', 'req_count': 1, 'target_type': 'BUILDING', 'target_id': 'MARKET', 'output': 'ITEM:铜钱:5', 'time': 40, 'desc': '出售生鱼'},
    
    # 农夫工作
    {'id': 'WORK_FARM_WHEAT', 'input': 'FARMER', 'target_type': 'BUILDING', 'target_id': 'FARM', 'output': 'ITEM:小麦:1', 'time': 200, 'desc': '耕种'},
    {'id': 'WORK_FARM_PLAYER', 'input': 'PLAYER', 'target_type': 'BUILDING', 'target_id': 'FARM', 'output': 'ITEM:小麦:1', 'time': 200, 'desc': '耕种'},
    
    # 商人工作
    {'id': 'WORK_MARKET', 'input': 'MERCHANT', 'target_type': 'BUILDING', 'target_id': 'MARKET', 'ext_input': '小麦:1', 'output': 'ITEM:铜钱:5', 'time': 100, 'desc': '出售粮食'},
    {'id': 'FARMER_SELL', 'input': 'FARMER', 'target_type': 'BUILDING', 'target_id': 'MARKET', 'ext_input': '小麦:1', 'output': 'ITEM:铜钱:5', 'time': 120, 'desc': '农夫卖粮'},
    
    # 书院
    {'id': 'WORK_SCHOOL', 'input': 'SCHOLAR', 'target_type': 'BUILDING', 'target_id': 'SCHOOL', 'output': 'ITEM:铜钱:2', 'time': 180, 'desc': '讲学'},

    # ==========================
    # 招募与转职
    # ==========================
    {'id': 'RECRUIT_GUARD', 'input': 'NONE', 'cost_money': 100, 'target_type': 'HUMAN', 'target_id': 'ANY', 'output': 'FOLLOWER:TRUE', 'time': 100, 'desc': '招募护院'},
    {'id': 'TRAIN_FARMER', 'input': 'NONE', 'target_type': 'BUILDING', 'target_id': 'GRANARY', 'output': 'JOB:FARMER', 'time': 150, 'desc': '安置农夫'},


    
    # ==========================
    # 汴京社会循环 (职业产出)
    # ==========================
    
    # 1. 农业 (农夫 + 农田 -> 小麦)
    {'id': 'FARM_WORK', 'input': 'FARMER', 'target_type': 'BUILDING', 'target_id': 'FARM', 'output': 'ITEM:小麦:1', 'time': 200, 'desc': '耕种'},
    
    # 2. 餐饮业 (商贾/厨子 + 酒肆 + 小麦 -> 肉包子)
    # 十字坡孙二娘的黑店逻辑
    {'id': 'COOK_BUN', 'input': 'MERCHANT', 'target_type': 'BUILDING', 'target_id': 'INN', 'ext_input': '小麦:1', 'output': 'ITEM:肉包子:1', 'time': 150, 'desc': '做包子'},
    {'id': 'COOK_BUN_2', 'input': 'FARMER', 'target_type': 'BUILDING', 'target_id': 'INN', 'ext_input': '小麦:1', 'output': 'ITEM:肉包子:1', 'time': 150, 'desc': '做包子'},

    # 3. 文化业 (文人 + 书院 -> 字画)
    {'id': 'WRITE_SCROLL', 'input': 'SCHOLAR', 'target_type': 'BUILDING', 'target_id': 'SCHOOL', 'output': 'ITEM:字画:1', 'time': 300, 'desc': '著书立说'},
    
    # 4. 宗教业 (和尚 + 寺庙 -> 护身符)
    {'id': 'PRAY', 'input': 'MONK', 'target_type': 'BUILDING', 'target_id': 'TEMPLE', 'output': 'ITEM:护身符:1', 'time': 250, 'desc': '诵经祈福'},
    
    # 5. 娱乐业 (工匠/舞姬 + 瓦舍 -> 直接赚钱，魅力加成在 recipe_system 处理)
    # 魅力(charm)高的人演出收入更多，在 result_callback 中按 charm 加成
    {'id': 'PERFORM', 'input': 'ARTISAN', 'target_type': 'BUILDING', 'target_id': 'THEATER', 'output': 'ITEM:铜钱:8', 'time': 180, 'desc': '献艺'},
    {'id': 'PERFORM_DANCER', 'input': 'DANCER', 'target_type': 'BUILDING', 'target_id': 'THEATER', 'output': 'ITEM:铜钱:10', 'time': 180, 'desc': '献舞'},

    # 6. 制造业 (工匠 + 工坊 -> 精制器物/武器/护甲，消耗铁料)
    {'id': 'CRAFT_TOOL',    'input': 'ARTISAN', 'target_type': 'BUILDING', 'target_id': 'WORKSHOP', 'ext_input': '木材:1',  'output': 'ITEM:精制器物:1', 'time': 200, 'desc': '打造器物'},
    {'id': 'CRAFT_SWORD',   'input': 'ARTISAN', 'target_type': 'BUILDING', 'target_id': 'WORKSHOP', 'ext_input': '铁料:2',  'output': 'ITEM:铁剑:1',   'time': 300, 'desc': '锻造铁剑'},
    {'id': 'CRAFT_KNIFE',   'input': 'ARTISAN', 'target_type': 'BUILDING', 'target_id': 'WORKSHOP', 'ext_input': '铁料:1',  'output': 'ITEM:朴刀:1',   'time': 220, 'desc': '打制朴刀'},
    {'id': 'CRAFT_LEATHER', 'input': 'ARTISAN', 'target_type': 'BUILDING', 'target_id': 'WORKSHOP', 'ext_input': '木材:2',  'output': 'ITEM:皮甲:1',   'time': 280, 'desc': '制作皮甲'},
    {'id': 'CRAFT_MAIL',    'input': 'ARTISAN', 'target_type': 'BUILDING', 'target_id': 'WORKSHOP', 'ext_input': '铁料:4',  'output': 'ITEM:锁子甲:1', 'time': 500, 'desc': '锻造锁甲'},
    {'id': 'CRAFT_COAT',    'input': 'ARTISAN', 'target_type': 'BUILDING', 'target_id': 'WORKSHOP', 'ext_input': '木棍:1',  'output': 'ITEM:粗布衣:1', 'time': 120, 'desc': '缝制布衣'},
    {'id': 'CRAFT_PADDED',  'input': 'ARTISAN', 'target_type': 'BUILDING', 'target_id': 'WORKSHOP', 'ext_input': '木棍:2',  'output': 'ITEM:棉袄:1',   'time': 180, 'desc': '缝制棉袄'},
    # 工匠/商人将武器装备带去集市出售
    {'id': 'SELL_TOOL_ARTISAN', 'input': 'ARTISAN',  'target_type': 'BUILDING', 'target_id': 'MARKET', 'ext_input': '精制器物:1', 'output': 'ITEM:铜钱:20', 'time': 100, 'desc': '售卖器物'},
    {'id': 'SELL_SWORD',        'input': 'ARTISAN',  'target_type': 'BUILDING', 'target_id': 'MARKET', 'ext_input': '铁剑:1',     'output': 'ITEM:铜钱:60', 'time': 100, 'desc': '售卖铁剑'},
    {'id': 'SELL_KNIFE',        'input': 'ARTISAN',  'target_type': 'BUILDING', 'target_id': 'MARKET', 'ext_input': '朴刀:1',     'output': 'ITEM:铜钱:40', 'time': 100, 'desc': '售卖朴刀'},
    {'id': 'SELL_ARMOR',        'input': 'MERCHANT', 'target_type': 'BUILDING', 'target_id': 'MARKET', 'ext_input': '皮甲:1',     'output': 'ITEM:铜钱:50', 'time': 100, 'desc': '售卖皮甲'},

    # 7. 官府
    # 7a. 官员审案 -> 产出铜钱（代表官府税收/罚款收入，这是货币的唯一来源）
    {'id': 'GOV_WORK',      'input': 'OFFICIAL', 'target_type': 'BUILDING', 'target_id': 'GOV_OFFICE', 'output': 'ITEM:铜钱:15', 'time': 400, 'desc': '审案断狱'},
    # 7b. 官差去府衙领俸禄（官府铜钱 -> 官差手中，再消费流入市场）
    {'id': 'GUARD_SALARY',  'input': 'GUARD',    'target_type': 'BUILDING', 'target_id': 'GOV_OFFICE', 'output': 'ITEM:铜钱:10', 'time': 300, 'desc': '领取俸禄'},
    
    {'id': 'HEAL_IN_HOSPITAL', 'input': 'ANY', 'target_type': 'BUILDING', 'target_id': 'CLINIC', 'output': 'ACTION:HEAL', 'time': 300, 'desc': '救治中'},
    {'id': 'HEAL_WILD', 'input': 'MONK', 'target_type': 'NPC', 'target_id': 'ANY', 'output': 'ACTION:HEAL_SLOW', 'time': 150, 'desc': '念经疗伤'},
    {'id': 'HEAL_WILD_DOC', 'input': 'ANY', 'target_type': 'NPC', 'target_id': 'ANY', 'output': 'ACTION:HEAL_SLOW', 'time': 200, 'desc': '野外急救'},
    # ==========================
    # 贸易循环 (所有产出物 -> 集市 -> 钱)
    # ==========================
    # 农夫卖粮
    {'id': 'SELL_WHEAT', 'input': 'FARMER', 'target_type': 'BUILDING', 'target_id': 'MARKET', 'ext_input': '小麦:1', 'output': 'ITEM:铜钱:3', 'time': 80, 'desc': '卖粮'},
    # 商人高价卖货（魅力加成在 result_callback 中体现）
    {'id': 'SELL_SCROLL', 'input': 'MERCHANT', 'target_type': 'BUILDING', 'target_id': 'MARKET', 'ext_input': '字画:1', 'output': 'ITEM:铜钱:20', 'time': 100, 'desc': '倒卖字画'},
    {'id': 'SELL_AMULET', 'input': 'MERCHANT', 'target_type': 'BUILDING', 'target_id': 'MARKET', 'ext_input': '护身符:1', 'output': 'ITEM:铜钱:15', 'time': 100, 'desc': '售卖符水'},
    {'id': 'SELL_FURNITURE', 'input': 'MERCHANT', 'target_type': 'BUILDING', 'target_id': 'MARKET', 'ext_input': '精制器物:1', 'output': 'ITEM:铜钱:25', 'time': 100, 'desc': '出售器物'},
    {'id': 'SELL_BUN', 'input': 'MERCHANT', 'target_type': 'BUILDING', 'target_id': 'MARKET', 'ext_input': '肉包子:1', 'output': 'ITEM:铜钱:10', 'time': 80, 'desc': '卖包子'},

    # ══════════════════════════════════════════════════════════════
    # 【新增】各势力特色建筑配方
    # ══════════════════════════════════════════════════════════════
    
    # ──────────────────────────────────────────────────────────────
    # 朝廷/军事势力建筑 (士/兵)
    # ──────────────────────────────────────────────────────────────
    
    # 【岗哨】城门守卫 - 检查过往行人
    {'id': 'GUARD_GATE',    'input': 'GUARD',   'target_type': 'BUILDING', 'target_id': 'GATEHOUSE', 'output': 'ITEM:铜钱:5', 'time': 300, 'desc': '把守城门'},
    {'id': 'CHECK_PASS',    'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'GATEHOUSE', 'cost_money': 10, 'output': 'ITEM:路引:1', 'time': 60, 'desc': '办理路引'},
    
    # 【牢房】关押犯人
    {'id': 'JAIL_GUARD',    'input': 'GUARD',   'target_type': 'BUILDING', 'target_id': 'JAIL', 'output': 'ITEM:铜钱:8', 'time': 400, 'desc': '看守囚犯'},
    {'id': 'JAIL_VISIT',    'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'JAIL', 'cost_money': 20, 'output': 'ACTION:VISIT_PRISONER', 'time': 100, 'desc': '探监'},
    
    # 【校场】训练士兵
    {'id': 'TRAIN_SOLDIER', 'input': 'GUARD',   'target_type': 'BUILDING', 'target_id': 'BARRACKS', 'output': 'STAT:COMBAT_EXP', 'time': 300, 'desc': '操练武艺'},
    {'id': 'TRAIN_PLAYER',  'input': 'PLAYER',  'target_type': 'BUILDING', 'target_id': 'BARRACKS', 'output': 'STAT:COMBAT_EXP', 'time': 300, 'desc': '习武练功'},
    
    # 【武库】存储军械
    {'id': 'STORE_WEAPON',  'input': 'GUARD',   'target_type': 'BUILDING', 'target_id': 'ARMORY', 'ext_input': '铁剑:1', 'output': 'STAT:ARMORY_STORED', 'time': 80, 'desc': '入库军械'},
    {'id': 'DRAW_WEAPON',   'input': 'GUARD',   'target_type': 'BUILDING', 'target_id': 'ARMORY', 'output': 'ITEM:朴刀:1', 'time': 100, 'desc': '领取兵器'},
    
    # ──────────────────────────────────────────────────────────────
    # 商业势力建筑 (商)
    # ──────────────────────────────────────────────────────────────
    
    # 【当铺/质库】典当物品换钱
    {'id': 'PAWN_SILK',     'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'PAWNSHOP', 'ext_input': '丝绸:1', 'output': 'ITEM:铜钱:20', 'time': 60, 'desc': '典当丝绸'},
    {'id': 'PAWN_JADE',     'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'PAWNSHOP', 'ext_input': '玉器:1', 'output': 'ITEM:铜钱:35', 'time': 60, 'desc': '典当玉器'},
    {'id': 'PAWN_JEWELRY',  'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'PAWNSHOP', 'ext_input': '首饰:1', 'output': 'ITEM:铜钱:25', 'time': 60, 'desc': '典当首饰'},
    {'id': 'PAWN_WEAPON',   'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'PAWNSHOP', 'ext_input': '铁剑:1', 'output': 'ITEM:铜钱:40', 'time': 60, 'desc': '典当兵器'},
    {'id': 'WORK_PAWNSHOP', 'input': 'MERCHANT','target_type': 'BUILDING', 'target_id': 'PAWNSHOP', 'output': 'ITEM:铜钱:12', 'time': 250, 'desc': '经营当铺'},
    
    # 【粮铺】买卖粮食
    {'id': 'BUY_GRAIN',     'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'GRAIN_SHOP', 'cost_money': 8, 'output': 'ITEM:谷物:1', 'time': 40, 'desc': '买粮'},
    {'id': 'SELL_GRAIN',    'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'GRAIN_SHOP', 'ext_input': '小麦:2', 'output': 'ITEM:铜钱:5', 'time': 40, 'desc': '卖粮'},
    {'id': 'WORK_GRAINSHOP','input': 'MERCHANT','target_type': 'BUILDING', 'target_id': 'GRAIN_SHOP', 'output': 'ITEM:铜钱:10', 'time': 200, 'desc': '经营粮铺'},
    
    # 【茶馆】收集情报、社交
    {'id': 'DRINK_TEA',     'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'TEAHOUSE', 'cost_money': 5, 'output': 'ITEM:茶水:1', 'time': 80, 'desc': '品茗'},
    {'id': 'GATHER_INFO',   'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'TEAHOUSE', 'cost_money': 15, 'output': 'ITEM:情报:1', 'time': 200, 'desc': '打探消息'},
    {'id': 'WORK_TEAHOUSE', 'input': 'MERCHANT','target_type': 'BUILDING', 'target_id': 'TEAHOUSE', 'output': 'ITEM:铜钱:8', 'time': 180, 'desc': '经营茶馆'},
    
    # 【酒楼】高端餐饮
    {'id': 'DRINK_WINE',    'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'TAVERN', 'cost_money': 15, 'output': 'ITEM:好酒:1', 'time': 100, 'desc': '饮酒'},
    {'id': 'EAT_MEAL',      'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'TAVERN', 'cost_money': 10, 'output': 'STAT:HUNGER_FULL', 'time': 120, 'desc': '用膳'},
    {'id': 'BREW_WINE',     'input': 'MERCHANT','target_type': 'BUILDING', 'target_id': 'TAVERN', 'ext_input': '小麦:3', 'output': 'ITEM:好酒:1', 'time': 300, 'desc': '酿酒'},
    
    # 【马厩】马匹买卖、骑乘
    {'id': 'BUY_HORSE',     'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'STABLE', 'cost_money': 200, 'output': 'ITEM:马匹:1', 'time': 100, 'desc': '买马'},
    {'id': 'SELL_HORSE',    'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'STABLE', 'ext_input': '马匹:1', 'output': 'ITEM:铜钱:150', 'time': 80, 'desc': '卖马'},
    {'id': 'TEND_HORSE',    'input': 'FARMER',  'target_type': 'BUILDING', 'target_id': 'STABLE', 'output': 'ITEM:铜钱:6', 'time': 200, 'desc': '喂马'},
    
    # ──────────────────────────────────────────────────────────────
    # 工匠势力建筑 (工)
    # ──────────────────────────────────────────────────────────────
    
    # 【铁匠铺】锻造武器护甲
    {'id': 'FORGE_SPEAR',   'input': 'ARTISAN', 'target_type': 'BUILDING', 'target_id': 'SMITHY', 'ext_input': '铁料:2', 'output': 'ITEM:长枪:1', 'time': 280, 'desc': '锻造长枪'},
    {'id': 'FORGE_BLADE',   'input': 'ARTISAN', 'target_type': 'BUILDING', 'target_id': 'SMITHY', 'ext_input': '铁料:3', 'output': 'ITEM:大刀:1', 'time': 350, 'desc': '锻造大刀'},
    {'id': 'FORGE_SCALE',   'input': 'ARTISAN', 'target_type': 'BUILDING', 'target_id': 'SMITHY', 'ext_input': '铁料:5', 'output': 'ITEM:鳞甲:1', 'time': 500, 'desc': '锻造鳞甲'},
    {'id': 'FORGE_HELM',    'input': 'ARTISAN', 'target_type': 'BUILDING', 'target_id': 'SMITHY', 'ext_input': '铁料:1', 'output': 'ITEM:铁盔:1', 'time': 150, 'desc': '锻造铁盔'},
    {'id': 'REPAIR_WEAPON', 'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'SMITHY', 'cost_money': 20, 'output': 'ACTION:REPAIR', 'time': 150, 'desc': '修理兵器'},
    
    # 【织坊】纺织丝绸布料
    {'id': 'WEAVE_SILK',    'input': 'ARTISAN', 'target_type': 'BUILDING', 'target_id': 'WEAVING', 'output': 'ITEM:丝绸:1', 'time': 350, 'desc': '织造丝绸'},
    {'id': 'MAKE_SILKROBE', 'input': 'ARTISAN', 'target_type': 'BUILDING', 'target_id': 'WEAVING', 'ext_input': '丝绸:1', 'output': 'ITEM:丝衣:1', 'time': 200, 'desc': '缝制丝衣'},
    {'id': 'MAKE_CLOAK',    'input': 'ARTISAN', 'target_type': 'BUILDING', 'target_id': 'WEAVING', 'ext_input': '羊毛:2', 'output': 'ITEM:斗篷:1', 'time': 180, 'desc': '织造斗篷'},
    
    # 【窑场】烧制砖瓦瓷器
    {'id': 'MAKE_BRICK',    'input': 'ARTISAN', 'target_type': 'BUILDING', 'target_id': 'KILN', 'ext_input': '泥土:2', 'output': 'ITEM:砖瓦:1', 'time': 200, 'desc': '烧砖'},
    {'id': 'MAKE_CERAMIC',  'input': 'ARTISAN', 'target_type': 'BUILDING', 'target_id': 'KILN', 'ext_input': '泥土:3', 'output': 'ITEM:瓷器:1', 'time': 400, 'desc': '烧瓷'},
    
    # 【首饰铺】制作首饰
    {'id': 'MAKE_JEWELRY',  'input': 'ARTISAN', 'target_type': 'BUILDING', 'target_id': 'JEWELER', 'ext_input': '玉器:1', 'output': 'ITEM:首饰:1', 'time': 300, 'desc': '制作首饰'},
    {'id': 'SELL_JEWELRY',  'input': 'MERCHANT','target_type': 'BUILDING', 'target_id': 'JEWELER', 'ext_input': '首饰:1', 'output': 'ITEM:铜钱:40', 'time': 80, 'desc': '售卖首饰'},
    
    # ──────────────────────────────────────────────────────────────
    # 学术/宗教势力建筑 (学)
    # ──────────────────────────────────────────────────────────────
    
    # 【药铺】医疗与制药
    {'id': 'BUY_MEDICINE',  'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'PHARMACY', 'cost_money': 20, 'output': 'ITEM:伤药:1', 'time': 60, 'desc': '买药'},
    {'id': 'MAKE_MEDICINE', 'input': 'SCHOLAR', 'target_type': 'BUILDING', 'target_id': 'PHARMACY', 'ext_input': '草药:2', 'output': 'ITEM:伤药:1', 'time': 200, 'desc': '制药'},
    {'id': 'MAKE_MEDWINE',  'input': 'SCHOLAR', 'target_type': 'BUILDING', 'target_id': 'PHARMACY', 'ext_input': '草药:3', 'output': 'ITEM:药酒:1', 'time': 350, 'desc': '泡制药酒'},
    {'id': 'WORK_PHARMACY', 'input': 'SCHOLAR', 'target_type': 'BUILDING', 'target_id': 'PHARMACY', 'output': 'ITEM:铜钱:10', 'time': 250, 'desc': '坐堂问诊'},
    
    # 【书斋】藏书、抄书
    {'id': 'READ_BOOK',     'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'LIBRARY', 'cost_money': 5, 'output': 'STAT:KNOWLEDGE_EXP', 'time': 300, 'desc': '读书'},
    {'id': 'COPY_BOOK',     'input': 'SCHOLAR', 'target_type': 'BUILDING', 'target_id': 'LIBRARY', 'output': 'ITEM:书籍:1', 'time': 400, 'desc': '抄书'},
    {'id': 'COMPOSE_MUSIC', 'input': 'SCHOLAR', 'target_type': 'BUILDING', 'target_id': 'LIBRARY', 'output': 'ITEM:琴谱:1', 'time': 500, 'desc': '谱曲'},
    
    # 【道观】炼丹、卜卦
    {'id': 'MAKE_PILL',     'input': 'MONK',    'target_type': 'BUILDING', 'target_id': 'TAOIST', 'ext_input': '草药:3', 'output': 'ITEM:丹药:1', 'time': 450, 'desc': '炼丹'},
    {'id': 'DIVINE',        'input': 'MONK',    'target_type': 'BUILDING', 'target_id': 'TAOIST', 'cost_money': 10, 'output': 'ITEM:情报:1', 'time': 150, 'desc': '卜卦'},
    {'id': 'MAKE_INCENSE',  'input': 'MONK',    'target_type': 'BUILDING', 'target_id': 'TAOIST', 'output': 'ITEM:香烛:2', 'time': 180, 'desc': '制香'},
    
    # ──────────────────────────────────────────────────────────────
    # 江湖/盗匪势力建筑 (游/匪)
    # ──────────────────────────────────────────────────────────────
    
    # 【赌坊】赌博
    {'id': 'GAMBLE_SMALL',  'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'GAMBLING', 'cost_money': 10, 'output': 'ACTION:GAMBLE_SMALL', 'time': 100, 'desc': '小赌怡情'},
    {'id': 'GAMBLE_BIG',    'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'GAMBLING', 'cost_money': 50, 'output': 'ACTION:GAMBLE_BIG', 'time': 150, 'desc': '豪赌'},
    {'id': 'WORK_GAMBLING', 'input': 'MERCHANT','target_type': 'BUILDING', 'target_id': 'GAMBLING', 'output': 'ITEM:铜钱:15', 'time': 200, 'desc': '开设赌局'},
    
    # 【青楼】娱乐场所
    {'id': 'VISIT_BROTHEL', 'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'BROTHEL', 'cost_money': 30, 'output': 'STAT:MOOD_BOOST', 'time': 200, 'desc': '寻欢作乐'},
    {'id': 'PERFORM_SONG',  'input': 'DANCER',  'target_type': 'BUILDING', 'target_id': 'BROTHEL', 'output': 'ITEM:铜钱:15', 'time': 180, 'desc': '卖唱'},
    
    # 【黑市】非法交易
    {'id': 'BUY_STOLEN',    'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'BLACKMARKET', 'cost_money': 30, 'output': 'ITEM:玉器:1', 'time': 100, 'desc': '收购赃物'},
    {'id': 'SELL_STOLEN',   'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'BLACKMARKET', 'ext_input': '玉器:1', 'output': 'ITEM:铜钱:30', 'time': 80, 'desc': '销赃'},
    {'id': 'HIRE_THUG',     'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'BLACKMARKET', 'cost_money': 80, 'output': 'ACTION:HIRE_THUG', 'time': 150, 'desc': '雇佣打手'},
    
    # 【山寨】土匪据点
    {'id': 'BANDIT_REST',   'input': 'BANDIT',  'target_type': 'BUILDING', 'target_id': 'BANDIT_LAIR', 'output': 'STAT:REST', 'time': 200, 'desc': '歇脚'},
    {'id': 'DIVIDE_LOOT',   'input': 'BANDIT',  'target_type': 'BUILDING', 'target_id': 'BANDIT_LAIR', 'output': 'ITEM:铜钱:20', 'time': 300, 'desc': '分赃'},
    {'id': 'PLAN_RAID',     'input': 'BANDIT',  'target_type': 'BUILDING', 'target_id': 'BANDIT_LAIR', 'output': 'ACTION:PLAN_RAID', 'time': 400, 'desc': '谋划劫掠'},
    
    # ──────────────────────────────────────────────────────────────
    # 农业/畜牧建筑 (农)
    # ──────────────────────────────────────────────────────────────
    
    # 【猎场】狩猎
    {'id': 'HUNT',          'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'HUNTING', 'output': 'ITEM:生肉:1', 'time': 250, 'desc': '狩猎'},
    {'id': 'SET_TRAP',      'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'HUNTING', 'ext_input': '陷阱:1', 'output': 'ITEM:皮革:1', 'time': 300, 'desc': '设置陷阱'},
    {'id': 'GATHER_HERB',   'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'HUNTING', 'output': 'ITEM:草药:1', 'time': 180, 'desc': '采药'},
    
    # 【磨坊】加工粮食
    {'id': 'MILL_WHEAT',    'input': 'FARMER',  'target_type': 'BUILDING', 'target_id': 'MILL', 'ext_input': '小麦:2', 'output': 'ITEM:馒头:2', 'time': 150, 'desc': '磨面蒸馒头'},
    {'id': 'MILL_RICE',     'input': 'FARMER',  'target_type': 'BUILDING', 'target_id': 'MILL', 'ext_input': '稻米:1', 'output': 'ITEM:米饭:1', 'time': 100, 'desc': '蒸米饭'},
    {'id': 'MAKE_NOODLE',   'input': 'FARMER',  'target_type': 'BUILDING', 'target_id': 'MILL', 'ext_input': '小麦:2', 'output': 'ITEM:面条:1', 'time': 120, 'desc': '擀面条'},
    
    # 【牧场】养殖
    {'id': 'RAISE_SHEEP',   'input': 'FARMER',  'target_type': 'BUILDING', 'target_id': 'RANCH', 'output': 'ITEM:羊毛:1', 'time': 300, 'desc': '牧羊'},
    {'id': 'BUTCHER',       'input': 'FARMER',  'target_type': 'BUILDING', 'target_id': 'RANCH', 'output': 'ITEM:生肉:2', 'time': 250, 'desc': '宰杀牲畜'},
    {'id': 'TAN_LEATHER',   'input': 'ARTISAN', 'target_type': 'BUILDING', 'target_id': 'RANCH', 'ext_input': '皮革:2', 'output': 'ITEM:护臂:1', 'time': 200, 'desc': '鞣制皮具'},
    
    # ──────────────────────────────────────────────────────────────
    # 通用烹饪扩展
    # ──────────────────────────────────────────────────────────────
    {'id': 'COOK_MEAT',     'input': '生肉',    'target_type': 'BUILDING', 'target_id': 'CAMPFIRE', 'output': 'ITEM:烤肉:1', 'time': 150, 'desc': '烤肉'},
    {'id': 'BOIL_WATER',    'input': 'ANY',     'target_type': 'BUILDING', 'target_id': 'CAMPFIRE', 'output': 'ITEM:清水:1', 'time': 60, 'desc': '烧水'},
    
    # ──────────────────────────────────────────────────────────────
    # 建造扩展配方
    # ──────────────────────────────────────────────────────────────
    {'id': 'BUILD_SMITHY',   'input': '木材', 'req_count': 8,  'target_type': 'HUMAN', 'target_id': 'ANY', 'ext_input': '铁料:3', 'output': 'BUILDING:SMITHY', 'time': 600, 'desc': '建造铁匠铺'},
    {'id': 'BUILD_STABLE',   'input': '木材', 'req_count': 6,  'target_type': 'HUMAN', 'target_id': 'ANY', 'output': 'BUILDING:STABLE', 'time': 500, 'desc': '建造马厩'},
    {'id': 'BUILD_TEAHOUSE', 'input': '木材', 'req_count': 6,  'target_type': 'HUMAN', 'target_id': 'ANY', 'output': 'BUILDING:TEAHOUSE', 'time': 450, 'desc': '建造茶馆'},
    {'id': 'BUILD_PHARMACY', 'input': '木材', 'req_count': 5,  'target_type': 'HUMAN', 'target_id': 'ANY', 'output': 'BUILDING:PHARMACY', 'time': 400, 'desc': '建造药铺'},
    {'id': 'BUILD_MILL',     'input': '木材', 'req_count': 5,  'target_type': 'HUMAN', 'target_id': 'ANY', 'ext_input': '石料:2', 'output': 'BUILDING:MILL', 'time': 450, 'desc': '建造磨坊'},
]

recipe_headers = ['id', 'input', 'req_count', 'ext_input', 'cost_money', 'target_type', 'target_id', 'output', 'time', 'desc']




def write_csv(filename, headers, data):
    path = os.path.join('../data', filename)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in data:
            writer.writerow({k: row.get(k, '') for k in headers})
    print(f"Generated {path}")

if __name__ == "__main__":
    write_csv('items.csv', item_headers, items)
    write_csv('recipes.csv', recipe_headers, recipes)