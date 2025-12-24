import sys
from PyQt6.QtWidgets import QApplication
from db import init_database
from auth import authenticate
from admin_ui import AdminWindow
from chief_ui import ChiefWindow
from patient_ui import PatientWindow
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox


class LoginDialog(QDialog):
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Авторизация")
        self.setFixedSize(300, 150)
        self.user_info = None
        
        layout = QVBoxLayout()
        
        self.login_edit = QLineEdit()
        self.login_edit.setPlaceholderText("Логин")
        layout.addWidget(self.login_edit)
        
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Пароль")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_edit)
        
        login_btn = QPushButton("Войти")
        login_btn.clicked.connect(self.login)
        layout.addWidget(login_btn)
        
        self.setLayout(layout)
    
    def login(self):
        login = self.login_edit.text()
        password = self.password_edit.text()
        
        if not login or not password:
            QMessageBox.warning(self, "Ошибка", "Введите логин и пароль")
            return
        
        user_info = authenticate(login, password)
        if user_info:
            self.user_info = user_info
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", "Неверный логин или пароль")


def main():
    app = QApplication(sys.argv)
    
    if not init_database():
        QMessageBox.critical(None, "Ошибка", "Не удалось инициализировать базу данных")
        sys.exit(1)
    
    login_dialog = LoginDialog()
    if login_dialog.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)
    
    user_info = login_dialog.user_info
    if not user_info:
        sys.exit(0)
    
    if user_info['role'] == 'ADMIN':
        window = AdminWindow(user_info)
    elif user_info['role'] == 'CHIEF':
        window = ChiefWindow(user_info)
    elif user_info['role'] == 'PATIENT':
        window = PatientWindow(user_info)
    else:
        QMessageBox.critical(None, "Ошибка", "Неизвестная роль пользователя")
        sys.exit(1)
    
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
