from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt6 import QtCore
import sys

class MainWindow(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #代碼開始
        self.setWindowTitle("手寫登錄頁面")
        self.setFixedSize(400,300)

        #設置佈局
        layout = QVBoxLayout()
        username = QHBoxLayout()
        password = QHBoxLayout()
        button = QHBoxLayout()

        #添加使用者部件
        username_label = QLabel('使用者名稱:')
        username_edit = QLineEdit()
        username.addWidget(username_label,stretch=1)
        username.addWidget(username_edit,stretch=4)

        #添加密碼部件
        password_label = QLabel('密碼:')
        password_edit = QLineEdit()
        password.addWidget(password_label,stretch=1)
        password.addWidget(password_edit,stretch=4)

        #添加按鈕部件
        login_button = QPushButton('登錄')
        button.addWidget(login_button)
        login_button.setFixedWidth(100)
        collect_button = QPushButton('收藏')
        collect_button.setFixedWidth(100)
        collect_button.setCheckable(True)
        collect_button.clicked.connect(lambda:collect_button.setText('收藏成功') if collect_button.isChecked()else collect_button.setText('收藏'))
        button.addWidget(collect_button,alignment=QtCore.Qt.AlignmentFlag.AlignRight)

        

        #將部件添加到佈局中
        layout.addLayout(username)
        layout.addLayout(password)
        layout.addLayout(button)
        self.setLayout(layout)
        self.setContentsMargins(50,20,50,20)
        #代碼結束
        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())