import torch
import sys
import streamlit as st
import tempfile
import os
from models import session, Transcription  # Import the session and Transcription model
from fpdf import FPDF
import time
from google.oauth2 import service_account
from google.cloud import compute_v1
import logging
import tensorflow as tf
from google.cloud import speech

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Path to your service account key file
SERVICE_ACCOUNT_FILE = "/Users/paulmcnally/Library/CloudStorage/OneDrive-Personal/PYTHON/WHISPER/podapp-432105-c73aa2e2c6a8.json"

# Create credentials
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE
)

# Set project and zone information
project_id = "podapp-432105"  # Your Google Cloud project ID
zone = "us-central1-a"  # Your instance zone

# Create the Compute Engine client
compute_client = compute_v1.InstancesClient(credentials=credentials)

# List all instances in a specific zone
def list_instances(project, zone):
    logging.info("Listing instances in project: %s, zone: %s", project, zone)
    request = compute_v1.ListInstancesRequest(
        project=project,
        zone=zone
    )
    response = compute_client.list(request)
    if not response.items:
        logging.info("No instances found.")
    else:
        for instance in response.items:
            logging.info("Instance Name: %s, Status: %s, Machine Type: %s", instance.name, instance.status, instance.machine_type)

# Example usage
if __name__ == "__main__":
    logging.info("Checking GPU availability...")
    if torch.cuda.is_available():
        logging.info("GPU is available and will be used.")
    else:
        logging.info("GPU is not available. Using CPU instead.")
    list_instances(project_id, zone)

    # Check GPU availability
    print("Num GPUs Available: ", len(tf.config.list_physical_devices('GPU')))

# Streamlit app UI
st.title("Zimbabwean Court Transcription AI")

# Log the start of the Streamlit app
logging.info("Streamlit app started.")

# File uploader for audio and video files
uploaded_file = st.file_uploader("Upload an audio or video file", type=["mp3", "wav", "m4a", "mp4", "mov"])

# Button to start transcription
if uploaded_file is not None:
    logging.info("File uploaded: %s", uploaded_file.name)
    st.write("File uploaded successfully!")
    st.write(f"File uploaded: {uploaded_file.name}")

    # Save uploaded file to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio_file:
        temp_audio_file.write(uploaded_file.read())
        temp_audio_path = temp_audio_file.name
        logging.info("Temporary audio file created at %s", temp_audio_path)
        st.write(f"Temporary audio file created at {temp_audio_path}")

    # Start transcription
    if st.button("Transcribe Audio/Video"):
        logging.info("Transcription started for file: %s", uploaded_file.name)
        with st.spinner("Transcribing... This may take a while for longer files."):
            st.write("Starting transcription process...")

            # Perform actual transcription
            transcription_text = transcribe_audio(temp_audio_path)
            if transcription_text == "Transcription failed due to an error.":
                st.error("Transcription failed. Please check the logs for more details.")
            else:
                logging.info("Transcription completed for file: %s", uploaded_file.name)
                st.write("Transcription completed.")

                # Display transcription result
                st.subheader("Transcription Result")
                st.text_area("Transcription", transcription_text, height=300)

                # Save transcription to database and as a PDF document
                pdf_file_name = f"{uploaded_file.name.split('.')[0]}.pdf"
                pdf_file_path = os.path.join(os.getcwd(), pdf_file_name)

                # Create and save PDF document
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.cell(200, 10, txt="Transcription", ln=True, align='C')
                pdf.multi_cell(0, 10, transcription_text)
                pdf.output(pdf_file_path)
                logging.info("PDF document created at %s", pdf_file_path)
                st.write(f"PDF document created at {pdf_file_path}")

                # Save transcription and PDF file path in the database
                new_transcription = Transcription(
                    filename=uploaded_file.name,
                    transcription=transcription_text,
                    word_file_path=pdf_file_path  # Consider renaming this field to file_path
                )
                session.add(new_transcription)
                session.commit()
                logging.info("Transcription saved to database for file: %s", uploaded_file.name)
                st.write("Transcription saved to database.")
                st.success("Transcription complete and saved as a PDF document!")

                # Provide a download button for the PDF document
                with open(pdf_file_path, "rb") as pdf_file:
                    st.download_button(
                        label="Download PDF Document",
                        data=pdf_file,
                        file_name=pdf_file_name,
                        mime="application/pdf"
                    )

                # Clean up the temporary audio file
                os.remove(temp_audio_path)
                logging.info("Temporary audio file %s removed.", temp_audio_path)
                st.write(f"Temporary audio file {temp_audio_path} removed.")

# Section to display previously saved transcriptions
st.header("Previously Saved Transcriptions")

transcriptions = session.query(Transcription).all()
if transcriptions:
    for transcription in transcriptions:
        st.write(f"**Filename:** {transcription.filename}")
        st.write(f"**Transcription:** {transcription.transcription}")
        st.write(f"**Timestamp:** {transcription.timestamp}")

        # Provide a download button for each saved PDF document
        if transcription.word_file_path and os.path.exists(transcription.word_file_path):
            with open(transcription.word_file_path, "rb") as pdf_file:
                st.download_button(
                    label=f"Download PDF Document for {transcription.filename}",
                    data=pdf_file,
                    file_name=os.path.basename(transcription.word_file_path),
                    mime="application/pdf"
                )
        st.markdown("---")
else:
    st.write("No transcriptions found in the database.")

def transcribe_audio(file_path):
    try:
        # Initialize a client with the credentials
        client = speech.SpeechClient(credentials=credentials)

        # Load your audio file
        with open(file_path, "rb") as audio_file:
            content = audio_file.read()

        # Configure the audio settings
        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.MP3,  # Adjust encoding for MP3 files
            sample_rate_hertz=44100,  # Adjust based on your audio file's properties
            language_code="en-US",    # Adjust this based on your language
        )

        # Perform the transcription
        logging.info("Using Google Speech-to-Text API for transcription...")
        response = client.recognize(config=config, audio=audio)

        # Extract and return the transcript
        transcript = ""
        for result in response.results:
            transcript += result.alternatives[0].transcript

        return transcript

    except Exception as e:
        logging.error(f"Error occurred during transcription: {e}")
        return "Transcription failed due to an error."