import subprocess
import os
from PyQt5.QtCore import QMetaObject, Q_ARG, Qt
from PyQt5.QtWidgets import QWidget

def execute_command_stream_util(main_win, cmd, terminal_box, action_button, status_label, env=None):
    """Универсальный сквозной движок асинхронного выполнения команд Ansible и вывода логов."""

    # Сразу блокируем кнопку в начале запуска
    if action_button:
        QMetaObject.invokeMethod(action_button, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, False))

    process = None
    try:
        QMetaObject.invokeMethod(terminal_box, "append", Qt.QueuedConnection, Q_ARG(str, "[СИСТЕМА]: Запуск процесса автоматизации Ansible по сети...\n"))

        current_env = env if env is not None else os.environ.copy()

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=current_env,
            bufsize=1
        )

        # Регистрируем процесс в пуле для защиты от зомби-потоков
        if hasattr(main_win, 'active_processes'):
            main_win.active_processes.append(process)

        # Читаем вывод в реальном времени построчно
        for line in process.stdout:
            # ИСПРАВЛЕНО: rstrip("\n") вместо strip(), чтобы сохранять отступы логов Ansible
            clean_line = line.rstrip("\n")
            QMetaObject.invokeMethod(terminal_box, "append", Qt.QueuedConnection, Q_ARG(str, clean_line))

        process.wait()

        # Удаляем из пула по завершении
        if hasattr(main_win, 'active_processes') and process in main_win.active_processes:
            main_win.active_processes.remove(process)

        # Корректно обрабатываем коды возврата (0 — успех, 4 — часть ПК недоступна)
        if process.returncode in (0, 4):
            status_text = "Успех!" if process.returncode == 0 else "Выполнено (часть ПК недоступна)"
            status_color = "color: #27ae60; font-weight: bold;" if process.returncode == 0 else "color: #e67e22; font-weight: bold;"

            QMetaObject.invokeMethod(status_label, "setText", Qt.QueuedConnection, Q_ARG(str, status_text))
            QMetaObject.invokeMethod(status_label, "setStyleSheet", Qt.QueuedConnection, Q_ARG(str, status_color))
        else:
            QMetaObject.invokeMethod(status_label, "setText", Qt.QueuedConnection, Q_ARG(str, f"Ошибка (Код {process.returncode})"))
            QMetaObject.invokeMethod(status_label, "setStyleSheet", Qt.QueuedConnection, Q_ARG(str, "color: #c0392b; font-weight: bold;"))

            QMetaObject.invokeMethod(terminal_box, "append", Qt.QueuedConnection, Q_ARG(str, f"\n[ВНИМАНИЕ]: Процесс завершился с ошибкой {process.returncode}."))

    except Exception as e:
        QMetaObject.invokeMethod(terminal_box, "append", Qt.QueuedConnection, Q_ARG(str, f"\n[КРИТИЧЕСКАЯ ОШИБКА ДВИЖКА]: {e}"))
        if status_label:
            QMetaObject.invokeMethod(status_label, "setText", Qt.QueuedConnection, Q_ARG(str, "Критическая ошибка запуска"))
            QMetaObject.invokeMethod(status_label, "setStyleSheet", Qt.QueuedConnection, Q_ARG(str, "color: #c0392b; font-weight: bold;"))

    finally:
        # 1. Сначала принудительно возвращаем кнопку в активное состояние в GUI-потоке
        if action_button:
            QMetaObject.invokeMethod(action_button, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, True))

        # 2. Затем безопасно пытаемся сохранить историю логов
        if hasattr(main_win, '_safe_finalize_ui'):
            try:
                # Определяем тип операции на основе переданного терминала логов
                if hasattr(main_win, 'tab_scripts') and terminal_box == main_win.tab_scripts.script_terminal_box:
                    op_type, nodes = "ЗАПУСК СКРИПТА", main_win.tab_scripts.script_ip_entry.text()
                elif hasattr(main_win, 'tab_commands') and terminal_box == main_win.tab_commands.command_terminal_box:
                    op_type, nodes = "ВЫПОЛНЕНИЕ КОМАНДЫ", main_win.tab_commands.command_ip_entry.text()
                else:
                    op_type = "УСТАНОВКА ПО"
                    nodes = main_win.tab_packages.ip_entry.text() if hasattr(main_win, 'tab_packages') else "Неизвестно"

                # Вызываем метод сохранения лога истории
                main_win.save_to_log_file(op_type, nodes, terminal_box.toPlainText())
            except Exception as e:
                print(f"[Дебаг движка]: Ошибка сохранения логов в истории: {e}")
