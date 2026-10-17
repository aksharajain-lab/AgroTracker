"""Runtime verification for app.py (items 1-7). AppTest + forced-offline fallback."""

import re
from datetime import date, timedelta

import requests
from streamlit.testing.v1 import AppTest

OFFLINE = True


def _offline(*args, **kwargs):
    raise requests.RequestException("offline (forced by verifier)")


_real_get = requests.get
requests.get = _offline

failed = []


def report(label, ok, detail=""):
    if not ok:
        failed.append(label)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))


def make_app():
    at = AppTest.from_file("app.py", default_timeout=60)
    at.run()
    return at


def submit(at):
    at.button[0].click()
    at.run()
    return at


def set_inputs(at, crop=None, storage=None, city=None, harvest=None):
    if crop:
        at.selectbox[0].set_value(crop)
    if storage:
        at.selectbox[1].set_value(storage)
    if city is not None:
        at.text_input[0].set_value(city)
    if harvest is not None:
        at.date_input[0].set_value(harvest)
    return at


def peak(at):
    for s in at.subheader:
        m = re.search(r"—\s*(\d+)/100", s.value)
        if m:
            return int(m.group(1))
    return None


def warnings(at):
    return [w.value for w in at.warning]


def metric(at, label):
    for m in at.metric:
        if m.label == label:
            return m
    return None


def exceptions(at):
    return [f"{e.name}: {e.value}" for e in at.exception]


def elements(at):
    return sorted({k for k in dir(at) if not k.startswith("_") and isinstance(getattr(at, k, None), (list,))})


# ---------------------------------------------------------------- item 1
print("== 1. App starts without exceptions ==")
at0 = make_app()
ex = exceptions(at0)
report("1. initial load has no exception", not ex, "; ".join(ex)[:400])
print(f"       trace title={at0.title[0].value!r}, widgets: boxes={len(at0.selectbox)} "
      f"text={len(at0.text_input)} date={len(at0.date_input)}")

# ------------------------------------------------- items 2-4 (offline)
requests.get = _offline
today = date.today()

print("\n== 2. Tomato / Open air / Pune, fallback forced ==")
at_fresh = set_inputs(make_app(), crop="Tomato", storage="Open air", city="Pune", harvest=today)
submit(at_fresh)
ex = exceptions(at_fresh)
peak_today = peak(at_fresh)
warn_today = warnings(at_fresh)
src_today = " | ".join(c.value for c in at_fresh.caption)
print(f"       harvest=today  peak={peak_today} warnings={warn_today}")
print(f"       captions={src_today}")

at_old = set_inputs(make_app(), crop="Tomato", storage="Open air", city="Pune", harvest=today - timedelta(days=12))
submit(at_old)
ex2 = exceptions(at_old)
peak_old = peak(at_old)
warn_old = warnings(at_old)
src_old = " | ".join(c.value for c in at_old.caption)
print(f"       harvest=-12d   peak={peak_old} warnings={warn_old}")
print(f"       captions={src_old}")

report("2a. both runs exception-free", not ex and not ex2, "; ".join(ex + ex2)[:400])
report("2b. fallback (sample data) actually forced",
       "sample weather data" in src_today.lower() and "sample weather data" in src_old.lower(),
       src_today[:160])
report("2c. 12-day-old peak risk is HIGHER than today's",
       peak_today is not None and peak_old is not None and peak_old > peak_today,
       f"{peak_old} > {peak_today}")
report("2d. 12-day case shows 'past its typical shelf life' warning",
       any("past its typical shelf life" in w for w in warn_old),
       "; ".join(warn_old) or "no warning")
report("2e. today's case has NO shelf-life warning",
       not any("past its typical shelf life" in w for w in warn_today),
       "; ".join(warn_today) or "no warning")

# ---------------------------------------------------------------- item 3
print("\n== 3. Same inputs, Cold storage ==")
at_cold = set_inputs(make_app(), crop="Tomato", storage="Cold storage", city="Pune",
                     harvest=today - timedelta(days=12))
submit(at_cold)
peak_cold = peak(at_cold)
print(f"       cold / -12d peak={peak_cold} (open air peak={peak_old}) warnings={warnings(at_cold)}")
at_cold_today = set_inputs(make_app(), crop="Tomato", storage="Cold storage", city="Pune", harvest=today)
submit(at_cold_today)
peak_cold_today = peak(at_cold_today)
print(f"       cold / today  peak={peak_cold_today} (open air peak={peak_today})")
report("3a. Cold storage risk much LOWER than Open air (12-day case)",
       peak_cold is not None and peak_old is not None and peak_cold < peak_old
       and peak_old - peak_cold >= 30,
       f"{peak_cold} vs {peak_old}")
report("3b. Cold storage risk much LOWER than Open air (today)",
       peak_cold_today is not None and peak_today is not None and peak_cold_today < peak_today,
       f"{peak_cold_today} vs {peak_today}")
report("3c. cold-storage run exception-free", not exceptions(at_cold) and not exceptions(at_cold_today),
       "; ".join(exceptions(at_cold) + exceptions(at_cold_today))[:300])

