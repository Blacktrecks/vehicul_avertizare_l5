document.addEventListener('DOMContentLoaded', () => {
  const svg = document.getElementById('radar-svg');
  if (!svg) return;

  const rings = [60, 120, 180, 240, 300, 360, 420];
  const center = 250;

  const ns = 'http://www.w3.org/2000/svg';

  const createSvg = (name, attrs = {}) => {
    const el = document.createElementNS(ns, name);
    Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, value));
    return el;
  };

  rings.forEach((r) => {
    svg.appendChild(createSvg('circle', {
      cx: center,
      cy: center,
      r,
      fill: 'none',
      stroke: 'rgba(57,255,136,0.22)',
      'stroke-width': 1
    }));
  });

  for (let a = 0; a < 12; a++) {
    const angle = (a / 12) * Math.PI * 2;
    const x1 = center + Math.cos(angle) * 90;
    const y1 = center + Math.sin(angle) * 90;
    const x2 = center + Math.cos(angle) * 200;
    const y2 = center + Math.sin(angle) * 200;

    svg.appendChild(createSvg('line', {
      x1,
      y1,
      x2,
      y2,
      stroke: 'rgba(57,255,136,0.22)',
      'stroke-width': 1,
      'stroke-linecap': 'round'
    }));
  }

  const vehicle = createSvg('g', { transform: `translate(${center} ${center})` });
  vehicle.appendChild(createSvg('circle', {
    cx: 0,
    cy: 0,
    r: 12,
    fill: '#39ff88',
    opacity: 0.9
  }));
  vehicle.appendChild(createSvg('path', {
    d: 'M 0 -16 L 18 0 L 0 16 L -18 0 Z',
    fill: 'rgba(168,85,247,0.7)'
  }));
  svg.appendChild(vehicle);

  const pulseRing = createSvg('circle', {
    cx: center,
    cy: center,
    r: 10,
    fill: 'none',
    stroke: 'rgba(57,255,136,0.6)',
    'stroke-width': 2
  });
  svg.appendChild(pulseRing);

  let frame = 0;
  const animate = () => {
    frame += 1;
    const radius = 22 + (Math.sin(frame / 18) + 1) * 18;
    pulseRing.setAttribute('r', String(radius));
    pulseRing.setAttribute('opacity', String(0.9 - radius / 100));
    requestAnimationFrame(animate);
  };

  requestAnimationFrame(animate);
});
