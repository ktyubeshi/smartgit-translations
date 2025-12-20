from __future__ import annotations

from pathlib import Path
from typing import Iterable, cast

import questionary
from questionary import Style, Choice
from prompt_toolkit.keys import Keys

from path_finder import PoPathFinder

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


def _po_choices(finder: PoPathFinder) -> list[tuple[str, str]]:
    """Return (value, label) tuples for locale selection and summaries."""

    po_files = sorted(finder.get_po_files(translation_file_only=True))
    return [(po_file, f"{Path(po_file).stem}  ({po_file})") for po_file in po_files]


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
            return [str(c.value) for c in choices]

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
        selected_set = set(cast(list[str], selected))
        ordered = [str(c.value) for c in choices if c.value in selected_set]
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


def _interactive_simple(action, finder: PoPathFinder) -> None:
    _run_with_feedback(lambda: action(finder))


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
            "Config",
            [
                ("Configure sgpo.toml / repo root / version", "config"),
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
