# --- tools/make_event_csv.py ---
"""
AI事件配置生成器 - 支持动态剧情对话

新版设计：
1. 事件可以有开场对话（intro_dialog_id）
2. 每个选项可以有后续对话（dialog_a/b/c_id）
3. 对话数据在独立的 event_dialog_config.csv 中配置
4. 支持动作演出、角色对话、分支剧情
"""
import csv
import os

os.makedirs('../data', exist_ok=True)
filepath = '../data/event_data.csv'
dialog_filepath = '../data/event_dialog_config.csv'

# 扩充 Header，增加对话关联字段
# 总列数：23列
headers = [
    ['id', 'title', 'desc_template', 'type', 'tag_main', 'tag_target', 
     'intro_dialog_id',  # 新增：开场对话ID
     'btn_a', 'eff_a', 'req_a', 'chain_a', 'dialog_a_id',  # 新增：选项A后续对话
     'btn_b', 'eff_b', 'req_b', 'chain_b', 'dialog_b_id',  # 新增：选项B后续对话
     'btn_c', 'eff_c', 'req_c', 'chain_c', 'dialog_c_id',  # 新增：选项C后续对话
     'weight'],
    ['int', 'str', 'str', 'enum', 'str', 'str', 
     'str',
     'str', 'str', 'str', 'str', 'str',
     'str', 'str', 'str', 'str', 'str',
     'str', 'str', 'str', 'str', 'str',
     'int'],
    ['ID', '标题', '描述', '类型', '主角标签', '配角标签', 
     '开场对话',
     '选项A', '效果A', '需求A', '连锁A', '对话A',
     '选项B', '效果B', '需求B', '连锁B', '对话B',
     '选项C', '效果C', '需求C', '连锁C', '对话C',
     '权重'],
]

# 对话配置表头
dialog_headers = [
    ['dialog_id', 'speaker', 'text', 'action'],
    ['str', 'str', 'str', 'str'],
    ['对话组ID', '说话人', '文本内容', '动作指令']
]

# 格式约定：
# intro_dialog_id: 事件开场对话组ID（可选，不填则无开场剧情）
# dialog_a/b/c_id: 选择该选项后播放的对话组ID（可选）
# A: 冤大头/资源消耗/常规善行
# B: 门客/特殊依赖/黑化选项
# C: 自身能力/保底/拒绝/中立

