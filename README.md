# Coordenador de Download do YouTube
Um coordenador de tarefas distribuído para download de vídeos do YouTube (ou execução de qualquer outras tarefas relacionadas a vídeos do YouTube) usando Google Planilhas como uma fila de tarefas centralizada. Este sistema permite que múltiplas máquinas trabalhem juntas, expandindo automaticamente canais/playlists do YouTube em tarefas de vídeos individuais e coordenando o trabalho entre os trabalhadores.

## Funcionalidades
- **Processamento Distribuído de Tarefas**: Múltiplas máquinas podem trabalhar na mesma fila simultaneamente
- **Integração com Google Planilhas**: Usa Google Planilhas como uma fila de tarefas centralizada e legível para humanos
- **Expansão Automática de Fontes**: Converte canais, playlists e vídeos individuais do YouTube em tarefas individuais
- **Tolerância a Falhas**: Lida com tarefas travadas, tentativas de reexecução e filas de carta morta para conteúdo problemático
- **Importação de Fontes via Arquivo**: Importa automaticamente novas fontes de arquivos de texto
- **Monitoramento de Saúde dos Trabalhadores**: Rastreia status e atividade dos trabalhadores
- **Gerenciamento de Resultados**: Organiza o conteúdo baixado e fornece ferramentas para manipulação de resultados

## Pré-requisitos
- Python 3.8 ou superior
- Conta do Google Cloud Platform com API do Sheets habilitada
- Credenciais de Conta de Serviço do Google com acesso à sua planilha de destino

## Instalação
### Opção 1: Instalar do código-fonte como biblioteca usando pip
```bash
pip install git+https://github.com/AndreKoraleski/Youtube-Download-Coordinator.git
```
### Estamos considerando adicionar uma forma de instalar via PyPI.

## Configuração
### 1. Configuração do Google Planilhas
1. Crie uma Planilha do Google com as seguintes abas:
   - **Sources**: Onde canais/playlists do YouTube são adicionados
   - **Video Tasks**: Tarefas individuais de download de vídeo
   - **Dead-Letter Sources**: Fontes que falharam após tentativas máximas
   - **Dead-Letter Tasks**: Tarefas que falharam após tentativas máximas  
   - **Workers**: Status dos trabalhadores e monitoramento de saúde

2. Configure as colunas necessárias em cada aba:

**Aba Sources:**
```
ID | URL | Status | ClaimedBy | ClaimedAt | Name | Gender | Accent | ContentType | Type | MultispeakerPercentage | RetryCount | LastError
```

**Aba Video Tasks:**
```
ID | SourceID | URL | Status | Duration | ClaimedBy | ClaimedAt | RetryCount | LastError
```

**Aba Workers:**
```
Hostname | LastSeen | Status
```

### 2. Credenciais do Google Cloud
1. Crie um Projeto no Google Cloud
2. Habilite a API do Google Planilhas
3. Crie uma Conta de Serviço e baixe o arquivo de credenciais JSON
4. Compartilhe sua Planilha do Google com o email da conta de serviço (dê permissões de Editor)

### 3. Configuração
Crie sua configuração e inicialize o coordenador:
```python
from youtube_download_coordinator import Config, Coordinator

config = Config(
    credentials_file="caminho/para/suas/credenciais.json",
    spreadsheet_id="id_da_sua_planilha_google",
    sources_file_path="sources.txt",  # Opcional: para importação de fontes via arquivo
    results_dir="downloads",
    selected_dir="selected"
)

coordinator = Coordinator(config)
```

## Uso
### Padrão de Uso Básico
```python
import yt_dlp
from youtube_download_coordinator import Config, Coordinator

def download_video(url: str):
    """Sua função personalizada de processamento"""
    ydl_opts = {
        'outtmpl': f'{config.results_dir}/%(id)s/%(title)s.%(ext)s',
        # Adicione suas opções do yt-dlp aqui
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

config = Config(
    credentials_file="credentials.json",
    spreadsheet_id="id_da_sua_planilha"
)

coordinator = Coordinator(config)

# Processar tarefas continuamente
while True:
    if not coordinator.process_next_task(download_video):
        print("Nenhuma tarefa disponível, aguardando...")
        time.sleep(30)
```

### Importação de Fontes via Arquivo
Crie um arquivo `sources.txt` com uma fonte por linha:
```
https://www.youtube.com/@channel1|Nome do Canal|Female|American|Educational|Channel|15.5
https://www.youtube.com/playlist?list=PLxxx|Nome da Playlist|Male|British|Entertainment|Playlist|5.0
https://www.youtube.com/watch?v=xxxxx|Título do Vídeo|Female|Canadian|Tutorial|Video|0
```
Formato: `URL|Nome|Gênero|Sotaque|TipoConteúdo|Tipo|PorcentagemMultifalante`

O coordenador importará automaticamente novas fontes quando o arquivo for alterado.

### Gerenciamento de Resultados
```python
# Mover resultados de uma fonte específica para o diretório selecionado
coordinator.manage_results(source_id="123")

# Mover todos os resultados de volta para o diretório principal de resultados
coordinator.manage_results()
```

