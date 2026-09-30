import streamlit as st

st.title("تست st.iframe")

# تست ۱: با data URL
html = """
<!DOCTYPE html>
<html><body>
<h1>Hello from iframe</h1>
<script>
document.body.innerHTML += '<p>JS اجرا شد!</p>';
</script>
</body></html>
"""

# این رو تست کن:
try:
    st.iframe(f"data:text/html;charset=utf-8,{html}", height=100)
    st.success("st.iframe کار کرد!")
except Exception as e:
    st.error(f"st.iframe خطا: {e}")
