import os
import json
import threading
import subprocess
import base64
# Пишите это в самом верху файлов вкладок вместо конструкции "import __main__ / from main import ..."
from widgets.autocomplete import FreeIPAAutocompleteEntry
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QGridLayout,
    QLabel, QPushButton, QHBoxLayout, QLineEdit,
    QMessageBox, QScrollArea, QTextEdit, QFileDialog
)
from PyQt5.QtCore import Qt, QMetaObject, Q_ARG, pyqtSignal

class YandexTab(QWidget):
    # Безопасный сигнал для вывода логов из фонового потока в основной GUI-поток
    log_signal = pyqtSignal(str)

    def __init__(self, parent_window, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main_win = parent_window  # Сохраняем ссылку на главное окно AnsibleGuiApp
        self.tile_rows = []            # Список для хранения строк ввода сайтов Табло
        self.remote_folder = "/etc/opt/yandex/browser/policies/managed"

        self.setup_ui()
        self.log_signal.connect(self.append_log_safe)

    def setup_ui(self):
        layout_tab_yandex = QVBoxLayout(self)
        layout_tab_yandex.setContentsMargins(10, 10, 10, 10)

        # --- БЛОК 1: Назначение (Выбор ПК) ---
        frame_targets = QGroupBox(" Параметры назначения ")
        grid_targets = QGridLayout(frame_targets)
        grid_targets.setSpacing(10)

        grid_targets.addWidget(QLabel("Целевые ПК (IP / Хосты FreeIPA через запятую):"), 0, 0)

        import __main__
        if hasattr(__main__, 'FreeIPAAutocompleteEntry'):
            self.policy_ip_entry = __main__.FreeIPAAutocompleteEntry()
        else:
            from main import FreeIPAAutocompleteEntry
            self.policy_ip_entry = FreeIPAAutocompleteEntry()

        self.policy_ip_entry.setPlaceholderText("Вводите имена или IP через запятую...")
        grid_targets.addWidget(self.policy_ip_entry, 0, 1)
        layout_tab_yandex.addWidget(frame_targets)

        # --- БЛОК 2: Основные параметры (Стартовая и Фон) ---
        frame_basic_policies = QGroupBox(" Основные параметры браузера ")
        grid_basic = QGridLayout(frame_basic_policies)
        grid_basic.setSpacing(10)

        # Поле ввода стартовой страницы
        grid_basic.addWidget(QLabel("Стартовая страница (URL):"), 0, 0)
        self.le_homepage = QLineEdit()
        self.le_homepage.setPlaceholderText("Например: https://ya.ru (оставьте пустым, если не нужно менять)")
        grid_basic.addWidget(self.le_homepage, 0, 1, 1, 2)

        # Поле ввода пути к картинке фонда
        grid_basic.addWidget(QLabel("Фоновое изображение (Обои):"), 1, 0)
        self.le_wallpaper_path = QLineEdit()
        self.le_wallpaper_path.setPlaceholderText("Выберите локальный файл изображения (.jpg, .png)...")
        self.le_wallpaper_path.setReadOnly(False)
        grid_basic.addWidget(self.le_wallpaper_path, 1, 1)

        # Кнопка «Обзор...» для выбора картинки (Жестко завязана на !important, чтобы сбить CSS из main.py)
        self.btn_browse_wallpaper = QPushButton("Обзор...")
        self.btn_browse_wallpaper.setCursor(Qt.PointingHandCursor)
        self.btn_browse_wallpaper.setFixedSize(110, 29)
        self.btn_browse_wallpaper.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-size: 13px;
                font-weight: bold;
                border-radius: 4px;
                border: none;
                margin: 0px !important;
                padding: 0px !important;
            }
            QPushButton:hover { background-color: #219653; }
        """)
        self.btn_browse_wallpaper.clicked.connect(self.browse_wallpaper_file)
        grid_basic.addWidget(self.btn_browse_wallpaper, 1, 2)

        layout_tab_yandex.addWidget(frame_basic_policies)

        # --- БЛОК 3: Конструктор Табло Яндекса ---
        frame_constructor = QGroupBox(" Конструктор плиток Табло (Быстрый доступ) ")
        layout_constructor = QVBoxLayout(frame_constructor)

        # Кнопка добавления новой строчки сайта
        self.btn_add_tile = QPushButton("+ Добавить сайт в Табло")
        self.btn_add_tile.setCursor(Qt.PointingHandCursor)
        self.btn_add_tile.setFixedSize(290, 34)
        self.btn_add_tile.setStyleSheet("""
            QPushButton {
                background-color: #2980b9;
                color: white;
                font-size: 13px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
                margin-top: 0px !important;
                margin-bottom: 0px !important;
                padding: 0px 10px !important;
            }
            QPushButton:hover {
                background-color: #2471a3;
            }
            QPushButton:pressed {
                background-color: #1f618d;
            }
        """)
        self.btn_add_tile.clicked.connect(lambda: self.add_tile_row())
        layout_constructor.addWidget(self.btn_add_tile)

        # Область прокрутки (ScrollArea) для строк с сайтами
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: 1px solid #CCCCCC; border-radius: 4px; background-color: white; }")

        self.scroll_widget = QWidget()
        self.scroll_widget.setStyleSheet("background-color: white;")
        self.tiles_layout = QVBoxLayout(self.scroll_widget)
        self.tiles_layout.setContentsMargins(5, 5, 5, 5)
        self.tiles_layout.setSpacing(8)

        # Создаем скрытый виджет-распорку в самом низу, чтобы элементы прижимались к верху
        self.spacer_widget = QWidget()
        self.tiles_layout.addWidget(self.spacer_widget)

        self.scroll_area.setWidget(self.scroll_widget)
        layout_constructor.addWidget(self.scroll_area)
        layout_tab_yandex.addWidget(frame_constructor)

        # --- БЛОК 4: Управление и статус ---
        layout_buttons = QHBoxLayout()

        self.btn_run_policies = QPushButton("Применить все политики")
        self.btn_run_policies.setCursor(Qt.PointingHandCursor)
        self.btn_run_policies.setStyleSheet("""
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
        self.btn_run_policies.clicked.connect(self.start_policy_process)

        self.clear_policy_log_button = QPushButton("Очистить терминал")
        self.clear_policy_log_button.setCursor(Qt.PointingHandCursor)
        self.clear_policy_log_button.setStyleSheet("""
            QPushButton { background-color: #f0f3f4; color: #34495e; border: 1px solid #bdc3c7; }
            QPushButton:hover { background-color: #eaeded; border-color: #95a5a6; }
            QPushButton:pressed { background-color: #d5dbdb; }
        """)
        self.clear_policy_log_button.clicked.connect(lambda: self.policy_terminal_box.clear())

        self.policy_status_label = QLabel(f"Авторизован: {self.main_win.sudo_user}")
        self.policy_status_label.setStyleSheet("color: #2E7D32; font-style: italic;")

        layout_buttons.addWidget(self.btn_run_policies)
        layout_buttons.addWidget(self.clear_policy_log_button)
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.policy_status_label)
        layout_tab_yandex.addLayout(layout_buttons)

        # --- БЛОК 5: Зеленый терминал логов ---
        self.policy_terminal_box = QTextEdit()
        self.policy_terminal_box.setReadOnly(True)
        self.policy_terminal_box.setStyleSheet("""
            QTextEdit { background-color: #1E1E1E; color: #00FF00; font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; border: 1px solid #CCCCCC; }
        """)
        layout_tab_yandex.addWidget(self.policy_terminal_box)

        # Инициализируем одну пустую строчку сайта при открытии вкладки
        self.add_tile_row()

    def browse_wallpaper_file(self):
        """Диалог выбора локальной картинки для фона (Железный фикс кортежа)."""
        # Распаковываем кортеж Qt сразу в две переменные: путь и фильтр
        file_path, selected_filter = QFileDialog.getOpenFileName(
            self, "Выберите изображение для фона Броузера", "",
            "Изображения (*.jpg *.jpeg *.png);;Все файлы (*.*)"
        )
        # Если путь выбран, пишем в текстовое поле СТРОКУ, а не кортеж
        if file_path:
            self.le_wallpaper_path.setText(str(file_path))

    def add_tile_row(self, name_txt="", url_txt="", bg_txt="EC5515", text_txt="FFFFFF"):
        """Динамически добавляет новую строку полей для создания плитки сайта."""
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)

        le_name = QLineEdit()
        le_name.setPlaceholderText("Название (например: Почта)")
        le_name.setText(name_txt)

        le_url = QLineEdit()
        le_url.setPlaceholderText("Ссылка (например: https://mail.ru)")
        le_url.setText(url_txt)

        le_bg = QLineEdit()
        le_bg.setPlaceholderText("Цвет плитки (HEX)")
        le_bg.setText(bg_txt)
        le_bg.setFixedWidth(110)

        le_text = QLineEdit()
        le_text.setPlaceholderText("Цвет текста (HEX)")
        le_text.setText(text_txt)
        le_text.setFixedWidth(110)

        btn_del = QPushButton("×")
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setFixedSize(29, 29)
        btn_del.setStyleSheet("""
            QPushButton {
                background-color: #c0392b;
                color: white;
                font-weight: bold;
                font-size: 18px;
                border-radius: 4px;
                border: none;
                margin: 0px;
                padding: 0px 0px 3px 0px;
            }
            QPushButton:hover { background-color: #e74c3c; }
            QPushButton:pressed { background-color: #962d22; }
        """)

        row_data = {
            "name": le_name,
            "url": le_url,
            "bg": le_bg,
            "text": le_text,
            "widget": row_widget
        }

        btn_del.clicked.connect(lambda: self.remove_tile_row(row_data))

        row_layout.addWidget(QLabel("Сайт:"))
        row_layout.addWidget(le_name, 2)
        row_layout.addWidget(QLabel("URL:"))
        row_layout.addWidget(le_url, 3)
        row_layout.addWidget(QLabel("Фон:"))
        row_layout.addWidget(le_bg, 1)
        row_layout.addWidget(QLabel("Текст:"))
        row_layout.addWidget(le_text, 1)
        row_layout.addWidget(btn_del)

        # Вставляем строку строго перед нижней пружиной-распоркой
        idx = self.tiles_layout.indexOf(self.spacer_widget)
        self.tiles_layout.insertWidget(idx, row_widget)
        self.tile_rows.append(row_data)

    def remove_tile_row(self, row_data):
        """Удаляет строку полей сайта из интерфейса и кэша памяти."""
        if len(self.tile_rows) <= 1:
            QMessageBox.information(self, "Внимание", "Должен оставаться как минимум один сайт!")
            return

        row_data["widget"].deleteLater()
        self.tile_rows.remove(row_data)

    def append_log_safe(self, text):
        """Потокобезопасный вывод строки лога в окно терминала."""
        self.policy_terminal_box.append(text)

    def start_policy_process(self):
        """Сборка единого JSON манифеста и запуск фонового потока Ansible."""
        ip_target = self.policy_ip_entry.text().strip()
        if not ip_target:
            QMessageBox.warning(self, "Внимание", "Укажите целевые IP или хосты!")
            return

        policies_dict = {}

        # 1. Сборка Стартовой страницы
        homepage_url = self.le_homepage.text().strip()
        if homepage_url:
            policies_dict["RestoreOnStartup"] = 4
            policies_dict["RestoreOnStartupURLs"] = [homepage_url]

        # 2. Сборка Фона (Официальное правило Новой вкладки для Linux хостов)
        wallpaper_path = self.le_wallpaper_path.text().strip()
        if wallpaper_path and os.path.exists(wallpaper_path):
            # Передаем легитимный локальный URL, который появится на целевом ПК после работы Ansible
            policies_dict["NtpWallpaper"] = "file:///usr/share/backgrounds/corporate_wallpaper.jpg"

        # 3. Сборка массива Плиток Табло быстрого доступа
        tablo_list = []
        for row in self.tile_rows:
            url = row["url"].text().strip()
            title = row["name"].text().strip()
            bg_color = row["bg"].text().strip().replace("#", "")
            text_color = row["text"].text().strip().replace("#", "")

            if url and title:
                tablo_list.append({
                    "title": title,
                    "url": url,
                    "background_color": bg_color if bg_color else "EC5515",
                    "text_color": text_color if text_color else "FFFFFF"
                })

        if tablo_list:
            policies_dict["TabloPreset"] = tablo_list

        if not policies_dict and not wallpaper_path:
            QMessageBox.warning(self, "Внимание", "Заполните хотя бы один параметр!")
            return

        # Формируем плоский JSON
        policies_json_str = json.dumps(policies_dict, indent=4, ensure_ascii=False)

        self.btn_run_policies.setEnabled(False)
        self.policy_terminal_box.clear()
        self.policy_status_label.setText(f"Авторизован: {self.main_win.sudo_user}")

        # Запускаем выполнение в фоновом потоке Python
        threading.Thread(
            target=self.run_ansible_policies_thread,
            args=(policies_json_str, ip_target, wallpaper_path),
            daemon=True
        ).start()

    def run_ansible_policies_thread(self, policies_json_str, ip_target, wallpaper_path):
        try:
            # Читаем BASE_DIR через главное окно, защищаясь от циклического импорта
            base_dir_path = self.main_win.BASE_DIR

            # Складываем файлы инвентаря строго в выделенную подпапку hosts
            hosts_dir = os.path.join(base_dir_path, "hosts")
            os.makedirs(hosts_dir, exist_ok=True)
            hosts_path = os.path.join(hosts_dir, "hosts_yandex")

            # === СИНХРОНИЗАЦИЯ: Читаем состояние галочки проверки SSH-ключей ===
            ignore_keys = self.main_win.tab_settings.chk_key_checking.isChecked()

            # Железное переопределение на уровне процесса для фоновых модулей Ansible
            if ignore_keys:
                os.environ["ANSIBLE_HOST_KEY_CHECKING"] = "False"
            else:
                os.environ["ANSIBLE_HOST_KEY_CHECKING"] = "True"

            # Формируем инвентарь для конкретной сетевой задачи
            ip_list = [ip.strip() for ip in ip_target.split(",") if ip.strip()]
            with open(hosts_path, "w", encoding="utf-8") as f:
                f.write("[yandex_targets]\n")
                for ip in ip_list:
                    if ip.lower() in ["localhost", "127.0.0.1"] or ip.startswith("127."):
                        f.write(f"{ip} ansible_connection=local\n")
                    else:
                        # Динамически управляем аргументами SSH-подключения на основе GUI
                        if ignore_keys:
                            f.write(f"{ip} ansible_ssh_common_args='-o StrictHostKeyChecking=no'\n")
                        else:
                            f.write(f"{ip} ansible_ssh_common_args='-o StrictHostKeyChecking=yes'\n")

            # Пишем тяжелый JSON-манифест во временный файл переменных,
            # чтобы обойти ограничение Linux на длину аргументов командной строки (ARG_MAX)
            playbooks_dir = os.path.join(base_dir_path, "playbooks")
            os.makedirs(playbooks_dir, exist_ok=True)
            vars_file_path = os.path.join(playbooks_dir, "yandex_vars.json")

            # Собираем все переменные, включая пароль sudo и контент политик
            vars_dict = {
                "ansible_become_password": self.main_win.sudo_password,
                "yandex_policy_content": policies_json_str,
                "yandex_local_wallpaper_path": wallpaper_path
            }

            if not self.main_win.tab_settings.chk_use_ssh_key.isChecked():
                vars_dict["ansible_password"] = self.main_win.sudo_password

            # Сохраняем словарь в файл
            with open(vars_file_path, "w", encoding="utf-8") as json_f:
                json.dump(vars_dict, json_f, ensure_ascii=False, indent=4)

            # Путь к заранее заготовленному неизменяемому плейбуку в папке playbooks
            playbook_path = os.path.join(playbooks_dir, "yandex_policy_playbook.yml")

            # Формируем команду вызова. Вместо строки передаем путь к файлу через префикс '@'
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

            # Срезаем логи для вывода на экран панели управления
            log_display = policies_json_str
            if "NTPCustomBackground" in log_display:
                log_display = "[ФОНОВОЕ ИЗОБРАЖЕНИЕ ЗАКОДИРОВАНО В BASE64]\n" + json.dumps({k: v for k, v in json.loads(policies_json_str).items() if k != "NTPCustomBackground"}, indent=4, ensure_ascii=False)

            self.log_signal.emit(f"[АНСИБЛ ПЛЕЙБУК ЯНДЕКС]: Данные упакованы в yandex_vars.json. Запуск сценария...\n{log_display}\n" + "="*60)

            # Передаем сформированную команду в универсальный потоковый движок чтения логов главного окна
            self.main_win._execute_command_stream(
                cmd, self.policy_terminal_box, self.btn_run_policies, self.policy_status_label
            )
        except Exception as e:
            self.log_signal.emit(f"[ОШИБКА ДВИЖКА ЗАПУСКА]: {e}")
            QMetaObject.invokeMethod(self.btn_run_policies, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, True))
