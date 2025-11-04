# dashboard_glass.py

import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import math
import random
import urllib.parse
from datetime import datetime
from geopy.geocoders import Nominatim
from streamlit_js_eval import streamlit_js_eval

# --------------------------------------------------------------------
# API Keys
# --------------------------------------------------------------------
DATA_GOV_API = "579b464db66ec23bdd000001c15dfae5a00f4ecf75e017c1d9d0134f"
WEATHER_API = "24f1b6ddec2d940b269f29a913c7b3c4"

# --------------------------------------------------------------------
# Helper Functions
# --------------------------------------------------------------------
from opencage.geocoder import OpenCageGeocode

def get_district_state(lat, lon):
    """Reverse geocode coordinates to get district & state using OpenCage API."""
    try:
        key = "1dda90ade0c54d06b3c27991c3d94c1b"  # your API key
        geocoder = OpenCageGeocode(key)
        results = geocoder.reverse_geocode(lat, lon)

        if results and len(results) > 0:
            components = results[0]['components']
            district = components.get('county') or components.get('state_district') or components.get('city', None)
            state = components.get('state', None)
            return district, state
        else:
            return None, None
    except Exception as e:
        print("Geocoding error:", e)
        return None, None



def get_nearest_irrigation_source(lat, lon):
    """Find nearest irrigation source using Overpass API."""
    district, state = get_district_state(lat, lon)
    if not state:
        return None, None, None

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

    res = requests.post("https://overpass-api.de/api/interpreter", data={"data": query})
    if not res.ok:
        return None, None, None

    elements = res.json().get("elements", [])
    if not elements:
        return None, None, None

    el = elements[0]
    name = el.get("tags", {}).get("name", "Irrigation Source")
    lat2 = el.get("lat") or el.get("center", {}).get("lat")
    lon2 = el.get("lon") or el.get("center", {}).get("lon")

    return name, state, (lat2, lon2)


def get_nearest_krishi_center(lat, lon):
    """Find nearest Krishi / Agriculture center."""
    district, state = get_district_state(lat, lon)
    if not state:
        return None, None, None

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

    res = requests.post("https://overpass-api.de/api/interpreter", data={"data": query})
    if not res.ok:
        return None, None, None

    elements = res.json().get("elements", [])
    if not elements:
        return None, None, None

    el = elements[0]
    name = el.get("tags", {}).get("name", "Krishi Center")
    lat2 = el.get("lat") or el.get("center", {}).get("lat")
    lon2 = el.get("lon") or el.get("center", {}).get("lon")

    return name, state, (lat2, lon2)


def show_crop_production_chart(lat, lon, container):
    """Display crop production chart for the user's state."""
    district, state = get_district_state(lat, lon)
    if not state:
        container.warning("⚠️ Unable to detect state.")
        return

    with container:
        st.subheader(f"🌾 Crop Production in {state}")

        api_url = (
            f"https://api.data.gov.in/resource/35be999b-0208-4354-b557-f6ca9a5355de?"
            f"api-key={DATA_GOV_API}&format=json&limit=100&filters[state_name]={urllib.parse.quote(state)}"
        )

        try:
            res = requests.get(api_url)
            res.raise_for_status()
            records = res.json().get("records", [])
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            return

        crops, production = [], []
        for record in records:
            crop = record.get("crop", "Unknown")
            prod = record.get("production_")
            try:
                prod_val = float(prod)
                crops.append(crop)
                production.append(prod_val)
            except (TypeError, ValueError):
                continue

        if not crops:
            st.warning(f"⚠️ No valid crop data found for {state}")
            return

        df = pd.DataFrame({"Crop": crops[:5], "Production": production[:5]})
        fig = px.bar(df, x="Crop", y="Production", color="Crop", title=f"Top 5 Crop Productions in {state}")
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#e6eef6"
        )
        st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------------------------
# Streamlit Layout and Logic
# --------------------------------------------------------------------
st.set_page_config(page_title="AgroMitra Dashboard", layout="wide")

# Sidebar Navigation
st.sidebar.title("📊 Dashboard")
page = st.sidebar.radio("", ["🏠 Overview", "🌦 Weather", "🗺️ Map"])
st.sidebar.markdown("<hr>", unsafe_allow_html=True)

