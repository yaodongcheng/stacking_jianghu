# 🎮 AI 配置指南

欢迎使用《堆叠江湖》！本游戏支持 AI 驱动的动态内容生成。

## 🔑 配置方式（二选一）

### 方式一：游戏内设置（推荐）

1. **启动游戏**
2. **打开设置面板**：按 `ESC` 键或点击设置按钮
3. **填写 AI 配置**：
   - **模型名称**：如 `deepseek-chat`、`gpt-3.5-turbo`
   - **Base URL**：API 服务器地址
   - **API Key**：你的 API 密钥
4. **点击保存**：配置会自动保存

### 方式二：编辑配置文件

配置文件位于游戏目录下：
- **Windows**: `游戏目录/user_config/ai_config.json`
- **macOS**: `堆叠江湖.app/Contents/Resources/user_config/ai_config.json`

用文本编辑器打开并修改：

```json
{
  "llm": {
    "api_key": "sk-你的API密钥",
    "api_base": "https://api.deepseek.com/v1",
    "model": "deepseek-chat",
    "enabled": true
  },
  "image": {
    "api_key": "你的图像API密钥",
    "api_base": "https://ark.cn-beijing.volces.com/api/v3",
    "model": "doubao-seedream-5-0-260128",
    "enabled": true
  }
}
```

---

## 🌐 推荐服务商

### LLM（文本生成）

| 服务商 | Base URL | 模型示例 |
|--------|----------|----------|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| OpenAI | `https://api.openai.com/v1` | `gpt-3.5-turbo` |
| 阿里云 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-turbo` |

### 图像生成

| 服务商 | Base URL | 模型示例 |
|--------|----------|----------|
| 豆包 | `https://ark.cn-beijing.volces.com/api/v3` | `doubao-seedream-5-0-260128` |

---

## 💡 常见问题

**Q: API Key 安全吗？**
A: 密钥只存储在你的本地电脑，不会上传。

**Q: 会产生费用吗？**
A: 会。API 调用费用由服务商收取，请查看他们的定价页面。

**Q: 不想用 AI 功能怎么办？**
A: 可以不配置，游戏会正常使用默认内容。

**Q: 配置不生效？**
A: 检查 JSON 格式是否正确，API Key 是否有效。

---

**祝你游戏愉快！** 🎉
