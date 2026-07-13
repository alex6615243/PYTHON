import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import json
from supabase import create_client, Client
import datetime
import tempfile
import os
import requests
import urllib.parse
import base64
import re
import streamlit.components.v1 as components

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
# 2. 樣式注入與輔助函數 (加入 disabled 支援)
# ==========================================
def construction_button(label, key, disabled=False):
    return st.button(label, key=key, use_container_width=True, disabled=disabled)

def comm_button(label, key, disabled=False):
    return st.button(label, key=key, use_container_width=True, disabled=disabled)

def safe_date(d):
    if pd.isna(d) or d == "" or d is None: return None
    return d.isoformat() if hasattr(d, 'isoformat') else str(d)

def has_unsaved_changes():
    for k in [f"ed_plan_state_{selected_project}", f"ed_act_state_{selected_project}", 
              f"ed_c_plan_state_{selected_project}", f"ed_c_act_state_{selected_project}"]:
        if k in st.session_state:
            state = st.session_state[k]
            if isinstance(state, dict):
                if state.get("edited_rows") or state.get("added_rows") or state.get("deleted_rows"):
                    return True
    return False

# ==========================================
# 3. 專案切換與動態資料載入
# ==========================================
if 'projects' not in st.session_state: st.session_state.projects = load_projects()

st.sidebar.title("工程管理")
selected_project = st.sidebar.selectbox("請選擇工程案：", st.session_state.projects)

with st.sidebar.expander("新增與刪除專案", expanded=False):
    new_p = st.text_input("新增專案名稱", placeholder="輸入新工程案名稱...")
    if st.button("新增專案", use_container_width=True):
        if new_p and new_p not in st.session_state.projects:
            try:
                supabase.table("projects").insert({"name": new_p}).execute()
                st.session_state.projects.append(new_p)
                st.success(f"已新增 {new_p}")
                st.rerun()
            except Exception as e: st.error(f"新增失敗: {e}")
            
    st.divider()
    del_p = st.selectbox("選擇要刪除的專案", st.session_state.projects)
    
    @st.dialog("⚠️ 確定要刪除專案嗎？")
    def confirm_delete(project_name):
        st.error(f"即將徹底刪除【{project_name}】！\n\n包含所有任務資料、進度、日誌與檔案都將被清空。")
        st.warning("此動作無法復原，請確認您已備份所需資料。")
        if st.button("🚨 我確定要徹底刪除", type="primary", use_container_width=True):
            try:
                supabase.table("tasks").delete().eq("project_name", project_name).execute()
                supabase.table("commissioning_tasks").delete().eq("project_name", project_name).execute()
                supabase.table("regions").delete().eq("project_name", project_name).execute()
                supabase.table("subcontractors").delete().eq("project_name", project_name).execute()
                supabase.table("projects").delete().eq("name", project_name).execute()
                
                st.session_state.projects.remove(project_name)
                st.success("✅ 專案已徹底刪除")
                st.rerun()
            except Exception as e: 
                st.error(f"刪除失敗: {e}")

    if st.button("刪除專案", type="primary", use_container_width=True):
        if len(st.session_state.projects) > 1:
            confirm_delete(del_p)
        else:
            st.error("必須保留至少一個專案！")

col_title, col_btn = st.columns([5, 1])

if 'current_project' not in st.session_state or st.session_state.current_project != selected_project:
    st.session_state.current_project = selected_project
    st.session_state.tasks = load_data("tasks", selected_project)
    st.session_state.comm_tasks = load_data("commissioning_tasks", selected_project)
    st.session_state.regions = load_list("regions", selected_project)
    st.session_state.subcontractors = load_list("subcontractors", selected_project)
    
    try:
        p_res = supabase.table("projects").select("is_closed, closed_date").eq("name", selected_project).execute()
        if p_res.data:
            st.session_state.is_closed = p_res.data[0].get('is_closed', False)
            st.session_state.closed_date = p_res.data[0].get('closed_date', None)
        else:
            st.session_state.is_closed = False
            st.session_state.closed_date = None
    except Exception:
        st.session_state.is_closed = False
        st.session_state.closed_date = None

with col_title:
    title_icon = "🔒" if st.session_state.get('is_closed', False) else "🛠️"
    st.title(f"{title_icon} {selected_project} ")

with col_btn:
    st.write("") 
    if st.session_state.get('is_closed', False):
        if st.button("🔓 解除結案", use_container_width=True):
            try:
                supabase.table("projects").update({"is_closed": False, "closed_date": None}).eq("name", selected_project).execute()
                st.session_state.is_closed = False
                st.session_state.closed_date = None
                st.rerun()
            except Exception as e: 
                st.error(f"❌ 操作失敗: {e}")
        st.caption(f"於 {st.session_state.closed_date} 結案")
    else:
        if st.button("結案", type="primary", use_container_width=True):
            try:
                today_str = datetime.date.today().isoformat()
                supabase.table("projects").update({"is_closed": True, "closed_date": today_str}).eq("name", selected_project).execute()
                st.session_state.is_closed = True
                st.session_state.closed_date = today_str
                st.balloons() 
                st.rerun()
            except Exception as e:
                st.error(f"❌ 結案失敗，真實錯誤為：{e}")

st.markdown("---")

is_proj_closed = st.session_state.get('is_closed', False)

if is_proj_closed:
    st.warning("🔒 **此專案已結案！** 系統已進入唯讀模式，所有排程、日誌與檔案上傳功能皆已鎖定。")

