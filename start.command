#!/bin/zsh
cd "${0:A:h}"
RESPONSE="$(curl --max-time 2 --fail --silent http://127.0.0.1:8766/api/config 2>/dev/null)"
if [[ "$RESPONSE" == *'"app_id": "korean-tts-compare"'* ]]; then
    open http://127.0.0.1:8766
    exit 0
fi
(sleep 1; open http://127.0.0.1:8766) &
exec .venvs/piper/bin/python serve.py --port 8766
