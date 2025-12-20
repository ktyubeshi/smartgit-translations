from __future__ import annotations

import argparse
import subprocess
import sys
import re
import textwrap
import os
from pathlib import Path
from typing import Iterable, Sequence

import questionary
import tomllib
from sgpo.actions import (
    _cleanup_obsolete_empty_msgstr_po,
    _compress_msgctxt_msgid,
    _default_output_path,
    _delete_extracted_comments,
    _ensure_colon_suffix_po,
    _export_placeholder_msgids,
    _format_locales,
    _format_pot,
    _import_mismatch,
    _import_pot,
    _import_unknown,
    _propagate_ellipsis_translation_po,
    _special_sort_locales,
    _strip_msgctxt_placeholders_po,
    _extract_added_entries,
)
from sgpo.tui_helpers import (
    MENU_STYLE,
    _enable_escape_cancel,
    _interactive_simple,
    _menu_choices,
    _patch_shortcut_rendering,
    _po_choices,
    _po_target_selection,
    _prompt_required_text,
    _run_with_feedback,
    _select_po_and_pot_files,
    _select_po_files,
)
from path_finder import PoPathFinder, get_repository_root


CONFIG_FILENAME = "sgpo.toml"
_VERSION_PATTERN = re.compile(r"^(unknown|mismatch)\.(\d+_\d+)$")
_SMARTGIT_PROP_NAME = "smartgit.properties"
_SMARTGIT_PROP_KEY_REPO = "smartgit.debug.i18n.development"


def _load_config(base_dir: Path) -> tuple[str | None, str | None]:
    """Load sgpo.toml from base_dir if present."""

    path = base_dir / CONFIG_FILENAME
    if not path.exists():
        return None, None

    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except Exception:
        return None, None

    repo_root = data.get("repo_root")
    version = data.get("version")
    return repo_root, version


def _read_properties(path: Path) -> dict[str, str]:
    """Parse a minimal .properties file (key=value)."""

    props: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
        elif ":" in line:
            key, value = line.split(":", 1)
        else:
            continue
        props[key.strip()] = value.strip()
    return props


def _find_smartgit_properties() -> list[Path]:
    """Best-effort search for *all* smartgit.properties in common locations.

    Returns a list ordered by (newer version first) then platform-specific preference.
    """

    home = Path.home()
    xdg_config_home = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))

    # Order matters for tie‑breaking after version priority.
    candidates: list[Path] = [
        home / "Library" / "Preferences" / "SmartGit",  # macOS
        xdg_config_home / "smartgit",  # Linux (current default)
        xdg_config_home / "SmartGit",  # Linux (older installers / case variants)
        xdg_config_home / "syntevo" / "SmartGit",  # Linux (older Syntevo layout)
        home / ".smartgit",  # Linux legacy
        home / ".SmartGit",  # Linux legacy (case variant)
        home / "AppData" / "Roaming" / "syntevo" / "SmartGit",  # Windows
        home / "AppData" / "Roaming" / "SmartGit",  # Windows (legacy)
    ]

    found: list[tuple[int, Path]] = []
    seen_dirs: set[tuple[int, int]] = set()
    seen_files: set[tuple[int, int]] = set()
    for idx, base in enumerate(candidates):
        try:
            base_stat = base.stat()
        except OSError:
            continue
        base_id = (base_stat.st_dev, base_stat.st_ino)
        if base_id in seen_dirs:
            continue
        seen_dirs.add(base_id)
        for path in base.glob(f"**/{_SMARTGIT_PROP_NAME}"):
            try:
                path_stat = path.stat()
            except OSError:
                continue
            path_id = (path_stat.st_dev, path_stat.st_ino)
            if path_id in seen_files:
                continue
            seen_files.add(path_id)
            found.append((idx, path))

    def _version_key(item: tuple[int, Path]) -> tuple[int, int, int, int]:
        idx, path = item
        ver = _derive_version_from_properties_path(path)
        if ver and "_" in ver:
            major, minor = ver.split("_", 1)
            try:
                return (0, -int(major), -int(minor), idx)
            except ValueError:
                pass
        return (1, 0, 0, idx)

    found.sort(key=_version_key)
    return [path for _, path in found]


