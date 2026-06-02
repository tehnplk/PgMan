from PyQt6.QtWidgets import QTableWidgetItem, QListWidgetItem, QMessageBox, QMenu, QTableWidget, QInputDialog
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRectF, QThread
from PyQt6.QtGui import QCursor, QPixmap, QPainter, QFont, QIcon, QImage
import re

from src.ui.ObjectTabUI import ObjectTabUI
from src.ui.UiUtils import show_exception_dialog, start_thread

class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, text, val=None):
        super().__init__(text)
        self.val = val

    def __lt__(self, other):
        if not isinstance(other, NumericTableWidgetItem):
            return super().__lt__(other)
            
        v1 = self.val
        v2 = other.val
        
        if v1 is None and v2 is None:
            return False
        if v1 is None:
            return True
        if v2 is None:
            return False
            
        t1 = type(v1)
        t2 = type(v2)
        
        if t1 == t2:
            try:
                return v1 < v2
            except Exception:
                return str(v1) < str(v2)
                
        is_num1 = isinstance(v1, (int, float))
        is_num2 = isinstance(v2, (int, float))
        
        if is_num1 and is_num2:
            return v1 < v2
        elif is_num1:
            return True
        elif is_num2:
            return False
        else:
            return str(v1) < str(v2)

def parse_size_to_bytes(size_str):
    if not size_str or size_str == "-":
        return -1
    parts = size_str.split()
    if len(parts) < 2:
        return 0
    try:
        val = float(parts[0])
        unit = parts[1].upper()
        multipliers = {
            "BYTES": 1,
            "KB": 1024,
            "MB": 1024 * 1024,
            "GB": 1024 * 1024 * 1024,
            "TB": 1024 * 1024 * 1024 * 1024,
            "PB": 1024 * 1024 * 1024 * 1024 * 1024
        }
        return int(val * multipliers.get(unit, 1))
    except Exception:
        return 0

def emoji_to_icon(emoji):
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 96):
        render_size = max(128, size * 2)
        image = QImage(render_size, render_size, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(image)
        font = QFont("Segoe UI Emoji", int(render_size * 0.85))
        painter.setFont(font)
        painter.drawText(image.rect(), Qt.AlignmentFlag.AlignCenter, emoji)
        painter.end()
        
        # Scan for bounding box of non-transparent pixels (alpha > 10)
        min_y = -1
        for y in range(render_size):
            row_has_alpha = False
            for x in range(render_size):
                if ((image.pixel(x, y) >> 24) & 0xFF) > 10:
                    row_has_alpha = True
                    break
            if row_has_alpha:
                min_y = y
                break
        
        if min_y == -1:
            # Fallback to simple rendering if crop fails or emoji is empty
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            font = QFont("Segoe UI Emoji", int(size * 0.75))
            painter.setFont(font)
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, emoji)
            painter.end()
            icon.addPixmap(pixmap)
            continue
            
        max_y = -1
        for y in range(render_size - 1, min_y - 1, -1):
            row_has_alpha = False
            for x in range(render_size):
                if ((image.pixel(x, y) >> 24) & 0xFF) > 10:
                    row_has_alpha = True
                    break
            if row_has_alpha:
                max_y = y
                break
                
        min_x = -1
        for x in range(render_size):
            col_has_alpha = False
            for y in range(min_y, max_y + 1):
                if ((image.pixel(x, y) >> 24) & 0xFF) > 10:
                    col_has_alpha = True
                    break
            if col_has_alpha:
                min_x = x
                break
                
        max_x = -1
        for x in range(render_size - 1, min_x - 1, -1):
            col_has_alpha = False
            for y in range(min_y, max_y + 1):
                if ((image.pixel(x, y) >> 24) & 0xFF) > 10:
                    col_has_alpha = True
                    break
            if col_has_alpha:
                max_x = x
                break
                
        width = max_x - min_x + 1
        height = max_y - min_y + 1
        
        cropped = image.copy(min_x, min_y, width, height)
        
        # Fit into target size leaving a tiny 5% margin
        margin = 0.05
        target_max_w = size * (1 - 2 * margin)
        target_max_h = size * (1 - 2 * margin)
        
        aspect = width / height
        if aspect > 1:
            w = target_max_w
            h = w / aspect
        else:
            h = target_max_h
            w = h * aspect
            
        x_offset = (size - w) / 2
        y_offset = (size - h) / 2
        
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawImage(QRectF(x_offset, y_offset, w, h), cropped)
        painter.end()
        
        icon.addPixmap(pixmap)
    return icon

