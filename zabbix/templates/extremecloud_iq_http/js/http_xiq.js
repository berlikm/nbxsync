function cloudBase(params) {
  var url = String((params && params.url) || 'https://api.extremecloudiq.com');
  if (url.charAt(url.length - 1) === '/') {
    url = url.substring(0, url.length - 1);
  }
  return url;
}

function cloudGet(params, path) {
  var request = new HttpRequest();
  request.addHeader('Accept: application/json');
  request.addHeader('Content-Type: application/json');
  request.addHeader('Authorization: Bearer ' + params.token);
  var response = request.get(cloudBase(params) + path);
  var code = request.getStatus();
  var body;
  try {
    body = JSON.parse(response);
  } catch (error) {
    return { ok: 0, error: 'HTTP ' + code + ' invalid JSON', status: code, data: null };
  }
  if (code !== 200) {
    return { ok: 0, error: 'HTTP ' + code, status: code, data: body };
  }
  return { ok: 1, error: '', status: code, data: body };
}

function parseExpireEpoch(raw) {
  if (raw === null || raw === undefined || raw === '') {
    return 0;
  }
  if (typeof raw === 'number' && isFinite(raw)) {
    if (raw > 1e12) {
      return Math.floor(raw / 1000);
    }
    if (raw > 1e9) {
      return Math.floor(raw);
    }
    return 0;
  }
  var text = String(raw);
  text = text.replace(/\+0000$/, 'Z');
  text = text.replace(/([+-])(\d{2})(\d{2})$/, '$1$2:$3');
  var ms = Date.parse(text);
  if (isNaN(ms)) {
    return 0;
  }
  return Math.floor(ms / 1000);
}

function classifyLicense(row) {
  var type = String((row && row.license_type) || '');
  var key = String((row && row.entitlement_key) || '');
  var hay = (type + ' ' + key).toUpperCase();
  if (!hay.replace(/\s/g, '')) {
    return 'other';
  }
  if (hay.indexOf('NAC') !== -1) {
    return 'nac';
  }
  if (hay.indexOf('COPILOT') !== -1 || hay.indexOf('CO-PILOT') !== -1 || hay.indexOf('XIQ-COP') !== -1) {
    return 'copilot';
  }
  if (hay.indexOf('NAV') !== -1) {
    return 'nav';
  }
  if (hay.indexOf('PIL') !== -1) {
    return 'pilot';
  }
  return 'other';
}

function emptyPool() {
  return {
    present: 0,
    have: 0,
    activated: 0,
    available: 0,
    expire: 0,
    status: '',
    types: []
  };
}

function addLicenseToPool(pool, row) {
  pool.present = 1;
  pool.have += Number(row.devices) || 0;
  pool.activated += Number(row.activated) || 0;
  pool.available += Number(row.available) || 0;
  var exp = parseExpireEpoch(row.expire_date);
  if (exp > 0 && (pool.expire === 0 || exp < pool.expire)) {
    pool.expire = exp;
  }
  var st = String(row.status || '');
  if (st) {
    pool.status = st;
  }
  var lt = String(row.license_type || '');
  if (lt && pool.types.indexOf(lt) === -1) {
    pool.types.push(lt);
  }
}

function aggregateLicenses(rows) {
  var pools = {
    pilot: emptyPool(),
    nav: emptyPool(),
    copilot: emptyPool(),
    nac: emptyPool(),
    other: emptyPool()
  };
  var types = [];
  var i;
  if (!Array.isArray(rows)) {
    rows = [];
  }
  for (i = 0; i < rows.length; i++) {
    var row = rows[i] || {};
    var kind = classifyLicense(row);
    addLicenseToPool(pools[kind], row);
    var lt = String(row.license_type || '');
    if (lt && types.indexOf(lt) === -1) {
      types.push(lt);
    }
  }
  return {
    licenseCount: rows.length,
    licenseTypes: types.join(','),
    pools: pools
  };
}

function vhmIsActive(status) {
  var text = String(status || '').toUpperCase();
  return text === 'ACTIVE_STATUS' || text === 'ACTIVE' ? 1 : 0;
}

function flattenPool(prefix, pool, out) {
  out[prefix + 'Present'] = pool.present;
  out[prefix + 'Have'] = pool.have;
  out[prefix + 'Activated'] = pool.activated;
  out[prefix + 'Available'] = pool.available;
  out[prefix + 'Expire'] = pool.expire;
  out[prefix + 'Status'] = pool.status;
}

function emptyAccountSnapshot(error) {
  var snap = {
    ok: 0,
    error: String(error || ''),
    customerId: '',
    expired: 0,
    vhmStatus: '',
    vhmActive: 2,
    tokenTtl: 0,
    tokenKnown: 0,
    licenseCount: 0,
    licenseTypes: '',
    pilotPresent: 0,
    pilotHave: 0,
    pilotActivated: 0,
    pilotAvailable: 0,
    pilotExpire: 0,
    pilotStatus: '',
    navPresent: 0,
    navHave: 0,
    navActivated: 0,
    navAvailable: 0,
    navExpire: 0,
    navStatus: '',
    copilotPresent: 0,
    copilotHave: 0,
    copilotActivated: 0,
    copilotAvailable: 0,
    copilotExpire: 0,
    nacPresent: 0,
    nacHave: 0,
    nacActivated: 0,
    nacAvailable: 0,
    nacExpire: 0,
    nacStatus: ''
  };
  return snap;
}

