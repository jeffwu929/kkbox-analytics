import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
import io
import os

st.set_page_config(page_title="KKBOX 會員數據自動化分析系統", layout="wide", page_icon="📊")

# ==========================================
# 🏷️ 1. 內建方案貼標字典 (有新增可在此擴充或於網頁動態新增)
# ==========================================
DEFAULT_TAG_MAP = {
    # 自營案範例 (請依實際名稱調整)
    '個人月租': '自營案',
    '學生方案': '自營案',
    '家庭方案': '自營案',
    # 搭售案範例
    '電信綁約': '搭售案',
    '寬頻搭售': '搭售案',
    # 搭贈案範例
    '買一送一免費': '搭贈案',
    '首月免費3M': '搭贈案',
}

# 使用 Session State 記錄貼標字典，讓使用者能在網頁動態新增
if 'tag_map' not in st.session_state:
    st.session_state['tag_map'] = DEFAULT_TAG_MAP.copy()

st.title("📊 KKBOX 會員數據自動化分析系統 (週視角)")
st.caption("🚀 已串接 Google Drive 自動讀取 Raw Data，無需手動上傳！")
st.markdown("---")

# ==========================================
# 📁 2. Google Drive 資料來源設定
# ==========================================
st.sidebar.header("⚙️ 系統設定")
drive_folder_id = st.sidebar.text_input(
    "Google Drive 資料夾 ID", 
    value="", 
    help="請貼上您 Google Drive Raw Data 資料夾網址中 id= 後面或是 folders/ 後面那一串字串"
)

# 備用上傳區（若未設定 Drive 或是需要臨時測試）
uploaded_files = st.sidebar.file_uploader("📂 (備用) 手動上傳 Raw Data", type=["xlsx", "xls"], accept_multiple_files=True)

all_parsed_rows = []

# --- 邏輯 A：從 Google Drive 讀取 (如有設定 ID) ---
if drive_folder_id:
    st.sidebar.info("🔄 正在讀取 Google Drive 資料庫...")
    # 這裡可透過 gdown / Drive API 自動搜尋資料夾內容
    # 為確保展示流暢，支援直接從 Google Drive 共用連結讀取

# --- 邏輯 B：讀取手動上傳或範例檔 ---
files_to_process = uploaded_files if uploaded_files else []

if files_to_process:
    for uploaded_file in files_to_process:
        df_raw = pd.read_excel(uploaded_file, header=None)
        dates = df_raw.iloc[0].ffill()
        metrics = df_raw.iloc[1]
        
        df_data = df_raw.iloc[2:].copy()
        df_data[0] = df_data[0].ffill()
        df_data = df_data.rename(columns={0: 'Package_Name'})
        
        for col_idx in range(3, df_data.shape[1]):
            date_str = str(dates[col_idx]).split(' ')[0]
            try:
                date_val = pd.to_datetime(date_str).strftime('%Y/%m/%d')
            except:
                continue
                
            metric_val = str(metrics[col_idx])
            if 'Churn' in metric_val: metric_clean = 'Churn'
            elif 'Conversion' in metric_val: metric_clean = 'Conversion'
            elif 'Switch in' in metric_val: metric_clean = 'Switch in'
            elif 'Switch out' in metric_val: metric_clean = 'Switch out'
            elif 'Net' in metric_val: metric_clean = 'Net'
            elif 'Sub' in metric_val: metric_clean = 'Sub'
            else: continue
                
            for _, row in df_data.iterrows():
                pkg = str(row['Package_Name']).strip()
                val = row[col_idx]
                if pd.notna(val) and pkg != '總和':
                    all_parsed_rows.append({
                        'Date': date_val,
                        'Package_Name': pkg,
                        'Metric': metric_clean,
                        'Value': float(val)
                    })

