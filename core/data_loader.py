import pandas as pd
import os
from typing import List, Dict

class CMDBDataLoader:
    """
    Loads and normalizes CMDB data from multiple discovery sources.
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.required_columns = [
            'ci_name', 'ip_address', 'ci_type', 'environment',
            'owner', 'status', 'last_discovered', 'location'
        ]

    def load_all_sources(self) -> pd.DataFrame:
        """Load and combine all discovery sources."""

        sources = {
            'network_discovery': 'network_discovery.csv',
            'app_discovery': 'app_discovery.csv',
            'manual_import': 'manual_import.csv'
        }

        all_data = []

        for source_name, filename in sources.items():
            filepath = os.path.join(self.data_dir, filename)
            if os.path.exists(filepath):
                df = pd.read_csv(filepath)
                df['source'] = source_name # Tracks where data came from
                df = self._normalize_data(df)
                all_data.append(df)

        combined_df = pd.concat(all_data, ignore_index=True)
        return combined_df
    
    def _normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize data formats across sources."""

        df = df.copy() # Makes a copy and does not modify the original

        # Strip whitespaces from all string columns
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].str.strip()

        # Standardize environment names
        environment_mapping = {
            'Prod': 'Production',
            'Dev': 'Development',
            'Test': 'Testing',
            'DR': 'Disaster Recovery'
        }
        df['environment'] = df['environment'].replace(environment_mapping)

        # Standardize status values
        status_mapping = {
            'Running': 'Active',
            'Up': 'Active',
            'Down': 'Inactive'
        }
        df['status'] = df['status'].replace(status_mapping)

        # Add normalized name for fuzzy matching
        df['ci_name_normalized'] = df['ci_name'].str.lower().str.replace('_', '-', regex=False).str.replace(' ', '-', regex=False)

        return df
    
    def get_data_summary(self, df:pd.DataFrame) -> Dict:
        """Generate summary stats about loaded data."""

        summary = {
            'total_records': len(df),
            'unique_ips': df['ip_address'].nunique(),
            'sources': df['source'].value_counts().to_dict(),
            'environments': df['environment'].value_counts().to_dict(),
            'missing_data': df.isnull().sum().to_dict()
        }

        return summary