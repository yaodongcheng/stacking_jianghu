# --- src/ai/constants.py ---
"""
AI系统常量定义
从原ai_system.py抽离，避免循环导入
"""

# 战斗参数常量
COMBAT_FACE_DIST = 55      # 双方面对面保持的间距(px)
COMBAT_ATTACK_RANGE = 85   # 出拳判定范围
SPECTATE_RADIUS_MIN = 160  # 围观最小半径
SPECTATE_RADIUS_MAX = 310  # 围观最大半径
SPECTATE_NOTICE_RADIUS = 600  # 听闻战斗广播事件的最大距离
SPECTATE_DURATION = 10.0  # 围观持续时间(秒)

# 感知范围
SCAN_RADIUS = 400    # 索敌范围
SEE_RADIUS = 250     # 视觉感知半径

# 阵营定义
HOSTILE_JOBS = {'BANDIT', 'THUG'}
NEUTRAL_JOBS = {'OFFICIAL', 'GUARD', 'FARMER', 'MERCHANT',
                'SCHOLAR', 'MONK', 'ARTISAN', 'NONE', 'PLAYER'}

# 冷却时间（毫秒）
HATE_COOLDOWN_MS = 3000      # 仇恨累加冷却
ALLY_HATE_COOLDOWN_MS = 5000  # 同盟援助仇恨冷却
PASSIVE_HATE_COOLDOWN_MS = 5000  # 被动仇恨冷却
INTERCEPT_COOLDOWN_SEC = 30   # 拦截冷却（秒）

# 护卫拦截参数
INTERCEPT_RANGE = 180  # 拦截触发距离

# 组织系统
RALLY_RADIUS = 500        # 集结号召范围
RALLY_COOLDOWN = 5.0      # 集结冷却时间(秒)
FOLLOW_DISTANCE_MIN = 40  # 跟随最小距离
FOLLOW_DISTANCE_MAX = 80  # 跟随最大距离