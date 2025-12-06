import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime, timedelta
import warnings
import os

warnings.filterwarnings('ignore')

# Настройка отображения
plt.style.use('default')
sns.set_palette("husl")


def load_and_prepare_data(file_path):
    """Загрузка и подготовка данных"""
    try:
        # Проверяем существование файла
        if not os.path.exists(file_path):
            print(f"ОШИБКА: Файл {file_path} не найден!")
            print(f"Текущая директория: {os.getcwd()}")
            print(f"Файлы в директории: {os.listdir('.')}")
            return None

        # Пробуем разные кодировки
        encodings = ['utf-8', 'cp1251', 'latin1']
        df = None

        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                print(f"Файл успешно загружен с кодировкой {encoding}")
                break
            except UnicodeDecodeError:
                continue

        if df is None:
            print("ОШИБКА: Не удалось загрузить файл ни с одной кодировкой")
            return None

        print(f"Загружено записей: {len(df)}")
        print(f"Столбцы в данных: {list(df.columns)}")

        # Функция для преобразования русских дат
        def parse_russian_date(date_str):
            try:
                # Словарь для преобразования русских сокращений в английские
                russian_to_english = {
                    'пн': 'Mon', 'вт': 'Tue', 'ср': 'Wed', 'чт': 'Thu',
                    'пт': 'Fri', 'сб': 'Sat', 'вс': 'Sun'
                }

                # Разделяем строку на части
                parts = date_str.split(', ')
                if len(parts) == 2:
                    day_abbr = parts[0].strip()
                    date_part = parts[1].strip()

                    # Преобразуем русское сокращение в английское
                    if day_abbr in russian_to_english:
                        english_abbr = russian_to_english[day_abbr]
                        # Собираем обратно в строку с английским сокращением
                        english_date_str = f"{english_abbr}, {date_part}"
                        return pd.to_datetime(english_date_str, format='%a, %d.%m.%Y')

                # Если не удалось распарсить особым способом, пробуем стандартный
                return pd.to_datetime(date_str, errors='coerce')
            except:
                return pd.NaT

        # Применяем функцию преобразования дат
        df['дата_публикации'] = df['дата_публикации'].apply(parse_russian_date)

        # Проверяем результат преобразования даты
        nan_dates = df['дата_публикации'].isna().sum()
        if nan_dates > 0:
            print(f"Предупреждение: {nan_dates} записей с некорректными датами")
            print("Примеры некорректных дат:")
            print(df[df['дата_публикации'].isna()]['дата_публикации'].head())

        # Удаляем строки с некорректными датами
        df_clean = df.dropna(subset=['дата_публикации'])
        print(f"Осталось записей после очистки дат: {len(df_clean)}")

        if len(df_clean) > 0:
            print(
                f"Диапазон дат в данных: от {df_clean['дата_публикации'].min()} до {df_clean['дата_публикации'].max()}")

        return df_clean

    except Exception as e:
        print(f"ОШИБКА при загрузке данных: {e}")
        import traceback
        print(traceback.format_exc())
        return None


def prepare_time_series_data(df):
    """Подготовка данных временных рядов"""

    if df is None or len(df) == 0:
        print("Нет данных для анализа временных рядов")
        return None

    # Сортируем по дате
    df_sorted = df.sort_values('дата_публикации')

    # Агрегация по дням
    daily_requests = df_sorted.groupby('дата_публикации').agg({
        'id': 'count'
    }).rename(columns={'id': 'количество_заявок'})

    print(f"Уникальных дней в данных: {len(daily_requests)}")
    print(f"Диапазон дат: с {daily_requests.index.min()} по {daily_requests.index.max()}")

    if len(daily_requests) == 0:
        print("Нет данных для анализа временных рядов")
        return None

    # Заполнение пропущенных дат
    try:
        date_range = pd.date_range(start=daily_requests.index.min(),
                                   end=daily_requests.index.max(),
                                   freq='D')
        daily_requests = daily_requests.reindex(date_range, fill_value=0)
        print(f"Полный диапазон дат с заполнением: с {date_range[0]} по {date_range[-1]}")
    except Exception as e:
        print(f"Ошибка при создании диапазона дат: {e}")
        return None

    # Добавление временных признаков
    daily_requests['день_недели'] = daily_requests.index.dayofweek
    daily_requests['день_месяца'] = daily_requests.index.day
    daily_requests['месяц'] = daily_requests.index.month
    daily_requests['день_года'] = daily_requests.index.dayofyear

    # Накопительная сумма для тренда
    daily_requests['накопленные_заявки'] = daily_requests['количество_заявок'].cumsum()

    return daily_requests


