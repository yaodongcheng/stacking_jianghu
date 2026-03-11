#!/usr/bin/env python3
"""
Git 图形化快捷工具 - 极简弹窗版
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
import subprocess
import sys
import os

# 切换到项目目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

GIT_PATH = r"C:\Program Files\Git\cmd\git.exe"

#Releally？

def run_git(cmd):
    """运行 git 命令"""
    full_cmd = cmd.replace('git ', f'"{GIT_PATH}" ', 1)
    result = subprocess.run(full_cmd, shell=True, capture_output=True)
    stdout = result.stdout.decode('gbk', errors='ignore') if result.stdout else ""
    stderr = result.stderr.decode('gbk', errors='ignore') if result.stderr else ""
    return result.returncode == 0, stdout, stderr


def get_status():
    """获取当前状态"""
    success, stdout, _ = run_git("git status --porcelain")
    if success:
        return stdout.strip()
    return ""


def commit(push_after=False):
    """提交更改"""
    status = get_status()
    if not status:
        messagebox.showinfo("提示", "没有需要提交的更改")
        return False
    
    # 添加并提交
    run_git("git add -A")
    msg = simpledialog.askstring("提交", "输入提交信息:", initialvalue="更新代码")
    if not msg:
        return False
    
    success, stdout, stderr = run_git(f'git commit -m "{msg}"')
    if success:
        if push_after:
            push()
        else:
            messagebox.showinfo("成功", "本地提交成功！\n记得点击'推送'上传到 GitHub")
        return True
    else:
        messagebox.showerror("错误", f"提交失败:\n{stderr}")
        return False


def push():
    """推送到远程"""
    success, stdout, stderr = run_git("git push origin main")
    if success:
        messagebox.showinfo("成功", "已推送到 GitHub！")
        return True
    else:
        messagebox.showerror("错误", f"推送失败:\n{stderr}")
        return False


def build():
    """触发打包"""
    run_git("git tag -d v1.0.0")
    run_git("git push origin :refs/tags/v1.0.0")
    run_git("git tag v1.0.0")
    success, _, stderr = run_git("git push origin v1.0.0")
    if success:
        messagebox.showinfo("成功", "打包已触发！\n请访问 GitHub Actions 查看进度")
        return True
    else:
        messagebox.showerror("错误", f"触发打包失败:\n{stderr}")
        return False


def commit_and_build():
    """提交并打包"""
    if commit():
        if push():
            build()


def reset():
    """回退版本"""
    # 获取最近提交
    success, stdout, _ = run_git("git log --oneline -10")
    if not success:
        messagebox.showerror("错误", "无法获取提交历史")
        return
    
    # 显示提交历史并询问
    msg = "最近提交:\n\n" + stdout + "\n\n输入要回退的版本号 (前7位即可):"
    commit_hash = simpledialog.askstring("回退版本", msg)
    
    if not commit_hash:
        return
    
    if not messagebox.askyesno("确认", f"确定要回退到 {commit_hash}?\n这将丢失当前未提交的更改！"):
        return
    
    success, _, stderr = run_git(f"git reset --hard {commit_hash}")
    if success:
        run_git("git push origin main --force")
        messagebox.showinfo("成功", "回退成功并已强制推送！")
    else:
        messagebox.showerror("错误", f"回退失败:\n{stderr}")


def main():
    """主界面"""
    root = tk.Tk()
    root.title("Git 快捷工具")
    root.geometry("300x250")
    root.resizable(False, False)
    
    # 居中显示
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - 150
    y = (root.winfo_screenheight() // 2) - 125
    root.geometry(f'+{x}+{y}')
    
    # 标题
    tk.Label(root, text="堆叠江湖 - Git 工具", font=("Microsoft YaHei", 16, "bold"), pady=20).pack()
    
    # 按钮
    btn_width = 20
    btn_height = 2
    
    tk.Button(root, text="📤 提交并推送", width=btn_width, height=btn_height,
              font=("Microsoft YaHei", 11),
              command=lambda: [commit(push_after=True), root.update()]).pack(pady=5)
    
    tk.Button(root, text="🚀 提交并打包", width=btn_width, height=btn_height,
              font=("Microsoft YaHei", 11), bg="#4CAF50", fg="white",
              command=lambda: [commit_and_build(), root.update()]).pack(pady=5)
    
    tk.Button(root, text="⏪ 回退版本", width=btn_width, height=btn_height,
              font=("Microsoft YaHei", 11), bg="#f44336", fg="white",
              command=lambda: [reset(), root.update()]).pack(pady=5)
    
    # 状态显示
    status_text = get_status()
    if status_text:
        tk.Label(root, text="有未提交的更改", fg="orange", font=("Microsoft YaHei", 9)).pack(pady=5)
    else:
        tk.Label(root, text="工作区干净", fg="green", font=("Microsoft YaHei", 9)).pack(pady=5)
    
    root.mainloop()


if __name__ == "__main__":
    main()