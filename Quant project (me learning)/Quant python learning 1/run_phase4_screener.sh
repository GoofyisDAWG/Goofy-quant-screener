#!/bin/bash
# ═══════════════════════════════════════════════════════════
#   GOOFY SCREENER — PHASE 4  (Mac/Linux launcher)
#   Multi-market screener + regime-aware verdict layer
#   Run: bash run_phase4_screener.sh
#   Or:  chmod +x run_phase4_screener.sh && ./run_phase4_screener.sh
# ═══════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo " ══════════════════════════════════════════════"
echo "   GOOFY SCREENER — PHASE 4 (regime-aware)"
echo "   Markets: 🇺🇸 US  |  🇦🇺 ASX  |  🇯🇵 JPX"
echo " ══════════════════════════════════════════════"
echo ""
echo " This will take ~5–15 minutes."
echo ""

# Try Anaconda first, then conda env, then system python
if command -v conda &>/dev/null; then
    # Use conda's base python
    PYTHON=$(conda run -n base which python 2>/dev/null || echo "python3")
elif [ -f "$HOME/anaconda3/bin/python" ]; then
    PYTHON="$HOME/anaconda3/bin/python"
elif [ -f "$HOME/miniconda3/bin/python" ]; then
    PYTHON="$HOME/miniconda3/bin/python"
else
    PYTHON="python3"
fi

echo " Using: $PYTHON"
echo ""

$PYTHON "$SCRIPT_DIR/goofy_screener_phase4.py" --market ALL

echo ""
echo " Done! Check screener_output/ for your Excel report."
echo " Look for: Goofy_Phase4_YYYY-MM-DD.xlsx"
echo " Open the 'Today's Trade List' tab first."
echo ""
