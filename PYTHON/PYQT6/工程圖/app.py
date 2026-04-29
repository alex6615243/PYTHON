import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
from supabase import create_client, Client

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
    if not df.empty:
        df = df.rename(columns={
            'task_name': '工作項目',
            'start_date': '開始時間',
            'end_date': '完成時間',
            'region': '區域',
            'subcontractor': '施工廠商',
            'is_milestone': '是否為里程碑'
        })
        df['開始時間'] = pd.to_datetime(df['開始時間'])
        df['完成時間'] = pd.to_datetime(df['完成時間'])
        cols = ['工作項目', '開始時間', '完成時間', '區域', '施工廠商', '是否為里程碑']
        return df[cols]
    return pd.DataFrame(columns=['工作項目', '開始時間', '完成時間', '區域', '施工廠商', '是否為里程碑'])

def load_list(table_name):
    res = supabase.table(table_name).select("name").execute()
    return [item['name'] for item in res.data] if res.data else ["未設定"]

def load_project_name():
    try:
        res = supabase.table("project_config").select("project_name").eq("id", 1).execute()
        return res.data[0]['project_name'] if res.data else "新工程案"
    except:
        return "新工程案"

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
    tab_reg_add, tab_reg_del = st.tabs(["➕ 新增", "🗑️ 刪除"])
    with tab_reg_add:
        new_reg = st.text_input("新增區域名稱", key="new_reg_input")
        if st.button("加入區域", use_container_width=True):
            if new_reg and new_reg not in st.session_state.regions:
                supabase.table("regions").insert({"name": new_reg}).execute()
                st.session_state.regions.append(new_reg)
                st.toast(f"✅ 區域「{new_reg}」已新增！", icon="📍")
                st.rerun()
    with tab_reg_del:
        del_reg = st.selectbox("選擇要刪除的區域", st.session_state.regions, key="del_reg_sel")
        if st.button("刪除區域", type="primary", use_container_width=True):
            if (st.session_state.tasks['區域'] == del_reg).any():
                st.error(f"⚠️ 無法刪除！該區域尚有任務。")
            else:
                supabase.table("regions").delete().eq("name", del_reg).execute()
                st.session_state.regions.remove(del_reg)
                st.rerun()

with st.sidebar.expander("👷 廠商管理", expanded=False):
    tab_sub_add, tab_sub_del = st.tabs(["➕ 新增", "🗑️ 刪除"])
    with tab_sub_add:
        new_sub = st.text_input("新增廠商名稱", key="new_sub_input")
        if st.button("加入廠商", use_container_width=True):
            if new_sub and new_sub not in st.session_state.subcontractors:
                supabase.table("subcontractors").insert({"name": new_sub}).execute()
                st.session_state.subcontractors.append(new_sub)
                st.toast(f"✅ 廠商「{new_sub}」已新增！", icon="👷")
                st.rerun()
    with tab_sub_del:
        del_sub = st.selectbox("選擇要刪除的廠商", st.session_state.subcontractors, key="del_sub_sel")
        if st.button("刪除廠商", type="primary", use_container_width=True):
            if (st.session_state.tasks['施工廠商'] == del_sub).any():
                st.error(f"⚠️ 無法刪除！該廠商尚有任務。")
            else:
                supabase.table("subcontractors").delete().eq("name", del_sub).execute()
                st.session_state.subcontractors.remove(del_sub)
                st.rerun()

# ==========================================
# 5. 新增工作項目
# ==========================================
st.sidebar.divider()
st.sidebar.header("➕ 新增工作項目")
with st.sidebar.form("add_task_form"):
    t_name = st.text_input("項目名稱")
    c_reg = st.selectbox("歸屬區域", st.session_state.regions)
    c_sub = st.selectbox("負責廠商", st.session_state.subcontractors)
    col1, col2 = st.columns(2)
    s_d = col1.date_input("開始日期")
    e_d = col2.date_input("結束日期")
    is_m = st.checkbox("設為里程碑")
    if st.form_submit_button("確認新增"):
        if t_name:
            new_task = {
                "task_name": t_name, "start_date": s_d.isoformat(),
                "end_date": s_d.isoformat() if is_m else e_d.isoformat(),
                "region": c_reg, "subcontractor": c_sub, "is_milestone": is_m
            }
            supabase.table("tasks").insert(new_task).execute()
            st.session_state.tasks = load_data()
            st.rerun()

# ==========================================
# 6. 主畫面表格與【嚴格驗證】存檔邏輯
# ==========================================
st.subheader("📋 工程任務清單")
edited_df = st.data_editor(
    st.session_state.tasks, 
    num_rows="dynamic", 
    use_container_width=True,
    key="main_editor"
)

