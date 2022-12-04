import toml
from typing import Any, List, Mapping, Annotated, Union, Literal

from pydantic import BaseSettings, Field
from enum import Enum
from pydantic import BaseModel


def toml_config_settings_source(settings: BaseSettings) -> dict[str, Any]:
    """
    A simple settings source that loads variables from a TOML file
    at the project's root.

    Here we happen to choose to use the `env_file_encoding` from Config
    when reading `config.json`

    [server]
    log_level = "DEBUG"


    [iface.wlan0]
    freq = 5432
    tx_power = 30


    [channels.video.tx]
    iface = "wlan0"
    k = 2
    p = 4
    port = 5600
    id = 34445

    [channels.video.rx]
    k = 2
    p = 4
    port = 5700
    id = 34445

    [channels.thermal.tx]
    command = "wfb_tx -k 3 -p 4 wlan0 5777"

    [processes.camera]


    """
    raw = toml.load(settings.__config__.toml_file_path)
    print(raw)
    return raw


class LogLevel(str, Enum):
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    ERROR = 'ERROR'


class ServerConfig(BaseModel):
    log_level: LogLevel = LogLevel.INFO


class IfaceConfig(BaseModel):
    name: str = None
    freq: int = 5432
    tx_power: int = 30


class ChannelTxConfig(BaseModel):
    iface: str
    fec_k: int = 2
    fec_f: int = 4
    port: int
    link_id: int


class ChannelRxConfig(BaseModel):
    iface: str
    fec_k: int = 2
    fec_f: int = 4
    port: int
    link_id: int


class ProcessConfig(BaseModel):
    command: str


class ChannelConfig(BaseModel):
    tx: ChannelTxConfig | ProcessConfig = None
    rx: ChannelRxConfig | ProcessConfig = None


class Settings(BaseSettings):
    server: ServerConfig
    ifaces: List[IfaceConfig]
    channels: Mapping[str, ChannelConfig]
    processes: Mapping[str, ProcessConfig]

    class Config:

        toml_file_path = 'config.toml'

        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            return (
                init_settings,
                toml_config_settings_source,
                env_settings,
            )


settings = Settings()

print(settings)