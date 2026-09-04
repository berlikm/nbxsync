function lastSundayDay(year, month) {
  var date = new Date(Date.UTC(year, month, 0));
  return date.getUTCDate() - date.getUTCDay();
}

function europeZurichOffsetMinutes(year, month, day, hour) {
  // EU DST as used by Europe/Zurich: last Sunday March 02:00 local CET → CEST,
  // last Sunday October 03:00 local CEST → CET. Ambiguous 02:00–02:59 in October
  // stays on CEST (hour < 3).
  var startDay = lastSundayDay(year, 3);
  var endDay = lastSundayDay(year, 10);
  var dst = false;
  if (month > 3 && month < 10) {
    dst = true;
  } else if (month === 3) {
    if (day > startDay || (day === startDay && hour >= 2)) {
      dst = true;
    }
  } else if (month === 10) {
    if (day < endDay || (day === endDay && hour < 3)) {
      dst = true;
    }
  }
  return dst ? 120 : 60;
}

function tzOffsetMinutes(tz, year, month, day, hour) {
  var zone = String(tz === undefined || tz === null ? 'Europe/Zurich' : tz);
  zone = zone.replace(/^\s+|\s+$/g, '');
  if (zone === 'UTC' || zone === 'GMT' || zone === 'Z') {
    return 0;
  }
  var fixed = zone.match(/^([+-])(\d{2}):?(\d{2})$/);
  if (fixed) {
    var sign = fixed[1] === '-' ? -1 : 1;
    return sign * (Number(fixed[2]) * 60 + Number(fixed[3]));
  }
  return europeZurichOffsetMinutes(year, month, day, hour);
}

function parseOffsetToken(token) {
  if (!token || token === 'Z' || token === 'z') {
    return 0;
  }
  var match = String(token).match(/^([+-])(\d{2}):?(\d{2})$/);
  if (!match) {
    return null;
  }
  var sign = match[1] === '-' ? -1 : 1;
  return sign * (Number(match[2]) * 60 + Number(match[3]));
}

function parseAuthTime(raw, tz) {
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
  var named = '';
  var namedMatch = text.match(/\s+(CEST|CET)$/i);
  if (namedMatch) {
    named = namedMatch[1].toUpperCase();
    text = text.slice(0, text.length - namedMatch[0].length);
  }
  var iso = text.match(
    /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:[.,](\d{1,3}))?(Z|[+-]\d{2}:?\d{2})?$/
  );
  if (iso) {
    var year = Number(iso[1]);
    var month = Number(iso[2]);
    var day = Number(iso[3]);
    var hour = Number(iso[4]);
    var minute = Number(iso[5]);
    var second = Number(iso[6]);
    var millis = iso[7] ? Number((iso[7] + '000').slice(0, 3)) : 0;
    var offsetMin;
    if (iso[8]) {
      offsetMin = parseOffsetToken(iso[8]);
      if (offsetMin === null) {
        return null;
      }
    } else if (named === 'CEST') {
      offsetMin = 120;
    } else if (named === 'CET') {
      offsetMin = 60;
    } else {
      // NBI 25.5.12.6 emits lastAuthEventTime without a zone, e.g.
      // 2026-09-04T08:39:05.366 while the clock is 06:39 UTC (CEST).
      // Date.parse() in Zabbix/Duktape treats that as UTC, then the 60s
      // future-skew drops current auths (~969 live on 2026-09-04).
      offsetMin = tzOffsetMinutes(tz, year, month, day, hour);
    }
    return Date.UTC(year, month - 1, day, hour, minute, second, millis) - offsetMin * 60000;
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

function countLicenseWindow(rows, nowMs, windowMs, tz) {
  var macs = {};
  var users = {};
  var byEngine = {};
  var i;
  if (!Array.isArray(rows)) {
    rows = [];
  }
  for (i = 0; i < rows.length; i++) {
    var row = rows[i] || {};
    var stamp = parseAuthTime(row.lastAuthEventTime, tz);
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
      // -1 = no event in the census. 0 = just now, or SE clock slightly ahead
      // of the proxy. A timezone-less NBI stamp is Site Engine local time,
      // not UTC — do not treat CEST "now" as two hours in the future.
      lastAuthAge: byEngine[engineIp].lastAuth
        ? Math.max(0, Math.floor((nowMs - byEngine[engineIp].lastAuth) / 1000))
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
