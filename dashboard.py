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



import requests
import time

def get_nearest_irrigation_source(lat, lon, max_retries=5, delay=3):
    """Find nearest irrigation source using Overpass API, retrying until found."""
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

    # Keep retrying until data is found or retries exhausted
    attempt = 0
    while attempt < max_retries:
        res = requests.post("https://overpass-api.de/api/interpreter", data={"data": query})
        if res.ok:
            elements = res.json().get("elements", [])
            if elements:
                el = elements[0]
                name = el.get("tags", {}).get("name", "Irrigation Source")
                lat2 = el.get("lat") or el.get("center", {}).get("lat")
                lon2 = el.get("lon") or el.get("center", {}).get("lon")
                if lat2 and lon2:
                    return name, state, (lat2, lon2)
        # Wait before retrying
        attempt += 1
        time.sleep(delay)

    # If still nothing after retries, keep looping indefinitely
    while True:
        res = requests.post("https://overpass-api.de/api/interpreter", data={"data": query})
        if res.ok:
            elements = res.json().get("elements", [])
            if elements:
                el = elements[0]
                name = el.get("tags", {}).get("name", "Irrigation Source")
                lat2 = el.get("lat") or el.get("center", {}).get("lat")
                lon2 = el.get("lon") or el.get("center", {}).get("lon")
                if lat2 and lon2:
                    return name, state, (lat2, lon2)
        time.sleep(delay)

import requests
import time

def get_nearest_krishi_center(lat, lon, max_retries=5, delay=3):
    """Find nearest Krishi / Agriculture center using Overpass API, retrying until found."""
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

    # Initial limited retries
    attempt = 0
    while attempt < max_retries:
        res = requests.post("https://overpass-api.de/api/interpreter", data={"data": query})
        if res.ok:
            elements = res.json().get("elements", [])
            if elements:
                el = elements[0]
                name = el.get("tags", {}).get("name", "Krishi Center")
                lat2 = el.get("lat") or el.get("center", {}).get("lat")
                lon2 = el.get("lon") or el.get("center", {}).get("lon")
                if lat2 and lon2:
                    return name, state, (lat2, lon2)
        attempt += 1
        time.sleep(delay)

    # Continuous loop if still not found
    while True:
        res = requests.post("https://overpass-api.de/api/interpreter", data={"data": query})
        if res.ok:
            elements = res.json().get("elements", [])
            if elements:
                el = elements[0]
                name = el.get("tags", {}).get("name", "Krishi Center")
                lat2 = el.get("lat") or el.get("center", {}).get("lat")
                lon2 = el.get("lon") or el.get("center", {}).get("lon")
                if lat2 and lon2:
                    return name, state, (lat2, lon2)
        time.sleep(delay)


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

        # ✅ Theme handling
        theme_mode = st.session_state.get("theme", "🌙 Dark")
        if theme_mode == "🌞 Light":
            template = "plotly_white"
            font_color = "#087f23"   # green text for light mode
            axis_color = "#087f23"
        else:
            template = "plotly_dark"
            font_color = "#e6eef6"   # light gray for dark mode
            axis_color = "#e6eef6"

        # ✅ Build DataFrame and Chart
        df = pd.DataFrame({"Crop": crops[:5], "Production": production[:5]})
        fig = px.bar(df, x="Crop", y="Production", color="Crop",
                     title=f"Top 5 Crop Productions in {state}")

        # ✅ Apply full theme-based layout
        fig.update_layout(
            template=template,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=font_color, size=14),
            title=dict(font=dict(color=font_color, size=18)),
            legend=dict(font=dict(color=font_color, size=12)),
            xaxis=dict(
                title_font=dict(color=axis_color),
                tickfont=dict(color=axis_color),
                showgrid=False
            ),
            yaxis=dict(
                title_font=dict(color=axis_color),
                tickfont=dict(color=axis_color),
                showgrid=True
            )
        )

        st.plotly_chart(fig, use_container_width=True)



# --------------------------------------------------------------------
# Streamlit Layout and Logic
# --------------------------------------------------------------------
st.set_page_config(page_title="AgroMitra Dashboard", layout="wide")
import streamlit as st

# --- Initialize theme ---
if "theme" not in st.session_state:
    st.session_state.theme = "🌙 Dark"

