const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

let mainWindow;
let pythonProcess = null;
const PYTHON_PORT = 8000;

function startPythonBackend() {
    const isDev = !app.isPackaged;
    const rootDir = path.join(__dirname, '../../');

    // 1. Resolve Python executable (prefers .venv in development)
    let pythonExec = process.platform === 'win32' ? 'python' : 'python3';
    if (isDev) {
        const venvPython = process.platform === 'win32'
            ? path.join(rootDir, '.venv', 'Scripts', 'python.exe')
            : path.join(rootDir, '.venv', 'bin', 'python');

        if (fs.existsSync(venvPython)) {
            pythonExec = venvPython;
        }
    }

    // 2. Run Python as a module (-m core.server) from the root working directory
    pythonProcess = spawn(pythonExec, ['-m', 'core.server', PYTHON_PORT.toString()], {
        cwd: rootDir
    });

    pythonProcess.stdout.on('data', (data) => console.log(`[Python]: ${data}`));
    pythonProcess.stderr.on('data', (data) => console.error(`[Python Err]: ${data}`));
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1280,
        height: 800,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
    });

    const isDev = !app.isPackaged;
    if (isDev) {
        mainWindow.loadURL('http://localhost:5173');
    } else {
        // Correct path to frontend build: frontend/dist/index.html
        mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
    }
}

app.whenReady().then(() => {
    // Only spawn Python from Electron if packaged for production
    if (app.isPackaged) {
        startPythonBackend();
    }
    createWindow();
});

// Ensure backend process is killed on exit
app.on('will-quit', () => {
    if (pythonProcess) {
        pythonProcess.kill();
    }
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});