# Tabel mapare pini (L4, cerința 3)

| Pin | Tip semnal | Nume semnal | Definiție |
| --- | --- | --- | --- |
| GPIO2 / SDA1 (pin 3) | COM | I2C_SDA | Linie date I2C către accelerometrul MPU6050 |
| GPIO3 / SCL1 (pin 5) | COM | I2C_SCL | Linie ceas I2C către accelerometrul MPU6050 |
| GPIO17 (pin 11) | DOP | BUZZER | Alertă sonoră: rezistență 1 kΩ, bază tranzistor NPN, buzzer între 5 V și colector, diodă de protecție |
| GPIO27 (pin 13) | DOP | LED | Alertă vizuală: LED cu rezistență de 330 Ω către GND |
| USB (hub alimentat) | COM | ZIGBEE | XBee3 Zigbee prin adaptor USB, /dev/ttyUSB0, 9600 baud |
| USB (hub alimentat) | COM | MESHTASTIC | Modul ESP Meshtastic (LoRa), /dev/ttyACM0, 115200 baud |
| 3V3 (pin 1) | PWR | VCC_MPU | Alimentare 3,3 V pentru MPU6050 |
| GND (pin 6) | PWR | GND | Masă comună (Pi, MPU6050, LED, tranzistor buzzer) |

Tipuri: DOP = ieșire digitală, DIP = intrare digitală, COM = comunicație, PWR = alimentare.
Sursa tabelului este `mcd/config.py` (`PIN_TABLE`); aceeași listă este afișată pe pagina web și la `/api/pins/`.
