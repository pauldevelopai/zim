# newapp.py

import os
import io
import streamlit as st
from google.cloud import speech
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import subprocess

# Set up Google Cloud Speech client
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/paulmcnally/Desktop/SPEECHTOTEXT/podapp-432105-5225ff04ef25.json"
client = speech.SpeechClient()

# Set up SQLAlchemy
Base = declarative_base()
engine = create_engine('sqlite:///justice.db')
Session = sessionmaker(bind=engine)
session = Session()

class Transcription(Base):
    __tablename__ = 'transcriptions'
    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    transcription = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

def transcribe_audio(file_path):
    st.write("Reading audio file...")
    with io.open(file_path, "rb") as audio_file:
        content = audio_file.read()

    # Determine the encoding based on the file extension
    if file_path.endswith('.mp3'):
        encoding = speech.RecognitionConfig.AudioEncoding.MP3
    elif file_path.endswith('.wav'):
        encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16
    else:
        st.error("Unsupported audio format.")
        return None

    st.write("Sending audio to Google Speech-to-Text API...")
    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=encoding,
        sample_rate_hertz=16000,
        language_code="en-US",
    )

    response = client.recognize(config=config, audio=audio)

    st.write("Processing transcription results...")
    for result in response.results:
        return result.alternatives[0].transcript

def process_file(file_path):
    # Convert video to audio if necessary
    if file_path.endswith(('.mp4', '.mkv', '.avi')):
        st.write("Converting video to audio...")
        audio_path = 'temp_audio.wav'
        subprocess.run(['ffmpeg', '-i', file_path, '-q:a', '0', '-map', 'a', audio_path])
        file_path = audio_path

    transcription = transcribe_audio(file_path)
    if transcription:
        st.write("Storing transcription in the database...")
        new_transcription = Transcription(filename=os.path.basename(file_path), transcription=transcription)
        session.add(new_transcription)
        session.commit()

    if file_path == 'temp_audio.wav':
        os.remove(file_path)

    return transcription

def main():
    st.title("Zimbabwean Justice AI")
    st.write("Upload an audio or video file to transcribe it using Google Speech-to-Text.")

    uploaded_file = st.file_uploader("Choose an audio or video file", type=["mp3", "wav", "mp4", "mkv", "avi"])

    if uploaded_file is not None:
        file_path = f"temp_{uploaded_file.name}"
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.write(f"File '{uploaded_file.name}' uploaded successfully.")

        if st.button("Transcribe Audio/Video"):
            st.write("Starting transcription process...")
            transcription = process_file(file_path)
            st.write("Transcription completed:")
            st.text(transcription)

            os.remove(file_path)

if __name__ == "__main__":
    main()