# Futmonitor
Dados futebol 

# Scraper Brasileirão Série A - Supabase

Este projeto faz scraping dos dados da tabela de classificação do Brasileirão Série A 
do site ogol.com.br e envia para uma tabela no Supabase.

## 📋 Pré-requisitos

- Python 3.8+
- Conta no Supabase (https://supabase.com)
- URL e chave de API do Supabase

## 🚀 Configuração

1. **Instalar dependências:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configurar variáveis de ambiente:**
   Crie um arquivo `.env` na raiz do projeto:
   ```
   SUPABASE_URL=https://seu-projeto.supabase.co
   SUPABASE_KEY=sua_chave_anon_aqui
   ```

3. **Criar tabela no Supabase:**
   Execute o script SQL `create_table_brasileirao.sql` no SQL Editor do Supabase

4. **Executar o scraper:**
   ```bash
   python scraper_brasileirao.py
   ```

## 📊 Estrutura dos Dados

Os seguintes campos são coletados:
- `posicao`: Posição na tabela (1-20)
- `nome_time`: Nome do time
- `pontos`: Pontos conquistados
- `jogos`: Jogos disputados
- `vitorias`: Número de vitórias
- `empates`: Número de empates
- `derrotas`: Número de derrotas
- `gols_marcados`: Gols marcados
- `gols_sofridos`: Gols sofridos
- `saldo_gols`: Saldo de gols
- `data_atualizacao`: Data/hora da atualização

## 🔄 Automação

Para executar automaticamente, configure um agendamento (cron job) ou 
use GitHub Actions conforme necessidade.
