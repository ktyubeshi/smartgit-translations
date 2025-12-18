from __future__ import annotations

import argparse
import sys
from pathlib import Path
import re
import textwrap
import tomllib
from typing import Iterable, Iterator, Sequence
import os

import questionary
from questionary import Style, Choice
from prompt_toolkit.keys import Keys
import sgpo
from extract_added_po_entries import (
    _build_added_po,
    _load_po_from_commit,
    _resolve_target_path,
    _sanitize_label,
)
from path_finder import PoPathFinder, get_repository_root


def _patch_shortcut_rendering() -> None:
    """Hide Questionary's shortcut prefix defensively."""

    if not hasattr(Choice, "get_shortcut_title"):
        return

    original = Choice.get_shortcut_title

    def _no_shortcut_prefix(self: Choice) -> str:  # type: ignore[override]
        return ""

    try:
        Choice.get_shortcut_title = _no_shortcut_prefix  # type: ignore[assignment]
    except Exception:  # pragma: no cover - extremely defensive
        Choice.get_shortcut_title = original  # type: ignore[assignment]


def _enable_escape_cancel(question: questionary.Question) -> questionary.Question:
    """Allow ESC to cancel the prompt (matching Ctrl+C behavior)."""

    kb = getattr(question.application, "key_bindings", None)
    if kb is not None and hasattr(kb, "add"):

        @kb.add(Keys.Escape, eager=True)
        def _(event):
            event.app.exit(exception=KeyboardInterrupt, style="class:aborting")

    return question


MENU_STYLE = Style(
    [
        ("qmark", "fg:#00d1b2 bold"),
        ("question", "bold"),
        ("answer", "fg:#00d1b2 bold"),
        ("pointer", "fg:#00d1b2"),
        ("highlighted", "fg:#00d1b2 bold"),
        ("selected", "fg:#00d1b2"),
        ("separator", "fg:#888888"),
        ("instruction", "fg:#aaaaaa italic"),
        ("text", ""),
    ]
)


CONFIG_FILENAME = "sgpo.toml"
_VERSION_PATTERN = re.compile(r"^(unknown|mismatch)\.(\d+_\d+)$")
_SMARTGIT_PROP_NAME = "smartgit.properties"
_SMARTGIT_PROP_KEY_REPO = "smartgit.debug.i18n.development"
_PLACEHOLDER_PATTERN = re.compile(r"\$[0-9]+")


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
    seen_paths: set[Path] = set()
    for idx, base in enumerate(candidates):
        if base in seen_paths:
            continue
        seen_paths.add(base)
        if not base.exists():
            continue
        for path in base.glob(f"**/{_SMARTGIT_PROP_NAME}"):
            if path in seen_paths:
                continue
            seen_paths.add(path)
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


def _po_choices(finder: PoPathFinder) -> list[tuple[str, str]]:
    """Return (value, label) tuples for locale selection and summaries."""

    po_files = sorted(finder.get_po_files(translation_file_only=True))
    return [(po_file, f"{Path(po_file).stem}  ({po_file})") for po_file in po_files]


def _import_pot(finder: PoPathFinder, po_paths: Iterable[str]) -> Iterator[str]:
    pot_path = finder.get_pot_file()
    pot = sgpo.pofile(pot_path)
    yield f"POT: {pot_path}"

    totals = {"added": 0, "modified": 0, "obsolete": 0}
    processed = 0

    for po_path in po_paths:
        po = sgpo.pofile(po_path)
        result = po.import_pot(pot)
        po.format()
        po.save(po_path)
        processed += 1
        totals["added"] += result["added"]
        totals["modified"] += result["modified"]
        totals["obsolete"] += result["obsolete"]
        yield (
            f" po: {po_path}\n"
            f"   added={result['added']}, modified={result['modified']}, obsolete={result['obsolete']}"
        )

    yield (
        "Summary: {count} files | added={added}, modified={modified}, obsolete={obsolete}".format(
            count=processed,
            added=totals["added"],
            modified=totals["modified"],
            obsolete=totals["obsolete"],
        )
    )


