# ✨ NoteLecture.AI

**NoteLecture.AI** is an intelligent web application designed to automatically process lecture recordings and presentations, synchronizing spoken content with the corresponding slides. Upload your video (local file or URL) and presentation (PPTX/PDF), and get back an interactive, searchable lecture experience.

*_(Live Demo Not Available Yet, IN PROGRESS)_*


## 🚀 Features

### Core Functionality
*   📹 **Flexible Video Input:** Upload local video files or provide URLs (YouTube, Zoom recordings, etc., processed via `yt-dlp`).
*   📄 **Presentation Support:** Accepts presentation files in `.pptx` and `.pdf` formats.
*   🔊 **Automatic Audio Extraction:** Seamlessly extracts audio tracks from video inputs using `moviepy`.

### Intelligent Processing & Synchronization
*   🤖 **AI-Powered Transcription:** Leverages the [IVRIT.AI API](https://hebrew-ai.com/) for accurate audio-to-text transcription (specialized for Hebrew).
*   🖼️ **Slide Image Extraction:** Converts presentation slides/pages into individual images using `PyMuPDF` and `python-pptx`.
*   💡 **Advanced Slide Matching:** Employs computer vision (OpenCV) to analyze video frames and synchronize them with the correct presentation slide using techniques like:
    *   ORB Feature Matching 
    *   BRISK Feature Matching
    *   SIFT Feature Matching
    *   Template Matching 
*   ⏱️ **Timestamped Synchronization:** Precisely maps transcribed text segments to the corresponding slide based on timing in the video.

