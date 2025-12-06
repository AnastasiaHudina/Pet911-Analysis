import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
import os

warnings.filterwarnings("ignore")

# Настройка графиков
plt.rcParams['font.size'] = 12
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
sns.set_style("whitegrid")

# 🔽 Пути к файлам
lost_file = 'Dataset_final_Pet911_lost.csv'
found_file = 'dataset_final_Pet911_found.csv'

# Создаём папки
os.makedirs('Результаты 5 главы анализа', exist_ok=True)

print("🔍 Начало загрузки данных...")

# Столбцы для lost
column_names_lost = [
    'url', 'id', 'тип объявления', 'регион', 'статус', 'тип_животного',
    'окрас', 'порода', 'место события', 'дата_публикации', 'пол', 'возраст',
    'описание', 'Длина_описания_в_словах', 'наличие_описания', 'есть_фото',
    'количество_фото', 'количество_комментариев', 'дата пропажи', 'есть_контакты'
]

# Столбцы для found
column_names_found = [
    'url', 'id', 'тип объявления', 'регион', 'статус', 'тип_животного',
    'окрас', 'порода', 'место события', 'дата_публикации', 'пол', 'возраст',
    'описание', 'Длина_описания_в_словах', 'наличие_описания', 'есть_фото',
    'количество_фото', 'количество_комментариев', 'дата находки', 'есть_контакты'
]


def load_data(file_path, columns):
    try:
        df = pd.read_csv(file_path, names=columns, header=None, encoding='utf-8')
        # Удаляем первую строку, если это заголовки
        if isinstance(df.iloc[0]['url'], str) and 'http' not in df.iloc[0]['url']:
            df = df.drop(0).reset_index(drop=True)
        return df
    except Exception as e:
        print(f"❌ Ошибка загрузки {file_path}: {e}")
        return pd.DataFrame()


# Загружаем данные
lost_df = load_data(lost_file, column_names_lost)
found_df = load_data(found_file, column_names_found)

if lost_df.empty or found_df.empty:
    print("❌ Не удалось загрузить данные. Проверьте пути к файлам.")
    exit()

print("✅ Данные успешно загружены")
print(f"📊 Пропавшие: {len(lost_df)}, Найденные: {len(found_df)}")

# Словарь замены русских дней недели
day_map = {'пн': 'Mon', 'вт': 'Tue', 'ср': 'Wed', 'чт': 'Thu', 'пт': 'Fri', 'сб': 'Sat', 'вс': 'Sun'}


def parse_russian_date(date_str):
    if pd.isna(date_str) or str(date_str).strip() in ['Неизвестно', '', 'nan']:
        return pd.NaT
    try:
        parts = str(date_str).strip().split(', ')
        if len(parts) != 2:
            return pd.NaT
        day_en = day_map.get(parts[0].strip())
        if not day_en:
            return pd.NaT
        full_str = f"{day_en}, {parts[1]}"
        return pd.to_datetime(full_str, format='%a, %d.%m.%Y', errors='coerce')
    except:
        return pd.NaT


# Парсинг дат
for col in ['дата_публикации', 'дата пропажи']:
    if col in lost_df.columns:
        lost_df[col] = lost_df[col].astype(str).apply(parse_russian_date)
lost_df['время_до_публикации'] = (lost_df['дата_публикации'] - lost_df['дата пропажи']).dt.days

for col in ['дата_публикации', 'дата находки']:
    if col in found_df.columns:
        found_df[col] = found_df[col].astype(str).apply(parse_russian_date)
found_df['время_до_публикации'] = (found_df['дата_публикации'] - found_df['дата находки']).dt.days

# Очистка возраста
def clean_age(age):
    if pd.isna(age) or str(age).strip() in ['Неизвестно', '', 'nan', 'не указан']: return np.nan
    try:
        num_str = ''.join(filter(str.isdigit, str(age).split(',')[0]))
        return float(num_str) if num_str else np.nan
    except: return np.nan

lost_df['возраст_число'] = lost_df['возраст'].apply(clean_age)
found_df['возраст_число'] = found_df['возраст'].apply(clean_age)

