"""
命运图谱界面 (FateGraphUI)

展示所有NPC的人生困境轨迹，以时间轴方式呈现每个NPC的起承转合。
参考 fate.md 的交互设计，每个命运节点对接 story_director.py 中的 NPC 困境。
"""

import pygame
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.definitions import *
from src.ui.base import UIBase


class NodeType(Enum):
    """命运节点类型"""
    PAST_DECIDED = "past"       # □ 过去已决定的节点
    CURRENT_INTERVENABLE = "current"  # ■ 当前可介入的节点
    PLAYER_INTERVENED = "player"      # 🎮 玩家介入了此节点
    NPC_NATURAL = "npc"               # ⚙ NPC自己选的（自然发展）


@dataclass
class FateNode:
    """命运节点 - 对应一个困境事件"""
    npc_id: str
    npc_name: str
    npc_job: str
    npc_avatar: Optional[pygame.Surface] = None
    
    # 困境信息
    dilemma_title: str = ""           # 困境标题
    dilemma_desc: str = ""            # 困境描述
    phase: str = "EMERGE"             # 阶段: EMERGE/ESCALATE/CLIMAX/SETTLE
    
    # 时间信息
    game_day: int = 1                 # 游戏内天数
    game_season: str = "春"           # 季节
    game_year: int = 1                # 年份
    
    # 选择信息
    player_choice: Optional[str] = None   # 玩家选择（如果有）
    alternative_choices: List[str] = None # 未选择的其他选项
    
    # 结果
    consequence: str = ""             # 后果描述
    
    # 节点状态
    node_type: NodeType = NodeType.PAST_DECIDED
    is_intervenable: bool = False     # 是否可介入
    
    def __post_init__(self):
        if self.alternative_choices is None:
            self.alternative_choices = []


@dataclass
class NPCTimeline:
    """NPC的命运时间线"""
    npc_id: str
    npc_name: str
    npc_job: str
    npc_avatar: Optional[pygame.Surface] = None
    nodes: List[FateNode] = None
    current_phase: str = "EMERGE"
    heat: float = 0.0
    
    def __post_init__(self):
        if self.nodes is None:
            self.nodes = []


