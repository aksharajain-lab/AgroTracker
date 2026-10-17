#  Spoilage Risk Meter

### Predict post-harvest spoilage *before* it happens.

A lightweight web app that gives farmers and traders an early warning for crop spoilage. Pick your crop, storage type, harvest date, and city. We combine a live 5-day weather forecast with crop-specific tolerance limits and tell you **when** your produce is at risk and **what to do about it**.

**Live demo:** `https://agrotracker-spoilagemanager.streamlit.app/`

**Built at:** `IEEE HackSprint

**Track**: Agritech

**Team**: `AIVORA`

---

##  The Problem

Farmers lose a significant share of their produce *after* harvest, mostly to heat and humidity in storage. Weather apps tell them it's hot. Nothing tells them **"your 9-day-old tomatoes in open storage are in trouble on Thursday."** By the time spoilage is visible, it's too late to act.



##  The Solution

Spoilage Risk Meter turns a generic weather forecast into a **personalized, actionable risk score** for each crop and each day.

1. Enter **crop**, **storage type**, **harvest date**, and **city**
2. Get a **0-100 risk score** for each of the next 5 days
3. See a **gauge, chart, and plain-language tips** (ventilate, move to shade, sell early)
4. Optionally receive the alert as an **SMS**

##  Features

| Feature | What it does |
|---|---|
|  **Live forecast** | 5-day temperature and humidity from Open-Meteo, for any city |
|  **9 crops** | Tomato, Potato, Onion, Banana, Wheat, Mango, Cabbage, Green chilli, Rice |
|  **Storage-aware** | Open air, shed, and cold storage change the exposure and the risk |
|  **Harvest-date aware** | Fresh and days-old stock aren't treated the same. Older stock carries more risk, and expired stock gets flagged |
|  **Clear dashboard** | Risk gauge, 5-day risk chart, and a data table |
|  **Smart tips** | Actions tailored to risk level, crop, and storage type |
|  **Offline fallback** | If the weather API is down, the app switches to sample data instead of crashing |
|  **Hidden easter egg** | There's a secret in here. Can you find it? |

##  How the Risk Score Works

For each forecast day, we check how far the temperature and humidity exceed the crop's safe limits, then adjust for storage and age.

```
effective_temp = max_temp  + storage.temp_offset
effective_hum  = humidity  + storage.humidity_offset

temp_score = min(max(effective_temp - crop.max_temp, 0) * 6, 60)
hum_score  = min(max(effective_hum  - crop.max_hum,  0) * 3, 40)

base       = (temp_score + hum_score) * storage.factor
age_mult   = 1 + min(age_days / crop.shelf_life, 1) * 0.5
overdue    = 15 if age_days > crop.shelf_life else 0

risk = min(round(base * age_mult + overdue), 100)
```

| Risk | Score | Meaning |
|---|---|---|
| 🟢 Low | 0-34 | Conditions look safe |
| 🟠 Medium | 35-64 | Take preventive action |
| 🔴 High | 65-100 | Act now: sell, move, or protect the stock |

> Crop thresholds and shelf-life values are typical estimates for demo purposes and can be tuned per region and variety.

##  Tech Stack

- **Frontend and backend:** [Streamlit](https://streamlit.io) (Python)
- **Charts:** Plotly and Streamlit native charts
- **Data:** pandas
- **Weather and geocoding:** [Open-Meteo](https://open-meteo.com) (free, no API key)
- **SMS (optional):** Twilio

##  Run Locally

```bash
git clone <your-repo-url>
cd <your-repo-folder>
pip install -r requirements.txt
streamlit run app.py
```

The app opens at `http://localhost:8501`.


##  Project Structure

```
.
├── app.py             # The entire app: data, risk engine, UI
├── requirements.txt   # streamlit, requests, pandas, plotly
└── README.md
```

##  What's Next

-  Live mandi (market) prices, so the app can say *"sell now or wait"*
-  Regional language support and voice alerts
-  IoT sensor input for real in-storage temperature and humidity
-  Calibrating crop thresholds with agronomy experts and real spoilage data
-  WhatsApp alerts and farmer-group broadcasts

##  Team

| Name | Role |
|---|---|
| `<Akshara Jain>` | `<Team Leader- AI assisstent development & Technical implementation>` |
| `<Daksh Sharma>` | `<Product Strategy & Pitch and presentation>` |

---

<p align="center"><i>Because the best time to save a harvest is before it spoils.</i> 🌱</p>