function emptyOpsSnapshot(error) {
  return {
    ok: 0,
    error: String(error || ''),
    lastConfigBackup: 0,
    lastConfigBackupAge: 0,
    lastConfigBackupName: '',
    backupCount: 0,
    deviceTotal: 0,
    deviceManaged: 0,
    deviceConnected: 0,
    deviceDisconnected: 0,
    deviceUnmanaged: 0
  };
}

function pickConfigBackup(grid, nowSec) {
  var rows = (grid && grid.data) || [];
  var newest = 0;
  var name = '';
  var i;
  if (!Array.isArray(rows)) {
    rows = [];
  }
  for (i = 0; i < rows.length; i++) {
    var row = rows[i] || {};
    var units = String(row.backup_units || '').toUpperCase();
    if (units !== 'CONFIG') {
      continue;
    }
    var ts = parseExpireEpoch(row.backup_date);
    if (ts > newest) {
      newest = ts;
      name = String(row.backup_file_name || '');
    }
  }
  var age = 0;
  if (newest > 0 && nowSec > newest) {
    age = nowSec - newest;
  }
  return {
    lastConfigBackup: newest,
    lastConfigBackupAge: age,
    lastConfigBackupName: name,
    backupCount: rows.length
  };
}

function collectAccount(params, getJson) {
  getJson = getJson || cloudGet;
  var snap = emptyAccountSnapshot('missing token');
  if (!params || !String(params.token || '')) {
    return snap;
  }
  var viq = getJson(params, '/account/viq');
  if (!viq.ok || !viq.data) {
    snap.error = viq.error || 'viq failed';
    return snap;
  }
  var body = viq.data;
  var counted = aggregateLicenses(body.licenses);
  snap.ok = 1;
  snap.error = '';
  snap.customerId = String(body.customer_id || '');
  snap.expired = body.expired === true || body.expired === 1 || body.expired === 'true' ? 1 : 0;
  snap.licenseCount = counted.licenseCount;
  snap.licenseTypes = counted.licenseTypes;
  flattenPool('pilot', counted.pools.pilot, snap);
  flattenPool('nav', counted.pools.nav, snap);
  flattenPool('copilot', counted.pools.copilot, snap);
  flattenPool('nac', counted.pools.nac, snap);

  var vhm = getJson(params, '/account/vhm/status');
  if (vhm.ok && vhm.data) {
    snap.vhmStatus = String(vhm.data.current_status || '');
    snap.vhmActive = vhmIsActive(snap.vhmStatus);
  } else {
    snap.vhmActive = 2;
    snap.vhmStatus = '';
    snap.error = vhm.error || 'vhm failed';
  }

  var token = getJson(params, '/auth/apitoken/info');
  if (token.ok && token.data) {
    var ttl = Number(token.data.expires_in);
    if (!isFinite(ttl) || ttl < 0) {
      var exp = parseExpireEpoch(token.data.expiration_time);
      ttl = exp > 0 ? exp - Math.floor(Date.now() / 1000) : 0;
      if (ttl < 0) {
        ttl = 0;
      }
    }
    snap.tokenTtl = ttl;
    snap.tokenKnown = 1;
  } else {
    snap.tokenKnown = 0;
    snap.tokenTtl = 0;
    if (!snap.error) {
      snap.error = token.error || 'token info failed';
    }
  }
  return snap;
}

function collectOps(params, getJson, nowSec) {
  getJson = getJson || cloudGet;
  nowSec = nowSec || Math.floor(Date.now() / 1000);
  var snap = emptyOpsSnapshot('missing token');
  if (!params || !String(params.token || '')) {
    return snap;
  }
  var errors = [];
  var backup = getJson(params, '/backup/history/grid?page=1&limit=10');
  if (backup.ok && backup.data) {
    var picked = pickConfigBackup(backup.data, nowSec);
    snap.lastConfigBackup = picked.lastConfigBackup;
    snap.lastConfigBackupAge = picked.lastConfigBackupAge;
    snap.lastConfigBackupName = picked.lastConfigBackupName;
    snap.backupCount = picked.backupCount;
  } else {
    errors.push(backup.error || 'backup grid failed');
  }
  var stats = getJson(params, '/devices/stats');
  if (stats.ok && stats.data) {
    snap.deviceTotal = Number(stats.data.total_device_count) || 0;
    snap.deviceManaged = Number(stats.data.managed_device_count) || 0;
    snap.deviceConnected = Number(stats.data.connected_device_count) || 0;
    var basis = snap.deviceManaged > 0 ? snap.deviceManaged : snap.deviceTotal;
    snap.deviceDisconnected = basis > snap.deviceConnected ? basis - snap.deviceConnected : 0;
    snap.deviceUnmanaged = snap.deviceTotal > snap.deviceManaged ? snap.deviceTotal - snap.deviceManaged : 0;
  } else {
    errors.push(stats.error || 'device stats failed');
  }
  snap.ok = errors.length ? 0 : 1;
  snap.error = errors.join('; ');
  return snap;
}
