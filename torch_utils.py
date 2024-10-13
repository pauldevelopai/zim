import torch_utils
device = "cuda" if torch_utils.cuda.is_available() else "cpu"
model = whisper.load_model("small", device=device)