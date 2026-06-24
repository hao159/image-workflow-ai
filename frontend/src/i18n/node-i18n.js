import { t } from './index.js'

// Vietnamese backend category name → stable catalog slug.
const CATEGORY_SLUG = {
  'Đầu vào': 'input',
  'AI': 'ai',
  'Biến đổi': 'transform',
  'Đầu ra': 'output',
  'Khác': 'other',
}

/** Translate node title; falls back to backend Vietnamese string. */
export function nodeTitle(meta) {
  return t(`nodes.${meta.type}.title`, meta.title)
}

/** Translate node description; falls back to backend Vietnamese string. */
export function nodeDescription(meta) {
  return t(`nodes.${meta.type}.description`, meta.description)
}

/** Translate category label; maps Vietnamese backend name via slug. */
export function nodeCategory(catVi) {
  const slug = CATEGORY_SLUG[catVi]
  return slug ? t(`category.${slug}`, catVi) : catVi
}

/** Translate a port label by port.name and direction ('inputs'|'outputs'); falls back to backend port.label. */
export function portLabel(type, port, direction) {
  return t(`nodes.${type}.${direction}.${port.name}`, port.label)
}

/** Translate a param label by param.name; falls back to backend param.label. */
export function paramLabel(type, param) {
  return t(`nodes.${type}.params.${param.name}.label`, param.label)
}

/** Translate a param supplement label; falls back to backend param.supplement_label. */
export function paramSupplementLabel(type, param) {
  return t(`nodes.${type}.params.${param.name}.supplement`, param.supplement_label)
}
