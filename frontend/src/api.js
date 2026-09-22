const API_BASE = 'http://127.0.0.1:8000/api';

/**
 * Every route here returns JSON even on failure (FastAPI's HTTPException
 * produces {"detail": "..."}), so error handling reads that instead of
 * just throwing the raw response text.
 */
async function handleResponse(response) {
    if (!response.ok) {
        let detail;
        try {
            detail = (await response.json()).detail;
        } catch {
            detail = await response.text();
        }
        throw new Error(detail || `Request failed with status ${response.status}`);
    }
    return response.json();
}

export async function loadDatabase(folderPath, format = 'csv') {
    const response = await fetch(
        `${API_BASE}/load?folder_path=${encodeURIComponent(folderPath)}&format=${encodeURIComponent(format)}`,
        { method: 'POST' }
    );
    return handleResponse(response);
}

export async function saveDatabase(format) {
    const query = format ? `?format=${encodeURIComponent(format)}` : '';
    const response = await fetch(`${API_BASE}/save${query}`, { method: 'POST' });
    return handleResponse(response);
}

/**
 * Read-only snapshot of everything currently in memory (doesn't touch
 * disk, unlike loadDatabase). Use this to refresh the UI's view of state
 * after a create/update/delete elsewhere, or when a second view/tab needs
 * the current data.
 */
export async function getDatabase() {
    const response = await fetch(`${API_BASE}/database`);
    return handleResponse(response);
}

/**
 * Generic create - one function for every entity type instead of one
 * function per class.
 *
 * @param {string} entityType - the Python class name, e.g. "Node",
 *   "StatBoost", "NodeTree", "Reward".
 * @param {object} fields - that entity's constructor kwargs. Any field
 *   that references another entity is given as that entity's ID string
 *   (or an array of ID strings, for Reward's abilities/stat_boosts) -
 *   never a nested object.
 *
 * Examples:
 *   createInstance('NodeTree', { name: 'Warrior Class' })
 *   createInstance('StatBoost', { stat_type: 'STAT-1', upg_tag: 'UPGTAG-1', value: 5 })
 *   createInstance('Node', { requirement: '10', startingNode: false, nodeTree: 'TREE-1', reward: 'RWD-1' })
 *   createInstance('Reward', { abilities: ['ABILITY-1'], stat_boosts: ['STATBOOST-1'] })
 *   createInstance('NodeRelation', { parentNode: 'NODE-1', childNode: 'NODE-2' })
 */
export async function createInstance(entityType, fields) {
    const response = await fetch(`${API_BASE}/instance/${entityType}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(fields),
    });
    return handleResponse(response);
}

/**
 * Generic update, same ID-string convention as createInstance. Only the
 * fields included in `fields` are changed - omit anything you don't want
 * touched.
 *
 * Note: NodeRelation's parentNode/childNode can't be changed this way
 * (the backend rejects it with a 400 explaining why) - delete the
 * relation and create a new one instead.
 */
export async function updateInstance(entityType, instanceId, fields) {
    const response = await fetch(`${API_BASE}/instance/${entityType}/${instanceId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(fields),
    });
    return handleResponse(response);
}

export async function deleteInstance(entityType, instanceId, inCascade = false) {
    const response = await fetch(
        `${API_BASE}/instance/${entityType}/${instanceId}?in_cascade=${inCascade}`,
        { method: 'DELETE' }
    );
    return handleResponse(response);
}