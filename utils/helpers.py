import logging
from datetime import datetime, timedelta
from typing import List, Dict
from pytz import timezone
from config import REMINDER_DAYS_BEFORE, REMINDER_HOURS_BEFORE, SERVICE_PRICE_RUB
from database.models import Booking

logger = logging.getLogger(__name__)

def format_date(date_str: str) -> str:
    """Форматирование даты для отображения"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')

        # Русские названия дней недели
        weekdays = {
            0: 'понедельник', 1: 'вторник', 2: 'среда', 3: 'четверг',
            4: 'пятница', 5: 'суббота', 6: 'воскресенье'
        }

        # Русские названия месяцев
        months = {
            1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
            5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
            9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
        }

        day = date_obj.day
        month = months[date_obj.month]
        weekday = weekdays[date_obj.weekday()]

        return f"{day} {month} ({weekday})"

    except Exception as e:
        logger.error(f"Ошибка форматирования даты {date_str}: {e}")
        return date_str

def format_booking_list(bookings: List[Dict]) -> str:
    """Форматирование списка записей для отображения"""
    if not bookings:
        return "Записи отсутствуют."

    formatted_bookings = []

    for booking in bookings:
        date_formatted = format_date(booking['date'])

        # Определяем статус
        status_icons = {
            'confirmed': '✅ Подтверждена',
            'cancelled': '❌ Отменена'
        }

        status = status_icons.get(booking['status'], booking['status'])

        booking_text = (
            f"📅 {date_formatted}\n"
            f"🕐 {booking['time']}\n"
            f"👤 {booking['contact_info']}\n"
            f"📋 {status}\n"
            f"💰 {SERVICE_PRICE_RUB} руб.\n"
        )

        formatted_bookings.append(booking_text)

    return "\n".join(formatted_bookings)

async def schedule_booking_reminders(context, booking: Booking, booking_id: int):
    """Планирование напоминаний о записи"""
    try:
        tz = timezone('Europe/Minsk')
        # 2. Создаем "наивный" объект datetime
        appointment_datetime_naive = datetime.strptime(f"{booking.date} {booking.time}", "%Y-%m-%d %H:%M")
        # 3. Делаем его "осознающим" часовой пояс
        appointment_datetime = tz.localize(appointment_datetime_naive)
        #appointment_datetime = datetime.strptime(f"{booking.date} {booking.time}", "%Y-%m-%d %H:%M")
        current_time = datetime.now(tz)

        # Напоминание за день
        reminder_day = appointment_datetime - timedelta(days=REMINDER_DAYS_BEFORE)
        if reminder_day > current_time:
            context.job_queue.run_once(
                send_day_reminder,
                reminder_day,
                data={'booking_id': booking_id, 'booking': booking},
                name=f"day_reminder_{booking_id}"
            )
            logger.info(f"Запланировано напоминание за день для записи {booking_id}")

        # Напоминание за час
        reminder_hour = appointment_datetime - timedelta(hours=REMINDER_HOURS_BEFORE)
        if reminder_hour > current_time:
            context.job_queue.run_once(
                send_hour_reminder,
                reminder_hour,
                data={'booking_id': booking_id, 'booking': booking},
                name=f"hour_reminder_{booking_id}"
            )
            logger.info(f"Запланировано напоминание за час для записи {booking_id}")

    except Exception as e:
        logger.error(f"Ошибка планирования напоминаний: {e}")

async def send_day_reminder(context):
    """Отправка напоминания за день"""
    from config import ADMIN_CONTACT, PHONE_NUMBER

    booking_data = context.job.data
    booking = booking_data['booking']

    date_formatted = format_date(booking.date)

    await context.bot.send_message(
        chat_id=booking.user_id,
        text=f"📅 <b>Напоминание!</b>\n\n"
             f"Завтра у вас запланирована консультация:\n"
             f"🗓 Дата: {date_formatted}\n"
             f"🕐 Время: {booking.time}\n\n"
             f"💰 Стоимость: {SERVICE_PRICE_RUB} руб.\n"
             f"💳 Оплата администратору: {ADMIN_CONTACT}\n"
             f"📱 Телефон: {PHONE_NUMBER}\n\n"
             f"До встречи!",
        parse_mode='HTML'
    )

async def send_hour_reminder(context):
    """Отправка напоминания за час"""
    booking_data = context.job.data
    booking = booking_data['booking']

    await context.bot.send_message(
        chat_id=booking.user_id,
        text=f"⏰ <b>Напоминание!</b>\n\n"
             f"Через час у вас консультация:\n"
             f"🕐 Время: {booking.time}\n\n"
             f"Увидимся скоро!",
        parse_mode='HTML'
    )
