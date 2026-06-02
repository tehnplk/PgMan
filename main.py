import sys
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QSettings
from src.ui.MainWindowLogic import MainWindow
from src.ui.Stylesheets import get_theme_qss
from src.ui.ModernSplashScreen import ModernSplashScreen

def main():
    if sys.platform == 'win32':
        import ctypes
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("tehnplk.pgman.client.1.0")
        except Exception:
            pass

    app = QApplication(sys.argv)
    
    # Load and apply theme from settings (default to dark)
    settings = QSettings("PgMan", "ThemeSettings")
    theme = settings.value("theme", "dark")
    app.setStyleSheet(get_theme_qss(theme))

    # 1. Initialize Modern Splash Screen
    splash = ModernSplashScreen(theme=theme)
    splash.show()
    
    # 2. Simulate progressive modern loading messages
    splash.showMessage("Loading database configurations...", 30)
    app.processEvents()
    time.sleep(0.5)

    splash.showMessage("Initializing UI subsystems...", 65)
    app.processEvents()
    time.sleep(0.5)

    splash.showMessage("Loading database explorer module...", 100)
    app.processEvents()
    time.sleep(0.4)

    # 3. Initialize & show main window
    window = MainWindow()
    splash.finish(window)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
