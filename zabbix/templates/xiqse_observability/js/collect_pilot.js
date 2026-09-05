var PILOT_QUERIES = [
  '{ network { devices { deviceData { xiqLicenseState } } } }',
  '{ network { devices { ip deviceData { xiqLicenseState } } } }'
];

function emptyPilotSnapshot(error) {
  var counted = emptyDeviceLicenses();
  return {
    ok: 0,
    error: error,
    pilotUsed: counted.pilotUsed,
    navigatorUsed: counted.navigatorUsed,
    pending: counted.pending,
    unmanaged: counted.unmanaged,
    other: counted.other
  };
}

function collectPilot(params) {
  var auth = fetchToken(params);
  if (!auth.ok) {
    return emptyPilotSnapshot(auth.error);
  }
  var result = graphqlTry(params, auth.token, PILOT_QUERIES);
  if (!result.ok) {
    return emptyPilotSnapshot(result.error);
  }
  var devices = (((result.data || {}).network) || {}).devices;
  var counted = countDeviceLicenses(devices);
  return {
    ok: 1,
    error: '',
    pilotUsed: counted.pilotUsed,
    navigatorUsed: counted.navigatorUsed,
    pending: counted.pending,
    unmanaged: counted.unmanaged,
    other: counted.other
  };
}

var params = JSON.parse(value);
return JSON.stringify(collectPilot(params));
