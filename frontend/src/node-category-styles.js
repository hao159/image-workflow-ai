// Icon SVG + màu + hiệu ứng chạy mặc định theo nhóm node — dùng chung cho
// Palette (sidebar) và WorkflowNode (canvas). Tên nhóm phải khớp `category`
// trong metadata node ở backend (backend/app/nodes/).
import { ImportIcon, ExportIcon, SparklesIcon, SlidersIcon, WrenchIcon } from './components/icons.jsx'

export const CATEGORY_STYLES = {
  'Đầu vào': { Icon: ImportIcon, color: 'var(--cat-input)', runEffect: 'glow' },
  AI: { Icon: SparklesIcon, color: 'var(--cat-ai)', runEffect: 'scan' },
  'Biến đổi': { Icon: SlidersIcon, color: 'var(--cat-transform)', runEffect: 'pulse' },
  'Đầu ra': { Icon: ExportIcon, color: 'var(--cat-output)', runEffect: 'glow' },
}

export const DEFAULT_CATEGORY_STYLE = { Icon: WrenchIcon, color: 'var(--cat-misc)', runEffect: 'glow' }

export const categoryStyle = (category) => CATEGORY_STYLES[category] || DEFAULT_CATEGORY_STYLE
