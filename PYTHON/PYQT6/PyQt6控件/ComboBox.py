from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QComboBox
import sys

class MainWindow(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #代碼開始
        self.setWindowTitle("下拉框控件")
        self.setFixedSize(400,300)
        layout = QVBoxLayout()
        combo = QComboBox()
        combo.addItem('中日')
        combo.addItem('中韓')
        combo.addItem('中英')
        combo.addItem('中法')
        layout.addWidget(combo)
        self.setLayout(layout)
        #代碼結束
        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())