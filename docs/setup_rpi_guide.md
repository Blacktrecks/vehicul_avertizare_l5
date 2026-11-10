# Setup Raspberry Pi 4/5 și testare aplicației

Acest ghid este pentru încărcarea codului pe Raspberry Pi și pornirea automată a aplicației. Urmează pas cu pas pe Pi 4/5 cu sistemul de operare complet instalat.

## 1. Prerechizite

- Raspberry Pi 4/5 cu Raspberry OS (32-bit sau 64-bit)
- acces la internet
- Python 3.11+ 
- Git
- opțional: monitor / touchscreen / browser desktop pentru testare
- dispozitive Meshtastic și/sau Zigbee disponibile pentru testare reală

## 2. Pregătirea sistemului

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git curl sqlite3
```

Activează I2C și serial port-ul dacă folosești hardware real:

```bash
sudo raspi-config
```

Apoi:
- Interface Options -> I2C -> Enable
- Interface Options -> Serial -> Enable (dacă folosești noduri USB serial)

## 3. Descărcarea proiectului pe Pi

```bash
cd /home/pi
git clone <repo-url>
cd vehicul_avertizare_l5
```

## 4. Crearea mediului virtual și instalarea dependențelor

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-pi.txt
```

Dacă folosești și noduri Meshtastic reale, instalează și biblioteca specifică:

```bash
pip install meshtastic
```

## 5. Variabile de mediu

Creează un fișier `.env` în folderul proiectului sau exportă variabilele direct:

```bash
export DJANGO_DEBUG=0
export DJANGO_ALLOWED_HOSTS='*'
export DJANGO_SECRET_KEY='schimba-acesta-cheie'
export MCD_SIMULATE=0
```

Pentru modul de simulare:

```bash
export MCD_SIMULATE=1
```

## 6. Pornirea aplicației manuală

În proiect:

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Apoi deschide:

- `http://<IP-PI>:8000/`
- sau `http://localhost:8000/` pe Pi

## 7. Pornire automată la boot (systemd)

Din folderul proiectului:

```bash
chmod +x scripts/install-systemd-service.sh
sudo ./scripts/install-systemd-service.sh
```

Acest script:
- copiază serviciul Django în `/etc/systemd/system/vehicul-alert.service`
- copiază serviciul browserului kiosk
- activează ambele servicii
- le pornește imediat

Verifică statusul:

```bash
sudo systemctl status vehicul-alert.service
sudo systemctl status vehicul-kiosk.service
```

Dacă trebuie să repornești serviciile:

```bash
sudo systemctl restart vehicul-alert.service
sudo systemctl restart vehicul-kiosk.service
```

## 8. Conectarea nodurilor Meshtastic

### 8.1 Prin USB serial

Verifică porturile disponibile:

```bash
ls /dev/ttyACM*
ls /dev/ttyUSB*
```

Exemple:
- `/dev/ttyACM0`
- `/dev/ttyUSB0`

Verifică dacă placa este accesibilă:

```bash
meshtastic --port /dev/ttyACM0 --info
```

### 8.2 Prin WiFi/TCP

Dacă nodul este în aceeași rețea WLAN:

```bash
meshtastic --host 192.168.1.50 --info
```

În aplicație, schema de conectare este:
- port serial pentru noduri USB
- IP + port 4403 pentru noduri WiFi/TCP
- conexiune simulată pentru dezvoltare fără hardware

## 9. Cum funcționează scanarea și conectarea dispozitivelor

În aplicația web:
- butonul de scanare detectează dispozitive disponibile
- din tabelul din UI poți face:
  - Conectează
  - Deconectează
  - Test

Acțiunea `Test` trimite un mesaj/packet de validare și verifică dacă dispozitivul răspunde corespunzător.

## 10. Testarea reală a aplicației

### Test automat Python

```bash
source .venv/bin/activate
python -m unittest tests.test_device_registry -v
python manage.py test --verbosity 1
```

### Test de prin port serial / Meshtastic

```bash
meshtastic --port /dev/ttyACM0 --nodes
meshtastic --port /dev/ttyACM0 --sendtext "hello from Pi"
```

### Test de WiFi

```bash
meshtastic --host 192.168.1.50 --sendtext "hello from Pi over wifi"
```

## 11. Test de funcționare a dashboard-ului

Verifică:

- pagina principală se încarcă
- dispozitivele apar în managerul de dispozitive
- scanarea funcționează
- butonul `Test` răspunde
- logurile se actualizează
- butonul de oprire tot se comportă corect

## 12. Verificări de daune / soluții rapide

### Port ocupat serial
Dacă apare eroare de port ocupat:

```bash
sudo lsof /dev/ttyACM0
```

Sau închide Meshtastic Web / CLI care utilizează portul.

### Nu apare dispozitivul în scanare
- verifică cablurile
- verifică portul serial
- verifică dacă nodul este configurat Meshtastic
- verifică dacă IP-ul și portul sunt accesibile pentru WiFi/TCP

### App nu pornește la boot
```bash
sudo journalctl -u vehicul-alert.service -b --no-pager
sudo journalctl -u vehicul-kiosk.service -b --no-pager
```

## 13. Checklist finală înainte de demonstrație

- [ ] aplicația rulează pe Pi
- [ ] browserul se deschide automat
- [ ] dashboard-ul se încarcă la boot
- [ ] nodul Meshtastic este conectat prin USB sau WiFi
- [ ] scanarea detectează dispozitivul
- [ ] butonul `Test` funcționează
- [ ] logurile înregistrează evenimentele
- [ ] aplicația funcționează în modul hardware și în modul simulare

## 14. Observații

- Meshtastic este un sistem LoRa Mesh, nu LoRaWAN.
- Configurarea nodurilor trebuie să fie consistentă între dispozitive.
- Pentru dezvoltare și test local, modulul de simulare este util și sigur.
