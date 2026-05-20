#!/bin/bash
set -e
echo "=== 建置前端 ==="
cd frontend
npm install
npm run build
echo "=== 前端建置完成 ==="
cd ..
echo "=== 複製前端到後端 ==="
cp -r frontend/dist backend/dist
echo "=== 全部完成 ==="
