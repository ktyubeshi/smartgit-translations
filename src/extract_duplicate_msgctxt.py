#!/usr/bin/env python3
"""
Extract PO entries with duplicate msgctxt but different msgid.

This script identifies cases where the same msgctxt appears multiple times
with different msgid values. While this is allowed in GNU gettext, SmartGit
assumes msgctxt is unique when it doesn't end with ':'.

Usage:
    # Basic usage - show all duplicate msgctxt entries
    python extract_duplicate_msgctxt.py path/to/file.po
    
    # Generate Markdown report for problematic entries (msgctxt not ending with ':')
    python extract_duplicate_msgctxt.py path/to/file.po --markdown
    
    # Generate Markdown report with custom output path
    python extract_duplicate_msgctxt.py path/to/file.po --markdown --output report.md
    
    # Export as CSV format
    python extract_duplicate_msgctxt.py path/to/file.po --csv
    
    # Fix duplicate msgctxt by appending ':' to problematic entries
    python extract_duplicate_msgctxt.py path/to/file.po --fix

Examples:
    # Analyze template file
    python extract_duplicate_msgctxt.py ../po/messages.pot --markdown
    
    # Fix all PO files in a directory
    python extract_duplicate_msgctxt.py ../po/messages.pot --fix
    python extract_duplicate_msgctxt.py ../po/ja_JP.po --fix
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sgpo.sgpo import pofile


def extract_duplicate_msgctxt(po_file_path: Path) -> Dict[str, List[Tuple[str, str, int]]]:
    """
    Extract entries with duplicate msgctxt but different msgid.
    
    Args:
        po_file_path: Path to the PO file
        
    Returns:
        Dictionary mapping msgctxt to list of (msgid, msgstr, line_number) tuples
    """
    # Track msgctxt occurrences
    msgctxt_entries = defaultdict(list)
    
    try:
        po_file = pofile(str(po_file_path))
        
        for entry in po_file:
            if entry.msgctxt:
                # Store msgid, msgstr, and line number for each msgctxt
                msgctxt_entries[entry.msgctxt].append((
                    entry.msgid,
                    entry.msgstr,
                    entry.linenum if hasattr(entry, 'linenum') else 0
                ))
                
    except Exception as e:
        print(f"Error reading PO file: {e}", file=sys.stderr)
        return {}
    
    # Filter to only include duplicate msgctxt with different msgid
    duplicates = {}
    for msgctxt, entries in msgctxt_entries.items():
        # Check if this msgctxt has multiple different msgid values
        unique_msgids = set(entry[0] for entry in entries)
        if len(unique_msgids) > 1:
            duplicates[msgctxt] = entries
            
    return duplicates


def print_duplicates(duplicates: Dict[str, List[Tuple[str, str, int]]], 
                    po_file_path: Path) -> None:
    """
    Print duplicate msgctxt entries in a readable format.
    
    Args:
        duplicates: Dictionary of duplicate entries
        po_file_path: Path to the PO file for display
    """
    if not duplicates:
        print(f"No duplicate msgctxt entries found in {po_file_path}")
        return
        
    print(f"Found {len(duplicates)} msgctxt values with different msgid in {po_file_path}:\n")
    
    for msgctxt, entries in sorted(duplicates.items()):
        print(f"msgctxt: {repr(msgctxt)}")
        print(f"  Appears {len(entries)} times with different msgid values:")
        
        for i, (msgid, msgstr, linenum) in enumerate(entries, 1):
            print(f"\n  Entry {i} (line ~{linenum}):")
            print(f"    msgid: {repr(msgid)}")
            print(f"    msgstr: {repr(msgstr)}")
            
        print("-" * 80)


def fix_duplicate_msgctxt(po_file_path: Path, duplicates: Dict[str, List[Tuple[str, str, int]]]) -> int:
    """
    Fix duplicate msgctxt entries by appending ':' to those that don't already end with ':'.
    
    Args:
        po_file_path: Path to the PO file to fix
        duplicates: Dictionary of duplicate entries
        
    Returns:
        Number of entries fixed
    """
    # Filter to only include msgctxt that don't end with ':'
    problematic = {k: v for k, v in duplicates.items() if not k.endswith(':')}
    
    if not problematic:
        return 0
    
    # Read the entire file
    with open(po_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    fixed_count = 0
    modified_lines = lines.copy()
    
    # Process each problematic msgctxt
    for msgctxt in problematic:
        # Find and fix all occurrences of this msgctxt
        i = 0
        while i < len(modified_lines):
            line = modified_lines[i]
            if line.strip().startswith('msgctxt "') and msgctxt in line:
                # Check if this is the exact msgctxt we're looking for
                # Extract the msgctxt value from the line
                start_quote = line.find('"') + 1
                end_quote = line.rfind('"')
                if start_quote > 0 and end_quote > start_quote:
                    line_msgctxt = line[start_quote:end_quote]
                    if line_msgctxt == msgctxt:
                        # Replace the msgctxt with the fixed version
                        fixed_msgctxt = msgctxt + ':'
                        modified_lines[i] = line.replace(f'"{msgctxt}"', f'"{fixed_msgctxt}"')
                        fixed_count += 1
            i += 1
    
    # Write the fixed file
    if fixed_count > 0:
        with open(po_file_path, 'w', encoding='utf-8') as f:
            f.writelines(modified_lines)
    
    return fixed_count


def generate_markdown_report(duplicates: Dict[str, List[Tuple[str, str, int]]], 
                           po_file_path: Path) -> str:
    """
    Generate a Markdown report for duplicate msgctxt entries that don't end with ':'.
    
    Args:
        duplicates: Dictionary of duplicate entries
        po_file_path: Path to the PO file
        
    Returns:
        Markdown formatted report
    """
    # Filter to only include msgctxt that don't end with ':'
    problematic = {k: v for k, v in duplicates.items() if not k.endswith(':')}
    
    if not problematic:
        return f"# Duplicate msgctxt Analysis Report\n\nNo problematic duplicate msgctxt entries found in `{po_file_path.name}`.\n\nAll duplicate msgctxt entries end with ':' and should be compatible with SmartGit."
    
    report = []
    report.append(f"# Duplicate msgctxt Analysis Report")
    report.append(f"\n**File:** `{po_file_path.name}`")
    report.append(f"\n**Date:** {sys.modules['datetime'].datetime.now().strftime('%Y-%m-%d %H:%M:%S') if 'datetime' in sys.modules else 'N/A'}")
    report.append(f"\n## Summary")
    report.append(f"\nFound **{len(problematic)}** problematic msgctxt values that:")
    report.append("1. Appear multiple times with different msgid values")
    report.append("2. Don't end with ':' (violates SmartGit's uniqueness assumption)")
    
    report.append(f"\n## Problematic Entries\n")
    
    for i, (msgctxt, entries) in enumerate(sorted(problematic.items()), 1):
        report.append(f"### {i}. `{msgctxt}`")
        report.append(f"\nThis msgctxt appears **{len(entries)}** times with different msgid values:\n")
        
        for j, (msgid, msgstr, linenum) in enumerate(entries, 1):
            report.append(f"#### Entry {j} (line ~{linenum})")
            report.append("```")
            report.append(f'msgctxt "{msgctxt}"')
            report.append(f'msgid "{msgid}"')
            if msgstr:
                report.append(f'msgstr "{msgstr}"')
            else:
                report.append('msgstr ""')
            report.append("```")
            report.append("")
    
    report.append("\n## Recommendation\n")
    report.append("These entries should be reviewed and fixed to ensure SmartGit compatibility.")
    report.append("Consider adding ':' to the end of the msgctxt or ensuring each msgctxt is truly unique.")
    
    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(
        description="Extract PO entries with duplicate msgctxt but different msgid"
    )
    parser.add_argument(
        "po_file",
        type=Path,
        help="Path to the PO file to analyze"
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Output results in CSV format"
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Generate Markdown report for problematic entries (msgctxt not ending with ':')"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path for the report (default: script_dir/duplicate_msgctxt_report_{po_filename}.md)"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix duplicate msgctxt by appending ':' to entries that don't already end with ':'"
    )
    
    args = parser.parse_args()
    
    if not args.po_file.exists():
        print(f"Error: File not found: {args.po_file}", file=sys.stderr)
        sys.exit(1)
        
    # Extract duplicates
    duplicates = extract_duplicate_msgctxt(args.po_file)
    
    if args.fix:
        # Fix the duplicate msgctxt entries
        fixed_count = fix_duplicate_msgctxt(args.po_file, duplicates)
        if fixed_count > 0:
            print(f"Fixed {fixed_count} duplicate msgctxt entries in {args.po_file}")
            # Re-extract duplicates to verify the fix
            duplicates_after = extract_duplicate_msgctxt(args.po_file)
            remaining = {k: v for k, v in duplicates_after.items() if not k.endswith(':')}
            if remaining:
                print(f"Warning: {len(remaining)} problematic entries remain after fix")
            else:
                print("All problematic duplicate msgctxt entries have been fixed!")
        else:
            print(f"No problematic duplicate msgctxt entries to fix in {args.po_file}")
        return
    
    if args.markdown:
        # Import datetime for the report
        import datetime
        sys.modules['datetime'] = datetime
        
        # Generate Markdown report
        report = generate_markdown_report(duplicates, args.po_file)
        
        # Determine output file path
        if args.output:
            output_path = args.output
        else:
            # Default: save in script directory with descriptive filename
            script_dir = Path(__file__).parent
            po_basename = args.po_file.stem  # e.g., "ru_RU" from "ru_RU.po"
            output_path = script_dir / f"duplicate_msgctxt_report_{po_basename}.md"
        
        # Write report to file
        output_path.write_text(report, encoding='utf-8')
        print(f"Report saved to: {output_path}")
        
        # Also print to stdout for convenience
        print("\n" + "="*80 + "\n")
        print(report)
    elif args.csv:
        # CSV output
        print("msgctxt,msgid,msgstr,line_number")
        for msgctxt, entries in sorted(duplicates.items()):
            for msgid, msgstr, linenum in entries:
                # Escape quotes for CSV
                msgctxt_csv = msgctxt.replace('"', '""')
                msgid_csv = msgid.replace('"', '""')
                msgstr_csv = msgstr.replace('"', '""')
                print(f'"{msgctxt_csv}","{msgid_csv}","{msgstr_csv}",{linenum}')
    else:
        # Human-readable output
        print_duplicates(duplicates, args.po_file)
        
        # Summary for SmartGit compatibility
        if duplicates:
            print("\nSmartGit Compatibility Warning:")
            print("The following msgctxt values appear multiple times with different msgid:")
            for msgctxt in sorted(duplicates.keys()):
                if not msgctxt.endswith(':'):
                    print(f"  - {repr(msgctxt)} (doesn't end with ':')")
                else:
                    print(f"  - {repr(msgctxt)} (ends with ':' - should be OK)")


if __name__ == "__main__":
    main()