def _format_locales(finder: PoPathFinder, po_paths: Iterable[str]) -> Iterator[str]:
    for po_path in po_paths:
        po = sgpo.pofile(po_path)
        po.format()
        po.save(po_path)
        yield f"formatted: {po_path}"


def _format_pot(finder: PoPathFinder) -> Iterator[str]:
    pot_path = finder.get_pot_file()
    pot = sgpo.pofile(pot_path)
    pot.format()
    pot.save(pot_path)
    yield f"formatted: {pot_path}"


def _is_untranslated(entry) -> bool:
    """Return True if entry has no translation (singular or plural)."""

    if getattr(entry, "obsolete", False):
        return False

    if hasattr(entry, "msgstr_plural") and entry.msgstr_plural:
        return all(not text.strip() for text in entry.msgstr_plural.values())

    return not bool(getattr(entry, "msgstr", "").strip())


def _special_sort_locales(finder: PoPathFinder, po_paths: Iterable[str]) -> Iterator[str]:
    """Sort locales while moving untranslated entries to the end."""

    for po_path in po_paths:
        po = sgpo.pofile(po_path)
        po.sort(key=lambda entry: (_is_untranslated(entry), po._po_entry_to_sort_key(entry)))  # type: ignore[attr-defined]  # noqa: SLF001
        po.save(po_path)
        yield f"special-sorted: {po_path} (untranslated entries moved to bottom)"


def _ensure_file_exists(path: str, hint: str) -> None:
    if not Path(path).exists():
        raise FileNotFoundError(f"[missing] {path}\n{hint}")


def _import_unknown(finder: PoPathFinder) -> Iterator[str]:
    pot_path = finder.get_pot_file()
    unknown_path = finder.get_unknown_file()
    _ensure_file_exists(
        unknown_path,
        (
            f"unknown.* file not found (suffix: {finder.version}). Adjust --version or use "
            "--version to specify the suffix explicitly."
        ),
    )
    pot = sgpo.pofile(pot_path)
    unknown = sgpo.pofile(unknown_path)
    result = pot.import_unknown(unknown)
    pot.format()
    pot.save(pot_path)
    yield f"    pot: {pot_path}"
    yield f"unknown: {unknown_path}"
    yield f"Summary: added {result['added']} entries from unknown file."


def _import_mismatch(finder: PoPathFinder) -> Iterator[str]:
    pot_path = finder.get_pot_file()
    mismatch_path = finder.get_mismatch_file()
    _ensure_file_exists(
        mismatch_path,
        (
            f"mismatch.* file not found (suffix: {finder.version}). Adjust --version or use "
            "--version to specify the suffix explicitly."
        ),
    )
    pot = sgpo.pofile(pot_path)
    mismatch = sgpo.pofile(mismatch_path)
    result = pot.import_mismatch(mismatch)
    pot.sort()
    pot.save(pot_path)
    yield f"     pot: {pot_path}"
    yield f"mismatch: {mismatch_path}"
    yield "Summary: added {added} entries, modified {modified} entries.".format(
        added=result["added"],
        modified=result["modified"],
    )


def _delete_extracted_comments(finder: PoPathFinder) -> Iterator[str]:
    pot_path = finder.get_pot_file()
    pot = sgpo.pofile(pot_path)
    removed = pot.delete_extracted_comments()
    pot.save(pot_path)
    yield f"    pot: {pot_path}"
    yield f"Removed extracted comments from {removed} entries."


def _compress_msgctxt(po) -> int:
    changed = 0
    for entry in po:
        if getattr(entry, "obsolete", False):
            continue
        if entry.msgid == "":
            continue
        msgctxt = getattr(entry, "msgctxt", None)
        if not msgctxt:
            continue

        pattern = '"' + entry.msgid + '"'  # polib でアンエスケープ済み前提
        if msgctxt.endswith(pattern):
            entry.msgctxt = msgctxt[: -len(pattern)] + ":"
            changed += 1
    return changed


