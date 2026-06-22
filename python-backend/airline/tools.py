from __future__ import annotations as _annotations

import random
import string
from copy import deepcopy

from agents import RunContextWrapper, function_tool
from chatkit.types import ProgressUpdateEvent

from .context import AirlineAgentChatContext
from .demo_data import active_itinerary, apply_itinerary_defaults, get_itinerary_for_flight


@function_tool(
    name_override="faq_lookup_tool", description_override="Lookup frequently asked questions."
)
async def faq_lookup_tool(question: str) -> str:
    """Lookup answers to frequently asked questions."""
    q = question.lower()
    if any(k in q for k in ["bag", "baggage", "equipaje", "maleta"]):
        return (
            "Puedes llevar una maleta a bordo. "
            "Debe pesar menos de 50 libras y medir 56 cm x 36 cm x 23 cm. "
            "Si una maleta se retrasa o se pierde, abre un reclamo de equipaje y la rastreamos para entregártela."
        )
    if any(k in q for k in ["compensation", "delay", "voucher", "compensación", "compensacion", "retraso", "demora", "indemniz"]):
        return (
            "Ante retrasos prolongados ofrecemos deber de asistencia: vales de hotel y comidas, más transporte terrestre cuando se necesite. "
            "Si el retraso supera las 3 horas o causa una conexión perdida, también abrimos un caso de compensación y podemos ofrecer millas o crédito de viaje. "
            "Un agente de Reembolsos y Compensación puede registrar el caso y compartirte los detalles de los vales."
        )
    elif any(k in q for k in ["seats", "plane", "asiento", "avión", "avion"]):
        return (
            "El avión tiene 120 asientos. "
            "Hay 22 asientos de clase ejecutiva y 98 de económica. "
            "Las filas de salida son la 4 y la 16. "
            "Las filas 5 a 8 son Economy Plus, con espacio extra para las piernas."
        )
    elif "wifi" in q:
        return "Tenemos wifi gratis a bordo; conéctate a la red Istmenas-Wifi."
    return "Lo siento, no tengo la respuesta a esa pregunta."


@function_tool(
    name_override="get_trip_details",
    description_override="Infer the disrupted David->Ciudad de Panamá->Cartagena trip from user text and hydrate context.",
)
async def get_trip_details(
    context: RunContextWrapper[AirlineAgentChatContext], message: str
) -> str:
    """
    If the user mentions David, Ciudad de Panamá/Panamá, or Cartagena, hydrate the context with the disrupted mock itinerary.
    Otherwise, hydrate the on-time mock itinerary. Returns the detected flight and confirmation.
    """
    text = message.lower()
    keywords = ["david", "panamá", "panama", "cartagena"]
    scenario_key = "disrupted" if any(k in text for k in keywords) else "on_time"
    apply_itinerary_defaults(context.context.state, scenario_key=scenario_key)
    ctx = context.context.state
    if scenario_key == "disrupted":
        ctx.origin = ctx.origin or "David (DAV)"
        ctx.destination = ctx.destination or "Cartagena (CTG)"
    segments = ctx.itinerary or []
    segment_summaries = []
    for seg in segments:
        segment_summaries.append(
            f"{seg.get('flight_number')} {seg.get('origin')} -> {seg.get('destination')} "
            f"status: {seg.get('status')}"
        )
    summary = "; ".join(segment_summaries) if segment_summaries else "No segment details available"
    return (
        f"Hydrated {scenario_key} itinerary: flight {ctx.flight_number}, confirmation "
        f"{ctx.confirmation_number}, origin {ctx.origin}, destination {ctx.destination}. {summary}"
    )


@function_tool
async def update_seat(
    context: RunContextWrapper[AirlineAgentChatContext], confirmation_number: str, new_seat: str
) -> str:
    """Update the seat for a given confirmation number."""
    apply_itinerary_defaults(context.context.state)
    context.context.state.confirmation_number = confirmation_number
    context.context.state.seat_number = new_seat
    assert context.context.state.flight_number is not None, "Flight number is required"
    return f"Asiento actualizado a {new_seat} para la confirmación {confirmation_number}"


