# --- src/data/organization_defs.py ---
"""
组织/势力定义 - 北宋汴京社会分层系统
定义了基于势力类型的动态组织架构（士农工商学兵游匪）、组织等级、职业称号。
NPC 实例数据来自 data/npc_data.csv，本文件只定义结构性常量。
"""

# ======================== 势力类型定义 ========================
# 基于北宋社会结构，每种势力有不同的资源重点和行为特征
POWER_TYPES = {
    '士': {
        'name': '朝廷势力', 'eng': 'COURT',
        'resource_focus': 'AUTHORITY',  # 主要追求权力和地位
        'wealth_bonus': 1.5,            # 俸禄丰厚
        'influence_bonus': 2.0,         # 影响力强大
        'desc': '掌握朝廷权力，以官职品级论高低'
    },
    '农': {
        'name': '地主势力', 'eng': 'LANDOWNER', 
        'resource_focus': 'LAND',       # 主要掌握土地资源
        'wealth_bonus': 1.2,            # 有田产收入
        'influence_bonus': 1.3,         # 乡土影响力
        'desc': '拥有田地宅院，雇佣佃农长工'
    },
    '工': {
        'name': '工匠势力', 'eng': 'ARTISAN',
        'resource_focus': 'CRAFT',      # 技艺和制作能力
        'wealth_bonus': 0.9,            # 收入不稳定但技艺珍贵
        'influence_bonus': 1.0,         # 专业声望
        'desc': '掌握精湛技艺，以师父徒弟传承'
    },
    '商': {
        'name': '商贾势力', 'eng': 'MERCHANT',
        'resource_focus': 'GOLD',       # 金钱和商路
        'wealth_bonus': 1.8,            # 最会赚钱
        'influence_bonus': 1.1,         # 财富带来影响力
        'desc': '经营商铺货栈，财富雄厚但地位不高'
    },
    '学': {
        'name': '学术势力', 'eng': 'SCHOLAR',
        'resource_focus': 'KNOWLEDGE',  # 知识和文化
        'wealth_bonus': 0.8,            # 清贫但受尊敬
        'influence_bonus': 1.4,         # 文化声望高
        'desc': '传授学问，培养人才，受人敬重'
    },
    '兵': {
        'name': '军事势力', 'eng': 'MILITARY',
        'resource_focus': 'FORCE',      # 武力和军备
        'wealth_bonus': 1.0,            # 军饷固定
        'influence_bonus': 1.2,         # 武力威慑
        'desc': '掌控武力，维护秩序或制造动乱'
    },
    '游': {
        'name': '江湖势力', 'eng': 'MARTIAL',
        'resource_focus': 'FREEDOM',    # 自由和义气
        'wealth_bonus': 0.7,            # 收入不稳定
        'influence_bonus': 0.9,         # 江湖声望
        'desc': '游侠刺客，重义气轻生死，自由自在'
    },
    '匪': {
        'name': '盗匪势力', 'eng': 'BANDIT',
        'resource_focus': 'PLUNDER',    # 抢掠和藏匿
        'wealth_bonus': 0.6,            # 不稳定但有时暴富
        'influence_bonus': 0.5,         # 恶名在外
        'desc': '落草为寇，占山为王，与官府对立'
    }
}

# ======================== 组织等级系统 ========================
# 每个组织内部的等级划分，数字越大等级越高
ORG_RANKS = {
    1: {'name': '门徒', 'desc': '初入组织的新人'},
    2: {'name': '核心', 'desc': '组织的中坚力量'}, 
    3: {'name': '头目', 'desc': '负责一方事务的管理者'},
    4: {'name': '长老', 'desc': '位高权重的资深成员'},
    5: {'name': '首领', 'desc': '组织的最高统治者'}
}

