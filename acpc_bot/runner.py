from .app import AcpcMentorBotApp
from .config import Settings
from .knowledge import KnowledgeBase
from .llm import build_llm_client
from .mentor import MentorService
from .state import ConversationStateStore


def main() -> None:
    settings = Settings.from_env()
    settings.validate()

    knowledge_base = KnowledgeBase.load(settings)
    llm_client = build_llm_client(settings)
    state_store = ConversationStateStore(
        path=settings.state_file,
        max_history_messages=settings.max_history_messages,
    )
    mentor_service = MentorService(
        settings=settings,
        knowledge_base=knowledge_base,
        llm_client=llm_client,
        state_store=state_store,
    )
    app = AcpcMentorBotApp(settings=settings, mentor_service=mentor_service)
    app.run()
