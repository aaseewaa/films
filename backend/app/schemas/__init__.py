"""Pydantic-схемы для API."""
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserMe,
)
from app.schemas.catalog import (
    FilmCard,
    FilmsResponse,
    GenreItem,
    PersonCard,
    PersonsResponse,
    PopularResponse,
)
from app.schemas.common import (
    ImageURLs,
    LanguageRead,
    PaginatedResponse,
    TaxonomyTermRead,
)
from app.schemas.entity import (
    FilmRead,
    FilmRef,
    InfluenceRef,
    PersonRead,
    PersonRef,
)
from app.schemas.graph import GraphLink, GraphNode, GraphResponse
from app.schemas.recommendations import (
    RecommendationItem,
    RecommendationsResponse,
)
from app.schemas.search import SearchHit, SearchResponse
from app.schemas.user_data import (
    EntityRatingStats,
    FavoriteAddRequest,
    FavoriteCheckResponse,
    FavoriteItem,
    FavoritesResponse,
    HistoryResponse,
    RateRequest,
    RatingItem,
    SearchHistoryItem,
    ViewHistoryItem,
)

__all__ = [
    "SearchHit", "SearchResponse",
    "FilmRead", "FilmRef", "PersonRead", "PersonRef", "InfluenceRef",
    "FilmCard", "FilmsResponse", "PersonCard", "PersonsResponse",
    "GenreItem", "PopularResponse",
    "RegisterRequest", "LoginRequest", "TokenResponse", "UserMe",
    "UpdateProfileRequest", "ChangePasswordRequest",
    "FavoriteAddRequest", "FavoriteItem", "FavoritesResponse", "FavoriteCheckResponse",
    "RateRequest", "RatingItem", "EntityRatingStats",
    "SearchHistoryItem", "ViewHistoryItem", "HistoryResponse",
    "GraphNode", "GraphLink", "GraphResponse",
    "RecommendationItem", "RecommendationsResponse",
    "ImageURLs", "LanguageRead", "PaginatedResponse", "TaxonomyTermRead",
]
