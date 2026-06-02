from PyQt6.QtWidgets import QTreeWidget
from PyQt6.QtCore import Qt, pyqtSignal

class DbTreeUI(QTreeWidget):
    # Signals to communicate actions back to main window
    open_query_editor_signal = pyqtSignal(object, str, str, str)  # (db_engine, database_name, schema_name, initial_sql)
    open_table_viewer_signal = pyqtSignal(object, str, str, str) # (db_engine, database_name, schema_name, table_name)
    open_object_tab_signal = pyqtSignal(object, str, str, str, dict) # (db_engine, database_name, schema_name, group_name, profile)
    connection_changed_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("Database Explorer")
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setIndentation(15)  # Indentation for hierarchy
