#!/usr/bin/env python3
"""
NPC头像预处理脚本
功能：
1. 将高分辨率头像转换为128x128标准尺寸
2. 保留原始高清版本到 avatars_hd 目录
3. 优化后的头像存到 avatars 目录供游戏使用

使用方法：
    python tools/process_avatars.py
"""

import os
import sys
from pathlib import Path
from PIL import Image

# 配置
SOURCE_DIR = Path("data/avatars")      # 源目录
OUTPUT_DIR = Path("assets/head_icon")     # 输出目录（游戏使用）
HD_BACKUP_DIR = Path("assets/head_icon_hd")  # 高清备份目录
TARGET_SIZE = (128, 128)               # 目标尺寸
SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp')

def process_avatar(input_path: Path, output_path: Path, size: tuple = TARGET_SIZE):
    """
    处理单个头像图片
    - 转换为RGBA模式
    - 缩放至目标尺寸（使用LANCZOS高质量缩放）
    - 保存为PNG
    """
    try:
        with Image.open(input_path) as img:
            # 转换为RGBA模式（支持透明）
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # 使用LANCZOS算法进行高质量缩放
            img_resized = img.resize(size, Image.Resampling.LANCZOS)
            
            # 保存
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img_resized.save(output_path, 'PNG', optimize=True)
            
        return True
    except Exception as e:
        print(f"  ❌ 处理失败 {input_path.name}: {e}")
        return False

def backup_hd_avatar(input_path: Path, backup_path: Path):
    """备份高清原图"""
    try:
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 如果备份目录中已存在同名文件，跳过
        if backup_path.exists():
            return True
            
        # 复制原文件
        import shutil
        shutil.copy2(input_path, backup_path)
        return True
    except Exception as e:
        print(f"  ❌ 备份失败 {input_path.name}: {e}")
        return False

def main():
    print("=" * 60)
    print("🎨 NPC头像预处理工具")
    print("=" * 60)
    print(f"\n📂 源目录: {SOURCE_DIR}")
    print(f"📂 输出目录: {OUTPUT_DIR}")
    print(f"📂 高清备份: {HD_BACKUP_DIR}")
    print(f"📐 目标尺寸: {TARGET_SIZE[0]}x{TARGET_SIZE[1]}")
    print()
    
    # 检查源目录
    if not SOURCE_DIR.exists():
        print(f"❌ 错误: 源目录不存在 {SOURCE_DIR}")
        sys.exit(1)
    
    # 收集所有图片文件（排除子目录中的）
    image_files = [
        f for f in SOURCE_DIR.iterdir() 
        if f.is_file() and f.suffix.lower() in SUPPORTED_FORMATS
    ]
    
    if not image_files:
        print("⚠️  未找到头像图片文件")
        sys.exit(0)
    
    print(f"🖼️  找到 {len(image_files)} 个头像文件")
    print()
    
    # 统计
    processed = 0
    skipped = 0
    failed = 0
    total_saved = 0
    
    for img_path in sorted(image_files):
        # 输出文件名（不含扩展名）
        name = img_path.stem
        output_path = OUTPUT_DIR / f"{name}.png"
        backup_path = HD_BACKUP_DIR / img_path.name
        
        print(f"🔄 处理: {img_path.name}", end=" ")
        
        # 获取原始文件大小
        original_size = img_path.stat().st_size
        
        # 备份高清版本
        if not backup_path.exists():
            backup_hd_avatar(img_path, backup_path)
        
        # 检查是否已存在优化版本
        if output_path.exists():
            print("⏭️  已存在，跳过")
            skipped += 1
            continue
        
        # 处理头像
        if process_avatar(img_path, output_path):
            # 计算节省的空间
            new_size = output_path.stat().st_size
            saved = original_size - new_size
            total_saved += saved
            
            # 获取原始尺寸信息
            with Image.open(img_path) as img:
                orig_w, orig_h = img.size
            
            print(f"✅ {orig_w}x{orig_h} -> {TARGET_SIZE[0]}x{TARGET_SIZE[1]} "
                  f"({original_size/1024:.1f}KB -> {new_size/1024:.1f}KB)")
            processed += 1
        else:
            failed += 1
    
    print()
    print("=" * 60)
    print("📊 处理结果")
    print("=" * 60)
    print(f"  ✅ 成功处理: {processed}")
    print(f"  ⏭️  跳过: {skipped}")
    print(f"  ❌ 失败: {failed}")
    print(f"  💾 节省空间: {total_saved / 1024 / 1024:.2f} MB")
    print()
    print(f"📂 优化后的头像已保存到: {OUTPUT_DIR}")
    print(f"📂 高清备份已保存到: {HD_BACKUP_DIR}")
    print()
    print("💡 提示：游戏将自动使用优化后的头像")
    print("=" * 60)

if __name__ == "__main__":
    main()
