import os
import uuid
import soundfile as sf
import numpy as np

# Monkey patch torchaudio to fix WhisperX crash on newer PyTorch versions
import torchaudio
if getattr(torchaudio, "AudioMetaData", None) is None:
    class AudioMetaData:
        pass
    torchaudio.AudioMetaData = AudioMetaData

def synthesize_audio(text: str, session_id: str) -> str:
    """
    Synthesize speech using Kokoro.
    Returns the file path to the generated .wav file.
    """
    if not text.strip():
        return ""
        
    os.makedirs("data/audio", exist_ok=True)
    filename = f"session_{session_id}_{uuid.uuid4().hex[:8]}.wav"
    filepath = os.path.join("data", "audio", filename)
    
    try:
        from kokoro import KPipeline
        pipeline = KPipeline(lang_code='a') 
        generator = pipeline(text, voice='af_bella', speed=1)
        
        audio_chunks = []
        for i, (gs, ps, audio) in enumerate(generator):
            audio_chunks.append(audio)
            
        if audio_chunks:
            full_audio = np.concatenate(audio_chunks)
            sf.write(filepath, full_audio, 24000)
            return filepath
    except Exception as e:
        print(f"Kokoro Synthesis Error (this is expected if dependencies are missing): {e}")
        print("Attempting to use gTTS fallback...")
        try:
            from gtts import gTTS
            filepath = filepath.replace(".wav", ".mp3")
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(filepath)
            return filepath
        except Exception as fallback_e:
            print(f"gTTS fallback also failed: {fallback_e}")
            
    return ""

def extract_timestamps(audio_path: str, text: str = "") -> list:
    """
    Use WhisperX to align words in the audio file and return JSON timing bounds.
    If WhisperX fails, estimates timestamps from the text.
    """
    if not audio_path or not os.path.exists(audio_path):
        return []
        
    try:
        import whisperx
        device = "cpu" # Defaulting to CPU. Switch to 'cuda' if environment supports it.
        
        # Transcribe
        model = whisperx.load_model("base", device=device, compute_type="int8")
        audio = whisperx.load_audio(audio_path)
        result = model.transcribe(audio)
        
        # Align
        model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
        result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
        
        # Extract precise words
        timestamps = []
        for segment in result["segments"]:
            for word in segment.get("words", []):
                if "start" in word and "end" in word:
                    timestamps.append({
                        "word": word["word"],
                        "start": word["start"],
                        "end": word["end"]
                    })
        return timestamps
    except Exception as e:
        print(f"WhisperX Alignment Error: {e}")
        print("Falling back to proportional audio duration timestamps...")
        
        # Robust Fallback: Calculate exact duration and distribute across words proportionally
        if text and audio_path:
            try:
                import soundfile as sf
                audio_info = sf.info(audio_path)
                total_duration = audio_info.frames / audio_info.samplerate
                
                import re
                words = [w for w in text.split() if re.search(r'[A-Za-z0-9]', w)]
                # Calculate total characters excluding spaces to weight the duration
                total_chars = sum(len(w) for w in words)
                time_per_char = total_duration / max(1, total_chars)
                
                timestamps = []
                current_time = 0.0
                for word in words:
                    duration = len(word) * time_per_char
                    timestamps.append({
                        "word": word,
                        "start": current_time,
                        "end": current_time + duration
                    })
                    current_time += duration
                return timestamps
            except Exception as e_fallback:
                print(f"Fallback timestamp generation failed: {e_fallback}")
                
        return []

def transcribe_audio(audio_path: str) -> str:
    """
    Use Groq API (whisper-large-v3) to transcribe user audio to text.
    """
    if not audio_path or not os.path.exists(audio_path):
        return ""
        
    try:
        import httpx
        
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise Exception("GROQ_API_KEY not found in environment")
            
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        with open(audio_path, "rb") as f:
            files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
            data = {"model": "whisper-large-v3"}
            
            with httpx.Client() as client:
                response = client.post(url, headers=headers, files=files, data=data, timeout=30.0)
                
                if response.status_code == 200:
                    text = response.json().get("text", "")
                    return text.strip()
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
        return text.strip()
    except Exception as e:
        print(f"Groq STT Error: {e}")
        return f"[ERROR] Groq STT failed: {e}"

