import logging
import os
import socket
import json
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto

# Конфигурация
api_id = '29758240'
api_hash = '45aa1a0337bf2ab7c931f4fa6a45b344'
bot_token = '7833414798:AAFpEUyslDz0TrzWupNC2nrAk9gY2nFWzio'

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Адрес и порт для TCP-сокета
HOST = '127.0.0.1'
PORT = 65432

# Файлы для сохранения чатов и контактов
chats_file = 'chats.json'
contacts_file = 'contacts.json'
log_file = 'logi.txt'

# Инициализация бота
bot = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

# Глобальные переменные для хранения состояния и сообщения
waiting_for_message = False
waiting_for_contact_message = False
saved_message_list = []
contact_saved_message_list = []
group_timeout = 2
contact_timeout = 2

# Глобальные переменные для папок
group_folder = "info"
contact_folder = "coninfo"

# Глобальная переменная для количества аккаунтов
account_count = 1

def generate_unique_filename(extension, folder):
    counter = 1
    while True:
        file_name = f"photo_{counter}.{extension}"
        if not os.path.exists(os.path.join(folder, file_name)):
            return file_name
        counter += 1

async def save_message(message, folder, saved_list):
    if message.text:
        file_name = generate_unique_filename('txt', folder)
        saved_list.append(file_name)
        with open(os.path.join(folder, file_name), 'w', encoding='utf-8') as f:
            f.write(message.text)
    elif isinstance(message.media, MessageMediaPhoto):
        file_name = generate_unique_filename('jpg', folder)
        await message.download_media(file=os.path.join(folder, file_name))
        saved_list.append(file_name)
        if message.message:
            caption_name = file_name.replace('.jpg', '_caption.txt')
            with open(os.path.join(folder, caption_name), 'w', encoding='utf-8') as f:
                f.write(message.message)
            saved_list.append(caption_name)

def send_command_to_client(command):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((HOST, PORT))
            client_socket.sendall(command.encode('utf-8'))
            logger.info(f'Отправлена команда клиенту: {command}')
    except Exception as e:
        logger.error(f'Не удалось отправить команду клиенту: {e}')

def save_chat_to_file(chat_id, chat_title):
    chat = {"id": chat_id, "title": chat_title}
    if os.path.exists(chats_file):
        with open(chats_file, 'r', encoding='utf-8') as f:
            chats = json.load(f)
    else:
        chats = []

    chats.append(chat)

    with open(chats_file, 'w', encoding='utf-8') as f:
        json.dump(chats, f, ensure_ascii=False, indent=4)

def save_contact_to_file(contact_id, contact_title):
    contact = {"id": contact_id, "title": contact_title}
    if os.path.exists(contacts_file):
        with open(contacts_file, 'r', encoding='utf-8') as f:
            contacts = json.load(f)
    else:
        contacts = []

    contacts.append(contact)

    with open(contacts_file, 'w', encoding='utf-8') as f:
        json.dump(contacts, f, ensure_ascii=False, indent=4)

@bot.on(events.NewMessage(pattern='/groupspam'))
async def groupspam_handler(event):
    global waiting_for_message, waiting_for_contact_message
    waiting_for_message = True
    waiting_for_contact_message = False
    logger.info('Получена команда /groupspam')
    await event.reply('Пожалуйста, отправьте текст, фото или фото с подписью, которое вы хотите разослать.')

@bot.on(events.NewMessage(pattern='/contactsspam'))
async def contactsspam_handler(event):
    global waiting_for_message, waiting_for_contact_message
    waiting_for_message = False
    waiting_for_contact_message = True
    logger.info('Получена команда /contactsspam')
    await event.reply('Пожалуйста, отправьте текст, фото или фото с подписью, которое вы хотите разослать.')

