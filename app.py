import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import re
import json
import os
from datetime import datetime

try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

st.set_page_config(page_title="KKBOX 會員數據自動化分析系統", layout="wide", page_icon="📊")

CONFIG_FILE = "sheet_urls_db.json"
TARGETS_FILE = "monthly_targets_db.json"
TAGS_FILE = "package_tags_db.json"

# ==========================================
# 💾 0. 數據庫讀寫邏輯
# ==========================================
DEFAULT_URL_DB = {
    "2026/07/12": "https://docs.google.com/spreadsheets/d/1rfEcF4gQn-o-8KQ-LVcFT9e4QrSJNzQJ/edit?gid=1647904491#gid=1647904491"
}

DEFAULT_TARGETS = {
    "2026/07": 118000,
    "2026/08": 120000
}

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

if 'tag_map' not in st.session_state:
    st.session_state['tag_map'] = load_json_file(TAGS_FILE, OFFICIAL_TAG_MAP)

st.title("📊 KKBOX 會員數據自動化分析系統")
st.caption("🚀 模組化極簡儀表板：訂閱數趨勢與方案類型佔比雙頁面獨立展示！")
st.markdown("---")

main_tab1, main_tab2, main_tab3, main_tab4 = st.tabs([
    "📈 數據分析儀表板", 
    "⚙️ Raw Data 網址庫管理", 
    "🎯 月度目標維護",
    "🏷️ 方案類型維護"
])

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
# 🎯 分頁三：月度目標維護
# ==========================================
with main_tab3:
    st.subheader("🎯 各月份 TWM 會員數目標維護")
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

    st.markdown("---")
    st.write("📋 **目前月度目標設定一覽：**")
    if st.session_state['target_db']:
        t_df = [{"月份": m, "目標會員數": f"{v:,}"} for m, v in st.session_state['target_db'].items()]
        st.dataframe(pd.DataFrame(t_df), use_container_width=True)
        
        col_tdel1, col_tdel2 = st.columns([3, 1])
        del_m_target = col_tdel1.selectbox("選擇要刪除的月份目標：", list(st.session_state['target_db'].keys()))
        if col_tdel2.button("🗑️ 刪除該月目標"):
            if del_m_target in st.session_state['target_db']:
                del st.session_state['target_db'][del_m_target]
                save_json_file(TARGETS_FILE, st.session_state['target_db'])
                st.success(f"已刪除『{del_m_target}』！")
                st.rerun()

# ==========================================
# 🔄 數據讀取邏輯
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

df_clean, loaded_count = load_all_saved_urls(st.session_state['url_db'])

# ==========================================
# 🏷️ 分頁四：方案類型獨立維護
# ==========================================
with main_tab4:
    st.subheader("🏷️ 方案類型對照管理")
    st.info("💡 系統已為您自動彙總目前資料庫中出現過的所有方案。您可在下方直接編輯或修改各方案對應的「方案類型」。")
    
    if not df_clean.empty:
        all_detected_pkgs = sorted(df_clean['Package_Name'].unique().tolist())
        
        tag_list_data = []
        for pkg in all_detected_pkgs:
            tag_list_data.append({
                "方案名稱": pkg,
                "對應方案類型": st.session_state['tag_map'].get(pkg, "🚨 未分類新方案")
            })
            
        st.dataframe(pd.DataFrame(tag_list_data), use_container_width=True)
        st.markdown("---")
        
        st.write("✏️ **編輯方案類型：**")
        col_tag1, col_tag2, col_tag3 = st.columns([3, 2, 1])
        selected_pkg = col_tag1.selectbox("選擇要設定的方案：", all_detected_pkgs)
        assign_tag = col_tag2.selectbox("指定方案類型：", ["搭售", "無約", "搭贈", "其他"])
        
        st.write("")
        if col_tag3.button("💾 儲存方案類型"):
            st.session_state['tag_map'][selected_pkg] = assign_tag
            save_json_file(TAGS_FILE, st.session_state['tag_map'])
            st.success(f"✅ 已成功將「{selected_pkg}」歸類為 [{assign_tag}]！")
            st.rerun()
    else:
        st.write("尚無讀取到方案數據，請先載入每週 Raw Data。")

