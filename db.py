import pymysql
from config import DB_CONFIG


def get_connection():
    try:
        connection = pymysql.connect(**DB_CONFIG)
        return connection
    except pymysql.Error as e:
        print(f"Ошибка подключения к БД: {e}")
        return None


def create_database():
    try:
        config = DB_CONFIG.copy()
        database = config.pop('database')
        connection = pymysql.connect(**config)
        cursor = connection.cursor()
        cursor.execute(f"create database if not exists {database} character set utf8mb4 collate utf8mb4_unicode_ci")
        connection.commit()
        cursor.close()
        connection.close()
    except pymysql.Error as e:
        print(f"Ошибка создания БД: {e}")


def run_migrations():
    connection = get_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        cursor.execute("""
            create table if not exists app_user (
                id int auto_increment primary key,
                login varchar(50) unique not null,
                password varchar(100) not null,
                role enum('ADMIN', 'CHIEF', 'PATIENT') not null,
                full_name varchar(200) not null,
                created_at timestamp default current_timestamp
            ) engine=InnoDB default charset=utf8mb4
        """)
        
        cursor.execute("""
            create table if not exists specialization (
                id int auto_increment primary key,
                name varchar(100) not null unique
            ) engine=InnoDB default charset=utf8mb4
        """)
        
        cursor.execute("""
            create table if not exists doctor (
                id int auto_increment primary key,
                full_name varchar(200) not null,
                specialization_id int not null,
                phone varchar(20),
                email varchar(100),
                foreign key (specialization_id) references specialization(id) on delete cascade
            ) engine=InnoDB default charset=utf8mb4
        """)
        
        cursor.execute("""
            create table if not exists patient (
                id int auto_increment primary key,
                medical_record_number varchar(50) unique not null,
                full_name varchar(200) not null,
                date_of_birth date not null,
                gender enum('М', 'Ж') not null,
                address text,
                phone varchar(20),
                email varchar(100),
                passport_series varchar(10),
                passport_number varchar(20),
                oms_policy varchar(50),
                dms_policy varchar(50),
                insurance_company varchar(200),
                insurance_type enum('ОМС', 'ДМС') default 'ОМС',
                created_at timestamp default current_timestamp
            ) engine=InnoDB default charset=utf8mb4
        """)
        
        cursor.execute("""
            create table if not exists appointment (
                id int auto_increment primary key,
                patient_id int not null,
                doctor_id int not null,
                appointment_date date not null,
                appointment_time time not null,
                appointment_type enum('Первичный', 'Повторный', 'Профилактический') not null,
                status enum('Запланирован', 'Пациент на приёме', 'Завершён', 'Не явился', 'Отменён') default 'Запланирован',
                cost decimal(10, 2) default 0.00,
                payment_method enum('Наличные', 'Карта', 'По полису') null,
                diagnosis text,
                prescription text,
                created_at timestamp default current_timestamp,
                foreign key (patient_id) references patient(id) on delete cascade,
                foreign key (doctor_id) references doctor(id) on delete cascade
            ) engine=InnoDB default charset=utf8mb4
        """)
        
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except pymysql.Error as e:
        print(f"Ошибка выполнения миграций: {e}")
        if connection:
            connection.close()
        return False


def insert_test_data():
    connection = get_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        cursor.execute("select count(*) from app_user")
        if cursor.fetchone()[0] > 0:
            cursor.close()
            connection.close()
            return True
        
        users = [
            ('admin', 'admin123', 'ADMIN', 'Администратор Регистратуры'),
            ('chief', 'chief123', 'CHIEF', 'Главный Врач'),
            ('patient1', 'patient123', 'PATIENT', 'Иванов Иван Иванович'),
            ('patient2', 'patient123', 'PATIENT', 'Петрова Мария Сергеевна')
        ]
        cursor.executemany("""
            insert into app_user (login, password, role, full_name) 
            values (%s, %s, %s, %s)
        """, users)

        specializations = [
            ('Терапевт',),
            ('Кардиолог',),
            ('Эндокринолог',),
            ('Хирург',),
            ('Невролог',)
        ]
        cursor.executemany("""
            insert into specialization (name) values (%s)
        """, specializations)
        
        doctors = [
            ('Смирнов Александр Петрович', 1, '+7-900-111-22-33', 'smirnov@clinic.ru'),
            ('Козлова Елена Викторовна', 2, '+7-900-222-33-44', 'kozlova@clinic.ru'),
            ('Волков Дмитрий Сергеевич', 3, '+7-900-333-44-55', 'volkov@clinic.ru'),
            ('Новикова Ольга Александровна', 1, '+7-900-444-55-66', 'novikova@clinic.ru')
        ]
        cursor.executemany("""
            insert into doctor (full_name, specialization_id, phone, email) 
            values (%s, %s, %s, %s)
        """, doctors)
        
        patients = [
            ('MR-001', 'Иванов Иван Иванович', '1980-05-15', 'М', 'г. Москва, ул. Ленина, д. 10', 
             '+7-900-555-66-77', 'ivanov@mail.ru', '4510', '123456', '1234567890123456', None, 
             'Страховая Компания 1', 'ОМС'),
            ('MR-002', 'Петрова Мария Сергеевна', '1990-08-20', 'Ж', 'г. Москва, ул. Пушкина, д. 5', 
             '+7-900-666-77-88', 'petrova@mail.ru', '4511', '234567', None, '9876543210987654', 
             'Страховая Компания 2', 'ДМС'),
            ('MR-003', 'Сидоров Петр Николаевич', '1975-12-10', 'М', 'г. Москва, ул. Гагарина, д. 15', 
             '+7-900-777-88-99', 'sidorov@mail.ru', '4512', '345678', '1111222233334444', None, 
             'Страховая Компания 1', 'ОМС')
        ]
        cursor.executemany("""
            insert into patient (medical_record_number, full_name, date_of_birth, gender, address, 
            phone, email, passport_series, passport_number, oms_policy, dms_policy, insurance_company, insurance_type) 
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, patients)
        
        from datetime import date, time, timedelta
        today = date.today()
        
        appointments = [
            (1, 1, today + timedelta(days=1), time(10, 0), 'Первичный', 'Запланирован', 1500.00, None, None, None),
            (2, 2, today + timedelta(days=2), time(14, 30), 'Повторный', 'Запланирован', 2000.00, None, None, None),
            (1, 3, today - timedelta(days=1), time(11, 0), 'Профилактический', 'Завершён', 1000.00, 'Карта', 
             'Гипертония', 'Принимать препарат X по 1 таблетке утром'),
            (3, 1, today - timedelta(days=2), time(15, 0), 'Первичный', 'Завершён', 1500.00, 'Наличные', 
             'ОРВИ', 'Постельный режим, обильное питье'),
            (2, 4, today - timedelta(days=3), time(9, 0), 'Первичный', 'Не явился', 1500.00, None, None, None)
        ]
        cursor.executemany("""
            insert into appointment (patient_id, doctor_id, appointment_date, appointment_time, 
            appointment_type, status, cost, payment_method, diagnosis, prescription) 
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, appointments)
        
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except pymysql.Error as e:
        print(f"Ошибка заполнения тестовыми данными: {e}")
        if connection:
            connection.close()
        return False


def init_database():
    create_database()
    if run_migrations():
        insert_test_data()
        return True
    return False
