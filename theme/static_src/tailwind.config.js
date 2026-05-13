/**
 * FinanPy Tailwind config — migrado da configuração inline em
 * templates/base.html durante a Sprint 8 / M0 (Mobile-First).
 *
 * Paleta preservada do CDN. Adições do M0:
 *  - alias `primary-action` para WCAG AA (texto branco em fundo escuro)
 *  - utilitários `safe-area` (pt-safe, pb-safe, mb-nav, etc) via plugin
 *  - utilitário `font-tnum` para tabular numerals em valores monetários
 *  - heights variáveis (h-bottom-nav, h-top-bar)
 *
 * Refs:
 *  - docs/mobile-architecture.md §2.4
 *  - docs/lighthouse-baseline/transactions.md (issue color-contrast)
 */

const plugin = require('tailwindcss/plugin');

module.exports = {
    darkMode: 'class',
    content: [
        // Templates do app theme (theme/templates/**/*.html)
        '../templates/**/*.html',
        // Templates globais do projeto (BASE_DIR/templates/**/*.html)
        '../../templates/**/*.html',
        // Templates de outros apps (BASE_DIR/<app>/templates/**/*.html)
        '../../**/templates/**/*.html',
        // Forms e widgets renderizados via Python (rótulos dinâmicos)
        '../../**/forms.py',
        '../../**/forms/**/*.py',
    ],
    theme: {
        extend: {
            colors: {
                // Cor primária do app (paleta sky do Tailwind)
                primary: {
                    50: '#f0f9ff',
                    100: '#e0f2fe',
                    200: '#bae6fd',
                    300: '#7dd3fc',
                    400: '#38bdf8',
                    500: '#0ea5e9',
                    600: '#0284c7', // ⚠️ NÃO usar com texto branco (4.09:1 — abaixo de WCAG AA)
                    700: '#0369a1', // ✅ Acessível com texto branco (5.39:1)
                    800: '#075985',
                    900: '#0c4a6e',
                    950: '#082f49',
                },
                /**
                 * Alias semântico para botões/CTAs com texto branco.
                 * Aponta para `primary-700` para garantir WCAG AA.
                 * Use `bg-primary-action` em vez de `bg-primary-600` quando
                 * o texto for branco. Hover: `hover:bg-primary-800`.
                 */
                'primary-action': '#0369a1', // ≡ primary-700 — 5.39:1 com #fff

                secondary: {
                    50: '#f8fafc',
                    100: '#f1f5f9',
                    200: '#e2e8f0',
                    300: '#cbd5e1',
                    400: '#94a3b8',
                    500: '#64748b',
                    600: '#475569',
                    700: '#334155',
                    800: '#1e293b',
                    900: '#0f172a',
                    950: '#020617',
                },
                success: {
                    50: '#f0fdf4',
                    100: '#dcfce7',
                    200: '#bbf7d0',
                    300: '#86efac',
                    400: '#4ade80',
                    500: '#22c55e',
                    600: '#16a34a',
                    700: '#15803d',
                    800: '#166534',
                    900: '#14532d',
                    950: '#052e16',
                },
                danger: {
                    50: '#fef2f2',
                    100: '#fee2e2',
                    200: '#fecaca',
                    300: '#fca5a5',
                    400: '#f87171',
                    500: '#ef4444',
                    600: '#dc2626',
                    700: '#b91c1c',
                    800: '#991b1b',
                    900: '#7f1d1d',
                    950: '#450a0a',
                },
                warning: {
                    50: '#fffbeb',
                    100: '#fef3c7',
                    200: '#fde68a',
                    300: '#fcd34d',
                    400: '#fbbf24',
                    500: '#f59e0b',
                    600: '#d97706',
                    700: '#b45309',
                    800: '#92400e',
                    900: '#78350f',
                    950: '#451a03',
                },
                // Tons usados no fundo dark-theme
                dark: {
                    50: '#f8fafc',
                    100: '#f1f5f9',
                    200: '#e2e8f0',
                    300: '#cbd5e1',
                    400: '#94a3b8',
                    500: '#64748b',
                    600: '#475569',
                    700: '#334155',
                    800: '#1e293b',
                    900: '#0f172a',
                    950: '#020617',
                },
            },
            backgroundImage: {
                'gradient-financial': 'linear-gradient(135deg, #0ea5e9 0%, #0369a1 50%, #164e63 100%)',
                'gradient-financial-dark': 'linear-gradient(135deg, #075985 0%, #0c4a6e 50%, #082f49 100%)',
                'gradient-success': 'linear-gradient(135deg, #22c55e 0%, #16a34a 50%, #15803d 100%)',
                'gradient-danger': 'linear-gradient(135deg, #ef4444 0%, #dc2626 50%, #b91c1c 100%)',
                'gradient-warning': 'linear-gradient(135deg, #f59e0b 0%, #d97706 50%, #b45309 100%)',
            },
            fontFamily: {
                sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
            },
            // Heights da Sprint 8 (sincronizados com tokens.css)
            height: {
                'top-bar': 'var(--top-bar-h)',
                'bottom-nav': 'var(--bottom-nav-h)',
                'touch': 'var(--touch-min)',
            },
            minHeight: {
                'touch': 'var(--touch-min)',
            },
            minWidth: {
                'touch': 'var(--touch-min)',
            },
            spacing: {
                'safe-top': 'var(--safe-top)',
                'safe-bottom': 'var(--safe-bottom)',
                'safe-left': 'var(--safe-left)',
                'safe-right': 'var(--safe-right)',
                'bottom-nav': 'var(--bottom-nav-h)',
                'top-bar': 'var(--top-bar-h)',
                'content-pb': 'var(--content-pb)',
            },
            borderRadius: {
                'sheet': 'var(--radius-sheet)',
                'card-mobile': 'var(--radius-card)',
            },
            boxShadow: {
                'sheet': 'var(--shadow-sheet)',
                'fab': 'var(--shadow-fab)',
            },
            transitionTimingFunction: {
                'out-quart': 'var(--ease-out-quart)',
            },
            animation: {
                'fade-in': 'fadeIn 0.5s ease-in-out',
                'slide-up': 'slideUp 0.3s ease-out',
                'bounce-gentle': 'bounceGentle 2s infinite',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
                slideUp: {
                    '0%': { transform: 'translateY(20px)', opacity: '0' },
                    '100%': { transform: 'translateY(0)', opacity: '1' },
                },
                bounceGentle: {
                    '0%, 100%': { transform: 'translateY(0)' },
                    '50%': { transform: 'translateY(-5px)' },
                },
            },
        },
    },
    plugins: [
        require('@tailwindcss/forms'),
        require('@tailwindcss/typography'),
        require('@tailwindcss/aspect-ratio'),

        /**
         * Plugin custom: utilitários `safe-area` para iOS (notch/home indicator)
         * e `font-tnum` para valores monetários alinhados.
         *
         * Exemplos:
         *   <header class="pt-safe">       — padding-top = safe-area-inset-top
         *   <nav class="pb-safe">          — padding-bottom = safe-area-inset-bottom
         *   <main class="pb-content">      — padding-bottom = bottom-nav + safe-area
         *   <span class="font-tnum">R$...  — tabular numerals
         */
        plugin(function ({ addUtilities }) {
            addUtilities({
                '.pt-safe': { 'padding-top': 'env(safe-area-inset-top, 0px)' },
                '.pb-safe': { 'padding-bottom': 'env(safe-area-inset-bottom, 0px)' },
                '.pl-safe': { 'padding-left': 'env(safe-area-inset-left, 0px)' },
                '.pr-safe': { 'padding-right': 'env(safe-area-inset-right, 0px)' },
                '.mt-safe': { 'margin-top': 'env(safe-area-inset-top, 0px)' },
                '.mb-safe': { 'margin-bottom': 'env(safe-area-inset-bottom, 0px)' },
                '.pb-content': { 'padding-bottom': 'var(--content-pb)' },
                '.font-tnum': { 'font-variant-numeric': 'tabular-nums' },
                // Touch targets WCAG / Apple HIG / Material
                '.touch-min': {
                    'min-height': 'var(--touch-min)',
                    'min-width': 'var(--touch-min)',
                },
            });
        }),
    ],
};