events = [
    # ==========================================
    # --- 600系列：门客专属高权重事件 (三选一) - 带动态剧情演示 ---
    # ==========================================
    # 示例：收保护费事件，带完整对话剧情
    [601, '收保护费', '地痞流氓围住了 {A} 的摊位，扬言不交钱就砸摊子。', 'CHOICE', 'MERCHANT', 'ANY',
     'E601_INTRO',  # 开场对话
     '替他交钱(破财)', 'PLAYER:Money:-100;SELF:emotion:DEPRESSED;PLAYER:Fame:20', 'MONEY:100', '', 'E601_A',
     '关门放打手(需打手)', 'PLAYER:Fame:150;SELF:emotion:HAPPY;SELF:money:50', 'FOLLOWER:THUG', '', 'E601_B', 
     '亲自武力驱逐(需恶名)', 'PLAYER:Fame:100;PLAYER:AddTag:THUG', 'FAME:-100', '', 'E601_C', 
     20],

    [602, '官府查账', '税务官突然造访 {A} 的店铺，吹毛求疵意图索贿。', 'CHOICE', 'MERCHANT', 'ANY',
     'E602_INTRO',  # 开场对话
     '帮忙塞红包(贿赂)', 'PLAYER:Money:-200;SELF:safety:NORMAL', 'MONEY:200', '', 'E602_A',
     '让文人辩法(需文人)', 'PLAYER:Fame:150;SELF:eco_status:RICH;PLAYER:AddTag:JUSTICE', 'FOLLOWER:SCHOLAR', '', 'E602_B',
     '袖手旁观(无视)', 'SELF:money:-300;SELF:emotion:ANGRY', '', '', '', 
     20],

    [603, '农田虫害', '农夫 {A} 看着满地蝗虫欲哭无泪，今年的收成要完了。', 'CHOICE', 'FARMER', 'ANY',
     'E603_INTRO',
     '资助买药(善举)', 'PLAYER:Money:-50;SELF:inventory:GRAIN:5', 'MONEY:50', '', 'E603_A',
     '科学除虫(需科学家)', 'PLAYER:Fame:200;SELF:inventory:GRAIN:15;SELF:emotion:HAPPY', 'FOLLOWER:SCIENTIST', '', 'E603_B',
     '烧香祈福(迷信)', 'PLAYER:Fame:-10;SELF:emotion:NORMAL', '', '', 'E603_C',
     20],
     
    [604, '恶霸欺市', '{A} 在市场被恶霸欺负，敢怒不敢言。', 'CHOICE', 'MERCHANT', 'ANY',
     'E604_INTRO',
     '花钱摆平', 'PLAYER:Money:-100;SELF:safety:NORMAL', 'MONEY:100', '', 'E604_A',
     '路见不平(需打手)', 'PLAYER:Fame:150;SELF:money:20;SELF:emotion:HAPPY', 'FOLLOWER:THUG', '', 'E604_B',
     '大声呵斥(需名望)', 'PLAYER:Fame:50;SELF:emotion:NORMAL', 'FAME:500', '', 'E604_C', 
     15],

    # ==========================================
    # --- 100系列：经济类 (改造版 - 两难抉择) ---
    # ==========================================
    # 设计原则：每个选项都有代价，不存在"安全逃生"
    
    [101, '交子贬值', '{A} 持旧交子去钱庄兑换被拒，急得要跳河。钱庄老板 {B} 看热闹不嫌事大。', 'CHOICE', 'POOR', 'MERCHANT', 
     'E101_INTRO',
     '原价兑换(破财)', 'PLAYER:Money:-200;PLAYER:Fame:100;SELF:emotion:GRATEFUL;SELF:affinity:PLAYER:50', 'MONEY:200', '', 'E101_A',
     '低价收割(趁人之危)', 'PLAYER:Money:300;PLAYER:Fame:-150;PLAYER:AddTag:PROFITEER;SELF:emotion:DESPAIR;SELF:affinity:PLAYER:-50', '', '', 'E101_B',
     '怒斥钱庄(得罪富商)', 'PLAYER:Fame:80;PLAYER:AddTag:JUSTICE;SELF:emotion:HAPPY;OTHER:affinity:PLAYER:-80;OTHER:tags:ENEMY', '', '', 'E101_C',
     10],
     
    [102, '汴京买房梦', '书生 {A} 每日打三份工只为买房，如今积劳成疾，命悬一线。他跪求你借他最后一笔钱凑齐首付。', 'CHOICE', 'POOR', 'ANY',
     'E102_INTRO',
     '借他钱(成全执念)', 'PLAYER:Money:-800;SELF:emotion:HAPPY;SELF:hp:50;PLAYER:Fame:100', 'MONEY:800', '', 'E102_A',
     '劝他放弃(残忍真相)', 'PLAYER:Fame:-50;SELF:emotion:DESPAIR;SELF:tags:LAY_FLAT;SELF:affinity:PLAYER:-30', '', '', 'E102_B',
     '送他去医(先活下来)', 'PLAYER:Money:-300;PLAYER:Fame:50;SELF:hp:80;SELF:tags:INDEBTED;SELF:emotion:SAD', 'MONEY:300', '', 'E102_C',
     10],
     
    [103, '甜水巷内卷', '新来的舞姬 {A} 才艺出众价格低廉，老牌花魁 {B} 准备联合行会将她逐出。两人都向你求助。', 'CHOICE', 'DANCER', 'DANCER',
     'E103_INTRO',
     '保护新人(得罪行会)', 'PLAYER:Money:-150;PLAYER:Fame:80;PLAYER:AddTag:FAIR;SELF:affinity:PLAYER:60;SELF:safety:NORMAL;OTHER:affinity:PLAYER:-80;OTHER:tags:ENEMY', 'MONEY:150', '', 'E103_A',
     '支持老人(帮凶)', 'PLAYER:Money:200;PLAYER:Fame:-100;PLAYER:AddTag:BULLY;SELF:safety:EXILE;SELF:emotion:DESPAIR;OTHER:affinity:PLAYER:50;OTHER:eco_status:RICH', '', '', 'E103_B',
     '撮合合作(各退一步)', 'PLAYER:Fame:50;SELF:affinity:PLAYER:20;SELF:eco_status:ENOUGH;OTHER:affinity:PLAYER:20;OTHER:eco_status:ENOUGH', '', '', 'E103_C',
     10],

    [104, '瓦舍裁员', '老琴师 {A} 被瓦舍无故辞退且不给遣散费。他是三十年的老员工，如今老无所依。瓦舍老板是你的债主 {B}。', 'CHOICE', 'MUSICIAN', 'MERCHANT',
     'E104_INTRO',
     '出资聘请(收留)', 'PLAYER:Money:-400;PLAYER:Fame:150;SELF:is_follower:True;SELF:emotion:GRATEFUL;OTHER:affinity:PLAYER:-20', 'MONEY:400', '', 'E104_A',
     '替老板说话(讨好债主)', 'PLAYER:Fame:-100;SELF:emotion:DESPAIR;SELF:eco_status:POOR;OTHER:affinity:PLAYER:30', '', '', 'E104_B',
     '仗义执言(得罪债主)', 'PLAYER:Fame:200;PLAYER:AddTag:JUSTICE;SELF:money:100;SELF:emotion:HAPPY;OTHER:affinity:PLAYER:-60', '', '', 'E104_C',
     8],

    [105, '高利贷陷阱', '妇人 {A} 借驴打滚买首饰，如今利滚利，债主要卖她女儿抵债。债主 {B} 是本地恶霸。', 'CHOICE', 'POOR', 'THUG',
     'E105_INTRO',
     '代为还债(散财)', 'PLAYER:Money:-600;PLAYER:Fame:200;SELF:safety:NORMAL;SELF:emotion:GRATEFUL;SELF:affinity:PLAYER:80', 'MONEY:600', '', 'E105_A',
     '买下女儿(获得奴仆)', 'PLAYER:Money:-200;PLAYER:Fame:-50;SELF:emotion:DESPAIR;SELF:family:BROKEN', 'MONEY:200', '', 'E105_B',
     '暴力抗债(结仇恶霸)', 'PLAYER:Fame:100;PLAYER:AddTag:JUSTICE;SELF:safety:NORMAL;OTHER:affinity:PLAYER:-100;OTHER:tags:ENEMY;PLAYER:safety:DANGER', 'FOLLOWER:THUG', '', 'E105_C',
     10],

    [106, '学徒剥削', '铁匠铺师傅以"学艺"为由，三年不给学徒 {A} 分文。师傅 {B} 是你的老熟人。', 'CHOICE', 'POOR', 'CRAFTSMAN',
     'E106_INTRO',
     '为学徒出头(得罪熟人)', 'PLAYER:Fame:150;PLAYER:AddTag:JUSTICE;SELF:emotion:HAPPY;SELF:affinity:PLAYER:60;OTHER:affinity:PLAYER:-80', '', '', 'E106_A',
     '支持师傅(传统规矩)', 'PLAYER:Fame:-80;SELF:emotion:DEPRESSED;SELF:tags:SLAVE_MIND;OTHER:affinity:PLAYER:30', '', '', 'E106_B',
     '挖墙脚(带走学徒)', 'PLAYER:Money:-100;SELF:is_follower:True;SELF:affinity:PLAYER:40;OTHER:affinity:PLAYER:-100;OTHER:tags:ENEMY', 'MONEY:100', '', 'E106_C',
     8],

    [107, '虚假宣传', '郎中 {A} 的假药害死了寡妇的儿子。寡妇 {B} 当街跪求你主持公道。{A} 曾救过你的命。', 'CHOICE', 'DOCTOR', 'POOR',
     'E107_INTRO',
     '包庇郎中(还人情)', 'PLAYER:Fame:-200;PLAYER:AddTag:ACCOMPLICE;SELF:affinity:PLAYER:50;OTHER:emotion:DESPAIR;OTHER:affinity:PLAYER:-100', '', '', 'E107_A',
     '揭发郎中(恩将仇报)', 'PLAYER:Fame:200;PLAYER:AddTag:JUSTICE;SELF:freedom:PRISON;SELF:affinity:PLAYER:-100;OTHER:emotion:HAPPY', '', '', 'E107_B',
     '私了赔偿(和稀泥)', 'PLAYER:Money:-300;PLAYER:Fame:50;SELF:affinity:PLAYER:-30;SELF:eco_status:POOR;OTHER:emotion:SAD', 'MONEY:300', '', 'E107_C',
     8],

    [108, '合同诈骗', '不识字的脚夫 {A} 被骗签了卖身契。行骗者 {B} 背后是本城最大的人牙子。', 'CHOICE', 'POOR', 'THUG',
     'E108_INTRO',
     '撕毁契约(得罪黑帮)', 'PLAYER:Fame:200;PLAYER:AddTag:JUSTICE;PLAYER:safety:DANGER;SELF:freedom:FULL;SELF:affinity:PLAYER:80;OTHER:affinity:PLAYER:-100', '', '', 'E108_A',
     '买下脚夫(花钱了事)', 'PLAYER:Money:-300;PLAYER:Fame:-30;SELF:is_follower:True;SELF:freedom:SERVANT;OTHER:affinity:PLAYER:20', 'MONEY:300', '', 'E108_B',
     '假装没看见(明哲保身)', 'PLAYER:Fame:-100;SELF:freedom:SLAVE;SELF:emotion:DESPAIR;SELF:affinity:PLAYER:-50', '', '', 'E108_C',
     8],

    [109, '关扑成瘾', '赌徒 {A} 输光家产，赌坊老板 {B} 要他卖儿卖女抵债。{A} 跪求你救他一命。', 'CHOICE', 'GAMBLER', 'MERCHANT',
     'E109_INTRO',
     '替他还债(养虎为患)', 'PLAYER:Money:-500;PLAYER:Fame:50;SELF:emotion:HAPPY;SELF:tags:ADDICTED;SELF:affinity:PLAYER:30', 'MONEY:500', '', 'E109_A',
     '砸了赌坊(惹祸上身)', 'PLAYER:Fame:200;PLAYER:AddTag:JUSTICE;PLAYER:safety:DANGER;SELF:safety:NORMAL;OTHER:affinity:PLAYER:-100;OTHER:tags:ENEMY', 'FOLLOWER:THUG', '', 'E109_B',
     '买下孩子(保住血脉)', 'PLAYER:Money:-200;PLAYER:Fame:-50;SELF:family:BROKEN;SELF:emotion:SAD', 'MONEY:200', '', 'E109_C',
     10],

    # ==========================================
    # --- 200系列：家庭伦理 (改造版 - 两难抉择) ---
    # ==========================================
    # 设计原则：家庭矛盾无完美解，每个选择都会伤害某一方
    
    [201, '天价聘礼', '穷书生 {A} 凑不齐聘礼，女方父亲 {B} 扬言三日内不交钱就退婚另嫁。{A}已准备卖身为奴。', 'CHOICE', 'POOR', 'RICH',
     'E201_INTRO',
     '资助聘礼(散财)', 'PLAYER:Money:-800;PLAYER:Fame:200;SELF:emotion:GRATEFUL;SELF:affinity:PLAYER:80;OTHER:affinity:PLAYER:30', 'MONEY:800', '', 'E201_A',
     '说服退婚(棒打鸳鸯)', 'PLAYER:Fame:50;SELF:emotion:DESPAIR;SELF:tags:HEARTBROKEN;OTHER:affinity:PLAYER:50;OTHER:emotion:HAPPY', '', '', 'E201_B',
     '借他高利贷(埋雷)', 'PLAYER:Money:200;PLAYER:Fame:-100;SELF:safety:DANGER;SELF:affinity:PLAYER:-30', '', '', 'E201_C',
     10],

    [202, '赘婿的尊严', '赘婿 {A} 被岳家当狗使唤。他私下告诉你，岳父 {B} 暗中贪污，他手握证据想要翻身。', 'CHOICE', 'HUSBAND', 'RICH',
     'E202_INTRO',
     '协助揭发(正义)', 'PLAYER:Fame:200;PLAYER:AddTag:JUSTICE;SELF:emotion:HAPPY;SELF:eco_status:RICH;OTHER:freedom:PRISON;OTHER:affinity:PLAYER:-100', '', '', 'E202_A',
     '劝他隐忍(保全)', 'PLAYER:Fame:-50;SELF:emotion:DEPRESSED;SELF:tags:COWARD;OTHER:affinity:PLAYER:20', '', '', 'E202_B',
     '两边勒索(黑吃黑)', 'PLAYER:Money:500;PLAYER:Fame:-200;PLAYER:AddTag:BLACKMAILER;SELF:affinity:PLAYER:-50;OTHER:affinity:PLAYER:-80', '', '', 'E202_C',
     10],

    [203, '扶弟魔', '丈夫 {A} 发现妻子偷光积蓄给了弟弟 {B}。{A}要休妻，{B}威胁要打断{A}的腿。你是他们的邻居兼债主。', 'CHOICE', 'HUSBAND', 'THUG',
     'E203_INTRO',
     '支持丈夫(休妻)', 'PLAYER:Fame:50;SELF:emotion:ANGRY;SELF:affinity:PLAYER:30;OTHER:affinity:PLAYER:-80;OTHER:emotion:ANGRY', '', '', 'E203_A',
     '支持弟弟(亲情)', 'PLAYER:Fame:-50;SELF:emotion:SAD;SELF:affinity:PLAYER:-50;OTHER:affinity:PLAYER:30', '', '', 'E203_B',
     '要回欠款(债务优先)', 'PLAYER:Money:300;PLAYER:Fame:-30;SELF:affinity:PLAYER:-30;OTHER:eco_status:POOR;OTHER:affinity:PLAYER:-30', '', '', 'E203_C',
     8],

    [204, '假名媛拼单', '女子 {A} 拼单租借名贵首饰参加诗会，不慎弄丢。首饰主人 {B} 是你的生意伙伴，价值千金。', 'CHOICE', 'POOR', 'MERCHANT',
     'E204_INTRO',
     '替她赔偿(冤大头)', 'PLAYER:Money:-500;PLAYER:Fame:100;SELF:emotion:GRATEFUL;SELF:affinity:PLAYER:80;OTHER:affinity:PLAYER:20', 'MONEY:500', '', 'E204_A',
     '让她卖身抵债', 'PLAYER:Fame:-100;SELF:freedom:SLAVE;SELF:emotion:DESPAIR;OTHER:affinity:PLAYER:30;OTHER:emotion:HAPPY', '', '', 'E204_B',
     '私下找回(暗箱操作)', 'PLAYER:Money:-200;PLAYER:Fame:50;SELF:emotion:HAPPY;OTHER:affinity:PLAYER:-50;OTHER:tags:CHEATED', 'MONEY:200', '', 'E204_C',
     8],

    [205, '指腹为婚', '富家女 {A} 爱上穷书生，却被父亲强迫嫁给太尉之子 {B}。太尉之子是个纨绔，但得罪太尉后果严重。', 'CHOICE', 'RICH', 'NOBLE',
     'E205_INTRO',
     '协助私奔(得罪太尉)', 'PLAYER:Fame:100;PLAYER:safety:DANGER;SELF:emotion:HAPPY;SELF:family:ISOLATED;OTHER:affinity:PLAYER:-100;OTHER:tags:ENEMY', '', '', 'E205_A',
     '劝她认命(明哲保身)', 'PLAYER:Fame:-50;SELF:emotion:DESPAIR;SELF:affinity:PLAYER:-60;OTHER:affinity:PLAYER:30', '', '', 'E205_B',
     '揭发太尉之子(风险极高)', 'PLAYER:Fame:300;PLAYER:AddTag:BRAVE;PLAYER:safety:DANGER;SELF:emotion:HAPPY;OTHER:freedom:PRISON', 'FOLLOWER:SCHOLAR', '', 'E205_C',
     8],

    [206, '抛妻弃子', '新科状元 {A} 要休掉糟糠之妻 {B}。{A}曾是你资助的穷书生，{B}是你的远房表妹。', 'CHOICE', 'SCHOLAR', 'WIFE',
     'E206_INTRO',
     '写文揭露(毁他前程)', 'PLAYER:Fame:200;SELF:soc_status:LOW;SELF:tags:HYPOCRITE;SELF:affinity:PLAYER:-100;OTHER:emotion:HAPPY;OTHER:affinity:PLAYER:50', '', '', 'E206_A',
     '收受贿赂(助纣为虐)', 'PLAYER:Money:800;PLAYER:Fame:-300;PLAYER:AddTag:CORRUPT;SELF:affinity:PLAYER:30;OTHER:emotion:DESPAIR;OTHER:affinity:PLAYER:-100', '', '', 'E206_B',
     '调解复合(和事佬)', 'PLAYER:Fame:100;SELF:affinity:PLAYER:-20;SELF:emotion:ANGRY;OTHER:emotion:SAD;OTHER:affinity:PLAYER:20', '', '', 'E206_C',
     8],

    [207, '重男轻女', '媳妇 {A} 被婆婆逼迫连续生育，身体已垮。婆婆 {B} 是你母亲的故交，曾照顾过你的童年。', 'CHOICE', 'WIFE', 'OLD',
     'E207_INTRO',
     '强行带走媳妇(得罪长辈)', 'PLAYER:Fame:150;PLAYER:AddTag:COMPASSION;SELF:hp:NORMAL;SELF:emotion:GRATEFUL;SELF:affinity:PLAYER:80;OTHER:affinity:PLAYER:-100', '', '', 'E207_A',
     '劝媳妇忍耐(保守)', 'PLAYER:Fame:-100;SELF:hp:POOR;SELF:emotion:DESPAIR;SELF:affinity:PLAYER:-50;OTHER:affinity:PLAYER:30', '', '', 'E207_B',
     '出钱请医调理(折中)', 'PLAYER:Money:-300;PLAYER:Fame:50;SELF:hp:ENOUGH;SELF:affinity:PLAYER:30;OTHER:affinity:PLAYER:-20', 'MONEY:300', '', 'E207_C',
     8],

    [208, '断袖疑云', '知名侠客 {A} 被传与书童 {B} 关系暧昧。{A}是你的救命恩人，正遭到江湖围攻。{B}其实是女扮男装的官家千金。', 'CHOICE', 'HERO', 'DANCER',
     'E208_INTRO',
     '揭露真相(女扮男装)', 'PLAYER:Fame:100;SELF:emotion:ANGRY;SELF:affinity:PLAYER:-30;OTHER:safety:DANGER;OTHER:family:ISOLATED', '', '', 'E208_A',
     '力挺恩人(不惧流言)', 'PLAYER:Fame:-150;PLAYER:AddTag:LOYAL;SELF:emotion:HAPPY;SELF:affinity:PLAYER:80;OTHER:emotion:HAPPY', '', '', 'E208_B',
     '沉默旁观(明哲保身)', 'PLAYER:Fame:-30;SELF:emotion:SAD;SELF:affinity:PLAYER:-40;OTHER:emotion:NORMAL', '', '', 'E208_C',
     8],

    # ==========================================
    # --- 300系列：社会乱象 (改造版 - 两难抉择) ---
    # ==========================================
    # 设计原则：公共事件中，帮谁都会得罪另一方
    
    [301, '当街碰瓷', '老人 {A} 倒在马车前哀嚎，车主 {B} 是你的债主。围观群众义愤填膺，但你怀疑老人是职业碰瓷。', 'CHOICE', 'OLD', 'MERCHANT',
     'E301_INTRO',
     '送医赔钱(帮老人)', 'PLAYER:Money:-300;PLAYER:Fame:150;SELF:emotion:HAPPY;SELF:affinity:PLAYER:50;OTHER:affinity:PLAYER:-50', 'MONEY:300', '', 'E301_A',
     '替债主说话(帮车主)', 'PLAYER:Fame:-100;SELF:emotion:ANGRY;SELF:affinity:PLAYER:-80;OTHER:affinity:PLAYER:50', '', '', 'E301_B',
     '当众揭穿(需医生)', 'PLAYER:Fame:100;SELF:tags:LIAR;SELF:emotion:DESPAIR;SELF:affinity:PLAYER:-100;OTHER:affinity:PLAYER:30', 'FOLLOWER:DOCTOR', '', 'E301_C',
     12],

    [302, '造谣一张嘴', '外乡人 {A} 被谣传是江洋大盗。造谣者 {B} 是本地富商，你的重要客户。{A}已走投无路。', 'CHOICE', 'POOR', 'MERCHANT',
     'E302_INTRO',
     '收留外乡人(得罪客户)', 'PLAYER:Fame:100;SELF:safety:NORMAL;SELF:is_follower:True;SELF:affinity:PLAYER:80;OTHER:affinity:PLAYER:-80', '', '', 'E302_A',
     '驱逐外乡人(讨好客户)', 'PLAYER:Fame:-80;SELF:safety:EXILE;SELF:emotion:DESPAIR;SELF:affinity:PLAYER:-100;OTHER:affinity:PLAYER:40', '', '', 'E302_B',
     '查明真相(需文人)', 'PLAYER:Fame:150;SELF:emotion:HAPPY;SELF:affinity:PLAYER:60;OTHER:freedom:PRISON;OTHER:affinity:PLAYER:-100', 'FOLLOWER:SCHOLAR', '', 'E302_C',
     10],

    [303, '熊孩子作恶', '小孩划坏了画家 {B} 的名贵字画。家长 {A} 是你的老相识，拒不赔偿还撒泼打滚。', 'CHOICE', 'RICH', 'SCHOLAR',
     'E303_INTRO',
     '替相识赔偿(破财)', 'PLAYER:Money:-200;PLAYER:Fame:50;SELF:affinity:PLAYER:30;SELF:tags:SHAMELESS;OTHER:emotion:SAD;OTHER:affinity:PLAYER:40', 'MONEY:200', '', 'E303_A',
     '替画家讨公道(得罪相识)', 'PLAYER:Fame:100;SELF:affinity:PLAYER:-80;SELF:emotion:ANGRY;OTHER:emotion:HAPPY;OTHER:affinity:PLAYER:60', '', '', 'E303_B',
     '各打五十大板(和稀泥)', 'PLAYER:Fame:-30;SELF:affinity:PLAYER:-30;OTHER:affinity:PLAYER:-30', '', '', 'E303_C',
     10],

    [304, '流浪狗风波', '爱狗人士 {A} 喂养的流浪狗咬伤了孩童。孩童父亲 {B} 要求打死狗并索赔。双方各有支持者。', 'CHOICE', 'POOR', 'THUG',
     'E304_INTRO',
     '支持打狗赔钱', 'PLAYER:Fame:80;SELF:emotion:SAD;SELF:affinity:PLAYER:-60;OTHER:emotion:HAPPY;OTHER:affinity:PLAYER:50', '', '', 'E304_A',
     '保护狗主人', 'PLAYER:Fame:-50;PLAYER:Money:-200;SELF:emotion:HAPPY;SELF:affinity:PLAYER:60;OTHER:affinity:PLAYER:-80;OTHER:emotion:ANGRY', 'MONEY:200', '', 'E304_B',
     '建立收容所(根治)', 'PLAYER:Money:-500;PLAYER:Fame:200;SELF:affinity:PLAYER:40;OTHER:affinity:PLAYER:30', 'MONEY:500', '', 'E304_C',
     8],

    [305, '插队冲突', '壮汉 {A} 在你的施粥铺前插队。被插队的 {B} 是怀孕妇人，当场晕倒。', 'CHOICE', 'THUG', 'WIFE',
     'E305_INTRO',
     '武力教训壮汉', 'PLAYER:Fame:150;SELF:hp:POOR;SELF:emotion:ANGRY;SELF:affinity:PLAYER:-100;OTHER:emotion:HAPPY;OTHER:affinity:PLAYER:60', '', '', 'E305_A',
     '多给一份(息事宁人)', 'PLAYER:Fame:-50;SELF:tags:GREEDY;SELF:affinity:PLAYER:20;OTHER:emotion:SAD;OTHER:affinity:PLAYER:-30', '', '', 'E305_B',
     '送孕妇就医', 'PLAYER:Money:-150;PLAYER:Fame:100;SELF:emotion:NORMAL;OTHER:hp:NORMAL;OTHER:affinity:PLAYER:80', 'MONEY:150', '', 'E305_C',
     10],

    [306, '噪音扰民', '铁匠 {A} 半夜打铁赶工，因为要还你的债。书生 {B} 神经衰弱，明日就是大考。', 'CHOICE', 'CRAFTSMAN', 'SCHOLAR',
     'E306_INTRO',
     '让铁匠停工(损失债务)', 'PLAYER:Fame:50;SELF:eco_status:POOR;SELF:affinity:PLAYER:-50;OTHER:emotion:HAPPY;OTHER:affinity:PLAYER:50', '', '', 'E306_A',
     '让书生忍耐(保债务)', 'PLAYER:Fame:-50;SELF:affinity:PLAYER:30;OTHER:hp:POOR;OTHER:affinity:PLAYER:-80;OTHER:tags:FAILED', '', '', 'E306_B',
     '资助书生搬家', 'PLAYER:Money:-100;PLAYER:Fame:80;SELF:affinity:PLAYER:20;OTHER:affinity:PLAYER:60;OTHER:emotion:HAPPY', 'MONEY:100', '', 'E306_C',
     8],

    [307, '地域歧视', '本地人 {A} 嘲笑外地客商 {B} 的口音，并开始动手。{A}是你的远房亲戚，{B}是你的合作伙伴。', 'CHOICE', 'THUG', 'MERCHANT',
     'E307_INTRO',
     '帮亲戚(护短)', 'PLAYER:Fame:-80;SELF:emotion:HAPPY;SELF:affinity:PLAYER:50;OTHER:safety:DANGER;OTHER:affinity:PLAYER:-100', '', '', 'E307_A',
     '帮伙伴(公道)', 'PLAYER:Fame:100;PLAYER:AddTag:JUSTICE;SELF:emotion:ANGRY;SELF:affinity:PLAYER:-80;OTHER:affinity:PLAYER:60', '', '', 'E307_B',
     '报官(两边得罪)', 'PLAYER:Fame:30;SELF:affinity:PLAYER:-40;SELF:freedom:PRISON;OTHER:affinity:PLAYER:-20', '', '', 'E307_C',
     8],

    [308, '杀猪盘', '貌美女子 {A} 正在骗老人 {B} 的棺材本。老人{B}是你已故恩师的遗孀，女子{A}是你门客的妹妹。', 'CHOICE', 'BEAUTIFUL', 'OLD',
     'E308_INTRO',
     '当面揭穿(得罪门客)', 'PLAYER:Fame:150;SELF:tags:LIAR;SELF:affinity:PLAYER:-100;OTHER:emotion:HAPPY;OTHER:affinity:PLAYER:80', '', '', 'E308_A',
     '私下收买(花钱了事)', 'PLAYER:Money:-300;PLAYER:Fame:30;SELF:affinity:PLAYER:20;OTHER:emotion:NORMAL', 'MONEY:300', '', 'E308_B',
     '装作不知(明哲保身)', 'PLAYER:Fame:-100;SELF:eco_status:RICH;OTHER:emotion:DESPAIR;OTHER:affinity:PLAYER:-50', '', '', 'E308_C',
     8],

    [309, '假冒官差', '假官差 {A} 正在勒索摊贩 {B}。{A}是你小时候的玩伴，落魄至此；{B}是你生意上的竞争对手。', 'CHOICE', 'THUG', 'MERCHANT',
     'E309_INTRO',
     '揭发玩伴(大义灭亲)', 'PLAYER:Fame:200;SELF:freedom:PRISON;SELF:affinity:PLAYER:-100;OTHER:affinity:PLAYER:50', '', '', 'E309_A',
     '协助玩伴(落井下石)', 'PLAYER:Money:100;PLAYER:Fame:-150;PLAYER:AddTag:ACCOMPLICE;SELF:affinity:PLAYER:50;OTHER:eco_status:POOR;OTHER:affinity:PLAYER:-80', '', '', 'E309_B',
     '放走玩伴(私放)', 'PLAYER:Fame:-50;SELF:affinity:PLAYER:30;SELF:safety:EXILE;OTHER:affinity:PLAYER:-30', '', '', 'E309_C',
     8],

    [310, '道德绑架', '乞丐 {A} 当众指责你为富不仁。旁边的富商 {B} 看热闹，正是你想攀附的大人物。', 'CHOICE', 'POOR', 'RICH',
     'E310_INTRO',
     '大方施舍(做面子)', 'PLAYER:Money:-200;PLAYER:Fame:100;SELF:emotion:HAPPY;SELF:affinity:PLAYER:40;OTHER:affinity:PLAYER:30', 'MONEY:200', '', 'E310_A',
     '厉声呵斥(显威严)', 'PLAYER:Fame:-50;SELF:emotion:SAD;SELF:affinity:PLAYER:-60;OTHER:affinity:PLAYER:50;OTHER:emotion:HAPPY', '', '', 'E310_B',
     '视而不见(冷漠)', 'PLAYER:Fame:-80;SELF:emotion:DESPAIR;OTHER:affinity:PLAYER:-30', '', '', 'E310_C',
     10],

    # ==========================================
    # --- 400系列：江湖恩怨 (改造版 - 两难抉择) ---
    # ==========================================
    # 设计原则：江湖事件涉及生死、恩仇，选择更加残酷
    
    [401, '金盆洗手难', '杀手 {A} 想退隐，组织 {B} 以其家人性命相逼。{A}曾救过你的命，{B}的首领是你的债主。', 'CHOICE', 'THUG', 'EVIL',
     'E401_INTRO',
     '协助灭门(报恩)', 'PLAYER:Money:-500;PLAYER:Fame:300;PLAYER:safety:DANGER;SELF:freedom:FULL;SELF:is_follower:True;SELF:affinity:PLAYER:100;OTHER:affinity:PLAYER:-100', 'MONEY:500', '', 'E401_A',
     '出卖恩人(领赏)', 'PLAYER:Money:800;PLAYER:Fame:-400;PLAYER:AddTag:TRAITOR;SELF:safety:DEAD;SELF:affinity:PLAYER:-100;OTHER:affinity:PLAYER:50', '', '', 'E401_B',
     '送他远走(两不相帮)', 'PLAYER:Fame:-50;SELF:family:ISOLATED;SELF:affinity:PLAYER:30;OTHER:affinity:PLAYER:-50', '', '', 'E401_C',
     8],

    [402, '秘籍争夺', '一本秘籍引发 {A} 和 {B} 的械斗。{A}是你的门客，{B}是你的生意伙伴。秘籍其实是假的。', 'CHOICE', 'FOLLOWER', 'MERCHANT',
     'E402_INTRO',
     '帮门客抢夺', 'PLAYER:Fame:-100;SELF:emotion:HAPPY;SELF:affinity:PLAYER:50;OTHER:hp:POOR;OTHER:affinity:PLAYER:-100', '', '', 'E402_A',
     '帮伙伴抢夺', 'PLAYER:Fame:-100;SELF:hp:POOR;SELF:affinity:PLAYER:-80;OTHER:emotion:HAPPY;OTHER:affinity:PLAYER:50', '', '', 'E402_B',
     '揭穿假秘籍(需学者)', 'PLAYER:Fame:150;SELF:emotion:ANGRY;SELF:affinity:PLAYER:-30;OTHER:emotion:ANGRY;OTHER:affinity:PLAYER:-30', 'FOLLOWER:SCHOLAR', '', 'E402_C',
     8],

    [403, '镖局失信', '镖局弄丢了寡妇 {A} 的传家宝。镖局总镖头 {B} 是你的结拜兄弟，寡妇{A}是你已故好友的遗孀。', 'CHOICE', 'POOR', 'HERO',
     'E403_INTRO',
     '为寡妇索赔(得罪兄弟)', 'PLAYER:Fame:200;PLAYER:AddTag:JUSTICE;SELF:eco_status:ENOUGH;SELF:affinity:PLAYER:80;OTHER:affinity:PLAYER:-80', '', '', 'E403_A',
     '替兄弟说话(亏欠遗孀)', 'PLAYER:Fame:-100;SELF:emotion:DESPAIR;SELF:affinity:PLAYER:-80;OTHER:affinity:PLAYER:50', '', '', 'E403_B',
     '自掏腰包赔偿', 'PLAYER:Money:-400;PLAYER:Fame:100;SELF:affinity:PLAYER:50;OTHER:affinity:PLAYER:30', 'MONEY:400', '', 'E403_C',
     8],

    [404, '冒名顶替', '骗子 {A} 冒充大侠招摇撞骗。真正的大侠 {B} 要杀他。{A}是你失散多年的表弟。', 'CHOICE', 'LIAR', 'HERO',
     'E404_INTRO',
     '救表弟(得罪大侠)', 'PLAYER:Money:-100;PLAYER:Fame:-100;SELF:is_follower:True;SELF:affinity:PLAYER:60;OTHER:affinity:PLAYER:-80', 'MONEY:100', '', 'E404_A',
     '袖手旁观(表弟死)', 'PLAYER:Fame:30;SELF:safety:DEAD;OTHER:affinity:PLAYER:30;OTHER:emotion:HAPPY', '', '', 'E404_B',
     '说情饶命(苦求大侠)', 'PLAYER:Fame:50;SELF:safety:EXILE;SELF:affinity:PLAYER:40;OTHER:affinity:PLAYER:-20', '', '', 'E404_C',
     8],

    [405, '黑吃黑', '{A} 与 {B} 交易违禁品，{A}埋伏了刀斧手准备黑吃黑。{A}是你的债主，{B}是你的救命恩人。', 'CHOICE', 'EVIL', 'MERCHANT',
     'E405_INTRO',
     '告密给{B}(救恩人)', 'PLAYER:Fame:100;SELF:affinity:PLAYER:-100;SELF:tags:ENEMY;OTHER:affinity:PLAYER:80;OTHER:safety:NORMAL', '', '', 'E405_A',
     '加入埋伏(帮债主)', 'PLAYER:Money:600;PLAYER:Fame:-400;PLAYER:AddTag:VILLAIN;SELF:affinity:PLAYER:50;OTHER:safety:DEAD', '', '', 'E405_B',
     '两边举报(正义)', 'PLAYER:Fame:300;PLAYER:Money:200;SELF:freedom:PRISON;SELF:affinity:PLAYER:-100;OTHER:freedom:PRISON;OTHER:affinity:PLAYER:-100', '', '', 'E405_C',
     8],

    # ==========================================
    # --- 500系列：超自然与荒诞 (已补全) ---
    # ==========================================
    [501, '时间穿越者', '疯子 {A} 满嘴"YYDS"、"绝绝子"，被官府抓捕。', 'CHOICE', 'CRAZY', 'ANY',
     'E501_INTRO',
     '保释他(老乡?)', 'PLAYER:Money:-300;PLAYER:Fame:0;SELF:tags:TIMETRAVELER;SELF:is_follower:True', 'MONEY:300', '', 'E501_A',
     '送去切片研究', 'PLAYER:Money:500;PLAYER:Fame:100;SELF:safety:DANGER', '', '', 'E501_B', 
     '听不懂(无视)', 'SELF:emotion:CONFUSED', '', '', 'E501_C',
     5],

    [502, '赛博机关人', '你发现 {A} 皮肤下竟然是齿轮和电线。', 'CHOICE', 'ANY', 'ANY',
     'E502_INTRO',
     '隐藏秘密(获得高达)', 'PLAYER:Fame:-100;SELF:tags:ROBOT;SELF:is_follower:True', '', '', 'E502_A',
     '当众拆解(需科学家)', 'PLAYER:Fame:300;SELF:safety:DANGER;PLAYER:AddTag:SCIENTIST', 'FOLLOWER:SCIENTIST', '', 'E502_B', 
     '以为眼花(无视)', 'SELF:emotion:NORMAL', '', '', 'E502_C',
     3],

    [503, '性别互换', '误食丹药，壮汉 {A} 变成了娇滴滴的女子。', 'CHOICE', 'STRONG', 'ANY',
     'E503_INTRO',
     '捧她做花魁', 'PLAYER:Money:1000;PLAYER:Fame:-200;SELF:eco_status:RICH;SELF:tags:DANCER', '', '', 'E503_A',
     '帮他寻找解药', 'PLAYER:Money:-500;PLAYER:Fame:200;SELF:tags:LOYAL', 'MONEY:500', '', 'E503_B', 
     '收为家丁(招募)', 'PLAYER:Money:-100;SELF:is_follower:True', 'MONEY:100', '', 'E503_C',
     5],

    [504, '古董成精', '传言 {A} 的传家宝夜里会说话，引来各路觊觎。', 'CHOICE', 'ANY', 'ANY',
     'E504_INTRO',
     '低价收购', 'PLAYER:Money:-200;PLAYER:Fame:-50;SELF:eco_status:ENOUGH', 'MONEY:200', '', 'E504_A',
     '辟谣保护', 'PLAYER:Fame:100;SELF:safety:NORMAL;SELF:emotion:HAPPY', '', '', 'E504_B', 
     '鉴定真伪(需学者)', 'PLAYER:Fame:150;PLAYER:Money:100', 'FOLLOWER:SCHOLAR', '', 'E504_C',
     8],

    [505, '甚至不是人', '路人 {A} 走路姿势僵硬，似乎是玩家上传的bug数据。', 'CHOICE', 'ANY', 'ANY',
     'E505_INTRO',
     '尝试修复(治疗)', 'PLAYER:Money:-100;PLAYER:Fame:50;SELF:emotion:NORMAL', 'MONEY:100', '', 'E505_A',
     '删除数据(暗杀)', 'PLAYER:Fame:-100;SELF:safety:DANGER', '', '', 'E505_B', 
     '提交工单(无视)', 'PLAYER:Fame:1', '', '', 'E505_C',
     2],
    # ==========================================
    # --- 600系列补充：入门级事件 ---
    # ==========================================
    [605, '叩阙求食', '流民 {A} 跪在城门外，衣衫褴褛，恳求施舍一口热粥。', 'CHOICE', 'NONE', 'ANY',
     'E605_INTRO',
     '开仓放粮(仁政)', 'PLAYER:inventory:GRAIN:-1;PLAYER:Fame:150;SELF:emotion:HAPPY;SELF:hp:100', 'ITEM:GRAIN', '', 'E605_A',
     '武力驱逐(酷吏)', 'PLAYER:Fame:50;SELF:safety:DANGER;SELF:tags:HATED;PLAYER:AddTag:CRUEL', '', '', 'E605_B', 
     '视而不见(冷漠)', 'PLAYER:Fame:-10;SELF:emotion:DESPAIR', '', '', 'E605_C', 
     30],

    # ==========================================
    # --- 700系列：核心困境事件 (真正的两难抉择) ---
    # 设计原则：
    # 1. 每个选项都有实质代价，不存在完美解
    # 2. 选择会触发实际的游戏状态变化（金钱、HP、关系、标签）
    # 3. 配套对话演出，言行一致
    # ==========================================
    
    # 700 【背叛困境】正义vs恩情 - 举报救命恩人
    [700, '【背叛困境】沉默的证人', 
     '你的门客 {A} 私下告诉你：你的商业伙伴 {B} 一直在走私禁品。而 {B} 曾在你最落魄时救过你的命。官府正在调查，若隐瞒可能受牵连。', 
     'DILEMMA', 'FOLLOWER', 'MERCHANT',
     'E700_INTRO',
     '如实举报(正义)', 'PLAYER:Fame:300;PLAYER:AddTag:JUSTICE;OTHER:freedom:SLAVE;OTHER:safety:EXILE;OTHER:affinity:PLAYER:-100', '', '', 'E700_A',
     '伪造证据脱罪', 'PLAYER:Fame:-200;PLAYER:AddTag:ACCOMPLICE;OTHER:affinity:PLAYER:50;PLAYER:Money:-500', 'MONEY:500', '', 'E700_B',
     '杀人灭口', 'PLAYER:Fame:-500;PLAYER:AddTag:VILLAIN;SELF:safety:DEAD;OTHER:emotion:NORMAL', '', '', 'E700_C',
     40],

    # 701 【牺牲困境】情义vs大局 - 只能救一人
    [701, '【牺牲困境】瘟疫来袭',
     '大疫封城，解药只够救一人。{A}是陪你出生入死的好友，{B}是能研制更多解药的神医。两人都已染病，神医若死，全城人将跟着陪葬。',
     'DILEMMA', 'FRIEND', 'DOCTOR',
     'E701_INTRO',
     '救好友(情义)', 'PLAYER:Fame:-100;PLAYER:AddTag:LOYAL;SELF:safety:NORMAL;SELF:hp:100;OTHER:safety:DEAD;PLAYER:AddTag:SELFISH', '', '', 'E701_A',
     '救神医(大局)', 'PLAYER:Fame:200;PLAYER:AddTag:RUTHLESS;SELF:safety:DEAD;SELF:affinity:PLAYER:-100;OTHER:safety:NORMAL;OTHER:is_follower:True', '', '', 'E701_B',
     '独吞解药(自保)', 'PLAYER:hp:100;PLAYER:Fame:-500;PLAYER:AddTag:COWARD;SELF:safety:DEAD;OTHER:safety:DEAD', '', '', 'E701_C',
     40],

    # 702 【大义困境】忠vs义 - 恩人成了叛军
    [702, '【大义困境】叛军头领',
     '你擒获叛军首领 {A}，他曾在你被追杀时冒死救你。朝廷悬赏千金，但{A}的部众扬言若官府处刑，便血洗全城平民。',
     'DILEMMA', 'REBEL', 'ANY',
     'E702_INTRO',
     '交给官府(忠)', 'PLAYER:Money:1000;PLAYER:Fame:500;PLAYER:AddTag:LOYAL_COURT;SELF:freedom:SLAVE;SELF:safety:EXECUTION;SELF:affinity:PLAYER:-100', '', '', 'E702_A',
     '放虎归山(义)', 'PLAYER:Fame:-300;PLAYER:AddTag:REBEL_FRIEND;SELF:affinity:PLAYER:100;SELF:safety:NORMAL;PLAYER:safety:WANTED', '', '', 'E702_B',
     '秘密处决', 'PLAYER:Fame:100;PLAYER:AddTag:PRAGMATIC;SELF:safety:DEAD;PLAYER:Money:0', '', '', 'E702_C',
     35],
    
    # 703 【打压困境】功臣震主 - 门客太强
    [703, '【打压困境】功臣震主',
     '你门下最得力的门客 {A} 声望日隆，在外的名声几乎盖过了你。有人密告他正在暗中笼络你的人脉，准备自立门户抢走你的生意。',
     'DILEMMA', 'FOLLOWER', 'ANY',
     'E703_INTRO',
     '找茬驱逐', 'PLAYER:Fame:-150;PLAYER:AddTag:TYRANT;SELF:is_follower:False;SELF:affinity:PLAYER:-100;SELF:emotion:ANGRY;SELF:tags:BETRAYED', '', '', 'E703_A',
     '委以重任(信任)', 'PLAYER:Fame:200;PLAYER:AddTag:MAGNANIMOUS;SELF:affinity:PLAYER:80;SELF:tags:LOYAL', '', '', 'E703_B',
     '暗中监视', 'PLAYER:Money:-300;SELF:emotion:NORMAL', 'MONEY:300', '', 'E703_C',
     35],
    
    # 704 【人情困境】被胁迫还人情 
    [704, '【人情困境】救命稻草',
     '你欠 {A} 一个天大的人情——当年他变卖家产救你于绝境。如今他落魄来求你：帮他打压诚实经营的竞争对手 {B}。若拒绝，他威胁将你当年的丑闻公之于众。',
     'DILEMMA', 'CREDITOR', 'MERCHANT',
     'E704_INTRO',
     '帮他打压{partner}', 'PLAYER:Fame:-200;PLAYER:AddTag:BULLY;OTHER:eco_status:POOR;OTHER:emotion:DESPAIR;SELF:affinity:PLAYER:50;SELF:emotion:HAPPY', '', '', 'E704_A',
     '断然拒绝(丑闻曝光)', 'PLAYER:Fame:-400;PLAYER:AddTag:SCANDAL;SELF:affinity:PLAYER:-80;OTHER:emotion:NORMAL', '', '', 'E704_B',
     '铤而走险(灭口)', 'PLAYER:Fame:-300;PLAYER:AddTag:ASSASSIN;SELF:safety:DEAD;OTHER:safety:NORMAL', '', '', 'E704_C',
     35],
    
    # 705 【复合困境】三角债 - 两个债主只能还一个
    [705, '【复合困境】三角债',
     '你同时欠 {A} 和 {B} 各五百两，但你只有五百两。{A}是你的救命恩人，{B}手握你贪赃枉法的证据。两人今日同时上门，必须当场做决定。',
     'DILEMMA', 'CREDITOR', 'CREDITOR',
     'E705_INTRO',
     '还给{npc}(恩情)', 'PLAYER:Money:-500;SELF:affinity:PLAYER:50;SELF:emotion:HAPPY;OTHER:affinity:PLAYER:-100;OTHER:emotion:ANGRY;PLAYER:AddTag:SCANDAL', 'MONEY:500', '', 'E705_A',
     '还给{partner}(保密)', 'PLAYER:Money:-500;SELF:affinity:PLAYER:-100;SELF:emotion:ANGRY;OTHER:affinity:PLAYER:30;OTHER:emotion:NORMAL', 'MONEY:500', '', 'E705_B',
     '宣布破产', 'PLAYER:Money:-500;PLAYER:Fame:-200;PLAYER:eco_status:POOR;SELF:emotion:SAD;OTHER:emotion:SAD;PLAYER:AddTag:SCANDAL', 'MONEY:500', '', 'E705_C',
     30],
    
    # 706 【道德困境】奴隶母子 - 只能买一个
    [706, '【道德困境】奴隶拍卖',
     '奴隶市场上，母子二人 {A} 正被分开贩卖。母亲声嘶力竭跪求你买下孩子，孩子年幼不懂事只知道哭喊要娘。你的钱只够买一人。',
     'DILEMMA', 'SLAVE', 'ANY',
     'E706_INTRO',
     '买母亲(劳动力)', 'PLAYER:Money:-300;PLAYER:Fame:50;SELF:freedom:SERVANT;SELF:emotion:DESPAIR;SELF:is_follower:True;SELF:tags:BROKEN', 'MONEY:300', '', 'E706_A',
     '买孩子(良心)', 'PLAYER:Money:-200;PLAYER:Fame:100;PLAYER:AddTag:COMPASSION', 'MONEY:200', '', 'E706_B',
     '放弃(无力回天)', 'PLAYER:Fame:-50;SELF:emotion:DESPAIR', '', '', 'E706_C',
     35],
    
    # 707 【知情困境】门客是逃犯
    [707, '【知情困境】致命秘密',
     '你偶然发现最信任的门客 {A} 其实是朝廷通缉的重犯，十年前杀过人。他对你忠心耿耿，但若被发现窝藏，你全家都要流放。',
     'DILEMMA', 'FOLLOWER', 'ANY',
     'E707_INTRO',
     '举报领赏', 'PLAYER:Money:800;PLAYER:Fame:200;SELF:freedom:SLAVE;SELF:safety:EXECUTION;SELF:affinity:PLAYER:-100', '', '', 'E707_A',
     '协助隐藏(庇护)', 'PLAYER:Fame:-100;PLAYER:AddTag:HARBORER;SELF:affinity:PLAYER:100;SELF:emotion:HAPPY;PLAYER:safety:DANGER', '', '', 'E707_B',
     '送他远走', 'PLAYER:Fame:0;SELF:is_follower:False;SELF:affinity:PLAYER:30;SELF:emotion:SAD;PLAYER:Money:-200', 'MONEY:200', '', 'E707_C',
     35],
    
    # 708 【继承困境】遗产分配 - 情vs法
    [708, '【继承困境】遗产纷争',
     '富商 {A} 临终托孤，将万贯家财交你分配。按律当归不孝长子，但 {A} 的遗愿是给在床前尽孝的次子 {B}。长子放言若不按律分，便告你侵吞。',
     'DILEMMA', 'RICH', 'ANY',
     'E708_INTRO',
     '按遗愿执行(情)', 'PLAYER:Fame:100;SELF:emotion:HAPPY;OTHER:affinity:PLAYER:50;PLAYER:safety:LAWSUIT', '', '', 'E708_A',
     '按律执行(法)', 'PLAYER:Fame:100;SELF:emotion:SAD;PLAYER:AddTag:LAWFUL;OTHER:emotion:ANGRY', '', '', 'E708_B',
     '私吞遗产', 'PLAYER:Money:2000;PLAYER:Fame:-500;PLAYER:AddTag:THIEF;SELF:emotion:DESPAIR;OTHER:affinity:PLAYER:-100', '', '', 'E708_C',
     25],

    # --- 999 保底 ---
    [999, '平静的一天', '虽然没有什么大事发生，但 {A} 看起来心情不错。', 'NEWS', 'ANY', 'ANY', '', '', '', '', '', '', '', '', '', '', '', '', 1]
]