# ======================== 具体组织实例 ========================
# 动态的组织列表，包含势力类型、领导者、势力范围等
# 每个组织由 org_id 标识，可以随时创建新的组织
ORGANIZATIONS = {
    # 朝廷系统
    'kaifeng_fu': {
        'name': '开封府', 'power_type': '士',
        'leader_seed': '方承意',  # 组织创立者/当前领导者
        'territory': '开封府衙',  # 势力范围
        'wealth_level': 5, 'influence_level': 5,
        'desc': '北宋都城最高行政机构'
    },
    'shenhou_fu': {
        'name': '神侯府', 'power_type': '士', 
        'leader_seed': '无情',
        'territory': '神侯府',
        'wealth_level': 4, 'influence_level': 5,
        'desc': '皇室直属的秘密执法机构'
    },
    
    # 地主势力
    'gao_manor': {
        'name': '高府', 'power_type': '农',
        'leader_seed': '高衙内', 
        'territory': '高府宅院',
        'wealth_level': 4, 'influence_level': 3,
        'desc': '高太尉家族的私人势力'
    },
    
    # 商业势力  
    'tianshui_alley': {
        'name': '甜水巷商会', 'power_type': '商',
        'leader_seed': '郁芊芊',
        'territory': '甜水巷',
        'wealth_level': 5, 'influence_level': 2, 
        'desc': '汴京最繁华商业街区的商人联盟'
    },
    
    # 学术势力
    'taixue': {
        'name': '太学馆', 'power_type': '学',
        'leader_seed': '袁桐',
        'territory': '太学馆',
        'wealth_level': 2, 'influence_level': 4,
        'desc': '培养士子的最高学府'
    },
    
    # 宗教势力
    'daxiangguo': {
        'name': '大相国寺', 'power_type': '学',  # 佛学也属于学问
        'leader_seed': '鲁智深',
        'territory': '大相国寺',
        'wealth_level': 3, 'influence_level': 4,
        'desc': '汴京香火最盛的佛寺'
    },
    
    # 江湖势力
    'beggar_gang': {
        'name': '丐帮', 'power_type': '游',
        'leader_seed': '洪小六',  # 暂时的小头目
        'territory': '街头巷尾',
        'wealth_level': 1, 'influence_level': 2,
        'desc': '遍布天下的乞丐组织'
    },
    
    # 服务业势力
    'shizizhipo': {
        'name': '十字坡', 'power_type': '商',
        'leader_seed': '孙二娘',
        'territory': '十字坡客栈',
        'wealth_level': 2, 'influence_level': 1,
        'desc': '路边客栈，消息灵通'
    },
    
    # 盗匪势力 - 实际上受高府暗中资助
    'heifeng_zhai': {
        'name': '黑风寨', 'power_type': '匪',
        'leader_seed': '王老虎',  # 黑风大王就是王老虎，绰号"黑风大王"
        'territory': '城外山林',
        'wealth_level': 2, 'influence_level': 1,
        'desc': '名义上落草为寇，实际暗中受高府资助，替高衙内办事',
        'secret_backer': 'gao_manor'  # 暗中支持者
    },
    'qinglang_bang': {
        'name': '青狼帮', 'power_type': '匪',
        'leader_seed': '青狼',
        'territory': '城外山林',
        'wealth_level': 2, 'influence_level': 1,
        'desc': '凶狠狡诈的山贼团伙'
    },
    'luopo_gang': {
        'name': '骆驼帮', 'power_type': '匪',
        'leader_seed': '骆大',
        'territory': '官道两侧',
        'wealth_level': 1, 'influence_level': 1,
        'desc': '专劫往来商旅的马贼'
    }
}

# ======================== 职业等级称号系统 ========================
# 每种职业在不同等级时的称号
JOB_RANK_TITLES = {
    'OFFICIAL': {
        1: '小吏', 2: '主簿', 3: '县丞', 4: '知县', 5: '知府'
    },
    'GUARD': {
        1: '新卒', 2: '甲长', 3: '队正', 4: '校尉', 5: '都尉'
    },
    'MERCHANT': {
        1: '小贩', 2: '店伙', 3: '掌柜', 4: '东家', 5: '巨贾'
    },
    'FARMER': {
        1: '佃户', 2: '自耕农', 3: '富农', 4: '庄主', 5: '大地主'
    },
    'SCHOLAR': {
        1: '童生', 2: '秀才', 3: '举人', 4: '进士', 5: '大儒'
    },
    'MONK': {
        1: '沙弥', 2: '僧众', 3: '知客', 4: '首座', 5: '方丈'
    },
    'ARTISAN': {
        1: '学徒', 2: '帮工', 3: '匠人', 4: '匠师', 5: '大师'
    },
    'BANDIT': {
        1: '喽啰', 2: '小头目', 3: '当家', 4: '二当家', 5: '大当家'
    },
    'THUG': {
        1: '小混混', 2: '泼皮', 3: '头目', 4: '堂主', 5: '大哥'
    },
    'NONE': {
        1: '流民', 2: '流民', 3: '流民', 4: '流民', 5: '流民'
    }
}

def get_job_title(job, org_rank):
    """获取职业等级称号"""
    job_titles = JOB_RANK_TITLES.get(job, JOB_RANK_TITLES['NONE'])
    return job_titles.get(org_rank, job_titles.get(1, job))
