# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Настройка отображения графиков
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class PetSearchAnalyzer:
    def __init__(self, file_path):
        """
        Инициализация анализатора с загрузкой данных
        
        Parameters:
        file_path (str): путь к CSV файлу с данными
        """
        self.df = pd.read_csv(file_path, encoding='utf-8')
        self.preprocess_data()
        
    def preprocess_data(self):
        """Предобработка данных и создание целевой переменной"""
        print("🔧 Предобработка данных...")
        
        # Копируем данные чтобы избежать предупреждений
        df = self.df.copy()
        
        # Приводим текстовые колонки к нижнему регистру для consistency
        text_columns = ['тип_объявления', 'регион', 'статус_поиска', 'тип_животного', 
                       'пол', 'возраст', 'окрас', 'есть_фото', 'есть_контакты']
        
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.lower()
        
        # Создаем целевую переменную is_success
        df['is_success'] = (
            (df['тип_объявления'] == 'потерян') & (df['статус_поиска'] == 'найден')
        ) | (
            (df['тип_объявления'] == 'найден') & (df['статус_поиска'] == 'хозяин найден')
        )
        df['is_success'] = df['is_success'].astype(int)
        
        # Обработка бинарных признаков
        df['есть_фото'] = df['есть_фото'].map({'да': 1, 'нет': 0, '1': 1, '0': 0})
        df['есть_контакты'] = df['есть_контакты'].map({'да': 1, 'нет': 0, '1': 1, '0': 0})
        
        # Заполнение пропусков в числовых колонках
        numeric_columns = ['количество_фото', 'длина_описания', 'количество_комментариев']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Обработка категориальных признаков - заменяем редкие значения
        categorical_columns = ['пол', 'возраст', 'окрас', 'регион']
        for col in categorical_columns:
            if col in df.columns:
                # Заменяем редкие категории (менее 2% данных) на 'другое/не указано'
                value_counts = df[col].value_counts(normalize=True)
                rare_categories = value_counts[value_counts < 0.02].index
                df[col] = df[col].replace(rare_categories, 'другое/не указано')
        
        self.df_processed = df
        print(f"✅ Обработано {len(df)} объявлений")
        print(f"✅ Успешных случаев: {df['is_success'].sum()} ({df['is_success'].mean()*100:.1f}%)")
        
    def analyze_overall_success(self):
        """Анализ общей успешности по типам объявлений"""
        print("\n📊 АНАЛИЗ ОБЩЕЙ УСПЕШНОСТИ")
        
        success_by_type = self.df_processed.groupby('тип_объявления')['is_success'].agg([
            ('count', 'count'),
            ('success_count', 'sum'),
            ('success_rate', 'mean')
        ]).round(3)
        
        print(success_by_type)
        
        # Визуализация
        fig, axes = plt.subplots(1, 2, figsize=(15, 5))
        
        # График 1: Распределение типов объявлений
        type_counts = self.df_processed['тип_объявления'].value_counts()
        axes[0].pie(type_counts.values, labels=type_counts.index, autopct='%1.1f%%')
        axes[0].set_title('Распределение типов объявлений')
        
        # График 2: Доля успеха по типам
        success_rates = self.df_processed.groupby('тип_объявления')['is_success'].mean()
        axes[1].bar(success_rates.index, success_rates.values * 100, color=['skyblue', 'lightcoral'])
        axes[1].set_title('Доля успешных поисков по типам объявлений')
        axes[1].set_ylabel('Доля успеха, %')
        
        for i, v in enumerate(success_rates.values):
            axes[1].text(i, v * 100 + 1, f'{v*100:.1f}%', ha='center')
        
        plt.tight_layout()
        plt.show()
        
        return success_by_type
    
    def analyze_categorical_factors(self, factor_column, min_count=3):
        """
        Анализ влияния категориального фактора на успешность
        
        Parameters:
        factor_column (str): название колонки для анализа
        min_count (int): минимальное количество наблюдений для категории
        """
        if factor_column not in self.df_processed.columns:
            print(f"⚠️ Колонка {factor_column} не найдена в данных")
            return None
            
        print(f"\n📈 АНАЛИЗ ФАКТОРА: {factor_column}")
        
        # Группируем данные
        factor_analysis = self.df_processed.groupby(factor_column).agg({
            'is_success': ['count', 'sum', 'mean'],
            'тип_объявления': 'first'  # для информации
        }).round(3)
        
        # Выравниваем multi-index
        factor_analysis.columns = ['count', 'success_count', 'success_rate', 'main_type']
        factor_analysis = factor_analysis[factor_analysis['count'] >= min_count]
        factor_analysis = factor_analysis.sort_values('success_rate', ascending=False)
        
        print(factor_analysis)
        
        # Статистическая значимость - тест хи-квадрат
        if len(factor_analysis) > 1:
            contingency_table = pd.crosstab(self.df_processed[factor_column], 
                                          self.df_processed['is_success'])
            chi2, p_value, dof, expected = stats.chi2_contingency(contingency_table)
            print(f"📊 Тест хи-квадрат: p-value = {p_value:.4f}")
            if p_value < 0.05:
                print("✅ Влияние статистически значимо (p < 0.05)")
            else:
                print("❌ Влияние статистически не значимо (p >= 0.05)")
        
        # Визуализация
        plt.figure(figsize=(12, 6))
        
        # Оставляем только категории с достаточным количеством данных
        plot_data = factor_analysis.head(10)  # Топ-10 категорий по успешности
        
        if len(plot_data) > 0:
            bars = plt.bar(range(len(plot_data)), plot_data['success_rate'] * 100, 
                          color='lightgreen', alpha=0.7)
            plt.xticks(range(len(plot_data)), plot_data.index, rotation=45)
            plt.title(f'Доля успешных поисков по фактору: {factor_column}')
            plt.ylabel('Доля успеха, %')
            
            # Добавляем подписи значений
            for i, bar in enumerate(bars):
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                        f'{height:.1f}%', ha='center', va='bottom')
            
            plt.tight_layout()
            plt.show()
        
        return factor_analysis
    
    def analyze_numeric_factors(self, factor_column):
        """
        Анализ влияния числового фактора на успешность
        
        Parameters:
        factor_column (str): название числовой колонки для анализа
        """
        if factor_column not in self.df_processed.columns:
            print(f"⚠️ Колонка {factor_column} не найдена в данных")
            return None
            
        print(f"\n📈 АНАЛИЗ ЧИСЛОВОГО ФАКТОРА: {factor_column}")
        
        # Описательная статистика по группам успеха
        numeric_stats = self.df_processed.groupby('is_success')[factor_column].describe()
        print(numeric_stats)
        
        # Статистический тест
        success_data = self.df_processed[self.df_processed['is_success'] == 1][factor_column]
        fail_data = self.df_processed[self.df_processed['is_success'] == 0][factor_column]
        
        t_stat, p_value = stats.mannwhitneyu(success_data, fail_data, alternative='two-sided')
        print(f"📊 U-тест Манна-Уитни: p-value = {p_value:.4f}")
        if p_value < 0.05:
            print("✅ Различия статистически значимы (p < 0.05)")
        else:
            print("❌ Различия статистически не значимы (p >= 0.05)")
        
        # Визуализация
        fig, axes = plt.subplots(1, 2, figsize=(15, 5))
        
        # Boxplot
        sns.boxplot(data=self.df_processed, x='is_success', y=factor_column, ax=axes[0])
        axes[0].set_title(f'Распределение {factor_column} по успешности поиска')
        axes[0].set_xlabel('Успешность (0-нет, 1-да)')
        axes[0].set_ylabel(factor_column)
        
        # Гистограмма
        sns.histplot(data=self.df_processed, x=factor_column, hue='is_success', 
                    multiple="layer", alpha=0.6, ax=axes[1])
        axes[1].set_title(f'Распределение {factor_column} по успешности поиска')
        
        plt.tight_layout()
        plt.show()
        
        return numeric_stats
    
    def analyze_binary_factors(self, factor_column):
        """
        Анализ влияния бинарного фактора на успешность
        
        Parameters:
        factor_column (str): название бинарной колонки для анализа
        """
        if factor_column not in self.df_processed.columns:
            print(f"⚠️ Колонка {factor_column} не найдена в данных")
            return None
            
        print(f"\n📈 АНАЛИЗ БИНАРНОГО ФАКТОРА: {factor_column}")
        
        binary_analysis = self.df_processed.groupby(factor_column)['is_success'].agg([
            ('count', 'count'),
            ('success_count', 'sum'),
            ('success_rate', 'mean')
        ]).round(3)
        
        print(binary_analysis)
        
        # Визуализация
        plt.figure(figsize=(8, 5))
        bars = plt.bar([str(x) for x in binary_analysis.index], 
                      binary_analysis['success_rate'] * 100, 
                      color=['lightcoral', 'lightgreen'])
        
        plt.title(f'Влияние {factor_column} на успешность поиска')
        plt.ylabel('Доля успеха, %')
        plt.xlabel(f'{factor_column} (0-нет, 1-да)')
        
        for i, bar in enumerate(bars):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{height:.1f}%', ha='center', va='bottom')
        
        plt.tight_layout()
        plt.show()
        
        return binary_analysis
    
    def comprehensive_analysis(self):
        """Комплексный анализ всех факторов"""
        print("🚀 ЗАПУСК КОМПЛЕКСНОГО АНАЛИЗА")
        
        results = {}
        
        # 1. Общая успешность
        results['overall'] = self.analyze_overall_success()
        
        # 2. Категориальные факторы
        categorical_factors = ['тип_животного', 'пол', 'возраст', 'окрас', 'регион']
        
        for factor in categorical_factors:
            if factor in self.df_processed.columns:
                results[factor] = self.analyze_categorical_factors(factor)
        
        # 3. Числовые факторы  
        numeric_factors = ['количество_фото', 'длина_описания', 'количество_комментариев']
        
        for factor in numeric_factors:
            if factor in self.df_processed.columns:
                results[factor] = self.analyze_numeric_factors(factor)
        
        # 4. Бинарные факторы
        binary_factors = ['есть_фото', 'есть_контакты']
        
        for factor in binary_factors:
            if factor in self.df_processed.columns:
                results[factor] = self.analyze_binary_factors(factor)
        
        # 5. Сводка ключевых выводов
        self.generate_summary(results)
        
        return results
    
    def generate_summary(self, results):
        """Генерация сводки ключевых выводов"""
        print("\n" + "="*60)
        print("📋 СВОДКА КЛЮЧЕВЫХ ВЫВОДОВ")
        print("="*60)
        
        # Собираем ключевые инсайты
        insights = []
        
        # Анализ по типам животных
        if 'тип_животного' in results and results['тип_животного'] is not None:
            animal_success = results['тип_животного']
            best_animal = animal_success.index[0]
            best_rate = animal_success.iloc[0]['success_rate']
            worst_animal = animal_success.index[-1]
            worst_rate = animal_success.iloc[-1]['success_rate']
            
            insights.append(f"🐕🐈 Наивысшая успешность у '{best_animal}' ({best_rate*100:.1f}%), "
                          f"низшая у '{worst_animal}' ({worst_rate*100:.1f}%)")
        
        # Анализ фото
        if 'есть_фото' in results and results['есть_фото'] is not None:
            photo_effect = results['есть_фото']
            if 1 in photo_effect.index and 0 in photo_effect.index:
                with_photo = photo_effect.loc[1]['success_rate']
                without_photo = photo_effect.loc[0]['success_rate']
                diff = (with_photo - without_photo) * 100
                insights.append(f"📸 Наличие фото увеличивает шансы на {diff:+.1f}%")
        
        # Анализ контактов
        if 'есть_контакты' in results and results['есть_контакты'] is not None:
            contacts_effect = results['есть_контакты']
            if 1 in contacts_effect.index and 0 in contacts_effect.index:
                with_contacts = contacts_effect.loc[1]['success_rate']
                without_contacts = contacts_effect.loc[0]['success_rate']
                diff = (with_contacts - without_contacts) * 100
                insights.append(f"📞 Наличие контактов увеличивает шансы на {diff:+.1f}%")
        
        # Анализ описания
        if 'длина_описания' in results and results['длина_описания'] is not None:
            desc_stats = results['длина_описания']
            if not desc_stats.empty:
                success_mean = desc_stats.loc[1, 'mean'] if 1 in desc_stats.index else 0
                fail_mean = desc_stats.loc[0, 'mean'] if 0 in desc_stats.index else 0
                if success_mean > fail_mean:
                    insights.append(f"📝 Успешные объявления содержат больше слов в описании "
                                  f"({success_mean:.0f} vs {fail_mean:.0f} слов)")
        
        # Вывод инсайтов
        for i, insight in enumerate(insights, 1):
            print(f"{i}. {insight}")
        
        # Рекомендации
        print("\n💡 РЕКОМЕНДАЦИИ ДЛЯ УВЕЛИЧЕНИЯ ШАНСОВ:")
        print("   • Всегда добавляйте фото питомца")
        print("   • Указывайте контактные данные")  
        print("   • Составляйте подробное описание")
        print("   • Указывайте точные приметы и окрас")
        print("   • Регулярно обновляйте объявление")

