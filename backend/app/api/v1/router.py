"""Aggregates all v1 routers under one APIRouter (mounted at /api/v1)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import (
    admin,
    auth,
    health,
    highlights,
    insights,
    leaderboards,
    looking_for,
    matches,
    messages,
    organizers,
    players,
    presets,
    rule_templates,
    search,
    social,
    teams,
    tournament_staff,
    tournaments,
    users,
    venues,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(organizers.router)
api_router.include_router(users.router)
api_router.include_router(search.router)
api_router.include_router(highlights.router)
api_router.include_router(health.router)
api_router.include_router(presets.router)
api_router.include_router(rule_templates.router)
api_router.include_router(players.router)
api_router.include_router(teams.router)
api_router.include_router(leaderboards.router)
api_router.include_router(insights.router)
api_router.include_router(tournaments.router)
api_router.include_router(tournament_staff.router)
api_router.include_router(matches.router)
api_router.include_router(social.router)
api_router.include_router(messages.router)
api_router.include_router(looking_for.router)
api_router.include_router(venues.router)
