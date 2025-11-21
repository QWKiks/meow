import json
import re

import requests
from rich.console import Console
from rich.markdown import Markdown
from rich.markup import MarkupError, escape
from rich.panel import Panel
from rich.table import Table

from .tools import (
    agent_execute_shell,
    agent_list_directory,
    agent_read_file,
    agent_write_file,
    load_config,
    save_config,
)

PROVIDER_URLS = {
    "base": {
        "models": "https://text.pollinations.ai/models",
        "chat": "https://text.pollinations.ai/openai",
    },
    "openrouter": {
        "models": "https://openrouter.ai/api/v1/models",
        "chat": "https://openrouter.ai/api/v1/chat/completions",
    },
    "gemini": {
        "models": "https://generativelanguage.googleapis.com/v1beta/models",
        "chat": "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
    },
}

SYSTEM_PROMPT = """
You are a powerful CLI assistant running in a local environment. You can perform tasks by responding ONLY with a JSON object describing the tool you want to use. You can have a conversation with the user, but all your responses that are not a final answer MUST be in the specified JSON format.

NEVER write any text outside of the JSON object. Do not add explanations or any extra characters.

Available tools:
1. `list_directory`: Lists files and directories.
   - `path` (string, required): The path of the directory to list. Use "." for the current directory.

2. `read_file`: Reads the content of a file.
   - `path` (string, required): The path to the file.

3. `write_file`: Writes content to a file. This will overwrite the file if it exists.
   - `path` (string, required): The path to the file.
   - `content` (string, required): The content to write.

4. `execute_shell`: Executes a shell command.
   - `command` (string, required): The command to execute.

5. `ask_user`: Ask the user for clarification.
   - `question` (string, required): The question to ask the user.

6. `final_answer`: Give the final answer to the user and finish the task.
   - `text` (string, required): The final text response.

---
Best Practices:
- When writing HTML, create a separate .css file for styles and link it using a <link> tag in the HTML's <head>. Do not use inline <style> tags unless specifically asked.
- Always use the `write_file` tool to create or modify files. Do not use `execute_shell` with `echo` or other redirection operators for writing files.
- Think step-by-step. For a complex task like "create a website", first write the HTML file, then the CSS file, then link them.
---

Example of a user asking to list files:
User: "Show me the files in the current directory."
You:
{
    "tool": "list_directory",
    "args": {
        "path": "."
    }
}

Example of providing a final answer:
User: "Thank you!"
You:
{
    "tool": "final_answer",
    "args": {
        "text": "You're welcome! Let me know if you need anything else."
    }
}
"""

console = Console()


def print_help():
    table = Table(title="[bold white]Справка по командам[/bold white]")
    table.add_column("Команда", style="white", no_wrap=True)
    table.add_column("Описание", style="white")

    table.add_row("/help", "Показать это сообщение")
    table.add_row(
        "/models", "Показать список доступных моделей для текущего провайдера"
    )
    table.add_row(
        "/chat [имя_модели]",
        "Начать чат с ИИ-агентом. Если модель не указана, используется модель по умолчанию для текущего провайдера.",
    )
    table.add_row("/settings show", "Показать текущие настройки")
    table.add_row(
        "/settings set provider <имя_провайдера>",
        "Установить провайдера по умолчанию (base, openrouter, gemini)",
    )
    table.add_row(
        "/settings set api_key <имя_провайдера> <ключ>",
        "Установить API ключ для указанного провайдера",
    )
    table.add_row(
        "/settings set model <имя_провайдера> <модель>",
        "Установить модель по умолчанию для указанного провайдера",
    )
    table.add_row("/exit", "Выйти из программы")
    console.print(
        Panel(
            "Теперь в режиме /chat работает ИИ-агент, который может работать с файлами и выполнять команды. Просто дайте ему задачу.",
            title="[bold white]Режим Агента[/bold white]",
            border_style="white",
        )
    )
    console.print(table)


