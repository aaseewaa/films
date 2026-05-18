-- ════════════════════════════════════════════════════════════════
-- Миграция: добавление backdrop (большого фонового кадра) для фильмов
-- ════════════════════════════════════════════════════════════════
--
-- ЧТО ДЕЛАЕТ:
-- 1. Добавляет колонку entity.primary_backdrop_url
--    Это широкоформатный кадр из фильма (16:9, ~1280x720), который
--    рисуется на всю ширину сверху карточки фильма.
--
-- 2. Проверяет что в media_role enum есть значения 'backdrop' и 'still'
--    Если нет — добавляет их.
--
-- ИДЕМПОТЕНТНО: можно запускать несколько раз, ничего не сломается.
-- ════════════════════════════════════════════════════════════════

-- 1) Добавляем primary_backdrop_url
ALTER TABLE public.entity
    ADD COLUMN IF NOT EXISTS primary_backdrop_url text;

-- 2) Проверяем media_role enum — нужны 'backdrop' и 'still'
-- ALTER TYPE ADD VALUE IF NOT EXISTS — Postgres 12+
DO $$
BEGIN
    -- Проверяем существование значения 'backdrop' в enum
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumtypid = 'public.media_role'::regtype
          AND enumlabel = 'backdrop'
    ) THEN
        ALTER TYPE public.media_role ADD VALUE 'backdrop';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumtypid = 'public.media_role'::regtype
          AND enumlabel = 'still'
    ) THEN
        ALTER TYPE public.media_role ADD VALUE 'still';
    END IF;
END$$;

-- 3) Проверим что media_source_kind поддерживает 'tmdb'
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumtypid = 'public.media_source_kind'::regtype
          AND enumlabel = 'tmdb'
    ) THEN
        ALTER TYPE public.media_source_kind ADD VALUE 'tmdb';
    END IF;
END$$;

-- 4) Проверим что всё на месте
SELECT
    column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'entity'
  AND column_name = 'primary_backdrop_url';