# ==========================================
# 4. 區域與廠商管理 (側邊欄) - 智慧阻斷警告版
# ==========================================
st.sidebar.header(f"基礎資料管理 ({selected_project})")
with st.sidebar.expander("區域與廠商管理"):
    
    if not is_proj_closed:
        st.error("⚠️ **新增前防呆提醒**\n\n新增項目會重新整理網頁來更新下拉選單。請務必先將右側任務 **「儲存並同步」**，否則尚未存檔的內容將會遺失！")
        
    @st.dialog("⚠️ 偵測到未儲存的任務變更")
    def confirm_add_base_data(data_type, item_name):
        st.error("右側表格有「尚未儲存」的編輯內容！")
        st.warning("如果您現在執意加入項目，網頁將會強制重新整理，剛才編輯的所有排程與百分比將會「完全遺失」！")
        st.markdown(f"準備新增的項目：**{item_name}**")
        
        c_back, c_go = st.columns(2)
        with c_back:
            if st.button("↩️ 放棄新增（先去右邊存檔）", use_container_width=True):
                st.rerun()
        with c_go:
            if st.button("🔥 不存檔，確定直接新增", type="primary", use_container_width=True):
                try:
                    if data_type == "region":
                        supabase.table("regions").insert({"name": item_name, "project_name": selected_project}).execute()
                        st.session_state.regions.append(item_name)
                    elif data_type == "subcontractor":
                        supabase.table("subcontractors").insert({"name": item_name, "project_name": selected_project}).execute()
                        st.session_state.subcontractors.append(item_name)
                    st.success("新增成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"新增失敗: {e}")

    t_reg, t_sub = st.tabs(["區域", "廠商"])
    with t_reg:
        nr = st.text_input("新增區域名稱", key="nr_in", disabled=is_proj_closed, placeholder="輸入前請先確認任務已存檔")
        if construction_button("加入區域", key="btn_add_reg", disabled=is_proj_closed):
            if nr:
                if has_unsaved_changes():
                    confirm_add_base_data("region", nr)
                elif nr not in st.session_state.regions:
                    supabase.table("regions").insert({"name": nr, "project_name": selected_project}).execute()
                    st.session_state.regions.append(nr)
                    st.rerun()
        
        dr_options = st.session_state.regions if st.session_state.regions else ["(尚無資料)"]
        dr = st.selectbox("選擇刪除區域", dr_options, disabled=is_proj_closed)
        if st.button("刪除區域", type="primary", disabled=is_proj_closed) and dr != "(尚無資料)":
            if not (st.session_state.tasks['區域'] == dr).any() and not (st.session_state.comm_tasks['區域'] == dr).any():
                supabase.table("regions").delete().eq("name", dr).eq("project_name", selected_project).execute()
                st.session_state.regions.remove(dr)
                st.rerun()
            else: st.error("⚠️ 該區域尚有任務")
            
    with t_sub:
        ns = st.text_input("新增廠商名稱", key="ns_in", disabled=is_proj_closed, placeholder="輸入前請先確認任務已存檔")
        if construction_button("加入廠商", key="btn_add_sub", disabled=is_proj_closed):
            if ns:
                if has_unsaved_changes():
                    confirm_add_base_data("subcontractor", ns)
                elif ns not in st.session_state.subcontractors:
                    supabase.table("subcontractors").insert({"name": ns, "project_name": selected_project}).execute()
                    st.session_state.subcontractors.append(ns)
                    st.rerun()
                
        ds_options = st.session_state.subcontractors if st.session_state.subcontractors else ["(尚無資料)"]
        ds = st.selectbox("選擇刪除廠商", ds_options, key="ds_sel", disabled=is_proj_closed)
        if st.button("刪除廠商", type="primary", disabled=is_proj_closed) and ds != "(尚無資料)":
            if not (st.session_state.tasks['施工廠商'] == ds).any():
                supabase.table("subcontractors").delete().eq("name", ds).eq("project_name", selected_project).execute()
                st.session_state.subcontractors.remove(ds)
                st.rerun()
            else: st.error("⚠️ 該廠商尚有任務")

safe_regions = st.session_state.regions if st.session_state.regions else ["未設定"]
safe_subcontractors = st.session_state.subcontractors if st.session_state.subcontractors else ["未設定"]

# ==========================================
# 5. 施工任務管理 (完美修正無幽靈欄位版)
# ==========================================
with st.expander("施工任務管理", expanded=True):
    
    for col in ['預定開始', '預定完成', '實際開始', '實際完成']:
        st.session_state.tasks[col] = pd.to_datetime(st.session_state.tasks[col], errors='coerce').dt.date
    st.session_state.tasks['是否為里程碑'] = st.session_state.tasks['是否為里程碑'].fillna(False).astype(bool)

    with st.form(key=f"form_tasks_{selected_project}"):
        st.subheader("1. 預定計畫")
        col_cfg_plan = {
            "區域": st.column_config.SelectboxColumn("區域", options=safe_regions, required=True),
            "施工項目": st.column_config.TextColumn("施工項目", required=True),
            "施工廠商": st.column_config.TextColumn("施工廠商 (複選請用逗號 , 分隔)", help="若有多個廠商，請使用半形逗號分隔，例如：廠商A, 廠商B", required=True),
            "預定開始": st.column_config.DateColumn("預定開始", format="MM/DD", required=True),
            "預定完成": st.column_config.DateColumn("預定完成", format="MM/DD", required=True),
            "是否為里程碑": st.column_config.CheckboxColumn("里程碑", default=False)
        }
        ed_plan = st.data_editor(st.session_state.tasks[['區域', '施工項目', '施工廠商', '預定開始', '預定完成', '是否為里程碑']], column_config=col_cfg_plan, num_rows="dynamic", use_container_width=True, disabled=is_proj_closed, key=f"ed_plan_state_{selected_project}")

        st.subheader("2. 實際進度回報")
        col_cfg_act = {
            "施工項目": st.column_config.TextColumn("施工項目", disabled=True),
            "實際開始": st.column_config.DateColumn("實際開工", format="MM/DD"),
            "實際完成": st.column_config.DateColumn("實際完成", format="MM/DD"),
            "完成度(%)": st.column_config.NumberColumn("完成度 (%)", min_value=0, max_value=100, step=10, format="%d %%")
        }

        act_sync = st.session_state.tasks[['區域', '施工項目', '施工廠商']].copy()

        if not st.session_state.tasks.empty:
            mapping_keys = ['區域', '施工項目', '施工廠商']
            mapping_df = st.session_state.tasks[mapping_keys + ['實際開始', '實際完成', '完成度(%)']].drop_duplicates(subset=mapping_keys)
            act_sync = act_sync.reset_index().merge(mapping_df, on=mapping_keys, how='left').set_index('index')
        else:
            act_sync['實際開始'] = None
            act_sync['實際完成'] = None
            act_sync['完成度(%)'] = 0

        # 精準切回 4 欄，完全排除幽靈欄位
        act_sync = act_sync[['施工項目', '實際開始', '實際完成', '完成度(%)']]
        act_sync['完成度(%)'] = act_sync['完成度(%)'].fillna(0).astype(int)
        
        act_sync['實際開始'] = act_sync['實際開始'].apply(lambda x: x if pd.notnull(x) else None)
        act_sync['實際完成'] = act_sync['實際完成'].apply(lambda x: x if pd.notnull(x) else None)

        ed_act = st.data_editor(act_sync, column_config=col_cfg_act, num_rows="fixed", use_container_width=True, disabled=is_proj_closed, key=f"ed_act_state_{selected_project}")

        hist_key_t = f"tasks_hist_{selected_project}"
        can_undo_t = hist_key_t in st.session_state
        
        col_space, col_undo, col_save = st.columns([6, 2, 2])
        with col_undo:
            btn_undo_t = st.form_submit_button("↩️ 復原上一次儲存", disabled=is_proj_closed or not can_undo_t, use_container_width=True)
        with col_save:
            btn_save_t = st.form_submit_button("儲存並同步", type="primary", disabled=is_proj_closed, use_container_width=True)

        if btn_undo_t and can_undo_t:
            with st.spinner("復原資料中..."):
                clean_t = st.session_state[hist_key_t]
                try:
                    supabase.table("tasks").delete().eq("project_name", selected_project).execute()
                    if not clean_t.empty:
                        up_t = []
                        for _, r in clean_t.iterrows():
                            comp_val = r.get('完成度(%)', 0)
                            up_t.append({
                                "project_name": selected_project, 
                                "task_name": str(r['施工項目']), "subcontractor": str(r['施工廠商']), 
                                "start_date": safe_date(r['預定開始']), "end_date": safe_date(r['預定完成']), "region": str(r['區域']), 
                                "is_milestone": bool(r.get('是否為里程碑', False)), 
                                "actual_start": safe_date(r['實際開始']), "actual_end": safe_date(r['實際完成']), 
                                "completion": 0 if pd.isna(comp_val) or comp_val == "" else int(float(comp_val)), 
                                "remarks": "" if pd.isna(r.get('備註', '')) else str(r.get('備註', ''))
                            })
                        supabase.table("tasks").insert(up_t).execute()
                    
                    st.session_state.tasks = clean_t
                    del st.session_state[hist_key_t]
                    st.success("✅ 已完美復原至上一次的任務狀態！")
                    st.rerun()
                except Exception as e:
                    st.error(f"⚠️ 復原失敗: {e}")
            
        if btn_save_t:
            with st.spinner("資料同步中..."):
                st.session_state[hist_key_t] = st.session_state.tasks.copy() 
                
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
# 6. 試車任務管理 (復原上一步版)
# ==========================================
with st.expander("試車任務管理", expanded=True):
    
    for col in ['預定開始', '預定完成', '實際開始', '實際完成']:
        st.session_state.comm_tasks[col] = pd.to_datetime(st.session_state.comm_tasks[col], errors='coerce').dt.date
    st.session_state.comm_tasks['是否為里程碑'] = st.session_state.comm_tasks['是否為里程碑'].fillna(False).astype(bool)

    with st.form(key=f"form_comm_{selected_project}"):
        st.subheader("1. 預定計畫")
        col_cfg_c_plan = {
            "區域": st.column_config.SelectboxColumn("區域", options=safe_regions, required=True),
            "試車項目": st.column_config.TextColumn("試車項目", required=True),
            "預定開始": st.column_config.DateColumn("預定開始", format="MM/DD", required=True),
            "預定完成": st.column_config.DateColumn("預定完成", format="MM/DD", required=True),
            "是否為里程碑": st.column_config.CheckboxColumn("里程碑", default=False)
        }
        ed_c_plan = st.data_editor(st.session_state.comm_tasks[['區域', '試車項目', '預定開始', '預定完成', '是否為里程碑']], column_config=col_cfg_c_plan, num_rows="dynamic", use_container_width=True, disabled=is_proj_closed, key=f"ed_c_plan_state_{selected_project}")

        st.subheader("2. 實際進度回報")
        
        c_act_sync = st.session_state.comm_tasks[['區域', '試車項目']].copy()

        if not st.session_state.comm_tasks.empty:
            mapping_keys_c = ['區域', '試車項目']
            mapping_df_c = st.session_state.comm_tasks[mapping_keys_c + ['實際開始', '實際完成', '完成度(%)']].drop_duplicates(subset=mapping_keys_c)
            c_act_sync = c_act_sync.reset_index().merge(mapping_df_c, on=mapping_keys_c, how='left').set_index('index')
        else:
            c_act_sync['實際開始'] = None
            c_act_sync['實際完成'] = None
            c_act_sync['完成度(%)'] = 0

        c_act_sync = c_act_sync[['試車項目', '實際開始', '實際完成', '完成度(%)']]
        c_act_sync['完成度(%)'] = c_act_sync['完成度(%)'].fillna(0).astype(int)
        c_act_sync['實際開始'] = c_act_sync['實際開始'].apply(lambda x: x if pd.notnull(x) else None)
        c_act_sync['實際完成'] = c_act_sync['實際完成'].apply(lambda x: x if pd.notnull(x) else None)

        ed_c_act = st.data_editor(c_act_sync, column_config=col_cfg_act, num_rows="fixed", use_container_width=True, disabled=is_proj_closed, key=f"ed_c_act_state_{selected_project}")

        hist_key_c = f"comm_hist_{selected_project}"
        can_undo_c = hist_key_c in st.session_state
        
        col_space, col_undo, col_save = st.columns([6, 2, 2])
        with col_undo:
            btn_undo_c = st.form_submit_button("↩️ 復原上一次儲存", disabled=is_proj_closed or not can_undo_c, use_container_width=True)
        with col_save:
            btn_save_c = st.form_submit_button("儲存並同步", type="primary", disabled=is_proj_closed, use_container_width=True)

        if btn_undo_c and can_undo_c:
            with st.spinner("復原資料中..."):
                clean_c = st.session_state[hist_key_c]
                try:
                    supabase.table("commissioning_tasks").delete().eq("project_name", selected_project).execute()
                    if not clean_c.empty:
                        up_c = []
                        for _, r in clean_c.iterrows():
                            comp_val = r.get('完成度(%)', 0)
                            up_c.append({
                                "project_name": selected_project, 
                                "test_item": str(r['試車項目']), "start_date": safe_date(r['預定開始']), "end_date": safe_date(r['預定完成']), 
                                "region": str(r['區域']), "is_milestone": bool(r.get('是否為里程碑', False)), 
                                "actual_start": safe_date(r['實際開始']), "actual_end": safe_date(r['實際完成']), 
                                "completion": 0 if pd.isna(comp_val) or comp_val == "" else int(float(comp_val)), 
                                "remarks": "" if pd.isna(r.get('備註', '')) else str(r.get('備註', ''))
                            })
                        supabase.table("commissioning_tasks").insert(up_c).execute()
                    
                    st.session_state.comm_tasks = clean_c
                    del st.session_state[hist_key_c]
                    st.success("✅ 已完美復原至上一次的試車狀態！")
                    st.rerun()
                except Exception as e:
                    st.error(f"⚠️ 復原失敗: {e}")

        if btn_save_c:
            with st.spinner("資料同步中..."):
                st.session_state[hist_key_c] = st.session_state.comm_tasks.copy()
                
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
tab_g1, tab_g2 = st.tabs(["📊 施工進度圖表", "⚙️ 試車排程圖表"])

def draw_gantt(df, title, color_col):
    p_df = df.dropna(subset=[df.columns[1], '預定開始', '預定完成']).copy()
    if p_df.empty: return st.warning("請先輸入計畫資料")
    
    p_df['預定開始'] = pd.to_datetime(p_df['預定開始'])
    p_df['預定完成'] = pd.to_datetime(p_df['預定完成'])
    p_df['實際開始'] = pd.to_datetime(p_df['實際開始'], errors='coerce')
    p_df['實際完成'] = pd.to_datetime(p_df['實際完成'], errors='coerce')
    p_df = p_df.sort_values("預定開始")
    
    p_df['預定完成_繪圖'] = p_df['預定完成'] + pd.Timedelta(days=1)
    p_df['進度結束_繪圖'] = pd.NaT
    task_col = p_df.columns[1] 

    for idx, row in p_df.iterrows():
        if pd.notnull(row['實際完成']) and pd.notnull(row['預定完成']):
            if row['實際完成'] < row['預定完成']: 
                p_df.loc[idx, task_col] = f"[提前完工!] {row[task_col]}"
            elif row['實際完成'] > row['預定完成']: 
                p_df.loc[idx, task_col] = f"[Delay] {row[task_col]}"

        if pd.notnull(row['實際開始']):
            if pd.notnull(row['實際完成']):
                p_df.loc[idx, '進度結束_繪圖'] = row['實際完成'] + pd.Timedelta(days=1)
            else:
                planned_days = (row['預定完成'] - row['預定開始']).days + 1
                p_df.loc[idx, '進度結束_繪圖'] = row['實際開始'] + pd.Timedelta(days=planned_days * (row['完成度(%)'] / 100.0))
    
    color_map = {v: px.colors.qualitative.Plotly[i % 10] for i, v in enumerate(p_df[color_col].unique())}
    draw_df = p_df[~p_df['是否為里程碑']].copy()
    
    if draw_df.empty: return st.warning("⚠️ 至少需有一項非里程碑任務")
        
    draw_df['預定開始_str'] = draw_df['預定開始'].dt.strftime('%Y-%m-%d')
    draw_df['預定完成_str'] = draw_df['預定完成'].dt.strftime('%Y-%m-%d')
    
    fig = px.timeline(draw_df, x_start="預定開始", x_end="預定完成_繪圖", y=task_col, color=color_col, color_discrete_map=color_map, height=400+len(p_df)*30, custom_data=['預定開始_str', '預定完成_str'])
    fig.update_traces(opacity=0.3, hovertemplate="<b>%{y}</b><br>預定區間: %{customdata[0]} ~ %{customdata[1]}<extra></extra>")
    
    prog_df = draw_df.dropna(subset=['實際開始', '進度結束_繪圖']).copy()
    if not prog_df.empty:
        prog_df['實際開始_str'] = prog_df['實際開始'].dt.strftime('%Y-%m-%d')
        prog_df['實際完成_str'] = prog_df['實際完成'].dt.strftime('%Y-%m-%d').fillna('進行中')
        prog_df['完成度_str'] = prog_df['完成度(%)'].astype(str) + '%'
        
        fig2 = px.timeline(prog_df, x_start="實際開始", x_end="進度結束_繪圖", y=task_col, color=color_col, color_discrete_map=color_map, custom_data=['實際開始_str', '實際完成_str', '完成度_str'])
        fig2.update_traces(opacity=1.0, marker_pattern_shape="/", hovertemplate="<b>%{y} (實際)</b><br>實際區間: %{customdata[0]} ~ %{customdata[1]}<br>目前進度: %{customdata[2]}<extra></extra>") 
        for tr in fig2.data: tr.showlegend = False; fig.add_trace(tr)
            
    fig.update_layout(barmode='overlay') 
    
    ms_leg_set = set() 
    for _, m in p_df[p_df['是否為里程碑']].iterrows():
        cat = m[color_col]
        region = m['區域']
        is_done = pd.notnull(m['實際完成'])
        
        leg_name = f"{cat}(完成)" if is_done else f"{cat}"
        show_leg = leg_name not in ms_leg_set
        if show_leg: ms_leg_set.add(leg_name)
        
        vendor_info = f"<br>廠商: {m['施工廠商']}" if '施工廠商' in m else ""
        hover_text = f"<b>里程碑：{m[task_col]}</b><br>區域: {region}{vendor_info}<br>日期: {m['預定開始'].strftime('%Y-%m-%d')}<extra></extra>"
        
        if is_done:
            fig.add_trace(go.Scatter(
                x=[m['實際完成'] + pd.Timedelta(hours=12)], y=[m[task_col]], mode='text', 
                text=[f"✅ {m['實際完成'].strftime('%m/%d')}"], textfont=dict(color='green', size=16, weight='bold'), 
                name=leg_name, legendgroup=leg_name, showlegend=show_leg, hovertemplate=hover_text
            ))
        else:
            fig.add_trace(go.Scatter(
                x=[m['預定開始'] + pd.Timedelta(hours=12)], y=[m[task_col]], mode='markers+text', 
                marker=dict(symbol='star', size=18, color=color_map.get(cat, 'gray'), line=dict(color='black', width=1)), 
                text=[f" {m['預定開始'].strftime('%m/%d')}"], textposition='middle right', textfont=dict(color='black', size=12), 
                name=leg_name, legendgroup=leg_name, showlegend=show_leg, hovertemplate=hover_text
            ))

    if is_proj_closed and st.session_state.get('closed_date'):
        closed_ts = pd.to_datetime(st.session_state.closed_date)
        fig.add_vline(x=closed_ts, line_width=2, line_dash="dash", line_color="gray", layer="above")
        fig.add_annotation(x=closed_ts, y=1, yref="paper", yanchor="bottom", text="結案日", showarrow=False, font=dict(color="gray", size=14))
    else:
        today = pd.Timestamp.now(tz='Asia/Taipei').normalize()
        fig.add_vline(x=today, line_width=2, line_dash="dash", line_color="red", layer="above")
        fig.add_annotation(x=today, y=1, yref="paper", yanchor="bottom", text="今日", showarrow=False, font=dict(color="red", size=14))

    fig.update_yaxes(categoryorder='array', categoryarray=p_df[task_col].tolist(), autorange="reversed", showgrid=True, gridcolor='black', tickfont=dict(color="black", size=14))
    
    fig.update_xaxes(
        showgrid=True, 
        gridcolor='black', 
        tickformat="%m/%d", 
        dtick="D1", 
        ticklabelmode="period", 
        tickfont=dict(color="black", size=12)
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False, 'modeBarButtonsToRemove': ['lasso2d', 'select2d']})

