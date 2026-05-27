import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import json
from supabase import create_client, Client
import datetime

# ==========================================
# 0. 頁面基本設定 (⚠️ 必須在第一行)
# ==========================================
st.set_page_config(layout="wide", page_title="多專案營建與試車管理系統")

# ==========================================
# 1. Supabase 初始化與資料處理
# ==========================================
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

def load_projects():
    res = supabase.table("projects").select("name").execute()
    return [item['name'] for item in res.data] if res.data else ["未命名專案"]

def load_data(table_name="tasks", project_name="W442 新增UT機"):
    res = supabase.table(table_name).select("*").eq("project_name", project_name).execute()
    df = pd.DataFrame(res.data)
    
    if table_name == "tasks":
        cols = ['區域', '施工項目', '施工廠商', '預定開始', '預定完成', '實際開始', '實際完成', '完成度(%)', '是否為里程碑', '備註']
        rename_map = {'task_name': '施工項目', 'subcontractor': '施工廠商', 'start_date': '預定開始', 'end_date': '預定完成', 'region': '區域', 'is_milestone': '是否為里程碑', 'actual_start': '實際開始', 'actual_end': '實際完成', 'completion': '完成度(%)', 'remarks': '備註'}
    else:
        cols = ['區域', '試車項目', '預定開始', '預定完成', '實際開始', '實際完成', '完成度(%)', '是否為里程碑', '備註']
        rename_map = {'test_item': '試車項目', 'start_date': '預定開始', 'end_date': '預定完成', 'region': '區域', 'actual_start': '實際開始', 'actual_end': '實際完成', 'completion': '完成度(%)', 'is_milestone': '是否為里程碑', 'remarks': '備註'}

    if not df.empty:
        df = df.rename(columns=rename_map)
        for c in cols:
            if c not in df.columns:
                df[c] = 0 if c == '完成度(%)' else (False if c == '是否為里程碑' else "")
        for d in ['預定開始', '預定完成', '實際開始', '實際完成']:
            df[d] = pd.to_datetime(df[d]).dt.date
        df['是否為里程碑'] = df['是否為里程碑'].fillna(False).astype(bool)
        df['完成度(%)'] = df['完成度(%)'].fillna(0).astype(int)
        df['備註'] = df['備註'].fillna("")
        return df[cols]
    return pd.DataFrame(columns=cols)

def load_list(table_name, project_name):
    res = supabase.table(table_name).select("name").eq("project_name", project_name).execute()
    return [item['name'] for item in res.data] if res.data else []

# ==========================================
# 2. 樣式注入與輔助函數 (純淨版)
# ==========================================
def construction_button(label, key):
    return st.button(label, key=key, use_container_width=True)

def comm_button(label, key):
    return st.button(label, key=key, use_container_width=True)

def safe_date(d):
    if pd.isna(d) or d == "" or d is None: return None
    return d.isoformat() if hasattr(d, 'isoformat') else str(d)
# ==========================================
# 3. 專案切換與動態資料載入
# ==========================================
if 'projects' not in st.session_state: st.session_state.projects = load_projects()

st.sidebar.title("工程管理")
selected_project = st.sidebar.selectbox("請選擇工程案：", st.session_state.projects)

with st.sidebar.expander("新增與刪除專案", expanded=False):
    new_p = st.text_input("新增專案名稱", placeholder="輸入新工程案名稱...")
    if st.button("➕ 新增專案", use_container_width=True):
        if new_p and new_p not in st.session_state.projects:
            try:
                supabase.table("projects").insert({"name": new_p}).execute()
                st.session_state.projects.append(new_p)
                st.success(f"已新增 {new_p}")
                st.rerun()
            except Exception as e: st.error(f"新增失敗: {e}")
            
    st.divider()
    del_p = st.selectbox("選擇要刪除的專案", st.session_state.projects)
    if st.button("刪除專案", type="primary", use_container_width=True):
        if len(st.session_state.projects) > 1:
            try:
                supabase.table("tasks").delete().eq("project_name", del_p).execute()
                supabase.table("commissioning_tasks").delete().eq("project_name", del_p).execute()
                supabase.table("regions").delete().eq("project_name", del_p).execute()
                supabase.table("subcontractors").delete().eq("project_name", del_p).execute()
                supabase.table("projects").delete().eq("name", del_p).execute()
                
                st.session_state.projects.remove(del_p)
                st.toast(f"已徹底刪除 {del_p}", icon="🗑️")
                st.rerun()
            except Exception as e: st.error(f"刪除失敗: {e}")
        else:
            st.error("必須保留至少一個專案！")

