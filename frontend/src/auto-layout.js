import dagre from '@dagrejs/dagre'

// Kích thước mặc định khi node chưa được đo (chưa render lần nào hoặc thiếu measured).
const DEFAULT_W = 256
const DEFAULT_H = 180

// Dàn node tự động theo tầng (layered) bằng dagre, hướng trái → phải (LR) khớp
// với luồng pipeline của app (node nguồn bên trái, kết quả bên phải).
// Trả về mảng node mới với `position` đã cập nhật; KHÔNG đổi gì khác.
//
// dagre đặt gốc tọa độ ở TÂM node, còn React Flow ở GÓC trên-trái → trừ nửa
// width/height để quy đổi. Dùng kích thước thật của node (width/measured) nên
// node đã resize to/nhỏ vẫn được chừa đúng chỗ, không chồng lấn.
export function layoutNodes(nodes, edges, { rankdir = 'LR' } = {}) {
  if (nodes.length === 0) return nodes

  const g = new dagre.graphlib.Graph()
  g.setGraph({ rankdir, ranksep: 90, nodesep: 40, marginx: 20, marginy: 20 })
  g.setDefaultEdgeLabel(() => ({}))

  const sizeOf = (n) => ({
    width: n.width || n.measured?.width || DEFAULT_W,
    height: n.height || n.measured?.height || DEFAULT_H,
  })

  for (const n of nodes) {
    const { width, height } = sizeOf(n)
    g.setNode(n.id, { width, height })
  }
  for (const e of edges) {
    // Chỉ nối node thực sự tồn tại trên canvas (bỏ dây mồ côi nếu có).
    if (g.hasNode(e.source) && g.hasNode(e.target)) g.setEdge(e.source, e.target)
  }

  dagre.layout(g)

  return nodes.map((n) => {
    const pos = g.node(n.id)
    if (!pos) return n
    const { width, height } = sizeOf(n)
    return { ...n, position: { x: pos.x - width / 2, y: pos.y - height / 2 } }
  })
}
