import streamlit as st
import pandas as pd
import numpy as np
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
import pytz

# --- 1. 時區與自動重整 (5秒) ---
tw_tz = pytz.timezone('Asia/Taipei')
st_autorefresh(interval=5000, key="tmf_full_v11")

st.set_page_config(page_title="微台全 3分K 監控", layout="wide")

# --- 🔑 2. Token 安全登入 (多重嘗試) ---
MY_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMy0wOSAyMDozOToxOSIsInVzZXJfaWQiOiJhcmljYTUxNSIsImVtYWlsIjoiZXZlbmNoZW41MTVAZ21haWwuY29tIiwiaXAiOiIxMjQuNi4xMS4yMTYifQ.NkLHnTiAp10uKfrc8qkt0YevD-Cc1XV062O1u3lBvh4"

@st.cache_resource
def init_api(token):
    api = DataLoader()
    # 針對你的環境做多重登入測試，避開 AttributeError
    for func in ["login", "login_by_token", "login_token"]:
        if hasattr(api, func):
            try:
                getattr(api, func)(api_token=token)
                return api
            except: continue
    return api

api_client = init_api(MY_TOKEN)

# --- 3. 抓取「全日盤」連續數據 ---
@st.cache_data(ttl=3)
def get_tmf_full_data():
    now_tw = datetime.now(tw_tz)
    # 抓取包含昨日的數據，這對「全日盤」至關重要，因為夜盤是從今天下午開始的
    start_dt = (now_tw - timedelta(days=1)).strftime('%Y-%m-%d')
    try:
        # 嘗試抓取 TMF (微台03全)
        df = api_client.taiwan_futures_tick(futures_id="TMF", date=start_dt)
        if df is None or df.empty:
            return None, "目前 TMF 無數據回傳"
        return df, "OK"
    except Exception as e:
        return None, str(e)

# --- 4. 運算核心 (3分K) ---
def calc_tmf_logic(df):
    # 時間與價格標準化
    p_col = 'price' if 'price' in df.columns else 'deal_price'
    df['date'] = pd.to_datetime(df['date'] + ' ' + df['time'])
    df = df.set_index('date')
    
    # Resample 成 3分K
    df_3m = df[p_col].resample('3min').ohlc()
    df_3m['volume'] = df['qty'].resample('3min').sum() if 'qty' in df.columns else 0
    df_3m = df_3m.dropna().reset_index()
    
    # 40 個指標邏輯 (以 MA 作為範例基準)
    df_3m['ma5'] = df_3m['close'].rolling(5).mean()
    df_3m['buy_score'] = (df_3m['close'] > df_3m['ma5']).astype(int) * 5
    df_3m['sell_score'] = (df_3m['close'] < df_3m['ma5']).astype(int) * 5
    return df_3m

# --- 5. UI 介面 (拿掉側邊欄) ---
st.title("📊 微台 03 全 - 3分K 交易監控")
st.write(f"⏰ **台灣即時時間**: {datetime.now(tw_tz).strftime('%H:%M:%S')}")

raw_df, status = get_tmf_full_data()

if status == "OK":
    df_3m = calc_tmf_logic(raw_df)
    last = df_3m.iloc[-1]
    
    # 燈號處理 (Rich 的對消邏輯)
    r_raw = min(3, int(last['buy_score'] // 5))
    g_raw = min(3, int(last['sell_score'] // 5))
    f_red = max(0, r_raw - g_raw) # 後進綠燈扣除紅燈
    f_green = g_raw

    # 燈號顯示區
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🔴 買進紅燈")
        html = "".join([f'<div style="width:70px;height:70px;background:{"red" if i<f_red else "#220000"};border-radius:50%;display:inline-block;margin:10px;border:3px solid white;box-shadow:{"0 0 20px red" if i<f_red else "none"};"></div>' for i in range(3)])
        st.markdown(html, unsafe_allow_html=True)
        st.metric("當前點位", f"{last['close']:.0f}")

    with c2:
        st.markdown("### 🟢 賣出綠燈")
        html = "".join([f'<div style="width:70px;height:70px;background:{"#00FF00" if i<f_green else "#002200"};border-radius:50%;display:inline-block;margin:10px;border:3px solid white;box-shadow:{"0 0 20px #00FF00" if i<f_green else "none"};"></div>' for i in range(3)])
        st.markdown(html, unsafe_allow_html=True)
        st.metric("買進積分", f"{int(last['buy_score'])}/20")

    st.markdown("---")
    st.write("📊 **微台全 3分K 即時指數明細**")
    st.dataframe(df_3m.tail(10))
else:
    st.error(f"📡 數據抓取失敗：{status}")
    st.info("提示：這通常是因為 FinMind 的 'TMF' 代號在夜盤需要特定的 Token 權限，或嘗試重新整理網頁。")
