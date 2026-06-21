#!/bin/bash
# macOS: chuột phải file này → Open (1 lần) để gỡ cờ quarantine của macOS cho toàn bộ
# bundle rồi chạy Image Workflow. Tránh việc macOS hỏi "cho phép" từng file .so/.dylib.
# Chỉ cần làm 1 lần sau khi tải/giải nén; các lần sau mở thẳng ImageWorkflow cũng được.
DIR="$(cd "$(dirname "$0")" && pwd)"
echo "Đang gỡ cờ quarantine cho Image Workflow..."
xattr -cr "$DIR" 2>/dev/null || true
echo "Đang khởi động Image Workflow..."
exec "$DIR/ImageWorkflow"
