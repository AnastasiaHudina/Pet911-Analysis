# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
import os
import csv
import json

warnings.filterwarnings('ignore')

# Настройка стиля графиков
plt.style.use('default')
sns.set_palette("husl")

class PetSearchAnalyzer:
    def __init__(self, file_path, file_type):
        self.file_type = file_type
        self.file_path = file_path
        self.stats_results = {}
        print(f"📁 Загрузка данных из файла: {os.path.basename(file_path)}")
        
        self.df = self.load_proper_csv(file_path)
        
        if not self.df.empty:
            self.preprocess_data()
        else:
            print("❌ Не удалось загрузить данные")
    
    def load_proper_csv(self, file_path):
        """Загружает CSV файл с правильным парсингом кавычек, пропускает первую строку"""
        try:
            encodings = ['utf-8', 'cp1251', 'latin1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        reader = csv.reader(f)
                        rows = list(reader)
                    
                    if rows:
                        print(f"✅ Успешно загружено с кодировкой {encoding}")
                        break
                except UnicodeDecodeError:
                    continue
            else:
                print("❌ Не удалось загрузить файл с доступными кодировками")
                return pd.DataFrame()
            
            if len(rows) > 1:
                data_rows = rows[1:]
                print(f"📊 Строк данных: {len(data_rows)}")
            else:
                print("❌ В файле нет данных кроме заголовка")
                return pd.DataFrame()
            
            column_names = [
                'url', 'id', 'тип_объявления', 'регион', 'статус', 'тип_животного', 
                'окрас', 'порода', 'место_события', 'дата_публикации', 'пол', 
                'возраст', 'описание', 'длина_описания', 'наличие_описания', 
                'есть_фото', 'количество_фото', 'количество_комментариев', 
                'дата_события', 'есть_контакты'
            ]
            
            df = pd.DataFrame(data_rows, columns=column_names[:len(data_rows[0])])
            print(f"✅ Создано {len(df)} строк с {len(df.columns)} колонками")
            
            return df
            
        except Exception as e:
            print(f"❌ Ошибка загрузки файла: {e}")
            return pd.DataFrame()
        
    def preprocess_data(self):
        """Предобработка данных"""
        print("🔧 Предобработка данных...")
        
        df = self.df.copy()
        
        # Очищаем данные от лишних кавычек и пробелов
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.strip('"').str.strip("'")
        
        # Приводим текстовые колонки к нижнему регистру
        text_columns = ['тип_объявления', 'регион', 'статус', 'тип_животного', 
                       'пол', 'окрас', 'порода', 'место_события']
        
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].str.lower()
        
        # Создаем целевую переменную is_success
        if 'статус' in df.columns:
            if self.file_type == 'lost':
                df['is_success'] = df['статус'].str.contains('найден', na=False)
            else:
                df['is_success'] = df['статус'].str.contains('хозяин найден', na=False)
            
            df['is_success'] = df['is_success'].astype(int)
        
        # Обработка бинарных признаков
        binary_mapping = {'true': 1, 'false': 0, 'да': 1, 'нет': 0, '1': 1, '0': 0}
        binary_columns = ['наличие_описания', 'есть_фото', 'есть_контакты']
        
        for col in binary_columns:
            if col in df.columns:
                df[col] = df[col].str.lower().map(binary_mapping).fillna(0).astype(int)
        
        # Заполнение пропусков в числовых колонках
        numeric_columns = ['количество_фото', 'длина_описания', 'количество_комментариев']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        self.df_processed = df
        print(f"✅ Обработано {len(df)} объявлений")
        print(f"✅ Успешных случаев: {df['is_success'].sum()} ({df['is_success'].mean()*100:.1f}%)")
        
        # Сохраняем базовую статистику
        self.stats_results['base_success_rate'] = df['is_success'].mean()
        self.stats_results['total_ads'] = len(df)
        self.stats_results['successful_ads'] = df['is_success'].sum()
    
    def plot_success_by_animal_type(self):
        """График 3 и 7: Доля успеха по типам животных"""
        if 'тип_животного' not in self.df_processed.columns:
            return
        
        df = self.df_processed
        animal_success = df.groupby('тип_животного')['is_success'].agg(['count', 'mean']).round(3)
        animal_success = animal_success[animal_success['count'] >= 3]
        animal_success = animal_success.sort_values('mean', ascending=False)
        
        plt.figure(figsize=(10, 6))
        bars = plt.bar(animal_success.index, animal_success['mean'] * 100, 
                      color='lightgreen', alpha=0.7)
        
        title = f'Доля успеха "потерян" по типам животных' if self.file_type == 'lost' else f'Доля успеха "найден" по типам животных'
        plt.title(title, fontsize=14, fontweight='bold')
        plt.ylabel('Доля успеха, %', fontsize=12)
        plt.xlabel('Тип животного', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', alpha=0.3)
        
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{height:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.show()
        
        return animal_success
    
    def plot_photo_impact(self):
        """График 4 и 8: Влияние фото на успешность поиска"""
        if 'есть_фото' not in self.df_processed.columns:
            return
        
        df = self.df_processed
        photo_analysis = df.groupby('есть_фото')['is_success'].mean()
        
        plt.figure(figsize=(8, 6))
        bars = plt.bar(['Без фото', 'С фото'], 
                      [photo_analysis.get(0, 0) * 100, photo_analysis.get(1, 0) * 100],
                      color=['lightcoral', 'lightgreen'])
        
        title = f'Влияние фото на успешность поиска (потерян)' if self.file_type == 'lost' else f'Влияние фото на успешность поиска (найден)'
        plt.title(title, fontsize=14, fontweight='bold')
        plt.ylabel('Доля успеха, %', fontsize=12)
        plt.xlabel('Наличие фото', fontsize=12)
        
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{height:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.show()
        
        return photo_analysis
    
    def plot_photo_count_impact(self):
        """График 5 и 9: Распределение количества фото на успешность поиска"""
        if 'количество_фото' not in self.df_processed.columns:
            return
        
        df = self.df_processed
        df['фото_группа'] = pd.cut(df['количество_фото'], 
                                  bins=[-1, 0, 1, 2, 3, 5, 100],
                                  labels=['0', '1', '2', '3', '4-5', '6+'])
        
        photo_count_success = df.groupby('фото_группа')['is_success'].agg(['count', 'mean']).round(3)
        photo_count_success = photo_count_success[photo_count_success['count'] >= 2]
        
        plt.figure(figsize=(10, 6))
        bars = plt.bar(photo_count_success.index.astype(str), photo_count_success['mean'] * 100,
                      color='lightblue', alpha=0.7)
        
        title = f'Влияние количества фото на успешность поиска (потерян)' if self.file_type == 'lost' else f'Влияние количества фото на успешность поиска (найден)'
        plt.title(title, fontsize=14, fontweight='bold')
        plt.ylabel('Доля успеха, %', fontsize=12)
        plt.xlabel('Количество фото', fontsize=12)
        plt.grid(axis='y', alpha=0.3)
        
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{height:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.show()
        
        return photo_count_success
    
    def plot_description_length_impact(self):
        """График 6 и 10: Влияние длины описания на успешность поиска"""
        if 'длина_описания' not in self.df_processed.columns:
            return
        
        df = self.df_processed
        df['описание_группа'] = pd.cut(df['длина_описания'], 
                                      bins=[-1, 0, 10, 20, 30, 50, 100, 1000],
                                      labels=['0', '1-10', '11-20', '21-30', '31-50', '51-100', '100+'])
        
        desc_success = df.groupby('описание_группа')['is_success'].agg(['count', 'mean']).round(3)
        desc_success = desc_success[desc_success['count'] >= 2]
        
        plt.figure(figsize=(12, 6))
        bars = plt.bar(desc_success.index.astype(str), desc_success['mean'] * 100,
                      color='lightcoral', alpha=0.7)
        
        title = f'Влияние длины описания на успешность поиска (потерян)' if self.file_type == 'lost' else f'Влияние длины описания на успешность поиска (найден)'
        plt.title(title, fontsize=14, fontweight='bold')
        plt.ylabel('Доля успеха, %', fontsize=12)
        plt.xlabel('Длина описания (слов)', fontsize=12)
        plt.grid(axis='y', alpha=0.3)
        
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{height:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.show()
        
        return desc_success
    
    def calculate_animal_statistics(self):
        """Рассчитывает статистику по типам животных"""
        if 'тип_животного' not in self.df_processed.columns:
            return
        
        df = self.df_processed
        animal_stats = df.groupby('тип_животного').agg({
            'is_success': ['count', 'sum', 'mean']
        }).round(4)
        animal_stats.columns = ['count', 'success_count', 'success_rate']
        
        self.stats_results['animal_success_rates'] = animal_stats['success_rate'].to_dict()
        
        return animal_stats
    
    def calculate_photo_statistics(self):
        """Рассчитывает статистику по фото"""
        photo_stats = {}
        
        if 'есть_фото' in self.df_processed.columns:
            photo_presence = self.df_processed.groupby('есть_фото')['is_success'].mean()
            photo_stats['has_photo_impact'] = {
                0: float(photo_presence.get(0, 0)),
                1: float(photo_presence.get(1, 0))
            }
        
        if 'количество_фото' in self.df_processed.columns:
            df = self.df_processed.copy()
            df['фото_группа'] = pd.cut(df['количество_фото'], 
                                      bins=[-1, 0, 1, 2, 3, 5, 100],
                                      labels=['0', '1', '2', '3', '4-5', '6+'])
            
            photo_count_stats = df.groupby('фото_группа')['is_success'].mean()
            photo_stats['photo_count_impact'] = photo_count_stats.to_dict()
        
        self.stats_results['photo_statistics'] = photo_stats
        return photo_stats
    
    def calculate_description_statistics(self):
        """Рассчитывает статистику по описанию"""
        desc_stats = {}
        
        if 'наличие_описания' in self.df_processed.columns:
            desc_presence = self.df_processed.groupby('наличие_описания')['is_success'].mean()
            desc_stats['has_description_impact'] = {
                0: float(desc_presence.get(0, 0)),
                1: float(desc_presence.get(1, 0))
            }
        
        if 'длина_описания' in self.df_processed.columns:
            df = self.df_processed.copy()
            df['описание_группа'] = pd.cut(df['длина_описания'], 
                                          bins=[-1, 0, 10, 20, 30, 50, 100, 1000],
                                          labels=['0', '1-10', '11-20', '21-30', '31-50', '51-100', '100+'])
            
            desc_length_stats = df.groupby('описание_группа')['is_success'].mean()
            desc_stats['description_length_impact'] = desc_length_stats.to_dict()
        
        self.stats_results['description_statistics'] = desc_stats
        return desc_stats
    
    def calculate_contacts_statistics(self):
        """Рассчитывает статистику по контактам"""
        if 'есть_контакты' not in self.df_processed.columns:
            return
        
        contacts_stats = self.df_processed.groupby('есть_контакты')['is_success'].mean()
        self.stats_results['contacts_impact'] = {
            0: float(contacts_stats.get(0, 0)),
            1: float(contacts_stats.get(1, 0))
        }
        
        return contacts_stats
    
    def save_statistics(self, output_dir='3p1_statistics'):
        """Сохраняет статистику в файлы"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        filename = f"pet911_{self.file_type}_statistics.json"
        filepath = os.path.join(output_dir, filename)
        
        def convert_to_serializable(obj):
            if isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_to_serializable(x) for x in obj]
            else:
                return obj
        
        serializable_stats = convert_to_serializable(self.stats_results)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(serializable_stats, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Статистика сохранена в: {filepath}")
        
        self.save_detailed_stats_csv(output_dir)
        
        return filepath
    
    def save_detailed_stats_csv(self, output_dir):
        """Сохраняет детальную статистику в CSV"""
        filename = f"pet911_{self.file_type}_detailed_stats.csv"
        filepath = os.path.join(output_dir, filename)
        
        detailed_data = []
        
        detailed_data.append({
            'category': 'base',
            'factor': 'base_success_rate',
            'value': self.stats_results['base_success_rate'],
            'description': 'Базовый уровень успешности'
        })
        
        if 'animal_success_rates' in self.stats_results:
            for animal, rate in self.stats_results['animal_success_rates'].items():
                detailed_data.append({
                    'category': 'animal_type',
                    'factor': animal,
                    'value': rate,
                    'description': f'Успешность для {animal}'
                })
        
        if 'photo_statistics' in self.stats_results:
            photo_stats = self.stats_results['photo_statistics']
            if 'has_photo_impact' in photo_stats:
                detailed_data.append({
                    'category': 'photo',
                    'factor': 'no_photo',
                    'value': photo_stats['has_photo_impact'].get(0, 0),
                    'description': 'Успешность без фото'
                })
                detailed_data.append({
                    'category': 'photo', 
                    'factor': 'with_photo',
                    'value': photo_stats['has_photo_impact'].get(1, 0),
                    'description': 'Успешность с фото'
                })
        
        df_detailed = pd.DataFrame(detailed_data)
        df_detailed.to_csv(filepath, index=False, encoding='utf-8')
        print(f"📊 Детальная статистика сохранена в: {filepath}")

    def comprehensive_analysis(self):
        """Комплексный анализ всех факторов"""
        print(f"\n{'='*60}")
        print(f"🚀 ПОЛНЫЙ АНАЛИЗ - {self.file_type.upper()}")
        print(f"{'='*60}")
        
        total_ads = len(self.df_processed)
        success_ads = self.df_processed['is_success'].sum()
        success_rate = self.df_processed['is_success'].mean() * 100
        
        print(f"📈 Общая статистика:")
        print(f"   Всего объявлений: {total_ads}")
        print(f"   Успешных случаев: {success_ads}")
        print(f"   Уровень успеха: {success_rate:.1f}%")
        
        # Построение графиков
        print(f"\n📊 Построение графиков...")
        
        # Графики для текущего типа объявлений
        self.plot_success_by_animal_type()
        self.plot_photo_impact()
        self.plot_photo_count_impact()
        self.plot_description_length_impact()
        
        # Расчет статистики для сохранения
        print(f"\n📊 Расчет статистики для прогнозирования...")
        self.calculate_animal_statistics()
        self.calculate_photo_statistics()
        self.calculate_description_statistics()
        self.calculate_contacts_statistics()
        
        # Сохранение статистики
        saved_file = self.save_statistics()
        
        print(f"\n✅ Анализ завершен! Статистика сохранена для использования в прогнозной модели")
        
        return self.stats_results

def plot_comparison_charts(lost_analyzer, found_analyzer):
    """Графики 1 и 2: Сравнительные графики для обоих файлов"""
    
    # График 1: Диаграмма распределения типов объявлений
    plt.figure(figsize=(12, 5))
    
    plt.subplot(1, 2, 1)
    types = ['Потерян', 'Найден']
    counts = [len(lost_analyzer.df_processed), len(found_analyzer.df_processed)]
    colors = ['lightblue', 'lightcoral']
    
    plt.pie(counts, labels=types, autopct='%1.1f%%', colors=colors)
    plt.title('Распределение типов объявлений', fontsize=14, fontweight='bold')
    
    # График 2: Доля успеха по типам объявлений
    plt.subplot(1, 2, 2)
    lost_success = lost_analyzer.df_processed['is_success'].mean() * 100
    found_success = found_analyzer.df_processed['is_success'].mean() * 100
    
    bars = plt.bar(['Потерян', 'Найден'], [lost_success, found_success], 
                  color=['lightblue', 'lightcoral'])
    plt.title('Доля успеха по типам объявлений', fontsize=14, fontweight='bold')
    plt.ylabel('Доля успеха, %', fontsize=12)
    
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{height:.1f}%', ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.show()
    
    print(f"\n📊 СВОДНАЯ СТАТИСТИКА:")
    print(f"   Потерянные животные: {lost_success:.1f}% успеха")
    print(f"   Найденные животные: {found_success:.1f}% успеха")

def main():
    """Основная функция программы анализа"""
    print("🎯 АНАЛИЗ ДАННЫХ PET911 - СОХРАНЕНИЕ СТАТИСТИКИ")
    print("=" * 60)
    
    # Файлы для анализа
    lost_file = 'Dataset_final_Pet911_lost.csv'
    found_file = 'dataset_final_Pet911_found.csv'
    
    all_statistics = {}
    analyzers = {}
    
    # Анализ потерянных животных
    if os.path.exists(lost_file):
        print(f"\n{'🔍'*20} АНАЛИЗ ПОТЕРЯННЫХ ЖИВОТНЫХ {'🔍'*20}")
        lost_analyzer = PetSearchAnalyzer(lost_file, 'lost')
        if not lost_analyzer.df.empty:
            stats_lost = lost_analyzer.comprehensive_analysis()
            all_statistics['lost'] = stats_lost
            analyzers['lost'] = lost_analyzer
    else:
        print(f"❌ Файл {lost_file} не найден")
    
    # Анализ найденных животных
    if os.path.exists(found_file):
        print(f"\n{'🔍'*20} АНАЛИЗ НАЙДЕННЫХ ЖИВОТНЫХ {'🔍'*20}")
        found_analyzer = PetSearchAnalyzer(found_file, 'found')
        if not found_analyzer.df.empty:
            stats_found = found_analyzer.comprehensive_analysis()
            all_statistics['found'] = stats_found
            analyzers['found'] = found_analyzer
    else:
        print(f"❌ Файл {found_file} не найден")
    
    # Сравнительные графики
    if 'lost' in analyzers and 'found' in analyzers:
        print(f"\n{'📊'*20} СРАВНИТЕЛЬНЫЕ ГРАФИКИ {'📊'*20}")
        plot_comparison_charts(analyzers['lost'], analyzers['found'])
    
    print(f"\n✅ Анализ завершен! Статистика сохранена в папке 'statistics/'")
    print("💡 Теперь можно запустить программу прогнозирования!")

if __name__ == "__main__":
    main()
