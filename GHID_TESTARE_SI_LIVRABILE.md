# Ghid: încărcare pe Pi 4, testarea plăcilor Meshtastic și livrabile

Proiect: Sistem hibrid de avertizare a vehiculelor (Zigbee + LoRa Meshtastic). Echipa: Roman Petrica, Ghidoarca Petru Cristi.

---

## 1. Ce încarci pe Pi 4

### 1.1 Ce intră și ce NU intră în arhivă
Arhiva `vehicul_avertizare_l5.zip` conține și `.venv/` (mediul virtual de pe PC). **Nu îl urca pe Pi**: este specific sistemului de operare de pe PC și nu va funcționa pe Raspberry Pi OS.

| Încarci | NU încarci |
| --- | --- |
| `manage.py`, `vehicul/`, `mcd/` | `.venv/` |
| `requirements.txt`, `requirements-pi.txt` | `__pycache__/`, `*.pyc` |
| `docs/`, `README.md`, `COPILOT_INSTRUCTIONS.md` | `docs_lab/` (PDF-urile de laborator, nu sunt necesare pe Pi) |
| Pe parcurs: `ioc/ sdc/ sched/ rte/ app/ sim/ testkit/ web/ scenarios/ tests/` | `data/`, `logs/` (se creează pe Pi) |

### 1.2 Varianta recomandată: Git
Pe PC, în folderul proiectului:
```bash
git init
git add .
git commit -m "Initial commit"
# creează un repo gol pe GitHub (gratuit), apoi:
git remote add origin <URL-ul-repo-ului>
git push -u origin main
```
Pe Pi 4:
```bash
git clone <URL-ul-repo-ului> vehicul_avertizare
cd vehicul_avertizare
```
La fiecare fază nouă: `git push` pe PC, `git pull` pe Pi.

### 1.3 Varianta rapidă: rsync/scp (fără Git)
Din folderul proiectului, pe PC (hostname-ul și utilizatorul tău de pe Pi):
```bash
rsync -av --exclude '.venv' --exclude '__pycache__' --exclude 'docs_lab' --exclude 'data' --exclude 'logs' ./ pi4@Pi4Master.local:~/vehicul_avertizare/
```
Pe Windows, dacă nu ai `rsync`: `scp -r` după ce ștergi `.venv`, sau WinSCP (gratuit).

### 1.4 Pregătirea Pi-ului (o singură dată)
```bash
sudo apt update && sudo apt install -y python3-venv python3-dev git
sudo raspi-config                # Interface Options -> I2C -> Enable
sudo usermod -aG dialout,i2c,gpio pi4   # acces la porturi seriale, I2C, GPIO
sudo reboot
```
După repornire:
```bash
cd ~/vehicul_avertizare
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-pi.txt
pip install meshtastic            # când ajungi la fazele cu dispozitive
```

### 1.5 Primele verificări pe Pi
```bash
python -m mcd.test
python manage.py test
MCD_SIMULATE=0 MCD_HW_TESTS=1 python -m mcd.test HardwareSmokeTest   # cu cablajul real
DJANGO_ALLOWED_HOSTS='*' python manage.py runserver 0.0.0.0:8000
```
Deschide `http://Pi4Master.local:8000/` din laptop (același WiFi). Pe ecranul de 7": Chromium în mod kiosk.

### 1.6 Simulare vs hardware real

Proiectul este conceput pentru a funcționa în două moduri distincte:

- `MCD_SIMULATE=1` -> forțează simularea completă; potrivit pentru dezvoltare, demo, dashboard și validare logică fără dispozitive fizice.
- `MCD_SIMULATE=0` -> forțează modulul hardware; aplicația încearcă să folosească GPIO, I2C, porturi seriale și noduri Meshtastic/Zigbee reale.
- `MCD_SIMULATE=auto` sau variabila necompletată -> se folosește hardware dacă este disponibil, altfel se activează simularea.

Comenzile rapide:

```bash
# SIMULARE
MCD_SIMULATE=1 python manage.py runserver 0.0.0.0:8000

# HARDWARE REAL
MCD_SIMULATE=0 python manage.py runserver 0.0.0.0:8000

# VERIFICARE PORTURI
ls /dev/ttyUSB*
ls /dev/ttyACM*

# VERIFICARE MESHSTASTIC
meshtastic --port /dev/ttyACM0 --info
```

Important: conectarea fizică a unui dispozitiv nu este suficientă. Sistemul funcționează numai dacă:

- portul USB este detectat corect de Linux
- dispozitivul este configurat cu aceeași regiune, canal și cheie pe toate nodurile Meshtastic
- aplicația rulează în mod hardware, nu în simulare
- permisiunile de acces la portul serial sunt corecte

### 1.7 Cum adaugi un dispozitiv Meshtastic Heltec V3

Dacă ai un Heltec V3 (sau orice altă plăcuță Meshtastic), nu trebuie să schimbi codul aplicației ca să-l vezi. Procedura este:

