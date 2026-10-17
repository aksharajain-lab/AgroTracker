from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st


st.set_page_config(page_title="Spoilage Risk Meter", page_icon="🌾")
st.markdown("""
<style>
#MainMenu, footer, header {visibility: hidden;}
[data-testid="stToolbar"], [data-testid="stAppDeployButton"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] {display: none !important;}
</style>
""", unsafe_allow_html=True)

CROP_THRESHOLDS = {
    "Tomato": {"max_temp": 25, "max_humidity": 85, "shelf": 10},
    "Potato": {"max_temp": 20, "max_humidity": 90, "shelf": 60},
    "Onion": {"max_temp": 30, "max_humidity": 70, "shelf": 90},
    "Banana": {"max_temp": 28, "max_humidity": 90, "shelf": 7},
    "Wheat": {"max_temp": 30, "max_humidity": 65, "shelf": 180},
    "Mango": {"max_temp": 28, "max_humidity": 85, "shelf": 8},
    "Cabbage": {"max_temp": 20, "max_humidity": 95, "shelf": 21},
    "Green chilli": {"max_temp": 28, "max_humidity": 80, "shelf": 12},
    "Rice": {"max_temp": 30, "max_humidity": 70, "shelf": 180},
}

STORAGE_MODIFIERS = {
    "Open air": {"temp_offset": 0, "humidity_offset": 0, "factor": 1.0},
    "Shed": {"temp_offset": -3, "humidity_offset": -8, "factor": 0.8},
    "Cold storage": {"temp_offset": -15, "humidity_offset": -5, "factor": 0.3},
}

SAMPLE_TEMPERATURES = [29, 31, 30, 32, 31]
SAMPLE_HUMIDITIES = [72, 76, 73, 81, 78]


class CityNotFoundError(Exception):
    """The geocoding service returned no matching city."""


@st.cache_data(ttl=1800, show_spinner=False)
def geocode_city(city):
    response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1},
        timeout=8,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    if not results:
        raise CityNotFoundError(city)
    return results[0]


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_forecast(latitude, longitude):
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "daily": "temperature_2m_max,relative_humidity_2m_mean",
            "forecast_days": 5,
            "timezone": "auto",
        },
        timeout=8,
    )
    response.raise_for_status()
    daily = response.json()["daily"]
    forecast = pd.DataFrame(
        {
            "Date": daily["time"],
            "Max temperature (°C)": daily["temperature_2m_max"],
            "Mean relative humidity (%)": daily["relative_humidity_2m_mean"],
        }
    )
    if len(forecast) != 5 or forecast.isna().any().any():
        raise ValueError("The forecast response did not contain five complete days.")
    return forecast


def sample_forecast():
    today = date.today()
    return pd.DataFrame(
        {
            "Date": [(today + timedelta(days=offset)).isoformat() for offset in range(5)],
            "Max temperature (°C)": SAMPLE_TEMPERATURES,
            "Mean relative humidity (%)": SAMPLE_HUMIDITIES,
        }
    )


def score_day(effective_temp, effective_humidity, crop_limits, storage_settings, age_days):
    temp_score = min(max(effective_temp - crop_limits["max_temp"], 0) * 6, 60)
    humidity_score = min(
        max(effective_humidity - crop_limits["max_humidity"], 0) * 3,
        40,
    )
    base = (temp_score + humidity_score) * storage_settings["factor"]
    age_mult = 1 + min(age_days / crop_limits["shelf"], 1) * 0.5
    overdue = 15 if age_days > crop_limits["shelf"] else 0
    return round(min(base * age_mult + overdue, 100))


def calculate_risk(forecast, crop, storage, days_old):
    crop_limits = CROP_THRESHOLDS[crop]
    storage_settings = STORAGE_MODIFIERS[storage]
    result = forecast.copy()
    result["Effective temperature (°C)"] = (
        result["Max temperature (°C)"] + storage_settings["temp_offset"]
    )
    result["Effective humidity (%)"] = (
        result["Mean relative humidity (%)"] + storage_settings["humidity_offset"]
    )

    result["Risk score"] = [
        score_day(
            row["Effective temperature (°C)"],
            row["Effective humidity (%)"],
            crop_limits,
            storage_settings,
            days_old + forecast_day,
        )
        for forecast_day, (_, row) in enumerate(result.iterrows())
    ]
    return result


def risk_details(score):
    if score < 35:
        return "Low", "🟢"
    if score < 65:
        return "Medium", "🟠"
    return "High", "🔴"


