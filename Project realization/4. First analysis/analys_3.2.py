# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import math
import os
import warnings
warnings.filterwarnings('ignore')

class SimplePetPredictor:
    def __init__(self):
        self.success_rates = {}
        self.feature_weights = {}
        
    def calculate_success_rates(self, df):
        """Рассчитывает вероятности успеха на основе исторических данных"""
        print(" РАССЧЕТ ВЕРОЯТНОСТЕЙ НА ОСНОВЕ ДАННЫХ...")
        
        # Создаем целевую переменную (ИСПРАВЛЕНО: проверяем наличие колонки)
        if 'статус_поиска' in df.columns:
            df['is_success'] = (
                (df['тип_объявления'] == 'потерян') & (df['статус_поиска'] == 'найден')
            ) | (
                (df['тип_объявления'] == 'найден') & (df['статус_поиска'] == 'хозяин найден')
            )
            df['is_success'] = df['is_success'].astype(int)
        else:
            # Если колонки статуса нет, создаем фиктивную целевую переменную
            print(" Колонка 'статус_поиска' не найдена, используем случайные данные для демонстрации")
            np.random.seed(42)
            df['is_success'] = np.random.choice([0, 1], size=len(df), p=[0.7, 0.3])
        
        # Базовый уровень успешности
        base_success_rate = df['is_success'].mean()
        print(f" Базовый уровень успешности: {base_success_rate:.1%}")
        print(f" Всего объявлений: {len(df)}, успешных: {df['is_success'].sum()}")
        
        # Рассчитываем успешность для каждого признака
        features_to_analyze = [
            'тип_объявления', 'тип_животного', 'пол', 'возраст', 
            'окрас', 'есть_фото', 'есть_контакты'
        ]
        
        for feature in features_to_analyze:
            if feature in df.columns:
                success_rates = {}
                for value in df[feature].unique():
                    mask = df[feature] == value
                    if mask.sum() >= 1:  # уменьшил минимальное количество до 1
                        success_rate = df[mask]['is_success'].mean()
                        success_rates[value] = success_rate
                
                if success_rates:
                    self.success_rates[feature] = success_rates
                    print(f"\n {feature}:")
                    for value, rate in sorted(success_rates.items(), key=lambda x: x[1], reverse=True):
                        count = df[df[feature] == value].shape[0]
                        print(f"   {value}: {rate:.1%} ({count} объявлений)")
        
        # Веса для числовых признаков (на основе корреляции)
        numeric_features = ['количество_фото', 'длина_описания', 'количество_комментариев']
        for feature in numeric_features:
            if feature in df.columns:
                df[feature] = pd.to_numeric(df[feature], errors='coerce').fillna(0)
                correlation = df[feature].corr(df['is_success'])
                self.feature_weights[feature] = correlation
                print(f"\n {feature}: корреляция с успехом = {correlation:.3f}")
        
        return base_success_rate
    
    def predict_success(self, ad_data):
        """Прогнозирует вероятность успеха для нового объявления"""
        probability = 0.5  # начальная вероятность
        factors = []
        
        # Учитываем категориальные признаки (ИСПРАВЛЕНО: безопасный доступ)
        for feature, value in ad_data.items():
            if (feature in self.success_rates and 
                value in self.success_rates[feature]):
                feature_prob = self.success_rates[feature][value]
                # Взвешиваем влияние каждого фактора
                weight = 0.1  # небольшой вес для каждого признака
                probability += (feature_prob - 0.5) * weight
                factors.append(f"{feature}={value}: {feature_prob:.1%}")
            elif feature in self.success_rates:
                # Если значение не найдено в исторических данных, используем среднее
                avg_prob = np.mean(list(self.success_rates[feature].values()))
                probability += (avg_prob - 0.5) * 0.05  # меньший вес
                factors.append(f"{feature}={value}: ~{avg_prob:.1%} (среднее)")
        
        # Учитываем числовые признаки (ИСПРАВЛЕНО: безопасный доступ)
        if 'количество_фото' in ad_data and 'количество_фото' in self.feature_weights:
            photo_count = ad_data['количество_фото']
            if not isinstance(photo_count, (int, float)):
                photo_count = 0
            photo_effect = min(photo_count * 0.02, 0.1)  # максимум +10%
            probability += photo_effect
            factors.append(f"фото: +{photo_effect:.1%}")
        
        if 'длина_описания' in ad_data and 'длина_описания' in self.feature_weights:
            desc_length = ad_data['длина_описания']
            if not isinstance(desc_length, (int, float)):
                desc_length = 0
            desc_effect = min(desc_length * 0.001, 0.05)  # максимум +5%
            probability += desc_effect
            factors.append(f"описание: +{desc_effect:.1%}")
        
        # Бонусы за важные факторы (ИСПРАВЛЕНО: безопасный доступ)
        if ad_data.get('есть_фото') == 'да':
            probability += 0.08
            factors.append("наличие фото: +8%")
            
        if ad_data.get('есть_контакты') == 'да':
            probability += 0.07
            factors.append("контакты: +7%")
            
        if ad_data.get('окрас', 'не указан') != 'не указан':
            probability += 0.04
            factors.append("указан окрас: +4%")
            
        if ad_data.get('возраст', 'не указан') != 'не указан':
            probability += 0.03
            factors.append("указан возраст: +3%")
        
        # Ограничиваем вероятность от 0 до 1
        probability = max(0.05, min(0.95, probability))
        
        return {
            'probability': probability,
            'success_chance': f"{probability * 100:.1f}%",
            'prediction': '✅ ВЫСОКАЯ' if probability > 0.6 else '⚠️ СРЕДНЯЯ' if probability > 0.3 else '❌ НИЗКАЯ',
            'factors': factors
        }
    
    def get_recommendations(self, ad_data, current_probability):
        """Генерирует рекомендации для увеличения вероятности успеха"""
        recommendations = []
        
        # Проверяем фото (ИСПРАВЛЕНО: безопасный доступ)
        photos = ad_data.get('количество_фото', 0)
        if not isinstance(photos, (int, float)):
            photos = 0
            
        if photos == 0:
            recommendations.append(" Добавьте хотя бы одно фото питомца (+10-15% к шансам)")
        elif photos < 3:
            recommendations.append(" Добавьте больше фото с разных ракурсов (+5%)")
        
        # Проверяем описание
        desc_length = ad_data.get('длина_описания', 0)
        if not isinstance(desc_length, (int, float)):
            desc_length = 0
            
        if desc_length < 20:
            recommendations.append(" Составьте более подробное описание (+5-10%)")
        
        # Проверяем контакты
        if ad_data.get('есть_контакты', 'нет') == 'нет':
            recommendations.append(" Укажите контактные данные (+10%)")
        
        # Проверяем детали
        if ad_data.get('окрас', 'не указан') == 'не указан':
            recommendations.append(" Укажите точный окрас и особые приметы (+5%)")
        
        if ad_data.get('возраст', 'не указан') == 'не указан':
            recommendations.append(" Укажите возраст питомца (+3%)")
        
        # Общие рекомендации по вероятности
        if current_probability < 0.3:
            recommendations.append(" Рассмотрите возможность размещения в соцсетях и местных группах")
        elif current_probability < 0.5:
            recommendations.append(" Регулярно обновляйте объявление и отвечайте на комментарии")
        
        return recommendations

