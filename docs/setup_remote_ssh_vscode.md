# Setup Remote SSH in VS Code (Laptop -> Raspberry Pi)

This guide explains how to connect VS Code on your laptop to your Raspberry Pi using SSH, so you can edit and run this project directly on the Pi.

## 1. Requirements

- Laptop and Raspberry Pi on the same network.
- SSH server enabled on Raspberry Pi.
- Pi user and IP known (example used below: `pi4@10.33.173.229`).
- VS Code installed on laptop.

## 2. Install Required VS Code Extension

Install this extension on your laptop:

- **Remote - SSH** (Microsoft)

Optional but useful:

- **Remote - SSH: Editing Configuration Files**

## 3. Prepare SSH Keys on Laptop

Run on laptop terminal:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
ssh-keygen -t ed25519 -C "pi4-laptop"
```

When asked for key path, press Enter to keep default:

- `~/.ssh/id_ed25519`

Copy public key to Pi:

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub pi4@10.33.173.229
```

Test key login:

```bash
ssh -i ~/.ssh/id_ed25519 pi4@10.33.173.229
```

If this works without password prompt, key setup is complete.

## 4. Create SSH Config on Laptop

Edit:

```bash
nano ~/.ssh/config
```

Add:

```sshconfig
Host pi4
    HostName 10.33.173.229
    User pi4
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
    ServerAliveInterval 20
    ServerAliveCountMax 3
    ConnectTimeout 10
```

Set proper permission:

```bash
chmod 600 ~/.ssh/config
```

Quick test:

```bash
ssh pi4
```

## 5. Connect from VS Code

1. Open VS Code.
2. Press `Ctrl+Shift+P` (Command Palette).
3. Run: `Remote-SSH: Connect to Host...`
4. Choose `pi4`.
5. If asked platform, choose **Linux**.
6. Wait until remote window opens.
7. In remote window, click **Open Folder** and open:
   - `/home/pi4/Desktop/vehicul_avertizare_l5`

After this, all file edits and terminals are running on the Pi.

## 6. Verify You Are Really on the Pi

In the remote VS Code terminal:

```bash
hostname
pwd
```

Expected:

- hostname like `Pi4Master`
- project path under `/home/pi4/...`

## 7. Common Issues and Fixes

### A) "Connection timed out"

Usually network issue.

Check from laptop:

```bash
ping -c 4 10.33.173.229
ssh -vvv pi4@10.33.173.229
```

If ping/ssh works, network is fine.

### B) "Connecting was canceled"

Usually the VS Code connection wizard was interrupted.

Fix:

1. Retry `Remote-SSH: Connect to Host...`
2. Select Linux and wait (do not close popup).
3. If still failing, close VS Code and run on laptop:

```bash
pkill -f vscode-server || true
pkill -f "code.*ssh" || true
```

Then reopen VS Code and reconnect.

### C) Broken VS Code `remote.SSH.configFile`

This setting must be a **file path**, not host text.

Correct value:

- `/home/<your-user>/.ssh/config`

## 8. Recommended VS Code SSH Settings

In VS Code settings (`settings.json`):

```json
{
  "remote.SSH.configFile": "/home/think-pici-linux/.ssh/config",
  "remote.SSH.useLocalServer": false,
  "remote.SSH.useExecServer": true
}
```

## 9. After Connection: Run the Project on Pi

Inside remote terminal (on Pi):

```bash
cd /home/pi4/Desktop/vehicul_avertizare_l5
source .venv/bin/activate
python manage.py check
python manage.py runserver 0.0.0.0:8000
```

Open in browser:

- `http://10.33.173.229:8000/`

---

If hardware actions still fail after connection, verify serial permissions and attached USB devices on Pi:

```bash
ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
groups
```