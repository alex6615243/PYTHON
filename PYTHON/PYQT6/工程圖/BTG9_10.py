import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import json
from supabase import create_client, Client
import datetime

# ==========================================
# 1. 樣式注入 (利用 ID 兄弟選擇器強行上色)
# ==========================================
st.markdown("""
    <style>
    /* 施工按鈕樣式 (深藍色) */
    div:has(#blue-btn) + div button {
        background-color: #003366 !important;
        color: white !important;
        border: none !important;
        width: 100% !important;
        font-weight: bold !important;
        height: 3em !important;
    }
    div:has(#blue-btn) + div button:hover {
        background-color: #004080 !important;
        color: #FFD700 !important;
    }

    /* 試車按鈕樣式 (深綠色) */
    div:has(#green-btn) + div button {
        background-color: #1B5E20 !important;
        color: white !important;
        border: none !important;
        width: 100% !important;
        font-weight: bold !important;
        height: 3em !important;
    }
    div:has(#green-btn) + div button:hover {
        background-color: #2E7D32 !important;
        color: #CCFF90 !important;
    }

    /* 修正按鈕邊距 */
    .stButton { margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- 按鈕 Helper 函數 ---
def construction_button(label, key):
    st.markdown('<div id="blue-btn"></div>', unsafe_allow_html=True)
    return st.button(label, key=key, use_container_width=True)

def comm_button(label, key):
    st.markdown('<div id="green-btn"></div>', unsafe_allow_html=True)
    return st.button(label, key=key, use_container_width=True)

# ==========================================
# 2. Supabase 初始化與資料處理
# ==========================================
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

def load_data(table_name="tasks"):
    res = supabase.table(table_name).select("*").execute()
    df = pd.DataFrame(res.data)
    if table_name == "tasks":
        cols = ['區域', '施工項目', '施工廠商', '開始時間', '完成時間', '是否為里程碑']
        if not df.empty:
            df = df.rename(columns={'task_name': '施工項目', 'subcontractor': '施工廠商', 'start_date': '開始時間', 'end_date': '完成時間', 'region': '區域', 'is_milestone': '是否為里程碑'})
            for c in cols:
                if c not in df.columns: df[c] = None
            df['開始時間'] = pd.to_datetime(df['開始時間']).dt.date
            df['完成時間'] = pd.to_datetime(df['完成時間']).dt.date
            df['是否為里程碑'] = df['是否為里程碑'].fillna(False).astype(bool)
            return df[cols]
        return pd.DataFrame(columns=cols)
    else:
        cols = ['區域', '試車項目', '開始時間', '完成時間']
        if not df.empty:
            df = df.rename(columns={'test_item': '試車項目', 'start_date': '開始時間', 'end_date': '完成時間', 'region': '區域'})
            for c in cols:
                if c not in df.columns: df[c] = None
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
st.set_page_config(layout="wide", page_title="BTG9/10")
if 'tasks' not in st.session_state: st.session_state.tasks = load_data("tasks")
if 'comm_tasks' not in st.session_state: st.session_state.comm_tasks = load_data("commissioning_tasks")
if 'regions' not in st.session_state: st.session_state.regions = load_list("regions")
if 'subcontractors' not in st.session_state: st.session_state.subcontractors = load_list("subcontractors")
if 'project_name' not in st.session_state: st.session_state.project_name = load_project_name()

st.title(f"🏢 {st.session_state.project_name}")

new_proj_name = st.text_input("📌 專案名稱設定：", value=st.session_state.project_name)
if new_proj_name != st.session_state.project_name:
    try:
        supabase.table("project_config").upsert({"id": 1, "project_name": new_proj_name}).execute()
        st.session_state.project_name = new_proj_name
        st.toast("專案名稱已更新", icon="📝")
        st.rerun()
    except Exception as e: st.error(f"專案名稱更新失敗: {e}")

# ==========================================
# 4. 側邊欄 (區域與廠商管理)
# ==========================================
st.sidebar.header("⚙️ 基礎資料管理")
with st.sidebar.expander("📍 區域與廠商管理"):
    t_reg, t_sub = st.tabs(["📍 區域", "👷 廠商"])
    with t_reg:
        nr = st.text_input("新增區域名稱", key="nr_in")
        if construction_button("加入區域", key="btn_add_reg"):
            if nr and nr not in st.session_state.regions:
                supabase.table("regions").insert({"name": nr}).execute()
                st.session_state.regions.append(nr)
                st.rerun()
        dr = st.selectbox("選擇刪除區域", st.session_state.regions, key="dr_sel")
        if st.button("🗑️ 刪除區域", type="primary", key="btn_del_reg"):
            if not (st.session_state.tasks['區域'] == dr).any() and not (st.session_state.comm_tasks['區域'] == dr).any():
                supabase.table("regions").delete().eq("name", dr).execute()
                st.session_state.regions.remove(dr)
                st.rerun()
            else: st.error("⚠️ 該區域尚有任務使用中")
    with t_sub:
        ns = st.text_input("新增廠商名稱", key="ns_in")
        if construction_button("加入廠商", key="btn_add_sub"):
            if ns and ns not in st.session_state.subcontractors:
                supabase.table("subcontractors").insert({"name": ns}).execute()
                st.session_state.subcontractors.append(ns)
                st.rerun()
        ds = st.selectbox("選擇刪除廠商", st.session_state.subcontractors, key="ds_sel")
        if st.button("🗑️ 刪除廠商", type="primary", key="btn_del_sub"):
            if not (st.session_state.tasks['施工廠商'] == ds).any():
                supabase.table("subcontractors").delete().eq("name", ds).execute()
                st.session_state.subcontractors.remove(ds)
                st.rerun()
            else: st.error("⚠️ 該廠商尚有任務使用中")

# ==========================================
# 5. 施工任務清單
# ==========================================
st.header("🧱 施工任務清單")

col_cfg_task = {
    "區域": st.column_config.SelectboxColumn("區域", options=st.session_state.regions, required=True),
    "施工項目": st.column_config.TextColumn("施工項目", required=True),
    "施工廠商": st.column_config.SelectboxColumn("施工廠商", options=st.session_state.subcontractors, required=True),
    "開始時間": st.column_config.DateColumn("開始時間", format="MM/DD", required=True),
    "完成時間": st.column_config.DateColumn("完成時間", format="MM/DD", required=True),
    "是否為里程碑": st.column_config.CheckboxColumn("里程碑", default=False)
}
edited_tasks = st.data_editor(st.session_state.tasks, column_config=col_cfg_task, num_rows="dynamic", use_container_width=True, key="tasks_editor")

clean_current_t = st.session_state.tasks.dropna(subset=['施工項目', '開始時間', '完成時間']).copy()
clean_edited_t = edited_tasks.dropna(subset=['施工項目', '開始時間', '完成時間']).copy()

if not clean_edited_t.equals(clean_current_t):
    invalid_t = [i+1 for i, r in clean_edited_t.iterrows() if str(r['區域']) not in st.session_state.regions or str(r['施工廠商']) not in st.session_state.subcontractors]
    if not invalid_t:
        try:
            up_t = []
            for _, r in clean_edited_t.iterrows():
                s_t = r['開始時間'].isoformat() if hasattr(r['開始時間'], 'isoformat') else str(r['開始時間'])
                e_t = r['完成時間'].isoformat() if hasattr(r['完成時間'], 'isoformat') else str(r['完成時間'])
                up_t.append({"task_name": str(r['施工項目']), "subcontractor": str(r['施工廠商']), "start_date": s_t, "end_date": e_t, "region": str(r['區域']), "is_milestone": bool(r['是否為里程碑'])})
            
            supabase.table("tasks").delete().neq("id", -1).execute()
            if up_t: supabase.table("tasks").insert(up_t).execute()
            
            st.session_state.tasks = edited_tasks
            st.toast("施工清單已同步", icon="🏗️")
        except Exception as e: st.error(f"施工同步發生錯誤: {e}")
    else: st.error(f"施工清單第 {invalid_t} 列廠商或區域名稱不合法")

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

clean_current_c = st.session_state.comm_tasks.dropna(subset=['試車項目', '開始時間', '完成時間']).copy()
clean_edited_c = edited_comm.dropna(subset=['試車項目', '開始時間', '完成時間']).copy()

if not clean_edited_c.equals(clean_current_c):
    invalid_c = [i+1 for i, r in clean_edited_c.iterrows() if str(r['區域']) not in st.session_state.regions]
    if not invalid_c:
        try:
            up_c = []
            for _, r in clean_edited_c.iterrows():
                s_d = r['開始時間'].isoformat() if hasattr(r['開始時間'], 'isoformat') else str(r['開始時間'])
                e_d = r['完成時間'].isoformat() if hasattr(r['完成時間'], 'isoformat') else str(r['完成時間'])
                up_c.append({"test_item": str(r['試車項目']), "start_date": s_d, "end_date": e_d, "region": str(r['區域'])})
            
            supabase.table("commissioning_tasks").delete().neq("id", -1).execute()
            if up_c: supabase.table("commissioning_tasks").insert(up_c).execute()
            
            st.session_state.comm_tasks = edited_comm
            st.toast("試車清單已同步", icon="🧪")
        except Exception as e: st.error(f"試車同步發生錯誤: {e}")
    else: st.error(f"試車清單第 {invalid_c} 列區域名稱不合法")

# ==========================================
# 7. 圖表生成 (精準對齊刻度版)
# ==========================================
st.divider()
tab_g1, tab_g2 = st.tabs(["📊 施工進度圖表", "⚙️ 試車排程圖表"])

def draw_gantt(df, title, color_col, is_comm=False):
    p_df = df.dropna(subset=[df.columns[1], '開始時間', '完成時間']).copy()
    if p_df.empty: return st.warning("請填寫資料")
    
    p_df['開始時間'] = pd.to_datetime(p_df['開始時間'])
    p_df['完成時間'] = pd.to_datetime(p_df['完成時間'])
    p_df = p_df.sort_values("開始時間")
    
    color_map = {v: px.colors.qualitative.Plotly[i % 10] for i, v in enumerate(p_df[color_col].unique())}
    
    if not is_comm:
        p_df['是否為里程碑'] = p_df['是否為里程碑'].fillna(False).astype(bool)
        draw_df = p_df[~p_df['是否為里程碑']]
        if draw_df.empty: 
            return st.warning("⚠️ 必須至少有一項「非里程碑」的任務才能建立座標軸！")
    else:
        draw_df = p_df
        
    fig = px.timeline(draw_df, x_start="開始時間", x_end="完成時間", y=draw_df.columns[1], color=color_col, color_discrete_map=color_map, height=400+len(p_df)*30)
    
    if not is_comm: 
        leg_set = set(draw_df[color_col].unique())
        for _, m in p_df[p_df['是否為里程碑']].iterrows():
            cat = m[color_col]
            show_leg = cat not in leg_set
            if show_leg: leg_set.add(cat)
            fig.add_trace(go.Scatter(
                x=[m['開始時間']], y=[m[p_df.columns[1]]], mode='markers+text',
                marker=dict(symbol='star', size=18, color=color_map.get(cat, 'gray'), line=dict(color='black', width=1)),
                text=[f" {m['開始時間'].strftime('%m/%d')}"], textposition='middle right', 
                textfont=dict(color='black', size=12),
                name=cat, legendgroup=cat, showlegend=show_leg
            ))

    # 💡 核心修正：利用 normalize() 將時、分、秒歸零，強迫對齊 00:00 刻度線
    try:
        today = pd.Timestamp.now(tz='Asia/Taipei').normalize()
    except:
        today = pd.Timestamp.now().normalize()
        
    fig.add_vline(x=today, line_width=2, line_dash="dash", line_color="red", layer="above")
    fig.add_annotation(x=today, y=1, yref="paper", yanchor="bottom", text="今日", showarrow=False, font=dict(color="red", size=14))

    fig.update_yaxes(categoryorder='array', categoryarray=p_df[p_df.columns[1]].tolist(), autorange="reversed", showgrid=True, gridcolor='black', tickfont=dict(color="black", size=14))
    fig.update_xaxes(showgrid=True, gridcolor='black', tickformat="%m/%d", dtick="D1", tickfont=dict(color="black", size=12))
    fig.update_layout(plot_bgcolor="#f0f0f0", paper_bgcolor="#f0f0f0", font=dict(color="black"), title=dict(text=title, font=dict(size=22)))
    # 統一控制列設定：移除容易產生差異的圈選工具，並隱藏 Plotly Logo
    chart_config = {
        'displaylogo': False,
        'modeBarButtonsToRemove': ['lasso2d', 'select2d'] 
    }
    st.plotly_chart(fig, use_container_width=True, config=chart_config)

with tab_g1:
    v_mode = st.radio("分類維度：", ["區域", "施工廠商"], horizontal=True, key="mode_const")
    if construction_button("🚀 生成施工甘特圖", key="run_g1"): 
        draw_gantt(edited_tasks, f"🧱 {st.session_state.project_name} - 施工進度總表", v_mode)

with tab_g2:
    if comm_button("✅ 生成試車甘特圖", key="run_g2"): 
        draw_gantt(edited_comm, f"🧪 {st.session_state.project_name} - 試車排程總表", "區域", is_comm=True)

# ==========================================
# 8. 系統存檔與回復
# ==========================================
st.sidebar.divider()
with st.sidebar.expander("💾 檔案管理"):
    st.download_button("📥 下載施工 CSV", data=st.session_state.tasks.to_csv(index=False).encode('utf-8-sig'), file_name="tasks.csv", use_container_width=True)
    st.download_button("📥 下載試車 CSV", data=st.session_state.comm_tasks.to_csv(index=False).encode('utf-8-sig'), file_name="comm.csv", use_container_width=True)
    
    st.divider()
    bn = st.text_input("存檔名稱", key="bn_in")
    if construction_button("💾 立即存檔", key="btn_save_snap"):
        snap = {"tasks": st.session_state.tasks.to_json(orient='records', date_format='iso'), "comm": st.session_state.comm_tasks.to_json(orient='records', date_format='iso')}
        supabase.table("tasks_backups").insert({"backup_name": bn if bn else "自動備份", "data_json": json.dumps(snap)}).execute()
        st.toast("已建立雲端存檔")
        st.rerun()

    res_b = supabase.table("tasks_backups").select("id", "backup_time", "backup_name").order("backup_time", desc=True).execute()
    if res_b.data:
        opts = {f"{i['backup_time'][5:16]} - {i['backup_name']}": i['id'] for i in res_b.data}
        sel_b = st.selectbox("選擇檔案回復", options=list(opts.keys()))
        c1, c2 = st.columns(2)
        with c1:
            if st.button("確認回復", use_container_width=True, key="btn_restore"):
                try:
                    snap_res = supabase.table("tasks_backups").select("data_json").eq("id", opts[sel_b]).execute()
                    full_data = json.loads(snap_res.data[0]['data_json'])
                    
                    df_t = pd.read_json(io.StringIO(full_data['tasks']))
                    up_t = [{"task_name": r['施工項目'], "subcontractor": r['施工廠商'], "start_date": pd.to_datetime(r['開始時間']).date().isoformat(), "end_date": pd.to_datetime(r['完成時間']).date().isoformat(), "region": r['區域'], "is_milestone": bool(r['是否為里程碑'])} for _, r in df_t.iterrows()]
                    supabase.table("tasks").delete().neq("id", -1).execute()
                    if up_t: supabase.table("tasks").insert(up_t).execute()
                    
                    df_c = pd.read_json(io.StringIO(full_data['comm']))
                    up_c = [{"test_item": r['試車項目'], "start_date": pd.to_datetime(r['開始時間']).date().isoformat(), "end_date": pd.to_datetime(r['完成時間']).date().isoformat(), "region": r['區域']} for _, r in df_c.iterrows()]
                    supabase.table("commissioning_tasks").delete().neq("id", -1).execute()
                    if up_c: supabase.table("commissioning_tasks").insert(up_c).execute()
                    
                    st.session_state.tasks = load_data("tasks")
                    st.session_state.comm_tasks = load_data("commissioning_tasks")
                    st.rerun()
                except Exception as e: st.error(f"回復失敗: {e}")
        with c2:
            if st.button("刪除存檔", type="primary", use_container_width=True, key="btn_del_snap"):
                supabase.table("tasks_backups").delete().eq("id", opts[sel_b]).execute()
                st.rerun()
