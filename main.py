import streamlit as st
import pandas as pd
import numpy as np
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta, time
import pytz

# --- 1. 環境設定 ---
tw_tz = pytz.timezone('Asia/Taipei')
st_autorefresh(interval=5000, key="tmf_final_v5") # 5秒刷新一次最穩定

st.set_page_config(page_title="TMF 微台全監控", layout="wide")
st.title("TMF 微台全 3分K 交易系統")

# --- 🔑 2. Token 與 登入 (強化相容性) ---
MY_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMy0wOSAyMDozOToxOSIsInVzZXJfaWQiOiJhcmljYTUxNSIsImVtYWlsIjoiZXZlbmNoZW41MTVAZ21haWwuY29tIiwiaXAiOiIxMjQuNi4xMS4yMTYifQ.NkLHnTiAp10uKfrc8qkt0YevD-Cc1XV062O1u3lBvh4"

@st.cache_resource
def get_api_client(token):
    api = DataLoader()
    try:
        # 嘗試多種登入語法
        if hasattr(api, 'login'):
            api.login(api_token=token)
        elif hasattr(api, 'login_by_token'):
            api.login_by_token(api_token=token)
    except:
        pass
    return api

api_client = get_api_client(MY_TOKEN)

# --- 3. 指標運算 (3分K 基準) ---
def calculate_signals(df):
    if df.empty: return df
    
    # A. 基礎線
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma90'] = df['close'].rolling(90).mean()
    
    # B. 當日參考點 (08:45)
    df['date_only'] = df['date'].dt.date
    df['day_open'] = df.groupby('date_only')['open'].transform('first')
    df['day_high'] = df.groupby('date_only')['high'].expanding().max().reset_index(0, drop=True)
    df['day_low'] = df.groupby('date_only')['low'].expanding().min().reset_index(0, drop=True)
    
    # C. 買進指標 (B1-B20)
    is_red = df['close'] > df['open']
    df['B1'] = (df['low'] <= df['day_high'] * (1-0.382)).astype(int) # 0.382回檔
    df['B10'] = (df['close'] > df['day_open']).astype(int) # 突破開盤
    df['B11'] = (df['close'] > df['ma5']).astype(int) # 5MA之上
    df['B14'] = (is_red & is_red.shift(1) & is_red.shift(2)).astype(int) # 連三紅
    df['B20'] = (df['volume'] > 1500).astype(int) # 量大門檻
    
    # D. 賣出指標 (S1-S20)
    is_green = df['close'] < df['open']
    df['S8'] = (df['close'] < df['day_open']).astype(int) # 開盤下
    df['S11'] = (df['close'] < df['ma5']).astype(int) # 跌破5MA
    df['S14'] = (is_green & is_green.shift(1) & is_green.shift(2)).astype(int) # 連三綠
    
    # E. 積分
    df['buy_score'] = df[[c for c in df.columns if c.startswith('B')]].sum(axis=1)
    df['sell_score'] = df[[c for c in df.columns if c.startswith('S')]].sum(axis=1)
    
    # F. 開盤燈 (首4根含連3)
    df['is_op_red'] = df.groupby('date_only')['B14'].transform(lambda x: 1 if x.head(4).max()==1 else 0)
    return df

# --- 4. 數據抓取與渲染 ---
now_tw = datetime.now(tw_tz)
st.write(f"⏰ **台灣站點時間**: {now_tw.strftime('%H:%M:%S')}")

try:
    # 抓取 TMF (微台全)
    raw = api_client.taiwan_futures_tick(futures_id="TMF", date=now_tw.strftime('%Y-%m-%d'))
    
    if raw is not None and not raw.empty:
        # 轉換為 3分K
        raw['date'] = pd.to_datetime(raw['date'] + ' ' + raw['time'])
        raw = raw.set_index('date')
        ohlc = raw['price'].resample('3min').ohlc()
        ohlc['volume'] = raw['qty'].resample('3min').sum()
        df = calculate_signals(ohlc.dropna().reset_index())
        
        last = df.iloc[-1]
        
        # 燈號邏輯 (對消後顯示)
        r_raw = min(3, (1 if last['is_op_red'] else 0) + (last['buy_score'] // 5))
        g_raw = min(3, (last['sell_score'] // 5))
        f_red = max(0, r_raw - g_raw)
        f_green = g_raw

        # UI 渲染
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🔴 買進紅燈")
            l_html = "".join([f'<div style="width:70px;height:70px;background:{"red" if i<f_red else "#220000"};border-radius:50%;display:inline-block;margin:10px;border:3px solid white;box-shadow:{"0 0 20px red" if i<f_red else "none"};"></div>' for i in range(3)])
            st.markdown(l_html, unsafe_allow_html=True)
            st.metric("買進積分", int(last['buy_score']))
        with c2:
            st.markdown("### 🟢 賣出綠燈")
            l_html = "".join([f'<div style="width:70px;height:70px;background:{"#00FF00" if i<f_green else "#002200"};border-radius:50%;display:inline-block;margin:10px;border:3px solid white;box-shadow:{"0 0 20px #00FF00" if i<f_green else "none"};"></div>' for i in range(3)])
            st.markdown(l_html, unsafe_allow_html=True)
            st.metric("賣出積分", int(last['sell_score']))

        st.markdown("---")
        st.write("📊 **即時 3分K 數據明細 (包含指標計算)**")
        st.dataframe(df.tail(10))
    else:
        st.info("📡 正在等待 TMF 夜盤數據流進來... (目前 21:05 為交易時間)")

except Exception as e:
    st.error(f"連線中，請稍候: {e}")
