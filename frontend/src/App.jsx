import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  ControlButton,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  useReactFlow,
} from '@xyflow/react'
import Palette from './components/Palette.jsx'
import SettingsModal from './components/SettingsModal.jsx'
import WorkflowBrowserModal from './components/workflow-browser-modal.jsx'
import ImageLibraryModal from './components/image-library-modal.jsx'
import WorkflowNode from './components/WorkflowNode.jsx'
import DeletableEdge from './components/DeletableEdge.jsx'
import ConnectNodeMenu from './components/ConnectNodeMenu.jsx'
import { RunContext } from './RunContext.jsx'
import { ImageViewerProvider } from './ImageViewerContext.jsx'
import { useToast } from './ToastContext.jsx'
import { useT } from './i18n/use-t.js'
import { LANG_OPTIONS, translateError } from './i18n/index.js'
import { layoutNodes } from './auto-layout.js'
import { reconcileParams } from './node-params-reconcile.js'
import {
  AlertIcon,
  CheckIcon,
  FolderIcon,
  GearIcon,
  ImageIcon,
  LayoutIcon,
  PlayIcon,
  SaveIcon,
  StopIcon,
  TrashIcon,
} from './components/icons.jsx'
import {
  clearCache as clearCacheApi,
  deleteWorkflow,
  fetchNodeTypes,
  listWorkflows,
  loadWorkflow,
  openRunSocket,
  saveWorkflow,
} from './api.js'
import { resolveTheme } from './ui-settings.js'

const nodeTypes = { wf: WorkflowNode }
const edgeTypes = { deletable: DeletableEdge }
let nodeCounter = 1

