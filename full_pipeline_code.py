# data ingestion

import pandas as pd
import numpy as np
import sqlite3
import hashlib
import re
from pathlib import Path

# Read all source tables
flights = pd.read_excel("UseCase - Airlines.xlsx", sheet_name="flights")
bookings = pd.read_excel("UseCase - Airlines.xlsx", sheet_name="bookings")
payments = pd.read_excel("UseCase - Airlines.xlsx", sheet_name="payments")
passengers = pd.read_excel("UseCase - Airlines.xlsx", sheet_name="passengers")


print("Data Ingestion Completed")
print("-" * 50)

print("Flights    :", flights.shape)
print("Bookings   :", bookings.shape)
print("Payments   :", payments.shape)
print("Passengers :", passengers.shape)

# Schemas Validation

expected_schema = {

    "flights": [
        "flight_id",
        "airline",
        "source",
        "destination",
        "departure_time",
        "arrival_time",
        "duration"
    ],

    "bookings": [
        "booking_id",
        "passenger_id",
        "flight_id",
        "booking_date",
        "status",
        "passport_number",
        "seat_number",
        "emergency_contact_name",
        "emergency_contact_phone"
    ],

    "payments": [
        "payment_id",
        "booking_id",
        "amount",
        "payment_method"
    ],

    "passengers": [
        "passenger_id",
        "first_name",
        "last_name",
        "age",
        "gender",
        "email",
        "phone",
        "aadhaar_id",
        "date_of_birth"
    ]
}


def validate_schema(df, table_name):

    expected_columns = expected_schema[table_name]

    missing_columns = set(expected_columns) - set(df.columns)
    extra_columns = set(df.columns) - set(expected_columns)

    if missing_columns:
        print(
            f"{table_name}: Missing columns -> "
            f"{missing_columns}"
        )

    if extra_columns:
        print(
            f"{table_name}: Extra columns -> "
            f"{extra_columns}"
        )

    if not missing_columns:
        print(f"{table_name}: Schema validation PASSED")


validate_schema(flights, "flights")
validate_schema(bookings, "bookings")
validate_schema(payments, "payments")
validate_schema(passengers, "passengers")

# Data Quality checks
def data_quality_report(df, table_name):

    print("\n" + "=" * 60)
    print(f"DATA QUALITY REPORT: {table_name}")
    print("=" * 60)

    print("Rows              :", len(df))
    print("Columns           :", len(df.columns))

    print("Duplicate rows    :", df.duplicated().sum())

    print("Missing values:")
    print(df.isnull().sum())

    print("\nData types:")
    print(df.dtypes)


data_quality_report(flights, "flights")
data_quality_report(bookings, "bookings")
data_quality_report(payments, "payments")
data_quality_report(passengers, "passengers")

# Invalid record detection
invalid_flights = flights[flights["flight_id"].isna()].copy()

print("Invalid flight records:", len(invalid_flights))

payments["amount"] = pd.to_numeric(payments["amount"], errors="coerce")
invalid_payments = payments[payments["amount"].notna() & (payments["amount"] <= 0)
].copy()

print("Invalid payment records:", len(invalid_payments))

invalid_passengers = passengers[
    passengers["age"].notna() &
    (
        (passengers["age"] < 0) |
        (passengers["age"] > 120)
    )
].copy()

print("Invalid passenger age records:",
      len(invalid_passengers))

# Remove duplicate flight records

flights = flights.drop_duplicates(
    subset=["flight_id"],
    keep="first"
)

# Remove duplicate bookings

bookings = bookings.drop_duplicates(
    subset=["booking_id"],
    keep="first"
)

# Remove duplicate payments

payments = payments.drop_duplicates(
    subset=["payment_id"],
    keep="first"
)

# Remove duplicate passengers

passengers = passengers.drop_duplicates(
    subset=["passenger_id"],
    keep="first"
)


print("Duplicates removed.")

# convert date/time columns
flights["departure_time"] = pd.to_datetime(
    flights["departure_time"],
    errors="coerce"
)

flights["arrival_time"] = pd.to_datetime(
    flights["arrival_time"],
    errors="coerce"
)

bookings["booking_date"] = pd.to_datetime(
    bookings["booking_date"],
    errors="coerce"
)

passengers["date_of_birth"] = pd.to_datetime(
    passengers["date_of_birth"],
    errors="coerce"
)

