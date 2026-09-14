"""Public care directory plus an explicitly separate fictional booking service."""
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
from typing import Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .common import ROOT
from .predict import predict_text, predict_queue

ZONE = ZoneInfo('Asia/Kolkata')
DB_PATH = Path(os.environ.get('HEALTHCARE_APP_DB', ROOT / 'data/app_demo.sqlite3'))
PROVIDERS = [
    {'id': 'd1', 'name': 'Dr. Anaya Mehra', 'specialty': 'General Medicine', 'initials': 'AM', 'hospital': 'Cedar Care Clinic', 'area': 'Model Town', 'experience': 'Demo physician', 'fee': 450, 'color': '#E7F0F3'},
    {'id': 'd2', 'name': 'Dr. Rohan Sethi', 'specialty': 'Dermatology', 'initials': 'RS', 'hospital': 'Cedar Care Clinic', 'area': 'Model Town', 'experience': 'Demo specialist', 'fee': 650, 'color': '#F4EAE1'},
    {'id': 'd3', 'name': 'Dr. Meera Kapoor', 'specialty': 'Orthopedics', 'initials': 'MK', 'hospital': 'Willow Medical Centre', 'area': 'Urban Estate', 'experience': 'Demo specialist', 'fee': 600, 'color': '#E8EBF6'},
    {'id': 'd4', 'name': 'Dr. Arjun Rao', 'specialty': 'Pulmonology', 'initials': 'AR', 'hospital': 'Willow Medical Centre', 'area': 'Urban Estate', 'experience': 'Demo specialist', 'fee': 700, 'color': '#E3F1EC'},
    {'id': 'd5', 'name': 'Dr. Naina Batra', 'specialty': 'Gastroenterology', 'initials': 'NB', 'hospital': 'Cedar Care Clinic', 'area': 'Model Town', 'experience': 'Demo specialist', 'fee': 700, 'color': '#F4EAE1'},
    {'id': 'd6', 'name': 'Dr. Kabir Shah', 'specialty': 'Neurology', 'initials': 'KS', 'hospital': 'Willow Medical Centre', 'area': 'Urban Estate', 'experience': 'Demo specialist', 'fee': 800, 'color': '#E8EBF6'},
    {'id': 'd7', 'name': 'Dr. Tara Anand', 'specialty': 'Endocrinology', 'initials': 'TA', 'hospital': 'Cedar Care Clinic', 'area': 'Model Town', 'experience': 'Demo specialist', 'fee': 700, 'color': '#E3F1EC'},
    {'id': 'd8', 'name': 'Dr. Ishaan Roy', 'specialty': 'Rheumatology', 'initials': 'IR', 'hospital': 'Willow Medical Centre', 'area': 'Urban Estate', 'experience': 'Demo specialist', 'fee': 750, 'color': '#E7F0F3'},
    {'id': 'd9', 'name': 'Dr. Sara Gill', 'specialty': 'Vascular Surgery', 'initials': 'SG', 'hospital': 'Willow Medical Centre', 'area': 'Urban Estate', 'experience': 'Demo specialist', 'fee': 800, 'color': '#F4EAE1'},
]
BY_ID = {p['id']: p for p in PROVIDERS}


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db


