from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QToolBar, QSplitter, QPlainTextEdit,
    QHeaderView, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt


class TableDesignerUI(QWidget):
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

        self.save_btn = QPushButton("💾 Save")
        self.save_btn.setObjectName("saveBtn")
        self.toolbar.addWidget(self.save_btn)

        self.toolbar.addSeparator()

        self.add_col_btn = QPushButton("➕ Add Column")
        self.toolbar.addWidget(self.add_col_btn)

        self.del_col_btn = QPushButton("❌ Remove Column")
        self.toolbar.addWidget(self.del_col_btn)

        self.toolbar.addSeparator()

        self.move_up_btn = QPushButton("⬆ Move Up")
        self.toolbar.addWidget(self.move_up_btn)

        self.move_down_btn = QPushButton("⬇ Move Down")
        self.toolbar.addWidget(self.move_down_btn)

        self.toolbar.addSeparator()

        self.refresh_btn = QPushButton("↺ Refresh")
        self.toolbar.addWidget(self.refresh_btn)

        layout.addWidget(self.toolbar)

        # Main content: splitter between column grid and SQL preview
        self.splitter = QSplitter(Qt.Orientation.Vertical)

        # Column Grid
        self.column_table = QTableWidget()
        self.column_table.setColumnCount(8)
        self.column_table.setHorizontalHeaderLabels([
            "Column Name", "Type", "Length", "Not Null", "Default", "Primary Key",
            "Auto Increment", "Comment"
        ])
        self.column_table.horizontalHeader().setStretchLastSection(True)
        self.column_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.column_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.column_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.column_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.column_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self.column_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.column_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.column_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)

        # Set fixed/interactive widths for columns
        self.column_table.setColumnWidth(0, 180) # Column Name
        self.column_table.setColumnWidth(1, 130) # Type
        self.column_table.setColumnWidth(2, 70)  # Length
        self.column_table.setColumnWidth(3, 70)  # Not Null
        self.column_table.setColumnWidth(4, 130) # Default
        self.column_table.setColumnWidth(5, 85)  # Primary Key
        self.column_table.setColumnWidth(6, 105) # Auto Increment

        self.column_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.column_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.column_table.verticalHeader().setDefaultSectionSize(28)

        self.splitter.addWidget(self.column_table)

        # SQL Preview
        sql_container = QWidget()
        sql_layout = QVBoxLayout(sql_container)
        sql_layout.setContentsMargins(4, 4, 4, 4)
        sql_layout.setSpacing(2)

        self.sql_label = QLabel("📋 SQL Preview (ALTER TABLE statements)")
        sql_layout.addWidget(self.sql_label)

        self.sql_preview = QPlainTextEdit()
        self.sql_preview.setReadOnly(True)
        self.sql_preview.setMaximumHeight(180)
        self.sql_preview.setPlaceholderText("No changes to preview.")
        sql_layout.addWidget(self.sql_preview)

        self.splitter.addWidget(sql_container)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)

        layout.addWidget(self.splitter)

        # Status Bar
        self.status_lbl = QLabel(f"🛠 Design: {self.schema}.{self.table_name}")
        self.status_lbl.setObjectName("dataViewerStatusBar")
        layout.addWidget(self.status_lbl)
