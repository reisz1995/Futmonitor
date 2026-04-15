import os
import json
import re
from datetime import datetime
from bs4 import BeautifulSoup

# Configuração do Supabase (Acesso ao Banco de Memória)
try:
    from supabase import create_client
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None
except ImportError:
    supabase = None

# Dicionário de roteamento extraído da topologia da UFMG
NODOS_SISTEMA = {
    "ufmg_classificacao_geral": "http://www.mat.ufmg.br/futebol/classificacao-geral_seriea/",
    "ufmg_classificacao_10_rodadas": "http://www.mat.ufmg.br/futebol/classificacao-das-ultimas-10-rodadas_seriea/",
    "ufmg_classificacao_mandante": "http://www.mat.ufmg.br/futebol/classificacao-como-mandante_seriea/",
    "ufmg_classificacao_visitante": "http://www.mat.ufmg.br/futebol/classificacao-como-visitante_seriea/",
    "ufmg_classificacao_turno": "http://www.mat.ufmg.br/futebol/classificacao-do-turno_seriea/",
    "ufmg_classificacao_returno": "http://www.mat.ufmg.br/futebol/classificacao-do-returno_seriea/",
    "ufmg_proxima_rodada": "http://www.mat.ufmg.br/futebol/tabela-da-proxima-rodada_seriea/",
    "ufmg_probabilidades_jogos": "http://www.mat.ufmg.br/futebol/tabela-de-probabilidades_seriea/",
    "ufmg_seq_vitorias": "http://www.mat.ufmg.br/futebol/sequencia-de-vitorias_seriea/",
    "ufmg_seq_derrotas": "http://www.mat.ufmg.br/futebol/sequencia-de-derrotas_seriea/",
    "ufmg_seq_invencibilidade": "http://www.mat.ufmg.br/futebol/sequencia-de-invencibilidade_seriea/",
    "ufmg_seq_sem_vitorias": "http://www.mat.ufmg.br/futebol/sequencia-sem-vitorias_seriea/",
    "ufmg_melhor_ataque": "http://www.mat.ufmg.br/futebol/melhor-ataque_seriea/",
    "ufmg_melhor_defesa": "http://www.mat.ufmg.br/futebol/melhor-defesa_seriea/"
}

def sanitizar_chave(texto):
    """Padroniza chaves de dicionário para o formato SQL snake_case."""
    texto = texto.lower().strip()
    texto = re.sub(r'[^\w\s]', '', texto)  
    texto = re.sub(r'\s+', '_', texto)     
    return texto if texto else "coluna_desconhecida"


def extrair_matriz_dinamica(html_source):
    """
    Sub-rotina de decodificação.
    Executa a varredura do DOM e aplica o DTO Mapper para conformidade SQL.
    """
    from bs4 import BeautifulSoup
    from datetime import datetime
    
    soup = BeautifulSoup(html_source, 'html.parser')
    tabelas = soup.find_all('table')
    
    if not tabelas:
        return []

    tabela_alvo = tabelas[0]
    linhas = tabela_alvo.find_all('tr')
    
    if not linhas:
        return []

    # MATRIZ DE CONFIGURAÇÃO DTO (Força a realidade do Python a casar com o SQL)
    MAPA_DE_SINTAXE = {
        "n": "pos",
        "pe": "empate",
        "p1": "mandante_1",
        "p2": "visitante_1",
        "gols_marcados": "gols",
        "gols_sofridos": "gols",
        "campeao": "campeão"
    }

    linha_cabecalho = linhas[0]
    chaves_brutas = [sanitizar_chave(th.get_text(strip=True)) for th in linha_cabecalho.find_all(['th', 'td'])]
    
    chaves = []
    for c in chaves_brutas:
        # Interceptação: Traduz a chave se existir no mapa, senão mantém a original
        base = MAPA_DE_SINTAXE.get(c, c)
        
        contador = 1
        chave_final = base
        while chave_final in chaves:
            chave_final = f"{base}_{contador}"
            contador += 1
        chaves.append(chave_final)
    
    dados_processados = []

    # Processamento vetorial (Inalterado)
    for idx in range(1, len(linhas)):
        colunas = linhas[idx].find_all(['td', 'th'])
        
        if len(colunas) != len(chaves):
            continue
            
        entidade = {}
        for k_idx, chave in enumerate(chaves):
            valor_bruto = colunas[k_idx].get_text(strip=True)
            
            if valor_bruto.isdigit():
                entidade[chave] = int(valor_bruto)
            elif valor_bruto.replace('.', '', 1).isdigit() and valor_bruto.count('.') == 1:
                entidade[chave] = float(valor_bruto)
            elif '%' in valor_bruto:
                try:
                    entidade[chave] = float(valor_bruto.replace('%', '').replace(',', '.'))
                except ValueError:
                    entidade[chave] = valor_bruto
            else:
                entidade[chave] = valor_bruto

        entidade['data_atualizacao'] = datetime.now().isoformat()
        dados_processados.append(entidade)

    return dados_processados
    

def operar_pipeline_multinodo():
    """Motor central: orquestra iteração de rede, extração (parser) e persistência."""
    from seleniumbase import SB
    
    print("[SYS] INICIALIZANDO ROTINA DE VARREDURA MULTI-NÓ")
    
    with SB(uc=True, headless=True) as sb:
        for nome_tabela, url_alvo in NODOS_SISTEMA.items():
            print(f"\n[EXEC] Estabelecendo vetor de conexão: {url_alvo}")
            
            try:
                sb.uc_open_with_reconnect(url_alvo, reconnect_time=2)
                sb.sleep(1.5) # Latência otimizada para estabilidade
                
                # Chamada restaurada para a sub-rotina de decodificação
                matriz_dados = extrair_matriz_dinamica(sb.get_page_source())
                
                if matriz_dados:
                    print(f"       [OK] Matriz mapeada: {len(matriz_dados)} vetores compilados.")
                    
                    # 1. Camada de Segurança: Persistência Local
                    arquivo_dump = f"dump_{nome_tabela}.json"
                    with open(arquivo_dump, 'w', encoding='utf-8') as f:
                        json.dump(matriz_dados, f, ensure_ascii=False, indent=2)
                    
                    # 2. Camada de Produção: Persistência Supabase
                    if supabase:
                        supabase.table(nome_tabela).insert(matriz_dados).execute()
                        print(f"       [OK] Sincronização commitada no Supabase: HUD '{nome_tabela}'")
                    else:
                        print("       [WARN] Supabase offline. Persistência de I/O restrita ao disco.")
                else:
                    print(f"       [ERR] Quebra de contrato de dados. DOM estéril ou inacessível.")
            
            except Exception as e:
                print(f"       [FATAL] Exceção crítica bloqueando o nó {nome_tabela}: {e}")

if __name__ == "__main__":
    operar_pipeline_multinodo()
