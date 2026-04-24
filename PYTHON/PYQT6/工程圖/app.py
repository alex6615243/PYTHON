import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import os

# ==========================================
# 檔案儲存設定
# ==========================================
SAVE_FILE = "project_data.csv" # 存檔的檔名

# 讀取存檔的函數
def load_data():
    if os.path.exists(SAVE_FILE):
        # 讀取 CSV，並確保日期欄位格式正確
        df = pd.read_csv(SAVE_FILE)
        df['開始時間'] = pd.to_datetime(df['開始時間'])
        df['完成時間'] = pd.to_datetime(df['完成時間'])
        return df
    else:
        # 如果沒有存檔，建立空的 DataFrame
        return pd.DataFrame(columns=['工作項目', '開始時間', '完成時間', '區域', '是否為里程碑'])

# 儲存檔案的函數
def save_data(df):
    # 將資料存成 CSV，不包含 index
    df.to_csv(SAVE_FILE, index=False)

# ==========================================
# 頁面與狀態初始化
# ==========================================
st.set_page_config(layout="wide", page_title="多區域進度規劃系統")

# 初始化 session_state，啟動時呼叫 load_data() 讀取舊資料
if 'tasks' not in st.session_state:
    st.session_state.tasks = load_data()

st.title("🏢 營建工程進度規劃系統")

# ==========================================
# 側邊欄：資料輸入區
# ==========================================
with st.sidebar:
    st.header("➕ 新增工作項目")
    
    with st.form("add_task_form"):
        region = st.selectbox("選擇區域", ["A區", "B區", "C區", "主區域"])
        task_name = st.text_input("工作項目名稱")
        start_date = st.date_input("開始時間")
        end_date = st.date_input("完成時間")
        is_milestone = st.checkbox("這是一個里程碑 (單日檢核點)")
        
        submit = st.form_submit_button("加入清單")
        
        if submit and task_name:
            if end_date < start_date and not is_milestone:
                st.error("完成時間不能早於開始時間！")
            else:
                if is_milestone:
                    end_date = start_date
                    task_name = f"★ {task_name}"
                
                new_task = pd.DataFrame([{
                    '工作項目': task_name,
                    '開始時間': pd.to_datetime(start_date),
                    '完成時間': pd.to_datetime(end_date),
                    '區域': region,
                    '是否為里程碑': is_milestone
                }])
                # 更新 session_state
                st.session_state.tasks = pd.concat([st.session_state.tasks, new_task], ignore_index=True)
                
                # 【新增】馬上將最新資料寫入硬碟存檔
                save_data(st.session_state.tasks)
                st.success("已加入並自動存檔！")

# ==========================================
# 主畫面：資料表與整合繪圖
# ==========================================
st.subheader("📋 目前工作清單")

# 使用者可以在表格上直接修改、刪除列
edited_df = st.data_editor(st.session_state.tasks, num_rows="dynamic", use_container_width=True)

# 檢查使用者是否有在表格上做修改，如果有，就更新並存檔
if not edited_df.equals(st.session_state.tasks):
    st.session_state.tasks = edited_df
    save_data(edited_df) # 【新增】表格修改後自動存檔

st.divider()

# 繪圖區
if st.button("🌟 產生整合甘特圖", type="primary"):
    df = st.session_state.tasks.copy()
    
    if df.empty:
        st.warning("目前沒有資料可以繪圖！")
    else:
        # 計算天數差 (為了保證型別正確，先轉回 datetime 再算)
        df['開始時間'] = pd.to_datetime(df['開始時間'])
        df['完成時間'] = pd.to_datetime(df['完成時間'])
        df['period'] = (df['完成時間'] - df['開始時間']).dt.days
        
        y_positions = range(len(df))
        
        fig, ax = plt.subplots(figsize=(12, 7))
        plt.title("工程案全區域總表", fontsize=18, fontweight='bold')
        sns.set_theme(style='whitegrid')
        sns.set_style({"font.sans-serif":['Microsoft JhengHei', 'PingFang TC', 'Heiti TC']})
        
        unique_regions = df['區域'].unique()
        colors = sns.color_palette("husl", len(unique_regions))
        region_color_map = dict(zip(unique_regions, colors))

        for y, (_, row) in zip(y_positions, df.iterrows()):
            current_color = region_color_map[row['區域']]
            
            if row['是否為里程碑']:
                ax.plot([row["開始時間"]], [y], marker='*', markersize=18, color=current_color, markeredgecolor='white')
            else:
                ax.barh(y, row['period'], left=row["開始時間"], height=0.4, edgecolor="grey", color=current_color)
        
        ax.set_yticks(y_positions)
        ax.set_yticklabels(df['工作項目'])
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        st.pyplot(fig)