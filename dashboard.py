# dashboard_glass.py
import streamlit as st

import pandas as pd
import plotly.express as px
import requests
import streamlit.components.v1 as components
from streamlit_js_eval import streamlit_js_eval
from geopy.geocoders import Nominatim
import urllib.parse
import os

from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import requests
API_KEY = "579b464db66ec23bdd000001f2b91b051d524b604ec6d9bdfcd4dbb6"
IRRIGATION_API = "https://api.data.gov.in/resource/9a0d593b-2447-48f7-982b-b10a3f681b10"
KRISHI_API = "https://api.data.gov.in/resource/ab9a1a4a-c33e-4c80-bf30-d99d3cbf1b4d"

import requests
import math
from geopy.geocoders import Nominatim

import requests
import matplotlib.pyplot as plt
import random
    
import requests
import streamlit as st

# # --------------------------------------------------------
# # WHITE BACKGROUND + HIDE STREAMLIT UI
# # --------------------------------------------------------
# st.markdown("""
#     <style>
#         [data-testid="stAppViewContainer"] {
#             background-color: white !important;
#         }
#         [data-testid="stSidebar"] {
#             background-color: white !important;
#         }
#         #MainMenu, footer, header {visibility: hidden;}
#         .block-container {padding: 0 !important; margin: 0 !important;}
#         body {background-color: white !important;}
#     </style>
# """, unsafe_allow_html=True)

# # --------------------------------------------------------
# # SESSION STATE INIT
# # --------------------------------------------------------
# if "authenticated" not in st.session_state:
#     st.session_state.authenticated = False

# query_params = st.query_params
# if "login" in query_params:
#     st.session_state.authenticated = True

# # --------------------------------------------------------
# # LOAD LOGIN HTML
# # --------------------------------------------------------
# def load_html(file_path):
#     with open(file_path, "r", encoding="utf-8") as f:
#         return f.read()

# if not st.session_state.authenticated:
#     html_file = os.path.join("src", "templates", "index.html")
#     html_code = load_html(html_file)
#     components.html(html_code, height=700, scrolling=True)
#     st.stop()

# -------------------- GEOLOCATION --------------------
lat = streamlit_js_eval(js_expressions="localStorage.getItem('lat')", key="get_lat_dashboard")
lon = streamlit_js_eval(js_expressions="localStorage.getItem('lon')", key="get_lon_dashboard")


# Sidebar Navigation
st.sidebar.title("📊 Dashboard")
page = st.sidebar.radio("", ["🏠 Overview", "🌦 Weather", "🗺️ Map"])
st.sidebar.markdown("<hr>", unsafe_allow_html=True)

# --------------------------------------------------------
# JS GEOLOCATION FETCH
# --------------------------------------------------------
# st.markdown("""
# <script>
# navigator.geolocation.getCurrentPosition(
#     (pos) => {
#         localStorage.setItem("lat", pos.coords.latitude);
#         localStorage.setItem("lon", pos.coords.longitude);
#         window.parent.postMessage({lat: pos.coords.latitude, lon: pos.coords.longitude}, "*");
#     },
#     (err) => { console.log(err); }
# );
# </script>
# """, unsafe_allow_html=True)

# --------------------------------------------------------
# GLOBAL CSS (GLASS STYLE)
# --------------------------------------------------------
# st.markdown("""
# <style>
# :root {
#     --bg: #ffffff;
#     --panel: #ffffff;
#     --accent: #4CAF50;
#     --muted: #9fb3c8;
#     --glass: rgba(255, 255, 255, 0.05);
#     --radius: 12px;
# }
# .stApp {
#     background-color: var(--bg);
#     font-family: 'Inter', sans-serif;
# }
# [data-testid="stSidebar"] {
#     background: linear-gradient(180deg,var(--panel), rgba(15,37,71,0.9));
# }
# h1, h2, h3 { color: #111; }
# hr { border-color: rgba(0,0,0,0.1); }
# </style>
# """, unsafe_allow_html=True)

