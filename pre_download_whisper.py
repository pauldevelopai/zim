import whisper

# Load and cache the model
model = whisper.load_model("small")  # Change "small" to the model you need, such as "base", "medium", or "large"
print("Model downloaded and cached successfully.")