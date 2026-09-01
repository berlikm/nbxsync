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
    return nbiHealthSnapshot({}, [], auth.error);
  }
  var info = graphql(params, auth.token, SERVER_INFO_QUERY);
  if (!info.ok) {
    return nbiHealthSnapshot({}, [], info.error);
  }
  var server = (((info.data || {}).administration || {}).serverInfo) || {};
  var enginesResult = graphqlTry(params, auth.token, ENGINES_QUERIES);
  var engines = [];
  if (enginesResult.ok) {
    engines = normalizeEngines((((enginesResult.data || {}).accessControl) || {}).engines);
  }
  return nbiHealthSnapshot(
    server,
    engines,
    enginesResult.ok ? '' : String(enginesResult.error || ''),
    1
  );
}

var params = JSON.parse(value);
return JSON.stringify(collectHealth(params));
