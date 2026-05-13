/**
 * FinanPy — Utilitários financeiros globais
 */
class CurrencyFormatter {
  static format(amount, options = {}) {
    const { currency = 'BRL', locale = 'pt-BR', showSymbol = true, decimals = 2 } = options;
    return new Intl.NumberFormat(locale, {
      style: showSymbol ? 'currency' : 'decimal',
      currency,
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(amount);
  }

  static formatInput(input) {
    if (!input.value) return;
    let value = input.value.replace(/[^\d,]/g, '');
    if (value.includes(',')) {
      const parts = value.split(',');
      if (parts.length > 2) value = parts.slice(0, -1).join('') + ',' + parts[parts.length - 1];
      if (parts[1] && parts[1].length > 2) value = parts[0] + ',' + parts[1].substring(0, 2);
    }
    const parts = value.split(',');
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    input.value = parts.join(',');
  }

  static unformat(formattedValue) {
    if (!formattedValue) return '0';
    return formattedValue.replace(/[R$\s]/g, '').replace(/\./g, '').replace(',', '.');
  }

  static parseBrazilianNumber(value) {
    return parseFloat(this.unformat(value)) || 0;
  }
}

class FinancialUtils {
  static formatCurrency(amount, currency = 'BRL') {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency }).format(amount);
  }

  static formatNumber(number, decimals = 2) {
    return new Intl.NumberFormat('pt-BR', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(number);
  }

  static formatDate(date) {
    return new Intl.DateTimeFormat('pt-BR').format(new Date(date));
  }
}

window.CurrencyFormatter = CurrencyFormatter;
window.FinancialUtils = FinancialUtils;