def _compress_msgctxt_msgid(finder: PoPathFinder) -> Iterator[str]:
    pot_path = finder.get_pot_file()
    po_files = finder.get_po_files(translation_file_only=True)

    targets: list[str] = []
    if pot_path:
        targets.append(pot_path)  # messages.pot も処理対象に含める
    targets.extend(po_files)

    total = 0
    for po_path in targets:
        po = sgpo.pofile(po_path)
        changed = _compress_msgctxt(po)
        if changed:
            po.save(po_path)
        yield f"{po_path}: compressed {changed} entries."
        total += changed
    yield f"Total compressed: {total}"


def _ensure_colon(po) -> int:
    changed = 0
    for entry in po:
        if getattr(entry, "obsolete", False):
            continue
        if entry.msgid == "":
            continue
        msgctxt = getattr(entry, "msgctxt", None)
        if not msgctxt:
            continue
        if not msgctxt.endswith(":"):
            entry.msgctxt = msgctxt + ":"
            changed += 1
    return changed


def _ensure_colon_suffix_po(finder: PoPathFinder) -> Iterator[str]:
    po_files = finder.get_po_files(translation_file_only=True)

    total = 0
    for po_path in po_files:
        po = sgpo.pofile(po_path)
        changed = _ensure_colon(po)
        if changed:
            po.save(po_path)
        yield f"{po_path}: appended colon to {changed} entries."
        total += changed
    yield f"Total changed: {total}"


def _strip_msgctxt_placeholders(po) -> int:
    changed = 0
    for entry in po:
        if getattr(entry, "obsolete", False):
            continue
        if entry.msgid == "":
            continue
        msgctxt = getattr(entry, "msgctxt", None)
        if not msgctxt:
            continue

        new_msgctxt = re.sub(r"%\d+$", "", msgctxt)
        if new_msgctxt != msgctxt:
            entry.msgctxt = new_msgctxt
            changed += 1
    return changed


def _strip_msgctxt_placeholders_po(finder: PoPathFinder) -> Iterator[str]:
    pot_path = finder.get_pot_file()
    po_files = finder.get_po_files(translation_file_only=True)

    targets: list[str] = []
    if pot_path:
        targets.append(pot_path)
    targets.extend(po_files)

    total = 0
    for po_path in targets:
        po = sgpo.pofile(po_path)
        changed = _strip_msgctxt_placeholders(po)
        if changed:
            po.save(po_path)
        yield f"{po_path}: stripped placeholders from {changed} entries."
        total += changed
    yield f"Total changed: {total}"


def _normalize_ellipsis(text: str) -> str:
    """Treat '...', '…', and '\\u2026' (literal) as equivalent."""

    normalized = text.replace("…", "...")
    normalized = normalized.replace("\\u2026", "...")
    return normalized


def _is_translated(entry) -> bool:
    if getattr(entry, "obsolete", False):
        return False
    if hasattr(entry, "msgstr_plural") and entry.msgstr_plural:
        return any(val.strip() for val in entry.msgstr_plural.values())
    return bool(getattr(entry, "msgstr", "").strip())


def _copy_translation(source, target) -> None:
    """Copy translation from source to target entry."""

    if hasattr(source, "msgstr_plural") and source.msgstr_plural:
        # Copy plural forms if present.
        target.msgstr_plural = {k: v for k, v in source.msgstr_plural.items()}
        target.msgstr = ""
    else:
        target.msgstr = getattr(source, "msgstr", "")


def _propagate_ellipsis_translation(po) -> int:
    """Copy translations between ellipsis variants when one is translated and the other is not."""

    groups: dict[tuple[str, str], list] = {}
    for entry in po:
        if getattr(entry, "obsolete", False):
            continue
        if entry.msgid == "":
            continue
        msgctxt = getattr(entry, "msgctxt", "") or ""
        key = (msgctxt, _normalize_ellipsis(entry.msgid))
        groups.setdefault(key, []).append(entry)

    applied = 0
    for entries in groups.values():
        translated = [e for e in entries if _is_translated(e)]
        if not translated:
            continue
        source = translated[0]
        for target in entries:
            if target is source or _is_translated(target):
                continue
            _copy_translation(source, target)
            applied += 1
    return applied