def _derive_repo_from_properties(props: dict[str, str]) -> str | None:
    """Try to deduce repo_root from SmartGit properties."""

    dev_path = props.get(_SMARTGIT_PROP_KEY_REPO)
    if not dev_path:
        return None

    po_path = Path(dev_path).expanduser()
    if po_path.name == "po":
        return str(po_path.parent.resolve())
    if po_path.is_dir() and (po_path / "po").exists():
        return str(po_path.resolve())
    return None


def _derive_version_from_properties_path(path: Path) -> str | None:
    """Try to extract version suffix from SmartGit settings path (e.g., 25.1 -> 25_1)."""

    for part in reversed(path.parts):
        match = re.match(r"(\d+)[._](\d+)", part)
        if match:
            return f"{match.group(1)}_{match.group(2)}"
    return None


def _version_suffix_candidates(po_dir: Path) -> list[str]:
    """Return detected version suffixes like 24_1 from unknown./mismatch. files."""

    if not po_dir.exists():
        return []

    versions = {
        match.group(2)
        for path in po_dir.iterdir()
        if path.is_file() and (match := _VERSION_PATTERN.match(path.name))
    }
    return sorted(versions)


def _resolve_version(repo_root: str, provided: str | None, interactive: bool = True) -> str:
    """Choose version suffix: use provided, otherwise auto-detect from unknown./mismatch. files."""

    if provided:
        return provided

    po_dir = Path(repo_root) / "po"
    candidates = _version_suffix_candidates(po_dir)

    if not candidates:
        return "24_1"
    if len(candidates) == 1 or not interactive:
        return candidates[0]

    prompt = questionary.select(
        "Select version suffix (from unknown./mismatch. files):",
        choices=[questionary.Choice(title=ver, value=ver) for ver in candidates],
        qmark="❯",
        instruction="(Enter to confirm, Esc to cancel)",
        style=MENU_STYLE,
    )
    choice = _enable_escape_cancel(prompt).ask(kbi_msg="")
    return choice or candidates[0]


def _write_config(path: Path, repo_root: str, version: str) -> None:
    header = "# sgpo configuration\n"
    body = textwrap.dedent(
        f"""\
        repo_root = "{repo_root}"
        version = "{version}"
        """
    )
    path.write_text(header + body, encoding="utf-8")


def _init_config(repo_root: str, version_suffix: str | None) -> int:
    props_paths = _find_smartgit_properties()

    selected_props: Path | None = None
    if props_paths:
        if len(props_paths) == 1:
            selected_props = props_paths[0]
        else:
            choices = [
                questionary.Choice(
                    title=f"{path} (version: {_derive_version_from_properties_path(path) or 'unknown'})",
                    value=path,
                )
                for path in props_paths
            ]
            prompt = questionary.select(
                "Detected multiple smartgit.properties files. Choose one:",
                choices=choices + [questionary.Choice(title="Cancel", value=None)],
                qmark="❯",
                instruction="(Enter to confirm, Esc to cancel)",
                style=MENU_STYLE,
            )
            selected_props = _enable_escape_cancel(prompt).ask(kbi_msg="")
            if selected_props is None:
                questionary.print("Canceled init.", style="bold fg:yellow")
                return 1

    props = _read_properties(selected_props) if selected_props else {}
    repo_from_props = _derive_repo_from_properties(props)
    props_version_hint = _derive_version_from_properties_path(selected_props) if selected_props else None

    cwd = str(Path.cwd())
    repo = repo_root or repo_from_props or cwd
    version_hint = version_suffix or (props_version_hint if repo == repo_from_props else None)

    if not repo_root and repo_from_props and repo_from_props != cwd:
        prompt = questionary.select(
            "Select repository root for sgpo.toml:",
            choices=[
                questionary.Choice(title=f"Use SmartGit config path ({repo_from_props})", value="props"),
                questionary.Choice(title=f"Use current working directory ({cwd})", value="cwd"),
                questionary.Choice(title="Cancel", value="cancel"),
            ],
            qmark="❯",
            instruction="(Enter to confirm, Esc to cancel)",
            style=MENU_STYLE,
        )
        choice = _enable_escape_cancel(prompt).ask(kbi_msg="")
        if choice in (None, "cancel"):
            questionary.print("Canceled init.", style="bold fg:yellow")
            return 1
        if choice == "cwd":
            repo = cwd
            version_hint = version_suffix
        elif choice == "props":
            repo = repo_from_props
            version_hint = version_suffix or props_version_hint

    version = _resolve_version(repo, version_hint, interactive=True)
    config_path = Path.cwd() / CONFIG_FILENAME

    if config_path.exists():
        prompt = questionary.select(
            f"{CONFIG_FILENAME} already exists at {config_path}. Overwrite?",
            choices=[
                questionary.Choice(title="Overwrite", value="overwrite"),
                questionary.Choice(title="Keep existing (cancel)", value="cancel"),
            ],
            qmark="❯",
            instruction="(Enter to confirm, Esc to cancel)",
            style=MENU_STYLE,
        )
        choice = _enable_escape_cancel(prompt).ask(kbi_msg="")
        if choice != "overwrite":
            questionary.print(f"[skip] Kept existing {CONFIG_FILENAME}.", style="bold fg:yellow")
            return 1

    _write_config(config_path, str(Path(repo).resolve()), version)
    if selected_props:
        questionary.print(f"Detected {selected_props} and used it as a hint.", style="fg:cyan")
    questionary.print(f"Created {CONFIG_FILENAME} at {config_path}", style="bold fg:green")
    return 0


