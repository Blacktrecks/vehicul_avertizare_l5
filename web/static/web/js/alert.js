document.addEventListener('DOMContentLoaded', () => {
  const ackButton = document.getElementById('alert-confirm');
  const emergencyButton = document.getElementById('emergency-off');
  const toastContainer = document.getElementById('toast-container');

  const showToast = (message, tone = 'info') => {
    if (!toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast ${tone}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 2200);
  };

  if (ackButton) {
    ackButton.addEventListener('click', async () => {
      try {
        await fetch('/api/alert/ack/', { method: 'POST' });
        showToast('Alertă confirmată', 'success');
      } catch (error) {
        showToast('Nu s-a putut confirma alertă', 'error');
      }
    });
  }

  if (emergencyButton) {
    emergencyButton.addEventListener('click', async () => {
      try {
        await fetch('/api/sim/stop/', { method: 'POST' });
        showToast('Protecția a fost oprită', 'warning');
      } catch (error) {
        showToast('Eroare oprire emergență', 'error');
      }
    });
  }
});
