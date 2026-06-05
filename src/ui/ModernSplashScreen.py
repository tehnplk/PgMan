import sys
from PyQt6.QtWidgets import QSplashScreen
from PyQt6.QtGui import QPixmap, QColor, QFont, QPainter, QLinearGradient, QPen
from PyQt6.QtCore import Qt, QRect
from src.ui.Stylesheets import get_resource_path
from src.Version import version_name, version_release

class ModernSplashScreen(QSplashScreen):
    def __init__(self, theme="dark"):
        self.theme = theme.lower()
        
        # Dimensions including the shadow margin (12px on each side)
        self.shadow_margin = 12
        self.width = 500 + (self.shadow_margin * 2)
        self.height = 300 + (self.shadow_margin * 2)
        
        # Create a transparent pixmap to define splash size
        pixmap = QPixmap(self.width, self.height)
        pixmap.fill(Qt.GlobalColor.transparent)
        super().__init__(pixmap)
        
        # Setup frameless and translucent background window attributes
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.SplashScreen
        )
        
        # Initial status message and progress
        self._message = "Initializing components..."
        self._progress = 0
        
        # Load and scale app icon
        logo_path = get_resource_path("resources/app_icon.png")
        self.logo_pixmap = QPixmap(logo_path)
        if not self.logo_pixmap.isNull():
            self.logo_pixmap = self.logo_pixmap.scaled(
                90, 90,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
        # Define theme-specific styling attributes
        if self.theme == "light":
            self.bg_start = QColor("#ffffff")
            self.bg_end = QColor("#f6f8fa")
            self.accent_color = QColor("#0969da")  # GitHub Blue
            self.border_end = QColor("#d0d7de")
            self.title_color = QColor("#24292f")
            self.version_color = QColor("#57606a")
            self.progress_track = QColor("#eaeef2")
        else:
            self.bg_start = QColor("#1e222b")  # One Dark background
            self.bg_end = QColor("#12151a")
            self.accent_color = QColor("#00e5ff")  # Neon cyan
            self.border_end = QColor("#282c34")
            self.title_color = QColor("#ffffff")
            self.version_color = QColor("#8c92ac")
            self.progress_track = QColor("#282c34")

    def showMessage(self, message: str, alignment_or_progress=None, color=None):
        """
        Custom showMessage that accepts progressive text and progress value.
        Can be called with:
            showMessage(message)
            showMessage(message, progress_int)
            showMessage(message, alignment, color)
        """
        self._message = message
        if isinstance(alignment_or_progress, (int, float)):
            self._progress = int(alignment_or_progress)
        self.repaint()

    def setProgress(self, progress: int):
        """Explicitly set progress percentage (0-100)"""
        self._progress = max(0, min(int(progress), 100))
        self.repaint()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # 1. Paint modern drop shadow using translucent concentric rectangles
        for i in range(self.shadow_margin):
            # Quadratic opacity drop-off for a softer edge shadow
            opacity = int(25 * (1.0 - (i / self.shadow_margin) ** 2))
            if opacity > 0:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(0, 0, 0, opacity))
                painter.drawRoundedRect(
                    self.rect().adjusted(i, i, -i, -i),
                    16, 16
                )
        
        # 2. Main card body rect
        body_rect = self.rect().adjusted(
            self.shadow_margin, self.shadow_margin,
            -self.shadow_margin, -self.shadow_margin
        )
        
        # Draw background gradient
        bg_gradient = QLinearGradient(body_rect.topLeft().toPointF(), body_rect.bottomRight().toPointF())
        bg_gradient.setColorAt(0.0, self.bg_start)
        bg_gradient.setColorAt(1.0, self.bg_end)
        painter.setBrush(bg_gradient)
        
        # Draw premium themed border gradient
        border_gradient = QLinearGradient(body_rect.topLeft().toPointF(), body_rect.bottomRight().toPointF())
        border_gradient.setColorAt(0.0, self.accent_color)
        border_gradient.setColorAt(0.4, self.border_end)
        border_gradient.setColorAt(1.0, self.bg_end)
        
        painter.setPen(QPen(border_gradient, 1.5))
        painter.drawRoundedRect(body_rect, 14, 14)
        
        # 3. Draw App Logo
        if not self.logo_pixmap.isNull():
            logo_x = body_rect.x() + (body_rect.width() - self.logo_pixmap.width()) // 2
            logo_y = body_rect.y() + 40
            painter.drawPixmap(logo_x, logo_y, self.logo_pixmap)
            
        # 4. Draw Title "PgMan"
        title_font = QFont("Segoe UI", 26)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(self.title_color)
        title_rect = QRect(body_rect.x(), body_rect.y() + 140, body_rect.width(), 40)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, "PgMan")
        
        # 5. Draw Version
        version_font = QFont("Segoe UI", 9)
        version_font.setBold(True)
        painter.setFont(version_font)
        painter.setPen(self.version_color)
        version_rect = QRect(body_rect.x(), title_rect.bottom() - 2, body_rect.width(), 20)
        painter.drawText(version_rect, Qt.AlignmentFlag.AlignCenter, f"v.{version_name} ({version_release})")
        
        # 5.1 Draw "by TENz"
        by_tenz_font = QFont("Segoe UI", 9)
        by_tenz_font.setItalic(True)
        painter.setFont(by_tenz_font)
        painter.setPen(self.version_color)
        by_tenz_rect = QRect(body_rect.x(), version_rect.bottom() - 2, body_rect.width(), 20)
        painter.drawText(by_tenz_rect, Qt.AlignmentFlag.AlignCenter, "by TENz")
        
        # 6. Progress bar layout configuration
        bar_height = 4
        bar_margin = 48
        bar_y = body_rect.bottom() - 32
        bar_width = body_rect.width() - (bar_margin * 2)
        bar_x = body_rect.x() + bar_margin
        
        # Draw progress bar track
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.progress_track)
        painter.drawRoundedRect(bar_x, bar_y, bar_width, bar_height, bar_height // 2, bar_height // 2)
        
        # Draw filled progress and accent glow
        if self._progress > 0:
            fill_width = int(bar_width * (min(self._progress, 100) / 100.0))
            if fill_width > 0:
                # Border/fill glow
                glow_color = QColor(self.accent_color.red(), self.accent_color.green(), self.accent_color.blue(), 40)
                painter.setBrush(glow_color)
                painter.drawRoundedRect(
                    bar_x - 1, bar_y - 1,
                    fill_width + 2, bar_height + 2,
                    (bar_height + 2) // 2, (bar_height + 2) // 2
                )
                
                # Solid progress line
                painter.setBrush(self.accent_color)
                painter.drawRoundedRect(
                    bar_x, bar_y,
                    fill_width, bar_height,
                    bar_height // 2, bar_height // 2
                )
                
        # 7. Draw loading text neatly above the progress line
        msg_font = QFont("Segoe UI", 9)
        painter.setFont(msg_font)
        painter.setPen(self.accent_color)
        msg_rect = QRect(body_rect.x(), bar_y - 25, body_rect.width(), 20)
        painter.drawText(msg_rect, Qt.AlignmentFlag.AlignCenter, self._message)
