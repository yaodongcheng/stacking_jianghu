# --- src/task/actions/__init__.py ---
"""
Action Handler 注册表

合并所有子模块的 HANDLERS dict，供 QuestManager 统一使用。
每个子模块导出 HANDLERS: dict[str, Callable]，
函数签名统一为 (quest_mgr, ctx, *params)。
"""

from .cinematic import HANDLERS as _CINEMATIC
from .economy import HANDLERS as _ECONOMY
from .faction import HANDLERS as _FACTION
from .tutorial import HANDLERS as _TUTORIAL
from .yuxishi_event import HANDLERS as _YUXISHI

ALL_HANDLERS = {}
ALL_HANDLERS.update(_CINEMATIC)
ALL_HANDLERS.update(_ECONOMY)
ALL_HANDLERS.update(_FACTION)
ALL_HANDLERS.update(_TUTORIAL)
ALL_HANDLERS.update(_YUXISHI)
