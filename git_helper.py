#!/usr/bin/env python3
"""
Git 快捷操作脚本 - 堆叠江湖项目管理工具
用法: python git_helper.py [命令]
"""

import sys
import os
import subprocess

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def run_cmd(cmd, check=True):
    """运行 shell 命令"""
    print(f"{Colors.BLUE}> {cmd}{Colors.RESET}")
    # Windows 下使用 gbk 编码
    import sys
    encoding = 'gbk' if sys.platform == 'win32' else 'utf-8'
    # Windows 下使用 git bash
    if sys.platform == 'win32' and not cmd.startswith('"'):
        git_path = r'"C:\Program Files\Git\bin\git.exe"'
        if cmd.startswith('git '):
            cmd = cmd.replace('git ', git_path + ' ', 1)
    result = subprocess.run(cmd, shell=True, capture_output=True)
    if result.stdout:
        try:
            print(result.stdout.decode(encoding, errors='ignore'))
        except:
            print(result.stdout.decode('utf-8', errors='ignore'))
    if result.stderr and check:
        try:
            print(f"{Colors.RED}{result.stderr.decode(encoding, errors='ignore')}{Colors.RESET}")
        except:
            print(f"{Colors.RED}{result.stderr.decode('utf-8', errors='ignore')}{Colors.RESET}")
    return result.returncode == 0

def status():
    """查看当前状态"""
    print(f"\n{Colors.YELLOW}=== Git 状态 ==={Colors.RESET}")
    run_cmd("git status -s")
    print(f"\n{Colors.YELLOW}=== 最近提交 ==={Colors.RESET}")
    run_cmd("git log --oneline -5")
    print(f"\n{Colors.YELLOW}=== 当前分支 ==={Colors.RESET}")
    run_cmd("git branch -v")

def commit():
    """提交更改"""
    # 检查是否有更改
    import sys
    encoding = 'gbk' if sys.platform == 'win32' else 'utf-8'
    git_path = r'"C:\Program Files\Git\bin\git.exe"' if sys.platform == 'win32' else 'git'
    result = subprocess.run(f"{git_path} status --porcelain", shell=True, capture_output=True)
    stdout = result.stdout.decode(encoding, errors='ignore') if result.stdout else ""
    if not stdout.strip():
        print(f"{Colors.YELLOW}没有需要提交的更改{Colors.RESET}")
        return
    
    # 添加所有更改
    print(f"\n{Colors.YELLOW}=== 添加更改 ==={Colors.RESET}")
    if not run_cmd("git add -A"):
        return
    
    # 显示更改的文件
    print(f"\n{Colors.YELLOW}=== 待提交文件 ==={Colors.RESET}")
    run_cmd("git status -s")
    
    # 输入提交信息
    msg = input(f"\n{Colors.GREEN}输入提交信息 (直接回车使用默认'更新代码'): {Colors.RESET}").strip()
    if not msg:
        msg = "更新代码"
    
    # 提交
    print(f"\n{Colors.YELLOW}=== 提交 ==={Colors.RESET}")
    if run_cmd(f'git commit -m "{msg}"'):
        print(f"{Colors.GREEN}✓ 提交成功{Colors.RESET}")
    else:
        print(f"{Colors.RED}✗ 提交失败{Colors.RESET}")

def push():
    """推送到远程"""
    print(f"\n{Colors.YELLOW}=== 推送到远程 ==={Colors.RESET}")
    if run_cmd("git push origin main"):
        print(f"{Colors.GREEN}✓ 推送成功{Colors.RESET}")
    else:
        print(f"{Colors.RED}✗ 推送失败{Colors.RESET}")

def commit_and_push():
    """提交并推送"""
    commit()
    push()

