#!/usr/bin/env python3
"""
Consulta de Processos via API Pública do Datajud - Versão Enriquecida
Extrai e apresenta TODOS os dados disponíveis na resposta da API
Desenvolvido para maximizar a extração de informações processuais
"""

import re
import requests
import json
from typing import Dict, Optional, Tuple, List
import os
from datetime import datetime
from collections import defaultdict, Counter

# Importar dotenv se disponível
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


class DatajudConsultaEnriquecida:
    """
    Classe enriquecida para consulta de processos na API Pública do Datajud
    Extrai e apresenta TODOS os dados disponíveis na resposta
    """

    def __init__(self, api_key: str = None):
        """
        Inicializa a classe com credenciais da API

        Args:
            api_key: API Key da Datajud (se não fornecida, carrega do .env)
        """
        self.api_key = api_key or os.getenv('DATAJUD_API_KEY')
        self.base_url = "https://api-publica.datajud.cnj.jus.br"

        # Mapeamento completo dos códigos de tribunal para aliases da API
        self.mapeamento_tribunais = {
            ('1', '00'): 'stf', ('2', '00'): 'stj',
            ('4', '01'): 'trf1', ('4', '02'): 'trf2', ('4', '03'): 'trf3',
            ('4', '04'): 'trf4', ('4', '05'): 'trf5', ('4', '06'): 'trf6',
            ('5', '00'): 'tst',
            ('5', '01'): 'trt1', ('5', '02'): 'trt2', ('5', '03'): 'trt3',
            ('5', '04'): 'trt4', ('5', '05'): 'trt5', ('5', '06'): 'trt6',
            ('5', '07'): 'trt7', ('5', '08'): 'trt8', ('5', '09'): 'trt9',
            ('5', '10'): 'trt10', ('5', '11'): 'trt11', ('5', '12'): 'trt12',
            ('5', '13'): 'trt13', ('5', '14'): 'trt14', ('5', '15'): 'trt15',
            ('5', '16'): 'trt16', ('5', '17'): 'trt17', ('5', '18'): 'trt18',
            ('5', '19'): 'trt19', ('5', '20'): 'trt20', ('5', '21'): 'trt21',
            ('5', '22'): 'trt22', ('5', '23'): 'trt23', ('5', '24'): 'trt24',
            ('6', '00'): 'tse', ('7', '00'): 'stm',
            ('8', '02'): 'tjac', ('8', '17'): 'tjal', ('8', '23'): 'tjap',
            ('8', '04'): 'tjam', ('8', '05'): 'tjba', ('8', '07'): 'tjce',
            ('8', '26'): 'tjdft', ('8', '14'): 'tjes', ('8', '29'): 'tjgo',
            ('8', '21'): 'tjma', ('8', '28'): 'tjmt', ('8', '11'): 'tjms',
            ('8', '13'): 'tjmg', ('8', '16'): 'tjpa', ('8', '25'): 'tjpb',
            ('8', '02'): 'tjpr', ('8', '18'): 'tjpe', ('8', '22'): 'tjpi',
            ('8', '19'): 'tjrj', ('8', '20'): 'tjrn', ('8', '21'): 'tjrs',
            ('8', '11'): 'tjro', ('8', '24'): 'tjrr', ('8', '10'): 'tjsc',
            ('8', '26'): 'tjsp', ('8', '27'): 'tjse', ('8', '29'): 'tjto'
        }

        # Códigos de movimentação expandidos
        self.movimentacoes_interesse = {
            22: "Baixa Definitiva", 26: "Distribuição", 51: "Conclusão",
            60: "Expedição de documento", 85: "Petição", 92: "Publicação",
            380: "Citação", 384: "Intimação", 581: "Documento",
            848: "Trânsito em Julgado", 861: "Arquivamento",
            981: "Recebimento", 982: "Remessa", 1051: "Decurso de Prazo",
            1061: "Disponibilização no Diário da Justiça Eletrônico",
            10456: "Arquivamento Definitivo", 11010: "Mero expediente",
            12284: "Citação", 12286: "Citação Eletrônica", 12289: "Cancelamento"
        }

        # Mapeamento de códigos IBGE para municípios (principais)
        self.municipios_ibge = {
            3301702: "Duque de Caxias/RJ",
            3304557: "Rio de Janeiro/RJ",
            3550308: "São Paulo/SP",
            5300108: "Brasília/DF",
            # Adicionar mais conforme necessário
        }

        if self.api_key:
            print(f"✅ API Key carregada: {self.api_key[:20]}...")
        else:
            print("❌ API Key não encontrada no ambiente")

    def _construir_headers(self) -> Dict[str, str]:
        """Constrói os headers para a requisição"""
        if not self.api_key:
            return {}
        return {
            "Authorization": f"APIKey {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def validar_numero_processo(self, numero: str) -> bool:
        """Valida se o número do processo está no formato correto do CNJ"""
        numero_limpo = re.sub(r'[.\-\s]', '', numero)
        return bool(re.match(r'^\d{20}$', numero_limpo))

    def extrair_segmentos_processo(self, numero: str) -> Tuple[str, str, str]:
        """Extrai os segmentos J (ramo da justiça) e TR (tribunal) do número do processo"""
        numero_limpo = re.sub(r'[.\-\s]', '', numero)
        ramo_justica = numero_limpo[13]
        codigo_tribunal = numero_limpo[14:16]
        return numero_limpo, ramo_justica, codigo_tribunal

    def obter_endpoint_tribunal(self, numero: str) -> str:
        """Obtém o endpoint correto da API baseado no número do processo"""
        if not self.validar_numero_processo(numero):
            raise ValueError("Número de processo inválido")

        numero_limpo, ramo_justica, codigo_tribunal = self.extrair_segmentos_processo(numero)
        chave_tribunal = (ramo_justica, codigo_tribunal)
        alias_tribunal = self.mapeamento_tribunais.get(chave_tribunal)

        if not alias_tribunal:
            raise ValueError(f"Tribunal não encontrado para o código {ramo_justica}.{codigo_tribunal}")

        return f"{self.base_url}/api_publica_{alias_tribunal}/_search"

    def formatar_data(self, data_iso: str) -> str:
        """Formata data ISO para formato mais legível"""
        try:
            dt = datetime.fromisoformat(data_iso.replace('Z', '+00:00'))
            return dt.strftime('%d/%m/%Y %H:%M')
        except:
            return data_iso

    def extrair_metadados_elasticsearch(self, response_data: Dict) -> Dict:
        """
        Extrai metadados da resposta do Elasticsearch

        Args:
            response_data: Dados brutos da resposta

        Returns:
            Dict: Metadados estruturados
        """
        return {
            'tempo_resposta_ms': response_data.get('took', 0),
            'timeout': response_data.get('timed_out', False),
            'shards': {
                'total': response_data.get('_shards', {}).get('total', 0),
                'sucessos': response_data.get('_shards', {}).get('successful', 0),
                'falhas': response_data.get('_shards', {}).get('failed', 0),
                'ignorados': response_data.get('_shards', {}).get('skipped', 0)
            },
            'hits': {
                'total': response_data.get('hits', {}).get('total', {}).get('value', 0),
                'max_score': response_data.get('hits', {}).get('max_score', 0),
                'relacao': response_data.get('hits', {}).get('total', {}).get('relation', 'eq')
            }
        }

    def extrair_detalhes_processo(self, hit_data: Dict) -> Dict:
        """
        Extrai detalhes enriquecidos do processo

        Args:
            hit_data: Dados do hit do Elasticsearch

        Returns:
            Dict: Detalhes enriquecidos do processo
        """
        source = hit_data.get('_source', {})

        # Informações básicas enriquecidas
        detalhes = {
            'elasticsearch': {
                'index': hit_data.get('_index', ''),
                'id': hit_data.get('_id', ''),
                'score': hit_data.get('_score', 0)
            },
            'identificacao': {
                'numero_processo': source.get('numeroProcesso', ''),
                'id_interno': source.get('id', ''),
                'tribunal': source.get('tribunal', ''),
                'grau': source.get('grau', '')
            },
            'timestamps': {
                'data_ajuizamento': source.get('dataAjuizamento', ''),
                'ultima_atualizacao': source.get('dataHoraUltimaAtualizacao', ''),
                'timestamp_indexacao': source.get('@timestamp', ''),
                'data_ajuizamento_formatada': self.formatar_data(source.get('dataAjuizamento', '')),
                'ultima_atualizacao_formatada': self.formatar_data(source.get('dataHoraUltimaAtualizacao', ''))
            },
            'classificacao': {
                'classe': source.get('classe', {}),
                'assuntos': source.get('assuntos', []),
                'nivel_sigilo': source.get('nivelSigilo', 0),
                'sigilo_descricao': 'Público' if source.get('nivelSigilo',
                                                            0) == 0 else f'Sigiloso (nível {source.get("nivelSigilo", 0)})'
            },
            'sistema': {
                'sistema': source.get('sistema', {}),
                'formato': source.get('formato', {})
            },
            'orgao_julgador': self._enriquecer_orgao_julgador(source.get('orgaoJulgador', {})),
            'movimentacoes': self._analisar_movimentacoes_enriquecidas(source.get('movimentos', [])),
            'partes': {
                'polo_ativo': source.get('poloAtivo', []),
                'polo_passivo': source.get('poloPassivo', [])
            }
        }

        return detalhes

    def _enriquecer_orgao_julgador(self, orgao_data: Dict) -> Dict:
        """
        Enriquece informações do órgão julgador

        Args:
            orgao_data: Dados do órgão julgador

        Returns:
            Dict: Informações enriquecidas
        """
        codigo_ibge = orgao_data.get('codigoMunicipioIBGE')
        municipio = self.municipios_ibge.get(codigo_ibge, f"Código IBGE: {codigo_ibge}") if codigo_ibge else "N/A"

        return {
            'codigo': orgao_data.get('codigo', ''),
            'nome': orgao_data.get('nome', ''),
            'municipio': {
                'codigo_ibge': codigo_ibge,
                'nome': municipio
            }
        }

    def _analisar_movimentacoes_enriquecidas(self, movimentos: List[Dict]) -> Dict:
        """
        Análise enriquecida das movimentações

        Args:
            movimentos: Lista de movimentações

        Returns:
            Dict: Análise completa das movimentações
        """
        if not movimentos:
            return {'total': 0, 'movimentacoes': [], 'estatisticas': {}, 'complementos': {}}

        # Estatísticas básicas
        total = len(movimentos)
        codigos_unicos = set(mov.get('codigo') for mov in movimentos if mov.get('codigo'))

        # Análise temporal
        datas = [mov.get('dataHora') for mov in movimentos if mov.get('dataHora')]
        primeira_data = min(datas) if datas else None
        ultima_data = max(datas) if datas else None

        # Contagem por tipo
        contagem_tipos = Counter(mov.get('codigo') for mov in movimentos if mov.get('codigo'))

        # Análise de complementos tabelados
        complementos_analise = self._analisar_complementos_tabelados(movimentos)

        # Movimentações por mês
        movs_por_mes = defaultdict(int)
        for mov in movimentos:
            data = mov.get('dataHora', '')
            if data:
                try:
                    mes = data[:7]  # YYYY-MM
                    movs_por_mes[mes] += 1
                except:
                    pass

        # Movimentações enriquecidas
        movimentacoes_enriquecidas = []
        for mov in movimentos:
            mov_enriquecida = {
                'codigo': mov.get('codigo'),
                'nome': mov.get('nome', ''),
                'data_hora': mov.get('dataHora', ''),
                'data_formatada': self.formatar_data(mov.get('dataHora', '')),
                'tipo_interesse': mov.get('codigo') in self.movimentacoes_interesse,
                'descricao_interesse': self.movimentacoes_interesse.get(mov.get('codigo'), 'Outros'),
                'complementos_tabelados': mov.get('complementosTabelados', []),
                'total_complementos': len(mov.get('complementosTabelados', []))
            }
            movimentacoes_enriquecidas.append(mov_enriquecida)

        return {
            'total': total,
            'tipos_unicos': len(codigos_unicos),
            'periodo': {
                'primeira_movimentacao': primeira_data,
                'ultima_movimentacao': ultima_data,
                'primeira_formatada': self.formatar_data(primeira_data) if primeira_data else 'N/A',
                'ultima_formatada': self.formatar_data(ultima_data) if ultima_data else 'N/A'
            },
            'distribuicao_temporal': dict(sorted(movs_por_mes.items())),
            'contagem_por_tipo': dict(contagem_tipos.most_common()),
            'movimentacoes_interesse': sum(
                1 for mov in movimentos if mov.get('codigo') in self.movimentacoes_interesse),
            'complementos_analise': complementos_analise,
            'movimentacoes': movimentacoes_enriquecidas
        }

    def _analisar_complementos_tabelados(self, movimentos: List[Dict]) -> Dict:
        """
        Análise detalhada dos complementos tabelados

        Args:
            movimentos: Lista de movimentações

        Returns:
            Dict: Análise dos complementos
        """
        todos_complementos = []
        for mov in movimentos:
            complementos = mov.get('complementosTabelados', [])
            todos_complementos.extend(complementos)

        if not todos_complementos:
            return {'total': 0, 'tipos': {}, 'detalhes': []}

        # Contagem por tipo de complemento
        tipos_complementos = Counter()
        detalhes_complementos = []

        for comp in todos_complementos:
            codigo = comp.get('codigo')
            nome = comp.get('nome', '')
            descricao = comp.get('descricao', '')
            valor = comp.get('valor', '')

            tipos_complementos[f"{codigo} - {nome}"] += 1

            detalhes_complementos.append({
                'codigo': codigo,
                'nome': nome,
                'descricao': descricao,
                'valor': valor
            })

        return {
            'total': len(todos_complementos),
            'tipos_unicos': len(tipos_complementos),
            'contagem_por_tipo': dict(tipos_complementos.most_common()),
            'detalhes': detalhes_complementos
        }

    def consultar_processo_enriquecido(self, numero: str) -> Dict:
        """
        Consulta um processo com extração enriquecida de todos os dados
        """
        try:
            if not self.api_key:
                return {
                    "sucesso": False,
                    "erro": "API Key não encontrada",
                    "detalhes": "Verifique se DATAJUD_API_KEY está configurada"
                }

            if not self.validar_numero_processo(numero):
                return {
                    "sucesso": False,
                    "erro": "Número de processo inválido",
                    "detalhes": "O número deve ter 20 dígitos no formato CNJ"
                }

            endpoint = self.obter_endpoint_tribunal(numero)
            headers = self._construir_headers()

            # Query para busca
            query = {
                "query": {
                    "match_phrase": {
                        "numeroProcesso": numero
                    }
                }
            }

            response = requests.post(endpoint, json=query, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Extrair metadados do Elasticsearch
            metadados_es = self.extrair_metadados_elasticsearch(data)

            if data.get('hits', {}).get('total', {}).get('value', 0) > 0:
                hits = data['hits']['hits']

                # Processar TODOS os hits e consolidar informações
                processos_por_grau = {}
                todas_movimentacoes = []
                orgaos_julgadores = []

                for hit in hits:
                    source = hit.get('_source', {})
                    grau = source.get('grau', '')

                    # Consolidar movimentações de todos os graus
                    movimentos = source.get('movimentos', [])
                    todas_movimentacoes.extend(movimentos)

                    # Coletar órgãos julgadores
                    orgao = source.get('orgaoJulgador', {})
                    if orgao:
                        orgaos_julgadores.append(orgao)

                    # Manter informações do primeiro hit como base (ou escolher um específico)
                    if not processos_por_grau:
                        processo_base = self.extrair_detalhes_processo(hit)

                # Substituir as movimentações do processo base pelas consolidadas
                if todas_movimentacoes:
                    processo_base['movimentacoes'] = self._analisar_movimentacoes_enriquecidas(todas_movimentacoes)

                # Adicionar informações sobre múltiplos graus
                processo_base['multiplos_graus'] = {
                    'total_encontrado': len(hits),
                    'graus': [hit['_source'].get('grau', '') for hit in hits],
                    'orgaos_julgadores': [self._enriquecer_orgao_julgador(orgao) for orgao in orgaos_julgadores]
                }

                return {
                    "sucesso": True,
                    "metadados_consulta": {
                        "numero_processo": numero,
                        "endpoint_usado": endpoint,
                        "timestamp_consulta": datetime.now().isoformat(),
                        "elasticsearch": metadados_es
                    },
                    "processo": processo_base,
                    "dados_brutos": [hit['_source'] for hit in hits]  # Todos os dados brutos
                }
            else:
                return {
                    "sucesso": False,
                    "erro": "Processo não encontrado",
                    "detalhes": "O processo pode ser sigiloso, muito recente ou não estar indexado",
                    "metadados_consulta": {
                        "numero_processo": numero,
                        "endpoint_usado": endpoint,
                        "elasticsearch": metadados_es
                    }
                }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": "Erro na consulta",
                "detalhes": str(e)
            }

    def exibir_resultado_enriquecido(self, resultado: Dict) -> None:
        """
        Exibe resultado enriquecido de forma detalhada

        Args:
            resultado: Resultado da consulta enriquecida
        """
        if not resultado["sucesso"]:
            print("❌ ERRO na consulta:")
            print(f"Erro: {resultado['erro']}")
            print(f"Detalhes: {resultado['detalhes']}")
            return

        processo = resultado["processo"]
        metadados = resultado["metadados_consulta"]

        print("=" * 80)
        print("📋 RELATÓRIO ENRIQUECIDO DO PROCESSO")
        print("=" * 80)

        # Seção 1: Identificação
        print(f"\n🔍 IDENTIFICAÇÃO:")
        print(f"   Número: {processo['identificacao']['numero_processo']}")
        print(f"   ID Interno: {processo['identificacao']['id_interno']}")
        print(f"   Tribunal: {processo['identificacao']['tribunal']}")
        print(f"   Grau: {processo['identificacao']['grau']}")

        # Seção 2: Metadados da Consulta
        es_meta = metadados["elasticsearch"]
        print(f"\n⚡ PERFORMANCE DA CONSULTA:")
        print(f"   Tempo de resposta: {es_meta['tempo_resposta_ms']}ms")
        print(f"   Score de relevância: {es_meta['hits']['max_score']:.2f}")
        print(f"   Shards consultados: {es_meta['shards']['sucessos']}/{es_meta['shards']['total']}")
        print(f"   Índice: {processo['elasticsearch']['index']}")

        # Seção 3: Timestamps
        timestamps = processo["timestamps"]
        print(f"\n📅 LINHA DO TEMPO:")
        print(f"   Ajuizamento: {timestamps['data_ajuizamento_formatada']}")
        print(f"   Última atualização: {timestamps['ultima_atualizacao_formatada']}")
        print(f"   Indexação: {self.formatar_data(timestamps['timestamp_indexacao'])}")

        # Seção 4: Classificação
        classificacao = processo["classificacao"]
        print(f"\n📂 CLASSIFICAÇÃO:")
        print(
            f"   Classe: {classificacao['classe'].get('nome', 'N/A')} (código: {classificacao['classe'].get('codigo', 'N/A')})")
        print(f"   Sigilo: {classificacao['sigilo_descricao']}")

        if classificacao['assuntos']:
            print(f"   Assuntos ({len(classificacao['assuntos'])}):")
            for assunto in classificacao['assuntos']:
                print(f"     • {assunto.get('nome', 'N/A')} (código: {assunto.get('codigo', 'N/A')})")

        # Seção 5: Sistema e Formato
        sistema = processo["sistema"]
        print(f"\n💻 SISTEMA:")
        print(
            f"   Sistema: {sistema['sistema'].get('nome', 'N/A')} (código: {sistema['sistema'].get('codigo', 'N/A')})")
        print(
            f"   Formato: {sistema['formato'].get('nome', 'N/A')} (código: {sistema['formato'].get('codigo', 'N/A')})")

        # Seção 6: Órgão Julgador
        orgao = processo["orgao_julgador"]
        print(f"\n⚖️ ÓRGÃO JULGADOR:")
        print(f"   Nome: {orgao['nome']}")
        print(f"   Código: {orgao['codigo']}")
        print(f"   Município: {orgao['municipio']['nome']}")
        if orgao['municipio']['codigo_ibge']:
            print(f"   Código IBGE: {orgao['municipio']['codigo_ibge']}")

        # NOVA SEÇÃO: Múltiplos Graus
        if 'multiplos_graus' in processo:
            multiplos = processo['multiplos_graus']
            print(f"\n🎯 MÚLTIPLOS GRAUS ENCONTRADOS:")
            print(f"   Total de instâncias: {multiplos['total_encontrado']}")
            print(f"   Graus: {', '.join(multiplos['graus'])}")

            if len(multiplos['orgaos_julgadores']) > 1:
                print(f"   Órgãos julgadores envolvidos:")
                for i, orgao_info in enumerate(multiplos['orgaos_julgadores'], 1):
                    print(f"     {i}. {orgao_info['nome']} (Grau: {multiplos['graus'][i - 1]})")

        # Seção 7: Análise de Movimentações
        movs = processo["movimentacoes"]
        print(f"\n🔄 ANÁLISE DE MOVIMENTAÇÕES:")
        print(f"   Total: {movs['total']} movimentações")
        print(f"   Tipos únicos: {movs['tipos_unicos']}")
        print(f"   Movimentações de interesse: {movs['movimentacoes_interesse']}")
        print(f"   Período: {movs['periodo']['primeira_formatada']} até {movs['periodo']['ultima_formatada']}")

        # Top 5 tipos de movimentação
        print(f"\n   📊 Top 5 tipos de movimentação:")
        for codigo, count in list(movs['contagem_por_tipo'].items())[:5]:
            nome_mov = self.movimentacoes_interesse.get(codigo, f"Código {codigo}")
            print(f"     • {nome_mov}: {count} ocorrências")

        # Distribuição temporal
        if movs['distribuicao_temporal']:
            print(f"\n   📈 Distribuição por mês:")
            for mes, count in list(movs['distribuicao_temporal'].items())[-6:]:  # Últimos 6 meses
                print(f"     • {mes}: {count} movimentações")

        # Seção 8: Complementos Tabelados
        complementos = movs["complementos_analise"]
        if complementos['total'] > 0:
            print(f"\n📋 COMPLEMENTOS TABELADOS:")
            print(f"   Total: {complementos['total']} complementos")
            print(f"   Tipos únicos: {complementos['tipos_unicos']}")

            print(f"\n   🏷️ Top 5 tipos de complementos:")
            for tipo, count in list(complementos['contagem_por_tipo'].items())[:5]:
                print(f"     • {tipo}: {count} ocorrências")

        # Seção 9: Partes do Processo
        partes = processo["partes"]
        print(f"\n👥 PARTES DO PROCESSO:")

        if partes['polo_ativo']:
            print(f"   🔷 Polo Ativo ({len(partes['polo_ativo'])}):")
            for parte in partes['polo_ativo']:
                print(f"     • {parte.get('nome', 'N/A')}")

        if partes['polo_passivo']:
            print(f"   🔶 Polo Passivo ({len(partes['polo_passivo'])}):")
            for parte in partes['polo_passivo']:
                print(f"     • {parte.get('nome', 'N/A')}")

        if not partes['polo_ativo'] and not partes['polo_passivo']:
            print(f"   ❌ Nenhuma parte identificada")

        print("=" * 80)


def exemplo_uso_enriquecido():
    """
    Exemplo de uso da versão enriquecida
    """
    consulta = DatajudConsultaEnriquecida()
    numero = "10008971220248260053" # "00076477720164013700" # "00105975520245030106" #  #"50247597020204025101" # "09715058120248190001" # "08319230620248190021" ##"13.927.801/0029-40" # "08319230620248190021" ## "0010637-74.2015.5.15.0023"   ##

    print("🔍 Consultando processo com análise enriquecida...")
    resultado = consulta.consultar_processo_enriquecido(numero)

    consulta.exibir_resultado_enriquecido(resultado)

    return resultado


if __name__ == "__main__":
    # Configurar API key para teste
    os.environ['DATAJUD_API_KEY'] = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

    exemplo_uso_enriquecido()

