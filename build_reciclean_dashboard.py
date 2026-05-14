from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "dashboard_reciclean_registros_mes_actual.html"

MONTHS_ES = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}

SHORT_MONTHS_ES = {
    1: "ene",
    2: "feb",
    3: "mar",
    4: "abr",
    5: "may",
    6: "jun",
    7: "jul",
    8: "ago",
    9: "sep",
    10: "oct",
    11: "nov",
    12: "dic",
}


def resolve_input_file() -> Path:
    pattern = re.compile(r"vales_detallada_(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})\.xlsx$")
    candidates = list(BASE_DIR.glob("vales_detallada_*.xlsx"))
    if not candidates:
        raise FileNotFoundError("No encontré archivos vales_detallada_*.xlsx en la carpeta actual.")

    def candidate_key(path: Path) -> tuple[datetime, float]:
        match = pattern.match(path.name)
        if match:
            stamp = datetime.strptime(f"{match.group(1)} {match.group(2)}", "%Y-%m-%d %H-%M-%S")
            return stamp, path.stat().st_mtime
        return datetime.min, path.stat().st_mtime

    return sorted(candidates, key=candidate_key, reverse=True)[0]


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return "Sin dato"
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return "Sin dato"
    return text


def normalize_title(value: object) -> str:
    text = normalize_text(value)
    return text if text == "Sin dato" else text.title()


