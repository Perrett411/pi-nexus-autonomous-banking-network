"""Audit-log analytics: chart series plus anomaly & spike detection.

Turns the hash-chained audit trail into time-bucketed series that are
ready to chart, and flags network anomalies — transaction spikes,
amount outliers, invalid amounts, self-transfers, forks and slashing —
so they are visible at a glance on the dashboard.
"""
import math
from datetime import datetime, timezone

# A bucket must contain at least this many transactions to count as a spike.
MIN_SPIKE_COUNT = 3


class AuditAnalytics:
    def __init__(self, audit_log):
        self.audit_log = audit_log

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _recorded_at(entry):
        ts = (entry.get('payload') or {}).get('recorded_at')
        try:
            return datetime.fromisoformat(ts)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _bucket_start(dt, bucket_seconds):
        epoch = int(dt.timestamp())
        return epoch - (epoch % bucket_seconds)

    @staticmethod
    def _mean_std(values):
        if not values:
            return 0.0, 0.0
        mean = sum(values) / len(values)
        var = sum((v - mean) ** 2 for v in values) / len(values)
        return mean, math.sqrt(var)

    # -- public API --------------------------------------------------------
    def analyze(self, bucket_seconds=60, lookback=30):
        """Return chart-ready series, detected anomalies and a summary."""
        tx_entries = self.audit_log.get_entries('TRANSACTION')
        cc_entries = self.audit_log.get_entries('CONSENSUS_CHANGE')

        now_bucket = self._bucket_start(datetime.now(timezone.utc), bucket_seconds)
        first_bucket = now_bucket - (lookback - 1) * bucket_seconds

        buckets = {}
        b = first_bucket
        while b <= now_bucket:
            buckets[b] = {'t': b, 'transactions': 0, 'consensus': 0, 'amount': 0.0}
            b += bucket_seconds

        amounts = []
        for entry in tx_entries:
            tx = (entry.get('payload') or {}).get('transaction') or {}
            amount = tx.get('amount')
            valid_amount = isinstance(amount, (int, float)) and not isinstance(amount, bool)
            if valid_amount and amount > 0:
                amounts.append(float(amount))
            dt = self._recorded_at(entry)
            if dt is None:
                continue
            key = self._bucket_start(dt, bucket_seconds)
            if key in buckets:
                buckets[key]['transactions'] += 1
                if valid_amount:
                    buckets[key]['amount'] += amount

        for entry in cc_entries:
            dt = self._recorded_at(entry)
            if dt is None:
                continue
            key = self._bucket_start(dt, bucket_seconds)
            if key in buckets:
                buckets[key]['consensus'] += 1

        series = [buckets[k] for k in sorted(buckets)]

        # --- anomaly & spike detection ------------------------------------
        anomalies = []

        counts = [bkt['transactions'] for bkt in series]
        mean, std = self._mean_std(counts)
        for bkt in series:
            if (bkt['transactions'] >= MIN_SPIKE_COUNT and mean > 0 and std > 0
                    and bkt['transactions'] > mean + 2 * std):
                anomalies.append({
                    'type': 'TRANSACTION_SPIKE',
                    'severity': 'high' if bkt['transactions'] > mean + 3 * std else 'medium',
                    'message': (f"Spike: {bkt['transactions']} transactions in one minute "
                                f"vs {mean:.1f} average"),
                    't': bkt['t'],
                })

        a_mean, a_std = self._mean_std(amounts)
        for entry in tx_entries:
            tx = (entry.get('payload') or {}).get('transaction') or {}
            amount = tx.get('amount')
            valid_amount = isinstance(amount, (int, float)) and not isinstance(amount, bool)
            dt = self._recorded_at(entry)
            if dt is None or dt.timestamp() < first_bucket:
                continue
            ts = int(dt.timestamp())
            if not valid_amount or amount <= 0:
                anomalies.append({
                    'type': 'INVALID_AMOUNT',
                    'severity': 'high',
                    'message': f"Invalid transaction amount: {amount!r}",
                    't': ts,
                })
            elif a_std > 0 and abs(amount - a_mean) > 3 * a_std:
                anomalies.append({
                    'type': 'AMOUNT_OUTLIER',
                    'severity': 'medium',
                    'message': f"Unusual amount: {amount} QNP (average {a_mean:.2f})",
                    't': ts,
                })
            if tx.get('sender') and tx.get('sender') == tx.get('recipient'):
                anomalies.append({
                    'type': 'SELF_TRANSFER',
                    'severity': 'medium',
                    'message': f"Self-transfer: {tx.get('sender')} → itself",
                    't': ts,
                })

        for entry in cc_entries[-100:]:
            change_type = (entry.get('payload') or {}).get('change_type')
            if change_type not in ('FORK_RESOLVED', 'VALIDATOR_SLASHED'):
                continue
            dt = self._recorded_at(entry)
            if dt is None or dt.timestamp() < first_bucket:
                continue
            if change_type == 'FORK_RESOLVED':
                message = 'Chain fork resolved — competing chain adopted'
            else:
                vid = (entry.get('payload', {}).get('details') or {}).get('validator_id', '?')
                message = f"Validator slashed: {vid}"
            anomalies.append({
                'type': change_type,
                'severity': 'high' if change_type == 'FORK_RESOLVED' else 'medium',
                'message': message,
                't': int(dt.timestamp()),
            })

        anomalies.sort(key=lambda a: a['t'], reverse=True)
        anomalies = anomalies[:25]

        peak = max(series, key=lambda bkt: bkt['transactions']) if series else None
        return {
            'bucket_seconds': bucket_seconds,
            'series': series,
            'anomalies': anomalies,
            'summary': {
                'transactions_analyzed': len(tx_entries),
                'average_per_bucket': round(mean, 2),
                'peak_bucket': peak['transactions'] if peak else 0,
                'total_volume': round(sum(amounts), 2),
                'anomaly_count': len(anomalies),
            },
        }
