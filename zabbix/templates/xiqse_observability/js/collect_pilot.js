var PILOT_QUERIES = [
  '{ network { devices { deviceData { xiqLicenseState } } } }',
  '{ network { devices { ip deviceData { xiqLicenseState } } } }'
];

function collectPilot(params) {
  var auth = fetchToken(params);
  if (!auth.ok) {
    return { ok: 0, error: auth.error, pilotUsed: 0 };
  }
  var result = graphqlTry(params, auth.token, PILOT_QUERIES);
  if (!result.ok) {
    return { ok: 0, error: result.error, pilotUsed: 0 };
  }
  var devices = (((result.data || {}).network) || {}).devices;
  return { ok: 1, error: '', pilotUsed: countPilot(devices) };
}

var params = JSON.parse(value);
return JSON.stringify(collectPilot(params));