with tab_g1:
    v_mode = st.radio("分類維度：", ["區域", "施工廠商"], horizontal=True, key="mode_const")
    
    plot_df = st.session_state.tasks.copy()
    all_vendors = set()
    if not plot_df.empty:
        for v in plot_df['施工廠商'].dropna():
            for sub_v in str(v).replace('，', ',').split(','):
                if sub_v.strip(): all_vendors.add(sub_v.strip())
                
    selected_vendors = st.multiselect("🔍 篩選顯示特定廠商 (留空代表顯示全部)：", list(all_vendors), key=f"v_filter_{selected_project}")
    
    if selected_vendors:
        def check_vendor(task_vendors_str):
            if not task_vendors_str: return False
            task_v_list = [v.strip() for v in str(task_vendors_str).replace('，', ',').split(',')]
            return any(v in task_v_list for v in selected_vendors)
        plot_df = plot_df[plot_df['施工廠商'].apply(check_vendor)]

    draw_gantt(plot_df, f"{selected_project} - 施工圖", v_mode)

with tab_g2:
    draw_gantt(st.session_state.comm_tasks, f"{selected_project} - 試車圖", "區域")

# ==========================================
# 8. 動態備註與每日日誌系統 (型態防禦與安全淨化版)
# ==========================================
st.divider()
st.subheader("施工日誌")
c1, c2 = st.columns([1, 1])

