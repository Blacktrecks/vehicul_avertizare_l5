# Copilot instructions v2 – Hybrid vehicle warning system (Raspberry Pi 4/5, Django)

> How to use this file
> 1. Save it as `.github/copilot-instructions.md` (Copilot reads it automatically) AND keep a copy in the repo root as `COPILOT_INSTRUCTIONS.md`.
> 2. In VS Code open Copilot Chat in **Agent mode** and paste ONE phase prompt at a time (section 8). Run the tests after every phase, commit, then continue.
> 3. Never ask Copilot to "do everything". Small phases = fewer broken files.
> 4. If a phase fails twice, stop, `git diff`, and paste only the failing test output back to Copilot.

---

## 1. Project context

University project (course "Proiectarea sistemelor încorporate"), team: Roman Petrica, Ghidoarca Petru Cristi. V-model documentation.
Each vehicle node sees nearby vehicles over **Zigbee** (XBee3) and reports its position over **LoRa Meshtastic** to a control centre. On impact or hard braking the nearby drivers get an alert (visual + sound). **Warning only – the system never controls brakes or engine.**

- Hardware: Raspberry Pi 4 (development/validation, hostname `Pi4Master`) and Pi 5 (target), 7" touch display, MPU6050 (I2C), buzzer on GPIO17 via NPN, LED on GPIO27 (330 Ω). **No GPS**: position comes from a configured/simulated route.
- **Meshtastic boards available (3, stock Meshtastic firmware, no custom firmware):** Heltec e-ink board, Seeed XIAO (LoRa), second Heltec. They are used as: (a) the Pi's own LoRa modem, (b) simulated remote vehicles V2/V3 that send position/alert packets, (c) optionally the control-centre receiver. Boards connect to the Pi by **USB serial** (`/dev/ttyACM*` / `/dev/ttyUSB*`, prefer `/dev/serial/by-id/*`) or by **WiFi/TCP** (port 4403).
- Zigbee: XBee3 on `/dev/ttyUSB0` @ 9600 if present. If no XBee is available, Zigbee runs in **simulation** and the docs must say so honestly.
- Architecture follows AUTOSAR layering (lab L3): `APP (POS, ACC, NBR, HMI, RPT) → RTE → IOC / SDC / SCHED → MCD (PCS, I2C, USB, TIM)`. APP talks to the platform only through RTE.
- Current state: MCD (L4) done and tested (`mcd/pcs.py, i2c.py, mpu6050.py, usb.py, tim.py, config.py, test.py`). Django serves a basic page with dummy dashboard data (`mcd/views.py`). Everything above MCD is missing.
- Meshtastic is **not** LoRaWAN (no gateway, no ChirpStack). Write "LoRa Meshtastic" everywhere.

## 2. Hard rules (never break)

1. Keep existing MCD function names/signatures (`PCS_vSetOutputGpio`, `I2C_u8ReadReg`, `USB_u16Write`, `TIM_bHasElapsed`, …). You may add functions, never rename.
2. Everything must work **without hardware** (`MCD_SIMULATE=auto|1|0`) so the project runs on a PC.
3. Invalid parameters are ignored or raise exactly what current tests expect. Do not weaken tests; add new ones.
4. Hardware access: polling, one hardware thread, locks around drivers (web server is multi-threaded). Meshtastic/serial/TCP calls run in **worker threads**, never inside a request handler.
5. Every endpoint that actuates hardware or a device: POST only, CSRF-protected or LAN-restricted, **auto-off timeout** (max 5 s for manual buzzer/LED), refused when mode is not allowed. Destructive device actions (factory reset, reboot, region/channel change) need an explicit `confirm=true` and are logged.
6. UI text in **Romanian with correct diacritics** (ă â î ș ț). Code, identifiers, comments, commits in English.
7. Free/open-source only, no sign-ups, **no runtime CDN** (Pi may be offline). Vendor JS/CSS in `static/web/vendor/` with the license file next to it.
8. Python 3.11+, Django `>=5.0,<6.0`, **no database** (`DATABASES = {}`). Persistence = JSON/JSONL files under `data/` and `logs/` (git-ignored).
9. Security: `DEBUG` off unless `DJANGO_DEBUG=1`; `ALLOWED_HOSTS` and `SECRET_KEY` from env. **HMAC key and Meshtastic channel PSK are secrets**: load from env or `data/secrets.json` (git-ignored), never log them, never put them in templates or API responses.
10. GPIO chip: do not hardcode order. Detect the header chip by label (`pinctrl-rp1` Pi 5, `pinctrl-bcm2711` Pi 4) – use the chip **number found**, not a constant – via `lgpio.gpio_get_chip_info()` or `/dev/gpiochip*` probing; allow override `MCD_GPIOCHIP`.
11. Uploaded test files are **declarative data (JSON)**, validated against a schema, size-limited (64 KB). Never `exec`/`eval`/import uploaded content.
12. The app never flashes firmware. Firmware flashing is done outside (browser flasher, see `docs/ghid_dispozitive.md`). The app only reads info and applies a **project profile** (region, role, name, channel) with preview + confirmation.
13. Serial ports are exclusive: only one owner per port. The device manager must detect "port busy" and show a Romanian hint ("Închide Meshtastic Web / CLI care folosește portul").

