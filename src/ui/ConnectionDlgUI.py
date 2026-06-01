from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QPushButton, QLabel
)

class ConnectionDialogUI(QDialog):
    def __init__(self, parent=None, profile=None):
        super().__init__(parent)
        self.profile = profile or {}
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("New Connection" if not self.profile else "Edit Connection")
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()

        # Database Type selection
        self.db_type_combo = QComboBox()
        self.db_type_combo.addItems(["PostgreSQL", "MySQL", "SQLite"])
        self.db_type_combo.setCurrentText(self.profile.get("db_type", "PostgreSQL"))

        # Connection Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Local Postgres")
        self.name_input.setText(self.profile.get("name", ""))

        # --- Server-mode fields ---
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

        # SSL fields
        self.ssl_label = QLabel("SSL Mode:")
        self.ssl_combo = QComboBox()
        self.ssl_combo.addItems(["disable", "allow", "prefer", "require", "verify-ca", "verify-full"])
        self.ssl_combo.setCurrentText(self.profile.get("sslmode", "prefer"))

        # --- SQLite file-mode fields ---
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("Path to .db or .sqlite file")
        self.file_input.setText(self.profile.get("file_path", ""))

        self.browse_btn = QPushButton("Browse…")
        self.browse_btn.setObjectName("browseBtn")
        self.browse_btn.setFixedWidth(80)

        self.new_file_btn = QPushButton("New…")
        self.new_file_btn.setObjectName("newFileBtn")
        self.new_file_btn.setFixedWidth(60)

        file_row = QHBoxLayout()
        file_row.addWidget(self.file_input)
        file_row.addWidget(self.browse_btn)
        file_row.addWidget(self.new_file_btn)

        # Add to form — store labels for show/hide
        self.form_layout.addRow("Database Type:", self.db_type_combo)
        self.form_layout.addRow("Connection Name:", self.name_input)

        # Server-mode rows (keep label references for toggling)
        self.host_label = QLabel("Host:")
        self.port_label = QLabel("Port:")
        self.db_label = QLabel("Database:")
        self.user_label = QLabel("Username:")
        self.pass_label = QLabel("Password:")

        self.form_layout.addRow(self.host_label, self.host_input)
        self.form_layout.addRow(self.port_label, self.port_input)
        self.form_layout.addRow(self.db_label, self.db_input)
        self.form_layout.addRow(self.user_label, self.user_input)
        self.form_layout.addRow(self.pass_label, self.pass_input)
        self.form_layout.addRow(self.ssl_label, self.ssl_combo)

        # SQLite file row
        self.file_label = QLabel("Database File:")
        self.form_layout.addRow(self.file_label, file_row)

        layout.addLayout(self.form_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.setObjectName("testBtn")

        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("saveBtn")

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancelBtn")

        btn_layout.addWidget(self.test_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)
