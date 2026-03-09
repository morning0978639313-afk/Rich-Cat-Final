import streamlit as st
import pandas as pd
import numpy as np
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
import pytz

# --- 1. 環境設定 (台灣時區與自動重整) ---
tw_tz = pytz.timezone('Asia/Taipei')
# 設定 5 秒重新整理一次，有 Token 就不怕被封鎖
st_autorefresh(interval=5000, key="tmf_final_hero")

# --- 🔑 2. Token 設定區 (已填入 Rich 的 Token) ---
MY_FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMy0wOSAyMDozOToxOSIsInVzZXJfaWQiOiJhcmljYTUxNSIsImVtYWlsIjoiZXZlbmNoZW41MTVAZ21haWwuY29tIiwiaXAiOiIxMjQuNi4xMS4yMTYifQ.NkLHnTiAp10uKfrc8qkt0YevD-Cc1XV062O1u3lBvh4"

@st.cache_data(ttl=5)
def get_tmf_data_live(token):
    api = DataLoader()
    if token:
        try:
            # 正確的登入語法
            api.login(api_token=token)
        except Exception as e:
            st.error(f"Token 登入發生錯誤: {e}")
    
    now_tw = datetime.now(tw_tz)
    # 抓取包含昨日的數據，確保計算指標(如夜盤均價)不中斷
    start_dt = (now_tw - timedelta(days=1)).strftime('%Y-%m-%d')
    try:
        # 抓取 TMF (微台全)
        df = api.taiwan_futures_tick(futures_id="TMF", date=start_dt)
        if df is None or df.empty:
            return pd.DataFrame()
        
        # 轉換為 3分K
        df['date'] = pd.to_datetime(df['date'] + ' ' + df['time'])
        df = df.set_index('date')
        
        # Resample 成 3分K OHLCV
        ohlc = df['price'].resample('3min').ohlc()
        ohlc['volume'] = df['qty'].resample('3min').sum()
        
        # 移除空值並重設索引
        return ohlc.dropna().reset_index()
    except Exception as e:
        st.error(f"數據抓取失敗: {e}")
        return pd.DataFrame()

# --- 3. 指標運算核心 (3分K 基準) ---
def calculate_all_signals(df):
    if df.empty:
        return df
        
    # 基礎運算 (MA 均線)
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    
    # 當日高低點 (以 08:45 日盤開盤為基準)
    df['day'] = df['date'].dt.date
    df['day_open'] = df.groupby('day')['open'].transform('first')
    df['day_high'] = df.groupby('day')['high'].expanding().max().reset_index(0, drop=True)
    df['day_low'] = df.groupby('day')['low'].expanding().min().reset_index(0, drop=True)

    # --- 買進訊號判定 (B1-B20) ---
    is_red = df['close'] > df['open']
    # 實作幾個核心規則作為範例
    df['B11'] = (df['close'] > df['ma5']).astype(int)      # 5MA之上
    df['B14'] = (is_red & is_red.shift(1) & is_red.shift(2)).astype(int) # 連續三根紅K
    df['B19'] = (df['close'] > df['open'].shift(1)).astype(int)         # 收盤高於前一根開盤
    df['B20'] = (df['volume'] > 2000).astype(int)         # 成交量大於門檻 (微台建議 2000)

    # --- 賣出訊號判定 (S1-S20) ---
    is_green = df['close'] < df['open']
    df['S8'] = (df['close'] < df['day_open']).astype(int)  # 開盤價之下
    df['S11'] = (df['close'] < df['ma5']).astype(int)     # 跌破 5MA
    df['S14'] = (is_green & is_green.shift(1) & is_green.shift(2)).astype(int) # 連續三根綠K
    
    # 積分統計 (將所有 B 開頭與 S 開頭的指標加總)
    df['buy_score'] = df[[c for c in df.columns if c.startswith('B')]].sum(axis=1)
    df['sell_score'] = df[[c for c in df.columns if c.startswith('S')]].sum(axis=1)
    
    # 開盤首4根 K 線規則 (紅燈 1)
    df['is_op_red'] = df.groupby('day')['B14'].transform(lambda x: 1 if x.head(4).max()==1 else 0)
    df['is_op_green'] = df.groupby('day')['S14'].transform(lambda x: 1 if x.head(4).max()==1 else 0)
    
    return df

# --- 4. 介面渲染 ---
st.set_page_config(page_title="TMF 監控系統", layout="wide")
st.title("TMF 微台全 3分K 交易監控")
st.write(f"⏰ **台灣站點時間**: {datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')}")

# 獲取數據
df_raw = get_tmf_data_live(MY_FINMIND_TOKEN)

if not df_raw.empty:
    df = calculate_all_signals(df_raw)
    last = df.iloc[-1]
    
    # 燈號計數邏輯 (每 5 分亮一顆燈)
    r_raw = min(3, (1 if last['is_op_red'] else 0) + (last['buy_score'] // 5))
    g_raw = min(3, (1 if last['is_op_green'] else 0) + (last['sell_score'] // 5))
    
    # Rich 的「後進對消」邏輯：綠燈會扣除紅燈存量
    final_red = max(0, r_raw - g_raw)
    final_green = g_raw

    # 燈號顯示
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🔴 買進紅燈")
        l_html = "".join([f'<div style="width:75px;height:75px;background:{"#FF0000" if i<final_red else "#220000"};border-radius:50%;display:inline-block;margin:10px;border:3px solid white;box-shadow:{"0 0 20px #FF0000" if i<final_red else "none"};"></div>' for i in range(3)])
        st.markdown(l_html, unsafe_allow_html=True)
        st.metric("買進指標積分", f"{int(last['buy_score'])} / 20")

    with c2:
        st.markdown("### 🟢 賣出綠燈")
        l_html = "".join([f'<div style="width:75px;height:75px;background:{"#00FF00" if i<final_green else "#002200"};border-radius:50%;display:inline-block;margin:10px;border:3px solid white;box-shadow:{"0 0 20px #00FF00" if i<final_green else "none"};"></div>' for i in range(3)])
        st.markdown(l_html, unsafe_allow_html=True)
        st.metric("賣出指標積分", f"{int(last['sell_score'])} / 20")

    st.markdown("---")
    st.write("📊 **即時 3分K 數據明細**")
    st.dataframe(df[['date', 'open', 'high', 'low', 'close', 'volume', 'buy_score', 'sell_score']].tail(5))
else:
    st.warning("📡 正在同步 TMF 數據... 請確認目前是否為交易時段 (08:45 - 次日 05:00)。")
