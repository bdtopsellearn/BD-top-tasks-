#!/bin/bash
# ═══════════════════════════════════════════════════
#  BD TopSell Bot — Termux One-Click Setup
#  Run this ONCE to install everything
# ═══════════════════════════════════════════════════
echo ""
echo "🤖 BD TopSell Bot Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 1: Update Termux
echo "📦 Updating packages..."
pkg update -y 2>/dev/null
pkg upgrade -y 2>/dev/null

# Step 2: Install Python
echo "🐍 Installing Python..."
pkg install python -y 2>/dev/null

# Step 3: Install pip packages
echo "📥 Installing bot dependencies..."
pip install python-telegram-bot==20.7 --break-system-packages -q
pip install firebase-admin==6.4.0 --break-system-packages -q
pip install openpyxl==3.1.2 --break-system-packages -q

echo ""
echo "✅ Setup complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━"
echo "▶️  Now run: python bot.py"
echo "━━━━━━━━━━━━━━━━━━━━━━"