# 🔧 ИСПОЛЬЗОВАНИЕ ПРОГРАММЫ:
# ЗАМЕНИТЕ 'pets_dataset_2025.csv' НА ПУТЬ К ВАШЕМУ ФАЙЛУ

if __name__ == "__main__":
    # Создаем анализатор и загружаем данные
    analyzer = PetSearchAnalyzer('pets_dataset_2025.csv')
    
    # Запускаем комплексный анализ
    results = analyzer.comprehensive_analysis()
    
    # 📍 КОММЕНТАРИЙ ДЛЯ РЕДАКТИРОВАНИЯ:
    # Если нужно проанализировать отдельный фактор, раскомментируйте нужные строки:
    
    analyzer.analyze_categorical_factors('пол')  # Анализ по полу животного
    analyzer.analyze_numeric_factors('количество_комментариев')  # Анализ комментариев
    analyzer.analyze_binary_factors('есть_контакты')  # Анализ контактов
    
    # 📍 ЕСЛИ ХОТИТЕ СОХРАНИТЬ РЕЗУЛЬТАТЫ В ФАЙЛ:
    # import json
    # with open('analysis_results.json', 'w', encoding='utf-8') as f:
    #     # Конвертируем DataFrame в словари для сохранения
    #     results_serializable = {}
    #     for key, value in results.items():
    #         if hasattr(value, 'to_dict'):
    #             results_serializable[key] = value.to_dict()
    #         else:
    #             results_serializable[key] = value
    #     json.dump(results_serializable, f, ensure_ascii=False, indent=2)