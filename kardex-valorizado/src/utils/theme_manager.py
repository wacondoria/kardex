from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QFile, QTextStream
from pathlib import Path

class ThemeManager:
    @staticmethod
    def apply_theme(app, theme_name="light"):
        if theme_name == "dark":
            style_path = Path(__file__).parent.parent / "resources" / "styles" / "dark.qss"
            if style_path.exists():
                file = QFile(str(style_path))
                file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text)
                stream = QTextStream(file)
                app.setStyleSheet(stream.readAll())
            else:
                print(f"Error: No se encontró el tema oscuro en {style_path}")
        else:
            app.setStyleSheet("") # Reset to default (light/fusion)

    @staticmethod
    def toggle_theme(app, current_theme):
        new_theme = "dark" if current_theme == "light" else "light"
        ThemeManager.apply_theme(app, new_theme)
        return new_theme
