from .knowledge import KnowledgeBase, extract_problem_ids
from .config import Settings
from .llm import LLMClient
from .prompts import build_user_prompt
from .security import has_critical_injection_signal
from .state import ConversationStateStore
from .text_utils import detect_taxonomy, extract_code_snippet, tokenize


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
            if self._looks_like_prompt_attack(question):
                answer = self.settings.bot_config.prompts.prompt_injection_message
                self.state_store.append_message(chat_id, "assistant", answer)
                return answer

            history_text = self.state_store.render_history(chat_id)
            retrieved_documents = self.knowledge_base.search(
                query=question,
                limit=self.settings.bot_config.retrieval.max_documents,
            )
            if self._needs_more_context(question, retrieved_documents):
                answer = self.settings.bot_config.prompts.insufficient_context_message
                self.state_store.append_message(chat_id, "assistant", answer)
                return answer

            prompt = build_user_prompt(
                question=question,
                conversation_history=history_text,
                final_memory=self.knowledge_base.final_memory,
                retrieved_documents=retrieved_documents,
                prompt_config=self.settings.bot_config.prompts,
                retrieval_config=self.settings.bot_config.retrieval,
            )
            answer = self.llm_client.generate(self.settings.bot_config.prompts.system, prompt)
        except Exception as error:
            answer = self._format_error_message(error)

        self.state_store.append_message(chat_id, "assistant", answer)
        return answer

    def reset_history(self, chat_id: int) -> None:
        self.state_store.reset_history(chat_id)

    def status_text(self) -> str:
        return (
            f"البوت: {self.settings.bot_config.metadata.name} v{self.settings.bot_config.metadata.version}\n"
            f"المزوّد: {self.settings.resolved_provider()}\n"
            f"النموذج: {self.settings.resolved_model()}\n"
            f"ملف الإعداد: {self.settings.bot_config_file.name}\n"
            f"ملف المصادر الخارجية: {self.settings.external_documents_file.name}\n"
            f"ملفات المعرفة: {self.settings.final_memory_file.name}, "
            f"{self.settings.chunk_summaries_file.name}\n"
            f"عدد الوثائق المحمّلة: {len(self.knowledge_base.documents)}\n"
            f"توزيع المصادر: {self._render_source_mix()}"
        )

    def _format_error_message(self, error: Exception) -> str:
        return self.settings.bot_config.prompts.error_message.format(error=error)

    def _needs_more_context(self, question: str, retrieved_documents: list) -> bool:
        normalized_question = question.strip()
        if not normalized_question:
            return True
        if extract_code_snippet(normalized_question):
            return False
        if extract_problem_ids(normalized_question):
            return False
        if detect_taxonomy(normalized_question):
            return False
        token_count = len(tokenize(normalized_question))
        if token_count < 3:
            return True
        return token_count < 5 and not retrieved_documents

    def _render_source_mix(self) -> str:
        counts = self.knowledge_base.document_counts_by_source()
        return ", ".join(f"{source}={count}" for source, count in counts.items()) or "n/a"

    def _looks_like_prompt_attack(self, question: str) -> bool:
        normalized_question = question.strip()
        if not normalized_question:
            return False
        if extract_code_snippet(normalized_question):
            return False
        return has_critical_injection_signal(normalized_question)