## 3. Target structure

```
vehicul_avertizare/
├─ manage.py
├─ vehicul/                  # Django project
├─ mcd/                      # DONE – drivers
├─ ioc/                      # IOC_vSetOutputPort, accelerometer conditioning
├─ sdc/                      # packets, HMAC, seq/replay, framing
│  ├─ packets.py             # encode/decode, signature, replay window
│  ├─ transport.py           # abstract Transport: open/close/send/poll/info
│  ├─ transport_serial.py    # Meshtastic over USB serial
│  ├─ transport_tcp.py       # Meshtastic over WiFi (TCP 4403)
│  ├─ transport_sim.py       # fully simulated device (for PC + CI)
│  ├─ meshtastic_link.py     # wraps `meshtastic` python lib, pubsub -> queue
│  ├─ zigbee_link.py         # XBee API frames (or simulated)
│  ├─ registry.py            # device registry (data/devices.json)
│  └─ profile.py             # project profile + diff/apply
├─ sched/                    # 1 s / 60 s tasks, alert expiry
├─ rte/                      # only interface for APP
├─ app/                      # POS, ACC, NBR, HMI logic, RPT, stats (no hardware imports!)
├─ sim/                      # SimulatedFleet, scenarios, fault injection
├─ testkit/                  # device test runner, uploaded-scenario validation, reports
├─ web/                      # Django app: views, urls, templates, static
│  ├─ templates/web/         # base.html + one template per page
│  └─ static/web/            # css/, js/, vendor/
├─ scenarios/                # example JSON scenarios and test plans
├─ data/  logs/              # runtime, git-ignored
├─ docs/                     # see section 9
├─ tests/                    # one test module per layer
└─ README.md
```

Dependency rule: `web → rte → ioc/sdc/sched → mcd`. `app` imports only `rte`. `sim` and `testkit` may import `sdc` and `rte`. Nothing imports upward. A test must fail if `app` imports `mcd`, `sdc` or `ioc`.

## 4. Design system ("Neon Night": black / green / purple)

One CSS file `static/web/css/app.css`, CSS variables, system font stack (no downloads), 8 px grid.

```css
:root {                       /* dark = default */
  --bg:#07070b;  --bg-2:#0d0d15; --surface:#12121c; --surface-2:#1a1a28; --border:#26263a;
  --text:#ecebf5; --text-dim:#9a98b5;
  --green:#39ff88; --green-dim:#1fbf6a;      /* primary: OK, active, main buttons */
  --purple:#a855f7; --purple-dim:#7c3aed;    /* secondary: links, charts, selection, simulation */
  --amber:#ffb020; --red:#ff3b5c;            /* warning / fault / alert */
  --radius:14px; --glow:0 0 0 1px var(--green-dim), 0 0 16px rgba(57,255,136,.25);
}
:root[data-theme="light"] { --bg:#f6f5fb; --surface:#fff; --text:#14131f; --green:#0a8f4a; --purple:#6d28d9; /* keep contrast ≥ 4.5:1 */ }
```