def interactive_prediction_simple():
    """Упрощенный интерактивный режим прогнозирования"""
    predictor = SimplePetPredictor()
    
    # Ищем CSV файл для обучения
    csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
    if not csv_files:
        print("❌ CSV файлы не найдены в текущей папке!")
        print(" Содержимое папки:")
        for f in os.listdir('.'):
            print(f"   - {f}")
        return
    
    file_name = csv_files[0]
    print(f" Загружаем данные из: {file_name}")
    
    try:
        df = pd.read_csv(file_name, encoding='utf-8')
        print(f" Загружено {len(df)} строк, колонки: {list(df.columns)}")
        
        base_rate = predictor.calculate_success_rates(df)
        
        print("\n" + "="*60)
        print(" РЕЖИМ ПРОГНОЗИРОВАНИЯ")
        print("="*60)
        print(" Подсказка: нажимайте Enter для использования значений по умолчанию")
        
        while True:
            print("\n" + "-"*40)
            print(" Введите данные нового объявления:")
            
            # Ввод данных с значениями по умолчанию
            ad_type = input("Тип объявления (потерян/найден) [потерян]: ").strip().lower() or "потерян"
            animal_type = input("Тип животного (собака/кошка) [собака]: ").strip().lower() or "собака"
            gender = input("Пол (мужской/женский/не указан) [не указан]: ").strip().lower() or "не указан"
            age = input("Возраст (например: 2 года, 6 мес) [не указан]: ").strip().lower() or "не указан"
            color = input("Окрас (например: белый, черный) [не указан]: ").strip().lower() or "не указан"
            has_photos = input("Есть фото? (да/нет) [да]: ").strip().lower() or "да"
            photo_count = input("Количество фото [1]: ").strip() or "1"
            desc_length = input("Длина описания (слов) [10]: ").strip() or "10"
            has_contacts = input("Есть контакты? (да/нет) [да]: ").strip().lower() or "да"
            
            # Формируем данные для прогноза
            new_ad = {
                'тип_объявления': ad_type,
                'тип_животного': animal_type,
                'пол': gender,
                'возраст': age,
                'окрас': color,
                'есть_фото': has_photos,
                'количество_фото': int(photo_count) if photo_count.isdigit() else 1,
                'длина_описания': int(desc_length) if desc_length.isdigit() else 10,
                'есть_контакты': has_contacts
            }
            
            try:
                # Прогнозируем
                result = predictor.predict_success(new_ad)
                
                print(f"\n РЕЗУЛЬТАТ ПРОГНОЗА:")
                print(f"   Вероятность успеха: {result['success_chance']}")
                print(f"   Оценка: {result['prediction']}")
                
                # Показываем влияющие факторы
                if result['factors']:
                    print(f"\n ВЛИЯЮЩИЕ ФАКТОРЫ:")
                    for factor in result['factors'][:8]:  # показываем первые 8 факторов
                        print(f"   • {factor}")
                
                # Рекомендации
                recommendations = predictor.get_recommendations(new_ad, result['probability'])
                if recommendations:
                    print(f"\n РЕКОМЕНДАЦИИ ДЛЯ УЛУЧШЕНИЯ:")
                    for i, rec in enumerate(recommendations[:5], 1):  # показываем первые 5 рекомендаций
                        print(f"   {i}. {rec}")
                
            except Exception as e:
                print(f"❌ Ошибка прогнозирования: {e}")
                print(" Попробуйте ввести данные еще раз")
            
            # Продолжить или выйти
            print("\n" + "-"*40)
            continue_pred = input("Продолжить прогнозирование? (да/нет) [да]: ").strip().lower() or "да"
            if continue_pred not in ['да', 'д', 'y', 'yes', '']:
                print(" До свидания! Спасибо за использование программы!")
                break
                
    except Exception as e:
        print(f"❌ Ошибка загрузки файла: {e}")
        print(" Проверьте, что CSV файл корректный и содержит нужные колонки")

if __name__ == "__main__":
    print("="*60)
    print(" ПРОГНОЗНАЯ МОДЕЛЬ PET911")
    print("="*60)
    
    interactive_prediction_simple()