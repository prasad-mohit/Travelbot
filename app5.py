import streamlit as st
import requests
import google.generativeai as genai
from datetime import datetime, timedelta
from dateutil import parser
import json

# Configure API keys
AMADEUS_API_KEY = "5YWlF018OsxWXu9kMAHRIfBEATNd4irF"
AMADEUS_API_SECRET = "YS1jZZ088P6h5xLk"
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")  # Add your Gemini API key to Streamlit secrets

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")

# Streamlit app configuration
st.set_page_config(
    page_title="Sakman Sakman AI Travel Assistant",
    page_icon="✈️",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .header {
        background: linear-gradient(135deg, #4a8cff 0%, #2a56d6 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .flight-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        background-color: white;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }
    .flight-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .price-tag {
        background-color: #4a8cff;
        color: white;
        padding: 5px 10px;
        border-radius: 15px;
        font-weight: bold;
        display: inline-block;
    }
    .assistant-message {
        background-color: #f0f8ff;
        padding: 12px;
        border-radius: 10px;
        margin: 8px 0;
    }
    .user-message {
        background-color: #e6f2ff;
        padding: 12px;
        border-radius: 10px;
        margin: 8px 0;
    }
    .debug-info {
        background-color: #fff4f4;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
        font-family: monospace;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# Airport codes (IATA)
AIRPORT_CODES = {
    "DEL": "Delhi", "BOM": "Mumbai", "MCT": "Muscat",
    "DOH": "Doha", "LHR": "London", "DXB": "Dubai",
    "JFK": "New York", "SIN": "Singapore", "BKK": "Bangkok"
}

# Airline logos
AIRLINE_LOGOS = {
    "AI": "https://www.airindia.com/content/dam/air-india/airindia-revamp/logos/AI_Logo_Red_New.svg",
    "EK": "https://logos-world.net/wp-content/uploads/2021/08/Emirates-Logo.png",
    "QR": "https://logos-world.net/wp-content/uploads/2020/11/Qatar-Airways-Logo.png",
    "6E": "https://www.goindigo.in/content/dam/s6web/in/en/assets/logo/IndiGo_logo_2x.png",
    "default": "https://cdn-icons-png.flaticon.com/512/1169/1169168.png"
}

# Initialize session state
if 'conversation' not in st.session_state:
    st.session_state.conversation = []
if 'form_data' not in st.session_state:
    st.session_state.form_data = {
        "origin": "",
        "destination": "",
        "departure_date": "",
        "return_date": "",
        "travelers": 1,
        "flight_class": "ECONOMY"
    }
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'debug_info' not in st.session_state:
    st.session_state.debug_info = []

# Function to get Amadeus access token
def get_amadeus_token():
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'grant_type': 'client_credentials',
        'client_id': AMADEUS_API_KEY,
        'client_secret': AMADEUS_API_SECRET
    }
    
    try:
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json()['access_token']
        else:
            st.error("Failed to get Amadeus token")
            return None
    except Exception as e:
        st.error(f"Token error: {str(e)}")
        return None

# Function to search flights
def search_flights(form_data):
    token = get_amadeus_token()
    if not token:
        return None
    
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    params = {
        "originLocationCode": form_data["origin"],
        "destinationLocationCode": form_data["destination"],
        "departureDate": form_data["departure_date"],
        "adults": form_data["travelers"],
        "max": 10,
        "currencyCode": "OMR",
        "travelClass": form_data["flight_class"].upper()
    }
    
    if form_data["return_date"]:
        params["returnDate"] = form_data["return_date"]
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Flight search failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Search error: {str(e)}")
        return None

# Function to process flight data
def process_flight_data(flight_data, form_data):
    processed_flights = []
    
    if not flight_data or 'data' not in flight_data:
        return None
    
    for offer in flight_data['data']:
        try:
            # Basic flight info
            airline_code = offer['itineraries'][0]['segments'][0]['carrierCode']
            airline_logo = AIRLINE_LOGOS.get(airline_code, AIRLINE_LOGOS['default'])
            
            # Flight segments
            segments = offer['itineraries'][0]['segments']
            first_segment = segments[0]
            last_segment = segments[-1]
            
            # Calculate duration
            departure_time = parser.parse(first_segment['departure']['at'])
            arrival_time = parser.parse(last_segment['arrival']['at'])
            duration = arrival_time - departure_time
            hours, remainder = divmod(duration.seconds, 3600)
            minutes = remainder // 60
            duration_str = f"{hours}h {minutes}m"
            
            # Fare details
            price = float(offer['price']['grandTotal'])
            
            # Baggage info
            baggage_allowance = "7 kg cabin"
            if 'travelerPricings' in offer and offer['travelerPricings']:
                traveler_pricing = offer['travelerPricings'][0]
                if 'fareDetailsBySegment' in traveler_pricing and traveler_pricing['fareDetailsBySegment']:
                    fare_details = traveler_pricing['fareDetailsBySegment'][0]
                    if 'includedCheckedBags' in fare_details:
                        baggage = fare_details['includedCheckedBags']
                        if 'weight' in baggage and 'weightUnit' in baggage:
                            baggage_allowance = f"7 kg cabin, {baggage['weight']} {baggage['weightUnit']} checked"
            
            # Flexibility info
            flexibility = "Standard"
            if 'nonHomogeneous' in offer and offer['nonHomogeneous']:
                flexibility = "Flexible"
            
            # Cancellation policy
            cancellation = "Refundable with fees"
            if 'nonRefundable' in offer and offer['nonRefundable']:
                cancellation = "Non-refundable"
            
            # Get travel class from form_data
            travel_class = form_data["flight_class"].capitalize()
            
            processed_flight = {
                "Airline": airline_code,
                "Airline Logo": airline_logo,
                "Source": first_segment['departure']['iataCode'],
                "Departure": departure_time.strftime("%a, %d-%b-%y %H:%M:%S"),
                "Destination": last_segment['arrival']['iataCode'],
                "Duration": duration_str,
                "Arrival": arrival_time.strftime("%a, %d-%b-%y %H:%M:%S"),
                "Baggage": baggage_allowance,
                "Flexibility": flexibility,
                "Class": travel_class,
                "Price (OMR)": price,
                "Cancellation Policy": cancellation,
                "raw_data": offer
            }
            processed_flights.append(processed_flight)
        except Exception as e:
            error_msg = f"Skipping flight due to processing error: {str(e)}"
            st.session_state.debug_info.append(error_msg)
            continue
    
    return processed_flights

# Function to extract travel details using Gemini
def extract_travel_details(user_input):
    prompt = f"""Extract travel details from the following user request and return ONLY valid JSON:
    User Input: "{user_input}"
    
    Extract these fields:
    - origin (IATA airport code like "DEL" for Delhi)
    - destination (IATA airport code)
    - departure_date (YYYY-MM-DD format)
    - return_date (YYYY-MM-DD format if round trip, otherwise empty)
    - travelers (number, default to 1 if not specified)
    - flight_class ("ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", or "FIRST", default to "ECONOMY")
    
    Example Output:
    {{
        "origin": "DEL",
        "destination": "DOH",
        "departure_date": "2024-05-15",
        "return_date": "2024-05-22",
        "travelers": 2,
        "flight_class": "BUSINESS"
    }}
    
    Return ONLY the JSON object, no additional text or explanation."""
    
    try:
        # Debug: Log the prompt being sent
        debug_msg = f"[DEBUG] Sending prompt to Gemini:\n{prompt}"
        st.session_state.debug_info.append(debug_msg)
        
        response = model.generate_content(prompt)
        
        # Debug: Log the raw response
        debug_msg = f"[DEBUG] Raw Gemini response:\n{response.text}"
        st.session_state.debug_info.append(debug_msg)
        
        # Clean the response to extract just the JSON
        response_text = response.text.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith('```'):
            response_text = response_text[3:-3].strip()
        
        # Debug: Log cleaned response
        debug_msg = f"[DEBUG] Cleaned response text:\n{response_text}"
        st.session_state.debug_info.append(debug_msg)
        
        extracted_data = json.loads(response_text)
        
        # Debug: Log extracted data
        debug_msg = f"[DEBUG] Extracted JSON data:\n{json.dumps(extracted_data, indent=2)}"
        st.session_state.debug_info.append(debug_msg)
        
        # Validate required fields
        required_fields = ['origin', 'destination', 'departure_date']
        missing_fields = [field for field in required_fields if field not in extracted_data or not extracted_data[field]]
        
        if missing_fields:
            debug_msg = f"[DEBUG] Missing required fields: {missing_fields}"
            st.session_state.debug_info.append(debug_msg)
            st.error(f"Couldn't extract these required details: {', '.join(missing_fields)}. Please provide more specific information.")
            return None
        
        return extracted_data
    except json.JSONDecodeError as e:
        debug_msg = f"[DEBUG] JSON decode error: {str(e)}\nResponse text: {response_text if 'response_text' in locals() else 'N/A'}"
        st.session_state.debug_info.append(debug_msg)
        st.error(f"Sorry, I couldn't understand your travel request. Please try being more specific.")
        return None
    except Exception as e:
        debug_msg = f"[DEBUG] Error extracting travel details: {str(e)}"
        st.session_state.debug_info.append(debug_msg)
        st.error(f"Error processing your request: {str(e)}")
        return None

# Function to display flight results
def display_flight_results(flights):
    if not flights:
        st.warning("No flights found for your search criteria")
        return
    
    st.success(f"Found {len(flights)} flight options")
    
    # Sort by price
    flights.sort(key=lambda x: x['Price (OMR)'])
    
    for flight in flights:
        with st.container():
            st.markdown("<div class='flight-card'>", unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 3])
            with col1:
                st.image(flight['Airline Logo'], width=80)
                st.markdown(f"<span class='price-tag'>{flight['Price (OMR)']:.2f} OMR</span>", unsafe_allow_html=True)
                st.write(f"Class: {flight['Class']}")
            
            with col2:
                st.write(f"**{flight['Source']} → {flight['Destination']}**")
                st.write(f"**Departure:** {flight['Departure']}")
                st.write(f"**Arrival:** {flight['Arrival']}")
                st.write(f"**Duration:** {flight['Duration']}")
                
                # Flight details expander
                with st.expander("View Fare Details"):
                    details_col1, details_col2 = st.columns(2)
                    with details_col1:
                        st.write("**Baggage Allowance:**")
                        st.write(flight['Baggage'])
                        st.write("**Flexibility:**")
                        st.write(flight['Flexibility'])
                    with details_col2:
                        st.write("**Cancellation Policy:**")
                        st.write(flight['Cancellation Policy'])
                        st.write("**Airline:**")
                        st.write(flight['Airline'])
            
            st.markdown("</div>", unsafe_allow_html=True)

# Main app
st.title("✈️ Sakman Sakman AI Travel Assistant")
st.markdown("<div class='header'>Tell me about your trip and I'll find the best flights</div>", unsafe_allow_html=True)

# Display conversation
for msg in st.session_state.conversation:
    role = msg['role']
    content = msg['content']
    st.markdown(f"<div class='{role}-message'><b>{role.capitalize()}:</b> {content}</div>", 
                unsafe_allow_html=True)

# User input
user_input = st.chat_input("Where would you like to travel? (e.g., 'I want to fly from Delhi to Doha on May 15th for 2 people in business class')")

if user_input:
    # Add user message to conversation
    st.session_state.conversation.append({"role": "user", "content": user_input})
    st.rerun()

# Process user input when conversation exists
if st.session_state.conversation and st.session_state.conversation[-1]["role"] == "user":
    user_input = st.session_state.conversation[-1]["content"]
    
    with st.spinner("Understanding your travel plans..."):
        # Extract travel details using Gemini
        extracted_data = extract_travel_details(user_input)
        
        if extracted_data:
            # Update form data with extracted values
            for key in ['origin', 'destination', 'departure_date', 'return_date', 'travelers', 'flight_class']:
                if key in extracted_data and extracted_data[key]:
                    st.session_state.form_data[key] = extracted_data[key]
            
            # Add assistant response to conversation
            origin_name = AIRPORT_CODES.get(st.session_state.form_data["origin"], st.session_state.form_data["origin"])
            dest_name = AIRPORT_CODES.get(st.session_state.form_data["destination"], st.session_state.form_data["destination"])
            
            response = f"I found these travel details:\n"
            response += f"- From: {origin_name}\n"
            response += f"- To: {dest_name}\n"
            response += f"- Departure: {st.session_state.form_data['departure_date']}\n"
            if st.session_state.form_data.get('return_date'):
                response += f"- Return: {st.session_state.form_data['return_date']}\n"
            response += f"- Travelers: {st.session_state.form_data['travelers']}\n"
            response += f"- Class: {st.session_state.form_data['flight_class'].capitalize()}\n\n"
            response += "Searching for flights now..."
            
            st.session_state.conversation.append({"role": "assistant", "content": response})
            st.rerun()

# Perform flight search when assistant has responded but no results yet
if (len(st.session_state.conversation) >= 2 and 
    st.session_state.conversation[-1]["role"] == "assistant" and 
    "Searching for flights" in st.session_state.conversation[-1]["content"] and 
    not st.session_state.search_results):
    
    with st.spinner("Searching for flights..."):
        flight_data = search_flights(st.session_state.form_data)
        if flight_data:
            processed_flights = process_flight_data(flight_data, st.session_state.form_data)
            st.session_state.search_results = processed_flights
            st.rerun()

# Display flight results when available
if st.session_state.search_results:
    # Clear the "Searching for flights" message
    if "Searching for flights" in st.session_state.conversation[-1]["content"]:
        st.session_state.conversation.pop()
    
    # Add confirmation message
    origin_name = AIRPORT_CODES.get(st.session_state.form_data["origin"], st.session_state.form_data["origin"])
    dest_name = AIRPORT_CODES.get(st.session_state.form_data["destination"], st.session_state.form_data["destination"])
    confirmation = f"Here are flight options from {origin_name} to {dest_name} on {st.session_state.form_data['departure_date']}"
    if st.session_state.form_data.get('return_date'):
        confirmation += f", returning {st.session_state.form_data['return_date']}"
    confirmation += f" for {st.session_state.form_data['travelers']} traveler(s) in {st.session_state.form_data['flight_class'].capitalize()} class:"
    
    st.session_state.conversation.append({"role": "assistant", "content": confirmation})
    
    # Display results
    display_flight_results(st.session_state.search_results)
    st.rerun()

# Debug information section
if st.session_state.debug_info:
    with st.expander("Debug Information"):
        for info in st.session_state.debug_info[-5:]:  # Show last 5 debug messages
            st.markdown(f"<div class='debug-info'>{info}</div>", unsafe_allow_html=True)

# Add some information about the app
st.markdown("""
### How to Use This Sakman Sakman AI Travel Assistant
1. Tell me about your trip in natural language (examples below)
2. I'll extract the details and confirm with you
3. I'll search for flights and show you the best options

**Example requests:**
- "I need to fly from Delhi to Doha on May 15th"
- "Book me a business class ticket from Mumbai to Dubai for 2 people next Monday"
- "Looking for round trip flights from London to New York, departing June 1st and returning June 15th"
""")
