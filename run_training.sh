#!/bin/bash
# Run model training with crypto_env environment

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🚀 Starting Crypto Price Prediction Model Training..."
echo ""

# Activate environment and run training
/opt/anaconda3/envs/crypto_env/bin/python train_models.py

echo ""
echo "✓ Training complete! Check output above for results."
