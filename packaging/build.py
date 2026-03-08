#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
堆叠江湖 - 一键打包脚本
支持 Windows 和 macOS

使用方法:
    python build.py              # 打包当前平台
    python build.py --clean      # 清理并重新打包
    python build.py --onefile    # 打包为单文件
    python build.py --console    # 保留控制台窗口（调试用）
"""

import sys
import os

# 设置 stdout 编码为 utf-8（解决 GitHub Actions Windows 环境的编码问题）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import json
import shutil
import subprocess
import argparse
from pathlib import Path

# 获取项目根目录（packaging 的父目录）
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "packaging"))
from build_config import BUILD_CONFIG, get_platform_config


def clean_build():
    """清理构建目录"""
    dirs_to_remove = ["build", "dist", "__pycache__"]
    files_to_remove = ["*.spec", "堆叠江湖.spec"]
    
    print("🧹 清理构建目录...")
    
    # 删除目录
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"  删除: {dir_name}/")
    
    # 删除根目录的 spec 文件
    for pattern in files_to_remove:
        for file_path in Path(".").glob(pattern):
            if file_path.parent == Path("."):  # 只在根目录查找
                file_path.unlink()
                print(f"  删除: {file_path}")
    
    print("✅ 清理完成\n")


def move_spec_to_build():
    """将生成的 spec 文件移动到 build 目录"""
    spec_file = Path("堆叠江湖.spec")
    if spec_file.exists():
        build_dir = Path("build")
        build_dir.mkdir(exist_ok=True)
        target = build_dir / spec_file.name
        shutil.move(str(spec_file), str(target))
        print(f"  移动 spec 文件到: {target}")


def check_pyinstaller():
    """检查 PyInstaller 是否安装"""
    try:
        import PyInstaller
        return True
    except ImportError:
        print("❌ PyInstaller 未安装")
        print("正在安装 PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✅ PyInstaller 安装完成\n")
        return True


def build_app(onefile=False, console=False, clean=False):
    """
    构建应用程序
    
    Args:
        onefile: 是否打包为单文件
        console: 是否保留控制台窗口
        clean: 是否先清理构建目录
    """
    # 切换到项目根目录执行构建
    original_dir = os.getcwd()
    os.chdir(PROJECT_ROOT)
    
    if clean:
        clean_build()
    
    check_pyinstaller()
    
    platform_config = get_platform_config()
    
    # 构建 PyInstaller 命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        BUILD_CONFIG["main_script"],
        "--name", BUILD_CONFIG["name"],
        "--noconfirm",
        "--distpath", str(PROJECT_ROOT / "release"),  # 输出到 release 目录（绝对路径）
        "--workpath", str(PROJECT_ROOT / "build"),    # 临时文件到 build 目录（绝对路径）
        "--specpath", str(PROJECT_ROOT / "build"),    # spec 文件到 build 目录（绝对路径）
    ]
    
    # 单文件或单目录
    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")
    
    # 窗口模式
    if not console:
        cmd.append("--windowed")
    
    # 图标
    if platform_config["icon"] and os.path.exists(platform_config["icon"]):
        cmd.extend(["--icon", platform_config["icon"]])
    
    # 添加数据文件（使用绝对路径）
    for src, dst in BUILD_CONFIG["datas"]:
        src_path = PROJECT_ROOT / src
        if src_path.exists():
            cmd.extend(["--add-data", f"{src_path}{platform_config['separator']}{dst}"])
    
    # 隐藏导入
    for hidden in BUILD_CONFIG["hidden_imports"]:
        cmd.extend(["--hidden-import", hidden])
    
    # 排除模块
    for exclude in BUILD_CONFIG["excludes"]:
        cmd.extend(["--exclude-module", exclude])
    
    # 运行时钩子（用于处理配置文件路径）
    hooks_dir = "hooks"
    if os.path.exists(hooks_dir):
        cmd.extend(["--runtime-hook", os.path.join(hooks_dir, "runtime_hook.py")])
    
    print(f"🔨 开始构建 {BUILD_CONFIG['name']} v{BUILD_CONFIG['version']}...")
    print(f"   平台: {sys.platform}")
    print(f"   模式: {'单文件' if onefile else '单目录'}")
    print(f"   控制台: {'保留' if console else '隐藏'}")
    print()
    
    # 执行构建
    try:
        subprocess.check_call(cmd)
        
        # 移动 spec 文件到 build 目录
        move_spec_to_build()
        
        print(f"\n✅ 构建成功!")
        
        # 显示输出路径
        output_dir = "release"
        app_name = BUILD_CONFIG["name"]
        if sys.platform == "win32":
            app_name += ".exe"
        
        output_path = os.path.join(output_dir, app_name)
        if os.path.exists(output_path):
            print(f"📦 输出文件: {os.path.abspath(output_path)}")
            
            # 计算文件大小
            if os.path.isfile(output_path):
                size = os.path.getsize(output_path)
                print(f"📊 文件大小: {size / 1024 / 1024:.1f} MB")
            else:
                # 目录大小
                total_size = sum(
                    os.path.getsize(os.path.join(dirpath, filename))
                    for dirpath, dirnames, filenames in os.walk(output_path)
                    for filename in filenames
                )
                print(f"📊 目录大小: {total_size / 1024 / 1024:.1f} MB")
        
        # 显示配置信息
        print("\n📋 配置说明:")
        print("   配置文件位置: user_config/ai_config.json")
        print("   玩家可以在游戏内设置面板配置 AI 参数")
        
        print("\n🎉 构建完成! 请查看 release 目录")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 构建失败: {e}")
        sys.exit(1)


def create_user_config_template():
    """创建用户配置模板"""
    user_config_dir = Path("user_config")
    user_config_dir.mkdir(exist_ok=True)
    
    template_file = user_config_dir / "ai_config.json"
    if not template_file.exists():
        # 创建默认配置模板
        default_config = {
            "_comment": "堆叠江湖 - AI 配置文件",
            "_warning": "请勿分享包含 API Key 的配置文件！",
            "llm": {
                "enabled": False,
                "api_key": "",
                "api_base": "https://api.deepseek.com",
                "model": "deepseek-chat",
                "max_tokens": 500,
                "temperature": 0.85
            },
            "image": {
                "enabled": False,
                "api_key": "",
                "api_base": "https://ark.cn-beijing.volces.com/api/v3",
                "model": "doubao-seedream-5-0-260128"
            },
            "director": {
                "use_llm": False,
                "interval_ms": 60000
            }
        }
        with open(template_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        print(f"✓ 已创建用户配置模板: {template_file}")


def main():
    parser = argparse.ArgumentParser(description="堆叠江湖打包工具")
    parser.add_argument("--clean", action="store_true", help="清理构建目录")
    parser.add_argument("--onefile", action="store_true", help="打包为单文件")
    parser.add_argument("--console", action="store_true", help="保留控制台窗口")
    
    args = parser.parse_args()
    
    build_app(
        onefile=args.onefile,
        console=args.console,
        clean=args.clean
    )


if __name__ == "__main__":
    main()