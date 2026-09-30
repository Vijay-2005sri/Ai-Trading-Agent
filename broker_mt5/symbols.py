"""Explicit instrument identity; broker spelling is only an adapter concern."""

from types import MappingProxyType

from config.execution_mode import ModeError


class SymbolError(ModeError):
    pass


_DEFAULT_BROKER = {
    "EURUSD": "EURUSD", "GBPUSD": "GBPUSD", "USDJPY": "USDJPY", "AUDUSD": "AUDUSD",
    "XAUUSD": "GOLD.i#", "XAGUSD": "SILVER.i#", "USOIL": "OILCash#",
    "BTCUSD": "BTCUSD#", "ETHUSD": "ETHUSD#",
}


class SymbolRegistry:
    def __init__(self, broker_symbols=None, legacy_aliases=None):
        mapping = dict(_DEFAULT_BROKER if broker_symbols is None else broker_symbols)
        if set(mapping) != set(_DEFAULT_BROKER):
            raise SymbolError("broker.symbol_map must define exactly the nine canonical instruments")
        aliases = {key: [value] for key, value in _DEFAULT_BROKER.items()}
        if legacy_aliases is not None:
            if not isinstance(legacy_aliases, dict) or not set(legacy_aliases) <= set(mapping):
                raise SymbolError("Invalid legacy symbol aliases")
            for key, values in legacy_aliases.items():
                if not isinstance(values, list):
                    raise SymbolError("Legacy aliases must be lists")
                aliases[key].extend(values)
        lookup = {}
        history = {}
        for canonical, broker in mapping.items():
            names = [canonical, broker, *aliases[canonical]]
            for name in names:
                if not isinstance(name, str) or not name or name != name.strip() or name == "GLOBAL":
                    raise SymbolError("Instrument names must be nonempty exact strings")
                if name in lookup and lookup[name] != canonical:
                    raise SymbolError(f"Ambiguous instrument name: {name}")
                lookup[name] = canonical
            history[canonical] = tuple(dict.fromkeys(names))
        self._broker = MappingProxyType(mapping)
        self._lookup = MappingProxyType(lookup)
        self._history = MappingProxyType(history)

    @classmethod
    def from_config(cls, config):
        broker = config.get("broker", {})
        mapping = broker.get("symbol_map")
        if "symbol_map" in broker and not isinstance(mapping, dict):
            raise SymbolError("broker.symbol_map must be a mapping")
        return cls(mapping, broker.get("legacy_symbol_aliases"))

    def canonical(self, name):
        if not isinstance(name, str) or name not in self._lookup:
            raise SymbolError(f"Unknown instrument: {name!r}")
        return self._lookup[name]

    def broker_symbol(self, name):
        canonical = name if isinstance(name, str) and name in self._broker else self.from_broker(name)
        return self._broker[canonical]

    def from_broker(self, name):
        for canonical, broker in self._broker.items():
            if name == broker:
                return canonical
        raise SymbolError(f"Unmapped current broker symbol: {name!r}")

    def aliases(self, name):
        return self._history[self.canonical(name)]

    def active_symbols(self, names):
        if not isinstance(names, list) or not names:
            raise SymbolError("broker.symbols must be a nonempty list")
        canonical = [self.canonical(name) for name in names]
        if len(set(canonical)) != len(canonical):
            raise SymbolError("Duplicate canonical instrument in broker.symbols")
        return canonical

    def memory_filter(self, name, *, include_global=False):
        names = list(self.aliases(name))
        if include_global:
            names.append("GLOBAL")
        return {"pair": {"$in": names}}
