import pymysql
from config import DB_CONFIG


def authenticate(login, password):
    try:
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        cursor.execute("""
            select id, login, role, full_name 
            from app_user 
            where login = %s and password = %s
        """, (login, password))
        
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if result:
            return {
                'id': result[0],
                'login': result[1],
                'role': result[2],
                'full_name': result[3]
            }
        return None
    except pymysql.Error as e:
        print(f"Ошибка авторизации: {e}")
        return None
