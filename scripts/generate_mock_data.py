import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "freshmart_sales.csv"

COLUMNS = [
    "invoice_id",
    "branch",
    "city",
    "product_line",
    "unit_price",
    "quantity",
    "date",
    "payment",
    "rating",
]

BRANCH_CITY = {
    "A": "Kanpur",
    "B": "Lucknow",
    "C": "Agra",
}

PRODUCT_LINES = ["Electronics", "Grocery", "Fashion", "Health"]
PAYMENT_METHODS = ["Cash", "Credit Card", "UPI"]

rows = []

for i in range(1, 501):
    branch = random.choice(list(BRANCH_CITY.keys()))

    unit_price = round(random.uniform(10, 500), 2)
    quantity = random.randint(1, 10)

    # Add invalid values to test the transformation logic
    if i % 50 == 0:
        quantity = 0
    if i % 75 == 0:
        unit_price = 0.0

    sale_date = datetime(2025, 11, 1) + timedelta(
        days=random.randint(0, 29)
    )

    rows.append({
        "invoice_id": f"INV{i:05d}",
        "branch": branch,
        "city": BRANCH_CITY[branch],
        "product_line": random.choice(PRODUCT_LINES),
        "unit_price": unit_price,
        "quantity": quantity,
        "date": sale_date.strftime("%Y-%m-%d"),
        "payment": random.choice(PAYMENT_METHODS),
        "rating": round(random.uniform(1, 10), 1),
    })

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(rows)

invalid_rows = sum(
    row["quantity"] == 0 or row["unit_price"] == 0
    for row in rows
)

print(f"Dataset created: {OUTPUT_PATH}")
print(f"Total rows: {len(rows)}")
print(f"Invalid rows for filtering: {invalid_rows}")
print(f"Expected cleaned rows: {len(rows) - invalid_rows}")
