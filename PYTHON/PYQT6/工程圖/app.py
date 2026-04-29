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
# 2. 資料讀寫邏輯 (確保型態 100% 正確)
# ==========================================
def load_data(table_name="tasks"):
    res = supabase.table(table_name).select("*").execute()
    df = pd.DataFrame(res.data)
    
    if table_name == "tasks":
        cols = ['區域', '施工項目', '施工廠商', '開始時間', '完成時間', '是否為里程碑']
        if not df.empty:
            df = df.rename(columns={
                'task_name': '施工項目', 'start_date': '開始時間',
                'end_date': '完成時間', 'region': '區域',
                'subcontractor': '施工廠商', 'is_milestone': '是否為里程碑'
            })
            df['開始時間'] = pd.to_datetime(df['開始時間']).dt.date
            df['完成時間'] = pd.to_datetime(df['完成時間']).dt.date
            df['是否為里程碑'] = df['是否為里程碑'].fillna(False).astype(bool)
            return df[cols]
        return pd.DataFrame(columns=cols)
    
    else: # 試車資料表邏輯
        cols = ['區域', '試車項目', '開始時間', '完成時間']
        if not df.empty:
            df = df.rename(columns={
                'test_item': '試車項目', 'start_date': '開始時間',
                'end_date': '完成時間', 'region': '區域'
            })
            df['開始時間'] = pd.to_datetime(df['開始時間']).dt.date
            df['完成時間'] = pd.to_datetime(df['完成時間']).dt.date
            return df[cols]
        return pd.DataFrame(columns=cols)

def load_list(table_name):
    res = supabase.table(table_name).select("name").execute()
    return [item['name'] for item in res.data] if res.data else ["未設定"]

def load_project_name():
    try:
        res = supabase.table("project_config").select("project_name").eq("id", 1).execute()
        return res.data[0]['project_name'] if res.data else "新工程案"
    except: return "新工程案"

# ==========================================
# 3. 初始化設定
# ==========================================
st.set_page_config(layout="wide", page_title="營建與試車規劃系統")

if 'tasks' not in st.session_state: st.session_state.tasks = load_data("tasks")
if 'comm_tasks' not in st.session_state: st.session_state.comm_tasks = load_data("commissioning_tasks")
if 'regions' not in st.session_state: st.session_state.regions = load_list("regions")
if 'subcontractors' not in st.session_state: st.session_state.subcontractors = load_list("subcontractors")
if 'project_name' not in st.session_state: st.session_state.project_name = load_project_name()

st.title(f"🏢 {st.session_state.project_name}")

# ==========================================
# 4. 側邊欄管理 (維持原樣)
# ==========================================
st.sidebar.header("⚙️ 基礎資料管理")
with st.sidebar.expander("📍 區域管理"):
    t1, t2 = st.tabs(["➕ 新增", "🗑️ 刪除"])
    with t1:
        nr = st.text_input("新增區域", key="nr_in")
        if st.button("加入區域"):
            if nr and nr not in st.session_state.regions:
                supabase.table("regions").insert({"name": nr}).execute()
                st.session_state.regions.append(nr)
                st.rerun()
    with t2:
        dr = st.selectbox("選擇刪除區域", st.session_state.regions)
        if st.button("刪除區域"):
            if not (st.session_state.tasks['區域'] == dr).any():
                supabase.table("regions").delete().eq("name", dr).execute()
                st.session_state.regions.remove(dr)
                st.rerun()
            else: st.error("尚有任務使用此區域")

# ==========================================
# 6. 主畫面表格 (施工任務清單)
# ==========================================
st.header("🧱 施工任務清單")
col_cfg_task = {
    "區域": st.column_config.SelectboxColumn("區域", options=st.session_state.regions, required=True),
    "施工廠商": st.column_config.SelectboxColumn("施工廠商", options=st.session_state.subcontractors, required=True),
    "開始時間": st.column_config.DateColumn("開始時間", required=True, format="MM/DD"),
    "完成時間": st.column_config.DateColumn("完成時間", required=True, format="MM/DD"),
    "是否為里程碑": st.column_config.CheckboxColumn("里程碑？", default=False)
}
edited_tasks = st.data_editor(st.session_state.tasks, column_config=col_cfg_task, num_rows="dynamic", use_container_width=True, key="tasks_editor")

