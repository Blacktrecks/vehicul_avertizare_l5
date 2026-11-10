# Ghid: workflow XIAO Meshtastic in aplicatie

Acest ghid explica pasii pentru conectare, profil, test TX si rulare scenarii pentru XIAO (ESP32-C3/S3) cu firmware Meshtastic.

## 1. Pregatire hardware

1. Conecteaza placa XIAO la Raspberry Pi prin USB.
2. Verifica portul:
   - `ls /dev/ttyACM*`
   - `ls /dev/ttyUSB*`
3. Daca folosesti Meshtastic Web/CLI in paralel, inchide-l ca sa nu blocheze portul serial.

## 2. Instalare dependinte pentru integrare reala Meshtastic

1. Activeaza mediul virtual.
2. Instaleaza pachete:
   - `pip install -r requirements-pi.txt`
   - `pip install meshtastic`

Daca pachetul `meshtastic` lipseste, aplicatia ramane functionala in fallback si ruleaza test simulat.

## 3. Flux UI (pagina Dispozitive)

1. Intra la `/devices/`.
2. Apasa **Scanare dispozitive**.
3. Pentru dispozitivul XIAO:
   - apasa **Conecteaza**
   - apasa **Preview profil**
   - verifica diferentele
   - apasa **Aplica profil**
4. Ruleaza **Test**.
5. Citeste rezultatul in panoul **Feedback test Meshtastic**:
   - nod tinta
   - payload transmis
   - mesaj de succes/eroare
6. Apasa **Deconecteaza** pentru inchidere curata.

## 4. Endpoint-uri API utile

- `GET /api/devices/scan/` -> detectare USB
- `POST /api/devices/<id>/connect/` -> conectare persistenta
- `POST /api/devices/<id>/disconnect/` -> deconectare
- `GET /api/devices/<id>/profile-preview/` -> preview profil
- `POST /api/devices/<id>/apply-profile/` -> aplicare profil
- `POST /api/devices/<id>/send-test/` -> test Meshtastic
- `GET /api/logs/stream/` -> SSE loguri live

## 5. Teste scenarii JSON

1. Uploadeaza scenariu:
   - `POST /api/tests/`
2. Ruleaza scenariu:
   - `POST /api/tests/run/`
3. Rapoartele sunt salvate in `data/reports/`.

Fisier exemplu inclus: `scenarios/xiao_meshtastic_smoke.json`.

## 6. Exemplu curl rapid

```bash
curl -s http://127.0.0.1:8000/api/devices/scan/
curl -s -X POST http://127.0.0.1:8000/api/devices/dev-ttyACM0/connect/
curl -s http://127.0.0.1:8000/api/devices/dev-ttyACM0/profile-preview/
curl -s -X POST http://127.0.0.1:8000/api/devices/dev-ttyACM0/apply-profile/
curl -s -X POST http://127.0.0.1:8000/api/devices/dev-ttyACM0/send-test/
curl -s -X POST http://127.0.0.1:8000/api/devices/dev-ttyACM0/disconnect/
```

## 7. Note practice

- ID-ul dispozitivului poate fi diferit (`dev-ttyACM0`, `dev-ttyUSB0`, etc.).
- Pentru test real Meshtastic, placa trebuie sa ruleze firmware Meshtastic si sa fie accesibila pe port.
- Daca vezi eroare de port ocupat, inchide orice alta aplicatie care foloseste acelasi serial.
