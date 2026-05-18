import type { Config } from 'tailwindcss';

/**
 * Дизайн-токены проекта.
 * Палитра: тёплый кремовый журнал.
 *  - бежевый фон #FAF6EE
 *  - тёмно-серый текст
 *  - винный акцент (deep wine)
 *  - сливочное масло (butter)
 *  - тёмный (только для страницы графа — контраст)
 */
const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Основная палитра
        cream: {
          50: '#FEFCF8',
          100: '#FAF6EE',  // ОСНОВНОЙ ФОН САЙТА
          200: '#F2EBDD',
          300: '#E8DFC8',
          400: '#D9CBAA',
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
        // Для страницы графа (тёмный режим)
        graph: {
          bg: '#1A1815',
          surface: '#252320',
          edge: '#4A4540',
          text: '#E8DFC8',
        },
        // Шапка и фон главной — как на макете
        'header-bar': '#4d4d4d',
      },
      fontFamily: {
        // Заголовки — serif, как в журнале
        serif: ['"Playfair Display"', '"Lora"', 'Georgia', 'serif'],
        // Основной текст
        sans: ['"Inter"', '"Geist"', 'system-ui', 'sans-serif'],
        // Моноширинный для tag и метаданных
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        // Журнальные крупные заголовки
        'display': ['clamp(2.5rem, 6vw, 4.5rem)', { lineHeight: '1.05', letterSpacing: '-0.02em' }],
        'h1': ['clamp(2rem, 4vw, 3rem)', { lineHeight: '1.1', letterSpacing: '-0.01em' }],
        'h2': ['clamp(1.5rem, 3vw, 2rem)', { lineHeight: '1.2' }],
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
