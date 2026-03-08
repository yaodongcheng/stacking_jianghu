# --- src/faction_colors.py ---
"""
【势力可视化系统】

为不同势力/组织分配独特的颜色，用于：
1. 大地图上 NPC 卡牌的边框颜色
2. 小地图上 NPC 的点颜色
3. 根据势力内等级调整边框粗细/点大小

颜色设计原则：
- 朝廷/官府：金黄色系（权威）
- 江湖门派：各有特色
- 盗匪势力：红黑色系（危险）
- 商业势力：紫色系（财富）
- 宗教势力：青白色系（清净）
- 平民/无势力：灰色系
"""

# ═══════════════════════════════════════════════════════════════════
# 组织颜色映射 - (R, G, B) 格式
# ═══════════════════════════════════════════════════════════════════
# 设计原则：
# 【白道】明亮、正色调 - 金/蓝/绿/紫系
# 【黑道】暗沉、危险色调 - 红/棕/灰黑系
# 每个势力必须有明显区别，避免同色系撞色
# ═══════════════════════════════════════════════════════════════════
ORG_COLORS = {
    # ══════════════════════════════════════════════════════════════
    # 【白道势力】- 明亮、正气的色调
    # ══════════════════════════════════════════════════════════════
    
    # === 朝廷系统 (皇家金/官府蓝) ===
    'kaifeng_fu':     (255, 215, 0),    # 开封府 - 明黄金色（皇权象征）
    'shenhou_fu':     (70, 130, 220),   # 神侯府 - 皇家蓝（秘密执法）
    
    # === 地主势力 (橙黄暖色) ===
    'gao_manor':      (230, 160, 60),   # 高府 - 土豪橙（暴发户金）
    
    # === 商业势力 (紫/粉富贵色) ===
    'tianshui_alley': (200, 100, 180),  # 甜水巷商会 - 富贵紫
    'shizizhipo':     (180, 130, 100),  # 十字坡 - 商旅棕（客栈）
    
    # === 学术势力 (书卷青/蓝) ===
    'taixue':         (100, 180, 160),  # 太学馆 - 书卷青（文气）
    
    # === 宗教势力 (禅意青白) ===
    'daxiangguo':     (220, 200, 140),  # 大相国寺 - 袈裟金黄
    
    # === 江湖正道 (侠义绿) ===
    'beggar_gang':    (140, 180, 100),  # 丐帮 - 草莽绿（江湖义气）
    
    # ══════════════════════════════════════════════════════════════
    # 【黑道势力】- 暗沉、危险的色调
    # ══════════════════════════════════════════════════════════════
    
    # === 盗匪势力 (血红/暗黑系) ===
    'heifeng_zhai':   (180, 50, 50),    # 黑风寨 - 暗血红（山贼凶煞）
    'qinglang_bang':  (80, 100, 80),    # 青狼帮 - 狼灰绿（阴险狡诈）
    'luopo_gang':     (130, 90, 60),    # 骆驼帮 - 沙漠棕（马贼）
    
    # ══════════════════════════════════════════════════════════════
    # 【特殊标记】
    # ══════════════════════════════════════════════════════════════
    'NONE':           (130, 130, 130),  # 无势力 - 中灰色
    'PLAYER_ORG':     (80, 200, 255),   # 玩家势力 - 天蓝色
}

# 组织等级对应的边框粗细和点大小
# rank 0 (普通成员) -> 1 (干部) -> 2 (精英) -> 3 (核心) -> 4/5 (领袖)
# 等级越低边框越细，差异要更明显
RANK_BORDER_WIDTH = {
    0: 2,   # 普通成员：细边框
    1: 2,   # 干部：细边框
    2: 3,   # 精英
    3: 4,   # 核心
    4: 5,   # 领袖
    5: 6,   # 最高领袖
}

# 社会等级额外加成（大人物边框更粗）
# social_level 1-5 对应额外加粗 0-4
SOCIAL_LEVEL_BORDER_BONUS = {
    1: 0,   # 平民
    2: 1,   # 富户
    3: 2,   # 官绅
    4: 3,   # 权贵
    5: 4,   # 显贵（如方承意）
}

RANK_MINIMAP_RADIUS = {
    0: 2,   # 普通成员：小点
    1: 2,   # 干部
    2: 3,   # 精英
    3: 3,   # 核心
    4: 4,   # 领袖
    5: 4,   # 最高领袖
}


