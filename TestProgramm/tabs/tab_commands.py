import os
import json
import threading
import subprocess
# Пишите это в самом верху файлов вкладок вместо конструкции "import __main__ / from main import ..."
from widgets.autocomplete import FreeIPAAutocompleteEntry
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QGridLayout,
    QLabel, QLineEdit, QCheckBox, QPushButton,
    QHBoxLayout, QTextEdit, QMessageBox
)
from PyQt5.QtCore import Qt, QMetaObject, Q_ARG, pyqtSignal

class CommandsTab(QWidget):
    # Безопасный сигнал для логирования из фоновых потоков в основной GUI
    log_signal = pyqtSignal(str)

    def __init__(self, parent_window, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main_win = parent_window  # Сохраняем ссылку на главное окно
        self.setup_ui()
        self.log_signal.connect(self.append_log_safe)

    def setup_ui(self):
        # ГЛАВНЫЙ СЛОЙ ВКЛАДКИ
        layout_tab3 = QVBoxLayout(self)
        layout_tab3.setContentsMargins(10, 10, 10, 10)

        frame_cmd_inputs = QGroupBox(" Параметры выполнения команды ")
        grid_cmd = QGridLayout(frame_cmd_inputs)
        grid_cmd.setSpacing(10)

        grid_cmd.addWidget(QLabel("Введите консольную команду:"), 0, 0)
        self.command_entry = QLineEdit()
        self.command_entry.setPlaceholderText("Например: uptime или systemctl status ssh")
        self.command_entry.setStyleSheet("""
            QLineEdit { border: 1px solid #CCCCCC; border-radius: 4px; padding: 6px 8px; font-size: 13px; background-color: white; }
            QLineEdit:focus { border: 1px solid #8e44ad; }
        """)
        grid_cmd.addWidget(self.command_entry, 0, 1)

        grid_cmd.addWidget(QLabel("Целевые ПК (IP через запятую):"), 1, 0)

        self.command_ip_entry = FreeIPAAutocompleteEntry()

        grid_cmd.addWidget(self.command_ip_entry, 1, 1)

        layout_tab3.addWidget(frame_cmd_inputs)

        # Контейнер для кнопок (Вертикальный пирог)
        layout_buttons3 = QVBoxLayout()

        # Строка 1: Основные кнопки
        row1_layout = QHBoxLayout()

        self.btn_run_cmd = QPushButton("Выполнить команду")
        self.btn_run_cmd.setCursor(Qt.PointingHandCursor)
        self.btn_run_cmd.setStyleSheet("""
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
            QPushButton:disabled {
                background-color: #BDC3C7;
                color: #7F8C8D;
            }
        """)
        self.btn_run_cmd.clicked.connect(self.start_custom_command_process)

        self.clear_cmd_log_button = QPushButton("Очистить терминал")
        self.clear_cmd_log_button.setCursor(Qt.PointingHandCursor)
        self.clear_cmd_log_button.setStyleSheet("""
            QPushButton { background-color: #f0f3f4; color: #34495e; border: 1px solid #bdc3c7; }
            QPushButton:hover { background-color: #eaeded; border-color: #95a5a6; }
            QPushButton:pressed { background-color: #d5dbdb; }
        """)
        self.clear_cmd_log_button.clicked.connect(lambda: self.command_terminal_box.clear())

        self.command_status_label = QLabel(f"Авторизован: {self.main_win.sudo_user}")
        self.command_status_label.setStyleSheet("color: #2E7D32; font-style: italic;")

        row1_layout.addWidget(self.btn_run_cmd)
        row1_layout.addWidget(self.clear_cmd_log_button)
        row1_layout.addStretch()
        row1_layout.addWidget(self.command_status_label)
        layout_buttons3.addLayout(row1_layout)

        # Строка 2: Новая строка для кнопки SSH-ключей
        row2_layout = QHBoxLayout()

        self.btn_deploy_key = QPushButton("Разослать мой SSH-ключ на указанные ПК")
        self.btn_deploy_key.setCursor(Qt.PointingHandCursor)
        self.btn_deploy_key.setStyleSheet("""
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
        self.btn_deploy_key.clicked.connect(self.start_ssh_deploy_process)

        row2_layout.addWidget(self.btn_deploy_key)
        row2_layout.addStretch()
        layout_buttons3.addLayout(row2_layout)

        # Добавляем весь двухэтажный контейнер кнопок в главный слой вкладки
        layout_tab3.addLayout(layout_buttons3)

        # Текстовое окно терминала в самом низу
        self.command_terminal_box = QTextEdit()
        self.command_terminal_box.setReadOnly(True)
        self.command_terminal_box.setStyleSheet("""
            QTextEdit { background-color: #1E1E1E; color: #00FF00; font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; border: 1px solid #CCCCCC; }
        """)
        layout_tab3.addWidget(self.command_terminal_box)

    def append_log_safe(self, text):
        self.command_terminal_box.append(text)

    def start_custom_command_process(self):
        custom_cmd = self.command_entry.text().strip()
        ip_target = self.command_ip_entry.text().strip()

        if custom_cmd.lower().startswith("sudo "):
            custom_cmd = custom_cmd[5:].strip()
            self.command_entry.setText(custom_cmd)

        if not custom_cmd or not ip_target:
            QMessageBox.warning(self, "Внимание", "Введите консольную команду и укажите целевые IP!")
            return

        self.btn_run_cmd.setEnabled(False)
        self.command_status_label.setText("Статус: Команда выполняется...")
        self.command_status_label.setStyleSheet("color: blue;")
        self.command_terminal_box.clear()

        threading.Thread(target=self.run_ansible_custom_command_thread, args=(custom_cmd, ip_target), daemon=True).start()

    def run_ansible_custom_command_thread(self, custom_cmd, ip_target):
        try:
            # Читаем BASE_DIR через главное окно, защищаясь от циклического импорта
            base_dir_path = self.main_win.BASE_DIR

            # Складываем файлы инвентаря строго в выделенную подпапку hosts
            hosts_dir = os.path.join(base_dir_path, "hosts")
            os.makedirs(hosts_dir, exist_ok=True)
            hosts_path = os.path.join(hosts_dir, "hosts_commands")

            # === СИНХРОНИЗАЦИЯ: Читаем состояние галочки проверки SSH-ключей ===
            ignore_keys = self.main_win.tab_settings.chk_key_checking.isChecked()

            # Железное переопределение на уровне процесса для фоновых модулей Ansible
            if ignore_keys:
                os.environ["ANSIBLE_HOST_KEY_CHECKING"] = "False"
            else:
                os.environ["ANSIBLE_HOST_KEY_CHECKING"] = "True"

            ip_list = [ip.strip() for ip in ip_target.split(",") if ip.strip()]
            with open(hosts_path, "w", encoding="utf-8") as f:
                f.write("[cmd_targets]\n")
                for ip in ip_list:
                    if ip.lower() in ["localhost", "127.0.0.1"] or ip.startswith("127."):
                        f.write(f"{ip} ansible_connection=local ansible_python_interpreter=/usr/bin/python3\n")
                    else:
                        # Динамически управляем аргументами SSH-подключения на основе GUI
                        if ignore_keys:
                            f.write(f"{ip} ansible_ssh_common_args='-o StrictHostKeyChecking=no' ansible_python_interpreter=/usr/bin/python3\n")
                        else:
                            f.write(f"{ip} ansible_ssh_common_args='-o StrictHostKeyChecking=yes' ansible_python_interpreter=/usr/bin/python3\n")

            # Безопасное сохранение строки команды во временный файл JSON
            playbooks_dir = os.path.join(base_dir_path, "playbooks")
            os.makedirs(playbooks_dir, exist_ok=True)
            vars_file_path = os.path.join(playbooks_dir, "command_vars.json")

            vars_dict = {
                "ansible_become_password": self.main_win.sudo_password,
                "target_custom_command": custom_cmd
            }

            if not self.main_win.tab_settings.chk_use_ssh_key.isChecked():
                vars_dict["ansible_password"] = self.main_win.sudo_password

            with open(vars_file_path, "w", encoding="utf-8") as json_f:
                json.dump(vars_dict, json_f, ensure_ascii=False, indent=4)

            # Вызываем наш обновленный структурированный плейбук
            playbook_path = os.path.join(playbooks_dir, "commands_playbook.yml")
            cmd = ["ansible-playbook", "-i", hosts_path, playbook_path, "--extra-vars", f"@{vars_file_path}"]

            # === СИНХРОНИЗАЦИЯ: Читаем параметры сетевых таймаутов из вкладки настроек ===
            timeout_index = self.main_win.tab_settings.timeout_combo.currentIndex()
            timeout_val = "30" if timeout_index == 1 else ("60" if timeout_index == 2 else "10")
            cmd.extend(["-T", timeout_val])

            # === СИНХРОНИЗАЦИЯ: Читаем выбранный уровень детализации дебага задач ===
            verbosity_index = self.main_win.tab_settings.verbosity_combo.currentIndex()
            if verbosity_index == 1:
                cmd.append("-v")
            elif verbosity_index == 2:
                cmd.append("-vvvv")

            self.log_signal.emit(f"[АНСИБЛ КОМАНДЫ]: Выполнение консольной команды на удаленных хостах...\nКоманда: {custom_cmd}\n" + "="*60)

            # Отправляем в сквозной потоковый движок чтения логов главного окна
            self.main_win._execute_command_stream(cmd, self.command_terminal_box, self.btn_run_cmd, self.command_status_label)

        except Exception as e:
            QMetaObject.invokeMethod(self.command_terminal_box, "append", Qt.QueuedConnection, Q_ARG(str, f"[ОШИБКА КОМАНДЫ]: {e}"))
            QMetaObject.invokeMethod(self.btn_run_cmd, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, True))

    def start_ssh_deploy_process(self):
        """Валидация публичного ключа Ed25519 перед запуском потока рассылки"""
        ip_target = self.command_ip_entry.text().strip()
        if not ip_target:
            QMessageBox.warning(self, "Внимание", "Укажите целевые хосты в поле ПК для копирования ключа!")
            return

        # ИСПРАВЛЕНО: Теперь программа ищет современный открытый ключ id_ed25519.pub
        pub_key_path = os.path.expanduser("~/.ssh/id_ed25519.pub")
        if not os.path.exists(pub_key_path):
            QMessageBox.critical(
                self, "Ключ не найден",
                "У вас в системе не найден SSH-ключ Ed25519!\n"
                "Сначала выполните в обычном терминале команду:\n"
                "ssh-keygen -t ed25519"
            )
            return

        try:
            with open(pub_key_path, "r", encoding="utf-8") as f:
                public_key_content = f.read().strip()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось прочитать файл ключа: {e}")
            return

        self.btn_deploy_key.setEnabled(False)
        self.command_status_label.setText("Статус: Рассылка SSH-ключей...")
        self.command_status_label.setStyleSheet("color: purple;")
        self.command_terminal_box.clear()

        threading.Thread(target=self.run_ansible_ssh_deploy, args=(ip_target, public_key_content), daemon=True).start()

    def run_ansible_ssh_deploy(self, ip_target, key_content):
        """Профессиональный движок рассылки ключей через expect по стандартам ИБ организаций"""
        try:
            QMetaObject.invokeMethod(self.command_terminal_box, "append", Qt.QueuedConnection, Q_ARG(str, "[СИСТЕМА]: Запуск безопасной рассылки ключей Ed25519 через expect...\n"))

            password = self.main_win.sudo_password
            username = self.main_win.sudo_user
            ip_list = [ip.strip() for ip in ip_target.split(",") if ip.strip()]
            pub_key_path = os.path.expanduser("~/.ssh/id_ed25519.pub")

            # ЧИТАЕМ СЕТЕВОЙ ТАЙМАУТ ИЗ НАШЕЙ ЕДИНОЙ ВКЛАДКИ НАСТРОЕК:
            timeout_index = self.main_win.tab_settings.timeout_combo.currentIndex()
            custom_timeout = 30 if timeout_index == 1 else (60 if timeout_index == 2 else 10)

            # === СИНХРОНИЗАЦИЯ: Читаем состояние галочки проверки SSH-ключей ===
            ignore_keys = self.main_win.tab_settings.chk_key_checking.isChecked()
            strict_host_checking_value = "no" if ignore_keys else "yes"

            for ip in ip_list:
                log_start = f"⏳ Отправка ключа на {ip}..."
                QMetaObject.invokeMethod(self.command_terminal_box, "append", Qt.QueuedConnection, Q_ARG(str, log_start))

                # Скриптexpect теперь полностью синхронизирован по таймаутам и ИБ-проверкам
                expect_script = f"""
                set timeout {custom_timeout}
                set password "{password}"
                spawn ssh-copy-id -i "{pub_key_path}" -o "StrictHostKeyChecking={strict_host_checking_value}" {username}@{ip}
                expect {{
                    "Are you sure you want to continue connecting" {{
                        send -- "yes\r"
                        exp_continue
                    }}
                    "*assword:" {{
                        send -- "$password\r"
                        exp_continue
                    }}
                    "Already authorized" {{
                        exit 0
                    }}
                    eof {{
                        catch wait result
                        exit [lindex $result 3]
                    }}
                    timeout {{
                        exit 1
                    }}
                }}
                """

                # Запускаем expect в интерактивном режиме "-", ожидая поток данных из памяти
                process = subprocess.Popen(
                    ["expect", "-"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )

                # Передаем весь готовый скрипт из оперативной памяти прямо в процесс expect с динамическим таймаутом
                stdout, _ = process.communicate(input=expect_script, timeout=custom_timeout + 5)

                # Безопасно выводим лог системы на экран, полностью затирая реальный пароль
                stdout_masked = stdout.replace(password, "******").strip()
                QMetaObject.invokeMethod(self.command_terminal_box, "append", Qt.QueuedConnection, Q_ARG(str, f"[ЛОГ СИСТЕМЫ]:\n{stdout_masked}"))

                stdout_clean = stdout.lower()

                # СИНХРОНИЗАЦИЯ ЛОГОВ: Проверяем маркеры успешного копирования или пропуска ключа в Astra Linux
                if (
                    "number of key(s) added" in stdout_clean or
                    "added" in stdout_clean or
                    "already authorized" in stdout_clean or
                    "already exist" in stdout_clean or    # Обработка случая, когда ключ уже записан
                    "skipped" in stdout_clean             # Обработка пропуска дубликатов ключей
                ):
                    log_res = f"🟢 УСПЕХ: Ключ Ed25519 гарантированно записан (или уже существовал) в authorized_keys на {ip}\n"
                else:
                    log_res = f"🔴 ОШИБКА: Авторизация на {ip} сорвалась системно. Проверьте сеть или пароль.\n"

                QMetaObject.invokeMethod(self.command_terminal_box, "append", Qt.QueuedConnection, Q_ARG(str, log_res))

            QMetaObject.invokeMethod(self.command_terminal_box, "append", Qt.QueuedConnection, Q_ARG(str, "--- РАССЫЛКА КЛЮЧЕЙ ЗАВЕРШЕНА ---"))
            QMetaObject.invokeMethod(self.command_status_label, "setText", Qt.QueuedConnection, Q_ARG(str, f"Авторизован: {username} | Ключи готовы"))
            QMetaObject.invokeMethod(self.command_status_label, "setStyleSheet", Qt.QueuedConnection, Q_ARG(str, "color: green;"))

        except subprocess.TimeoutExpired:
            QMetaObject.invokeMethod(self.command_terminal_box, "append", Qt.QueuedConnection, Q_ARG(str, f"🔴 ОШИБКА: Превышено время ожидания ответа от удаленного узла (более {custom_timeout} сек)."))
        except Exception as e:
            QMetaObject.invokeMethod(self.command_terminal_box, "append", Qt.QueuedConnection, Q_ARG(str, f"[КРИТИЧЕСКАЯ ОШИБКА ДВИЖКА]: {e}"))
        finally:
            # Возвращаем активность вашей кнопке self.btn_deploy_key при любом исходе
            if hasattr(self, 'btn_deploy_key') and self.btn_deploy_key:
                QMetaObject.invokeMethod(self.btn_deploy_key, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, True))
