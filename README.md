# Sistem hibrid de avertizare a vehiculelor – L4 (drivere MCD, Django)

Rezolvarea cerințelor din L4, pe baza arhitecturii din L2 și L3 (Raspberry Pi 5, MPU6050, buzzer/LED, XBee3 Zigbee, modul Meshtastic).

| Cerință L4 | Unde este |
| --- | --- |
| 1. Codul pentru modulele proiectului | `mcd/pcs.py` (GPIO), `mcd/i2c.py` (+ `mcd/mpu6050.py`), `mcd/usb.py`, `mcd/tim.py`, `mcd/config.py` |
| 2. Fișier `test.py` care testează toate driverele | `mcd/test.py` |
| 3. Tabel cu descrierea și maparea pinilor | `docs/tabel_pini.md`, pagina `/` și `/api/pins/` (sursa: `PIN_TABLE` din `mcd/config.py`) |

## Drivere (nivelul MCD din L3)

| Fișier | Driver | Funcții principale |
| --- | --- | --- |
| `pcs.py` | GPIO (lgpio) | `PCS_vInit`, `PCS_vSetOutputGpio` (din L3: pin 0–27, valoare 0/1, parametri invalizi ignorați), `PCS_u8GetGpio`, `PCS_vConfigInput`, `PCS_vDeinit` |
| `i2c.py` | I2C (smbus2) | `I2C_vInit`, `I2C_u8ReadReg`, `I2C_vWriteReg`, `I2C_lReadBlock`, `I2C_vDeinit` |
| `mpu6050.py` | acces MPU6050 peste I2C | `MPU6050_vInit`, `MPU6050_tReadRaw`, `MPU6050_tReadG`, `MPU6050_fReadMagnitudeG` |
| `usb.py` | USB serial (pyserial) – XBee3 și Meshtastic | `USB_vOpen`, `USB_u16Write`, `USB_baRead`, `USB_u16Available`, `USB_vClose` |
| `tim.py` | temporizare prin polling pentru SCHED | `TIM_vStart` (1 s / 60 s / alertă), `TIM_bHasElapsed`, `TIM_u32GetMs`, `TIM_vDelayMs` |

Driverele nu depind de Django. Dacă lipsește hardware-ul sau biblioteca (de exemplu pe PC), rulează într-un mod de simulare (MPU6050 simulat, buffere USB în memorie), deci tot proiectul poate fi dezvoltat și testat în VS Code fără Raspberry Pi.
Modul se controlează cu variabila `MCD_SIMULATE`: `auto` (implicit), `1` (simulare forțată), `0` (hardware forțat).

IOC, SDC, RTE, SCHED și aplicația (POS, ACC, NBR, HMI, RPT) sunt straturile de deasupra și nu fac parte din L4.

## Rulare în Visual Studio Code

```bash
cd vehicul_avertizare
python -m venv .venv
# Windows: .venv\Scripts\activate      Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

python -m mcd.test          # doar driverele (fără Django)
python manage.py test       # drivere + stratul Django
python manage.py runserver  # http://127.0.0.1:8000/
```

În VS Code: **Run and Debug** are trei configurații (runserver, teste Django, `python -m mcd.test`).
Pagina `/` afișează un dashboard modern cu date dummy (vecini vehicul, nivel risc, trend accelerație), tabelul de pini, butonul de citire a accelerometrului (`/api/accel/`) și butonul de auto-test (`/api/selftest/`).

API-ul dashboard este disponibil la `/api/dashboard/` și livrează JSON pentru:
- vehiculul curent (viteză, heading, GPS),
- vecini din Zigbee/Meshtastic cu risc estimat,
- trend accelerație pentru ultimele eșantioane,
- sumar al alertelor active.

## Pe Raspberry Pi (hardware real)

```bash
sudo raspi-config            # Interface Options -> I2C -> Enable
pip install -r requirements-pi.txt
MCD_HW_TESTS=1 python -m mcd.test HardwareSmokeTest   # pulsează LED/buzzer, citește MPU6050, verifică porturile USB
```

Porturile USB implicite: `/dev/ttyUSB0` (XBee3, 9600 baud), `/dev/ttyACM0` (Meshtastic, 115200 baud). Se pot schimba cu `MCD_ZIGBEE_PORT` și `MCD_MESHTASTIC_PORT`.

## Testare pe Raspberry Pi, simulare și hardware real

Pentru ghidul complet cu comenzi, verificări, Meshtastic și teste de validare pe Pi, vezi:

- `docs/testare_pi_simulare_hardware.md`
- `GHID_TESTARE_SI_LIVRABILE.md`

### Adăugarea unui Heltec V3 / Meshtastic

Dacă conectezi un Heltec V3:

```bash
ls /dev/ttyACM*
meshtastic --port /dev/ttyACM0 --info
# sau, pe WiFi:
meshtastic --host 192.168.1.50 --info
```

Dacă placa este validă, apare în aplicație ca nod Meshtastic. Se recomandă USB serial pentru testare locală și WiFi/TCP dacă placa este la distanță pe aceeași rețea. Pentru Meshtastic există și conexiune TCP pe port 4403, dar USB este preferat pentru debug rapid.

Comenzi rapide:

```bash
# simulare
MCD_SIMULATE=1 python manage.py runserver 0.0.0.0:8000

# hardware real
MCD_SIMULATE=0 python manage.py runserver 0.0.0.0:8000

# verificare porturi
ls /dev/ttyUSB*
ls /dev/ttyACM*

# verificare Meshtastic
meshtastic --port /dev/ttyACM0 --info
```

## Observații

- `MPU6050_vInit` acceptă doar WHO_AM_I = 0x68; unele plăci clonă raportează altă valoare.
- Pe Pi 5, lgpio încearcă `gpiochip4`, apoi `gpiochip0`.
- Pagina de auto-test rulează doar testele în simulare, nu pornește buzzerul real.