# ==========================================
# 📈 分頁一：數據分析儀表板
# ==========================================
with main_tab1:
    if st.sidebar.button("🔄 重新載入最新數據"):
        st.cache_data.clear()
        st.rerun()

    if not df_clean.empty:
        st.sidebar.success(f"✅ 已連結 {loaded_count} 個歷史資料庫，共涵蓋 {df_clean['Date'].nunique()} 個獨立週別！")

        def get_official_tag(pkg):
            return st.session_state['tag_map'].get(pkg, '🚨 未分類新方案')

        df_clean['方案類型'] = df_clean['Package_Name'].apply(get_official_tag)
        
        available_dates = df_clean['Date'].unique().tolist()
        available_dts = [pd.to_datetime(d) for d in available_dates]
        
        # 📅 1. 日期選擇器
        st.sidebar.markdown("---")
        st.sidebar.subheader("📅 1. 指定日期自動判別週別")
        selected_date_input = st.sidebar.date_input("選擇任意日期：", datetime.now().date())
        
        matched_date_str = None
        if selected_date_input:
            input_dt = pd.to_datetime(selected_date_input)
            valid_dts = [d for d in available_dts if d <= input_dt]
            if valid_dts:
                closest_dt = max(valid_dts)
                matched_date_str = closest_dt.strftime('%Y/%m/%d')
            else:
                matched_date_str = available_dates[0]
            st.sidebar.info(f"🎯 自動判別對應週別為：**{matched_date_str}**")

        # 📅 2. 週別區間篩選 (增加「近 5 週」)
        st.sidebar.subheader("📅 2. 週別區間篩選")
        quick_select = st.sidebar.selectbox("🚀 快速時間選擇：", ["自動連動指定日期", "近 4 週", "近 5 週", "近 8 週", "近 12 週", "全選", "自訂"])
        
        if quick_select == "自動連動指定日期" and matched_date_str:
            idx = available_dates.index(matched_date_str) if matched_date_str in available_dates else len(available_dates)-1
            start_idx = max(0, idx - 4) # 展示當週及前 4 週共 5 週
            default_selected = available_dates[start_idx:idx+1]
        elif quick_select == "近 4 週":
            default_selected = available_dates[-4:] if len(available_dates) >= 4 else available_dates
        elif quick_select == "近 5 週":
            default_selected = available_dates[-5:] if len(available_dates) >= 5 else available_dates
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
            
            df_sub_weekly = df_sub.groupby(['Date', 'Date_dt'], as_index=False)['Value'].sum().sort_values('Date_dt')
            
            latest_date_str = df_sub_weekly.iloc[-1]['Date']
            latest_val = df_sub_weekly.iloc[-1]['Value']
            
            prev_val = df_sub_weekly.iloc[-2]['Value'] if len(df_sub_weekly) >= 2 else None
            wow_val = (latest_val - prev_val) if prev_val else 0
            wow_pct = (wow_val / prev_val * 100) if prev_val else 0.0
            
            latest_dt = pd.to_datetime(latest_date_str)
            month_key = latest_dt.strftime('%Y/%m')
            target_val = st.session_state['target_db'].get(month_key, 0)
            
            diff_target = latest_val - target_val if target_val > 0 else 0
            achievement_rate = (latest_val / target_val * 100) if target_val > 0 else 0.0

            sub_tab1, sub_tab2 = st.tabs(["📊 1. 會員數趨勢與目標比較", "🧩 2. 方案類型佔比分析"])

            # ====================================================
            # 兩大類之一：訂閱數變化
            # ====================================================
            with sub_tab1:
                st.subheader(f"📌 TWM 會員數比較指標 ({latest_date_str})")
                
                if prev_val:
                    wow_color = "#1DB954" if wow_val >= 0 else "#E50914"
                    wow_html = f"<span style='color:{wow_color}; font-weight:bold;'>{'+' if wow_val > 0 else ''}{int(round(wow_val)):,} ({wow_pct:+.2f}%)</span>"
                else:
                    wow_html = "N/A"
                    
                if target_val > 0:
                    diff_color = "#1DB954" if diff_target >= 0 else "#E50914"
                    diff_html = f"<span style='color:{diff_color}; font-weight:bold;'>{'+' if diff_target > 0 else ''}{int(round(diff_target)):,}</span>"
                    
                    achieve_color = "#1DB954" if achievement_rate >= 100.0 else "#E50914"
                    achieve_html = f"<span style='color:{achieve_color}; font-weight:bold;'>{achievement_rate:.2f}%</span>"
                else:
                    diff_html = "N/A"
                    achieve_html = "N/A"

                twm_html_table = f"""
                <table style="width:100%; border-collapse:collapse; text-align:center; font-size:16px;">
                    <thead>
                        <tr style="background-color:#f2f2f2; border-bottom:2px solid #ddd;">
                            <th style="padding:10px; text-align:center;">指標項目</th>
                            <th style="padding:10px; text-align:center;">本週</th>
                            <th style="padding:10px; text-align:center;">上週</th>
                            <th style="padding:10px; text-align:center;">WOW 增減</th>
                            <th style="padding:10px; text-align:center;">{latest_dt.month}月目標</th>
                            <th style="padding:10px; text-align:center;">與目標落差</th>
                            <th style="padding:10px; text-align:center;">達成率</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr style="border-bottom:1px solid #ddd;">
                            <td style="padding:12px; font-weight:bold; text-align:center;">TWM 會員數 (Sub)</td>
                            <td style="padding:12px; font-weight:bold; text-align:center;">{int(round(latest_val)):,}</td>
                            <td style="padding:12px; text-align:center;">{f"{int(round(prev_val)):,}" if prev_val else "N/A"}</td>
                            <td style="padding:12px; text-align:center;">{wow_html}</td>
                            <td style="padding:12px; text-align:center;">{f"{target_val:,}" if target_val > 0 else "未設定"}</td>
                            <td style="padding:12px; text-align:center;">{diff_html}</td>
                            <td style="padding:12px; text-align:center;">{achieve_html}</td>
                        </tr>
                    </tbody>
                </table>
                """
                st.markdown(twm_html_table, unsafe_allow_html=True)
                st.markdown("---")

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

                st.subheader("📋 各方案類型會員數 (Sub) 跨週透視表")
                pivot_df = df_sub.pivot_table(index=['方案類型', 'Package_Name'], columns='Date', values='Value', aggfunc='sum', fill_value=0)
                pivot_df = pivot_df.round(0).astype(int)
                
                if hasattr(pivot_df, 'map'):
                    formatted_pivot = pivot_df.map(lambda x: f"{x:,}")
                else:
                    formatted_pivot = pivot_df.applymap(lambda x: f"{x:,}")
                    
                # 數字與標頭全面置中
                st.dataframe(formatted_pivot.style.set_properties(**{'text-align': 'center'}), use_container_width=True)

            # ====================================================
            # 兩大類之二：方案類型佔比分析 (含跨週動態比較欄位)
            # ====================================================
            with sub_tab2:
                base_date_str = selected_dates[0] # 選取區間的起始對照週
                
                st.subheader(f"🧩 方案類型佔比分析 (本週: {latest_date_str} vs 對照週: {base_date_str})")
                st.caption(f"💡 本區塊自動對比您選取的【{len(selected_dates)} 週時間區間】內，最新週與對照週（{base_date_str}）的 Conversion、Churn、Switch in/out 指標增減變化：")
                
                # 計算最新週與對照週的各 Tag 彙總數據
                df_latest_all = df_filtered[df_filtered['Date'] == latest_date_str]
                df_base_all = df_filtered[df_filtered['Date'] == base_date_str]
                
                tag_latest = df_latest_all.pivot_table(index='方案類型', columns='Metric', values='Value', aggfunc='sum', fill_value=0)
                tag_base = df_base_all.pivot_table(index='方案類型', columns='Metric', values='Value', aggfunc='sum', fill_value=0)
                
                metrics_list = ['Sub', 'Conversion', 'Churn', 'Switch in', 'Switch out']
                for m in metrics_list:
                    if m not in tag_latest.columns: tag_latest[m] = 0
                    if m not in tag_base.columns: tag_base[m] = 0
                
                comp_display = pd.DataFrame(index=tag_latest.index)
                comp_display['Sub (本週)'] = tag_latest['Sub'].round(0).astype(int)
                
                # 動態加入各指標的本週數值與對照增減
                for m_name, m_key in [('Conversion', 'Conversion'), ('Churn', 'Churn'), ('Switch-in', 'Switch in'), ('Switch-out', 'Switch out')]:
                    l_v = tag_latest[m_key]
                    b_v = tag_base[m_key]
                    diff_v = l_v - b_v
                    
                    comp_display[f'{m_name} (本週)'] = l_v.round(0).astype(int).apply(lambda x: f"{x:,}")
                    comp_display[f'{m_name} 較對照週增減'] = diff_v.round(0).astype(int).apply(lambda x: f"{'+' if x>0 else ''}{x:,}")

                col_comp1, col_comp2 = st.columns([3, 2])
                
                with col_comp1:
                    st.write("**📋 方案類型指標與跨週比較總覽表：**")
                    # 數字與標頭全面置中
                    st.dataframe(comp_display.style.set_properties(**{'text-align': 'center'}), use_container_width=True)
                    
                with col_comp2:
                    st.write("**🍰 Sub 會員數方案類型佔比：**")
                    if 'Sub (本週)' in comp_display.columns and comp_display['Sub (本週)'].sum() > 0:
                        sub_by_tag = comp_display['Sub (本週)'].reset_index()
                        
                        if HAS_PLOTLY:
                            fig_plotly = px.pie(
                                sub_by_tag, 
                                names='方案類型', 
                                values='Sub (本週)',
                                color_discrete_sequence=['#1DB954', '#4B9CD3', '#FF9F1C', '#E50914', '#9B59B6'],
                                hole=0.3
                            )
                            fig_plotly.update_traces(textposition='inside', textinfo='percent+label')
                            fig_plotly.update_layout(
                                margin=dict(t=10, b=10, l=10, r=10),
                                showlegend=True
                            )
                            st.plotly_chart(fig_plotly, use_container_width=True)
                        else:
                            fig_m, ax_m = plt.subplots(figsize=(5, 4.2))
                            ax_m.pie(sub_by_tag['Sub (本週)'], labels=sub_by_tag['方案類型'], autopct='%1.1f%%', startangle=140)
                            ax_m.axis('equal')
                            st.pyplot(fig_m)
                    else:
                        st.info("尚無 Sub 數據可繪製佔比圖。")

    else:
        st.info("💡 請點選上方『⚙️ Raw Data 網址庫管理』分頁新增每週分頁網址。")
