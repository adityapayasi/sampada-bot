from pathlib import Path
import sys

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_manager import init_db

def main():
    print("🏛️  Sampada 2.0 e-Registry Co-Pilot")
    print("=" * 40)
    print("Initialising database...")
    init_db()
    print(f"Database ready at: {PROJECT_ROOT / 'data' / 'db' / 'sampada_state.db'}")
    print()
    print("To launch the dashboard, run:")
    print("   streamlit run app/streamlit_app.py")
    print()
    print("Make sure you have:")
    print("  1. Set GEMINI_API_KEY in .env or environment")
    print("  2. Installed Playwright browsers:  playwright install chromium")
    print("  3. Installed Python deps:  pip install -r requirements.txt")

if __name__ == "__main__":
    main()
