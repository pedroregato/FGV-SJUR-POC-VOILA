from app.agents.sjur_agent import extract_processos

def test_extract_multiplos_processos():
    texto = (
        "Segue a lista de processos: 0801950-78.2025.4.05.8400, "
        "0801234-56.2024.4.01.3400 e ainda 0812345-67.2023.4.02.5001."
    )
    processos = extract_processos(texto)
    assert set(processos) == {
        "0801950-78.2025.4.05.8400",
        "0801234-56.2024.4.01.3400",
        "0812345-67.2023.4.02.5001"
    }
