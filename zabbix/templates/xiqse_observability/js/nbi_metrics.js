function parseAuthTime(raw) {
  if (raw === null || raw === undefined || raw === '') {
    return null;
  }
  if (typeof raw === 'number' && isFinite(raw)) {
    return raw > 0 && raw < 1e11 ? raw * 1000 : raw;
  }
  var text = String(raw);
  if (/^\d+$/.test(text)) {
    var numeric = Number(text);
    return numeric > 0 && numeric < 1e11 ? numeric * 1000 : numeric;
  }
  var parsed = Date.parse(text);
  return isNaN(parsed) ? null : parsed;
}

function objectSize(obj) {
  var count = 0;
  var key;
  for (key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      count++;
    }
  }
  return count;
}

function countLicenseWindow(rows, nowMs, windowMs) {
  var macs = {};
  var users = {};
  var byEngine = {};
  var i;
  if (!Array.isArray(rows)) {
    rows = [];
  }
  for (i = 0; i < rows.length; i++) {
    var row = rows[i] || {};
    var stamp = parseAuthTime(row.lastAuthEventTime);
    if (stamp === null || nowMs - stamp > windowMs || stamp > nowMs + 60000) {
      continue;
    }
    var mac = String(row.macAddress || '').toLowerCase();
    if (!mac) {
      continue;
    }
    macs[mac] = 1;
    var user = String(row.username || '').replace(/^\s+|\s+$/g, '');
    if (user) {
      users[user] = 1;
    }
    var ip = String(row.nacApplianceIP || row.nacApplianceIp || '');
    if (!ip) {
      continue;
    }
    if (!byEngine[ip]) {
      byEngine[ip] = { macs: {}, lastAuth: 0 };
    }
    byEngine[ip].macs[mac] = 1;
    if (stamp > byEngine[ip].lastAuth) {
      byEngine[ip].lastAuth = stamp;
    }
  }
  var engines = {};
  var engineIp;
  for (engineIp in byEngine) {
    if (!Object.prototype.hasOwnProperty.call(byEngine, engineIp)) {
      continue;
    }
    engines[engineIp] = {
      used24h: objectSize(byEngine[engineIp].macs),
      lastAuthAge: byEngine[engineIp].lastAuth
        ? Math.floor((nowMs - byEngine[engineIp].lastAuth) / 1000)
        : -1
    };
  }
  return {
    nacUsed24h: objectSize(macs),
    users24h: objectSize(users),
    engines: engines
  };
}

function bool01(value) {
  if (value === true || value === 1 || value === '1' || value === 'true') {
    return 1;
  }
  if (value === false || value === 0 || value === '0' || value === 'false') {
    return 0;
  }
  return 2;
}

function uptimeSeconds(raw) {
  var numeric = Number(raw);
  if (!isFinite(numeric) || numeric < 0) {
    return 0;
  }
  if (numeric > 1e10) {
    return Math.floor(numeric / 1000);
  }
  return Math.floor(numeric);
}

function normalizeEngine(raw) {
  var row = raw || {};
  var ip = String(row.ipAddress || row.ip || '');
  var connected = 2;
  if (row.connected !== undefined) {
    connected = bool01(row.connected);
  } else if (row.isConnected !== undefined) {
    connected = bool01(row.isConnected);
  }
  return {
    ip: ip,
    name: String(row.displayName || row.name || ip),
    version: String(row.version || ''),
    licensed: bool01(row.licensed),
    capacity: Number(row.capacity) || 0,
    freeRadiusEnabled: bool01(row.freeRadiusEnabled),
    needsEnforce: bool01(row.needsEnforce),
    connected: connected,
    virtual: bool01(row.virtual)
  };
}

function normalizeEngines(raw) {
  var rows = Array.isArray(raw) ? raw : [];
  var out = [];
  var i;
  for (i = 0; i < rows.length; i++) {
    var engine = normalizeEngine(rows[i]);
    if (engine.ip) {
      out.push(engine);
    }
  }
  return out;
}

function enginesToLld(engines) {
  var out = [];
  var i;
  var rows = Array.isArray(engines) ? engines : [];
  for (i = 0; i < rows.length; i++) {
    var engine = rows[i] || {};
    if (!engine.ip) {
      continue;
    }
    out.push({
      '{#ENGINE.IP}': String(engine.ip),
      '{#ENGINE.NAME}': String(engine.name || engine.ip),
      '{#ENGINE.CAPACITY}': String(engine.capacity || 0)
    });
  }
  return out;
}

function countPilot(devices) {
  var used = 0;
  var i;
  var rows = Array.isArray(devices) ? devices : [];
  for (i = 0; i < rows.length; i++) {
    var data = rows[i] && rows[i].deviceData;
    if (data && String(data.xiqLicenseState) === 'XIQ_PILOT') {
      used++;
    }
  }
  return used;
}

function pickEngineField(payload, ip, field, missing) {
  var engines = payload && Array.isArray(payload.engines) ? payload.engines : [];
  var i;
  for (i = 0; i < engines.length; i++) {
    if (String(engines[i].ip) === String(ip)) {
      if (engines[i][field] === undefined || engines[i][field] === null) {
        return missing;
      }
      return engines[i][field];
    }
  }
  return missing;
}

function pickLicenseEngineField(payload, ip, field, missing) {
  var row = payload && payload.engines ? payload.engines[String(ip)] : null;
  if (!row || row[field] === undefined || row[field] === null) {
    return missing;
  }
  return row[field];
}
