import logging
from typing import List, Dict, Optional
from datetime import datetime
from pytz import timezone
from config import DATABASE_PATH
from database.manager import DatabaseManager, Booking
from database.models import TimeSlot
from calendar_api.manager import GoogleCalendarManager

logger = logging.getLogger(__name__)

class BookingService:
    """Сервис для управления записями"""

    def __init__(self):
        self.db = DatabaseManager(DATABASE_PATH)
        self.calendar = GoogleCalendarManager()

    def get_available_slots(self) -> List[TimeSlot]:
        """Получение доступных временных слотов"""
        try:
            # Получаем слоты из календаря
            calendar_slots = self.calendar.get_available_slots()

            # Фильтруем уже забронированные слоты
            available_slots = []
            for slot in calendar_slots:
                if not self.db.is_slot_booked(slot.date, slot.time):
                    available_slots.append(slot)

            logger.info(f"Доступно {len(available_slots)} временных слотов")
            return available_slots

        except Exception as e:
            logger.error(f"Ошибка получения доступных слотов: {e}")
            return []

    def is_slot_taken(self, date: str, time: str) -> bool:
        """Проверка занятости слота"""
        try:
            # Проверяем в базе данных
            if self.db.is_slot_booked(date, time):
                return True

            # Проверяем в календаре
            slot_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
            return not self.calendar.is_slot_available(slot_datetime)

        except Exception as e:
            logger.error(f"Ошибка проверки занятости слота: {e}")
            return True  # В случае ошибки считаем занятым

    async def create_booking(self, user_id: int, username: str, date: str, time: str, contact_info: str) -> Dict:
        """Создание записи"""
        try:
            # Создаем событие в календаре
            client_info = f"@{username}" if username else f"ID: {user_id}"
            event_id = self.calendar.create_event(date, time, client_info, contact_info)

            if not event_id:
                return {'success': False, 'error': 'Не удалось создать событие в календаре'}

            # Создаем запись в базе данных
            booking = Booking(
                user_id=user_id,
                username=username,
                date=date,
                time=time,
                contact_info=contact_info,
                event_id=event_id,
                status="confirmed"
            )

            booking_id = self.db.save_booking(booking)

            logger.info(f"Создана запись {booking_id} для пользователя {user_id}")

            return {
                'success': True,
                'booking_id': booking_id,
                'booking': booking
            }

        except Exception as e:
            logger.error(f"Ошибка создания записи: {e}")
            return {'success': False, 'error': str(e)}

    def get_user_bookings(self, user_id: int) -> List[Dict]:
        """Получение всех записей пользователя"""
        return self.db.get_user_bookings(user_id)

    def get_user_future_bookings(self, user_id: int):
        """Получение только предстоящих записей пользователя."""
        all_bookings = self.db.get_user_bookings(user_id)
        future_bookings = []

        # Определяем текущее время в нужном часовом поясе
        # Важно, чтобы часовой пояс совпадал с тем, в котором вы работаете!
        # Например, 'Europe/Moscow'
        tz = timezone('Europe/Minsk')
        now = datetime.now(tz)

        for booking in all_bookings:
            # Превращаем строковые дату и время из базы в объект datetime
            booking_datetime_naive = datetime.strptime(f"{booking['date']} {booking['time']}", "%Y-%m-%d %H:%M")

            # Делаем его "осознающим" часовой пояс
            booking_datetime_aware = tz.localize(booking_datetime_naive)

            # Сравниваем с текущим временем
            if booking_datetime_aware >= now:
                future_bookings.append(booking)

        return future_bookings
    def cancel_booking(self, booking_id: int) -> bool:
        """Отмена записи"""
        try:
            # Здесь можно добавить логику отмены
            # Например, удаление события из календаря и обновление статуса в БД
            self.db.update_booking_status(booking_id, "cancelled")
            return True
        except Exception as e:
            logger.error(f"Ошибка отмены записи {booking_id}: {e}")
            return False