def _propagate_ellipsis_translation_po(finder: PoPathFinder) -> Iterator[str]:
    po_files = finder.get_po_files(translation_file_only=True)

    total = 0
    for po_path in po_files:
        po = sgpo.pofile(po_path)
        applied = _propagate_ellipsis_translation(po)
        if applied:
            po.save(po_path)
        yield f"{po_path}: propagated translations to {applied} entries."
        total += applied
    yield f"Total propagated: {total}"


def _has_msgstr_text(entry) -> bool:
    plurals = getattr(entry, "msgstr_plural", None)
    if plurals:
        return any((val or "").strip() for val in plurals.values())
    msgstr = getattr(entry, "msgstr", "") or ""
    return bool(msgstr.strip())


def _cleanup_obsolete_empty_msgstr(po) -> int:
    removed = 0
    kept_entries = []
    for entry in po:
        if getattr(entry, "obsolete", False) and not _has_msgstr_text(entry):
            removed += 1
            continue
        kept_entries.append(entry)
    if removed:
        po._po[:] = kept_entries  # type: ignore[attr-defined]  # noqa: SLF001
    return removed


def _cleanup_obsolete_empty_msgstr_po(finder: PoPathFinder) -> Iterator[str]:
    po_files = finder.get_po_files(translation_file_only=True)

    total = 0
    for po_path in po_files:
        po = sgpo.pofile(po_path)
        removed = _cleanup_obsolete_empty_msgstr(po)
        if removed:
            po.save(po_path)
        yield f"{po_path}: removed {removed} obsolete entries with empty msgstr."
        total += removed
    yield f"Total removed: {total}"


def _placeholder_entries(po) -> list:
    entries: list = []
    for entry in po:
        if getattr(entry, "obsolete", False):
            continue
        msgid = getattr(entry, "msgid", "")
        if not msgid:
            continue
        if _PLACEHOLDER_PATTERN.search(msgid):
            entries.append(entry)
    return entries


def _export_placeholder_msgids(repo_root: Path, target_paths: list[str], output_dir: Path) -> Iterator[str]:
    resolved_targets: list[Path] = []
    for target in target_paths:
        path = Path(target)
        if not path.is_absolute():
            path = (repo_root / path).resolve()
        resolved_targets.append(path)

    created_output_dir = False
    total_entries = 0
    written_files = 0

    for po_path in resolved_targets:
        if not po_path.exists():
            yield f"[missing] {po_path}"
            continue

        po = sgpo.pofile(str(po_path))
        matches = _placeholder_entries(po)
        if not matches:
            yield f"{po_path}: 0 entries with $n placeholders (skipped)"
            continue

        if not created_output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            created_output_dir = True

        subset = sgpo.SGPoFile()
        subset.metadata = po.metadata
        for entry in matches:
            subset.append(entry)
        subset.format()

        target_path = output_dir / f"{Path(po_path).stem}-placeholders.po"
        subset.save(str(target_path))

        yield f"{po_path}: {len(matches)} entries -> {target_path}"
        total_entries += len(matches)
        written_files += 1

    if written_files == 0:
        yield "No msgid entries with $n placeholders were found."
    else:
        yield f"Total entries: {total_entries} across {written_files} file(s)."


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


def _select_po_files(finder: PoPathFinder, all_label: str) -> list[str] | None:
    # Defensive guard: never include messages.pot or other non-.po files.
    choices = [(path, label) for path, label in _po_choices(finder) if Path(path).suffix == ".po"]
    if not choices:
        questionary.print("No <locale>.po files were found under the po directory.", style="bold fg:red")
        return None

    while True:
        action_prompt = questionary.select(
            "Locale selection:",
            choices=[
                questionary.Choice(title=all_label, value="all"),
                questionary.Choice(title="Select locales interactively…", value="interactive"),
                questionary.Choice(title="Cancel", value="cancel"),
            ],
            qmark="❯",
            instruction="(Enter to run, Esc to cancel)",
            style=MENU_STYLE,
        )
        action = _enable_escape_cancel(action_prompt).ask(kbi_msg="")

        if action is None or action == "cancel":
            return None
        if action == "all":
            return [value for value, _ in choices]
        if action == "interactive":
            q_choices = [
                questionary.Choice(title=f"    ↳ {label}", value=value) for value, label in choices
            ]
            prompt = questionary.checkbox(
                "Select locales to process (Space to toggle, Enter to confirm, Esc to cancel):",
                choices=q_choices,
                qmark="❯",
                instruction="",
                style=MENU_STYLE,
            )
            selected = _enable_escape_cancel(prompt).ask(kbi_msg="")

            if selected is None:
                return None

            ordered = [value for value, _ in choices if value in selected]
            return ordered