# 💡 安全機制 1：全自動強轉日期型態函數，阻斷任何與資料庫的比對錯誤
def to_safe_date(d):
    if pd.isnull(d) or d == "": return None
    if isinstance(d, datetime.date): return d
    try:
        return pd.to_datetime(d).date()
    except:
        return None

with c1:
    st.markdown("##### 每日施工日誌")
    
    date_state_key = f"current_date_{selected_project}"
    if date_state_key not in st.session_state:
        st.session_state[date_state_key] = datetime.date.today()
    
    raw_dates = []
    try:
        res_logged = supabase.table("daily_logs").select("log_date").eq("project_name", selected_project).order("log_date").execute()
        if res_logged.data:
            raw_dates = sorted(list(set([d['log_date'] for d in res_logged.data])))
    except Exception:
        pass

    if raw_dates:
        st.markdown("**快速跳轉出工日期：**")
        cols_date = st.columns(len(raw_dates) if len(raw_dates) < 8 else 8)
        for idx, date_str in enumerate(raw_dates):
            c_target = cols_date[idx % 8]
            d_obj = to_safe_date(date_str)
            if d_obj:
                display_str = d_obj.strftime('%m/%d')
                btn_type = "primary" if d_obj == st.session_state[date_state_key] else "secondary"
                with c_target:
                    if st.button(display_str, key=f"btn_jump_{selected_project}_{date_str}", type=btn_type, use_container_width=True):
                        st.session_state[date_state_key] = d_obj
                        st.rerun()
        st.write("") 

    log_date = st.date_input("選擇日期：", key=date_state_key)
    safe_log_date = to_safe_date(log_date)

    active_tasks = []
    if not st.session_state.tasks.empty and safe_log_date:
        for _, r in st.session_state.tasks.iterrows():
            start = to_safe_date(r['實際開始'] if pd.notnull(r['實際開始']) else r['預定開始'])
            end = to_safe_date(r['實際完成'] if pd.notnull(r['實際完成']) else r['預定完成'])
            
            if start and end:
                if start <= safe_log_date <= end:
                    active_tasks.append(str(r['施工項目']))
            elif start and start == safe_log_date: 
                active_tasks.append(str(r['施工項目']))

    if active_tasks:
        st.info(f"**本日施工項目：** {', '.join(active_tasks)}")

    existing_log_raw = ""
    try:
        res_log = supabase.table("daily_logs").select("content").eq("project_name", selected_project).eq("log_date", str(safe_log_date)).execute()
        if res_log.data:
            existing_log_raw = res_log.data[0]['content']
    except Exception:
        pass
        
    parsed_logs = {}
    if existing_log_raw:
        try:
            parsed_logs = json.loads(existing_log_raw)
            if not isinstance(parsed_logs, dict):
                parsed_logs = {"綜合": existing_log_raw}
        except json.JSONDecodeError:
            parsed_logs = {"綜合": existing_log_raw}

    sub_list = st.session_state.subcontractors if st.session_state.subcontractors else []
    
    # 💡 將複選逗號拆開為獨立廠商，擴充為動態日誌頁籤
    expanded_subs = []
    if not st.session_state.tasks.empty:
        for v_str in st.session_state.tasks['施工廠商'].dropna():
            for v in str(v_str).replace('，', ',').split(','):
                if v.strip() and v.strip() not in expanded_subs:
                    expanded_subs.append(v.strip())
                    
    all_keys = ["綜合"] + expanded_subs + sub_list + list(parsed_logs.keys())
    
    # 💡 安全機制 2：全面淨化頁籤，濾除空值、重複值及無效型態，徹底防範 st.tabs 崩潰
    tab_names = []
    for k in all_keys:
        if k and str(k).strip() and str(k).strip() not in tab_names:
            tab_names.append(str(k).strip())

    tabs = st.tabs(tab_names)
    current_inputs = {}

    for i, t_name in enumerate(tab_names):
        with tabs[i]:
            val = parsed_logs.get(t_name, "")
            current_inputs[t_name] = st.text_area(
                f"📝 【{t_name}】本日施工內容：", 
                value=val, 
                height=150, 
                key=f"txt_log_{selected_project}_{safe_log_date}_{t_name}", 
                disabled=is_proj_closed
            )
    
    if st.button("儲存施工日誌", key=f"save_t_{selected_project}", use_container_width=True, disabled=is_proj_closed):
        final_logs = {k: v.strip() for k, v in current_inputs.items() if v.strip()}
        
        try:
            supabase.table("daily_logs").delete().eq("project_name", selected_project).eq("log_date", str(safe_log_date)).execute()
            
            if final_logs:
                json_str = json.dumps(final_logs, ensure_ascii=False)
                supabase.table("daily_logs").insert({
                    "project_name": selected_project, 
                    "log_date": str(safe_log_date), 
                    "content": json_str
                }).execute()
                
            st.success(f"✅ {safe_log_date} 施工日誌已依照廠商分類同步至雲端！")
            st.rerun() 
        except Exception as e:
            st.error(f"寫入失敗: {e}")

