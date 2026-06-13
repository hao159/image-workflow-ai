import { memo } from 'react'
import { Handle, Position, useReactFlow, useNodeConnections } from '@xyflow/react'
import { categoryStyle } from '../node-category-styles.js'
import { resolveRunEffect } from '../ui-settings.js'
import { useRun } from '../RunContext.jsx'
import { useImageViewer } from '../ImageViewerContext.jsx'
import NodeParamField from './NodeParamField.jsx'
import { EyeIcon, PlayIcon, XIcon } from './icons.jsx'

// Card kết quả của node Lưu ảnh: thumbnail + tên file + nút xem ảnh (mở lightbox).
function FileResultCard({ url }) {
  const filename = url.split('/').pop()
  const { openViewer } = useImageViewer()
  const view = () => openViewer({ src: url, filename })
  return (
    <div className="wf-file-result nodrag">
      <img className="wf-file-thumb" src={url} alt={filename} onClick={view} />
      <div className="wf-file-info">
        <span className="wf-file-name" title={filename}>{filename}</span>
        <span className="wf-file-hint">Đã lưu vào outputs/</span>
      </div>
      <button type="button" className="icon-btn" title="Xem ảnh (phóng to)" onClick={view}>
        <EyeIcon size={13} />
      </button>
    </div>
  )
}

function WorkflowNode({ id, data }) {
  const { updateNodeData, deleteElements } = useReactFlow()
  const { runNode, running } = useRun()
  const { openViewer } = useImageViewer()
  const { meta, params = {}, status, preview, error, outputs, cached } = data
  const cat = categoryStyle(meta.category)

  // Ô "Mô tả ảnh" (is_image_label) làm phụ đề node — vai trò "đặt tên" node nguồn.
  const labelSpec = meta.params.find((p) => p.is_image_label)
  const nodeLabel = labelSpec ? (params[labelSpec.name] || '').trim() : ''

  // Cổng input nào đang được nối dây → để báo "đã nối" + đổi nhãn param bổ sung.
  const connections = useNodeConnections({ id, handleType: 'target' })
  const connectedHandles = new Set(connections.map((c) => c.targetHandle))
  const isConnected = (portName) => connectedHandles.has(`in-${portName}`)

  const setParam = (name, value) =>
    updateNodeData(id, { params: { ...params, [name]: value } })

  const textOutput = outputs
    ? Object.values(outputs).find((o) => o.dtype === 'text')?.value
    : null
  // Output của node Lưu ảnh là đường dẫn file → hiển thị card file thay vì text thô
  const outputFileUrl =
    typeof textOutput === 'string' && textOutput.startsWith('/api/outputs/') ? textOutput : null

  // URL ảnh GỐC full-res để xem/tải: lấy sha từ output ảnh → /api/cache-image/{sha}
  // (preview chỉ là thumbnail JPEG). Node chưa chạy (chưa có sha) → null, modal
  // tạm dùng preview cho tới khi có ảnh gốc.
  const imageOutput = outputs
    ? Object.values(outputs).find((o) => o.dtype === 'image')
    : null
  const fullResUrl = imageOutput?.sha ? `/api/cache-image/${imageOutput.sha}` : null

  const effect = status === 'running' ? resolveRunEffect(meta.category) : null

  return (
    <div
      className={`wf-node status-${status || 'idle'}${effect ? ` effect-${effect}` : ''}`}
      style={{ '--node-accent': cat.color }}
    >
      <div className="wf-node-header">
        <span className="wf-node-icon"><cat.Icon size={12} /></span>
        <span className="wf-node-title">{meta.title}</span>
        {cached && (
          <span className="wf-node-cache-badge" title="Dùng kết quả cache (không chạy lại, không gọi API)">
            ⚡ cache
          </span>
        )}
        <span className={`status-dot ${status || 'idle'}`} title={status || ''} />
        <button
          className="wf-node-run nodrag"
          title="Chạy tới node này (ép node này sinh mới, upstream dùng cache)"
          disabled={running}
          onClick={() => runNode(id)}
        >
          <PlayIcon size={11} />
        </button>
        <button
          className="wf-node-close nodrag"
          title="Xóa node"
          onClick={() => deleteElements({ nodes: [{ id }] })}
        >
          <XIcon size={13} />
        </button>
      </div>

      {nodeLabel && (
        <div className="wf-node-subtitle nodrag" title={nodeLabel}>{nodeLabel}</div>
      )}

      <div className="wf-node-ports">
        <div className="wf-node-inputs">
          {meta.inputs.map((port) => (
            <div className="wf-port" key={port.name}>
              <Handle
                type="target"
                position={Position.Left}
                id={`in-${port.name}`}
                style={{ top: 'auto' }}
                className={`wf-handle dtype-${port.dtype}${port.multiple ? ' multi' : ''}`}
              />
              <span className="wf-port-label">
                {port.label}
                {isConnected(port.name) ? (
                  <span className="wf-port-badge">✓ đã nối</span>
                ) : port.multiple ? (
                  ' (nhiều dây)'
                ) : port.required ? (
                  ''
                ) : (
                  ' (tùy chọn)'
                )}
              </span>
            </div>
          ))}
        </div>
        <div className="wf-node-outputs">
          {meta.outputs.map((port) => (
            <div className="wf-port out" key={port.name}>
              <span className="wf-port-label">{port.label}</span>
              <Handle
                type="source"
                position={Position.Right}
                id={`out-${port.name}`}
                style={{ top: 'auto' }}
                className={`wf-handle dtype-${port.dtype}`}
              />
            </div>
          ))}
        </div>
      </div>

      <div className="wf-node-params">
        {meta.params.map((spec) => {
          // Param "bổ sung" cho một cổng: khi cổng đó đã nối, đổi nhãn để rõ
          // giá trị này được ghép thêm vào prompt nối, không thay thế.
          const paramLabel =
            spec.supplement_for && isConnected(spec.supplement_for)
              ? spec.supplement_label || spec.label
              : spec.label
          return (
            <label className="wf-param" key={spec.name}>
              <span className="wf-param-label">{paramLabel}</span>
              <NodeParamField
                spec={spec}
                value={params[spec.name]}
                onChange={(v) => setParam(spec.name, v)}
              />
            </label>
          )
        })}
      </div>

      {/* Node Tải ảnh lên đã hiển thị ảnh ở ô upload (param) → bỏ preview trùng. */}
      {preview && meta.type !== 'load_image' && (
        <div className="wf-node-preview">
          <img
            src={preview}
            alt="kết quả"
            onClick={() => openViewer({ src: fullResUrl ?? preview, filename: `${meta.title}.png` })}
          />
        </div>
      )}
      {outputFileUrl && <FileResultCard url={outputFileUrl} />}
      {textOutput && !outputFileUrl && !preview && (
        <div className="wf-node-text-output">{textOutput}</div>
      )}
      {error && <div className="wf-node-error">{error}</div>}
    </div>
  )
}

export default memo(WorkflowNode)
