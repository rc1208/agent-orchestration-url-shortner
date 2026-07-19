from abc import ABC, abstractmethod
import logging
from typing import Literal, TypeVar

from pydantic import BaseModel, Field

from .logging import log_event


class RequirementAnalysis(BaseModel):
    normalized_requirement: str
    ambiguity_score: float = Field(ge=0, le=1)
    assumptions: list[str]
    clarification_questions: list[str]


class ArchitectureProposal(BaseModel):
    components: list[str]
    decisions: list[str]


class RiskAnalysis(BaseModel):
    risks: list[str]
    controls: list[str]


class TaskItem(BaseModel):
    task_id: str
    title: str
    dependencies: list[str] = Field(default_factory=list)


class TaskPlan(BaseModel):
    tasks: list[TaskItem]


class Artifact(BaseModel):
    path: str
    content: str


class ImplementationProposal(BaseModel):
    summary: str
    artifacts: list[Artifact]


class ReviewResult(BaseModel):
    outcome: Literal["approved", "retry", "terminal"]
    rationale: str


class AgentProvider(ABC):
    name: str

    @abstractmethod
    def analyze_requirement(self, requirement: str, scenario: str) -> RequirementAnalysis: ...

    @abstractmethod
    def architecture(self, requirement: str) -> ArchitectureProposal: ...

    @abstractmethod
    def risks(self, requirement: str) -> RiskAnalysis: ...

    @abstractmethod
    def plan(self, requirement: str) -> TaskPlan: ...

    @abstractmethod
    def implement(self, requirement: str, scenario: str, attempt: int) -> ImplementationProposal: ...

    def review(self, passed: bool, attempt: int, max_retries: int) -> ReviewResult:
        if passed:
            return ReviewResult(outcome="approved", rationale="All deterministic gates passed")
        if attempt <= max_retries:
            return ReviewResult(outcome="retry", rationale="Validation failed within retry budget")
        return ReviewResult(outcome="terminal", rationale="Retry budget exhausted")


class MockProvider(AgentProvider):
    name = "mock"

    def analyze_requirement(self, requirement: str, scenario: str) -> RequirementAnalysis:
        ambiguous = scenario == "ambiguous" and "expir" not in requirement.lower()
        return RequirementAnalysis(
            normalized_requirement=requirement.strip(),
            ambiguity_score=0.9 if ambiguous else 0.15,
            assumptions=[] if ambiguous else ["HTTP API", "SQLite persistence", "Python 3.11+"],
            clarification_questions=["Which safety controls are required?"] if ambiguous else [],
        )

    def architecture(self, requirement: str) -> ArchitectureProposal:
        return ArchitectureProposal(
            components=["API boundary", "domain service", "SQLite repository", "audit log"],
            decisions=["Separate validated inputs from domain logic", "Use restart-safe persistence"],
        )

    def risks(self, requirement: str) -> RiskAnalysis:
        return RiskAnalysis(
            risks=["Unsafe redirect targets", "Alias collisions", "Unbounded generated changes"],
            controls=["URL validation", "Unique database constraint", "Sandbox and approval gate"],
        )

    def plan(self, requirement: str) -> TaskPlan:
        return TaskPlan(tasks=[
            TaskItem(task_id="T1", title="Implement domain behavior"),
            TaskItem(task_id="T2", title="Add validation", dependencies=["T1"]),
            TaskItem(task_id="T3", title="Add tests and documentation", dependencies=["T1", "T2"]),
        ])

    def implement(self, requirement: str, scenario: str, attempt: int) -> ImplementationProposal:
        safer = "safe" in requirement.lower() or "expir" in requirement.lower()
        solution = '''"""Generated, reviewable URL-shortener domain artifact."""\n\nimport hashlib\nimport re\n\n\ndef shorten(url: str, alias: str | None = None) -> str:\n    if not url.startswith(("http://", "https://")):\n        raise ValueError("Only HTTP(S) URLs are allowed")\n    if alias is not None:\n        if not re.fullmatch(r"[A-Za-z0-9_-]{3,32}", alias):\n            raise ValueError("Unsafe alias")\n        return alias\n    return hashlib.sha256(url.encode()).hexdigest()[:7]\n'''
        if safer:
            solution += '\n\ndef requires_expiration() -> bool:\n    return True\n'
        tests = '''from solution import shorten\n\ndef test_stable_shortening():\n    assert shorten("https://example.com") == shorten("https://example.com")\n\ndef test_custom_alias():\n    assert shorten("https://example.com", "demo-link") == "demo-link"\n'''
        if "[fail-tests]" in requirement:
            tests += "\n\ndef test_injected_failure():\n    assert False, 'deterministic failure injection'\n"
        return ImplementationProposal(
            summary=f"{scenario} implementation proposal (attempt {attempt})",
            artifacts=[Artifact(path="solution.py", content=solution), Artifact(path="test_solution.py", content=tests)],
        )


