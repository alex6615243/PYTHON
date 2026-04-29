import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
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
def load_data():
    res = supabase.table("tasks").select("*").execute()
    df = pd.DataFrame(res.data)
    cols = ['工作項目', '開始時間', '完成時間', '區域', '施工廠商', '是否為里程碑']
    
    if not df.empty:
        df = df.rename(columns={
            'task_name': '工作項目', 'start_date': '開始時間',
            'end_date': '完成時間', 'region': '區域',
            'subcontractor': '施工廠商', 'is_milestone': '是否為里程碑'
        })
        # 🛡️ 關鍵：對齊日期格式為 datetime.date
        df['開始時間'] = pd.to_datetime(df['開始時間']).dt.date
        df['完成時間'] = pd.to_datetime(df['完成時間']).dt.date
        df['是否為里程碑'] = df['是否為里程碑'].fillna(False).astype(bool)
        return df[cols]
    
    empty_df = pd.DataFrame(columns=cols)
    empty_df['是否為里程碑'] = empty_df['是否為里程碑'].astype(bool)
    return empty_df

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
st.set_page_config(layout="wide", page_title="營建工程規劃系統")

if 'tasks' not in st.session_state:
    st.session_state.tasks = load_data()
if 'regions' not in st.session_state:
    st.session_state.regions = load_list("regions")
if 'subcontractors' not in st.session_state:
    st.session_state.subcontractors = load_list("subcontractors")
if 'project_name' not in st.session_state:
    st.session_state.project_name = load_project_name()

st.title("🏢 營建工程進度規劃系統")

# 專案名稱同步
new_proj_name = st.text_input("📌 專案名稱：", value=st.session_state.project_name)
if new_proj_name != st.session_state.project_name:
    supabase.table("project_config").upsert({"id": 1, "project_name": new_proj_name}).execute()
    st.session_state.project_name = new_proj_name
    st.toast("專案名稱已更新", icon="📝")

# ==========================================
# 4. 側邊欄管理 (區域與廠商)
# ==========================================
st.sidebar.header("⚙️ 基礎資料管理")

with st.sidebar.expander("📍 區域管理", expanded=False):
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

with st.sidebar.expander("👷 廠商管理", expanded=False):
    t3, t4 = st.tabs(["➕ 新增", "🗑️ 刪除"])
    with t3:
        ns = st.text_input("新增廠商", key="ns_in")
        if st.button("加入廠商"):
            if ns and ns not in st.session_state.subcontractors:
                supabase.table("subcontractors").insert({"name": ns}).execute()
                st.session_state.subcontractors.append(ns)
                st.rerun()
    with t4:
        ds = st.selectbox("選擇刪除廠商", st.session_state.subcontractors)
        if st.button("刪除廠商"):
            if not (st.session_state.tasks['施工廠商'] == ds).any():
                supabase.table("subcontractors").delete().eq("name", ds).execute()
                st.session_state.subcontractors.remove(ds)
                st.rerun()
            else: st.error("尚有任務使用此廠商")

# ==========================================
# 5. 新增工作項目
# ==========================================
st.sidebar.divider()
st.sidebar.header("➕ 新增工作項目")
with st.sidebar.form("add_form"):
    tn = st.text_input("項目名稱")
    rg = st.selectbox("歸屬區域", st.session_state.regions)
    sc = st.selectbox("負責廠商", st.session_state.subcontractors)
    c1, c2 = st.columns(2)
    sd = c1.date_input("開始")
    ed = c2.date_input("結束")
    im = st.checkbox("里程碑")
    if st.form_submit_button("確認新增"):
        if tn:
            supabase.table("tasks").insert({
                "task_name": tn, "start_date": sd.isoformat(),
                "end_date": sd.isoformat() if im else ed.isoformat(),
                "region": rg, "subcontractor": sc, "is_milestone": im
            }).execute()
            st.session_state.tasks = load_data()
            st.rerun()

# ==========================================
# 6. 主畫面表格與【嚴格驗證】邏輯
# ==========================================
st.subheader("📋 工程任務清單")

