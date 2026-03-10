# --- src/data/character_seeds.py ---
"""
NPC 种子数据仓库 - 北宋汴京社会分层系统
定义了基于势力类型的动态组织架构，任何NPC都可以成立或加入组织。
势力类型：士农工商学兵游匪 - 体现真实的社会运转和等级秩序。
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

# 保持向后兼容的旧式组织映射
ORGS = {org_id: org_data['name'] for org_id, org_data in ORGANIZATIONS.items()}
ORGS['NONE'] = '无'

# ======================== 角色种子数据 ======================== 
# 新的属性结构：
# - power_type: 势力类型 (士农工商学兵游匪)  
# - org_id: 组织ID (对应ORGANIZATIONS中的key)
# - org_role: 组织内角色 ('LEADER'/'MEMBER'/'BODYGUARD')
# - social_level: 社会等级 (1-5, 影响接触难度和护卫需求)
SEEDS = [
    
    # =============== 朝廷势力 (士) ===============
    {
        'name': '方承意', 'gender': 'Male', 'age': 26,
        'power_type': '士', 'org_id': 'kaifeng_fu', 'org_role': 'LEADER', 'org_rank': 5,
        'social_level': 5,
        'desc': '明昭侯，开封府尹，心思深沉，权倾朝野。',
        'tags': ['POWERFUL', 'RICH', 'NOBLE', 'CUNNING'],
        'relations': {'BODYGUARD': '林冲', 'SUBORDINATE': '无情'},
        'wealth_level': 5, 'influence_level': 5,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '温和',      # 脾气：温和（表面）
            'spirit': '勇敢',      # 胆量：勇敢
            'ism': '现实',         # 主义：现实（实用主义者）
            'act_style': '缜密',   # 风格：缜密（心思深沉）
            'friendship': '不重情义',  # 情义：不重情义（政治动物）
            'ambition': 85,        # 野心：高（权倾朝野）
            'desire_type': '权力', # 物欲类型
            'desire': '贪心'       # 物欲程度
        },
        # 【新增】初始困境 - 权力危机
        'initial_dilemma': {
            'title': '朝堂暗涌',
            'surface': '朝中老臣对方承意年轻上位心存不满，暗中散布谣言质疑他的能力',
            'core_conflict': '欲望：巩固权力地位 vs 现实：资历尚浅，需要更多政绩',
            'desire': '让朝中大臣心服口服，稳固自己的地位',
            'block': '老臣们暗中阻挠，需要一场大案来证明能力，但赵师爷等老臣阳奉阴违'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神深邃锐利。人物：方承意，26岁，明昭侯，开封府尹，权倾朝野的贵族公子，气质冷峻深沉，身着华贵紫色官服，玉带束腰，头戴乌纱。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, noble and powerful aura'
    },
    {
        'name': '无情', 'gender': 'Male', 'age': 24,  
        'power_type': '士', 'org_id': 'shenhou_fu', 'org_role': 'LEADER', 'org_rank': 5,
        'social_level': 4,
        'desc': '神侯府四大名捕之首，双腿残疾但轻功暗器一绝。',
        'tags': ['SMART', 'CALM', 'DETECTIVE', 'DISABLED'],
        'relations': {'SUPERIOR': '方承意'},
        'wealth_level': 3, 'influence_level': 4,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '温和',      # 脾气：温和（冷静理智）
            'spirit': '勇敢',      # 胆量：勇敢（不畏权贵）
            'ism': '现实',         # 主义：现实（注重证据）
            'act_style': '缜密',   # 风格：缜密（神探本色）
            'friendship': '重情义',  # 情义：重情义（对兄弟有情有义）
            'ambition': 60,        # 野心：中等（追求正义而非权力）
            'desire_type': '名誉', # 物欲类型
            'desire': '一般'       # 物欲程度
        },
        # 【新增】初始困境 - 身份困境
        'initial_dilemma': {
            'title': '轮椅上的枷锁',
            'surface': '作为神侯府名捕，无情需要追捕一名潜逃的朝廷要犯，但地形复杂，轮椅难以通行',
            'core_conflict': '欲望：证明自己依然是最强的捕快 vs 现实：双腿残疾带来的行动限制',
            'desire': '不因残疾而被轻视，维护神侯府的威名',
            'block': '身体的局限与自尊心的冲突，以及下属暗中保护带来的屈辱感'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神冷静睿智。人物：无情，24岁，神侯府名捕，坐轮椅的冷面神探，气质清冷孤傲，身着黑色捕快服，银色暗纹，长发束冠。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, cold and intelligent detective'
    },
    {
        'name': '林冲', 'gender': 'Male', 'age': 35,
        'power_type': '兵', 'org_id': 'kaifeng_fu', 'org_role': 'BODYGUARD', 'org_rank': 3,
        'social_level': 3,
        'desc': '八十万禁军教头，武艺高强，护卫方承意。',
        'tags': ['HERO', 'JUSTICE', 'LOYAL', 'WARRIOR'],
        'relations': {'LEADER': '方承意', 'FRIEND': '鲁智深'},
        'wealth_level': 2, 'influence_level': 2,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '暴躁',      # 脾气：暴躁（但隐忍）
            'spirit': '勇敢',      # 胆量：勇敢（武艺高强）
            'ism': '理想',         # 主义：理想（忠君爱国）
            'act_style': '豪放',   # 风格：豪放（武将本色）
            'friendship': '重情义',  # 情义：重情义（对朋友肝胆相照）
            'ambition': 40,        # 野心：较低（只想安稳度日）
            'desire_type': '安定', # 物欲类型
            'desire': '一般'       # 物欲程度
        },
        # 【新增】初始困境 - 身份困境
        'initial_dilemma': {
            'title': '忠义的枷锁',
            'surface': '林冲发现方承意暗中打压政敌，手段并不光明磊落',
            'core_conflict': '欲望：保持忠君爱国的理想 vs 现实：效忠的主公并非完美君子',
            'desire': '既不想背叛主公，又不想违背内心的正义',
            'block': '方承意对他有知遇之恩，但某些命令让他良心不安'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神坚毅正直。人物：林冲，35岁，禁军教头，武艺高强的忠勇武将，气质刚毅沉稳，身着铠甲战袍，肩披斗篷，英武挺拔。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, heroic warrior'
    },

    # =============== 地主势力 (农) ===============  
    {
        'name': '高衙内', 'gender': 'Male', 'age': 30,
        'power_type': '农', 'org_id': 'gao_manor', 'org_role': 'LEADER', 'org_rank': 5,
        'social_level': 4,
        'desc': '高太尉养子，拥有大量田产，仗势欺人。',
        'tags': ['VILLAIN', 'LUSTFUL', 'RICH', 'ARROGANT'],
        'relations': {'BODYGUARD': '高大胜'},
        'wealth_level': 4, 'influence_level': 3,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '暴躁',      # 脾气：暴躁（纨绔子弟）
            'spirit': '胆小',      # 胆量：胆小（欺软怕硬）
            'ism': '现实',         # 主义：现实（享乐主义者）
            'act_style': '豪放',   # 风格：豪放（行事张扬）
            'friendship': '不重情义',  # 情义：不重情义（利用他人）
            'ambition': 70,        # 野心：较高（想证明自己不是废物）
            'desire_type': '美色', # 物欲类型
            'desire': '贪心'       # 物欲程度
        },
        # 【新增】初始困境 - 继承危机
        'initial_dilemma': {
            'title': '养子的阴影',
            'surface': '高府的远房亲戚们开始觊觎家产，高衙内担心自己的地位不保',
            'core_conflict': '欲望：保住高府的产业和自己的地位 vs 现实：只是养子，血缘上不占优势',
            'desire': '证明自己的能力，让高府上下认可自己',
            'block': '府中上下都认为他只是靠养父庇护的纨绔，没有真本事，连高大胜都暗中看不起他'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神猥琐傲慢。人物：高衙内，30岁，高太尉养子，纨绔子弟，气质轻浮嚣张，身着华丽锦缎长袍，金饰玉佩，面带邪笑。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, villainous and arrogant noble'
    },
    {
        'name': '高大胜', 'gender': 'Male', 'age': 27,
        'power_type': '兵', 'org_id': 'gao_manor', 'org_role': 'BODYGUARD', 'org_rank': 2,
        'social_level': 2,
        'desc': '高府金牌打手，为给母亲治病而卖身高府。',
        'tags': ['FILIAL', 'STRONG', 'CONFLICTED'],
        'relations': {'LEADER': '高衙内'},
        'wealth_level': 2, 'influence_level': 1,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '温和',      # 脾气：温和（本性善良）
            'spirit': '勇敢',      # 胆量：勇敢（武艺高强）
            'ism': '现实',         # 主义：现实（为母治病）
            'act_style': '豪放',   # 风格：豪放（武将本色）
            'friendship': '重情义',  # 情义：重情义（孝顺母亲）
            'ambition': 35,        # 野心：低（只想救母）
            'desire_type': '亲情', # 物欲类型
            'desire': '一般'       # 物欲程度
        },
        # 【新增】初始困境 - 道德困境
        'initial_dilemma': {
            'title': '孝与义的抉择',
            'surface': '高衙内命令高大胜去教训一个欠租的穷苦佃农',
            'core_conflict': '欲望：孝顺母亲，需要这份工作的收入买药 vs 现实：本性善良，不愿欺负弱小',
            'desire': '攒够钱给母亲治好病，然后离开高府',
            'block': '母亲的病需要持续用药，他无法承担失去工作的后果'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神矛盾挣扎。人物：高大胜，27岁，高府打手，身材魁梧的壮汉，气质憨厚中带忧郁，身着粗布劲装，肌肉发达，表情复杂。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, conflicted strong fighter'
    },
    {
        'name': '张青', 'gender': 'Male', 'age': 38,
        'power_type': '农', 'org_id': 'shizizhipo', 'org_role': 'MEMBER', 'org_rank': 2,
        'social_level': 1,
        'desc': '菜园子张青，在十字坡种菜，怕老婆。',
        'tags': ['HENPECKED', 'HONEST', 'HARDWORKING'],
        'relations': {'WIFE': '孙二娘'},
        'wealth_level': 1, 'influence_level': 1,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '温和',      # 脾气：温和（老实人）
            'spirit': '胆小',      # 胆量：胆小（怕老婆）
            'ism': '现实',         # 主义：现实（只求安稳）
            'act_style': '缜密',   # 风格：缜密（种菜需要耐心）
            'friendship': '重情义',  # 情义：重情义（对妻子百依百顺）
            'ambition': 20,        # 野心：很低（只想种菜）
            'desire_type': '安定', # 物欲类型
            'desire': '一般'       # 物欲程度
        },
        # 【新增】初始困境 - 婚姻困境
        'initial_dilemma': {
            'title': '菜园子的烦恼',
            'surface': '孙二娘又逼张青去城里收保护费，但他只想安心种菜',
            'core_conflict': '欲望：过平静的田园生活 vs 现实：妻子是江湖人，不甘平凡',
            'desire': '种出最好的蔬菜，过上安稳日子',
            'block': '妻子孙二娘性格强势，总是拉他卷入江湖纷争'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神老实憨厚。人物：张青，38岁，菜园农夫，老实巴交的庄稼汉，气质朴实懦弱，身着粗布短打，皮肤黝黑，面带苦相。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, honest henpecked farmer'
    },

    # =============== 商业势力 (商) ===============
    {
        'name': '郁芊芊', 'gender': 'Female', 'age': 19,
        'power_type': '商', 'org_id': 'tianshui_alley', 'org_role': 'LEADER', 'org_rank': 4,
        'social_level': 3,
        'desc': '甜水巷商会会长，富家大小姐，经商天赋极高。',
        'tags': ['RICH', 'ARROGANT', 'SMART', 'BUSINESS_GENIUS'],
        'relations': {'SUBORDINATE': '王小乐'},
        'wealth_level': 5, 'influence_level': 2,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '暴躁',      # 脾气：暴躁（大小姐脾气）
            'spirit': '勇敢',      # 胆量：勇敢（敢想敢做）
            'ism': '现实',         # 主义：现实（利益至上）
            'act_style': '豪放',   # 风格：豪放（行事果决）
            'friendship': '不重情义',  # 情义：不重情义（商人本色）
            'ambition': 75,        # 野心：高（想超越父辈）
            'desire_type': '财富', # 物欲类型
            'desire': '贪心'       # 物欲程度
        },
        # 【新增】初始困境 - 家族危机
        'initial_dilemma': {
            'title': '千金的重担',
            'surface': '郁家最大的商业伙伴突然撤资，甜水巷商会面临资金链断裂的危机',
            'core_conflict': '欲望：证明自己的能力，不靠家族也能成功 vs 现实：商会危机需要家族势力才能解决',
            'desire': '独立解决危机，让父亲刮目相看',
            'block': '父亲要求她放弃商会管理权，嫁给另一个富商之子换取资金支持'
        },
        'avatar_prompt': '国漫古风女性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神自信傲气。人物：郁芊芊，19岁，甜水巷商会会长，富家千金，气质高贵优雅，身着华丽丝绸长裙，金钗玉饰，眉目如画。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, arrogant rich lady'
    },
    {
        'name': '孙二娘', 'gender': 'Female', 'age': 35,
        'power_type': '商', 'org_id': 'shizizhipo', 'org_role': 'LEADER', 'org_rank': 3,
        'social_level': 2,
        'desc': '十字坡老板娘，擅长黑暗料理和收集情报。',
        'tags': ['TOUGH', 'COOK_DARK', 'INFORMATION_BROKER'],
        'relations': {'HUSBAND': '张青'},
        'wealth_level': 2, 'influence_level': 2,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '暴躁',      # 脾气：暴躁（江湖儿女）
            'spirit': '勇敢',      # 胆量：勇敢（天不怕地不怕）
            'ism': '现实',         # 主义：现实（利益至上）
            'act_style': '豪放',   # 风格：豪放（行事果决）
            'friendship': '重情义',  # 情义：重情义（对丈夫刀子嘴豆腐心）
            'ambition': 55,        # 野心：中等（想扩大十字坡势力）
            'desire_type': '财富', # 物欲类型
            'desire': '贪心'       # 物欲程度
        },
        # 【新增】初始困境 - 婚姻与事业
        'initial_dilemma': {
            'title': '十字坡的野心',
            'surface': '孙二娘想将十字坡客栈扩张为江湖情报中心，但张青只想安心种菜',
            'core_conflict': '欲望：在江湖上闯出一番事业 vs 现实：丈夫是个老实人，不愿卷入江湖纷争',
            'desire': '让十字坡成为汴京最大的消息集散地',
            'block': '丈夫张青的反对，以及缺乏启动资金和人脉'
        },
        'avatar_prompt': '国漫古风女性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神凌厉精明。人物：孙二娘，35岁，十字坡客栈老板娘，泼辣干练的江湖女，气质强悍泼辣，身着粗布围裙，挽袖束腰，面带煞气。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, tough and fierce woman'
    },
    {
        'name': '鱼西施', 'gender': 'Female', 'age': 18,
        'power_type': '商', 'org_id': None, 'org_role': None, 'org_rank': 0,
        'social_level': 1,
        'desc': '城东门外卖鱼的姑娘，因貌美如花被街坊称为鱼西施。',
        'tags': ['BEAUTIFUL', 'HARDWORKING', 'GENTLE', 'POOR'],
        'relations': {},
        'wealth_level': 1, 'influence_level': 1,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '温和',      # 脾气：温和（温柔善良）
            'spirit': '胆小',      # 胆量：胆小（弱女子）
            'ism': '理想',         # 主义：理想（相信好人有好报）
            'act_style': '缜密',   # 风格：缜密（卖鱼需要精打细算）
            'friendship': '重情义',  # 情义：重情义（对帮助过她的人感恩）
            'ambition': 25,        # 野心：低（只想安稳生活）
            'desire_type': '安定', # 物欲类型
            'desire': '一般'       # 物欲程度
        },
        # 【新增】初始困境 - 美貌困境
        'initial_dilemma': {
            'title': '美貌的诅咒',
            'surface': '高衙内看上了鱼西施的美貌，派人来提亲，威胁她若不从就让她无法在城中卖鱼',
            'core_conflict': '欲望：靠自己的努力过平凡生活 vs 现实：美貌引来权贵觊觎',
            'desire': '继续卖鱼养活自己，不想成为任何人的玩物',
            'block': '高衙内的权势让她无处可逃，普通街坊也不敢帮助她'
        },
        'avatar_prompt': '国漫古风女性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神清澈灵动。人物：鱼西施，18岁，市井渔家少女，清秀灵动，气质干净纯粹，略带水乡灵气。中式武侠布衣设计，简约素雅。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, gentle and pure village girl'
    },
    {
        'name': '王小乐', 'gender': 'Male', 'age': 45,
        'power_type': '商', 'org_id': 'tianshui_alley', 'org_role': 'MEMBER', 'org_rank': 1,
        'social_level': 1,
        'desc': '甜水巷的老油条伙计，善于逢迎拍马。',
        'tags': ['SLIPPERY', 'SNOB', 'EXPERIENCED'],
        'relations': {'LEADER': '郁芊芊'},
        'wealth_level': 2, 'influence_level': 1,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '温和',      # 脾气：温和（表面逢迎）
            'spirit': '胆小',      # 胆量：胆小（不敢得罪人）
            'ism': '现实',         # 主义：现实（利益至上）
            'act_style': '缜密',   # 风格：缜密（察言观色）
            'friendship': '不重情义',  # 情义：不重情义（墙头草）
            'ambition': 45,        # 野心：中等（想往上爬）
            'desire_type': '财富', # 物欲类型
            'desire': '贪心'       # 物欲程度
        },
        # 【新增】初始困境 - 职场困境
        'initial_dilemma': {
            'title': '老伙计的危机',
            'surface': '郁芊芊发现王小乐暗中收商户贿赂，在分配摊位时偏袒某些商家',
            'core_conflict': '欲望：攒够钱回乡养老 vs 现实：习惯了灰色收入，难以收手',
            'desire': '不被赶出商会，保住这份做了二十年的差事',
            'block': '郁芊芊年轻气盛，整顿商会纪律，他的老一套行不通了'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神谄媚圆滑。人物：王小乐，45岁，甜水巷老油条伙计，市侩精明的商人，气质油滑世故，身着灰色布衣，点头哈腰，面带假笑。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, sly and snobbish shop assistant'
    },

    # =============== 工匠势力 (工) ===============
    {
        'name': '李师师', 'gender': 'Female', 'age': 22,
        'power_type': '工', 'org_id': 'tianshui_alley', 'org_role': 'MEMBER', 'org_rank': 5,
        'social_level': 3,
        'desc': '名动京师的花魁，琴棋书画样样精通。',
        'tags': ['BEAUTIFUL', 'TALENTED', 'ARTISTIC', 'FAMOUS'],
        'relations': {},
        'wealth_level': 3, 'influence_level': 3,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '温和',      # 脾气：温和（表面温婉）
            'spirit': '勇敢',      # 胆量：勇敢（内心坚强）
            'ism': '理想',         # 主义：理想（渴望真爱）
            'act_style': '缜密',   # 风格：缜密（察言观色）
            'friendship': '重情义',  # 情义：重情义（对知己倾心）
            'ambition': 50,        # 野心：中等（想摆脱风尘）
            'desire_type': '自由', # 物欲类型
            'desire': '一般'       # 物欲程度
        },
        # 【新增】初始困境 - 风尘困境
        'initial_dilemma': {
            'title': '花魁的归宿',
            'surface': '一位富商愿出千金为李师师赎身，但她知道对方只是贪图她的美貌',
            'core_conflict': '欲望：摆脱风尘，过上普通女子的生活 vs 现实：赎身后不过是换个笼子',
            'desire': '找到一个真正懂她、尊重她的人，而非只把她当玩物',
            'block': '花魁的身份既是她的光环也是她的枷锁，无人相信她有真心'
        },
        'avatar_prompt': '国漫古风女性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神妩媚动人。人物：李师师，22岁，名动京师的花魁，倾国倾城之貌，气质优雅脱俗，身着华丽舞衣，珠翠环绕，风情万种。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, glamorous and talented courtesan'
    },

    # =============== 学术势力 (学) ===============
    {
        'name': '袁桐', 'gender': 'Female', 'age': 50,
        'power_type': '学', 'org_id': 'taixue', 'org_role': 'LEADER', 'org_rank': 4,
        'social_level': 3,
        'desc': '太学馆山长夫人，学识渊博，溺爱女儿。',
        'tags': ['LOVING_MOTHER', 'SCHOLARLY', 'RESPECTED'],
        'relations': {'CHILD': '孙小溪'},
        'wealth_level': 2, 'influence_level': 4,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '温和',      # 脾气：温和（慈母）
            'spirit': '胆小',      # 胆量：胆小（不愿惹事）
            'ism': '理想',         # 主义：理想（相信教育）
            'act_style': '缜密',   # 风格：缜密（学者本色）
            'friendship': '重情义',  # 情义：重情义（对女儿百依百顺）
            'ambition': 30,        # 野心：低（只想女儿好）
            'desire_type': '亲情', # 物欲类型
            'desire': '一般'       # 物欲程度
        },
        # 【新增】初始困境 - 教育困境
        'initial_dilemma': {
            'title': '严母与慈母',
            'surface': '孙小溪又逃课去大相国寺喂鸽子，袁桐不知该严厉管教还是继续纵容',
            'core_conflict': '欲望：让女儿成为知书达理的大家闺秀 vs 现实：女儿天性活泼，不爱读书',
            'desire': '女儿能快乐成长，同时又不辜负太学馆的期望',
            'block': '山长夫人的身份让她必须维持体面，但女儿的不争气让她颜面尽失'
        },
        'avatar_prompt': '国漫古风女性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神慈爱温和。人物：袁桐，50岁，太学馆山长夫人，端庄贤淑的学者妇人，气质温文尔雅，身着素雅长衫，发髻整齐，面带慈祥。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, scholarly and motherly woman'
    },
    {
        'name': '孙小溪', 'gender': 'Female', 'age': 15,
        'power_type': '学', 'org_id': 'taixue', 'org_role': 'MEMBER', 'org_rank': 1,
        'social_level': 1,
        'desc': '太学馆学生，聪明伶俐但爱逃课玩耍。',
        'tags': ['PLAYFUL', 'ANIMAL_LOVER', 'INTELLIGENT'],
        'relations': {'MOTHER': '袁桐'},
        'wealth_level': 2, 'influence_level': 1,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '暴躁',      # 脾气：暴躁（活泼好动）
            'spirit': '勇敢',      # 胆量：勇敢（天不怕地不怕）
            'ism': '理想',         # 主义：理想（相信世界美好）
            'act_style': '豪放',   # 风格：豪放（不拘小节）
            'friendship': '重情义',  # 情义：重情义（对小动物有爱心）
            'ambition': 35,        # 野心：低（只想自由自在）
            'desire_type': '自由', # 物欲类型
            'desire': '一般'       # 物欲程度
        },
        # 【新增】初始困境 - 成长困境
        'initial_dilemma': {
            'title': '笼中鸟',
            'surface': '袁桐要求孙小溪参加即将到来的才女选拔，但她只想每天去大相国寺喂鸽子',
            'core_conflict': '欲望：自由自在地玩耍，不想被规矩束缚 vs 现实：身为山长之女，必须维持体面',
            'desire': '做一个普通女孩，而不是什么才女',
            'block': '母亲的期望和太学馆的压力让她喘不过气'
        },
        'avatar_prompt': '国漫古风女性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神活泼俏皮。人物：孙小溪，15岁，太学馆学生，古灵精怪的少女，气质天真烂漫，身着淡色襦裙，发带飘扬，笑容甜美。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, playful and intelligent young girl'
    },
    {
        'name': '鲁智深', 'gender': 'Male', 'age': 40,
        'power_type': '学', 'org_id': 'daxiangguo', 'org_role': 'LEADER', 'org_rank': 3,
        'social_level': 2,
        'desc': '大相国寺知客僧，力大无穷，倒拔垂杨柳。',
        'tags': ['JUSTICE', 'STRONG', 'DRUNK', 'MONK'],
        'relations': {'FRIEND': '林冲', 'SUBORDINATE': '弥乐'},
        'wealth_level': 1, 'influence_level': 3,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '暴躁',      # 脾气：暴躁（火爆脾气）
            'spirit': '勇敢',      # 胆量：勇敢（天不怕地不怕）
            'ism': '理想',         # 主义：理想（路见不平拔刀相助）
            'act_style': '豪放',   # 风格：豪放（行事洒脱）
            'friendship': '重情义',  # 情义：重情义（为朋友两肋插刀）
            'ambition': 30,        # 野心：低（只求快意恩仇）
            'desire_type': '酒肉', # 物欲类型
            'desire': '贪心'       # 物欲程度
        },
        # 【新增】初始困境 - 佛门困境
        'initial_dilemma': {
            'title': '酒肉穿肠过',
            'surface': '鲁智深因醉酒打伤了寺中僧人，方丈要罚他禁闭思过',
            'core_conflict': '欲望：追求自由自在、快意恩仇的生活 vs 现实：身为僧人需守清规戒律',
            'desire': '做一个行侠仗义的江湖人，而非困于寺中的和尚',
            'block': '他确实杀了人，佛门给了他庇护；但佛门清规与他的本性冲突不断'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神豪爽不羁。人物：鲁智深，40岁，大相国寺花和尚，魁梧壮硕的莽和尚，气质豪迈粗犷，身着破旧僧袍，络腮胡须，浓眉大眼。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, bold and righteous monk warrior'
    },
    {
        'name': '弥乐', 'gender': 'Male', 'age': 52,
        'power_type': '学', 'org_id': 'daxiangguo', 'org_role': 'MEMBER', 'org_rank': 2,
        'social_level': 1,
        'desc': '以算命为幌子的骗子和尚，喜欢偷偷吃肉。',
        'tags': ['LIAR', 'GREEDY', 'FORTUNE_TELLER'],
        'relations': {'LEADER': '鲁智深'},
        'wealth_level': 1, 'influence_level': 1,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '温和',      # 脾气：温和（表面和善）
            'spirit': '胆小',      # 胆量：胆小（怕事）
            'ism': '现实',         # 主义：现实（唯利是图）
            'act_style': '缜密',   # 风格：缜密（骗术需要心思）
            'friendship': '不重情义',  # 情义：不重情义（只认钱）
            'ambition': 40,        # 野心：中等（想发财）
            'desire_type': '财富', # 物欲类型
            'desire': '贪心'       # 物欲程度
        },
        # 【新增】初始困境 - 身份暴露危机
        'initial_dilemma': {
            'title': '假和尚的真麻烦',
            'surface': '弥乐骗了一位富商的钱，对方发现后带人来大相国寺要人',
            'core_conflict': '欲望：继续在大相国寺混吃混喝 vs 现实：骗子身份即将暴露',
            'desire': '保住大相国寺的庇护，继续他的算命生意',
            'block': '鲁智深最讨厌骗子，如果知道真相可能会把他扔出寺门'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神狡黠圆滑。人物：弥乐，52岁，大相国寺骗子和尚，油嘴滑舌的老滑头，气质猥琐市侩，身着僧袍但邋里邋遢，三角眼，山羊胡。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, cunning and greedy fake monk'
    },
    {
        'name': '阿禅', 'gender': 'Male', 'age': 8,
        'power_type': '学', 'org_id': 'daxiangguo', 'org_role': 'MEMBER', 'org_rank': 1,
        'social_level': 1,
        'desc': '身世凄惨的小沙弥，被街坊邻居养大。',
        'tags': ['KIND', 'ORPHAN', 'INNOCENT'],
        'relations': {},
        'wealth_level': 1, 'influence_level': 1,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '温和',      # 脾气：温和（天真善良）
            'spirit': '胆小',      # 胆量：胆小（年幼体弱）
            'ism': '理想',         # 主义：理想（相信世界美好）
            'act_style': '缜密',   # 风格：缜密（心思细腻）
            'friendship': '重情义',  # 情义：重情义（感恩养育他的人）
            'ambition': 15,        # 野心：很低（只想活下去）
            'desire_type': '亲情', # 物欲类型
            'desire': '一般'       # 物欲程度
        },
        # 【新增】初始困境 - 孤儿困境
        'initial_dilemma': {
            'title': '小沙弥的疑惑',
            'surface': '阿禅听到其他僧人议论他是被遗弃在寺门口的野孩子，开始怀疑自己的身世',
            'core_conflict': '欲望：知道自己的亲生父母是谁 vs 现实：可能永远无法得知真相',
            'desire': '找到亲生父母，或者接受大相国寺就是他的家',
            'block': '年幼的他既渴望亲情，又害怕知道真相后无法面对'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神纯真无邪。人物：阿禅，8岁，小沙弥，天真可爱的小和尚，气质纯真善良，身着小僧袍，光头，大眼睛，笑容腼腆。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, innocent and kind young monk boy'
    },

    # =============== 江湖势力 (游) ===============
    {
        'name': '洪小六', 'gender': 'Male', 'age': 20,
        'power_type': '游', 'org_id': 'beggar_gang', 'org_role': 'LEADER', 'org_rank': 2,
        'social_level': 1,
        'desc': '丐帮小头目，虽贫穷但热心肠，有江湖义气。',
        'tags': ['POOR', 'KIND', 'LOYAL', 'STREET_SMART'],
        'relations': {},
        'wealth_level': 1, 'influence_level': 2,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '温和',      # 脾气：温和（热心肠）
            'spirit': '勇敢',      # 胆量：勇敢（敢作敢当）
            'ism': '理想',         # 主义：理想（相信义气）
            'act_style': '豪放',   # 风格：豪放（江湖儿女）
            'friendship': '重情义',  # 情义：重情义（对兄弟讲义气）
            'ambition': 45,        # 野心：中等（想让丐帮壮大）
            'desire_type': '义气', # 物欲类型
            'desire': '一般'       # 物欲程度
        },
        # 【新增】初始困境 - 生存困境
        'initial_dilemma': {
            'title': '乞丐的尊严',
            'surface': '冬天将至，丐帮弟兄们缺衣少食，洪小六考虑是否要向富商低头乞讨',
            'core_conflict': '欲望：保持江湖儿女的骨气 vs 现实：弟兄们可能冻饿而死',
            'desire': '让丐帮弟兄们有口饭吃，有件衣服御寒',
            'block': '他不愿向欺压百姓的权贵低头，但普通百姓的施舍也有限'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神热情仗义。人物：洪小六，20岁，丐帮小头目，衣衫褴褛但精神饱满，气质豪爽热心，身着破旧乞丐装，蓬头但面带笑容。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, kind and loyal beggar youth'
    },
    
    # =============== 可招募的帮手 - 新手引导用 ===============
    {
        'name': '猎户张三', 'gender': 'Male', 'age': 28,
        'power_type': '游', 'org_id': None, 'org_role': None, 'org_rank': 0,
        'social_level': 1,
        'desc': '城外山林的猎户，为人仗义，箭术精湛。曾被黑风大王手下欺负过，对泼皮恶霸深恶痛绝。目前独居，以打猎为生。',
        'tags': ['HERO', 'JUSTICE', 'HUNTER', 'ARCHERY', 'RECRUITABLE'],
        'relations': {'ENEMY': '黑风大王'},
        'wealth_level': 1, 'influence_level': 1,
        'recruit_cost': 50,
        'recruit_condition': 'Q_FIND_ZHANGSAN',
        'combat_power': 3,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '暴躁',      # 脾气：暴躁（嫉恶如仇）
            'spirit': '勇敢',      # 胆量：勇敢（敢与恶势力对抗）
            'ism': '理想',         # 主义：理想（相信正义）
            'act_style': '豪放',   # 风格：豪放（江湖儿女）
            'friendship': '重情义',  # 情义：重情义（对朋友肝胆相照）
            'ambition': 40,        # 野心：中等（想保护弱小）
            'desire_type': '正义', # 物欲类型
            'desire': '一般'       # 物欲程度
        },
        # 【新增】初始困境 - 正义困境
        'initial_dilemma': {
            'title': '孤胆猎人',
            'surface': '张三发现黑风大王又在欺负山下的村民，但他知道单凭自己无法对抗整个黑风寨',
            'core_conflict': '欲望：为被欺负的村民讨回公道 vs 现实：势单力薄，可能白白送死',
            'desire': '找到志同道合的人，一起铲除黑风寨这个毒瘤',
            'block': '村民们都怕事不敢反抗，官府也被高府收买，他孤立无援'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神坚毅正义。人物：猎户张三，28岁，城外山林猎户，正直仗义的青年猎手，气质淳朴刚毅，身着兽皮猎装，肩背弓箭，皮肤黝黑。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, righteous hunter warrior'
    },

    # =============== 新增角色 - 增强社会分层 ===============
    
    # 更多朝廷官员
    {
        'name': '赵师爷', 'gender': 'Male', 'age': 55,
        'power_type': '士', 'org_id': 'kaifeng_fu', 'org_role': 'MEMBER', 'org_rank': 3,
        'social_level': 3,
        'desc': '开封府资深师爷，熟悉法典，阿谀奉承。',
        'tags': ['BUREAUCRAT', 'EXPERIENCED', 'SYCOPHANT'],
        'relations': {'LEADER': '方承意'},
        'wealth_level': 3, 'influence_level': 2,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '温和',      # 脾气：温和（表面和善）
            'spirit': '胆小',      # 胆量：胆小（怕得罪人）
            'ism': '现实',         # 主义：现实（官场生存法则）
            'act_style': '缜密',   # 风格：缜密（老谋深算）
            'friendship': '不重情义',  # 情义：不重情义（只认利益）
            'ambition': 50,        # 野心：中等（想保住位置）
            'desire_type': '权力', # 物欲类型
            'desire': '贪心'       # 物欲程度
        },
        # 【新增】初始困境 - 职场危机
        'initial_dilemma': {
            'title': '老臣的焦虑',
            'surface': '方承意上任后重用年轻人，赵师爷担心自己的位置不保',
            'core_conflict': '欲望：保住资深师爷的地位和体面 vs 现实：新上司不信任老臣',
            'desire': '证明老臣仍有价值，同时培养接班人确保后路',
            'block': '年轻人嫌他保守，上司嫌他圆滑，他夹在中间进退两难'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神谄媚老练。人物：赵师爷，55岁，开封府资深师爷，老谋深算的官场老油条，气质圆滑世故，身着青色官服，蓄着山羊胡，面带假笑。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, sycophant old bureaucrat'
    },
    
    # 更多护卫/军人
    {
        'name': '铁牛', 'gender': 'Male', 'age': 32,
        'power_type': '兵', 'org_id': 'kaifeng_fu', 'org_role': 'BODYGUARD', 'org_rank': 2,
        'social_level': 2,
        'desc': '府衙护卫队长，忠诚勇猛，保护重要官员。',
        'tags': ['LOYAL', 'STRONG', 'DUTIFUL'],
        'relations': {'COLLEAGUE': '林冲'},
        'wealth_level': 2, 'influence_level': 1,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '暴躁',      # 脾气：暴躁（武将本色）
            'spirit': '勇敢',      # 胆量：勇敢（忠诚勇猛）
            'ism': '理想',         # 主义：理想（忠君爱国）
            'act_style': '豪放',   # 风格：豪放（武将本色）
            'friendship': '重情义',  # 情义：重情义（对兄弟肝胆相照）
            'ambition': 40,        # 野心：中等（想建功立业）
            'desire_type': '荣誉', # 物欲类型
            'desire': '一般'       # 物欲程度
        },
        # 【新增】初始困境 - 忠诚困境
        'initial_dilemma': {
            'title': '护卫的良心',
            'surface': '铁牛发现方承意的一些命令有违正义，但作为护卫他必须服从',
            'core_conflict': '欲望：做一个正直的武士 vs 现实：身为护卫必须服从主公',
            'desire': '既能尽忠职守，又不违背内心的正义',
            'block': '方承意手段狠辣，有些命令让他良心不安，但背叛主公更是大逆不道'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神忠诚坚毅。人物：铁牛，32岁，府衙护卫队长，身材魁梧的忠诚卫士，气质刚毅可靠，身着铠甲，腰佩长刀，英武挺拔。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, loyal and strong guard captain'
    },
    
    # 更多商人
    {
        'name': '钱掌柜', 'gender': 'Male', 'age': 48,
        'power_type': '商', 'org_id': 'tianshui_alley', 'org_role': 'MEMBER', 'org_rank': 3,
        'social_level': 2,
        'desc': '布庄掌柜，精于算计，但讲求诚信。',
        'tags': ['MERCHANT', 'CALCULATING', 'HONEST_BUSINESS'],
        'relations': {'LEADER': '郁芊芊'},
        'wealth_level': 3, 'influence_level': 2,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '温和',      # 脾气：温和（和气生财）
            'spirit': '胆小',      # 胆量：胆小（怕得罪人）
            'ism': '现实',         # 主义：现实（商人本色）
            'act_style': '缜密',   # 风格：缜密（精于算计）
            'friendship': '重情义',  # 情义：重情义（对老客户有情有义）
            'ambition': 40,        # 野心：中等（想扩大生意）
            'desire_type': '财富', # 物欲类型
            'desire': '贪心'       # 物欲程度
        },
        # 【新增】初始困境 - 诚信困境
        'initial_dilemma': {
            'title': '诚信的代价',
            'surface': '钱掌柜发现一批布料有瑕疵，如果如实告知会损失一大笔钱，如果隐瞒可以大赚',
            'core_conflict': '欲望：坚持诚信经营 vs 现实：生意难做，需要这笔钱周转',
            'desire': '守住诚信的底线，同时不让布庄倒闭',
            'block': '郁芊芊整顿商会，对违规者严惩不贷，但他确实急需这笔钱救命'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神精明稳重。人物：钱掌柜，48岁，布庄掌柜，精打细算的诚信商人，气质稳重务实，身着绸缎长衫，头戴方巾，面带和善笑容。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, honest and calculating merchant'
    },
    
    # 底层民众
    {
        'name': '老李头', 'gender': 'Male', 'age': 60,
        'power_type': '农', 'org_id': None, 'org_role': None, 'org_rank': 0,
        'social_level': 1,
        'desc': '城郊老农，辛苦劳作，生活贫困。',
        'tags': ['POOR', 'HARDWORKING', 'SIMPLE'],
        'relations': {},
        'wealth_level': 1, 'influence_level': 0,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '温和',      # 脾气：温和（老实人）
            'spirit': '胆小',      # 胆量：胆小（怕惹事）
            'ism': '现实',         # 主义：现实（只求温饱）
            'act_style': '缜密',   # 风格：缜密（种地需要耐心）
            'friendship': '重情义',  # 情义：重情义（对邻里友善）
            'ambition': 10,        # 野心：很低（只想活下去）
            'desire_type': '安定', # 物欲类型
            'desire': '一般'       # 物欲程度
        },
        # 【新增】初始困境 - 生存困境
        'initial_dilemma': {
            'title': '老农的无奈',
            'surface': '高大胜奉高衙内之命来收租，老李头今年的收成不好，交不起租子',
            'core_conflict': '欲望：保住祖传的几亩薄田 vs 现实：天灾人祸，无力交租',
            'desire': '能有个安稳的晚年，不给儿女添麻烦',
            'block': '高衙内催租催得紧，官府也被收买不为百姓做主，他走投无路'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神沧桑朴实。人物：老李头，60岁，城郊老农，饱经风霜的贫苦农民，气质朴实憨厚，身着破旧短打，皮肤黝黑，满脸皱纹。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, weathered hardworking old farmer'
    },
    
    {
        'name': '小翠', 'gender': 'Female', 'age': 16,
        'power_type': '工', 'org_id': None, 'org_role': None, 'org_rank': 0,
        'social_level': 1,
        'desc': '绣房女工，手艺精巧，希望有朝一日开个绣庄。',
        'tags': ['HARDWORKING', 'SKILLFUL', 'AMBITIOUS'],
        'relations': {},
        'wealth_level': 1, 'influence_level': 0,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '温和',      # 脾气：温和（温柔善良）
            'spirit': '勇敢',      # 胆量：勇敢（敢于追梦）
            'ism': '理想',         # 主义：理想（相信努力就有回报）
            'act_style': '缜密',   # 风格：缜密（绣工需要耐心）
            'friendship': '重情义',  # 情义：重情义（对帮助过她的人感恩）
            'ambition': 65,        # 野心：较高（想开绣庄）
            'desire_type': '事业', # 物欲类型
            'desire': '贪心'       # 物欲程度
        },
        # 【新增】初始困境 - 梦想困境
        'initial_dilemma': {
            'title': '绣娘的梦想',
            'surface': '小翠攒了三年的钱准备开绣庄，但房东突然涨租，资金不够了',
            'core_conflict': '欲望：靠手艺改变命运，开自己的绣庄 vs 现实：底层女子创业艰难，处处碰壁',
            'desire': '靠自己的绣活手艺，在汴京闯出一片天地',
            'block': '没有背景没有本钱，绣房老板还想把她培养成接班人，不愿放她走'
        },
        'avatar_prompt': '国漫古风女性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神憧憬坚定。人物：小翠，16岁，绣房女工，勤劳上进的年轻绣娘，气质温柔坚韧，身着素色布衣，手持绣针，目光充满希望。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, hardworking ambitious young craftswoman'
    },

    # =============== 盗匪势力 (匪) ===============
    # 【核心设定】黑风大王，本名王老虎，是黑风寨寨主
    # 黑风寨表面是山贼，实际暗中受高府资助，替高衙内办见不得人的事
    {
        'name': '黑风大王', 'gender': 'Male', 'age': 35,
        'power_type': '匪', 'org_id': 'heifeng_zhai', 'org_role': 'LEADER', 'org_rank': 5,
        'social_level': 3,
        'desc': '黑风寨大当家，本名王老虎，江湖人称"黑风大王"。表面是占山为王的山贼头子，实则暗中受高府资助，在城内外横行霸道，替高衙内做脏活。',
        'tags': ['VILLAIN', 'STRONG', 'RUTHLESS', 'BANDIT_CHIEF', 'GAO_PUPPET'],
        'relations': {'SUBORDINATE': '泼皮牛二', 'SECRET_BACKER': '高衙内'},
        'wealth_level': 2, 'influence_level': 2,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '暴躁',      # 脾气：暴躁（恶霸本色）
            'spirit': '勇敢',      # 胆量：勇敢（敢作敢为）
            'ism': '现实',         # 主义：现实（利益至上）
            'act_style': '豪放',   # 风格：豪放（行事张扬）
            'friendship': '不重情义',  # 情义：不重情义（只认利益）
            'ambition': 70,        # 野心：较高（想扩大势力）
            'desire_type': '权力', # 物欲类型
            'desire': '贪心'       # 物欲程度
        },
        # 【新增】初始困境 - 身份困境
        'initial_dilemma': {
            'title': '傀儡的觉醒',
            'surface': '高衙内命令黑风大王去绑架一位朝廷命官的家眷，这会让他成为朝廷通缉的要犯',
            'core_conflict': '欲望：摆脱高府的控制，真正自立为王 vs 现实：没有高府的资助，黑风寨无法维持',
            'desire': '既能保持黑风寨的独立，又不失去高府这个金主',
            'block': '高衙内越来越过分的要求让他骑虎难下，反抗意味着毁灭，顺从意味着万劫不复'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神凶狠霸道。人物：黑风大王（王老虎），35岁，黑风寨大当家，满脸横肉的恶霸头子，气质残暴嚣张，身着虎皮袄，腰挂大刀，面目狰狞。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, ruthless bandit chief with scarred face'
    },
    {
        'name': '山贼甲', 'gender': 'Male', 'age': 25,
        'power_type': '匪', 'org_id': 'heifeng_zhai', 'org_role': 'MEMBER', 'org_rank': 1,
        'social_level': 1,
        'desc': '黑风寨喽啰，听命于黑风大王。',
        'tags': ['VILLAIN', 'SIMPLE', 'FOLLOWER'],
        'relations': {'LEADER': '黑风大王'},
        'wealth_level': 1, 'influence_level': 1,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '暴躁',      # 脾气：暴躁（本性凶恶）
            'spirit': '胆小',      # 胆量：胆小（欺软怕硬）
            'ism': '现实',         # 主义：现实（只为混口饭吃）
            'act_style': '豪放',   # 风格：豪放（行事鲁莽）
            'friendship': '不重情义',  # 情义：不重情义（见风使舵）
            'ambition': 30,        # 野心：低（只想活下去）
            'desire_type': '财富', # 物欲类型
            'desire': '贪心'       # 物欲程度
        },
        # 【新增】初始困境 - 生存困境
        'initial_dilemma': {
            'title': '喽啰的觉悟',
            'surface': '山贼甲听说官府要围剿黑风寨，考虑是否要逃跑',
            'core_conflict': '欲望：离开黑风寨，重新做人 vs 现实：没有一技之长，离开也是死路一条',
            'desire': '能有个安稳的生计，不再过刀口舔血的日子',
            'block': '他犯过太多事，官府不会放过他，黑风大王也不会放他走'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神愚钝凶恶。人物：山贼甲，25岁，黑风寨小喽啰，面目可憎的杂兵，气质粗鄙愚蠢，身着破烂布衣，手持木棍，獐头鼠目。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, ugly bandit minion'
    },
    {
        'name': '山贼乙', 'gender': 'Male', 'age': 28,
        'power_type': '匪', 'org_id': 'heifeng_zhai', 'org_role': 'MEMBER', 'org_rank': 1,
        'social_level': 1,
        'desc': '黑风寨喽啰，跟着黑风大王混饭吃。',
        'tags': ['VILLAIN', 'SIMPLE', 'FOLLOWER'],
        'relations': {'LEADER': '黑风大王'},
        'wealth_level': 1, 'influence_level': 1,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '温和',      # 脾气：温和（本性懦弱）
            'spirit': '胆小',      # 胆量：胆小（欺软怕硬）
            'ism': '现实',         # 主义：现实（只为混口饭吃）
            'act_style': '缜密',   # 风格：缜密（小心翼翼）
            'friendship': '不重情义',  # 情义：不重情义（见风使舵）
            'ambition': 20,        # 野心：很低（只想活下去）
            'desire_type': '安定', # 物欲类型
            'desire': '一般'       # 物欲程度
        },
        # 【新增】初始困境 - 生存困境
        'initial_dilemma': {
            'title': '喽啰的悲哀',
            'surface': '山贼乙在黑风寨里总是被欺负，分到的赃物最少，还要做最危险的活',
            'core_conflict': '欲望：离开黑风寨，重新做人 vs 现实：胆小怕事，不敢逃跑',
            'desire': '能有个安稳的生计，不再被人欺负',
            'block': '他太胆小，既不敢反抗黑风大王，也不敢逃跑，只能继续忍气吞声'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神猥琐怯懦。人物：山贼乙，28岁，黑风寨小喽啰，畏畏缩缩的跟班，气质猥琐胆小，身着脏兮兮的旧衣，缩头缩脑，贼眉鼠眼。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, cowardly bandit follower'
    },
    {
        'name': '泼皮牛二', 'gender': 'Male', 'age': 33,
        'power_type': '匪', 'org_id': 'heifeng_zhai', 'org_role': 'MEMBER', 'org_rank': 2,
        'social_level': 1,
        'desc': '街头泼皮，黑风大王在城内的头号打手。好酒无赖，专门欺负老实人，负责收保护费、调戏妇女等脏活。',
        'tags': ['VILLAIN', 'DRUNK', 'BULLY', 'THUG'],
        'relations': {'PARTNER': '泼皮狗蛋', 'LEADER': '黑风大王'},
        'wealth_level': 1, 'influence_level': 0,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '暴躁',      # 脾气：暴躁（恶霸本色）
            'spirit': '胆小',      # 胆量：胆小（欺软怕硬）
            'ism': '现实',         # 主义：现实（享乐主义）
            'act_style': '豪放',   # 风格：豪放（行事张扬）
            'friendship': '不重情义',  # 情义：不重情义（只认利益）
            'ambition': 35,        # 野心：低（只想混吃混喝）
            'desire_type': '酒色', # 物欲类型
            'desire': '贪心'       # 物欲程度
        },
        # 【新增】初始困境 - 生存困境
        'initial_dilemma': {
            'title': '泼皮的末路',
            'surface': '牛二喝多了酒，调戏了高府的一个丫鬟，高衙内要拿他问罪',
            'core_conflict': '欲望：继续过欺软怕硬的泼皮生活 vs 现实：得罪了惹不起的人',
            'desire': '保住性命，继续他的泼皮生涯',
            'block': '高衙内比他还狠，黑风大王也不会为了他得罪高府'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神淫邪无赖。人物：泼皮牛二，33岁，街头泼皮，黑风大王的城内打手，气质下流无耻，身着邋遢短打，酒糟鼻，三角眼，一脸横肉。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, despicable drunken thug'
    },
    {
        'name': '泼皮狗蛋', 'gender': 'Male', 'age': 28,
        'power_type': '匪', 'org_id': 'heifeng_zhai', 'org_role': 'MEMBER', 'org_rank': 1,
        'social_level': 1,
        'desc': '牛二的跟班，脑子不好使但拳头硬。跟着牛二在城内欺压百姓。',
        'tags': ['VILLAIN', 'SIMPLE', 'FOLLOWER', 'THUG'],
        'relations': {'PARTNER': '泼皮牛二', 'LEADER': '黑风大王'},
        'wealth_level': 1, 'influence_level': 0,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '暴躁',      # 脾气：暴躁（本性凶恶）
            'spirit': '胆小',      # 胆量：胆小（欺软怕硬）
            'ism': '现实',         # 主义：现实（只听牛二的）
            'act_style': '豪放',   # 风格：豪放（行事鲁莽）
            'friendship': '重情义',  # 情义：重情义（对牛二忠心）
            'ambition': 20,        # 野心：很低（只想跟着牛二混）
            'desire_type': '酒肉', # 物欲类型
            'desire': '贪心'       # 物欲程度
        },
        # 【新增】初始困境 - 生存困境
        'initial_dilemma': {
            'title': '跟班的悲哀',
            'surface': '狗蛋发现牛二得罪了高衙内，可能会被处死，他不知该跟着牛二还是另寻出路',
            'core_conflict': '欲望：继续跟着牛二混吃混喝 vs 现实：牛二可能自身难保',
            'desire': '能继续有酒有肉，不用自己动脑子',
            'block': '他太笨，没有牛二带着，他连怎么欺负人都不知道'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神呆滞凶蛮。人物：泼皮狗蛋，28岁，牛二的跟班，四肢发达头脑简单的打手，气质愚钝蛮横，身着破旧短褂，肌肉发达，表情呆滞。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, dumb strong henchman'
    },
    
    # 青狼帮
    {
        'name': '青狼', 'gender': 'Male', 'age': 32,
        'power_type': '匪', 'org_id': 'qinglang_bang', 'org_role': 'LEADER', 'org_rank': 5,
        'social_level': 3,
        'desc': '青狼帮大当家，狡猾阴险，善于伏击。',
        'tags': ['VILLAIN', 'SMART', 'RUTHLESS', 'BANDIT_CHIEF'],
        'relations': {},
        'wealth_level': 2, 'influence_level': 2,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '温和',      # 脾气：温和（表面和善）
            'spirit': '勇敢',      # 胆量：勇敢（敢作敢为）
            'ism': '现实',         # 主义：现实（利益至上）
            'act_style': '缜密',   # 风格：缜密（狡猾阴险）
            'friendship': '不重情义',  # 情义：不重情义（只认利益）
            'ambition': 75,        # 野心：较高（想吞并其他山寨）
            'desire_type': '权力', # 物欲类型
            'desire': '贪心'       # 物欲程度
        },
        # 【新增】初始困境 - 扩张困境
        'initial_dilemma': {
            'title': '狼王的野心',
            'surface': '青狼想吞并附近几个小山寨，但黑风大王背后有高府撑腰，不好下手',
            'core_conflict': '欲望：成为汴京周边最大的山贼势力 vs 现实：黑风寨有官府背景，硬碰硬会吃亏',
            'desire': '找到黑风寨的弱点，一举吞并或瓦解他们',
            'block': '黑风大王虽然鲁莽，但高府的庇护让青狼帮投鼠忌器'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神阴狠狡诈。人物：青狼，32岁，青狼帮大当家，阴险狡诈的山贼首领，气质阴鸷狠毒，身着狼皮披风，眼神如狼般凶狠，面带刀疤。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, cunning wolf-like bandit leader'
    },
    {
        'name': '铁塔', 'gender': 'Male', 'age': 35,
        'power_type': '匪', 'org_id': 'qinglang_bang', 'org_role': 'MEMBER', 'org_rank': 3,
        'social_level': 2,
        'desc': '青狼帮二当家，力大无穷。',
        'tags': ['VILLAIN', 'STRONG', 'SIMPLE'],
        'relations': {'LEADER': '青狼'},
        'wealth_level': 1, 'influence_level': 1,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '暴躁',      # 脾气：暴躁（本性凶恶）
            'spirit': '勇敢',      # 胆量：勇敢（力大无穷）
            'ism': '现实',         # 主义：现实（只听青狼的）
            'act_style': '豪放',   # 风格：豪放（行事鲁莽）
            'friendship': '重情义',  # 情义：重情义（对青狼忠心）
            'ambition': 30,        # 野心：低（只想跟着青狼混）
            'desire_type': '酒肉', # 物欲类型
            'desire': '贪心'       # 物欲程度
        },
        # 【新增】初始困境 - 忠诚困境
        'initial_dilemma': {
            'title': '二当家的烦恼',
            'surface': '铁塔发现青狼为了扩张势力，不惜出卖帮中兄弟，他不知该继续追随还是提醒兄弟们',
            'core_conflict': '欲望：对青狼忠心耿耿 vs 现实：青狼的野心可能害死帮中兄弟',
            'desire': '既能忠于大哥，又能保护帮中兄弟',
            'block': '他脑子笨，分不清青狼的做法是对是错，只知道大哥说啥他做啥'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神蛮横愚钝。人物：铁塔，35岁，青狼帮二当家，身材魁梧如铁塔的壮汉，气质粗暴蛮横，身着厚重铠甲，肌肉虬结，面无表情。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, brutish strongman enforcer'
    },
    {
        'name': '瘦猴', 'gender': 'Male', 'age': 22,
        'power_type': '匪', 'org_id': 'qinglang_bang', 'org_role': 'MEMBER', 'org_rank': 1,
        'social_level': 1,
        'desc': '青狼帮探子，身手灵活，负责打探消息。',
        'tags': ['VILLAIN', 'AGILE', 'SCOUT'],
        'relations': {'LEADER': '青狼'},
        'wealth_level': 1, 'influence_level': 1,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '温和',      # 脾气：温和（表面和善）
            'spirit': '胆小',      # 胆量：胆小（欺软怕硬）
            'ism': '现实',         # 主义：现实（只为混口饭吃）
            'act_style': '缜密',   # 风格：缜密（探子需要心思）
            'friendship': '不重情义',  # 情义：不重情义（见风使舵）
            'ambition': 40,        # 野心：中等（想往上爬）
            'desire_type': '财富', # 物欲类型
            'desire': '贪心'       # 物欲程度
        },
        # 【新增】初始困境 - 身份困境
        'initial_dilemma': {
            'title': '探子的两难',
            'surface': '瘦猴打探到官府即将围剿青狼帮的消息，他不知该如实汇报还是趁机逃跑',
            'core_conflict': '欲望：立功受赏，在帮中地位提升 vs 现实：青狼帮可能覆灭，留下来是死路一条',
            'desire': '既能保住性命，又能从这次危机中获利',
            'block': '背叛青狼会被追杀，但留下来可能被官府抓去砍头'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神机警鬼祟。人物：瘦猴，22岁，青狼帮探子，瘦小灵活的侦察兵，气质鬼祟机警，身着紧身夜行衣，尖嘴猴腮，目光闪烁。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, sneaky agile scout'
    },

    # 骆驼帮
    {
        'name': '骆大', 'gender': 'Male', 'age': 40,
        'power_type': '匪', 'org_id': 'luopo_gang', 'org_role': 'LEADER', 'org_rank': 5,
        'social_level': 2,
        'desc': '骆驼帮头目，专劫商队，手段毒辣。',
        'tags': ['VILLAIN', 'GREEDY', 'RUTHLESS', 'BANDIT_CHIEF'],
        'relations': {},
        'wealth_level': 2, 'influence_level': 1,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '暴躁',      # 脾气：暴躁（本性凶恶）
            'spirit': '勇敢',      # 胆量：勇敢（敢作敢为）
            'ism': '现实',         # 主义：现实（利益至上）
            'act_style': '缜密',   # 风格：缜密（专劫商队需要计划）
            'friendship': '不重情义',  # 情义：不重情义（只认利益）
            'ambition': 65,        # 野心：较高（想扩大势力）
            'desire_type': '财富', # 物欲类型
            'desire': '贪心'       # 物欲程度
        },
        # 【新增】初始困境 - 生存困境
        'initial_dilemma': {
            'title': '马贼的末路',
            'surface': '骆驼帮最近几次劫掠都扑了空，兄弟们开始怀疑骆大的能力',
            'core_conflict': '欲望：维持骆驼帮的势力和自己的地位 vs 现实：商队开始绕道，生意越来越难做',
            'desire': '找到新的财路，重振骆驼帮的声威',
            'block': '官府加强了官道巡逻，其他山寨也在抢地盘，骆驼帮腹背受敌'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神贪婪阴毒。人物：骆大，40岁，骆驼帮头目，专劫商队的马贼首领，气质阴毒贪婪，身着沙漠游牧服饰，满脸风霜，目光阴狠。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, greedy desert bandit chief'
    },
    {
        'name': '骆二', 'gender': 'Male', 'age': 35,
        'power_type': '匪', 'org_id': 'luopo_gang', 'org_role': 'MEMBER', 'org_rank': 2,
        'social_level': 1,
        'desc': '骆驼帮喽啰，骆大的亲弟弟。',
        'tags': ['VILLAIN', 'SIMPLE', 'FOLLOWER'],
        'relations': {'LEADER': '骆大'},
        'wealth_level': 1, 'influence_level': 1,
        # 【新增】仿太阁5性格维度
        'personality': {
            'temper': '温和',      # 脾气：温和（本性懦弱）
            'spirit': '胆小',      # 胆量：胆小（欺软怕硬）
            'ism': '现实',         # 主义：现实（只听哥哥的）
            'act_style': '缜密',   # 风格：缜密（小心翼翼）
            'friendship': '重情义',  # 情义：重情义（对哥哥忠心）
            'ambition': 25,        # 野心：很低（只想跟着哥哥混）
            'desire_type': '安定', # 物欲类型
            'desire': '一般'       # 物欲程度
        },
        # 【新增】初始困境 - 家庭困境
        'initial_dilemma': {
            'title': '弟弟的担忧',
            'surface': '骆二发现哥哥骆大最近越来越暴躁，对兄弟们动辄打骂，他担心哥哥会众叛亲离',
            'core_conflict': '欲望：帮助哥哥维持骆驼帮 vs 现实：哥哥的做法正在失去人心',
            'desire': '让哥哥冷静下来，重新赢得兄弟们的信任',
            'block': '他不敢违逆哥哥，但又看着哥哥一步步走向毁灭'
        },
        'avatar_prompt': '国漫古风男性头像，《秦时明月》×《雾山五行》融合美术风格，2D手绘平涂，硬朗利落线条，高对比光影，色彩干净高级，面部清晰精致，眼神愚忠盲从。人物：骆二，35岁，骆驼帮喽啰，骆大的亲弟弟，对哥哥唯命是从的跟班，气质愚钝盲从，身着破旧游牧装，面带谄笑。方形构图，游戏UI头像规格，纯白色背景，高清精致，只显示肩部及以上，脸部微侧向左，无文字，边缘锐利干净。game UI icon, headshot only, 128×128, clean sharp edges, white background, 2D flat color, cel shading, sharp line art, high contrast lighting, Chinese anime style, beautiful detailed face, clear eyes, blindly loyal bandit follower'
    }
]

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
