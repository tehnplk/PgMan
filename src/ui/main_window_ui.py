from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QTabWidget, QToolBar,
    QPushButton, QStatusBar, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from src.ui.db_tree_logic import DbTreeWidget
from src.ui.stylesheets import get_resource_path

class MainWindowUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PgMan - PostgreSQL Client")
        self.resize(1100, 750)
        self.setWindowIcon(QIcon(get_resource_path("resources/app_icon.png")))
        self.init_ui()

    def init_ui(self):
        # 1. Toolbar
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        self.new_conn_btn = QPushButton("➕ Connection")
        self.toolbar.addWidget(self.new_conn_btn)

        self.toolbar.addSeparator()

        self.new_query_btn = QPushButton("📄 New Query")
        self.toolbar.addWidget(self.new_query_btn)

        # 2. Main Central Splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Side Tree
        self.tree = DbTreeWidget(self)
        main_splitter.addWidget(self.tree)

        # Right Side Closable Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        main_splitter.addWidget(self.tabs)

        # Set ratio (25% Tree, 75% Tabs)
        main_splitter.setSizes([250, 850])

        self.setCentralWidget(main_splitter)

        # 3. Status Bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")
