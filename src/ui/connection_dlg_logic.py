from PyQt6.QtWidgets import QMessageBox, QDialog
import psycopg
from src.ui.connection_dlg_ui import ConnectionDialogUI

class ConnectionDialog(ConnectionDialogUI):
    def __init__(self, parent=None, profile=None):
        super().__init__(parent, profile)
        
        # Bind signals to slot handlers
        self.test_btn.clicked.connect(self.test_connection)
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

    def get_data(self):
        return {
            "id": self.profile.get("id", ""),
            "name": self.name_input.text().strip() or f"{self.host_input.text().strip() or 'localhost'}:{self.port_input.text().strip() or '5432'}",
            "host": self.host_input.text().strip() or "localhost",
            "port": int(self.port_input.text().strip() or 5432),
            "database": self.db_input.text().strip() or "postgres",
            "username": self.user_input.text().strip() or "postgres",
            "password": self.pass_input.text(),
            "sslmode": self.ssl_combo.currentText()
        }

    def test_connection(self):
        data = self.get_data()
        self.test_btn.setEnabled(False)
        self.test_btn.setText("Testing...")
        
        try:
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
            QMessageBox.information(self, "Success", "Connection tested successfully!", QMessageBox.StandardButton.Ok)
        except Exception as e:
            QMessageBox.critical(self, "Connection Failed", f"Could not connect to database:\n{str(e)}", QMessageBox.StandardButton.Ok)
        finally:
            self.test_btn.setEnabled(True)
            self.test_btn.setText("Test Connection")