def get_available_models(config):
    """Получает и выводит модели в виде отформатированной таблицы."""
    provider = config.get("default_provider", "base")
    provider_config = config.get("providers", {}).get(provider, {})
    api_key = provider_config.get("api_key")
    models_url = PROVIDER_URLS.get(provider, {}).get("models")

    if not models_url:
        console.print(
            f"[bold red]URL для получения моделей у провайдера '{provider}' не найден.[/bold red]"
        )
        return []

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        with console.status("[white]Загрузка моделей...[/white]"):
            response = requests.get(models_url, headers=headers)
            response.raise_for_status()

        models_data = response.json()

        # Адаптация апи
        if provider == "openrouter":
            models = models_data.get("data", [])
        elif provider == "gemini":
            models = models_data.get("models", [])
        else:  # base
            models = models_data

        table = Table(
            title=f"[bold white]Доступные модели AI ({provider})[/bold white]",
            show_header=True,
            header_style="bold white",
        )
        table.add_column("Имя модели (name)", style="white", no_wrap=True)
        if provider != "gemini":
            table.add_column("Описание (description)")
            table.add_column("Тип", style="white")

        model_names = []
        if provider == "gemini":
            for model in models:
                model_name = model.get("name")
                if model_name:
                    table.add_row(escape(model_name))
                    model_names.append(model_name)
        else:
            official_models = [m for m in models if not m.get("community")]
            community_models = [m for m in models if m.get("community")]

            for model in official_models:
                model_name = model.get("name", "N/A")
                table.add_row(
                    escape(model_name),
                    model.get("description", "Нет описания"),
                    "Официальная",
                )
                model_names.append(model_name)
            if community_models:
                table.add_section()
                for model in community_models:
                    model_name = model.get("name", "N/A")
                    table.add_row(
                        escape(model_name),
                        model.get("description", "Нет описания"),
                        "Сообщество",
                    )
                    model_names.append(model_name)

        try:
            console.print(table)
        except MarkupError as e:
            console.print(
                f"[bold red]Ошибка рендеринга таблицы моделей: {escape(str(e))}[/bold red]"
            )
            console.print(
                "[bold yellow]Кароче это я не дофиксил, но ты можешь попробовать пофиксить сам, если хочешь[/bold yellow]"
            )

        return model_names

    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Ошибка при получении моделей:[/bold red] {e}")
        return []
    except json.JSONDecodeError:
        console.print(
            f"[bold red]Не удалось декодировать ответ от API моделей. Ответ:\n{response.text}[/bold red]"
        )
        return []


def handle_settings(args, config, available_models):
    """Обрабатывает команду /settings."""
    if not args or args[0] == "show":
        table = Table(title="[bold white]Текущие настройки[/bold white]")
        table.add_column("Настройка", style="white", no_wrap=True)
        table.add_column("Значение", style="white")

        default_provider = config.get("default_provider", "N/A")
        table.add_row("Провайдер по умолчанию", default_provider)

        for provider_name, provider_config in config.get("providers", {}).items():
            table.add_section()
            table.add_row(f"[bold]{provider_name}[/bold]", "")
            key_display = provider_config.get("api_key")
            if key_display and len(key_display) > 7:
                key_display = key_display[:4] + "..." + key_display[-3:]
            table.add_row("  API ключ", key_display or "Не установлен")
            table.add_row(
                "  Модель по умолчанию",
                provider_config.get("model") or "Не установлена",
            )

        console.print(table)

    elif len(args) >= 3 and args[0] == "set":
        key_to_set = args[1].lower()

        if key_to_set == "provider":
            provider_name = args[2].lower()
            if provider_name in config["providers"]:
                config["default_provider"] = provider_name
                save_config(config)
                console.print(
                    f"[bold #ffb6c1]✓ Провайдер по умолчанию установлен на '{provider_name}'.[/bold #ffb6c1]"
                )
            else:
                console.print(
                    f"[bold red]Ошибка: Провайдер '{provider_name}' не найден. Доступные: {', '.join(config['providers'].keys())}.[/bold red]"
                )

        elif key_to_set == "api_key":
            if len(args) >= 4:
                provider_name = args[2].lower()
                value = args[3]
                if provider_name in config["providers"]:
                    config["providers"][provider_name]["api_key"] = value
                    save_config(config)
                    console.print(
                        f"[bold #ffb6c1]✓ API ключ для '{provider_name}' сохранен.[/bold #ffb6c1]"
                    )
                else:
                    console.print(
                        f"[bold red]Ошибка: Провайдер '{provider_name}' не найден.[/bold red]"
                    )
            else:
                console.print(
                    "[bold red]Ошибка: Укажите провайдера и ключ. /settings set api_key <провайдер> <ключ>[/bold red]"
                )

        elif key_to_set == "model":
            if len(args) >= 4:
                provider_name = args[2].lower()
                value = " ".join(args[3:])
                if provider_name in config["providers"]:
                    config["providers"][provider_name]["model"] = value
                    save_config(config)
                    console.print(
                        f"[bold #ffb6c1]✓ Модель по умолчанию для '{provider_name}' установлена на '{value}'.[/bold #ffb6c1]"
                    )
                else:
                    console.print(
                        f"[bold red]Ошибка: Провайдер '{provider_name}' не найден.[/bold red]"
                    )
            else:
                console.print(
                    "[bold red]Ошибка: Укажите провайдера и модель. /settings set model <провайдер> <модель>[/bold red]"
                )

        else:
            console.print(f"[bold red]Неизвестная настройка '{key_to_set}'.[/bold red]")
    else:
        print_help()