def _select_po_and_pot_files(finder: PoPathFinder) -> list[str] | None:
    po_dir = Path(finder.root_dir) / "po"
    files: list[str] = []
    if po_dir.exists():
        files = [
            str(path)
            for path in sorted(
                list(po_dir.rglob("*.po")) + list(po_dir.rglob("*.pot")),
                key=lambda p: p.as_posix(),
            )
            if path.is_file()
        ]
    if not files:
        questionary.print("No .po/.pot files were found under the po directory.", style="bold fg:red")
        return None
    choices: list[Choice] = [
        questionary.Choice(title=str(path), value=str(path)) for path in files
    ]

    while True:
        action_prompt = questionary.select(
            "Select files to process:",
            choices=[
                questionary.Choice(title="All (messages.pot + all locales)", value="all"),
                questionary.Choice(title="Select interactively…", value="interactive"),
                questionary.Choice(title="Cancel", value="cancel"),
            ],
            qmark="❯",
            instruction="(Enter to run, Esc to cancel)",
            style=MENU_STYLE,
        )
        action = _enable_escape_cancel(action_prompt).ask(kbi_msg="")
        if action in (None, "cancel"):
            return None
        if action == "all":
            return [c.value for c in choices]

        q_choices = [
            questionary.Choice(title=f"    ↳ {c.title}", value=c.value) for c in choices
        ]
        prompt = questionary.checkbox(
            "Select files (Space to toggle, Enter to confirm, Esc to cancel):",
            choices=q_choices,
            qmark="❯",
            instruction="",
            style=MENU_STYLE,
        )
        selected = _enable_escape_cancel(prompt).ask(kbi_msg="")
        if selected is None:
            return None
        ordered = [c.value for c in choices if c.value in selected]
        return ordered


def _po_target_selection(finder: PoPathFinder) -> str | None:
    pot_path = finder.get_pot_file()
    choices: list[Choice] = [
        questionary.Choice(title=f"messages.pot ({pot_path})", value=pot_path),
    ]
    choices.extend(
        questionary.Choice(title=label, value=path)
        for path, label in _po_choices(finder)
    )
    choices.append(questionary.Choice(title="Enter custom path…", value="custom"))
    choices.append(questionary.Choice(title="Cancel", value=None))

    prompt = questionary.select(
        "Select target PO/POT file:",
        choices=choices,
        qmark="❯",
        instruction="(Enter to confirm, Esc to cancel)",
        style=MENU_STYLE,
    )
    selection = _enable_escape_cancel(prompt).ask(kbi_msg="")
    if selection == "custom":
        custom_prompt = questionary.text(
            "Enter PO/POT path (relative to repo root or absolute):",
            default=pot_path,
            qmark="❯",
            style=MENU_STYLE,
        )
        return _enable_escape_cancel(custom_prompt).ask(kbi_msg="")
    return selection


def _prompt_required_text(message: str, default: str = "") -> str | None:
    while True:
        prompt = questionary.text(
            message,
            default=default,
            qmark="❯",
            style=MENU_STYLE,
        )
        value = _enable_escape_cancel(prompt).ask(kbi_msg="")
        if value is None:
            return None
        value = value.strip()
        if value:
            return value
        questionary.print("Please enter a value or press Esc to cancel.", style="bold fg:yellow")


def _default_output_path(target_abs: Path, repo_root: Path, old_commit: str, new_commit: str) -> Path:
    output_name = (
        f"added-{target_abs.stem}-"
        f"{_sanitize_label(old_commit[:12])}-"
        f"{_sanitize_label(new_commit[:12])}.po"
    )
    return repo_root / "po" / output_name


