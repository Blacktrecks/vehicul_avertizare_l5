document.addEventListener('DOMContentLoaded', () => {
  const tableBody = document.getElementById('device-table-body');
  const scanButton = document.getElementById('scan-devices-btn');

  const getCookie = (name) => {
    const match = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : '';
  };

  const renderRows = (devices = []) => {
    if (!tableBody) return;
    if (!devices.length) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="5">Niciun dispozitiv găsit. Conectează un adaptor Zigbee sau un modul Meshtastic și apasă pe Scanare dispozitive.</td>
        </tr>
      `;
      return;
    }

    tableBody.innerHTML = devices.map((device) => {
      const id = device.id || device.address || 'device';
      const type = device.type || device.transport || 'sim';
      const address = device.address || device.port || device.device || '-';
      const state = device.state || 'connected';
      const label = device.label || device.name || device.id || address;
      const isConnected = state === 'connected';
      return `
        <tr>
          <td>${label}</td>
          <td>${type}</td>
          <td>${address}</td>
          <td><span class="status-chip ${isConnected ? 'ok' : ''}">${isConnected ? 'Conectat' : 'Disponibil'}</span></td>
          <td>
            <div class="chip-actions">
              <button type="button" data-device-id="${id}" data-device-action="connect">Conectează</button>
              <button type="button" data-device-id="${id}" data-device-action="disconnect">Deconectează</button>
              <button type="button" data-device-id="${id}" data-device-action="send-test">Test</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  };

  const loadDevices = async () => {
    try {
      const response = await fetch('/api/devices/scan/', { credentials: 'same-origin' });
      if (!response.ok) return;
      const payload = await response.json();
      renderRows(payload.devices || []);
    } catch (error) {
      console.warn('Device scan failed:', error);
    }
  };

  const postAction = async (deviceId, action) => {
    const csrfToken = getCookie('csrftoken');
    const response = await fetch(`/api/devices/${deviceId}/${action}/`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {}),
      },
    });
    if (response.ok) {
      await loadDevices();
    }
  };

  if (scanButton) {
    scanButton.addEventListener('click', loadDevices);
  }

  document.addEventListener('click', async (event) => {
    const trigger = event.target.closest('[data-device-action]');
    if (!trigger) return;
    const deviceId = trigger.getAttribute('data-device-id');
    const action = trigger.getAttribute('data-device-action');
    if (!deviceId || !action) return;
    await postAction(deviceId, action);
  });

  loadDevices();
});
