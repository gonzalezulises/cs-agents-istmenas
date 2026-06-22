from __future__ import annotations as _annotations

from copy import deepcopy

from .context import AirlineAgentContext

MOCK_ITINERARIES = {
    "disrupted": {
        "name": "David a Ciudad de Panamá a Cartagena",
        "passenger_name": "Ana Lucía Him",
        "confirmation_number": "IS-D204",
        "seat_number": "14C",
        "baggage_tag": "BG20488",
        "segments": [
            {
                "flight_number": "IS-441",
                "origin": "David (DAV)",
                "destination": "Ciudad de Panamá (PTY)",
                "departure": "2026-06-22 14:10",
                "arrival": "2026-06-22 15:25",
                "status": "Retrasado 5 horas por mal tiempo; salida estimada 19:55",
                "gate": "B18",
            },
            {
                "flight_number": "IS-802",
                "origin": "Ciudad de Panamá (PTY)",
                "destination": "Cartagena (CTG)",
                "departure": "2026-06-22 17:10",
                "arrival": "2026-06-22 18:35",
                "status": "Conexión perdida por el retraso del primer tramo",
                "gate": "C7",
            },
        ],
        "rebook_options": [
            {
                "flight_number": "IS-950",
                "origin": "Ciudad de Panamá (PTY)",
                "destination": "Cartagena (CTG)",
                "departure": "2026-06-23 09:45",
                "arrival": "2026-06-23 11:00",
                "seat": "2A (fila delantera)",
                "note": "Vuelo asegurado con reacomodo automático para pasajeros afectados",
            },
            {
                "flight_number": "IS-982",
                "origin": "Ciudad de Panamá (PTY)",
                "destination": "Cartagena (CTG)",
                "departure": "2026-06-23 13:20",
                "arrival": "2026-06-23 14:45",
                "seat": "3C",
                "note": "Opción de respaldo si el vuelo de la mañana se llena",
            },
        ],
        "vouchers": {
            "hotel": "Hotel por una noche cubierto hasta $180 cerca del Aeropuerto de Tocumen",
            "meal": "Crédito de $60 para comidas por el retraso",
            "ground": "Crédito de $40 para transporte terrestre al hotel",
        },
    },
    "on_time": {
        "name": "Vuelo doméstico puntual",
        "passenger_name": "Roberto Achurra",
        "confirmation_number": "LL0EZ6",
        "seat_number": "23A",
        "baggage_tag": "BG55678",
        "segments": [
            {
                "flight_number": "IS-123",
                "origin": "Ciudad de Panamá (PTY)",
                "destination": "David (DAV)",
                "departure": "2026-06-22 16:10",
                "arrival": "2026-06-22 17:25",
                "status": "A tiempo y operando según lo programado",
                "gate": "A10",
            }
        ],
        "rebook_options": [],
        "vouchers": {},
    },
}


def apply_itinerary_defaults(ctx: AirlineAgentContext, scenario_key: str | None = None) -> None:
    """Populate the context with a demo itinerary if missing."""
    target_key = scenario_key or ctx.scenario or "disrupted"
    data = MOCK_ITINERARIES.get(target_key) or next(iter(MOCK_ITINERARIES.values()))
    ctx.scenario = target_key
    ctx.passenger_name = ctx.passenger_name or data.get("passenger_name")
    ctx.confirmation_number = ctx.confirmation_number or data.get("confirmation_number")
    segments = data.get("segments", [])
    if ctx.flight_number is None and segments:
        ctx.flight_number = segments[0].get("flight_number")
    ctx.seat_number = ctx.seat_number or data.get("seat_number")
    if ctx.itinerary is None:
        ctx.itinerary = deepcopy(segments)
    # Set trip endpoints for display without exposing the full itinerary
    if segments:
        ctx.origin = ctx.origin or segments[0].get("origin")
        ctx.destination = ctx.destination or segments[-1].get("destination")


def get_itinerary_for_flight(flight_number: str | None) -> tuple[str, dict] | None:
    """Return (scenario_key, itinerary) if the flight is present in a mock itinerary."""
    if not flight_number:
        return None
    for key, itinerary in MOCK_ITINERARIES.items():
        for segment in itinerary.get("segments", []):
            if segment.get("flight_number", "").lower() == flight_number.lower():
                return key, itinerary
        for segment in itinerary.get("rebook_options", []):
            if segment.get("flight_number", "").lower() == flight_number.lower():
                return key, itinerary
    return None


def active_itinerary(ctx: AirlineAgentContext) -> tuple[str, dict]:
    """Resolve the active itinerary for the current context."""
    if ctx.scenario and ctx.scenario in MOCK_ITINERARIES:
        return ctx.scenario, MOCK_ITINERARIES[ctx.scenario]
    match = get_itinerary_for_flight(ctx.flight_number)
    if match:
        ctx.scenario = match[0]
        return match
    ctx.scenario = "disrupted"
    return ctx.scenario, MOCK_ITINERARIES["disrupted"]
