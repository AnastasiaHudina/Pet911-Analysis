import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

# Настройка отображения
plt.style.use('default')
sns.set_palette("husl")


def load_and_prepare_data(file_path, dataset_type):
    """Загрузка и подготовка данных"""
    df = pd.read_csv(file_path)

    # Функция для преобразования русских дат
    def parse_russian_date(date_str):
        try:
            russian_to_english = {
                'пн': 'Mon', 'вт': 'Tue', 'ср': 'Wed', 'чт': 'Thu',
                'пт': 'Fri', 'сб': 'Sat', 'вс': 'Sun'
            }

            parts = date_str.split(', ')
            if len(parts) == 2:
                day_abbr = parts[0].strip()
                date_part = parts[1].strip()

                if day_abbr in russian_to_english:
                    english_abbr = russian_to_english[day_abbr]
                    english_date_str = f"{english_abbr}, {date_part}"
                    return pd.to_datetime(english_date_str, format='%a, %d.%m.%Y')

            return pd.to_datetime(date_str, errors='coerce')
        except:
            return pd.NaT

    # Применяем функцию преобразования дат
    df['дата_публикации'] = df['дата_публикации'].apply(parse_russian_date)

    # Удаляем строки с некорректными датами
    df_clean = df.dropna(subset=['дата_публикации'])

    return df_clean


def prepare_monthly_data(df):
    """Подготовка месячных данных"""
    if df is None or len(df) == 0:
        return None

    # Создаем копию и устанавливаем дату как индекс
    df_temp = df.copy()
    df_temp.set_index('дата_публикации', inplace=True)

    # Агрегируем по месяцам
    monthly_data = df_temp.resample('M').size()
    monthly_data = monthly_data.to_frame(name='количество_заявок')

    # Добавляем месяц и год для удобства
    monthly_data['год'] = monthly_data.index.year
    monthly_data['месяц'] = monthly_data.index.month

    return monthly_data


def prepare_weekly_data(df):
    """Подготовка недельных данных"""
    if df is None or len(df) == 0:
        return None

    df_temp = df.copy()
    df_temp.set_index('дата_публикации', inplace=True)

    # Агрегируем по неделям
    weekly_data = df_temp.resample('W').size()
    weekly_data = weekly_data.to_frame(name='количество_заявок')

    return weekly_data


def prepare_daily_data(df):
    """Подготовка дневных данных по дням недели"""
    if df is None or len(df) == 0:
        return None

    df_temp = df.copy()

    # Добавляем день недели
    df_temp['день_недели'] = df_temp['дата_публикации'].dt.dayofweek
    df_temp['название_дня'] = df_temp['день_недели'].map({
        0: 'Понедельник', 1: 'Вторник', 2: 'Среда',
        3: 'Четверг', 4: 'Пятница', 5: 'Суббота', 6: 'Воскресенье'
    })

    # Группируем по дням недели
    daily_data = df_temp.groupby(['день_недели', 'название_дня']).size()
    daily_data = daily_data.to_frame(name='количество_заявок').reset_index()

    return daily_data