@function_tool(
    name_override="flight_status_tool",
    description_override="Lookup status for a flight."
)
async def flight_status_tool(
    context: RunContextWrapper[AirlineAgentChatContext], flight_number: str
) -> str:
    """Lookup the status for a flight using mock itineraries."""
    await context.context.stream(ProgressUpdateEvent(text=f"Consultando el estado del vuelo {flight_number}..."))
    ctx_state = context.context.state
    ctx_state.flight_number = flight_number
    match = get_itinerary_for_flight(flight_number)
    if match:
        scenario_key, itinerary = match
        apply_itinerary_defaults(ctx_state, scenario_key=scenario_key)
        segments = itinerary.get("segments", [])
        rebook_options = itinerary.get("rebook_options", [])
        segment = next(
            (seg for seg in segments if seg.get("flight_number", "").lower() == flight_number.lower()),
            None,
        )
        if segment:
            route = f"{segment.get('origin', 'Desconocido')} a {segment.get('destination', 'Desconocido')}"
            details = [
                f"Vuelo {flight_number} ({route})",
                f"Estado: {segment.get('status', 'A tiempo')}",
            ]
            if segment.get("gate"):
                details.append(f"Puerta: {segment['gate']}")
            if segment.get("departure") and segment.get("arrival"):
                details.append(f"Programado {segment['departure']} -> {segment['arrival']}")
            if scenario_key == "disrupted" and segment.get("flight_number") == "IS-441":
                details.append("Este retraso causará la pérdida de la conexión IS-802. Se recomienda reacomodo.")
            await context.context.stream(
                ProgressUpdateEvent(text=f"Estado encontrado para el vuelo {flight_number}")
            )
            return " | ".join(details)
        replacement = next(
            (
                seg
                for seg in rebook_options
                if seg.get("flight_number", "").lower() == flight_number.lower()
            ),
            None,
        )
        if replacement:
            route = f"{replacement.get('origin', 'Desconocido')} a {replacement.get('destination', 'Desconocido')}"
            seat = replacement.get("seat", "por asignar")
            await context.context.stream(
                ProgressUpdateEvent(text=f"Vuelo alterno encontrado {flight_number}")
            )
            return (
                f"El vuelo de reemplazo {flight_number} ({route}) está disponible. "
                f"Sale {replacement.get('departure')} y llega {replacement.get('arrival')}. Asiento {seat} reservado."
            )
    await context.context.stream(ProgressUpdateEvent(text=f"Sin afectaciones para el vuelo {flight_number}"))
    return f"El vuelo {flight_number} está a tiempo y saldrá por la puerta A10."


@function_tool(
    name_override="baggage_tool",
    description_override="Lookup baggage allowance and fees."
)
async def baggage_tool(query: str) -> str:
    """Lookup baggage allowance and fees."""
    q = query.lower()
    if any(k in q for k in ["fee", "cargo", "costo", "tarifa"]):
        return "El cargo por exceso de equipaje es de $75."
    if any(k in q for k in ["allowance", "franquicia", "permitido", "incluye"]):
        return "Se incluye un equipaje de mano y una maleta facturada (hasta 50 libras)."
    if any(k in q for k in ["missing", "lost", "perdid", "extravi"]):
        return "Si una maleta no aparece, abre un reclamo de equipaje en el aeropuerto o con el agente de equipaje para rastrearla y entregártela."
    return "Por favor, dame más detalles sobre tu consulta de equipaje."