def show_weather_widget(lat, lon, container):
        with container:
            st.subheader("🌦 5-Day Weather Forecast")
            # Use OpenWeather One Call API
            api_key = "24f1b6ddec2d940b269f29a913c7b3c4"
            url = f"https://api.openweathermap.org/data/2.5/onecall?lat={lat}&lon={lon}&exclude=minutely,hourly,alerts&units=metric&appid={api_key}"
            try:
                resp = requests.get(url)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                st.error(f"Error fetching weather data: {e}")
                return
            
            daily = data.get("daily", [])
            if not daily:
                st.warning("No daily forecast data available.")
                return
            
            # Take first 5 days
            for day in daily[:5]:
                dt = day.get("dt")
                temp = day.get("temp", {})
                tmin = temp.get("min")
                tmax = temp.get("max")
                weather = day.get("weather", [{}])[0].get("description", "").title()
                date_str = pd.to_datetime(dt, unit="s").strftime("%Y-%m-%d")
                st.markdown(f"**{date_str}**: {weather} — {tmin}°C / {tmax}°C")


def get_district_state(lat, lon):
        geolocator = Nominatim(user_agent="geoapi")
        location = geolocator.reverse((lat, lon), language='en')
        if not location:
            return None, None
        address = location.raw.get('address', {})
        district = address.get('county') or address.get('state_district') or address.get('city')
        state = address.get('state')
        return district, state

def haversine(lat1, lon1, lat2, lon2):
        R = 6371  # Earth radius (km)
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        a = math.sin(dLat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def get_nearest_irrigation_source(lat, lon):
        # Step 1: Detect the state from coordinates
        district, state = get_district_state(lat, lon)
        if not state:
            return None, None, None

        # Step 2: Query for irrigation sources in the entire state
        query = f"""
        [out:json][timeout:60];
        area["name"="{state}"][admin_level=4];
        (
        node["water"="reservoir"](area);
        way["water"="reservoir"](area);
        relation["water"="reservoir"](area);
        node["waterway"="dam"](area);
        way["waterway"="dam"](area);
        way["waterway"="canal"](area);
        );
        out center 1;
        """

        res = requests.post(
            "https://overpass-api.de/api/interpreter",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"data": query},
        )

        if not res.ok:
            return None, None, None

        data = res.json().get("elements", [])
        if not data:
            return None, None, None

        # Pick any irrigation source (first result)
        el = data[0]
        name = el.get("tags", {}).get("name", "Irrigation Source")
        lat2 = el.get("lat") or el.get("center", {}).get("lat")
        lon2 = el.get("lon") or el.get("center", {}).get("lon")

        return name, state, (lat2, lon2)


def get_nearest_krishi_center(lat, lon):
        # Step 1: Detect the state from coordinates
        district, state = get_district_state(lat, lon)
        if not state:
            return None, None, None

        # Step 2: Query for Krishi centers / agricultural institutions in the state
        query = f"""
        [out:json][timeout:60];
        area["name"="{state}"][admin_level=4];
        (
        node["name"~"Krishi"](area);
        node["office"="agriculture"](area);
        node["amenity"="research_institute"](area);
        node["name"~"Agriculture"](area);
        );
        out center 1;
        """

        res = requests.post(
            "https://overpass-api.de/api/interpreter",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"data": query},
        )

        if not res.ok:
            return None, None, None

        data = res.json().get("elements", [])
        if not data:
            return None, None, None

        # Pick any Krishi center (first result)
        el = data[0]
        name = el.get("tags", {}).get("name", "Krishi Center")
        lat2 = el.get("lat") or el.get("center", {}).get("lat")
        lon2 = el.get("lon") or el.get("center", {}).get("lon")

        return name, state, (lat2, lon2)




