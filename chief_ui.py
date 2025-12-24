from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QTableWidget, QTableWidgetItem,
                             QPushButton, QLabel, QDateEdit, QLineEdit, QGroupBox, QMessageBox)
from PyQt6.QtCore import QDate
import pymysql
from config import DB_CONFIG

class ChiefWindow(QMainWindow):

    def __init__(self, user_info):
        super().__init__()
        self.user_info = user_info
        self.setWindowTitle(f"Главный врач - {user_info['full_name']}")
        self.setGeometry(100, 100, 1200, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        tabs = QTabWidget()

        tabs.addTab(self.create_statistics_tab(), "Статистика")
        tabs.addTab(self.create_attendance_tab(), "Процент явки")
        tabs.addTab(self.create_average_check_tab(), "Средний чек")

        layout.addWidget(tabs)
        central_widget.setLayout(layout)

    def get_connection(self):

        try:
            return pymysql.connect(**DB_CONFIG)
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка подключения к БД: {e}")
            return None

    def create_statistics_tab(self):

        widget = QWidget()
        layout = QVBoxLayout()

        stats_group = QGroupBox("Общая статистика")
        stats_layout = QVBoxLayout()

        self.stats_patients_label = QLabel("Количество пациентов: 0")
        stats_layout.addWidget(self.stats_patients_label)

        self.stats_appointments_label = QLabel("Количество приёмов: 0")
        stats_layout.addWidget(self.stats_appointments_label)

        self.stats_completed_label = QLabel("Завершённых приёмов: 0")
        stats_layout.addWidget(self.stats_completed_label)

        btn_refresh = QPushButton("Обновить статистику")
        btn_refresh.clicked.connect(self.load_statistics)
        stats_layout.addWidget(btn_refresh)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        doctors_group = QGroupBox("Загруженность врачей")
        doctors_layout = QVBoxLayout()

        self.doctors_table = QTableWidget()
        self.doctors_table.setColumnCount(4)
        self.doctors_table.setHorizontalHeaderLabels(["Врач", "Специализация", "Всего приёмов", "Завершено"])
        doctors_layout.addWidget(self.doctors_table)

        btn_refresh_doctors = QPushButton("Обновить загруженность")
        btn_refresh_doctors.clicked.connect(self.load_doctors_workload)
        doctors_layout.addWidget(btn_refresh_doctors)

        doctors_group.setLayout(doctors_layout)
        layout.addWidget(doctors_group)

        widget.setLayout(layout)
        self.load_statistics()
        self.load_doctors_workload()
        return widget

    def load_statistics(self):

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()

            cursor.execute("select count(*) from patient")
            patients_count = cursor.fetchone()[0]

            cursor.execute("select count(*) from appointment")
            appointments_count = cursor.fetchone()[0]

            cursor.execute("select count(*) from appointment where status = 'Завершён'")
            completed_count = cursor.fetchone()[0]

            self.stats_patients_label.setText(f"Количество пациентов: {patients_count}")
            self.stats_appointments_label.setText(f"Количество приёмов: {appointments_count}")
            self.stats_completed_label.setText(f"Завершённых приёмов: {completed_count}")

            cursor.close()
            connection.close()
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки статистики: {e}")
            if connection:
                connection.close()

    def load_doctors_workload(self):

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()
            cursor.execute("""
                select d.full_name, s.name,
                       count(a.id) as total_appointments,
                       sum(case when a.status = 'Завершён' then 1 else 0 end) as completed
                from doctor d
                left join specialization s on d.specialization_id = s.id
                left join appointment a on d.id = a.doctor_id
                group by d.id, d.full_name, s.name
                order by total_appointments desc
            """)
            doctors = cursor.fetchall()

            self.doctors_table.setRowCount(len(doctors))
            for row, (doctor_name, specialization, total, completed) in enumerate(doctors):
                self.doctors_table.setItem(row, 0, QTableWidgetItem(doctor_name))
                self.doctors_table.setItem(row, 1, QTableWidgetItem(specialization or ""))
                self.doctors_table.setItem(row, 2, QTableWidgetItem(str(total)))
                self.doctors_table.setItem(row, 3, QTableWidgetItem(str(completed)))

            self.doctors_table.resizeColumnsToContents()
            cursor.close()
            connection.close()
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки загруженности: {e}")
            if connection:
                connection.close()

    def create_attendance_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        form_group = QGroupBox("Расчёт процента явки пациентов")
        form_layout = QVBoxLayout()

        self.attendance_date_from = QDateEdit()
        self.attendance_date_from.setDate(QDate.currentDate().addDays(-30))
        self.attendance_date_from.setCalendarPopup(True)
        form_layout.addWidget(QLabel("Дата с:"))
        form_layout.addWidget(self.attendance_date_from)

        self.attendance_date_to = QDateEdit()
        self.attendance_date_to.setDate(QDate.currentDate())
        self.attendance_date_to.setCalendarPopup(True)
        form_layout.addWidget(QLabel("Дата по:"))
        form_layout.addWidget(self.attendance_date_to)

        btn_calculate = QPushButton("Рассчитать процент явки")
        btn_calculate.clicked.connect(self.calculate_attendance)
        form_layout.addWidget(btn_calculate)

        self.attendance_result = QLabel("Результат: не рассчитан")
        self.attendance_result.setStyleSheet("font-size: 16px; font-weight: bold;")
        form_layout.addWidget(self.attendance_result)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        widget.setLayout(layout)
        return widget

    def calculate_attendance(self):

        date_from = self.attendance_date_from.date().toPyDate()
        date_to = self.attendance_date_to.date().toPyDate()

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()

            cursor.execute("""
                select count(*)
                from appointment
                where appointment_date between %s and %s
                and status != 'Отменён'
            """, (date_from, date_to))

            total_scheduled = cursor.fetchone()[0]

            cursor.execute("""
                select count(*)
                from appointment
                where appointment_date between %s and %s
                and status = 'Завершён'
            """, (date_from, date_to))

            completed = cursor.fetchone()[0]

            if total_scheduled > 0:
                attendance_percent = (completed / total_scheduled) * 100
                self.attendance_result.setText(
                    f"Процент явки: {attendance_percent:.2f}% ({completed} из {total_scheduled})"
                )
            else:
                self.attendance_result.setText("Нет записей за выбранный период")

            cursor.close()
            connection.close()
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка расчёта: {e}")
            if connection:
                connection.close()

    def create_average_check_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        form_group = QGroupBox("Расчёт среднего чека")
        form_layout = QVBoxLayout()

        self.avg_check_date_from = QDateEdit()
        self.avg_check_date_from.setDate(QDate.currentDate().addDays(-30))
        self.avg_check_date_from.setCalendarPopup(True)
        form_layout.addWidget(QLabel("Дата с:"))
        form_layout.addWidget(self.avg_check_date_from)

        self.avg_check_date_to = QDateEdit()
        self.avg_check_date_to.setDate(QDate.currentDate())
        self.avg_check_date_to.setCalendarPopup(True)
        form_layout.addWidget(QLabel("Дата по:"))
        form_layout.addWidget(self.avg_check_date_to)

        btn_calculate = QPushButton("Рассчитать средний чек")
        btn_calculate.clicked.connect(self.calculate_average_check)
        form_layout.addWidget(btn_calculate)

        self.avg_check_result = QLabel("Результат: не рассчитан")
        self.avg_check_result.setStyleSheet("font-size: 16px; font-weight: bold;")
        form_layout.addWidget(self.avg_check_result)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        widget.setLayout(layout)
        return widget

    def calculate_average_check(self):

        date_from = self.avg_check_date_from.date().toPyDate()
        date_to = self.avg_check_date_to.date().toPyDate()

        connection = self.get_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()

            cursor.execute("""
                select avg(cost), count(*), sum(cost)
                from appointment
                where appointment_date between %s and %s
                and status = 'Завершён'
            """, (date_from, date_to))

            result = cursor.fetchone()
            avg_cost = result[0]
            count = result[1]
            total_cost = result[2]

            if avg_cost:
                self.avg_check_result.setText(
                    f"Средний чек: {avg_cost:.2f} руб. (Всего приёмов: {count}, Общая сумма: {total_cost:.2f} руб.)"
                )
            else:
                self.avg_check_result.setText("Нет завершённых приёмов за выбранный период")

            cursor.close()
            connection.close()
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка расчёта: {e}")
            if connection:
                connection.close()