- Green = healthy/primary action. Purple = simulation, selection, secondary data series. Amber/red only for degraded/fault/alert. Never colour alone: always icon + text.
- Cards with subtle border and glow on focus/active, big numbers, monospace for logs/IDs. Thin neon-green top bar on the active nav item.
- Light animation (CSS transforms only), `prefers-reduced-motion` respected, alert flash ≤ 3 Hz.
- A purple **"SIMULARE"** badge is shown in the top bar whenever any driver/device is simulated. A green **"HARDWARE"** badge when all real.
- Touch: targets ≥ 48 px (≥ 64 px for critical), text ≥ 16 px (alert ≥ 32 px). Dashboard never scrolls at 800×480. Other pages scroll normally.
- Intuitiveness rules: one primary action per card; empty states with a call-to-action ("Nu ai niciun dispozitiv. Adaugă unul →"); toasts for results; confirm dialogs for risky actions; inline help `?` tooltips (tap-friendly); a **"Pași de pornire"** checklist on the home page (hardware detectat, dispozitive conectate, test rulat, simulare pornită) with green ticks.

## 5. Pages

Navigation: left sidebar on desktop, bottom tab bar on the 7" kiosk, hidden long-press menu in kiosk mode. All pages extend `base.html`. Top bar (always): status chips for Zigbee, LoRa Meshtastic, MPU6050, buzzer/LED, clock, SIMULARE/HARDWARE badge, "Oprește tot" emergency-off button.

| URL | Name | Purpose |
| --- | --- | --- |
| `/` | Șofer | Driver dashboard (kiosk): radar, speed, heading, alert overlay, "Pași de pornire" when idle |
| `/devices/` | Dispozitive | Device manager (section 6) |
| `/simulator/` | Simulare | Simulation lab (section 7) |
| `/tests/` | Teste | Test centre: component tests, uploaded scenarios, reports (section 7.4) |
| `/stats/` | Statistici | Charts and statistics (section 7.5) |
| `/logs/` | Loguri | Live logs, filters, export (section 7.6) |
| `/diagnostics/` | Diagnoză | Pin table, live accelerometer, buzzer/LED test, self-test |
| `/operator/` | Centru | Control-centre map, vehicles from LoRa reports, alert list |

### 5.1 Driver dashboard (`/`)
- Centre: SVG radar (no libs) with rings 25/50/100 m (auto-scale), ego in the centre, neighbours as arrows rotated by heading, colour: grey = irrelevant, white = relevant, red = in alert. Tap a vehicle → side card (ID, distance, bearing, speed, last seen, source Zigbee/LoRa).
- Left/right: big speed, heading + compass letter, neighbour count.
- **Alert overlay**: banner over the top half, flashing red/amber, text ≥ 32 px (e.g. "ATENȚIE: IMPACT ÎN FAȚĂ – 42 m"), source ID, countdown, **"Confirmă"** button ≥ 64 px high, contrast ≥ 7:1. Buzzer/LED state mirrored on screen.
- Day/night toggle (dark default).

### 5.2 Diagnostics
Pin table from `PIN_TABLE` with live levels; "Test buzzer 1 s", "Test LED 1 s" (POST `duration_ms` ≤ 5000); live accelerometer canvas chart (ax, ay, az, |a|, 30 s, 200 ms refresh, threshold line); "Simulează impact" (simulation only); self-test with pass/fail + expandable log.

### 5.3 Operator
Leaflet vendored locally (OSM tiles online) + **offline SVG fallback** with scale bar; alert list with acknowledge; vehicle table with age colouring (amber > 90 s, red > 180 s).

## 6. Device manager (`/devices/`)

Goal: add, connect, configure, test and monitor Meshtastic devices (and Zigbee) from the browser, similar in spirit to the Meshtastic flasher/web client, but integrated in the app.

