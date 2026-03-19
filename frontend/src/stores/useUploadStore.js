import { create } from 'zustand';
import {
  uploadFile,
  previewImport,
  confirmImport,
} from '../api/upload';

const useUploadStore = create((set, get) => ({
  // Step: idle → uploaded → mapped → previewing → importing → done
  step: 'idle',

  // Upload result
  uploadId: null,
  filename: null,
  headers: [],
  sampleRows: [],
  suggestedMapping: {},
  targetFields: {},

  // User mapping
  mapping: {},
  dataType: 'trading',

  // Preview result
  preview: null,

  // Import result
  result: null,

  // UI state
  loading: false,
  error: null,

  // Step 1: Upload file
  doUpload: async (file, dataType) => {
    set({ loading: true, error: null, dataType });
    try {
      const res = await uploadFile(file, dataType);
      set({
        step: 'uploaded',
        uploadId: res.upload_id,
        filename: res.filename,
        headers: res.headers,
        sampleRows: res.sample_rows,
        suggestedMapping: res.suggested_mapping,
        targetFields: res.target_fields,
        mapping: res.suggested_mapping,
        loading: false,
      });
    } catch (err) {
      set({ error: err.message, loading: false });
    }
  },

  // Update column mapping
  setMapping: (mapping) => set({ mapping }),

  // Step 2: Preview import
  doPreview: async () => {
    const { uploadId, dataType, mapping } = get();
    set({ loading: true, error: null, step: 'previewing' });
    try {
      const res = await previewImport({ uploadId, dataType, mapping });
      set({ preview: res, step: 'mapped', loading: false });
    } catch (err) {
      set({ error: err.message, step: 'uploaded', loading: false });
    }
  },

  // Step 3: Confirm import
  doConfirm: async (skipErrors = true) => {
    const { uploadId, dataType } = get();
    set({ loading: true, error: null, step: 'importing' });
    try {
      const res = await confirmImport({ uploadId, dataType, skipErrors });
      set({ result: res, step: 'done', loading: false });
    } catch (err) {
      set({ error: err.message, step: 'mapped', loading: false });
    }
  },

  // Reset wizard to initial state
  reset: () =>
    set({
      step: 'idle',
      uploadId: null,
      filename: null,
      headers: [],
      sampleRows: [],
      suggestedMapping: {},
      targetFields: {},
      mapping: {},
      dataType: 'trading',
      preview: null,
      result: null,
      loading: false,
      error: null,
    }),
}));

export default useUploadStore;
