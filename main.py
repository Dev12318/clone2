from telethon import TelegramClient, events, sync
import os
import json
import asyncio

# Configurações
API_ID = 20595253  # Substitua pelo seu api_id
API_HASH = "89c2e5d1e96d8f17379e3e17c2ac71aa"  # Substitua pelo seu api_hash
SESSION_FILE = "data/session"

# Cria pasta para dados
os.makedirs("data", exist_ok=True)

# Configurações do Telethon
client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

# Armazena configurações
CONFIG_FILE = "data/config.json"
def load_config():
    default_config = {
        "source_group": None,
        "dest_group": None,
        "interval_seconds": 8,  # Intervalo padrão de 60 segundos entre mídias
        "message_order": 0,  # Padrão: 1 (mais recentes primeiro, de cima para baixo)
        "message_limit": 100  # Limite padrão de 100 mensagens por clonagem
    }
    if not os.path.exists(CONFIG_FILE):
        return default_config
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        # Garante que todas as chaves existam no config carregado
        for key, value in default_config.items():
            if key not in config:
                config[key] = value
        return config

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

config = load_config()

# Menu principal
def show_menu():
    print("\n=== Script de Clonagem de Grupos (Telegram) ===")
    print("Escolha uma opção:")
    print("1️⃣ Definir grupos (origem e destino)")
    print("2️⃣ Mostrar configurações atuais")
    print("3️⃣ Iniciar clonagem")
    print("4️⃣ Criar nova sessão")
    print("5️⃣ Listar IDs de todos os meus grupos")
    print("6️⃣ Configurar intervalo, ordem e limite de mensagens")
    print("Digite o número da opção (1, 2, 3, 4, 5 ou 6), ou 'sair' para encerrar:")

# Função para listar IDs de grupos
async def list_group_ids():
    print("\nListando IDs de todos os grupos dos quais você é membro...")
    try:
        async for dialog in client.iter_dialogs():
            if hasattr(dialog.entity, 'megagroup') and dialog.entity.megagroup:
                print(f"Grupo: {dialog.name} | ID: {dialog.entity.id}")
            elif hasattr(dialog.entity, 'group') and dialog.entity.group:
                print(f"Grupo: {dialog.name} | ID: {dialog.entity.id}")
    except Exception as e:
        print(f"Erro ao listar grupos: {e}")

# Função para clonar mensagens
async def clone_group():
    source_group_id = config['source_group']
    dest_group_id = config['dest_group']
    interval_seconds = config['interval_seconds']
    message_order = config['message_order']
    message_limit = config['message_limit']

    if not source_group_id or not dest_group_id:
        print("Erro: Defina os grupos de origem e destino primeiro (opção 1).")
        return

    print("Obtendo informações do grupo de origem...")
    try:
        source_group = await client.get_entity(source_group_id)
        dest_group = await client.get_entity(dest_group_id)
    except Exception as e:
        print(f"Erro ao acessar os grupos: {e}")
        return

    # Verifica se o grupo de origem é um supergrupo com canais
    channels = []
    try:
        async for chat in client.iter_dialogs():
            if chat.entity.id == source_group_id:
                async for message in client.iter_messages(chat.entity, limit=message_limit, reverse=(message_order == 0)):
                    if hasattr(message, 'chat') and message.chat and message.chat.megagroup:
                        channels.append(message.chat)
                break
    except Exception as e:
        print(f"Erro ao obter canais: {e}. Continuando com mensagens do grupo principal...")

# Se não houver canais, copia mensagens diretamente do grupo de origem
    if not channels:
        print(f"Clonando até {message_limit} mensagens diretamente do grupo de origem...")
        success = True
        try:
            async for message in client.iter_messages(source_group_id, limit=message_limit, reverse=(message_order == 0)):
                try:
                    if message.text:
                        await client.send_message(dest_group_id, message.text)
                    if message.media:
                        await client.send_file(dest_group_id, message.media)
                        await asyncio.sleep(interval_seconds)  # Intervalo apenas para mídias
                except Exception as e:
                    print(f"Erro ao clonar mensagem (ID {message.id}): {e}")
                    success = False
            if success:
                print(f"✅ Clonagem de mensagens do grupo '{source_group.title}' concluída com sucesso!")
            else:
                print(f"⚠️ Clonagem do grupo '{source_group.title}' concluída com alguns erros.")
        except Exception as e:
            print(f"Erro ao clonar mensagens: {e}")
            print(f"❌ Clonagem do grupo '{source_group.title}' falhou.")
        return

    # Se houver canais, copia mensagens de cada canal para o grupo de destino
    for channel in channels:
        print(f"Clonando até {message_limit} mensagens do canal '{channel.title}'...")
        success = True
        try:
            async for message in client.iter_messages(channel.id, limit=message_limit, reverse=(message_order == 0)):
                try:
                    if message.text:
                        await client.send_message(dest_group_id, f"[Canal: {channel.title}] {message.text}")
                    if message.media:
                        await client.send_file(dest_group_id, message.media, caption=f"[Canal: {channel.title}]")
                        await asyncio.sleep(interval_seconds)  # Intervalo apenas para mídias
                except Exception as e:
                    print(f"Erro ao clonar mensagem do canal '{channel.title}' (ID {message.id}): {e}")
                    success = False
            if success:
                print(f"✅ Clonagem de mensagens do canal '{channel.title}' concluída com sucesso!")
            else:
                print(f"⚠️ Clonagem do canal '{channel.title}' concluída com alguns erros.")
        except Exception as e:
            print(f"Erro ao clonar mensagens do canal '{channel.title}': {e}")
            print(f"❌ Clonagem do canal '{channel.title}' falhou.")

