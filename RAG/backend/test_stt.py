import asyncio
import os
from services import audio

# Create dummy wav file
dummy_wav = "dummy.wav"
with open(dummy_wav, "wb") as f:
    f.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")

try:
    print(audio.transcribe_audio(dummy_wav))
except Exception as e:
    print(f"FAILED: {e}")