# convert flight duration
flights["duration_minutes"] = (
    pd.to_timedelta(
        flights["duration"].astype(str),
        errors="coerce"
    ).dt.total_seconds() / 60
)

# validation duration
invalid_duration = flights[
    flights["duration_minutes"].isna() |
    (flights["duration_minutes"] <= 0)
].copy()

print(
    "Invalid duration records:",
    len(invalid_duration)
)

# remove invalid duration
flights = flights[
    flights["duration_minutes"].notna() &
    (flights["duration_minutes"] > 0)
].copy()


# Standardize airline and airport codes
flights["airline"] = (
    flights["airline"]
    .astype("string")
    .str.strip()
    .str.upper()
)

flights["source"] = (
    flights["source"]
    .astype("string")
    .str.strip()
    .str.upper()
)

flights["destination"] = (
    flights["destination"]
    .astype("string")
    .str.strip()
    .str.upper()
)

# Standardize booking status
bookings["status"] = (
    bookings["status"]
    .astype("string")
    .str.strip()
    .str.upper()
)

# Handling missing status

bookings["status"] = bookings["status"].fillna(
    "UNKNOWN"
)

flights["airline"] = flights["airline"].fillna(
    "UNKNOWN"
)

passengers["last_name"] = (
    passengers["last_name"]
    .fillna("UNKNOWN")
)

payments["amount_missing_flag"] = (
    payments["amount"].isna()
)

valid_payments = payments[
    payments["amount"].notna() &
    (payments["amount"] >= 0)
].copy()

# Pll masking /hashing
def hash_value(value):

    if pd.isna(value):
        return None

    value = str(value).strip()

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()

# Passenger data

passengers["first_name_hash"] = (
    passengers["first_name"]
    .apply(hash_value)
)

passengers["last_name_hash"] = (
    passengers["last_name"]
    .apply(hash_value)
)

passengers["email_hash"] = (
    passengers["email"]
    .apply(hash_value)
)

passengers["phone_hash"] = (
    passengers["phone"]
    .apply(hash_value)
)

passengers["aadhaar_hash"] = (
    passengers["aadhaar_id"]
    .apply(hash_value)
)
# Booking
bookings["passport_hash"] = (
    bookings["passport_number"]
    .apply(hash_value)
)

bookings["emergency_contact_name_hash"] = (
    bookings["emergency_contact_name"]
    .apply(hash_value)
)

bookings["emergency_contact_phone_hash"] = (
    bookings["emergency_contact_phone"]
    .apply(hash_value)
)

passengers = passengers.drop(
    columns=[
        "first_name",
        "last_name",
        "email",
        "phone",
        "aadhaar_id"
    ]
)

bookings = bookings.drop(
    columns=[
        "passport_number",
        "emergency_contact_name",
        "emergency_contact_phone"
    ]
)

# Create route
flights["route"] = (
    flights["source"]
    + " → "
    + flights["destination"]
)


##### Data Model and storage
# connecting

connection = sqlite3.connect(
    "airline_analytics.db"
)

# flight dimension
dim_flight = flights[
    [
        "flight_id",
        "airline",
        "source",
        "destination",
        "route",
        "departure_time",
        "arrival_time",
        "duration_minutes"
    ]
].copy()

# passenger dimension
dim_passenger = passengers[
    [
        "passenger_id",
        "first_name_hash",
        "last_name_hash",
        "age",
        "gender",
        "email_hash",
        "phone_hash",
        "aadhaar_hash",
        "date_of_birth"
    ]
].copy()

# booking fact
fact_booking = bookings[
    [
        "booking_id",
        "passenger_id",
        "flight_id",
        "booking_date",
        "status",
        "passport_hash",
        "seat_number"
    ]
].copy()

# payment dimension

dim_payment = payments[
    [
        "payment_id",
        "booking_id",
        "amount",
        "payment_method",
        "amount_missing_flag"
    ]
].copy()

dim_flight.to_sql(
    "dim_flight",
    connection,
    if_exists="replace",
    index=False
)

dim_passenger.to_sql(
    "dim_passenger",
    connection,
    if_exists="replace",
    index=False
)

fact_booking.to_sql(
    "fact_booking",
    connection,
    if_exists="replace",
    index=False
)

dim_payment.to_sql(
    "dim_payment",
    connection,
    if_exists="replace",
    index=False
)

print("Data stored successfully in SQLite.")


tables = pd.read_sql_query(
    """
    SELECT name
    FROM sqlite_master
    WHERE type = 'table';
    """,
    connection
)

print(tables)