def _interactive_placeholder_msgids(finder: PoPathFinder) -> None:
    repo_root = Path(finder.root_dir).resolve()
    targets = _select_po_and_pot_files(finder)
    if targets is None:
        return
    default_output = repo_root / "tmp" / "placeholder-msgid"
    prompt = questionary.text(
        "Output directory for extracted placeholder entries:",
        default=str(default_output),
        qmark="❯",
        style=MENU_STYLE,
    )
    output_raw = _enable_escape_cancel(prompt).ask(kbi_msg="")
    if output_raw is None:
        return

    output_dir = Path(output_raw.strip()) if output_raw.strip() else default_output
    if not output_dir.is_absolute():
        output_dir = (repo_root / output_dir).resolve()

    _run_with_feedback(lambda: _export_placeholder_msgids(repo_root, targets, output_dir))




def _interactive_extract_added_entries(finder: PoPathFinder) -> None:
    repo_root = Path(finder.root_dir).resolve()
    po_path = _po_target_selection(finder)
    if po_path is None:
        return

    old_commit = _prompt_required_text("Older commit/tag:", default="HEAD~1")
    if old_commit is None:
        return

    new_commit = _prompt_required_text("Newer commit/tag:", default="HEAD")
    if new_commit is None:
        return

    selected_path = Path(po_path)
    target_abs = selected_path if selected_path.is_absolute() else (repo_root / selected_path).resolve()
    default_output = _default_output_path(target_abs, repo_root, old_commit, new_commit)

    output_prompt = questionary.text(
        "Output path (Enter to use the suggested default):",
        default=str(default_output),
        qmark="❯",
        style=MENU_STYLE,
    )
    output_raw = _enable_escape_cancel(output_prompt).ask(kbi_msg="")
    if output_raw is None:
        return

    output_path = Path(output_raw.strip()) if output_raw.strip() else default_output

    _run_with_feedback(
        lambda: _extract_added_entries(repo_root, po_path, old_commit, new_commit, output_path)
    )


def _run_cli_lines(lines: Iterable[str]) -> int:
    try:
        for line in lines:
            print(line)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


def _interactive_import_pot(finder: PoPathFinder) -> None:
    while True:
        targets = _select_po_files(finder, "Import POT into all locales")
        if targets is None:
            return
        if not targets:
            questionary.print(
                "No locales selected. Please choose at least one locale.",
                style="bold fg:yellow",
            )
            continue
        _run_with_feedback(lambda: _import_pot(finder, targets))
        return


