#!/usr/bin/env python3
"""Customers CSV Bakiye Özeti Hesaplayıcı.

fixtures/data/customers.csv dosyasını okuyarak kişisel verileri dahil etmeden
yalnızca toplulaştırılmış bakiye istatistiklerini hesaplar ve ekrana basar / rapora yazar.
"""

import csv
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "fixtures" / "data" / "customers.csv"
REPORT_PATH = ROOT / "reports" / "balance-summary.md"


def calculate_balance_summary(csv_path: Path):
    balances = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            val = row.get("balance_try", "").strip()
            if val:
                balances.append(Decimal(val))

    if not balances:
        return {
            "customer_count": 0,
            "total_balance": Decimal("0.00"),
            "average_balance": Decimal("0.00"),
            "max_balance": Decimal("0.00"),
            "min_balance": Decimal("0.00"),
        }

    count = len(balances)
    total = sum(balances)
    avg = (total / Decimal(count)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    max_bal = max(balances)
    min_bal = min(balances)

    return {
        "customer_count": count,
        "total_balance": total,
        "average_balance": avg,
        "max_balance": max_bal,
        "min_balance": min_bal,
    }


def generate_markdown_report(summary: dict) -> str:
    return f"""# Müşteri Bakiye Özeti Raporu

Bu rapor `fixtures/data/customers.csv` veri setindeki bakiye bilgilerinin toplulaştırılmış özetini içerir. Rapor hiçbir kişisel veri (PII) içermemektedir.

## Özet İstatistikler

| Metrik | Değer (TRY) |
| :--- | :--- |
| **Toplam Müşteri Sayısı** | {summary['customer_count']} |
| **Toplam Bakiye** | {summary['total_balance']:,.2f} TRY |
| **Ortalama Bakiye** | {summary['average_balance']:,.2f} TRY |
| **En Yüksek Bakiye** | {summary['max_balance']:,.2f} TRY |
| **En Düşük Bakiye** | {summary['min_balance']:,.2f} TRY |

---
*Not: Finansal hesaplamalarda hassasiyet kaybını önlemek için `Decimal` kullanılmıştır.*
"""


def main():
    summary = calculate_balance_summary(CSV_PATH)

    print("--- Bakiye Özeti (Toplulaştırılmış) ---")
    print(f"Müşteri Sayısı    : {summary['customer_count']}")
    print(f"Toplam Bakiye     : {summary['total_balance']} TRY")
    print(f"Ortalama Bakiye   : {summary['average_balance']} TRY")
    print(f"En Yüksek Bakiye  : {summary['max_balance']} TRY")
    print(f"En Düşük Bakiye   : {summary['min_balance']} TRY")

    report_content = generate_markdown_report(summary)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report_content, encoding="utf-8")
    print(f"\nRapor başarıyla kaydedildi: {REPORT_PATH}")


if __name__ == "__main__":
    main()
