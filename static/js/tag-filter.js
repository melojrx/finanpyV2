(function () {
  'use strict';

  document.querySelectorAll('[data-tag-filter-root]').forEach(function (root) {
    var trigger = root.querySelector('[data-tag-filter-trigger]');
    var panel = root.querySelector('[data-tag-filter-panel]');
    var summary = root.querySelector('[data-tag-filter-summary]');
    var chevron = root.querySelector('[data-tag-filter-chevron]');
    var options = Array.from(root.querySelectorAll('[data-tag-filter-option]'));

    function updateSummary() {
      var selected = options.filter(function (option) { return option.checked; });
      if (!selected.length) summary.textContent = 'Todas as tags';
      else if (selected.length === 1) summary.textContent = selected[0].dataset.tagName;
      else summary.textContent = selected.length + ' tags selecionadas';
    }

    function close() {
      panel.hidden = true;
      trigger.setAttribute('aria-expanded', 'false');
      chevron.classList.remove('rotate-180');
    }

    trigger.addEventListener('click', function () {
      var opening = panel.hidden;
      document.querySelectorAll('[data-tag-filter-panel]').forEach(function (other) {
        other.hidden = true;
      });
      document.querySelectorAll('[data-tag-filter-trigger]').forEach(function (other) {
        other.setAttribute('aria-expanded', 'false');
      });
      panel.hidden = !opening;
      trigger.setAttribute('aria-expanded', String(opening));
      chevron.classList.toggle('rotate-180', opening);
    });

    options.forEach(function (option) {
      option.addEventListener('change', updateSummary);
    });

    root.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
        close();
        trigger.focus();
      }
    });

    document.addEventListener('click', function (event) {
      if (!root.contains(event.target)) close();
    });

    updateSummary();
  });
})();
