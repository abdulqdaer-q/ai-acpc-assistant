from .config import Settings
from .knowledge import KnowledgeBase
from .llm import LLMClient
from .prompts import MASTER_PROMPT, build_user_prompt
from .state import ConversationStateStore


class MentorService:
    def __init__(
        self,
        settings: Settings,
        knowledge_base: KnowledgeBase,
        llm_client: LLMClient,
        state_store: ConversationStateStore,
    ) -> None:
        self.settings = settings
        self.knowledge_base = knowledge_base
        self.llm_client = llm_client
        self.state_store = state_store

    def answer_question(self, chat_id: int, question: str) -> str:
        self.state_store.append_message(chat_id, "user", question)

        try:
            history_text = self.state_store.render_history(chat_id)
            retrieved_chunks = self.knowledge_base.search(
                query=question,
                limit=self.settings.max_retrieved_chunks,
            )
            prompt = build_user_prompt(
                question=question,
                conversation_history=history_text,
                final_memory=self.knowledge_base.final_memory,
                retrieved_chunks=retrieved_chunks,
            )
            answer = self.llm_client.generate(MASTER_PROMPT, prompt)
        except Exception as error:
            answer = self._format_error_message(error)

        self.state_store.append_message(chat_id, "assistant", answer)
        return answer

    def reset_history(self, chat_id: int) -> None:
        self.state_store.reset_history(chat_id)

    def status_text(self) -> str:
        return (
            f"Provider: {self.settings.resolved_provider()}\n"
            f"Model: {self.settings.resolved_model()}\n"
            f"Knowledge files: {self.settings.final_memory_file.name}, "
            f"{self.settings.chunk_summaries_file.name}\n"
            f"Loaded chunks: {len(self.knowledge_base.chunks)}"
        )

    @staticmethod
    def _format_error_message(error: Exception) -> str:
        return (
            "I could not generate a mentor response right now.\n"
            f"Reason: {error}\n"
            "Check the selected LLM provider, credentials, and knowledge files."
        )