with c2:
    st.markdown("##### 試車項目備註")
    comm_opts = st.session_state.comm_tasks['試車項目'].dropna().unique().tolist()
    if comm_opts:
        sel_c = st.selectbox("選擇試車項目：", comm_opts, key=f"sel_note_c_{selected_project}")
        if sel_c:
            row_c = st.session_state.comm_tasks[st.session_state.comm_tasks['試車項目'] == sel_c].iloc[0]
            new_note_c = st.text_area(f"【{sel_c}】備註：", value=row_c.get('備註', ''), height=150, key=f"txt_c_{selected_project}_{sel_c}", disabled=is_proj_closed)
            
            if st.button("儲存試車備註", key=f"save_c_{selected_project}", use_container_width=True, disabled=is_proj_closed):
                st.session_state.comm_tasks.loc[st.session_state.comm_tasks['試車項目'] == sel_c, '備註'] = new_note_c
                try:
                    supabase.table("commissioning_tasks").update({"remarks": new_note_c}).eq("test_item", sel_c).eq("project_name", selected_project).execute()
                    st.success("✅ 試車備註已同步至雲端！")
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
    bn = st.text_input("存檔名稱", key="bn_in", disabled=is_proj_closed)
    if construction_button("立即存檔", key="btn_save_snap", disabled=is_proj_closed):
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
            if st.button("確認回復", use_container_width=True, key="btn_restore", disabled=is_proj_closed):
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
            if st.button("刪除存檔", type="primary", use_container_width=True, key="btn_del_snap", disabled=is_proj_closed):
                supabase.table("tasks_backups").delete().eq("id", opts[sel_b]).execute()
                st.rerun()