# 施工存檔邏輯 (含嚴格驗證)
if not edited_tasks.equals(st.session_state.tasks):
    clean_t = edited_tasks.dropna(subset=['施工項目', '開始時間', '完成時間']).copy()
    invalid_t = [i+1 for i, r in clean_t.iterrows() if str(r['區域']) not in st.session_state.regions or str(r['施工廠商']) not in st.session_state.subcontractors]
    if invalid_t:
        st.error(f"施工清單第 {invalid_t} 列名稱不合法")
    elif edited_tasks.empty and not st.session_state.tasks.empty:
        st.warning("防止意外清空，施工自動同步已攔截")
    else:
        try:
            up_t = [{"task_name": str(r['施工項目']), "start_date": r['開始時間'].isoformat(), "end_date": r['完成時間'].isoformat(), "region": str(r['區域']), "subcontractor": str(r['施工廠商']), "is_milestone": bool(r['是否為里程碑'])} for _, r in clean_t.iterrows()]
            supabase.table("tasks").delete().neq("id", -1).execute()
            if up_t: supabase.table("tasks").insert(up_t).execute()
            st.session_state.tasks = edited_tasks
            st.toast("施工清單同步成功")
        except Exception as e: st.error(f"施工同步失敗: {e}")

# ==========================================
# 6.5 主畫面表格 (試車任務清單)
# ==========================================
st.header("🧪 試車任務清單")
col_cfg_comm = {
    "區域": st.column_config.SelectboxColumn("區域", options=st.session_state.regions, required=True),
    "開始時間": st.column_config.DateColumn("開始時間", required=True, format="MM/DD"),
    "完成時間": st.column_config.DateColumn("完成時間", required=True, format="MM/DD"),
}
edited_comm = st.data_editor(st.session_state.comm_tasks, column_config=col_cfg_comm, num_rows="dynamic", use_container_width=True, key="comm_editor")

# 試車存檔邏輯
if not edited_comm.equals(st.session_state.comm_tasks):
    clean_c = edited_comm.dropna(subset=['試車項目', '開始時間', '完成時間']).copy()
    invalid_c = [i+1 for i, r in clean_c.iterrows() if str(r['區域']) not in st.session_state.regions]
    if invalid_c:
        st.error(f"試車清單第 {invalid_c} 列名稱不合法")
    else:
        try:
            up_c = [{"test_item": str(r['試車項目']), "start_date": r['開始時間'].isoformat(), "end_date": r['完成時間'].isoformat(), "region": str(r['區域'])} for _, r in clean_c.iterrows()]
            supabase.table("commissioning_tasks").delete().neq("id", -1).execute()
            if up_c: supabase.table("commissioning_tasks").insert(up_c).execute()
            st.session_state.comm_tasks = edited_comm
            st.toast("試車清單同步成功")
        except Exception as e: st.error(f"試車同步失敗: {e}")

# ==========================================
# 7. 多維度甘特圖生成 (獨立按鍵)
# ==========================================
st.divider()
tab1, tab2 = st.tabs(["📊 生成施工圖表", "⚙️ 生成試車圖表"])

def draw_gantt(df, title, color_col, is_comm=False):
    if df.empty: return st.warning("無數據可繪圖")
    p_df = df.dropna(subset=[df.columns[1], '開始時間', '完成時間']).copy()
    if p_df.empty: return st.warning("請填寫完整的項目與日期")
    
    p_df['開始時間'] = pd.to_datetime(p_df['開始時間'])
    p_df['完成時間'] = pd.to_datetime(p_df['完成時間'])
    p_df['繪圖結束'] = p_df['完成時間'] + pd.Timedelta(days=1)
    p_df = p_df.sort_values("開始時間")
    
    color_map = {v: px.colors.qualitative.Plotly[i % 10] for i, v in enumerate(p_df[color_col].unique())}
    
    # 施工表特有里程碑
    tasks_to_draw = p_df if is_comm else p_df[~p_df['是否為里程碑']]
    
    fig = px.timeline(tasks_to_draw, x_start="開始時間", x_end="繪圖結束", y=p_df.columns[1], color=color_col, color_discrete_map=color_map, height=400+len(p_df)*30)
    
    if not is_comm: # 施工星星
        leg_set = set(tasks_to_draw[color_col].unique())
        for _, m in p_df[p_df['是否為里程碑']].iterrows():
            sl = m[color_col] not in leg_set
            if sl: leg_set.add(m[color_col])
            fig.add_trace(go.Scatter(x=[m['開始時間']], y=[m['施工項目']], mode='markers+text',
                marker=dict(symbol='star', size=18, color=color_map.get(m[color_col], 'gray'), line=dict(color='black', width=1)),
                text=[f" {m['開始時間'].strftime('%m/%d')}"], textposition='middle right', textfont=dict(color='black', size=12),
                name=m[color_col], legendgroup=m[color_col], showlegend=sl))

    fig.update_yaxes(categoryorder='array', categoryarray=p_df[p_df.columns[1]].tolist(), autorange="reversed", showgrid=True, gridcolor='black', tickfont=dict(color="black", size=14))
    fig.update_xaxes(showgrid=True, gridcolor='black', tickformat="%m/%d", dtick="D1", tickfont=dict(color="black", size=12))
    fig.update_layout(plot_bgcolor="#f0f0f0", paper_bgcolor="#f0f0f0", font=dict(color="black"), title=dict(text=title, font=dict(size=22)))
    st.plotly_chart(fig, use_container_width=True)

