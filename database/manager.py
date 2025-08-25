import sqlite3
import logging
from typing import List, Dict, Optional
from datetime import datetime
from .models import Booking

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Менеджер для работы с базой данных"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Инициализация базы данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Создание таблицы записей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    contact_info TEXT NOT NULL,
                    event_id TEXT,
                    status TEXT DEFAULT 'confirmed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Создание индексов для быстрого поиска
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON bookings(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON bookings(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_date_time ON bookings(date, time)')

            conn.commit()
            logger.info("База данных инициализирована")

        except sqlite3.Error as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise
        finally:
            conn.close()

    def save_booking(self, booking: Booking) -> int:
        """Сохранение брони в БД"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO bookings (user_id, username, date, time, contact_info, event_id, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                booking.user_id, booking.username, booking.date, booking.time,
                booking.contact_info, booking.event_id, booking.status
            ))

            booking_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Сохранена запись ID: {booking_id}")
            return booking_id

        except sqlite3.Error as e:
            logger.error(f"Ошибка сохранения записи: {e}")
            raise
        finally:
            conn.close()

    def update_booking_status(self, booking_id: int, status: str, event_id: str = None):
        """Обновление статуса брони"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if event_id:
                cursor.execute(
                    'UPDATE bookings SET status = ?, event_id = ? WHERE id = ?',
                    (status, event_id, booking_id)
                )
            else:
                cursor.execute(
                    'UPDATE bookings SET status = ? WHERE id = ?',
                    (status, booking_id)
                )

            conn.commit()
            logger.info(f"Обновлен статус записи {booking_id}: {status}")

        except sqlite3.Error as e:
            logger.error(f"Ошибка обновления статуса: {e}")
            raise
        finally:
            conn.close()

    def get_user_bookings(self, user_id: int) -> List[Dict]:
        """Получение записей пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, date, time, contact_info, status, created_at
                FROM bookings
                WHERE user_id = ?
                ORDER BY date DESC, time DESC
            ''', (user_id,))

            bookings = cursor.fetchall()
            return [
                {
                    'id': b[0], 'date': b[1], 'time': b[2],
                    'contact_info': b[3], 'status': b[4], 'created_at': b[5]
                }
                for b in bookings
            ]

        except sqlite3.Error as e:
            logger.error(f"Ошибка получения записей пользователя: {e}")
            return []
        finally:
            conn.close()

    def get_confirmed_bookings(self) -> List[Dict]:
        """Получение подтвержденных записей для напоминаний"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, user_id, date, time, contact_info, event_id
                FROM bookings
                WHERE status = 'confirmed'
            ''')

            bookings = cursor.fetchall()
            return [
                {
                    'id': b[0], 'user_id': b[1], 'date': b[2],
                    'time': b[3], 'contact_info': b[4], 'event_id': b[5]
                }
                for b in bookings
            ]

        except sqlite3.Error as e:
            logger.error(f"Ошибка получения подтвержденных записей: {e}")
            return []
        finally:
            conn.close()

    def is_slot_booked(self, date: str, time: str) -> bool:
        """Проверка, занят ли временной слот"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT COUNT(*) FROM bookings
                WHERE date = ? AND time = ? AND status = 'confirmed'
            ''', (date, time))

            count = cursor.fetchone()[0]
            return count > 0

        except sqlite3.Error as e:
            logger.error(f"Ошибка проверки слота: {e}")
            return True  # В случае ошибки считаем слот занятым
        finally:
            conn.close()