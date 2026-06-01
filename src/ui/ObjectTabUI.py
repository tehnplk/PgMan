from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QListWidget, QLineEdit, QLabel, QHeaderView,
    QPushButton, QStackedWidget, QButtonGroup
)
from PyQt6.QtCore import Qt, QSize

class ObjectTabUI(QWidget):
    def __init__(self, dbname, schema, group_name, parent=None):
        super().__init__(parent)
        self.dbname = dbname
        self.schema = schema
        self.group_name = group_name  # "Tables", "Views", or "Functions"
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Top Bar: Header, Search, View Toggles
        top_bar = QHBoxLayout()
        
        self.header_lbl = QLabel(f"📂 {self.group_name} in {self.schema}")
        self.header_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #00e5ff; background: transparent;")
        top_bar.addWidget(self.header_lbl)
        
        top_bar.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search objects...")
        self.search_input.setFixedWidth(200)
        top_bar.addWidget(self.search_input)

        # View Toggles
        self.btn_detail = QPushButton("📊 Detail")
        self.btn_list = QPushButton("📋 List")
        self.btn_grid = QPushButton("🔲 Grid")
        
        self.btn_detail.setCheckable(True)
        self.btn_list.setCheckable(True)
        self.btn_grid.setCheckable(True)
        
        self.btn_detail.setChecked(True)
        
        # Exclusive Button Group
        self.view_group = QButtonGroup(self)
        self.view_group.addButton(self.btn_detail)
        self.view_group.addButton(self.btn_list)
        self.view_group.addButton(self.btn_grid)
        self.view_group.setExclusive(True)
        
        top_bar.addWidget(self.btn_detail)
        top_bar.addWidget(self.btn_list)
        top_bar.addWidget(self.btn_grid)
        layout.addLayout(top_bar)

        # Central Stacked Widget
        self.stack = QStackedWidget()
        
        # 1. Detail View: Table Widget (columns: Name, Type, Rows, Size)
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(4)
        self.table_widget.setHorizontalHeaderLabels(["Name", "Type", "Rows", "Size"])
        self.table_widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table_widget.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table_widget.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.table_widget.setColumnWidth(1, 100)
        self.table_widget.setColumnWidth(2, 100)
        self.table_widget.setColumnWidth(3, 100)
        self.table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_widget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_widget.verticalHeader().setVisible(False)
        self.table_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.stack.addWidget(self.table_widget)

        # 2. List View: QListWidget in ListMode
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list_widget.setEditTriggers(QListWidget.EditTrigger.NoEditTriggers)
        self.list_widget.setViewMode(QListWidget.ViewMode.ListMode)
        self.list_widget.setIconSize(QSize(20, 20))
        self.list_widget.setSpacing(2)
        self.list_widget.setWrapping(False)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.stack.addWidget(self.list_widget)

        # 3. Grid View: QListWidget flowing horizontally in ListMode (small icons, left-aligned)
        self.grid_widget = QListWidget()
        self.grid_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.grid_widget.setEditTriggers(QListWidget.EditTrigger.NoEditTriggers)
        self.grid_widget.setViewMode(QListWidget.ViewMode.ListMode)
        self.grid_widget.setFlow(QListWidget.Flow.LeftToRight)
        self.grid_widget.setWrapping(True)
        self.grid_widget.setIconSize(QSize(20, 20))
        self.grid_widget.setGridSize(QSize(220, 30))
        self.grid_widget.setSpacing(6)
        self.grid_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.stack.addWidget(self.grid_widget)
        
        layout.addWidget(self.stack)

        # Status Bar
        self.status_lbl = QLabel("Total: 0 objects")
        self.status_lbl.setStyleSheet("color: #5c6370; font-size: 11px; background: transparent;")
        layout.addWidget(self.status_lbl)
