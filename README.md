# 🧠 Robert Chat

A multimodal voice and chat assistant built with Flask and powered by AI. Robert Chat supports transcription, intelligent responses, and tool execution based on interpreted intent (e.g., `tool_use: [dance]`).

## 🚀 Features

- 🎙️ Voice transcription with support for multiple models (e.g., Whisper, Google, OpenRouter)
- 🤖 Smart AI response generation
- 🛠️ Tool execution based on AI-detected actions (e.g., `dance`)
- 🌐 Web UI with audio upload and chat functionality
- 🔧 JSON-based configuration and response format handling

---

## 📂 Project Structure

```
robert_chat/
│
├── app.py                      # Main Flask app
├── models/
│   ├── settings.py             # Load/save/update settings
│   ├── model_info.py           # Load model definitions and capabilities
│
├── services/
│   ├── service_factory.py      # Factory for selecting correct AI/transcription service
│   ├── openai_service.py       # Integration with OpenAI models
│   └── google_service.py       # Integration with Google AI models
│
├── utils/
│   ├── prompt_utils.py         # Generate system prompts
│   ├── audio_utils.py          # Audio file handling (e.g., base64 encoding, size check)
│   └── tool_executor.py        # Execute tools like "dance" based on AI response
│
├── templates/
│   └── index.html              # Web UI template
│
├── .env                        # Environment variables (API keys, etc.)
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation (this file)
```

---

## 🛠️ Installation

1. **Clone the repo**

```bash
git clone https://github.com/yourusername/robert_chat.git
cd robert_chat
```

2. **Create virtual environment**

```bash
python -m venv envs/robert_chat
source envs/robert_chat/Scripts/activate  # On Windows
# or
source envs/robert_chat/bin/activate      # On Unix/macOS
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set up environment variables**

Create a `.env` file and add your API keys:

```env
OPENAI_API_KEY=your-key-here
GOOGLE_API_KEY=your-key-here
```

---

## 🧪 Running the App

```bash
python app.py
```

Then open your browser and visit:  
`http://127.0.0.1:5000`

---

## 🧰 API Endpoints

| Method | Endpoint         | Description                                |
|--------|------------------|--------------------------------------------|
| GET    | `/`              | Render the web UI                          |
| GET    | `/models`        | List available models                      |
| GET    | `/settings`      | Get current settings                       |
| POST   | `/settings`      | Update model settings                      |
| POST   | `/transcribe`    | Upload audio and get transcription/response |
| POST   | `/chat`          | Send text and receive AI response          |
| GET    | `/test-tool`     | Test the tool execution engine             |

---

## 🧠 Example Response Format

```json
{
  "transcription": "Can you dance?",
  "response": "Sure, let's dance!",
  "tool_use": "tool_use: [dance]"
}
```

---

## 📄 License

MIT © [Your Name](https://github.com/yourusername)
