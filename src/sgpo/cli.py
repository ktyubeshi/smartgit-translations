from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Sequence

import questionary
from questionary import Style, Choice
from prompt_toolkit.keys import Keys
import sgpo
from path_finder import PoPathFinder


def _patch_shortcut_rendering() -> None:
    def _no_shortcut_prefix(self: Choice) -> str:  # type: ignore[override]
        return ""

    Choice.get_shortcut_title = _no_shortcut_prefix  # type: ignore[assignment]


_patch_shortcut_rendering()


def _enable_escape_cancel(question: questionary.Question) -> questionary.Question:
    """Allow ESC to cancel the prompt (matching Ctrl+C behavior)."""

    kb = getattr(question.application, "key_bindings", None)
    if kb is not None:

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


def _po_choices(finder: PoPathFinder) -> list[tuple[str, str]]:
    """Return (value, label) tuples for locale selection and summaries."""

    po_files = sorted(finder.get_po_files(translation_file_only=True))
    return [(po_file, f"{Path(po_file).stem}  ({po_file})") for po_file in po_files]


def _import_pot(finder: PoPathFinder, po_paths: Iterable[str]) -> list[str]:
    pot_path = finder.get_pot_file()
    pot = sgpo.pofile(pot_path)
    summary = [f"POT: {pot_path}"]

    for po_path in po_paths:
        po = sgpo.pofile(po_path)
        result = po.import_pot(pot)
        po.format()
        po.save(po_path)
        summary.append(
            f" po: {po_path}\n"
            f"   added={result['added']}, modified={result['modified']}, obsolete={result['obsolete']}"
        )

    return summary


def _format_locales(finder: PoPathFinder, po_paths: Iterable[str]) -> list[str]:
    output: list[str] = []
    for po_path in po_paths:
        po = sgpo.pofile(po_path)
        po.format()
        po.save(po_path)
        output.append(f"formatted: {po_path}")
    return output


def _import_unknown(finder: PoPathFinder) -> list[str]:
    pot_path = finder.get_pot_file()
    unknown_path = finder.get_unknown_file()
    pot = sgpo.pofile(pot_path)
    unknown = sgpo.pofile(unknown_path)
    result = pot.import_unknown(unknown)
    pot.format()
    pot.save(pot_path)
    return [
        f"    pot: {pot_path}",
        f"unknown: {unknown_path}",
        f"Summary: added {result['added']} entries from unknown file.",
    ]


def _import_mismatch(finder: PoPathFinder) -> list[str]:
    pot_path = finder.get_pot_file()
    mismatch_path = finder.get_mismatch_file()
    pot = sgpo.pofile(pot_path)
    mismatch = sgpo.pofile(mismatch_path)
    result = pot.import_mismatch(mismatch)
    pot.sort()
    pot.save(pot_path)
    return [
        f"     pot: {pot_path}",
        f"mismatch: {mismatch_path}",
        "Summary: added {added} entries, modified {modified} entries.".format(
            added=result["added"],
            modified=result["modified"],
        ),
    ]


def _delete_extracted_comments(finder: PoPathFinder) -> list[str]:
    pot_path = finder.get_pot_file()
    pot = sgpo.pofile(pot_path)
    removed = pot.delete_extracted_comments()
    pot.save(pot_path)
    return [
        f"    pot: {pot_path}",
        f"Removed extracted comments from {removed} entries.",
    ]


def _select_po_files(finder: PoPathFinder) -> list[str] | None:
    choices = _po_choices(finder)
    if not choices:
        questionary.print("No <locale>.po files were found under the po directory.", style="bold fg:red")
        return None

    questionary_choices = [
        questionary.Choice(title=f"    ↳ {label}", value=value) for value, label in choices
    ]
    prompt = questionary.checkbox(
        "Select locales to process (Space to toggle, Enter to confirm, Esc to cancel):",
        choices=questionary_choices,
        qmark="❯",
        instruction="",
        style=MENU_STYLE,
    )
    prompt = _enable_escape_cancel(prompt)
    selected = prompt.ask(kbi_msg="")
    return selected


