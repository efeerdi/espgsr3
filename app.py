import streamlit as st
import requests
import re
from datetime import datetime
import pandas as pd
import time

# --- AYARLAR ---
# URL'yi latest.json'dan history.json'a değiştirdik
FIREBASE_URL = "https://espgsr3-default-rtdb.europe-west1.firebasedatabase.app/history.json"

st.set_page_config(page_title="ESP32-C6 Geçmiş Paneli", page_icon="📈", layout="wide")
st.title("📈 ESP32-C6 Sensör Geçmişi")

# --- VERİ ÇEKME VE PARÇALAMA ---
def fetch_data():
    try:
        response = requests.get(FIREBASE_URL)
        if response.status_code == 200:
            data = response.json()
            if data:
                return data
        return {}
    except Exception as e:
        st.error(f"Bağlantı hatası: {e}")
        return {}

def parse_history(firebase_data):
    parsed_records = []
    
    # firebase_data bize eşsiz kimliklere sahip bir sözlük (dictionary) döner
    # Örnek: {'-Nabc123': {'data': '#19140%RMS1000%201#', 'timestamp': 1716200000000}}
    
    for push_id, record in firebase_data.items():
        raw_text = record.get('data', '')
        timestamp_ms = record.get('timestamp', 0)
        
        # UNIX zamanını okunabilir tarihe çevir
        if timestamp_ms > 0:
            dt_object = datetime.fromtimestamp(timestamp_ms / 1000.0)
            time_str = dt_object.strftime("%d/%m/%Y %H:%M:%S")
        else:
            time_str = "Bilinmiyor"
            
        # BLE formatını parçala (#ID%KEY%VALUE#)
        pattern = r"#\d+%([^%]+)%([^#]+)#"
        matches = re.findall(pattern, raw_text)
        
        # Tablo için temel bir sözlük oluştur
        row_data = {"Zaman": time_str, "Timestamp": timestamp_ms} 
        
        for match in matches:
            key = match[0].strip()
            value = match[1].strip()
            row_data[key] = value
            
        parsed_records.append(row_data)
        
    return parsed_records

# --- ARAYÜZ (UI) ---
raw_data = fetch_data()

if raw_data:
    # Verileri parçala ve Pandas DataFrame'e çevir (Tablo için en iyisi)
    records = parse_history(raw_data)
    df = pd.DataFrame(records)
    
    # Verileri zamana göre sırala (En yeni en üstte) ve Timestamp sütununu gizle
    df = df.sort_values(by="Timestamp", ascending=False).drop(columns=["Timestamp"])
    
    # En son gelen veriyi ayır
    latest_data = df.iloc[0]
    
    st.subheader("🔴 Canlı Veriler (Son Okuma)")
    st.caption(f"Son Güncelleme: {latest_data['Zaman']}")
    
    # 'Zaman' dışındaki tüm sütunları (RMS değerleri) bul
    metric_cols = [col for col in df.columns if col != 'Zaman']
    
    # En son değerleri büyük kartlar halinde göster
    cols = st.columns(len(metric_cols))
    for idx, col in enumerate(metric_cols):
        cols[idx].metric(label=col, value=latest_data[col])
        
    st.divider()
    
    # Sütunları yan yana koyarak Grafik ve Tabloyu yerleştir
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📉 Zaman İçinde Değişim")
        # Grafiğe dökebilmek için metinleri sayıya çevir
        chart_df = df.copy()
        chart_df = chart_df.set_index('Zaman')
        for col in metric_cols:
            chart_df[col] = pd.to_numeric(chart_df[col], errors='coerce')
        
        # Grafiği soldan sağa doğru akması için ters çevir
        chart_df = chart_df.iloc[::-1] 
        st.line_chart(chart_df[metric_cols])

    with col2:
        st.subheader("📜 Tüm Kayıtlar")
        st.dataframe(df, use_container_width=True, height=400)

else:
    st.info("Veritabanı boş veya veri bekleniyor...")

# Sayfayı her 3 saniyede bir otomatik yenile
time.sleep(3)
st.rerun()