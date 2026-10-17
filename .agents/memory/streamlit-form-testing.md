---
name: Streamlit form testing
description: AppTest behavior when checking submitted values from widgets inside st.form.
---

**Rule:** In Streamlit AppTest, stage form widget values, click the form's submit button, then run the app to verify submitted state. Setting a form input and running alone leaves the form value unsubmitted.

**Why:** Streamlit buffers form widgets until submission; tests that skip the submit event can incorrectly conclude that the app ignores the input.

**How to apply:** Set the target input, click `form_submit_button`, and call `run()` once. For controls outside the form, such as reactive sliders, update their values and run again to verify recalculated output.