def _menu_choices(finder: PoPathFinder) -> list:
    sections = [
        (
            "Locale workflows",
            [
                ("Import POT into locale .po files (import_pot)", "import_pot"),
                ("Format locale .po files (format)", "format_po"),
            ],
        ),
        (
            "messages.pot workflows",
            [
                ("Import unknown.* into messages.pot (import_unknown)", "import_unknown"),
                ("Import mismatch.* into messages.pot (import_mismatch)", "import_mismatch"),
                ("Delete extracted comments from messages.pot", "delete_extracted_comments"),
            ],
        ),
        (
            "Misc",
            [
                (
                    f"Change unknown/mismatch suffix (current: {finder.version})",
                    "change_version",
                ),
                ("Quit", "quit"),
            ],
        ),
    ]

    choices: list = []
    shortcut = 1
    for section, entries in sections:
        choices.append(questionary.Separator(f" {section}"))
        for title, value in entries:
            label = f"[{shortcut}] {title}"
            choices.append(
                questionary.Choice(
                    title=f"    ↳ {label}",
                    value=value,
                    shortcut_key=str(shortcut),
                )
            )
            shortcut += 1
    return choices


def _ask_version(default: str = "24_1") -> str:
    value = questionary.text(
        "Enter the suffix for unknown./mismatch. files",
        default=default,
        qmark="❯",
        style=MENU_STYLE,
    ).ask()
    return value or default


def _render_lines(lines: Iterable[str]) -> None:
    for line in lines:
        questionary.print(line)


def _print_completion() -> None:
    questionary.print("\n--- Completed ---\n", style="fg:green")


def _run_with_feedback(func):
    try:
        lines = list(func())
    except FileNotFoundError as exc:
        questionary.print(str(exc), style="bold fg:red")
        return
    except Exception as exc:  # pragma: no cover - defensive
        questionary.print(f"[error] {exc}", style="bold fg:red")
        return

    _render_lines(lines)
    _print_completion()


def _interactive_import_pot(finder: PoPathFinder) -> None:
    while True:
        targets = _select_po_files(finder)
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
        targets = _select_po_files(finder)
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


def _interactive_simple(action, finder: PoPathFinder) -> None:
    _run_with_feedback(lambda: action(finder))


def run_tui(repo_root: str | None, version_suffix: str | None) -> int:
    finder = PoPathFinder(repository_root_dir=repo_root or "", version=version_suffix or "24_1")

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

        if action == "change_version":
            finder.version = _ask_version(finder.version)
            continue

        if action == "import_pot":
            _interactive_import_pot(finder)
        elif action == "format_po":
            _interactive_format(finder)
        elif action == "import_unknown":
            _interactive_simple(_import_unknown, finder)
        elif action == "import_mismatch":
            _interactive_simple(_import_mismatch, finder)
        elif action == "delete_extracted_comments":
            _interactive_simple(_delete_extracted_comments, finder)

    return 0


def run_cli(args: argparse.Namespace) -> int:
    finder = PoPathFinder(repository_root_dir=args.repo_root or "", version=args.version)

    if args.command == "import-pot":
        po_paths = _targets_from_args(finder, args.locales)
        for line in _import_pot(finder, po_paths):
            print(line)
        return 0

    if args.command == "format":
        po_paths = _targets_from_args(finder, args.locales)
        for line in _format_locales(finder, po_paths):
            print(line)
        return 0

    if args.command == "import-unknown":
        for line in _import_unknown(finder):
            print(line)
        return 0

    if args.command == "import-mismatch":
        for line in _import_mismatch(finder):
            print(line)
        return 0

    if args.command == "delete-extracted-comments":
        for line in _delete_extracted_comments(finder):
            print(line)
        return 0

    return 1


def _targets_from_args(finder: PoPathFinder, locales: Sequence[str] | None) -> list[str]:
    if not locales:
        return [value for value, _ in _po_choices(finder)]

    candidates = {Path(path).stem: path for path, _ in _po_choices(finder)}
    missing = [locale for locale in locales if locale not in candidates]
    if missing:
        missing_text = ", ".join(missing)
        raise SystemExit(f"locale not found: {missing_text}")

    return [candidates[locale] for locale in locales]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sgpo", add_help=True)
    parser.add_argument("--repo-root", default="", help="Repository root (autodetect when omitted)")
    parser.add_argument("--version", default="24_1", help="Suffix for unknown./mismatch. files (e.g. 24_1)")
    subparsers = parser.add_subparsers(dest="command")

    sub = subparsers.add_parser("import-pot", help="Apply messages.pot changes into locale .po files (format + save)")
    sub.add_argument("--locales", nargs="*", help="Target locales (e.g. ja_JP zh_CN)")

    sub = subparsers.add_parser("format", help="Format locale .po files")
    sub.add_argument("--locales", nargs="*", help="Target locales (e.g. ja_JP zh_CN)")

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
