import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import re

st.set_page_config(page_title="KKBOX 會員數據自動化分析系統", layout="wide", page_icon="📊")

# ==========================================
# 🔑 1. 預設綁定的主試算表 ID
# ==========================================
SPREADSHEET_ID = "1rfEcF4gQn-o-8KQ-LVcFT9e4QrSJNzQJ"

# 預設的分頁 gid 清單 (可自由新增/貼上多個分頁網址)
DEFAULT_GIDS = ["1647904491"] 

# ==========================================
# 🏷️ 2. 100% 官方內建對照字典
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

st.title("📊 KKBOX 會員數據自動化分析系統 (全跨週串聯版)")
st.caption("🚀 多分頁自動串聯：自動合併各分頁數據，串起完整 8+ 週歷史走勢！")
st.markdown("---")

# ==========================================
# ⚙️ 左側邊欄：多分頁網址管理
# ==========================================
st.sidebar.header("🔗 多分頁雲端資料庫管理")
st.sidebar.caption("💡 可貼入多個分頁的網址(每行一個)，系統會自動抓取並去重拼接成完整歷史趨勢！")

urls_text = st.sidebar.text_area(
    "請輸入各分頁的 Google Sheets 網址 (每行一個)：",
    value="https://docs.google.com/spreadsheets/d/1rfEcF4gQn-o-8KQ-LVcFT9e4QrSJNzQJ/edit?gid=1647904491#gid=1647904491",
    height=120
)

# 解析所有輸入的 GID
def extract_gids(text):
    gids = re.findall(r'gid=([0-9]+)', text)
    return list(set(gids)) if gids else ["1647904491"]

# ==========================================
# 🔄 3. 多分頁讀取、解析與自動去重
# ==========================================
@st.cache_data(ttl=60)
def load_all_sheets_data(spreadsheet_id, gid_list):
    all_parsed_rows = []
    
    for gid in gid_list:
        csv_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
        try:
            df_raw = pd.read_csv(csv_url, header=None)
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
                    
                    # 剔除總和列與空白列
                    if not pkg or '總和' in pkg or 'Total' in pkg or pkg == 'nan':
                        continue
                        
                    val = row[col_idx]
                    if pd.notna(val):
                        try:
                            val_clean = str(val).replace(',', '').strip()
                            val_num = float(val_clean)
                            all_parsed_rows.append({
                                'Date': date_val,
                                'Package_Name': pkg,
                                'Metric': metric_clean,
                                'Value': val_num
                            })
                        except:
                            continue
        except Exception:
            continue

    if all_parsed_rows:
        df_all = pd.DataFrame(all_parsed_rows)
        # 🚨 關鍵去重：跨分頁重複出現的日期與方案，取最新/最大值，達成多分頁無縫無損串接！
        df_clean = df_all.groupby(['Date', 'Package_Name', 'Metric'], as_index=False)['Value'].max()
        df_clean['Date_dt'] = pd.to_datetime(df_clean['Date'])
        return df_clean.sort_values('Date_dt')
        
    return pd.DataFrame()

# 側邊欄重新整理按鈕
if st.sidebar.button("🔄 立即同步並合併所有分頁"):
    st.cache_data.clear()
    st.rerun()

# 執行載入
gids = extract_gids(urls_text)
df_clean = load_all_sheets_data(SPREADSHEET_ID, gids)

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
    st.sidebar.subheader("📅 跨週區間篩選 (已自動合併所有分頁)")
    selected_dates = st.sidebar.multiselect("選擇檢視週別 (可複選看跨週趨勢)", available_dates, default=available_dates)
    
    if selected_dates:
        df_filtered = df_clean[df_clean['Date'].isin(selected_dates)]
        df_sub = df_filtered[df_filtered['Metric'] == 'Sub']
        
        latest_date = df_sub['Date'].max()
        latest_sub = df_sub[df_sub['Date'] == latest_date]['Value'].sum()
        
        col1, col2 = st.columns(2)
        col1.metric(label=f"最新週別 ({latest_date}) Total Sub 會員數", value=f"{int(latest_sub):,}")
        col2.metric(label="成功串接歷史週數", value=f"{len(selected_dates)} 週")
        
        st.markdown("---")
        tab1, tab2 = st.tabs(["📊 全歷史 Total Sub 走勢圖", "📋 跨週方案透視表"])
        
        with tab1:
            st.subheader("Total Sub 跨週走勢圖")
            df_trend = df_sub.groupby(['Date', 'Date_dt'], as_index=False)['Value'].sum().sort_values('Date_dt')
            fig, ax = plt.subplots(figsize=(12, 4.5))
            ax.plot(df_trend['Date'], df_trend['Value'], marker='o', color='#1DB954', linewidth=2.5)
            for i, row in df_trend.iterrows():
                ax.annotate(f"{int(row['Value']):,}", (row['Date'], row['Value']), textcoords="offset points", xytext=(0,10), ha='center', fontweight='bold')
            ax.set_ylabel("Subscribers")
            plt.xticks(rotation=30)
            ax.grid(True, linestyle='--', alpha=0.5)
            st.pyplot(fig)
            
        with tab2:
            st.subheader("各貼標與方案會員數 (Sub) 跨週透視表")
            pivot_df = df_sub.pivot_table(index=['Tag', 'Package_Name'], columns='Date', values='Value', aggfunc='sum', fill_value=0)
            st.dataframe(pivot_df, use_container_width=True)
else:
    st.info("👈 請在左側邊欄貼入你的 Google 試算表分頁網址。")
