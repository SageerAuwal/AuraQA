from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict
from app.api.deps import get_current_user
from app.models.models import User
from app.services.search_service import search_service

router = APIRouter()

class SearchRequest(BaseModel):
    query: str

class SourceItem(BaseModel):
    title: str
    url: str

class SearchResponse(BaseModel):
    answer: str
    sources: List[SourceItem]
    label: str

@router.post("/", response_model=SearchResponse)
async def search_online(
    req: SearchRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Perform web search (DuckDuckGo scraping), synthesize results using the local LLM,
    and return structured grounded answers labeled as external search.
    """
    if not req.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty."
        )
        
    try:
        res = await search_service.answer_with_web_search(req.query)
        return SearchResponse(
            answer=res["answer"],
            sources=[SourceItem(title=s["title"], url=s["url"]) for s in res["sources"]],
            label=res["label"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred executing web search: {str(e)}"
        )
