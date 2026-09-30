"""Development-only execution policy. There is deliberately no live override."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
import os


class ModeError(ValueError):
    """Configuration or verified broker state cannot authorize this operation."""


class ExecutionMode(str, Enum):
    HISTORICAL = "historical"
    PAPER = "paper"
    DEMO_MT5 = "demo_mt5"
    LIVE = "live"


@dataclass(frozen=True)
class DevelopmentPolicy:
    mode: ExecutionMode
    enable_demo_orders: bool = False

    def __post_init__(self):
        if not isinstance(self.mode, ExecutionMode):
            raise ModeError("Use an explicit validated execution mode")
        if type(self.enable_demo_orders) is not bool:
            raise ModeError("enable_demo_orders must be a YAML boolean")
        if self.mode is ExecutionMode.LIVE:
            raise ModeError("Live execution is disabled during foundational development")
        if self.enable_demo_orders and self.mode is not ExecutionMode.DEMO_MT5:
            raise ModeError("enable_demo_orders is only valid for demo_mt5")

    @classmethod
    def from_config(cls, config, *, environ=None):
        if not isinstance(config, Mapping) or not isinstance(config.get("broker"), Mapping):
            raise ModeError("Configuration requires a broker mapping with an explicit mode")
        broker = config["broker"]
        mode_value = broker.get("mode")
        if not isinstance(mode_value, str):
            raise ModeError("broker.mode must be historical, paper, demo_mt5 or live")
        try:
            mode = ExecutionMode(mode_value)
        except ValueError:
            raise ModeError("Unknown broker.mode; use historical, paper or demo_mt5") from None
        if "demo_mode" in broker and broker["demo_mode"] is not True:
            raise ModeError("Legacy demo_mode must be true; false no longer enables live execution")
        env = os.environ if environ is None else environ
        if "TRADING_MODE" in env and env["TRADING_MODE"] != mode.value:
            raise ModeError("TRADING_MODE must exactly match broker.mode; environment cannot override YAML")
        if "MT5_DEMO" in env and env["MT5_DEMO"] != "true":
            raise ModeError("Legacy MT5_DEMO must be exactly 'true' if present")
        return cls(mode, broker.get("enable_demo_orders", False))

    def require_demo_session(self):
        if self.mode is ExecutionMode.PAPER:
            raise ModeError("paper mode unavailable: real paper adapter is required (task 2.4)")
        if self.mode is ExecutionMode.HISTORICAL:
            raise ModeError("historical mode uses the separate backtester, not the online engine or MT5 executor")
        if self.mode is not ExecutionMode.DEMO_MT5 or self.enable_demo_orders is not True:
            raise ModeError("demo_mt5 requires the explicit enable_demo_orders: true test profile")


def validate_demo_credentials(login, password, server, path=None):
    """Validate without echoing secrets or falling back to the terminal's account."""
    if type(login) is not int or login <= 0:
        raise ModeError("A positive explicit MT5_LOGIN is required for demo_mt5")
    if not isinstance(password, str) or not password.strip():
        raise ModeError("MT5_PASSWORD is required for demo_mt5")
    if not isinstance(server, str) or not server.strip() or server != server.strip():
        raise ModeError("An explicit MT5_SERVER without surrounding whitespace is required")
    if path is not None and (not isinstance(path, str) or not path.strip()):
        raise ModeError("MT5_PATH must be a nonempty path when supplied")


def demo_credentials_from_environment():
    value = os.environ.get("MT5_LOGIN", "")
    try:
        login = int(value)
    except ValueError:
        raise ModeError("A positive explicit MT5_LOGIN is required for demo_mt5") from None
    credentials = dict(login=login, password=os.environ.get("MT5_PASSWORD", ""),
                       server=os.environ.get("MT5_SERVER", ""), path=os.environ.get("MT5_PATH"))
    validate_demo_credentials(**credentials)
    return credentials
