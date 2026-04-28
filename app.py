import streamlit as st
import requests
import re
from datetime import datetime
import pandas as pd
import time

# --- KONFİGÜRASYON ---
FIREBASE_URL = "https://espgsr3-default-rtdb.europe-west1.firebasedatabase.app/history.json?auth=RHH3pZHZbQ0idDw5fJJNazR3mAVduBEqLnV6Yeam"

st.set_page_config(page_title="ESP32-C6 Panel", page_icon="📈", layout="wide")

# HIZLANDIRMA 1: requests.Session() kullanımı
# Her istekte sıfırdan SSL/TCP bağlantısı kurmak yerine bağlantıyı (Keep-Alive) açık tutar.
# İstek süresini ~800ms'den ~50ms'ye düşürür.
if 'http_session' not in st.session_state:
    st.session_state.http_session = requests.Session()

# --- YAN MENÜ (SIDEBAR) AYARLARI ---
st.sidebar.header("⚙️ Kontrol Paneli")

# Sayfa yenileme hızı ayarı
refresh_rate = st.sidebar.slider("Yenileme Hızı (Saniye)", min_value=1, max_value=60, value=1)
st.sidebar.write(f"⏱️ Hedeflenen hız: {refresh_rate} saniye")

st.sidebar.divider()

data_limit = st.sidebar.number_input("Görüntülenecek Son Veri Sayısı", min_value=10, max_value=1000, value=50, step=10)
st.sidebar.info("Performans için sadece en son gelen veriler ekranda tutulur.")

st.title("📈 ESP32-C6 Sensör Geçmişi")

# --- FONKSİYONLAR ---

def fetch_data(limit):
    """Firebase'den veriyi açık HTTP oturumu üzerinden çeker"""
    try:
        params = {
            'orderBy': '"timestamp"',
            'limitToLast': limit
        }
        # requests.get yerine Session üzerinden get yapıyoruz
        response = st.session_state.http_session.get(FIREBASE_URL, params=params, timeout=5)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {}
    except Exception as e:
        st.sidebar.error(f"Bağlantı hatası: {e}")
        return {}

def parse_history(firebase_data):
    """Firebase'den gelen karmaşık veriyi tablo formatına çevirir"""
    parsed_records = []
    
    if not firebase_data or not isinstance(firebase_data, dict): 
        return []
    
    for push_id, record in firebase_data.items():
        if not isinstance(record, dict):
            continue
            
        raw_text = record.get('data', '')
        timestamp_ms = record.get('timestamp', 0)
        
        if timestamp_ms > 0:
            dt_object = datetime.fromtimestamp(timestamp_ms / 1000.0)
            time_str = dt_object.strftime("%H:%M:%S")
        else:
            time_str = "Bilinmiyor"
            
        pattern = r"#\d+%([^%]+)%([^#]+)#"
        matches = re.findall(pattern, raw_text)
        
        row_data = {"Zaman": time_str, "Timestamp": timestamp_ms} 
        
        for match in matches:
            key = match[0].strip()
            value = match[1].strip()
            row_data[key] = value
            
        parsed_records.append(row_data)
        
    return parsed_records

# --- ANA EKRAN İŞLEMLERİ ---

placeholder = st.empty()

while True:
    # HIZLANDIRMA 2: Döngü başlangıç zamanını kaydet
    start_time = time.time()

    raw_data = fetch_data(data_limit)

    with placeholder.container():
        if raw_data:
            records = parse_history(raw_data)
            
            if len(records) > 0:
                df = pd.DataFrame(records)
                df = df.sort_values(by="Timestamp", ascending=False).drop(columns=["Timestamp"])
                latest_data = df.iloc[0]
                
                st.subheader(f"🔴 Canlı Veriler (Son Okuma: {latest_data['Zaman']})")
                
                metric_cols = [col for col in df.columns if col != 'Zaman']
                
                cols = st.columns(len(metric_cols))
                for idx, col_name in enumerate(metric_cols):
                    cols[idx].metric(label=col_name, value=latest_data[col_name])

                st.divider()

                col1, col2 = st.columns([5, 3])
                
                with col1:
                    st.subheader("📉 Zaman İçinde Değişim")
                    chart_df = df.copy()
                    chart_df = chart_df.set_index('Zaman').iloc[::-1]
                    
                    for c in metric_cols:
                        chart_df[c] = pd.to_numeric(chart_df[c], errors='coerce')
                        
                    st.line_chart(chart_df)
                
                with col2:
                    st.subheader(f"📜 Son {len(df)} Kayıt")
                    st.dataframe(df, use_container_width=True, height=400)
            else:
                st.warning("Veriler parçalanamadı. Gönderilen veri formatını kontrol edin.")
        else:
            st.info("Veritabanı boş veya cihazdan veri bekleniyor...")

    # HIZLANDIRMA 3: Dinamik Bekleme Süresi
    # Veriyi çekip ekrana çizmek ne kadar sürdüyse, o süreyi hedef bekleme süresinden çıkar.
    execution_time = time.time() - start_time
    sleep_time = max(0, refresh_rate - execution_time)
    
    # Sadece kalan süre kadar uyu, eğer işlem 1 saniyeden uzun sürdüyse hiç uyuma hemen devam et.
    time.sleep(sleep_time)