# Тип местности
urban_keywords = ['москва', 'санкт-петербург', 'vidnoye', 'kolomna', 'obninsk', 'moskva']
lost_df['тип_местности'] = lost_df['регион'].astype(str).str.lower().apply(
    lambda x: 'город' if any(city in x for city in urban_keywords) else 'область/село'
)
found_df['тип_местности'] = found_df['регион'].astype(str).str.lower().apply(
    lambda x: 'город' if any(city in x for city in urban_keywords) else 'область/село'
)

# Породистостьdjphfcn
def is_pedigree(breed):
    if pd.isna(breed) or breed in ['Неизвестно', 'метис']: return 'Нет'
    return 'Да'

lost_df['породистое'] = lost_df['порода'].apply(is_pedigree)
found_df['породистое'] = found_df['порода'].apply(is_pedigree)

# Замена True/False → "Да"/"Нет"
#bool_cols = ['есть_фото', 'наличие_описания', 'есть_контакты']
#for col in bool_cols:
#    if col in lost_df.columns:
#        lost_df[col] = lost_df[col].map({True: 'Да', False: 'Нет'}, na_action='ignore')
#    if col in found_df.columns:
#        found_df[col] = found_df[col].map({True: 'Да', False: 'Нет'}, na_action='ignore')

print("\n📌 Генерация графиков по пропаже...")

success_mask_lost = lost_df['статус'] == 'питомец найден'

# 1. Время до публикации
valid_data = lost_df[['статус', 'время_до_публикации']].dropna()
if len(valid_data) > 0 and valid_data['статус'].nunique() > 1:
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=valid_data, x='статус', y='время_до_публикации')
    plt.title("Влияние скорости публикации на успех (При пропаже)")
    plt.ylabel("Время до публикации, дни")
    plt.xlabel("Статус объявления")
    plt.tight_layout()
    plt.savefig('Результаты 5 главы анализа/5.1. Влияние скорости публикации на успех (При пропаже).png', dpi=150)
    plt.close()

# 2. Возраст
age_data = lost_df[lost_df['возраст_число'].notna()]
if len(age_data) > 0:
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=age_data, x='статус', y='возраст_число')
    plt.title("Возраст (При пропаже)")
    plt.ylabel("Возраст, лет")
    plt.xlabel("Статус")
    plt.tight_layout()
    plt.savefig('Результаты 5 главы анализа/5.2. Возраст (При пропаже).png', dpi=150)
    plt.close()

# 3. Местность
plt.figure(figsize=(8, 6))
terrain_success = lost_df.groupby('тип_местности')['статус'].apply(lambda x: (x == 'питомец найден').mean())
terrain_success.plot(kind='bar', color=['skyblue', 'lightgreen'])
plt.title("Успешность по типу местности (При пропаже)")
plt.ylabel("Доля найденных")
plt.xlabel("Тип местности")
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig('Результаты 5 главы анализа/5.3. Успешность по типу местности (При пропаже).png', dpi=150)
plt.close()


# 4. Породистость
plt.figure(figsize=(8, 6))
breed_success = lost_df.groupby('породистое')['статус'].apply(lambda x: (x == 'питомец найден').mean())
breed_success.plot(kind='bar', color=['orange', 'purple'])
plt.title("Влияние породистости на успех (При пропаже)")
plt.ylabel("Доля найденных")
plt.xlabel("Породистое животное")
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig('Результаты 5 главы анализа/5.4. Влияние породистости на успех (При пропаже).png', dpi=150)
plt.close()

print("\n📌 Генерация графиков по находке...")

return_mask = found_df['статус'] == 'хозяин найден'

# 1. Время до публикации
valid_data = found_df[['статус', 'время_до_публикации']].dropna()
if len(valid_data) > 0 and valid_data['статус'].nunique() > 1:
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=valid_data, x='статус', y='время_до_публикации')
    plt.title("Влияние скорости публикации на успех (При находке)")
    plt.ylabel("Время до публикации, дни")
    plt.xlabel("Статус")
    plt.tight_layout()
    plt.savefig('Результаты 5 главы анализа/5.5. Влияние скорости публикации на успех (При находке).png', dpi=150)
    plt.close()

