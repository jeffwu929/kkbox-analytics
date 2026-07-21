
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="KKBOX 會員數據分析系統", layout="wide", page_icon="📊")

st.title("📊 KKBOX 會員數據自動化分析系統")
st.caption("輕鬆整理每週/每月 Raw Data，自動計算會員數與動態趨勢圖表")
st.markdown("---")

st.sidebar.header("📁 資料源上傳")
uploaded_files = st.sidebar.file_uploader("1. 上傳每週/每月 Raw Data (可多選)", type=["xlsx", "xls"], accept_multiple_files=True)
tag_file = st.sidebar.file_uploader("2. (選填) 上傳貼標對照表 (package_tags.xlsx)", type=["xlsx", "xls"])

tag_dict = {}
if tag_file:
    try:
        df_tags = pd.read_excel(tag_file)
        tag_dict = dict(zip(df_tags['Package_Name'], df_tags['Tag']))
        st.sidebar.success("✅ 成功套用貼標對照表！")
    except Exception as e:
        st.sidebar.error("⚠️ 貼標對照表格式不符，請確認包含 Package_Name 與 Tag 欄位")

if uploaded_files:
    all_parsed_rows = []
    for uploaded_file in uploaded_files:
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
                pkg = row['Package_Name']
                val = row[col_idx]
                if pd.notna(val) and str(pkg) != '總和':
                    all_parsed_rows.append({
                        'Date': date_val,
                        'Package_Name': pkg,
                        'Metric': metric_clean,
                        'Value': float(val)
                    })
    
    df_all = pd.DataFrame(all_parsed_rows)
    df_clean = df_all.groupby(['Date', 'Package_Name', 'Metric'], as_index=False)['Value'].max()
    df_clean['Date_dt'] = pd.to_datetime(df_clean['Date'])
    df_clean = df_clean.sort_values('Date_dt')
    
    if tag_dict:
        df_clean['Tag'] = df_clean['Package_Name'].map(tag_dict).fillna('未分類/新方案')
    else:
        def get_tag(pkg):
            if '免費' in pkg or '3M' in pkg: return '搭贈案'
            elif '個人' in pkg or '月租' in pkg: return '自營案'
            else: return '搭售案'
        df_clean['Tag'] = df_clean['Package_Name'].apply(get_tag)
        
    unknown_packages = df_clean[df_clean['Tag'] == '未分類/新方案']['Package_Name'].unique()
    if len(unknown_packages) > 0:
        st.warning(f"🚨 提醒：發現 {len(unknown_packages)} 個方案未在對照表中設定貼標：{', '.join(unknown_packages[:3])}...")
    
    available_dates = df_clean['Date'].unique().tolist()
    st.sidebar.subheader("📅 時間區間篩選")
    selected_dates = st.sidebar.multiselect("選擇要檢視的日期", available_dates, default=available_dates)
    
    if selected_dates:
        df_filtered = df_clean[df_clean['Date'].isin(selected_dates)]
        df_sub = df_filtered[df_filtered['Metric'] == 'Sub']
        
        latest_date = df_sub['Date'].max()
        latest_sub = df_sub[df_sub['Date'] == latest_date]['Value'].sum()
        
        col1, col2 = st.columns(2)
        col1.metric(label=f"最新日期 ({latest_date}) Total Sub 會員數", value=f"{int(latest_sub):,}")
        col2.metric(label="涵蓋資料筆數", value=f"{len(selected_dates)} 筆")
        
        st.markdown("---")
        tab1, tab2 = st.tabs(["📊 趨勢圖表", "📋 方案會員數透視表"])
        
        with tab1:
            st.subheader("Total Sub 會員數走勢圖")
            df_trend = df_sub.groupby(['Date', 'Date_dt'], as_index=False)['Value'].sum().sort_values('Date_dt')
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(df_trend['Date'], df_trend['Value'], marker='o', color='#1DB954', linewidth=2.5)
            for i, row in df_trend.iterrows():
                ax.annotate(f"{int(row['Value']):,}", (row['Date'], row['Value']), textcoords="offset points", xytext=(0,10), ha='center', fontweight='bold')
            ax.set_ylabel("Subscribers")
            ax.grid(True, linestyle='--', alpha=0.5)
            st.pyplot(fig)
            
        with tab2:
            st.subheader("各方案會員數 (Sub) 透視表")
            pivot_df = df_sub.pivot_table(index=['Tag', 'Package_Name'], columns='Date', values='Value', aggfunc='sum', fill_value=0)
            st.dataframe(pivot_df, use_container_width=True)

else:
    st.info("👈 請點選左側邊欄上傳每週 Raw Data 檔案與貼標對照表。")