st.title(f"🛠️ {selected_project} ")
st.markdown("---")

if 'current_project' not in st.session_state or st.session_state.current_project != selected_project:
    st.session_state.current_project = selected_project
    st.session_state.tasks = load_data("tasks", selected_project)
    st.session_state.comm_tasks = load_data("commissioning_tasks", selected_project)
    st.session_state.regions = load_list("regions", selected_project)
    st.session_state.subcontractors = load_list("subcontractors", selected_project)

# ==========================================
# 4. 區域與廠商管理 (側邊欄) - 隔離版
# ==========================================
st.sidebar.header(f"基礎資料管理 ({selected_project})")
with st.sidebar.expander("區域與廠商管理"):
    t_reg, t_sub = st.tabs(["區域", "廠商"])
    with t_reg:
        nr = st.text_input("新增區域名稱", key="nr_in")
        if construction_button("加入區域", key="btn_add_reg"):
            if nr and nr not in st.session_state.regions:
                supabase.table("regions").insert({"name": nr, "project_name": selected_project}).execute()
                st.session_state.regions.append(nr)
                st.rerun()
        
        dr_options = st.session_state.regions if st.session_state.regions else ["(尚無資料)"]
        dr = st.selectbox("選擇刪除區域", dr_options)
        if st.button("🗑️ 刪除區域", type="primary") and dr != "(尚無資料)":
            if not (st.session_state.tasks['區域'] == dr).any() and not (st.session_state.comm_tasks['區域'] == dr).any():
                supabase.table("regions").delete().eq("name", dr).eq("project_name", selected_project).execute()
                st.session_state.regions.remove(dr)
                st.rerun()
            else: st.error("⚠️ 該區域尚有任務")
            
    with t_sub:
        ns = st.text_input("新增廠商名稱", key="ns_in")
        if construction_button("加入廠商", key="btn_add_sub"):
            if ns and ns not in st.session_state.subcontractors:
                supabase.table("subcontractors").insert({"name": ns, "project_name": selected_project}).execute()
                st.session_state.subcontractors.append(ns)
                st.rerun()
                
        ds_options = st.session_state.subcontractors if st.session_state.subcontractors else ["(尚無資料)"]
        ds = st.selectbox("選擇刪除廠商", ds_options, key="ds_sel")
        if st.button("🗑️ 刪除廠商", type="primary") and ds != "(尚無資料)":
            if not (st.session_state.tasks['施工廠商'] == ds).any():
                supabase.table("subcontractors").delete().eq("name", ds).eq("project_name", selected_project).execute()
                st.session_state.subcontractors.remove(ds)
                st.rerun()
            else: st.error("⚠️ 該廠商尚有任務")

safe_regions = st.session_state.regions if st.session_state.regions else ["未設定"]
safe_subcontractors = st.session_state.subcontractors if st.session_state.subcontractors else ["未設定"]

