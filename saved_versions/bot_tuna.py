# bot_tuna.py (обновленная версия)
import logging
from aiogram import Bot, Dispatcher, Router
from aiogram.types import (
    Message, WebAppInfo, MenuButtonWebApp, 
    ReplyKeyboardMarkup, KeyboardButton, WebAppData
)
from aiogram.filters import Command
import json
import asyncio
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import subprocess
import re
import time
import select
from saved_versions.database import Database

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8282664849:AAFauecKA2GD7Gqa8stzoc-CL6uH9RMeSC8"
TUNA_URL = ""  

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
db = Database()

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()
    
    def do_GET(self):
        if self.path == '/':
            self.path = '/mini-app.html'
        return super().do_GET()

def run_http_server():
    """Запуск HTTP сервера в отдельном потоке"""
    port = 8080
    server_address = ('', port)
    httpd = HTTPServer(server_address, CORSRequestHandler)
    print(f'HTTP Server running on http://localhost:{port}')
    httpd.serve_forever()

def start_tuna_tunnel():
    global TUNA_URL
    
    try:
        logger.info("Starting Tuna with command: ['tuna', 'http', '8080']")
        
        process = subprocess.Popen(
            ['tuna', 'http', '8080'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        logger.info("Tuna process started, waiting for URL...")
        
        # Ждем и читаем вывод постепенно
        start_time = time.time()
        timeout = 30  # 30 секунд максимум
        
        while time.time() - start_time < timeout:
            # Проверяем stdout
            if select.select([process.stdout], [], [], 0.5)[0]:
                stdout_line = process.stdout.readline()
                if stdout_line:
                    line = stdout_line.strip()
                    logger.info(f"Tuna stdout: {line}")
                    
                    # Ищем URL в разных форматах
                    url_patterns = [
                        r'https://[a-zA-Z0-9\-]+\.ru\.tuna\.am',
                        r'https://[a-zA-Z0-9\-]+\.tuna\.am',
                        r'http://[a-zA-Z0-9\-]+\.ru\.tuna\.am',
                        r'http://[a-zA-Z0-9\-]+\.tuna\.am'
                    ]
                    
                    for pattern in url_patterns:
                        url_match = re.search(pattern, line)
                        if url_match:
                            TUNA_URL = url_match.group(0)
                            # Убедимся, что используем https
                            if TUNA_URL.startswith('http://'):
                                TUNA_URL = TUNA_URL.replace('http://', 'https://')
                            logger.info(f"🎣 Tuna URL detected: {TUNA_URL}")
                            return process
            
            # Проверяем stderr
            if select.select([process.stderr], [], [], 0)[0]:
                stderr_line = process.stderr.readline()
                if stderr_line:
                    line = stderr_line.strip()
                    logger.info(f"Tuna stderr: {line}")
                    
                    # Также ищем URL в stderr
                    url_patterns = [
                        r'https://[a-zA-Z0-9\-]+\.ru\.tuna\.am',
                        r'https://[a-zA-Z0-9\-]+\.tuna\.am',
                        r'http://[a-zA-Z0-9\-]+\.ru\.tuna\.am',
                        r'http://[a-zA-Z0-9\-]+\.tuna\.am'
                    ]
                    
                    for pattern in url_patterns:
                        url_match = re.search(pattern, line)
                        if url_match:
                            TUNA_URL = url_match.group(0)
                            if TUNA_URL.startswith('http://'):
                                TUNA_URL = TUNA_URL.replace('http://', 'https://')
                            logger.info(f"🎣 Tuna URL detected in stderr: {TUNA_URL}")
                            return process
            
            # Проверяем, не завершился ли процесс
            if process.poll() is not None:
                logger.error("Tuna process exited prematurely")
                break
                
            time.sleep(0.1)
        
        # Если URL не найден в выводе, пробуем получить через tuna list
        if not TUNA_URL:
            logger.info("Trying to get URL via 'tuna list'...")
            try:
                result = subprocess.run(
                    ['tuna', 'list', '--json'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0 and result.stdout:
                    import json
                    tunnels = json.loads(result.stdout)
                    if tunnels and isinstance(tunnels, list) and len(tunnels) > 0:
                        TUNA_URL = tunnels[0].get('public_url', '')
                        if TUNA_URL:
                            if TUNA_URL.startswith('http://'):
                                TUNA_URL = TUNA_URL.replace('http://', 'https://')
                            logger.info(f"🎣 Tuna URL from list: {TUNA_URL}")
                            return process
            except Exception as e:
                logger.warning(f"Could not get URL from tuna list: {e}")
        
        logger.error(f"Tuna URL not found after {timeout} seconds")
        return process
        
    except Exception as e:
        logger.error(f"Error starting Tuna: {e}")
        return None

async def setup_bot_menu():
    """Настройка меню бота с Web App"""
    try:
        if TUNA_URL:
            web_app_url = f"{TUNA_URL}/mini-app.html"
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="🎮 Open Task Tracker", 
                    web_app=WebAppInfo(url=web_app_url)
                )
            )
            logger.info(f"Bot menu configured with URL: {web_app_url}")
        else:
            logger.warning("Tuna URL not available for menu setup")
    except Exception as e:
        logger.error(f"Error setting bot menu: {e}")

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    # Регистрируем пользователя в базе данных
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    
    db.create_user(user_id, username, full_name)
    logger.info(f"User registered: {user_id} - {full_name}")
    
    if not TUNA_URL:
        await message.answer("❌ Tuna tunnel is not ready yet. Please wait...")
        return
        
    web_app_url = f"{TUNA_URL}/mini-app.html"
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(
                text="🚀 Open Task Tracker", 
                web_app=WebAppInfo(url=web_app_url)
            )]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "👋 Welcome to Task Tracker Bot!\n\n"
        "Manage your projects and tasks efficiently.\n"
        "Click the button below to open the Task Tracker:",
        reply_markup=keyboard
    )

