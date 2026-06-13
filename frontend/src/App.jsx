import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  useReactFlow,
} from '@xyflow/react'
import Palette from './components/Palette.jsx'
import SettingsModal from './components/SettingsModal.jsx'
import WorkflowNode from './components/WorkflowNode.jsx'
import DeletableEdge from './components/DeletableEdge.jsx'
import ConnectNodeMenu from './components/ConnectNodeMenu.jsx'
import { RunContext } from './RunContext.jsx'
import { ImageViewerProvider } from './ImageViewerContext.jsx'
import {
  AlertIcon,
  CheckIcon,
  ChevronDownIcon,
  FolderIcon,
  GearIcon,
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
  const [showWorkflows, setShowWorkflows] = useState(false)
  // Khi kéo dây thả ra khoảng trống → mở menu chọn node để tạo + tự nối.
  const [connectMenu, setConnectMenu] = useState(null)
  const { screenToFlowPosition, updateNodeData } = useReactFlow()
  const wsRef = useRef(null)

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
      nds.map((n) => ({
        ...n,
        data: { ...n.data, meta: byType[n.data.meta.type] || n.data.meta },
      })),
    )
  }, [setNodes])

  useEffect(() => {
    fetchNodeTypes()
      .then(setNodeTypeMetas)
      .catch(() => setStatusMsg('⚠ Không kết nối được backend (cổng 8000). Hãy chạy backend trước.'))
    listWorkflows().then(setSavedList).catch(() => {})
  }, [])

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
        { id, type: 'wf', position, data: { meta, params: defaults, status: 'idle' } },
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
      setStatusMsg(target ? 'Đang chạy node...' : 'Đang chạy...')
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
            updateNodeData(ev.node_id, { status: 'error', error: ev.message })
            break
          case 'run_finished':
            runEnded = true
            setStatusMsg('✓ Hoàn thành')
            setRunning(false)
            setRunningNodeId(null)
            setEdgesAnimated(false)
            break
          case 'run_error':
            runEnded = true
            setStatusMsg(`✗ Lỗi: ${ev.message}`)
            setRunning(false)
            setRunningNodeId(null)
            setEdgesAnimated(false)
            break
        }
      }
      // WS đóng khi run chưa kết thúc = backend rớt/restart (vd uvicorn --reload
      // khi file .py đổi giữa lúc chạy) → báo lỗi rõ thay vì treo "Đang chạy...".
      ws.onclose = () => {
        if (runEnded) return
        setStatusMsg('✗ Mất kết nối backend giữa chừng (backend restart?). Chạy lại workflow.')
        setRunning(false)
        setRunningNodeId(null)
        setEdgesAnimated(false)
        setNodes((nds) =>
          nds.map((n) =>
            n.data.status === 'running'
              ? { ...n, data: { ...n.data, status: 'error', error: 'Mất kết nối khi đang chạy.' } }
              : n,
          ),
        )
      }
    },
    [running, nodes.length, buildPayload, setNodes, updateNodeData, setEdgesAnimated],
  )

  const run = useCallback(() => startRun({ target: null, force: [] }), [startRun])
  // ▶ trên node: chạy tới node đó + ép chính nó chạy lại (xem output / sinh ảnh mới).
  const runNode = useCallback((id) => startRun({ target: id, force: [id] }), [startRun])

  const stop = useCallback(() => {
    if (wsRef.current) wsRef.current.onclose = null // dừng chủ động — không báo "mất kết nối"
    wsRef.current?.close()
    setRunning(false)
    setRunningNodeId(null)
    setStatusMsg('Đã dừng.')
    setEdgesAnimated(false)
  }, [setEdgesAnimated])

  const clearCache = useCallback(async () => {
    try {
      await clearCacheApi()
      setStatusMsg('Đã xóa cache')
      setNodes((nds) => nds.map((n) => ({ ...n, data: { ...n.data, cached: false } })))
    } catch (e) {
      setStatusMsg(`✗ ${e.message}`)
    }
  }, [setNodes])

  // Giá trị context cho WorkflowNode (▶ node + biết trạng thái bận để disable).
  const runCtx = useMemo(() => ({ runNode, runningNodeId, running }), [runNode, runningNodeId, running])

  const save = useCallback(async () => {
    try {
      const { saved } = await saveWorkflow(buildPayload())
      setStatusMsg(`Đã lưu "${saved}"`)
      setSavedList(await listWorkflows())
    } catch (e) {
      setStatusMsg(`✗ ${e.message}`)
    }
  }, [buildPayload])

  const removeWorkflow = useCallback(async (name) => {
    if (!confirm(`Xóa workflow "${name}"?`)) return
    try {
      await deleteWorkflow(name)
      setSavedList(await listWorkflows())
      setStatusMsg(`Đã xóa "${name}"`)
    } catch (e) {
      setStatusMsg(`✗ ${e.message}`)
    }
  }, [])

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
        setStatusMsg(`Đã tải "${name}"`)
        setShowWorkflows(false)
      } catch (e) {
        setStatusMsg(`✗ ${e.message}`)
      }
    },
    [metaByType, setNodes, setEdges],
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
            placeholder="tên workflow"
          />
          <div className="toolbar-sep" />
          <button className="btn primary" onClick={run} disabled={running || nodes.length === 0}>
            <PlayIcon size={13} /> Chạy
          </button>
          {running && (
            <button className="btn danger" onClick={stop}><StopIcon size={11} /> Dừng</button>
          )}
          <button className="btn" onClick={save} disabled={nodes.length === 0}>
            <SaveIcon size={14} /> Lưu
          </button>
          <div className="wf-menu">
            <button className="btn" onClick={() => setShowWorkflows((s) => !s)}>
              <FolderIcon size={14} /> Workflows
              <ChevronDownIcon size={12} className={`chev${showWorkflows ? ' open' : ''}`} />
            </button>
            {showWorkflows && (
              <div className="wf-menu-panel">
                {savedList.length === 0 && <div className="wf-menu-empty">Chưa có workflow nào.</div>}
                {savedList.map((wf) => (
                  <div className="wf-menu-item" key={wf.name}>
                    <button className="wf-menu-open" title={`Cập nhật: ${wf.updated_at}`} onClick={() => load(wf.name)}>
                      <span className="wf-menu-name">{wf.name}</span>
                      <span className="wf-menu-date">{wf.updated_at}</span>
                    </button>
                    <button className="btn ghost danger" title="Xóa workflow" onClick={() => removeWorkflow(wf.name)}>
                      <TrashIcon size={13} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
          <button className="btn" onClick={() => setShowSettings(true)}>
            <GearIcon size={14} /> Cài đặt
          </button>
          <button
            className="btn ghost"
            title="Xóa cache output (lần chạy kế sẽ chạy lại tất cả, gọi lại API)"
            onClick={clearCache}
            disabled={running}
          >
            <TrashIcon size={14} /> Xóa cache
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
            title="Xóa toàn bộ node trên canvas"
            onClick={() => {
              setNodes([])
              setEdges([])
              setStatusMsg('')
            }}
          >
            <TrashIcon size={14} /> Xóa hết
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
            colorMode="dark"
            defaultEdgeOptions={{ type: 'deletable', style: { strokeWidth: 1.8 } }}
          >
            <Background gap={22} size={1.4} color="#272838" />
            <Controls />
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