# ---------------------------------------------------------------- item 4
print("\n== 4. 'Crop age' metric ==")
m12 = metric(at_old, "Crop age")
m0 = metric(at_fresh, "Crop age")
print(f"       -12d metric={None if m12 is None else (m12.label, m12.value, m12.delta)}")
print(f"       today metric={None if m0 is None else (m0.label, m0.value, m0.delta)}")
report("4. 'Crop age' shows '12 days old'",
       m12 is not None and m12.value == "12 days old",
       "not found" if m12 is None else m12.value)

# --------------------------------------------------------- items 5 and 6
print("\n== 5. City = 'impact' easter egg ==")
at_egg = make_app()
set_inputs(at_egg, city="impact")
submit(at_egg)
egg_exc = exceptions(at_egg)
headers = [h.value for h in at_egg.header]
slider_labels = [s.label for s in at_egg.slider]
metric_pairs = [(m.label, m.value) for m in at_egg.metric]
captions = [c.value for c in at_egg.caption]
egg_seen = at_egg.session_state.get("egg_seen")
balloons_attr = [name for name in ("balloons", "blobs") if hasattr(at_egg, name)]
n_balloon = 0
if balloons_attr:
    for name in balloons_attr:
        n_balloon += len(list(getattr(at_egg, name)))
print(f"       exceptions={egg_exc}")
print(f"       headers={headers}")
print(f"       captions={captions}")
print(f"       sliders({len(slider_labels)})={slider_labels}")
print(f"       metrics({len(metric_pairs)})={metric_pairs}")
print(f"       session egg_seen={egg_seen}  balloon elements={balloons_attr} n={n_balloon}")
print(f"       subheaders={ [s.value for s in at_egg.subheader] } charts={len(list(at_egg.get('plotly_chart')))}")
report("5. 'impact' shows the easter egg without crashing",
       not egg_exc and headers and "Secret unlocked: Impact Counter" in headers[0] and egg_seen is not False,
       "; ".join(egg_exc)[:300])

print("\n== 6. City back to Pune ==")
set_inputs(at_egg, city="Pune")
submit(at_egg)
ex6 = exceptions(at_egg)
peak6 = peak(at_egg)
print(f"       exceptions={ex6}")
print(f"       subheaders={[s.value for s in at_egg.subheader]}")
print(f"       metric={[(m.label, m.value) for m in at_egg.metric]}")
print(f"       headers={ [h.value for h in at_egg.header] } sliders={len(list(at_egg.slider))}")
print(f"       charts={len(list(at_egg.get('plotly_chart')))} tables={len(list(at_egg.get('dataframe')))} "
      f"code={len(list(at_egg.code))} warnings={[w.value for w in at_egg.warning]}")
report("6a. no exception after switching back to Pune", not ex6, "; ".join(ex6)[:300])
report("6b. normal risk result restored (metric + gauge + table + tips + alert)",
       peak6 is not None and at_egg.metric and len(list(at_egg.get("plotly_chart"))) == 2
       and len(list(at_egg.get("dataframe"))) == 1 and len(list(at_egg.markdown)) >= 3
       and len(list(at_egg.code)) == 1 and not at_egg.header,
       f"peak={peak6}")

# ---------------------------------------------------------------- item 7
print("\n== 7. Potato, harvest 2 days ago, Pune (live network) ==")
requests.get = _real_get
at_p = set_inputs(make_app(), crop="Potato", storage="Open air", city="Pune",
                  harvest=today - timedelta(days=2))
submit(at_p)
ex7 = exceptions(at_p)
charts = len(list(at_p.get("plotly_chart")))
tables = len(list(at_p.get("dataframe")))
code = len(list(at_p.code))
cap = [c.value for c in at_p.caption]
print(f"       exceptions={ex7}")
print(f"       subheaders={[s.value for s in at_p.subheader]}")
print(f"       metric={[(m.label, m.value, m.delta) for m in at_p.metric]}")
print(f"       charts={charts} tables={tables} code_blocks={code}")
print(f"       captions={cap}")
print(f"       tips={[m.value for m in at_p.markdown]}")
print(f"       warnings={[w.value for w in at_p.warning]} errors={[e.value for e in at_p.error]}")
report("7a. no exception", not ex7, "; ".join(ex7)[:400])
report("7b. gauge + bar chart", charts == 2, f"{charts} plotly charts")
report("7c. table", tables == 1, f"{tables}")
report("7d. tips", len(list(at_p.markdown)) >= 3, f"{len(list(at_p.markdown))} markdown lines")
report("7e. alert preview", code == 1 and any("Preview alert message" == e.label for e in at_p.expander))
report("7f. 'Crop age' metric shows '2 days old'",
       metric(at_p, "Crop age") is not None and metric(at_p, "Crop age").value == "2 days old",
       "missing" if metric(at_p, "Crop age") is None else metric(at_p, "Crop age").value)

print("\n================ SUMMARY ================")
print("FAILURES:", failed if failed else "none — all items passed")