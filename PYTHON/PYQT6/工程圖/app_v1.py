import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import json
from supabase import create_client, Client
import datetime

# ==========================================
# 1. Supabase 初始化連接
# ==========================================
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# ==========================================
# 2. 資料讀寫邏輯 (關鍵修正：欄位映射對齊)
# ==========================================
def load_data(table_name="tasks"):
    res = supabase.table(table_name).select("*").execute()
    df = pd.DataFrame(res.data)
    
    if table_name == "tasks":
        # 🛡️ 確保施工表必備欄位 (防止資料庫回傳時缺項)
        cols = ['區域', '施工項目', '施工廠商', '開始時間', '完成時間', '是否為里程碑']
        if not df.empty:
            # 💡 這裡將 DB 欄位正確映射到中文介面
            df = df.rename(columns={
                'task_name': '施工項目', 
                'subcontractor': '施工廠商', 
                'start_date': '開始時間',
                'end_date': '完成時間', 
                'region': '區域',
                'is_milestone': '是否為里程碑'
            })
            # 🛡️ 防呆：如果資料庫完全沒資料，手動補齊缺失欄位
            for c in cols:
                if c not in df.columns: df[c] = None
            
            df['開始時間'] = pd.to_datetime(df['開始時間']).dt.date
            df['完成時間'] = pd.to_datetime(df['完成時間']).dt.date
            df['是否為里程碑'] = df['是否為里程碑'].fillna(False).astype(bool)
            return df[cols]
        return pd.DataFrame(columns=cols)
    
    else: # 試車資料表
        cols = ['區域', '試車項目', '開始時間', '完成時間']
        if not df.empty:
            df = df.rename(columns={
                'test_item': '試車項目', 
                'start_date': '開始時間',
                'end_date': '完成時間', 
                'region': '區域'
            })
            for c in cols:
                if c not in df.columns: df[c] = None
            df['開始時間'] = pd.to_datetime(df['開始時間']).dt.date
            df['完成時間'] = pd.to_datetime(df['完成時間']).dt.date
            return df[cols]
        return pd.DataFrame(columns=cols)

def load_list(table_name):
    res = supabase.table(table_name).select("name").execute()
    return [item['name'] for item in res.data] if res.data else ["未設定"]

# ==========================================
# 3. 初始化與 UI 設置
# ==========================================
st.set_page_config(layout="wide", page_title="營建與試車規劃系統")

if 'tasks' not in st.session_state: st.session_state.tasks = load_data("tasks")
if 'comm_tasks' not in st.session_state: st.session_state.comm_tasks = load_data("commissioning_tasks")
if 'regions' not in st.session_state: st.session_state.regions = load_list("regions")
if 'subcontractors' not in st.session_state: st.session_state.subcontractors = load_list("subcontractors")

st.title("🏢 營建工程與試車管理系統")

# ==========================================
# 4. 側邊欄基礎資料管理 (區域、廠商)
# ==========================================
st.sidebar.header("⚙️ 基礎資料管理")
with st.sidebar.expander("📍 區域與廠商管理"):
    t_reg, t_sub = st.tabs(["📍 區域", "👷 廠商"])
    with t_reg:
        nr = st.text_input("新增區域", key="new_reg")
        if st.button("加入區域"):
            if nr and nr not in st.session_state.regions:
                supabase.table("regions").insert({"name": nr}).execute()
                st.session_state.regions.append(nr)
                st.rerun()
    with t_sub:
        ns = st.text_input("新增廠商", key="new_sub")
        if st.button("加入廠商"):
            if ns and ns not in st.session_state.subcontractors:
                supabase.table("subcontractors").insert({"name": ns}).execute()
                st.session_state.subcontractors.append(ns)
                st.rerun()

# ==========================================
# 5. 施工任務清單 (核心修正區)
# ==========================================
st.header("🧱 施工任務清單")

# 🛡️ 確保在渲染前強制校正型態
st.session_state.tasks['是否為里程碑'] = st.session_state.tasks['是否為里程碑'].astype(bool)

col_cfg_task = {
    "區域": st.column_config.SelectboxColumn("區域", options=st.session_state.regions, required=True),
    "施工項目": st.column_config.TextColumn("施工項目", required=True),
    "施工廠商": st.column_config.SelectboxColumn("施工廠商", options=st.session_state.subcontractors, required=True),
    "開始時間": st.column_config.DateColumn("開始時間", format="MM/DD", required=True),
    "完成時間": st.column_config.DateColumn("完成時間", format="MM/DD", required=True),
    "是否為里程碑": st.column_config.CheckboxColumn("里程碑", default=False)
}

