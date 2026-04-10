# Week 3 Frontend Test Checklist

## Setup
- [ ] Flask backend running on localhost:5000
- [ ] `npm run dev` started successfully
- [ ] Electron window opened

## Status Bar
- [ ] Status bar shows "Backend Connected" with green indicator
- [ ] GPU name displayed (e.g. NVIDIA GeForce GTX 1650)
- [ ] If backend is stopped, indicator turns red

## File Upload (EN → TA)
- [ ] Set direction to EN → TA
- [ ] Upload a .mp3 file
- [ ] Loading state shown while processing
- [ ] Transcript appears in left panel (English)
- [ ] Tamil translation appears in right panel
- [ ] Tamil characters render correctly (not boxes)

## File Upload (TA → EN)
- [ ] Set direction to TA → EN
- [ ] Upload a Tamil audio file (or reuse test_audio.mp3 — result will just be EN→EN)
- [ ] Both panels populate

## Direction Toggle
- [ ] Toggle switches between EN→TA and TA→EN
- [ ] Toggle is disabled while processing

## Mic Button
- [ ] Button visible and styled
- [ ] Clicking shows "Coming Soon" message
- [ ] Does not crash the app

## Error Handling
- [ ] Stop Flask backend, try uploading a file
- [ ] Error message appears in UI (not a blank screen or console-only error)
