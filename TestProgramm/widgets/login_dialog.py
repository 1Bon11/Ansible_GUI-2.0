import os
import sys
import shutil
import subprocess
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QMessageBox, QApplication, QGroupBox
from PyQt5.QtCore import Qt

# Корневая папка проекта для сохранения базы хостов в logs/hosts_db.txt
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class LoginDialog(QDialog):
    """Окно авторизации администратора с раздельной системной проверкой Sudo и FreeIPA Kerberos."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Авторизация — Ansible GUI")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Задаем базовые размеры (ширина фиксирована, высота адаптируется под галочку)
        self.setMinimumWidth(450)
        self.resize(450, 480)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(10)

        # Главный заголовок окна
        lbl_title = QLabel("Панель управления Ansible")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2C3E50; margin-bottom: 5px;")
        main_layout.addWidget(lbl_title)

        # === БЛОК 1: Права локального администратора (Sudo) ===
        self.group_local = QGroupBox()
        grid_local = QGridLayout(self.group_local)
        grid_local.setSpacing(10)
        grid_local.setContentsMargins(15, 15, 15, 15)

        # Текстовый заголовок с уникальным objectName для стилизации без обводки
        lbl_local_title = QLabel("Права суперпользователя")
        lbl_local_title.setObjectName("login_title_label")
        lbl_local_title.setStyleSheet("font-weight: bold; color: #2C3E50; font-size: 13px; margin-bottom: 5px;")
        grid_local.addWidget(lbl_local_title, 0, 0, 1, 2)

        grid_local.addWidget(QLabel("Локальный admin:"), 1, 0)
        self.user_input = QLineEdit()
        self.user_input.setText("administrator")
        grid_local.addWidget(self.user_input, 1, 1)

        grid_local.addWidget(QLabel("Пароль Sudo/SSH:"), 2, 0)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        grid_local.addWidget(self.password_input, 2, 1)

        main_layout.addWidget(self.group_local)

        # Переключатель доменной авторизации
        self.chk_use_domain = QCheckBox("Авторизоваться в домене FreeIPA")
        self.chk_use_domain.setChecked(True)
        self.chk_use_domain.toggled.connect(self.toggle_domain_fields)
        main_layout.addWidget(self.chk_use_domain)

        # === БЛОК 2: Доступ к FreeIPA (Kerberos) ===
        self.group_domain = QGroupBox()
        grid_domain = QGridLayout(self.group_domain) # ИСПРАВЛЕНО: Объявлено как локальная переменная grid_domain
        grid_domain.setSpacing(10)
        grid_domain.setContentsMargins(15, 15, 15, 15)

        # Текстовый заголовок домена с уникальным objectName
        lbl_domain_title = QLabel("Учетная запись FreeIPA")
        lbl_domain_title.setObjectName("login_title_label")
        lbl_domain_title.setStyleSheet("font-weight: bold; color: #2C3E50; font-size: 13px; margin-bottom: 5px;")
        grid_domain.addWidget(lbl_domain_title, 0, 0, 1, 2) # ИСПРАВЛЕНО: Убрана приставка self. (Строка 64 больше не упадет!)

        grid_domain.addWidget(QLabel("Администратор домена:"), 1, 0)
        self.domain_user_entry = QLineEdit()
        self.domain_user_entry.setText("admin")
        grid_domain.addWidget(self.domain_user_entry, 1, 1)

        grid_domain.addWidget(QLabel("Пароль домена (Kerberos):"), 2, 0)
        self.domain_password_entry = QLineEdit()
        self.domain_password_entry.setEchoMode(QLineEdit.Password)
        grid_domain.addWidget(self.domain_password_entry, 2, 1)

        main_layout.addWidget(self.group_domain)

        # Кнопка входа
        self.btn_ok = QPushButton("Войти в панель")
        self.btn_ok.setCursor(Qt.PointingHandCursor)
        self.btn_ok.setText("Войти в панель") # Сброс опечатки строки
        self.btn_ok.setStyleSheet("font-weight: bold; padding: 10px;")
        self.btn_ok.clicked.connect(self.check_auth)
        main_layout.addWidget(self.btn_ok)

        # Горячие клавиши для быстрой отправки формы по нажатию Enter
        self.password_input.returnPressed.connect(self.check_auth)
        self.domain_password_entry.returnPressed.connect(self.check_auth)
        self.password_input.setFocus()

    def toggle_domain_fields(self, checked):
        """Плавное скрытие доменной группы и динамическое изменение высоты окна под Fly WM."""
        # ИСПРАВЛЕНО НАМЕРТВО: Скрываем всю рамку-обводочку целиком в один клик
        self.group_domain.setVisible(checked)

        # Динамически меняем размеры окна авторизации, чтобы оно аккуратно схлопывалось во Fly WM
        if checked:
            self.setMinimumSize(450, 480)
            self.resize(450, 480)
        else:
            self.setMinimumSize(450, 290)
            self.resize(450, 290)


    def verify_local_sudo_password(self, username, password):
        """Реальная проверка пароля через su (PAM-подсистему Linux) без уязвимостей shell=True."""
        try:
            cmd = ["su", username, "-c", "whoami"]
            process = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            stdout, stderr = process.communicate(input=f"{password}\n", timeout=3)
            return process.returncode == 0
        except Exception:
            return False

    def build_hosts_database(self):
        """Безопасный сбор базы хостов FreeIPA на основе kinit и ipa host-find."""
        log_dir = os.path.join(BASE_DIR, "logs")
        os.makedirs(log_dir, exist_ok=True)
        db_path = os.path.join(log_dir, "hosts_db.txt")

        # Если домен отключен — принудительно очищаем кэш хостов
        if not self.chk_use_domain.isChecked():
            try:
                with open(db_path, "w", encoding="utf-8") as f: f.write("")
            except Exception: pass
            return True

        ipa_user = self.domain_user_entry.text().strip()
        ipa_password = self.domain_password_entry.text().strip()

        if not ipa_user or not ipa_password:
            QMessageBox.warning(self, "Внимание FreeIPA", "Заполните данные учетной записи FreeIPA!")
            return False

        try:
            # 1. Безопасный вызов kinit для получения билета Kerberos
            kinit_process = subprocess.Popen(
                ["kinit", ipa_user],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            stdout_k, stderr_k = kinit_process.communicate(input=f"{ipa_password}\n", timeout=5)

            if kinit_process.returncode != 0:
                err_msg = stderr_k.strip() or stdout_k.strip() or "Неверный пароль Kerberos."
                QMessageBox.critical(self, "Ошибка FreeIPA", f"Не удалось получить билет Kerberos!\n\nОтвет системы:\n{err_msg}")
                self.domain_password_entry.clear()
                self.domain_password_entry.setFocus()
                return False

            # 2. Вызов host-find и сбор FQDN/коротких имен машин
            ipa_path = shutil.which("ipa") or "/usr/bin/ipa"
            if not os.path.exists(ipa_path):
                # Если бинарник ipa отсутствует (например, утилиты администрирования не поставлены локально)
                with open(db_path, "w", encoding="utf-8") as f: f.write("")
                return True

            result = subprocess.run([ipa_path, "host-find"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False, timeout=6)
            if result.returncode != 0:
                with open(db_path, "w", encoding="utf-8") as f: f.write("")
                return True

            hosts = []
            for line in result.stdout.splitlines():
                line_str = line.strip()
                line_lower = line_str.lower()
                if not line_str or any(x in line_lower for x in ["/", "@", "generic", "---", "выдано хостов", "matched", "найдено хостов", "параметры"]):
                    continue
                if ":" in line_str:
                    parts = line_str.split(":", 1)
                    if len(parts) > 1:
                        key, val = parts[0].lower().strip(), parts[1].strip()
                        if any(m in key for m in ["хост", "host", "fqdn", "имя"]) and val and " " not in val:
                            hosts.append(val)
                            continue
                if "." in line_str and " " not in line_str and not line_str.replace(".", "").isdigit():
                    hosts.append(line_str)
                    continue
                if " " not in line_str and line_str.isalnum():
                    hosts.append(line_str)

            clean_hosts = sorted(list(set(hosts)))
            with open(db_path, "w", encoding="utf-8") as f:
                f.write("\n".join(clean_hosts))
            return True

        except Exception:
            with open(db_path, "w", encoding="utf-8") as f: f.write("")
            return True

    def check_auth(self):
        """Сквозная валидация локальных/доменных прав перед успешным закрытием окна."""
        username = self.user_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Внимание", "Заполните имя локального пользователя и его пароль!")
            return

        # Визуальный индикатор ожидания на время выполнения su/kinit
        QApplication.setOverrideCursor(Qt.WaitCursor)
        local_valid = self.verify_local_sudo_password(username, password)
        QApplication.restoreOverrideCursor()

        if not local_valid:
            QMessageBox.critical(self, "Ошибка авторизации", "Введен неверный пароль Sudo/SSH!\nДоступ отклонен.")
            self.password_input.clear()
            self.password_input.setFocus()
            return

        # Генерируем или очищаем базу хостов (внутри происходит kinit)
        if not self.build_hosts_database():
            return

        # Возвращаем управление в main.py с флагом Accepted
        self.accept()

    def get_username(self): return self.user_input.text().strip()
    def get_password(self): return self.password_input.text().strip()