OutputT = TypeVar("OutputT", bound=BaseModel)


class OpenAIProvider(MockProvider):
    """Structured OpenAI provider; deterministic generation remains the offline fallback."""

    name = "openai"

    def __init__(self, model: str) -> None:
        from openai import OpenAI

        self.client = OpenAI()
        self.model = model

    def _structured(self, schema: type[OutputT], instruction: str) -> OutputT:
        response = self.client.responses.parse(
            model=self.model,
            input=[{"role": "system", "content": "Return a safe, concise engineering artifact."},
                   {"role": "user", "content": instruction[:12000]}],
            text_format=schema,
        )
        if response.output_parsed is None:
            raise ValueError("Model did not return the required structured output")
        return response.output_parsed

    def analyze_requirement(self, requirement: str, scenario: str) -> RequirementAnalysis:
        return self._structured(RequirementAnalysis, f"Analyze this {scenario} requirement: {requirement}")

    def architecture(self, requirement: str) -> ArchitectureProposal:
        return self._structured(ArchitectureProposal, f"Design an architecture for: {requirement}")

    def risks(self, requirement: str) -> RiskAnalysis:
        return self._structured(RiskAnalysis, f"Identify security and delivery risks for: {requirement}")

    def plan(self, requirement: str) -> TaskPlan:
        return self._structured(TaskPlan, f"Create a dependency-aware implementation plan for: {requirement}")

    def implement(self, requirement: str, scenario: str, attempt: int) -> ImplementationProposal:
        return self._structured(ImplementationProposal, f"Generate Python files for {scenario}: {requirement}")


class FallbackProvider(AgentProvider):
    """Use the primary provider, falling back deterministically on runtime failures."""

    name = "openai_with_mock_fallback"

    def __init__(self, primary: AgentProvider, fallback: AgentProvider | None = None) -> None:
        self.primary = primary
        self.fallback = fallback or MockProvider()
        self.logger = logging.getLogger("agentic_url_shortener.provider")

    def _call(self, method: str, *args):
        try:
            return getattr(self.primary, method)(*args)
        except Exception as error:
            log_event(self.logger, "provider_fallback", level=logging.WARNING,
                      details={"method": method, "provider": self.primary.name,
                               "error_type": type(error).__name__, "reason": str(error)})
            return getattr(self.fallback, method)(*args)

    def analyze_requirement(self, requirement: str, scenario: str) -> RequirementAnalysis:
        return self._call("analyze_requirement", requirement, scenario)

    def architecture(self, requirement: str) -> ArchitectureProposal:
        return self._call("architecture", requirement)

    def risks(self, requirement: str) -> RiskAnalysis:
        return self._call("risks", requirement)

    def plan(self, requirement: str) -> TaskPlan:
        return self._call("plan", requirement)

    def implement(self, requirement: str, scenario: str, attempt: int) -> ImplementationProposal:
        return self._call("implement", requirement, scenario, attempt)
