from PyQt6.QtWidgets import QMessageBox, QDialog
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
        
        # Handle database type changes
        self.db_type_combo.currentTextChanged.connect(self.on_db_type_changed)
        self.on_db_type_changed(self.db_type_combo.currentText())

    def on_db_type_changed(self, db_type):
        is_pg = (db_type == "PostgreSQL")
        
        # Toggle SSL mode fields
        self.ssl_label.setVisible(is_pg)
        self.ssl_combo.setVisible(is_pg)
        
        # Set database type-specific defaults
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

    def get_data(self):
        db_type = self.db_type_combo.currentText()
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
            if data["db_type"] == "PostgreSQL":
                conn = psycopg.connect(
                    host=data["host"],
                    port=data["port"],
                    dbname=data["database"],
                    user=data["username"],
                    password=data["password"],
                    sslmode=data["sslmode"],
                    connect_timeout=4
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
                    connect_timeout=4
                )
                conn.close()
            QMessageBox.information(self, "Success", "Connection tested successfully!", QMessageBox.StandardButton.Ok)
        except Exception as e:
            show_exception_dialog(self, "Connection Failed", f"Could not connect to database:\n{str(e)}")
        finally:
            self.test_btn.setEnabled(True)
            self.test_btn.setText("Test Connection")
