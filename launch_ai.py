import json
import os
import subprocess
import sys
import time
import threading
import urllib.error
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SERVER=ROOT/'runtime'/'llama-b11612'/'llama-server.exe'
MODEL=ROOT/'models'/'Qwen3-4B-Instruct-2507-Q4_K_M.gguf'
MODELS='http://127.0.0.1:8080/v1/models'
_START_LOCK = threading.Lock()

def server_status():
    try:
        with urllib.request.urlopen(MODELS,timeout=2) as response: data=json.load(response)
        return 'ready' if any(x.get('id')=='local-qwen' for x in data.get('data',[])) else 'occupied'
    except (OSError,ValueError): return 'absent'

def _start_server():
    status=server_status()
    if status=='occupied': raise RuntimeError('Порт 8080 занят другим сервером модели. Освободите порт и запустите ещё раз.')
    if status=='absent':
        if not SERVER.is_file() or not MODEL.is_file(): raise RuntimeError('Не найден сервер llama.cpp или файл модели. Проверьте папки runtime и models.')
        log=(ROOT/'runtime'/'llama-server.log').open('ab')
        process=subprocess.Popen([str(SERVER),'-m',str(MODEL),'--alias','local-qwen','--host','127.0.0.1','--port','8080','-ngl','24','-c','4096'],cwd=str(SERVER.parent),stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        print('Запускаю локальную модель; первый запуск может занять минуту...',flush=True)
        for _ in range(120):
            time.sleep(1)
            if process.poll() is not None: raise RuntimeError('Сервер модели завершился. Проверьте runtime/llama-server.log.')
            if server_status()=='ready': break
        else:
            process.terminate()
            raise RuntimeError('Сервер модели не ответил. Проверьте runtime/llama-server.log.')
        log.close()
def ensure_server():
    with _START_LOCK:
        _start_server()


def main():
    ensure_server()
    print('Локальная модель готова. Запускаю приложение...',flush=True)
    return subprocess.call([sys.executable,'-m','streamlit','run',str(ROOT/'app.py'),'--server.address','127.0.0.1','--browser.gatherUsageStats','false'],cwd=str(ROOT))

if __name__=='__main__':
    try: sys.exit(main())
    except Exception as exc:
        print('Ошибка:',exc,file=sys.stderr)
        sys.exit(1)
