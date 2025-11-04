# dashboard_glass.py

import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import math
import random
import urllib.parse
from datetime import datetime
from streamlit_js_eval import streamlit_js_eval
import streamlit.components.v1 as components
import plotly.express as px
import plotly.graph_objects as go
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
st.markdown("""
    <style>
        /* Reduce the top padding in the main content area */
        .block-container {
            padding-top: 0.25rem !important;
        }
    </style>
""", unsafe_allow_html=True)
if "page" not in st.session_state:
    st.session_state.page = "Overview"
# Sidebar Navigation
st.sidebar.title("Dashboard")
page = st.sidebar.radio("", ["Overview", "Past Trends"])
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

if page == "Overview":
    st.title("🌾 AgroKheti Dashboard")

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
    left, mid, _ = st.columns([4, 4, 0.01])

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

elif page == "Past Trends":
    st.title("Farmer’s Past Trends and Comparison")

    # Sample data (replace with your backend or CSV data)
    import pandas as pd
    import plotly.express as px

    data = {
        "Year": [2020, 2021, 2022, 2023, 2024],
        "Crop Yield (tons)": [3.5, 4.0, 3.8, 4.5, 4.2],
        "Income (₹ in lakhs)": [1.2, 1.5, 1.4, 1.8, 1.7],
        "Fertilizer Used (kg/acre)": [60, 58, 65, 70, 68],
        "Rainfall (mm)": [820, 760, 850, 900, 870],
    }
    df = pd.DataFrame(data)

    # Dropdown to choose what to compare
    metric = st.selectbox("Select Metric to View:", ["Crop Yield (tons)", "Income (₹ in lakhs)"])

    # Line chart for past trends
    fig = px.line(
        df,
        x="Year",
        y=metric,
        title=f"{metric} Over the Years",
        markers=True,
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- 2️⃣ BAR CHART (Comparison) ---
    st.subheader(f"Yearly Comparison of {metric}")
    fig_bar = px.bar(
        df,
        x="Year",
        y=metric,
        text=metric,
        title=f"{metric} Comparison (Bar Chart)",
    )
    fig_bar.update_traces(texttemplate='%{text:.2s}', textposition='outside')
    fig_bar.update_layout(yaxis_title=metric)
    st.plotly_chart(fig_bar, use_container_width=True)

    # --- 3️⃣ SCATTER PLOT (Correlation: Yield vs Income) ---
    st.subheader("Correlation Between Yield and Income")
    fig_scatter = px.scatter(
        df,
        x="Crop Yield (tons)",
        y="Income (₹ in lakhs)",
        size="Rainfall (mm)",
        color="Year",
        hover_data=["Fertilizer Used (kg/acre)"],
        title="Crop Yield vs Income (Bubble Size = Rainfall)",
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

    # --- 4️⃣ PERCENT CHANGE VISUALIZATION ---
    st.subheader("📊 Year-over-Year Percentage Change")
    df_change = df.copy()
    for col in df.columns[1:]:
        df_change[col] = df[col].pct_change() * 100

    fig_change = go.Figure()
    for col in df.columns[1:]:
        fig_change.add_trace(go.Scatter(
            x=df["Year"], y=df_change[col],
            mode='lines+markers', name=col
        ))
    fig_change.update_layout(
        title="Percentage Change Over Years",
        xaxis_title="Year",
        yaxis_title="Change (%)",
        legend_title="Metric"
    )
    st.plotly_chart(fig_change, use_container_width=True)

    # --- 5️⃣ MOVING AVERAGE TREND (Optional Smoother View) ---
    st.subheader("📈 Smoothed 3-Year Moving Average (for Crop Yield)")
    df["Yield_MA3"] = df["Crop Yield (tons)"].rolling(window=3).mean()
    fig_ma = go.Figure()
    fig_ma.add_trace(go.Scatter(x=df["Year"], y=df["Crop Yield (tons)"], mode='lines+markers', name="Actual Yield"))
    fig_ma.add_trace(go.Scatter(x=df["Year"], y=df["Yield_MA3"], mode='lines', name="3-Year Moving Average"))
    fig_ma.update_layout(title="Crop Yield Moving Average Trend", xaxis_title="Year", yaxis_title="Yield (tons)")
    st.plotly_chart(fig_ma, use_container_width=True)

# --------------------------------------------------------------------
# PAGE: ADVISOR
# --------------------------------------------------------------------
if st.sidebar.button("🌾 Crop Advisor"):
    crop_url = "https://agrikheti.streamlit.app/"
    components.html(
        f"""
        <script>
            window.open("{crop_url}", "_blank");
        </script>
        """,
        height=0,
    )



# --------------------------------------------------------------------
# PAGE: WEATHER
# --------------------------------------------------------------------

