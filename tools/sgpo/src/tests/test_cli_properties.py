import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sgpo.cli import _find_smartgit_properties


class TestFindSmartGitProperties(unittest.TestCase):
    def test_find_in_default_linux_config_dir(self):
        """Detect ~/.config/smartgit/.../smartgit.properties on Linux."""

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            props_dir = home / ".config" / "smartgit" / "25.1"
            props_dir.mkdir(parents=True)
            expected = props_dir / "smartgit.properties"
            expected.write_text("smartgit.debug.i18n.development=/tmp/po\n", encoding="utf-8")

            with mock.patch.dict(os.environ, {}, clear=True):
                with mock.patch("pathlib.Path.home", return_value=home):
                    found = _find_smartgit_properties()

            self.assertEqual(found[0], expected)

    def test_respects_xdg_config_home(self):
        """Detect when XDG_CONFIG_HOME points to a non-default location."""

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            xdg_config = home / "xdg" / "config"
            props_dir = xdg_config / "smartgit" / "25.1"
            props_dir.mkdir(parents=True)
            expected = props_dir / "smartgit.properties"
            expected.write_text("smartgit.debug.i18n.development=/tmp/po\n", encoding="utf-8")

            env = {"XDG_CONFIG_HOME": str(xdg_config)}
            with mock.patch.dict(os.environ, env, clear=True):
                with mock.patch("pathlib.Path.home", return_value=home):
                    found = _find_smartgit_properties()

            self.assertEqual(found[0], expected)

    def test_prefers_newer_version_first(self):
        """When multiple versions exist, newer (e.g. 25.1) is first."""

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            older = home / ".config" / "smartgit" / "24.1"
            newer = home / ".config" / "smartgit" / "25.1"
            for path in (older, newer):
                path.mkdir(parents=True)
                (path / "smartgit.properties").write_text("smartgit.i18n=ja_JP\n", encoding="utf-8")

            with mock.patch.dict(os.environ, {}, clear=True):
                with mock.patch("pathlib.Path.home", return_value=home):
                    found = _find_smartgit_properties()

            self.assertEqual(newer / "smartgit.properties", found[0])
            self.assertEqual(older / "smartgit.properties", found[1])

    def test_prefers_newer_version_across_platforms(self):
        """Newer version wins even if path order differs (macOS vs Windows)."""

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)

            mac_dir = home / "Library" / "Preferences" / "SmartGit" / "24.1"
            win_dir = home / "AppData" / "Roaming" / "syntevo" / "SmartGit" / "25.1"
            for path in (mac_dir, win_dir):
                path.mkdir(parents=True)
                (path / "smartgit.properties").write_text("smartgit.i18n=ja_JP\n", encoding="utf-8")

            with mock.patch.dict(os.environ, {}, clear=True):
                with mock.patch("pathlib.Path.home", return_value=home):
                    found = _find_smartgit_properties()

            self.assertEqual(win_dir / "smartgit.properties", found[0])
            self.assertEqual(mac_dir / "smartgit.properties", found[1])


if __name__ == "__main__":
    unittest.main()
