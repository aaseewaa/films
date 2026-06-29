/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_AVATAR_MAX_BYTES?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
