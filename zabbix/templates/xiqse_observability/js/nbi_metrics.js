function isNaiveIsoTime(text) {
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?$/.test(text);
}

function parseAuthTime(raw, naiveOffsetMs) {
  if (raw === null || raw === undefined || raw === '') {
    return null;
  }
  if (typeof raw === 'number' && isFinite(raw)) {
    return raw > 0 && raw < 1e11 ? raw * 1000 : raw;
  }
  var text = String(raw).replace(/^\s+|\s+$/g, '');
  if (/^\d+$/.test(text)) {
    var numeric = Number(text);
    return numeric > 0 && numeric < 1e11 ? numeric * 1000 : numeric;
  }
  var parsed = Date.parse(isNaiveIsoTime(text) ? text + 'Z' : text);
  if (isNaN(parsed)) {
    return null;
  }
  return parsed - (isNaiveIsoTime(text) ? Number(naiveOffsetMs || 0) : 0);
}

function inferNaiveTimeOffset(rows, nowMs) {
  var newestWallTime = 0;
  var i;
  if (!Array.isArray(rows)) {
    return 0;
  }
  for (i = 0; i < rows.length; i++) {
    var row = rows[i] || {};
    var text = String(row.lastSeenTime || row.lastAuthEventTime || '');
    if (!isNaiveIsoTime(text)) {
      continue;
    }
    var wallTime = Date.parse(text + 'Z');
    if (!isNaN(wallTime) && wallTime > newestWallTime) {
      newestWallTime = wallTime;
    }
  }
  if (!newestWallTime) {
    return 0;
  }
  // Site Engine emits local wall-clock timestamps without a zone. The newest
  // lastSeenTime is normally seconds old, so round its skew to a real 15m zone.
  var offset = Math.round((newestWallTime - nowMs) / 900000) * 900000;
  return Math.abs(offset) <= 50400000 ? offset : 0;
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

function remainingSeats(total, used) {
  // Purchased totals are macros. 0 / blank / NaN means unknown entitlement,
  // not "sold out" — do not return used as a negative remaining.
  var purchased = Number(total);
  var observed = Number(used);
  if (!isFinite(purchased) || purchased <= 0) {
    return 0;
  }
  if (!isFinite(observed) || observed < 0) {
    observed = 0;
  }
  return purchased - observed;
}

function usedSeatPercent(total, used) {
  var purchased = Number(total);
  var observed = Number(used);
  if (!isFinite(purchased) || purchased <= 0) {
    return 0;
  }
  if (!isFinite(observed) || observed < 0) {
    observed = 0;
  }
  return observed / purchased * 100;
}

function normalizeMac(raw) {
  var mac = String(raw || '').toLowerCase().replace(/[^0-9a-f]/g, '');
  return /^[0-9a-f]{12}$/.test(mac) ? mac : '';
}

function countAuthenticatedWindow(rows, nowMs, windowMs) {
  var macs = {};
  var users = {};
  var byEngine = {};
  var i;
  if (!Array.isArray(rows)) {
    rows = [];
  }
  var sourceOffsetMs = inferNaiveTimeOffset(rows, nowMs);
  for (i = 0; i < rows.length; i++) {
    var row = rows[i] || {};
    var stamp = parseAuthTime(row.lastAuthEventTime, sourceOffsetMs);
    if (stamp === null || nowMs - stamp > windowMs || stamp > nowMs + 60000) {
      continue;
    }
    var mac = normalizeMac(row.macAddress);
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
      // -1 = no event in the census. 0 = just now, or SE clock slightly ahead
      // of the proxy. A timezone-less NBI stamp is Site Engine local time,
      // not UTC — do not treat CEST "now" as two hours in the future.
      lastAuthAge: byEngine[engineIp].lastAuth
        ? Math.max(0, Math.floor((nowMs - byEngine[engineIp].lastAuth) / 1000))
        : -1
    };
  }
  return {
    macs: macs,
    authenticated24h: objectSize(macs),
    users24h: objectSize(users),
    sourceTimeOffsetMinutes: sourceOffsetMs / 60000,
    engines: engines
  };
}

function countNacLicenseUsage(rows, devices, nowMs, windowMs) {
  var authenticated = countAuthenticatedWindow(rows, nowMs, windowMs);
  var macs = authenticated.macs;
  var pending = {};
  var i;
  if (!Array.isArray(devices)) {
    devices = [];
  }
  for (i = 0; i < devices.length; i++) {
    var device = devices[i] || {};
    var state = String(((device.deviceData || {}).xiqLicenseState) || '');
    if (state !== 'XIQ_PENDING') {
      continue;
    }
    var mac = normalizeMac(device.baseMac);
    if (!mac) {
      continue;
    }
    pending[mac] = 1;
    macs[mac] = 1;
  }
  return {
    nacUsed: objectSize(macs),
    nacAuthenticated24h: authenticated.authenticated24h,
    nacPendingDevices: objectSize(pending),
    users24h: authenticated.users24h,
    sourceTimeOffsetMinutes: authenticated.sourceTimeOffsetMinutes,
    engines: authenticated.engines
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

function emptyDeviceLicenses() {
  return {
    pilotUsed: 0,
    navigatorUsed: 0,
    pending: 0,
    unmanaged: 0,
    platformOne: 0,
    other: 0
  };
}

function countDeviceLicenses(devices) {
  var out = emptyDeviceLicenses();
  var i;
  var rows = Array.isArray(devices) ? devices : [];
  for (i = 0; i < rows.length; i++) {
    var data = rows[i] && rows[i].deviceData;
    var state = data ? String(data.xiqLicenseState || '') : '';
    if (!state) {
      continue;
    }
    if (state === 'XIQ_PILOT') {
      out.pilotUsed++;
    } else if (state === 'XIQ_NAVIGATOR') {
      out.navigatorUsed++;
    } else if (state === 'XIQ_PENDING') {
      out.pending++;
    } else if (state === 'XIQ_UNMANAGED') {
      out.unmanaged++;
    } else if (state.indexOf('XIQ_ADVANCED') === 0 || state.indexOf('XIQ_STANDARD') === 0) {
      out.platformOne++;
    } else {
      out.other++;
    }
  }
  return out;
}

function countPilot(devices) {
  return countDeviceLicenses(devices).pilotUsed;
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
