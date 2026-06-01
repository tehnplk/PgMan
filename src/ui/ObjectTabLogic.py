from PyQt6.QtWidgets import QTableWidgetItem, QListWidgetItem, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QCursor, QPixmap, QPainter, QFont, QIcon
import re

from src.ui.ObjectTabUI import ObjectTabUI
from src.ui.UiUtils import show_exception_dialog

def emoji_to_icon(emoji):
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 96):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        font = QFont("Segoe UI Emoji", int(size * 0.75))
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, emoji)
        painter.end()
        
        icon.addPixmap(pixmap)
    return icon

class ObjectTab(ObjectTabUI):
    open_table_signal = pyqtSignal(object, str, str, str)  # (db_engine, dbname, schema, table_name)
    open_query_signal = pyqtSignal(object, str, str, str)  # (db_engine, dbname, schema, initial_sql)

    def __init__(self, db_engine, dbname, schema, group_name, children, parent=None):
        super().__init__(dbname, schema, group_name, parent)
        self.db_engine = db_engine
        self.children = children
        
        self.profile = None
        if children:
            self.profile = children[0]["data"].get("profile")
        
        # Cache emoji icon
        emoji_map = {
            "Tables": "📊",
            "Views": "👁️",
            "Functions": "⚙️"
        }
        self.emoji = emoji_map.get(self.group_name, "📄")
        self.cached_icon = emoji_to_icon(self.emoji)
        
        self.populate_data()
        
        # Load and apply saved view style
        from PyQt6.QtCore import QSettings
        settings = QSettings("PgMan", "ObjectTabSettings")
        view_style = settings.value("view_style", "detail")
        if view_style == "list":
            self.set_view_list()
        elif view_style == "grid":
            self.set_view_grid()
        else:
            self.set_view_detail()
        
        # Connect signals
        self.search_input.textChanged.connect(self.filter_objects)
        self.table_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.list_widget.itemDoubleClicked.connect(self.on_list_item_double_clicked)
        self.grid_widget.itemDoubleClicked.connect(self.on_list_item_double_clicked)
        
        # View switches
        self.btn_detail.clicked.connect(self.set_view_detail)
        self.btn_list.clicked.connect(self.set_view_list)
        self.btn_grid.clicked.connect(self.set_view_grid)
        self.btn_refresh.clicked.connect(self.refresh_data)

    def populate_data(self):
        # Build lookup of child user data by name
        children_lookup = {child["name"]: child["data"] for child in self.children}

        # 1. Populate Table (Detail view)
        self.table_widget.setRowCount(0)
        
        if self.group_name == "Tables":
            # Fetch detailed table list (with rows and size)
            tables_detailed = self.db_engine.get_tables_detailed(self.schema)
            self.table_widget.setRowCount(len(tables_detailed))
            
            for idx, table in enumerate(tables_detailed):
                name = table["name"]
                rows_count = table["rows"]
                size_str = table["size"]
                child_data = children_lookup.get(name)
                
                # Column 0: Name with icon
                name_item = QTableWidgetItem(name)
                name_item.setIcon(self.cached_icon)
                name_item.setData(Qt.ItemDataRole.UserRole, child_data)
                self.table_widget.setItem(idx, 0, name_item)
                
                # Column 1: Type
                type_item = QTableWidgetItem("Table")
                self.table_widget.setItem(idx, 1, type_item)
                
                # Column 2: Rows
                rows_item = QTableWidgetItem(rows_count)
                self.table_widget.setItem(idx, 2, rows_item)
                
                # Column 3: Size
                size_item = QTableWidgetItem(size_str)
                self.table_widget.setItem(idx, 3, size_item)
        else:
            # Views or Functions (Rows and Size are "-")
            self.table_widget.setRowCount(len(self.children))
            for idx, child in enumerate(self.children):
                name = child["name"]
                child_data = child["data"]
                
                # Column 0: Name with icon
                name_item = QTableWidgetItem(name)
                name_item.setIcon(self.cached_icon)
                name_item.setData(Qt.ItemDataRole.UserRole, child_data)
                self.table_widget.setItem(idx, 0, name_item)
                
                # Column 1: Type
                type_str = self.group_name.rstrip("s")
                type_item = QTableWidgetItem(type_str)
                self.table_widget.setItem(idx, 1, type_item)
                
                # Column 2: Rows
                rows_item = QTableWidgetItem("-")
                self.table_widget.setItem(idx, 2, rows_item)
                
                # Column 3: Size
                size_item = QTableWidgetItem("-")
                self.table_widget.setItem(idx, 3, size_item)
            
        # 2. Populate List View
        self.list_widget.clear()
        # 3. Populate Grid View
        self.grid_widget.clear()
        
        for child in self.children:
            name = child["name"]
            child_data = child["data"]
            
            # List item
            list_item = QListWidgetItem(name)
            list_item.setIcon(self.cached_icon)
            list_item.setData(Qt.ItemDataRole.UserRole, child_data)
            self.list_widget.addItem(list_item)
            
            # Grid item
            grid_item = QListWidgetItem(name)
            grid_item.setIcon(self.cached_icon)
            grid_item.setData(Qt.ItemDataRole.UserRole, child_data)
            self.grid_widget.addItem(grid_item)
            
        self.status_lbl.setText(f"Total: {len(self.children)} {self.group_name.lower()}")

    def set_view_detail(self):
        self.stack.setCurrentIndex(0)
        self.btn_detail.setChecked(True)
        from PyQt6.QtCore import QSettings
        QSettings("PgMan", "ObjectTabSettings").setValue("view_style", "detail")

    def set_view_list(self):
        self.stack.setCurrentIndex(1)
        self.btn_list.setChecked(True)
        from PyQt6.QtCore import QSettings
        QSettings("PgMan", "ObjectTabSettings").setValue("view_style", "list")

    def set_view_grid(self):
        self.stack.setCurrentIndex(2)
        self.btn_grid.setChecked(True)
        from PyQt6.QtCore import QSettings
        QSettings("PgMan", "ObjectTabSettings").setValue("view_style", "grid")

    def filter_objects(self):
        query = self.search_input.text().lower()
        visible_count = 0
        
        # Filter table rows
        for row in range(self.table_widget.rowCount()):
            name_item = self.table_widget.item(row, 0)
            if name_item:
                name_text = name_item.text().lower()
                if query in name_text:
                    self.table_widget.setRowHidden(row, False)
                    visible_count += 1
                else:
                    self.table_widget.setRowHidden(row, True)
                    
        # Filter list items
        for idx in range(self.list_widget.count()):
            item = self.list_widget.item(idx)
            if item:
                name_text = item.text().lower()
                if query in name_text:
                    item.setHidden(False)
                else:
                    item.setHidden(True)
                    
        # Filter grid items
        for idx in range(self.grid_widget.count()):
            item = self.grid_widget.item(idx)
            if item:
                name_text = item.text().lower()
                if query in name_text:
                    item.setHidden(False)
                else:
                    item.setHidden(True)
                    
        total = len(self.children)
        if query:
            self.status_lbl.setText(f"Total: {total} | Filtered: {visible_count} {self.group_name.lower()}")
        else:
            self.status_lbl.setText(f"Total: {total} {self.group_name.lower()}")

    def on_item_double_clicked(self, item):
        row = item.row()
        name_item = self.table_widget.item(row, 0)
        if name_item:
            data = name_item.data(Qt.ItemDataRole.UserRole)
            self.open_object_with_data(data)

    def on_list_item_double_clicked(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        self.open_object_with_data(data)

    def open_object_with_data(self, data):
        if not data:
            return
            
        node_type = data.get("type")
        if node_type in ("table", "view"):
            table_name = data["table_name"]
            self.open_table_signal.emit(self.db_engine, self.dbname, self.schema, table_name)
        elif node_type == "function":
            func_name = data["func_name"]
            
            self.setCursor(QCursor(Qt.CursorShape.WaitCursor))
            try:
                sql_def = self.db_engine.get_function_definition(self.schema, func_name)
                self.open_query_signal.emit(self.db_engine, self.dbname, self.schema, sql_def)
            except Exception as e:
                show_exception_dialog(self, "Error", f"Could not retrieve function definition:\n{str(e)}")
            finally:
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def update_data(self, db_engine, dbname, schema, group_name, children):
        self.db_engine = db_engine
        self.dbname = dbname
        self.schema = schema
        self.group_name = group_name
        self.children = children
        self.profile = None
        if children:
            self.profile = children[0]["data"].get("profile")
        
        emoji_map = {
            "Tables": "📊",
            "Views": "👁️",
            "Functions": "⚙️"
        }
        self.emoji = emoji_map.get(self.group_name, "📄")
        self.cached_icon = emoji_to_icon(self.emoji)
        
        self.header_lbl.setText(f"📂 {self.group_name} in {self.schema}")
        
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)
        
        self.populate_data()

    def refresh_data(self):
        self.setCursor(QCursor(Qt.CursorShape.WaitCursor))
        try:
            # Clear metadata cache in DbEngine
            self.db_engine.clear_cache()
            
            # Fetch fresh metadata list
            children = []
            if self.group_name == "Tables":
                tables = self.db_engine.get_tables(self.schema)
                for t in tables:
                    children.append({
                        "name": t,
                        "data": {
                            "type": "table",
                            "profile": self.profile,
                            "dbname": self.dbname,
                            "schema": self.schema,
                            "table_name": t
                        }
                    })
            elif self.group_name == "Views":
                views = self.db_engine.get_views(self.schema)
                for v in views:
                    children.append({
                        "name": v,
                        "data": {
                            "type": "view",
                            "profile": self.profile,
                            "dbname": self.dbname,
                            "schema": self.schema,
                            "table_name": v
                        }
                    })
            elif self.group_name == "Functions":
                funcs = self.db_engine.get_functions(self.schema)
                for f in funcs:
                    children.append({
                        "name": f,
                        "data": {
                            "type": "function",
                            "profile": self.profile,
                            "dbname": self.dbname,
                            "schema": self.schema,
                            "func_name": f
                        }
                    })
            
            self.children = children
            self.populate_data()
            
            # Keep search filter applied
            self.filter_objects()
            
        except Exception as e:
            show_exception_dialog(self, "Error", f"Failed to refresh data:\n{str(e)}")
        finally:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
