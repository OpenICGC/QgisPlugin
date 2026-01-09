from typing import Any, Iterator

from pydantic import BaseModel

from .result import GeoResult


class GeoResponse(BaseModel):
    """Modelo para una respuesta completa de geocodificación."""
    query: str
    results: list[GeoResult]
    count: int
    error: str | None = None
    time_ms: float | None = None

    @classmethod
    def from_results(cls, query: str, results: list[dict[str, Any]]) -> "GeoResponse":
        return cls(
            query=query,
            results=[GeoResult(**r) for r in results],
            count=len(results)
        )

    def __iter__(self) -> Iterator[GeoResult]:  # type: ignore[override]
        """Permite iterar directamente sobre los resultados."""
        return iter(self.results)
