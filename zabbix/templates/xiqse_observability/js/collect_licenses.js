function endSystemQuery(maxResults, firstResult) {
  return '{ accessControl { endSystems(maxResults: ' + maxResults + ', firstResult: ' + firstResult + ') { count success errorMessage endSystems { macAddress lastAuthEventTime lastSeenTime username nacApplianceIP } } } }';
}

function pendingDeviceQuery() {
  return '{ network { devices { baseMac deviceData { xiqLicenseState } } } }';
}

function emptyLicenseSnapshot(error) {
  return {
    ok: 0,
    error: error,
    truncated: 0,
    fetched: 0,
    nacUsed: 0,
    nacAuthenticated24h: 0,
    nacPendingDevices: 0,
    sourceTimeOffsetMinutes: 0,
    users24h: 0,
    nacRemaining: 0,
    nacUsedPct: 0,
    engines: {}
  };
}

function collectLicenses(params) {
  var maxResults = Number(params.max_results) || 20000;
  var pageSize = Number(params.page_size) || 500;
  var nacTotal = params.nac_total;
  if (pageSize < 1) {
    pageSize = 500;
  }
  if (pageSize > maxResults) {
    pageSize = maxResults;
  }
  var auth = fetchToken(params);
  if (!auth.ok) {
    return emptyLicenseSnapshot(auth.error);
  }
  var rows = [];
  var first = 0;
  var truncated = 0;
  while (first < maxResults) {
    var take = pageSize;
    if (first + take > maxResults) {
      take = maxResults - first;
    }
    var page = graphql(params, auth.token, endSystemQuery(take, first));
    if (!page.ok) {
      var failed = emptyLicenseSnapshot(page.error);
      failed.truncated = truncated;
      failed.fetched = rows.length;
      return failed;
    }
    var wrap = (((page.data || {}).accessControl) || {}).endSystems || {};
    if (wrap.success === false) {
      var denied = emptyLicenseSnapshot(String(wrap.errorMessage || 'endSystems success=false'));
      denied.truncated = truncated;
      denied.fetched = rows.length;
      return denied;
    }
    var batch = Array.isArray(wrap.endSystems) ? wrap.endSystems : [];
    var i;
    for (i = 0; i < batch.length; i++) {
      rows.push(batch[i]);
    }
    if (rows.length >= maxResults) {
      truncated = 1;
      break;
    }
    if (batch.length < take) {
      break;
    }
    first += take;
  }
  var devicesResult = graphql(params, auth.token, pendingDeviceQuery());
  if (!devicesResult.ok) {
    var deviceFailed = emptyLicenseSnapshot(devicesResult.error);
    deviceFailed.truncated = truncated;
    deviceFailed.fetched = rows.length;
    return deviceFailed;
  }
  var devices = (((devicesResult.data || {}).network) || {}).devices;
  var counted = countNacLicenseUsage(rows, devices, Date.now(), 86400000);
  return {
    ok: 1,
    error: '',
    truncated: truncated,
    fetched: rows.length,
    nacUsed: counted.nacUsed,
    nacAuthenticated24h: counted.nacAuthenticated24h,
    nacPendingDevices: counted.nacPendingDevices,
    users24h: counted.users24h,
    sourceTimeOffsetMinutes: counted.sourceTimeOffsetMinutes,
    nacRemaining: remainingSeats(nacTotal, counted.nacUsed),
    nacUsedPct: usedSeatPercent(nacTotal, counted.nacUsed),
    engines: counted.engines
  };
}

var params = JSON.parse(value);
return JSON.stringify(collectLicenses(params));
