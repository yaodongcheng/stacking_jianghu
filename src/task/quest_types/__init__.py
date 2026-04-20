# --- src/task/quest_types/__init__.py ---
"""
任务类型插件目录

启动时自动加载本目录下所有非下划线开头的 .py 文件。
策划新建一个文件，只要文件里用了 @register 装饰器，就自动生效。
"""

import importlib
import pkgutil

from ._base import QuestType, register, get, is_auto_activate

# 自动加载所有插件文件
for _, modname, _ in pkgutil.iter_modules(__path__):
    if not modname.startswith('_'):
        importlib.import_module(f'.{modname}', __name__)


__all__ = ['QuestType', 'register', 'get', 'is_auto_activate']
