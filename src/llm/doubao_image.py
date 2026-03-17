"""
豆包(Volcengine/火山引擎) 图像生成 API 集成
===================================================

支持文生图功能，用于AI导演系统生成事件配图。

使用官方 OpenAI 兼容格式：
https://www.volcengine.com/docs/6791/1131816

模型：doubao-seedream-5-0-260128 (豆包·种子梦文生图)
"""

import asyncio
import aiohttp
import base64
import hashlib
import os
import time
import json
import threading
from typing import Optional, Callable, Dict, Any
from pathlib import Path

from src.definitions import *
from src.utils import log_game_event, resource_path

# 尝试导入PIL用于图像处理
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("[DoubaoImage] 警告: PIL未安装，图像处理功能受限")

# 尝试导入openai库（官方推荐方式）
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("[DoubaoImage] 警告: openai库未安装，将使用aiohttp替代")


class DoubaoImageGenerator:

    # 图片缓存目录 - 使用玩家本地目录（不在assets，避免打包）
    # 开发环境: ./image_cache/
    # 打包后:   EXE同级目录的 image_cache/
    @classmethod
    def _get_cache_dir(cls) -> Path:
        """获取图片缓存目录（玩家本地，不打包）"""
        import sys
        if getattr(sys, 'frozen', False):
            # 打包后：放在EXE同级目录，便于玩家查看和管理
            base_path = Path(sys.executable).parent
        else:
            # 开发环境：放在项目根目录
            base_path = Path(__file__).parent.parent.parent
        return base_path / "image_cache"
    
    # 兼容旧代码的类属性访问
    @property
    def CACHE_DIR(self) -> Path:
        return self._get_cache_dir()
    
    # 官方API基础地址
    DEFAULT_API_BASE = "https://ark.cn-beijing.volces.com/api/v3"
    
    # 官方推荐模型
    DEFAULT_MODEL = "doubao-seedream-5-0-260128"
    
    # 支持的尺寸映射 
    # 根据官方示例代码: size="2K"（大写）
    SIZE_MAP = {
        # 全部统一使用 2K（官方示例格式，大写）
        (512, 512): "2K",
        (768, 1024): "2K",
        (1024, 768): "2K",
        (576, 1024): "2K",
        (1024, 576): "2K",
        (400, 300): "2K",         # 导演系统常用
        (300, 400): "2K",
        (1920, 1080): "2K",
        # 默认回退
        "default": "2K",
    }
    
    def __init__(self):
        self._pending_requests: Dict[str, bool] = {}
        self._lock = threading.Lock()
        self._openai_client: Optional[OpenAI] = None
        
        # 确保缓存目录存在
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    def _get_config(self):
        """获取API配置"""
        from src.llm.config import LLMConfig
        return LLMConfig.get_instance()
    
    def _get_api_key(self) -> str:
        """获取API Key（优先环境变量，其次配置文件）"""
        # 优先从环境变量获取（官方推荐）
        env_key = os.environ.get("ARK_API_KEY")
        if env_key:
            return env_key
        
        # 其次从配置文件获取
        config = self._get_config()
        return config.doubao_api_key
    
    def _get_openai_client(self) -> Optional[OpenAI]:
        """获取或创建OpenAI客户端（官方推荐方式）"""
        if not HAS_OPENAI:
            return None
        
        config = self._get_config()
        api_key = self._get_api_key()
        api_base = config.doubao_api_base or self.DEFAULT_API_BASE
        
        # 检查是否需要重新创建客户端（配置发生变化）
        need_recreate = (
            self._openai_client is None or
            getattr(self, '_cached_api_key', None) != api_key or
            getattr(self, '_cached_api_base', None) != api_base
        )
        
        if need_recreate and api_key:
            self._openai_client = OpenAI(
                base_url=api_base,
                api_key=api_key,
            )
            # 缓存当前配置，用于检测变化
            self._cached_api_key = api_key
            self._cached_api_base = api_base
            print(f"[DoubaoImage] OpenAI客户端已创建/更新: {api_base}")
        
        return self._openai_client
    
    def is_available(self) -> bool:
        """检查豆包API是否可用"""
        return bool(self._get_api_key())
    
    def get_cache_path(self, prompt: str) -> Path:
        """根据prompt获取缓存路径"""
        # 使用prompt的hash作为文件名
        prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()[:16]
        return self.CACHE_DIR / f"doubao_{prompt_hash}.png"
    
    def check_cache(self, prompt: str) -> Optional[str]:
        """检查是否有缓存图片，返回路径或None"""
        cache_path = self.get_cache_path(prompt)
        if cache_path.exists():
            return str(cache_path)
        return None
    
    def _get_size_param(self, width: int, height: int) -> str:
        """将宽高转换为API支持的尺寸参数
        
        根据官方示例代码: size="2K"（大写）
        """
        # 查找匹配的尺寸
        key = (width, height)
        if key in self.SIZE_MAP:
            return self.SIZE_MAP[key]
        
        # 默认返回 2K（官方示例格式）
        return "2K"
    
    def generate_image_async(
        self, 
        prompt: str, 
        callback: Callable[[Optional[Any], Optional[str]], None],
        width: int = 512,
        height: int = 512,
        style: str = "artistic",
        reference_images: Optional[list] = None
    ):
        """
        异步生成图片（不阻塞主线程）
        
        Args:
            prompt: 图像描述（中文效果也很好）
            callback: 完成回调 callback(pygame_surface, image_path)
            width: 图片宽度（会映射到API支持的尺寸）
            height: 图片高度
            style: 风格提示 (anime/realistic/artistic)
            reference_images: 参考图路径列表，用于保持人物一致性
        """
        # 根据配置选择使用哪个服务提供商
        from src.definitions import IMAGE_GEN_PROVIDER
        
        if IMAGE_GEN_PROVIDER == 'DANQINGYUE':
            # 使用丹青约API
            self._generate_image_async_danqingyue(prompt, callback, width, height, style, reference_images)
        else:
            # 默认使用豆包API
            self._generate_image_async_doubao(prompt, callback, width, height, style, reference_images)
    
    def _generate_image_async_doubao(
        self, 
        prompt: str, 
        callback: Callable[[Optional[Any], Optional[str]], None],
        width: int = 512,
        height: int = 512,
        style: str = "artistic",
        reference_images: Optional[list] = None
    ):
        """
        使用豆包API异步生成图片
        """
        # 构建缓存key（包含参考图信息）
        cache_key = prompt
        if reference_images:
            cache_key += "|" + "|".join(reference_images)
        
        # 检查缓存
        cached = self.check_cache(cache_key)
        if cached:
            print(f"[DoubaoImage·异步] 命中缓存: {cached}")
            surface = self._load_image_as_surface(cached)
            print(f"[DoubaoImage·异步] 缓存加载结果 - surface: {type(surface).__name__ if surface else 'None'}")
            callback(surface, cached)
            return
        
        # 检查是否已有相同请求在处理中
        with self._lock:
            if cache_key in self._pending_requests:
                print(f"[DoubaoImage·异步] [!] 请求已在处理中，跳过（不调用回调）")
                return
            self._pending_requests[cache_key] = True
        
        print(f"[DoubaoImage·异步] 启动后台工作线程...")
        if reference_images:
            print(f"[DoubaoImage·异步] 参考图: {reference_images}")
        
        # 启动后台线程
        def worker():
            try:
                result_path = self._generate_image_sync(prompt, width, height, style, reference_images)
                print(f"[DoubaoImage·worker] _generate_image_sync 返回: {result_path}")
                
                if result_path:
                    surface = self._load_image_as_surface(result_path)
                    callback(surface, result_path)
                    print(f"[DoubaoImage·worker] 回调调用完成")
                else:
                    print(f"[DoubaoImage·worker] [!] result_path为空，调用回调(None, None)")
                    callback(None, None)
            except Exception as e:
                print(f"[DoubaoImage·worker] [!] 工作线程异常: {e}")
                import traceback
                traceback.print_exc()
                callback(None, None)
            finally:
                with self._lock:
                    self._pending_requests.pop(cache_key, None)
                print(f"[DoubaoImage·worker] 工作线程结束")
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
    
    def _generate_image_async_danqingyue(
        self, 
        prompt: str, 
        callback: Callable[[Optional[Any], Optional[str]], None],
        width: int = 512,
        height: int = 512,
        style: str = "artistic",
        reference_images: Optional[list] = None
    ):
        """
        使用丹青约API异步生成图片
        """
        # 构建缓存key
        cache_key = f"danqingyue_{prompt}"
        if reference_images:
            cache_key += "|" + "|".join(reference_images)
        
        # 检查缓存
        cached = self.check_cache(cache_key)
        if cached:
            print(f"[Danqingyue·异步] 命中缓存: {cached}")
            surface = self._load_image_as_surface(cached)
            callback(surface, cached)
            return
        
        # 检查是否已有相同请求在处理中
        with self._lock:
            if cache_key in self._pending_requests:
                print(f"[Danqingyue·异步] [!] 请求已在处理中，跳过")
                return
            self._pending_requests[cache_key] = True
        
        print(f"[Danqingyue·异步] 启动后台工作线程...")
        
        # 启动后台线程
        def worker():
            try:
                result_path = self._generate_with_danqingyue(prompt, width, height, style, reference_images)
                print(f"[Danqingyue·worker] 返回: {result_path}")
                
                if result_path:
                    surface = self._load_image_as_surface(result_path)
                    callback(surface, result_path)
                else:
                    callback(None, None)
            except Exception as e:
                print(f"[Danqingyue·worker] [!] 工作线程异常: {e}")
                import traceback
                traceback.print_exc()
                callback(None, None)
            finally:
                with self._lock:
                    self._pending_requests.pop(cache_key, None)
                print(f"[Danqingyue·worker] 工作线程结束")
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
    
    def _generate_with_danqingyue(
        self, 
        prompt: str, 
        width: int, 
        height: int, 
        style: str,
        reference_images: Optional[list] = None
    ) -> Optional[str]:
        """
        使用丹青约API同步生成图片 - 与danqingyue_test.py完全一致
        """
        import requests
        import json
        
        # 获取API配置
        config = self._get_config()
        api_key = config.danqingyue_api_key if hasattr(config, 'danqingyue_api_key') else None
        api_key = "sk-xp97drsAZGjr7RNKvk6CmciZA0mmPyHh"  # 临时代码，实际使用时请从配置获取
        if not api_key:
            print("[Danqingyue] API Key未配置，使用占位图")
            return self._generate_placeholder(prompt, width, height)
        
        # 增强prompt
        enhanced_prompt = self._enhance_prompt(prompt, style)
        
        url = "https://aigc-api.fuxi.netease.com/v3/text/chat"
        
        # 构建请求体（与danqingyue_test.py完全一致）
        payload = {
            "model": "doubao-seedream-5-0-260128",
            "prompt": enhanced_prompt,
            "size": "2K",
            "sequential_image_generation": "disabled",
            "stream": False,
            "response_format": "b64_json",
            "seed": -1,
            "watermark": True
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            print(f"[Danqingyue] 开始请求...")
            
            resp = requests.post(url, headers=headers, json=payload)
            
            print(f"[Danqingyue] 请求结束，状态码: {resp.status_code}")
            
            if resp.status_code == 200:
                result = json.loads(resp.text)
                if 'data' in result and len(result['data']) > 0:
                    output_base64_data = result['data'][0]['b64_json']
                    image_bytes = base64.b64decode(output_base64_data)
                    
                    # 保存到缓存
                    cache_path = self.get_cache_path(f"danqingyue_{prompt}")
                    with open(cache_path, 'wb') as f:
                        f.write(image_bytes)
                    
                    print(f"[Danqingyue] 图片已保存: {cache_path}")
                    return str(cache_path)
                else:
                    print(f"[Danqingyue] 响应中没有数据: {result}")
                    return self._generate_placeholder(prompt, width, height)
            else:
                print(f"[Danqingyue] 请求失败: {resp.status_code}, {resp.text[:200]}")
                return self._generate_placeholder(prompt, width, height)
                
        except Exception as e:
            print(f"[Danqingyue] 请求异常: {e}")
            import traceback
            traceback.print_exc()
            return self._generate_placeholder(prompt, width, height)
    
    def _generate_image_sync(
        self, 
        prompt: str, 
        width: int, 
        height: int, 
        style: str,
        reference_images: Optional[list] = None
    ) -> Optional[str]:
        """
        同步生成图片（在后台线程中调用）
        
        优先使用OpenAI客户端（官方推荐），否则回退到aiohttp
        
        Args:
            prompt: 图像描述
            width: 图片宽度
            height: 图片高度
            style: 风格
            reference_images: 参考图路径列表
        """
        api_key = self._get_api_key()
        
        if not api_key:
            print("[DoubaoImage] 豆包API Key未配置，使用占位图")
            return self._generate_placeholder(prompt, width, height)
        
        # 增强prompt
        enhanced_prompt = self._enhance_prompt(prompt, style)
        
        # 获取尺寸参数
        size_param = self._get_size_param(width, height)
        
        # 处理参考图：转换为base64
        ref_images_base64 = []
        if reference_images:
            for img_path in reference_images:
                try:
                    base64_img = self._image_to_base64(img_path)
                    if base64_img:
                        ref_images_base64.append(base64_img)
                        print(f"[DoubaoImage] 已加载参考图: {os.path.basename(img_path)}")
                except Exception as e:
                    print(f"[DoubaoImage] 加载参考图失败 {img_path}: {e}")
        
        # 优先使用OpenAI客户端（官方推荐方式）
        if HAS_OPENAI:
            result = self._generate_with_openai(enhanced_prompt, size_param, ref_images_base64)
            if result:
                return result
        
        # 回退到aiohttp
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self._generate_with_aiohttp(enhanced_prompt, size_param, width, height, ref_images_base64)
            )
        finally:
            loop.close()
    
    def _generate_with_openai(
        self, 
        prompt: str, 
        size: str, 
        reference_images: Optional[list] = None,
        max_retries: int = 3
    ) -> Optional[str]:
        """使用OpenAI客户端生成图片（官方推荐方式）
        
        Args:
            prompt: 图像描述
            size: 尺寸参数
            reference_images: 参考图base64列表
            max_retries: 最大重试次数（用于处理敏感内容检测等随机错误）
        """
        client = self._get_openai_client()
        if not client:
            return None
        
        config = self._get_config()
        model = config.doubao_model or self.DEFAULT_MODEL
        
        last_error = None

        #调试打印
        doubao_log = f"[DoubaoImage] 调用OpenAI SDK - 模型: {model}, 尺寸: {size}, client信息：{client.base_url}, {client.api_key}"
        log_game_event(doubao_log)



        for attempt in range(max_retries):
            try:
                # ===== 记录请求日志 =====
                log_game_event(f"[DoubaoImage] ===== 发送图像生成请求 (尝试 {attempt + 1}/{max_retries}) =====")
                log_game_event(f"[DoubaoImage] Prompt: {prompt}")                
                
                # 构建extra_body
                extra_body = {
                    "watermark": True,  # 官方示例使用True
                }
                
                # 添加参考图（如果提供）
                if reference_images and len(reference_images) > 0:
                    extra_body["image"] = reference_images
                    log_game_event(f"[DoubaoImage] 已添加 {len(reference_images)} 张参考图")
                
                # 调用API（严格按照官方示例格式）
                response = client.images.generate(
                    model=model,
                    prompt=prompt,
                    size=size,
                    response_format="url",
                    extra_body=extra_body,
                )
                
                # ===== 记录响应日志 =====
                log_game_event(f"[DoubaoImage] ===== 收到图像生成响应 =====")
                
                # 获取图片URL
                if response.data and len(response.data) > 0:
                    image_url = response.data[0].url
                    log_game_event(f"[DoubaoImage] 图片URL: {image_url}")
                    
                    # 下载图片并缓存
                    return self._download_and_cache(image_url, prompt)
                else:
                    log_game_event(f"[DoubaoImage] API响应为空")
                    print(f"{'='*60}\n")
                    last_error = "API响应为空"
                    continue
                    
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                log_game_event(f"\n{'='*60}")
                log_game_event(f"[DoubaoImage] ===== 图像生成失败 (尝试 {attempt + 1}/{max_retries}) =====")
                log_game_event(f"[DoubaoImage] 错误类型: {type(e).__name__}")
                log_game_event(f"[DoubaoImage] 错误内容: {e}")
                
                # 判断是否为可重试的错误
                is_retryable = False
                
                # OutputImageSensitiveContentDetected - 生成的图像被检测为敏感，可重试
                if 'sensitive' in error_str or 'outputimagesensitive' in error_str:
                    log_game_event(f"[DoubaoImage] 生成的图像被检测为敏感内容，将重试...")
                    is_retryable = True
                elif 'rate limit' in error_str or '429' in error_str:
                    log_game_event(f"[DoubaoImage] 请求过频，等待后重试...")
                    is_retryable = True
                    time.sleep(2)  # 等待2秒后重试
                elif 'timeout' in error_str:
                    log_game_event(f"[DoubaoImage] 请求超时，将重试...")
                    is_retryable = True
                elif 'bad request' in error_str or '400' in error_str:
                    # 400错误可能是参数问题，不重试
                    log_game_event(f"[DoubaoImage] 检测到400错误（参数问题），不重试")
                    is_retryable = False
                elif 'unauthorized' in error_str or '401' in error_str:
                    log_game_event(f"[DoubaoImage] 检测到401错误（API Key无效），不重试")
                    is_retryable = False
                else:
                    # 其他未知错误，尝试重试
                    log_game_event(f"[DoubaoImage] 未知错误，将重试...")
                    is_retryable = True
                
                
                if not is_retryable:
                    break
                    
                # 如果不是最后一次尝试，等待一下再重试
                if attempt < max_retries - 1:
                    time.sleep(1)
        
        # 所有重试都失败了
        log_game_event(f"[DoubaoImage] 所有 {max_retries} 次尝试都失败，使用占位图")
        log_game_event(f"[DoubaoImage] 最后错误: {last_error}")
        
        # 返回占位图而非None，确保UI有图可显示
        return self._generate_placeholder(prompt, 400, 300)
    
    async def _generate_with_aiohttp(
        self, 
        prompt: str, 
        size: str,
        width: int,
        height: int,
        reference_images: Optional[list] = None
    ) -> Optional[str]:
        """使用aiohttp调用API（备用方式）"""
        try:
            api_key = self._get_api_key()
            config = self._get_config()
            api_base = config.doubao_api_base or self.DEFAULT_API_BASE
            model = config.doubao_model or self.DEFAULT_MODEL
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "prompt": prompt,
                "size": size,
                "response_format": "url",
            }
            
            # 添加参考图（如果提供）
            if reference_images and len(reference_images) > 0:
                payload["image"] = reference_images
                log_game_event(f"[DoubaoImage] aiohttp方式添加 {len(reference_images)} 张参考图")
            
            url = f"{api_base}/images/generations"
            print(f"[DoubaoImage] 调用API (aiohttp): {url}")
            
            # 使用definitions中的超时配置
            from src.definitions import TIMEOUT_IMAGE_GEN
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=TIMEOUT_IMAGE_GEN)
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"[DoubaoImage] API错误 ({response.status}): {error_text[:300]}")
                        return self._generate_placeholder(prompt, width, height)
                    
                    result = await response.json()
                    
                    # 解析响应
                    if "data" in result and len(result["data"]) > 0:
                        item = result["data"][0]
                        
                        if "url" in item:
                            return self._download_and_cache(item["url"], prompt)
                        elif "b64_json" in item:
                            image_data = base64.b64decode(item["b64_json"])
                            return self._save_and_cache(image_data, prompt)
                    
                    print(f"[DoubaoImage] 无法解析响应: {list(result.keys())}")
                    return self._generate_placeholder(prompt, width, height)
                    
        except Exception as e:
            print(f"[DoubaoImage] aiohttp调用失败: {e}")
            return self._generate_placeholder(prompt, width, height)
    
    def _download_and_cache(self, url: str, prompt: str) -> Optional[str]:
        """下载图片并缓存到本地"""
        import urllib.request
        
        try:
            cache_path = self.get_cache_path(prompt)
            
            # 下载图片
            print(f"[DoubaoImage] 正在下载图片...")
            urllib.request.urlretrieve(url, cache_path)
            
            print(f"[DoubaoImage] 图片已保存: {cache_path}")
            return str(cache_path)
            
        except Exception as e:
            print(f"[DoubaoImage] 下载图片失败: {e}")
            return None
    
    def _save_and_cache(self, image_data: bytes, prompt: str) -> str:
        """保存图片数据到缓存"""
        cache_path = self.get_cache_path(prompt)
        
        with open(cache_path, 'wb') as f:
            f.write(image_data)
        
        print(f"[DoubaoImage] 图片已保存: {cache_path}")
        return str(cache_path)
    
    def _enhance_prompt(self, prompt: str, style: str) -> str:
        """增强prompt以获得更好的宋代中国风格"""
        style_additions = {
            "anime": "动漫风格，色彩鲜艳，中国水墨画影响",
            "realistic": "写实风格，电影光效，细节丰富",
            "artistic": "数字艺术，概念艺术，氛围感强，戏剧性构图"
        }
        
        base_style = style_additions.get(style, style_additions["artistic"])
        
        # 如果prompt已经是中文，保持原样；如果是英文，添加中国风格关键词
        if any('\u4e00' <= c <= '\u9fff' for c in prompt):
            # 中文prompt，添加风格词
            return f"{prompt}，{base_style}，宋代中国，古代建筑，汉服，高质量"
        else:
            # 英文prompt，添加英文风格词
            song_dynasty_keywords = (
                "Song dynasty China, traditional Chinese architecture, "
                "ancient Chinese clothing hanfu, historical setting"
            )
            return f"{prompt}, {song_dynasty_keywords}, {base_style}, high quality, detailed"
    
    def _generate_placeholder(self, prompt: str, width: int, height: int) -> Optional[str]:
        """生成占位图片（当API不可用时）"""
        cache_path = self.get_cache_path(f"placeholder_{prompt}")
        
        if cache_path.exists():
            return str(cache_path)
        
        if HAS_PIL:
            # 使用PIL生成渐变占位图
            img = Image.new('RGB', (width, height))
            pixels = img.load()
            
            # 创建宋代风格的渐变色（暖色调）
            for y in range(height):
                for x in range(width):
                    # 从暖棕色到暖黄色的渐变
                    r = int(180 + (x / width) * 50)
                    g = int(140 + (y / height) * 60)
                    b = int(100 + ((x + y) / (width + height)) * 40)
                    pixels[x, y] = (min(r, 255), min(g, 255), min(b, 255))
            
            img.save(cache_path, 'PNG')
            print(f"[DoubaoImage] 已生成占位图: {cache_path}")
            return str(cache_path)
        else:
            # 没有PIL，返回None
            return None
    
    def _load_image_as_surface(self, image_path: str) -> Optional[Any]:
        """将图片加载为Pygame Surface"""
        try:
            import pygame
            return pygame.image.load(image_path)
        except Exception as e:
            print(f"[DoubaoImage] 加载图片失败: {e}")
            return None
    
    def _image_to_base64(self, image_path: str) -> Optional[str]:
        """将本地图片转换为base64字符串（data URI格式）
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            base64编码的data URI字符串，如 "data:image/png;base64,xxxxx"
        """
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            # 获取文件扩展名
            ext = os.path.splitext(image_path)[1].lower()
            mime_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
            
            # 转换为base64并添加data URI前缀
            base64_str = base64.b64encode(image_data).decode("utf-8")
            return f"data:{mime_type};base64,{base64_str}"
        except Exception as e:
            print(f"[DoubaoImage] 图片转base64失败 {image_path}: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════
# 全局实例
# ═══════════════════════════════════════════════════════════════════════════

_image_generator: Optional[DoubaoImageGenerator] = None

def get_image_generator() -> DoubaoImageGenerator:
    """获取全局图像生成器实例"""
    global _image_generator
    if _image_generator is None:
        _image_generator = DoubaoImageGenerator()
    return _image_generator