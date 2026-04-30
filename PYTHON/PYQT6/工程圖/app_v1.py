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
# 2. 資料讀寫邏輯
# ==========================================
def load_data(table_name="tasks"):
    res = supabase.table(table_name).select("*").execute()
    df = pd.DataFrame(res.data)
    
    if table_name == "tasks":
        cols = ['區域', '施工項目', '施工廠商', '開始時間', '完成時間', '是否為里程碑']
        if not df.empty:
            df = df.rename(columns={
                'task_name': '施工項目', 'subcontractor': '施工廠商', 
                'start_date': '開始時間', 'end_date': '完成時間', 
                'region': '區域', 'is_milestone': '是否為里程碑'
            })
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
                'test_item': '試車項目', 'start_date': '開始時間',
                'end_date': '完成時間', 'region': '區域'
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
# 3. 初始化設定
# ==========================================
st.set_page_config(layout="wide", page_title="營建與試車規劃系統")

if 'tasks' not in st.session_state: st.session_state.tasks = load_data("tasks")
if 'comm_tasks' not in st.session_state: st.session_state.comm_tasks = load_data("commissioning_tasks")
if 'regions' not in st.session_state: st.session_state.regions = load_list("regions")
if 'subcontractors' not in st.session_state: st.session_state.subcontractors = load_list("subcontractors")

st.title("🏢 營建工程與試車管理系統")

# ==========================================
# 4. 側邊欄管理 (區域與廠商管理 - 完整版)
# ==========================================
st.sidebar.header("⚙️ 基礎資料管理")

# 📍 區域管理
with st.sidebar.expander("📍 區域管理", expanded=False):
    tab_reg_add, tab_reg_del = st.tabs(["➕ 新增", "🗑️ 刪除"])
    
    with tab_reg_add:
        new_reg = st.text_input("新增區域名稱", key="new_reg_input")
        if st.button("加入區域", use_container_width=True):
            if new_reg and new_reg not in st.session_state.regions:
                try:
                    supabase.table("regions").insert({"name": new_reg}).execute()
                    st.session_state.regions.append(new_reg)
                    st.toast(f"✅ 區域「{new_reg}」已新增！", icon="📍")
                    st.rerun()
                except Exception as e: st.error(f"新增失敗: {e}")
            elif new_reg in st.session_state.regions: st.warning("該區域已存在")

    with tab_reg_del:
        del_reg = st.selectbox("選擇要刪除的區域", st.session_state.regions, key="del_reg_sel")
        if st.button("確認刪除區域", type="primary", use_container_width=True):
            # 🛡️ 安全檢查：確認該區域是否正被任何任務使用
            in_construction = (st.session_state.tasks['區域'] == del_reg).any()
            in_commissioning = (st.session_state.comm_tasks['區域'] == del_reg).any()
            
            if in_construction or in_commissioning:
                where = []
                if in_construction: where.append("施工任務")
                if in_commissioning: where.append("試車任務")
                st.error(f"⚠️ 無法刪除！「{del_reg}」目前仍有【{' & '.join(where)}】在使用中。")
            else:
                try:
                    supabase.table("regions").delete().eq("name", del_reg).execute()
                    st.session_state.regions.remove(del_reg)
                    st.toast(f"🗑️ 區域「{del_reg}」已成功移除", icon="✅")
                    st.rerun()
                except Exception as e: st.error(f"刪除失敗: {e}")

# 👷 廠商管理
with st.sidebar.expander("👷 廠商管理", expanded=False):
    tab_sub_add, tab_sub_del = st.tabs(["➕ 新增", "🗑️ 刪除"])
    
    with tab_sub_add:
        new_sub = st.text_input("新增廠商名稱", key="ns_in")
        if st.button("加入廠商", use_container_width=True):
            if new_sub and new_sub not in st.session_state.subcontractors:
                try:
                    supabase.table("subcontractors").insert({"name": new_sub}).execute()
                    st.session_state.subcontractors.append(new_sub)
                    st.toast(f"✅ 廠商「{new_sub}」已新增！", icon="👷")
                    st.rerun()
                except Exception as e: st.error(f"新增失敗: {e}")
            elif new_sub in st.session_state.subcontractors: st.warning("該廠商已存在")

    with tab_sub_del:
        del_sub = st.selectbox("選擇要刪除的廠商", st.session_state.subcontractors, key="del_sub_sel")
        if st.button("確認刪除廠商", type="primary", use_container_width=True):
            # 🛡️ 安全檢查：確認該廠商是否正被施工任務使用
            in_use = (st.session_state.tasks['施工廠商'] == del_sub).any()
            
            if in_use:
                st.error(f"⚠️ 無法刪除！「{del_sub}」目前仍負責施工任務中。請先修改或刪除相關任務。")
            else:
                try:
                    # 從資料庫移除
                    supabase.table("subcontractors").delete().eq("name", del_sub).execute()
                    # 從本地快取移除
                    st.session_state.subcontractors.remove(del_sub)
                    st.toast(f"🗑️ 廠商「{del_sub}」已成功移除", icon="✅")
                    st.rerun()
                except Exception as e: st.error(f"刪除失敗: {e}")
