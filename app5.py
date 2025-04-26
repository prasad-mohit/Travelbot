
import streamlit as st
import requests
import google.generativeai as genai
from datetime import datetime
from dateutil import parser
import pandas as pd
import json

# Configure API keys
AMADEUS_API_KEY = "5YWlF018OsxWXu9kMAHRIfBEATNd4irF"
AMADEUS_API_SECRET = "YS1jZZ088P6h5xLk"
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")

# Streamlit app setup
st.set_page_config(page_title="Sakman AI Travel Assistant", page_icon="✈️", layout="wide")

st.markdown("""
<style>
    .header { background: linear-gradient(135deg, #4a8cff 0%, #2a56d6 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
    .assistant-message { background-color: #f0f8ff; padding: 12px; border-radius: 10px; margin: 8px 0; }
    .user-message { background-color: #e6f2ff; padding: 12px; border-radius: 10px; margin: 8px 0; }
</style>
""", unsafe_allow_html=True)

# --- Session State ---
if 'conversation' not in st.session_state:
    st.session_state.conversation = []
if 'form_data' not in st.session_state:
    st.session_state.form_data = {"origin": "", "destination": "", "departure_date": "", "return_date": "", "travelers": 1, "flight_class": "ECONOMY"}
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'search_complete' not in st.session_state:
    st.session_state.search_complete = False
if 'travel_guide' not in st.session_state:
    st.session_state.travel_guide = ""
if 'hotel_suggestions' not in st.session_state:
    st.session_state.hotel_suggestions = ""

# --- Functions ---
def get_amadeus_token():
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'grant_type': 'client_credentials', 'client_id': AMADEUS_API_KEY, 'client_secret': AMADEUS_API_SECRET}
    try:
        response = requests.post(url, headers=headers, data=data)
        return response.json()['access_token']
    except:
        st.error("Amadeus token error")
        return None

def search_flights(form_data):
    token = get_amadeus_token()
    if not token:
        return None
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    params = {"originLocationCode": form_data["origin"], "destinationLocationCode": form_data["destination"],
              "departureDate": form_data["departure_date"], "adults": form_data["travelers"], "max": 10,
              "currencyCode": "OMR", "travelClass": form_data["flight_class"].upper()}
    if form_data["return_date"]:
        params["returnDate"] = form_data["return_date"]
    response = requests.get(url, headers=headers, params=params)
    return response.json() if response.status_code == 200 else None

def process_flight_data(flight_data):
    flights = []
    if not flight_data or 'data' not in flight_data:
        return []
    for offer in flight_data['data']:
        segments = offer['itineraries'][0]['segments']
        dep = parser.parse(segments[0]['departure']['at'])
        arr = parser.parse(segments[-1]['arrival']['at'])
        price = offer['price']['grandTotal']
        flights.append({"From": segments[0]['departure']['iataCode'],
                        "To": segments[-1]['arrival']['iataCode'],
                        "Departure": dep.strftime("%Y-%m-%d %H:%M"),
                        "Arrival": arr.strftime("%Y-%m-%d %H:%M"),
                        "Price (OMR)": price})
    return flights

def fetch_travel_guide(destination):
    prompt = f"Suggest 5 best things to do in {destination}. Return it as a bullet list."
    response = model.generate_content(prompt)
    return response.text.strip()

def fetch_hotels(destination):
    prompt = f"Suggest 5 good hotels to stay in {destination} with approximate price range."
    response = model.generate_content(prompt)
    return response.text.strip()

def download_excel(flights):
    df = pd.DataFrame(flights)
    return df.to_excel(index=False, engine='openpyxl')

# --- App Body ---
st.title("✈️ Sakman AI Travel Assistant")

for msg in st.session_state.conversation:
    role = msg['role']
    content = msg['content']
    st.markdown(f"<div class='{role}-message'><b>{role.capitalize()}:</b> {content}</div>", unsafe_allow_html=True)

user_input = st.chat_input("Where would you like to travel?")

if user_input:
    st.session_state.conversation.append({"role": "user", "content": user_input})
    # Extract minimal info (for demo purposes; real app would parse IATA etc.)
    st.session_state.form_data["origin"] = "DEL"
    st.session_state.form_data["destination"] = "DOH"
    st.session_state.form_data["departure_date"] = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    st.session_state.search_complete = False
    st.rerun()

if st.session_state.form_data["origin"] and not st.session_state.search_complete:
    flight_data = search_flights(st.session_state.form_data)
    flights = process_flight_data(flight_data)
    if flights:
        st.session_state.search_results = flights
        st.session_state.search_complete = True
        st.session_state.travel_guide = fetch_travel_guide(st.session_state.form_data["destination"])
        st.session_state.hotel_suggestions = fetch_hotels(st.session_state.form_data["destination"])
        st.session_state.conversation.append({"role": "assistant", "content": f"Here are flights from {st.session_state.form_data['origin']} to {st.session_state.form_data['destination']}! ✈️"})
        st.rerun()

if st.session_state.search_complete and st.session_state.search_results:
    st.subheader("🛫 Flight Options")
    df = pd.DataFrame(st.session_state.search_results)
    st.dataframe(df)
    st.download_button("📥 Download Flights as Excel", data=download_excel(st.session_state.search_results), file_name="flight_options.xlsx")

    st.subheader("📍 Things to Do")
    st.markdown(st.session_state.travel_guide)

    st.subheader("🏨 Top Hotels")
    st.markdown(st.session_state.hotel_suggestions)

    # Allow chatting again
    user_followup = st.chat_input("Ask me more about your trip! (e.g., 'Tell me best food in Doha')")
    if user_followup:
        reply = model.generate_content(user_followup)
        st.session_state.conversation.append({"role": "user", "content": user_followup})
        st.session_state.conversation.append({"role": "assistant", "content": reply.text.strip()})
        st.rerun()
