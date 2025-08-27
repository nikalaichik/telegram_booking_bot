import os
import pickle
import logging
from datetime import datetime, timedelta
from pytz import timezone
from typing import List, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account


from config import (
    GOOGLE_SERVICE_ACCOUNT_FILE, GOOGLE_SCOPES, CALENDAR_ID,
    SERVICE_NAME, SERVICE_DURATION_HOURS, WORKING_DAYS, WORKING_HOURS_START,
    WORKING_HOURS_END, DAYS_AHEAD_BOOKING, SERVICE_PRICE_RUB, ADMIN_CONTACT, PHONE_NUMBER
)
from database.models import TimeSlot

logger = logging.getLogger(__name__)

class GoogleCalendarManager:
    """Менеджер для работы с Google Calendar API"""

    def __init__(self):
        self.service = None
        self.authenticate()

    def authenticate(self):
        """Аутентификация через Service Account"""
        try:
            if not os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE):
                raise FileNotFoundError(
                    f"Файл {GOOGLE_SERVICE_ACCOUNT_FILE} не найден. "
                    "Скачайте JSON с ключами сервисного аккаунта из Google Cloud Console."
                )

            creds = service_account.Credentials.from_service_account_file(
                GOOGLE_SERVICE_ACCOUNT_FILE,
                scopes=GOOGLE_SCOPES
            )
            self.service = build('calendar', 'v3', credentials=creds)
            logger.info("Google Calendar API инициализован через Service Account")

        except Exception as e:
            logger.error(f"Ошибка аутентификации Google: {e}")
            raise

    def get_available_slots(self) -> List[TimeSlot]:
        """Получение доступных временных слотов с диагностикой"""
        available_slots = []
        tz = timezone('Europe/Minsk')  # Указываем ваш часовой пояс

        try:
            current_time = datetime.now(tz)
            logger.info(f"Текущее время: {current_time}")
            logger.info(f"Рабочие дни: {WORKING_DAYS}")
            logger.info(f"Рабочие часы: {WORKING_HOURS_START}-{WORKING_HOURS_END}")
            logger.info(f"Дней вперед: {DAYS_AHEAD_BOOKING}")

            # --- Оптимизация: Получаем все занятые события за один запрос ---
            start_period = current_time
            end_period = current_time + timedelta(days=DAYS_AHEAD_BOOKING + 1)

            events_result = self.service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=start_period.isoformat(),
                timeMax=end_period.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            busy_events = events_result.get('items', [])

            # Создаем множество с началом занятых слотов для быстрой проверки
            busy_slots_start_times = set()
            for event in busy_events:
                # Google API всегда возвращает время с часовым поясом
                start_str = event['start'].get('dateTime', event['start'].get('date'))
                start_dt = datetime.fromisoformat(start_str)
                busy_slots_start_times.add(start_dt)

            for day in range(1, DAYS_AHEAD_BOOKING + 1):
                date_to_check = current_time.date() + timedelta(days=day)

                if date_to_check.weekday() not in WORKING_DAYS:
                    continue

                for hour in range(WORKING_HOURS_START, WORKING_HOURS_END):
                    # Сразу создаем "осознающий" объект datetime
                    slot_datetime = tz.localize(datetime(
                        date_to_check.year, date_to_check.month, date_to_check.day, hour
                    ))

                    if slot_datetime <= current_time:
                        continue

                    # Проверяем, не занят ли слот, локально (быстро)
                    if slot_datetime not in busy_slots_start_times:
                        slot = TimeSlot(
                            date=slot_datetime.strftime('%Y-%m-%d'),
                            time=slot_datetime.strftime('%H:%M'),
                            datetime=slot_datetime,
                            is_available=True
                        )
                        available_slots.append(slot)

            logger.info(f"Найдено доступных слотов: {len(available_slots)}")
            return available_slots

            '''slots_generated = 0
            slots_available = 0

            for day in range(1, DAYS_AHEAD_BOOKING + 1):
                date = current_time + timedelta(days=day)

                # Пропускаем нерабочие дни
                if date.weekday() not in WORKING_DAYS:
                    logger.debug(f"Пропуск нерабочего дня: {date.strftime('%Y-%m-%d (%A)')}")
                    continue

                # Генерируем слоты для рабочих часов
                for hour in range(WORKING_HOURS_START, WORKING_HOURS_END):
                    slot_datetime = date.replace(
                        hour=hour, minute=0, second=0, microsecond=0
                    )

                    slots_generated += 1

                    # Пропускаем прошедшие слоты
                    if slot_datetime <= current_time:
                        logger.debug(f"Пропуск прошедшего слота: {slot_datetime}")
                        continue

                    # Проверяем доступность в календаре
                    logger.debug(f"Проверяем слот: {slot_datetime}")

                    if self.is_slot_available(slot_datetime):
                        slot = TimeSlot(
                            date=slot_datetime.strftime('%Y-%m-%d'),
                            time=slot_datetime.strftime('%H:%M'),
                            datetime=slot_datetime,
                            is_available=True
                        )
                        available_slots.append(slot)
                        slots_available += 1
                        logger.debug(f"Доступный слот: {slot_datetime}")
                    else:
                        logger.debug(f"Занятый слот: {slot_datetime}")

            logger.info(f"Сгенерировано слотов: {slots_generated}")
            logger.info(f"Доступных слотов: {slots_available}")
            logger.info(f"Возвращаем первые {min(50, len(available_slots))} слотов")'''

            return available_slots[:50]  # Ограничиваем количество

        except Exception as e:
            logger.error(f"Ошибка получения доступных слотов: {e}")
            import traceback
            logger.error(f"Полная трассировка: {traceback.format_exc()}")
            return []

    def is_slot_available(self, slot_datetime: datetime) -> bool:
        """Проверка доступности временного слота в календаре"""
        try:
            tz = timezone('Europe/Moscow')
            # Если пришел "наивный" datetime, делаем его "осознающим"
            if slot_datetime.tzinfo is None:
                slot_datetime = tz.localize(slot_datetime)
            #slot_datetime = slot_datetime.astimezone(tz)  # Конвертируем в нужную TZ

            time_min = slot_datetime.isoformat()  # Убрали 'Z' - используем локальное время
            time_max = (slot_datetime + timedelta(hours=SERVICE_DURATION_HOURS)).isoformat()
            #time_min = slot_datetime.isoformat() + 'Z'
            #time_max = (slot_datetime + timedelta(hours=SERVICE_DURATION_HOURS)).isoformat() + 'Z'

            events_result = self.service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            # Добавим логирование событий
            if events:
                logger.info(f"Найдены события, делающие слот {slot_datetime} занятым:")
                for event in events:
                    logger.info(f"- {event.get('summary')} ({event['start'].get('dateTime')} - {event['end'].get('dateTime')})")
            return len(events) == 0

        except HttpError as e:
            logger.error(f"Ошибка проверки доступности слота: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при проверке слота: {e}")
            return False

    def create_event(self, date: str, time: str, client_info: str, contact_info: str) -> Optional[str]:
        """Создание события в календаре"""
        try:
            start_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
            end_datetime = start_datetime + timedelta(hours=SERVICE_DURATION_HOURS)

            description = (
                f"Консультация с клиентом: {client_info}\n"
                f"Контакт: {contact_info}\n"
                f"Стоимость: {SERVICE_PRICE_RUB} руб.\n"
                f"Администратор: {ADMIN_CONTACT}\n"
                f"Телефон: {PHONE_NUMBER}"
            )

            event = {
                'summary': f'{SERVICE_NAME} - {client_info}',
                'description': description,
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'Europe/Moscow',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'Europe/Moscow',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # За день
                        {'method': 'popup', 'minutes': 60},       # За час
                    ],
                },
            }

            created_event = self.service.events().insert(
                calendarId=CALENDAR_ID, body=event
            ).execute()

            event_id = created_event['id']
            logger.info(f"Создано событие в календаре: {event_id}")
            return event_id

        except HttpError as e:
            logger.error(f"Ошибка создания события в календаре: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при создании события: {e}")
            return None

    def delete_event(self, event_id: str) -> bool:
        """Удаление события из календаря"""
        try:
            self.service.events().delete(
                calendarId=CALENDAR_ID, eventId=event_id
            ).execute()

            logger.info(f"Удалено событие из календаря: {event_id}")
            return True

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Событие {event_id} не найдено")
            else:
                logger.error(f"Ошибка удаления события: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при удалении события: {e}")
            return False
