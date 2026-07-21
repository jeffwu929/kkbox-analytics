import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import re
import json
import os

st.set_page_config(page_title="KKBOX 會員數據自動化分析系統", layout="wide", page_icon="📊")

CONFIG_FILE = "sheet_urls_db.json"

# ==========================================
# 💾 0. 網址永久儲存庫
# ==========================================
DEFAULT_URL_DB = {
    "2026/07/12": "https://docs.google.com/spreadsheets/d/1rfEcF4gQn-o-8KQ-LVcFT9e4QrSJNzQJ/edit?gid=1647904491#gid=1647904491"
}

def load_url_db():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_URL_DB.copy()
    return DEFAULT_URL_DB.copy()

def save_url_db(db):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        st.error(f"儲存失敗：{e}")
        return False

if 'url_db' not in st.session_state:
    st.session_state['url_db'] = load_url_db()

# ==========================================
# 🏷️ 1. 100% 官方內建對照字典
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

st.title("📊 KKBOX 會員數據自動化分析系統 (全歷史連通版)")
st.caption("🚀 精準精算版：已修正子項目加總邏輯，對齊 100% 原始數據！")
st.markdown("---")

main_tab1, main_tab2 = st.tabs(["📈 數據分析儀表板", "⚙️ Raw Data 網址庫管理"])

# ==========================================
# ⚙️ 分頁二：Raw Data 網址庫管理
# ==========================================
with main_tab2:
    st.subheader("📁 每週 Raw Data 網址記憶庫")
    st.info("💡 在此新增每週 Google Sheets 分頁網址，系統會自動儲存並永久連通！")
    
    col_add1, col_add2, col_add3 = st.columns([2, 4, 1])
    new_title = col_add1.text_input("週別標題 (例如: 2026/07/19)", placeholder="YYYY/MM/DD")
    new_url = col_add2.text_input("Google Sheets 分頁網址", placeholder="https://docs.google.com/spreadsheets/d/.../edit#gid=...")
    
    st.write("")
    if col_add3.button("➕ 新增並儲存"):
        if new_title and new_url:
            st.session_state['url_db'][new_title.strip()] = new_url.strip()
            save_url_db(st.session_state['url_db'])
            st.success(f"✅ 已成功記錄『{new_title}』！")
            st.rerun()
        else:
            st.warning("⚠️ 請輸入標題與網址。")

    st.markdown("---")
    st.write("📋 **目前已紀錄的每週網址清單：**")
    
    if st.session_state['url_db']:
        db_df = [{"週別標題": title, "分頁網址": url} for title, url in st.session_state['url_db'].items()]
        st.dataframe(pd.DataFrame(db_df), use_container_width=True)
        
        col_del1, col_del2 = st.columns([3, 1])
        del_target = col_del1.selectbox("選擇要刪除的歷史週別記錄：", list(st.session_state['url_db'].keys()))
        if col_del2.button("🗑️ 刪除該筆記錄"):
            if del_target in st.session_state['url_db']:
                del st.session_state['url_db'][del_target]
                save_url_db(st.session_state['url_db'])
                st.success(f"已刪除『{del_target}』！")
                st.rerun()

# ==========================================
# 🔄 多分頁自動解析與精準加總邏輯
# ==========================================
@st.cache_data(ttl=60)
def load_all_saved_urls(url_map):
    all_rows = []
    loaded_count = 0
    
    for title, url in url_map.items():
        sheet_match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        gid_match = re.search(r'gid=([0-9]+)', url)
        
        if not sheet_match:
            continue
            
        sid = sheet_match.group(1)
        gid = gid_match.group(1) if gid_match else '0'
        csv_url = f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid={gid}"
        
        try:
            df_raw = pd.read_csv(csv_url, header=None)
            dates = df_raw.iloc[0].ffill()
            metrics = df_raw.iloc[1]
            
            df_data = df_raw.iloc[2:].copy()
            df_data[0] = df_data[0].ffill()  # 處理跨行拆分方案名
            df_data = df_data.rename(columns={0: 'Package_Name'})
            
            has_data = False
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
                    
                    # 剔除彙總與空白列
                    if not pkg or '總和' in pkg or 'Total' in pkg or pkg == 'nan':
                        continue
                        
                    val = row[col_idx]
                    if pd.notna(val):
                        try:
                            val_clean = str(val).replace(',', '').strip()
                            val_num = float(val_clean)
                            all_rows.append({
                                'Tab_Title': title, # 記住來源分頁
                                'Date': date_val,
                                'Package_Name': pkg,
                                'Metric': metric_clean,
                                'Value': val_num
                            })
                            has_data = True
                        except:
                            continue
            if has_data:
                loaded_count += 1
        except Exception:
            continue

    if all_rows:
        df_all = pd.DataFrame(all_rows)
        
        # 🚨 第一階段精準校正：同一個分頁內，若方案因為跨行有複數列，使用 .sum() 完整累加！
        df_tab_sum = df_all.groupby(['Tab_Title', 'Date', 'Package_Name', 'Metric'], as_index=False)['Value'].sum()
        
        # 🚨 第二階段跨頁去重：重疊週別採納最新的分頁數據 (.last() 或 .max())
        df_clean = df_tab_sum.groupby(['Date', 'Package_Name', 'Metric'], as_index=False)['Value'].last()
        
        df_clean['Date_dt'] = pd.to_datetime(df_clean['Date'])
        return df_clean.sort_values('Date_dt'), loaded_count
        
    return pd.DataFrame(), 0