def _interactive_format(finder: PoPathFinder) -> None:
    while True:
        targets = _select_po_files(finder, "Format all locales")
        if targets is None:
            return
        if not targets:
            questionary.print(
                "No locales selected. Please choose at least one locale.",
                style="bold fg:yellow",
            )
            continue
        _run_with_feedback(lambda: _format_locales(finder, targets))
        return


def _interactive_special_sort(finder: PoPathFinder) -> None:
    while True:
        targets = _select_po_files(finder, "Special sort all locales")
        if targets is None:
            return
        if not targets:
            questionary.print(
                "No locales selected. Please choose at least one locale.",
                style="bold fg:yellow",
            )
            continue
        _run_with_feedback(lambda: _special_sort_locales(finder, targets))
        return


def _interactive_simple(action, finder: PoPathFinder) -> None:
    _run_with_feedback(lambda: action(finder))


def _print_current_settings(repo: str, version: str, config_base_dir: Path) -> None:
    config_path = config_base_dir / CONFIG_FILENAME
    questionary.print("=== Current settings ===", style="bold")
    questionary.print(f"Config base dir: {config_base_dir}", style="fg:cyan")
    questionary.print(
        f"Config file: {config_path} ({'present' if config_path.exists() else 'missing'})",
        style="fg:cyan",
    )
    questionary.print(f"Repo root (session): {Path(repo).resolve()}", style="fg:cyan")
    questionary.print(f"Version suffix (session): {version}", style="fg:cyan")

    config_repo, config_version = _load_config(config_base_dir)
    if config_repo or config_version:
        questionary.print("")
        questionary.print("Loaded from config file:", style="bold")
        if config_repo:
            questionary.print(f"  repo_root = {config_repo}", style="fg:cyan")
        if config_version:
            questionary.print(f"  version = {config_version}", style="fg:cyan")

    if config_path.exists():
        try:
            content = config_path.read_text(encoding="utf-8").rstrip()
        except Exception:
            content = ""
        if content:
            questionary.print("")
            questionary.print("--- sgpo.toml ---", style="bold")
            questionary.print(content)


def _prompt_version_suffix(repo: str, default: str) -> str | None:
    po_dir = Path(repo) / "po"
    candidates = _version_suffix_candidates(po_dir)

    if candidates:
        choices: list[questionary.Choice] = []
        for ver in candidates:
            label = f"{ver} (current)" if ver == default else ver
            choices.append(questionary.Choice(title=label, value=ver))
        choices.append(questionary.Choice(title="Enter custom value…", value="custom"))
        choices.append(questionary.Choice(title="Cancel", value=None))

        prompt = questionary.select(
            "Select version suffix:",
            choices=choices,
            qmark="❯",
            instruction="(Enter to confirm, Esc to cancel)",
            style=MENU_STYLE,
        )
        selection = _enable_escape_cancel(prompt).ask(kbi_msg="")
        if selection == "custom":
            return _prompt_required_text("Enter version suffix (e.g. 25_1):", default=default)
        return selection

    return _prompt_required_text("Enter version suffix (e.g. 25_1):", default=default)


def _discover_repo_root(start: Path) -> Path | None:
    start_dir = start.resolve() if start.is_dir() else start.resolve().parent

    for parent in [start_dir] + list(start_dir.parents):
        if (parent / ".git").exists():
            return parent

    for parent in [start_dir] + list(start_dir.parents):
        if (parent / "po").is_dir():
            return parent

    return None


def _run_git(args: list[str], cwd: Path) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return proc.stdout


def _git_toplevel(start: Path) -> Path | None:
    start_dir = start if start.is_dir() else start.parent
    out = _run_git(["rev-parse", "--show-toplevel"], cwd=start_dir)
    if not out:
        return None
    line = out.splitlines()[0].strip() if out.splitlines() else ""
    if not line:
        return None
    return Path(line).expanduser().resolve()


