from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.models.ai_request import AIRequest
from app.models.user import User
from app.schemas.ai import AIHistoryResponse, AIRequestCreate, AIResponse
from app.services.ai_context import build_context
from app.services.ai_service import AI_MODEL, generate_ai_response

router = APIRouter(prefix="/ai", tags=["AI Race Assistant"])


@router.post("/explain", response_model=AIResponse)
def explain(
    body: AIRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Ask the AI Race Assistant a question.

    GridPulse context (standings, favourites, upcoming sessions, reminders)
    is gathered from the database and injected into the prompt automatically.
    The assistant will say when it does not have enough data to answer.
    """
    context = build_context(current_user, db)
    response_text, tokens_used = generate_ai_response(body.prompt, context)

    record = AIRequest(
        user_id=current_user.id,
        prompt=body.prompt,
        response=response_text,
        request_type=body.request_type,
        tokens_used=tokens_used or None,
        model_name=AI_MODEL,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return record


@router.get("/history", response_model=list[AIHistoryResponse])
def history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return the current user's AI Race Assistant question history, newest first.
    Limited to the 20 most recent requests.
    """
    return (
        db.query(AIRequest)
        .filter(AIRequest.user_id == current_user.id)
        .order_by(AIRequest.created_at.desc())
        .limit(20)
        .all()
    )
