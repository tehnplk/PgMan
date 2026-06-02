from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QAbstractTableModel, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QKeySequence, QShortcut
import time
from src.ui.QueryEditorUI import QueryEditorUI
from src.ui.UiUtils import resize_columns_fast, start_thread

class SqlTableModel(QAbstractTableModel):
    def __init__(self, columns=None, rows=None, parent=None):
        super().__init__(parent)
        self.cols = columns or []
        self.rows_data = rows or []

    def rowCount(self, parent=None):
        return len(self.rows_data)

    def columnCount(self, parent=None):
        return len(self.cols)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            val = self.rows_data[index.row()][index.column()]
            if val is None:
                return "[NULL]"
            return str(val)
        elif role == Qt.ItemDataRole.ForegroundRole:
            val = self.rows_data[index.row()][index.column()]
            if val is None:
                return QColor("#5c6370")
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.cols[section]
            else:
                return str(section + 1)
        return None


class QueryWorker(QThread):
    finished = pyqtSignal(object, object, str, float)  # (columns, rows, message, duration)
    failed = pyqtSignal(str, float)               # (error_message, duration)

    def __init__(self, db_engine, sql):
        super().__init__()
        self.db_engine = db_engine
        self.sql = sql

    def run(self):
        start_time = time.time()
        try:
            columns, rows, message = self.db_engine.execute_query(self.sql)
            duration = time.time() - start_time
            self.finished.emit(columns, rows, message, duration)
        except Exception as e:
            duration = time.time() - start_time
            self.failed.emit(str(e), duration)


class QueryEditorTab(QueryEditorUI):
    def __init__(self, db_engine, database_name, schema_name="public", parent=None):
        self.db_engine = db_engine
        super().__init__(database_name, schema_name, parent)
        
        # Load tables/views for autocompletion
        object_names = []
        try:
            tables = self.db_engine.get_tables(self.schema_name)
            views = self.db_engine.get_views(self.schema_name)
            object_names = tables + views
        except Exception:
            pass
            
        self.editor.set_autocomplete_words(object_names)
        self.editor.resolve_columns_callback = self.resolve_columns_for_alias
        self.column_cache = {}
        
        # Shortcuts for running query
        self.shortcut_return = QShortcut(QKeySequence("Ctrl+Shift+Return"), self)
        self.shortcut_return.activated.connect(self.run_query)
        self.shortcut_enter = QShortcut(QKeySequence("Ctrl+Shift+Enter"), self)
        self.shortcut_enter.activated.connect(self.run_query)
        
        self.run_btn.clicked.connect(self.run_query)
        self.worker = None

    def get_table_columns(self, table_name):
        if table_name in self.column_cache:
            return self.column_cache[table_name]
            
        try:
            cols_info = self.db_engine.get_columns(self.schema_name, table_name)
            cols = [col["name"] for col in cols_info]
            self.column_cache[table_name] = cols
            return cols
        except Exception:
            return []

    def resolve_columns_for_alias(self, alias):
        sql = self.editor.toPlainText()
        table_name = self.resolve_alias(sql, alias)
        if table_name:
            return self.get_table_columns(table_name)
        return []

    def resolve_alias(self, sql, alias):
        import re
        sql_clean = re.sub(r'--.*', '', sql)
        sql_clean = re.sub(r'/\*.*?\*/', '', sql_clean, flags=re.DOTALL)
        
        pattern = r'\b(FROM|JOIN)\s+(?:[a-zA-Z0-9_]+\.)?([a-zA-Z0-9_]+)(?:\s+AS)?\s+\b' + re.escape(alias) + r'\b'
        match = re.search(pattern, sql_clean, re.IGNORECASE)
        if match:
            return match.group(2)
        return alias

    def run_query(self):
        sql = self.editor.toPlainText().strip()
        if not sql:
            return

        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            sql = cursor.selectedText().replace('\u2029', '\n')

        self.run_btn.setEnabled(False)
        self.run_btn.setText("⏳ Executing...")
        self.message_log.clear()
        self.bottom_tabs.setCurrentIndex(1)
        self.message_log.append("Executing query...")

        self.worker = QueryWorker(self.db_engine, sql)
        self.worker.finished.connect(self.on_query_success)
        self.worker.failed.connect(self.on_query_failure)
        start_thread(self.worker)


    def on_query_success(self, columns, rows, message, duration):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("▶ Run")
        
        self.message_log.append(f"\n{message}")
        self.message_log.append(f"Execution time: {duration:.3f} s")

        if columns:
            model = SqlTableModel(columns, rows, self)
            self.results_view.setModel(model)
            resize_columns_fast(self.results_view, columns, rows)
            self.bottom_tabs.setCurrentIndex(0)
        else:
            self.results_view.setModel(None)
            self.bottom_tabs.setCurrentIndex(1)

    def on_query_failure(self, error_message, duration):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("▶ Run")
        
        self.message_log.append(f"\n❌ ERROR: {error_message}")
        self.message_log.append(f"Execution time: {duration:.3f} s")
        self.bottom_tabs.setCurrentIndex(1)