def _git_worktrees(repo_dir: Path) -> list[tuple[Path, str | None]]:
    out = _run_git(["worktree", "list", "--porcelain"], cwd=repo_dir)
    if not out:
        return []

    worktrees: list[tuple[Path, str | None]] = []
    current_path: Path | None = None
    current_branch: str | None = None

    for raw in out.splitlines():
        line = raw.strip()
        if line.startswith("worktree "):
            if current_path is not None:
                worktrees.append((current_path, current_branch))
            current_path = Path(line[len("worktree ") :].strip()).expanduser()
            current_branch = None
            continue

        if line.startswith("branch "):
            ref = line[len("branch ") :].strip()
            current_branch = ref.removeprefix("refs/heads/")
            continue

        if line == "detached":
            current_branch = "detached"
            continue

    if current_path is not None:
        worktrees.append((current_path, current_branch))

    return [(path.resolve(), branch) for path, branch in worktrees]


def _repo_root_choice_sections(repo: str, config_base_dir: Path) -> list[tuple[str, list[tuple[str, Path]]]]:
    """Return repo root candidates grouped into labeled sections for selection."""

    tool_cwd = Path.cwd().resolve()
    session_repo = Path(repo).expanduser()
    if not session_repo.is_absolute():
        session_repo = (tool_cwd / session_repo).resolve()
    config_base_dir = config_base_dir.expanduser()
    if not config_base_dir.is_absolute():
        config_base_dir = (tool_cwd / config_base_dir).resolve()
    else:
        config_base_dir = config_base_dir.resolve()

    sections: dict[str, list[tuple[str, Path]]] = {}
    seen: set[str] = set()

    def _add(section: str, label: str, path: Path) -> None:
        resolved = path.expanduser()
        if not resolved.is_absolute():
            resolved = (tool_cwd / resolved).resolve()
        else:
            resolved = resolved.resolve()
        key = str(resolved)
        if key in seen:
            return
        seen.add(key)
        sections.setdefault(section, []).append((label, resolved))

    _add("Execution", "Tool working directory (cwd)", tool_cwd)
    _add("Execution", "Current session repo root", session_repo)
    _add("Execution", "Config base dir", config_base_dir)

    config_repo, _config_version = _load_config(config_base_dir)
    if config_repo:
        _add("Config", f"repo_root from {CONFIG_FILENAME}", Path(config_repo))

    discovered = _discover_repo_root(tool_cwd)
    if discovered:
        _add("Discovery", "Parent search (.git / po) from cwd", discovered)

    git_root_cwd = _git_toplevel(tool_cwd)
    if git_root_cwd:
        _add("Git", "Git top-level from cwd", git_root_cwd)

    git_root_session = _git_toplevel(session_repo)
    if git_root_session:
        _add("Git", "Git top-level from session repo", git_root_session)

    worktree_base = git_root_session or git_root_cwd
    if worktree_base:
        for path, branch in _git_worktrees(worktree_base):
            suffix = f" ({branch})" if branch else ""
            _add("Git worktrees", f"Worktree{suffix}", path)

    for props_path in _find_smartgit_properties():
        try:
            props = _read_properties(props_path)
        except Exception:
            continue
        repo_from_props = _derive_repo_from_properties(props)
        if not repo_from_props:
            continue
        ver_hint = _derive_version_from_properties_path(props_path) or "unknown"
        _add("SmartGit", f"From {props_path} (ver: {ver_hint})", Path(repo_from_props))

    return [(name, items) for name, items in sections.items() if items]


