# --- src/story/__init__.py ---
"""
剧情指令系统 - StoryDirective

统一的剧情指令体系，让AI生成的动态剧情能够真正影响游戏世界。
"""

from .story_directive_executor import StoryDirectiveExecutor

__all__ = ['StoryDirectiveExecutor']