@router.message(Command("mytasks"))
async def cmd_my_tasks(message: Message):
    """Показать задачи пользователя"""
    user_id = message.from_user.id
    tasks = db.get_user_tasks(user_id)
    
    if not tasks:
        await message.answer("📝 You don't have any tasks yet.")
        return
    
    response = "📋 Your Tasks:\n\n"
    for task in tasks:
        task_id, title, description, project_id, status_id, author_id, assignee_id, priority, due_date, created_at, updated_at, status_name, project_name = task
        response += f"• {title} ({status_name})\n"
        response += f"  Project: {project_name}\n"
        response += f"  Priority: {priority}\n"
        if due_date:
            response += f"  Due: {due_date[:10]}\n"
        response += "\n"
    
    await message.answer(response)

@router.message(Command("myprojects"))
async def cmd_my_projects(message: Message):
    """Показать проекты пользователя"""
    user_id = message.from_user.id
    projects = db.get_user_projects(user_id)
    
    if not projects:
        await message.answer("📂 You don't have any projects yet.")
        return
    
    response = "📁 Your Projects:\n\n"
    for project in projects:
        project_id, name, description, created_by, created_at = project
        response += f"• {name}\n"
        response += f"  {description}\n\n"
    
    await message.answer(response)

@router.message(Command("url"))
async def cmd_url(message: Message):
    """Показать URL Mini App"""
    if TUNA_URL:
        await message.answer(f"🌐 Task Tracker URL: {TUNA_URL}/mini-app.html")
    else:
        await message.answer("❌ Tuna URL not available")

@router.message(Command("status"))
async def cmd_status(message: Message):
    """Показать статус Tuna tunnel"""
    status = "✅ Active" if TUNA_URL else "❌ Inactive"
    await message.answer(
        f"🤖 Bot Status:\n"
        f"• Tuna Tunnel: {status}\n"
        f"• URL: {TUNA_URL or 'Not available'}\n"
        f"• Database: ✅ Connected"
    )

