"""Registry boundaries and real strategy smoke checks on synthetic closed bars."""

import json

import numpy as np
import pandas as pd


def test_twelve_baseline_strategies_load_and_run_without_suppressed_errors(capsys):
    from strategy_library import strategy_master as master
    assert master.get_active_count() == 12
    close = 1.1 + np.arange(200) * 0.00001 + np.sin(np.arange(200) / 5) * 0.001
    frame = pd.DataFrame({
        "open": close - 0.0001, "high": close + 0.0003,
        "low": close - 0.0003, "close": close,
        "tick_volume": np.full(200, 100), "real_volume": np.zeros(200),
        "spread": np.full(200, 10),
    }, index=pd.date_range("2026-01-01", periods=200, freq="h", tz="UTC"))
    signals = master.run_all_strategies(frame, "EURUSD")
    # Call each implementation directly too: runner's broad catch cannot mask
    # a broken strategy by changing its warning text.
    for strategy in master.STRATEGY_REGISTRY.values():
        assert isinstance(strategy(pair="EURUSD").generate_signals(frame), list)
    assert "failed:" not in capsys.readouterr().out
    assert signals == sorted(signals, key=lambda item: item["confidence"], reverse=True)
    for signal in signals:
        assert {"strategy", "direction", "pair", "entry_price", "stop_loss", "take_profit"} <= signal.keys()
        assert signal["pair"] == "EURUSD"
    assert "Total strategies active: 12" in master.get_strategy_summary()


def test_registry_filters_non_live_and_experimental_without_importing_them(tmp_path, monkeypatch):
    from strategy_library import strategy_master as master
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"strategies": {
        "disabled": {"status": "DISABLED", "file": "disabled.py", "class": "Disabled"},
        "experimental": {"status": "LIVE", "file": "experimental/test.py", "class": "Unsafe"},
        "dynamic": {"status": "LIVE", "file": "dynamic_strategies/test.py", "class": "Unsafe"},
        "valid": {"status": "LIVE", "file": "trend_following.py", "class": "EMACrossoverStrategy"},
    }}))
    monkeypatch.setattr(master, "REGISTRY_PATH", path)
    imports = []

    def import_spy(module, name):
        imports.append((module, name))
        return object

    monkeypatch.setattr(master, "_dynamic_import", import_spy)
    assert master._build_strategy_registry() == {"valid": object}
    assert imports == [("strategy_library.live.trend_following", "EMACrossoverStrategy")]
