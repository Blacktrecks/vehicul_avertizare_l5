# Copilot instructions – Hybrid vehicle warning system (Raspberry Pi 4/5, Django)

> How to use this file
> 1. Save it as `.github/copilot-instructions.md` in the repo (Copilot reads it automatically), AND keep a copy in the repo root.
> 2. In VS Code open Copilot Chat in **Agent mode**, and paste ONE phase prompt at a time (section 5). Run the tests after every phase before starting the next one.
> 3. Never ask Copilot to "do everything". Small phases = fewer broken files.

---

## 1. Project context

University project (course: "Proiectarea sistemelor încorporate"), team: Roman Petrica, Ghidoarca Petru Cristi.
Each vehicle node sees nearby vehicles over **Zigbee** (XBee3) and reports its position over **LoRa Meshtastic** (ESP module) to a control centre. On impact or hard braking the driver of nearby vehicles gets an alert (visual + sound). **Warning only – the system never controls brakes or engine.**

- Hardware: Raspberry Pi 4 (development/validation) and Pi 5 (target), 7" touch display, MPU6050 accelerometer (I2C), buzzer on GPIO17 via NPN transistor, LED on GPIO27 (330 Ω), XBee3 on `/dev/ttyUSB0` (9600 baud), Meshtastic ESP on `/dev/ttyACM0` (115200 baud). **No GPS**: position comes from a configured/simulated route.
- Software architecture follows AUTOSAR layering (from lab L3): `APP (POS, ACC, NBR, HMI, RPT) → RTE → IOC / SDC / SCHED → MCD drivers (PCS, I2C, USB, TIM)`.
- The app talks to the platform only through RTE; the UI is the HMI part of APP.
- Current state: the MCD layer (L4) is done and tested: `mcd/pcs.py`, `i2c.py`, `mpu6050.py`, `usb.py`, `tim.py`, `config.py`, `test.py`. Django serves a basic page. Everything above MCD is still missing.
- Note: Meshtastic is **not** LoRaWAN (no gateway, no ChirpStack). Use "LoRa Meshtastic" everywhere.

## 2. Hard rules (never break these)

1. Keep the existing MCD function names and signatures (`PCS_vSetOutputGpio`, `I2C_u8ReadReg`, `USB_u16Write`, `TIM_bHasElapsed`, …). They are referenced by lab documents. You may add functions, not rename.
2. Drivers must keep working **without hardware** (simulation mode, `MCD_SIMULATE=auto|1|0`) so the project runs on a PC in VS Code.
3. Invalid parameters are ignored or raise a clear error exactly as the current tests expect. Do not weaken existing tests; add new ones.
4. Alert logic is polling-based, single main thread for hardware access, with a lock around driver access (the web server is multi-threaded).
5. Every endpoint that actuates hardware: POST only, CSRF-protected or restricted to localhost/LAN setting, **auto-off timeout** (max 5 s for manual buzzer/LED tests), and it must refuse when mode is not explicitly allowed.
6. UI text in **Romanian with correct diacritics** (ă â î ș ț). Code, identifiers, comments and commit messages in English.
7. No paid services, no sign-ups, no CDN that is needed at runtime (the Pi can be offline). Vendor any JS/CSS locally in `static/`. Free/open-source only.
8. Python 3.11+, Django 5.x (`>=5.0,<6.0`), no database required (`DATABASES = {}` stays unless a phase says otherwise).
9. Security defaults: `DEBUG` off unless `DJANGO_DEBUG=1`; `ALLOWED_HOSTS` from env; secret key from env with a dev fallback only when DEBUG is on.
10. Pi chip selection: do not hardcode gpiochip order. Detect the header chip by label (`pinctrl-rp1` on Pi 5, `pinctrl-bcm2711` on Pi 4) and allow override with `MCD_GPIOCHIP`.

## 3. Target structure

Mirror the layered structure from the lab (APP / RTE / IOC / SDC / SCHED / MCD) as Python packages, one Django project on top.