def parse_amount(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


def parse_weight(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def month_label(period: pd.Period) -> str:
    return f"{MONTHS_ES[period.month].capitalize()} {period.year}"


def period_window_label(periods: list[pd.Period]) -> str:
    if not periods:
        return "Sin período"
    if len(periods) == 1:
        return month_label(periods[0])
    if len(periods) > 2:
        first_period = periods[0]
        last_period = periods[-1]
        if first_period.year == last_period.year:
            return f"{MONTHS_ES[first_period.month].capitalize()} a {MONTHS_ES[last_period.month]} {last_period.year}"
        return f"{month_label(first_period)} - {month_label(last_period)}"

    first_period = periods[0]
    last_period = periods[-1]
    if first_period.year == last_period.year:
        return f"{MONTHS_ES[first_period.month].capitalize()} y {MONTHS_ES[last_period.month]} {last_period.year}"
    return f"{month_label(first_period)} - {month_label(last_period)}"


def period_key(period: pd.Period) -> str:
    return str(period)


def short_date_label(date_value: pd.Timestamp) -> str:
    return f"{date_value.day:02d} {SHORT_MONTHS_ES[date_value.month]}"


def family_from_material(material: str) -> str:
    value = material.lower()
    if material == "Sin dato":
        return "Sin dato"
    if any(token in value for token in ["carton", "papel", "duplex", "mixto", "diario"]):
        return "Papeles y cartones"
    if any(
        token in value
        for token in [
            "film",
            "polietileno",
            "pet",
            "plast",
            "tapas",
            "invernadero",
            "stretch",
            "strech",
        ]
    ):
        return "Plásticos y films"
    if "vidrio" in value:
        return "Vidrio"
    if any(token in value for token in ["chatarra", "aluminio", "fierro", "metal", "lata"]):
        return "Metales y chatarra"
    return "Otros"


def split_materials(value: object) -> list[str]:
    text = normalize_text(value)
    if text == "Sin dato" or text == "|":
        return ["Sin dato"]
    parts = [part.strip() for part in text.split("|") if part.strip()]
    return parts or ["Sin dato"]


def fmt_number(value: float, decimals: int = 0) -> str:
    formatted = f"{value:,.{decimals}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def top_share_text(value: float, total: float) -> str:
    if not total:
        return "0%"
    return f"{(value / total) * 100:.1f}%".replace(".", ",")


INPUT_FILE = resolve_input_file()
df = pd.read_excel(INPUT_FILE)
df["FECHA_DT"] = pd.to_datetime(df["FECHA"], dayfirst=True, errors="coerce")
period_counts = df["FECHA_DT"].dt.to_period("M").value_counts()
available_periods = sorted(period_counts.index.tolist())
dashboard_periods = available_periods[-4:] if len(available_periods) >= 4 else available_periods
default_period = dashboard_periods[-1]
dashboard_period_label = period_window_label(dashboard_periods)
full_df = df.copy()
full_df["periodKey"] = full_df["FECHA_DT"].dt.to_period("M").map(period_key)
full_df["amount"] = parse_amount(full_df["TOTAL VALE"])
full_df["weight"] = parse_weight(full_df["PESO FINAL"])
full_df["ticket"] = full_df["amount"]
full_df["branch"] = full_df["SUCURSAL"].map(normalize_title)
full_df["service"] = full_df["TIPO SERVICIO"].map(normalize_title)
full_df["transport"] = full_df["TIPO TRANSPORTE"].map(normalize_title)
full_df["client"] = full_df["RAZÓN SOCIAL"].map(normalize_text)
full_df["material"] = full_df["DESC PRODUCTO"].map(normalize_text)
full_df["city"] = full_df["CIUDAD"].map(normalize_title)
full_df["receptionDispatch"] = full_df["RECEPCIÓN DESPACHO"].map(normalize_title)
full_df["originDestination"] = full_df["ORIGEN DESTINO"].map(normalize_text)
full_df["serviceA"] = full_df["SERVICIO A"].map(normalize_text)

window_df = full_df[full_df["FECHA_DT"].dt.to_period("M").isin(dashboard_periods)].copy()

quality_cols = {
    "Sucursal": "branch",
    "Servicio": "service",
    "Transporte": "transport",
    "Cliente": "client",
    "Material": "material",
    "Peso final": "weight",
    "Origen / destino": "originDestination",
    "Recepción / despacho": "receptionDispatch",
    "Servicio a": "serviceA",
}


def build_flat_df(frame: pd.DataFrame, use_magnitude: bool = False) -> pd.DataFrame:
    flat_rows: list[dict[str, object]] = []
    for _, row in frame.iterrows():
        materials = split_materials(row["DESC PRODUCTO"])
        share = 1 / len(materials)
        amount_value = float(row["amount"])
        weight_value = float(0 if pd.isna(row["weight"]) else row["weight"])
        if use_magnitude:
            amount_value = abs(amount_value)
            weight_value = abs(weight_value)
        for material in materials:
            flat_rows.append(
                {
                    "material": material,
                    "family": family_from_material(material),
                    "amount": amount_value * share,
                    "weight": weight_value * share,
                    "folio": int(row["FOLIO"]),
                    "client": row["client"],
                    "periodKey": row["periodKey"],
                }
            )
    return pd.DataFrame(flat_rows)


def build_view(frame: pd.DataFrame, branch_label: str, current_period_label: str) -> dict[str, object]:
    total_records = int(len(frame))
    total_amount = float(frame["amount"].sum())
    total_weight = float(frame["weight"].sum(skipna=True))
    weight_records = int(frame["weight"].notna().sum())
    avg_ticket = float(frame["ticket"].mean()) if total_records else 0.0
    avg_weight = float(frame["weight"].mean(skipna=True)) if weight_records else 0.0

    daily = (
        frame.groupby("FECHA_DT")
        .agg(records=("FOLIO", "count"), amount=("amount", "sum"), weight=("weight", "sum"))
        .reset_index()
    )
    daily["label"] = daily["FECHA_DT"].map(short_date_label)
    daily["iso"] = daily["FECHA_DT"].dt.strftime("%Y-%m-%d")

    branch_stats = (
        frame.groupby("branch")
        .agg(records=("FOLIO", "count"), amount=("amount", "sum"), weight=("weight", "sum"))
        .sort_values(["amount", "records"], ascending=[False, False])
        .reset_index()
    )
    service_stats = (
        frame.groupby("service")
        .agg(records=("FOLIO", "count"), amount=("amount", "sum"), weight=("weight", "sum"))
        .sort_values(["amount", "records"], ascending=[False, False])
        .reset_index()
    )
    transport_stats = (
        frame.groupby("transport")
        .agg(records=("FOLIO", "count"), amount=("amount", "sum"))
        .sort_values(["records", "amount"], ascending=[False, False])
        .reset_index()
    )
    client_stats = (
        frame.groupby("client")
        .agg(records=("FOLIO", "count"), amount=("amount", "sum"), weight=("weight", "sum"))
        .sort_values(["amount", "records"], ascending=[False, False])
        .reset_index()
    )

    flat_df = build_flat_df(frame)
    family_stats = (
        flat_df[flat_df["family"] != "Sin dato"]
        .groupby("family")
        .agg(weight=("weight", "sum"), amount=("amount", "sum"), mentions=("folio", "count"))
        .sort_values(["weight", "amount"], ascending=[False, False])
        .reset_index()
    )
    material_stats = (
        flat_df[flat_df["material"] != "Sin dato"]
        .groupby("material")
        .agg(weight=("weight", "sum"), amount=("amount", "sum"), mentions=("folio", "count"))
        .sort_values(["weight", "amount"], ascending=[False, False])
        .reset_index()
    )

    peak_day = daily.sort_values(["amount", "records"], ascending=[False, False]).iloc[0]
    top_branch = branch_stats.iloc[0]
    top_service = service_stats.iloc[0]
    top_client = client_stats.iloc[0]
    top_material = material_stats.iloc[0] if not material_stats.empty else None

    quality_metrics = []
    missing_rates = []
    for label, col in quality_cols.items():
        series = frame[col]
        if col == "weight":
            missing = int(series.isna().sum())
        else:
            missing = int((series == "Sin dato").sum())
        missing_rate = (missing / total_records) * 100 if total_records else 0
        quality_metrics.append(
            {
                "label": label,
                "missingCount": missing,
                "missingRate": round(missing_rate, 1),
                "completeness": round(100 - missing_rate, 1),
            }
        )
        missing_rates.append(missing_rate)

    quality_metrics = sorted(quality_metrics, key=lambda item: item["missingRate"], reverse=True)
    data_completeness = round(100 - (sum(missing_rates) / len(missing_rates)), 1) if missing_rates else 100
    top_three_days_share = round(daily.sort_values("amount", ascending=False).head(3)["amount"].sum() / total_amount * 100, 1)
    top_two_clients_share = round(client_stats.head(2)["amount"].sum() / total_amount * 100, 1)

    alerts = []
    if total_amount and top_branch["amount"] / total_amount >= 0.7 and branch_label == "Todas":
        alerts.append(
            f"{top_branch['branch']} concentra {top_share_text(top_branch['amount'], total_amount)} del monto mensual."
        )
    for metric in quality_metrics[:4]:
        if metric["missingRate"] >= 15:
            alerts.append(
                f"{metric['label']} presenta {str(metric['missingRate']).replace('.', ',')}% de vacíos."
            )
    if top_two_clients_share >= 55:
        alerts.append(
            f"Los dos principales clientes explican {str(top_two_clients_share).replace('.', ',')}% del monto valorizado."
        )
    if top_three_days_share >= 45:
        alerts.append(
            f"Los tres días de mayor monto concentran {str(top_three_days_share).replace('.', ',')}% del valor del mes."
        )

    if branch_label == "Todas":
        first_summary = f"{current_period_label} cerró con {total_records} registros, CLP {fmt_number(total_amount)} valorizados y {fmt_number(total_weight / 1000, 1)} toneladas con dato de peso."
        second_summary = f"{top_branch['branch']} concentró {top_share_text(top_branch['amount'], total_amount)} del monto del mes, mientras la operación diaria alcanzó su máximo el {peak_day['FECHA_DT'].day} de {MONTHS_ES[peak_day['FECHA_DT'].month]}."
        third_summary = f"{top_service['service']} explicó {top_share_text(top_service['amount'], total_amount)} del valor mensual y la integridad de datos muestra brechas en origen / destino ({str(quality_metrics[0]['missingRate']).replace('.', ',')}%) y peso final ({str(next(item['missingRate'] for item in quality_metrics if item['label'] == 'Peso final')).replace('.', ',')}%)."
        first_insight = f"{top_branch['branch']} lidera por valorización con {top_share_text(top_branch['amount'], total_amount)} del monto, mientras Talca sostiene el mayor flujo por cantidad de registros ({int(branch_stats.loc[branch_stats['branch'] == 'Talca', 'records'].iloc[0]) if (branch_stats['branch'] == 'Talca').any() else int(top_branch['records'])})."
    else:
        first_summary = f"{branch_label} acumuló {total_records} registros, CLP {fmt_number(total_amount)} valorizados y {fmt_number(total_weight / 1000, 1)} toneladas con dato de peso en {current_period_label}."
        second_summary = f"El mayor día por monto fue el {peak_day['FECHA_DT'].day} de {MONTHS_ES[peak_day['FECHA_DT'].month]} y el servicio dominante fue {top_service['service']} con {top_share_text(top_service['amount'], total_amount)} del total de la sucursal."
        third_summary = f"La calidad del dato en {branch_label} muestra mayor brecha en {quality_metrics[0]['label'].lower()} ({str(quality_metrics[0]['missingRate']).replace('.', ',')}%) y en peso final ({str(next(item['missingRate'] for item in quality_metrics if item['label'] == 'Peso final')).replace('.', ',')}%)."
        first_insight = f"{branch_label} registra {total_records} folios en el mes y concentra su valorización principalmente en {top_service['service']}, con ticket promedio de CLP {fmt_number(avg_ticket)}."

    insights = [
        {
            "title": "Concentración operativa",
            "body": first_insight,
        },
        {
            "title": "Servicio dominante",
            "body": f"{top_service['service']} aporta {top_share_text(top_service['amount'], total_amount)} del monto del período y concentra {int(top_service['records'])} registros con mayor ticket que el resto del mix.",
        },
        {
            "title": "Cliente tractor",
            "body": f"{top_client['client']} explica {top_share_text(top_client['amount'], total_amount)} del valor del corte; los dos primeros clientes reúnen {str(top_two_clients_share).replace('.', ',')}% del total valorizado.",
        },
        {
            "title": "Materiales relevantes",
            "body": (
                f"{top_material['material']} lidera el peso identificado con {fmt_number(top_material['weight'] / 1000, 1)} t."
                if top_material is not None
                else "No hay suficiente dato de material para identificar liderazgo."
            ),
        },
        {
            "title": "Picos y calidad",
            "body": f"El mayor día por monto fue el {peak_day['FECHA_DT'].day} de {MONTHS_ES[peak_day['FECHA_DT'].month]} con CLP {fmt_number(peak_day['amount'])}; además persisten vacíos relevantes en origen / destino y peso final.",
        },
    ]

    return {
        "meta": {
            "recordCount": total_records,
            "clientCount": int(frame["client"].nunique()),
            "branchCount": int(frame["branch"].nunique()),
            "serviceCount": int(frame["service"].nunique()),
            "branchLabel": branch_label,
        },
        "summary": [first_summary, second_summary, third_summary],
        "kpis": {
            "totalRecords": total_records,
            "totalAmount": total_amount,
            "totalWeightKg": total_weight,
            "avgTicket": avg_ticket,
            "avgWeightKg": avg_weight,
            "weightRecords": weight_records,
            "peakDayLabel": short_date_label(peak_day["FECHA_DT"]),
            "peakDayAmount": float(peak_day["amount"]),
            "leaderBranch": top_branch["branch"],
            "leaderBranchShare": round((top_branch["amount"] / total_amount) * 100, 1) if total_amount else 0,
            "dominantService": top_service["service"],
            "dominantServiceShare": round((top_service["amount"] / total_amount) * 100, 1) if total_amount else 0,
        },
        "series": {
            "dailyRecords": [
                {"label": row["label"], "date": row["iso"], "value": int(row["records"])}
                for _, row in daily.iterrows()
            ],
            "dailyAmount": [
                {"label": row["label"], "date": row["iso"], "value": float(row["amount"])}
                for _, row in daily.iterrows()
            ],
        },
        "panels": {
            "services": [
                {
                    "label": row["service"],
                    "value": float(row["amount"]),
                    "secondary": f"{int(row['records'])} registros",
                    "share": round((row["amount"] / total_amount) * 100, 1) if total_amount else 0,
                }
                for _, row in service_stats.iterrows()
            ],
            "branches": [
                {
                    "label": row["branch"],
                    "value": float(row["amount"]),
                    "secondary": f"{int(row['records'])} registros",
                    "share": round((row["amount"] / total_amount) * 100, 1) if total_amount else 0,
                }
                for _, row in branch_stats.iterrows()
            ],
            "clients": [
                {
                    "label": row["client"],
                    "value": float(row["amount"]),
                    "secondary": f"{int(row['records'])} registros",
                    "share": round((row["amount"] / total_amount) * 100, 1) if total_amount else 0,
                }
                for _, row in client_stats.head(8).iterrows()
            ],
            "families": [
                {
                    "label": row["family"],
                    "value": float(row["weight"]),
                    "secondary": f"CLP {fmt_number(row['amount'])}",
                    "share": round((row["weight"] / family_stats["weight"].sum()) * 100, 1)
                    if not family_stats.empty and family_stats["weight"].sum()
                    else 0,
                }
                for _, row in family_stats.iterrows()
            ],
            "materials": [
                {
                    "label": row["material"],
                    "value": float(row["weight"]),
                    "secondary": f"CLP {fmt_number(row['amount'])}",
                    "share": round((row["weight"] / material_stats.head(8)["weight"].sum()) * 100, 1)
                    if not material_stats.empty and material_stats.head(8)["weight"].sum()
                    else 0,
                }
                for _, row in material_stats.head(8).iterrows()
            ],
            "transport": [
                {
                    "label": row["transport"],
                    "value": float(row["records"]),
                    "secondary": f"CLP {fmt_number(row['amount'])}",
                    "share": round((row["records"] / total_records) * 100, 1) if total_records else 0,
                }
                for _, row in transport_stats.iterrows()
            ],
        },
        "quality": {
            "completenessScore": data_completeness,
            "materialMissing": int((frame["material"] == "Sin dato").sum()),
            "weightMissing": int(frame["weight"].isna().sum()),
            "alertCount": len(alerts),
            "metrics": quality_metrics,
            "alerts": alerts,
        },
        "insights": insights,
    }


def delta_percent(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 1)


def build_history_data(active_period: pd.Period) -> dict[str, object]:
    periods_until = [period for period in dashboard_periods if period <= active_period]
    monthly = []
    for period in periods_until:
        frame = window_df[window_df["periodKey"] == period_key(period)].copy()
        monthly.append(
            {
                "key": period_key(period),
                "label": month_label(period),
                "records": int(len(frame)),
                "amount": float(frame["amount"].sum()),
                "weightKg": float(frame["weight"].sum(skipna=True)),
            }
        )

    current_frame = full_df[full_df["periodKey"] == period_key(active_period)].copy()
    previous_candidates = [period for period in available_periods if period < active_period]
    previous_period = previous_candidates[-1] if previous_candidates else None
    previous_frame = (
        full_df[full_df["periodKey"] == period_key(previous_period)].copy()
        if previous_period is not None
        else full_df.iloc[0:0].copy()
    )

    idx = available_periods.index(active_period)
    trailing_periods = available_periods[max(0, idx - 3):idx]
    trailing_frame = (
        full_df[full_df["FECHA_DT"].dt.to_period("M").isin(trailing_periods)].copy()
        if trailing_periods
        else full_df.iloc[0:0].copy()
    )

    current_clients = set(current_frame["client"].tolist())
    inactive_rows = []
    if not trailing_frame.empty:
        grouped = trailing_frame.groupby("client").agg(
            last_visit=("FECHA_DT", "max"),
            amount=("amount", "sum"),
            visits=("FOLIO", "count"),
        ).reset_index()
        grouped = grouped[~grouped["client"].isin(current_clients)]
        grouped = grouped.sort_values(["amount", "last_visit"], ascending=[False, False]).head(12)
        cutoff_date = (
            current_frame["FECHA_DT"].max().normalize()
            if not current_frame.empty
            else pd.Timestamp(active_period.end_time).normalize()
        )
        for _, row in grouped.iterrows():
            days_inactive = int((cutoff_date - row["last_visit"].normalize()).days)
            if days_inactive < 30:
                continue
            inactive_rows.append(
                {
                    "client": row["client"],
                    "lastVisit": row["last_visit"].strftime("%d/%m/%Y"),
                    "daysInactive": days_inactive,
                    "amount": float(row["amount"]),
                    "visits": int(row["visits"]),
                }
            )

    behavior_rows: list[dict[str, object]] = []
    behavior_summary = {
        "drops": 0,
        "gains": 0,
        "mixChanges": 0,
        "reactivated": 0,
    }
    behavior_window_label = "Sin base histórica suficiente"
    if trailing_periods and not current_frame.empty:
        baseline_month_count = len(trailing_periods)
        behavior_window_label = f"Compara el mes activo contra el promedio de {baseline_month_count} mes{'es' if baseline_month_count != 1 else ''} previo{'s' if baseline_month_count != 1 else ''}."
        older_frame = full_df[full_df["FECHA_DT"].dt.to_period("M") < trailing_periods[0]].copy()
        older_clients = set(older_frame["client"].tolist())

        current_behavior = current_frame.copy()
        baseline_behavior = trailing_frame.copy()
        current_behavior["behaviorAmount"] = current_behavior["amount"].abs()
        current_behavior["behaviorWeight"] = current_behavior["weight"].abs()
        baseline_behavior["behaviorAmount"] = baseline_behavior["amount"].abs()
        baseline_behavior["behaviorWeight"] = baseline_behavior["weight"].abs()

        current_stats = current_behavior.groupby("client").agg(
            visits=("FOLIO", "count"),
            amount=("behaviorAmount", "sum"),
            weight=("behaviorWeight", "sum"),
        )
        baseline_stats = baseline_behavior.groupby("client").agg(
            visits=("FOLIO", "count"),
            amount=("behaviorAmount", "sum"),
            weight=("behaviorWeight", "sum"),
            last_visit=("FECHA_DT", "max"),
        )

        current_flat = build_flat_df(current_behavior, use_magnitude=True)
        baseline_flat = build_flat_df(baseline_behavior, use_magnitude=True)

        def dominant_materials(flat_df: pd.DataFrame) -> dict[str, str]:
            if flat_df.empty:
                return {}
            enriched = flat_df.copy()
            enriched["weightForRank"] = enriched["weight"].fillna(0.0)
            grouped = (
                enriched.groupby(["client", "material"])
                .agg(weight=("weightForRank", "sum"), amount=("amount", "sum"))
                .reset_index()
                .sort_values(["client", "weight", "amount"], ascending=[True, False, False])
            )
            dominant: dict[str, str] = {}
            for client, client_frame in grouped.groupby("client"):
                top_row = client_frame.iloc[0]
                dominant[str(client)] = str(top_row["material"])
            return dominant

        current_materials = dominant_materials(current_flat)
        baseline_materials = dominant_materials(baseline_flat)

        def behavior_pct_text(value: float | None) -> str:
            if value is None or pd.isna(value):
                return "Sin base"
            absolute = abs(float(value))
            if absolute > 999:
                return ">999%"
            return f"{absolute:.0f}%"

        def add_trend_label(labels: list[str], label: str) -> None:
            if label not in labels:
                labels.append(label)

        for client in sorted(current_clients):
            current_visits = int(current_stats.loc[client, "visits"]) if client in current_stats.index else 0
            current_amount_client = float(current_stats.loc[client, "amount"]) if client in current_stats.index else 0.0
            current_weight_client = float(current_stats.loc[client, "weight"]) if client in current_stats.index and pd.notna(current_stats.loc[client, "weight"]) else 0.0

            baseline_visits_total = float(baseline_stats.loc[client, "visits"]) if client in baseline_stats.index else 0.0
            baseline_amount_total = float(baseline_stats.loc[client, "amount"]) if client in baseline_stats.index else 0.0
            baseline_weight_total = float(baseline_stats.loc[client, "weight"]) if client in baseline_stats.index and pd.notna(baseline_stats.loc[client, "weight"]) else 0.0

            baseline_visits_avg = baseline_visits_total / baseline_month_count
            baseline_amount_avg = baseline_amount_total / baseline_month_count
            baseline_weight_avg = baseline_weight_total / baseline_month_count

            meaningful_baseline = (
                baseline_visits_avg >= 3
                or baseline_amount_avg >= 250000
                or baseline_weight_avg >= 2000
            )
            meaningful_current = (
                current_visits >= 3
                or current_amount_client >= 250000
                or current_weight_client >= 2000
            )

            visits_pct = delta_percent(float(current_visits), baseline_visits_avg)
            amount_pct = delta_percent(current_amount_client, baseline_amount_avg)
            weight_pct = delta_percent(current_weight_client, baseline_weight_avg)

            current_material = current_materials.get(client, "Sin dato")
            baseline_material = baseline_materials.get(client, "Sin dato")
            alerts: list[str] = []
            trend_labels: list[str] = []
            score = 0.0

            if baseline_visits_avg >= 3 and current_visits <= max(0, baseline_visits_avg * 0.6):
                alerts.append(
                    f"Frecuencia cae {behavior_pct_text(visits_pct)} vs prom. previo ({baseline_visits_avg:.1f} visitas/mes)."
                )
                add_trend_label(trend_labels, "Frecuencia a la baja")
                behavior_summary["drops"] += 1
                score += min(abs(visits_pct or 0), 300)
            elif (
                baseline_visits_avg >= 1
                and meaningful_current
                and current_visits >= max(baseline_visits_avg * 1.5, baseline_visits_avg + 2, 3)
            ):
                alerts.append(
                    f"Frecuencia sube {behavior_pct_text(visits_pct)} vs prom. previo ({baseline_visits_avg:.1f} visitas/mes)."
                )
                add_trend_label(trend_labels, "Frecuencia al alza")
                behavior_summary["gains"] += 1
                score += min(abs(visits_pct or 0), 300)

            if baseline_weight_avg >= 2000 and current_weight_client <= baseline_weight_avg * 0.65:
                alerts.append(
                    f"Kilos caen {behavior_pct_text(weight_pct)} vs prom. previo ({fmt_number(baseline_weight_avg, 0)} kg/mes)."
                )
                if "Frecuencia a la baja" not in trend_labels and "Kilos a la baja" not in trend_labels and "Monto a la baja" not in trend_labels:
                    add_trend_label(trend_labels, "Kilos a la baja")
                    behavior_summary["drops"] += 1
                score += min(abs(weight_pct or 0), 300)
            elif (
                baseline_weight_avg >= 1000
                and meaningful_current
                and current_weight_client >= max(baseline_weight_avg * 1.5, baseline_weight_avg + 1500)
            ):
                alerts.append(
                    f"Kilos suben {behavior_pct_text(weight_pct)} vs prom. previo ({fmt_number(baseline_weight_avg, 0)} kg/mes)."
                )
                if "Frecuencia al alza" not in trend_labels and "Kilos al alza" not in trend_labels and "Monto al alza" not in trend_labels:
                    add_trend_label(trend_labels, "Kilos al alza")
                    behavior_summary["gains"] += 1
                score += min(abs(weight_pct or 0), 300)

            if baseline_amount_avg >= 250000 and current_amount_client <= baseline_amount_avg * 0.65:
                alerts.append(
                    f"Monto cae {behavior_pct_text(amount_pct)} vs prom. previo (CLP {fmt_number(baseline_amount_avg)} / mes)."
                )
                if (
                    "Frecuencia a la baja" not in trend_labels
                    and "Kilos a la baja" not in trend_labels
                    and "Monto a la baja" not in trend_labels
                ):
                    add_trend_label(trend_labels, "Monto a la baja")
                    behavior_summary["drops"] += 1
                score += min(abs(amount_pct or 0), 300)
            elif (
                baseline_amount_avg >= 250000
                and meaningful_current
                and current_amount_client >= max(baseline_amount_avg * 1.5, baseline_amount_avg + 200000)
            ):
                alerts.append(
                    f"Monto sube {behavior_pct_text(amount_pct)} vs prom. previo (CLP {fmt_number(baseline_amount_avg)} / mes)."
                )
                if (
                    "Frecuencia al alza" not in trend_labels
                    and "Kilos al alza" not in trend_labels
                    and "Monto al alza" not in trend_labels
                ):
                    add_trend_label(trend_labels, "Monto al alza")
                    behavior_summary["gains"] += 1
                score += min(abs(amount_pct or 0), 300)

            if (
                current_material != "Sin dato"
                and baseline_material != "Sin dato"
                and current_material != baseline_material
                and (meaningful_baseline or meaningful_current)
            ):
                alerts.append(f"Cambia material dominante: de {baseline_material} a {current_material}.")
                if "Cambio de mix" not in trend_labels:
                    add_trend_label(trend_labels, "Cambio de mix")
                    behavior_summary["mixChanges"] += 1
                score += 30

            if (
                baseline_visits_total == 0
                and client in older_clients
                and (current_visits >= 2 or current_amount_client >= 100000 or current_weight_client >= 1000)
            ):
                older_last_visit = older_frame.loc[older_frame["client"] == client, "FECHA_DT"].max()
                if pd.notna(older_last_visit):
                    dormant_days = int((current_frame["FECHA_DT"].max().normalize() - older_last_visit.normalize()).days)
                    alerts.append(f"Cliente reactivado tras {dormant_days} días sin movimientos en la ventana reciente.")
                    if "Reactivado" not in trend_labels:
                        add_trend_label(trend_labels, "Reactivado")
                        behavior_summary["reactivated"] += 1
                    score += max(25, dormant_days / 2)

            if not alerts or (not meaningful_baseline and not meaningful_current and "Reactivado" not in trend_labels):
                continue

            severity = "critical" if len(alerts) >= 3 or score >= 180 else "warning"
            behavior_rows.append(
                {
                    "client": client,
                    "trend": " · ".join(trend_labels) if trend_labels else "Seguimiento",
                    "visitsCurrent": current_visits,
                    "visitsBaselineAvg": round(baseline_visits_avg, 1),
                    "weightCurrentKg": current_weight_client,
                    "weightBaselineAvgKg": baseline_weight_avg,
                    "amountCurrent": current_amount_client,
                    "amountBaselineAvg": baseline_amount_avg,
                    "materialCurrent": current_material,
                    "materialBaseline": baseline_material,
                    "alerts": alerts,
                    "severity": severity,
                    "score": score,
                }
            )

        behavior_rows = sorted(
            behavior_rows,
            key=lambda item: (
                0 if item["severity"] == "critical" else 1,
                -item["score"],
                -item["amountCurrent"],
            ),
        )[:12]

    current_amount = float(current_frame["amount"].sum())
    current_weight = float(current_frame["weight"].sum(skipna=True))
    current_records = int(len(current_frame))
    previous_amount = float(previous_frame["amount"].sum()) if not previous_frame.empty else 0.0
    previous_weight = float(previous_frame["weight"].sum(skipna=True)) if not previous_frame.empty else 0.0
    previous_records = int(len(previous_frame)) if not previous_frame.empty else 0

    return {
        "activeLabel": month_label(active_period),
        "previousLabel": month_label(previous_period) if previous_period is not None else "Sin base previa",
        "monthly": monthly,
        "deltas": {
            "amountPct": delta_percent(current_amount, previous_amount),
            "weightPct": delta_percent(current_weight, previous_weight),
            "recordsPct": delta_percent(float(current_records), float(previous_records)),
            "currentAmount": current_amount,
            "currentWeightKg": current_weight,
            "currentRecords": current_records,
            "previousAmount": previous_amount,
            "previousWeightKg": previous_weight,
            "previousRecords": previous_records,
        },
        "inactiveClients": inactive_rows,
        "behavior": {
            "windowLabel": behavior_window_label,
            "summary": [
                {
                    "label": "Clientes con caída",
                    "value": behavior_summary["drops"],
                    "foot": "Frecuencia, kilos o monto por debajo del patrón reciente.",
                },
                {
                    "label": "Clientes con alza",
                    "value": behavior_summary["gains"],
                    "foot": "Incrementos relevantes de actividad o valorización.",
                },
                {
                    "label": "Cambio de material",
                    "value": behavior_summary["mixChanges"],
                    "foot": "Cambio detectado en el material dominante del cliente.",
                },
                {
                    "label": "Clientes reactivados",
                    "value": behavior_summary["reactivated"],
                    "foot": "Vuelven a operar tras salir de la ventana reciente.",
                },
            ],
            "rows": behavior_rows,
        },
    }


def build_risk_data(active_period: pd.Period) -> dict[str, object]:
    period_frame = full_df[full_df["periodKey"] == period_key(active_period)].copy()
    baseline_frame = full_df[full_df["FECHA_DT"].dt.to_period("M") <= active_period].copy()

    stock_entries: list[dict[str, object]] = []
    for _, row in period_frame.iterrows():
        materials = split_materials(row["DESC PRODUCTO"])
        if pd.isna(row["weight"]):
            continue
        weight_share = float(row["weight"]) / len(materials)
        for material in materials:
            service = str(row["service"]).lower()
            stock_entries.append(
                {
                    "material": material,
                    "boughtKg": weight_share if service == "compra" else 0.0,
                    "soldKg": weight_share if service == "venta" else 0.0,
                    "amount": float(row["amount"]) / len(materials),
                }
            )

    stock_rows = []
    if stock_entries:
        stock_df = pd.DataFrame(stock_entries)
        stock_grouped = (
            stock_df.groupby("material")
            .agg(boughtKg=("boughtKg", "sum"), soldKg=("soldKg", "sum"), amount=("amount", "sum"))
            .reset_index()
        )
        stock_grouped["netKg"] = stock_grouped["boughtKg"] - stock_grouped["soldKg"]
        stock_grouped = stock_grouped.sort_values(["amount", "netKg"], ascending=[False, False]).head(12)
        for _, row in stock_grouped.iterrows():
            stock_rows.append(
                {
                    "material": row["material"],
                    "boughtKg": float(row["boughtKg"]),
                    "soldKg": float(row["soldKg"]),
                    "netKg": float(row["netKg"]),
                    "flag": bool(row["netKg"] < 0),
                }
            )

    total_amount = float(period_frame["amount"].sum())
    client_grouped = period_frame.groupby("client")["amount"].sum().sort_values(ascending=False)
    top_client_name = client_grouped.index[0] if not client_grouped.empty else "Sin dato"
    top_client_amount = float(client_grouped.iloc[0]) if not client_grouped.empty else 0.0

    flat_period = build_flat_df(period_frame)
    material_grouped = flat_period.groupby("material")["amount"].sum().sort_values(ascending=False) if not flat_period.empty else pd.Series(dtype=float)
    top_material_name = material_grouped.index[0] if not material_grouped.empty else "Sin dato"
    top_material_amount = float(material_grouped.iloc[0]) if not material_grouped.empty else 0.0

    daily_grouped = period_frame.groupby("FECHA_DT")["amount"].sum().sort_values(ascending=False)
    top_day_date = daily_grouped.index[0] if not daily_grouped.empty else None
    top_day_amount = float(daily_grouped.iloc[0]) if not daily_grouped.empty else 0.0

    def concentration_status(share: float) -> str:
        if share > 50:
            return "critical"
        if share >= 30:
            return "warning"
        return "healthy"

    concentration = [
        {
            "label": "Top 1 cliente",
            "subject": top_client_name,
            "share": round((top_client_amount / total_amount) * 100, 1) if total_amount else 0,
            "detail": f"Si sale {top_client_name}, se expone ese porcentaje del monto del mes.",
        },
        {
            "label": "Top 1 material",
            "subject": top_material_name,
            "share": round((top_material_amount / total_amount) * 100, 1) if total_amount else 0,
            "detail": f"{top_material_name} concentra la mayor parte del valor valorizado identificado.",
        },
        {
            "label": "Top 1 día",
            "subject": short_date_label(top_day_date) if top_day_date is not None else "Sin dato",
            "share": round((top_day_amount / total_amount) * 100, 1) if total_amount else 0,
            "detail": f"El día más intenso del período concentra ese porcentaje del monto total.",
        },
    ]
    for item in concentration:
        item["status"] = concentration_status(item["share"])

    client_baseline = baseline_frame.groupby("client").agg(
        mean_amount=("amount", "mean"),
        std_amount=("amount", "std"),
        visits=("FOLIO", "count"),
    )
    material_baseline = baseline_frame.groupby("material").agg(
        mean_weight=("weight", "mean"),
        std_weight=("weight", "std"),
        visits=("FOLIO", "count"),
    )
    day_client_counts = period_frame.groupby(["FECHA_DT", "client"]).size()
    day_amount_counts = period_frame.groupby(["FECHA_DT", "amount"]).size()

    outliers = []
    for _, row in period_frame.sort_values(["amount", "FECHA_DT"], ascending=[False, False]).iterrows():
        alerts = []
        client_stats = client_baseline.loc[row["client"]] if row["client"] in client_baseline.index else None
        if client_stats is not None and client_stats["visits"] > 3 and pd.notna(client_stats["std_amount"]) and float(client_stats["std_amount"]) > 0:
            threshold = float(client_stats["mean_amount"]) + (3 * float(client_stats["std_amount"]))
            if float(row["amount"]) > threshold:
                alerts.append("Ticket sobre 3 desviaciones del promedio del cliente")

        material_stats = material_baseline.loc[row["material"]] if row["material"] in material_baseline.index else None
        if (
            material_stats is not None
            and material_stats["visits"] > 3
            and pd.notna(row["weight"])
            and pd.notna(material_stats["std_weight"])
            and float(material_stats["std_weight"]) > 0
        ):
            weight_threshold = float(material_stats["mean_weight"]) + (3 * float(material_stats["std_weight"]))
            if float(row["weight"]) > weight_threshold:
                alerts.append("Peso sobre 3 desviaciones del promedio del material")

        if int(day_client_counts.loc[(row["FECHA_DT"], row["client"])]) > 2:
            alerts.append("Cliente con más de 2 visitas en el mismo día")

        if int(day_amount_counts.loc[(row["FECHA_DT"], row["amount"])]) >= 3:
            alerts.append("Monto exacto repetido 3+ veces el mismo día")

        if alerts:
            outliers.append(
                {
                    "folio": int(row["FOLIO"]),
                    "date": row["FECHA_DT"].strftime("%d/%m/%Y"),
                    "client": row["client"],
                    "amount": float(row["amount"]),
                    "service": row["service"],
                    "alerts": alerts,
                }
            )

    return {
        "alertCount": len(outliers),
        "stockRows": stock_rows,
        "concentration": concentration,
        "outliers": outliers[:20],
    }


def build_quality_tab_data(active_period: pd.Period) -> dict[str, object]:
    period_frame = full_df[full_df["periodKey"] == period_key(active_period)].copy()
    matrix_fields = [
        ("originDestination", "Origen / destino"),
        ("weight", "Peso final"),
        ("material", "Material"),
        ("transport", "Transporte"),
        ("receptionDispatch", "Recepción / despacho"),
    ]

    branch_matrix = []
    for branch, branch_frame in period_frame.groupby("branch"):
        row = {"branch": branch, "records": int(len(branch_frame))}
        completeness_values = []
        for field_key, _ in matrix_fields:
            if field_key == "weight":
                missing = int(branch_frame[field_key].isna().sum())
            else:
                missing = int((branch_frame[field_key] == "Sin dato").sum())
            completeness = round(100 - ((missing / len(branch_frame)) * 100), 1) if len(branch_frame) else 100.0
            row[field_key] = completeness
            completeness_values.append(completeness)
        row["avgCompleteness"] = round(sum(completeness_values) / len(completeness_values), 1) if completeness_values else 100.0
        branch_matrix.append(row)
    branch_matrix = sorted(branch_matrix, key=lambda item: item["avgCompleteness"], reverse=True)

    gaps = []
    critical_fields = [
        ("branch", "Sucursal"),
        ("service", "Servicio"),
        ("transport", "Transporte"),
        ("material", "Material"),
        ("weight", "Peso final"),
        ("originDestination", "Origen / destino"),
        ("receptionDispatch", "Recepción / despacho"),
    ]
    for _, row in period_frame.iterrows():
        missing_fields = []
        for field_key, label in critical_fields:
            if field_key == "weight":
                if pd.isna(row[field_key]):
                    missing_fields.append(label)
            elif row[field_key] == "Sin dato":
                missing_fields.append(label)
        if missing_fields:
            gaps.append(
                {
                    "folio": int(row["FOLIO"]),
                    "date": row["FECHA_DT"].strftime("%d/%m/%Y"),
                    "client": row["client"],
                    "branch": row["branch"],
                    "service": row["service"],
                    "amount": float(row["amount"]),
                    "missingFields": missing_fields,
                }
            )
    gaps = sorted(gaps, key=lambda item: item["amount"], reverse=True)[:20]

    return {
        "fields": [{"key": key, "label": label} for key, label in matrix_fields],
        "branchMatrix": branch_matrix,
        "gaps": gaps,
    }

lookup_sources = {
    "clients": sorted(window_df["client"].unique().tolist()),
    "branches": sorted(window_df["branch"].unique().tolist()),
    "services": sorted(window_df["service"].unique().tolist()),
    "transports": sorted(window_df["transport"].unique().tolist()),
    "materials": sorted(window_df["material"].unique().tolist()),
    "cities": sorted(window_df["city"].unique().tolist()),
    "origins": sorted(window_df["originDestination"].unique().tolist()),
}
lookup_index = {name: {value: idx for idx, value in enumerate(values)} for name, values in lookup_sources.items()}
compact_rows = []
for _, row in window_df.sort_values(["FECHA_DT", "FOLIO"], ascending=[False, False]).iterrows():
    compact_rows.append(
        [
            row["periodKey"],
            row["FECHA_DT"].strftime("%Y-%m-%d"),
            int(row["FOLIO"]),
            lookup_index["clients"][row["client"]],
            lookup_index["branches"][row["branch"]],
            lookup_index["services"][row["service"]],
            lookup_index["transports"][row["transport"]],
            lookup_index["materials"][row["material"]],
            None if pd.isna(row["weight"]) else float(row["weight"]),
            float(row["amount"]),
            lookup_index["cities"][row["city"]],
            lookup_index["origins"][row["originDestination"]],
        ]
    )

period_option_items = [
    {"value": period_key(period), "label": month_label(period)}
    for period in dashboard_periods
]
branch_options_by_period: dict[str, list[str]] = {}
views_by_period: dict[str, dict[str, dict[str, object]]] = {}

for period in dashboard_periods:
    key = period_key(period)
    period_label = month_label(period)
    period_frame = window_df[window_df["periodKey"] == key].copy()
    period_branches = sorted(period_frame["branch"].unique().tolist())
    branch_options_by_period[key] = ["Todas"] + period_branches
    views_by_period[key] = {
        "Todas": build_view(period_frame, "Todas", period_label),
        **{
            branch: build_view(period_frame[period_frame["branch"] == branch].copy(), branch, period_label)
            for branch in period_branches
        },
    }

data = {
    "meta": {
        "title": "Dashboard Ejecutivo de Registros Operacionales",
        "subtitle": "Reciclean | valorización, materiales y desempeño operativo del período seleccionado",
        "periodWindowLabel": dashboard_period_label,
        "sourceFile": INPUT_FILE.name,
        "updatedAt": datetime.now().strftime("%d/%m/%Y %H:%M"),
    },
    "defaultBranch": "Todas",
    "defaultPeriod": period_key(default_period),
    "periodOptions": period_option_items,
    "branchOptionsByPeriod": branch_options_by_period,
    "viewsByPeriod": views_by_period,
    "historyRangeOptions": [
        {"value": "1m", "label": "Mes actual", "months": 1},
        {"value": "3m", "label": "Últimos 3 meses", "months": 3},
        {"value": "6m", "label": "Últimos 6 meses", "months": 6},
        {"value": "12m", "label": "Últimos 12 meses", "months": 12},
        {"value": "ytd", "label": "Año completo", "months": 12},
    ],
    "historicalByPeriod": {
        period_key(period): build_history_data(period)
        for period in dashboard_periods
    },
    "riskByPeriod": {
        period_key(period): build_risk_data(period)
        for period in dashboard_periods
    },
    "qualityByPeriod": {
        period_key(period): build_quality_tab_data(period)
        for period in dashboard_periods
    },
    "compact": {
        "lookups": lookup_sources,
        "rows": compact_rows,
    },
}

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Dashboard Reciclean | {data["meta"]["periodWindowLabel"]}</title>
  <style>
    :root {{
      --bg: #eef3ea;
      --bg-strong: #f7faf6;
      --surface: rgba(255, 255, 255, 0.9);
      --surface-strong: #ffffff;
      --line: rgba(40, 68, 53, 0.12);
      --line-strong: rgba(40, 68, 53, 0.22);
      --text: #1f3428;
      --muted: #687b6e;
      --green-900: #214932;
      --green-800: #2d6a45;
      --green-700: #3f8654;
      --green-600: #5fa36d;
      --green-400: #a9cbac;
      --green-300: #d4e5d0;
      --accent: #f0f6ec;
      --sand: #f7f4ec;
      --amber: #a96a24;
      --danger: #9b4638;
      --shadow: 0 18px 50px rgba(31, 52, 40, 0.08);
      --shadow-soft: 0 12px 28px rgba(31, 52, 40, 0.05);
      --radius-xl: 28px;
      --radius-lg: 22px;
      --radius-md: 16px;
      --radius-sm: 12px;
      --max: 1360px;
    }}

    * {{
      box-sizing: border-box;
    }}

    html {{
      scroll-behavior: smooth;
    }}

    body {{
      margin: 0;
      overflow-x: hidden;
      background:
        radial-gradient(circle at top left, rgba(95, 163, 109, 0.18), transparent 28rem),
        radial-gradient(circle at 100% 0%, rgba(33, 73, 50, 0.09), transparent 26rem),
        linear-gradient(180deg, #edf3ec 0%, #f8faf7 32%, #eff5f0 100%);
      color: var(--text);
      font-family: "Avenir Next", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    }}

    body.printing-dashboard {{
      background: #ffffff;
    }}

    body::before,
    body::after {{
      content: "";
      position: fixed;
      inset: auto;
      pointer-events: none;
      z-index: 0;
      filter: blur(3px);
    }}

    body::before {{
      top: -6rem;
      right: -6rem;
      width: 22rem;
      height: 22rem;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(169, 203, 172, 0.32), transparent 68%);
    }}

    body::after {{
      bottom: -8rem;
      left: -7rem;
      width: 25rem;
      height: 25rem;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(95, 163, 109, 0.16), transparent 72%);
    }}

    .page {{
      position: relative;
      z-index: 1;
      max-width: var(--max);
      margin: 0 auto;
      padding: 32px 20px 44px;
    }}

    .hero {{
      position: relative;
      display: grid;
      grid-template-columns: minmax(0, 1.5fr) minmax(320px, 0.9fr);
      gap: 22px;
      padding: 32px;
      border: 1px solid rgba(40, 68, 53, 0.08);
      border-radius: var(--radius-xl);
      background:
        linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(242, 248, 239, 0.94)),
        linear-gradient(180deg, rgba(33, 73, 50, 0.04), transparent);
      box-shadow: var(--shadow);
      overflow: hidden;
    }}

    .hero::after {{
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(120deg, rgba(95, 163, 109, 0.05), transparent 45%),
        repeating-linear-gradient(90deg, transparent, transparent 62px, rgba(33, 73, 50, 0.025) 62px, rgba(33, 73, 50, 0.025) 63px);
      pointer-events: none;
    }}

    .hero-block,
    .hero-aside {{
      position: relative;
      z-index: 1;
    }}

    .eyebrow {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(47, 106, 70, 0.08);
      color: var(--green-800);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    h1 {{
      margin: 16px 0 10px;
      font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
      font-size: clamp(2.1rem, 4.2vw, 3.7rem);
      line-height: 0.98;
      letter-spacing: -0.04em;
    }}

    .subtitle {{
      max-width: 58rem;
      margin: 0;
      color: var(--muted);
      font-size: 1rem;
      line-height: 1.6;
    }}

    .hero-meta {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, max-content));
      gap: 10px;
      margin-top: 18px;
      align-items: start;
    }}

    .chip {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 14px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.76);
      color: var(--text);
      font-size: 0.92rem;
      white-space: normal;
      max-width: 100%;
    }}

    .chip-select {{
      gap: 10px;
      padding-right: 10px;
    }}

    .chip-select-label {{
      color: var(--muted);
      font-weight: 700;
      white-space: nowrap;
    }}

    .chip-select select {{
      border: 0;
      outline: 0;
      background: transparent;
      color: var(--text);
      font: inherit;
      font-weight: 700;
      min-width: 110px;
      padding-right: 14px;
      cursor: pointer;
      appearance: none;
      -webkit-appearance: none;
      -moz-appearance: none;
    }}

    .chip-select select:focus {{
      outline: none;
    }}

    .summary-list {{
      display: grid;
      gap: 12px;
      margin: 22px 0 0;
      padding: 0;
      list-style: none;
    }}

    .summary-item {{
      position: relative;
      padding-left: 18px;
      color: var(--text);
      line-height: 1.6;
      font-size: 0.99rem;
    }}

    .summary-item::before {{
      content: "";
      position: absolute;
      left: 0;
      top: 10px;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: linear-gradient(135deg, var(--green-700), var(--green-400));
      box-shadow: 0 0 0 4px rgba(63, 134, 84, 0.12);
    }}

    .hero-aside {{
      display: grid;
      gap: 14px;
      align-content: start;
    }}

    .aside-card {{
      display: grid;
      gap: 10px;
      padding: 18px 18px 16px;
      border-radius: var(--radius-lg);
      background: rgba(255, 255, 255, 0.88);
      border: 1px solid rgba(40, 68, 53, 0.08);
      box-shadow: var(--shadow-soft);
    }}

    .aside-card strong {{
      font-size: 1rem;
      font-weight: 800;
      letter-spacing: -0.02em;
    }}

    .aside-kpis {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }}

    .mini-stat {{
      padding: 14px;
      border-radius: var(--radius-md);
      background: linear-gradient(180deg, var(--accent), rgba(255,255,255,0.92));
      border: 1px solid rgba(40, 68, 53, 0.08);
    }}

    .mini-stat .value {{
      font-size: 1.3rem;
      font-weight: 800;
      letter-spacing: -0.04em;
    }}

    .mini-stat .label {{
      margin-top: 6px;
      color: var(--muted);
      font-size: 0.84rem;
    }}

    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 16px;
      margin-top: 22px;
    }}

    .kpi-card,
    .panel,
    .insight-card,
    .filters-card {{
      border: 1px solid rgba(40, 68, 53, 0.08);
      background: rgba(255, 255, 255, 0.9);
      box-shadow: var(--shadow-soft);
      border-radius: var(--radius-lg);
    }}

    .kpi-card {{
      padding: 18px;
      display: grid;
      gap: 14px;
      min-height: 168px;
    }}

    .kpi-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }}

    .icon-box {{
      width: 44px;
      height: 44px;
      border-radius: 14px;
      display: grid;
      place-items: center;
      background: linear-gradient(135deg, rgba(63, 134, 84, 0.12), rgba(212, 229, 208, 0.66));
      color: var(--green-800);
      border: 1px solid rgba(63, 134, 84, 0.12);
    }}

    .kpi-label {{
      color: var(--muted);
      font-size: 0.88rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-weight: 700;
    }}

    .kpi-value {{
      font-size: clamp(1.7rem, 3vw, 2.35rem);
      line-height: 0.95;
      font-weight: 800;
      letter-spacing: -0.05em;
    }}

    .kpi-foot {{
      color: var(--muted);
      font-size: 0.92rem;
      line-height: 1.45;
    }}

    .section-title {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin: 30px 0 14px;
    }}

    .section-title h2 {{
      margin: 0;
      font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
      font-size: clamp(1.45rem, 2.4vw, 2rem);
      letter-spacing: -0.04em;
    }}

    .section-title p {{
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 0.95rem;
    }}

    .section-badge {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: var(--green-800);
      background: rgba(47, 106, 70, 0.08);
      border-radius: 999px;
      padding: 10px 14px;
      font-size: 0.86rem;
      font-weight: 700;
      white-space: normal;
    }}

    .panel-grid {{
      display: grid;
      grid-template-columns: repeat(12, minmax(0, 1fr));
      gap: 16px;
    }}

    .panel {{
      padding: 18px;
      min-width: 0;
      overflow: hidden;
    }}

    .span-12 {{ grid-column: span 12; }}
    .span-8 {{ grid-column: span 8; }}
    .span-7 {{ grid-column: span 7; }}
    .span-6 {{ grid-column: span 6; }}
    .span-5 {{ grid-column: span 5; }}
    .span-4 {{ grid-column: span 4; }}

    .panel-header {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
    }}

    .panel-title {{
      margin: 0;
      font-size: 1.04rem;
      letter-spacing: -0.02em;
    }}

    .panel-subtitle {{
      margin: 5px 0 0;
      color: var(--muted);
      font-size: 0.9rem;
      line-height: 1.45;
    }}

    .panel-note {{
      padding: 8px 12px;
      border-radius: 999px;
      background: var(--sand);
      color: var(--amber);
      font-size: 0.82rem;
      font-weight: 700;
      white-space: normal;
      text-align: center;
    }}

    .chart-shell {{
      width: 100%;
      min-width: 0;
      overflow: hidden;
    }}

    .chart-legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 4px 0 0;
      color: var(--muted);
      font-size: 0.86rem;
    }}

    .legend-dot {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
      display: inline-block;
      margin-right: 7px;
      background: var(--green-700);
    }}

    .rank-list {{
      display: grid;
      gap: 12px;
    }}

    .rank-item {{
      display: grid;
      gap: 8px;
      padding: 14px 14px 12px;
      border-radius: var(--radius-md);
      background: linear-gradient(180deg, rgba(240, 246, 236, 0.72), rgba(255,255,255,0.96));
      border: 1px solid rgba(40, 68, 53, 0.08);
    }}

    .rank-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }}

    .rank-label {{
      font-weight: 700;
      min-width: 0;
      line-height: 1.3;
    }}

    .rank-value {{
      flex-shrink: 0;
      text-align: right;
      font-weight: 800;
      letter-spacing: -0.03em;
    }}

    .rank-secondary {{
      color: var(--muted);
      font-size: 0.86rem;
    }}

    .bar-track {{
      height: 9px;
      border-radius: 999px;
      background: rgba(63, 134, 84, 0.12);
      overflow: hidden;
    }}

    .bar-fill {{
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, var(--green-700), var(--green-400));
    }}

    .quality-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }}

    .quality-card {{
      padding: 16px;
      border-radius: var(--radius-md);
      border: 1px solid rgba(40, 68, 53, 0.08);
      background: linear-gradient(180deg, rgba(247, 250, 246, 0.96), rgba(240, 246, 236, 0.84));
    }}

    .quality-card .value {{
      font-size: 1.85rem;
      font-weight: 800;
      letter-spacing: -0.05em;
    }}

    .quality-card .label {{
      color: var(--muted);
      font-size: 0.86rem;
      margin-top: 6px;
    }}

    .alerts {{
      display: grid;
      gap: 10px;
      margin-top: 14px;
    }}

    .alert-item {{
      padding: 13px 14px;
      border-radius: var(--radius-md);
      background: rgba(169, 106, 36, 0.08);
      border: 1px solid rgba(169, 106, 36, 0.12);
      color: #7b541d;
      font-size: 0.92rem;
      line-height: 1.5;
    }}

    .insights-grid {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 16px;
    }}

    .insight-card {{
      padding: 18px;
      display: grid;
      gap: 12px;
      min-height: 188px;
    }}

    .insight-card h3 {{
      margin: 0;
      font-size: 1rem;
      letter-spacing: -0.02em;
    }}

    .insight-card p {{
      margin: 0;
      color: var(--muted);
      font-size: 0.94rem;
      line-height: 1.6;
    }}

    .filters-card {{
      padding: 18px;
    }}

    .filters-grid {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 12px;
      margin-top: 14px;
    }}

    .field {{
      display: grid;
      gap: 8px;
      min-width: 0;
    }}

    .field label {{
      color: var(--muted);
      font-size: 0.82rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .field input,
    .field select {{
      width: 100%;
      min-width: 0;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid rgba(40, 68, 53, 0.12);
      background: rgba(255,255,255,0.96);
      color: var(--text);
      font: inherit;
      outline: none;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.8);
    }}

    .field input:focus,
    .field select:focus {{
      border-color: rgba(63, 134, 84, 0.45);
      box-shadow: 0 0 0 4px rgba(63, 134, 84, 0.12);
    }}

    .field select:disabled {{
      background: rgba(237, 243, 234, 0.98);
      color: var(--muted);
      cursor: not-allowed;
    }}

    .auth-actions {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
    }}

    .auth-copy {{
      display: grid;
      gap: 4px;
    }}

    .auth-label {{
      color: var(--green-800);
      font-size: 0.78rem;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    .auth-description {{
      color: var(--muted);
      font-size: 0.9rem;
      line-height: 1.45;
    }}

    .ghost-button {{
      appearance: none;
      border: 1px solid rgba(40, 68, 53, 0.14);
      background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(240, 246, 236, 0.96));
      color: var(--green-900);
      border-radius: 14px;
      padding: 12px 16px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease;
      box-shadow: var(--shadow-soft);
    }}

    .ghost-button:hover {{
      transform: translateY(-1px);
      border-color: rgba(63, 134, 84, 0.26);
    }}

    .ghost-button:focus-visible {{
      outline: none;
      box-shadow: 0 0 0 4px rgba(63, 134, 84, 0.14);
    }}

    .ghost-button:disabled {{
      opacity: 0.65;
      cursor: wait;
      transform: none;
    }}

    .button-row {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }}

    .action-status {{
      min-height: 18px;
      color: var(--muted);
      font-size: 0.82rem;
      line-height: 1.4;
    }}

    .action-status[data-tone="success"] {{
      color: var(--green-800);
    }}

    .action-status[data-tone="info"] {{
      color: var(--green-900);
    }}

    .action-status[data-tone="error"] {{
      color: var(--danger);
    }}

    .results-meta {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin: 18px 0 12px;
      color: var(--muted);
      font-size: 0.92rem;
    }}

    .table-wrap {{
      overflow: auto;
      border: 1px solid rgba(40, 68, 53, 0.08);
      border-radius: var(--radius-lg);
      background: rgba(255,255,255,0.96);
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 980px;
    }}

    th,
    td {{
      padding: 14px 16px;
      border-bottom: 1px solid rgba(40, 68, 53, 0.08);
      text-align: left;
      vertical-align: top;
      font-size: 0.94rem;
    }}

    th {{
      position: sticky;
      top: 0;
      z-index: 1;
      background: #f2f7ef;
      color: var(--green-900);
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    tbody tr:hover {{
      background: rgba(95, 163, 109, 0.06);
    }}

    .money,
    .num {{
      white-space: nowrap;
      font-variant-numeric: tabular-nums;
    }}

    .desktop-table {{
      display: block;
    }}

    .mobile-cards {{
      display: none;
      gap: 12px;
    }}

    .mobile-card {{
      padding: 16px;
      border-radius: var(--radius-md);
      border: 1px solid rgba(40, 68, 53, 0.08);
      background: rgba(255,255,255,0.94);
      box-shadow: var(--shadow-soft);
      display: grid;
      gap: 12px;
    }}

    .mobile-head {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
    }}

    .mobile-client {{
      font-weight: 800;
      line-height: 1.35;
    }}

    .mobile-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px 12px;
    }}

    .mobile-field {{
      display: grid;
      gap: 4px;
    }}

    .mobile-field .label {{
      color: var(--muted);
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-weight: 700;
    }}

    .mobile-field .value {{
      font-size: 0.92rem;
      line-height: 1.45;
    }}

    .pill {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 7px 10px;
      border-radius: 999px;
      background: rgba(47, 106, 70, 0.08);
      color: var(--green-800);
      font-size: 0.8rem;
      font-weight: 700;
      width: fit-content;
      max-width: 100%;
    }}

    .empty-state {{
      padding: 30px 18px;
      text-align: center;
      color: var(--muted);
      background: rgba(255,255,255,0.92);
      border: 1px dashed rgba(40, 68, 53, 0.18);
      border-radius: var(--radius-lg);
    }}

    .tab-bar {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin: 18px 0 22px;
      padding: 10px;
      border-radius: 24px;
      background: rgba(255,255,255,0.72);
      border: 1px solid rgba(40, 68, 53, 0.08);
      box-shadow: var(--shadow-soft);
      width: 100%;
    }}

    .tab-button {{
      appearance: none;
      border: 0;
      background: transparent;
      color: var(--muted);
      padding: 12px 16px;
      border-radius: 999px;
      font: inherit;
      font-weight: 800;
      letter-spacing: 0.01em;
      cursor: pointer;
      transition: background 0.16s ease, color 0.16s ease, transform 0.16s ease;
      text-align: center;
    }}

    .tab-button:hover {{
      background: rgba(47, 106, 70, 0.08);
      color: var(--green-900);
      transform: translateY(-1px);
    }}

    .tab-button.is-active {{
      background: linear-gradient(135deg, var(--green-800), var(--green-600));
      color: #fff;
      box-shadow: var(--shadow-soft);
    }}

    .tab-pane {{
      display: none;
    }}

    .tab-pane.is-active {{
      display: block;
    }}

    #print-root {{
      display: none;
    }}

    @media print {{
      body.printing-dashboard {{
        background: #ffffff !important;
      }}

      body.printing-dashboard .page > *:not(#print-root) {{
        display: none !important;
      }}

      body.printing-dashboard #print-root {{
        display: block !important;
      }}

      body.printing-dashboard .page {{
        max-width: none;
        padding: 0;
      }}

      body.printing-dashboard #print-root .ghost-button,
      body.printing-dashboard #print-root .tab-bar {{
        display: none !important;
      }}

      body.printing-dashboard #print-root .tab-pane {{
        display: none !important;
      }}

      body.printing-dashboard #print-root .tab-pane.is-active {{
        display: block !important;
      }}
    }}

    .history-toolbar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 16px;
    }}

    .metric-strip {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }}

    .metric-pill {{
      padding: 16px;
      border-radius: var(--radius-md);
      border: 1px solid rgba(40, 68, 53, 0.08);
      background: linear-gradient(180deg, rgba(240, 246, 236, 0.84), rgba(255,255,255,0.96));
      box-shadow: var(--shadow-soft);
    }}

    .metric-pill .label {{
      color: var(--muted);
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-weight: 800;
    }}

    .metric-pill .value {{
      margin-top: 10px;
      font-size: 1.7rem;
      font-weight: 800;
      letter-spacing: -0.04em;
    }}

    .metric-pill .foot {{
      margin-top: 8px;
      color: var(--muted);
      font-size: 0.88rem;
      line-height: 1.45;
    }}

    .status-chip {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 10px;
      border-radius: 999px;
      font-size: 0.8rem;
      font-weight: 800;
      width: fit-content;
    }}

    .status-chip.critical {{
      background: rgba(155, 70, 56, 0.12);
      color: var(--danger);
    }}

    .status-chip.warning {{
      background: rgba(169, 106, 36, 0.12);
      color: var(--amber);
    }}

    .status-chip.healthy {{
      background: rgba(47, 106, 70, 0.1);
      color: var(--green-800);
    }}

    .simple-table {{
      width: 100%;
      border-collapse: collapse;
    }}

    .simple-table th,
    .simple-table td {{
      padding: 12px 14px;
      border-bottom: 1px solid rgba(40, 68, 53, 0.08);
      text-align: left;
      vertical-align: top;
      font-size: 0.9rem;
    }}

    .simple-table th {{
      background: #f2f7ef;
      color: var(--green-900);
      font-size: 0.77rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .tag-list {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}

    .tag {{
      display: inline-flex;
      align-items: center;
      padding: 5px 8px;
      border-radius: 999px;
      background: rgba(47, 106, 70, 0.08);
      color: var(--green-800);
      font-size: 0.78rem;
      font-weight: 700;
    }}

    .tag.alert {{
      background: rgba(155, 70, 56, 0.12);
      color: var(--danger);
    }}

    .footnote {{
      margin-top: 12px;
      color: var(--muted);
      font-size: 0.84rem;
      line-height: 1.5;
    }}

    @media (max-width: 1180px) {{
      .hero {{
        grid-template-columns: 1fr;
      }}

      .kpi-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}

      .insights-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}

      .filters-grid {{
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }}

      .metric-strip {{
        grid-template-columns: 1fr;
      }}
    }}

    @media (max-width: 980px) {{
      .span-8,
      .span-7,
      .span-6,
      .span-5,
      .span-4 {{
        grid-column: span 12;
      }}

      .quality-grid {{
        grid-template-columns: 1fr;
      }}
    }}

    @media (max-width: 860px) {{
      .page {{
        padding: 18px 14px 34px;
      }}

      .hero {{
        padding: 22px 18px;
        border-radius: 22px;
      }}

      .aside-kpis,
      .kpi-grid,
      .filters-grid {{
        grid-template-columns: 1fr;
      }}

      .insights-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}

      .tab-bar {{
        width: 100%;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        border-radius: 22px;
      }}

      .section-title {{
        align-items: flex-start;
        flex-direction: column;
      }}

      .desktop-table {{
        display: none;
      }}

      .mobile-cards {{
        display: grid;
      }}

      .results-meta {{
        flex-direction: column;
        align-items: flex-start;
      }}
    }}

    @media (max-width: 640px) {{
      .page {{
        padding: 14px 12px 28px;
      }}

      .hero {{
        gap: 16px;
        padding: 18px 16px;
      }}

      .eyebrow {{
        font-size: 11px;
        padding: 7px 10px;
      }}

      h1 {{
        margin: 12px 0 8px;
        font-size: 1.95rem;
      }}

      .subtitle {{
        font-size: 0.94rem;
        line-height: 1.52;
      }}

      .hero-meta {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-top: 16px;
      }}

      .chip {{
        min-height: 46px;
        padding: 10px 12px;
        font-size: 0.84rem;
        align-items: flex-start;
      }}

      #source-chip {{
        display: none;
      }}

      .summary-list {{
        gap: 10px;
        margin-top: 18px;
      }}

      .summary-item {{
        font-size: 0.92rem;
        line-height: 1.48;
      }}

      .hero-aside {{
        gap: 10px;
      }}

      .aside-card {{
        padding: 14px;
        border-radius: 18px;
      }}

      .auth-actions {{
        flex-direction: column;
        align-items: stretch;
      }}

      .button-row {{
        grid-template-columns: 1fr;
      }}

      .ghost-button {{
        width: 100%;
        min-height: 50px;
      }}

      .aside-kpis {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
      }}

      .mini-stat {{
        padding: 12px;
      }}

      .mini-stat .value {{
        font-size: 1.15rem;
      }}

      .kpi-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
      }}

      .kpi-card {{
        min-height: unset;
        padding: 16px 14px;
        gap: 10px;
      }}

      .icon-box {{
        width: 40px;
        height: 40px;
      }}

      .kpi-label {{
        font-size: 0.76rem;
      }}

      .kpi-value {{
        font-size: 1.55rem;
      }}

      .kpi-foot {{
        font-size: 0.84rem;
        line-height: 1.38;
      }}

      .section-title {{
        margin: 24px 0 12px;
      }}

      .section-title h2 {{
        font-size: 1.5rem;
      }}

      .section-title p,
      .section-badge {{
        font-size: 0.88rem;
      }}

      .panel-grid {{
        gap: 12px;
      }}

      .panel {{
        padding: 14px;
        border-radius: 18px;
      }}

      .panel-header {{
        flex-direction: column;
        margin-bottom: 12px;
      }}

      .panel-title {{
        font-size: 0.98rem;
      }}

      .panel-subtitle {{
        font-size: 0.86rem;
        line-height: 1.42;
      }}

      .panel-note {{
        width: 100%;
      }}

      .rank-item {{
        padding: 12px;
      }}

      .rank-top {{
        flex-direction: column;
        align-items: flex-start;
      }}

      .rank-value {{
        text-align: left;
      }}

      .rank-secondary {{
        font-size: 0.82rem;
        line-height: 1.45;
      }}

      .quality-card {{
        padding: 14px;
      }}

      .quality-card .value {{
        font-size: 1.55rem;
      }}

      .insights-grid {{
        grid-template-columns: 1fr;
        gap: 12px;
      }}

      .insight-card {{
        min-height: unset;
        padding: 14px;
      }}

      .filters-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}

      .history-toolbar {{
        flex-direction: column;
        align-items: stretch;
      }}

      .filters-card {{
        padding: 14px;
      }}

      .field input,
      .field select {{
        min-height: 48px;
      }}

      .results-meta {{
        gap: 6px;
        font-size: 0.86rem;
      }}

      .mobile-cards {{
        gap: 10px;
      }}

      .mobile-card {{
        padding: 14px;
      }}
    }}

    @media (max-width: 480px) {{
      h1 {{
        font-size: 1.78rem;
      }}

      .kpi-card,
      .panel,
      .insight-card,
      .filters-card {{
        border-radius: 18px;
      }}

      .hero-meta,
      .kpi-grid,
      .filters-grid,
      .aside-kpis,
      .metric-strip {{
        grid-template-columns: 1fr;
      }}

      #updated-chip {{
        display: none;
      }}

      .eyebrow,
      .section-badge,
      .pill {{
        width: 100%;
        justify-content: center;
        text-align: center;
      }}

      .summary-item {{
        padding-left: 16px;
      }}

      .summary-item::before {{
        top: 9px;
      }}

      .mobile-head {{
        flex-direction: column;
      }}

      .mobile-grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <div class="hero-block">
        <span class="eyebrow">Reciclean · Economía Circular · Operación mensual</span>
        <h1 id="hero-title"></h1>
        <p class="subtitle" id="hero-subtitle"></p>
        <div class="hero-meta">
          <label class="chip chip-select" for="global-period-select">
            <span class="chip-select-label">Mes analizado:</span>
            <select id="global-period-select" aria-label="Mes analizado"></select>
          </label>
          <label class="chip chip-select" for="global-branch-select">
            <span class="chip-select-label">Vista sucursal:</span>
            <select id="global-branch-select" aria-label="Vista sucursal"></select>
          </label>
          <span class="chip" id="source-chip"></span>
          <span class="chip" id="updated-chip"></span>
        </div>
        <ul class="summary-list" id="summary-list"></ul>
      </div>
      <aside class="hero-aside">
        <div class="aside-card">
          <div class="auth-actions">
            <div class="auth-copy">
              <span class="auth-label">Acceso privado</span>
              <span class="auth-description">Sesión activa para visualización interna del dashboard.</span>
            </div>
            <div class="button-row">
              <button type="button" class="ghost-button" id="export-pdf-button">Exportar PDF</button>
              <button type="button" class="ghost-button" id="export-excel-button">Exportar Excel</button>
              <button type="button" class="ghost-button" id="logout-button">Cerrar sesión</button>
            </div>
            <div class="action-status" id="action-status" data-tone="default"></div>
          </div>
        </div>
        <div class="aside-card">
          <strong>Vista rápida de cobertura</strong>
          <div class="aside-kpis">
            <div class="mini-stat">
              <div class="value" id="meta-records"></div>
              <div class="label">registros del período</div>
            </div>
            <div class="mini-stat">
              <div class="value" id="meta-clients"></div>
              <div class="label">clientes activos</div>
            </div>
            <div class="mini-stat">
              <div class="value" id="meta-branches"></div>
              <div class="label">sucursales con actividad</div>
            </div>
            <div class="mini-stat">
              <div class="value" id="meta-services"></div>
              <div class="label">servicios presentes</div>
            </div>
          </div>
        </div>
        <div class="aside-card">
          <strong>Identidad operativa Reciclean</strong>
          <div class="pill">Compra · Retiro · Recepción · Certificación</div>
          <div class="pill">Cartón · Papel · Plásticos · Films · Vidrio · Metales</div>
          <div class="pill">Santiago · Talca · Gestión de materiales valorizables</div>
        </div>
      </aside>
    </section>

    <nav class="tab-bar" aria-label="Secciones del dashboard">
      <button type="button" class="tab-button is-active" data-tab-target="resumen">Resumen Ejecutivo</button>
      <button type="button" class="tab-button" data-tab-target="historico">Histórico y Tendencias</button>
      <button type="button" class="tab-button" data-tab-target="riesgos">Riesgos e Inconsistencias</button>
      <button type="button" class="tab-button" data-tab-target="calidad">Calidad y Brechas</button>
    </nav>

    <div id="print-root" aria-hidden="true"></div>

    <section class="tab-pane is-active" data-tab-pane="resumen">
    <section class="kpi-grid" id="kpi-grid"></section>

    <div class="section-title">
      <div>
        <h2>Desempeño operacional</h2>
        <p>Seguimiento de volumen, valorización, mix de servicio y desempeño comercial del mes.</p>
      </div>
      <div class="section-badge">Lectura orientada a gerencia comercial y operaciones</div>
    </div>

    <section class="panel-grid">
      <article class="panel span-6">
        <div class="panel-header">
          <div>
            <h3 class="panel-title">Evolución diaria de registros</h3>
            <p class="panel-subtitle">Comportamiento diario del flujo operativo de vales durante el mes.</p>
          </div>
        </div>
        <div id="daily-records-chart" class="chart-shell"></div>
      </article>

      <article class="panel span-6">
        <div class="panel-header">
          <div>
            <h3 class="panel-title">Evolución diaria de monto</h3>
            <p class="panel-subtitle">Valorización diaria consolidada del período en pesos chilenos.</p>
          </div>
        </div>
        <div id="daily-amount-chart" class="chart-shell"></div>
      </article>

      <article class="panel span-4">
        <div class="panel-header">
          <div>
            <h3 class="panel-title">Mix por tipo de servicio</h3>
            <p class="panel-subtitle">Distribución por monto valorizado y registros asociados.</p>
          </div>
        </div>
        <div id="services-list" class="rank-list"></div>
      </article>

      <article class="panel span-4">
        <div class="panel-header">
          <div>
            <h3 class="panel-title">Ranking de sucursales</h3>
            <p class="panel-subtitle">Comparativo de monto con contexto del número de registros.</p>
          </div>
        </div>
        <div id="branches-list" class="rank-list"></div>
      </article>

      <article class="panel span-4">
        <div class="panel-header">
          <div>
            <h3 class="panel-title">Transporte utilizado</h3>
            <p class="panel-subtitle">Uso de modalidad de transporte según registros del mes.</p>
          </div>
        </div>
        <div id="transport-list" class="rank-list"></div>
      </article>

      <article class="panel span-7">
        <div class="panel-header">
          <div>
            <h3 class="panel-title">Ranking de clientes</h3>
            <p class="panel-subtitle">Clientes con mayor valorización en el período analizado.</p>
          </div>
          <span class="panel-note">Top 8 por monto</span>
        </div>
        <div id="clients-list" class="rank-list"></div>
      </article>

      <article class="panel span-5">
        <div class="panel-header">
          <div>
            <h3 class="panel-title">Mix por familia de material</h3>
            <p class="panel-subtitle">Clasificación inferida a partir de la descripción real de materiales del Excel.</p>
          </div>
          <span class="panel-note">Excluye vacíos de material</span>
        </div>
        <div id="families-list" class="rank-list"></div>
      </article>

      <article class="panel span-6">
        <div class="panel-header">
          <div>
            <h3 class="panel-title">Materiales más relevantes</h3>
            <p class="panel-subtitle">Peso estimado por material identificado en la descripción del registro.</p>
          </div>
          <span class="panel-note">Top 8 por peso</span>
        </div>
        <div id="materials-list" class="rank-list"></div>
        <p class="footnote">Cuando una celda combina varios materiales separados por “|”, el peso y el monto se prorratean entre los ítems identificados para no inflar el mix.</p>
      </article>

      <article class="panel span-6">
        <div class="panel-header">
          <div>
            <h3 class="panel-title">Calidad de dato e integridad</h3>
            <p class="panel-subtitle">Brechas relevantes para lectura gerencial, control operativo y trazabilidad.</p>
          </div>
        </div>
        <div class="quality-grid" id="quality-cards"></div>
        <div id="quality-list" class="rank-list"></div>
        <div id="alerts-list" class="alerts"></div>
      </article>
    </section>

    <div class="section-title">
      <div>
        <h2>Insights automáticos</h2>
        <p>Conclusiones ejecutivas generadas desde la data procesada del Excel mensual.</p>
      </div>
      <div class="section-badge">Resumen corto, accionable y legible</div>
    </div>

    <section class="insights-grid" id="insights-grid"></section>

    <div class="section-title">
      <div>
        <h2>Detalle operativo</h2>
        <p>Filtra por sucursal, servicio, cliente o fecha y revisa el detalle completo del mes.</p>
      </div>
      <div class="section-badge">Tabla usable en desktop y versión tarjeta en móvil</div>
    </div>

    <section class="filters-card">
      <div class="filters-grid">
        <div class="field">
          <label for="filter-search">Buscador</label>
          <input id="filter-search" type="search" placeholder="Cliente, material, folio o ciudad" />
        </div>
        <div class="field">
          <label for="filter-branch">Sucursal</label>
          <select id="filter-branch"></select>
        </div>
        <div class="field">
          <label for="filter-service">Servicio</label>
          <select id="filter-service"></select>
        </div>
        <div class="field">
          <label for="filter-client">Cliente</label>
          <select id="filter-client"></select>
        </div>
        <div class="field">
          <label for="filter-from">Fecha desde</label>
          <input id="filter-from" type="date" />
        </div>
        <div class="field">
          <label for="filter-to">Fecha hasta</label>
          <input id="filter-to" type="date" />
        </div>
      </div>

      <div class="results-meta">
        <div id="results-count"></div>
        <div id="results-amount"></div>
      </div>

      <div id="table-output">
        <div class="desktop-table">
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Folio</th>
                  <th>Cliente</th>
                  <th>Sucursal</th>
                  <th>Servicio</th>
                  <th>Transporte</th>
                  <th>Material</th>
                  <th>Peso final</th>
                  <th>Monto</th>
                  <th>Ciudad</th>
                </tr>
              </thead>
              <tbody id="detail-table-body"></tbody>
            </table>
          </div>
        </div>
        <div id="mobile-cards" class="mobile-cards"></div>
      </div>
    </section>
    </section>

    <section class="tab-pane" data-tab-pane="historico">
      <div class="section-title">
        <div>
          <h2>Histórico y Tendencias</h2>
          <p>Comparativo mensual, evolución consolidada y lectura comercial del rango seleccionado.</p>
        </div>
        <div class="section-badge">Base actual: datos accesibles del Excel vigente</div>
      </div>

      <section class="filters-card">
        <div class="history-toolbar">
          <div>
            <strong style="display:block; font-size:1rem;">Comparativo mensual</strong>
            <span class="footnote" id="history-caption"></span>
          </div>
          <div class="field" style="min-width: 240px;">
            <label for="history-range-select">Rango histórico</label>
            <select id="history-range-select"></select>
          </div>
        </div>
        <div class="metric-strip" id="history-delta-cards"></div>
      </section>

      <section class="panel-grid">
        <article class="panel span-7">
          <div class="panel-header">
            <div>
              <h3 class="panel-title">Evolución mensual de monto</h3>
              <p class="panel-subtitle">Comportamiento del valor valorizado según el rango histórico activo.</p>
            </div>
          </div>
          <div id="monthly-amount-chart" class="chart-shell"></div>
        </article>

        <article class="panel span-5">
          <div class="panel-header">
            <div>
              <h3 class="panel-title">Resumen mensual</h3>
              <p class="panel-subtitle">Monto, kilos y registros por mes dentro del rango comparado.</p>
            </div>
          </div>
          <div class="table-wrap">
            <table class="simple-table">
              <thead>
                <tr>
                  <th>Mes</th>
                  <th>Monto</th>
                  <th>Kilos</th>
                  <th>Registros</th>
                </tr>
              </thead>
              <tbody id="monthly-summary-body"></tbody>
            </table>
          </div>
        </article>

        <article class="panel span-12">
          <div class="panel-header">
            <div>
              <h3 class="panel-title">Clientes inactivos 30+ días</h3>
              <p class="panel-subtitle">Clientes visibles en meses previos que no aparecen en el mes seleccionado.</p>
            </div>
          </div>
          <div class="table-wrap">
            <table class="simple-table">
              <thead>
                <tr>
                  <th>Cliente</th>
                  <th>Última visita</th>
                  <th>Días sin venir</th>
                  <th>Monto previo</th>
                  <th>Visitas previas</th>
                </tr>
              </thead>
              <tbody id="inactive-clients-body"></tbody>
            </table>
          </div>
        </article>

        <article class="panel span-12">
          <div class="panel-header">
            <div>
              <h3 class="panel-title">Patrones y cambios de comportamiento</h3>
              <p class="panel-subtitle">Señales ejecutivas de cambio en frecuencia, kilos, monto y material dominante por cliente.</p>
            </div>
          </div>
          <div class="metric-strip" id="behavior-summary-cards"></div>
          <div class="footnote" id="behavior-window-note"></div>
          <div class="table-wrap" style="margin-top: 14px;">
            <table class="simple-table">
              <thead>
                <tr>
                  <th>Cliente</th>
                  <th>Tendencia</th>
                  <th>Visitas</th>
                  <th>Kilos</th>
                  <th>Monto</th>
                  <th>Material dominante</th>
                  <th>Cambio detectado</th>
                  <th>Nivel</th>
                </tr>
              </thead>
              <tbody id="behavior-table-body"></tbody>
            </table>
          </div>
        </article>
      </section>
    </section>

    <section class="tab-pane" data-tab-pane="riesgos">
      <div class="section-title">
        <div>
          <h2>Riesgos e Inconsistencias</h2>
          <p>Lectura de inventario derivado, concentración y alertas automáticas detectables desde la data actual.</p>
        </div>
        <div class="section-badge">Versión 1 sin modificar el Excel original</div>
      </div>

      <section class="filters-card">
        <div class="metric-strip" id="risk-concentration-cards"></div>
      </section>

      <section class="panel-grid">
        <article class="panel span-6">
          <div class="panel-header">
            <div>
              <h3 class="panel-title">Inventario derivado por material</h3>
              <p class="panel-subtitle">Suma peso en compras y resta peso en ventas para detectar stock teórico y descuadres.</p>
            </div>
          </div>
          <div class="table-wrap">
            <table class="simple-table">
              <thead>
                <tr>
                  <th>Material</th>
                  <th>Comprado kg</th>
                  <th>Vendido kg</th>
                  <th>Stock teórico kg</th>
                </tr>
              </thead>
              <tbody id="stock-table-body"></tbody>
            </table>
          </div>
        </article>

        <article class="panel span-6">
          <div class="panel-header">
            <div>
              <h3 class="panel-title">Registros con alerta</h3>
              <p class="panel-subtitle">Outliers V1 y patrones sospechosos detectados en el mes activo.</p>
            </div>
            <span class="panel-note" id="outlier-count-note"></span>
          </div>
          <div class="table-wrap">
            <table class="simple-table">
              <thead>
                <tr>
                  <th>Folio</th>
                  <th>Fecha</th>
                  <th>Cliente</th>
                  <th>Monto</th>
                  <th>Alertas</th>
                </tr>
              </thead>
              <tbody id="outliers-table-body"></tbody>
            </table>
          </div>
        </article>
      </section>
    </section>

    <section class="tab-pane" data-tab-pane="calidad">
      <div class="section-title">
        <div>
          <h2>Calidad y Brechas</h2>
          <p>Completitud por sucursal y focos concretos a corregir esta semana, ordenados por impacto.</p>
        </div>
        <div class="section-badge">Priorización operativa sobre campos críticos</div>
      </div>

      <section class="panel-grid">
        <article class="panel span-12">
          <div class="panel-header">
            <div>
              <h3 class="panel-title">Calidad del dato por sucursal</h3>
              <p class="panel-subtitle">Porcentaje de completitud de campos críticos para cada sucursal del período activo.</p>
            </div>
          </div>
          <div class="table-wrap">
            <table class="simple-table">
              <thead id="quality-branch-head"></thead>
              <tbody id="quality-branch-body"></tbody>
            </table>
          </div>
        </article>

        <article class="panel span-12">
          <div class="panel-header">
            <div>
              <h3 class="panel-title">Brechas a corregir esta semana</h3>
              <p class="panel-subtitle">Top 20 registros con campos críticos vacíos, ordenados por monto descendente.</p>
            </div>
          </div>
          <div class="table-wrap">
            <table class="simple-table">
              <thead>
                <tr>
                  <th>Folio</th>
                  <th>Fecha</th>
                  <th>Cliente</th>
                  <th>Sucursal</th>
                  <th>Servicio</th>
                  <th>Monto</th>
                  <th>Campos faltantes</th>
                </tr>
              </thead>
              <tbody id="gaps-table-body"></tbody>
            </table>
          </div>
        </article>
      </section>
    </section>
  </main>

  <script>
    const DATA = {json.dumps(data, ensure_ascii=False)};
    const VIEWS = DATA.viewsByPeriod;
    let activeTab = 'resumen';
    let activePeriod = DATA.defaultPeriod;
    let activeBranch = DATA.defaultBranch;
    let activeHistoryRange = '3m';
    const TABLE_ROWS = DATA.compact.rows.map(row => {{
      const [periodKey, fecha, folio, cliente, sucursal, servicio, transporte, material, pesoKg, monto, ciudad, origenDestino] = row;
      const fechaDate = new Date(`${{fecha}}T00:00:00`);
      const fechaLabel = `${{String(fechaDate.getDate()).padStart(2, '0')}}/${{String(fechaDate.getMonth() + 1).padStart(2, '0')}}/${{fechaDate.getFullYear()}}`;
      return {{
        periodKey,
        fecha,
        fechaLabel,
        folio,
        cliente: DATA.compact.lookups.clients[cliente],
        sucursal: DATA.compact.lookups.branches[sucursal],
        servicio: DATA.compact.lookups.services[servicio],
        transporte: DATA.compact.lookups.transports[transporte],
        material: DATA.compact.lookups.materials[material],
        pesoKg,
        monto,
        ciudad: DATA.compact.lookups.cities[ciudad],
        origenDestino: DATA.compact.lookups.origins[origenDestino]
      }};
    }});

    const iconPaths = {{
      records: '<path d="M6 7.5h12M6 12h12M6 16.5h8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><rect x="4" y="4" width="16" height="16" rx="4" stroke="currentColor" stroke-width="1.4" fill="none"/>',
      amount: '<path d="M12 4v16M16 7.5c0-1.8-1.8-3.2-4-3.2s-4 1.4-4 3.2 1.5 2.8 4 3.3 4 1.4 4 3.3-1.8 3.2-4 3.2-4-1.4-4-3.2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" fill="none"/>',
      weight: '<path d="M7 9.5h10l1.4 8.5H5.6L7 9.5Z" stroke="currentColor" stroke-width="1.6" fill="none"/><path d="M9.5 9.5a2.5 2.5 0 1 1 5 0" stroke="currentColor" stroke-width="1.6" fill="none"/><path d="M12 12.3v2.8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
      ticket: '<path d="M5 8.5h14v7H5z" stroke="currentColor" stroke-width="1.5" fill="none"/><path d="M8 6.5V10M16 6.5V10M8 14.5V18M16 14.5V18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="12" cy="12" r="1.6" fill="currentColor"/>',
      peak: '<path d="M5 18.5h14" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M8 15l3-4 2.5 2.5L18 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M16.5 8H18v1.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" fill="none"/>',
      branch: '<path d="M4.5 18.5h15" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M7 18V7l5-3 5 3v11" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linejoin="round"/><path d="M10 11.5h4M10 14.5h4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>',
      service: '<path d="M4.5 16.5 8 10l3.2 2.8L15.8 6l3.7 2.8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" fill="none"/><circle cx="8" cy="10" r="1.4" fill="currentColor"/><circle cx="15.8" cy="6" r="1.4" fill="currentColor"/>',
      quality: '<path d="M12 4l7 3v5.3c0 3.6-2.3 6.9-7 7.7-4.7-.8-7-4.1-7-7.7V7l7-3Z" stroke="currentColor" stroke-width="1.5" fill="none"/><path d="m9.2 11.8 1.8 1.8 3.8-4.2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
    }};

    function branchOptionsForCurrentPeriod() {{
      return DATA.branchOptionsByPeriod[activePeriod] || [DATA.defaultBranch];
    }}

    function normalizeActiveBranch() {{
      if (!branchOptionsForCurrentPeriod().includes(activeBranch)) {{
        activeBranch = DATA.defaultBranch;
      }}
    }}

    function currentView() {{
      normalizeActiveBranch();
      const periodViews = VIEWS[activePeriod] || VIEWS[DATA.defaultPeriod];
      return periodViews[activeBranch] || periodViews[DATA.defaultBranch];
    }}

    function currentMeta() {{
      return currentView().meta;
    }}

    function currentHistory() {{
      return DATA.historicalByPeriod[activePeriod] || DATA.historicalByPeriod[DATA.defaultPeriod];
    }}

    function currentRisk() {{
      return DATA.riskByPeriod[activePeriod] || DATA.riskByPeriod[DATA.defaultPeriod];
    }}

    function currentQualityTab() {{
      return DATA.qualityByPeriod[activePeriod] || DATA.qualityByPeriod[DATA.defaultPeriod];
    }}

    const kpiDefinitions = [
      {{
        key: 'totalRecords',
        label: 'Total de registros',
        icon: 'records',
        value: () => formatInteger(currentView().kpis.totalRecords),
        foot: () => `${{formatInteger(currentMeta().clientCount)}} clientes únicos en el período`
      }},
      {{
        key: 'totalAmount',
        label: 'Monto total valorizado',
        icon: 'amount',
        value: () => formatCompactCurrency(currentView().kpis.totalAmount),
        foot: () => `CLP ${{formatCurrency(currentView().kpis.totalAmount)}} acumulados`
      }},
      {{
        key: 'totalWeightKg',
        label: 'Peso total',
        icon: 'weight',
        value: () => `${{formatOneDecimal(currentView().kpis.totalWeightKg / 1000)}} t`,
        foot: () => `${{formatInteger(Math.round(currentView().kpis.totalWeightKg))}} kg con dato de peso`
      }},
      {{
        key: 'avgTicket',
        label: 'Ticket promedio',
        icon: 'ticket',
        value: () => formatCompactCurrency(currentView().kpis.avgTicket),
        foot: () => `Promedio por registro del mes`
      }},
      {{
        key: 'avgWeightKg',
        label: 'Peso promedio',
        icon: 'weight',
        value: () => `${{formatInteger(Math.round(currentView().kpis.avgWeightKg))}} kg`,
        foot: () => `Calculado sobre ${{formatInteger(currentView().kpis.weightRecords)}} registros con peso`
      }},
      {{
        key: 'peakDayLabel',
        label: 'Día de mayor monto',
        icon: 'peak',
        value: () => currentView().kpis.peakDayLabel,
        foot: () => `CLP ${{formatCurrency(currentView().kpis.peakDayAmount)}}`
      }},
      {{
        key: 'leaderBranch',
        label: 'Sucursal líder',
        icon: 'branch',
        value: () => currentView().kpis.leaderBranch,
        foot: () => `${{formatPercent(currentView().kpis.leaderBranchShare)}} del monto mensual`
      }},
      {{
        key: 'dominantService',
        label: 'Servicio dominante',
        icon: 'service',
        value: () => currentView().kpis.dominantService,
        foot: () => `${{formatPercent(currentView().kpis.dominantServiceShare)}} del monto mensual`
      }}
    ];

    function formatInteger(value) {{
      return new Intl.NumberFormat('es-CL', {{ maximumFractionDigits: 0 }}).format(value);
    }}

    function formatCurrency(value) {{
      return new Intl.NumberFormat('es-CL', {{ maximumFractionDigits: 0 }}).format(Math.round(value || 0));
    }}

    function formatCompactCurrency(value) {{
      const numeric = Number(value || 0);
      if (Math.abs(numeric) >= 1_000_000) {{
        return `CLP ${{new Intl.NumberFormat('es-CL', {{ minimumFractionDigits: 1, maximumFractionDigits: 1 }}).format(numeric / 1_000_000)}} M`;
      }}
      if (Math.abs(numeric) >= 1_000) {{
        return `CLP ${{new Intl.NumberFormat('es-CL', {{ minimumFractionDigits: 1, maximumFractionDigits: 1 }}).format(numeric / 1_000)}} mil`;
      }}
      return `CLP ${{formatCurrency(numeric)}}`;
    }}

    function formatOneDecimal(value) {{
      return new Intl.NumberFormat('es-CL', {{ minimumFractionDigits: 1, maximumFractionDigits: 1 }}).format(Number(value || 0));
    }}

    function formatPercent(value) {{
      return `${{new Intl.NumberFormat('es-CL', {{ minimumFractionDigits: 1, maximumFractionDigits: 1 }}).format(Number(value || 0))}}%`;
    }}

    function formatWeight(value) {{
      const numeric = Number(value || 0);
      if (numeric >= 1000) {{
        return `${{formatOneDecimal(numeric / 1000)}} t`;
      }}
      return `${{formatInteger(Math.round(numeric))}} kg`;
    }}

    function iconMarkup(name) {{
      return `
        <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" focusable="false">
          ${{iconPaths[name] || ''}}
        </svg>
      `;
    }}

    function fillHero() {{
      const view = currentView();
      const meta = currentMeta();
      document.getElementById('hero-title').textContent = DATA.meta.title;
      document.getElementById('hero-subtitle').textContent = DATA.meta.subtitle;
      document.getElementById('source-chip').textContent = `Fuente: ${{DATA.meta.sourceFile}}`;
      document.getElementById('updated-chip').textContent = `Actualizado: ${{DATA.meta.updatedAt}}`;
      document.getElementById('meta-records').textContent = formatInteger(meta.recordCount);
      document.getElementById('meta-clients').textContent = formatInteger(meta.clientCount);
      document.getElementById('meta-branches').textContent = formatInteger(meta.branchCount);
      document.getElementById('meta-services').textContent = formatInteger(meta.serviceCount);
      document.getElementById('summary-list').innerHTML = view.summary
        .map(item => `<li class="summary-item">${{item}}</li>`)
        .join('');
    }}

    function renderKpis() {{
      const root = document.getElementById('kpi-grid');
      root.innerHTML = kpiDefinitions.map(card => `
        <article class="kpi-card">
          <div class="kpi-head">
            <div class="kpi-label">${{card.label}}</div>
            <div class="icon-box">${{iconMarkup(card.icon)}}</div>
          </div>
          <div class="kpi-value">${{card.value()}}</div>
          <div class="kpi-foot">${{card.foot()}}</div>
        </article>
      `).join('');
    }}

    function renderAreaChart(targetId, series, formatter, legendLabel) {{
      const root = document.getElementById(targetId);
      const width = root.clientWidth || 560;
      const compact = width <= 430;
      const svgWidth = 640;
      const svgHeight = compact ? 236 : 268;
      const margin = {{ top: 18, right: 14, bottom: compact ? 36 : 42, left: compact ? 46 : 64 }};
      const maxValue = Math.max(...series.map(item => Number(item.value || 0)), 1);
      const innerWidth = svgWidth - margin.left - margin.right;
      const innerHeight = svgHeight - margin.top - margin.bottom;
      const stepX = series.length > 1 ? innerWidth / (series.length - 1) : innerWidth;
      const y = value => margin.top + innerHeight - (Number(value || 0) / maxValue) * innerHeight;
      const x = index => margin.left + index * stepX;
      const path = series.map((item, index) => `${{index === 0 ? 'M' : 'L'}}${{x(index).toFixed(2)}},${{y(item.value).toFixed(2)}}`).join(' ');
      const area = `${{path}} L ${{x(series.length - 1).toFixed(2)}},${{(margin.top + innerHeight).toFixed(2)}} L ${{x(0).toFixed(2)}},${{(margin.top + innerHeight).toFixed(2)}} Z`;
      const ticks = 4;
      const yTicks = Array.from({{ length: ticks + 1 }}, (_, index) => {{
        const value = maxValue * (1 - index / ticks);
        return {{ value, y: margin.top + innerHeight * (index / ticks) }};
      }});
      const labelStep = compact ? Math.ceil(series.length / 4) : Math.ceil(series.length / 7);

      root.innerHTML = `
        <svg viewBox="0 0 ${{svgWidth}} ${{svgHeight}}" width="100%" role="img" aria-label="${{legendLabel}}">
          <defs>
            <linearGradient id="${{targetId}}-fill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stop-color="rgba(63, 134, 84, 0.32)"></stop>
              <stop offset="100%" stop-color="rgba(63, 134, 84, 0.02)"></stop>
            </linearGradient>
          </defs>
          ${{yTicks.map(tick => `
            <g>
              <line x1="${{margin.left}}" x2="${{svgWidth - margin.right}}" y1="${{tick.y}}" y2="${{tick.y}}" stroke="rgba(40, 68, 53, 0.08)" stroke-dasharray="4 6"></line>
              <text x="${{margin.left - 10}}" y="${{tick.y + 4}}" font-size="${{compact ? 10 : 11}}" fill="rgba(104, 123, 110, 0.95)" text-anchor="end">${{formatter(tick.value)}}</text>
            </g>
          `).join('')}}
          <path d="${{area}}" fill="url(#${{targetId}}-fill)"></path>
          <path d="${{path}}" fill="none" stroke="var(--green-700)" stroke-width="${{compact ? 2.4 : 2.8}}" stroke-linecap="round" stroke-linejoin="round"></path>
          ${{series.map((item, index) => `
            <circle cx="${{x(index)}}" cy="${{y(item.value)}}" r="${{compact ? 3.3 : 4.2}}" fill="#fff" stroke="var(--green-700)" stroke-width="2"></circle>
          `).join('')}}
          ${{series.map((item, index) => index % labelStep === 0 || index === series.length - 1 ? `
            <text x="${{x(index)}}" y="${{svgHeight - 12}}" font-size="${{compact ? 10 : 11}}" fill="rgba(104, 123, 110, 0.95)" text-anchor="middle">${{item.label}}</text>
          ` : '').join('')}}
        </svg>
        <div class="chart-legend"><span><span class="legend-dot"></span>${{legendLabel}}</span></div>
      `;
    }}

    function renderRankList(targetId, items, formatter) {{
      const root = document.getElementById(targetId);
      const maxValue = Math.max(...items.map(item => Number(item.value || 0)), 1);
      root.innerHTML = items.map(item => `
        <div class="rank-item">
          <div class="rank-top">
            <div class="rank-label">${{item.label}}</div>
            <div class="rank-value">${{formatter(item.value)}}</div>
          </div>
          <div class="bar-track"><div class="bar-fill" style="width:${{Math.max(6, (Number(item.value || 0) / maxValue) * 100)}}%"></div></div>
          <div class="rank-secondary">${{item.secondary}} · ${{formatPercent(item.share)}}</div>
        </div>
      `).join('');
    }}

    function renderQuality() {{
      const quality = currentView().quality;
      document.getElementById('quality-cards').innerHTML = `
        <div class="quality-card">
          <div class="value">${{formatPercent(quality.completenessScore)}}</div>
          <div class="label">Completitud promedio de campos críticos</div>
        </div>
        <div class="quality-card">
          <div class="value">${{formatInteger(quality.weightMissing)}}</div>
          <div class="label">Registros sin peso final informado</div>
        </div>
        <div class="quality-card">
          <div class="value">${{formatInteger(quality.materialMissing)}}</div>
          <div class="label">Registros sin material identificado</div>
        </div>
      `;

      renderRankList(
        'quality-list',
        quality.metrics.map(item => ({{
          label: item.label,
          value: item.missingRate,
          secondary: `${{formatInteger(item.missingCount)}} vacíos`,
          share: item.missingRate
        }})),
        value => `${{formatPercent(value)}}`
      );

      const alertsRoot = document.getElementById('alerts-list');
      alertsRoot.innerHTML = quality.alerts.length
        ? quality.alerts.map(alert => `<div class="alert-item">${{alert}}</div>`).join('')
        : `<div class="alert-item">No se detectaron alertas significativas de concentración ni vacíos críticos.</div>`;
    }}

    function renderInsights() {{
      document.getElementById('insights-grid').innerHTML = currentView().insights.map((item, index) => `
        <article class="insight-card">
          <div class="icon-box">${{iconMarkup(['branch', 'service', 'amount', 'weight', 'quality'][index] || 'records')}}</div>
          <h3>${{item.title}}</h3>
          <p>${{item.body}}</p>
        </article>
      `).join('');
    }}

    function historyRangeConfig() {{
      return DATA.historyRangeOptions.find(item => item.value === activeHistoryRange) || DATA.historyRangeOptions[1];
    }}

    function filteredMonthlyHistory() {{
      const monthly = currentHistory().monthly || [];
      if (activeHistoryRange === 'ytd') {{
        const activeYear = activePeriod.slice(0, 4);
        return monthly.filter(item => item.key.startsWith(activeYear));
      }}
      const months = historyRangeConfig().months || monthly.length;
      return monthly.slice(Math.max(0, monthly.length - months));
    }}

    function formatDelta(value) {{
      if (value == null || Number.isNaN(value)) return 'Sin base';
      const signal = value > 0 ? '+' : '';
      return `${{signal}}${{new Intl.NumberFormat('es-CL', {{ minimumFractionDigits: 1, maximumFractionDigits: 1 }}).format(value)}}%`;
    }}

    function renderHistoricalTab() {{
      const history = currentHistory();
      const monthly = filteredMonthlyHistory();
      document.getElementById('history-caption').textContent = `Corte activo: ${{history.activeLabel}} · comparación contra ${{history.previousLabel}}`;

      const deltaCards = [
        {{
          label: 'Monto vs mes anterior',
          value: formatDelta(history.deltas.amountPct),
          foot: `Actual: CLP ${{formatCurrency(history.deltas.currentAmount)}} · previo: CLP ${{formatCurrency(history.deltas.previousAmount)}}`
        }},
        {{
          label: 'Kilos vs mes anterior',
          value: formatDelta(history.deltas.weightPct),
          foot: `Actual: ${{formatWeight(history.deltas.currentWeightKg)}} · previo: ${{formatWeight(history.deltas.previousWeightKg)}}`
        }},
        {{
          label: 'Registros vs mes anterior',
          value: formatDelta(history.deltas.recordsPct),
          foot: `Actual: ${{formatInteger(history.deltas.currentRecords)}} · previo: ${{formatInteger(history.deltas.previousRecords)}}`
        }}
      ];
      document.getElementById('history-delta-cards').innerHTML = deltaCards.map(card => `
        <article class="metric-pill">
          <div class="label">${{card.label}}</div>
          <div class="value">${{card.value}}</div>
          <div class="foot">${{card.foot}}</div>
        </article>
      `).join('');

      renderAreaChart(
        'monthly-amount-chart',
        monthly.map(item => ({{
          label: item.label.replace(' 2026', '').replace(' 2025', ''),
          date: item.key,
          value: item.amount
        }})),
        value => {{
          if (value >= 1_000_000) return `${{formatOneDecimal(value / 1_000_000)}}M`;
          if (value >= 1_000) return `${{formatInteger(Math.round(value / 1_000))}}k`;
          return formatInteger(Math.round(value));
        }},
        'Monto mensual en CLP'
      );

      document.getElementById('monthly-summary-body').innerHTML = monthly.map(item => `
        <tr>
          <td>${{item.label}}</td>
          <td class="money">CLP ${{formatCurrency(item.amount)}}</td>
          <td class="num">${{formatWeight(item.weightKg)}}</td>
          <td class="num">${{formatInteger(item.records)}}</td>
        </tr>
      `).join('');

      const inactiveRows = history.inactiveClients || [];
      document.getElementById('inactive-clients-body').innerHTML = inactiveRows.length
        ? inactiveRows.map(item => `
          <tr>
            <td>${{escapeHtml(item.client)}}</td>
            <td>${{item.lastVisit}}</td>
            <td class="num">${{formatInteger(item.daysInactive)}}</td>
            <td class="money">CLP ${{formatCurrency(item.amount)}}</td>
            <td class="num">${{formatInteger(item.visits)}}</td>
          </tr>
        `).join('')
        : `<tr><td colspan="5"><div class="empty-state">No se detectan clientes inactivos dentro de la ventana comparada.</div></td></tr>`;

      const behavior = history.behavior || {{ summary: [], rows: [], windowLabel: 'Sin base suficiente' }};
      document.getElementById('behavior-summary-cards').innerHTML = (behavior.summary || []).map(card => `
        <article class="metric-pill">
          <div class="label">${{card.label}}</div>
          <div class="value">${{formatInteger(card.value)}}</div>
          <div class="foot">${{card.foot}}</div>
        </article>
      `).join('');
      document.getElementById('behavior-window-note').textContent = behavior.windowLabel || 'Sin base suficiente para comparar comportamiento.';
      document.getElementById('behavior-table-body').innerHTML = (behavior.rows || []).length
        ? behavior.rows.map(item => `
          <tr>
            <td>${{escapeHtml(item.client)}}</td>
            <td>${{escapeHtml(item.trend)}}</td>
            <td class="num">${{formatInteger(item.visitsCurrent)}} vs ${{item.visitsBaselineAvg.toLocaleString('es-CL', {{ minimumFractionDigits: 1, maximumFractionDigits: 1 }})}}</td>
            <td class="num">${{formatWeight(item.weightCurrentKg)}} vs ${{formatWeight(item.weightBaselineAvgKg)}}</td>
            <td class="money">CLP ${{formatCurrency(item.amountCurrent)}} vs CLP ${{formatCurrency(item.amountBaselineAvg)}}</td>
            <td>${{escapeHtml(item.materialCurrent)}}${{item.materialBaseline !== item.materialCurrent ? `<div class="footnote">Antes: ${{escapeHtml(item.materialBaseline)}}</div>` : ''}}</td>
            <td><div class="tag-list">${{item.alerts.map(alert => `<span class="tag">${{escapeHtml(alert)}}</span>`).join('')}}</div></td>
            <td><span class="status-chip ${{item.severity}}">${{item.severity === 'critical' ? 'Alerta alta' : 'Seguimiento'}}</span></td>
          </tr>
        `).join('')
        : `<tr><td colspan="8"><div class="empty-state">No se detectan cambios relevantes de comportamiento con la ventana histórica actual.</div></td></tr>`;
    }}

    function renderRiskTab() {{
      const risk = currentRisk();
      document.getElementById('risk-concentration-cards').innerHTML = risk.concentration.map(item => `
        <article class="metric-pill">
          <div class="label">${{item.label}}</div>
          <div class="value">${{formatPercent(item.share)}}</div>
          <div class="foot">${{escapeHtml(item.subject)}}</div>
          <div class="status-chip ${{item.status}}">${{item.detail}}</div>
        </article>
      `).join('');

      document.getElementById('stock-table-body').innerHTML = risk.stockRows.length
        ? risk.stockRows.map(item => `
          <tr>
            <td>${{escapeHtml(item.material)}}</td>
            <td class="num">${{formatWeight(item.boughtKg)}}</td>
            <td class="num">${{formatWeight(item.soldKg)}}</td>
            <td class="num">${{item.flag ? `<span class="tag alert">${{formatWeight(item.netKg)}}</span>` : formatWeight(item.netKg)}}</td>
          </tr>
        `).join('')
        : `<tr><td colspan="4"><div class="empty-state">No hay suficiente dato de compra y venta con peso para calcular inventario derivado.</div></td></tr>`;

      document.getElementById('outlier-count-note').textContent = `${{formatInteger(risk.alertCount)}} alertas`;
      document.getElementById('outliers-table-body').innerHTML = risk.outliers.length
        ? risk.outliers.map(item => `
          <tr>
            <td class="num">${{formatInteger(item.folio)}}</td>
            <td>${{item.date}}</td>
            <td>${{escapeHtml(item.client)}}</td>
            <td class="money">CLP ${{formatCurrency(item.amount)}}</td>
            <td><div class="tag-list">${{item.alerts.map(alert => `<span class="tag alert">${{escapeHtml(alert)}}</span>`).join('')}}</div></td>
          </tr>
        `).join('')
        : `<tr><td colspan="5"><div class="empty-state">No se detectaron outliers con las reglas automáticas básicas para este período.</div></td></tr>`;
    }}

    function renderQualityTab() {{
      const quality = currentQualityTab();
      const head = document.getElementById('quality-branch-head');
      head.innerHTML = `
        <tr>
          <th>Sucursal</th>
          <th>Registros</th>
          ${{quality.fields.map(field => `<th>${{field.label}}</th>`).join('')}}
          <th>Promedio</th>
        </tr>
      `;

      document.getElementById('quality-branch-body').innerHTML = quality.branchMatrix.length
        ? quality.branchMatrix.map(row => `
          <tr>
            <td>${{escapeHtml(row.branch)}}</td>
            <td class="num">${{formatInteger(row.records)}}</td>
            ${{quality.fields.map(field => `<td class="num">${{formatPercent(row[field.key])}}</td>`).join('')}}
            <td class="num">${{formatPercent(row.avgCompleteness)}}</td>
          </tr>
        `).join('')
        : `<tr><td colspan="${{quality.fields.length + 3}}"><div class="empty-state">No hay información suficiente para construir la matriz de calidad.</div></td></tr>`;

      document.getElementById('gaps-table-body').innerHTML = quality.gaps.length
        ? quality.gaps.map(item => `
          <tr>
            <td class="num">${{formatInteger(item.folio)}}</td>
            <td>${{item.date}}</td>
            <td>${{escapeHtml(item.client)}}</td>
            <td>${{escapeHtml(item.branch)}}</td>
            <td>${{escapeHtml(item.service)}}</td>
            <td class="money">CLP ${{formatCurrency(item.amount)}}</td>
            <td><div class="tag-list">${{item.missingFields.map(field => `<span class="tag">${{escapeHtml(field)}}</span>`).join('')}}</div></td>
          </tr>
        `).join('')
        : `<tr><td colspan="7"><div class="empty-state">No se detectan brechas críticas en el período activo.</div></td></tr>`;
    }}

    function buildSelect(selectId, values, defaultLabel) {{
      const select = document.getElementById(selectId);
      select.innerHTML = [`<option value="">${{defaultLabel}}</option>`]
        .concat(values.map(value => `<option value="${{escapeHtml(value)}}">${{escapeHtml(value)}}</option>`))
        .join('');
    }}

    function escapeHtml(text) {{
      return String(text)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }}

    function uniqueValues(values) {{
      return [...new Set(values)].sort((a, b) => a.localeCompare(b, 'es'));
    }}

    function getRowsForActivePeriod() {{
      return TABLE_ROWS.filter(row => row.periodKey === activePeriod);
    }}

    function getScopedRows() {{
      const rowsForPeriod = getRowsForActivePeriod();
      return activeBranch === DATA.defaultBranch
        ? rowsForPeriod
        : rowsForPeriod.filter(row => row.sucursal === activeBranch);
    }}

    function syncSelectValue(select, nextValue) {{
      const exists = Array.from(select.options).some(option => option.value === nextValue);
      select.value = exists ? nextValue : '';
    }}

    function refreshTableFilters() {{
      const periodRows = getRowsForActivePeriod();
      const branchSelect = document.getElementById('filter-branch');
      const serviceSelect = document.getElementById('filter-service');
      const clientSelect = document.getElementById('filter-client');
      const fromInput = document.getElementById('filter-from');
      const toInput = document.getElementById('filter-to');

      const previousBranch = branchSelect.value;
      const previousService = serviceSelect.value;
      const previousClient = clientSelect.value;

      buildSelect(
        'filter-branch',
        uniqueValues(periodRows.map(row => row.sucursal)),
        'Todas las sucursales'
      );
      syncSelectValue(branchSelect, previousBranch);

      buildSelect('filter-service', uniqueValues(periodRows.map(row => row.servicio)), 'Todos los servicios');
      syncSelectValue(serviceSelect, previousService);

      buildSelect('filter-client', uniqueValues(periodRows.map(row => row.cliente)), 'Todos los clientes');
      syncSelectValue(clientSelect, previousClient);

      const sortedDates = periodRows.map(row => row.fecha).sort();
      fromInput.value = sortedDates[0] || '';
      toInput.value = sortedDates[sortedDates.length - 1] || '';

      renderTable();
    }}

    function getFilteredRows() {{
      const query = document.getElementById('filter-search').value.trim().toLowerCase();
      const branch = document.getElementById('filter-branch').value;
      const service = document.getElementById('filter-service').value;
      const client = document.getElementById('filter-client').value;
      const from = document.getElementById('filter-from').value;
      const to = document.getElementById('filter-to').value;

      return getRowsForActivePeriod().filter(row => {{
        const haystack = [
          row.fechaLabel,
          row.folio,
          row.cliente,
          row.sucursal,
          row.servicio,
          row.transporte,
          row.material,
          row.ciudad,
          row.origenDestino
        ].join(' ').toLowerCase();

        return (!query || haystack.includes(query))
          && (!branch || row.sucursal === branch)
          && (!service || row.servicio === service)
          && (!client || row.cliente === client)
          && (!from || row.fecha >= from)
          && (!to || row.fecha <= to);
      }});
    }}

    function initFilters() {{
      ['filter-search', 'filter-branch', 'filter-service', 'filter-client', 'filter-from', 'filter-to']
        .forEach(id => document.getElementById(id).addEventListener('input', renderTable));
    }}

    // Filtros y render del detalle en tabla desktop y tarjetas móvil.
    function renderTable() {{
      const rows = getFilteredRows();

      document.getElementById('results-count').textContent = `${{formatInteger(rows.length)}} registros visibles`;
      document.getElementById('results-amount').textContent = `Monto filtrado: CLP ${{formatCurrency(rows.reduce((sum, row) => sum + Number(row.monto || 0), 0))}}`;

      const desktopBody = document.getElementById('detail-table-body');
      const mobileCards = document.getElementById('mobile-cards');

      if (!rows.length) {{
        desktopBody.innerHTML = `<tr><td colspan="10"><div class="empty-state">No hay registros que coincidan con los filtros seleccionados.</div></td></tr>`;
        mobileCards.innerHTML = `<div class="empty-state">No hay registros que coincidan con los filtros seleccionados.</div>`;
        return;
      }}

      desktopBody.innerHTML = rows.map(row => `
        <tr>
          <td>${{row.fechaLabel}}</td>
          <td class="num">${{formatInteger(row.folio)}}</td>
          <td>${{escapeHtml(row.cliente)}}</td>
          <td>${{escapeHtml(row.sucursal)}}</td>
          <td>${{escapeHtml(row.servicio)}}</td>
          <td>${{escapeHtml(row.transporte)}}</td>
          <td>${{escapeHtml(row.material)}}</td>
          <td class="num">${{row.pesoKg == null ? 'Sin dato' : formatWeight(row.pesoKg)}}</td>
          <td class="money">CLP ${{formatCurrency(row.monto)}}</td>
          <td>${{escapeHtml(row.ciudad)}}</td>
        </tr>
      `).join('');

      mobileCards.innerHTML = rows.map(row => `
        <article class="mobile-card">
          <div class="mobile-head">
            <div>
              <div class="mobile-client">${{escapeHtml(row.cliente)}}</div>
              <div class="pill">Folio ${{formatInteger(row.folio)}} · ${{row.fechaLabel}}</div>
            </div>
            <div class="rank-value">CLP ${{formatCurrency(row.monto)}}</div>
          </div>
          <div class="mobile-grid">
            <div class="mobile-field">
              <span class="label">Sucursal</span>
              <span class="value">${{escapeHtml(row.sucursal)}}</span>
            </div>
            <div class="mobile-field">
              <span class="label">Servicio</span>
              <span class="value">${{escapeHtml(row.servicio)}}</span>
            </div>
            <div class="mobile-field">
              <span class="label">Transporte</span>
              <span class="value">${{escapeHtml(row.transporte)}}</span>
            </div>
            <div class="mobile-field">
              <span class="label">Peso final</span>
              <span class="value">${{row.pesoKg == null ? 'Sin dato' : formatWeight(row.pesoKg)}}</span>
            </div>
            <div class="mobile-field">
              <span class="label">Material</span>
              <span class="value">${{escapeHtml(row.material)}}</span>
            </div>
            <div class="mobile-field">
              <span class="label">Ciudad</span>
              <span class="value">${{escapeHtml(row.ciudad)}}</span>
            </div>
          </div>
        </article>
      `).join('');
    }}

    function renderResponsiveCharts() {{
      const series = currentView().series;
      renderAreaChart('daily-records-chart', series.dailyRecords, value => formatInteger(Math.round(value)), 'Registros diarios');
      renderAreaChart('daily-amount-chart', series.dailyAmount, value => {{
        if (value >= 1_000_000) return `${{formatOneDecimal(value / 1_000_000)}}M`;
        if (value >= 1_000) return `${{formatInteger(Math.round(value / 1_000))}}k`;
        return formatInteger(Math.round(value));
      }}, 'Monto diario en CLP');
    }}

    function applyActiveTab() {{
      document.querySelectorAll('[data-tab-target]').forEach(button => {{
        button.classList.toggle('is-active', button.dataset.tabTarget === activeTab);
      }});
      document.querySelectorAll('[data-tab-pane]').forEach(pane => {{
        pane.classList.toggle('is-active', pane.dataset.tabPane === activeTab);
      }});
    }}

    function initTabs() {{
      document.querySelectorAll('[data-tab-target]').forEach(button => {{
        button.addEventListener('click', () => {{
          activeTab = button.dataset.tabTarget || 'resumen';
          applyActiveTab();
        }});
      }});
      applyActiveTab();
    }}

    function initGlobalPeriodSelect() {{
      const select = document.getElementById('global-period-select');
      select.innerHTML = DATA.periodOptions
        .map(item => `<option value="${{escapeHtml(item.value)}}">${{escapeHtml(item.label)}}</option>`)
        .join('');
      select.value = activePeriod;
      select.addEventListener('change', event => {{
        activePeriod = event.target.value || DATA.defaultPeriod;
        normalizeActiveBranch();
        rerenderDashboard();
      }});
    }}

    function initHistoryRangeSelect() {{
      const select = document.getElementById('history-range-select');
      select.innerHTML = DATA.historyRangeOptions
        .map(item => `<option value="${{escapeHtml(item.value)}}">${{escapeHtml(item.label)}}</option>`)
        .join('');
      select.value = activeHistoryRange;
      select.addEventListener('change', event => {{
        activeHistoryRange = event.target.value || '3m';
        renderHistoricalTab();
      }});
    }}

    function refreshGlobalBranchSelect() {{
      const select = document.getElementById('global-branch-select');
      select.innerHTML = branchOptionsForCurrentPeriod()
        .map(value => `<option value="${{escapeHtml(value)}}">${{escapeHtml(value)}}</option>`)
        .join('');
      normalizeActiveBranch();
      select.value = activeBranch;
    }}

    function initGlobalBranchSelect() {{
      const select = document.getElementById('global-branch-select');
      refreshGlobalBranchSelect();
      select.addEventListener('change', event => {{
        activeBranch = event.target.value || DATA.defaultBranch;
        rerenderDashboard();
      }});
    }}

    function rerenderDashboard() {{
      normalizeActiveBranch();
      refreshGlobalBranchSelect();
      fillHero();
      renderKpis();
      renderResponsiveCharts();
      renderRankList('services-list', currentView().panels.services, value => formatCompactCurrency(value));
      renderRankList('branches-list', currentView().panels.branches, value => formatCompactCurrency(value));
      renderRankList('transport-list', currentView().panels.transport, value => `${{formatInteger(value)}} reg.`);
      renderRankList('clients-list', currentView().panels.clients, value => formatCompactCurrency(value));
      renderRankList('families-list', currentView().panels.families, value => formatWeight(value));
      renderRankList('materials-list', currentView().panels.materials, value => formatWeight(value));
      renderQuality();
      renderInsights();
      refreshTableFilters();
      renderHistoricalTab();
      renderRiskTab();
      renderQualityTab();
      document.getElementById('global-period-select').value = activePeriod;
      document.getElementById('global-branch-select').value = activeBranch;
      document.getElementById('history-range-select').value = activeHistoryRange;
      applyActiveTab();
    }}

    function activeTabLabel() {{
      const button = document.querySelector(`[data-tab-target="${{activeTab}}"]`);
      return button ? button.textContent.trim() : 'Resumen Ejecutivo';
    }}

    function activePeriodLabel() {{
      const option = DATA.periodOptions.find(item => item.value === activePeriod);
      return option ? option.label : activePeriod;
    }}

    function slugify(value) {{
      return String(value || '')
        .normalize('NFD')
        .replace(/[\\u0300-\\u036f]/g, '')
        .replace(/[^a-zA-Z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '')
        .toLowerCase();
    }}

    function currentDetailFilters() {{
      const query = document.getElementById('filter-search').value.trim();
      const branch = document.getElementById('filter-branch').value || 'Todas las sucursales';
      const service = document.getElementById('filter-service').value || 'Todos los servicios';
      const client = document.getElementById('filter-client').value || 'Todos los clientes';
      const from = document.getElementById('filter-from').value || 'Sin límite';
      const to = document.getElementById('filter-to').value || 'Sin límite';
      return [
        `Búsqueda: ${{query || 'Sin texto'}}`,
        `Sucursal detalle: ${{branch}}`,
        `Servicio: ${{service}}`,
        `Cliente: ${{client}}`,
        `Desde: ${{from}}`,
        `Hasta: ${{to}}`
      ];
    }}

    function triggerDownload(fileName, blob, mimeType) {{
      const url = URL.createObjectURL(new Blob([blob], {{ type: mimeType }}));
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    }}

    function setActionStatus(message, tone = 'default') {{
      const node = document.getElementById('action-status');
      if (!node) return;
      node.textContent = message;
      node.dataset.tone = tone;
    }}

    function exportExcel() {{
      const rows = getFilteredRows();
      if (!rows.length) {{
        window.alert('No hay registros filtrados para exportar.');
        return;
      }}

      const headers = ['Fecha', 'Folio', 'Cliente', 'Sucursal', 'Servicio', 'Transporte', 'Material', 'Peso final kg', 'Monto CLP', 'Ciudad'];
      const body = rows.map(row => [
        row.fechaLabel,
        row.folio,
        row.cliente,
        row.sucursal,
        row.servicio,
        row.transporte,
        row.material,
        row.pesoKg == null ? 'Sin dato' : Math.round(Number(row.pesoKg)),
        Math.round(Number(row.monto || 0)),
        row.ciudad
      ]);

      const tableMarkup = `
        <table>
          <thead><tr>${{headers.map(header => `<th>${{escapeHtml(header)}}</th>`).join('')}}</tr></thead>
          <tbody>
            ${{body.map(cells => `<tr>${{cells.map(cell => `<td>${{escapeHtml(cell)}}</td>`).join('')}}</tr>`).join('')}}
          </tbody>
        </table>
      `;

      const workbook = `
        <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
          <head>
            <meta charset="UTF-8">
            <style>
              table {{ border-collapse: collapse; }}
              th, td {{ border: 1px solid #c5d2c5; padding: 6px 8px; font-family: Arial, sans-serif; font-size: 12px; }}
              th {{ background: #eef4ec; font-weight: 700; }}
            </style>
          </head>
          <body>
            <h2>Detalle operativo exportado</h2>
            <p>Período: ${{escapeHtml(activePeriodLabel())}} | Vista sucursal: ${{escapeHtml(activeBranch)}} | Tab: ${{escapeHtml(activeTabLabel())}}</p>
            <p>${{currentDetailFilters().map(item => escapeHtml(item)).join(' | ')}}</p>
            ${{tableMarkup}}
          </body>
        </html>
      `;

      triggerDownload(
        `reciclean-detalle-${{slugify(activePeriodLabel())}}-${{slugify(activeBranch)}}.xls`,
        workbook,
        'application/vnd.ms-excel;charset=utf-8'
      );
      setActionStatus('Excel generado con el detalle filtrado.', 'success');
    }}

    function exportPdf() {{
      const heroMarkup = document.querySelector('.hero').outerHTML;
      const activePaneMarkup = document.querySelector(`.tab-pane[data-tab-pane="${{activeTab}}"]`).outerHTML;
      const detailFilterTags = currentDetailFilters().map(item => `<span class="tag">${{escapeHtml(item)}}</span>`).join('');
      const filterSummary = `
        <div class="aside-card" style="margin: 18px 0 22px;">
          <strong>Filtros activos</strong>
          <div class="tag-list">
            <span class="tag">Período: ${{escapeHtml(activePeriodLabel())}}</span>
            <span class="tag">Vista sucursal: ${{escapeHtml(activeBranch)}}</span>
            <span class="tag">Tab: ${{escapeHtml(activeTabLabel())}}</span>
            ${{detailFilterTags}}
          </div>
        </div>
      `;

      const printRoot = document.getElementById('print-root');
      printRoot.innerHTML = `
        ${{heroMarkup}}
        ${{filterSummary}}
        <section class="tab-pane is-active" data-tab-pane="${{activeTab}}">
          ${{activePaneMarkup}}
        </section>
      `;

      const cleanup = () => {{
        document.body.classList.remove('printing-dashboard');
        printRoot.innerHTML = '';
        window.removeEventListener('afterprint', cleanup);
      }};

      window.addEventListener('afterprint', cleanup);
      document.body.classList.add('printing-dashboard');
      setActionStatus('Abriendo impresión para guardar PDF.', 'info');
      window.setTimeout(() => {{
        window.print();
      }}, 50);
    }}

    function initDashboard() {{
      initTabs();
      initGlobalPeriodSelect();
      initGlobalBranchSelect();
      initHistoryRangeSelect();
      initFilters();
      rerenderDashboard();
    }}

    async function verifySession() {{
      try {{
        const response = await fetch('/api/session', {{
          credentials: 'same-origin',
          headers: {{ 'Accept': 'application/json' }}
        }});
        if (!response.ok) {{
          window.location.replace('/login?reason=expired');
        }}
      }} catch (error) {{
        window.location.replace('/login?reason=expired');
      }}
    }}

    async function handleLogout() {{
      const button = document.getElementById('logout-button');
      button.disabled = true;
      const originalText = button.textContent;
      button.textContent = 'Cerrando...';
      setActionStatus('Cerrando sesión...', 'info');
      try {{
        await fetch('/api/logout', {{
          method: 'POST',
          credentials: 'same-origin',
          headers: {{ 'Content-Type': 'application/json' }}
        }});
      }} finally {{
        button.textContent = originalText;
        window.location.replace('/login?reason=logout');
      }}
    }}

    document.getElementById('logout-button').addEventListener('click', handleLogout);
    document.getElementById('export-excel-button').addEventListener('click', exportExcel);
    document.getElementById('export-pdf-button').addEventListener('click', exportPdf);
    verifySession().then(initDashboard);
    window.addEventListener('resize', debounce(renderResponsiveCharts, 120));

    function debounce(fn, delay) {{
      let timer = null;
      return () => {{
        window.clearTimeout(timer);
        timer = window.setTimeout(fn, delay);
      }};
    }}
  </script>
</body>
</html>
"""

OUTPUT_FILE.write_text(html, encoding="utf-8")
print(f"HTML generado en: {OUTPUT_FILE}")