# --- Render a custom toggle switch (centered at top) ---
st.markdown("""
<style>
.theme-toggle {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 1rem;
}
.switch {
  position: relative;
  display: inline-block;
  width: 60px;
  height: 34px;
}
.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: .4s;
  border-radius: 34px;
}
.slider:before {
  position: absolute;
  content: "🌞";
  height: 26px;
  width: 26px;
  left: 4px;
  bottom: 4px;
  background-color: white;
  transition: .4s;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}
input:checked + .slider {
  background-color: #2196F3;
}
input:checked + .slider:before {
  transform: translateX(26px);
  content: "🌙";
}
</style>

<div class="theme-toggle">
  <label class="switch">
    <input type="checkbox" id="themeSwitch" onchange="setTheme(this.checked)">
    <span class="slider"></span>
  </label>
</div>

<script>
  const themeSwitch = window.parent.document.getElementById('themeSwitch');
  const currentTheme = window.parent.document.body.getAttribute('data-theme');
  if (currentTheme === 'dark') themeSwitch.checked = true;

  function setTheme(isDark) {
    const streamlitDoc = window.parent.document;
    const theme = isDark ? '🌙 Dark' : '🌞 Light';
    window.parent.postMessage({type: 'theme-change', value: theme}, '*');
  }
</script>
""", unsafe_allow_html=True)

# --- Listen for theme toggle state ---
theme_mode = st.session_state.theme

# This runs once per rerun triggered by JS
if "theme_change_event" not in st.session_state:
    st.session_state.theme_change_event = None

# We can simulate theme sync via a Streamlit rerun button if needed
if st.button("🔄 Change Theme"):
    st.session_state.theme = "🌙 Dark" if st.session_state.theme == "🌞 Light" else "🌞 Light"

theme_mode = st.session_state.theme


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

# 🌞 Apply custom styles only for Light Mode (keep sidebar same)
if theme_mode == "🌞 Light":
    st.markdown("""
        <style>
            /* ---------- Main Page Background ---------- */
            body, .stApp {
                background-color: #f9f9f9 !important;
                color: #000000 !important;
            }

            /* ---------- Main Dashboard Text ---------- */
            .block-container h1, 
            .block-container h2, 
            .block-container h3, 
            .block-container h4, 
            .block-container h5, 
            .block-container h6, 
            .block-container p, 
            .block-container div, 
            .block-container span {
                color: #45a049 !important;  /* Green text for main content */
            }

            /* ---------- Sidebar (unchanged for both modes) ---------- */
            section[data-testid="stSidebar"] {
                background-color: #1a1a1a !important; /* consistent dark sidebar */
            }
            section[data-testid="stSidebar"] * {
                color: #ffffff !important;
            }

            /* ---------- Metric Cards ---------- */
            .stMetric {
                background: rgba(255,255,255,0.9) !important;
                color: #087f23 !important;
                border-radius: 10px;
                padding: 0.5rem;
            }

            /* ---------- Buttons ---------- */
            .stButton>button {
                background-color: #087f23 !important;
                color: white !important;
                border: none;
            }
            .stButton>button:hover {
                background-color: #0a5f1d !important;
                .stApp {
            background-color: #f5f5f5 !important;
            color: #000 !important;
        }
        div.stButton > button {
            background-color: #333333 !important;
            color: white !important;
            border-radius: 8px;
            border: none;
            transition: 0.3s;
        }
        div.stButton > button:hover {
            background-color: #000000 !important;
            color: #ffffff !important;
        }
            }
        </style>
    """, unsafe_allow_html=True)





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

            # ✅ Detect theme mode
            theme_mode = st.session_state.get("theme", "🌙 Dark")
            if theme_mode == "🌞 Light":
                template = "plotly_white"
                font_color = "#087f23"  # green for light mode
                axis_color = "#087f23"
            else:
                template = "plotly_dark"
                font_color = "#e6eef6"  # light gray for dark mode
                axis_color = "#e6eef6"

            # ✅ Create figure
            fig = px.line(
                df,
                x="Date",
                y=["Temp (°C)", "Humidity (%)"],
                markers=True,
                title="5-Day Temperature & Humidity Trend"
            )

            # ✅ Apply consistent text + axis styling
            fig.update_layout(
                template=template,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=font_color, size=14),
                title=dict(font=dict(color=font_color, size=18)),
                legend=dict(font=dict(color=font_color, size=12)),
                xaxis=dict(
                    title_font=dict(color=axis_color),
                    tickfont=dict(color=axis_color),
                    showgrid=False,
                ),
                yaxis=dict(
                    title_font=dict(color=axis_color),
                    tickfont=dict(color=axis_color),
                    showgrid=True,
                ),
            )

            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Error fetching weather: {e}")



