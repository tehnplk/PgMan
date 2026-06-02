from PyQt6.QtWidgets import (
    QTableWidgetItem, QCheckBox, QWidget, QHBoxLayout, QMessageBox, QApplication, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from src.ui.TableDesignerUI import TableDesignerUI
from src.ui.UiUtils import show_exception_dialog, start_thread


class DesignerLoaderWorker(QThread):
    finished_signal = pyqtSignal(object, str)  # (columns_detailed, error_message)

    def __init__(self, db_engine, schema, table_name):
        super().__init__()
        self.db_engine = db_engine
        self.schema = schema
        self.table_name = table_name

    def run(self):
        try:
            cols = self.db_engine.get_columns_detailed(self.schema, self.table_name)
            self.finished_signal.emit(cols, "")
        except Exception as e:
            self.finished_signal.emit([], str(e))


def _make_centered_checkbox(checked=False):
    """Create a centered checkbox widget for table cells."""
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    cb = QCheckBox()
    cb.setChecked(checked)
    layout.addWidget(cb)
    container._checkbox = cb
    return container


def parse_type_and_length(column_type):
    """Parse column type and extract base name and length/precision."""
    import re
    match = re.match(r'^([^(]+)\((.+)\)$', column_type.strip())
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return column_type.strip(), ""


class TableDesignerTab(TableDesignerUI):
    def __init__(self, db_engine, dbname, schema, table_name, parent=None, is_new_table=False):
        self.db_engine = db_engine
        self.is_new_table = is_new_table
        super().__init__(dbname, schema, table_name, parent)

        self.original_columns = []  # snapshot of loaded columns
        self.loader_worker = None

        # Connect signals
        self.save_btn.clicked.connect(self.save_changes)
        self.add_col_btn.clicked.connect(self.add_column)
        self.del_col_btn.clicked.connect(self.remove_column)
        self.move_up_btn.clicked.connect(self.move_row_up)
        self.move_down_btn.clicked.connect(self.move_row_down)
        self.refresh_btn.clicked.connect(self.load_structure)

        # Track changes for SQL preview
        self.column_table.cellChanged.connect(self.update_sql_preview)

        self.load_structure()

    def get_supported_types(self):
        db_type = self.db_engine.db_type.lower()
        if db_type == "postgresql":
            return ["varchar", "char", "text", "integer", "bigint", "smallint", "boolean", "numeric", "double precision", "real", "date", "timestamp", "json", "jsonb", "uuid", "bytea", "serial", "bigserial"]
        elif db_type == "mysql":
            return ["VARCHAR", "CHAR", "TEXT", "INT", "BIGINT", "SMALLINT", "TINYINT", "DECIMAL", "FLOAT", "DOUBLE", "DATE", "DATETIME", "TIMESTAMP", "JSON", "BLOB"]
        else: # sqlite or fallback
            return ["INTEGER", "TEXT", "REAL", "NUMERIC", "BLOB"]

    def load_structure(self):
        self.column_table.setRowCount(0)
        self.sql_preview.clear()

        if self.is_new_table:
            self.original_columns = []
            self.column_table.blockSignals(True)
            self.column_table.setRowCount(1)
            
            # Column Name
            name_item = QTableWidgetItem("id")
            self.column_table.setItem(0, 0, name_item)
            
            # Type (QComboBox)
            type_combo = QComboBox()
            supported_types = self.get_supported_types()
            default_type = "INT" if self.db_engine.db_type == "mysql" else "serial"
            items = list(supported_types)
            if default_type not in items:
                items.append(default_type)
            type_combo.addItems(items)
            type_combo.setCurrentText(default_type)
            type_combo.currentTextChanged.connect(self.on_type_changed)
            self.column_table.setCellWidget(0, 1, type_combo)

            # Length
            self.column_table.setItem(0, 2, QTableWidgetItem(""))
            
            # Not Null (checked)
            nn_cb = _make_centered_checkbox(True)
            nn_cb._checkbox.stateChanged.connect(self.update_sql_preview)
            self.column_table.setCellWidget(0, 3, nn_cb)
            
            # Default
            self.column_table.setItem(0, 4, QTableWidgetItem(""))
            
            # Primary Key (checked)
            pk_cb = _make_centered_checkbox(True)
            pk_cb._checkbox.stateChanged.connect(self.update_sql_preview)
            self.column_table.setCellWidget(0, 5, pk_cb)
            
            # Auto Increment (checked)
            ai_cb = _make_centered_checkbox(True)
            ai_cb._checkbox.stateChanged.connect(self.update_sql_preview)
            self.column_table.setCellWidget(0, 6, ai_cb)
            
            # Comment
            self.column_table.setItem(0, 7, QTableWidgetItem(""))
            
            self.column_table.blockSignals(False)
            
            self.status_lbl.setText(f"🛠 Create Table: {self.schema}.{self.table_name}")
            self.update_sql_preview()
        else:
            self.status_lbl.setText("⏳ Loading table structure...")
            self.loader_worker = DesignerLoaderWorker(self.db_engine, self.schema, self.table_name)
            self.loader_worker.finished_signal.connect(self.on_structure_loaded)
            start_thread(self.loader_worker)

    def on_structure_loaded(self, columns, error_msg):
        if error_msg:
            self.status_lbl.setText("Error loading structure.")
            show_exception_dialog(self, "Load Error", f"Failed to load table structure:\n{error_msg}")
            return

        self.original_columns = [dict(c) for c in columns]  # deep copy
        self._populate_grid(columns)
        self.status_lbl.setText(f"🛠 Design: {self.schema}.{self.table_name} — {len(columns)} columns")
        self.update_sql_preview()

    def _populate_grid(self, columns):
        self.column_table.blockSignals(True)
        self.column_table.setRowCount(0)
        self.column_table.setRowCount(len(columns))

        supported_types = self.get_supported_types()

        for row_idx, col in enumerate(columns):
            # Column Name
            name_item = QTableWidgetItem(col["name"])
            self.column_table.setItem(row_idx, 0, name_item)

            # Parse base type and length
            base_type, length_str = parse_type_and_length(col["column_type"])

            # Type (QComboBox)
            type_combo = QComboBox()
            items = list(supported_types)
            match_found = False
            for item in items:
                if item.lower() == base_type.lower():
                    match_found = True
                    base_type = item
                    break
            if not match_found:
                items.append(base_type)
            type_combo.addItems(items)
            type_combo.setCurrentText(base_type)
            type_combo.currentTextChanged.connect(self.on_type_changed)
            self.column_table.setCellWidget(row_idx, 1, type_combo)

            # Length
            length_item = QTableWidgetItem(length_str)
            self.column_table.setItem(row_idx, 2, length_item)

            # Not Null (checkbox)
            nn_cb = _make_centered_checkbox(not col["nullable"])
            nn_cb._checkbox.stateChanged.connect(self.update_sql_preview)
            self.column_table.setCellWidget(row_idx, 3, nn_cb)

            # Default
            default_val = col["default"] if col["default"] is not None else ""
            default_item = QTableWidgetItem(str(default_val))
            self.column_table.setItem(row_idx, 4, default_item)

            # Primary Key (checkbox)
            pk_cb = _make_centered_checkbox(col["key"] == "PRI")
            pk_cb._checkbox.stateChanged.connect(self.update_sql_preview)
            self.column_table.setCellWidget(row_idx, 5, pk_cb)

            # Auto Increment (checkbox)
            ai_cb = _make_centered_checkbox("auto_increment" in col.get("extra", "").lower())
            ai_cb._checkbox.stateChanged.connect(self.update_sql_preview)
            self.column_table.setCellWidget(row_idx, 6, ai_cb)

            # Comment
            comment_item = QTableWidgetItem(col.get("comment", ""))
            self.column_table.setItem(row_idx, 7, comment_item)

        self.column_table.blockSignals(False)

    def _get_grid_columns(self):
        """Read the current state of the grid into a list of column dicts."""
        cols = []
        for row in range(self.column_table.rowCount()):
            name_item = self.column_table.item(row, 0)
            type_combo = self.column_table.cellWidget(row, 1)
            length_item = self.column_table.item(row, 2)
            nn_widget = self.column_table.cellWidget(row, 3)
            default_item = self.column_table.item(row, 4)
            pk_widget = self.column_table.cellWidget(row, 5)
            ai_widget = self.column_table.cellWidget(row, 6)
            comment_item = self.column_table.item(row, 7)

            name = name_item.text().strip() if name_item else ""
            base_type = type_combo.currentText().strip() if type_combo else ""
            length = length_item.text().strip() if length_item else ""
            
            if length:
                col_type = f"{base_type}({length})"
            else:
                col_type = base_type

            not_null = nn_widget._checkbox.isChecked() if nn_widget and hasattr(nn_widget, '_checkbox') else False
            default = default_item.text().strip() if default_item else ""
            is_pk = pk_widget._checkbox.isChecked() if pk_widget and hasattr(pk_widget, '_checkbox') else False
            is_ai = ai_widget._checkbox.isChecked() if ai_widget and hasattr(ai_widget, '_checkbox') else False
            comment = comment_item.text().strip() if comment_item else ""

            cols.append({
                "name": name,
                "column_type": col_type,
                "nullable": not not_null,
                "default": default if default else None,
                "key": "PRI" if is_pk else "",
                "extra": "auto_increment" if is_ai else "",
                "comment": comment
            })
        return cols

    def _generate_alter_sql(self):
        """Generate ALTER TABLE SQL statements by diffing original vs current grid state."""
        current_cols = self._get_grid_columns()
        original_names = {c["name"]: c for c in self.original_columns}
        current_names = {c["name"]: c for c in current_cols if c["name"]}
        q = self.db_engine._quote_ident
        table_ref = self.db_engine.quote_table_name(self.schema, self.table_name)
        db_type = self.db_engine.db_type

        statements = []

        # 1. Detect dropped columns
        for orig in self.original_columns:
            if orig["name"] not in current_names:
                statements.append(f"ALTER TABLE {table_ref} DROP COLUMN {q(orig['name'])};")

        # 2. Detect new columns and modifications
        prev_col_name = None
        for idx, cur in enumerate(current_cols):
            if not cur["name"] or not cur["column_type"]:
                continue

            if cur["name"] not in original_names:
                # New column
                col_def = self._build_column_def(cur, db_type)
                position = ""
                if db_type == "mysql":
                    if idx == 0:
                        position = " FIRST"
                    elif prev_col_name:
                        position = f" AFTER {q(prev_col_name)}"
                statements.append(f"ALTER TABLE {table_ref} ADD COLUMN {col_def}{position};")
            else:
                # Check for modifications
                orig = original_names[cur["name"]]
                changes = self._detect_changes(orig, cur)
                if changes:
                    if db_type == "mysql":
                        col_def = self._build_column_def(cur, db_type)
                        statements.append(f"ALTER TABLE {table_ref} MODIFY COLUMN {col_def};")
                    else:
                        # PostgreSQL: separate ALTER for each change
                        for change in changes:
                            statements.append(f"ALTER TABLE {table_ref} {change};")

            prev_col_name = cur["name"]

        # 3. Detect PK changes
        orig_pks = sorted([c["name"] for c in self.original_columns if c["key"] == "PRI"])
        cur_pks = sorted([c["name"] for c in current_cols if c["key"] == "PRI" and c["name"]])
        if orig_pks != cur_pks:
            if orig_pks:
                if db_type == "mysql":
                    statements.append(f"ALTER TABLE {table_ref} DROP PRIMARY KEY;")
                else:
                    # Find constraint name for PostgreSQL
                    statements.append(f"ALTER TABLE {table_ref} DROP CONSTRAINT IF EXISTS {q(self.table_name + '_pkey')};")
            if cur_pks:
                pk_cols = ", ".join([q(pk) for pk in cur_pks])
                statements.append(f"ALTER TABLE {table_ref} ADD PRIMARY KEY ({pk_cols});")

        return statements

    def _generate_create_sql(self):
        """Generate CREATE TABLE SQL statements from the current grid state."""
        current_cols = self._get_grid_columns()
        if not current_cols:
            return []

        q = self.db_engine._quote_ident
        table_ref = self.db_engine.quote_table_name(self.schema, self.table_name)
        db_type = self.db_engine.db_type

        col_defs = []
        pks = []
        comments = []

        for col in current_cols:
            if not col["name"] or not col["column_type"]:
                continue

            parts = [q(col["name"]), col["column_type"]]

            # Nullability
            if not col["nullable"]:
                parts.append("NOT NULL")
            else:
                if db_type == "mysql":
                    parts.append("NULL")

            # Default
            if col["default"]:
                parts.append(f"DEFAULT {col['default']}")

            # Auto increment (MySQL)
            if col["extra"] and "auto_increment" in col["extra"].lower():
                if db_type == "mysql":
                    parts.append("AUTO_INCREMENT")

            # Comment (MySQL)
            if col.get("comment") and db_type == "mysql":
                escaped = col["comment"].replace("'", "''")
                parts.append(f"COMMENT '{escaped}'")

            col_defs.append("    " + " ".join(parts))

            # Primary Key
            if col["key"] == "PRI":
                pks.append(q(col["name"]))

            # Comment (PostgreSQL)
            if col.get("comment") and db_type == "postgresql":
                escaped = col["comment"].replace("'", "''")
                comments.append(f"COMMENT ON COLUMN {table_ref}.{q(col['name'])} IS '{escaped}';")

        # Primary key constraint
        if pks:
            col_defs.append(f"    PRIMARY KEY ({', '.join(pks)})")

        sql = f"CREATE TABLE {table_ref} (\n" + ",\n".join(col_defs) + "\n);"

        statements = [sql]
        statements.extend(comments)

        return statements

    def _build_column_def(self, col, db_type):
        """Build a column definition string for ALTER TABLE ADD/MODIFY."""
        q = self.db_engine._quote_ident
        parts = [q(col["name"]), col["column_type"]]

        if not col["nullable"]:
            parts.append("NOT NULL")
        else:
            if db_type == "mysql":
                parts.append("NULL")

        if col["default"]:
            parts.append(f"DEFAULT {col['default']}")

        if col["extra"] and "auto_increment" in col["extra"].lower():
            if db_type == "mysql":
                parts.append("AUTO_INCREMENT")

        if col.get("comment") and db_type == "mysql":
            escaped = col["comment"].replace("'", "''")
            parts.append(f"COMMENT '{escaped}'")

        return " ".join(parts)

    def _detect_changes(self, orig, cur):
        """Detect differences between original and current column definition."""
        q = self.db_engine._quote_ident
        col_name = q(cur["name"])
        db_type = self.db_engine.db_type
        changes = []

        # Type change
        if orig["column_type"].lower().strip() != cur["column_type"].lower().strip():
            if db_type != "mysql":
                changes.append(f"ALTER COLUMN {col_name} TYPE {cur['column_type']}")

        # Nullability
        if orig["nullable"] != cur["nullable"]:
            if db_type != "mysql":
                if cur["nullable"]:
                    changes.append(f"ALTER COLUMN {col_name} DROP NOT NULL")
                else:
                    changes.append(f"ALTER COLUMN {col_name} SET NOT NULL")

        # Default
        orig_default = orig["default"] if orig["default"] else ""
        cur_default = cur["default"] if cur["default"] else ""
        if str(orig_default).strip() != str(cur_default).strip():
            if db_type != "mysql":
                if cur_default:
                    changes.append(f"ALTER COLUMN {col_name} SET DEFAULT {cur_default}")
                else:
                    changes.append(f"ALTER COLUMN {col_name} DROP DEFAULT")

        # Comment change
        if orig.get("comment", "") != cur.get("comment", ""):
            if db_type != "mysql":
                escaped = cur.get("comment", "").replace("'", "''")
                changes.append(f"-- Comment change for {cur['name']}: '{escaped}'")

        # For MySQL, detect if ANY property changed (will use MODIFY COLUMN)
        if db_type == "mysql":
            if (orig["column_type"].lower().strip() != cur["column_type"].lower().strip() or
                orig["nullable"] != cur["nullable"] or
                str(orig_default).strip() != str(cur_default).strip() or
                orig.get("extra", "").lower() != cur.get("extra", "").lower() or
                orig.get("comment", "") != cur.get("comment", "")):
                changes.append("__mysql_modify__")

        return changes

    def update_sql_preview(self, *args):
        """Regenerate the SQL preview from the current grid state."""
        try:
            if self.is_new_table:
                stmts = self._generate_create_sql()
            else:
                stmts = self._generate_alter_sql()
            if stmts:
                self.sql_preview.setPlainText("\n".join(stmts))
            else:
                self.sql_preview.setPlainText("")
        except Exception as e:
            self.sql_preview.setPlainText(f"-- Error generating SQL: {str(e)}")

    def on_type_changed(self, text):
        sender = self.sender()
        if not sender:
            return
            
        for row in range(self.column_table.rowCount()):
            if self.column_table.cellWidget(row, 1) == sender:
                if text.upper() in ("DECIMAL", "NUMERIC"):
                    length_item = self.column_table.item(row, 2)
                    if not length_item:
                        length_item = QTableWidgetItem("")
                        self.column_table.setItem(row, 2, length_item)
                    if not length_item.text().strip():
                        length_item.setText("10,2")
                break
                
        self.update_sql_preview()

    def add_column(self):
        self.column_table.blockSignals(True)
        row = self.column_table.rowCount()
        self.column_table.insertRow(row)

        # Column Name
        self.column_table.setItem(row, 0, QTableWidgetItem("new_column"))

        # Type (QComboBox)
        type_combo = QComboBox()
        supported_types = self.get_supported_types()
        default_type = "VARCHAR" if self.db_engine.db_type == "mysql" else "varchar"
        if self.db_engine.db_type == "sqlite":
            default_type = "TEXT"
        items = list(supported_types)
        if default_type not in items:
            items.append(default_type)
        type_combo.addItems(items)
        type_combo.setCurrentText(default_type)
        type_combo.currentTextChanged.connect(self.on_type_changed)
        self.column_table.setCellWidget(row, 1, type_combo)

        # Length
        default_len = "255" if default_type.lower() in ("varchar", "char") else ""
        self.column_table.setItem(row, 2, QTableWidgetItem(default_len))

        # Not Null (unchecked)
        nn_cb = _make_centered_checkbox(False)
        nn_cb._checkbox.stateChanged.connect(self.update_sql_preview)
        self.column_table.setCellWidget(row, 3, nn_cb)

        # Default
        self.column_table.setItem(row, 4, QTableWidgetItem(""))

        # Primary Key (unchecked)
        pk_cb = _make_centered_checkbox(False)
        pk_cb._checkbox.stateChanged.connect(self.update_sql_preview)
        self.column_table.setCellWidget(row, 5, pk_cb)

        # Auto Increment (unchecked)
        ai_cb = _make_centered_checkbox(False)
        ai_cb._checkbox.stateChanged.connect(self.update_sql_preview)
        self.column_table.setCellWidget(row, 6, ai_cb)

        # Comment
        self.column_table.setItem(row, 7, QTableWidgetItem(""))
        
        self.column_table.blockSignals(False)

        self.column_table.selectRow(row)
        self.column_table.scrollToItem(self.column_table.item(row, 0))
        self.update_sql_preview()

    def remove_column(self):
        row = self.column_table.currentRow()
        if row < 0:
            return
        name_item = self.column_table.item(row, 0)
        name = name_item.text() if name_item else "(unnamed)"

        reply = QMessageBox.question(
            self, "Confirm Remove",
            f"Remove column '{name}' from the design?\n\nThis will generate a DROP COLUMN statement when saved.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.column_table.removeRow(row)
            self.update_sql_preview()

    def move_row_up(self):
        row = self.column_table.currentRow()
        if row <= 0:
            return
        self._swap_rows(row, row - 1)
        self.column_table.selectRow(row - 1)
        self.update_sql_preview()

    def move_row_down(self):
        row = self.column_table.currentRow()
        if row < 0 or row >= self.column_table.rowCount() - 1:
            return
        self._swap_rows(row, row + 1)
        self.column_table.selectRow(row + 1)
        self.update_sql_preview()

    def _swap_rows(self, row_a, row_b):
        """Swap two rows in the column table."""
        self.column_table.blockSignals(True)

        data_a = self._read_row(row_a)
        data_b = self._read_row(row_b)
        self._write_row(row_a, data_b)
        self._write_row(row_b, data_a)

        self.column_table.blockSignals(False)

    def _read_row(self, row):
        """Read all values from a row into a dict."""
        name_item = self.column_table.item(row, 0)
        type_combo = self.column_table.cellWidget(row, 1)
        length_item = self.column_table.item(row, 2)
        nn_widget = self.column_table.cellWidget(row, 3)
        default_item = self.column_table.item(row, 4)
        pk_widget = self.column_table.cellWidget(row, 5)
        ai_widget = self.column_table.cellWidget(row, 6)
        comment_item = self.column_table.item(row, 7)

        return {
            "name": name_item.text() if name_item else "",
            "type": type_combo.currentText() if type_combo else "",
            "length": length_item.text() if length_item else "",
            "not_null": nn_widget._checkbox.isChecked() if nn_widget else False,
            "default": default_item.text() if default_item else "",
            "pk": pk_widget._checkbox.isChecked() if pk_widget else False,
            "ai": ai_widget._checkbox.isChecked() if ai_widget else False,
            "comment": comment_item.text() if comment_item else "",
        }

    def _write_row(self, row, data):
        """Write a dict of values into a row."""
        self.column_table.item(row, 0).setText(data["name"])
        
        type_combo = self.column_table.cellWidget(row, 1)
        if type_combo:
            idx = type_combo.findText(data["type"])
            if idx == -1:
                type_combo.addItem(data["type"])
                type_combo.setCurrentText(data["type"])
            else:
                type_combo.setCurrentIndex(idx)
                
        self.column_table.item(row, 2).setText(data["length"])

        nn_widget = self.column_table.cellWidget(row, 3)
        if nn_widget:
            nn_widget._checkbox.setChecked(data["not_null"])

        self.column_table.item(row, 4).setText(data["default"])

        pk_widget = self.column_table.cellWidget(row, 5)
        if pk_widget:
            pk_widget._checkbox.setChecked(data["pk"])

        ai_widget = self.column_table.cellWidget(row, 6)
        if ai_widget:
            ai_widget._checkbox.setChecked(data["ai"])

        self.column_table.item(row, 7).setText(data["comment"])

    def save_changes(self):
        if self.is_new_table:
            stmts = self._generate_create_sql()
        else:
            stmts = self._generate_alter_sql()

        if not stmts:
            QMessageBox.information(self, "No Changes", "No structural changes detected.")
            return

        sql_text = "\n".join(stmts)
        action_title = "Confirm CREATE TABLE" if self.is_new_table else "Confirm ALTER TABLE"
        reply = QMessageBox.question(
            self, action_title,
            f"Execute the following SQL?\n\n{sql_text}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.status_lbl.setText("⏳ Applying changes...")
        errors = []
        for stmt in stmts:
            try:
                self.db_engine.execute_query(stmt, fetch_results=False)
            except Exception as e:
                errors.append(f"{stmt}\n  → {str(e)}")

        if errors:
            show_exception_dialog(self, "Partial Error",
                f"Some statements failed:\n\n" + "\n\n".join(errors))
            self.status_lbl.setText("❌ Error applying changes.")
        else:
            self.status_lbl.setText("✅ Table created successfully!" if self.is_new_table else "✅ Changes saved successfully!")

            # Copy SQL to clipboard
            QApplication.clipboard().setText(sql_text)

            self.db_engine.clear_cache()

            if self.is_new_table:
                self.is_new_table = False
                main_win = self.window()
                if hasattr(main_win, "tabs"):
                    idx = main_win.tabs.indexOf(self)
                    if idx != -1:
                        main_win.tabs.setTabText(idx, f"🛠 {self.table_name}")

            # Refresh any matching ObjectTab
            main_win = self.window()
            if hasattr(main_win, "tabs"):
                for i in range(main_win.tabs.count()):
                    w = main_win.tabs.widget(i)
                    from src.ui.ObjectTabLogic import ObjectTab
                    if isinstance(w, ObjectTab):
                        if w.db_engine == self.db_engine and w.schema == self.schema and w.group_name == "Tables":
                            w.refresh_data()

        # Reload structure to reflect actual DB state
        self.load_structure()
