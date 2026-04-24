import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

# 讀取 Excel 檔案
file_path = r"C:\Users\234500\Desktop\123.xlsx"
df = pd.read_excel(file_path)

# 增加小寫欄位做比較
df['From_lower'] = df['From'].str.strip().str.lower()
df['Circuit_upper'] = df['Circuit'].str.strip().str.upper()

# 儲存路徑
path_edges = []

def trace_path(start_device):
    current_device = start_device.strip().lower()
    selected_circuit = None  # 用來記錄第一次選擇的電路代碼

    while True:
        # 篩選出 current_device 開頭的資料
        matches = df[df['From_lower'] == current_device]

        if selected_circuit:
            # 如果已經設定 Circuit，則只留相同 Circuit 的選項
            matches = matches[matches['Circuit_upper'] == selected_circuit]

        if matches.empty:
            print(f"\n設備 {current_device.upper()} 沒有符合 Circuit 條件的後續連線，追蹤結束。")
            break

        # 自動跳過只有一條選項的情況
        if len(matches) == 1:
            selected = matches.iloc[0]
            print(f"\n只剩一條連線，自動選擇：TO: {selected['TO']}, Circuit: {selected['Circuit']}, Cable No.: {selected['Cable No.']}")
        else:
            # 顯示選項
            print(f"\n設備 {current_device.upper()} 的連線如下：")
            for i, (_, row) in enumerate(matches.iterrows()):
                print(f"{i + 1}. TO: {row['TO']}, Circuit: {row['Circuit']}, Cable No.: {row['Cable No.']}")

            choice = input("\n請輸入要追蹤的選項編號（或輸入 q 離開）: ")
            if choice.lower() == 'q':
                break

            try:
                index = int(choice) - 1
                if 0 <= index < len(matches):
                    selected = matches.iloc[index]
                else:
                    print("無效的選項，請重新輸入。")
                    continue
            except ValueError:
                print("請輸入數字選項或 q 離開。")
                continue

        # 紀錄路徑並設定下一輪條件
        from_dev = selected['From'].strip()
        to_dev = selected['TO'].strip()
        path_edges.append((from_dev, to_dev))

        # 設定第一次選擇後的 circuit 過濾條件
        if not selected_circuit:
            selected_circuit = selected['Circuit_upper']

        # 下一個查詢目標
        current_device = to_dev.strip().lower()

def draw_graph(edges):
    G = nx.DiGraph()
    G.add_edges_from(edges)

    pos = nx.spring_layout(G)
    plt.figure(figsize=(10, 6))
    nx.draw(G, pos, with_labels=True, node_color='lightblue', edge_color='gray',
            node_size=2000, font_size=10, arrowsize=20)
    plt.title("設備連線路徑（Circuit 限制追蹤）")
    plt.show()

# 主程式入口
start = input("請輸入要查詢的起始設備名稱（From 欄位）: ")
trace_path(start)

# 畫圖
if path_edges:
    draw_graph(path_edges)
else:
    print("沒有任何有效的連線。")
