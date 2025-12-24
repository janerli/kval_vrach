from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QTableWidget, QTableWidgetItem,
                             QPushButton, QDialog, QLabel, QLineEdit, QComboBox,
                             QDateEdit, QTimeEdit, QTextEdit, QMessageBox, QGroupBox, QInputDialog)
from PyQt6.QtCore import QDate, QTime, Qt
from PyQt6.QtGui import QIntValidator
import pymysql
from config import DB_CONFIG
from datetime import datetime, timedelta

class AdminWindow(QMainWindow):

    def __init__(self, user_info):
        super().__init__()
        self.user_info = user_info
        self.setWindowTitle(f"Администратор регистратуры - {user_info['full_name']}")
        self.setGeometry(100, 100, 1200, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        tabs = QTabWidget()

        tabs.addTab(self.create_patient_registration_tab(), "Регистрация пациента")
        tabs.addTab(self.create_appointment_tab(), "Запись на приём")
        tabs.addTab(self.create_appointments_management_tab(), "Управление записями")
        tabs.addTab(self.create_payment_tab(), "Оплата услуг")

        layout.addWidget(tabs)
        central_widget.setLayout(layout)

    def get_connection(self):

        try:
            return pymysql.connect(**DB_CONFIG)
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка подключения к БД: {e}")
            return None

    def create_patient_registration_tab(self):

        widget = QWidget()
        layout = QVBoxLayout()

        form_layout = QVBoxLayout()

        self.patient_name = QLineEdit()
        self.patient_name.setPlaceholderText("ФИО")
        form_layout.addWidget(QLabel("ФИО:"))
        form_layout.addWidget(self.patient_name)

        self.patient_birthdate = QDateEdit()
        self.patient_birthdate.setDate(QDate.currentDate().addYears(-30))
        self.patient_birthdate.setCalendarPopup(True)
        form_layout.addWidget(QLabel("Дата рождения:"))
        form_layout.addWidget(self.patient_birthdate)

        self.patient_gender = QComboBox()
        self.patient_gender.addItems(['М', 'Ж'])
        form_layout.addWidget(QLabel("Пол:"))
        form_layout.addWidget(self.patient_gender)

        self.patient_address = QLineEdit()
        self.patient_address.setPlaceholderText("Адрес")
        form_layout.addWidget(QLabel("Адрес:"))
        form_layout.addWidget(self.patient_address)

        self.patient_phone = QLineEdit()
        self.patient_phone.setPlaceholderText("Телефон")
        form_layout.addWidget(QLabel("Телефон:"))
        form_layout.addWidget(self.patient_phone)

        self.patient_email = QLineEdit()
        self.patient_email.setPlaceholderText("Email")
        form_layout.addWidget(QLabel("Email:"))
        form_layout.addWidget(self.patient_email)

        self.patient_passport_series = QLineEdit()
        self.patient_passport_series.setPlaceholderText("Серия паспорта")
        form_layout.addWidget(QLabel("Серия паспорта:"))
        form_layout.addWidget(self.patient_passport_series)

        self.patient_passport_number = QLineEdit()
        self.patient_passport_number.setPlaceholderText("Номер паспорта")
        form_layout.addWidget(QLabel("Номер паспорта:"))
        form_layout.addWidget(self.patient_passport_number)

        self.patient_insurance_type = QComboBox()
        self.patient_insurance_type.addItems(['ОМС', 'ДМС'])
        form_layout.addWidget(QLabel("Тип страхования:"))
        form_layout.addWidget(self.patient_insurance_type)

        self.patient_policy_number = QLineEdit()
        self.patient_policy_number.setPlaceholderText("Номер полиса")
        form_layout.addWidget(QLabel("Номер полиса:"))
        form_layout.addWidget(self.patient_policy_number)

        self.patient_insurance_company = QComboBox()
        self.patient_insurance_company.setEditable(True)
        self.patient_insurance_company.addItems([
            'Страховая Компания 1',
            'Страховая Компания 2',
            'СОГАЗ',
            'АльфаСтрахование',
            'Росгосстрах',
            'Ингосстрах',
            'РЕСО-Гарантия',
            'ВСК',
            'Другая'
        ])
        form_layout.addWidget(QLabel("Страховая компания:"))
        form_layout.addWidget(self.patient_insurance_company)

        self.patient_password = QLineEdit()
        self.patient_password.setPlaceholderText("Пароль для входа")
        self.patient_password.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addWidget(QLabel("Пароль для входа в систему:"))
        form_layout.addWidget(self.patient_password)

        btn_register = QPushButton("Зарегистрировать пациента")
        btn_register.clicked.connect(self.register_patient)
        form_layout.addWidget(btn_register)

        widget.setLayout(form_layout)
        return widget

    def register_patient(self):

        if not self.patient_name.text():
            QMessageBox.warning(self, "Ошибка", "Введите ФИО пациента")
            return

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()

            cursor.execute("select count(*) from patient")
            count = cursor.fetchone()[0]
            medical_record_number = f"MR-{str(count + 1).zfill(3)}"

            cursor.execute("select id from patient where medical_record_number = %s", (medical_record_number,))
            if cursor.fetchone():
                medical_record_number = f"MR-{str(count + 2).zfill(3)}"

            birthdate = self.patient_birthdate.date().toPyDate()
            insurance_type = self.patient_insurance_type.currentText()
            policy_number = self.patient_policy_number.text() or None
            insurance_company = self.patient_insurance_company.currentText() or None

            oms_policy = policy_number if insurance_type == 'ОМС' else None
            dms_policy = policy_number if insurance_type == 'ДМС' else None

            patient_password = self.patient_password.text()
            if not patient_password:
                QMessageBox.warning(self, "Ошибка", "Введите пароль для входа в систему")
                cursor.close()
                connection.close()
                return

            cursor.execute("""
                insert into patient (medical_record_number, full_name, date_of_birth, gender,
                address, phone, email, passport_series, passport_number, oms_policy, dms_policy,
                insurance_company, insurance_type)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                medical_record_number,
                self.patient_name.text(),
                birthdate,
                self.patient_gender.currentText(),
                self.patient_address.text() or None,
                self.patient_phone.text() or None,
                self.patient_email.text() or None,
                self.patient_passport_series.text() or None,
                self.patient_passport_number.text() or None,
                oms_policy,
                dms_policy,
                insurance_company,
                insurance_type
            ))

            patient_id = cursor.lastrowid

            patient_login = self.patient_email.text() if self.patient_email.text() else f"patient_{medical_record_number}"

            cursor.execute("select id from app_user where login = %s", (patient_login,))
            if cursor.fetchone():
                patient_login = f"{patient_login}_{patient_id}"

            cursor.execute("""
                insert into app_user (login, password, role, full_name)
                values (%s, %s, %s, %s)
            """, (patient_login, patient_password, 'PATIENT', self.patient_name.text()))

            connection.commit()
            QMessageBox.information(self, "Успех",
                                   f"Пациент зарегистрирован. Номер медкарты: {medical_record_number}\n"
                                   f"Логин для входа: {patient_login}")

            self.load_patients()

            self.patient_name.clear()
            self.patient_address.clear()
            self.patient_phone.clear()
            self.patient_email.clear()
            self.patient_passport_series.clear()
            self.patient_passport_number.clear()
            self.patient_policy_number.clear()
            self.patient_insurance_company.setCurrentIndex(0)
            self.patient_insurance_type.setCurrentIndex(0)
            self.patient_password.clear()

            cursor.close()
            connection.close()
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка регистрации: {e}")
            if connection:
                connection.close()

    def create_appointment_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        form_layout = QVBoxLayout()

        patient_layout = QHBoxLayout()
        patient_layout.addWidget(QLabel("Пациент:"))
        self.appointment_patient = QComboBox()
        self.load_patients()
        patient_layout.addWidget(self.appointment_patient)
        btn_refresh_patients = QPushButton("Обновить")
        btn_refresh_patients.clicked.connect(self.load_patients)
        patient_layout.addWidget(btn_refresh_patients)
        form_layout.addLayout(patient_layout)

        self.appointment_specialization = QComboBox()
        self.load_specializations()
        self.appointment_specialization.currentIndexChanged.connect(self.load_doctors_by_specialization)
        form_layout.addWidget(QLabel("Специализация:"))
        form_layout.addWidget(self.appointment_specialization)

        self.appointment_doctor = QComboBox()
        form_layout.addWidget(QLabel("Врач:"))
        form_layout.addWidget(self.appointment_doctor)

        if self.appointment_specialization.count() > 0:

            self.appointment_specialization.setCurrentIndex(0)

        self.appointment_date = QDateEdit()
        self.appointment_date.setDate(QDate.currentDate())
        self.appointment_date.setMinimumDate(QDate.currentDate())
        self.appointment_date.setCalendarPopup(True)
        form_layout.addWidget(QLabel("Дата приёма:"))
        form_layout.addWidget(self.appointment_date)

        self.appointment_time = QTimeEdit()
        self.appointment_time.setTime(QTime(9, 0))
        form_layout.addWidget(QLabel("Время приёма:"))
        form_layout.addWidget(self.appointment_time)

        self.appointment_type = QComboBox()
        self.appointment_type.addItems(['Первичный', 'Повторный', 'Профилактический'])
        form_layout.addWidget(QLabel("Тип приёма:"))
        form_layout.addWidget(self.appointment_type)

        self.appointment_cost = QLineEdit()
        self.appointment_cost.setPlaceholderText("Стоимость (автоматически)")
        self.appointment_cost.setReadOnly(True)
        form_layout.addWidget(QLabel("Стоимость:"))
        form_layout.addWidget(self.appointment_cost)

        btn_calculate = QPushButton("Рассчитать стоимость")
        btn_calculate.clicked.connect(self.calculate_appointment_cost)
        form_layout.addWidget(btn_calculate)

        btn_create = QPushButton("Создать запись")
        btn_create.clicked.connect(self.create_appointment)
        form_layout.addWidget(btn_create)

        widget.setLayout(form_layout)
        return widget

    def load_patients(self):

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()
            cursor.execute("select id, medical_record_number, full_name from patient order by full_name")
            patients = cursor.fetchall()

            self.appointment_patient.clear()
            for patient_id, record_num, name in patients:
                self.appointment_patient.addItem(f"{record_num} - {name}", patient_id)

            cursor.close()
            connection.close()
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки пациентов: {e}")
            if connection:
                connection.close()

    def load_specializations(self):

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()
            cursor.execute("select id, name from specialization order by name")
            specializations = cursor.fetchall()

            self.appointment_specialization.clear()
            for spec_id, name in specializations:
                self.appointment_specialization.addItem(name, spec_id)

            cursor.close()
            connection.close()
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки специализаций: {e}")
            if connection:
                connection.close()

    def load_doctors_by_specialization(self, index=None):

        connection = self.get_connection()
        if not connection:
            return

        try:
            if index is not None and index >= 0:
                spec_id = self.appointment_specialization.itemData(index)
            else:
                spec_id = self.appointment_specialization.currentData()

            if not spec_id:
                self.appointment_doctor.clear()
                return

            cursor = connection.cursor()
            cursor.execute("""
                select id, full_name from doctor
                where specialization_id = %s
                order by full_name
            """, (spec_id,))
            doctors = cursor.fetchall()

            self.appointment_doctor.clear()
            for doctor_id, name in doctors:
                self.appointment_doctor.addItem(name, doctor_id)

            cursor.close()
            connection.close()
        except Exception as e:
            print(f"Ошибка загрузки врачей: {e}")
            if connection:
                try:
                    connection.close()
                except:
                    pass

    def calculate_appointment_cost(self):

        patient_id = self.appointment_patient.currentData()
        appointment_type = self.appointment_type.currentText()

        if not patient_id:
            QMessageBox.warning(self, "Ошибка", "Выберите пациента")
            return

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()
            cursor.execute("select insurance_type from patient where id = %s", (patient_id,))
            result = cursor.fetchone()

            if not result:
                QMessageBox.warning(self, "Ошибка", "Пациент не найден")
                return

            insurance_type = result[0]

            base_costs = {
                'Первичный': 1500.00,
                'Повторный': 2000.00,
                'Профилактический': 1000.00
            }
            base_cost = base_costs.get(appointment_type, 1500.00)

            if insurance_type == 'ОМС':
                cost = base_cost * 0.5
            else:
                cost = base_cost

            self.appointment_cost.setText(str(cost))

            cursor.close()
            connection.close()
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка расчёта стоимости: {e}")
            if connection:
                connection.close()

    def create_appointment(self):

        patient_id = self.appointment_patient.currentData()
        doctor_id = self.appointment_doctor.currentData()
        appointment_date = self.appointment_date.date().toPyDate()
        appointment_time = self.appointment_time.time().toPyTime()
        appointment_type = self.appointment_type.currentText()
        cost = self.appointment_cost.text()

        if not patient_id or not doctor_id:
            QMessageBox.warning(self, "Ошибка", "Выберите пациента и врача")
            return

        if not cost:
            QMessageBox.warning(self, "Ошибка", "Рассчитайте стоимость приёма")
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

            cursor.execute("""
                insert into appointment (patient_id, doctor_id, appointment_date, appointment_time,
                appointment_type, status, cost)
                values (%s, %s, %s, %s, %s, %s, %s)
            """, (patient_id, doctor_id, appointment_date, appointment_time,
                  appointment_type, 'Запланирован', float(cost)))

            connection.commit()
            QMessageBox.information(self, "Успех", "Запись на приём создана")

            self.appointment_cost.clear()

            cursor.close()
            connection.close()
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка создания записи: {e}")
            if connection:
                connection.close()

    def create_appointments_management_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        filter_group = QGroupBox("Фильтры")
        filter_layout = QHBoxLayout()

        self.filter_date_from = QDateEdit()
        self.filter_date_from.setDate(QDate.currentDate().addDays(-30))
        self.filter_date_from.setCalendarPopup(True)
        filter_layout.addWidget(QLabel("Дата с:"))
        filter_layout.addWidget(self.filter_date_from)

        self.filter_date_to = QDateEdit()
        self.filter_date_to.setDate(QDate.currentDate().addDays(30))
        self.filter_date_to.setCalendarPopup(True)
        filter_layout.addWidget(QLabel("Дата по:"))
        filter_layout.addWidget(self.filter_date_to)

        self.filter_doctor = QComboBox()
        self.filter_doctor.addItem("Все врачи", None)
        self.load_all_doctors()
        filter_layout.addWidget(QLabel("Врач:"))
        filter_layout.addWidget(self.filter_doctor)

        self.filter_status = QComboBox()
        self.filter_status.addItems(["Все статусы", "Запланирован", "Пациент на приёме",
                                    "Завершён", "Не явился", "Отменён"])
        filter_layout.addWidget(QLabel("Статус:"))
        filter_layout.addWidget(self.filter_status)

        btn_filter = QPushButton("Применить фильтр")
        btn_filter.clicked.connect(self.filter_appointments)
        filter_layout.addWidget(btn_filter)

        btn_show_all = QPushButton("Показать все")
        btn_show_all.clicked.connect(self.load_all_appointments)
        filter_layout.addWidget(btn_show_all)

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        self.appointments_table = QTableWidget()
        self.appointments_table.setColumnCount(9)
        self.appointments_table.setHorizontalHeaderLabels([
            "ID", "Пациент", "Врач", "Дата", "Время", "Тип", "Статус", "Стоимость", "Действия"
        ])
        layout.addWidget(self.appointments_table)

        btn_layout = QHBoxLayout()
        btn_update_status = QPushButton("Изменить статус")
        btn_update_status.clicked.connect(self.update_appointment_status)
        btn_layout.addWidget(btn_update_status)

        btn_cancel = QPushButton("Отменить запись")
        btn_cancel.clicked.connect(self.cancel_appointment)
        btn_layout.addWidget(btn_cancel)

        btn_reschedule = QPushButton("Перенести запись")
        btn_reschedule.clicked.connect(self.reschedule_appointment)
        btn_layout.addWidget(btn_reschedule)

        layout.addLayout(btn_layout)

        widget.setLayout(layout)
        self.load_all_appointments()
        return widget

    def load_all_doctors(self):

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()
            cursor.execute("select id, full_name from doctor order by full_name")
            doctors = cursor.fetchall()

            for doctor_id, name in doctors:
                self.filter_doctor.addItem(name, doctor_id)

            cursor.close()
            connection.close()
        except pymysql.Error as e:
            if connection:
                connection.close()

    def load_all_appointments(self):

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()
            cursor.execute("""
                select a.id, p.full_name, d.full_name, a.appointment_date, a.appointment_time,
                a.appointment_type, a.status, a.cost
                from appointment a
                join patient p on a.patient_id = p.id
                join doctor d on a.doctor_id = d.id
                order by a.appointment_date desc, a.appointment_time desc
            """)
            appointments = cursor.fetchall()

            self.appointments_table.setRowCount(len(appointments))
            for row, (app_id, patient, doctor, date, time, app_type, status, cost) in enumerate(appointments):
                self.appointments_table.setItem(row, 0, QTableWidgetItem(str(app_id)))
                self.appointments_table.setItem(row, 1, QTableWidgetItem(patient))
                self.appointments_table.setItem(row, 2, QTableWidgetItem(doctor))
                self.appointments_table.setItem(row, 3, QTableWidgetItem(str(date)))
                self.appointments_table.setItem(row, 4, QTableWidgetItem(str(time)))
                self.appointments_table.setItem(row, 5, QTableWidgetItem(app_type))
                self.appointments_table.setItem(row, 6, QTableWidgetItem(status))
                self.appointments_table.setItem(row, 7, QTableWidgetItem(str(cost)))

                btn = QPushButton("Выбрать")
                btn.setProperty("appointment_id", app_id)
                self.appointments_table.setCellWidget(row, 8, btn)

            self.appointments_table.resizeColumnsToContents()
            cursor.close()
            connection.close()
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки записей: {e}")
            if connection:
                connection.close()

    def filter_appointments(self):

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()

            date_from = self.filter_date_from.date().toPyDate()
            date_to = self.filter_date_to.date().toPyDate()
            doctor_id = self.filter_doctor.currentData()
            status = self.filter_status.currentText()

            query = """
                select a.id, p.full_name, d.full_name, a.appointment_date, a.appointment_time,
                a.appointment_type, a.status, a.cost
                from appointment a
                join patient p on a.patient_id = p.id
                join doctor d on a.doctor_id = d.id
                where a.appointment_date between %s and %s
            """
            params = [date_from, date_to]

            if doctor_id:
                query += " and a.doctor_id = %s"
                params.append(doctor_id)

            if status != "Все статусы":
                query += " and a.status = %s"
                params.append(status)

            query += " order by a.appointment_date desc, a.appointment_time desc"

            cursor.execute(query, params)
            appointments = cursor.fetchall()

            self.appointments_table.setRowCount(len(appointments))
            for row, (app_id, patient, doctor, date, time, app_type, status_val, cost) in enumerate(appointments):
                self.appointments_table.setItem(row, 0, QTableWidgetItem(str(app_id)))
                self.appointments_table.setItem(row, 1, QTableWidgetItem(patient))
                self.appointments_table.setItem(row, 2, QTableWidgetItem(doctor))
                self.appointments_table.setItem(row, 3, QTableWidgetItem(str(date)))
                self.appointments_table.setItem(row, 4, QTableWidgetItem(str(time)))
                self.appointments_table.setItem(row, 5, QTableWidgetItem(app_type))
                self.appointments_table.setItem(row, 6, QTableWidgetItem(status_val))
                self.appointments_table.setItem(row, 7, QTableWidgetItem(str(cost)))

                btn = QPushButton("Выбрать")
                btn.setProperty("appointment_id", app_id)
                self.appointments_table.setCellWidget(row, 8, btn)

            self.appointments_table.resizeColumnsToContents()
            cursor.close()
            connection.close()
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка фильтрации: {e}")
            if connection:
                connection.close()

    def get_selected_appointment_id(self):
        try:
            current_row = self.appointments_table.currentRow()
            if current_row < 0:
                return None

            item = self.appointments_table.item(current_row, 0)
            if item:
                try:
                    return int(item.text())
                except (ValueError, TypeError):
                    return None
            return None
        except Exception:
            return None

    def update_appointment_status(self):

        app_id = self.get_selected_appointment_id()
        if not app_id:
            QMessageBox.warning(self, "Ошибка", "Выберите запись")
            return

        statuses = ["Запланирован", "Пациент на приёме", "Завершён", "Не явился", "Отменён"]

        try:
            status, ok = QInputDialog.getItem(self, "Изменение статуса", "Выберите новый статус:", statuses, 0, False)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка выбора статуса: {e}")
            return

        if not ok or not status:
            return

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()
            cursor.execute("update appointment set status = %s where id = %s", (status, app_id))
            connection.commit()
            QMessageBox.information(self, "Успех", "Статус обновлён")

            try:
                self.load_all_appointments()
            except Exception as e:
                print(f"Ошибка обновления таблицы: {e}")

            cursor.close()
            connection.close()
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка обновления: {e}")
            if connection:
                try:
                    connection.close()
                except:
                    pass
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Неожиданная ошибка: {e}")
            if connection:
                try:
                    connection.close()
                except:
                    pass

    def cancel_appointment(self):

        app_id = self.get_selected_appointment_id()
        if not app_id:
            QMessageBox.warning(self, "Ошибка", "Выберите запись")
            return

        reply = QMessageBox.question(self, "Подтверждение", "Отменить запись?")
        if reply != QMessageBox.StandardButton.Yes:
            return

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()
            cursor.execute("update appointment set status = 'Отменён' where id = %s", (app_id,))
            connection.commit()
            QMessageBox.information(self, "Успех", "Запись отменена")
            self.load_all_appointments()
            cursor.close()
            connection.close()
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка отмены: {e}")
            if connection:
                connection.close()

    def reschedule_appointment(self):

        app_id = self.get_selected_appointment_id()
        if not app_id:
            QMessageBox.warning(self, "Ошибка", "Выберите запись")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Перенос записи")
        dialog.setFixedSize(300, 150)
        layout = QVBoxLayout()

        new_date = QDateEdit()
        new_date.setDate(QDate.currentDate())
        new_date.setMinimumDate(QDate.currentDate())
        new_date.setCalendarPopup(True)
        layout.addWidget(QLabel("Новая дата:"))
        layout.addWidget(new_date)

        new_time = QTimeEdit()
        new_time.setTime(QTime(9, 0))
        layout.addWidget(QLabel("Новое время:"))
        layout.addWidget(new_time)

        btn_ok = QPushButton("Применить")
        btn_cancel = QPushButton("Отмена")

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        dialog.setLayout(layout)

        def apply_reschedule():
            connection = self.get_connection()
            if not connection:
                return

            try:
                cursor = connection.cursor()

                cursor.execute("""
                    select id from appointment
                    where doctor_id = (select doctor_id from appointment where id = %s)
                    and appointment_date = %s and appointment_time = %s
                    and id != %s and status not in ('Отменён', 'Не явился')
                """, (app_id, new_date.date().toPyDate(), new_time.time().toPyTime(), app_id))

                if cursor.fetchone():
                    QMessageBox.warning(dialog, "Ошибка", "Это время уже занято")
                    return

                cursor.execute("""
                    update appointment
                    set appointment_date = %s, appointment_time = %s
                    where id = %s
                """, (new_date.date().toPyDate(), new_time.time().toPyTime(), app_id))

                connection.commit()
                QMessageBox.information(dialog, "Успех", "Запись перенесена")
                dialog.accept()
                self.load_all_appointments()
                cursor.close()
                connection.close()
            except pymysql.Error as e:
                QMessageBox.critical(dialog, "Ошибка", f"Ошибка переноса: {e}")
                if connection:
                    connection.close()

        btn_ok.clicked.conn7ect(apply_reschedule)
        btn_cancel.clicked.connect(dialog.reject)

        dialog.exec()

    def create_payment_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        form_layout = QVBoxLayout()

        self.payment_appointment = QComboBox()
        self.load_appointments_for_payment()
        form_layout.addWidget(QLabel("Запись на приём:"))
        form_layout.addWidget(self.payment_appointment)

        self.payment_method = QComboBox()
        self.payment_method.addItems(['Наличные', 'Карта', 'По полису'])
        form_layout.addWidget(QLabel("Способ оплаты:"))
        form_layout.addWidget(self.payment_method)

        btn_pay = QPushButton("Оформить оплату")
        btn_pay.clicked.connect(self.process_payment)
        form_layout.addWidget(btn_pay)

        widget.setLayout(form_layout)
        return widget

    def load_appointments_for_payment(self):

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()
            cursor.execute("""
                select a.id, p.full_name, d.full_name, a.appointment_date, a.cost, a.payment_method
                from appointment a
                join patient p on a.patient_id = p.id
                join doctor d on a.doctor_id = d.id
                where a.status in ('Завершён', 'Запланирован', 'Пациент на приёме')
                order by a.appointment_date desc
            """)
            appointments = cursor.fetchall()

            self.payment_appointment.clear()
            for app_id, patient, doctor, date, cost, payment_method in appointments:
                payment_status = f" (Оплачено: {payment_method})" if payment_method else ""
                self.payment_appointment.addItem(
                    f"{date} - {patient} - {doctor} - {cost} руб.{payment_status}",
                    app_id
                )

            cursor.close()
            connection.close()
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки записей: {e}")
            if connection:
                connection.close()

    def process_payment(self):

        app_id = self.payment_appointment.currentData()
        payment_method = self.payment_method.currentText()

        if not app_id:
            QMessageBox.warning(self, "Ошибка", "Выберите запись")
            return

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()
            cursor.execute("""
                update appointment
                set payment_method = %s
                where id = %s
            """, (payment_method, app_id))

            connection.commit()
            QMessageBox.information(self, "Успех", "Оплата оформлена")
            self.load_appointments_for_payment()
            cursor.close()
            connection.close()
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка оплаты: {e}")
            if connection:
                connection.close()
