import { memo } from 'react'
import { Handle, Position, NodeResizer, useReactFlow, useNodeConnections } from '@xyflow/react'
import { categoryStyle } from '../node-category-styles.js'
import { resolveRunEffect } from '../ui-settings.js'
import { useRun } from '../RunContext.jsx'
import { useImageViewer } from '../ImageViewerContext.jsx'
import NodeParamField from './NodeParamField.jsx'
import { EyeIcon, PlayIcon, XIcon } from './icons.jsx'
import { useT } from '../i18n/use-t.js'
import { nodeTitle, portLabel, paramLabel, paramSupplementLabel } from '../i18n/node-i18n.js'

// Card kết quả của node Lưu ảnh: thumbnail + tên file + nút xem ảnh (mở lightbox).
function FileResultCard({ url }) {
  const filename = url.split('/').pop()
  const { openViewer } = useImageViewer()
  const { t } = useT()
  const view = () => openViewer({ src: url, filename })
  return (
    <div className="wf-file-result nodrag">
      <img className="wf-file-thumb" src={url} alt={filename} onClick={view} />
      <div className="wf-file-info">
        <span className="wf-file-name" title={filename}>{filename}</span>
        <span className="wf-file-hint">{t('node.savedToOutputs')}</span>
      </div>
      <button type="button" className="icon-btn" title={t('node.viewImageTitle')} onClick={view}>
        <EyeIcon size={13} />
      </button>
    </div>
  )
}

function WorkflowNode({ id, data, selected }) {
  const { updateNodeData, deleteElements } = useReactFlow()
  const { runNode, running } = useRun()
  const { openViewer } = useImageViewer()
  const { t, lang } = useT()
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
      {/* Kéo mép/góc để resize node; chỉ hiện control khi node được chọn. */}
      <NodeResizer minWidth={220} minHeight={120} isVisible={selected} />
      <div className="wf-node-header">
        <span className="wf-node-icon"><cat.Icon size={12} /></span>
        <span className="wf-node-title">{nodeTitle(meta)}</span>
        {cached && (
          <span className="wf-node-cache-badge" title={t('node.cacheBadgeTitle')}>
            {t('node.cacheBadgeLabel')}
          </span>
        )}
        <span className={`status-dot ${status || 'idle'}`} title={status || ''} />
        <button
          className="wf-node-run nodrag"
          title={t('node.runTitle')}
          disabled={running}
          onClick={() => runNode(id)}
        >
          <PlayIcon size={11} />
        </button>
        <button
          className="wf-node-close nodrag"
          title={t('node.deleteTitle')}
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
                {portLabel(meta.type, port, 'inputs')}
                {isConnected(port.name) ? (
                  <span className="wf-port-badge">{t('node.portConnected')}</span>
                ) : port.multiple ? (
                  t('node.portMultiple')
                ) : port.required ? (
                  ''
                ) : (
                  t('node.portOptional')
                )}
              </span>
            </div>
          ))}
        </div>
        <div className="wf-node-outputs">
          {meta.outputs.map((port) => (
            <div className="wf-port out" key={port.name}>
              <span className="wf-port-label">{portLabel(meta.type, port, 'outputs')}</span>
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
          const resolvedParamLabel =
            spec.supplement_for && isConnected(spec.supplement_for)
              ? paramSupplementLabel(meta.type, spec)
              : paramLabel(meta.type, spec)
          return (
            <label className="wf-param" key={spec.name}>
              <span className="wf-param-label">{resolvedParamLabel}</span>
              <NodeParamField
                spec={spec}
                nodeType={meta.type}
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
            alt={t('node.previewAlt')}
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
