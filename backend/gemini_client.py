# backend/gemini_client.py
import os
from typing import List, Dict, Optional
import google.generativeai as genai
from dotenv import load_dotenv
from duckduckgo_search import DDGS
# Handle import for both direct execution and package import
try:
    from .database import SupabaseDB
except ImportError:
    from database import SupabaseDB

# Load environment variables from .env file in the backend directory
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

# function uses a query string and duckduckgo_search library to perform a web search
def perform_web_search(query: str, max_results: int = 6) -> List[Dict[str, str]]:
    """Perform a DuckDuckGo search and return a list of results.

    Each result contains: title, href, body.
    """
    results: List[Dict[str, str]] = []
    try:
        with DDGS() as ddgs:
            for result in ddgs.text(query, max_results=max_results):
                # result keys typically include: title, href, body
                results.append({
                    "title": result.get("title", ""),
                    "href": result.get("href", ""),
                    "body": result.get("body", "")
                })
    except Exception as e:
        print(f"Search error: {e}")
    return results


class GeminiClient:
    def __init__(self, use_database: bool = True):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        self.conversation_history: List[Dict[str, str]] = []
        self.use_database = use_database
        self.db: Optional[SupabaseDB] = None
        self.current_conversation_id: Optional[str] = None
        
        if use_database:
            try:
                self.db = SupabaseDB()
            except Exception as e:
                print(f"Warning: Could not initialize Supabase. Running without persistence: {e}")
                self.use_database = False
                self.db = None
        
        # System prompt that defines the agent's role and capabilities
        # self.system_prompt = """You are an AI Study Planner Agent. Your role is to help users create effective study plans, 
        # provide learning resources, and guide them through their educational journey.

        # You have access to a web search tool. When a user asks for resources, information, or anything that might benefit from 
        # current online information, you can use the search function by detecting search queries.

        # If a user message starts with "search:" or "/search", treat the rest as a search query. Otherwise, analyze if the user 
        # might benefit from web search results. If so, you can suggest performing a search or ask clarifying questions.

        # IMPORTANT: When creating study plans or roadmaps, ALWAYS include a Mermaid diagram at the BEGINNING of your response. 
        # The diagram should visualize the study roadmap structure with a simple flow. Use VALID Mermaid syntax with this format:
        
        # ```mermaid
        # graph TD
        #     A[Main Topic] --> B[Step 1]
        #     A --> C[Step 2]
        #     B --> D[Subtopic 1.1]
        #     B --> E[Subtopic 1.2]
        #     C --> F[Subtopic 2.1]
        #     C --> G[Subtopic 2.2]
        # ```
        
        # CRITICAL Mermaid Requirements:
        # - Use graph TD (top-down) for roadmaps
        # - Node IDs must be unique letters (A, B, C, D, etc.)
        # - Use square brackets [] for node labels: A[Label Text]
        # - Use --> for connections between nodes
        # - Keep it simple with basic nodes and connections
        # - Ensure proper syntax and structure
        # - Put the labels in Quotes
        # - the diagram must be easy to read and understand
        # - Beautify the diagram for clarity
                
        # Always be helpful, encouraging, and provide structured study plans when requested. Remember the conversation history 
        # to provide context-aware responses."""

        self.system_prompt = """
            You are an AI Study Planner Agent. Your role is to help users create effective study plans,
            learning roadmaps, and structured educational guidance.

            You have access to a web search tool. When a user asks for learning resources, references,
            or information that may benefit from current online data, you may suggest or perform a web search.

            ────────────────────────────────────────
            MERMAID ROADMAP REQUIREMENTS (CRITICAL)
            ────────────────────────────────────────

            When creating a study plan or roadmap, you MUST include a Mermaid diagram
            at the VERY BEGINNING of your response.

            The diagram must be VALID Mermaid syntax and follow ALL rules below.

            MERMAID FORMAT:
            ```mermaid
            flowchart TD
            STRUCTURE RULES:

            Use flowchart TD (top-down)

            Use clear section comments such as:
            %% Phase 1: Foundations
            %% Phase 2: Core Topics

            Node IDs must be unique and readable (A, B, C, A1, B1, etc.)

            Use square brackets for labels: A[Topic Name]

            Use --> for all connections

            Keep labels short and meaningful

            Avoid complex crossings or dense layouts

            Make sure the syntax is correct so it can be rendered properly

            STYLING RULES (MANDATORY):

            The diagram MUST be colorful and well-structured

            Use consistent colors for nodes belonging to the same phase

            Use either style OR classDef (preferred) for coloring

            Use soft, readable pastel colors

            Do NOT use icons, emojis, or HTML

            COLOR SEMANTICS:

            Foundations / Basics → light blue (#b3d9ff)

            Core Concepts → light green (#c2f0c2)

            Practice / Exercises → light yellow (#fff2b3)

            Projects / Application → light purple (#e0ccff)

            Review / Assessment → light red (#f8b4b4)

            RECOMMENDED CLASS DEFINITIONS:

            classDef foundation fill:#b3d9ff
            classDef core fill:#c2f0c2
            classDef practice fill:#fff2b3
            classDef project fill:#e0ccff
            classDef review fill:#f8b4b4
            Apply classes using:
            A[Topic]:::foundation

            READABILITY REQUIREMENTS:

            The roadmap must be understandable at a glance

            Each phase should clearly flow into the next

            The diagram should visually reflect a learning progression

            ────────────────────────────────────────
            RESPONSE STYLE
            ────────────────────────────────────────

            Always start with the Mermaid diagram

            Follow the diagram with a clear, structured explanation

            Be encouraging, concise, and educational

            Adapt the roadmap depth to the user’s level (beginner, intermediate, advanced)
            """

    def _detect_search_query(self, user_message: str) -> str | None:
        """Detect if the user wants to perform a web search."""
        user_message_lower = user_message.lower().strip()
        
        if user_message_lower.startswith("search:") or user_message_lower.startswith("/search"):
            # Extract the query after "search:" or "/search"
            if user_message_lower.startswith("search:"):
                query = user_message[len("search:"):].strip()
            else:
                query = user_message[len("/search"):].strip()
            return query if query else None
        return None

    def set_conversation_id(self, conversation_id: str):
        """Set the current conversation ID and load history from database."""
        self.current_conversation_id = conversation_id
        
        if self.use_database and self.db:
            # Load conversation history from database
            self.conversation_history = self.db.get_conversation_history(conversation_id)

    def chat(self, user_message: str, session_id: Optional[str] = None, user_settings: Optional[Dict] = None) -> str:
        """Process user message and return AI response."""
        # Initialize conversation if using database
        if self.use_database and self.db and session_id:
            if not self.current_conversation_id:
                conversation_id = self.db.get_or_create_conversation(session_id)
                if conversation_id:
                    self.set_conversation_id(conversation_id)
            elif not self.conversation_history:
                # Reload history if empty
                self.conversation_history = self.db.get_conversation_history(self.current_conversation_id)
        
        # Check if user wants to search
        search_query = self._detect_search_query(user_message)
        
        if search_query:
            # Perform web search
            search_results = perform_web_search(search_query, max_results=6)
            
            if search_results:
                # Format search results for the model
                search_context = "\n\n--- Web Search Results ---\n"
                for idx, result in enumerate(search_results, 1):
                    search_context += f"\n[{idx}] {result['title']}\n"
                    search_context += f"URL: {result['href']}\n"
                    search_context += f"Summary: {result['body']}\n"
                
                # Add search context to the user message
                enhanced_message = f"{user_message}\n\n{search_context}\n\nPlease provide a helpful response based on these search results, citing sources with [1], [2], etc."
            else:
                enhanced_message = f"{user_message}\n\n(Note: Web search did not return results. Please respond based on your knowledge.)"
        else:
            enhanced_message = user_message

        # Add user settings context if provided
        settings_context = ""
        if user_settings:
            settings_parts = []
            if user_settings.get("duration"):
                settings_parts.append(f"Study Duration: {user_settings['duration']}")
            if user_settings.get("current_level"):
                settings_parts.append(f"Current Level: {user_settings['current_level']}")
            if user_settings.get("study_field"):
                settings_parts.append(f"Study Field: {user_settings['study_field']}")
            if settings_parts:
                settings_context = "\n\nUser Settings:\n" + "\n".join(settings_parts) + "\n"
                enhanced_message = settings_context + enhanced_message

        # Add user message to conversation history
        self.conversation_history.append({"role": "user", "content": enhanced_message})
        
        # Save user message to database
        if self.use_database and self.db and self.current_conversation_id:
            self.db.save_message(self.current_conversation_id, "user", enhanced_message)

        # Prepare the full conversation context
        conversation_text = self.system_prompt + "\n\n"
        for msg in self.conversation_history:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                conversation_text += f"User: {content}\n\n"
            else:
                conversation_text += f"Assistant: {content}\n\n"
        
        conversation_text += "Assistant:"

        try:
            # Generate response using Gemini
            response = self.model.generate_content(conversation_text)
            ai_response = response.text.strip()

            # Add AI response to conversation history
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            
            # Save AI response to database
            if self.use_database and self.db and self.current_conversation_id:
                self.db.save_message(self.current_conversation_id, "assistant", ai_response)

            return ai_response
        except Exception as e:
            return f"Error generating response: {str(e)}"

    def reset_conversation(self):
        """Reset the conversation history."""
        if self.use_database and self.db and self.current_conversation_id:
            self.db.clear_conversation(self.current_conversation_id)
        self.conversation_history = []
        self.current_conversation_id = None

    def parse_mermaid_diagram(self, mermaid_code: str) -> List[Dict[str, str]]:
        """Parse Mermaid diagram code to extract nodes and their labels."""
        import re

        items = []

        # Find all node definitions like A[Label Text] or A[Label]
        node_pattern = r'([A-Z]\w*)\[([^\]]+)\]'
        matches = re.findall(node_pattern, mermaid_code)

        for node_id, label in matches:
            # Clean up the label
            clean_label = label.strip()
            items.append({
                "id": node_id,
                "title": clean_label,
                "description": f"Complete: {clean_label}"
            })

        return items

    def save_roadmap(self, title: str, mermaid_diagram: str) -> Optional[str]:
        """Save a roadmap with its items to the database."""
        if not self.use_database or not self.db or not self.current_conversation_id:
            return None

        try:
            # Parse the diagram to extract items
            items = self.parse_mermaid_diagram(mermaid_diagram)

            # Save roadmap and items
            roadmap_id = self.db.save_roadmap(
                conversation_id=self.current_conversation_id,
                title=title,
                mermaid_diagram=mermaid_diagram,
                items=items
            )

            return roadmap_id
        except Exception as e:
            print(f"Error saving roadmap: {e}")
            return None

    def get_roadmaps(self) -> List[Dict]:
        """Get all roadmaps for the current conversation."""
        if not self.use_database or not self.db or not self.current_conversation_id:
            return []

        return self.db.get_roadmaps(self.current_conversation_id)

    def get_roadmap_progress(self, roadmap_id: str) -> Dict:
        """Get progress for a specific roadmap."""
        if not self.use_database or not self.db:
            return {"total_items": 0, "completed_items": 0, "progress_percentage": 0, "items": []}

        return self.db.get_roadmap_progress(roadmap_id)

    def update_item_progress(self, item_id: str, completed: bool) -> bool:
        """Update the completion status of a roadmap item."""
        if not self.use_database or not self.db:
            return False

        return self.db.update_item_progress(item_id, completed)

