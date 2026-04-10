const { app, BrowserWindow, globalShortcut, ipcMain } = require('electron')
const path = require('path')

let mainWindow = null
let overlayWindow = null

const isDev = process.env.NODE_ENV !== 'production'

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 650,
    minWidth: 800,
    minHeight: 600,
    title: 'Caption Generator',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  })

  // In development, wait for Vite to start on localhost:5173
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    // In production, load the built index.html
    mainWindow.loadFile(path.join(__dirname, 'renderer/dist/index.html'))
  }
}

function createOverlay() {
  overlayWindow = new BrowserWindow({
    width: 800,
    height: 100,
    x: 100,
    y: 50,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  })

  overlayWindow.setIgnoreMouseEvents(true, { forward: true })
  overlayWindow.loadFile(path.join(__dirname, 'overlay.html'))
  overlayWindow.hide() // Hidden by default — toggled via hotkey
}

function toggleOverlay() {
  if (!overlayWindow) return
  if (overlayWindow.isVisible()) {
    overlayWindow.hide()
  } else {
    overlayWindow.show()
  }
}

app.whenReady().then(() => {
  createWindow()    // existing main window function
  createOverlay()   // new overlay window

  // Global hotkey — works even when app is not focused
  globalShortcut.register('CommandOrControl+Shift+C', toggleOverlay)
})

app.on('will-quit', () => {
  globalShortcut.unregisterAll()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

ipcMain.on('overlay-drag-start', () => {
  if (overlayWindow) { overlayWindow.setIgnoreMouseEvents(false) }
})

ipcMain.on('overlay-drag-end', () => {
  if (overlayWindow) { overlayWindow.setIgnoreMouseEvents(true, { forward: true }) }
})

ipcMain.on('move-overlay', (event, { dx, dy }) => {
  if (!overlayWindow) return
  const [x, y] = overlayWindow.getPosition()
  overlayWindow.setPosition(x + dx, y + dy)
})

ipcMain.on('caption-to-overlay', (event, data) => {
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    overlayWindow.webContents.send('caption-from-main', data)
  }
})

ipcMain.on('overlay-settings', (event, settings) => {
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    overlayWindow.webContents.send('apply-settings', settings)
  }
})
