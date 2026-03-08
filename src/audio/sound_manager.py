"""
音效管理器 - AI事件通知音效
===================================================

提供简单的音效播放功能，用于：
- AI事件触发时的通知音
- 选择/确认音效
- 氛围音效

注意：由于Pygame的mixer初始化可能与主游戏冲突，
这里使用延迟加载模式。
"""

import os
from pathlib import Path
from typing import Optional, Dict
import math

from src.utils import resource_path

# Pygame将在需要时导入
pygame = None


def _ensure_pygame():
    """确保pygame已导入并初始化mixer"""
    global pygame
    if pygame is None:
        import pygame as pg
        pygame = pg
        # mixer可能已经在main中初始化
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
                print("[SoundManager] Mixer初始化成功")
            except Exception as e:
                print(f"[SoundManager] Mixer初始化失败: {e}")


class SoundManager:
    """
    音效管理器
    
    使用方法:
        sm = get_sound_manager()
        sm.play_notification()  # 播放通知音
    """
    
    # 音效文件目录（使用 resource_path 确保打包后也能正常工作）
    SOUND_DIR = Path(resource_path("assets/sounds"))
    
    def __init__(self):
        self._sounds: Dict[str, any] = {}
        self._enabled = True
        self._volume = 0.7
        self._initialized = False
        
        # 生成的音效缓存
        self._generated_sounds: Dict[str, any] = {}
    
    def _lazy_init(self):
        """延迟初始化"""
        if self._initialized:
            return
        
        _ensure_pygame()
        self._initialized = True
        
        # 确保音效目录存在
        self.SOUND_DIR.mkdir(parents=True, exist_ok=True)
        
        # 尝试加载预置音效
        self._load_sounds()
    
    def _load_sounds(self):
        """加载所有预置音效"""
        sound_files = {
            "notification": "notification.wav",
            "confirm": "confirm.wav",
            "cancel": "cancel.wav",
            "dramatic": "dramatic.wav",
            "whisper": "whisper.wav",
        }
        
        for name, filename in sound_files.items():
            path = self.SOUND_DIR / filename
            if path.exists():
                try:
                    self._sounds[name] = pygame.mixer.Sound(str(path))
                    self._sounds[name].set_volume(self._volume)
                    print(f"[SoundManager] 已加载音效: {name}")
                except Exception as e:
                    print(f"[SoundManager] 加载失败 {name}: {e}")
    
    # ═══════════════════════════════════════════════════════════════
    # 程序生成的简单音效（无需外部文件）
    # ═══════════════════════════════════════════════════════════════
    
    def _generate_beep(self, frequency: int = 440, duration_ms: int = 200, 
                       volume: float = 0.5, fade_out: bool = True) -> any:
        """
        生成简单的正弦波蜂鸣音
        
        Args:
            frequency: 频率 (Hz)
            duration_ms: 持续时间 (毫秒)
            volume: 音量 (0.0-1.0)
            fade_out: 是否淡出
        """
        _ensure_pygame()
        
        cache_key = f"beep_{frequency}_{duration_ms}_{volume}_{fade_out}"
        if cache_key in self._generated_sounds:
            return self._generated_sounds[cache_key]
        
        try:
            import array
            
            sample_rate = 44100
            n_samples = int(sample_rate * duration_ms / 1000)
            
            # 生成正弦波
            samples = []
            for i in range(n_samples):
                t = i / sample_rate
                
                # 基础正弦波
                value = math.sin(2 * math.pi * frequency * t)
                
                # 淡出效果
                if fade_out:
                    fade_ratio = 1.0 - (i / n_samples)
                    value *= fade_ratio
                
                # 转换为16位整数
                sample = int(value * 32767 * volume)
                samples.append(sample)
            
            # 创建Sound对象
            # 立体声，所以每个样本复制两次
            stereo_samples = []
            for s in samples:
                stereo_samples.append(s)  # 左声道
                stereo_samples.append(s)  # 右声道
            
            sound_array = array.array('h', stereo_samples)
            sound = pygame.mixer.Sound(buffer=sound_array.tobytes())
            
            self._generated_sounds[cache_key] = sound
            return sound
            
        except Exception as e:
            print(f"[SoundManager] 生成音效失败: {e}")
            return None
    
    def _generate_notification_chord(self) -> any:
        """生成通知和弦音（更悦耳的多音组合）"""
        cache_key = "notification_chord"
        if cache_key in self._generated_sounds:
            return self._generated_sounds[cache_key]
        
        _ensure_pygame()
        
        try:
            import array
            
            sample_rate = 44100
            duration_ms = 400
            n_samples = int(sample_rate * duration_ms / 1000)
            
            # 使用和弦（C-E-G）
            frequencies = [523.25, 659.25, 783.99]  # C5, E5, G5
            
            samples = []
            for i in range(n_samples):
                t = i / sample_rate
                value = 0
                
                for freq in frequencies:
                    value += math.sin(2 * math.pi * freq * t)
                
                # 平均并应用包络
                value /= len(frequencies)
                
                # ADSR包络（简化版）
                progress = i / n_samples
                if progress < 0.1:  # Attack
                    envelope = progress / 0.1
                elif progress < 0.3:  # Decay
                    envelope = 1.0 - (progress - 0.1) * 0.3
                else:  # Release
                    envelope = 0.7 * (1.0 - (progress - 0.3) / 0.7)
                
                value *= envelope * 0.4  # 总音量
                
                sample = int(value * 32767)
                samples.append(sample)
            
            # 立体声
            stereo = []
            for s in samples:
                stereo.append(s)
                stereo.append(s)
            
            sound_array = array.array('h', stereo)
            sound = pygame.mixer.Sound(buffer=sound_array.tobytes())
            
            self._generated_sounds[cache_key] = sound
            return sound
            
        except Exception as e:
            print(f"[SoundManager] 生成和弦失败: {e}")
            return None
    
    def _generate_dramatic_sound(self) -> any:
        """生成戏剧性音效（低音+高音组合）"""
        cache_key = "dramatic"
        if cache_key in self._generated_sounds:
            return self._generated_sounds[cache_key]
        
        _ensure_pygame()
        
        try:
            import array
            
            sample_rate = 44100
            duration_ms = 800
            n_samples = int(sample_rate * duration_ms / 1000)
            
            samples = []
            for i in range(n_samples):
                t = i / sample_rate
                progress = i / n_samples
                value = 0
                
                # 低音（渐强）
                low_freq = 110 + progress * 50  # A2，渐升
                value += math.sin(2 * math.pi * low_freq * t) * 0.5 * min(progress * 2, 1)
                
                # 高音琶音（快速序列）
                if progress > 0.2:
                    high_progress = (progress - 0.2) / 0.8
                    high_freq = 880 * (1 + high_progress * 0.5)  # A5，渐升
                    value += math.sin(2 * math.pi * high_freq * t) * 0.3 * (1 - high_progress)
                
                # 淡出
                if progress > 0.7:
                    fade = 1.0 - (progress - 0.7) / 0.3
                    value *= fade
                
                sample = int(value * 32767 * 0.5)
                samples.append(sample)
            
            stereo = []
            for s in samples:
                stereo.append(s)
                stereo.append(s)
            
            sound_array = array.array('h', stereo)
            sound = pygame.mixer.Sound(buffer=sound_array.tobytes())
            
            self._generated_sounds[cache_key] = sound
            return sound
            
        except Exception as e:
            print(f"[SoundManager] 生成戏剧音效失败: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════════
    # 公共播放接口
    # ═══════════════════════════════════════════════════════════════
    
    def play_notification(self):
        """播放通知音（AI事件触发时）"""
        if not self._enabled:
            return
        
        self._lazy_init()
        
        # 优先使用预置音效
        if "notification" in self._sounds:
            self._sounds["notification"].play()
            return
        
        # 否则使用生成的和弦
        sound = self._generate_notification_chord()
        if sound:
            sound.play()
    
    def play_dramatic(self):
        """播放戏剧性音效（重大事件）"""
        if not self._enabled:
            return
        
        self._lazy_init()
        
        if "dramatic" in self._sounds:
            self._sounds["dramatic"].play()
            return
        
        sound = self._generate_dramatic_sound()
        if sound:
            sound.play()
    
    def play_confirm(self):
        """播放确认音（选择后）"""
        if not self._enabled:
            return
        
        self._lazy_init()
        
        if "confirm" in self._sounds:
            self._sounds["confirm"].play()
            return
        
        # 简单的高音蜂鸣
        sound = self._generate_beep(880, 100, 0.3, True)
        if sound:
            sound.play()
    
    def play_cancel(self):
        """播放取消音"""
        if not self._enabled:
            return
        
        self._lazy_init()
        
        if "cancel" in self._sounds:
            self._sounds["cancel"].play()
            return
        
        # 低音蜂鸣
        sound = self._generate_beep(330, 150, 0.3, True)
        if sound:
            sound.play()
    
    def play_beep(self, frequency: int = 440, duration_ms: int = 100):
        """播放自定义蜂鸣音"""
        if not self._enabled:
            return
        
        self._lazy_init()
        
        sound = self._generate_beep(frequency, duration_ms, 0.3, True)
        if sound:
            sound.play()
    
    # ═══════════════════════════════════════════════════════════════
    # 设置
    # ═══════════════════════════════════════════════════════════════
    
    def set_enabled(self, enabled: bool):
        """启用/禁用音效"""
        self._enabled = enabled
    
    def set_volume(self, volume: float):
        """设置音量 (0.0-1.0)"""
        self._volume = max(0.0, min(1.0, volume))
        
        # 更新已加载音效的音量
        for sound in self._sounds.values():
            sound.set_volume(self._volume)
    
    def is_enabled(self) -> bool:
        return self._enabled
    
    def get_volume(self) -> float:
        return self._volume


# ═══════════════════════════════════════════════════════════════════════════
# 全局实例
# ═══════════════════════════════════════════════════════════════════════════

_sound_manager: Optional[SoundManager] = None

def get_sound_manager() -> SoundManager:
    """获取全局音效管理器实例"""
    global _sound_manager
    if _sound_manager is None:
        _sound_manager = SoundManager()
    return _sound_manager
