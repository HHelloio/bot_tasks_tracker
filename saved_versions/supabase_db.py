# supabase_db.py
import os
from supabase import create_client, Client
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class SupabaseDB:
    def __init__(self):
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase URL and Key must be set in environment variables")
        
        try:
            self.supabase: Client = create_client(supabase_url, supabase_key)
            logger.info("Supabase database connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            raise

    # User methods
    def create_user(self, telegram_id: int, username: str, full_name: str, email: str = None, role: str = "user"):
        """Create or update user"""
        try:
            data = {
                "user_id": telegram_id,
                "username": username,
                "full_name": full_name,
                "email": email,
                "role": role
            }
            
            # Проверяем, существует ли пользователь
            existing_user = self.supabase.table("users").select("*").eq("user_id", telegram_id).execute()
            
            if existing_user.data:
                # Обновляем существующего пользователя
                result = self.supabase.table("users").update(data).eq("user_id", telegram_id).execute()
            else:
                # Создаем нового пользователя
                result = self.supabase.table("users").insert(data).execute()
            
            if result.data:
                logger.info(f"User created/updated: {telegram_id}")
                return telegram_id
            else:
                logger.error(f"Error creating user: {result.error}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        try:
            result = self.supabase.table("users").select("*").eq("user_id", user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    # Project methods
    def create_project(self, name: str, description: str, created_by: int):
        """Create new project"""
        try:
            data = {
                "name": name,
                "description": description,
                "created_by": created_by
            }
            result = self.supabase.table("projects").insert(data).execute()
            
            if result.data:
                project_id = result.data[0]['project_id']
                logger.info(f"Project created: {project_id}")
                return project_id
            else:
                logger.error(f"Error creating project: {result.error}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating project: {e}")
            return None

    def get_user_projects(self, user_id: int) -> List[Dict]:
        """Get user's projects"""
        try:
            result = self.supabase.table("projects").select("*").eq("created_by", user_id).execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting projects: {e}")
            return []

    # Task methods
    def create_task(self, title: str, description: str, project_id: int, 
                   author_id: int, priority: str = "medium", assignee_id: int = None, 
                   due_date: str = None):
        """Create new task"""
        try:
            data = {
                "title": title,
                "description": description,
                "project_id": project_id,
                "author_id": author_id,
                "priority": priority,
                "assignee_id": assignee_id,
                "due_date": due_date
            }
            result = self.supabase.table("tasks").insert(data).execute()
            
            if result.data:
                task_id = result.data[0]['task_id']
                logger.info(f"Task created: {task_id}")
                return task_id
            else:
                logger.error(f"Error creating task: {result.error}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return None

    def get_user_tasks(self, user_id: int) -> List[Dict]:
        """Get user's tasks"""
        try:
            # Сначала получаем задачи пользователя
            tasks_result = self.supabase.table("tasks").select("*").eq("author_id", user_id).execute()
            
            if not tasks_result.data:
                return []
            
            tasks = []
            for task in tasks_result.data:
                # Получаем информацию о проекте
                project_result = self.supabase.table("projects").select("name").eq("project_id", task['project_id']).execute()
                project_name = project_result.data[0]['name'] if project_result.data else "Unknown"
                
                # Получаем информацию о статусе
                status_result = self.supabase.table("task_statuses").select("name").eq("status_id", task['status_id']).execute()
                status_name = status_result.data[0]['name'] if status_result.data else "Unknown"
                
                task_data = {
                    **task,
                    "project_name": project_name,
                    "status_name": status_name
                }
                tasks.append(task_data)
            
            return tasks
            
        except Exception as e:
            logger.error(f"Error getting tasks: {e}")
            return []

    def update_task_status(self, task_id: int, status_id: int):
        """Update task status"""
        try:
            data = {
                "status_id": status_id
            }
            result = self.supabase.table("tasks").update(data).eq("task_id", task_id).execute()
            
            if result.data:
                logger.info(f"Task {task_id} status updated to {status_id}")
                return True
            else:
                logger.error(f"Error updating task: {result.error}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating task: {e}")
            return False

    def add_comment(self, task_id: int, author_id: int, message: str):
        """Add comment to task"""
        try:
            data = {
                "task_id": task_id,
                "author_id": author_id,
                "message": message
            }
            result = self.supabase.table("task_comments").insert(data).execute()
            
            if result.data:
                comment_id = result.data[0]['comment_id']
                logger.info(f"Comment added to task {task_id}")
                return comment_id
            else:
                logger.error(f"Error adding comment: {result.error}")
                return None
                
        except Exception as e:
            logger.error(f"Error adding comment: {e}")
            return None

    def get_task_statuses(self):
        """Get all task statuses"""
        try:
            result = self.supabase.table("task_statuses").select("*").order("order_index").execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting statuses: {e}")
            return []

    def test_connection(self):
        """Test database connection"""
        try:
            result = self.supabase.table("task_statuses").select("count").execute()
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False