import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QGridLayout,
    QLabel, QLineEdit, QPushButton, QHBoxLayout,
    QTextEdit, QMessageBox, QFileDialog, QDialog,
    QListWidget, QListWidgetItem, QApplication
)
from PyQt5.QtCore import Qt, QMetaObject, Q_ARG, pyqtSignal

class FreeIPAAutocompleteEntry(QWidget):
    hosts_loaded = pyqtSignal(list)

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.lista = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("Вводите имена хостов через запятую или выберите из списка...")
        layout.addWidget(self.line_edit)

        self.btn_add = QPushButton("+")
        self.btn_add.setFixedSize(30, 29)
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.setStyleSheet("""
            QPushButton {
                background-color: #2980b9; color: white; font-size: 16px; font-weight: bold;
                border-radius: 4px; border: none; margin: 0px; padding: 0px;
            }
            QPushButton:hover { background-color: #2471a3; }
            QPushButton:pressed { background-color: #1f618d; }
        """)
        self.btn_add.clicked.connect(self.open_checklist_dialog)
        layout.addWidget(self.btn_add)

        self.popup_list = QListWidget()
        self.popup_list.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus)
        self.popup_list.setFocusPolicy(Qt.NoFocus)
        self.popup_list.itemClicked.connect(self._on_item_clicked)

        self.line_edit.focusInEvent = self.custom_focus_in
        self.line_edit.keyPressEvent = self.custom_key_press

        # Базовая инициализация списка хостов при старте приложения
        self.refresh_hosts()

    def text(self): return self.line_edit.text()
    def setText(self, text): self.line_edit.setText(text)
    def setPlaceholderText(self, text): self.line_edit.setPlaceholderText(text)
    def clear(self): self.line_edit.clear()

    def custom_focus_in(self, event):
        QLineEdit.focusInEvent(self.line_edit, event)
        full_text = self.line_edit.text().strip()
        current_word = full_text.split(",")[-1].strip()
        if len(current_word) < 1:
            self.popup_list.hide()
            return
        self.show_suggestions(current_word)

    def _on_item_clicked(self, item):
        full_text = self.line_edit.text()
        parts = [p.strip() for p in full_text.split(",")]
        if parts:
            parts[-1] = item.text()
        else:
            parts = [item.text()]
        clean_parts = [p for p in parts if p]
        self.line_edit.setText(", ".join(clean_parts) + ", ")
        self.popup_list.hide()
        self.line_edit.setFocus()

    def show_suggestions(self, current_word):
        self.popup_list.clear()
        matches = self.lista if not current_word else [item for item in self.lista if current_word.lower() in item.lower()]
        if not matches:
            self.popup_list.hide()
            return
        display_matches = matches[:8]
        self.popup_list.addItems(display_matches)
        self.popup_list.setCurrentRow(0)

        pos = self.line_edit.mapToGlobal(self.line_edit.rect().bottomLeft())
        height = min(180, len(display_matches) * 26 + 4)
        self.popup_list.setGeometry(pos.x(), pos.y() + 2, self.line_edit.width(), height)
        self.popup_list.show()

    def custom_key_press(self, event):
        if self.popup_list.isVisible():
            if event.key() == Qt.Key_Down:
                next_row = (self.popup_list.currentRow() + 1) % self.popup_list.count()
                self.popup_list.setCurrentRow(next_row)
                return
            elif event.key() == Qt.Key_Up:
                prev_row = (self.popup_list.currentRow() - 1 + self.popup_list.count()) % self.popup_list.count()
                self.popup_list.setCurrentRow(prev_row)
                return
            elif event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Tab):
                current_item = self.popup_list.currentItem() or self.popup_list.item(0)
                if current_item:
                    self._on_item_clicked(current_item)
                    event.accept()
                return
            elif event.key() == Qt.Key_Escape:
                self.popup_list.hide()
                event.accept()
                return

        QLineEdit.keyPressEvent(self.line_edit, event)
        full_text = self.line_edit.text()

        if not full_text or full_text.endswith(", ") or full_text.endswith(","):
            self.popup_list.hide()
            return

        current_word = full_text.split(",")[-1].strip()
        if len(current_word) >= 1:
            self.show_suggestions(current_word)
        else:
            self.popup_list.hide()

    def hide_popup(self):
        if hasattr(self, 'popup_list') and self.popup_list.isVisible():
            self.popup_list.hide()

    def open_checklist_dialog(self):
        # ИСПРАВЛЕНО: Убран лишний повторный refresh_hosts(), база уже прочитана при старте
        if not self.lista:
            QMessageBox.information(self, "Инфо", "База FreeIPA пуста.")
            return

        dialog = QDialog(self.window())
        dialog.setAttribute(Qt.WA_StyledBackground, True)
        dialog.setWindowTitle("Выбор целевых ПК")
        dialog.setFixedSize(380, 480)
        dialog_layout = QVBoxLayout(dialog)

        # Поле поиска
        search_edit = QLineEdit()
        search_edit.setPlaceholderText("Быстрый поиск по имени ПК...")
        dialog_layout.addWidget(search_edit)

        # Горизонтальный слой для кнопок массового выбора
        actions_layout = QHBoxLayout()

        btn_select_all = QPushButton("Выбрать все")
        btn_select_all.setCursor(Qt.PointingHandCursor)
        btn_select_all.setStyleSheet("QPushButton { background-color: #2980b9; color: white; padding: 4px; font-size: 12px; } QPushButton:hover { background-color: #2471a3; }")

        btn_deselect_all = QPushButton("Снять все")
        btn_deselect_all.setCursor(Qt.PointingHandCursor)
        btn_deselect_all.setStyleSheet("QPushButton { background-color: #7f8c8d; color: white; padding: 4px; font-size: 12px; } QPushButton:hover { background-color: #707b7c; }")

        actions_layout.addWidget(btn_select_all)
        actions_layout.addWidget(btn_deselect_all)
        dialog_layout.addLayout(actions_layout)

        # Виджет списка
        list_widget = QListWidget()

        # Оставляем локальный styleSheet пустым, чтобы список успешно брал
        # объемные синие кубики с градиентом из твоего глобального styles.py
        list_widget.setStyleSheet("")

        current_hosts = [h.strip().lower() for h in self.line_edit.text().split(",") if h.strip()]

        for host in self.lista:
            item = QListWidgetItem(host)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if host.lower() in current_hosts else Qt.Unchecked)
            list_widget.addItem(item)
        dialog_layout.addWidget(list_widget)

        # ЛОГИКА ДЛЯ КНОПОК «ВЫБРАТЬ ВСЕ» И «СНЯТЬ ВСЕ»
        def select_all_hosts():
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                if not list_widget.isRowHidden(i):
                    item.setCheckState(Qt.Checked)

        def deselect_all_hosts():
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                if not list_widget.isRowHidden(i):
                    item.setCheckState(Qt.Unchecked)

        btn_select_all.clicked.connect(select_all_hosts)
        btn_deselect_all.clicked.connect(deselect_all_hosts)

        # Логика фильтрации поиска
        def filter_hosts(text):
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                list_widget.setRowHidden(i, text.lower() not in item.text().lower())
        search_edit.textChanged.connect(filter_hosts)

        # Главная кнопка применения
        btn_ok = QPushButton("Применить выбор")
        def apply_selection():
            selected = [list_widget.item(i).text() for i in range(list_widget.count()) if list_widget.item(i).checkState() == Qt.Checked]
            if selected:
                self.line_edit.setText(", ".join(selected) + ", ")
            else:
                self.line_edit.clear()
            dialog.accept()

        btn_ok.clicked.connect(apply_selection)
        dialog_layout.addWidget(btn_ok)
        search_edit.setFocus()
        dialog.exec_()

    def refresh_hosts(self):
        # ИСПРАВЛЕНО НАМЕРТВО: Автоматически высчитываем корень проекта на любом ПК без использования внешних импортов
        current_dir = os.path.dirname(os.path.abspath(__file__))  # Папка 'widgets'
        base_dir_path = os.path.dirname(current_dir)              # Корень папки проекта 'TestProgramm'

        db_path = os.path.join(base_dir_path, "logs", "hosts_db.txt")
        self.lista = []
        if os.path.exists(db_path):
            try:
                with open(db_path, "r", encoding="utf-8") as f:
                    self.lista = [line.strip() for line in f if line.strip()]
            except Exception:
                pass
        self.popup_list.clear()
        if self.lista:
            self.hosts_loaded.emit(self.lista)
        else:
            self.popup_list.hide()

