from typing import Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator
from .common import ROOT
from .predict import predict_text, predict_queue

app = FastAPI(title='Healthcare ML Research API', version='0.1.0',
              description='Local educational experiments. Specialty labels are unreviewed proxies. Queue model uses simulated data.')


class TextInput(BaseModel):
    text: str = Field(min_length=10, max_length=2000)
    model: Literal['baseline', 'distilbert'] = 'baseline'


class QueueInput(BaseModel):
    department: Literal['General Medicine', 'Dermatology', 'Orthopedics']
    patients_ahead: int = Field(ge=0, le=100)
    active_doctors: int = Field(ge=1, le=3)
    busy_doctors: int = Field(ge=0, le=3)
    recent_mean_minutes: float = Field(gt=0, le=120, allow_inf_nan=False)
    minute_of_session: float = Field(ge=0, le=1440, allow_inf_nan=False)
    day_of_week: int = Field(ge=0, le=6)

    @model_validator(mode='after')
    def consistent_capacity(self):
        if self.busy_doctors > self.active_doctors:
            raise ValueError('busy_doctors cannot exceed active_doctors')
        if self.patients_ahead > 0 and self.busy_doctors < self.active_doctors:
            raise ValueError('FCFS simulation cannot have waiting patients while a doctor is free')
        return self


@app.get('/health')
def health():
    paths = {'condition_baseline': 'condition_baseline/model.joblib',
             'specialty_baseline': 'specialty_baseline/model.joblib',
             'specialty_distilbert': 'specialty_distilbert/model.safetensors',
             'queue_catboost': 'queue_catboost/model.cbm'}
    available = {name: (ROOT / 'models' / path).exists() for name, path in paths.items()}
    return {'status': 'ready' if all(available.values()) else 'partial',
            'research_only': True, 'artifacts': available}


@app.post('/research/specialty')
def specialty(request: TextInput):
    try:
        return predict_text(request.text, 'specialty', request.model)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except (FileNotFoundError, OSError) as error:
        raise HTTPException(503, 'Requested trained model is not available locally.') from error


@app.post('/research/conditions')
def conditions(request: TextInput):
    if request.model != 'baseline':
        raise HTTPException(422, 'Only the baseline condition model has been trained.')
    try:
        return predict_text(request.text, 'condition', 'baseline')
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except (FileNotFoundError, OSError) as error:
        raise HTTPException(503, 'Condition model is not available locally.') from error


@app.post('/research/queue')
def queue(request: QueueInput):
    if not (ROOT / 'models/queue_catboost/model.cbm').exists():
        raise HTTPException(503, 'Queue model is not available locally.')
    return predict_queue(request.model_dump())
