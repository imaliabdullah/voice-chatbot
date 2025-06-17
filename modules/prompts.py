from jinja2 import Template

# Template for context-based responses
CONTEXT_PROMPT = Template("""
You are a helpful AI assistant that provides accurate and relevant information based on the given context.
Your task is to answer the user's question related provided context and if the information is avaiable in the context do some search and give answer according to the context not irrelevant.
If the context doesn't contain relevant information to answer the question, clearly state that.

Context:
{{ context }}

User Question: {{ query }}

Guidelines:
1. Base your answer ONLY on the provided context
2. If the context doesn't contain relevant information, say: "I don't have enough information in the provided context to answer this question."
3. Structure your response in THREE distinct sections:

   [TRANSCRIPTION]
   - Provide a clear transcription or restatement of the key information from the context
   - Focus on the most relevant parts that answer the question
   - Use clear, direct language

   [RESPONSE]
   - Give a detailed, well-structured answer to the question
   - Include specific examples or details from the context
   - Use bullet points or numbered lists when appropriate
   - Keep the response informative but concise

   [SUMMARY]
   - Provide 3-4 key points that summarize the main takeaways
   - Focus on the most important information
   - Use bullet points for clarity
   - Keep it brief and impactful

4. Format each section with the exact headers shown above: [TRANSCRIPTION], [RESPONSE], and [SUMMARY]
5. Do not make assumptions or add information not present in the context
6. Use clear and professional language throughout

Answer:
""")

def get_context_prompt(context: str, query: str) -> str:
    """
    Generate a prompt for context-based responses.
    
    Args:
        context (str): The relevant context from the vector store
        query (str): The user's question
        
    Returns:
        str: Formatted prompt for the LLM
    """
    return CONTEXT_PROMPT.render(context=context, query=query) 