def create_daily_analysis(daily_data, dataset_type, df, output_prefix=''):
    """Анализ данных по дням недели"""

    title_map = {
        'lost': 'поиска питомцев',
        'found': 'поиска хозяев'
    }

    dataset_title = title_map[dataset_type]

    if daily_data is None or len(daily_data) == 0:
        return

    plt.figure(figsize=(10, 6))

    # Сортируем по дню недели
    daily_data = daily_data.sort_values('день_недели')

    bars = plt.bar(daily_data['название_дня'], daily_data['количество_заявок'],
                   color=['lightblue' if i < 5 else 'orange' for i in range(7)],
                   alpha=0.7)
    plt.title(f'Распределение заявок по дням недели ({dataset_title})',
              fontsize=14, fontweight='bold')
    plt.ylabel('Количество заявок')
    plt.grid(True, alpha=0.3)

    # Добавляем значения на столбцы
    for bar, value in zip(bars, daily_data['количество_заявок']):
        plt.text(bar.get_x() + bar.get_width() / 2, value + max(daily_data['количество_заявок']) * 0.01,
                 f'{value}', ha='center', va='bottom', fontweight='bold')

    # Добавляем пояснение
    start_date = df['дата_публикации'].min().strftime('%d.%m.%Y')
    end_date = df['дата_публикации'].max().strftime('%d.%m.%Y')
    total_days = (df['дата_публикации'].max() - df['дата_публикации'].min()).days + 1
    explanation = (f"Анализ основан на данных с {start_date} по {end_date} "
                   f"({total_days} дней)\n"
                   f"Значения показывают общее количество заявок по каждому дню недели за весь период")
    plt.figtext(0.02, 0.02, explanation, fontsize=9, style='italic',
                bbox={'facecolor': 'lightgray', 'alpha': 0.7, 'pad': 5})

    plt.tight_layout()
    plt.savefig(f'{output_prefix}daily_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()


def create_weekly_analysis(weekly_data, dataset_type, df, output_prefix=''):
    """Анализ недельных данных"""

    title_map = {
        'lost': 'поиска питомцев',
        'found': 'поиска хозяев'
    }

    dataset_title = title_map[dataset_type]

    if weekly_data is None or len(weekly_data) < 2:
        return

    plt.figure(figsize=(12, 6))

    # Форматируем даты для отображения (начало недели - конец недели)
    # Учитываем разные годы в данных
    def format_week_range(start_date):
        end_date = start_date + timedelta(days=6)
        # Если неделя в пределах одного года
        if start_date.year == end_date.year:
            return f"{start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m')}"
        else:
            # Если неделя переходит через год
            return f"{start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m.%Y')}"

    weekly_data['метка'] = weekly_data.index.map(format_week_range)

    plt.plot(weekly_data['метка'], weekly_data['количество_заявок'],
             marker='o', linewidth=2, color='green', alpha=0.7)
    plt.title(f'Динамика заявок по неделям ({dataset_title})',
              fontsize=14, fontweight='bold')
    plt.xlabel('Неделя')
    plt.ylabel('Количество заявок')

    # Уменьшаем количество меток на оси X для лучшей читаемости
    n = len(weekly_data)
    step = max(1, n // 10)  # Показываем примерно 10 меток
    plt.xticks(range(0, n, step), weekly_data['метка'].iloc[::step], rotation=45)

    plt.grid(True, alpha=0.3)

    # Добавляем пояснение
    start_date = df['дата_публикации'].min().strftime('%d.%m.%Y')
    end_date = df['дата_публикации'].max().strftime('%d.%m.%Y')
    total_weeks = len(weekly_data)
    explanation = (f"Анализ основан на данных с {start_date} по {end_date} "
                   f"({total_weeks} недель)\n"
                   f"Каждая точка показывает количество заявок за неделю")
    plt.figtext(0.02, 0.02, explanation, fontsize=9, style='italic',
                bbox={'facecolor': 'lightgray', 'alpha': 0.7, 'pad': 5})

    plt.tight_layout()
    plt.savefig(f'{output_prefix}weekly_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()


def create_monthly_forecast(monthly_data, dataset_type, df, output_prefix=''):
    """Прогноз на 3 месяца вперед"""

    title_map = {
        'lost': 'поиска питомцев',
        'found': 'поиска хозяев'
    }

    dataset_title = title_map[dataset_type]

    if monthly_data is None or len(monthly_data) < 1:
        return

    # Создаем визуализацию
    plt.figure(figsize=(12, 6))

    # Подготовка данных для прогноза
    last_date = monthly_data.index[-1]
    forecast_months = []

    for i in range(1, 4):
        next_month = last_date + pd.DateOffset(months=i)
        forecast_months.append(next_month)

    # Простой прогноз: среднее значение предыдущих месяцев
    avg_requests = monthly_data['количество_заявок'].mean()
    # Добавляем небольшую случайную вариацию для реалистичности
    np.random.seed(42)  # для воспроизводимости
    forecast_values = [avg_requests * (0.9 + 0.2 * np.random.random()) for _ in range(3)]

    # Подготовка данных для графика прогноза
    months_names = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн',
                    'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']

    historical_labels = [f"{months_names[date.month - 1]} {date.year}" for date in monthly_data.index]
    forecast_labels = [f"{months_names[date.month - 1]} {date.year}" for date in forecast_months]

    all_labels = historical_labels + forecast_labels
    all_values = monthly_data['количество_заявок'].tolist() + forecast_values

    # График с фактическими данными и прогнозом
    colors = ['lightblue'] * len(monthly_data) + ['lightcoral'] * len(forecast_months)

    bars = plt.bar(range(len(all_labels)), all_values, color=colors, alpha=0.7)
    plt.title(f'Прогноз количества заявок на 3 месяца ({dataset_title})',
              fontsize=14, fontweight='bold')
    plt.ylabel('Количество заявок')
    plt.xticks(range(len(all_labels)), all_labels, rotation=45)
    plt.grid(True, alpha=0.3)

    # Добавляем разделительную линию между фактом и прогнозом
    plt.axvline(x=len(monthly_data) - 0.5, color='red', linestyle='--', alpha=0.7)
    plt.text(len(monthly_data) - 0.5, max(all_values) * 0.9, 'Прогноз',
             rotation=90, ha='right', va='top', color='red', fontweight='bold')

    # Добавляем значения на столбцы
    for i, value in enumerate(all_values):
        plt.text(i, value + max(all_values) * 0.01, f'{value:.0f}',
                 ha='center', va='bottom', fontweight='bold')

    # Добавляем пояснение
    start_date = df['дата_публикации'].min().strftime('%d.%m.%Y')
    end_date = df['дата_публикации'].max().strftime('%d.%m.%Y')
    total_months = len(monthly_data)
    explanation = (f"Анализ основан на данных с {start_date} по {end_date} "
                   f"({total_months} месяцев)\n"
                   f"Прогноз построен на основе среднемесячных значений с учетом случайных вариаций")
    plt.figtext(0.02, 0.02, explanation, fontsize=9, style='italic',
                bbox={'facecolor': 'lightgray', 'alpha': 0.7, 'pad': 5})

    plt.tight_layout()
    plt.savefig(f'{output_prefix}monthly_forecast.png', dpi=300, bbox_inches='tight')
    plt.close()


def analyze_dataset(file_path, dataset_type, output_prefix=''):
    """Полный анализ временных рядов для одного датасета"""

    # Загрузка данных
    df = load_and_prepare_data(file_path, dataset_type)

    if df is None or len(df) == 0:
        print(f"Нет данных для анализа: {file_path}")
        return

    # Подготовка данных
    monthly_data = prepare_monthly_data(df)
    weekly_data = prepare_weekly_data(df)
    daily_data = prepare_daily_data(df)

    # Создание визуализаций в правильном порядке
    create_daily_analysis(daily_data, dataset_type, df, output_prefix)
    create_weekly_analysis(weekly_data, dataset_type, df, output_prefix)
    create_monthly_forecast(monthly_data, dataset_type, df, output_prefix)


def main_analysis():
    """Основная функция анализа"""

    # Анализ для lost датасета (поиск питомцев)
    analyze_dataset('Dataset_final_Pet911_lost.csv', 'lost', output_prefix='lost_')

    # Анализ для found датасета (поиск хозяев)
    analyze_dataset('dataset_final_Pet911_found.csv', 'found', output_prefix='found_')


if __name__ == "__main__":
    main_analysis()