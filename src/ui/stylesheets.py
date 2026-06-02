import os
import sys
import base64

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path).replace('\\', '/')
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, relative_path).replace('\\', '/')

# Dark Theme QSS Template
DARK_THEME_TEMPLATE = """
/* Global Styles */
QWidget {
    background-color: #1e222b;
    color: #abb2bf;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

/* Main Window & Sidebar Splitter */
QSplitter::handle {
    background-color: #181a1f;
    width: 2px;
    height: 2px;
}

/* Tree Widget / Database Explorer */
QTreeView, QTreeWidget {
    background-color: #181a1f;
    border: none;
    border-right: 1px solid #282c34;
    padding: 5px;
    outline: none;
    show-decoration-selected: 0;
}

QTreeView::item, QTreeWidget::item {
    height: 28px;
    padding-left: 10px;
    border-radius: 4px;
    margin: 1px 0px;
    border: none;
    outline: none;
}

QTreeView::item:hover, QTreeWidget::item:hover {
    background-color: #2c313c;
    color: #00e5ff;
    border: none;
    outline: none;
}

QTreeView::item:selected, QTreeWidget::item:selected {
    background-color: #3e4451;
    color: #ffffff;
    border: none;
    outline: none;
}

QTreeView::branch, QTreeWidget::branch {
    background: transparent !important;
    background-color: transparent !important;
}

QTreeView::branch:selected, QTreeWidget::branch:selected,
QTreeView::branch:hover, QTreeWidget::branch:hover {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    outline: none !important;
}

QTreeView::branch:has-siblings, QTreeWidget::branch:has-siblings,
QTreeView::branch:has-siblings:adjoining-item, QTreeWidget::branch:has-siblings:adjoining-item,
QTreeView::branch:!has-children:!has-siblings:adjoining-item, QTreeWidget::branch:!has-children:!has-siblings:adjoining-item {
    image: none !important;
    border-image: none !important;
    background: transparent !important;
    background-color: transparent !important;
}

QTreeView::branch:has-children:!has-siblings:closed, QTreeWidget::branch:has-children:!has-siblings:closed,
QTreeView::branch:closed:has-children:has-siblings, QTreeWidget::branch:closed:has-children:has-siblings {
    image: url(plus.svg);
}

QTreeView::branch:open:has-children:!has-siblings, QTreeWidget::branch:open:has-children:!has-siblings,
QTreeView::branch:open:has-children:has-siblings, QTreeWidget::branch:open:has-children:has-siblings {
    image: url(minus.svg);
}

/* Table Widget / Data Grids */
QTableView, QTableWidget {
    background-color: #181a1f;
    border: 1px solid #282c34;
    gridline-color: #2c313c;
    selection-background-color: #3e4451;
    selection-color: #ffffff;
    border-radius: 6px;
}

QHeaderView::section {
    background-color: #21252b;
    color: #abb2bf;
    padding: 6px;
    border: 1px solid #181a1f;
    font-weight: bold;
}

QHeaderView::section:horizontal {
    border-top: none;
    border-left: none;
}

QHeaderView::section:vertical {
    border-left: none;
    border-top: none;
    background-color: #181a1f;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #282c34;
    background-color: #1e222b;
    border-radius: 6px;
}

QTabBar::tab {
    background-color: #21252b;
    border: 1px solid #282c34;
    border-bottom: none;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
    color: #8c92ac;
}

QTabBar::tab:selected {
    background-color: #1e222b;
    border-bottom: 2px solid #00e5ff;
    color: #00e5ff;
    font-weight: bold;
}

QTabBar::tab:hover:!selected {
    background-color: #2c313c;
    color: #abb2bf;
}

/* Input Fields (QLineEdit, QTextEdit) */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #181a1f;
    border: 1px solid #3e4451;
    border-radius: 4px;
    padding: 6px;
    color: #abb2bf;
    selection-background-color: #3e4451;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #00e5ff;
}

/* Buttons */
QPushButton {
    background-color: #21252b;
    border: 1px solid #3e4451;
    border-radius: 4px;
    padding: 6px 12px;
    color: #abb2bf;
    min-width: 60px;
}

QPushButton:hover {
    background-color: #2c313c;
    border-color: #00e5ff;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #181a1f;
}

QPushButton:disabled {
    background-color: #1a1c23;
    color: #5c6370;
    border-color: #282c34;
}

/* Primary/Special Buttons (e.g. Save, Test Connection, Run) */
QPushButton#saveBtn, QPushButton#testBtn, QPushButton#runBtn {
    background-color: #00bfa5;
    border: 1px solid #00bfa5;
    color: #1e222b;
    font-weight: bold;
}

QPushButton#saveBtn:hover, QPushButton#testBtn:hover, QPushButton#runBtn:hover {
    background-color: #00e5ff;
    border-color: #00e5ff;
    color: #1e222b;
}

QPushButton:checked {
    background-color: #00bfa5;
    border-color: #00bfa5;
    color: #1e222b;
    font-weight: bold;
}

/* List Widget */
QListWidget {
    background-color: #181a1f;
    border: 1px solid #282c34;
    border-radius: 6px;
    padding: 5px;
    outline: none;
}

QListWidget::item {
    padding: 6px;
    border-radius: 4px;
    color: #abb2bf;
}

QListWidget::item:hover {
    background-color: #2c313c;
    color: #00e5ff;
}

QListWidget::item:selected {
    background-color: #3e4451;
    color: #ffffff;
}

QPushButton#cancelBtn {
    background-color: #2c313c;
    color: #abb2bf;
}

QPushButton#stopBtn {
    background-color: #e06c75;
    border-color: #e06c75;
    color: #1e222b;
    font-weight: bold;
}

QPushButton#stopBtn:hover {
    background-color: #ff808a;
    border-color: #ff808a;
}

/* ComboBox */
QComboBox {
    background-color: #181a1f;
    border: 1px solid #3e4451;
    border-radius: 4px;
    padding: 6px;
    color: #abb2bf;
}

QComboBox:on {
    border-color: #00e5ff;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #181a1f;
    border: 1px solid #3e4451;
    selection-background-color: #3e4451;
    selection-color: #ffffff;
}

/* Menu Widget */
QMenu {
    background-color: #21252b;
    border: 1px solid #3e4451;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 20px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #3e4451;
    color: #00e5ff;
}

QMenu::separator {
    height: 1px;
    background-color: #3e4451;
    margin: 4px 0px;
}

/* Dialog Styling */
QDialog {
    background-color: #1e222b;
}

/* ToolBar & Status Bar */
QToolBar {
    background-color: #21252b;
    border-bottom: 1px solid #181a1f;
    spacing: 5px;
    padding: 4px;
}

QStatusBar {
    background-color: #21252b;
    border-top: 1px solid #181a1f;
    color: #5c6370;
}

/* ScrollBars */
QScrollBar:vertical {
    border: none;
    background-color: #181a1f;
    width: 10px;
    margin: 0px 0 0px 0;
}

QScrollBar::handle:vertical {
    background-color: #3e4451;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #00e5ff;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

QScrollBar:horizontal {
    border: none;
    background-color: #181a1f;
    height: 10px;
    margin: 0px 0 0px 0;
}

QScrollBar::handle:horizontal {
    background-color: #3e4451;
    min-width: 20px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #00e5ff;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
}

/* Labels & Groupboxes */
QLabel {
    background-color: transparent;
    color: #abb2bf;
}

QGroupBox {
    border: 1px solid #3e4451;
    border-radius: 6px;
    margin-top: 12px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 3px;
    color: #00e5ff;
}
"""

