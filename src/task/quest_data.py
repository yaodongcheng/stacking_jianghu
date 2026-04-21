# --- src/task/quest_data.py ---
"""
任务与对话的纯数据对象

策划须知：
- QuestData 一行 = quest_config.csv 的一行
- DialogData 一行 = dialog_config.csv 的一行
- 这两个类只负责"读 CSV、解析字段"，不含任何任务流转逻辑
- 想加新字段：直接在 __init__ 里读 row.get('字段名', 默认值) 即可
"""

from .npc_registry import get_speaker_id


class QuestData:
    """单个任务的静态配置（来自 quest_config.csv）"""

    def __init__(self, row):
        self.id = row['id']
        self.title = row['title']
        self.type = row['type']
        self.target = row['target']
        self.count = int(row['count'])
        self.next_id = row['next']
        self.desc = row['desc']
        self.submit_npc = row.get('submit_npc', '9000')
        self.submit_npc_id = self._resolve_submit_npc_id(self.submit_npc)
        self.scenario = row.get('scenario', '')

        # 委托型字段（设计文档 §3.2，全部可选 / 空 = "不适用"）
        # budget / reward 走 DSL，例如 "MONEY:300;ITEM:生鱼:3"；deadline 单位为天
        self.budget = (row.get('budget') or '').strip()
        self.reward = (row.get('reward') or '').strip()
        deadline_raw = (row.get('deadline') or '').strip()
        self.deadline = int(deadline_raw) if deadline_raw else 0

        # 通用触发字段（策划配置）
        # trigger 取值（策划在 quest_config.csv 直接看：
        #   NEWGAME           — 游戏新开局自动触发，只触发一次
        #   AUTO              — 上一段任务推进过来时，自动激活并播开场对白
        #   CLICKNPC:<NPC名>  — 等玩家点击/交互指定 NPC 触发
        #   空                — 旧配置兼容，按 submit_npc + 类型默认逻辑判断
        # precondition: 触发前置条件，目前支持 'true' / 空 = 始终通过；预留 flag 表达式扩展
        raw_trigger = (row.get('trigger') or '').strip()
        self.trigger_raw = raw_trigger          # 保留原始字符串供日志
        self.trigger_npc = ''                    # CLICKNPC 解析出的 NPC 名
        if ':' in raw_trigger:
            head, _, tail = raw_trigger.partition(':')
            self.trigger = head.strip().upper()
            self.trigger_npc = tail.strip()
        else:
            self.trigger = raw_trigger.upper()
        self.precondition = (row.get('precondition') or '').strip()

        # 分支任务支持
        # CHOICE 类型任务可以有多个后续分支
        # 格式: "next_good|next_evil" 或 "BRANCH_A:条件A|BRANCH_B:条件B"
        self.branches = {}  # {choice_key: next_quest_id}
        if self.type == 'CHOICE' and '|' in self.next_id:
            parts = self.next_id.split('|')
            for i, part in enumerate(parts):
                if ':' in part:
                    key, val = part.split(':', 1)
                    self.branches[key] = val
                else:
                    # 默认: 第一个是正义路线，第二个是邪恶路线
                    if i == 0:
                        self.branches['GOOD'] = part
                    else:
                        self.branches['EVIL'] = part

    @staticmethod
    def _resolve_submit_npc_id(submit_npc):
        """把 quest_config.csv 里的 submit_npc 字段（可能是 ID 或名字）标准化为 int ID。
        空 / 解析不出来 → None（表示"无指定 NPC"）。
        """
        s = (submit_npc or '').strip()
        if not s:
            return None
        if s.isdigit():
            return int(s)
        return get_speaker_id(s)


class DialogData:
    """单条对话（来自 dialog_config.csv）"""

    def __init__(self, row):
        self.quest_id = row['quest_id']
        self.speaker = row['speaker']
        # CSV 里的 \n 文本转成真换行
        raw_text = row['text']
        self.text = raw_text.replace('\\n', '\n') if raw_text else ''
        self.bg_img = row['bg_img']
        self.action = row['action']
        self.speaker_id = get_speaker_id(self.speaker)
