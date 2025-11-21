import json
import os
import platform
import subprocess

PLATFORM_NAME = OS_NAME = platform.system()
if PLATFORM_NAME == "Linux":
    OS_NAME = platform.freedesktop_os_release()["PRETTY_NAME"]

match PLATFORM_NAME:
    case "Windows":
        CONFIG_FILE = os.path.join(
            os.environ.get("APPDATA", ""), "meowcli", "config.json"
        )
    case "Linux":
        CONFIG_FILE = os.path.join(
            os.environ.get("XDG_CONFIG_HOME", ""), "meowcli", "config.json"
        )
    case "Darwin":
        CONFIG_FILE = os.path.expanduser(
            "~/Library/Application Support/meowcli/config.json"
        )


def load_config():
    """
    Загружает конфигурацию из config.json.
    """
    default_config = {
        "default_provider": "base",
        "providers": {
            "base": {"api_key": "", "model": "default-model"},
            "openrouter": {"api_key": "", "model": "default-model"},
            "gemini": {"api_key": "", "model": "default-model"},
        },
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                for provider in default_config["providers"]:
                    if provider not in config["providers"]:
                        config["providers"][provider] = default_config["providers"][
                            provider
                        ]
                return config
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            return default_config
    return default_config


def save_config(config):
    """
    Сейв конфига.
    """
    config_dir = os.path.dirname(CONFIG_FILE)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


def agent_list_directory(path):
    try:
        files = os.listdir(path)
        return f"Содержимое директории '{path}':\n" + "\n".join(files)
    except Exception as e:
        return f"Ошибка при просмотре директории: {e}"


def agent_read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return f"Содержимое файла '{path}':\n```\n{content}\n```"
    except Exception as e:
        return f"Ошибка при чтении файла: {e}"


def agent_write_file(path, content):
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Файл '{path}' успешно записан."
    except Exception as e:
        return f"Ошибка при записи файла: {e}"


def agent_execute_shell(command):
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, encoding="utf-8"
        )
        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        if not output:
            output = "Команда выполнена без вывода."
        return output
    except Exception as e:
        return f"Ошибка при выполнении команды: {e}"
