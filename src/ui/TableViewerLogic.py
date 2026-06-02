from PyQt6.QtWidgets import QMessageBox, QMenu
from PyQt6.QtCore import Qt, QAbstractTableModel, QThread, pyqtSignal, QSettings, QModelIndex
from PyQt6.QtGui import QColor
from src.ui.TableViewerUI import TableViewerUI
from src.ui.UiUtils import resize_columns_fast, show_exception_dialog, start_thread

class DataLoaderWorker(QThread):
    finished = pyqtSignal(object, object, int, object)  # (columns, rows, total_rows, primary_keys)
    failed = pyqtSignal(str)                       # (error_message)

    def __init__(self, db_engine, schema, table_name, page_size, offset):
        super().__init__()
        self.db_engine = db_engine
        self.schema = schema
        self.table_name = table_name
        self.page_size = page_size
        self.offset = offset

    def run(self):
        try:
            # 1. Fetch total rows count
            quoted_table = self.db_engine.quote_table_name(self.schema, self.table_name)
            count_sql = f'SELECT count(*) FROM {quoted_table}'
            _, count_rows, _ = self.db_engine.execute_query(count_sql)
            total_rows = count_rows[0][0] if count_rows else 0
            
            # 2. Fetch current page records
            sql = f'SELECT * FROM {quoted_table} LIMIT {self.page_size} OFFSET {self.offset}'
            columns, rows, _ = self.db_engine.execute_query(sql)
            
            # 3. Fetch primary keys
            pks = self.db_engine.get_primary_keys(self.schema, self.table_name)
            
            self.finished.emit(columns, rows, total_rows, pks)
        except Exception as e:
            self.failed.emit(str(e))

