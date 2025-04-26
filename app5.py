
import streamlit as st
import requests
import google.generativeai as genai
from datetime import datetime, timedelta
import pandas as pd
import io
import json
from dateutil import parser

# API Configuration
AMADEUS_API_KEY = "5YWlF018OsxWXu9kMAHRIfBEATNd4irF"
AMADEUS_API_SECRET = "YS1jZZ088P6h5xLk"
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")

# Streamlit Page Config
st.set_page_config(page_title="Sakman AI Travel Assistant", page_icon="✈️", layout="wide")

st.markdown("""
<style>
    .assistant-message { background-color: #e0f7fa; padding: 10px; border-radius: 10px; margin: 10px 0; }
    .user-message { background-color: #f1f8e9; padding: 10px; border-radius: 10px; margin: 10px 0; }
    .flight-card { border: 1px solid #ccc; padding: 15px; border-radius: 10px; margin-bottom: 10px; background-color: #ffffff; }
</style>
""", unsafe_allow_html=True)

# Initialize session
if 'conversation' not in st.session_state:
    st.session_state.conversation = []
if 'form_data' not in st.session_state:
    st.session_state.form_data = {}
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'search_complete' not in st.session_state:
    st.session_state.search_complete = False
if 'travel_guide' not in st.session_state:
    st.session_state.travel_guide = ""
if 'hotels_info' not in st.session_state:
    st.session_state.hotels_info = ""

# Functions
def get_amadeus_token():
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    data = {'grant_type': 'client_credentials', 'client_id': AMADEUS_API_KEY, 'client_secret': AMADEUS_API_SECRET}
    r = requests.post(url, data=data)
    return r.json()['access_token']

def search_flights(form_data):
    token = get_amadeus_token()
    headers = {'Authorization': f'Bearer {token}'}
    params = {
        "originLocationCode": form_data["origin"],
        "destinationLocationCode": form_data["destination"],
        "departureDate": form_data["departure_date"],
        "adults": form_data["travelers"],
        "travelClass": form_data["flight_class"],
        "currencyCode": "USD",
        "max": 5
    }
    r = requests.get("https://test.api.amadeus.com/v2/shopping/flight-offers", headers=headers, params=params)
    return r.json()

def process_flights(data):
    flights = []
    if 'data' not in data:
        return flights
    for offer in data['data']:
        segments = offer['itineraries'][0]['segments']
        dep = parser.parse(segments[0]['departure']['at'])
        arr = parser.parse(segments[-1]['arrival']['at'])
        flights.append({
            "From": segments[0]['departure']['iataCode'],
            "To": segments[-1]['arrival']['iataCode'],
            "Departure": dep.strftime("%Y-%m-%d %H:%M"),
            "Arrival": arr.strftime("%Y-%m-%d %H:%M"),
            "Price (USD)": offer['price']['grandTotal']
        })
    return flights

def download_excel(data):
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Flights')
    output.seek(0)
    return output

def fetch_travel_guide(dest):
    prompt = f"Suggest top 5 things to do in {dest} as a friendly list."
    response = model.generate_content(prompt)
    return response.text.strip()

def fetch_hotels(dest):
    prompt = f"Suggest top 5 hotels in {dest} with approximate price range."
    response = model.generate_content(prompt)
    return response.text.strip()

# App starts
st.title("✈️ Sakman AI Travel Assistant")

# Show conversation
for chat in st.session_state.conversation:
    with st.container():
        st.markdown(f"<div class='{chat['role']}-message'><b>{chat['role'].capitalize()}:</b> {chat['content']}</div>", unsafe_allow_html=True)

# Chat input
user_input = st.chat_input("Tell me your trip plan! (e.g., I want to fly from Delhi to Doha on May 5th)")

if user_input:
    st.session_state.conversation.append({"role": "user", "content": user_input})
    st.session_state.form_data = {
        "origin": "DEL",
        "destination": "DOH",
        "departure_date": (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d"),
        "return_date": "",
        "travelers": 1,
        "flight_class": "ECONOMY"
    }
    st.rerun()

# Once form_data is filled
if st.session_state.form_data and not st.session_state.search_complete:
    with st.spinner("Searching for flights..."):
        raw = search_flights(st.session_state.form_data)
        st.session_state.search_results = process_flights(raw)
        st.session_state.travel_guide = fetch_travel_guide(st.session_state.form_data["destination"])
        st.session_state.hotels_info = fetch_hotels(st.session_state.form_data["destination"])
        st.session_state.search_complete = True
        st.session_state.conversation.append({"role": "assistant", "content": f"Here are some amazing flight options from {st.session_state.form_data['origin']} to {st.session_state.form_data['destination']}! ✈️"})
    st.rerun()

if st.session_state.search_complete:
    st.subheader("📋 Your Trip Summary")
    st.success(f"🛫 {st.session_state.form_data['origin']} → {st.session_state.form_data['destination']} | 📅 Departure: {st.session_state.form_data['departure_date']} | 👤 Travelers: {st.session_state.form_data['travelers']} | 🎟️ Class: {st.session_state.form_data['flight_class'].capitalize()}")

    st.subheader("✈️ Flight Options")
    for flight in st.session_state.search_results:
        with st.container():
            st.markdown(f"<div class='flight-card'><b>{flight['From']} ➔ {flight['To']}</b><br>Departure: {flight['Departure']} | Arrival: {flight['Arrival']}<br>💲Price: {flight['Price (USD)']} USD</div>", unsafe_allow_html=True)

    excel = download_excel(st.session_state.search_results)
    st.download_button("📥 Download Flights Excel", excel, "flights.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.subheader("🌟 Travel Guide")
    st.markdown(st.session_state.travel_guide)

    st.subheader("🏨 Top Hotels")
    st.markdown(st.session_state.hotels_info)

    # Allow more natural conversation
    followup = st.chat_input("Ask me more about your destination! (e.g., best beaches in Doha)")
    if followup:
        ai_response = model.generate_content(followup)
        st.session_state.conversation.append({"role": "user", "content": followup})
        st.session_state.conversation.append({"role": "assistant", "content": ai_response.text.strip()})
        st.rerun()
