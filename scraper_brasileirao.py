
import requests
from bs4 import BeautifulSoup
import os
from supabase import create_client
from datetime import datetime

# Configuração do Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL", "sua_url_aqui")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sua_chave_aqui")

# Inicializar cliente Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def scrape_brasileirao():
    """
    Faz scraping da tabela do Brasileirão Série A do site ogol.com.br
    """
    url = "https://www.ogol.com.br/edicao/brasileirao-serie-a-2026/210277"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Encontrar a tabela de classificação
        # Procurar por elementos que contenham os dados dos times
        tabela = soup.find('table', {'class': 'classificacao'}) or soup.find('table')

        if not tabela:
            # Tentar encontrar por outras classes comuns
            tabela = soup.find('table', {'class': 'zebra'}) or soup.find('table', {'class': 'std'})

        if not tabela:
            print("Tabela não encontrada. Verificando estrutura...")
            # Listar todas as tabelas para debug
            tabelas = soup.find_all('table')
            print(f"Total de tabelas encontradas: {len(tabelas)}")
            if tabelas:
                tabela = tabelas[0]  # Usar primeira tabela

        dados_times = []

        if tabela:
            linhas = tabela.find_all('tr')

            for linha in linhas:
                colunas = linha.find_all(['td', 'th'])

                if len(colunas) >= 10:
                    try:
                        # Extrair dados das colunas
                        posicao = colunas[0].get_text(strip=True)
                        time_elem = colunas[1].find('a') or colunas[1]
                        nome_time = time_elem.get_text(strip=True) if time_elem else colunas[1].get_text(strip=True)

                        # Extrair número de jogos, pontos, etc
                        pontos = colunas[2].get_text(strip=True)
                        jogos = colunas[3].get_text(strip=True)
                        vitorias = colunas[4].get_text(strip=True)
                        empates = colunas[5].get_text(strip=True)
                        derrotas = colunas[6].get_text(strip=True)
                        gm = colunas[7].get_text(strip=True)
                        gc = colunas[8].get_text(strip=True)
                        sg = colunas[9].get_text(strip=True)

                        # Validar se é número
                        if posicao.isdigit():
                            dados_times.append({
                                'posicao': int(posicao),
                                'nome_time': nome_time,
                                'pontos': int(pontos) if pontos.isdigit() else 0,
                                'jogos': int(jogos) if jogos.isdigit() else 0,
                                'vitorias': int(vitorias) if vitorias.isdigit() else 0,
                                'empates': int(empates) if empates.isdigit() else 0,
                                'derrotas': int(derrotas) if derrotas.isdigit() else 0,
                                'gols_marcados': int(gm) if gm.isdigit() else 0,
                                'gols_sofridos': int(gc) if gc.isdigit() else 0,
                                'saldo_gols': int(sg) if sg.replace('+', '').replace('-', '').isdigit() else 0,
                                'data_atualizacao': datetime.now().isoformat()
                            })
                    except Exception as e:
                        print(f"Erro ao processar linha: {e}")
                        continue

        return dados_times

    except requests.RequestException as e:
        print(f"Erro na requisição: {e}")
        return []
    except Exception as e:
        print(f"Erro inesperado: {e}")
        return []

def enviar_para_supabase(dados):
    """
    Envia os dados para o Supabase
    """
    try:
        # Limpar tabela antes de inserir (opcional)
        # supabase.table('classificacao_brasileirao').delete().neq('id', 0).execute()

        # Inserir dados em batch
        if dados:
            result = supabase.table('classificacao_brasileirao').insert(dados).execute()
            print(f"✅ {len(dados)} registros inseridos com sucesso!")
            return result
    except Exception as e:
        print(f"❌ Erro ao enviar para Supabase: {e}")
        return None

def main():
    print("🏆 Iniciando scraping do Brasileirão Série A...")

    dados = scrape_brasileirao()

    if dados:
        print(f"\n📊 Dados coletados de {len(dados)} times")
        print("\nEnviando para o Supabase...")
        enviar_para_supabase(dados)

        # Mostrar preview
        print("\n📈 Preview da classificação:")
        for time in dados[:5]:
            print(f"{time['posicao']}. {Time['nome_time']} - {Time['pontos']} pts")
    else:
        print("❌ Nenhum dado coletado")

if __name__ == "__main__":
    main()
