import asyncio
import requests

from fastapi import APIRouter, HTTPException, Query

from services.economic_calendar_service import get_weekly_calendar

router = APIRouter()


@router.get("/economic-calendar/weekly")
async def weekly_economic_calendar(
    week: str = Query(
        default="current",
        pattern="^(current|next)$",
    ),
    force_refresh: bool = Query(default=False),
):
    try:
        return await asyncio.to_thread(
            get_weekly_calendar,
            week,
            force_refresh,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except requests.exceptions.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail="ارتباط با سایت ایران بروکر برقرار نشد.",
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"دریافت تقویم اقتصادی ناموفق بود: {str(exc)}",
        ) from exc
