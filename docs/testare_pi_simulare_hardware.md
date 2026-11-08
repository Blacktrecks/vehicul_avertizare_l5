# Testare pe Raspberry Pi, simulare și hardware real

## 1. Ce rulează în simulare și ce rulează pe hardware real

Proiectul este conceput pentru a funcționa în două moduri:

- Mod simulare: sistemul rulează fără dispozitive fizice; datele sunt generate în memorie și aplicația poate fi testată pe laptop, PC sau Raspberry Pi.
- Mod hardware: aplicația folosește GPIO, I2C, porturi USB și noduri Meshtastic/Zigbee reale.

Comutarea se face prin variabila `MCD_SIMULATE`:

- `MCD_SIMULATE=1` -> forțează simularea
- `MCD_SIMULATE=0` -> forțează hardware-ul real
- `MCD_SIMULATE=auto` sau variabilă necompletată -> folosește hardware dacă este disponibil, altfel simulează

Acest design permite dezvoltarea și testarea fără hardware, apoi validarea cu dispozitive reale pe Raspberry Pi.

---

## 2. Cum se rulează pe Raspberry Pi

### 2.1 Instalează dependențele

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev git
sudo raspi-config
```

În `raspi-config`:

- activează `I2C`
- verifică că serial-ul este disponibil dacă urmează să folosești dispozitive USB
- asigură-te că utilizatorul este în grupurile potrivite

```bash
sudo usermod -aG dialout,i2c,gpio $USER
sudo reboot
```

### 2.2 Creează mediul virtual și instalează dependențele

```bash
cd ~/vehicul_avertizare_l5
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-pi.txt
```

Dacă ai nevoie de suport pentru Meshtastic:

```bash
pip install meshtastic
```

### 2.3 Rulează testele

```bash
python -m mcd.test
python manage.py test
```

### 2.4 Rulează aplicația

```bash
DJANGO_ALLOWED_HOSTS='*' python manage.py runserver 0.0.0.0:8000
```

Apoi deschide:

- `http://<ip-pi>:8000/`
- sau `http://localhost:8000/` când ești direct pe Pi

---

## 3. Testare în mod simulare

Cel mai simplu mod de verificare este simularea:

```bash
MCD_SIMULATE=1 python manage.py runserver 0.0.0.0:8000
```

În acest mod:

- dashboard-ul trebuie să se încarce
- alertările pot fi generate logic
- lista de vecini apare din date simulate
- butoanele și interfața funcționează fără dispozitive fizice
- rularea este stabilă pe laptop/PC sau pe Pi

Acesta este metoda recomandată pentru verificarea UI-ului și a logicii de aplicație înainte de a conecta hardware-ul real.

---

## 4. Testare cu hardware real

### 4.1 Activează hardware-ul

```bash
MCD_SIMULATE=0 python manage.py runserver 0.0.0.0:8000
```

În acest mod aplicația încearcă să folosească dispozitivele fizice disponibile, cum ar fi:

- GPIO
- I2C (ex. MPU6050)
- porturi seriale USB
- noduri Meshtastic/Zigbee

### 4.2 Verifică porturile USB

```bash
ls /dev/serial/by-id/
ls /dev/ttyUSB*
ls /dev/ttyACM*
```

Dacă trebuie să fixezi explicit portul:

```bash
export MCD_ZIGBEE_PORT=/dev/ttyUSB0
export MCD_MESHTASTIC_PORT=/dev/ttyACM0
```

### 4.3 Verifică Meshtastic

```bash
meshtastic --port /dev/ttyACM0 --info
meshtastic --port /dev/ttyACM0 --nodes
meshtastic --port /dev/ttyACM0 --sendtext "hello from Pi"
```

Dacă placa este corect configurată, trebuie să vezi informațiile nodului, vecinii și mesajele trimise.

---

## 5. Cum se conectează dispozitivele reale

### 5.1 GPIO și I2C

Plăcile Raspberry Pi pot avea direct conectate:

- Senzorul MPU6050 prin I2C
- LED-uri și buzzer prin GPIO
- alte triggeruri sau semnale digitale

Se verifică cu:

```bash
python -m mcd.test
```

### 5.2 USB serial

Proiectul suportă dispozitive de tip USB serial, în special:

- Zigbee/XBee-like
- Meshtastic

Dacă un dispozitiv este conectat, dar aplicația continuă să ruleze în mod simulare, hardware-ul nu este folosit. Verifică:

```bash
echo $MCD_SIMULATE
```

Dacă valoarea este `1`, schimba-o la `0` înainte de a lansa aplicația.

### 5.3 Wireless Meshtastic

Pentru testarea reală între mai multe noduri:

1. flashează fiecare nod cu firmware Meshtastic
2. configurează aceeași regiune, canal și cheie pe toate nodurile
3. dă nume diferite fiecărui nod
4. conectează unul dintre ele la Pi prin USB
5. testează detectarea și comunicarea

Important: un nod Meshtastic nu va funcționa corect dacă:

- portul USB este greșit
- regiunea/canalul/cheia nu coincid
- dispozitivul nu este detectat de Linux
- aplicația rulează în simulare

---

## 6. Checklist pentru testele reale

Înainte să consideri că hardware-ul funcționează, verifică toate punctele de mai jos:

- [ ] aplicația rulează cu `MCD_SIMULATE=0`
- [ ] dispozitivul apare în `/dev/ttyUSB*` sau `/dev/ttyACM*`
- [ ] portul este corect
- [ ] `meshtastic --port ... --info` funcționează
- [ ] nodurile au aceeași regiune și aceeași cheie
- [ ] aplicația nu folosește date simulate
- [ ] alertarea se declanșează când este necesar

---

## 7. Reguli practice pentru testare

### Testare recomandată

1. Pornește sistemul în simulare
2. verifică UI-ul și comportamentele în browser
3. conectează un dispozitiv real
4. verifică portul și informațiile nodului
5. activează hardware-ul și rulează aplicația în modul real
6. testează mesajele și alertarea într-un scenariu real

### Regula de aur

Plasarea fizică a unui dispozitiv nu este suficientă. Sistemul va funcționa doar dacă:

- dispozitivul este detectat de Linux
- portul este corect
- aplicația este în mod hardware
- nodurile Meshtastic au configurația potrivită
- software-ul nu este în simulare

---

## 8. Ce este real și ce este simulat

În documentația proiectului trebuie să distingem clar între:

- real: GPIO, I2C, porturi USB, noduri Meshtastic, comunicație radio
- simulat: condiții de risc, vecini virtuali, valori de accelerație, date de test și scenarii de alertă

Este important ca în raport și în livrabile să se menționeze exact ce a fost validat în hardware real și ce a fost verificat doar în simulare.

---

## 9. Comenzi rapide de referință

```bash
# simulare
MCD_SIMULATE=1 python manage.py runserver 0.0.0.0:8000

# hardware real
MCD_SIMULATE=0 python manage.py runserver 0.0.0.0:8000

# teste
python -m mcd.test
python manage.py test

# verificare porturi
ls /dev/ttyUSB*
ls /dev/ttyACM*

# verificare Meshtastic
meshtastic --port /dev/ttyACM0 --info
meshtastic --port /dev/ttyACM0 --nodes
```

Aceste comenzi sunt utile atât pentru dezvoltare, cât și pentru testarea finală pe Raspberry Pi.