### 6.1 Add device (wizard, 3 steps)
1. **Alege conexiunea**: `USB serial` | `WiFi (TCP)` | `Simulat`.
2. **Detectare**: for USB, `serial.tools.list_ports` scan button listing port, VID:PID, description, a guess of the board (Heltec / XIAO / ESP32-S3 / CP210x / CH340 / native USB), and `by-id` path; "port ocupat" detection. For WiFi: host/IP + port (default 4403) + "Testează conexiunea". For simulated: pick a template.
3. **Rol și nume**: role = `Radio propriu (Pi)` | `Vehicul simulat V2` | `Vehicul simulat V3` | `Centru de control` | `Doar test`. Save in `data/devices.json` (id, label, transport, address, role, board guess, added_at).

### 6.2 Device card (one per device)
Status chip (conectat / deconectat / port ocupat / eroare), board model, firmware version, node ID (`!xxxxxxxx`), long/short name, region, modem preset, channel name (**never the PSK**), battery %, uptime, last RX time, last RSSI/SNR, packet counters, a mini sparkline for RSSI. Buttons: Conectează/Deconectează, Info, **Sincronizează profil**, **Trimite test**, **Rulează teste**, Loguri, Elimină.

### 6.3 Sync project profile ("Sincronizează")
Profile (`sdc/profile.py`, editable on page, stored in `data/profile.json`): region `EU_868`, modem preset (default `LONG_FAST`), project channel name `VEH`, PSK (generated once, stored in `data/secrets.json`), role-specific short names (`V1`, `V2`, `V3`, `CTR`), position broadcast interval, GPS disabled / fixed position from route. Flow: read current config → **show diff table** (field, now, target) → user ticks fields → `confirm` → apply through the `meshtastic` library → verify by re-reading → log result. Changing region/channel may reboot the device: show a Romanian warning and wait for reconnect.
Also: "Verifică compatibilitate" – checks that all connected devices share region, preset and channel name, and shows a green/red matrix.

### 6.4 Messaging between devices
- **Test message** modal: from device A to device B (or broadcast), type `text` or `pachet proiect` (binary private-app packet signed with HMAC, see `docs/packet_format.md`), count, interval.
- Live **conversation view**: TX/RX bubbles with time, from/to, hop count, RSSI, SNR, size, decoded fields, signature OK/FAIL, replay/seq status.
- **Loopback test** (A→B within N s) shows RTT, delivery %, RSSI/SNR.
- Zigbee: same card type with XBee info (address, PAN, signal) and send/receive frame test; simulated if no XBee.

### 6.5 Backend contract
`sdc.transport.Transport` (abstract): `open()`, `close()`, `is_open()`, `info() -> dict`, `send_text(dest, text)`, `send_packet(dest, bytes, portnum=256)`, `poll() -> list[Event]`, `get_config()`, `apply_config(diff)`. Implementations: serial, TCP, simulated. `meshtastic_link` uses `meshtastic.serial_interface.SerialInterface` / `meshtastic.tcp_interface.TCPInterface` and `pubsub` (`meshtastic.receive`, `meshtastic.connection.lost`) and pushes events into a thread-safe queue; reconnect with exponential backoff. If the `meshtastic` package is missing, the simulated transport is used and the UI shows it. Every TX/RX/connect/error becomes a structured log event (section 7.6).

## 7. Simulation, tests, statistics, logs

### 7.1 Modes
`virtual` (all software; no hardware), `hybrid` (real boards act as vehicles V2/V3 and send simulated-route packets over LoRa; Pi receives through its own board), `hardware` (real sensors/links only). The mode is visible in the top bar and in every report.

### 7.2 Simulation lab (`/simulator/`)
- Scenario selector (JSON files in `scenarios/`) + editor form: number of vehicles (1–5), route file, speeds, start offsets, packet loss %, added latency, link drop windows.
- Controls: ▶ start, ⏸ pause, ⏹ stop, speed ×1/×2/×5, timeline scrubber, event markers.
- Events to inject by button or by scenario time: **impact**, **hard braking**, **spoofed packet** (bad HMAC), **replayed packet** (old seq), **out-of-order**, **link loss**, **sensor fault**.
- Result panel: alert shown in X ms (requirement < 500 ms), correct vehicles alerted, spoofed/replayed rejected ✓/✗, false alarms count.
- Hybrid mode: assign a scenario vehicle to a real device (V2 → XIAO, V3 → Heltec); packets are sent over the real radio; show side by side "trimis" vs "primit".
- Map: offline SVG of the route with moving vehicles and scale bar.

