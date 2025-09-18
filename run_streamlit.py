# run_streamlit.py
import streamlit.web.bootstrap
import sys
import os

if __name__ == "__main__":
    app_file = sys.argv[1]
    args = sys.argv[2:]

    print(f"DEBUG: Iniciando Streamlit com arquivo: {app_file}")
    print(f"DEBUG: Argumentos: {args}")

    # Força modo debug para ver mensagens
    os.environ['STREAMLIT_DEBUG'] = 'true'

    try:
        streamlit.web.bootstrap.run(app_file, "", args, {})
        print("DEBUG: Streamlit encerrado normalmente")
    except Exception as e:
        print(f"DEBUG: Erro ao iniciar Streamlit: {e}")
        import traceback

        traceback.print_exc()