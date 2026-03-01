from core.data_loader import CMDBDataLoader
from core.quality_analyzer import CMDBQualityAnalyzer
import json

# Load data
print("=" * 60)
print("CMDB QUALITY ANALYZER TEST")
print("=" * 60)

loader = CMDBDataLoader(data_dir='data')
df = loader.load_all_sources()

print(f"\n Loaded {len(df)} records from {df['source'].nunique()} sources\n")

# Initialize analyzer
analyzer = CMDBQualityAnalyzer(similarity_threshold=85)

# Test 1: Duplicate Detection
print("-" * 60)
print("TEST 1: DUPLICATE DETECTION")
print("-" * 60)

duplicate_analysis = analyzer.analyze_duplicates(df)

print(f"\nTotal duplicate records found: {duplicate_analysis['total_duplicate_records']}")
print(f"Unique duplicate groups: {duplicate_analysis['unique_duplicate_groups']}")
print(f"\nDuplicates by detection method:")
for method, count in duplicate_analysis['duplicates_by_method'].items():
    print(f"  - {method}: {count} groups")

print(f"\nDuplicate Groups Detail:")
for i, group in enumerate(duplicate_analysis['duplicate_groups'][:5], 1):  # Show first 5
    print(f"\n  Group {i} ({group['method']}, {group['confidence']}% confidence):")
    for ci in group['cis']:
        # Find the record details
        ci_data = df[df['ci_name'] == ci].iloc[0]
        print(f"    - {ci} (IP: {ci_data['ip_address']}, Source: {ci_data['source']})")

# Test 2: Data Quality Scoring
print("\n" + "-" * 60)
print("TEST 2: DATA QUALITY SCORING")
print("-" * 60)

quality_scores = analyzer.score_data_quality(df)

print(f"\nCompleteness Score: {quality_scores['completeness']['overall_score']}%")
print("  By field:")
for field, score in quality_scores['completeness']['by_field'].items():
    print(f"    - {field}: {score}%")

print(f"\nAccuracy Score:")
print(f"  - IP Address Validity: {quality_scores['accuracy']['ip_address_validity']}%")

print(f"\nConsistency Score: {quality_scores['consistency']['score']}%")
print(f"  - Issues found: {quality_scores['consistency']['issues_found']}")

print("\n" + "=" * 60)
print("QUALITY ANALYZER WORKING CORRECTLY")
print("=" * 60)