def action_tips(report, crop, storage, level):
    worst = report.loc[report["Risk score"].idxmax()]
    worst_day = pd.Timestamp(worst["Date"]).strftime("%A, %d %b")
    temperature = round(worst["Max temperature (°C)"])
    humidity = round(worst["Mean relative humidity (%)"])

    if level == "Low":
        return [
            "Conditions look safe. Keep routine checks going.",
            "Keep storage clean and dry.",
        ]

    tips = [
        (
            f"For {crop} in {storage.lower()}, the highest risk is {worst_day} "
            f"({temperature}°C, {humidity}% humidity)."
        ),
        f"Ventilate the {storage.lower()} and keep produce off the floor.",
        "Sort produce and remove damaged items early.",
    ]
    if level == "High":
        tips.append(f"Consider selling {crop} early or moving it to shaded/cold storage.")
        if storage == "Open air":
            tips.append(
                "Open-air storage is risky now. Cover with breathable material at minimum."
            )
    return tips


def make_gauge(score):
    figure = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "/100", "font": {"size": 34}},
            title={"text": "Peak spoilage risk"},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1},
                "bar": {"color": "#253b2b"},
                "bgcolor": "white",
                "borderwidth": 1,
                "bordercolor": "#d8dfd4",
                "steps": [
                    {"range": [0, 35], "color": "#b9dfc0"},
                    {"range": [35, 65], "color": "#f6d18a"},
                    {"range": [65, 100], "color": "#edaaa1"},
                ],
            },
        )
    )
    figure.update_layout(height=260, margin={"l": 24, "r": 24, "t": 55, "b": 12})
    return figure


def make_risk_chart(report):
    colors = [
        "#45a568" if score < 35 else "#e79a2f" if score < 65 else "#cf5146"
        for score in report["Risk score"]
    ]
    labels = [pd.Timestamp(day).strftime("%a, %d %b") for day in report["Date"]]
    figure = go.Figure(
        go.Bar(
            x=labels,
            y=report["Risk score"],
            marker_color=colors,
            text=report["Risk score"],
            textposition="outside",
            hovertemplate="%{x}<br>Risk: %{y}/100<extra></extra>",
        )
    )
    figure.update_layout(
        height=300,
        margin={"l": 10, "r": 10, "t": 16, "b": 12},
        yaxis={"title": "Risk score", "range": [0, 110], "dtick": 20},
        xaxis={"title": None},
        showlegend=False,
    )
    figure.add_hline(y=35, line_dash="dot", line_color="#87958a", annotation_text="Medium")
    figure.add_hline(y=65, line_dash="dot", line_color="#87958a", annotation_text="High")
    return figure


st.title("Spoilage Risk Meter")
st.caption("Predict post-harvest spoilage before it happens.")

with st.form("risk_inputs"):
    crop_column, storage_column, city_column = st.columns(3)
    with crop_column:
        selected_crop = st.selectbox("Crop", list(CROP_THRESHOLDS))
    with storage_column:
        selected_storage = st.selectbox("Storage type", list(STORAGE_MODIFIERS))
    with city_column:
        selected_city = st.text_input("City", value="Pune")
        selected_harvest_date = st.date_input(
            "🌾 Harvest date",
            value=date.today() - timedelta(days=2),
            max_value=date.today(),
        )
    submitted = st.form_submit_button("Check risk", type="primary", use_container_width=True)

city = selected_city.strip()

# 🥚 Easter egg: type "impact" in the City box and press Enter
if city.strip().lower() == "impact":
    if "egg_seen" not in st.session_state:
        st.balloons()
        st.session_state["egg_seen"] = True
    st.header("🌱 Secret unlocked: Impact Counter")
    st.caption("What if farmers actually used this?")
    farmers = st.slider("Farmers using the tool", 100, 10000, 1000, step=100)
    tonnes = st.slider("Avg produce stored per farmer (tonnes)", 1.0, 10.0, 2.0, step=0.5)
    loss = st.slider("Typical post-harvest loss (%)", 5, 40, 20)
    cut = st.slider("Loss prevented by early action (%)", 10, 60, 30)
    price = st.slider("Avg crop price (₹/kg)", 5, 60, 20)

    saved_t = farmers * tonnes * (loss / 100) * (cut / 100)
    value = saved_t * 1000 * price
    c1, c2 = st.columns(2)
    c1.metric("Produce saved", f"{saved_t:,.0f} tonnes")
    c2.metric("Value protected", f"₹{value / 100000:,.1f} lakh")
    st.caption("Illustrative estimates based on adjustable assumptions.")
    st.stop()

