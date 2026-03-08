# 堆叠江湖 (Stacking Jianghu)

一款AI驱动的武侠江湖模拟游戏。

## 游戏简介

在《堆叠江湖》中，你将扮演一名江湖人士，通过收集物品、合成装备、完成任务来在武侠世界中生存和发展。游戏特色包括：

- 🤖 **AI驱动剧情** - 由大语言模型生成的动态事件和剧情
- 🎨 **AI配图** - 豆包AI为每个事件生成独特配图
- 🎴 **卡牌合成** - 收集物品卡牌，探索合成配方
- ⚔️ **武侠生存** - 管理气血、内力、饱食度，在江湖中活下去

## 快速开始

### Windows
1. 下载 `stacking_jianghu_windows.zip`
2. 解压到任意文件夹
3. 双击 `堆叠江湖.exe` 运行

### macOS
1. 下载 `堆叠江湖_macOS.dmg`
2. 打开DMG，将应用拖到 Applications 文件夹
3. 从启动台运行游戏

## 配置AI

游戏需要配置AI API Key才能体验完整功能：

1. 首次运行后，点击右上角「设置」
2. 在AI配置面板填入：
   - DeepSeek API Key（用于剧情生成）
   - 豆包 API Key（用于图片生成）
3. 点击保存，重新启动游戏

> 提示：你可以只配置其中一个AI，游戏会相应调整功能

## 目录说明

```
堆叠江湖/
├── 堆叠江湖.exe          # 主程序
├── _internal/            # 游戏资源（勿删）
├── user_config/          # 用户配置（可备份）
│   └── ai_config.json    # AI配置
└── image_cache/          # AI生成图片缓存（可清理）
```

## 系统要求

- **Windows**: Windows 10/11, 64位
- **macOS**: macOS 11 (Big Sur) 或更高版本
- **内存**: 4GB+
- **存储**: 500MB 可用空间
- **网络**: 需要网络连接AI服务

## 开发

```bash
# 克隆仓库
git clone https://github.com/yaodongcheng/stacking_jianghu.git
cd stacking_jianghu

# 安装依赖
pip install -r requirements.txt

# 运行游戏
python main.py

# 打包
python packaging/build.py
```

## 技术栈

- Python 3.12
- Pygame - 游戏引擎
- PyInstaller - 打包工具
- DeepSeek API - 文本生成
- 豆包 API - 图像生成

## 开源协议

MIT License

## 致谢

感谢所有测试玩家和贡献者！