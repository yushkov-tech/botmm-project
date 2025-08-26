import os
# Путь к базе данных
db_path = r'c:\Users\yushkov.mi\Desktop\bor-project\messages.db'
# Удаление базы данных
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"База данных {db_path} была удалена.")
else:
    print(f"База данных {db_path} не найдена.")