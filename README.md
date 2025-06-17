# Voice-Based Document Chatbot

A real-time voice-based chatbot that can process PDFs and images, and answer questions about their content using natural language.

## Features

- 🎤 Voice input using Web Speech API
- 📄 PDF text extraction
- 🖼️ Image OCR using EasyOCR
- 🔍 Semantic search using FAISS and sentence-transformers
- 🤖 LLM-powered responses using Groq
- 🔊 Text-to-speech output using Coqui TTS

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory and add your Groq API key:
```
GROQ_API_KEY=your_api_key_here
```

5. Run the application:
```bash
python app.py
```

6. Open your browser and navigate to `http://localhost:5000`

## Usage

1. Upload Documents:
   - Click the "Choose File" button to select a PDF or image
   - Click "Upload" to process the document

2. Ask Questions:
   - Click the "Start Recording" button
   - Speak your question
   - Click "Stop Recording" when finished
   - The chatbot will process your question and respond with both text and voice

## Project Structure

```
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── templates/         # HTML templates
│   └── index.html    # Main page template
├── static/           # Static files
│   ├── js/          # JavaScript files
│   │   └── voice.js # Voice handling
│   └── css/         # CSS files
│       └── styles.css
├── uploads/          # Uploaded files and generated audio
└── modules/          # Backend modules
    ├── pdf_parser.py    # PDF text extraction
    ├── image_ocr.py     # Image OCR
    ├── vector_store.py  # Vector storage and search
    ├── llm_query.py     # LLM integration
    └── prompts.py          # pre-defined prompt
```

## Requirements

- Python 3.8+
- Modern web browser with Web Speech API support
- Microphone access
- Groq API key

## License

MIT License 