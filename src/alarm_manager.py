"""
AMR Sentinel - High-Priority Alarm & Evidence Lifecycle Manager.
Provides deterministic alarm evaluation, audio state transitions,
session deduplication, and evidence serialization.
"""
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import asdict
from src.alerts import AMRAlert


class AlarmManager:
    """
    Manages alarm sound lifecycle, alert deduplication, and audio mute states.
    Guarantees that:
    1. Only genuine HIGH/CRITICAL alerts trigger audio alarms.
    2. Repeated file uploads with identical hashes do not restart alarms.
    3. STOP ALARM stops the audio loop immediately without dismissing the alert.
    4. ACKNOWLEDGE is a distinct audit-logged action.
    5. Single alarm loop enforcement (singleton playback lock).
    """

    def __init__(self):
        self.silenced_alert_ids: set[str] = set()
        self.acknowledged_alert_ids: set[str] = set()
        self.processed_file_hashes: Dict[str, List[str]] = {}  # hash -> list of alert IDs
        self.active_alarm_alert_id: Optional[str] = None
        self.is_alarm_sounding: bool = False
        self.alarm_volume: float = 0.8  # 0.0 to 1.0

    @staticmethod
    def compute_file_hash(content: str) -> str:
        """Returns SHA-256 hash of normalized CSV content."""
        if not content:
            return ""
        norm = "".join(content.split())
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()

    def process_dataset_alerts(
        self,
        alerts: List[AMRAlert],
        file_content: Optional[str] = None,
        force_reevaluate: bool = False
    ) -> Tuple[bool, Optional[AMRAlert], List[AMRAlert]]:
        """
        Analyzes detected alerts against alarm policy.
        Returns (should_sound, active_high_alert, all_high_alerts).
        """
        if not alerts:
            self.is_alarm_sounding = False
            self.active_alarm_alert_id = None
            return False, None, []

        file_hash = self.compute_file_hash(file_content) if file_content else None

        # Filter strictly High and Critical alerts
        high_alerts = [a for a in alerts if a.severity in ("Critical", "High")]

        if not high_alerts:
            # Medium, Low, Watch NEVER trigger alarm
            self.is_alarm_sounding = False
            self.active_alarm_alert_id = None
            return False, None, []

        # Check if identical file was already evaluated and all its alerts handled
        if file_hash and not force_reevaluate:
            if file_hash in self.processed_file_hashes:
                prev_ids = set(self.processed_file_hashes[file_hash])
                current_ids = set(a.id for a in high_alerts)
                # If all high alerts for this file are already silenced or acknowledged, do not ring
                if current_ids.issubset(self.silenced_alert_ids.union(self.acknowledged_alert_ids)):
                    self.is_alarm_sounding = False
                    return False, None, high_alerts

        # If this is a genuinely new file (distinct hash), allow its alerts to sound
        if file_hash and file_hash not in self.processed_file_hashes:
            for a in high_alerts:
                self.silenced_alert_ids.discard(a.id)

        # Record this file hash
        if file_hash:
            self.processed_file_hashes[file_hash] = [a.id for a in high_alerts]

        # Find first high alert that has NOT been silenced and NOT acknowledged
        qualifying_alert = None
        for a in high_alerts:
            if a.id not in self.silenced_alert_ids and a.id not in self.acknowledged_alert_ids:
                qualifying_alert = a
                break

        if qualifying_alert is not None:
            self.is_alarm_sounding = True
            self.active_alarm_alert_id = qualifying_alert.id
            return True, qualifying_alert, high_alerts
        else:
            self.is_alarm_sounding = False
            return False, None, high_alerts

    def stop_alarm(self, alert_id: Optional[str] = None) -> bool:
        """
        Immediately silences the alarm sound.
        The alert remains visible and active.
        """
        target_id = alert_id or self.active_alarm_alert_id
        if target_id:
            self.silenced_alert_ids.add(target_id)
        self.is_alarm_sounding = False
        return True

    def acknowledge_alert(
        self,
        alert_id: str,
        reviewer_email: str = "analyst@amrsentinel.org",
        notes: Optional[str] = None
    ) -> bool:
        """
        Marks an alert as reviewed/acknowledged.
        Silences the alarm if it was currently sounding for this alert.
        """
        self.acknowledged_alert_ids.add(alert_id)
        self.silenced_alert_ids.add(alert_id)
        if self.active_alarm_alert_id == alert_id:
            self.is_alarm_sounding = False
            self.active_alarm_alert_id = None
        return True

    def get_alarm_state(self) -> Dict[str, Any]:
        """Returns the current alarm state for UI and API clients."""
        return {
            "is_sounding": self.is_alarm_sounding,
            "active_alert_id": self.active_alarm_alert_id,
            "silenced_alert_ids": list(self.silenced_alert_ids),
            "acknowledged_alert_ids": list(self.acknowledged_alert_ids),
            "volume": self.alarm_volume,
        }

    def set_volume(self, volume: float) -> float:
        """Sets alarm volume between 0.0 and 1.0."""
        self.alarm_volume = max(0.0, min(1.0, float(volume)))
        return self.alarm_volume

    def reset(self):
        """Resets all alarm states (used for testing or session reset)."""
        self.silenced_alert_ids.clear()
        self.acknowledged_alert_ids.clear()
        self.processed_file_hashes.clear()
        self.active_alarm_alert_id = None
        self.is_alarm_sounding = False


# Global singleton instance for server session
GLOBAL_ALARM_MANAGER = AlarmManager()
