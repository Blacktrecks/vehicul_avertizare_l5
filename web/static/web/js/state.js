document.addEventListener('DOMContentLoaded', () => {
  const clockEl = document.getElementById('clock');
  const modeToggle = document.getElementById('mode-toggle');
  const modeToggleLabel = document.getElementById('mode-toggle-label');
  const themeToggle = document.getElementById('theme-toggle');
  const speedValue = document.getElementById('speed-value');
  const headingValue = document.getElementById('heading-value');
  const distanceValue = document.getElementById('distance-value');
  const sourceValue = document.getElementById('source-value');
  const expiresValue = document.getElementById('expires-value');
  const alertState = document.getElementById('alert-state');
  const alertPanel = document.getElementById('alert-panel');
  const alertMessage = document.getElementById('alert-message');
  const neighbourCount = document.getElementById('neighbour-count');
  const tableBody = document.getElementById('neighbours-table-body');
  const stateDataEl = document.getElementById('state-data');
  const liveState = stateDataEl ? JSON.parse(stateDataEl.textContent) : {};

  const getCookie = (name) => {
    const match = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : '';
  };

  const applyTheme = (theme) => {
    const resolved = theme === 'light' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', resolved);
    document.body.setAttribute('data-theme', resolved);
    if (themeToggle) {
      themeToggle.textContent = resolved === 'dark' ? '☀️' : '🌙';
      themeToggle.setAttribute('aria-label', resolved === 'dark' ? 'Comută în mod lumină' : 'Comută în mod întuneric');
    }
    try {
      window.localStorage.setItem('vehicul-theme', resolved);
    } catch (error) {
      console.warn('Theme storage unavailable:', error);
    }
  };

  const updateModeDisplay = (mode) => {
    const resolvedMode = String(mode || 'simulation').toLowerCase();
    const isHardware = resolvedMode === 'hardware' || resolvedMode === 'real' || resolvedMode === 'hw';
    if (modeToggle) {
      modeToggle.classList.toggle('is-hardware', isHardware);
    }
    if (modeToggleLabel) {
      modeToggleLabel.textContent = isHardware ? 'HARDWARE' : 'SIMULARE';
    }
  };

  const savedTheme = (() => {
    try {
      return window.localStorage.getItem('vehicul-theme') || 'dark';
    } catch (error) {
      return 'dark';
    }
  })();

  applyTheme(savedTheme);

  if (themeToggle) {
    const toggleTheme = () => {
      const currentTheme = document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
      const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
      applyTheme(nextTheme);
    };
    themeToggle.addEventListener('click', toggleTheme);
    themeToggle.onclick = toggleTheme;
  }

  const updateClock = () => {
    const now = new Date();
    if (clockEl) clockEl.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const normalizeState = (state) => {
    const ego = state.ego || {};
    const alert = state.alert || {};
    const neighbors = Array.isArray(state.neighbours) ? state.neighbours : [];
    const nearest = neighbors.reduce((closest, item) => {
      const distance = Number(item.distance_m ?? Number.POSITIVE_INFINITY);
      return Number.isFinite(distance) && distance < (closest ?? Number.POSITIVE_INFINITY) ? distance : closest;
    }, Number.POSITIVE_INFINITY);
    const distance = Number(alert.distance_m ?? (Number.isFinite(nearest) ? nearest : null));
    const source = alert.source || (neighbors[0] && neighbors[0].source) || 'sim';
    const expires = Number(alert.expires_in_s ?? 0);
    const severity = alert.active ? (alert.type === 'impact' || distance <= 25 ? 'danger' : 'warning') : 'safe';

    return {
      mode: state.mode || 'virtual',
      speed: Number(ego.speed_kmh ?? 0),
      heading: Number(ego.heading_deg ?? 0),
      distance: Number.isFinite(distance) ? distance : 0,
      source,
      expires,
      alert: severity,
      neighbors: neighbors.map((n) => ({
        id: n.id ?? '--',
        source: n.source ?? '--',
        distance: Number(n.distance_m ?? 0),
        heading: Number(n.heading_deg ?? n.bearing_deg ?? 0),
        speed: Number(n.speed_kmh ?? 0),
        last_rx: `${Number(n.age_s ?? 0).toFixed(1)} s`,
      })),
    };
  };

  const renderAlertState = (state) => {
    if (!alertState || !alertPanel || !alertMessage) return;
    const alertText = state.alert === 'warning' ? 'Atenție' : state.alert === 'danger' ? 'Pericol' : 'În siguranță';
    const classes = state.alert === 'warning' ? 'warn' : state.alert === 'danger' ? 'error' : 'neutral';
    alertState.className = `pill-text ${classes}`;
    alertState.textContent = alertText;

    if (state.alert === 'danger') {
      alertPanel.classList.remove('hidden');
      alertMessage.textContent = 'IMPACT ÎN FAȚĂ';
    } else if (state.alert === 'warning') {
      alertPanel.classList.remove('hidden');
      alertMessage.textContent = 'PERSOANĂ / OBSTACOL APROPIAT';
    } else {
      alertPanel.classList.add('hidden');
    }
  };

  const renderNeighbors = (neighbors = []) => {
    if (!neighbourCount || !tableBody) return;
    neighbourCount.textContent = `${neighbors.length} vecini`;
    tableBody.innerHTML = neighbors.map((n) => `
      <tr>
        <td>${n.id ?? '--'}</td>
        <td>${n.source ?? '--'}</td>
        <td>${Number(n.distance ?? 0).toFixed(1)} m</td>
        <td>${Number(n.heading ?? 0).toFixed(0)}°</td>
        <td>${Number(n.speed ?? 0).toFixed(0)} km/h</td>
        <td>${n.last_rx ?? '--'}</td>
      </tr>
    `).join('');
  };

  const updateTrendBars = (selector, values) => {
    const bars = document.querySelectorAll(selector);
    bars.forEach((bar, index) => {
      const value = Number(values[index] ?? 40);
      bar.style.height = `${Math.max(18, Math.min(100, value))}%`;
    });
  };

  const applyState = (state) => {
    const normalized = normalizeState(state || {});
    const currentMode = String((state && state.mode) || normalized.mode || 'simulation').toLowerCase();
    const visualMode = ['simulation', 'virtual', 'sim'].includes(currentMode) ? 'simulation' : 'hardware';
    const zigbee = state && state.links && state.links.zigbee ? state.links.zigbee : { state: 'ok', rx: 120, tx: 120, err: 0, last_rx_s: 0.4 };
    const meshtastic = state && state.links && state.links.meshtastic ? state.links.meshtastic : { state: 'ok', rx: 4, tx: 4, err: 0, last_rx_s: 12.0 };
    const deviceCount = Array.isArray(state && state.devices) ? state.devices.length : 0;
    const zigbeePct = Math.max(0, Math.min(100, Math.round((zigbee.rx / Math.max(zigbee.tx || zigbee.rx || 1, 1)) * 100 || 72)));
    const meshtasticPct = Math.max(0, Math.min(100, Math.round((meshtastic.rx / Math.max(meshtastic.tx || meshtastic.rx || 1, 1)) * 100 || 91)));
    const hardwarePct = Math.max(45, Math.min(100, 72 + (visualMode === 'hardware' ? 12 : 0) - (deviceCount ? 3 : 0)));

    if (speedValue) speedValue.textContent = normalized.speed.toFixed(0);
    if (headingValue) headingValue.textContent = normalized.heading.toFixed(0);
    if (distanceValue) distanceValue.textContent = `${normalized.distance.toFixed(1)} m`;
    if (sourceValue) sourceValue.textContent = normalized.source;
    if (expiresValue) expiresValue.textContent = `${normalized.expires.toFixed(1)} s`;

    const zigbeeBar = document.getElementById('zigbee-signal-bar');
    const meshtasticBar = document.getElementById('meshtastic-signal-bar');
    const hardwareBar = document.getElementById('hardware-signal-bar');
    if (zigbeeBar) zigbeeBar.style.width = `${zigbeePct}%`;
    if (meshtasticBar) meshtasticBar.style.width = `${meshtasticPct}%`;
    if (hardwareBar) hardwareBar.style.width = `${hardwarePct}%`;

    const zigbeeValue = document.getElementById('zigbee-signal-value');
    const meshtasticValue = document.getElementById('meshtastic-signal-value');
    const hardwareValue = document.getElementById('hardware-signal-value');
    if (zigbeeValue) zigbeeValue.textContent = `${zigbeePct}%`;
    if (meshtasticValue) meshtasticValue.textContent = `${meshtasticPct}%`;
    if (hardwareValue) hardwareValue.textContent = `${hardwarePct}%`;

    const rssiZigbee = document.getElementById('rssi-zigbee');
    const rssiMeshtastic = document.getElementById('rssi-meshtastic');
    if (rssiZigbee) rssiZigbee.textContent = `${(zigbee.last_rx_s ?? 0.4) > 5 ? '-72' : '-60'} dBm`;
    if (rssiMeshtastic) rssiMeshtastic.textContent = `${(meshtastic.last_rx_s ?? 12) > 20 ? '-76' : '-68'} dBm`;

    const pdrSummary = document.getElementById('pdr-summary');
    if (pdrSummary) pdrSummary.textContent = `${Math.round((zigbeePct + meshtasticPct) / 2)}%`;

    const deviceSummary = document.getElementById('device-summary');
    if (deviceSummary) deviceSummary.textContent = `${deviceCount} noduri`;

    const riskIndex = document.getElementById('risk-index');
    if (riskIndex) {
      const dangerScore = Math.max(22, Math.min(98, Math.round((100 - normalized.distance) + (normalized.alert === 'danger' ? 20 : normalized.alert === 'warning' ? 10 : 0))));
      riskIndex.textContent = `${dangerScore}%`;
    }

    const speedTrendValue = document.getElementById('speed-trend-value');
    if (speedTrendValue) {
      speedTrendValue.textContent = `${Math.max(0, normalized.speed).toFixed(0)} km/h`;
    }

    const latencyTrendValue = document.getElementById('latency-trend-value');
    if (latencyTrendValue) {
      const latencyMs = Math.max(180, Math.min(950, Math.round(280 + normalized.distance * 1.8 + (visualMode === 'hardware' ? 40 : 0))));
      latencyTrendValue.textContent = `${latencyMs} ms`;
    }

    const riskTrend = [30, 36, 44, 50, 61, 70, 82, 90].map((base) => Math.min(100, base + (normalized.alert === 'danger' ? 12 : normalized.alert === 'warning' ? 6 : 0)));
    const speedTrend = [38, 42, 48, 53, 60, 64, 72, 86].map((base) => Math.min(100, base + normalized.speed * 0.18));
    const latencyTrend = [28, 34, 44, 52, 61, 58, 46, 60].map((base) => Math.min(100, base + (normalized.distance > 40 ? 12 : 0)));
    updateTrendBars('[data-trend="risk"]', riskTrend);
    updateTrendBars('[data-trend="speed"]', speedTrend);
    updateTrendBars('[data-trend="latency"]', latencyTrend);

    const meshHealthBar = document.getElementById('mesh-health-bar');
    const usbHealthBar = document.getElementById('usb-health-bar');
    const positionHealthBar = document.getElementById('position-health-bar');
    const meshHealthValue = document.getElementById('mesh-health-value');
    const usbHealthValue = document.getElementById('usb-health-value');
    const positionHealthValue = document.getElementById('position-health-value');
    const meshHealth = Math.min(100, Math.max(50, meshtasticPct + 8));
    const usbHealth = Math.min(100, Math.max(50, zigbeePct + 12));
    const positionHealth = Math.min(100, Math.max(60, 88 - (normalized.distance > 100 ? 10 : 0) + (visualMode === 'hardware' ? 4 : 0)));
    if (meshHealthBar) meshHealthBar.style.width = `${meshHealth}%`;
    if (usbHealthBar) usbHealthBar.style.width = `${usbHealth}%`;
    if (positionHealthBar) positionHealthBar.style.width = `${positionHealth}%`;
    if (meshHealthValue) meshHealthValue.textContent = `${meshHealth}%`;
    if (usbHealthValue) usbHealthValue.textContent = `${usbHealth}%`;
    if (positionHealthValue) positionHealthValue.textContent = `${positionHealth}%`;

    updateModeDisplay(visualMode);
    renderAlertState(normalized);
    renderNeighbors(normalized.neighbors || []);
  };

  if (modeToggle) {
    modeToggle.addEventListener('click', async () => {
      const currentMode = (modeToggleLabel && modeToggleLabel.textContent ? modeToggleLabel.textContent.toLowerCase() : 'simulation');
      const nextMode = currentMode.includes('hardware') ? 'simulation' : 'hardware';
      const csrfToken = getCookie('csrftoken');
      updateModeDisplay(nextMode);
      try {
        const response = await fetch('/api/mode/', {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {}),
          },
          body: JSON.stringify({ mode: nextMode }),
        });
        if (!response.ok) {
          throw new Error('Mode switch failed');
        }
        const payload = await response.json();
        updateModeDisplay(payload.state && payload.state.mode ? payload.state.mode : nextMode);
        if (payload.state) {
          applyState(payload.state);
        }
      } catch (error) {
        console.warn('Mode switch failed:', error);
        updateModeDisplay(currentMode);
      }
    });
  }

  updateClock();
  if (Object.keys(liveState).length) {
    applyState(liveState);
  } else {
    updateModeDisplay('simulation');
  }
  setInterval(updateClock, 1000 * 30);

  const refreshFromApi = async () => {
    try {
      const response = await fetch('/api/state/');
      if (!response.ok) return;
      const payload = await response.json();
      applyState(payload);
    } catch (error) {
      console.warn('State fetch failed:', error);
    }
  };

  window.setInterval(refreshFromApi, 2500);
});