class FateGraphUI:
    """
    命运图谱界面
    
    布局参考 fate.md:
    - 顶部标题栏（显示当前游戏时间）
    - 时间轴（横向，显示年份和季节）
    - NPC命运线（纵向排列，每条线展示该NPC的起承转合）
    - 图例说明
    """
    
    def __init__(self, screen_w: int, screen_h: int):
        self.screen_w = screen_w
        self.screen_h = screen_h
        
        # 面板尺寸
        self.panel_w = int(screen_w * 0.9)
        self.panel_h = int(screen_h * 0.85)
        self.panel_x = (screen_w - self.panel_w) // 2
        self.panel_y = (screen_h - self.panel_h) // 2
        
        # 颜色配置
        self.colors = {
            'bg': (25, 28, 35),
            'panel_bg': (35, 38, 45),
            'border': (100, 90, 70),
            'title': (255, 215, 0),
            'timeline': (80, 80, 90),
            'text': (220, 220, 220),
            'text_dim': (150, 150, 150),
            'node_past': (120, 120, 130),      # 过去节点
            'node_current': (255, 100, 100),   # 当前可介入
            'node_player': (100, 200, 255),    # 玩家介入
            'node_npc': (150, 150, 100),       # NPC自然选择
            'line_real': (180, 160, 120),      # 真实路径
            'line_alt': (80, 80, 90),          # 未选择路径（虚线）
            'heat_high': (255, 100, 100),      # 高热度
            'heat_med': (255, 200, 100),       # 中热度
            'heat_low': (100, 200, 100),       # 低热度
        }
        
        # 布局参数
        self.header_h = 50
        self.timeline_h = 40
        self.legend_h = 80
        self.npc_row_h = 100
        self.node_size = 16
        self.avatar_size = 40
        
        # 时间轴参数
        self.timeline_start_x = 150  # 左侧留空给NPC信息
        self.timeline_y = self.panel_y + self.header_h + 30
        
        # 数据
        self.timelines: List[NPCTimeline] = []
        self.selected_node: Optional[FateNode] = None
        self.scroll_offset = 0
        self.max_scroll = 0
        
        # 字体（后续在draw时传入）
        self.font_big = None
        self.font_ui = None
        self.font_small = None
        
        # 动画
        self.hover_node: Optional[FateNode] = None
        self.hover_timeline: Optional[NPCTimeline] = None
        
        # 拖拽滚动
        self.is_dragging = False
        self.drag_start_y = 0
        self.drag_start_scroll = 0
        
    def set_fonts(self, font_big, font_ui, font_small):
        """设置字体"""
        self.font_big = font_big
        self.font_ui = font_ui
        self.font_small = font_small
        
    def _generate_test_data(self, current_day: int = 1):
        """生成测试数据，使用npc_data.csv中的真实NPC"""
        test_timelines = []
        
        # NPC 1: 鱼西施 (1008) - 卖鱼姑娘的命运线
        timeline1 = NPCTimeline(
            npc_id="1008",
            npc_name="鱼西施",
            npc_job="MERCHANT",
            current_phase="CLIMAX",
            heat=90.0
        )
        
        # 节点1: 高衙内逼婚 (过去，玩家介入)
        node1_1 = FateNode(
            npc_id="1008",
            npc_name="鱼西施",
            npc_job="MERCHANT",
            dilemma_title="高衙内逼婚",
            dilemma_desc="高衙内要强纳她为妾，威胁不从就让她无法在城中卖鱼",
            phase="EMERGE",
            game_day=30,
            game_season="春",
            game_year=1,
            player_choice="拒绝婚事",
            alternative_choices=["顺从高衙内"],
            consequence="与父亲决裂，独自在城东卖鱼为生",
            node_type=NodeType.PLAYER_INTERVENED
        )
        
        # 节点2: 泼皮抢鱼摊 (过去，玩家介入)
        node1_2 = FateNode(
            npc_id="1008",
            npc_name="鱼西施",
            npc_job="MERCHANT",
            dilemma_title="泼皮抢鱼摊",
            dilemma_desc="泼皮牛二带人来收保护费，要霸占她的鱼摊",
            phase="ESCALATE",
            game_day=200,
            game_season="冬",
            game_year=1,
            player_choice="挺身而出",
            alternative_choices=["忍气吞声"],
            consequence="泼皮被赶走，但结下梁子",
            node_type=NodeType.PLAYER_INTERVENED
        )
        
        # 节点3: 黑风寨来人 (当前可介入)
        node1_3 = FateNode(
            npc_id="1008",
            npc_name="鱼西施",
            npc_job="MERCHANT",
            dilemma_title="黑风寨来人",
            dilemma_desc="黑风大王派人传话，要她上山做压寨夫人",
            phase="CLIMAX",
            game_day=current_day,
            game_season="秋",
            game_year=3,
            is_intervenable=True,
            node_type=NodeType.CURRENT_INTERVENABLE
        )
        
        timeline1.nodes = [node1_1, node1_2, node1_3]
        test_timelines.append(timeline1)
        
        # NPC 2: 泼皮牛二 (1026) - 反派也有命运
        timeline2 = NPCTimeline(
            npc_id="1026",
            npc_name="泼皮牛二",
            npc_job="BANDIT",
            current_phase="SETTLE",
            heat=70.0
        )
        
        # 节点1: 欠下赌债 (NPC自然选择)
        node2_1 = FateNode(
            npc_id="1026",
            npc_name="泼皮牛二",
            npc_job="BANDIT",
            dilemma_title="欠下赌债",
            dilemma_desc="赌钱输光了，欠了一屁股债",
            phase="EMERGE",
            game_day=60,
            game_season="夏",
            game_year=1,
            player_choice=None,
            alternative_choices=["金盆洗手"],
            consequence="投靠黑风大王，当起了泼皮",
            node_type=NodeType.NPC_NATURAL
        )
        
        # 节点2: 调戏鱼西施被教训 (玩家介入)
        node2_2 = FateNode(
            npc_id="1026",
            npc_name="泼皮牛二",
            npc_job="BANDIT",
            dilemma_title="调戏鱼西施被教训",
            dilemma_desc="调戏鱼西施时被玩家打败",
            phase="ESCALATE",
            game_day=200,
            game_season="冬",
            game_year=1,
            player_choice="放他一马",
            alternative_choices=["送官查办"],
            consequence="心存怨恨，伺机报复",
            node_type=NodeType.PLAYER_INTERVENED
        )
        
        # 节点3: 得罪高衙内 (NPC选择)
        node2_3 = FateNode(
            npc_id="1026",
            npc_name="泼皮牛二",
            npc_job="BANDIT",
            dilemma_title="得罪高衙内",
            dilemma_desc="喝多了酒，调戏了高府的丫鬟",
            phase="CLIMAX",
            game_day=400,
            game_season="春",
            game_year=2,
            player_choice=None,
            alternative_choices=["向高衙内求饶", "逃跑"],
            consequence="被高衙内追杀",
            node_type=NodeType.NPC_NATURAL
        )
        
        # 节点4: 当前状态
        node2_4 = FateNode(
            npc_id="1026",
            npc_name="泼皮牛二",
            npc_job="BANDIT",
            dilemma_title="黑风寨的庇护",
            dilemma_desc="黑风大王庇护他，但要求高衙内的人情",
            phase="SETTLE",
            game_day=current_day,
            game_season="秋",
            game_year=3,
            is_intervenable=True,
            node_type=NodeType.CURRENT_INTERVENABLE
        )
        
        timeline2.nodes = [node2_1, node2_2, node2_3, node2_4]
        test_timelines.append(timeline2)
        
        # NPC 3: 黑风大王 (1023) - 幕后BOSS
        timeline3 = NPCTimeline(
            npc_id="1023",
            npc_name="黑风大王",
            npc_job="BANDIT",
            current_phase="CLIMAX",
            heat=95.0
        )
        
        node3_1 = FateNode(
            npc_id="1023",
            npc_name="黑风大王",
            npc_job="BANDIT",
            dilemma_title="寨子缺粮",
            dilemma_desc="冬天寨子粮食不够，兄弟们要饿肚子",
            phase="EMERGE",
            game_day=100,
            game_season="冬",
            game_year=1,
            player_choice=None,
            alternative_choices=["下山抢粮", "紧缩度日"],
            consequence="派手下到镇上收保护费",
            node_type=NodeType.NPC_NATURAL
        )
        
        node3_2 = FateNode(
            npc_id="1023",
            npc_name="黑风大王",
            npc_job="BANDIT",
            dilemma_title="高衙内的命令",
            dilemma_desc="高衙内命令他绑架一位朝廷命官的家眷",
            phase="CLIMAX",
            game_day=current_day,
            game_season="秋",
            game_year=3,
            is_intervenable=True,
            node_type=NodeType.CURRENT_INTERVENABLE
        )
        
        timeline3.nodes = [node3_1, node3_2]
        test_timelines.append(timeline3)
        
        # NPC 4: 林冲 (1002) - 禁军教头（只有过去事件，没有当前可介入）
        timeline4 = NPCTimeline(
            npc_id="1002",
            npc_name="林冲",
            npc_job="GUARD",
            current_phase="SETTLE",
            heat=80.0
        )
        
        node4_1 = FateNode(
            npc_id="1002",
            npc_name="林冲",
            npc_job="GUARD",
            dilemma_title="发现主公秘密",
            dilemma_desc="发现方承意暗中打压政敌，手段并不光明",
            phase="EMERGE",
            game_day=120,
            game_season="春",
            game_year=1,
            player_choice=None,
            alternative_choices=["向主公进谏", "装作不知"],
            consequence="内心挣扎，继续效忠",
            node_type=NodeType.NPC_NATURAL
        )
        
        node4_2 = FateNode(
            npc_id="1002",
            npc_name="林冲",
            npc_job="GUARD",
            dilemma_title="忠义的抉择",
            dilemma_desc="方承意命令他做违背良心的事",
            phase="ESCALATE",
            game_day=350,
            game_season="夏",
            game_year=2,
            player_choice="婉拒执行",
            alternative_choices=["违心执行", "直言进谏"],
            consequence="主公对他产生嫌隙",
            node_type=NodeType.PLAYER_INTERVENED
        )
        
        timeline4.nodes = [node4_1, node4_2]
        test_timelines.append(timeline4)
        
        # NPC 5: 鲁智深 (1013) - 花和尚（只有过去事件）
        timeline5 = NPCTimeline(
            npc_id="1013",
            npc_name="鲁智深",
            npc_job="MONK",
            current_phase="SETTLE",
            heat=75.0
        )
        
        node5_1 = FateNode(
            npc_id="1013",
            npc_name="鲁智深",
            npc_job="MONK",
            dilemma_title="醉酒打人",
            dilemma_desc="因醉酒打伤了寺中僧人，方丈要罚他禁闭",
            phase="EMERGE",
            game_day=80,
            game_season="夏",
            game_year=1,
            player_choice=None,
            alternative_choices=["接受惩罚", "逃离寺院"],
            consequence="被罚禁闭思过",
            node_type=NodeType.NPC_NATURAL
        )
        
        node5_2 = FateNode(
            npc_id="1013",
            npc_name="鲁智深",
            npc_job="MONK",
            dilemma_title="救林冲",
            dilemma_desc="林冲被陷害充军，他出手相救",
            phase="CLIMAX",
            game_day=380,
            game_season="冬",
            game_year=2,
            player_choice="大闹野猪林",
            alternative_choices=["暗中护送", "不插手"],
            consequence="与官府结仇，被迫流亡",
            node_type=NodeType.PLAYER_INTERVENED
        )
        
        timeline5.nodes = [node5_1, node5_2]
        test_timelines.append(timeline5)
        
        # NPC 6-33: 添加所有其他NPC（来自npc_data.csv）
        all_other_npcs = [
            ("1000", "方承意", "OFFICIAL"),
            ("1001", "无情", "OFFICIAL"),
            ("1003", "高衙内", "FARMER"),
            ("1004", "高大胜", "GUARD"),
            ("1005", "张青", "FARMER"),
            ("1006", "郁芊芊", "MERCHANT"),
            ("1007", "孙二娘", "MERCHANT"),
            ("1009", "王小乐", "MERCHANT"),
            ("1010", "李师师", "ARTISAN"),
            ("1011", "袁桐", "SCHOLAR"),
            ("1012", "孙小溪", "SCHOLAR"),
            ("1014", "弥乐", "SCHOLAR"),
            ("1015", "阿禅", "SCHOLAR"),
            ("1016", "洪小六", "THUG"),
            ("1017", "猎户张三", "THUG"),
            ("1018", "赵师爷", "OFFICIAL"),
            ("1019", "铁牛", "GUARD"),
            ("1020", "钱掌柜", "MERCHANT"),
            ("1021", "老李头", "FARMER"),
            ("1022", "小翠", "ARTISAN"),
            ("1024", "山贼甲", "BANDIT"),
            ("1025", "山贼乙", "BANDIT"),
            ("1027", "泼皮狗蛋", "BANDIT"),
            ("1028", "青狼", "BANDIT"),
            ("1029", "铁塔", "BANDIT"),
            ("1030", "瘦猴", "BANDIT"),
            ("1031", "骆大", "BANDIT"),
            ("1032", "骆二", "BANDIT"),
        ]
        
        for npc_id, name, job in all_other_npcs:
            timeline = NPCTimeline(
                npc_id=npc_id,
                npc_name=name,
                npc_job=job,
                current_phase="EMERGE",
                heat=float(10 + hash(name) % 30)  # 随机热度 10-40
            )
            test_timelines.append(timeline)
        
        return test_timelines

    def load_data(self, story_director, all_npcs: List, current_day: int = 1):
        """
        从StoryDirector加载命运数据，显示所有NPC（包括没有困境的）
        
        Args:
            story_director: StoryDirector实例
            all_npcs: 所有NPC列表
            current_day: 当前游戏天数
        """
        self.timelines = []
        
        # 如果使用测试数据
        if DEBUG_FATE_GRAPH_TEST_DATA:
            self.timelines = self._generate_test_data(current_day)
            # 计算最大滚动
            content_h = len(self.timelines) * self.npc_row_h
            self.max_scroll = max(0, content_h - (self.panel_h - self.header_h - self.timeline_h - self.legend_h - 40))
            return
        
        # 过滤出所有NPC（排除玩家和资源卡）
        from src.entities import NPC
        npc_list = [npc for npc in all_npcs if isinstance(npc, NPC)]
            
        for npc in npc_list:
            if not hasattr(npc, 'id'):
                continue
                
            npc_id = npc.id
            
            # 创建时间线（无论是否有困境数据）
            timeline = NPCTimeline(
                npc_id=npc_id,
                npc_name=getattr(npc, 'name', 'Unknown'),
                npc_job=getattr(npc, 'job', 'NONE'),
                current_phase="EMERGE",
                heat=0.0
            )
            
            # 加载头像
            avatar_path = f"assets/head_icon/{timeline.npc_name}.png"
            try:
                timeline.npc_avatar = pygame.image.load(avatar_path)
                timeline.npc_avatar = pygame.transform.scale(
                    timeline.npc_avatar, (self.avatar_size, self.avatar_size)
                )
            except:
                timeline.npc_avatar = None
            
            # 如果有StoryDirector数据，加载困境信息
            if story_director:
                seed = story_director.seeds.get(npc_id)
                if seed:
                    timeline.current_phase = seed.phase.value if seed.phase else "EMERGE"
                    timeline.heat = seed.heat
                    
                    # 从story_beats创建节点
                    for i, beat in enumerate(seed.story_beats):
                        node = FateNode(
                            npc_id=npc_id,
                            npc_name=timeline.npc_name,
                            npc_job=timeline.npc_job,
                            npc_avatar=timeline.npc_avatar,
                            dilemma_title=beat.event_summary,
                            dilemma_desc=f"{beat.desire[:30] if beat.desire else ''}..." if beat.desire else beat.event_summary,
                            phase=beat.phase.value if beat.phase else "EMERGE",
                            game_day=i * 30 + 1,  # 估算天数
                            game_season=["春", "夏", "秋", "冬"][(i // 4) % 4],
                            game_year=1 + i // 4,
                            player_choice=beat.player_choice,
                            consequence=beat.consequence_summary,
                            node_type=NodeType.PLAYER_INTERVENED if beat.player_choice else NodeType.NPC_NATURAL
                        )
                        timeline.nodes.append(node)
                    
                    # 添加当前可介入节点（如果有pending_event）
                    if hasattr(seed, 'pending_event') and seed.pending_event:
                        pending = seed.pending_event
                        node = FateNode(
                            npc_id=npc_id,
                            npc_name=timeline.npc_name,
                            npc_job=timeline.npc_job,
                            npc_avatar=timeline.npc_avatar,
                            dilemma_title=pending.title,
                            dilemma_desc=pending.description[:50] + "..." if len(pending.description) > 50 else pending.description,
                            phase=seed.phase.value if seed.phase else "EMERGE",
                            game_day=current_day,
                            game_season=["春", "夏", "秋", "冬"][(current_day // 90) % 4],
                            game_year=1 + current_day // 360,
                            is_intervenable=True,
                            node_type=NodeType.CURRENT_INTERVENABLE
                        )
                        timeline.nodes.append(node)
            
            # 所有NPC都添加到时间线列表（即使没有节点）
            self.timelines.append(timeline)
        
        # 按热度排序（有困境的排在前面）
        self.timelines.sort(key=lambda t: (t.heat, len(t.nodes)), reverse=True)
        
        # 计算最大滚动
        content_h = len(self.timelines) * self.npc_row_h
        self.max_scroll = max(0, content_h - (self.panel_h - self.header_h - self.timeline_h - self.legend_h - 40))
        
    def handle_event(self, mx: int, my: int, click_event: bool, mouse_down: bool = False, 
                     mouse_up: bool = False, scroll_y: int = 0) -> Optional[str]:
        """
        处理鼠标事件（支持滚轮滚动和滚动条拖动）
        
        Args:
            mx, my: 鼠标坐标
            click_event: 是否有点击事件（MOUSEBUTTONDOWN）
            mouse_down: 鼠标是否按下（MOUSEBUTTONDOWN）
            mouse_up: 鼠标是否释放（MOUSEBUTTONUP）
            scroll_y: 鼠标滚轮滚动值（正数向上，负数向下）
        
        Returns:
            动作字符串或None
        """
        # 检查是否在面板内
        panel_rect = pygame.Rect(self.panel_x, self.panel_y, self.panel_w, self.panel_h)
        
        # 内容区域
        content_top = self.panel_y + self.header_h + self.timeline_h + 20
        content_left = self.panel_x + 20
        content_w = self.panel_w - 40
        content_h = self.panel_h - self.header_h - self.timeline_h - self.legend_h - 30
        
        content_area = pygame.Rect(content_left, content_top, content_w, content_h)
        
        # 计算是否需要滚动
        total_content_height = len(self.timelines) * self.npc_row_h
        can_scroll = total_content_height > content_h
        
        # 滚动条参数（与_draw_scrollbar保持一致）
        scrollbar_x = self.panel_x + self.panel_w - 20
        scrollbar_w = 8
        scrollbar_track_rect = pygame.Rect(scrollbar_x, content_top, scrollbar_w, content_h)
        
        # 滑块高度
        scrollbar_h = max(30, int(content_h * content_h / total_content_height)) if can_scroll else content_h
        scroll_track_h = content_h - scrollbar_h
        
        # 计算滑块位置
        if can_scroll and self.max_scroll > 0:
            visible_ratio = self.scroll_offset / self.max_scroll
            scrollbar_y = content_top + visible_ratio * scroll_track_h
        else:
            scrollbar_y = content_top
        scrollbar_rect = pygame.Rect(scrollbar_x, scrollbar_y, scrollbar_w, scrollbar_h)
        
        # 处理鼠标滚轮（在内容区域内）
        if scroll_y != 0 and content_area.collidepoint(mx, my) and can_scroll:
            # 翻转方向：y>0时向上滚动（减小scroll_offset）
            scroll_speed = 30  # 每次滚动30像素
            if scroll_y > 0:
                self.scroll_offset = max(0, self.scroll_offset - scroll_speed)
            else:
                self.scroll_offset = min(self.max_scroll, self.scroll_offset + scroll_speed)
            return None
        
        # 处理鼠标释放（结束拖拽）
        if mouse_up:
            was_dragging = self.is_dragging
            self.is_dragging = False
            # 如果之前在拖拽，不处理其他点击
            if was_dragging:
                return None
        
        # 处理滚动条拖动 - 检测点击滑块开始拖拽
        if can_scroll and mouse_down and scrollbar_rect.collidepoint(mx, my):
            self.is_dragging = True
            self.drag_start_y = my
            self.drag_start_scroll = self.scroll_offset
            return None
        
        # 处理点击轨道（跳转到该位置）
        if can_scroll and click_event and scrollbar_track_rect.collidepoint(mx, my) and not scrollbar_rect.collidepoint(mx, my):
            click_ratio = (my - content_top) / content_h
            self.scroll_offset = int(click_ratio * self.max_scroll)
            self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))
            return None
        
        # 处理拖动中 - 只要is_dragging为True就处理
        if self.is_dragging:
            if can_scroll and scroll_track_h > 0:
                drag_delta = my - self.drag_start_y
                scroll_ratio = drag_delta / scroll_track_h
                self.scroll_offset = self.drag_start_scroll + int(scroll_ratio * self.max_scroll)
                self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))
            return None
        
        # 处理内容区域拖拽滚动（点击空白处拖动）
        if mouse_down and content_area.collidepoint(mx, my):
            # 检查是否点击在节点上，如果不是则开始拖拽
            clicked_on_node = False
            test_timeline_y = content_top - self.scroll_offset
            for timeline in self.timelines:
                for node in timeline.nodes:
                    node_x = self._get_node_x(node)
                    node_y = test_timeline_y + self.npc_row_h // 2
                    node_rect = pygame.Rect(
                        node_x - self.node_size - 5,
                        node_y - self.node_size - 5,
                        self.node_size * 2 + 10,
                        self.node_size * 2 + 10
                    )
                    if node_rect.collidepoint(mx, my):
                        clicked_on_node = True
                        break
                if clicked_on_node:
                    break
                test_timeline_y += self.npc_row_h
            
            if not clicked_on_node and not scrollbar_rect.collidepoint(mx, my):
                self.is_dragging = True
                self.drag_start_y = my
                self.drag_start_scroll = self.scroll_offset
                return None
        
        if not panel_rect.collidepoint(mx, my):
            if click_event:
                return "CLOSE"
            return None
        
        # 检查关闭按钮
        close_rect = pygame.Rect(
            self.panel_x + self.panel_w - 40,
            self.panel_y + 10,
            30, 30
        )
        if close_rect.collidepoint(mx, my):
            if click_event:
                return "CLOSE"
        
        # 检查节点点击
        timeline_y = content_top - self.scroll_offset
        
        for timeline in self.timelines:
            row_rect = pygame.Rect(content_left, timeline_y, content_w, self.npc_row_h)
            
            if row_rect.collidepoint(mx, my):
                # 检查是否点击了某个节点
                for node in timeline.nodes:
                    node_x = self._get_node_x(node)
                    node_y = timeline_y + self.npc_row_h // 2
                    node_rect = pygame.Rect(
                        node_x - self.node_size,
                        node_y - self.node_size,
                        self.node_size * 2,
                        self.node_size * 2
                    )
                    
                    if node_rect.collidepoint(mx, my):
                        self.selected_node = node
                        if click_event:
                            if node.is_intervenable:
                                return f"INTERVENE:{node.npc_id}"
                            else:
                                return f"VIEW:{node.npc_id}"
                        break
            
            timeline_y += self.npc_row_h
        
        return None
    
    def _get_node_x(self, node: FateNode) -> int:
        """根据游戏时间计算节点的X坐标"""
        # 假设一年360天，每季90天
        total_days = (node.game_year - 1) * 360 + ["春", "夏", "秋", "冬"].index(node.game_season) * 90 + 1
        
        # 计算最大时间范围（根据所有节点）
        max_days = 360 * 3  # 默认3年
        for timeline in self.timelines:
            for n in timeline.nodes:
                days = (n.game_year - 1) * 360 + ["春", "夏", "秋", "冬"].index(n.game_season) * 90 + 1
                max_days = max(max_days, days)
        
        # 映射到时间轴
        timeline_w = self.panel_w - self.timeline_start_x - 40
        if max_days > 0:
            ratio = total_days / max_days
        else:
            ratio = 0
            
        return self.panel_x + self.timeline_start_x + int(ratio * timeline_w)
    
    def draw(self, screen: pygame.Surface, mx: int, my: int, game_time: Dict = None):
        """绘制命运图谱"""
        if not self.font_big:
            return
            
        # 半透明背景遮罩
        overlay = pygame.Surface((self.screen_w, self.screen_h))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))
        
        # 面板背景
        panel_rect = pygame.Rect(self.panel_x, self.panel_y, self.panel_w, self.panel_h)
        pygame.draw.rect(screen, self.colors['panel_bg'], panel_rect, border_radius=10)
        pygame.draw.rect(screen, self.colors['border'], panel_rect, 2, border_radius=10)
        
        # 标题栏
        self._draw_header(screen, game_time)
        
        # 时间轴
        self._draw_timeline(screen)
        
        # NPC命运线（带裁剪）
        self._draw_npc_lines(screen, mx, my)
        
        # 图例
        self._draw_legend(screen)
        
        # 关闭按钮
        self._draw_close_button(screen, mx, my)
        
        # 详情弹窗（如果有选中节点）
        if self.selected_node:
            self._draw_node_detail(screen, self.selected_node, mx, my)
    
    def _draw_header(self, screen: pygame.Surface, game_time: Dict):
        """绘制标题栏"""
        # 标题
        title = "🏘 枫溪小镇 · 命运图谱"
        title_surf = self.font_big.render(title, True, self.colors['title'])
        screen.blit(title_surf, (self.panel_x + 20, self.panel_y + 15))
        
        # 游戏时间
        if game_time:
            year = game_time.get('year', 1)
            season = game_time.get('season', '春')
            day = game_time.get('day', 1)
            time_str = f"第{year}年·{season} 第{day}天"
        else:
            time_str = "第1年·春"
        
        time_surf = self.font_ui.render(time_str, True, self.colors['text'])
        screen.blit(time_surf, (self.panel_x + self.panel_w - time_surf.get_width() - 60, self.panel_y + 20))
    
    def _draw_timeline(self, screen: pygame.Surface):
        """绘制时间轴"""
        timeline_y = self.timeline_y
        
        # 时间轴线
        start_x = self.panel_x + self.timeline_start_x
        end_x = self.panel_x + self.panel_w - 40
        pygame.draw.line(screen, self.colors['timeline'], (start_x, timeline_y), (end_x, timeline_y), 2)
        
        # 年份标记
        years = [1, 2, 3]
        for year in years:
            x = start_x + (end_x - start_x) * (year - 1) // 3
            
            # 刻度
            pygame.draw.line(screen, self.colors['timeline'], (x, timeline_y - 5), (x, timeline_y + 5), 2)
            
            # 年份文字
            year_surf = self.font_small.render(f"{year}年", True, self.colors['text_dim'])
            screen.blit(year_surf, (x - year_surf.get_width() // 2, timeline_y - 20))
            
            # 季节标记
            seasons = ["春", "夏", "秋", "冬"]
            for i, season in enumerate(seasons):
                sx = x + (end_x - start_x) // 12 * i
                if year < 3 or i < 2:  # 不画超出边界的
                    season_surf = self.font_small.render(season, True, self.colors['text_dim'])
                    screen.blit(season_surf, (sx - season_surf.get_width() // 2, timeline_y + 8))
    
    def _draw_npc_lines(self, screen: pygame.Surface, mx: int, my: int):
        """绘制NPC命运线"""
        content_top = self.panel_y + self.header_h + self.timeline_h + 20
        content_left = self.panel_x + 20
        content_w = self.panel_w - 40
        
        # 创建裁剪区域
        clip_rect = pygame.Rect(content_left, content_top, content_w, 
                               self.panel_h - self.header_h - self.timeline_h - self.legend_h - 30)
        
        # 保存原裁剪区域
        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)
        
        timeline_y = content_top - self.scroll_offset
        
        for timeline in self.timelines:
            # 跳过完全不在可视区域的
            if timeline_y + self.npc_row_h < content_top or timeline_y > content_top + clip_rect.height:
                timeline_y += self.npc_row_h
                continue
            
            # 行背景（悬停高亮）
            row_rect = pygame.Rect(content_left, timeline_y, content_w, self.npc_row_h - 5)
            is_hover = row_rect.collidepoint(mx, my)
            if is_hover:
                pygame.draw.rect(screen, (45, 48, 55), row_rect, border_radius=4)
            
            # 分隔线
            pygame.draw.line(screen, self.colors['timeline'], 
                           (content_left + self.timeline_start_x - 20, timeline_y + self.npc_row_h - 5),
                           (content_left + content_w, timeline_y + self.npc_row_h - 5), 1)
            
            # NPC信息（左侧）
            self._draw_npc_info(screen, timeline, content_left + 10, timeline_y + 10)
            
            # 命运节点和连线
            self._draw_nodes_for_timeline(screen, timeline, timeline_y + self.npc_row_h // 2, mx, my)
            
            timeline_y += self.npc_row_h
        
        # 恢复裁剪区域
        screen.set_clip(old_clip)
        
        # 绘制滚动条（如果需要）
        if self.max_scroll > 0:
            self._draw_scrollbar(screen, content_top, clip_rect.height)
    
    def _draw_npc_info(self, screen: pygame.Surface, timeline: NPCTimeline, x: int, y: int):
        """绘制NPC基本信息（显示正确头像）"""
        # 加载头像（使用npc_data.csv中的head_img字段格式）
        avatar = None
        try:
            # 尝试加载头像，使用head_01.png或head_02.png格式
            import random
            head_img = f"head_0{random.randint(1, 2)}.png"  # 临时使用随机头像，实际应该从NPC数据中获取
            avatar_path = f"assets/head_icon/{head_img}"
            avatar = pygame.image.load(avatar_path)
            avatar = pygame.transform.scale(avatar, (self.avatar_size, self.avatar_size))
        except:
            # 如果加载失败，使用默认头像框
            avatar = None
        
        # 绘制头像
        if avatar:
            screen.blit(avatar, (x, y))
        else:
            # 默认头像框
            pygame.draw.rect(screen, (80, 80, 90), (x, y, self.avatar_size, self.avatar_size), border_radius=4)
            default_initials = timeline.npc_name[:1] if timeline.npc_name else "?"
            initial_surf = self.font_ui.render(default_initials, True, self.colors['text'])
            screen.blit(initial_surf, (x + self.avatar_size // 2 - initial_surf.get_width() // 2,
                                      y + self.avatar_size // 2 - initial_surf.get_height() // 2))
        
        # 名字
        name_surf = self.font_ui.render(timeline.npc_name, True, self.colors['text'])
        screen.blit(name_surf, (x + self.avatar_size + 8, y + 5))
        
        # 职业
        from src.definitions import JOB_LABELS
        job_label = JOB_LABELS.get(timeline.npc_job, timeline.npc_job)
        job_surf = self.font_small.render(job_label, True, self.colors['text_dim'])
        screen.blit(job_surf, (x + self.avatar_size + 8, y + 28))
        
        # 热度指示（不显示阶段文字）
        heat_color = self.colors['heat_low'] if timeline.heat < 40 else \
                     self.colors['heat_med'] if timeline.heat < 70 else self.colors['heat_high']
        heat_str = f"热度:{int(timeline.heat)}"
        heat_surf = self.font_small.render(heat_str, True, heat_color)
        screen.blit(heat_surf, (x + self.avatar_size + 8, y + 45))
    
    def _draw_nodes_for_timeline(self, screen: pygame.Surface, timeline: NPCTimeline, 
                                  center_y: int, mx: int, my: int):
        """为一条时间线绘制所有节点"""
        if not timeline.nodes:
            return
        
        # 绘制节点间的连线
        for i in range(len(timeline.nodes) - 1):
            node1 = timeline.nodes[i]
            node2 = timeline.nodes[i + 1]
            
            x1 = self._get_node_x(node1)
            x2 = self._get_node_x(node2)
            
            # 实线连接
            pygame.draw.line(screen, self.colors['line_real'], (x1, center_y), (x2, center_y), 2)
        
        # 绘制节点
        for node in timeline.nodes:
            node_x = self._get_node_x(node)
            self._draw_node(screen, node, node_x, center_y, mx, my)
    
    def _draw_node(self, screen: pygame.Surface, node: FateNode, x: int, y: int, mx: int, my: int):
        """绘制单个命运节点"""
        # 根据节点类型确定颜色
        if node.node_type == NodeType.CURRENT_INTERVENABLE:
            color = self.colors['node_current']
            size = self.node_size + 4
        elif node.node_type == NodeType.PLAYER_INTERVENED:
            color = self.colors['node_player']
            size = self.node_size
        elif node.node_type == NodeType.NPC_NATURAL:
            color = self.colors['node_npc']
            size = self.node_size - 2
        else:
            color = self.colors['node_past']
            size = self.node_size - 2
        
        # 悬停检测
        node_rect = pygame.Rect(x - size, y - size, size * 2, size * 2)
        is_hover = node_rect.collidepoint(mx, my)
        
        if is_hover:
            size += 2
            self.hover_node = node
        
        # 绘制节点
        if node.node_type == NodeType.CURRENT_INTERVENABLE:
            # 当前节点用方形
            pygame.draw.rect(screen, color, (x - size, y - size, size * 2, size * 2), border_radius=2)
            # 闪烁效果（可介入提示）
            if pygame.time.get_ticks() % 1000 < 500:
                pygame.draw.rect(screen, (255, 255, 255), (x - size - 2, y - size - 2, size * 2 + 4, size * 2 + 4), 1, border_radius=2)
        else:
            # 过去节点用圆形
            pygame.draw.circle(screen, color, (x, y), size)
        
        # 节点边框
        border_color = (255, 255, 255) if is_hover else (60, 60, 70)
        if node.node_type == NodeType.CURRENT_INTERVENABLE:
            pygame.draw.rect(screen, border_color, (x - size, y - size, size * 2, size * 2), 1, border_radius=2)
        else:
            pygame.draw.circle(screen, border_color, (x, y), size, 1)
        
        # 绘制困境标题（在节点上方）
        if is_hover or node.node_type == NodeType.CURRENT_INTERVENABLE:
            title_surf = self.font_small.render(node.dilemma_title[:12], True, self.colors['text'])
            title_x = x - title_surf.get_width() // 2
            title_y = y - size - 20
            screen.blit(title_surf, (title_x, title_y))
        
        # 绘制未选择的路径（虚线）
        if node.alternative_choices and len(node.alternative_choices) > 0:
            for alt in node.alternative_choices[:1]:  # 只画第一个备选
                # 向上飘散的虚线
                alt_y = y - 30
                for i in range(5):
                    dash_x = x + i * 8
                    dash_y = alt_y - i * 6
                    pygame.draw.circle(screen, self.colors['line_alt'], (dash_x, dash_y), 2)
    
    def _draw_legend(self, screen: pygame.Surface):
        """绘制图例"""
        legend_y = self.panel_y + self.panel_h - self.legend_h + 10
        legend_x = self.panel_x + 20
        
        # 图例标题
        title_surf = self.font_ui.render("图例:", True, self.colors['title'])
        screen.blit(title_surf, (legend_x, legend_y))
        
        # 图例项
        items = [
            ("━━□━━ 实线+节点 = 已走过的真实路径", self.colors['line_real']),
            ("□ 过去已决定的节点", self.colors['node_past']),
            ("■ 当前可介入的节点", self.colors['node_current']),
            ("🎮 玩家介入了此节点", self.colors['node_player']),
            ("⚙ NPC自己选的（自然发展）", self.colors['node_npc']),
        ]
        
        item_x = legend_x
        item_y = legend_y + 30
        
        for text, color in items:
            # 颜色块
            pygame.draw.rect(screen, color, (item_x, item_y, 12, 12), border_radius=2)
            # 文字
            text_surf = self.font_small.render(text, True, self.colors['text_dim'])
            screen.blit(text_surf, (item_x + 18, item_y - 2))
            
            item_x += text_surf.get_width() + 40
            if item_x > self.panel_x + self.panel_w - 200:
                item_x = legend_x
                item_y += 20
    
    def _draw_close_button(self, screen: pygame.Surface, mx: int, my: int):
        """绘制关闭按钮"""
        close_rect = pygame.Rect(
            self.panel_x + self.panel_w - 40,
            self.panel_y + 10,
            30, 30
        )
        
        is_hover = close_rect.collidepoint(mx, my)
        color = (200, 80, 80) if is_hover else (80, 70, 70)
        
        pygame.draw.rect(screen, color, close_rect, border_radius=6)
        pygame.draw.rect(screen, (150, 100, 100), close_rect, 2, border_radius=6)
        
        # X符号
        x_color = (255, 255, 255) if is_hover else (200, 200, 200)
        padding = 8
        x1, y1 = close_rect.left + padding, close_rect.top + padding
        x2, y2 = close_rect.right - padding, close_rect.bottom - padding
        pygame.draw.line(screen, x_color, (x1, y1), (x2, y2), 3)
        pygame.draw.line(screen, x_color, (x2, y1), (x1, y2), 3)
    
    def _draw_node_detail(self, screen: pygame.Surface, node: FateNode, mx: int, my: int):
        """绘制节点详情弹窗"""
        # 弹窗尺寸
        popup_w = 350
        popup_h = 200
        
        # 计算位置（在节点附近）
        node_x = self._get_node_x(node)
        popup_x = min(max(node_x - popup_w // 2, self.panel_x + 10), 
                     self.panel_x + self.panel_w - popup_w - 10)
        popup_y = self.panel_y + self.header_h + self.timeline_h + 50
        
        # 弹窗背景
        popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
        pygame.draw.rect(screen, (45, 48, 55), popup_rect, border_radius=8)
        pygame.draw.rect(screen, self.colors['border'], popup_rect, 2, border_radius=8)
        
        # 标题
        title_surf = self.font_ui.render(node.dilemma_title, True, self.colors['title'])
        screen.blit(title_surf, (popup_x + 15, popup_y + 15))
        
        # 描述
        desc_lines = [node.dilemma_desc[i:i+20] for i in range(0, len(node.dilemma_desc), 20)]
        desc_y = popup_y + 45
        for line in desc_lines[:3]:
            desc_surf = self.font_small.render(line, True, self.colors['text'])
            screen.blit(desc_surf, (popup_x + 15, desc_y))
            desc_y += 18
        
        # 玩家选择
        if node.player_choice:
            choice_surf = self.font_small.render(f"你的选择: {node.player_choice[:15]}", 
                                                True, self.colors['node_player'])
            screen.blit(choice_surf, (popup_x + 15, desc_y + 5))
            desc_y += 20
        
        # 后果
        if node.consequence:
            cons_surf = self.font_small.render(f"后果: {node.consequence[:20]}...", 
                                              True, self.colors['text_dim'])
            screen.blit(cons_surf, (popup_x + 15, desc_y + 5))
        
        # 可介入提示
        if node.is_intervenable:
            hint_surf = self.font_ui.render("【点击介入此困境】", True, self.colors['node_current'])
            screen.blit(hint_surf, (popup_x + (popup_w - hint_surf.get_width()) // 2, 
                                   popup_y + popup_h - 30))
    
    def _draw_scrollbar(self, screen: pygame.Surface, content_top: int, content_h: int):
        """绘制滚动条（支持拖动）"""
        # 计算滚动条参数（与handle_event保持一致）
        total_content_height = len(self.timelines) * self.npc_row_h
        can_scroll = total_content_height > content_h
        
        scrollbar_x = self.panel_x + self.panel_w - 20
        scrollbar_w = 8
        
        # 滚动条轨道背景
        pygame.draw.rect(screen, (50, 50, 60), 
                        (scrollbar_x, content_top, scrollbar_w, content_h), border_radius=4)
        
        # 滚动块（滑块）
        if can_scroll and self.max_scroll > 0:
            scrollbar_h = max(30, int(content_h * content_h / total_content_height))
            scroll_track_h = content_h - scrollbar_h
            
            visible_ratio = self.scroll_offset / self.max_scroll
            scrollbar_y = content_top + visible_ratio * scroll_track_h
            
            # 根据是否正在拖动改变颜色
            thumb_color = (140, 140, 160) if self.is_dragging else (100, 100, 120)
            pygame.draw.rect(screen, thumb_color, 
                            (scrollbar_x, scrollbar_y, scrollbar_w, scrollbar_h), border_radius=4)
        else:
            # 无需滚动时，滑块填满轨道
            pygame.draw.rect(screen, (80, 80, 90), 
                            (scrollbar_x, content_top, scrollbar_w, content_h), border_radius=4)
    
    def scroll(self, delta: int):
        """滚动内容"""
        self.scroll_offset = max(0, min(self.max_scroll, self.scroll_offset + delta))


# 全局实例
_fate_graph_ui: Optional[FateGraphUI] = None


def get_fate_graph_ui(screen_w: int = 0, screen_h: int = 0) -> FateGraphUI:
    """获取命运图谱界面实例（单例）"""
    global _fate_graph_ui
    if _fate_graph_ui is None:
        _fate_graph_ui = FateGraphUI(screen_w, screen_h)
    return _fate_graph_ui


def toggle_fate_graph_ui():
    """切换命运图谱界面显示状态"""
    panel = get_fate_graph_ui()
    # 由外部管理显示状态
    return panel
