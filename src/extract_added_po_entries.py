"""
Extract only the PO/POT entries that were added between two commits and write
them into a standalone PO file.

Examples:
    python extract_added_po_entries.py <old_commit> <new_commit> --po-path po/messages.pot
    python extract_added_po_entries.py <old_commit> <new_commit> --po-path po/ja_JP.po -o /tmp/added.po
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import sgpo
from sgpo import Key_tuple
from sgpo_common.sgpo_common import get_repository_root


def _sanitize_label(label: str) -> str:
    """Make a commit-ish safe for use in file names."""
    sanitized = ''.join(ch if (ch.isalnum() or ch in ('-', '_')) else '-' for ch in label)
    sanitized = sanitized.strip('-')
    return sanitized or 'unknown'


def _resolve_target_path(po_path: str, repo_root: Path) -> tuple[Path, str]:
    """Return the absolute path and repo-relative path for git show."""
    target_abs = Path(po_path)
    if not target_abs.is_absolute():
        target_abs = (repo_root / target_abs).resolve()
    try:
        rel = target_abs.relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise SystemExit(
            f"PO/POT path must live inside the repository root: {target_abs}"
        ) from exc
    return target_abs, rel


def _load_po_from_commit(commit: str, rel_path: str, repo_root: Path) -> sgpo.SGPoFile:
    """Read a PO/POT from git show output."""
    cmd = ["git", "-C", str(repo_root), "show", f"{commit}:{rel_path}"]
    try:
        content = subprocess.check_output(cmd, encoding="utf-8")
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"git show {commit}:{rel_path} failed: {exc}") from exc
    return sgpo.pofile_from_text(content)


def _build_added_po(old_po: sgpo.SGPoFile, new_po: sgpo.SGPoFile) -> tuple[sgpo.SGPoFile, int]:
    """Return a PO containing only entries present in new_po but not old_po."""
    old_keys = set(old_po.get_key_list())
    added_po = sgpo.SGPoFile()
    added_po.metadata = new_po.metadata

    added_count = 0
    for entry in new_po:
        if getattr(entry, "obsolete", False):
            continue
        key = Key_tuple(
            msgctxt=entry.msgctxt,
            msgid=entry.msgid if entry.msgctxt.endswith(':') else None,
        )
        if key in old_keys:
            continue
        added_po.append(entry)
        added_count += 1

    added_po.format()
    return added_po, added_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a PO file containing only entries added between two commits."
    )
    parser.add_argument("old_commit", help="Base (older) commit")
    parser.add_argument("new_commit", help="Newer commit to compare against")
    parser.add_argument(
        "--po-path",
        default="po/messages.pot",
        help="PO/POT file to compare (relative to repo root or absolute path).",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output path for the extracted PO. Defaults to po/added-<basename>-<old>-<new>.po.",
    )
    args = parser.parse_args()

    repo_root = Path(get_repository_root())
    target_abs, rel_path = _resolve_target_path(args.po_path, repo_root)

    old_po = _load_po_from_commit(args.old_commit, rel_path, repo_root)
    new_po = _load_po_from_commit(args.new_commit, rel_path, repo_root)

    added_po, added_count = _build_added_po(old_po, new_po)

    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = (Path.cwd() / output_path).resolve()
    else:
        base_name = target_abs.stem
        output_name = f"added-{base_name}-{_sanitize_label(args.old_commit[:12])}-{_sanitize_label(args.new_commit[:12])}.po"
        output_path = repo_root / "po" / output_name

    output_path.parent.mkdir(parents=True, exist_ok=True)
    added_po.save(str(output_path))

    print(f"Target file:   {rel_path}")
    print(f"Old commit:    {args.old_commit}")
    print(f"New commit:    {args.new_commit}")
    print(f"Added entries: {added_count}")
    print(f"Output:        {output_path}")


if __name__ == "__main__":
    main()
