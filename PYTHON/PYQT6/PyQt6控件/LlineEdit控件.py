from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit
import sys

class MainWindow(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #代碼開始
        self.setWindowTitle('文本框控件')
        self.resize(400,300)
        #設置布局
        layout = QVBoxLayout()
        line1 = QLineEdit()
        line2 = QLineEdit()
        line2.setEchoMode(QLineEdit.EchoMode.Password)
        line3 = QLineEdit()
        line3.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        line4 = QLineEdit()
        line4.setEchoMode(QLineEdit.EchoMode.NoEcho)

        layout.addWidget(line1)
        layout.addWidget(line2)
        layout.addWidget(line3)
        layout.addWidget(line4)
        self.setLayout(layout)

        #代碼結束
        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())