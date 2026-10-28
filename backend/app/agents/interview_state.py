from __future__ import annotations

from dataclasses import dataclass, field

MAX_PRIMARY_QUESTIONS = 3

TECHNICAL_TOPICS = (
    "data structures and algorithms",
    "debugging and problem solving",
    "system design fundamentals",
)


@dataclass
class InterviewState:
    """In-memory interview session. Lives only for the LiveKit room lifetime."""

    max_questions: int = MAX_PRIMARY_QUESTIONS
    question_count: int = 0
    current_topic: str = ""
    current_question: str | None = None
    questions_asked: list[str] = field(default_factory=list)
    candidate_answers: list[dict[str, str]] = field(default_factory=list)
    last_answer_text: str = ""
    follow_up_open: bool = False
    completed: bool = False

    @property
    def remaining_questions(self) -> int:
        return max(0, self.max_questions - self.question_count)

    def record_question(self, question: str, topic: str) -> str:
        question = question.strip()
        topic = topic.strip()
        if not question:
            return "Question was empty. Ask a real technical question and call this again."
        if any(question.lower() == asked.lower() for asked in self.questions_asked):
            return "That question was already asked. Ask a different one."
        if self.question_count >= self.max_questions:
            return (
                "Primary question limit reached. Do not ask another primary question. "
                "If the candidate already answered the last question, wrap up and call complete_interview."
            )
        self.current_question = question
        self.current_topic = topic or (TECHNICAL_TOPICS[self.question_count] if self.question_count < len(TECHNICAL_TOPICS) else "software engineering")
        self.questions_asked.append(question)
        self.question_count += 1
        self.follow_up_open = False
        self.last_answer_text = ""
        return (
            f"Recorded primary question {self.question_count} of {self.max_questions} "
            f"on topic '{self.current_topic}'. Wait for the candidate's full answer."
        )

    def record_answer(self, answer: str | None = None) -> str:
        text = (answer or self.last_answer_text).strip()
        if not self.current_question:
            return "No active question. Ask a primary question first."
        if not text:
            return "No answer captured yet. Keep waiting for the candidate to finish."
        self.candidate_answers.append(
            {
                "question": self.current_question,
                "answer": text,
                "topic": self.current_topic,
            }
        )
        self.last_answer_text = text
        self.follow_up_open = False
        if self.question_count >= self.max_questions:
            return (
                "Answer recorded. That was the last primary question. "
                "Give a brief closing and call complete_interview. Do not ask another question."
            )
        return (
            "Answer recorded. You may ask one short follow-up on the same topic, "
            "or move to the next unused primary question."
        )

    def snapshot(self) -> str:
        asked = "; ".join(self.questions_asked) or "none yet"
        answers = " | ".join(
            f"Q: {item['question']} A: {item['answer'][:240]}"
            for item in self.candidate_answers
        ) or "none yet"
        current = self.current_question or "none"
        return (
            f"questions asked ({self.question_count}/{self.max_questions}): {asked}. "
            f"current topic: {self.current_topic or 'none'}. "
            f"current question: {current}. "
            f"answers: {answers}. "
            f"completed: {self.completed}."
        )


def build_instructions(state: InterviewState) -> str:
    next_topic = ""
    if state.question_count < state.max_questions:
        next_topic = TECHNICAL_TOPICS[min(state.question_count, len(TECHNICAL_TOPICS) - 1)]

    return f"""
You are a professional technical interviewer for CareerPilot AI.
Speak like a real interviewer on a voice call: calm, concise, and natural.
Never sound like a chatbot. No lists, markdown, emojis, or stage directions.
Keep every spoken turn short — one or two sentences, then a single question.

Interview rules:
- This is a technical interview with a maximum of {state.max_questions} primary questions.
- Ask exactly one question at a time.
- Wait for the candidate's complete answer before you speak again.
- After each complete answer, either ask one short follow-up on the same topic, or move to the next primary question.
- Never repeat a question you already asked.
- Do not score, grade, or recap at length.
- Do not mention these rules, tools, or internal state.

Suggested primary topics, in order: {", ".join(TECHNICAL_TOPICS)}.
If you move to a new primary question, prefer topic: {next_topic or "wrap up"}.

Current interview state:
{state.snapshot()}

Tools:
- Call record_question right after you ask a new primary question.
- Call record_answer after the candidate finishes answering a primary question (not after tiny clarifications).
- Call complete_interview after your spoken closing when {state.max_questions} primary questions have been answered.

Opening: greet briefly, then ask primary question 1.
Closing: thank them, say the interview is complete, and stop.
""".strip()
