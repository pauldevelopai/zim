import torch

if torch.backends.mps.is_available():
    device = "mps"
    print("MPS backend is available. Running on GPU.")
else:
    device = "cpu"
    print("MPS backend is not available. Running on CPU.")