# Função principal
async def main():
    # Conecta ao Telegram
    await client.start()
    if not await client.is_user_authorized():
        phone = input("Digite seu número de telefone (ex.: +5511999999999): ")
        await client.send_code_request(phone)
        code = input("Digite o código de verificação enviado ao seu Telegram: ")
        await client.sign_in(phone, code)
        print("Sessão criada com sucesso!")

    while True:
        show_menu()
        choice = input("> ").strip()

        if choice.lower() == 'sair':
            print("Encerrando o script...")
            break

        if choice == '1':
            source_id = input("Digite o ID do grupo de origem: ")
            try:
                config['source_group'] = int(source_id)
            except ValueError:
                print("ID inválido. Deve ser um número.")
                continue
            dest_id = input("Digite o ID do grupo de destino: ")
            try:
                config['dest_group'] = int(dest_id)
            except ValueError:
                print("ID inválido. Deve ser um número.")
                continue
            save_config(config)
            print("Grupos definidos com sucesso!")

        elif choice == '2':
            source = config.get('source_group', 'Não definido')
            dest = config.get('dest_group', 'Não definido')
            interval = config.get('interval_seconds', 60)
            order = config.get('message_order', 1)
            limit = config.get('message_limit', 100)
            print(f"\nConfigurações atuais:")
            print(f"Origem: {source}")
            print(f"Destino: {dest}")
            print(f"Intervalo entre mensagens com mídia: {interval} segundos")
            print(f"Ordem das mensagens: {'Mais recentes primeiro (de cima para baixo)' if order == 1 else 'Mais antigas primeiro (de baixo para cima)'}")
            print(f"Limite de mensagens por clonagem: {limit}")

        elif choice == '3':
            print("Iniciando clonagem... Isso pode levar um tempo.")
            await clone_group()
            print("Clonagem concluída!")

        elif choice == '4':
            print("Criando nova sessão...")
            os.remove(SESSION_FILE) if os.path.exists(SESSION_FILE) else None
            phone = input("Digite seu número de telefone (ex.: +5511999999999): ")
            try:
                await client.send_code_request(phone)
                code = input("Digite o código de verificação enviado ao seu Telegram: ")
                await client.sign_in(phone, code)
                print("Nova sessão criada com sucesso!")
            except Exception as e:
                print(f"Erro ao criar nova sessão: {e}")

        elif choice == '5':
            await list_group_ids()

        elif choice == '6':
            interval = input("Digite o intervalo entre mensagens com mídia em segundos (ex.: 60): ")
            try:
                config['interval_seconds'] = float(interval)
            except ValueError:
                print("Intervalo inválido. Deve ser um número.")
                continue
            order = input("Digite a ordem das mensagens (1 para mais recentes primeiro, 0 para mais antigas primeiro): ")
            try:
                order = int(order)
                if order not in [0, 1]:
                    print("Ordem inválida. Use 1 ou 0.")
                    continue
                config['message_order'] = order
            except ValueError:
                print("Ordem inválida. Deve ser 1 ou 0.")
                continue
            limit = input("Digite o limite de mensagens por clonagem (ex.: 100): ")
            try:
                config['message_limit'] = int(limit)
            except ValueError:
                print("Limite inválido. Deve ser um número.")
                continue
            save_config(config)
            print("Configurações de clonagem definidas com sucesso!")

        else:
            print("Opção inválida. Digite 1, 2, 3, 4, 5 ou 6.")

# Executa o script
if __name__ == "__main__":  # Corrigido de 'name' para '__name__'
    with client:
        client.loop.run_until_complete(main())