def _extract_added_entries(
    repo_root: Path,
    po_path: str,
    old_commit: str,
    new_commit: str,
    output_path: Path | None,
) -> Iterator[str]:
    try:
        target_abs, rel_path = _resolve_target_path(po_path, repo_root)
        old_po = _load_po_from_commit(old_commit, rel_path, repo_root)
        new_po = _load_po_from_commit(new_commit, rel_path, repo_root)
    except SystemExit as exc:
        raise RuntimeError(str(exc)) from exc

    added_po, added_count = _build_added_po(old_po, new_po)

    if output_path is None:
        resolved_output = _default_output_path(target_abs, repo_root, old_commit, new_commit)
    elif output_path.is_absolute():
        resolved_output = output_path
    else:
        resolved_output = (repo_root / output_path).resolve()

    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    added_po.save(str(resolved_output))

    yield f"Target file:   {rel_path}"
    yield f"Old commit:    {old_commit}"
    yield f"New commit:    {new_commit}"
    yield f"Added entries: {added_count}"
    yield f"Output:        {resolved_output}"


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

    try:
        target_abs, _ = _resolve_target_path(po_path, repo_root)
    except SystemExit as exc:
        questionary.print(str(exc), style="bold fg:red")
        return

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


def _menu_choices(finder: PoPathFinder) -> list:
    sections = [
        (
            "Locale workflows",
            [
                ("Format locale .po files (format)", "format_po"),
                ("Import POT into locale .po files (import-pot)", "import_pot"),
                ("Special sort locale .po files (special-sort)", "special_sort_po"),
            ],
        ),
        (
            "messages.pot workflows",
            [
                ("Format messages.pot (format-pot)", "format_pot"),
                ("Import unknown.* into messages.pot (import-unknown)", "import_unknown"),
                ("Import mismatch.* into messages.pot (import-mismatch)", "import_mismatch"),
                ("Delete extracted comments from messages.pot (delete-extracted-comments)", "delete_extracted_comments"),
            ],
        ),
        (
            "Msgctxt utilities",
            [
                ("Compress msgctxt suffix (strip duplicated msgid)", "compress_msgctxt_msgid"),
                ("Append missing ':' to msgctxt", "ensure_colon_suffix"),
                ("Strip trailing %n count suffix from msgctxt", "strip_msgctxt_placeholders"),
                ("Propagate ellipsis translations (… vs ...)", "propagate_ellipsis_translation"),
            ],
        ),
        (
            "Cleanup",
            [
                ("Remove obsolete entries with empty msgstr", "cleanup_obsolete_empty_msgstr"),
            ],
        ),
        (
            "Git diff workflows",
            [
                ("Extract added PO/POT entries between two commits", "extract_added_entries"),
            ],
        ),
        (
            "Reports",
            [
                ("Export msgid entries containing $n placeholders to .po files", "export_placeholder_msgids"),
            ],
        ),
        (
            "Misc",
            [
                ("Quit", "quit"),
            ],
        ),
    ]

    choices: list = []
    shortcut = 1
    for section, entries in sections:
        choices.append(questionary.Separator(f" {section}"))
        for title, value in entries:
            shortcut_char: str | None = str(shortcut) if shortcut <= 9 else None
            label = f"[{shortcut_char}] {title}" if shortcut_char else title
            choices.append(
                questionary.Choice(
                    title=f"    ↳ {label}",
                    value=value,
                    shortcut_key=shortcut_char,
                )
            )
            shortcut += 1
    return choices


def _print_completion() -> None:
    questionary.print("\n--- Completed ---\n", style="fg:green")


def _run_with_feedback(func):
    try:
        lines = func()
        for line in lines:
            questionary.print(line)
    except FileNotFoundError as exc:
        questionary.print(str(exc), style="bold fg:red")
        return
    except Exception as exc:  # pragma: no cover - defensive
        questionary.print(f"[error] {exc}", style="bold fg:red")
        return

    _print_completion()


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


def run_tui(repo_root: str | None, version_suffix: str | None) -> int:
    _patch_shortcut_rendering()

    repo_arg = repo_root or ""
    config_repo, config_version = _load_config(Path(repo_arg or ".").resolve())
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
