/**
 * Lightweight input masks for FinanPy.
 *
 * Activates by data-attributes — no extra dependency. Add `data-mask="phone-br"`
 * on any <input> to format Brazilian phone numbers as the user types:
 *   (11) 9876-5432   (10 digits)
 *   (11) 98765-4321  (11 digits)
 *
 * The form's clean_phone strips formatting before saving, so the database
 * always stores digits-only.
 */
(function () {
  'use strict';

  function formatPhoneBr(digits) {
    digits = digits.replace(/\D/g, '').slice(0, 11);
    const len = digits.length;
    if (len === 0) return '';
    if (len < 3) return '(' + digits;
    if (len <= 6) return '(' + digits.slice(0, 2) + ') ' + digits.slice(2);
    if (len <= 10) {
      return '(' + digits.slice(0, 2) + ') ' + digits.slice(2, 6) + '-' + digits.slice(6);
    }
    return '(' + digits.slice(0, 2) + ') ' + digits.slice(2, 7) + '-' + digits.slice(7);
  }

  function bindPhoneMask(input) {
    if (input.dataset.maskBound === '1') return;
    input.dataset.maskBound = '1';

    const apply = () => {
      const next = formatPhoneBr(input.value);
      if (next !== input.value) {
        input.value = next;
      }
    };

    input.addEventListener('input', apply);
    apply(); // format pre-filled values on page load
  }

  function init() {
    document.querySelectorAll('input[data-mask="phone-br"]').forEach(bindPhoneMask);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
