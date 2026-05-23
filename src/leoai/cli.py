from rich.console import Console

from .assistant import LeoAIAssistant
from .config import get_settings


console = Console()


def main() -> None:
    console.print("[bold cyan]LeoAI iniciado[/bold cyan] | digite [bold]sair[/bold] para encerrar")

    try:
        settings = get_settings()
    except ValueError as exc:
        console.print(f"[bold red]Erro:[/bold red] {exc}")
        raise SystemExit(1) from exc

    assistant = LeoAIAssistant(settings)

    while True:
        user_input = console.input("\n[bold green]Você:[/bold green] ").strip()
        if user_input.lower() in {"sair", "exit", "quit"}:
            console.print("[dim]Encerrando LeoAI...[/dim]")
            break
        if not user_input:
            continue

        try:
            answer = assistant.ask(user_input)
        except Exception as exc:  # noqa: BLE001
            console.print(f"[bold red]Falha ao chamar o modelo:[/bold red] {exc}")
            continue

        console.print(f"[bold blue]LeoAI:[/bold blue] {answer}")
