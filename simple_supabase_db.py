# simple_supabase_db.py
import os
import requests
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class SimpleSupabaseDB:
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase URL and Key must be set in environment variables")
        
        self.headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json"
        }
        logger.info("SimpleSupabaseDB initialized successfully")
        
    def _make_request(self, endpoint, method="GET", data=None, params=None):
        """Универсальный метод для выполнения запросов"""
        url = f"{self.supabase_url}/rest/v1/{endpoint}"
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, params=params)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method == "PUT":
                response = requests.put(url, headers=self.headers, json=data)
            elif method == "PATCH":
                response = requests.patch(url, headers=self.headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers)
            
            if response.status_code >= 400:
                logger.error(f"HTTP {response.status_code}: {response.text}")
                return None
                
            return response.json() if response.content else []
            
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

    def create_user(self, telegram_id: int, username: str, full_name: str, email: str = None, role: str = "user"):
        """Create or update user"""
        try:
            # Сначала проверяем, существует ли пользователь
            existing_user = self._make_request("users", params={"user_id": f"eq.{telegram_id}"})
            
            user_data = {
                "user_id": telegram_id,
                "username": username,
                "full_name": full_name,
                "email": email,
                "role": role
            }
            
            if existing_user and len(existing_user) > 0:
                # Обновляем существующего пользователя
                result = self._make_request(f"users?user_id=eq.{telegram_id}", "PATCH", user_data)
            else:
                # Создаем нового пользователя
                result = self._make_request("users", "POST", user_data)
            
            if result is not None:
                logger.info(f"User created/updated: {telegram_id}")
                return telegram_id
            else:
                logger.error("Failed to create/update user")
                return None
                
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        try:
            result = self._make_request("users", params={"user_id": f"eq.{user_id}"})
            return result[0] if result and len(result) > 0 else None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    def create_project(self, name: str, description: str, created_by: int):
        """Create new project"""
        try:
            project_data = {
                "name": name,
                "description": description,
                "created_by": created_by
            }
            
            result = self._make_request("projects", "POST", project_data)
            
            if result and isinstance(result, list) and len(result) > 0:
                project_id = result[0]['project_id']
                logger.info(f"Project created: {project_id}")
                return project_id
            else:
                logger.error("Failed to create project")
                return None
                
        except Exception as e:
            logger.error(f"Error creating project: {e}")
            return None

    def get_user_projects(self, user_id: int) -> List[Dict]:
        """Get user's projects"""
        try:
            result = self._make_request("projects", params={"created_by": f"eq.{user_id}"})
            return result if result else []
        except Exception as e:
            logger.error(f"Error getting projects: {e}")
            return []

    def create_task(self, title: str, description: str, project_id: int, 
                   author_id: int, priority: str = "medium", assignee_id: int = None, 
                   due_date: str = None):
        """Create new task"""
        try:
            task_data = {
                "title": title,
                "description": description,
                "project_id": project_id,
                "author_id": author_id,
                "priority": priority,
                "assignee_id": assignee_id,
                "due_date": due_date
            }
            
            result = self._make_request("tasks", "POST", task_data)
            
            if result and isinstance(result, list) and len(result) > 0:
                task_id = result[0]['task_id']
                logger.info(f"Task created: {task_id}")
                return task_id
            else:
                logger.error("Failed to create task")
                return None
                
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return None

    def get_user_tasks(self, user_id: int) -> List[Dict]:
        """Get user's tasks with project and status info"""
        try:
            # Получаем задачи пользователя
            tasks = self._make_request("tasks", params={"author_id": f"eq.{user_id}"})
            
            if not tasks:
                return []
            
            enriched_tasks = []
            for task in tasks:
                # Получаем информацию о проекте
                project = self._make_request("projects", params={"project_id": f"eq.{task['project_id']}"})
                project_name = project[0]['name'] if project and len(project) > 0 else "Unknown"
                
                # Получаем информацию о статусе
                status = self._make_request("task_statuses", params={"status_id": f"eq.{task['status_id']}"})
                status_name = status[0]['name'] if status and len(status) > 0 else "Unknown"
                
                enriched_task = {
                    **task,
                    "project_name": project_name,
                    "status_name": status_name
                }
                enriched_tasks.append(enriched_task)
            
            return enriched_tasks
            
        except Exception as e:
            logger.error(f"Error getting tasks: {e}")
            return []

    def update_task_status(self, task_id: int, status_id: int):
        """Update task status"""
        try:
            update_data = {
                "status_id": status_id
            }
            
            result = self._make_request(f"tasks?task_id=eq.{task_id}", "PATCH", update_data)
            
            if result is not None:
                logger.info(f"Task {task_id} status updated to {status_id}")
                return True
            else:
                logger.error(f"Failed to update task {task_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating task: {e}")
            return False

    def add_comment(self, task_id: int, author_id: int, message: str):
        """Add comment to task"""
        try:
            comment_data = {
                "task_id": task_id,
                "author_id": author_id,
                "message": message
            }
            
            result = self._make_request("task_comments", "POST", comment_data)
            
            if result and isinstance(result, list) and len(result) > 0:
                comment_id = result[0]['comment_id']
                logger.info(f"Comment added to task {task_id}")
                return comment_id
            else:
                logger.error("Failed to add comment")
                return None
                
        except Exception as e:
            logger.error(f"Error adding comment: {e}")
            return None

    def get_task_statuses(self):
        """Get all task statuses"""
        try:
            result = self._make_request("task_statuses")
            return result if result else []
        except Exception as e:
            logger.error(f"Error getting statuses: {e}")
            return []

    def test_connection(self):
        """Test database connection"""
        try:
            result = self._make_request("task_statuses")
            return result is not None
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False