if submitted:
    st.session_state.pop("risk_report", None)
    st.session_state.pop("risk_error", None)
    st.session_state.pop("risk_warning", None)

    if not city:
        st.session_state["risk_error"] = "Enter a city to check its forecast."
    else:
        try:
            with st.spinner(f"Checking the five-day forecast for {city}…"):
                place = geocode_city(city)
                forecast_data = fetch_forecast(place["latitude"], place["longitude"])
                place_name = place.get("name", city)
                admin_area = place.get("admin1")
                if admin_area and admin_area.lower() != place_name.lower():
                    place_name = f"{place_name}, {admin_area}"
                place_country = place.get("country")
                if place_country:
                    place_name = f"{place_name}, {place_country}"
            st.session_state["risk_report"] = {
                "forecast": forecast_data,
                "crop": selected_crop,
                "storage": selected_storage,
                "city": city,
                "place_name": place_name,
                "sample": False,
                "harvest_date": selected_harvest_date,
            }
        except CityNotFoundError:
            st.session_state["risk_error"] = (
                f"City “{city}” was not found. Check the spelling and try again."
            )
        except (requests.RequestException, ValueError, KeyError, TypeError, IndexError) as error:
            st.session_state["risk_warning"] = (
                f"Weather data is unavailable right now ({error}). Showing sample data so "
                "you can still explore the risk meter."
            )
            st.session_state["risk_report"] = {
                "forecast": sample_forecast(),
                "crop": selected_crop,
                "storage": selected_storage,
                "city": city,
                "place_name": city,
                "sample": True,
                "harvest_date": selected_harvest_date,
            }

if st.session_state.get("risk_error"):
    st.error(st.session_state["risk_error"])

if st.session_state.get("risk_warning"):
    st.warning(st.session_state["risk_warning"])

saved_report = st.session_state.get("risk_report")
if saved_report:
    crop = saved_report["crop"]
    storage = saved_report["storage"]
    days_old = (date.today() - saved_report["harvest_date"]).days
    shelf_life = CROP_THRESHOLDS[crop]["shelf"]
    shelf_life_left = max(shelf_life - days_old, 0)
    report = calculate_risk(saved_report["forecast"], crop, storage, days_old)
    peak_row = report.loc[report["Risk score"].idxmax()]
    peak_score = int(peak_row["Risk score"])
    level, risk_icon = risk_details(peak_score)
    worst_day = pd.Timestamp(peak_row["Date"]).strftime("%A, %d %b")
    tips = action_tips(report, crop, storage, level)

    st.divider()
    source_label = "Sample weather data" if saved_report["sample"] else "Open-Meteo 5-day forecast"
    st.caption(
        f"{saved_report['place_name']} · {crop} · {storage} · {source_label}"
    )
    st.metric(
        "Crop age",
        f"{days_old} days old",
        delta=f"{shelf_life_left} days of shelf life left",
    )
    if days_old > shelf_life:
        st.warning("This crop is past its typical shelf life. Sell or process it ASAP.")
    st.subheader(f"{risk_icon} {level} risk — {peak_score}/100")
    st.write(f"Peak risk is forecast for **{worst_day}**.")

    gauge_column, chart_column = st.columns([0.85, 1.5], vertical_alignment="center")
    with gauge_column:
        st.plotly_chart(make_gauge(peak_score), use_container_width=True)
    with chart_column:
        st.plotly_chart(make_risk_chart(report), use_container_width=True)

    st.subheader("5-day forecast and risk")
    display_report = report[
        [
            "Date",
            "Max temperature (°C)",
            "Mean relative humidity (%)",
            "Effective temperature (°C)",
            "Effective humidity (%)",
            "Risk score",
        ]
    ].copy()
    display_report["Date"] = pd.to_datetime(display_report["Date"]).dt.strftime("%a, %d %b")
    display_report = display_report.rename(
        columns={
            "Max temperature (°C)": "Max temp (°C)",
            "Mean relative humidity (%)": "Mean humidity (%)",
            "Effective temperature (°C)": "Effective temp (°C)",
            "Effective humidity (%)": "Effective humidity (%)",
        }
    )
    st.dataframe(display_report, hide_index=True, use_container_width=True)

    st.subheader("What you can do")
    for tip in tips:
        st.markdown(f"- {tip}")

    first_tip = tips[0]
    message_text = (
        f"Spoilage Risk Meter: {level} risk for {crop} in {saved_report['city']}. "
        f"Peak risk {peak_score}/100 on {worst_day}. {first_tip}"
    )
    with st.expander("Preview alert message"):
        st.caption("Mock SMS / WhatsApp message — not sent")
        st.code(message_text, language=None)

    st.caption(
        "Risk estimates use the selected crop’s safe temperature and humidity thresholds "
        "with your storage adjustment. Use this as an early warning, not a guarantee."
    )
