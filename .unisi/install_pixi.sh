#!/bin/bash

echo ">>> Installing Pixi..."
curl -fsSL https://pixi.sh/install.sh | sh
export PATH="$HOME/.pixi/bin:$PATH"
echo ">>> Pixi installed!"
