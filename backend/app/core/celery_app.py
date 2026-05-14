from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.agents.agent_2_pdf_type",
        "app.agents.agent_3_ocr",
        "app.agents.agent_4_classifier",
        "app.agents.agent_5_table_extraction",
        "app.agents.agent_6_normalization",
        "app.agents.agent_7_analysis",
        "app.agents.agent_8_nlp_summary",
        "app.agents.agent_9_verdict",
        "app.agents.agent_10_visualization"
    ]
)

celery_app.conf.task_routes = {
    "app.agents.*": "main-queue"
}
