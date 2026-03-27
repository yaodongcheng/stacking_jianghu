# --- src/definitions.py ---
import pygame
from enum import Enum

class Emotion(Enum):
    """NPC情绪枚举"""
    NORMAL = ("NORMAL", "平静")
    HAPPY = ("HAPPY", "开心")
    SAD = ("SAD", "悲伤")
    ANGRY = ("ANGRY", "愤怒")
    DEPRESSED = ("DEPRESSED", "沮丧")
    DESPAIR = ("DESPAIR", "绝望")
    ANXIOUS = ("ANXIOUS", "焦虑")
    CONFUSED = ("CONFUSED", "困惑")

# 兼容旧的常量定义（只取value的第一项）
EMOTION_NORMAL = Emotion.NORMAL.value[0]
EMOTION_HAPPY = Emotion.HAPPY.value[0]
EMOTION_SAD = Emotion.SAD.value[0]
EMOTION_ANGRY = Emotion.ANGRY.value[0]
EMOTION_DEPRESSED = Emotion.DEPRESSED.value[0]
EMOTION_DESPAIR = Emotion.DESPAIR.value[0]
EMOTION_ANXIOUS = Emotion.ANXIOUS.value[0]
EMOTION_CONFUSED = Emotion.CONFUSED.value[0]

# 情绪中文映射（便于UI层使用）
EMOTION_CN = {e.value[0]: e.value[1] for e in Emotion}

# =========================================
# 调试开关
# =========================================
DEBUG_FATE_GRAPH_TEST_DATA = True  # 命运图谱是否使用测试数据

# =========================================
# 游戏状态常量
# =========================================
SIDEBAR_W = 280  # 侧边栏宽度

TOPBAR_H = 50    # 顶部栏高度

# ── 小地图 UI 参数（通用，所有剧本共享）──────────────────────────
MINIMAP_W = 180          # 小地图宽度（px）
MINIMAP_H = 120          # 小地图高度（px）
MINIMAP_MARGIN = 8       # 小地图与右边栏左边缘的间距（px）
MINIMAP_ALPHA = 210      # 小地图背景透明度（0~255）

# ── 视口边缘滚动参数 ────────────────────────────────────────────
EDGE_SCROLL_ZONE = 80    # 鼠标距屏幕边缘多少像素内触发自动滚动（px）
EDGE_SCROLL_SPEED = 20   # 边缘滚动速度（px/帧，越靠近边缘越快，最高可达此值2倍）

# ── 世界边界保护参数 ────────────────────────────────────────────
WORLD_BOUNDARY_PADDING = 20  # 卡牌距世界边界的最小距离（px），防止NPC被打到地图外

# =========================================
# 1. 游戏核心状态 & 流程
# =========================================
GAME_STATE_PLAYING = 1     
GAME_STATE_EVENT_DIALOG = 2  
GAME_STATE_NEWS_FEED = 3     
GAME_STATE_NPC_DETAIL = 4    
GAME_STATE_DAILY_REPORT = 5  
GAME_STATE_GAME_OVER = 6     
GAME_STATE_ROSTER = 7        
GAME_STATE_TECH_TREE = 8   
GAME_STATE_RESOURCE_DETAIL = 9
GAME_STATE_QUEST_LOG = 10
GAME_STATE_FACTION_VIEW = 11  # 【阶段4】势力关系面板
GAME_STATE_PERSUASION = 12     # 【阶段1】语言检定界面
GAME_STATE_PERSUASION_RESULT = 13  # 【阶段1】检定结果显示
GAME_STATE_ORG_TASK_DIALOG = 14  # 【组织任务】长老对话界面
GAME_STATE_GUARD_INTERCEPT = 15  # 【阶层系统】护卫拦截界面
GAME_STATE_FOLLOWER_PANEL = 16   # 【门客管理】门客管理面板
GAME_STATE_RUMOR_PANEL = 17      # 【传闻系统】江湖传闻面板
GAME_STATE_FEE_CONFIRM = 18      # 【手续费系统】使用费确认弹窗
GAME_STATE_BUILDING_INFO = 19    # 【建筑面板】建筑详情与占领界面
GAME_STATE_LIVE_SNAPSHOT = 20    # 【大宋实况】实况快照面板
GAME_STATE_FATE_GRAPH = 21       # 【命运图谱】NPC命运轨迹面板

