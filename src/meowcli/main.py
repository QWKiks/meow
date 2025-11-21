import sys

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.text import Text

from .q1q import load_config, save_config
from .q2q import chat_with_bot, get_available_models, handle_settings


def gradient_color(start_color, end_color, steps):
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    start_rgb = hex_to_rgb(start_color)
    end_rgb = hex_to_rgb(end_color)
    gradient = []
    for i in range(steps):
        ratio = i / max(steps - 1, 1)
        rgb = tuple(
            int(start_rgb[j] + (end_rgb[j] - start_rgb[j]) * ratio) for j in range(3)
        )
        gradient.append(f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}")
    return gradient


def print_banner(console):
    gradient_text = [
        " ███╗   ███╗███████╗ ██████╗ ██╗    ██╗     ██████╗██╗     ██╗ ",
        "████╗ ████║██╔════╝██╔═══██╗██║    ██║    ██╔════╝██║     ██║",
        "██╔████╔██║█████╗  ██║   ██║██║ █╗ ██║    ██║     ██║     ██║",
        "██║╚██╔╝██║██╔══╝  ██║   ██║██║███╗██║    ██║     ██║     ██║",
        "██║ ╚═╝ ██║███████╗╚██████╔╝╚███╔███╔╝    ╚██████╗███████╗██║",
        "╚═╝     ╚═╝╚══════╝ ╚═════╝  ╚══╝╚══╝      ╚═════╝╚══════╝╚═╝",
    ]
    for line in gradient_text:
        colors = gradient_color("#ffb6c1", "#ffffff", len(line))
        text = Text()
        for char, color in zip(line, colors):
            text.append(char, style=f"bold {color}")
        console.print(text)
    console.print(
        Panel(
            "[bold white]https://github.com/QWKiks meow :3 ![/bold white]\nВведите [white]/help[/white] для просмотра доступных команд.",
            border_style="#ffb6c1",
        )
    )


def main():
    config = load_config()
    save_config(config)

    console = Console()
    print_banner(console)

    provider = config.get("default_provider")
    api_key = config.get("providers", {}).get(provider, {}).get("api_key")

    if not api_key:
        console.print(
            f"[bold #ffb6c1]API ключ для провайдера '{provider}' не найден. Пожалуйста, установите его с помощью команды /settings set api_key {provider} <ваш_ключ>[/bold #ffb6c1]"
        )

    provider_config = config.get("providers", {}).get(
        config.get("default_provider"), {}
    )
    default_model = provider_config.get("model")
    available_models = []

    while True:
        try:
            command_line = console.input("[bold #ffb6c1]>>> ").strip()
            if not command_line:
                continue

            parts = command_line.split()
            command = parts[0].lower()
            args = parts[1:]

            if command == "/help":
                console.print(
                    "[bold white]Доступные команды: /help, /settings, /models, /chat, /exit[/bold white]"
                )
            elif command == "/settings":
                handle_settings(args, config, available_models)
            elif command == "/models":
                available_models[:] = get_available_models(config)
            elif command == "/chat":
                current_provider = config.get("default_provider")
                provider_config = config.get("providers", {}).get(current_provider, {})
                model_name = args[0] if args else provider_config.get("model")
                if not model_name or model_name == "default-model":
                    console.print(
                        f"[bold red]Ошибка: Модель не указана и модель по умолчанию для '{current_provider}' не установлена. Укажите модель (например, /chat <имя_модели>) или установите ее через /settings.[/bold red]"
                    )
                    continue
                chat_with_bot(model_name, config)
            elif command == "/exit":
                console.print("[bold yellow]До свидания![/bold yellow]")
                break
            else:
                console.print(
                    f"[bold red]Неизвестная команда '{command}'. Введите /help для справки.[/bold red]"
                )
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Выход...[/bold yellow]")
            break
        except Exception as e:
            console.print(
                f"[bold red]Произошла непредвиденная ошибка: {escape(str(e))}[/bold red]"
            )
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
