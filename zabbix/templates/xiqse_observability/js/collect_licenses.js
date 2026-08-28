function endSystemQuery(maxResults, firstResult) {
  return '{ accessControl { endSystems(maxResults: ' + maxResults + ', firstResult: ' + firstResult + ') { count success errorMessage endSystems { macAddress lastAuthEventTime username nacApplianceIP } } } }';
}

function collectLicenses(params) {
  var maxResults = Number(params.max_results) || 20000;
  var pageSize = Number(params.page_size) || 500;
  if (pageSize < 1) {
    pageSize = 500;
  }
  if (pageSize > maxResults) {
    pageSize = maxResults;
  }
  var auth = fetchToken(params);
  if (!auth.ok) {
    return { ok: 0, error: auth.error, truncated: 0, fetched: 0, nacUsed24h: 0, users24h: 0, engines: {} };
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
      return { ok: 0, error: page.error, truncated: truncated, fetched: rows.length, nacUsed24h: 0, users24h: 0, engines: {} };
    }
    var wrap = (((page.data || {}).accessControl) || {}).endSystems || {};
    if (wrap.success === false) {
      return { ok: 0, error: String(wrap.errorMessage || 'endSystems success=false'), truncated: truncated, fetched: rows.length, nacUsed24h: 0, users24h: 0, engines: {} };
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
  var counted = countLicenseWindow(rows, Date.now(), 86400000);
  return {
    ok: 1,
    error: '',
    truncated: truncated,
    fetched: rows.length,
    nacUsed24h: counted.nacUsed24h,
    users24h: counted.users24h,
    engines: counted.engines
  };
}

var params = JSON.parse(value);
return JSON.stringify(collectLicenses(params));
