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
import subprocess

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
whisper_model = whisper.load_model("tiny", device="cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Loaded Whisper model on device: {whisper_model.device}")

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'wav', 'mp3', 'm4a', 'webm', 'ogg', 'mp4'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_audio(input_path, output_path):
    """Convert audio to WAV format using ffmpeg."""
    try:
        # First, check if input file exists and has content
        if not os.path.exists(input_path):
            logger.error(f"Input file does not exist: {input_path}")
            return False
            
        if os.path.getsize(input_path) == 0:
            logger.error(f"Input file is empty: {input_path}")
            return False
            
        # Log the input file details
        logger.info(f"Converting audio file: {input_path}")
        logger.info(f"File size: {os.path.getsize(input_path)} bytes")
        
        command = [
            'ffmpeg',
            '-i', input_path,
            '-acodec', 'pcm_s16le',
            '-ar', '16000',
            '-ac', '1',
            '-y',
            output_path
        ]
        
        logger.info(f"Running FFmpeg command: {' '.join(command)}")
        
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode()
            logger.error(f"FFmpeg error: {error_msg}")
            raise Exception(f"FFmpeg conversion failed: {error_msg}")
            
        # Verify the output file
        if not os.path.exists(output_path):
            logger.error("Output file was not created")
            return False
            
        if os.path.getsize(output_path) == 0:
            logger.error("Output file is empty")
            return False
            
        logger.info(f"Successfully converted audio to WAV format: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error converting audio: {str(e)}")
        return False

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
        
        # Generate a simple summary
        summary = "Key points:\n" + "\n".join([
            "- " + line.strip()
            for line in response.split('.')
            if len(line.strip()) > 20
        ][:3])
        
        return jsonify({
            'text_response': response,
            'summary': summary
        })
    except IndexError:
        return jsonify({
            'text_response': "I don't have any documents to search through yet. Please upload some documents first.",
            'summary': "No documents available for analysis."
        }), 200
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
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
    
    # Create temporary files for input and output
    with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_input_file, \
         tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_output_file:
        try:
            # Save the uploaded file
            audio_file.save(temp_input_file.name)
            logger.info(f"Saved input file to: {temp_input_file.name}")
            
            # Convert to WAV if needed
            if not convert_audio(temp_input_file.name, temp_output_file.name):
                raise Exception("Failed to convert audio to WAV format")
            
            # Verify the WAV file is valid
            if not os.path.getsize(temp_output_file.name) > 0:
                raise ValueError("Empty audio file")
            
            # Transcribe using Whisper
            logger.info(f"Transcribing audio: {temp_output_file.name}")
            result = whisper_model.transcribe(
                temp_output_file.name,
                language="en",
                fp16=False,
                beam_size=1,
                best_of=1,
                temperature=0.0
            )
            
            if not result or 'text' not in result:
                raise ValueError("No transcription result")
            
            return jsonify({'transcription': result['text']})
            
        except Exception as e:
            logger.error(f"Error during transcription: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
        finally:
            # Clean up the temporary files
            try:
                os.unlink(temp_input_file.name)
                os.unlink(temp_output_file.name)
            except Exception as e:
                logger.warning(f"Error cleaning up temporary files: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True) 