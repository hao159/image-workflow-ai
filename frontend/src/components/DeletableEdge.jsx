import { memo, useState } from 'react'
import { BaseEdge, EdgeLabelRenderer, getBezierPath, useReactFlow } from '@xyflow/react'
import { XIcon } from './icons.jsx'
import { useT } from '../i18n/use-t.js'

// Dây nối có nút xóa: rê chuột vào dây (hoặc chọn dây) → hiện nút × ở giữa
// để xóa nhanh, thay vì phải chọn rồi bấm phím Delete.
function DeletableEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
  style,
  selected,
}) {
  const { deleteElements } = useReactFlow()
  const { t } = useT()
  const [hovered, setHovered] = useState(false)
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  })

  const show = hovered || selected
  const enter = () => setHovered(true)
  const leave = () => setHovered(false)

  return (
    <>
      <BaseEdge id={id} path={edgePath} markerEnd={markerEnd} style={style} />
      {/* đường trong suốt rộng để bắt hover dễ hơn dây mảnh */}
      <path
        d={edgePath}
        fill="none"
        stroke="transparent"
        strokeWidth={18}
        className="wf-edge-hit"
        onMouseEnter={enter}
        onMouseLeave={leave}
      />
      <EdgeLabelRenderer>
        <button
          type="button"
          className={`wf-edge-delete nodrag nopan${show ? ' show' : ''}`}
          style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
          title={t('edge.delete')}
          onMouseEnter={enter}
          onMouseLeave={leave}
          onClick={(e) => {
            e.stopPropagation()
            deleteElements({ edges: [{ id }] })
          }}
        >
          <XIcon size={11} />
        </button>
      </EdgeLabelRenderer>
    </>
  )
}

export default memo(DeletableEdge)
