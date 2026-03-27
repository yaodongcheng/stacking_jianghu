# src/ui/live_news_panel.py
"""
═══════════════════════════════════════════════════════════════════════════════
【大宋实况】新闻面板 - 当前事件 + 历史事件查看
═══════════════════════════════════════════════════════════════════════════════

功能：
  1. 显示当前活跃的新闻事件
  2. 显示历史新闻事件（可滚动）
  3. 点击查看事件详情
  4. 筛选功能（按分类、按优先级）
"""

import pygame
import time
import os
from pathlib import Path as PyPath
from typing import Optional, List, Callable, Tuple
from enum import Enum

from src.ui.event_notification import (
    LiveNewsItem, EventNotificationManager, 
    get_notification_manager, NewsCategory,
    draw_event_card
)
from src.definitions import SIDEBAR_W, DEBUG_LIVE_NEWS_TEST_EVENT
from src.utils import resource_path

from src.ui.event_notification import LiveNewsItem, NewsCategory, DilemmaType

class NewsTab(Enum):
    """新闻标签页"""
    CURRENT = "当前"
    HISTORY = "历史"


class LiveNewsPanel:
    """
    大宋实况新闻面板
    
    显示当前活跃事件和历史事件的完整列表
    """
    
    # 布局
    PANEL_WIDTH = 420
    PANEL_HEIGHT = 550
    HEADER_HEIGHT = 50
    TAB_HEIGHT = 36
    ITEM_HEIGHT = 80  # 与 EventNotificationManager 保持一致
    ITEM_MARGIN = 10  # 与 EventNotificationManager 保持一致
    PADDING = 16
    SCROLL_WIDTH = 8
    
    # 头像缓存（复用通知管理器的缓存）
    _shared_avatar_cache: dict = {}
    
    # 颜色
    COLOR_BG = (25, 23, 35, 245)
    COLOR_HEADER = (35, 32, 50)
    COLOR_TAB_ACTIVE = (60, 80, 120)
    COLOR_TAB_INACTIVE = (40, 38, 55)
    COLOR_ITEM_BG = (38, 35, 52)
    COLOR_ITEM_HOVER = (50, 48, 70)
    COLOR_ITEM_UNREAD = (45, 50, 70)
    COLOR_BORDER = (70, 65, 90)
    COLOR_TEXT = (240, 240, 250)
    COLOR_TEXT_DIM = (160, 160, 180)
    COLOR_TEXT_MUTED = (120, 120, 140)
    COLOR_ACCENT = (100, 150, 255)
    COLOR_URGENT = (255, 120, 100)
    COLOR_SCROLL = (80, 75, 100)
    COLOR_SCROLL_THUMB = (120, 115, 150)
    
    # 分类颜色
    CATEGORY_COLORS = {
        NewsCategory.ECONOMIC: (255, 200, 80),
        NewsCategory.SOCIAL: (100, 200, 255),
        NewsCategory.MORAL: (200, 150, 255),
        NewsCategory.MARTIAL: (255, 100, 100),
        NewsCategory.SUPERNATURAL: (100, 255, 180),
        NewsCategory.POLITICAL: (255, 180, 100),
    }
    
    # 分类名称
    CATEGORY_NAMES = {
        NewsCategory.ECONOMIC: "经济",
        NewsCategory.SOCIAL: "社会",
        NewsCategory.MORAL: "道德",
        NewsCategory.MARTIAL: "武林",
        NewsCategory.SUPERNATURAL: "奇闻",
        NewsCategory.POLITICAL: "官场",
    }
    
    def __init__(self, screen_w: int, screen_h: int):
        self.screen_w = screen_w
        self.screen_h = screen_h
        
        # 面板位置（居中偏上）
        self.panel_x = (screen_w - SIDEBAR_W - self.PANEL_WIDTH) // 2
        self.panel_y = (screen_h - self.PANEL_HEIGHT) // 2 - 30
        
        # 状态
        self.visible = False
        self.current_tab = NewsTab.CURRENT
        self.scroll_offset = 0
        self.max_scroll = 0
        self.hovered_item_index = -1
        self.is_scrolling = False
        self.scroll_drag_start_y = 0
        self.scroll_drag_start_offset = 0
        
        # 字体缓存
        self._font_cache = {}
        
        # 回调
        self.on_item_click: Optional[Callable[[LiveNewsItem], None]] = None
        self.on_close: Optional[Callable[[], None]] = None
        
        # 动画
        self.open_progress = 0.0
        self.target_progress = 0.0
        
        # 【调试】添加测试事件到历史
        if DEBUG_LIVE_NEWS_TEST_EVENT:
            self._add_test_event()
    
    def _add_test_event(self):
        """添加调试测试事件 - 添加多个不同场景的事件以测试布局
        
        【角色说明】使用 npc_data.csv 中实际存在的角色：
        - 1000:方承意, 1001:无情, 1002:林冲, 1003:高衙内, 1004:高大胜
        - 1005:张青, 1006:郁芊芊, 1007:孙二娘, 1008:王小乐, 1009:李师师
        - 1010:袁桐, 1011:孙小溪, 1012:鲁智深, 1013:弥乐, 1014:阿禅
        - 1015:洪小六, 1016:赵师爷, 1017:铁牛, 1018:钱掌柜, 1019:老李头
        - 1020:小翠, 1021:黑风大王, 1022:山贼甲, 1023:山贼乙, 1024:泼皮牛二
        
        重构说明：
        - 不再需要 LiveSnapshotData，直接在 LiveNewsItem 上设置属性
        - story_choices 存储故事选项
        """
        
        # 基础时间（当前时间），每个事件间隔5分钟
        base_time = time.time()
        
        # ═══════════════════════════════════════════════════════════════════════
        # 测试事件1：标准事件（2个当事人）- 最早发生（20分钟前）
        # 使用角色：郁芊芊(1006) vs 泼皮牛二(1024) - 商会与泼皮的冲突
        # ═══════════════════════════════════════════════════════════════════════
        test_news_1 = LiveNewsItem(
            id="test_event_001",
            title="【爆款】甜水巷商会与泼皮发生冲突！",
            description="郁芊芊的商队运送贵重布料途中，被泼皮牛二当街拦路勒索。牛二声称要收'过路费'，否则不让通行。郁芊芊不愿屈服，双方僵持不下。郁芊芊的商队运送贵重布料途中，被泼皮牛二当街拦路勒索。牛二声称要收'过路费'，否则不让通行。郁芊芊不愿屈服，双方僵持不下。",
            category=NewsCategory.SOCIAL,
            dilemma_type=DilemmaType.MORAL_GREY,
            actor_ids=[1006, 1024],  # 郁芊芊, 泼皮牛二
            actor_names=["郁芊芊", "泼皮牛二"],
            location="无更市甜水巷",
            story_choices=[
                {"text": "帮助郁芊芊赶走泼皮", "effect": "JUSTICE:+20;FAME:+10"},
                {"text": "暗中调解，各退一步", "effect": "INTEL:+15;GOLD:-30"},
                {"text": "静观其变", "effect": "NEUTRAL"}
            ],
            priority=4,
            auto_popup=False,
            tags=["郁芊芊", "泼皮牛二", "商会", "勒索"],
            comments=[
                {"user": "张青", "text": "这泼皮太可恶了，必须严惩！", "type": "支持"},
                {"user": "孙二娘", "text": "郁大小姐太可怜了，希望有人能帮她", "type": "中立"},
                {"user": "李师师", "text": "郁姐姐人很好的，牛二太过分了", "type": "支持"},
                {"user": "高衙内", "text": "嘿嘿，有意思，本公子去看看", "type": "搞笑"},
            ],
            heat_score=25888,
            image_prompt="A dramatic scene in ancient Chinese market...",
            image_url="placeholder"
        )
        test_news_1.setup_ui_choices(level=1)  # 初始化 UI 选项
        test_news_1.is_resolved = False  # 未解决
        test_news_1.read = False
        test_news_1.created_at = base_time - 20 * 60  # 20分钟前
        
        # 【添加对话扩写】测试事件1：郁芊芊 vs 泼皮牛二
        from src.llm.event_dialog_generator import EventScriptFull, EventDialogLine
        test_news_1._pregen_script = EventScriptFull(
            intro_dialogs=[
                EventDialogLine('NARRATOR', '甜水巷人来人往，一队商队被堵在路中央。', ''),
                EventDialogLine('OTHER', '郁大小姐，这条路是我牛二开的，想过就得留下买路钱！', ''),
                EventDialogLine('SELF', '牛二！你不要太放肆，我郁家商队你也敢拦？', ''),
                EventDialogLine('OTHER', '嘿嘿，郁家又怎样？今天不给钱，谁也别想走！', ''),
                EventDialogLine('NARRATOR', '牛二一挥手，几个泼皮围了上来，气氛剑拔弩张。', 'SHAKE_CAMERA:3'),
                EventDialogLine('SELF', '你...你们想怎样？', 'SET_EMOTION:郁芊芊:SCARED'),
                EventDialogLine('OTHER', '很简单，一百两银子，或者...把货留下！', ''),
                EventDialogLine('NARRATOR', '围观百姓指指点点，却无人敢上前。你，会怎么做？', 'SHOW_EVENT_CHOICE')
            ],
            choice_a_dialogs=[
                EventDialogLine('PLAYER', '光天化日，竟敢当街勒索！给我住手！', ''),
                EventDialogLine('OTHER', '你、你是什么人？敢管老子的闲事！', 'SET_EMOTION:泼皮牛二:ANGRY'),
                EventDialogLine('SELF', '恩公！多谢恩公仗义执言！', 'SET_EMOTION:郁芊芊:HAPPY'),
                EventDialogLine('PLAYER', '还不快滚？再让我看见你作恶，定不轻饶！', ''),
                EventDialogLine('OTHER', '哼...算你们狠！咱们走着瞧！', 'NPC_FLEE:泼皮牛二'),
                EventDialogLine('NARRATOR', '泼皮们灰溜溜地逃走了，郁芊芊感激地看着你。', 'SET_AFFINITY:郁芊芊:+30;PLAYER_FAME:+10')
            ],
            choice_b_dialogs=[
                EventDialogLine('PLAYER', '两位且慢动手，听我一言。', ''),
                EventDialogLine('OTHER', '哦？你想说什么？', ''),
                EventDialogLine('PLAYER', '牛二哥，郁家商队常走这条路，何必把事情做绝？三十两银子，买杯茶喝，如何？', ''),
                EventDialogLine('OTHER', '嗯...既然有人求情，那就给这个面子。', ''),
                EventDialogLine('SELF', '多谢恩公调解...只是这三十两...', ''),
                EventDialogLine('NARRATOR', '你帮郁芊芊解了围，也给了牛二台阶下，双方各退一步。', 'PLAYER_MONEY:-30;INTEL:+15')
            ],
            choice_c_dialogs=[
                EventDialogLine('PLAYER', '（站在人群中静静观察）', ''),
                EventDialogLine('OTHER', '怎么样？想好了没有？', ''),
                EventDialogLine('SELF', '你...你别欺人太甚！', ''),
                EventDialogLine('NARRATOR', '双方僵持不下，最终郁芊芊咬牙掏了五十两银子，牛二得意洋洋地离开了。', 'SET_AFFINITY:郁芊芊:-10'),
                EventDialogLine('NARRATOR', '你选择了旁观，这件事与你无关。', '')
            ]
        )
        
        # ═══════════════════════════════════════════════════════════════════════
        # 测试事件2：多个当事人（测试头像和名字省略）- 15分钟前
        # 使用角色：黑风寨众人 - 黑风大王(1021), 山贼甲(1022), 山贼乙(1023) + 泼皮牛二(1024) + 洪小六(1015)
        # ═══════════════════════════════════════════════════════════════════════
        test_news_2 = LiveNewsItem(
            id="test_event_002",
            title="黑风寨众匪当街斗殴引发骚乱，路人纷纷躲避",
            subtitle="多人受伤，官府已介入调查",
            category=NewsCategory.MARTIAL,
            actor_ids=[1021, 1022, 1023, 1024, 1015],
            actor_names=["黑风大王", "山贼甲", "山贼乙", "泼皮牛二", "洪小六"],
            location="无更市东街",
            story_choices=[
                {"text": "上前制止", "effect": "FAME:+30"},
                {"text": "暗中观察", "effect": "NEUTRAL"},
            ],
            priority=3,
            tags=["黑风寨", "斗殴", "骚乱"],
            comments=[
                {"user": "鱼西施", "text": "这些土匪太嚣张了，官府人呢？", "type": "反对"},
                {"user": "赵师爷", "text": "此事需从长计议，不可轻举妄动", "type": "中立"},
                {"user": "王小乐", "text": "哈哈哈打得好热闹，比戏班子还好看", "type": "搞笑"},
                {"user": "郁芊芊", "text": "洪小六也在其中？他平时看着挺老实的", "type": "中立"},
            ],
            heat_score=15234,
            image_url="placeholder"
        )
        test_news_2.setup_ui_choices(level=1)
        test_news_2.is_resolved = False  # 未解决
        test_news_2.read = False
        test_news_2.created_at = base_time - 15 * 60  # 15分钟前
        
        # 【添加对话扩写】测试事件2：黑风寨斗殴
        test_news_2._pregen_script = EventScriptFull(
            intro_dialogs=[
                EventDialogLine('NARRATOR', '东街酒肆前，两拨人马对峙，剑拔弩张。', ''),
                EventDialogLine('OTHER', '黑风大王，你抢了我们牛哥的生意，今天必须给个说法！', ''),
                EventDialogLine('SELF', '哼，无更市的街道，谁拳头硬谁说了算！', ''),
                EventDialogLine('OTHER', '好大的口气！兄弟们，给我上！', ''),
                EventDialogLine('NARRATOR', '双方瞬间混战在一起，刀光剑影，百姓四散奔逃。', 'SHAKE_CAMERA:8;FLASH_WHITE:100'),
                EventDialogLine('SELF', '来得好！让尔等见识见识黑风寨的厉害！', ''),
                EventDialogLine('OTHER', '洪小六，你还愣着干什么？动手啊！', ''),
                EventDialogLine('NARRATOR', '洪小六犹豫地站在一旁。你，会怎么做？', 'SHOW_EVENT_CHOICE')
            ],
            choice_a_dialogs=[
                EventDialogLine('PLAYER', '都给我住手！光天化日之下，成何体统！', ''),
                EventDialogLine('SELF', '你是什么人？敢管我们的闲事？', 'SET_EMOTION:黑风大王:ANGRY'),
                EventDialogLine('PLAYER', '我乃无更市侠客，专管不平之事！', ''),
                EventDialogLine('OTHER', '大侠饶命！我们不敢了！', 'SET_EMOTION:泼皮牛二:SCARED'),
                EventDialogLine('NARRATOR', '你的威名震慑了众人，双方各自散去，街道恢复平静。', 'NPC_FLEE:黑风大王;NPC_FLEE:泼皮牛二;PLAYER_FAME:+30')
            ],
            choice_b_dialogs=[
                EventDialogLine('PLAYER', '（躲在暗处观察，寻找时机）', ''),
                EventDialogLine('NARRATOR', '双方打得难解难分，洪小六趁机溜走了。', ''),
                EventDialogLine('SELF', '今日算你们走运，改日再算账！', ''),
                EventDialogLine('OTHER', '哼，谁怕谁！', ''),
                EventDialogLine('NARRATOR', '你选择了旁观，这场斗殴最终不了了之。', '')
            ],
            choice_c_dialogs=[
                EventDialogLine('PLAYER', '（悄悄离开，去报官）', ''),
                EventDialogLine('NARRATOR', '你快步走向衙门，将此事告知捕快。', ''),
                EventDialogLine('NARRATOR', '等捕快赶到时，双方已经散去，只留下一片狼藉。', ''),
                EventDialogLine('NARRATOR', '虽然没有制止斗殴，但你尽了一个市民的责任。', '')
            ]
        )
        
        # ═══════════════════════════════════════════════════════════════════════
        # 测试事件3：超长标题（测试省略）- 10分钟前
        # 使用角色：老李头(1019) - 城郊老农，负责看守粮仓
        # ═══════════════════════════════════════════════════════════════════════
        test_news_3 = LiveNewsItem(
            id="test_event_003",
            title="【紧急】无更市粮仓突发大火，火势蔓延至周边商铺，百姓哭喊求救，情况万分危急！",
            subtitle="老李头呼救，火势凶猛",
            category=NewsCategory.SOCIAL,
            actor_ids=[1019],  # 老李头
            actor_names=["老李头"],
            location="无更市粮仓",
            story_choices=[{"text": "组织救火", "effect": "FAME:+50"}],
            priority=5,  # 最高优先级
            tags=["火灾", "紧急"],
            comments=[
                {"user": "鲁智深", "text": "阿弥陀佛，老衲这就去救火救人！", "type": "支持"},
                {"user": "钱掌柜", "text": "我的货啊！全在粮仓里！", "type": "反对"},
                {"user": "阿禅", "text": "火势凶猛，需从长计议", "type": "中立"},
                {"user": "铁牛", "text": "俺来帮忙！水桶在哪？", "type": "支持"},
            ],
            heat_score=99999,
            image_url="placeholder"
        )
        test_news_3.setup_ui_choices(level=1)
        test_news_3.is_resolved = False  # 未解决，显示在"当前"tab
        test_news_3.read = False
        test_news_3.created_at = base_time - 10 * 60  # 10分钟前
        
        # 【添加对话扩写】测试事件3：粮仓大火
        test_news_3._pregen_script = EventScriptFull(
            intro_dialogs=[
                EventDialogLine('NARRATOR', '粮仓方向浓烟滚滚，火光冲天！', ''),
                EventDialogLine('SELF', '救火啊！快来人救火啊！粮仓要烧没了！', 'SET_EMOTION:老李头:SCARED'),
                EventDialogLine('NARRATOR', '老李头浑身是灰，拼命呼救。', ''),
                EventDialogLine('OTHER', '我的货！我的货还在里面！', 'SET_EMOTION:钱掌柜:PANIC'),
                EventDialogLine('NARRATOR', '火势凶猛，热浪逼人，百姓们惊慌失措。', 'SHAKE_CAMERA:5;FLASH_WHITE:150'),
                EventDialogLine('SELF', '求求各位，帮忙救火啊！这是全城的粮食啊！', ''),
                EventDialogLine('NARRATOR', '如果再不行动，整个粮仓都将化为灰烬。你，会怎么做？', 'SHOW_EVENT_CHOICE')
            ],
            choice_a_dialogs=[
                EventDialogLine('PLAYER', '大家跟我来！用水桶、用衣服，能救多少是多少！', ''),
                EventDialogLine('SELF', '多谢恩公！多谢各位！', 'SET_EMOTION:老李头:HAPPY'),
                EventDialogLine('OTHER', '我的货...我的货保住了！多谢大侠！', 'SET_EMOTION:钱掌柜:RELIEVED'),
                EventDialogLine('NARRATOR', '在你的带领下，众人齐心协力，终于将大火扑灭。', 'SHAKE_CAMERA:3'),
                EventDialogLine('NARRATOR', '虽然损失了一部分粮食，但大部分都保住了。', 'PLAYER_FAME:+50;SET_AFFINITY:老李头:+40')
            ],
            choice_b_dialogs=[
                EventDialogLine('PLAYER', '（组织附近百姓撤离，防止火势蔓延）', ''),
                EventDialogLine('NARRATOR', '你指挥百姓远离火场，设立隔离带。', ''),
                EventDialogLine('SELF', '完了...全完了...', 'SET_EMOTION:老李头:SAD'),
                EventDialogLine('NARRATOR', '最终粮仓被烧毁，但至少没有人员伤亡。', ''),
                EventDialogLine('NARRATOR', '你尽力了，但火势太大，无力回天。', 'PLAYER_FAME:+10')
            ],
            choice_c_dialogs=[
                EventDialogLine('PLAYER', '（远远观望，不靠近火场）', ''),
                EventDialogLine('NARRATOR', '火势越来越大，浓烟遮蔽了半边天。', ''),
                EventDialogLine('SELF', '救命啊...谁来帮帮我...', ''),
                EventDialogLine('NARRATOR', '你选择了保全自己，粮仓最终被完全烧毁。', ''),
                EventDialogLine('NARRATOR', '这件事很快传遍了无更市，人们议论纷纷。', 'PLAYER_FAME:-10')
            ]
        )
        
        # ═══════════════════════════════════════════════════════════════════════
        # 测试事件4：无当事人（系统事件）- 5分钟前（最新）
        # 使用角色：弥乐(1013) - 以算命为幌子的骗子和尚，可以解读天象
        # ═══════════════════════════════════════════════════════════════════════
        test_news_4 = LiveNewsItem(
            id="test_event_004",
            title="天降异象，红月当空",
            subtitle="算命和尚弥乐称此乃大凶之兆",
            category=NewsCategory.SUPERNATURAL,
            actor_ids=[1013],  # 弥乐
            actor_names=["弥乐"],
            location="无更市全城",
            story_choices=[{"text": "观测天象", "effect": "INTEL:+10"}],
            priority=2,
            tags=["天象", "异象"],
            comments=[
                {"user": "李师师", "text": "好可怕的红月，怕是要出大事了", "type": "反对"},
                {"user": "林冲", "text": "兵戈之兆，看来无更市不太平了", "type": "中立"},
                {"user": "袁桐", "text": "弥乐大师说得对，此乃不祥之兆", "type": "支持"},
                {"user": "阿禅", "text": "阿弥陀佛，愿众生平安", "type": "中立"},
            ],
            heat_score=5000,
            image_url="placeholder"
        )
        test_news_4.setup_ui_choices(level=1)
        test_news_4.is_resolved = False  # 未解决
        test_news_4.read = False
        test_news_4.created_at = base_time - 5 * 60  # 5分钟前（最新）
        
        # 【添加对话扩写】测试事件4：天降异象，红月当空
        test_news_4._pregen_script = EventScriptFull(
            intro_dialogs=[
                EventDialogLine('NARRATOR', '夜幕降临，一轮血红的月亮悄然升起。', ''),
                EventDialogLine('NARRATOR', '街市上的人们纷纷驻足，仰望这诡异的天象。', ''),
                EventDialogLine('SELF', '阿弥陀佛...此乃大凶之兆啊！', ''),
                EventDialogLine('OTHER', '弥乐大师，这红月预示着什么？', ''),
                EventDialogLine('SELF', '血光之灾，兵戈之祸...无更市将有大难！', 'SET_EMOTION:弥乐:WORRIED'),
                EventDialogLine('NARRATOR', '弥乐神色凝重，手指掐算。', ''),
                EventDialogLine('SELF', '老衲观天象，三日之内，必有大事发生...', ''),
                EventDialogLine('NARRATOR', '围观百姓议论纷纷。你，会怎么做？', 'SHOW_EVENT_CHOICE')
            ],
            choice_a_dialogs=[
                EventDialogLine('PLAYER', '大师可否详细说说，如何能化解此劫？', ''),
                EventDialogLine('SELF', '施主有心了...此劫乃天降，非人力可逆。', ''),
                EventDialogLine('SELF', '唯有积德行善，或可减轻灾祸...', ''),
                EventDialogLine('PLAYER', '多谢大师指点，我定当谨记。', ''),
                EventDialogLine('NARRATOR', '弥乐为你细细解读天象，你获得了一些情报。', 'INTEL:+10;SET_AFFINITY:弥乐:+20')
            ],
            choice_b_dialogs=[
                EventDialogLine('PLAYER', '装神弄鬼，不过是骗钱的把戏！', ''),
                EventDialogLine('SELF', '施主不信，老衲也不强求...只是这灾祸，唉...', 'SET_EMOTION:弥乐:SAD'),
                EventDialogLine('OTHER', '就是！什么大凶之兆，我看就是瞎说！', ''),
                EventDialogLine('NARRATOR', '你拂袖而去，但红月依旧挂在天上，心中隐隐不安。', 'PLAYER_FAME:+5')
            ],
            choice_c_dialogs=[
                EventDialogLine('PLAYER', '（默默观察，不置可否）', ''),
                EventDialogLine('NARRATOR', '你静静看着红月，心中若有所思。', ''),
                EventDialogLine('SELF', '天意难测，各人有各人的造化...', ''),
                EventDialogLine('NARRATOR', '你选择了沉默，让时间来验证一切。', '')
            ]
        )
        
        # 添加到通知管理器
        mgr = get_notification_manager()
        mgr.add_event(test_news_1)
        mgr.add_event(test_news_2)
        mgr.add_event(test_news_3)
        mgr.add_event(test_news_4)
        
        print(f"[LiveNewsPanel] 已添加 {4} 个调试测试事件")
        
    def _get_font(self, size: int) -> pygame.font.Font:
        """获取缓存字体"""
        if size not in self._font_cache:
            self._font_cache[size] = pygame.font.SysFont(
                "microsoftyahei,simhei,pingfangsc,arial", size
            )
        return self._font_cache[size]
    
    def show(self):
        """显示面板"""
        self.visible = True
        self.target_progress = 1.0
        self.scroll_offset = 0
        print("[LiveNewsPanel] 打开大宋实况面板")
    
    def hide(self):
        """隐藏面板"""
        self.target_progress = 0.0
        print("[LiveNewsPanel] 关闭大宋实况面板")
    
    def toggle(self):
        """切换显示状态"""
        if self.visible and self.open_progress > 0.5:
            self.hide()
        else:
            self.show()
    
    def is_open(self) -> bool:
        """是否正在显示"""
        return self.visible and self.open_progress > 0.1
    
    def update(self, dt_ms: int):
        """更新动画"""
        # 开关动画
        speed = dt_ms / 200.0  # 200ms完成动画
        if self.open_progress < self.target_progress:
            self.open_progress = min(self.target_progress, self.open_progress + speed)
        elif self.open_progress > self.target_progress:
            self.open_progress = max(self.target_progress, self.open_progress - speed)
            if self.open_progress <= 0:
                self.visible = False
    
    def _get_items(self) -> List[LiveNewsItem]:
        """获取当前标签页的事件列表
        
        当前tab: 未处理的事件 (is_resolved=False)
        历史tab: 已处理的事件 (is_resolved=True)
        
        按 created_at 时间倒序排列（最新的在前）
        """
        mgr = get_notification_manager()
        # 获取所有历史事件，按时间倒序排列
        all_events = sorted(
            mgr.get_history(),
            key=lambda e: e.created_at,
            reverse=True  # 最新的在前
        )
        
        if self.current_tab == NewsTab.CURRENT:
            # 当前tab: 未处理的事件
            return [e for e in all_events if not e.is_resolved]
        else:
            # 历史tab: 已处理的事件
            return [e for e in all_events if e.is_resolved]
    
    def _get_content_rect(self) -> pygame.Rect:
        """获取内容区域"""
        x = self.panel_x + self.PADDING
        y = self.panel_y + self.HEADER_HEIGHT + self.TAB_HEIGHT + 10
        w = self.PANEL_WIDTH - self.PADDING * 2 - self.SCROLL_WIDTH - 4
        h = self.PANEL_HEIGHT - self.HEADER_HEIGHT - self.TAB_HEIGHT - 30
        return pygame.Rect(x, y, w, h)
    
    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        处理事件
        
        Returns:
            是否消费了事件
        """
        if not self.visible or self.open_progress < 0.5:
            return False
        
        panel_rect = pygame.Rect(
            self.panel_x, self.panel_y, 
            self.PANEL_WIDTH, self.PANEL_HEIGHT
        )
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            
            # 点击面板外关闭
            if not panel_rect.collidepoint(mx, my):
                self.hide()
                return True
            
            # 点击关闭按钮
            close_rect = pygame.Rect(
                self.panel_x + self.PANEL_WIDTH - 40,
                self.panel_y + 10,
                30, 30
            )
            if close_rect.collidepoint(mx, my):
                self.hide()
                return True
            
            # 点击标签页
            tab_y = self.panel_y + self.HEADER_HEIGHT
            for i, tab in enumerate(NewsTab):
                tab_rect = pygame.Rect(
                    self.panel_x + 10 + i * 90,
                    tab_y,
                    80, self.TAB_HEIGHT - 4
                )
                if tab_rect.collidepoint(mx, my):
                    if self.current_tab != tab:
                        self.current_tab = tab
                        self.scroll_offset = 0
                    return True
            
            # 滚动条拖拽
            scroll_rect = self._get_scroll_rect()
            if scroll_rect and scroll_rect.collidepoint(mx, my):
                self.is_scrolling = True
                self.scroll_drag_start_y = my
                self.scroll_drag_start_offset = self.scroll_offset
                return True
            
            # 点击事件项
            content_rect = self._get_content_rect()
            if content_rect.collidepoint(mx, my):
                items = self._get_items()
                for i, item in enumerate(items):
                    item_y = content_rect.y + i * (self.ITEM_HEIGHT + self.ITEM_MARGIN) - self.scroll_offset
                    if item_y > content_rect.y - self.ITEM_HEIGHT and item_y < content_rect.bottom:
                        item_rect = pygame.Rect(
                            content_rect.x, item_y,
                            content_rect.width, self.ITEM_HEIGHT
                        )
                        if item_rect.collidepoint(mx, my):
                            self._on_item_click(item)
                            return True
            
            return True  # 点击面板内都消费事件
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if self.is_scrolling:
                self.is_scrolling = False
                return True
        
        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            
            # 拖拽滚动条
            if self.is_scrolling:
                delta_y = my - self.scroll_drag_start_y
                content_rect = self._get_content_rect()
                items = self._get_items()
                total_height = len(items) * (self.ITEM_HEIGHT + self.ITEM_MARGIN)
                if total_height > content_rect.height:
                    scroll_range = content_rect.height - 40  # 滚动条滑块区域
                    scroll_ratio = delta_y / scroll_range
                    new_offset = self.scroll_drag_start_offset + scroll_ratio * (total_height - content_rect.height)
                    self.scroll_offset = max(0, min(new_offset, total_height - content_rect.height))
                return True
            
            # 悬停检测
            content_rect = self._get_content_rect()
            self.hovered_item_index = -1
            if content_rect.collidepoint(mx, my):
                items = self._get_items()
                for i, item in enumerate(items):
                    item_y = content_rect.y + i * (self.ITEM_HEIGHT + self.ITEM_MARGIN) - self.scroll_offset
                    if item_y > content_rect.y - self.ITEM_HEIGHT and item_y < content_rect.bottom:
                        item_rect = pygame.Rect(
                            content_rect.x, item_y,
                            content_rect.width, self.ITEM_HEIGHT
                        )
                        if item_rect.collidepoint(mx, my):
                            self.hovered_item_index = i
                            break
        
        elif event.type == pygame.MOUSEWHEEL:
            if panel_rect.collidepoint(pygame.mouse.get_pos()):
                # 滚轮滚动
                content_rect = self._get_content_rect()
                items = self._get_items()
                total_height = len(items) * (self.ITEM_HEIGHT + self.ITEM_MARGIN)
                if total_height > content_rect.height:
                    self.scroll_offset -= event.y * 40
                    self.scroll_offset = max(0, min(self.scroll_offset, total_height - content_rect.height))
                return True
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.hide()
                return True
        
        return False
    
    def _get_scroll_rect(self) -> Optional[pygame.Rect]:
        """获取滚动条区域"""
        content_rect = self._get_content_rect()
        items = self._get_items()
        total_height = len(items) * (self.ITEM_HEIGHT + self.ITEM_MARGIN)
        
        if total_height <= content_rect.height:
            return None
        
        # 滚动条轨道
        track_x = content_rect.right + 4
        track_y = content_rect.y
        track_h = content_rect.height
        
        # 滑块大小和位置
        thumb_ratio = content_rect.height / total_height
        thumb_h = max(30, int(track_h * thumb_ratio))
        scroll_range = total_height - content_rect.height
        thumb_y = track_y + int((self.scroll_offset / scroll_range) * (track_h - thumb_h)) if scroll_range > 0 else track_y
        
        return pygame.Rect(track_x, thumb_y, self.SCROLL_WIDTH, thumb_h)
    
    def _on_item_click(self, item: LiveNewsItem):
        """点击事件项"""
        print(f"[LiveNewsPanel] 点击事件: {item.title}")
        print(f"[LiveNewsPanel] snapshot_data 存在: {item.snapshot_data is not None}")
        if item.snapshot_data:
            print(f"[LiveNewsPanel] snapshot_data.title: {getattr(item.snapshot_data, 'title', 'N/A')}")
            print(f"[LiveNewsPanel] snapshot_data.choices: {getattr(item.snapshot_data, 'choices', [])}")
        else:
            print(f"[LiveNewsPanel] [!] 事件没有 snapshot_data！检查 Director 是否正确设置")
            print(f"[LiveNewsPanel] item 属性: id={item.id}, title={item.title}")
            print(f"[LiveNewsPanel] item.headline={item.headline}, item.description={item.description}")
        item.read = True
        if self.on_item_click:
            self.on_item_click(item)
    
    def draw(self, screen: pygame.Surface):
        """绘制面板"""
        if not self.visible or self.open_progress <= 0:
            return
        
        # 应用动画缩放
        scale = self._ease_out_back(self.open_progress)
        alpha = int(255 * self.open_progress)
        
        # 创建面板surface
        panel_surf = pygame.Surface((self.PANEL_WIDTH, self.PANEL_HEIGHT), pygame.SRCALPHA)
        
        # 背景
        pygame.draw.rect(panel_surf, self.COLOR_BG, 
                         (0, 0, self.PANEL_WIDTH, self.PANEL_HEIGHT), 
                         border_radius=12)
        pygame.draw.rect(panel_surf, self.COLOR_BORDER, 
                         (0, 0, self.PANEL_WIDTH, self.PANEL_HEIGHT), 
                         2, border_radius=12)
        
        # 头部
        self._draw_header(panel_surf)
        
        # 标签页
        self._draw_tabs(panel_surf)
        
        # 内容区域
        self._draw_content(panel_surf)
        
        # 绘制到屏幕（带缩放动画）
        if scale < 1.0:
            scaled_w = int(self.PANEL_WIDTH * scale)
            scaled_h = int(self.PANEL_HEIGHT * scale)
            scaled_surf = pygame.transform.smoothscale(panel_surf, (scaled_w, scaled_h))
            x = self.panel_x + (self.PANEL_WIDTH - scaled_w) // 2
            y = self.panel_y + (self.PANEL_HEIGHT - scaled_h) // 2
            screen.blit(scaled_surf, (x, y))
        else:
            screen.blit(panel_surf, (self.panel_x, self.panel_y))
    
    def _draw_header(self, surf: pygame.Surface):
        """绘制头部"""
        # 头部背景
        pygame.draw.rect(surf, self.COLOR_HEADER,
                         (0, 0, self.PANEL_WIDTH, self.HEADER_HEIGHT),
                         border_top_left_radius=12, border_top_right_radius=12)
        
        # 标题
        font_title = self._get_font(20)
        title_surf = font_title.render("[报] 大宋实况", True, self.COLOR_TEXT)
        surf.blit(title_surf, (self.PADDING, (self.HEADER_HEIGHT - title_surf.get_height()) // 2))
        
        # 统计信息
        mgr = get_notification_manager()
        unread = mgr.get_unread_count()
        total_history = mgr.get_history_count()
        
        font_stat = self._get_font(12)
        stat_text = f"未读 {unread} | 历史 {total_history} 条"
        stat_surf = font_stat.render(stat_text, True, self.COLOR_TEXT_DIM)
        surf.blit(stat_surf, (self.PANEL_WIDTH - stat_surf.get_width() - 50, 
                              (self.HEADER_HEIGHT - stat_surf.get_height()) // 2))
        
        # 关闭按钮
        close_font = self._get_font(18)
        close_surf = close_font.render("X", True, self.COLOR_TEXT_DIM)
        surf.blit(close_surf, (self.PANEL_WIDTH - 32, 14))
    
    def _draw_tabs(self, surf: pygame.Surface):
        """绘制标签页"""
        tab_y = self.HEADER_HEIGHT + 4
        font_tab = self._get_font(14)
        
        # 只从历史记录获取（与 _get_items 逻辑一致，避免重复）
        mgr = get_notification_manager()
        all_events = mgr.get_history()
        
        for i, tab in enumerate(NewsTab):
            x = 10 + i * 90
            is_active = (tab == self.current_tab)
            
            # 标签背景
            color = self.COLOR_TAB_ACTIVE if is_active else self.COLOR_TAB_INACTIVE
            pygame.draw.rect(surf, color, (x, tab_y, 80, self.TAB_HEIGHT - 8), border_radius=6)
            
            # 标签文字
            text_color = self.COLOR_TEXT if is_active else self.COLOR_TEXT_DIM
            tab_text = tab.value
            
            # 根据 is_resolved 状态统计数量
            if tab == NewsTab.CURRENT:
                count = len([e for e in all_events if not e.is_resolved])
                if count > 0:
                    tab_text = f"{tab.value} ({count})"
            else:
                count = len([e for e in all_events if e.is_resolved])
                if count > 0:
                    tab_text = f"{tab.value} ({count})"
            
            text_surf = font_tab.render(tab_text, True, text_color)
            tx = x + (80 - text_surf.get_width()) // 2
            ty = tab_y + (self.TAB_HEIGHT - 8 - text_surf.get_height()) // 2
            surf.blit(text_surf, (tx, ty))
    
    def _draw_content(self, surf: pygame.Surface):
        """绘制内容区域"""
        items = self._get_items()
        content_rect = pygame.Rect(
            self.PADDING,
            self.HEADER_HEIGHT + self.TAB_HEIGHT + 10,
            self.PANEL_WIDTH - self.PADDING * 2 - self.SCROLL_WIDTH - 4,
            self.PANEL_HEIGHT - self.HEADER_HEIGHT - self.TAB_HEIGHT - 30
        )
        
        # 空状态
        if not items:
            font = self._get_font(14)
            empty_text = "暂无事件" if self.current_tab == NewsTab.CURRENT else "暂无历史记录"
            text_surf = font.render(empty_text, True, self.COLOR_TEXT_MUTED)
            surf.blit(text_surf, (
                content_rect.x + (content_rect.width - text_surf.get_width()) // 2,
                content_rect.y + 50
            ))
            return
        
        # 计算总高度
        total_height = len(items) * (self.ITEM_HEIGHT + self.ITEM_MARGIN)
        self.max_scroll = max(0, total_height - content_rect.height)
        
        # 创建裁剪区域
        content_surf = pygame.Surface((content_rect.width, content_rect.height), pygame.SRCALPHA)
        
        # 绘制每个事件项
        for i, item in enumerate(items):
            item_y = i * (self.ITEM_HEIGHT + self.ITEM_MARGIN) - self.scroll_offset
            
            # 跳过不可见项
            if item_y < -self.ITEM_HEIGHT or item_y > content_rect.height:
                continue
            
            is_hover = (i == self.hovered_item_index)
            self._draw_item(content_surf, item, 0, item_y, content_rect.width, is_hover)
        
        surf.blit(content_surf, content_rect.topleft)
        
        # 绘制滚动条
        if total_height > content_rect.height:
            self._draw_scrollbar(surf, content_rect, total_height)
    
    def _draw_item(self, surf: pygame.Surface, item: LiveNewsItem, 
                   x: int, y: int, width: int, is_hover: bool):
        """绘制单个事件项 - 复用与通知栏相同的布局"""
        # 使用共享的 draw_event_card 函数，保持UI一致性
        # 复用通知管理器的头像缓存
        mgr = get_notification_manager()
        
        draw_event_card(
            surface=surf,
            notif=item,
            x=x,
            y=y,
            width=width,
            height=self.ITEM_HEIGHT,
            font_cache=self._font_cache,
            avatar_cache=mgr._avatar_cache,  # 复用通知管理器的头像缓存
            is_hover=is_hover,
            is_unread=not item.read,
            show_border=True
        )
        
        # 额外绘制：已解决标记（在右上角）
        if item.is_resolved:
            font_small = self._get_font(10)
            resolved_surf = font_small.render("✓", True, (100, 200, 150))
            surf.blit(resolved_surf, (x + width - 20, y + 6))
    
    def _draw_scrollbar(self, surf: pygame.Surface, content_rect: pygame.Rect, total_height: float):
        """绘制滚动条"""
        track_x = content_rect.x + content_rect.width + 4
        track_y = content_rect.y
        track_h = content_rect.height
        
        # 轨道
        pygame.draw.rect(surf, self.COLOR_SCROLL, 
                         (track_x, track_y, self.SCROLL_WIDTH, track_h), 
                         border_radius=4)
        
        # 滑块
        thumb_ratio = content_rect.height / total_height
        thumb_h = max(30, int(track_h * thumb_ratio))
        scroll_range = total_height - content_rect.height
        thumb_y = track_y + int((self.scroll_offset / scroll_range) * (track_h - thumb_h)) if scroll_range > 0 else track_y
        
        thumb_color = self.COLOR_SCROLL_THUMB if not self.is_scrolling else (150, 145, 180)
        pygame.draw.rect(surf, thumb_color, 
                         (track_x, thumb_y, self.SCROLL_WIDTH, thumb_h), 
                         border_radius=4)
    
    def _draw_actor_avatar(self, surf: pygame.Surface, actor_name: str, x: int, y: int, size: int = 36):
        """绘制角色头像"""
        
        # 头像路径（唯一路径）
        avatar_path = PyPath(resource_path(f"assets/head_icon/{actor_name}.png"))
        
        # 尝试加载头像
        avatar_surface = None
        if avatar_path.exists():
            try:
                avatar_surface = pygame.image.load(str(avatar_path))
                avatar_surface = pygame.transform.smoothscale(avatar_surface, (size, size))
            except:
                pass
        
        # 绘制圆形裁剪区域
        circle_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.ellipse(circle_surf, (255, 255, 255), (0, 0, size, size))
        
        if avatar_surface:
            # 使用头像
            avatar_surface.blit(circle_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(avatar_surface, (x, y))
        else:
            # 使用默认头像（名字首字）
            pygame.draw.ellipse(surf, (80, 80, 100), (x, y, size, size))
            font = self._get_font(size // 2)
            initial = actor_name[0] if actor_name else "?"
            text_surf = font.render(initial, True, (200, 200, 220))
            text_x = x + (size - text_surf.get_width()) // 2
            text_y = y + (size - text_surf.get_height()) // 2
            surf.blit(text_surf, (text_x, text_y))
        
        # 绘制边框
        pygame.draw.ellipse(surf, (120, 120, 140), (x, y, size, size), 2)
    
    def _ease_out_back(self, t: float) -> float:
        """弹性缓出动画"""
        c1 = 1.70158
        c3 = c1 + 1
        return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)


# ═══════════════════════════════════════════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════════════════════════════════════════

_live_news_panel: Optional[LiveNewsPanel] = None

def get_live_news_panel(screen_w: int = 0, screen_h: int = 0) -> LiveNewsPanel:
    """获取全局大宋实况面板"""
    global _live_news_panel
    if _live_news_panel is None:
        if screen_w == 0 or screen_h == 0:
            try:
                screen_w, screen_h = pygame.display.get_surface().get_size()
            except:
                screen_w, screen_h = 1280, 720
        _live_news_panel = LiveNewsPanel(screen_w, screen_h)
    return _live_news_panel


def toggle_live_news_panel():
    """切换大宋实况面板显示"""
    panel = get_live_news_panel()
    panel.toggle()
