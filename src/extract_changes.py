# /// script
# dependencies = ["polib"]
# ///

import sgpo
import argparse
import sys
import os


def main():
    parser = argparse.ArgumentParser(
        prog='diff_sgpo',
        description='Compare two SmartGit PO/POT files and extract differences'
    )
    
    parser.add_argument('base_file', 
                        help='Path to the base (old) PO/POT file')
    parser.add_argument('compare_file',
                        help='Path to the compare (new) PO/POT file')
    parser.add_argument('-o', '--output',
                        help='Output file path (if not specified, outputs to stdout)')
    parser.add_argument('--include-added', action='store_true', default=True,
                        help='Include added entries (default: true)')
    parser.add_argument('--no-include-added', action='store_false', dest='include_added',
                        help='Do not include added entries')
    parser.add_argument('--include-removed', action='store_true', default=False,
                        help='Include removed entries (default: false)')
    parser.add_argument('--include-modified', action='store_true', default=True,
                        help='Include modified entries (default: true)')
    parser.add_argument('--no-include-modified', action='store_false', dest='include_modified',
                        help='Do not include modified entries')
    parser.add_argument('--include-fuzzy-removed', action='store_true', default=False,
                        help='Include entries with fuzzy flag removed (default: false)')
    parser.add_argument('--show-previous', action='store_true', default=False,
                        help='Add previous content comments (#|) for modified entries')
    parser.add_argument('--sort', action='store_true', default=False,
                        help='Sort entries in the output')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose output to stderr')
    parser.add_argument('--wrap-width', type=int, default=9999,
                        help='Line wrap width for output (0 = no wrap, default: 9999)')
    parser.add_argument('--interactive', action='store_true',
                        help='Interactive mode (wait for input before exit when launched from GUI)')
    
    args = parser.parse_args()
    
    try:
        if args.interactive:
            print("Interactive mode is not implemented in Python version", file=sys.stderr)
        
        # Read files
        if args.verbose:
            print(f"Loading base file: {args.base_file}", file=sys.stderr)
        
        if args.base_file == '-':
            base_content = sys.stdin.read()
            base_po = sgpo.parse_string(base_content)
        else:
            base_po = sgpo.pofile(args.base_file)
        
        if args.verbose:
            print(f"Loading compare file: {args.compare_file}", file=sys.stderr)
        
        if args.compare_file == '-':
            if args.base_file == '-':
                print("Cannot read both base and compare files from stdin", file=sys.stderr)
                sys.exit(1)
            compare_content = sys.stdin.read()
            compare_po = sgpo.parse_string(compare_content)
        else:
            compare_po = sgpo.pofile(args.compare_file)
        
        # Extract differences
        changed_po = extract_differences(base_po, compare_po, args)
        
        if args.verbose:
            print(f"Found {len(changed_po)} different entries", file=sys.stderr)
        
        # If sorting is required
        if args.sort:
            if args.verbose:
                print("Sorting entries...", file=sys.stderr)
            changed_po.sort()
        
        # Output
        if args.output:
            if args.verbose:
                print(f"Writing to file: {args.output}", file=sys.stderr)
            changed_po.save(args.output)
        else:
            # Output to stdout
            print(changed_po)
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def extract_differences(base_po: sgpo.SgPo, compare_po: sgpo.SgPo, args) -> sgpo.SgPo:
    """Extract differences between two PO files based on the provided arguments."""
    changed_po = sgpo.SgPo()
    changed_po.metadata = compare_po.metadata

    # Create a dictionary for faster lookup of base entries
    base_entries = {}
    for entry in base_po:
        key = (entry.msgctxt, entry.msgid)
        base_entries[key] = entry

    # Check entries in compare file
    for compare_entry in compare_po:
        key = (compare_entry.msgctxt, compare_entry.msgid)
        base_entry = base_entries.get(key)
        
        if base_entry is None:
            # Added entry
            if args.include_added:
                changed_po.append(compare_entry)
        else:
            # Check if modified
            is_modified = False
            modification_details = []
            
            # Check msgstr changes
            if compare_entry.msgstr != base_entry.msgstr:
                is_modified = True
                modification_details.append("msgstr changed")
            
            # Check fuzzy flag changes
            base_fuzzy = 'fuzzy' in (base_entry.flags or [])
            compare_fuzzy = 'fuzzy' in (compare_entry.flags or [])
            
            if base_fuzzy and not compare_fuzzy:
                # Fuzzy flag removed
                if args.include_fuzzy_removed:
                    is_modified = True
                    modification_details.append("fuzzy flag removed")
            elif not base_fuzzy and compare_fuzzy:
                # Fuzzy flag added
                is_modified = True
                modification_details.append("fuzzy flag added")
            
            # Check other changes (comments, etc.)
            if base_entry.comment != compare_entry.comment:
                is_modified = True
                modification_details.append("comment changed")
            
            if is_modified and args.include_modified:
                entry = compare_entry.__class__()
                entry.msgctxt = compare_entry.msgctxt
                entry.msgid = compare_entry.msgid
                entry.msgstr = compare_entry.msgstr
                entry.flags = compare_entry.flags
                entry.comment = compare_entry.comment
                entry.tcomment = compare_entry.tcomment
                entry.occurrences = compare_entry.occurrences
                
                # Add previous content if requested
                if args.show_previous and base_entry.msgstr:
                    if entry.tcomment:
                        entry.tcomment = entry.tcomment + "\nPrevious-msgstr: " + base_entry.msgstr
                    else:
                        entry.tcomment = "Previous-msgstr: " + base_entry.msgstr
                
                changed_po.append(entry)
    
    # Check for removed entries if requested
    if args.include_removed:
        compare_entries = {}
        for entry in compare_po:
            key = (entry.msgctxt, entry.msgid)
            compare_entries[key] = entry
        
        for base_entry in base_po:
            key = (base_entry.msgctxt, base_entry.msgid)
            if key not in compare_entries:
                # Removed entry
                entry = base_entry.__class__()
                entry.msgctxt = base_entry.msgctxt
                entry.msgid = base_entry.msgid
                entry.msgstr = base_entry.msgstr
                entry.flags = base_entry.flags
                entry.comment = base_entry.comment
                entry.occurrences = base_entry.occurrences
                
                # Add removed marker
                removed_comment = "REMOVED: This entry was removed in the new version"
                if entry.tcomment:
                    entry.tcomment = removed_comment + "\n" + entry.tcomment
                else:
                    entry.tcomment = removed_comment
                
                changed_po.append(entry)
    
    return changed_po


if __name__ == "__main__":
    main()
