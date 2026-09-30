"""Offline test entry point: disable unrelated plugins before pytest starts."""

import os
from pathlib import Path
import sys

os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
sys.dont_write_bytecode = True
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
os.chdir(root)

if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main(sys.argv[1:]))
