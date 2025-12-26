import sqlite3
import logging
from datetime import datetime
import json

# Настройка логгера
logger = logging.getLogger('telegram_bot.database')


class Database:
    def __init__(self, db_name='notes.db'):
        """Инициализация базы данных"""
        self.db_name = db_name
        self.init_database()

    def get_connection(self):
        """Получение соединения с базой данных"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """Инициализация таблиц базы данных"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица заметок с составным ключом
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notes (
                    user_id INTEGER NOT NULL,
                    note_local_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT,
                    category TEXT DEFAULT 'general',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, note_local_id)
                )
            ''')

            # Удаляем старый индекс если он есть и создаем новый
            cursor.execute('DROP INDEX IF EXISTS idx_user_id')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_notes_user_id ON notes(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at)')

            conn.commit()
            logger.info("База данных инициализирована успешно")

        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()

    def add_or_update_user(self, user_id, username=None, first_name=None, last_name=None):
        """Добавление или обновление информации о пользователе"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_name, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, username, first_name, last_name))

            conn.commit()
            logger.info(f"Пользователь {user_id} обновлен в БД")
            return True

        except Exception as e:
            logger.error(f"Ошибка добавления пользователя {user_id}: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()

    def get_next_local_id(self, user_id):
        """Получение следующего локального ID для пользователя"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT COALESCE(MAX(note_local_id), 0) as max_id 
                FROM notes 
                WHERE user_id = ?
            ''', (user_id,))

            result = cursor.fetchone()
            max_id = result['max_id'] if result else 0

            return max_id + 1

        except Exception as e:
            logger.error(f"Ошибка получения следующего ID для пользователя {user_id}: {e}")
            return 1
        finally:
            if 'conn' in locals():
                conn.close()

    def add_note(self, user_id, title, content, tags=None, category='general'):
        """Добавление новой заметки с локальным ID"""
        try:
            # Сначала добавляем/обновляем пользователя
            self.add_or_update_user(user_id)

            # Получаем следующий локальный ID
            note_local_id = self.get_next_local_id(user_id)

            conn = self.get_connection()
            cursor = conn.cursor()

            tags_json = json.dumps(tags) if tags else None

            cursor.execute('''
                INSERT INTO notes 
                (user_id, note_local_id, title, content, tags, category, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (user_id, note_local_id, title, content, tags_json, category))

            conn.commit()

            logger.info(f"Заметка добавлена: user={user_id}, local_id={note_local_id}")
            return note_local_id  # Возвращаем локальный ID

        except Exception as e:
            logger.error(f"Ошибка добавления заметки: {e}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()

    def get_user_notes(self, user_id, limit=50, offset=0, category=None):
        """Получение списка заметок пользователя"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            query = '''
                SELECT user_id, note_local_id, title, content, tags, category,
                       created_at, updated_at
                FROM notes 
                WHERE user_id = ?
            '''
            params = [user_id]

            if category:
                query += ' AND category = ?'
                params.append(category)

            query += ' ORDER BY note_local_id DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])

            cursor.execute(query, params)
            notes = cursor.fetchall()

            # Преобразуем в словари и добавляем поле id (это будет note_local_id)
            result = []
            for note in notes:
                note_dict = dict(note)
                # Для совместимости со старым кодом добавляем поле id
                note_dict['id'] = note_dict['note_local_id']
                result.append(note_dict)

            return result

        except Exception as e:
            logger.error(f"Ошибка получения заметок пользователя {user_id}: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()

    def get_note_by_id(self, user_id, note_local_id):
        """Получение конкретной заметки по локальному ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT user_id, note_local_id, title, content, tags, category,
                       created_at, updated_at
                FROM notes 
                WHERE user_id = ? AND note_local_id = ?
            ''', (user_id, note_local_id))

            note = cursor.fetchone()
            if note:
                note_dict = dict(note)
                note_dict['id'] = note_dict['note_local_id']  # Для совместимости
                return note_dict
            return None

        except Exception as e:
            logger.error(f"Ошибка получения заметки {note_local_id}: {e}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()

    def search_notes(self, user_id, search_text, search_in_content=True):
        """Поиск заметок по тексту"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            search_pattern = f'%{search_text}%'

            if search_in_content:
                query = '''
                    SELECT user_id, note_local_id, title, content, tags, category,
                           created_at, updated_at
                    FROM notes 
                    WHERE user_id = ? 
                    AND (title LIKE ? OR content LIKE ?)
                    ORDER BY note_local_id DESC
                '''
                cursor.execute(query, (user_id, search_pattern, search_pattern))
            else:
                query = '''
                    SELECT user_id, note_local_id, title, content, tags, category,
                           created_at, updated_at
                    FROM notes 
                    WHERE user_id = ? AND title LIKE ?
                    ORDER BY note_local_id DESC
                '''
                cursor.execute(query, (user_id, search_pattern))

            notes = cursor.fetchall()

            # Преобразуем и добавляем поле id
            result = []
            for note in notes:
                note_dict = dict(note)
                note_dict['id'] = note_dict['note_local_id']
                result.append(note_dict)

            return result

        except Exception as e:
            logger.error(f"Ошибка поиска заметок: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()

    def update_note(self, user_id, note_local_id, title=None, content=None, tags=None, category=None):
        """Обновление заметки"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Получаем текущие данные заметки
            current_note = self.get_note_by_id(user_id, note_local_id)
            if not current_note:
                return False

            # Обновляем только переданные поля
            new_title = title if title is not None else current_note['title']
            new_content = content if content is not None else current_note['content']
            new_tags = json.dumps(tags) if tags is not None else current_note['tags']
            new_category = category if category is not None else current_note['category']

            cursor.execute('''
                UPDATE notes 
                SET title = ?, content = ?, tags = ?, category = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND note_local_id = ?
            ''', (new_title, new_content, new_tags, new_category, user_id, note_local_id))

            conn.commit()
            logger.info(f"Заметка {note_local_id} пользователя {user_id} обновлена")
            return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Ошибка обновления заметки {note_local_id}: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()

    def delete_note(self, user_id, note_local_id):
        """Удаление заметки"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                DELETE FROM notes 
                WHERE user_id = ? AND note_local_id = ?
            ''', (user_id, note_local_id))

            conn.commit()
            deleted = cursor.rowcount > 0

            if deleted:
                logger.info(f"Заметка {note_local_id} пользователя {user_id} удалена")

            return deleted

        except Exception as e:
            logger.error(f"Ошибка удаления заметки {note_local_id}: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()

    def get_notes_count(self, user_id, category=None):
        """Получение количества заметок пользователя"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            if category:
                cursor.execute('''
                    SELECT COUNT(*) as count 
                    FROM notes 
                    WHERE user_id = ? AND category = ?
                ''', (user_id, category))
            else:
                cursor.execute('''
                    SELECT COUNT(*) as count 
                    FROM notes 
                    WHERE user_id = ?
                ''', (user_id,))

            result = cursor.fetchone()
            return result['count'] if result else 0

        except Exception as e:
            logger.error(f"Ошибка получения количества заметок: {e}")
            return 0
        finally:
            if 'conn' in locals():
                conn.close()

    def get_all_user_notes(self, user_id):
        """Получение всех заметок пользователя (для экспорта)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT user_id, note_local_id, title, content, tags, category,
                       created_at, updated_at
                FROM notes 
                WHERE user_id = ?
                ORDER BY note_local_id
            ''', (user_id,))

            notes = cursor.fetchall()

            # Преобразуем и добавляем поле id
            result = []
            for note in notes:
                note_dict = dict(note)
                note_dict['id'] = note_dict['note_local_id']
                result.append(note_dict)

            return result

        except Exception as e:
            logger.error(f"Ошибка получения всех заметок пользователя {user_id}: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()