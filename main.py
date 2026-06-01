import sys
import time
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QPixmap, QColor, QFont
from PyQt6.QtCore import Qt, QSettings
from src.ui.MainWindowLogic import MainWindow
from src.ui.Stylesheets import get_theme_qss, get_resource_path

def main():
    app = QApplication(sys.argv)
    
    # Load and apply theme from settings (default to dark)
    settings = QSettings("PgMan", "ThemeSettings")
    theme = settings.value("theme", "dark")
    app.setStyleSheet(get_theme_qss(theme))

    # 1. Initialize Splash Screen
    pixmap = QPixmap(get_resource_path("resources/app_icon.png"))
    pixmap = pixmap.scaled(320, 320, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    
    splash = QSplashScreen(pixmap)
    splash.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
    
    # Configure font style for loading messages
    font = QFont("Segoe UI", 10)
    font.setBold(True)
    splash.setFont(font)
    
    splash.show()
    
    # 2. Simulate progressive modern loading messages
    text_color = QColor("#00e5ff")  # Neon cyan accent color
    
    splash.showMessage("Loading database configurations...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, text_color)
    app.processEvents()
    time.sleep(0.5)

    splash.showMessage("Initializing UI subsystems...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, text_color)
    app.processEvents()
    time.sleep(0.5)

    splash.showMessage("Loading database explorer module...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, text_color)
    app.processEvents()
    time.sleep(0.4)

    # 3. Initialize & show main window
    window = MainWindow()
    splash.finish(window)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