edited_tasks = st.data_editor(
    st.session_state.tasks, 
    column_config=col_cfg_task, 
    num_rows="dynamic", 
    use_container_width=True, 
    key="tasks_editor"
)

# 施工同步邏輯
if not edited_tasks.equals(st.session_state.tasks):
    clean_t = edited_tasks.dropna(subset=['施工項目', '開始時間', '完成時間']).copy()
    invalid_t = [i+1 for i, r in clean_t.iterrows() if str(r['區域']) not in st.session_state.regions or str(r['施工廠商']) not in st.session_state.subcontractors]
    
    if invalid_t:
        st.error(f"施工清單第 {invalid_t} 列名稱不合法 (請使用選單項目)")
    elif edited_tasks.empty and not st.session_state.tasks.empty:
        st.warning("檢測到大量刪除，自動同步已攔截")
    else:
        try:
            upload_t = []
            for _, r in clean_t.iterrows():
                upload_t.append({
                    "task_name": str(r['施工項目']), 
                    "subcontractor": str(r['施工廠商']), # 👈 確保寫回 DB 的是 subcontractor
                    "start_date": r['開始時間'].isoformat(), 
                    "end_date": r['完成時間'].isoformat(), 
                    "region": str(r['區域']), 
                    "is_milestone": bool(r['是否為里程碑'])
                })
            supabase.table("tasks").delete().neq("id", -1).execute()
            if upload_t: supabase.table("tasks").insert(upload_t).execute()
            st.session_state.tasks = edited_tasks
            st.toast("施工資料已同步", icon="🏗️")
        except Exception as e: st.error(f"施工同步失敗: {e}")

# ==========================================
# 6. 試車任務清單
# ==========================================
st.header("🧪 試車任務清單")
col_cfg_comm = {
    "區域": st.column_config.SelectboxColumn("區域", options=st.session_state.regions, required=True),
    "試車項目": st.column_config.TextColumn("試車項目", required=True),
    "開始時間": st.column_config.DateColumn("開始時間", format="MM/DD", required=True),
    "完成時間": st.column_config.DateColumn("完成時間", format="MM/DD", required=True),
}
edited_comm = st.data_editor(st.session_state.comm_tasks, column_config=col_cfg_comm, num_rows="dynamic", use_container_width=True, key="comm_editor")

if not edited_comm.equals(st.session_state.comm_tasks):
    clean_c = edited_comm.dropna(subset=['試車項目', '開始時間', '完成時間']).copy()
    if not clean_c.empty:
        try:
            upload_c = [{"test_item": str(r['試車項目']), "start_date": r['開始時間'].isoformat(), "end_date": r['完成時間'].isoformat(), "region": str(r['區域'])} for _, r in clean_c.iterrows()]
            supabase.table("commissioning_tasks").delete().neq("id", -1).execute()
            supabase.table("commissioning_tasks").insert(upload_c).execute()
            st.session_state.comm_tasks = edited_comm
            st.toast("試車資料已同步", icon="🧪")
        except Exception as e: st.error(f"試車同步失敗: {e}")

# ==========================================
# 7. 獨立甘特圖生成區
# ==========================================
st.divider()
tab_g1, tab_g2 = st.tabs(["📊 施工進度圖表", "⚙️ 試車排程圖表"])

def draw_gantt(df, title, color_col, is_comm=False):
    p_df = df.dropna(subset=[df.columns[1], '開始時間', '完成時間']).copy()
    if p_df.empty: return st.warning("請先填寫資料再生成圖表")
    
    p_df['開始時間'] = pd.to_datetime(p_df['開始時間'])
    p_df['完成時間'] = pd.to_datetime(p_df['完成時間'])
    p_df['繪圖結束'] = p_df['完成時間'] + pd.Timedelta(days=1)
    p_df = p_df.sort_values("開始時間")
    
    color_map = {v: px.colors.qualitative.Plotly[i % 10] for i, v in enumerate(p_df[color_col].unique())}
    
    # 過濾里程碑 (施工圖專用)
    draw_df = p_df[~p_df['是否為里程碑']] if not is_comm else p_df
    
    fig = px.timeline(draw_df, x_start="開始時間", x_end="繪圖結束", y=draw_df.columns[1], color=color_col, color_discrete_map=color_map, height=400+len(p_df)*30)
    
    # 畫里程碑星星
    if not is_comm:
        for _, m in p_df[p_df['是否為里程碑']].iterrows():
            fig.add_trace(go.Scatter(x=[m['開始時間']], y=[m['施工項目']], mode='markers+text',
                                     marker=dict(symbol='star', size=18, color=color_map.get(m[color_col], 'gray'), line=dict(color='black', width=1)),
                                     text=[f" {m['開始時間'].strftime('%m/%d')}"], textposition='middle right',
                                     textfont=dict(color='black', size=12), showlegend=False))

    fig.update_yaxes(categoryorder='array', categoryarray=p_df[p_df.columns[1]].tolist(), autorange="reversed", showgrid=True, gridcolor='black', tickfont=dict(color="black", size=14))
    fig.update_xaxes(showgrid=True, gridcolor='black', tickformat="%m/%d", dtick="D1", tickfont=dict(color="black", size=12))
    fig.update_layout(plot_bgcolor="#f0f0f0", paper_bgcolor="#f0f0f0", font=dict(color="black"), title=dict(text=title, font=dict(size=22)))
    st.plotly_chart(fig, use_container_width=True)

