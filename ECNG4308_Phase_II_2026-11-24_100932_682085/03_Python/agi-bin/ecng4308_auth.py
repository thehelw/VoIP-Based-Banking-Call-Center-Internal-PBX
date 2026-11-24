#!/usr/bin/env python3
"""Authenticate a fictional banking customer through Asterisk's AGI protocol."""

import hashlib
import hmac
from pathlib import Path
import re
import sqlite3
import sys
from contextlib import closing


def pin_verifier(pin, salt):
    return hashlib.pbkdf2_hmac("sha256", pin.encode("ascii"), salt, 210_000)


def command(statement):
    print(statement, flush=True)
    reply = re.fullmatch(r"200 result=(-?\d+)(?: \((.*)\))?\s*", sys.stdin.readline())
    if reply is None or reply[1] == "-1":
        raise RuntimeError("AGI session ended or rejected the command")
    return reply[2] if reply[1] == "1" else None


def authenticate(card, pin, database):
    if not re.fullmatch(r"[0-9]{16}", card) or not re.fullmatch(r"[0-9]{4}", pin):
        return None
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as connection:
        row = connection.execute(
            "SELECT pin_salt, pin_verifier, balance_piasters, status, phone "
            "FROM customers WHERE card_number = ?",
            (card,),
        ).fetchone()

    salt = row[0] if row else bytes(16)
    expected = row[1] if row else bytes(32)
    valid = hmac.compare_digest(pin_verifier(pin, salt), expected)
    if row is not None and row[3] == "active":
        if valid:
            return ("OK", row[2], row[4])
        return ("BAD_PIN", row[0].hex(), row[4])
    return None


def balance_audio(piasters):
    pounds, remainder = divmod(piasters, 100)
    amount = str(pounds)
    if remainder:
        amount += "." + f"{remainder:02d}"
    return "&".join(
        "ecng4308/point" if digit == "." else f"ecng4308/digit-{digit}"
        for digit in amount
    )


def main():
    for line in sys.stdin:
        if not line.strip():
            break
    else:
        return

    try:
        card = command("GET VARIABLE ECNG_CARD") or ""
        pin = command("GET VARIABLE ECNG_PIN") or ""
        command('SET VARIABLE ECNG_CARD ""')
        command('SET VARIABLE ECNG_PIN ""')
        database = Path(__file__).resolve().with_name("ecng4308.sqlite")
        command('SET VARIABLE ECNG_BAD_PIN_TOKEN ""')
        command('SET VARIABLE ECNG_BAD_PIN_NUMBER ""')
        try:
            customer = authenticate(card, pin, database)
        except sqlite3.Error:
            command("SET VARIABLE ECNG_AUTH ERROR")
            return

        if customer is None:
            command("SET VARIABLE ECNG_AUTH INVALID")
            return

        outcome, value, phone = customer
        if outcome == "BAD_PIN":
            if re.fullmatch(r"100[12]|110[12]", phone or ""):
                command(f'SET VARIABLE ECNG_BAD_PIN_TOKEN "{value}"')
                command(f'SET VARIABLE ECNG_BAD_PIN_NUMBER "{phone}"')
            command("SET VARIABLE ECNG_AUTH INVALID")
            return

        piasters = value
        callback_number = phone if re.fullmatch(r"100[12]|110[12]", phone or "") else ""
        command(f'SET VARIABLE ECNG_REGISTERED_CALLBACK "{callback_number}"')
        command(f'SET VARIABLE ECNG_BALANCE_AUDIO "{balance_audio(piasters)}"')
        command(f"SET VARIABLE ECNG_BALANCE_PIASTERS {piasters}")
        command("SET VARIABLE ECNG_AUTH OK")
    except (BrokenPipeError, RuntimeError):
        return


if __name__ == "__main__":
    main()
