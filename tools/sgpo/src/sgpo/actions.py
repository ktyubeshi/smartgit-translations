from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Iterator

import sgpo
from extract_added_po_entries import (
    _build_added_po,
    _load_po_from_commit,
    _resolve_target_path,
    _sanitize_label,
)
from path_finder import PoPathFinder

_PLACEHOLDER_PATTERN = re.compile(r"\$[0-9]+")


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
    pot_path = finder.get_pot_file()
    po_files = finder.get_po_files(translation_file_only=True)

    targets: list[str] = []
    if pot_path:
        targets.append(pot_path)
    targets.extend(po_files)

    total = 0
    for po_path in targets:
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
    """Treat '...', '…', and '\u2026' (literal) as equivalent."""

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
