import json
import uuid
from pathlib import Path
from typing import Any, Dict

from omegaconf import DictConfig, OmegaConf

from simple_xiaozhi.utils.logging_config import get_logger
from simple_xiaozhi.utils.resource_finder import resource_finder

logger = get_logger(__name__)


class ConfigManager:
    """配置管理器 - 单例模式"""

    _instance = None

    # 默认配置
    DEFAULT_CONFIG = {
        "SYSTEM_OPTIONS": {
            "CLIENT_ID": None,
            "DEVICE_ID": None,
            "NETWORK": {
                "OTA_VERSION_URL": "https://api.tenclass.net/xiaozhi/ota/",
                "WEBSOCKET_URL": None,
                "WEBSOCKET_ACCESS_TOKEN": None,
                "MQTT_INFO": None,
                "ACTIVATION_VERSION": "v2",  # 可选值: v1, v2
                "AUTHORIZATION_URL": "https://xiaozhi.me/",
            },
        },
        "WAKE_WORD_OPTIONS": {
            "USE_WAKE_WORD": True,
            "MODEL_PATH": "models",
            "NUM_THREADS": 4,
            "PROVIDER": "cpu",
            "MAX_ACTIVE_PATHS": 2,
            "KEYWORDS_SCORE": 1.8,
            "KEYWORDS_THRESHOLD": 0.2,
            "NUM_TRAILING_BLANKS": 1,
        },
        "CAMERA": {
            "camera_index": 0,
            "frame_width": 640,
            "frame_height": 480,
            "fps": 30,
            "Local_VL_url": "https://open.bigmodel.cn/api/paas/v4/",
            "VLapi_key": "",
            "models": "glm-4v-plus",
        },
        "SHORTCUTS": {
            "ENABLED": True,
            "MANUAL_PRESS": {"modifier": "ctrl", "key": "j", "description": "按住说话"},
            "AUTO_TOGGLE": {"modifier": "ctrl", "key": "k", "description": "自动对话"},
            "ABORT": {"modifier": "ctrl", "key": "q", "description": "中断对话"},
            "MODE_TOGGLE": {"modifier": "ctrl", "key": "m", "description": "切换模式"},
            "WINDOW_TOGGLE": {
                "modifier": "ctrl",
                "key": "w",
                "description": "显示/隐藏窗口",
            },
        },
        "AEC_OPTIONS": {
            "ENABLED": False,
            "BUFFER_MAX_LENGTH": 200,
            "FRAME_DELAY": 3,
            "FILTER_LENGTH_RATIO": 0.4,
            "ENABLE_PREPROCESS": True,
        },
        "AUDIO_DEVICES": {
            "input_device_id": None,
            "input_device_name": None,
            "output_device_id": None,
            "output_device_name": None,
            "input_sample_rate": None,
            "output_sample_rate": None,
            "input_channels": None,
            "output_channels": None,
        },
    }

    def __new__(cls, *args, **kwargs):
        """
        确保单例模式.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        config_dir: Path | None = None,
        overrides: Dict[str, Any] | None = None,
    ):
        """
        初始化配置管理器.
        """
        if self._initialized:
            if config_dir is not None:
                self._set_config_dir(config_dir)
                self._config = self._load_config()
            if overrides is not None:
                self.set_overrides(overrides)
            return
        self._initialized = True
        self._overrides: DictConfig = OmegaConf.create({})

        # 初始化配置文件路径
        self._init_config_paths(config_dir)

        # 确保必要的目录存在
        self._ensure_required_directories()

        # 加载配置
        self._config = self._load_config()
        if overrides is not None:
            self.set_overrides(overrides)

    def _set_config_dir(self, config_dir: Path) -> None:
        config_path = Path(config_dir).expanduser()
        if not config_path.is_absolute():
            config_path = (Path.cwd() / config_path).resolve()
        else:
            config_path = config_path.resolve()
        self.config_dir = config_path
        self.config_file = self.config_dir / "config.json"

    def _init_config_paths(self, config_dir: Path | None = None):
        """
        Initialize config file paths.
        """
        if config_dir is not None:
            self._set_config_dir(config_dir)
        else:
            self.config_dir = resource_finder.find_config_dir()
            if not self.config_dir:
                project_root = resource_finder.get_project_root()
                self.config_dir = project_root / "config"
            self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Config directory: {self.config_dir.absolute()}")
        logger.info(f"Config file: {self.config_file.absolute()}")

    def _ensure_required_directories(self):
        """
        确保必要的目录存在.
        """
        project_root = resource_finder.get_project_root()

        # 创建 models 目录
        models_dir = project_root / "models"
        if not models_dir.exists():
            models_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"创建模型目录: {models_dir.absolute()}")

        # 创建 cache 目录
        cache_dir = project_root / "cache"
        if not cache_dir.exists():
            cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"创建缓存目录: {cache_dir.absolute()}")

    def _build_default_config(self) -> DictConfig:
        return OmegaConf.create(self.DEFAULT_CONFIG)

    def _load_config(self) -> DictConfig:
        """
        加载配置文件，如果不存在则创建.
        """
        try:
            if self.config_file.exists():
                logger.debug(f"使用实例路径找到配置文件: {self.config_file}")
                config = OmegaConf.load(self.config_file)
                return OmegaConf.merge(self._build_default_config(), config)
            else:
                logger.info("配置文件不存在，使用默认配置")
                return self._build_default_config()

        except Exception as e:
            logger.error(f"配置加载错误: {e}")
            return self._build_default_config()

    def _save_config(self, config: DictConfig) -> bool:
        """
        保存配置到文件.
        """
        try:
            # 确保配置目录存在
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # 保存配置文件
            data = OmegaConf.to_container(config, resolve=True)
            self.config_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            logger.debug(f"配置已保存到: {self.config_file}")
            return True

        except Exception as e:
            logger.error(f"配置保存错误: {e}")
            return False

    def set_overrides(self, overrides: Dict[str, Any] | None) -> None:
        self._overrides = OmegaConf.create(overrides or {})

    @property
    def config(self) -> DictConfig:
        if self._overrides and len(self._overrides) > 0:
            return OmegaConf.merge(self._config, self._overrides)
        return self._config

    @property
    def mutable_config(self) -> DictConfig:
        return self._config

    def save(self) -> bool:
        """
        保存当前配置到文件.
        """
        return self._save_config(self._config)

    def reload_config(self) -> bool:
        """
        重新加载配置文件.
        """
        try:
            self._config = self._load_config()
            logger.info("配置文件已重新加载")
            return True
        except Exception as e:
            logger.error(f"配置重新加载失败: {e}")
            return False

    def generate_uuid(self) -> str:
        """
        生成 UUID v4.
        """
        return str(uuid.uuid4())

    def initialize_client_id(self):
        """
        确保存在客户端ID.
        """
        if not self.config.SYSTEM_OPTIONS.CLIENT_ID:
            client_id = self.generate_uuid()
            self._config.SYSTEM_OPTIONS.CLIENT_ID = client_id
            if self.save():
                logger.info(f"已生成新的客户端ID: {client_id}")
            else:
                logger.error("保存新的客户端ID失败")

    def initialize_device_id_from_fingerprint(self, device_fingerprint):
        """
        从设备指纹初始化设备ID.
        """
        if not self.config.SYSTEM_OPTIONS.DEVICE_ID:
            try:
                # 从efuse.json获取MAC地址作为DEVICE_ID
                mac_address = device_fingerprint.get_mac_address_from_efuse()
                if mac_address:
                    self._config.SYSTEM_OPTIONS.DEVICE_ID = mac_address
                    if self.save():
                        logger.info(f"从efuse.json获取DEVICE_ID: {mac_address}")
                    else:
                        logger.error("保存DEVICE_ID失败")
                else:
                    logger.error("无法从efuse.json获取MAC地址")
                    # 备用方案：从设备指纹直接获取
                    fingerprint = device_fingerprint.generate_fingerprint()
                    mac_from_fingerprint = fingerprint.get("mac_address")
                    if mac_from_fingerprint:
                        self._config.SYSTEM_OPTIONS.DEVICE_ID = mac_from_fingerprint
                        if self.save():
                            logger.info(
                                f"使用指纹中的MAC地址作为DEVICE_ID: "
                                f"{mac_from_fingerprint}"
                            )
                        else:
                            logger.error("保存备用DEVICE_ID失败")
            except Exception as e:
                logger.error(f"初始化DEVICE_ID时出错: {e}")

    @classmethod
    def get_instance(cls, config_dir: Path | None = None, overrides: Dict[str, Any] | None = None):
        """
        获取配置管理器实例.
        """
        if cls._instance is None:
            cls._instance = cls(config_dir=config_dir, overrides=overrides)
        else:
            if config_dir is not None:
                cls._instance._set_config_dir(config_dir)
                cls._instance._config = cls._instance._load_config()
            if overrides is not None:
                cls._instance.set_overrides(overrides)
        return cls._instance
