import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

# 讀取 Excel
file_path = r"C:\Users\234500\Desktop\123.xlsx"
df = pd.read_excel(file_path)

# 統一處理大小寫
df['From_lower'] = df['From'].str.strip().str.lower()

# 儲存追蹤路徑用的清單
path_edges = []

def trace_path(start_device):
    current_device = start_device.strip().lower()

    while True:
        # 查詢所有以 current_device 為起點的連線
        matches = df[df['From_lower'] == current_device]

        if matches.empty:
            print(f"\n設備 {current_device.upper()} 沒有後續連線，追蹤結束。")
            break

        print(f"\n設備 {current_device.upper()} 的連線如下：")
        for i, (_, row) in enumerate(matches.iterrows()):
            print(f"{i + 1}. TO: {row['TO']}, Circuit: {row['Circuit']}, Cable No.: {row['Cable No.']}")

        # 使用者選擇要追蹤哪一條
        choice = input("\n請輸入要追蹤的選項編號（或輸入 q 離開）: ")
        if choice.lower() == 'q':
            break

        try:
            index = int(choice) - 1
            if 0 <= index < len(matches):
                selected = matches.iloc[index]
                from_dev = selected['From'].strip()
                to_dev = selected['TO'].strip()

                # 儲存這條邊
                path_edges.append((from_dev, to_dev))

                # 設定下一輪要查的設備
                current_device = to_dev.strip().lower()
            else:
                print("請輸入有效的選項。")
        except ValueError:
            print("請輸入數字選項。")

def draw_graph(edges):
    G = nx.DiGraph()
    G.add_edges_from(edges)

    pos = nx.spring_layout(G)  # 自動排版
    plt.figure(figsize=(10, 6))
    nx.draw(G, pos, with_labels=True, node_color='lightblue', edge_color='gray',
            node_size=2000, font_size=10, arrowsize=20)
    plt.title("設備連線關係圖")
    plt.show()

# 主程式
start = input("請輸入要查詢的起始設備名稱（From 欄位）: ")
trace_path(start)

# 畫圖
if path_edges:
    draw_graph(path_edges)
else:
    print("沒有可顯示的連線路徑。")


