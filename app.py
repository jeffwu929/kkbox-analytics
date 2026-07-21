import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import re

st.set_page_config(page_title="KKBOX 會員數據自動化分析系統", layout="wide", page_icon="📊")

# ==========================================
# 🔑 1. 預設綁定的 Google Sheets 網址
# ==========================================
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1rfEcF4gQn-o-8KQ-LVcFT9e4QrSJNzQJ/edit?gid=1647904491#gid=1647904491"

# ==========================================
# 🏷️ 2. 100% 官方內建對照字典 (完整綁定 package_tags)
# ==========================================
OFFICIAL_TAG_MAP = {
    '[台哥大方案] 無損音質 24M優惠$209': '搭售',
    '[台哥大方案] 無損音質單月免綁約': '無約',
    '[台哥大方案] 標準音質': '無約',
    '[台哥大方案] 標準音質3M免費': '搭贈',
    '[台哥大方案] 標準音質6M優惠$134': '搭售',
    '[台哥大方案] 標準音質12M優惠$129': '搭售',
    '[台哥大方案] 標準音質24M優惠$89': '搭售',
    '[台哥大方案] 標準音質24M優惠$109': '搭售',
    '[台哥大方案] 標準音質30M優惠$89': '搭售',
    '[台哥大方案] 標準音質優惠月租方案': '無約',
    '[台灣大哥大] 個人方案 - 月租$109': '搭售',
    '[台灣大哥大] 個人方案 - 月租$119': '搭售',
    '[台灣大哥大] 個人方案 - 月租$129': '搭售',
    '[台灣大哥大] 個人方案 - 月租$139': '搭售',
    '[台灣大哥大] 個人方案 - 月租$159': '搭售',
    '[台灣大哥大] 個人方案 - 首3月$0': '搭贈',
    '[台灣大哥大] 學生方案 - 月租$89': '搭售'
}

if 'tag_map' not in st.session_state:
    st.session_state['tag_map'] = OFFICIAL_TAG_MAP.copy()

st.title("📊 KKBOX 會員數據自動化分析系統 (週視角)")
st.caption("🚀 雲端試算表直連版：打開網頁即刻呈現最新分析結果！")
st.markdown("---")

# ==========================================
# ⚙️ 左側邊欄：網址設定與動態切換
# ==========================================
st.sidebar.header("🔗 雲端資料庫設定")
user_url = st.sidebar.text_input(
    "Google Sheets 分頁網址：", 
    value=DEFAULT_SHEET_URL,
    help="如需切換其他週別分頁，請直接在此貼上該分頁的網址"
)

# 自動將標準網址轉換為 CSV 匯出網址
def convert_to_csv_url(url):
    sheet_id_match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    gid_match = re.search(r'gid=([0-9]+)', url)
    
    if sheet_id_match:
        sheet_id = sheet_id_match.group(1)
        gid = gid_match.group(1) if gid_match else '0'
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return url

# ==========================================
# 🔄 3. 自動讀取與解析
# ==========================================
@st.cache_data(ttl=60)
def load_data_from_url(url):
    csv_url = convert_to_csv_url(url)
    try:
        df_raw = pd.read_csv(csv_url, header=None)
        dates = df_raw.iloc[0].ffill()
        metrics = df_raw.iloc[1]
        
        df_data = df_raw.iloc[2:].copy()
        df_data[0] = df_data[0].ffill()
        df_data = df_data.rename(columns={0: 'Package_Name'})
        
        parsed_rows = []
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
                    try:
                        val_num = float(val)
                        parsed_rows.append({
                            'Date': date_val,
                            'Package_Name': pkg,
                            'Metric': metric_clean,
                            'Value': val_num
                        })
                    except:
                        continue

        if parsed_rows:
            df_all = pd.DataFrame(parsed_rows)
            df_clean = df_all.groupby(['Date', 'Package_Name', 'Metric'], as_index=False)['Value'].max()
            df_clean['Date_dt'] = pd.to_datetime(df_clean['Date'])
            return df_clean.sort_values('Date_dt')
    except Exception as e:
        st.error(f"❌ 讀取失敗。請確認試算表分享權限已開啟『知道連結者皆可檢視』。錯誤訊息：{e}")
    return pd.DataFrame()

# 側邊欄強制重新整理按鈕
if st.sidebar.button("🔄 立即同步最新數據"):
    st.cache_data.clear()
    st.rerun()

if user_url:
    df_clean = load_data_from_url(user_url)

    if not df_clean.empty:
        def get_official_tag(pkg):
            return st.session_state['tag_map'].get(pkg, '🚨 未分類新方案')

        df_clean['Tag'] = df_clean['Package_Name'].apply(get_official_tag)
        
        # 🚨 4. 新方案自動攔截與動態設定
        unknown_pkgs = df_clean[df_clean['Tag'] == '🚨 未分類新方案']['Package_Name'].unique().tolist()
        if unknown_pkgs:
            st.warning(f"🚨 提醒：發現 {len(unknown_pkgs)} 個尚未在官方對照表中的新方案！請在下方指定分類：")
            with st.expander("🛠️ 點此快速維護新方案貼標", expanded=True):
                col_a, col_b, col_c = st.columns([2, 2, 1])
                selected_new_pkg = col_a.selectbox("選擇新方案：", unknown_pkgs)
                assign_tag = col_b.selectbox("指定官方 Tag：", ["搭售", "無約", "搭贈", "其他"])
                if col_c.button("💾 儲存分類"):
                    st.session_state['tag_map'][selected_new_pkg] = assign_tag
                    st.success(f"✅ 已成功將「{selected_new_pkg}」歸類為 [{assign_tag}]！")
                    st.rerun()

        # 📅 5. 週視角資料展示
        available_dates = df_clean['Date'].unique().tolist()
        st.sidebar.markdown("---")
        st.sidebar.subheader("📅 近 5 週區間篩選")
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
            tab1, tab2 = st.tabs(["📊 近 5 週 Total Sub 趨勢圖", "📋 週視角方案透視表"])
            
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
    st.info("👈 請在左側邊欄確認 Google 試算表網址。")