# 設置表格下拉選單
col_cfg = {
    "區域": st.column_config.SelectboxColumn("區域", options=st.session_state.regions, required=True),
    "施工廠商": st.column_config.SelectboxColumn("施工廠商", options=st.session_state.subcontractors, required=True),
    "開始時間": st.column_config.DateColumn("開始時間", required=True),
    "完成時間": st.column_config.DateColumn("完成時間", required=True),
    "是否為里程碑": st.column_config.CheckboxColumn("里程碑？", default=False)
}

edited_df = st.data_editor(
    st.session_state.tasks, column_config=col_cfg,
    num_rows="dynamic", use_container_width=True, key="main_editor"
)

# 儲存與同步邏輯
if not edited_df.equals(st.session_state.tasks):
    # 1. 濾掉空白列
    clean_df = edited_df.dropna(subset=['工作項目', '開始時間', '完成時間']).copy()
    
    # 2. 嚴格驗證
    invalid = []
    for i, r in clean_df.iterrows():
        if str(r['區域']) not in st.session_state.regions or str(r['施工廠商']) not in st.session_state.subcontractors:
            invalid.append(f"第 {i+1} 列名稱不合法")
            
    if invalid:
        st.error(f"🚫 同步攔截：{', '.join(invalid)}")
    elif edited_df.empty and not st.session_state.tasks.empty:
        st.warning("⚠️ 防止意外全刪，自動同步已關閉")
    else:
        try:
            upload = []
            for _, r in clean_df.iterrows():
                upload.append({
                    "task_name": str(r['工作項目']),
                    "start_date": r['開始時間'].isoformat() if hasattr(r['開始時間'], 'isoformat') else str(r['開始時間']),
                    "end_date": r['完成時間'].isoformat() if hasattr(r['完成時間'], 'isoformat') else str(r['完成時間']),
                    "region": str(r['區域']), "subcontractor": str(r['施工廠商']),
                    "is_milestone": bool(r['是否為里程碑'])
                })
            supabase.table("tasks").delete().neq("id", -1).execute()
            if upload: supabase.table("tasks").insert(upload).execute()
            st.session_state.tasks = edited_df
            st.toast("💾 同步成功")
        except Exception as e: st.error(f"同步失敗：{e}")

# ==========================================
# 7. 多維度甘特圖生成 (日期格式：月/日 版)
# ==========================================
st.divider()
target = st.radio("📊 分類維度：", ["依區域", "依施工廠商"], horizontal=True)

