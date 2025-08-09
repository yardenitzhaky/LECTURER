// src/components/NotesSection.tsx
import React, { useState } from 'react';
import { Edit2, Save, X, StickyNote } from 'lucide-react';

interface NotesSectionProps {
    notes?: string;
    onSaveNotes: (notes: string) => Promise<void>;
    lectureId: number;
}

export const NotesSection: React.FC<NotesSectionProps> = ({
    notes,
    onSaveNotes,
}) => {
    const [isEditing, setIsEditing] = useState(false);
    const [editedNotes, setEditedNotes] = useState(notes || '');
    const [isSaving, setIsSaving] = useState(false);

    const handleEditClick = () => {
        setEditedNotes(notes || '');
        setIsEditing(true);
    };

    const handleSaveClick = async () => {
        setIsSaving(true);
        try {
            await onSaveNotes(editedNotes);
            setIsEditing(false);
        } catch (error) {
            console.error('Error saving notes:', error);
        } finally {
            setIsSaving(false);
        }
    };

    const handleCancelClick = () => {
        setEditedNotes(notes || '');
        setIsEditing(false);
    };

    return (
        <div className="bg-white rounded-lg shadow-sm p-4 mb-4">
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center">
                    <StickyNote className="h-5 w-5 text-blue-600 mr-2" />
                    <h3 className="text-lg font-semibold text-gray-900">My Notes</h3>
                </div>
                
                {!isEditing && (
                    <button
                        onClick={handleEditClick}
                        className="flex items-center px-3 py-1 text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-md transition-colors"
                    >
                        <Edit2 className="h-4 w-4 mr-1" />
                        {notes ? 'Edit' : 'Add Notes'}
                    </button>
                )}
            </div>

            {isEditing ? (
                <div className="space-y-3">
                    <textarea
                        value={editedNotes}
                        onChange={(e) => setEditedNotes(e.target.value)}
                        placeholder="Add your personal notes about this lecture..."
                        className="w-full h-32 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 resize-vertical"
                        autoFocus
                    />
                    <div className="flex items-center space-x-2">
                        <button
                            onClick={handleSaveClick}
                            disabled={isSaving}
                            className="flex items-center px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            <Save className="h-4 w-4 mr-1" />
                            {isSaving ? 'Saving...' : 'Save Notes'}
                        </button>
                        <button
                            onClick={handleCancelClick}
                            disabled={isSaving}
                            className="flex items-center px-3 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            <X className="h-4 w-4 mr-1" />
                            Cancel
                        </button>
                    </div>
                </div>
            ) : (
                <div className="text-gray-700">
                    {notes ? (
                        <div className="whitespace-pre-wrap bg-gray-50 p-3 rounded-md">
                            {notes}
                        </div>
                    ) : (
                        <p className="text-gray-500 italic">No notes added yet. Click "Add Notes" to start.</p>
                    )}
                </div>
            )}
        </div>
    );
};

export default NotesSection;