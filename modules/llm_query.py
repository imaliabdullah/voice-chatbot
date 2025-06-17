import os
from groq import Groq
from dotenv import load_dotenv
from .prompts import get_context_prompt

# Load environment variables
load_dotenv()

# Initialize Groq client
client = Groq(api_key=os.getenv('GROQ_API_KEY'))

def query_llm(query, context):
    """
    Query the LLM with the user's question and relevant context.
    
    Args:
        query (str): The user's question
        context (str): Relevant context from the vector store
        
    Returns:
        str: LLM's response
    """
    try:
        # Get formatted prompt using Jinja template
        prompt = get_context_prompt(context, query)
        print(prompt)

        # Get response from Groq
        completion = client.chat.completions.create(
            model="deepseek-r1-distill-llama-70b",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides clear, well-structured answers based on the provided context."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1024
        )

        return completion.choices[0].message.content

    except Exception as e:
        print(f"Error querying LLM: {str(e)}")
        return "I apologize, but I encountered an error while processing your question." 