import os
import google.auth
import vertexai
from deepeval.models import DeepEvalBaseLLM
from vertexai.generative_models import GenerativeModel


class VertexGemini(DeepEvalBaseLLM):
    """Custom DeepEval LLM integration for Google Vertex AI Gemini."""

    def __init__(self, model_name: str = "gemini-2.0-flash", *args, **kwargs) -> None:
        """Initialize the Vertex AI Gemini model."""
        super().__init__(*args, **kwargs)
        self.model_name = model_name
        self.location = os.getenv("VERTEX_LOCATION", "europe-west1")
        credentials, project_id = google.auth.default()
        vertexai.init(
            project=project_id, location=self.location, credentials=credentials
        )
        self.model = GenerativeModel(self.model_name)

    def load_model(self) -> DeepEvalBaseLLM:
        """Return the underlying GenerativeModel."""
        return self

    def generate(self, prompt: str) -> str:
        """Generate a synchronous text response."""
        return self.model.generate_content(prompt).text

    async def a_generate(self, prompt: str) -> str:
        """Generate an asynchronous text response."""
        return (await self.model.generate_content_async(prompt)).text

    def get_model_name(self) -> str:
        """Return the model identifier."""
        return self.model_name
