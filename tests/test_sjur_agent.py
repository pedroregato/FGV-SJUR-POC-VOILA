import pytest
from pathlib import Path
from unittest.mock import MagicMock
from app.agents.sjur_agent import gerar_json_do_email, parse_email_html, extract_processos

@pytest.fixture
def mock_email_obj():
    mock = MagicMock()
    mock.ReceivedTime.strftime.return_value = "2025-05-06 15:45:00"
    mock.EntryID = "MSGID-TEST-123"
    mock.Subject = "Publicações do dia"
    mock.SenderEmailAddress = "serdon@exemplo.com"
    mock.HTMLBody = """
        <html>
            <body>
                <table>
                    <tr><td>Escritório:</td><td>FGV</td></tr>
                    <tr><td>Código:</td><td>123</td></tr>
                    <tr><td>Área:</td><td>910</td></tr>
                    <tr><td>Jornal:</td><td>Diário Oficial</td></tr>
                    <tr><td>Data de Disponibilização:</td><td>06/05/2025</td></tr>
                </table>
                <table>
                    <tr><td>Nome Pesquisado</td><td>FGV</td></tr>
                    <tr><td>Tribunal</td><td>TRF1</td></tr>
                    <tr><td>Secretaria</td><td>1ª Vara</td></tr>
                    <tr><td>Data de Publicação</td><td>06/05/2025</td></tr>
                    <tr><td>Publicação</td><td>NPU: 0801950-78.2025.4.05.8400 Parte FGV</td></tr>
                </table>
            </body>
        </html>
    """
    return mock

def test_extract_processos():
    texto = "Processo 0801950-78.2025.4.05.8400 em trâmite no TRF5."
    processos = extract_processos(texto)
    assert processos == ["0801950-78.2025.4.05.8400"]

def test_parse_email_html(mock_email_obj):
    html = mock_email_obj.HTMLBody
    dados, pesquisas = parse_email_html(html)
    assert dados["escritorio"] == "FGV"
    assert pesquisas[0]["nome_pesquisado"] == "FGV"
    assert "0801950-78.2025.4.05.8400" in pesquisas[0]["publicacao"]

def test_gerar_json_do_email(tmp_path, mock_email_obj):
    pasta_html = tmp_path / "html"
    pasta_json = tmp_path / "json"
    caminho = gerar_json_do_email(mock_email_obj, pasta_html, pasta_json)

    assert caminho is not None
    assert caminho.exists()
    with open(caminho, encoding="utf-8") as f:
        conteudo = f.read()
        assert "FGV" in conteudo
        assert "0801950-78.2025.4.05.8400" in conteudo