@bot.on(events.NewMessage)
async def message_handler(event):
    global waiting_for_message, waiting_for_contact_message, group_folder, contact_folder
    if waiting_for_message and not event.message.message.startswith('/'):
        waiting_for_message = False
        await save_message(event.message, group_folder, saved_message_list)
        await event.reply(f'Сообщение сохранено в папку {group_folder}. Введите команду /sendspams для рассылки.')
        logger.info('Сообщение сохранено.')
    elif waiting_for_contact_message and not event.message.message.startswith('/'):
        waiting_for_contact_message = False
        await save_message(event.message, contact_folder, contact_saved_message_list)
        await event.reply(f'Сообщение сохранено в папку {contact_folder}. Введите команду /conspams для рассылки.')
        logger.info('Сообщение сохранено.')

@bot.on(events.NewMessage(pattern='/sendspams'))
async def sendspams_handler(event):
    send_command_to_client('send_spam')

@bot.on(events.NewMessage(pattern='/conspams'))
async def conspams_handler(event):
    send_command_to_client('send_contact_spam')

@bot.on(events.NewMessage(pattern='/delinfo'))
async def delinfo_handler(event):
    global group_folder
    # Очистка выбранной папки для групп
    for filename in os.listdir(group_folder):
        file_path = os.path.join(group_folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            logger.error(f'Не удалось удалить {file_path}. Причина: {e}')
    await event.reply(f'Папка {group_folder} очищена.')

@bot.on(events.NewMessage(pattern='/delcontact'))
async def delcontact_handler(event):
    global contact_folder
    # Очистка выбранной папки для контактов
    for filename in os.listdir(contact_folder):
        file_path = os.path.join(contact_folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            logger.error(f'Не удалось удалить {file_path}. Причина: {e}')
    await event.reply(f'Папка {contact_folder} очищена.')

@bot.on(events.NewMessage(pattern='/logi'))
async def logi_handler(event):
    if os.path.exists(log_file):
        await bot.send_file(event.chat_id, log_file)
    else:
        await event.reply('Файл logi.txt не найден.')

@bot.on(events.NewMessage(pattern='/timeoutgroup'))
async def timeoutgroup_handler(event):
    global group_timeout
    try:
        # Получение аргумента команды
        args = event.message.message.split()
        if len(args) != 2:
            await event.reply('Неправильный формат команды. Используйте: /timeoutgroup (время в секундах)')
            return

        group_timeout = int(args[1])
        await event.reply(f'Задержка для групп установлена на {group_timeout} секунд.')
    except Exception as e:
        logger.error(f'Ошибка при обработке команды /timeoutgroup: {e}')
        await event.reply('Произошла ошибка при установке задержки.')

@bot.on(events.NewMessage(pattern='/timeoutcontact'))
async def timeoutcontact_handler(event):
    global contact_timeout
    try:
        # Получение аргумента команды
        args = event.message.message.split()
        if len(args) != 2:
            await event.reply('Неправильный формат команды. Используйте: /timeoutcontact (время в секундах)')
            return

        contact_timeout = int(args[1])
        await event.reply(f'Задержка для контактов установлена на {contact_timeout} секунд.')
    except Exception as e:
        logger.error(f'Ошибка при обработке команды /timeoutcontact: {e}')
        await event.reply('Произошла ошибка при установке задержки.')

@bot.on(events.NewMessage(pattern='/newspam'))
async def newspam_handler(event):
    try:
        # Получение аргумента команды
        args = event.message.message.split()
        if len(args) != 2:
            await event.reply('Неправильный формат команды. Используйте: /newspam (название папки)')
            return

        folder_name = args[1]
        os.makedirs(folder_name, exist_ok=True)
        await event.reply(f'Папка для спама в группы {folder_name} создана.')
    except Exception as e:
        logger.error(f'Ошибка при обработке команды /newspam: {e}')
        await event.reply('Произошла ошибка при создании папки.')

@bot.on(events.NewMessage(pattern='/newcontactspam'))
async def newcontactspam_handler(event):
    try:
        # Получение аргумента команды
        args = event.message.message.split()
        if len(args) != 2:
            await event.reply('Неправильный формат команды. Используйте: /newcontactspam (название папки)')
            return

        folder_name = args[1]
        os.makedirs(folder_name, exist_ok=True)
        await event.reply(f'Папка для спама в контакты {folder_name} создана.')
    except Exception as e:
        logger.error(f'Ошибка при обработке команды /newcontactspam: {e}')
        await event.reply('Произошла ошибка при создании папки.')

@bot.on(events.NewMessage(pattern='/vspam'))
async def vspam_handler(event):
    global group_folder
    try:
        # Получение аргумента команды
        args = event.message.message.split()
        if len(args) != 2:
            await event.reply('Неправильный формат команды. Используйте: /vspam (название папки)')
            return

        folder_name = args[1]
        if not os.path.exists(folder_name):
            await event.reply(f'Папка {folder_name} не существует.')
            return

        group_folder = folder_name
        send_command_to_client(f'set_group_folder {folder_name}')
        await event.reply(f'Папка для спама в группы изменена на {folder_name}. Теперь отправьте сообщение для сохранения.')
    except Exception as e:
        logger.error(f'Ошибка при обработке команды /vspam: {e}')
        await event.reply('Произошла ошибка при изменении папки.')

@bot.on(events.NewMessage(pattern='/vcontact'))
async def vcontact_handler(event):
    global contact_folder
    try:
        # Получение аргумента команды
        args = event.message.message.split()
        if len(args) != 2:
            await event.reply('Неправильный формат команды. Используйте: /vcontact (название папки)')
            return

        folder_name = args[1]
        if not os.path.exists(folder_name):
            await event.reply(f'Папка {folder_name} не существует.')
            return

        contact_folder = folder_name
        send_command_to_client(f'set_contact_folder {folder_name}')
        await event.reply(f'Папка для спама в контакты изменена на {folder_name}. Теперь отправьте сообщение для сохранения.')
    except Exception as e:
        logger.error(f'Ошибка при обработке команды /vcontact: {e}')
        await event.reply('Произошла ошибка при изменении папки.')

@bot.on(events.NewMessage(pattern='/schats'))
async def schats_handler(event):
    try:
        # Получение аргументов команды
        args = event.message.message.split()
        if len(args) != 3:
            await event.reply('Неправильный формат команды. Используйте: /schats (group_id) (название канала)')
            return

        group_id = int(args[1])
        group_title = args[2]

        # Сохранение чата в файл
        save_chat_to_file(group_id, group_title)
        await event.reply(f'Канал {group_title} сохранен в файл {chats_file}.')
    except Exception as e:
        logger.error(f'Ошибка при обработке команды /schats: {e}')
        await event.reply('Произошла ошибка при сохранении канала.')

@bot.on(events.NewMessage(pattern='/conadd'))
async def conadd_handler(event):
    try:
        # Получение аргументов команды
        args = event.message.message.split()
        if len(args) != 3:
            await event.reply('Неправильный формат команды. Используйте: /conadd (id пользователя) (имя)')
            return

        contact_id = int(args[1])
        contact_title = args[2]

        # Сохранение контакта в файл
        save_contact_to_file(contact_id, contact_title)
        await event.reply(f'Контакт {contact_title} сохранен в файл {contacts_file}.')
    except Exception as e:
        logger.error(f'Ошибка при обработке команды /conadd: {e}')
        await event.reply('Произошла ошибка при сохранении контакта.')

@bot.on(events.NewMessage(pattern='/accountstart'))
async def accountstart_handler(event):
    global account_count
    try:
        # Получение аргумента команды
        args = event.message.message.split()
        if len(args) != 2:
            await event.reply('Неправильный формат команды. Используйте: /accountstart (количество аккаунтов или "all")')
            return

        if args[1].lower() == "all":
            account_count = "all"
        else:
            account_count = int(args[1])
        await event.reply(f'Количество аккаунтов для рассылки установлено на {account_count}.')
        
        # Отправка команды на перезагрузку клиентов в клиентском скрипте
        send_command_to_client('reload_clients')
    except Exception as e:
        logger.error(f'Ошибка при обработке команды /accountstart: {e}')
        await event.reply('Произошла ошибка при установке количества аккаунтов.')

with bot:
    bot.run_until_disconnected()