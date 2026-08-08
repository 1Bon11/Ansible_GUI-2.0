import os
import json
import threading
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QGridLayout,
    QLabel, QLineEdit, QPushButton, QHBoxLayout,
    QTextEdit, QMessageBox
)
from PyQt5.QtCore import Qt, QMetaObject, Q_ARG, pyqtSignal


class MessagesTab(QWidget):
    # Безопасный сигнал для вывода логов из фонового потока в GUI
    log_signal = pyqtSignal(str)

    def __init__(self, parent_window, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main_win = parent_window  # Ссылка на главное окно QMainWindow
        self.setup_ui()
        self.log_signal.connect(self.append_log_safe)

    def setup_ui(self):
        # Безопасный локальный импорт автокомплита для защиты от циклических зависимостей
        try:
            from widgets.autocomplete import FreeIPAAutocompleteEntry
        except ImportError:
            from main import FreeIPAAutocompleteEntry

        # Главный вертикальный слой всей вкладки с хорошими отступами
        layout_tab = QVBoxLayout(self)
        layout_tab.setContentsMargins(24, 24, 24, 24)
        layout_tab.setSpacing(20)

        frame_inputs = QGroupBox(" Параметры отправки уведомления ")
        grid_msg = QGridLayout(frame_inputs)
        grid_msg.setContentsMargins(20, 24, 20, 20)
        grid_msg.setSpacing(16)

        grid_msg.setColumnStretch(0, 0)
        grid_msg.setColumnStretch(1, 1)

        # ПОЛЕ 1: Тема / Заголовок окна
        grid_msg.addWidget(QLabel("Заголовок окна (Тема):"), 0, 0)
        self.msg_title_entry = QLineEdit()
        self.msg_title_entry.setPlaceholderText("Например: Внимание! Технические работы...")
        self.msg_title_entry.setFixedWidth(320)
        grid_msg.addWidget(self.msg_title_entry, 0, 1, Qt.AlignLeft)

        # ПОЛЕ 2: Текст сообщения (С жестким белым стилем, чтобы не наследовал черный цвет)
        grid_msg.addWidget(QLabel("Текст сообщения пользователю:"), 1, 0)
        self.msg_text_entry = QTextEdit()
        self.msg_text_entry.setPlaceholderText("Введите текст, который появится в центре экрана пользователя...")
        self.msg_text_entry.setFixedWidth(320)
        self.msg_text_entry.setMaximumHeight(80)
        self.msg_text_entry.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                color: #000000;
                border: 1px solid #BDC3C7;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 13px;
            }
            QTextEdit:focus {
                border: 1px solid #2980B9;
            }
        """)
        grid_msg.addWidget(self.msg_text_entry, 1, 1, Qt.AlignLeft)

        # ПОЛЕ 3: Таймер блокировки окна (Только цифры)
        grid_msg.addWidget(QLabel("Заблокировать окно на (сек):"), 2, 0)
        self.msg_timer_entry = QLineEdit()
        self.msg_timer_entry.setPlaceholderText("Например: 10 (0 — без блокировки)")
        self.msg_timer_entry.setText("0")
        self.msg_timer_entry.setFixedWidth(320)
        from PyQt5.QtGui import QIntValidator
        self.msg_timer_entry.setValidator(QIntValidator(0, 60, self))
        grid_msg.addWidget(self.msg_timer_entry, 2, 1, Qt.AlignLeft)

        # ПОЛЕ 4: Выбор целевых компьютеров
        grid_msg.addWidget(QLabel("Целевые ПК (IP / Хосты через запятую):"), 3, 0)
        self.msg_ip_entry = FreeIPAAutocompleteEntry()
        self.msg_ip_entry.setPlaceholderText("Вводите имена или IP через запятую...")
        self.msg_ip_entry.setFixedWidth(430)
        grid_msg.addWidget(self.msg_ip_entry, 3, 1, Qt.AlignLeft)

        layout_tab.addWidget(frame_inputs)

        # --- Кнопки управления и статуса ---
        layout_buttons = QHBoxLayout()
        layout_buttons.setContentsMargins(0, 0, 0, 0)
        layout_buttons.setSpacing(12)

        self.btn_send_msg = QPushButton("Отправить сообщение")
        self.btn_send_msg.setCursor(Qt.PointingHandCursor)
        self.btn_send_msg.clicked.connect(self.start_message_process)
        self.btn_send_msg.setStyleSheet("""
            QPushButton {
                background-color: #2E7D32;
                color: white;
                border-radius: 4px;
                font-weight: bold;
                height: 32px
                padding: 0px !important;
                margin: 0px !important;
            }
            QPushButton:hover {
                background-color: #1B5E20;
            }
            QPushButton:pressed {
                background-color: #123C14;
            }
            QPushButton:disabled {
                background-color: #BDC3C7;
                color: #7F8C8D;
            }
        """)


        self.clear_msg_log_button = QPushButton("Очистить терминал")
        self.clear_msg_log_button.setCursor(Qt.PointingHandCursor)
        self.clear_msg_log_button.setFixedWidth(180)
        self.clear_msg_log_button.setStyleSheet("""
            QPushButton { background-color: #f0f3f4; color: #34495e; border: 1px solid #bdc3c7; }
            QPushButton:hover { background-color: #eaeded; border-color: #95a5a6; }
            QPushButton:pressed { background-color: #d5dbdb; }
        """)
        self.clear_msg_log_button.clicked.connect(lambda: self.msg_terminal_box.clear())

        self.msg_status_label = QLabel(f"Авторизован: {self.main_win.sudo_user}")
        self.msg_status_label.setStyleSheet("color: #2E7D32; font-style: italic; font-weight: bold; font-size: 12px;")

        layout_buttons.addWidget(self.btn_send_msg)
        layout_buttons.addWidget(self.clear_msg_log_button)
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.msg_status_label)
        layout_tab.addLayout(layout_buttons)

        # Глубокий терминал логов
        self.msg_terminal_box = QTextEdit()
        self.msg_terminal_box.setReadOnly(True)
        layout_tab.addWidget(self.msg_terminal_box)

    def append_log_safe(self, text):
        self.msg_terminal_box.append(text)

    def start_message_process(self):
        title = self.msg_title_entry.text().strip()
        message = self.msg_text_entry.toPlainText().strip()
        ip_target = self.msg_ip_entry.text().strip()

        # 1. СНАЧАЛА ОБЯЗАТЕЛЬНО СОЗДАЕМ И СЧИТЫВАЕМ ПЕРЕМЕННУЮ:
        timer_str = self.msg_timer_entry.text().strip()
        timer_val = int(timer_str) if timer_str else 0

        # 2. И ТОЛЬКО ПОСЛЕ ЭТОГО ДЕЛАЕМ ПРОВЕРКУ НА 60 СЕКУНД:
        if timer_val > 60:
            QMessageBox.warning(self, "Защита системы", "Максимальное время блокировки окна не может превышать 60 секунд!")
            return

        if not message or not ip_target:
            QMessageBox.warning(self, "Внимание", "Укажите текст сообщения и выберите целевые IP!")
            return

        if not title:
            title = "Сообщение от администратора"

        self.btn_send_msg.setEnabled(False)
        self.msg_terminal_box.clear()
        self.msg_status_label.setText(f"Авторизован: {self.main_win.sudo_user}")

        # Передаем timer_val в поток
        threading.Thread(
            target=self.run_ansible_messages_thread,
            args=(title, message, ip_target, timer_val),
            daemon=True
        ).start()


    # ИСПРАВЛЕНО: Добавлен пятый аргумент timer_val в объявление метода!
    def run_ansible_messages_thread(self, title, message, ip_target, timer_val):
        try:
            base_dir_path = self.main_win.BASE_DIR

            # Складываем файлы инвентаря строго в выделенную подпапку hosts
            hosts_dir = os.path.join(base_dir_path, "hosts")
            os.makedirs(hosts_dir, exist_ok=True)
            hosts_path = os.path.join(hosts_dir, "hosts_messages")

            # === СИНХРОНИЗАЦИЯ: Читаем состояние галочки из вкладки настроек ===
            ignore_keys = self.main_win.tab_settings.chk_key_checking.isChecked()

            if ignore_keys:
                os.environ["ANSIBLE_HOST_KEY_CHECKING"] = "False"
            else:
                os.environ["ANSIBLE_HOST_KEY_CHECKING"] = "True"

            ip_list = [ip.strip() for ip in ip_target.split(",") if ip.strip()]
            with open(hosts_path, "w", encoding="utf-8") as f:
                f.write("[message_targets]\n")
                for ip in ip_list:
                    if ip.lower() in ["localhost", "127.0.0.1"] or ip.startswith("127."):
                        f.write(f"{ip} ansible_connection=local\n")
                    else:
                        if ignore_keys:
                            f.write(f"{ip} ansible_ssh_common_args='-o StrictHostKeyChecking=no'\n")
                        else:
                            f.write(f"{ip} ansible_ssh_common_args='-o StrictHostKeyChecking=yes'\n")

            # Безопасное сохранение тяжелых строк во временный файл переменных JSON
            playbooks_dir = os.path.join(base_dir_path, "playbooks")
            os.makedirs(playbooks_dir, exist_ok=True)
            vars_file_path = os.path.join(playbooks_dir, "message_vars.json")

            vars_dict = {
                "ansible_become_password": self.main_win.sudo_password,
                "msg_title": title,
                "msg_text": message,
                "msg_timeout": timer_val  # Пробрасываем таймер
            }

            if not self.main_win.tab_settings.chk_use_ssh_key.isChecked():
                vars_dict["ansible_password"] = self.main_win.sudo_password

            with open(vars_file_path, "w", encoding="utf-8") as json_f:
                json.dump(vars_dict, json_f, ensure_ascii=False, indent=4)

            # Вызываем твой асинхронный плейбук
            playbook_path = os.path.join(playbooks_dir, "messages_playbook.yml")
            cmd = ["ansible-playbook", "-i", hosts_path, playbook_path, "--extra-vars", f"@{vars_file_path}"]

            # === СИНХРОНИЗАЦИЯ: Читаем параметры сетевых таймаутов из вкладки настроек ===
            timeout_index = self.main_win.tab_settings.timeout_combo.currentIndex()
            timeout_val_ansible = "30" if timeout_index == 1 else ("60" if timeout_index == 2 else "10")
            cmd.extend(["-T", timeout_val_ansible])

            # === СИНХРОНИЗАЦИЯ: Читаем выбранный уровень детализации дебага задач ===
            verbosity_index = self.main_win.tab_settings.verbosity_combo.currentIndex()
            if verbosity_index == 1:
                cmd.append("-v")
            elif verbosity_index == 2:
                cmd.append("-vvvv")

            self.log_signal.emit(f"[АНСИБЛ СООБЩЕНИЯ]: Подготовка сценария массовой рассылки...\nЗаголовок окна: {title}\nТекст сообщения: {message}\nБлокировка: {timer_val} сек.\n" + "="*60)

            # Отправляем сформированную команду в сквозной потоковый движок чтения логов главного окна
            self.main_win._execute_command_stream(cmd, self.msg_terminal_box, self.btn_send_msg, self.msg_status_label)

        except Exception as e:
            QMetaObject.invokeMethod(self.msg_terminal_box, "append", Qt.QueuedConnection, Q_ARG(str, f"[ОШИБКА ДВИЖКА СООБЩЕНИЙ]: {e}"))
            QMetaObject.invokeMethod(self.btn_send_msg, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, True))