# 2. Местность
plt.figure(figsize=(8, 6))
place_success = found_df.groupby('тип_местности')['статус'].apply(lambda x: (x == 'хозяин найден').mean())
place_success.plot(kind='bar', color=['gold', 'brown'])
plt.title("Успешность по типу местности (При находке)")
plt.ylabel("Доля возвратов")
plt.xlabel("Тип местности")
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig('Результаты 5 главы анализа/5.6. Успешность по типу местности (При находке).png', dpi=150)
plt.close()


# 3. Породистость
plt.figure(figsize=(8, 6))
breed_return = found_df.groupby('породистое')['статус'].apply(lambda x: (x == 'хозяин найден').mean())
breed_return.plot(kind='bar', color=['pink', 'violet'])
plt.title("Влияние породистости на успех (При находке)")
plt.ylabel("Доля возвратов")
plt.xlabel("Породистое животное")
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig('Результаты 5 главы анализа/5.7. Влияние породистости на успех (При находке).png', dpi=150)
plt.close()

print("\n📌 Сравнительный анализ...")

mean_delay_lost = lost_df['время_до_публикации'].mean()
mean_delay_found = found_df['время_до_публикации'].mean()

breed_eff_lost = lost_df.groupby('породистое')['статус'].apply(lambda x: (x == 'питомец найден').mean())
breed_eff_found = found_df.groupby('породистое')['статус'].apply(lambda x: (x == 'хозяин найден').mean())

# Собираем вывод
output_lines = []
output_lines.append("📌 5.1. АНАЛИЗ ОБЪЯВЛЕНИЙ О ПРОПАЖЕ ЖИВОТНОГО")
output_lines.append(f" • Всего объявлений: {len(lost_df)}")
output_lines.append(f" • Найдено: {success_mask_lost.sum()}")
output_lines.append(f" • В поиске: {len(lost_df) - success_mask_lost.sum()}")
output_lines.append(f" • Среднее время до публикации: {mean_delay_lost:.1f} дней")

output_lines.append("\n📌 5.2. АНАЛИЗ ОБЪЯВЛЕНИЙ О НАХОДКЕ ЖИВОТНОГО")
output_lines.append(f" • Всего объявлений: {len(found_df)}")
output_lines.append(f" • Хозяин найден: {return_mask.sum()}")
output_lines.append(f" • Ищут хозяина: {len(found_df) - return_mask.sum()}")
output_lines.append(f" • Среднее время до публикации: {mean_delay_found:.1f} дней")

output_lines.append("\n📌 5.3. СРАВНЕНИЕ: ПРОПАЖА vs НАХОДКА")
output_lines.append(f" • Пропажа: {mean_delay_lost:.1f} дней, Находка: {mean_delay_found:.1f} дней")
output_lines.append(f" • Эффект породистости (пропажа): +{breed_eff_lost.get('Да', 0) - breed_eff_lost.get('Нет', 0):.1%}")
output_lines.append(f" • Эффект породистости (находка): +{breed_eff_found.get('Да', 0) - breed_eff_found.get('Нет', 0):.1%}")

if mean_delay_found < mean_delay_lost:
    output_lines.append("✅ Публикация о находке происходит быстрее.")
else:
    output_lines.append("⚠️ Люди медленнее публикуют находки.")

if breed_eff_found.get('Да', 0) > breed_eff_lost.get('Да', 0):
    output_lines.append("✅ Породистые животные чаще узнаются при находке.")
else:
    output_lines.append("💡 Порода важна, но не решающе.")

# Сохраняем в txt-файл
with open('Результаты 5 главы анализа/Вывод 5 главы.txt', 'w', encoding='utf-8') as f:
    for line in output_lines:
        print(line)
        f.write(line + '\n')

print("✅ Все результаты сохранены в папке 'Результаты 5 главы анализа'")
print(f"\n✅ Вывод сохранён в файле 'Вывод 5 главы.txt'")
