import sys
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.lines import Line2D
from PyQt5.QtGui import QFont  # 在 import 區也記得加上這行
from matplotlib.patches import Patch
from PyQt5.QtWidgets import QToolTip
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit,
    QLabel, QMessageBox, QFileDialog, QInputDialog
)

# Circuit 對應顏色
circuit_colors = {
    'SH': 'red',
    'HT': 'orange',
    'HM': '#8B4513',
    'HC': 'green',
    'LC': 'blue',
    'LT': 'purple'
}





# 讀取資料
df = pd.read_excel(r"C:\Users\234500\Desktop\123.xlsx")
df['From_lower'] = df['From'].str.strip().str.lower()
df['TO_lower'] = df['TO'].str.strip().str.lower()
df['Circuit_upper'] = df['Circuit'].str.strip().str.upper()

class CableTracer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("設備上下游查詢圖")
        self.setGeometry(200, 100, 1000, 700)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.input_label = QLabel("請輸入中心設備名稱：")
        self.input_label
        self.input_field = QLineEdit()
        self.search_button = QPushButton("查詢上下游並繪圖")
        self.save_button = QPushButton("匯出圖（PNG 或 PDF）")

        self.search_button.clicked.connect(self.search_and_plot)
        self.save_button.clicked.connect(self.export_plot)

        self.layout.addWidget(self.input_label)
        self.layout.addWidget(self.input_field)
        self.layout.addWidget(self.search_button)
        self.layout.addWidget(self.save_button)

        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

        self.edges = []  # 儲存 (from, to, circuit, cable)

    def search_and_plot(self):
        self.figure.clear()
        self.edges = []

        device = self.input_field.text().strip().lower()
        if not device:
            QMessageBox.warning(self, "錯誤", "請輸入設備名稱")
            return

        self.trace(device, direction='upstream')
        self.trace(device, direction='downstream')

        if not self.edges:
            QMessageBox.information(self, "查無資料", "找不到連線")
            return

        self.plot_graph(device)

    def trace(self, start_device, direction):
        current = start_device
        circuit_filter = None

        while True:
            if direction == 'downstream':
                matches = df[df['From_lower'] == current]
            else:
                matches = df[df['TO_lower'] == current]

            if circuit_filter:
                matches = matches[matches['Circuit_upper'] == circuit_filter]

            if matches.empty:
                break

            if len(matches) == 1:
                selected = matches.iloc[0]
            else:
                options = []
                for _, row in matches.iterrows():
                    text = f"{row['From']} ➜ {row['TO']} | {row['Circuit']} | {row['Cable No.']}"
                    options.append(text)

                item, ok = QInputDialog.getItem(self, f"選擇{direction}路徑", "請選擇一條連線：", options, editable=False)
                if not ok:
                    break
                selected = matches.iloc[options.index(item)]

            from_dev = selected['From'].strip()
            to_dev = selected['TO'].strip()
            circuit = selected['Circuit_upper']
            cable = selected['Cable No.']

            self.edges.append((from_dev, to_dev, circuit, cable))

            if not circuit_filter:
                circuit_filter = circuit

            current = to_dev.lower() if direction == 'downstream' else from_dev.lower()

    def plot_graph(self, center_device):
        self.figure.clf()
        G = nx.DiGraph()
        edge_colors = {}

        for f, t, circuit, cable in self.edges:
            G.add_edge(f, t)
            edge_colors[(f, t)] = circuit_colors.get(circuit, 'black')

        pos = nx.spring_layout(G)
        ax = self.figure.add_subplot(111)
        edge_color_values = [edge_colors[(f, t)] for f, t in G.edges()]

        self.pos = pos  # 儲存位置
        self.graph = G  # 儲存圖
        self.ax = ax    # 儲存圖軸

        nx.draw(G, pos, ax=ax, with_labels=True, node_color='lightgreen',
                edge_color=edge_color_values, node_size=3000, font_size=10, arrowsize=20)

        legend_items = [Patch(color=color, label=circ) for circ, color in circuit_colors.items()]
        ax.legend(handles=legend_items, loc='lower right', title="Circuit 類型")

        ax.set_title(f"{center_device.upper()} 的上下游連線圖", fontsize=14)

        self.figure.tight_layout()
        self.canvas.draw()

        # 接收滑鼠點擊事件
        self.canvas.mpl_connect("button_press_event", self.on_click)



    def export_plot(self):
        if not self.edges:
            QMessageBox.information(self, "尚未繪圖", "請先查詢再匯出")
            return

        path, _ = QFileDialog.getSaveFileName(self, "儲存圖檔", "", "PNG 圖檔 (*.png);;PDF 檔案 (*.pdf)")
        if path:
            self.figure.savefig(path, bbox_inches='tight')
            QMessageBox.information(self, "儲存成功", f"已儲存圖形至：\n{path}")

    def on_click(self, event):
        if event.inaxes != self.ax:
            return

        for node, (x, y) in self.pos.items():
            # 判斷滑鼠點擊是否靠近節點
            if abs(event.xdata - x) < 0.05 and abs(event.ydata - y) < 0.05:
                related_rows = df[
                    (df['From'].str.strip() == node) | (df['TO'].str.strip() == node)
                ][['Cable No.']].dropna()

                if related_rows.empty:
                    info = "無相關 Cable No."
                else:
                    cable_list = related_rows['Cable No.'].unique().tolist()
                    info = "\n".join(cable_list)

                QMessageBox.information(self, f"{node} 的 Cable No.", info)
                break


class QSSloader:
    def load_qss(self):
        with open('./PYQT6/style.qss','r') as f:
            style = f.read()
        return style 


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # ✅ 設定全域字體為微軟正黑體
    font = QFont("Microsoft JhengHei", 10)
    app.setFont(font)
    
    window = CableTracer()
    window.show()
    
    qss = QSSloader().load_qss()
    app.setStyleSheet(qss)
    
    sys.exit(app.exec())

