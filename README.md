# ✨ NoteLecture.AI ✨

NoteLecture.AI is an intelligent web application designed to automatically process lecture recordings and presentations. It transcribes the audio, synchronizes the spoken content with the corresponding presentation slides, and provides an interactive, searchable, and summarizable lecture experience.

<br/>

**🚀 Deployment Status: Coming Soon! 🚀**


<br/>

<details>
<summary>📱 Screenshots</summary>

**Homepage:**
![Homepage Screenshot](screenshots/Screenshot%202025-04-06%20at%2012.16.49.png)

**Upload Interface:**
![Upload Interface Screenshot](screenshots/Screenshot%202025-04-06%20at%2012.17.19.png)

**Lecture Loading State (Processing):**
![Lecture Loading Screenshot](screenshots/Screenshot%202025-04-09%20at%2017.01.11.png)

**Lecture View Interface (Completed):**
![Lecture View Screenshot](screenshots/Screenshot%202025-04-09%20at%2017.01.53.png) {/* <<< CORRECTED FILENAME HERE */}

</details>

---

## 💡 Features

### Core Input & Processing
*   📹 **Flexible Video Input:** Handles local video files or URLs (e.g., YouTube, Zoom recordings) processed via `yt-dlp`.
*   📄 **Presentation Support:** Accepts presentation files in pdf and pptx formats.
*   🔊 **Automatic Audio Extraction:** Seamlessly extracts audio tracks from video inputs using `moviepy`.
*   🖼️ **Slide Image Extraction:** Converts PDF pages into individual slide images using `PyMuPDF` (`fitz`).

### Intelligent Analysis & Synchronization
*   🤖 **AI-Powered Transcription:** Leverages the [IVRIT.AI API](https://hebrew-ai.com/) for accurate audio-to-text transcription, optimized for Hebrew.
*   💡 **Slide-to-Video Synchronization:** Employs OpenCV feature matching (ORB detector, BFMatcher) to analyze video frames and determine the active slide, with temporal smoothing.
*   ⏱️ **Timestamped Transcription Mapping:** Precisely maps transcribed text segments to the corresponding slide based on video timing and slide detection.
*   ✍️ **AI-Powered Summarization:** Utilizes OpenAI to generate concise summaries for the transcribed text associated with each slide, available on demand.

### User Experience
*   🖥️ **Interactive Lecture View:** Displays the synchronized presentation slide alongside its corresponding transcription segments.
*   🔄 **Status Tracking:** Provides real-time updates on the processing status (e.g., Downloading, Transcribing, Matching, Completed, Failed).
*   ✨ **On-Demand Summaries:** Generate AI summaries for individual slides after processing is complete.

---

## 🤔 How It Works (High-Level)

1.  **Upload:** The user provides a video (file or URL) and a PDF presentation via the web interface.
2.  **Backend Processing:**
    *   The system extracts audio from the video (`moviepy`, `yt-dlp`).
    *   Presentation slides are converted to images (`PyMuPDF`).
    *   Audio is sent to IVRIT.AI for transcription.
    *   Video frames are analyzed (`OpenCV`) to match them with slide images.
    *   Transcription segments are aligned with slides based on timing and matching results.
    *   All data (slides, segments, status) is stored in a MySQL database.
3.  **Interactive View:** The frontend displays the slides alongside the synchronized transcription segments.
4.  **Summarization (Optional):** Users can request an AI-generated summary (via OpenAI) for the text of the currently viewed slide.

---

## 🛠️ Tech Stack

### Backend (`notelecture-backend`)
*   **Framework:** FastAPI (Python)
*   **Database:** MySQL 
*   **Async:** `asyncio`, `httpx`, `aiofiles`
*   **Video/Audio:** `opencv-python`, `moviepy`, `yt-dlp`
*   **Document:** `PyMuPDF` (`fitz`)
*   **AI Services:** IVRIT.AI (Transcription), OpenAI (Summarization)
*   **Server:** Uvicorn

### Frontend (`notelecture-frontend`)
*   **Framework:** React.JS & TypeScript & Vite
*   **Styling:** Tailwind CSS
*   **Routing:** React Router DOM
*   **HTTP:** Axios
*   **UI:** Headless UI, Lucide React

---


*Created by Yarden Itzhaky* ([Portfolio](https://yardenitzhaky.github.io/Portfolio/) | [LinkedIn](https://www.linkedin.com/in/yardenitzhaky) | [GitHub](https://github.com/yardenitzhaky))
