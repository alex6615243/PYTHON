import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import os

# ==========================================
# 檔案儲存與載入
# ==========================================
SAVE_FILE = "project_data_v2.csv"
REGION_FILE = "regions.csv"

def load_data():
    if os.path.exists(SAVE_FILE):
        df = pd.read_csv(SAVE_FILE)
        df['開始時間'] = pd.to_datetime(df['開始時間'])
        df['完成時間'] = pd.to_datetime(df['完成時間'])
        return df
    return pd.DataFrame(columns=['工作項目', '開始時間', '完成時間', '區域', '是否為里程碑'])

def load_regions():
    if os.path.exists(REGION_FILE):
        return pd.read_csv(REGION_FILE)['區域名稱'].tolist()
    return ["主區域"]

# ==========================================
# 初始化設定
# ==========================================
st.set_page_config(layout="wide", page_title="多區域工程規劃系統")

if 'tasks' not in st.session_state:
    st.session_state.tasks = load_data()
if 'regions' not in st.session_state:
    st.session_state.regions = load_regions()

st.title("🏢 營建工程進度規劃系統")
project_name = st.text_input("📌 工程案名稱：", value="未命名工程案")

# ==========================================
# 區域管理器 (支援新增與更名)
# ==========================================
st.sidebar.header("⚙️ 區域管理")
new_region_name = st.sidebar.text_input("新增區域名稱：")
if st.sidebar.button("➕ 新增區域"):
    if new_region_name and new_region_name not in st.session_state.regions:
        st.session_state.regions.append(new_region_name)
        pd.DataFrame(st.session_state.regions, columns=['區域名稱']).to_csv(REGION_FILE, index=False)
        st.sidebar.success(f"已新增：{new_region_name}")

# 使用 Data Editor 讓使用者可以直接改名
st.sidebar.write("編輯區域名稱 (直接在下方表格修改)：")
# 建立一個暫時的 DataFrame 供編輯
region_df = pd.DataFrame(st.session_state.regions, columns=['區域名稱'])
edited_region_df = st.sidebar.data_editor(region_df, num_rows="dynamic", use_container_width=True)

# 邏輯：如果區域名稱發生變動，同步更新 tasks 裡的區域標籤
if not edited_region_df.equals(region_df):
    old_regions = region_df['區域名稱'].tolist()
    new_regions = edited_region_df['區域名稱'].tolist()
    
    # 檢查是否有更名動作
    for old, new in zip(old_regions, new_regions):
        if old != new:
            # 同步更新工作清單中的區域標籤
            st.session_state.tasks.loc[st.session_state.tasks['區域'] == old, '區域'] = new
    
    st.session_state.regions = new_regions
    pd.DataFrame(new_regions, columns=['區域名稱']).to_csv(REGION_FILE, index=False)
    st.session_state.tasks.to_csv(SAVE_FILE, index=False)
    st.sidebar.info("區域已更新並同步工作項目")

# ==========================================
# 側邊欄：新增工作項目
# ==========================================
st.sidebar.divider()
st.sidebar.header("➕ 新增工作")
with st.sidebar.form("add_task_form"):
    # 從區域管理器動態獲取清單
    selected_region = st.selectbox("歸屬區域", st.session_state.regions)
    task_name = st.text_input("項目名稱")
    col1, col2 = st.columns(2)
    start_d = col1.date_input("開始")
    end_d = col2.date_input("結束")
    is_m = st.checkbox("里程碑")
    
    if st.form_submit_button("加入清單"):
        if task_name:
            if is_m: end_d = start_d
            new_row = pd.DataFrame([{
                '工作項目': f"★ {task_name}" if is_m else task_name,
                '開始時間': pd.to_datetime(start_d),
                '完成時間': pd.to_datetime(end_d),
                '區域': selected_region,
                '是否為里程碑': is_m
            }])
            st.session_state.tasks = pd.concat([st.session_state.tasks, new_row], ignore_index=True)
            st.session_state.tasks.to_csv(SAVE_FILE, index=False)
            st.success("已新增")

# ==========================================
# 主畫面：甘特圖繪製
# ==========================================
st.subheader("📋 工作清單與圖表")
# 顯示工作清單編輯器
st.session_state.tasks = st.data_editor(st.session_state.tasks, num_rows="dynamic", use_container_width=True)

if st.button("🌟 生成甘特圖", type="primary"):
    df = st.session_state.tasks.copy()
    if not df.empty:
        df['開始時間'] = pd.to_datetime(df['開始時間'])
        df['完成時間'] = pd.to_datetime(df['完成時間'])
        df['天數'] = (df['完成時間'] - df['開始時間']).dt.days
        
        fig, ax = plt.subplots(figsize=(12, len(df)*0.6 + 2))
        plt.title(f"{project_name} - 進度總表", fontsize=16, fontweight='bold')
        sns.set_theme(style='whitegrid')
        sns.set_style({"font.sans-serif":['Microsoft JhengHei', 'PingFang TC', 'Heiti TC']})
        
        # 顏色對映
        unique_regs = df['區域'].unique()
        colors = sns.color_palette("husl", len(unique_regs))
        reg_color_map = dict(zip(unique_regs, colors))

        for y, (idx, row) in enumerate(df.iterrows()):
            c = reg_color_map.get(row['區域'], 'gray')
            if row['是否為里程碑']:
                ax.plot([row["開始時間"]], [y], marker='*', markersize=15, color=c, markeredgecolor='black')
            else:
                ax.barh(y, row['天數'], left=row["開始時間"], height=0.5, color=c, edgecolor="black", alpha=0.8)
            
            # 標註日期文字
            ax.text(row["開始時間"], y, f" {row['工作項目']}", va='center', ha='left', fontsize=9)

        ax.set_yticks(range(len(df)))
        ax.set_yticklabels(df['區域'], fontsize=10) # Y 軸顯示區域，清楚區分
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax.invert_yaxis() # 讓最新輸入的在上面
        st.pyplot(fig)