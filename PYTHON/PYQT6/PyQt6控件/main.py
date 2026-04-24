from PyQt6.QtWidgets import (QApplication, QWidget,QVBoxLayout,QHBoxLayout,QLabel,
                            QLineEdit,QPushButton,QListWidget,QFileDialog,QMessageBox)
import sys

class MainWindow(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #代碼開始
        self.setWindowTitle('影片合成軟件')
        self.resize(700,500)
        layout = QVBoxLayout()
        
        line_describe1 = QLabel('請添加需要合併的視頻文件')
        layout.addWidget(line_describe1)
        #第一部分布局
        sec1_layout = QHBoxLayout()
        self.list_widget = QListWidget()
        sec1_1_layout = QVBoxLayout()
        self.btn1 = QPushButton('打開')
        self.btn1.clicked.connect(self.open_file)
        self.btn2 = QPushButton('刪除')
        self.btn2.clicked.connect(self.delete_file)
        sec1_1_layout.addWidget(self.btn1,stretch=1)
        sec1_1_layout.addWidget(self.btn2,stretch=1)
        sec1_1_layout.addStretch(1)

        sec1_layout.addWidget(self.list_widget)
        sec1_layout.addLayout(sec1_1_layout)
        layout.addLayout(sec1_layout)
        #第二部分布局
        sec2_layout = QHBoxLayout()
        self.lineedit = QLineEdit()
        self.btn3 = QPushButton('選擇')
        sec2_layout.addWidget(self.lineedit)
        sec2_layout.addWidget(self.btn3)
        layout.addLayout(sec2_layout)
        #第三部分布局
        line_describe2 = QLabel('請選擇合成文件保存位置')
        layout.addWidget(line_describe2)
        self.btn4 = QPushButton('開始合成視頻')
        layout.addWidget(self.btn4)
        self.setLayout(layout)

        
        #代碼結束
        self.show()

    def open_file(self):
        file_path,_ = QFileDialog.getOpenFileName(self,'打開文件','./','MP4 Files(*.mp4)')
        if not file_path:
            return False
        else:
            self.list_widget.addItem(file_path)

    def delete_file(self):
        selected_items = self.list_widget.selectedItems()
        
        if not selected_items:
            QMessageBox.critical(self,'注意','請選擇需要刪除的文件')
            return False
        else:
            for item in selected_items:
                index = self.list_widget.indexFromItem(item).row()
                self.list_widget.takeItem(index)
            

class QSSloader:
    def load_qss(self):
        with open('./PYQT6/style.qss','r') as f:
            style = f.read()
        return style

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    qss = QSSloader().load_qss()
    app.setStyleSheet(qss)
    sys.exit(app.exec())