from PyQt6.QtWidgets import QMessageBox, QDialog
from PyQt6.QtCore import Qt

from src.ui.main_window_ui import MainWindowUI
from src.ui.connection_dlg_logic import ConnectionDialog
from src.ui.query_editor_logic import QueryEditorTab
from src.ui.table_viewer_logic import TableViewerTab
from src.db_engine import DbEngine
import src.config as config

class MainWindow(MainWindowUI):
    def __init__(self):
        super().__init__()
        
        # Connect visual buttons to handlers
        self.new_conn_btn.clicked.connect(self.open_new_connection_dialog)
        self.new_query_btn.clicked.connect(self.open_new_query_editor)
        
        # Connect tree signals
        self.tree.open_query_editor_signal.connect(self.add_query_tab)
        self.tree.open_table_viewer_signal.connect(self.add_table_tab)
        self.tabs.tabCloseRequested.connect(self.close_tab)

    def open_new_connection_dialog(self):
        dlg = ConnectionDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            profile = dlg.get_data()
            config.add_or_update_profile(profile)
            self.tree.load_profiles()
            self.status.showMessage("Connection profile saved.")

    def open_new_query_editor(self):
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
        tab = QueryEditorTab(db_engine, dbname, schema, self)
        if initial_sql:
            tab.editor.setPlainText(initial_sql)
        index = self.tabs.addTab(tab, f"Query [{dbname}]")
        self.tabs.setCurrentIndex(index)
        self.status.showMessage(f"Opened query tab for database: {dbname}")

    def add_table_tab(self, db_engine, dbname, schema, table_name):
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
