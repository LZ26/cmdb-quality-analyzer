from core.data_loader import CMDBDataLoader

# Load data
loader = CMDBDataLoader(data_dir='data')
df = loader.load_all_sources()

# Print summary
print(f"Total records loaded: {len(df)}")
print(f"\nRecords by source:")
print(df['source'].value_counts())
print(f"\nSample of loaded data:")
print(df[['ci_name', 'ci_name_normalized', 'ip_address', 'source']].head(10))
print(f"\nData summary:")
import json
print(json.dumps(loader.get_data_summary(df), indent=2))