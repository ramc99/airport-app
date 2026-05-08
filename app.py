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
    """Chatbot API endpoint using Ollama LLM for answering user queries."""
    import httpx
    
    data = request.get_json() or {}
    message = (data.get("message") or "").strip()
    
    if not message:
        return {"response": "Please ask a question about flights, airports, airlines, schedules, delays, or routes."}
    
    # Get Ollama configuration from environment
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
    
    # System prompt to guide the LLM - now includes context about available data
    system_prompt = """You are a helpful airport assistant powered by AI. You help users with queries about flights, airports, airlines, schedules, delays, and routes.

When answering:
- Be concise and informative
- If you need specific codes (airport, airline, flight numbers), ask the user politely
- Use IATA codes (3 letters for airports, 2 letters for airlines) when possible
- For flight status, mention departure/arrival airports and current status
- For delays, mention the duration and affected flights
- For routes, list available airlines between airports

You have access to general aviation knowledge. If the user needs real-time data, guide them to use the search features on the website or provide general information based on your training data.
"""
    
    try:
        # Call Ollama API
        async def call_ollama():
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{ollama_host}/api/generate",
                    json={
                        "model": ollama_model,
                        "prompt": message,
                        "system": system_prompt,
                        "stream": False
                    }
                )
                response.raise_for_status()
                return response.json()
        
        # Run async code in sync context
        import asyncio
        result = asyncio.run(call_ollama())
        llm_response = result.get("response", "")
        
        return {"response": llm_response}
        
    except httpx.ConnectError:
        return {"response": "I'm unable to connect to the AI service right now. Please ensure Ollama is running locally (run 'ollama serve') and try again."}
    except Exception as e:
        app.logger.error(f"Ollama error: {e}")
        return {"response": f"Sorry, I encountered an error processing your request. Please make sure Ollama is running with a model loaded (e.g., 'ollama pull llama3.2' then 'ollama serve')."}


if __name__ == "__main__":
    app.run(debug=True, port=5000)
