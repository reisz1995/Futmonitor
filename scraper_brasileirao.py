import os
import time
import random
from datetime import datetime

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

def scrape_brasileirao_seleniumbase():
    """
    Faz scraping usando SeleniumBase UC Mode para bypass de Cloudflare
    """
    try:
        from seleniumbase import SB
        from bs4 import BeautifulSoup

        url = "https://www.ogol.com.br/edicao/brasileirao-serie-a-2026/210277"

        print("🏆 Iniciando scraping com SeleniumBase UC Mode...")
        print(f"📍 URL: {url}")

        with SB(uc=True, headless=True) as sb:
            # Abrir página com reconexão automática
            sb.uc_open_with_reconnect(url, reconnect_time=5)

            # Aguardar carregamento
            sb.sleep(3)

            # Verificar se passou do Cloudflare
            page_source = sb.get_page_source()
            if "cloudflare" in page_source.lower() or "just a moment" in page_source.lower():
                print("⏳ Detectada página de challenge, aguardando...")
                sb.sleep(5)
                page_source = sb.get_page_source()

            # Verificar se carregou conteúdo real
            if "Brasileirão" in page_source or "classificação" in page_source.lower() or "Palmeiras" in page_source:
                print("✅ Página carregada com sucesso!")
            else:
                print("⚠️ Conteúdo pode não estar completo, mas prosseguindo...")

            # Extrair HTML
            html = sb.get_page_source()

            # Parse com BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')

            # Salvar HTML para debug
            with open('debug_page.html', 'w', encoding='utf-8') as f:
                f.write(soup.prettify())
            print("💾 HTML salvo em debug_page.html")

            # Extrair dados da tabela
            dados_times = extrair_dados_tabela(soup)

            return dados_times

    except ImportError:
        print("❌ SeleniumBase não instalado. Use: pip install seleniumbase")
        return None
    except Exception as e:
        print(f"❌ Erro com SeleniumBase: {e}")
        import traceback
        traceback.print_exc()
        return None

def extrair_dados_tabela(soup):
    """Extrai dados da tabela de classificação - versão melhorada"""

    dados_times = []

    print("🔍 Procurando tabela de classificação...")

    # Estratégia 1: Procurar por classe específica
    tabela = soup.find('table', {'class': 'classificacao'})
    if tabela:
        print("✅ Tabela encontrada por classe 'classificacao'")

    # Estratégia 2: Procurar por outras classes comuns
    if not tabela:
        tabela = soup.find('table', {'class': 'zebra'})
        if tabela:
            print("✅ Tabela encontrada por classe 'zebra'")

    if not tabela:
        tabela = soup.find('table', {'class': 'std'})
        if tabela:
            print("✅ Tabela encontrada por classe 'std'")

    # Estratégia 3: Procurar em divs específicas
    if not tabela:
        div_tabela = soup.find('div', {'id': 'classificacao'})
        if div_tabela:
            tabela = div_tabela.find('table')
            if tabela:
                print("✅ Tabela encontrada em div#classificacao")

    if not tabela:
        div_tabela = soup.find('div', {'class': 'tabela'})
        if div_tabela:
            tabela = div_tabela.find('table')
            if tabela:
                print("✅ Tabela encontrada em div.tabela")

    # Estratégia 4: Procurar por tabela com texto específico
    if not tabela:
        tabelas = soup.find_all('table')
        print(f"🔍 Total de tabelas encontradas: {len(tabelas)}")

        for idx, t in enumerate(tabelas):
            # Verificar se a tabela contém dados de classificação
            texto = t.get_text()

            # Procurar por indicadores de classificação
            if any(indicador in texto for indicador in ['Palmeiras', 'Flamengo', 'São Paulo', 'Pontos', 'Jogos', 'Vitorias']):
                linhas = t.find_all('tr')
                print(f"   Tabela {idx+1}: {len(linhas)} linhas - contém times brasileiros")

                # Se tiver entre 10-25 linhas, provavelmente é a tabela de classificação
                if 10 <= len(linhas) <= 25:
                    tabela = t
                    print(f"✅ Tabela selecionada: {len(linhas)} linhas (índice {idx+1})")
                    break

    if not tabela:
        print("❌ Nenhuma tabela de classificação encontrada")
        return []

    linhas = tabela.find_all('tr')
    print(f"📊 Processando {len(linhas)} linhas da tabela...")

    # Ignorar primeira linha se for header
    primeira_linha = linhas[0] if linhas else None
    if primeira_linha:
        ths = primeira_linha.find_all('th')
        if ths:
            print(f"   Primeira linha é header com {len(ths)} colunas")
            linhas = linhas[1:]  # Remover header

    for idx, linha in enumerate(linhas):
        colunas = linha.find_all(['td', 'th'])

        # Depuração: mostrar primeira linha
        if idx == 0:
            print(f"   Primeira linha de dados: {len(colunas)} colunas")
            for i, col in enumerate(colunas[:5]):
                print(f"      Coluna {i}: '{col.get_text(strip=True)[:30]}'")

        # Precisamos de pelo menos 10 colunas (pos, time, pts, j, v, e, d, gm, gc, sg)
        if len(colunas) >= 10:
            try:
                texto_colunas = [col.get_text(strip=True) for col in colunas]

                # Verificar se primeira coluna é número (posição)
                posicao_str = texto_colunas[0]
                if not posicao_str.isdigit():
                    continue

                posicao = int(posicao_str)

                # Extrair nome do time (geralmente na segunda coluna)
                nome_time = texto_colunas[1]

                # Limpar nome do time - remover possíveis números ou símbolos extras
                nome_time = ' '.join(nome_time.split())

                # Extrair estatísticas numéricas
                def extrair_numero(texto):
                    """Extrai número de texto, tratando casos especiais"""
                    if not texto:
                        return 0
                    # Remover caracteres não numéricos exceto sinal negativo
                    limpo = ''.join(c for c in texto if c.isdigit() or c == '-')
                    try:
                        return int(limpo) if limpo else 0
                    except:
                        return 0

                pontos = extrair_numero(texto_colunas[2])
                jogos = extrair_numero(texto_colunas[3])
                vitorias = extrair_numero(texto_colunas[4])
                empates = extrair_numero(texto_colunas[5])
                derrotas = extrair_numero(texto_colunas[6])
                gm = extrair_numero(texto_colunas[7])
                gc = extrair_numero(texto_colunas[8])

                # Saldo de gols pode ter sinal + ou -
                sg_str = texto_colunas[9].replace('+', '')
                sg = extrair_numero(sg_str)
                if texto_colunas[9].startswith('-'):
                    sg = -sg

                # Validar dados básicos
                if posicao > 0 and nome_time and len(nome_time) > 2:
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
                if idx < 3:  # Mostrar erros das primeiras linhas apenas
                    print(f"⚠️ Erro ao processar linha {idx+1}: {e}")
                    print(f"   Conteúdo: {texto_colunas[:5] if 'texto_colunas' in locals() else 'N/A'}")
                continue

    print(f"✅ {len(dados_times)} times processados com sucesso")
    return dados_times