1. Flash-ează firmware Meshtastic stabil din Web Flasher sau din `meshtastic` CLI.
2. Conectează placa la Pi prin USB serial sau prin WiFi/TCP.
3. Verifică portul:
   ```bash
   ls /dev/ttyACM*
   ls /dev/serial/by-id/
   ```
4. Rulează:
   ```bash
   meshtastic --port /dev/ttyACM0 --info
   ```
   sau, dacă este WiFi:
   ```bash
   meshtastic --host 192.168.1.50 --info
   ```
5. Setează aceeași regiune, presetul și canal pe toate dispozitivele (`EU_868`, același canal/PSK).
6. Repornește dispozitivul dacă ai schimbat profilul.
7. În interfața aplicației, placa va apărea ca nod Meshtastic. Dacă folosești USB, apare ca port serial (`/dev/ttyACM*` sau `/dev/ttyUSB*`). Dacă folosești WiFi, apare ca nod TCP la IP + port 4403.

Dacă nu ai încă portul, aplicația rămâne în simulare și indică clar acest lucru. Nu „îl inventează” ca real dacă nu există conexiunea activă.

### 1.8 Este Heltec V3 văzut?

Da, dacă este conectat fizic prin USB sau este accesibil pe rețea prin WiFi. Sistemul îl recunoaște ca dispozitiv Meshtastic dacă:

- portul este valid și disponibil;
- firmware-ul este Meshtastic (nu un USB generic sau altă aplicație);
- placa este respectiv conectată la aceeași rețea / canal / cheie;
- aplicația rulează în modul hardware (`MCD_SIMULATE=0`).

În cazul WiFi, nu este nevoie să fie legat la USB, ci doar să fie în aceeași LAN și accesibil prin TCP 4403.

### 1.9 Ce suportă aplicația

Aplicația suportă Meshtastic ca transport de comunicație între noduri. Nu este un gateway LoRaWAN și nu are nevoie de ChirpStack. În practică:

- USB serial: cel mai stabil și recomandat pentru dezvoltare și testare locală;
- WiFi/TCP: util pentru noduri Meshtastic care sunt pe aceeași rețea;
- simulare: utilizată când nu există hardware sau când vrei să testelezi logica de alertă fără echipament real.

Ghidul complet cu explicații detaliate, checklist și scenarii de testare este în `docs/testare_pi_simulare_hardware.md`.

### 1.7 Notă despre GPIO
În `mcd/pcs.py`, funcția `_resolve_gpiochip` întoarce constante (4 / 4 / 0) în loc de numărul chip-ului găsit. Acum merge doar datorită fallback-ului `[4, 0]`. Faza 0 din fișierul nou de instrucțiuni o corectează.

---

## 2. Cum folosești fișierul nou cu Copilot

1. Înlocuiește `COPILOT_INSTRUCTIONS.md` din proiect cu cel nou și copiază-l și ca `.github/copilot-instructions.md`.
2. VS Code → Copilot Chat → **Agent mode**.
3. Lipește **o singură fază** din secțiunea 8 a fișierului (începe cu Faza 0).
4. Rulează testele, fă commit, apoi treci la faza următoare.
5. Dacă ceva se strică de două ori la rând: `git diff` și trimite-i lui Copilot doar eroarea.

Prompt scurt de pornire (îl lipești o dată, înainte de Faza 0):
> Citește `.github/copilot-instructions.md` în întregime. Respectă regulile din secțiunea 2 și structura din secțiunea 3. Lucrează doar pe faza pe care ți-o dau, nu pe altele. După fiecare fază rulează `python -m mcd.test` și `python manage.py test` și arată-mi rezultatele, plus un rezumat scurt al fișierelor modificate.

---

## 3. Cele 3 plăci Meshtastic (Heltec e-ink, XIAO, al doilea Heltec)

### 3.1 Roluri propuse
| Placă | Rol |
| --- | --- |
| XIAO | Vehicul simulat V2 |
| Heltec #2 | Vehicul simulat V3 |
| Heltec e-ink | Radioul propriu al Pi-ului (conectat la Pi prin USB) sau centrul de control |

Poți schimba rolurile din pagina `/devices/`. Important: la toate trei trebuie să fie **aceeași regiune, același preset și același canal (cu aceeași cheie)**.

### 3.2 Pregătirea fiecărei plăci (o singură dată)
1. Flash firmware Meshtastic stabil cu **Meshtastic Web Flasher** (`flasher.meshtastic.org`): gratuit, fără cont, în Chrome/Edge (Web Serial). Alege modelul exact al plăcii.
2. Setează **regiunea `EU_868`** (obligatoriu în Europa).
3. Nume diferit pe fiecare placă (ex. `V1`, `V2`, `V3`).
4. Același canal și aceeași cheie (PSK) pe toate, diferite de canalul public implicit.
5. Închide pagina web a Meshtastic după configurare: portul serial poate fi folosit de **un singur program** odată.

