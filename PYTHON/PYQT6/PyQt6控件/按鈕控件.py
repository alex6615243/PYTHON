from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
import sys

class MainWindow(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #代碼開始
        self.setWindowTitle("按鈕控件")
        self.resize(400,300)
        #設置布局
        layout = QVBoxLayout()

        self.btn1 = QPushButton("按鈕1")
        self.btn1.setCheckable(True)
        self.btn1.toggled.connect(self.btn1_clicked)
        self.btn2 = QPushButton("按鈕2")
        self.btn2.setEnabled(False)
        layout.addWidget(self.btn1)
        layout.addWidget(self.btn2)
        self.setLayout(layout)

        #代碼結束
        self.show()
    def btn1_clicked(self):
        if self.btn1.isChecked():
            self.btn1.setStyleSheet("background-color:red")
        else:
            self.btn1.setStyleSheet("background-color:lightblue")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())