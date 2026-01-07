"""TTS 音频缓存模块

提供 TTS 返回音频的缓存功能，将完整的 TTS 对话音频保存为 WAV 文件。
"""

import struct
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import numpy as np

from simple_xiaozhi.constants.constants import AudioConfig
from simple_xiaozhi.utils.config_manager import ConfigManager
from simple_xiaozhi.utils.logging_config import get_logger
from simple_xiaozhi.utils.resource_finder import resource_finder

logger = get_logger(__name__)


class TTSCache:
    """TTS 音频缓存器

    功能:
    - 在应用启动时创建以日期-时间命名的会话目录
    - 在每次 TTS 对话期间收集所有音频片段
    - TTS 结束时将完整音频保存为单个 WAV 文件

    使用示例:
        cache = TTSCache()
        cache.start_session()  # 应用启动时调用

        # TTS 开始时
        cache.start_tts()

        # 每次收到 TTS 音频片段时
        cache.append_audio(pcm_data)

        # TTS 结束时
        cache.end_tts()  # 自动保存完整音频

        cache.end_session()  # 应用关闭时调用
    """

    def __init__(self):
        """初始化 TTS 缓存器."""
        self.config_manager = ConfigManager.get_instance()
        self._enabled = False
        self._cache_dir: Optional[Path] = None
        self._session_dir: Optional[Path] = None
        self._tts_counter = 0  # TTS 对话计数器
        self._lock = threading.Lock()

        # 当前 TTS 对话的音频缓冲区
        self._audio_buffer: List[np.ndarray] = []
        self._is_collecting = False
        self._tts_start_time: Optional[str] = None

        # 从配置加载设置
        self._load_config()

    def _load_config(self):
        """从配置加载缓存设置."""
        try:
            tts_config = self.config_manager.config.TTS_CACHE
            self._enabled = tts_config.ENABLED
            cache_dir_str = tts_config.CACHE_DIR

            # 解析缓存目录路径
            project_root = resource_finder.get_project_root()
            self._cache_dir = project_root / cache_dir_str

            if self._enabled:
                logger.info(f"TTS 缓存已启用，目录: {self._cache_dir}")
            else:
                logger.debug("TTS 缓存已禁用")

        except Exception as e:
            logger.warning(f"加载 TTS 缓存配置失败: {e}")
            self._enabled = False

    @property
    def enabled(self) -> bool:
        """缓存是否启用."""
        return self._enabled

    def start_session(self):
        """启动新的缓存会话（应用启动时调用）.

        创建以当前日期-时间命名的会话目录。
        """
        if not self._enabled:
            return

        try:
            # 创建会话目录：<日期-时间>
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            self._session_dir = self._cache_dir / timestamp

            # 确保目录存在
            self._session_dir.mkdir(parents=True, exist_ok=True)

            # 重置计数器
            self._tts_counter = 0

            logger.info(f"TTS 缓存会话已启动: {self._session_dir}")

        except Exception as e:
            logger.error(f"创建 TTS 缓存会话目录失败: {e}")
            self._session_dir = None

    def end_session(self):
        """结束当前缓存会话（应用关闭时调用）."""
        if not self._enabled:
            return

        # 如果还有未保存的 TTS，先保存
        if self._is_collecting and self._audio_buffer:
            self._save_current_tts()

        if self._session_dir:
            logger.info(f"TTS 缓存会话已结束，共保存 {self._tts_counter} 个 TTS 音频")
            self._session_dir = None
            self._tts_counter = 0

    def start_tts(self):
        """开始收集新的 TTS 对话音频."""
        if not self._enabled or self._session_dir is None:
            return

        with self._lock:
            # 如果上一个 TTS 还没结束，先保存
            if self._is_collecting and self._audio_buffer:
                self._save_current_tts()

            # 开始新的 TTS 收集
            self._audio_buffer = []
            self._is_collecting = True
            self._tts_start_time = datetime.now().strftime("%H%M%S")
            logger.debug("开始收集 TTS 音频")

    def end_tts(self):
        """结束当前 TTS 对话，保存完整音频."""
        if not self._enabled or not self._is_collecting:
            return

        with self._lock:
            self._save_current_tts()
            self._is_collecting = False

    def append_audio(self, pcm_data: np.ndarray):
        """追加音频片段到缓冲区.

        Args:
            pcm_data: PCM 音频数据 (int16 格式, 24kHz 单声道)
        """
        if not self._enabled or not self._is_collecting:
            return

        with self._lock:
            # 确保数据是 int16 格式
            if pcm_data.dtype != np.int16:
                pcm_data = pcm_data.astype(np.int16)
            self._audio_buffer.append(pcm_data.copy())

    def _save_current_tts(self):
        """保存当前缓冲区中的完整 TTS 音频."""
        if not self._audio_buffer or self._session_dir is None:
            return

        try:
            # 合并所有音频片段
            combined_audio = np.concatenate(self._audio_buffer)

            # 计算音频时长
            duration_seconds = len(combined_audio) / AudioConfig.OUTPUT_SAMPLE_RATE

            # 生成文件名：<开始时间>_<序号>.wav
            self._tts_counter += 1
            filename = f"{self._tts_start_time}_{self._tts_counter:04d}.wav"
            filepath = self._session_dir / filename

            # 写入 WAV 文件
            self._write_wav(filepath, combined_audio)

            logger.info(
                f"TTS 音频已保存: {filename} "
                f"(时长: {duration_seconds:.2f}s, 片段数: {len(self._audio_buffer)})"
            )

            # 清空缓冲区
            self._audio_buffer = []

        except Exception as e:
            logger.warning(f"保存 TTS 音频失败: {e}")
            self._audio_buffer = []

    def _write_wav(self, filepath: Path, pcm_data: np.ndarray):
        """写入 WAV 文件.

        Args:
            filepath: 文件路径
            pcm_data: PCM 数据 (int16)
        """
        # WAV 文件参数
        sample_rate = AudioConfig.OUTPUT_SAMPLE_RATE  # 24000 Hz
        channels = AudioConfig.CHANNELS  # 1 (单声道)
        bits_per_sample = 16

        # 确保数据是 int16 格式
        if pcm_data.dtype != np.int16:
            pcm_data = pcm_data.astype(np.int16)

        # 计算数据大小
        data_size = len(pcm_data) * 2  # 16-bit = 2 bytes
        byte_rate = sample_rate * channels * bits_per_sample // 8
        block_align = channels * bits_per_sample // 8

        with open(filepath, "wb") as f:
            # RIFF 头
            f.write(b"RIFF")
            f.write(struct.pack("<I", 36 + data_size))  # 文件大小 - 8
            f.write(b"WAVE")

            # fmt 子块
            f.write(b"fmt ")
            f.write(struct.pack("<I", 16))  # fmt 块大小
            f.write(struct.pack("<H", 1))  # 音频格式 (1 = PCM)
            f.write(struct.pack("<H", channels))
            f.write(struct.pack("<I", sample_rate))
            f.write(struct.pack("<I", byte_rate))
            f.write(struct.pack("<H", block_align))
            f.write(struct.pack("<H", bits_per_sample))

            # data 子块
            f.write(b"data")
            f.write(struct.pack("<I", data_size))
            f.write(pcm_data.tobytes())