```
vehicul_avertizare/
├─ manage.py
├─ vehicul/                 # Django project (settings, urls, wsgi)
├─ mcd/                     # DONE – drivers: pcs, i2c, mpu6050, usb, tim, config, test
├─ ioc/                     # input/output conditioning: accelerometer, alert channels -> pins
├─ sdc/                     # packets, HMAC signature, sequence numbers, Zigbee/Meshtastic framing
├─ sched/                   # periodic tasks: 1 s (position, Zigbee), 60 s (LoRa report), alert expiry
├─ rte/                     # the only interface APP uses: rte.py (vSetAlertaSonora, vSetAlertaVizuala, ...)
├─ app/                     # POS, ACC, NBR, HMI logic, RPT  (no hardware imports!)
├─ web/                     # Django app: views, urls, templates, static (the HMI)
│  ├─ templates/web/        # base.html, dashboard.html, diagnostics.html, operator.html
│  └─ static/web/           # css/, js/, vendor/
├─ docs/                    # tabel_pini.md, wiring.md, requirements_trace.md, hazards.md
├─ tests/                   # one test module per layer
└─ README.md
```

Dependency rule: `web → rte → ioc/sdc/sched → mcd`. `app` calls only `rte`. Nothing imports upward. Add a test that fails if `app` imports `mcd` directly.

## 4. UI specification (the HMI)

Target screen: **7" touch display, 800×480 or 1024×600**, shown in Chromium kiosk mode, plus any desktop browser. Design for the driver: glanceable, big, high contrast.

### 4.1 Pages
| URL | Purpose |
| --- | --- |
| `/` | **Driver dashboard** (kiosk): radar of nearby vehicles, own speed/heading, status bar, alert overlay |
| `/diagnostics/` | Engineer page: pin table, live accelerometer chart, test buzzer/LED, run self-test, link status, event log |
| `/operator/` | Control-centre view: map with all vehicles from LoRa reports, alert list, history |

A top navigation (or hidden long-press menu on the kiosk) switches pages. All pages share `base.html`.

### 4.2 Driver dashboard layout
- **Top status bar** (always visible): icons + short labels for Zigbee, LoRa Meshtastic, MPU6050, buzzer/LED state, clock; a clear **"SIMULARE"** badge when any driver is simulated. Colours: green = OK, amber = degraded/no data in last 5 s, red = fault.
- **Centre: radar view** (SVG or canvas, no external libs): own vehicle at centre, concentric rings (25 / 50 / 100 m, auto-scale), neighbours as arrows rotated by heading, colour by relevance (grey = irrelevant direction, white = relevant, red = in alert). Tap a vehicle → side card with ID, distance, bearing, speed, last seen.
- **Left/right info**: large speed number, heading with compass letter, neighbour count.
- **Alert overlay** (the most important element): full-width banner that covers the top half, flashing red/amber, large text (e.g. "ATENȚIE: IMPACT ÎN FAȚĂ – 42 m"), the source vehicle ID, a countdown to auto-expire, and a big **"Confirm"** button (min. 64 px high). It must be readable in direct sunlight (contrast ≥ 7:1). The buzzer/LED state is mirrored on screen so a silent buzzer is visible.
- **Day/night theme** toggle (dark default). Respect `prefers-color-scheme` on desktop.
- **Touch rules**: tap targets ≥ 48 px (64 px for critical), no hover-only behaviour, no text below 16 px (alert text ≥ 32 px), no scrolling on the dashboard.

### 4.3 Diagnostics page
- Pin mapping table (from `PIN_TABLE`), with live level indicators for buzzer and LED.
- Buttons: "Test buzzer 1 s", "Test LED 1 s" (POST with `duration_ms`), "Oprește tot" (emergency off, always visible).
- Live accelerometer chart (ax, ay, az, |a|) for the last 30 s, drawn with plain canvas, updated every 200 ms; threshold line for impact detection; "Simulează impact" button (simulation mode only).
- Self-test button with a pass/fail summary and expandable log.
- Link status table: last RX time, packet counters, errors for Zigbee and Meshtastic.
- Event log (last 100 events: alert raised/cleared, sensor error, port opened/closed), auto-scrolling, filter by level.

