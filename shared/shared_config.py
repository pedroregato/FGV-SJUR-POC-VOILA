# shared_config.py - Módulo de Configuração Compartilhada entre Aplicações

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Configurações
CONFIG_FILE = "app_config.json"
DEFAULT_OUTPUT_FOLDER = "outputs"


class SharedConfig:
    """Gerenciador de configuração compartilhada entre o coletor e analisador"""

    def __init__(self):
        self.config_path = Path(CONFIG_FILE)
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Carrega configuração do arquivo ou cria padrão"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Valida se a pasta ainda existe
                    if self._validate_folder(config.get('output_folder', DEFAULT_OUTPUT_FOLDER)):
                        return config
                    else:
                        # Se pasta não existe mais, volta para padrão
                        return self._create_default_config()
            except Exception:
                # Se erro ao ler, cria configuração padrão
                return self._create_default_config()
        else:
            return self._create_default_config()

    def _create_default_config(self) -> Dict[str, Any]:
        """Cria configuração padrão"""
        return {
            "output_folder": DEFAULT_OUTPUT_FOLDER,
            "last_updated": datetime.now().isoformat(),
            "updated_by": "system",
            "version": "1.0"
        }

    def _validate_folder(self, folder_path: str) -> bool:
        """Valida se a pasta existe ou pode ser criada"""
        try:
            path = Path(folder_path)
            if path.exists():
                return path.is_dir()
            else:
                # Tenta criar para validar se é possível
                path.mkdir(parents=True, exist_ok=True)
                return True
        except Exception:
            return False

    def _save_config(self):
        """Salva configuração no arquivo"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao salvar configuração: {e}")

    def get_output_folder(self) -> str:
        """Retorna a pasta de saída configurada"""
        return self._config.get('output_folder', DEFAULT_OUTPUT_FOLDER)

    def set_output_folder(self, folder_path: str, updated_by: str = "user") -> bool:
        """
        Define nova pasta de saída

        Args:
            folder_path: Caminho da nova pasta
            updated_by: Quem fez a atualização (coletor, analisador, user)

        Returns:
            bool: True se configuração foi salva com sucesso
        """
        if not self._validate_folder(folder_path):
            return False

        self._config.update({
            "output_folder": str(Path(folder_path).resolve()),
            "last_updated": datetime.now().isoformat(),
            "updated_by": updated_by
        })

        self._save_config()
        return True

    def get_config_info(self) -> Dict[str, Any]:
        """Retorna informações completas da configuração"""
        return self._config.copy()

    def get_data_paths(self) -> Dict[str, str]:
        """Retorna caminhos completos para os arquivos de dados"""
        base_folder = Path(self.get_output_folder())

        return {
            "base": str(base_folder),
            "json": str(base_folder / "json"),
            "html": str(base_folder / "html"),
            "dashboard_data": str(base_folder / "json" / "dashboard_data.json"),
            "emails_data": str(base_folder / "json" / "emails_data.json")
        }

    def check_data_availability(self) -> Dict[str, bool]:
        """Verifica se os arquivos de dados existem"""
        paths = self.get_data_paths()

        return {
            "base_folder": Path(paths["base"]).exists(),
            "json_folder": Path(paths["json"]).exists(),
            "html_folder": Path(paths["html"]).exists(),
            "dashboard_data": Path(paths["dashboard_data"]).exists(),
            "emails_data": Path(paths["emails_data"]).exists()
        }

    def find_available_data_folders(self) -> list:
        """Encontra pastas que contêm dados válidos"""
        possible_folders = []

        # Verifica pasta atual configurada
        current_folder = self.get_output_folder()
        if self._has_valid_data(current_folder):
            possible_folders.append(current_folder)

        # Verifica pasta padrão se diferente da atual
        if current_folder != DEFAULT_OUTPUT_FOLDER:
            if self._has_valid_data(DEFAULT_OUTPUT_FOLDER):
                possible_folders.append(DEFAULT_OUTPUT_FOLDER)

        # Verifica outras pastas comuns
        common_folders = ["output", "dados", "resultados", "coleta"]
        for folder in common_folders:
            if folder not in [current_folder, DEFAULT_OUTPUT_FOLDER]:
                if self._has_valid_data(folder):
                    possible_folders.append(folder)

        return possible_folders

    def _has_valid_data(self, folder_path: str) -> bool:
        """Verifica se uma pasta contém dados válidos"""
        try:
            base_path = Path(folder_path)
            dashboard_path = base_path / "json" / "dashboard_data.json"
            emails_path = base_path / "json" / "emails_data.json"

            return dashboard_path.exists() and emails_path.exists()
        except Exception:
            return False

    def auto_detect_data_folder(self) -> Optional[str]:
        """Detecta automaticamente pasta com dados mais recentes"""
        available_folders = self.find_available_data_folders()

        if not available_folders:
            return None

        # Se só tem uma opção, retorna ela
        if len(available_folders) == 1:
            return available_folders[0]

        # Se tem múltiplas, retorna a com dados mais recentes
        newest_folder = None
        newest_time = 0

        for folder in available_folders:
            try:
                dashboard_path = Path(folder) / "json" / "dashboard_data.json"
                if dashboard_path.exists():
                    mtime = dashboard_path.stat().st_mtime
                    if mtime > newest_time:
                        newest_time = mtime
                        newest_folder = folder
            except Exception:
                continue

        return newest_folder


# Instância global para uso nas aplicações
shared_config = SharedConfig()


# Funções de conveniência para uso direto
def get_output_folder() -> str:
    """Função de conveniência para obter pasta de saída"""
    return shared_config.get_output_folder()


def set_output_folder(folder_path: str, updated_by: str = "user") -> bool:
    """Função de conveniência para definir pasta de saída"""
    return shared_config.set_output_folder(folder_path, updated_by)


def get_data_paths() -> Dict[str, str]:
    """Função de conveniência para obter caminhos de dados"""
    return shared_config.get_data_paths()


def check_data_availability() -> Dict[str, bool]:
    """Função de conveniência para verificar disponibilidade de dados"""
    return shared_config.check_data_availability()


def auto_detect_data_folder() -> Optional[str]:
    """Função de conveniência para detecção automática"""
    return shared_config.auto_detect_data_folder()


# Exemplo de uso:
if __name__ == "__main__":
    print("=== Teste do Módulo de Configuração Compartilhada ===")

    # Mostra configuração atual
    print(f"Pasta atual: {get_output_folder()}")
    print(f"Caminhos: {get_data_paths()}")
    print(f"Disponibilidade: {check_data_availability()}")

    # Testa detecção automática
    detected = auto_detect_data_folder()
    if detected:
        print(f"Pasta detectada automaticamente: {detected}")
    else:
        print("Nenhuma pasta com dados encontrada")

