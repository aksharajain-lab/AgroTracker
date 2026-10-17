"""Verification harness for app.py (item-by-item, prints PASS/FAIL lines)."""

import ast
import traceback

from streamlit.testing.v1 import AppTest

SRC = open("app.py", encoding="utf-8").read()
TREE = ast.parse(SRC)


def result(label, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))


def get(at, name):
    try:
        return list(at.get(name))
    except Exception:
        return []


def get_elements(at, name):
    return get(at, name)


# --- structural checks on the source -------------------------------------
names = {n.id for n in ast.walk(TREE) if isinstance(n, ast.Name)}
funcs = {n.name for n in ast.walk(TREE) if isinstance(n, ast.FunctionDef)}

has_crops = "CROPS" in names
crops_value = None
for node in ast.walk(TREE):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == "CROPS":
                if isinstance(node.value, ast.Dict):
                    crops_value = [ast.literal_eval(k) for k in node.value.keys]

expected = ["Tomato", "Potato", "Onion", "Banana", "Wheat", "Mango", "Cabbage", "Green chilli", "Rice"]
result("2. CROPS with 9 named crops", crops_value == expected, f"got {crops_value}")

if crops_value:
    keys = None
    for node in ast.walk(TREE):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "CROPS" and isinstance(node.value, ast.Dict):
                    keys = [set(ast.literal_eval(k).keys()) if isinstance(k, ast.Dict) else None for k in node.value.values]
    ok = keys is not None and all(k is not None and {"t_max", "h_max", "shelf"} <= k for k in keys)
    result("2b. every crop has t_max, h_max, shelf", ok, f"key sets {keys}")

result("3. score_day function exists", "score_day" in funcs)

# Exact formula checks (textual, since we cannot execute what isn't there)
if "score_day" in funcs:
    snippet = ast.get_source_segment(SRC, next(n for n in ast.walk(TREE) if isinstance(n, ast.FunctionDef) and n.name == "score_day")) or ""
else:
    snippet = ""
f_ok = (
    "age_mult = 1 + min(age_days / shelf, 1) * 0.5" in snippet.replace("age_days / shelf", "age_days / shelf")
    and "15 if age_days > shelf else 0" in snippet
    and "round(min(base * age_mult + overdue, 100))" in snippet.replace(" ", "").replace("round(min(base*age_mult+overdue,100))", "round(min(base*age_mult+overdue,100))")
)
result("3b. exact score_day formula", f_ok and bool(snippet), "" if f_ok else "formula text not found")

# 4. age wiring
age_ok = "days_old + i" in SRC or "days_old+i" in SRC.replace(" ", "")
result("4. forecast calls score_day(..., age_days = days_old + i)", age_ok)

# 8. twilio
has_twilio = "send_sms" in funcs
phone_send = "def send_sms" in SRC and "st.text_input" in SRC and "phone" in SRC.lower()
result("8. Twilio send_sms + phone input present", has_twilio and phone_send,
       "no Twilio code found" if not has_twilio else "")
if has_twilio:
    fn = next(n for n in ast.walk(TREE) if isinstance(n, ast.FunctionDef) and n.name == "send_sms")
    seg = ast.get_source_segment(SRC, fn) or ""
    print("---- send_sms source ----\n" + seg + "\n-------------------------")

# --- runtime checks -------------------------------------------------------
print("\n== AppTest: initial load ==")
at = AppTest.from_file("app.py", default_timeout=60)
at.run()
exc = [str(e.value) for e in at.exception]
result("1. app script runs without exceptions", not exc, "; ".join(exc))
print(f"       titles={[t.value for t in at.title]}, selectboxes={len(at.selectbox)}, text_inputs={len(at.text_input)}")
print(f"       'impact' easter egg present? markers={[m.value for m in at.markdown if 'Impact Counter' in str(m.value)]}")

print("\n== AppTest: Potato + Pune submit ==")
try:
    at.selectbox[0].set_value("Potato")
    at.text_input[0].set_value("Pune")
    at.button[0].click()
    at.run()
    exc = [str(e.value) for e in at.exception]
    result("7a. Potato/Pune submit raises no exception", not exc, "; ".join(exc)[:500])
    print(f"       subheaders={[s.value for s in at.subheader]}")
    print(f"       element types: {sorted(list(set(at._tree)))}")
    charts = get_elements(at, "plotly_chart")
    tables = get(at, "dataframe") or get(at, "arrow_data_frame") or []
    print(f"       plotly_charts={len(charts)} dataframes={len(tables)}")
    print(f"       tips={[m.value for m in at.markdown][:8]}")
    print(f"       expanders={[e.label for e in at.expander]} code blocks={len(at.code)}")
    result("7b. gauge + chart render", len(charts) >= 2, f"{len(charts)} charts")
    result("7c. forecast table renders", len(tables) >= 1, f"{len(tables)} tables")
    result("7d. tips + alert preview render", len(at.markdown) >= 3 and len(at.code) >= 1,
           f"tips={len(at.markdown)} code={len(at.code)}")
    warn = [w.value for w in at.warning] + [e.value for e in at.error]
    print(f"       warnings/errors: {warn}")
except Exception:
    traceback.print_exc()

print("\n== AppTest: city 'impact' then back ==")
try:
    at.text_input[0].set_value("impact")
    at.button[0].click()
    at.run()
    exc = [str(e.value) for e in at.exception]
    result("6a. typing 'impact' does not crash", not exc, "; ".join(exc)[:300])
    balloon_count = len(at.markdown)  # keep reference
    print(f"       after 'impact': markers={len(at.markdown)}, charts={len(get_elements(at, 'plotly_chart'))}, warnings={[w.value for w in at.warning]}, subheaders={[s.value for s in at.subheader]}")
    at.text_input[0].set_value("Pune")
    at.button[0].click()
    at.run()
    exc = [str(e.value) for e in at.exception]
    result("6b. switching City back to Pune still works", not exc, "; ".join(exc)[:300])
    print(f"       after back: subheaders={[s.value for s in at.subheader]}, charts={len(get_elements(at, 'plotly_chart'))}")
except Exception:
    traceback.print_exc()

print("\n== Fallback path (network-disabled style check) ==")
# Report what the fallback sample data is, without changing it.
import re
m = re.search(r"SAMPLE_TEMPERATURES\s*=\s*(\[[^\]]*\])", SRC)
m2 = re.search(r"SAMPLE_HUMIDITIES\s*=\s*(\[[^\]]*\])", SRC)
print(f"       fallback temps={m.group(1) if m else '?'} hums={m2.group(1) if m2 else '?'}")