# --------------------------------------------------------------------
# Get Geolocation
# --------------------------------------------------------------------
coords = streamlit_js_eval(
    js_expressions="""
    new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        pos => resolve([pos.coords.latitude, pos.coords.longitude]),
        err => reject(err)
      );
    })
    """,
    key="get_coords"
)

if coords:
    lat, lon = coords
else:
    lat, lon = None, None
    st.warning("📍 Waiting for location access...")

# --------------------------------------------------------------------
# PAGE: OVERVIEW
# --------------------------------------------------------------------
if page == "🏠 Overview":
    st.title("🌾 AgroMitra Dashboard")

    c1, c2, c3, c4 = st.columns(4)

    if lat and lon:
        district, state = get_district_state(lat, lon)
        if state:
            irr_name, _, _ = get_nearest_irrigation_source(lat, lon)
            kr_name, _, _ = get_nearest_krishi_center(lat, lon)
            c1.metric("💧 Nearest Irrigation Source", irr_name or "Not found")
            c4.metric("🚜 Nearest Krishi Center", kr_name or "Not found")
        else:
            c1.metric("💧 Nearest Irrigation Source", "Detecting...")
            c4.metric("🚜 Nearest Krishi Center", "Detecting...")
    else:
        c1.metric("💧 Nearest Irrigation Source", "Fetching...")
        c4.metric("🚜 Nearest Krishi Center", "Fetching...")

    # Next Rainfall Metric
    if lat and lon:
        try:
            url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={WEATHER_API}&units=metric"
            res = requests.get(url).json()
            next_rain = next((datetime.utcfromtimestamp(e["dt"]) for e in res["list"] if "rain" in e), None)
            c2.metric("🌧️ Next Rainfall", next_rain.strftime("%d %b %Y") if next_rain else "No rain in next 5 days")
        except Exception:
            c2.metric("🌧️ Next Rainfall", "Unavailable")
    else:
        c2.metric("🌧️ Next Rainfall", "Fetching...")

    # Crop Production Metric
    if lat and lon:
        try:
            district, state = get_district_state(lat, lon)
            if state:
                api_url = (
                    f"https://api.data.gov.in/resource/35be999b-0208-4354-b557-f6ca9a5355de?"
                    f"api-key={DATA_GOV_API}&format=json&limit=100&filters[state_name]={urllib.parse.quote(state)}"
                )
                data = requests.get(api_url).json()
                records = data.get("records", [])
                valid = [r for r in records if r.get("production_")]
                if valid:
                    r = random.choice(valid)
                    c3.metric(f"🌾 {r.get('crop', 'Unknown')}", f"{r.get('production_', '0')} tonnes")
                else:
                    c3.metric("🌾 Commodity Data", "No data")
        except Exception:
            c3.metric("🌾 Commodity Data", "Unavailable")

    st.markdown("---")
    left, mid, _ = st.columns([3, 3, 1])

    if lat and lon:
        show_crop_production_chart(lat, lon, left)

    with mid:
        st.subheader("🌤️ 5-Day Weather Forecast")
        try:
            url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={WEATHER_API}&units=metric"
            data = requests.get(url).json()
            forecast = []
            for i in range(0, len(data["list"]), 8):
                e = data["list"][i]
                forecast.append({
                    "Date": e["dt_txt"].split(" ")[0],
                    "Temp (°C)": e["main"]["temp"],
                    "Humidity (%)": e["main"]["humidity"]
                })
            df = pd.DataFrame(forecast)
            fig = px.line(df, x="Date", y=["Temp (°C)", "Humidity (%)"], markers=True,
                          title="5-Day Temperature & Humidity Trend")
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error fetching weather: {e}")

# --------------------------------------------------------------------
# PAGE: MAP
# --------------------------------------------------------------------
elif page == "🗺️ Map":
    st.header("🗺️ Redirecting to Map...")
    map_url = "https://agrikheti.streamlit.app/"
    st.markdown(
        f"""
        <meta http-equiv="refresh" content="0; url={map_url}">
        <p>If you are not redirected automatically,
        <a href="{map_url}" target="_blank">click here</a>.</p>
        """,
        unsafe_allow_html=True,
    )

# --------------------------------------------------------------------
# PAGE: WEATHER
# --------------------------------------------------------------------
elif page == "🌦 Weather":
    st.title("🌦 Real-Time Weather Data")
    if lat and lon:
        show_crop_production_chart(lat, lon, st)
    else:
        st.warning("📍 Please allow location access to view weather data.")