### 7.3 SimulatedFleet
2–3 neighbour vehicles driving the route with realistic noise, producing Zigbee-style neighbour updates and LoRa-style reports through the same `sdc` packet code as real devices (so the same parser/validator is exercised).

### 7.4 Test centre (`/tests/`)
- **Catalogue** of component tests with status badges: GPIO/buzzer, LED, MPU6050 (WHO_AM_I, noise, 1 g check), USB ports, Zigbee link, Meshtastic link (per device), HMAC/replay, scheduler timing, alert chain RTE→IOC→PCS, end-to-end alert latency.
- Run one / run all / run selected on a device; live progress and a log pane; pass/fail/skip with reason (e.g. "Skip: no hardware").
- **Upload test scenario** (`.json`): drag-and-drop, schema validation with clear Romanian errors, preview of steps, "Rulează". Format example:
```json
{"v":1,"name":"Loopback V2→CTR","target_roles":["Vehicul simulat V2","Centru de control"],
 "steps":[
  {"op":"connect","device":"V2"},
  {"op":"send_packet","from":"V2","to":"CTR","kind":"position","count":20,"interval_s":5},
  {"op":"expect_rx","device":"CTR","within_s":15,"min_count":18,"signature":"ok"},
  {"op":"assert","metric":"delivery_pct","gte":90}]}
```
Allowed ops are a fixed whitelist (`connect, disconnect, send_text, send_packet, expect_rx, wait, inject, assert`).
- **Reports**: each run saves `data/reports/<timestamp>.json`; export as JSON, CSV and a printable HTML page (header: date, mode, devices, firmware, pass/fail table, charts, raw log excerpt). These are deliverables for the final report.

### 7.5 Statistics and charts (`/stats/`)
Vendored **Chart.js** (MIT) or plain canvas. Time-range selector (5 min / 1 h / session), CSV export per chart.
Charts: accelerometer |a| with impact threshold; RSSI and SNR per device over time; packets TX/RX per minute per link; **delivery ratio (PDR %)**; latency histogram + min/avg/p95; alert-to-display latency per alert; neighbour count over time; link uptime timeline; alerts by type.
KPI cards: alerts total, false alarms, rejected spoofed/replayed, average latency, PDR, duty-cycle estimate (airtime used vs 1 % limit for EU868), session length.
Data comes from in-memory ring buffers in `app/stats.py` plus `logs/*.jsonl`; no database.

### 7.6 Logs (`/logs/`)
Structured events: `{ts, level, source, device, kind, msg, data}`. Sources: app, sched, mcd, zigbee, meshtastic:<device>, sim, test. Live tail over SSE (`/api/logs/stream/`), filters (level, source, device, text), pause/resume, auto-scroll toggle, **raw/decoded** toggle for packets (hex dump + parsed fields), copy line, export (JSONL/CSV), clear view (not the file). Files rotate (5 × 2 MB) under `logs/`. Secrets are redacted.

## 8. Phase prompts (paste ONE at a time, Agent mode)

### Phase 0 – Cleanup and safety
> Read `.github/copilot-instructions.md`. Do not rename any MCD function. (1) In `mcd/pcs.py`, fix `_resolve_gpiochip`: it currently returns constants from `label_map` (4/4/0) and reads `/sys/class/gpio/*/label`; instead probe each `/dev/gpiochipN` (e.g. `lgpio.gpiochip_open` + `lgpio.gpio_get_chip_info`) and return the **number of the chip whose label is `pinctrl-rp1` or `pinctrl-bcm2711`**; keep `MCD_GPIOCHIP` override; keep simulation fallback only for `MCD_SIMULATE=auto`. (2) Add mocked tests for Pi 4 layout, Pi 5 layout (both old and new numbering) and override. (3) Add `.venv/`, `data/`, `logs/`, `*.pyc` to `.gitignore`. (4) Run `python -m mcd.test` and `python manage.py test` and show results. No UI changes.

