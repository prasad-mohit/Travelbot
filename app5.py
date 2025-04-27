import streamlit as st
import requests
import google.generativeai as genai
from datetime import datetime, timedelta
import pandas as pd
import io
import json
from dateutil import parser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# API Configuration
AMADEUS_API_KEY = "5YWlF018OsxWXu9kMAHRIfBEATNd4irF"
AMADEUS_API_SECRET = "YS1jZZ088P6h5xLk"
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
EMAIL_SENDER = "sakmantravels@gmail.com"
EMAIL_PASSWORD = st.secrets.get("EMAIL_PASSWORD")  # Store in Streamlit secrets

# Configure Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")

# Currency Conversion
USD_TO_OMR = 0.385  # 1 USD = 0.385 OMR (approximate rate)

# Streamlit Page Config
st.set_page_config(
    page_title="Sakman AI Travel Assistant Pro Max",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Theme Configuration
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

# Custom CSS with Theme Support
def get_theme_css():
    if st.session_state.theme == 'dark':
        return """
        <style>
            .main { background-color: #1f2937; color: #f3f4f6; }
            .assistant-message {
                background-color: #374151;
                color: #e5e7eb;
                padding: 15px;
                border-radius: 10px;
                margin: 10px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
            .user-message {
                background-color: #4b5563;
                color: #e5e7eb;
                padding: 15px;
                border-radius: 10px;
                margin: 10px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
            .flight-card {
                border: 1px solid #4b5563;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
                background: #374151;
                color: #e5e7eb;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                transition: transform 0.2s;
            }
            .flight-card:hover {
                transform: translateY(-5px);
            }
            .flight-card.selected {
                border: 2px solid #60a5fa;
                background-color: #4b5563;
            }
            .flight-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
            }
            .flight-title {
                font-weight: 700;
                font-size: 20px;
                color: #bfdbfe;
            }
            .flight-price {
                font-weight: bold;
                font-size: 22px;
                color: #60a5fa;
            }
            .flight-details {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                margin-bottom: 15px;
            }
            .detail-row {
                display: flex;
                align-items: center;
            }
            .detail-label {
                font-weight: 600;
                min-width: 140px;
                color: #9ca3af;
            }
            .detail-value {
                color: #d1d5db;
                font-size: 14px;
            }
            .fee-badge {
                background-color: #ef4444;
                color: white;
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
            }
            .baggage-badge {
                background-color: #3b82f6;
                color: white;
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
            }
            .policy-badge {
                background-color: #22c55e;
                color: white;
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
            }
            .section-header {
                color: #60a5fa;
                margin-top: 25px;
                margin-bottom: 15px;
                font-size: 24px;
                font-weight: 700;
            }
            .info-card {
                border-left: 4px solid #3b82f6;
                padding: 15px;
                margin: 15px 0;
                background-color: #4b5563;
                color: #e5e7eb;
                border-radius: 8px;
            }
            .stChatInput {
                background-color: #ffffff !important;
                border: 1px solid #6b7280 !important;
                border-radius: 8px !important;
                padding: 10px !important;
            }
            .stChatInput > div > input {
                color: #1f2937 !important;
                background-color: #ffffff !important;
            }
            .stChatInput > div > input::placeholder {
                color: #6b7280 !important;
            }
            .stButton > button {
                background-color: #3b82f6;
                color: white;
                border-radius: 8px;
                padding: 8px 16px;
            }
            .stButton > button:hover {
                background-color: #2563eb;
            }
        </style>
        """
    else:
        return """
        <style>
            .main { background-color: #f9fafb; color: #1f2937; }
            .assistant-message {
                background-color: #e6f3ff;
                padding: 15px;
                border-radius: 10px;
                margin: 10px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .user-message {
                background-color: #f0fff4;
                padding: 15px;
                border-radius: 10px;
                margin: 10px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .flight-card {
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
                background: #ffffff;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                transition: transform 0.2s;
            }
            .flight-card:hover {
                transform: translateY(-5px);
            }
            .flight-card.selected {
                border: 2px solid #2a56d6;
                background-color: #f8faff;
            }
            .flight-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
            }
            .flight-title {
                font-weight: 700;
                font-size: 20px;
                color: #1a3c5e;
            }
            .flight-price {
                font-weight: bold;
                font-size: 22px;
                color: #2a56d6;
            }
            .flight-details {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                margin-bottom: 15px;
            }
            .detail-row {
                display: flex;
                align-items: center;
            }
            .detail-label {
                font-weight: 600;
                min-width: 140px;
                color: #6b7280;
            }
            .detail-value {
                color: #1f2937;
                font-size: 14px;
            }
            .fee-badge {
                background-color: #dc2626;
                color: white;
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
            }
            .baggage-badge {
                background-color: #2563eb;
                color: white;
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
            }
            .policy-badge {
                background-color: #16a34a;
                color: white;
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
            }
            .section-header {
                color: #1e40af;
                margin-top: 25px;
                margin-bottom: 15px;
                font-size: 24px;
                font-weight: 700;
            }
            .info-card {
                border-left: 4px solid #2563eb;
                padding: 15px;
                margin: 15px 0;
                background-color: #f9fafb;
                border-radius: 8px;
            }
            .stChatInput {
                background-color: #ffffff !important;
                border: 1px solid #d1d5db !important;
                border-radius: 8px !important;
                padding: 10px !important;
            }
            .stChatInput > div > input {
                color: #1f2937 !important;
                background-color: #ffffff !important;
            }
            .stChatInput > div > input::placeholder {
                color: #9ca3af !important;
            }
            .stButton > button {
                background-color: #2563eb;
                color: white;
                border-radius: 8px;
                padding: 8px 16px;
            }
            .stButton > button:hover {
                background-color: #1e40af;
            }
        </style>
        """

st.markdown(get_theme_css(), unsafe_allow_html=True)

# Sidebar for Theme Switcher
with st.sidebar:
    st.header("Settings")
    theme = st.selectbox("Theme", ["Light", "Dark"], index=0 if st.session_state.theme == 'light' else 1)
    if theme.lower() != st.session_state.theme:
        st.session_state.theme = theme.lower()
        st.rerun()

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

def convert_to_omr(price_usd):
    return round(float(price_usd) * USD_TO_OMR, 2)

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
            
            try:
                base_price_usd = float(offer['price']['grandTotal'])
            except (KeyError, TypeError, ValueError):
                base_price_usd = 0.0
            
            base_price_omr = convert_to_omr(base_price_usd)
            ssl_fee_usd = 25
            ssl_fee_omr = convert_to_omr(ssl_fee_usd)
            
            baggage_checkin = "20kg" if base_price_usd > 300 else "15kg"
            baggage_cabin = "7kg" if offer.get('travelClass', "ECONOMY") == "ECONOMY" else "10kg"
            
            flights.append({
                "Airline": segments[0].get('carrierCode', c'Unknown'),
                "From": segments[0]['departure'].get('iataCode', 'Unknown'),
                "To": segments[-1]['arrival'].get('iataCode', 'Unknown'),
                "Departure": dep.strftime("%a, %d %b %Y %H:%M"),
                "Arrival": arr.strftime("%a, %d %b %Y %H:%M"),
                "Duration": f"{hours}h {minutes}m",
                "Base Price (OMR)": base_price_omr,
                "Stops": len(segments) - 1,
                "Aircraft": segments[0].get('aircraft', {}).get('code', 'Unknown'),
                "Flight Number": f"{segments[0].get('carrierCode', '')}{segments[0].get('number', '')}",
                "Baggage Check-in": baggage_checkin,
                "Baggage Cabin": baggage_cabin,
                "Cancellation Policy": "Free within 24 hours" if base_price_usd > 400 else "Non-refundable",
                "Refund Policy": "Full refund" if base_price_usd > 400 else "Credit only",
                "SSL Fee (OMR)": ssl_fee_omr,
                "Total Price (OMR)": base_price_omr + ssl_fee_omr
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

def send_flight_email(recipient_email, flight_data, origin, destination):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = recipient_email
        msg['Subject'] = f"Flight Options from {origin} to {destination}"
        
        body = "Dear Traveler,\n\nHere are your requested flight options:\n\n"
        for i, flight in enumerate(flight_data, 1):
            body += f"Flight Option #{i}:\n"
            body += f"From: {flight['From']} To: {flight['To']}\n"
            body += f"Departure: {flight['Departure']}\n"
            body += f"Arrival: {flight['Arrival']}\n"
            body += f"Duration: {flight['Duration']}\n"
            body += f"Total Price: {flight['Total Price (OMR)']:.2f} OMR\n"
            body += f"Flight Number: {flight['Flight Number']}\n"
            body += f"Baggage: Check-in {flight['Baggage Check-in']}, Cabin {flight['Baggage Cabin']}\n"
            body += f"Cancellation: {flight['Cancellation Policy']}\n\n"
        
        body += "Thank you for using Sakman AI Travel Assistant!\n"
        msg.attach(MIMEText(body, 'plain'))
        
        excel_data = download_excel(flight_data)
        excel_part = MIMEApplication(excel_data.getvalue(), Name=f"flights_{origin}_to_{destination}.xlsx")
        excel_part['Content-Disposition'] = f'attachment; filename="flights_{origin}_to_{destination}.xlsx"'
        msg.attach(excel_part)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        st.error(f"Failed to send email: {str(e)}")
        return False

def generate_travel_content(prompt):
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if "USD" in text:
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if 'USD' in line:
                    try:
                        price_part = line.split('Price range:')[1].split('USD')[0].strip()
                        if '-' in price_part:
                            low, high = map(float, price_part.replace('$', '').split('-'))
                            low_omr = convert_to_omr(low)
                            high_omr = convert_to_omr(high)
                            lines[i] = line.replace(f"${low}-${high} USD", f"{low_omr:.2f}-{high_omr:.2f} OMR")
                        else:
                            price = float(price_part.replace('$', ''))
                            price_omr = convert_to_omr(price)
                            lines[i] = line.replace(f"${price} USD", f"{price_omr:.2f} OMR")
                    except:
                        continue
            text = '\n'.join(lines)
        return text
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
st.markdown("Plan your perfect trip with AI-powered travel assistance", help="Enter your travel details below to get started!")

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
    
    details = extract_travel_details(user_input)
    if details:
        st.session_state.form_data = details
        st.session_state.destination_name = AIRPORT_CODES.get(details["destination"], details["destination"])
        
        confirmation = f"Great! I'll find flights from {AIRPORT_CODES.get(details['origin'], details['origin'])} "
        confirmation += f"to {st.session_state.destination_name} on {details['departure_date']}"
        if details.get('return_date'):
            confirmation += f", returning {details['return_date']}"
        confirmation += f" for {details['travelers']} traveler(s) in {details['flight_class'].capitalize()} class."
        
        st.session_state.conversation.append({"role": "assistant", "content": confirmation})
    st.rerun()

# Process flight search
if st.session_state.form_data and not st.session_state.search_complete:
    with st.spinner("🔍 Searching for flights and travel information..."):
        raw_flights = search_flights(st.session_state.form_data)
        st.session_state.search_results = process_flights(raw_flights)
        
        travel_prompt = f"""Create a comprehensive travel guide for {st.session_state.destination_name} including:
        - Top 5 attractions with descriptions
        - Local cuisine recommendations
        - Cultural tips
        - Best times to visit each attraction
        Format as markdown with headings."""
        st.session_state.travel_guide = generate_travel_content(travel_prompt)
        
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
                        <div class='flight-price'>{flight['Total Price (OMR)']:.2f} OMR</div>
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
                                <span class='fee-badge'>SSL: {flight['SSL Fee (OMR)']:.2f} OMR</span>
                            </span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Select Flight #{i+1}", key=f"select_{i}"):
                    st.session_state.selected_flight = i
                    st.rerun()
        
        # Download and Email Section
        st.markdown("---")
        st.subheader("💾 Save Your Flight Details")
        with st.container():
            col1, col2 = st.columns([2, 3])
            with col1:
                excel_data = download_excel(st.session_state.search_results)
                st.download_button(
                    label="📥 Download Flight Details (Excel)",
                    data=excel_data,
                    file_name=f"flights_{st.session_state.form_data['origin']}_to_{st.session_state.form_data['destination']}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="Download flight details as an Excel file"
                )
            with col2:
                st.markdown("**Email Your Flight Details**")
                email_input = st.text_input(
                    "Enter your email",
                    placeholder="your.email@example.com",
                    key="email_input"
                )
                if st.button("📧 Send Flight Details", help="Send flight details to your email"):
                    if email_input:
                        with st.spinner("Sending email..."):
                            success = send_flight_email(
                                email_input,
                                st.session_state.search_results,
                                st.session_state.form_data['origin'],
                                st.session_state.form_data['destination']
                            )
                            if success:
                                st.success("Flight details sent to your email!")
                    else:
                        st.error("Please enter a valid email address.")
                    st.rerun()

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