export default function App() {
  const [nodeTypeMetas, setNodeTypeMetas] = useState([])
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [workflowName, setWorkflowName] = useState('my-workflow')
  const [savedList, setSavedList] = useState([])
  const [running, setRunning] = useState(false)
  // id node đang chạy riêng lẻ (▶ trên node); null khi chạy tổng hoặc đang rảnh
  const [runningNodeId, setRunningNodeId] = useState(null)
  const [statusMsg, setStatusMsg] = useState('')
  const [showSettings, setShowSettings] = useState(false)
  const [showWorkflowBrowser, setShowWorkflowBrowser] = useState(false)
  const [showImageLibrary, setShowImageLibrary] = useState(false)
  // Khi kéo dây thả ra khoảng trống → mở menu chọn node để tạo + tự nối.
  const [connectMenu, setConnectMenu] = useState(null)
  // Theme hiện tại ('light'|'dark') để React Flow đổi colorMode + màu lưới nền
  // theo Sáng/Tối. Nghe sự kiện 'iw-theme-change' (phát từ ui-settings.applyTheme).
  const [theme, setTheme] = useState(resolveTheme)
  const { screenToFlowPosition, updateNodeData, fitView } = useReactFlow()
  const toast = useToast()
  const { lang, setLang, t } = useT()
  const wsRef = useRef(null)

  useEffect(() => {
    const onThemeChange = (e) => setTheme(e.detail?.theme || resolveTheme())
    window.addEventListener('iw-theme-change', onThemeChange)
    return () => window.removeEventListener('iw-theme-change', onThemeChange)
  }, [])

  // React Flow <Background> nhận màu trực tiếp (không qua CSS var) → đọc token
  // --rf-grid đã đổi theo theme từ computed style, tính lại mỗi khi theme đổi.
  const gridColor = useMemo(() => {
    if (typeof window === 'undefined') return '#262b35'
    return getComputedStyle(document.documentElement).getPropertyValue('--rf-grid').trim() || '#262b35'
  }, [theme])

  const metaByType = useMemo(
    () => Object.fromEntries(nodeTypeMetas.map((m) => [m.type, m])),
    [nodeTypeMetas],
  )

  // Tải lại metadata node (options select model thay đổi theo cấu hình trong DB)
  // và cập nhật cả các node đang nằm trên canvas.
  const refreshNodeTypes = useCallback(async () => {
    const metas = await fetchNodeTypes()
    setNodeTypeMetas(metas)
    const byType = Object.fromEntries(metas.map((m) => [m.type, m]))
    setNodes((nds) =>
      nds.map((n) => {
        const meta = byType[n.data.meta.type] || n.data.meta
        // Khi cấu hình model thay đổi, options của param 'select' động đổi theo →
        // gán lại giá trị param đã cũ/rỗng về default mới (xem reconcileParams).
        return { ...n, data: { ...n.data, meta, params: reconcileParams(n.data.params, meta) } }
      }),
    )
  }, [setNodes])

  useEffect(() => {
    fetchNodeTypes()
      .then(setNodeTypeMetas)
      .catch(() => {
        const m = '⚠ ' + t('status.backendUnavailable')
        setStatusMsg(m) // giữ trong chip vì là lỗi BỀN (backend chưa chạy)
        toast.error(t('status.backendUnavailable'))
      })
    listWorkflows().then(setSavedList).catch(() => {})
  }, [toast])

  const findPort = useCallback(
    (nodeId, handleId, direction) => {
      const node = nodes.find((n) => n.id === nodeId)
      const meta = node && metaByType[node.data.meta.type]
      if (!meta) return null
      const name = (handleId || '').replace(/^(in|out)-/, '')
      const ports = direction === 'out' ? meta.outputs : meta.inputs
      return ports.find((p) => p.name === name) ?? null
    },
    [nodes, metaByType],
  )

  const isValidConnection = useCallback(
    (conn) => {
      const src = findPort(conn.source, conn.sourceHandle, 'out')
      const dst = findPort(conn.target, conn.targetHandle, 'in')
      return !!src && !!dst && src.dtype === dst.dtype && conn.source !== conn.target
    },
    [findPort],
  )

  const onConnect = useCallback(
    (conn) => {
      const dst = findPort(conn.target, conn.targetHandle, 'in')
      setEdges((eds) =>
        addEdge(
          { ...conn, type: 'deletable' },
          // cổng multiple nhận nhiều dây; cổng thường chỉ 1 dây — dây mới thay dây cũ
          dst?.multiple
            ? eds
            : eds.filter((e) => !(e.target === conn.target && e.targetHandle === conn.targetHandle)),
        ),
      )
    },
    [findPort, setEdges],
  )

  const addNode = useCallback(
    (type, position) => {
      const meta = metaByType[type]
      if (!meta) return null
      const id = `${type}_${nodeCounter++}_${Math.random().toString(36).slice(2, 7)}`
      const defaults = Object.fromEntries(meta.params.map((p) => [p.name, p.default]))
      setNodes((nds) => [
        ...nds,
        // width mặc định 256px = cơ sở cho NodeResizer; kéo mép sẽ ghi đè width/height.
        { id, type: 'wf', position, width: 256, data: { meta, params: defaults, status: 'idle' } },
      ])
      return id
    },
    [metaByType, setNodes],
  )

  const onDrop = useCallback(
    (event) => {
      event.preventDefault()
      const type = event.dataTransfer.getData('application/x-node-type')
      addNode(type, screenToFlowPosition({ x: event.clientX, y: event.clientY }))
    },
    [addNode, screenToFlowPosition],
  )

  // Bấm item trong sidebar → thêm node và tự nối vào node đang chọn
  // (không thì node thêm gần nhất) thành một flow, kiểu n8n.
  const addNodeFromPalette = useCallback(
    (type) => {
      const meta = metaByType[type]
      if (!meta) return
      const source = nodes.findLast((n) => n.selected) || nodes[nodes.length - 1]

      let position
      let connection = null
      if (source) {
        // nối cổng ra đầu tiên của node nguồn với cổng vào cùng dtype của node mới
        const srcMeta = source.data.meta
        const out = srcMeta.outputs.find((o) => meta.inputs.some((i) => i.dtype === o.dtype))
        const inp = out && meta.inputs.find((i) => i.dtype === out.dtype)
        if (inp) {
          connection = { source: source.id, sourceHandle: `out-${out.name}`, targetHandle: `in-${inp.name}` }
        }
        position = { x: source.position.x + 310, y: source.position.y }
      } else {
        const center = screenToFlowPosition({ x: window.innerWidth / 2, y: window.innerHeight / 2 })
        position = { x: center.x - 125, y: center.y - 80 }
      }
      // tránh đè lên node đã có
      while (nodes.some((n) => Math.abs(n.position.x - position.x) < 60 && Math.abs(n.position.y - position.y) < 60)) {
        position = { x: position.x, y: position.y + 100 }
      }

      const id = addNode(type, position)
      if (id && connection) {
        setEdges((eds) => addEdge({ ...connection, target: id, type: 'deletable' }, eds))
      }
    },
    [metaByType, nodes, addNode, screenToFlowPosition, setEdges],
  )

  // Kéo dây từ một cổng rồi thả ra khoảng trống (không trúng cổng nào) → mở
  // menu liệt kê node tương thích để tạo node mới và tự nối luôn (kiểu n8n).
  const onConnectEnd = useCallback(
    (event, connectionState) => {
      if (connectionState.isValid) return // đã nối được vào cổng khác → onConnect lo
      const fromHandle = connectionState.fromHandle
      if (!fromHandle?.nodeId) return
      const dir = fromHandle.type === 'source' ? 'out' : 'in'
      const port = findPort(fromHandle.nodeId, fromHandle.id, dir)
      if (!port) return
      const { clientX, clientY } = 'changedTouches' in event ? event.changedTouches[0] : event
      setConnectMenu({
        screenX: clientX,
        screenY: clientY,
        flowPosition: screenToFlowPosition({ x: clientX, y: clientY }),
        fromNodeId: fromHandle.nodeId,
        fromHandleId: fromHandle.id,
        fromType: fromHandle.type, // 'source' (kéo từ cổng ra) | 'target' (kéo từ cổng vào)
        dtype: port.dtype,
      })
    },
    [findPort, screenToFlowPosition],
  )

  // Node tương thích = có cổng cùng dtype ở phía đối diện hướng kéo.
  const compatibleNodeTypes = useMemo(() => {
    if (!connectMenu) return []
    return nodeTypeMetas.filter((m) => {
      const ports = connectMenu.fromType === 'source' ? m.inputs : m.outputs
      return ports.some((p) => p.dtype === connectMenu.dtype)
    })
  }, [connectMenu, nodeTypeMetas])

  // Chọn node trong menu thả-dây: tạo node tại điểm thả rồi nối cổng tương thích.
  const createConnectedNode = useCallback(
    (type) => {
      if (!connectMenu) return
      const meta = metaByType[type]
      if (!meta) return
      const ports = connectMenu.fromType === 'source' ? meta.inputs : meta.outputs
      const newPort = ports.find((p) => p.dtype === connectMenu.dtype)
      // Kéo từ cổng vào (target) → node mới mọc bên trái, lùi đủ bề ngang node.
      const pos =
        connectMenu.fromType === 'source'
          ? { x: connectMenu.flowPosition.x, y: connectMenu.flowPosition.y - 20 }
          : { x: connectMenu.flowPosition.x - 256, y: connectMenu.flowPosition.y - 20 }
      const newId = addNode(type, pos)
      if (newId && newPort) {
        const edge =
          connectMenu.fromType === 'source'
            ? {
                source: connectMenu.fromNodeId,
                sourceHandle: connectMenu.fromHandleId,
                target: newId,
                targetHandle: `in-${newPort.name}`,
              }
            : {
                source: newId,
                sourceHandle: `out-${newPort.name}`,
                target: connectMenu.fromNodeId,
                targetHandle: connectMenu.fromHandleId,
              }
        setEdges((eds) => addEdge({ ...edge, type: 'deletable' }, eds))
      }
      setConnectMenu(null)
    },
    [connectMenu, metaByType, addNode, setEdges],
  )

  const buildPayload = useCallback(
    () => ({
      name: workflowName,
      nodes: nodes.map((n) => ({
        id: n.id,
        type: n.data.meta.type,
        params: n.data.params,
        position: n.position,
        // Lưu kích thước (ưu tiên giá trị đã resize, fallback kích thước đo được)
        // để mở lại workflow giữ nguyên node to/nhỏ người dùng đã chỉnh.
        width: n.width ?? n.measured?.width,
        height: n.height ?? n.measured?.height,
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        sourceHandle: (e.sourceHandle || '').replace(/^out-/, ''),
        target: e.target,
        targetHandle: (e.targetHandle || '').replace(/^in-/, ''),
      })),
    }),
    [workflowName, nodes, edges],
  )

  // Bật/tắt hiệu ứng "kiến bò" trên toàn bộ dây nối trong lúc workflow chạy
  const setEdgesAnimated = useCallback(
    (animated) => setEdges((eds) => eds.map((e) => ({ ...e, animated }))),
    [setEdges],
  )

  // Mở socket chạy workflow. `target` = chạy tới node đó (+ tổ tiên), `force` =
  // danh sách node ép chạy lại (bỏ qua cache). Dùng chung cho chạy tổng + ▶ node.
  const startRun = useCallback(
    ({ target = null, force = [] } = {}) => {
      if (running || nodes.length === 0) return
      setRunning(true)
      setRunningNodeId(target)
      setStatusMsg(target ? t('status.runningNode') : t('status.running'))
      setEdgesAnimated(true)
      // Chạy tổng → reset hết. Chạy 1 node → chỉ reset node đó (giữ preview các
      // node khác; node cache-hit upstream tự cập nhật qua event node_finished).
      setNodes((nds) =>
        nds.map((n) =>
          target && n.id !== target
            ? n
            : { ...n, data: { ...n.data, status: 'idle', preview: null, error: null, outputs: null, cached: false } },
        ),
      )

      const ws = openRunSocket()
      wsRef.current = ws
      let runEnded = false // true khi đã nhận run_finished/run_error — onclose sau đó là bình thường
      ws.onopen = () =>
        ws.send(JSON.stringify({ workflow: buildPayload(), target, force }))
      ws.onmessage = (msg) => {
        const ev = JSON.parse(msg.data)
        switch (ev.type) {
          case 'node_started':
            updateNodeData(ev.node_id, { status: 'running' })
            break
          case 'node_finished':
            updateNodeData(ev.node_id, {
              status: 'done',
              preview: ev.preview || null,
              outputs: ev.outputs || null,
              cached: ev.cached || false,
            })
            break
          case 'node_error':
            updateNodeData(ev.node_id, { status: 'error', error: translateError(ev.code, ev.message, ev.params) })
            break
          case 'run_finished':
            runEnded = true
            setStatusMsg('') // chip chỉ giữ trạng thái đang chạy → xong thì ẩn
            toast.success(t('status.done'))
            setRunning(false)
            setRunningNodeId(null)
            setEdgesAnimated(false)
            break
          case 'run_error': {
            runEnded = true
            const runErrMsg = translateError(ev.code, ev.message, ev.params)
            setStatusMsg('✗ ' + t('status.error', undefined, { message: runErrMsg })) // giữ lỗi trong chip (bền) + toast
            toast.error(t('status.error', undefined, { message: runErrMsg }))
            setRunning(false)
            setRunningNodeId(null)
            setEdgesAnimated(false)
            break
          }
        }
      }
      // WS đóng khi run chưa kết thúc = backend rớt/restart (vd uvicorn --reload
      // khi file .py đổi giữa lúc chạy) → báo lỗi rõ thay vì treo "Đang chạy...".
      ws.onclose = () => {
        if (runEnded) return
        setStatusMsg('✗ ' + t('status.connLost'))
        toast.error(t('status.connLost'))
        setRunning(false)
        setRunningNodeId(null)
        setEdgesAnimated(false)
        setNodes((nds) =>
          nds.map((n) =>
            n.data.status === 'running'
              ? { ...n, data: { ...n.data, status: 'error', error: t('status.connLostNode') } }
              : n,
          ),
        )
      }
    },
    [running, nodes.length, buildPayload, setNodes, updateNodeData, setEdgesAnimated, toast],
  )

  const run = useCallback(() => startRun({ target: null, force: [] }), [startRun])
  // ▶ trên node: chạy tới node đó + ép chính nó chạy lại (xem output / sinh ảnh mới).
  const runNode = useCallback((id) => startRun({ target: id, force: [id] }), [startRun])

  const stop = useCallback(() => {
    if (wsRef.current) wsRef.current.onclose = null // dừng chủ động — không báo "mất kết nối"
    wsRef.current?.close()
    setRunning(false)
    setRunningNodeId(null)
    setStatusMsg('')
    toast.info(t('status.stopped'))
    setEdgesAnimated(false)
  }, [setEdgesAnimated, toast])

  const clearCache = useCallback(async () => {
    try {
      await clearCacheApi()
      setStatusMsg('')
      toast.success(t('status.cacheCleared'))
      setNodes((nds) => nds.map((n) => ({ ...n, data: { ...n.data, cached: false } })))
    } catch (e) {
      setStatusMsg('')
      toast.error(e.message)
    }
  }, [setNodes, toast])

  // Dàn node tự động (trái→phải) cho gọn rồi fit khung nhìn. requestAnimationFrame
  // để React Flow kịp đo lại kích thước node mới đặt trước khi fitView.
  const arrange = useCallback(() => {
    setNodes((nds) => layoutNodes(nds, edges))
    requestAnimationFrame(() => fitView({ padding: 0.2, duration: 300 }))
  }, [setNodes, edges, fitView])

  // Giá trị context cho WorkflowNode (▶ node + biết trạng thái bận để disable).
  const runCtx = useMemo(() => ({ runNode, runningNodeId, running }), [runNode, runningNodeId, running])

  const doSave = useCallback(async (overwrite) => {
    try {
      const { saved } = await saveWorkflow(buildPayload(), { overwrite })
      setStatusMsg('')
      toast.success(t('status.saved', undefined, { name: saved }))
      setSavedList(await listWorkflows())
    } catch (e) {
      // Backend trả 409 (tên đã tồn tại) → hỏi xác nhận ghi đè rồi lưu lại.
      if (e.code === 'exists') {
        if (confirm(t('app.confirmOverwrite', undefined, { name: workflowName }))) {
          await doSave(true)
        } else {
          toast.info(t('status.saveCancelled'))
        }
        return
      }
      setStatusMsg('')
      toast.error(e.message)
    }
  }, [buildPayload, workflowName, toast])

  const save = useCallback(() => doSave(false), [doSave])

  const removeWorkflow = useCallback(async (name) => {
    if (!confirm(t('app.confirmDeleteWorkflow', undefined, { name }))) return
    try {
      await deleteWorkflow(name)
      setSavedList(await listWorkflows())
      setStatusMsg('')
      toast.success(t('status.workflowDeleted', undefined, { name }))
    } catch (e) {
      setStatusMsg('')
      toast.error(e.message)
    }
  }, [toast])

  const load = useCallback(
    async (name) => {
      if (!name) return
      try {
        const wf = await loadWorkflow(name)
        setWorkflowName(wf.name || name)
        setEdges([])
        setNodes(
          wf.nodes
            .filter((n) => metaByType[n.type])
            .map((n) => ({
              id: n.id,
              type: 'wf',
              position: { x: n.position?.x ?? 0, y: n.position?.y ?? 0 },
              // Khôi phục kích thước đã lưu; workflow cũ chưa có size → mặc định 256px.
              width: n.width ?? 256,
              ...(n.height ? { height: n.height } : {}),
              data: { meta: metaByType[n.type], params: n.params, status: 'idle' },
            })),
        )
        setEdges(
          wf.edges.map((e, i) => ({
            id: e.id || `e${i}`,
            type: 'deletable',
            source: e.source,
            sourceHandle: `out-${e.sourceHandle}`,
            target: e.target,
            targetHandle: `in-${e.targetHandle}`,
          })),
        )
        setStatusMsg('')
        toast.success(t('status.workflowLoaded', undefined, { name }))
        setShowWorkflowBrowser(false)
      } catch (e) {
        setStatusMsg('')
        toast.error(e.message)
      }
    },
    [metaByType, setNodes, setEdges, toast],
  )

  // Tô màu status chip theo nội dung thông báo (✓ xanh, ✗/⚠ đỏ, đang chạy xanh dương)
  const statusKind = running ? 'busy' : statusMsg.startsWith('✓') ? 'ok' : /^[✗⚠]/.test(statusMsg) ? 'err' : ''

  return (
    <ImageViewerProvider>
    <div className="app">
      <Palette nodeTypes={nodeTypeMetas} onAdd={addNodeFromPalette} />
      <div className="canvas-wrap">
        <div className="toolbar">
          <input
            className="wf-name"
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value)}
            placeholder={t('toolbar.workflowNamePlaceholder')}
          />
          <div className="toolbar-sep" />
          <button className="btn primary" onClick={run} disabled={running || nodes.length === 0}>
            <PlayIcon size={13} /> {t('toolbar.run')}
          </button>
          {running && (
            <button className="btn danger" onClick={stop}><StopIcon size={11} /> {t('toolbar.stop')}</button>
          )}
          <button className="btn" onClick={save} disabled={nodes.length === 0}>
            <SaveIcon size={14} /> {t('toolbar.save')}
          </button>
          <button
            className="btn"
            onClick={() => { listWorkflows().then(setSavedList).catch(() => {}); setShowWorkflowBrowser(true) }}
          >
            <FolderIcon size={14} /> {t('toolbar.open')}
          </button>
          <button className="btn" onClick={() => setShowImageLibrary(true)}>
            <ImageIcon size={14} /> {t('toolbar.imageLibrary')}
          </button>
          <div className="lang-seg" role="group" aria-label={t('toolbar.language')}>
            {LANG_OPTIONS.map((o) => (
              <button
                key={o.value}
                type="button"
                className={`lang-seg-btn${lang === o.value ? ' active' : ''}`}
                onClick={() => setLang(o.value)}
              >
                {o.value.toUpperCase()}
              </button>
            ))}
          </div>
          <button className="btn" onClick={() => setShowSettings(true)}>
            <GearIcon size={14} /> {t('toolbar.settings')}
          </button>
          <button
            className="btn ghost"
            title={t('toolbar.clearCacheTitle')}
            onClick={clearCache}
            disabled={running}
          >
            <TrashIcon size={14} /> {t('toolbar.clearCache')}
          </button>
          <div className="toolbar-spacer" />
          {statusMsg && (
            <span className={`status-chip ${statusKind}`} title={statusMsg}>
              {statusKind === 'busy' && <span className="spinner" />}
              {statusKind === 'ok' && <CheckIcon size={13} />}
              {statusKind === 'err' && <AlertIcon size={13} />}
              {statusMsg.replace(/^[✓✗⚠]\s*/, '')}
            </span>
          )}
          <button
            className="btn ghost danger"
            title={t('toolbar.clearCanvasTitle')}
            onClick={() => {
              setNodes([])
              setEdges([])
              setStatusMsg('')
            }}
          >
            <TrashIcon size={14} /> {t('toolbar.clearCanvas')}
          </button>
        </div>
        <RunContext.Provider value={runCtx}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onConnectEnd={onConnectEnd}
            isValidConnection={isValidConnection}
            onDrop={onDrop}
            onDragOver={(e) => {
              e.preventDefault()
              e.dataTransfer.dropEffect = 'move'
            }}
            fitView
            deleteKeyCode={['Delete', 'Backspace']}
            colorMode={theme}
            defaultEdgeOptions={{ type: 'deletable', style: { strokeWidth: 1.8 } }}
          >
            <Background gap={22} size={1.4} color={gridColor} />
            <Controls>
              <ControlButton
                onClick={arrange}
                title={t('toolbar.autoLayoutTitle')}
                disabled={nodes.length === 0}
              >
                <LayoutIcon size={15} />
              </ControlButton>
            </Controls>
            <MiniMap pannable zoomable />
          </ReactFlow>
        </RunContext.Provider>
      </div>
      {showSettings && (
        <SettingsModal
          onClose={() => setShowSettings(false)}
          onChanged={() => refreshNodeTypes().catch(() => {})}
        />
      )}
      {showWorkflowBrowser && (
        <WorkflowBrowserModal
          workflows={savedList}
          onLoad={load}
          onDelete={removeWorkflow}
          onClose={() => setShowWorkflowBrowser(false)}
        />
      )}
      {showImageLibrary && (
        <ImageLibraryModal onClose={() => setShowImageLibrary(false)} />
      )}
      {connectMenu && (
        <ConnectNodeMenu
          screenX={connectMenu.screenX}
          screenY={connectMenu.screenY}
          items={compatibleNodeTypes}
          onPick={createConnectedNode}
          onClose={() => setConnectMenu(null)}
        />
      )}
    </div>
    </ImageViewerProvider>
  )
}
