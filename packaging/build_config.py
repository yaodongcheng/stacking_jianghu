#!/usr/bin/env python3
"""
堆叠江湖 - 构建配置文件
支持 Windows 和 macOS 打包
"""

import sys
import os

# 应用信息
APP_NAME = "堆叠江湖"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Your Name"

# 打包配置
BUILD_CONFIG = {
    # 主入口文件
    "main_script": "main.py",
    
    # 应用名称
    "name": APP_NAME,
    
    # 版本号
    "version": APP_VERSION,
    
    # 窗口化应用（无控制台）
    "windowed": True,
    
    # 单文件模式（False=单目录，启动更快；True=单文件，分发更方便）
    "onefile": False,
    
    # 需要包含的数据文件/目录
    # 注意：
    #   - 不打包 user_config，避免打包本地开发配置（API Key等）
    #   - 不打包 assets/image_cache，这是玩家运行时生成的AI图片缓存
    # 玩家首次运行时会自动创建这些目录
    "datas": [
        ("assets/head_icon", "assets/head_icon"),  # NPC头像
        ("assets/story", "assets/story"),          # 剧情图片
        # assets/image_cache 不打包！玩家本地生成
        ("data", "data"),
        ("src", "src"),
    ],
    
    # 需要包含的隐藏导入
    "hidden_imports": [
        "pygame",
        "requests",
        "urllib3",
        "certifi",
        "charset_normalizer",
        "idna",
        # LLM 相关依赖
        "aiohttp",
        "aiohttp.client",
        "openai",
        "httpx",
    ],
    
    # 排除的模块（减小体积）
    # 注意：不要排除 Python 标准库的核心模块，可能导致兼容性问题
    "excludes": [
        # GUI 相关
        "tkinter",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "wx",
        "kivy",
        
        # 数据科学（游戏不需要）
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "sklearn",
        
        # 图像处理（如果不用）
        "PIL",
        "Pillow",
        "imageio",
        
        # 测试和文档
        "pytest",
        "unittest",
        "pydoc",
        "doctest",
        "sphinx",
        
        # 网络协议（保留 requests 即可）
        "ftplib",
        "poplib",
        "imaplib",
        "nntplib",
        "smtplib",
        "telnetlib",
        
        # 注意：不要排除 email，pkg_resources 依赖它
        # "email",
        
        # 数据库
        "sqlite3",
        "dbm",
        
        # 其他
        "turtledemo",
        "idlelib",
    ],
    
    # 图标文件
    "icon_windows": "assets/icon.ico" if os.path.exists("assets/icon.ico") else None,
    "icon_macos": "assets/icon.icns" if os.path.exists("assets/icon.icns") else None,
}

def get_platform_config():
    """获取当前平台的配置"""
    if sys.platform == "win32":
        return {
            "icon": BUILD_CONFIG["icon_windows"],
            "extension": ".exe",
            "separator": ";",
        }
    elif sys.platform == "darwin":
        return {
            "icon": BUILD_CONFIG["icon_macos"],
            "extension": "",
            "separator": ":",
        }
    else:
        return {
            "icon": None,
            "extension": "",
            "separator": ":",
        }