class EditableSqlTableModel(QAbstractTableModel):
    def __init__(self, columns=None, rows=None, primary_keys=None, parent=None):
        super().__init__(parent)
        self.cols = columns or []
        self.primary_keys = primary_keys or []
        
        self.DELETED_OFFSET = len(self.cols)
        self.EDITED_OFFSET = len(self.cols) + 1
        self.ORIGINAL_OFFSET = len(self.cols) + 2
        self.IS_NEW_OFFSET = len(self.cols) + 3
        
        # Cache theme for BackgroundRole to avoid QSettings overhead on every data() call
        settings = QSettings("PgMan", "ThemeSettings")
        self._cached_theme = settings.value("theme", "dark").lower()
        
        # Each row is a list: [col_0, ..., col_N, is_deleted, edited_dict, original_row, is_new]
        self.rows_data = []
        for r in (rows or []):
            row_list = list(r)
            row_list.extend([False, {}, list(r), False])
            self.rows_data.append(row_list)

    def rowCount(self, parent=None):
        return len(self.rows_data)

    def columnCount(self, parent=None):
        return len(self.cols)

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        row_data = self.rows_data[index.row()]
        if row_data[self.DELETED_OFFSET]:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        return Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
            
        row = index.row()
        col = index.column()
        if row < 0 or row >= len(self.rows_data) or col < 0 or col >= len(self.cols):
            return None
        row_data = self.rows_data[row]
        
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            val = row_data[col]
            if val is None:
                return "[NULL]" if role == Qt.ItemDataRole.DisplayRole else ""
            return str(val)
            
        elif role == Qt.ItemDataRole.BackgroundRole:
            theme = self._cached_theme
            
            if row_data[self.DELETED_OFFSET]:
                return QColor(250, 219, 216) if theme == "light" else QColor(96, 43, 41)
            elif row_data[self.IS_NEW_OFFSET]:
                return QColor(213, 245, 227) if theme == "light" else QColor(34, 106, 68)
            elif col in row_data[self.EDITED_OFFSET]:
                return QColor(250, 229, 211) if theme == "light" else QColor(96, 61, 32)
                
        elif role == Qt.ItemDataRole.ForegroundRole:
            val = row_data[col]
            if val is None:
                return QColor("#5c6370")
                
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                suffix = " 🔑" if self.cols[section] in self.primary_keys else ""
                return f"{self.cols[section]}{suffix}"
            else:
                return str(section + 1)
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False
            
        row = index.row()
        col = index.column()
        if row < 0 or row >= len(self.rows_data):
            return False
        row_data = self.rows_data[row]
        
        if value == "[NULL]" or value == "":
            stored_value = None
        else:
            stored_value = value

        row_data[col] = stored_value
        
        if not row_data[self.IS_NEW_OFFSET]:
            row_data[self.EDITED_OFFSET][col] = stored_value
            
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.BackgroundRole])
        return True

    def add_row(self):
        for row_data in self.rows_data:
            if row_data[self.IS_NEW_OFFSET]:
                return False
        self.beginInsertRows(QModelIndex(), len(self.rows_data), len(self.rows_data))
        new_row = [None] * len(self.cols)
        new_row.extend([False, {}, [None] * len(self.cols), True])
        self.rows_data.append(new_row)
        self.endInsertRows()
        return True

    def mark_selected_row_for_deletion(self, row):
        if row < 0 or row >= len(self.rows_data):
            return
            
        row_data = self.rows_data[row]
        row_data[self.DELETED_OFFSET] = not row_data[self.DELETED_OFFSET]
            
        self.dataChanged.emit(
            self.index(row, 0), 
            self.index(row, len(self.cols) - 1), 
            [Qt.ItemDataRole.BackgroundRole]
        )

    def revert_row(self, row):
        if row < 0 or row >= len(self.rows_data):
            return
            
        row_data = self.rows_data[row]
        if row_data[self.IS_NEW_OFFSET]:
            # Remove the row from the model
            self.beginRemoveRows(QModelIndex(), row, row)
            self.rows_data.pop(row)
            self.endRemoveRows()
        else:
            # Revert edited cells and restore original values
            orig = row_data[self.ORIGINAL_OFFSET]
            for i in range(len(self.cols)):
                row_data[i] = orig[i]
            row_data[self.EDITED_OFFSET] = {}
            row_data[self.DELETED_OFFSET] = False
            self.dataChanged.emit(
                self.index(row, 0),
                self.index(row, len(self.cols) - 1),
                [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.BackgroundRole]
            )

    def sort(self, column, order):
        self.layoutAboutToBeChanged.emit()
        reverse = (order == Qt.SortOrder.DescendingOrder)
        
        def sort_key(row_list):
            val = row_list[column]
            if val is None:
                return (2, "")
            if isinstance(val, (int, float)):
                return (0, val)
            try:
                num_val = float(val) if '.' in str(val) else int(val)
                return (0, num_val)
            except Exception:
                return (1, str(val).lower())

        self.rows_data.sort(key=sort_key, reverse=reverse)
        self.layoutChanged.emit()

    def get_pending_changes(self):
        updates = []
        inserts = []
        deletes = []
        
        for row_data in self.rows_data:
            if row_data[self.DELETED_OFFSET]:
                if not row_data[self.IS_NEW_OFFSET]:
                    pks = {}
                    orig_row = row_data[self.ORIGINAL_OFFSET]
                    for pk in self.primary_keys:
                        pk_idx = self.cols.index(pk)
                        pks[pk] = orig_row[pk_idx]
                    if not pks:
                        for idx, col_name in enumerate(self.cols):
                            pks[col_name] = orig_row[idx]
                    deletes.append(pks)
                continue
                
            if row_data[self.IS_NEW_OFFSET]:
                insert_dict = {}
                for idx, col_name in enumerate(self.cols):
                    if row_data[idx] is not None:
                        insert_dict[col_name] = row_data[idx]
                if insert_dict:  # Skip rows where all columns are NULL
                    inserts.append(insert_dict)
            elif row_data[self.EDITED_OFFSET]:
                pks = {}
                orig_row = row_data[self.ORIGINAL_OFFSET]
                for pk in self.primary_keys:
                    pk_idx = self.cols.index(pk)
                    pks[pk] = orig_row[pk_idx]
                if not pks:
                    for idx, col_name in enumerate(self.cols):
                        pks[col_name] = orig_row[idx]
                        
                col_updates = {}
                for col_idx, val in row_data[self.EDITED_OFFSET].items():
                    col_updates[self.cols[col_idx]] = val
                    
                updates.append({
                    "primary_keys": pks,
                    "updates": col_updates
                })
                
        return updates, inserts, deletes


