from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QTabWidget, QToolBar,
    QPushButton, QStatusBar, QWidget, QHBoxLayout, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from src.ui.db_tree import DbTreeWidget
from src.ui.connection_dlg import ConnectionDialog
from src.ui.query_editor import QueryEditorTab
from src.ui.table_viewer import TableViewerTab
from src.ui.stylesheets import get_resource_path
import src.config as config
from src.db_engine import DbEngine

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PgMan - PostgreSQL Client")
        self.resize(1100, 750)
        self.setWindowIcon(QIcon(get_resource_path("resources/app_icon.png")))
        self.init_ui()

    def init_ui(self):
        # 1. Toolbar
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.new_conn_btn = QPushButton("➕ Connection")
        self.new_conn_btn.clicked.connect(self.open_new_connection_dialog)
        toolbar.addWidget(self.new_conn_btn)

        toolbar.addSeparator()

        self.new_query_btn = QPushButton("📄 New Query")
        self.new_query_btn.clicked.connect(self.open_new_query_editor)
        toolbar.addWidget(self.new_query_btn)

        # 2. Main Central Splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Side Tree
        self.tree = DbTreeWidget(self)
        self.tree.open_query_editor_signal.connect(self.add_query_tab)
        self.tree.open_table_viewer_signal.connect(self.add_table_tab)
        main_splitter.addWidget(self.tree)

        # Right Side Closable Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        main_splitter.addWidget(self.tabs)

        # Set ratio (25% Tree, 75% Tabs)
        main_splitter.setSizes([250, 850])

        self.setCentralWidget(main_splitter)

        # 3. Status Bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")

    def open_new_connection_dialog(self):
        dlg = ConnectionDialog(self)
        if dlg.exec() == ConnectionDialog.DialogCode.Accepted:
            profile = dlg.get_data()
            config.add_or_update_profile(profile)
            self.tree.load_profiles()
            self.status.showMessage("Connection profile saved.")

    def open_new_query_editor(self):
        # Determine if we have a selected database connection
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, "Select Database", "Please click/select a database or schema in the explorer tree first.")
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            QMessageBox.warning(self, "Select Database", "Please select a database or schema in the explorer tree first.")
            return

        profile = data.get("profile")
        dbname = data.get("dbname")
        schema = data.get("schema", "public")

        if not profile or not dbname:
            QMessageBox.warning(self, "Select Database", "Please select a database or schema in the explorer tree first.")
            return

        # Fetch active connection engine or construct a new one
        engine_key = (profile["id"], dbname)
        engine = self.tree.db_engines.get(engine_key)
        if not engine:
            try:
                engine = DbEngine(
                    host=profile["host"],
                    port=profile["port"],
                    database=dbname,
                    username=profile["username"],
                    password=profile["password"],
                    sslmode=profile["sslmode"]
                )
                engine.connect()
                self.tree.db_engines[engine_key] = engine
            except Exception as e:
                QMessageBox.critical(self, "Connection Error", f"Failed to connect to database '{dbname}':\n{str(e)}")
                return

        self.add_query_tab(engine, dbname, schema, "")

    def add_query_tab(self, db_engine, dbname, schema, initial_sql=""):
        # Open query tab
        tab = QueryEditorTab(db_engine, dbname, schema, self)
        if initial_sql:
            tab.editor.setPlainText(initial_sql)
        index = self.tabs.addTab(tab, f"Query [{dbname}]")
        self.tabs.setCurrentIndex(index)
        self.status.showMessage(f"Opened query tab for database: {dbname}")

    def add_table_tab(self, db_engine, dbname, schema, table_name):
        # Open table tab
        # Check if tab is already open for this table to avoid duplicates
        for idx in range(self.tabs.count()):
            widget = self.tabs.widget(idx)
            if isinstance(widget, TableViewerTab):
                if widget.dbname == dbname and widget.schema == schema and widget.table_name == table_name:
                    self.tabs.setCurrentIndex(idx)
                    return

        tab = TableViewerTab(db_engine, dbname, schema, table_name, self)
        index = self.tabs.addTab(tab, f"{schema}.{table_name}")
        self.tabs.setCurrentIndex(index)
        self.status.showMessage(f"Opened table viewer for: {schema}.{table_name}")

    def close_tab(self, index):
        widget = self.tabs.widget(index)
        if widget:
            # If it's a table viewer, check if there are pending edits
            if isinstance(widget, TableViewerTab) and hasattr(widget, "model"):
                updates, inserts, deletes = widget.model.get_pending_changes()
                if updates or inserts or deletes:
                    reply = QMessageBox.question(
                        self, "Unsaved Changes",
                        f"Table '{widget.schema}.{widget.table_name}' has pending uncommitted changes. Close anyway?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.No:
                        return
            
            widget.deleteLater()
        self.tabs.removeTab(index)
