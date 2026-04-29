import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client

# ==========================================
# 1. Supabase 初始化連接 (這裡定義了 supabase，絕對不能漏掉！)
# ==========================================
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# 這裡把連線物件命名為 supabase，後面的程式才能呼叫它
supabase = init_connection()

# ==========================================
# 2. 資料讀寫邏輯
# ==========================================
def load_data():
    res = supabase.table("tasks").select("*").execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df = df.rename(columns={
            'task_name': '工作項目',
            'start_date': '開始時間',
            'end_date': '完成時間',
            'region': '區域',
            'is_milestone': '是否為里程碑'
        })
        df['開始時間'] = pd.to_datetime(df['開始時間'])
        df['完成時間'] = pd.to_datetime(df['完成時間'])
        return df[['工作項目', '開始時間', '完成時間', '區域', '是否為里程碑']]
    return pd.DataFrame(columns=['工作項目', '開始時間', '完成時間', '區域', '是否為里程碑'])

def load_regions():
    res = supabase.table("regions").select("name").execute()
    return [item['name'] for item in res.data] if res.data else ["主區域"]

def load_project_name():
    res = supabase.table("project_config").select("project_name").eq("id", 1).execute()
    return res.data[0]['project_name'] if res.data else "未命名工程案"

# ==========================================
# 3. 初始化設定與網頁標題
# ==========================================
st.set_page_config(layout="wide", page_title="多區域工程規劃系統")

if 'tasks' not in st.session_state:
    st.session_state.tasks = load_data()
if 'regions' not in st.session_state:
    st.session_state.regions = load_regions()
if 'project_name' not in st.session_state:
    st.session_state.project_name = load_project_name()

st.title("營建工程進度規劃系統")

current_name = st.text_input("📌 工程案名稱：", value=st.session_state.project_name)
if current_name != st.session_state.project_name:
    supabase.table("project_config").upsert({'id': 1, 'project_name': current_name}).execute()
    st.session_state.project_name = current_name
    st.toast("✅ 工程名稱已同步", icon="🏗️")

# ==========================================
# 4. 區域管理 (Sidebar)
# ==========================================
st.sidebar.header("⚙️ 區域管理")
new_region = st.sidebar.text_input("新增區域名稱：")
if st.sidebar.button("➕ 新增區域"):
    if new_region and new_region not in st.session_state.regions:
        supabase.table("regions").insert({"name": new_region}).execute()
        st.session_state.regions.append(new_region)
        st.sidebar.success(f"已新增：{new_region}")
        st.rerun()

region_df = pd.DataFrame(st.session_state.regions, columns=['區域名稱'])
st.sidebar.data_editor(region_df, use_container_width=True, disabled=True)

# ==========================================
# 5. 新增工作項目 (Sidebar)
# ==========================================
st.sidebar.divider()
st.sidebar.header("➕ 新增工作")
with st.sidebar.form("add_task_form"):
    sel_reg = st.selectbox("歸屬區域", st.session_state.regions)
    t_name = st.text_input("項目名稱")
    c1, c2 = st.columns(2)
    s_d = c1.date_input("開始")
    e_d = c2.date_input("結束")
    is_m = st.checkbox("里程碑")
    
    if st.form_submit_button("加入清單"):
        if t_name:
            if is_m: e_d = s_d
            new_task = {
                "task_name": t_name,
                "start_date": s_d.isoformat(),
                "end_date": e_d.isoformat(),
                "region": sel_reg,
                "is_milestone": is_m
            }
            supabase.table("tasks").insert(new_task).execute()
            st.session_state.tasks = load_data()
            st.success("已新增至資料庫")
            st.rerun()

# ==========================================
# 6. 主畫面：工作清單與自動存檔 (含防呆除錯)
# ==========================================
st.subheader("📋 工作清單")
edited_df = st.data_editor(
    st.session_state.tasks, 
    num_rows="dynamic", 
    use_container_width=True,
    key="db_editor"
)

