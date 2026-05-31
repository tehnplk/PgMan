from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QPushButton, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt
import psycopg

class ConnectionDialog(QDialog):
    def __init__(self, parent=None, profile=None):
        super().__init__(parent)
        self.profile = profile or {}
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("New Connection" if not self.profile else "Edit Connection")
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Input fields
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Local Postgres")
        self.name_input.setText(self.profile.get("name", ""))

        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("localhost")
        self.host_input.setText(self.profile.get("host", "localhost"))

        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("5432")
        self.port_input.setText(str(self.profile.get("port", "5432")))

        self.db_input = QLineEdit()
        self.db_input.setPlaceholderText("postgres")
        self.db_input.setText(self.profile.get("database", "postgres"))

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("postgres")
        self.user_input.setText(self.profile.get("username", "postgres"))

        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("password")
        self.pass_input.setText(self.profile.get("password", ""))

        self.ssl_combo = QComboBox()
        self.ssl_combo.addItems(["disable", "allow", "prefer", "require", "verify-ca", "verify-full"])
        self.ssl_combo.setCurrentText(self.profile.get("sslmode", "prefer"))

        # Add to form
        form_layout.addRow("Connection Name:", self.name_input)
        form_layout.addRow("Host:", self.host_input)
        form_layout.addRow("Port:", self.port_input)
        form_layout.addRow("Database:", self.db_input)
        form_layout.addRow("Username:", self.user_input)
        form_layout.addRow("Password:", self.pass_input)
        form_layout.addRow("SSL Mode:", self.ssl_combo)

        layout.addLayout(form_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.test_connection)
        self.test_btn.setObjectName("testBtn")

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setObjectName("saveBtn")

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setObjectName("cancelBtn")

        btn_layout.addWidget(self.test_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

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
        
        # We run the psycopg connection synchronously for simple testing in dialog
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
