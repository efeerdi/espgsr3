import streamlit as st
import requests
import re
import time

# --- CONFIGURATION ---
# Replace this with your actual Firebase URL (must end in .json)
FIREBASE_URL = "https://espgsr3-default-rtdb.europe-west1.firebasedatabase.app/lastest.json"

# Set up the web page layout
st.set_page_config(page_title="ESP32-C6 Dashboard", page_icon="📡", layout="wide")
st.title("📡 Live ESP32-C6 Sensor Dashboard")
st.markdown("This dashboard fetches real-time BLE data relayed via Wi-Fi.")

# --- DATA FETCHING & PARSING ---
def get_latest_data():
    try:
        response = requests.get(FIREBASE_URL)
        if response.status_code == 200:
            return response.text # Returns the raw string sent by ESP32
        else:
            return None
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

def parse_payload(raw_text):
    parsed_data = {}
    if not raw_text:
        return parsed_data
    
    # This pattern handles multi-line strings from your log
    pattern = r"#\d+%([^%]+)%([^#]+)#"
    matches = re.findall(pattern, raw_text)
    
    for match in matches:
        key = match[0].strip()
        value = match[1].strip()
        parsed_data[key] = value
        
    return parsed_data

# --- UI LAYOUT ---
# Create empty containers to update data without redrawing the whole page
raw_data_container = st.empty()
metrics_container = st.empty()

# --- MAIN LOOP FOR LIVE UPDATES ---
raw_text = get_latest_data()
parsed_data = parse_payload(raw_text)

with raw_data_container.container():
    st.subheader("Raw Payload")
    st.code(raw_text, language="text")

with metrics_container.container():
    st.subheader("Parsed Sensor Values")
    if parsed_data:
        # Create columns dynamically based on how many data points exist
        cols = st.columns(len(parsed_data))
        
        # Loop through the dictionary and create a metric card for each
        for idx, (key, value) in enumerate(parsed_data.items()):
            cols[idx].metric(label=key, value=value)
    else:
        st.info("No valid data found in the payload or waiting for ESP32 connection.")

# Force the script to rerun every 3 seconds to fetch new data
time.sleep(3)
st.rerun()