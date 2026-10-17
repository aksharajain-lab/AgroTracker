---
name: Streamlit artifact deployment
description: Replit artifact deployment details for a single-file Streamlit app in the pnpm workspace.
---

**Rules:**
- For a web artifact that runs a server, configure `[services.production.run]`; the artifact validator rejected `serve = "run"`. Reserve `serve = "static"` for static artifacts.
- Artifact-managed development commands run from their artifact directory. Use paths such as `../../app.py` and `../../.pythonlibs/bin/streamlit` to reach workspace-root files.

**Why:** A static artifact had no running Streamlit process, while the first managed development command failed because its root-relative launcher path resolved from inside the artifact directory.

**How to apply:** Configure the production run command and build environment in the artifact TOML. Keep the development command's working directory in mind, and align its Streamlit port with the artifact service's `localPort`.
