import streamlit as st
import pandas as pd
import numpy as np
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
import pytz

# --- 1. 時區與自動重整設定 (改為 5 秒，避免 API 鎖定) ---
tw_tz = pytz.timezone('Asia/Taipei')
st_autorefresh(interval=5000, key="tmf_final_v1")

# --- 2. 強化版數據抓取 ---
@st.cache_data(ttl=5)
def get_tmf_data_v2():
    api = DataLoader()
    # 取得台灣當下的正確日期
    now_tw = datetime.now(tw_tz)
    today_str = now_tw.strftime('%Y-%m-%d')
    
    try:
        # 嘗試抓取 TMF (微台全)
        df = api.taiwan_futures_tick(futures_id="TMF", date=today_str)
        
        # 關鍵防錯：如果今天沒資料，自動嘗試抓前一天，確保畫面有東西能測試邏輯
        if df is None or df.empty or 'price' not in df.columns:
            yesterday_str = (now_tw - timedelta(days=1)).strftime('%Y-%m-%d')
            df = api.taiwan_futures_tick(futures_id="TMF", date=yesterday_str)
        
        return df
    except Exception as e:
        return f"API 連線異常: {str(e)}"

# --- 3. UI 介面設定 ---
st.set_page_config(page_title="TMF 3分K 監控", layout="wide")
st.title("TMF 3分K 監控系統 - 終極校正版")

# 顯示校正後的台灣時間
now_str = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.write(f"⏰ **目前台灣時間**: {now_str}")
st.markdown("---")

res = get_tmf_data_v2()

if isinstance(res, str):
    st.error(res)
    st.info("💡 提示：這通常是 FinMind API 流量限制。我們已將更新調降至 5 秒以維持穩定。")
elif res is not None and not res.empty:
    st.success(f"✅ 成功獲取 {len(res)} 筆 TMF 原始數據")
    
    # 資料轉換邏輯 (3分K)
    df_raw = res.copy()
    price_col = 'price' if 'price' in df_raw.columns else 'deal_price'
    df_raw['date'] = pd.to_datetime(df_raw['date'] + ' ' + df_raw['time'])
    df_raw = df_raw.set_index('date')
    
    # Resample 3分K
    df_3m = df_raw[price_col].resample('3min').ohlc()
    df_3m['volume'] = df_raw['qty'].resample('3min').sum()
    df = df_3m.dropna().reset_index()

    if not df.empty:
        # --- Rich 的燈號對消邏輯 ---
        df['ma5'] = df['close'].rolling(5).mean()
        # 簡化指標範例：收盤價 > 5MA 給一燈
        df['buy_score'] = (df['close'] > df['ma5']).astype(int) * 5
        df['sell_score'] = (df['close'] < df['ma5']).astype(int) * 5
        
        last_row = df.iloc[-1]
        r_raw = int(last_row['buy_score'] // 5)
        g_raw = int(last_row['sell_score'] // 5)
        
        # 對消邏輯：後增加的留著，對方的減少
        display_red = max(0, r_raw - g_raw)
        display_green = g_raw

        # 燈號渲染
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("買進紅燈")
            red_html = "".join([f'<div style="width:50px;height:50px;background:{"red" if i<display_red else "#330000"};border-radius:50%;display:inline-block;margin:5px;border:2px solid white;"></div>' for i in range(3)])
            st.markdown(red_html, unsafe_allow_html=True)
        with c2:
            st.subheader("賣出綠燈")
            green_html = "".join([f'<div style="width:50px;height:50px;background:{"#00FF00" if i<display_green else "#003300"};border-radius:50%;display:inline-block;margin:5px;border:2px solid white;"></div>' for i in range(3)])
            st.markdown(green_html, unsafe_allow_html=True)

        st.markdown("---")
        st.write("📊 **即時 3分K 數據明細**")
        st.dataframe(df.tail(10))
    else:
        st.warning("⏳ 3分K 數據計算中，請保持連線...")
else:
    st.info("🔭 正在嘗試同步 TMF 歷史/即時數據...")