# ==========================================
# 5. 施工任務管理
# ==========================================
with st.expander("施工任務管理", expanded=True):
    
    for col in ['預定開始', '預定完成', '實際開始', '實際完成']:
        st.session_state.tasks[col] = pd.to_datetime(st.session_state.tasks[col], errors='coerce').dt.date
    st.session_state.tasks['是否為里程碑'] = st.session_state.tasks['是否為里程碑'].fillna(False).astype(bool)

    st.subheader("1. 預定計畫")
    col_cfg_plan = {
        "區域": st.column_config.SelectboxColumn("區域", options=safe_regions, required=True),
        "施工項目": st.column_config.TextColumn("施工項目", required=True),
        "施工廠商": st.column_config.SelectboxColumn("施工廠商", options=safe_subcontractors, required=True),
        "預定開始": st.column_config.DateColumn("預定開始", format="MM/DD", required=True),
        "預定完成": st.column_config.DateColumn("預定完成", format="MM/DD", required=True),
        "是否為里程碑": st.column_config.CheckboxColumn("里程碑", default=False)
    }
    ed_plan = st.data_editor(st.session_state.tasks[['區域', '施工項目', '施工廠商', '預定開始', '預定完成', '是否為里程碑']], column_config=col_cfg_plan, num_rows="dynamic", use_container_width=True)

    st.subheader("2. 實際進度回報")
    col_cfg_act = {
        "施工項目": st.column_config.TextColumn("施工項目", disabled=True),
        "實際開始": st.column_config.DateColumn("實際開工", format="MM/DD"),
        "實際完成": st.column_config.DateColumn("實際完成", format="MM/DD"),
        "完成度(%)": st.column_config.NumberColumn("完成度 (%)", min_value=0, max_value=100, step=10, format="%d %%")
    }

    act_sync = ed_plan[['施工項目']].copy()
    act_sync['實際開始'] = None
    act_sync['實際完成'] = None
    act_sync['完成度(%)'] = 0

    if not st.session_state.tasks.empty:
        min_len = min(len(act_sync), len(st.session_state.tasks))
        act_sync.loc[act_sync.index[:min_len], '實際開始'] = st.session_state.tasks['實際開始'].values[:min_len]
        act_sync.loc[act_sync.index[:min_len], '實際完成'] = st.session_state.tasks['實際完成'].values[:min_len]
        act_sync.loc[act_sync.index[:min_len], '完成度(%)'] = st.session_state.tasks['完成度(%)'].values[:min_len]
        
    act_sync['完成度(%)'] = act_sync['完成度(%)'].fillna(0).astype(int)
    ed_act = st.data_editor(act_sync, column_config=col_cfg_act, num_rows="fixed", use_container_width=True)

    col1, col2 = st.columns([5, 1])
    with col2:
        btn_save_t = st.button("儲存並同步", type="primary", use_container_width=True, key="btn_save_tasks")
        
    if btn_save_t:
        with st.spinner("資料同步中..."):
            new_tasks = pd.concat([ed_plan, ed_act[['實際開始', '實際完成', '完成度(%)']]], axis=1)
            new_tasks['備註'] = st.session_state.tasks['備註'] if '備註' in st.session_state.tasks.columns else ""
            new_tasks['備註'] = new_tasks['備註'].fillna("")

            m_mask = new_tasks['是否為里程碑'] == True
            new_tasks.loc[m_mask, '預定完成'] = new_tasks.loc[m_mask, '預定開始']
            new_tasks.loc[m_mask, '實際完成'] = new_tasks.loc[m_mask, '實際開始']
            new_tasks.loc[new_tasks['實際完成'].notnull(), '完成度(%)'] = 100

            clean_t = new_tasks.dropna(subset=['施工項目', '預定開始', '預定完成']).copy()
            
            try:
                supabase.table("tasks").delete().eq("project_name", selected_project).execute()
                
                if not clean_t.empty:
                    up_t = []
                    for _, r in clean_t.iterrows():
                        comp_val = r.get('完成度(%)', 0)
                        comp_int = 0 if pd.isna(comp_val) or comp_val == "" else int(float(comp_val))
                        rmk = r.get('備註', '')
                        rmk_str = "" if pd.isna(rmk) else str(rmk)
                        
                        up_t.append({
                            "project_name": selected_project, 
                            "task_name": str(r['施工項目']), "subcontractor": str(r['施工廠商']), 
                            "start_date": safe_date(r['預定開始']), "end_date": safe_date(r['預定完成']), "region": str(r['區域']), 
                            "is_milestone": bool(r.get('是否為里程碑', False)), 
                            "actual_start": safe_date(r['實際開始']), "actual_end": safe_date(r['實際完成']), 
                            "completion": comp_int, "remarks": rmk_str
                        })
                    supabase.table("tasks").insert(up_t).execute()
                
                st.session_state.tasks = clean_t
                st.success("✅ 施工進度已成功同步！")
                st.rerun()
            except Exception as e:
                st.error(f"⚠️ 資料庫寫入失敗: {e}")

