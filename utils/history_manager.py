"""
History Manager for ROESAN-SALVAGUARDAR
Manages historical records of processing for reconciliation and auditing
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd


class HistoryManager:
    """Manages historical records of processing for comparison and reconciliation"""

    def __init__(self, history_dir: str):
        """
        Initialize history manager

        Args:
            history_dir: Directory to store historical records
        """
        self.history_dir = history_dir
        os.makedirs(history_dir, exist_ok=True)
        self.history_file = os.path.join(history_dir, 'processing_history.json')
        self._ensure_history_file()

    def _ensure_history_file(self) -> None:
        """Ensure history file exists"""
        if not os.path.exists(self.history_file):
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def save_processing(self, movements_df: pd.DataFrame, master_df: pd.DataFrame,
                       analytics: Dict[str, Any]) -> str:
        """
        Save a processing record to history

        Args:
            movements_df: Processed movements dataframe
            master_df: Updated master template dataframe
            analytics: Analytics/insights data

        Returns:
            str: Record ID (timestamp)
        """
        record_id = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Convert dataframes to dict format
        movements_data = movements_df.to_dict('records') if movements_df is not None else []
        master_data = master_df.to_dict('records') if master_df is not None else []

        # Convert Timestamp objects to strings for JSON serialization
        for record in movements_data:
            for key, value in record.items():
                if pd.notna(value) and hasattr(value, 'isoformat'):
                    record[key] = str(value)

        for record in master_data:
            for key, value in record.items():
                if pd.notna(value) and hasattr(value, 'isoformat'):
                    record[key] = str(value)

        record = {
            'id': record_id,
            'timestamp': datetime.now().isoformat(),
            'date_formatted': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'movements_count': len(movements_data),
            'master_count': len(master_data),
            'movements': movements_data,
            'master': master_data,
            'analytics': analytics
        }

        # Append to history
        with open(self.history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)

        history.append(record)

        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

        return record_id

    def get_history_list(self) -> List[Dict[str, Any]]:
        """
        Get list of all historical records (summary)

        Returns:
            List of record summaries without full data
        """
        with open(self.history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)

        # Return only summary info
        return [{
            'id': record['id'],
            'date_formatted': record.get('date_formatted', record['timestamp']),
            'movements_count': record['movements_count'],
            'master_count': record['master_count']
        } for record in history]

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific historical record

        Args:
            record_id: ID of the record to retrieve

        Returns:
            Record data or None if not found
        """
        with open(self.history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)

        for record in history:
            if record['id'] == record_id:
                return record

        return None

    def compare_records(self, record_id_old: str, movements_df_new: pd.DataFrame) -> Dict[str, Any]:
        """
        Compare old historical record with new movements

        Args:
            record_id_old: ID of old record to compare
            movements_df_new: New movements dataframe

        Returns:
            Dict with comparison results (added, removed, modified)
        """
        old_record = self.get_record(record_id_old)
        if not old_record:
            return {'error': 'Record not found'}

        old_movements = pd.DataFrame(old_record['movements'])
        new_movements = movements_df_new.copy()

        # Ensure we have necessary columns
        old_id_column = 'Cedula' if 'Cedula' in old_movements.columns else 'ID'
        new_id_column = 'Cedula' if 'Cedula' in new_movements.columns else 'ID'

        old_ids = set(old_movements[old_id_column].astype(str)) if len(old_movements) > 0 else set()
        new_ids = set(new_movements[new_id_column].astype(str)) if len(new_movements) > 0 else set()

        # Find differences
        added = new_ids - old_ids
        removed = old_ids - new_ids
        common = old_ids & new_ids

        # Find modifications (same ID but different data)
        modified = []
        for cid in common:
            old_row = old_movements[old_movements[old_id_column].astype(str) == cid].iloc[0]
            new_row = new_movements[new_movements[new_id_column].astype(str) == cid].iloc[0]

            if not old_row.equals(new_row):
                modified.append({
                    'id': cid,
                    'old_data': old_row.to_dict(),
                    'new_data': new_row.to_dict()
                })

        return {
            'old_record_id': record_id_old,
            'old_date': old_record['date_formatted'],
            'new_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'summary': {
                'added_count': len(added),
                'removed_count': len(removed),
                'modified_count': len(modified),
                'unchanged_count': len(common) - len(modified)
            },
            'added': list(added),
            'removed': list(removed),
            'modified': modified
        }