class AutocompleteEntry(QLineEdit):
    packages_loaded = pyqtSignal(list)

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.lista = []

        # Создание всплывающего окна подсказок
        self.popup_list = QListWidget()
        self.popup_list.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus)
        self.popup_list.setFocusPolicy(Qt.NoFocus)
        self.popup_list.itemClicked.connect(self._on_item_clicked)

        # Безопасное обновление данных GUI через механизм сигналов
        self.packages_loaded.connect(self._apply_loaded_packages)

        # Асинхронное сканирование кэша пакетов APT в системе
        import threading
        threading.Thread(target=self._load_packages_async, daemon=True).start()

    def _load_packages_async(self):
        """Фоновое чтение списка пакетов apt-cache без блокировки основного потока интерфейса."""
        try:
            if not shutil.which("apt-cache"):
                raise Exception
            result = subprocess.run(["apt-cache", "pkgnames"], stdout=subprocess.PIPE, text=True, timeout=8)
            filtered = [
                pkg.strip() for pkg in result.stdout.splitlines()
                if pkg.strip() and not pkg.startswith("lib") and not pkg.endswith(("-dev", "-dbg"))
            ]
            if filtered:
                self.packages_loaded.emit(sorted(list(set(filtered))))
                return
        except Exception:
            pass
        # Fallback-список на случай отсутствия apt-cache (например, запуск на другой ОС)
        self.packages_loaded.emit(["nginx", "docker-ce", "postgresql-15", "apache2", "git", "zabbix-agent"])

    def _apply_loaded_packages(self, package_list):
        """Слот для записи полученных фоновым потоком пакетов в оперативную память."""
        self.lista = package_list

    def _on_item_clicked(self, item):
        self.insert_completion(item.text())

    def insert_completion(self, completion):
        """Безопасная склейка и подстановка выбранного слова в массив строки через запятую."""
        parts = [p.strip() for p in self.text().split(",")]
        if parts:
            parts[-1] = completion
        else:
            parts = [completion]
        clean_parts = [p for p in parts if p]
        self.setText(", ".join(clean_parts) + ", ")
        self.popup_list.hide()
        self.setFocus()

    def show_suggestions(self, current_word):
        """Фильтрация, расчет геометрии и отображение всплывающего окна подсказок."""
        self.popup_list.clear()
        if not current_word:
            self.popup_list.hide()
            return
        matches = [item for item in self.lista if current_word.lower() in item.lower()]
        if not matches:
            self.popup_list.hide()
            return
        display_matches = matches[:8]
        self.popup_list.addItems(display_matches)
        self.popup_list.setCurrentRow(0)

        # Точное позиционирование строго под QLineEdit
        pos = self.mapToGlobal(self.rect().bottomLeft())
        height = min(180, len(display_matches) * 26 + 4)
        self.popup_list.setGeometry(pos.x(), pos.y() + 2, self.width(), height)
        self.popup_list.show()

    def keyPressEvent(self, event):
        """Обработка навигации (Вверх/Вниз/Enter/Tab/Esc) и реакция на ввод текста."""
        if self.popup_list.isVisible():
            if event.key() == Qt.Key_Down:
                next_row = (self.popup_list.currentRow() + 1) % self.popup_list.count()
                self.popup_list.setCurrentRow(next_row)
                return
            elif event.key() == Qt.Key_Up:
                prev_row = (self.popup_list.currentRow() - 1 + self.popup_list.count()) % self.popup_list.count()
                self.popup_list.setCurrentRow(prev_row)
                return
            elif event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Tab):
                current_item = self.popup_list.currentItem() or self.popup_list.item(0)
                if current_item:
                    self.insert_completion(current_item.text())
                    event.accept()
                return
            elif event.key() == Qt.Key_Escape:
                self.popup_list.hide()
                event.accept()
                return

        # Передача ввода в стандартный QLineEdit
        super().keyPressEvent(event)
        full_text = self.text()

        # Реакция на удаление символов (Backspace / Delete)
        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete) or not full_text:
            current_word = full_text.split(",")[-1].strip() if full_text else ""
            if len(current_word) < 2:
                self.popup_list.hide()
                return
            self.show_suggestions(current_word)
            return

        # Гасим список, если строка завершилась разделителем
        if full_text.endswith(", ") or full_text.endswith(","):
            self.popup_list.hide()
            return

        # Проверка длины текущего слова (подсказки выводятся от 2-х символов)
        current_word = full_text.split(",")[-1].strip()
        if len(current_word) >= 2:
            self.show_suggestions(current_word)
        else:
            self.popup_list.hide()

    def hide_popup(self):
        """Принудительное закрытие выпадающего окна подсказок."""
        if hasattr(self, 'popup_list') and self.popup_list.isVisible():
            self.popup_list.hide()

    def focusInEvent(self, event):
        """Автоматическое выкатывание подсказок при возврате фокуса мыши в поле ввода."""
        super().focusInEvent(event)
        full_text = self.text().strip()
        current_word = full_text.split(",")[-1].strip() if full_text else ""
        if len(current_word) >= 2:
            self.show_suggestions(current_word)
        else:
            self.popup_list.hide()