# ==========================================
# 10. 魔法變色系統 (JavaScript 強制渲染)
# ==========================================
components.html(
    """
    <script>
    const doc = window.parent.document;
    const styleButtons = () => {
        const buttons = doc.querySelectorAll('.stButton button');
        buttons.forEach(btn => {
            const text = btn.innerText;
            if (text.includes('儲存施工') || text.includes('加入區域') || text.includes('加入廠商') || text.includes('立即存檔')) {
                btn.style.backgroundColor = '#003366';
                btn.style.color = '#FFFFFF';
                btn.style.border = 'none';
            } 
            else if (text.includes('LINE') || text.includes('儲存試車')) {
                btn.style.backgroundColor = '#1B5E20';
                btn.style.color = '#FFFFFF';
                btn.style.border = 'none';
            }
        });
    };
    styleButtons();
    const observer = new MutationObserver(styleButtons);
    observer.observe(doc.body, { childList: true, subtree: true });
    </script>
    """,
    height=0,
    width=0,
)

# ==========================================
# 12. 專案檔案上傳區 (支援一鍵清除與多檔案)
# ==========================================
def encode_safe(text, is_file=False):
    prefix = re.sub(r'[^a-zA-Z0-9]', '_', text)
    prefix = re.sub(r'_+', '_', prefix).strip('_')
    if not prefix: prefix = "Item"
    b64_part = base64.urlsafe_b64encode(text.encode('utf-8')).decode('utf-8').rstrip('=')
    if is_file and "." in text:
        ext = text.split(".")[-1]
        return f"{prefix}__b64__{b64_part}.{ext}"
    return f"{prefix}__b64__{b64_part}"

