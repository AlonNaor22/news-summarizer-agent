"""Entry point for the News Summarizer Agent CLI."""

from cli.commands import process_command
from cli.display import display_welcome
from cli.state import AgentState


def run(state: AgentState | None = None) -> None:
    """Show the welcome screen and loop on user input until quit/EOF."""
    if state is None:
        state = AgentState()

    display_welcome()

    while state.is_running:
        try:
            user_input = input("\n> ").strip()
            if user_input:
                process_command(state, user_input)

        except KeyboardInterrupt:
            print("\n\nInterrupted. Type 'quit' to exit.")

        except EOFError:
            state.is_running = False

        except (ValueError, KeyError, IndexError) as e:
            print(f"\nError: {e}")
            print("Something went wrong. Please try again.")


def main() -> None:
    """Console-script entry point (referenced from pyproject.toml)."""
    run()


if __name__ == "__main__":
    main()
