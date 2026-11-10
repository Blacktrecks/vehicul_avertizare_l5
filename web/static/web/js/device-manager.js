document.addEventListener('DOMContentLoaded', () => {
  const tableBody = document.getElementById('device-table-body');
  const scanButton = document.getElementById('scan-devices-btn');
  const profilePreviewEl = document.getElementById('device-profile-preview');
  const testFeedbackEl = document.getElementById('device-test-feedback');

  const escapeHtml = (value) => String(value == null ? '' : value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');

  const getCookie = (name) => {
    const match = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : '';
  };

  const statusClass = (status) => {
    const s = String(status || '').toLowerCase();
    if (s.includes('connected') || s.includes('ok')) return 'ok';
    if (s.includes('error') || s.includes('failed')) return 'error';
    return 'warn';
  };

  const humanState = (device) => {
    const state = String(device.state || 'available').toLowerCase();
    if (state.includes('connected')) return 'Conectat';
    if (state.includes('disconnected')) return 'Deconectat';
    if (state.includes('error')) return 'Eroare';
    return 'Disponibil';
  };

  const renderRows = (devices = []) => {
    if (!tableBody) return;
    if (!devices.length) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="6">Niciun dispozitiv găsit. Conectează un adaptor Zigbee sau un modul Meshtastic și apasă pe Scanare dispozitive.</td>
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
      const status = humanState(device);
      const region = device.region || 'UNKNOWN';
      const preset = device.preset || 'UNKNOWN';
      const channel = device.channel_name || 'UNKNOWN';
      const profileText = `${region} / ${preset} / ${channel}`;
      return `
        <tr>
          <td>${escapeHtml(label)}</td>
          <td>${escapeHtml(type)}</td>
          <td>${escapeHtml(address)}</td>
          <td>${escapeHtml(profileText)}</td>
          <td><span class="status-chip ${statusClass(state)}">${status}</span></td>
          <td>
            <div class="chip-actions">
              <button type="button" data-device-id="${id}" data-device-action="connect">Conectează</button>
              <button type="button" data-device-id="${id}" data-device-action="disconnect">Deconectează</button>
              <button type="button" data-device-id="${id}" data-device-action="send-test">Test</button>
              <button type="button" data-device-id="${id}" data-device-action="profile-preview">Preview profil</button>
              <button type="button" data-device-id="${id}" data-device-action="apply-profile">Aplică profil</button>
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

  const renderProfilePreview = (preview) => {
    if (!profilePreviewEl) return;
    if (!preview) {
      profilePreviewEl.textContent = 'Nu există date de profil.';
      return;
    }
    const diff = preview.diff || {};
    const rows = Object.keys(diff).map((key) => {
      const item = diff[key] || {};
      return `<div><strong>${escapeHtml(key)}</strong>: ${escapeHtml(item.current)} → ${escapeHtml(item.target)}</div>`;
    }).join('');
    profilePreviewEl.innerHTML = `
      <div><strong>Device:</strong> ${escapeHtml(preview.device_id || '-')}</div>
      <div><strong>Compatibil:</strong> ${preview.compatible ? 'Da' : 'Nu'}</div>
      <div><strong>Țintă:</strong> ${escapeHtml((preview.target || {}).region || '-')}/${escapeHtml((preview.target || {}).preset || '-')}/${escapeHtml((preview.target || {}).channel_name || '-')}</div>
      ${rows || '<div>Nu există diferențe. Profilul este deja sincronizat.</div>'}
    `;
  };

  const renderTestFeedback = (payload, action) => {
    if (!testFeedbackEl) return;
    const result = payload && payload.result ? payload.result : {};
    const preview = payload && payload.preview ? payload.preview : {};
    const ts = new Date().toLocaleTimeString();
    testFeedbackEl.innerHTML = `
      <div><strong>Acțiune:</strong> ${escapeHtml(action)}</div>
      <div><strong>Ora:</strong> ${escapeHtml(ts)}</div>
      <div><strong>Mesaj:</strong> ${escapeHtml(result.message || payload.message || 'Acțiune executată')}</div>
      ${preview.node ? `<div><strong>Nod:</strong> ${escapeHtml(preview.node)}</div>` : ''}
      ${preview.payload ? `<div><strong>Payload:</strong> ${escapeHtml(preview.payload)}</div>` : ''}
    `;
  };

  const loadProfilePreview = async (deviceId) => {
    const response = await fetch(`/api/devices/${deviceId}/profile-preview/`, {
      credentials: 'same-origin',
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      window.alert(payload.error || 'Nu s-a putut încărca preview-ul profilului.');
      return;
    }
    renderProfilePreview(payload.preview);
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
    const payload = await response.json().catch(() => ({}));
    if (response.ok) {
      await loadDevices();
      renderTestFeedback(payload, action);
      if (action === 'apply-profile' || action === 'connect') {
        await loadProfilePreview(deviceId);
      }
      if (payload.result && payload.result.message) {
        window.alert(payload.result.message);
      }
    } else {
      window.alert(payload.error || 'Acțiunea a eșuat.');
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
    if (action === 'profile-preview') {
      await loadProfilePreview(deviceId);
      return;
    }
    await postAction(deviceId, action);
  });

  loadDevices();
});