def _interactive_config(repo: str, version: str, config_base_dir: Path) -> tuple[str, str, Path]:
    while True:
        questionary.print("")
        questionary.print("=== Config ===", style="bold")

        config_path = config_base_dir / CONFIG_FILENAME
        prompt = questionary.select(
            "Choose a config operation:",
            choices=[
                questionary.Choice(title="Show current settings", value="show"),
                questionary.Choice(title=f"Write {CONFIG_FILENAME} from current settings", value="write"),
                questionary.Choice(title=f"Reload settings from {CONFIG_FILENAME}", value="reload"),
                questionary.Choice(title="Set working directory (repo root)", value="set_repo"),
                questionary.Choice(title="Set version suffix (session)", value="set_version"),
                questionary.Choice(title="Back", value="back"),
            ],
            qmark="❯",
            instruction="(Enter to confirm, Esc to go back)",
            style=MENU_STYLE,
        )
        action = _enable_escape_cancel(prompt).ask(kbi_msg="")

        if action in (None, "back"):
            return repo, version, config_base_dir

        if action == "show":
            _print_current_settings(repo, version, config_base_dir)
            continue

        if action == "write":
            if config_path.exists():
                overwrite_prompt = questionary.select(
                    f"{CONFIG_FILENAME} already exists at {config_path}. Overwrite?",
                    choices=[
                        questionary.Choice(title="Overwrite", value="overwrite"),
                        questionary.Choice(title="Cancel", value="cancel"),
                    ],
                    qmark="❯",
                    instruction="(Enter to confirm, Esc to cancel)",
                    style=MENU_STYLE,
                )
                choice = _enable_escape_cancel(overwrite_prompt).ask(kbi_msg="")
                if choice != "overwrite":
                    questionary.print("Canceled.", style="bold fg:yellow")
                    continue

            _write_config(config_path, str(Path(repo).resolve()), version)
            questionary.print(f"Wrote {CONFIG_FILENAME} to {config_path}", style="bold fg:green")
            continue

        if action == "reload":
            config_repo, config_version = _load_config(config_base_dir)
            if not config_repo and not config_version:
                questionary.print(
                    f"No {CONFIG_FILENAME} found (or it could not be read).",
                    style="bold fg:yellow",
                )
                continue

            if config_repo:
                repo = config_repo
            version = _resolve_version(repo, config_version, interactive=True)
            questionary.print("Reloaded settings.", style="bold fg:green")
            questionary.print(f"Repo root (session): {Path(repo).resolve()}", style="fg:cyan")
            questionary.print(f"Version suffix (session): {version}", style="fg:cyan")
            continue

        if action == "set_repo":
            sections = _repo_root_choice_sections(repo, config_base_dir)
            choices: list = []
            for section, entries in sections:
                choices.append(questionary.Separator(f" {section}"))
                for label, path in entries:
                    missing = " (missing)" if not path.exists() else ""
                    title = f"    ↳ {label}: {path}{missing}"
                    choices.append(questionary.Choice(title=title, value=str(path)))

            choices.append(questionary.Separator(" Manual"))
            choices.append(questionary.Choice(title="    ↳ Enter custom path…", value="custom"))
            choices.append(questionary.Choice(title="    ↳ Cancel", value=None))

            repo_prompt = questionary.select(
                "Select working directory / repo root:",
                choices=choices,
                qmark="❯",
                instruction="(Enter to confirm, Esc to cancel)",
                style=MENU_STYLE,
                use_shortcuts=True,
            )
            selection = _enable_escape_cancel(repo_prompt).ask(kbi_msg="")
            if selection is None:
                continue

            if selection == "custom":
                value = _prompt_required_text(
                    "Enter repository root path:",
                    default=str(Path(repo).resolve()),
                )
                if value is None:
                    continue
                repo_candidate = value
            else:
                repo_candidate = selection

            candidate_path = Path(repo_candidate).expanduser()
            if not candidate_path.is_absolute():
                candidate_path = (Path.cwd() / candidate_path).resolve()
            else:
                candidate_path = candidate_path.resolve()

            if not candidate_path.exists() or not candidate_path.is_dir():
                questionary.print("Repository root must be an existing directory.", style="bold fg:red")
                continue

            repo = str(candidate_path)
            config_base_dir = candidate_path

            _cfg_repo, cfg_version = _load_config(config_base_dir)
            version_prompt_choices: list[questionary.Choice] = [
                questionary.Choice(title=f"Keep current ({version})", value="keep"),
            ]
            if cfg_version:
                version_prompt_choices.append(
                    questionary.Choice(title=f"Use {CONFIG_FILENAME} value ({cfg_version})", value="config")
                )
            version_prompt_choices.extend(
                [
                    questionary.Choice(title="Auto-detect from unknown./mismatch. files", value="detect"),
                    questionary.Choice(title="Select / enter manually…", value="manual"),
                ]
            )

            version_prompt = questionary.select(
                "Update version suffix too?",
                choices=version_prompt_choices,
                qmark="❯",
                instruction="(Enter to confirm, Esc to keep current)",
                style=MENU_STYLE,
            )
            ver_choice = _enable_escape_cancel(version_prompt).ask(kbi_msg="")
            if ver_choice == "detect":
                version = _resolve_version(repo, None, interactive=True)
            elif ver_choice == "config" and cfg_version:
                version = _resolve_version(repo, cfg_version, interactive=True)
            elif ver_choice == "manual":
                chosen = _prompt_version_suffix(repo, default=(cfg_version or version))
                if chosen is not None:
                    version = chosen

            questionary.print("Updated working directory.", style="bold fg:green")
            questionary.print(f"Config base dir: {config_base_dir}", style="fg:cyan")
            questionary.print(f"Repo root (session): {Path(repo).resolve()}", style="fg:cyan")
            questionary.print(f"Version suffix (session): {version}", style="fg:cyan")
            continue

        if action == "set_version":
            choice_prompt = questionary.select(
                "Select version suffix:",
                choices=[
                    questionary.Choice(title="Auto-detect from unknown./mismatch. files", value="detect"),
                    questionary.Choice(title="Select / enter manually…", value="manual"),
                    questionary.Choice(title="Cancel", value="cancel"),
                ],
                qmark="❯",
                instruction="(Enter to confirm, Esc to cancel)",
                style=MENU_STYLE,
            )
            ver_choice = _enable_escape_cancel(choice_prompt).ask(kbi_msg="")
            if ver_choice in (None, "cancel"):
                continue
            if ver_choice == "detect":
                version = _resolve_version(repo, None, interactive=True)
            else:
                chosen = _prompt_version_suffix(repo, default=version)
                if chosen is None:
                    continue
                version = chosen
            questionary.print(f"Version suffix updated: {version}", style="bold fg:green")
            continue


