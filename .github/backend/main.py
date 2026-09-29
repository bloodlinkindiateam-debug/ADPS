from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import List
import sqlite3
import os
import math


# ============================================================
# ADPS BACKEND
# Airline Disruption & Recovery Planning System
# Prototype / Synthetic Data
# ============================================================

APP_NAME = "ADPS"
DB_PATH = os.getenv("ADPS_DB_PATH", "adps.db")

app = FastAPI(
    title="ADPS API",
    description="Airline Disruption & Recovery Planning System",
    version="1.0.0"
)


# ------------------------------------------------------------
# CORS
# ------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------
# DATABASE
# ------------------------------------------------------------

def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():

    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            airline_code TEXT NOT NULL,
            created_at TEXT NOT NULL,
            disrupted_flights REAL NOT NULL,
            delay_severity REAL NOT NULL,
            rebooking_factor REAL NOT NULL,
            recommended_strategy TEXT NOT NULL,
            composite_score REAL NOT NULL,
            estimated_cost REAL NOT NULL,
            protected_passengers REAL NOT NULL,
            delay_exposure_minutes REAL NOT NULL
        )
    """)

    connection.commit()
    connection.close()


init_database()


# ------------------------------------------------------------
# MODELS
# ------------------------------------------------------------

class ScenarioRequest(BaseModel):

    airline_code: str = Field(
        min_length=2,
        max_length=10
    )

    disrupted_flights: float = Field(
        ge=0,
        le=100000
    )

    delay_severity: float = Field(
        ge=0,
        le=100
    )

    rebooking_factor: float = Field(
        ge=0,
        le=100
    )


class ScenarioResponse(BaseModel):

    success: bool
    prototype_notice: str
    airline_code: str
    scenario: dict


# ------------------------------------------------------------
# HEALTH
# ------------------------------------------------------------

@app.get("/")
def root():

    return {
        "success": True,
        "system": APP_NAME,
        "version": "1.0.0",
        "status": "online",
        "prototype": True
    }


@app.get("/health")
def health():

    return {
        "success": True,
        "status": "healthy",
        "system": APP_NAME
    }


# ------------------------------------------------------------
# STRATEGY ENGINE
# ------------------------------------------------------------

def calculate_strategy(
    disrupted_flights: float,
    delay_severity: float,
    rebooking_factor: float
):

    pressure = (
        disrupted_flights * 0.35
        + delay_severity * 10
        + rebooking_factor * 8
    )

    if pressure < 100:
        strategy = "Standard Rebooking"

    elif pressure < 220:
        strategy = "Priority Rebooking"

    elif pressure < 400:
        strategy = "Multi-Flight Recovery"

    else:
        strategy = "Major Disruption Recovery"


    # Synthetic illustrative calculations

    protected_passengers = (
        disrupted_flights
        * 120
        * min(1.0, 0.75 + rebooking_factor * 0.05)
    )

    delay_exposure_minutes = (
        disrupted_flights
        * delay_severity
        * 35
    )

    estimated_cost = (
        disrupted_flights * 850
        + delay_exposure_minutes * 2.5
        + protected_passengers * 1.5
    )

    raw_score = (
        100
        - delay_severity * 8
        - rebooking_factor * 5
        - disrupted_flights * 0.5
    )

    composite_score = max(
        0,
        min(100, raw_score)
    )

    return {
        "recommended_strategy": strategy,
        "composite_score": round(
            composite_score,
            2
        ),
        "estimated_cost": round(
            estimated_cost,
            2
        ),
        "protected_passengers": round(
            protected_passengers,
            2
        ),
        "delay_exposure_minutes": round(
            delay_exposure_minutes,
            2
        )
    }


# ------------------------------------------------------------
# CREATE SCENARIO
# ------------------------------------------------------------

@app.post(
    "/api/scenarios/run",
    response_model=ScenarioResponse
)
def run_scenario(request: ScenarioRequest):

    airline = request.airline_code.strip().upper()

    if not airline:
        raise HTTPException(
            status_code=400,
            detail="Airline code is required."
        )

    result = calculate_strategy(
        request.disrupted_flights,
        request.delay_severity,
        request.rebooking_factor
    )

    created_at = datetime.now(
        timezone.utc
    ).isoformat()

    connection = get_connection()

    cursor = connection.execute("""
        INSERT INTO scenarios (
            airline_code,
            created_at,
            disrupted_flights,
            delay_severity,
            rebooking_factor,
            recommended_strategy,
            composite_score,
            estimated_cost,
            protected_passengers,
            delay_exposure_minutes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        airline,
        created_at,
        request.disrupted_flights,
        request.delay_severity,
        request.rebooking_factor,
        result["recommended_strategy"],
        result["composite_score"],
        result["estimated_cost"],
        result["protected_passengers"],
        result["delay_exposure_minutes"]
    ))

    connection.commit()

    scenario_id = cursor.lastrowid

    connection.close()

    scenario = {
        "id": scenario_id,
        "created_at": created_at,
        "disrupted_flights": request.disrupted_flights,
        "delay_severity": request.delay_severity,
        "rebooking_factor": request.rebooking_factor,
        **result
    }

    return {
        "success": True,
        "prototype_notice":
            "Synthetic illustrative scenario only",
        "airline_code": airline,
        "scenario": scenario
    }