def decode_safe(safe_name):
    if "__b64__" in safe_name:
        core_part = safe_name.rsplit(".", 1)[0] if "." in safe_name else safe_name
        b64_part = core_part.split("__b64__")[-1]
        pad = '=' * (4 - (len(b64_part) % 4))
        try:
            return base64.urlsafe_b64decode((b64_part + pad).encode('utf-8')).decode('utf-8')
        except:
            pass
    return safe_name

st.divider()
st.subheader("工程資料夾")

if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0

c_cat, c_up = st.columns([1, 2])
with c_cat:
    custom_category = st.text_input("輸入檔案分類：", placeholder="例如：設計圖、試車報告...", disabled=is_proj_closed)
    final_category = custom_category.strip() if custom_category.strip() else "未分類"

with c_up:
    uploaded_files = st.file_uploader(
        f"上傳【{selected_project} - {final_category}】的檔案：", 
        disabled=is_proj_closed, 
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.uploader_key}" 
    )

if uploaded_files:
    col_info, col_clear = st.columns([3, 1])
    with col_clear:
        if st.button("清除檔案", use_container_width=True):
            st.session_state.uploader_key += 1 
            st.rerun()
            
    with col_info:
        total_size = sum([f.size for f in uploaded_files]) / 1024
        st.info(f"準備上傳：共 {len(uploaded_files)} 個檔案 (總大小 {total_size:.1f} KB)")
    
    if st.button("確認上傳", type="primary", use_container_width=True, disabled=is_proj_closed):
        with st.spinner("檔案上傳中..."):
            success_count = 0
            for file in uploaded_files:
                try:
                    file_bytes = file.getvalue()
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
                    
                    enc_folder = encode_safe(selected_project)
                    enc_cat = encode_safe(final_category)
                    enc_name = encode_safe(file.name, is_file=True)
                    
                    raw_path = f"{enc_cat}__time__{timestamp}__{enc_name}"
                    
                    fd, tmp_path = tempfile.mkstemp()
                    with os.fdopen(fd, 'wb') as f:
                        f.write(file_bytes)
                    
                    res = supabase.storage.from_("project_files").upload(
                        path=f"{enc_folder}/{raw_path}",
                        file=tmp_path,
                        file_options={"content-type": file.type}
                    )
                    success_count += 1
                except Exception as e:
                    st.error(f"❌ 【{file.name}】上傳失敗: {e}")
                finally:
                    if 'tmp_path' in locals() and os.path.exists(tmp_path):
                        os.remove(tmp_path)
            
            if success_count > 0:
                st.success(f"✅ 成功上傳 {success_count} 個檔案！")
                st.session_state.uploader_key += 1 
                st.balloons()
                st.rerun() 

