function zabbixItemValue(value) {
  // Cloud 7.0 JS preprocessing treats numeric 0 and '' as empty → item
  // unsupported. lastAuthAge 0 (SE clock ahead) and capacity 0 hit this.
  if (value === undefined || value === null || value === '') {
    return '-';
  }
  return String(value);
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