with tab_g1:
    v_mode = st.radio("分類維度：", ["區域", "施工廠商"], horizontal=True, key="mode_const")
    if st.button("🚀 生成施工甘特圖"):
        draw_gantt(edited_tasks, "🧱 施工進度總表", v_mode)

with tab_g2:
    if st.button("🚀 生成試車甘特圖"):
        draw_gantt(edited_comm, "🧪 試車進度總表", "區域", is_comm=True)

# ==========================================
# 8. 備份與回復系統
# ==========================================
st.sidebar.divider()
with st.sidebar.expander("💾 系統數據管理"):
    st.download_button("📥 下載施工 CSV", data=st.session_state.tasks.to_csv(index=False).encode('utf-8-sig'), file_name="tasks.csv", use_container_width=True)
    st.download_button("📥 下載試車 CSV", data=st.session_state.comm_tasks.to_csv(index=False).encode('utf-8-sig'), file_name="comm.csv", use_container_width=True)
    
    st.divider()
    bn = st.text_input("快照備份名稱")
    if st.button("🚀 建立雲端全系統快照"):
        snap = {
            "tasks": st.session_state.tasks.to_json(orient='records', date_format='iso'),
            "comm": st.session_state.comm_tasks.to_json(orient='records', date_format='iso')
        }
        supabase.table("tasks_backups").insert({"backup_name": bn if bn else "自動備份", "data_json": json.dumps(snap)}).execute()
        st.toast("快照已建立")
        st.rerun()

    res_b = supabase.table("tasks_backups").select("id", "backup_time", "backup_name").order("backup_time", desc=True).execute()
    if res_b.data:
        opts = {f"{i['backup_time'][5:16]} - {i['backup_name']}": i['id'] for i in res_b.data}
        sel_b = st.selectbox("選擇回復儲存點", options=list(opts.keys()))
        c1, c2 = st.columns(2)
        if c1.button("🔥 確認回復", use_container_width=True):
            snap_res = supabase.table("tasks_backups").select("data_json").eq("id", opts[sel_b]).execute()
            data = json.loads(snap_res.data[0]['data_json'])
            
            # 回復施工
            df_t = pd.read_json(io.StringIO(data['tasks']))
            supabase.table("tasks").delete().neq("id", -1).execute()
            up_t = [{"task_name": r['施工項目'], "subcontractor": r['施工廠商'], "start_date": pd.to_datetime(r['開始時間']).isoformat(), "end_date": pd.to_datetime(r['完成時間']).isoformat(), "region": r['區域'], "is_milestone": bool(r['是否為里程碑'])} for _, r in df_t.iterrows()]
            if up_t: supabase.table("tasks").insert(up_t).execute()
            
            # 回復試車
            df_c = pd.read_json(io.StringIO(data['comm']))
            supabase.table("commissioning_tasks").delete().neq("id", -1).execute()
            up_c = [{"test_item": r['試車項目'], "start_date": pd.to_datetime(r['開始時間']).isoformat(), "end_date": pd.to_datetime(r['完成時間']).isoformat(), "region": r['區域']} for _, r in df_c.iterrows()]
            if up_c: supabase.table("commissioning_tasks").insert(upload_list=up_c).execute()
            
            st.toast("數據已回復")
            st.rerun()
        if c2.button("🗑️ 刪除", use_container_width=True):
            supabase.table("tasks_backups").delete().eq("id", opts[sel_b]).execute()
            st.rerun()