def commit_and_build():
    """提交并触发打包"""
    commit()
    push()
    
    print(f"\n{Colors.YELLOW}=== 触发打包 ==={Colors.RESET}")
    
    # 删除并重新创建标签
    run_cmd("git tag -d v1.0.0", check=False)
    run_cmd("git push origin :refs/tags/v1.0.0", check=False)
    run_cmd("git tag v1.0.0")
    
    if run_cmd("git push origin v1.0.0"):
        print(f"{Colors.GREEN}✓ 打包已触发，请访问 GitHub Actions 查看进度{Colors.RESET}")
        print(f"{Colors.BLUE}  https://github.com/yaodongcheng/stacking_jianghu/actions{Colors.RESET}")
    else:
        print(f"{Colors.RED}✗ 触发打包失败{Colors.RESET}")

def log():
    """查看提交历史"""
    print(f"\n{Colors.YELLOW}=== 提交历史 ==={Colors.RESET}")
    run_cmd("git log --oneline -20 --graph")

def reset():
    """回退到指定版本"""
    print(f"\n{Colors.YELLOW}=== 可用版本 ==={Colors.RESET}")
    run_cmd("git log --oneline -10")
    
    commit_hash = input(f"\n{Colors.GREEN}输入要回退的版本号 (完整或前7位): {Colors.RESET}").strip()
    if not commit_hash:
        print(f"{Colors.RED}未输入版本号，取消操作{Colors.RESET}")
        return
    
    confirm = input(f"{Colors.RED}警告: 这将丢失当前未提交的更改！确认回退到 {commit_hash}? (y/N): {Colors.RESET}").strip().lower()
    if confirm != 'y':
        print(f"{Colors.YELLOW}已取消{Colors.RESET}")
        return
    
    print(f"\n{Colors.YELLOW}=== 回退中 ==={Colors.RESET}")
    if run_cmd(f"git reset --hard {commit_hash}"):
        run_cmd("git push origin main --force")
        print(f"{Colors.GREEN}✓ 回退成功并已强制推送到远程{Colors.RESET}")
    else:
        print(f"{Colors.RED}✗ 回退失败{Colors.RESET}")

def build_only():
    """仅触发打包（不提交）"""
    print(f"\n{Colors.YELLOW}=== 触发打包 ==={Colors.RESET}")
    run_cmd("git tag -d v1.0.0", check=False)
    run_cmd("git push origin :refs/tags/v1.0.0", check=False)
    run_cmd("git tag v1.0.0")
    
    if run_cmd("git push origin v1.0.0"):
        print(f"{Colors.GREEN}✓ 打包已触发{Colors.RESET}")
    else:
        print(f"{Colors.RED}✗ 触发失败{Colors.RESET}")

def help_menu():
    """显示帮助"""
    print(f"""
{Colors.YELLOW}=== 堆叠江湖 Git 快捷工具 ==={Colors.RESET}

用法: python git_helper.py [命令]

命令:
  status    - 查看 Git 状态
  commit    - 提交更改 (会提示输入提交信息)
  push      - 推送到远程
  cp        - 提交并推送 (commit + push)
  build     - 提交并触发打包 (commit + push + tag)
  buildonly - 仅触发打包 (不提交代码)
  log       - 查看提交历史
  reset     - 回退到指定版本
  help      - 显示此帮助

示例:
  python git_helper.py status     # 查看状态
  python git_helper.py commit     # 提交更改
  python git_helper.py build      # 提交并打包
  python git_helper.py reset      # 回退版本
""")

def main():
    if len(sys.argv) < 2:
        help_menu()
        return
    
    command = sys.argv[1].lower()
    
    # 切换到项目目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    commands = {
        'status': status,
        's': status,
        'commit': commit,
        'c': commit,
        'push': push,
        'p': push,
        'cp': commit_and_push,
        'build': commit_and_build,
        'b': commit_and_build,
        'buildonly': build_only,
        'bo': build_only,
        'log': log,
        'l': log,
        'reset': reset,
        'r': reset,
        'help': help_menu,
        'h': help_menu,
    }
    
    if command in commands:
        try:
            commands[command]()
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}操作已取消{Colors.RESET}")
    else:
        print(f"{Colors.RED}未知命令: {command}{Colors.RESET}")
        help_menu()

if __name__ == "__main__":
    main()