# ==========================================
# 6. 試車任務管理
# ==========================================
with st.expander("試車任務管理", expanded=True):
    
    for col in ['預定開始', '預定完成', '實際開始', '實際完成']:
        st.session_state.comm_tasks[col] = pd.to_datetime(st.session_state.comm_tasks[col], errors='coerce').dt.date
    st.session_state.comm_tasks['是否為里程碑'] = st.session_state.comm_tasks['是否為里程碑'].fillna(False).astype(bool)

    st.subheader("1. 預定計畫")
    col_cfg_c_plan = {
        "區域": st.column_config.SelectboxColumn("區域", options=safe_regions, required=True),
        "試車項目": st.column_config.TextColumn("試車項目", required=True),
        "預定開始": st.column_config.DateColumn("預定開始", format="MM/DD", required=True),
        "預定完成": st.column_config.DateColumn("預定完成", format="MM/DD", required=True),
        "是否為里程碑": st.column_config.CheckboxColumn("里程碑", default=False)
    }
    ed_c_plan = st.data_editor(st.session_state.comm_tasks[['區域', '試車項目', '預定開始', '預定完成', '是否為里程碑']], column_config=col_cfg_c_plan, num_rows="dynamic", use_container_width=True)

    st.subheader("2. 實際進度回報")
    
    c_act_sync = ed_c_plan[['試車項目']].copy()
    c_act_sync['實際開始'] = None
    c_act_sync['實際完成'] = None
    c_act_sync['完成度(%)'] = 0

    if not st.session_state.comm_tasks.empty:
        min_len_c = min(len(c_act_sync), len(st.session_state.comm_tasks))
        c_act_sync.loc[c_act_sync.index[:min_len_c], '實際開始'] = st.session_state.comm_tasks['實際開始'].values[:min_len_c]
        c_act_sync.loc[c_act_sync.index[:min_len_c], '實際完成'] = st.session_state.comm_tasks['實際完成'].values[:min_len_c]
        c_act_sync.loc[c_act_sync.index[:min_len_c], '完成度(%)'] = st.session_state.comm_tasks['完成度(%)'].values[:min_len_c]
        
    c_act_sync['完成度(%)'] = c_act_sync['完成度(%)'].fillna(0).astype(int)
    ed_c_act = st.data_editor(c_act_sync, column_config=col_cfg_act, num_rows="fixed", use_container_width=True)

    col1, col2 = st.columns([5, 1])
    with col2:
        btn_save_c = st.button("儲存並同步", type="primary", use_container_width=True, key="btn_save_comm")

    if btn_save_c:
        with st.spinner("資料同步中..."):
            new_c_tasks = pd.concat([ed_c_plan, ed_c_act[['實際開始', '實際完成', '完成度(%)']]], axis=1)
            new_c_tasks['備註'] = st.session_state.comm_tasks['備註'] if '備註' in st.session_state.comm_tasks.columns else ""
            new_c_tasks['備註'] = new_c_tasks['備註'].fillna("")

            mc_mask = new_c_tasks['是否為里程碑'] == True
            new_c_tasks.loc[mc_mask, '預定完成'] = new_c_tasks.loc[mc_mask, '預定開始']
            new_c_tasks.loc[mc_mask, '實際完成'] = new_c_tasks.loc[mc_mask, '實際開始']
            new_c_tasks.loc[new_c_tasks['實際完成'].notnull(), '完成度(%)'] = 100

            clean_c = new_c_tasks.dropna(subset=['試車項目', '預定開始', '預定完成']).copy()
            
            try:
                supabase.table("commissioning_tasks").delete().eq("project_name", selected_project).execute()
                
                if not clean_c.empty:
                    up_c = []
                    for _, r in clean_c.iterrows():
                        comp_val = r.get('完成度(%)', 0)
                        comp_int = 0 if pd.isna(comp_val) or comp_val == "" else int(float(comp_val))
                        rmk = r.get('備註', '')
                        rmk_str = "" if pd.isna(rmk) else str(rmk)
                        
                        up_c.append({
                            "project_name": selected_project, 
                            "test_item": str(r['試車項目']), "start_date": safe_date(r['預定開始']), "end_date": safe_date(r['預定完成']), 
                            "region": str(r['區域']), "is_milestone": bool(r.get('是否為里程碑', False)), 
                            "actual_start": safe_date(r['實際開始']), "actual_end": safe_date(r['實際完成']), 
                            "completion": comp_int, "remarks": rmk_str
                        })
                    supabase.table("commissioning_tasks").insert(up_c).execute()
                
                st.session_state.comm_tasks = clean_c
                st.success("✅ 試車進度已成功同步！")
                st.rerun()
            except Exception as e:
                st.error(f"⚠️ 資料庫寫入失敗: {e}")