# --- Main Section ---
if page == "🏠 Overview":
    st.title("🌱 AgroMitra Overview")
    st.write("Welcome to the AgroMitra Dashboard!")
    # Add JavaScript to get location and store in localStorage
    st.markdown("""
    <script>
    navigator.geolocation.getCurrentPosition(
    (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        localStorage.setItem("lat", lat);
        localStorage.setItem("lon", lon);
        window.parent.postMessage({lat: lat, lon: lon}, "*");
    },
    (err) => { console.log(err); }
    );
    </script>
    """, unsafe_allow_html=True)

    # -------------------------------------
    # CUSTOM CSS
    # -------------------------------------
    st.markdown("""
    <style>
    :root {
    --bg: #07122a;
    --panel: ##0F2547;
    --accent: #4CAF50;
    --muted: #9fb3c8;
    --glass: rgba(255, 255, 255, 0.03);
    --radius: 12px;
    }

    /* Global Styles */
    body, .stApp {
    background-color: var(--bg);
    color: #fffffff;
    font-family: 'Inter', system-ui, Arial, sans-serif;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
    background: linear-gradient(180deg,var(--panel), rgba(15,37,71,0.9));
    width: 220px !important;
    padding: 20px 12px;
    color: var(--muted);
    }

    [data-testid="stSidebar"] a, [data-testid="stSidebar"] label {
    color: var(--muted) !important;
    }

    [data-testid="stSidebar"] a:hover, [data-testid="stSidebar"] div:hover {
    background: var(--glass);
    border-radius: var(--radius);
    color: #fff !important;
    }

    /* Titles & Text */
    h1, h2, h3 {
    color: #e6eef6;
    }
    hr {
    border-color: rgba(255,255,255,0.05);
    }

    /* Metric Cards */
    .stMetric {
    background: var(--glass);
    border-radius: var(--radius);
    padding: 16px;
    text-align: center;
    box-shadow: 0 6px 20px rgba(2,6,23,0.4);
    }

    /* Plot */
    .plotly {
    background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
    border-radius: var(--radius);
    box-shadow: 0 6px 20px rgba(2,6,23,0.4);
    padding: 10px;
    }

    /* Weather Box */
    .weather-box {
    background: var(--glass);
    border-radius: var(--radius);
    padding: 18px;
    text-align: center;
    box-shadow: 0 6px 20px rgba(2,6,23,0.4);
    }

    /* Footer */
    footer, .stMarkdown {
    text-align: center;
    color: var(--muted);
    }
    </style>
    """, unsafe_allow_html=True)


    lat = streamlit_js_eval(js_expressions="localStorage.getItem('lat')", key="get_lat")
    lon = streamlit_js_eval(js_expressions="localStorage.getItem('lon')", key="get_lon")


    # -------------------------------------
    # MAIN DASHBOARD CONTENT
    # -------------------------------------
    if page == "🏠 Overview":
        st.markdown("<h1 style='text-align:center;'>🌍 Glass Insights Dashboard</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:#9fb3c8;'>Modern dark UI with glass panels and real data</p>", unsafe_allow_html=True)
        st.markdown("---")

        # Top Cards
        c1, c2, c3, c4 = st.columns(4)
        from datetime import datetime

        if lat and lon:
            district, state = get_district_state(lat, lon)
            if state:
                irr_name, irr_district, irr_dist = get_nearest_irrigation_source(lat, lon)
                if irr_name:
                    c1.metric("💧 Nearest Irrigation Source", irr_name, f"{irr_district} ({irr_dist} km)")
                else:
                    c1.metric("💧 Nearest Irrigation Source", "Not found within 50 km", "")

                kr_name, kr_district, kr_dist = get_nearest_krishi_center(lat, lon)
                if kr_name:
                    c4.metric("🚜 Nearest Krishi Center", kr_name, f"{kr_district} ({kr_dist} km)")
                else:
                    c4.metric("🚜 Nearest Krishi Center", "Not found within 50 km", "")
            else:
                c1.metric("💧 Nearest Irrigation Source", "Detecting location...", "")
                c4.metric("🚜 Nearest Krishi Center", "Detecting location...", "")
        else:
            c1.metric("💧 Nearest Irrigation Source", "Fetching location...", "")
            c4.metric("🚜 Nearest Krishi Center", "Fetching location...", "")



        # 2️⃣ Next Rainfall Date metric
        if lat and lon:
            try:
                api_key = "24f1b6ddec2d940b269f29a913c7b3c4"  # Replace with your actual API key
                url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric"
                response = requests.get(url).json()

                next_rain = None
                for entry in response.get("list", []):
                    if "rain" in entry:
                        timestamp = entry["dt"]
                        next_rain = datetime.utcfromtimestamp(timestamp)
                        break

                if next_rain:
                    date_str = next_rain.strftime("%d %b %Y")  # example: "06 Nov 2025"
                    c2.metric("🌧️ Next Rainfall", date_str)
                else:
                    c2.metric("🌧️ Next Rainfall", "No rain in next 5 days")
            except Exception as e:
                c2.metric("🌧️ Next Rainfall", "Unavailable")
                st.error(f"Error fetching rainfall data: {e}")
        else:
            c2.metric("🌧️ Next Rainfall", "Fetching location...")

        # 3️⃣ Commodity Production Metric
        if lat and lon:
            try:
                geolocator = Nominatim(user_agent="geoapiDashboard")
                location = geolocator.reverse((lat, lon), language='en')
                address = location.raw.get("address", {})
                state = address.get("state", None)

                if state:
                    import urllib.parse
                    state_encoded = urllib.parse.quote(state)

                    api_url = (
                        "https://api.data.gov.in/resource/"
                        "35be999b-0208-4354-b557-f6ca9a5355de?"
                        "api-key=579b464db66ec23bdd000001c15dfae5a00f4ecf75e017c1d9d0134f"
                        f"&format=json&limit=100&filters[state_name]={state_encoded}"
                    )

                    response = requests.get(api_url)
                    data = response.json()
                    records = data.get("records", [])

                    # Filter only valid numeric production values
                    valid_records = []
                    for record in records:
                        prod = record.get("production_")
                        try:
                            prod_value = float(prod)
                            if prod_value > 0:
                                valid_records.append(record)
                        except (ValueError, TypeError):
                            continue

                    if valid_records:
                        # You can pick the first, random, or highest production crop
                        import random
                        chosen = random.choice(valid_records)
                        crop = chosen.get("crop", "Unknown Crop")
                        production = chosen.get("production_", "0")
                        c3.metric(f"🌾 {crop}", f"{production} tonnes")
                    else:
                        c3.metric("🌾 Commodity Data", "No valid numeric production found")

                else:
                    c3.metric("🌾 Commodity Data", "State not found")

            except Exception as e:
                c3.metric("🌾 Commodity Data", "Unavailable")
                st.error(f"Error fetching commodity data: {e}")

        else:
            c3.metric("🌾 Commodity Data", "Fetching location...")


    # --- Crop Chart Function ---
    def show_crop_production_chart(lat, lon, container):
        # Step 1: Detect the state name
        district, state = get_district_state(lat, lon)
        if not state:
            container.warning("⚠️ Unable to detect state.")
            return

        with container:
            st.subheader(f"🌾 Crop Production in {state}")

            # Step 2: Fetch data from API
            base_url = "https://api.data.gov.in/resource/35be999b-0208-4354-b557-f6ca9a5355de"
            api_key = "579b464db66ec23bdd000001c15dfae5a00f4ecf75e017c1d9d0134f"
            url = f"{base_url}?api-key={api_key}&format=json&limit=100&filters[state_name]={state.replace(' ', '%20')}"

            try:
                res = requests.get(url)
                res.raise_for_status()
                records = res.json().get("records", [])
            except Exception as e:
                st.error(f"Error fetching data: {e}")
                return

            if not records:
                st.warning(f"⚠️ No crop data found for {state}")
                return

            # Step 3: Extract crop and production info
            crops = []
            production = []
            for record in records:
                crop = record.get("crop", "Unknown")
                prod = record.get("production_")

                # Ensure production_ is numeric
                try:
                    prod_val = float(prod)
                except (TypeError, ValueError):
                    continue

                crops.append(crop)
                production.append(prod_val)

            if not crops:
                st.warning(f"⚠️ No valid numeric production data for {state}")
                return

            # Step 4: Choose any 5 random crops
            sample_indices = random.sample(range(len(crops)), min(5, len(crops)))
            df = pd.DataFrame({
                "Crop": [crops[i] for i in sample_indices],
                "Production": [production[i] for i in sample_indices]
            })

            # Step 5: Plotly bar chart
            fig = px.bar(
                df,
                x="Crop",
                y="Production",
                color="Crop",
                color_discrete_sequence=["#4CAF50"] * len(df),
                title=f"Top 5 Crop Productions in {state}"
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e6eef6"
            )
            st.plotly_chart(fig, use_container_width=True)


    # --- MAIN DASHBOARD ---
    st.markdown("---")

    # Create 3-column grid globally
    left, mid, right = st.columns([3,3,0.25])

    # Bar Chart in Left
    with left:
        # Example coordinates (Tamil Nadu)
        show_crop_production_chart(11.0168, 76.9558, left)

    # Weather Widget in Middle
    # 🌦️ Weather Widget (Dynamic Coordinates)
    # 🌤️ Enlarged & Centered Weather Widget
    with mid:
        st.subheader("🌤️ 5-Day Weather Forecast")

        try:
            api_key = "24f1b6ddec2d940b269f29a913c7b3c4"
            url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric"

            res = requests.get(url)
            data = res.json()

            # Process 1 entry every 8 (≈ daily)
            forecast_data = []
            for i in range(0, len(data["list"]), 8):
                entry = data["list"][i]
                date = entry["dt_txt"].split(" ")[0]
                temp = entry["main"]["temp"]
                humidity = entry["main"]["humidity"]
                desc = entry["weather"][0]["description"].capitalize()
                icon = entry["weather"][0]["icon"]
                forecast_data.append({
                    "Date": date,
                    "Temp (°C)": temp,
                    "Humidity (%)": humidity,
                    "Condition": desc,
                    "Icon": f"http://openweathermap.org/img/wn/{icon}@2x.png"
                })

            df_forecast = pd.DataFrame(forecast_data)

            # Bigger chart for better visibility
            fig = px.line(
                df_forecast,
                x="Date",
                y=["Temp (°C)", "Humidity (%)"],
                markers=True,
                title="5-Day Temperature & Humidity Trend"
            )
            fig.update_layout(
                height=500,  # increased height
                width=1000,   # make it wider
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e6eef6",
                legend=dict(orientation="h", y=-0.25, x=0.2),
                margin=dict(l=20, r=20, t=60, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Error fetching weather: {e}")

elif page == "🗺️ Map":
        st.header("🗺️ Redirecting to Map...")

        map_url = "https://agrikheti.streamlit.app/"  # <-- your deployed map link here

        # Auto-redirect user immediately when they click the "🗺️ Map" tab
        st.markdown(
            f"""
            <meta http-equiv="refresh" content="0; url={map_url}">
            <p>If you are not redirected automatically, 
            <a href="{map_url}" target="_blank">click here</a>.</p>
            """,
            unsafe_allow_html=True
        )


    # Footer
        st.markdown("---")
        st.markdown("<p style='text-align:center;color:#9fb3c8;'>Built with ❤️ by Team 7 AF1</p>", unsafe_allow_html=True)


