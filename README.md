# AI Study Planner Agent

An advanced AI-powered study planner agent built with Google Gemini API, Flask, and Tailwind CSS. This agent can understand your goals, make decisions, and help you create effective study plans with the ability to search the web for relevant resources.

## Features

- **Persistent Memory**: The agent remembers your entire conversation history using Supabase, allowing it to provide follow-up advice and adapt its plans based on your feedback across sessions.
- **Web Search**: The agent can perform real-time web searches using DuckDuckGo to find relevant online resources and provide up-to-date information.
- **Goal-Based Planning**: Create personalized study plans tailored to your learning goals.
- **Interactive Settings**: Adjust study duration, current level, and study field to get personalized recommendations.
- **Visual Roadmaps**: Study plans include Mermaid diagrams visualizing the learning path and structure.
- **Progress Tracking**: Track your learning progress with interactive checklists for each roadmap item, including completion status and progress metrics.
- **Modern UI**: Clean, user-friendly interface built with Streamlit.
- **Database Integration**: All conversations, roadmaps, and progress data are stored in Supabase for persistence and retrieval.

## Prerequisites

Before you begin, ensure you have:

- Python 3.7 or higher installed
- A Google AI Studio account (for Gemini API key)
- A Supabase account (free tier works fine)
- Basic knowledge of Python and web development

## Setup Instructions

### 1. Clone or Download the Project

Navigate to the project directory:

```bash
cd study-planner
```

### 2. Create a Virtual Environment

It's recommended to work in a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

Install all required packages:

```bash
pip install -r requirements.txt
```

### 4. Get Your Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key" in the API Keys section
4. **Important**: Save your API key immediately - you may not be able to see it again!

### 5. Set Up Supabase Database

1. Go to [Supabase](https://supabase.com) and create a free account
2. Create a new project
3. Once your project is ready, go to **Settings** → **API**
4. Copy your **Project URL** and **anon/public key**
5. Go to **SQL Editor** in your Supabase dashboard
6. Run the SQL script from `supabase_schema.sql` to create the necessary tables:
   - `conversations` table to store conversation sessions
   - `messages` table to store individual messages
   - `roadmaps` table to store generated study roadmaps
   - `roadmap_items` table to store individual roadmap items for progress tracking

### 6. Configure Environment Variables

1. Open `backend/.env` file (it should already exist)
2. Add your credentials:
   ```
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_KEY=your_supabase_anon_key_here
   ```

**Note**: The `.env` file is already created for you. Just add your actual API keys.

## Running the Application

1. Make sure you're in the project root directory (not the backend folder)

2. Run the Streamlit application:
   ```bash
   streamlit run app.py
   ```

3. The application will automatically open in your browser at:
   ```
   http://localhost:8501
   ```

   If it doesn't open automatically, you can manually navigate to the URL shown in the terminal.

## Usage Examples

### Basic Study Planning
- "Make me a 3-week plan to learn Java programming for beginners."
- "Provide me a quiz on AI agents development."
- "I want to learn Python. Create a study schedule for 2 months."

### Web Search
You can trigger web searches using these formats:
- `search: resources for java`
- `/search how to prepare frontend coding interviews`

When you use the search prefix, the agent will:
1. Fetch relevant links from DuckDuckGo
2. Ask Gemini to synthesize the information
3. Provide a response with inline citations like [1], [2], etc.

## Project Structure

```
study-planner/
├── app.py                  # Streamlit main application
├── backend/
│   ├── .env                # Environment variables (API keys)
│   ├── gemini_client.py    # Gemini client with web search
│   └── database.py        # Supabase database integration
├── requirements.txt        # Python dependencies
├── supabase_schema.sql     # Database schema for Supabase
└── README.md              # This file
```

## How It Works

1. **Conversation Memory**: The agent maintains a conversation history stored in Supabase that is loaded and sent to Gemini with each request, allowing for context-aware responses across sessions.

2. **Database Persistence**: 
   - Each conversation session is stored in Supabase
   - Messages are saved to the database in real-time
   - Conversation history is automatically loaded when a session continues

3. **Roadmap Generation**:
   - When users request study plans, the AI generates Mermaid diagrams visualizing the learning path
   - Roadmaps are automatically parsed and saved to the database with individual trackable items

4. **Progress Tracking**:
   - Users can select saved roadmaps and track completion of individual items
   - Progress is displayed with metrics and visual progress bars
   - Completion status is saved in real-time to the database

5. **User Settings**: 
   - Users can configure their study duration, current level, and study field
   - These settings are automatically included in prompts to personalize study plans
   - Settings are stored in session state and persist during the conversation

4. **Visual Roadmaps**: 
   - The AI generates Mermaid diagrams to visualize study roadmaps
   - Diagrams are automatically rendered in the Streamlit interface
   - Users can view both the rendered diagram and the source code

5. **Web Search Integration**: When a user message starts with "search:" or "/search", the agent:
   - Extracts the search query
   - Performs a DuckDuckGo search
   - Formats the results
   - Sends them to Gemini for synthesis
   - Returns a response with citations

6. **Streamlit Interface**: 
   - Clean, interactive UI with sidebar settings
   - Real-time chat interface
   - Automatic diagram rendering
   - Session management built-in

## Troubleshooting

### API Key Issues
- Ensure your `.env` file is in the `backend/` directory
- Verify your API keys (Gemini and Supabase) are correct and have no extra spaces
- Check that you've activated your virtual environment

### Supabase Connection Issues
- Verify your Supabase URL and key are correct in `.env`
- Make sure you've run the SQL schema script in Supabase SQL Editor
- Check that Row Level Security (RLS) policies are set correctly
- If you see database errors, the app will continue to work but without persistence

### Import Errors
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Verify you're using the correct Python interpreter (the one in your virtual environment)

### Port Already in Use
- If port 5000 is already in use, modify `app.py` to use a different port:
  ```python
  app.run(debug=True, host="0.0.0.0", port=5001)
  ```

## Future Enhancements

- Save conversation histories in a database
- Add user authentication for multiple users
- Connect to calendars or task managers
- Add more tools and capabilities
- Implement conversation export/import

## License

This project is open source and available for educational purposes.

## Credits

Based on the tutorial: [How to Build an AI Study Planner Agent using Gemini in Python](https://www.freecodecamp.org/news/how-to-build-an-ai-study-planner-agent-using-gemini-in-python/)

## Support

If you encounter any issues or have questions, please refer to the original tutorial or check the documentation for the libraries used:
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Google Gemini API](https://ai.google.dev/)
- [DuckDuckGo Search](https://github.com/deedy5/duckduckgo_search)