### 4.4 Operator page
- Map with vehicle markers and the last route. Use Leaflet vendored locally; tiles from OpenStreetMap when online, and an **offline fallback**: plain SVG canvas of the simulated route with a scale bar, so it works with no internet.
- Alert list with time, vehicle, type (impact / hard braking), distance to others, "acknowledged" state.
- Vehicle table: ID, last report age (turns amber after 90 s, red after 180 s), speed, heading.

### 4.5 Data flow
- Server pushes state with **Server-Sent Events** at `/api/stream/` (fallback: polling `/api/state/` every 500 ms). One JSON document, versioned (`"v": 1`).
- JSON shape (keep stable, document it in `docs/api.md`):
```json
{
  "v": 1, "ts": 1730000000.0, "mode": "simulation|hardware",
  "ego": {"id": "V1", "lat": 47.15, "lon": 27.59, "speed_kmh": 42, "heading_deg": 90},
  "neighbours": [{"id": "V2", "lat": 47.1502, "lon": 27.5903, "speed_kmh": 40, "heading_deg": 88,
                   "distance_m": 31, "bearing_deg": 85, "relevant": true, "age_s": 0.8}],
  "alert": {"active": false, "type": null, "source": null, "distance_m": null, "expires_in_s": null},
  "outputs": {"buzzer": 0, "led": 0},
  "accel": {"ax": 0.0, "ay": 0.0, "az": 1.0, "mag": 1.0},
  "links": {"zigbee": {"state": "ok", "last_rx_s": 0.4, "rx": 120, "err": 0},
            "meshtastic": {"state": "ok", "last_rx_s": 12.0, "rx": 4, "err": 0}},
  "drivers": {"gpio": "simulated", "i2c": "simulated", "usb_zigbee": "simulated", "usb_meshtastic": "simulated"}
}
```
- Actions (POST, JSON): `/api/outputs/` `{channel, value, duration_ms}`, `/api/alert/ack/`, `/api/sim/impact/`, `/api/selftest/`, `/api/outputs/off/`.

### 4.6 Visual style
- One CSS file with CSS variables (colours, spacing, font sizes), two themes. System font stack, no web-font downloads.
- 8 px spacing grid, rounded cards, one accent colour. Status colours always paired with an icon or text (colour-blind safe).
- Smooth but light animation only (CSS transforms), `prefers-reduced-motion` respected; alert flash ≤ 3 Hz.

## 5. Phase prompts (paste one at a time, in Agent mode)

### Phase 0 – Cleanup and safety
> Read `.github/copilot-instructions.md` first. Do not change any MCD function names. Tasks: (1) in `mcd/pcs.py` replace the hardcoded `(4, 0)` chip loop with detection by chip label (`pinctrl-rp1` for Pi 5, `pinctrl-bcm2711` for Pi 4), overridable with env `MCD_GPIOCHIP`; fall back to simulation only when `MCD_SIMULATE=auto`. (2) In `vehicul/settings.py`: DEBUG default off, `ALLOWED_HOSTS` and `SECRET_KEY` from env, add `DJANGO_ALLOWED_HOSTS=*` handling for LAN use. (3) Pin Django to `>=5.0,<6.0` in both requirements files. (4) Add tests for the chip selection (mock lgpio). (5) Run `python -m mcd.test` and `python manage.py test` and show me the results. Do not touch the UI yet.

