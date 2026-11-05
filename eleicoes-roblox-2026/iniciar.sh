#!/usr/bin/env bash
# Eleições Roblox 2026 — inicia o site no Linux/Mac
cd "$(dirname "$0")" || exit 1
echo "Instalando dependências..."
python3 -m pip install -r requirements.txt
echo
echo "Abra http://127.0.0.1:5000 no navegador (Ctrl+C para sair)."
python3 app.py
