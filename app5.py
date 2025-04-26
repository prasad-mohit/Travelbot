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

# Configure Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")

# Streamlit Page Config
st.set_page_config(
    page_title="Sakman AI Travel Assistant", 
    page_icon="✈️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS with improved flight cards
st.markdown("""
<style>
    .assistant-message { 
        background-color: #e0f7fa; 
        padding: 15px; 
        border-radius: 10px; 
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .user-message { 
        background-color: #f1f8e9; 
        padding: 15px; 
        border-radius: 10px; 
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .flight-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        background: white;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    .flight-card.selected {
        border: 2px solid #4CAF50;
        background-color: #f8fff8;
    }
    .flight-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .flight-title {
        font-weight: 600;
        font-size: 18px;
        color: #2c3e50;
    }
    .flight-price {
        font-weight: bold;
        font-size: 20px;
        color: #27ae60;
    }
    .flight-details {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
        margin-bottom: 10px;
    }
    .detail-row {
        display: flex;
    }
    .detail-label {
        font-weight: 600;
        min-width: 140px;
        color: #7f8c8d;
    }
    .detail-value {
        color: #2c3e50;
    }
    .fee-badge {
        background-color: #e74c3c;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    .baggage-badge {
        background-color: #3498db;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    .policy-badge {
        background-color: #2ecc71;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    .section-header {
        color: #2a56d6;
        margin-top: 20px;
        margin-bottom: 10px;
    }
    .info-card {
        border-left: 4px solid #4a8cff;
        padding: 12px;
        margin: 10px 0;
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
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
if 'destination_name' not in st.session_state:
    st.session_state.destination_name = ""
if 'selected_flight' not in st.session_state:
    st.session_state.selected_flight = None

# Airport code mapping
AIRPORT_CODES = {
    "DEL": "Delhi", "BOM": "Mumbai", "DOH": "Doha",
    "LHR": "London", "DXB": "Dubai", "JFK": "New York",
    "SIN": "Singapore", "BKK": "Bangkok", "MCT": "Muscat"
}

# Helper Functions
def get_amadeus_token():
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    data = {
        'grant_type': 'client_credentials',
        'client_id': AMADEUS_API_KEY,
        'client_secret': AMADEUS_API_SECRET
    }
    try:
        r = requests.post(url, data=data)
        return r.json()['access_token']
    except Exception as e:
        st.error(f"Failed to get Amadeus token: {str(e)}")
        return None

def search_flights(form_data):
    token = get_amadeus_token()
    if not token:
        return None
    
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
    
    if form_data.get("return_date"):
        params["returnDate"] = form_data["return_date"]
    
    try:
        r = requests.get(
            "https://test.api.amadeus.com/v2/shopping/flight-offers", 
            headers=headers, 
            params=params
        )
        return r.json()
    except Exception as e:
        st.error(f"Flight search failed: {str(e)}")
        return None

def process_flights(data):
    flights = []
    if not data or 'data' not in data:
        return flights
    
    for offer in data['data']:
        try:
            segments = offer['itineraries'][0]['segments']
            dep = parser.parse(segments[0]['departure']['at'])
            arr = parser.parse(segments[-1]['arrival']['at'])
            duration = arr - dep
            hours, remainder = divmod(duration.seconds, 3600)
            minutes = remainder // 60
            
            # Generate baggage info (mock since Amadeus doesn't always provide this)
            baggage_checkin = "20kg" if offer['price']['grandTotal'] > 300 else "15kg"
            baggage_cabin = "7kg" if offer['travelClass'] == "ECONOMY" else "10kg"
            
            flights.append({
                "Airline": segments[0]['carrierCode'],
                "From": segments[0]['departure']['iataCode'],
                "To": segments[-1]['arrival']['iataCode'],
                "Departure": dep.strftime("%a, %d %b %Y %H:%M"),
                "Arrival": arr.strftime("%a, %d %b %Y %H:%M"),
                "Duration": f"{hours}h {minutes}m",
                "Base Price (USD)": float(offer['price']['grandTotal']),
                "Stops": len(segments) - 1,
                "Aircraft": segments[0]['aircraft']['code'],
                "Flight Number": f"{segments[0]['carrierCode']}{segments[0]['number']}",
                "Baggage Check-in": baggage_checkin,
                "Baggage Cabin": baggage_cabin,
                "Cancellation Policy": "Free within 24 hours" if offer['price']['grandTotal'] > 400 else "Non-refundable",
                "Refund Policy": "Full refund" if offer['price']['grandTotal'] > 400 else "Credit only",
                "SSL Fee": 25,
                "Total Price (USD)": float(offer['price']['grandTotal']) + 25
            })
        except Exception as e:
            st.warning(f"Skipping flight due to processing error: {str(e)}")
            continue
    
    return flights

def download_excel(data):
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Flights')
    output.seek(0)
    return output

def generate_travel_content(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        st.error(f"Error generating content: {str(e)}")
        return "Content not available at the moment."

def extract_travel_details(user_input):
    prompt = f"""Extract travel details from this request: "{user_input}"
    Return JSON with:
    - origin (IATA code)
    - destination (IATA code)
    - departure_date (YYYY-MM-DD)
    - return_date (YYYY-MM-DD or empty)
    - travelers (number)
    - flight_class (ECONOMY/PREMIUM_ECONOMY/BUSINESS/FIRST)
    
    Example:
    {{
        "origin": "DEL",
        "destination": "DOH",
        "departure_date": "2024-05-15",
        "return_date": "",
        "travelers": 2,
        "flight_class": "ECONOMY"
    }}"""
    
    try:
        response = model.generate_content(prompt)
        clean_json = response.text.strip().strip('```json').strip('```').strip()
        return json.loads(clean_json)
    except Exception as e:
        st.error(f"Couldn't understand your request. Please try being more specific.")
        return None

# Main App
st.title("✈️ Sakman AI Travel Assistant")
st.markdown("Your personal travel planning companion powered by AI")

# Display conversation
for chat in st.session_state.conversation:
    with st.container():
        st.markdown(
            f"<div class='{chat['role']}-message'><b>{chat['role'].capitalize()}:</b> {chat['content']}</div>", 
            unsafe_allow_html=True
        )

# User input
user_input = st.chat_input("Tell me about your trip (e.g., 'I want to fly from Delhi to Doha on May 15th for 2 people')")

if user_input:
    st.session_state.conversation.append({"role": "user", "content": user_input})
    
    # Extract travel details
    details = extract_travel_details(user_input)
    if details:
        st.session_state.form_data = details
        st.session_state.destination_name = AIRPORT_CODES.get(details["destination"], details["destination"])
        
        # Add confirmation message
        confirmation = f"Great! I'll find flights from {AIRPORT_CODES.get(details['origin'], details['origin'])} "
        confirmation += f"to {st.session_state.destination_name} on {details['departure_date']}"
        if details.get('return_date'):
            confirmation += f", returning {details['return_date']}"
        confirmation += f" for {details['travelers']} traveler(s) in {details['flight_class'].capitalize()} class."
        
        st.session_state.conversation.append({"role": "assistant", "content": confirmation})
    st.rerun()

# Process flight search when form_data is ready
if st.session_state.form_data and not st.session_state.search_complete:
    with st.spinner("🔍 Searching for flights and travel information..."):
        # Get flights
        raw_flights = search_flights(st.session_state.form_data)
        st.session_state.search_results = process_flights(raw_flights)
        
        # Get travel guide
        travel_prompt = f"""Create a comprehensive travel guide for {st.session_state.destination_name} including:
        - Top 5 attractions with descriptions
        - Local cuisine recommendations
        - Cultural tips
        - Best times to visit each attraction
        Format as markdown with headings."""
        st.session_state.travel_guide = generate_travel_content(travel_prompt)
        
        # Get hotel recommendations
        hotels_prompt = f"""List 5 recommended hotels in {st.session_state.destination_name} with:
        - Property name
        - Price range (USD)
        - Location/neighborhood
        - Key amenities
        - Guest rating
        Format as markdown with headings."""
        st.session_state.hotels_info = generate_travel_content(hotels_prompt)
        
        st.session_state.search_complete = True
        st.session_state.conversation.append({
            "role": "assistant", 
            "content": f"Here are your travel options for {st.session_state.destination_name}! ✈️"
        })
    st.rerun()

# Display results
if st.session_state.search_complete:
    st.markdown("---")
    st.subheader("📋 Your Trip Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("From", AIRPORT_CODES.get(st.session_state.form_data['origin'], st.session_state.form_data['origin']))
    with col2:
        st.metric("To", st.session_state.destination_name)
    with col3:
        st.metric("Departure", st.session_state.form_data['departure_date'])
    with col4:
        st.metric("Class", st.session_state.form_data['flight_class'].capitalize())

    st.markdown("---")
    st.subheader("✈️ Flight Options")
    
    if not st.session_state.search_results:
        st.warning("No flights found for your criteria. Try adjusting your search.")
    else:
        for i, flight in enumerate(st.session_state.search_results):
            selected_class = "selected" if st.session_state.selected_flight == i else ""
            with st.container():
                st.markdown(f"""
                <div class='flight-card {selected_class}'>
                    <div class='flight-header'>
                        <div class='flight-title'>{flight['From']} → {flight['To']}</div>
                        <div class='flight-price'>${flight['Total Price (USD)']:.2f}</div>
                    </div>
                    <div class='flight-details'>
                        <div class='detail-row'>
                            <span class='detail-label'>Departure:</span>
                            <span class='detail-value'>{flight['Departure']}</span>
                        </div>
                        <div class='detail-row'>
                            <span class='detail-label'>Arrival:</span>
                            <span class='detail-value'>{flight['Arrival']}</span>
                        </div>
                        <div class='detail-row'>
                            <span class='detail-label'>Duration:</span>
                            <span class='detail-value'>{flight['Duration']}</span>
                        </div>
                        <div class='detail-row'>
                            <span class='detail-label'>Flight Number:</span>
                            <span class='detail-value'>{flight['Airline']} {flight['Flight Number']}</span>
                        </div>
                        <div class='detail-row'>
                            <span class='detail-label'>Baggage:</span>
                            <span class='detail-value'>
                                <span class='baggage-badge'>Check-in: {flight['Baggage Check-in']}</span>
                                <span class='baggage-badge'>Cabin: {flight['Baggage Cabin']}</span>
                            </span>
                        </div>
                        <div class='detail-row'>
                            <span class='detail-label'>Policies:</span>
                            <span class='detail-value'>
                                <span class='policy-badge'>{flight['Cancellation Policy']}</span>
                                <span class='policy-badge'>{flight['Refund Policy']}</span>
                            </span>
                        </div>
                        <div class='detail-row'>
                            <span class='detail-label'>Stops:</span>
                            <span class='detail-value'>{flight['Stops']}</span>
                        </div>
                        <div class='detail-row'>
                            <span class='detail-label'>Aircraft:</span>
                            <span class='detail-value'>{flight['Aircraft']}</span>
                        </div>
                        <div class='detail-row'>
                            <span class='detail-label'>Fees:</span>
                            <span class='detail-value'>
                                <span class='fee-badge'>SSL: ${flight['SSL Fee']}</span>
                            </span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Select Flight #{i+1}", key=f"select_{i}"):
                    st.session_state.selected_flight = i
                    st.rerun()
        
        # Download button
        excel_data = download_excel(st.session_state.search_results)
        st.download_button(
            label="📥 Download Flight Details (Excel)",
            data=excel_data,
            file_name=f"flights_{st.session_state.form_data['origin']}_to_{st.session_state.form_data['destination']}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.markdown("---")
    st.subheader("🌟 Travel Guide")
    st.markdown(st.session_state.travel_guide)

    st.markdown("---")
    st.subheader("🏨 Recommended Hotels")
    st.markdown(st.session_state.hotels_info)

    # Follow-up conversation
    st.markdown("---")
    st.subheader("💬 Need more information?")
    followup = st.chat_input(f"Ask me anything about {st.session_state.destination_name}...")
    
    if followup:
        st.session_state.conversation.append({"role": "user", "content": followup})
        with st.spinner("Thinking..."):
            response = model.generate_content(f"About {st.session_state.destination_name}: {followup}")
            st.session_state.conversation.append({"role": "assistant", "content": response.text})
        st.rerun()
