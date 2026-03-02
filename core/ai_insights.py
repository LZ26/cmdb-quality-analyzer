import os
from typing import Dict, List, Optional
import json
from unittest import result

class AIInsightsEngine:
    """
    Provides AI-powered insights for CMDB data quality issues.
    
    Capabilities:
    - Smart duplicate resolution recommendations
    - Root cause analysis of data quality issues
    - Natural language explanations
    
    Supports two modes:
    - Live mode: Uses Anthropic Claude API
    - Demo mode: Returns pre-generated insights (no API needed)
    """

    def __init__(self, api_key: Optional[str] = None, demo_mode: Optional[bool] = None):
        """
        Initialize insights engine.

        Args:
            api_key: Anthropic API key (optional, reads from .env if not provided)
            demo_mode: If True, use pre-generated responses. If None, reads from .env
        """
        
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()

        # Determine demo mode
        if demo_mode is None:
            # Check environment variable
            demo_mode_env = os.getenv('DEMO_MODE', 'true').lower()
            self.demo_mode = demo_mode_env in ['true', '1', 'yes']
        else:
            self.demo_mode = demo_mode

        # Get API key
        if api_key is None:
            api_key = os.getenv('ANTHROPIC_API_KEY')

        self.client = None

        if not self.demo_mode and api_key:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=api_key)
                print("AI Insights: Live mode enabled")
            except ImportError:
                print("Warning: anthropic package not available, using demo mode")
                self.demo_mode = True
            except Exception as e:
                print(f"Warning: Could not initialize Anthropic client: {e}")
                self.demo_mode = True
        else:
            print("AI Insights: Demo mode enabled (no API calls)")
            self.demo_mode = True

    def analyze_duplicate_group(self, duplicate_group: Dict, ci_details: List[Dict]) -> Dict:
        """
        Provide AI-powered recommendation for resolving a duplicate group.
        
        Args:
            duplicate_group: Duplicate group info with method and confidence
            ci_details: List of CI record details (dicts with all fields)
            
        Returns:
            Dict with recommendation, reasoning, and actions
        """
        if self.demo_mode:
            return self._demo_duplicate_analysis(duplicate_group, ci_details)
        
        return self._live_duplicate_analysis(duplicate_group, ci_details)

    def analyze_root_causes(self, duplicate_analysis: Dict, quality_scores: Dict) -> Dict:
        """
        Analyze root causes of CMDB data quality issues.
        
        Args:
            duplicate_analysis: Results from duplicate detection
            quality_scores: Data quality scores
            
        Returns:
            Dict with root cause analysis and recommendations
        """
        if self.demo_mode:
            return self._demo_root_cause_analysis(duplicate_analysis, quality_scores)
        
        return self._live_root_cause_analysis(duplicate_analysis, quality_scores)
    
    def _demo_duplicate_analysis(self, duplicate_group: Dict, ci_details: List[Dict]) -> Dict:
        """
        Pre-generated duplicate resolution recommendation (demo mode).
        """

        # Find the "best" record (most complete, most reliable source)
        best_record = max(ci_details, key=lambda x: self._score_record_quality(x))

        return {
            'recommended_action': 'merge_and_keep_primary',
            'primary_record': best_record['ci_name'],
            'records_to_merge': [r['ci_name'] for r in ci_details if r['ci_name'] != best_record['ci_name']],
            'reasoning': f"Recommend keeping '{best_record['ci_name']}' from {best_record['source']} as the primary record. "
                        f"This record has the most complete data and comes from an automated discovey source, "
                        f"making it more reliable than manual imports. The other {len(ci_details)-1} records "
                        f"appear to be the same configuration item with naming variations.",
            'confidence': duplicate_group['confidence'],
            'suggested_canonical_name': best_record['ci_name'],
            'data_to_preserve': self._identify_unique_data(ci_details),
            'remediation_steps': [
                f"1. Designate '{best_record['ci_name']}' as the canonical CI",
                "2. Mege any unique attributes from duplicate records",
                "3. Update references in dependent systems",
                "4. Mark duplicate records for deletion",
                "5. Add discovery rule to prevent future duplicates"
            ]            
        }
    
    def _live_duplicate_analysis(self, duplicate_group: Dict, ci_details: List[Dict]) -> Dict:
        """
        Use Claude API for duplicate resolution recommendation (live mode).
        """
        # Prepare context for Claude
        ci_summary = "\n".join([
            f"- {ci['ci_name']} (IP: {ci.get('ip_address', 'N/A')}, "
            f"Type: {ci.get('ci_type', 'N/A')}, "
            f"Source: {ci['source']}, "
            f"Owner: {ci.get('owner', 'N/A')})"
            for ci in ci_details
        ])
        
        prompt = f"""Analyze this CMDB duplicate group and provide a resolution recommendation.

        Duplicate CIs detected:
        {ci_summary}

        Detection method: {duplicate_group['method']}
        Confidence: {duplicate_group['confidence']}%

        Respond with ONLY valid JSON (no markdown, no explanation before or after). Use this exact structure:
        {{
        "recommended_action": "merge_and_keep_primary",
        "primary_record": "name of primary CI",
        "records_to_merge": ["name1", "name2"],
        "reasoning": "brief explanation in one sentence",
        "suggested_canonical_name": "canonical name",
        "remediation_steps": ["step 1", "step 2", "step 3"]
        }}

        Keep all strings simple with no quotes inside them."""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text.strip()
            
            # Extract JSON - handle various formats
            json_str = response_text
            
            # Remove markdown code blocks if present
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()
            
            # Find JSON object boundaries
            start = json_str.find('{')
            end = json_str.rfind('}') + 1
            if start != -1 and end > start:
                json_str = json_str[start:end]
            
            result = json.loads(json_str)
            
            # Normalize response format
            if isinstance(result.get('primary_record'), dict):
                result['primary_record'] = result['primary_record'].get('name', ci_details[0]['ci_name'])
            
            if 'records_to_merge' in result:
                normalized_merge = []
                for item in result['records_to_merge']:
                    if isinstance(item, dict):
                        normalized_merge.append(item.get('name', ''))
                    else:
                        normalized_merge.append(str(item))
                result['records_to_merge'] = normalized_merge
            
            # Ensure remediation_steps is a list
            if 'remediation_steps' not in result:
                result['remediation_steps'] = [
                    f"1. Keep {result.get('primary_record', 'primary')} as canonical",
                    "2. Merge unique data from duplicates",
                    "3. Mark duplicates for deletion"
                ]
            
            result['confidence'] = duplicate_group['confidence']
            result['data_to_preserve'] = self._identify_unique_data(ci_details)
            
            return result
        
        except Exception as e:
            print(f"API call failed: {e}, falling back to demo mode")
            return self._demo_duplicate_analysis(duplicate_group, ci_details)
    def _demo_root_cause_analysis(self, duplicate_analysis: Dict, quality_scores: Dict) -> Dict:
        """
        Pre-generated root cause analysis (demo mode).
        """
        total_duplicates = duplicate_analysis['total_duplicate_records']
        duplicate_groups = duplicate_analysis['unique_duplicate_groups']
        
        return {
            'summary': f"Identified {total_duplicates} duplicate records across {duplicate_groups} groups. "
                      f"Primary issue is inconsistent naming conventions across discovery sources.",
            'root_causes': [
                {
                    'cause': 'Multiple Discovery Sources with Different Naming Standards',
                    'impact': 'High',
                    'affected_records': total_duplicates,
                    'explanation': 'Network discovery, application discovery, and manual imports use different '
                                  'naming conventions (hyphens vs underscores, case sensitivity). This creates '
                                  'duplicate CIs for the same physical/logical asset.'
                },
                {
                    'cause': 'Lack of Centralized Naming Policy',
                    'impact': 'Medium',
                    'affected_records': total_duplicates,
                    'explanation': 'No enforced naming standard means different teams create CIs with variations '
                                  'like "web-server-01", "web_server_01", "webserver01".'
                },
                {
                    'cause': 'Manual Data Entry Without Validation',
                    'impact': 'Medium',
                    'affected_records': 6,
                    'explanation': 'Manual imports allow free-text entry without validation against existing CIs, '
                                  'leading to duplicates and inconsistent formatting.'
                }
            ],
            'recommendations': [
                {
                    'priority': 'High',
                    'recommendation': 'Implement Naming Standard Policy',
                    'details': 'Define and enforce a standard naming convention (e.g., lowercase with hyphens). '
                              'Add validation rules to discovery sources and manual import workflows.'
                },
                {
                    'priority': 'High',
                    'recommendation': 'Enable Automated Duplicate Prevention',
                    'details': 'Configure ServiceNow reconciliation rules to check for existing CIs by IP address '
                              'and normalized name before creating new records.'
                },
                {
                    'priority': 'Medium',
                    'recommendation': 'Consolidate Discovery Sources',
                    'details': 'Review if all discovery sources are necessary. Consider standardizing on fewer, '
                              'more reliable automated tools rather than mixing automated and manual processes.'
                },
                {
                    'priority': 'Medium',
                    'recommendation': 'Regular CMDB Health Audits',
                    'details': 'Schedule monthly scans using this tool to identify and remediate duplicates '
                              'before they accumulate. Track metrics over time to measure improvement.'
                }
            ],
            'estimated_impact': {
                'duplicate_reduction': '85-95%',
                'data_quality_improvement': f"{100 - quality_scores['completeness']['overall_score']:.0f}% increase in completeness possible",
                'time_savings': '20 hours/month in manual duplicate cleanup'
            }
        }

    def _live_root_cause_analysis(self, duplicate_analysis: Dict, quality_scores: Dict) -> Dict:
        """
        Use Claude API for root cause analysis (live mode).
        """
        prompt = f"""Analyze CMDB data quality issues and identify root causes.

        Data Quality Metrics:
        - Total duplicate records: {duplicate_analysis['total_duplicate_records']}
        - Unique duplicate groups: {duplicate_analysis['unique_duplicate_groups']}
        - Duplicates by method: {duplicate_analysis['duplicates_by_method']}
        - Completeness score: {quality_scores['completeness']['overall_score']}%
        - Consistency score: {quality_scores['consistency']['score']}%

        Respond with ONLY valid JSON (no markdown, no text before or after). Use this exact structure:
        {{
        "summary": "one sentence summary",
        "root_causes": [
            {{"cause": "cause name", "impact": "High", "affected_records": 10, "explanation": "brief explanation"}},
            {{"cause": "another cause", "impact": "Medium", "affected_records": 5, "explanation": "brief explanation"}}
        ],
        "recommendations": [
            {{"priority": "High", "recommendation": "rec name", "details": "brief details"}},
            {{"priority": "Medium", "recommendation": "another rec", "details": "brief details"}}
        ],
        "estimated_impact": {{"duplicate_reduction": "85-95%", "time_savings": "20 hours per month"}}
        }}

        Keep all text short and simple. No quotes or special characters in strings."""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text.strip()
            
            # Extract JSON
            json_str = response_text
            
            # Remove markdown code blocks
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()
            
            # Find JSON object boundaries
            start = json_str.find('{')
            end = json_str.rfind('}') + 1
            if start != -1 and end > start:
                json_str = json_str[start:end]
            
            # Clean common issues
            json_str = json_str.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            # Remove multiple spaces
            while '  ' in json_str:
                json_str = json_str.replace('  ', ' ')
            
            result = json.loads(json_str)
            
            # Validate structure and provide defaults if needed
            if 'summary' not in result:
                result['summary'] = f"Found {duplicate_analysis['total_duplicate_records']} duplicates"
            
            if 'root_causes' not in result or not result['root_causes']:
                result['root_causes'] = [{
                    'cause': 'Multiple discovery sources',
                    'impact': 'High',
                    'affected_records': duplicate_analysis['total_duplicate_records'],
                    'explanation': 'Different naming conventions create duplicates'
                }]
            
            if 'recommendations' not in result or not result['recommendations']:
                result['recommendations'] = [{
                    'priority': 'High',
                    'recommendation': 'Implement naming standards',
                    'details': 'Enforce consistent CI naming across sources'
                }]
            
            if 'estimated_impact' not in result:
                result['estimated_impact'] = {
                    'duplicate_reduction': '85-95%',
                    'time_savings': '20 hours/month'
                }
            
            return result
        
        except Exception as e:
            print(f"API call failed: {e}, falling back to demo mode")
            return self._demo_root_cause_analysis(duplicate_analysis, quality_scores)
    def _score_record_quality(self, record: Dict) -> int:
        """
        Score a CI record's quality (higher = better).
        
        Scoring factors:
        - Automated source > Manual source (+10 points)
        - Complete fields (+2 points each)
        """
        score = 0
        
        # Source reliability
        if 'network_discovery' in record.get('source', ''):
            score += 10
        elif 'app_discovery' in record.get('source', ''):
            score += 8
        
        # Completeness
        required_fields = ['ci_name', 'ip_address', 'ci_type', 'owner']
        for field in required_fields:
            if record.get(field) and str(record[field]) != 'nan':
                score += 2
        
        return score
    
    def _identify_unique_data(self, ci_details: List[Dict]) -> List[str]:
        """
        Identify unique attributes across duplicate records that should be preserved.
        """
        unique_data = []
        
        # Check for different owners
        owners = set(r.get('owner') for r in ci_details if r.get('owner') and str(r.get('owner')) != 'nan')
        if len(owners) > 1:
            unique_data.append(f"Multiple owners identified: {', '.join(owners)}")
        
        # Check for different CI types
        types = set(r.get('ci_type') for r in ci_details if r.get('ci_type') and str(r.get('ci_type')) != 'nan')
        if len(types) > 1:
            unique_data.append(f"Multiple CI types: {', '.join(types)}")
        
        return unique_data if unique_data else ["No conflicting data found"]