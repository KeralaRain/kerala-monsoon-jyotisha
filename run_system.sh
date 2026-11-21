#!/usr/bin/env bash
APP_DIR="/opt/monsoon_jyotisha_app"
if ! pgrep -f "streamlit run $APP_DIR/app.py" > /dev/null; then
    nohup "$APP_DIR/venv/bin/streamlit" run "$APP_DIR/app.py" --server.address=0.0.0.0 --server.port=8501 --server.headless=true > /tmp/monsoon_app.log 2>&1 &
    sleep 4
fi
xdg-open http://localhost:8501 >/dev/null 2>&1 || sensible-browser http://localhost:8501 >/dev/null 2>&1 || true
