import os
import json
import threading
import subprocess
# Пишите это в самом верху файлов вкладок вместо конструкции "import __main__ / from main import ..."
from widgets.autocomplete import FreeIPAAutocompleteEntry

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QGridLayout,
    QLabel, QLineEdit, QPushButton, QHBoxLayout,
    QTextEdit, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt, QMetaObject, Q_ARG, pyqtSignal

class ScriptsTab(QWidget):
    # Безопасный сигнал для вывода логов из фонового потока в GUI-поток
    log_signal = pyqtSignal(str)

    def __init__(self, parent_window, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main_win = parent_window  # Ссылка на главное окно с паролями и движком
        self.setup_ui()
        self.log_signal.connect(self.append_log_safe)

    def setup_ui(self):
        layout_tab2 = QVBoxLayout(self)
        layout_tab2.setContentsMargins(10, 10, 10, 10)

        frame_script_inputs = QGroupBox(" Параметры сценария и пакета ")
        grid_script = QGridLayout(frame_script_inputs)
        grid_script.setSpacing(10)

        # ПОЛЕ 1: Выбор файла скрипта
        grid_script.addWidget(QLabel("Выберите файл скрипта:"), 0, 0)
        self.script_path_entry = QLineEdit()
        self.script_path_entry.setPlaceholderText("Выберите скрипт на диске (.sh/.py) или укажите путь...")
        self.script_path_entry.setStyleSheet("""
            QLineEdit { border: 1px solid #CCCCCC; border-radius: 4px; padding: 6px 8px; font-size: 13px; background-color: white; }
            QLineEdit:focus { border: 1px solid #4CAF50; }
        """)

        btn_browse_script = QPushButton("Обзор...")
        btn_browse_script.setCursor(Qt.PointingHandCursor)
        btn_browse_script.setFixedSize(110, 29)
        btn_browse_script.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; font-size: 13px; font-weight: bold; border-radius: 4px; border: none; margin: 0px !important; padding: 0px !important; }
            QPushButton:hover { background-color: #45a049; }
        """)
        btn_browse_script.clicked.connect(self.browse_script_file)

        layout_browse_script = QHBoxLayout()
        layout_browse_script.setContentsMargins(0, 0, 0, 0)
        layout_browse_script.setSpacing(10)
        layout_browse_script.addWidget(self.script_path_entry, alignment=Qt.AlignVCenter)
        layout_browse_script.addWidget(btn_browse_script, alignment=Qt.AlignVCenter)
        grid_script.addLayout(layout_browse_script, 0, 1)

        # ПОЛЕ 2: Выбор файла DEB-пакета (Новое поле!)
        grid_script.addWidget(QLabel("Связанный DEB-пакет (Опционально):"), 1, 0)
        self.deb_path_entry = QLineEdit()
        self.deb_path_entry.setPlaceholderText("Оставьте пустым, если скрипту не нужен файл пакета...")
        self.deb_path_entry.setStyleSheet("""
            QLineEdit { border: 1px solid #CCCCCC; border-radius: 4px; padding: 6px 8px; font-size: 13px; background-color: white; }
            QLineEdit:focus { border: 1px solid #27ae60; }
        """)

        btn_browse_deb = QPushButton("Обзор...")
        btn_browse_deb.setCursor(Qt.PointingHandCursor)
        btn_browse_deb.setFixedSize(110, 29)
        btn_browse_deb.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; font-size: 13px; font-weight: bold; border-radius: 4px; border: none; margin: 0px !important; padding: 0px !important; }
            QPushButton:hover { background-color: #219653; }
        """)
        btn_browse_deb.clicked.connect(self.browse_deb_file)

        layout_browse_deb = QHBoxLayout()
        layout_browse_deb.setContentsMargins(0, 0, 0, 0)
        layout_browse_deb.setSpacing(10)
        layout_browse_deb.addWidget(self.deb_path_entry, alignment=Qt.AlignVCenter)
        layout_browse_deb.addWidget(btn_browse_deb, alignment=Qt.AlignVCenter)
        grid_script.addLayout(layout_browse_deb, 1, 1)

        # ПОЛЕ 3: Целевые компьютеры
        grid_script.addWidget(QLabel("Целевые ПК (IP / Хосты FreeIPA через запятую):"), 2, 0)

        import __main__
        if hasattr(__main__, 'FreeIPAAutocompleteEntry'):
            self.script_ip_entry = __main__.FreeIPAAutocompleteEntry()
        else:
            from main import FreeIPAAutocompleteEntry
            self.script_ip_entry = FreeIPAAutocompleteEntry()

        self.script_ip_entry.setPlaceholderText("Вводите имена или IP через запятую...")
        grid_script.addWidget(self.script_ip_entry, 2, 1)

        layout_tab2.addWidget(frame_script_inputs)

        # --- Кнопки управления и статуса ---
        layout_buttons2 = QHBoxLayout()

        self.btn_run_script = QPushButton("Запустить скрипт")
        self.btn_run_script.setCursor(Qt.PointingHandCursor)
        self.btn_run_script.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 13px;
                font-weight: bold;
                border-radius: 4px;
                padding: 8px 15px;
                border: none;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """)
        self.btn_run_script.clicked.connect(self.start_script_process)

        self.clear_script_log_button = QPushButton("Очистить терминал")
        self.clear_script_log_button.setCursor(Qt.PointingHandCursor)
        self.clear_script_log_button.setStyleSheet("""
            QPushButton { background-color: #f0f3f4; color: #34495e; border: 1px solid #bdc3c7; }
            QPushButton:hover { background-color: #eaeded; border-color: #95a5a6; }
            QPushButton:pressed { background-color: #d5dbdb; }
        """)
        self.clear_script_log_button.clicked.connect(lambda: self.script_terminal_box.clear())

        self.script_status_label = QLabel(f"Авторизован: {self.main_win.sudo_user}")
        self.script_status_label.setStyleSheet("color: #2E7D32; font-style: italic;")

        layout_buttons2.addWidget(self.btn_run_script)
        layout_buttons2.addWidget(self.clear_script_log_button)
        layout_buttons2.addStretch()
        layout_buttons2.addWidget(self.script_status_label)
        layout_tab2.addLayout(layout_buttons2)

        # Зеленый терминал
        self.script_terminal_box = QTextEdit()
        self.script_terminal_box.setReadOnly(True)
        self.script_terminal_box.setStyleSheet("""
            QTextEdit { background-color: #1E1E1E; color: #00FF00; font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; border: 1px solid #CCCCCC; }
        """)
        layout_tab2.addWidget(self.script_terminal_box)

    def browse_script_file(self):
        """Выбор файла скрипта."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите скрипт для запуска", "",
            "Скрипты (*.sh *.py *.bash);;Все файлы (*.*)"
        )
        if file_path:
            self.script_path_entry.setText(str(file_path))

    def browse_deb_file(self):
        """Выбор локального DEB-пакета со стола или любой папки."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите DEB-пакет для отправки", "",
            "Пакеты Debian (*.deb);;Все файлы (*.*)"
        )
        if file_path:
            self.deb_path_entry.setText(str(file_path))

    def append_log_safe(self, text):
        self.script_terminal_box.append(text)

    def start_script_process(self):
        script_path = self.script_path_entry.text().strip()
        deb_path = self.deb_path_entry.text().strip()
        ip_target = self.script_ip_entry.text().strip()

        if not script_path or not ip_target:
            QMessageBox.warning(self, "Внимание", "Выберите файл скрипта и укажите целевые IP!")
            return

        if not os.path.exists(script_path):
            QMessageBox.critical(self, "Ошибка", f"Скрипт не найден:\n{script_path}")
            return

        self.btn_run_script.setEnabled(False)
        self.script_terminal_box.clear()
        self.script_status_label.setText(f"Авторизован: {self.main_win.sudo_user}")

        threading.Thread(
            target=self.run_ansible_scripts_thread,
            args=(script_path, deb_path, ip_target),
            daemon=True
        ).start()

    def run_ansible_scripts_thread(self, script_path, deb_path, ip_target):
        try:
            # Читаем BASE_DIR через главное окно.
            base_dir_path = self.main_win.BASE_DIR

            # Складываем файлы инвентаря строго в выделенную подпапку hosts
            hosts_dir = os.path.join(base_dir_path, "hosts")
            os.makedirs(hosts_dir, exist_ok=True)
            hosts_path = os.path.join(hosts_dir, "hosts_scripts")

            # === СИНХРОНИЗАЦИЯ: Читаем состояние галочки из вкладки настроек ===
            ignore_keys = self.main_win.tab_settings.chk_key_checking.isChecked()

            # Железное переопределение на уровне процесса для фоновых модулей Ansible
            if ignore_keys:
                os.environ["ANSIBLE_HOST_KEY_CHECKING"] = "False"
            else:
                os.environ["ANSIBLE_HOST_KEY_CHECKING"] = "True"

            ip_list = [ip.strip() for ip in ip_target.split(",") if ip.strip()]
            with open(hosts_path, "w", encoding="utf-8") as f:
                f.write("[script_targets]\n")
                for ip in ip_list:
                    if ip.lower() in ["localhost", "127.0.0.1"] or ip.startswith("127."):
                        f.write(f"{ip} ansible_connection=local\n")
                    else:
                        # Динамически управляем аргументами SSH-подключения на основе GUI
                        if ignore_keys:
                            f.write(f"{ip} ansible_ssh_common_args='-o StrictHostKeyChecking=no'\n")
                        else:
                            f.write(f"{ip} ansible_ssh_common_args='-o StrictHostKeyChecking=yes'\n")

            # Безопасное сохранение тяжелых путей во временный файл переменных JSON
            playbooks_dir = os.path.join(base_dir_path, "playbooks")
            os.makedirs(playbooks_dir, exist_ok=True)
            vars_file_path = os.path.join(playbooks_dir, "script_vars.json")

            # Сохраняем твои оригинальные ключи переменных для плейбука
            vars_dict = {
                "ansible_become_password": self.main_win.sudo_password,
                "custom_script_path": script_path,
                "custom_deb_path": deb_path  # Передаем точный путь к DEB-файлу, выбранному админом
            }

            # Читаем состояние одной общей галочки из вкладки НАСТРОЕК
            if not self.main_win.tab_settings.chk_use_ssh_key.isChecked():
                # Если в настройках ключ выключен — принудительно прокидываем пароль для sshpass
                vars_dict["ansible_password"] = self.main_win.sudo_password

            with open(vars_file_path, "w", encoding="utf-8") as json_f:
                json.dump(vars_dict, json_f, ensure_ascii=False, indent=4)

            # Вызываем твой оригинальный плейбук script_playbook.yml
            playbook_path = os.path.join(playbooks_dir, "script_playbook.yml")
            cmd = ["ansible-playbook", "-i", hosts_path, playbook_path, "--extra-vars", f"@{vars_file_path}"]

            # Читаем параметры сетевых таймаутов подключения из вкладки настроек
            timeout_index = self.main_win.tab_settings.timeout_combo.currentIndex()
            timeout_val = "30" if timeout_index == 1 else ("60" if timeout_index == 2 else "10")
            cmd.extend(["-T", timeout_val])

            # Читаем выбранный сисадмином уровень детализации дебага задач
            verbosity_index = self.main_win.tab_settings.verbosity_combo.currentIndex()
            if verbosity_index == 1:
                cmd.append("-v")
            elif verbosity_index == 2:
                cmd.append("-vvvv")

            self.log_signal.emit(f"[АНСИБЛ СКРИПТЫ]: Подготовка сценария автоматизации...\nСкрипт: {script_path}\nПакет: {deb_path if deb_path else 'Не указан'}\n" + "="*60)

            # Отправляем в сквозной потоковый движок чтения логов главного окна
            self.main_win._execute_command_stream(cmd, self.script_terminal_box, self.btn_run_script, self.script_status_label)

        except Exception as e:
            QMetaObject.invokeMethod(self.script_terminal_box, "append", Qt.QueuedConnection, Q_ARG(str, f"[ОШИБКА ДВИЖКА СКРИПТОВ]: {e}"))
            QMetaObject.invokeMethod(self.btn_run_script, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, True))
