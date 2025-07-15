#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import os
import re
from datetime import datetime
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QLineEdit, QCheckBox,
                             QApplication)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

class CommitPickerDialog(QDialog):
    def __init__(self, repo_path, parent=None):
        super().__init__(parent)
        self.repo_path = repo_path
        self.selected_commit = None
        self.branches = []
        self.init_ui()
        
        # Use QTimer to load data after dialog is shown
        QTimer.singleShot(100, self.initialize_data)
    
    def initialize_data(self):
        """Load data after dialog is fully initialized"""
        self.load_branches()
        self.load_commits()
    
    def init_ui(self):
        self.setWindowTitle("Select Commit")
        self.setGeometry(200, 200, 1000, 600)
        
        layout = QVBoxLayout()
        
        # Branch selection
        branch_layout = QHBoxLayout()
        branch_layout.addWidget(QLabel("Branch:"))
        
        self.branch_combo = QComboBox()
        self.branch_combo.currentTextChanged.connect(self.on_branch_changed)
        branch_layout.addWidget(self.branch_combo)
        
        self.all_branches_check = QCheckBox("Show all branches")
        self.all_branches_check.stateChanged.connect(self.on_all_branches_changed)
        branch_layout.addWidget(self.all_branches_check)
        
        branch_layout.addStretch()
        layout.addLayout(branch_layout)
        
        # Search
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search commit messages...")
        self.search_edit.returnPressed.connect(self.on_search)
        search_layout.addWidget(self.search_edit)
        
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.on_search)
        search_layout.addWidget(self.search_button)
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.on_clear_search)
        search_layout.addWidget(self.clear_button)
        
        layout.addLayout(search_layout)
        
        # Commit table
        self.commit_table = QTableWidget()
        self.commit_table.setColumnCount(6)
        self.commit_table.setHorizontalHeaderLabels(["Graph", "SHA", "Author", "Date", "Message", "Full SHA"])
        self.commit_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.commit_table.setAlternatingRowColors(True)
        self.commit_table.doubleClicked.connect(self.on_table_double_click)
        
        # Hide full SHA column
        self.commit_table.setColumnHidden(5, True)
        
        # Set column widths
        header = self.commit_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        self.commit_table.setColumnWidth(0, 150)
        
        # Set monospace font
        font = QFont("Consolas, Monaco, monospace")
        self.commit_table.setFont(font)
        
        layout.addWidget(self.commit_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.select_button = QPushButton("Select")
        self.select_button.clicked.connect(self.on_select)
        button_layout.addWidget(self.select_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_branches(self):
        try:
            os.chdir(self.repo_path)
            
            # Get current branch
            result = subprocess.run(["git", "branch", "--show-current"], 
                                  capture_output=True, text=True, encoding='utf-8')
            current_branch = result.stdout.strip()
            
            # Get all branches
            cmd = ["git", "branch", "-a", "--format=%(refname:short)"]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode == 0:
                branches = result.stdout.strip().split('\n')
                self.branches = [b.strip() for b in branches if b.strip()]
                
                # Add branches to combo box
                self.branch_combo.blockSignals(True)
                self.branch_combo.clear()
                self.branch_combo.addItem("HEAD")
                
                # Add local branches first
                local_branches = [b for b in self.branches if not b.startswith('origin/')]
                for branch in sorted(local_branches):
                    self.branch_combo.addItem(branch)
                
                # Set current branch as selected
                if current_branch:
                    index = self.branch_combo.findText(current_branch)
                    if index >= 0:
                        self.branch_combo.setCurrentIndex(index)
                
                self.branch_combo.blockSignals(False)
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load branches: {str(e)}")
    
    def on_all_branches_changed(self, state):
        self.branch_combo.blockSignals(True)
        
        if state == Qt.Checked:
            # Add remote branches
            self.branch_combo.clear()
            self.branch_combo.addItem("HEAD")
            self.branch_combo.addItem("--all")
            
            for branch in sorted(self.branches):
                self.branch_combo.addItem(branch)
        else:
            # Show only local branches
            self.load_branches()
        
        self.branch_combo.blockSignals(False)
        self.load_commits()
    
    def on_branch_changed(self):
        self.load_commits()
    
    def on_search(self):
        self.load_commits()
    
    def on_clear_search(self):
        self.search_edit.clear()
        self.load_commits()
    
    def load_commits(self):
        """Load commits with graph using git log --graph"""
        try:
            os.chdir(self.repo_path)
            
            branch = self.branch_combo.currentText() if self.branch_combo.currentText() != "HEAD" else None
            search_term = self.search_edit.text().strip() if self.search_edit.text().strip() else None
            
            self.commit_table.setRowCount(0)
            
            # Build git log command with graph
            cmd = ["git", "log", "--graph", "--max-count=500", 
                   "--pretty=format:%x1f%H%x1f%h%x1f%an%x1f%ae%x1f%ad%x1f%s", 
                   "--date=iso", "--abbrev-commit"]
            
            if branch:
                cmd.append(branch)
            
            if search_term:
                cmd.extend(["--grep", search_term])
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode != 0:
                if "does not have any commits" not in result.stderr:
                    QMessageBox.warning(self, "Warning", f"Failed to load commits: {result.stderr}")
                return
            
            commits = []
            graph_pattern = re.compile(r'^([*\\/\-\s|\\]+)\s*\x1f')
            
            for line in result.stdout.split('\n'):
                if not line.strip():
                    continue
                
                # Extract graph part
                match = graph_pattern.match(line)
                if match:
                    graph = match.group(1)
                    # Remove graph from line to get commit data
                    commit_data = line[match.end():]
                    parts = commit_data.split('\x1f')
                    
                    if len(parts) >= 6:
                        commit = {
                            'graph': graph,
                            'hash': parts[0],
                            'short_hash': parts[1],
                            'author': parts[2],
                            'email': parts[3],
                            'date': parts[4],
                            'message': parts[5]
                        }
                        commits.append(commit)
                else:
                    # Fallback if pattern doesn't match
                    parts = line.strip().split('\x1f')
                    if len(parts) >= 6:
                        commit = {
                            'graph': '',
                            'hash': parts[0],
                            'short_hash': parts[1],
                            'author': parts[2],
                            'email': parts[3],
                            'date': parts[4],
                            'message': parts[5]
                        }
                        commits.append(commit)
            
            # Update table
            self.commit_table.setRowCount(len(commits))
            
            for i, commit in enumerate(commits):
                # Graph
                graph_item = QTableWidgetItem(commit['graph'])
                graph_item.setFont(QFont("Consolas, Monaco, monospace", 9))
                self.commit_table.setItem(i, 0, graph_item)
                
                # Short SHA
                self.commit_table.setItem(i, 1, QTableWidgetItem(commit['short_hash']))
                
                # Author
                self.commit_table.setItem(i, 2, QTableWidgetItem(commit['author']))
                
                # Date (format it nicely)
                try:
                    date_obj = datetime.fromisoformat(commit['date'].replace(' ', 'T'))
                    date_str = date_obj.strftime('%Y-%m-%d %H:%M')
                except:
                    date_str = commit['date']
                self.commit_table.setItem(i, 3, QTableWidgetItem(date_str))
                
                # Message (first line only)
                message = commit['message'].split('\n')[0]
                self.commit_table.setItem(i, 4, QTableWidgetItem(message))
                
                # Full SHA (hidden)
                self.commit_table.setItem(i, 5, QTableWidgetItem(commit['hash']))
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load commits: {str(e)}")
    
    def on_table_double_click(self):
        self.on_select()
    
    def on_select(self):
        current_row = self.commit_table.currentRow()
        if current_row >= 0:
            # Get full SHA from hidden column
            self.selected_commit = self.commit_table.item(current_row, 5).text()
            self.accept()
        else:
            QMessageBox.warning(self, "Warning", "Please select a commit.")
    
    def get_selected_commit(self):
        return self.selected_commit