@router.message()
async def handle_web_app_data(message: Message):
    """Обработка данных из Web App"""
    if message.web_app_data:
        try:
            data = json.loads(message.web_app_data.data)
            logger.info(f"Received data from Mini App: {data}")
            
            action = data.get('action')
            user_id = message.from_user.id
            
            if action == "create_task":
                # Создание новой задачи
                task_id = db.create_task(
                    title=data.get('title'),
                    description=data.get('description'),
                    project_id=data.get('project_id'),
                    author_id=user_id,
                    priority=data.get('priority', 'medium'),
                    assignee_id=data.get('assignee_id'),
                    due_date=data.get('due_date')
                )
                await message.answer(f"✅ Task created successfully! (ID: {task_id})")
                
            elif action == "create_project":
                # Создание нового проекта
                project_id = db.create_project(
                    name=data.get('name'),
                    description=data.get('description'),
                    created_by=user_id
                )
                await message.answer(f"✅ Project created successfully! (ID: {project_id})")
                
            elif action == "update_task_status":
                # Обновление статуса задачи
                db.update_task_status(
                    task_id=data.get('task_id'),
                    status_id=data.get('status_id')
                )
                await message.answer("✅ Task status updated!")
                
            elif action == "add_comment":
                # Добавление комментария
                comment_id = db.add_comment(
                    task_id=data.get('task_id'),
                    author_id=user_id,
                    message=data.get('message')
                )
                await message.answer("✅ Comment added!")
                
            else:
                await message.answer(
                    f"📨 <b>Data received from Task Tracker!</b>\n\n"
                    f"• <b>Action:</b> {data.get('action', 'N/A')}\n"
                    f"• <b>Message:</b> {data.get('message', 'N/A')}\n"
                    f"• <b>Time:</b> {data.get('timestamp', 'N/A')[:19]}\n"
                    f"• <b>Tunnel:</b> Tuna",
                    parse_mode="HTML"
                )
            
        except json.JSONDecodeError as e:
            await message.answer(f"❌ Error parsing data: {e}")
        except Exception as e:
            await message.answer(f"❌ Error: {e}")
    elif message.text:
        await message.answer("Use /start to open Task Tracker or /mytasks to see your tasks")

async def main():
    # Запуск HTTP сервера в отдельном потоке
    server_thread = threading.Thread(target=run_http_server, daemon=True)
    server_thread.start()
    
    logger.info("🚀 Starting HTTP server...")
    await asyncio.sleep(2)
    
    # Запуск Tuna tunnel
    logger.info("🎣 Starting Tuna tunnel...")
    tuna_process = start_tuna_tunnel()
    
    # Ждем пока Tuna URL станет доступен
    max_attempts = 60
    for attempt in range(max_attempts):
        if TUNA_URL:
            break
        if attempt % 10 == 0:
            logger.info(f"Waiting for Tuna URL... ({attempt + 1}/{max_attempts})")
        await asyncio.sleep(1)
    
    if not TUNA_URL:
        logger.error("❌ Failed to get Tuna URL after maximum attempts")
        logger.info("Bot starting without Tuna URL - some features will be unavailable")
    
    # Настройка бота
    dp.include_router(router)
    if TUNA_URL:
        await setup_bot_menu()
    
    logger.info("🤖 Bot started successfully!")
    if TUNA_URL:
        logger.info(f"🌐 Tuna URL: {TUNA_URL}")
    else:
        logger.info("🌐 Tuna URL: Not available")
    logger.info("✅ Ready to receive messages!")
    
    try:
        await dp.start_polling(bot)
    finally:
        if tuna_process:
            tuna_process.terminate()
            logger.info("Tuna process terminated")

if __name__ == "__main__":
    asyncio.run(main())