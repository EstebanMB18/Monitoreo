from __future__ import annotations

import time
from typing import Any

import boto3


def crear_cliente(profile: str, region: str):
    return boto3.Session(profile_name=profile, region_name=region).client("logs")


def ejecutar_query(client, log_group: str, query: str, inicio, fin, limit: int = 10000) -> list[dict[str, Any]]:
    response = client.start_query(
        logGroupName=log_group,
        startTime=int(inicio.timestamp()),
        endTime=int(fin.timestamp()),
        queryString=query,
        limit=limit,
    )
    query_id = response["queryId"]
    while True:
        result = client.get_query_results(queryId=query_id)
        status = result["status"]
        if status == "Complete":
            return [
                {cell.get("field", ""): cell.get("value", "") for cell in row}
                for row in result.get("results", [])
            ]
        if status in {"Failed", "Cancelled", "Timeout", "Unknown"}:
            raise RuntimeError(f"Consulta fallida en {log_group}: {status}")
        time.sleep(1)


def contar(client, log_group: str, query: str, inicio, fin) -> int:
    rows = ejecutar_query(client, log_group, query, inicio, fin)
    if not rows:
        return 0
    for key in ("count", "total", "cantidad"):
        if key in rows[0]:
            try:
                return int(float(rows[0][key]))
            except (TypeError, ValueError):
                pass
    return len(rows)
