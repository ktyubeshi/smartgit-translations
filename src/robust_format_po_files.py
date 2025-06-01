#!/usr/bin/env python3
"""
Robust PO file formatter with msgcat fallback.

This script formats PO files using sgpo, and falls back to msgcat
if sgpo fails due to syntax errors.
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from path_finder import PoPathFinder
from sgpo import sgpo


def has_msgcat():
    """Check if msgcat is available."""
    try:
        subprocess.run(['msgcat', '--version'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL, 
                      check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def format_with_msgcat(po_file_path):
    """
    Format a PO file using msgcat to fix syntax errors.
    
    Args:
        po_file_path: Path to the PO file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.po', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        # Run msgcat to fix syntax errors
        result = subprocess.run([
            'msgcat',
            '--no-wrap',
            '--sort-output',
            '-o', tmp_path,
            po_file_path
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"  msgcat failed: {result.stderr.strip()}")
            os.unlink(tmp_path)
            return False
        
        # If successful, replace the original file
        shutil.move(tmp_path, po_file_path)
        print(f"  ✓ Repaired with msgcat")
        return True
        
    except Exception as e:
        print(f"  msgcat error: {e}")
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return False


def attempt_manual_repair(po_file_path):
    """
    Attempt to manually repair common syntax errors in PO files.
    
    Args:
        po_file_path: Path to the PO file
        
    Returns:
        bool: True if repaired, False otherwise
    """
    try:
        with open(po_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Common repairs
        repaired = False
        new_lines = []
        
        for i, line in enumerate(lines):
            # Remove standalone backslashes on their own line
            if line.strip() == '\\':
                print(f"  Removing stray backslash on line {i+1}")
                repaired = True
                continue
            
            # Fix lines that end with backslash but shouldn't
            if line.rstrip().endswith('\\') and not line.strip().startswith('"'):
                if i + 1 < len(lines) and not lines[i + 1].strip().startswith('"'):
                    print(f"  Removing trailing backslash on line {i+1}")
                    line = line.rstrip()[:-1] + '\n'
                    repaired = True
            
            new_lines.append(line)
        
        if repaired:
            # Write repaired content
            with open(po_file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"  ✓ Manual repair completed")
            return True
        
        return False
        
    except Exception as e:
        print(f"  Manual repair error: {e}")
        return False


def format_po_file_robust(po_file_path):
    """
    Format a PO file robustly, with fallback to msgcat.
    
    Args:
        po_file_path: Path to the PO file
        
    Returns:
        bool: True if successful, False otherwise
    """
    print(f"Formatting: {po_file_path}")
    
    # First, try with sgpo
    try:
        po = sgpo.pofile(po_file_path)
        po.format()
        po.save(po_file_path)
        print(f"  ✓ Formatted with sgpo")
        return True
    except Exception as e:
        print(f"  ✗ sgpo failed: {e}")
        
        # Try manual repair first
        print(f"  Attempting manual repair...")
        manual_repaired = attempt_manual_repair(po_file_path)
        
        if manual_repaired:
            # Try sgpo again after manual repair
            try:
                po = sgpo.pofile(po_file_path)
                po.format()
                po.save(po_file_path)
                print(f"  ✓ Formatted with sgpo after manual repair")
                return True
            except Exception as e2:
                print(f"  ✗ sgpo still failed after manual repair: {e2}")
        
        # If msgcat is available, try to repair
        if has_msgcat():
            print(f"  Attempting repair with msgcat...")
            if format_with_msgcat(po_file_path):
                # Try sgpo again after repair
                try:
                    po = sgpo.pofile(po_file_path)
                    # Fix entries with None msgctxt before formatting
                    for entry in po:
                        if entry.msgctxt is None:
                            entry.msgctxt = ""
                    po.format()
                    po.save(po_file_path)
                    print(f"  ✓ Formatted with sgpo after msgcat repair")
                    return True
                except Exception as e2:
                    print(f"  ✗ sgpo still failed after repair: {e2}")
                    # If sgpo still fails, at least msgcat formatted it
                    print(f"  ✓ File was formatted by msgcat")
                    return True
            else:
                return False
        else:
            print(f"  ✗ msgcat not available for repair")
            return False


def main():
    """Main function to format all PO files."""
    # Check if msgcat is available
    if has_msgcat():
        print("msgcat is available for fallback repairs")
    else:
        print("WARNING: msgcat not found. Fallback repair will not be available.")
        print("Install gettext tools for better error recovery.")
    
    print()
    
    # Find all PO files
    path_finder = PoPathFinder()
    po_files = path_finder.get_po_files(translation_file_only=True)
    
    if not po_files:
        print("No PO files found to format.")
        return 0
    
    # Track results
    total = len(po_files)
    successful = 0
    failed = []
    
    # Process each file
    for po_file in po_files:
        if format_po_file_robust(po_file):
            successful += 1
        else:
            failed.append(po_file)
    
    # Summary
    print()
    print(f"Summary: {successful}/{total} files formatted successfully")
    
    if failed:
        print("\nFailed files:")
        for f in failed:
            print(f"  - {f}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())