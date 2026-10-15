#!/usr/bin/env bash
# One-time setup per fresh session. Installs drawing + TTS deps and the voice model.
set -e
pip install --break-system-packages -q pycairo kokoro-onnx soundfile scipy numpy pillow
mkdir -p "$HOME/tts-models"
cd "$HOME/tts-models"
[ -f voices-v1.0.bin ] || curl -sSL -o voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
[ -f kokoro-v1.0.onnx ] || curl -sSL -o kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
which ffmpeg >/dev/null
echo "setup ok"
