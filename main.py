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
    
    # 2. Simulate progressive modern loading messages smoothly
    loading_steps = [
        (30, "Loading database configurations..."),
        (65, "Initializing UI subsystems..."),
        (100, "Loading database explorer module...")
    ]
    
    current_progress = 0
    for target_progress, message in loading_steps:
        splash.showMessage(message, current_progress)
        while current_progress < target_progress:
            current_progress += 1
            splash.setProgress(current_progress)
            app.processEvents()
            time.sleep(0.005)

    # 3. Initialize & show main window
    window = MainWindow()
    splash.finish(window)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
