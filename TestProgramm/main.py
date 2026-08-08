import os
import sys
import threading
import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QMessageBox, QWidget, QVBoxLayout, QDialog
from PyQt5.QtCore import Qt, QEvent, QMetaObject, Q_ARG

# НАШИ ЧИСТЫЕ ИМПОРТЫ МОДУЛЕЙ
from utils.styles import get_application_style
from utils.engine import execute_command_stream_util
from widgets.autocomplete import FreeIPAAutocompleteEntry, AutocompleteEntry

# Импорты твоих готовых вкладок
from tabs.tab_yandex import YandexTab
from tabs.tab_messages import MessagesTab
from tabs.tab_scripts import ScriptsTab
from tabs.tab_commands import CommandsTab
from tabs.tab_packages import PackagesTab
from tabs.tab_settings import SettingsTab

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class AnsibleGuiApp(QMainWindow):
    def __init__(self, user, password):
        super().__init__()

        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        self.sudo_user = user
        self.sudo_password = password

        # Пул для отслеживания активных фоновых процессов Ansible
        self.active_processes = []

        # ЖЕСТКИЙ ФИКС ДЛЯ ОКРУЖЕНИЯ FLY ASTRA LINUX (возвращаем кнопку развертывания)
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowTitleHint |
            Qt.WindowSystemMenuHint |
            Qt.WindowMinimizeButtonHint |
            Qt.WindowMaximizeButtonHint |
            Qt.WindowCloseButtonHint
        )

        self.setWindowTitle("Панель управления Ansible — Рабочая область")
        self.setMinimumSize(850, 700)
        self.resize(850, 700)

        # Применяем восстановленные стили приложения
        self.setStyleSheet(get_application_style())

        # Инициализация вкладок
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabWidget::pane { background-color: white; border: 1px solid #CCCCCC; border-radius: 4px; }")
        self.setCentralWidget(self.tabs)

        # Инициализация твоих готовых модульных вкладок
        self.tab_packages = PackagesTab(self)
        self.tab_scripts = ScriptsTab(self)
        self.tab_commands = CommandsTab(self)
        self.tab_yandex = YandexTab(self)
        self.tab_messages = MessagesTab(self)
        self.tab_settings = SettingsTab(self)

        self.tabs.addTab(self.tab_packages, "Установка ПО")
        self.tabs.addTab(self.tab_scripts, "Запуск скриптов")
        self.tabs.addTab(self.tab_commands, "Выполнение команд")
        self.tabs.addTab(self.tab_yandex, "Яндекс")
        self.tabs.addTab(self.tab_messages, "Сообщения")
        self.tabs.addTab(self.tab_settings, "Настройки")

        # Принудительно заставляем автокомплиты обновить подсказки при старте
        self.refresh_all_tab_hosts()

        # Намертво синхронизируем списки подсказок при смене вкладок
        self.tabs.currentChanged.connect(self.close_all_popups_on_tab_change)

    def refresh_all_tab_hosts(self):
        """Обновление баз данных хостов внутри всех полей ввода"""
        if hasattr(self.tab_packages, 'ip_entry'):
            self.tab_packages.ip_entry.refresh_hosts()
        if hasattr(self.tab_scripts, 'script_ip_entry'):
            self.tab_scripts.script_ip_entry.refresh_hosts()
        if hasattr(self.tab_commands, 'command_ip_entry'):
            self.tab_commands.command_ip_entry.refresh_hosts()

    def _execute_command_stream(self, cmd, terminal_box, action_button, status_label, env=None):
        """Перенаправляем вызов в общий вынесенный утилитный движок (в фоне)."""
        threading.Thread(
            target=execute_command_stream_util,
            args=(self, cmd, terminal_box, action_button, status_label, env),
            daemon=True
        ).start()

    def _safe_finalize_ui(self, op_type, nodes, terminal, button):
        """Метод гарантированно выполняется в главном GUI-потоке по вызову из движка"""
        try:
            full_text = terminal.toPlainText()
            self.save_to_log_file(op_type, nodes, full_text)
        except Exception as e:
            print(f"[СБОЙ ФИНАЛИЗАЦИИ]: {e}")
        finally:
            if button:
                button.setEnabled(True)

    def save_to_log_file(self, operation_type, target_nodes, content):
        """Автоматическая запись логов в файл истории"""
        try:
            log_dir = os.path.join(BASE_DIR, "logs")
            log_path = os.path.join(log_dir, "history.log")
            os.makedirs(log_dir, exist_ok=True)

            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n[{timestamp}] АДМИН: {self.sudo_user} | ТИП: {operation_type} | ХОСТЫ: {target_nodes}\n")
                f.write("-" * 60 + "\n" + content.strip() + "\n" + "=" * 60 + "\n")
        except Exception as e:
            print(f"[СБОЙ ЗАПИСИ ЛОГА]: {e}")

    # === ГЛОБАЛЬНЫЙ КЛИК-ФИЛЬТР (Прячет подсказки, когда кликают мимо полей) ===
    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            self.close_all_active_popups()
        return super().eventFilter(obj, event)

    def close_all_active_popups(self):
        """Поиск всех кастомных виджетов ввода во всем окне для скрытия их списков"""
        for widget in self.findChildren(QWidget):
            if hasattr(widget, 'hide_popup'):
                try:
                    widget.hide_popup()
                except Exception:
                    pass

    def close_all_popups_on_tab_change(self, index):
        self.close_all_active_popups()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.close_all_active_popups()

    def closeEvent(self, event):
        """Уничтожение фоновых процессов при закрытии приложения крестиком"""
        if hasattr(self, 'active_processes') and self.active_processes:
            for process in self.active_processes:
                try:
                    process.terminate()
                    process.wait(timeout=1)
                except Exception:
                    try:
                        process.kill()
                    except Exception:
                        pass
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    from widgets.login_dialog import LoginDialog
    login_window = LoginDialog()

    # ПРИМЕНЯЕМ КОРПОРАТИВНЫЙ СТИЛЬ К ОКНУ АВТОРИЗАЦИИ:
    login_window.setStyleSheet(get_application_style())

    if login_window.exec_() == QDialog.Accepted:
        username = login_window.get_username()
        password = login_window.get_password()

        main_win = AnsibleGuiApp(username, password)

        # Регистрируем фильтр событий в приложении
        app.installEventFilter(main_win)

        main_win.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0)
