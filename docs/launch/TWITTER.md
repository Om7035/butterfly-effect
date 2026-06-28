# Twitter/X Thread

**Tweet 1 — The hook:**

Hamas attacks Israel (Oct 7, 2023).

Everyone saw: oil prices spike.

What nobody saw coming:
→ Red Sea shipping reroutes
→ Suez Canal traffic -40%
→ EU LNG prices +28%
→ ECB's "mission accomplished" on inflation... reversed.

That last effect showed up in Eurostat data 90 days later.

I built a tool that traces these chains automatically.

🧵

---

**Tweet 2 — War domain:**

Type: "Hamas attacks Israel — October 7, 2023"

Get back:
Hop 1 [t+2h]: Attack → IDF mobilization (0.97)
Hop 2 [t+6h]: IDF → Brent crude +8.3% (0.82)
Hop 3 [t+72h]: IDF → Red Sea reroutes (0.71) ← most analysts stop at hop 2
Hop 4 [t+96h]: Red Sea → Suez -40% (0.85)
Hop 5 [t+168h]: Suez → EU LNG +28% (0.63) ← 3rd order
Hop 6 [t+720h]: LNG → EU inflation restarts (0.58) ← 4th order

---

**Tweet 3 — Economics domain:**

Type: "Fed raises rates 75bps"

Get back:
Hop 1 [t+2h]: Fed → Treasury yields +75bps
Hop 2 [t+48h]: Yields → mortgage rates +92bps
Hop 3 [t+168h]: Mortgages → housing starts -247k ← 3rd order
Hop 4 [t+720h]: Housing → construction job losses ← 4th order

The 4th-order effect shows up in JOLTS data 30 days after housing starts.
Most analysts attribute it to "the economy."

---

**Tweet 4 — Tech domain:**

Type: "OpenAI releases AGI-level model"

Get back:
Hop 1: AI capability → $200B VC flood
Hop 2: VC → GPU shortage, data center buildout
Hop 3: AI → white-collar employment renegotiation ← 3rd order
Hop 4: Employment disruption → AI regulation pressure ← 4th order
Hop 5: Regulatory arbitrage → AI companies incorporate in Singapore ← 5th order

That last one is already visible in company registration data.

---

**Tweet 5 — Climate + Supply chain:**

Type: "Category 5 hurricane makes landfall in Miami"

3rd-order effect: mortgage market repricing across the entire Southeast — not just Miami.

Type: "Global semiconductor shortage declared"

5th-order effect: the chip shortage contributed to the 2022 Fed rate hike cycle.
A supply chain event in Taiwan triggered a monetary policy response that affected every borrower in America.

---

**Tweet 6 — How it works:**

4 ingredients:

1. LLM parses your question → domains, actors, severity
2. Evidence fetched in parallel → Wikipedia, FRED, DuckDuckGo, World Bank, GDELT
3. Agent simulation → Timeline A (event) vs Timeline B (no event), diff = true causal impact
4. Chain extraction → hops ordered by timing, confidence from simulation divergence

The simulation runs in 0.01 seconds. Total time: ~40 seconds.

---

**Tweet 7 — Open source, free to run:**

Open source. MIT license.

Free to run:
- No paid APIs required (uses Gemini free tier)
- No Docker required
- No database required
- Works on a clean machine in 5 minutes

```bash
git clone github.com/Om7035/butterfly-effect
cd backend && pip install -r requirements.txt
# add free Gemini key to .env
python -m uvicorn butterfly.main:app --port 8000
```

---

**Tweet 8 — CTA:**

If you'd use this — or know someone who would — a ⭐ helps more people find it.

github.com/Om7035/butterfly-effect

Also: if you find a wrong causal chain, open an issue. That's how we make it better.

What event would you trace first?