def run_tui(repo_root: str | None, version_suffix: str | None) -> int:
    _patch_shortcut_rendering()

    repo_arg = repo_root or ""
    config_base_dir = Path(repo_arg or ".").resolve()
    config_repo, config_version = _load_config(config_base_dir)
    repo = repo_arg or config_repo or get_repository_root()
    version = _resolve_version(repo, version_suffix or config_version, interactive=True)
    finder = PoPathFinder(repository_root_dir=repo, version=version)

    questionary.print(f"Working directory: {Path(repo or '.').resolve()}", style="fg:cyan")
    questionary.print(
        "\nUse ↑/↓ to move, Space to toggle (checkbox prompts), Enter to confirm.",
        style="fg:cyan",
    )

    while True:
        questionary.print("")
        questionary.print("=== sgpo TUI ===", style="bold")
        prompt = questionary.select(
            "Choose an operation:",
            choices=_menu_choices(finder),
            qmark="❯",
            instruction="(Use shortcuts / arrow keys, Esc to quit)",
            style=MENU_STYLE,
            use_shortcuts=True,
        )
        prompt = _enable_escape_cancel(prompt)
        action = prompt.ask(kbi_msg="")

        questionary.print("")

        if action is None or action == "quit":
            return 0

        if action == "import_pot":
            _interactive_import_pot(finder)
        elif action == "format_po":
            _interactive_format(finder)
        elif action == "special_sort_po":
            _interactive_special_sort(finder)
        elif action == "config":
            repo, version, config_base_dir = _interactive_config(repo, version, config_base_dir)
            finder = PoPathFinder(repository_root_dir=repo, version=version)
        elif action == "format_pot":
            _interactive_simple(_format_pot, finder)
        elif action == "import_unknown":
            _interactive_simple(_import_unknown, finder)
        elif action == "import_mismatch":
            _interactive_simple(_import_mismatch, finder)
        elif action == "delete_extracted_comments":
            _interactive_simple(_delete_extracted_comments, finder)
        elif action == "compress_msgctxt_msgid":
            _interactive_simple(_compress_msgctxt_msgid, finder)
        elif action == "ensure_colon_suffix":
            _interactive_simple(_ensure_colon_suffix_po, finder)
        elif action == "strip_msgctxt_placeholders":
            _interactive_simple(_strip_msgctxt_placeholders_po, finder)
        elif action == "propagate_ellipsis_translation":
            _interactive_simple(_propagate_ellipsis_translation_po, finder)
        elif action == "cleanup_obsolete_empty_msgstr":
            _interactive_simple(_cleanup_obsolete_empty_msgstr_po, finder)
        elif action == "export_placeholder_msgids":
            _interactive_placeholder_msgids(finder)
        elif action == "extract_added_entries":
            _interactive_extract_added_entries(finder)

    return 0


