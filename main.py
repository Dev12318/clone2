import os
import json
import asyncio
from telethon import TelegramClient, events, sync
from datetime import datetime, timedelta
import logging

# Configurações de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurações
API_ID = int(os.getenv('API_ID'))  # Obtém do ambiente
API_HASH = os.getenv('API_HASH')   # Obtém do ambiente
SESSION_FILE = "data/session"
CONFIG_FILE = "data/config.json"

# Cria pasta para dados
os.makedirs("data", exist_ok=True)

# Configurações do Telethon
client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

# Carrega configurações
def load_config():
    default_config = {
        "source_group": int(os.getenv('SOURCE_GROUP_ID')),
        "dest_group": int(os.getenv('DEST_GROUP_ID')),
        "interval_seconds": float(os.getenv('INTERVAL_SECONDS', 8)),
        "message_limit": int(os.getenv('MESSAGE_LIMIT', 100)),
        "last_clone_time": None
    }
    if not os.path.exists(CONFIG_FILE):
        return default_config
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        for key, value in default_config.items():
            if key not in config:
                config[key] = value
        return config

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

# Função para clonar apenas mídias e fotos
async def clone_media():
    config = load_config()
    source_group_id = config['source_group']
    dest_group_id = config['dest_group']
    interval_seconds = config['interval_seconds']
    message_limit = config['message_limit']

    if not source_group_id or not dest_group_id:
        logger.error("Grupos de origem ou destino não definidos nas variáveis de ambiente.")
        return False

    logger.info("Obtendo informações do grupo de origem...")
    try:
        source_group = await client.get_entity(source_group_id)
        dest_group = await client.get_entity(dest_group_id)
    except Exception as e:
        logger.error(f"Erro ao acessar os grupos: {e}")
        return False

    logger.info(f"Clonando até {message_limit} mídias/fotos do grupo '{source_group.title}'...")
    success = True
    try:
        async for message in client.iter_messages(source_group_id, limit=message_limit):
            if message.media and (message.photo or message.video or message.document):
                try:
                    await client.send_file(dest_group_id, message.media, caption=message.text or '')
                    logger.info(f"Mídia clonada (ID {message.id})")
                    await asyncio.sleep(interval_seconds)
                except Exception as e:
                    logger.error(f"Erro ao clonar mídia (ID {message.id}): {e}")
                    success = False
        if success:
            logger.info(f"✅ Clonagem de mídias do grupo '{source_group.title}' concluída com sucesso!")
        else:
            logger.warning(f"⚠️ Clonagem do grupo '{source_group.title}' concluída com alguns erros.")
        config['last_clone_time'] = datetime.now().isoformat()
        save_config(config)
        return success
    except Exception as e:
        logger.error(f"Erro ao clonar mídias: {e}")
        logger.error(f"❌ Clonagem do grupo '{source_group.title}' falhou.")
        return False

# Função para exibir ticks no terminal
async def tick_until_next_clone():
    config = load_config()
    last_clone_time = config.get('last_clone_time')
    if last_clone_time:
        last_clone = datetime.fromisoformat(last_clone_time)
        next_clone = last_clone + timedelta(hours=24)
    else:
        next_clone = datetime.now()

    while True:
        now = datetime.now()
        if now >= next_clone:
            logger.info("Iniciando novo ciclo de clonagem...")
            await clone_media()
            next_clone = datetime.now() + timedelta(hours=24)
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
            logger.error("Sessão não autorizada. Configure as variáveis de ambiente PHONE_NUMBER e execute o script localmente primeiro.")
            return
        logger.info("Cliente Telegram conectado com sucesso!")
        await tick_until_next_clone()
    except Exception as e:
        logger.error(f"Erro na inicialização: {e}")

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
