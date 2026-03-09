import streamlit as st
import pandas as pd
import numpy as np
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta

# --- 1秒極速重整 ---
st_autorefresh(interval=1000, key="tmf_debug_monitor")

@st.cache_data(ttl=2)
def get_tmf_data():
    api = DataLoader()
    # 稍微多抓一點時間，確保 3分K 有足夠樣本
    start_dt = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d')
    try:
        # 抓取 TMF (微台全)
        df = api.taiwan_futures_tick(futures_id="TMF", date=start_dt)
        return df
    except Exception as e:
        st.error(f"API 抓取失敗: {e}")
        return pd.DataFrame()

st.title("TMF 3分K 監控系統 - 實戰版")
st.write(f"系統偵測時間: {datetime.now().strftime('%H:%M:%S')}")

df_raw = get_tmf_data()

if not df_raw.empty:
    st.success(f"✅ 已接收到 {len(df_raw)} 筆原始 Tick 數據")
    
    # --- 數據預處理與欄位檢查 ---
    # 自動尋找價格欄位 (FinMind 有時會變動名稱)
    price_col = 'price' if 'price' in df_raw.columns else 'deal_price'
    qty_col = 'qty' if 'qty' in df_raw.columns else 'volume'
    
    # 建立時間索引
    df_raw['date'] = pd.to_datetime(df_raw['date'] + ' ' + df_raw['time'])
    df_raw = df_raw.set_index('date')
    
    # --- 轉成 3分K ---
    ohlc = df_raw[price_col].resample('3min').ohlc()
    ohlc['volume'] = df_raw[qty_col].resample('3min').sum()
    df = ohlc.dropna().reset_index()

    if not df.empty:
        # --- 指標計算 (簡化版，確保必亮燈) ---
        df['ma5'] = df['close'].rolling(5).mean()
        df['buy_score'] = (df['close'] > df['ma5']).astype(int) * 5  # 只要站上均線就給5分亮一燈
        df['sell_score'] = (df['close'] < df['ma5']).astype(int) * 5
        
        last_row = df.iloc[-1]
        
        # --- 燈號對消邏輯 (Rich 專屬) ---
        # 假設原始燈號 (每5分亮一顆)
        r_raw = int(last_row['buy_score'] // 5)
        g_raw = int(last_row['sell_score'] // 5)
        
        # 後增加的留著，前面的對方的會減少
        display_red = max(0, r_raw - g_raw)
        display_green = g_raw 
        
        # --- UI 顯示 ---
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("買進紅燈")
            red_html = "".join([f'<div style="width:40px;height:40px;background:{"red" if i<display_red else "#330000"};border-radius:50%;display:inline-block;margin:5px;border:2px solid white;"></div>' for i in range(3)])
            st.markdown(red_html, unsafe_allow_html=True)
            st.metric("紅燈數", display_red)

        with col2:
            st.subheader("賣出綠燈")
            green_html = "".join([f'<div style="width:40px;height:40px;background:{"#00FF00" if i<display_green else "#003300"};border-radius:50%;display:inline-block;margin:5px;border:2px solid white;"></div>' for i in range(3)])
            st.markdown(green_html, unsafe_allow_html=True)
            st.metric("綠燈數", display_green)

        st.markdown("---")
        st.write("### 即時 3分K 數據明細")
        st.dataframe(df.tail(5))
    else:
        st.warning("⚠️ 數據轉換為 3分K 時失敗，可能該時段交易量太小。")
else:
    st.info("⌛ 正在連線至 FinMind 獲取 TMF 即時數據...")
