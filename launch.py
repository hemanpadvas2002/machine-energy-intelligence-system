import subprocess
import sys
import os

def start_application():
    """
    BACKEND ENTRY POINT.
    Run this file to launch the entire Web Application.
    This file itself will not be visible in the user interface.
    """
    print("🚀 Initializing Digital Transformation Ecosystem...")
    print("---")
    
    # Internal app UI logic
    ui_script = "app.py"
    
    if not os.path.exists(ui_script):
        print(f"❌ Error: {ui_script} not found!")
        return

    # Trigger Streamlit Web server for the preview
    print(f"🖥️ Launching Dashboard and Backend Services...")
    try:
        # Launching the internal 'app.py' which handles fetcher and UI
        subprocess.run(["streamlit", "run", ui_script])
    except KeyboardInterrupt:
        print("\n🛑 Application stopped.")
    except Exception as e:
        print(f"❌ Runtime Error: {e}")

if __name__ == "__main__":
    start_application()
