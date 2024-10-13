import os
import io
import openai
import streamlit as st
from google.cloud import speech
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import subprocess
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# Get the API keys from the environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# Initialize the OpenAI client with the API key
openai.api_key = OPENAI_API_KEY
client = openai

# Set up Google Cloud Speech client
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/paulmcnally/Desktop/SPEECHTOTEXT/podapp-432105-5225ff04ef25.json"
speech_client = speech.SpeechClient()  # Renamed to avoid conflict with OpenAI client

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

    response = speech_client.recognize(config=config, audio=audio)  # Use speech_client

    st.write("Processing transcription results...")
    transcript = ''
    for result in response.results:
        transcript += result.alternatives[0].transcript + '\n'
    return transcript

def process_file(file_path):
    # Convert video to audio if necessary
    if file_path.endswith(('.mp4', '.mkv', '.avi')):
        st.write("Converting video to audio...")
        audio_path = 'temp_audio.wav'
        subprocess.run(['ffmpeg', '-i', file_path, '-q:a', '0', '-map', 'a', audio_path])
        file_path = audio_path

    # Display a progress bar while transcribing
    progress_bar = st.progress(0)
    transcription = transcribe_audio(file_path)
    progress_bar.progress(100)

    if file_path == 'temp_audio.wav':
        os.remove(file_path)

    return transcription

def save_transcription_to_db():
    try:
        new_transcription = Transcription(
            filename=st.session_state['filename'],
            transcription=st.session_state['transcription']
        )
        session.add(new_transcription)
        session.commit()
        st.success("Transcript saved successfully.")
        # Set the saved flag to True
        st.session_state['transcription_saved'] = True
        # Refresh the transcripts list
        load_transcripts()
    except Exception as e:
        session.rollback()
        st.error(f"Failed to save transcription: {e}")
        st.write(f"Error details: {e}")

def save_transcription_as_txt(transcription, filename):
    txt_path = f"{filename}.txt"
    with open(txt_path, "w") as txt_file:
        txt_file.write(transcription)
    return txt_path

def load_transcripts():
    transcripts = session.query(Transcription).order_by(Transcription.timestamp.desc()).all()
    transcript_titles = [f"{t.filename} - {t.timestamp.strftime('%Y-%m-%d %H:%M:%S')}" for t in transcripts]
    st.session_state['transcripts'] = transcripts
    st.session_state['transcript_titles'] = transcript_titles

def summarize_transcript(transcription_text):
    st.write("Generating summary...") 
    try:
        response = client.chat.completions.create(model="gpt-4",  # Use 'gpt-3.5-turbo' if you don't have access to GPT-4
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes legal transcripts."},
            {"role": "user", "content": f"Please provide a concise summary of the following transcript:\n\n{transcription_text}"}
        ])
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Failed to generate summary: {e}")
        return None

def chat_with_database(user_input):
    # Ensure 'transcripts' is initialized in session state
    if 'transcripts' not in st.session_state:
        st.session_state['transcripts'] = []

    # Combine all transcriptions into one context
    all_transcriptions = "\n\n".join([t.transcription for t in st.session_state['transcripts']])
    
    try:
        response = client.chat.completions.create(model="gpt-4",  
        messages=[
            {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided legal transcripts."},
            {"role": "assistant", "content": f"The following are transcripts from legal proceedings:\n\n{all_transcriptions}"},
            {"role": "user", "content": user_input}
        ])
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Failed to generate response: {e}")
        return None

def main():
    st.title("Justice AI")
    st.write("Upload an audio or video file to transcribe it using Google Speech-to-Text.")

    # Initialize session state variables if they don't exist
    if 'transcription' not in st.session_state:
        st.session_state['transcription'] = None
    if 'filename' not in st.session_state:
        st.session_state['filename'] = None
    if 'transcription_saved' not in st.session_state:
        st.session_state['transcription_saved'] = False
    if 'transcripts' not in st.session_state:
        load_transcripts()

    # Sidebar for displaying saved transcripts
    st.sidebar.title("Saved Transcripts")
    if st.session_state['transcripts']:
        selected_transcript = st.sidebar.selectbox(
            "Select a transcript",
            [""] + st.session_state['transcript_titles']
        )
        if selected_transcript and selected_transcript != "":
            selected_index = st.session_state['transcript_titles'].index(selected_transcript)
            selected_transcription = st.session_state['transcripts'][selected_index]
            st.sidebar.write("Filename:", selected_transcription.filename)
            st.sidebar.write("Timestamp:", selected_transcription.timestamp)
            st.sidebar.text_area(
                "Transcription",
                selected_transcription.transcription,
                height=200,
                key=f"sidebar_transcription_{selected_transcription.id}"
            )
            # Summarize Button
            if st.sidebar.button("Summarize Transcript", key=f"summarize_{selected_transcription.id}"):
                summary = summarize_transcript(selected_transcription.transcription)
                if summary:
                    st.sidebar.subheader("Summary")
                    st.sidebar.write(summary)
            # Generate TXT and provide download button
            txt_path = save_transcription_as_txt(selected_transcription.transcription, selected_transcription.filename)
            with open(txt_path, "rb") as txt_file:
                st.sidebar.download_button(
                    label="Download Transcription as TXT",
                    data=txt_file,
                    file_name=f"{selected_transcription.filename}.txt",
                    mime="text/plain",
                    key=f"sidebar_download_{selected_transcription.id}"
                )
            # Clean up the generated TXT file
            os.remove(txt_path)
    else:
        st.sidebar.write("No transcripts available.")

    uploaded_file = st.file_uploader("Choose an audio or video file", type=["mp3", "wav", "mp4", "mkv", "avi"])

    if uploaded_file is not None:
        file_path = f"temp_{uploaded_file.name}"
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.write(f"File '{uploaded_file.name}' uploaded successfully.")

        if st.button("Transcribe Audio/Video"):
            st.write("Starting transcription process...")
            transcription = process_file(file_path)
            if transcription:
                st.write("Transcription completed:")
                st.text_area(
                    "Transcription",
                    transcription,
                    height=200,
                    key="main_transcription"
                )
                # Store transcription and filename in session state
                st.session_state['transcription'] = transcription
                st.session_state['filename'] = uploaded_file.name
                st.session_state['transcription_saved'] = False  # Reset saved state

                # Generate TXT and provide download button
                txt_path = save_transcription_as_txt(transcription, uploaded_file.name)
                with open(txt_path, "rb") as txt_file:
                    st.download_button(
                        label="Download Transcription as TXT",
                        data=txt_file,
                        file_name=f"{uploaded_file.name}.txt",
                        mime="text/plain"
                    )
                # Clean up the generated TXT file
                os.remove(txt_path)
            else:
                st.error("Transcription failed.")
            os.remove(file_path)

    # Display "Save to Database" button if transcription is available and not yet saved
    if st.session_state['transcription'] and not st.session_state['transcription_saved']:
        st.button("Save to Database", on_click=save_transcription_to_db)

    st.header("Chat with the Transcripts")
    user_input = st.text_input("Ask a question about the transcripts:")
    if user_input:
        answer = chat_with_database(user_input)
        if answer:
            st.write("**Answer:**")
            st.write(answer)

if __name__ == "__main__":
    main()