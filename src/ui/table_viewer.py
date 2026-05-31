from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView,
    QPushButton, QComboBox, QLabel, QMessageBox, QToolBar
)
from PyQt6.QtCore import Qt, QAbstractTableModel, pyqtSignal
from PyQt6.QtGui import QColor

class EditableSqlTableModel(QAbstractTableModel):
    def __init__(self, columns=None, rows=None, primary_keys=None, parent=None):
        super().__init__(parent)
        self.cols = columns or []
        self.rows_data = [list(r) for r in (rows or [])]
        # Keep original copies to generate WHERE clauses and detect changes
        self.original_rows_data = [list(r) for r in self.rows_data]
        self.primary_keys = primary_keys or []
        
        # Edit tracking
        self.edited_cells = {}  # {row_idx: {col_idx: new_value}}
        self.deleted_row_indices = set()

    def rowCount(self, parent=None):
        return len(self.rows_data)

    def columnCount(self, parent=None):
        return len(self.cols)

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        if index.row() in self.deleted_row_indices:
            # Row is marked for deletion; allow selection but not editing
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        return Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
            
        row = index.row()
        col = index.column()
        
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            val = self.rows_data[row][col]
            if val is None:
                return "[NULL]" if role == Qt.ItemDataRole.DisplayRole else ""
            return str(val)
            
        elif role == Qt.ItemDataRole.BackgroundRole:
            if row in self.deleted_row_indices:
                return QColor("#5c2d30")  # Dark red for deleted
            elif row >= len(self.original_rows_data):
                return QColor("#1e3f20")  # Dark green for new row
            elif row in self.edited_cells and col in self.edited_cells[row]:
                return QColor("#5c431e")  # Amber for edited
                
        elif role == Qt.ItemDataRole.ForegroundRole:
            val = self.rows_data[row][col]
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
        
        # Handle custom null/empty entry
        if value == "[NULL]" or value == "":
            stored_value = None
        else:
            stored_value = value

        self.rows_data[row][col] = stored_value
        
        # If it's a new row, we don't need to track in edited_cells (its whole row is inserts)
        if row < len(self.original_rows_data):
            if row not in self.edited_cells:
                self.edited_cells[row] = {}
            self.edited_cells[row][col] = stored_value
            
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.BackgroundRole])
        return True

    def add_row(self):
        self.beginInsertRows(self.index(len(self.rows_data), 0), len(self.rows_data), len(self.rows_data))
        new_row = [None] * len(self.cols)
        self.rows_data.append(new_row)
        self.endInsertRows()

    def mark_selected_row_for_deletion(self, row):
        if row < 0 or row >= len(self.rows_data):
            return
            
        if row in self.deleted_row_indices:
            self.deleted_row_indices.remove(row)
        else:
            self.deleted_row_indices.add(row)
            
        self.dataChanged.emit(
            self.index(row, 0), 
            self.index(row, len(self.cols) - 1), 
            [Qt.ItemDataRole.BackgroundRole]
        )

    def get_pending_changes(self):
        updates = []
        for row, cols_dict in self.edited_cells.items():
            if row in self.deleted_row_indices:
                continue
            
            pks = {}
            for pk in self.primary_keys:
                pk_idx = self.cols.index(pk)
                pks[pk] = self.original_rows_data[row][pk_idx]
                
            if not pks:
                # Use all original columns if no primary keys
                for idx, col_name in enumerate(self.cols):
                    pks[col_name] = self.original_rows_data[row][idx]
                    
            col_updates = {}
            for col_idx, val in cols_dict.items():
                col_updates[self.cols[col_idx]] = val
                
            updates.append({
                "primary_keys": pks,
                "updates": col_updates
            })
            
        inserts = []
        for row in range(len(self.original_rows_data), len(self.rows_data)):
            if row in self.deleted_row_indices:
                continue
            row_vals = self.rows_data[row]
            insert_dict = {}
            for idx, col_name in enumerate(self.cols):
                if row_vals[idx] is not None:
                    insert_dict[col_name] = row_vals[idx]
            inserts.append(insert_dict)
            
        deletes = []
        for row in self.deleted_row_indices:
            if row >= len(self.original_rows_data):
                continue
            pks = {}
            for pk in self.primary_keys:
                pk_idx = self.cols.index(pk)
                pks[pk] = self.original_rows_data[row][pk_idx]
                
            if not pks:
                for idx, col_name in enumerate(self.cols):
                    pks[col_name] = self.original_rows_data[row][idx]
            deletes.append(pks)
            
        return updates, inserts, deletes


