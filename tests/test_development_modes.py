"""Development mode contract: unavailable/unsafe modes stop before I/O."""

from copy import deepcopy
from unittest.mock import Mock

import pytest

from config.execution_mode import DevelopmentPolicy, ModeError


def profile(mode="demo_mt5", enabled=True):
    return {"broker": {"mode": mode, "demo_mode": True, "enable_demo_orders": enabled}}


@pytest.mark.parametrize("bad", [None, [], {}, {"broker": None}, {"broker": {}},
                                     profile("LIVE"), profile("unknown"), profile(None)])
def test_invalid_or_missing_mode_is_rejected(bad):
    with pytest.raises(ModeError):
        DevelopmentPolicy.from_config(bad, environ={})


@pytest.mark.parametrize("value", [False, "true", "false", 0, 1, None])
def test_legacy_demo_flag_cannot_select_live_or_use_truthiness(value):
    config = profile()
    config["broker"]["demo_mode"] = value
    with pytest.raises(ModeError):
        DevelopmentPolicy.from_config(config, environ={})


@pytest.mark.parametrize("enabled", [False, "true", "false", 0, 1, None])
def test_demo_requires_strict_explicit_opt_in(enabled):
    with pytest.raises(ModeError):
        DevelopmentPolicy.from_config(profile(enabled=enabled), environ={}).require_demo_session()


@pytest.mark.parametrize("environ", [{"TRADING_MODE": "live"}, {"TRADING_MODE": "paper"},
                                         {"TRADING_MODE": ""}, {"MT5_DEMO": "false"},
                                         {"MT5_DEMO": "1"}, {"MT5_DEMO": ""}])
def test_environment_cannot_override_or_ambiguously_enable_mode(environ):
    with pytest.raises(ModeError):
        DevelopmentPolicy.from_config(profile(), environ=environ)


def test_explicit_demo_profile_and_matching_environment():
    policy = DevelopmentPolicy.from_config(profile(), environ={"TRADING_MODE": "demo_mt5", "MT5_DEMO": "true"})
    policy.require_demo_session()
    assert policy.mode.value == "demo_mt5"


@pytest.mark.parametrize("mode", ["paper", "historical", "live"])
def test_unavailable_modes_cannot_construct_broker_session(mode):
    with pytest.raises(ModeError):
        DevelopmentPolicy.from_config(profile(mode, False), environ={}).require_demo_session()


@pytest.mark.parametrize("mode", ["paper", "historical", "live", "unknown", None])
def test_startup_rejects_mode_before_external_constructors(monkeypatch, settings, mode):
    import main
    config = deepcopy(settings)
    config["broker"].update(mode=mode, enable_demo_orders=False)
    monkeypatch.setattr(main, "load_config", lambda: config)
    constructors = []
    for name in ("MT5DataFetcher", "OrderExecutor", "WebSearchAgent", "TradingRAG", "LLMProvider"):
        spy = Mock(side_effect=AssertionError("External constructor reached"))
        monkeypatch.setattr(main, name, spy)
        constructors.append(spy)
    with pytest.raises(ModeError):
        main.TradingEngine()
    for spy in constructors:
        spy.assert_not_called()


def test_shipped_profile_cannot_start_a_broker_session(settings):
    policy = DevelopmentPolicy.from_config(settings, environ={})
    assert policy.mode.value == "paper"
    assert policy.enable_demo_orders is False
    with pytest.raises(ModeError, match="paper"):
        policy.require_demo_session()


@pytest.mark.parametrize("environ", [{"MT5_DEMO": "True"}, {"MT5_DEMO": " true "},
                                         {"TRADING_MODE": "demo_mt5 "}])
def test_environment_values_are_exact_not_truthy(environ):
    with pytest.raises(ModeError):
        DevelopmentPolicy.from_config(profile(), environ=environ)


@pytest.mark.parametrize("boundary", ["connect", "feed", "identity", "health", "rag", "provider"])
def test_startup_failure_cleans_session_and_never_enters_cycle(startup, boundary):
    main, doubles = startup
    executor = doubles["OrderExecutor"].return_value
    fetcher = doubles["MT5DataFetcher"].return_value
    if boundary == "connect":
        executor.connect.return_value = False
    elif boundary == "feed":
        fetcher.connect.return_value = False
    elif boundary == "identity":
        executor.assert_demo_session.side_effect = ModeError("Account changed by feed")
    elif boundary == "health":
        fetcher.health_check.side_effect = ModeError("Health unavailable")
    else:
        doubles["TradingRAG" if boundary == "rag" else "LLMProvider"].side_effect = ModeError("Fixture startup failure")
    with pytest.raises(ModeError):
        main.TradingEngine()
    executor.disconnect.assert_called_once()
    executor.place_order.assert_not_called()
    if boundary == "connect":
        doubles["MT5DataFetcher"].assert_not_called()
    if boundary in {"connect", "feed", "identity", "health"}:
        doubles["TradingRAG"].assert_not_called()
        doubles["LLMProvider"].assert_not_called()


@pytest.mark.parametrize("key,value", [("MT5_LOGIN", ""), ("MT5_LOGIN", "not-an-account"),
                                         ("MT5_LOGIN", "0"), ("MT5_PASSWORD", ""), ("MT5_SERVER", "")])
def test_startup_invalid_credentials_do_not_create_adapters(startup, monkeypatch, key, value):
    main, doubles = startup
    monkeypatch.setenv(key, value)
    with pytest.raises(ModeError):
        main.TradingEngine()
    for constructor in doubles.values():
        constructor.assert_not_called()


def test_cli_reports_blocked_startup_without_entering_loop(monkeypatch, capsys):
    import main
    constructor = Mock(side_effect=ModeError("paper adapter unavailable"))
    monkeypatch.setattr(main, "TradingEngine", constructor)
    assert main.main() == 1
    assert "[BLOCKED] paper adapter unavailable" in capsys.readouterr().out


@pytest.mark.parametrize("contents", [None, "broker: [invalid yaml"])
def test_missing_or_malformed_yaml_has_explicit_startup_error(tmp_path, monkeypatch, contents):
    import main
    monkeypatch.setattr(main, "__file__", str(tmp_path / "main.py"))
    if contents is not None:
        (tmp_path / "config").mkdir()
        (tmp_path / "config/settings.yaml").write_text(contents)
    with pytest.raises(ModeError, match="startup blocked"):
        main.load_config()
