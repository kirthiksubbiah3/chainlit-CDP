import chainlit as cl
from io import BytesIO
import wave
import logging
from google.cloud import speech
from google.oauth2 import service_account
from config import app_config
from utils import generate_response

logger = logging.getLogger(__name__)

mcp_servers_config_to_pass = app_config.mcp_servers_config_to_pass
mcp_service_config = app_config.mcp_service_config
profiles = app_config.profiles
starters = app_config.starters
env = app_config.env
gcp_credentials_path = app_config.gcp_credentials_path

# Setup Google Cloud Speech client
credentials = service_account.Credentials.from_service_account_file(
    gcp_credentials_path
)
client = speech.SpeechClient(credentials=credentials)


@cl.on_audio_start
async def on_audio_start():
    # Initialize buffer in session for audio chunks
    cl.user_session.set("audio_buffer", BytesIO())
    return True


@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    audio_buffer = cl.user_session.get("audio_buffer")
    audio_buffer.write(chunk.data)
    cl.user_session.set("audio_buffer", audio_buffer)
    return True


@cl.on_audio_end
async def on_audio_end():
    audio_buffer = cl.user_session.get("audio_buffer")
    if not audio_buffer:
        await cl.Message(content="No audio recorded. Please try again.").send()
        return

    raw_audio = audio_buffer.getvalue()

    # Convert raw bytes to WAV format with header
    wav_io = BytesIO()
    with wave.open(wav_io, "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit samples
        wav_file.setframerate(16000)  # Sample rate (match mic/sample rate)
        wav_file.writeframes(raw_audio)
    wav_io.seek(0)
    wav_bytes = wav_io.read()

    # Prepare Google STT request
    audio = speech.RecognitionAudio(content=wav_bytes)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
        enable_automatic_punctuation=True,
    )

    # Call Google STT API
    response = client.recognize(config=config, audio=audio)

    # Extract transcribed text
    transcription = " ".join(
        [result.alternatives[0].transcript for result in response.results]
    ).strip()

    if not transcription:
        logger.warning("No transcription obtained from audio.")
        await cl.Message(content="Sorry, I didn't catch that. Please try again.").send()
        return

    await cl.Message(
        content=f"{transcription}",
        author="user",
        type="user_message"
    ).send()

    await generate_response(
        transcription,
        mcp_servers_config_to_pass,
        mcp_service_config,
        profiles,
        starters,
        env,
    )
