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
