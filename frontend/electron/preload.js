const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    // Add IPC communication bridge functions here if native desktop OS APIs are required
});