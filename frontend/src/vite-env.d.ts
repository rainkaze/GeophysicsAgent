/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 后端 API 根地址，缺省为 http://127.0.0.1:8000/api/v1 */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