### 3.3 Verificări rapide din terminal (pe Pi, cu venv activ)
```bash
ls /dev/serial/by-id/                     # vezi plăcile conectate
meshtastic --port /dev/ttyACM0 --info     # info nod, regiune, canal
meshtastic --port /dev/ttyACM0 --nodes    # noduri vecine
meshtastic --port /dev/ttyACM0 --sendtext "test V1"
```
Pentru WiFi (dacă placa are WiFi activat): `meshtastic --host <IP> --info`.

### 3.4 Plan de teste (completezi tabelul și îl anexezi la raport)

| ID | Test | Pași | Rezultat așteptat | Trecut / picat |
| --- | --- | --- | --- | --- |
| T01 | Conectare USB | Conectează placa, scanează în `/devices/` | Placa apare cu modelul corect | |
| T02 | Info dispozitiv | Buton „Info” | Firmware, ID nod, regiune EU_868 vizibile | |
| T03 | Compatibilitate | „Verifică compatibilitate” cu toate plăcile | Matrice verde (regiune, preset, canal) | |
| T04 | Mesaj text | V2 → Pi, text | Mesaj primit, RSSI/SNR afișate | |
| T05 | Pachet proiect semnat | V2 → Pi, „pachet proiect” | Primit, semnătură OK, secvență acceptată | |
| T06 | Semnătură falsă | Injectează pachet cu HMAC greșit | Respins, logat „FAIL” | |
| T07 | Retransmitere falsă | Retrimite un pachet vechi | Respins (replay), logat | |
| T08 | Pierderi de pachete | 100 de pachete, interval conform limitei de duty cycle | PDR ≥ 90 % în aceeași încăpere | |
| T09 | Latență | Loopback A→B | min / medie / p95 în raport | |
| T10 | Rază | Mută o placă la 10 / 50 / 100 m (afară) | Tabel distanță – RSSI – SNR – PDR | |
| T11 | Alertă cap-coadă | Simulează impact pe V2 (hibrid) | Alertă pe ecran < 500 ms, buzzer + LED pornesc și se opresc | |
| T12 | Pierdere conexiune | Scoate cablul USB | Stare „deconectat”, reconectare automată la reintroducere | |
| T13 | Hardware local | Test buzzer, LED, MPU6050 (WHO_AM_I, 1 g) | Toate trec | |
| T14 | Zigbee | Doar dacă ai XBee3; altfel rămâne simulat | Se documentează clar „simulat” sau „real” | |

Observații:
- Meshtastic aplică limite de timp de emisie în EU_868 (duty cycle 1 %). Un raport la 60 s este în regulă; nu trimite rafale lungi.
- Fă testele de rază afară și notează locul, ora și antena folosită.

### 3.5 Teste încărcate din aplicație
Pagina `/tests/` acceptă fișiere `.json` cu scenarii (doar pași declarativi, fără cod). Exemple vor fi în `scenarios/`. Fiecare rulare produce un raport (JSON, CSV, HTML printabil) pe care îl atașezi la livrabile.

---

## 4. Ce livrezi (după modelul în V din proiect)

| Etapă din modelul în V | Livrabil | Unde |
| --- | --- | --- |
| Cerințe | Tabel CF1–CF10 / CNF1–CNF8 (ex.: alertă < 500 ms până la 100 m, raport la 60 s, fără acționarea vehiculelor) | `docs/requirements_trace.md` |
| Analiza pericolelor | Alarmă falsă, ratată, întârziată, falsificată + măsuri | `docs/hazards.md` |
| Proiectare sistem | Arhitectura AUTOSAR (L3), formate de mesaje, alegerea radio-urilor | `docs/architecture.md`, `docs/packet_format.md` |
| Proiectare detaliată | Schemă electrică / cablaj, tabel pini (L4), module software, structura pachetului | `docs/wiring.md`, `docs/tabel_pini.md` |
| Implementare | Cod sursă curat, rulabil, cu README | arhiva proiectului (fără `.venv`) |
| Teste unitare | Codare/decodare pachete, verificare semnătură, prag impact, drivere MCD | `tests/`, `mcd/test.py` |
| Teste de integrare | Zigbee + LoRa pe același nod; placă → Pi; alertă cap-coadă | rapoarte din `/tests/` |
| Validare sistem | Rază, latență, pierderi, test de retransmitere falsă, comparație cu cerințele | `docs/reports/` + tabelul din secțiunea 3.4 |
| Raport final | Rezultate, limite (precizie poziție simulată, Zigbee real/simulat), concluzii | document final |

Pachetul final de predat:
1. Arhiva codului (fără `.venv`, `__pycache__`, `data/`, `logs/`).
2. Folderul `docs/` completat.
3. Rapoartele de test exportate (`docs/reports/`).
4. Capturi de ecran: dashboard, `/devices/`, `/simulator/`, `/stats/`, `/logs/`.
5. Un video scurt (1–2 min) cu demonstrația: impact simulat → alertă pe ecran + buzzer + LED, apoi mesaj între plăci.
6. Pozele cablajului real și lista componentelor.

Cinstit, în raport: spune ce a fost **real** și ce a fost **simulat** (poziția vine dintr-un traseu, nu din GPS; Zigbee e simulat dacă nu ai XBee; LoRa este Meshtastic, nu LoRaWAN).
