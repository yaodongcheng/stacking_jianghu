# src/llm/config.py
"""
LLM配置管理 - 支持游戏设置界面输入API Key
包含：
- DeepSeek LLM API（文本生成）
- 豆包生图 API（图片生成）

【更新说明】v2.0 支持用户自定义配置
- 优先从用户配置目录加载（%APPDATA%/堆叠江湖/ai_config.json）
- 支持打包后独立配置
"""

import os
import json
from pathlib import Path

class LLMConfig:
    """LLM服务配置管理器 - 支持用户自定义配置"""
    
    # 默认配置（作为后备）
    DEFAULT_CONFIG = {
        # === DeepSeek LLM 配置 ===
        "api_key": "",
        "api_base": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "enabled": False,
        
        # === 通用 LLM 参数 ===
        "max_tokens": 500,
        "temperature": 0.85,
        "max_retries": 3,
        "timeout": 30,
        
        # === 豆包生图 API 配置 ===
        "doubao_api_key": "",
        "doubao_api_base": "https://ark.cn-beijing.volces.com/api/v3",
        "doubao_model": "doubao-seedream-5-0-260128",
        "doubao_enabled": False,
        
        # === 导演系统配置 ===
        "director_interval_ms": 60000,
        "director_use_llm": False,
    }
    
    _instance = None
    _config = None
    _user_config_loaded = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        return cls()
    
    def _load_config(self):
        """加载配置文件（优先从用户配置加载）"""
        self._config = self.DEFAULT_CONFIG.copy()
        
        # 首先尝试加载用户配置
        try:
            from src.user_config import get_user_config
            user_cfg = get_user_config()
            
            # 获取 LLM 配置
            llm_config = user_cfg.get_llm_config()
            image_config = user_cfg.get_image_config()
            director_config = user_cfg.get_director_config()
            
            # 合并配置
            self._config.update({
                # LLM 配置
                "api_key": llm_config.get("api_key", ""),
                "api_base": llm_config.get("api_base", self.DEFAULT_CONFIG["api_base"]),
                "model": llm_config.get("model", self.DEFAULT_CONFIG["model"]),
                "enabled": llm_config.get("enabled", False),
                "max_tokens": llm_config.get("max_tokens", self.DEFAULT_CONFIG["max_tokens"]),
                "temperature": llm_config.get("temperature", self.DEFAULT_CONFIG["temperature"]),
                "max_retries": llm_config.get("max_retries", self.DEFAULT_CONFIG["max_retries"]),
                "timeout": llm_config.get("timeout", self.DEFAULT_CONFIG["timeout"]),
                
                # 图像配置
                "doubao_api_key": image_config.get("api_key", ""),
                "doubao_api_base": image_config.get("api_base", self.DEFAULT_CONFIG["doubao_api_base"]),
                "doubao_model": image_config.get("model", self.DEFAULT_CONFIG["doubao_model"]),
                "doubao_enabled": image_config.get("enabled", False),
                
                # 导演配置
                "director_interval_ms": director_config.get("interval_ms", self.DEFAULT_CONFIG["director_interval_ms"]),
                "director_use_llm": director_config.get("use_llm", self.DEFAULT_CONFIG["director_use_llm"]),
            })
            
            self._user_config_loaded = True
            print(f"[LLMConfig] 已从用户配置加载")
            return
            
        except Exception as e:
            print(f"[LLMConfig] 用户配置加载失败，回退到本地配置: {e}")
        
        # 回退到本地配置文件
        config_file = self._get_config_file_path()
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    self._config.update(saved_config)
                print(f"[LLMConfig] 已加载本地配置文件: {config_file}")
            except Exception as e:
                print(f"[LLMConfig] 本地配置文件加载失败: {e}")
        else:
            print(f"[LLMConfig] 配置文件不存在，使用默认配置")
    
    def _get_config_file_path(self) -> Path:
        """获取配置文件路径（支持打包后）"""
        import sys
        if getattr(sys, 'frozen', False):
            # 打包后的可执行文件
            if sys.platform == "darwin":
                # macOS .app 包结构
                return Path(sys.executable).parent.parent / "Resources" / "data" / "llm_config.json"
            else:
                return Path(sys.executable).parent / "data" / "llm_config.json"
        else:
            # 开发环境
            return Path(__file__).parent.parent.parent / "data" / "llm_config.json"
    
    def _save_config(self):
        """保存配置到用户配置目录（与可执行程序一起）"""
        try:
            # 使用 UserConfig 保存到本地（便携模式）
            from src.user_config import get_user_config
            user_cfg = get_user_config()
            
            # 构建配置数据
            config_data = {
                "llm": {
                    "api_key": self._config.get("api_key", ""),
                    "api_base": self._config.get("api_base", self.DEFAULT_CONFIG["api_base"]),
                    "model": self._config.get("model", self.DEFAULT_CONFIG["model"]),
                    "enabled": self._config.get("enabled", False),
                    "max_tokens": self._config.get("max_tokens", self.DEFAULT_CONFIG["max_tokens"]),
                    "temperature": self._config.get("temperature", self.DEFAULT_CONFIG["temperature"]),
                    "max_retries": self._config.get("max_retries", self.DEFAULT_CONFIG["max_retries"]),
                    "timeout": self._config.get("timeout", self.DEFAULT_CONFIG["timeout"]),
                },
                "image": {
                    "api_key": self._config.get("doubao_api_key", ""),
                    "api_base": self._config.get("doubao_api_base", self.DEFAULT_CONFIG["doubao_api_base"]),
                    "model": self._config.get("doubao_model", self.DEFAULT_CONFIG["doubao_model"]),
                    "enabled": self._config.get("doubao_enabled", False),
                },
                "director": {
                    "interval_ms": self._config.get("director_interval_ms", self.DEFAULT_CONFIG["director_interval_ms"]),
                    "use_llm": self._config.get("director_use_llm", self.DEFAULT_CONFIG["director_use_llm"]),
                }
            }
            
            # 保存到用户配置（本地优先）
            if user_cfg.save_config(config_data):
                print(f"[LLMConfig] 配置已保存")
                return True
            else:
                raise Exception("UserConfig 保存失败")
            
        except Exception as e:
            print(f"[LLMConfig] 保存配置失败: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════
    # DeepSeek LLM 属性
    # ═══════════════════════════════════════════════════════════════
    
    @property
    def api_key(self):
        return self._config.get("api_key", "")
    
    @api_key.setter
    def api_key(self, value):
        self._config["api_key"] = value
        # 有API Key时自动启用
        if value:
            self._config["enabled"] = True
        self._save_config()
    
    @property
    def api_base(self):
        return self._config.get("api_base", self.DEFAULT_CONFIG["api_base"])
    
    @api_base.setter
    def api_base(self, value):
        self._config["api_base"] = value
        self._save_config()
    
    @property
    def model(self):
        return self._config.get("model", self.DEFAULT_CONFIG["model"])
    
    @model.setter
    def model(self, value):
        self._config["model"] = value
        self._save_config()
    
    @property
    def max_tokens(self):
        return self._config.get("max_tokens", self.DEFAULT_CONFIG["max_tokens"])
    
    @property
    def temperature(self):
        return self._config.get("temperature", self.DEFAULT_CONFIG["temperature"])
    
    @property
    def max_retries(self):
        return self._config.get("max_retries", self.DEFAULT_CONFIG["max_retries"])
    
    @property
    def timeout(self):
        return self._config.get("timeout", self.DEFAULT_CONFIG["timeout"])
    
    @property
    def enabled(self):
        return self._config.get("enabled", False) and bool(self.api_key)
    
    @enabled.setter
    def enabled(self, value):
        self._config["enabled"] = value
        self._save_config()
    
    # ═══════════════════════════════════════════════════════════════
    # 豆包生图 API 属性
    # ═══════════════════════════════════════════════════════════════
    
    @property
    def doubao_api_key(self):
        return self._config.get("doubao_api_key", "")
    
    @doubao_api_key.setter
    def doubao_api_key(self, value):
        self._config["doubao_api_key"] = value
        if value:
            self._config["doubao_enabled"] = True
        self._save_config()
    
    @property
    def doubao_api_base(self):
        return self._config.get("doubao_api_base", self.DEFAULT_CONFIG["doubao_api_base"])
    
    @doubao_api_base.setter
    def doubao_api_base(self, value):
        self._config["doubao_api_base"] = value
        self._save_config()
    
    @property
    def doubao_model(self):
        return self._config.get("doubao_model", self.DEFAULT_CONFIG["doubao_model"])
    
    @doubao_model.setter
    def doubao_model(self, value):
        self._config["doubao_model"] = value
        self._save_config()
    
    @property
    def doubao_enabled(self):
        return self._config.get("doubao_enabled", False) and bool(self.doubao_api_key)
    
    @doubao_enabled.setter
    def doubao_enabled(self, value):
        self._config["doubao_enabled"] = value
        self._save_config()
    
    # ═══════════════════════════════════════════════════════════════
    # 导演系统配置
    # ═══════════════════════════════════════════════════════════════
    
    @property
    def director_interval_ms(self):
        return self._config.get("director_interval_ms", self.DEFAULT_CONFIG["director_interval_ms"])
    
    @director_interval_ms.setter
    def director_interval_ms(self, value):
        self._config["director_interval_ms"] = value
        self._save_config()
    
    @property
    def director_use_llm(self):
        return self._config.get("director_use_llm", self.DEFAULT_CONFIG["director_use_llm"])
    
    @director_use_llm.setter
    def director_use_llm(self, value):
        self._config["director_use_llm"] = value
        self._save_config()
    
    # ═══════════════════════════════════════════════════════════════
    # 便捷方法
    # ═══════════════════════════════════════════════════════════════
    
    def is_configured(self):
        """检查是否已配置 LLM API Key"""
        return bool(self.api_key)
    
    def is_enabled(self):
        """检查 LLM 功能是否启用"""
        return self.enabled and self.is_configured()
    
    def is_doubao_configured(self):
        """检查是否已配置图像生成 API Key"""
        return bool(self.doubao_api_key)
    
    def is_doubao_enabled(self):
        """检查图像生成功能是否启用"""
        return self.doubao_enabled and self.is_doubao_configured()
    
    def is_llm_fully_configured(self):
        """检查 LLM 是否完全配置（api_key + base_url + model）"""
        return bool(self.api_key) and bool(self.api_base) and bool(self.model)
    
    def is_image_fully_configured(self):
        """检查图像生成是否完全配置（api_key + base_url + model）"""
        return bool(self.doubao_api_key) and bool(self.doubao_api_base) and bool(self.doubao_model)
    
    def is_ai_ready(self):
        """检查 AI 是否准备就绪（LLM和图像生成都已配置）"""
        return self.is_llm_fully_configured() and self.is_image_fully_configured()
    
    def get_ai_status(self):
        """获取AI配置状态详情，用于UI显示"""
        status = {
            "llm": {
                "ready": self.is_llm_fully_configured(),
                "api_key": bool(self.api_key),
                "base_url": bool(self.api_base),
                "model": bool(self.model)
            },
            "image": {
                "ready": self.is_image_fully_configured(),
                "api_key": bool(self.doubao_api_key),
                "base_url": bool(self.doubao_api_base),
                "model": bool(self.doubao_model)
            },
            "ready": self.is_ai_ready()
        }
        return status
    
    def get_status_text(self):
        """获取 DeepSeek 状态文本（用于UI显示）"""
        if not self.api_key:
            return "未配置API Key"
        elif not self.enabled:
            return "已禁用"
        else:
            return "已启用"
    
    def get_doubao_status_text(self):
        """获取豆包状态文本（用于UI显示）"""
        if not self.doubao_api_key:
            return "未配置API Key"
        elif not self.doubao_enabled:
            return "已禁用"
        else:
            return "已启用"
    
    def set_api_key_from_input(self, key_text):
        """
        从用户输入设置 DeepSeek API Key
        
        Args:
            key_text: 用户输入的API Key文本
            
        Returns:
            (success: bool, message: str)
        """
        key_text = key_text.strip()
        
        if not key_text:
            return False, "API Key不能为空"
        
        # 简单验证格式（DeepSeek的Key通常以sk-开头）
        if not key_text.startswith("sk-"):
            return False, "API Key格式不正确（应以sk-开头）"
        
        if len(key_text) < 20:
            return False, "API Key太短"
        
        self.api_key = key_text
        return True, "API Key设置成功！"
    
    def set_doubao_api_key_from_input(self, key_text):
        """
        从用户输入设置豆包 API Key
        
        Args:
            key_text: 用户输入的API Key文本
            
        Returns:
            (success: bool, message: str)
        """
        key_text = key_text.strip()
        
        if not key_text:
            return False, "API Key不能为空"
        
        if len(key_text) < 10:
            return False, "API Key太短"
        
        self.doubao_api_key = key_text
        return True, "豆包 API Key设置成功！"
    
    def update_settings(self, **kwargs):
        """
        批量更新设置
        
        Args:
            **kwargs: 配置项，如 temperature=0.9, max_tokens=800
        """
        for key, value in kwargs.items():
            if key in self._config:
                self._config[key] = value
        self._save_config()
    
    def to_dict(self):
        """导出配置（隐藏敏感信息）"""
        config = self._config.copy()
        # 隐藏API Key的中间部分
        if config.get("api_key"):
            key = config["api_key"]
            if len(key) > 10:
                config["api_key"] = key[:6] + "..." + key[-4:]
        if config.get("doubao_api_key"):
            key = config["doubao_api_key"]
            if len(key) > 10:
                config["doubao_api_key"] = key[:6] + "..." + key[-4:]
        return config