def run_cli(args: argparse.Namespace) -> int:
    repo_arg = args.repo_root or ""
    config_repo, config_version = _load_config(Path(repo_arg or ".").resolve())
    repo = repo_arg or config_repo or get_repository_root()
    version = _resolve_version(repo, args.version or config_version, interactive=not args.non_interactive)
    finder = PoPathFinder(repository_root_dir=repo, version=version)

    if args.command == "import-pot":
        try:
            po_paths = _targets_from_args(finder, args.locales)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 2
        return _run_cli_lines(_import_pot(finder, po_paths))

    if args.command == "init":
        return _init_config(repo, args.version)

    if args.command == "format":
        try:
            po_paths = _targets_from_args(finder, args.locales)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 2
        return _run_cli_lines(_format_locales(finder, po_paths))

    if args.command == "special-sort":
        try:
            po_paths = _targets_from_args(finder, args.locales)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 2
        return _run_cli_lines(_special_sort_locales(finder, po_paths))

    if args.command == "format-pot":
        return _run_cli_lines(_format_pot(finder))

    if args.command == "import-unknown":
        return _run_cli_lines(_import_unknown(finder))

    if args.command == "import-mismatch":
        return _run_cli_lines(_import_mismatch(finder))

    if args.command == "delete-extracted-comments":
        return _run_cli_lines(_delete_extracted_comments(finder))

    return 1


def _targets_from_args(finder: PoPathFinder, locales: Sequence[str] | None) -> list[str]:
    if not locales:
        return [value for value, _ in _po_choices(finder)]

    candidates = {Path(path).stem: path for path, _ in _po_choices(finder)}
    missing = [locale for locale in locales if locale not in candidates]
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"locale not found: {missing_text}")

    return [candidates[locale] for locale in locales]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sgpo", add_help=True)
    parser.add_argument("--repo-root", default="", help="Repository root (autodetect when omitted)")
    parser.add_argument(
        "--version",
        default=None,
        help="Suffix for unknown./mismatch. files (e.g. 24_1). Auto-detect when omitted.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run without interactive prompts (chooses first detected version/candidate)",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init", help="Generate sgpo configuration file (sgpo.toml)")
    sub = subparsers.add_parser("import-pot", help="Apply messages.pot changes into locale .po files (format + save)")
    sub.add_argument("--locales", nargs="*", help="Target locales (e.g. ja_JP zh_CN)")

    sub = subparsers.add_parser("format", help="Format locale .po files")
    sub.add_argument("--locales", nargs="*", help="Target locales (e.g. ja_JP zh_CN)")

    sub = subparsers.add_parser("special-sort", help="Special sort locale .po files (move untranslated entries to bottom)")
    sub.add_argument("--locales", nargs="*", help="Target locales (e.g. ja_JP zh_CN)")

    subparsers.add_parser("format-pot", help="Format messages.pot")
    subparsers.add_parser("import-unknown", help="Import unknown.* into messages.pot (format + save)")
    subparsers.add_parser("import-mismatch", help="Import mismatch.* into messages.pot (sort + save)")
    subparsers.add_parser("delete-extracted-comments", help="Remove extracted comments from messages.pot")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if args.command is None:
        return run_tui(args.repo_root, args.version)
    return run_cli(args)


if __name__ == "__main__":
    raise SystemExit(main())
