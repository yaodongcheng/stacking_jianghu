# --- copyCode.py ---
#!/usr/bin/env python3
"""
将项目中的所有代码文件内容合并，并复制到剪贴板。
用法: python copy_code_to_clipboard.py [项目目录]
如果没有指定目录，则使用当前工作目录。
"""

import os
import sys
import argparse

# 想要包含的文件扩展名（可根据需要增删）
CODE_EXTENSIONS = {
    '.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.htm', '.css', '.scss',
    '.csv', '.kt', '.kts', '.c', '.cpp', '.h', '.hpp', '.cs', '.go',
    '.rb', '.php', '.swift', '.m', '.mm', '.rs', '.json', '.xml', '.yaml',
    '.yml', '.md', '.rst', '.txt', '.sh', '.bash', '.zsh', '.ps1', '.bat',
    '.cmake', '.sql', '.graphql', '.vue', '.svelte', '.tf', '.dockerfile',
    '.ini', '.cfg', '.conf', '.properties'
}

# 需要排除的目录名称（支持通配，这里简单用全名匹配）
EXCLUDE_DIRS = {
    '.git', '__pycache__', 'node_modules', '.idea', '.vscode',
    'build', 'dist', 'target', 'venv', 'env', '.env', 'out'
}

# 需要排除的文件（完全匹配文件名）
EXCLUDE_FILES = {
    '.DS_Store', 'Thumbs.db'
}

def collect_files(root_dir):
    """收集所有符合条件的文件路径"""
    collected = []
    
    # 特殊处理：确保根目录下的 game_log.txt 被包含，方便反馈
    log_file = os.path.join(root_dir, 'game_log.txt')
    if os.path.exists(log_file):
        collected.append(log_file)

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # 跳过排除的目录
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        for filename in filenames:
            if filename in EXCLUDE_FILES:
                continue
            
            # 避免重复添加 game_log.txt
            if filename == 'game_log.txt':
                continue

            ext = os.path.splitext(filename)[1].lower()
            if ext in CODE_EXTENSIONS:
                full_path = os.path.join(dirpath, filename)
                collected.append(full_path)
    return sorted(collected)

def read_file_content(file_path):
    """读取文件内容，尝试用 utf-8 编码，失败则跳过"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # 可能是二进制文件，跳过
        return None
    except Exception as e:
        print(f"警告：无法读取文件 {file_path} - {e}")
        return None

def copy_to_clipboard(text):
    """将文本复制到剪贴板"""
    try:
        import pyperclip
        pyperclip.copy(text)
        print("[ok] 内容已复制到剪贴板！")
    except ImportError:
        # 如果没有 pyperclip，尝试使用系统命令
        print("[!] 未安装 pyperclip，尝试使用系统剪贴板命令...")
        copied = False
        if sys.platform == 'win32':
            # Windows: clip
            import subprocess
            try:
                subprocess.run('clip', input=text.encode('utf-16'), check=True)
                copied = True
            except Exception as e:
                print(f"[x] 使用 clip 失败: {e}")
        elif sys.platform == 'darwin':
            # macOS: pbcopy
            import subprocess
            try:
                subprocess.run('pbcopy', input=text.encode('utf-8'), check=True)
                copied = True
            except Exception as e:
                print(f"[x] 使用 pbcopy 失败: {e}")
        else:
            # Linux: 尝试 xclip 或 xsel
            import subprocess
            for cmd in ['xclip -selection clipboard', 'xsel -b']:
                try:
                    subprocess.run(cmd.split(), input=text.encode('utf-8'), check=True)
                    copied = True
                    break
                except (subprocess.SubprocessError, FileNotFoundError):
                    continue
        if copied:
            print("[ok] 内容已复制到剪贴板！")
        else:
            print("[x] 无法复制到剪贴板，请安装 pyperclip 或手动复制输出。")

def main():
    parser = argparse.ArgumentParser(description="将项目代码合并到剪贴板")
    parser.add_argument('directory', nargs='?', default='.',
                        help='要扫描的项目目录（默认当前目录）')
    args = parser.parse_args()

    root_dir = os.path.abspath(args.directory)
    if not os.path.isdir(root_dir):
        print(f"错误：目录不存在 - {root_dir}")
        sys.exit(1)

    print(f"扫描目录: {root_dir}")
    files = collect_files(root_dir)
    print(f"找到 {len(files)} 个代码文件")

    if not files:
        print("没有找到任何代码文件。")
        return

    # 构建输出文本
    output_lines = []
    for file_path in files:
        # 获取相对路径，使输出更简洁
        rel_path = os.path.relpath(file_path, root_dir)
        content = read_file_content(file_path)
        if content is None:
            continue

        # 添加文件头（使用注释，可以根据扩展名选择注释风格，这里统一用简单标记）
        output_lines.append(f"# --- {rel_path} ---")
        output_lines.append(content)
        output_lines.append("\n")  # 分隔

    final_text = "\n".join(output_lines)
    print(f"总字符数: {len(final_text)}")

    copy_to_clipboard(final_text)

if __name__ == "__main__":
    main()
    