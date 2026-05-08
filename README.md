# Airport App with Chatbot

A Flask-based airport information application with an integrated AI chatbot for answering user queries about flights, airports, airlines, schedules, delays, and routes.

## Features

- **Flight Information**: Search and view flight details by flight number
- **Airport Information**: Get details about airports worldwide
- **Airline Information**: View airline details and statistics
- **Flight Schedules**: Browse scheduled flights
- **Delay Information**: Track flight delays
- **Route Information**: Find routes between airports
- **Nearby Airports**: Discover airports near a location
- **AI Chatbot**: Natural language interface to query all the above information

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- An API key from [AirLabs](https://airlabs.co/)
- (Optional) Ollama for AI-powered chatbot responses

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/ramc99/airport-app.git
cd airport-app
```

### 2. Create a Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

If `requirements.txt` doesn't exist, install the required packages manually:

```bash
pip install flask requests python-dotenv
```

### 4. Set Up Environment Variables

Create a `.env` file in the project root directory:

```bash
cp .env.example .env
```

Edit the `.env` file and add your API keys:

```
AIRLABS_API_KEY=your_api_key_here
FLASK_SECRET_KEY=your_secret_key

# Ollama LLM Configuration (optional - falls back to rule-based if not set)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

You can get a free API key from [AirLabs](https://airlabs.co/).

**For AI-powered chatbot responses:**

1. Install Ollama from [https://ollama.ai/](https://ollama.ai/)
2. Pull a language model:
   ```bash
   ollama pull llama3.2
   ```
3. Start Ollama server:
   ```bash
   ollama serve
   ```

Note: If Ollama is not configured or unavailable, the chatbot will automatically fall back to a rule-based response system.

## Running the Application

### Start the Server

```bash
python app.py
```

The application will start on `http://127.0.0.1:5000`

### Access the Application

Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

## Using the Chatbot

The chatbot is accessible from any page in the application:

1. **Open the Chatbot**: Click the "Chat" button in the bottom-right corner of the screen
2. **Ask Questions**: Type your question in natural language
3. **Get Answers**: The chatbot will process your query and provide relevant information

### Example Queries

**Flight Status:**
- "What's the status of BA178?"
- "Show me flight AA100"
- "Where is flight DL456?"

**Airport Information:**
- "Tell me about JFK airport"
- "What's the code for Heathrow?"
- "Show me details for LAX"

**Airline Information:**
- "Which airlines fly from LHR?"
- "Tell me about Delta Airlines"
- "Show me British Airways info"

**Delays:**
- "Show me delays at JFK"
- "Are there any delays at ORD?"
- "What flights are delayed?"

**Schedules:**
- "Show me schedules from LHR to JFK"
- "What flights leave from CDG tomorrow?"
- "Find flights to Dubai"

**Routes:**
- "Which airlines fly from LHR to JFK?"
- "Show me routes from SFO to LAX"
- "How can I get from Paris to New York?"

## Project Structure

```
airport-app/
├── app.py              # Main Flask application with chatbot API
├── airlabs.py          # AirLabs API integration module
├── static/
│   ├── style.css       # CSS styles including chatbot styling
│   └── ...             # Other static files
├── templates/
│   ├── base.html       # Base template with chatbot UI
│   ├── index.html      # Home page
│   ├── flight.html     # Flight details page
│   ├── airport.html    # Airport details page
│   ├── airline.html    # Airline details page
│   ├── schedules.html  # Flight schedules page
│   ├── delays.html     # Delay information page
│   ├── routes.html     # Route information page
│   ├── nearby.html     # Nearby airports page
│   └── error.html      # Error page
├── .env                # Environment variables (API keys)
├── .env.example        # Example environment file
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## Chatbot Architecture

The chatbot consists of three main components:

### 1. Frontend UI (`templates/base.html`)
- Floating chat widget with toggle button
- Message display area
- Input field for user queries
- JavaScript for handling user interactions

### 2. Styling (`static/style.css`)
- Modern, responsive design
- Matches the application's theme
- Mobile-friendly layout

### 3. Backend API (`app.py`)
- `/api/chat` endpoint for processing queries
- **Ollama LLM Integration**: Uses Ollama API for natural language understanding and generation
- **Fallback System**: Automatically falls back to rule-based responses if Ollama is unavailable
- Intent detection using regex patterns
- Entity extraction (flight numbers, airport codes, airline codes)
- Integration with AirLabs API for real-time data

## Troubleshooting

### Common Issues

**1. Application won't start:**
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check if port 5000 is available
- Verify Python version is 3.8 or higher

**2. Chatbot not responding:**
- Check that the server is running
- Open browser console (F12) to check for JavaScript errors
- Verify the `/api/chat` endpoint is accessible

**3. API errors:**
- Ensure your AirLabs API key is valid
- Check your internet connection
- Verify the API key is correctly set in the `.env` file

**4. Ollama not responding:**
- Ensure Ollama is installed and running: `ollama serve`
- Check if the model is pulled: `ollama list`
- Verify `OLLAMA_HOST` and `OLLAMA_MODEL` in your `.env` file
- The chatbot will fall back to rule-based responses if Ollama is unavailable

**5. No data showing:**
- The AirLabs API may have rate limits on free plans
- Check if the flight/airport/airline code exists
- Verify the API response in the browser console

## API Reference

### Chat Endpoint

**POST** `/api/chat`

Request Body:
```json
{
  "message": "What's the status of BA178?"
}
```

Response:
```json
{
  "response": "Flight BA178 is currently en route from LHR to JFK..."
}
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Commit your changes: `git commit -am 'Add new feature'`
4. Push to the branch: `git push origin feature/new-feature`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or suggestions, please open an issue on the GitHub repository.

## Acknowledgments

- [AirLabs](https://airlabs.co/) for providing flight data API
- Flask framework community
- All contributors to this project