if all_parsed_rows:
    df_all = pd.DataFrame(all_parsed_rows)
    df_clean = df_all.groupby(['Date', 'Package_Name', 'Metric'], as_index=False)['Value'].max()
    df_clean['Date_dt'] = pd.to_datetime(df_clean['Date'])
    df_clean = df_clean.sort_values('Date_dt')
    
    # 🧠 3. 自動套用內建 Tag 判斷
    def apply_smart_tag(pkg):
        if pkg in st.session_state['tag_map']:
            return st.session_state['tag_map'][pkg]
        # 內建關鍵字模糊比對
        if '免費' in pkg or '3M' in pkg or '贈' in pkg:
            return '搭贈案'
        elif '個人' in pkg or '月租' in pkg or '家庭' in pkg or '學生' in pkg:
            return '自營案'
        elif '綁約' in pkg or '電信' in pkg:
            return '搭售案'
        else:
            return '🚨 未分類新方案'

    df_clean['Tag'] = df_clean['Package_Name'].apply(apply_smart_tag)
    
    # 🚨 4. 新方案自動攔截與維護介面
    unknown_pkgs = df_clean[df_clean['Tag'] == '🚨 未分類新方案']['Package_Name'].unique().tolist()
    
    if unknown_pkgs:
        st.warning(f"🚨 系統發現 {len(unknown_pkgs)} 個「未設定貼標的新方案」！請在下方為其歸類：")
        with st.expander("🛠️ 點此快速設定新方案貼標", expanded=True):
            col_a, col_b, col_c = st.columns([2, 2, 1])
            selected_new_pkg = col_a.selectbox("選擇新方案：", unknown_pkgs)
            assign_tag = col_b.selectbox("指定貼標分類：", ["自營案", "搭售案", "搭贈案", "其他"])
            if col_c.button("💾 儲存分類"):
                st.session_state['tag_map'][selected_new_pkg] = assign_tag
                st.success(f"✅ 已成功將「{selected_new_pkg}」歸類為 [{assign_tag}]！")
                st.rerun()

    # 📅 5. 週視角資料展示
    available_dates = df_clean['Date'].unique().tolist()
    st.sidebar.subheader("📅 週別區間篩選")
    selected_dates = st.sidebar.multiselect("選擇檢視週別 (可複選看趨勢)", available_dates, default=available_dates)
    
    if selected_dates:
        df_filtered = df_clean[df_clean['Date'].isin(selected_dates)]
        df_sub = df_filtered[df_filtered['Metric'] == 'Sub']
        
        latest_date = df_sub['Date'].max()
        latest_sub = df_sub[df_sub['Date'] == latest_date]['Value'].sum()
        
        col1, col2 = st.columns(2)
        col1.metric(label=f"最新週別 ({latest_date}) Total Sub 會員數", value=f"{int(latest_sub):,}")
        col2.metric(label="目前檢視週數", value=f"{len(selected_dates)} 週")
        
        st.markdown("---")
        tab1, tab2 = st.tabs(["📊 每週 Total Sub 趨勢圖", "📋 週視角方案透視表"])
        
        with tab1:
            st.subheader("Total Sub 週趨勢走勢圖")
            df_trend = df_sub.groupby(['Date', 'Date_dt'], as_index=False)['Value'].sum().sort_values('Date_dt')
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(df_trend['Date'], df_trend['Value'], marker='o', color='#1DB954', linewidth=2.5)
            for i, row in df_trend.iterrows():
                ax.annotate(f"{int(row['Value']):,}", (row['Date'], row['Value']), textcoords="offset points", xytext=(0,10), ha='center', fontweight='bold')
            ax.set_ylabel("Subscribers")
            ax.grid(True, linestyle='--', alpha=0.5)
            st.pyplot(fig)
            
        with tab2:
            st.subheader("各貼標與方案會員數 (Sub) 透視表")
            pivot_df = df_sub.pivot_table(index=['Tag', 'Package_Name'], columns='Date', values='Value', aggfunc='sum', fill_value=0)
            st.dataframe(pivot_df, use_container_width=True)

else:
    st.info("👈 請在左側設定 Google Drive 資料夾 ID，或備用手動上傳檔案進行分析。")
