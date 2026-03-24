# src/llm/llm_service.py
"""
LLM服务封装 - 支持 OpenAI SDK 和原生 HTTP 两种调用方式
基于参考项目的C#实现移植
"""

import json
import re
import time
import threading
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from queue import Queue

from src.utils import log_game_event

# 尝试导入 OpenAI SDK
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("[LLMService] 提示: 未安装 openai 库，将使用 requests 方式调用")

# 尝试导入requests库
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("[LLMService] 警告: 未安装 requests 库，LLM功能将不可用")

from .config import LLMConfig

# 默认使用 OpenAI SDK（如果可用）
DEFAULT_USE_OPENAI_SDK = True


@dataclass
class LLMResponse:
    """
    LLM响应结构 - 只包含原始响应，不做业务解析
    
    各业务模块需要自己解析 raw_response 中的 JSON
    """
    raw_response: str = ""                   # 原始响应文本（LLM直接返回的内容）
    success: bool = True                     # 是否成功
    error: str = ""                          # 错误信息
    
    @classmethod
    def from_error(cls, error_msg: str):
        """创建错误响应"""
        return cls(
            raw_response="",
            success=False,
            error=error_msg
        )


class LLMService:
    """
    LLM服务单例
    负责与DeepSeek API通信，处理重试和响应解析
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.config = LLMConfig.get_instance()
        self._request_queue = Queue()
        self._is_processing = False
        
        # 调用方式开关：True=使用OpenAI SDK, False=使用requests
        self._use_openai_sdk = DEFAULT_USE_OPENAI_SDK and HAS_OPENAI
        
        # OpenAI SDK 客户端（延迟初始化）
        self._openai_client: Optional[OpenAI] = None
        
        # 统计信息
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_tokens_used = 0
        
        # 打印当前使用的调用方式
        if self._use_openai_sdk:
            print("[LLMService] 服务初始化完成 [调用方式: OpenAI SDK]")
        else:
            if HAS_OPENAI:
                print("[LLMService] 服务初始化完成 [调用方式: requests (可通过 set_use_openai_sdk(True) 切换)]")
            else:
                print("[LLMService] 服务初始化完成 [调用方式: requests (未安装 openai 库)]")
    
    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        return cls()
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return HAS_REQUESTS and self.config.is_enabled()
    
    # ═══════════════════════════════════════════════════════════════
    # 调用方式切换
    # ═══════════════════════════════════════════════════════════════
    
    def set_use_openai_sdk(self, use_sdk: bool) -> bool:
        """
        设置是否使用 OpenAI SDK 调用
        
        Args:
            use_sdk: True 使用 OpenAI SDK, False 使用 requests
            
        Returns:
            bool: 设置是否成功
        """
        if use_sdk and not HAS_OPENAI:
            print("[LLMService] 错误: 未安装 openai 库，无法切换到 SDK 模式")
            print("[LLMService] 请运行: pip install openai")
            return False
        
        self._use_openai_sdk = use_sdk
        
        # 如果切换到 SDK 模式，重置客户端以便下次使用时重新初始化
        if not use_sdk:
            self._openai_client = None
        
        mode = "OpenAI SDK" if use_sdk else "requests"
        print(f"[LLMService] 已切换到: {mode} 调用方式")
        return True
    
    def get_use_openai_sdk(self) -> bool:
        """获取当前是否使用 OpenAI SDK"""
        return self._use_openai_sdk
    
    def _get_openai_client(self) -> OpenAI:
        """
        获取或创建 OpenAI SDK 客户端（延迟初始化）
        
        如果配置发生变化，会重新创建客户端
        
        Returns:
            OpenAI: OpenAI SDK 客户端实例
        """
        # 检查是否需要重新创建客户端（配置发生变化）
        need_recreate = (
            self._openai_client is None or
            getattr(self, '_cached_api_key', None) != self.config.api_key or
            getattr(self, '_cached_api_base', None) != self.config.api_base
        )
        
        if need_recreate:
            self._openai_client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.api_base,
                timeout=self.config.timeout
            )
            # 缓存当前配置，用于检测变化
            self._cached_api_key = self.config.api_key
            self._cached_api_base = self.config.api_base
            print(f"[LLMService] OpenAI SDK 客户端已创建/更新: {self.config.api_base}")
        
        return self._openai_client
    
    # ═══════════════════════════════════════════════════════════════
    # 同步请求方法
    # ═══════════════════════════════════════════════════════════════
    
    def chat(self, system_prompt: str, user_message: str, 
             conversation_history: List[Dict] = None,
             max_tokens: int = None) -> LLMResponse:
        """
        发送对话请求（同步）
        
        Args:
            system_prompt: 系统提示词（角色设定、世界观等）
            user_message: 用户消息
            conversation_history: 历史对话记录
            max_tokens: 可选的最大token数，覆盖配置默认值
            
        Returns:
            LLMResponse: 解析后的响应
        """
        if not self.is_available():
            print("[LLMService] 服务不可用，跳过请求")
            return LLMResponse.from_error("LLM服务不可用")
        
        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": user_message})
        
        # 确定实际使用的max_tokens
        actual_max_tokens = max_tokens if max_tokens is not None else self.config.max_tokens
        
        # 记录请求日志

        #上面这部分可以做成一个字符串，然后用log_game_event打印，这样就能在游戏日志里看到完整的请求信息了
        request_log = f"[LLMService] ===== 发送LLM请求 =====\n" \
                      f"[LLMService] 模型: {self.config.model}\n" \
                      f"[LLMService] max_tokens: {actual_max_tokens}\n" \
                      f"[LLMService] System Prompt: {system_prompt}\n" \
                      f"[LLMService] User Message: {user_message}\n"

        if conversation_history:
            print(f"[LLMService] 历史消息数: {len(conversation_history)}")
            request_log+=f"[LLMService] 历史消息数: {len(conversation_history)}\n"

        log_game_event(request_log)
        
        # 带重试的请求
        last_error = ""
        for attempt in range(self.config.max_retries):
            try:
                raw_response = self._send_request(messages, actual_max_tokens)
                self.total_requests += 1
                self.successful_requests += 1
                
              
                #log_game_event(f"[LLMService] 收到原始响应 {raw_response}")
                
                # 返回原始响应，让业务层自己解析
                return LLMResponse(raw_response=raw_response, success=True)
                    
            except Exception as e:
                last_error = str(e)
                print(f"[LLMService] 请求异常 (尝试 {attempt + 1}/{self.config.max_retries}): {e}")
                time.sleep(1)  # 重试前等待
        
        self.failed_requests += 1
        print(f"[LLMService] 所有重试失败，最后错误: {last_error}")
        return LLMResponse.from_error(f"请求失败: {last_error}")
    
    def _send_request(self, messages: List[Dict], max_tokens: int = None) -> str:
        """
        发送API请求 - 根据配置选择 OpenAI SDK 或 requests 方式
        
        Args:
            messages: OpenAI格式的消息列表
            max_tokens: 最大token数（可选，默认使用配置值）
            
        Returns:
            str: 原始响应文本
        """
        # 使用传入的max_tokens，如果未指定则使用配置默认值
        actual_max_tokens = max_tokens if max_tokens is not None else self.config.max_tokens
        
        # 根据任务复杂度动态调整超时
        from src.definitions import TIMEOUT_LLM_SIMPLE, TIMEOUT_LLM_COMPLEX
        if max_tokens > 1000:
            request_timeout = max(TIMEOUT_LLM_COMPLEX, self.config.timeout)
        else:
            request_timeout = max(TIMEOUT_LLM_SIMPLE, self.config.timeout)
        
        # 根据开关选择调用方式
        if self._use_openai_sdk:
            return self._send_request_openai_sdk(messages, actual_max_tokens, request_timeout)
        else:
            return self._send_request_requests(messages, actual_max_tokens, request_timeout)
    
    def _send_request_openai_sdk(self, messages: List[Dict], max_tokens: int, timeout: int) -> str:
        """
        使用 OpenAI SDK 发送请求
        
        Args:
            messages: OpenAI格式的消息列表
            max_tokens: 最大token数
            timeout: 超时时间（秒）
            
        Returns:
            str: 原始响应文本
        """
        client = self._get_openai_client()
        
        # 更新客户端超时设置
        client.timeout = timeout
        
        log_game_event(f"[LLMService] 使用 OpenAI SDK 发送请求 (timeout={timeout}s)")

        response = client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=self.config.temperature,
            stream=False
        )

        # 详细的响应调试日志
        debug_info = f"[LLMService] OpenAI SDK 收到响应 (id={response.id}, model={response.model})"
        if response.usage:
            debug_info += f", tokens={response.usage.total_tokens}"
        #log_game_event(debug_info)
        
        # 统计token使用
        if response.usage:
            self.total_tokens_used += response.usage.total_tokens
        
        # 提取回复文本
        if not response.choices:
            raise Exception("API返回空choices")
        
        choice = response.choices[0]
        #log_game_event(f"[LLMService] Choice详情: index={choice.index}, finish_reason={choice.finish_reason}")
        
        # 调试：打印完整的message对象
        message = choice.message
        #log_game_event(f"[LLMService] Message对象: role={message.role}, content_type={type(message.content)}, content={repr(message.content)}")
        
        content = message.content
        
        # 处理 content 为 None 或空字符串的情况
        if content is None:
            finish_reason = choice.finish_reason
            if finish_reason == "content_filter":
                raise Exception("内容被API过滤 (content_filter)")
            elif finish_reason == "length":
                raise Exception("达到最大token限制 (length)")
            else:
                raise Exception(f"API返回空内容 (finish_reason={finish_reason})")
        
        # 处理空字符串（某些模型可能返回空字符串）
        if content.strip() == "":
            raise Exception(f"API返回空字符串 (finish_reason={choice.finish_reason})")
        
        return content
    
    def _send_request_requests(self, messages: List[Dict], max_tokens: int, timeout: int) -> str:
        """
        使用 requests 库发送请求
        
        Args:
            messages: OpenAI格式的消息列表
            max_tokens: 最大token数
            timeout: 超时时间（秒）
            
        Returns:
            str: 原始响应文本
        """
        url = f"{self.config.api_base}/chat/completions"
        apikey = self.config.api_key
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {apikey}"
        }
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": self.config.temperature,
            "stream": False
        }
        log_game_event(f"[LLMService] 使用 requests 发送请求 (timeout={timeout}s)")
        
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=timeout
        )

        log_game_event(f"[LLMService] requests 收到响应 (status_code={response.status_code})")
        
        if response.status_code != 200:
            raise Exception(f"API错误: {response.status_code} - {response.text}")
        
        data = response.json()
        
        # 详细的响应调试日志
        debug_info = f"[LLMService] requests 响应解析成功"
        if "usage" in data:
            debug_info += f", tokens={data['usage'].get('total_tokens', 0)}"
        log_game_event(debug_info)
        
        # 统计token使用
        if "usage" in data:
            self.total_tokens_used += data["usage"].get("total_tokens", 0)
        
        # 提取回复文本
        choices = data.get("choices", [])
        if not choices:
            raise Exception("API返回空choices")
        
        choice = choices[0]
        finish_reason = choice.get("finish_reason", "unknown")
        log_game_event(f"[LLMService] Choice详情: index={choice.get('index', 0)}, finish_reason={finish_reason}")
        
        content = choice.get("message", {}).get("content")
        if content is None:
            raise Exception(f"API返回空内容 (finish_reason={finish_reason})")
        
        return content
    
    def clean_llm_response(self, content: str) -> Dict:
        """
        解析LLM返回的JSON内容
        
        增强健壮性：
        - 处理 ```json ... ``` 代码块
        - 修复尾部逗号问题
        - 处理截断的JSON（尝试补全）
        - 移除非法控制字符
        """
        
        try:
            # 清理内容
            json_str = content.strip()
            
            # 尝试提取JSON块（处理 ```json ... ``` 格式）
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', json_str, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            
            # 如果还是以 ``` 开头，继续清理
            if json_str.startswith('```'):
                json_str = json_str[3:]
            if json_str.endswith('```'):
                json_str = json_str[:-3]
            
            # 移除可能的 json 标记
            if json_str.lower().startswith('json'):
                json_str = json_str[4:].strip()
            
            # 确保以 { 开头
          #  brace_start = json_str.find('{')
          #  if brace_start > 0:
           #     json_str = json_str[brace_start:]
            
            # 确保以 } 结尾（找最后一个 }）
           # brace_end = json_str.rfind('}')
           # if brace_end >= 0 and brace_end < len(json_str) - 1:
           #     json_str = json_str[:brace_end + 1]
            
            # ═══════════════════════════════════════════════════════════════
            # 【健壮性增强】修复常见的LLM JSON格式问题
            # ═══════════════════════════════════════════════════════════════
            
            # 1. 移除非法控制字符（ASCII 0-31，除了换行和制表符）
            json_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', json_str)
            
            # 2. 修复尾部逗号问题（在 ] 或 } 前的逗号）
            json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
            
            # 3. 【新增】修复中文引号问题（LLM经常使用中文引号）
            # 将中文引号 " 和 " 替换为英文引号 "
            json_str = json_str.replace('"', '"').replace('"', '"')
            
            # 4. 修复单引号问题（某些LLM会用单引号）
            # 只处理键名的单引号，避免误改字符串内容
            json_str = re.sub(r"'(\w+)'(\s*:)", r'"\1"\2', json_str)
            
            # 4. 修复裸露的#标签问题（如 #鱼西施 → "鱼西施"）
            # LLM有时会用小红书风格的标签，但JSON不支持
            json_str = re.sub(r',\s*#([^\s,\]]+)', r', "\1"', json_str)
            json_str = re.sub(r'\[\s*#([^\s,\]]+)', r'["\1"', json_str)
            
            # 5. 修复 #"xxx" 写法（#号在引号外面），如 #"汴京实况" → "汴京实况"
            json_str = re.sub(r'#"', '"', json_str)
            
            # 尝试解析
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as first_error:
                # ═══════════════════════════════════════════════════════════════
                # 【进一步修复】尝试修补截断的JSON
                # ═══════════════════════════════════════════════════════════════
                log_game_event(f"[Director] 首次解析失败，尝试修复截断问题: {first_error}", tag="DIRECTOR")
                
                # 统计括号数量
                open_braces = json_str.count('{')
                close_braces = json_str.count('}')
                open_brackets = json_str.count('[')
                close_brackets = json_str.count(']')
                
                # 补全缺失的闭合符号
                repair_str = json_str
                
                # 如果缺少闭合括号，尝试补全
                if close_brackets < open_brackets:
                    repair_str += ']' * (open_brackets - close_brackets)
                if close_braces < open_braces:
                    repair_str += '}' * (open_braces - close_braces)
                
                # 再次清理尾部逗号（补全后可能产生新的问题）
                repair_str = re.sub(r',\s*([}\]])', r'\1', repair_str)
                
                try:
                    result = json.loads(repair_str)
                    log_game_event(f"[Director] JSON修复成功！补全了 {open_braces - close_braces} 个 '}}' 和 {open_brackets - close_brackets} 个 ']'", tag="DIRECTOR")
                    return result
                except json.JSONDecodeError:
                    # 修复失败，记录详情
                    pass
                
                # 所有修复尝试失败
                raise first_error
                
        except json.JSONDecodeError as e:
            log_game_event(f"[Director] JSON解析最终失败: {e}, 原始文本: {content}", tag="DIRECTOR")

            return None
        except Exception as e:
            log_game_event(f"[Director] 解析过程异常: {e}, 原始文本: {content}", tag="DIRECTOR")
            return None   
    
    
      
    
    # ═══════════════════════════════════════════════════════════════
    # 异步请求方法
    # ═══════════════════════════════════════════════════════════════
    
    def chat_async(self, system_prompt: str, user_message: str,
                   callback: Callable[[LLMResponse], None],
                   conversation_history: List[Dict] = None):
        """
        发送对话请求（异步）
        
        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            callback: 完成回调函数
            conversation_history: 历史对话记录
        """
        def _worker():
            response = self.chat(system_prompt, user_message, conversation_history)
            callback(response)
        
        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
    
   
    
    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        return {
            "total_requests": self.total_requests,
            "successful": self.successful_requests,
            "failed": self.failed_requests,
            "success_rate": self.successful_requests / max(1, self.total_requests),
            "tokens_used": self.total_tokens_used,
            "is_available": self.is_available(),
            "use_openai_sdk": self._use_openai_sdk,
            "has_openai_lib": HAS_OPENAI
        }
