# main.py (versão debug)
import subprocess
import sys
import os
import traceback


def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


if __name__ == "__main__":
    try:
        base_path = get_base_path()
        python_executable = sys.executable
        streamlit_runner_path = os.path.join(base_path, "run_streamlit.py")
        app_path = os.path.join(base_path, "app_coletor.py")

        print(f"Base path: {base_path}")
        print(f"Python executable: {python_executable}")
        print(f"Streamlit runner exists: {os.path.exists(streamlit_runner_path)}")
        print(f"App path exists: {os.path.exists(app_path)}")

        command = [
            python_executable,
            streamlit_runner_path,
            app_path,
            "--server.port=8501",
            "--server.headless=true",
            "--global.developmentMode=false"
        ]

        print(f"Command: {' '.join(command)}")

        # Execute com timeout para não travar
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30
        )

        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")

    except subprocess.TimeoutExpired:
        print("Processo timeout - pode estar funcionando!")
    except Exception as e:
        print(f"Erro: {e}")
        traceback.print_exc()