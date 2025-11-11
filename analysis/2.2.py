import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
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


def analyze_publication_factors(df, dataset_type):
    """Анализ влияния фото и описания на успешность"""

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

    # Преобразуем есть_фото в числовой формат
    df_analysis['есть_фото_num'] = df_analysis['есть_фото'].astype(int)

    # Анализ по наличию фото
    photo_success = df_analysis.groupby('есть_фото_num')['успех'].agg(['mean', 'count'])

    # Анализ корреляций
    photo_corr = df_analysis['есть_фото_num'].corr(df_analysis['успех'])
    photos_count_corr = df_analysis['количество_фото'].corr(df_analysis['успех'])
    desc_length_corr = df_analysis['Длина_описания_в_словах'].corr(df_analysis['успех'])

    return df_analysis, photo_success, photo_corr, photos_count_corr, desc_length_corr, success_description, display_name


def create_photo_success_chart(photo_success, display_name, success_description):
    """Создание диаграммы успешности по наличию фото"""

    plt.figure(figsize=(10, 7))

    categories = ['Без фото', 'С фото']

    # Проверяем на NaN и заменяем на 0
    success_rates = [
        (photo_success.loc[0, 'mean'] * 100) if 0 in photo_success.index else 0,
        (photo_success.loc[1, 'mean'] * 100) if 1 in photo_success.index else 0
    ]

    bars = plt.bar(categories, success_rates, color=['lightcoral', 'lightgreen'], alpha=0.7, width=0.6)
    plt.title(f'Успешность поиска по наличию фото ({display_name})', fontsize=14, fontweight='bold')
    plt.ylabel('Доля успешных поисков (%)')
    plt.grid(True, alpha=0.3, axis='y')

    # Добавление значений на столбцы
    for bar, rate in zip(bars, success_rates):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f'{rate:.1f}%', ha='center', va='bottom', fontsize=12, fontweight='bold')

    # Добавляем поясняющую подпись
    plt.figtext(0.02, 0.02, success_description,
                fontsize=10, style='italic',
                bbox={'facecolor': 'lightgray', 'alpha': 0.7, 'pad': 5})

    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    plt.savefig(f'photo_success_{display_name.replace(" ", "_")}.png', dpi=300, bbox_inches='tight')
    plt.close()


def create_photos_count_chart(df_analysis, display_name, success_description):
    """Создание диаграммы успешности по количеству фото"""

    # Создаем группы по количеству фото
    df_analysis['группа_фото'] = pd.cut(df_analysis['количество_фото'],
                                        bins=[-1, 0, 1, 3, 10, 100],
                                        labels=['0 фото', '1 фото', '2-3 фото', '4-10 фото', '10+ фото'])

    photos_success = df_analysis.groupby('группа_фото')['успех'].mean() * 100

    # Заменяем NaN на 0
    photos_success = photos_success.fillna(0)

    plt.figure(figsize=(12, 7))

    bars = plt.bar(range(len(photos_success)), photos_success.values,
                   color='skyblue', alpha=0.7, width=0.6)
    plt.title(f'Успешность поиска по количеству фото ({display_name})', fontsize=14, fontweight='bold')
    plt.xlabel('Количество фото')
    plt.ylabel('Доля успешных поисков (%)')
    plt.xticks(range(len(photos_success)), photos_success.index, rotation=45)
    plt.grid(True, alpha=0.3, axis='y')

    # Добавление значений на столбцы
    for bar, value in zip(bars, photos_success.values):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f'{value:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')

    # Добавляем поясняющую подпись
    plt.figtext(0.02, 0.02, success_description,
                fontsize=10, style='italic',
                bbox={'facecolor': 'lightgray', 'alpha': 0.7, 'pad': 5})

    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    plt.savefig(f'photos_count_{display_name.replace(" ", "_")}.png', dpi=300, bbox_inches='tight')
    plt.close()

    return photos_success


def create_description_length_chart(df_analysis, display_name, success_description):
    """Создание диаграммы успешности по длине описания"""

    # Создаем группы по длине описания (количество слов)
    desc_stats = df_analysis['Длина_описания_в_словах'].describe()

    # Создаем группы на основе квартилей
    q1 = desc_stats['25%']
    q2 = desc_stats['50%']
    q3 = desc_stats['75%']

    bins = [-1, q1, q2, q3, df_analysis['Длина_описания_в_словах'].max()]
    labels = [f'0-{int(q1)} слов', f'{int(q1) + 1}-{int(q2)} слов',
              f'{int(q2) + 1}-{int(q3)} слов', f'{int(q3) + 1}+ слов']

    df_analysis['группа_описания'] = pd.cut(df_analysis['Длина_описания_в_словах'],
                                            bins=bins,
                                            labels=labels)

    desc_success = df_analysis.groupby('группа_описания')['успех'].mean() * 100

    # Заменяем NaN на 0
    desc_success = desc_success.fillna(0)

    plt.figure(figsize=(12, 7))

    bars = plt.bar(range(len(desc_success)), desc_success.values,
                   color='lightseagreen', alpha=0.7, width=0.6)
    plt.title(f'Успешность поиска по длине описания ({display_name})', fontsize=14, fontweight='bold')
    plt.xlabel('Длина описания (количество слов)')
    plt.ylabel('Доля успешных поисков (%)')
    plt.xticks(range(len(desc_success)), desc_success.index, rotation=45)
    plt.grid(True, alpha=0.3, axis='y')

    # Добавление значений на столбцы
    for bar, value in zip(bars, desc_success.values):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f'{value:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')

    # Добавляем поясняющую подпись
    plt.figtext(0.02, 0.02, success_description,
                fontsize=10, style='italic',
                bbox={'facecolor': 'lightgray', 'alpha': 0.7, 'pad': 5})

    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    plt.savefig(f'description_length_{display_name.replace(" ", "_")}.png', dpi=300, bbox_inches='tight')
    plt.close()

    return desc_success


