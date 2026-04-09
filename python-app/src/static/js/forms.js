/* ============================================================
   FORMS.JS — Utilidades globales de formularios y UI
   CaliPro Packing Exportación · MVP v0.1

   Cargado desde base.html — disponible en TODAS las páginas.
   ============================================================ */

/* ───────────────────────────────────────────
   TOAST SYSTEM
─────────────────────────────────────────── */

/**
 * Muestra un toast en esquina inferior derecha.
 * @param {string} msg   - Mensaje a mostrar
 * @param {string} type  - 'success' | 'info' | 'warning' | 'error'
 * @param {number} ms    - Duración en milisegundos (default 3000)
 */
function showToast(msg, type = 'info', ms = 3000) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const icons = { success: '✅', info: 'ℹ️', warning: '⚠️', error: '❌' };
  const toast = document.createElement('div');
  toast.className = 'toast ' + type;
  toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${msg}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = 'opacity 0.3s ease';
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 320);
  }, ms);
}

/* ───────────────────────────────────────────
   DJANGO MESSAGES → TOASTS
   Lee los mensajes de Django inyectados en #django-messages
   y los convierte en toasts automáticamente.
─────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const msgContainer = document.getElementById('django-messages');
  if (!msgContainer) return;

  msgContainer.querySelectorAll('span').forEach(span => {
    const raw  = span.dataset.type || 'info';
    // Django usa tags como 'messages success', normalizar:
    const type = raw.includes('error')   ? 'error'
               : raw.includes('warning') ? 'warning'
               : raw.includes('success') ? 'success'
               : 'info';
    showToast(span.textContent.trim(), type, 4000);
  });
});

/* ───────────────────────────────────────────
   PESO NETO — cálculo reactivo
   Usado en recepción y pesaje.
   IDs esperados: #peso-bruto, #peso-tara, #peso-neto
─────────────────────────────────────────── */
function updateNeto() {
  const brutoEl = document.getElementById('peso-bruto');
  const taraEl  = document.getElementById('peso-tara');
  const netoEl  = document.getElementById('peso-neto');
  if (!brutoEl || !netoEl) return;

  const bruto = parseFloat(brutoEl.value) || 0;
  const tara  = parseFloat(taraEl?.value) || 0;
  const neto  = Math.max(0, bruto - tara);
  netoEl.textContent = neto.toFixed(0) + ' kg';
}

document.addEventListener('input', e => {
  if (e.target.id === 'peso-bruto' || e.target.id === 'peso-tara') {
    updateNeto();
  }
});

/* ───────────────────────────────────────────
   NUMBER INPUT CON BOTONES +/-
   Uso: changeVal('campo-id', +1) / changeVal('campo-id', -1)
─────────────────────────────────────────── */
function changeVal(id, delta) {
  const input = document.getElementById(id);
  if (!input) return;
  const current = parseFloat(input.value) || 0;
  input.value = Math.max(0, current + delta);
  // Dispara evento input para que updateNeto se active si corresponde
  input.dispatchEvent(new Event('input', { bubbles: true }));
}

/* ───────────────────────────────────────────
   LIVE CLOCK
   Actualiza cualquier elemento con id="live-time"
─────────────────────────────────────────── */
function updateClock() {
  const el = document.getElementById('live-time');
  if (el) el.textContent = new Date().toLocaleTimeString('es-CL');
}
if (document.getElementById('live-time')) {
  updateClock();
  setInterval(updateClock, 1000);
}

/* ───────────────────────────────────────────
   CONFIRM DELETE — helper para formularios de eliminación
─────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', e => {
      const msg = el.dataset.confirm || '¿Confirmas esta acción?';
      if (!confirm(msg)) e.preventDefault();
    });
  });
});

/* ───────────────────────────────────────────
   SUBMIT LOADING STATE — previene doble envío
   Desactiva el botón y muestra spinner mientras
   el backend procesa la solicitud.
   Se aplica a todos los formularios POST.
─────────────────────────────────────────── */
document.addEventListener('submit', e => {
  const form = e.target;

  // Saltar formularios GET (búsquedas/filtros — no modifican datos)
  if ((form.getAttribute('method') || 'get').toLowerCase() === 'get') return;

  // e.submitter: botón exacto que disparó el submit (incluye botones externos con form="id")
  // Fallback: primer [type=submit] dentro del form
  const btn = e.submitter || form.querySelector('[type="submit"]');
  if (!btn || btn.disabled) return;

  btn.disabled = true;
  btn.innerHTML = '<span class="btn-spinner"></span> Enviando\u2026';
});