with tab1:
    target = st.radio("分類維度：", ["區域", "施工廠商"], key="target_const", horizontal=True)
    if st.button("🌟 生成施工甘特圖", type="primary"):
        draw_gantt(edited_tasks, "🏗️ 施工進度總表", target)

with tab2:
    if st.button("🌟 生成試車甘特圖", type="primary"):
        draw_gantt(edited_comm, "🧪 試車進度總表", "區域", is_comm=True)

# ==========================================
# 8. 系統備份與回復 (支援全系統兩表備份)
# ==========================================
st.sidebar.divider()
with st.sidebar.expander("💾 全系統備份與回復"):
    # 本地 CSV 下載
    csv_t = st.session_state.tasks.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下載施工清單 CSV", data=csv_t, file_name="施工備份.csv", use_container_width=True)
    
    csv_c = st.session_state.comm_tasks.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下載試車清單 CSV", data=csv_c, file_name="試車備份.csv", use_container_width=True)

    st.divider()
    bn = st.text_input("備份名稱", key="bn_full")
    if st.button("🚀 建立全系統儲存點", use_container_width=True):
        # 將兩份資料打包在一起
        full_snap = {
            "tasks": st.session_state.tasks.to_json(orient='records', date_format='iso'),
            "comm": st.session_state.comm_tasks.to_json(orient='records', date_format='iso')
        }
        supabase.table("tasks_backups").insert({"backup_name": bn, "data_json": json.dumps(full_snap)}).execute()
        st.toast("全系統備份成功")
        st.rerun()

    res_b = supabase.table("tasks_backups").select("id", "backup_time", "backup_name").order("backup_time", desc=True).execute()
    if res_b.data:
        opts = {f"{i['backup_time'][5:16]} - {i['backup_name']}": i['id'] for i in res_b.data}
        sel_b = st.selectbox("選擇回復點", options=list(opts.keys()))
        c1, c2 = st.columns(2)
        if c1.button("🔥 回復", use_container_width=True):
            snap = supabase.table("tasks_backups").select("data_json").eq("id", opts[sel_b]).execute()
            data = json.loads(snap.data[0]['data_json'])
            
            # 回復施工表
            r_t = pd.read_json(io.StringIO(data['tasks']))
            supabase.table("tasks").delete().neq("id", -1).execute()
            up_t = [{"task_name": r['施工項目'], "start_date": pd.to_datetime(r['開始時間']).isoformat(), "end_date": pd.to_datetime(r['完成時間']).isoformat(), "region": r['區域'], "subcontractor": r['施工廠商'], "is_milestone": bool(r['是否為里程碑'])} for _, r in r_t.iterrows()]
            if up_t: supabase.table("tasks").insert(up_t).execute()
            
            # 回復試車表
            r_c = pd.read_json(io.StringIO(data['comm']))
            supabase.table("commissioning_tasks").delete().neq("id", -1).execute()
            up_c = [{"test_item": r['試車項目'], "start_date": pd.to_datetime(r['開始時間']).isoformat(), "end_date": pd.to_datetime(r['完成時間']).isoformat(), "region": r['區域']} for _, r in r_c.iterrows()]
            if up_c: supabase.table("commissioning_tasks").insert(up_c).execute()
            
            st.session_state.tasks = load_data("tasks")
            st.session_state.comm_tasks = load_data("commissioning_tasks")
            st.rerun()
        if c2.button("🗑️ 刪除", use_container_width=True):
            supabase.table("tasks_backups").delete().eq("id", opts[sel_b]).execute()
            st.rerun()
