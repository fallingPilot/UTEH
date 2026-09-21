const API_BASE = 'http://127.0.0.1:8000/api';

export async function loadDatabase(folderPath) {
    const response = await fetch(`${API_BASE}/load?folder_path=${encodeURIComponent(folderPath)}`, {
        method: 'POST',
    });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
}

export async function saveDatabase() {
    const response = await fetch(`${API_BASE}/save`, { method: 'POST' });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
}

export async function deleteInstance(entityType, instanceId, inCascade = false) {
    const response = await fetch(
        `${API_BASE}/instance/${entityType}/${instanceId}?in_cascade=${inCascade}`,
        { method: 'DELETE' }
    );
    if (!response.ok) throw new Error(await response.text());
    return response.json();
}