# --- src/task/action_dispatcher.py ---
"""
Action 指令分发器

策划须知：
- CSV 里 dialog 的 action 字段 / quest 的 action 字段都走这里
- 想加新动作 → 在 actions/ 下新建 handler 文件即可（自动加载）
- 想给某个动作打"演出标签"（让调试跳过停下来）→ 改下面 CINEMATIC_ACTIONS 集合

支持格式：
- 单条：ACTION_NAME 或 ACTION_NAME:PARAM1:PARAM2
- 多条：用 ; 分隔，例如 "SHAKE_CAMERA:5;SET_AFFINITY:鱼西施:+30"
"""

# 演出型 action：调试跳过时执行后停下来让玩家观看
CINEMATIC_ACTIONS = {
    # 动画/演出
    'POPI_FLEE',              # 泼皮逃跑
    'EVENT_NPC_RELEASE',      # 释放事件 NPC
    # 战斗相关
    'KNOCKOUT',               # 击倒玩家
    'START_AUTO_COMBAT',      # 自动战斗
    'PLAYER_DEFEATED',        # 玩家被打倒
    'PLAYER_ATTACK_POPI',     # 玩家攻击泼皮
    'START_COMBAT_BULLY',     # 与泼皮战斗
    # 生成/伏击
    'SPAWN_ENEMY_NEAR',
    'SPAWN_BULLY_FOR_REVENGE',
    'TRIGGER_REVENGE_AMBUSH',
    # 屏幕效果
    'FADE_TO_BLACK', 'FADE_FROM_BLACK', 'FLASH_WHITE',
    # 传送
    'TELEPORT_PLAYER',
}


def is_cinematic_action(action_str):
    """判断 action 是否是"演出型"（调试跳过时不能跳）"""
    if not action_str:
        return False
    base = action_str.split(':')[0]
    return base in CINEMATIC_ACTIONS


class ActionDispatcher:
    """Action 指令分发器。挂在 QuestManager 上，通过 self.qm 访问 handler 注册表。"""

    def __init__(self, qm):
        self.qm = qm

    def trigger(self, action_name, ctx=None):
        """执行 action 指令（支持 ; 分隔的多条指令）"""
        if not action_name:
            return
        for directive in action_name.split(';'):
            directive = directive.strip()
            if directive:
                self._execute_single(directive, ctx)

    def _execute_single(self, action_str, ctx=None):
        """执行单条 action 指令。"""
        qm = self.qm
        parts = action_str.split(':')
        base_action = parts[0].upper()
        params = parts[1:]

        print(f"[Quest] >>> 执行动作: {base_action}" + (f" 参数: {params}" if params else ""))

        # 1. 优先用本地 action_handlers
        if base_action in qm.action_handlers:
            handler = qm.action_handlers[base_action]
            try:
                if params:
                    handler(qm, ctx, *params)
                else:
                    handler(qm, ctx)
            except TypeError:
                # 兼容老 handler 签名
                try:
                    handler(qm)
                except TypeError:
                    handler()
            return

        # 2. 兜底：交给 StoryDirectiveExecutor
        try:
            from src.story.story_directive_executor import get_directive_executor
            executor = get_directive_executor()
            if ctx:
                executor.bind_context(ctx)
            if executor.execute(action_str):
                return
        except Exception as e:
            print(f"[Quest] StoryDirective 执行失败: {e}")

        print(f"[Quest] [!] 未知动作: {base_action}")