def init_db():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS appointments (
          id TEXT PRIMARY KEY, session_hash TEXT NOT NULL REFERENCES sessions(token_hash),
          provider_id TEXT NOT NULL, slot TEXT NOT NULL, status TEXT NOT NULL,
          request_id TEXT NOT NULL, created_at TEXT NOT NULL, token TEXT NOT NULL,
          ahead INTEGER NOT NULL DEFAULT 3, UNIQUE(session_hash, request_id));
        CREATE UNIQUE INDEX IF NOT EXISTS one_active_booking_per_slot
        ON appointments(provider_id, slot) WHERE status != 'cancelled';
        ''')


app = FastAPI(title='Carelane - Patient app demo', version='0.1.0')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:8081', 'http://127.0.0.1:8081',
                                               'http://localhost:8082', 'http://127.0.0.1:8082'],
                   allow_methods=['GET', 'POST'], allow_headers=['Authorization', 'Content-Type'])
init_db()


def session(authorization: str = Header(default='')):
    if not authorization.startswith('Bearer '):
        raise HTTPException(401, 'Open a demo session first.')
    digest = hashlib.sha256(authorization[7:].encode()).hexdigest()
    with connect() as db:
        if not db.execute('SELECT 1 FROM sessions WHERE token_hash=?', (digest,)).fetchone():
            raise HTTPException(401, 'Your demo session expired. Please reload the app.')
    return digest


def now():
    return datetime.now(ZONE)


def available_slots(provider_id):
    if provider_id not in BY_ID:
        raise HTTPException(404, 'Doctor not found.')
    result = []
    current = now()
    for offset in range(4):
        day = current.date() + timedelta(days=offset)
        for hour in [9, 10, 11, 14, 15, 16, 17]:
            slot = datetime(day.year, day.month, day.day, hour, tzinfo=ZONE)
            if slot > current + timedelta(minutes=15):
                result.append(slot.isoformat())
    return result


def owned(db, appointment_id, owner):
    row = db.execute('SELECT * FROM appointments WHERE id=? AND session_hash=?', (appointment_id, owner)).fetchone()
    if row is None:
        raise HTTPException(404, 'Appointment not found.')
    return row


def present(row):
    return {'id': row['id'], 'provider': BY_ID[row['provider_id']], 'slot': row['slot'],
            'status': row['status'], 'token': row['token'], 'created_at': row['created_at'], 'demo': True}


@app.get('/health')
def health():
    return {'status': 'ok', 'app': 'carelane-demo', 'demo': True}


@app.post('/api/session')
def create_session():
    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode()).hexdigest()
    with connect() as db:
        db.execute('INSERT INTO sessions VALUES (?,?)', (digest, now().isoformat()))
    return {'token': token, 'profile': {'name': 'Demo Patient'}, 'demo': True}


@app.get('/api/providers')
def providers():
    return {'providers': PROVIDERS, 'demo': True, 'city': 'Patiala'}


@app.get('/api/directory')
def public_directory():
    """Source-checked public listings; these are never bookable via demo endpoints."""
    path = ROOT / 'data/public_directory.json'
    return json.loads(path.read_text(encoding='utf-8'))


class Symptoms(BaseModel):
    text: str = Field(min_length=10, max_length=2000)


@app.post('/api/guidance')
def guidance(request: Symptoms, owner=Depends(session)):
    try:
        result = predict_text(request.text, 'specialty', 'baseline')
    except ValueError as error:
        raise HTTPException(422, 'Please describe your symptoms in a little more detail.') from error
    except (OSError, FileNotFoundError) as error:
        raise HTTPException(503, 'Specialty guidance is unavailable. You can still browse doctors.') from error
    # Raw symptom text is not persisted by the demo service.
    return {'specialties': [row['label'] for row in result['ranked_labels']],
            'review_required': True, 'demo': True,
            'message': 'These are experimental suggestions. Confirm the appropriate department with clinic staff.'}


@app.get('/api/providers/{provider_id}/slots')
def slots(provider_id: str):
    values = available_slots(provider_id)
    with connect() as db:
        booked = {row['slot'] for row in db.execute("SELECT slot FROM appointments WHERE provider_id=? AND status!='cancelled'", (provider_id,))}
    return {'slots': [{'value': slot, 'available': slot not in booked} for slot in values], 'demo': True}


class Booking(BaseModel):
    provider_id: str
    slot: str
    request_id: str = Field(min_length=8, max_length=100)


@app.post('/api/appointments', status_code=201)
def book(request: Booking, owner=Depends(session)):
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        previous = db.execute('SELECT * FROM appointments WHERE session_hash=? AND request_id=?', (owner, request.request_id)).fetchone()
        if previous:
            if previous['provider_id'] != request.provider_id or previous['slot'] != request.slot:
                raise HTTPException(409, 'This booking request has already been used.')
            return present(previous)
        if request.slot not in available_slots(request.provider_id):
            raise HTTPException(422, 'That slot is no longer available. Please choose another time.')
        uid = str(uuid4())
        token = 'C-' + secrets.token_hex(2).upper()
        try:
            db.execute('INSERT INTO appointments (id,session_hash,provider_id,slot,status,request_id,created_at,token) VALUES (?,?,?,?,?,?,?,?)',
                       (uid, owner, request.provider_id, request.slot, 'booked', request.request_id, now().isoformat(), token))
        except sqlite3.IntegrityError as error:
            raise HTTPException(409, 'Someone just booked that time. Please choose another slot.') from error
        return present(owned(db, uid, owner))


@app.get('/api/appointments')
def appointments(owner=Depends(session)):
    with connect() as db:
        return {'appointments': [present(row) for row in db.execute('SELECT * FROM appointments WHERE session_hash=? ORDER BY created_at DESC', (owner,))]}


@app.post('/api/appointments/{appointment_id}/cancel')
def cancel(appointment_id: str, owner=Depends(session)):
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = owned(db, appointment_id, owner)
        if row['status'] not in ['booked', 'cancelled']:
            raise HTTPException(409, 'This visit has already checked in. Contact the demo desk.')
        db.execute("UPDATE appointments SET status='cancelled' WHERE id=?", (appointment_id,))
        return present(owned(db, appointment_id, owner))


@app.post('/api/appointments/{appointment_id}/check-in')
def check_in(appointment_id: str, owner=Depends(session)):
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = owned(db, appointment_id, owner)
        if row['status'] == 'booked':
            db.execute("UPDATE appointments SET status='checked_in' WHERE id=?", (appointment_id,))
        elif row['status'] not in ['checked_in', 'ready']:
            raise HTTPException(409, 'This appointment cannot be checked in.')
        return present(owned(db, appointment_id, owner))


@app.get('/api/appointments/{appointment_id}/queue')
def queue(appointment_id: str, owner=Depends(session)):
    with connect() as db:
        row = owned(db, appointment_id, owner)
    if row['status'] not in ['checked_in', 'ready', 'completed']:
        raise HTTPException(409, 'Check in to start the demo queue.')
    ahead = row['ahead'] if row['status'] == 'checked_in' else 0
    department = BY_ID[row['provider_id']]['specialty']
    estimate = 0
    if ahead:
        if department in ['General Medicine', 'Dermatology', 'Orthopedics']:
            estimate = predict_queue({'department': department, 'patients_ahead': ahead, 'active_doctors': 1,
                                     'busy_doctors': 1, 'recent_mean_minutes': 12, 'minute_of_session': 60,
                                     'day_of_week': now().weekday()})['estimated_minutes']
        else:
            estimate = (ahead + .5) * 12
    return {'appointment': present(row), 'ahead': ahead, 'estimated_minutes': round(estimate),
            'position': ahead + 1 if row['status'] != 'completed' else 0, 'demo': True,
            'message': 'Simulated queue. Use the demo desk to advance fictional patients.'}


@app.post('/api/appointments/{appointment_id}/demo-advance')
def advance(appointment_id: str, owner=Depends(session)):
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = owned(db, appointment_id, owner)
        if row['status'] == 'ready':
            db.execute("UPDATE appointments SET status='completed' WHERE id=?", (appointment_id,))
        elif row['status'] == 'checked_in':
            ahead = max(0, row['ahead'] - 1)
            db.execute('UPDATE appointments SET ahead=?,status=? WHERE id=?', (ahead, 'ready' if ahead == 0 else 'checked_in', appointment_id))
        else:
            raise HTTPException(409, 'No active demo queue to advance.')
    return queue(appointment_id, owner)
