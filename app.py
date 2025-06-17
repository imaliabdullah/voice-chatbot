import os
from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename
from modules.pdf_parser import extract_text_from_pdf
from modules.image_ocr import extract_text_from_image
from modules.vector_store import VectorStore
from modules.llm_query import query_llm
# from modules.tts import text_to_speech
import tempfile
import whisper
import logging
import torch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize vector store and Whisper model
vector_store = VectorStore()
# Use the smallest model for faster transcription
whisper_model = whisper.load_model("tiny", device="cuda" if torch.cuda.is_available() else "cpu")

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'wav', 'mp3', 'm4a', 'webm'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        logger.error("No file part in request")
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        logger.error("No selected file")
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        logger.info(f"Saving uploaded file to: {filepath}")
        file.save(filepath)
        
        try:
            # Extract text based on file type
            if filename.endswith('.pdf'):
                logger.info("Processing PDF file")
                text = extract_text_from_pdf(filepath)
            else:
                logger.info("Processing image file")
                text = extract_text_from_image(filepath)
            
            if not text.strip():
                logger.error("No text extracted from file")
                return jsonify({'error': 'No text could be extracted from the file'}), 400
            
            # Add to vector store
            logger.info("Adding extracted text to vector store")
            vector_store.add_document(text)
            
            # Save vector store to disk
            vector_store_path = os.path.join(app.config['UPLOAD_FOLDER'], 'vector_store')
            vector_store.save(vector_store_path)
            
            logger.info("File processed successfully")
            return jsonify({'message': 'File processed successfully'})
            
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    
    logger.error(f"Invalid file type: {file.filename}")
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/query', methods=['POST'])
def process_query():
    data = request.json
    if not data or 'query' not in data:
        return jsonify({'error': 'No query provided'}), 400
    
    query = data['query']
    
    try:
        # Get relevant context from vector store
        context = vector_store.search(query)
        
        # Get response from LLM
        response = query_llm(query, context)
        
        # Generate a simple summary (you can enhance this later)
        summary = "Key points:\n" + "\n".join([
            "- " + line.strip()
            for line in response.split('.')
            if len(line.strip()) > 20
        ][:3])  # Take first 3 substantial sentences as summary
        
        return jsonify({
            'text_response': response,
            'summary': summary,
            'audio_url': None
        })
    except IndexError:
        return jsonify({
            'text_response': "I don't have any documents to search through yet. Please upload some documents first.",
            'summary': "No documents available for analysis.",
            'audio_url': None
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/audio/<filename>')
def get_audio(filename):
    return send_file(os.path.join('uploads', filename), mimetype='audio/wav')

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    if 'audio' not in request.files:
        logger.error("No audio file provided")
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    if audio_file.filename == '':
        logger.error("No selected file")
        return jsonify({'error': 'No selected file'}), 400
    
    # Save the audio file temporarily
    temp_audio_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_audio.webm')
    audio_file.save(temp_audio_path)
    
    try:
        logger.info("Starting transcription")
        # Transcribe using Whisper with optimized settings
        result = whisper_model.transcribe(
            temp_audio_path,
            language='en',  # Specify language for faster processing
            fp16=False,     # Use FP32 for better compatibility
            beam_size=1     # Use smaller beam size for faster processing
        )
        transcription = result["text"]
        
        # Clean up temporary file
        os.remove(temp_audio_path)
        
        logger.info("Transcription completed successfully")
        return jsonify({
            'transcription': transcription
        })
    except Exception as e:
        # Clean up temporary file in case of error
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
        logger.error(f"Transcription error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 