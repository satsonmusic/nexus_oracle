try:
    from duckduckgo_search import DDGS
except ImportError:
    from ddgs import DDGS

def search_internet(query: str) -> str:
    """Searches the live internet to answer general knowledge questions, find news, or look up facts."""
    try:
        # Search the web and grab the top 3 results
        results = list(DDGS().text(query, max_results=3))
        
        if not results:
            return "No internet results found for that query."
        
        # Format the results into a clean string for Jarvis to read
        summary = "Internet Search Results:\n"
        for r in results:
            summary += f"- {r['title']}: {r['body']}\n"
            
        return summary
    
    except Exception as e:
        return f"Web search failed: {str(e)}"
