import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
# 4. 側邊欄：區域與廠商管理 (含新增、刪除與防呆)
# ==========================================
st.sidebar.header("⚙️ 基礎資料管理")

# 📍 區域管理
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
                st.error(f"⚠️ 無法刪除！「{del_reg}」尚有任務綁定。")
            else:
                supabase.table("regions").delete().eq("name", del_reg).execute()
                st.session_state.regions.remove(del_reg)
                st.toast(f"🗑️ 區域「{del_reg}」已刪除", icon="✅")
                st.rerun()

# 👷 廠商管理
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
                st.error(f"⚠️ 無法刪除！「{del_sub}」尚有任務。")
            else:
                supabase.table("subcontractors").delete().eq("name", del_sub).execute()
                st.session_state.subcontractors.remove(del_sub)
                st.toast(f"🗑️ 廠商「{del_sub}」已刪除", icon="✅")
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
                "task_name": t_name,
                "start_date": s_d.isoformat(),
                "end_date": s_d.isoformat() if is_m else e_d.isoformat(),
                "region": c_reg,
                "subcontractor": c_sub,
                "is_milestone": is_m
            }
            supabase.table("tasks").insert(new_task).execute()
            st.session_state.tasks = load_data()
            st.rerun()

# ==========================================
# 6. 主畫面表格與自動存檔 (雙重防呆版：區域 + 廠商)
# ==========================================
st.subheader("📋 工程任務清單")
edited_df = st.data_editor(
    st.session_state.tasks, 
    num_rows="dynamic", 
    use_container_width=True,
    key="main_editor"
)

if not edited_df.equals(st.session_state.tasks):
    try:
        # 1. 濾掉完全沒填關鍵資訊的列
        clean_df = edited_df.dropna(subset=['工作項目', '開始時間', '完成時間']).copy()
        
        # 2. 💡 動態抓取「當前合法」的預設值
        # 優先使用名單中的第一項，如果名單是空的，則給予一個警告標籤
        default_reg = st.session_state.regions[0] if st.session_state.regions else "未設定"
        default_sub = st.session_state.subcontractors[0] if st.session_state.subcontractors else "未設定"
        
        upload_list = []
        for _, row in clean_df.iterrows():
            # 取得原始值
            val_reg = str(row['區域']) if pd.notna(row['區域']) else ""
            val_sub = str(row['施工廠商']) if pd.notna(row['施工廠商']) else ""
            
            # 🛡️ 區域防呆：如果不在合法名單內或是空的，就強制轉為預設值
            if val_reg not in st.session_state.regions:
                final_reg = default_reg
            else:
                final_reg = val_reg
                
            # 🛡️ 廠商防呆：如果不在合法名單內或是空的，就強制轉為預設值
            if val_sub not in st.session_state.subcontractors:
                final_sub = default_sub
            else:
                final_sub = val_sub
            
            upload_list.append({
                "task_name": str(row['工作項目']),
                "start_date": row['開始時間'].isoformat() if hasattr(row['開始時間'], 'isoformat') else str(row['開始時間']),
                "end_date": row['完成時間'].isoformat() if hasattr(row['完成時間'], 'isoformat') else str(row['完成時間']),
                "region": final_reg,
                "subcontractor": final_sub,
                "is_milestone": bool(row['是否為里程碑'])
            })
            
        # 3. 執行資料庫同步
        supabase.table("tasks").delete().neq("id", -1).execute()
        if upload_list:
            supabase.table("tasks").insert(upload_list).execute()
            
        st.session_state.tasks = edited_df
        st.toast("💾 資料庫已同步", icon="☁️")
        
    except Exception as e:
        st.error(f"同步失敗：{e}")
        st.info("💡 提示：請檢查您的區域或廠商名單是否已清空，或者表格中是否有未填寫完整的欄位。")

# ==========================================
# 7. 多維度甘特圖生成 (全項目日期排序版)
# ==========================================
st.divider()
col_ctrl1, col_ctrl2 = st.columns([1, 2])
group_target = col_ctrl1.radio("📊 圖表分類維度：", ["依區域", "依施工廠商"], horizontal=True)

