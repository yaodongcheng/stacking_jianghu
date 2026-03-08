# 游戏打包与发布指南

## 📦 打包系统概述

本项目使用 **PyInstaller** 进行打包，支持 Windows 和 macOS 双平台。

### 特性

- ✅ **用户自定义 AI 配置**：玩家可独立配置 LLM 和图像生成 API
- ✅ **跨平台支持**：Windows (.exe) 和 macOS (.app)
- ✅ **自动配置模板**：打包时自动生成配置文件模板
- ✅ **智能配置加载**：优先加载用户配置，回退到默认配置

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install pyinstaller
```

### 2. 运行打包脚本

```bash
# Windows - 生成目录版（推荐，启动更快）
python build.py

# Windows - 生成单文件版
python build.py --onefile

# macOS
python build.py
```

### 3. 输出位置

- **Windows**: `dist/堆叠江湖/`
- **macOS**: `dist/堆叠江湖.app/`

---

## 📁 配置文件说明（便携模式）

### 配置文件位置

配置文件会和可执行程序放在一起，采用**便携模式**：

#### Windows
```
游戏目录/
├── 堆叠江湖.exe
├── user_config/
│   └── ai_config.json    ← 配置文件在这里
├── assets/
└── data/
```

#### macOS
```
堆叠江湖.app/
└── Contents/
    └── Resources/
        ├── user_config/
        │   └── ai_config.json    ← 配置文件在这里
        └── ...
```

### 便携模式的优势

- ✅ **移动方便**：复制整个游戏文件夹即可，配置跟着走
- ✅ **备份简单**：直接备份游戏目录即可
- ✅ **多份配置**：可以在不同位置放置多份游戏，各自独立配置
- ✅ **无需管理员权限**：不需要写入系统目录

### 配置模板

打包后的游戏目录包含 `user_config/` 文件夹，内有默认配置模板。

### 后备机制

如果找不到本地配置，游戏会尝试从系统配置目录加载（便于迁移旧配置）。

---

## ⚙️ 配置项说明

### LLM 配置 (llm)

| 字段 | 说明 | 示例 |
|------|------|------|
| `api_key` | LLM API 密钥 | `sk-xxxxxxxx...` |
| `api_base` | API 基础 URL | `https://api.deepseek.com/v1` |
| `model` | 模型名称 | `deepseek-chat` |
| `enabled` | 是否启用 | `true` / `false` |
| `max_tokens` | 最大生成 token 数 | `500` |
| `temperature` | 生成温度 (0-1) | `0.85` |

### 图像生成配置 (image)

| 字段 | 说明 | 示例 |
|------|------|------|
| `api_key` | 图像 API 密钥 | `xxxxxxxx...` |
| `api_base` | API 基础 URL | `https://ark.cn-beijing.volces.com/api/v3` |
| `model` | 模型名称 | `doubao-seedream-5-0-260128` |
| `enabled` | 是否启用 | `true` / `false` |

### 导演系统配置 (director)

| 字段 | 说明 | 示例 |
|------|------|------|
| `interval_ms` | 事件触发间隔（毫秒） | `60000` |
| `use_llm` | 是否使用 LLM 生成事件 | `true` / `false` |

---

## 🔧 打包配置

### build_config.py

修改此文件可自定义打包参数：

```python
APP_NAME = "堆叠江湖"           # 应用名称
APP_VERSION = "1.0.0"          # 版本号
ICON_WINDOWS = "icon.ico"      # Windows 图标
ICON_MACOS = "icon.icns"       # macOS 图标
```

### 包含的文件

默认包含以下文件/目录：
- `assets/` - 游戏资源
- `data/` - 游戏数据
- `fonts/` - 字体文件

---

## 🖥️ 平台特定说明

### Windows

- 生成 `.exe` 可执行文件
- 支持 Windows 10/11
- 需要 Visual C++ Redistributable（通常已安装）

### macOS

- 生成 `.app` 应用包
- 支持 macOS 10.15+
- 首次运行可能需要右键打开（未签名应用）
- 如需签名分发，需要 Apple Developer 账号

---

## 📋 发布清单

发布前请确认：

- [ ] 运行 `python build.py` 成功
- [ ] 测试生成的可执行文件能正常启动
- [ ] 检查 `user_config_template.json` 已包含在发布包中
- [ ] 编写玩家配置指南（如何填写 API Key）
- [ ] 在 README 中说明配置文件的存放位置

---

## 🐛 常见问题

### Q: 玩家如何配置自己的 API Key？

A: 有两种方式：

**方式一：游戏内设置（推荐）**
1. 启动游戏
2. 按 ESC 或点击设置按钮打开设置面板
3. 在 AI 配置区域填写 API Key、Base URL 和模型名称
4. 点击保存

**方式二：手动编辑配置文件**
1. 找到游戏目录下的 `user_config/ai_config.json`
2. 用文本编辑器打开
3. 填写 API Key 等信息
4. 保存文件

### Q: 配置文件在哪里？

A: 配置文件与游戏可执行程序放在一起（便携模式）：
- **Windows**: `游戏目录/user_config/ai_config.json`
- **macOS**: `堆叠江湖.app/Contents/Resources/user_config/ai_config.json`

### Q: 打包后的游戏找不到资源文件？

A: 确保 `build_config.py` 中的 `datas` 包含了所有需要的资源目录。

### Q: macOS 提示"无法打开应用"？

A: 右键点击应用图标，选择"打开"。这是因为应用未签名，首次运行需要手动允许。

### Q: 如何备份或迁移配置？

A: 由于是便携模式，直接复制整个游戏文件夹即可，配置会一起被复制。

### Q: 如何更新游戏而不丢失玩家配置？

A: 由于配置与游戏放在一起，更新时**不要删除** `user_config` 文件夹，只替换其他文件即可。

---

## 📚 相关文件

| 文件 | 说明 |
|------|------|
| `build.py` | 打包脚本 |
| `build_config.py` | 打包配置 |
| `src/user_config.py` | 用户配置管理器 |
| `user_config_template.json` | 配置模板 |
| `src/llm/config.py` | LLM 配置类 |

---

## 🔗 参考链接

- [PyInstaller 文档](https://pyinstaller.org/en/stable/)
- [Python 打包最佳实践](https://packaging.python.org/)
