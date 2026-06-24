// Installs the JSON catalogs into the i18n core. Imported for its side effect
// from main.jsx before the app renders. Vite resolves the plain JSON imports.
import en from './locales/en.json'
import vi from './locales/vi.json'
import { registerCatalogs } from './index.js'

registerCatalogs(en, vi)
