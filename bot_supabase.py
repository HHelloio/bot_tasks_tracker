# bot_supabase.py
import logging
import os
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message
from aiogram.filters import Command
import asyncio
from simple_supabase_db import SimpleSupabaseDB
from dotenv import load_dotenv
from aiogram.filters import CommandObject

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN must be set in environment variables")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

# Инициализация SimpleSupabaseDB
try:
    db = SimpleSupabaseDB()
    
    # Тестируем подключение
    if db.test_connection():
        logger.info("✅ Supabase connection test successful")
    else:
        logger.error("❌ Supabase connection test failed")
        raise Exception("Failed to connect to Supabase")
        
except Exception as e:
    logger.error(f"Failed to initialize Supabase: {e}")
    db = None

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    if not db:
        await message.answer("❌ Database is not available. Please try again later.")
        return
        
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    
    if db.create_user(user_id, username, full_name):
        await message.answer(
            "👋 Welcome to Task Tracker Bot!\n\n"
            "📋 Available commands:\n"
            "/mytasks - View your tasks\n"
            "/myprojects - View your projects\n"
            "/createproject <name> [description] - Create new project\n"
            "/createtask - Create new task\n"
            "/status - Check bot status\n\n"
            "Type any command to get started!"
        )
    else:
        await message.answer("❌ Error registering user. Please try again.")

@router.message(Command("mytasks"))
async def cmd_my_tasks(message: Message):
    """Показать задачи пользователя"""
    if not db:
        await message.answer("❌ Database is not available. Please try again later.")
        return
        
    user_id = message.from_user.id
    tasks = db.get_user_tasks(user_id)
    
    if not tasks:
        await message.answer("📝 You don't have any tasks yet.\n\nUse /createtask to create your first task!")
        return
    
    response = "📋 Your Tasks:\n\n"
    for task in tasks:
        response += f"• {task['title']} ({task['status_name']})\n"
        response += f"  Project: {task['project_name']}\n"
        response += f"  Priority: {task.get('priority', 'medium')}\n"
        if task.get('due_date'):
            response += f"  Due: {task['due_date'][:10]}\n"
        if task.get('description'):
            response += f"  Description: {task['description'][:50]}...\n"
        response += "\n"
    
    await message.answer(response)

@router.message(Command("myprojects"))
async def cmd_my_projects(message: Message):
    """Показать проекты пользователя"""
    if not db:
        await message.answer("❌ Database is not available. Please try again later.")
        return
        
    user_id = message.from_user.id
    projects = db.get_user_projects(user_id)
    
    if not projects:
        await message.answer("📂 You don't have any projects yet.\n\nUse /createproject to create your first project!")
        return
    
    response = "📁 Your Projects:\n\n"
    for project in projects:
        response += f"• {project['name']} (ID: {project['project_id']})\n"
        if project['description']:
            response += f"  {project['description']}\n"
        response += f"  Created: {project['created_at'][:10]}\n\n"
    
    await message.answer(response)

@router.message(Command("createproject"))
async def cmd_create_project(message: Message):
    """Создать новый проект"""
    if not db:
        await message.answer("❌ Database is not available. Please try again later.")
        return
        
    args = message.text.split(' ', 2)
    if len(args) < 2:
        await message.answer(
            "📝 Usage: /createproject <project_name> [description]\n\n"
            "Examples:\n"
            "/createproject MyNewProject\n"
            "/createproject Website Development Creating a company website\n"
            "/createproject Mobile App Development new mobile application project"
        )
        return
    
    project_name = args[1]
    description = args[2] if len(args) > 2 else ""
    
    project_id = db.create_project(project_name, description, message.from_user.id)
    
    if project_id:
        await message.answer(f"✅ Project '{project_name}' created successfully! (ID: {project_id})")
    else:
        await message.answer("❌ Failed to create project. Please try again.")

@router.message(Command("createtask"))
async def cmd_create_task_with_args(message: Message, command: CommandObject):
    """Обработчик команды createtask с аргументами"""
    if not db:
        await message.answer("❌ Database is not available. Please try again later.")
        return
        
    # Если нет аргументов, показываем инструкцию
    if not command.args:
        await show_create_task_instruction(message)
        return
        
    await handle_create_task_with_args(message, command.args)


@router.message(Command("createtask"))
async def show_create_task_instruction(message: Message):
    """Показать инструкцию по созданию задачи"""
    user_id = message.from_user.id
    projects = db.get_user_projects(user_id)
    
    if not projects:
        await message.answer(
            "❌ You don't have any projects yet.\n\n"
            "Please create a project first using:\n"
            "/createproject <project_name>"
        )
        return
    
    projects_list = "\n".join([f"• {p['name']} (ID: {p['project_id']})" for p in projects])
    
    await message.answer(
        "📝 To create a task, use:\n"
        "/createtask <project_id> <task_title> [description]\n\n"
        "📁 Your available projects:\n" +
        projects_list +
        "\n\nExample:\n"
        "/createtask 1 Fix homepage layout\n"
        "/createtask 2 Add user authentication Implement login and registration"
    )

@router.message(Command("status"))
async def cmd_status(message: Message):
    """Показать статус бота"""
    db_status = "✅ Connected" if db and db.test_connection() else "❌ Disconnected"
    
    await message.answer(
        f"🤖 Bot Status:\n"
        f"• Database: {db_status}\n"
        f"• User ID: {message.from_user.id}\n"
        f"• Commands available:\n"
        f"  /start - Welcome message\n"
        f"  /mytasks - View your tasks\n"
        f"  /myprojects - View your projects\n"
        f"  /createproject - Create new project\n"
        f"  /createtask - Create new task\n"
        f"  /status - This message"
    )

@router.message()
async def handle_other_messages(message: Message):
    """Обработка всех остальных сообщений"""
    await message.answer(
        "🤖 I don't understand that command.\n\n"
        "Available commands:\n"
        "/start - Welcome message\n"
        "/mytasks - View your tasks\n"
        "/myprojects - View your projects\n"
        "/createproject - Create new project\n"
        "/createtask - Create new task\n"
        "/status - Bot status"
    )
        
async def handle_create_task_with_args(message: Message, args: str):
    """Обработка команды создания задачи с аргументами"""
    if not db:
        await message.answer("❌ Database is not available. Please try again later.")
        return
        
    args_list = args.split(' ', 2)
    if len(args_list) < 2:
        await show_create_task_instruction(message)
        return
    
    try:
        project_id = int(args_list[0])
        title = args_list[1]
        description = args_list[2] if len(args_list) > 2 else ""
        
        # Проверяем существование проекта
        projects = db.get_user_projects(message.from_user.id)
        project_exists = any(p['project_id'] == project_id for p in projects)
        
        if not project_exists:
            await message.answer("❌ Project not found or you don't have access to it.")
            return
        
        task_id = db.create_task(
            title=title,
            description=description,
            project_id=project_id,
            author_id=message.from_user.id,
            priority="medium"
        )
        
        if task_id:
            await message.answer(f"✅ Task '{title}' created successfully! (ID: {task_id})")
        else:
            await message.answer("❌ Failed to create task. Please try again.")
            
    except ValueError:
        await message.answer("❌ Invalid project ID. Please use a numeric project ID.")
    except Exception as e:
        await message.answer(f"❌ Error creating task: {e}")

async def main():
    dp.include_router(router)
    logger.info("🤖 Task Tracker Bot started successfully!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())