from PyQt6.QtWidgets import (QApplication, QWidget,QVBoxLayout,QHBoxLayout
                             ,QLabel,QLayout,QLineEdit,QPushButton,
                             QCalendarWidget,QTreeWidget,QTreeWidgetItem
                             ,QMessageBox,QFileDialog)
from PyQt6 import QtCore
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import sys

class MainWindow(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 代碼開始
        self.setWindowTitle('進度規劃')
        self.resize(700,600)

        # 第一部分布局
        layout = QVBoxLayout()
        sec1_layout = QHBoxLayout()
        item_label = QLabel('請輸入工作項目:')
        self.input_line = QLineEdit()
        
        sec1_layout.addWidget(item_label)
        sec1_layout.addWidget(self.input_line)
        layout.addLayout(sec1_layout)

        # 第二部分布局
        start_layout = QVBoxLayout()
        over_layout = QVBoxLayout()
        sec2_layout = QHBoxLayout()
        selected_tree_layout = QVBoxLayout()

        start_label = QLabel('請選擇開始時間:')
        over_label = QLabel('請選擇完成時間:')
        self.start_calender = QCalendarWidget()
        self.over_calender = QCalendarWidget()

        self.selected_tree = QTreeWidget() 
        self.selected_tree.setColumnCount(4)
        self.selected_tree.setHeaderLabels(['編號','工作項目','開始時間','完成時間'])
        self.selected_tree.setColumnWidth(0,50)
        self.selected_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.selected_tree.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)

        # 創建第二個 QTreeWidget
        self.selected_tree_2 = QTreeWidget()
        self.selected_tree_2.setColumnCount(4)
        self.selected_tree_2.setHeaderLabels(['編號','工作項目','開始時間','完成時間'])
        self.selected_tree_2.setColumnWidth(0,50)
        self.selected_tree_2.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.selected_tree_2.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)

        start_layout.addWidget(start_label)
        start_layout.addWidget(self.start_calender)
        over_layout.addWidget(over_label)
        over_layout.addWidget(self.over_calender)
        sec2_layout.addLayout(start_layout)
        sec2_layout.addLayout(over_layout)

        selected_tree_layout.addLayout(sec2_layout)
        selected_tree_layout.addWidget(self.selected_tree)
        selected_tree_layout.addWidget(self.selected_tree_2)  # 添加第二個 QTreeWidget

        # 第三部分布局
        sec3_layout = QHBoxLayout()
        buttons = QVBoxLayout()
        self.check_btn = QPushButton('確認')
        self.check_btn.clicked.connect(self.add_item)
        
        self.delete_btn = QPushButton('刪除')
        self.delete_btn.clicked.connect(self.delete_item)

        self.import_btn = QPushButton('匯入檔案')
        self.import_btn.clicked.connect(self.import_file)

        # 新增"匯入檔案二"按鈕
        self.import_btn_2 = QPushButton('匯入檔案二')
        self.import_btn_2.clicked.connect(self.import_file_2)

        self.draw_btn = QPushButton('繪圖')
        self.draw_btn.setFixedHeight(50)
        self.draw_btn.clicked.connect(self.draw_chart)

        buttons.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        buttons.addWidget(self.check_btn)
        buttons.setContentsMargins(0,20,0,0)
        buttons.addWidget(self.delete_btn)
        buttons.addStretch(1)
        buttons.addWidget(self.import_btn)
        buttons.addWidget(self.import_btn_2)  # 添加匯入檔案二按鈕
        buttons.addWidget(self.draw_btn)

        sec3_layout.addLayout(selected_tree_layout)
        sec3_layout.addLayout(buttons)
        layout.addLayout(sec3_layout)

        self.setLayout(layout)

        # 代碼結束
        self.show()

    def import_file(self):
        file_path = QFileDialog.getOpenFileName(self, '選擇文件', filter='*.xlsx')
        if not file_path[0]:
            return False
        df = pd.read_excel(file_path[0])
        for i in range(len(df)):
            item_list = [str(i+1), df.loc[i, '工作項目'], str(df.loc[i, '開始時間']), str(df.loc[i, '完成時間'])]
            item_widget = QTreeWidgetItem(item_list)
            self.selected_tree.addTopLevelItem(item_widget)

    def import_file_2(self):
        # 新增的匯入文件功能，將數據顯示在第二個樹形控件
        file_path = QFileDialog.getOpenFileName(self, '選擇文件', filter='*.xlsx')
        if not file_path[0]:
            return False
        df = pd.read_excel(file_path[0])
        for i in range(len(df)):
            item_list = [str(i+1), df.loc[i, '工作項目'], str(df.loc[i, '開始時間']), str(df.loc[i, '完成時間'])]
            item_widget = QTreeWidgetItem(item_list)
            self.selected_tree_2.addTopLevelItem(item_widget)

    def add_item(self):
        # 獲取輸入框的內容
        item = self.input_line.text()
        if not item:
            QMessageBox.critical(self, '錯誤', '請輸入工作項目')
            return False
        start_date = self.start_calender.selectedDate()
        over_date = self.over_calender.selectedDate()
        period = start_date.daysTo(over_date)
        if period < 0:
            QMessageBox.critical(self, '錯誤', '完成時間不能早於開始時間')
            return False
        # 將日期轉換為字符串
        start_date_str = start_date.toString('yyyy-MM-dd')
        over_date_str = over_date.toString('yyyy-MM-dd')
        # 添加到樹狀列表中
        item_num = self.selected_tree.topLevelItemCount() + 1
        item_list = [str(item_num), item, start_date_str, over_date_str]
        item_widget = QTreeWidgetItem(item_list)
        self.selected_tree.addTopLevelItem(item_widget)

    def delete_item(self):
        selected_items = self.selected_tree.selectedItems()
        if not selected_items:
            QMessageBox.critical(self, '錯誤', '請選擇要刪除的工作')
            return False
        for item in selected_items:
            index = self.selected_tree.indexFromItem(item).row()
            self.selected_tree.takeTopLevelItem(index)

    
    def draw_chart(self):
    # 获取两棵树的数据
        data = []
    
        # 获取第一个树形结构中的数据
        for i in range(self.selected_tree.topLevelItemCount()):
            item = self.selected_tree.topLevelItem(i)
            data.append([item.text(i) for i in range(4)])
    
        # 获取第二个树形结构中的数据
        for i in range(self.selected_tree_2.topLevelItemCount()):
            item = self.selected_tree_2.topLevelItem(i)
            data.append([item.text(i) for i in range(4)])
    
        # 将数据转换为DataFrame
        df = pd.DataFrame(data, columns=['編號', '工作項目', '開始時間', '完成時間'])
    
        # 将日期转换为时间格式
        df['開始時間'] = pd.to_datetime(df['開始時間'], errors='coerce')
        df['完成時間'] = pd.to_datetime(df['完成時間'], errors='coerce')
        
        # 排序数据
        df = df.sort_values(by="編號", ascending=False)
    
        # 计算每个工作的持续时间
        period = df['完成時間'] - df['開始時間']
    
        # 绘制图表
        plt.figure(figsize=(10, 5))
        plt.title("進度規劃")
        sns.set_theme(style='whitegrid', palette='summer')
        plt.grid(axis='x', linestyle='--', linewidth=0.5)
        sns.set_style({"font.sans-serif": ['Microsoft JhengHei']})
    
        # 使用红色显示第一个树的条形图，黑色显示第二个树的条形图
        first_tree_count = self.selected_tree.topLevelItemCount()
    
        for idx, (_, i) in enumerate(df.iterrows()):
            # 如果是来自第一个树结构，颜色为红色；如果是来自第二个树结构，颜色为黑色
            color = 'red' if idx < first_tree_count else 'black'
    
            # 检查开始时间和完成时间是否为有效日期
            if pd.isna(i["開始時間"]) or pd.isna(i["完成時間"]):
                continue  # 跳过无效日期的数据
            
            # 绘制条形图
            plt.barh(i["工作項目"], period[idx], left=i["開始時間"], height=0.2, edgecolor="grey", color=color, alpha=0.5)
    
            # 显示日期范围
            date_range = f"{i['開始時間'].strftime('%m/%d').lstrip('0').replace('/0', '/')}~{i['完成時間'].strftime('%m/%d').lstrip('0').replace('/0', '/')} \n      ({period[idx].days + 1}天)"
            plt.text(i["開始時間"] + pd.Timedelta(days=1), i["工作項目"], date_range, fontsize=8, va="center", bbox=dict(facecolor='none', edgecolor='none'))
    
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            plt.xticks(rotation=45, fontsize=8)
    
        plt.show()




class Qss_loader():
    def read_qss(self,file_path):
        with open(file_path,'r') as files:
            return files.read()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    qss = Qss_loader()
    qss_file = qss.read_qss('./PYQT6/style.qss')
    window.setStyleSheet(qss_file)
    sys.exit(app.exec())