# UI 面板状态列表：打开这些面板时禁止摄像机边缘滚动
UI_PANEL_STATES = [
    GAME_STATE_TECH_TREE,
    GAME_STATE_NEWS_FEED,
    GAME_STATE_ROSTER,
    GAME_STATE_FACTION_VIEW,
    GAME_STATE_QUEST_LOG,
    GAME_STATE_FATE_GRAPH,
    GAME_STATE_NPC_DETAIL,
    GAME_STATE_FOLLOWER_PANEL,
    GAME_STATE_LIVE_SNAPSHOT,  # 大宋实况详细面板
]
# =========================================
# 2. 视觉配置
# =========================================
# --- 场景颜色 ---
COLOR_BG = (50, 60, 50)             
COLOR_CITY_GROUND = (120, 115, 110) 
COLOR_WALL = (60, 55, 50)           
COLOR_GATE = (100, 90, 80)          

# --- 卡牌专用视觉 ---
COLOR_CARD_BG = (230, 225, 210)     
COLOR_CARD_BORDER = (50, 50, 50)    
COLOR_PROGRESS_BAR = (100, 100, 200)
COLOR_PROGRESS_BG = (80, 80, 80) 
COLOR_HIGHLIGHT = (255, 215, 0)     

# --- 卡牌类型颜色区分 ---
COLOR_EVENT_CARD = (220, 100, 100)   
COLOR_PLAYER_CARD = (193, 210, 240)  
COLOR_RESOURCE_CARD = (100, 180, 100) # [新增] 资源卡颜色 (绿色系)
COLOR_NPC_CARD = (230, 225, 210)     
COLOR_BUILDING_CARD = (180, 180, 190) 

# --- UI 通用颜色 ---
COLOR_UI_PANEL = (40, 40, 45, 250)    
COLOR_BTN = (70, 70, 80)
COLOR_BTN_HOVER = (100, 100, 110)
COLOR_BTN_DISABLED = (40, 30, 30) 

# --- 字体颜色配置 ---
COLOR_TEXT = (230, 230, 230)   
COLOR_TEXT_DARK = (20, 20, 20) 
COLOR_TEXT_WHITE = (255, 255, 255)   
COLOR_COST_BAD = (255, 100, 100) 
COLOR_COST_GOOD = (100, 255, 100) 
COLOR_TAG_NEUTRAL = (180, 180, 200)

# =========================================
# 3. 卡牌物理参数
# =========================================
CARD_W, CARD_H = 70, 90  
CARD_HEADER_H = 22        
STACK_OFFSET_Y = 30       

# =========================================
# 4. 实体属性枚举
# =========================================
ECO_POOR = "POOR"       
ECO_COMMON = "COMMON"   
ECO_ENOUGH = "ENOUGH"   
ECO_RICH = "RICH"       

SOC_LOW = "LOW"         
SOC_COMMON = "COMMON"   
SOC_NOBLE = "NOBLE"     

FREE_SLAVE = "SLAVE"    
FREE_FULL = "FULL"      

FAMILY_ISOLATED = "ISOLATED" 
FAMILY_LOCAL = "LOCAL"       

# 情绪枚举已移至文件顶部的Emotion类定义

SAFETY_NORMAL = "NORMAL"
SAFETY_DANGER = "DANGER" 
SAFETY_DEAD = "DEAD"     
SAFETY_EXILED = "EXILED" 
SAFETY_DOWNED = "DOWNED" # [新增] 重伤 (未死，但失去行动力)

# =========================================
# 5. 逻辑状态与类型
# =========================================
CARD_TYPE_HUMAN = "HUMAN"       
CARD_TYPE_RESOURCE = "RESOURCE" 
CARD_TYPE_EVENT = "EVENT"       
CARD_TYPE_BUILDING = "BUILDING" 

# --- NPC/卡牌 行为状态 ---
STATE_IDLE = "IDLE"           
STATE_MOVING = "MOVING"       
STATE_WORKING = "WORKING"     
STATE_TRADING = "TRADING"     
STATE_CHATTING = "CHATTING"   
STATE_EVENT = "EVENT"         
STATE_GONE = "GONE"           
STATE_MEETING = "MEETING"     
STATE_WATCHING = "WATCHING"
STATE_COMBAT = "COMBAT"

# [新增] 状态
STATE_CARRYING = "CARRYING"   # 搬运物资中
STATE_SLEEPING = "SLEEPING"   # 休息/回家
STATE_DOWNED = "DOWNED"       # [新增] 重伤倒地
STATE_FLEEING = "FLEEING"     # [新增] 逃跑中
STATE_FOLLOW = "FOLLOW"       # [新增] 跟随主人（门客状态）

# --- 区域定义 ---
ZONE_OUTER = "OUTER"   
ZONE_INNER = "INNER"   
ZONE_FARM = "FARM"     
ZONE_MARKET = "MARKET" 
ZONE_SLUM = "SLUM"     

# --- 物品定义 ---
ITEM_COIN = "铜钱"  # 与 items.csv 保持一致
ITEM_GRAIN = "谷物"
ITEM_BERRY = "浆果"
ITEM_WOOD = "木材"

