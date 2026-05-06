import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import json
from supabase import create_client, Client
import datetime

# ==========================================
# 1. 樣式注入
# ==========================================
st.markdown("""
    <style>
    div:has(#blue-btn) + div button { background-color: #003366 !important; color: white !important; border: none !important; width: 100% !important; font-weight: bold !important; height: 3em !important; }
    div:has(#blue-btn) + div button:hover { background-color: #004080 !important; color: #FFD700 !important; }
    div:has(#green-btn) + div button { background-color: #1B5E20 !important; color: white !important; border: none !important; width: 100% !important; font-weight: bold !important; height: 3em !important; }
    div:has(#green-btn) + div button:hover { background-color: #2E7D32 !important; color: #CCFF90 !important; }
    .stButton { margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

def construction_button(label, key):
    st.markdown('<div id="blue-btn"></div>', unsafe_allow_html=True)
    return st.button(label, key=key, use_container_width=True)

def comm_button(label, key):
    st.markdown('<div id="green-btn"></div>', unsafe_allow_html=True)
    return st.button(label, key=key, use_container_width=True)

def safe_date(d):
    if pd.isna(d) or d == "" or d is None: return None
    return d.isoformat() if hasattr(d, 'isoformat') else str(d)

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
        cols = ['區域', '施工項目', '施工廠商', '預定開始', '預定完成', '實際開始', '實際完成', '完成度(%)', '是否為里程碑']
        if not df.empty:
            df = df.rename(columns={'task_name': '施工項目', 'subcontractor': '施工廠商', 'start_date': '預定開始', 'end_date': '預定完成', 'region': '區域', 'is_milestone': '是否為里程碑', 'actual_start': '實際開始', 'actual_end': '實際完成', 'completion': '完成度(%)'})
            for c in cols:
                if c not in df.columns: df[c] = 0 if c == '完成度(%)' else None
            for d in ['預定開始', '預定完成', '實際開始', '實際完成']:
                df[d] = pd.to_datetime(df[d]).dt.date
            df['是否為里程碑'] = df['是否為里程碑'].fillna(False).astype(bool)
            df['完成度(%)'] = df['完成度(%)'].fillna(0).astype(int)
            return df[cols]
        return pd.DataFrame(columns=cols)
    else: # 💡 試車任務現在也支援里程碑了
        cols = ['區域', '試車項目', '預定開始', '預定完成', '實際開始', '實際完成', '完成度(%)', '是否為里程碑']
        if not df.empty:
            df = df.rename(columns={'test_item': '試車項目', 'start_date': '預定開始', 'end_date': '預定完成', 'region': '區域', 'actual_start': '實際開始', 'actual_end': '實際完成', 'completion': '完成度(%)', 'is_milestone': '是否為里程碑'})
            for c in cols:
                if c not in df.columns: df[c] = 0 if c == '完成度(%)' else None
            for d in ['預定開始', '預定完成', '實際開始', '實際完成']:
                df[d] = pd.to_datetime(df[d]).dt.date
            df['是否為里程碑'] = df['是否為里程碑'].fillna(False).astype(bool)
            df['完成度(%)'] = df['完成度(%)'].fillna(0).astype(int)
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
st.set_page_config(layout="wide", page_title="營建與試車管理系統")
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
                # 1. 確保日期欄位是正宗的 datetime.date 物件 (解決 DateColumn 報錯)
date_cols = ['預定開始', '預定完成', '實際開始', '實際完成'] # 請換成你實際的日期欄位名稱
for col in date_cols:
    if col in current_tasks.columns:
        current_tasks[col] = pd.to_datetime(current_tasks[col], errors='coerce').dt.date

# 2. 確保 Checkbox 欄位是嚴格的 Boolean (解決 CheckboxColumn 報錯)
if '是否為里程碑' in current_tasks.columns:
    current_tasks['是否為里程碑'] = current_tasks['是否為里程碑'].fillna(False).astype(bool)

# 3. 確保數字欄位是整數或浮點數 (解決 NumberColumn 報錯)
if '完成度(%)' in current_tasks.columns:
    current_tasks['完成度(%)'] = pd.to_numeric(current_tasks['完成度(%)'], errors='coerce').fillna(0).astype(int)

# --- 轉換完成後，再丟給 data_editor ---
edited_tasks = st.data_editor(current_tasks, column_config=col_cfg_task, num_rows="dynamic", use_container_width=True, key="tasks_editor")

# ==========================================
# 5. 施工任務管理 (💡 統一為單一強大表格)
# ==========================================
st.header("🧱 施工任務管理")

col_cfg_task = {
    "區域": st.column_config.SelectboxColumn("📍 區域", options=st.session_state.regions, required=True),
    "施工項目": st.column_config.TextColumn("🧱 施工項目", required=True),
    "施工廠商": st.column_config.SelectboxColumn("👷 廠商", options=st.session_state.subcontractors, required=True),
    "預定開始": st.column_config.DateColumn("📅 預定開始", format="MM/DD", required=True),
    "預定完成": st.column_config.DateColumn("📅 預定完成", format="MM/DD", required=True),
    "實際開始": st.column_config.DateColumn("🏃 實際開始", format="MM/DD"),
    "實際完成": st.column_config.DateColumn("✅ 實際完成", format="MM/DD"),
    "完成度(%)": st.column_config.NumberColumn("💯 完成度", min_value=0, max_value=100, step=10, format="%d %%"),
    "是否為里程碑": st.column_config.CheckboxColumn("⭐ 里程碑", default=False)
}

# 取得最新的畫面狀態
current_tasks = st.session_state.tasks.copy()
edited_tasks = st.data_editor(current_tasks, column_config=col_cfg_task, num_rows="dynamic", use_container_width=True, key="tasks_editor")

# 自動滿百邏輯
edited_tasks.loc[edited_tasks['實際完成'].notnull(), '完成度(%)'] = 100

if not edited_tasks.equals(current_tasks):
    st.session_state.tasks = edited_tasks # 無條件保留狀態，徹底消滅閃退
    
    clean_t = edited_tasks.dropna(subset=['施工項目', '預定開始', '預定完成'])
    invalid_t = [i+1 for i, r in clean_t.iterrows() if str(r['區域']) not in st.session_state.regions or str(r['施工廠商']) not in st.session_state.subcontractors]
    
    if not invalid_t:
        try:
            up_t = []
            for _, r in clean_t.iterrows():
                comp_val = r.get('完成度(%)', 0)
                comp_int = 0 if pd.isna(comp_val) or comp_val == "" else int(float(comp_val))
                up_t.append({
                    "task_name": str(r['施工項目']), "subcontractor": str(r['施工廠商']), 
                    "start_date": safe_date(r['預定開始']), "end_date": safe_date(r['預定完成']), "region": str(r['區域']), 
                    "is_milestone": bool(r['是否為里程碑']), 
                    "actual_start": safe_date(r['實際開始']), "actual_end": safe_date(r['實際完成']), "completion": comp_int
                })
            
            supabase.table("tasks").delete().neq("id", -1).execute()
            if up_t: supabase.table("tasks").insert(up_t).execute()
        except Exception as e: pass
    else: st.error(f"施工清單第 {invalid_t} 列廠商或區域名稱不合法")

# ==========================================
# 6. 試車任務管理 (💡 統一表格 + 支援里程碑)
# ==========================================
st.header("🧪 試車任務管理")

col_cfg_comm = {
    "區域": st.column_config.SelectboxColumn("📍 區域", options=st.session_state.regions, required=True),
    "試車項目": st.column_config.TextColumn("🧪 試車項目", required=True),
    "預定開始": st.column_config.DateColumn("📅 預定開始", format="MM/DD", required=True),
    "預定完成": st.column_config.DateColumn("📅 預定完成", format="MM/DD", required=True),
    "實際開始": st.column_config.DateColumn("🏃 實際開始", format="MM/DD"),
    "實際完成": st.column_config.DateColumn("✅ 實際完成", format="MM/DD"),
    "完成度(%)": st.column_config.NumberColumn("💯 完成度", min_value=0, max_value=100, step=10, format="%d %%"),
    "是否為里程碑": st.column_config.CheckboxColumn("⭐ 里程碑", default=False)
}

current_c_tasks = st.session_state.comm_tasks.copy()
edited_comm = st.data_editor(current_c_tasks, column_config=col_cfg_comm, num_rows="dynamic", use_container_width=True, key="comm_editor")

edited_comm.loc[edited_comm['實際完成'].notnull(), '完成度(%)'] = 100

if not edited_comm.equals(current_c_tasks):
    st.session_state.comm_tasks = edited_comm # 無條件保留狀態
    
    clean_c = edited_comm.dropna(subset=['試車項目', '預定開始', '預定完成'])
    invalid_c = [i+1 for i, r in clean_c.iterrows() if str(r['區域']) not in st.session_state.regions]
    
    if not invalid_c:
        try:
            up_c = []
            for _, r in clean_c.iterrows():
                comp_val = r.get('完成度(%)', 0)
                comp_int = 0 if pd.isna(comp_val) or comp_val == "" else int(float(comp_val))
                up_c.append({
                    "test_item": str(r['試車項目']), "start_date": safe_date(r['預定開始']), "end_date": safe_date(r['預定完成']), 
                    "region": str(r['區域']), "is_milestone": bool(r.get('是否為里程碑', False)),
                    "actual_start": safe_date(r['實際開始']), "actual_end": safe_date(r['實際完成']), "completion": comp_int
                })
            
            supabase.table("commissioning_tasks").delete().neq("id", -1).execute()
            if up_c: supabase.table("commissioning_tasks").insert(up_c).execute()
        except Exception as e: pass
    else: st.error(f"試車清單第 {invalid_c} 列區域名稱不合法")

# ==========================================
# 7. 圖表生成 (💡 支援試車里程碑標記)
# ==========================================
st.divider()
tab_g1, tab_g2 = st.tabs(["📊 施工進度圖表", "⚙️ 試車排程圖表"])

def draw_gantt(df, title, color_col):
    p_df = df.dropna(subset=[df.columns[1], '預定開始', '預定完成']).copy()
    if p_df.empty: return st.warning("請填寫資料")
    
    p_df['預定開始'] = pd.to_datetime(p_df['預定開始'])
    p_df['預定完成'] = pd.to_datetime(p_df['預定完成'])
    p_df['實際開始'] = pd.to_datetime(p_df['實際開始'], errors='coerce')
    p_df['實際完成'] = pd.to_datetime(p_df['實際完成'], errors='coerce')
    p_df['完成度(%)'] = p_df['完成度(%)'].fillna(0).astype(int)
    p_df = p_df.sort_values("預定開始")
    
    planned_duration = p_df['預定完成'] - p_df['預定開始']
    p_df['進度開始'] = p_df['實際開始']
    p_df['進度結束'] = pd.NaT
    
    task_col = p_df.columns[1] 

    for idx, row in p_df.iterrows():
        # 🌟 超前或延誤判定 (加入表情符號)
        if pd.notnull(row['實際完成']) and pd.notnull(row['預定完成']):
            if row['實際完成'] < row['預定完成']:
                p_df.loc[idx, task_col] = f"🧨 {row[task_col]}"
            elif row['實際完成'] > row['預定完成']:
                p_df.loc[idx, task_col] = f"💀 {row[task_col]}"

        # 🌟 實際進度推移計算
        if pd.notnull(row['實際開始']):
            if pd.notnull(row['實際完成']):
                p_df.loc[idx, '進度結束'] = row['實際完成']
                p_df.loc[idx, '完成度(%)'] = 100
            else:
                p_df.loc[idx, '進度結束'] = row['實際開始'] + planned_duration[idx] * (row['完成度(%)'] / 100.0)
    
    color_map = {v: px.colors.qualitative.Plotly[i % 10] for i, v in enumerate(p_df[color_col].unique())}
    
    p_df['是否為里程碑'] = p_df['是否為里程碑'].fillna(False).astype(bool)
    draw_df = p_df[~p_df['是否為里程碑']]
    if draw_df.empty: return st.warning("⚠️ 必須至少有一項「非里程碑」的任務才能建立座標軸！")
        
    # 第一層：預定計畫 (透明底色)
    fig = px.timeline(draw_df, x_start="預定開始", x_end="預定完成", y=task_col, color=color_col, color_discrete_map=color_map, height=400+len(p_df)*30)
    fig.update_traces(opacity=0.3)
    
    # 第二層：實際進度 (實色斜線，從實際開工日開始推移)
    prog_df = draw_df.dropna(subset=['進度開始', '進度結束'])
    if not prog_df.empty:
        fig2 = px.timeline(prog_df, x_start="進度開始", x_end="進度結束", y=task_col, color=color_col, color_discrete_map=color_map)
        fig2.update_traces(opacity=1.0, marker_pattern_shape="/") 
        for tr in fig2.data:
            tr.showlegend = False 
            fig.add_trace(tr)
            
    fig.update_layout(barmode='overlay') 
    
    # 第三層：里程碑 (現在施工與試車通用)
    leg_set = set(draw_df[color_col].unique()) if not draw_df.empty else set()
    for _, m in p_df[p_df['是否為里程碑']].iterrows():
        cat = m[color_col]
        show_leg = cat not in leg_set
        if show_leg: leg_set.add(cat)
        
        if pd.notnull(m['實際完成']):
            fig.add_trace(go.Scatter(
                x=[m['實際完成']], y=[m[task_col]], mode='text',
                text=[f"✅ {m['實際完成'].strftime('%m/%d')}"], textposition='middle center', 
                textfont=dict(color='green', size=16, weight='bold'),
                name=cat, legendgroup=cat, showlegend=show_leg
            ))
        else:
            fig.add_trace(go.Scatter(
                x=[m['預定開始']], y=[m[task_col]], mode='markers+text',
                marker=dict(symbol='star', size=18, color=color_map.get(cat, 'gray'), line=dict(color='black', width=1)),
                text=[f" {m['預定開始'].strftime('%m/%d')}"], textposition='middle right', 
                textfont=dict(color='black', size=12),
                name=cat, legendgroup=cat, showlegend=show_leg
            ))

    # 今日線定位
    try: today = pd.Timestamp.now(tz='Asia/Taipei').normalize()
    except: today = pd.Timestamp.now().normalize()
        
    fig.add_vline(x=today, line_width=2, line_dash="dash", line_color="red", layer="above")
    fig.add_annotation(x=today, y=1, yref="paper", yanchor="bottom", text="今日", showarrow=False, font=dict(color="red", size=14))

    fig.update_yaxes(categoryorder='array', categoryarray=p_df[task_col].tolist(), autorange="reversed", showgrid=True, gridcolor='black', tickfont=dict(color="black", size=14))
    fig.update_xaxes(showgrid=True, gridcolor='black', tickformat="%m/%d", dtick="D1", tickfont=dict(color="black", size=12))
    
    chart_config = {'displaylogo': False, 'modeBarButtonsToRemove': ['lasso2d', 'select2d']}
    fig.update_layout(plot_bgcolor="#f0f0f0", paper_bgcolor="#f0f0f0", font=dict(color="black"), title=dict(text=title, font=dict(size=22)))
    st.plotly_chart(fig, use_container_width=True, config=chart_config)

with tab_g1:
    v_mode = st.radio("分類維度：", ["區域", "施工廠商"], horizontal=True, key="mode_const")
    if construction_button("🚀 生成施工甘特圖", key="run_g1"): 
        draw_gantt(st.session_state.tasks, f"🧱 {st.session_state.project_name} - 施工進度總表", v_mode)

with tab_g2:
    if comm_button("✅ 生成試車甘特圖", key="run_g2"): 
        draw_gantt(st.session_state.comm_tasks, f"🧪 {st.session_state.project_name} - 試車排程總表", "區域")

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
        clean_snap_t = st.session_state.tasks.dropna(subset=['施工項目', '預定開始', '預定完成'])
        clean_snap_c = st.session_state.comm_tasks.dropna(subset=['試車項目', '預定開始', '預定完成'])
        snap = {"tasks": clean_snap_t.to_json(orient='records', date_format='iso'), "comm": clean_snap_c.to_json(orient='records', date_format='iso')}
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
                    up_t = []
                    for _, r in df_t.iterrows():
                        c_val = r.get('完成度(%)', 0)
                        c_int = 0 if pd.isna(c_val) or c_val == "" else int(float(c_val))
                        up_t.append({"task_name": r['施工項目'], "subcontractor": r['施工廠商'], "start_date": safe_date(r['預定開始']), "end_date": safe_date(r['預定完成']), "region": r['區域'], "is_milestone": bool(r.get('是否為里程碑', False)), "actual_start": safe_date(r.get('實際開始')), "actual_end": safe_date(r.get('實際完成')), "completion": c_int})
                    supabase.table("tasks").delete().neq("id", -1).execute()
                    if up_t: supabase.table("tasks").insert(up_t).execute()
                    
                    df_c = pd.read_json(io.StringIO(full_data['comm']))
                    up_c = []
                    for _, r in df_c.iterrows():
                        c_val = r.get('完成度(%)', 0)
                        c_int = 0 if pd.isna(c_val) or c_val == "" else int(float(c_val))
                        up_c.append({"test_item": r['試車項目'], "start_date": safe_date(r['預定開始']), "end_date": safe_date(r['預定完成']), "region": r['區域'], "is_milestone": bool(r.get('是否為里程碑', False)), "actual_start": safe_date(r.get('實際開始')), "actual_end": safe_date(r.get('實際完成')), "completion": c_int})
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
