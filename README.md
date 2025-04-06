# ✨ NoteLecture.AI

**NoteLecture.AI** is an intelligent web application designed to automatically process lecture recordings and presentations, synchronizing spoken content with the corresponding slides. Upload your video (local file or URL) and presentation (PPTX/PDF), and get back an interactive, searchable lecture experience.
*(Live Demo Not Available Yet, SOON WILL BE DEPLOYED)*

<details>
<summary> 📱 Screenshots</summary>

![Homepage](screenshots/Screenshot%202025-04-06%20at%2012.16.49.png)
![Upload Interface](screenshots/Screenshot%202025-04-06%20at%2012.17.19.png)
![Lecture View](screenshots/Screenshot%202025-04-06%20at%2013.12.56.png)
</details>

<details>
<summary> 🚀 Features</summary>

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
</details>

## 🔧 Tech Stack

### Backend
- **Framework:** FastAPI (Python)
- **Database:** MySQL
- **Transcription Service:** IVRIT.AI
- **Video Processing:** OpenCV, MoviePy, yt-dlp
- **Document Processing:** PyMuPDF, python-pptx

### Frontend
- **Framework:** React.JS with TypeScript
- **Styling:** Tailwind CSS
- **Routing:** React Router
- **HTTP Client:** Axios
- **Icons:** Lucide React
