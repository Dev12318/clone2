import os
import asyncio
from telethon import TelegramClient, events, sync
from datetime import datetime, timedelta
import logging
import json

# Configurações de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurações
API_ID = int(os.getenv('API_ID'))  # Obtém do ambiente
API_HASH = os.getenv('API_HASH')   # Obtém do ambiente
SESSION_FILE = "data/session"
LAST_CLONE_FILE = "data/last_clone.json"  # Arquivo pra persistir LAST_CLONE_TIME

# Configurações hardcodadas
SOURCE_GROUP_ID = -1002216934203
DEST_GROUP_ID = -1002812160351
INTERVAL_SECONDS = 20.0
MESSAGE_ORDER = 1  # 1 para mais recentes primeiro
MESSAGE_LIMIT = 260
DEFAULT_LAST_CLONE_TIME = "2025-08-01T13:23:00-03:00"  # 24 horas atrás do horário atual (02/08/2025 13:23 -03)

# Cria pasta para dados
os.makedirs("data", exist_ok=True)

# Configurações do Telethon
client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

# Função para carregar LAST_CLONE_TIME do arquivo ou variável de ambiente
def load_last_clone_time():
    # Tenta carregar do arquivo persistente
    if os.path.exists(LAST_CLONE_FILE):
        try:
            with open(LAST_CLONE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('last_clone_time', DEFAULT_LAST_CLONE_TIME)
        except Exception as e:
            logger.error(f"Erro ao carregar LAST_CLONE_TIME do arquivo: {e}")
    # Fallback para variável de ambiente ou padrão
    return os.getenv('LAST_CLONE_TIME', DEFAULT_LAST_CLONE_TIME)

# Função para salvar LAST_CLONE_TIME no arquivo
def save_last_clone_time(time_str):
    try:
        with open(LAST_CLONE_FILE, 'w') as f:
            json.dump({'last_clone_time': time_str}, f)
    except Exception as e:
        logger.error(f"Erro ao salvar LAST_CLONE_TIME no arquivo: {e}")

# Função para clonar apenas mídias e fotos
async def clone_media():
    if not SOURCE_GROUP_ID or not DEST_GROUP_ID:
        logger.error("Grupos de origem ou destino não definidos.")
        return False

    logger.info("Obtendo informações do grupo de origem...")
    try:
        source_group = await client.get_entity(SOURCE_GROUP_ID)
        dest_group = await client.get_entity(DEST_GROUP_ID)
    except Exception as e:
        logger.error(f"Erro ao acessar os grupos: {e}")
        return False

    logger.info(f"Clonando até {MESSAGE_LIMIT} mídias/fotos do grupo '{source_group.title}'...")
    success = True
    try:
        async for message in client.iter_messages(SOURCE_GROUP_ID, limit=MESSAGE_LIMIT, reverse=(MESSAGE_ORDER == 0)):
            if message.media and (message.photo or message.video or message.document):
                try:
                    await client.send_file(DEST_GROUP_ID, message.media, caption=message.text or '')
                    logger.info(f"Mídia clonada (ID {message.id})")
                    await asyncio.sleep(INTERVAL_SECONDS)
                except Exception as e:
                    logger.error(f"Erro ao clonar mídia (ID {message.id}): {e}")
                    success = False
        if success:
            logger.info(f"✅ Clonagem de mídias do grupo '{source_group.title}' concluída com sucesso!")
        else:
            logger.warning(f"⚠️ Clonagem do grupo '{source_group.title}' concluída com alguns erros.")
        return success
    except Exception as e:
        logger.error(f"Erro ao clonar mídias: {e}")
        logger.error(f"❌ Clonagem do grupo '{source_group.title}' falhou.")
        return False

# Função para exibir ticks no terminal
async def tick_until_next_clone():
    last_clone_time = load_last_clone_time()
    try:
        last_clone = datetime.fromisoformat(last_clone_time)
    except ValueError:
        logger.error("Formato inválido de LAST_CLONE_TIME. Iniciando clonagem imediatamente.")
        last_clone = datetime.now() - timedelta(hours=24)
    
    while True:
        now = datetime.now()
        next_clone = last_clone + timedelta(hours=24)
        if now >= next_clone:
            logger.info("Iniciando novo ciclo de clonagem...")
            # Atualiza LAST_CLONE_TIME antes da clonagem
            new_last_clone_time = datetime.now().isoformat()
            save_last_clone_time(new_last_clone_time)
            await clone_media()
            last_clone = datetime.fromisoformat(new_last_clone_time)
        else:
            time_left = (next_clone - now).total_seconds()
            hours, remainder = divmod(time_left, 3600)
            minutes, seconds = divmod(remainder, 60)
            logger.info(f"⏳ Próxima clonagem em {int(hours)}h {int(minutes)}m {int(seconds)}s")
            await asyncio.sleep(60)  # Tick a cada minuto

# Função principal
async def main():
    try:
        await client.start()
        if not await client.is_user_authorized():
            logger.error("Sessão não autorizada. Execute o script localmente primeiro para gerar a sessão.")
            return
        logger.info("Cliente Telegram conectado com sucesso!")
        await tick_until_next_clone()
    except Exception as e:
        logger.error(f"Erro na inicialização: {e}")

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
