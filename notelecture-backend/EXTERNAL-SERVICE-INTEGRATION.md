# External Processing Service Integration Guide

## Overview
This document describes how to integrate an external processing service with your Vercel-deployed NoteLecture backend to handle heavy processing tasks that cannot run in Vercel's serverless environment.

## Affected Services
The following services in your backend now require external processing:

### 1. PresentationService (`app/services/presentation.py`)
- **Function**: `process_presentation()` - PDF processing
- **Missing Dependency**: PyMuPDF (fitz)
- **Error**: "PDF processing is not available - please use external service"

### 2. TranscriptionService (`app/services/transcription.py`)  
- **Function**: `extract_audio()` - Audio extraction from video files
- **Missing Dependency**: moviepy
- **Error**: "Audio extraction requires moviepy which is not available - please use external service"

- **Function**: `download_and_extract_audio()` - Video download and audio extraction
- **Missing Dependency**: yt_dlp
- **Error**: "Video download requires yt_dlp which is not available - please use external service"

### 3. SlideMatchingService (`app/services/slide_matching.py`)
- **Function**: `match_transcription_to_slides()` - Computer vision slide matching
- **Missing Dependencies**: opencv-python (cv2), numpy
- **Error**: "Slide matching requires OpenCV which is not available - please use external service"

## Integration Architecture

```
Frontend → Vercel Backend → External Processing Service
                ↓
          PostgreSQL Database
```

## Implementation Steps

### Step 1: Create External Processing Service
Create a new service (e.g., using Docker, AWS Lambda with larger limits, or a VPS) with:
- Python 3.11+
- Install dependencies from `external-service-requirements.txt`
- Implement API endpoints for each processing function

### Step 2: Recommended External Service Structure
```python
# external_service/main.py
from fastapi import FastAPI, UploadFile, File, Form
from services.presentation import ExternalPresentationService
from services.transcription import ExternalTranscriptionService  
from services.slide_matching import ExternalSlideMatchingService

app = FastAPI()

@app.post("/process-pdf/")
async def process_pdf(file: UploadFile = File(...)):
    service = ExternalPresentationService()
    content = await file.read()
    return await service.process_pdf(content)

@app.post("/extract-audio/")
async def extract_audio(video_file: UploadFile = File(...)):
    service = ExternalTranscriptionService()
    # Implementation here
    pass

@app.post("/download-extract-audio/")
async def download_extract_audio(video_url: str = Form(...)):
    service = ExternalTranscriptionService()
    # Implementation here
    pass

@app.post("/match-slides/")
async def match_slides(
    video_file: UploadFile = File(...),
    slides_data: str = Form(...),  # JSON string
    transcription_data: str = Form(...),  # JSON string
):
    service = ExternalSlideMatchingService()
    # Implementation here
    pass
```

### Step 3: Update Vercel Backend Configuration
Add environment variables to your Vercel deployment:

```bash
# In your Vercel environment variables
EXTERNAL_SERVICE_URL=https://your-external-service.com
EXTERNAL_SERVICE_API_KEY=your-api-key  # Optional for authentication
```

### Step 4: Update Backend Service Calls
Modify your services to call the external API instead of local processing:

#### Example for PresentationService:
```python
# In app/services/presentation.py
import httpx
from app.core.config import settings

async def process_presentation(self, file_content: bytes, file_extension: str) -> List[str]:
    if file_extension.lower() == 'pdf':
        if not FITZ_AVAILABLE:
            # Call external service
            async with httpx.AsyncClient() as client:
                files = {"file": ("presentation.pdf", file_content, "application/pdf")}
                response = await client.post(
                    f"{settings.EXTERNAL_SERVICE_URL}/process-pdf/",
                    files=files,
                    headers={"Authorization": f"Bearer {settings.EXTERNAL_SERVICE_API_KEY}"}
                )
                response.raise_for_status()
                return response.json()["slides"]
        return await self._process_pdf(file_content)
```

### Step 5: Update Configuration
Add to `app/core/config.py`:
```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # External service configuration
    EXTERNAL_SERVICE_URL: str = ""
    EXTERNAL_SERVICE_API_KEY: str = ""
```

### Step 6: Error Handling
Implement proper error handling and fallbacks:
- Timeout handling for external service calls
- Retry logic for transient failures
- Graceful degradation when external service is unavailable

### Step 7: Testing
1. Test each endpoint individually
2. Test the full flow: upload → process → display
3. Test error scenarios and timeouts

## Deployment Options for External Service

### Option 1: AWS Lambda (with container support)
- Use AWS Lambda with container images for larger memory/timeout limits
- Deploy using AWS SAM or CDK
- Benefits: Serverless, auto-scaling, pay-per-use

### Option 2: Google Cloud Run
- Container-based serverless platform
- Better for longer-running tasks than Vercel
- Benefits: Serverless, better resource limits

### Option 3: Railway/Render
- Simple deployment platforms
- Good for quick deployment
- Benefits: Easy setup, reasonable pricing

### Option 4: VPS/Dedicated Server
- Full control over environment
- Use Docker for containerization
- Benefits: Maximum flexibility, consistent performance

## Security Considerations
1. Use API keys for authentication between services
2. Validate all inputs on the external service
3. Use HTTPS for all communications
4. Consider VPN or private networking for sensitive data
5. Implement rate limiting on external service

## Monitoring and Logging
1. Add structured logging to both services
2. Monitor external service health and response times
3. Set up alerts for failures
4. Track usage and costs

## File Upload Considerations
- Implement file size limits
- Use streaming for large files
- Consider using cloud storage (S3, GCS) as intermediate storage
- Clean up temporary files after processing

## Cost Optimization
1. Use appropriate instance sizes for workload
2. Implement caching where possible
3. Consider batch processing for multiple files
4. Monitor usage patterns and scale accordingly