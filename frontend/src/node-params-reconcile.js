// Đồng bộ params của node theo metadata mới nhất.
//
// Bối cảnh: giá trị param của node được "chụp" một lần lúc tạo node (App.addNode)
// rồi giữ nguyên. Param 'select' động (vd "provider" — cấu hình model) lấy options
// từ DB tại thời điểm /api/node-types. Nếu node được tạo lúc CHƯA có cấu hình nào,
// provider bị chụp là "" (rỗng). Khi người dùng thêm cấu hình rồi gọi refreshNodeTypes,
// chỉ `meta` được cập nhật (dropdown có options mới) còn `params` vẫn giữ "".
//
// Hệ quả: <select> controlled có value="" nhưng options=["Cấu hình A"] sẽ HIỂN THỊ
// option đầu (trông như đã chọn) trong khi value thật vẫn "". Người dùng chọn lại đúng
// option đang hiển thị → không phát onChange → value vẫn "" → chạy node báo
// model_config_not_found.
//
// Hàm này gán lại mọi param 'select' có giá trị không còn nằm trong options mới
// (rỗng, hoặc trỏ tới cấu hình đã bị xoá/đổi tên) về default mới (options[0]).
// Trả về cùng tham chiếu cũ khi không có gì đổi để tránh re-render thừa.
export function reconcileParams(params, meta) {
  const cur = params || {}
  if (!meta || !Array.isArray(meta.params)) return cur
  let next = null // chỉ clone khi thực sự có thay đổi
  for (const spec of meta.params) {
    if (spec.ptype !== 'select') continue
    const opts = spec.options || []
    if (opts.length === 0) continue // chưa có lựa chọn nào → giữ nguyên
    if (opts.includes(cur[spec.name])) continue // giá trị vẫn hợp lệ
    if (!next) next = { ...cur }
    next[spec.name] = opts.includes(spec.default) ? spec.default : opts[0]
  }
  return next || cur
}