if not edited_df.equals(st.session_state.tasks):
    try:
        res_del = supabase.table("tasks").delete().neq("id", -1).execute()
        
        upload_list = []
        for _, row in edited_df.iterrows():
            upload_list.append({
                "task_name": str(row['工作項目']),
                "start_date": row['開始時間'].isoformat(),
                "end_date": row['完成時間'].isoformat(),
                "region": row['區域'],
                "is_milestone": bool(row['是否為里程碑'])
            })
        
        if upload_list:
            res_ins = supabase.table("tasks").insert(upload_list).execute()
            
        st.session_state.tasks = edited_df
        st.toast("💾 資料庫同步成功", icon="☁️")
        
    except Exception as e:
        st.error(f"❌ 同步失敗！錯誤訊息：{str(e)}")
        st.info("提示：這通常是 Supabase 的 RLS 權限阻擋，請到 Supabase 後台關閉 RLS 或設定 Insert/Delete Policy。")

# ==========================================
# 7. 繪製甘特圖 (修復 Plotly 時間戳記 Bug 版)
# ==========================================
if st.button("🌟 生成互動式甘特圖", type="primary"):
    df = st.session_state.tasks.copy()
    if not df.empty:
        plot_df = df.copy()
        # 確保長條圖涵蓋完整結束日
        plot_df['繪圖結束'] = plot_df['完成時間'] + pd.Timedelta(days=1)
        
        unique_regions = df['區域'].unique()
        color_seq = px.colors.qualitative.Plotly
        color_map = {reg: color_seq[i % len(color_seq)] for i, reg in enumerate(unique_regions)}

        fig = px.timeline(
            plot_df[~plot_df['是否為里程碑']], 
            x_start="開始時間", 
            x_end="繪圖結束", 
            y="工作項目", 
            color="區域",
            color_discrete_map=color_map,
            title=f"{st.session_state.project_name} - 進度總表",
            height=400 + len(df)*30
        )

        # 處理里程碑星號
        ms_df = plot_df[plot_df['是否為里程碑']]
        for _, m in ms_df.iterrows():
            fig.add_trace(go.Scatter(
                x=[m['開始時間']], 
                y=[m['工作項目']], 
                mode='markers+text',
                marker=dict(
                    symbol='star', size=20, 
                    color=color_map.get(m['區域'], 'gray'), 
                    line=dict(color='black', width=1)
                ),
                text=[f" {m['開始時間'].strftime('%m/%d')}"], 
                textposition='middle right', 
                name=m['區域'], 
                legendgroup=m['區域'], 
                showlegend=False
            ))

        # 取得今天日期
        try:
            today = pd.Timestamp.now(tz='Asia/Taipei')
        except:
            today = pd.Timestamp.now()

        # 💡 解法核心：將畫線與文字分開，避開 Plotly 底層 Bug
        # 1. 單純畫紅色虛線
        fig.add_vline(
            x=today, 
            line_width=2, 
            line_dash="dash", 
            line_color="red",
            layer="above"
        )
        
        # 2. 獨立加上「今日」文字註解
        fig.add_annotation(
            x=today,
            y=1,               # 定位在 Y 軸最頂端
            yref="paper",      # 鎖定圖表外框比例，不會受任務數量影響
            yanchor="bottom",  # 文字的底部貼齊頂端
            text="今日",
            showarrow=False,
            font=dict(color="red", size=14),
            xanchor="left",    # 文字靠線的右邊
            xshift=5           # 稍微往右平移 5px 避免壓到線
        )

        # 設定格線與日期格式 (改為黑色格線與黑色文字)
        fig.update_yaxes(autorange="reversed", type='category')
        fig.update_layout(
            font=dict(color="black"), # 💡 新增：將圖表內所有文字（X軸、Y軸、標籤）統一改為黑色
            xaxis_title="日期",
            yaxis_title="工作項目",
            hovermode="closest",
            plot_bgcolor="#d3d3d3",   # 保持灰色背景
            paper_bgcolor="#d3d3d3",  # 保持灰色背景
            xaxis=dict(
                showgrid=True, 
                gridcolor='black',    # 💡 修改：X 軸垂直格線改為黑色
                tickformat="%m/%d",   
                dtick="D1"            
            ),
            yaxis=dict(
                showgrid=True, 
                gridcolor='black'     # 💡 修改：Y 軸水平格線改為黑色
            ),
            margin=dict(l=20, r=20, t=60, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)
