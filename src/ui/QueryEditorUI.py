from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QPlainTextEdit,
    QTableView, QTabWidget, QTextEdit, QPushButton, QLabel, QToolBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from src.ui.SyntaxHighlighter import SQLHighlighter

class QueryEditorUI(QWidget):
    def __init__(self, database_name, schema_name="public", parent=None):
        super().__init__(parent)
        self.database_name = database_name
        self.schema_name = schema_name
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        self.toolbar = QToolBar()
        self.run_btn = QPushButton("▶ Run")
        self.run_btn.setObjectName("runBtn")
        self.toolbar.addWidget(self.run_btn)

        self.toolbar.addSeparator()
        self.status_label = QLabel(f"Connected to: {self.database_name} ({self.schema_name})")
        self.status_label.setStyleSheet("color: #abb2bf; padding-left: 10px;")
        self.toolbar.addWidget(self.status_label)

        layout.addWidget(self.toolbar)

        # Splitter between Editor and Results
        splitter = QSplitter(Qt.Orientation.Vertical)

        # SQL Editor
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("SELECT * FROM schema.table LIMIT 100;")
        
        # Set code font
        font = QFont("Consolas", 11)
        if not font.exactMatch():
            font = QFont("Courier New", 11)
        self.editor.setFont(font)
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        # Set Syntax Highlighter
        self.highlighter = SQLHighlighter(self.editor.document())
        splitter.addWidget(self.editor)

        # Bottom Area Tabs (Results vs Messages)
        self.bottom_tabs = QTabWidget()
        
        # Results grid
        self.results_view = QTableView()
        self.bottom_tabs.addTab(self.results_view, "Results")

        # Messages log
        self.message_log = QTextEdit()
        self.message_log.setReadOnly(True)
        self.message_log.setFont(font)
        self.bottom_tabs.addTab(self.message_log, "Messages")

        splitter.addWidget(self.bottom_tabs)
        
        # Set splitter sizes (approx 40% editor, 60% results)
        splitter.setSizes([300, 450])
        layout.addWidget(splitter)
