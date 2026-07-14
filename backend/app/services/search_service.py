import httpx
import re
from typing import List, Dict, Any
from app.services.llm_service import llm_service

class SearchService:
    async def search_web(self, query: str) -> Dict[str, Any]:
        """
        Query DuckDuckGo and return parsed search results (Title, URL, Snippet).
        If the network request fails, it falls back to empty list.
        """
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        params = {"q": query}
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params, headers=headers)
                if response.status_code != 200:
                    return {"results": [], "source": "fallback"}
                    
                html = response.text
                
                # Find all web-result blocks using boundary finditer
                matches = list(re.finditer(r'<div class="[^"]*web-result[^"]*">', html))
                
                results = []
                for idx, match in enumerate(matches[:4]): # Limit to top 4 results
                    start = match.start()
                    end = matches[idx+1].start() if idx + 1 < len(matches) else len(html)
                    block = html[start:end]
                    
                    # Extract URL (look for result__a href or result__url href)
                    url_match = re.search(r'href="([^"]*uddg=[^"]+)"', block)
                    if not url_match:
                        url_match = re.search(r'href="([^"]+)"', block)
                        
                    url_val = url_match.group(1) if url_match else ""
                    if url_val.startswith("//"):
                        url_val = "https:" + url_val
                        
                    # Unescape URL parameter if it's redirected
                    if "uddg=" in url_val:
                        m = re.search(r'uddg=([^&]+)', url_val)
                        if m:
                            import urllib.parse
                            url_val = urllib.parse.unquote(m.group(1))
                            
                    # Extract Title
                    title_match = re.search(r'class="result__a"[^>]*>(.*?)</a>', block, re.DOTALL)
                    title_val = title_match.group(1).strip() if title_match else ""
                    title_val = re.sub(r'<[^>]+>', '', title_val) # Strip HTML tags
                    
                    # Extract Snippet
                    snippet_match = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', block, re.DOTALL)
                    snippet_val = snippet_match.group(1).strip() if snippet_match else ""
                    snippet_val = re.sub(r'<[^>]+>', '', snippet_val)
                    
                    if url_val and snippet_val:
                        results.append({
                            "title": title_val or "Web Link",
                            "url": url_val,
                            "snippet": snippet_val
                        })
                        
                return {"results": results, "source": "duckduckgo"}
                
        except Exception:
            return {"results": [], "source": "fallback"}

    async def answer_with_web_search(self, query: str) -> Dict[str, Any]:
        """
        Runs the online search, feeds snippets into the local LLM context,
        and returns a structured web grounded answer.
        """
        search_data = await self.search_web(query)
        results = search_data["results"]
        
        if not results:
            # Fallback to general LLM knowledge if search failed or offline
            system_prompt = (
                "You are an AI assistant answering questions using your general knowledge because the online web search is currently offline.\n"
                "State clearly at the beginning of your answer: '[Answer generated using general knowledge (offline fallback)]'.\n"
                "Keep your answer concise and informative."
            )
            answer = await llm_service.generate_response(prompt=query, system_prompt=system_prompt)
            return {
                "answer": answer,
                "sources": [],
                "label": "General Knowledge (Search Offline)"
            }
            
        # Formulate grounded context
        context_blocks = []
        sources = []
        for i, res in enumerate(results):
            context_blocks.append(f"[Source {i+1}]: Title: {res['title']}\nSnippet: {res['snippet']}")
            sources.append({
                "title": res["title"],
                "url": res["url"]
            })
            
        context = "\n\n".join(context_blocks)
        
        system_prompt = (
            "You are a helpful AI assistant. Answer the user's question grounded in the provided Web Search Context.\n"
            "Provide a comprehensive, factual response. Link back to source indexes e.g. [1] or [2] where appropriate.\n"
            "Keep your answer concise and direct."
        )
        
        user_prompt = (
            f"Web Search Context:\n"
            f"{context}\n\n"
            f"Question: {query}\n"
            f"Answer:"
        )
        
        answer = await llm_service.generate_response(prompt=user_prompt, system_prompt=system_prompt)
        
        return {
            "answer": answer,
            "sources": sources,
            "label": "Online Web Search Results"
        }

# Global search service singleton
search_service = SearchService()