def get_org_color(org_id):
    """
    获取组织对应的颜色
    
    Args:
        org_id: 组织ID (如 'kaifeng_fu', 'heifeng_zhai')
    
    Returns:
        (R, G, B) 颜色元组
    """
    if not org_id or org_id == 'NONE':
        return ORG_COLORS['NONE']
    
    return ORG_COLORS.get(org_id, ORG_COLORS['NONE'])


def get_border_width_for_rank(org_rank):
    """
    根据组织内等级获取边框粗细
    
    Args:
        org_rank: 组织内等级 (0-4)
    
    Returns:
        边框宽度 (2-4)
    """
    rank = min(4, max(0, org_rank or 0))
    return RANK_BORDER_WIDTH.get(rank, 2)


def get_minimap_radius_for_rank(org_rank):
    """
    根据组织内等级获取小地图点大小
    
    Args:
        org_rank: 组织内等级 (0-4)
    
    Returns:
        点半径 (1-4)
    """
    rank = min(4, max(0, org_rank or 0))
    return RANK_MINIMAP_RADIUS.get(rank, 1)


def get_npc_faction_visual(npc):
    """
    获取 NPC 的势力可视化信息
    
    边框粗细计算规则：
    1. 基础粗细由 org_rank 决定（组织内等级）
    2. 额外粗细由 social_level 决定（社会地位）
    3. 最终粗细 = 基础 + 社会等级加成
    
    这样可以确保：
    - 方承意（org_rank=5, social_level=5）边框最粗（6+4=10）
    - 高衙内（org_rank=5, social_level=4）次粗（6+3=9）
    - 泼皮牛二（org_rank=2, social_level=1）较细（3+0=3）
    - 泼皮狗蛋（org_rank=1, social_level=1）最细（2+0=2）
    
    Args:
        npc: NPC 对象
    
    Returns:
        dict: {
            'color': (R, G, B),     # 边框/点颜色
            'border_width': int,    # 边框粗细
            'minimap_radius': int,  # 小地图点大小
            'org_name': str,        # 组织名称（用于tooltip）
        }
    """
    # 玩家特殊处理
    if getattr(npc, 'job', '') == 'PLAYER':
        return {
            'color': (255, 255, 255),  # 玩家始终白色
            'border_width': 3,
            'minimap_radius': 3,
            'org_name': '玩家',
            'is_player': True,
        }
    
    # 门客特殊处理
    if getattr(npc, 'is_follower', False):
        return {
            'color': ORG_COLORS['PLAYER_ORG'],  # 跟随玩家的用天蓝色
            'border_width': 2,
            'minimap_radius': 2,
            'org_name': '门客',
            'is_follower': True,
        }
    
    # 获取组织信息
    org_id = getattr(npc, 'organization', None) or getattr(npc, 'org_id', None) or 'NONE'
    org_rank = getattr(npc, 'org_rank', 0) or 0
    social_level = getattr(npc, 'social_level', 1) or 1
    
    # 获取组织名称
    org_name = '无势力'
    if org_id and org_id != 'NONE':
        try:
            from src.data.character_seeds import ORGANIZATIONS
            org_data = ORGANIZATIONS.get(org_id, {})
            org_name = org_data.get('name', org_id)
        except:
            org_name = org_id
    
    color = get_org_color(org_id)
    
    # 计算边框粗细：基础 + 社会等级加成
    base_width = RANK_BORDER_WIDTH.get(min(5, org_rank), 2)
    social_bonus = SOCIAL_LEVEL_BORDER_BONUS.get(min(5, social_level), 0)
    border_width = base_width + social_bonus
    
    # 小地图点大小
    minimap_radius = RANK_MINIMAP_RADIUS.get(min(5, org_rank), 2)
    
    return {
        'color': color,
        'border_width': border_width,
        'minimap_radius': minimap_radius,
        'org_name': org_name,
        'org_id': org_id,
        'org_rank': org_rank,
        'social_level': social_level,
    }


# ═══════════════════════════════════════════════════════════════════
# 调试：打印所有势力颜色
# ═══════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print("=== 势力颜色配置 ===")
    for org_id, color in ORG_COLORS.items():
        print(f"  {org_id}: RGB{color}")
