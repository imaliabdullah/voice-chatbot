let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let transcriptionTimeout;
let silenceTimer;
let isProcessing = false;
let audioContext;
let analyser;
let silenceStartTime = null;
let isSilent = false;

// DOM Elements
const startButton = document.getElementById('startRecording');
const stopButton = document.getElementById('stopRecording');
const recordingStatus = document.getElementById('recordingStatus');
const uploadForm = document.getElementById('uploadForm');
const uploadStatus = document.getElementById('uploadStatus');

// Content containers
const transcriptionContent = document.querySelector('.transcription-content');
const responseContent = document.querySelector('.response-content');
const summaryContent = document.querySelector('.summary-content');

// Interview state
let interviewState = {
    isActive: false,
    lastQuestionTime: null,
    silenceThreshold: 2000, // 2 seconds of silence to consider question complete
    processingTimeout: 30000, // 30 seconds max processing time
    silenceThresholdDb: -50, // Silence threshold in decibels
    silenceCheckInterval: 100 // Check for silence every 100ms
};

// Create progress elements
function createProgressElement() {
    const statusDiv = document.createElement('div');
    statusDiv.className = 'processing-status';
    
    const spinner = document.createElement('div');
    spinner.className = 'loading-spinner';
    
    const text = document.createElement('span');
    text.className = 'loading-text';
    text.textContent = 'Processing question...';
    
    const progressContainer = document.createElement('div');
    progressContainer.className = 'progress-container';
    
    const progressBar = document.createElement('div');
    progressBar.className = 'progress-bar';
    
    progressContainer.appendChild(progressBar);
    statusDiv.appendChild(spinner);
    statusDiv.appendChild(text);
    statusDiv.appendChild(progressContainer);
    
    return { statusDiv, progressBar };
}

// Handle file upload
uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        uploadStatus.textContent = 'Please select a file';
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        uploadStatus.textContent = 'Uploading...';
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        
        if (response.ok) {
            uploadStatus.textContent = 'File uploaded successfully';
            fileInput.value = '';
        } else {
            uploadStatus.textContent = `Error: ${data.error}`;
        }
    } catch (error) {
        uploadStatus.textContent = 'Error uploading file';
        console.error('Upload error:', error);
    }
});

// Handle voice recording
startButton.addEventListener('click', async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        // Set up audio context and analyser
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioContext.createAnalyser();
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);
        
        // Configure analyser
        analyser.fftSize = 2048;
        analyser.smoothingTimeConstant = 0.8;
        
        mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm;codecs=opus',
            audioBitsPerSecond: 128000
        });
        
        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            if (isProcessing) return; // Don't process if already processing
            
            isProcessing = true;
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            audioChunks = [];
            
            // Create progress indicator
            const { statusDiv, progressBar } = createProgressElement();
            transcriptionContent.appendChild(statusDiv);
            
            // Send audio to backend for transcription
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.webm');
            
            try {
                recordingStatus.textContent = 'Processing question...';
                
                // Simulate progress
                let progress = 0;
                const progressInterval = setInterval(() => {
                    progress += 5;
                    if (progress <= 90) {
                        progressBar.style.width = `${progress}%`;
                    }
                }, 500);
                
                const response = await fetch('/transcribe', {
                    method: 'POST',
                    body: formData
                });
                
                clearInterval(progressInterval);
                progressBar.style.width = '100%';
                
                const data = await response.json();
                
                if (response.ok) {
                    const transcript = data.transcription;
                    statusDiv.remove();
                    
                    // Add only the transcription to the transcription column
                    addTranscription(transcript);
                    
                    // Process the transcript with the LLM
                    const queryResponse = await fetch('/query', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ query: transcript })
                    });
                    
                    const queryData = await queryResponse.json();
                    
                    if (queryResponse.ok) {
                        const sections = parseLLMResponse(queryData.text_response);
                        
                        // Add content to each column while preserving history
                        addResponse(sections.response);
                        addSummary(sections.summary);
                        
                        if (queryData.audio_url) {
                            const audio = new Audio(queryData.audio_url);
                            audio.play();
                        }
                    } else {
                        addResponse('Error processing query');
                    }
                } else {
                    statusDiv.remove();
                    addResponse('Error transcribing audio');
                }
            } catch (error) {
                console.error('Transcription error:', error);
                addResponse('Error processing audio');
            } finally {
                isProcessing = false;
                recordingStatus.textContent = 'Ready for next question';
                // Auto-start recording for next question
                if (interviewState.isActive) {
                    startRecording();
                }
            }
        };

        // Start recording with smaller chunks for more frequent updates
        startRecording();
        interviewState.isActive = true;
        recordingStatus.textContent = 'Listening for questions...';
        
    } catch (error) {
        console.error('Error accessing microphone:', error);
        recordingStatus.textContent = 'Error accessing microphone';
    }
});

