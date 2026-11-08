document.addEventListener('DOMContentLoaded', () => {
  const clockEl = document.getElementById('clock');
  const modeBadge = document.getElementById('mode-badge');
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

  const updateClock = () => {
    const now = new Date();
    clockEl.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
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

  const applyState = (state) => {
    const normalized = normalizeState(state);
    speedValue.textContent = normalized.speed.toFixed(0);
    headingValue.textContent = normalized.heading.toFixed(0);
    distanceValue.textContent = `${normalized.distance.toFixed(1)} m`;
    sourceValue.textContent = normalized.source;
    expiresValue.textContent = `${normalized.expires.toFixed(1)} s`;
    modeBadge.textContent = (normalized.mode || 'SIMULARE').toUpperCase();
    modeBadge.className = `badge ${(normalized.mode === 'hardware' ? 'badge-hw' : 'badge-sim')}`;
    renderAlertState(normalized);
    renderNeighbors(normalized.neighbors || []);
  };

  updateClock();
  applyState(liveState);
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
