import sqlite3
import os

db_path = 'instance/database.db'

if not os.path.exists(db_path):
    print(f"❌ База данных не найдена: {db_path}")
    exit()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Проверяем структуру
cursor.execute("PRAGMA table_info(doctor)")
columns = [col[1] for col in cursor.fetchall()]

print(f"Текущие колонки: {columns}")

# Добавляем новые колонки если их нет
if 'confirmed' not in columns:
    print("Добавляем 'confirmed'...")
    cursor.execute("ALTER TABLE doctor ADD COLUMN confirmed BOOLEAN DEFAULT 0")
    
if 'confirmed_on' not in columns:
    print("Добавляем 'confirmed_on'...")
    cursor.execute("ALTER TABLE doctor ADD COLUMN confirmed_on DATETIME")

# Подтверждаем всех существующих докторов
cursor.execute("UPDATE doctor SET confirmed = 1 WHERE confirmed IS NULL OR confirmed = 0")

conn.commit()
conn.close()

print("✅ Миграция завершена!")