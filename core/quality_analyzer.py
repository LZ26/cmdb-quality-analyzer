import pandas as pd
from typing import Dict, List, Tuple
from rapidfuzz import fuzz
import re

class CMDBQualityAnalyzer:
    """
    Analyzes CMDB data quality and detects duplicates.
    
    Key capabilities:
    - Detect exact and fuzzy duplicates
    - Score data completeness and accuracy
    - Identify data quality issues
    - Group duplicate CIs with confidence scores
    """

    def __init__(self, similarity_threshold: int = 85):
        """
        Initialize analyzer.
        
        Args:
            similarity_threshold: Minimum similarity score (0-100)
        """
        self.similarity_threshold = similarity_threshold
        self.required_fields = ['ci_name', 'ip_address', 'ci_type', 'environment', 'owner', 'status']

    def analyze_duplicates(self, df: pd.DataFrame) -> Dict:
        """
        Comprehensive duplicate detection using multiple methods.
        
        Returns:
            Dictionary containing:
            - duplicate_groups: List of duplicate CI groups
            - total_duplicates: Count of duplicate records
            - duplicates_by_method: Breakdown by detection method
        """
        duplicate_groups = []
        seen_records = set() # Track records already in a group

        # Method 1: Exact IP match
        ip_duplicates = self._find_ip_duplicates(df)
        for group in ip_duplicates:
            duplicate_groups.append({
                'cis': group,
                'method': 'exact_ip_match',
                'confidence': 95
            })
            seen_records.update(group)
        
        # Method 2: Exact normalized name match
        name_duplicates = self._find_normalized_name_duplicates(df, seen_records)
        for group in name_duplicates:
            duplicate_groups.append({
                'cis': group,
                'method': 'exact_name_match',
                'confidence': 90
            })
            seen_records.update(group)

        # Method 3: Fuzzy name similarity
        fuzzy_duplicates = self._find_fuzzy_duplicates(df, seen_records)
        for group, score in fuzzy_duplicates:
            duplicate_groups.append({
                'cis': group,
                'method': 'fuzzy_name_match',
                'confidence': score
            })
        
        # Calculate statistics
        total_duplicate_records = sum(len(g['cis']) for g in duplicate_groups)

        method_counts = {}
        for group in duplicate_groups:
            method = group['method']
            method_counts[method] = method_counts.get(method, 0) + 1
        
        return {
            'duplicate_groups': duplicate_groups,
            'total_duplicate_records': total_duplicate_records,
            'unique_duplicate_groups': len(duplicate_groups),
            'duplicates_by_method': method_counts
        }
    
    def _find_ip_duplicates(self, df: pd.DataFrame) -> List[List[str]]:
        """
        Find CIs with identical IP addresses.
        
        Logic: Group by IP address, keep groups with 2+ CIs
        """
        duplicate_groups = []

        # Remove rows with missing IPs
        df_with_ip = df[df['ip_address'].notna()].copy()

        # Group by IP address
        ip_groups = df_with_ip.groupby('ip_address')['ci_name'].apply(list)

        # Keep only groups with 2+ items
        for ip, ci_names in ip_groups.items():
            if len(ci_names) > 1:
                duplicate_groups.append(ci_names)
        
        return duplicate_groups
    
    def _find_normalized_name_duplicates(self, df: pd.DataFrame, seen_records: set) -> List[List[str]]:
        """
        Find CIs with identical normalized names (excluding already found duplicates).
        
        Logic: Group by ci_name_normalized, exclude records already in IP duplicate groups
        """
        duplicate_groups = []

        # Filter out already-found duplicates
        df_unseen = df[~df['ci_name'].isin(seen_records)].copy()

        # Group by normalized name
        name_groups = df_unseen.groupby('ci_name_normalized')['ci_name'].apply(list)

        # Keep only groups with 2+ items
        for normalized_name, ci_names in name_groups.items():
            if len(ci_names) > 1:
                duplicate_groups.append(ci_names)

        return duplicate_groups
    
    def _find_fuzzy_duplicates(self, df: pd.DataFrame, seen_records: set) -> List[Tuple[List[str], int]]:
        """
        Find CIs with similar names using fuzzy string matching.
        
        Logic:
        - Compare each unseen CI name with all others
        - Use Lavenshtein distance (character edit distance)
        - If similarity ≥ threshold, group as potential duplicate
        """
        duplicate_groups = []

        # Filter out already-found duplicates
        df_unseen = df[~df['ci_name'].isin(seen_records)].copy()
        ci_names = df_unseen['ci_name'].unique().tolist()

        checked_pairs = set() # Track pairs already compared

        for i, name1 in enumerate(ci_names):
            for name2 in ci_names[i+1:]:
                # Skip if we've already checked this pair
                pair = tuple(sorted([name1, name2]))
                if pair in checked_pairs:
                    continue

                # Calculate similarity score (0-100)
                similarity = fuzz.ratio(name1.lower(), name2.lower())

                if similarity >= self.similarity_threshold:
                    duplicate_groups.append(([name1, name2], similarity))
                    checked_pairs.add(pair)
        
        return duplicate_groups
    
    def score_data_quality(self, df: pd.DataFrame) -> Dict:
        """
        Calculate data quality metrics.
        
        Metrics:
        - Completeness: % of required fields filled
        - Accuracy: % of records with valid data formats
        - Consistency: % of records with consistent cross-field values
        """
        total_records = len(df)

        # Completeness Score
        completeness_scores = {}
        for field in self.required_fields:
            if field in df.columns:
                filled = df[field].notna().sum()
                completeness_scores[field] = (filled / total_records) * 100

        overall_completeness = sum(completeness_scores.values()) / len(completeness_scores)

        # Accuracy Score (validate IP addresses and data formats)
        valid_ips = df['ip_address'].apply(self._is_valid_ip).sum()
        ip_accuracy = (valid_ips / df['ip_address'].notna().sum() * 100) if df['ip_address'].notna().sum() > 0 else 0

        # Consistency Score (check for conflicting data)
        # Example: same IP with different ci_types
        consistency_issues = self._find_consistency_issues(df)
        consistency_score = 100 - (len(consistency_issues) / total_records * 100)

        return {
            'completeness': {
                'overall_score': round(overall_completeness, 2),
                'by_field': {k: round(v, 2) for k, v in completeness_scores.items()}
            },
            'accuracy': {
                'ip_address_validity': round(ip_accuracy, 2)
            },
            'consistency': {
                'score': round(consistency_score, 2),
                'issues_found': len(consistency_issues)
            }
        }
    
    def _is_valid_ip(self, ip: str) -> bool:
        """
        Validate IP address format.
        
        Uses regex to check if IP follows xxx.xxx.xxx.xxx pattern
        """
        if pd.isna(ip):
            return False
        
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(ip_pattern, str(ip)):
            return False
        
        # Check each octet is between 0 and 255
        try:
            octets = str(ip).split('.')
            return all(0 <= int(octet) <= 255 for octet in octets)
        except:
            return False
    
    def _find_consistency_issues(self, df: pd.DataFrame) -> List[Dict]:
        """
        Find records with conflicting information.
        
        Example: Same IP address but different ci_types
        """
        issues = []

        # Check for same IP with different CI types
        df_with_ip = df[df['ip_address'].notna() & df['ci_type'].notna()]

        for ip in df_with_ip['ip_address'].unique():
            ip_records = df_with_ip[df_with_ip['ip_address'] == ip]
            unique_types = ip_records['ci_type'].unique()

            if len(unique_types) > 1:
                issues.append({
                    'ip_address': ip,
                    'issue': 'multiple_ci_types',
                    'values': unique_types.tolist()
                })
        
        return issues