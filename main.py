import streamlit as st
import pandas as pd
import numpy as np
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, time, timedelta

# --- 極速更新設定 (1秒) ---
st_autorefresh(interval=1000, key="tmf_realtime_monitor")

# --- 數據獲取與快取保護 ---
@st.cache_data(ttl=2)  # 每2秒才允許真正請求一次 API
def get_tmf_data(token=""):
    api = DataLoader()
    # 抓取包含昨日的數據，確保指標17(夜盤均價)能計算
    start_dt = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    try:
        df = api.taiwan_futures_tick(futures_id="TMF", date=start_dt)
        if df.empty: return pd.DataFrame()
        
        # 轉換為 3分K
        df['date'] = pd.to_datetime(df['date'] + ' ' + df['time'])
        df = df.set_index('date')
        ohlc = df['price'].resample('3min').ohlc()
        ohlc['volume'] = df['qty'].resample('3min').sum()
        return ohlc.dropna().reset_index()
    except:
        return pd.DataFrame()

# --- 40 個指標運算 (全 3分K 基準) ---
def calculate_logic(df):
    if df.empty: return df
    
    # 基礎運算
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['day'] = df['date'].dt.date
    df['day_open'] = df.groupby('day')['open'].transform('first')
    df['day_high'] = df.groupby('day')['high'].expanding().max().reset_index(0, drop=True)
    df['day_low'] = df.groupby('day')['low'].expanding().min().reset_index(0, drop=True)

    # 8:45-9:05 區間 (指標10)
    mask_905 = (df['date'].dt.time >= time(8,45)) & (df['date'].dt.time <= time(9,5))
    df['box_h'] = df[mask_905].groupby('day')['high'].transform('max')
    df['box_l'] = df[mask_905].groupby('day')['low'].transform('min')
    df[['box_h', 'box_l']] = df.groupby('day')[['box_h', 'box_l']].ffill()

    # 買進指標 (B1-B20) - 示例核心邏輯
    is_red = df['close'] > df['open']
    df['B11'] = (df['close'] > df['ma5']).astype(int)
    df['B14'] = (is_red & is_red.shift(1) & is_red.shift(2)).astype(int)
    df['B19'] = (df['close'] > df['open'].shift(1)).astype(int)
    df['B20'] = (df['volume'] > 5000).astype(int) # 注意微台量級

    # 賣出指標 (S1-S20)
    is_green = df['close'] < df['open']
    df['S8'] = (df['close'] < df['day_open']).astype(int)
    df['S11'] = (df['close'] < df['ma5']).astype(int)
    df['S14'] = (is_green & is_green.shift(1) & is_green.shift(2)).astype(int)

    # 積分統計
    df['buy_score'] = df[[c for c in df.columns if c.startswith('B')]].sum(axis=1)
    df['sell_score'] = df[[c for c in df.columns if c.startswith('S')]].sum(axis=1)
    
    # 開盤規則
    df['is_op_red'] = df.groupby('day')['B14'].transform(lambda x: 1 if x.head(4).max()==1 else 0)
    df['is_op_green'] = df.groupby('day')['S14'].transform(lambda x: 1 if x.head(4).max()==1 else 0)
    
    return df

# --- 燈號處理邏輯 ---
def process_lights(row):
    # 原始紅燈/綠燈計算 (開盤1 + 每5個訊號+1)
    r_raw = min(3, (1 if row['is_op_red'] else 0) + (row['buy_score'] // 5))
    g_raw = min(3, (1 if row['is_op_green'] else 0) + (row['sell_score'] // 5))

    # Rich 的邏輯：後增加的留著，前面的對方的會減少
    # 綠燈會抵銷紅燈，但綠燈自己會亮起
    display_red = max(0, r_raw - g_raw)
    display_green = g_raw 
    
    return int(display_red), int(display_green)

# --- UI 渲染 ---
st.title("TMF 3分K 極速監控儀表板")
st.markdown(f"系統時間: {datetime.now().strftime('%H:%M:%S')}")

df_raw = get_tmf_data()
if not df_raw.empty:
    df = calculate_logic(df_raw)
    last_row = df.iloc[-1]
    r_cnt, g_cnt = process_lights(last_row)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("買進紅燈")
        # CSS 圓燈
        l_html = "".join([f'<div style="width:45px;height:45px;background:{"red" if i<r_cnt else "#220000"};border-radius:50%;display:inline-block;margin:5px;border:2px solid white;"></div>' for i in range(3)])
        st.markdown(l_html, unsafe_allow_html=True)
        st.metric("買進積分", int(last_row['buy_score']))

    with c2:
        st.subheader("賣出綠燈")
        l_html = "".join([f'<div style="width:45px;height:45px;background:{"#00FF00" if i<g_cnt else "#002200"};border-radius:50%;display:inline-block;margin:5px;border:2px solid white;"></div>' for i in range(3)])
        st.markdown(l_html, unsafe_allow_html=True)
        st.metric("賣出積分", int(last_row['sell_score']))

    st.markdown("---")
    st.write("#### 數據明細")
    st.dataframe(df[['date', 'close', 'buy_score', 'sell_score']].tail(5))
else:
    st.info("等待 TMF 數據更新中...")