def create_combined_factors_chart(df_analysis, display_name, success_description):
    """Создание диаграммы успешности по комбинации факторов (фото + описание)"""

    # Создаем комбинированные группы на основе количества фото и длины описания
    median_desc = df_analysis['Длина_описания_в_словах'].median()

    # Определяем пороги для количества фото
    conditions = [
        (df_analysis['количество_фото'] == 0) & (df_analysis['Длина_описания_в_словах'] <= median_desc),
        (df_analysis['количество_фото'] == 0) & (df_analysis['Длина_описания_в_словах'] > median_desc),
        (df_analysis['количество_фото'] == 1) & (df_analysis['Длина_описания_в_словах'] <= median_desc),
        (df_analysis['количество_фото'] == 1) & (df_analysis['Длина_описания_в_словах'] > median_desc),
        (df_analysis['количество_фото'] >= 2) & (df_analysis['Длина_описания_в_словах'] <= median_desc),
        (df_analysis['количество_фото'] >= 2) & (df_analysis['Длина_описания_в_словах'] > median_desc)
    ]

    choices = [
        f'0 фото, ≤{int(median_desc)} слов',
        f'0 фото, >{int(median_desc)} слов',
        f'1 фото, ≤{int(median_desc)} слов',
        f'1 фото, >{int(median_desc)} слов',
        f'2+ фото, ≤{int(median_desc)} слов',
        f'2+ фото, >{int(median_desc)} слов'
    ]

    df_analysis['комбинированная_группа'] = np.select(conditions, choices, default='Другое')

    combined_success = df_analysis.groupby('комбинированная_группа')['успех'].agg(['mean', 'count'])
    combined_success = combined_success.sort_values('mean', ascending=False)

    # Заменяем NaN на 0
    combined_success['mean'] = combined_success['mean'].fillna(0) * 100

    plt.figure(figsize=(14, 8))

    colors = ['lightcoral', 'lightcoral', 'orange', 'orange', 'lightgreen', 'lightgreen']
    bars = plt.bar(range(len(combined_success)), combined_success['mean'],
                   color=colors[:len(combined_success)], alpha=0.7, width=0.6)

    plt.title(f'Успешность поиска по комбинации факторов\n(количество фото + длина описания) ({display_name})',
              fontsize=14, fontweight='bold')
    plt.xlabel('Комбинация факторов')
    plt.ylabel('Доля успешных поисков (%)')
    plt.xticks(range(len(combined_success)), combined_success.index, rotation=45, ha='right')
    plt.grid(True, alpha=0.3, axis='y')

    # Добавление значений и количества наблюдений
    for i, (bar, (group, row)) in enumerate(zip(bars, combined_success.iterrows())):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f'{row["mean"]:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Добавляем поясняющую подпись (только про 100%, без упоминания цветов)
    plt.figtext(0.02, 0.02, success_description,
                fontsize=10, style='italic',
                bbox={'facecolor': 'lightgray', 'alpha': 0.7, 'pad': 5})

    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    plt.savefig(f'combined_factors_{display_name.replace(" ", "_")}.png', dpi=300, bbox_inches='tight')
    plt.close()

    return combined_success


def analyze_single_dataset_publication(file_path, dataset_type):
    """Анализ одного датасета для публикационных факторов"""

    # Загрузка данных
    df = load_data(file_path)

    if df is None:
        return

    # Анализ факторов публикации
    df_analysis, photo_success, photo_corr, photos_count_corr, desc_length_corr, success_description, display_name = analyze_publication_factors(
        df, dataset_type)

    # Создание четырех диаграмм
    create_photo_success_chart(photo_success, display_name, success_description)
    photos_success = create_photos_count_chart(df_analysis, display_name, success_description)
    desc_success = create_description_length_chart(df_analysis, display_name, success_description)
    combined_success = create_combined_factors_chart(df_analysis, display_name, success_description)


def main_publication_analysis():
    """Основная функция анализа типов публикаций"""

    # Анализ датасета найденных животных (поиск хозяина)
    analyze_single_dataset_publication('dataset_final_Pet911_found.csv', 'found')

    # Анализ датасета потерянных животных (поиск питомца)
    analyze_single_dataset_publication('Dataset_final_Pet911_lost.csv', 'lost')


if __name__ == "__main__":
    main_publication_analysis()