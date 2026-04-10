const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  version: process.versions.electron,

  // Overlay drag handle
  startDrag: () => ipcRenderer.send('overlay-drag-start'),
  endDrag: () => ipcRenderer.send('overlay-drag-end'),

  // Send captions to overlay from main window
  sendCaption: (data) => ipcRenderer.send('caption-to-overlay', data),

  // Receive captions in overlay window
  onCaption: (callback) => ipcRenderer.on('caption-from-main', (_, data) => callback(data)),

  // Manual Drag Coordination
  moveOverlay: (dx, dy) => ipcRenderer.send('move-overlay', { dx, dy }),

  // Custom Settings Application 
  sendOverlaySettings: (settings) => ipcRenderer.send('overlay-settings', settings),
  onSettings: (callback) => ipcRenderer.on('apply-settings', (_, s) => callback(s))
})
