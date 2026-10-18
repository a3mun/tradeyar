from services.analyzer_service import analyze

r = analyze(ticker="BTC-USD", source="nobitex", tf_name="۱۵ دقیقه", skip_record=True)

if r:
    print(f"Signal: {r.get('signal')}")
    print(f"Confidence: {r.get('confidence')}")
    print(f"Direction: {r.get('direction')}")
    print(f"Is Fallback: {r.get('is_fallback')}")
    print(f"Source Used: {r.get('source_used')}")
else:
    print("No result (analyze returned None)")
