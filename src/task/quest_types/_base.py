# --- src/task/quest_types/_base.py ---
"""
任务类型插件基类

策划须知：
====================================================================
想加一种新任务类型？三步：
  1. 在 quest_types/ 目录下新建 xxx.py
  2. 写一个继承 QuestType 的类，覆盖你需要的方法
  3. 用 @register 装饰器注册即可，无需改任何其它文件

每个任务类型最多回答 4 个问题：
  - auto_activate    : 上一段任务完成后，本段是否自动激活（不需要去找 NPC 接取）
  - objective_text(q): 详情面板"完成条件"字段显示什么
  - progress_text(q, player, all_cards): 侧边栏的进度文字（如 "(3/5)"）
  - can_act(q, dragged, target, recipe_mgr): 玩家这步操作允不允许做
====================================================================

注意：判断"任务是否完成"在 goal_checkers.py 里（已经是注册表模式），
本文件不重复实现。两套注册表职责互补：
  - goal_checkers : 何时判定完成
  - QuestType     : 完成前后该如何展示/限制
"""

from typing import Optional


# 全局注册表
_REGISTRY: dict[str, "QuestType"] = {}


class QuestType:
    """所有任务类型的基类。子类只需覆盖关心的字段/方法。"""

    name: str = ""              # 任务类型名（必须唯一，与 quest_config.csv 的 type 列匹配）
    auto_activate: bool = False  # 接到下一段后是否自动激活（不需要找 NPC）

    def objective_text(self, q) -> str:
        """详情面板"完成条件"显示文案。空字符串表示不显示。"""
        return ""

    def progress_text(self, q, player, all_cards) -> str:
        """侧边栏的进度文字（如 "(3/5)" 或 "(进行中)"）。空字符串表示无进度。"""
        if q.count > 0:
            return f"(0/{q.count})"
        return ""

    def can_act(self, q, dragged_card, target_card, recipe_mgr=None) -> tuple[bool, str]:
        """玩家拖拽卡牌时，是否允许这次操作。
        Returns: (允许?, 不允许时的提示文字)
        """
        return True, ""


def register(cls):
    """装饰器：把任务类型注册到全局表。
    用法：
        @register
        class GatherType(QuestType):
            name = "GATHER"
            ...
    """
    if not cls.name:
        raise ValueError(f"{cls.__name__} 缺少 name 字段")
    _REGISTRY[cls.name] = cls()
    return cls


_DEFAULT = QuestType()  # 未注册类型的兜底


def get(type_name: str) -> QuestType:
    """根据类型名取插件。未注册返回默认实例（一切按默认行为）。"""
    return _REGISTRY.get(type_name, _DEFAULT)


def is_auto_activate(type_name: str) -> bool:
    """快捷查询：某个类型是否需要自动激活"""
    return get(type_name).auto_activate