### Phase 1 – Layers above MCD (no UI)
> Create `ioc`, `sdc`, `sched`, `rte`, `app` per section 3. `IOC_vSetOutputPort` with `IOC_CH_BUZZER=0x0001`→GPIO17, `IOC_CH_LED=0x0002`→GPIO27 (unknown channel ignored). `rte.vSetAlertaSonora/vSetAlertaVizuala` (values outside [0,1] ignored). `sdc/packets.py`: compact binary position packet (target ≈12–16 bytes, document the byte layout and the trade-off in `docs/packet_format.md`) with truncated HMAC-SHA256, timestamp, sequence number, replay window; alert packet type. `sched` with `TIM` for 1 s / 60 s tasks and alert expiry. `app`: POS (route from JSON, 1 Hz), ACC (impact/hard-braking from |a| threshold with debounce), NBR (relevance filter by direction and radius), RPT (60 s report). `app` imports only `rte`. One test module per layer + an import-rule test. Run all tests.

### Phase 2 – State service and API
> In `web/` add a thread-safe `StateService` running the scheduler in one background thread (not under the autoreloader). Expose JSON v2 (section 10) at `GET /api/state/` and SSE `GET /api/stream/`, and POST actions with CSRF and auto-off timers. Add `sim/SimulatedFleet`. Replace the dummy data in `mcd/views.py` usage with the real service (keep old URLs working). View tests for every endpoint including invalid JSON, `duration_ms` above limit, action refused when not allowed.

### Phase 3 – Design system + driver dashboard
> Implement the "Neon Night" design system (section 4) in `static/web/css/app.css`, `base.html` (top bar, sidebar/tab bar, theme toggle, emergency-off, toasts, confirm dialog) and the driver dashboard `/` (section 5.1) with `state.js` (EventSource + polling fallback + backoff + "no data" state), `radar.js`, `alert.js`. Romanian text with diacritics. Usable at 800×480 with no scrolling. Include the "Pași de pornire" checklist. Write `docs/ui_checklist.md`.

### Phase 4 – Device transports and registry (backend only)
> Implement `sdc/transport*.py`, `meshtastic_link.py`, `zigbee_link.py`, `registry.py`, `profile.py` as in section 6.5. Simulated transport must pass the same contract tests as real ones (use mocks for serial/TCP/`meshtastic`). Add endpoints: `GET/POST /api/devices/`, `DELETE /api/devices/<id>/`, `GET /api/devices/scan/`, `POST /api/devices/<id>/connect|disconnect|apply-profile|send-test`, `GET /api/devices/<id>/info`, with the safety rules from section 2. Structured logging to `logs/`. Tests for: port busy, lost connection and reconnect, bad profile, diff computation, redaction of secrets.

### Phase 5 – Devices page
> Implement `/devices/` per section 6 using only local static files: add-device wizard, device cards, sync-profile diff dialog, compatibility matrix, test-message modal, conversation view. Romanian text, empty states, toasts, confirm dialogs. Works fully with simulated devices on a PC.

### Phase 6 – Simulation lab
> Implement `sim/` scenarios + fault injection and `/simulator/` per section 7.2, including hybrid mode (scenario vehicle bound to a real device) and the result panel with measured alert latency. Add 3 example scenarios in `scenarios/` (convoy, impact ahead, spoofed+replay attack).

### Phase 7 – Test centre
> Implement `testkit/` and `/tests/` per section 7.4: catalogue, runner with live progress, scenario upload with schema validation and whitelist ops, report saving and export (JSON, CSV, printable HTML). Tests for validation errors and for refusing unknown ops.

### Phase 8 – Statistics and logs
> Implement `app/stats.py`, `/stats/` and `/logs/` per sections 7.5 and 7.6 (vendored Chart.js with license, CSV/JSONL export, SSE log stream, rotation, redaction).

### Phase 9 – Diagnostics and operator
> Implement `/diagnostics/` (5.2) and `/operator/` (5.3) in the same design system, with simulated LoRa reports in simulation mode.