# ═══════════════════════════════════════════════════════════════
# 事件对话配置
# ═══════════════════════════════════════════════════════════════
# 格式: [dialog_id, speaker, text, action]
# speaker支持: NARRATOR(旁白), SELF({A}), OTHER({B}), PLAYER(我), 或具体NPC名
# action支持: 空, SHOW_CHOICE(显示选择), 动作指令等

event_dialogs = [
    # --- E601: 收保护费 - 完整剧情示例 ---
    ['E601_INTRO', 'NARRATOR', '繁华的街市上，突然传来一阵骚动。', ''],
    ['E601_INTRO', 'NARRATOR', '几个泼皮地痞围住了{A}的摊位。', ''],
    ['E601_INTRO', 'SELF', '大爷...小的只是做点小生意糊口...', ''],
    ['E601_INTRO', '地痞头目', '少废话！这条街都是我们罩着的！', ''],
    ['E601_INTRO', '地痞头目', '今天要是不交保护费，就别想在这儿做生意！', ''],
    ['E601_INTRO', 'SELF', '可是...我真的拿不出那么多钱啊...', ''],
    ['E601_INTRO', 'NARRATOR', '围观的人群窃窃私语，但没人敢出头。', ''],
    ['E601_INTRO', 'NARRATOR', '你会怎么做？', 'SHOW_CHOICE'],
    
    # 选项A后续：替他交钱
    ['E601_A', 'PLAYER', '住手！这钱我替他出了！', ''],
    ['E601_A', '地痞头目', '哟，哪来的冤大头？', ''],
    ['E601_A', 'PLAYER', '拿着钱，别为难他了。', 'PLAYER:Money:-100'],
    ['E601_A', '地痞头目', '嘿嘿，识相！', ''],
    ['E601_A', 'SELF', '恩公大恩，小人没齿难忘！', 'SELF:emotion:HAPPY'],
    ['E601_A', 'NARRATOR', '周围的人对你的善举议论纷纷。', 'PLAYER:Fame:20'],
    
    # 选项B后续：放打手
    ['E601_B', 'PLAYER', '欺负老实人算什么本事？', ''],
    ['E601_B', 'PLAYER', '兄弟们，教训一下这些不长眼的！', ''],
    ['E601_B', 'NARRATOR', '你的打手上前，三下五除二将地痞打趴下。', 'NPC_ATTACK_THUGS'],
    ['E601_B', '地痞头目', '好汉饶命！我们有眼不识泰山！', ''],
    ['E601_B', 'SELF', '多谢大人相救！', 'SELF:emotion:HAPPY'],
    ['E601_B', 'NARRATOR', '你的威名传开了。', 'PLAYER:Fame:150'],
    
    # 选项C后续：亲自驱逐
    ['E601_C', 'PLAYER', '光天化日，竟敢如此放肆！', ''],
    ['E601_C', '地痞头目', '又来一个找死的？', ''],
    ['E601_C', 'NARRATOR', '你一脚将地痞踹倒，其他人见状落荒而逃。', 'PLAYER_KICK_THUG'],
    ['E601_C', 'SELF', '多谢壮士！', ''],
    ['E601_C', 'NARRATOR', '但周围有人认出你是那个臭名昭著的恶霸...', 'PLAYER:AddTag:THUG'],
    
    # --- E602: 官府查账 ---
    ['E602_INTRO', 'NARRATOR', '一名税务官带着随从来到{A}的店铺。', ''],
    ['E602_INTRO', '税务官', '例行检查，把账本拿来！', ''],
    ['E602_INTRO', 'SELF', '大人，这是小店的账本...', ''],
    ['E602_INTRO', '税务官', '嗯...这笔账有问题！', ''],
    ['E602_INTRO', 'SELF', '大人明鉴，小的绝无虚报！', ''],
    ['E602_INTRO', '税务官', '哼，到底有没有问题，还得看你的诚意。', ''],
    ['E602_INTRO', 'NARRATOR', '税务官摆明了是想要好处。你会如何应对？', 'SHOW_CHOICE'],
    
    ['E602_A', 'PLAYER', '大人辛苦，这是一点心意。', 'PLAYER:Money:-200'],
    ['E602_A', '税务官', '嗯，算你识相。账目没问题，走了。', ''],
    ['E602_A', 'SELF', '多谢大人通融...', 'SELF:safety:NORMAL'],
    
    ['E602_B', 'PLAYER', '大人请看，这账目确实没有问题。', ''],
    ['E602_B', 'NARRATOR', '你让文人帮忙据理力争，税务官无言以对。', ''],
    ['E602_B', '税务官', '哼，算你们走运！', ''],
    ['E602_B', 'SELF', '多谢恩公主持公道！', 'PLAYER:Fame:150'],
    
    # ═══════════════════════════════════════════════════════════════
    # 100系列：经济类事件对话
    # ═══════════════════════════════════════════════════════════════
    
    # --- E101: 交子贬值 ---
    ['E101_INTRO', 'NARRATOR', '钱庄门口围满了人，一个衣衫褴褛的男子正在哭喊。', ''],
    ['E101_INTRO', 'SELF', '我存了十年的积蓄啊！全在这旧交子上！', ''],
    ['E101_INTRO', 'OTHER', '（冷笑）谁让你不早来换？过期作废，概不负责。', ''],
    ['E101_INTRO', 'SELF', '你们这是吃人啊！我不活了！', ''],
    ['E101_INTRO', 'NARRATOR', '{A}挣脱人群，朝河边跑去。你恰好路过...', 'SHOW_CHOICE'],
    
    ['E101_A', 'PLAYER', '（拦住他）别冲动！我来帮你换！', ''],
    ['E101_A', 'NARRATOR', '你掏出银两，按原价兑换了他的旧交子。', 'PLAYER:Money:-200'],
    ['E101_A', 'SELF', '（跪地叩首）恩公大德，小人来世做牛做马报答您！', 'SELF:emotion:GRATEFUL'],
    ['E101_A', 'NARRATOR', '围观群众对你的善举交口称赞。', 'PLAYER:Fame:100'],
    
    ['E101_B', 'PLAYER', '（低声）这些旧交子，我可以收...不过只能按三成价。', ''],
    ['E101_B', 'SELF', '三成？可是...', ''],
    ['E101_B', 'PLAYER', '三成或者一文不值，你选。', ''],
    ['E101_B', 'NARRATOR', '{A}含泪将交子交给你。你转手便高价出售给了急需的商人...', 'PLAYER:Money:300'],
    ['E101_B', 'NARRATOR', '有人在背后指指点点：「趁火打劫的奸商！」', 'PLAYER:Fame:-150;PLAYER:AddTag:PROFITEER'],
    
    ['E101_C', 'PLAYER', '（指着钱庄老板）你们这是黑店！', ''],
    ['E101_C', 'OTHER', '你算什么东西，敢管老子的事？', ''],
    ['E101_C', 'PLAYER', '我是什么东西不重要，重要的是你这黑心钱庄，我记住了。', ''],
    ['E101_C', 'NARRATOR', '你替{A}出头，虽然钱没讨回来，但钱庄老板记下了你。', 'OTHER:affinity:PLAYER:-80;PLAYER:Fame:80'],
    
    # --- E102: 汴京买房梦 ---
    ['E102_INTRO', 'NARRATOR', '医馆门口，一个面色蜡黄的书生被人搀扶着走出。', ''],
    ['E102_INTRO', 'SELF', '（剧烈咳嗽）只差最后三百两...只差三百两我就能买到房了...', ''],
    ['E102_INTRO', 'NARRATOR', '他是{A}，连续三年打三份工，就为在汴京买套房。', ''],
    ['E102_INTRO', 'SELF', '（看到你）恩公！求您借我这笔钱！凑齐首付我就解脱了！', ''],
    ['E102_INTRO', 'NARRATOR', '郎中在一旁摇头：「再不休养，怕是活不过今年...」', 'SHOW_CHOICE'],
    
    ['E102_A', 'PLAYER', '（叹气）拿去吧...', 'PLAYER:Money:-800'],
    ['E102_A', 'SELF', '（狂喜）太好了！我终于能买房了！', 'SELF:emotion:HAPPY'],
    ['E102_A', 'NARRATOR', '他拿着钱，踉跄着往牙行跑去。你看着他的背影，不知该喜该忧。', ''],
    ['E102_A', 'NARRATOR', '三个月后，{A}在新房中咳血而亡...', 'SELF:hp:50'],
    
    ['E102_B', 'PLAYER', '（握住他的手）别买了。房子买了，人没了，有什么意义？', ''],
    ['E102_B', 'SELF', '（眼神涣散）不买房...活着有什么意义...', ''],
    ['E102_B', 'NARRATOR', '{A}失魂落魄地离去。此后再无买房的执念，却也失去了活下去的动力。', 'SELF:emotion:DESPAIR;SELF:tags:LAY_FLAT'],
    
    ['E102_C', 'PLAYER', '先把身体养好！我出钱给你治病。', 'PLAYER:Money:-300'],
    ['E102_C', 'SELF', '可是...我的房子...', ''],
    ['E102_C', 'PLAYER', '命都没了，要房子何用？', ''],
    ['E102_C', 'NARRATOR', '你强行将他送进医馆。{A}康复后，对你又感激又怨恨...', 'SELF:hp:80;SELF:emotion:SAD'],

    # --- E103: 甜水巷内卷 ---
    ['E103_INTRO', 'NARRATOR', '甜水巷的花楼里传来争吵声。', ''],
    ['E103_INTRO', 'SELF', '这条巷子是我们的地盘！容不下你这种贱货！', ''],
    ['E103_INTRO', 'OTHER', '（冷笑）姐姐年老色衰，怕被抢了饭碗？', ''],
    ['E103_INTRO', 'NARRATOR', '新来的舞姬{A}才艺出众、价格低廉，威胁到了老牌花魁{B}的生意。', ''],
    ['E103_INTRO', 'OTHER', '行会已经决定了，今晚就把你赶出去！', ''],
    ['E103_INTRO', 'NARRATOR', '两人都看向你，似乎在等你表态...', 'SHOW_CHOICE'],
    
    ['E103_A', 'PLAYER', '（站到{A}身前）欺负一个新来的姑娘算什么本事？', 'PLAYER:Money:-150'],
    ['E103_A', 'OTHER', '你...你要管这闲事？', ''],
    ['E103_A', 'PLAYER', '甜水巷的规矩，轮不到你来定。', ''],
    ['E103_A', 'NARRATOR', '你花钱摆平了行会，{A}得以留下。但{B}记住了这个仇...', 'SELF:affinity:PLAYER:60;OTHER:affinity:PLAYER:-80'],
    
    ['E103_B', 'PLAYER', '（对{A}摇头）这条巷子...不适合你。', ''],
    ['E103_B', 'SELF', '（绝望）您...您也要赶我走？', ''],
    ['E103_B', 'NARRATOR', '在你的默许下，{A}被赶出了甜水巷。', 'SELF:safety:EXILE;SELF:emotion:DESPAIR'],
    ['E103_B', 'OTHER', '（得意）多谢您仗义执言！', 'OTHER:affinity:PLAYER:50;PLAYER:Money:200'],
    
    ['E103_C', 'PLAYER', '这样吧，你们各退一步。{A}换个时段，{B}降点价。', ''],
    ['E103_C', 'NARRATOR', '两人虽然都不太满意，但总算勉强接受了。', ''],
    ['E103_C', 'SELF', '（勉强）...好吧。', 'SELF:affinity:PLAYER:20'],
    ['E103_C', 'OTHER', '（不情愿）算你公道...', 'OTHER:affinity:PLAYER:20'],
    
    # --- E104: 瓦舍裁员 ---
    ['E104_INTRO', 'NARRATOR', '瓦舍门口，一个老者抱着琴盒无助地坐在台阶上。', ''],
    ['E104_INTRO', 'SELF', '三十年了...说辞就辞，连遣散费都没有...', ''],
    ['E104_INTRO', 'NARRATOR', '他是{A}，瓦舍的老琴师。被辞退后，老无所依。', ''],
    ['E104_INTRO', 'OTHER', '（从里面走出）老家伙，还不走？碍眼！', ''],
    ['E104_INTRO', 'NARRATOR', '瓦舍老板{B}，恰好也是你的债主。', 'SHOW_CHOICE'],
    
    ['E104_A', 'PLAYER', '老先生，我这里正缺一位琴师。', 'PLAYER:Money:-400'],
    ['E104_A', 'SELF', '（老泪纵横）多谢恩公...多谢恩公！', 'SELF:is_follower:True;SELF:emotion:GRATEFUL'],
    ['E104_A', 'OTHER', '（阴阳怪气）呦，当冤大头呢？', 'OTHER:affinity:PLAYER:-20'],
    
    ['E104_B', 'PLAYER', '（对{A}摇头）这是人家的家务事，我不好插手。', ''],
    ['E104_B', 'SELF', '（绝望地低下头）...是啊，谁会管一个老家伙呢。', 'SELF:emotion:DESPAIR;SELF:eco_status:POOR'],
    ['E104_B', 'OTHER', '（满意地点头）还是你识大体。改天那笔账的事，好商量。', 'OTHER:affinity:PLAYER:30'],
    
    ['E104_C', 'PLAYER', '（上前一步）三十年的老员工，就这么扫地出门？', ''],
    ['E104_C', 'OTHER', '你管得着吗？', ''],
    ['E104_C', 'PLAYER', '你不给遣散费，我就让全汴京都知道你是怎么对待老员工的。', ''],
    ['E104_C', 'NARRATOR', '在你的施压下，{A}拿到了应有的补偿。但{B}的脸色，阴沉得可怕...', 'SELF:money:100;SELF:emotion:HAPPY;OTHER:affinity:PLAYER:-60'],
    
    # --- E105: 高利贷陷阱 ---
    ['E105_INTRO', 'NARRATOR', '街角传来女人的哭声。', ''],
    ['E105_INTRO', 'SELF', '求求你们...再宽限几天...', ''],
    ['E105_INTRO', 'OTHER', '（狞笑）宽限？利滚利，你还得起吗？', ''],
    ['E105_INTRO', 'OTHER', '把你女儿带走抵债！', ''],
    ['E105_INTRO', 'NARRATOR', '妇人{A}借了高利贷买首饰，如今利滚利，债主{B}要卖她女儿抵债。', ''],
    ['E105_INTRO', 'SELF', '不要！不要带走我的女儿！', 'SHOW_CHOICE'],
    
    ['E105_A', 'PLAYER', '欠多少？我替她还！', ''],
    ['E105_A', 'OTHER', '（看了看你）六百两。', ''],
    ['E105_A', 'PLAYER', '（掏钱）拿着，滚！', 'PLAYER:Money:-600'],
    ['E105_A', 'SELF', '（跪地叩首）恩公大德！恩公大德！', 'SELF:safety:NORMAL;SELF:emotion:GRATEFUL;SELF:affinity:PLAYER:80'],
    
    ['E105_B', 'PLAYER', '（低声）这女儿...卖给我如何？', ''],
    ['E105_B', 'OTHER', '（眼睛一亮）大人好眼光！二百两！', 'PLAYER:Money:-200'],
    ['E105_B', 'SELF', '（绝望）大人...您...', 'SELF:emotion:DESPAIR;SELF:family:BROKEN'],
    ['E105_B', 'NARRATOR', '你买下了她的女儿。至于是救她还是害她...只有天知道。', ''],
    
    ['E105_C', 'PLAYER', '放开她！', ''],
    ['E105_C', 'OTHER', '又来一个多管闲事的？', ''],
    ['E105_C', 'NARRATOR', '你唤出打手，将债主一顿暴打。', 'SELF:safety:NORMAL'],
    ['E105_C', 'OTHER', '（被打翻在地）好...好...你给我记住！', 'OTHER:affinity:PLAYER:-100;OTHER:tags:ENEMY'],
    ['E105_C', 'NARRATOR', '你虽然救了人，但也结下了死仇。', 'PLAYER:safety:DANGER'],
    
    # --- E106: 学徒剥削 ---
    ['E106_INTRO', 'NARRATOR', '铁匠铺里，一个少年正在被师傅责骂。', ''],
    ['E106_INTRO', 'OTHER', '三年了！连一根铁钉都打不好！', ''],
    ['E106_INTRO', 'SELF', '师傅...我日夜苦练...', ''],
    ['E106_INTRO', 'OTHER', '还敢顶嘴？这个月工钱全扣！', ''],
    ['E106_INTRO', 'NARRATOR', '学徒{A}入行三年，师傅{B}以「学艺」为由分文不给。{B}是你的老熟人。', 'SHOW_CHOICE'],
    
    ['E106_A', 'PLAYER', '（上前）老张，这就是你的待徒之道？', ''],
    ['E106_A', 'OTHER', '你管得着吗？这是我的徒弟！', ''],
    ['E106_A', 'PLAYER', '徒弟也是人！三年不给工钱，传出去你还要不要做人？', ''],
    ['E106_A', 'NARRATOR', '在你的施压下，{A}终于拿到了应得的报酬。但你和{B}的关系...', 'SELF:emotion:HAPPY;SELF:affinity:PLAYER:60;OTHER:affinity:PLAYER:-80'],
    
    ['E106_B', 'PLAYER', '（摇头）老张的规矩一向如此，年轻人要多磨练。', ''],
    ['E106_B', 'SELF', '（低下头）...是。', 'SELF:emotion:DEPRESSED;SELF:tags:SLAVE_MIND'],
    ['E106_B', 'OTHER', '（满意）还是老兄弟明白事理！', 'OTHER:affinity:PLAYER:30'],
    
    ['E106_C', 'PLAYER', '（悄声对{A}）想不想跟我走？我给你工钱。', 'PLAYER:Money:-100'],
    ['E106_C', 'SELF', '（眼睛一亮）真的吗？', ''],
    ['E106_C', 'NARRATOR', '你趁{B}不注意，将{A}带走了。', 'SELF:is_follower:True;SELF:affinity:PLAYER:40'],
    ['E106_C', 'NARRATOR', '事后{B}得知真相，勃然大怒...', 'OTHER:affinity:PLAYER:-100;OTHER:tags:ENEMY'],
    
    # --- E107: 虚假宣传（恩人是凶手） ---
    ['E107_INTRO', 'NARRATOR', '街上围满了人，一个寡妇正在哭诉。', ''],
    ['E107_INTRO', 'OTHER', '就是他的假药害死了我儿子！求各位为我主持公道！', ''],
    ['E107_INTRO', 'NARRATOR', '郎中{A}面色苍白，他曾经救过你的命。', ''],
    ['E107_INTRO', 'SELF', '我...我不知道药有问题...', ''],
    ['E107_INTRO', 'NARRATOR', '寡妇{B}是你已故恩师的遗孀，正跪在地上向你求救。', 'SHOW_CHOICE'],
    
    ['E107_A', 'PLAYER', '（沉默片刻）...药确实是他卖的，但人是病死的，与他无关。', ''],
    ['E107_A', 'OTHER', '（绝望）你...你也要帮他说话？', 'OTHER:emotion:DESPAIR;OTHER:affinity:PLAYER:-100'],
    ['E107_A', 'SELF', '（感激地看你一眼）多谢...多谢...', 'SELF:affinity:PLAYER:50'],
    ['E107_A', 'NARRATOR', '你帮恩人脱了罪，但师母的眼神，像刀一样刺痛你的心。', 'PLAYER:Fame:-200;PLAYER:AddTag:ACCOMPLICE'],
    
    ['E107_B', 'PLAYER', '（深吸一口气）师母，我会为你主持公道。', ''],
    ['E107_B', 'SELF', '你...你要背叛我？我可是救过你的命！', ''],
    ['E107_B', 'PLAYER', '人命关天，恩情也无法抵消罪过。', ''],
    ['E107_B', 'NARRATOR', '你作证揭发，{A}被押入大牢。他临走前恨恨地看了你一眼...', 'SELF:freedom:PRISON;SELF:affinity:PLAYER:-100;OTHER:emotion:HAPPY'],
    
    ['E107_C', 'PLAYER', '这样吧，{A}出钱赔偿丧葬费，此事私了。', 'PLAYER:Money:-300'],
    ['E107_C', 'SELF', '（咬牙）...好。', 'SELF:affinity:PLAYER:-30;SELF:eco_status:POOR'],
    ['E107_C', 'OTHER', '（不甘心）可是我儿子...', 'OTHER:emotion:SAD'],
    ['E107_C', 'NARRATOR', '你用钱平息了事端，但双方都不满意。', ''],
    
    # --- E108: 合同诈骗 ---
    ['E108_INTRO', 'NARRATOR', '码头边，一个脚夫正在发抖。', ''],
    ['E108_INTRO', 'SELF', '我...我怎么就签了卖身契...', ''],
    ['E108_INTRO', 'OTHER', '（冷笑）白纸黑字，按了手印，想赖账？', ''],
    ['E108_INTRO', 'NARRATOR', '{A}不识字，被骗签了卖身契。行骗者{B}背后是本城最大的人牙子。', 'SHOW_CHOICE'],
    
    ['E108_A', 'PLAYER', '（一把夺过契约）这契约无效！', ''],
    ['E108_A', 'OTHER', '你敢？！你知道我背后是谁吗？', ''],
    ['E108_A', 'PLAYER', '管你背后是谁，不义之财我必管！', ''],
    ['E108_A', 'NARRATOR', '你当众撕毁契约。{A}自由了，但你也上了人牙子的黑名单...', 'SELF:freedom:FULL;SELF:affinity:PLAYER:80;OTHER:affinity:PLAYER:-100;PLAYER:safety:DANGER'],
    
    ['E108_B', 'PLAYER', '（低声）这人...我买了。多少钱？', 'PLAYER:Money:-300'],
    ['E108_B', 'OTHER', '（眼睛一转）三百两！', ''],
    ['E108_B', 'NARRATOR', '你买下了{A}的卖身契。至少他不会落入更坏的人手中。', 'SELF:is_follower:True;SELF:freedom:SERVANT;OTHER:affinity:PLAYER:20'],
    
    ['E108_C', 'NARRATOR', '你看了一眼这场闹剧，转身离去。', ''],
    ['E108_C', 'SELF', '（绝望地喊）大人！救救我！大人！', 'SELF:freedom:SLAVE;SELF:emotion:DESPAIR;SELF:affinity:PLAYER:-50'],
    ['E108_C', 'NARRATOR', '身后的哭喊声渐渐远去...', 'PLAYER:Fame:-100'],
    
    # --- E109: 关扑成瘾 ---
    ['E109_INTRO', 'NARRATOR', '赌坊门口，一个男人正在哀求。', ''],
    ['E109_INTRO', 'SELF', '再给我一次机会...一次就好...', ''],
    ['E109_INTRO', 'OTHER', '你已经输光了！把你儿女带来抵债！', ''],
    ['E109_INTRO', 'NARRATOR', '赌徒{A}输光了家产，赌坊老板{B}要他卖儿卖女。', ''],
    ['E109_INTRO', 'SELF', '（看到你）恩公！求您救我一命！', 'SHOW_CHOICE'],
    
    ['E109_A', 'PLAYER', '欠多少？', ''],
    ['E109_A', 'OTHER', '五百两！', ''],
    ['E109_A', 'PLAYER', '（掏钱）给他还了。', 'PLAYER:Money:-500'],
    ['E109_A', 'SELF', '（感激涕零）多谢恩公！多谢恩公！', 'SELF:emotion:HAPPY;SELF:affinity:PLAYER:30'],
    ['E109_A', 'NARRATOR', '但你知道，这种人十有八九还会再赌...', 'SELF:tags:ADDICTED'],
    
    ['E109_B', 'PLAYER', '（看向打手）砸了这个黑店！', ''],
    ['E109_B', 'NARRATOR', '你带人将赌坊砸了个稀烂。', 'SELF:safety:NORMAL'],
    ['E109_B', 'OTHER', '（被打翻在地）好...好...你等着！', 'OTHER:affinity:PLAYER:-100;OTHER:tags:ENEMY;PLAYER:safety:DANGER'],
    
    ['E109_C', 'PLAYER', '你的孩子...我买了。', 'PLAYER:Money:-200'],
    ['E109_C', 'SELF', '（痛哭）我的孩子...', 'SELF:family:BROKEN;SELF:emotion:SAD'],
    ['E109_C', 'NARRATOR', '你买下了孩子，至少能保证他们不会落入更坏的人手中。', ''],

    # ═══════════════════════════════════════════════════════════════
    # 200系列：家庭伦理事件对话
    # ═══════════════════════════════════════════════════════════════
    
    # --- E201: 天价聘礼 ---
    ['E201_INTRO', 'NARRATOR', '媒婆的吆喝声回荡在街头。', ''],
    ['E201_INTRO', 'SELF', '求您了...三日之内我一定凑齐聘礼！', ''],
    ['E201_INTRO', 'OTHER', '（冷笑）三日？你拿什么凑？', ''],
    ['E201_INTRO', 'NARRATOR', '穷书生{A}凑不齐聘礼，女方父亲{B}扬言退婚另嫁。', ''],
    ['E201_INTRO', 'SELF', '（走向你）恩公...您能借我八百两吗？实在不行...我愿卖身为奴！', 'SHOW_CHOICE'],
    
    ['E201_A', 'PLAYER', '（叹气）拿去吧，不用还了。', 'PLAYER:Money:-800'],
    ['E201_A', 'SELF', '（跪地叩首）恩公大恩！小人来世做牛做马报答！', 'SELF:emotion:GRATEFUL;SELF:affinity:PLAYER:80'],
    ['E201_A', 'OTHER', '（惊讶）哦？倒是有人肯帮你。', 'OTHER:affinity:PLAYER:30'],
    
    ['E201_B', 'PLAYER', '（对{A}摇头）这桩婚事...怕是不成的。', ''],
    ['E201_B', 'SELF', '可是...我们已经定亲了...', ''],
    ['E201_B', 'PLAYER', '你没钱，她父亲不会答应的。长痛不如短痛。', ''],
    ['E201_B', 'NARRATOR', '在你的劝说下，{A}放弃了这门亲事。', 'SELF:emotion:DESPAIR;SELF:tags:HEARTBROKEN'],
    ['E201_B', 'OTHER', '（满意）总算有个明白人。', 'OTHER:affinity:PLAYER:50'],
    
    ['E201_C', 'PLAYER', '我这里有条路子...高利贷。', ''],
    ['E201_C', 'SELF', '高利贷？', ''],
    ['E201_C', 'PLAYER', '利息高，但能救急。你自己考虑。', 'PLAYER:Money:200'],
    ['E201_C', 'NARRATOR', '{A}借了高利贷，娶到了心上人。但驴打滚的债务...终将把他压垮。', 'SELF:safety:DANGER;SELF:affinity:PLAYER:-30'],

    # --- E202: 赘婿的尊严 ---
    ['E202_INTRO', 'NARRATOR', '后院的角落里，一个男人蹲在地上，神色复杂。', ''],
    ['E202_INTRO', 'SELF', '（苦笑）又被罚跪了...', ''],
    ['E202_INTRO', 'NARRATOR', '他是{A}，入赘到豪门，却被当狗一样使唤。', ''],
    ['E202_INTRO', 'SELF', '（低声）其实...我手里有岳父的把柄。', ''],
    ['E202_INTRO', 'PLAYER', '什么把柄？', ''],
    ['E202_INTRO', 'SELF', '他暗中贪污的账本...我能让他身败名裂！', 'SHOW_CHOICE'],
    
    ['E202_A', 'PLAYER', '贪官污吏，人人得而诛之。我帮你。', ''],
    ['E202_A', 'NARRATOR', '你协助{A}将证据呈交官府。', ''],
    ['E202_A', 'SELF', '（大笑）哈哈哈！看他还怎么欺负我！', 'SELF:emotion:HAPPY;SELF:eco_status:RICH'],
    ['E202_A', 'NARRATOR', '岳父{B}锒铛入狱，{A}翻身做主。', 'OTHER:freedom:PRISON;OTHER:affinity:PLAYER:-100'],
    
    ['E202_B', 'PLAYER', '算了吧，得饶人处且饶人。', ''],
    ['E202_B', 'SELF', '（低下头）...是啊，我又能怎样呢。', 'SELF:emotion:DEPRESSED;SELF:tags:COWARD'],
    ['E202_B', 'NARRATOR', '他选择了隐忍，继续过着被践踏的日子。', 'OTHER:affinity:PLAYER:20'],
    
    ['E202_C', 'PLAYER', '（眼珠一转）这账本...或许可以换点好处。', ''],
    ['E202_C', 'NARRATOR', '你两边敲诈，从赘婿那里拿到账本副本，又从岳父那里收取封口费。', 'PLAYER:Money:500'],
    ['E202_C', 'SELF', '（警觉）你...你要干什么？', 'SELF:affinity:PLAYER:-50'],
    ['E202_C', 'OTHER', '（阴沉）你最好把嘴闭紧...', 'OTHER:affinity:PLAYER:-80'],

    # --- E203: 扶弟魔 ---
    ['E203_INTRO', 'NARRATOR', '隔壁传来激烈的争吵声。', ''],
    ['E203_INTRO', 'SELF', '你疯了！把家里的钱都给了你弟弟！', ''],
    ['E203_INTRO', 'OTHER', '那是我弟弟！你敢动他一根手指，我就跟你拼命！', ''],
    ['E203_INTRO', 'NARRATOR', '丈夫{A}和妻弟{B}为了钱大打出手。你是他们的邻居兼债主。', 'SHOW_CHOICE'],
    
    ['E203_A', 'PLAYER', '（指着{B}）你妹妹再怎么帮你，也不能害得人家倾家荡产！', ''],
    ['E203_A', 'SELF', '（感激）多谢您主持公道！', 'SELF:emotion:ANGRY;SELF:affinity:PLAYER:30'],
    ['E203_A', 'OTHER', '（怒目而视）你管得着吗？', 'OTHER:affinity:PLAYER:-80'],
    
    ['E203_B', 'PLAYER', '（摇头）亲情为大，这种事外人不好说。', ''],
    ['E203_B', 'SELF', '（绝望）连你也...', 'SELF:emotion:SAD;SELF:affinity:PLAYER:-50'],
    ['E203_B', 'OTHER', '（得意）听到没？识相点！', 'OTHER:affinity:PLAYER:30'],
    
    ['E203_C', 'PLAYER', '先别吵。你们还欠我三百两，什么时候还？', 'PLAYER:Money:300'],
    ['E203_C', 'NARRATOR', '两人都愣住了。', ''],
    ['E203_C', 'SELF', '（苦涩）...我去想办法。', 'SELF:affinity:PLAYER:-30'],
    ['E203_C', 'OTHER', '（恼怒）真是趁火打劫！', 'OTHER:affinity:PLAYER:-30;OTHER:eco_status:POOR'],

    # --- E204: 假名媛拼单 ---
    ['E204_INTRO', 'NARRATOR', '诗会散场，一个女子蹲在角落啜泣。', ''],
    ['E204_INTRO', 'SELF', '首饰不见了...那可是价值千金的传家宝...', ''],
    ['E204_INTRO', 'NARRATOR', '她是{A}，借首饰参加诗会，却不慎弄丢。', ''],
    ['E204_INTRO', 'OTHER', '（怒气冲冲）我的首饰呢！你赔得起吗！', ''],
    ['E204_INTRO', 'NARRATOR', '首饰主人{B}是你的生意伙伴，价值千金。', 'SHOW_CHOICE'],
    
    ['E204_A', 'PLAYER', '这钱我来出。', 'PLAYER:Money:-500'],
    ['E204_A', 'SELF', '（感激涕零）恩公大德！', 'SELF:emotion:GRATEFUL;SELF:affinity:PLAYER:80'],
    ['E204_A', 'OTHER', '算你识相。', 'OTHER:affinity:PLAYER:20'],
    
    ['E204_B', 'PLAYER', '赔不起就卖身抵债，这是规矩。', ''],
    ['E204_B', 'SELF', '（绝望）我...我愿意...', 'SELF:freedom:SLAVE;SELF:emotion:DESPAIR'],
    ['E204_B', 'OTHER', '（满意）这还差不多。', 'OTHER:affinity:PLAYER:30'],
    
    ['E204_C', 'PLAYER', '我派人去找找，也许还能找回来。', 'PLAYER:Money:-200'],
    ['E204_C', 'NARRATOR', '你花钱找人，最终在当铺寻回了首饰。', ''],
    ['E204_C', 'SELF', '太好了！', 'SELF:emotion:HAPPY'],
    ['E204_C', 'OTHER', '（疑惑）怎么会在当铺...', 'OTHER:affinity:PLAYER:-50'],

    # --- E205: 指腹为婚 ---
    ['E205_INTRO', 'NARRATOR', '富家小姐{A}跪在你面前，泪流满面。', ''],
    ['E205_INTRO', 'SELF', '求您救救我...我不想嫁给那个纨绔！', ''],
    ['E205_INTRO', 'NARRATOR', '太尉之子{B}是出了名的败家子，但得罪太尉后果严重。', ''],
    ['E205_INTRO', 'SELF', '我心里有人了...是个穷书生...', 'SHOW_CHOICE'],
    
    ['E205_A', 'PLAYER', '跟我走，我送你们出城。', ''],
    ['E205_A', 'NARRATOR', '你冒着风险，协助两人私奔。', 'SELF:emotion:HAPPY;SELF:family:ISOLATED'],
    ['E205_A', 'NARRATOR', '太尉震怒，扬言要让你好看...', 'OTHER:affinity:PLAYER:-100;PLAYER:safety:DANGER'],
    
    ['E205_B', 'PLAYER', '认命吧，太尉府得罪不起。', ''],
    ['E205_B', 'SELF', '（绝望）...是。', 'SELF:emotion:DESPAIR;SELF:affinity:PLAYER:-60'],
    ['E205_B', 'OTHER', '（得意）识时务者为俊杰。', 'OTHER:affinity:PLAYER:30'],
    
    ['E205_C', 'PLAYER', '太尉之子的丑闻...我这里有些。', ''],
    ['E205_C', 'NARRATOR', '你让文人帮忙，将纨绔的恶行公之于众。', ''],
    ['E205_C', 'SELF', '（喜极而泣）谢谢您！', 'SELF:emotion:HAPPY'],
    ['E205_C', 'NARRATOR', '纨绔被家法处置，但太尉记住了你...', 'OTHER:freedom:PRISON;PLAYER:safety:DANGER'],

    # --- E206: 抛妻弃子 ---
    ['E206_INTRO', 'NARRATOR', '新科状元府前，一个妇人跪在门口。', ''],
    ['E206_INTRO', 'OTHER', '（哭诉）他当年穷得揭不开锅，是我卖嫁妆供他读书！', ''],
    ['E206_INTRO', 'NARRATOR', '{A}是新科状元，要休掉糟糠之妻{B}。', ''],
    ['E206_INTRO', 'SELF', '（冷漠）过去的事就让它过去吧。', ''],
    ['E206_INTRO', 'NARRATOR', '{A}曾是你资助的穷书生，{B}是你的远房表妹。', 'SHOW_CHOICE'],
    
    ['E206_A', 'PLAYER', '陈世美的故事，该让天下人都知道。', ''],
    ['E206_A', 'NARRATOR', '你写文揭露，状元郎的丑行传遍汴京。', 'SELF:soc_status:LOW;SELF:tags:HYPOCRITE'],
    ['E206_A', 'SELF', '（恨恨地）你毁了我的前程！', 'SELF:affinity:PLAYER:-100'],
    ['E206_A', 'OTHER', '（感激）表哥...谢谢你为我出头...', 'OTHER:emotion:HAPPY;OTHER:affinity:PLAYER:50'],
    
    ['E206_B', 'PLAYER', '（收下银票）这事我不知道。', 'PLAYER:Money:800'],
    ['E206_B', 'SELF', '（满意）识时务。', 'SELF:affinity:PLAYER:30'],
    ['E206_B', 'OTHER', '（绝望）表哥...你也...', 'OTHER:emotion:DESPAIR;OTHER:affinity:PLAYER:-100'],
    ['E206_B', 'NARRATOR', '你收了好处，选择沉默。表妹被扫地出门...', 'PLAYER:AddTag:CORRUPT'],
    
    ['E206_C', 'PLAYER', '你们都冷静一下，这事可以商量。', ''],
    ['E206_C', 'NARRATOR', '在你的调解下，两人勉强复合。', ''],
    ['E206_C', 'SELF', '（不情愿）...好吧。', 'SELF:affinity:PLAYER:-20;SELF:emotion:ANGRY'],
    ['E206_C', 'OTHER', '（苦涩）...谢谢表哥。', 'OTHER:emotion:SAD;OTHER:affinity:PLAYER:20'],

    # --- E207: 重男轻女 ---
    ['E207_INTRO', 'NARRATOR', '后院传来虚弱的咳嗽声。', ''],
    ['E207_INTRO', 'SELF', '婆婆...我真的生不动了...', ''],
    ['E207_INTRO', 'OTHER', '生不出儿子，你就没用！继续生！', ''],
    ['E207_INTRO', 'NARRATOR', '媳妇{A}被婆婆{B}逼迫连续生育，身体已垮。', ''],
    ['E207_INTRO', 'NARRATOR', '{B}是你母亲的故交，曾照顾过你的童年。', 'SHOW_CHOICE'],
    
    ['E207_A', 'PLAYER', '伯母，这样下去她会死的。我带她去看病。', ''],
    ['E207_A', 'OTHER', '你管得着吗？这是我们家的事！', 'OTHER:affinity:PLAYER:-100'],
    ['E207_A', 'NARRATOR', '你不顾阻拦，强行将{A}带走治疗。', 'SELF:hp:NORMAL;SELF:emotion:GRATEFUL;SELF:affinity:PLAYER:80'],
    
    ['E207_B', 'PLAYER', '伯母说得对，传宗接代是大事。', ''],
    ['E207_B', 'SELF', '（绝望地闭上眼睛）...', 'SELF:hp:POOR;SELF:emotion:DESPAIR;SELF:affinity:PLAYER:-50'],
    ['E207_B', 'OTHER', '还是你懂事。', 'OTHER:affinity:PLAYER:30'],
    
    ['E207_C', 'PLAYER', '我出钱请最好的大夫来调理。', 'PLAYER:Money:-300'],
    ['E207_C', 'NARRATOR', '你花钱请来名医，为{A}调养身体。', 'SELF:hp:ENOUGH;SELF:affinity:PLAYER:30'],
    ['E207_C', 'OTHER', '（不满）多管闲事...', 'OTHER:affinity:PLAYER:-20'],

    # --- E208: 断袖疑云 ---
    ['E208_INTRO', 'NARRATOR', '茶楼里，众人议论纷纷。', ''],
    ['E208_INTRO', 'NARRATOR', '知名侠客{A}被传与书童{B}关系暧昧。', ''],
    ['E208_INTRO', 'SELF', '（愤怒）那些都是谣言！', ''],
    ['E208_INTRO', 'NARRATOR', '其实{B}是女扮男装的官家千金，但揭露身份会害了她。', ''],
    ['E208_INTRO', 'NARRATOR', '{A}是你的救命恩人，正遭到江湖围攻。', 'SHOW_CHOICE'],
    
    ['E208_A', 'PLAYER', '各位稍安勿躁，我来揭开真相。', ''],
    ['E208_A', 'NARRATOR', '你当众揭露{B}的女儿身，流言不攻自破。', ''],
    ['E208_A', 'SELF', '（复杂）你...', 'SELF:emotion:ANGRY;SELF:affinity:PLAYER:-30'],
    ['E208_A', 'OTHER', '（惊恐）完了...我的身份暴露了...', 'OTHER:safety:DANGER;OTHER:family:ISOLATED'],
    
    ['E208_B', 'PLAYER', '他是我的恩人，我相信他的人品！', ''],
    ['E208_B', 'NARRATOR', '你力挺恩人，不惧流言蜚语。', 'SELF:emotion:HAPPY;SELF:affinity:PLAYER:80'],
    ['E208_B', 'NARRATOR', '众人虽然将信将疑，但你的声誉也受到了影响...', 'PLAYER:Fame:-150;PLAYER:AddTag:LOYAL'],
    
    ['E208_C', 'NARRATOR', '你默默站在人群中，不发一言。', ''],
    ['E208_C', 'SELF', '（失望地看你一眼）...', 'SELF:emotion:SAD;SELF:affinity:PLAYER:-40'],
    ['E208_C', 'NARRATOR', '恩人独自承受流言，你选择了明哲保身。', 'PLAYER:Fame:-30'],

    # --- E301-E310: 300系列社会乱象对话 ---
    # (为了节省篇幅,以下是简化版)
    
    # --- E301: 当街碰瓷 ---
    ['E301_INTRO', 'NARRATOR', '马车急停，一个老人倒在车轮旁哀嚎。', ''],
    ['E301_INTRO', 'SELF', '哎呦！我的腿！撞断了！', ''],
    ['E301_INTRO', 'OTHER', '我明明没碰到你！', ''],
    ['E301_INTRO', 'NARRATOR', '围观群众越来越多，{A}是老人，{B}是你的债主。', 'SHOW_CHOICE'],
    
    ['E301_A', 'PLAYER', '先送老人家去看看大夫。', 'PLAYER:Money:-300'],
    ['E301_A', 'SELF', '好人啊...', 'SELF:emotion:HAPPY;SELF:affinity:PLAYER:50'],
    ['E301_A', 'OTHER', '（不满）冤枉钱...', 'OTHER:affinity:PLAYER:-50'],
    
    ['E301_B', 'PLAYER', '这马车离老人还有三尺远，怎么可能撞到？', ''],
    ['E301_B', 'SELF', '（怒目）你...你帮着他说话？', 'SELF:emotion:ANGRY;SELF:affinity:PLAYER:-80'],
    ['E301_B', 'OTHER', '（感激）多谢仗义执言！', 'OTHER:affinity:PLAYER:50'],
    
    ['E301_C', 'PLAYER', '（让随从的医生上前检查）我这位朋友懂医术。', ''],
    ['E301_C', 'NARRATOR', '医生检查后宣布老人的腿本来就是断的，根本不是新伤。', ''],
    ['E301_C', 'SELF', '（面如死灰）...', 'SELF:tags:LIAR;SELF:emotion:DESPAIR;SELF:affinity:PLAYER:-100'],

    # --- E302: 造谣一张嘴 ---
    ['E302_INTRO', 'NARRATOR', '城门口，一个衣衫褴褛的外乡人被众人围堵。', ''],
    ['E302_INTRO', 'OTHER', '就是他！江洋大盗！抓住他！', ''],
    ['E302_INTRO', 'SELF', '冤枉！我只是来做生意的！', ''],
    ['E302_INTRO', 'NARRATOR', '造谣者{B}是本地富商，你的重要客户。外乡人{A}已走投无路。', 'SHOW_CHOICE'],
    
    ['E302_A', 'PLAYER', '且慢！这人我认识，跟我走。', ''],
    ['E302_A', 'SELF', '（感激）恩公救命！', 'SELF:safety:NORMAL;SELF:is_follower:True;SELF:affinity:PLAYER:80'],
    ['E302_A', 'OTHER', '（阴沉）你要跟我作对？', 'OTHER:affinity:PLAYER:-80'],
    
    ['E302_B', 'PLAYER', '大盗？那还等什么，打出去！', ''],
    ['E302_B', 'SELF', '（绝望）不是的...我不是...', 'SELF:safety:EXILE;SELF:emotion:DESPAIR;SELF:affinity:PLAYER:-100'],
    ['E302_B', 'OTHER', '（满意）还是你识大体。', 'OTHER:affinity:PLAYER:40'],
    
    ['E302_C', 'PLAYER', '慢着，让我查查看。', ''],
    ['E302_C', 'NARRATOR', '你让文人帮忙调查，发现所谓的"通缉令"是伪造的。', ''],
    ['E302_C', 'SELF', '谢天谢地...', 'SELF:emotion:HAPPY;SELF:affinity:PLAYER:60'],
    ['E302_C', 'NARRATOR', '造谣者{B}因诬陷罪被捕，你失去了一个大客户...', 'OTHER:freedom:PRISON;OTHER:affinity:PLAYER:-100'],

    # --- E303: 熊孩子作恶 ---
    ['E303_INTRO', 'NARRATOR', '画坊里传来一声惨叫。', ''],
    ['E303_INTRO', 'OTHER', '我的画！毁了！毁了！', ''],
    ['E303_INTRO', 'NARRATOR', '一个小孩拿着墨汁，画家{B}的名作被划得面目全非。', ''],
    ['E303_INTRO', 'SELF', '小孩子不懂事，你跟他计较什么！', ''],
    ['E303_INTRO', 'NARRATOR', '家长{A}是你的老相识，拒不赔偿还撒泼打滚。', 'SHOW_CHOICE'],
    
    ['E303_A', 'PLAYER', '这画我赔了，多少钱？', 'PLAYER:Money:-200'],
    ['E303_A', 'SELF', '（得意）早说嘛，何必...', 'SELF:affinity:PLAYER:30;SELF:tags:SHAMELESS'],
    ['E303_A', 'OTHER', '（叹气）算了...', 'OTHER:emotion:SAD;OTHER:affinity:PLAYER:40'],
    
    ['E303_B', 'PLAYER', '画家的心血，岂能如此糟蹋？必须赔偿！', ''],
    ['E303_B', 'SELF', '（翻脸）你算什么东西！', 'SELF:affinity:PLAYER:-80;SELF:emotion:ANGRY'],
    ['E303_B', 'OTHER', '（感激）多谢公道！', 'OTHER:emotion:HAPPY;OTHER:affinity:PLAYER:60'],
    
    ['E303_C', 'PLAYER', '各退一步，赔一半。', ''],
    ['E303_C', 'NARRATOR', '双方都不满意，但勉强接受。', ''],
    ['E303_C', 'SELF', '哼...', 'SELF:affinity:PLAYER:-30'],
    ['E303_C', 'OTHER', '罢了...', 'OTHER:affinity:PLAYER:-30'],

    # --- E304: 流浪狗风波 ---
    ['E304_INTRO', 'NARRATOR', '街角传来孩子的哭声。', ''],
    ['E304_INTRO', 'OTHER', '你养的狗咬了我儿子！必须打死！', ''],
    ['E304_INTRO', 'SELF', '它只是受惊了！不能杀它！', ''],
    ['E304_INTRO', 'NARRATOR', '爱狗人士{A}与孩童父亲{B}对峙，双方各有支持者。', 'SHOW_CHOICE'],
    
    ['E304_A', 'PLAYER', '狗咬人，就该处理掉。', ''],
    ['E304_A', 'SELF', '（哭泣）不要...', 'SELF:emotion:SAD;SELF:affinity:PLAYER:-60'],
    ['E304_A', 'OTHER', '痛快！', 'OTHER:emotion:HAPPY;OTHER:affinity:PLAYER:50'],
    
    ['E304_B', 'PLAYER', '狗只是畜生，人才是无辜的。我来赔医药费。', 'PLAYER:Money:-200'],
    ['E304_B', 'SELF', '谢谢你...', 'SELF:emotion:HAPPY;SELF:affinity:PLAYER:60'],
    ['E304_B', 'OTHER', '（不满）便宜它了！', 'OTHER:affinity:PLAYER:-80'],
    
    ['E304_C', 'PLAYER', '这样吧，我出钱建个收容所，流浪狗统一管理。', 'PLAYER:Money:-500'],
    ['E304_C', 'NARRATOR', '你的提议得到了大家的认可。', ''],
    ['E304_C', 'SELF', '谢谢您...', 'SELF:affinity:PLAYER:40'],
    ['E304_C', 'OTHER', '这倒是个办法。', 'OTHER:affinity:PLAYER:30'],

    # --- E305: 插队冲突 ---
    ['E305_INTRO', 'NARRATOR', '施粥铺前，人群骚动。', ''],
    ['E305_INTRO', 'SELF', '老子等不及了！让开！', ''],
    ['E305_INTRO', 'NARRATOR', '壮汉{A}强行插队，被插队的孕妇{B}晕倒在地。', 'SHOW_CHOICE'],
    
    ['E305_A', 'PLAYER', '大胆！敢在我的铺子撒野！', ''],
    ['E305_A', 'NARRATOR', '你一拳将壮汉打倒。', 'SELF:hp:POOR;SELF:emotion:ANGRY;SELF:affinity:PLAYER:-100'],
    ['E305_A', 'OTHER', '（虚弱地）谢谢...', 'OTHER:emotion:HAPPY;OTHER:affinity:PLAYER:60'],
    
    ['E305_B', 'PLAYER', '算了算了，再盛一碗给他。', ''],
    ['E305_B', 'SELF', '（得意）识相！', 'SELF:tags:GREEDY;SELF:affinity:PLAYER:20'],
    ['E305_B', 'OTHER', '（委屈地哭）...', 'OTHER:emotion:SAD;OTHER:affinity:PLAYER:-30'],
    
    ['E305_C', 'PLAYER', '快！送这位夫人去医馆！', 'PLAYER:Money:-150'],
    ['E305_C', 'NARRATOR', '你将孕妇送去救治。', 'OTHER:hp:NORMAL;OTHER:affinity:PLAYER:80'],
    ['E305_C', 'SELF', '（趁乱拿了两碗）...', 'SELF:emotion:NORMAL'],

    # --- E306: 噪音扰民 ---
    ['E306_INTRO', 'NARRATOR', '深夜，铁锤声不断。', ''],
    ['E306_INTRO', 'OTHER', '能不能安静点！明天就是科考！', ''],
    ['E306_INTRO', 'SELF', '我也没办法...不赶工就还不上债...', ''],
    ['E306_INTRO', 'NARRATOR', '铁匠{A}要还你的债，书生{B}明日大考。', 'SHOW_CHOICE'],
    
    ['E306_A', 'PLAYER', '你的债先放一放，让书生好好休息。', ''],
    ['E306_A', 'SELF', '（无奈）...是。', 'SELF:eco_status:POOR;SELF:affinity:PLAYER:-50'],
    ['E306_A', 'OTHER', '（感激）多谢！', 'OTHER:emotion:HAPPY;OTHER:affinity:PLAYER:50'],
    
    ['E306_B', 'PLAYER', '欠债还钱天经地义，继续打。', ''],
    ['E306_B', 'SELF', '（如释重负）多谢理解！', 'SELF:affinity:PLAYER:30'],
    ['E306_B', 'OTHER', '（绝望）完了...', 'OTHER:hp:POOR;OTHER:affinity:PLAYER:-80;OTHER:tags:FAILED'],
    
    ['E306_C', 'PLAYER', '我出钱帮书生租个安静的地方。', 'PLAYER:Money:-100'],
    ['E306_C', 'NARRATOR', '你两边照顾到了。', ''],
    ['E306_C', 'SELF', '谢谢...', 'SELF:affinity:PLAYER:20'],
    ['E306_C', 'OTHER', '恩公大德！', 'OTHER:affinity:PLAYER:60;OTHER:emotion:HAPPY'],

    # --- E307: 地域歧视 ---
    ['E307_INTRO', 'NARRATOR', '酒楼里起了争执。', ''],
    ['E307_INTRO', 'SELF', '你这外地人，说话怪里怪气的，滚出汴京！', ''],
    ['E307_INTRO', 'OTHER', '我是来做生意的，有什么不对？', ''],
    ['E307_INTRO', 'NARRATOR', '{A}是你的远房亲戚，{B}是你的合作伙伴。', 'SHOW_CHOICE'],
    
    ['E307_A', 'PLAYER', '表弟说得对，这里是汴京！', ''],
    ['E307_A', 'SELF', '（得意）听到没！', 'SELF:emotion:HAPPY;SELF:affinity:PLAYER:50'],
    ['E307_A', 'OTHER', '（失望）你...', 'OTHER:safety:DANGER;OTHER:affinity:PLAYER:-100'],
    
    ['E307_B', 'PLAYER', '人不论出身，何必为难？', ''],
    ['E307_B', 'SELF', '你帮外人？', 'SELF:emotion:ANGRY;SELF:affinity:PLAYER:-80'],
    ['E307_B', 'OTHER', '（感激）多谢公道！', 'OTHER:affinity:PLAYER:60'],
    
    ['E307_C', 'PLAYER', '来人，叫巡城！', ''],
    ['E307_C', 'NARRATOR', '你选择报官，两边都被带走问话。', ''],
    ['E307_C', 'SELF', '（恨恨地）你...', 'SELF:affinity:PLAYER:-40;SELF:freedom:PRISON'],
    ['E307_C', 'OTHER', '（无奈）...', 'OTHER:affinity:PLAYER:-20'],

    # --- E308: 杀猪盘 ---
    ['E308_INTRO', 'NARRATOR', '你偶然撞见一幕可疑的场景。', ''],
    ['E308_INTRO', 'SELF', '老夫人，这玉佩能保您长命百岁...', ''],
    ['E308_INTRO', 'NARRATOR', '貌美女子{A}正在忽悠老人{B}买假货。{B}是你恩师的遗孀，{A}是你门客的妹妹。', 'SHOW_CHOICE'],
    
    ['E308_A', 'PLAYER', '住手！这是骗局！', ''],
    ['E308_A', 'SELF', '（恼羞成怒）你...', 'SELF:tags:LIAR;SELF:affinity:PLAYER:-100'],
    ['E308_A', 'OTHER', '什么？骗我？', 'OTHER:emotion:HAPPY;OTHER:affinity:PLAYER:80'],
    
    ['E308_B', 'PLAYER', '（悄声对{A}）我出三百两，你放过她。', 'PLAYER:Money:-300'],
    ['E308_B', 'SELF', '（眼睛一亮）成交！', 'SELF:affinity:PLAYER:20'],
    ['E308_B', 'OTHER', '（茫然）怎么走了...', 'OTHER:emotion:NORMAL'],
    
    ['E308_C', 'NARRATOR', '你装作没看见，转身离去。', ''],
    ['E308_C', 'SELF', '（继续行骗）...', 'SELF:eco_status:RICH'],
    ['E308_C', 'OTHER', '（被骗）好...好...', 'OTHER:emotion:DESPAIR;OTHER:affinity:PLAYER:-50'],

    # --- E309: 假冒官差 ---
    ['E309_INTRO', 'NARRATOR', '市场上，一个"官差"正在勒索摊贩。', ''],
    ['E309_INTRO', 'SELF', '例行检查！交钱！', ''],
    ['E309_INTRO', 'OTHER', '大人...小的真没钱...', ''],
    ['E309_INTRO', 'NARRATOR', '你认出那"官差"是你儿时玩伴{A}，落魄至此。摊贩{B}是你的竞争对手。', 'SHOW_CHOICE'],
    
    ['E309_A', 'PLAYER', '来人！抓住这个冒牌货！', ''],
    ['E309_A', 'SELF', '（愕然）是你...', 'SELF:freedom:PRISON;SELF:affinity:PLAYER:-100'],
    ['E309_A', 'OTHER', '（感激）多谢揭发！', 'OTHER:affinity:PLAYER:50'],
    
    ['E309_B', 'PLAYER', '（低声对{A}）分我一半。', 'PLAYER:Money:100'],
    ['E309_B', 'SELF', '（惊喜）老兄够意思！', 'SELF:affinity:PLAYER:50'],
    ['E309_B', 'OTHER', '（痛苦）求求你们...', 'OTHER:eco_status:POOR;OTHER:affinity:PLAYER:-80'],
    
    ['E309_C', 'PLAYER', '（悄声）快跑，我装作没看见。', ''],
    ['E309_C', 'SELF', '（感激）多谢！', 'SELF:affinity:PLAYER:30;SELF:safety:EXILE'],
    ['E309_C', 'OTHER', '（疑惑）怎么跑了...', 'OTHER:affinity:PLAYER:-30'],

    # --- E310: 道德绑架 ---
    ['E310_INTRO', 'NARRATOR', '大街上，一个乞丐拦住你的去路。', ''],
    ['E310_INTRO', 'SELF', '有钱人！却见死不救！为富不仁啊！', ''],
    ['E310_INTRO', 'NARRATOR', '旁边的富商{B}正是你想攀附的大人物，正看着这场好戏。', 'SHOW_CHOICE'],
    
    ['E310_A', 'PLAYER', '来，这些钱你拿去。', 'PLAYER:Money:-200'],
    ['E310_A', 'SELF', '谢谢老爷！', 'SELF:emotion:HAPPY;SELF:affinity:PLAYER:40'],
    ['E310_A', 'OTHER', '（赞赏）仁义之人。', 'OTHER:affinity:PLAYER:30'],
    
    ['E310_B', 'PLAYER', '滚开！我凭什么给你钱！', ''],
    ['E310_B', 'SELF', '（退缩）...', 'SELF:emotion:SAD;SELF:affinity:PLAYER:-60'],
    ['E310_B', 'OTHER', '（点头）有魄力。', 'OTHER:affinity:PLAYER:50;OTHER:emotion:HAPPY'],
    
    ['E310_C', 'NARRATOR', '你无视他，径直走过。', ''],
    ['E310_C', 'SELF', '（绝望）没人管我...', 'SELF:emotion:DESPAIR'],
    ['E310_C', 'OTHER', '（冷漠）穷人...', 'OTHER:affinity:PLAYER:-30'],
    
    # --- E401-E405: 400系列江湖恩怨对话 ---
    
    # --- E401: 金盆洗手难 ---
    ['E401_INTRO', 'NARRATOR', '深夜，一个黑衣人翻墙进入你的院子。', ''],
    ['E401_INTRO', 'SELF', '（低声）是我...{A}。', ''],
    ['E401_INTRO', 'PLAYER', '你怎么来了？', ''],
    ['E401_INTRO', 'SELF', '组织要杀我全家...我想金盆洗手，他们不允许。', ''],
    ['E401_INTRO', 'NARRATOR', '他曾救过你的命。但组织的首领，恰好是你的债主。', 'SHOW_CHOICE'],
    
    ['E401_A', 'PLAYER', '你救过我的命，这次轮到我帮你了。', 'PLAYER:Money:-500'],
    ['E401_A', 'NARRATOR', '你出钱出人，协助{A}灭了组织。', ''],
    ['E401_A', 'SELF', '（抱拳）大恩不言谢，从此唯你马首是瞻！', 'SELF:freedom:FULL;SELF:is_follower:True;SELF:affinity:PLAYER:100'],
    ['E401_A', 'NARRATOR', '但组织余党四处追杀你...', 'OTHER:affinity:PLAYER:-100;PLAYER:safety:DANGER'],
    
    ['E401_B', 'PLAYER', '（沉默片刻）...对不起，我帮不了你。', ''],
    ['E401_B', 'SELF', '你...', ''],
    ['E401_B', 'NARRATOR', '你将{A}的藏身之处告诉了组织，换取了一笔赏金。', 'PLAYER:Money:800'],
    ['E401_B', 'NARRATOR', '三天后，{A}的尸体被挂在城门口示众...', 'SELF:safety:DEAD;SELF:affinity:PLAYER:-100;PLAYER:AddTag:TRAITOR'],
    
    ['E401_C', 'PLAYER', '我不能帮你，但我可以送你离开。', ''],
    ['E401_C', 'NARRATOR', '你出钱帮{A}远走高飞，他的家人却被留下...', 'SELF:family:ISOLATED;SELF:affinity:PLAYER:30'],
    ['E401_C', 'OTHER', '（收到消息）他跑了？算了，反正他也翻不出什么浪花。', 'OTHER:affinity:PLAYER:-50'],

    # ═══════════════════════════════════════════════════════════════
    # 700系列：困境事件对话 - 言行一致，选择有后果
    # ═══════════════════════════════════════════════════════════════
    
    # --- E700: 背叛困境 - 沉默的证人 ---
    ['E700_INTRO', 'NARRATOR', '夜深人静，你的门客{A}神色凝重地来到书房。', ''],
    ['E700_INTRO', 'SELF', '主人，有件事...我思虑再三，还是得告诉您。', ''],
    ['E700_INTRO', 'PLAYER', '何事如此慎重？', ''],
    ['E700_INTRO', 'SELF', '是关于{B}的...我发现他一直在走私禁品。', ''],
    ['E700_INTRO', 'NARRATOR', '你心中一震。{B}是你的商业伙伴，更是当年救你于绝境的恩人。', ''],
    ['E700_INTRO', 'SELF', '官府已经在调查了...他们迟早会查到您这里。', ''],
    ['E700_INTRO', 'NARRATOR', '窗外传来更夫的梆子声，仿佛在催促你做出抉择。', 'SHOW_CHOICE'],
    
    ['E700_A', 'PLAYER', '（深吸一口气）国法不可违，我会如实向官府禀报。', ''],
    ['E700_A', 'NARRATOR', '你写下证词，交给了等候已久的官差。', 'OTHER:freedom:SLAVE'],
    ['E700_A', 'NARRATOR', '数日后，{B}被押解流放，临行前回望你一眼，眼中尽是不解与怨恨。', 'OTHER:safety:EXILE'],
    ['E700_A', 'PLAYER', '（自语）我问心无愧...', 'PLAYER:Fame:300;PLAYER:AddTag:JUSTICE'],
    
    ['E700_B', 'PLAYER', '他救过我的命...我不能见死不救。', ''],
    ['E700_B', 'SELF', '主人的意思是...？', ''],
    ['E700_B', 'PLAYER', '去找几个可靠的人，我们需要一些"证据"证明他的清白。', 'PLAYER:Money:-500'],
    ['E700_B', 'NARRATOR', '你花费重金伪造证据，官府的调查不了了之。', ''],
    ['E700_B', 'NARRATOR', '{B}得知真相后，对你感激涕零。但你知道，从此你们是一根绳上的蚂蚱。', 'PLAYER:AddTag:ACCOMPLICE;OTHER:affinity:PLAYER:50'],
    
    ['E700_C', 'PLAYER', '（目光阴冷）这件事...不能有第三个人知道。', ''],
    ['E700_C', 'SELF', '主人？您...您要做什么？', ''],
    ['E700_C', 'NARRATOR', '你没有回答，只是唤来心腹...', ''],
    ['E700_C', 'NARRATOR', '三日后，人们发现{A}的尸体漂浮在河中。', 'SELF:safety:DEAD'],
    ['E700_C', 'NARRATOR', '官府以失足落水结案。但你知道，从此夜里再难安眠。', 'PLAYER:Fame:-500;PLAYER:AddTag:VILLAIN'],
    
    # --- E701: 牺牲困境 - 瘟疫来袭 ---
    ['E701_INTRO', 'NARRATOR', '瘟疫肆虐，城门紧闭。死亡的阴影笼罩着每一个人。', ''],
    ['E701_INTRO', 'NARRATOR', '你好不容易弄到一剂解药，却面临着残酷的抉择。', ''],
    ['E701_INTRO', 'NARRATOR', '{A}躺在榻上，脸色苍白。他是陪你出生入死的好友。', ''],
    ['E701_INTRO', 'SELF', '（虚弱地）老友...我怕是撑不过今晚了...', ''],
    ['E701_INTRO', 'NARRATOR', '隔壁房间，神医{B}同样病入膏肓。他若死了，全城都将陪葬。', ''],
    ['E701_INTRO', 'OTHER', '（剧烈咳嗽）解药...给我两天...我就能配出更多...', ''],
    ['E701_INTRO', 'NARRATOR', '手中的药瓶，只够救一人。你该如何抉择？', 'SHOW_CHOICE'],
    
    ['E701_A', 'PLAYER', '（走向{A}的病榻）老友，把药喝了。', ''],
    ['E701_A', 'SELF', '可是...神医他...', ''],
    ['E701_A', 'PLAYER', '我不管什么大局！你是我的兄弟！', 'SELF:safety:NORMAL;SELF:hp:100'],
    ['E701_A', 'NARRATOR', '{A}含泪喝下解药，缓缓恢复了气色。', ''],
    ['E701_A', 'NARRATOR', '隔壁传来一声沉闷的倒地声...神医{B}，永远闭上了眼睛。', 'OTHER:safety:DEAD'],
    ['E701_A', 'NARRATOR', '没有神医，瘟疫在城中继续蔓延...', 'PLAYER:Fame:-100;PLAYER:AddTag:LOYAL;PLAYER:AddTag:SELFISH'],
    
    ['E701_B', 'PLAYER', '（走向{B}的病榻）神医，把药喝了...救更多的人。', ''],
    ['E701_B', 'SELF', '（绝望地）老友...你...', ''],
    ['E701_B', 'PLAYER', '（不敢回头）对不起...', 'OTHER:safety:NORMAL;OTHER:is_follower:True'],
    ['E701_B', 'NARRATOR', '你强忍泪水，将解药交给神医。身后传来{A}最后的叹息...', 'SELF:safety:DEAD'],
    ['E701_B', 'NARRATOR', '神医康复后，连夜配制解药。全城得救，但你失去了最好的朋友。', 'PLAYER:Fame:200;PLAYER:AddTag:RUTHLESS'],
    
    ['E701_C', 'NARRATOR', '你看看{A}，又看看{B}...', ''],
    ['E701_C', 'PLAYER', '（低语）对不起...我想活下去。', ''],
    ['E701_C', 'NARRATOR', '你躲进内室，独自服下了解药。', 'PLAYER:hp:100'],
    ['E701_C', 'NARRATOR', '第二天，两具冰冷的尸体被抬出城外。而你，成了全城唯一幸存的人...', 'SELF:safety:DEAD;OTHER:safety:DEAD'],
    ['E701_C', 'NARRATOR', '余生，你再也无法直视镜中的自己。', 'PLAYER:Fame:-500;PLAYER:AddTag:COWARD'],
    
    # --- E702: 大义困境 - 叛军头领 ---
    ['E702_INTRO', 'NARRATOR', '牢房中，叛军首领{A}被五花大绑。', ''],
    ['E702_INTRO', 'NARRATOR', '十年前，正是他冒死将你从追兵刀下救出。', ''],
    ['E702_INTRO', 'SELF', '没想到...我们会以这种方式重逢。', ''],
    ['E702_INTRO', 'PLAYER', '你为何要造反？', ''],
    ['E702_INTRO', 'SELF', '朝廷腐败，民不聊生。我不得不反。', ''],
    ['E702_INTRO', 'NARRATOR', '城外，叛军余部虎视眈眈，扬言若官府处刑，便血洗全城。', ''],
    ['E702_INTRO', 'NARRATOR', '而朝廷悬赏千金，等你的答复...', 'SHOW_CHOICE'],
    
    ['E702_A', 'PLAYER', '（闭眼）来人，将犯人押送京城！', ''],
    ['E702_A', 'SELF', '我救你一命，你却...', ''],
    ['E702_A', 'PLAYER', '国法如山，私情难顾。', 'SELF:freedom:SLAVE;SELF:safety:EXECUTION'],
    ['E702_A', 'NARRATOR', '你收下赏金，却仿佛听到城外传来阵阵哭声...', 'PLAYER:Money:1000;PLAYER:Fame:500'],
    ['E702_A', 'NARRATOR', '{A}临刑前，仰天长叹：「世间再无义气可言...」', 'PLAYER:AddTag:LOYAL_COURT;SELF:affinity:PLAYER:-100'],
    
    ['E702_B', 'PLAYER', '（挥手让狱卒退下）...走吧。', ''],
    ['E702_B', 'SELF', '你...', ''],
    ['E702_B', 'PLAYER', '当年的恩情，今日还了。从此两清。', ''],
    ['E702_B', 'NARRATOR', '你亲自打开牢门，{A}深深看你一眼，消失在夜色中。', 'SELF:affinity:PLAYER:100;SELF:safety:NORMAL'],
    ['E702_B', 'NARRATOR', '此事若被朝廷得知...你可能万劫不复。', 'PLAYER:Fame:-300;PLAYER:AddTag:REBEL_FRIEND;PLAYER:safety:WANTED'],
    
    ['E702_C', 'PLAYER', '（拔出匕首）你...自己了断吧。', ''],
    ['E702_C', 'SELF', '...也罢。总好过受那凌迟之苦。', ''],
    ['E702_C', 'NARRATOR', '一声闷响后，牢房中只剩下沉默。', 'SELF:safety:DEAD'],
    ['E702_C', 'NARRATOR', '你对外宣称叛首越狱时被杀。这场风波，似乎就此平息...', 'PLAYER:Fame:100;PLAYER:AddTag:PRAGMATIC'],
    
    # --- E703: 打压困境 - 功臣震主 ---
    ['E703_INTRO', 'NARRATOR', '书房内，你看着手中的密报，眉头紧锁。', ''],
    ['E703_INTRO', 'NARRATOR', '你最得力的门客{A}，风头正劲，外间甚至有人称他为"小主人"。', ''],
    ['E703_INTRO', 'NARRATOR', '密报上说，{A}近来频繁与你的客户私下接触...', ''],
    ['E703_INTRO', 'PLAYER', '（自语）养虎为患...还是疑心生暗鬼？', ''],
    ['E703_INTRO', 'NARRATOR', '此时，{A}正在门外等候觐见。', 'SHOW_CHOICE'],
    
    ['E703_A', 'PLAYER', '（冷着脸）进来。', ''],
    ['E703_A', 'SELF', '主人唤我何事？', ''],
    ['E703_A', 'PLAYER', '你近来...似乎很忙啊。', ''],
    ['E703_A', 'NARRATOR', '你将几项莫须有的罪名扣在{A}头上，当众将他逐出门墙。', 'SELF:is_follower:False'],
    ['E703_A', 'SELF', '（咬牙）主人...我对您忠心耿耿，您却如此相待！', 'SELF:affinity:PLAYER:-100;SELF:emotion:ANGRY'],
    ['E703_A', 'NARRATOR', '外间议论纷纷，都说你卸磨杀驴、忘恩负义。', 'PLAYER:Fame:-150;PLAYER:AddTag:TYRANT;SELF:tags:BETRAYED'],
    
    ['E703_B', 'PLAYER', '（微笑）进来，坐。', ''],
    ['E703_B', 'SELF', '主人有何吩咐？', ''],
    ['E703_B', 'PLAYER', '你近来辛苦了。我决定...让你独当一面，负责东市的所有生意。', ''],
    ['E703_B', 'SELF', '（惊喜交加）主人...您信任我？', ''],
    ['E703_B', 'PLAYER', '疑人不用，用人不疑。', 'SELF:affinity:PLAYER:80;SELF:tags:LOYAL'],
    ['E703_B', 'NARRATOR', '你选择相信{A}。此举或许是慧眼识人，又或许...是引狼入室。', 'PLAYER:Fame:200;PLAYER:AddTag:MAGNANIMOUS'],
    
    ['E703_C', 'PLAYER', '（不动声色）让他等着。', ''],
    ['E703_C', 'NARRATOR', '你暗中安排人手，监视{A}的一举一动。', 'PLAYER:Money:-300'],
    ['E703_C', 'NARRATOR', '真相...早晚会水落石出。', 'SELF:emotion:NORMAL'],
    
    # --- E706: 道德困境 - 奴隶拍卖 ---
    ['E706_INTRO', 'NARRATOR', '奴隶市场上，人声鼎沸。', ''],
    ['E706_INTRO', 'NARRATOR', '一对母子{A}被分别推上拍卖台。', ''],
    ['E706_INTRO', 'SELF', '（声嘶力竭）求求各位大爷...买下我的孩子！他还小！', ''],
    ['E706_INTRO', 'NARRATOR', '孩子不过五六岁，脸上挂满泪痕，只知道哭喊着要娘。', ''],
    ['E706_INTRO', 'NARRATOR', '你摸了摸钱袋，发现只够买下一人...', 'SHOW_CHOICE'],
    
    ['E706_A', 'PLAYER', '（指向母亲）我买这个女人。', 'PLAYER:Money:-300'],
    ['E706_A', 'NARRATOR', '交易完成，母亲被带到你面前。', 'SELF:freedom:SERVANT;SELF:is_follower:True'],
    ['E706_A', 'SELF', '（扑通跪下）谢谢大人...但我的孩子...', ''],
    ['E706_A', 'NARRATOR', '她绝望地看向另一边，孩子正被一个肥头大耳的商人带走...', 'SELF:emotion:DESPAIR;SELF:tags:BROKEN'],
    ['E706_A', 'NARRATOR', '从此，她成了你最忠诚却也最沉默的仆人。', 'PLAYER:Fame:50'],
    
    ['E706_B', 'PLAYER', '（指向孩子）把那个孩子带过来。', 'PLAYER:Money:-200'],
    ['E706_B', 'NARRATOR', '你将孩子抱在怀里，他已经哭得没了力气。', ''],
    ['E706_B', 'SELF', '（泪流满面）谢谢大人...谢谢您救了我的孩子...', ''],
    ['E706_B', 'NARRATOR', '母亲被另一个买家带走时，不停地回头望向孩子...', ''],
    ['E706_B', 'NARRATOR', '你不知道这是否是正确的选择，但至少...孩子不会再受苦了。', 'PLAYER:Fame:100;PLAYER:AddTag:COMPASSION'],
    
    ['E706_C', 'NARRATOR', '你站在人群中，看着这一幕，却迈不动脚步。', ''],
    ['E706_C', 'PLAYER', '（自语）我...无能为力。', ''],
    ['E706_C', 'NARRATOR', '母子二人被不同的买家带走，从此天各一方。', 'SELF:emotion:DESPAIR'],
    ['E706_C', 'NARRATOR', '你转身离去，身后的哭声久久萦绕耳畔。', 'PLAYER:Fame:-50'],

    # --- E704: 人情困境 - 救命稻草 ---
    ['E704_INTRO', 'NARRATOR', '多年未见的故人{A}突然登门造访。', ''],
    ['E704_INTRO', 'SELF', '老朋友，我来找你帮个忙。', ''],
    ['E704_INTRO', 'NARRATOR', '他是当年变卖家产救你于绝境的恩人，如今却落魄潦倒。', ''],
    ['E704_INTRO', 'SELF', '市场上有个竞争对手{B}，我想让他消失。', ''],
    ['E704_INTRO', 'PLAYER', '这...', ''],
    ['E704_INTRO', 'SELF', '（阴沉）你欠我的，别忘了。若不帮忙，当年的丑闻...', ''],
    ['E704_INTRO', 'NARRATOR', '他手握你的把柄，正威胁着要公之于众。', 'SHOW_CHOICE'],
    
    ['E704_A', 'PLAYER', '（咬牙）好，我帮你。', ''],
    ['E704_A', 'NARRATOR', '你动用人脉，打压了{B}的生意。', 'OTHER:eco_status:POOR;OTHER:emotion:DESPAIR'],
    ['E704_A', 'SELF', '（满意）这才对嘛。', 'SELF:affinity:PLAYER:50;SELF:emotion:HAPPY'],
    ['E704_A', 'NARRATOR', '但你知道，从此你欠了一笔新的良心债...', 'PLAYER:Fame:-200;PLAYER:AddTag:BULLY'],
    
    ['E704_B', 'PLAYER', '不行！我不会做这种事！', ''],
    ['E704_B', 'SELF', '（冷笑）好，那就别怪我了。', ''],
    ['E704_B', 'NARRATOR', '三日后，你当年的丑闻传遍汴京...', 'PLAYER:Fame:-400;PLAYER:AddTag:SCANDAL'],
    ['E704_B', 'SELF', '（拂袖而去）你自作自受！', 'SELF:affinity:PLAYER:-80'],
    
    ['E704_C', 'PLAYER', '（沉默良久）...我有更好的办法。', ''],
    ['E704_C', 'NARRATOR', '你暗中安排人手...', ''],
    ['E704_C', 'NARRATOR', '数日后，{A}在回家的路上"失足"落入河中...', 'SELF:safety:DEAD'],
    ['E704_C', 'NARRATOR', '秘密永远被埋葬了。但你知道，你已经变成了曾经最厌恶的那种人。', 'PLAYER:Fame:-300;PLAYER:AddTag:ASSASSIN'],

    # --- E705: 复合困境 - 三角债 ---
    ['E705_INTRO', 'NARRATOR', '两个债主同时出现在你的厅堂。', ''],
    ['E705_INTRO', 'SELF', '欠债还钱，天经地义！', ''],
    ['E705_INTRO', 'OTHER', '我的钱你也该还了！', ''],
    ['E705_INTRO', 'NARRATOR', '你欠{A}和{B}各五百两，但你只有五百两。', ''],
    ['E705_INTRO', 'NARRATOR', '{A}是你的救命恩人，{B}手握你贪赃枉法的证据。', ''],
    ['E705_INTRO', 'NARRATOR', '两人虎视眈眈，等你做出选择。', 'SHOW_CHOICE'],
    
    ['E705_A', 'PLAYER', '（将钱袋递向{A}）恩公，这钱先还您。', ''],
    ['E705_A', 'SELF', '（点头）算你有良心。', 'SELF:affinity:PLAYER:50;SELF:emotion:HAPPY'],
    ['E705_A', 'OTHER', '（暴怒）好！你给我等着！', 'OTHER:affinity:PLAYER:-100;OTHER:emotion:ANGRY'],
    ['E705_A', 'NARRATOR', '数日后，你贪赃枉法的证据被公之于众...', 'PLAYER:AddTag:SCANDAL;PLAYER:Money:-500'],
    
    ['E705_B', 'PLAYER', '（将钱袋递向{B}）这钱先还您，封口费也在里面。', 'PLAYER:Money:-500'],
    ['E705_B', 'OTHER', '（满意）你很识时务。', 'OTHER:affinity:PLAYER:30;OTHER:emotion:NORMAL'],
    ['E705_B', 'SELF', '（愤怒）你...你宁可得罪恩人，也要讨好这种小人！', 'SELF:affinity:PLAYER:-100;SELF:emotion:ANGRY'],
    ['E705_B', 'NARRATOR', '恩人拂袖而去，从此与你恩断义绝。', ''],
    
    ['E705_C', 'PLAYER', '（摊手）我没钱了，你们看着办吧。', ''],
    ['E705_C', 'NARRATOR', '你当众宣布破产。', 'PLAYER:Money:-500;PLAYER:Fame:-200;PLAYER:eco_status:POOR'],
    ['E705_C', 'SELF', '（叹气）...罢了。', 'SELF:emotion:SAD'],
    ['E705_C', 'OTHER', '（冷笑）好，那我就让全城都知道你的底细！', 'OTHER:emotion:SAD;PLAYER:AddTag:SCANDAL'],

    # --- E707: 知情困境 - 致命秘密 ---
    ['E707_INTRO', 'NARRATOR', '无意间，你发现了一个惊天秘密。', ''],
    ['E707_INTRO', 'NARRATOR', '你最信任的门客{A}，竟然是朝廷通缉十年的重犯。', ''],
    ['E707_INTRO', 'NARRATOR', '他对你忠心耿耿，从未有过二心。', ''],
    ['E707_INTRO', 'NARRATOR', '但若被发现窝藏钦犯，你全家都要流放。', ''],
    ['E707_INTRO', 'PLAYER', '（看着通缉画像）这...怎么可能...', 'SHOW_CHOICE'],
    
    ['E707_A', 'PLAYER', '来人！拿下此人！', ''],
    ['E707_A', 'SELF', '（愕然）主人？', ''],
    ['E707_A', 'PLAYER', '你以为你能骗我到什么时候？', ''],
    ['E707_A', 'NARRATOR', '你将{A}交给官府，领取了八百两赏金。', 'PLAYER:Money:800;PLAYER:Fame:200'],
    ['E707_A', 'NARRATOR', '三日后，{A}被处以极刑...临行前，他只说了一句话：', 'SELF:freedom:SLAVE;SELF:safety:EXECUTION'],
    ['E707_A', 'SELF', '（绝望）我对得起你...你却对不起我...', 'SELF:affinity:PLAYER:-100'],
    
    ['E707_B', 'PLAYER', '（烧掉通缉令）我什么都没看到。', ''],
    ['E707_B', 'NARRATOR', '你选择为{A}保守秘密。', ''],
    ['E707_B', 'SELF', '（感激涕零）主人...您...', 'SELF:affinity:PLAYER:100;SELF:emotion:HAPPY'],
    ['E707_B', 'PLAYER', '从今往后，你就是新的人了。', ''],
    ['E707_B', 'NARRATOR', '但你知道，这是一颗随时可能引爆的炸弹...', 'PLAYER:Fame:-100;PLAYER:AddTag:HARBORER;PLAYER:safety:DANGER'],
    
    ['E707_C', 'PLAYER', '你走吧，越远越好。', ''],
    ['E707_C', 'SELF', '主人？', ''],
    ['E707_C', 'PLAYER', '拿着这些钱，找个没人认识你的地方，重新开始。', 'PLAYER:Money:-200'],
    ['E707_C', 'SELF', '（跪拜）主人大恩，{A}没齿难忘...', 'SELF:is_follower:False;SELF:affinity:PLAYER:30;SELF:emotion:SAD'],
    ['E707_C', 'NARRATOR', '你目送他消失在夜色中，不知此生是否还能再见。', ''],

    # --- E708: 继承困境 - 遗产纷争 ---
    ['E708_INTRO', 'NARRATOR', '富商{A}病榻前，你被托付了一个艰难的使命。', ''],
    ['E708_INTRO', 'SELF', '（气若游丝）我的遗产...全交给次子{B}...他在我床前尽孝...', ''],
    ['E708_INTRO', 'NARRATOR', '但按律，遗产当归长子。长子已放话，若不按律办，便告你侵吞。', ''],
    ['E708_INTRO', 'NARRATOR', '{A}握着你的手，眼中满是期盼。', ''],
    ['E708_INTRO', 'SELF', '求你了...按我的遗愿办...', 'SHOW_CHOICE'],
    
    ['E708_A', 'PLAYER', '放心，我一定按您的遗愿办。', ''],
    ['E708_A', 'SELF', '（欣慰地闭上眼睛）谢谢...', 'SELF:emotion:HAPPY'],
    ['E708_A', 'NARRATOR', '你将遗产分给了次子{B}。', 'OTHER:affinity:PLAYER:50'],
    ['E708_A', 'NARRATOR', '数日后，长子将你告上公堂...', 'PLAYER:Fame:100;PLAYER:safety:LAWSUIT'],
    
    ['E708_B', 'PLAYER', '（叹气）对不起，我只能按律办事。', ''],
    ['E708_B', 'SELF', '（痛苦）你...你答应过我的...', 'SELF:emotion:SAD'],
    ['E708_B', 'NARRATOR', '你将遗产判给了长子。次子跪在门外，久久不肯离去。', 'OTHER:emotion:ANGRY'],
    ['E708_B', 'NARRATOR', '众人皆说你秉公执法，但你知道，你辜负了临终之托。', 'PLAYER:Fame:100;PLAYER:AddTag:LAWFUL'],
    
    ['E708_C', 'PLAYER', '（看着遗产清单）这钱...我替他保管一段时间。', ''],
    ['E708_C', 'NARRATOR', '你巧立名目，将遗产据为己有。', 'PLAYER:Money:2000'],
    ['E708_C', 'SELF', '（绝望）你...你怎么能...', 'SELF:emotion:DESPAIR'],
    ['E708_C', 'OTHER', '（怒不可遏）贪得无厌的小人！', 'OTHER:affinity:PLAYER:-100'],
    ['E708_C', 'NARRATOR', '你发了一笔横财，但"无耻小人"的名声也传遍了汴京。', 'PLAYER:Fame:-500;PLAYER:AddTag:THIEF'],

    # --- E605: 叩阙求食（入门级事件） ---
    ['E605_INTRO', 'NARRATOR', '城门外，跪着一个衣衫褴褛的流民。', ''],
    ['E605_INTRO', 'SELF', '好心的大人...求您赏口饭吃...', ''],
    ['E605_INTRO', 'NARRATOR', '{A}已经三天没吃东西了，奄奄一息。', ''],
    ['E605_INTRO', 'NARRATOR', '城内物资紧张，守城的士兵正犹豫是否驱赶。', 'SHOW_CHOICE'],
    
    ['E605_A', 'PLAYER', '拿我的粮食，给他吃！', ''],
    ['E605_A', 'NARRATOR', '你将自己的口粮分给了流民。', 'PLAYER:inventory:GRAIN:-1'],
    ['E605_A', 'SELF', '（狼吞虎咽）谢谢...谢谢恩公...', 'SELF:emotion:HAPPY;SELF:hp:100'],
    ['E605_A', 'NARRATOR', '围观的百姓对你的善举交口称赞。', 'PLAYER:Fame:150'],
    
    ['E605_B', 'PLAYER', '（挥手）给我轰出去！', ''],
    ['E605_B', 'NARRATOR', '士兵上前，将流民拖走。', 'SELF:safety:DANGER;SELF:tags:HATED'],
    ['E605_B', 'SELF', '（绝望）大人...大人...', ''],
    ['E605_B', 'NARRATOR', '你的果断赢得了部分人的认可，但更多人在背后议论...', 'PLAYER:Fame:50;PLAYER:AddTag:CRUEL'],
    
    ['E605_C', 'NARRATOR', '你从他身边走过，没有停下脚步。', ''],
    ['E605_C', 'SELF', '（绝望地趴在地上）没人管我...', 'SELF:emotion:DESPAIR'],
    ['E605_C', 'NARRATOR', '又一个被时代抛弃的人，消失在城墙脚下...', 'PLAYER:Fame:-10'],

    # --- E402: 秘籍争夺 ---
    ['E402_INTRO', 'NARRATOR', '两个人为了一本秘籍打得头破血流。', ''],
    ['E402_INTRO', 'SELF', '这秘籍是我先发现的！', ''],
    ['E402_INTRO', 'OTHER', '胡说！明明是我的！', ''],
    ['E402_INTRO', 'NARRATOR', '{A}是你的门客，{B}是你的生意伙伴。', ''],
    ['E402_INTRO', 'NARRATOR', '但你知道，这本秘籍其实是假的...', 'SHOW_CHOICE'],
    
    ['E402_A', 'PLAYER', '住手！这秘籍归{A}！', ''],
    ['E402_A', 'SELF', '（感激）多谢主人！', 'SELF:emotion:HAPPY;SELF:affinity:PLAYER:50'],
    ['E402_A', 'OTHER', '（愤怒）你这是什么意思！', 'OTHER:hp:POOR;OTHER:affinity:PLAYER:-100'],
    
    ['E402_B', 'PLAYER', '住手！这秘籍归{B}！', ''],
    ['E402_B', 'OTHER', '（得意）总算有人说公道话！', 'OTHER:emotion:HAPPY;OTHER:affinity:PLAYER:50'],
    ['E402_B', 'SELF', '（绝望）主人...您怎么能...', 'SELF:hp:POOR;SELF:affinity:PLAYER:-80'],
    
    ['E402_C', 'PLAYER', '这秘籍是假的，你们被骗了。', ''],
    ['E402_C', 'NARRATOR', '你让学者验证，果然是赝品。', ''],
    ['E402_C', 'SELF', '（恼怒）什么？白打了？', 'SELF:emotion:ANGRY;SELF:affinity:PLAYER:-30'],
    ['E402_C', 'OTHER', '（愤怒）谁干的！', 'OTHER:emotion:ANGRY;OTHER:affinity:PLAYER:-30'],

    # --- E403: 镖局失信 ---
    ['E403_INTRO', 'NARRATOR', '镖局门口，一个寡妇正在哭诉。', ''],
    ['E403_INTRO', 'SELF', '那是我丈夫的遗物！你们怎么能弄丢！', ''],
    ['E403_INTRO', 'OTHER', '我们已经尽力了，实在抱歉...', ''],
    ['E403_INTRO', 'NARRATOR', '镖局总镖头{B}是你的结拜兄弟，寡妇{A}是你已故好友的遗孀。', 'SHOW_CHOICE'],
    
    ['E403_A', 'PLAYER', '兄弟，这件事你必须给个交代。', ''],
    ['E403_A', 'OTHER', '（无奈）好...我赔...', 'OTHER:affinity:PLAYER:-80'],
    ['E403_A', 'SELF', '（感激）谢谢您主持公道！', 'SELF:eco_status:ENOUGH;SELF:affinity:PLAYER:80'],
    
    ['E403_B', 'PLAYER', '嫂子，兄弟他也是无心之过...', ''],
    ['E403_B', 'SELF', '（绝望）你...你也帮着他说话...', 'SELF:emotion:DESPAIR;SELF:affinity:PLAYER:-80'],
    ['E403_B', 'OTHER', '（松了口气）多谢兄弟说情。', 'OTHER:affinity:PLAYER:50'],
    
    ['E403_C', 'PLAYER', '这钱我出，嫂子您收着。', 'PLAYER:Money:-400'],
    ['E403_C', 'SELF', '（感激）这...这怎么好意思...', 'SELF:affinity:PLAYER:50'],
    ['E403_C', 'OTHER', '（感激）兄弟仗义！', 'OTHER:affinity:PLAYER:30'],

    # --- E404: 冒名顶替 ---
    ['E404_INTRO', 'NARRATOR', '人群中传来一声怒喝。', ''],
    ['E404_INTRO', 'OTHER', '你竟敢冒充我的名号招摇撞骗！', ''],
    ['E404_INTRO', 'SELF', '（跪地求饶）大侠饶命！小的一时糊涂！', ''],
    ['E404_INTRO', 'NARRATOR', '骗子{A}是你失散多年的表弟，大侠{B}正要取他性命。', 'SHOW_CHOICE'],
    
    ['E404_A', 'PLAYER', '且慢！这人我来处置！', 'PLAYER:Money:-100'],
    ['E404_A', 'NARRATOR', '你出钱将表弟赎下。', ''],
    ['E404_A', 'SELF', '（感激）多谢表哥救命！', 'SELF:is_follower:True;SELF:affinity:PLAYER:60'],
    ['E404_A', 'OTHER', '（不满）哼，看你的面子。', 'OTHER:affinity:PLAYER:-80'],
    
    ['E404_B', 'NARRATOR', '你站在人群中，没有出声。', ''],
    ['E404_B', 'NARRATOR', '一道寒光闪过，你的表弟倒在血泊中...', 'SELF:safety:DEAD'],
    ['E404_B', 'OTHER', '（收剑）骗子，该杀。', 'OTHER:affinity:PLAYER:30;OTHER:emotion:HAPPY'],
    
    ['E404_C', 'PLAYER', '大侠，能否饶他一命，赶出江湖便是。', ''],
    ['E404_C', 'OTHER', '（考虑）...看你的面子，滚吧！', 'OTHER:affinity:PLAYER:-20'],
    ['E404_C', 'SELF', '（落荒而逃）谢谢表哥...', 'SELF:safety:EXILE;SELF:affinity:PLAYER:40'],

    # --- E405: 黑吃黑 ---
    ['E405_INTRO', 'NARRATOR', '深夜，你收到一封密信。', ''],
    ['E405_INTRO', 'NARRATOR', '你的债主{A}准备在今晚的交易中黑吃黑，对方{B}是你的救命恩人。', ''],
    ['E405_INTRO', 'NARRATOR', '交易地点就在城外破庙，刀斧手已经埋伏妥当。', ''],
    ['E405_INTRO', 'NARRATOR', '你该如何抉择？', 'SHOW_CHOICE'],
    
    ['E405_A', 'PLAYER', '（给{B}送信）今晚有危险，别去！', ''],
    ['E405_A', 'NARRATOR', '你冒险通风报信，救了恩人一命。', 'OTHER:affinity:PLAYER:80;OTHER:safety:NORMAL'],
    ['E405_A', 'NARRATOR', '但债主得知后，将你视为死敌...', 'SELF:affinity:PLAYER:-100;SELF:tags:ENEMY'],
    
    ['E405_B', 'PLAYER', '（带着手下赶往破庙）一起分赃！', ''],
    ['E405_B', 'NARRATOR', '你加入了黑吃黑，分得六百两赃款。', 'PLAYER:Money:600'],
    ['E405_B', 'NARRATOR', '而你的恩人{B}...永远留在了那个夜晚。', 'OTHER:safety:DEAD;PLAYER:AddTag:VILLAIN'],
    ['E405_B', 'SELF', '（狞笑）识时务者为俊杰！', 'SELF:affinity:PLAYER:50'],
    
    ['E405_C', 'PLAYER', '（向官府告发）两边都不是好人，一起抓！', ''],
    ['E405_C', 'NARRATOR', '你向官府告发，两边都被一网打尽。', ''],
    ['E405_C', 'SELF', '（在牢中）好...好...你等着！', 'SELF:freedom:PRISON;SELF:affinity:PLAYER:-100'],
    ['E405_C', 'OTHER', '（在牢中）你...', 'OTHER:freedom:PRISON;OTHER:affinity:PLAYER:-100'],
    ['E405_C', 'NARRATOR', '你得到了赏金和清白，但也结下了两个死仇。', 'PLAYER:Fame:300;PLAYER:Money:200'],

    # ═══════════════════════════════════════════════════════════════
    # 500系列：超自然与荒诞事件对话
    # ═══════════════════════════════════════════════════════════════
    
    # --- E501: 时间穿越者 ---
    ['E501_INTRO', 'NARRATOR', '街头突然一阵骚动，衙役正在追捕一个衣着怪异的男子。', ''],
    ['E501_INTRO', 'SELF', '（惊恐）各位大爷！这绝对是搞错了！我只是说了几句现代话！', ''],
    ['E501_INTRO', '衙役', '妖言惑众！他刚才说什么"YYDS"、"绝绝子"，一定是邪教咒语！', ''],
    ['E501_INTRO', 'SELF', '不是的！那只是夸奖的意思！拜托了各位！', ''],
    ['E501_INTRO', 'NARRATOR', '此人言行举止与常人迥异，你心中隐隐有种奇怪的熟悉感...', 'SHOW_CHOICE'],
    
    ['E501_A', 'PLAYER', '且慢！这人我来保释。', 'PLAYER:Money:-300'],
    ['E501_A', 'SELF', '（惊喜）你...你是老乡？', ''],
    ['E501_A', 'PLAYER', '（意味深长）也许是吧。', ''],
    ['E501_A', 'NARRATOR', '你带走了这个神秘男子。他究竟是疯子还是来自另一个时代？', 'SELF:tags:TIMETRAVELER;SELF:is_follower:True'],
    
    ['E501_B', 'PLAYER', '（低声对衙役）这种人...或许可以卖给那些研究奇技淫巧的术士。', ''],
    ['E501_B', '衙役', '（眼睛一亮）大人高见！', ''],
    ['E501_B', 'NARRATOR', '你得到了五百两赏金。至于那个可怜人会遭遇什么...你选择不去想。', 'PLAYER:Money:500;SELF:safety:DANGER'],
    
    ['E501_C', 'NARRATOR', '你摇摇头，从人群中走开。', ''],
    ['E501_C', 'SELF', '（绝望）大人！大人！救救我啊！', 'SELF:emotion:CONFUSED'],
    ['E501_C', 'NARRATOR', '你听不懂他在说什么，也不想听懂。', ''],

    # --- E502: 赛博机关人 ---
    ['E502_INTRO', 'NARRATOR', '你在街角撞见{A}时，他的袖口被划破了。', ''],
    ['E502_INTRO', 'NARRATOR', '透过破损的衣物，你看到的不是血肉，而是闪闪发光的齿轮和铜线。', ''],
    ['E502_INTRO', 'SELF', '（慌张地遮掩）这...这只是...', ''],
    ['E502_INTRO', 'PLAYER', '你不是人类。', ''],
    ['E502_INTRO', 'SELF', '（低头）...是的。但我有自己的思想和感情。', ''],
    ['E502_INTRO', 'NARRATOR', '面对这个超越认知的存在，你该如何抉择？', 'SHOW_CHOICE'],
    
    ['E502_A', 'PLAYER', '我什么都没看见。你的秘密在我这里很安全。', ''],
    ['E502_A', 'SELF', '（感激）您...您愿意接纳我？', 'SELF:tags:ROBOT;SELF:is_follower:True'],
    ['E502_A', 'NARRATOR', '你收留了这个非人的存在。也许有一天，他能告诉你更多关于这个世界的秘密。', 'PLAYER:Fame:-100'],
    
    ['E502_B', 'PLAYER', '来人！把它拆了，我要看看里面是什么构造！', ''],
    ['E502_B', 'SELF', '（恐惧）不...不要...', 'SELF:safety:DANGER'],
    ['E502_B', 'NARRATOR', '你的门客中恰好有钻研奇技的术士。这具机关人体给你带来了巨大的声望...', 'PLAYER:Fame:300;PLAYER:AddTag:SCIENTIST'],
    
    ['E502_C', 'NARRATOR', '你揉了揉眼睛，决定当自己什么都没看到。', ''],
    ['E502_C', 'SELF', '（如释重负）...', 'SELF:emotion:NORMAL'],
    ['E502_C', 'NARRATOR', '大概是最近太累了，产生幻觉了吧。', ''],

    # --- E503: 性别互换 ---
    ['E503_INTRO', 'NARRATOR', '一个娇滴滴的女子跪在你面前，泪流满面。', ''],
    ['E503_INTRO', 'SELF', '恩公！救救我！我本是张屠夫，三百斤的壮汉！', ''],
    ['E503_INTRO', 'PLAYER', '...什么？', ''],
    ['E503_INTRO', 'SELF', '那天我捡了一颗药丸，以为是仙丹吃了下去...醒来就变成了这样！', ''],
    ['E503_INTRO', 'NARRATOR', '她的声音虽然柔媚，但举止粗犷，确实不像寻常女子...', 'SHOW_CHOICE'],
    
    ['E503_A', 'PLAYER', '（眼珠一转）这副样貌...倒是有另一条出路。', ''],
    ['E503_A', 'SELF', '什么出路？', ''],
    ['E503_A', 'PLAYER', '甜水巷正缺新人。以你的姿色，保管日进斗金。', ''],
    ['E503_A', 'NARRATOR', '你将"她"送进了青楼。一年后，这位"花魁"成了汴京最红的舞姬。', 'PLAYER:Money:1000;SELF:eco_status:RICH;SELF:tags:DANCER'],
    
    ['E503_B', 'PLAYER', '我认识几个术士，或许能帮你恢复原状。', 'PLAYER:Money:-500'],
    ['E503_B', 'SELF', '（感激涕零）多谢恩公！', ''],
    ['E503_B', 'NARRATOR', '你花费重金四处寻找解药。虽然未能完全恢复，但张屠夫至少能过正常生活了。', 'SELF:tags:LOYAL'],
    
    ['E503_C', 'PLAYER', '你愿意在我府上做个家丁吗？包吃包住。', 'PLAYER:Money:-100'],
    ['E503_C', 'SELF', '（犹豫）...好吧。总比流落街头强。', 'SELF:is_follower:True'],
    ['E503_C', 'NARRATOR', '你招募了一个奇特的仆人。希望其他下人不会觉得奇怪。', ''],

    # --- E504: 古董成精 ---
    ['E504_INTRO', 'NARRATOR', '关于{A}家传家宝的流言越传越邪乎。', ''],
    ['E504_INTRO', 'SELF', '（惊恐）各位大人，小的真的不知道它为什么会说话！', ''],
    ['E504_INTRO', 'NARRATOR', '据说那个古董夜里会发出人声，引来了各方势力觊觎。', ''],
    ['E504_INTRO', 'NARRATOR', '{A}已经被围堵多日，走投无路。', 'SHOW_CHOICE'],
    
    ['E504_A', 'PLAYER', '这宝贝...我买了。开个价吧。', 'PLAYER:Money:-200'],
    ['E504_A', 'SELF', '（如释重负）给您给您！', 'SELF:eco_status:ENOUGH'],
    ['E504_A', 'NARRATOR', '你低价收购了这件神秘古董。是真有妖异还是人为炒作，只有时间能证明。', 'PLAYER:Fame:-50'],
    
    ['E504_B', 'PLAYER', '都是无稽之谈！我作证，这只是件普通古董！', ''],
    ['E504_B', 'NARRATOR', '你的辟谣让那些觊觎者悻悻离去。', ''],
    ['E504_B', 'SELF', '（感激）多谢恩公仗义执言！', 'SELF:safety:NORMAL;SELF:emotion:HAPPY'],
    ['E504_B', 'NARRATOR', '你的正义之举传开了。', 'PLAYER:Fame:100'],
    
    ['E504_C', 'PLAYER', '让我的学者朋友鉴定一下真伪。', ''],
    ['E504_C', 'NARRATOR', '学者经过仔细检验，发现古董里藏着一个精巧的机关发声装置。', ''],
    ['E504_C', 'NARRATOR', '原来是前任主人设计的防盗机关，被误传成了妖物。', 'PLAYER:Fame:150;PLAYER:Money:100'],

    # --- E505: 甚至不是人（Bug人） ---
    ['E505_INTRO', 'NARRATOR', '路边的{A}站姿僵硬，动作机械，仿佛...仿佛不是真实存在的。', ''],
    ['E505_INTRO', 'NARRATOR', '你仔细观察，发现他的轮廓偶尔会闪烁，像是...数据异常？', ''],
    ['E505_INTRO', 'SELF', '（声音卡顿）您...您好...今...今天...', ''],
    ['E505_INTRO', 'NARRATOR', '他说话也断断续续，似乎这个"人"的程序出了故障。', 'SHOW_CHOICE'],
    
    ['E505_A', 'PLAYER', '...我试试能不能帮你修复。', 'PLAYER:Money:-100'],
    ['E505_A', 'NARRATOR', '你不知道自己为什么会这么做，但你伸出手，在他身上比划了几下。', ''],
    ['E505_A', 'SELF', '（恢复正常）感谢您...我好多了。', 'SELF:emotion:NORMAL'],
    ['E505_A', 'NARRATOR', '也许这只是你的错觉吧。', 'PLAYER:Fame:50'],
    
    ['E505_B', 'PLAYER', '（低语）bug数据...必须删除。', ''],
    ['E505_B', 'NARRATOR', '你唤来手下，将这个"人"带走处理。', ''],
    ['E505_B', 'NARRATOR', '第二天，没有人记得这条街上曾有过这个人。', 'SELF:safety:DANGER;PLAYER:Fame:-100'],
    
    ['E505_C', 'NARRATOR', '你决定不去理会这种超出认知的事物。', ''],
    ['E505_C', 'NARRATOR', '（心中默念）这一定是我太累了产生的幻觉。提交工单，让运营去处理吧。', 'PLAYER:Fame:1'],
    
    # ═══════════════════════════════════════════════════════════════
    # 603-604系列：门客专属事件对话
    # ═══════════════════════════════════════════════════════════════
    
    # --- E603: 农田虫害 ---
    ['E603_INTRO', 'NARRATOR', '田间一片哀嚎，蝗虫遮天蔽日。', ''],
    ['E603_INTRO', 'SELF', '（欲哭无泪）今年的收成全完了...一家老小要饿死了...', ''],
    ['E603_INTRO', 'NARRATOR', '农夫{A}跪在地里，看着满目疮痍的庄稼。', ''],
    ['E603_INTRO', 'NARRATOR', '其他农民也聚了过来，一脸绝望。', 'SHOW_CHOICE'],
    
    ['E603_A', 'PLAYER', '先别慌，我出钱买些药来除虫。', 'PLAYER:Money:-50'],
    ['E603_A', 'SELF', '（感激）多谢恩公！', ''],
    ['E603_A', 'NARRATOR', '虽然损失惨重，但总算保住了部分收成。', 'SELF:inventory:GRAIN:5'],
    
    ['E603_B', 'PLAYER', '正好我府上有位精通农事的先生，让他来看看。', ''],
    ['E603_B', 'NARRATOR', '你的门客研究出一套科学的除虫方法，不仅保住了庄稼，还教会了农民们防治之法。', ''],
    ['E603_B', 'SELF', '（惊喜）今年竟然还能丰收！', 'SELF:inventory:GRAIN:15;SELF:emotion:HAPPY'],
    ['E603_B', 'NARRATOR', '你的善举传遍十里八乡。', 'PLAYER:Fame:200'],
    
    ['E603_C', 'PLAYER', '...去城隍庙烧香祈福吧，或许能感动上天。', ''],
    ['E603_C', 'SELF', '（无奈）也只能如此了...', 'SELF:emotion:NORMAL'],
    ['E603_C', 'NARRATOR', '你的建议虽然没什么实际帮助，但至少给了他们一点心理安慰。', 'PLAYER:Fame:-10'],

    # --- E604: 恶霸欺市 ---
    ['E604_INTRO', 'NARRATOR', '市场上传来一阵骚动。', ''],
    ['E604_INTRO', '恶霸', '这条街是我罩着的！你一个外来户也想在这摆摊？', ''],
    ['E604_INTRO', 'SELF', '大爷...小的只是讨口饭吃...', ''],
    ['E604_INTRO', 'NARRATOR', '恶霸一脚踢翻了{A}的货摊，围观的人群敢怒不敢言。', 'SHOW_CHOICE'],
    
    ['E604_A', 'PLAYER', '（上前）这位爷，给个面子，放他一马。这是一点心意。', 'PLAYER:Money:-100'],
    ['E604_A', '恶霸', '（接过银两）看在钱的份上，今天就饶了你！', ''],
    ['E604_A', 'SELF', '（感激）多谢恩公！', 'SELF:safety:NORMAL'],
    
    ['E604_B', 'PLAYER', '（一声呵斥）住手！', ''],
    ['E604_B', 'NARRATOR', '你的打手上前，将恶霸按倒在地。', ''],
    ['E604_B', '恶霸', '（惊恐）大人饶命！小的有眼不识泰山！', ''],
    ['E604_B', 'SELF', '（感激涕零）多谢大人相救！', 'SELF:money:20;SELF:emotion:HAPPY'],
    ['E604_B', 'NARRATOR', '你的威名在市场传开了。', 'PLAYER:Fame:150'],
    
    ['E604_C', 'PLAYER', '（大声）你知道我是谁吗？敢在我面前撒野！', ''],
    ['E604_C', 'NARRATOR', '恶霸一看你的衣着派头，顿时吓得屁滚尿流。', ''],
    ['E604_C', '恶霸', '是...是小的瞎了眼...', ''],
    ['E604_C', 'SELF', '谢谢大人！', 'SELF:emotion:NORMAL'],
    ['E604_C', 'NARRATOR', '恶霸落荒而逃。你的名声略有提升。', 'PLAYER:Fame:50'],
]

try:
    # 生成事件数据
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(headers)
        writer.writerows(events)
    print(f"[ok] 成功生成事件数据: {filepath}，共 {len(events)} 条事件")
    
    # 生成对话数据
    with open(dialog_filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(dialog_headers)
        writer.writerows(event_dialogs)
    print(f"[ok] 成功生成事件对话数据: {dialog_filepath}，共 {len(event_dialogs)} 句对话")
    
except Exception as e:
    print(f"[x] 生成失败: {e}")