@function_tool(
    name_override="get_matching_flights",
    description_override="Find replacement flights when a segment is delayed or cancelled."
)
async def get_matching_flights(
    context: RunContextWrapper[AirlineAgentChatContext],
    origin: str | None = None,
    destination: str | None = None,
) -> str:
    """Return mock matching flights for a disrupted itinerary."""
    await context.context.stream(ProgressUpdateEvent(text="Buscando vuelos disponibles..."))
    ctx_state = context.context.state
    scenario_key, itinerary = active_itinerary(ctx_state)
    apply_itinerary_defaults(ctx_state, scenario_key=scenario_key)
    options = itinerary.get("rebook_options", [])
    if not options:
        await context.context.stream(ProgressUpdateEvent(text="No se necesitan alternas — viaje a tiempo"))
        return "Todos los vuelos operan a tiempo. No se necesitan vuelos alternos."
    filtered = [
        opt
        for opt in options
        if (origin is None or origin.lower() in opt.get("origin", "").lower())
        and (destination is None or destination.lower() in opt.get("destination", "").lower())
    ]
    final_options = filtered or options
    await context.context.stream(
        ProgressUpdateEvent(text=f"Se encontraron {len(final_options)} opción(es) de vuelo")
    )
    lines = []
    for opt in final_options:
        lines.append(
            f"{opt.get('flight_number')} {opt.get('origin')} -> {opt.get('destination')} "
            f"sale {opt.get('departure')} llega {opt.get('arrival')} | asiento {opt.get('seat', 'por asignar')} | {opt.get('note', '')}"
        )
    if scenario_key == "disrupted":
        lines.append("Estas opciones llegan a Cartagena al día siguiente. El hotel por la noche y las comidas están cubiertos.")
    ctx_state.itinerary = ctx_state.itinerary or deepcopy(itinerary.get("segments", []))
    return "Vuelos disponibles:\n" + "\n".join(lines)


@function_tool(
    name_override="book_new_flight",
    description_override="Book a new or replacement flight and auto-assign a seat."
)
async def book_new_flight(
    context: RunContextWrapper[AirlineAgentChatContext], flight_number: str | None = None
) -> str:
    """Book a replacement flight using mock inventory and update context."""
    await context.context.stream(ProgressUpdateEvent(text="Reservando vuelo de reemplazo..."))
    ctx_state = context.context.state
    scenario_key, itinerary = active_itinerary(ctx_state)
    apply_itinerary_defaults(ctx_state, scenario_key=scenario_key)
    options = itinerary.get("rebook_options", [])
    selection = None
    if flight_number:
        selection = next(
            (opt for opt in options if opt.get("flight_number", "").lower() == flight_number.lower()),
            None,
        )
    if selection is None and options:
        selection = options[0]
    if selection is None:
        seat = ctx_state.seat_number or "auto-assign"
        confirmation = ctx_state.confirmation_number or "".join(
            random.choices(string.ascii_uppercase + string.digits, k=6)
        )
        ctx_state.confirmation_number = confirmation
        await context.context.stream(ProgressUpdateEvent(text="Vuelo provisional reservado"))
        return (
            f"Vuelo {flight_number or 'por definir'} reservado con la confirmación {confirmation}. "
            f"Asiento asignado: {seat}."
        )
    ctx_state.flight_number = selection.get("flight_number")
    ctx_state.seat_number = selection.get("seat") or ctx_state.seat_number or "auto-assign"
    ctx_state.itinerary = ctx_state.itinerary or deepcopy(itinerary.get("segments", []))
    updated_itinerary = [
        seg
        for seg in ctx_state.itinerary
        if not (
            scenario_key == "disrupted"
            and seg.get("origin", "").startswith("Ciudad de Panamá")
            and seg.get("destination", "").startswith("Cartagena")
        )
    ]
    updated_itinerary.append(
        {
            "flight_number": selection["flight_number"],
            "origin": selection.get("origin", ""),
            "destination": selection.get("destination", ""),
            "departure": selection.get("departure", ""),
            "arrival": selection.get("arrival", ""),
            "status": "Confirmed replacement flight",
            "gate": "TBD",
        }
    )
    ctx_state.itinerary = updated_itinerary
    confirmation = ctx_state.confirmation_number or "".join(
        random.choices(string.ascii_uppercase + string.digits, k=6)
    )
    ctx_state.confirmation_number = confirmation
    await context.context.stream(
        ProgressUpdateEvent(
            text=f"Reacomodado al {selection['flight_number']} con asiento {ctx_state.seat_number}",
        )
    )
    return (
        f"Reacomodado al {selection['flight_number']} de {selection.get('origin')} a {selection.get('destination')}. "
        f"Sale {selection.get('departure')}, llega {selection.get('arrival')} (llegada al día siguiente a Cartagena). "
        f"Asiento asignado: {ctx_state.seat_number}. Confirmación {confirmation}."
    )