### Phase 10 – Documentation and traceability
> Update `README.md` (PC run, Pi 4/Pi 5 run, env variables, wiring, device setup). Create/refresh `docs/wiring.md` (Mermaid + pin table), `docs/api.md`, `docs/packet_format.md`, `docs/requirements_trace.md` (CF1–CF10, CNF1–CNF8 → module → test), `docs/hazards.md` (false/missed/delayed/spoofed alarm → mitigation), `docs/ghid_dispozitive.md`, `docs/test_plan.md`. Romanian where the lab documents are Romanian.

## 9. Documents expected in `docs/` (V-model deliverables)

`requirements_trace.md`, `hazards.md`, `architecture.md` (AUTOSAR diagram from L3 + component diagram), `packet_format.md`, `wiring.md`, `tabel_pini.md`, `api.md`, `test_plan.md`, `ui_checklist.md`, `ghid_dispozitive.md`, plus exported test reports (`data/reports/`) copied to `docs/reports/` for submission.

## 10. API – state JSON v2 (keep stable, document in `docs/api.md`)

```json
{
  "v": 2, "ts": 1730000000.0, "mode": "virtual|hybrid|hardware",
  "ego": {"id":"V1","lat":47.15,"lon":27.59,"speed_kmh":42,"heading_deg":90},
  "neighbours": [{"id":"V2","source":"zigbee|lora","lat":47.1502,"lon":27.5903,"speed_kmh":40,"heading_deg":88,
                  "distance_m":31,"bearing_deg":85,"relevant":true,"age_s":0.8}],
  "alert": {"active":false,"type":null,"source":null,"distance_m":null,"expires_in_s":null},
  "outputs": {"buzzer":0,"led":0},
  "accel": {"ax":0.0,"ay":0.0,"az":1.0,"mag":1.0,"threshold":2.5},
  "links": {"zigbee":{"state":"ok|degraded|fault|sim","last_rx_s":0.4,"rx":120,"tx":120,"err":0},
            "meshtastic":{"state":"ok","last_rx_s":12.0,"rx":4,"tx":4,"err":0}},
  "devices": [{"id":"d1","label":"XIAO","role":"V2","state":"connected","transport":"serial|tcp|sim",
               "rssi":-71,"snr":8.5,"battery":87,"last_rx_s":3.1,"rx":10,"tx":10}],
  "stats": {"pdr_pct":96.0,"latency_ms":{"min":210,"avg":480,"p95":900},"alerts":3,"false_alarms":0,"rejected":2},
  "drivers": {"gpio":"simulated","i2c":"simulated","usb_zigbee":"simulated","usb_meshtastic":"simulated"}
}
```
POST (JSON): `/api/outputs/`, `/api/outputs/off/`, `/api/alert/ack/`, `/api/sim/start|pause|stop|inject/`, `/api/selftest/`, `/api/tests/run/`, `/api/tests/upload/`. GET: `/api/logs/`, `/api/logs/stream/`, `/api/stats/`, `/api/tests/`, `/api/tests/report/<id>/`.

## 11. Definition of done (each phase)

- `python -m mcd.test` and `python manage.py test` pass on a PC in simulation.
- On the Pi: `MCD_SIMULATE=0 MCD_HW_TESTS=1 python -m mcd.test HardwareSmokeTest` passes with the real wiring.
- No new runtime dependency without adding it to the right requirements file (`meshtastic`, `pyserial` go in `requirements-pi.txt`; the app must still start without them).
- No upward imports across layers.
- Dashboard readable at 800×480; alert visible within 500 ms of the event in simulation.
- A short summary of what changed and how to run it.

## 12. What the student still needs

Hardware: Raspberry Pi 4 + good PSU, MPU6050, **active** buzzer, NPN (2N2222/BC547), 1 kΩ, 1N4148/1N4007, LED + 330 Ω, breadboard/jumpers, 3 Meshtastic boards (Heltec e-ink, XIAO, Heltec) + USB cables, powered USB hub, 7" display (or a laptop browser), XBee3 + USB adapter only if available.
Software (all free): VS Code + Copilot, Python 3.11+, Git, Django 5, `lgpio`, `smbus2`, `pyserial`, `meshtastic`, Chromium (kiosk), Chart.js and Leaflet vendored.
