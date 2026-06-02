import os
import sqlite3
from PyQt6.QtWidgets import QMessageBox, QDialog, QFileDialog
import psycopg
from src.ui.ConnectionDlgUI import ConnectionDialogUI
from src.ui.UiUtils import show_exception_dialog

class ConnectionDialog(ConnectionDialogUI):
    def __init__(self, parent=None, profile=None):
        super().__init__(parent, profile)
        
        # Bind signals to slot handlers
        self.test_btn.clicked.connect(self.test_connection)
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        
        # SQLite file buttons
        self.browse_btn.clicked.connect(self.browse_file)
        self.new_file_btn.clicked.connect(self.create_new_file)
        
        # Handle database type changes
        self.db_type_combo.currentTextChanged.connect(self.on_db_type_changed)
        self.on_db_type_changed(self.db_type_combo.currentText())

    def _set_server_fields_visible(self, visible):
        """Show or hide all server-mode fields (host, port, db, user, pass, ssl)."""
        for widget in (self.host_label, self.host_input,
                       self.port_label, self.port_input,
                       self.db_label, self.db_input,
                       self.user_label, self.user_input,
                       self.pass_label, self.pass_input):
            widget.setVisible(visible)

    def _set_sqlite_fields_visible(self, visible):
        """Show or hide SQLite file-mode fields."""
        self.file_label.setVisible(visible)
        self.file_input.setVisible(visible)
        self.browse_btn.setVisible(visible)
        self.new_file_btn.setVisible(visible)

    def on_db_type_changed(self, db_type):
        is_pg = (db_type == "PostgreSQL")
        is_sqlite = (db_type == "SQLite")
        
        # Toggle SSL mode fields (PostgreSQL only)
        self.ssl_label.setVisible(is_pg)
        self.ssl_combo.setVisible(is_pg)
        
        # Toggle server vs file fields
        self._set_server_fields_visible(not is_sqlite)
        self._set_sqlite_fields_visible(is_sqlite)
        
        if is_sqlite:
            return
        
        # Set database type-specific defaults for server modes
        current_port = self.port_input.text().strip()
        current_db = self.db_input.text().strip()
        current_user = self.user_input.text().strip()

        if is_pg:
            if current_port in ("", "3306"):
                self.port_input.setText("5432")
            if current_db == "":
                self.db_input.setText("postgres")
            if current_user in ("", "root"):
                self.user_input.setText("postgres")
        else:
            if current_port in ("", "5432"):
                self.port_input.setText("3306")
            if current_db == "postgres":
                self.db_input.setText("")
            if current_user in ("", "postgres"):
                self.user_input.setText("root")

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select SQLite Database",
            "",
            "SQLite Database (*.db *.sqlite *.sqlite3 *.s3db);;All Files (*)"
        )
        if file_path:
            self.file_input.setText(file_path)
            # Auto-fill connection name from filename if empty
            if not self.name_input.text().strip():
                self.name_input.setText(os.path.basename(file_path))

    def create_new_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Create New SQLite Database",
            "",
            "SQLite Database (*.db);;SQLite Database (*.sqlite);;All Files (*)"
        )
        if file_path:
            # Create the empty database file
            try:
                conn = sqlite3.connect(file_path)
                conn.close()
            except Exception as e:
                show_exception_dialog(self, "Error", f"Could not create database file:\n{str(e)}")
                return
            self.file_input.setText(file_path)
            if not self.name_input.text().strip():
                self.name_input.setText(os.path.basename(file_path))

    def get_data(self):
        db_type = self.db_type_combo.currentText()
        
        if db_type == "SQLite":
            file_path = self.file_input.text().strip()
            return {
                "id": self.profile.get("id", ""),
                "db_type": db_type,
                "name": self.name_input.text().strip() or os.path.basename(file_path) or "SQLite",
                "file_path": file_path,
                "host": "",
                "port": 0,
                "database": os.path.basename(file_path),
                "username": "",
                "password": "",
                "sslmode": ""
            }
        
        default_port = 5432 if db_type == "PostgreSQL" else 3306
        default_user = "postgres" if db_type == "PostgreSQL" else "root"
        
        return {
            "id": self.profile.get("id", ""),
            "db_type": db_type,
            "name": self.name_input.text().strip() or f"{self.host_input.text().strip() or 'localhost'}:{self.port_input.text().strip() or default_port}",
            "host": self.host_input.text().strip() or "localhost",
            "port": int(self.port_input.text().strip() or default_port),
            "database": self.db_input.text().strip(),
            "username": self.user_input.text().strip() or default_user,
            "password": self.pass_input.text(),
            "sslmode": self.ssl_combo.currentText()
        }

    def test_connection(self):
        data = self.get_data()
        self.test_btn.setEnabled(False)
        self.test_btn.setText("Testing...")
        
        try:
            if data["db_type"] == "SQLite":
                file_path = data.get("file_path", "")
                if not file_path:
                    raise ValueError("No database file specified.")
                conn = sqlite3.connect(file_path)
                # Verify it's a valid SQLite database
                conn.execute("SELECT 1")
                conn.close()
            elif data["db_type"] == "PostgreSQL":
                conn = psycopg.connect(
                    host=data["host"],
                    port=data["port"],
                    dbname=data["database"],
                    user=data["username"],
                    password=data["password"],
                    sslmode=data["sslmode"],
                    connect_timeout=5
                )
                conn.close()
            else:
                import pymysql
                conn = pymysql.connect(
                    host=data["host"],
                    port=data["port"],
                    database=data["database"] if data["database"] else None,
                    user=data["username"],
                    password=data["password"],
                    connect_timeout=5
                )
                conn.close()
            QMessageBox.information(self, "Success", "Connection tested successfully!", QMessageBox.StandardButton.Ok)
        except Exception as e:
            show_exception_dialog(self, "Connection Failed", f"Could not connect to database:\n{str(e)}")
        finally:
            self.test_btn.setEnabled(True)
            self.test_btn.setText("Test Connection")