class ObjectLoaderWorker(QThread):
    finished_signal = pyqtSignal(object, object, str)  # (children, tables_detailed, error_message)

    def __init__(self, db_engine, dbname, schema, group_name, profile):
        super().__init__()
        self.db_engine = db_engine
        self.dbname = dbname
        self.schema = schema
        self.group_name = group_name
        self.profile = profile

    def run(self):
        try:
            children = []
            tables_detailed = []
            
            if self.group_name == "Tables":
                # Fetch detailed list (with row counts and sizes)
                tables_detailed = self.db_engine.get_tables_detailed(self.schema)
                for t in tables_detailed:
                    name = t["name"]
                    children.append({
                        "name": name,
                        "data": {
                            "type": "table",
                            "profile": self.profile,
                            "dbname": self.dbname,
                            "schema": self.schema,
                            "table_name": name
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
            
            self.finished_signal.emit(children, tables_detailed, "")
        except Exception as e:
            self.finished_signal.emit([], [], str(e))

class ObjectTab(ObjectTabUI):
    open_table_signal = pyqtSignal(object, str, str, str)  # (db_engine, dbname, schema, table_name)
    open_query_signal = pyqtSignal(object, str, str, str)  # (db_engine, dbname, schema, initial_sql)
    open_designer_signal = pyqtSignal(object, str, str, str, bool)  # (db_engine, dbname, schema, table_name, is_new_table)

    def __init__(self, db_engine, dbname, schema, group_name, profile, parent=None):
        super().__init__(dbname, schema, group_name, parent)
        self.db_engine = db_engine
        self.profile = profile
        self.children = []
        self.tables_detailed = []
        self.loader_worker = None
        self.views_populated = {"detail": False, "list": False, "grid": False}
        
        # Cache emoji icon
        emoji_map = {
            "Tables": "📄",
            "Views": "📄",
            "Functions": "📄"
        }
        self.emoji = emoji_map.get(self.group_name, "📄")
        self.cached_icon = emoji_to_icon(self.emoji)
        
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
        
        self.table_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.grid_widget.customContextMenuRequested.connect(self.show_context_menu)
        
        # View switches
        self.btn_detail.clicked.connect(self.set_view_detail)
        self.btn_list.clicked.connect(self.set_view_list)
        self.btn_grid.clicked.connect(self.set_view_grid)
        
        self.start_loading()

    def start_loading(self):
        if self.loader_worker is not None and self.loader_worker.isRunning():
            return
        # Clear UI elements and show loading message
        self.status_lbl.setText("Loading objects...")
        
        # Clear UI components
        self.table_widget.setUpdatesEnabled(False)
        self.table_widget.setSortingEnabled(False)
        self.list_widget.setUpdatesEnabled(False)
        self.grid_widget.setUpdatesEnabled(False)
        self.table_widget.setRowCount(0)
        self.list_widget.clear()
        self.grid_widget.clear()
        self.table_widget.setUpdatesEnabled(True)
        self.list_widget.setUpdatesEnabled(True)
        self.grid_widget.setUpdatesEnabled(True)
        
        # Reset populated status
        self.views_populated = {"detail": False, "list": False, "grid": False}
        
        # Stop existing worker if running
        if self.loader_worker and self.loader_worker.isRunning():
            try:
                self.loader_worker.finished_signal.disconnect(self.on_loading_finished)
            except Exception:
                pass
            
        self.loader_worker = ObjectLoaderWorker(self.db_engine, self.dbname, self.schema, self.group_name, self.profile)
        self.loader_worker.finished_signal.connect(self.on_loading_finished)
        start_thread(self.loader_worker)


    def on_loading_finished(self, children, tables_detailed, error_msg):
        if error_msg:
            self.status_lbl.setText("Error loading objects.")
            show_exception_dialog(self, "Load Error", f"Failed to retrieve objects list:\n{error_msg}")
            return
            
        self.children = children
        self.tables_detailed = tables_detailed
        
        self.populate_data()
        
        # Apply search filter if active
        self.filter_objects()

    def populate_data(self):
        # Only populate the currently active view tab
        active_index = self.stack.currentIndex()
        if active_index == 0:
            self.populate_detail_view()
        elif active_index == 1:
            self.populate_list_view()
        elif active_index == 2:
            self.populate_grid_view()
            
        self.status_lbl.setText(f"Total: {len(self.children)} {self.group_name.lower()}")

    def populate_detail_view(self):
        if self.views_populated.get("detail"):
            return
            
        children_lookup = {child["name"]: child["data"] for child in self.children}

        self.table_widget.setUpdatesEnabled(False)
        self.table_widget.setSortingEnabled(False)
        self.table_widget.setRowCount(0)
        
        if self.group_name == "Tables":
            self.table_widget.setRowCount(len(self.tables_detailed))
            for idx, table in enumerate(self.tables_detailed):
                name = table["name"]
                rows_count = table["rows"]
                size_str = table["size"]
                child_data = children_lookup.get(name)
                
                # Column 0: Name with icon
                name_item = NumericTableWidgetItem(name, name.lower())
                name_item.setIcon(self.cached_icon)
                name_item.setData(Qt.ItemDataRole.UserRole, child_data)
                self.table_widget.setItem(idx, 0, name_item)
                
                # Column 1: Type
                type_item = NumericTableWidgetItem("Table", "table")
                self.table_widget.setItem(idx, 1, type_item)
                
                # Column 2: Rows
                try:
                    r_val = int(rows_count.replace(",", ""))
                except ValueError:
                    r_val = -1
                rows_item = NumericTableWidgetItem(rows_count, r_val)
                self.table_widget.setItem(idx, 2, rows_item)
                
                # Column 3: Size
                s_val = parse_size_to_bytes(size_str)
                size_item = NumericTableWidgetItem(size_str, s_val)
                self.table_widget.setItem(idx, 3, size_item)
        else:
            self.table_widget.setRowCount(len(self.children))
            for idx, child in enumerate(self.children):
                name = child["name"]
                child_data = child["data"]
                
                # Column 0: Name with icon
                name_item = NumericTableWidgetItem(name, name.lower())
                name_item.setIcon(self.cached_icon)
                name_item.setData(Qt.ItemDataRole.UserRole, child_data)
                self.table_widget.setItem(idx, 0, name_item)
                
                # Column 1: Type
                type_str = self.group_name.rstrip("s")
                type_item = NumericTableWidgetItem(type_str, type_str.lower())
                self.table_widget.setItem(idx, 1, type_item)
                
                # Column 2: Rows
                rows_item = NumericTableWidgetItem("-", -1)
                self.table_widget.setItem(idx, 2, rows_item)
                
                # Column 3: Size
                size_item = NumericTableWidgetItem("-", -1)
                self.table_widget.setItem(idx, 3, size_item)
            
        self.table_widget.setUpdatesEnabled(True)
        self.table_widget.setSortingEnabled(True)
        self.views_populated["detail"] = True

    def populate_list_view(self):
        if self.views_populated.get("list"):
            return
            
        self.list_widget.setUpdatesEnabled(False)
        self.list_widget.clear()
        
        for child in self.children:
            name = child["name"]
            child_data = child["data"]
            
            list_item = QListWidgetItem(name)
            list_item.setIcon(self.cached_icon)
            list_item.setData(Qt.ItemDataRole.UserRole, child_data)
            self.list_widget.addItem(list_item)
            
        self.list_widget.setUpdatesEnabled(True)
        self.views_populated["list"] = True

    def populate_grid_view(self):
        if self.views_populated.get("grid"):
            return
            
        self.grid_widget.setUpdatesEnabled(False)
        self.grid_widget.clear()
        
        for child in self.children:
            name = child["name"]
            child_data = child["data"]
            
            grid_item = QListWidgetItem(name)
            grid_item.setIcon(self.cached_icon)
            grid_item.setData(Qt.ItemDataRole.UserRole, child_data)
            self.grid_widget.addItem(grid_item)
            
        self.grid_widget.setUpdatesEnabled(True)
        self.views_populated["grid"] = True

    def set_view_detail(self):
        self.stack.setCurrentIndex(0)
        self.btn_detail.setChecked(True)
        from PyQt6.QtCore import QSettings
        QSettings("PgMan", "ObjectTabSettings").setValue("view_style", "detail")
        if hasattr(self, "children") and self.children:
            self.populate_detail_view()
            self.filter_objects()

    def set_view_list(self):
        self.stack.setCurrentIndex(1)
        self.btn_list.setChecked(True)
        from PyQt6.QtCore import QSettings
        QSettings("PgMan", "ObjectTabSettings").setValue("view_style", "list")
        if hasattr(self, "children") and self.children:
            self.populate_list_view()
            self.filter_objects()

    def set_view_grid(self):
        self.stack.setCurrentIndex(2)
        self.btn_grid.setChecked(True)
        from PyQt6.QtCore import QSettings
        QSettings("PgMan", "ObjectTabSettings").setValue("view_style", "grid")
        if hasattr(self, "children") and self.children:
            self.populate_grid_view()
            self.filter_objects()

    def filter_objects(self):
        query = self.search_input.text().lower()
        visible_count = 0
        active_index = self.stack.currentIndex()
        
        if active_index == 0:
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
        elif active_index == 1:
            # Filter list items
            for idx in range(self.list_widget.count()):
                item = self.list_widget.item(idx)
                if item:
                    name_text = item.text().lower()
                    if query in name_text:
                        item.setHidden(False)
                        visible_count += 1
                    else:
                        item.setHidden(True)
        elif active_index == 2:
            # Filter grid items
            for idx in range(self.grid_widget.count()):
                item = self.grid_widget.item(idx)
                if item:
                    name_text = item.text().lower()
                    if query in name_text:
                        item.setHidden(False)
                        visible_count += 1
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

    def update_data(self, db_engine, dbname, schema, group_name, profile):
        self.db_engine = db_engine
        self.dbname = dbname
        self.schema = schema
        self.group_name = group_name
        self.profile = profile
        
        emoji_map = {
            "Tables": "📄",
            "Views": "📄",
            "Functions": "📄"
        }
        self.emoji = emoji_map.get(self.group_name, "📄")
        self.cached_icon = emoji_to_icon(self.emoji)
        
        self.header_lbl.setText(f"📂 {self.group_name} in {self.schema}")
        
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)
        
        self.start_loading()

    def refresh_data(self):
        self.db_engine.clear_cache()
        self.start_loading()

    def show_context_menu(self, position):
        sender = self.sender()
        if not sender:
            return
            
        data = None
        if isinstance(sender, QTableWidget):
            item = sender.itemAt(position)
            if item:
                row = item.row()
                name_item = sender.item(row, 0)
                if name_item:
                    data = name_item.data(Qt.ItemDataRole.UserRole)
        else:
            item = sender.itemAt(position)
            if item:
                data = item.data(Qt.ItemDataRole.UserRole)
                
        menu = QMenu(self)
        
        open_action = None
        ddl_action = None
        design_action = None
        drop_action = None
        create_action = None
        
        if data:
            node_type = data.get("type")
            if node_type == "table":
                open_action = menu.addAction("Open Table")
                design_action = menu.addAction("Design Table")
                ddl_action = menu.addAction("Show DDL")
                drop_action = menu.addAction("Drop Table")
                menu.addSeparator()
            elif node_type == "view":
                open_action = menu.addAction("Open View")
                ddl_action = menu.addAction("Show DDL")
                menu.addSeparator()
            elif node_type == "function":
                open_action = menu.addAction("Open Function Definition")
                menu.addSeparator()
                
        refresh_action = menu.addAction("Refresh")
        is_running = self.loader_worker is not None and self.loader_worker.isRunning()
        refresh_action.setEnabled(not is_running)
        
        if not data and self.group_name == "Tables":
            menu.addSeparator()
            create_action = menu.addAction("Create New Table")
            
        action = menu.exec(sender.mapToGlobal(position))
        if action is not None:
            if action == open_action:
                self.open_object_with_data(data)
            elif action == design_action and design_action:
                self.open_designer_for_object(data)
            elif action == ddl_action:
                self.show_ddl_for_object(data)
            elif action == drop_action and drop_action:
                self.drop_table_for_object(data)
            elif action == create_action and create_action:
                self.create_new_table()
            elif action == refresh_action:
                self.refresh_data()

    def show_ddl_for_object(self, data):
        node_type = data.get("type")
        table_name = data.get("table_name")
        
        self.setCursor(QCursor(Qt.CursorShape.WaitCursor))
        try:
            if node_type == "table":
                sql_def = self.db_engine.get_table_definition(self.schema, table_name)
            else:  # view
                sql_def = self.db_engine.get_view_definition(self.schema, table_name)
            self.open_query_signal.emit(self.db_engine, self.dbname, self.schema, sql_def)
        except Exception as e:
            show_exception_dialog(self, "Error", f"Could not retrieve definition:\n{str(e)}")
        finally:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def open_designer_for_object(self, data):
        table_name = data.get("table_name")
        if table_name:
            self.open_designer_signal.emit(self.db_engine, self.dbname, self.schema, table_name, False)

    def create_new_table(self):
        name, ok = QInputDialog.getText(self, "Create New Table", "Enter table name:")
        if ok and name.strip():
            table_name = name.strip()
            self.open_designer_signal.emit(self.db_engine, self.dbname, self.schema, table_name, True)

    def drop_table_for_object(self, data):
        table_name = data.get("table_name")
        if not table_name:
            return
            
        table_ref = self.db_engine.quote_table_name(self.schema, table_name)
        reply = QMessageBox.question(
            self, "Confirm Drop Table",
            f"Are you sure you want to DROP the table {table_ref}?\n\nThis action cannot be undone and all data in the table will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.setCursor(QCursor(Qt.CursorShape.WaitCursor))
            try:
                sql = f"DROP TABLE {table_ref};"
                self.db_engine.execute_query(sql, fetch_results=False)
                self.db_engine.clear_cache()
                self.refresh_data()
                
                # Close any open TableViewerTab or TableDesignerTab for this table
                main_win = self.window()
                if hasattr(main_win, "tabs"):
                    from src.ui.TableViewerLogic import TableViewerTab
                    from src.ui.TableDesignerLogic import TableDesignerTab
                    tabs_to_close = []
                    for idx in range(main_win.tabs.count()):
                        w = main_win.tabs.widget(idx)
                        if isinstance(w, TableViewerTab) or isinstance(w, TableDesignerTab):
                            if w.dbname == self.dbname and w.schema == self.schema and w.table_name == table_name:
                                tabs_to_close.append(idx)
                    for idx in sorted(tabs_to_close, reverse=True):
                        w = main_win.tabs.widget(idx)
                        if w:
                            w.deleteLater()
                        main_win.tabs.removeTab(idx)
            except Exception as e:
                show_exception_dialog(self, "Error", f"Failed to drop table:\n{str(e)}")
            finally:
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
