import json
import logging
import asyncio
import os
from datetime import datetime
from telethon import TelegramClient
from telethon.errors import FloodWaitError, PeerIdInvalidError

# Конфигурация
api_id = '29758240'
api_hash = '45aa1a0337bf2ab7c931f4fa6a45b344'
session_folder = 'sessions'  # Папка для хранения файлов сессий
json_file = 'chats.json'
contacts_file = 'contacts.json'
log_file = 'logi.txt'

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Адрес и порт для TCP-сокета
HOST = '127.0.0.1'
PORT = 65432

# Параметры для задержки
group_timeout = 2
contact_timeout = 2

# Глобальные переменные для папок
group_folder = "info"
contact_folder = "coninfo"

# Глобальная переменная для количества аккаунтов
account_count = "all"

# Инициализация клиентов
clients = []

def load_json_from_file(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f'{filename} не найден. Возвращается пустой список.')
        return []

def log_to_file(log_message):
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_message + '\n')

def load_clients(session_folder, account_count):
    global clients
    clients = []  # Очищаем список клиентов перед загрузкой новых
    session_files = [f for f in os.listdir(session_folder) if f.endswith('.session')]
    if account_count == "all":
        account_count = len(session_files)
    else:
        account_count = int(account_count)
    session_files = session_files[:account_count]
    for session_file in session_files:
        session_path = os.path.join(session_folder, session_file)
        client = TelegramClient(session_path, api_id, api_hash)
        clients.append(client)

async def send_message_to_chat(client, chat_id, message):
    try:
        logger.debug(f'Попытка отправки сообщения в чат ID {chat_id}')
        await client.send_message(chat_id, message)
        logger.info(f'Сообщение отправлено в чат ID {chat_id}')
        return True
    except FloodWaitError as e:
        logger.warning(f'Ошибка Flood wait: нужно подождать {e.seconds} секунд')
        await asyncio.sleep(e.seconds)
        return False
    except PeerIdInvalidError as e:
        logger.error(f'Не удалось отправить сообщение в чат ID {chat_id}: {e}')
        return False
    except Exception as e:
        logger.error(f'Не удалось отправить сообщение в чат ID {chat_id}: {e}')
        return False

async def send_photo_to_chat(client, chat_id, photo_path, caption):
    try:
        logger.debug(f'Попытка отправки фото в чат ID {chat_id} с подписью {caption}')
        await client.send_file(chat_id, photo_path, caption=caption)
        logger.info(f'Фото отправлено в чат ID {chat_id}')
        return True
    except FloodWaitError as e:
        logger.warning(f'Ошибка Flood wait: нужно подождать {e.seconds} секунд')
        await asyncio.sleep(e.seconds)
        return False
    except PeerIdInvalidError as e:
        logger.error(f'Не удалось отправить фото в чат ID {chat_id}: {e}')
        return False
    except Exception as e:
        logger.error(f'Не удалось отправить фото в чат ID {chat_id}: {e}')
        return False

async def mass_send_message(json_file, folder, timeout):
    entries = load_json_from_file(json_file)
    files = os.listdir(folder)
    paired_files = {}

    # Поиск пар файлов с одинаковыми базовыми именами
    for file in files:
        base_name, ext = os.path.splitext(file)
        if base_name not in paired_files:
            paired_files[base_name] = {}
        paired_files[base_name][ext] = file

    successful_sends = 0
    failed_sends = 0

    for client in clients:
        await client.connect()
        for entry in entries:
            logger.info(f'Отправка сообщения в: {entry["title"]} (ID: {entry["id"]})')
            entity = None
            try:
                entity = await client.get_entity(entry['id'])
            except Exception as e:
                logger.error(f'Не удалось получить сущность для ID {entry["id"]}: {e}')
                failed_sends += 1
                continue

            for base_name, files in paired_files.items():
                if '.jpg' in files and '.txt' in files:
                    photo_path = os.path.join(folder, files['.jpg'])
                    caption_path = os.path.join(folder, files['.txt'])
                    with open(caption_path, 'r', encoding='utf-8') as f:
                        caption = f.read()
                    success = await send_photo_to_chat(client, entity, photo_path, caption)
                elif '.txt' in files:
                    text_path = os.path.join(folder, files['.txt'])
                    with open(text_path, 'r', encoding='utf-8') as f:
                        message = f.read()
                    success = await send_message_to_chat(client, entity, message)
                elif '.jpg' in files:
                    photo_path = os.path.join(folder, files['.jpg'])
                    success = await send_photo_to_chat(client, entity, photo_path, "")

                if success:
                    logger.info(f'Успешно отправлено сообщение в {entry["title"]}')
                    successful_sends += 1
                else:
                    logger.error(f'Не удалось отправить сообщение в {entry["title"]}')
                    failed_sends += 1
                await asyncio.sleep(timeout)  # Задержка между отправками

        await client.disconnect()

    # Логирование статистики
    log_message = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Успешные отправки: {successful_sends}, Неуспешные отправки: {failed_sends}"
    logger.info(log_message)
    log_to_file(log_message)

async def handle_client_command(reader, writer):
    global group_folder, contact_folder
    data = await reader.read(1024)
    command = data.decode('utf-8')
    logger.info(f'Получена команда: {command}')

    if command == 'send_spam':
        await mass_send_message(json_file, group_folder, group_timeout)
    elif command == 'send_contact_spam':
        await mass_send_message(contacts_file, contact_folder, contact_timeout)
    elif command == 'reload_clients':
        load_clients(session_folder, account_count)
    elif command.startswith('set_group_folder'):
        _, folder_name = command.split()
        group_folder = folder_name
        logger.info(f'Папка для рассылки в группы изменена на {group_folder}')
    elif command.startswith('set_contact_folder'):
        _, folder_name = command.split()
        contact_folder = folder_name
        logger.info(f'Папка для рассылки в контакты изменена на {contact_folder}')

    writer.close()
    await writer.wait_closed()

async def start_server():
    server = await asyncio.start_server(handle_client_command, HOST, PORT)
    async with server:
        await server.serve_forever()

async def main():
    load_clients(session_folder, account_count)
    for client in clients:
        await client.connect()

    # Start the TCP server to listen for commands
    await start_server()

if __name__ == "__main__":
    asyncio.run(main())