class TableViewerTab(TableViewerUI):
    def __init__(self, db_engine, dbname, schema, table_name, parent=None):
        self.db_engine = db_engine
        super().__init__(dbname, schema, table_name, parent)
        
        # Pagination state
        self.current_page = 1
        self.page_size = 100
        self.total_rows = 0
        self.total_pages = 1
        self.is_loading = False
        
        self.setup_logic()
        self.load_data()

    def setup_logic(self):
        self.add_btn.clicked.connect(self.add_row)
        self.delete_btn.clicked.connect(self.delete_row)
        self.commit_btn.clicked.connect(self.commit_changes)
        self.refresh_btn.clicked.connect(self.load_data)
        self.ddl_btn.clicked.connect(self.show_ddl)
        
        self.first_page_btn.clicked.connect(self.go_first_page)
        self.prev_page_btn.clicked.connect(self.go_prev_page)
        self.next_page_btn.clicked.connect(self.go_next_page)
        self.last_page_btn.clicked.connect(self.go_last_page)
        
        self.limit_combo.currentTextChanged.connect(self.on_limit_changed)
        
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)
        self.table_view.setSortingEnabled(True)
        self.table_view.installEventFilter(self)

    def eventFilter(self, source, event):
        from PyQt6.QtCore import QEvent
        if source == self.table_view and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Down:
                current_index = self.table_view.currentIndex()
                if hasattr(self, "model"):
                    rowCount = self.model.rowCount()
                    if rowCount == 0 or (current_index.isValid() and current_index.row() == rowCount - 1):
                        self.add_row()
                        return True
            elif event.key() == Qt.Key.Key_Escape:
                current_index = self.table_view.currentIndex()
                if current_index.isValid() and hasattr(self, "model"):
                    self.model.revert_row(current_index.row())
                    return True
            elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                current_index = self.table_view.currentIndex()
                if current_index.isValid() and hasattr(self, "model"):
                    row = current_index.row()
                    if row < len(self.model.rows_data):
                        row_data = self.model.rows_data[row]
                        if row_data[self.model.IS_NEW_OFFSET]:
                            self.commit_changes()
                            return True
        return super().eventFilter(source, event)

    def set_loading_state(self, is_loading):
        self.is_loading = is_loading
        self.add_btn.setEnabled(not is_loading)
        self.delete_btn.setEnabled(not is_loading)
        self.commit_btn.setEnabled(not is_loading)
        self.refresh_btn.setEnabled(not is_loading)
        self.ddl_btn.setEnabled(not is_loading)
        
        self.first_page_btn.setEnabled(not is_loading)
        self.prev_page_btn.setEnabled(not is_loading)
        self.next_page_btn.setEnabled(not is_loading)
        self.last_page_btn.setEnabled(not is_loading)
        self.limit_combo.setEnabled(not is_loading)
        
        if is_loading:
            self.setCursor(Qt.CursorShape.WaitCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def show_ddl(self):
        try:
            self.setCursor(Qt.CursorShape.WaitCursor)
            
            # Check if this object is a view or a table
            views = self.db_engine.get_views(self.schema)
            is_view = (self.table_name in views)
            
            if is_view:
                sql_def = self.db_engine.get_view_definition(self.schema, self.table_name)
            else:
                sql_def = self.db_engine.get_table_definition(self.schema, self.table_name)
                
            main_win = self.window()
            if hasattr(main_win, "add_query_tab"):
                main_win.add_query_tab(self.db_engine, self.dbname, self.schema, sql_def)
        except Exception as e:
            show_exception_dialog(self, "Error", f"Could not retrieve definition:\n{str(e)}")
        finally:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def load_data(self):
        if self.is_loading:
            return
        self.set_loading_state(True)
        self.status_bar_lbl.setText("⏳ Loading table data...")
        
        # Disconnect previous worker signals to prevent stale results
        if hasattr(self, 'worker') and self.worker is not None:
            try:
                self.worker.finished.disconnect(self.on_load_success)
                self.worker.failed.disconnect(self.on_load_failed)
            except (TypeError, RuntimeError):
                pass
        
        self.page_size = int(self.limit_combo.currentText())
        offset = (self.current_page - 1) * self.page_size
        
        self.worker = DataLoaderWorker(self.db_engine, self.schema, self.table_name, self.page_size, offset)
        self.worker.finished.connect(self.on_load_success)
        self.worker.failed.connect(self.on_load_failed)
        start_thread(self.worker)


    def on_load_success(self, columns, rows, total_rows, pks):
        self.set_loading_state(False)
        self.total_rows = total_rows
        
        self.total_pages = max(1, (self.total_rows + self.page_size - 1) // self.page_size)
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
            
        self.page_label.setText(f"Page {self.current_page} of {self.total_pages}")
        self.status_bar_lbl.setText(f"Table: {self.schema}.{self.table_name} | Total Rows: {self.total_rows}")
        
        self.model = EditableSqlTableModel(columns, rows, pks, self)
        self.table_view.setModel(self.model)
        
        resize_columns_fast(self.table_view, columns, rows)
        
        self.first_page_btn.setEnabled(self.current_page > 1)
        self.prev_page_btn.setEnabled(self.current_page > 1)
        self.next_page_btn.setEnabled(self.current_page < self.total_pages)
        self.last_page_btn.setEnabled(self.current_page < self.total_pages)

    def on_load_failed(self, error_message):
        self.set_loading_state(False)
        self.status_bar_lbl.setText(f"Error loading table: {self.schema}.{self.table_name}")
        show_exception_dialog(self, "Error Loading Table", f"Failed to fetch table records:\n{error_message}")

    def add_row(self):
        if hasattr(self, "model"):
            if self.model.add_row():
                self.table_view.scrollToBottom()
                
                # Select and start editing the first cell of the new row immediately
                new_row_idx = self.model.rowCount() - 1
                model_index = self.model.index(new_row_idx, 0)
                self.table_view.setCurrentIndex(model_index)
                self.table_view.edit(model_index)
            else:
                self.status_bar_lbl.setText("⚠ A new uncommitted row already exists. Commit or cancel it first.")

    def delete_row(self):
        if not hasattr(self, "model"):
            return
        
        sel_model = self.table_view.selectionModel()
        if sel_model is None:
            return
            
        indexes = sel_model.selectedRows()
        if not indexes:
            # Fallback to the current row if no entire row is selected
            current_index = self.table_view.currentIndex()
            if current_index.isValid():
                self.model.mark_selected_row_for_deletion(current_index.row())
            else:
                self.status_bar_lbl.setText("⚠ Select a cell or row to delete.")
            return
            
        for index in indexes:
            self.model.mark_selected_row_for_deletion(index.row())

    def commit_changes(self):
        if not hasattr(self, "model"):
            return
            
        updates, inserts, deletes = self.model.get_pending_changes()
        
        if not (updates or inserts or deletes):
            self.status_bar_lbl.setText("No changes to commit.")
            return

        self.setCursor(Qt.CursorShape.WaitCursor)
        try:
            # 1. Run Deletes first
            for pk_dict in deletes:
                self.db_engine.delete_row(self.schema, self.table_name, pk_dict)
                
            # 2. Run Updates
            for upd in updates:
                self.db_engine.update_row(self.schema, self.table_name, upd["primary_keys"], upd["updates"])
                
            # 3. Run Inserts
            for ins in inserts:
                self.db_engine.insert_row(self.schema, self.table_name, ins)

            self.status_bar_lbl.setText("✔ Changes successfully committed to database!")
            self.load_data()
        except Exception as e:
            show_exception_dialog(self, "Commit Failed", f"An error occurred while saving changes:\n{str(e)}\n\nReloading table data...")
            self.load_data()
        finally:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def on_limit_changed(self):
        self.current_page = 1
        self.load_data()

    def go_first_page(self):
        self.current_page = 1
        self.load_data()

    def go_prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_data()

    def go_next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_data()

    def go_last_page(self):
        self.current_page = self.total_pages
        self.load_data()

    def show_context_menu(self, position):
        menu = QMenu(self)
        
        sel_model = self.table_view.selectionModel()
        index = self.table_view.indexAt(position)
        if index.isValid() and sel_model is not None:
            # If the row is not already selected, select it to make operations intuitive
            if not sel_model.isRowSelected(index.row()):
                self.table_view.selectRow(index.row())
                
        # 1. Add Row
        add_action = menu.addAction("➕ Add Row")
        
        # 2. Delete Row(s)
        selected_rows = sel_model.selectedRows() if sel_model else []
        delete_action = None
        if selected_rows:
            delete_action = menu.addAction("❌ Delete Row(s)")
            
        menu.addSeparator()
        
        # 3. Set Cell to NULL (if clicking an active, non-null cell)
        null_action = None
        if (index.isValid() and hasattr(self, "model")
                and index.row() < len(self.model.rows_data)
                and not self.model.rows_data[index.row()][self.model.DELETED_OFFSET]):
            row = index.row()
            col = index.column()
            val = self.model.rows_data[row][col]
            if val is not None:
                null_action = menu.addAction("Set Cell to NULL")
                menu.addSeparator()
                
        # 4. Commit Changes
        commit_action = menu.addAction("✔ Commit Changes")
        
        # 5. Refresh
        refresh_action = menu.addAction("↺ Refresh")
        refresh_action.setEnabled(not self.is_loading)
        
        # 6. Show DDL
        ddl_action = menu.addAction("📄 Show DDL")
        
        action = menu.exec(self.table_view.mapToGlobal(position))
        if action is not None:
            if action == add_action:
                self.add_row()
            elif action == delete_action:
                self.delete_row()
            elif action == null_action:
                self.model.setData(index, "[NULL]")
            elif action == commit_action:
                self.commit_changes()
            elif action == refresh_action:
                self.load_data()
            elif action == ddl_action:
                self.show_ddl()
