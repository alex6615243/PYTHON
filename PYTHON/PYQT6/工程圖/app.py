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
# 2. 資料讀寫邏輯 (增加施工廠商)
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
        # 確保所有欄位都存在
        cols = ['工作項目', '開始時間', '完成時間', '區域', '施工廠商', '是否為里程碑']
        return df[cols]
    return pd.DataFrame(columns=['工作項目', '開始時間', '完成時間', '區域', '施工廠商', '是否為里程碑'])

def load_list(table_name):
    res = supabase.table(table_name).select("name").execute()
    return [item['name'] for item in res.data] if res.data else ["未設定"]

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

st.title("🏢 營建工程進度規劃系統")

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
            elif new_reg in st.session_state.regions:
                st.warning("該區域已存在")
                
    with tab_reg_del:
        del_reg = st.selectbox("選擇要刪除的區域", st.session_state.regions, key="del_reg_sel")
        if st.button("刪除區域", type="primary", use_container_width=True):
            # 🛡️ 防呆檢查：確認該區域是否正被任務使用中
            is_used = (st.session_state.tasks['區域'] == del_reg).any()
            if is_used:
                st.error(f"⚠️ 無法刪除！「{del_reg}」目前已有綁定的工程任務。請先修改或刪除相關任務。")
            else:
                try:
                    supabase.table("regions").delete().eq("name", del_reg).execute()
                    st.session_state.regions.remove(del_reg)
                    st.toast(f"🗑️ 區域「{del_reg}」已成功刪除！", icon="✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"刪除失敗：{e}")

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
            elif new_sub in st.session_state.subcontractors:
                st.warning("該廠商已存在")
                
    with tab_sub_del:
        del_sub = st.selectbox("選擇要刪除的廠商", st.session_state.subcontractors, key="del_sub_sel")
        if st.button("刪除廠商", type="primary", use_container_width=True):
            # 🛡️ 防呆檢查：確認該廠商是否正被任務使用中
            is_used = (st.session_state.tasks['施工廠商'] == del_sub).any()
            if is_used:
                st.error(f"⚠️ 無法刪除！「{del_sub}」目前仍在負責工程任務。請先轉移或刪除相關任務。")
            else:
                try:
                    supabase.table("subcontractors").delete().eq("name", del_sub).execute()
                    st.session_state.subcontractors.remove(del_sub)
                    st.toast(f"🗑️ 廠商「{del_sub}」已成功刪除！", icon="✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"刪除失敗：{e}")
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
# 6. 主畫面表格與自動存檔 (修復空白列 NaN 報錯版)
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
        clean_df = edited_df.dropna(subset=['工作項目', '開始時間', '完成時間']).copy()
        
        # 🛡️ 動態抓取合法的預設值 (確保絕對存在於資料庫中)
        default_reg = st.session_state.regions[0] if st.session_state.regions else "主區域"
        default_sub = st.session_state.subcontractors[0] if st.session_state.subcontractors else "未指定廠商"
        
        upload_list = []
        for _, row in clean_df.iterrows():
            # 讀取當前列的值
            val_reg = str(row['區域'])
            val_sub = str(row['施工廠商'])
            
            # 嚴格過濾：如果真的是空的、nan 或是 None，就強制替換成合法預設值
            final_reg = val_reg if pd.notna(row['區域']) and val_reg not in ['nan', 'None', ''] else default_reg
            final_sub = val_sub if pd.notna(row['施工廠商']) and val_sub not in ['nan', 'None', ''] else default_sub
            
            upload_list.append({
                "task_name": str(row['工作項目']),
                "start_date": row['開始時間'].isoformat(),
                "end_date": row['完成時間'].isoformat(),
                "region": final_reg,
                "subcontractor": final_sub,
                "is_milestone": bool(row['是否為里程碑'])
            })
            
        # 執行同步
        supabase.table("tasks").delete().neq("id", -1).execute()
        if upload_list:
            supabase.table("tasks").insert(upload_list).execute()
            
        st.session_state.tasks = edited_df
        st.toast("💾 資料庫已同步", icon="☁️")
        
    except Exception as e:
        st.error(f"同步失敗：{e}")

            
    # ==========================================
# 7. 多維度甘特圖生成 (修復里程碑星星與全黑字體版)
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
        
        # 2. 確保里程碑資料型態正確 (防呆)
        plot_df['是否為里程碑'] = plot_df['是否為里程碑'].fillna(False).astype(bool)
        plot_df['繪圖結束'] = plot_df['完成時間'] + pd.Timedelta(days=1)
        
        # 3. 建立動態顏色對照表
        unique_vals = df[color_col].unique()
        color_seq = px.colors.qualitative.Plotly
        color_map = {val: color_seq[i % len(color_seq)] for i, val in enumerate(unique_vals)}

        # 4. 繪製一般任務長條圖
        fig = px.timeline(
            plot_df[~plot_df['是否為里程碑']], 
            x_start="開始時間", x_end="繪圖結束", y="工作項目", 
            color=color_col,
            color_discrete_map=color_map,
            height=400 + len(df)*30
        )

        # 🌟 5. 處理里程碑星號 (動態抓取對應分類的顏色)
        ms_df = plot_df[plot_df['是否為里程碑']]
        for _, m in ms_df.iterrows():
            fig.add_trace(go.Scatter(
                x=[m['開始時間']], 
                y=[m['工作項目']], 
                mode='markers+text',
                marker=dict(
                    symbol='star', size=20, 
                    # 💡 這裡將寫死的 '區域' 改為動態變數 color_col
                    color=color_map.get(m[color_col], 'gray'), 
                    line=dict(color='black', width=1)
                ),
                text=[f" {m['開始時間'].strftime('%m/%d')}"], 
                textposition='middle right', 
                textfont=dict(color='black', size=14), 
                name=m[color_col],        # 💡 同步修改為動態對應
                legendgroup=m[color_col], # 💡 同步修改為動態對應
                showlegend=False
            ))

        # 6. 加入今日垂直線
        try:
            today = pd.Timestamp.now(tz='Asia/Taipei')
        except:
            today = pd.Timestamp.now()
            
        fig.add_vline(x=today, line_width=2, line_dash="dash", line_color="red", layer="above")
        fig.add_annotation(
            x=today, y=1, yref="paper", yanchor="bottom", 
            text="今日", showarrow=False, 
            font=dict(color="red", size=14), 
            xanchor="left", xshift=5
        )

        # 7. 版面與黑字/黑線格式強制設定
        fig.update_yaxes(autorange="reversed", type='category')
        fig.update_layout(
            title=dict(text=f"{st.session_state.project_name} - 進度總表 (分類：{color_col})", font=dict(color="black", size=20)),
            xaxis_title=dict(text="日期", font=dict(color="black", size=14)),
            yaxis_title=dict(text="工作項目", font=dict(color="black", size=14)),
            font=dict(color="black"),
            plot_bgcolor="#d3d3d3", paper_bgcolor="#d3d3d3",
            xaxis=dict(showgrid=True, gridcolor='black', tickformat="%m/%d", dtick="D1", tickfont=dict(color="black", size=12)),
            yaxis=dict(showgrid=True, gridcolor='black', tickfont=dict(color="black", size=14)),
            legend=dict(font=dict(color="black")),
            margin=dict(l=20, r=20, t=60, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)
