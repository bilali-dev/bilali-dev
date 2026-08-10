#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Instalando dependencias Python..."
pip install -r requirements.txt

echo "Instalando navegador do Playwright (usado pelo monitor)..."
playwright install chromium

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Arquivo .env criado a partir de .env.example. Preencha suas credenciais antes de rodar."
else
  echo ".env ja existe, mantendo como esta."
fi

echo "Setup concluido."
