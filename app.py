import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import re
import json
import os

st.set_page_config(page_title="KKBOX 會員數據自動化分析系統", layout="wide", page_icon="📊")

CONFIG_FILE = "sheet_urls_db.json"
TARGETS_FILE = "monthly_targets_db.json"

# ==========================================
# 💾 0. 數據庫讀寫邏輯 (網址庫 & 月目標)
# ==========================================
DEFAULT_URL_DB = {
    "2026/07/12": "https://docs.google.com/spreadsheets/d/1rfEcF4gQn-o-8KQ-LVcFT9e4QrSJNzQJ/edit?gid=1647904491#gid=1647904491"
}

DEFAULT_TARGETS = {
    "2026/07": 118000,
    "2026/08": 120000
}

def load_json_file(filename, default_data):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_data.copy()
    return default_data.copy()

def save_json_file(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        st.error(f"儲存失敗：{e}")
        return False

if 'url_db' not in st.session_state:
    st.session_state['url_db'] = load_json_file(CONFIG_FILE, DEFAULT_URL_DB)

if 'target_db' not in st.session_state:
    st.session_state['target_db'] = load_json_file(TARGETS_FILE, DEFAULT_TARGETS)

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

st.title("📊 KKBOX 會員數據自動化分析系統")
st.caption("🚀 一頁式全面監控：整合 TWM 會員數目標比較表、歷史趨勢圖與方案透視表！")
st.markdown("---")

main_tab1, main_tab2, main_tab3 = st.tabs(["📈 數據分析儀表板", "⚙️ Raw Data 網址庫管理", "🎯 月度目標維護"])

# ==========================================
# ⚙️ 分頁二：網址庫管理
# ==========================================
with main_tab2:
    st.subheader("📁 每週 Raw Data 網址記憶庫")
    col_add1, col_add2, col_add3 = st.columns([2, 4, 1])
    new_title = col_add1.text_input("週別標題 (例如: 2026/07/19)", placeholder="YYYY/MM/DD")
    new_url = col_add2.text_input("Google Sheets 分頁網址", placeholder="https://docs.google.com/spreadsheets/d/.../edit#gid=...")
    
    st.write("")
    if col_add3.button("➕ 新增並儲存網址"):
        if new_title and new_url:
            st.session_state['url_db'][new_title.strip()] = new_url.strip()
            save_json_file(CONFIG_FILE, st.session_state['url_db'])
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
        if col_del2.button("🗑️ 刪除網址記錄"):
            if del_target in st.session_state['url_db']:
                del st.session_state['url_db'][del_target]
                save_json_file(CONFIG_FILE, st.session_state['url_db'])
                st.success(f"已刪除『{del_target}』！")
                st.rerun()

# ==========================================
# 🎯 分頁三：月度目標維護 (含新增/編輯與刪除)
# ==========================================
with main_tab3:
    st.subheader("🎯 各月份 TWM 會員數目標維護")
    st.info("💡 輸入月份與目標值點擊儲存，若月份已存在將自動覆蓋更新。")
    
    col_t1, col_t2, col_t3 = st.columns([2, 3, 1])
    target_month = col_t1.text_input("月份 (例如: 2026/07)", placeholder="YYYY/MM")
    target_val = col_t2.number_input("該月目標會員數 (Sub)", min_value=0, step=1000, value=120000)
    
    st.write("")
    if col_t3.button("💾 儲存 / 更新月目標"):
        if target_month and target_val > 0:
            st.session_state['target_db'][target_month.strip()] = int(target_val)
            save_json_file(TARGETS_FILE, st.session_state['target_db'])
            st.success(f"✅ 已成功儲存 {target_month} 目標為 {int(target_val):,}！")
            st.rerun()
        else:
            st.warning("⚠️ 請輸入正確的月份與目標數值。")

    st.markdown("---")
    st.write("📋 **目前月度目標設定一覽：**")
    if st.session_state['target_db']:
        t_df = [{"月份": m, "目標會員數": f"{v:,}"} for m, v in st.session_state['target_db'].items()]
        st.dataframe(pd.DataFrame(t_df), use_container_width=True)
        
        # 🗑️ 新增刪除月度目標功能
        st.markdown("---")
        col_tdel1, col_tdel2 = st.columns([3, 1])
        del_m_target = col_tdel1.selectbox("選擇要刪除的月份目標：", list(st.session_state['target_db'].keys()))
        if col_tdel2.button("🗑️ 刪除該月目標"):
            if del_m_target in st.session_state['target_db']:
                del st.session_state['target_db'][del_m_target]
                save_json_file(TARGETS_FILE, st.session_state['target_db'])
                st.success(f"已刪除『{del_m_target}』的目標設定！")
                st.rerun()
    else:
        st.write("目前尚無任何月度目標設定。")

# ==========================================
# 🔄 數據讀取與處理邏輯
# ==========================================
@st.cache_data(ttl=60)
def load_all_saved_urls(url_map):
    all_rows = []
    loaded_count = 0
    
    for title, url in url_map.items():
        sheet_match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        gid_match = re.search(r'gid=([0-9]+)', url)
        if not sheet_match: continue
            
        sid = sheet_match.group(1)
        gid = gid_match.group(1) if gid_match else '0'
        csv_url = f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid={gid}"
        
        try:
            df_raw = pd.read_csv(csv_url, header=None)
            dates = df_raw.iloc[0].ffill()
            metrics = df_raw.iloc[1]
            
            df_data = df_raw.iloc[2:].copy()
            df_data[0] = df_data[0].ffill()
            df_data = df_data.rename(columns={0: 'Package_Name'})
            
            has_data = False
            for col_idx in range(3, df_data.shape[1]):
                date_str = str(dates[col_idx]).split(' ')[0]
                try: date_val = pd.to_datetime(date_str).strftime('%Y/%m/%d')
                except: continue
                    
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
                    if not pkg or '總和' in pkg or 'Total' in pkg or pkg == 'nan': continue
                        
                    val = row[col_idx]
                    if pd.notna(val):
                        try:
                            val_clean = str(val).replace(',', '').strip()
                            val_num = float(val_clean)
                            all_rows.append({
                                'Tab_Title': title,
                                'Date': date_val,
                                'Package_Name': pkg,
                                'Metric': metric_clean,
                                'Value': val_num
                            })
                            has_data = True
                        except: continue
            if has_data: loaded_count += 1
        except Exception: continue

    if all_rows:
        df_all = pd.DataFrame(all_rows)
        df_tab_sum = df_all.groupby(['Tab_Title', 'Date', 'Package_Name', 'Metric'], as_index=False)['Value'].sum()
        df_clean = df_tab_sum.groupby(['Date', 'Package_Name', 'Metric'], as_index=False)['Value'].last()
        df_clean['Date_dt'] = pd.to_datetime(df_clean['Date'])
        return df_clean.sort_values('Date_dt'), loaded_count
        
    return pd.DataFrame(), 0

# ==========================================
# 📈 分頁一：一頁式數據分析儀表板
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

        # 📅 週別區間快速選單功能 (近X週)
        available_dates = df_clean['Date'].unique().tolist()
        st.sidebar.markdown("---")
        st.sidebar.subheader("📅 週別區間快速篩選")
        
        quick_select = st.sidebar.selectbox("🚀 快速時間選擇：", ["全選", "近 4 週", "近 8 週", "近 12 週", "自訂"])
        
        if quick_select == "近 4 週":
            default_selected = available_dates[-4:] if len(available_dates) >= 4 else available_dates
        elif quick_select == "近 8 週":
            default_selected = available_dates[-8:] if len(available_dates) >= 8 else available_dates
        elif quick_select == "近 12 週":
            default_selected = available_dates[-12:] if len(available_dates) >= 12 else available_dates
        elif quick_select == "全選":
            default_selected = available_dates
        else:
            default_selected = available_dates

        selected_dates = st.sidebar.multiselect("複選調整檢視週別：", available_dates, default=default_selected)
        
        if selected_dates:
            df_filtered = df_clean[df_clean['Date'].isin(selected_dates)]
            df_sub = df_filtered[df_filtered['Metric'] == 'Sub']
            
            # 彙總各週 Sub 數據
            df_sub_weekly = df_sub.groupby(['Date', 'Date_dt'], as_index=False)['Value'].sum().sort_values('Date_dt')
            
            # 最新週與上週數據計算
            latest_date_str = df_sub_weekly.iloc[-1]['Date']
            latest_val = df_sub_weekly.iloc[-1]['Value']
            
            prev_val = df_sub_weekly.iloc[-2]['Value'] if len(df_sub_weekly) >= 2 else None
            wow_val = (latest_val - prev_val) if prev_val else 0
            wow_pct = (wow_val / prev_val * 100) if prev_val else 0.0
            
            # 月度目標匹配 (以最新週之 YYYY/MM 對應)
            latest_dt = pd.to_datetime(latest_date_str)
            month_key = latest_dt.strftime('%Y/%m')
            target_val = st.session_state['target_db'].get(month_key, 0)
            
            diff_target = latest_val - target_val if target_val > 0 else 0
            achievement_rate = (latest_val / target_val * 100) if target_val > 0 else 0.0

            # ----------------------------------------------------
            # 1️⃣ TWM 會員數指標比較表
            # ----------------------------------------------------
            st.subheader(f"📌 TWM 會員數比較指標 ({latest_date_str})")
            
            twm_metrics_data = {
                "指標項目": ["TWM 會員數 (Sub)"],
                "本週": [f"{int(round(latest_val)):,}"],
                "上週": [f"{int(round(prev_val)):,}" if prev_val else "N/A"],
                "WOW 增減": [f"{'+' if wow_val > 0 else ''}{int(round(wow_val)):,} ({wow_pct:+.2f}%)" if prev_val else "N/A"],
                f"{latest_dt.month}月目標": [f"{target_val:,}" if target_val > 0 else "未設定"],
                "與目標落差": [f"{'+' if diff_target > 0 else ''}{int(round(diff_target)):,}" if target_val > 0 else "N/A"],
                "達成率": [f"{achievement_rate:.2f}%" if target_val > 0 else "N/A"]
            }
            
            st.dataframe(pd.DataFrame(twm_metrics_data), use_container_width=True, hide_index=True)
            st.markdown("---")

            # ----------------------------------------------------
            # 2️⃣ Total Sub 跨週趨勢圖 (一頁式展示)
            # ----------------------------------------------------
            st.subheader("📈 Total Sub 跨週走勢圖")
            fig, ax = plt.subplots(figsize=(12, 4.2))
            ax.plot(df_sub_weekly['Date'], df_sub_weekly['Value'], marker='o', color='#1DB954', linewidth=2.5)
            
            for i, row in df_sub_weekly.iterrows():
                ax.annotate(f"{int(round(row['Value'])):,}", (row['Date'], row['Value']), textcoords="offset points", xytext=(0,10), ha='center', fontweight='bold')
                
            ax.set_ylabel("Subscribers")
            plt.xticks(rotation=30)
            ax.grid(True, linestyle='--', alpha=0.5)
            st.pyplot(fig)
            st.markdown("---")

            # ----------------------------------------------------
            # 3️⃣ 各貼標與方案會員數 (Sub) 跨週透視表 (一頁式展示)
            # ----------------------------------------------------
            st.subheader("📋 各貼標與方案會員數 (Sub) 跨週透視表")
            pivot_df = df_sub.pivot_table(index=['Tag', 'Package_Name'], columns='Date', values='Value', aggfunc='sum', fill_value=0)
            pivot_df = pivot_df.round(0).astype(int)
            
            if hasattr(pivot_df, 'map'):
                formatted_pivot = pivot_df.map(lambda x: f"{x:,}")
            else:
                formatted_pivot = pivot_df.applymap(lambda x: f"{x:,}")
                
            st.dataframe(formatted_pivot, use_container_width=True)
            
    else:
        st.info("💡 請點選上方『⚙️ Raw Data 網址庫管理』分頁新增每週分頁網址。")
