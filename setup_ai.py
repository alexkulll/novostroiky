import hashlib
import os
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL_URL = 'https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/resolve/main/Qwen3-4B-Instruct-2507-Q4_K_M.gguf'
MODEL_HASH = '3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597'
ENGINE_URL = 'https://github.com/ggml-org/llama.cpp/releases/download/b11612/llama-b11612-bin-win-vulkan-x64.zip'
ENGINE_HASH = 'e62f0674970a70b007fa3c425d191ceacabbf02406d6c9ac8b6f27cd23abe9e9'
MODEL = ROOT / 'models' / 'Qwen3-4B-Instruct-2507-Q4_K_M.gguf'
ARCHIVE = ROOT / 'runtime' / 'llama-b11612.zip'
ENGINE = ROOT / 'runtime' / 'llama-b11612'


def checksum(path):
    digest = hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda: file.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def download(url, destination, expected):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        print(f'Проверяю {destination.name}...', flush=True)
        if checksum(destination) == expected:
            return
        raise RuntimeError(f'Контрольная сумма {destination} не совпала. Проверьте файл перед заменой.')
    temporary = destination.with_name(destination.name + '.part')
    print(f'Скачиваю {destination.name}...', flush=True)
    request = urllib.request.Request(url, headers={'User-Agent': 'Novostroiky/1.0'})
    digest = hashlib.sha256()
    with urllib.request.urlopen(request, timeout=90) as response, temporary.open('wb') as file:
        count = 0
        last_report = 0
        for block in iter(lambda: response.read(1024 * 1024), b''):
            file.write(block)
            digest.update(block)
            count += len(block)
            if count - last_report >= 250 * 1024 * 1024:
                print(f'Загружено: {count // (1024 * 1024)} МБ', flush=True)
                last_report = count
    if digest.hexdigest() != expected:
        raise RuntimeError(f'Контрольная сумма {destination.name} не совпала; файл не установлен.')
    os.replace(temporary, destination)


def main():
    if os.name != 'nt':
        raise RuntimeError('Эта сборка llama.cpp предназначена для Windows x64.')
    download(ENGINE_URL, ARCHIVE, ENGINE_HASH)
    download(MODEL_URL, MODEL, MODEL_HASH)
    if not (ENGINE / 'llama-server.exe').exists():
        ENGINE.mkdir(parents=True, exist_ok=True)
        root = ENGINE.resolve()
        with zipfile.ZipFile(ARCHIVE) as archive:
            for name in archive.namelist():
                if not (root / name).resolve().is_relative_to(root):
                    raise RuntimeError('В архиве обнаружен недопустимый путь.')
            archive.extractall(root)
    if not (ENGINE / 'llama-server.exe').is_file():
        raise RuntimeError('В архиве не найден llama-server.exe.')
    print('Модель и сервер готовы. Запустите приложение командой из README.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f'Ошибка установки: {exc}', flush=True)
        raise SystemExit(1) from exc
