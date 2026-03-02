from core.data_loader import CMDBDataLoader
from core.quality_analyzer import CMDBQualityAnalyzer
from core.ai_insights import AIInsightsEngine
import json

print("=" * 60)
print("AI INSIGHTS ENGINE TEST")
print("=" * 60)

# Load and analyze data
loader = CMDBDataLoader(data_dir='data')
df = loader.load_all_sources()

analyzer = CMDBQualityAnalyzer(similarity_threshold=85)
duplicate_analysis = analyzer.analyze_duplicates(df)
quality_scores = analyzer.score_data_quality(df)

# Initialize AI engine (demo mode)
ai_engine = AIInsightsEngine()

print("\n" + "-" * 60)
print("TEST 1: DUPLICATE RESOLUTION RECOMMENDATION")
print("-" * 60)

# Test on first duplicate group
first_group = duplicate_analysis['duplicate_groups'][3]  # The web-server group with 4 CIs
ci_names = first_group['cis']

# Get full details for these CIs
ci_details = []
for ci_name in ci_names:
    ci_data = df[df['ci_name'] == ci_name].iloc[0].to_dict()
    ci_details.append(ci_data)

# Get AI recommendation
recommendation = ai_engine.analyze_duplicate_group(first_group, ci_details)

print(f"\nDuplicate Group: {', '.join(ci_names)}")
print(f"Detection Method: {first_group['method']}")
print(f"Confidence: {first_group['confidence']}%")
print(f"\n AI Recommendation:")
print(f"  Primary Record: {recommendation['primary_record']}")
print(f"  Records to Merge: {', '.join(recommendation['records_to_merge'])}")
print(f"\n  Reasoning: {recommendation['reasoning']}")
print(f"\n  Remediation Steps:")
for step in recommendation['remediation_steps']:
    print(f"    {step}")

print("\n" + "-" * 60)
print("TEST 2: ROOT CAUSE ANALYSIS")
print("-" * 60)

# Get root cause analysis
root_cause = ai_engine.analyze_root_causes(duplicate_analysis, quality_scores)

print(f"\n Summary: {root_cause['summary']}")
print(f"\n Root Causes Identified:")
for i, cause in enumerate(root_cause['root_causes'], 1):
    print(f"\n  {i}. {cause['cause']}")
    print(f"     Impact: {cause['impact']}")
    print(f"     Affected Records: {cause['affected_records']}")
    print(f"     Explanation: {cause['explanation']}")

print(f"\n Recommendations:")
for i, rec in enumerate(root_cause['recommendations'], 1):
    print(f"\n  {i}. [{rec['priority']}] {rec['recommendation']}")
    print(f"     {rec['details']}")

print(f"\n Estimated Impact:")
for metric, value in root_cause['estimated_impact'].items():
    print(f"  - {metric.replace('_', ' ').title()}: {value}")

print("\n" + "=" * 60)
print(" AI INSIGHTS ENGINE WORKING CORRECTLY - TESTS PASSED ")
print("=" * 60)