import streamlit as st
import pandas as pd
import numpy as np
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
import pytz

# --- 1. 時區與自動重整 (設定 5 秒，平衡即時性與穩定性) ---
tw_tz = pytz.timezone('Asia/Taipei')
st_autorefresh(interval=5000, key="tmf_final_v9")

st.set_page_config(page_title="TMF 3分K 交易監控", layout="wide")
st.title("TMF 微台全 3分K 交易系統")

# --- 🔑 2. Token 安全登入機制 ---
MY_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMy0wOSAyMDozOToxOSIsInVzZXJfaWQiOiJhcmljYTUxNSIsImVtYWlsIjoiZXZlbmNoZW41MTVAZ21haWwuY29tIiwiaXAiOiIxMjQuNi4xMS4yMTYifQ.NkLHnTiAp10uKfrc8qkt0YevD-Cc1XV062O1u3lBvh4"

def get_authorized_api(token):
    api = DataLoader()
    # 解決 AttributeError: 嘗試多種可能的登入語法
    for method in ["login", "login_by_token", "login_token"]:
        if hasattr(api, method):
            try:
                getattr(api, method)(api_token=token)
                return api
            except: continue
    return api

api_client = get_authorized_api(MY_TOKEN)

# --- 3. 數據抓取與指標運算 (3分K 基準) ---
@st.cache_data(ttl=3)
def fetch_and_calc(token):
    now_tw = datetime.now(tw_tz)
    # 抓取包含昨天的數據，確保均線(MA)計算有足夠樣本
    start_dt = (now_tw - timedelta(days=1)).strftime('%Y-%m-%d')
    try:
        df = api_client.taiwan_futures_tick(futures_id="TMF", date=start_dt)
        if df is None or df.empty or 'price' not in df.columns:
            return None, "目前 API 未回傳有效 TMF 數據"
        
        # --- 3分K 轉換 ---
        df['date'] = pd.to_datetime(df['date'] + ' ' + df['time'])
        df = df.set_index('date')
        df_3m = df['price'].resample('3min').ohlc()
        df_3m['volume'] = df['qty'].resample('3min').sum()
        df_3m = df_3m.dropna().reset_index()
        
        # --- 20+20 指標邏輯 ---
        df_3m['ma5'] = df_3m['close'].rolling(5).mean()
        df_3m['ma20'] = df_3m['close'].rolling(20).mean()
        df_3m['buy_score'] = (df_3m['close'] > df_3m['ma5']).astype(int) * 5
        df_3m['sell_score'] = (df_3m['close'] < df_3m['ma5']).astype(int) * 5
        
        return df_3m, "OK"
    except Exception as e:
        return None, f"連線異常: {str(e)}"

# --- 4. UI 渲染 ---
now_str = datetime.now(tw_tz).strftime('%H:%M:%S')
st.write(f"⏰ **台灣站點時間**: {now_str}")

data_df, msg = fetch_and_calc(MY_TOKEN)

if msg == "OK":
    last = data_df.iloc[-1]
    # 燈號對消邏輯
    r_raw = min(3, int(last['buy_score'] // 5))
    g_raw = min(3, int(last['sell_score'] // 5))
    f_red = max(0, r_raw - g_raw)
    f_green = g_raw

    # 頂部指數看板
    st.metric("TMF 即時指數", f"{last['close']:.0f}", f"{last['close'] - data_df.iloc[-2]['close']:.0f}")

    # 燈號區
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🔴 買進紅燈")
        st.markdown("".join([f'<div style="width:75px;height:75px;background:{"red" if i<f_red else "#220000"};border-radius:50%;display:inline-block;margin:10px;border:3px solid white;box-shadow:{"0 0 20px red" if i<f_red else "none"};"></div>' for i in range(3)]), unsafe_allow_html=True)
    with c2:
        st.markdown("### 🟢 賣出綠燈")
        st.markdown("".join([f'<div style="width:75px;height:75px;background:{"#00FF00" if i<f_green else "#002200"};border-radius:50%;display:inline-block;margin:10px;border:3px solid white;box-shadow:{"0 0 20px #00FF00" if i<f_green else "none"};"></div>' for i in range(3)]), unsafe_allow_html=True)

    st.markdown("---")
    st.write("📊 **即時 3分K 指標明細表**")
    st.dataframe(data_df.tail(10))
else:
    # 即使沒資料也要畫出燈號架構
    st.error(f"📡 狀態：{msg}")
    st.info("提示：若持續看到 'data' 錯誤，請確認 FinMind 是否正在進行系統維護。")
    st.markdown("### 🔴 買進燈 (待機) &emsp; 🟢 賣出燈 (待機)")
