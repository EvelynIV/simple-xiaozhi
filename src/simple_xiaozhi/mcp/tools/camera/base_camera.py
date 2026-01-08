"""
Base camera implementation.
"""

import threading
from abc import ABC, abstractmethod
from typing import Dict

from simple_xiaozhi.utils.config_manager import ConfigManager
from simple_xiaozhi.utils.logging_config import get_logger

logger = get_logger(__name__)


class BaseCamera(ABC):
    """
    基础摄像头类，定义接口.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        """
        初始化基础摄像头.
        """
        self.jpeg_data = {"buf": b"", "len": 0}  # 图像的JPEG字节数据  # 字节数据长度

        # 从配置中读取相机参数
        config = ConfigManager.get_instance().config
        self.camera_index = config.CAMERA.camera_index
        self.frame_width = config.CAMERA.frame_width
        self.frame_height = config.CAMERA.frame_height

    @abstractmethod
    def capture(self) -> bool:
        """
        捕获图像.
        """

    @abstractmethod
    def analyze(self, question: str) -> str:
        """
        分析图像.
        """

    def get_jpeg_data(self) -> Dict[str, any]:
        """
        获取JPEG数据.
        """
        return self.jpeg_data

    def set_jpeg_data(self, data_bytes: bytes):
        """
        设置JPEG数据.
        """
        self.jpeg_data["buf"] = data_bytes
        self.jpeg_data["len"] = len(data_bytes)