if st.button("🌟 生成互動式甘特圖", type="primary"):
    df = st.session_state.tasks.copy()
    if not df.empty:
        # 1. 設定動態分類基準
        color_col = "區域" if group_target == "依區域" else "施工廠商"
        plot_df = df.copy()
        
        # 2. 數據預處理與強制轉型
        plot_df['是否為里程碑'] = plot_df['是否為里程碑'].fillna(False).astype(bool)
        plot_df['開始時間'] = pd.to_datetime(plot_df['開始時間'])
        plot_df['完成時間'] = pd.to_datetime(plot_df['完成時間'])
        plot_df['繪圖結束'] = plot_df['完成時間'] + pd.Timedelta(days=1)
        
        # 🚀 3. 核心排序：不論是否為里程碑，全體依開始日期排序
        plot_df = plot_df.sort_values(by="開始時間", ascending=True)
        
        # 💡 關鍵動作：提取排序後的「工作項目」清單，這將決定 Y 軸的順序
        sorted_task_order = plot_df['工作項目'].tolist()
        
        # 4. 建立顏色表
        all_unique_vals = plot_df[color_col].unique()
        color_seq = px.colors.qualitative.Plotly
        color_map = {val: color_seq[i % len(color_seq)] for i, val in enumerate(all_unique_vals)}

        # 5. 繪製一般任務 (過濾掉里程碑)
        tasks_only = plot_df[~plot_df['是否為里程碑']]
        fig = px.timeline(
            tasks_only, 
            x_start="開始時間", x_end="繪圖結束", y="工作項目", 
            color=color_col, color_discrete_map=color_map,
            height=400 + len(df)*30
        )

        # 6. 處理里程碑 (依序加入星星)
        categories_in_legend = set(tasks_only[color_col].unique())
        ms_df = plot_df[plot_df['是否為里程碑']]
        for _, m in ms_df.iterrows():
            current_cat = m[color_col]
            show_this_in_legend = current_cat not in categories_in_legend
            if show_this_in_legend:
                categories_in_legend.add(current_cat)

            fig.add_trace(go.Scatter(
                x=[m['開始時間']], y=[m['工作項目']], mode='markers+text',
                marker=dict(symbol='star', size=20, color=color_map.get(current_cat, 'gray'), line=dict(color='black', width=1)),
                text=[f" {m['開始時間'].strftime('%m/%d')}"], textposition='middle right',
                textfont=dict(color='black', size=14), name=current_cat, 
                legendgroup=current_cat, showlegend=show_this_in_legend
            ))

        # 7. 今日線與標記
        try:
            today = pd.Timestamp.now(tz='Asia/Taipei')
        except:
            today = pd.Timestamp.now()
        fig.add_vline(x=today, line_width=2, line_dash="dash", line_color="red", layer="above")
        fig.add_annotation(x=today, y=1, yref="paper", yanchor="bottom", text="今日", showarrow=False, font=dict(color="red", size=14), xanchor="left", xshift=5)

        # 🚀 8. 強制 Y 軸遵循我們排好的日期順序
        fig.update_yaxes(
            categoryorder='array', 
            categoryarray=sorted_task_order, 
            autorange="reversed" # 配合 array 排序，讓最早的在最上面
        )

        # 9. 版面樣式
        fig.update_layout(
            title=dict(text=f"{st.session_state.project_name} - 全方位進度表", font=dict(color="black", size=20)),
            font=dict(color="black"),
            plot_bgcolor="#d3d3d3", paper_bgcolor="#d3d3d3",
            xaxis=dict(showgrid=True, gridcolor='black', tickformat="%m/%d", dtick="D1", tickfont=dict(color="black")),
            yaxis=dict(showgrid=True, gridcolor='black', tickfont=dict(color="black")),
            legend=dict(font=dict(color="black")),
            margin=dict(l=20, r=20, t=60, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 8. 系統備份與回復功能 (新增於側邊欄或主畫面)
# ==========================================
st.sidebar.divider()
st.sidebar.header("💾 系統備份與回復")

with st.sidebar.expander("🛠️ 資料備份工具"):
    # --- 保險 1：下載 CSV 到本地 ---
    csv = st.session_state.tasks.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 下載目前資料為 CSV",
        data=csv,
        file_name=f"工程備份_{pd.Timestamp.now().strftime('%m%d_%H%M')}.csv",
        mime='text/csv',
        use_container_width=True
    )

    st.divider()

    # --- 保險 2：雲端存儲快照 (儲存點) ---
    b_name = st.text_input("備份名稱", placeholder="例如：開工前存檔")
    if st.button("🚀 建立雲端儲存點", use_container_width=True):
        try:
            # 將 DataFrame 轉為 JSON 格式存入
            json_data = st.session_state.tasks.to_json(orient='records', date_format='iso')
            supabase.table("tasks_backups").insert({
                "backup_name": b_name if b_name else "未命名備份",
                "data_json": json_data
            }).execute()
            st.toast("✅ 雲端備份成功！", icon="💾")
        except Exception as e:
            st.error(f"備份失敗：{e}")

    st.divider()

    # --- 保險 3：從雲端回復資料 ---
    st.subheader("⚠️ 從備份回復")
    res_b = supabase.table("tasks_backups").select("id", "backup_time", "backup_name").order("backup_time", desc=True).execute()
    if res_b.data:
        b_options = {f"{item['backup_time'][5:16]} - {item['backup_name']}": item['id'] for item in res_b.data}
        selected_b = st.selectbox("選擇儲存點", options=list(b_options.keys()))
        
        if st.button("🔥 確認回復資料", type="secondary", use_container_width=True):
            try:
                # 取得選定的備份資料
                target_id = b_options[selected_b]
                b_data = supabase.table("tasks_backups").select("data_json").eq("id", target_id).execute()
                restored_list = pd.read_json(b_data.data[0]['data_json'])
                
                # 將回復的資料寫入主表
                supabase.table("tasks").delete().neq("id", -1).execute()
                
                upload_list = []
                for _, row in restored_list.iterrows():
                    upload_list.append({
                        "task_name": str(row['工作項目']),
                        "start_date": pd.to_datetime(row['開始時間']).isoformat(),
                        "end_date": pd.to_datetime(row['完成時間']).isoformat(),
                        "region": row['區域'],
                        "subcontractor": row['施工廠商'],
                        "is_milestone": bool(row['是否為里程碑'])
                    })
                
                if upload_list:
                    supabase.table("tasks").insert(upload_list).execute()
                
                st.session_state.tasks = load_data()
                st.success("✅ 資料已成功回復至指定儲存點！")
                st.rerun()
            except Exception as e:
                st.error(f"回復失敗：{e}")
