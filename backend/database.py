# backend/database.py
import os
from typing import List, Dict, Optional
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file in the backend directory
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)


class SupabaseDB:
    def __init__(self):
        """Initialize Supabase client following official documentation."""
        # Use os.environ.get() as per Supabase documentation
        supabase_url: str = os.environ.get("SUPABASE_URL", "")
        supabase_key: str = os.environ.get("SUPABASE_KEY", "")
        
        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set in environment variables. "
                "Please check your .env file in the backend directory."
            )
        
        # Initialize Supabase client as per official documentation
        # Reference: https://supabase.com/docs/reference/python/initializing
        try:
            self.client: Client = create_client(supabase_url, supabase_key)
            self.conversations_table = "conversations"
            self.messages_table = "messages"
            self.roadmaps_table = "roadmaps"
            self.roadmap_items_table = "roadmap_items"
        except Exception as e:
            raise ConnectionError(
                f"Failed to initialize Supabase client: {str(e)}. "
                "Please verify your SUPABASE_URL and SUPABASE_KEY are correct."
            ) from e

    def create_conversation(self, session_id: str) -> Optional[str]:
        """Create a new conversation record and return conversation ID."""
        try:
            response = self.client.table(self.conversations_table).insert({
                "session_id": session_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).execute()
            
            # Check if response has data
            if response.data and len(response.data) > 0:
                return response.data[0].get("id")
            return None
        except Exception as e:
            error_msg = str(e)
            # Check if it's a table not found error - suppress repeated errors
            if "PGRST205" in error_msg or "Could not find the table" in error_msg:
                # Error message is handled in get_or_create_conversation to avoid duplicates
                return None
            else:
                print(f"Error creating conversation: {e}")
                if hasattr(e, 'message'):
                    print(f"Error message: {e.message}")
            return None

    def get_or_create_conversation(self, session_id: str) -> Optional[str]:
        """Get existing conversation ID or create a new one."""
        try:
            # Try to find existing conversation
            # Using order by created_at descending to get the most recent
            response = self.client.table(self.conversations_table)\
                .select("id")\
                .eq("session_id", session_id)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0].get("id")
            
            # Create new conversation if not found
            return self.create_conversation(session_id)
        except Exception as e:
            error_msg = str(e)
            # Check if it's a table not found error - suppress repeated errors
            if "PGRST205" in error_msg or "Could not find the table" in error_msg:
                # Only show error once using a class variable
                if not hasattr(self, '_table_error_shown'):
                    print("\n" + "="*70)
                    print("⚠️  DATABASE SETUP REQUIRED")
                    print("="*70)
                    print("The Supabase tables have not been created yet.")
                    print("\nTo fix this:")
                    print("1. Go to your Supabase project dashboard")
                    print("2. Navigate to SQL Editor")
                    print("3. Run the SQL script from: supabase_schema.sql")
                    print("4. The script will create the 'conversations' and 'messages' tables")
                    print("\nThe app will continue to work without database persistence.")
                    print("(This message will only show once)")
                    print("="*70 + "\n")
                    self._table_error_shown = True
                # Return None silently - app will work without database
                return None
            else:
                # Other errors - log them
                print(f"Error getting/creating conversation: {e}")
                if hasattr(e, 'message'):
                    print(f"Error message: {e.message}")
            return None

    def save_message(self, conversation_id: str, role: str, content: str) -> bool:
        """Save a message to the database."""
        try:
            self.client.table(self.messages_table).insert({
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "created_at": datetime.utcnow().isoformat()
            }).execute()
            return True
        except Exception as e:
            print(f"Error saving message: {e}")
            return False

    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, str]]:
        """Retrieve conversation history from database."""
        try:
            # Order by created_at ascending to get chronological order
            response = self.client.table(self.messages_table)\
                .select("role, content")\
                .eq("conversation_id", conversation_id)\
                .order("created_at", desc=False)\
                .execute()
            
            if response.data:
                return [
                    {
                        "role": msg.get("role", ""),
                        "content": msg.get("content", "")
                    }
                    for msg in response.data
                ]
            return []
        except Exception as e:
            print(f"Error retrieving conversation history: {e}")
            if hasattr(e, 'message'):
                print(f"Error message: {e.message}")
            return []

    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear all messages for a conversation."""
        try:
            self.client.table(self.messages_table)\
                .delete()\
                .eq("conversation_id", conversation_id)\
                .execute()
            return True
        except Exception as e:
            print(f"Error clearing conversation: {e}")
            return False

    def save_roadmap(self, conversation_id: str, title: str, mermaid_diagram: str, items: List[Dict[str, str]]) -> Optional[str]:
        """Save a roadmap and its items to the database."""
        try:
            # Save roadmap
            roadmap_response = self.client.table(self.roadmaps_table).insert({
                "conversation_id": conversation_id,
                "title": title,
                "mermaid_diagram": mermaid_diagram,
                "created_at": datetime.utcnow().isoformat()
            }).execute()

            if not roadmap_response.data or len(roadmap_response.data) == 0:
                return None

            roadmap_id = roadmap_response.data[0].get("id")

            # Save roadmap items
            items_data = []
            for item in items:
                items_data.append({
                    "roadmap_id": roadmap_id,
                    "item_id": item.get("id", ""),
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "completed": False
                })

            if items_data:
                self.client.table(self.roadmap_items_table).insert(items_data).execute()

            return roadmap_id
        except Exception as e:
            print(f"Error saving roadmap: {e}")
            return None

    def get_roadmaps(self, conversation_id: str) -> List[Dict]:
        """Get all roadmaps for a conversation."""
        try:
            response = self.client.table(self.roadmaps_table)\
                .select("id, title, mermaid_diagram, created_at")\
                .eq("conversation_id", conversation_id)\
                .order("created_at", desc=True)\
                .execute()

            return response.data if response.data else []
        except Exception as e:
            print(f"Error getting roadmaps: {e}")
            return []

    def get_roadmap_items(self, roadmap_id: str) -> List[Dict]:
        """Get all items for a roadmap."""
        try:
            response = self.client.table(self.roadmap_items_table)\
                .select("id, item_id, title, description, completed, completed_at")\
                .eq("roadmap_id", roadmap_id)\
                .order("item_id")\
                .execute()

            return response.data if response.data else []
        except Exception as e:
            print(f"Error getting roadmap items: {e}")
            return []

    def update_item_progress(self, item_id: str, completed: bool) -> bool:
        """Update the completion status of a roadmap item."""
        try:
            update_data = {
                "completed": completed,
                "completed_at": datetime.utcnow().isoformat() if completed else None
            }

            self.client.table(self.roadmap_items_table)\
                .update(update_data)\
                .eq("id", item_id)\
                .execute()
            return True
        except Exception as e:
            print(f"Error updating item progress: {e}")
            return False

    def get_roadmap_progress(self, roadmap_id: str) -> Dict:
        """Get progress statistics for a roadmap."""
        try:
            items = self.get_roadmap_items(roadmap_id)
            total_items = len(items)
            completed_items = len([item for item in items if item.get("completed", False)])

            return {
                "total_items": total_items,
                "completed_items": completed_items,
                "progress_percentage": (completed_items / total_items * 100) if total_items > 0 else 0,
                "items": items
            }
        except Exception as e:
            print(f"Error getting roadmap progress: {e}")
            return {"total_items": 0, "completed_items": 0, "progress_percentage": 0, "items": []}

