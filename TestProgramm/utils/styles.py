def get_application_style():
    """Полная QSS-таблица стилей корпоративного интерфейса админ-панели."""
    return """
        /* ================================================================= */
        /*   НАСТРОЕК СТИЛЯ ОКНА АВТОРИЗАЦИИ (ЛОГИНА) И ЕГО КОМПОНЕНТОВ       */
        /* ================================================================= */
        QDialog {
            background-color: #FFFFFF; /* Весь фон окна авторизации теперь строго белый */
        }

        /* Красивые скругленные карточки-подложки для блоков полей */
        QDialog QGroupBox {
            background-color: #FFFFFF;
            border: 1px solid #D5DBDB; /* Тонкая аккуратная серая обводочка вокруг всего блока */
            border-radius: 6px;        /* Красивое мягкое скругление углов */
            margin-top: 5px;
        }

        /* ИСПРАВЛЕНО СТРОГО: Отключаем рамки ТОЛЬКО у конкретных слов по их имени объекта,
           чтобы большие общие рамки карточек QGroupBox вернулись на экран и не ломались */
        QLabel#login_title_label {
            border: none !important;
            background-color: #FFFFFF !important;
        }

        /* Поля ввода внутри окна авторизации */
        QDialog QLineEdit {
            border: 1px solid #BDC3C7;
            border-radius: 4px;
            padding: 5px 8px;
            font-size: 13px;
            background-color: #FFFFFF;
            color: #000000;
        }
        QDialog QLineEdit:focus {
            border: 1px solid #2980B9; /* Синий фокус при вводе пароля */
            background-color: #FFFFFF;
        }

        QMainWindow, QWidget {
            background-color: #F4F6F7;
        }

        /* Панель вкладок */
        QTabWidget::pane {
            border: 1px solid #D5DBDB;
            background-color: white;
            border-radius: 6px;
            position: absolute;
            top: -1px;
        }
        QTabBar::tab {
            background: #EAEDED;
            color: #2C3E50;
            padding: 6px 8px;
            border: 1px solid #D5DBDB;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            font-size: 11px;
            font-weight: bold;
        }
        QTabBar::tab:selected {
            background: white;
            border-bottom: 2px solid white;
            color: #2980B9;
        }
        QTabBar::tab:hover {
            background: #F2F4F4;
        }

        /* Группы контейнеров */
        QGroupBox {
            font-weight: bold;
            color: #2C3E50;
            border: 1px solid #D5DBDB;
            border-radius: 6px;
            margin-top: 15px;
            padding-top: 20px;
            font-size: 13px;
            background-color: #FDFEFE;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 15px;
            padding: 0 8px;
            background-color: #F4F6F7;
            border-radius: 3px;
        }

        /* Точечный отступ для надписей внутри групп */
        QGroupBox QLabel {
            color: #000000;
            padding-left: 10px;
        }

        /* Поля ввода текста */
        QLineEdit {
            border: 1px solid #BDC3C7;
            border-radius: 4px;
            padding: 6px 10px;
            font-size: 13px;
            background-color: white;
            color: #000000;
        }
        QLineEdit:focus {
            border: 1px solid #2980B9;
            background-color: #F7F9F9;
            color: #000000;
        }

        /* Чекбоксы на теле вкладок и в окне авторизации */
        QCheckBox {
            font-size: 13px;
            color: #000000;
            spacing: 8px;
        }

        /* НАСТРОЙКА КОМБОБОКСОВ ДЛЯ СТАБИЛЬНОЙ КОНТРАСТНОЙ СТРЕЛОЧКИ */
        QComboBox {
            border: 1px solid #BDC3C7;
            border-radius: 4px;
            padding: 6px 10px;
            font-size: 13px;
            background: white;
            /* Позволяем операционной системе самой управлять цветом текста и стрелки,
               чтобы она сразу использовала контрастную системную текстуру уголка */
        }
        QComboBox:focus {
            border: 1px solid #2980B9;
        }

        /* Выпадающий список комбобокса (мягкое серое выделение) */
        QComboBox QAbstractItemView {
            border: 1px solid #BDC3C7;
            background-color: white;
            selection-background-color: #E5E8E8;
            selection-color: #000000;
            color: #000000;
        }

        /* Кнопки действия (Установка, Запуск и т.д.) */
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

        /* Глубокий терминал логов (черный фон / зеленый шрифт) */
        QTextEdit {
            background-color: #1E1E1E;
            color: #00FF00;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 13px;
            border: 1px solid #333333;
            border-radius: 4px;
            padding: 8px;
        }

        /* Всплывающие списки подсказок автокомплита и чек-листы */
        QListWidget {
            border: 1px solid #BDC3C7;
            background-color: white;
            font-size: 13px;
            color: #000000;
        }
        QListWidget::item {
            padding: 6px 10px;
            background-color: transparent;
            color: #000000;
        }
        QListWidget::item:hover {
            background-color: transparent;
        }
        QListWidget::item:selected {
            background-color: #E5E8E8;
            color: #000000;
        }

        /* КВАДРАТИКИ ЧЕКБОКСОВ С ЛИНЕЙНЫМ ГРАДИЕНТОМ КВЕРХУ */
        QListWidget::indicator {
            border: 1px solid #BDC3C7;
            border-radius: 3px;
            width: 14px;
            height: 14px;
        }
        /* В выключенном состоянии — просто чисто белый квадрат */
        QListWidget::indicator:unchecked {
            background-color: white;
            border-color: #BDC3C7;
        }
        QListWidget::indicator:unchecked:hover {
            background-color: white;
            border-color: #2980B9;
        }
        /* Во включенном состоянии — синий квадрат с мягким градиентом, светлеющим кверху */
        QListWidget::indicator:checked {
            background-color: qlineargradient(x1: 0, y1: 1, x2: 0, y2: 0, stop: 0 #2980B9, stop: 1 #5DADE2);
            border-color: #1F618D;
            image: url(none); /* Глушим системную галочку, оставляя только синий кубик */
        }
        /* При наведении на активный чекбокс — градиент становится чуть темнее */
        QListWidget::indicator:checked:hover {
            background-color: qlineargradient(x1: 0, y1: 1, x2: 0, y2: 0, stop: 0 #2471A3, stop: 1 #4894C4);
            border-color: #1F618D;
        }

                /* КРАСИВАЯ СТИЛИЗАЦИЯ ПОЛОСЫ ПРОКРУТКИ ДЛЯ ВСЕХ ТАБЛИЦ И СПИСКОВ */
        QScrollBar:vertical {
            border: none;
            background-color: #F4F6F7; /* Цвет подложки скроллбара под фон окна */
            width: 10px;               /* Делаем полосу тонкой и аккуратной */
            margin: 0px 0px 0px 0px;
        }

        /* Ползунок, за который мы тащим мышкой */
        QScrollBar::handle:vertical {
            background-color: #BDC3C7; /* Приглушенный серый цвет ползунка */
            min-height: 20px;
            border-radius: 5px;        /* Округляем края ползунка, чтобы убрать топорность */
        }

        /* Цвет ползунка при наведении мыши */
        QScrollBar::handle:vertical:hover {
            background-color: #95A5A6; /* Чуть темнее при наведении */
        }

        /* Убираем позорные стрелочки сверху и снизу скроллбара */
        QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical {
            border: none;
            background: none;
            width: 0px;
            height: 0px;
        }
        QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
            background: none;
            width: 0px;
            height: 0px;
        }

        /* Настройка зоны трека (пустого пространства, по которому бегает ползунок) */
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }

    """
