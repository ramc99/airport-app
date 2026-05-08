"""airport-app — Flask routes for live airport / flight queries."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, url_for

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

import airlabs  # noqa: E402  (import after dotenv so module reads env at call time)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-only")


def _err(message: str, status: int = 400):
    return render_template("error.html", message=message), status


@app.errorhandler(airlabs.AirLabsError)
def _handle_airlabs(e: airlabs.AirLabsError):
    return _err(f"AirLabs: {e}", status=502)


# ---------- pages ----------


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/healthz")
def healthz():
    return {"status": "ok", "ts": datetime.utcnow().isoformat() + "Z"}


@app.route("/search")
def search():
    """Universal search bar: figure out what they typed and route to the right page."""
    q = (request.args.get("q") or "").strip().upper()
    if not q:
        return redirect(url_for("home"))

    # Heuristic: airline/flight codes have digits, airports don't.
    has_digits = any(c.isdigit() for c in q)
    if has_digits:
        return redirect(url_for("flight_view", code=q))
    if len(q) == 3:
        return redirect(url_for("airport_view", code=q))
    if len(q) == 2:
        return redirect(url_for("airline_view", code=q))
    # 4 letters could be ICAO airport
    if len(q) == 4:
        return redirect(url_for("airport_view", code=q))
    return _err(f"Couldn't interpret '{q}'. Try an IATA airport code (3 letters), airline code (2 letters), or flight number (e.g. BA178).")


# ---------- flight ----------


@app.route("/flight")
def flight_view():
    code = (request.args.get("code") or "").strip().upper()
    if not code:
        return render_template("flight.html", flight=None, code=None)
    is_icao = len(code) >= 4 and not any(c.isdigit() for c in code[:3])
    if is_icao:
        f = airlabs.flight(flight_icao=code)
    else:
        f = airlabs.flight(flight_iata=code)
    return render_template("flight.html", flight=f, code=code)


# ---------- airport ----------


@app.route("/airport/<code>")
def airport_view(code: str):
    code = code.strip().upper()
    if len(code) == 4:
        info = airlabs.airport(icao=code)
    else:
        info = airlabs.airport(iata=code)
    if not info:
        return _err(f"No airport found for code '{code}'", status=404)

    iata = info.get("iata_code") or (code if len(code) == 3 else None)
    deps = airlabs.schedules(dep_iata=iata, limit=15) if iata else []
    arrs = airlabs.schedules(arr_iata=iata, limit=15) if iata else []
    delayed = airlabs.delays(dep_iata=iata, min_delay_min=30, limit=10) if iata else []

    return render_template(
        "airport.html",
        airport=info,
        iata=iata,
        departures=deps,
        arrivals=arrs,
        delays=delayed,
    )


# ---------- airline ----------


@app.route("/airline/<code>")
def airline_view(code: str):
    code = code.strip().upper()
    if len(code) == 3:
        info = airlabs.airline(icao=code)
    else:
        info = airlabs.airline(iata=code)
    if not info:
        return _err(f"No airline found for code '{code}'", status=404)
    iata = info.get("iata_code") or (code if len(code) == 2 else None)
    flights = airlabs.live_flights(airline_iata=iata, limit=20) if iata else []
    return render_template("airline.html", airline=info, iata=iata, flights=flights)


# ---------- schedules ----------


@app.route("/schedules")
def schedules_view():
    dep = (request.args.get("dep") or "").strip().upper() or None
    arr = (request.args.get("arr") or "").strip().upper() or None
    airline_code = (request.args.get("airline") or "").strip().upper() or None
    rows: list[dict] = []
    if dep or arr or airline_code:
        rows = airlabs.schedules(
            dep_iata=dep,
            arr_iata=arr,
            airline_iata=airline_code,
            limit=50,
        )
    return render_template(
        "schedules.html",
        rows=rows,
        dep=dep or "",
        arr=arr or "",
        airline=airline_code or "",
        searched=any([dep, arr, airline_code]),
    )


# ---------- routes ----------


@app.route("/routes")
def routes_view():
    dep = (request.args.get("dep") or "").strip().upper() or None
    arr = (request.args.get("arr") or "").strip().upper() or None
    airline_code = (request.args.get("airline") or "").strip().upper() or None
    rows: list[dict] = []
    if dep or arr or airline_code:
        rows = airlabs.routes(
            dep_iata=dep,
            arr_iata=arr,
            airline_iata=airline_code,
            limit=50,
        )
    return render_template(
        "routes.html",
        rows=rows,
        dep=dep or "",
        arr=arr or "",
        airline=airline_code or "",
        searched=any([dep, arr, airline_code]),
    )


# ---------- delays ----------


@app.route("/delays")
def delays_view():
    dep = (request.args.get("dep") or "").strip().upper() or None
    arr = (request.args.get("arr") or "").strip().upper() or None
    delay_min = request.args.get("min", "30")
    try:
        delay_min_int = int(delay_min)
    except ValueError:
        delay_min_int = 30
    type_ = request.args.get("type", "departures")
    if type_ not in ("departures", "arrivals"):
        type_ = "departures"

    rows: list[dict] = []
    if dep or arr:
        rows = airlabs.delays(
            dep_iata=dep,
            arr_iata=arr,
            min_delay_min=delay_min_int,
            type=type_,
            limit=50,
        )
    return render_template(
        "delays.html",
        rows=rows,
        dep=dep or "",
        arr=arr or "",
        min_delay=delay_min_int,
        type=type_,
        searched=bool(dep or arr),
    )


# ---------- nearby ----------


@app.route("/nearby")
def nearby_view():
    lat = request.args.get("lat")
    lng = request.args.get("lng")
    dist = request.args.get("distance", "100")
    result = None
    if lat and lng:
        try:
            result = airlabs.nearby(
                lat=float(lat),
                lng=float(lng),
                distance_km=int(dist) if dist.isdigit() else 100,
            )
        except (ValueError, TypeError):
            return _err("Invalid coordinates")
    return render_template(
        "nearby.html",
        result=result,
        lat=lat or "",
        lng=lng or "",
        distance=dist,
    )


# ---------- chatbot API ----------


@app.route("/api/chat", methods=["POST"])
def chat_api():
    """Chatbot API endpoint for answering user queries."""
    import re

    data = request.get_json() or {}
    message = (data.get("message") or "").strip()

    if not message:
        return {"response": "Please ask a question about flights, airports, airlines, schedules, delays, or routes."}

    msg_lower = message.lower()

    # Helper to extract codes (3-letter airport, 2-letter airline, flight numbers)
    def extract_airport_code(text):
        # Look for 3-letter uppercase codes or common airport names
        match = re.search(r'\b([A-Z]{3})\b', text)
        if match:
            return match.group(1)
        # Check for known airport names
        airport_names = {
            'jfk': 'JFK', 'lhr': 'LHR', 'cdg': 'CDG', 'hnd': 'HND', 'dxb': 'DXB',
            'sin': 'SIN', 'lax': 'LAX', 'fra': 'FRA', 'ord': 'ORD', 'dfw': 'DFW',
            'den': 'DEN', 'sfo': 'SFO', 'sea': 'SEA', 'las': 'LAS', 'mco': 'MCO',
            'mia': 'MIA', 'bos': 'BOS', 'ewr': 'EWR', 'phx': 'PHX', 'iah': 'IAH',
        }
        for name, code in airport_names.items():
            if name in text_lower:
                return code
        return None

    def extract_airline_code(text):
        match = re.search(r'\b([A-Z]{2})\b', text)
        if match:
            return match.group(1)
        return None

    def extract_flight_number(text):
        # Match patterns like BA178, AA100, etc.
        match = re.search(r'\b([A-Z]{2}\d{1,4})\b', text.upper())
        if match:
            return match.group(1)
        return None

    # Determine intent
    if any(word in msg_lower for word in ['flight', 'flights', 'status']):
        flight_code = extract_flight_number(message)
        if flight_code:
            try:
                flight = airlabs.flight(flight_iata=flight_code)
                if flight:
                    status = flight.get('status', 'unknown')
                    dep = flight.get('dep_iata', 'N/A')
                    arr = flight.get('arr_iata', 'N/A')
                    alt = flight.get('alt', 'N/A')
                    speed = flight.get('speed', 'N/A')
                    return {
                        "response": f"Flight {flight_code}: Status is {status}. From {dep} to {arr}. Altitude: {alt}, Speed: {speed}."
                    }
                else:
                    return {"response": f"No live data found for flight {flight_code}."}
            except Exception:
                return {"response": f"Could not retrieve flight information for {flight_code}."}
        else:
            return {"response": "Please specify a flight number (e.g., BA178, AA100)."}

    elif any(word in msg_lower for word in ['airport', 'airports']):
        airport_code = extract_airport_code(message)
        if airport_code:
            try:
                airport = airlabs.airport(iata=airport_code)
                if airport:
                    name = airport.get('name', 'Unknown')
                    city = airport.get('city', 'Unknown')
                    country = airport.get('country', 'Unknown')
                    return {
                        "response": f"{airport_code} - {name}, located in {city}, {country}."
                    }
                else:
                    return {"response": f"No airport found with code {airport_code}."}
            except Exception:
                return {"response": f"Could not retrieve airport information for {airport_code}."}
        else:
            return {"response": "Please specify an airport code (e.g., JFK, LHR) or airport name."}

    elif any(word in msg_lower for word in ['airline', 'airlines']):
        airline_code = extract_airline_code(message)
        if airline_code:
            try:
                airline = airlabs.airline(iata=airline_code)
                if airline:
                    name = airline.get('name', 'Unknown')
                    country = airline.get('country', 'Unknown')
                    return {
                        "response": f"{airline_code} - {name}, based in {country}."
                    }
                else:
                    return {"response": f"No airline found with code {airline_code}."}
            except Exception:
                return {"response": f"Could not retrieve airline information for {airline_code}."}
        else:
            return {"response": "Please specify an airline code (e.g., BA, AA, DL)."}

    elif any(word in msg_lower for word in ['delay', 'delays', 'delayed']):
        airport_code = extract_airport_code(message)
        if airport_code:
            try:
                delays = airlabs.delays(dep_iata=airport_code, min_delay_min=30, limit=5)
                if delays and len(delays) > 0:
                    delay_list = [f"{d.get('flight_iata', 'N/A')} ({d.get('delayed', 0)} min)" for d in delays[:3]]
                    return {
                        "response": f"Current delays at {airport_code}: {', '.join(delay_list)}."
                    }
                else:
                    return {"response": f"No significant delays reported at {airport_code}."}
            except Exception:
                return {"response": f"Could not retrieve delay information for {airport_code}."}
        else:
            return {"response": "Please specify an airport code to check for delays."}

    elif any(word in msg_lower for word in ['schedule', 'schedules']):
        dep = extract_airport_code(message)
        arr_match = re.search(r'(?:to|→)\s*([A-Z]{3})', message.upper())
        arr = arr_match.group(1) if arr_match else None
        
        if dep or arr:
            try:
                schedules = airlabs.schedules(dep_iata=dep, arr_iata=arr, limit=5)
                if schedules and len(schedules) > 0:
                    schedule_info = [f"{s.get('flight_iata', 'N/A')} to {s.get('arr_iata', 'N/A')}" for s in schedules[:3]]
                    return {
                        "response": f"Upcoming flights: {', '.join(schedule_info)}."
                    }
                else:
                    return {"response": "No scheduled flights found matching your criteria."}
            except Exception:
                return {"response": "Could not retrieve schedule information."}
        else:
            return {"response": "Please specify a departure or arrival airport code."}

    elif any(word in msg_lower for word in ['route', 'routes']):
        dep = extract_airport_code(message)
        arr_match = re.search(r'(?:to|→)\s*([A-Z]{3})', message.upper())
        arr = arr_match.group(1) if arr_match else None
        
        if dep and arr:
            try:
                routes = airlabs.routes(dep_iata=dep, arr_iata=arr, limit=5)
                if routes and len(routes) > 0:
                    airlines = set(r.get('airline_iata', 'N/A') for r in routes)
                    return {
                        "response": f"Airlines flying from {dep} to {arr}: {', '.join(airlines)}."
                    }
                else:
                    return {"response": f"No direct routes found from {dep} to {arr}."}
            except Exception:
                return {"response": "Could not retrieve route information."}
        else:
            return {"response": "Please specify both departure and arrival airport codes (e.g., 'routes from JFK to LHR')."}

    elif any(word in msg_lower for word in ['hello', 'hi', 'hey', 'help']):
        return {
            "response": "Hello! I can help you with flight information, airport details, airline info, schedules, delays, and routes. Try asking: 'What's the status of BA178?' or 'Show me delays at JFK'."
        }

    else:
        return {
            "response": "I'm here to help with airport and flight information. You can ask about flights, airports, airlines, schedules, delays, or routes. For example: 'What flights are at JFK?' or 'Show me delays at LHR'."
        }


if __name__ == "__main__":
    app.run(debug=True, port=5000)
