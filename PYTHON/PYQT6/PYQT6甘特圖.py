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

        #代碼開始
        self.setWindowTitle('進度規劃')
        self.resize(700,600)

        #第一部分布局
        layout = QVBoxLayout()
        sec1_layout = QHBoxLayout()
        item_label = QLabel('請輸入工作項目:')
        self.input_line = QLineEdit()
        
        sec1_layout.addWidget(item_label)
        sec1_layout.addWidget(self.input_line)
        layout.addLayout(sec1_layout)
        #第二部分布局
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
        self.selected_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)#設置列表選項可多選
        self.selected_tree.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)#設置列表可上下拖動
        
        start_layout.addWidget(start_label)
        start_layout.addWidget(self.start_calender)
        over_layout.addWidget(over_label)
        over_layout.addWidget(self.over_calender)
        sec2_layout.addLayout(start_layout)
        sec2_layout.addLayout(over_layout)
        selected_tree_layout.addLayout(sec2_layout)
        selected_tree_layout.addWidget(self.selected_tree)
        
        #第三部分布局
        sec3_layout = QHBoxLayout()
        buttons = QVBoxLayout()
        self.check_btn =QPushButton('確認')
        self.check_btn.clicked.connect(self.add_item)

        # 【新增】里程碑按鈕
        self.milestone_btn = QPushButton('里程碑')
        self.milestone_btn.clicked.connect(self.add_milestone)
        
        self.delete_btn = QPushButton('刪除')
        self.delete_btn.clicked.connect(self.delete_item)

        self.import_btn = QPushButton('匯入檔案')
        self.import_btn.clicked.connect(self.import_file)

        self.draw_btn = QPushButton('繪圖')
        self.draw_btn.setFixedHeight(50)
        self.draw_btn.clicked.connect(self.draw_chart)


        buttons.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        buttons.addWidget(self.check_btn)
        buttons.addWidget(self.milestone_btn)
        buttons.setContentsMargins(0,20,0,0)
        buttons.addWidget(self.delete_btn)
        buttons.addStretch(1)
        buttons.addWidget(self.import_btn)
        buttons.addWidget(self.draw_btn)

        sec3_layout.addLayout(selected_tree_layout)
        sec3_layout.addLayout(buttons)
        layout.addLayout(sec3_layout)

        self.setLayout(layout)

        #代碼結束
        self.show()

    def add_item(self):
        #獲取輸入框的內容
        item = self.input_line.text()
        if not item:
            QMessageBox.critical(self,'錯誤','請輸入工作項目')
            return False
        start_date = self.start_calender.selectedDate()
        over_date = self.over_calender.selectedDate()
        period = start_date.daysTo(over_date)
        if period < 0:
            QMessageBox.critical(self,'錯誤','完成時間不能早於開始時間')
            return False
        #將日期轉換為字符串
        start_date_str = start_date.toString('yyyy-MM-dd')
        over_date_str = over_date.toString('yyyy-MM-dd')
        #添加到樹狀列表中
        item_num = self.selected_tree.topLevelItemCount() + 1
        item_list = [str(item_num),item,start_date_str,over_date_str]
        item_widget = QTreeWidgetItem(item_list)
        self.selected_tree.addTopLevelItem(item_widget)

    def delete_item(self):
        selected_items = self.selected_tree.selectedItems()
        if not selected_items:
            QMessageBox.critical(self, '錯誤', '請選擇要刪除的工作')
            return
        
        # 透過 item 尋找父節點(隱藏的 root)並移除自身，避免 index 偏移問題
        for item in selected_items:
            root = self.selected_tree.invisibleRootItem()
            root.removeChild(item)

    def add_milestone(self):
        # 獲取輸入框的內容
        item = self.input_line.text()
        if not item:
            QMessageBox.critical(self,'錯誤','請輸入里程碑項目')
            return False
            
        # 里程碑只需讀取開始時間
        target_date = self.start_calender.selectedDate()
        date_str = target_date.toString('yyyy-MM-dd')
        
        # 添加到樹狀列表中 (開始與完成時間設為同一天)
        item_num = self.selected_tree.topLevelItemCount() + 1
        # 在名稱前加上標記，方便使用者在列表中識別
        item_list = [str(item_num), f"★ {item}", date_str, date_str] 
        item_widget = QTreeWidgetItem(item_list)
        self.selected_tree.addTopLevelItem(item_widget)
    
    def import_file(self):
        file_path = QFileDialog.getOpenFileName(self,'選擇文件',filter='*.xlsx')
        if not file_path[0]:
            return False
        
        df = pd.read_excel(file_path[0])
        for i in range(len(df)):
            item_list = [str(i+1),df.loc[i,'工作項目'],str(df.loc[i,'開始時間']),str(df.loc[i,'完成時間'])]
            if not item_list[0] or not item_list[1] or not item_list[2] or not item_list[3]:
                QMessageBox.critical(self,'錯誤','文件中存在空值')
                return False
            item_widget = QTreeWidgetItem(item_list)
            self.selected_tree.addTopLevelItem(item_widget)

    def draw_chart(self):
        #獲取樹狀列表中的數據
        data = []
        for i in range(self.selected_tree.topLevelItemCount()):
            item = self.selected_tree.topLevelItem(i)
            data.append([item.text(i) for i in range(4)])
        #將數據轉換為DataFrame
        df = pd.DataFrame(data,columns=['編號','工作項目','開始時間','完成時間'])
        #將日期轉換為時間格式
        df['開始時間'] = pd.to_datetime(df['開始時間'])
        df['完成時間'] = pd.to_datetime(df['完成時間'])
        df = df.sort_index(ascending=False)
        #計算每個工作的持續時間
        period = df['完成時間'] - df['開始時間']
        #繪製圖表
        plt.figure(figsize=(10,5))
        plt.title("工作進度規劃圖", fontsize=16)
        sns.set_theme(style='whitegrid',palette='summer')
        plt.grid(axis='both', linestyle='--', linewidth=0.5)
        sns.set_style({"font.sans-serif":['Microsoft JhengHei']})
        
 # --- draw_chart 迴圈部分替換成以下程式碼 ---
        for _, i in df.iterrows():
            if period[_].days == 0:
                # 【繪製里程碑】如果開始與完成時間差距為 0 天，畫星星
                # marker='*' 表示星型，markersize 調整大小，color 設為金色
                plt.plot([i["開始時間"]], [i["工作項目"]], marker='*', markersize=18, color='gold', markeredgecolor='darkorange')
                
                # 里程碑的文字標籤只需顯示單一日期
                date_str = i['開始時間'].strftime('%m/%d').lstrip('0').replace('/0', '/')
                plt.text(i["開始時間"] + pd.Timedelta(days=0.5), i["工作項目"], f" {date_str}\n (里程碑)", fontsize=8, va="center")
            
            else:
                # 【繪製一般任務】
                plt.barh(i["工作項目"], period[_].days, left=i["開始時間"], height=0.2, edgecolor="grey", color="skyblue")
                date_range = f"{i['開始時間'].strftime('%m/%d').lstrip('0').replace('/0', '/')}~{i['完成時間'].strftime('%m/%d').lstrip('0').replace('/0', '/')} \n      ({period[_].days + 1}天)"
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