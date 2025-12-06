import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# Для текстовой обработки
import re
import string
from collections import Counter
from nltk.corpus import stopwords
import pymorphy3

# Для машинного обучения
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import chi2

# Настройка отображения
plt.rcParams['font.family'] = 'DejaVu Sans'
sns.set_palette("husl")
pd.set_option('display.max_columns', None)

def setup_russian_analysis():
    """Настройка инструментов для русского языка"""
    try:
        russian_stopwords = stopwords.words('russian')
    except:
        print("Внимание: не удалось загрузить стоп-слова из nltk. Используется базовый список.")
        russian_stopwords = ['и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все', 'она', 'так', 'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по', 'только', 'ее', 'мне', 'было', 'вот', 'от', 'меня', 'еще', 'нет', 'о', 'из', 'ему', 'теперь', 'когда', 'даже', 'ну', 'вдруг', 'ли', 'если', 'уже', 'или', 'ни', 'быть', 'был', 'него', 'до', 'вас', 'нибудь', 'опять', 'уж', 'вам', 'ведь', 'там', 'потом', 'себя', 'ничего', 'ей', 'может', 'они', 'тут', 'где', 'есть', 'надо', 'ней', 'для', 'мы', 'тебя', 'их', 'чем', 'была', 'сам', 'чтоб', 'без', 'будто', 'чего', 'раз', 'тоже', 'себе', 'под', 'будет', 'ж', 'тогда', 'кто', 'этот', 'того', 'потому', 'этого', 'какой', 'совсем', 'ним', 'здесь', 'этом', 'один', 'почти', 'мой', 'тем', 'чтобы', 'нее', 'сейчас', 'были', 'куда', 'зачем', 'всех', 'никогда', 'можно', 'при', 'наконец', 'два', 'об', 'другой', 'хоть', 'после', 'над', 'больше', 'тот', 'через', 'эти', 'нас', 'про', 'всего', 'них', 'какая', 'много', 'разве', 'три', 'эту', 'моя', 'впрочем', 'хорошо', 'свою', 'этой', 'перед', 'иногда', 'лучше', 'чуть', 'том', 'нельзя', 'такой', 'им', 'более', 'всегда', 'конечно', 'всю', 'между']
    
    # Инициализация лемматизатора
    morph = pymorphy3.MorphAnalyzer()
    
    return russian_stopwords, morph

def preprocess_text(text, stopwords_list, morph_analyzer):
    """
    Функция для предобработки текста: приведение к нижнему регистру, удаление пунктуации,
    чисел, стоп-слов и лемматизация.
    """
    if pd.isna(text):
        return ""
    
    # Приводим к нижнему регистру
    text = text.lower()
    # Удаляем пунктуацию и цифры
    text = re.sub(f'[{string.punctuation}«»—…"",,,""]', ' ', text)
    text = re.sub(r'\d+', '', text)
    # Удаляем множественные пробелы
    text = re.sub(r'\s+', ' ', text).strip()
    # Разбиваем на слова
    words = text.split()
    # Удаляем стоп-слова и применяем лемматизацию
    processed_words = []
    for word in words:
        if word not in stopwords_list and len(word) > 2:
            parsed_word = morph_analyzer.parse(word)[0]
            lemma = parsed_word.normal_form
            processed_words.append(lemma)
    
    return " ".join(processed_words)

def load_and_prepare_data(lost_file, found_file):
    """
    Загружает данные из двух файлов, объединяет их и создает целевую переменную is_success.
    """
    print("Загрузка данных...")
    
    # Загрузка данных
    df_lost = pd.read_csv(lost_file)
    df_found = pd.read_csv(found_file)
    
    # Добавляем метку типа объявления
    df_lost['объявление_тип'] = 'lost'
    df_found['объявление_тип'] = 'found'
    
    # Объединяем датасеты
    df_combined = pd.concat([df_lost, df_found], ignore_index=True)
    
    # Создаем целевую переменную is_success
    success_conditions = (
        (df_combined['статус'] == 'питомец найден') | 
        (df_combined['статус'] == 'хозяин найден')
    )
    df_combined['is_success'] = success_conditions
    
    print(f"Всего объявлений: {len(df_combined)}")
    print(f"Успешных случаев: {df_combined['is_success'].sum()}")
    print(f"Неуспешных случаев: {len(df_combined) - df_combined['is_success'].sum()}")
    print(f"Процент успешных: {df_combined['is_success'].mean():.1%}")
    
    return df_combined