# ==========================================
# 7. 圖表生成
# ==========================================
st.divider()
tab_g1, tab_g2 = st.tabs(["施工進度圖表", "試車排程圖表"])

def draw_gantt(df, title, color_col):
    p_df = df.dropna(subset=[df.columns[1], '預定開始', '預定完成']).copy()
    if p_df.empty: return st.warning("請先輸入計畫資料")
    
    p_df['預定開始'] = pd.to_datetime(p_df['預定開始'])
    p_df['預定完成'] = pd.to_datetime(p_df['預定完成'])
    p_df['實際開始'] = pd.to_datetime(p_df['實際開始'], errors='coerce')
    p_df['實際完成'] = pd.to_datetime(p_df['實際完成'], errors='coerce')
    p_df = p_df.sort_values("預定開始")
    
    p_df['進度結束'] = pd.NaT

    task_col = p_df.columns[1] 

    for idx, row in p_df.iterrows():
        if pd.notnull(row['實際完成']) and pd.notnull(row['預定完成']):
            if row['實際完成'] < row['預定完成']: 
                p_df.loc[idx, task_col] = f"[提前完工!] {row[task_col]}"
            elif row['實際完成'] > row['預定完成']: 
                p_df.loc[idx, task_col] = f"[Delay] {row[task_col]}"

        if pd.notnull(row['實際開始']):
            if pd.notnull(row['實際完成']):
                p_df.loc[idx, '進度結束'] = row['實際完成']
            else:
                planned_dur = row['預定完成'] - row['預定開始']
                p_df.loc[idx, '進度結束'] = row['實際開始'] + planned_dur * (row['完成度(%)'] / 100.0)
    
    color_map = {v: px.colors.qualitative.Plotly[i % 10] for i, v in enumerate(p_df[color_col].unique())}
    draw_df = p_df[~p_df['是否為里程碑']]
    
    if draw_df.empty: return st.warning("⚠️ 至少需有一項非里程碑任務")
        
    fig = px.timeline(draw_df, x_start="預定開始", x_end="預定完成", y=task_col, color=color_col, color_discrete_map=color_map, height=400+len(p_df)*30)
    fig.update_traces(opacity=0.3)
    
    prog_df = draw_df.dropna(subset=['實際開始', '進度結束'])
    if not prog_df.empty:
        fig2 = px.timeline(prog_df, x_start="實際開始", x_end="進度結束", y=task_col, color=color_col, color_discrete_map=color_map)
        fig2.update_traces(opacity=1.0, marker_pattern_shape="/") 
        for tr in fig2.data: tr.showlegend = False; fig.add_trace(tr)
            
    fig.update_layout(barmode='overlay') 
    
    ms_leg_set = set() 
    
    for _, m in p_df[p_df['是否為里程碑']].iterrows():
        cat = m[color_col]
        region = m['區域']
        is_done = pd.notnull(m['實際完成'])
        
        # 💡 核心修正：讓右側圖例名稱動態跟隨您選擇的分類維度 (cat)，並加上「里程碑」字樣使其更清晰
        leg_name = f"{cat}(完成)" if is_done else f"{cat}"
        
        show_leg = leg_name not in ms_leg_set
        if show_leg: ms_leg_set.add(leg_name)
        
        vendor_info = f"<br>廠商: {m['施工廠商']}" if '施工廠商' in m else ""
        hover_text = f"<b>里程碑：{m[task_col]}</b><br>區域: {region}{vendor_info}<br>日期: %{{x|%Y-%m-%d}}<extra></extra>"
        
        if is_done:
            fig.add_trace(go.Scatter(
                x=[m['實際完成']], y=[m[task_col]], mode='text', 
                text=[f"✅ {m['實際完成'].strftime('%m/%d')}"], textfont=dict(color='green', size=16, weight='bold'), 
                name=leg_name, legendgroup=leg_name, showlegend=show_leg,
                hovertemplate=hover_text
            ))
        else:
            fig.add_trace(go.Scatter(
                x=[m['預定開始']], y=[m[task_col]], mode='markers+text', 
                marker=dict(symbol='star', size=18, color=color_map.get(cat, 'gray'), line=dict(color='black', width=1)), 
                text=[f" {m['預定開始'].strftime('%m/%d')}"], textposition='middle right', textfont=dict(color='black', size=12), 
                name=leg_name, legendgroup=leg_name, showlegend=show_leg,
                hovertemplate=hover_text
            ))

    today = pd.Timestamp.now(tz='Asia/Taipei').normalize()
    fig.add_vline(x=today, line_width=2, line_dash="dash", line_color="red", layer="above")
    fig.add_annotation(x=today, y=1, yref="paper", yanchor="bottom", text="今日", showarrow=False, font=dict(color="red", size=14))

    fig.update_yaxes(categoryorder='array', categoryarray=p_df[task_col].tolist(), autorange="reversed", showgrid=True, gridcolor='black', tickfont=dict(color="black", size=14))
    fig.update_xaxes(showgrid=True, gridcolor='black', tickformat="%m/%d", dtick="D1", tickfont=dict(color="black", size=12))
    st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False, 'modeBarButtonsToRemove': ['lasso2d', 'select2d']})

