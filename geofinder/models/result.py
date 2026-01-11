from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..exceptions import CoordinateError


class GeoResult(BaseModel):
    """Modelo para un resultado de geocodificación individual."""
    model_config = ConfigDict(populate_by_name=True)

    nom: str = Field(..., description="Nombre del lugar")
    id: str | None = Field(None, description="Identificador único del resultado")
    idTipus: int | None = Field(None, description="ID del tipo de lugar")
    nomTipus: str = Field("", description="Nombre del tipo de lugar")
    nomMunicipi: str = Field("", description="Nombre del municipio")
    nomComarca: str = Field("", description="Nombre de la comarca")

    # Códigos internos
    idMunicipi: str | None = Field(None, description="Código ID del municipio")
    idComarca: str | None = Field(None, description="Código ID de la comarca")
    layer: str | None = Field(None, description="Capa de origen (topo1, adreça, etc.)")

    # Coordenadas
    x: float = Field(..., description="Coordenada X (habitualmente longitud)")
    y: float = Field(..., description="Coordenada Y (habitualmente latitud)")
    epsg: int = Field(..., description="Código EPSG del sistema de coordenadas")

    # Metadatos para rectángulos (opcional)
    west: float | None = None
    north: float | None = None
    east: float | None = None
    south: float | None = None

    @field_validator('epsg')
    @classmethod
    def validate_epsg(cls, v: int) -> int:
        if v <= 0:
            raise CoordinateError(
                "El código EPSG debe ser un número positivo",
                details={"epsg": v}
            )
        return v

    @model_validator(mode='after')
    def validate_coordinate_ranges(self) -> 'GeoResult':
        """Valida que las coordenadas estén en rangos plausibles para WGS84."""
        if self.epsg == 4326:
            if not (-180 <= self.x <= 180):
                raise CoordinateError(
                    "Longitud fuera de rango (-180, 180)",
                    details={"x": self.x, "epsg": self.epsg}
                )
            if not (-90 <= self.y <= 90):
                raise CoordinateError(
                    "Latitud fuera de rango (-90, 90)",
                    details={"y": self.y, "epsg": self.epsg}
                )
        return self

    @field_validator('nomTipus', mode='before')
    @classmethod
    def validate_nom_tipus(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v)

    @classmethod
    def from_icgc_feature(cls, feature: dict[str, Any], epsg: int, default_type: str | None = None) -> "GeoResult":
        """Crea una instancia a partir de una feature GeoJSON del ICGC."""
        props: dict[str, Any] = feature.get("properties", {})
        addendum: dict[str, Any] = props.get("addendum", {})
        coords: list[float] = feature.get("geometry", {}).get("coordinates", [0.0, 0.0])

        # Extraer nombre
        nom = addendum.get("scn", {}).get("label") or props.get("etiqueta") or props.get("nom") or ""

        # Extraer tipo
        id_tipus = (
            addendum.get("id_tipus")
            or (1000 if props.get("tipus_via") else None)
            or (1001 if props.get("km") else None)
        )

        nom_tipus = (
            addendum.get("tipus")
            or props.get("tipus_via")
            or ("Punt quilomètric" if props.get("km") else None)
            or default_type
            or ""
        )

        return cls(
            nom=nom,
            id=props.get("id") or feature.get("id"),
            idTipus=id_tipus,
            nomTipus=nom_tipus,
            nomMunicipi=props.get("municipi", ""),
            nomComarca=props.get("comarca", ""),
            idMunicipi=props.get("id_municipi"),
            idComarca=props.get("id_comarca"),
            layer=props.get("layer"),
            x=coords[0],
            y=coords[1],
            epsg=epsg
        )

    def is_in_catalonia(self) -> bool:
        """Comprueba si el punto está dentro de los límites aproximados de Cataluña.

        Soporta WGS84 (4326) y UTM 31N (25831).
        """
        if self.epsg == 4326:
            # Lon [0.1, 3.4], Lat [40.5, 42.9]
            return 0.1 <= self.x <= 3.4 and 40.5 <= self.y <= 42.9
        elif self.epsg == 25831:
            # X [250000, 540000], Y [4480000, 4750000]
            return 250000 <= self.x <= 540000 and 4480000 <= self.y <= 4750000
        return True # Para otros EPSG no validamos por ahora

    def __getitem__(self, key: str) -> Any:
        """Soporte para acceso tipo diccionario (para compatibilidad)."""
        # 1. Campos definidos en el modelo Pydantic
        if key in self.__class__.model_fields:
            return getattr(self, key)
            
        # 2. Soporte para 'properties' si se añadió dinámicamente
        props = getattr(self, "properties", None)
        if props and isinstance(props, dict) and key in props:
            return props[key]
            
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        """Soporte para método get (para compatibilidad)."""
        props = getattr(self, "properties", None)
        if props and isinstance(props, dict) and key in props:
            return props.get(key, default)
        return getattr(self, key, default)
