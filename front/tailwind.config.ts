import type { Config } from 'tailwindcss';

/**
 * Дизайн-токены проекта.
 * Палитра FilmCine:
 *  - Alice Blue #E1EFF6 — фон сайта, графа, всех страниц
 *  - Blush Pop / Deep Mocha / Pearl Aqua / Lime Cream — плашки статей
 *  - Lime Cream #BCDE7F — полноэкранное меню
 */
const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx,css}'],
  theme: {
    extend: {
      colors: {
        // Палитра сайта
        palette: {
          alice: '#E1EFF6',
          blush: '#EBA7CD',
          mocha: '#422F33',
          aqua: '#81D8D0',
          lime: '#BCDE7F',
        },
        // Фон сайта: bg-site-bg / hover:bg-site-hover
        'site-bg': '#E1EFF6',
        'site-hover': '#97D2FB',
        // Tiffany Blue — логотип FMW, активные фильтры каталога
        tiffany: {
          DEFAULT: '#0ABAB5',
          dark: '#099a96',
        },
        // Фоновые оттенки (на базе Alice Blue)
        cream: {
          50: '#E1EFF6',
          100: '#E1EFF6',  // = site.bg
          200: '#C8DDE8',
          300: '#A8C5D4',
          400: '#8AADBE',
        },
        ink: {
          // Тёмно-серый для текста (не чисто чёрный — журнальный приём)
          50: '#71706B',
          100: '#605F5A',
          200: '#48473F',
          300: '#34332D',   // ОСНОВНОЙ ТЕКСТ
          400: '#1F1F1B',
          500: '#0F0F0D',
        },
        wine: {
          // Винный акцент для ссылок, кнопок
          400: '#A04555',
          500: '#8B2F40',   // ОСНОВНОЙ АКЦЕНТ
          600: '#70202F',
          700: '#561822',
        },
        butter: {
          // Сливочное масло — мягкий тёплый акцент
          200: '#FBE9B4',
          300: '#F6D77E',
          400: '#EFC358',   // АКЦЕНТ
          500: '#D9A938',
        },
        // Страница графа — тот же светлый фон
        graph: {
          bg: '#E1EFF6',
          surface: '#C8DDE8',
          edge: '#422F33',
          text: '#34332D',
        },
        'header-bar': '#E1EFF6', // = site.bg
      },
      fontFamily: {
        // Логотип и заголовки каталога — Pluffy Loon Outline Shadow
        pluffy: ['"Pluffy Loon Outline Shadow"', 'system-ui', 'sans-serif'],
        'pluffy-outline': ['"Pluffy Loon Outline Shadow"', 'system-ui', 'sans-serif'],
        // Заголовки — serif, как в журнале
        serif: ['"Playfair Display"', '"Lora"', 'Georgia', 'serif'],
        // Основной текст
        sans: ['"Inter"', '"Geist"', 'system-ui', 'sans-serif'],
        // Моноширинный для tag и метаданных
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        // Журнальные крупные заголовки
        display: ['clamp(2.5rem, 6vw, 4.5rem)', { lineHeight: '1.05', letterSpacing: '-0.02em' }],
        h1: ['clamp(2rem, 4vw, 3rem)', { lineHeight: '1.1', letterSpacing: '-0.01em' }],
        h2: ['clamp(1.5rem, 3vw, 2rem)', { lineHeight: '1.2' }],
      },
      maxWidth: {
        'reading': '68ch',   // Оптимальная ширина для длинных эссе
        'page': '1680px',
      },
      spacing: {
        '18': '4.5rem',
        '22': '5.5rem',
      },
      animation: {
        'fade-in': 'fadeIn 0.4s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
};

export default config;