def analyze_word_frequencies(df, stopwords_list, morph_analyzer):
    """
    Анализирует частоты слов в успешных и неуспешных объявлениях.
    """
    print("\nПредобработка текстов...")
    df['описание_обработанное'] = df['описание'].apply(
        lambda x: preprocess_text(x, stopwords_list, morph_analyzer)
    )
    
    # Разделяем на успешные и неуспешные
    success_texts = df[df['is_success'] == True]['описание_обработанное']
    fail_texts = df[df['is_success'] == False]['описание_обработанное']
    
    print(f"Успешных объявлений с описанием: {success_texts.str.len().gt(0).sum()}")
    print(f"Неуспешных объявлений с описанием: {fail_texts.str.len().gt(0).sum()}")
    
    # Собираем все слова
    all_success_words = ' '.join(success_texts).split()
    all_fail_words = ' '.join(fail_texts).split()
    
    # Считаем частоты
    success_freq = Counter(all_success_words)
    fail_freq = Counter(all_fail_words)
    
    # Создаем DataFrame для сравнения
    all_words = set(all_success_words + all_fail_words)
    word_comparison = []
    
    for word in all_words:
        if len(word) > 2:  # Игнорируем слишком короткие слова
            success_count = success_freq.get(word, 0)
            fail_count = fail_freq.get(word, 0)
            total_success = len(all_success_words)
            total_fail = len(all_fail_words)
            
            # Вычисляем относительные частоты (на 1000 слов)
            success_rel = (success_count / total_success * 1000) if total_success > 0 else 0
            fail_rel = (fail_count / total_fail * 1000) if total_fail > 0 else 0
            
            word_comparison.append({
                'word': word,
                'success_count': success_count,
                'fail_count': fail_count,
                'success_freq_per_1000': success_rel,
                'fail_freq_per_1000': fail_rel,
                'freq_difference': success_rel - fail_rel
            })
    
    word_df = pd.DataFrame(word_comparison)
    
    # Фильтруем слова, которые встречаются достаточно часто
    min_occurrences = 10
    word_df = word_df[
        (word_df['success_count'] >= min_occurrences) | 
        (word_df['fail_count'] >= min_occurrences)
    ]
    
    return word_df, success_texts, fail_texts

def analyze_with_tfidf(df, success_texts, fail_texts):
    """
    Анализирует слова с помощью TF-IDF подхода.
    """
    print("\nАнализ с помощью TF-IDF...")
    
    # Создаем TF-IDF векторайзер
    vectorizer = TfidfVectorizer(
        max_features=1500, 
        min_df=5, 
        max_df=0.8,
        ngram_range=(1, 2)  # Учитываем отдельные слова и биграммы
    )
    
    # Применяем ко всем текстам
    all_texts = df['описание_обработанное']
    X = vectorizer.fit_transform(all_texts)
    feature_names = vectorizer.get_feature_names_out()
    
    # Разделяем на успешные и неуспешные индексы
    success_idx = df[df['is_success'] == True].index
    fail_idx = df[df['is_success'] == False].index
    
    # Вычисляем средний TF-IDF для каждой группы
    success_tfidf = X[success_idx].mean(axis=0).A1
    fail_tfidf = X[fail_idx].mean(axis=0).A1
    
    # Создаем DataFrame для сравнения
    tfidf_comparison = pd.DataFrame({
        'word': feature_names,
        'success_tfidf': success_tfidf,
        'fail_tfidf': fail_tfidf
    })
    
    # Вычисляем разницу и относительную важность
    tfidf_comparison['tfidf_difference'] = tfidf_comparison['success_tfidf'] - tfidf_comparison['fail_tfidf']
    tfidf_comparison['abs_difference'] = abs(tfidf_comparison['tfidf_difference'])
    
    return tfidf_comparison

