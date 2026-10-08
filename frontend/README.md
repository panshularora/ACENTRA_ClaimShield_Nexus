# ClaimShield Nexus web

Investigator workflow (Step 1): login, manager queue, my cases.

```
npm install
npm run dev
```

Proxies `/api` to `http://127.0.0.1:8000`. Start the backend first:

```
cd ../backend
uv run uvicorn claimshield.api.main:app --reload --app-dir src --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:5173/login
