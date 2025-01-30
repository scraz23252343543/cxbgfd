import json
import logging
import asyncio
import os
from datetime import datetime
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError, PeerIdInvalidError

# Конфигурация
api_id = '29758240'
api_hash = '45aa1a0337bf2ab7c931f4fa6a45b344'
phone = '+380958153249'
json_file = 'chats.json'
contacts_file = 'contacts.json'
log_file = 'logi.txt'

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Адрес и порт для TCP-сокета
HOST = '127.0.0.1'
PORT = 65432

# Папки для сохранения сообщений
save_folder = "info"
contact_save_folder = "coninfo"

# Инициализация клиента
client = TelegramClient('session_name', api_id, api_hash)

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

async def send_message_to_chat(chat_id, message):
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

async def send_photo_to_chat(chat_id, photo_path, caption):
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

async def mass_send_message(json_file, folder):
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
                success = await send_photo_to_chat(entity, photo_path, caption)
            elif '.txt' in files:
                text_path = os.path.join(folder, files['.txt'])
                with open(text_path, 'r', encoding='utf-8') as f:
                    message = f.read()
                success = await send_message_to_chat(entity, message)
            elif '.jpg' in files:
                photo_path = os.path.join(folder, files['.jpg'])
                success = await send_photo_to_chat(entity, photo_path, "")

            if success:
                logger.info(f'Успешно отправлено сообщение в {entry["title"]}')
                successful_sends += 1
            else:
                logger.error(f'Не удалось отправить сообщение в {entry["title"]}')
                failed_sends += 1
            await asyncio.sleep(2)  # Задержка в 2 секунды между отправками

    # Логирование статистики
    log_message = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Успешные отправки: {successful_sends}, Неуспешные отправки: {failed_sends}"
    logger.info(log_message)
    log_to_file(log_message)

async def handle_client_command(reader, writer):
    data = await reader.read(1024)
    command = data.decode('utf-8')
    logger.info(f'Получена команда: {command}')

    if command == 'send_spam':
        await mass_send_message(json_file, save_folder)
    elif command == 'send_contact_spam':
        await mass_send_message(contacts_file, contact_save_folder)

    writer.close()
    await writer.wait_closed()

async def start_server():
    server = await asyncio.start_server(handle_client_command, HOST, PORT)
    async with server:
        await server.serve_forever()

async def main():
    await client.start(phone)
    if not await client.is_user_authorized():
        try:
            await client.send_code_request(phone)
            await client.sign_in(phone, input('Введите код: '))
        except SessionPasswordNeededError:
            await client.sign_in(password=input('Пароль: '))

    # Start the TCP server to listen for commands
    await start_server()

if __name__ == "__main__":
    asyncio.run(main())