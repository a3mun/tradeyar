from services.analyzer_service import analyze

res = analyze(ticker="BTC-USD", source="wallex", tf_name="۳۰ دقیقه", skip_record=False)

if res:
    print(f"Is Fallback: {res.get('is_fallback')}")
    print(f"Signal: {res.get('signal')}")
    print(f"Source Used: {res.get('source_used')}")
else:
    print("No result (possibly no data).")
