var SERVER_INFO_QUERY = '{ administration { serverInfo { version upTime startTime heapMemoryUsed heapMemoryMax freePhysicalMemory totalPhysicalMemory threadCount } } }';
var ENGINES_QUERIES = [
  '{ accessControl { engines { ipAddress name displayName version licensed capacity freeRadiusEnabled needsEnforce connected virtual } } }',
  '{ accessControl { engines { ipAddress name displayName version licensed capacity freeRadiusEnabled needsEnforce isConnected virtual } } }',
  '{ accessControl { engines { ipAddress name displayName version licensed capacity freeRadiusEnabled needsEnforce virtual } } }',
  '{ accessControl { engines { ipAddress name version licensed capacity } } }',
  '{ accessControl { engines { ipAddress name } } }'
];

function collectHealth(params) {
  var auth = fetchToken(params);
  if (!auth.ok) {
    return { ok: 0, error: auth.error, engineCount: 0, engines: [] };
  }
  var info = graphql(params, auth.token, SERVER_INFO_QUERY);
  if (!info.ok) {
    return { ok: 0, error: info.error, engineCount: 0, engines: [] };
  }
  var server = (((info.data || {}).administration || {}).serverInfo) || {};
  var enginesResult = graphqlTry(params, auth.token, ENGINES_QUERIES);
  var engines = [];
  if (enginesResult.ok) {
    engines = normalizeEngines((((enginesResult.data || {}).accessControl) || {}).engines);
  }
  return {
    ok: 1,
    error: enginesResult.ok ? '' : String(enginesResult.error || ''),
    version: String(server.version || ''),
    upTime: uptimeSeconds(server.upTime),
    startTime: String(server.startTime || ''),
    heapMemoryUsed: Number(server.heapMemoryUsed) || 0,
    heapMemoryMax: Number(server.heapMemoryMax) || 0,
    freePhysicalMemory: Number(server.freePhysicalMemory) || 0,
    totalPhysicalMemory: Number(server.totalPhysicalMemory) || 0,
    threadCount: Number(server.threadCount) || 0,
    engineCount: engines.length,
    engines: engines
  };
}

var params = JSON.parse(value);
return JSON.stringify(collectHealth(params));