### Phase 1 – Layers above MCD (no UI)
> Create packages `ioc`, `sdc`, `sched`, `rte`, `app` as in section 3. Implement: `ioc.IOC_vSetOutputPort(channel, value)` with channels `IOC_CH_BUZZER=0x0001`, `IOC_CH_LED=0x0002` (routing table to GPIO17/27, unknown channel ignored); `rte.vSetAlertaSonora(u8Value)` and `rte.vSetAlertaVizuala(u8Value)` (values outside [0,1] ignored) calling IOC; `sdc` packet encode/decode (compact binary, Meshtastic position packet ≤ 12 bytes) with HMAC-SHA256 truncated signature, timestamp and sequence number, reject replays; `sched` using `TIM` for 1 s and 60 s periodic tasks plus alert expiry; `app` modules POS (simulated route from a JSON file, 1 Hz), ACC (impact/hard-braking detection from |a| threshold with debounce), NBR (neighbour list with direction/radius relevance filter), RPT (60 s report builder). `app` must only import `rte`. Add one test module per layer in `tests/` and a test that enforces the import rules. Run all tests.

### Phase 2 – State service and API
> In `web/`, add a thread-safe `StateService` that runs the scheduler in a background thread (started once, not under the Django autoreloader) and exposes the JSON document from section 4.5. Add `GET /api/state/`, `GET /api/stream/` (SSE), and the POST actions with CSRF handling and auto-off timers. Add a `SimulatedFleet` that creates 2–3 neighbour vehicles driving along the route so the UI has data without hardware. Write view tests for every endpoint, including: invalid JSON, `duration_ms` above the limit, hardware actions refused when not allowed.

### Phase 3 – Driver dashboard UI
> Implement `/` exactly as in section 4.2 using only local static files: `base.html`, `static/web/css/app.css` (variables, dark/light themes), `static/web/js/state.js` (EventSource with polling fallback, reconnect with backoff, "no data" state), `radar.js` (SVG radar), `alert.js` (overlay). Romanian UI text with diacritics. Make it usable at 800×480 with no scrolling. Add a "Simulează impact" button visible only in simulation mode to demo the alert. Provide screenshots or a short manual test checklist in `docs/ui_checklist.md`.

### Phase 4 – Diagnostics page
> Implement `/diagnostics/` as in section 4.3: pin table with live levels, test buttons with auto-off, emergency off, live accelerometer canvas chart (30 s window), self-test with log, link status, event log. No chart libraries.

### Phase 5 – Operator page
> Implement `/operator/` as in section 4.4 with locally vendored Leaflet and an offline SVG fallback, alert list with acknowledge, vehicle table with age colouring. Vehicles come from the simulated LoRa reports in simulation mode.

### Phase 6 – Documentation and traceability
> Update `README.md` (run on PC, run on Pi 4/Pi 5, env variables, wiring). Create `docs/wiring.md` with a Mermaid wiring diagram and a pin table, `docs/api.md`, `docs/requirements_trace.md` (table CF1–CF10 and CNF1–CNF8 → module → test), and `docs/hazards.md` (false alarm, missed alarm, delayed alarm, spoofed alarm → mitigation). Keep Romanian text with correct diacritics where the lab documents are Romanian.

## 6. Definition of done (each phase)

- `python -m mcd.test` and `python manage.py test` both pass on a PC in simulation.
- On the Pi: `MCD_SIMULATE=0 MCD_HW_TESTS=1 python -m mcd.test HardwareSmokeTest` passes with the real wiring.
- No new runtime dependency without adding it to the right requirements file.
- No file imports upward across layers.
- Dashboard readable at 800×480, alert visible within 500 ms of the event in simulation.
- A short summary of what changed and how to run it.

## 7. What you (the student) still need

Hardware: Raspberry Pi 4 (or 5) + good PSU, MPU6050 board, **active** buzzer, NPN transistor (2N2222/BC547), 1 kΩ resistor, 1N4148/1N4007 diode, LED + 330 Ω, breadboard and jumper wires, XBee3 Zigbee + USB adapter (ideally two for a real neighbour link), 1–2 ESP Meshtastic boards, powered USB hub, 7" display (or just a browser on a laptop while developing).
Software (all free): VS Code + Copilot, Python 3.11+, Git, Django 5, `lgpio`, `smbus2`, `pyserial`, `meshtastic` (Python library), Chromium for kiosk mode, Leaflet (vendored).