# ==========================================
# 📈 分頁一：數據分析儀表板
# ==========================================
with main_tab1:
    if st.sidebar.button("🔄 重新載入最新數據"):
        st.cache_data.clear()
        st.rerun()

    df_clean, loaded_count = load_all_saved_urls(st.session_state['url_db'])

    if not df_clean.empty:
        st.sidebar.success(f"✅ 已連結 {loaded_count} 個歷史資料庫，共涵蓋 {df_clean['Date'].nunique()} 個獨立週別！")

        def get_official_tag(pkg):
            return st.session_state['tag_map'].get(pkg, '🚨 未分類新方案')

        df_clean['Tag'] = df_clean['Package_Name'].apply(get_official_tag)
        
        # 🚨 新方案自動攔截
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

        # 📅 週別區間篩選
        available_dates = df_clean['Date'].unique().tolist()
        st.sidebar.markdown("---")
        st.sidebar.subheader("📅 跨週區間篩選")
        selected_dates = st.sidebar.multiselect("選擇檢視週別 (可複選看趨勢)", available_dates, default=available_dates)
        
        if selected_dates:
            df_filtered = df_clean[df_clean['Date'].isin(selected_dates)]
            df_sub = df_filtered[df_filtered['Metric'] == 'Sub']
            
            latest_date = df_sub['Date'].max()
            latest_sub = df_sub[df_sub['Date'] == latest_date]['Value'].sum()
            
            col1, col2 = st.columns(2)
            col1.metric(label=f"最新週別 ({latest_date}) Total Sub 會員數", value=f"{int(round(latest_sub)):,}")
            col2.metric(label="目前累積週數", value=f"{len(selected_dates)} 週")
            
            st.markdown("---")
            view_tab1, view_tab2 = st.tabs(["📊 Total Sub 跨週趨勢圖", "📋 週視角方案透視表"])
            
            with view_tab1:
                st.subheader("Total Sub 跨週趨勢走勢圖")
                df_trend = df_sub.groupby(['Date', 'Date_dt'], as_index=False)['Value'].sum().sort_values('Date_dt')
                fig, ax = plt.subplots(figsize=(12, 4.5))
                ax.plot(df_trend['Date'], df_trend['Value'], marker='o', color='#1DB954', linewidth=2.5)
                for i, row in df_trend.iterrows():
                    ax.annotate(f"{int(round(row['Value'])):,}", (row['Date'], row['Value']), textcoords="offset points", xytext=(0,10), ha='center', fontweight='bold')
                ax.set_ylabel("Subscribers")
                plt.xticks(rotation=30)
                ax.grid(True, linestyle='--', alpha=0.5)
                st.pyplot(fig)
                
            with view_tab2:
                st.subheader("各貼標與方案會員數 (Sub) 跨週透視表")
                pivot_df = df_sub.pivot_table(index=['Tag', 'Package_Name'], columns='Date', values='Value', aggfunc='sum', fill_value=0)
                # 自動四捨五入為整數顯示
                pivot_df = pivot_df.round(0).astype(int)
                st.dataframe(pivot_df, use_container_width=True)
    else:
        st.info("💡 請點選上方『⚙️ Raw Data 網址庫管理』分頁新增每週分頁網址。")
