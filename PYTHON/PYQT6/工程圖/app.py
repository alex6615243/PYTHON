import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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

st.sidebar.write("編輯區域名稱 (直接在下方表格修改)：")
region_df = pd.DataFrame(st.session_state.regions, columns=['區域名稱'])
edited_region_df = st.sidebar.data_editor(region_df, num_rows="dynamic", use_container_width=True)

if not edited_region_df.equals(region_df):
    old_regions = region_df['區域名稱'].tolist()
    new_regions = edited_region_df['區域名稱'].tolist()
    
    for old, new in zip(old_regions, new_regions):
        if old != new:
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
                '工作項目': f"{task_name}", # 移除星號前綴，交給繪圖處理
                '開始時間': pd.to_datetime(start_d),
                '完成時間': pd.to_datetime(end_d),
                '區域': selected_region,
                '是否為里程碑': is_m
            }])
            st.session_state.tasks = pd.concat([st.session_state.tasks, new_row], ignore_index=True)
            st.session_state.tasks.to_csv(SAVE_FILE, index=False)
            st.success("已新增")

# ==========================================
# 主畫面：甘特圖繪製 (Plotly 升級版)
# ==========================================
st.subheader("📋 工作清單與圖表")
st.session_state.tasks = st.data_editor(st.session_state.tasks, num_rows="dynamic", use_container_width=True)

if st.button("🌟 生成互動式甘特圖", type="primary"):
    df = st.session_state.tasks.copy()
    if not df.empty:
        # 確保時間格式正確
        df['開始時間'] = pd.to_datetime(df['開始時間'])
        df['完成時間'] = pd.to_datetime(df['完成時間'])

        df['工作項目'] = df['工作項目'].astype(str)
        
        # 為了讓 Plotly 的長條圖能夠包容最後一天，我們在繪圖專用的 DataFrame 中把完成日 +1 天
        plot_df = df.copy()
        plot_df['繪圖結束時間'] = plot_df['完成時間'] + pd.Timedelta(days=1)
        
        # 建立甘特圖底圖 (自動用區域進行顏色分類)
        fig = px.timeline(
            plot_df[~plot_df['是否為里程碑']], # 先畫不是里程碑的常規任務
            x_start="開始時間", 
            x_end="繪圖結束時間", 
            y="工作項目", 
            color="區域",
            title=f"{project_name} - 進度總表",
            height=300 + len(df)*30 # 自動根據任務數量調整高度
        )
        
        # 針對里程碑添加星星圖示
        milestones = plot_df[plot_df['是否為里程碑']]
        if not milestones.empty:
            for _, m in milestones.iterrows():
                fig.add_trace(go.Scatter(
                    x=[m['開始時間']],
                    y=[m['工作項目']],
                    mode='markers+text',
                    marker=dict(symbol='star', size=20, line=dict(color='black', width=1)),
                    text=[f"{m['開始時間'].strftime('%m/%d')} (里程碑)"],
                    textposition='middle right',
                    showlegend=False,
                    name=m['區域']
                ))

        # 反轉 Y 軸讓最新的資料在上面，並優化版面
        fig.update_yaxes(autorange="reversed" , type='category')
        fig.update_layout(
            xaxis_title="日期",
            yaxis_title="工作項目",
            hovermode="closest",
            plot_bgcolor="white",
            xaxis=dict(showgrid=True, gridcolor='lightgray', tickformat="%Y-%m-%d"),
            yaxis=dict(showgrid=True, gridcolor='lightgray')
        )
        
        # 輸出到 Streamlit 網頁上
        st.plotly_chart(fig, use_container_width=True)
