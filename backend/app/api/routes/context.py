"""User health context API route.

Exposes the authenticated user's structured clinical context, strictly derived
from the verified session token. Never accepts an untrusted client-supplied user_id.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services.context_builder import (
    ContextBuilderDatabaseError,
    ContextBuilderError,
    build_user_health_context,
)

router = APIRouter(prefix="/health-context", tags=["User Health Context"])


@router.get("/me", status_code=status.HTTP_200_OK)
def get_my_health_context(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve the structured clinical context for the authenticated user.

    Strict security guarantees:
    - User identity is verified exclusively through the cryptographically signed session token.
    - Untrusted user_id parameters are rejected; cross-user querying is impossible.
    - Missing clinical domains and tests are reported honestly without fabrication.
    """
    try:
        context = build_user_health_context(db=db, user=current_user)
        return context.to_dict()
    except ContextBuilderDatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except ContextBuilderError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/me/summary", status_code=status.HTTP_200_OK)
def get_my_clinical_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve a de-identified, prompt-ready clinical markdown summary for the authenticated user."""
    try:
        context = build_user_health_context(db=db, user=current_user)
        return {
            "user_id": current_user.id,
            "generated_at": context.generated_at,
            "summary_markdown": context.to_clinical_prompt_text(),
            "missing_data_summary": context.missing_data_summary,
        }
    except ContextBuilderDatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