with tab_g1:
    v_mode = st.radio("分類維度：", ["區域", "施工廠商"], horizontal=True, key="mode_const")
    draw_gantt(st.session_state.tasks, f"{selected_project} - 施工圖", v_mode)

with tab_g2:
    draw_gantt(st.session_state.comm_tasks, f"{selected_project} - 試車圖", "區域")
# 8. 動態備註系統
# ==========================================
st.divider()
st.subheader("施工日誌 / 備註")
c1, c2 = st.columns([1, 1])

with c1:
    task_opts = st.session_state.tasks['施工項目'].dropna().unique().tolist()
    if task_opts:
        sel_t = st.selectbox("選擇施工項目：", task_opts, key="sel_note_t")
        if sel_t:
            row = st.session_state.tasks[st.session_state.tasks['施工項目'] == sel_t].iloc[0]
            new_note_t = st.text_area(f"【{sel_t}】備註：", value=row.get('備註', ''), height=150, key=f"txt_t_{sel_t}")
            if st.button("儲存施工備註", key="save_t"):
                st.session_state.tasks.loc[st.session_state.tasks['施工項目'] == sel_t, '備註'] = new_note_t
                try:
                    supabase.table("tasks").update({"remarks": new_note_t}).eq("task_name", sel_t).eq("project_name", selected_project).execute()
                    st.success("施工備註已同步至雲端！")
                except Exception as e: st.error(f"備註寫入失敗: {e}")
    else: st.info("尚無施工項目可供填寫備註。")

with c2:
    comm_opts = st.session_state.comm_tasks['試車項目'].dropna().unique().tolist()
    if comm_opts:
        sel_c = st.selectbox("選擇試車項目：", comm_opts, key="sel_note_c")
        if sel_c:
            row_c = st.session_state.comm_tasks[st.session_state.comm_tasks['試車項目'] == sel_c].iloc[0]
            new_note_c = st.text_area(f"【{sel_c}】備註：", value=row_c.get('備註', ''), height=150, key=f"txt_c_{sel_c}")
            if st.button("儲存試車備註", key="save_c"):
                st.session_state.comm_tasks.loc[st.session_state.comm_tasks['試車項目'] == sel_c, '備註'] = new_note_c
                try:
                    supabase.table("commissioning_tasks").update({"remarks": new_note_c}).eq("test_item", sel_c).eq("project_name", selected_project).execute()
                    st.success("試車備註已同步至雲端！")
                except Exception as e: st.error(f"備註寫入失敗: {e}")
    else: st.info("尚無試車項目可供填寫備註。")

