import os
import json
import threading
import subprocess
from widgets.autocomplete import FreeIPAAutocompleteEntry, AutocompleteEntry
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QGridLayout, QLabel, QComboBox, QCheckBox, QHBoxLayout, QPushButton, QTextEdit, QMessageBox
from PyQt5.QtCore import Qt, QMetaObject, Q_ARG, pyqtSignal

class PackagesTab(QWidget):

    log_signal = pyqtSignal(str)

    def __init__(self, parent_window, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main_win = parent_window  # Ссылка на главное окно с паролями и сетевым движком
        self.setup_ui()
        self.log_signal.connect(self.append_log_safe)

    def setup_ui(self):
        layout_tab1 = QVBoxLayout(self)
        layout_tab1.setContentsMargins(10, 10, 10, 10)

        frame_inputs = QGroupBox(" Настройки конфигурации ")
        grid_config = QGridLayout(frame_inputs)
        grid_config.setSpacing(10)

        grid_config.addWidget(QLabel("Список пакетов (через запятую):"), 0, 0)
        from main import AutocompleteEntry
        self.package_entry = AutocompleteEntry()
        self.package_entry.setPlaceholderText("Вводите имена пакетов через запятую (например: nginx, git)...")
        grid_config.addWidget(self.package_entry, 0, 1)

        grid_config.addWidget(QLabel("Целевые хосты (IP / Доменные имена):"), 1, 0)
        from main import FreeIPAAutocompleteEntry
        self.ip_entry = FreeIPAAutocompleteEntry()
        grid_config.addWidget(self.ip_entry, 1, 1)

        grid_config.addWidget(QLabel("Одновременно настраивать ПК:"), 2, 0)
        self.forks_combobox = QComboBox()
        self.forks_combobox.addItems(["1 (Строго по очереди)", "5 (Стандарт)", "10 (Оптимально)", "20 (Быстро)", "50 (Максимум)"])
        grid_config.addWidget(self.forks_combobox, 2, 1)

        self.chk_delete = QCheckBox("Удалить указанные программы (Режим очистки)")
        self.chk_delete.setStyleSheet("QCheckBox { color: #D32F2F; font-weight: bold; }")
        self.chk_delete.toggled.connect(self.toggle_button_text)
        grid_config.addWidget(self.chk_delete, 4, 0, 1, 2)

        layout_tab1.addWidget(frame_inputs)

        layout_buttons = QHBoxLayout()
        self.start_button = QPushButton("Установить")
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 25px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """)

        self.start_button.clicked.connect(self.start_process)

        self.ping_button = QPushButton("Проверить связь")
        self.ping_button.setCursor(Qt.PointingHandCursor)
        self.ping_button.setStyleSheet("""
            QPushButton {
                background-color: #2980b9;
                color: white;
                font-size: 13px;
                padding: 8px 20px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2471a3;
            }
            QPushButton:pressed {
                background-color: #1f618d;
            }
        """)

        self.ping_button.clicked.connect(self.start_ping_process)

        self.clear_log_button = QPushButton("Очистить терминал")
        self.clear_log_button.setCursor(Qt.PointingHandCursor)
        self.clear_log_button.setStyleSheet("""
            QPushButton { background-color: #f0f3f4; color: #34495e; border: 1px solid #bdc3c7; }
            QPushButton:hover { background-color: #eaeded; border-color: #95a5a6; }
            QPushButton:pressed { background-color: #d5dbdb; }
        """)

        self.clear_log_button.clicked.connect(lambda: self.output_text.clear())

        self.status_label = QLabel(f"Авторизован: {self.main_win.sudo_user}")
        self.status_label.setStyleSheet("color: #2E7D32; font-style: italic;")

        layout_buttons.addWidget(self.start_button)
        layout_buttons.addWidget(self.ping_button)
        layout_buttons.addWidget(self.clear_log_button)
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.status_label)
        layout_tab1.addLayout(layout_buttons)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        layout_tab1.addWidget(self.output_text)

    def toggle_button_text(self, checked):
        if checked:
            self.start_button.setText("Удалить")
            self.start_button.setStyleSheet("""
                QPushButton { background-color: #D32F2F; color: white; font-weight: bold; padding: 8px 25px; border-radius: 4px; border: none; }
                QPushButton:hover { background-color: #B71C1C; }
                QPushButton:pressed { background-color: #9A1B1B; }
            """)
        else:
            self.start_button.setText("Установить")
            self.start_button.setStyleSheet("""
                QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px 25px; border-radius: 4px; border: none; }
                QPushButton:hover { background-color: #45a049; }
                QPushButton:pressed { background-color: #3e8e41; }
            """)

    def append_log_safe(self, text):
        """Потокобезопасный вывод строки лога в текстовое окно терминала."""
        self.output_text.append(text)

    def start_process(self):
        package = self.package_entry.text().strip()
        ip_target = self.ip_entry.text().strip()

        if not package or not ip_target:
            QMessageBox.warning(self, "Внимание", "Пожалуйста, заполните поля пакетов и IP!")
            return

        self.start_button.setEnabled(False)
        self.status_label.setText("Статус: Выполняется операция...")
        self.status_label.setStyleSheet("color: blue;")
        self.output_text.clear()

        threading.Thread(target=self.run_ansible_packages_thread, args=(package, ip_target), daemon=True).start()

    def start_ping_process(self):
        ip_target = self.ip_entry.text().strip()
        if not ip_target:
            QMessageBox.warning(self, "Внимание", "Введите IP-адреса для проверки связи!")
            return

        self.ping_button.setEnabled(False)
        self.status_label.setText("Статус: Проверка связи...")
        self.status_label.setStyleSheet("color: #2980b9;")
        self.output_text.clear()
        QMetaObject.invokeMethod(self.output_text, "append", Qt.QueuedConnection, Q_ARG(str, "--- ЗАПУСК ПРОВЕРКИ ДОСТУПНОСТИ УЗЛОВ (PING) ---\n"))

        threading.Thread(target=self.run_ping_thread, args=(ip_target,), daemon=True).start()

    def run_ping_thread(self, ip_target):
        try:
            ip_list = [ip.strip() for ip in ip_target.split(",") if ip.strip()]
            for ip in ip_list:
                cmd = ["ping", "-c", "1", "-W", "1", ip]
                process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                log_line = f"🟢 Компьютер {ip} — ДОСТУПЕН" if process.returncode == 0 else f"🔴 Компьютер {ip} — НЕ ДОСТУПЕН"
                QMetaObject.invokeMethod(self.output_text, "append", Qt.QueuedConnection, Q_ARG(str, log_line))

            QMetaObject.invokeMethod(self.output_text, "append", Qt.QueuedConnection, Q_ARG(str, "\n--- ПРОВЕРКА СВЯЗИ ЗАВЕРШЕНА ---"))
            QMetaObject.invokeMethod(self.status_label, "setText", Qt.QueuedConnection, Q_ARG(str, f"Авторизован: {self.main_win.sudo_user}"))
            QMetaObject.invokeMethod(self.status_label, "setStyleSheet", Qt.QueuedConnection, Q_ARG(str, "color: #2E7D32;"))
        except Exception as e:
            QMetaObject.invokeMethod(self.output_text, "append", Qt.QueuedConnection, Q_ARG(str, f"[ОШИБКА ДВИЖКА ПИНГА]: {e}"))
        finally:
            QMetaObject.invokeMethod(self.ping_button, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, True))

    def run_ansible_packages_thread(self, package, ip_target):
        try:
            # Читаем BASE_DIR через главное окно, чтобы избежать циклического импорта
            base_dir_path = self.main_win.BASE_DIR

            # Складываем файлы инвентаря строго в выделенную подпапку hosts
            hosts_dir = os.path.join(base_dir_path, "hosts")
            os.makedirs(hosts_dir, exist_ok=True)
            hosts_path = os.path.join(hosts_dir, "hosts_packages")

            # Читаем настройки параллельности из вашего комбобокса
            forks_mapping = {
                "1 (Строго по очереди)": "1",
                "5 (Стандарт)": "5",
                "10 (Оптимально)": "10",
                "20 (Быстро)": "20",
                "50 (Максимум)": "50"
            }
            forks_value = forks_mapping.get(self.forks_combobox.currentText(), "20")

            # === СИНХРОНИЗАЦИЯ: Читаем состояние галочки проверки SSH-ключей ===
            ignore_keys = self.main_win.tab_settings.chk_key_checking.isChecked()

            # Корневое переопределение на уровне процесса для фоновых модулей Ansible
            if ignore_keys:
                os.environ["ANSIBLE_HOST_KEY_CHECKING"] = "False"
            else:
                os.environ["ANSIBLE_HOST_KEY_CHECKING"] = "True"

            # Генерируем инвентарь package_targets для сетевой задачи
            ip_list = [ip.strip() for ip in ip_target.split(",") if ip.strip()]
            with open(hosts_path, "w", encoding="utf-8") as f:
                f.write("[package_targets]\n")
                for ip in ip_list:
                    # Безопасная проверка локального хоста
                    if ip.lower() in ["localhost", "127.0.0.1"] or ip.startswith("127."):
                        f.write(f"{ip} ansible_connection=local\n")
                    else:
                        # Динамически управляем аргументами SSH-подключения на основе GUI
                        if ignore_keys:
                            f.write(f"{ip} ansible_ssh_common_args='-o StrictHostKeyChecking=no'\n")
                        else:
                            f.write(f"{ip} ansible_ssh_common_args='-o StrictHostKeyChecking=yes'\n")

            # Разбираем строку пакетов через запятую в массив строк для модуля apt
            package_list = [pkg.strip() for pkg in package.split(",") if pkg.strip()]
            state_value = "absent" if self.chk_delete.isChecked() else "present"

            # Формируем понятное русское слово для рамок плейбука в зависимости от галочки удаления
            action_text = "УДАЛЕНИЯ" if state_value == "absent" else "УСТАНОВКИ"

            # Упаковываем все данные в файл переменных, защищаясь от ограничений длины аргументов
            vars_file_path = os.path.join(base_dir_path, "playbooks", "install_vars.json")
            vars_dict = {
                "target_packages": package_list,
                "package_state": state_value,
                "dynamic_serial": int(forks_value),
                "action_word": action_text  # Передаем динамический текст операции для рамок
            }

            # Безопасно прокидываем пароли sudo авторизации из вкладки настроек
            if not self.main_win.tab_settings.chk_use_ssh_key.isChecked():
                vars_dict["ansible_password"] = self.main_win.sudo_password
                vars_dict["ansible_become_password"] = self.main_win.sudo_password
            else:
                if self.main_win.sudo_password:
                    vars_dict["ansible_become_password"] = self.main_win.sudo_password

            with open(vars_file_path, "w", encoding="utf-8") as json_f:
                json.dump(vars_dict, json_f, ensure_ascii=False, indent=4)

            # Вызываем ваш единый плейбук packages_playbook.yml
            playbook_path = os.path.join(base_dir_path, "playbooks", "packages_playbook.yml")
            command = ["ansible-playbook", "-i", hosts_path, playbook_path, "--extra-vars", f"@{vars_file_path}"]

            # === СИНХРОНИЗАЦИЯ: Читаем параметры таймаутов из вкладки настроек ===
            timeout_index = self.main_win.tab_settings.timeout_combo.currentIndex()
            timeout_val = "30" if timeout_index == 1 else ("60" if timeout_index == 2 else "10")
            command.extend(["-T", timeout_val])

            # === СИНХРОНИЗАЦИЯ: Читаем выбранный уровень детализации дебага задач ===
            verbosity_index = self.main_win.tab_settings.verbosity_combo.currentIndex()
            if verbosity_index == 1:
                command.append("-v")
            elif verbosity_index == 2:
                command.append("-vvvv")

            self.log_signal.emit(f"[АНСИБЛ ПАКЕТЫ]: Запуск массовой настройки программного обеспечения...\nРежим: {action_text}\nПакеты: {package}\nГруппы обработки: по {forks_value} ПК\n" + "="*60)

            # Вызываем сквозной потоковый движок чтения логов из главного окна
            self.main_win._execute_command_stream(command, self.output_text, self.start_button, self.status_label)

        except Exception as e:
            QMetaObject.invokeMethod(self.output_text, "append", Qt.QueuedConnection, Q_ARG(str, f"[ОШИБКА ДВИЖКА ПАКЕТОВ]: {e}"))
            QMetaObject.invokeMethod(self.start_button, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, True))