@function_tool(
    name_override="assign_special_service_seat",
    description_override="Assign front row or special service seating for medical needs."
)
async def assign_special_service_seat(
    context: RunContextWrapper[AirlineAgentChatContext], seat_request: str = "fila delantera por motivos médicos"
) -> str:
    """Assign a special service seat and record the request."""
    ctx_state = context.context.state
    apply_itinerary_defaults(ctx_state)
    req = seat_request.lower()
    preferred_seat = "1A" if ("front" in req or "delant" in req or "fila" in req) else "2A"
    ctx_state.seat_number = preferred_seat
    ctx_state.special_service_note = seat_request
    confirmation = ctx_state.confirmation_number or "".join(
        random.choices(string.ascii_uppercase + string.digits, k=6)
    )
    ctx_state.confirmation_number = confirmation
    return (
        f"Asegurado el asiento {preferred_seat} ({seat_request}) en el vuelo {ctx_state.flight_number or 'próximo tramo'}. "
        f"Confirmación {confirmation} marcada con servicio especial."
    )


@function_tool(
    name_override="issue_compensation",
    description_override="Create a compensation case and issue hotel/meal vouchers."
)
async def issue_compensation(
    context: RunContextWrapper[AirlineAgentChatContext], reason: str = "Retraso que causó una conexión perdida"
) -> str:
    """Open a compensation case and attach vouchers."""
    await context.context.stream(ProgressUpdateEvent(text="Abriendo caso de compensación..."))
    ctx_state = context.context.state
    scenario_key, itinerary = active_itinerary(ctx_state)
    apply_itinerary_defaults(ctx_state, scenario_key=scenario_key)
    case_id = ctx_state.compensation_case_id or f"CMP-{random.randint(1000, 9999)}"
    ctx_state.compensation_case_id = case_id
    voucher_values = list(itinerary.get("vouchers", {}).values())
    if voucher_values:
        ctx_state.vouchers = voucher_values
    else:
        ctx_state.vouchers = ctx_state.vouchers or []
    vouchers_text = "; ".join(ctx_state.vouchers) if ctx_state.vouchers else "Compensación documentada sin vales requeridos."
    await context.context.stream(ProgressUpdateEvent(text=f"Vales emitidos para el caso {case_id}"))
    return (
        f"Caso de compensación {case_id} abierto por: {reason}. "
        f"Emitido: {vouchers_text}. Guarda los recibos de hotel o comidas y adjúntalos a este caso."
    )


@function_tool(
    name_override="display_seat_map",
    description_override="Display an interactive seat map to the customer so they can choose a new seat."
)
async def display_seat_map(
    context: RunContextWrapper[AirlineAgentChatContext]
) -> str:
    """Trigger the UI to show an interactive seat map to the customer."""
    # The returned string will be interpreted by the UI to open the seat selector.
    return "DISPLAY_SEAT_MAP"


@function_tool(
    name_override="cancel_flight",
    description_override="Cancel a flight."
)
async def cancel_flight(
    context: RunContextWrapper[AirlineAgentChatContext]
) -> str:
    """Cancel the flight in the context."""
    apply_itinerary_defaults(context.context.state)
    fn = context.context.state.flight_number
    assert fn is not None, "Flight number is required"
    confirmation = context.context.state.confirmation_number or "".join(
        random.choices(string.ascii_uppercase + string.digits, k=6)
    )
    context.context.state.confirmation_number = confirmation
    return f"Vuelo {fn} cancelado correctamente para la confirmación {confirmation}"
