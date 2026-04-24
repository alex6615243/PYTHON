from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QCalendarWidget, 
                             QTreeWidget, QTreeWidgetItem, QMessageBox, 
                             QFileDialog, QTabWidget, QInputDialog)
from PyQt6 import QtCore
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import sys

# ==========================================
# 分頁元件 (RegionTab)
# ==========================================
class RegionTab(QWidget):
    def __init__(self, region_name="主區域", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.region_name = region_name

        layout = QVBoxLayout()
        
        # 第一部分佈局：工作項目輸入
        sec1_layout = QHBoxLayout()
        item_label = QLabel('請輸入工作項目:')
        self.input_line = QLineEdit()
        sec1_layout.addWidget(item_label)
        sec1_layout.addWidget(self.input_line)
        layout.addLayout(sec1_layout)
        
        # 第二部分佈局：日曆與列表
        start_layout = QVBoxLayout()
        over_layout = QVBoxLayout()
        sec2_layout = QHBoxLayout()
        selected_tree_layout = QVBoxLayout()

        start_label = QLabel('請選擇開始時間:')
        over_label = QLabel('請選擇完成時間:')
        self.start_calender = QCalendarWidget()
        self.over_calender = QCalendarWidget()

        # --- 【修正】日曆暗色系樣式 (強制修改 QTableView 解決反黑問題) ---
        # --- 【修改】日曆灰色系樣式 (質感淺灰) ---
        gray_calendar_style = """
        /* 頂部導航列 (淺灰背景) */
        QCalendarWidget QWidget#qt_calendar_navigationbar { background-color: #D3D3D3; border-bottom: 1px solid #AAAAAA; }
        
        /* 導航列按鈕與文字 (深灰字體) */
        QCalendarWidget QToolButton { color: #222222; font-size: 14px; font-weight: bold; background-color: transparent; border-radius: 3px; margin: 2px; }
        QCalendarWidget QToolButton:hover { background-color: #B0B0B0; }
        
        /* 底層表格 (日期網格) */
        QCalendarWidget QTableView { 
            background-color: #F0F0F0; /* 整個日曆的底色 */
            color: #333333;            /* 日期數字的顏色 */
            selection-background-color: #808080; /* 選中時的背景色改為深灰色 */
            selection-color: #FFFFFF;  /* 選中時的文字顏色保持白色 */
            alternate-background-color: #E8E8E8; /* 交替行的微調底色 */
        }
        
        /* 非本月日期的顏色 (淡灰色) */
        QCalendarWidget QTableView:disabled { color: #A0A0A0; }
        
        /* 下拉選單 */
        QCalendarWidget QMenu { background-color: #F0F0F0; color: #333333; }
        QCalendarWidget QSpinBox { color: #333333; background-color: transparent; selection-background-color: #808080; selection-color: #FFFFFF; }
        """
        self.start_calender.setStyleSheet(gray_calendar_style)
        self.over_calender.setStyleSheet(gray_calendar_style)

        self.selected_tree = QTreeWidget() 
        self.selected_tree.setColumnCount(4)
        self.selected_tree.setHeaderLabels(['編號','工作項目','開始時間','完成時間'])
        self.selected_tree.setColumnWidth(0,50)
        self.selected_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.selected_tree.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        
        start_layout.addWidget(start_label)
        start_layout.addWidget(self.start_calender)
        over_layout.addWidget(over_label)
        over_layout.addWidget(self.over_calender)
        sec2_layout.addLayout(start_layout)
        sec2_layout.addLayout(over_layout)
        selected_tree_layout.addLayout(sec2_layout)
        selected_tree_layout.addWidget(self.selected_tree)
        
        # 第三部分佈局：按鈕
        sec3_layout = QHBoxLayout()
        buttons = QVBoxLayout()
        self.check_btn = QPushButton('確認')
        self.check_btn.clicked.connect(self.add_item)
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

    def add_item(self):
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
        start_date_str = start_date.toString('yyyy-MM-dd')
        over_date_str = over_date.toString('yyyy-MM-dd')
        item_num = self.selected_tree.topLevelItemCount() + 1
        item_list = [str(item_num), item, start_date_str, over_date_str]
        item_widget = QTreeWidgetItem(item_list)
        self.selected_tree.addTopLevelItem(item_widget)

    def add_milestone(self):
        item = self.input_line.text()
        if not item:
            QMessageBox.critical(self,'錯誤','請輸入里程碑項目')
            return False
        target_date = self.start_calender.selectedDate()
        date_str = target_date.toString('yyyy-MM-dd')
        item_num = self.selected_tree.topLevelItemCount() + 1
        item_list = [str(item_num), f"★ {item}", date_str, date_str] 
        item_widget = QTreeWidgetItem(item_list)
        self.selected_tree.addTopLevelItem(item_widget)

    def delete_item(self):
        selected_items = self.selected_tree.selectedItems()
        if not selected_items:
            QMessageBox.critical(self,'錯誤','請選擇要刪除的工作')
            return False
        for item in selected_items:
            root = self.selected_tree.invisibleRootItem()
            root.removeChild(item)
    
    def import_file(self):
        file_path = QFileDialog.getOpenFileName(self,'選擇文件',filter='*.xlsx')
        if not file_path[0]: return False
        df = pd.read_excel(file_path[0])
        for i in range(len(df)):
            item_list = [str(i+1), df.loc[i,'工作項目'], str(df.loc[i,'開始時間']).split(' ')[0], str(df.loc[i,'完成時間']).split(' ')[0]]
            item_widget = QTreeWidgetItem(item_list)
            self.selected_tree.addTopLevelItem(item_widget)

    def draw_chart(self):
        data = []
        for i in range(self.selected_tree.topLevelItemCount()):
            item = self.selected_tree.topLevelItem(i)
            data.append([item.text(i) for i in range(4)])
        if not data: return
        
        project_name = self.window().project_name_input.text() if self.window().project_name_input.text() else "未命名工程案"

        df = pd.DataFrame(data,columns=['編號','工作項目','開始時間','完成時間'])
        df['開始時間'] = pd.to_datetime(df['開始時間'])
        df['完成時間'] = pd.to_datetime(df['完成時間'])
        df = df.sort_index(ascending=False)
        period = df['完成時間'] - df['開始時間']
        
        # 建立獨立 Y 座標 (防止同名工作合併)
        y_positions = range(len(df))
        
        plt.figure(figsize=(10,5))
        plt.title(f"{project_name} - {self.region_name}", fontsize=16, fontweight='bold') 
        sns.set_theme(style='whitegrid',palette='summer')
        plt.grid(axis='both', linestyle='--', linewidth=0.5)
        sns.set_style({"font.sans-serif":['Microsoft JhengHei', 'PingFang TC', 'Heiti TC']})
        
        # 使用獨立 Y 座標繪圖
        for y, (_, i) in zip(y_positions, df.iterrows()):
            if period[_].days == 0:
                plt.plot([i["開始時間"]], [y], marker='*', markersize=18, color='gold', markeredgecolor='darkorange')
                date_str = i['開始時間'].strftime('%m/%d').lstrip('0').replace('/0', '/')
                plt.text(i["開始時間"] + pd.Timedelta(days=0.5), y, f" {date_str}\n (里程碑)", fontsize=8, va="center")
            else:
                plt.barh(y, period[_].days, left=i["開始時間"], height=0.2, edgecolor="grey", color="skyblue")
                date_range = f"{i['開始時間'].strftime('%m/%d').lstrip('0').replace('/0', '/')}~{i['完成時間'].strftime('%m/%d').lstrip('0').replace('/0', '/')} \n ({period[_].days + 1}天)"
                plt.text(i["開始時間"] + pd.Timedelta(days=1), y, date_range, fontsize=8, va="center", bbox=dict(facecolor='none', edgecolor='none'))

        # 將原本的數值 Y 座標替換為工作名稱文字
        plt.yticks(y_positions, df['工作項目'])
        
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        plt.xticks(rotation=45, fontsize=8)
        plt.show()

# ==========================================
# 主視窗 (管理 TabWidget 與工程案名稱)
# ==========================================
class MainWindow(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle('多區域進度規劃系統')
        self.resize(850, 750)

        self.main_layout = QVBoxLayout(self)
        
        project_header_layout = QHBoxLayout()
        project_label = QLabel('🏢 本工程案名稱:')
        project_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.project_name_input = QLineEdit()
        self.project_name_input.setPlaceholderText("請輸入工程案名稱（將顯示於圖表標題）...")
        self.project_name_input.setStyleSheet("padding: 5px; font-size: 14px;")
        project_header_layout.addWidget(project_label)
        project_header_layout.addWidget(self.project_name_input)
        self.main_layout.addLayout(project_header_layout)
        
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        
        self.add_tab_btn = QPushButton('➕ 新增區域')
        self.add_tab_btn.clicked.connect(self.add_new_tab)
        self.tabs.setCornerWidget(self.add_tab_btn, QtCore.Qt.Corner.TopRightCorner)

        self.main_layout.addWidget(self.tabs)

        self.draw_all_btn = QPushButton('🌟 整合繪圖 (輸出全區總表)')
        self.draw_all_btn.setFixedHeight(55)
        self.draw_all_btn.setStyleSheet("""
            QPushButton { background-color: #2E8B57; color: white; font-size: 16px; font-weight: bold; border-radius: 5px; }
            QPushButton:hover { background-color: #3CB371; }
        """)
        self.draw_all_btn.clicked.connect(self.draw_all_charts)
        self.main_layout.addWidget(self.draw_all_btn)

        self.create_tab("主區域")

    def add_new_tab(self):
        text, ok = QInputDialog.getText(self, '新增區域', '請輸入新區域的名稱:')
        if ok and text: self.create_tab(text)

    def create_tab(self, region_name):
        new_tab = RegionTab(region_name=region_name)
        self.tabs.addTab(new_tab, region_name)
        self.tabs.setCurrentWidget(new_tab)

    def close_tab(self, index):
        if self.tabs.count() > 1: self.tabs.removeTab(index)
        else: QMessageBox.warning(self, '提示', '必須保留至少一個區域！')

    def draw_all_charts(self):
        data = []
        project_name = self.project_name_input.text() if self.project_name_input.text() else "未命名工程案"
        
        for i in range(self.tabs.count()):
            tab_widget = self.tabs.widget(i)
            region_name = self.tabs.tabText(i)
            for j in range(tab_widget.selected_tree.topLevelItemCount()):
                item = tab_widget.selected_tree.topLevelItem(j)
                # 【修改】不再加上區域前綴，直接抓取工作項目名稱
                task_name = item.text(1) 
                data.append([item.text(0), task_name, item.text(2), item.text(3), region_name])
                
        if not data: return

        df = pd.DataFrame(data, columns=['編號','工作項目','開始時間','完成時間', '區域'])
        df['開始時間'] = pd.to_datetime(df['開始時間'])
        df['完成時間'] = pd.to_datetime(df['完成時間'])
        df = df.sort_index(ascending=False)
        period = df['完成時間'] - df['開始時間']
        
        # 【修改】建立獨立 Y 座標 (防止不同區域的同名工作合併成同一條線)
        y_positions = range(len(df))
        
        plt.figure(figsize=(12, 7))
        plt.title(f"{project_name} - 全區域總表", fontsize=18, fontweight='bold')
        sns.set_theme(style='whitegrid')
        sns.set_style({"font.sans-serif":['Microsoft JhengHei', 'PingFang TC', 'Heiti TC']})
        
        unique_regions = df['區域'].unique()
        colors = sns.color_palette("husl", len(unique_regions))
        region_color_map = dict(zip(unique_regions, colors))

        # 使用獨立 Y 座標繪圖
        for y, (_, i) in zip(y_positions, df.iterrows()):
            current_color = region_color_map[i['區域']]
            if period[_].days == 0:
                # 【修改】將星號顏色改為 current_color，並加上白色邊框讓它更立體
                plt.plot([i["開始時間"]], [y], marker='*', markersize=18, color=current_color, markeredgecolor='white')
                date_str = i['開始時間'].strftime('%m/%d').lstrip('0').replace('/0', '/')
                plt.text(i["開始時間"] + pd.Timedelta(days=0.5), y, f" {date_str}\n (里程碑)", fontsize=8, va="center")
            else:
                plt.barh(y, period[_].days, left=i["開始時間"], height=0.4, edgecolor="grey", color=current_color)
                date_range = f"{i['開始時間'].strftime('%m/%d').lstrip('0').replace('/0', '/')}~{i['完成時間'].strftime('%m/%d').lstrip('0').replace('/0', '/')} \n ({period[_].days + 1}天)"
                plt.text(i["開始時間"] + pd.Timedelta(days=1), y, date_range, fontsize=8, va="center", bbox=dict(facecolor='none', edgecolor='none'))

        # 【修改】將數值的 Y 座標轉換回乾淨的工作項目名稱
        plt.yticks(y_positions, df['工作項目'])

        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor=region_color_map[region], edgecolor='grey', label=region) for region in unique_regions]
        plt.legend(handles=legend_elements, title="分區標示", loc="upper left", bbox_to_anchor=(1.01, 1))
        
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        plt.xticks(rotation=45, fontsize=8)
        plt.tight_layout() 
        plt.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    
    try:
        with open('./PYQT6/style.qss','r') as f:
            window.setStyleSheet(f.read())
    except:
        pass
        
    window.show()
    sys.exit(app.exec())