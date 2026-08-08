import os
import json
import subprocess
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QGroupBox, QCheckBox, QComboBox, QMessageBox
from PyQt5.QtCore import Qt

class SettingsTab(QWidget):
    def __init__(self, parent_window):
        super().__init__()
        self.main_win = parent_window  # Доступ к главному окну QMainWindow

        # Главный вертикальный слой всей вкладки с хорошими отступами
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # === БЛОК 1: Параметры оптимизации и подключения Ansible ===
        group_ansible = QGroupBox(" Параметры оптимизации сетевого движка Ansible ")
        grid_ansible = QGridLayout(group_ansible)
        grid_ansible.setContentsMargins(20, 24, 20, 20)
        grid_ansible.setSpacing(16)

        # Распределение колонок: левая подстраивается под текст, правая забирает остаток
        grid_ansible.setColumnStretch(0, 0)
        grid_ansible.setColumnStretch(1, 1)

        # 1. Чекбокс авторизации (занимает 2 колонки, убрана лишняя метка слева)
        self.chk_use_ssh_key = QCheckBox("Использовать SSH-ключ администратора")
        self.chk_use_ssh_key.setToolTip("Позволяет выполнять подключение к узлам без использования утилиты sshpass")
        self.chk_use_ssh_key.setChecked(False)
        grid_ansible.addWidget(self.chk_use_ssh_key, 0, 0, 1, 2, Qt.AlignLeft)

        # 2. Чекбокс проверки SSH-ключей (занимает 2 колонки, убран лишний текст)
        self.chk_key_checking = QCheckBox("Игнорировать проверку ключей неизвестных хостов")
        self.chk_key_checking.setToolTip("Рекомендуется включить, чтобы автоматизация не зависала на новых или переустановленных серверах")
        self.chk_key_checking.setChecked(True)
        grid_ansible.addWidget(self.chk_key_checking, 1, 0, 1, 2, Qt.AlignLeft)

        # Небольшой разделительный шаг между чекбоксами и комбобоксами для структуры
        grid_ansible.setRowMinimumHeight(2, 8)

        # 3. Выпадающий список таймаутов
        grid_ansible.addWidget(QLabel("Таймаут ожидания ответа:"), 3, 0)
        self.timeout_combo = QComboBox()
        self.timeout_combo.addItems(["10 секунд (Стандарт)", "30 секунд (Медленная сеть)", "60 секунд (Максимальный)"])
        self.timeout_combo.setFixedWidth(320)
        grid_ansible.addWidget(self.timeout_combo, 3, 1, Qt.AlignLeft)

        # 4. Выпадающий список логирования (Дебаг)
        grid_ansible.addWidget(QLabel("Детализация логов (Дебаг):"), 4, 0)
        self.verbosity_combo = QComboBox()
        self.verbosity_combo.addItems(["Обычный вывод (PLAY RECAP)", "Подробный отчет", "Максимальный дебаг SSH"])
        self.verbosity_combo.setToolTip("Режимы вывода Ansible: базовый, подробный (-v) или режим полной отладки сессий (-vvvv)")
        self.verbosity_combo.setFixedWidth(320)
        grid_ansible.addWidget(self.verbosity_combo, 4, 1, Qt.AlignLeft)

        layout.addWidget(group_ansible)

        # === БЛОК 2: Системное обслуживание панели управления ===
        group_system = QGroupBox(" Обслуживание и файлы автоматизации ")
        grid_system = QGridLayout(group_system)
        grid_system.setContentsMargins(20, 24, 20, 20)
        grid_system.setSpacing(16)
        grid_system.setColumnStretch(0, 0)
        grid_system.setColumnStretch(1, 1)

        # Очистка логов (Опасное действие -> Спокойный плоский красный цвет)
        grid_system.addWidget(QLabel("Очистка глобального лога истории:"), 0, 0)
        self.btn_clear_logs = QPushButton("Удалить историю")
        self.btn_clear_logs.setCursor(Qt.PointingHandCursor)
        self.btn_clear_logs.setFixedWidth(320)
        self.btn_clear_logs.setStyleSheet("""
            QPushButton { background-color: #e74c3c; color: white; border: none; }
            QPushButton:hover { background-color: #c0392b; }
            QPushButton:pressed { background-color: #962d22; }
        """)
        self.btn_clear_logs.clicked.connect(self.clear_history_log)
        grid_system.addWidget(self.btn_clear_logs, 0, 1, Qt.AlignLeft)

        # Просмотр файлов (Второстепенное действие -> Нейтральный светло-серый цвет)
        grid_system.addWidget(QLabel("Просмотр конфигурационных файлов на диске:"), 1, 0)
        self.btn_open_folder = QPushButton("Открыть папку логов приложения")
        self.btn_open_folder.setCursor(Qt.PointingHandCursor)
        self.btn_open_folder.setFixedWidth(320)
        self.btn_open_folder.setStyleSheet("""
            QPushButton { background-color: #f0f3f4; color: #34495e; border: 1px solid #bdc3c7; }
            QPushButton:hover { background-color: #eaeded; border-color: #95a5a6; }
            QPushButton:pressed { background-color: #d5dbdb; }
        """)
        self.btn_open_folder.clicked.connect(self.open_logs_folder)
        grid_system.addWidget(self.btn_open_folder, 1, 1, Qt.AlignLeft)

        layout.addWidget(group_system)

        # === БЛОК АВТОСОХРАНЕНИЯ НАСТРОЕК ===
        # Автоматически загружаем сохраненные настройки из папки config при старте окна
        self.load_settings_from_json()

        # Подключаем автоматическое сохранение при любом клике или изменении параметров
        self.chk_use_ssh_key.stateChanged.connect(self.save_settings_to_json)
        self.chk_key_checking.stateChanged.connect(self.save_settings_to_json)
        self.timeout_combo.currentIndexChanged.connect(self.save_settings_to_json)
        self.verbosity_combo.currentIndexChanged.connect(self.save_settings_to_json)

        layout.addStretch() # Мягко прижимает группы к верху окна, сохраняя верстку

    def clear_history_log(self):
        """Безопасная очистка лога истории на диске"""
        log_path = os.path.join(self.main_win.BASE_DIR, "logs", "history.log")
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены, что хотите полностью очистить лог истории выполнения?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write("")
                QMessageBox.information(self, "Успех", "Логи истории успешно очищены.")
            except Exception as e:
                QMetaObject.invokeMethod(self, "show_critical_error", Qt.QueuedConnection, Q_ARG(str, f"Не удалось очистить файл логов: {e}"))

    def open_logs_folder(self):
        """Открытие системного менеджера файлов Astra Linux Fly в папке логов"""
        log_dir = os.path.join(self.main_win.BASE_DIR, "logs")
        os.makedirs(log_dir, exist_ok=True)
        try:
            subprocess.Popen(["fly-fm", log_dir])
        except Exception:
            try:
                os.startdirectory(log_dir)
            except Exception:
                pass

    def save_settings_to_json(self):
        """Сохранение состояния всех галочек и комбобоксов в файл конфигурации."""
        try:
            base_dir_path = self.main_win.BASE_DIR

            # ИСПРАВЛЕНО: Создаем выделенную подпапку config, если её ещё нет
            config_dir = os.path.join(base_dir_path, "config")
            os.makedirs(config_dir, exist_ok=True)
            config_path = os.path.join(config_dir, "config.json")

            settings_dict = {
                "use_ssh_key": self.chk_use_ssh_key.isChecked(),
                "ignore_key_checking": self.chk_key_checking.isChecked(),
                "timeout_index": self.timeout_combo.currentIndex(),
                "verbosity_index": self.verbosity_combo.currentIndex()
            }

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(settings_dict, f, ensure_ascii=False, indent=4)
        except Exception:
            pass  # Молча игнорируем ошибки записи, чтобы не спамить сисадмина

    def load_settings_from_json(self):
        """Загрузка сохраненных параметров при запуске панели управления."""
        try:
            base_dir_path = self.main_win.BASE_DIR
            # ИСПРАВЛЕНО: Читаем строго из подпапки config
            config_path = os.path.join(base_dir_path, "config", "config.json")

            if not os.path.exists(config_path):
                return  # Файла нет (первый запуск на новом ПК) -> остаются значения по умолчанию

            with open(config_path, "r", encoding="utf-8") as f:
                settings_dict = json.load(f)

            # Блокируем сигналы виджетов, чтобы при программном выставлении
            # галочек метод сохранения save_settings_to_json не вызывался циклически
            self.chk_use_ssh_key.blockSignals(True)
            self.chk_key_checking.blockSignals(True)
            self.timeout_combo.blockSignals(True)
            self.verbosity_combo.blockSignals(True)

            # Восстанавливаем состояние элементов управления из файла
            if "use_ssh_key" in settings_dict:
                self.chk_use_ssh_key.setChecked(settings_dict["use_ssh_key"])
            if "ignore_key_checking" in settings_dict:
                self.chk_key_checking.setChecked(settings_dict["ignore_key_checking"])
            if "timeout_index" in settings_dict:
                self.timeout_combo.setCurrentIndex(settings_dict["timeout_index"])
            if "verbosity_index" in settings_dict:
                self.verbosity_combo.setCurrentIndex(settings_dict["verbosity_index"])

        except Exception:
            pass
        finally:
            # Обязательно возвращаем отправку сигналов кнопками в штатный режим
            self.chk_use_ssh_key.blockSignals(False)
            self.chk_key_checking.blockSignals(False)
            self.timeout_combo.blockSignals(False)
            self.verbosity_combo.blockSignals(False)
