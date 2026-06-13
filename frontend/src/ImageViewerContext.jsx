import { createContext, useCallback, useContext, useState } from 'react'
import ImageViewerModal from './components/ImageViewerModal.jsx'

// Lightbox dùng chung cho mọi node hiển thị ảnh. Component lồng sâu
// (App→ReactFlow→WorkflowNode→NodeParamField→ImageUploadField) không prop-drill
// qua ReactFlow được nên cấp qua Context — giống RunContext.jsx.
const ImageViewerContext = createContext({ openViewer: () => {} })

export function useImageViewer() {
  return useContext(ImageViewerContext)
}

export function ImageViewerProvider({ children }) {
  const [view, setView] = useState(null) // { src, filename } | null

  const openViewer = useCallback((v) => setView(v), [])
  const closeViewer = useCallback(() => setView(null), [])

  return (
    <ImageViewerContext.Provider value={{ openViewer }}>
      {children}
      {view && <ImageViewerModal view={view} onClose={closeViewer} />}
    </ImageViewerContext.Provider>
  )
}
