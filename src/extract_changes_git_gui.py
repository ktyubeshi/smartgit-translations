#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import subprocess
import tempfile
import shutil
import json
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTextEdit, QFileDialog, QMessageBox, QGroupBox,
                             QProgressBar, QCheckBox, QSpinBox, QComboBox,
                             QTabWidget, QDialog)
from PySide6.QtCore import Qt, QThread, Signal, QSettings
import sgpo
from extract_changes import extract_differences
from commit_picker_dialog import CommitPickerDialog
import argparse

class GitExtractWorker(QThread):
    progress = Signal(str)
    error = Signal(str)
    finished = Signal(dict)
    
    def __init__(self, repo_path, base_commit, compare_commit, relative_path, options):
        super().__init__()
        self.repo_path = repo_path
        self.base_commit = base_commit
        self.compare_commit = compare_commit
        self.relative_path = relative_path
        self.options = options
        self.temp_dir = None
    
    def run(self):
        try:
            os.chdir(self.repo_path)
            
            # Validate commits
            self.progress.emit("Validating commits...")
            for commit in [self.base_commit, self.compare_commit]:
                result = subprocess.run(["git", "rev-parse", commit], 
                                      capture_output=True, text=True, encoding='utf-8')
                if result.returncode != 0:
                    self.error.emit(f"Invalid commit: {commit}")
                    return
            
            # Get list of changed files
            self.progress.emit("Getting changed files...")
            cmd = ["git", "diff", "--name-only", f"{self.base_commit}..{self.compare_commit}"]
            if self.relative_path:
                cmd.extend(["--", self.relative_path])
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', check=True)
            changed_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            # Filter for PO files
            po_files = [f for f in changed_files if f.endswith('.po') or f.endswith('.pot')]
            
            if not po_files:
                self.progress.emit("No PO/POT files found in the changes.")
                self.finished.emit({"files": []})
                return
            
            # Create temporary directory for extraction
            self.temp_dir = tempfile.mkdtemp(prefix="smartgit_extract_")
            output_dir = Path("extracted_changes")
            output_dir.mkdir(exist_ok=True)
            
            results = {"files": [], "stats": {}}
            total_added = 0
            total_modified = 0
            total_removed = 0
            
            for po_file in po_files:
                self.progress.emit(f"Processing {po_file}...")
                
                # Extract base version to temp
                base_temp = Path(self.temp_dir) / f"base_{Path(po_file).name}"
                cmd = ["git", "show", f"{self.base_commit}:{po_file}"]
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
                
                if result.returncode != 0:
                    self.progress.emit(f"  Base version not found (new file)")
                    # This is a new file, create empty base
                    base_po = sgpo.SgPo()
                else:
                    with open(base_temp, 'w', encoding='utf-8') as f:
                        f.write(result.stdout)
                    base_po = sgpo.pofile(str(base_temp))
                
                # Extract compare version to temp
                compare_temp = Path(self.temp_dir) / f"compare_{Path(po_file).name}"
                cmd = ["git", "show", f"{self.compare_commit}:{po_file}"]
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
                
                if result.returncode != 0:
                    self.progress.emit(f"  Compare version not found (deleted file)")
                    # This file was deleted, create empty compare
                    compare_po = sgpo.SgPo()
                else:
                    with open(compare_temp, 'w', encoding='utf-8') as f:
                        f.write(result.stdout)
                    compare_po = sgpo.pofile(str(compare_temp))
                
                # Extract differences using the existing function
                args = argparse.Namespace(
                    include_added=self.options['include_added'],
                    include_removed=self.options['include_removed'],
                    include_modified=self.options['include_modified'],
                    include_fuzzy_removed=self.options['include_fuzzy_removed'],
                    show_previous=self.options['show_previous'],
                    sort=self.options['sort'],
                    verbose=False
                )
                
                changed_po = extract_differences(base_po, compare_po, args)
                
                # Count changes
                added = 0
                modified = 0
                removed = 0
                
                for entry in changed_po:
                    if entry.tcomment and "REMOVED:" in entry.tcomment:
                        removed += 1
                    elif (entry.msgctxt, entry.msgid) not in [(e.msgctxt, e.msgid) for e in base_po]:
                        added += 1
                    else:
                        modified += 1
                
                total_added += added
                total_modified += modified
                total_removed += removed
                
                # Save the differences
                if len(changed_po) > 0:
                    output_file = output_dir / f"{Path(po_file).stem}_changes.po"
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    changed_po.save(str(output_file))
                    
                    file_info = {
                        "original": po_file,
                        "output": str(output_file),
                        "added": added,
                        "modified": modified,
                        "removed": removed,
                        "total": len(changed_po)
                    }
                    results["files"].append(file_info)
                    
                    self.progress.emit(f"  Changes: +{added} ~{modified} -{removed}")
                else:
                    self.progress.emit(f"  No changes found")
            
            results["stats"] = {
                "total_added": total_added,
                "total_modified": total_modified,
                "total_removed": total_removed,
                "total_files": len(results["files"])
            }
            
            self.progress.emit("\nExtraction completed!")
            self.finished.emit(results)
            
        except subprocess.CalledProcessError as e:
            self.error.emit(f"Git command failed: {e.stderr}")
        except Exception as e:
            self.error.emit(f"Error: {str(e)}")
        finally:
            # Clean up temp directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)

class ExtractChangesGitGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("SmartGit", "ExtractChangesGUI")
        self.init_ui()
        self.load_settings()
        self.worker = None
        
    def init_ui(self):
        self.setWindowTitle("SmartGit Translation Changes Extractor (Git Integration)")
        self.setGeometry(100, 100, 900, 700)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create tabs
        tabs = QTabWidget()
        
        # Main tab
        main_tab = QWidget()
        main_layout = QVBoxLayout(main_tab)
        
        # Repository settings group
        repo_group = QGroupBox("Repository Settings")
        repo_layout = QVBoxLayout()
        
        # Repository root
        repo_root_layout = QHBoxLayout()
        repo_root_layout.addWidget(QLabel("Repository Root:"))
        self.repo_root_edit = QLineEdit()
        self.repo_root_edit.setPlaceholderText("e.g., C:\\Users\\username\\git_repository\\project")
        repo_root_layout.addWidget(self.repo_root_edit)
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_repository)
        repo_root_layout.addWidget(self.browse_button)
        repo_layout.addLayout(repo_root_layout)
        
        # Relative path
        relative_path_layout = QHBoxLayout()
        relative_path_layout.addWidget(QLabel("Relative Path (optional):"))
        self.relative_path_edit = QLineEdit()
        self.relative_path_edit.setPlaceholderText("e.g., po/ or src/translations/")
        relative_path_layout.addWidget(self.relative_path_edit)
        repo_layout.addLayout(relative_path_layout)
        
        repo_group.setLayout(repo_layout)
        main_layout.addWidget(repo_group)
        
        # Commit settings group
        commit_group = QGroupBox("Commit Selection")
        commit_layout = QVBoxLayout()
        
        # Base commit
        base_commit_layout = QHBoxLayout()
        base_commit_layout.addWidget(QLabel("Base Commit:"))
        self.base_commit_edit = QLineEdit()
        self.base_commit_edit.setPlaceholderText("e.g., a26c991, HEAD~5, or branch name")
        base_commit_layout.addWidget(self.base_commit_edit)
        self.base_commit_picker_button = QPushButton("...")
        self.base_commit_picker_button.setMaximumWidth(30)
        self.base_commit_picker_button.clicked.connect(self.pick_base_commit)
        base_commit_layout.addWidget(self.base_commit_picker_button)
        commit_layout.addLayout(base_commit_layout)
        
        # Compare commit
        compare_commit_layout = QHBoxLayout()
        compare_commit_layout.addWidget(QLabel("Compare Commit:"))
        self.compare_commit_edit = QLineEdit()
        self.compare_commit_edit.setPlaceholderText("e.g., 1bd4d37, HEAD, or branch name")
        self.compare_commit_edit.setText("HEAD")
        compare_commit_layout.addWidget(self.compare_commit_edit)
        self.compare_commit_picker_button = QPushButton("...")
        self.compare_commit_picker_button.setMaximumWidth(30)
        self.compare_commit_picker_button.clicked.connect(self.pick_compare_commit)
        compare_commit_layout.addWidget(self.compare_commit_picker_button)
        commit_layout.addLayout(compare_commit_layout)
        
        commit_group.setLayout(commit_layout)
        main_layout.addWidget(commit_group)
        
        tabs.addTab(main_tab, "Main")
        
        # Options tab
        options_tab = QWidget()
        options_layout = QVBoxLayout(options_tab)
        
        options_group = QGroupBox("Extraction Options")
        options_group_layout = QVBoxLayout()
        
        self.include_added_check = QCheckBox("Include added entries")
        self.include_added_check.setChecked(True)
        options_group_layout.addWidget(self.include_added_check)
        
        self.include_modified_check = QCheckBox("Include modified entries")
        self.include_modified_check.setChecked(True)
        options_group_layout.addWidget(self.include_modified_check)
        
        self.include_removed_check = QCheckBox("Include removed entries")
        self.include_removed_check.setChecked(False)
        options_group_layout.addWidget(self.include_removed_check)
        
        self.include_fuzzy_removed_check = QCheckBox("Include entries with fuzzy flag removed")
        self.include_fuzzy_removed_check.setChecked(False)
        options_group_layout.addWidget(self.include_fuzzy_removed_check)
        
        self.show_previous_check = QCheckBox("Show previous content for modified entries")
        self.show_previous_check.setChecked(False)
        options_group_layout.addWidget(self.show_previous_check)
        
        self.sort_check = QCheckBox("Sort entries in output")
        self.sort_check.setChecked(False)
        options_group_layout.addWidget(self.sort_check)
        
        options_group.setLayout(options_group_layout)
        options_layout.addWidget(options_group)
        options_layout.addStretch()
        
        tabs.addTab(options_tab, "Options")
        layout.addWidget(tabs)
        
        # Action buttons
        button_layout = QHBoxLayout()
        self.extract_button = QPushButton("Extract Changes")
        self.extract_button.clicked.connect(self.extract_changes)
        button_layout.addWidget(self.extract_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_extraction)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.cancel_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Output area
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(self.output_text.font())
        layout.addWidget(self.output_text)
        
        # Set default repository if in git repo
        self.set_default_repository()
    
    def load_settings(self):
        """Load saved settings"""
        # Repository settings
        self.repo_root_edit.setText(self.settings.value("repo_root", ""))
        self.relative_path_edit.setText(self.settings.value("relative_path", ""))
        
        # Commit settings
        self.base_commit_edit.setText(self.settings.value("base_commit", ""))
        self.compare_commit_edit.setText(self.settings.value("compare_commit", "HEAD"))
        
        # Options
        self.include_added_check.setChecked(self.settings.value("include_added", True, type=bool))
        self.include_modified_check.setChecked(self.settings.value("include_modified", True, type=bool))
        self.include_removed_check.setChecked(self.settings.value("include_removed", False, type=bool))
        self.include_fuzzy_removed_check.setChecked(self.settings.value("include_fuzzy_removed", False, type=bool))
        self.show_previous_check.setChecked(self.settings.value("show_previous", False, type=bool))
        self.sort_check.setChecked(self.settings.value("sort", False, type=bool))
    
    def save_settings(self):
        """Save current settings"""
        # Repository settings
        self.settings.setValue("repo_root", self.repo_root_edit.text())
        self.settings.setValue("relative_path", self.relative_path_edit.text())
        
        # Commit settings
        self.settings.setValue("base_commit", self.base_commit_edit.text())
        self.settings.setValue("compare_commit", self.compare_commit_edit.text())
        
        # Options
        self.settings.setValue("include_added", self.include_added_check.isChecked())
        self.settings.setValue("include_modified", self.include_modified_check.isChecked())
        self.settings.setValue("include_removed", self.include_removed_check.isChecked())
        self.settings.setValue("include_fuzzy_removed", self.include_fuzzy_removed_check.isChecked())
        self.settings.setValue("show_previous", self.show_previous_check.isChecked())
        self.settings.setValue("sort", self.sort_check.isChecked())
    
    def set_default_repository(self):
        try:
            result = subprocess.run(["git", "rev-parse", "--show-toplevel"], 
                                  capture_output=True, text=True, encoding='utf-8', check=True)
            repo_root = result.stdout.strip()
            self.repo_root_edit.setText(repo_root)
            
            # Also try to set default relative path if we're in a known structure
            cwd = os.getcwd()
            if "po" in cwd or os.path.exists(os.path.join(repo_root, "po")):
                self.relative_path_edit.setText("po/")
        except:
            pass
    
    def browse_repository(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Repository Root")
        if directory:
            self.repo_root_edit.setText(directory)
    
    def extract_changes(self):
        # Save settings before extraction
        self.save_settings()
        
        repo_root = self.repo_root_edit.text().strip()
        base_commit = self.base_commit_edit.text().strip()
        compare_commit = self.compare_commit_edit.text().strip()
        relative_path = self.relative_path_edit.text().strip()
        
        # Validation
        if not repo_root:
            QMessageBox.warning(self, "Warning", "Please specify repository root.")
            return
        
        if not os.path.exists(repo_root):
            QMessageBox.warning(self, "Warning", "Repository root does not exist.")
            return
        
        if not base_commit:
            QMessageBox.warning(self, "Warning", "Please specify base commit.")
            return
        
        if not compare_commit:
            QMessageBox.warning(self, "Warning", "Please specify compare commit.")
            return
        
        # Clear output
        self.output_text.clear()
        self.output_text.append(f"Repository: {repo_root}")
        self.output_text.append(f"Base commit: {base_commit}")
        self.output_text.append(f"Compare commit: {compare_commit}")
        if relative_path:
            self.output_text.append(f"Relative path: {relative_path}")
        self.output_text.append("-" * 70)
        
        # Gather options
        options = {
            'include_added': self.include_added_check.isChecked(),
            'include_modified': self.include_modified_check.isChecked(),
            'include_removed': self.include_removed_check.isChecked(),
            'include_fuzzy_removed': self.include_fuzzy_removed_check.isChecked(),
            'show_previous': self.show_previous_check.isChecked(),
            'sort': self.sort_check.isChecked()
        }
        
        # Disable buttons and start progress
        self.extract_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setRange(0, 0)
        
        # Start worker thread
        self.worker = GitExtractWorker(repo_root, base_commit, compare_commit, 
                                      relative_path, options)
        self.worker.progress.connect(self.on_progress)
        self.worker.error.connect(self.on_error)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
    
    def cancel_extraction(self):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.output_text.append("\nExtraction cancelled.")
            self.reset_ui()
    
    def on_progress(self, message):
        self.output_text.append(message)
    
    def on_error(self, error_message):
        self.output_text.append(f"\nERROR: {error_message}")
        QMessageBox.critical(self, "Error", error_message)
        self.reset_ui()
    
    def on_finished(self, results):
        self.output_text.append("\n" + "=" * 70)
        
        if results["files"]:
            stats = results["stats"]
            self.output_text.append(f"\nSummary:")
            self.output_text.append(f"  Total files with changes: {stats['total_files']}")
            self.output_text.append(f"  Total added entries: {stats['total_added']}")
            self.output_text.append(f"  Total modified entries: {stats['total_modified']}")
            self.output_text.append(f"  Total removed entries: {stats['total_removed']}")
            
            self.output_text.append(f"\nExtracted files:")
            for file_info in results["files"]:
                self.output_text.append(f"\n  {file_info['original']}:")
                self.output_text.append(f"    → {file_info['output']}")
                self.output_text.append(f"    Changes: +{file_info['added']} ~{file_info['modified']} -{file_info['removed']} (Total: {file_info['total']})")
            
            self.output_text.append("\nFiles saved to 'extracted_changes' directory.")
        else:
            self.output_text.append("No changes found in PO/POT files.")
        
        self.reset_ui()
    
    def reset_ui(self):
        self.extract_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
    
    def closeEvent(self, event):
        """Save settings when closing the window"""
        self.save_settings()
        event.accept()
    
    def pick_base_commit(self):
        """Open commit picker dialog for base commit"""
        repo_root = self.repo_root_edit.text().strip()
        if not repo_root:
            QMessageBox.warning(self, "Warning", "Please specify repository root first.")
            return
        
        if not os.path.exists(repo_root):
            QMessageBox.warning(self, "Warning", "Repository root does not exist.")
            return
        
        dialog = CommitPickerDialog(repo_root, self)
        if dialog.exec() == QDialog.Accepted:
            commit = dialog.get_selected_commit()
            if commit:
                self.base_commit_edit.setText(commit)
    
    def pick_compare_commit(self):
        """Open commit picker dialog for compare commit"""
        repo_root = self.repo_root_edit.text().strip()
        if not repo_root:
            QMessageBox.warning(self, "Warning", "Please specify repository root first.")
            return
        
        if not os.path.exists(repo_root):
            QMessageBox.warning(self, "Warning", "Repository root does not exist.")
            return
        
        dialog = CommitPickerDialog(repo_root, self)
        if dialog.exec() == QDialog.Accepted:
            commit = dialog.get_selected_commit()
            if commit:
                self.compare_commit_edit.setText(commit)

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = ExtractChangesGitGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()