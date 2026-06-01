from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView,
    QPushButton, QComboBox, QLabel, QToolBar
)

class TableViewerUI(QWidget):
    def __init__(self, dbname, schema, table_name, parent=None):
        super().__init__(parent)
        self.dbname = dbname
        self.schema = schema
        self.table_name = table_name
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        self.toolbar = QToolBar()
        
        self.add_btn = QPushButton("➕ Add Row")
        self.toolbar.addWidget(self.add_btn)
        
        self.delete_btn = QPushButton("❌ Delete Row")
        self.toolbar.addWidget(self.delete_btn)

        self.toolbar.addSeparator()

        self.commit_btn = QPushButton("✔ Commit")
        self.commit_btn.setObjectName("saveBtn")
        self.toolbar.addWidget(self.commit_btn)
        
        self.refresh_btn = QPushButton("↺ Refresh")
        self.toolbar.addWidget(self.refresh_btn)

        # Spacer in toolbar
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().Policy.Expanding, spacer.sizePolicy().Policy.Preferred)
        self.toolbar.addWidget(spacer)

        # Pagination controls
        self.first_page_btn = QPushButton("|<")
        self.toolbar.addWidget(self.first_page_btn)

        self.prev_page_btn = QPushButton("<")
        self.toolbar.addWidget(self.prev_page_btn)

        self.page_label = QLabel("Page 1 of 1")
        self.page_label.setStyleSheet("padding: 0px 8px; color: #abb2bf;")
        self.toolbar.addWidget(self.page_label)

        self.next_page_btn = QPushButton(">")
        self.toolbar.addWidget(self.next_page_btn)

        self.last_page_btn = QPushButton(">|")
        self.toolbar.addWidget(self.last_page_btn)

        self.toolbar.addSeparator()
        
        self.limit_combo = QComboBox()
        self.limit_combo.addItems(["100", "500", "1000"])
        self.toolbar.addWidget(self.limit_combo)

        layout.addWidget(self.toolbar)

        # Main Table View
        self.table_view = QTableView()
        layout.addWidget(self.table_view)

        # Status Bar
        self.status_bar_lbl = QLabel(f"Table: {self.schema}.{self.table_name} | Rows: 0")
        self.status_bar_lbl.setStyleSheet("padding: 4px; color: #5c6370; background-color: #21252b;")
        layout.addWidget(self.status_bar_lbl)
