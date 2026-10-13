# SkyLink — Flight Booking System (v2)

React + Vite frontend, FastAPI backend, SQLite database (created automatically).

## What changed from the earlier zip
| Your requirement | How it works now |
|---|---|
| 1. Passenger login, profile, bookings, cancellation, edit profile | Real accounts (email + password hashed with PBKDF2, JWT session). Pages: **Sign in / Create account / Forgot password**, **My trips** (Upcoming / Past / Cancelled), **trip detail with cancel + refund quote**, **Profile** (edit details, change password). All data is stored in the database. |
| 2. Domestic + international search | 38 airports (19 Indian, 19 international). Any route works; the page shows domestic/international and asks for passport details only when needed. |
| 3. Seat selection by passenger count, then booking | Pick N seats for N travellers on a cabin map (Business / extra-legroom / standard). Seats are **held for 10 minutes** and cannot be double-booked. Then passenger details → payment. |
| 4. UPI payment | UPI-ID request flow with QR + status polling, plus Card and Net banking. **Sandbox:** no money moves (see limits). |
| 5. Ticket generated | Boarding-pass style e-ticket with QR and per-passenger ticket numbers, **server-made PDF download**, print, and an emailed copy. |
| 6. Email when a fare drops, with the offer | Follow a route, or one flight (bell icon). A background watcher re-prices flights and emails you when the fare falls, including the `SKYDROP` discount code. |
| 7. Professional, unique, animated | Airport-signage design: animated split-flap departure board, animated flight path, page transitions, seat animations, loading states on buttons. Respects "reduce motion". |
| Button → next page | Every step is its own URL (`/flights`, `/book/:id/seats`, `/book/:id/passengers`, `/checkout/:pnr`, `/ticket/:pnr`, …) with a transition and loading indicator. |

## Run it (Windows / PowerShell)
**Terminal 1 — backend**
```powershell
cd SkyLink\backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload
```
API docs: http://127.0.0.1:8000/docs

**Terminal 2 — frontend**
```powershell
cd SkyLink\frontend
npm install
npm run dev
```
Open **http://127.0.0.1:5173** (not index.html directly). The dev server forwards `/api` to the backend, so no CORS setup is needed. If you have an old `.venv` or `node_modules` from the earlier project, delete them first.

## Suggested demo flow
1. **Create account** → you return to the home page.
2. Search e.g. Belagavi → Mumbai, or Delhi → London (international).
3. **Select seats** → choose a seat per traveller → **Continue**.
4. Enter passengers (try promo `SKYDROP`) → **Continue to payment**.
5. UPI: enter `yourname@okaxis` → **Send request** → in the sandbox panel click **Approve payment** (or **Decline** to show a failure). Cards: `4242 4242 4242 4242` succeeds, `4000 0000 0000 0002` is declined.
6. Ticket page: **Download PDF**. Open **My trips** → trip → **Cancel** (refund depends on time to departure).
7. **Fare alerts**: tap the bell on a flight (or add a route alert) → **Simulate fare drop** → the alert email is generated.

## Email setup
With no mail server configured, every email (welcome, ticket, cancellation, password reset, fare drop) is **saved as an HTML file in `backend/outbox/`**; open it in a browser. For real delivery fill in `backend/.env`:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=yourname@gmail.com
SMTP_PASSWORD=<Google App Password>
MAIL_FROM=SkyLink <yourname@gmail.com>
```
Gmail needs 2-Step Verification and an *App password* (your normal password won't work). Restart the backend afterwards.

## Fare-drop alerts
- Every `FARE_TICK_SECONDS` (default 300) the watcher moves fares of upcoming flights a few percent and records each change in `fare_history`.
- Then every active alert is checked: an email is sent when the tracked fare is at least 2 % below the last price you were told (or at/below your target). Fare rises reset the bar, so there is no spam.
- **Simulate fare drop** (Alerts page) forces a ~10 % drop for a demo. Turn off with `DEV_TOOLS=false`.

## Honest limits
- **Flights and fares are simulated.** No airline/GDS feed. Schedules are generated per route/date, stored in the DB and stay stable. For real inventory replace `ensure_flights()` in `backend/app/flights.py` and `reprice_tick()` in `backend/app/fares.py` with a licensed provider.
- **Payments are a sandbox.** The flow mirrors a real gateway (create → pending → success/failed) but no bank/UPI network is contacted; payee `skylink@sandbox` is fake. Razorpay/Cashfree test mode is the natural next step. Card numbers are validated but never stored (last 4 digits only).
- Tickets are simulations, not valid for travel. Time zones use fixed standard offsets (no daylight saving).
- Not production-hardened: no rate limiting, no email verification at sign-up, JWT kept in localStorage.
- The build environment had no browser, so screens were checked by a production build, server-side rendering of public pages and an end-to-end API test, **not by eye**. Expect small spacing/colour tweaks on first run.

## Database
`backend/data/skylink.db` (delete to reset). Tables: users, airports, airlines, flights, flight_seats, bookings, passengers, payments, fare_alerts, fare_history, promos, email_outbox.
`database/schema_sqlite.sql` = live schema · `database/schema_oracle_v2.sql` = Oracle translation for your report (not run on Oracle) · `database/schema_original_oracle.sql` = your original script.

## Promo codes
`SKYDROP` 5 % off (max ₹500) · `WELCOME300` ₹300 off first booking · `INTL1000` ₹1,000 off international trips above ₹25,000.

## Cancellation refund rule
90 % at 48 h+ before departure · 70 % at 24–48 h · 40 % at 4–24 h · none within 4 h.

## Tests
`cd backend; pip install pytest httpx; pytest` runs register → search → seats → pay → ticket → fare alert → cancel.

## Hosting
- **Frontend → Vercel.** Import the repo, set *Root Directory* to `frontend`, preset *Vite*, and add the environment variable `VITE_API_URL=https://<your-backend-url>` **before** building. `frontend/vercel.json` makes direct links such as `/trips` work after a refresh.
- **Backend → a host that runs a normal Python process** (Render, Railway, Fly.io). Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Set `JWT_SECRET`, `FRONTEND_URL` and `CORS_ORIGINS` to your Vercel URL, plus the SMTP values.
- SQLite is a file, so on hosts with a temporary disk it is wiped on redeploy. For anything beyond a demo, move to a hosted Postgres/MySQL (or attach a persistent disk).