# ------------------------------------------------------------
# HISTORY
# ------------------------------------------------------------

@app.get("/api/scenarios/history")
def scenario_history(
    airline_code: str
):

    airline = airline_code.strip().upper()

    connection = get_connection()

    rows = connection.execute("""
        SELECT *
        FROM scenarios
        WHERE airline_code = ?
        ORDER BY id DESC
    """, (airline,)).fetchall()

    connection.close()

    scenarios = [
        dict(row)
        for row in rows
    ]

    return {
        "success": True,
        "airline_code": airline,
        "scenarios": scenarios,
        "prototype_notice":
            "Historical values are synthetic and illustrative."
    }


# ------------------------------------------------------------
# ANALYTICS
# ------------------------------------------------------------

@app.get("/api/scenarios/analytics")
def scenario_analytics(
    airline_code: str
):

    airline = airline_code.strip().upper()

    connection = get_connection()

    rows = connection.execute("""
        SELECT *
        FROM scenarios
        WHERE airline_code = ?
        ORDER BY id DESC
    """, (airline,)).fetchall()

    connection.close()

    scenarios = [
        dict(row)
        for row in rows
    ]

    total = len(scenarios)

    if total == 0:

        return {
            "success": True,
            "airline_code": airline,
            "total_scenarios": 0,
            "total_disrupted_flights": 0,
            "total_protected_passengers": 0,
            "total_estimated_cost": 0,
            "total_delay_exposure_minutes": 0,
            "average_composite_score": 0,
            "strategy_distribution": {}
        }


    total_flights = sum(
        float(x["disrupted_flights"])
        for x in scenarios
    )

    protected = sum(
        float(x["protected_passengers"])
        for x in scenarios
    )

    cost = sum(
        float(x["estimated_cost"])
        for x in scenarios
    )

    exposure = sum(
        float(x["delay_exposure_minutes"])
        for x in scenarios
    )

    scores = [
        float(x["composite_score"])
        for x in scenarios
    ]

    distribution = {}

    for x in scenarios:

        strategy = x[
            "recommended_strategy"
        ]

        distribution[strategy] = (
            distribution.get(strategy, 0) + 1
        )


    return {
        "success": True,
        "airline_code": airline,
        "total_scenarios": total,
        "total_disrupted_flights":
            round(total_flights, 2),
        "total_protected_passengers":
            round(protected, 2),
        "total_estimated_cost":
            round(cost, 2),
        "total_delay_exposure_minutes":
            round(exposure, 2),
        "average_composite_score":
            round(
                sum(scores) / len(scores),
                2
            ),
        "strategy_distribution":
            distribution,
        "prototype_notice":
            "Analytics are based on synthetic illustrative scenarios."
    }