## Opções de Configuração
A classe `Config` suporta personalização extensiva:

### Configurações Principais
- `credentials_file`: Caminho para o arquivo JSON da Conta de Serviço do Google
- `spreadsheet_id`: ID do documento Google Planilhas
- `sources_file_path`: Caminho opcional para arquivo de importação de fontes
- `results_dir`: Diretório para conteúdo baixado (padrão: 'results')
- `selected_dir`: Diretório para resultados selecionados (padrão: 'selected')
- `api_wait_seconds`: Atraso entre chamadas da API (padrão: 1.0)

### Nomes das Abas
- `sources_worksheet_name`: Nome da aba de fontes (padrão: 'Sources')
- `video_tasks_worksheet_name`: Nome da aba de tarefas de vídeo (padrão: 'Video Tasks')
- `source_dead_letter_worksheet_name`: Fontes carta morta (padrão: 'Dead-Letter Sources')
- `task_dead_letter_worksheet_name`: Tarefas carta morta (padrão: 'Dead-Letter Tasks')
- `workers_worksheet_name`: Monitoramento de trabalhadores (padrão: 'Workers')

### Valores de Status
- `STATUS_PENDING`: 'pending'
- `STATUS_IN_PROGRESS`: 'in-progress'  
- `STATUS_DONE`: 'done'
- `STATUS_ERROR`: 'error'
- `STATUS_ACTIVE`: 'active'

### Ajuste do Sistema Distribuído
- `claim_jitter_seconds`: Atraso aleatório ao reivindicar tarefas (padrão: 5)
- `stalled_task_timeout_minutes`: Timeout para tarefas travadas (padrão: 60)
- `max_retries`: Tentativas máximas de reexecução (padrão: 3)
- `video_task_batch_size`: Tamanho do lote para adicionar tarefas (padrão: 25)
- `health_check_interval_seconds`: Frequência de verificação de saúde dos trabalhadores (padrão: 60)

### Tratamento de Erros
- `fatal_error_substrings`: Lista de mensagens de erro que acionam carta morta imediata

## Arquitetura
### Fluxo de Tarefas
1. **Sources**: URLs do YouTube (canais, playlists, vídeos) são adicionadas à aba Sources
2. **Expansão**: Trabalhadores reivindicam fontes e as expandem em tarefas de vídeos individuais
3. **Processamento**: Trabalhadores reivindicam tarefas de vídeo e executam sua função personalizada de processamento
4. **Resultados**: Tarefas concluídas são marcadas como feitas, tarefas com falha são reexecutadas ou enviadas para carta morta

### Tolerância a Falhas
- **Recuperação de Tarefas Travadas**: Detecta e recupera automaticamente tarefas travadas
- **Lógica de Reexecução**: Tarefas com falha são reexecutadas até o limite máximo de tentativas
- **Filas de Carta Morta**: Tarefas/fontes permanentemente com falha são movidas para abas separadas
- **Verificação de Reivindicação**: Garante que apenas um trabalhador pode reivindicar uma tarefa por vez

### Coordenação de Trabalhadores  
- **Monitoramento de Saúde**: Trabalhadores relatam periodicamente seu status
- **Reivindicações com Jitter**: Atrasos aleatórios previnem problemas de enxame
- **Operações Atômicas**: Atualizações de planilha usam padrões atômicos de reivindicação e verificação

## Monitoramento
Monitore seu sistema através da interface do Google Planilhas:
- **Aba Sources**: Rastreie o progresso da expansão de fontes
- **Aba Video Tasks**: Monitore o status de tarefas individuais
- **Aba Workers**: Visualize trabalhadores ativos e sua última atividade
- **Abas Dead Letter**: Revise tarefas com falha que precisam de atenção

## Solução de Problemas
### Problemas Comuns
**Erros de Autenticação**
- Verifique se o caminho do arquivo JSON da conta de serviço está correto
- Certifique-se de que a conta de serviço tem acesso à sua planilha
- Verifique se a API do Sheets está habilitada no Google Cloud

**Nenhuma Tarefa Encontrada**
- Verifique se os nomes das abas correspondem à sua configuração
- Verifique se as fontes têm status 'pending'
- Certifique-se de que sua planilha tem os cabeçalhos de coluna corretos

**Tarefas Ficando Presas**
- Verifique a configuração `stalled_task_timeout_minutes`
- Revise as filas de carta morta para padrões de erro
- Verifique se sua função de processamento lida com erros adequadamente

### Log de Debug
Habilite log detalhado:
```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('youtube_download_coordinator')
logger.setLevel(logging.DEBUG)
```

## Contribuindo
Contribuições são bem-vindas! Por favor, sinta-se à vontade para enviar um Pull Request. Para mudanças importantes, abra primeiro uma issue para discutir o que você gostaria de alterar.

## Licença
Este projeto está licenciado sob a Licença Pública Geral GNU v3.0 - veja o arquivo [LICENSE](LICENSE) para detalhes.

## Agradecimentos
- Construído com [yt-dlp](https://github.com/yt-dlp/yt-dlp) para extração de conteúdo (não download) do YouTube