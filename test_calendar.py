from datetime import datetime, timedelta
from config import WORKING_DAYS, WORKING_HOURS_START, WORKING_HOURS_END, DAYS_AHEAD_BOOKING

def test_config():
    """Тест конфигурации"""
    print("=== ТЕСТ НАСТРОЕК ===")
    print(f"Рабочие дни: {WORKING_DAYS}")
    print(f"Рабочие часы: {WORKING_HOURS_START}-{WORKING_HOURS_END}")
    print(f"Дней вперед: {DAYS_AHEAD_BOOKING}")

    current_time = datetime.now()
    print(f"Текущее время: {current_time}")

    print("\n=== ПРОВЕРКА СЛОТОВ ===")
    slots_count = 0

    for day in range(1, min(8, DAYS_AHEAD_BOOKING + 1)):  # Проверим первую неделю
        date = current_time + timedelta(days=day)

        if date.weekday() not in WORKING_DAYS:
            print(f"День {day}: {date.strftime('%Y-%m-%d %A')} - НЕРАБОЧИЙ")
            continue

        print(f"День {day}: {date.strftime('%Y-%m-%d %A')} - РАБОЧИЙ")

        for hour in range(WORKING_HOURS_START, WORKING_HOURS_END):
            slot_datetime = date.replace(hour=hour, minute=0, second=0, microsecond=0)

            if slot_datetime > current_time:
                slots_count += 1
                print(f"  Слот: {slot_datetime.strftime('%H:%M')}")

    print(f"\nВсего потенциальных слотов: {slots_count}")

    if slots_count == 0:
        print("\n❌ ПРОБЛЕМА: Нет потенциальных слотов!")
        print("Проверьте:")
        print("1. WORKING_DAYS содержит дни недели (0-6)")
        print("2. WORKING_HOURS_START < WORKING_HOURS_END")
        print("3. DAYS_AHEAD_BOOKING > 0")
    else:
        print(f"\n✅ Конфигурация выглядит правильно")

if __name__ == "__main__":
    test_config()