def create_seasonality_analysis(daily_data):
    """Анализ сезонности"""

    # Анализ по дням недели
    weekday_means = daily_data.groupby('день_недели')['количество_заявок'].mean()
    days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

    # Создание визуализаций
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))

    # 1. Временной ряд заявок
    axes[0, 0].plot(daily_data.index, daily_data['количество_заявок'], marker='o', linewidth=2, color='blue')
    axes[0, 0].set_title('Количество заявок по дням', fontsize=14, fontweight='bold')
    axes[0, 0].set_xlabel('Дата')
    axes[0, 0].set_ylabel('Количество заявок')
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].tick_params(axis='x', rotation=45)

    # 2. Сезонность по дням недели
    axes[0, 1].bar(range(7), weekday_means.values, color='orange', alpha=0.7)
    axes[0, 1].set_title('Среднее количество заявок по дням недели', fontsize=14, fontweight='bold')
    axes[0, 1].set_xlabel('День недели')
    axes[0, 1].set_ylabel('Среднее количество заявок')
    axes[0, 1].set_xticks(range(7))
    axes[0, 1].set_xticklabels(days)
    axes[0, 1].grid(True, alpha=0.3)

    # Добавление значений на столбцы
    for i, v in enumerate(weekday_means.values):
        axes[0, 1].text(i, v + 0.1, f'{v:.1f}', ha='center', va='bottom')

    # 3. Накопительный тренд
    axes[1, 0].plot(daily_data.index, daily_data['накопленные_заявки'], linewidth=2, color='green')
    axes[1, 0].set_title('Накопительное количество заявок', fontsize=14, fontweight='bold')
    axes[1, 0].set_xlabel('Дата')
    axes[1, 0].set_ylabel('Накопительное количество')
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].tick_params(axis='x', rotation=45)

    # 4. Распределение заявок по дням месяца
    day_month_means = daily_data.groupby('день_месяца')['количество_заявок'].mean()
    axes[1, 1].bar(day_month_means.index, day_month_means.values, color='purple', alpha=0.7)
    axes[1, 1].set_title('Распределение заявок по дням месяца', fontsize=14, fontweight='bold')
    axes[1, 1].set_xlabel('День месяца')
    axes[1, 1].set_ylabel('Среднее количество заявок')
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('seasonality_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()

    return weekday_means


def create_forecast(daily_data, days_forecast=14):
    """Создание прогноза на будущее"""

    # Простой прогноз на основе сезонности
    weekday_means = daily_data.groupby('день_недели')['количество_заявок'].mean()

    # Создание прогноза
    last_date = daily_data.index[-1]
    future_dates = [last_date + timedelta(days=i) for i in range(1, days_forecast + 1)]

    future_forecast = []
    for date in future_dates:
        day_of_week = date.weekday()
        # Базовый прогноз на основе среднего по дню недели
        base_forecast = weekday_means.get(day_of_week, daily_data['количество_заявок'].mean())
        # Добавляем случайные колебания (10% от значения)
        fluctuation = np.random.normal(0, base_forecast * 0.1)
        forecast = max(0, base_forecast + fluctuation)
        future_forecast.append(round(forecast))

    # Визуализация прогноза
    plt.figure(figsize=(15, 8))

    # Исторические данные (последние 30 дней или все доступные)
    historical_days = min(30, len(daily_data))
    historical_data = daily_data.tail(historical_days)

    # График исторических данных и прогноза
    plt.plot(historical_data.index, historical_data['количество_заявок'],
             label='Исторические данные', marker='o', linewidth=2, color='blue')

    plt.plot(future_dates, future_forecast,
             label='Прогноз', marker='s', linestyle='--', linewidth=2, color='red')

    plt.title(f'Прогноз количества заявок на {days_forecast} дней', fontsize=16, fontweight='bold')
    plt.xlabel('Дата')
    plt.ylabel('Количество заявок')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)

    # Добавление значений на точки прогноза
    for i, (date, value) in enumerate(zip(future_dates, future_forecast)):
        plt.annotate(f'{value}', (date, value),
                     textcoords="offset points", xytext=(0, 10), ha='center')

    plt.tight_layout()
    plt.savefig('forecast_visualization.png', dpi=300, bbox_inches='tight')
    plt.show()

    return future_dates, future_forecast


