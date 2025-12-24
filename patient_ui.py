from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QTableWidget, QTableWidgetItem,
                             QPushButton, QLabel, QComboBox, QDateEdit, QTimeEdit,
                             QMessageBox, QGroupBox, QTextEdit)
from PyQt6.QtCore import QDate, QTime, Qt
import pymysql
from config import DB_CONFIG
from datetime import datetime, timedelta

class PatientWindow(QMainWindow):

    def __init__(self, user_info):
        super().__init__()
        self.user_info = user_info
        self.setWindowTitle(f"Пациент - {user_info['full_name']}")
        self.setGeometry(100, 100, 1200, 700)

        self.patient_id = self.get_patient_id()
        if not self.patient_id:
            QMessageBox.critical(self, "Ошибка", "Не удалось найти данные пациента")
            self.close()
            return

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        tabs = QTabWidget()

        tabs.addTab(self.create_schedule_tab(), "Расписание врачей")
        tabs.addTab(self.create_booking_tab(), "Запись на приём")
        tabs.addTab(self.create_my_appointments_tab(), "Мои записи")
        tabs.addTab(self.create_medical_record_tab(), "Медицинская карта")

        layout.addWidget(tabs)
        central_widget.setLayout(layout)

    def get_connection(self):

        try:
            return pymysql.connect(**DB_CONFIG)
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка подключения к БД: {e}")
            return None

    def get_patient_id(self):

        connection = self.get_connection()
        if not connection:
            return None

        try:
            cursor = connection.cursor()
            cursor.execute("""
                select id from patient
                where full_name = %s
            """, (self.user_info['full_name'],))

            result = cursor.fetchone()
            patient_id = result[0] if result else None

            cursor.close()
            connection.close()
            return patient_id
        except pymysql.Error as e:
            if connection:
                connection.close()
            return None

    def create_schedule_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        filter_group = QGroupBox("Фильтры")
        filter_layout = QHBoxLayout()

        self.schedule_specialization = QComboBox()
        self.schedule_specialization.addItem("Все специализации", None)
        self.load_specializations_for_schedule()
        self.schedule_specialization.currentIndexChanged.connect(self.load_schedule)
        filter_layout.addWidget(QLabel("Специализация:"))
        filter_layout.addWidget(self.schedule_specialization)

        self.schedule_date = QDateEdit()
        self.schedule_date.setDate(QDate.currentDate())
        self.schedule_date.setMinimumDate(QDate.currentDate())
        self.schedule_date.setCalendarPopup(True)
        self.schedule_date.dateChanged.connect(self.load_schedule)
        filter_layout.addWidget(QLabel("Дата:"))
        filter_layout.addWidget(self.schedule_date)

        btn_refresh = QPushButton("Обновить")
        btn_refresh.clicked.connect(self.load_schedule)
        filter_layout.addWidget(btn_refresh)

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        self.schedule_table = QTableWidget()
        self.schedule_table.setColumnCount(5)
        self.schedule_table.setHorizontalHeaderLabels(["Врач", "Специализация", "Дата", "Время", "Доступность"])
        layout.addWidget(self.schedule_table)

        widget.setLayout(layout)
        self.load_schedule()
        return widget

    def load_specializations_for_schedule(self):

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()
            cursor.execute("select id, name from specialization order by name")
            specializations = cursor.fetchall()

            for spec_id, name in specializations:
                self.schedule_specialization.addItem(name, spec_id)

            cursor.close()
            connection.close()
        except pymysql.Error as e:
            if connection:
                connection.close()

    def load_schedule(self):

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()

            spec_id = self.schedule_specialization.currentData()
            selected_date = self.schedule_date.date().toPyDate()

            query = """
                select d.id, d.full_name, s.name,
                       count(case when a.appointment_date = %s and a.status not in ('Отменён', 'Не явился') then 1 end) as booked,
                       case
                           when count(case when a.appointment_date = %s and a.status not in ('Отменён', 'Не явился') then 1 end) < 8
                           then 'Есть места'
                           else 'Занято'
                       end as availability
                from doctor d
                left join specialization s on d.specialization_id = s.id
                left join appointment a on d.id = a.doctor_id
            """

            params = [selected_date, selected_date]

            if spec_id:
                query += " where d.specialization_id = %s"
                params.append(spec_id)

            query += " group by d.id, d.full_name, s.name"

            cursor.execute(query, params)
            doctors = cursor.fetchall()

            self.schedule_table.setRowCount(len(doctors))
            for row, (doctor_id, doctor_name, specialization, booked, availability) in enumerate(doctors):
                self.schedule_table.setItem(row, 0, QTableWidgetItem(doctor_name))
                self.schedule_table.setItem(row, 1, QTableWidgetItem(specialization or ""))
                self.schedule_table.setItem(row, 2, QTableWidgetItem(str(selected_date)))
                self.schedule_table.setItem(row, 3, QTableWidgetItem("9:00-17:00"))
                self.schedule_table.setItem(row, 4, QTableWidgetItem(availability))

            self.schedule_table.resizeColumnsToContents()
            cursor.close()
            connection.close()
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки расписания: {e}")
            if connection:
                connection.close()

    def create_booking_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        form_layout = QVBoxLayout()

        self.booking_specialization = QComboBox()
        self.load_specializations_for_booking()
        self.booking_specialization.currentIndexChanged.connect(self.load_doctors_for_booking)
        form_layout.addWidget(QLabel("Специализация:"))
        form_layout.addWidget(self.booking_specialization)

        self.booking_doctor = QComboBox()
        form_layout.addWidget(QLabel("Врач:"))
        form_layout.addWidget(self.booking_doctor)

        self.booking_date = QDateEdit()
        self.booking_date.setDate(QDate.currentDate())
        self.booking_date.setMinimumDate(QDate.currentDate())
        self.booking_date.setCalendarPopup(True)
        form_layout.addWidget(QLabel("Дата приёма:"))
        form_layout.addWidget(self.booking_date)

        self.booking_time = QComboBox()
        self.booking_time.addItems([
            "09:00", "10:00", "11:00", "12:00", "13:00",
            "14:00", "15:00", "16:00", "17:00"
        ])
        form_layout.addWidget(QLabel("Время приёма:"))
        form_layout.addWidget(self.booking_time)

        self.booking_cost = QLabel("Стоимость будет рассчитана автоматически")
        form_layout.addWidget(QLabel("Стоимость:"))
        form_layout.addWidget(self.booking_cost)

        btn_calculate = QPushButton("Рассчитать стоимость")
        btn_calculate.clicked.connect(self.calculate_booking_cost)
        form_layout.addWidget(btn_calculate)

        btn_book = QPushButton("Записаться на приём")
        btn_book.clicked.connect(self.book_appointment)
        form_layout.addWidget(btn_book)

        widget.setLayout(form_layout)
        return widget

    def load_specializations_for_booking(self):

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()
            cursor.execute("select id, name from specialization order by name")
            specializations = cursor.fetchall()

            self.booking_specialization.clear()
            for spec_id, name in specializations:
                self.booking_specialization.addItem(name, spec_id)

            cursor.close()
            connection.close()
        except pymysql.Error as e:
            if connection:
                connection.close()

    def load_doctors_for_booking(self):

        connection = self.get_connection()
        if not connection:
            return

        try:
            spec_id = self.booking_specialization.currentData()
            if not spec_id:
                self.booking_doctor.clear()
                return

            cursor = connection.cursor()
            cursor.execute("""
                select id, full_name from doctor
                where specialization_id = %s
                order by full_name
            """, (spec_id,))
            doctors = cursor.fetchall()

            self.booking_doctor.clear()
            for doctor_id, name in doctors:
                self.booking_doctor.addItem(name, doctor_id)

            cursor.close()
            connection.close()
        except pymysql.Error as e:
            if connection:
                connection.close()

    def calculate_booking_cost(self):

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()
            cursor.execute("select insurance_type from patient where id = %s", (self.patient_id,))
            result = cursor.fetchone()

            if not result:
                QMessageBox.warning(self, "Ошибка", "Не найдены данные пациента")
                return

            insurance_type = result[0]
            base_cost = 1500.00

            if insurance_type == 'ОМС':
                cost = base_cost * 0.5
            else:
                cost = base_cost

            self.booking_cost.setText(f"{cost:.2f} руб.")
            cursor.close()
            connection.close()
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка расчёта: {e}")
            if connection:
                connection.close()

    def book_appointment(self):

        doctor_id = self.booking_doctor.currentData()
        appointment_date = self.booking_date.date().toPyDate()
        appointment_time_str = self.booking_time.currentText()

        if not doctor_id:
            QMessageBox.warning(self, "Ошибка", "Выберите врача")
            return

        try:
            hour, minute = map(int, appointment_time_str.split(':'))
            appointment_time = datetime.strptime(appointment_time_str, "%H:%M").time()
        except:
            QMessageBox.warning(self, "Ошибка", "Неверный формат времени")
            return

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()

            cursor.execute("""
                select id from appointment
                where doctor_id = %s and appointment_date = %s and appointment_time = %s
                and status not in ('Отменён', 'Не явился')
            """, (doctor_id, appointment_date, appointment_time))

            if cursor.fetchone():
                QMessageBox.warning(self, "Ошибка", "Это время уже занято")
                cursor.close()
                connection.close()
                return

            cursor.execute("select insurance_type from patient where id = %s", (self.patient_id,))
            insurance_type = cursor.fetchone()[0]
            base_cost = 1500.00
            cost = base_cost * 0.5 if insurance_type == 'ОМС' else base_cost

            cursor.execute("""
                insert into appointment (patient_id, doctor_id, appointment_date, appointment_time,
                appointment_type, status, cost)
                values (%s, %s, %s, %s, %s, %s, %s)
            """, (self.patient_id, doctor_id, appointment_date, appointment_time,
                  'Первичный', 'Запланирован', cost))

            connection.commit()
            QMessageBox.information(self, "Успех", "Вы записаны на приём")

            self.booking_cost.setText("Стоимость будет рассчитана автоматически")

            cursor.close()
            connection.close()
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка записи: {e}")
            if connection:
                connection.close()

    def create_my_appointments_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        self.my_appointments_table = QTableWidget()
        self.my_appointments_table.setColumnCount(7)
        self.my_appointments_table.setHorizontalHeaderLabels([
            "ID", "Врач", "Дата", "Время", "Тип", "Статус", "Действия"
        ])
        layout.addWidget(self.my_appointments_table)

        btn_cancel = QPushButton("Отменить запись")
        btn_cancel.clicked.connect(self.cancel_my_appointment)
        layout.addWidget(btn_cancel)

        btn_refresh = QPushButton("Обновить")
        btn_refresh.clicked.connect(self.load_my_appointments)
        layout.addWidget(btn_refresh)

        widget.setLayout(layout)
        self.load_my_appointments()
        return widget

    def load_my_appointments(self):

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()
            cursor.execute("""
                select a.id, d.full_name, a.appointment_date, a.appointment_time,
                a.appointment_type, a.status
                from appointment a
                join doctor d on a.doctor_id = d.id
                where a.patient_id = %s
                order by a.appointment_date desc, a.appointment_time desc
            """, (self.patient_id,))
            appointments = cursor.fetchall()

            self.my_appointments_table.setRowCount(len(appointments))
            for row, (app_id, doctor, date, time, app_type, status) in enumerate(appointments):
                self.my_appointments_table.setItem(row, 0, QTableWidgetItem(str(app_id)))
                self.my_appointments_table.setItem(row, 1, QTableWidgetItem(doctor))
                self.my_appointments_table.setItem(row, 2, QTableWidgetItem(str(date)))
                self.my_appointments_table.setItem(row, 3, QTableWidgetItem(str(time)))
                self.my_appointments_table.setItem(row, 4, QTableWidgetItem(app_type))
                self.my_appointments_table.setItem(row, 5, QTableWidgetItem(status))

                from datetime import time as time_class
                if isinstance(time, timedelta):
                    total_seconds = int(time.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    time_obj = time_class(hours, minutes)
                elif isinstance(time, str):
                    time_parts = time.split(':')
                    time_obj = time_class(int(time_parts[0]), int(time_parts[1]))
                else:
                    time_obj = time

                appointment_datetime = datetime.combine(date, time_obj)
                time_diff = appointment_datetime - datetime.now()

                if status == 'Запланирован' and time_diff.total_seconds() >= 86400:
                    btn = QPushButton("Отменить")
                    btn.setProperty("appointment_id", app_id)
                    btn.setProperty("appointment_datetime", appointment_datetime)
                    btn.clicked.connect(self.on_cancel_button_clicked)
                    self.my_appointments_table.setCellWidget(row, 6, btn)
                else:
                    self.my_appointments_table.setItem(row, 6, QTableWidgetItem("Нельзя отменить"))

            self.my_appointments_table.resizeColumnsToContents()
            cursor.close()
            connection.close()
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки записей: {e}")
            if connection:
                connection.close()

    def cancel_my_appointment(self):

        current_row = self.my_appointments_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите запись")
            return

        item = self.my_appointments_table.item(current_row, 0)
        if item:
            app_id = int(item.text())
            self.cancel_appointment_by_id(app_id)

    def on_cancel_button_clicked(self):

        sender = self.sender()
        if sender:
            app_id = sender.property("appointment_id")
            if app_id:
                self.cancel_appointment_by_id(app_id)

    def cancel_appointment_by_id(self, app_id):

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()

            cursor.execute("""
                select appointment_date, appointment_time, status
                from appointment
                where id = %s and patient_id = %s
            """, (app_id, self.patient_id))

            result = cursor.fetchone()
            if not result:
                QMessageBox.warning(self, "Ошибка", "Запись не найдена")
                return

            appointment_date, appointment_time, status = result

            if status != 'Запланирован':
                QMessageBox.warning(self, "Ошибка", "Можно отменить только запланированные записи")
                return

            from datetime import time as time_class
            if isinstance(appointment_time, timedelta):
                total_seconds = int(appointment_time.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                time_obj = time_class(hours, minutes)
            elif isinstance(appointment_time, str):
                time_parts = appointment_time.split(':')
                time_obj = time_class(int(time_parts[0]), int(time_parts[1]))
            else:
                time_obj = appointment_time

            appointment_datetime = datetime.combine(appointment_date, time_obj)
            time_diff = appointment_datetime - datetime.now()

            if time_diff.total_seconds() < 86400:
                QMessageBox.warning(self, "Ошибка",
                                  "Отмена возможна не позднее чем за 24 часа до приёма")
                return

            reply = QMessageBox.question(self, "Подтверждение", "Отменить запись?")
            if reply != QMessageBox.StandardButton.Yes:
                return

            cursor.execute("update appointment set status = 'Отменён' where id = %s", (app_id,))
            connection.commit()
            QMessageBox.information(self, "Успех", "Запись отменена")
            self.load_my_appointments()

            cursor.close()
            connection.close()
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка отмены: {e}")
            if connection:
                connection.close()

    def create_medical_record_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        info_group = QGroupBox("Информация о пациенте")
        info_layout = QVBoxLayout()
        self.patient_info_label = QLabel()
        info_layout.addWidget(self.patient_info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        history_group = QGroupBox("История приёмов")
        history_layout = QVBoxLayout()

        self.medical_record_table = QTableWidget()
        self.medical_record_table.setColumnCount(6)
        self.medical_record_table.setHorizontalHeaderLabels([
            "Дата", "Врач", "Тип", "Диагноз", "Назначения", "Статус"
        ])
        history_layout.addWidget(self.medical_record_table)

        btn_refresh = QPushButton("Обновить")
        btn_refresh.clicked.connect(self.load_medical_record)
        history_layout.addWidget(btn_refresh)

        history_group.setLayout(history_layout)
        layout.addWidget(history_group)

        widget.setLayout(layout)
        self.load_medical_record()
        return widget

    def load_medical_record(self):

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()

            cursor.execute("""
                select medical_record_number, full_name, date_of_birth, gender,
                insurance_type, insurance_company
                from patient where id = %s
            """, (self.patient_id,))

            patient_info = cursor.fetchone()
            if patient_info:
                record_num, name, birthdate, gender, insurance_type, insurance_company = patient_info
                self.patient_info_label.setText(
                    f"Номер медкарты: {record_num} | ФИО: {name} | "
                    f"Дата рождения: {birthdate} | Пол: {gender} | "
                    f"Тип страхования: {insurance_type} | Страховая: {insurance_company or 'Не указана'}"
                )

            cursor.execute("""
                select a.appointment_date, d.full_name, a.appointment_type,
                a.diagnosis, a.prescription, a.status
                from appointment a
                join doctor d on a.doctor_id = d.id
                where a.patient_id = %s
                order by a.appointment_date desc, a.appointment_time desc
            """, (self.patient_id,))

            appointments = cursor.fetchall()

            self.medical_record_table.setRowCount(len(appointments))
            for row, (date, doctor, app_type, diagnosis, prescription, status) in enumerate(appointments):
                self.medical_record_table.setItem(row, 0, QTableWidgetItem(str(date)))
                self.medical_record_table.setItem(row, 1, QTableWidgetItem(doctor))
                self.medical_record_table.setItem(row, 2, QTableWidgetItem(app_type))
                self.medical_record_table.setItem(row, 3, QTableWidgetItem(diagnosis or "Не указан"))
                self.medical_record_table.setItem(row, 4, QTableWidgetItem(prescription or "Не указаны"))
                self.medical_record_table.setItem(row, 5, QTableWidgetItem(status))

            self.medical_record_table.resizeColumnsToContents()
            cursor.close()
            connection.close()
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки медкарты: {e}")
            if connection:
                connection.close()

            self.medical_record_table.resizeColumnsToContents()
            cursor.close()
            connection.close()
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки медкарты: {e}")
            if connection:
                connection.close()
