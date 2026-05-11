"""
Схемы графа влияний для интерактивной визуализации.

Формат специально подобран под react-force-graph-2d:
  nodes: список узлов
  links: список рёбер (source/target по id узла)

Это позволит на фронте делать:
    <ForceGraph2D
      graphData={data}
      nodeLabel="name"
      linkLabel={l => `${l.weight} (${l.confidence})`}
      ...
    />
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict


class GraphNode(BaseModel):
    """Узел графа — режиссёр."""

    id: int                          # entity_id персоны
    name: str                        # имя на запрошенном языке
    image: str | None = None         # фото
    group: Literal["director"] = "director"
    influences_count: int = 0        # сколько раз был источником
    influenced_by_count: int = 0     # сколько раз был целью
    is_center: bool = False          # центральный узел в /api/graph/director/{id}

    model_config = ConfigDict(from_attributes=True)


class GraphLink(BaseModel):
    """Ребро графа — связь A повлиял на B."""

    source: int                      # source_director_id (наш узел)
    target: int                      # target_director_id (наш узел)
    weight: int                      # 1-5
    confidence: float                # 0-1
    relation_note: str | None = None

    model_config = ConfigDict(from_attributes=True)


class GraphResponse(BaseModel):
    """Полный ответ — то что нужно react-force-graph."""

    nodes: list[GraphNode]
    links: list[GraphLink]
    center_id: int | None = None     # для /api/graph/director/{id} — id центра
    depth: int = 1                   # сколько шагов в глубину