elif page == "Past Trends":
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go

    st.title("🌾 Farmer’s Past Crop Trends and Comparison")

    # ✅ Sample multi-crop data
    data = {
        "Year": [2020, 2020, 2021, 2021, 2022, 2022, 2023, 2023, 2024, 2024],
        "Crop": ["Wheat", "Rice", "Wheat", "Rice", "Wheat", "Rice", "Wheat", "Rice", "Wheat", "Rice"],
        "Crop Yield (tons)": [3.5, 4.2, 4.0, 3.9, 3.8, 4.5, 4.5, 4.7, 4.2, 4.8],
        "Income (₹ in lakhs)": [1.2, 1.4, 1.5, 1.6, 1.4, 1.7, 1.8, 2.0, 1.7, 2.2],
        "Fertilizer Used (kg/acre)": [60, 65, 58, 62, 65, 68, 70, 72, 68, 70],
        "Rainfall (mm)": [820, 800, 760, 780, 850, 860, 900, 910, 870, 880],
    }
    df = pd.DataFrame(data)

    # ✅ Theme-based colors
    if theme_mode == "🌞 Light":
        bg_color = "#f9f9f9"
        text_color = "#000000"
        grid_color = "#d0d0d0"
        select_bg = "#ffffff"
        select_text = "#087f23"
        accent_color = "#087f23"
    else:
        bg_color = "#121212"
        text_color = "#ffffff"
        grid_color = "#444444"
        select_bg = "#333333"
        select_text = "#ffffff"
        accent_color = "#00e676"

    # ✅ Style selectboxes + their labels correctly
    st.markdown(
        f"""
        <style>
        /* --- Selectbox container --- */
        div[data-baseweb="select"] {{
            background-color: {select_bg} !important;
            color: {select_text} !important;
            border-radius: 8px;
            border: 1px solid {accent_color};
        }}
        div[data-baseweb="select"] * {{
            color: {select_text} !important;
        }}

        /* --- Fix the label text (like “Select Crop to View Trends:”) --- */
        label[data-testid="stMarkdownContainer"] p,
        div.row-widget.stSelectbox label p,
        label span {{
            color: {text_color} !important;
            font-weight: 600;
        }}

        /* --- General paragraph/subheader consistency --- */
        .stMarkdown p, .stSubheader, .stHeader, .stText {{
            color: {text_color} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    # ✅ Dropdowns
    crops = ["All"] + sorted(df["Crop"].unique().tolist())
    selected_crop = st.selectbox("Select Crop to View Trends:", crops)
    if theme_mode == "🌞 Light":
        st.markdown("""
            <style>
            /* ----- SELECTBOX + LABEL COLOR FIX ----- */
            div[data-baseweb="select"] > div {
                background-color: #ffffff !important;
                color: #000000 !important;
                border: 1px solid #ccc !important;
                border-radius: 6px !important;
            }
            div[data-baseweb="select"] span {
                color: #000000 !important;
            }
            div[data-baseweb="select"] svg {
                fill: #000000 !important;
            }
            label, .stMarkdown, .stSelectbox label {
                color: #087f23 !important;  /* label color */
            }

            /* Dropdown menu list background and text */
            ul[role="listbox"] {
                background-color: #ffffff !important;
                color: #000000 !important;
                border: 1px solid #ccc !important;
            }
            ul[role="listbox"] li {
                color: #000000 !important;
                background-color: #ffffff !important;
            }
            ul[role="listbox"] li:hover {
                background-color: #e6f4ea !important;
            }
            </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <style>
            div[data-baseweb="select"] > div {
                background-color: #1e1e1e !important;
                color: #ffffff !important;
                border: 1px solid #444 !important;
                border-radius: 6px !important;
            }
            div[data-baseweb="select"] span {
                color: #ffffff !important;
            }
            div[data-baseweb="select"] svg {
                fill: #ffffff !important;
            }
            label, .stMarkdown, .stSelectbox label {
                color: #f5f5f5 !important;
            }

            ul[role="listbox"] {
                background-color: #1e1e1e !important;
                color: #ffffff !important;
                border: 1px solid #444 !important;
            }
            ul[role="listbox"] li:hover {
                background-color: #333333 !important;
            }
            </style>
        """, unsafe_allow_html=True)


    if selected_crop != "All":
        df = df[df["Crop"] == selected_crop]

    metric = st.selectbox("Select Metric to View:", ["Crop Yield (tons)", "Income (₹ in lakhs)"])

    # --- 1️⃣ LINE CHART ---
    st.subheader(f"{metric} Over the Years")
    fig = px.line(
        df,
        x="Year",
        y=metric,
        color="Crop" if selected_crop == "All" else None,
        markers=True,
        title=f"{metric} Over the Years ({selected_crop})"
    )
    fig.update_layout(
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        font_color=text_color,
        title_font_color=text_color,
        xaxis=dict(showgrid=True, gridcolor=grid_color, color=text_color, titlefont=dict(color=text_color), tickfont=dict(color=text_color)),
        yaxis=dict(showgrid=True, gridcolor=grid_color, color=text_color, titlefont=dict(color=text_color), tickfont=dict(color=text_color)),
        legend=dict(font=dict(color=text_color))
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- 2️⃣ BAR CHART ---
    st.subheader(f"Yearly Comparison of {metric}")
    fig_bar = px.bar(
        df,
        x="Year",
        y=metric,
        color="Crop" if selected_crop == "All" else None,
        text=metric,
        title=f"{metric} Comparison by Year ({selected_crop})",
    )
    fig_bar.update_traces(texttemplate='%{text:.2s}', textposition='outside')
    fig_bar.update_layout(
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        font_color=text_color,
        title_font_color=text_color,
        yaxis_title=metric,
        xaxis=dict(color=text_color, gridcolor=grid_color, titlefont=dict(color=text_color), tickfont=dict(color=text_color)),
        yaxis=dict(color=text_color, gridcolor=grid_color, titlefont=dict(color=text_color), tickfont=dict(color=text_color)),
        legend=dict(font=dict(color=text_color))
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # --- 3️⃣ SCATTER PLOT ---
    st.subheader("Correlation Between Yield and Income")
    fig_scatter = px.scatter(
        df,
        x="Crop Yield (tons)",
        y="Income (₹ in lakhs)",
        color="Crop",
        size="Rainfall (mm)",
        hover_data=["Year", "Fertilizer Used (kg/acre)"],
        title="Crop Yield vs Income (Bubble Size = Rainfall)"
    )
    fig_scatter.update_layout(
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        font_color=text_color,
        xaxis=dict(color=text_color, gridcolor=grid_color, titlefont=dict(color=text_color), tickfont=dict(color=text_color)),
        yaxis=dict(color=text_color, gridcolor=grid_color, titlefont=dict(color=text_color), tickfont=dict(color=text_color)),
        legend=dict(font=dict(color=text_color))
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

    # --- 4️⃣ PERCENT CHANGE ---
    st.subheader("📊 Year-over-Year Percentage Change")
    df_change = df.copy()
    for col in df.columns[2:]:
        df_change[col] = df.groupby("Crop")[col].pct_change() * 100

    fig_change = go.Figure()
    for crop in df["Crop"].unique():
        sub_df = df_change[df_change["Crop"] == crop]
        fig_change.add_trace(go.Scatter(
            x=sub_df["Year"], y=sub_df[metric],
            mode='lines+markers', name=crop
        ))
    fig_change.update_layout(
        title="Year-over-Year Percentage Change",
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        font_color=text_color,
        xaxis=dict(title="Year", color=text_color, gridcolor=grid_color, titlefont=dict(color=text_color), tickfont=dict(color=text_color)),
        yaxis=dict(title="Change (%)", color=text_color, gridcolor=grid_color, titlefont=dict(color=text_color), tickfont=dict(color=text_color)),
        legend=dict(font=dict(color=text_color))
    )
    st.plotly_chart(fig_change, use_container_width=True)

    # --- 5️⃣ MOVING AVERAGE ---
    st.subheader("📈 Smoothed 3-Year Moving Average (Crop Yield)")
    fig_ma = go.Figure()
    for crop in df["Crop"].unique():
        sub_df = df[df["Crop"] == crop].copy()
        sub_df["Yield_MA3"] = sub_df["Crop Yield (tons)"].rolling(window=3).mean()
        fig_ma.add_trace(go.Scatter(
            x=sub_df["Year"], y=sub_df["Crop Yield (tons)"],
            mode='lines+markers', name=f"{crop} (Actual)"
        ))
        fig_ma.add_trace(go.Scatter(
            x=sub_df["Year"], y=sub_df["Yield_MA3"],
            mode='lines', name=f"{crop} (MA3)"
        ))
    fig_ma.update_layout(
        title="Crop Yield 3-Year Moving Average Trend",
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        font_color=text_color,
        xaxis=dict(title="Year", color=text_color, gridcolor=grid_color, titlefont=dict(color=text_color), tickfont=dict(color=text_color)),
        yaxis=dict(title="Yield (tons)", color=text_color, gridcolor=grid_color, titlefont=dict(color=text_color), tickfont=dict(color=text_color)),
        legend=dict(font=dict(color=text_color))
    )
    st.plotly_chart(fig_ma, use_container_width=True)

if st.sidebar.button("Analyze Your Soil"):
    crop_url = "https://blynk.cloud/dashboard/563937/global/devices/1/organization/563937/devices/1787820/dashboard"
    components.html(
        f"""
        <script>
            window.open("{crop_url}", "_blank");
        </script>
        """,
        height=0,
    )

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