if st.button("🌟 生成互動式甘特圖", type="primary"):
    p_df = edited_df.dropna(subset=['工作項目', '開始時間', '完成時間']).copy()
    
    if not p_df.empty:
        try:
            # 1. 數據格式轉換
            p_df['開始時間'] = pd.to_datetime(p_df['開始時間'])
            p_df['完成時間'] = pd.to_datetime(p_df['完成時間'])
            p_df['繪圖結束'] = p_df['完成時間'] + pd.Timedelta(days=1)
            
            color_col = "區域" if target == "依區域" else "施工廠商"
            p_df['是否為里程碑'] = p_df['是否為里程碑'].fillna(False).astype(bool)
            
            # 2. 🚀 核心排序：依日期先後整隊
            p_df = p_df.sort_values("開始時間")
            
            # 3. 建立顏色映射
            unique_vals = p_df[color_col].unique()
            color_map = {v: px.colors.qualitative.Plotly[i % 10] for i, v in enumerate(unique_vals)}
            
            # 4. 繪製主圖 (長條圖)
            fig = px.timeline(
                p_df[~p_df['是否為里程碑']], 
                x_start="開始時間", x_end="繪圖結束", y="工作項目", 
                color=color_col, color_discrete_map=color_map, 
                height=400 + len(p_df) * 30
            )
            
            # 5. 處理里程碑星星
            leg_set = set(p_df[~p_df['是否為里程碑']][color_col].unique())
            for _, m in p_df[p_df['是否為里程碑']].iterrows():
                curr_cat = m[color_col]
                show_leg = curr_cat not in leg_set
                if show_leg: leg_set.add(curr_cat)
                
                fig.add_trace(go.Scatter(
                    x=[m['開始時間']], y=[m['工作項目']], mode='markers+text',
                    marker=dict(symbol='star', size=18, color=color_map.get(curr_cat, 'gray'), line=dict(color='black', width=1)),
                    # 💡 關鍵修正：里程碑日期改為「月/日」
                    text=[f" {m['開始時間'].strftime('%m/%d')}"], 
                    textposition='middle right',
                    textfont=dict(color='black', size=12),
                    name=curr_cat, legendgroup=curr_cat, showlegend=show_leg
                ))
            
            # 6. 今日紅線
            try:
                today = pd.Timestamp.now(tz='Asia/Taipei')
            except:
                today = pd.Timestamp.now()
            fig.add_vline(x=today, line_width=2, line_dash="dash", line_color="red", layer="above")
            fig.add_annotation(x=today, y=1, yref="paper", yanchor="bottom", text="今日", showarrow=False, font=dict(color="red", size=14))

            # 7. 強制樣式設定：黑字、黑線、月/日格式
            fig.update_yaxes(
                categoryorder='array', 
                categoryarray=p_df['工作項目'].tolist(), 
                autorange="reversed",
                showgrid=True, gridcolor='black',      # 黑色橫向格線
                tickfont=dict(color="black", size=14)
            )
            
            fig.update_xaxes(
                showgrid=True, gridcolor='black',      # 黑色縱向格線
                # 💡 關鍵修正：X 軸日期格式改為「月/日」
                tickformat="%m/%d",
                dtick="D1",                            # 每一天顯示一個刻度
                tickfont=dict(color="black", size=12)
            )

            fig.update_layout(
                title=dict(text=f"{st.session_state.project_name} - 進度總表", font=dict(color="black", size=22)),
                font=dict(color="black"),
                plot_bgcolor="#f0f0f0",                 # 淺灰底色，增加對比
                paper_bgcolor="#f0f0f0",
                legend=dict(font=dict(color="black")),
                margin=dict(l=20, r=20, t=70, b=20)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"繪圖發生錯誤：{e}")
          
# 8. 系統備份與回復
# ==========================================
st.sidebar.divider()
with st.sidebar.expander("💾 備份與回復"):
    csv = st.session_state.tasks.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下載 CSV", data=csv, file_name="backup.csv", use_container_width=True)
    
    bn = st.text_input("備份名稱", key="bn_in")
    if st.button("🚀 建立雲端備份", use_container_width=True):
        js = st.session_state.tasks.to_json(orient='records', date_format='iso')
        supabase.table("tasks_backups").insert({"backup_name": bn, "data_json": js}).execute()
        st.toast("備份成功")
        st.rerun()

    res_b = supabase.table("tasks_backups").select("id", "backup_time", "backup_name").order("backup_time", desc=True).execute()
    if res_b.data:
        opts = {f"{i['backup_time'][5:16]} - {i['backup_name']}": i['id'] for i in res_b.data}
        sel_b = st.selectbox("選擇儲存點", options=list(opts.keys()))
        c1, c2 = st.columns(2)
        if c1.button("🔥 回復", use_container_width=True):
            snap = supabase.table("tasks_backups").select("data_json").eq("id", opts[sel_b]).execute()
            r_df = pd.read_json(io.StringIO(snap.data[0]['data_json']))
            supabase.table("tasks").delete().neq("id", -1).execute()
            up = []
            for _, r in r_df.iterrows():
                up.append({"task_name": str(r['工作項目']), "start_date": pd.to_datetime(r['開始時間']).isoformat(),
                           "end_date": pd.to_datetime(r['完成時間']).isoformat(), "region": r['區域'],
                           "subcontractor": r['施工廠商'], "is_milestone": bool(r['是否為里程碑'])})
            if up: supabase.table("tasks").insert(up).execute()
            st.session_state.tasks = load_data()
            st.rerun()
        if c2.button("🗑️ 刪除", use_container_width=True):
            supabase.table("tasks_backups").delete().eq("id", opts[sel_b]).execute()
            st.rerun()
