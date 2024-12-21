// src/pages/UploadPage.tsx
import { useState, ChangeEvent, FormEvent } from 'react';
import { Upload, FileType, Video } from 'lucide-react';

export const UploadPage: React.FC = () => {
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [presentationFile, setPresentationFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);

  const handleVideoFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.type.startsWith('video/')) {
      setVideoFile(file);
      setVideoUrl('');
    }
  };

  const handlePresentationFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && (file.type.includes('presentation') || file.type.includes('pdf'))) {
      setPresentationFile(file);
    }
  };

  const handleUrlChange = (event: ChangeEvent<HTMLInputElement>) => {
    setVideoUrl(event.target.value);
    setVideoFile(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsProcessing(true);
    
    try {
      // TODO: Implement file upload logic
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      <div className="bg-white shadow sm:rounded-lg p-6">
        <h2 className="text-2xl font-bold mb-6">Upload Your Lecture</h2>
        
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-4">
            <p className="text-sm text-gray-500">Choose video source:</p>
            
            {/* Video File Upload */}
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6">
              <div className="flex justify-center">
                <Video className="h-12 w-12 text-gray-400" />
              </div>
              <div className="mt-4 flex justify-center">
                <input
                  type="file"
                  accept="video/*"
                  onChange={handleVideoFileChange}
                  className="sr-only"
                  id="video-upload"
                />
                <label
                  htmlFor="video-upload"
                  className="cursor-pointer bg-blue-50 hover:bg-blue-100 text-blue-600 px-4 py-2 rounded-md"
                >
                  Select Video File
                </label>
              </div>
              {videoFile && (
                <p className="mt-2 text-sm text-gray-500 text-center">
                  Selected: {videoFile.name}
                </p>
              )}
            </div>

            {/* Video URL Input */}
            <div className="mt-4">
              <label htmlFor="video-url" className="block text-sm font-medium text-gray-700">
                Or paste video URL (YouTube/Zoom)
              </label>
              <input
                type="url"
                id="video-url"
                value={videoUrl}
                onChange={handleUrlChange}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                placeholder="https://"
              />
            </div>

            {/* Presentation Upload */}
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 mt-6">
              <div className="flex justify-center">
                <FileType className="h-12 w-12 text-gray-400" />
              </div>
              <div className="mt-4 flex justify-center">
                <input
                  type="file"
                  accept=".ppt,.pptx,.pdf"
                  onChange={handlePresentationFileChange}
                  className="sr-only"
                  id="presentation-upload"
                />
                <label
                  htmlFor="presentation-upload"
                  className="cursor-pointer bg-blue-50 hover:bg-blue-100 text-blue-600 px-4 py-2 rounded-md"
                >
                  Select Presentation File
                </label>
              </div>
              {presentationFile && (
                <p className="mt-2 text-sm text-gray-500 text-center">
                  Selected: {presentationFile.name}
                </p>
              )}
            </div>
          </div>

          <div className="flex justify-center">
            <button
              type="submit"
              disabled={isProcessing || (!videoFile && !videoUrl) || !presentationFile}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isProcessing ? (
                <span className="flex items-center">
                  <Upload className="animate-spin -ml-1 mr-3 h-5 w-5" />
                  Processing...
                </span>
              ) : (
                'Start Processing'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};