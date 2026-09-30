from types import SimpleNamespace


def native_symbol(name="EURUSD", **updates):
    fields = dict(name=name, currency_base="EUR", currency_profit="USD", currency_margin="EUR",
                  digits=5, point=0.00001, trade_tick_size=0.00001,
                  trade_tick_value_profit=0.8, trade_tick_value_loss=0.9,
                  trade_contract_size=100000.0, volume_min=0.01, volume_max=100.0,
                  volume_step=0.01, volume_limit=0.0, trade_stops_level=0,
                  trade_freeze_level=0, trade_mode=4, trade_exemode=2,
                  filling_mode=2, order_mode=127, trade_calc_mode=0,
                  margin_initial=0.0, margin_maintenance=0.0, margin_hedged=0.0,
                  margin_hedged_use_leg=False)
    fields.update(updates)
    return SimpleNamespace(**fields)


def native_account(**updates):
    fields = dict(server="Fixture-Server", login=12345, currency="EUR", leverage=100, margin_mode=2)
    fields.update(updates)
    return SimpleNamespace(**fields)
