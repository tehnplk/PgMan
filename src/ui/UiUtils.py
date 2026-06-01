from PyQt6.QtWidgets import QMessageBox, QApplication
from PyQt6.QtCore import Qt

def resize_columns_fast(table_view, columns, rows, max_scan_rows=50):
    if not columns:
        return
        
    fm = table_view.fontMetrics()
    # Initialize widths based on column name text length
    widths = [max(fm.horizontalAdvance(str(col)) + 30, 80) for col in columns]
    
    # Scan first max_scan_rows rows to find the max content width for each column
    for row in rows[:max_scan_rows]:
        for col_idx, val in enumerate(row):
            if col_idx < len(widths):
                if val is not None:
                    val_str = str(val)
                    if len(val_str) > 100:  # Limit string length check for performance
                        val_str = val_str[:100] + "..."
                    w = fm.horizontalAdvance(val_str) + 24
                    if w > widths[col_idx]:
                        widths[col_idx] = w
                        
    # Apply widths to column headers, capped at 300px
    for col_idx, width in enumerate(widths):
        table_view.setColumnWidth(col_idx, min(width, 300))

def show_exception_dialog(parent, title, message):
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    
    # Add custom Copy Details action button along with default OK button
    copy_btn = msg_box.addButton("Copy Details", QMessageBox.ButtonRole.ActionRole)
    msg_box.addButton(QMessageBox.StandardButton.Ok)
    
    msg_box.exec()
    
    # Copy details if clicked
    if msg_box.clickedButton() == copy_btn:
        QApplication.clipboard().setText(message)