def generate_recommendations(daily_data, future_forecast):
    """Генерация рекомендаций для волонтерских организаций"""

    # Анализ данных
    avg_daily = daily_data['количество_заявок'].mean()
    max_daily = daily_data['количество_заявок'].max()

    # Находим пиковый день недели
    weekday_means = daily_data.groupby('день_недели')['количество_заявок'].mean()
    if not weekday_means.empty:
        peak_day_idx = weekday_means.idxmax()
        days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        peak_day = days[peak_day_idx]
    else:
        peak_day = "не определен"

    # Прогноз на следующую неделю
    next_week_forecast = sum(future_forecast[:7])

    # Создание отчета
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axis('tight')
    ax.axis('off')

    # Данные для таблицы
    recommendations = [
        ['Средняя дневная нагрузка', f'{avg_daily:.1f} заявок'],
        ['Максимальная дневная нагрузка', f'{max_daily:.0f} заявок'],
        ['Пиковый день недели', peak_day],
        ['Прогноз на след. неделю', f'~{next_week_forecast:.0f} заявок'],
        ['Рекомендуемый запас ресурсов', f'на {max_daily:.0f}+ заявок'],
        ['Период повышенной готовности', f'{peak_day}']
    ]

    # Создание таблицы
    table = ax.table(cellText=recommendations,
                     colLabels=['Параметр', 'Рекомендация'],
                     cellLoc='center',
                     loc='center',
                     bbox=[0.1, 0.2, 0.8, 0.6])

    # Стилизация таблицы
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 2)

    # Цветовое оформление
    for i in range(len(recommendations) + 1):
        for j in range(2):
            if i == 0:  # Заголовок
                table[(i, j)].set_facecolor('#2E86AB')
                table[(i, j)].set_text_props(weight='bold', color='white')
            else:  # Данные
                table[(i, j)].set_facecolor('#F0F0F0')
                if 'Прогноз' in recommendations[i - 1][0] or 'Рекомендуемый' in recommendations[i - 1][0]:
                    table[(i, j)].set_facecolor('#FFE5D9')  # Выделение важных рекомендаций

    plt.title('Рекомендации для волонтерских организаций\nпо планированию нагрузки',
              fontsize=16, fontweight='bold', pad=30)

    plt.tight_layout()
    plt.savefig('volunteer_recommendations.png', dpi=300, bbox_inches='tight')
    plt.show()

    # Вывод в консоль
    print("\n" + "=" * 60)
    print("РЕКОМЕНДАЦИИ ДЛЯ ВОЛОНТЕРСКИХ ОРГАНИЗАЦИЙ")
    print("=" * 60)
    print(f"• Средняя дневная нагрузка: {avg_daily:.1f} заявок")
    print(f"• Максимальная дневная нагрузка: {max_daily:.0f} заявок")
    print(f"• Пиковый день недели: {peak_day}")
    print(f"• Прогноз на следующую неделю: ~{next_week_forecast:.0f} заявок")
    print(f"• Рекомендуемый запас ресурсов: на {max_daily:.0f}+ заявок")
    print(f"• Период повышенной готовности: {peak_day}")
    print("=" * 60)


def main_forecast():
    """Основная функция прогнозирования"""

    print("Анализ временных рядов и прогнозирование нагрузки...")
    print("=" * 50)

    # Загрузка данных - используем относительный путь
    file_path = 'pets_dataset_2025.csv'
    print(f"Поиск файла: {file_path}")

    df = load_and_prepare_data(file_path)

    if df is None or len(df) == 0:
        print("Не удалось загрузить данные. Проверьте:")
        print("1. Наличие файла pets_dataset_2025.csv в той же папке, что и скрипт")
        print("2. Правильность формата данных в файле")
        return

    print(f"Период данных: с {df['дата_публикации'].min()} по {df['дата_публикации'].max()}")

    # Подготовка временных рядов
    daily_data = prepare_time_series_data(df)

    if daily_data is None:
        print("Недостаточно данных для анализа временных рядов")
        return

    print(f"Дней для анализа: {len(daily_data)}")
    print(f"Общее количество заявок: {daily_data['количество_заявок'].sum()}")

    # Анализ сезонности
    print("\nАнализ сезонности...")
    weekday_means = create_seasonality_analysis(daily_data)

    # Создание прогноза
    print("\nСоздание прогноза...")
    future_dates, future_forecast = create_forecast(daily_data)

    # Генерация рекомендаций
    print("\nФормирование рекомендаций...")
    generate_recommendations(daily_data, future_forecast)

    # Вывод прогноза
    print("\nПРОГНОЗ НА 14 ДНЕЙ:")
    print("-" * 40)
    for date, forecast in zip(future_dates, future_forecast):
        print(f"  {date.strftime('%d.%m.%Y')}: {forecast} заявок")


if __name__ == "__main__":
    main_forecast()