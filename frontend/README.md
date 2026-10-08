# ClaimShield Nexus web

Cinematic 3D landing plus a working SIU app on the live FastAPI backend.

```
npm install
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`. Start the backend first:

```
cd ../backend
uv run uvicorn claimshield.api.main:app --reload --app-dir src --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:5173/

## Judge path (about 90 seconds)

1. Scroll the landing: improper payments are not fraud, cases are networks, harm goes first.
2. **Enter SIU** as `manager@demo.claimshield` / `demo-manager`.
3. Load tiny seed 7. Watch the 3D lane towers fill 40 investigator hours.
4. Open a harm or selected case. Orbit the 2-hop neighbourhood.
5. Record a human decision (20+ character reason). Check audit or a pending precedent.

## Routes

| Path | What |
| --- | --- |
| `/` | 3D scroll story |
| `/login` | Live cookie login |
| `/manager/queue` | Capacity knapsack queue |
| `/investigator/cases` | Worklist |
| `/investigator/workspace/:caseId` | Brief, claims, timeline, 3D network, decide |
| `/wiki/proposals` | Precedent approval |
| `/audit` | Hash-chained log |

`prefers-reduced-motion` slows camera auto-rotate.
