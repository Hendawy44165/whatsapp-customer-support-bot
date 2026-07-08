import os
import sys

# Ensure backend directory is in the import path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from core_agent.nuit_bot import NuitBot


def main():
    print("Compiling Nuit Bot v2 graph...")
    bot = NuitBot()

    # 1. Print ASCII representation in terminal
    print("\n--- Graph Structure (ASCII) ---")
    try:
        bot.graph.get_graph().print_ascii()
    except Exception as e:
        print(f"Could not print ASCII: {e}")

    # 2. Save PNG image directly using LangGraph's draw_mermaid_png method
    png_path = os.path.join(backend_dir, "graph.png")
    print(f"\nGenerating visual graph image at '{png_path}'...")
    try:
        bot.graph.get_graph().draw_mermaid_png(output_file_path=png_path)
        print("Success! You can now open 'backend/graph.png' to see the visual flow.")
    except Exception as e:
        print(f"Could not generate PNG: {e}")
        print(
            "Make sure you have an active internet connection (to reach mermaid.ink) or pygraphviz installed."
        )


if __name__ == "__main__":
    main()
