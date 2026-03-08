"""
用户配置管理模块
支持从用户目录加载 AI 配置，覆盖默认配置
"""

import os
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any


class UserConfig:
    """
    用户配置管理器
    
    配置加载优先级（从高到低）：
    1. 用户配置文件（系统配置目录）
    2. 游戏目录下的 user_config/ai_config.json（便携模式）
    3. 硬编码默认配置
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._config: Dict[str, Any] = {}
        self._config_path: Optional[Path] = None
        self._load_config()
        self._initialized = True
    
    @staticmethod
    def get_config_dir() -> Path:
        """
        获取用户配置目录
        
        Returns:
            Path: 配置目录路径
        """
        if sys.platform == "win32":
            # Windows: %APPDATA%/堆叠江湖
            base_dir = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
        elif sys.platform == "darwin":
            # macOS: ~/Library/Application Support/堆叠江湖
            base_dir = Path.home() / "Library/Application Support"
        else:
            # Linux: ~/.config/堆叠江湖
            base_dir = Path.home() / ".config"
        
        config_dir = base_dir / "堆叠江湖"
        return config_dir
    
    @staticmethod
    def get_default_config_path() -> Path:
        """获取默认配置文件路径（打包后）"""
        if getattr(sys, 'frozen', False):
            # 打包后的可执行文件
            if sys.platform == "darwin":
                # macOS .app 包结构
                base_path = Path(sys.executable).parent.parent / "Resources"
            else:
                base_path = Path(sys.executable).parent
        else:
            # 开发环境
            base_path = Path(__file__).parent.parent
        
        return base_path / "data" / "llm_config.json"
    
    def _find_user_config(self) -> Optional[Path]:
        """
        查找用户配置文件（优先本地配置，支持便携模式）
        
        Returns:
            Optional[Path]: 配置文件路径，如果未找到则返回 None
        """
        # 1. 游戏目录下的 user_config（优先，支持便携模式）
        if getattr(sys, 'frozen', False):
            # 打包后的可执行文件
            if sys.platform == "darwin":
                # macOS .app 包结构
                game_config = Path(sys.executable).parent.parent / "Resources" / "user_config" / "ai_config.json"
            else:
                # Windows/Linux
                game_config = Path(sys.executable).parent / "user_config" / "ai_config.json"
        else:
            # 开发环境
            game_config = Path(__file__).parent.parent / "user_config" / "ai_config.json"
        
        if game_config.exists():
            return game_config
        
        # 2. 系统配置目录（后备）
        config_dir = self.get_config_dir()
        system_config = config_dir / "ai_config.json"
        if system_config.exists():
            return system_config
        
        return None
    
    def get_save_path(self) -> Path:
        """
        获取配置保存路径（优先本地，便于携模式）
        
        Returns:
            Path: 配置文件保存路径
        """
        # 优先保存到游戏目录（便携模式）
        if getattr(sys, 'frozen', False):
            if sys.platform == "darwin":
                save_dir = Path(sys.executable).parent.parent / "Resources" / "user_config"
            else:
                save_dir = Path(sys.executable).parent / "user_config"
        else:
            save_dir = Path(__file__).parent.parent / "user_config"
        
        save_dir.mkdir(parents=True, exist_ok=True)
        return save_dir / "ai_config.json"
    
    def _load_config(self):
        """加载配置"""
        # 首先加载默认配置
        default_config = self._load_default_config()
        
        # 查找并加载用户配置
        user_config_path = self._find_user_config()
        
        if user_config_path:
            try:
                with open(user_config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                
                # 合并配置（用户配置覆盖默认配置）
                self._config = self._merge_config(default_config, user_config)
                self._config_path = user_config_path
                print(f"[UserConfig] 已加载用户配置: {user_config_path}")
            except Exception as e:
                print(f"[UserConfig] 加载用户配置失败: {e}，使用默认配置")
                self._config = default_config
        else:
            self._config = default_config
            print("[UserConfig] 未找到用户配置，使用默认配置")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置（硬编码，不再依赖外部文件）"""
        return self._get_hardcoded_default()
    
    def _get_hardcoded_default(self) -> Dict[str, Any]:
        """获取硬编码的默认配置"""
        return {
            "api_key": "",
            "api_base": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "enabled": False,
            "max_tokens": 500,
            "temperature": 0.85,
            "max_retries": 3,
            "timeout": 30,
            "doubao_api_key": "",
            "doubao_api_base": "https://ark.cn-beijing.volces.com/api/v3",
            "doubao_model": "doubao-seedream-5-0-260128",
            "doubao_enabled": False,
            "director_interval_ms": 60000,
            "director_use_llm": False,
        }
    
    def _merge_config(self, default: Dict, user: Dict) -> Dict:
        """
        递归合并配置
        
        Args:
            default: 默认配置
            user: 用户配置
            
        Returns:
            Dict: 合并后的配置
        """
        result = default.copy()
        
        for key, value in user.items():
            if key.startswith('_'):  # 跳过注释字段
                continue
                
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点号分隔（如 "llm.api_key"）
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_llm_config(self) -> Dict[str, Any]:
        """获取 LLM 配置"""
        return {
            "api_key": self.get("llm.api_key") or self.get("api_key", ""),
            "api_base": self.get("llm.api_base") or self.get("api_base", "https://api.deepseek.com"),
            "model": self.get("llm.model") or self.get("model", "deepseek-chat"),
            "enabled": self.get("llm.enabled", self.get("enabled", False)),
            "max_tokens": self.get("llm.max_tokens", self.get("max_tokens", 500)),
            "temperature": self.get("llm.temperature", self.get("temperature", 0.85)),
            "max_retries": self.get("llm.max_retries", self.get("max_retries", 3)),
            "timeout": self.get("llm.timeout", self.get("timeout", 30)),
        }
    
    def get_image_config(self) -> Dict[str, Any]:
        """获取图像生成配置"""
        return {
            "api_key": self.get("image.api_key") or self.get("doubao_api_key", ""),
            "api_base": self.get("image.api_base") or self.get("doubao_api_base", "https://ark.cn-beijing.volces.com/api/v3"),
            "model": self.get("image.model") or self.get("doubao_model", "doubao-seedream-5-0-260128"),
            "enabled": self.get("image.enabled", self.get("doubao_enabled", False)),
        }
    
    def get_director_config(self) -> Dict[str, Any]:
        """获取导演系统配置"""
        return {
            "enabled": self.get("director.enabled", True),
            "use_llm": self.get("director.use_llm", self.get("director_use_llm", False)),
            "interval_ms": self.get("director.interval_ms", self.get("director_interval_ms", 60000)),
            "min_interval_ms": self.get("director.min_interval_ms", 30000),
            "max_interval_ms": self.get("director.max_interval_ms", 120000),
        }
    
    def is_ai_enabled(self) -> bool:
        """检查 AI 是否启用"""
        llm = self.get_llm_config()
        return llm.get("enabled", False) and bool(llm.get("api_key"))
    
    def is_image_enabled(self) -> bool:
        """检查图像生成是否启用"""
        img = self.get_image_config()
        return img.get("enabled", False) and bool(img.get("api_key"))
    
    def save_config(self, config_data: Dict[str, Any]) -> bool:
        """
        保存配置到文件（优先保存到本地，支持便携模式）
        
        Args:
            config_data: 要保存的配置数据
            
        Returns:
            bool: 是否保存成功
        """
        try:
            save_path = self.get_save_path()
            
            # 读取现有配置（如果存在）
            existing_config = {}
            if save_path.exists():
                try:
                    with open(save_path, 'r', encoding='utf-8') as f:
                        existing_config = json.load(f)
                except:
                    pass
            
            # 合并新配置
            merged_config = self._merge_config(existing_config, config_data)
            
            # 保存到文件
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(merged_config, f, indent=2, ensure_ascii=False)
            
            # 更新内存中的配置
            self._config = merged_config
            self._config_path = save_path
            
            print(f"[UserConfig] 配置已保存到: {save_path}")
            return True
            
        except Exception as e:
            print(f"[UserConfig] 保存配置失败: {e}")
            return False
    
    @classmethod
    def create_template(cls, target_path: Optional[Path] = None) -> Path:
        """
        创建配置模板文件
        
        Args:
            target_path: 目标路径，默认为系统配置目录
            
        Returns:
            Path: 创建的文件路径
        """
        if target_path is None:
            config_dir = cls.get_config_dir()
            config_dir.mkdir(parents=True, exist_ok=True)
            target_path = config_dir / "ai_config.json"
        
        template = {
            "_comment": "堆叠江湖 - AI 配置文件",
            "_warning": "请勿分享包含 API Key 的配置文件！",
            "llm": {
                "enabled": False,
                "provider": "deepseek",
                "api_key": "",
                "api_base": "https://api.deepseek.com",
                "model": "deepseek-chat",
                "max_tokens": 500,
                "temperature": 0.85,
                "max_retries": 3,
                "timeout": 30
            },
            "image": {
                "enabled": False,
                "provider": "doubao",
                "api_key": "",
                "api_base": "https://ark.cn-beijing.volces.com/api/v3",
                "model": "doubao-seedream-5-0-260128"
            },
            "director": {
                "enabled": True,
                "use_llm": False,
                "interval_ms": 60000
            }
        }
        
        with open(target_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2, ensure_ascii=False)
        
        return target_path


# 全局配置实例
_user_config: Optional[UserConfig] = None


def get_user_config() -> UserConfig:
    """获取全局配置实例"""
    global _user_config
    if _user_config is None:
        _user_config = UserConfig()
    return _user_config


def reload_config():
    """重新加载配置"""
    global _user_config
    _user_config = UserConfig()
    return _user_config
