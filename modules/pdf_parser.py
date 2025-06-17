import fitz  # PyMuPDF
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_text_from_pdf(file_path):
    """
    Extract text from a PDF file using PyMuPDF.
    
    Args:
        file_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text from the PDF
    """
    try:
        logger.info(f"Opening PDF file: {file_path}")
        doc = fitz.open(file_path)
        text = ""
        
        for page_num, page in enumerate(doc):
            page_text = page.get_text()
            text += page_text
            logger.info(f"Extracted {len(page_text)} characters from page {page_num + 1}")
            
        doc.close()
        logger.info(f"Total extracted text length: {len(text)} characters")
        
        if not text.strip():
            logger.warning("No text was extracted from the PDF")
            return ""
            
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return "" 