// src/hooks/useLectureData.tsx
import { useState, useEffect, useCallback } from 'react';
import { APIService } from '../api';
import { Lecture } from '../index';

const POLLING_INTERVAL_MS = 15000;

export const useLectureData = (id: string | undefined) => {
    const [lecture, setLecture] = useState<Lecture | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [error, setError] = useState<string>('');
    const [pollingIntervalId, setPollingIntervalId] = useState<number | null>(null);

    const stopPolling = useCallback(() => {
        if (pollingIntervalId) {
            console.log(`Polling stopped for lecture ${id}.`);
            clearInterval(pollingIntervalId);
            setPollingIntervalId(null);
        }
    }, [pollingIntervalId, id]);

    const fetchLecture = useCallback(async (showLoadingSpinner = true) => {
        if (!id) {
            setError('Lecture ID is missing.');
            setIsLoading(false);
            setLecture(null);
            return;
        }

        if (showLoadingSpinner) {
            setIsLoading(true);
            setLecture(null);
        } else {
            setIsRefreshing(true);
        }
        setError('');

        try {
            const lectureData = await APIService.getLecture(id);
            setLecture(lectureData);

            const isProcessing = lectureData.status !== 'completed' && lectureData.status !== 'failed';

            if (!isProcessing) {
                stopPolling();
            } else if (!pollingIntervalId && showLoadingSpinner) {
                console.log(`Polling started for lecture ${id}. Status: ${lectureData.status}`);
                const intervalId = window.setInterval(() => {
                    console.log(`Polling lecture ${id}...`);
                    fetchLecture(false);
                }, POLLING_INTERVAL_MS);
                setPollingIntervalId(intervalId);
            }

        } catch (err) {
            let errorMessage = 'Failed to load lecture data.';
            if (err instanceof Error) errorMessage = err.message;
            else if (typeof err === 'object' && err !== null && 'detail' in err) {
                errorMessage = (err as { detail: string }).detail || errorMessage;
            }
            setError(errorMessage);
            setLecture(null);
            stopPolling();
            console.error("Error fetching lecture:", err);
        } finally {
            if (showLoadingSpinner) setIsLoading(false);
            setIsRefreshing(false);
        }
    }, [id, pollingIntervalId, stopPolling]);

    useEffect(() => {
        fetchLecture(true);
        return () => {
            stopPolling();
        };
    }, [id, fetchLecture, stopPolling]);

    const refetch = useCallback(() => fetchLecture(false), [fetchLecture]);

    return { lecture, isLoading, isRefreshing, error, refetch };
};