# ==========================================
# 13. 專案檔案展示區 (資源回收桶復原版)
# ==========================================
st.divider()

try:
    enc_folder = encode_safe(selected_project)
    file_list = supabase.storage.from_("project_files").list(enc_folder)
    
    with st.form("file_manager_form"):
        
        hist_key_f = f"files_hist_{selected_project}"
        can_undo_f = hist_key_f in st.session_state
        
        col_title, col_undo, col_batch_btn = st.columns([4, 2, 2])
        with col_title:
            st.subheader(f"【{selected_project}】檔案列表")
        with col_undo:
            btn_undo_f = st.form_submit_button("↩️ 復原剛刪除的檔案", disabled=is_proj_closed or not can_undo_f, use_container_width=True)
        with col_batch_btn:
            submitted = st.form_submit_button("刪除已選檔案", type="primary", disabled=is_proj_closed, use_container_width=True)

        files_to_delete = []
        
        valid_files = [f for f in (file_list or []) if isinstance(f, dict) and f.get('name') and f.get('name') != '.emptyFolderPlaceholder' and not f.get('name').endswith('.trash')]
        
        if not valid_files:
            st.info("尚無上傳任何有效檔案。")
        else:
            categorized_files = {}
            for f in valid_files:
                fname = f.get('name', '')
                parts = fname.split("__time__")
                if len(parts) >= 2:
                    cat = decode_safe(parts[0])
                    time_and_name = parts[1].split("__", 1)
                    actual_name = decode_safe(time_and_name[1]) if len(time_and_name) > 1 else decode_safe(parts[1])
                else:
                    cat = "未分類檔案"
                    actual_name = decode_safe(fname)
                    
                if cat not in categorized_files: categorized_files[cat] = []
                    
                safe_fname = urllib.parse.quote(actual_name)
                public_url = f"{st.secrets['SUPABASE_URL'].rstrip('/')}/storage/v1/object/public/project_files/{enc_folder}/{urllib.parse.quote(fname)}?download={safe_fname}"
                
                categorized_files[cat].append({
                    "name": actual_name,
                    "url": public_url,
                    "created_at": f.get("created_at", "")[:10],
                    "raw_name": fname
                })
            
            if categorized_files:
                tabs = st.tabs(list(categorized_files.keys()))
                for i, (cat, files) in enumerate(categorized_files.items()):
                    with tabs[i]:
                        for file_info in files:
                            col_chk, col_file = st.columns([0.5, 9.5])
                            with col_chk:
                                is_checked = st.checkbox("選取", key=f"chk_{file_info['raw_name']}", disabled=is_proj_closed, label_visibility="collapsed")
                                if is_checked:
                                    files_to_delete.append(f"{enc_folder}/{file_info['raw_name']}")
                            with col_file:
                                st.markdown(f"📄 **[{file_info['name']}]({file_info['url']})** *(上傳於: {file_info['created_at']})*")
            else:
                st.info("資料夾中無有效檔案。")

        if btn_undo_f and can_undo_f:
            with st.spinner("正在救援檔案..."):
                try:
                    for f_path in st.session_state[hist_key_f]:
                        supabase.storage.from_("project_files").move(f"{f_path}.trash", f_path)
                    
                    del st.session_state[hist_key_f]
                    st.toast("✅ 檔案救援成功！已全部復原。")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 救援失敗: {e}")

        if submitted:
            if files_to_delete:
                with st.spinner(f"正在將 {len(files_to_delete)} 個檔案移至垃圾桶..."):
                    try:
                        for f_path in files_to_delete:
                            supabase.storage.from_("project_files").move(f_path, f"{f_path}.trash")
                        
                        st.session_state[hist_key_f] = files_to_delete
                        st.toast(f"✅ 已刪除 {len(files_to_delete)} 個檔案！(若誤刪可點擊右上角復原)")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 刪除失敗: {e}")
            else:
                st.warning("⚠️ 請先在下方勾選要刪除的檔案！")

except Exception as e:
    st.info("尚無上傳任何檔案或找不到專案資料夾。")
