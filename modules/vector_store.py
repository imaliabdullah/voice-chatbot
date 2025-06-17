import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import os
import pickle
import logging
import torch
from huggingface_hub import snapshot_download
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        """
        Initialize the vector store with a sentence transformer model and FAISS index.
        
        Args:
            model_name (str): Name of the sentence transformer model to use
            cache_dir (str): Directory to cache the model
        """
        self.model = self.load_model()
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatL2(self.dimension)
        self.texts = []
        logger.info(f"VectorStore initialized with dimension: {self.dimension}")
    
    def load_model(self, max_retries=3, retry_delay=5):
        """
        Load the model with retries and caching.
        
        Args:
            model_name (str): Name of the model to load
            max_retries (int): Maximum number of retry attempts
            retry_delay (int): Delay between retries in seconds
            
        Returns:
            SentenceTransformer: Loaded model
        """
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        logger.info("Model loaded successfully")
        return model
    
    def add_document(self, text, chunk_size=500, overlap=50):
        """
        Add a document to the vector store by chunking it and creating embeddings.
        
        Args:
            text (str): The text to add
            chunk_size (int): Size of text chunks
            overlap (int): Overlap between chunks
        """
        if not text.strip():
            logger.warning("Attempted to add empty document to vector store")
            return
            
        logger.info(f"Adding document to vector store (text length: {len(text)})")
        
        # Split text into chunks
        chunks = self._create_chunks(text, chunk_size, overlap)
        logger.info(f"Created {len(chunks)} chunks from document")
        
        if not chunks:
            logger.warning("No chunks created from document")
            return
            
        try:
            # Create embeddings for chunks
            logger.info("Creating embeddings for chunks")
            embeddings = self.model.encode(chunks, show_progress_bar=True)
            
            # Add to FAISS index
            logger.info(f"Adding {len(embeddings)} embeddings to FAISS index")
            self.index.add(np.array(embeddings).astype('float32'))
            
            # Store original text chunks
            self.texts.extend(chunks)
            logger.info(f"Total documents in vector store: {len(self.texts)}")
            
        except Exception as e:
            logger.error(f"Error adding document to vector store: {str(e)}")
            raise
    
    def search(self, query, k=3):
        """
        Search for similar text chunks to the query.
        
        Args:
            query (str): The search query
            k (int): Number of results to return
            
        Returns:
            str: Concatenated relevant text chunks
        """
        if not self.texts:
            logger.warning("Vector store is empty, cannot perform search")
            raise IndexError("Vector store is empty")
            
        logger.info(f"Searching vector store for query: {query}")
        
        try:
            # Create query embedding
            query_embedding = self.model.encode([query])
            
            # Search in FAISS index
            distances, indices = self.index.search(
                np.array(query_embedding).astype('float32'), k
            )
            
            # Get relevant text chunks
            relevant_chunks = [self.texts[i] for i in indices[0]]
            logger.info(f"Found {len(relevant_chunks)} relevant chunks")
            
            return ' '.join(relevant_chunks)
            
        except Exception as e:
            logger.error(f"Error searching vector store: {str(e)}")
            raise
    
    def _create_chunks(self, text, chunk_size, overlap):
        """
        Split text into overlapping chunks.
        
        Args:
            text (str): Text to split
            chunk_size (int): Size of each chunk
            overlap (int): Overlap between chunks
            
        Returns:
            list: List of text chunks
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if chunk.strip():  # Only add non-empty chunks
                chunks.append(chunk)
            start = end - overlap
            
        return chunks
    
    def save(self, path):
        """
        Save the vector store to disk.
        
        Args:
            path (str): Path to save the vector store
        """
        logger.info(f"Saving vector store to {path}")
        os.makedirs(path, exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.index, os.path.join(path, 'index.faiss'))
        
        # Save texts
        with open(os.path.join(path, 'texts.pkl'), 'wb') as f:
            pickle.dump(self.texts, f)
            
        logger.info("Vector store saved successfully")
    
    def load(self, path):
        """
        Load the vector store from disk.
        
        Args:
            path (str): Path to load the vector store from
        """
        logger.info(f"Loading vector store from {path}")
        
        # Load FAISS index
        self.index = faiss.read_index(os.path.join(path, 'index.faiss'))
        
        # Load texts
        with open(os.path.join(path, 'texts.pkl'), 'rb') as f:
            self.texts = pickle.load(f)
            
        logger.info(f"Vector store loaded successfully with {len(self.texts)} documents") 