# --- 阶段1：职业产出物品 ---
ITEM_BOOK = "书卷"           # 学者产出
ITEM_MERIT = "功德"          # 僧侣功德值（虚拟）
ITEM_CRAFT = "精制器物"      # 工匠产出
ITEM_CLOTH = "布料"          # 工匠产出
ITEM_IRON = "铁器"           # 工匠产出
ITEM_FOOD = "熟食"           # 烹饪产出（可消费）
ITEM_CLOTHING = "棉袄"       # 服装（御寒消费品）

# --- 阶段2：商人贸易状态 ---
MERCHANT_STATE_IDLE = "IDLE"           # 空闲
MERCHANT_STATE_BUYING = "BUYING"       # 进货中
MERCHANT_STATE_SELLING = "SELLING"     # 卖货中
MERCHANT_STATE_RESTOCKING = "RESTOCK"  # 补货中

# [新增] 剧本常量
SCENARIO_TUTORIAL = "SCENARIO_TUTORIAL"
SCENARIO_SANDBOX = "SCENARIO_SANDBOX"

# ═══════════════════════════════════════════════════════════════
# NPC 名字常量（与 character_seeds.py 保持一致，避免硬编码字符串散落各处）
# ═══════════════════════════════════════════════════════════════
NPC_HEIFENG_DAWANG = '黑风大王'   # 黑风寨首领
NPC_POPI_NIUER = '泼皮牛二'       # 泼皮1
NPC_POPI_GOUDAN = '泼皮狗蛋'      # 泼皮2
NPC_YU_XISHI = '鱼西施'           # 卖鱼姑娘
NPC_CUNZHANG = '村长'             # 新手教程村长（特殊NPC，ID=9000）


# --- 新增职业 ---
JOB_SCHOLAR = 'SCHOLAR'  # 士
JOB_FARMER = 'FARMER'    # 农
JOB_ARTISAN = 'ARTISAN'  # 工
JOB_MERCHANT = 'MERCHANT'# 商
JOB_GUARD = 'GUARD'      # 兵
JOB_BANDIT = 'BANDIT'    # 匪
JOB_MONK = 'MONK'        # 僧
JOB_OFFICIAL = 'OFFICIAL'# 官
JOB_NONE = 'NONE'        # 流民

# --- 职业中文映射（唯一定义，勿在其他地方重复）---
JOB_LABELS = {
    'FARMER': '农夫', 'MERCHANT': '商贾', 'THUG': '泼皮', 
    'SCHOLAR': '书生', 'DOCTOR': '郎中', 'DANCER': '舞姬', 
    'GUARD': '护院', 'NONE': '流民', 'PLAYER': '玩家', 
    'BANDIT': '山贼', 'OFFICIAL': '官差', 'MONK': '僧人',
    'ARTISAN': '工匠'
}

# --- 组织 ---
ORG_NONE = 'NONE'
ORG_GOV = 'GOV'

# --- 游戏平衡参数 ---
DAILY_FOOD_CONSUMPTION = 1    # 每人每天消耗粮食
DAILY_WAGE_BASE = 10          # 基础日薪
SANITY_LOSS_HUNGRY = 20       # 没饭吃的理智惩罚
SANITY_LOSS_NO_PAY = 10       # 没发工资的理智惩罚
MAX_GRAIN_STACK = 5           # NPC身上最多背多少粮
# --- 新增数值常量 ---
MAX_HUNGER = 100
MAX_COLD = 100
MAX_DISSATISFACTION = 100
HUNGER_DAMAGE_THRESHOLD = 80 # 饥饿超过这个值开始扣血
COLD_DAMAGE_THRESHOLD = 80   # 寒冷超过这个值开始扣血

TICKS_PER_DAY = 7200 # 120秒 = 1天 (在1倍速下)

# --- 移动系统时间步长 ---
# NPC 移动逻辑每隔多少毫秒执行一次（与渲染帧率解耦）
# 100ms = 0.1s，每次步长约为 speed * 0.1，确保每步至少移动数像素
MOVE_LOGIC_INTERVAL_MS = 50   # ms 

QS_AVAILABLE = "AVAILABLE"
QS_ACTIVE = "ACTIVE"
QS_READY = "READY"
QS_FINISHED = "FINISHED"

DEBUG_COMBAT = False  # 战斗相关调试打印，默认关闭
DEBUG_RECIPE_AI = False  # NPC配方驱动AI调试（去建筑合成配方），默认关闭
DEBUG_ORG_AGGRO = False  # NPC组织仇恨感知调试（感知友方被攻击），默认关闭
DEBUG_SKIP_YUXISHI = True  # 【调试】跳过鱼西施主线，直接进入自由模式
DEBUG_LIVE_NEWS_TEST_EVENT = False  # 【调试】在大宋实况-历史版面显示测试事件