def enviar_para_supabase(dados):
    """Envia dados para o Supabase"""
    if not supabase or not dados:
        print("❌ Cliente Supabase ou dados não disponíveis")
        return None

    try:
        print(f"📤 Enviando {len(dados)} registros para o Supabase...")

        # Limpar tabela antes (opcional)
        # print("🧹 Limpando tabela antiga...")
        # supabase.table('classificacao_brasileirao').delete().neq('id', 0).execute()

        # Inserir dados em batch
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
    print("🏆 SCRAPER BRASILEIRÃO SÉRIE A - v3.0")
    print(f"⏰ Iniciado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*60)

    dados = None

    # Tentar SeleniumBase
    print("\n🔄 Tentando com SeleniumBase UC Mode...")
    dados = scrape_brasileirao_seleniumbase()

    # Se falhar ou não obter dados, usar fallback
    if not dados or len(dados) == 0:
        print("\n❌ Scraping não obteve dados")
        print("🔄 Usando dados de fallback...")

        # Dados atualizados da Rodada 11 (do arquivo fornecido)
        dados = [
            {"posicao": 1, "nome_time": "Palmeiras", "pontos": 26, "jogos": 11, "vitorias": 8, "empates": 2, "derrotas": 1, "gols_marcados": 21, "gols_sofridos": 10, "saldo_gols": 11, "data_atualizacao": datetime.now().isoformat()},
            {"posicao": 2, "nome_time": "Flamengo", "pontos": 20, "jogos": 10, "vitorias": 6, "empates": 2, "derrotas": 2, "gols_marcados": 18, "gols_sofridos": 10, "saldo_gols": 8, "data_atualizacao": datetime.now().isoformat()},
            {"posicao": 3, "nome_time": "São Paulo", "pontos": 20, "jogos": 11, "vitorias": 6, "empates": 2, "derrotas": 3, "gols_marcados": 15, "gols_sofridos": 9, "saldo_gols": 6, "data_atualizacao": datetime.now().isoformat()},
            {"posicao": 4, "nome_time": "Fluminense", "pontos": 20, "jogos": 11, "vitorias": 6, "empates": 2, "derrotas": 3, "gols_marcados": 18, "gols_sofridos": 13, "saldo_gols": 5, "data_atualizacao": datetime.now().isoformat()},
            {"posicao": 5, "nome_time": "Bahia", "pontos": 20, "jogos": 10, "vitorias": 6, "empates": 2, "derrotas": 2, "gols_marcados": 15, "gols_sofridos": 10, "saldo_gols": 5, "data_atualizacao": datetime.now().isoformat()},
            {"posicao": 6, "nome_time": "Athletico Paranaense", "pontos": 19, "jogos": 11, "vitorias": 6, "empates": 1, "derrotas": 4, "gols_marcados": 17, "gols_sofridos": 13, "saldo_gols": 4, "data_atualizacao": datetime.now().isoformat()},
            {"posicao": 7, "nome_time": "Coritiba", "pontos": 16, "jogos": 11, "vitorias": 4, "empates": 4, "derrotas": 3, "gols_marcados": 13, "gols_sofridos": 12, "saldo_gols": 1, "data_atualizacao": datetime.now().isoformat()},
            {"posicao": 8, "nome_time": "Atlético Mineiro", "pontos": 14, "jogos": 11, "vitorias": 4, "empates": 2, "derrotas": 5, "gols_marcados": 14, "gols_sofridos": 13, "saldo_gols": 1, "data_atualizacao": datetime.now().isoformat()},
            {"posicao": 9, "nome_time": "Red Bull Bragantino", "pontos": 14, "jogos": 11, "vitorias": 4, "empates": 2, "derrotas": 5, "gols_marcados": 11, "gols_sofridos": 12, "saldo_gols": -1, "data_atualizacao": datetime.now().isoformat()},
            {"posicao": 10, "nome_time": "Vitória", "pontos": 14, "jogos": 10, "vitorias": 4, "empates": 2, "derrotas": 4, "gols_marcados": 11, "gols_sofridos": 14, "saldo_gols": -3, "data_atualizacao": datetime.now().isoformat()},
            {"posicao": 11, "nome_time": "Botafogo", "pontos": 13, "jogos": 10, "vitorias": 4, "empates": 1, "derrotas": 5, "gols_marcados": 18, "gols_sofridos": 21, "saldo_gols": -3, "data_atualizacao": datetime.now().isoformat()},
            {"posicao": 12, "nome_time": "Grêmio", "pontos": 13, "jogos": 11, "vitorias": 3, "empates": 4, "derrotas": 4, "gols_marcados": 14, "gols_sofridos": 14, "saldo_gols": 0, "data_atualizacao": datetime.now().isoformat()},
            {"posicao": 13, "nome_time": "Vasco", "pontos": 13, "jogos": 11, "vitorias": 3, "empates": 4, "derrotas": 4, "gols_marcados": 16, "gols_sofridos": 17, "saldo_gols": -1, "data_atualizacao": datetime.now().isoformat()},
            {"posicao": 14, "nome_time": "Internacional", "pontos": 13, "jogos": 11, "vitorias": 3, "empates": 4, "derrotas": 4, "gols_marcados": 9, "gols_sofridos": 10, "saldo_gols": -1, "data_atualizacao": datetime.now().isoformat()},
            {"posicao": 15, "nome_time": "Santos", "pontos": 13, "jogos": 11, "vitorias": 3, "empates": 4, "derrotas": 4, "gols_marcados": 14, "gols_sofridos": 16, "saldo_gols": -2, "data_atualizacao": datetime.now().isoformat()},
            {"posicao": 16, "nome_time": "Corinthians", "pontos": 11, "jogos": 11, "vitorias": 2, "empates": 5, "derrotas": 4, "gols_marcados": 8, "gols_sofridos": 11, "saldo_gols": -3, "data_atualizacao": datetime.now().isoformat()},
            {"posicao": 17, "nome_time": "Cruzeiro", "pontos": 10, "jogos": 11, "vitorias": 2, "empates": 4, "derrotas": 5, "gols_marcados": 14, "gols_sofridos": 21, "saldo_gols": -7, "data_atualizacao": datetime.now().isoformat()},
            {"posicao": 18, "nome_time": "Remo", "pontos": 8, "jogos": 11, "vitorias": 1, "empates": 5, "derrotas": 5, "gols_marcados": 11, "gols_sofridos": 18, "saldo_gols": -7, "data_atualizacao": datetime.now().isoformat()},
            {"posicao": 19, "nome_time": "Chapecoense", "pontos": 8, "jogos": 10, "vitorias": 1, "empates": 5, "derrotas": 4, "gols_marcados": 10, "gols_sofridos": 18, "saldo_gols": -8, "data_atualizacao": datetime.now().isoformat()},
            {"posicao": 20, "nome_time": "Mirassol", "pontos": 6, "jogos": 10, "vitorias": 1, "empates": 3, "derrotas": 6, "gols_marcados": 11, "gols_sofridos": 16, "saldo_gols": -5, "data_atualizacao": datetime.now().isoformat()},
        ]

    if dados:
        print(f"\n📊 Dados coletados: {len(dados)} times")

        # Mostrar preview
        print("\n📈 Preview da classificação:")
        print("-" * 60)
        for time in dados[:5]:
            print(f"{time['posicao']:2d}. {time['nome_time'][:30]:30s} - {time['pontos']:2d} pts ({time['jogos']}J)")
        print("...")
        for time in dados[-3:]:
            print(f"{time['posicao']:2d}. {time['nome_time'][:30]:30s} - {time['pontos']:2d} pts ({time['jogos']}J)")
        print("-" * 60)

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
        print("\n❌ Nenhum dado disponível")

    print("\n" + "="*60)
    print(f"🏁 Finalizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*60)

if __name__ == "__main__":
    main()
