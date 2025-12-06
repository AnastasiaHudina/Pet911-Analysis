# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
import os
import json

warnings.filterwarnings('ignore')

class PetSearchPredictor:
    def __init__(self):
        self.stats_lost = None
        self.stats_found = None
        self.load_statistics()
    
    def load_statistics(self):
        """Загружает статистику из сохраненных файлов"""
        print("📊 Загрузка статистики для прогнозирования...")
        
        stats_dir = '3p1_statistics'
        
        # Загружаем статистику для потерянных
        lost_file = os.path.join(stats_dir, 'pet911_lost_statistics.json')
        if os.path.exists(lost_file):
            with open(lost_file, 'r', encoding='utf-8') as f:
                self.stats_lost = json.load(f)
            print(f"✅ Статистика для потерянных загружена")
        else:
            print(f"❌ Файл статистики для потерянных не найден: {lost_file}")
        
        # Загружаем статистику для найденных
        found_file = os.path.join(stats_dir, 'pet911_found_statistics.json')
        if os.path.exists(found_file):
            with open(found_file, 'r', encoding='utf-8') as f:
                self.stats_found = json.load(f)
            print(f"✅ Статистика для найденных загружена")
        else:
            print(f"❌ Файл статистики для найденных не найден: {found_file}")
    
    def calculate_probability(self, ad_data, ad_type):
        """Рассчитывает вероятность успеха на основе реальной статистики"""
        if ad_type == 'lost' and self.stats_lost:
            stats = self.stats_lost
            base_rate = stats['base_success_rate']
        elif ad_type == 'found' and self.stats_found:
            stats = self.stats_found
            base_rate = stats['base_success_rate']
        else:
            # Fallback если статистика не загружена
            base_rate = 0.15
            stats = {}
        
        probability = base_rate
        factors_log = []
        
        # Влияние типа животного
        animal_type = ad_data.get('animal_type', 'другое').lower()
        if 'animal_success_rates' in stats and animal_type in stats['animal_success_rates']:
            animal_rate = stats['animal_success_rates'][animal_type]
            animal_impact = animal_rate - base_rate
            probability += animal_impact
            factors_log.append(f"Тип животного ({animal_type}): {animal_impact:+.1%}")
        else:
            factors_log.append(f"Тип животного ({animal_type}): статистика недоступна")
        
        # Влияние фото
        has_photos = ad_data.get('has_photos', 'нет').lower()
        if 'photo_statistics' in stats and 'has_photo_impact' in stats['photo_statistics']:
            photo_stats = stats['photo_statistics']['has_photo_impact']
            if has_photos == 'нет':
                photo_impact = photo_stats.get('0', 0) - base_rate
                probability += photo_impact
                factors_log.append(f"Отсутствие фото: {photo_impact:+.1%}")
            else:
                photo_count = ad_data.get('photo_count', 1)
                # Используем статистику для фото > 0
                photo_impact = photo_stats.get('1', base_rate) - base_rate
                probability += photo_impact
                factors_log.append(f"Наличие фото: {photo_impact:+.1%}")
        
        # Влияние описания
        has_description = ad_data.get('has_description', 'нет').lower()
        if 'description_statistics' in stats and 'has_description_impact' in stats['description_statistics']:
            desc_stats = stats['description_statistics']['has_description_impact']
            if has_description == 'нет':
                desc_impact = desc_stats.get('0', 0) - base_rate
                probability += desc_impact
                factors_log.append(f"Отсутствие описания: {desc_impact:+.1%}")
            else:
                desc_impact = desc_stats.get('1', base_rate) - base_rate
                probability += desc_impact
                desc_length = ad_data.get('desc_length', 0)
                factors_log.append(f"Наличие описания ({desc_length} слов): {desc_impact:+.1%}")
        
        # Влияние контактов
        has_contacts = ad_data.get('has_contacts', 'нет').lower()
        if 'contacts_impact' in stats:
            contacts_stats = stats['contacts_impact']
            if has_contacts == 'нет':
                contacts_impact = contacts_stats.get('0', 0) - base_rate
                probability += contacts_impact
                factors_log.append(f"Отсутствие контактов: {contacts_impact:+.1%}")
            else:
                contacts_impact = contacts_stats.get('1', base_rate) - base_rate
                probability += contacts_impact
                factors_log.append(f"Наличие контактов: {contacts_impact:+.1%}")
        
        # Ограничиваем вероятность
        probability = max(0.01, min(0.95, probability))
        
        return probability, factors_log, base_rate

    # ... остальные методы (get_recommendations, collect_ad_data, display_prediction и т.д.)
    # остаются такими же как в предыдущей версии, но используют загруженную статистику

    def get_recommendations(self, ad_data, current_probability, ad_type, base_rate):
        """Генерирует рекомендации на основе реальной статистики"""
        recommendations = []
        
        animal_type = ad_data.get('animal_type', '').lower()
        
        # Рекомендации на основе введенных данных
        if ad_data.get('has_photos', 'нет') == 'нет':
            recommendations.append("📸 Добавьте фото питомца - по статистике это значительно увеличивает шансы")
        
        if ad_data.get('has_description', 'нет') == 'нет':
            recommendations.append("📝 Добавьте описание питомца - подробности помогают в поиске")
        
        if ad_data.get('has_contacts', 'нет') == 'нет':
            recommendations.append("📞 Укажите контакты - без них связь невозможна")
        
        # Специфические рекомендации
        if ad_type == 'lost':
            recommendations.append("📍 Укажите точное место и время пропажи")
            recommendations.append("🕒 Разместите объявление в местных группах")
        else:
            recommendations.append("📍 Укажите точное место и время находки")
            recommendations.append("🏠 Обратитесь в местные приюты")
        
        return recommendations

    def collect_ad_data(self, ad_type):
        """Сбор данных объявления от пользователя"""
        print("\n📝 Введите данные объявления:")
        print("💡 Подсказка: нажимайте Enter для использования значений по умолчанию")
        
        ad_data = {}
        
        # Тип животного
        animal_type = input("\nТип животного (собака/кошка/птица/грызун/рептилия/другое) [собака]: ").strip()
        ad_data['animal_type'] = animal_type if animal_type else 'собака'
        
        # Фото
        has_photos = input("\nЕсть фото? (да/нет) [да]: ").strip().lower()
        ad_data['has_photos'] = has_photos if has_photos else 'да'
        
        if ad_data['has_photos'] == 'да':
            photo_count_input = input("Количество фото [3]: ").strip()
            ad_data['photo_count'] = int(photo_count_input) if photo_count_input.isdigit() else 3
        else:
            ad_data['photo_count'] = 0
        
        # Описание
        has_description = input("\nЕсть описание? (да/нет) [да]: ").strip().lower()
        ad_data['has_description'] = has_description if has_description else 'да'
        
        if ad_data['has_description'] == 'да':
            desc_length_input = input("Длина описания (количество слов) [25]: ").strip()
            ad_data['desc_length'] = int(desc_length_input) if desc_length_input.isdigit() else 25
        else:
            ad_data['desc_length'] = 0
        
        # Контакты
        has_contacts = input("\nУказаны контакты? (да/нет) [да]: ").strip().lower()
        ad_data['has_contacts'] = has_contacts if has_contacts else 'да'
        
        return ad_data

    def predict_for_lost(self):
        """Прогноз для потерянного животного"""
        if not self.stats_lost:
            print("❌ Статистика для потерянных животных не загружена!")
            return
        
        print("\n" + "="*60)
        print("🐕 ПРОГНОЗ ДЛЯ ПОТЕРЯННОГО ЖИВОТНОГО")
        print("="*60)
        base_rate = self.stats_lost['base_success_rate']
        print(f"📊 Базовый уровень успешности: {base_rate*100:.1f}%")
        
        ad_data = self.collect_ad_data('lost')
        probability, factors_log, base_rate = self.calculate_probability(ad_data, 'lost')
        
        self.display_prediction(probability, factors_log, ad_data, 'lost', base_rate)
        
        return probability, ad_data

    def predict_for_found(self):
        """Прогноз для найденного животного"""
        if not self.stats_found:
            print("❌ Статистика для найденных животных не загружена!")
            return
        
        print("\n" + "="*60)
        print("🏠 ПРОГНОЗ ДЛЯ НАЙДЕННОГО ЖИВОТНОГО")
        print("="*60)
        base_rate = self.stats_found['base_success_rate']
        print(f"📊 Базовый уровень успешности: {base_rate*100:.1f}%")
        
        ad_data = self.collect_ad_data('found')
        probability, factors_log, base_rate = self.calculate_probability(ad_data, 'found')
        
        self.display_prediction(probability, factors_log, ad_data, 'found', base_rate)
        
        return probability, ad_data

    def display_prediction(self, probability, factors_log, ad_data, ad_type, base_rate):
        """Отображение результатов прогноза"""
        print(f"\n🎯 РЕЗУЛЬТАТ ПРОГНОЗА:")
        print(f"   Базовый уровень: {base_rate*100:.1f}%")
        print(f"   Ваша вероятность: {probability*100:.1f}%")
        
        difference = probability - base_rate
        if difference > 0.05:
            comparison = f"✅ Выше базового на {difference*100:+.1f}%"
        elif difference < -0.05:
            comparison = f"❌ Ниже базового на {difference*100:+.1f}%"
        else:
            comparison = f"⚠️ На уровне базового ({difference*100:+.1f}%)"
        print(f"   Сравнение: {comparison}")
        
        print(f"\n📊 ВЛИЯЮЩИЕ ФАКТОРЫ:")
        for factor in factors_log:
            print(f"   • {factor}")
        
        recommendations = self.get_recommendations(ad_data, probability, ad_type, base_rate)
        if recommendations:
            print(f"\n💡 РЕКОМЕНДАЦИИ:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        
        self.plot_probability(probability, base_rate, ad_type)

    def plot_probability(self, probability, base_rate, ad_type):
        """Визуализация вероятности успеха"""
        plt.figure(figsize=(12, 3))
        
        gradient = np.linspace(0, 1, 100).reshape(1, -1)
        plt.imshow(gradient, aspect='auto', cmap='RdYlGn', extent=[0, 100, 0, 1])
        
        plt.axvline(x=base_rate*100, color='blue', linestyle='-', linewidth=3, alpha=0.7, label='Базовый уровень')
        plt.axvline(x=probability*100, color='black', linestyle='--', linewidth=3, label='Ваша вероятность')
        
        plt.text(probability*100, 0.5, f'{probability*100:.1f}%', 
                ha='center', va='center', backgroundcolor='white', fontweight='bold', fontsize=12)
        
        plt.text(base_rate*100, 0.8, f'Базовый: {base_rate*100:.1f}%', 
                ha='center', va='center', backgroundcolor='lightblue', fontweight='bold')
        
        title = 'Вероятность нахождения питомца' if ad_type == 'lost' else 'Вероятность нахождения хозяина'
        plt.title(title, fontsize=14, fontweight='bold')
        plt.xlabel('Вероятность успеха, %', fontsize=12)
        plt.yticks([])
        plt.xlim(0, 100)
        plt.legend(loc='upper right')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()

def main():
    """Основная функция программы прогнозирования"""
    print("🎯 ПРОГНОЗНАЯ МОДЕЛЬ ДЛЯ PET911")
    print("=" * 60)
    print("📊 Модель использует реальную статистику из анализа данных")
    
    predictor = PetSearchPredictor()
    
    while True:
        print("\n📋 ВЫБЕРИТЕ ТИП ПРОГНОЗА:")
        print("1. 🐕 Прогноз для потерянного животного")
        print("2. 🏠 Прогноз для найденного животного") 
        print("3. ❌ Выход")
        
        choice = input("\nВаш выбор (1-3): ").strip()
        
        if choice == "1":
            predictor.predict_for_lost()
        elif choice == "2":
            predictor.predict_for_found()
        elif choice == "3":
            print("👋 До свидания!")
            break
        else:
            print("❌ Неверный выбор, попробуйте снова")
        
        if choice in ["1", "2"]:
            continue_pred = input("\nПродолжить прогнозирование? (да/нет) [да]: ").strip().lower()
            if continue_pred not in ['', 'да', 'д', 'y', 'yes']:
                print("👋 До свидания!")
                break

if __name__ == "__main__":
    main()