# ==========================================
# 9. 檔案備份與管理
# ==========================================
st.sidebar.divider()
with st.sidebar.expander("檔案管理"):
    st.download_button("下載施工 CSV", data=st.session_state.tasks.to_csv(index=False).encode('utf-8-sig'), file_name=f"{selected_project}_tasks.csv", use_container_width=True)
    st.download_button("下載試車 CSV", data=st.session_state.comm_tasks.to_csv(index=False).encode('utf-8-sig'), file_name=f"{selected_project}_comm.csv", use_container_width=True)
    
    st.divider()
    bn = st.text_input("存檔名稱", key="bn_in")
    if construction_button("立即存檔", key="btn_save_snap"):
        clean_snap_t = st.session_state.tasks.dropna(subset=['施工項目', '預定開始', '預定完成'])
        clean_snap_c = st.session_state.comm_tasks.dropna(subset=['試車項目', '預定開始', '預定完成'])
        snap = {"tasks": clean_snap_t.to_json(orient='records', date_format='iso'), "comm": clean_snap_c.to_json(orient='records', date_format='iso')}
        supabase.table("tasks_backups").insert({"backup_name": f"[{selected_project}] {bn if bn else '自動備份'}", "data_json": json.dumps(snap)}).execute()
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
                        up_t.append({"project_name": selected_project, "task_name": r['施工項目'], "subcontractor": r['施工廠商'], "start_date": safe_date(r['預定開始']), "end_date": safe_date(r['預定完成']), "region": r['區域'], "is_milestone": bool(r.get('是否為里程碑', False)), "actual_start": safe_date(r.get('實際開始')), "actual_end": safe_date(r.get('實際完成')), "completion": c_int, "remarks": r.get('備註', '')})
                    
                    supabase.table("tasks").delete().eq("project_name", selected_project).execute()
                    if up_t: supabase.table("tasks").insert(up_t).execute()
                    
                    df_c = pd.read_json(io.StringIO(full_data['comm']))
                    up_c = []
                    for _, r in df_c.iterrows():
                        c_val = r.get('完成度(%)', 0)
                        c_int = 0 if pd.isna(c_val) or c_val == "" else int(float(c_val))
                        up_c.append({"project_name": selected_project, "test_item": r['試車項目'], "start_date": safe_date(r['預定開始']), "end_date": safe_date(r['預定完成']), "region": r['區域'], "is_milestone": bool(r.get('是否為里程碑', False)), "actual_start": safe_date(r.get('實際開始')), "actual_end": safe_date(r.get('實際完成')), "completion": c_int, "remarks": r.get('備註', '')})
                    
                    supabase.table("commissioning_tasks").delete().eq("project_name", selected_project).execute()
                    if up_c: supabase.table("commissioning_tasks").insert(up_c).execute()
                    
                    st.session_state.tasks = load_data("tasks", selected_project)
                    st.session_state.comm_tasks = load_data("commissioning_tasks", selected_project)
                    st.rerun()
                except Exception as e: st.error(f"回復失敗: {e}")
        with c2:
            if st.button("刪除存檔", type="primary", use_container_width=True, key="btn_del_snap"):
                supabase.table("tasks_backups").delete().eq("id", opts[sel_b]).execute()
                st.rerun()

# ==========================================
# 10. 通知測試
# ==========================================
st.divider()
st.subheader("LINE 通知測試")

if st.button("測試", key="btn_test_line"):
    with st.spinner("LINE 通知發送中..."):
        try:
            res = supabase.functions.invoke(
                "notify-tasks", 
                invoke_options={"body": {"test": True}}
            )
            st.success("✅ 已觸發通知！請查看 LINE")
        except Exception as e:
            st.error(f"❌ 呼叫失敗：{e}")
# ==========================================
# 11. 魔法變色系統 (JavaScript 強制渲染)
# ==========================================
import streamlit.components.v1 as components

components.html(
    """
    <script>
    const doc = window.parent.document;
    const styleButtons = () => {
        const buttons = doc.querySelectorAll('.stButton button');
        buttons.forEach(btn => {
            const text = btn.innerText;
            
            // 🔹 只要按鈕文字包含這些字，全部強制變藍色
            if (text.includes('儲存施工') || text.includes('加入區域') || text.includes('加入廠商') || text.includes('立即存檔')) {
                btn.style.backgroundColor = '#003366';
                btn.style.color = '#FFFFFF';
                btn.style.border = 'none';
            } 
            // 🔸 只要按鈕文字包含這些字，全部強制變綠色
            else if (text.includes('LINE') || text.includes('儲存試車')) {
                btn.style.backgroundColor = '#1B5E20';
                btn.style.color = '#FFFFFF';
                btn.style.border = 'none';
            }
        });
    };
    
    // 立即執行一次
    styleButtons();
    // 建立監視器，只要您點擊網頁任何地方，確保按鈕顏色不會掉下來
    const observer = new MutationObserver(styleButtons);
    observer.observe(doc.body, { childList: true, subtree: true });
    </script>
    """,
    height=0,
    width=0,
)
