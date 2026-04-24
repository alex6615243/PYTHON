import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

# 讀取資料
file_path = r"C:\Users\234500\Desktop\123.xlsx"
df = pd.read_excel(file_path)

# 預處理欄位
df['From_lower'] = df['From'].str.strip().str.lower()
df['TO_lower'] = df['TO'].str.strip().str.lower()
df['Circuit_upper'] = df['Circuit'].str.strip().str.upper()

# 儲存上下游路徑
upstream_edges = []
downstream_edges = []

def trace_direction(current_device, direction='downstream'):
    """
    direction: 'downstream'（從 FROM 往 TO）或 'upstream'（從 TO 找 FROM）
    回傳路徑邊
    """
    circuit_lock = None
    path_edges = []

    while True:
        current_device_lc = current_device.lower()

        if direction == 'downstream':
            matches = df[df['From_lower'] == current_device_lc]
        else:  # upstream
            matches = df[df['TO_lower'] == current_device_lc]

        if circuit_lock:
            matches = matches[matches['Circuit_upper'] == circuit_lock]

        if matches.empty:
            print(f"\n設備 {current_device.upper()} 沒有符合 Circuit 條件的 {direction} 連線。")
            break

        # 若只有一條連線，自動選擇
        if len(matches) == 1:
            selected = matches.iloc[0]
            print(f"\n設備 {current_device.upper()} 的唯一連線，自動選擇：")
        else:
            print(f"\n設備 {current_device.upper()} 的{direction}連線如下：")
            for i, (_, row) in enumerate(matches.iterrows()):
                if direction == 'downstream':
                    print(f"{i + 1}. TO: {row['TO']}, Circuit: {row['Circuit']}, Cable No.: {row['Cable No.']}")
                else:
                    print(f"{i + 1}. FROM: {row['From']}, Circuit: {row['Circuit']}, Cable No.: {row['Cable No.']}")

            choice = input("\n請輸入要追蹤的選項編號（或輸入 q 離開）: ")
            if choice.lower() == 'q':
                break
            try:
                index = int(choice) - 1
                if 0 <= index < len(matches):
                    selected = matches.iloc[index]
                else:
                    print("無效選項，請重新輸入。")
                    continue
            except ValueError:
                print("請輸入有效數字或 q 離開。")
                continue

        from_dev = selected['From'].strip()
        to_dev = selected['TO'].strip()
        circuit = selected['Circuit_upper']

        # 鎖定 Circuit（只做第一次）
        if not circuit_lock:
            circuit_lock = circuit

        # 儲存邊，方向依據
        if direction == 'downstream':
            path_edges.append((from_dev, to_dev))
            current_device = to_dev
        else:
            path_edges.append((from_dev, to_dev))
            current_device = from_dev

    return path_edges

def draw_full_graph(up_edges, down_edges, center_device):
    G = nx.DiGraph()
    G.add_edges_from(up_edges + down_edges)

    pos = nx.spring_layout(G)
    plt.figure(figsize=(10, 6))
    nx.draw(G, pos, with_labels=True, node_color='lightgreen', edge_color='black',
            node_size=2000, font_size=10, arrowsize=20)
    plt.title(f"設備 {center_device.upper()} 的上下游電路圖")
    plt.show()

# 主程式
center_device = input("請輸入要查詢的設備（中心設備）: ").strip()

print("\n▶️ 開始追蹤下游（From → TO）...")
downstream_edges = trace_direction(center_device, direction='downstream')

print("\n🔁 開始追蹤上游（TO → From）...")
upstream_edges = trace_direction(center_device, direction='upstream')

# 畫圖
if upstream_edges or downstream_edges:
    draw_full_graph(upstream_edges, downstream_edges, center_device)
else:
    print("未產生任何設備連線，無圖可顯示。")