# Light Theme QSS Template
LIGHT_THEME_TEMPLATE = """
/* Global Styles */
QWidget {
    background-color: #f6f8fa;
    color: #24292f;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

/* Main Window & Sidebar Splitter */
QSplitter::handle {
    background-color: #d0d7de;
    width: 2px;
    height: 2px;
}

/* Tree Widget / Database Explorer */
QTreeView, QTreeWidget {
    background-color: #ffffff;
    border: none;
    border-right: 1px solid #d0d7de;
    padding: 5px;
    outline: none;
    show-decoration-selected: 0;
}

QTreeView::item, QTreeWidget::item {
    height: 28px;
    padding-left: 10px;
    border-radius: 4px;
    margin: 1px 0px;
    border: none;
    outline: none;
}

QTreeView::item:hover, QTreeWidget::item:hover {
    background-color: #eaeef2;
    color: #0969da;
    border: none;
    outline: none;
}

QTreeView::item:selected, QTreeWidget::item:selected {
    background-color: #e2e8f0;
    color: #0969da;
    border: none;
    outline: none;
}

QTreeView::branch, QTreeWidget::branch {
    background: transparent !important;
    background-color: transparent !important;
}

QTreeView::branch:selected, QTreeWidget::branch:selected,
QTreeView::branch:hover, QTreeWidget::branch:hover {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    outline: none !important;
}

QTreeView::branch:has-siblings, QTreeWidget::branch:has-siblings,
QTreeView::branch:has-siblings:adjoining-item, QTreeWidget::branch:has-siblings:adjoining-item,
QTreeView::branch:!has-children:!has-siblings:adjoining-item, QTreeWidget::branch:!has-children:!has-siblings:adjoining-item {
    image: none !important;
    border-image: none !important;
    background: transparent !important;
    background-color: transparent !important;
}

QTreeView::branch:has-children:!has-siblings:closed, QTreeWidget::branch:has-children:!has-siblings:closed,
QTreeView::branch:closed:has-children:has-siblings, QTreeWidget::branch:closed:has-children:has-siblings {
    image: url(plus.svg);
}

QTreeView::branch:open:has-children:!has-siblings, QTreeWidget::branch:open:has-children:!has-siblings,
QTreeView::branch:open:has-children:has-siblings, QTreeWidget::branch:open:has-children:has-siblings {
    image: url(minus.svg);
}

/* Table Widget / Data Grids */
QTableView, QTableWidget {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    gridline-color: #eaeef2;
    selection-background-color: #e2e8f0;
    selection-color: #0969da;
    border-radius: 6px;
}

QHeaderView::section {
    background-color: #f6f8fa;
    color: #57606a;
    padding: 6px;
    border: 1px solid #d0d7de;
    font-weight: bold;
}

QHeaderView::section:horizontal {
    border-top: none;
    border-left: none;
}

QHeaderView::section:vertical {
    border-left: none;
    border-top: none;
    background-color: #ffffff;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #d0d7de;
    background-color: #f6f8fa;
    border-radius: 6px;
}

QTabBar::tab {
    background-color: #eaeef2;
    border: 1px solid #d0d7de;
    border-bottom: none;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
    color: #57606a;
}

QTabBar::tab:selected {
    background-color: #f6f8fa;
    border-bottom: 2px solid #0969da;
    color: #0969da;
    font-weight: bold;
}

QTabBar::tab:hover:!selected {
    background-color: #eaeef2;
    color: #24292f;
}

/* Input Fields (QLineEdit, QTextEdit) */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 4px;
    padding: 6px;
    color: #24292f;
    selection-background-color: #e2e8f0;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #0969da;
}

/* Buttons */
QPushButton {
    background-color: #f6f8fa;
    border: 1px solid #d0d7de;
    border-radius: 4px;
    padding: 6px 12px;
    color: #24292f;
    min-width: 60px;
}

QPushButton:hover {
    background-color: #eaeef2;
    border-color: #0969da;
    color: #0969da;
}

QPushButton:pressed {
    background-color: #e2e8f0;
}

QPushButton:disabled {
    background-color: #fafbfc;
    color: #57606a;
    border-color: #eaeef2;
}

/* Primary/Special Buttons (e.g. Save, Test Connection, Run) */
QPushButton#saveBtn, QPushButton#testBtn, QPushButton#runBtn {
    background-color: #2da44e;
    border: 1px solid #2da44e;
    color: #ffffff;
    font-weight: bold;
}

QPushButton#saveBtn:hover, QPushButton#testBtn:hover, QPushButton#runBtn:hover {
    background-color: #2c974b;
    border-color: #2c974b;
    color: #ffffff;
}

QPushButton:checked {
    background-color: #2da44e;
    border-color: #2da44e;
    color: #ffffff;
    font-weight: bold;
}

/* List Widget */
QListWidget {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 5px;
    outline: none;
}

QListWidget::item {
    padding: 6px;
    border-radius: 4px;
    color: #24292f;
}

QListWidget::item:hover {
    background-color: #eaeef2;
    color: #0969da;
}

QListWidget::item:selected {
    background-color: #e2e8f0;
    color: #0969da;
}

QPushButton#cancelBtn {
    background-color: #f6f8fa;
    color: #57606a;
}

QPushButton#stopBtn {
    background-color: #cf222e;
    border-color: #cf222e;
    color: #ffffff;
    font-weight: bold;
}

QPushButton#stopBtn:hover {
    background-color: #b31d27;
    border-color: #b31d27;
}

/* ComboBox */
QComboBox {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 4px;
    padding: 6px;
    color: #24292f;
}

QComboBox:on {
    border-color: #0969da;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    selection-background-color: #e2e8f0;
    selection-color: #0969da;
}

/* Menu Widget */
QMenu {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 20px;
    border-radius: 4px;
    color: #24292f;
}

QMenu::item:selected {
    background-color: #eaeef2;
    color: #0969da;
}

QMenu::separator {
    height: 1px;
    background-color: #d0d7de;
    margin: 4px 0px;
}

/* Dialog Styling */
QDialog {
    background-color: #f6f8fa;
}

/* ToolBar & Status Bar */
QToolBar {
    background-color: #f6f8fa;
    border-bottom: 1px solid #d0d7de;
    spacing: 5px;
    padding: 4px;
}

QStatusBar {
    background-color: #f6f8fa;
    border-top: 1px solid #d0d7de;
    color: #57606a;
}

/* ScrollBars */
QScrollBar:vertical {
    border: none;
    background-color: #fafbfc;
    width: 10px;
    margin: 0px 0 0px 0;
}

QScrollBar::handle:vertical {
    background-color: #d0d7de;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #0969da;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

QScrollBar:horizontal {
    border: none;
    background-color: #fafbfc;
    height: 10px;
    margin: 0px 0 0px 0;
}

QScrollBar::handle:horizontal {
    background-color: #d0d7de;
    min-width: 20px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #0969da;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
}

/* Labels & Groupboxes */
QLabel {
    background-color: transparent;
    color: #24292f;
}

QGroupBox {
    border: 1px solid #d0d7de;
    border-radius: 6px;
    margin-top: 12px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 3px;
    color: #0969da;
}
"""

# Resolve SVG file paths
dark_closed = f'url("{get_resource_path("resources/plus_dark.svg")}")'
dark_open = f'url("{get_resource_path("resources/minus_dark.svg")}")'

light_closed = f'url("{get_resource_path("resources/plus_light.svg")}")'
light_open = f'url("{get_resource_path("resources/minus_light.svg")}")'

# Apply replacements to the stylesheets
DARK_THEME_QSS = DARK_THEME_TEMPLATE.replace("url(plus.svg)", dark_closed).replace("url(minus.svg)", dark_open)
LIGHT_THEME_QSS = LIGHT_THEME_TEMPLATE.replace("url(plus.svg)", light_closed).replace("url(minus.svg)", light_open)

def get_theme_qss(theme_name):
    if theme_name.lower() == "light":
        return LIGHT_THEME_QSS
    return DARK_THEME_QSS