if not edited_df.equals(st.session_state.tasks):
    # --- A. 數據初步清洗 ---
    # 濾掉還沒填完標題或日期的列 (這些不列入驗證範圍)
    clean_df = edited_df.dropna(subset=['工作項目', '開始時間', '完成時間']).copy()
    
    # --- B. 嚴格驗證檢查 ---
    # 找出所有不在名單內的名稱
    invalid_rows = []
    for index, row in clean_df.iterrows():
        reg_val = str(row['區域'])
        sub_val = str(row['施工廠商'])
        
        errors = []
        if reg_val not in st.session_state.regions:
            errors.append(f"區域「{reg_val}」不在名單內")
        if sub_val not in st.session_state.subcontractors:
            errors.append(f"廠商「{sub_val}」不在名單內")
            
        if errors:
            invalid_rows.append(f"第 {index+1} 列：{'、'.join(errors)}")

    # --- C. 判斷是否准予儲存 ---
    if invalid_rows:
        # ❌ 發現錯誤：跳出報錯訊息，拒絕執行資料庫同步
        st.error("🚫 儲存失敗！發現非預期名稱：")
        for err in invalid_rows:
            st.write(f"• {err}")
        st.info("💡 請從下拉選單選擇正確的名稱，或先在左側邊欄新增該區域/廠商。")
        
    elif edited_df.empty and not st.session_state.tasks.empty:
        # 🛡️ 保護鎖：防止意外全刪
        st.warning("⚠️ 檢測到清空表格操作，自動同步已攔截。")
        
    else:
        # ✅ 通過驗證：執行資料庫同步
        try:
            upload_list = []
            for _, row in clean_df.iterrows():
                upload_list.append({
                    "task_name": str(row['工作項目']),
                    "start_date": row['開始時間'].isoformat() if hasattr(row['開始時間'], 'isoformat') else str(row['開始時間']),
                    "end_date": row['完成時間'].isoformat() if hasattr(row['完成時間'], 'isoformat') else str(row['完成時間']),
                    "region": str(row['區域']),
                    "subcontractor": str(row['施工廠商']),
                    "is_milestone": bool(row['是否為里程碑'])
                })
            
            # 只有在資料正確時才執行刪除與新增
            supabase.table("tasks").delete().neq("id", -1).execute()
            if upload_list:
                supabase.table("tasks").insert(upload_list).execute()
            
            st.session_state.tasks = edited_df
            st.toast("💾 資料庫已同步成功", icon="☁️")
        except Exception as e:
            st.error(f"資料庫寫入失敗：{e}")
# ==========================================
# 7. 甘特圖生成 (全項目日期排序版)
# ==========================================
st.divider()
col_ctrl1, col_ctrl2 = st.columns([1, 2])
group_target = col_ctrl1.radio("📊 圖表分類維度：", ["依區域", "依施工廠商"], horizontal=True)

