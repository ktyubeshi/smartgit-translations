from __future__ import annotations

from pathlib import Path

from path_finder import PoPathFinder
from sgpo.tui_helpers import _menu_choices


def test_menu_contains_config_action(tmp_path: Path) -> None:
    finder = PoPathFinder(repository_root_dir=str(tmp_path), version="24_1")
    values = [getattr(choice, "value", None) for choice in _menu_choices(finder)]
    assert "config" in values

