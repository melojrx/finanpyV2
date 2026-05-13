/**
 * FinanPy — Shell mobile-first
 *
 * Responsabilidades:
 *   1. Registrar o service worker (/sw.js)
 *   2. Drawer lateral: abrir/fechar, focus trap, Escape, backdrop, scroll-lock
 *   3. Auto-dismiss de toasts em 5s (respeita prefers-reduced-motion)
 *   4. Bottom-sheet behavior (open/close + drag-to-close básico)
 *   5. Listener de mensagens do SW (ex.: SYNC_DRAINED)
 *
 * Carregado via <script defer src="{% static 'js/shell.js' %}">.
 */

(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // 1) Service Worker
  // ---------------------------------------------------------------------------
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker
        .register('/sw.js', { scope: '/' })
        .then(function (reg) {
          if (reg.waiting) {
            showUpdateBanner(reg.waiting);
          }
          reg.addEventListener('updatefound', function () {
            var nw = reg.installing;
            if (!nw) return;
            nw.addEventListener('statechange', function () {
              if (nw.state === 'installed' && navigator.serviceWorker.controller) {
                showUpdateBanner(nw);
              }
            });
          });
        })
        .catch(function (err) {
          console.warn('[FinanPy] SW registration falhou:', err);
        });

      navigator.serviceWorker.addEventListener('message', function (event) {
        if (!event.data) return;
        if (event.data.type === 'SYNC_DRAINED') {
          showSyncToast();
        }
      });

      var refreshing = false;
      navigator.serviceWorker.addEventListener('controllerchange', function () {
        if (refreshing) return;
        refreshing = true;
        window.location.reload();
      });
    });
  }

  function showUpdateBanner(worker) {
    var banner = document.createElement('div');
    banner.className = 'fixed bottom-20 left-4 right-4 md:left-auto md:right-4 md:w-80 z-50 bg-primary-700 text-white rounded-xl p-4 shadow-lg flex items-center justify-between gap-3';
    banner.setAttribute('role', 'alert');
    banner.innerHTML =
      '<span class="text-sm font-medium">Nova versão disponível</span>' +
      '<button type="button" class="px-3 py-1.5 bg-white text-primary-700 rounded-lg text-sm font-semibold hover:bg-gray-100 transition">Atualizar</button>';
    banner.querySelector('button').addEventListener('click', function () {
      worker.postMessage({ type: 'SKIP_WAITING' });
      banner.remove();
    });
    document.body.appendChild(banner);
  }

  function showSyncToast() {
    var container = document.getElementById('finanpy-toasts');
    if (!container) return;
    var toast = document.createElement('div');
    toast.className = 'finanpy-toast flex items-center gap-3 px-4 py-3 rounded-xl bg-success-700/90 text-white text-sm shadow-lg';
    toast.setAttribute('role', 'status');
    toast.textContent = 'Transações sincronizadas com sucesso';
    container.appendChild(toast);
    setTimeout(function () { toast.remove(); }, 4000);
  }

  // ---------------------------------------------------------------------------
  // 2) Drawer lateral
  // ---------------------------------------------------------------------------
  var drawer = document.getElementById('finanpy-drawer');
  var backdrop = document.getElementById('finanpy-drawer-backdrop');
  var openBtn = document.getElementById('drawer-open');
  var closeBtn = document.getElementById('drawer-close');

  function openDrawer() {
    if (!drawer) return;
    drawer.classList.remove('-translate-x-full');
    drawer.classList.add('translate-x-0');
    drawer.setAttribute('aria-hidden', 'false');
    if (openBtn) openBtn.setAttribute('aria-expanded', 'true');
    if (backdrop) {
      backdrop.classList.remove('opacity-0', 'pointer-events-none');
      backdrop.classList.add('opacity-100');
    }
    document.documentElement.style.overflow = 'hidden';
    // Foco no botão fechar para a11y
    if (closeBtn) {
      window.requestAnimationFrame(function () { closeBtn.focus(); });
    }
    trapFocus(drawer);
    var mainContent = document.querySelector('main');
    if (mainContent) mainContent.setAttribute('inert', '');
  }

  function closeDrawer() {
    if (!drawer) return;
    drawer.classList.add('-translate-x-full');
    drawer.classList.remove('translate-x-0');
    drawer.setAttribute('aria-hidden', 'true');
    if (openBtn) openBtn.setAttribute('aria-expanded', 'false');
    if (backdrop) {
      backdrop.classList.add('opacity-0', 'pointer-events-none');
      backdrop.classList.remove('opacity-100');
    }
    document.documentElement.style.overflow = '';
    var mainContent = document.querySelector('main');
    if (mainContent) mainContent.removeAttribute('inert');
    if (openBtn) openBtn.focus();
  }

  if (openBtn) openBtn.addEventListener('click', openDrawer);
  if (closeBtn) closeBtn.addEventListener('click', closeDrawer);
  if (backdrop) backdrop.addEventListener('click', closeDrawer);

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      if (drawer && drawer.getAttribute('aria-hidden') === 'false') {
        closeDrawer();
      }
      var openSheets = document.querySelectorAll('.finanpy-sheet:not(.hidden)');
      openSheets.forEach(function (s) { closeSheet(s); });
    }
  });

  // ---------------------------------------------------------------------------
  // 2.1) Focus trap utility
  // ---------------------------------------------------------------------------
  function trapFocus(container) {
    var focusable = container.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    );
    if (!focusable.length) return;
    var first = focusable[0];
    var last = focusable[focusable.length - 1];

    container.addEventListener('keydown', function (e) {
      if (e.key !== 'Tab') return;
      if (e.shiftKey) {
        if (document.activeElement === first) { e.preventDefault(); last.focus(); }
      } else {
        if (document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    });
  }

  // ---------------------------------------------------------------------------
  // 2.5) User menu dropdown (desktop)
  // ---------------------------------------------------------------------------
  var userMenuBtn = document.getElementById('user-menu-button');
  var userMenuPanel = document.getElementById('user-menu-panel');

  if (userMenuBtn && userMenuPanel) {
    userMenuBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      var isHidden = userMenuPanel.classList.toggle('hidden');
      userMenuBtn.setAttribute('aria-expanded', String(!isHidden));
    });

    document.addEventListener('click', function (e) {
      if (!userMenuPanel.classList.contains('hidden') &&
          !userMenuBtn.contains(e.target) && !userMenuPanel.contains(e.target)) {
        userMenuPanel.classList.add('hidden');
        userMenuBtn.setAttribute('aria-expanded', 'false');
      }
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !userMenuPanel.classList.contains('hidden')) {
        userMenuPanel.classList.add('hidden');
        userMenuBtn.setAttribute('aria-expanded', 'false');
        userMenuBtn.focus();
      }
    });
  }

  // ---------------------------------------------------------------------------
  // 3) Auto-dismiss de toasts
  // ---------------------------------------------------------------------------
  var toastContainer = document.getElementById('finanpy-toasts');
  if (toastContainer) {
    var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    setTimeout(function () {
      toastContainer.querySelectorAll('.finanpy-toast').forEach(function (t) {
        if (prefersReducedMotion) {
          t.remove();
          return;
        }
        t.style.transition = 'opacity 250ms ease, transform 250ms ease';
        t.style.opacity = '0';
        t.style.transform = 'translateY(8px)';
        setTimeout(function () { t.remove(); }, 280);
      });
    }, 5000);
  }

  // ---------------------------------------------------------------------------
  // 4) Bottom-sheet básico (open/close)
  // Markup esperado: .finanpy-sheet[id] com .finanpy-sheet-panel + .finanpy-sheet-backdrop
  // Triggers: [data-sheet-open="<id>"]; closers: [data-sheet-close]
  // ---------------------------------------------------------------------------
  function openSheet(id) {
    var sheet = document.getElementById(id);
    if (!sheet) return;
    sheet.classList.remove('hidden');
    requestAnimationFrame(function () {
      var panel = sheet.querySelector('.finanpy-sheet-panel');
      var bd = sheet.querySelector('.finanpy-sheet-backdrop');
      if (panel) panel.classList.replace('translate-y-full', 'translate-y-0');
      if (bd) bd.classList.replace('opacity-0', 'opacity-100');
    });
    document.documentElement.style.overflow = 'hidden';
    trapFocus(sheet);
    var mainContent = document.querySelector('main');
    if (mainContent) mainContent.setAttribute('inert', '');
  }

  function closeSheet(sheet) {
    if (!sheet) return;
    var panel = sheet.querySelector('.finanpy-sheet-panel');
    var bd = sheet.querySelector('.finanpy-sheet-backdrop');
    if (panel) panel.classList.replace('translate-y-0', 'translate-y-full');
    if (bd) bd.classList.replace('opacity-100', 'opacity-0');
    setTimeout(function () { sheet.classList.add('hidden'); }, 250);
    document.documentElement.style.overflow = '';
    var mainContent = document.querySelector('main');
    if (mainContent) mainContent.removeAttribute('inert');
  }

  document.addEventListener('click', function (e) {
    var openTarget = e.target.closest('[data-sheet-open]');
    if (openTarget) {
      e.preventDefault();
      openSheet(openTarget.getAttribute('data-sheet-open'));
      return;
    }
    var closeTarget = e.target.closest('[data-sheet-close]');
    if (closeTarget) {
      var sheet = closeTarget.closest('.finanpy-sheet');
      closeSheet(sheet);
    }
  });

  // Drag-to-close simples no handle do sheet
  document.querySelectorAll('.finanpy-sheet-handle').forEach(function (handle) {
    var startY = 0;
    var dy = 0;
    var panel = handle.closest('.finanpy-sheet-panel');
    if (!panel) return;

    handle.addEventListener('pointerdown', function (e) {
      startY = e.clientY;
      panel.style.transition = 'none';
      handle.setPointerCapture(e.pointerId);
    });

    handle.addEventListener('pointermove', function (e) {
      if (!startY) return;
      dy = Math.max(0, e.clientY - startY);
      panel.style.transform = 'translateY(' + dy + 'px)';
    });

    handle.addEventListener('pointerup', function () {
      panel.style.transition = '';
      if (dy > 80) {
        var sheet = panel.closest('.finanpy-sheet');
        closeSheet(sheet);
      }
      panel.style.transform = '';
      startY = 0;
      dy = 0;
    });
  });
})();