if st.button("🌟 生成互動式甘特圖", type="primary"):
    df = st.session_state.tasks.copy()
    if not df.empty:
        color_col = "區域" if group_target == "依區域" else "施工廠商"
        plot_df = df.copy()
        plot_df['是否為里程碑'] = plot_df['是否為里程碑'].fillna(False).astype(bool)
        plot_df['開始時間'] = pd.to_datetime(plot_df['開始時間'])
        plot_df['完成時間'] = pd.to_datetime(plot_df['完成時間'])
        plot_df['繪圖結束'] = plot_df['完成時間'] + pd.Timedelta(days=1)
        plot_df = plot_df.sort_values(by="開始時間", ascending=True)
        sorted_task_order = plot_df['工作項目'].tolist()
        
        all_unique_vals = plot_df[color_col].unique()
        color_seq = px.colors.qualitative.Plotly
        color_map = {val: color_seq[i % len(color_seq)] for i, val in enumerate(all_unique_vals)}

        tasks_only = plot_df[~plot_df['是否為里程碑']]
        fig = px.timeline(
            tasks_only, x_start="開始時間", x_end="繪圖結束", y="工作項目", 
            color=color_col, color_discrete_map=color_map, height=400 + len(df)*30
        )

        categories_in_legend = set(tasks_only[color_col].unique())
        ms_df = plot_df[plot_df['是否為里程碑']]
        for _, m in ms_df.iterrows():
            curr_cat = m[color_col]
            show_leg = curr_cat not in categories_in_legend
            if show_leg: categories_in_legend.add(curr_cat)

            fig.add_trace(go.Scatter(
                x=[m['開始時間']], y=[m['工作項目']], mode='markers+text',
                marker=dict(symbol='star', size=20, color=color_map.get(curr_cat, 'gray'), line=dict(color='black', width=1)),
                text=[f" {m['開始時間'].strftime('%m/%d')}"], textposition='middle right',
                textfont=dict(color='black', size=14), name=curr_cat, 
                legendgroup=curr_cat, showlegend=show_leg
            ))

        try:
            today = pd.Timestamp.now(tz='Asia/Taipei')
        except:
            today = pd.Timestamp.now()
        fig.add_vline(x=today, line_width=2, line_dash="dash", line_color="red", layer="above")
        fig.add_annotation(x=today, y=1, yref="paper", yanchor="bottom", text="今日", showarrow=False, font=dict(color="red", size=14), xanchor="left", xshift=5)

        fig.update_yaxes(categoryorder='array', categoryarray=sorted_task_order, autorange="reversed")
        fig.update_layout(
            title=dict(text=f"{st.session_state.project_name} - 進度總表", font=dict(color="black", size=20)),
            plot_bgcolor="#d3d3d3", paper_bgcolor="#d3d3d3",
            xaxis=dict(showgrid=True, gridcolor='black', tickformat="%m/%d", dtick="D1", tickfont=dict(color="black")),
            yaxis=dict(showgrid=True, gridcolor='black', tickfont=dict(color="black")),
            margin=dict(l=20, r=20, t=60, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 8. 系統備份與回復功能 (新增刪除備份功能)
# ==========================================
st.sidebar.divider()
st.sidebar.header("💾 系統備份與回復")

with st.sidebar.expander("🛠️ 資料備份工具"):
    # 1. 本地 CSV 備份
    csv = st.session_state.tasks.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 下載目前資料為 CSV",
        data=csv,
        file_name=f"工程備份_{pd.Timestamp.now().strftime('%m%d_%H%M')}.csv",
        mime='text/csv',
        use_container_width=True
    )

    st.divider()

    # 2. 雲端快照備份
    b_name = st.text_input("備份名稱", placeholder="例如：開工前存檔", key="backup_name_input")
    if st.button("🚀 建立雲端儲存點", use_container_width=True):
        try:
            json_data = st.session_state.tasks.to_json(orient='records', date_format='iso')
            supabase.table("tasks_backups").insert({
                "backup_name": b_name if b_name else "未命名備份",
                "data_json": json_data
            }).execute()
            st.toast("✅ 雲端備份成功！", icon="💾")
            st.rerun()
        except Exception as e:
            st.error(f"備份失敗：{e}")

    st.divider()

    # 3. 雲端回復與刪除資料
    st.subheader("⚠️ 管理儲存點")
    res_b = supabase.table("tasks_backups").select("id", "backup_time", "backup_name").order("backup_time", desc=True).execute()
    
    if res_b.data:
        # 建立選項清單
        b_options = {f"{item['backup_time'][5:16]} - {item['backup_name']}": item['id'] for item in res_b.data}
        selected_b = st.selectbox("選擇儲存點", options=list(b_options.keys()))
        target_id = b_options[selected_b]

        # 放置兩個按鈕：一個回復，一個刪除
        col_btn1, col_btn2 = st.columns(2)
        
        # --- 按鈕 A：回復資料 ---
        if col_btn1.button("🔥 回復", type="secondary", use_container_width=True):
            try:
                snapshot = supabase.table("tasks_backups").select("data_json").eq("id", target_id).execute()
                json_str = snapshot.data[0]['data_json']
                restored_df = pd.read_json(io.StringIO(json_str))
                
                if not restored_df.empty:
                    supabase.table("tasks").delete().neq("id", -1).execute()
                    new_upload = []
                    for _, row in restored_df.iterrows():
                        new_upload.append({
                            "task_name": str(row['工作項目']),
                            "start_date": pd.to_datetime(row['開始時間']).isoformat(),
                            "end_date": pd.to_datetime(row['完成時間']).isoformat(),
                            "region": row['區域'],
                            "subcontractor": row['施工廠商'],
                            "is_milestone": bool(row['是否為里程碑'])
                        })
                    if new_upload:
                        supabase.table("tasks").insert(new_upload).execute()
                    st.session_state.tasks = load_data()
                    st.toast("✅ 資料已恢復至該儲存點", icon="🔄")
                    st.rerun()
            except Exception as e:
                st.error(f"回復失敗：{e}")

        # --- 按鈕 B：刪除備份點 ---
        if col_btn2.button("🗑️ 刪除", type="primary", use_container_width=True):
            try:
                supabase.table("tasks_backups").delete().eq("id", target_id).execute()
                st.toast(f"已移除儲存點：{selected_b}", icon="🗑️")
                st.rerun() # 重新整理以更新下拉選單
            except Exception as e:
                st.error(f"刪除備份失敗：{e}")
    else:
        st.info("尚無雲端備份紀錄")