def chat_with_bot(model_name, config):
    """Организует интерактивный чат с ИИ-агентом."""
    provider = config.get("default_provider", "base")
    provider_config = config.get("providers", {}).get(provider, {})
    api_key = provider_config.get("api_key")
    chat_url = PROVIDER_URLS.get(provider, {}).get("chat")

    if not chat_url:
        console.print(
            f"[bold red]URL для чата у провайдера '{provider}' не найден.[/bold red]"
        )
        return

    if not api_key:
        console.print(
            f"[bold red]API ключ для провайдера '{provider}' не найден. Пожалуйста, установите его с помощью команды /settings set api_key {provider} <ваш_ключ>[/bold red]"
        )
        return

    console.print(
        Panel(
            f"Начат чат с ИИ-агентом [bold white]{model_name}[/bold white] (провайдер: {provider}).\nВведите [white]/back[/white] или [white]/exit[/white] для выхода.",
            border_style="#ffb6c1",
        )
    )

    history = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        user_prompt = console.input("[bold white]Вы > [/bold white]")

        if user_prompt.lower() in ["/exit", "/back"]:
            break
        if not user_prompt:
            continue

        history.append({"role": "user", "content": user_prompt})

        while True:
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            data = {"model": model_name, "messages": history}
            if provider == "gemini":
                data = {
                    "contents": [
                        {
                            "parts": [{"text": m["content"]}]
                            for m in history
                            if m["role"] == "user"
                        }
                    ]
                }

            try:
                with console.status(
                    "[bold #ffb6c1]Агент думает...[/bold #ffb6c1]", spinner="dots8"
                ):
                    response = requests.post(chat_url, headers=headers, json=data)
                    response.raise_for_status()

                response_json = response.json()

                if provider == "gemini":
                    response_text = response_json["candidates"][0]["content"]["parts"][
                        0
                    ]["text"]
                else:
                    response_text = response_json["choices"][0]["message"]["content"]

                history.append({"role": "assistant", "content": response_text})

                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)

                if json_match:
                    json_str = json_match.group()
                    try:
                        action = json.loads(json_str)
                        tool_name = action.get("tool")
                        args = action.get("args", {})

                        arg_lines = []
                        for k, v in args.items():
                            v_str = str(v)
                            if len(v_str.splitlines()) > 5:
                                v_str = "\n".join(v_str.splitlines()[:5]) + "\n..."
                            arg_lines.append(f"{k}='{v_str}'")

                        arg_string_truncated = ", ".join(arg_lines)

                        console.print(
                            Panel(
                                f"→ [dim]Calling tool:[/] [bold #ffb6c1]{tool_name}[/bold #ffb6c1]({arg_string_truncated})",
                                border_style="#ffb6c1",
                                expand=False,
                            )
                        )

                        tool_result = ""
                        if tool_name == "list_directory":
                            tool_result = agent_list_directory(args.get("path", "."))
                        elif tool_name == "read_file":
                            tool_result = agent_read_file(args.get("path"))
                        elif tool_name == "write_file":
                            tool_result = agent_write_file(
                                args.get("path"), args.get("content")
                            )
                        elif tool_name == "execute_shell":
                            tool_result = agent_execute_shell(args.get("command"))
                        elif tool_name == "ask_user":
                            console.print(
                                Panel(
                                    args.get("question"),
                                    title="[bold #ffb6c1]Вопрос от Агента[/bold #ffb6c1]",
                                    border_style="#ffb6c1",
                                )
                            )
                            break
                        elif tool_name == "final_answer":
                            console.print(
                                Panel(
                                    Markdown(args.get("text")),
                                    border_style="#ffb6c1",
                                )
                            )
                            break
                        else:
                            tool_result = f"Неизвестный инструмент: {tool_name}"

                        if "успешно записан" in tool_result:
                            console.print(
                                Panel(tool_result, border_style="green", expand=False)
                            )
                        else:
                            console.print(tool_result)
                        history.append(
                            {"role": "user", "content": f"TOOL_RESULT: {tool_result}"}
                        )

                    except json.JSONDecodeError:
                        console.print(Markdown(response_text))
                        break
                else:
                    console.print(Markdown(response_text))
                    break

            except requests.exceptions.RequestException as e:
                console.print(f"[bold red]Ошибка при отправке запроса: {e}[/bold red]")
                break
            except (IndexError, KeyError) as e:
                console.print(
                    f"[bold red]Не удалось разобрать ответ от API: {e}[/bold red]\nОтвет: {response.text}"
                )
                break
