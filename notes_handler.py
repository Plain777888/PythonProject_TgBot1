from idlelib.window import register_callback

import telebot

from telebot import types
import json
import os
import tempfile
from datetime import datetime
from config import (
    BOT_TOKEN, bot_logger, OPEN_METEO_URL, MOSCOW_COORDS,
    safe_log_user_info
)

from database import Database
import logging
from keyboards import create_main_keyboard, create_hide_keyboard

# Настройка логгера
logger = logging.getLogger('telegram_bot.notes')


def create_main_keyboard(self):
    """Создание основной клавиатуры бота"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        types.KeyboardButton("❓ О боте"),
        types.KeyboardButton("☀️ Погода Москва"),
        types.KeyboardButton("🤝 Помощь"),
        types.KeyboardButton("📝 Заметки"),
        types.KeyboardButton("🪄 Эхо команда"),
        types.KeyboardButton("⬇️ Скрыть клавиатуру")
    ]
    markup.add(*buttons)
    return markup
def escape_markdown(text):
    """Экранирование специальных символов Markdown"""
    if not text:
        return text

    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, '\\' + char)
    return text

class NotesHandler:
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        self.user_states = {}  # Для хранения состояний пользователей

        # Определения состояний
        self.STATE_ADD_NOTE_TITLE = "add_note_title"
        self.STATE_ADD_NOTE_CONTENT = "add_note_content"
        self.STATE_EDIT_NOTE_ID = "edit_note_id"
        self.STATE_EDIT_NOTE_FIELD = "edit_note_field"
        self.STATE_DELETE_NOTE_ID = "delete_note_id"
        self.STATE_SEARCH_NOTES = "search_notes"



    # def handle_note_list(self, message):
    #     """Обработка списка заметок"""
    #     user_id = message.from_user.id
    #     notes = self.db.get_user_notes(user_id, limit=10)
    #
    #     if not notes:
    #         self.bot.send_message(
    #             message.chat.id,
    #             "📭 У вас пока нет заметок."
    #         )
    #         return
    #
    #     response = "📋 *Ваши заметки:*\n\n"
    #     for i, note in enumerate(notes, 1):
    #         response += f"{i}. {note['title'][:30]}\n"
    #
    #     self.bot.send_message(
    #         message.chat.id,
    #         response,
    #         parse_mode='Markdown'
    #     )
    #
    # def handle_note_find(self, message):
    #     """Обработка поиска заметок"""
    #     self.bot.send_message(
    #         message.chat.id,
    #         "🔍 Поиск заметок...\n"
    #         "Введите текст для поиска:"
    #     )
    #
    # def handle_note_count(self, message):
    #     """Обработка подсчета заметок"""
    #     user_id = message.from_user.id
    #     count = self.db.get_notes_count(user_id)
    #
    #     self.bot.send_message(
    #         message.chat.id,
    #         f"📊 У вас {count} заметок"
    #     )
    #
    # def handle_note_export(self, message):
    #     """Обработка экспорта заметок"""
    #     self.bot.send_message(
    #         message.chat.id,
    #         "📁 Экспорт заметок (в разработке)"
    #     )
    def set_database(self, db):
        """Установка объекта базы данных"""
        self.db = db

    def handle_note_list1(self,message):
        """Показ списка заметок"""
        if not self.db:
            self.bot.send_message(message.chat.id, "❌ База данных не инициализирована")
            return
        user_id = message.from_user.id
        logger.info(f"NOTE_LIST запрошен: user_id={user_id}")

        notes = self.db.get_user_notes(user_id, limit=20)

        if not notes:
            self.bot.send_message(
                message.chat.id,
                "📭 У вас пока нет заметок.\n"
                "Добавьте первую заметку командой /note_add"
            )
            return

        response = "📋 *Ваши заметки:*\n\n"

        for i, note in enumerate(notes[:10], 1):  # Показываем первые 10

            created = datetime.strptime(note['created_at'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
            preview = note['content'][:50] + "..." if len(note['content']) > 50 else note['content']

            response += f"*{i}. {note['title']}*\n"
            response += f"   📅 {created} | 📁 {note['category']}\n"
            response += f"   {preview}\n"
            response += f"   ID: `{note['id']}`\n\n"

        if len(notes) > 10:
            response += f"*... и еще {len(notes) - 10} заметок*\n"

        response += "\nИспользуйте /note_find для поиска или /note_del для удаления"

        # Создаем inline-клавиатуру для навигации
        markup = types.InlineKeyboardMarkup(row_width=3)
        buttons = [
            types.InlineKeyboardButton("📥 Экспорт", callback_data="notes_export"),
            types.InlineKeyboardButton("🔍 Поиск", callback_data="notes_search"),
            types.InlineKeyboardButton("📊 Статистика", callback_data="notes_stats"),
            types.InlineKeyboardButton("📌 Закрепить", callback_data="notes_pin_menu"),
            types.InlineKeyboardButton("🗑 Удалить", callback_data="notes_delete_menu"),
            types.InlineKeyboardButton("➕ Новая", callback_data="notes_add_new")
        ]
        markup.add(*buttons)

        self.bot.send_message(
            message.chat.id,
            response
        )


    def handle_note_add1(self,message):
        """Начало добавления заметки"""

        if not self.db:
            self.bot.send_message(message.chat.id, "❌ База данных не инициализирована")
            return
        user_info = f"user_id={message.from_user.id}, username={message.from_user.username}"
        logger.info(f"NOTE_ADD начато: {user_info}")

        # Добавляем/обновляем пользователя в БД
        self.db.add_or_update_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name
        )

        self.user_states[message.from_user.id] = self.STATE_ADD_NOTE_TITLE

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(
            types.KeyboardButton("📝 Пример заголовка"),
            types.KeyboardButton("❌ Отмена")
        )

        self.bot.send_message(
            message.chat.id,
            "📝 *Добавление новой заметки*\n\n"
            "Шаг 1/2: Введите *заголовок* заметки:\n"
            "(не более 100 символов)\n\n"
            "Или используйте кнопки ниже:",
            reply_markup=markup
        )

    def handle_note_find1(self,message):
        """Поиск заметок"""
        if not self.db:
            self.bot.send_message(message.chat.id, "❌ База данных не инициализирована")
            return
        user_id = message.from_user.id
        logger.info(f"NOTE_FIND начат: user_id={user_id}")

        # Проверяем аргументы команды
        args = message.text.split(maxsplit=1)


        # Запрашиваем поисковый запрос
        self.user_states[user_id] = self.STATE_SEARCH_NOTES

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(
                types.KeyboardButton("🔙 Назад к заметкам"),
                types.KeyboardButton("❌ Отмена")
            )

        self.bot.send_message(
                message.chat.id,
                "🔍 *Поиск заметок*\n\n"
                "Введите текст для поиска:\n"
                "• Поиск ведется по заголовкам и содержанию\n"
                "• Можно искать по нескольким словам\n"
                "• Для точного поиска используйте кавычки\n\n"
                "Пример: `важная встреча`"
            )

    def handle_note_count1(self,message):
        """Показать количество заметок"""
        user_id = message.from_user.id
        logger.info(f"NOTE_COUNT запрошен: user_id={user_id}")

        total_count = self.db.get_notes_count(user_id)

        response = f"📊 *Статистика заметок*\n\n"
        response += f"Всего заметок: *{total_count}*\n\n"

        if total_count == 0:
            response += "\n📝 Добавьте первую заметку командой /note_add"
        else:
            response += f"\n📋 Показать все заметки: /note_list"
            response += f"\n🔍 Поиск по заметкам: /note_find"

        self.bot.send_message(
            message.chat.id,
            response

        )


    def handle_note_export1(self,message):
        """Экспорт заметок в файл"""
        user_id = message.from_user.id
        logger.info(f"NOTE_EXPORT запрошен: user_id={user_id}")

        notes = self.db.get_all_user_notes(user_id)

        if not notes:
            self.bot.send_message(
                message.chat.id,
                "📭 Нет заметок для экспорта."
            )
            return

        # Создаем временный файл
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                         suffix='.txt', delete=False) as f:
            f.write(f"Экспорт заметок пользователя @{message.from_user.username or 'unknown'}\n")
            f.write(f"Дата экспорта: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")

            for note in notes:
                f.write(f"ЗАМЕТКА #{note['id']}\n")
                f.write(f"Заголовок: {note['title']}\n")
                f.write(f"Категория: {note['category']}\n")
                f.write(f"Создана: {note['created_at']}\n")
                f.write(f"Обновлена: {note['updated_at']}\n")

                tags = json.loads(note['tags']) if note['tags'] else []
                if tags:
                    f.write(f"Теги: {', '.join(tags)}\n")

                f.write("\nСодержание:\n")
                f.write(note['content'])
                f.write("\n" + "=" * 50 + "\n\n")

            temp_file = f.name

        try:
            # Отправляем файл пользователю
            with open(temp_file, 'rb') as file:
                self.bot.send_document(
                    message.chat.id,
                    file,
                    caption=f"📁 Экспорт заметок\nВсего заметок: {len(notes)}"
                )

            logger.info(f"NOTE_EXPORT выполнен: user_id={user_id}, notes={len(notes)}")

        except Exception as e:
            logger.error(f"Ошибка отправки файла: {e}")
            self.bot.send_message(
                message.chat.id,
                "❌ Ошибка при создании файла экспорта."
            )
        finally:
            # Удаляем временный файл
            try:
                os.unlink(temp_file)
            except:
                pass

    def handle_notes_button(self,message):
        """Обработка кнопки 'Заметки'"""
        user_info = safe_log_user_info(
            message.from_user.id,
            message.from_user.username,
            'button_notes',
            message.text
        )
        bot_logger.info(f"BUTTON_NOTES: {user_info}")

        # Показываем меню заметок с правильной клавиатурой
        markup = self.create_main_notes_keyboard()  # Используем существующий handler

        self.bot.send_message(
            message.chat.id,
            "📝 *Менеджер заметок*\n\n"
            "Выберите действие:\n"
            "• 📝 Новая заметка - добавить заметку\n"
            "• 📋 Список заметок - просмотреть все\n"
            "• 🔍 Поиск заметок - найти по тексту\n"
            "• 📊 Статистика - количество заметок\n"
            "• 📁 Экспорт заметок - скачать файл\n\n"
            "Или используйте команды:\n"
            "/note_add - добавить заметку\n"
            "/note_list - список заметок\n"
            "/note_find - поиск заметок\n"
            "/note_count - статистика",
            reply_markup=markup

        )
    def register_reply_handlers(self):
        """Регистрация обработчиков reply-кнопок заметок"""



        @self.bot.message_handler(func=lambda message: message.text == "🔙 Главное меню")
        def handle_back_to_main_button(message):
            """Обработка кнопки 'Главное меню'"""
            self.bot.send_message(
                message.chat.id,
                "🔙 Возвращаюсь в главное меню...",
                reply_markup=create_main_keyboard()  # Функция из bot.py
            )

    def register_handlers(self):
        """Регистрация обработчиков команд заметок"""

        @self.bot.message_handler(commands=['note_add',"📝 Новая заметка"])
        def handle_note_add(message):
            """Начало добавления заметки"""

            if not self.db:
                self.bot.send_message(message.chat.id, "❌ База данных не инициализирована")
                return
            user_info = f"user_id={message.from_user.id}, username={message.from_user.username}"
            logger.info(f"NOTE_ADD начато: {user_info}")

            # Добавляем/обновляем пользователя в БД
            self.db.add_or_update_user(
                message.from_user.id,
                message.from_user.username,
                message.from_user.first_name,
                message.from_user.last_name
            )

            self.user_states[message.from_user.id] = self.STATE_ADD_NOTE_TITLE

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(
                types.KeyboardButton("📝 Пример заголовка"),
                types.KeyboardButton("❌ Отмена")
            )

            self.bot.send_message(
                message.chat.id,
                "📝 *Добавление новой заметки*\n\n"
                "Шаг 1/2: Введите *заголовок* заметки:\n"
                "(не более 100 символов)\n\n"
                "Или используйте кнопки ниже:"
            )

        @self.bot.message_handler(commands=['note_list', '📋 Список заметок'])
        def handle_note_list(message):
            """Показ списка заметок"""
            if not self.db:
                self.bot.send_message(message.chat.id, "❌ База данных не инициализирована")
                return
            user_id = message.from_user.id
            logger.info(f"NOTE_LIST запрошен: user_id={user_id}")

            notes = self.db.get_user_notes(user_id, limit=20)

            if not notes:
                self.bot.send_message(
                    message.chat.id,
                    "📭 У вас пока нет заметок.\n"
                    "Добавьте первую заметку командой /note_add"
                )
                return

            response = "📋 *Ваши заметки:*\n\n"

            for i, note in enumerate(notes[:10], 1):  # Показываем первые 10

                created = datetime.strptime(note['created_at'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
                preview = note['content'][:50] + "..." if len(note['content']) > 50 else note['content']

                response += f"*{i}. {note['title']}*\n"
                response += f"   📅 {created} | 📁 {note['category']}\n"
                response += f"   {preview}\n"
                response += f"   ID: `{note['id']}`\n\n"

            if len(notes) > 10:
                response += f"*... и еще {len(notes) - 10} заметок*\n"

            response += "\nИспользуйте /note_find для поиска или /note_del для удаления заметок."

            # Создаем inline-клавиатуру для навигации
            markup = types.InlineKeyboardMarkup(row_width=3)
            buttons = [
                types.InlineKeyboardButton("📥 Экспорт", callback_data="notes_export"),
                types.InlineKeyboardButton("🔍 Поиск", callback_data="notes_search"),
                types.InlineKeyboardButton("📊 Статистика", callback_data="notes_stats"),
                types.InlineKeyboardButton("📌 Закрепить", callback_data="notes_pin_menu"),
                types.InlineKeyboardButton("🗑 Удалить", callback_data="notes_delete_menu"),
                types.InlineKeyboardButton("➕ Новая", callback_data="notes_add_new")
            ]
            markup.add(*buttons)

            self.bot.send_message(
                message.chat.id,
                response
            )

        @self.bot.message_handler(commands=['note_find', '🔍 Поиск заметок'])
        def handle_note_find(message):
            """Поиск заметок"""
            if not self.db:
                self.bot.send_message(message.chat.id, "❌ База данных не инициализирована")
                return
            user_id = message.from_user.id
            logger.info(f"NOTE_FIND начат: user_id={user_id}")

            # Проверяем аргументы команды
            args = message.text.split(maxsplit=1)

            if len(args) > 1:
                # Если поисковый запрос указан сразу
                search_text = args[1]
                self.perform_note_search(message, search_text)
            else:
                # Запрашиваем поисковый запрос
                self.user_states[user_id] = self.STATE_SEARCH_NOTES

                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.add(
                    types.KeyboardButton("🔙 Назад к заметкам"),
                    types.KeyboardButton("❌ Отмена")
                )

                self.bot.send_message(
                    message.chat.id,
                    "🔍 *Поиск заметок*\n\n"
                    "Введите текст для поиска:\n"
                    "• Поиск ведется по заголовкам и содержанию\n"
                    "• Можно искать по нескольким словам\n"
                    "• Для точного поиска используйте кавычки\n\n"
                    "Пример: `важная встреча`"
                )

        @self.bot.message_handler(commands=['note_edit', 'note_edit@TAU_Lab_Bot'])
        def handle_note_edit(message):
            """Редактирование заметки"""
            user_id = message.from_user.id
            logger.info(f"NOTE_EDIT начат: user_id={user_id}")

            args = message.text.split()

            if len(args) > 1:
                # Если ID указан сразу
                try:
                    note_id = int(args[1])
                    self.show_note_for_edit(message, note_id)
                except ValueError:
                    self.bot.send_message(
                        message.chat.id,
                        "❌ Неверный формат ID. Используйте: /note_edit <ID_заметки>"
                    )
            else:
                # Запрашиваем ID
                self.user_states[user_id] = self.STATE_EDIT_NOTE_ID

                self.bot.send_message(
                    message.chat.id,
                    "✏️ *Редактирование заметки*\n\n"
                    "Введите ID заметки для редактирования.\n"
                    "ID можно узнать командой /note_list\n\n"
                    "Или введите `отмена` для выхода."

                )

        @self.bot.message_handler(commands=['note_del', 'note_del@TAU_Lab_Bot'])
        def handle_note_del(message):
            """Удаление заметки"""
            user_id = message.from_user.id
            logger.info(f"NOTE_DEL начат: user_id={user_id}")

            args = message.text.split()

            if len(args) > 1:
                # Если ID указан сразу
                try:
                    note_id = int(args[1])
                    self.confirm_note_delete(message, note_id)
                except ValueError:
                    self.bot.send_message(
                        message.chat.id,
                        "❌ Неверный формат ID. Используйте: /note_del <ID_заметки>"
                    )
            else:
                # Запрашиваем ID
                self.user_states[user_id] = self.STATE_DELETE_NOTE_ID

                self.bot.send_message(
                    message.chat.id,
                    "🗑 *Удаление заметки*\n\n"
                    "Введите ID заметки для удаления.\n"
                    "ID можно узнать командой /note_list\n\n"
                    "Или введите `отмена` для выхода."

                )

        @self.bot.message_handler(commands=['note_count', '📊 Статистика'])
        def handle_note_count(message):
            """Показать количество заметок"""
            user_id = message.from_user.id
            logger.info(f"NOTE_COUNT запрошен: user_id={user_id}")

            total_count = self.db.get_notes_count(user_id)




            response = f"📊 *Статистика заметок*\n\n"
            response += f"Всего заметок: *{total_count}*\n\n"





            if total_count == 0:
                response += "\n📝 Добавьте первую заметку командой /note_add"
            else:
                response += f"\n📋 Показать все заметки: /note_list"
                response += f"\n🔍 Поиск по заметкам: /note_find"

            self.bot.send_message(
                message.chat.id,
                response

            )

        @self.bot.message_handler(commands=['note_export', '📁 Экспорт заметок'])
        def handle_note_export(message):
            """Экспорт заметок в файл"""
            user_id = message.from_user.id
            logger.info(f"NOTE_EXPORT запрошен: user_id={user_id}")

            notes = self.db.get_all_user_notes(user_id)

            if not notes:
                self.bot.send_message(
                    message.chat.id,
                    "📭 Нет заметок для экспорта."
                )
                return

            # Создаем временный файл
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                             suffix='.txt', delete=False) as f:
                f.write(f"Экспорт заметок пользователя @{message.from_user.username or 'unknown'}\n")
                f.write(f"Дата экспорта: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")

                for note in notes:
                    f.write(f"ЗАМЕТКА #{note['id']}\n")
                    f.write(f"Заголовок: {note['title']}\n")
                    f.write(f"Категория: {note['category']}\n")
                    f.write(f"Создана: {note['created_at']}\n")
                    f.write(f"Обновлена: {note['updated_at']}\n")

                    tags = json.loads(note['tags']) if note['tags'] else []
                    if tags:
                        f.write(f"Теги: {', '.join(tags)}\n")

                    f.write("\nСодержание:\n")
                    f.write(note['content'])
                    f.write("\n" + "=" * 50 + "\n\n")

                temp_file = f.name

            try:
                # Отправляем файл пользователю
                with open(temp_file, 'rb') as file:
                    self.bot.send_document(
                        message.chat.id,
                        file,
                        caption=f"📁 Экспорт заметок\nВсего заметок: {len(notes)}"
                    )

                logger.info(f"NOTE_EXPORT выполнен: user_id={user_id}, notes={len(notes)}")

            except Exception as e:
                logger.error(f"Ошибка отправки файла: {e}")
                self.bot.send_message(
                    message.chat.id,
                    "❌ Ошибка при создании файла экспорта."
                )
            finally:
                # Удаляем временный файл
                try:
                    os.unlink(temp_file)
                except:
                    pass

        @self.bot.message_handler(func=lambda message:
        message.from_user.id in self.user_states and
        self.user_states[message.from_user.id] == self.STATE_ADD_NOTE_TITLE)
        def handle_note_title_input(message):
            """Обработка ввода заголовка заметки"""
            user_id = message.from_user.id

            if message.text == "❌ Отмена":
                self.cancel_note_creation(message)
                return

            # types.KeyboardButton("🏷 Добавить теги"),
            # types.KeyboardButton("📁 Выбрать категорию"),
            # types.KeyboardButton("❌ Отмена")


            if message.text == "📝 Пример заголовка":
                title = "Моя первая заметка"

            else:
                title = message.text.strip()

                if len(title) > 100:
                    self.bot.send_message(
                        message.chat.id,
                        "❌ Заголовок слишком длинный (макс. 100 символов). Попробуйте снова:"
                    )
                    return

            # Сохраняем заголовок и переходим к содержанию
            self.user_states[user_id] = {
                'state': self.STATE_ADD_NOTE_CONTENT,
                'temp_data': {'title': title}
            }

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(
                types.KeyboardButton("📝 Пример содержания"),
                # types.KeyboardButton("🏷 Добавить теги"),
                # types.KeyboardButton("📁 Выбрать категорию"),
                types.KeyboardButton("❌ Отмена")
            )

            self.bot.send_message(
                message.chat.id,
                f"📝 *Заголовок сохранен:* {title}\n\n"
                "Шаг 2/2: Введите *содержание* заметки:\n"
                "(не более 4000 символов)\n\n"
                "Или используйте кнопки ниже:",
                reply_markup=markup

            )

        @self.bot.message_handler(func=lambda message:
        message.from_user.id in self.user_states and
        isinstance(self.user_states[message.from_user.id], dict) and
        self.user_states[message.from_user.id].get('state') == self.STATE_ADD_NOTE_CONTENT)
        def handle_note_content_input(message):
            """Обработка ввода содержания заметки"""
            user_id = message.from_user.id
            temp_data = self.user_states[user_id]['temp_data']

            if message.text == "❌ Отмена":
                self.cancel_note_creation(message)
                return

            if message.text == "📝 Пример содержания":
                content = "Это пример содержания заметки. Здесь можно писать текст, идеи, задачи и т.д."
            # elif message.text == "🏷 Добавить теги":
            #     # Здесь можно реализовать добавление тегов
            #     self.bot.send_message(
            #         message.chat.id,
            #         "Введите теги через запятую (например: работа, важно, проект):"
            #     )
            #     # Продолжаем ожидать содержание
            #     return

            else:
                content = message.text.strip()

                if len(content) > 4000:
                    self.bot.send_message(
                        message.chat.id,
                        "❌ Содержание слишком длинное (макс. 4000 символов). Попробуйте снова:"
                    )
                    return

            # Добавляем заметку в БД
            note_id = self.db.add_note(
                user_id=user_id,
                title=temp_data['title'],
                content=content,
                category=temp_data.get('category', 'general'),
                tags=temp_data.get('tags')
            )

            if note_id:
                # Очищаем состояние
                del self.user_states[user_id]

                response = (
                    f"✅ *Заметка добавлена!*\n\n"
                    f"*Заголовок:* {temp_data['title']}\n"
                    f"*ID заметки:* `{note_id}`\n"
                    f"*Категория:* {temp_data.get('category', 'общее')}\n\n"
                    f"Просмотреть: /note_list\n"
                    f"Редактировать: /note_edit {note_id}"
                )

                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("📋 Меню заметок", callback_data="notes_list"),
                    #types.InlineKeyboardButton("➕ Новая заметка", callback_data="notes_add_new")
                )
                markup2 = types.ReplyKeyboardRemove()
                # markup2.add(
                #     types.KeyboardButton("📋 Меню заметок"),
                #     types.KeyboardButton("➕ Новая заметка")
                # )
                self.bot.send_message(
                    message.chat.id,
                    "Отлично!",
                    reply_markup=markup2

                )
                self.bot.send_message(
                    message.chat.id,
                    response,
                    reply_markup=markup

                )


                logger.info(f"NOTE_ADD завершен: user_id={user_id}, note_id={note_id}")
            else:
                self.bot.send_message(
                    message.chat.id,
                    "❌ Ошибка при сохранении заметки. Попробуйте снова."
                )

        # Обработчики других состояний
        @self.bot.message_handler(func=lambda message:
        message.from_user.id in self.user_states and
        self.user_states[message.from_user.id] == self.STATE_EDIT_NOTE_ID)
        def handle_edit_note_id_input(message):
            """Обработка ввода ID для редактирования"""
            user_id = message.from_user.id

            if message.text.lower() in ['отмена', 'cancel', '❌ отмена']:
                self.cancel_operation(message)
                return

            try:
                note_id = int(message.text.strip())
                self.show_note_for_edit(message, note_id)
            except ValueError:
                self.bot.send_message(
                    message.chat.id,
                    "❌ Неверный формат ID. Введите числовой ID или 'отмена':"
                )

        @self.bot.message_handler(func=lambda message:
        message.from_user.id in self.user_states and
        self.user_states[message.from_user.id] == self.STATE_DELETE_NOTE_ID)
        def handle_delete_note_id_input(message):
            """Обработка ввода ID для удаления"""
            user_id = message.from_user.id

            if message.text.lower() in ['отмена', 'cancel', '❌ отмена']:
                self.cancel_operation(message)
                return

            try:
                note_id = int(message.text.strip())
                self.confirm_note_delete(message, note_id)
            except ValueError:
                self.bot.send_message(
                    message.chat.id,
                    "❌ Неверный формат ID. Введите числовой ID или 'отмена':"
                )

        @self.bot.message_handler(func=lambda message:
        message.from_user.id in self.user_states and
        self.user_states[message.from_user.id] == self.STATE_SEARCH_NOTES)
        def handle_search_input(message):
            """Обработка поискового запроса"""
            user_id = message.from_user.id

            if message.text == "🔙 Назад к заметкам":
                self.cancel_operation(message)
                self.bot.send_message(
                    message.chat.id,
                    "Возвращаемся к списку заметок..."
                )
                handle_note_list(message)
                return

            if message.text == "❌ Отмена":
                self.cancel_operation(message)
                return

            search_text = message.text.strip()
            self.perform_note_search(message, search_text)

    # Вспомогательные методы
    def create_main_notes_keyboard(self):
        """Создание основной клавиатуры для работы с заметками"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        buttons = [
            "📝 Новая заметка",
            "📋 Список заметок",
            "🔍 Поиск заметок",
            "📊 Статистика",
            "📁 Экспорт заметок",
            "🔙 Главное меню"
        ]
        for btn in buttons:
            markup.add(types.KeyboardButton(btn))
        return markup

    def create_cancel_keyboard(self):
        """Создание клавиатуры с кнопкой отмены"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("❌ Отмена"))
        return markup

    def create_skip_keyboard(self):
        """Создание клавиатуры с кнопкой пропуска"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("⏭ Пропустить"))
        return markup

    def cancel_note_creation(self, message):
        """Отмена создания заметки"""
        user_id = message.from_user.id
        if user_id in self.user_states:
            del self.user_states[user_id]

        self.bot.send_message(
            message.chat.id,
            "❌ Создание заметки отменено."
        )

    def cancel_operation(self, message):
        """Отмена текущей операции"""
        user_id = message.from_user.id
        if user_id in self.user_states:
            del self.user_states[user_id]

        self.bot.send_message(
            message.chat.id,
            "❌ Операция отменена."
        )

    def perform_note_search(self, message, search_text):
        """Выполнение поиска заметок"""
        user_id = message.from_user.id

        # Очищаем состояние
        if user_id in self.user_states:
            del self.user_states[user_id]

        notes = self.db.search_notes(user_id, search_text)

        if not notes:
            self.bot.send_message(
                message.chat.id,
                f"🔍 *Результаты поиска по запросу:* `{search_text}`\n\n"
                "❌ Заметки не найдены.\n\n"
                "Попробуйте:\n"
                "• Изменить поисковый запрос\n"
                "• Использовать другие ключевые слова\n"
                "• Просмотреть все заметки: /note_list"
            )
            return

        response = f"🔍 *Результаты поиска по запросу:* `{search_text}`\n\n"
        response += f"Найдено заметок: *{len(notes)}*\n\n"

        for i, note in enumerate(notes[:5], 1):  # Показываем первые 5
            created = datetime.strptime(note['created_at'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
            preview = note['content'][:100] + "..." if len(note['content']) > 100 else note['content']

            response += f"*{i}. {note['title']}*\n"
            response += f"   📅 {created} | 📁 {note['category']}\n"
            response += f"   {preview}\n"
            response += f"   ID: `{note['id']}`\n\n"

        if len(notes) > 5:
            response += f"*... и еще {len(notes) - 5} заметок*\n"

        response += "\nДля просмотра всех заметок используйте /note_list или для удаления /note_del"

        self.bot.send_message(
            message.chat.id,
            response
        )

        logger.info(f"NOTE_SEARCH выполнен: user_id={user_id}, query='{search_text}', found={len(notes)}")


    def show_note_for_edit(self, message, note_id):
        """Показать заметку для редактирования"""
        user_id = message.from_user.id
        note = self.db.get_note_by_id(user_id, note_id)

        if not note:
            self.bot.send_message(
                message.chat.id,
                f"❌ Заметка с ID `{note_id}` не найдена или вам не принадлежит."
            )
            return

        # Очищаем состояние
        if user_id in self.user_states:
            del self.user_states[user_id]

        created = datetime.strptime(note['created_at'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')
        updated = datetime.strptime(note['updated_at'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')
        tags = json.loads(note['tags']) if note['tags'] else []

        response = (
            f"✏️ *Редактирование заметки #`{note_id}`*\n\n"
            f"*Заголовок:* {note['title']}\n"
            f"*Категория:* {note['category']}\n"
            f"*Теги:* {', '.join(tags) if tags else 'нет'}\n"
            f"*Создана:* {created}\n"
            f"*Обновлена:* {updated}\n\n"
            f"*Содержание:*\n{note['content'][:500]}"
            f"{'...' if len(note['content']) > 500 else ''}\n\n"
            f"Выберите, что хотите изменить:"
        )

        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = [
            types.InlineKeyboardButton("📝 Заголовок", callback_data=f"edit_title:{note_id}"),
            types.InlineKeyboardButton("📄 Содержание", callback_data=f"edit_content:{note_id}"),
            types.InlineKeyboardButton("🏷 Теги", callback_data=f"edit_tags:{note_id}"),
            types.InlineKeyboardButton("📁 Категория", callback_data=f"edit_category:{note_id}"),
            types.InlineKeyboardButton("📌 Закрепить", callback_data=f"toggle_pin:{note_id}"),
            types.InlineKeyboardButton("❌ Удалить", callback_data=f"delete_note:{note_id}"),
            types.InlineKeyboardButton("🔙 Назад", callback_data="notes_list")
        ]
        markup.add(*buttons)

        self.bot.send_message(
            message.chat.id,
            response
        )

    def confirm_note_delete(self, message, note_id):
        """Подтверждение удаления заметки"""
        user_id = message.from_user.id
        note = self.db.get_note_by_id(user_id, note_id)

        if not note:
            self.bot.send_message(
                message.chat.id,
                f"❌ Заметка с ID `{note_id}` не найдена или вам не принадлежит."
            )
            return

        # Очищаем состояние
        if user_id in self.user_states:
            del self.user_states[user_id]

        response = (
            f"🗑 *Подтверждение удаления*\n\n"
            f"Вы действительно хотите удалить заметку?\n\n"
            f"*{note['title']}*\n"
            f"ID: `{note_id}`\n"
            f"Категория: {note['category']}\n\n"
            f"⚠️ *Это действие нельзя отменить!*"
        )

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete:{note_id}"),
            types.InlineKeyboardButton("❌ Нет, отменить", callback_data="cancel_delete")
        )

        self.bot.send_message(
            message.chat.id,
            response,
            reply_markup=markup

        )

    def register_callbacks(self):
        """Регистрация обработчиков callback-запросов для заметок"""

        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_note_callbacks(call):
            """Обработка callback-запросов для заметок"""
            user_id = call.from_user.id
            data = call.data

            logger.info(f"CALLBACK_NOTE: user_id={user_id}, data={data}")

            if data.startswith("confirm_delete:"):
            # Подтверждение удаления
                note_id = int(data.split(":")[1])

                if self.db.delete_note(user_id, note_id):
                    self.bot.answer_callback_query(call.id, "Заметка удалена!")
                    self.bot.edit_message_text(
                        "✅ Заметка успешно удалена.",
                        call.message.chat.id,
                        call.message.message_id
                    )
                else:
                    self.bot.answer_callback_query(call.id, "Ошибка удаления!")

            elif data == "cancel_delete":
            # Отмена удаления
                self.bot.answer_callback_query(call.id, "Удаление отменено")
                self.bot.edit_message_text(
                "❌ Удаление отменено.",
                call.message.chat.id,
                call.message.message_id
            )

            elif data == "notes_list":
                # Показ списка заметок
                self.bot.answer_callback_query(call.id)
                self.handle_notes_button(call.message)

            elif data == "notes_add_new":
                # Добавление новой заметки
                self.bot.answer_callback_query(call.id)
                self.handle_note_add1(call.message)

            elif data == "notes_search":
                # Поиск заметок
                self.bot.answer_callback_query(call.id)
                self.handle_note_find1(call.message)

            elif data == "notes_stats":
                # Статистика
                self.bot.answer_callback_query(call.id)
                self.handle_note_count1(call.message)

            elif data == "notes_export":
                # Экспорт заметок
                self.bot.answer_callback_query(call.id, "📁 Создаю файл экспорта...")
                self.handle_note_export1(call.message)
            elif data.startswith("edit_"):
                # Редактирование определенного поля
                parts = data.split(":")
                if len(parts) == 2:
                    action, note_id = parts[0], int(parts[1])

                    # Здесь можно реализовать обработку редактирования
                    self.bot.answer_callback_query(
                        call.id,
                        f"Редактирование: {action.replace('edit_', '')}"
                    )

                    # Пока просто показываем сообщение
                    self.bot.send_message(
                        call.message.chat.id,
                        f"Для редактирования {action.replace('edit_', '')} "
                        f"заметки #{note_id} используйте команду:\n"
                        f"/note_edit {note_id}"
                    )


            else:
                self.bot.answer_callback_query(call.id, "❌ Действие не распознано")