class TableViewerTab(QWidget):
    def __init__(self, db_engine, dbname, schema, table_name, parent=None):
        super().__init__(parent)
        self.db_engine = db_engine
        self.dbname = dbname
        self.schema = schema
        self.table_name = table_name
        
        # Pagination state
        self.current_page = 1
        self.page_size = 100
        self.total_rows = 0
        self.total_pages = 1
        
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = QToolBar()
        
        self.add_btn = QPushButton("➕ Add Row")
        self.add_btn.clicked.connect(self.add_row)
        toolbar.addWidget(self.add_btn)
        
        self.delete_btn = QPushButton("❌ Delete Row")
        self.delete_btn.clicked.connect(self.delete_row)
        toolbar.addWidget(self.delete_btn)

        toolbar.addSeparator()

        self.commit_btn = QPushButton("✔ Commit")
        self.commit_btn.setObjectName("saveBtn")
        self.commit_btn.clicked.connect(self.commit_changes)
        toolbar.addWidget(self.commit_btn)
        
        self.refresh_btn = QPushButton("↺ Refresh")
        self.refresh_btn.clicked.connect(self.load_data)
        toolbar.addWidget(self.refresh_btn)

        # Spacer in toolbar
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().Policy.Expanding, spacer.sizePolicy().Policy.Preferred)
        toolbar.addWidget(spacer)

        # Pagination controls
        self.first_page_btn = QPushButton("|<")
        self.first_page_btn.clicked.connect(self.go_first_page)
        toolbar.addWidget(self.first_page_btn)

        self.prev_page_btn = QPushButton("<")
        self.prev_page_btn.clicked.connect(self.go_prev_page)
        toolbar.addWidget(self.prev_page_btn)

        self.page_label = QLabel("Page 1 of 1")
        self.page_label.setStyleSheet("padding: 0px 8px; color: #abb2bf;")
        toolbar.addWidget(self.page_label)

        self.next_page_btn = QPushButton(">")
        self.next_page_btn.clicked.connect(self.go_next_page)
        toolbar.addWidget(self.next_page_btn)

        self.last_page_btn = QPushButton(">|")
        self.last_page_btn.clicked.connect(self.go_last_page)
        toolbar.addWidget(self.last_page_btn)

        toolbar.addSeparator()
        
        self.limit_combo = QComboBox()
        self.limit_combo.addItems(["100", "500", "1000"])
        self.limit_combo.currentTextChanged.connect(self.on_limit_changed)
        toolbar.addWidget(self.limit_combo)

        layout.addWidget(toolbar)

        # Main Table View
        self.table_view = QTableView()
        layout.addWidget(self.table_view)

        # Status Bar
        self.status_bar_lbl = QLabel(f"Table: {self.schema}.{self.table_name} | Rows: 0")
        self.status_bar_lbl.setStyleSheet("padding: 4px; color: #5c6370; background-color: #21252b;")
        layout.addWidget(self.status_bar_lbl)

    def load_data(self):
        self.setCursor(Qt.CursorShape.WaitCursor)
        try:
            # 1. Fetch total rows count
            count_sql = f'SELECT count(*) FROM "{self.schema}"."{self.table_name}"'
            _, count_rows, _ = self.db_engine.execute_query(count_sql)
            self.total_rows = count_rows[0][0] if count_rows else 0
            
            # 2. Update pagination calculations
            self.page_size = int(self.limit_combo.currentText())
            self.total_pages = max(1, (self.total_rows + self.page_size - 1) // self.page_size)
            if self.current_page > self.total_pages:
                self.current_page = self.total_pages
                
            self.page_label.setText(f"Page {self.current_page} of {self.total_pages}")
            self.status_bar_lbl.setText(f"Table: {self.schema}.{self.table_name} | Total Rows: {self.total_rows}")
            
            # 3. Fetch current page records
            offset = (self.current_page - 1) * self.page_size
            sql = f'SELECT * FROM "{self.schema}"."{self.table_name}" LIMIT {self.page_size} OFFSET {offset}'
            columns, rows, _ = self.db_engine.execute_query(sql)
            
            # 4. Fetch primary keys
            pks = self.db_engine.get_primary_keys(self.schema, self.table_name)
            
            # 5. Populate model
            self.model = EditableSqlTableModel(columns, rows, pks, self)
            self.table_view.setModel(self.model)
            
            # Resize
            self.table_view.resizeColumnsToContents()
            for c in range(len(columns)):
                if self.table_view.columnWidth(c) > 300:
                    self.table_view.setColumnWidth(c, 300)
                    
            # Enable/disable page buttons
            self.first_page_btn.setEnabled(self.current_page > 1)
            self.prev_page_btn.setEnabled(self.current_page > 1)
            self.next_page_btn.setEnabled(self.current_page < self.total_pages)
            self.last_page_btn.setEnabled(self.current_page < self.total_pages)
            
        except Exception as e:
            QMessageBox.critical(self, "Error Loading Table", f"Failed to fetch table records:\n{str(e)}")
        finally:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def add_row(self):
        if hasattr(self, "model"):
            self.model.add_row()
            # Scroll to bottom
            self.table_view.scrollToBottom()

    def delete_row(self):
        if not hasattr(self, "model"):
            return
            
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.warning(self, "No Row Selected", "Please select entire row by clicking the row header on the left.")
            return
            
        for index in indexes:
            self.model.mark_selected_row_for_deletion(index.row())

    def commit_changes(self):
        if not hasattr(self, "model"):
            return
            
        updates, inserts, deletes = self.model.get_pending_changes()
        
        if not (updates or inserts or deletes):
            QMessageBox.information(self, "No Changes", "No modifications to commit.")
            return
            
        reply = QMessageBox.question(
            self, "Commit Changes", 
            f"Are you sure you want to write these modifications to the database?\n"
            f"- Updates: {len(updates)}\n"
            f"- Inserts: {len(inserts)}\n"
            f"- Deletes: {len(deletes)}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.setCursor(Qt.CursorShape.WaitCursor)
        try:
            # We run within a simple psycopg transaction block if possible, but 
            # for now we execute individually with engine.
            # 1. Run Deletes first
            for pk_dict in deletes:
                self.db_engine.delete_row(self.schema, self.table_name, pk_dict)
                
            # 2. Run Updates
            for upd in updates:
                self.db_engine.update_row(self.schema, self.table_name, upd["primary_keys"], upd["updates"])
                
            # 3. Run Inserts
            for ins in inserts:
                self.db_engine.insert_row(self.schema, self.table_name, ins)

            QMessageBox.information(self, "Success", "Changes successfully committed to database!")
            self.load_data()  # Reload
        except Exception as e:
            QMessageBox.critical(self, "Commit Failed", f"An error occurred while saving changes:\n{str(e)}\n\nReloading table data...")
            self.load_data()  # Reload to sync state
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
