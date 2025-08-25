import logging
from typing import Dict
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from config import SERVICE_NAME, SERVICE_PRICE_RUB, MESSAGES, ADMIN_CONTACT, PHONE_NUMBER
from database.manager import DatabaseManager, Booking
from calendar_api.manager import GoogleCalendarManager
from services.booking import BookingService
from .keyboards import BotKeyboards
from utils.helpers import format_date, format_booking_list

logger = logging.getLogger(__name__)

class BotHandlers:
    """Класс обработчиков команд бота"""

    def __init__(self):
        self.keyboards = BotKeyboards()
        self.booking_service = BookingService()
        self.user_sessions: Dict[int, Dict] = {}  # Сессии пользователей

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        logger.info(f"Пользователь {user.id} ({user.username}) запустил бота")

        await update.message.reply_text(
            MESSAGES['welcome'],
            reply_markup=self.keyboards.main_menu()
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = (
            "🤖 <b>Помощь по боту</b>\n\n"
            "📋 <b>Доступные команды:</b>\n"
            "/start - Главное меню\n"
            "/help - Эта справка\n"
            "/mybookings - Мои записи\n\n"
            "💡 <b>Как записаться:</b>\n"
            "1. Нажмите «Записаться на консультацию»\n"
            "2. Выберите удобную дату\n"
            "3. Выберите время\n"
            "4. Укажите контактную информацию\n"
            "5. Подтвердите запись\n"
            "6. Оплата производится администратору\n\n"
            f"💰 <b>Стоимость:</b> {SERVICE_PRICE_RUB} руб.\n"
            f"📞 <b>Администратор:</b> {ADMIN_CONTACT}\n"
            f"📱 <b>Телефон:</b> {PHONE_NUMBER}"
        )

        # Определяем, откуда пришел запрос
        if update.message:
            await update.message.reply_text(
                help_text,
                parse_mode='HTML',
                reply_markup=self.keyboards.back_to_main()
            )
        else:
            query = update.callback_query
            await query.edit_message_text(
                help_text,
                parse_mode='HTML',
                reply_markup=self.keyboards.back_to_main()
            )

    async def my_bookings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать будущие записи пользователя"""
        user = update.effective_user
        bookings = self.booking_service.get_user_future_bookings(user.id)

        # Всегда создаем новый текст и клавиатуру
        new_text = "📋 У вас пока нет записей на консультации." if not bookings else \
              "📋 <b>Ваши записи:</b>\n\n" + format_booking_list(bookings)
        new_markup = self.keyboards.back_to_main()

        # Определяем, откуда пришел запрос
        try:
            if update.message:
                await update.message.reply_text(
                    new_text,
                    parse_mode='HTML',
                    reply_markup=new_markup
                )
            else:
                query = update.callback_query
                current_text = query.message.text
                current_markup = query.message.reply_markup

                # Проверяем, действительно ли нужно обновлять сообщение
                if current_text != new_text or str(current_markup) != str(new_markup):
                    await query.edit_message_text(
                        new_text,
                        parse_mode='HTML',
                        reply_markup=new_markup
                    )
                else:
                    await query.answer("Ваши записи уже отображены")

        except Exception as e:
            logger.error(f"Ошибка отображения записей: {e}")
            if not update.message:
                await update.callback_query.answer("Произошла ошибка", show_alert=True)

    async def show_available_dates(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать доступные даты с улучшенной диагностикой"""
        query = update.callback_query
        # Обновляем сообщение с состоянием обработки
        await query.edit_message_text(
            "⌛ Ищем доступные слоты...",
            reply_markup=self.keyboards.main_menu(processing=True)
            )
        try:
            logger.info("Запрос доступных слотов...")
            available_slots = self.booking_service.get_available_slots()
            logger.info(f"Получено слотов: {len(available_slots)}")

            if not available_slots:
                logger.warning("Нет доступных слотов")

                # Диагностическое сообщение
                diagnostic_text = (
                    "😔 К сожалению, свободных слотов нет.\n\n"
                    "Возможные причины:\n"
                    "• Все время занято в календаре\n"
                    "• Настройки рабочего времени\n"
                    "• Проблемы с доступом к календарю\n\n"
                    "Попробуйте позже или обратитесь к администратору."
                )

                await query.edit_message_text(
                    diagnostic_text,
                    reply_markup=self.keyboards.back_to_main()
                )
                return

            # Группируем слоты по датам
            dates = {}
            for slot in available_slots:
                date = slot.date
                if date not in dates:
                    dates[date] = []
                dates[date].append(slot)

            logger.info(f"Сгруппировано по датам: {list(dates.keys())}")

            await query.edit_message_text(
                "📅 Выберите удобную дату:",
                reply_markup=self.keyboards.dates_keyboard(dates)
            )

        except Exception as e:
            logger.error(f"Ошибка получения доступных дат: {e}")
            import traceback
            logger.error(f"Полная трассировка: {traceback.format_exc()}")

            await query.edit_message_text(
                "❌ Произошла ошибка при загрузке доступных дат.\n"
                "Проверьте настройки календаря или обратитесь к администратору.",
                reply_markup=self.keyboards.back_to_main()
                )

    async def show_available_times(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать доступное время для выбранной даты"""
        query = update.callback_query
        await query.answer()

        date = query.data.split('_')[-1]
        date_formatted = format_date(date)

        try:
            # Сначала показываем сообщение о поиске времени
            await query.edit_message_text(
                f"⏳ Подбираем доступное время на {date_formatted}...",
                reply_markup=self.keyboards.processing_keyboard()
        )

        # Получаем доступные слоты (может занять время)
            available_slots = self.booking_service.get_available_slots()
            times = [slot for slot in available_slots if slot.date == date]

            if not times:
                await query.edit_message_text(
                    "😔 На эту дату нет свободного времени.",
                    reply_markup=self.keyboards.back_to_main()
                )
                return
            # Показываем доступное время
            await query.edit_message_text(
                f"🕐 Выберите время на {date_formatted}:",
                reply_markup=self.keyboards.times_keyboard(date, times)
            )

        except Exception as e:
            logger.error(f"Ошибка получения доступного времени: {e}")
            await query.edit_message_text(
                "❌ Произошла ошибка при загрузке времени. Попробуйте позже.",
                reply_markup=self.keyboards.back_to_main()
            )

    async def prepare_booking(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подготовка к записи - запрос контактных данных"""
        query = update.callback_query
        await query.answer()

        try:
            # Разбираем callback_data (формат: select_time_YYYY-MM-DD_HH-MM)
            _, _, date, time_part = query.data.split('_', 3)
            # Преобразуем HH-MM обратно в HH:MM
            time = time_part.replace("-", ":")
            user = update.effective_user

            # Проверяем, не занят ли слот
            if self.booking_service.is_slot_taken(date, time):
                await query.edit_message_text(
                    "😔 К сожалению, этот слот уже занят. Выберите другое время.",
                    reply_markup=self.keyboards.back_to_main()
                )
                return

            # Сохраняем данные в сессии пользователя
            self.user_sessions[user.id] = {
                'date': date,
                'time': time,
                'username': user.username or user.first_name,
                'waiting_for_contact': True
            }

            date_formatted = format_date(date)

            await query.edit_message_text(
                f"📋 <b>Предварительная запись:</b>\n\n"
                f"📅 Дата: {date_formatted}\n"
                f"🕐 Время: {time}\n"
                f"💰 Стоимость: {SERVICE_PRICE_RUB} руб.\n\n"
                f"{MESSAGES['ask_contact']}",
                parse_mode='HTML'
            )

        except Exception as e:
            logger.error(f"Ошибка подготовки записи: {e}")
            await query.edit_message_text(
                "❌ Произошла ошибка. Попробуйте снова.",
                reply_markup=self.keyboards.back_to_main()
            )

    async def handle_contact_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка контактной информации"""
        user = update.effective_user
        session_data = self.user_sessions.get(user.id)

        if not session_data or not session_data.get('waiting_for_contact'):
            return  # Игнорируем, если пользователь не в процессе записи

        contact_info = update.message.text.strip()

        if not contact_info or len(contact_info) < 5:
            await update.message.reply_text(
                "❌ Пожалуйста, укажите корректную контактную информацию.\n\n"
                "Например:\n"
                "• Иван Петров, +7 900 123 45 67\n"
                "• @ivan_petrov\n"
                "• ivan@email.com, +7 900 123 45 67"
            )
            return

        # Обновляем сессию
        session_data['contact_info'] = contact_info
        session_data['waiting_for_contact'] = False

        date_formatted = format_date(session_data['date'])

        confirmation_text = (
            f"📋 <b>Подтверждение записи:</b>\n\n"
            f"📅 Дата: {date_formatted}\n"
            f"🕐 Время: {session_data['time']}\n"
            f"👤 Контакт: {contact_info}\n\n"
            f"💰 Стоимость: {SERVICE_PRICE_RUB} руб.\n"
            f"💳 Оплата производится администратору: {ADMIN_CONTACT}\n"
            f"📱 Телефон: {PHONE_NUMBER}\n\n"
            f"Подтвердите создание записи:"
        )

        await update.message.reply_text(
            confirmation_text,
            parse_mode='HTML',
            reply_markup=self.keyboards.booking_confirmation(session_data['date'])
        )

    async def confirm_booking(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подтверждение и создание записи"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        session_data = self.user_sessions.get(user.id)

        if not session_data or not session_data.get('contact_info'):
            await query.edit_message_text(
                "❌ Ошибка: данные бронирования не найдены. Начните заново.",
                reply_markup=self.keyboards.back_to_main()
            )
            return

        try:
            # Создаем запись
            booking_result = await self.booking_service.create_booking(
                user_id=user.id,
                username=session_data['username'],
                date=session_data['date'],
                time=session_data['time'],
                contact_info=session_data['contact_info']
            )

            if booking_result['success']:
                # Планируем напоминания
                await self.schedule_reminders(context, booking_result['booking'], booking_result['booking_id'])

                date_formatted = format_date(session_data['date'])

                await query.edit_message_text(
                    MESSAGES['booking_success'].format(
                        date=date_formatted,
                        time=session_data['time'],
                        contact=session_data['contact_info'],
                        price=SERVICE_PRICE_RUB,
                        admin_contact=ADMIN_CONTACT,
                        phone=PHONE_NUMBER
                    ),
                    parse_mode='HTML',
                    reply_markup=self.keyboards.back_to_main()
                )

                # Очищаем сессию
                del self.user_sessions[user.id]
            else:
                await query.edit_message_text(
                    MESSAGES['booking_error'],
                    reply_markup=self.keyboards.back_to_main()
                )

        except Exception as e:
            logger.error(f"Ошибка создания записи: {e}")
            await query.edit_message_text(
                MESSAGES['booking_error'],
                reply_markup=self.keyboards.back_to_main()
            )

    async def schedule_reminders(self, context: ContextTypes.DEFAULT_TYPE, booking: Booking, booking_id: int):
        """Планирование напоминаний"""
        from utils.helpers import schedule_booking_reminders
        await schedule_booking_reminders(context, booking, booking_id)

    async def send_day_reminder(self, context: ContextTypes.DEFAULT_TYPE):
        """Отправка напоминания за день"""
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

    async def send_hour_reminder(self, context: ContextTypes.DEFAULT_TYPE):
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

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Общий обработчик кнопок с улучшенной обработкой ошибок"""
        query = update.callback_query

    # Безопасный ответ на callback query
        try:
            await query.answer()
        except Exception as e:
            logger.warning(f"Не удалось ответить на callback query: {e}")
        # Продолжаем выполнение, это не критично

        try:
            if query.data == 'book_appointment':
                await self.show_available_dates(update, context)
            elif query.data == 'processing':
                await query.answer("Идёт обработка вашего запроса...")
            elif query.data.startswith('select_date_'):
                await self.show_available_times(update, context)
            elif query.data.startswith('select_time_'):
                await self.prepare_booking(update, context)
            elif query.data == 'confirm_booking':
                await self.confirm_booking(update, context)
            elif query.data == 'my_bookings':
                await self.my_bookings(update, context)
            elif query.data == 'help':
                await self.help_command(update, context)
            elif query.data == 'back_to_main':
                # Очищаем сессию пользователя при возврате в главное меню
                user = update.effective_user
                if user.id in self.user_sessions:
                    del self.user_sessions[user.id]

                await query.edit_message_text(
                    MESSAGES['welcome'],
                    reply_markup=self.keyboards.main_menu()
                )
            else:
                logger.warning(f"Неизвестная команда: {query.data}")

        except Exception as e:
            logger.error(f"Ошибка обработки кнопки {query.data}: {e}")
            try:
                await query.edit_message_text(
                    "❌ Произошла ошибка. Возвращаюсь в главное меню.",
                    reply_markup=self.keyboards.main_menu()
                )
            except:
                # Если не удалось отредактировать сообщение, отправляем новое
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Произошла ошибка. Используйте /start для перезапуска.",
                    reply_markup=self.keyboards.main_menu()
                )