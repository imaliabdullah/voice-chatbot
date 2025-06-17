import easyocr
import os

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'])

def extract_text_from_image(file_path):
    """
    Extract text from an image using EasyOCR.
    
    Args:
        file_path (str): Path to the image file
        
    Returns:
        str: Extracted text from the image
    """
    try:
        # Read text from image
        results = reader.readtext(file_path)
        
        # Combine all detected text
        text = ' '.join([result[1] for result in results])
        
        return text
    except Exception as e:
        print(f"Error extracting text from image: {str(e)}")
        return "" 