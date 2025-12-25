from typing import Optional
from pydantic import BaseModel
from .result import GeoResult

class GeoResponse(BaseModel):
    """Modelo para una respuesta completa de geocodificación."""
    query: str
    results: list[GeoResult]
    count: int
    error: Optional[str] = None
    time_ms: Optional[float] = None

    @classmethod
    def from_results(cls, query: str, results: list[dict]) -> "GeoResponse":
        return cls(
            query=query,
            results=[GeoResult(**r) for r in results],
            count=len(results)
        )

    def __iter__(self):
        """Permite iterar sobre los resultados directamente: for r in response: ..."""
        return iter(self.results)
