from __future__ import annotations

from typing import Any

from backend.database import row, rows


def dashboard_stats() -> dict[str, int]:
    object_count = row("SELECT COUNT(*) AS value FROM objects")
    loaned_count = row("SELECT COUNT(*) AS value FROM loans WHERE status = 'active'")
    loaned_quantity = row("SELECT COALESCE(SUM(quantity - returned_quantity), 0) AS value FROM loans WHERE status = 'active'")
    overdue_count = row(
        """
        SELECT COUNT(*) AS value
        FROM loans
        WHERE status = 'active' AND due_time < datetime('now', 'localtime')
        """
    )
    low_stock_count = row("SELECT COUNT(*) AS value FROM objects WHERE available_quantity <= min_quantity")
    jobs_count = row("SELECT COUNT(*) AS value FROM loan_requests WHERE status IN ('requested', 'approved', 'prepared', 'loaned', 'returned')")
    consumable_count = row("SELECT COUNT(*) AS value FROM consumable_reports WHERE status = 'open'")
    return {
        "objects": int(object_count["value"] if object_count else 0),
        "loaned": int(loaned_count["value"] if loaned_count else 0),
        "loaned_quantity": int(loaned_quantity["value"] if loaned_quantity else 0),
        "overdue": int(overdue_count["value"] if overdue_count else 0),
        "low_stock": int(low_stock_count["value"] if low_stock_count else 0),
        "jobs": int(jobs_count["value"] if jobs_count else 0),
        "consumable_reports": int(consumable_count["value"] if consumable_count else 0),
        "quarantined_quantity": int(row("SELECT COALESCE(SUM(damaged_quantity), 0) AS value FROM loan_returns WHERE damage_status = 'quarantined'")["value"]),
    }


def statistics_data() -> dict[str, Any]:
    summary = dashboard_stats()
    summary["active_loan_rows"] = int(row("SELECT COUNT(*) AS value FROM loans WHERE status = 'active'")["value"])
    summary["orphan_active_loans"] = int(
        row(
            """
            SELECT COUNT(*) AS value
            FROM loans l
            LEFT JOIN loan_requests r ON r.request_id = l.loan_request_id
            WHERE l.status = 'active'
              AND l.loan_request_id IS NOT NULL
              AND r.request_id IS NULL
            """
        )["value"]
    )
    summary["ready_pickup"] = int(row("SELECT COUNT(*) AS value FROM loan_requests WHERE status = 'prepared'")["value"])
    summary["loaned_jobs"] = int(row("SELECT COUNT(*) AS value FROM loan_requests WHERE status = 'loaned'")["value"])
    summary["returned_jobs"] = int(row("SELECT COUNT(*) AS value FROM loan_requests WHERE status = 'returned'")["value"])
    summary["stocked_jobs"] = int(row("SELECT COUNT(*) AS value FROM loan_requests WHERE status = 'stocked'")["value"])
    summary["available_objects"] = int(row("SELECT COUNT(*) AS value FROM objects WHERE status = 'Tillgänglig'")["value"])
    summary["out_of_stock"] = int(row("SELECT COUNT(*) AS value FROM objects WHERE status = 'Slut'")["value"])

    return {
        "summary": summary,
        "object_status": rows("SELECT status AS label, COUNT(*) AS value FROM objects GROUP BY status ORDER BY value DESC"),
        "job_status": rows("SELECT status AS label, COUNT(*) AS value FROM loan_requests GROUP BY status ORDER BY value DESC"),
        "loans_per_month": rows(
            """
            SELECT strftime('%Y-%m', checkout_time) AS label,
                   COUNT(*) AS loans,
                   COALESCE(SUM(quantity), 0) AS quantity
            FROM loans
            GROUP BY strftime('%Y-%m', checkout_time)
            ORDER BY label
            """
        ),
        "returns_per_month": rows(
            """
            SELECT strftime('%Y-%m', returned_at) AS label,
                   COUNT(*) AS returns, SUM(quantity) AS quantity
            FROM loan_returns
            GROUP BY strftime('%Y-%m', returned_at)
            ORDER BY label
            """
        ),
        "top_borrowers": rows(
            """
            SELECT u.name AS label, COALESCE(SUM(l.quantity - l.returned_quantity), 0) AS value
            FROM loans l
            JOIN users u ON u.user_id = l.user_id
            WHERE l.status = 'active'
            GROUP BY u.user_id, u.name
            ORDER BY value DESC, u.name
            LIMIT 8
            """
        ),
        "due_buckets": [
            {
                "label": "Sen",
                "value": int(row("SELECT COUNT(*) AS value FROM loans WHERE status = 'active' AND due_time < date('now', 'localtime')")["value"]),
            },
            {
                "label": "Idag",
                "value": int(row("SELECT COUNT(*) AS value FROM loans WHERE status = 'active' AND date(due_time) = date('now', 'localtime')")["value"]),
            },
            {
                "label": "1-7 dagar",
                "value": int(row("SELECT COUNT(*) AS value FROM loans WHERE status = 'active' AND date(due_time) > date('now', 'localtime') AND date(due_time) <= date('now', '+7 days', 'localtime')")["value"]),
            },
            {
                "label": "Senare",
                "value": int(row("SELECT COUNT(*) AS value FROM loans WHERE status = 'active' AND date(due_time) > date('now', '+7 days', 'localtime')")["value"]),
            },
        ],
    }
