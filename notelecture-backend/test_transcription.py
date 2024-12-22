import asyncio
from app.services.transcription import TranscriptionService
import arabic_reshaper

async def test_transcription():
    service = TranscriptionService()

    # Replace with your test video file path
    video_path = "test_video.mp4"

    print("Extracting audio...")
    audio_path = await service.extract_audio(video_path)

    print("Starting transcription...")
    result = await service.transcribe(audio_path)

    print("\nTranscription Result:")
    print("===================")

    for segment in result["segments"]:
        # Reshape the text
        reshaped_text = arabic_reshaper.reshape(segment['text'])
        # Reverse the text for RTL display in LTR context
        displayed_text = reshaped_text[::-1]
        print(f"\nTimestamp: {segment['start_time']:.2f}s - {segment['end_time']:.2f}s")
        print(f"Text: {displayed_text}")

    # Cleanup
    await service.cleanup(audio_path)

if __name__ == "__main__":
    asyncio.run(test_transcription())