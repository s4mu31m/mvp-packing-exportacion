/* ============================================================
   SCAN.JS — Lógica de scanner de código de barras
   CaliPro Packing Exportación · MVP v0.1

   Cargado SOLO en páginas que tienen un #scan-box.
   Captura la entrada del lector de código de barras (USB HID)
   que actúa como teclado y termina con Enter.
   ============================================================ */

(function () {
  'use strict';

  /* ── Configuración ─────────────────────────────────────── */
  const SCAN_INPUT_ID  = 'scan-input';   // input oculto/autofocus
  const BIN_CODE_ID    = 'id_codigo';    // campo destino (nombre de campo Django)
  const SCAN_BOX_ID    = 'scan-box';
  const MIN_SCAN_LEN   = 3;              // longitud mínima para aceptar un scan
  const FLASH_MS       = 280;            // duración del flash visual

  /* ── Estado interno ─────────────────────────────────────── */
  let scanBuffer = '';
  let scanTimer  = null;

  /* ── Helpers ─────────────────────────────────────────────── */
  function flashScanBox(success = true) {
    const box = document.getElementById(SCAN_BOX_ID);
    if (!box) return;
    box.classList.add('active');
    if (success) box.style.borderColor = 'var(--teal-500)';
    else         box.style.borderColor = 'var(--danger)';
    setTimeout(() => {
      box.classList.remove('active');
      box.style.borderColor = '';
    }, FLASH_MS);
  }

  function setFieldValue(fieldId, value) {
    /* Intenta el ID exacto; si no, busca por name= (Django puede generar id_ prefix) */
    let el = document.getElementById(fieldId)
          || document.getElementById('id_' + fieldId)
          || document.querySelector(`[name="${fieldId}"]`);
    if (!el) return false;
    el.value = value;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  }

  function processScan(code) {
    code = code.trim();
    if (code.length < MIN_SCAN_LEN) return;

    const placed = setFieldValue(BIN_CODE_ID, code)
                || setFieldValue('bin-code', code)
                || setFieldValue('codigo_bin', code);

    if (placed) {
      flashScanBox(true);
      if (typeof showToast === 'function') {
        showToast('Bin ' + code + ' escaneado', 'success');
      }
      // Mueve foco al siguiente campo relevante (ej. peso bruto)
      const nextField = document.getElementById('id_peso_bruto')
                     || document.getElementById('peso-bruto');
      if (nextField) nextField.focus();
    } else {
      flashScanBox(false);
      if (typeof showToast === 'function') {
        showToast('Campo destino no encontrado para: ' + code, 'warning');
      }
      console.warn('[scan.js] No se encontró el campo destino para código:', code);
    }
  }

  /* ── Captura global de teclado (scanner USB actúa como kbd) ─ */
  document.addEventListener('keydown', function (e) {
    // Ignora si el foco está en un input real (el usuario está escribiendo)
    const tag = document.activeElement?.tagName;
    const type = document.activeElement?.type;
    const isTypingField = (tag === 'INPUT' && type !== 'submit' && type !== 'button')
                       || tag === 'TEXTAREA'
                       || tag === 'SELECT';

    // Si hay un input oculto de scan dedicado, siempre redirigir ahí
    const scanInput = document.getElementById(SCAN_INPUT_ID);
    if (scanInput && document.activeElement !== scanInput && !isTypingField) {
      scanInput.focus();
    }

    if (e.key === 'Enter') {
      if (scanBuffer.length >= MIN_SCAN_LEN) {
        processScan(scanBuffer);
        scanBuffer = '';
        e.preventDefault();
      }
      clearTimeout(scanTimer);
      return;
    }

    // Acumula caracteres del scanner (llegan muy rápido, < 50ms entre keystrokes)
    if (e.key.length === 1) {
      scanBuffer += e.key;
      clearTimeout(scanTimer);
      // Si no llega Enter en 200ms, descartar buffer (escritura manual)
      scanTimer = setTimeout(() => { scanBuffer = ''; }, 200);
    }
  });

  /* ── Input oculto como alternativa (fallback mobile / WebHID) ─ */
  const scanInput = document.getElementById(SCAN_INPUT_ID);
  if (scanInput) {
    scanInput.addEventListener('change', function () {
      if (this.value.trim()) {
        processScan(this.value.trim());
        this.value = '';
      }
    });
    // Mantener autofocus cuando el usuario hace click en el scan-box
    const scanBox = document.getElementById(SCAN_BOX_ID);
    if (scanBox) {
      scanBox.addEventListener('click', () => scanInput.focus());
    }
  }

  /* ── Exponer función pública para simular scan en desarrollo ─ */
  window.simularScan = function (code) {
    code = code || 'BIN-' + Math.floor(1000 + Math.random() * 9000);
    processScan(code);
  };

})();
