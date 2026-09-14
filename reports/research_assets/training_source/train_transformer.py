"""Fine-tune DistilBERT with a small GPU batch; select using validation only."""
import argparse
import time
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer, set_seed
from .common import ROOT, SEED, environment, journal, read_json, source_hashes, write_json
from .metrics import classify_metrics, save_predictions


class TextDataset(Dataset):
    def __init__(self, frame, tokenizer, label2id):
        self.encoded = tokenizer(frame.text.tolist(), truncation=True, padding='max_length', max_length=128)
        self.labels = [label2id[label] for label in frame.specialty]

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {**{k: torch.tensor(v[idx]) for k, v in self.encoded.items()},
                'labels': torch.tensor(self.labels[idx])}


@torch.inference_mode()
def predict(model, loader, device):
    model.eval()
    scores = []
    for batch in loader:
        inputs = {k: v.to(device) for k, v in batch.items() if k != 'labels'}
        scores.append(model(**inputs).logits.float().softmax(-1).cpu().numpy())
    return np.concatenate(scores)


def train(epochs=4):
    set_seed(SEED)
    torch.set_num_threads(4)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    parts = {split: pd.read_csv(ROOT / f'data/processed/{split}.csv')
             for split in ['train', 'validation', 'test']}
    labels = read_json(ROOT / 'data/processed/labels.json')['specialty']
    label2id = {label: i for i, label in enumerate(labels)}
    local = ROOT / 'models/pretrained/distilbert'
    tokenizer = AutoTokenizer.from_pretrained(local, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        local, local_files_only=True, use_safetensors=True, num_labels=len(labels),
        id2label={i: label for label, i in label2id.items()}, label2id=label2id).to(device)
    loaders = {split: DataLoader(TextDataset(frame, tokenizer, label2id),
                                 batch_size=8 if split == 'train' else 16,
                                 shuffle=split == 'train', num_workers=0)
               for split, frame in parts.items()}
    config = {'epochs': epochs, 'batch_size': 8, 'gradient_accumulation': 2,
              'learning_rate': 2e-5, 'weight_decay': 0.01, 'max_tokens': 128,
              'optimizer': 'AdamW', 'loss': 'class-weighted cross entropy',
              'device': str(device), 'mixed_precision': device.type == 'cuda',
              'selection': 'highest validation macro-F1; final test evaluated once',
              'pretrained_revision': read_json(local / 'download_manifest.json')['revision']}
    journal('TRAINING_STARTED', {'model': 'specialty_distilbert', 'config': config,
                                 'environment': environment(), 'training_rows': len(parts['train'])})
    begin = time.perf_counter()
    optimizer = torch.optim.AdamW(model.parameters(), lr=config['learning_rate'], weight_decay=0.01)
    counts = parts['train'].specialty.value_counts()
    weights = torch.tensor([len(parts['train']) / (len(labels) * counts[label]) for label in labels],
                           dtype=torch.float32, device=device)
    criterion = torch.nn.CrossEntropyLoss(weight=weights)
    scaler = torch.amp.GradScaler('cuda', enabled=device.type == 'cuda')
    output = ROOT / 'models/specialty_distilbert'
    output.mkdir(parents=True, exist_ok=True)
    best_f1 = -1
    history = []
    for epoch in range(1, epochs + 1):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        total_loss = 0.0
        epoch_start = time.perf_counter()
        for step, batch in enumerate(loaders['train'], start=1):
            batch = {k: v.to(device) for k, v in batch.items()}
            y = batch.pop('labels')
            # Account for a final accumulation window with only one batch.
            accumulation = 1 if step == len(loaders['train']) and step % 2 else 2
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=device.type == 'cuda'):
                logits = model(**batch).logits
                loss = criterion(logits, y)
            total_loss += loss.item() * len(y)
            scaler.scale(loss / accumulation).backward()
            if step % 2 == 0 or step == len(loaders['train']):
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)
        metrics = classify_metrics(parts['validation'].specialty,
                                   predict(model, loaders['validation'], device), labels)
        entry = {'epoch': epoch, 'train_loss': total_loss / len(parts['train']),
                 'validation_accuracy': metrics['accuracy'], 'validation_macro_f1': metrics['macro_f1'],
                 'seconds': time.perf_counter() - epoch_start}
        history.append(entry)
        journal('EPOCH_COMPLETED', {'model': 'specialty_distilbert', **entry})
        write_json(ROOT / 'reports/transformer_progress.json', {'state': 'running', 'history': history})
        if metrics['macro_f1'] > best_f1:
            best_f1, best_epoch, best_validation = metrics['macro_f1'], epoch, metrics
            model.save_pretrained(output, safe_serialization=True)
            tokenizer.save_pretrained(output)
    # Free the training model and optimizer before loading the selected checkpoint.
    del model, optimizer
    if device.type == 'cuda':
        torch.cuda.empty_cache()
    model = AutoModelForSequenceClassification.from_pretrained(output, local_files_only=True).to(device)
    scores = predict(model, loaders['test'], device)
    results = {'model': 'specialty_distilbert', 'config': config, 'best_epoch': best_epoch,
               'training_seconds': time.perf_counter() - begin, 'history': history,
               'validation': best_validation, 'test': classify_metrics(parts['test'].specialty, scores, labels),
               'label_status': 'UNREVIEWED condition-derived specialty proxies; not clinical routing ground truth',
               'score_status': 'Uncalibrated model scores', 'environment': environment(), 'source_hashes': source_hashes()}
    write_json(output / 'metadata.json', results)
    write_json(ROOT / 'reports/specialty_distilbert_metrics.json', results)
    write_json(ROOT / 'reports/transformer_progress.json', {'state': 'completed', 'history': history})
    save_predictions('specialty_distilbert', parts['test'], 'specialty', scores, labels)
    journal('TRAINING_COMPLETED', {'model': 'specialty_distilbert', 'best_epoch': best_epoch,
                                  'training_seconds': results['training_seconds'],
                                  'validation_macro_f1': best_f1, 'test_accuracy': results['test']['accuracy'],
                                  'test_macro_f1': results['test']['macro_f1'], 'test_rows': len(parts['test']),
                                  'artifact': 'models/specialty_distilbert', 'limitations': results['label_status']})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs', type=int, default=4)
    train(parser.parse_args().epochs)
