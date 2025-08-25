from typing import List, Dict
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from database.models import TimeSlot

class BotKeyboards:
    """Класс для создания клавиатур бота"""

    @staticmethod
    def main_menu(processing: bool = False) -> InlineKeyboardMarkup:
        """Главное меню"""
        keyboard = [
            [InlineKeyboardButton("⏳ Ищем доступные слоты..." if processing
                else "📅 Записаться на консультацию",
                callback_data='book_appointment' if not processing else 'processing')],
            [InlineKeyboardButton("📋 Мои записи", callback_data='my_bookings')],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data='help')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def dates_keyboard(dates: Dict[str, List]) -> InlineKeyboardMarkup:
        """Клавиатура с доступными датами"""
        keyboard = []

        for date, slots in list(dates.items())[:7]:  # Максимум 7 дней
            date_obj = datetime.strptime(date, '%Y-%m-%d')

            # Русские названия дней недели
            weekdays = {
                0: 'Пн', 1: 'Вт', 2: 'Ср', 3: 'Чт',
                4: 'Пт', 5: 'Сб', 6: 'Вс'
            }

            date_str = f"{date_obj.strftime('%d.%m')} ({weekdays[date_obj.weekday()]}) - {len(slots)} слотов"
            keyboard.append([InlineKeyboardButton(date_str, callback_data=f'select_date_{date}')])

        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def times_keyboard(date: str, times: List[TimeSlot]) -> InlineKeyboardMarkup:
        """Клавиатура с доступным временем"""
        keyboard = []

        # Группируем время по 3 кнопки в ряд
        row = []
        for time_slot in times:
            # Используем атрибуты объекта TimeSlot вместо словаря
            time_str = time_slot.time
            row.append(InlineKeyboardButton(
                f"🕐 {time_str}",
                #callback_data=f'select_time_{date}_{time_str}'
                callback_data=f'select_time_{date}_{time_str.replace(":", "-")}'
            ))

            if len(row) == 3:
                keyboard.append(row)
                row = []

        # Добавляем оставшиеся кнопки
        if row:
            keyboard.append(row)

        keyboard.append([
            InlineKeyboardButton("◀️ Назад к датам", callback_data='book_appointment')
        ])
        return InlineKeyboardMarkup(keyboard)
    '''@staticmethod
    def times_keyboard(date: str, times: List[Dict]) -> InlineKeyboardMarkup:
        """Клавиатура с доступным временем"""
        keyboard = []

        # Группируем время по 3 кнопки в ряд
        row = []
        for time_slot in times:
            time_str = time_slot['time']
            row.append(InlineKeyboardButton(f"🕐 {time_str}", callback_data=f'select_time_{date}_{time_str}'))

            if len(row) == 3:
                keyboard.append(row)
                row = []

        # Добавляем оставшиеся кнопки
        if row:
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton("◀️ Назад к датам", callback_data='book_appointment')])
        return InlineKeyboardMarkup(keyboard)'''

    @staticmethod
    def processing_keyboard() -> InlineKeyboardMarkup:
        """Клавиатура во время обработки"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⏳ Обработка...", callback_data='processing')]
    ])

    @staticmethod
    def booking_confirmation(date: str) -> InlineKeyboardMarkup:
        """Клавиатура подтверждения записи"""
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить запись", callback_data='confirm_booking')],
            [InlineKeyboardButton("◀️ Изменить время", callback_data=f'select_date_{date}')],
            [InlineKeyboardButton("❌ Отмена", callback_data='back_to_main')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def back_to_main() -> InlineKeyboardMarkup:
        """Кнопка возврата в главное меню"""
        keyboard = [
            [InlineKeyboardButton("◀️ В главное меню", callback_data='back_to_main')]
        ]
        return InlineKeyboardMarkup(keyboard)