# ==========================================
# 5. 施工任務清單
# ==========================================
st.header("🧱 施工任務清單")
st.session_state.tasks['是否為里程碑'] = st.session_state.tasks['是否為里程碑'].astype(bool)

col_cfg_task = {
    "區域": st.column_config.SelectboxColumn("區域", options=st.session_state.regions, required=True),
    "施工項目": st.column_config.TextColumn("施工項目", required=True),
    "施工廠商": st.column_config.SelectboxColumn("施工廠商", options=st.session_state.subcontractors, required=True),
    "開始時間": st.column_config.DateColumn("開始時間", format="MM/DD", required=True),
    "完成時間": st.column_config.DateColumn("完成時間", format="MM/DD", required=True),
    "是否為里程碑": st.column_config.CheckboxColumn("里程碑", default=False)
}

edited_tasks = st.data_editor(st.session_state.tasks, column_config=col_cfg_task, num_rows="dynamic", use_container_width=True, key="tasks_editor")

if not edited_tasks.equals(st.session_state.tasks):
    clean_t = edited_tasks.dropna(subset=['施工項目', '開始時間', '完成時間']).copy()
    invalid_t = [i+1 for i, r in clean_t.iterrows() if str(r['區域']) not in st.session_state.regions or str(r['施工廠商']) not in st.session_state.subcontractors]
    
    if invalid_t:
        st.error(f"施工清單第 {invalid_t} 列名稱不合法")
    elif edited_tasks.empty and not st.session_state.tasks.empty:
        st.warning("檢測到清空操作，自動同步已攔截")
    else:
        try:
            upload_t = []
            for _, r in clean_t.iterrows():
                upload_t.append({
                    "task_name": str(r['施工項目']), "subcontractor": str(r['施工廠商']), 
                    "start_date": r['開始時間'].isoformat() if hasattr(r['開始時間'], 'isoformat') else str(r['開始時間']), 
                    "end_date": r['完成時間'].isoformat() if hasattr(r['完成時間'], 'isoformat') else str(r['完成時間']), 
                    "region": str(r['區域']), "is_milestone": bool(r['是否為里程碑'])
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
    invalid_c = [i+1 for i, r in clean_c.iterrows() if str(r['區域']) not in st.session_state.regions]
    
    if invalid_c:
        st.error(f"試車清單第 {invalid_c} 列名稱不合法")
    else:
        try:
            upload_c = []
            for _, r in clean_c.iterrows():
                s_d = r['開始時間'].isoformat() if hasattr(r['開始時間'], 'isoformat') else str(r['開始時間'])
                e_d = r['完成時間'].isoformat() if hasattr(r['完成時間'], 'isoformat') else str(r['完成時間'])
                upload_c.append({"test_item": str(r['試車項目']), "start_date": s_d, "end_date": e_d, "region": str(r['區域'])})
            
            supabase.table("commissioning_tasks").delete().neq("id", -1).execute()
            if upload_c: supabase.table("commissioning_tasks").insert(upload_c).execute()
            st.session_state.comm_tasks = edited_comm
            st.toast("試車資料已同步", icon="🧪")
        except Exception as e: st.error(f"試車同步失敗: {e}")

# ==========================================
# 7. 甘特圖生成
# ==========================================
st.divider()
tab_g1, tab_g2 = st.tabs(["📊 施工進度圖表", "⚙️ 試車排程圖表"])

def draw_gantt(df, title, color_col, is_comm=False):
    p_df = df.dropna(subset=[df.columns[1], '開始時間', '完成時間']).copy()
    if p_df.empty: return st.warning("請先填寫資料")
    p_df['開始時間'] = pd.to_datetime(p_df['開始時間'])
    p_df['完成時間'] = pd.to_datetime(p_df['完成時間'])
    p_df['繪圖結束'] = p_df['完成時間'] + pd.Timedelta(days=1)
    p_df = p_df.sort_values("開始時間")
    
    color_map = {v: px.colors.qualitative.Plotly[i % 10] for i, v in enumerate(p_df[color_col].unique())}
    draw_df = p_df[~p_df['是否為里程碑']] if not is_comm else p_df
    
    fig = px.timeline(draw_df, x_start="開始時間", x_end="繪圖結束", y=draw_df.columns[1], color=color_col, color_discrete_map=color_map, height=400+len(p_df)*30)
    
    if not is_comm:
        for _, m in p_df[p_df['是否為里程碑']].iterrows():
            fig.add_trace(go.Scatter(x=[m['開始時間']], y=[m['施工項目']], mode='markers+text',
                marker=dict(symbol='star', size=18, color=color_map.get(m[color_col], 'gray'), line=dict(color='black', width=1)),
                text=[f" {m['開始時間'].strftime('%m/%d')}"], textposition='middle right', textfont=dict(color='black', size=12), showlegend=False))

    fig.update_yaxes(categoryorder='array', categoryarray=p_df[p_df.columns[1]].tolist(), autorange="reversed", showgrid=True, gridcolor='black', tickfont=dict(color="black", size=14))
    fig.update_xaxes(showgrid=True, gridcolor='black', tickformat="%m/%d", dtick="D1", tickfont=dict(color="black", size=12))
    fig.update_layout(plot_bgcolor="#f0f0f0", paper_bgcolor="#f0f0f0", font=dict(color="black"), title=dict(text=title, font=dict(size=22)))
    st.plotly_chart(fig, use_container_width=True)

with tab_g1:
    v_mode = st.radio("分類維度：", ["區域", "施工廠商"], horizontal=True, key="mode_const")
    if st.button("🚀 生成施工甘特圖"): draw_gantt(edited_tasks, "🧱 施工進度總表", v_mode)
with tab_g2:
    if st.button("🚀 生成試車甘特圖"): draw_gantt(edited_comm, "🧪 試車進度總表", "區域", is_comm=True)

# ==========================================
# 8. 備份與回復系統 (全系統修復版)
# ==========================================
st.sidebar.divider()
with st.sidebar.expander("💾 系統數據管理"):
    st.download_button("📥 下載施工 CSV", data=st.session_state.tasks.to_csv(index=False).encode('utf-8-sig'), file_name="tasks.csv", use_container_width=True)
    st.download_button("📥 下載試車 CSV", data=st.session_state.comm_tasks.to_csv(index=False).encode('utf-8-sig'), file_name="comm.csv", use_container_width=True)
    
    st.divider()
    bn = st.text_input("檔案名稱", key="bn_in")
    if st.button("存檔"):
        snap = {
            "tasks": st.session_state.tasks.to_json(orient='records', date_format='iso'),
            "comm": st.session_state.comm_tasks.to_json(orient='records', date_format='iso')
        }
        supabase.table("tasks_backups").insert({"backup_name": bn if bn else "自動備份", "data_json": json.dumps(snap)}).execute()
        st.toast("已存檔")
        st.rerun()

    res_b = supabase.table("tasks_backups").select("id", "backup_time", "backup_name").order("backup_time", desc=True).execute()
    if res_b.data:
        opts = {f"{i['backup_time'][5:16]} - {i['backup_name']}": i['id'] for i in res_b.data}
        sel_b = st.selectbox("選擇檔案回復", options=list(opts.keys()))
        c1, c2 = st.columns(2)
        if c1.button("確認回復", use_container_width=True):
            try:
                snap_res = supabase.table("tasks_backups").select("data_json").eq("id", opts[sel_b]).execute()
                full_data = json.loads(snap_res.data[0]['data_json'])
                
                # 1. 處理施工表回復
                r_t = pd.read_json(io.StringIO(full_data['tasks']))
                up_t = []
                for _, r in r_t.iterrows():
                    up_t.append({
                        "task_name": str(r['施工項目']), "subcontractor": str(r['施工廠商']), 
                        "start_date": pd.to_datetime(r['開始時間']).date().isoformat(), 
                        "end_date": pd.to_datetime(r['完成時間']).date().isoformat(), 
                        "region": str(r['區域']), "is_milestone": bool(r['是否為里程碑'])
                    })
                supabase.table("tasks").delete().neq("id", -1).execute()
                if up_t: supabase.table("tasks").insert(up_t).execute()
                
                # 2. 處理試車表回復
                r_c = pd.read_json(io.StringIO(full_data['comm']))
                up_c = []
                for _, r in r_c.iterrows():
                    up_c.append({
                        "test_item": str(r['試車項目']), 
                        "start_date": pd.to_datetime(r['開始時間']).date().isoformat(), 
                        "end_date": pd.to_datetime(r['完成時間']).date().isoformat(), 
                        "region": str(r['區域'])
                    })
                supabase.table("commissioning_tasks").delete().neq("id", -1).execute()
                if up_c: supabase.table("commissioning_tasks").insert(up_c).execute()
                
                # 重新載入數據
                st.session_state.tasks = load_data("tasks")
                st.session_state.comm_tasks = load_data("commissioning_tasks")
                st.toast("檔案已回復", icon="🔄")
                st.rerun()
            except Exception as e: st.error(f"回復失敗: {e}")

        if c2.button("刪除存檔", use_container_width=True):
            supabase.table("tasks_backups").delete().eq("id", opts[sel_b]).execute()
            st.rerun()