# [新增] 允许控制非己方 NPC (如丢弃物品)
DEBUG_CONTROLNPC = False 

# =========================================
# 寻路调试开关
# =========================================

# --- 主角调试 ---
# 开启后：主角的寻路过程实时打印到控制台
DEBUG_PLAYER_PATH = False

# --- NPC 调试（点击选中触发）---
# 开启后：点击 NPC 时不触发详情页，而是将该 NPC 设为寻路调试对象
DEBUG_NPC_PATH_NO_PAUSE = False
# 开启后：被选中调试的 NPC，其寻路过程实时打印到控制台
DEBUG_NPC_PATH_VERBOSE = False

# --- 渲染调试 ---
# 开启后：在画面上绘制路点图和当前路径
DEBUG_NPCPATHFINDING = False

# --- 隐身调试 ---
# 开启后：隐身单位仍然显示，但用半透明紫色边框标记
DEBUG_SHOW_INVISIBLE = True

# =========================================
# 剧情对话显示模式
# =========================================
# 'BUBBLE'  - 角色气泡式：对话框显示在说话角色头顶（默认，适合小品级游戏）
# 'SUBTITLE' - 底部字幕式：对话框固定在屏幕下方（适合3A大作风格）
DIALOG_DISPLAY_MODE = 'BUBBLE'

# =========================================
# 事件通知显示模式
# =========================================
# 'CORNER'  - 右上角模式：事件通知卡片固定显示在屏幕右上角（默认）
# 'ON_SITE' - 事发地模式：事件通知卡片显示在事件发生的地点
#             如果事件超出摄像机范围，显示在最靠近的边界并添加方向箭头
EVENT_DISPLAY_MODE = 'ON_SITE'

# 事发地显示配置
EVENT_ONSITE_CARD_OFFSET_X = 20    # 卡片相对事件位置的X偏移（避免遮挡）
EVENT_ONSITE_CARD_OFFSET_Y = -80   # 卡片相对事件位置的Y偏移（显示在事件上方）
EVENT_ARROW_SIZE = 16              # 方向箭头大小（像素）
EVENT_ARROW_MARGIN = 30            # 箭头距屏幕边缘的最小距离

# 气泡式对话框配置
BUBBLE_MAX_WIDTH = 280        # 气泡最大宽度
BUBBLE_PADDING = 12           # 气泡内边距
BUBBLE_OFFSET_Y = 20          # 气泡相对角色头顶的Y偏移（向上）
BUBBLE_BG_COLOR = (30, 30, 40, 220)      # 气泡背景色（RGBA）
BUBBLE_BORDER_COLOR = (200, 180, 120)    # 气泡边框色
BUBBLE_NAME_COLOR = (255, 230, 150)      # 说话者名字颜色
BUBBLE_TEXT_COLOR = (255, 255, 255)      # 对话文本颜色

# =========================================
# LLM / AI 超时配置（秒） - 统一 TIMEOUT_ 前缀
# =========================================

# --- DeepSeek LLM API 超时 ---
TIMEOUT_LLM_SIMPLE = 10          # 普通NPC对话（max_tokens ≤ 1000）
TIMEOUT_LLM_COMPLEX = 120        # 复杂任务如对话扩写（max_tokens > 1000）
TIMEOUT_LLM_DIRECTOR = 90        # 导演系统决策（生成事件JSON）

# --- 图像生成 API 配置 ---
# 选择图像生成服务提供商
# 'DOUBAO'  - 使用豆包(Volcengine)官方API (默认)
# 'DANQINGYUE' - 使用丹青约API (网易伏羲)
IMAGE_GEN_PROVIDER = 'DANQINGYUE'

# --- 豆包图像生成 API 超时 ---
TIMEOUT_IMAGE_GEN = 120           # 单次图像生成请求超时

# --- 事件预生成系统超时 ---
TIMEOUT_PREGEN_TOTAL = 120.0     # 完整预生成流程（对话+图像）总超时
TIMEOUT_PREGEN_WAIT = 130.0      # 等待预生成完成的超时（略大于总超时）
TIMEOUT_PREGEN_RESULT = 60.0     # 等待单个结果的超时

# --- DirectorEventManager 超时 ---
TIMEOUT_DIRECTOR_REQUEST = 180.0 # 导演事件管理器请求超时（需大于TIMEOUT_PREGEN_TOTAL+余量）

# --- NPC 记忆系统超时 ---
TIMEOUT_MEMORY_QUERY = 10        # NPC记忆向量查询超时

# --- NPC 移动超时（毫秒）---
TIMEOUT_NPC_MOVE_MS = 10000      # NPC移动Action默认超时
