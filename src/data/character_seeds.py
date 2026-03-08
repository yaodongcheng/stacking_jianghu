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