def visualize_results(word_df, tfidf_df):
    """
    Визуализирует результаты анализа.
    """
    print("\nВизуализация результатов...")
    
    # Топ-20 слов по разнице частот
    top_success_freq = word_df.nlargest(20, 'freq_difference')
    top_fail_freq = word_df.nsmallest(20, 'freq_difference')
    
    # Топ-20 слов по разнице TF-IDF
    top_success_tfidf = tfidf_df.nlargest(20, 'tfidf_difference')
    top_fail_tfidf = tfidf_df.nsmallest(20, 'tfidf_difference')
    
    # Создаем фигуру с 4 субплогами
    fig, axes = plt.subplots(2, 2, figsize=(20, 16))
    
    # 1. Слова по частоте - успешные
    axes[0, 0].barh(top_success_freq['word'], top_success_freq['freq_difference'], 
                   color='lightgreen', edgecolor='darkgreen')
    axes[0, 0].set_title('Топ-20 слов: в УСПЕШНЫХ объявлениях\n(по разнице частот)', 
                         fontsize=14, fontweight='bold')
    axes[0, 0].set_xlabel('Разница частот (на 1000 слов)')
    axes[0, 0].grid(axis='x', alpha=0.3)
    
    # 2. Слова по частоте - неуспешные
    axes[0, 1].barh(top_fail_freq['word'], top_fail_freq['freq_difference'], 
                   color='lightcoral', edgecolor='darkred')
    axes[0, 1].set_title('Топ-20 слов: в НЕУСПЕШНЫХ объявлениях\n(по разнице частот)', 
                         fontsize=14, fontweight='bold')
    axes[0, 1].set_xlabel('Разница частот (на 1000 слов)')
    axes[0, 1].grid(axis='x', alpha=0.3)
    
    # 3. Слова по TF-IDF - успешные
    axes[1, 0].barh(top_success_tfidf['word'], top_success_tfidf['tfidf_difference'], 
                   color='lightblue', edgecolor='darkblue')
    axes[1, 0].set_title('Топ-20 слов: в УСПЕШНЫХ объявлениях\n(по разнице TF-IDF)', 
                         fontsize=14, fontweight='bold')
    axes[1, 0].set_xlabel('Разница TF-IDF')
    axes[1, 0].grid(axis='x', alpha=0.3)
    
    # 4. Слова по TF-IDF - неуспешные
    axes[1, 1].barh(top_fail_tfidf['word'], top_fail_tfidf['tfidf_difference'], 
                   color='orange', edgecolor='darkorange')
    axes[1, 1].set_title('Топ-20 слов: в НЕУСПЕШНЫХ объявлениях\n(по разнице TF-IDF)', 
                         fontsize=14, fontweight='bold')
    axes[1, 1].set_xlabel('Разница TF-IDF')
    axes[1, 1].grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('linguistic_analysis_comprehensive.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Дополнительная визуализация: сравнение топ-10 слов
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
    
    # Сравнение частот для топ-10 успешных слов
    top_10_success = top_success_freq.head(10)
    x = range(len(top_10_success))
    width = 0.35
    
    ax1.bar([i - width/2 for i in x], top_10_success['success_freq_per_1000'], 
            width, label='Успешные', color='green', alpha=0.7)
    ax1.bar([i + width/2 for i in x], top_10_success['fail_freq_per_1000'], 
            width, label='Неуспешные', color='red', alpha=0.7)
    ax1.set_xlabel('Слова')
    ax1.set_ylabel('Частота (на 1000 слов)')
    ax1.set_title('Топ-10 слов из успешных объявлений:\nсравнение частот между группами')
    ax1.set_xticks(x)
    ax1.set_xticklabels(top_10_success['word'], rotation=45, ha='right')
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)
    
    # Сравнение частот для топ-10 неуспешных слов
    top_10_fail = top_fail_freq.head(10)
    x = range(len(top_10_fail))
    
    ax2.bar([i - width/2 for i in x], top_10_fail['success_freq_per_1000'], 
            width, label='Успешные', color='green', alpha=0.7)
    ax2.bar([i + width/2 for i in x], top_10_fail['fail_freq_per_1000'], 
            width, label='Неуспешные', color='red', alpha=0.7)
    ax2.set_xlabel('Слова')
    ax2.set_ylabel('Частота (на 1000 слов)')
    ax2.set_title('Топ-10 слов из неуспешных объявлений:\nсравнение частот между группами')
    ax2.set_xticks(x)
    ax2.set_xticklabels(top_10_fail['word'], rotation=45, ha='right')
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('word_frequency_comparison.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    return top_success_freq, top_fail_freq, top_success_tfidf, top_fail_tfidf

def print_insights(success_words_freq, fail_words_freq, success_words_tfidf, fail_words_tfidf):
    """
    Выводит ключевые результаты анализа.
    """
    print("\n" + "="*80)
    print("КЛЮЧЕВЫЕ РЕЗУЛЬТАТЫ ЛИНГВИСТИЧЕСКОГО АНАЛИЗА")
    print("="*80)
    
    print("\n📈 СЛОВА, СВЯЗАННЫЕ С УСПЕХОМ:")
    print("По частоте:")
    for i, (_, row) in enumerate(success_words_freq.head(10).iterrows(), 1):
        print(f"  {i:2d}. {row['word']:15} (разница: {row['freq_difference']:+.2f})")
    
    print("\nПо TF-IDF (характерные слова):")
    for i, (_, row) in enumerate(success_words_tfidf.head(10).iterrows(), 1):
        print(f"  {i:2d}. {row['word']:15} (разница TF-IDF: {row['tfidf_difference']:+.4f})")
    
    print("\n📉 СЛОВА, СВЯЗАННЫЕ С НЕУДАЧЕЙ:")
    print("По частоте:")
    for i, (_, row) in enumerate(fail_words_freq.head(10).iterrows(), 1):
        print(f"  {i:2d}. {row['word']:15} (разница: {row['freq_difference']:+.2f})")
    
    print("\nПо TF-IDF (характерные слова):")
    for i, (_, row) in enumerate(fail_words_tfidf.head(10).iterrows(), 1):
        print(f"  {i:2d}. {row['word']:15} (разница TF-IDF: {row['tfidf_difference']:+.4f})")

def main():
    """
    Основная функция для лингвистического анализа.
    """
    # Укажите пути к вашим файлам
    LOST_FILE = 'Dataset_final_Pet911_lost.csv'
    FOUND_FILE = 'dataset_final_Pet911_found.csv'
    
    try:
        print("=== ЛИНГВИСТИЧЕСКИЙ АНАЛИЗ ОПИСАНИЙ ===")
        print("Загрузка и настройка...")
        
        # Настройка инструментов для русского языка
        stopwords_list, morph_analyzer = setup_russian_analysis()
        
        # Загрузка данных
        df = load_and_prepare_data(LOST_FILE, FOUND_FILE)
        
        # Анализ частот слов
        word_freq_df, success_texts, fail_texts = analyze_word_frequencies(
            df, stopwords_list, morph_analyzer
        )
        
        # Анализ TF-IDF
        tfidf_df = analyze_with_tfidf(df, success_texts, fail_texts)
        
        # Визуализация результатов
        success_freq, fail_freq, success_tfidf, fail_tfidf = visualize_results(
            word_freq_df, tfidf_df
        )
        
        # Вывод инсайтов
        print_insights(success_freq, fail_freq, success_tfidf, fail_tfidf)
        
        # Сохранение результатов
        word_freq_df.to_csv('word_frequency_analysis.csv', index=False, encoding='utf-8-sig')
        tfidf_df.to_csv('tfidf_analysis.csv', index=False, encoding='utf-8-sig')
        
        print(f"\nРезультаты сохранены в файлы:")
        print("- word_frequency_analysis.csv")
        print("- tfidf_analysis.csv") 
        print("- linguistic_analysis_comprehensive.png")
        print("- word_frequency_comparison.png")
        
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()