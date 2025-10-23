import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import warnings
import os

warnings.filterwarnings('ignore')


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
                print(f"Файл успешно загружен с кодировкой {encoding}")
                break
            except UnicodeDecodeError:
                continue

        if df is None:
            print("ОШИБКА: Не удалось загрузить файл")
            return None

        print(f"Загружено записей: {len(df)}")
        return df

    except Exception as e:
        print(f"ОШИБКА при загрузке данных: {e}")
        return None


def analyze_comments_correlation(df):
    """Анализ корреляции между комментариями и успешностью поиска"""

    df_analysis = df.copy()

    # Создаем бинарную переменную успеха
    df_analysis['успех'] = 0
    df_analysis.loc[
        ((df_analysis['тип_объявления'] == 'потерян') & (df_analysis['статус_поиска'] == 'найден')) |
        ((df_analysis['тип_объявления'] == 'найден') & (df_analysis['статус_поиска'] == 'хозяин найден')),
        'успех'
    ] = 1

    print("=" * 60)
    print("АНАЛИЗ КОРРЕЛЯЦИИ: КОММЕНТАРИИ И УСПЕШНОСТЬ ПОИСКА")
    print("=" * 60)

    # Базовая статистика
    total_ads = len(df_analysis)
    success_ads = df_analysis['успех'].sum()
    success_rate = success_ads / total_ads * 100

    print(f"Всего объявлений: {total_ads}")
    print(f"Успешных объявлений: {success_ads} ({success_rate:.1f}%)")
    print(f"Среднее количество комментариев: {df_analysis['количество_комментариев'].mean():.2f}")

    # Статистика по успешным/неуспешным объявлениям
    success_stats = df_analysis.groupby('успех')['количество_комментариев'].agg(['mean', 'median', 'std', 'count'])
    print("\nСтатистика комментариев по успешности:")
    print(success_stats)

    # Корреляционный анализ
    correlation = df_analysis['количество_комментариев'].corr(df_analysis['успех'])
    print(f"\nКорреляция между комментариями и успехом: {correlation:.3f}")

    # T-тест для проверки значимости различий
    success_comments = df_analysis[df_analysis['успех'] == 1]['количество_комментариев']
    fail_comments = df_analysis[df_analysis['успех'] == 0]['количество_комментариев']

    # Заменяем NaN значения на 0 для статистического теста
    success_comments = success_comments.fillna(0)
    fail_comments = fail_comments.fillna(0)

    t_stat, p_value = stats.ttest_ind(success_comments, fail_comments, nan_policy='omit')
    print(f"T-тест: t={t_stat:.3f}, p-value={p_value:.3f}")

    if p_value < 0.05:
        print("Различия СТАТИСТИЧЕСКИ ЗНАЧИМЫ (p < 0.05)")
    else:
        print("Различия НЕ значимы (p >= 0.05)")

    return df_analysis, correlation, p_value, success_stats


def create_mean_comments_chart(success_stats):
    """Создание диаграммы среднего количества комментариев"""

    plt.figure(figsize=(8, 6))

    categories = ['Не найдено', 'Найдено']
    means = [success_stats.loc[0, 'mean'], success_stats.loc[1, 'mean']]

    # Проверяем на NaN и заменяем на 0
    means = [0 if pd.isna(x) else x for x in means]

    bars = plt.bar(categories, means, color=['lightcoral', 'lightgreen'], alpha=0.7, width=0.6)
    plt.title('Среднее количество комментариев', fontsize=14, fontweight='bold')
    plt.ylabel('Среднее количество комментариев')
    plt.grid(True, alpha=0.3, axis='y')

    # Добавление значений на столбцы
    for bar, value in zip(bars, means):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                 f'{value:.1f}', ha='center', va='bottom', fontsize=12, fontweight='bold')

    plt.tight_layout()
    plt.savefig('mean_comments_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()


def create_success_rate_by_comments_chart(df_analysis):
    """Создание диаграммы доли успешных по группам комментариев"""

    # Создаем группы комментариев
    df_analysis['группа_комментариев'] = pd.cut(df_analysis['количество_комментариев'],
                                                bins=[-1, 0, 2, 5, 10, 100],
                                                labels=['0', '1-2', '3-5', '6-10', '10+'])

    success_rate_by_group = df_analysis.groupby('группа_комментариев')['успех'].mean() * 100

    # Заменяем NaN на 0
    success_rate_by_group = success_rate_by_group.fillna(0)

    plt.figure(figsize=(10, 6))

    bars = plt.bar(range(len(success_rate_by_group)), success_rate_by_group.values,
                   color='lightseagreen', alpha=0.7, width=0.6)
    plt.title('Доля успешных поисков по группам комментариев', fontsize=14, fontweight='bold')
    plt.xlabel('Количество комментариев')
    plt.ylabel('Доля успешных поисков (%)')
    plt.xticks(range(len(success_rate_by_group)), success_rate_by_group.index)
    plt.grid(True, alpha=0.3, axis='y')

    # Добавление значений на столбцы
    for bar, value in zip(bars, success_rate_by_group.values):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f'{value:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')

    plt.tight_layout()
    plt.savefig('success_rate_by_comments.png', dpi=300, bbox_inches='tight')
    plt.show()

    return success_rate_by_group


def main_comments_analysis():
    """Основная функция анализа комментариев"""

    print("Анализ корреляции комментариев и успешности поиска...")
    print("=" * 50)

    # Загрузка данных
    file_path = 'pets_dataset_2025.csv'
    df = load_data(file_path)

    if df is None:
        return

    # Анализ корреляции
    df_analysis, correlation, p_value, success_stats = analyze_comments_correlation(df)

    # Создание двух диаграмм
    print("\nСоздание диаграмм...")
    create_mean_comments_chart(success_stats)
    success_rate_by_group = create_success_rate_by_comments_chart(df_analysis)

    # Вывод результатов
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ АНАЛИЗА")
    print("=" * 60)
    print(f"• Корреляция между комментариями и успехом: {correlation:.3f}")
    print(f"• Статистическая значимость: {'ДА' if p_value < 0.05 else 'НЕТ'}")
    print(f"• Успешные объявления имеют в среднем {success_stats.loc[1, 'mean']:.1f} комментариев")
    print(f"• Неуспешные объявления имеют в среднем {success_stats.loc[0, 'mean']:.1f} комментариев")

    if not success_rate_by_group.empty:
        best_group = success_rate_by_group.idxmax()
        best_rate = success_rate_by_group.max()
        print(f"• Наивысшая доля успеха в группе: {best_group} комментариев ({best_rate:.1f}%)")


if __name__ == "__main__":
    main_comments_analysis()