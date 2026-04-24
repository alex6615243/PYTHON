from PyQt6.QtWidgets import QMainWindow, QLabel, QLineEdit, QPushButton, QApplication
from PYQT6.login import Ui_MainWindow
import sys

class MainWindow(QMainWindow,Ui_MainWindow):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        #代碼開始
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.pushButton.clicked.connect(self.login)

        #代碼結束
        self.show()
    def login(self):
        username = self.username_edit.text() 
        password = self.password_edit.text()
        if username =='andy' and password == '123':
            print('登錄成功')
        else:
            print('登錄失敗')

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())