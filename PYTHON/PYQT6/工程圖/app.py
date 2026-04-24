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
                '工作項目': str(task_name), 
                '開始時間': pd.to_datetime(start_d),
                '完成時間': pd.to_datetime(end_d),
                '區域': selected_region,
                '是否為里程碑': is_m
            }])
            st.session_state.tasks = pd.concat([st.session_state.tasks, new_row], ignore_index=True)
            st.session_state.tasks.to_csv(SAVE_FILE, index=False)
            st.success("已新增")

# ==========================================
# 主畫面：甘特圖繪製 (顏色一致版)
# ==========================================
st.subheader("📋 工作清單與圖表")

# 1. 捕捉編輯後的表格 (edited_df)
# 加上 key="main_editor" 讓 Streamlit 能夠追蹤狀態
edited_df = st.data_editor(
    st.session_state.tasks, 
    num_rows="dynamic", 
    use_container_width=True,
    key="main_editor"
)

# 2. 【核心修復】比對新舊資料，若有變動則立即存檔
if not edited_df.equals(st.session_state.tasks):
    # 更新記憶體中的資料
    st.session_state.tasks = edited_df
    
    # 強制寫入 CSV 檔案，確保下次開啟時資料還在
    st.session_state.tasks.to_csv(SAVE_FILE, index=False)
    
    # 在畫面右下角彈出一個小提示，確認存檔成功
    st.toast("✅ 偵測到變動，資料已同步至雲端存檔", icon="💾")
st.session_state.tasks = st.data_editor(st.session_state.tasks, num_rows="dynamic", use_container_width=True)

if st.button("🌟 生成互動式甘特圖", type="primary"):
    df = st.session_state.tasks.copy()
    if not df.empty:
        # 資料預處理
        df['開始時間'] = pd.to_datetime(df['開始時間'])
        df['完成時間'] = pd.to_datetime(df['完成時間'])
        df['工作項目'] = df['工作項目'].astype(str) 
        
        unique_regions = df['區域'].unique()
        color_seq = px.colors.qualitative.Plotly 
        region_color_map = {reg: color_seq[i % len(color_seq)] for i, reg in enumerate(unique_regions)}
        
        plot_df = df.copy()
        plot_df['繪圖結束時間'] = plot_df['完成時間'] + pd.Timedelta(days=1)
        
        # 分離資料
        normal_tasks = plot_df[~plot_df['是否為里程碑']]
        milestones = plot_df[plot_df['是否為里程碑']]
        
        # 2. 畫長條圖
        fig = px.timeline(
            normal_tasks, 
            x_start="開始時間", 
            x_end="繪圖結束時間", 
            y="工作項目", 
            color="區域",
            color_discrete_map=region_color_map,
            title=f"{project_name} - 進度總表",
            height=300 + len(df)*35
        )
        
        # 記錄哪些區域已經被長條圖加進圖例了
        regions_with_bars = set(normal_tasks['區域'].unique())
        added_star_legends = set() # 確保純星星的區域只加一次圖例
        
        # 3. 畫里程碑
        if not milestones.empty:
            for _, m in milestones.iterrows():
                reg = m['區域']
                m_color = region_color_map.get(reg, "gray")
                
                # 💡 核心修正：判斷這顆星星是否需要自己建立圖例
                # 條件：該區域沒有長條圖 AND 我們還沒幫該區域的其他星星建過圖例
                needs_legend = (reg not in regions_with_bars) and (reg not in added_star_legends)
                
                if needs_legend:
                    added_star_legends.add(reg)
                
                fig.add_trace(go.Scatter(
                    x=[m['開始時間']],
                    y=[m['工作項目']],
                    mode='markers+text',
                    marker=dict(
                        symbol='star', 
                        size=22, 
                        color=m_color, 
                        line=dict(color='black', width=1.5)
                    ),
                    text=[f" {m['開始時間'].strftime('%m/%d')}"],
                    textposition='middle right',
                    showlegend=needs_legend, 
                    name=reg,                
                    legendgroup=reg          
                ))

        # 4. 強制 Y 軸為文字分類模式，並反轉排序
        fig.update_yaxes(autorange="reversed", type='category')
        fig.update_layout(
            xaxis_title="日期",
            yaxis_title="工作項目 (點擊右側圖例可過濾區域)",
            hovermode="closest",
            # --- 背景顏色修改區 ---
            plot_bgcolor="#d3d3d3",   # 繪圖區背景改為灰色 (LightGrey)
            paper_bgcolor="#d3d3d3",  # 整個圖表外框背景改為灰色
            # --------------------
            xaxis=dict(
                showgrid=True, 
                gridcolor='white',    # 網格線改為白色，在灰色背景上更易閱讀
                tickformat="%m/%d"
            ),
            yaxis=dict(
                showgrid=True, 
                gridcolor='white'     # 網格線改為白色
            ),
            margin=dict(l=20, r=20, t=60, b=20) # 調整邊距讓圖表更緊湊
        )
        
        st.plotly_chart(fig, use_container_width=True)