function startRecording() {
    if (mediaRecorder && !isRecording) {
        mediaRecorder.start(1000); // Get data every second
        isRecording = true;
        startButton.style.display = 'none';
        stopButton.style.display = 'block';
        startSilenceDetection();
    }
}

function startSilenceDetection() {
    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    
    function checkSilence() {
        if (!isRecording || isProcessing) return;
        
        analyser.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
        const db = 20 * Math.log10(average / 255);
        
        if (db < interviewState.silenceThresholdDb) {
            if (!isSilent) {
                isSilent = true;
                silenceStartTime = Date.now();
            } else if (Date.now() - silenceStartTime > interviewState.silenceThreshold) {
                console.log('Silence detected, stopping recording');
                mediaRecorder.stop();
                isRecording = false;
                return;
            }
        } else {
            isSilent = false;
            silenceStartTime = null;
        }
        
        if (isRecording) {
            setTimeout(checkSilence, interviewState.silenceCheckInterval);
        }
    }
    
    checkSilence();
}

stopButton.addEventListener('click', () => {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        interviewState.isActive = false;
        startButton.style.display = 'block';
        stopButton.style.display = 'none';
        recordingStatus.textContent = 'Interview mode stopped';
        
        // Clean up audio context
        if (audioContext) {
            audioContext.close();
        }
    }
});

function parseLLMResponse(response) {
    const sections = {
        transcription: '',
        response: '',
        summary: ''
    };

    // Split the response into sections
    const transcriptionMatch = response.match(/\[TRANSCRIPTION\]([\s\S]*?)(?=\[RESPONSE\]|$)/);
    const responseMatch = response.match(/\[RESPONSE\]([\s\S]*?)(?=\[SUMMARY\]|$)/);
    const summaryMatch = response.match(/\[SUMMARY\]([\s\S]*?)$/);

    if (transcriptionMatch) {
        sections.transcription = transcriptionMatch[1].trim();
    }
    if (responseMatch) {
        sections.response = responseMatch[1].trim();
    }
    if (summaryMatch) {
        sections.summary = summaryMatch[1].trim();
    }

    return sections;
}

// Helper functions to add content to each column
function addTranscription(text) {
    const div = document.createElement('div');
    div.className = 'transcription-item';
    div.textContent = text;
    transcriptionContent.appendChild(div);
    transcriptionContent.scrollTop = transcriptionContent.scrollHeight;
}

function addResponse(text) {
    const div = document.createElement('div');
    div.className = 'response-item';
    div.innerHTML = text; // Using innerHTML to support formatting
    responseContent.appendChild(div);
    responseContent.scrollTop = responseContent.scrollHeight;
}

function addSummary(text) {
    const div = document.createElement('div');
    div.className = 'summary-item';
    div.innerHTML = text; // Using innerHTML to support formatting
    summaryContent.appendChild(div);
    summaryContent.scrollTop = summaryContent.scrollHeight;
} 