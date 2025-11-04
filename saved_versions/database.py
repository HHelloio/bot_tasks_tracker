# database.py
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "task_tracker.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Инициализация базы данных с созданием таблиц"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Создание таблицы пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(50) UNIQUE,
                    email VARCHAR(100) UNIQUE,
                    full_name VARCHAR(100),
                    role VARCHAR(50),
                    registered_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Создание таблицы статусов задач
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_statuses (
                    status_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(50) UNIQUE,
                    order_index INTEGER
                )
            ''')
            
            # Создание таблицы проектов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100),
                    description TEXT,
                    created_by INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(user_id)
                )
            ''')
            
            # Создание таблицы задач
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title VARCHAR(200),
                    description TEXT,
                    project_id INTEGER,
                    status_id INTEGER,
                    author_id INTEGER,
                    assignee_id INTEGER,
                    priority VARCHAR(20),
                    due_date DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(project_id),
                    FOREIGN KEY (status_id) REFERENCES task_statuses(status_id),
                    FOREIGN KEY (author_id) REFERENCES users(user_id),
                    FOREIGN KEY (assignee_id) REFERENCES users(user_id)
                )
            ''')
            
            # Создание таблицы комментариев
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_comments (
                    comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER,
                    author_id INTEGER,
                    message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(task_id),
                    FOREIGN KEY (author_id) REFERENCES users(user_id)
                )
            ''')
            
            # Создание таблицы участников проектов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS project_members (
                    project_id INTEGER,
                    user_id INTEGER,
                    role_in_project VARCHAR(50),
                    PRIMARY KEY (project_id, user_id),
                    FOREIGN KEY (project_id) REFERENCES projects(project_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Добавление стандартных статусов задач
            default_statuses = [
                ('To Do', 1),
                ('In Progress', 2),
                ('In Review', 3),
                ('Done', 4)
            ]
            
            cursor.executemany('''
                INSERT OR IGNORE INTO task_statuses (name, order_index) 
                VALUES (?, ?)
            ''', default_statuses)
            
            conn.commit()
            logger.info("Database initialized successfully")

    # Методы для работы с пользователями
    def create_user(self, telegram_id: int, username: str, full_name: str, email: str = None, role: str = "user"):
        """Создание нового пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, username, email, full_name, role)
                VALUES (?, ?, ?, ?, ?)
            ''', (telegram_id, username, email, full_name, role))
            conn.commit()
            return cursor.lastrowid

    def get_user(self, user_id: int):
        """Получение пользователя по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            return cursor.fetchone()

    # Методы для работы с проектами
    def create_project(self, name: str, description: str, created_by: int):
        """Создание нового проекта"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO projects (name, description, created_by)
                VALUES (?, ?, ?)
            ''', (name, description, created_by))
            conn.commit()
            return cursor.lastrowid

    def get_user_projects(self, user_id: int):
        """Получение проектов пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.* FROM projects p
                LEFT JOIN project_members pm ON p.project_id = pm.project_id
                WHERE p.created_by = ? OR pm.user_id = ?
            ''', (user_id, user_id))
            return cursor.fetchall()

    # Методы для работы с задачами
    def create_task(self, title: str, description: str, project_id: int, 
                   author_id: int, priority: str = "medium", assignee_id: int = None, 
                   due_date: str = None):
        """Создание новой задачи"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Статус по умолчанию - "To Do" (id=1)
            cursor.execute('''
                INSERT INTO tasks (title, description, project_id, status_id, 
                                 author_id, assignee_id, priority, due_date)
                VALUES (?, ?, ?, 1, ?, ?, ?, ?)
            ''', (title, description, project_id, author_id, assignee_id, priority, due_date))
            conn.commit()
            return cursor.lastrowid

    def get_user_tasks(self, user_id: int):
        """Получение задач пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.*, ts.name as status_name, p.name as project_name
                FROM tasks t
                JOIN task_statuses ts ON t.status_id = ts.status_id
                JOIN projects p ON t.project_id = p.project_id
                WHERE t.author_id = ? OR t.assignee_id = ?
                ORDER BY t.created_at DESC
            ''', (user_id, user_id))
            return cursor.fetchall()

    def update_task_status(self, task_id: int, status_id: int):
        """Обновление статуса задачи"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tasks 
                SET status_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            ''', (status_id, task_id))
            conn.commit()

    # Методы для работы с комментариями
    def add_comment(self, task_id: int, author_id: int, message: str):
        """Добавление комментария к задаче"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO task_comments (task_id, author_id, message)
                VALUES (?, ?, ?)
            ''', (task_id, author_id, message))
            conn.commit()
            return cursor.lastrowid

    def get_task_comments(self, task_id: int):
        """Получение комментариев задачи"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT tc.*, u.full_name, u.username
                FROM task_comments tc
                JOIN users u ON tc.author_id = u.user_id
                WHERE tc.task_id = ?
                ORDER BY tc.created_at ASC
            ''', (task_id,))
            return cursor.fetchall()

    # Методы для работы с участниками проектов
    def add_project_member(self, project_id: int, user_id: int, role: str = "member"):
        """Добавление участника в проект"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO project_members (project_id, user_id, role_in_project)
                VALUES (?, ?, ?)
            ''', (project_id, user_id, role))
            conn.commit()

    def get_project_members(self, project_id: int):
        """Получение участников проекта"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.*, pm.role_in_project
                FROM project_members pm
                JOIN users u ON pm.user_id = u.user_id
                WHERE pm.project_id = ?
            ''', (project_id,))
            return cursor.fetchall()

    # Получение статусов задач
    def get_task_statuses(self):
        """Получение всех статусов задач"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM task_statuses ORDER BY order_index')
            return cursor.fetchall()