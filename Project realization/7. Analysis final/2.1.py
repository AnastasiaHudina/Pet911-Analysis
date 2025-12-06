import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import warnings
import os

warnings.filterwarnings('ignore')

# Создаем папку для результатов
os.makedirs('Результаты 2 главы анализа', exist_ok=True)

def load_data(file_path):
    """Загрузка данных"""
    try:
        if not os.path.exists(file_path):
            print(f"ОШИБКА: Файл {file_path} не найден!")
            return None

        encodings = ['utf-8', 'cp1251', 'latin1']
        df = None

        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue

        if df is None:
            print("ОШИБКА: Не удалось загрузить файл")
            return None

        return df

    except Exception as e:
        print(f"ОШИБКА при загрузке данных: {e}")
        return None


def analyze_comments_correlation(df, dataset_type):
    """Анализ корреляции между комментариями и успешностью поиска"""

    df_analysis = df.copy()

    # Создаем бинарную переменную успеха в зависимости от типа датасета
    df_analysis['успех'] = 0

    if dataset_type == 'found':
        # Для найденных животных: успех = "хозяин найден"
        df_analysis.loc[df_analysis['статус'] == 'хозяин найден', 'успех'] = 1
        success_description = "100% - все объявления о найденных животных"
        display_name = "поиск хозяев"
    else:
        # Для потерянных животных: успех = "питомец найден"
        df_analysis.loc[df_analysis['статус'] == 'питомец найден', 'успех'] = 1
        success_description = "100% - все объявления о потерянных животных"
        display_name = "поиск питомца"

    # Базовая статистика
    success_stats = df_analysis.groupby('успех')['количество_комментариев'].agg(['mean', 'median', 'std', 'count'])

    # Корреляционный анализ
    correlation = df_analysis['количество_комментариев'].corr(df_analysis['успех'])

    # T-тест для проверки значимости различий
    success_comments = df_analysis[df_analysis['успех'] == 1]['количество_комментариев'].fillna(0)
    fail_comments = df_analysis[df_analysis['успех'] == 0]['количество_комментариев'].fillna(0)

    t_stat, p_value = stats.ttest_ind(success_comments, fail_comments, nan_policy='omit')

    return df_analysis, correlation, p_value, success_stats, success_description, display_name


def create_mean_comments_chart(success_stats, display_name):
    """Создание диаграммы среднего количества комментариев"""

    plt.figure(figsize=(10, 7))

    categories = ['Не найдено', 'Найдено']
    means = [success_stats.loc[0, 'mean'], success_stats.loc[1, 'mean']]
    means = [0 if pd.isna(x) else x for x in means]

    bars = plt.bar(categories, means, color=['lightcoral', 'lightgreen'], alpha=0.7, width=0.6)

    title = f'Среднее количество комментариев ({display_name})'
    plt.title(title, fontsize=14, fontweight='bold')
    plt.ylabel('Среднее количество комментариев')
    plt.grid(True, alpha=0.3, axis='y')

    # Добавление значений на столбцы
    for bar, value in zip(bars, means):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                 f'{value:.1f}', ha='center', va='bottom', fontsize=12, fontweight='bold')

    plt.tight_layout()
    plt.savefig(f'Результаты 2 главы анализа/2.1.1. Среднее количество комментариев для {display_name}.png', dpi=300, bbox_inches='tight')
    plt.close()


def create_success_rate_by_comments_chart(df_analysis, display_name, success_description):
    """Создание диаграммы доли успешных по группам комментариев"""

    # Создаем группы комментариев
    df_analysis['группа_комментариев'] = pd.cut(df_analysis['количество_комментариев'],
                                                bins=[-1, 0, 2, 5, 10, 100],
                                                labels=['0', '1-2', '3-5', '6-10', '10+'])

    success_rate_by_group = df_analysis.groupby('группа_комментариев')['успех'].mean() * 100
    success_rate_by_group = success_rate_by_group.fillna(0)

    plt.figure(figsize=(12, 7))

    bars = plt.bar(range(len(success_rate_by_group)), success_rate_by_group.values,
                   color='lightseagreen', alpha=0.7, width=0.6)

    title = f'Доля успешных поисков по группам комментариев ({display_name})'
    plt.title(title, fontsize=14, fontweight='bold')
    plt.xlabel('Количество комментариев')
    plt.ylabel('Доля успешных поисков (%)')
    plt.xticks(range(len(success_rate_by_group)), success_rate_by_group.index)
    plt.grid(True, alpha=0.3, axis='y')

    # Добавление значений на столбцы
    for bar, value in zip(bars, success_rate_by_group.values):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f'{value:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')

    # Добавляем поясняющую подпись (только на этой диаграмме с процентами)
    plt.figtext(0.02, 0.02, f"Проценты рассчитываются в рамках каждой группы комментариев\n{success_description}",
                fontsize=10, style='italic',
                bbox={'facecolor': 'lightgray', 'alpha': 0.7, 'pad': 5})

    plt.tight_layout(rect=[0, 0.08, 1, 0.95])
    plt.savefig(f'Результаты 2 главы анализа/2.1.2. Зависимость успешности поиска от количества комментариев для {display_name}.png', dpi=300, bbox_inches='tight')
    plt.close()

    return success_rate_by_group


def analyze_single_dataset(file_path, dataset_type):
    """Анализ одного датасета"""

    # Загрузка данных
    df = load_data(file_path)

    if df is None:
        return

    # Анализ корреляции
    df_analysis, correlation, p_value, success_stats, success_description, display_name = analyze_comments_correlation(
        df, dataset_type)

    # Создание диаграмм
    create_mean_comments_chart(success_stats, display_name)
    success_rate_by_group = create_success_rate_by_comments_chart(df_analysis, display_name, success_description)

def main():
    """Основная функция для анализа обоих датасетов"""
    
    # Создаем папку для результатов
    os.makedirs('Результаты 2 главы анализа', exist_ok=True)

    # Анализ датасета найденных животных (поиск хозяина)
    analyze_single_dataset('dataset_final_Pet911_found.csv', 'found')

    # Анализ датасета потерянных животных (поиск питомца)
    analyze_single_dataset('Dataset_final_Pet911_lost.csv', 'lost')


if __name__ == "__main__":
    main()