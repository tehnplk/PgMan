from PyQt6.QtWidgets import QMessageBox, QDialog
from PyQt6.QtCore import Qt

from src.ui.MainWindowUI import MainWindowUI
from src.ui.ConnectionDlgLogic import ConnectionDialog
from src.ui.QueryEditorLogic import QueryEditorTab
from src.ui.TableViewerLogic import TableViewerTab
from src.ui.ObjectTabLogic import ObjectTab
from src.ui.TableDesignerLogic import TableDesignerTab
from src.DbEngine import DbEngine
import src.Config as config
from src.ui.UiUtils import show_exception_dialog

class MainWindow(MainWindowUI):
    def __init__(self):
        super().__init__()
        
        # Connect visual buttons to handlers
        self.new_conn_btn.clicked.connect(self.open_new_connection_dialog)
        self.new_query_btn.clicked.connect(self.open_new_query_editor)
        self.theme_btn.clicked.connect(self.toggle_theme)

        # Initialize theme button label from settings
        from PyQt6.QtCore import QSettings
        settings = QSettings("PgMan", "ThemeSettings")
        theme = settings.value("theme", "dark")
        if theme == "dark":
            self.theme_btn.setText("🌙 Dark Mode")
        else:
            self.theme_btn.setText("☀ Light Mode")
        
        # Connect tree signals
        self.tree.open_query_editor_signal.connect(self.add_query_tab)
        self.tree.open_table_viewer_signal.connect(self.add_table_tab)
        self.tree.open_object_tab_signal.connect(self.add_or_update_object_tab)
        self.tree.open_table_designer_signal.connect(self.add_designer_tab)
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
                    sslmode=profile.get("sslmode", "prefer"),
                    db_type=profile.get("db_type", "PostgreSQL"),
                    charset=profile.get("charset", "")
                )
                engine.connect()
                self.tree.db_engines[engine_key] = engine
            except Exception as e:
                show_exception_dialog(self, "Connection Error", f"Failed to connect to database '{dbname}':\n{str(e)}")
                return

        self.add_query_tab(engine, dbname, schema, "")

    def add_query_tab(self, db_engine, dbname, schema, initial_sql=""):
        tab = QueryEditorTab(db_engine, dbname, schema, self)
        if initial_sql:
            tab.editor.setPlainText(initial_sql)
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(initial_sql)
            status_msg = "DDL/SQL definition copied to clipboard."
        else:
            status_msg = f"Opened query tab for database: {dbname}"
            
        index = self.tabs.addTab(tab, f"Query [{dbname}]")
        self.tabs.setCurrentIndex(index)
        self.status.showMessage(status_msg)

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

    def add_or_update_object_tab(self, db_engine, dbname, schema, group_name, profile):
        # Find if tab named "Object" already exists
        object_tab_idx = -1
        existing_tab = None
        for idx in range(self.tabs.count()):
            if self.tabs.tabText(idx) == "Object":
                object_tab_idx = idx
                existing_tab = self.tabs.widget(idx)
                break
                
        if existing_tab and isinstance(existing_tab, ObjectTab):
            existing_tab.update_data(db_engine, dbname, schema, group_name, profile)
            self.tabs.setCurrentIndex(object_tab_idx)
        else:
            tab = ObjectTab(db_engine, dbname, schema, group_name, profile, self)
            tab.open_table_signal.connect(self.add_table_tab)
            tab.open_query_signal.connect(self.add_query_tab)
            tab.open_designer_signal.connect(self.add_designer_tab)
            if object_tab_idx != -1:
                self.tabs.insertTab(object_tab_idx, tab, "Object")
                self.tabs.removeTab(object_tab_idx + 1)
                self.tabs.setCurrentIndex(object_tab_idx)
            else:
                index = self.tabs.addTab(tab, "Object")
                self.tabs.setCurrentIndex(index)
        self.status.showMessage(f"Listing {group_name} in {schema} under 'Object' tab")

    def add_designer_tab(self, db_engine, dbname, schema, table_name, is_new_table=False):
        # Check if designer for same table already open
        for idx in range(self.tabs.count()):
            widget = self.tabs.widget(idx)
            if isinstance(widget, TableDesignerTab):
                if widget.dbname == dbname and widget.schema == schema and widget.table_name == table_name:
                    self.tabs.setCurrentIndex(idx)
                    return

        tab = TableDesignerTab(db_engine, dbname, schema, table_name, self, is_new_table=is_new_table)
        tab_title = f"🛠 {table_name} (New)" if is_new_table else f"🛠 {table_name}"
        index = self.tabs.addTab(tab, tab_title)
        self.tabs.setCurrentIndex(index)
        if is_new_table:
            self.status.showMessage(f"Opened Table Designer to create: {schema}.{table_name}")
        else:
            self.status.showMessage(f"Opened Table Designer for: {schema}.{table_name}")

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

    def toggle_theme(self):
        from PyQt6.QtCore import QSettings
        from PyQt6.QtWidgets import QApplication
        from src.ui.Stylesheets import get_theme_qss
        
        settings = QSettings("PgMan", "ThemeSettings")
        current_theme = settings.value("theme", "dark")
        
        # Toggle theme value
        new_theme = "light" if current_theme == "dark" else "dark"
        settings.setValue("theme", new_theme)
        
        # Apply the style globally
        QApplication.instance().setStyleSheet(get_theme_qss(new_theme))
        
        # Update theme button label
        if new_theme == "dark":
            self.theme_btn.setText("🌙 Dark Mode")
        else:
            self.theme_btn.setText("☀ Light Mode")
        
        # Update cached theme in any active TableViewerTab models
        from src.ui.TableViewerLogic import TableViewerTab
        for idx in range(self.tabs.count()):
            w = self.tabs.widget(idx)
            if isinstance(w, TableViewerTab) and hasattr(w, "model"):
                w.model._cached_theme = new_theme.lower()
                w.model.layoutChanged.emit()
            
        self.status.showMessage(f"Switched to {new_theme} mode.")
