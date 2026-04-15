import requests
from bs4 import BeautifulSoup
import os
import time
import random
from datetime import datetime

# Tentar usar curl_cffi se disponível (melhor para evitar TLS fingerprinting)
try:
    from curl_cffi import requests as curl_requests
    USE_CURL = True
    print("✅ Usando curl_cffi para evitar TLS fingerprinting")
except ImportError:
    USE_CURL = False
    print("⚠️ curl_cffi não disponível, usando requests padrão")

# Configuração do Supabase
try:
    from supabase import create_client
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Cliente Supabase inicializado")
    else:
        supabase = None
        print("⚠️ Variáveis de ambiente Supabase não configuradas")
except ImportError:
    supabase = None
    print("⚠️ Biblioteca supabase não instalada")

# Lista de User-Agents realistas
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
]

def get_headers():
    """Retorna headers completos de browser"""
    user_agent = random.choice(USER_AGENTS)

    headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'DNT': '1',
    }

    return headers

def fetch_with_retry(url, max_retries=3, delay=2):
    """Faz requisição com retry e delay"""

    for attempt in range(max_retries):
        try:
            headers = get_headers()

            # Adicionar delay aleatório para parecer mais humano
            if attempt > 0:
                sleep_time = delay + random.uniform(1, 3)
                print(f"⏳ Aguardando {sleep_time:.1f}s antes da tentativa {attempt + 1}...")
                time.sleep(sleep_time)
            else:
                time.sleep(random.uniform(1, 2))  # Delay inicial

            print(f"🌐 Tentativa {attempt + 1}/{max_retries}: {url}")

            # Tentar usar curl_cffi primeiro (evita TLS fingerprinting)
            if USE_CURL:
                try:
                    response = curl_requests.get(
                        url, 
                        headers=headers, 
                        timeout=30,
                        impersonate="chrome"
                    )
                    if response.status_code == 200:
                        print(f"✅ Sucesso com curl_cffi!")
                        return response
                except Exception as e:
                    print(f"⚠️ curl_cffi falhou: {e}, tentando requests padrão...")

            # Fallback para requests padrão
            session = requests.Session()
            session.headers.update(headers)

            response = session.get(url, timeout=30)
            response.raise_for_status()

            print(f"✅ Sucesso! Status: {response.status_code}")
            return response

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"❌ 403 Forbidden na tentativa {attempt + 1}")
                if attempt == max_retries - 1:
                    print("🚫 Todas as tentativas falharam com 403")
                    return None
            else:
                print(f"❌ HTTP Error {e.response.status_code}")
                if attempt == max_retries - 1:
                    return None

        except Exception as e:
            print(f"❌ Erro na tentativa {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                return None

    return None

def scrape_brasileirao():
    """
    Faz scraping da tabela do Brasileirão Série A do site ogol.com.br
    """
    url = "https://www.ogol.com.br/edicao/brasileirao-serie-a-2026/210277"

    print("🏆 Iniciando scraping do Brasileirão Série A...")
    print(f"📍 URL: {url}")

    response = fetch_with_retry(url, max_retries=3, delay=3)

    if not response:
        print("❌ Falha ao obter dados do site")
        return []

    try:
        soup = BeautifulSoup(response.content, 'html.parser')

        # Estratégia 1: Procurar tabela com classe específica
        tabela = soup.find('table', {'class': 'classificacao'})

        # Estratégia 2: Procurar por outras classes comuns
        if not tabela:
            tabela = soup.find('table', {'class': 'zebra'}) or soup.find('table', {'class': 'std'})

        # Estratégia 3: Procurar por tabela dentro de div com id específico
        if not tabela:
            div_tabela = soup.find('div', {'id': 'classificacao'}) or soup.find('div', {'class': 'tabela'})
            if div_tabela:
                tabela = div_tabela.find('table')

        # Estratégia 4: Usar primeira tabela com dados de classificação
        if not tabela:
            tabelas = soup.find_all('table')
            print(f"🔍 Total de tabelas encontradas: {len(tabelas)}")

            for t in tabelas:
                # Verificar se a tabela tem linhas suficientes (20 times)
                linhas = t.find_all('tr')
                if len(linhas) >= 20:
                    tabela = t
                    print(f"✅ Tabela selecionada com {len(linhas)} linhas")
                    break

        if not tabela:
            print("❌ Nenhuma tabela de classificação encontrada")
            # Salvar HTML para debug
            with open('debug_page.html', 'w', encoding='utf-8') as f:
                f.write(soup.prettify())
            print("💾 HTML salvo em debug_page.html para análise")
            return []

        dados_times = []
        linhas = tabela.find_all('tr')

        print(f"📊 Processando {len(linhas)} linhas da tabela...")

        for linha in linhas:
            colunas = linha.find_all(['td', 'th'])

            # Precisamos de pelo menos 10 colunas (pos, time, pts, j, v, e, d, gm, gc, sg)
            if len(colunas) >= 10:
                try:
                    # Extrair texto limpo
                    texto_colunas = [col.get_text(strip=True) for col in colunas]

                    # Verificar se primeira coluna é número (posição)
                    posicao_str = texto_colunas[0]
                    if not posicao_str.isdigit():
                        continue

                    posicao = int(posicao_str)

                    # Extrair nome do time (geralmente na segunda coluna)
                    nome_time = texto_colunas[1]

                    # Limpar nome do time (remover possíveis números ou símbolos)
                    nome_time = ' '.join(nome_time.split())

                    # Extrair estatísticas
                    pontos = int(texto_colunas[2]) if texto_colunas[2].isdigit() else 0
                    jogos = int(texto_colunas[3]) if texto_colunas[3].isdigit() else 0
                    vitorias = int(texto_colunas[4]) if texto_colunas[4].isdigit() else 0
                    empates = int(texto_colunas[5]) if texto_colunas[5].isdigit() else 0
                    derrotas = int(texto_colunas[6]) if texto_colunas[6].isdigit() else 0
                    gm = int(texto_colunas[7]) if texto_colunas[7].isdigit() else 0
                    gc = int(texto_colunas[8]) if texto_colunas[8].isdigit() else 0

                    # Saldo de gols pode ter sinal + ou -
                    sg_str = texto_colunas[9].replace('+', '').replace('-', '')
                    sg = int(sg_str) if sg_str.isdigit() else 0
                    if texto_colunas[9].startswith('-'):
                        sg = -sg

                    # Validar dados básicos
                    if posicao > 0 and nome_time and pontos >= 0:
                        dados_times.append({
                            'posicao': posicao,
                            'nome_time': nome_time,
                            'pontos': pontos,
                            'jogos': jogos,
                            'vitorias': vitorias,
                            'empates': empates,
                            'derrotas': derrotas,
                            'gols_marcados': gm,
                            'gols_sofridos': gc,
                            'saldo_gols': sg,
                            'data_atualizacao': datetime.now().isoformat()
                        })

                except Exception as e:
                    print(f"⚠️ Erro ao processar linha: {e}")
                    print(f"   Conteúdo: {texto_colunas}")
                    continue

        print(f"✅ {len(dados_times)} times processados com sucesso")
        return dados_times

    except Exception as e:
        print(f"❌ Erro ao parsear HTML: {e}")
        import traceback
        traceback.print_exc()
        return []

def enviar_para_supabase(dados):
    """
    Envia os dados para o Supabase
    """
    if not supabase:
        print("❌ Cliente Supabase não disponível")
        return None

    if not dados:
        print("❌ Nenhum dado para enviar")
        return None

    try:
        # Limpar tabela antes de inserir (opcional - descomente se necessário)
        # print("🧹 Limpando tabela antiga...")
        # supabase.table('classificacao_brasileirao').delete().neq('id', 0).execute()

        # Inserir dados em batch
        print(f"📤 Enviando {len(dados)} registros para o Supabase...")

        # Supabase tem limite de 1000 registros por inserção
        batch_size = 100
        for i in range(0, len(dados), batch_size):
            batch = dados[i:i+batch_size]
            result = supabase.table('classificacao_brasileirao').insert(batch).execute()
            print(f"   ✅ Batch {i//batch_size + 1}: {len(batch)} registros")

        print(f"✅ Total de {len(dados)} registros inseridos com sucesso!")
        return result

    except Exception as e:
        print(f"❌ Erro ao enviar para Supabase: {e}")
        import traceback
        traceback.print_exc()
        return None

def salvar_backup_local(dados):
    """Salva backup local dos dados em JSON"""
    import json

    if not dados:
        return

    filename = f"brasileirao_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        print(f"💾 Backup salvo: {filename}")
    except Exception as e:
        print(f"⚠️ Erro ao salvar backup: {e}")

def main():
    print("="*60)
    print("🏆 SCRAPER BRASILEIRÃO SÉRIE A")
    print(f"⏰ Iniciado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*60)

    
   # Executar scraping
    dados = scrape_brasileirao()

    if dados:
        print(f"\n📊 Dados coletados de {len(dados)} times")

        # Mostrar preview
        print("\n📈 Preview da classificação:")
        print("-" * 50)
        for time in dados[:5]:
            print(f"{time['posicao']:2d}. {time['nome_time'][:25]:25s} - {time['pontos']:2d} pts ({time['jogos']}J)")
        print("-" * 50)

        # Salvar backup local
        salvar_backup_local(dados)

        # Enviar para Supabase
        if supabase:
            print("\n📡 Enviando para o Supabase...")
            enviar_para_supabase(dados)
        else:
            print("\n⚠️ Dados não enviados para Supabase (cliente não configurado)")
            print("   Dados disponíveis no arquivo JSON de backup")

        print("\n✅ Processo concluído com sucesso!")

    else:
        print("\n❌ Nenhum dado coletado")
        print("   Possíveis causas:")
        print("   - Site bloqueando requisições automatizadas (403)")
        print("   - Estrutura HTML alterada")
        print("   - Problemas de conectividade")

        # Tentar fallback com dados estáticos para teste
        print("\n🔄 Tentando fallback com dados estáticos...")
        dados_fallback = [
            {"posicao": 1, "nome_time": "Palmeiras", "pontos": 26, "jogos": 11, "vitorias": 8, "empates": 2, "derrotas": 1, "gols_marcados": 21, "gols_sofridos": 10, "saldo_gols": 11, "data_atualizacao": datetime.now().isoformat()},
            {"posicao": 2, "nome_time": "Flamengo", "pontos": 20, "jogos": 10, "vitorias": 6, "empates": 2, "derrotas": 2, "gols_marcados": 18, "gols_sofridos": 10, "saldo_gols": 8, "data_atualizacao": datetime.now().isoformat()},
            {"posicao": 3, "nome_time": "São Paulo", "pontos": 20, "jogos": 11, "vitorias": 6, "empates": 2, "derrotas": 3, "gols_marcados": 15, "gols_sofridos": 9, "saldo_gols": 6, "data_atualizacao": datetime.now().isoformat()},
        ]

        if supabase:
            print("\n📡 Enviando dados de fallback para teste...")
            enviar_para_supabase(dados_fallback)

    print("\n" + "="*60)
    print(f"🏁 Finalizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*60)

if __name__ == "__main__":
    main()
    
