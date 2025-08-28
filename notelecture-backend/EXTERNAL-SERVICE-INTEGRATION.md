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
Create a Google Cloud Run service with:
- Python 3.11+
- Docker container with dependencies from `external-service-requirements.txt`
- FastAPI endpoints for each processing function
- Container registry for deployment

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
EXTERNAL_SERVICE_URL=https://your-service-name-12345-uc.a.run.app
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

## Google Cloud Run Deployment Guide

### Prerequisites
1. Google Cloud account with billing enabled
2. Google Cloud CLI (`gcloud`) installed
3. Docker installed locally
4. Enable Container Registry and Cloud Run APIs

### Deployment Steps

#### 1. Create Dockerfile
Create `external_service/Dockerfile`:
```dockerfile
FROM python:3.11-slim

# Install system dependencies for OpenCV and other packages
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgthread-2.0-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libgtk2.0-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY external-service-requirements.txt .
RUN pip install --no-cache-dir -r external-service-requirements.txt

COPY . .
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

#### 2. Update requirements.txt
Add to `external_service/external-service-requirements.txt`:
```txt
fastapi==0.109.0
uvicorn==0.27.0
# ... existing dependencies from your requirements file
```

#### 3. Build and Deploy
```bash
# Set your Google Cloud project
gcloud config set project YOUR_PROJECT_ID

# Build container image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/external-service

# Deploy to Cloud Run
gcloud run deploy external-service \
    --image gcr.io/YOUR_PROJECT_ID/external-service \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 900 \
    --max-instances 10
```

#### 4. Configure Environment Variables
```bash
gcloud run services update external-service \
    --set-env-vars "ENVIRONMENT=production" \
    --region us-central1
```

### Benefits of Google Cloud Run
- **Pay-per-use**: Only pay when processing requests
- **Auto-scaling**: Scales to zero when idle, up to 1000 concurrent requests
- **Container support**: Full Python dependency support
- **Managed**: No server management required
- **Global**: Deploy in multiple regions
- **Cost-effective**: ~$2-10/month for typical usage

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

## Cost Optimization for Google Cloud Run
1. **Right-size resources**: Start with 1 CPU/1GB RAM, increase if needed
2. **Set max instances**: Limit concurrent instances to control costs
3. **Use request timeout**: Set appropriate timeout (900s max)
4. **Monitor usage**: Use Cloud Monitoring to track requests and costs
5. **Implement caching**: Cache processed results to reduce duplicate processing
6. **Batch processing**: Process multiple files in single request when possible

## Troubleshooting
- **Container build fails**: Check system dependencies in Dockerfile
- **Timeout errors**: Increase timeout or optimize processing
- **Memory errors**: Increase memory allocation (up to 8GB available)
- **Cold starts**: Consider keeping 1 instance warm with min-instances=1